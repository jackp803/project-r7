# E7 Current Task

- task_id: `E7-20260822-007`
- issued_at: `2026-08-22T15:16:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e6-evidence-authority-rereview-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, prior E7 reviews under `status/e7/`

## Objective

Perform the final targeted exact-revision static/security re-review of PR #16 after E6 task `E6-20260822-005`, focusing on whether `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` is actually closed end-to-end at the authoritative persistence boundary without regression to `E6-EVIDENCE-CONTRACT-001` or accepted early-Slice-2 boundaries.

This is static/source review only. It does **not** authorize project execution, migrations, PAPER/SHADOW/LIVE, provider calls, or GitHub compute.

## Review inputs

- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- E6 branch: `agent/e6-platform`
- corrected source/tests/docs revision: `df39836adabd04c77cc4f0d0b531ea10408866ab`
- handoff refresh: `dfa6f6a34978a2e068c29279f6ce85836fc806f2`
- platform-status refresh: `63fe79ef2c9b377b960be7ceb2d5f7e9634bd99e`
- observed PR head at PM audit: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`
- E6 synchronization merge: `d94a64a1abaf70850167b3e6aec7af120f40ffa6`
- main synchronized by E6 before correction: `4474a919f0446881369914523132b4aa9b88007d`
- accepted prior finding: `E6-EVIDENCE-CONTRACT-001 / CLOSED / PASS STATIC`
- remaining finding under review: `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`
- executable verification: `NOT_RUN`

## Required review

1. Work only on fresh branch `agent/e7-e6-evidence-authority-rereview-20260822` created from latest `main` after this TASK issuance.
2. Review actual E6 source/tests at exact correction revision `df39836ad...`; do not rely only on E6 STATUS/handoff claims.
3. Verify the exact lifecycle vocabulary and edge shape remain only:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

and all other state pairs remain fail-closed at both Python persistence and SQL migration boundaries.
4. Verify `SQLiteRegistryStore.append_transition(...)` checks durable promotion authority **inside the transaction and before lifecycle INSERT/projection UPDATE**, while preserving current-state, expected-revision, resulting-revision, atomicity, and rollback behavior.
5. For `DRAFT -> BACKTESTING`, verify persistence independently requires durable exact-strategy E2 compatibility with:
   - checker accepted by existing E2 boundary semantics;
   - `PASS / LOCAL_EXECUTION`;
   - non-empty `source_revision`, `environment`, `command`, `result_ref`;
   - no transition-record field alone can manufacture authority.
6. For `BACKTESTING -> CANDIDATE`, verify persistence independently requires:
   - transition-selected durable `VALIDATION_DECISION` evidence;
   - producer `E3`, decision `PASS`;
   - exact strategy identity and content-hash binding;
   - complete `PASS / LOCAL_EXECUTION` metadata;
   - durable E3 parent `BACKTEST_RESULT` with exact same strategy/content binding and complete local PASS metadata;
   - revalidation through the accepted canonical BacktestResult and ValidationDecision validators;
   - exact canonical ValidationDecision -> BacktestResult ID binding;
   - malformed/mismatched/FAIL/BLOCKED/NOT_RUN/wrong-parent/wrong-evidence-type objects fail closed.
7. **Explicit provenance challenge:** inspect the full exported persistence surface, not only `append_transition()`. Determine whether a caller that can directly access `SQLiteRegistryStore` can first manufacture apparently durable promotion authority through public/reachable methods such as `save_compatibility(...)`, `save_validation_evidence(...)`, direct record construction, or equivalent raw-store interfaces, and then successfully call `append_transition(...)`. A synthetic record with strings like `checker="E2..."`, `producer="E3"`, and caller-supplied `PASS / LOCAL_EXECUTION` metadata must not count as trusted authority merely because it was inserted through an unrestricted public persistence method. Classify this specifically as `PASS`, `BLOCKING`, or a precisely justified non-blocking boundary based on the repository's authority model. Do not assume persistence provenance from field values alone.
8. Verify normal `StrategyPlatformService` flows still use the same or stricter lifecycle-authority semantics and cannot be weakened by the new helper layer.
9. Review `tests/storage/test_lifecycle_evidence_authority.py` and related tests. Confirm definitions cover missing/invalid E2 authority, missing/invalid E3 decision/backtest authority, no row/state/revision mutation on rejection, and valid service-authorized positive paths. Also check whether tests accidentally prove that a raw-store caller can create synthetic PASS evidence and promote; if so, classify the resulting authority implication explicitly rather than treating the test as positive security evidence.
10. Recheck SQL forbidden-edge trigger and append-only history protections remain intact. Note that SQL edge-shape enforcement alone is not sufficient evidence authority.
11. Recheck `E6-EVIDENCE-CONTRACT-001`: canonical validators, exact binding, invalid enum/type fail-closed behavior, caller metadata bypass protection, and BacktestResult-alone inability to authorize CANDIDATE must not regress.
12. Recheck repository scope and synchronization against latest `main`: no `contracts/**`, E1/E2/E3/E4/E5 production, workflow/CI, provider/credential/secret, Slice 3 execution-audit, or unrelated changes. Coordination-only main drift is not by itself a resync blocker.
13. Persist a new E7 targeted review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed E6 revision and observed PR head;
   - `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` disposition;
   - explicit raw-store evidence-provenance disposition;
   - `E6-EVIDENCE-CONTRACT-001` regression disposition;
   - edge/migration/concurrency/rollback/test/scope dispositions;
   - PR #16 merge recommendation;
   - executable verification `NOT_RUN`;
   - Gate A/B/C/D unchanged.
14. If and only if promotion authority is not bypassable through any public/reachable authoritative persistence surface and all prior accepted boundaries remain intact, state `PM MAY MERGE PR #16`.
15. If any authority bypass remains, identify the exact reachable source path and owner; keep PR #16 `DO NOT MERGE`. Do not modify E6 production code yourself.
16. Do not run project tests, migrations, backtests, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute. Do not create a Codex ticket without a locally reproduced executable defect.

## Acceptance

Task completes when Git contains an exact-revision review that either closes `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` end-to-end, including raw-store evidence provenance, and recommends PM merge PR #16; or keeps PR #16 blocked with a precise reachable authority-bypass condition. Executable evidence remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- lifecycle expansion;
- Slice 3 execution/provider persistence;
- provider execution;
- PAPER/SHADOW/LIVE advancement;
- GitHub compute/CI.

## Completion / status

Persist the targeted re-review and STATUS, then stop and wait for PM. Do not merge PR #16 or start another task automatically.
