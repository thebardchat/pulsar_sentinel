#!/usr/bin/env bash
# deploy_family_homebase.sh — Pi-side one-shot deploy for Family Homebase Cloud
#
# Run AFTER the bullfrog TrueNAS dataset + NFS share are created in the UI.
# Run this from the Pi:  bash /mnt/shanebrain-raid/pulsar-sentinel/scripts/deploy_family_homebase.sh
#
# Idempotent: re-running is safe. Skips steps already done.

set -euo pipefail

REPO=/mnt/shanebrain-raid/pulsar-sentinel
CORE=/mnt/shanebrain-raid/shanebrain-core
NAS=/mnt/nas/shanebrain
BULLFROG=100.92.153.3

banner() { echo; echo "=== $* ==="; }

banner "Step 1/6 — git pull pulsar_sentinel"
cd "$REPO"
git pull origin main

banner "Step 2/6 — Python deps (fastapi, uvicorn, bcrypt)"
pip3 install --user --upgrade fastapi 'uvicorn[standard]' bcrypt

banner "Step 3/6 — NFS mount of bullfrog:/mnt/tank/shanebrain"
if ! dpkg -s nfs-common >/dev/null 2>&1; then
  sudo apt-get update -y && sudo apt-get install -y nfs-common
fi
sudo mkdir -p "$NAS"
FSTAB_LINE="${BULLFROG}:/mnt/tank/shanebrain  ${NAS}  nfs  rw,hard,intr,_netdev  0  0"
if ! grep -qF "${BULLFROG}:/mnt/tank/shanebrain" /etc/fstab; then
  echo "$FSTAB_LINE" | sudo tee -a /etc/fstab
fi
mountpoint -q "$NAS" || sudo mount -a
echo "NAS mount check:"; ls -lah "$NAS"

banner "Step 4/6 — copy server + auth + CLI + seed into shanebrain-core"
sudo mkdir -p "$CORE/scripts"
sudo cp "$REPO/scripts/mindmap_server.py"     "$CORE/scripts/"
sudo cp "$REPO/scripts/mindmap_auth.py"       "$CORE/scripts/"
sudo cp "$REPO/scripts/add_mindmap_user.py"   "$CORE/scripts/"
sudo cp "$REPO/scripts/update_mindmap.py"     "$CORE/scripts/"
if [[ ! -f "$CORE/mindmap-state.json" ]]; then
  sudo cp "$REPO/scripts/mindmap-state.seed.json" "$CORE/mindmap-state.json"
fi
sudo chmod +x "$CORE/scripts/"*.py

banner "Step 5/6 — install systemd units"
sudo cp "$REPO/scripts/mindmap-server.service"  /etc/systemd/system/
sudo cp "$REPO/scripts/update-mindmap.service"  /etc/systemd/system/
sudo cp "$REPO/scripts/update-mindmap.timer"    /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mindmap-server.service
sudo systemctl enable --now update-mindmap.timer

banner "Step 6/6 — health check"
sleep 2
curl -sS http://localhost:8600/api/health || true
echo
echo
echo "DEPLOY DONE."
echo "Next: create owner + family accounts (interactive):"
echo "  cd $CORE/scripts"
echo "  python3 add_mindmap_user.py init   # you (shane) — owner"
echo "  python3 add_mindmap_user.py add tiffany --role family --display-name 'Tiffany'"
echo "  python3 add_mindmap_user.py add gavin   --role family --display-name 'Gavin'"
echo "  python3 add_mindmap_user.py add angel   --role family --display-name 'Angel'"
echo "  python3 add_mindmap_user.py add kai     --role family --display-name 'Kai'"
echo "  python3 add_mindmap_user.py add pierce  --role family --display-name 'Pierce'"
echo "  python3 add_mindmap_user.py add jaxton  --role family --display-name 'Jaxton'"
echo "  python3 add_mindmap_user.py add ryker   --role viewer --display-name 'Ryker'"
echo
echo "Then visit:  http://100.67.120.6:8600  from any Tailscale device."
