#!/usr/bin/env python3
"""
mindmap_server.py — ShaneBrain Universal Mindmap Service.

A single FastAPI app on the Pi (port 8600) that serves every project's mindmap
under one URL. Tailscale-accessible from any node Shane owns. No file copying.
No "is this the latest?" friction. Open the bookmark and see the live state
from pulsar00100, gulfshores, neworleans, iPhone, or anywhere on the mesh.

Endpoints
---------
GET  /                       Multi-project mindmap UI (HTML, mobile-friendly)
GET  /api/state              Full state JSON (all projects)
GET  /api/state/{project}    One project's slice
POST /api/delta              Apply a delta (called by update_mindmap.py)
GET  /api/projects           List of known project keys
GET  /api/health             Liveness probe
GET  /static/...             Optional static assets (favicon, screenshots)

State file
----------
/mnt/shanebrain-raid/shanebrain-core/mindmap-state.json

Format:
{
  "projects": {
    "yourlegacy": {
      "title": "YourLegacy",
      "subtitle": "Non-custodial Digital Trust · Q3 2026",
      "phase-1": [ { node }, ... ],
      "phase-2": [ ... ],
      "open-removed": [ ... ],
      "timeline": [ ... ]
    },
    "pulsar-sentinel": { ... },
    "srm-dispatch": { ... },
    "claim-cruncher": { ... },
    ...
  },
  "last_updated": "ISO timestamp",
  "processed_deltas": [ ... ]
}

Deploy
------
1. Copy this file: /mnt/shanebrain-raid/shanebrain-core/scripts/mindmap_server.py
2. Install deps:  pip3 install fastapi uvicorn[standard]
3. systemd unit:  scripts/mindmap-server.service (in this repo)
4. Open the bookmark from any device: http://100.67.120.6:8600

Bookmark on iPhone Safari for one-tap access.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from fastapi import Cookie, Depends, FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    import uvicorn
except ImportError:
    print("Install deps: pip3 install fastapi 'uvicorn[standard]' bcrypt", file=sys.stderr)
    raise

# Local module (lives next to this file)
sys.path.insert(0, str(Path(__file__).parent))
from mindmap_auth import Auth, require_login  # noqa: E402

# State path — defaults to NAS mount when available, falls back to local.
STATE_PATH = Path(
    os.environ.get(
        "MINDMAP_STATE_PATH",
        "/mnt/nas/shanebrain/mindmap-state.json"
        if Path("/mnt/nas/shanebrain").exists()
        else "/mnt/shanebrain-raid/shanebrain-core/mindmap-state.json",
    )
)
AUDIT_LOG_PATH = Path(
    os.environ.get(
        "MINDMAP_AUDIT_LOG",
        str(STATE_PATH.parent / "mindmap-audit.log"),
    )
)
PORT = int(os.environ.get("MINDMAP_PORT", "8600"))

# Auth — enabled when USERS_FILE env var is set (NAS path recommended).
auth = Auth(
    users_file=os.environ.get(
        "USERS_FILE",
        "/mnt/nas/shanebrain/users.json"
        if Path("/mnt/nas/shanebrain").exists()
        else None,
    ),
    sessions_file=os.environ.get(
        "SESSIONS_FILE",
        "/mnt/nas/shanebrain/sessions.json"
        if Path("/mnt/nas/shanebrain").exists()
        else None,
    ),
)

app = FastAPI(
    title="ShaneBrain Mindmap",
    description="Universal living mindmap across all projects. Tailscale + family multi-user.",
)


def audit(user: str, action: str, detail: str = "") -> None:
    """Append a line to the per-user audit log. Best-effort; never blocks."""
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = f"{datetime.now(timezone.utc).isoformat()}\t{user}\t{action}\t{detail}\n"
        with AUDIT_LOG_PATH.open("a") as f:
            f.write(line)
    except Exception:
        pass

# ── State persistence ──────────────────────────────────────────────────────


def empty_project(title: str, subtitle: str = "") -> dict[str, Any]:
    return {
        "title": title,
        "subtitle": subtitle,
        "phase-1": [],
        "phase-2": [],
        "open-removed": [],
        "timeline": [],
    }


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        # Seed with the projects we already have memory about.
        seed = {
            "projects": {
                "yourlegacy": empty_project(
                    "YourLegacy",
                    "Non-custodial Digital Trust · Q3 2026",
                ),
                "pulsar-sentinel": empty_project(
                    "Pulsar Sentinel",
                    "PQC + Q-Day countdown · LIVE since 2026-05-12",
                ),
                "srm-dispatch": empty_project(
                    "SRM Dispatch Manager",
                    "North Alabama · 14 triaxle drivers · daily rotation",
                ),
                "book-2": empty_project(
                    "Book 2: You Probably Think This Song",
                    "17 tracks · architecture locked · demo status",
                ),
                "claim-cruncher": empty_project(
                    "Claim Cruncher",
                    "Medical billing platform · Gavin building",
                ),
                "ai-trainer-max": empty_project(
                    "AI-Trainer-MAX",
                    "36-module local AI curriculum · 5 phases shipped",
                ),
                "halofinance": empty_project(
                    "HaloFinance",
                    "Private family financial dashboard · 31-bill SMS reminders",
                ),
                "mega-crew": empty_project(
                    "MEGA Crew",
                    "17 Docker bots · Arc gatekeeper · 24/7",
                ),
                "wrestling-facility": empty_project(
                    "Wrestling Facility",
                    "Hazel Green youth program · FreeCAD done",
                ),
            },
            "last_updated": None,
            "processed_deltas": [],
        }
        save_state(seed)
        return seed
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict[str, Any]) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def apply_delta_to_state(state: dict[str, Any], delta: dict[str, Any]) -> None:
    """Apply one MINDMAP_DELTA dict to the multi-project state in place."""
    project_key = delta.get("project", "yourlegacy")
    if project_key not in state["projects"]:
        state["projects"][project_key] = empty_project(
            delta.get("project_title", project_key.title()),
            delta.get("project_subtitle", ""),
        )
    project = state["projects"][project_key]

    for node in delta.get("added", []):
        branch = node.get("branch", "phase-1")
        if not any(n["title"] == node["title"] for n in project.get(branch, [])):
            project.setdefault(branch, []).append(node)

    for mod in delta.get("modified", []):
        title = mod["title"]
        branch = mod.get("branch", "phase-1")
        for node in project.get(branch, []):
            if node["title"] == title:
                node["status"] = "modified"
                node["prior"] = mod.get("prior", node.get("what", ""))
                node["now"] = mod.get("now", "")
                node["change_reason"] = mod.get("reason", "")
                node["change_commit"] = mod.get("commit", "")
                node["date_label"] = "CHANGED"
                break

    for rm in delta.get("removed", []):
        title = rm["title"]
        for branch in ("phase-1", "phase-2", "open-removed"):
            for node in project.get(branch, []):
                if node["title"] == title:
                    node["status"] = "removed"
                    node["date_cut"] = rm.get("date_cut")
                    node["why_removed"] = rm.get("why", "")
                    if branch != "open-removed":
                        project[branch].remove(node)
                        project.setdefault("open-removed", []).append(node)
                    break

    for tl in delta.get("timeline", []):
        if not any(
            t["date"] == tl["date"] and t["label"] == tl["label"]
            for t in project.get("timeline", [])
        ):
            project.setdefault("timeline", []).append(tl)


# ── API endpoints ──────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "shanebrain-mindmap",
        "port": PORT,
        "auth_enabled": auth.enabled,
        "state_path": str(STATE_PATH),
    }


# ── Auth endpoints ─────────────────────────────────────────────────────────


@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    token = auth.login(username, password)
    if not token:
        audit(username or "anon", "login.fail", "bad credentials")
        raise HTTPException(status_code=401, detail="invalid credentials")
    audit(username, "login.ok", "")
    resp = JSONResponse(
        {
            "ok": True,
            "user": username,
            "display_name": auth.whoami(token)["display_name"],
            "role": auth.whoami(token)["role"],
        }
    )
    resp.set_cookie(
        "mm_session",
        token,
        max_age=60 * 60 * 24 * 30,  # 30 days
        httponly=True,
        samesite="strict",
        secure=False,  # we're on Tailscale, not public HTTPS by default
    )
    return resp


@app.post("/api/logout")
async def logout(mm_session: str | None = Cookie(default=None)):
    if mm_session:
        sess = auth.whoami(mm_session)
        if sess:
            audit(sess["user"], "logout", "")
        auth.logout(mm_session)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("mm_session")
    return resp


@app.get("/api/whoami")
async def whoami(mm_session: str | None = Cookie(default=None)):
    sess = auth.whoami(mm_session)
    if not sess:
        return {"logged_in": False, "auth_enabled": auth.enabled}
    return {
        "logged_in": True,
        "auth_enabled": auth.enabled,
        "user": sess["user"],
        "display_name": sess["display_name"],
        "role": sess["role"],
    }


# ── Project + state endpoints (require login when auth enabled) ───────────


@app.get("/api/projects")
async def list_projects(user=Depends(require_login(auth))):
    state = load_state()
    audit(user["user"], "projects.list", "")
    return {
        key: {
            "title": proj.get("title"),
            "subtitle": proj.get("subtitle"),
            "counts": {
                "phase-1": len(proj.get("phase-1", [])),
                "phase-2": len(proj.get("phase-2", [])),
                "open-removed": len(proj.get("open-removed", [])),
            },
        }
        for key, proj in state.get("projects", {}).items()
    }


@app.get("/api/state")
async def get_state(user=Depends(require_login(auth))):
    audit(user["user"], "state.read", "")
    return load_state()


@app.get("/api/state/{project_key}")
async def get_project(project_key: str, user=Depends(require_login(auth))):
    state = load_state()
    if project_key not in state.get("projects", {}):
        raise HTTPException(status_code=404, detail=f"Unknown project: {project_key}")
    audit(user["user"], "project.read", project_key)
    return state["projects"][project_key]


@app.post("/api/delta")
async def post_delta(
    request: Request,
    user=Depends(require_login(auth, min_role="family")),
):
    delta = await request.json()
    state = load_state()
    apply_delta_to_state(state, delta)
    save_state(state)
    audit(
        user["user"],
        "delta.post",
        f"project={delta.get('project', 'yourlegacy')} "
        f"+{len(delta.get('added', []))} ~{len(delta.get('modified', []))} "
        f"-{len(delta.get('removed', []))}",
    )
    return {
        "ok": True,
        "project": delta.get("project", "yourlegacy"),
        "added": len(delta.get("added", [])),
        "modified": len(delta.get("modified", [])),
        "removed": len(delta.get("removed", [])),
    }


# ── HTML UI ────────────────────────────────────────────────────────────────


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(content=LOGIN_HTML)


@app.get("/", response_class=HTMLResponse)
async def root(mm_session: str | None = Cookie(default=None)):
    if auth.enabled and not auth.whoami(mm_session):
        return RedirectResponse("/login", status_code=302)
    return HTMLResponse(content=UI_HTML)


LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>ShaneBrain Mindmap — Sign In</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --void-dark: #0a0a12; --stellar-gray: #1a1a24; --node-gray: #14141e;
    --border-faint: #2a2a36; --text-primary: #f0f0f5; --text-secondary: #b0b0c0;
    --text-muted: #707080; --pulsar-magenta: #ff2b8f; --plasma-gold: #ffd700;
    --matrix-green: #00ff88; --alert-red: #ff3052;
    --font-mono: 'SF Mono', 'Consolas', monospace;
    --font-display: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; height: 100%; }
  body {
    background: radial-gradient(ellipse at top, #15151f 0%, var(--void-dark) 70%);
    color: var(--text-primary); font-family: var(--font-display);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 20px;
  }
  .card {
    max-width: 380px; width: 100%;
    background: var(--stellar-gray);
    border: 1px solid var(--border-faint);
    border-radius: 14px; padding: 28px 26px;
    box-shadow: 0 0 40px rgba(255, 43, 143, 0.15);
  }
  .eyebrow {
    font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--pulsar-magenta); margin-bottom: 8px;
  }
  h1 { margin: 0 0 18px; font-size: 1.4rem; }
  h1 .accent { color: var(--plasma-gold); }
  label {
    display: block; font-family: var(--font-mono); font-size: 0.7rem;
    letter-spacing: 0.15em; text-transform: uppercase; color: var(--text-muted);
    margin: 14px 0 6px;
  }
  input {
    width: 100%; padding: 10px 12px; background: var(--node-gray);
    border: 1px solid var(--border-faint); border-radius: 8px;
    color: var(--text-primary); font-family: var(--font-display); font-size: 0.95rem;
    outline: none; transition: border-color 0.15s;
  }
  input:focus { border-color: var(--pulsar-magenta); }
  button {
    width: 100%; margin-top: 20px; padding: 11px;
    background: var(--pulsar-magenta); color: white;
    border: none; border-radius: 8px; font-family: var(--font-display);
    font-size: 0.95rem; font-weight: 600; cursor: pointer;
    transition: opacity 0.15s; letter-spacing: 0.02em;
  }
  button:hover { opacity: 0.9; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .error {
    margin-top: 14px; padding: 8px 12px; color: var(--alert-red);
    font-size: 0.85rem; border: 1px solid var(--alert-red);
    background: rgba(255, 48, 82, 0.08); border-radius: 6px; display: none;
  }
  .error.show { display: block; }
  .hint {
    text-align: center; margin-top: 18px; color: var(--text-muted);
    font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.1em;
  }
</style>
</head><body>
<div class="card">
  <div class="eyebrow">ShaneBrain Mindmap</div>
  <h1>Family <span class="accent">Sign In</span></h1>
  <form id="f">
    <label>Username</label>
    <input id="u" autocomplete="username" autofocus required>
    <label>Password</label>
    <input id="p" type="password" autocomplete="current-password" required>
    <div class="error" id="err"></div>
    <button id="btn" type="submit">Sign in</button>
  </form>
  <p class="hint">Tailscale-only · Family use</p>
</div>
<script>
const f = document.getElementById('f');
const btn = document.getElementById('btn');
const err = document.getElementById('err');
f.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true; err.classList.remove('show');
  try {
    const r = await fetch('/api/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: document.getElementById('u').value,
        password: document.getElementById('p').value,
      })
    });
    if (r.ok) { location.href = '/'; }
    else {
      const j = await r.json().catch(() => ({}));
      err.textContent = j.detail || 'Sign-in failed';
      err.classList.add('show');
    }
  } catch (e) {
    err.textContent = 'Network error';
    err.classList.add('show');
  } finally { btn.disabled = false; }
});
</script>
</body></html>
"""


