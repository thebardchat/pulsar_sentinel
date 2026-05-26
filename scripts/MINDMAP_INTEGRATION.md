# YourLegacy Mindmap — Single-File Integration

> **Last Updated:** 2026-05-25 | **Owner:** Shane Brazelton | **Canonical path:** `/mnt/shanebrain-raid/shanebrain-core/yourlegacy-mindmap.html` on the Pi

---

## The rule (read this first)

**One file. Always overwritten. Never duplicated.** No more `yourlegacy-mindmap.html`, `yourlegacy-mindmap-v2.html`, `yourlegacy-mindmap-final.html`, etc. The Pi is the source of truth; every other machine pulls a copy via the existing claudemd-sync rails.

When something changes, **the old state is shown with a red strikethrough above the new state.** Auditor-grade visual diff: nothing gets lost.

---

## Where things live

| Surface | Path | Authority |
|---|---|---|
| Source of truth | `/mnt/shanebrain-raid/shanebrain-core/yourlegacy-mindmap.html` on Pi (`shanebrain` node) | ✅ Canonical |
| State cache | `/mnt/shanebrain-raid/shanebrain-core/yourlegacy-mindmap.state.json` on Pi | Tracks applied deltas |
| Updater script | `scripts/update_mindmap.py` | Reads Weaviate, applies deltas, rewrites HTML |
| Systemd service | `scripts/update-mindmap.service` | Runs the script |
| Systemd timer | `scripts/update-mindmap.timer` | Schedules hourly + boot runs |
| Hubby Desktop copy | `~/Desktop/yourlegacy-mindmap.html` | Read-only mirror (via claudemd-sync rails) |
| iPhone | Taildrop drop folder | Read-only mirror |
| Google Drive | `shanebrain@shanebrain.cloud` → Drive | Read-only mirror |

---

## How an update happens

```
[Claude session writes MINDMAP_DELTA into Weaviate Conversation]
        ↓
[Pi systemd timer fires hourly (update-mindmap.timer)]
        ↓
[update_mindmap.py queries Weaviate for new deltas]
        ↓
[Applies deltas to state.json — adds / modifies / removes nodes]
        ↓
[Re-renders yourlegacy-mindmap.html — overwrites in place]
        ↓
[inotifywait detects the file mtime change]
        ↓
[claudemd-sync distributes to Desktop / iPhone / Drive / Discord / email]
        ↓
[shanebrain_daily_briefing includes "Mindmap deltas (last 24h)" section]
```

---

## How to write a delta in your next session

When Claude finishes a chunk of work, it appends a `MINDMAP_DELTA` JSON block to its Weaviate Conversation log. The block is fenced as a json code block so the parser finds it cleanly.

Example block embedded inside a CODE-mode conversation log:

````
MINDMAP_DELTA:
```json
{
  "session_id": "yourlegacy-phase2-day1",
  "added": [
    {
      "branch": "phase-2",
      "title": "Chainlink Automation hook wired in",
      "status": "built",
      "date": "2026-05-30",
      "date_label": "ADDED",
      "what": "Vault registered with Chainlink Automation network. ~$5/yr per vault. Auto-calls inherit() at threshold."
    }
  ],
  "modified": [
    {
      "title": "RC 1.02 fires — funds to heir",
      "branch": "phase-1",
      "prior": "Heir must manually call inherit()",
      "now": "Chainlink Automation calls inherit() for the heir automatically at day 90",
      "reason": "UX upgrade — heir doesn't need a wallet ready at the moment threshold elapses",
      "commit": "abc1234"
    }
  ],
  "removed": [],
  "timeline": [
    {"date": "2026-05-30", "label": "Phase 2 begins", "major": true}
  ]
}
```
````

The script auto-applies these on the next timer tick.

---

## Deployment — first-time install on the Pi

```bash
# SSH to Pi
ssh shanebrain@100.67.120.6

# Pull latest from the pulsar_sentinel repo
cd /mnt/shanebrain-raid/pulsar-sentinel
git pull origin main

# Copy the script + units to shanebrain-core (keeps mindmap with the Pi tools, not the Sentinel app)
sudo cp scripts/update_mindmap.py /mnt/shanebrain-raid/shanebrain-core/scripts/
sudo chmod +x /mnt/shanebrain-raid/shanebrain-core/scripts/update_mindmap.py

# Install the systemd units
sudo cp scripts/update-mindmap.service /etc/systemd/system/
sudo cp scripts/update-mindmap.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now update-mindmap.timer

# Verify the timer is scheduled
systemctl list-timers update-mindmap.timer

# Manual first run to seed the state file
sudo systemctl start update-mindmap.service
sudo journalctl -u update-mindmap.service -n 50

# Confirm the canonical HTML now exists
ls -lah /mnt/shanebrain-raid/shanebrain-core/yourlegacy-mindmap.html
```

---

## Daily briefing integration

Add this to the existing `shanebrain_daily_briefing` MCP tool body (server.py on Pi):

```python
# Inside shanebrain_daily_briefing()
mindmap_summary = subprocess.check_output(
    ["python3",
     "/mnt/shanebrain-raid/shanebrain-core/scripts/update_mindmap.py",
     "--daily-summary",
     "--since", "24h"],
    timeout=10,
).decode()

# Append to the briefing payload
briefing["mindmap_deltas_24h"] = mindmap_summary
```

That's the only wiring needed — the script's `--daily-summary` flag returns a markdown snippet ready to drop in.

---

## What this DOES NOT do (yet)

- No GUI editor — node edits go through Weaviate deltas, not direct HTML editing
- No multi-user write coordination — the Pi is single-writer (matches the cluster-drift plan)
- No history scrubbing UI — you see current state + the recent prior on modified nodes, but full history lives in Weaviate

---

## Why this design

- **Single file, always overwritten** — Shane's #1 request. No proliferation.
- **Pi-authoritative** — matches the cluster-drift architecture decision from session 2026-05-25 (LegacyKnowledge UUID `7304f231-...`)
- **Uses existing rails** — claudemd-sync already broadcasts file changes; we ride those rails instead of building new ones
- **Weaviate as the change log** — every session already writes Conversation entries; the delta is just a structured block inside that
- **Auditor-grade diffs** — modified nodes show PRIOR (red strikethrough) above NOW (green) so the change history is always visible
- **Daily briefing integration** — the morning report shows what the mindmap gained / changed / lost overnight
