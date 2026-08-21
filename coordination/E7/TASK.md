# E7 Current Task

- task_id: `E7-20260821-011`
- issued_at: `2026-08-21T15:05:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision

## Objective

Hold after completing `E7-20260821-010`. PR #12 is blocked pending E4 correction of the five E7 safety findings.

## Accepted current review evidence

- review artifact persisted on `main`: `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md`
- E7 review evidence merged via PR #13
- reviewed E4 implementation: `b7031c52a38623c528ee9352276793d8110854e0`
- PR #12 merge recommendation: `BLOCKED / DO NOT MERGE`
- Demo environment/auth security: `PASS / STATIC ONLY`
- freshness hardening: `PASS / ACCEPT / STATIC ONLY`
- Broker/PaperBroker static compatibility: `PASS / STATIC ONLY`
- blocking owner: `E4`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Blocking findings being corrected by E4

- `E4-OKX-MATERIALIZATION-INTEGRITY-001`
- `E4-OKX-ACCOUNT-MATRIX-001`
- `E4-OKX-RETRY-PROVENANCE-001`
- `E4-OKX-ORDER-ABSENCE-001`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001`

## Required actions

1. Do not modify E1-E6 domain code or shared contracts.
2. Do not re-review PR #12 until PM replaces this HOLD after E4 posts fresh correction STATUS/handoff evidence for `E4-20260821-010`.
3. Preserve the current E7 review artifact and exact findings.
4. Do not advance any release gate.
5. Do not run provider requests, project tests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.
6. Do not authorize approved-local Demo connectivity, Demo order submission, provider retry, PAPER/SHADOW/LIVE, or real-money execution during this HOLD.
7. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

E7 remains idle while E4 corrects the five source blockers. Executable evidence remains `NOT_RUN`; PR #12 remains unmerged; provider execution and release gates remain blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E4 correction evidence. Do not start re-review or another task automatically.
