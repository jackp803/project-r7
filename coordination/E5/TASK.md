# E5 Current Task

- task_id: `E5-20260820-002`
- issued_at: `2026-08-20T18:36:00+08:00`
- state: `ACTIVE`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, E7 review `status/e7/POST_SLICE1_CONSTRUCTION_SYNC_REVIEW.md`

## Objective

Correct E7 blocking finding `E5-RISK-UNKNOWN-001` without expanding E5 scope or changing shared contracts.

The current Risk/Position skeleton has the correct authority chain and lifecycle structure, but contradictory status-string + companion-boolean inputs can be interpreted permissively. Make the required state semantics explicitly fail closed.

## Required actions

1. Synchronize `agent/e5-risk-position` with the latest `main` before correction, preserving existing E5 history. Do not force-rewrite history. If safe synchronization is not possible with the available Git tooling, report `BLOCKED` rather than improvising.
2. In E5-owned risk validation, make required market/account/order/position state semantics fail closed according to `contracts-v0.1`.
3. Explicitly reject canonical/recognized unknown, stale, reconciliation-required, degraded/unsafe required states even when a companion boolean incorrectly claims the state is known/fresh.
4. Explicitly reject contradictory status/boolean combinations rather than choosing the permissive interpretation.
5. Add deterministic safety test definitions covering at minimum:
   - `account_state_status="UNKNOWN"` + `account_state_known=true` -> reject;
   - `order_state_status="UNKNOWN"` + `order_state_known=true` -> reject;
   - `position_state_status="UNKNOWN"` + `position_state_known=true` -> reject;
   - unsafe/stale/degraded market status + `market_data_fresh=true` -> reject;
   - unknown/inconsistent state cannot produce an `APPROVE` RiskDecision or `ApprovedTradePlan`.
6. Preserve the existing `TradeIntent -> RiskDecision -> ApprovedTradePlan` authority chain.
7. Preserve the existing fail-closed position lifecycle; do not add PAPER/LIVE authorization, production risk values, sizing expansion, trailing/BE/structure-exit features, or broker logic.
8. Do not stabilize provisional `entry_instruction` / `protection_instruction` nesting as a new shared contract.
9. Update E5 handoff and `coordination/E5/STATUS.md` with the corrected revision, changed files, finding disposition, branch synchronization result, and verification state.
10. Executable verification remains local-only. If no Product Owner-approved local environment is available, record `NOT_RUN` plus exact commands.

## Acceptance

Static/source acceptance requires:

- `E5-RISK-UNKNOWN-001` is demonstrably corrected in source/test definitions;
- contradictory or unknown required state always fails closed;
- no shared contract changes;
- no E4/E6 implementation rewrite;
- no PAPER/LIVE authority;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` when local execution is unavailable.

## Writable scope

E5-owned paths only:

- `src/risk/**`
- `src/position/**` only if directly necessary for this finding
- `tests/risk/**`
- `tests/position/**` only if directly necessary
- `tests/safety/**` for E5 safety scenarios
- E5-owned docs/status/handoff
- `coordination/E5/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E2/E3/E4/E6 production rewrites;
- new risk-policy production values;
- broker/private Pionex work;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI.

## Local verification

If an approved local environment exists, use the E5 handoff commands. Otherwise keep:

```text
NOT_RUN
```

## Completion / status

After correcting the finding and updating the handoff/STATUS, stop and wait for E7 re-review. Do not begin another E5 feature automatically.
