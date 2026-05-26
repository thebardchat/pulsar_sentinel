# Run sheet — gulfshores (100.112.169.111)

SSH from pulsar00100 → gulfshores. Copy-paste these blocks.

## 0. Confirm you're on gulfshores

```bash
hostname
# expect: gulfshores
tailscale ip -4
# expect: 100.112.169.111
```

## 1. Sync the contracts/ folder from pulsar00100

You already have pulsar_sentinel cloned on gulfshores. Pull the contracts/
folder Shane wrote tonight into it. Pick whichever path matches your setup:

```bash
# OPTION A — git (after Shane commits & pushes from pulsar00100)
cd ~/pulsar_sentinel
git pull origin main
ls contracts/  # should show src/ test/ foundry.toml etc.

# OPTION B — direct copy via Tailscale, no commit yet
cd ~/pulsar_sentinel
rsync -av pulsar00100:/c/Users/Hubby/Downloads/pulsar_sentinel/contracts/ ./contracts/
```

## 2. One-time Foundry install (skip if already installed)

```bash
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
forge --version
# expect: forge 0.2.0+ — any 2024 build is fine
```

## 3. Install dependencies

```bash
cd ~/pulsar_sentinel/contracts
forge install foundry-rs/forge-std --no-commit
forge install OpenZeppelin/openzeppelin-contracts --no-commit
forge install aave/aave-v3-core --no-commit
ls lib/  # expect: aave-v3-core/ forge-std/ openzeppelin-contracts/
```

## 4. Run the suite — local only, no network

```bash
forge test -vvv
```

Expected outcome — **all 26 tests pass green**. Group breakdown:

- 5 constructor tests
- 6 deposit tests
- 5 ping tests
- 7 inherit tests
- 4 view-helper tests
- 3 fuzz tests (1000 runs each)
- 1 invariant test

If any test fails, **do not proceed past Phase 1**. Re-open the contract, fix, re-run.

## 5. Gas report (optional, but useful for the lawyer convo)

```bash
forge test --gas-report
```

This shows the cost of each function. Useful for the page disclosure: "Pinging costs ~24k gas, roughly $0.00X on Base."

## 6. Coverage report

```bash
forge coverage --report summary
```

Goal: 100% on `src/LegacyVault.sol`. Anything <100% is a logic path the tests miss — fix the tests, not the contract.

## 7. Slither static analysis

```bash
# One-time install
python3 -m pip install --user slither-analyzer

# Run
slither src/LegacyVault.sol --config-file slither.config.json
```

Expected: 0 high-severity findings. Medium/low informational findings get triaged into the lawyer-review checklist.

## 8. What NOT to run tonight

- `forge create` — deploys to a network. Blocked until lawyer consult.
- `forge script --broadcast` — same.
- Anything that requires `BASE_SEPOLIA_RPC_URL` to be set.

## 9. After the consult (2026-05-26 9am Central)

If lawyer green-lights the non-custodial framing:

```bash
# Fill in .env from .env.template
cp .env.template .env
nano .env
# Add BASE_SEPOLIA_RPC_URL (Alchemy free tier) and a TEST PRIVATE_KEY.
# NEVER use your personal wallet key. Generate a throwaway with cast wallet new.

source .env
forge create --rpc-url base_sepolia \
  --private-key $PRIVATE_KEY \
  src/LegacyVault.sol:LegacyVault \
  --constructor-args $HEIR_ADDR $USDC_SEPOLIA $AAVE_SEPOLIA 7776000
```

Get test ETH for the deployer wallet from
https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
