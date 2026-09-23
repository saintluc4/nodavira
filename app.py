"""Run from source or as the portable Windows executable."""
import sys
from pathlib import Path

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
if (ROOT / ".deps").is_dir():
    sys.path.insert(0, str(ROOT / ".deps"))

import argparse
import json
import threading
import time
import webbrowser

from nodavira.server import make_server
from nodavira.desktop import run_window


def main():
    parser = argparse.ArgumentParser(description="Nodavira — benchmark local de DNS")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--no-browser", action="store_true", help="Executar só o servidor, sem janela")
    modes.add_argument("--browser", action="store_true", help="Abrir no navegador em vez da janela Windows")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--session-file", type=Path)
    parser.add_argument("--hidden-window", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    server, state = make_server(ROOT / "static", output / "reports", args.port)
    url = f"http://127.0.0.1:{server.server_port}/#token={state.token}"
    if args.session_file:
        args.session_file.write_text(json.dumps({"url": url, "port": server.server_port}), encoding="utf-8")
    if sys.stdout:
        print(f"Nodavira: {url}", flush=True)
    server_finished = threading.Event()

    def serve():
        try:
            server.serve_forever(poll_interval=.3)
        finally:
            server_finished.set()

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    def idle_watch():
        while not server_finished.wait(5):
            # Closing the browser does not interrupt a running measurement.
            if time.monotonic() - state.last_seen > 120 and not (state.worker and state.worker.is_alive()):
                server.shutdown()
                return

    try:
        if args.no_browser:
            while not server_finished.wait(.5):
                pass
        elif args.browser:
            state.set_desktop(mode="browser")
            webbrowser.open(url)
            threading.Thread(target=idle_watch, daemon=True).start()
            while not server_finished.wait(.5):
                pass
        else:
            run_window(url, state, server_finished, hidden=args.hidden_window)
    except KeyboardInterrupt:
        pass
    finally:
        state.stop.set()
        server.shutdown()
        server_thread.join(2)
        if state.worker:
            state.worker.join(7)
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        message = ("Não foi possível iniciar o Nodavira.\n\n"
                   "A janela requer o Microsoft Edge WebView2 Runtime e .NET Framework 4.6.2 ou superior.\n"
                   "WebView2: https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
                   "Como alternativa, execute Nodavira.exe --browser.\n\n"
                   f"Detalhe: {type(exc).__name__}: {exc}")
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "Nodavira", 0x10)
        else:
            raise
