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
    """Real Post-quantum Threat Score from PTSCalculator."""
    pts_calc = getattr(request.app.state, "pts_calculator", None)
    if pts_calc is None:
        return {"ok": False, "pts": None, "error": "PTSCalculator not initialized"}
    import asyncio
    score = None; used = None
    for name in ["get_current_score", "calculate", "current_pts", "get_score", "score", "compute"]:
        m = getattr(pts_calc, name, None)
        if callable(m):
            try:
                r = await m() if asyncio.iscoroutinefunction(m) else m()
                if isinstance(r, (int, float)): score = float(r)
                elif isinstance(r, dict) and "score" in r: score = float(r["score"])
                elif hasattr(r, "score"): score = float(r.score)
                used = name; break
            except Exception: continue
    if score is None:
        return {"ok": False, "pts": None, "error": "no compatible method",
                "available": [n for n in dir(pts_calc) if not n.startswith("_")][:20]}
    return {"ok": True, "pts": round(score, 1), "method": used, "timestamp": time.time()}


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
