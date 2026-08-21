# E7 Current Task

- task_id: `E7-20260821-013`
- issued_at: `2026-08-21T16:19:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision

## Objective

Hold after completing `E7-20260821-012`. Four of five prior PR #12 blockers are statically closed; E4 now owns a final bounded correction for the remaining provider-submit materialization integrity blocker.

## Accepted current review evidence

- targeted re-review artifact persisted on `main`: `status/e7/E4_OKX_DEMO_TARGETED_REREVIEW_20260821.md`
- E7 targeted re-review evidence merged via PR #14
- reviewed corrected E4 implementation: `651541ba0da646f0c2ab69117219e2c8ca21247c`
- PR #12 merge recommendation: `BLOCKED / DO NOT MERGE`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED / NOT AUTHORIZED`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Closed findings — freeze these dispositions

- `E4-OKX-ACCOUNT-MATRIX-001` — `CLOSED / PASS STATIC`
- `E4-OKX-RETRY-PROVENANCE-001` — `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-ABSENCE-001` — `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001` — `CLOSED / PASS STATIC`

## Remaining finding under E4 correction

- `E4-OKX-MATERIALIZATION-INTEGRITY-001` — `BLOCKING / NOT CLOSED`

The remaining source condition is specifically at `submit_entry()`: caller-mutable/caller-constructible `OKXOrderMaterialization` provider request facts must not be accepted as submit authority without adapter-issued provenance/integrity or submit-time re-derivation/revalidation.

## Required actions

1. Do not modify E1-E6 domain code or shared contracts.
2. Do not re-review PR #12 until PM replaces this HOLD after E4 posts fresh correction STATUS/handoff evidence for `E4-20260821-012`.
3. Preserve the targeted re-review artifact and the four closed findings above.
4. Do not advance Gate A/B/C/D.
5. Do not run provider requests, project tests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.
6. Do not authorize approved-local Demo connectivity, Demo order submission, provider retry, PAPER/SHADOW/LIVE, or real-money execution during this HOLD.
7. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

E7 remains idle while E4 closes the one remaining submit-boundary materialization blocker. Executable evidence remains `NOT_RUN`; PR #12 remains unmerged; provider execution and release gates remain blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E4 correction evidence. Do not start re-review, provider execution, or another task automatically.