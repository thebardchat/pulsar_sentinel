# ShaneBrain Universal Mindmap — Tailscale-Live Integration

> **Last Updated:** 2026-05-25 | **Owner:** Shane Brazelton
> **Live URL:** `http://100.67.120.6:8600` (Tailscale, every node)
> **Source state:** `/mnt/shanebrain-raid/shanebrain-core/mindmap-state.json` on Pi

---

## The rule (read this first)

**One service. Every project. One URL. Every device.**

Open `http://100.67.120.6:8600` on pulsar00100, gulfshores, neworleans, your iPhone (over Tailscale), or any laptop on the mesh — same live state, every time. No file copying. No "is this the latest?" friction. No proliferation of HTML files. Bookmark it on Safari and you're one tap from the whole brain.

Projects are **tabs inside the same UI**: YourLegacy, Pulsar Sentinel, SRM Dispatch, Book 2, Claim Cruncher, AI-Trainer-MAX, HaloFinance, MEGA Crew, Wrestling Facility — all live behind the same URL. Add new projects on the fly via the `/api/delta` endpoint (the updater script handles this).

When something changes, **the old state shows with a red strikethrough above the new state.** Auditor-grade visual diff: nothing gets lost.

---

## Where things live

| Surface | Path | Authority |
|---|---|---|
| Live URL | `http://100.67.120.6:8600` (Tailscale) | ✅ Where you actually look |
| Server | `scripts/mindmap_server.py` on Pi:8600 | FastAPI app, serves UI + API |
| Server systemd | `scripts/mindmap-server.service` | Auto-start on boot, restart on failure |
| State file | `/mnt/shanebrain-raid/shanebrain-core/mindmap-state.json` | Canonical multi-project state |
| Updater script | `scripts/update_mindmap.py` | Reads Weaviate, posts deltas to server |
| Updater systemd | `scripts/update-mindmap.{service,timer}` | Hourly delta sync |
| API endpoints | `GET /api/state` · `POST /api/delta` · `GET /api/projects` | Programmatic access |
| Health check | `GET /api/health` | Liveness probe for uptime monitor |
| iPhone bookmark | `http://100.67.120.6:8600` saved to Safari Home Screen | One-tap access over Tailscale |

---

## How an update happens

```
[Claude session writes MINDMAP_DELTA into Weaviate Conversation]
        ↓
[Pi systemd timer fires hourly (update-mindmap.timer)]
        ↓
[update_mindmap.py queries Weaviate for new deltas]
        ↓
[POST each delta to http://localhost:8600/api/delta]
        ↓
[mindmap_server.py applies to state JSON in place]
        ↓
[Next page load (or 30-second poll) shows the change live]
        ↓
[shanebrain_daily_briefing includes "Mindmap deltas (last 24h)" section]
```

**Every device on Tailscale sees the same live state in real time.** The UI auto-polls every 30 seconds. No reload needed.

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

# Install Python deps (one-time)
pip3 install --user fastapi 'uvicorn[standard]'

# Copy server + updater + units to shanebrain-core
sudo mkdir -p /mnt/shanebrain-raid/shanebrain-core/scripts
sudo cp scripts/mindmap_server.py /mnt/shanebrain-raid/shanebrain-core/scripts/
sudo cp scripts/update_mindmap.py /mnt/shanebrain-raid/shanebrain-core/scripts/
sudo chmod +x /mnt/shanebrain-raid/shanebrain-core/scripts/mindmap_server.py
sudo chmod +x /mnt/shanebrain-raid/shanebrain-core/scripts/update_mindmap.py

# Install all three systemd units
sudo cp scripts/mindmap-server.service /etc/systemd/system/
sudo cp scripts/update-mindmap.service /etc/systemd/system/
sudo cp scripts/update-mindmap.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Start the server first (it serves the UI + API)
sudo systemctl enable --now mindmap-server.service
sudo systemctl status mindmap-server.service

# Then start the updater timer (hourly delta pulls from Weaviate)
sudo systemctl enable --now update-mindmap.timer
systemctl list-timers update-mindmap.timer

# Verify the server is live
curl http://localhost:8600/api/health
# Expected: {"status":"ok","service":"shanebrain-mindmap","port":8600}

# Open from any Tailscale device:
#   http://100.67.120.6:8600
# On iPhone Safari: Share → Add to Home Screen for one-tap access
```

## Optional — public URL via Cloudflare tunnel

```bash
# Add a mapping in your cloudflared config (where mcp.shanebrain.cloud already routes):
# mindmap.shanebrain.cloud → http://localhost:8600
# Then any device anywhere on the internet (with the right auth) sees it.
```

---

## Multi-user on the NAS (bullfrog · TrueNAS Scale)

Every family member gets their own login. Credentials live on bullfrog. Pi mounts them via NFS. Sessions persist across reboots.

### One-time bullfrog setup (TrueNAS web UI clicks)

These are the only steps that can't be automated — TrueNAS requires UI interaction.

1. **Web UI** at `http://100.92.153.3` → log in as your TrueNAS admin.
2. **Datasets** → tank → Add Dataset:
   - Name: `shanebrain`
   - Permissions Type: POSIX
   - Compression: lz4
   - Save
