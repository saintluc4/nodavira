import asyncio
import csv
import io
import json
import secrets
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .config import DOMAINS, catalog, validate_config
from .engine import Benchmark
from . import __version__


def csv_report(report):
    output = io.StringIO(newline="")
    fields = ["resolver", "address", "protocol", "family", "phase", "round", "domain", "qtype",
              "ms", "ok", "status", "ad", "ttl", "tcp_fallback", "http_version", "answers", "detail"]
    writer = csv.DictWriter(output, fields, extrasaction="ignore")
    writer.writeheader()
    resolvers = {r["id"]: r for r in report.get("config", {}).get("resolvers", [])}
    for sample in report.get("samples", []):
        r = resolvers[sample["resolver_id"]]
        row = {**sample, "resolver": r["name"], "address": r["address"],
               "protocol": r["protocol"], "family": r["family"], "answers": " | ".join(sample["answers"])}
        # Prevent spreadsheet formula execution in user-supplied labels.
        for key, value in row.items():
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                row[key] = "'" + value
        writer.writerow(row)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


class AppState:
    def __init__(self, output_dir):
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.report = {"state": "idle", "rows": [], "completed": 0, "total": 0, "message": "Pronto para começar"}
        self.stop = threading.Event()
        self.worker = None
        self.last_seen = time.monotonic()
        self.output_dir = Path(output_dir)
        self.desktop = {"mode": "server", "renderer": None, "loaded": False}

    def update(self, report):
        with self.lock:
            self.report = report

    def snapshot(self, full=False):
        with self.lock:
            result = dict(self.report) if full else {k: v for k, v in self.report.items() if k not in ("samples", "batches", "diagnostics")}
            result["desktop"] = dict(self.desktop)
            return result

    def set_desktop(self, **values):
        with self.lock:
            self.desktop.update(values)

    def start(self, config):
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("Já existe um benchmark em andamento.")
            self.stop = threading.Event()
            benchmark = Benchmark(config, self.update, self.stop)
            self.report = benchmark.snapshot()
            self.worker = threading.Thread(target=self.run, args=(benchmark,), daemon=True)
            self.worker.start()

    def run(self, benchmark):
        try:
            report = asyncio.run(benchmark.run())
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                destination = self.output_dir / f"nodavira-{stamp}.json"
                destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                report["saved_to"] = str(destination)
            except OSError as exc:
                report["save_error"] = f"Não foi possível salvar automaticamente: {exc}. Use Exportar."
            self.update(report)
        except Exception as exc:
            report = benchmark.snapshot()
            report.update(state="error", message=f"Erro no benchmark: {type(exc).__name__}: {exc}")
            self.update(report)


def make_server(static_dir, output_dir, port=0):
    state = AppState(output_dir)
    static_dir = Path(static_dir)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                # A closed WebView may drop an idle HTTP keep-alive connection.
                pass

        def log_message(self, *_):
            pass

        def authorized(self):
            expected_host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected_host:
                return False
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{expected_host}":
                return False
            parsed = urlsplit(self.path)
            token = self.headers.get("X-Nodavira-Token") or parse_qs(parsed.query).get("token", [""])[0]
            return secrets.compare_digest(token, state.token)

        def send(self, status, data, content_type="application/json; charset=utf-8", filename=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            path = urlsplit(self.path).path
            if path.startswith("/api/"):
                if not self.authorized():
                    return self.send(403, {"error": "Sessão inválida. Abra o aplicativo novamente."})
                state.last_seen = time.monotonic()
                if path == "/api/config":
                    return self.send(200, {"domains": DOMAINS, "resolvers": catalog(), "version": __version__})
                if path == "/api/status":
                    return self.send(200, state.snapshot())
                if path == "/api/export.json":
                    return self.send(200, state.snapshot(True), filename="nodavira-resultados.json")
                if path == "/api/export.csv":
                    return self.send(200, csv_report(state.snapshot(True)), "text/csv; charset=utf-8", "nodavira-consultas.csv")
                return self.send(404, {"error": "Não encontrado"})
            files = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8"),
                     "/favicon.svg": ("favicon.svg", "image/svg+xml"),
                     "/wordmark.svg": ("wordmark.svg", "image/svg+xml"),
                     "/notices.txt": ("notices.txt", "text/plain; charset=utf-8")}
            if path not in files:
                return self.send(404, {"error": "Não encontrado"})
            filename, content_type = files[path]
            return self.send(200, (static_dir / filename).read_bytes(), content_type)

        def do_POST(self):
            if not self.authorized():
                self.close_connection = True
                return self.send(403, {"error": "Sessão inválida"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 128000:
                    self.close_connection = True
                    return self.send(413, {"error": "Configuração grande demais ou vazia"})
                data = json.loads(self.rfile.read(length))
                state.last_seen = time.monotonic()
                path = urlsplit(self.path).path
                if path == "/api/start":
                    state.start(validate_config(data))
                elif path == "/api/stop":
                    state.stop.set()
                elif path == "/api/shutdown":
                    state.stop.set()
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                else:
                    return self.send(404, {"error": "Não encontrado"})
                self.send(200, {"ok": True})
            except (ValueError, TypeError, KeyError) as exc:
                self.send(400, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server, state
