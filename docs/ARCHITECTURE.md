# Architecture Documentation

## System Overview

PULSAR SENTINEL is a three-tier security framework providing:
- Post-quantum cryptographic operations
- Blockchain-based immutable audit logging
- Self-governance rule enforcement

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   FastAPI   │  │  MetaMask   │  │    Rate Limiting        │  │
│  │   Server    │  │    Auth     │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Governance Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Rules     │  │    PTS      │  │    Access Control       │  │
│  │   Engine    │  │ Calculator  │  │       (RBAC)            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Core Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  PQC Engine │  │   Legacy    │  │    ASR Engine           │  │
│  │  (ML-KEM)   │  │   Crypto    │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Blockchain Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Polygon   │  │   Smart     │  │    Event Logger         │  │
│  │   Client    │  │  Contract   │  │   (Merkle Proofs)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Layer

#### FastAPI Server (`api/server.py`)
- REST API with OpenAPI documentation
- Lifespan management for service initialization
- Global exception handling
- CORS middleware

#### MetaMask Auth (`api/auth.py`)
- Wallet signature verification
- JWT token issuance
- Session management
- Nonce generation and validation

#### Routes (`api/routes.py`)
- `/auth/*`: Authentication endpoints
- `/encrypt`, `/decrypt`: Crypto operations
- `/status`, `/health`: Monitoring
- `/asr/*`: Audit record access
- `/pts/*`: Threat score access

### 2. Governance Layer

#### Rules Engine (`governance/rules_engine.py`)
```
RC Codes:
├── RC 1.01: Signature Required
├── RC 1.02: Heir Transfer (90-day)
├── RC 2.01: Three-Strike Rule
└── RC 3.02: Gryphon Fallback
```

#### PTS Calculator (`governance/pts_calculator.py`)
```
PTS Formula:
├── quantum_risk_factor × 0.4
├── access_violation_count × 0.3
├── rate_limit_violations × 0.2
└── signature_failures × 0.1

Tiers:
├── Safe (Green): < 50
├── Caution (Yellow): 50-149
└── Critical (Red): ≥ 150
```

#### Access Control (`governance/access_control.py`)
```
Roles:
├── NONE (0): No access
├── USER (1): Basic operations
├── SENTINEL (2): Enhanced access
└── ADMIN (3): Full control

Tiers:
├── Legacy Builder: $10.99/mo, 5M ops
├── Sentinel Core: $16.99/mo, 10M ops
└── Autonomous Guild: $29.99/mo, Unlimited
```

### 3. Core Layer

#### PQC Engine (`core/pqc.py`)
```
Algorithms:
├── ML-KEM-768: NIST Level 3
├── ML-KEM-1024: NIST Level 5
└── Hybrid: ML-KEM + AES-256-GCM

Key Operations:
├── generate_keypair(): < 500ms
├── encapsulate(): < 50ms
└── decapsulate(): < 50ms
```

#### Legacy Crypto (`core/legacy.py`)
```
Algorithms:
├── AES-256-CBC + HMAC-SHA256
├── ECDSA secp256k1
└── TLS 1.3

Key Derivation:
└── PBKDF2-SHA256 (600,000 iterations)
```

#### ASR Engine (`core/asr_engine.py`)
```
Agent State Record:
├── asr_id: Unique identifier
├── timestamp: ISO8601
├── agent_id: User wallet
├── action: Operation type
├── threat_level: 1-5
├── pqc_status: safe/warning/critical
├── signature: SHA-256 hash
└── metadata: Additional data

Batching:
├── Max batch size: 50
├── Merkle tree proofs
└── Blockchain submission
```

### 4. Blockchain Layer

#### Polygon Client (`blockchain/polygon_client.py`)
```
Networks:
├── Mainnet: Chain ID 137
└── Testnet (Amoy): Chain ID 80002

Operations:
├── connect(): Initialize Web3
├── send_transaction(): Sign & submit
├── get_balance(): Query MATIC
└── wait_for_confirmations(): 2 blocks
```

#### Smart Contract (`blockchain/smart_contract.py`)
```
Governance Contract:
├── Roles: getRole(), grantRole()
├── Strikes: getStrikes(), issueStrike()
├── Rate Limits: getRateLimit(), setRateLimit()
├── Activity: recordActivity(), getLastActivity()
└── Events: logSecurityEvent()
```

