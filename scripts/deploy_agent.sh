#!/bin/bash
# Deploy Pulsar Sentinel agent to a cluster node.
# Usage: ./deploy_agent.sh <hostname> [ssh_user]
# Examples:
#   ./deploy_agent.sh alaska
#   ./deploy_agent.sh gulfshores gulfshores
set -e

HOST="${1:?Usage: $0 <hostname> [ssh_user]}"
USER="${2:-$HOST}"   # default: same as hostname
NODE_ID="$HOST"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_SCRIPT="$SCRIPT_DIR/sentinel_agent.py"
SERVICE_TEMPLATE="$SCRIPT_DIR/sentinel-agent.service"

echo "=== Deploying Sentinel Agent to $HOST (user: $USER) ==="

# 1. Push agent script
echo "[1/4] Copying agent script..."
ssh "$USER@$HOST" "sudo mkdir -p /opt/sentinel && sudo chown $USER:$USER /opt/sentinel"
scp "$AGENT_SCRIPT" "$USER@$HOST:/opt/sentinel/sentinel_agent.py"
ssh "$USER@$HOST" "chmod +x /opt/sentinel/sentinel_agent.py"

# 2. Write systemd service (substituting user + node_id)
echo "[2/4] Installing systemd service..."
SERVICE_CONTENT=$(sed -e "s/__USER__/$USER/g" -e "s/__NODE_ID__/$NODE_ID/g" "$SERVICE_TEMPLATE")
ssh "$USER@$HOST" "echo '$SERVICE_CONTENT' | sudo tee /etc/systemd/system/sentinel-agent.service > /dev/null"

# 3. Enable + start
echo "[3/4] Enabling + starting service..."
ssh "$USER@$HOST" "sudo systemctl daemon-reload && sudo systemctl enable --now sentinel-agent.service"

# 4. Verify
echo "[4/4] Verifying..."
sleep 3
ssh "$USER@$HOST" "systemctl is-active sentinel-agent.service && echo '✓ Agent running on $HOST'"

echo "=== Done: $HOST is reporting to http://shanebrain:8250 ==="
