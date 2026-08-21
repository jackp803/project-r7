# E4 Current Task

- task_id: `E4-20260821-002`
- issued_at: `2026-08-21T08:37:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`

## Objective

Freeze the completed bounded E4 Broker/PaperBroker skeleton while E7 performs static review and resolves the reported E4 <-> E5 entry-instruction contract mismatch.

## Frozen evidence

- branch: `agent/e4-execution-v2`
- implementation/handoff revision reported by E4: `53487a93f6f10d89723403b1a2e2426ba1c7e82a`
- handoff: `docs/execution/E4_TO_E7_HANDOFF.md`
- executable verification: `NOT_RUN`
- reported blocker: current provisional E5 `entry_instruction.style` has no E7-approved mapping to E4 `OrderRequest.order_type` / conditional price / TIF semantics.

## Required actions

1. Do not modify the completed E4 source/test skeleton while E7 reviews it.
2. Do not invent or stabilize an `entry_instruction.style -> OrderRequest` mapping.
3. Do not add cancel/protection/leverage/account/rate-limit/private-Pionex/restart/live features.
4. Do not alter shared contracts.
5. Preserve fail-closed translation behavior for the reported contract mismatch.
6. Keep executable evidence `NOT_RUN` until a Product Owner-approved local environment is available.
7. If acknowledging HOLD, update only `coordination/E4/STATUS.md` and do not claim E7 acceptance.

## Acceptance

- E4 implementation/handoff remains unchanged;
- no contract fork or silent mapping appears;
- no Pionex private API, credentials, SHADOW, or LIVE work;
- no GitHub Actions/CI/hosted runner/project compute;
- E7 is the next owner for static review and contract-boundary classification.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for a replacement TASK.md. Do not begin another E4 feature automatically.
