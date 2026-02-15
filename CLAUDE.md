# CLAUDE.md - Pulsar Sentinel

> **Last Updated:** February 15, 2026
> **Version:** 3.0
> **Owner:** Shane Brazelton (SRM Dispatch, Alabama)
> **Repo:** github.com/thebardchat/pulsar_sentinel

---

## Project Overview

**Pulsar Sentinel** is a production-grade Post-Quantum Cryptography (PQC) security framework for the Angel Cloud ecosystem. It provides quantum-resistant encryption (ML-KEM-768/1024), immutable blockchain audit trails (Polygon), AI-driven threat scoring (PTS), and self-governance rule codes.

**Mission:** Protect 800 million Windows users losing security updates with affordable, local-first security infrastructure.

---

## Quick Start

```bash
<<<<<<< HEAD
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
copy .env.template .env
# Edit .env with your values

# Run the server
uvicorn src.api.server:app --host 0.0.0.0 --port 8000

# Run Discord bot (standalone)
python scripts/run_discord_bot.py

# Run tests
pytest

# Windows launcher (does everything)
PULSAR_SENTINEL.bat
=======
# All services now run on the Raspberry Pi 5 (shanebrain-1)
# SSH into Pi from anywhere:
ssh shanebrain@100.67.120.6

# Start Weaviate (from RAID)
cd /mnt/shanebrain-raid/shanebrain-core/weaviate-config
docker-compose up -d

# Run ShaneBrain Agent
python /mnt/shanebrain-raid/shanebrain-core/langchain-chains/shanebrain_agent.py

# Run Angel Cloud CLI
python /mnt/shanebrain-raid/shanebrain-core/langchain-chains/angel_cloud_cli.py
>>>>>>> c145ef4 (Update CLAUDE.md v3.0 for Pi 5 reality)
```

---

<<<<<<< HEAD
## File Structure

