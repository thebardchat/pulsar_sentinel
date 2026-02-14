# CLAUDE.md - Pulsar Sentinel

> **Last Updated:** February 14, 2026
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
```

---

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
```

---

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
```

---

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

---

## Contact

**Owner:** Shane Brazelton
**Company:** SRM Dispatch (Alabama)
**Ko-fi:** ko-fi.com/shanebrain
**Discord:** discord.gg/xbHQZkggU7
