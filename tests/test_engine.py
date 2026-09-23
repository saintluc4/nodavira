import asyncio
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".deps"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dns.flags
import dns.message
import dns.rcode
import dns.rrset
import httpx
from nodavira.config import normalize_domains, validate_config
from nodavira.engine import Benchmark, QueryClient, percentile, summarize
from nodavira.server import csv_report


def resolver(protocol="udp", name="test"):
    return {"name": name, "protocol": protocol, "address": "127.0.0.1", "hostname": "dns.example.com",
            "url": "https://dns.example.com/dns-query"}


def sample(ms=10, ok=True, status="NOERROR"):
    return {"ms": ms, "ok": ok, "status": status, "tcp_fallback": False,
            "domain": "example.com", "qtype": "A", "answers": [], "http_version": None}


class ConfigTests(unittest.TestCase):
    def test_domains_idn_url_and_deduplication(self):
        self.assertEqual(normalize_domains("Example.com\nexample.com. https://www.python.org/a café.com"),
                         ["example.com", "www.python.org", "xn--caf-dma.com"])

    def test_reject_malformed_domains(self):
        for value in ["", "a..com", "foo.-bar.com", "localhost", "*.example.com", "a"*64 + ".com"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_domains(value)

    def test_limits(self):
        for key, value in [("rounds", 1), ("timeout_ms", 0), ("concurrency", 99), ("qtypes", []), ("resolvers", [])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_config({"resolvers": [resolver()], key: value})

    def test_dedup_udp_ignores_hostname(self):
        a, b = resolver(), resolver(name="duplicate")
        b["hostname"] = "different.example.com"
        self.assertEqual(len(validate_config({"resolvers": [a, b]})["resolvers"]), 1)

    def test_ipv6_transport_independent_of_qtype(self):
        r = resolver(); r["address"] = "::1"
        config = validate_config({"resolvers": [r], "qtypes": ["A"]})
        self.assertEqual(config["resolvers"][0]["family"], "IPv6")
        self.assertEqual(config["qtypes"], ["A"])

    def test_reject_plaintext_doh_and_tls_without_host(self):
        r = resolver("doh"); r["url"] = "http://dns.example.com"
        with self.assertRaises(ValueError): validate_config({"resolvers": [r]})
        r = resolver("dot"); r["hostname"] = ""
        with self.assertRaises(ValueError): validate_config({"resolvers": [r]})


class StatisticsTests(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([10,20,30,40,50], .95), 48)
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile([12], .95), 12)

    def test_fast_failure_is_penalized_and_not_in_latency(self):
        result = summarize([sample(10), sample(1, False, "REFUSED")], 1500)
        self.assertEqual(result["median_ms"], 10)
        self.assertEqual(result["failure_pct"], 50)
        self.assertEqual(result["cost_ms"], 755)

    def test_all_failed_has_no_success_latency(self):
        result = summarize([sample(2000, False, "TIMEOUT")], 1500)
        self.assertIsNone(result["p95_ms"])
        self.assertEqual(result["cost_ms"], 2000)

    def test_phase_weight_independent_of_repeat_count(self):
        config = validate_config({"resolvers": [resolver()], "rounds": 5})
        benchmark = Benchmark(config)
        benchmark.samples = [{**sample(100), "resolver_id": "r0", "phase": "first"}] + [
            {**sample(10), "resolver_id": "r0", "phase": "repeat"} for _ in range(4)]
        self.assertEqual(benchmark.snapshot()["rows"][0]["score_ms"], 55)

    def test_empty_data_not_zero_latency(self):
        self.assertIsNone(summarize([], 1000)["cost_ms"])


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def http_query(self, status=200, media="application/dns-message", rcode=0, wrong_id=False, address="1.2.3.4", body=None):
        r = validate_config({"resolvers": [resolver("doh")]})["resolvers"][0]
        client = QueryClient(r, 1000)
        def respond(request):
            query = dns.message.from_wire(request.content)
            self.assertEqual(query.id, 0)
            self.assertEqual(request.headers["content-type"], "application/dns-message")
            response = dns.message.make_response(query)
            response.set_rcode(rcode)
            if wrong_id: response.id = 1
            if address and rcode == 0:
                response.answer.append(dns.rrset.from_text("example.com.", 60, "IN", "A", address))
            return httpx.Response(status, headers={"content-type": media}, content=body or response.to_wire())
        client.http = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        try: return await client.query("example.com", "A")
        finally: await client.close()

    async def test_doh_wire_roundtrip(self):
        result = await self.http_query()
        self.assertTrue(result["ok"])
        self.assertEqual(result["answers"], ["1.2.3.4"])
        self.assertEqual(result["ttl"], 60)

    async def test_wrong_response_id_rejected(self):
        self.assertFalse((await self.http_query(wrong_id=True))["ok"])

    async def test_wrong_content_type_rejected(self):
        self.assertFalse((await self.http_query(media="text/html"))["ok"])

    async def test_http_error_rejected(self):
        self.assertFalse((await self.http_query(status=503))["ok"])

    async def test_oversized_reply_rejected(self):
        self.assertFalse((await self.http_query(body=b'x'*65536))["ok"])

    async def test_nxdomain_is_resolution_failure(self):
        result = await self.http_query(rcode=dns.rcode.NXDOMAIN)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "NXDOMAIN")

    async def test_nodata_is_valid_but_labeled(self):
        result = await self.http_query(address=None)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "NODATA")

    async def test_block_address_not_success(self):
        result = await self.http_query(address="0.0.0.0")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")

    async def test_timeout_bounds_total_exchange(self):
        client = QueryClient(validate_config({"resolvers": [resolver()]})["resolvers"][0], 20)
        async def slow(_): await asyncio.sleep(5)
        client.exchange = slow
        result = await client.query("example.com", "A")
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertLess(result["ms"], 300)

    async def test_udp_fallback_recorded(self):
        async def fake(query, *_args, **_kwargs):
            return dns.message.make_response(query), True
        client = QueryClient(validate_config({"resolvers": [resolver()]})["resolvers"][0], 1000)
        with patch("dns.asyncquery.udp_with_fallback", fake):
            result = await client.query("example.com", "AAAA")
        self.assertTrue(result["tcp_fallback"])


