#!/usr/bin/env bash
# deploy_family_homebase.sh — Pi-side one-shot deploy for Family Homebase Cloud
#
# v2 (2026-05-26): Pi-local storage on RAID. NFS removed.
# Bullfrog hardware died; 8TB ZFS pool migrated to Pi but kept read-only
# overnight pending verification. users.json + sessions.json land on
# /mnt/shanebrain-raid/family-homebase/ (Pi RAID 1, 1.8TB mirrored NVMe).
#
# When tank pool is promoted to read-write (tomorrow), migrate the JSON files
# to /tank/shanebrain/shared/family-homebase/ — 30 second move.
#
# Run from the Pi:  bash /mnt/shanebrain-raid/pulsar-sentinel/scripts/deploy_family_homebase.sh
#
# Idempotent: re-running is safe. Skips steps already done.

set -euo pipefail

REPO=/mnt/shanebrain-raid/pulsar-sentinel
CORE=/mnt/shanebrain-raid/shanebrain-core
HOMEBASE=/mnt/shanebrain-raid/family-homebase
# mindmap_auth.py defaults to /mnt/nas/shanebrain/users.json — we symlink that
# to our actual storage path so no code edit is needed.
COMPAT_NAS_LINK=/mnt/nas/shanebrain

banner() { echo; echo "=== $* ==="; }

banner "Step 1/6 — git pull pulsar_sentinel"
cd "$REPO"
git pull origin main

banner "Step 2/6 — Python deps (fastapi, uvicorn, bcrypt)"
pip3 install --user --upgrade fastapi 'uvicorn[standard]' bcrypt

banner "Step 3/6 — Pi-local storage (Pi RAID, no NFS)"
sudo mkdir -p "$HOMEBASE"
sudo chown shanebrain:shanebrain "$HOMEBASE"
# Compatibility symlink so mindmap_auth.py finds its expected path
sudo mkdir -p /mnt/nas
if [[ ! -e "$COMPAT_NAS_LINK" ]]; then
  sudo ln -s "$HOMEBASE" "$COMPAT_NAS_LINK"
fi
echo "Storage path:"; ls -lah "$HOMEBASE"
echo "Compat symlink:"; ls -lah "$COMPAT_NAS_LINK"

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
echo "Storage backend: $HOMEBASE  (compat link: $COMPAT_NAS_LINK)"
echo
echo "Next: create owner + family accounts (interactive):"
echo "  cd $CORE/scripts"
echo "  python3 add_mindmap_user.py init   # you (shane) — owner"
echo "  python3 add_mindmap_user.py add tiffany --role family --display-name 'Tiffany'"
echo "  python3 add_mindmap_user.py add gavin   --role family --display-name 'Gavin'"
ech