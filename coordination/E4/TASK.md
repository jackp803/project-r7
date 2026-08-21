# E4 Current Task

- task_id: `E4-20260821-009`
- issued_at: `2026-08-21T14:30:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision

## Objective

Freeze the completed Demo-first OKX provider-adapter source implementation while E7 performs static/security/integration review of PR #12.

## Frozen evidence

- completed task: `E4-20260821-008`
- branch: `agent/e4-okx-demo-adapter-20260821`
- implementation/tests/docs/handoff revision: `b7031c52a38623c528ee9352276793d8110854e0`
- PR: `#12 execution: add Demo-first OKX provider adapter`
- status: `coordination/E4/STATUS.md`
- handoff: `docs/execution/E4_TO_E7_HANDOFF.md`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`

## Required actions

1. Do not modify Demo adapter production/test source while E7 reviews PR #12.
2. Preserve Demo-only enforcement, runtime-only credential handling, canonical/provider quantity separation, fail-closed account prerequisites, ambiguity/reconciliation behavior, and submit-time metadata freshness hardening.
3. Do not add a concrete network transport, real credentials, production/live mode, actual Demo order execution, automatic account/position-mode/leverage mutation, or any asset-movement capability.
4. Do not weaken the current fail-closed order-absence behavior merely to make retry possible; the current `order_not_found_codes` default-empty limitation must remain explicit until E7/PM resolves the authoritative integration rule.
5. Keep executable evidence `NOT_RUN` until Product Owner-approved local execution occurs.
6. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- PR #12 source remains frozen for E7 review;
- no shared-contract or other-agent production change;
- no GitHub Actions/CI/hosted runner/project compute;
- no Demo/PAPER/SHADOW/LIVE or real-money authorization.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for E7/PM disposition of PR #12. Do not start local Demo execution or another provider feature automatically.
