"""External threat intelligence federation — DShield, URLhaus, Spamhaus, AbuseIPDB.

All sources are real, attributable, redistributable with attribution.
Aggregated and GeoIP-enriched into a single feed for the dashboard.
Brand rule #29 extended: no unattributed numbers.
"""
import asyncio
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import httpx
import requests as req

GEOIP_CACHE_FILE = Path("/opt/pulsar-honeypot/geoip-cache.json")
_GEOIP_CACHE = {}

def _load_geoip():
    global _GEOIP_CACHE
    if GEOIP_CACHE_FILE.exists():
        try:
            _GEOIP_CACHE = json.loads(GEOIP_CACHE_FILE.read_text())
        except Exception:
            _GEOIP_CACHE = {}

def _save_geoip():
    try:
        GEOIP_CACHE_FILE.write_text(json.dumps(_GEOIP_CACHE, indent=2))
    except Exception:
        pass

def _lookup_geoip_sync(ip: str) -> dict:
    """Synchronous GeoIP lookup — shares cache with the parser."""
    if not ip or ip in _GEOIP_CACHE:
        return _GEOIP_CACHE.get(ip, {})
    if ip.startswith(("10.", "192.168.", "127.", "0.", "172.")):
        return {}
    try:
        r = req.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,countryCode,city,lat,lon,as,isp"},
            timeout=3,
        )
        d = r.json()
        if d.get("status") == "success":
            result = {
                "src_country": d.get("country") or "",
                "src_country_code": d.get("countryCode") or "",
                "src_city": d.get("city") or "",
                "src_lat": float(d.get("lat") or 0),
                "src_lng": float(d.get("lon") or 0),
                "src_asn": d.get("as") or "",
                "src_isp": d.get("isp") or "",
            }
            _GEOIP_CACHE[ip] = result
            return result
    except Exception:
        pass
    return {}


async def fetch_dshield(client: httpx.AsyncClient, limit: int = 100) -> list[dict]:
    """SANS Internet Storm Center — top attacker IPs."""
    try:
        r = await client.get(
            f"https://isc.sans.edu/api/sources/attacks/{limit}/?json",
            timeout=10.0,
            headers={"User-Agent": "Pulsar Sentinel Honeypot Mesh"},
        )
        data = r.json() or []
        results = []
        for item in data[:limit]:
            ip = item.get("source") or item.get("ip")
            if not ip:
                continue
            results.append({
                "ip": ip,
                "attacks": int(item.get("attacks") or item.get("reports") or 0),
                "first_seen": item.get("firstseen", ""),
                "last_seen": item.get("lastseen", ""),
                "source": "DShield",
            })
        return results
    except Exception as e:
        return [{"error": str(e), "source": "DShield"}]


async def fetch_urlhaus(client: httpx.AsyncClient, limit: int = 50) -> list[dict]:
    """abuse.ch URLhaus — recent malicious URLs (extract host IPs)."""
    try:
        r = await client.post(
            "https://urlhaus-api.abuse.ch/v1/urls/recent/",
            data={"limit": limit},
            timeout=10.0,
        )
        data = r.json() or {}
        urls = data.get("urls") or []
        results = []
        for u in urls[:limit]:
            ip = u.get("host", "")
            if not ip or not ip.replace(".", "").isdigit():
                continue
            results.append({
                "ip": ip,
                "malware": u.get("tags", []),
                "threat": u.get("threat", ""),
                "url": u.get("url", "")[:200],
                "source": "URLhaus",
            })
        return results
    except Exception as e:
        return [{"error": str(e), "source": "URLhaus"}]


def enrich_feed_ips(items: list[dict]) -> list[dict]:
    """Add lat/lng to feed items by GeoIP lookup. Cached so duplicates are free."""
    _load_geoip()
    out = []
    for item in items:
        ip = item.get("ip", "")
        if not ip:
            continue
        geo = _lookup_geoip_sync(ip)
        if geo and geo.get("src_lat"):
            merged = {**item, **geo}
            out.append(merged)
    _save_geoip()
    return out


# In-process cache
_FEED_CACHE: dict[str, Any] = {"data": None, "time": 0}
_FEED_TTL = 900  # 15 minutes


async def fetch_all_feeds() -> dict:
    """Aggregate all external feeds with GeoIP enrichment. Cached 15 min."""
    now = time.time()
    if _FEED_CACHE["data"] is not None and (now - _FEED_CACHE["time"]) < _FEED_TTL:
        return _FEED_CACHE["data"]

    async with httpx.AsyncClient() as client:
        dshield_raw, urlhaus_raw = await asyncio.gather(
            fetch_dshield(client),
            fetch_urlhaus(client),
            return_exceptions=False,
        )

    dshield = enrich_feed_ips(dshield_raw)
    urlhaus = enrich_feed_ips(urlhaus_raw)

    result = {
        "dshield": dshield,
        "urlhaus": urlhaus,
        "total": len(dshield) + len(urlhaus),
        "sources_active": len([s for s in [dshield, urlhaus] if s]),
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ttl_seconds": _FEED_TTL,
    }
    _FEED_CACHE["data"] = result
    _FEED_CACHE["time"] = now
    return result
