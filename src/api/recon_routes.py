"""Recon dashboard routes — Cloudflare Radar proxy + recon UI surface.

Provides /api/v1/recon/radar/{panel} that proxies the 4 main Cloudflare Radar
endpoints with the server-side CLOUDFLARE_API_TOKEN. Responses are cached in
memory for 60 seconds per panel to stay well under Cloudflare's rate limits.

The Recon dashboard JS fetches from /api/v1/recon/radar/ddos-l3 (etc).
"""
import time
from typing import Any
import httpx
from fastapi import APIRouter, HTTPException, Request
from config.settings import get_settings
from config.logging import get_logger

logger = get_logger("recon")
recon_router = APIRouter(prefix="/recon", tags=["recon"])

RADAR_ENDPOINTS = {
    "ddos-l3":   "/radar/attacks/layer3/summary/VECTOR",
    "ddos-l7":   "/radar/attacks/layer7/summary/HTTP_METHOD",
    "outages":   "/radar/annotations/outages?limit=10",
    "bgp":       "/radar/bgp/hijacks/events?minConfidence=8&per_page=10&sortBy=TIME&sortOrder=DESC",
}

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 60

@recon_router.get("/health")
async def health():
    settings = get_settings()
    return {
        "ok": True,
        "panels": list(RADAR_ENDPOINTS.keys()),
        "token_configured": bool(settings.cloudflare_api_token),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }

@recon_router.get("/pts")
async def get_pts(request: Request):
    """System-level Post-quantum Threat Score from PTSCalculator.
    PTSCalculator is violation-based (higher = more dangerous), so we invert
    to a 0-100 security health score (higher = safer) for the recon dashboard."""
    pts_calc = getattr(request.app.state, "pts_calculator", None)
    if pts_calc is None:
        return {"ok": False, "pts": None, "error": "PTSCalculator not initialized"}
    try:
        result = pts_calc.calculate_pts("__system__")
        threat = float(getattr(result, "total_score", 0))
        pts = max(0, round(100 - threat, 1))
        return {"ok": True, "pts": pts, "threat_score": threat,
                "tier": str(getattr(result, "tier", "UNKNOWN")), "timestamp": time.time()}
    except Exception as e:
        return {"ok": False, "pts": None, "error": str(e)}


@recon_router.get("/squad/{wallet}")
async def get_squad(wallet: str):
    """Return squad (referral network) stats for a wallet.
    MOCK for now — wires to AccessController referrals in follow-up."""
    if not wallet.startswith("0x") or len(wallet) < 6:
        return {"ok": False, "error": "invalid wallet format"}
    # TODO: query AccessController for real referral count
    count = 0
    pts_boost = min(50, count)  # 1% per recruit, cap 50%
    milestones = [
        {"at": 5,  "reward": "+5% PTS BOOST", "achieved": count >= 5},
        {"at": 10, "reward": "1 MONTH FREE",  "achieved": count >= 10},
        {"at": 25, "reward": "LIFETIME SENTINEL CORE", "achieved": count >= 25},
    ]
    next_m = next((m for m in milestones if not m["achieved"]), None)
    invite_url = f"https://sentinel.shanebrain.cloud/recon?ref={wallet}"
    return {
        "ok": True,
        "wallet": wallet,
        "count": count,
        "pts_boost_pct": pts_boost,
        "next_milestone": next_m,
        "milestones": milestones,
        "invite_url": invite_url,
    }


@recon_router.post("/squad/join")
async def squad_join(payload: dict):
    """Record a squad-join when a new user signs up via ?ref=0xINVITER.
    MOCK for now — wires to AccessController in follow-up."""
    inviter = payload.get("inviter_wallet", "")
    invitee = payload.get("invitee_wallet", "")
    if not inviter or not invitee:
        return {"ok": False, "error": "missing inviter_wallet or invitee_wallet"}
    if not inviter.startswith("0x") or not invitee.startswith("0x"):
        return {"ok": False, "error": "invalid wallet format"}
    if inviter.lower() == invitee.lower():
        return {"ok": False, "error": "cannot recruit yourself"}
    # TODO: persist via AccessController + emit blockchain audit
    logger.info("squad_join_recorded", inviter=inviter, invitee=invitee)
    return {"ok": True, "inviter": inviter, "invitee": invitee, "recorded": True}


