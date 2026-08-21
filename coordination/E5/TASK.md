# E5 Current Task

- task_id: `E5-20260821-002`
- issued_at: `2026-08-21T08:37:00+08:00`
- state: `HOLD`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`

## Objective

Freeze the corrected E5 Risk/Position source after E7 static acceptance of `E5-RISK-UNKNOWN-001`. Wait for E7's separate E4 <-> E5 entry-instruction boundary decision and for future local verification.

## Accepted static evidence

- corrected revision: `cb65c951d59f6fd036bd61691d7e96d025e371c8`
- E7 re-review artifact: `status/e7/E5_E6_CORRECTION_REREVIEW_20260821.md`
- E7 finding disposition: `STATICALLY_RESOLVED / PASS (static)`
- executable verification: `NOT_RUN`

## Required actions

1. Do not modify the accepted fail-closed correction unless PM/E7 issues another bounded task.
2. Preserve `TradeIntent -> RiskDecision -> ApprovedTradePlan` authority.
3. Do not stabilize or extend provisional `entry_instruction` / `protection_instruction` semantics while E7 reviews the E4 boundary.
4. Do not add production risk values, sizing expansion, exit features, broker logic, PAPER, SHADOW, or LIVE.
5. Keep executable evidence `NOT_RUN` until approved local execution.
6. If acknowledging HOLD, update only `coordination/E5/STATUS.md`.

## Acceptance

- E7-accepted static correction remains intact;
- no shared-contract change;
- no execution-semantic expansion;
- no GitHub compute/CI;
- no executable PASS claim.

## Writable scope

Only `coordination/E5/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for a replacement TASK.md.
