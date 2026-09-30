# CLAUDE.md — Pulsar Sentinel
> **Last Updated:** 2026-05-12 | **Status:** LIVE + PAYING | **Owner:** Shane Brazelton

---

## Current State (Read This First)

Pulsar Sentinel is **live** at https://sentinel.shanebrain.cloud. Stripe live mode is wired. Discord bot is running. All 43 public repos have the ad banner. Do not treat this as a dev project — it is a running product.

---

## Where Things Live

| Thing | Path |
|---|---|
| Project root | `/mnt/shanebrain-raid/pulsar-sentinel/` |
| Source (FastAPI) | `src/api/server.py`, `src/api/routes.py`, `src/api/auth.py` |
| Config | `config/settings.py` |
| Landing page | `landing.html` → served at `/` |
| GitHub Pages copy | `index.html` (repo root) |
| Discord bot | `scripts/run_discord_bot.py` |
| Quantum banner | `quantum-banner.gif` (v5, animated, in repo root) |
| Environment | `.env` (never commit) |
| venv | `venv/` |

**The project is at `/mnt/shanebrain-raid/pulsar-sentinel/` — NOT inside shanebrain-core.**

---

## Running Services

| Service | Port | Command |
|---|---|---|
| `pulsar-sentinel` | 8250 | `sudo systemctl restart pulsar-sentinel` |
| `pulsar-sentinel-bot` | — | `sudo systemctl restart pulsar-sentinel-bot` |
| `cloudflared-mcp` | — | Cloudflare Zero Trust tunnel |

```bash
sudo systemctl status pulsar-sentinel
sudo journalctl -u pulsar-sentinel -f   # live logs
```

**Sentinel runs on the Pi only.** Pulsar Windows (100.81.70.117) does NOT run Sentinel — port 8250 times out there.

---

## PYTHONPATH — Critical, Do Not Change

```
PYTHONPATH=/mnt/shanebrain-raid/pulsar-sentinel/src:/mnt/shanebrain-raid/pulsar-sentinel
```

Both `src/` AND the project root must be in PYTHONPATH. `config/` lives at project root, not inside `src/`. The systemd service sets this correctly — do not move files or change paths without updating the service file.

**`src/__init__.py` has NO eager imports.** Do not add any. Eager imports there break cold start.

---

## Public URLs

| URL | What |
|---|---|
| https://sentinel.shanebrain.cloud | Live product — Cloudflare tunnel → Pi:8250 |
| https://thebardchat.github.io/pulsar_sentinel/ | GitHub Pages mirror (index.html at repo root) |

---

## API Endpoints

| Endpoint | Auth | Notes |
|---|---|---|
| `GET /` | none | Serves `landing.html` |
| `GET /app` | none | Jinja2 app template |
| `GET /api/v1/health` | **none** | `{"status":"healthy","pqc_available":true}` — point uptime monitors here |
| `GET /api/v1/status` | JWT or service key | User posture: role, tier, PTS, pqc_available |
| `POST /api/v1/auth/nonce` | none | MetaMask auth step 1 |
| `POST /api/v1/auth/verify` | none | MetaMask auth step 2 → JWT |
| `POST /api/v1/keys/generate` | JWT/key | ML-KEM keypair |
| `POST /api/v1/encrypt` | JWT/key | ML-KEM or AES encrypt |
| `POST /api/v1/decrypt` | JWT/key | Decrypt |
| `GET /api/v1/asr/{user_id}` | JWT/key | Agent State Records |
| `GET /api/v1/pts/{user_id}` | JWT/key | Pulsar Trust Score |
| `POST /api/v1/billing/checkout` | JWT/key | Stripe checkout |
| `POST /api/v1/billing/webhook` | Stripe sig | Webhook — do not add auth middleware here |

---

## Auth — Two Paths

### 1. MetaMask JWT (user-facing)
- User signs a nonce with MetaMask → gets JWT
- **JWT expires in 24 hours** — cannot be vaulted, cannot be reused
- `Authorization: Bearer <jwt>`

