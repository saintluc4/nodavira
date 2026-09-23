"""Small real-network verification. Does not modify DNS settings."""
import asyncio
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT / ".deps"),str(ROOT)]
from nodavira.config import catalog, validate_config
from nodavira.engine import QueryClient


async def main():
    if "--check-domains" in sys.argv:
        r=validate_config({"resolvers":[r for r in catalog() if r["name"]=="Cloudflare" and r["protocol"]=="udp" and r["family"]=="IPv4"]})["resolvers"][0]
        client=QueryClient(r,2000)
        try:
            for domain in ["raw.githubusercontent.com","download.windowsupdate.com","static-cdn.jtvnw.net","i.scdn.co"]:
                results=[await client.query(domain,kind) for kind in ["A","AAAA"]]
                print(json.dumps({"domain":domain,"results":[(s["qtype"],s["status"],s["answers"]) for s in results]}))
        finally: await client.close()
        return
    selected=[r for r in catalog() if r["name"]=="Cloudflare"]
    cfg=validate_config({"resolvers":selected,"domains":["example.com"]})
    results=[]
    for resolver in cfg["resolvers"]:
        client=QueryClient(resolver,2000)
        try:
            first=await client.query("example.com","A")
            second=await client.query("example.com","AAAA")
            row={"resolver":resolver,"first":first,"second":second}
            results.append(row)
            print(json.dumps({"protocol":resolver["protocol"],"family":resolver["family"],
                              "first":first["status"],"second":second["status"],"ms":round(second["ms"],2),
                              "http":second["http_version"],"detail":second["detail"]}),flush=True)
        finally: await client.close()
    folder=ROOT/"reports";folder.mkdir(exist_ok=True)
    (folder/"network-smoke.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    if any('10013' in row[phase]['detail'] for row in results for phase in ('first','second')):
        raise SystemExit(2)

asyncio.run(main())
