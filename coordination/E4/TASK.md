# E4 Current Task

- task_id: `E4-20260821-003`
- issued_at: `2026-08-21T09:05:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, E7 finding `E7-E4E5-ENTRY-001`

## Objective

Freeze the statically accepted bounded E4 Broker/PaperBroker skeleton while E7 completes the formal shared-contract/versioning decision for executable `ApprovedTradePlan.entry_instruction` semantics.

## Frozen evidence

- branch: `agent/e4-execution-v2`
- reviewed implementation revision: `53487a93f6f10d89723403b1a2e2426ba1c7e82a`
- E7 static disposition: `PASS (STATIC ONLY)`
- executable verification: `NOT_RUN`
- remaining boundary blocker: `E7-E4E5-ENTRY-001` / `CONTRACT MISMATCH`

## Required actions

1. Do not modify E4 source/test implementation during this HOLD.
2. Preserve the fail-closed provisional E5 entry translator behavior.
3. Do not invent `style -> order_type`, `reference_price -> limit_price`, TIF, stop/trigger, or exchange-specific semantics.
4. Do not add private Pionex, cancel/protection/leverage/account/rate-limit/restart/SHADOW/LIVE work.
5. Do not modify shared contracts.
6. Keep executable evidence `NOT_RUN` until Product-Owner-approved local execution occurs.
7. If acknowledging HOLD, update only `coordination/E4/STATUS.md`.

## Acceptance

- reviewed E4 skeleton remains unchanged;
- no silent contract fork appears;
- no scope expansion;
- no GitHub Actions/CI/hosted runner/project compute;
- E7 contract/versioning task remains the next authority action.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for a replacement task after E7 materializes or blocks the contract revision.