### 2. Internal Service Key (automation, MCP, Pi tools)
- `Authorization: Bearer $PULSAR_SERVICE_KEY`
- Set via `PULSAR_SERVICE_KEY` env var — **required, no default** (fail-closed since #12). Value lives in the vault, never in code.
- Node agents send the same value as `SENTINEL_KEY` (from `/etc/pulsar-sentinel/agent.env`, or `SENTINEL_KEY_FILE` for docker secrets)
- Permanent, Admin role, no MetaMask needed
- **Use this for all MCP tools, scripts, and internal calls**

---

## MCP Tools — Correct Implementation

```python
# Health — no auth, use for uptime monitors
@mcp.tool()
async def shanebrain_sentinel_health() -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:8250/api/v1/health", timeout=5)
        return r.json()

# Status — internal service key, NOT a vaulted JWT
@mcp.tool()
async def shanebrain_sentinel_status() -> dict:
    headers = {"Authorization": f"Bearer {os.environ['PULSAR_SERVICE_KEY']}"}
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:8250/api/v1/status", headers=headers, timeout=5)
        return r.json()
```

Use `localhost:8250` from the Pi. From other mesh nodes, use `http://100.67.120.6:8250`. **Never `100.81.70.117:8250`** — that's Pulsar Windows, Sentinel is not there.

---

## Stripe (Live Mode)

| Key | Where |
|---|---|
| `STRIPE_SECRET_KEY` | `.env` (sk_live_...) |
| `STRIPE_WEBHOOK_SECRET` | `.env` (whsec_...) |
| `STRIPE_PRICE_LEGACY` | `.env` — $10.99/mo |
| `STRIPE_PRICE_SENTINEL` | `.env` — $24.99/mo |
| `STRIPE_PRICE_GUILD` | `.env` — $49.99/mo |

---

## Banner / Ad

- `quantum-banner.gif` v5 — 24 frames @ 65ms, 1.8MB
- 3 ASCII faces formed by cycling numbers/symbols
- 6 eyes, each flashes on its own frame (frames 2,6,11,15,19,22) — anatomically correct, partially closed, never all at once
- Hosted at `raw.githubusercontent.com/thebardchat/pulsar_sentinel/main/quantum-banner.gif`
- **All 43 public repos already have the ad** in their README pointing to this URL
- Updating the GIF updates all 43 repos' banners simultaneously
- Script: `scripts/gen_quantum_faces.py`

---

## GitHub

- Repo: `thebardchat/pulsar_sentinel`, branch `main`
- Commit direct to main — no branches
- Latest: `5b24a83` — live Stripe, landing page rewrite, internal service key auth

---

## Security Stack

1. **ML-KEM-768** (CRYSTALS-Kyber) — NIST-approved lattice-based KEM, liboqs-python v0.15.0
2. **AES-256-GCM** — symmetric encryption
3. **HKDF** — key derivation from KEM shared secret
4. **HybridEncryptor** — ML-KEM encapsulation → HKDF → AES-256-GCM
5. `pqc_available: true` in health response = liboqs loaded and real ML-KEM active

---

## PTS Algorithm

`(quantum_risk × 0.4) + (access_violations × 0.3) + (rate_limits × 0.2) + (signature_failures × 0.1)`

Tiers: Safe < 50, Caution 50–149, Critical ≥ 150

---

## Rules

- Do not change port from 8250
- Do not add imports to `src/__init__.py`
- Do not commit `.env`
- Do not create branches — commit directly to main
- Do not touch `ui/templates/index.html` (Jinja2 extends base.html) — it is NOT the landing page
- `landing.html` at project root is the marketing page served at `/`
- `index.html` at project root is the GitHub Pages copy
- Show result on one file before applying changes to all files
- Sentinel runs on the Pi — verify with `curl localhost:8250/api/v1/health` before touching services