#### Event Logger (`blockchain/event_logger.py`)
```
Batch Processing:
├── Accumulate ASRs
├── Build Merkle tree
├── Submit to blockchain
└── Generate proofs

Verification:
├── verify_merkle_proof()
└── verify_asr_on_chain()
```

## Data Flow

### Authentication Flow
```
1. Client → POST /auth/nonce → Server
2. Server → Generate nonce → Client
3. Client → Sign with MetaMask
4. Client → POST /auth/verify → Server
5. Server → Verify signature → Issue JWT
6. Client → Use JWT for requests
```

### Encryption Flow
```
1. Client → POST /encrypt (with public_key)
2. Server → Check auth + rate limit
3. Server → ML-KEM encapsulate
4. Server → AES-256-GCM encrypt
5. Server → Create ASR record
6. Server → Return ciphertext
```

### ASR Logging Flow
```
1. Security event occurs
2. Create ASR with signature
3. Add to pending batch
4. When batch full:
   a. Build Merkle tree
   b. Submit to blockchain
   c. Cache proof data
5. Return Merkle proof
```

## Security Boundaries

```
┌────────────────────────────────────────────────────┐
│                    Public Zone                      │
│  • /health endpoint                                 │
│  • /auth/nonce (rate limited)                      │
└────────────────────────────────────────────────────┘
                         │
                    [Auth Required]
                         │
                         ▼
┌────────────────────────────────────────────────────┐
│                 Authenticated Zone                  │
│  • /encrypt, /decrypt                              │
│  • /status                                         │
│  • /asr/{own_id}                                   │
│  • /pts/{own_id}                                   │
└────────────────────────────────────────────────────┘
                         │
                    [Role: ADMIN]
                         │
                         ▼
┌────────────────────────────────────────────────────┐
│                    Admin Zone                       │
│  • /asr/{any_id}                                   │
│  • /pts/{any_id}                                   │
│  • User management                                 │
│  • Strike reset                                    │
└────────────────────────────────────────────────────┘
```

## Memory Management

Target: 7.4GB RAM systems

Optimizations:
- Lazy loading of PQC engine
- Batch size limits (50 ASRs)
- LRU caching for settings
- Stream processing for large payloads
- Periodic cleanup of expired data

## Error Handling

```
Exception Hierarchy:
├── ValueError: Input validation
├── PermissionError: Access denied
├── RateLimitExceeded: Rate limit hit
├── ConnectionError: Network issues
└── RuntimeError: System errors

Recovery:
├── Retry with backoff (blockchain)
├── Graceful degradation (PQC → simulated)
└── Circuit breaker (external services)
```

## Discord Integration Layer

### Discord Bot (`discord_bot/`)

Standalone community bot running as a separate lightweight process (~30-50MB RAM).

```
Discord Bot Architecture:
├── bot.py          # Main bot, on_ready, on_member_join (welcome embeds)
├── commands.py     # Cog: !help, !status, !pricing, !pts, !docs, !invite
├── embeds.py       # Themed embed builders (cyan/magenta/gold/green/red)
└── alerts.py       # Async queue + polling cog for PTS threat alerts
```

#### Bot Commands
```
!help    → Shows all commands (embeds.help_embed)
!status  → Hits /api/v1/health, shows online/offline + PQC status
!pricing → Reads TIER_CONFIGS from constants.py, shows all 3 tiers
!pts     → Shows PTS formula weights + tier thresholds
!docs    → Links to landing page, GitHub, API docs
!invite  → Shows Discord server invite link
```

#### Threat Alert System
```
Alert Flow:
1. Any part of the app calls push_alert(pts_score, tier, details)
2. Alert added to asyncio.Queue
3. AlertsCog polls queue every 5 seconds
4. Sends themed embed to configured alerts channel
```

### GitHub Actions Webhook (`.github/workflows/discord-notify.yml`)
- Triggers on push to `main`
- Sends cyan-themed Discord embed with commit info
- Zero dependencies (curl only)
- Requires `DISCORD_WEBHOOK_URL` GitHub Actions secret

## Future Extensions

1. **Multi-chain Support**
   - Ethereum mainnet
   - Arbitrum
   - Base

2. **HSM Integration**
   - Hardware key storage
   - PKCS#11 support

3. **Metrics & Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alert manager integration
