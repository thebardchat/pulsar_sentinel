# YourLegacy Contracts — Phase 1

**Status:** Local development. No network broadcast. Pre-lawyer-consult build.
**Lawyer consult:** 2026-05-26 9am Central. All design choices below are open for review.
**Chain target:** Base Sepolia (testnet) AFTER consult. Base mainnet is Phase 4 (post-audit).
**Owner:** Shane Brazelton — Pulsar Sentinel / Angel Cloud / ShaneBrain.

---

## What this is

`LegacyVault.sol` is the non-custodial digital trust fund contract that powers the YourLegacy feature of Pulsar Sentinel. One vault per family. Owner deposits USDC, vault supplies to Aave V3 and earns yield. Owner pings monthly to prove they're alive. After 90 days of silence, the named beneficiary can withdraw the full principal plus accrued yield.

ShaneBrain / Angel Cloud / Pulsar Sentinel are not custodians. They cannot touch user funds. The contract is the custodian. This is the keystone of the legal framing: software, not money-transmitter.

---

## File layout

```
contracts/
├── foundry.toml              # Foundry config — no mainnet RPC declared
├── remappings.txt            # OZ + Aave + forge-std import paths
├── .env.template             # Filled in AFTER lawyer consult
├── .gitignore                # out/, cache/, broadcast/, lib/, .env
├── README.md                 # this file
├── src/
│   ├── LegacyVault.sol       # ~150 lines incl NatSpec — core contract
│   └── interfaces/
│       ├── IAavePool.sol     # 2-function slim view of Aave V3 IPool
│       └── IERC20.sol        # minimal ERC-20 (for test mocks)
└── test/
    ├── LegacyVault.t.sol     # 26 tests — constructor, deposit, ping, inherit, fuzz, invariant
    └── mocks/
        ├── MockUSDC.sol      # 6-decimal mirror of real USDC
        └── MockAavePool.sol  # in-process Aave stand-in, supports simulateYield
```

---

## Pulsar Sentinel Rule Code mapping

The contract is wired to the existing PS rule-code framework:

| Function    | RC code | Meaning                                                          |
|-------------|---------|------------------------------------------------------------------|
| `ping()`    | RC 1.01 | Signature Required — owner heartbeat is the signature.           |
| `inherit()` | RC 1.02 | Heir Transfer — fires only after `inactivityThreshold` of silence. |

Future ASR integration (Phase 2): every `Deposited`, `Pinged`, and `Inherited` event gets ingested by the off-chain ASR engine and signed into the audit trail. Polygon anchoring optional.

---

## Phase 1 invariants

These are the truths the contract must never violate. The test suite enforces them; the lawyer can read them in plain English.

- **I1** — `lastHeartbeat` is monotonically non-decreasing. Nothing in the contract pushes it backward.
- **I2** — Only `owner` can call `ping()`.
- **I3** — Only `beneficiary` can call `inherit()`, and only after `block.timestamp - lastHeartbeat >= inactivityThreshold`.
- **I4** — `deposit()` pulls USDC and immediately supplies it to Aave. The vault never holds idle USDC between calls.
- **I5** — `inherit()` empties the entire aToken position to `beneficiary` and locks the vault forever.
- **I6** — `owner` and `beneficiary` are set at deployment and never change in v1. (See "Phase 1 scope" below.)

---

## Threat model

| Threat                                | Mitigation                                                                          |
|---------------------------------------|-------------------------------------------------------------------------------------|
| Re-entrancy in `deposit()` / `inherit()` | `ReentrancyGuard`. `inherited = true` set BEFORE Aave withdraw call (CEI pattern). |
| Owner key loss                        | Acknowledged in honest-risk-disclosure (page-level). Beneficiary inherits after 90d. |
| Beneficiary impatience / griefing     | `OwnerStillActive` custom error reverts cheaply. Owner can re-ping any time.         |
| Stranger calling sensitive functions  | `NotOwner` / `NotBeneficiary` custom errors on every privileged path.                |
| Constructor mis-config (zero address) | `ZeroAddress` reverts. Owner-equals-heir also reverts (same error reused).           |
| Inactivity threshold set absurdly low | Minimum 7-day floor enforced in constructor.                                         |
| Aave V3 protocol failure              | Out of scope of this contract. Documented on the user-facing page as a known risk.   |
| USDC depeg                            | Out of scope. Documented on the user-facing page.                                    |
| Double-inherit                        | `inherited` boolean prevents re-entry. Also blocks ping/deposit post-inherit.        |
| Allowance leak to Aave                | `forceApprove(pool, amount)` resets allowance per deposit. No lingering approvals.   |

---

## What Phase 1 deliberately does NOT cover

These are real questions that the lawyer's input shapes — not bugs.

- **Heir-change UX.** v1 immutables: owner and beneficiary are locked at deploy. v2 likely adds an owner-initiated `proposeBeneficiary` with a 30-day timelock so a coerced owner can't insta-redirect.
- **Multi-heir / 3-of-5 sons logic.** The trust-fund memory has a 3-of-5 multi-sig design from the original Shane-Brain 2.0 era. v1 ships single-heir to keep the contract surface tiny and audit cost low. Multi-heir is v2 via a Safe wallet as `beneficiary`.
- **Chainlink Automation hook.** The vault is currently passive — beneficiary must call `inherit()` themselves. Chainlink Automation can wake the heir at the threshold; this is an orchestrator concern (Pi MCP port 8550), not a contract concern.
- **Subscription auto-router contract.** `deposit()` accepts deposits from any address, so the subscription router can be a plain EOA or a separate router contract added later. No on-vault changes needed.
- **Emergency owner withdrawal.** Deliberately absent. If the owner could withdraw to an attacker wallet, the "non-custodial yet inheritable" guarantee dies. v2 may add an owner-initiated `withdraw` with the same 30-day timelock as heir-change.
- **Upgrade path.** No proxy. Vault is single-purpose and immutable. v2 ships a new contract; v1 vaults run to completion as-is.