```
pulsar_sentinel/
├── CLAUDE.md                    # This file
├── README.md                    # Project documentation
├── LICENSE                      # MIT License
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── pytest.ini                   # Test configuration
├── .env.template                # Environment variable template
├── .gitignore                   # Git ignore rules
├── PULSAR_SENTINEL.bat          # Windows launcher
├── landing.html                 # Marketing landing page (standalone)
│
├── src/
│   ├── api/
│   │   ├── server.py            # FastAPI application + Jinja2 UI routes
│   │   ├── auth.py              # MetaMask wallet authentication
│   │   └── routes.py            # API endpoint definitions
│   ├── core/
│   │   ├── pqc.py               # ML-KEM + hybrid encryption engine
│   │   ├── legacy.py            # AES-256, ECDSA, TLS classical crypto
│   │   └── asr_engine.py        # Agent State Records (audit trail)
│   ├── blockchain/
│   │   ├── polygon_client.py    # Polygon network integration
│   │   ├── smart_contract.py    # Governance smart contract interface
│   │   └── event_logger.py      # Blockchain event logging
│   ├── governance/
│   │   ├── rules_engine.py      # RC codes enforcement
│   │   ├── pts_calculator.py    # Points Toward Threat scoring
│   │   └── access_control.py    # RBAC + rate limiting
│   └── discord_bot/
│       ├── bot.py               # Discord bot initialization
│       ├── commands.py          # Bot commands (!help, !status, !pricing, !pts, !docs, !invite)
│       ├── embeds.py            # Message formatting
│       └── alerts.py            # Threat alert system
│
├── ui/
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── base.html            # Base layout (nav, footer)
│   │   ├── index.html           # Home/feature overview
│   │   ├── login.html           # MetaMask wallet auth
│   │   ├── dashboard.html       # User dashboard (stats, deployments, security)
│   │   ├── wallet.html          # Wallet management
│   │   ├── mining.html          # Mining dashboard
│   │   ├── marketplace.html     # NFT/MINT marketplace
│   │   └── shanebrain.html      # SHANEBRAIN AI interface
│   └── static/
│       ├── css/
│       │   └── quantum-theme.css  # Complete design system (30KB)
│       └── js/
│           ├── auth.js            # MetaMask authentication flow
│           ├── dashboard.js       # Dashboard data management
│           ├── landing.js         # Landing page modals
│           ├── marketplace.js     # Marketplace filtering/trading
│           ├── mining.js          # Mining stats/charts
│           ├── notifications.js   # Toast notification system
│           ├── quantum-effects.js # Particle background engine
│           ├── shanebrain.js      # AI panel management
│           ├── wallet.js          # Wallet operations
│           └── wallet-connect.js  # Web3 integration, JWT auth
│
├── tests/                       # Pytest test suite
├── config/                      # Configuration files
├── docs/                        # Documentation
│   ├── RAG.md                   # RAG knowledge base (659 lines)
│   ├── API.md                   # API endpoint docs
│   ├── ARCHITECTURE.md          # System architecture
│   ├── DEPLOYMENT.md            # Deployment guide
│   ├── SECURITY.md              # Security specifications
│   └── PATENT.md                # Patent documentation
├── patent_docs/                 # Patent-related documents
├── scripts/                     # Utility scripts
│   └── run_discord_bot.py       # Standalone bot launcher
├── .github/workflows/           # CI/CD + Discord notification
└── coverage_html/               # Test coverage reports
=======
## Current Status (February 15, 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama LLM | ✅ Running | v0.13+, models: llama3.2:1b, llama3.2:3b, nomic-embed-text |
| Weaviate | ✅ Connected | Docker container, 5 collections active |
| Docker | ✅ Running | shanebrain-weaviate, open-webui, portainer |
| Discord Bot | ✅ Running | v5.4 with Weaviate knowledge harvesting |
| Social Bot | ✅ Running | Facebook automation + comment harvesting |
| Arcade Bot | ✅ Running | Angel Arcade economy/casino bot |
| Security | ✅ Hardened | UFW, fail2ban, unattended-upgrades, restic backups |

**Platform:** Raspberry Pi 5 — 16GB RAM, RAID 1 (2x 2TB NVMe), 8TB external backup

---

## Project Vision

**ShaneBrain** = Central AI orchestrator for the entire ecosystem:
- **Angel Cloud** - Mental wellness platform (named for daughter-in-law Angel)
- **Pulsar AI** - Blockchain security layer (eventually Pulsar Sentinel)
- **Legacy AI** - Personal "TheirNameBrain" for each user's family legacy
- **LogiBot** - Business automation for SRM Dispatch

**Mission:** Serve 800 million Windows users losing security updates with affordable, secure AI infrastructure.

---

## Infrastructure

### Primary Server: Raspberry Pi 5 (shanebrain-1)
- **Hardware:** Pi 5, 16GB RAM, Pironman 5-MAX case
- **Storage:** RAID 1 (2x WD Blue SN5000 2TB NVMe) at `/mnt/shanebrain-raid/`
- **Backup:** 8TB Seagate USB at `/media/shane/ANGEL_CLOUD/` — restic encrypted, 3am daily
- **Network:** Wired ethernet, Tailscale VPN (100.67.120.6)
- **OS:** Raspberry Pi OS (Debian Trixie, arm64)

### Tailscale Network
| Device | Tailscale IP | Type |
|--------|-------------|------|
| shanebrain-1 | 100.67.120.6 | Pi 5 (primary server) |
| pulsar00100 | 100.81.70.117 | Windows desktop |
| iphone-13 | 100.86.68.38 | iPhone (mobile) |

### Services (all on Pi)
| Service | Port | Container/Process |
|---------|------|-------------------|
| Ollama | 11434 | Native (systemd) |
| Weaviate | 8080/50051 | Docker: shanebrain-weaviate |
| Open WebUI | 3000 | Docker: open-webui |
| Portainer CE | 9000 | Docker: portainer |
| Social Bot | — | systemd: shanebrain-social |
| Discord Bot | — | Background process |
| Arcade Bot | — | Background process |
| Glances | 61208 | System monitor |

### Weaviate Collections
| Collection | Purpose | Vectorizer |
|------------|---------|------------|
| LegacyKnowledge | Shane's personality, values, family | text2vec_ollama (llama3.2:1b) |
| Conversation | Chat history | text2vec_ollama |
| CrisisLog | Wellness tracking | text2vec_ollama |
| SocialKnowledge | Facebook + Discord interactions | text2vec_ollama |
| FriendProfile | Living profiles of interactors | text2vec_ollama |

---

## File Structure (Pi paths)

```
/mnt/shanebrain-raid/shanebrain-core/
├── .env                          # Credentials (NEVER commit)
├── RAG.md                        # ShaneBrain personality (MOST IMPORTANT)
├── CLAUDE.md                     # Claude Code project context
├── requirements.txt              # Python dependencies
├── bot/
│   └── bot.py                    # Discord bot v5.4 (Weaviate harvesting)
├── arcade/
│   └── arcade_bot.py             # Angel Arcade economy bot
├── social/                       # Facebook social bot (NEW Feb 15)
│   ├── fb_bot.py                 # Main entry (python -m social.fb_bot)
│   ├── facebook_api.py           # Graph API wrapper
│   ├── content_generator.py      # Ollama content + Pollinations images
│   ├── content_calendar.py       # 7-day themed calendar
│   ├── comment_harvester.py      # Poll comments → Weaviate
│   ├── friend_profiler.py        # Build living friend profiles
│   ├── token_exchange.py         # Facebook token management
│   └── config.py                 # Load from root .env
├── scripts/
│   ├── weaviate_helpers.py       # Weaviate CRUD (all 5 collections)
│   ├── setup_weaviate_schema.py  # Schema creation
│   ├── import_rag_to_weaviate.py # RAG ingestion
│   └── backup.sh                 # Restic backup script
├── systemd/
│   └── shanebrain-social.service # Social bot systemd unit
├── weaviate-config/
│   ├── docker-compose.yml        # Weaviate Docker config
│   └── schemas/                  # JSON schemas
├── langchain-chains/
│   ├── shanebrain_agent.py       # Central agent
│   ├── angel_cloud_cli.py        # Interactive CLI
│   └── crisis_detection_chain.py # Mental health detection
└── planning-system/
    ├── templates/                # Planning templates
    └── active-projects/          # Project data (gitignored)

