#!/usr/bin/env python3
"""
update_mindmap.py — Single-source-of-truth YourLegacy mindmap maintainer.

Run on the Pi. Reads CODE-mode Conversation entries from Weaviate that contain
a `MINDMAP_DELTA` JSON block. Applies each delta to the canonical HTML mindmap.
Overwrites the existing file in place — no proliferation. Distributes via the
existing claudemd-sync rails (the watcher already fires on file mtime).

Delta format inside a Conversation log message (anywhere in the body):

    MINDMAP_DELTA:
    ```json
    {
      "session_id": "yourlegacy-phase1-2026-05-25",
      "added": [
        {
          "branch": "phase-1" | "phase-2" | "open-removed",
          "title": "Foundry test suite — 33/33 GREEN",
          "status": "built" | "planned" | "decision" | "modified" | "removed",
          "date": "2026-05-25",
          "date_label": "VERIFIED",
          "what": "Plain-language description",
          "shane_note": "Optional",
          "tech": "Optional mono-font technical block",
          "choices": ["bullet 1", "bullet 2"]
        }
      ],
      "modified": [
        {
          "title": "inherit() local variable name",
          "branch": "phase-1",
          "prior": "uint256 silenceDuration = ...",
          "now": "uint256 elapsed = ...",
          "reason": "Shadowing fix",
          "commit": "3dda132"
        }
      ],
      "removed": [
        {
          "title": "Path B — Custodian-only architecture",
          "date_added": "2026-05-25",
          "date_cut": "2026-05-25",
          "why": "Too slow, too regulated for solo builder"
        }
      ],
      "timeline": [
        {"date": "2026-05-25", "label": "Phase 1 SEALED", "major": true}
      ]
    }
    ```

Usage:
    # One-shot (manual)
    python3 scripts/update_mindmap.py

    # Cron / systemd timer (every hour or every day)
    python3 scripts/update_mindmap.py --since 24h

    # Specific session
    python3 scripts/update_mindmap.py --session-id yourlegacy-phase1-2026-05-25

    # Force full rebuild from all sessions
    python3 scripts/update_mindmap.py --rebuild

Environment:
    WEAVIATE_URL          default http://100.100.90.66:8080
    MINDMAP_PATH          default /mnt/shanebrain-raid/shanebrain-core/yourlegacy-mindmap.html
    MINDMAP_DESKTOP_PATH  optional — secondary write target on a Hubby machine via Taildrop

This script is idempotent. Running it twice with the same input produces the
same output. It rebuilds the HTML from a JSON state file maintained alongside
the HTML (yourlegacy-mindmap.state.json), then re-renders.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ── Configuration ──────────────────────────────────────────────────────────
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://100.100.90.66:8080")
# Default: post deltas to local mindmap server. Falls back to file-write if unreachable.
MINDMAP_SERVER_URL = os.environ.get(
    "MINDMAP_SERVER_URL", "http://localhost:8600"
)
MINDMAP_PATH = Path(
    os.environ.get(
        "MINDMAP_PATH",
        "/mnt/shanebrain-raid/shanebrain-core/yourlegacy-mindmap.html",
    )
)
STATE_PATH = MINDMAP_PATH.with_suffix(".state.json")
DELTA_MARKER_RE = re.compile(
    r"MINDMAP_DELTA:\s*```json\s*(\{.*?\})\s*```", re.DOTALL
)

# ── Weaviate query helpers ─────────────────────────────────────────────────


def query_recent_conversations(since_hours: int | None) -> list[dict[str, Any]]:
    """Pull CODE-mode Conversation objects from Weaviate via GraphQL."""
    where_clause = ""
    if since_hours is not None:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=since_hours)
        ).isoformat()
        where_clause = (
            f', where: {{ path: ["timestamp"], operator: GreaterThan, '
            f'valueDate: "{cutoff}" }}'
        )

    query = f"""
    {{
      Get {{
        Conversation(
          limit: 200,
          sort: [{{path: ["timestamp"], order: desc}}]
          {where_clause}
        ) {{
          message
          timestamp
          session_id
          mode
        }}
      }}
    }}
    """
    req = urllib.request.Request(
        f"{WEAVIATE_URL}/v1/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    return body.get("data", {}).get("Get", {}).get("Conversation", []) or []


def query_session(session_id: str) -> list[dict[str, Any]]:
    """Pull all Conversation objects for one session."""
    query = f"""
    {{
      Get {{
        Conversation(
          limit: 200,
          where: {{
            path: ["session_id"],
            operator: Equal,
            valueString: "{session_id}"
          }}
        ) {{
          message
          timestamp
          session_id
          mode
        }}
      }}
    }}
    """
    req = urllib.request.Request(
        f"{WEAVIATE_URL}/v1/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    return body.get("data", {}).get("Get", {}).get("Conversation", []) or []


# ── Delta extraction ───────────────────────────────────────────────────────


def extract_deltas(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find MINDMAP_DELTA blocks in conversation messages."""
    deltas: list[dict[str, Any]] = []
    for conv in conversations:
        msg = conv.get("message") or ""
        for match in DELTA_MARKER_RE.finditer(msg):
            try:
                delta = json.loads(match.group(1))
                delta.setdefault("_timestamp", conv.get("timestamp"))
                deltas.append(delta)
            except json.JSONDecodeError as e:
                print(
                    f"  WARN: malformed delta in {conv.get('session_id')}: {e}",
                    file=sys.stderr,
                )
    # Oldest first so newer modifications win.
    deltas.sort(key=lambda d: d.get("_timestamp") or "")
    return deltas


