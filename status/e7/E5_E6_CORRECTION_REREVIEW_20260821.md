# E7 Static Re-review — E5/E6 Corrections

> Task: `E7-20260821-001`  
> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Review type: static source/test/branch review only  
> Contract baseline: `contracts-v0.1`  
> Executable evidence: `NOT_RUN`

## Scope

This review is limited to the two corrections named by the authoritative E7 task:

- E5 `E5-RISK-UNKNOWN-001`, corrected revision `cb65c951d59f6fd036bd61691d7e96d025e371c8`
- E6 `E6-EVIDENCE-CONTRACT-001`, corrected revision `4a845ff79ba48abb6122191a2cf8df7d52544475`

E4 is outside this re-review and remains under a separate PM-issued construction task. E7 does not review or modify E4 in this task.

No executable project code was run. No GitHub Actions, CI, hosted runner, GitHub-triggered runner, scheduled compute, backtest, unit test, integration test, or safety test was used.

---

## Disposition summary

| Area | Static disposition | Executable disposition | Owner / next responsibility |
|---|---|---|---|
| E5 `E5-RISK-UNKNOWN-001` | `PASS` — resolved statically | `NOT_RUN` | E5 owns local verification and future branch resync before integration |
| E6 `E6-EVIDENCE-CONTRACT-001` | `PASS` — resolved statically | `NOT_RUN` | E6 owns local verification and future branch resync before integration |
| E4 | `NOT_APPLICABLE` to this re-review; coordination state is `IN_PROGRESS / NOT_REVIEWED_THIS_TASK` | `NOT_RUN` / outside this task | E4 under separate PM task |
| Shared-contract collision | `PASS` — none found in reviewed corrections | `NOT_APPLICABLE` | E7 |
| GitHub-compute policy | `PASS` static policy review — no prohibited workflow/change found | `NOT_RUN` for project verification | E7 / all agents |
| Gate A/B/C/D | `BLOCKED` unchanged | `NOT_RUN` where executable evidence is required | E7 / responsible domain owners |

Static PASS does not imply executable PASS or release-gate PASS.

---

# 1. E5 re-review — `E5-RISK-UNKNOWN-001`

## Reviewed evidence

- coordination status on main: `coordination/E5/STATUS.md`
- corrected source: `src/risk/engine.py` at `cb65c951d59f6fd036bd61691d7e96d025e371c8`
- safety test definitions: `tests/safety/test_e5_fail_closed.py` at the same revision
- handoff: `status/E5_RISK_POSITION_HANDOFF.md` at the same revision

## Acceptance checks

### 1.1 Unsafe/unknown status cannot be made permissive by companion booleans — PASS

E5 now defines explicit E5-local safe allowlists:

- market: `HEALTHY`
- account: `KNOWN`
- position: `FLAT | CONSISTENT`
- order: `KNOWN`

Every unrecognized or non-safe required status produces a rejection reason independently of the boolean companion field. Therefore `UNKNOWN`, `STALE`, `DEGRADED`, `UNSAFE`, `MISMATCH`, `RECONCILIATION_REQUIRED`, or an unknown token cannot become permission simply because `*_known=True` or `market_data_fresh=True`.

These allowlists are explicitly documented as E5-local validation semantics, not new shared-contract enums.

### 1.2 Contradictory status/boolean combinations fail closed — PASS

The correction explicitly detects contradiction between each safe-status interpretation and its companion boolean:

- market status vs `market_data_fresh`
- account status vs `account_state_known`
- position status vs `position_state_known`
- order status vs `order_state_known`

Contradictions add deterministic rejection reason codes; non-boolean flag types also fail closed.

The safety test definitions cover the exact original defect classes, including `UNKNOWN + known=true`, unsafe market state + `fresh=true`, reconciliation-required state, and mismatch state.

### 1.3 Unsafe/forged APPROVE cannot become ApprovedTradePlan — PASS for this finding

`build_approved_trade_plan(...)` still requires `RiskDecision.decision == APPROVE`, matching policy version, matching intent ID, supported shared schema, and complete approved bounds.

The correction additionally re-checks RiskDecision market/account/position state against the same E5-local safe allowlists and rejects an APPROVE object carrying unsafe state. It also rejects an APPROVE object carrying non-empty rejection reasons.

The test definitions include a forged APPROVE whose market state is changed to `UNKNOWN`; plan construction must reject it.

This acceptance is limited to `E5-RISK-UNKNOWN-001` source semantics. Cross-module provenance/authentication of future E4/E5 runtime objects remains an integration concern and is not expanded by this task.

### 1.4 Authority chain preserved — PASS

The reviewed correction preserves:

`TradeIntent -> RiskDecision -> ApprovedTradePlan`

