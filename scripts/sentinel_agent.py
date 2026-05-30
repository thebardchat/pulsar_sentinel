#!/usr/bin/env python3
"""Pulsar Sentinel Node Agent — zero-dependency security watcher.

Runs on any cluster node. Reports heartbeats + auth events to the Pi.
No venv required — stdlib only (Python 3.6+).

Config via env vars:
  SENTINEL_URL       - Pi server, e.g. http://shanebrain:8250
  SENTINEL_KEY       - service key (default: shanebrain-internal-2026)
  SENTINEL_NODE_ID   - this node's ID (default: hostname)
  SENTINEL_INTERVAL  - heartbeat interval seconds (default: 60)
"""
import json
import os
import platform
import re
import socket
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_urls_env = os.environ.get("SENTINEL_URLS", "").strip()
if _urls_env:
    SENTINEL_URLS = [u.strip().rstrip("/") for u in _urls_env.split(",") if u.strip()]
else:
    SENTINEL_URLS = [os.environ.get("SENTINEL_URL", "http://shanebrain:8250").rstrip("/")]
SENTINEL_URL = SENTINEL_URLS[0]  # backward-compat alias for log lines
SENTINEL_KEY = os.environ.get("SENTINEL_KEY", "shanebrain-internal-2026")
NODE_ID      = os.environ.get("SENTINEL_NODE_ID", socket.gethostname())
INTERVAL     = int(os.environ.get("SENTINEL_INTERVAL", "60"))

AUTH_LOG_PATHS = [
    "/var/log/auth.log",      # Debian/Ubuntu
    "/var/log/secure",        # RHEL/CentOS/Fedora
    "/var/log/messages",      # fallback
]

# Track auth log position
_log_offset: dict[str, int] = {}
_events_since_last = 0


def _post(path: str, data: dict) -> bool:
    """Multi-post to all configured sentinels. Returns True if ANY succeed."""
    body = json.dumps(data).encode()
    any_ok = False
    for url in SENTINEL_URLS:
        full = f"{url}/api/v1{path}"
        req = urllib.request.Request(
            full, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {SENTINEL_KEY}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                if r.status == 200:
                    any_ok = True
        except Exception as e:
            print(f"[agent] POST {path} to {url} failed: {e}", file=sys.stderr)
    return any_ok


def _cpu_pct() -> float:
    """Read CPU usage from /proc/stat (two snapshots 0.5s apart)."""
    def _read():
        try:
            line = Path("/proc/stat").read_text().splitlines()[0]
            vals = list(map(int, line.split()[1:]))
            idle = vals[3]
            total = sum(vals)
            return idle, total
        except Exception:
            return 0, 1
    i1, t1 = _read()
    time.sleep(0.5)
    i2, t2 = _read()
    dt = t2 - t1
    if dt == 0:
        return 0.0
    return round(100.0 * (1.0 - (i2 - i1) / dt), 1)


def _ram_pct() -> float:
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            info[k.strip()] = int(v.split()[0])
        total = info.get("MemTotal", 1)
        avail = info.get("MemAvailable", total)
        return round(100.0 * (total - avail) / total, 1)
    except Exception:
        return 0.0


def _disk_pct() -> float:
    try:
        import shutil
        u = shutil.disk_usage("/")
        return round(100.0 * u.used / u.total, 1)
    except Exception:
        return 0.0


def _uptime_days() -> float:
    try:
        up_s = float(Path("/proc/uptime").read_text().split()[0])
        return round(up_s / 86400, 2)
    except Exception:
        return 0.0


def _my_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return ""


def _find_auth_log() -> Path | None:
    for p in AUTH_LOG_PATHS:
        if Path(p).exists():
            return Path(p)
    return None


def _read_new_lines(log_path: Path) -> list[str]:
    """Read lines added since last check."""
    global _log_offset
    key = str(log_path)
    try:
        size = log_path.stat().st_size
        offset = _log_offset.get(key, size)  # start from end on first run
        if size < offset:
            offset = 0  # log was rotated
        _log_offset[key] = size
        if offset >= size:
            return []
        with log_path.open("rb") as f:
            f.seek(offset)
            raw = f.read(size - offset)
        _log_offset[key] = size
        return raw.decode(errors="replace").splitlines()
    except Exception:
        return []


_AUTH_FAIL_RE = re.compile(
    r"(Failed password|Invalid user|authentication failure|FAILED LOGIN)",
    re.IGNORECASE,
)
_IP_RE = re.compile(r"from (\d+\.\d+\.\d+\.\d+)")
_USER_RE = re.compile(r"(?:for|user) (\S+)")


def _check_auth_log() -> list[dict]:
    """Scan new auth log lines for threat events."""
    log = _find_auth_log()
    if not log:
        return []
    events = []
    for line in _read_new_lines(log):
        if _AUTH_FAIL_RE.search(line):
            ip_m = _IP_RE.search(line)
            usr_m = _USER_RE.search(line)
            events.append({
                "event_type": "auth_failure",
                "source_ip": ip_m.group(1) if ip_m else "",
                "username": usr_m.group(1) if usr_m else "",
                "raw": line[:300],
                "threat_level": 2,
            })
    return events


def _threat_level(events: list[dict]) -> int:
    if not events:
        return 1
    return min(5, max(e["threat_level"] for e in events))


def run():
    global _events_since_last
    ip = _my_ip()
    print(f"[agent] {NODE_ID} starting — multi-posting to {len(SENTINEL_URLS)} sentinels: {SENTINEL_URLS}", flush=True)

    # Initialize log offsets (skip historical content on first run)
    log = _find_auth_log()
    if log:
        try:
            _log_offset[str(log)] = log.stat().st_size
        except Exception:
            pass

    while True:
        try:
            new_events = _check_auth_log()
            _events_since_last += len(new_events)

            for ev in new_events:
                _post(f"/agents/{NODE_ID}/event", ev)

            level = _threat_level(new_events)
            hb = {
                "hostname": NODE_ID,
                "ip": ip,
                "cpu_pct": _cpu_pct(),
                "ram_pct": _ram_pct(),
                "disk_pct": _disk_pct(),
                "uptime_days": _uptime_days(),
                "events_since_last": _events_since_last,
                "threat_level": level,
                "platform": platform.system().lower(),
            }
            ok = _post(f"/agents/{NODE_ID}/heartbeat", hb)
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            status = "ok" if ok else "FAIL"
            print(
                f"[agent] {ts} heartbeat {status} | "
                f"cpu={hb['cpu_pct']}% ram={hb['ram_pct']}% "
                f"disk={hb['disk_pct']}% events={_events_since_last}",
                flush=True,
            )
            _events_since_last = 0

        except KeyboardInterrupt:
            print("[agent] stopped", flush=True)
            break
        except Exception as e:
            print(f"[agent] error: {e}", file=sys.stderr, flush=True)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
