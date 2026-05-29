"""Sentinel Agent ingestion endpoints — heartbeats and security events from cluster nodes."""
import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from config.logging import get_logger

logger = get_logger("agents")
agent_router = APIRouter(prefix="/agents", tags=["agents"])

SERVICE_KEY = os.environ.get("PULSAR_SERVICE_KEY", "shanebrain-internal-2026")

# In-memory node registry — {node_id: {...}}
_nodes: dict[str, dict[str, Any]] = {}
# In-memory recent events — capped at 200
_events: list[dict[str, Any]] = []
_MAX_EVENTS = 200


def _auth(authorization: str | None) -> None:
    if not authorization or authorization.replace("Bearer ", "") != SERVICE_KEY:
        raise HTTPException(status_code=401, detail="invalid service key")


class HeartbeatPayload(BaseModel):
    hostname: str
    ip: str = ""
    cpu_pct: float = 0.0
    ram_pct: float = 0.0
    disk_pct: float = 0.0
    uptime_days: float = 0.0
    events_since_last: int = 0
    threat_level: int = 1
    platform: str = "linux"


class EventPayload(BaseModel):
    event_type: str
    source_ip: str = ""
    username: str = ""
    count: int = 1
    raw: str = ""
    threat_level: int = 2


@agent_router.post("/{node_id}/heartbeat")
async def heartbeat(
    node_id: str,
    payload: HeartbeatPayload,
    authorization: str | None = Header(default=None),
):
    _auth(authorization)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _nodes[node_id] = {
        "node_id": node_id,
        "hostname": payload.hostname,
        "ip": payload.ip,
        "cpu_pct": payload.cpu_pct,
        "ram_pct": payload.ram_pct,
        "disk_pct": payload.disk_pct,
        "uptime_days": round(payload.uptime_days, 1),
        "threat_level": payload.threat_level,
        "platform": payload.platform,
        "last_seen": now,
        "last_seen_ts": time.time(),
        "events_since_last": payload.events_since_last,
    }
    logger.info("agent_heartbeat", node_id=node_id, threat_level=payload.threat_level)
    return {"ok": True, "node_id": node_id, "received_at": now}


@agent_router.post("/{node_id}/event")
async def report_event(
    node_id: str,
    payload: EventPayload,
    authorization: str | None = Header(default=None),
):
    _auth(authorization)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ev = {
        "node_id": node_id,
        "event_type": payload.event_type,
        "source_ip": payload.source_ip,
        "username": payload.username,
        "count": payload.count,
        "raw": payload.raw[:500],
        "threat_level": payload.threat_level,
        "timestamp": now,
    }
    _events.append(ev)
    if len(_events) > _MAX_EVENTS:
        _events.pop(0)
    # Bump node threat level if this event is higher
    if node_id in _nodes and payload.threat_level > _nodes[node_id].get("threat_level", 1):
        _nodes[node_id]["threat_level"] = payload.threat_level
    logger.info("agent_event", node_id=node_id, event_type=payload.event_type,
                threat_level=payload.threat_level)
    return {"ok": True, "event_type": payload.event_type, "received_at": now}


@agent_router.get("/status")
async def nodes_status(authorization: str | None = Header(default=None)):
    _auth(authorization)
    now_ts = time.time()
    nodes = []
    for n in _nodes.values():
        age_s = now_ts - n.get("last_seen_ts", 0)
        if age_s < 90:
            status = "online"
        elif age_s < 300:
            status = "stale"
        else:
            status = "offline"
        nodes.append({**n, "status": status, "age_seconds": int(age_s)})
    nodes.sort(key=lambda x: x.get("last_seen_ts", 0), reverse=True)
    return {
        "nodes": nodes,
        "total": len(nodes),
        "online": sum(1 for n in nodes if n["status"] == "online"),
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@agent_router.get("/events")
async def recent_events(
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    _auth(authorization)
    safe = max(1, min(limit, 200))
    return {
        "events": list(reversed(_events))[:safe],
        "total": len(_events),
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
