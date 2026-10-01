# PM Codex LF-3 Delegation — 2026-10-01

## Authority

Codex is authorized to execute the local-only, credential-free LF-3 Failure Injection & Recovery gate for project-r7.

This authority is limited to deterministic failure injection, restart/recovery, ambiguity, stale-evidence, reconciliation, and fail-closed testing.

Qualified baseline executable revision:

`cec90965a0cd29fe59bec604987ebeebfb5ad09d`

## Mission

Drive LF-3 to PASS or stop only on a genuine architecture/authority/external infrastructure blocker.

Use section 7, "Failure-injection and recovery matrix", of:

`contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`

as the authoritative scenario set.

Every applicable row must be mapped to deterministic local evidence on one exact clean executable candidate.

Codex may:

- audit current tests against every LF-3 matrix row;
- add bounded deterministic failure-injection/recovery tests where coverage is missing;
- fix implementation defects revealed by those tests while preserving accepted contracts/architecture;
- run focused regressions;
- establish a new exact clean committed candidate if executable changes are required;
- run the complete LF-3 matrix on that same candidate;
- after LF-3 matrix passes, rerun the complete credential-free Phase 1 + Phase 2 qualification so the final candidate preserves LF-1/LF-2 PASS;
- commit/push sanitized LF-3 evidence.

Codex must stop and return to PM if a required fix would redefine shared architecture/contracts or require provider/private facts.

## Required LF-3 scenarios

At minimum cover every applicable profile row:

1. ACK/pending vs fill truth
2. ambiguous outcome / reconcile-before-retry
3. partial fill
4. stale market evidence
5. stale Position evidence
6. stale execution evidence
7. breached/equality protection trigger
8. duplicate protection
9. orphan protection
10. missing protection
11. restart flat
12. restart open protected
13. restart open unprotected
14. restart reconciliation-required
15. unchanged failure evidence / no blind retry
16. clock/temporal ordering
17. external/manual provider objects
18. close on order-status only forbidden
19. residual below actionable provider size
20. wrong runtime revision/mode/heartbeat

If a row is genuinely not applicable to the current architecture, Codex must document the exact accepted contract reason; it may not silently omit it.

## PASS definition

LF-3 PASS requires:

- one exact committed executable revision;
- clean approved-local Windows worktree;
- every applicable LF-3 matrix scenario PASS;
- durable scenario-to-test mapping;
- zero failed/errors in LF-3 evidence;
- complete Phase 1 focused P0 qualification PASS on the final candidate;
- complete Phase 2 14-suite credential-free matrix PASS on the final candidate;
- provider requests 0;
- private API NONE;
- credentials NONE;
- provider/account mutation 0;
- real order/protection actions 0;
- trading runtime NOT_STARTED;
- SHADOW/PAPER/LIVE NOT_STARTED;
- capital exposure NONE;
- GitHub compute NOT_USED.

## Prohibited

No provider/private API, credentials, provider/account mutation, real order/protection actions, SHADOW, PAPER, bounded live fire, Gate D, LIVE, capital movement, or GitHub Actions/hosted compute.

Do not infer LF-4/provider PASS from LF-3 simulation.

## Git

Use a bounded Codex branch, recommended:

`codex/lf3-failure-injection-recovery-20261001`

Do not merge main.

Persist sanitized evidence under `status/codex/`.

Return final branch + exact executable SHA to PM.