# ── State management ──────────────────────────────────────────────────────


def load_state() -> dict[str, Any]:
    """Load the persistent mindmap state (or start fresh)."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "phase-1": [],
        "phase-2": [],
        "open-removed": [],
        "timeline": [],
        "last_updated": None,
        "processed_deltas": [],
    }


def save_state(state: dict[str, Any]) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2))


def apply_delta(state: dict[str, Any], delta: dict[str, Any]) -> None:
    """Mutate state in-place by applying one delta."""
    # ADD
    for node in delta.get("added", []):
        branch = node.get("branch", "phase-1")
        # De-dupe by title within a branch.
        if not any(n["title"] == node["title"] for n in state.get(branch, [])):
            state.setdefault(branch, []).append(node)

    # MODIFY — find a node by title, flip status to "modified",
    # stash prior/now content blocks.
    for mod in delta.get("modified", []):
        title = mod["title"]
        branch = mod.get("branch", "phase-1")
        for node in state.get(branch, []):
            if node["title"] == title:
                node["status"] = "modified"
                node["prior"] = mod.get("prior", node.get("what", ""))
                node["now"] = mod.get("now", "")
                node["change_reason"] = mod.get("reason", "")
                node["change_commit"] = mod.get("commit", "")
                node["date_label"] = "CHANGED"
                break

    # REMOVE
    for rm in delta.get("removed", []):
        title = rm["title"]
        for branch in ("phase-1", "phase-2", "open-removed"):
            for node in state.get(branch, []):
                if node["title"] == title:
                    node["status"] = "removed"
                    node["date_cut"] = rm.get("date_cut")
                    node["why_removed"] = rm.get("why", "")
                    # Move to open-removed branch.
                    if branch != "open-removed":
                        state[branch].remove(node)
                        state.setdefault("open-removed", []).append(node)
                    break

    # TIMELINE
    for tl in delta.get("timeline", []):
        if not any(
            t["date"] == tl["date"] and t["label"] == tl["label"]
            for t in state.get("timeline", [])
        ):
            state.setdefault("timeline", []).append(tl)


# ── HTML rendering ─────────────────────────────────────────────────────────

HTML_TEMPLATE_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>YourLegacy Mindmap — Dated Routes</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="yourlegacy-mindmap.css">
<style>
  /* Inline fallback if external CSS missing. Full styles are in the
     hand-authored HTML on Shane's Desktop; this generator only needs the
     minimal pieces to keep the visual contract. */
  body { background: #0a0a12; color: #f0f0f5; font-family: sans-serif; padding: 24px; }
  .node { background: #14141e; border: 1px solid #2a2a36; border-radius: 10px;
          padding: 12px; margin: 8px; }
  .node[data-status="modified"] { border-color: #ff3052; }
  .node[data-status="removed"] h4 { text-decoration: line-through; color: #707080; }
  .prior { text-decoration: line-through; color: #707080;
           background: rgba(255,48,82,0.04); padding: 6px; }
  .now { color: #f0f0f5; background: rgba(0,255,136,0.05); padding: 6px; }
</style></head><body>
<header>
  <h1>YourLegacy Mindmap — CANONICAL · Updated {now}</h1>
  <p>Single source of truth. Overwritten by scripts/update_mindmap.py.</p>
</header>
"""