/mnt/shanebrain-raid/pulsar-sentinel/   # This repo
/mnt/shanebrain-raid/mini-shanebrain/   # DEPRECATED — merged into social/
>>>>>>> c145ef4 (Update CLAUDE.md v3.0 for Pi 5 reality)
```

---

<<<<<<< HEAD
## Architecture

### Security Stack (3 Layers)

1. **Layer 1: Post-Quantum Cryptography** (local, no internet required)
   - ML-KEM-768/1024 lattice-based key encapsulation
   - AES-256-GCM symmetric encryption
   - ECDSA secp256k1 digital signatures
   - Hybrid mode: ML-KEM + AES defense-in-depth

2. **Layer 2: Agent State Records** (local + optional blockchain)
   - Cryptographic signing of all security events
   - Merkle tree batching for efficiency
   - Local SQLite storage (offline capable)
   - Optional Polygon blockchain anchoring

3. **Layer 3: Governance & Threat Scoring** (local)
   - PTS algorithm: `(quantum_risk * 0.4) + (access_violations * 0.3) + (rate_limits * 0.2) + (signature_failures * 0.1)`
   - Tiers: Safe (<50), Caution (50-149), Critical (>=150)
   - Rule Codes: RC 1.01 (Signature Required), RC 1.02 (Heir Transfer), RC 2.01 (Three-Strike), RC 3.02 (Fallback)

### Authentication
- MetaMask wallet-based (zero password)
- JWT session tokens after wallet signature verification
- Web3.js v4.0.3 browser integration

### Subscription Tiers

| Tier | Price | PQC Level | Ops/Month |
|------|-------|-----------|-----------|
| Legacy Builder | $10.99 | AES-256 | 5M |
| Sentinel Core | $16.99 | ML-KEM-768 | 10M |
| Autonomous Guild | $29.99 | ML-KEM-1024 | Unlimited |

---

## API Endpoints

```
POST /api/v1/auth/nonce      - Request authentication nonce
POST /api/v1/auth/verify     - Verify wallet signature
POST /api/v1/encrypt         - Encrypt data with PQC
POST /api/v1/decrypt         - Decrypt data
GET  /api/v1/status          - System status
GET  /api/v1/pts/{user_id}   - Get threat score
GET  /api/v1/asr/{user_id}   - Get audit records
GET  /api/v1/health          - Health check
```

---

## UI Design System

- **Colors:** Quantum Cyan (#00f0ff), Pulsar Magenta (#ff00ff), Matrix Green, Gold
- **Fonts:** Orbitron (display), Rajdhani (body), Share Tech Mono (code)
- **Effects:** Canvas particle background, glow animations, scroll reveals
- **Responsive:** Mobile breakpoints at 1024px, 768px

---

## Discord Bot

Lightweight standalone process (~30-50MB RAM).

| Command | Action |
|---------|--------|
| `!help` | Show all commands |
| `!status` | API health + PQC status |
| `!pricing` | Subscription tiers |
| `!pts` | Explain threat scoring |
| `!docs` | Documentation links |
| `!invite` | Server invite |

**Automated:** Welcome embeds, threat alerts (5s poll), GitHub push notifications via Actions webhook.

---

## Environment Variables

See `.env.template` for full list. Key variables:

```env
POLYGON_NETWORK=testnet
PQC_SECURITY_LEVEL=768
API_PORT=8000
JWT_SECRET_KEY=
DISCORD_BOT_TOKEN=
DISCORD_WEBHOOK_URL=
=======
## Common Commands

