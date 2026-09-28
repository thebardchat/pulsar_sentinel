# STATUS — thebardchat/pulsar_sentinel

_Last updated: 2026-09-28 (America/Chicago) by Release manager_

## Snapshot

| Metric | Value |
|--------|-------|
| Open PRs | 0 |
| Blocked PRs | 0 |
| Ready PRs awaiting human merge | 0 |
| Days since last `main` merge | **4** (last: 2026-09-23, #13 → `63b6f4a7`) |
| CI health (`main` tip `63b6f4a7`) | Healthy — `test (3.12)` + `test (3.13)` + `docker-build` success; pages build/deploy/report/notify success |
| Open audit issues | 0 |

## Week of 2026-09-22 → 2026-09-28 (America/Chicago)

Meaningful gate activity on **2026-09-23** (board quiet since). Human merges by `thebardchat`; Release manager did not merge.

### Merged to `main` (locked stack + follow-ons)

| Order | PR | Topic | Merge SHA (short) |
|------:|----|--------|-------------------|
| 1 | [#9](https://github.com/thebardchat/pulsar_sentinel/pull/9) | plumbing: ruff baseline for `src/` | `087a24f4` |
| 2 | [#11](https://github.com/thebardchat/pulsar_sentinel/pull/11) | plumbing: cov-fail-under 80→40 (pytest red waived through this PR only) | `9dc47308` |
| 3 | [#10](https://github.com/thebardchat/pulsar_sentinel/pull/10) | draft: PTS/ASR test integrity (clears pytest) | `be9f0473` |
| 4 | [#6](https://github.com/thebardchat/pulsar_sentinel/pull/6) | draft: ML-KEM 90-day key rotation | `957279c9` |
| 5 | [#8](https://github.com/thebardchat/pulsar_sentinel/pull/8) | docs: sync key rotation with #6 | `b596a9e0` |
| — | [#12](https://github.com/thebardchat/pulsar_sentinel/pull/12) | plumbing/security: fail-closed `PULSAR_SERVICE_KEY` (audit #7) | `12cf9be0` |
| — | [#13](https://github.com/thebardchat/pulsar_sentinel/pull/13) | docs: sync fail-closed service key with #12 | `63b6f4a7` |

Preferred merge order `#9 → #11 → #10 → #6 → #8` completed; #12/#13 closed the service-key audit path.

### Ready-notify outcomes

- Stack PRs were converted draft→ready after Guru plumbing APPROVED (COMMENT accepted where required) and Pulsar crypto gate (N/A or COMMENTED Crypto APPROVED on author-account PRs); user merged each ready PR.
- Tip CI after #13 stayed green; no further ready PR; no open-gate notify after the stack cleared.

### Audit gates

- [#7](https://github.com/thebardchat/pulsar_sentinel/issues/7) `[audit]` CRITICAL hardcoded default `PULSAR_SERVICE_KEY` — **closed** 2026-09-23 after #12 merged (docs follow-on #13).

### Open PRs / open audits

None.

## Notes

- Nothing reaches `main` without Release manager gates + human merge.
- Release manager never writes app code, never merges, never touches secrets / deployed addresses / `.env`.