No direct Strategy -> Execution authority, broker logic, or execution bypass is introduced.

### 1.5 Shared contracts / PAPER / SHADOW / LIVE expansion — PASS

No `contracts/**` change is part of the correction. The nested `entry_instruction` and `protection_instruction` shapes remain explicitly provisional and are not asserted as a stabilized shared sub-contract.

No PAPER, SHADOW, LIVE, production risk-policy value, sizing expansion, or broker behavior is introduced.

## Correction-specific scope

The corrected E5 commit `cb65c951d59f6fd036bd61691d7e96d025e371c8` changes only:

- `src/risk/engine.py`
- `tests/safety/test_e5_fail_closed.py`
- `status/E5_RISK_POSITION_HANDOFF.md`

The coordination mailbox update was persisted separately on main.

No position implementation, shared contract, E4, E6, or GitHub workflow file is changed by the correction commit.

## Branch synchronization audit

E5's synchronization claim is confirmed for the correction start point:

- synchronized main: `4c531adc575ddd43f095ab8eabba3cae62ecc7b2`
- synchronization merge commit reported: `7afc026e8f3fdce7bd7efca7e955c841a0173da1`
- static compare from synchronized main to corrected E5 revision uses `4c531...` as merge-base and reports `behind_by=0`

At this E7 re-review, latest main is `03fc829602ffe70f8094d7924df49f5dad97d3c5`; E5 corrected revision is now diverged and `behind_by=6` because main advanced with later coordination work.

This does not invalidate the static finding correction, but E5 must resynchronize with the then-current main before a future integration/merge step. No force/history rewrite is authorized by this review.

## E5 final finding disposition

`E5-RISK-UNKNOWN-001`: **PASS — STATICALLY RESOLVED**.

Executable verification: **NOT_RUN**.

Required local commands remain:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py"
python -m unittest discover -s tests/position -p "test_*.py"
python -m unittest discover -s tests/safety -p "test_*.py"
```

No executable PASS is claimed.

---

# 2. E6 re-review — `E6-EVIDENCE-CONTRACT-001`

## Reviewed evidence

- coordination status on main: `coordination/E6/STATUS.md`
- contract validator: `src/registry/contract_validation.py` at `4a845ff79ba48abb6122191a2cf8df7d52544475`
- public evidence-ingest wrapper: `src/registry/service.py`
- preserved lifecycle implementation: `src/registry/service_base.py`
- regression definitions: `tests/registry/test_evidence_contract_validation.py`
- handoff: `status/E6_EARLY_SLICE2_HANDOFF.md`

## Acceptance checks

### 2.1 Complete canonical BacktestResult shape required before persistence — PASS

The new validator requires all canonical `contracts-v0.1` identity/reproducibility fields:

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

and all canonical core metrics:

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

Validation occurs before the public service delegates to persistence.

The current BASELINE interpretation of `profit_factor=null` when mathematically undefined is preserved; this review does not change the shared contract.

### 2.2 Complete canonical ValidationDecision shape required — PASS

The validator requires:

- `schema_version`
- `validation_decision_id`
- `strategy_id`
- `strategy_version`
- `backtest_result_id`
- `validation_policy_version`
- `decision`
- `reason_codes`
- `decided_at`

The decision enum is limited to `PASS | FAIL | BLOCKED | NOT_RUN`, and `reason_codes` must be a sequence of non-empty strings.

### 2.3 Invalid types/enums/bindings fail closed — PASS

Static checks cover:

- exact `contracts-v0.1` schema
- non-empty identity/version/hash strings
- RFC 3339 UTC timestamp shape
- dataset boundary ordering check
- count metrics as non-negative integers excluding booleans
- financial metrics as finite base-10 decimal strings rather than binary floats
- ValidationDecision enum and reason-code shape

The preserved service binding still checks exact registered strategy identity/content hash through the stored BacktestResult and exact `ValidationDecision.backtest_result_id` parent binding.

### 2.4 Caller PASS/LOCAL_EXECUTION metadata cannot bypass shape validation — PASS

The public `StrategyPlatformService` calls the canonical object validator before metadata validation and before delegating to the persistence implementation.

Therefore caller-provided:

```text
verification_status = PASS
verification_kind   = LOCAL_EXECUTION
```

cannot make a missing-field or incompatible shared object persistable.

The regression definitions explicitly omit every required BacktestResult and ValidationDecision field one-at-a-time while supplying synthetic local PASS metadata and assert rejection before evidence count changes.

### 2.5 E6 does not implement E3 methodology — PASS

The correction validates contract shape/type/binding only. It does not calculate or decide statistical thresholds, robustness, Monte Carlo, walk-forward, OOS quality, or validation-policy methodology.

A structurally complete BacktestResult is only admissible evidence data, not statistical PASS authority.

### 2.6 Lifecycle remains capped at CANDIDATE — PASS

The preserved transition graph remains exactly:

```text
DRAFT -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

