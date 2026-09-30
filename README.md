<div align="center"><img src=".github/assets/banner.png" alt="Pulsar Sentinel" width="100%"></div>

> **Try Claude free for 2 weeks** — the AI powering this ecosystem. [Start your free trial →](https://claude.ai/referral/4fAMYN9Ing)

![social card](assets/social-card.jpg)

[![Constitution](https://img.shields.io/badge/Constitution-ShaneTheBrain-blue)](https://github.com/thebardchat/constitution)
[![Status](https://img.shields.io/badge/Status-LIVE%20on%20Pi%205-brightgreen)](https://github.com/thebardchat/pulsar_sentinel)
[![PQC](https://img.shields.io/badge/PQC-ML--KEM--768%20%2B%20AES--256-purple)](https://github.com/thebardchat/pulsar_sentinel)
[![Cluster](https://img.shields.io/badge/Cluster-6%20Nodes-blue)](https://github.com/thebardchat/shanebrain-core)
[![Sponsor](https://img.shields.io/badge/Sponsor-thebardchat-ea4aaa?logo=github-sponsors)](https://github.com/sponsors/thebardchat)
[![Hugging Face](https://img.shields.io/badge/HuggingFace-thebardchat-yellow?logo=huggingface)](https://huggingface.co/thebardchat)

# PULSAR SENTINEL

> **Try Claude free for 2 weeks** — the AI behind this entire ecosystem. [Start your free trial →](https://claude.ai/referral/4fAMYN9Ing)

---



**Post-Quantum Cryptography Security Framework — LIVE on Port 8250**

A production-grade blockchain-integrated security layer providing quantum-resistant encryption (ML-KEM-768/1024), immutable audit trails (Agent State Records with Merkle proofs), real-time threat scoring (PTS), and role-based access control. Protecting the ShaneBrain cluster and the 800M Windows users facing security update deprecation.

**Currently protecting:** ShaneBrain ecosystem — 44 MCP tools, the 6-node Docker Swarm cluster (Pi 5 + alaska, biloxi, gulfshores, mexico, neworleans), Mega Dashboard, Angel Cloud Gateway, Weaviate vector DB.

This project operates under the [ShaneTheBrain Constitution](https://github.com/thebardchat/constitution/blob/main/CONSTITUTION.md).

---

## How It Works — Animated Walkthrough

<div align="center"><img src=".github/assets/how-it-works.gif" alt="Pulsar Sentinel animated walkthrough: a node heartbeat with a valid key gets accepted, a stale key gets rejected fail-closed, data gets locked with ML-KEM + AES-256, and the live PTS trust score stays in the safe tier" width="100%"></div>

A node checks in with its key → a valid key is accepted and logged; a stale/missing key is **rejected outright (fail closed)**, never silently waved through. Sensitive data gets locked with quantum-resistant hybrid encryption before it's stored. A live trust score (PTS) tracks the whole cluster's health in real time. See the [Security Diagnostic](#security-diagnostic--how-its-supposed-to-work-vs-how-its-actually-running) below for a real incident where this exact fail-closed behavior mattered.

---


## Live Status

| Endpoint | Status |
|----------|--------|
| Health | `curl http://localhost:8250/api/v1/health` |
| Swagger Docs | `http://100.67.120.6:8250/docs` |
| Dashboard | `http://100.67.120.6:8250/dashboard` |

---

## Security Diagnostic — How It's Supposed to Work vs. How It's Actually Running

_Diagnostic run 2026-09-30. Snapshot in time — re-verify live before trusting old numbers here._

### How it's supposed to work, in plain terms

Think of Pulsar Sentinel as the front-desk guard for the whole ShaneBrain cluster:

- Every machine (the Pi, alaska, biloxi, gulfshores, mexico, neworleans) runs a small **agent** that checks in every ~20–30 seconds ("I'm alive, nothing's wrong") — like a guard radioing in on a schedule.
- To check in, an agent has to show a **secret key** (`SENTINEL_KEY` / `PULSAR_SERVICE_KEY`). No key, or the wrong key, and the guard shack turns you away (`401 Unauthorized`). This is "fail closed" — when in doubt, lock the door, don't wave people through.
- Sentinel also locks up sensitive data with **quantum-resistant encryption (ML-KEM)** — a vault a future quantum computer still can't pick — and keeps a running **trust score (PTS)** that turns red if something starts acting suspicious (bad logins, rate-limit abuse, etc).
- Every change to Sentinel's own code has to pass automated tests and get a human click to merge on GitHub — so a bad change can't sneak into the guard's rulebook unnoticed.

### How it was actually running (found + fixed 2026-09-29/30)

On 2026-09-23 the master key was rotated as a security fix (closing [issue #7](https://github.com/thebardchat/pulsar_sentinel/issues/7) — the server used to accept a hardcoded default key if none was set, like a guard shack whose backup password was printed in the manual). The server-side fix was correct, but nobody had told the guards on patrol: every caller — the MCP security tools, the Bouncer watchdog, the nightly encrypted-memory backup, the mindmap tool, and every cluster-node agent — kept showing up with the *old* key.

Because the server was now doing the right thing (fail closed instead of quietly letting the old key through), every one of those callers got turned away with 401s — silently, with no alert firing. In practice that meant:

- The nightly quantum-encrypted memory backup failed **6 nights straight** (Sep 23–29) with nobody notified.
- The `shanebrain_sentinel_health` / `shanebrain_sentinel_status` MCP tools were broken.
- The Bouncer watchdog and the memory-vault sync script were both running on a rejected key.

**Fixed the night of 2026-09-29** (Claude Code session on pulsar00100, diagnosing a swarm/cluster issue): rotated the correct key out to every caller — 4 systemd agents, 2 API replicas, and the Docker Swarm secret (`sentinel_key`) — verified the old key now gets rejected everywhere and the new one works, rebuilt the MCP server, and manually re-ran the missed backup. The permanent fix (agents now fail closed instead of ever falling back to a public default key) shipped as [PR #15](https://github.com/thebardchat/pulsar_sentinel/pull/15), merged the same night.

### Confirmed live right now

| Check | Result |
|---|---|
| `pulsar-sentinel.service` (Pi) | active, up 1 week |
| `GET /api/v1/health` | `healthy`, `pqc_available: true` |
| `GET /api/v1/status` | `operational`, role `ADMIN`, PTS `0.0` (safe tier) |
| Swarm `sentinel-agent` service | 5/5 replicas running (alaska, biloxi, gulfshores, mexico, neworleans) on the rotated key |
| Test suite | 126/126 passing, 48% coverage |
| CI on `main` | green |

**Still open — not yet closed, needs Shane's click:** a docs-sync PR ([#16](https://github.com/thebardchat/pulsar_sentinel/pull/16), draft) recording this fix in the repo's own audit trail is waiting on a human merge; the Discord webhook that got printed in that fix session's transcript still needs rotating; two older repo clones (on neworleans and gulfshores) are still on May-30 code and need a `git pull`.

---

## Infrastructure

Runs on the ShaneBrain cluster — Pi 5 controller (Docker Swarm manager) + 5 Linux worker nodes (alaska, biloxi, gulfshores, mexico, neworleans) running a `sentinel-agent` replica each, plus `pulsar00100` as a separate Windows utility node.

| Component | Details |
|-----------|---------|
| **Compute** | Raspberry Pi 5, 16GB RAM |
| **Chassis** | Pironman 5-MAX by Sunfounder |
| **Storage** | RAID 1 — 2x WD Blue SN5000 2TB NVMe (mdadm) |
| **Core Path** | `/mnt/shanebrain-raid/shanebrain-core/` |
| **Backup** | 8TB Seagate USB — restic encrypted, daily |
| **Network** | Tailscale VPN across all devices |
| **OS** | Raspberry Pi OS (Debian Trixie, arm64) |

---

## Overview

PULSAR SENTINEL implements a three-tier security architecture:

| Tier | Name | Features | Price |
|------|------|----------|-------|
| 1 | **Sentinel Core** | ML-KEM PQC, 10M ops/month, Daily ASR | $16.99/mo |
| 2 | **Legacy Builder** | AES-256, 5M ops/month, Weekly ASR | $10.99/mo |
| 3 | **Autonomous Guild** | Full PQC + Smart Contracts, Unlimited | $29.99/mo |

## Security Features

### Post-Quantum Cryptography
- **ML-KEM-768/1024**: NIST-approved lattice-based key encapsulation
- **Hybrid Encryption**: ML-KEM + AES-256-GCM for defense in depth
- **Key Rotation**: ML-KEM keys rotate on a **90-day** default interval (`KEY_ROTATION_DAYS` / `key_rotation_days` / `DEFAULT_KEY_ROTATION_DAYS`), enforced by `KeyRotationManager` via `needs_rotation()` / `rotate()` (caller-driven; not a background timer). Retired keys stay usable for decapsulation during a **7-day** grace period.

### Classical Cryptography (Legacy)
- **AES-256-CBC**: HMAC-SHA256 authenticated encryption
- **ECDSA secp256k1**: Polygon-compatible signatures
- **TLS 1.3**: Enforced transport security

### Blockchain Integration
- **Polygon Network**: Mainnet and Amoy testnet support
- **MetaMask Auth**: Wallet-based passwordless authentication
- **Immutable Logging**: ASR records with Merkle proofs

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/thebardchat/pulsar_sentinel.git
cd pulsar_sentinel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env
# Edit .env with your configuration
```

### Running the Server

```bash
# Development mode
python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8250

# Production mode
python -m api.server
```

### API Documentation

Once running, access the API docs at:
- Swagger UI: http://localhost:8250/docs
- ReDoc: http://localhost:8250/redoc

## API Endpoints

### Authentication
```bash
# Request nonce
POST /api/v1/auth/nonce
{"wallet_address": "0x..."}

# Verify signature
POST /api/v1/auth/verify
{"wallet_address": "0x...", "signature": "0x...", "nonce": "..."}
```

### Cryptography
```bash
# Generate keys
POST /api/v1/keys/generate?algorithm=hybrid

# Encrypt data
POST /api/v1/encrypt
{"data": "base64...", "algorithm": "hybrid", "public_key": "base64..."}

# Decrypt data
POST /api/v1/decrypt
{"ciphertext": "base64...", "algorithm": "hybrid", "secret_key": "base64..."}
```

### Status & Monitoring
```bash
# Health check (no auth)
GET /api/v1/health

# System status
GET /api/v1/status

# Get PTS score
GET /api/v1/pts/{user_id}

# Get ASR records
GET /api/v1/asr/{user_id}
```

## Discord Community

Join the PULSAR SENTINEL Discord for real-time threat alerts and community support.

**Bot Commands:**
| Command | Description |
|---------|-------------|
| `!help` | Show all commands |
| `!status` | System health check |
| `!pricing` | View subscription tiers |
| `!pts` | PTS formula & thresholds |
| `!docs` | Documentation links |
| `!invite` | Get Discord invite link |

**Automated Features:**
- Push notifications on every commit to `main` (via GitHub Actions webhook)
- Welcome messages for new members
- Real-time PTS threat tier change alerts

```bash
# Run the Discord bot
python scripts/run_discord_bot.py
```

## Architecture

```
pulsar_sentinel/
├── src/
│   ├── core/           # Cryptographic engines
│   │   ├── pqc.py      # ML-KEM + hybrid encryption
│   │   ├── key_rotation.py  # KeyRotationPolicy + KeyRotationManager
│   │   ├── legacy.py   # AES-256, ECDSA, TLS
│   │   └── asr_engine.py  # Agent State Records
│   ├── blockchain/     # Polygon integration
│   │   ├── polygon_client.py
│   │   ├── smart_contract.py
│   │   └── event_logger.py
│   ├── governance/     # Self-governance
│   │   ├── rules_engine.py   # RC codes
│   │   ├── pts_calculator.py # Threat scoring
│   │   └── access_control.py # RBAC
│   ├── discord_bot/    # Discord community bot
│   │   ├── bot.py      # Main bot + events
│   │   ├── commands.py # !help, !status, !pricing, etc.
│   │   ├── embeds.py   # Themed embed builders
│   │   └── alerts.py   # PTS threat alert system
│   └── api/           # REST API
│       ├── server.py
│       ├── auth.py
│       └── routes.py
├── tests/             # Comprehensive test suite
├── config/            # Configuration
├── scripts/           # Deployment scripts
└── docs/              # Documentation
```

## Governance Rules (RC Codes)

| Code | Rule | Description |
|------|------|-------------|
| RC 1.01 | Signature Required | All requests require encryption signature |
| RC 1.02 | Heir Transfer | 90-day unresponsive triggers heir transfer |
| RC 2.01 | Three-Strike Rule | 3 violations = temporary ban |
| RC 3.02 | Transaction Fallback | Auto-fallback to Gryphon on TX failure |

## Points Toward Threat Score (PTS)

```
PTS = (quantum_risk * 0.4) + (access_violations * 0.3) +
      (rate_limit_hits * 0.2) + (signature_failures * 0.1)

Tier 1 (Safe):     PTS < 50   [Green]
Tier 2 (Caution):  PTS 50-149 [Yellow]
Tier 3 (Critical): PTS >= 150 [Red]
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m pqc          # PQC tests
pytest -m blockchain   # Blockchain tests
pytest -m governance   # Governance tests
```

## Configuration

Key environment variables (see `.env.template`):

| Variable | Description | Default |
|----------|-------------|---------|
| `POLYGON_NETWORK` | mainnet or testnet | testnet |
| `PQC_SECURITY_LEVEL` | 768 or 1024 | 768 |
| `KEY_ROTATION_DAYS` | Key rotation interval | 90 |
| `RATE_LIMIT_DEFAULT` | Requests per minute | 5 |
| `STRIKE_THRESHOLD` | Strikes before ban | 3 |
| `PULSAR_SERVICE_KEY` | Internal/admin Bearer key (required when `API_DEBUG=false`) | none (fail-closed) |
| `SENTINEL_KEY` | Node agent Bearer key (must match server `PULSAR_SERVICE_KEY`; no built-in default) | none (fail-closed) |
| `SENTINEL_KEY_FILE` | Alternate agent key path (e.g. docker secret); used when `SENTINEL_KEY` unset | none |
| `API_DEBUG` | Debug mode; skips service-key startup gate when true | false |
| `DISCORD_BOT_TOKEN` | Discord bot token | |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL | |

## Requirements

- Python 3.11+
- liboqs-python (for PQC operations)
- Web3.py (for blockchain)
- FastAPI (for REST API)

## Part of the Angel Cloud Ecosystem

| Project | Repo | Status |
|---------|------|--------|
| Constitution | thebardchat/constitution | Active |
| ShaneBrain Core | thebardchat/shanebrain-core | Active |
| Pulsar Sentinel | thebardchat/pulsar_sentinel | Active |
| Loudon/DeSarro | thebardchat/loudon-desarro | Active |

## Credits

| Partner | Contribution |
|---------|-------------|
| [Claude by Anthropic](https://claude.ai) | Co-built ecosystem infrastructure |
| [Raspberry Pi 5](https://raspberrypi.com) | Affordable local compute |
| [Pironman 5-MAX by Sunfounder](https://pironman.com) | RAID-capable NVMe chassis |

## License

MIT License - See LICENSE for details.

---

Built with Claude (Anthropic) · Runs on Raspberry Pi 5 + Pironman 5-MAX

*"Build it once. Secure it forever."*


---

## Support This Work

If what I'm building matters to you — local AI for real people, tools for the left-behind — here's how to help:

- **[Sponsor me on GitHub](https://github.com/sponsors/thebardchat)**
- **[Buy the book](https://www.amazon.com/Probably-Think-This-Book-About/dp/B0GT25R5FD)** — *You Probably Think This Book Is About You*
- **Star the repos** — visibility matters for projects like this

Built by **Shane Brazelton** · Co-built with **Claude** (Anthropic) · Hazel Green, Alabama

---

<div align="center">

*Part of the [ShaneBrain Ecosystem](https://github.com/thebardchat) · Built under the [Constitution](https://github.com/thebardchat/constitution)*

</div>