# Inline HTML — single-file, no external deps, mobile-friendly.
UI_HTML = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>ShaneBrain Mindmap — Universal</title>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=2">
<style>
  :root {
    --void-dark: #0a0a12;
    --stellar-gray: #1a1a24;
    --node-gray: #14141e;
    --border-faint: #2a2a36;
    --text-primary: #f0f0f5;
    --text-secondary: #b0b0c0;
    --text-muted: #707080;
    --pulsar-magenta: #ff2b8f;
    --plasma-gold: #ffd700;
    --matrix-green: #00ff88;
    --alert-red: #ff3052;
    --info-blue: #4ea1ff;
    --font-mono: 'SF Mono', 'Consolas', 'Monaco', monospace;
    --font-display: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: radial-gradient(ellipse at top, #15151f 0%, var(--void-dark) 70%);
    color: var(--text-primary);
    font-family: var(--font-display);
    line-height: 1.55;
    min-height: 100vh;
    padding-bottom: 60px;
    -webkit-font-smoothing: antialiased;
  }
  .container { max-width: 1400px; margin: 0 auto; padding: 24px 16px; }

  header.top { border-bottom: 1px solid var(--border-faint); padding-bottom: 18px; margin-bottom: 22px; }
  header.top .eyebrow { font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--pulsar-magenta); margin-bottom: 6px; }
  header.top h1 { font-size: 1.8rem; margin: 0 0 6px; }
  header.top h1 .accent { color: var(--plasma-gold); }
  header.top p { color: var(--text-secondary); font-size: 0.92rem; margin: 0; }
  header.top .meta { margin-top: 12px; font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); }

  /* Project tabs */
  .project-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px;
    background: var(--stellar-gray);
    border: 1px solid var(--border-faint);
    border-radius: 12px;
    margin-bottom: 22px;
    position: sticky;
    top: 0;
    z-index: 50;
  }
  .project-tab {
    padding: 8px 14px;
    background: var(--node-gray);
    border: 1px solid var(--border-faint);
    border-radius: 18px;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    cursor: pointer;
    transition: all 0.15s ease;
    text-decoration: none;
  }
  .project-tab:hover { border-color: var(--pulsar-magenta); color: var(--text-primary); }
  .project-tab.active {
    background: rgba(255, 43, 143, 0.18);
    border-color: var(--pulsar-magenta);
    color: var(--pulsar-magenta);
  }
  .project-tab .count {
    color: var(--text-muted);
    margin-left: 6px;
    font-size: 0.7rem;
  }

  /* Project header */
  .project-header {
    text-align: center;
    margin-bottom: 18px;
    padding: 16px 20px;
    background: linear-gradient(135deg, rgba(255, 43, 143, 0.10), rgba(255, 215, 0, 0.06));
    border: 1px solid var(--pulsar-magenta);
    border-radius: 12px;
  }
  .project-header h2 { margin: 0 0 4px; font-size: 1.4rem; }
  .project-header .subtitle { font-family: var(--font-mono); font-size: 0.78rem; color: var(--plasma-gold); letter-spacing: 0.1em; text-transform: uppercase; }

  /* Filter bar */
  .filter-bar { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 20px; padding: 10px 14px; background: var(--stellar-gray); border: 1px solid var(--border-faint); border-radius: 10px; }
  .filter-bar .filter-label { font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--text-muted); margin-right: 6px; align-self: center; }
  .filter-btn { padding: 5px 12px; background: var(--node-gray); border: 1px solid var(--border-faint); border-radius: 14px; color: var(--text-secondary); font-family: var(--font-mono); font-size: 0.72rem; cursor: pointer; }
  .filter-btn.active { background: rgba(255, 43, 143, 0.15); border-color: var(--pulsar-magenta); color: var(--pulsar-magenta); }

  /* Branch columns */
  .branches { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  @media (max-width: 900px) { .branches { grid-template-columns: 1fr; } }

  .branch-header { text-align: center; padding: 10px 14px; border-radius: 10px; border: 1px solid; margin-bottom: 12px; }
  .branch.phase-1 .branch-header { border-color: var(--matrix-green); background: rgba(0, 255, 136, 0.08); }
  .branch.phase-2 .branch-header { border-color: var(--info-blue); background: rgba(78, 161, 255, 0.08); }
  .branch.open-removed .branch-header { border-color: var(--alert-red); background: rgba(255, 48, 82, 0.08); }
  .branch-header h3 { margin: 0; font-size: 0.95rem; }
  .branch-header .subtitle { font-family: var(--font-mono); font-size: 0.65rem; letter-spacing: 0.15em; margin-top: 3px; text-transform: uppercase; }
  .branch.phase-1 .branch-header .subtitle { color: var(--matrix-green); }
  .branch.phase-2 .branch-header .subtitle { color: var(--info-blue); }
  .branch.open-removed .branch-header .subtitle { color: var(--alert-red); }

  /* Nodes */
  .node { background: var(--node-gray); border: 1px solid var(--border-faint); border-radius: 10px; padding: 11px 13px; margin-bottom: 10px; cursor: pointer; transition: all 0.15s ease; }
  .node:hover { border-color: var(--pulsar-magenta); transform: translateY(-1px); }
  .node-date { display: inline-block; font-family: var(--font-mono); font-size: 0.62rem; letter-spacing: 0.12em; color: var(--plasma-gold); background: rgba(255, 215, 0, 0.08); padding: 2px 7px; border-radius: 8px; margin-bottom: 5px; }
  .node-date.removed-date { color: var(--alert-red); background: rgba(255, 48, 82, 0.08); margin-left: 5px; }
  .node h4 { margin: 0; font-size: 0.88rem; user-select: none; line-height: 1.3; }
  .node-status { display: inline-block; margin-top: 5px; font-family: var(--font-mono); font-size: 0.6rem; letter-spacing: 0.12em; text-transform: uppercase; padding: 2px 7px; border-radius: 9px; border: 1px solid; }
  .node[data-status="built"] .node-status { color: var(--matrix-green); border-color: var(--matrix-green); }
  .node[data-status="planned"] .node-status { color: var(--info-blue); border-color: var(--info-blue); }
  .node[data-status="decision"] .node-status { color: var(--plasma-gold); border-color: var(--plasma-gold); }
  .node[data-status="modified"] .node-status { color: var(--alert-red); border-color: var(--alert-red); }
  .node[data-status="removed"] .node-status { color: var(--alert-red); border-color: var(--alert-red); }
  .node[data-status="removed"] h4 { text-decoration: line-through; text-decoration-color: var(--alert-red); color: var(--text-muted); }
  .node[data-status="removed"] { opacity: 0.78; }
  .node[data-status="modified"] { border-color: rgba(255, 48, 82, 0.5); }

  .node-details { max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
  .node.expanded .node-details { max-height: 1000px; margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-faint); }
  .node-details .what { color: var(--text-secondary); font-size: 0.82rem; margin: 0 0 6px; }
  .node-details .shane-note { background: rgba(255, 215, 0, 0.06); border-left: 3px solid var(--plasma-gold); padding: 6px 10px; margin: 6px 0; font-size: 0.78rem; font-style: italic; border-radius: 0 5px 5px 0; }
  .node-details .why-removed { background: rgba(255, 48, 82, 0.08); border-left: 3px solid var(--alert-red); padding: 6px 10px; margin: 6px 0; font-size: 0.78rem; border-radius: 0 5px 5px 0; }
  .node-details .why-removed::before { content: 'WHY CUT'; display: block; font-family: var(--font-mono); font-size: 0.58rem; letter-spacing: 0.15em; color: var(--alert-red); margin-bottom: 2px; font-weight: 600; }
  .node-details .prior { text-decoration: line-through; text-decoration-color: var(--alert-red); text-decoration-thickness: 2px; color: var(--text-muted); background: rgba(255, 48, 82, 0.04); padding: 6px 10px; border-left: 3px solid var(--alert-red); border-radius: 0 5px 5px 0; margin: 6px 0; font-size: 0.78rem; }
  .node-details .prior::before { content: 'PRIOR'; display: block; font-family: var(--font-mono); font-size: 0.58rem; letter-spacing: 0.15em; color: var(--alert-red); margin-bottom: 2px; text-decoration: none; font-weight: 600; }
  .node-details .now { background: rgba(0, 255, 136, 0.05); padding: 6px 10px; border-left: 3px solid var(--matrix-green); border-radius: 0 5px 5px 0; margin: 6px 0; font-size: 0.78rem; }
  .node-details .now::before { content: 'NOW'; display: block; font-family: var(--font-mono); font-size: 0.58rem; letter-spacing: 0.15em; color: var(--matrix-green); margin-bottom: 2px; font-weight: 600; }
  .node-details .tech { background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border-faint); border-radius: 5px; padding: 7px 10px; margin-top: 6px; font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-secondary); line-height: 1.6; }
  .node-details .tech strong { color: var(--matrix-green); }
  .node-details .choices ul { margin: 6px 0 0; padding-left: 16px; font-size: 0.78rem; color: var(--text-secondary); }
  .node.hidden { display: none; }

  /* Empty state */
  .empty {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.9rem;
  }
  .empty .hint { color: var(--text-secondary); font-size: 0.85rem; margin-top: 12px; }

  /* Status pill */
  .status-pill {
    position: fixed;
    bottom: 14px;
    right: 14px;
    background: rgba(0, 255, 136, 0.12);
    border: 1px solid var(--matrix-green);
    color: var(--matrix-green);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    padding: 5px 11px;
    border-radius: 12px;
    z-index: 100;
  }
  .status-pill.stale { background: rgba(255, 48, 82, 0.12); border-color: var(--alert-red); color: var(--alert-red); }
