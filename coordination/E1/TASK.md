# E1 Current Task

- task_id: `E1-20260821-004`
- issued_at: `2026-08-21T12:41:00+08:00`
- state: `ACTIVE`
- authority: `agents/E1_MARKET_DATA.md`, `agents/README.md`, `contracts-v0.1`, Product Owner OKX decision, PR #8, E7 finding `E1-INTEGRATION-SYNC-001`

## Objective

Resolve PR #8 repository synchronization only, while preserving the statically accepted OKX public historical-market-data implementation.

E7 has already given the reviewed E1 implementation/test definitions `PASS / STATIC ONLY`. The current blocker is branch synchronization/merge readiness, not market-data behavior.

## Accepted reviewed evidence

- branch: `agent/e1-market-data-okx`
- reviewed implementation revision: `c782438ae7e895f2304498946970f2ee5dd5b18f`
- PR: `#8 market-data: migrate V1 public history to OKX`
- E7 review: `status/e7/E1_OKX_MIGRATION_STATIC_REVIEW_20260821.md`
- static source disposition: `PASS`
- executable verification: `NOT_RUN`

## Required actions

1. Non-destructively synchronize `agent/e1-market-data-okx` with the latest `main`. Preserve reviewed E1 history; no force rewrite.
2. Resolve mailbox/status conflicts in favor of the latest PM-owned `main:coordination/E1/TASK.md`; keep E1-owned STATUS accurate for this task.
3. Preserve the reviewed production/test behavior. Do not redesign the adapter while synchronizing.
4. Correct E7 documentation finding `E1-OKX-DOC-AFTER-001`: current official OKX wording is that `after` returns records **earlier than** the requested timestamp. Update inaccurate comments/handoff wording only as needed; do not alter safe cursor behavior solely for this wording correction.
5. Keep the existing safe cursor behavior unless a new concrete defect is found:
   - first cursor = `end - 1 ms`;
   - next cursor = `earliest returned open_time - 1 ms`.
6. After synchronization, confirm PR #8 is no longer behind main / has a clean merge relationship if GitHub reports it. Do not merge PR #8 yourself.
7. If any production/test semantic blob changes beyond synchronization or documentation/comment precision, report the exact changed paths in STATUS so E7 can perform a full changed-content re-review.
8. Do not add WebSocket, MarketSnapshot, cache/retry platform, private/account API, Demo/private execution, credentials, or Pionex-specific work.
9. Update `coordination/E1/STATUS.md` with post-sync branch HEAD, synchronization commit, exact semantic changes (if any), documentation correction, PR mergeability observation, and verification state.
10. Executable verification remains local-only. If no Product Owner-approved local environment exists, keep `NOT_RUN` and exact commands.

## Acceptance

- branch is synchronized non-destructively with latest main;
- reviewed OKX adapter/test semantics remain unchanged unless explicitly reported;
- `after` documentation wording is corrected;
- PR #8 is ready for E7 bounded SHA/scope recheck;
- no shared-contract or private execution change;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` without approved local execution.

## Writable scope

E1-owned paths only as required for synchronization/documentation precision:

- `src/market_data/**` comments only unless a real defect is found and reported
- `tests/market_data/**` should remain unchanged unless a real defect is found and reported
- `status/e1/OKX_MIGRATION_HANDOFF.md`
- E1-owned docs/status
- `coordination/E1/STATUS.md`

## Forbidden scope

- shared contract changes;
- E2/E3/E4/E5/E6 production changes;
- private OKX/Pionex API/auth/account/order work;
- credentials/secrets;
- GitHub compute/CI;
- merging PR #8.

## Completion / status

Synchronize, correct the documentation precision finding, update STATUS, push to `agent/e1-market-data-okx`, then stop. Do not start another E1 feature automatically.