class FakeClient:
    calls = []
    closed = 0
    def __init__(self, r, _timeout): self.r = r
    async def query(self, domain, qtype):
        self.calls.append((self.r["id"], domain, qtype))
        return {**sample(), "domain": domain, "qtype": qtype}
    async def close(self): FakeClient.closed += 1


class ScheduleTests(unittest.IsolatedAsyncioTestCase):
    async def test_equal_workload_and_complete_cleanup(self):
        a, b = resolver(), resolver(name="second"); b["address"]="127.0.0.2"
        cfg = validate_config({"resolvers": [a,b], "domains":["python.org","github.com"], "rounds":2, "concurrency":2, "seed":42})
        FakeClient.calls=[];FakeClient.closed=0
        result = await Benchmark(cfg, client_factory=FakeClient).run()
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["completed"], 16)
        for row in result["rows"]:
            self.assertEqual(row["count"], 8)
            self.assertEqual(row["first"]["count"], 4)
            self.assertEqual(row["repeat"]["count"], 4)
        self.assertEqual(FakeClient.closed, 4)
        actual = [(s["resolver_id"],s["domain"],s["qtype"],s["round"]) for s in result["samples"]]
        repeat = await Benchmark(cfg, client_factory=FakeClient).run()
        self.assertEqual(actual, [(s["resolver_id"],s["domain"],s["qtype"],s["round"]) for s in repeat["samples"]])

    async def test_cancellation_is_partial(self):
        stop=threading.Event();stop.set()
        result=await Benchmark(validate_config({"resolvers":[resolver()]}), stop=stop, client_factory=FakeClient).run()
        self.assertEqual(result["state"],"cancelled")
        self.assertEqual(result["completed"],0)
        self.assertIsNone(result["rows"][0]["score_ms"])

    async def test_unavailable_is_visible_and_unranked(self):
        class Offline(FakeClient):
            async def query(self, domain, qtype): return sample(1,False,"REFUSED")
        result=await Benchmark(validate_config({"resolvers":[resolver()]}), client_factory=Offline).run()
        self.assertEqual(result["total"],0)
        self.assertEqual(result["planned"],180)
        self.assertFalse(result["rows"][0]["available"])
        self.assertIsNone(result["rows"][0]["score_ms"])

    def test_csv_formula_protection(self):
        cfg=validate_config({"resolvers":[resolver(name="=DANGEROUS()")]})
        data=csv_report({"config":cfg,"samples":[{**sample(),"resolver_id":"r0"}]}).decode("utf-8-sig")
        self.assertIn("'=DANGEROUS()",data)


if __name__ == '__main__': unittest.main()