</style>
</head>
<body>
<div class="container">

<header class="top">
  <div class="eyebrow">ShaneBrain · Universal Mindmap · Live on Tailscale</div>
  <h1>Mindmap <span class="accent">Map</span></h1>
  <p>Every project. Every decision. Every date. Every cut. Click any node to expand.</p>
  <div class="meta" id="meta-line">Loading...</div>
</header>

<div class="project-tabs" id="project-tabs"></div>

<div id="project-area"></div>

</div>

<div class="status-pill" id="status">Loading…</div>

<script>
let STATE = null;
let CURRENT_PROJECT = null;
let CURRENT_FILTER = localStorage.getItem('mm_filter') || 'all';

async function loadState() {
  try {
    const r = await fetch('/api/state');
    if (!r.ok) throw new Error(r.status);
    STATE = await r.json();
    document.getElementById('status').className = 'status-pill';
    document.getElementById('status').textContent = '● live';
    document.getElementById('meta-line').textContent =
      'Updated ' + (STATE.last_updated || '—') + ' · ' +
      Object.keys(STATE.projects || {}).length + ' projects';
    return true;
  } catch (e) {
    document.getElementById('status').className = 'status-pill stale';
    document.getElementById('status').textContent = '● offline';
    return false;
  }
}

function renderTabs() {
  const tabs = document.getElementById('project-tabs');
  tabs.innerHTML = '';
  const projects = STATE.projects || {};
  // Preserve sorted order: most-loaded first
  const sorted = Object.entries(projects).sort((a, b) => {
    const aSum = (a[1]['phase-1']||[]).length + (a[1]['phase-2']||[]).length + (a[1]['open-removed']||[]).length;
    const bSum = (b[1]['phase-1']||[]).length + (b[1]['phase-2']||[]).length + (b[1]['open-removed']||[]).length;
    return bSum - aSum;
  });
  if (!CURRENT_PROJECT && sorted.length > 0) {
    CURRENT_PROJECT = localStorage.getItem('mm_project') || sorted[0][0];
    if (!projects[CURRENT_PROJECT]) CURRENT_PROJECT = sorted[0][0];
  }
  for (const [key, proj] of sorted) {
    const total = (proj['phase-1']||[]).length + (proj['phase-2']||[]).length + (proj['open-removed']||[]).length;
    const tab = document.createElement('a');
    tab.className = 'project-tab' + (key === CURRENT_PROJECT ? ' active' : '');
    tab.href = '#';
    tab.innerHTML = (proj.title || key) + '<span class="count">' + total + '</span>';
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      CURRENT_PROJECT = key;
      localStorage.setItem('mm_project', key);
      renderTabs();
      renderProject();
    });
    tabs.appendChild(tab);
  }
}