HTML_TEMPLATE_FOOT = """
<footer>
  <p>Updated {now} · Source: Weaviate Conversation deltas · Generator: scripts/update_mindmap.py</p>
</footer>
</body></html>
"""


def render_node(node: dict[str, Any]) -> str:
    status = node.get("status", "built")
    title = node.get("title", "—")
    date = node.get("date", "")
    date_label = node.get("date_label", "ADDED")

    parts = [f'<div class="node" data-status="{status}">']
    parts.append(f'<div class="node-date">{date} · {date_label}</div>')

    if status == "removed" and node.get("date_cut"):
        parts.append(
            f'<div class="node-date removed-date">{node["date_cut"]} · CUT</div>'
        )

    parts.append(f"<h4>{title}</h4>")
    parts.append(f'<span class="node-status">{status.title()}</span>')

    parts.append('<div class="node-details">')
    if node.get("what"):
        parts.append(f'<p class="what">{node["what"]}</p>')
    if status == "modified":
        if node.get("prior"):
            parts.append(f'<div class="prior">{node["prior"]}</div>')
        if node.get("now"):
            parts.append(f'<div class="now">{node["now"]}</div>')
        if node.get("change_reason") or node.get("change_commit"):
            parts.append('<div class="tech">')
            if node.get("change_commit"):
                parts.append(
                    f'<strong>Commit:</strong> {node["change_commit"]}<br>'
                )
            if node.get("change_reason"):
                parts.append(f'<strong>Reason:</strong> {node["change_reason"]}')
            parts.append("</div>")
    if status == "removed" and node.get("why_removed"):
        parts.append(f'<div class="why-removed">{node["why_removed"]}</div>')
    if node.get("shane_note"):
        parts.append(f'<div class="shane-note">{node["shane_note"]}</div>')
    if node.get("tech"):
        parts.append(f'<div class="tech">{node["tech"]}</div>')
    if node.get("choices"):
        parts.append('<div class="choices"><ul>')
        for ch in node["choices"]:
            parts.append(f"<li>{ch}</li>")
        parts.append("</ul></div>")
    parts.append("</div></div>")
    return "\n".join(parts)


