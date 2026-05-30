# Changelog

All notable changes to PULSAR SENTINEL will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-05-30

First public release. PULSAR SENTINEL goes from "scattered MVP" to a production
post-quantum security framework with high-availability failover, real wallet auth,
and a live on-chain inheritance vault.

### Added

**Recon Dashboard — `/recon`**
- Live mesh status panel with 4-node Sentinel agent heartbeats (alaska, gulfshores, mexico, neworleans)
- PULSAR ATTACK MAP — rotating globe replaces Kaspersky embed
- Real honeypot ticker (`/api/v1/recon/honeypot/stats`) — 1600+ attacks logged
- PTS gauge wired to `PTSCalculator.calculate_pts()` (no more hardcoded values)
- Federated threat feeds — DShield + URLhaus integration
- Agent event log replaces mock squad panel
- Q-Day countdown strip — sticky header showing NIST/NSA/Mosca encryption breakage timelines
- 5 sound effects: radio static, comms beeps, radar sweep, threat alerts, tier upgrade
- New `/audio` StaticFiles mount

**Wallet + Blockchain**
- Real MetaMask wallet connect on `/recon` HUD — `eth_requestAccounts` → `personal_sign` flow
- JWT auth via `/api/v1/auth/nonce` + `/api/v1/auth/verify`
- Session persistence in localStorage with expiry refresh
- LegacyVault smart contract — LIVE on Base Sepolia
  - LegacyVault: `0x70167abe5f732a56aba789d97b3def117f8154bd`
  - MockUSDC: `0x9d9ba25a3231b702c66c0e8aebea5c8672e5abf9`
  - MockAavePool: `0xdcfecb7e3dec4972abfc836cdfabe2212d399da5`
  - Non-custodial digital trust fund: owner deposits USDC, beneficiary inherits after configurable inactivity (7-day testnet, 90-day production)

**High Availability**
- Sentinel API replicated to gulfshores (`100.112.169.111:8250`) with shared Weaviate + Redis state
- Caddy reverse-proxy on Pi `:8443` with `lb_policy first` failover
- Cloudflare Tunnel routes `sentinel.shanebrain.cloud` through Caddy
- Health-driven failover verified end-to-end: Pi service down → traffic seamlessly routes to gulfshores in <10s

**Infrastructure**
- liboqs 0.15.0 built from source for PQC on x86 nodes (gulfshores)
- Redis on neworleans exposed via Tailscale IP for cross-node state sync
- systemd unit `pulsar-sentinel.service` with `Restart=always` on both Pi and gulfshores

### Fixed

- README documented port 8000 → corrected to live 8250
- `/api/v1/health` no longer returns empty body
- Mesh data wired to live agents instead of mock 5-node placeholder
- Wallet overlay auto-dismissed (Phase 1) until blockchain wallet was wired
- Stale hardcoded PTS values, demo badges, RC code labels cleaned from ticker

### Security

- ML-KEM-768 (NIST FIPS 203) post-quantum key encapsulation operational on Pi and gulfshores
- All cross-node calls over Tailscale (100.x mesh)
- JWT secrets shared across replicas for token interchangeability
- Deploy private key never committed (`.gitignore`'d throwaway wallet, burn after use)

### Known Limitations (Phase 2 backlog)

- LegacyVault deployed on Base Sepolia testnet only; mainnet pending lawyer non-custodial framing clearance
- Heir transfer UI not yet wired (contract supports it)
- neworleans not yet a 3rd failover replica (gulfshores pattern proven, replication pending)
- Cloudflare Radar embed token deferred

### Infrastructure Notes

- Repo: https://github.com/thebardchat/pulsar_sentinel
- Live: https://sentinel.shanebrain.cloud
- Cluster: ShaneBrain Pi 5 + 3 x86 nodes (gulfshores, mexico, neworleans) over Tailscale

[1.0.0]: https://github.com/thebardchat/pulsar_sentinel/releases/tag/v1.0.0