function renderNode(node) {
  const status = node.status || 'built';
  const date = node.date || '';
  const dateLabel = node.date_label || 'ADDED';

  let html = `<div class="node" data-status="${status}">`;
  html += `<div class="node-date">${date} · ${dateLabel}</div>`;
  if (status === 'removed' && node.date_cut) {
    html += `<div class="node-date removed-date">${node.date_cut} · CUT</div>`;
  }
  html += `<h4>${escapeHtml(node.title || '—')}</h4>`;
  html += `<span class="node-status">${status}</span>`;
  html += '<div class="node-details">';
  if (node.what) html += `<p class="what">${escapeHtml(node.what)}</p>`;
  if (status === 'modified') {
    if (node.prior) html += `<div class="prior">${escapeHtml(node.prior)}</div>`;
    if (node.now) html += `<div class="now">${escapeHtml(node.now)}</div>`;
    if (node.change_commit || node.change_reason) {
      html += '<div class="tech">';
      if (node.change_commit) html += `<strong>Commit:</strong> ${escapeHtml(node.change_commit)}<br>`;
      if (node.change_reason) html += `<strong>Reason:</strong> ${escapeHtml(node.change_reason)}`;
      html += '</div>';
    }
  }
  if (status === 'removed' && node.why_removed) html += `<div class="why-removed">${escapeHtml(node.why_removed)}</div>`;
  if (node.shane_note) html += `<div class="shane-note">${escapeHtml(node.shane_note)}</div>`;
  if (node.tech) html += `<div class="tech">${node.tech}</div>`;
  if (node.choices && node.choices.length) {
    html += '<div class="choices"><ul>';
    for (const c of node.choices) html += `<li>${escapeHtml(c)}</li>`;
    html += '</ul></div>';
  }
  html += '</div></div>';
  return html;
}