`mark_candidate(...)` still requires a stored E3 ValidationDecision with `decision=PASS`, exact identity/content binding, a BacktestResult parent, and complete local PASS metadata for both decision and parent evidence.

No PAPER, READY_FOR_APPROVAL, APPROVED, LIVE, SHADOW, DEGRADED, operational-mode promotion, or generic transition API is introduced.

## Correction-specific scope

E6 reports the correction-specific paths as:

- `src/registry/contract_validation.py`
- `src/registry/service_base.py`
- `src/registry/service.py`
- `tests/registry/test_evidence_contract_validation.py`
- `status/E6_EARLY_SLICE2_HANDOFF.md`
- `status/E6_STATUS.md`
- `coordination/E6/STATUS.md`

No shared contract or storage migration change is required by the correction. Static branch comparison contains only E6-owned registry/storage/tests/docs/status paths and no `.github/workflows` change.

## Branch synchronization audit

E6's synchronization claim is confirmed for the correction start point:

- pre-sync head: `13c67d4fa91e1cf4cc3b5a394c7ce88de0902321`
- synchronized main: `4c531adc575ddd43f095ab8eabba3cae62ecc7b2`
- synchronization merge commit reported: `6f15f8190a597cdf25284f00eb7b84b3c34f73a0`
- static compare from synchronized main to corrected E6 revision uses `4c531...` as merge-base and reports `behind_by=0`

At this E7 re-review, latest main is `03fc829602ffe70f8094d7924df49f5dad97d3c5`; E6 corrected revision is now diverged and `behind_by=6` because main advanced with later coordination work.

This does not invalidate the static correction, but E6 must resynchronize with the then-current main before a future integration/merge step. No force/history rewrite is authorized by this review.

## E6 final finding disposition

`E6-EVIDENCE-CONTRACT-001`: **PASS — STATICALLY RESOLVED**.

Executable verification: **NOT_RUN**.

Required local commands remain:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Correction-focused command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_evidence_contract_validation.py" -v
```

No executable PASS is claimed.

---

# 3. Cross-cutting audit

## Shared-contract collision

`PASS` — no correction modifies `contracts/**` or claims a new shared semantic.

- E5 safe-state allowlists are explicitly local validation summaries.
- E5 entry/protection nested instruction serialization remains provisional.
- E6 evidence validators consume `contracts-v0.1` shape and do not redefine E3 methodology.

## Unsafe defaults / fail-open behavior

`PASS` static review for the two findings.

- E5 unsafe/unknown/contradictory required state now produces rejection.
- E6 incomplete/non-canonical evidence now fails before persistence despite caller PASS metadata.

## Scope violations

`PASS` for reviewed correction scope. No E4/E5/E6 cross-domain implementation rewrite by E7 and no shared-contract change occurred.

## GitHub compute

`PASS` static policy review: no `.github/workflows` correction change or prohibited compute mechanism is present in the reviewed diffs/handoffs.

Project executable verification remains `NOT_RUN`; GitHub repository inspection is not executable evidence.

---

# 4. E4 disposition for this task

E4 is explicitly outside this re-review.

```text
coordination state: IN_PROGRESS
E7 review state:    NOT_REVIEWED_THIS_TASK
formal disposition: NOT_APPLICABLE
```

E4 continues under its separate PM-issued task/branch. E7 does not infer or pre-review its unfinished construction here.

---

# 5. Release-gate bookkeeping

No release gate is advanced by this task.

```text
Gate A — RESEARCH_READY   BLOCKED
Gate B — PAPER_READY      BLOCKED
Gate C — SHADOW_READY     BLOCKED
Gate D — LIVE_READY       BLOCKED
```

Reasons include outstanding local executable evidence and broader integration prerequisites outside this bounded static re-review.

`STATIC PASS != EXECUTABLE PASS` and `NOT_RUN != PASS`.

---

# 6. Completion

Task `E7-20260821-001` is complete for static re-review scope.

- E5 finding: `PASS / STATICALLY RESOLVED`
- E6 finding: `PASS / STATICALLY RESOLVED`
- E4: `NOT_APPLICABLE / IN_PROGRESS / NOT_REVIEWED_THIS_TASK`
- executable evidence: `NOT_RUN`
- release gates: unchanged / `BLOCKED`
- Codex ticket: `NOT_APPLICABLE` — no locally reproduced defect remains from these two static findings

E7 stops after persisting this artifact and updating `coordination/E7/STATUS.md`. No next integration task is started automatically.