---

## Lawyer-review checklist (for 2026-05-26 9am consult)

Print this. Walk through it together. Open questions in bold.

1. **Non-custodial framing.** Does the contract genuinely qualify as non-custodial under Alabama / SEC interpretations? Shane never holds keys; the contract holds the aTokens; only owner/heir can move them.
2. **Yield language.** Is "earns yield via Aave V3" defensible without an RIA / broker-dealer license? Aave is a public protocol Shane neither runs nor controls.
3. **Inheritance language.** "Heir inherits funds" — on-chain only. **Does this need probate-court interaction or can we honestly say "skips probate-style delays"?**
4. **Subscription mingling.** Sentinel Core subscription dollars flow through ShaneBrain → vault. **Does that flow create a security under Howey?** The customer is paying for software (Sentinel Core) and the vault routing is a feature, not an investment contract.
5. **Tax language.** Can we say anything about tax on accrued yield? Probably not without naming "capital gains apply" and disclaiming any 401k/IRA/HSA equivalence.
6. **Waitlist copy.** Pre-launch page currently softens all claims to "designed to" / "will" with a "BUILDING NOW · NOT YET OPERATIONAL · WAITLIST OPEN" banner. **Is that sufficient to avoid pre-effective-date issues?**
7. **Geographic restrictions.** Does Shane need to geo-block any jurisdictions (NY BitLicense, Texas SB, etc.) at the dapp level?
8. **Disclaimer placement.** Honest-risk list currently in the architecture doc. Where does it need to live in the UI (page footer? Modal before deposit?) to count?
9. **Aspirational benefit cards vs Phase 1 reality.** The `/security` page (`ui/templates/security.html` ~line 1539) lists ~22 trust-fund benefits under "Designed to deliver what a traditional trust fund does". Phase 1's `LegacyVault.sol` delivers ~4 of them mechanically: single-heir non-custodial transfer, Aave yield, 90-day trigger, on-chain audit trail. The other ~18 (Conditional Distribution, Drip Schedule, Multi-Generational, Education Earmarks, Care for Dependent Heirs, Charitable Provisions, Income Stream, etc.) describe specific mechanisms that don't exist yet. **Is "Designed to deliver" softening enough cover, or do we need to (a) remove unbuilt cards from launch, (b) caveat each one with "Phase 2/3 feature", or (c) accelerate them into v1?**
10. **Digital-self inheritance language.** Same page promises "your encrypted data, your photos, your TheirNameBrain AI persona" inherit alongside the financial vault. That's a different technical surface (Pulsar Sentinel ASR + Weaviate, not `LegacyVault.sol`). **Is the legal treatment of digital-asset inheritance distinct from financial-asset inheritance? Does the page need to separate the two flows explicitly?**

---

## How to run the test suite

These commands assume gulfshores (Linux dev box). Do **not** run forge install on the Pi — keep the Pi for MCP/orchestrator work.

```bash
# One-time setup on gulfshores
cd ~/pulsar_sentinel/contracts
forge install foundry-rs/forge-std
forge install OpenZeppelin/openzeppelin-contracts
forge install aave/aave-v3-core

# Run the suite — local only, no RPC needed
forge test -vvv

# With gas snapshots
forge test --gas-report

# Coverage
forge coverage --report summary

# Slither static analysis (after `pip install slither-analyzer`)
slither src/LegacyVault.sol --config-file slither.config.json
```

Expected: all 26 tests pass green. No network calls. No keys touched.

---

## What NOT to run tonight

- `forge create` — deploys. Blocked by lawyer consult.
- `forge script --broadcast` — broadcasts. Blocked by lawyer consult.
- Anything that hits Base Sepolia or Base mainnet RPC. The `foundry.toml` has the Sepolia endpoint declared but `BASE_SEPOLIA_RPC_URL` is intentionally empty in `.env.template`.
- Any change to the waitlist page or marketing copy. Pre-launch banner stays as-is.

---

## Next steps (post-consult)

1. Lawyer signs off on framing → fill in `.env` with Base Sepolia RPC + test wallet key.
2. `forge create --rpc-url base_sepolia` against a throwaway deployer wallet funded from the Coinbase Sepolia faucet.
3. Manual smoke test on Sepolia: deploy, deposit small amount, ping, simulate inherit via `vm.warp`-equivalent in a script.
4. Schedule Code4rena or Spearbit audit ($5–15K — only meaningful spend in Phase 4).
5. Phase 2 work begins: Pi MCP orchestrator on port 8550, FastAPI heartbeat UX, Weaviate `LegacyVault` collection schema.

---

## Repo conventions

- Solidity 0.8.24 (latest stable on Base mainnet at the time of writing).
- OZ contracts via `@openzeppelin/` remapping.
- Aave V3 via `@aave/core-v3/` remapping (currently only used for the production import path — tests use the slim mock interface).
- Naming: `LegacyVault` matches the architecture doc. Tests live in `test/`, mocks in `test/mocks/`.
- No emojis in code or commit messages. Per repo convention.
