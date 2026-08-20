# E6 Current Task

- task_id: `E6-20260820-002`
- issued_at: `2026-08-20T18:36:00+08:00`
- state: `ACTIVE`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, E7 review `status/e7/POST_SLICE1_CONSTRUCTION_SYNC_REVIEW.md`

## Objective

Correct E7 blocking finding `E6-EVIDENCE-CONTRACT-001` without taking over E3 validation methodology and without expanding the lifecycle beyond the current early Slice 2 subset.

E6 must ensure that only complete, contract-compatible `BacktestResult` and `ValidationDecision` objects can be persisted as promotable evidence.

## Required actions

1. Synchronize `agent/e6-platform` with the latest `main` before correction, preserving existing E6 history. Do not force-rewrite history. If safe synchronization is not possible with the available Git tooling, report `BLOCKED` rather than improvising.
2. In `record_backtest_result(...)` or the equivalent E6 evidence-ingest boundary, reject any `contracts-v0.1` `BacktestResult` missing required identity/reproducibility fields:
   - `schema_version`
   - `backtest_result_id`
   - `strategy_id`
   - `strategy_version`
   - `strategy_content_hash`
   - `runtime_version`
   - `dataset_id`
   - `dataset_hash`
   - `dataset_start`
   - `dataset_end`
   - `cost_model_version`
   - `created_at`
3. Also require all `contracts-v0.1` core BacktestResult metrics before the record can be persisted as promotable evidence:
   - `total_trades`
   - `wins`
   - `losses`
   - `breakeven`
   - `gross_pnl`
   - `net_pnl`
   - `total_fees`
   - `profit_factor`
   - `expectancy`
   - `max_drawdown`
   - `max_consecutive_losses`
4. In `record_validation_decision(...)` or equivalent, require all canonical `ValidationDecision` fields before promotable persistence:
   - `schema_version`
   - `validation_decision_id`
   - `strategy_id`
   - `strategy_version`
   - `backtest_result_id`
   - `validation_policy_version`
   - `decision` with only canonical `PASS | FAIL | BLOCKED | NOT_RUN`
   - `reason_codes`
   - `decided_at`
5. Validate shared-object field types/enums/bindings sufficiently to reject incompatible payloads. This is contract-shape and identity validation only; do **not** duplicate E3 statistical methodology or decide whether a strategy is actually good.
6. Ensure caller-supplied `verification_status=PASS` / `verification_kind=LOCAL_EXECUTION` metadata can never make an incomplete/non-canonical BacktestResult or ValidationDecision promotable.
7. Add deterministic local-only test definitions proving:
   - each required BacktestResult category cannot be omitted and still become candidate evidence;
   - incomplete ValidationDecision cannot become candidate evidence;
   - fake/local PASS metadata does not bypass contract-shape validation;
   - valid-looking BacktestResult shape alone still cannot promote without a valid E3 ValidationDecision;
   - lifecycle remains bounded to `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`.
8. Do not add PAPER / READY_FOR_APPROVAL / APPROVED / LIVE behavior.
9. Preserve fail-closed default E2 compatibility `NOT_RUN` behavior; do not wire a real E2 adapter in this correction task.
10. Update E6 handoff and `coordination/E6/STATUS.md` with corrected revision, changed files, branch synchronization result, and verification state.
11. Executable verification remains local-only. If no Product Owner-approved local environment exists, record `NOT_RUN` plus exact commands.

## Acceptance

Static/source acceptance requires:

- `E6-EVIDENCE-CONTRACT-001` is corrected in source/test definitions;
- incomplete shared evidence cannot be stored as promotable evidence;
- caller metadata cannot bypass canonical contract-shape validation;
- E6 does not duplicate E3 statistical methodology;
- lifecycle remains capped at CANDIDATE;
- no shared contract changes;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` when local execution is unavailable.

## Writable scope

E6-owned paths only:

- `src/registry/**`
- `src/storage/**` only if directly necessary for evidence persistence
- `tests/registry/**`
- `tests/storage/**` only if directly necessary
- E6-owned docs/status/handoff
- `coordination/E6/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E2/E3/E4/E5 production rewrites;
- E3 statistical/validation methodology implementation;
- PAPER/SHADOW/LIVE lifecycle expansion;
- GitHub compute/CI.

## Local verification

If an approved local environment exists, use the E6 handoff commands. Otherwise keep:

```text
NOT_RUN
```

## Completion / status

After correcting the finding and updating handoff/STATUS, stop and wait for E7 re-review. Do not begin another E6 feature automatically.
