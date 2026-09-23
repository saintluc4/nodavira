import asyncio
import math
import random
import ssl
import statistics
import struct
import threading
import time
from collections import Counter
from datetime import datetime, timezone

import dns.asyncbackend
import dns.asyncquery
import dns.flags
import dns.message
import dns.rcode
import dns.rdatatype
import httpx
from . import __version__


def percentile(values, fraction):
    """Linear interpolation, same definition in exports and UI."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def summarize(samples, timeout_ms):
    good = [s["ms"] for s in samples if s["ok"]]
    # A fast refusal or NXDOMAIN must never win a positive-domain workload.
    costs = [s["ms"] if s["ok"] else max(s["ms"], timeout_ms) for s in samples]
    return {"count": len(samples), "success": len(good),
            "failure_pct": 100 * (len(samples) - len(good)) / len(samples) if samples else None,
            "median_ms": statistics.median(good) if good else None,
            "p95_ms": percentile(good, .95), "mean_ms": statistics.mean(good) if good else None,
            "cost_ms": statistics.mean(costs) if costs else None,
            "min_ms": min(good) if good else None, "max_ms": max(good) if good else None,
            "stddev_ms": statistics.pstdev(good) if good else None,
            "errors": dict(Counter(s["status"] for s in samples if not s["ok"])),
            "nodata": sum(s["status"] == "NODATA" for s in samples),
            "tcp_fallbacks": sum(s.get("tcp_fallback", False) for s in samples)}


class QueryClient:
    """One sequential lane; DoH and DoT connections persist between batches."""
    def __init__(self, resolver, timeout_ms):
        self.resolver = resolver
        self.timeout = timeout_ms / 1000
        self.http = None
        self.reader = None
        self.writer = None
        self.tls = ssl.create_default_context()

    async def close(self):
        if self.http:
            await self.http.aclose()
            self.http = None
        await self.close_stream()

    async def close_stream(self):
        if self.writer:
            self.writer.close()
            try:
                await asyncio.wait_for(self.writer.wait_closed(), .3)
            except Exception:
                pass
        self.reader = self.writer = None

    async def exchange(self, query):
        r = self.resolver
        fallback, connection_new, http_version = False, False, None
        if r["protocol"] == "udp":
            response, fallback = await dns.asyncquery.udp_with_fallback(
                query, r["address"], timeout=self.timeout, port=r["port"])
        elif r["protocol"] == "doh":
            if self.http is None:
                # Pin the connection to the selected IPv4/IPv6 IP while keeping
                # the original HTTPS authority, SNI and certificate validation.
                transport = dns.asyncbackend.get_backend("asyncio").get_transport_class()(
                    http1=True, http2=True, verify=self.tls,
                    bootstrap_address=r["address"],
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=1,
                                        keepalive_expiry=120))
                self.http = httpx.AsyncClient(transport=transport, trust_env=False,
                                               timeout=self.timeout, follow_redirects=False)
                connection_new = True
            query.id = 0
            async with self.http.stream("POST", r["url"], content=query.to_wire(),
                                        headers={"Content-Type": "application/dns-message",
                                                 "Accept": "application/dns-message"}) as result:
                result.raise_for_status()
                if result.headers.get("content-type", "").split(";")[0].strip().lower() != "application/dns-message":
                    raise ValueError("Tipo de resposta DoH inválido")
                chunks, size = [], 0
                async for chunk in result.aiter_bytes():
                    size += len(chunk)
                    if size > 65535:
                        raise ValueError("Resposta DNS grande demais")
                    chunks.append(chunk)
                response = dns.message.from_wire(b"".join(chunks))
                http_version = result.http_version
        else:
            if self.writer is None or self.writer.is_closing():
                self.reader, self.writer = await asyncio.open_connection(
                    r["address"], r["port"], ssl=self.tls, server_hostname=r["hostname"])
                connection_new = True
            wire = query.to_wire()
            self.writer.write(struct.pack("!H", len(wire)) + wire)
            await self.writer.drain()
            length = struct.unpack("!H", await self.reader.readexactly(2))[0]
            response = dns.message.from_wire(await self.reader.readexactly(length))
        if not query.is_response(response) or response.flags & dns.flags.TC:
            raise ValueError("Resposta DNS incompatível ou truncada")
        return response, fallback, connection_new, http_version

    async def query(self, domain, qtype):
        query = dns.message.make_query(domain, qtype, use_edns=0, payload=1232, want_dnssec=True)
        started = time.perf_counter()
        sample = {"domain": domain, "qtype": qtype, "ok": False, "status": "ERROR",
                  "tcp_fallback": False, "connection_new": False, "http_version": None,
                  "ad": False, "answers": [], "ttl": None, "detail": ""}
        try:
            response, fallback, fresh, http_version = await asyncio.wait_for(self.exchange(query), self.timeout)
            sample["ms"] = (time.perf_counter() - started) * 1000
            rcode = response.rcode()
            sample.update(status=dns.rcode.to_text(rcode), tcp_fallback=fallback,
                          connection_new=fresh, http_version=http_version,
                          ad=bool(response.flags & dns.flags.AD))
            answers = [rr for rr in response.answer if rr.rdtype == dns.rdatatype.from_text(qtype)]
            sample["answers"] = [item.to_text() for rr in answers for item in rr][:32]
            sample["ttl"] = min((rr.ttl for rr in answers), default=None)
            sample["ok"] = rcode == dns.rcode.NOERROR
            if sample["ok"] and not answers:
                sample["status"] = "NODATA"
            elif sample["ok"] and any(x in ("0.0.0.0", "::") for x in sample["answers"]):
                sample.update(ok=False, status="BLOCKED")
        except (asyncio.TimeoutError, dns.exception.Timeout, httpx.TimeoutException):
            sample.update(ms=(time.perf_counter() - started) * 1000, status="TIMEOUT",
                          detail="Tempo limite excedido")
            await self.close_stream()
        except Exception as exc:
            sample.update(ms=(time.perf_counter() - started) * 1000,
                          status=type(exc).__name__, detail=str(exc)[:250])
            await self.close_stream()
        return sample


class Benchmark:
    def __init__(self, config, progress=None, stop=None, client_factory=QueryClient):
        self.config = config
        self.progress = progress or (lambda result: None)
        self.stop = stop or threading.Event()
        self.client_factory = client_factory
        self.samples, self.batches, self.diagnostics = [], [], []
        self.available = set()
        self.started = datetime.now(timezone.utc).isoformat()
        self.clock = time.perf_counter()
        self.message = "Verificando conexões…"
        self.state = "running"
        self.total = len(config["resolvers"]) * len(config["domains"]) * len(config["qtypes"]) * config["rounds"]
        self.planned = self.total

    def snapshot(self):
        rows = []
        for r in self.config["resolvers"]:
            samples = [s for s in self.samples if s["resolver_id"] == r["id"]]
            first = summarize([s for s in samples if s["phase"] == "first"], self.config["timeout_ms"])
            repeat = summarize([s for s in samples if s["phase"] == "repeat"], self.config["timeout_ms"])
            summary = summarize(samples, self.config["timeout_ms"])
            # Equal phase weight, independent of the number of repeated passes.
            score = (first["cost_ms"] + repeat["cost_ms"]) / 2 if first["cost_ms"] is not None and repeat["cost_ms"] is not None else None
            batches = [b["ms"] for b in self.batches if b["resolver_id"] == r["id"]]
            diag = [s for s in self.diagnostics if s["resolver_id"] == r["id"]]
            rows.append({**r, **summary, "first": first, "repeat": repeat,
                         "score_ms": score, "batch_p95_ms": percentile(batches, .95),
                         "available": r["id"] in self.available,
                         "setup_ms": statistics.median([s["ms"] for s in diag if s["ok"]]) if any(s["ok"] for s in diag) else None,
                         "diagnostic_errors": dict(Counter(s["status"] for s in diag if not s["ok"])),
                         "http_versions": sorted(set(s["http_version"] for s in samples if s.get("http_version")))})
        rows.sort(key=lambda r: (r["score_ms"] is None or r["success"] == 0, r["score_ms"] or float("inf")))
        return {"schema": 1, "version": __version__, "state": self.state, "message": self.message,
                "started_at": self.started, "elapsed_seconds": time.perf_counter() - self.clock,
                "completed": len(self.samples), "total": self.total, "planned": self.planned,
                "config": self.config, "rows": rows, "samples": list(self.samples),
                "batches": list(self.batches), "diagnostics": list(self.diagnostics)}

    def publish(self):
        self.progress(self.snapshot())

    async def run(self):
        cfg = self.config
        rng = random.Random(cfg["seed"])
        lanes = {r["id"]: [self.client_factory(r, cfg["timeout_ms"]) for _ in range(cfg["concurrency"])] for r in cfg["resolvers"]}
        try:
            self.publish()
            preflight_order = list(cfg["resolvers"])
            rng.shuffle(preflight_order)
            for r in preflight_order:
                if self.stop.is_set():
                    break
                self.message = f"Verificando {r['name']} · {r['protocol'].upper()} · {r['family']}"
                self.publish()
                # Two distinct known names prevent a single filtered name from
                # suppressing an endpoint. No statistical samples are discarded.
                probes = await asyncio.gather(*(c.query("example.com", "A") for c in lanes[r["id"]]))
                if not any(s["ok"] for s in probes):
                    probes.append(await lanes[r["id"]][0].query("iana.org", "A"))
                for sample in probes:
                    sample["resolver_id"] = r["id"]
                    self.diagnostics.append(sample)
                if any(s["ok"] for s in probes):
                    self.available.add(r["id"])
            self.total = len(self.available) * len(cfg["domains"]) * len(cfg["qtypes"]) * cfg["rounds"]
            self.publish()
            pairs = [(domain, kind) for domain in cfg["domains"] for kind in cfg["qtypes"]]
            for round_index in range(cfg["rounds"]):
                order = list(pairs)
                rng.shuffle(order)
                for offset in range(0, len(order), cfg["concurrency"]):
                    group = order[offset:offset + cfg["concurrency"]]
                    resolver_order = [r for r in cfg["resolvers"] if r["id"] in self.available]
                    rng.shuffle(resolver_order)
                    for r in resolver_order:
                        if self.stop.is_set():
                            break
                        self.message = f"Passagem {round_index + 1}/{cfg['rounds']} · {r['name']} · {r['protocol'].upper()}"
                        start = time.perf_counter()
                        results = await asyncio.gather(*(lanes[r["id"]][i].query(*pair) for i, pair in enumerate(group)))
                        batch_ms = (time.perf_counter() - start) * 1000
                        batch_index = len(self.batches)
                        for sample in results:
                            sample.update(resolver_id=r["id"], phase="first" if round_index == 0 else "repeat",
                                          round=round_index + 1, batch=batch_index)
                            self.samples.append(sample)
                        self.batches.append({"resolver_id": r["id"], "round": round_index + 1,
                                             "ms": batch_ms, "count": len(group)})
                        self.publish()
                        await asyncio.sleep(.05)
                    if self.stop.is_set():
                        break
                if self.stop.is_set():
                    break
            self.state = "cancelled" if self.stop.is_set() else "complete"
            self.message = "Teste interrompido; resultados parciais." if self.stop.is_set() else "Benchmark concluído." if self.available else "Nenhum servidor respondeu. Verifique conexão, firewall e protocolos selecionados."
        finally:
            await asyncio.gather(*(c.close() for pool in lanes.values() for c in pool), return_exceptions=True)
        self.publish()
        return self.snapshot()