function renderProject() {
  const area = document.getElementById('project-area');
  if (!CURRENT_PROJECT || !STATE.projects[CURRENT_PROJECT]) {
    area.innerHTML = '<div class="empty">No project selected.<div class="hint">Pick a tab above.</div></div>';
    return;
  }
  const proj = STATE.projects[CURRENT_PROJECT];
  let html = `<div class="project-header"><h2>${escapeHtml(proj.title)}</h2><div class="subtitle">${escapeHtml(proj.subtitle || '')}</div></div>`;
  html += `<div class="filter-bar"><span class="filter-label">Show</span>` +
          `<button class="filter-btn ${CURRENT_FILTER==='all'?'active':''}" data-filter="all">All</button>` +
          `<button class="filter-btn ${CURRENT_FILTER==='built'?'active':''}" data-filter="built">Built</button>` +
          `<button class="filter-btn ${CURRENT_FILTER==='planned'?'active':''}" data-filter="planned">Planned</button>` +
          `<button class="filter-btn ${CURRENT_FILTER==='decision'?'active':''}" data-filter="decision">Decisions</button>` +
          `<button class="filter-btn ${CURRENT_FILTER==='modified'?'active':''}" data-filter="modified">Modified</button>` +
          `<button class="filter-btn ${CURRENT_FILTER==='removed'?'active':''}" data-filter="removed">Removed</button>` +
          `<button class="filter-btn ${CURRENT_FILTER==='active'?'active':''}" data-filter="active">Hide removed</button>` +
          `</div>`;

  html += '<div class="branches">';
  const branches = [
    ['phase-1', 'Phase 1', 'Built + Tested'],
    ['phase-2', 'Phase 2+', 'Planned / Promised'],
    ['open-removed', 'Open / Cut', 'Decisions + history'],
  ];
  for (const [key, label, sub] of branches) {
    html += `<div class="branch ${key}">`;
    html += `<div class="branch-header"><h3>${label}</h3><div class="subtitle">${sub}</div></div>`;
    const nodes = proj[key] || [];
    if (nodes.length === 0) {
      html += '<div style="text-align:center; color:var(--text-muted); font-size:0.78rem; padding:10px;">— empty —</div>';
    }
    for (const n of nodes) html += renderNode(n);
    html += '</div>';
  }
  html += '</div>';
  area.innerHTML = html;

  // Click handlers
  area.querySelectorAll('.node').forEach(n => {
    n.addEventListener('click', () => n.classList.toggle('expanded'));
  });
  area.querySelectorAll('.filter-btn').forEach(b => {
    b.addEventListener('click', () => {
      CURRENT_FILTER = b.dataset.filter;
      localStorage.setItem('mm_filter', CURRENT_FILTER);
      applyFilter();
      area.querySelectorAll('.filter-btn').forEach(x => x.classList.toggle('active', x === b));
    });
  });
  applyFilter();
}

function applyFilter() {
  document.querySelectorAll('#project-area .node').forEach(n => {
    const s = n.dataset.status;
    let show = false;
    if (CURRENT_FILTER === 'all') show = true;
    else if (CURRENT_FILTER === 'active') show = s !== 'removed';
    else show = s === CURRENT_FILTER;
    n.classList.toggle('hidden', !show);
  });
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, ch => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[ch]));
}

async function init() {
  if (await loadState()) {
    renderTabs();
    renderProject();
  }
  // Poll every 30 seconds for new deltas.
  setInterval(async () => {
    const ok = await loadState();
    if (ok) {
      renderTabs();
      renderProject();
    }
  }, 30000);
}

init();
</script>
</body></html>
"""


# ── Run ────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Seed state file if absent so first-boot serves a working page.
    load_state()
    print(f"ShaneBrain Mindmap serving on 0.0.0.0:{PORT}")
    print(f"Tailscale URL: http://100.67.120.6:{PORT}")
    print(f"State file: {STATE_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
