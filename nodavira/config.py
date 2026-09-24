import ipaddress
import re
import secrets
from urllib.parse import urlsplit

import dns.name
import dns.resolver

DOMAINS = [
    "google.com", "youtube.com", "gstatic.com", "googlevideo.com",
    "microsoft.com", "office.com", "live.com", "download.windowsupdate.com",
    "github.com", "raw.githubusercontent.com", "cloudflare.com", "wikipedia.org",
    "amazon.com.br", "mercadolivre.com.br", "globo.com", "uol.com.br",
    "netflix.com", "nflxvideo.net", "spotify.com", "i.scdn.co",
    "twitch.tv", "static-cdn.jtvnw.net", "steampowered.com", "steamcommunity.com",
    "epicgames.com", "discord.com", "discordapp.com", "whatsapp.com",
    "instagram.com", "facebook.com",
]


def normalize_domains(value):
    if not isinstance(value, (str, list)):
        raise ValueError("Informe uma lista de domínios.")
    values = re.split(r"[\s,;]+", value) if isinstance(value, str) else value
    result = []
    for item in values:
        if not isinstance(item, str):
            raise ValueError("Domínio inválido.")
        item = item.strip().lower().rstrip(".")
        if not item:
            continue
        if "://" in item:
            item = urlsplit(item).hostname or ""
        try:
            item = item.encode("idna").decode("ascii")
            labels = item.split(".")
            if len(labels) < 2 or len(item) > 253 or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels
            ):
                raise ValueError()
            dns.name.from_text(item)
        except (ValueError, UnicodeError, dns.name.NameTooLong):
            raise ValueError(f"Domínio inválido: {item[:100]}") from None
        if item not in result:
            result.append(item)
    if not 1 <= len(result) <= 300:
        raise ValueError("Use entre 1 e 300 domínios diferentes.")
    return result


def catalog():
    providers = [
        ("Cloudflare", "1.1.1.1", "2606:4700:4700::1111", "cloudflare-dns.com", "Sem filtro de conteúdo"),
        ("Google", "8.8.8.8", "2001:4860:4860::8888", "dns.google", "Sem filtro de conteúdo"),
        ("Quad9", "9.9.9.9", "2620:fe::fe", "dns.quad9.net", "Bloqueio de domínios maliciosos"),
    ]
    result = []
    for name, v4, v6, host, policy in providers:
        for family, address in [("IPv4", v4), ("IPv6", v6)]:
            for protocol in ("udp", "doh", "dot"):
                result.append({"id": f"{name.lower()}-{family.lower()}-{protocol}",
                               "name": name, "address": address, "family": family,
                               "protocol": protocol, "hostname": host,
                               "url": f"https://{host}/dns-query", "policy": policy,
                               "port": {"udp": 53, "dot": 853, "doh": 443}[protocol]})
    try:
        nameservers = dns.resolver.Resolver().nameservers
    except Exception:
        nameservers = []
    for index, address in enumerate(nameservers):
        try:
            family = f"IPv{ipaddress.ip_address(address).version}"
        except ValueError:
            continue
        existing = next((r for r in result if r["address"] == address and r["protocol"] == "udp"), None)
        if existing:
            existing["policy"] += " · Também configurado no sistema"
            continue
        result.insert(index, {"id": f"system-{index}", "name": "DNS do sistema",
                             "address": address, "family": family, "protocol": "udp",
                             "hostname": "", "url": "", "port": 53,
                             "policy": "Servidor configurado no sistema"})
    return result


def validate_config(data):
    if not isinstance(data, dict):
        raise ValueError("Configuração inválida.")
    domains = normalize_domains(data.get("domains", DOMAINS))
    try:
        rounds = int(data.get("rounds", 3))
        concurrency = int(data.get("concurrency", 4))
        timeout = int(data.get("timeout_ms", 1500))
        seed = int(data.get("seed", secrets.randbelow(2**31)))
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Use valores numéricos válidos.") from None
    if not 2 <= rounds <= 10 or not 1 <= concurrency <= 8 or not 500 <= timeout <= 5000:
        raise ValueError("Use 2–10 passagens, 1–8 consultas paralelas e timeout de 500–5000 ms.")
    qtypes = data.get("qtypes", ["A", "AAAA"])
    if not isinstance(qtypes, list) or not qtypes or any(x not in ["A", "AAAA"] for x in qtypes):
        raise ValueError("Selecione A e/ou AAAA.")
    resolvers = data.get("resolvers", [])
    if not isinstance(resolvers, list) or not 1 <= len(resolvers) <= 32:
        raise ValueError("Selecione entre 1 e 32 servidores.")
    validated, seen = [], set()
    for r in resolvers:
        if not isinstance(r, dict):
            raise ValueError("Servidor inválido.")
        protocol = r.get("protocol")
        if protocol not in ("udp", "doh", "dot"):
            raise ValueError("Protocolo inválido.")
        try:
            address = str(ipaddress.ip_address(r.get("address", "")))
            port = int(r.get("port") or {"udp": 53, "dot": 853, "doh": 443}[protocol])
        except (ValueError, TypeError):
            raise ValueError("Informe um IP de servidor válido.") from None
        if not 1 <= port <= 65535:
            raise ValueError("Porta inválida.")
        host = str(r.get("hostname", ""))[:253]
        url = str(r.get("url", ""))[:1000]
        if protocol == "doh":
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError("DoH exige uma URL HTTPS válida, sem credenciais ou fragmento.")
            try:
                port = parsed.port or 443
            except ValueError:
                raise ValueError("Porta da URL DoH inválida.") from None
            host = parsed.hostname
        if protocol == "dot" and not host:
            raise ValueError("DoT exige hostname para validar o certificado TLS.")
        key = (address, protocol, port, url if protocol == "doh" else host if protocol == "dot" else "")
        if key in seen:
            continue
        seen.add(key)
        validated.append({"id": f"r{len(validated)}", "name": str(r.get("name") or address)[:80],
                          "address": address, "protocol": protocol, "port": port,
                          "family": f"IPv{ipaddress.ip_address(address).version}",
                          "hostname": host, "url": url, "policy": str(r.get("policy", "Personalizado"))[:120]})
    if len(domains) * len(set(qtypes)) * rounds * len(validated) > 50000:
        raise ValueError("Limite de 50.000 consultas por teste. Reduza domínios, passagens ou servidores.")
    return {"domains": domains, "resolvers": validated, "rounds": rounds,
            "concurrency": concurrency, "timeout_ms": timeout, "seed": seed,
            "qtypes": list(dict.fromkeys(qtypes))}
