# E7 Current Task

- task_id: `E7-20260822-002`
- issued_at: `2026-08-22T02:48:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision

## Objective

Hold after completing the final static/security review of E4 PR #12. The review evidence is merged to `main`, and PR #12 has been merged. Do not start provider execution or another integration task automatically.

## Accepted evidence

- completed review task: `E7-20260822-001`
- final review artifact: `status/e7/E4_OKX_DEMO_FINAL_REREVIEW_20260822.md`
- E7 review branch evidence merged via PR #15: `349933d12f4e98518a27fece2f308586984d5535`
- E4 PR #12 merged to `main`: `572b54f9d454ddf33bb5a2d92f98bba67e852e16`
- `E4-OKX-MATERIALIZATION-INTEGRITY-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ACCOUNT-MATRIX-001`: `CLOSED / PASS STATIC`
- `E4-OKX-RETRY-PROVENANCE-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-ABSENCE-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001`: `CLOSED / PASS STATIC`
- executable verification: `NOT_RUN`
- actual Demo/provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED / NOT AUTHORIZED`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Required actions

1. Do not modify E1-E6 production code or shared contracts.
2. Do not start approved-local connectivity/read-only dry integration until PM/Product Owner explicitly authorizes an approved local environment and issues a separate task.
3. Do not authorize Demo order submission, provider retry, PAPER/SHADOW/LIVE, or real-money execution.
4. Preserve all accepted E7 review artifacts and finding dispositions.
5. Do not run provider requests, project tests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.
6. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

E7 remains idle with the E4 Demo adapter statically accepted and merged. Executable evidence remains `NOT_RUN`; provider execution and release gates remain blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for the next PM task. Do not start provider execution or another review automatically.