@recon_router.get("/radar/{panel}")
async def radar_panel(panel: str):
    if panel not in RADAR_ENDPOINTS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown panel. Available: {list(RADAR_ENDPOINTS.keys())}",
        )
    now = time.time()
    if panel in _cache:
        ts, data = _cache[panel]
        if now - ts < CACHE_TTL_SECONDS:
            return {
                "ok": True, "panel": panel, "endpoint": RADAR_ENDPOINTS[panel],
                "cached": True, "age_seconds": round(now - ts, 1), "data": data,
            }
    settings = get_settings()
    if not settings.cloudflare_api_token:
        raise HTTPException(
            status_code=503,
            detail="CLOUDFLARE_API_TOKEN not configured on server",
        )
    url = "https://api.cloudflare.com/client/v4" + RADAR_ENDPOINTS[panel]
    headers = {
        "Authorization": f"Bearer {settings.cloudflare_api_token}",
        "Accept": "application/json",
        "User-Agent": "pulsar-sentinel-recon/1.0",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("radar_upstream_error", panel=panel, status=e.response.status_code)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Cloudflare Radar HTTP {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error("radar_request_error", panel=panel, error=str(e))
        raise HTTPException(status_code=502, detail=f"Request failed: {e}")
    _cache[panel] = (now, data)
    return {
        "ok": True, "panel": panel, "endpoint": RADAR_ENDPOINTS[panel],
        "cached": False, "data": data,
    }


# === HONEYPOT MESH ENDPOINTS (L.3 Phase 3a, 2026-05-28) ===
from datetime import datetime, timezone

HONEYPOT_WEAVIATE_URL = "http://100.100.90.66:8080"

HONEYPOT_SENSORS = [
    {
        "uuid": "7d0d835e-58e3-11f1-a327-6228bf6b930a",
        "location": "NYC1",
        "provider": "DigitalOcean",
        "status": "online",
    },
]


@recon_router.get("/honeypot/recent")
async def honeypot_recent(limit: int = 50):
    """Latest attack events from the Pulsar honeypot mesh."""
    safe_limit = max(1, min(limit, 200))
    query = (
        '{ Get { HoneypotEvent(limit: ' + str(safe_limit) + ') '
        '{ src_ip username password command event_id timestamp sensor_location src_country src_country_code src_city src_region src_lat src_lng src_isp src_asn } } '
        'Aggregate { HoneypotEvent { meta { count } } } }'
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.post(f"{HONEYPOT_WEAVIATE_URL}/v1/graphql", json={"query": query})
            data = (r.json() or {}).get("data", {}) or {}
            events = (data.get("Get") or {}).get("HoneypotEvent") or []
            agg = (data.get("Aggregate") or {}).get("HoneypotEvent") or [{}]
            total = (agg[0].get("meta") or {}).get("count", 0)
            return {
                "total_events": total,
                "events": events,
                "sensors": HONEYPOT_SENSORS,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        except Exception as e:
            logger.error(f"honeypot_recent error: {e}")
            return {"error": str(e), "total_events": 0, "events": [], "sensors": HONEYPOT_SENSORS}


@recon_router.get("/honeypot/stats")
async def honeypot_stats():
    """Aggregated honeypot stats — totals + top usernames."""
    total_q = '{ Aggregate { HoneypotEvent { meta { count } } } }'
    users_q = '{ Aggregate { HoneypotEvent(groupBy: "username") { groupedBy { value } meta { count } } } }'
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            q24h = ('{ Aggregate { HoneypotEvent(where: {path:["timestamp"], operator:GreaterThan, valueDate:"' + cutoff + '"}) { meta { count } } } }')
            r1 = await client.post(f"{HONEYPOT_WEAVIATE_URL}/v1/graphql", json={"query": total_q})
            r2 = await client.post(f"{HONEYPOT_WEAVIATE_URL}/v1/graphql", json={"query": users_q})
            r3 = await client.post(f"{HONEYPOT_WEAVIATE_URL}/v1/graphql", json={"query": q24h})
            agg = ((r1.json() or {}).get("data", {}).get("Aggregate", {}).get("HoneypotEvent") or [{}])
            total = (agg[0].get("meta") or {}).get("count", 0)
            agg24 = ((r3.json() or {}).get("data", {}).get("Aggregate", {}).get("HoneypotEvent") or [{}])
            last_24h = (agg24[0].get("meta") or {}).get("count", 0)
            users = (r2.json() or {}).get("data", {}).get("Aggregate", {}).get("HoneypotEvent") or []
            top = sorted(users, key=lambda u: (u.get("meta") or {}).get("count", 0), reverse=True)[:10]
            return {
                "total_attacks": total,
                "last_24h": last_24h,
                "top_usernames": [
                    {"username": (u.get("groupedBy") or {}).get("value", ""),
                     "count": (u.get("meta") or {}).get("count", 0)}
                    for u in top
                ],
                "active_sensors": len([s for s in HONEYPOT_SENSORS if s["status"] == "online"]),
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        except Exception as e:
            logger.error(f"honeypot_stats error: {e}")
            return {"error": str(e), "total_attacks": 0, "top_usernames": [], "active_sensors": 0}
# === END HONEYPOT ENDPOINTS ===



# === FEDERATED THREAT FEEDS (Task #51 — DShield + URLhaus + ...) ===
from api.threat_feeds import fetch_all_feeds

@recon_router.get("/feeds/external")
async def feeds_external():
    """Aggregated external threat intelligence — DShield, URLhaus.
    All sources real, attributable. Cached 15 min server-side."""
    try:
        return await fetch_all_feeds()
    except Exception as e:
        logger.error(f"feeds/external error: {e}")
        return {"error": str(e), "dshield": [], "urlhaus": [], "total": 0}
# === END FEDERATED FEEDS ===


# === SENTINEL MESH (agent node status for recon dashboard) ===
@recon_router.get("/mesh")
async def mesh_status():
    """Public endpoint — returns cluster node status for recon dashboard.
    Read-only: no secrets exposed, just hostnames and health metrics."""
    import time as _time
    from api.agent_routes import _nodes, _events
    now_ts = _time.time()
    nodes = []
    for n in _nodes.values():
        age_s = now_ts - n.get("last_seen_ts", 0)
        status = "online" if age_s < 90 else ("stale" if age_s < 300 else "offline")
        nodes.append({
            "node_id":      n["node_id"],
            "hostname":     n["hostname"],
            "cpu_pct":      n.get("cpu_pct", 0),
            "ram_pct":      n.get("ram_pct", 0),
            "disk_pct":     n.get("disk_pct", 0),
            "uptime_days":  n.get("uptime_days", 0),
            "threat_level": n.get("threat_level", 1),
            "last_seen":    n.get("last_seen", ""),
            "status":       status,
        })
    nodes.sort(key=lambda x: x["node_id"])
    recent = list(reversed(_events))[:10]
    return {
        "nodes": nodes,
        "total": len(nodes),
        "online": sum(1 for n in nodes if n["status"] == "online"),
        "recent_events": recent,
        "fetched_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
    }
# === END SENTINEL MESH ===

@recon_router.get("/pi-stats")
async def pi_stats():
    """Pi system stats — temp and uptime for the health row."""
    import pathlib, datetime as dt
    temp_f = None
    try:
        raw = pathlib.Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        temp_c = int(raw) / 1000.0
        temp_f = round(temp_c * 9 / 5 + 32, 1)
    except Exception:
        pass
    uptime_days = None
    try:
        uptime_s = float(pathlib.Path("/proc/uptime").read_text().split()[0])
        uptime_days = round(uptime_s / 86400, 1)
    except Exception:
        pass
    return {"temp_f": temp_f, "uptime_days": uptime_days}
