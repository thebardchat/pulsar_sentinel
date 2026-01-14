# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints except `/health` and `/auth/*` require JWT authentication.

### Header Format
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### Authentication

#### Request Nonce
```http
POST /auth/nonce
Content-Type: application/json

{
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
}
```

**Response:**
```json
{
    "nonce": "abc123...",
    "message": "PULSAR SENTINEL Authentication\n\nPlease sign...",
    "expires_at": "2024-01-01T12:05:00Z"
}
```

#### Verify Signature
```http
POST /auth/verify
Content-Type: application/json

{
    "wallet_address": "0x1234...",
    "signature": "0xabcd...",
    "nonce": "abc123..."
}
```

**Response:**
```json
{
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "wallet_address": "0x1234...",
    "expires_at": "2024-01-02T12:00:00Z"
}
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer <token>
```

**Response:**
```json
{
    "message": "Logged out successfully"
}
```

### Cryptography

#### Generate Keys
```http
POST /keys/generate?algorithm=hybrid
Authorization: Bearer <token>
```

**Query Parameters:**
- `algorithm`: `hybrid` (ML-KEM + AES) or `aes`

**Response:**
```json
{
    "public_key": "base64_encoded_public_key",
    "key_id": "unique_key_identifier",
    "algorithm": "HYBRID-ML-KEM-768-AES256GCM"
}
```

#### Encrypt Data
```http
POST /encrypt
Authorization: Bearer <token>
Content-Type: application/json

{
    "data": "base64_encoded_plaintext",
    "algorithm": "hybrid",
    "public_key": "base64_encoded_public_key"
}
```

**For AES:**
```json
{
    "data": "base64_encoded_plaintext",
    "algorithm": "aes",
    "password": "your_password"
}
```

**Response:**
```json
{
    "ciphertext": "base64_encoded_ciphertext",
    "algorithm": "HYBRID-ML-KEM-768-AES256GCM"
}
```

#### Decrypt Data
```http
POST /decrypt
Authorization: Bearer <token>
Content-Type: application/json

{
    "ciphertext": "base64_encoded_ciphertext",
    "algorithm": "hybrid",
    "secret_key": "base64_encoded_secret_key"
}
```

**For AES:**
```json
{
    "ciphertext": "base64_encoded_ciphertext",
    "algorithm": "aes",
    "password": "your_password"
}
```

**Response:**
```json
{
    "data": "base64_encoded_plaintext",
    "algorithm": "HYBRID-ML-KEM-768-AES256GCM"
}
```

### Status & Monitoring

#### Health Check
```http
GET /health
```

**Response:**
```json
{
    "status": "healthy",
    "pqc_available": true,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### System Status
```http
GET /status
Authorization: Bearer <token>
```

**Response:**
```json
{
    "status": "operational",
    "pqc_available": true,
    "user": {
        "wallet_address": "0x1234...",
        "role": "USER",
        "tier": "sentinel_core",
        "rate_limit": 10
    },
    "pts": {
        "total_score": 25.5,
        "tier": "safe",
        "factors": {...}
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### ASR (Agent State Records)

#### Get ASR Records
```http
GET /asr/{user_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `start_date`: Filter start date (YYYY-MM-DD)
- `end_date`: Filter end date (YYYY-MM-DD)
- `threat_level_min`: Minimum threat level (1-5)

**Response:**
```json
{
    "records": [
        {
            "asr_id": "asr_abc123...",
            "timestamp": "2024-01-01T12:00:00Z",
            "agent_id": "0x1234...",
            "action": "encrypt_hybrid",
            "threat_level": 1,
            "pqc_status": "safe",
            "signature": "hash...",
            "metadata": {}
        }
    ],
    "total_count": 1,
    "user_id": "0x1234..."
}
```

### Governance

#### Get PTS Score
```http
GET /pts/{user_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
    "total_score": 45.5,
    "tier": "safe",
    "factors": {
        "quantum_risk_count": 1,
        "access_violation_count": 2,
        "rate_limit_violations": 0,
        "signature_failures": 0
    },
    "breakdown": {
        "quantum_risk": 20.0,
        "access_violation": 15.0,
        "rate_limit": 0.0,
        "signature_failure": 0.0
    },
    "calculated_at": "2024-01-01T12:00:00Z",
    "user_id": "0x1234..."
}
```

## Error Responses

### 400 Bad Request
```json
{
    "detail": "Invalid base64 data"
}
```

### 401 Unauthorized
```json
{
    "detail": "Missing or invalid Authorization header"
}
```

### 403 Forbidden
```json
{
    "detail": "Permission denied"
}
```

### 429 Too Many Requests
```json
{
    "detail": "Rate limit exceeded. Reset in 45s"
}
```

### 500 Internal Server Error
```json
{
    "detail": "Internal server error"
}
```

### 503 Service Unavailable
```json
{
    "detail": "PQC not available. Use algorithm='aes' for legacy crypto."
}
```

## Rate Limits

| Tier | Requests/Minute |
|------|-----------------|
| Legacy Builder | 5 |
| Sentinel Core | 10 |
| Autonomous Guild | 100 |

Rate limit headers:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1704110400
```

## Webhooks (Future)

Coming soon: Webhook notifications for:
- PTS tier changes
- Strike issuance
- Ban events
- Heir transfer initiation