def render_html(state: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [HTML_TEMPLATE_HEAD.format(now=now)]

    for branch, label in [
        ("phase-1", "Phase 1 — Built + Tested"),
        ("phase-2", "Phase 2+ — Planned"),
        ("open-removed", "Open / Decisions / Cut"),
    ]:
        out.append(f"<section><h2>{label}</h2>")
        for node in state.get(branch, []):
            out.append(render_node(node))
        out.append("</section>")

    if state.get("timeline"):
        out.append('<section class="time-axis"><h3>Timeline</h3>')
        for tl in sorted(state["timeline"], key=lambda t: t["date"]):
            cls = "tick major" if tl.get("major") else "tick"
            out.append(f'<span class="{cls}">{tl["date"]} · {tl["label"]}</span>')
        out.append("</section>")

    out.append(HTML_TEMPLATE_FOOT.format(now=now))
    return "\n".join(out)


# ── Daily-briefing hook ────────────────────────────────────────────────────


def daily_summary(state: dict[str, Any], since_hours: int = 24) -> str:
    """Return a short markdown summary for inclusion in shanebrain_daily_briefing."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).date()
    added = []
    modified = []
    cut = []
    for branch in ("phase-1", "phase-2", "open-removed"):
        for n in state.get(branch, []):
            try:
                d = datetime.fromisoformat(n.get("date", "")).date()
            except (TypeError, ValueError):
                continue
            if d < cutoff:
                continue
            if n.get("status") == "modified":
                modified.append(n["title"])
            elif n.get("status") == "removed":
                cut.append(n["title"])
            else:
                added.append(n["title"])

    lines = [f"### Mindmap deltas (last {since_hours}h)"]
    if added:
        lines.append(f"**Added ({len(added)}):**")
        for t in added:
            lines.append(f"- {t}")
    if modified:
        lines.append(f"**Modified ({len(modified)}):**")
        for t in modified:
            lines.append(f"- {t}")
    if cut:
        lines.append(f"**Cut ({len(cut)}):**")
        for t in cut:
            lines.append(f"- {t}")
    if not (added or modified or cut):
        lines.append("_No changes in window._")
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--since",
        default="24h",
        help="Time window to pull (e.g., 24h, 7d). Default: 24h.",
    )
    ap.add_argument(
        "--session-id",
        help="Process only this session_id. Overrides --since.",
    )
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Discard processed-delta cache and re-apply every delta found.",
    )
    ap.add_argument(
        "--daily-summary",
        action="store_true",
        help="Print only the daily-briefing markdown summary, then exit.",
    )
    args = ap.parse_args()

    # Parse --since
    since_hours = None
    if args.since.endswith("h"):
        since_hours = int(args.since[:-1])
    elif args.since.endswith("d"):
        since_hours = int(args.since[:-1]) * 24

    # Load existing state
    state = load_state()
    if args.rebuild:
        print("REBUILD — discarding processed-delta cache")
        state["processed_deltas"] = []

    # Daily-summary-only mode
    if args.daily_summary:
        print(daily_summary(state, since_hours or 24))
        return 0

    # Pull conversations
    if args.session_id:
        convs = query_session(args.session_id)
    else:
        convs = query_recent_conversations(since_hours)
    print(f"Pulled {len(convs)} Conversation objects from Weaviate")

    # Extract and apply deltas
    deltas = extract_deltas(convs)
    print(f"Found {len(deltas)} MINDMAP_DELTA blocks")
    applied = 0
    processed = set(state.get("processed_deltas", []))
    for delta in deltas:
        key = delta.get("_timestamp", "") + "|" + delta.get("session_id", "")
        if key in processed and not args.rebuild:
            continue
        apply_delta(state, delta)
        processed.add(key)
        applied += 1
    state["processed_deltas"] = sorted(processed)
    print(f"Applied {applied} new deltas")

    # Primary path: POST each new delta to the mindmap server. Live update.
    server_posted = 0
    server_ok = True
    try:
        for delta in deltas:
            key = delta.get("_timestamp", "") + "|" + delta.get("session_id", "")
            if key not in state.get("processed_deltas", []) and not args.rebuild:
                continue  # already-applied
            # Strip internal field before POST
            payload = {k: v for k, v in delta.items() if not k.startswith("_")}
            req = urllib.request.Request(
                f"{MINDMAP_SERVER_URL}/api/delta",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                json.load(r)
            server_posted += 1
        if server_posted:
            print(f"Posted {server_posted} deltas to {MINDMAP_SERVER_URL}/api/delta")
    except Exception as e:
        server_ok = False
        print(
            f"  WARN: server post failed ({e}). Falling back to file write.",
            file=sys.stderr,
        )

    # Fallback / dual-write: write a static HTML copy alongside the live server.
    # Useful when the server is down or for offline export.
    if not server_ok or os.environ.get("MINDMAP_DUAL_WRITE"):
        html = render_html(state)
        MINDMAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        MINDMAP_PATH.write_text(html, encoding="utf-8")
        save_state(state)
        print(f"Wrote static fallback {MINDMAP_PATH} ({len(html):,} bytes)")

    # Optional second target (e.g. for Taildrop to Hubby Desktop)
    desktop = os.environ.get("MINDMAP_DESKTOP_PATH")
    if desktop and (not server_ok or os.environ.get("MINDMAP_DUAL_WRITE")):
        Path(desktop).write_text(render_html(state), encoding="utf-8")
        print(f"Also wrote {desktop}")

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