```bash
# Services
cd /mnt/shanebrain-raid/shanebrain-core/weaviate-config && docker-compose up -d
docker ps                                    # Check containers
sudo systemctl status shanebrain-social      # Social bot status

# Social Bot
python -m social.fb_bot --verify             # Check Facebook token
python -m social.fb_bot --dry-run            # Preview a post
python -m social.fb_bot --post               # Publish one post
python -m social.fb_bot --harvest            # Poll comments → Weaviate
python -m social.fb_bot --friends            # Show friend profiles

# Ollama
ollama list                                  # Show installed models
ollama run llama3.2:1b                       # Interactive chat

# System
glances                                      # System monitor
sudo ufw status                             # Firewall rules
sudo fail2ban-client status sshd            # Ban list
restic -r /media/shane/ANGEL_CLOUD/shanebrain-backups snapshots  # Backup history

# Weaviate
python /mnt/shanebrain-raid/shanebrain-core/scripts/weaviate_helpers.py  # Collection stats
>>>>>>> c145ef4 (Update CLAUDE.md v3.0 for Pi 5 reality)
```

---

<<<<<<< HEAD
## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# View coverage report
open coverage_html/index.html
```

---

## Key Dependencies

- `liboqs-python` — Post-quantum cryptography (ML-KEM)
- `web3>=6.11.0` — Polygon blockchain integration
- `fastapi>=0.109.0` — REST API + UI serving
- `cryptography>=41.0.0` — Classical crypto (AES, ECDSA)
- `discord.py>=2.3.0` — Discord bot
- `pydantic>=2.5.0` — Data validation

---

## Security Rules

- NEVER commit `.env` files
- NEVER expose private keys or wallet secrets
- Keep repo PRIVATE until production ready
- Security works 100% offline (no mining dependency)
- Private keys never leave the user's device

---

## Part of the Angel Cloud Ecosystem

| Project | Repo | Status |
|---------|------|--------|
| ShaneBrain Core | thebardchat/shanebrain-core | Active |
| Pulsar Sentinel | thebardchat/pulsar_sentinel | Active |
| Loudon/DeSarro | thebardchat/loudon-desarro | Active |
| Mini-ShaneBrain | thebardchat/mini-shanebrain | Active |
=======
## Security

- **UFW Firewall** — default deny incoming, allow SSH + Tailscale (100.64.0.0/10) + LAN
- **fail2ban** — SSH jail: 3 attempts = 24h ban
- **unattended-upgrades** — automatic security patches
- **restic** — encrypted backups to 8TB external, 7 daily/4 weekly/6 monthly, 3am cron
- **Tailscale** — all remote access through VPN, no port forwarding
- Never commit `.env` files
- Crisis logs store metadata only (privacy)

---

## Shane's Development Philosophy

1. **"File structure first"** - Always establish architecture before coding
2. **Action over theory** - Build, don't just plan
3. **Family-first** - All projects serve the family's future
4. **ADHD as superpower** - Parallel processing, rapid context switching
5. **No fluff** - Direct solutions, minimal explanation
6. **Local first** - No cloud dependencies unless explicitly chosen
>>>>>>> c145ef4 (Update CLAUDE.md v3.0 for Pi 5 reality)

---

## Contact

**Owner:** Shane Brazelton
**Company:** SRM Dispatch (Alabama)
<<<<<<< HEAD
**Ko-fi:** ko-fi.com/shanebrain
**Discord:** discord.gg/xbHQZkggU7
=======
**Project:** Angel Cloud Ecosystem
**Mission:** 800 million users. Digital legacy for generations.
>>>>>>> c145ef4 (Update CLAUDE.md v3.0 for Pi 5 reality)
