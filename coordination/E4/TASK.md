# E4 Current Task

- task_id: `E4-20260821-007`
- issued_at: `2026-08-21T13:31:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, Product Owner OKX decision

## Objective

Freeze the completed canonical entry translator and deterministic local OKX sizing layer while E7 performs static/safety review of PR #11.

## Frozen evidence

- branch: `agent/e4-execution-v2`
- task: `E4-20260821-006`
- implementation/docs/handoff revision: `c71bf9c66a7f37cedb8bbbcf3000591970a081eb`
- PR: `#11 execution: add canonical entry translation and OKX sizing layer`
- status: `coordination/E4/STATUS.md`
- handoff: `docs/execution/E4_TO_E7_HANDOFF.md`
- executable verification: `NOT_RUN`

## Required actions

1. Do not modify the reviewed E4 production/test implementation while E7 reviews PR #11.
2. Preserve the existing Broker/PaperBroker authority, idempotency, partial-fill, overfill, ambiguous-acknowledgement, and reconciliation fail-closed behavior.
3. Preserve canonical `entry-v0.1 / MARKET` translation and `base-asset-v0.1 / BASE_ASSET / BTC` quantity semantics.
4. Preserve the rule that OKX provider sizing may round down or reject but must never exceed the E5-approved canonical BTC exposure.
5. Do not implement OKX networking, private/Demo API, auth/signatures, account calls, leverage-setting, order submission, provider `clOrdId` mapping, withdrawal, funding transfer, or sub-account capital movement during this HOLD.
6. Do not modify shared contracts or add Pionex-specific work.
7. Keep executable evidence `NOT_RUN` until Product Owner-approved local execution occurs.
8. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- PR #11 source remains frozen for E7 review;
- no scope expansion or shared-contract change;
- no private/Demo provider execution;
- no GitHub Actions/CI/hosted runner/project compute;
- no executable PASS or release-gate claim.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for E7/PM disposition of PR #11. Do not start OKX Demo/private execution automatically.
