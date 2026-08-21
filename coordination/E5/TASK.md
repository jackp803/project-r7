# E5 Current Task

- task_id: `E5-20260821-003`
- issued_at: `2026-08-21T10:07:00+08:00`
- state: `HOLD`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, Product Owner decision `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`

## Objective

Freeze the statically accepted E5 Risk/Position correction while E7 resolves executable entry-instruction semantics and the new OKX execution target is incorporated into cross-module adapter/sizing design.

The Product Owner has changed the V1 broker target from Pionex to a dedicated OKX sub-account. This HOLD does not authorize new broker-specific risk implementation yet.

## Accepted static evidence

- corrected revision: `cb65c951d59f6fd036bd61691d7e96d025e371c8`
- finding `E5-RISK-UNKNOWN-001`: `STATICALLY_RESOLVED / PASS (static)`
- executable verification: `NOT_RUN`

## Product target amendment

Future E5/E4 integration must account for OKX derivative contract sizing without moving exchange API responsibilities into E5.

Safety baseline for the future boundary:

- E5 remains authority for maximum approved exposure/risk bounds;
- E4/provider adapter may quantize to exchange contract units only within those bounds;
- exchange quantization may round down or reject, never round up above E5-approved exposure;
- unknown/stale/incompatible instrument metadata must block new exposure;
- E5 does not call OKX private APIs and does not manage API credentials;
- dedicated sub-account isolation does not replace E5 risk checks.

## Required actions

1. Do not modify the E7-accepted fail-closed correction during this HOLD.
2. Preserve `TradeIntent -> RiskDecision -> ApprovedTradePlan` authority.
3. Do not invent final `entry_instruction` semantics before E7's contract/version decision.
4. Do not implement OKX `sz`, `ctVal`, `lotSz`, `minSz`, `tickSz`, leverage-setting, account-mode, or broker-call logic in E5 during this HOLD.
5. Do not add Pionex-specific logic.
6. Do not add production risk values, sizing expansion, exit features, PAPER, SHADOW, or LIVE authority.
7. Keep executable evidence `NOT_RUN` until approved local execution.
8. If acknowledging HOLD, update only `coordination/E5/STATUS.md`.

## Acceptance

- accepted correction remains intact;
- E5 remains broker-API independent;
- no Pionex-specific new work;
- no premature OKX sizing semantics are stabilized;
- no shared-contract change;
- no GitHub compute/CI;
- no executable PASS claim.

## Writable scope

Only `coordination/E5/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for the E7 contract/OKX boundary decision. Do not start another feature automatically.