3. **Shares → UNIX (NFS) Shares** → Add:
   - Path: `/mnt/tank/shanebrain`
   - Authorized Networks: `100.64.0.0/10` (entire Tailscale CGNAT range)
   - Maproot User: `nobody`
   - Maproot Group: `nogroup`
   - Save → enable NFS service when prompted.

That's it for bullfrog. ~3 minutes of clicking.

### Pi-side mount (one-time)

```bash
ssh shanebrain@100.67.120.6
sudo apt-get install -y nfs-common
sudo mkdir -p /mnt/nas/shanebrain
# Add the mount to /etc/fstab (persistent across reboots)
echo '100.92.153.3:/mnt/tank/shanebrain  /mnt/nas/shanebrain  nfs  rw,hard,intr,_netdev  0  0' | sudo tee -a /etc/fstab
sudo mount -a
ls -lah /mnt/nas/shanebrain   # should list (empty directory ready for use)
```

### Initialize the users file (interactive)

```bash
# On the Pi
cd /mnt/shanebrain-raid/shanebrain-core/scripts
python3 add_mindmap_user.py init
# Prompts you for owner username (default: shane), display name, password.
# Creates /mnt/nas/shanebrain/users.json with chmod 600.

# Add family members
python3 add_mindmap_user.py add tiffany --role family --display-name "Tiffany"
python3 add_mindmap_user.py add gavin   --role family --display-name "Gavin"
python3 add_mindmap_user.py add angel   --role family --display-name "Angel"
python3 add_mindmap_user.py add kai     --role family --display-name "Kai"
python3 add_mindmap_user.py add pierce  --role family --display-name "Pierce"
python3 add_mindmap_user.py add jaxton  --role family --display-name "Jaxton"
python3 add_mindmap_user.py add ryker   --role viewer --display-name "Ryker"   # he's 5

python3 add_mindmap_user.py list
```

### Switch the mindmap server to multi-user mode

```bash
# Restart the server — it auto-detects the NAS mount and enables auth.
sudo systemctl restart mindmap-server.service
sudo journalctl -u mindmap-server.service -n 10

# Verify
curl http://localhost:8600/api/health
# Should now show "auth_enabled": true and state_path under /mnt/nas/shanebrain
```

### Family onboarding (~30 seconds per person)

For each family member, send them this:

> Open Safari (iPhone) or any browser. Make sure Tailscale is connected and shows the green dot. Go to: **http://100.67.120.6:8600**
> Sign in:
> - Username: `tiffany` (or whatever Shane gave you)
> - Password: (the one Shane set for you)
>
> Bookmark it. On iPhone: Share → Add to Home Screen → name it "Mindmap".

That's it. They're in.

### Migrate existing state to the NAS (one-time)

If you already have `/mnt/shanebrain-raid/shanebrain-core/mindmap-state.json` from earlier deploys, move it to the NAS so the server reads from one canonical location:

```bash
sudo cp /mnt/shanebrain-raid/shanebrain-core/mindmap-state.json /mnt/nas/shanebrain/mindmap-state.json
sudo systemctl restart mindmap-server.service
```

### Audit log

Every login, logout, read, and delta-write is appended to `/mnt/nas/shanebrain/mindmap-audit.log` with timestamp + user + action. Tail it any time:

```bash
tail -n 20 /mnt/nas/shanebrain/mindmap-audit.log
```

Example lines:

```
2026-05-26T14:32:09+00:00  shane    state.read
2026-05-26T14:33:01+00:00  tiffany  login.ok
2026-05-26T14:33:18+00:00  tiffany  project.read   yourlegacy
```

### Roles

| Role     | Read state | Post deltas | Use case |
|----------|------------|-------------|----------|
| `owner`  | ✅         | ✅          | Shane    |
| `family` | ✅         | ✅          | Tiffany, Gavin, Angel, older sons |
| `viewer` | ✅         | ❌          | Ryker, future kids' accounts |

Role is set when you create the user (`add_mindmap_user.py add ... --role family`).

### Disable auth (revert to Tailscale-only)

```bash
# Unmount the NAS or unset USERS_FILE
sudo systemctl edit mindmap-server.service
# Add under [Service]:
#   Environment="USERS_FILE="
sudo systemctl daemon-reload
sudo systemctl restart mindmap-server.service
```

Now the server is back to "anyone on Tailscale can see it" — no logins. Useful for solo dev.

---

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
