# Security Documentation

## Threat Model

### Target Adversaries

1. **Quantum Adversaries (2035+)**
   - Threat: Harvest-now-decrypt-later attacks
   - Mitigation: ML-KEM-768/1024 post-quantum encryption
   - Defense: Hybrid encryption (PQC + AES) for defense in depth

2. **Insider Threats**
   - Threat: Privilege escalation, unauthorized access
   - Mitigation: Smart contract verification on blockchain
   - Defense: Role-based access control, audit logging

3. **Replay Attacks**
   - Threat: Reusing old transactions/signatures
   - Mitigation: Nonce and timestamp validation
   - Defense: Short-lived tokens, request signing

4. **Denial of Service**
   - Threat: Brute force, resource exhaustion
   - Mitigation: Rate limiting, adaptive throttling
   - Defense: Per-user and per-endpoint limits

## Cryptographic Primitives

### Post-Quantum (Tier 1)

| Primitive | Algorithm | Security Level |
|-----------|-----------|----------------|
| Key Encapsulation | ML-KEM-768 | NIST Level 3 (~AES-192) |
| Key Encapsulation | ML-KEM-1024 | NIST Level 5 (~AES-256) |
| Symmetric Encryption | AES-256-GCM | 256-bit |
| Key Derivation | HKDF-SHA256 | 256-bit |

### Classical (Tier 2)

| Primitive | Algorithm | Security Level |
|-----------|-----------|----------------|
| Symmetric Encryption | AES-256-CBC | 256-bit |
| Authentication | HMAC-SHA256 | 256-bit |
| Digital Signatures | ECDSA secp256k1 | ~128-bit |
| Key Derivation | PBKDF2-SHA256 | 600,000 iterations |
| Transport | TLS 1.3 | Varies by suite |

## Security Controls

### Authentication

- **Method**: MetaMask wallet signature verification
- **Token**: JWT with 24-hour expiration
- **Nonce**: Single-use, 5-minute expiration
- **Storage**: No server-side password storage

### Authorization

- **Model**: Role-Based Access Control (RBAC)
- **Roles**: None, User, Sentinel, Admin
- **Permissions**: Per-operation granularity
- **Enforcement**: Pre-request middleware

### Rate Limiting

| Tier | Limit | Window |
|------|-------|--------|
| Default | 5 req | 1 minute |
| Sentinel | 10 req | 1 minute |
| Guild | 100 req | 1 minute |

### Input Validation

- All inputs validated using Pydantic models
- Base64 encoding verified before decryption
- Size limits enforced (10MB max request)
- SQL injection N/A (no SQL database)

## Attack Surface

### API Endpoints

| Endpoint | Risk | Mitigations |
|----------|------|-------------|
| `/auth/nonce` | DoS | Rate limiting |
| `/auth/verify` | Signature bypass | EIP-712 verification |
| `/encrypt` | Data exposure | Auth required, rate limited |
| `/decrypt` | Key exposure | Auth required, logging |
| `/asr/{id}` | Info disclosure | Own-data restriction |

### Cryptographic Operations

| Operation | Risk | Mitigations |
|-----------|------|-------------|
| Key Generation | Weak RNG | OS random source |
| Encryption | Padding oracle | GCM authenticated |
| Decryption | Timing attack | Constant-time HMAC |
| Signing | Key leakage | Memory-safe storage |

## Incident Response

### Threat Level Actions

| Level | Description | Response |
|-------|-------------|----------|
| 1 (Info) | Routine operations | Log only |
| 2 (Caution) | Failed auth | Monitor |
| 3 (Warning) | Weak cipher | Alert admin |
| 4 (Alert) | Breach pattern | Rate limit |
| 5 (Critical) | Active attack | Block + notify |

### PTS Escalation

- Safe (< 50): Normal operation
- Caution (50-149): Enhanced monitoring
- Critical (>= 150): Automatic restrictions

## Compliance

### Security Checklist

- [x] No hardcoded secrets
- [x] Environment-based configuration
- [x] Encrypted data at rest (optional)
- [x] TLS 1.3 for transport
- [x] Audit logging (ASR)
- [x] Rate limiting
- [x] Input validation
- [x] HMAC authentication on ciphertexts

### Key Management

- Key rotation: 90 days (configurable)
- Key storage: Local filesystem or HSM
- Key backup: User responsibility
- Key revocation: Via admin API

## Vulnerability Disclosure

Report security vulnerabilities to: security@angelcloud.io

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested mitigation (if known)

Response timeline:
- Acknowledgment: 24 hours
- Initial assessment: 72 hours
- Fix timeline: Based on severity
