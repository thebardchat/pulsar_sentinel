# Deployment Guide

## Prerequisites

- Python 3.11+ (3.13 recommended)
- 7.4GB RAM minimum
- liboqs library (for PQC support)
- MetaMask wallet (for authentication)
- Polygon MATIC balance (for blockchain operations)

## Local Development

### 1. Clone Repository
```bash
git clone https://github.com/thebardchat/pulsar_sentinel.git
cd pulsar_sentinel
```

### 2. Setup Environment
```bash
# Run setup script
chmod +x scripts/setup_venv.sh
./scripts/setup_venv.sh

# Or manually
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.template .env
# Edit .env with your settings
```

### 4. Run Development Server
```bash
# With hot reload
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

# Or use the script
./scripts/run_sentinel.sh
```

## Production Deployment

### Using Docker (Recommended)

Create `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for liboqs
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/asr logs

# Run as non-root
RUN useradd -m appuser
USER appuser

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t pulsar-sentinel .
docker run -d \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/logs:/app/logs \
    --env-file .env \
    pulsar-sentinel
```

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  pulsar-sentinel:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run:
```bash
docker-compose up -d
```

### Using systemd

Create `/etc/systemd/system/pulsar-sentinel.service`:
```ini
[Unit]
Description=PULSAR SENTINEL Security Framework
After=network.target

[Service]
Type=simple
User=pulsar
WorkingDirectory=/opt/pulsar_sentinel
Environment=PATH=/opt/pulsar_sentinel/venv/bin
EnvironmentFile=/opt/pulsar_sentinel/.env
ExecStart=/opt/pulsar_sentinel/venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pulsar-sentinel
sudo systemctl start pulsar-sentinel
```

## Polygon Network Setup

### Testnet (Amoy)

1. Get testnet MATIC from faucet: https://faucet.polygon.technology/
2. Configure `.env`:
```bash
POLYGON_NETWORK=testnet
POLYGON_TESTNET_RPC=https://rpc-amoy.polygon.technology
```

### Mainnet

1. Ensure sufficient MATIC balance
2. Configure `.env`:
```bash
POLYGON_NETWORK=mainnet
POLYGON_MAINNET_RPC=https://polygon-rpc.com
```

### Deploy Governance Contract

```bash
python scripts/deploy_contract.py --network testnet
```

## SSL/TLS Configuration

### Using Nginx Reverse Proxy

Create `/etc/nginx/sites-available/pulsar-sentinel`:
```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8000/api/v1/health
```

### Logs
```bash
# Application logs
tail -f logs/pulsar_sentinel.log

# Docker logs
docker logs -f pulsar-sentinel
```

### Metrics (Future)
Prometheus metrics endpoint: `/metrics`

## Backup & Recovery

### Data Backup
```bash
# Backup ASR data
tar -czf backup_$(date +%Y%m%d).tar.gz data/asr/

# Backup with blockchain cache
tar -czf backup_full_$(date +%Y%m%d).tar.gz data/
```

### Key Backup
Always backup:
- `.env` file (contains server wallet key)
- `data/asr/` directory (ASR records)
- Any generated keys

## Troubleshooting

### liboqs Not Available
```bash
# Install from source
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs && mkdir build && cd build
cmake -DOQS_PERMIT_UNSUPPORTED_ARCHITECTURE=ON ..
make -j4 && sudo make install
pip install liboqs-python
```

### Connection Refused
Check that the server is running on the correct host/port:
```bash
netstat -tlnp | grep 8000
```

### Rate Limit Issues
Adjust in `.env`:
```bash
RATE_LIMIT_DEFAULT=10
```

### Memory Issues
Ensure 7.4GB RAM minimum. For lower memory:
- Reduce batch sizes
- Disable blockchain logging temporarily
