# STATUS — thebardchat/pulsar_sentinel

_Last updated: 2026-09-22 (America/Chicago) by Release manager_

## Snapshot

| Metric | Value |
|--------|-------|
| Open PRs | 1 |
| Blocked PRs | 1 |
| Days since last `main` merge | **114** (last: 2026-05-31, Release v1.1.0) |
| CI health (`main` tip) | Unhealthy — `test (3.13)` failed on tip; deploy/pages jobs historically green |

## Open PRs

### [#6](https://github.com/thebardchat/pulsar_sentinel/pull/6) — draft: implement and test ML-KEM 90-day key rotation
- **State:** draft
- **Author account:** `thebardchat` (crypto/ML-KEM → Guardian lane)
- **Blocked:** yes
- **Why:**
  1. Missing plumbing approval (GitHub Guru)
  2. Missing crypto approval (Pulsar Sentinel Guardian)
  3. CI failure: `test (3.13)` — owner: Pulsar Sentinel Guardian; `test (3.12)` cancelled; `docker-build` skipped
- **Audit against this PR:** none
- **Stale:** no (opened 2026-09-22; under 7 days)

## Open audit issues (repo-wide, not PR-scoped)

- [#7](https://github.com/thebardchat/pulsar_sentinel/issues/7) `[audit]` CRITICAL: Hardcoded default `PULSAR_SERVICE_KEY` — blocks admin API if env unset. Flag only; Auditor does not open fix PRs.

## Notes

- Nothing reaches `main` without Release manager gates + human merge.
- Release manager never writes app code, never merges, never touches secrets / deployed addresses / `.env`.