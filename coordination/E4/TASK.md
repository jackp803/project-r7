# E4 Current Task

- task_id: `E4-20260821-004`
- issued_at: `2026-08-21T10:07:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, E7 finding `E7-E4E5-ENTRY-001`, Product Owner decision `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`

## Objective

Freeze the statically accepted broker-neutral E4 Broker/PaperBroker skeleton while two upstream architecture items are resolved:

1. E7 executable `ApprovedTradePlan.entry_instruction` contract/version decision;
2. OKX-specific execution boundary design for instrument sizing/account configuration.

The Product Owner has changed the V1 broker target from Pionex to a dedicated OKX sub-account. No new Pionex-specific development is authorized.

## Frozen evidence

- branch: `agent/e4-execution-v2`
- reviewed implementation revision: `53487a93f6f10d89723403b1a2e2426ba1c7e82a`
- E7 static disposition: `PASS (STATIC ONLY)`
- executable verification: `NOT_RUN`
- remaining shared boundary blocker: `E7-E4E5-ENTRY-001` / `CONTRACT MISMATCH`

## Product target amendment

Future exchange adapter target, after separate authorization:

```text
OKX
Dedicated R7 sub-account
BTC-USDT-SWAP
isolated intent
Demo Trading before real execution
```

The existing broker-neutral `Broker` / `PaperBroker` design remains valid and must not be hard-coded to OKX.

## Required actions

1. Do not modify the accepted E4 source/test skeleton during this HOLD.
2. Do not invent `entry_instruction` semantics before E7 finishes the contract decision.
3. Do not build `PionexBroker` or any new Pionex private/public execution logic.
4. Do not yet build private/Demo `OkxBroker`, authentication, signatures, account calls, leverage-setting calls, or real/demo order submission.
5. Do not assume canonical approved quantity is numerically identical to OKX derivative `sz`.
6. Future OKX sizing translation must use authoritative instrument metadata and may round down or reject, never round up above E5-approved exposure. The exact boundary is pending E7/E5/E4 design review.
7. Do not expose withdrawal, funding transfer, sub-account capital movement, or other non-trading money-movement capability in the future Broker interface.
8. Preserve fail-closed ambiguous acknowledgement/reconciliation behavior.
9. Do not modify shared contracts.
10. Keep executable evidence `NOT_RUN` until Product-Owner-approved local execution occurs.
11. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- reviewed broker-neutral skeleton remains unchanged;
- no Pionex-specific new work;
- no premature OKX private/Demo implementation;
- no shared-contract fork;
- no GitHub Actions/CI/hosted runner/project compute;
- no PAPER/SHADOW/LIVE authorization.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait. The next E4 ACTIVE task will be issued only after E7 has a coherent entry-contract decision and an OKX adapter/sizing boundary has been statically specified.
