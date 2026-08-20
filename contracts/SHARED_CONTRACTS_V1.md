# Canonical Shared Contracts — V1 Baseline

> Contract set: `contracts-v0.1`  
> Status: `BASELINE`  
> Technical authority: E7  
> Applies to: E1–E7 and bounded Codex fixes

This document materializes the minimum cross-module semantics required for parallel construction. It is language-neutral. Executable schemas/types may later be added under `contracts/` and/or approved shared `src/domain/`, but they must preserve these semantics unless E7 approves a versioned change.

---

## 1. Global conventions

### 1.1 Time

- Canonical internal timezone is UTC.
- Interchange timestamps use RFC 3339 UTC (`...Z`).
- Candle intervals are half-open: `[open_time, close_time)`.
- A candle with `close_time = T` contains market events before `T`; the next candle begins at `T`.
- Provider-specific inclusive close timestamps must be normalized by E1 at the adapter boundary.
- A candle is not usable as a closed candle until the evaluation boundary is at or after `close_time` **and** the source/normalizer marks it finalized.

### 1.2 Financial precision

- Price, quantity, fee, margin, notional, PnL, risk amount, and funding values use decimal arithmetic in executable code.
- At JSON/interchange boundaries they serialize as base-10 decimal strings.
- Binary floating-point values must not become the canonical representation for money/price/quantity semantics.

### 1.3 Identity and immutability

- IDs are opaque strings.
- Strategy identity is `(strategy_id, strategy_version)`.
- Once validation evidence is attached to a strategy version, that exact version is immutable.
- Logic, parameter, timeframe, indicator-semantic, entry, or exit changes require a new `strategy_version`.
- Cross-object references must identify the exact strategy version, not only a display name.

### 1.4 Fail-closed rule

Unknown or inconsistent market, order, account, position, risk, approval, or operational-mode state must never be interpreted as permission for new live exposure.

### 1.5 Common envelope

Every persisted/serialized shared object should carry:

- `schema_version`
- its own stable object identifier where applicable
- `created_at` or domain event timestamp where applicable
- exact upstream identity references necessary for audit/replay

---

## 2. `Candle`

**Producer:** E1  
**Consumers:** E2, E3  
**Purpose:** canonical OHLCV market interval.

Required fields:

- `schema_version`
- `symbol`
- `timeframe` — baseline values: `1m`, `15m`, `1h`, `4h`
- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `is_closed`
- `source`

Optional fields:

- `received_at`
- `source_record_id`

Invariants:

- `open_time < close_time`.
- `low <= open <= high`, `low <= close <= high`.
- volume is non-negative unless an explicitly versioned source semantic says otherwise.
- timestamps are UTC.
- duplicate identity for the same `symbol + timeframe + open_time` must be handled deterministically.
- `is_closed=false` data may not be treated as final by a closed-candle strategy.
- E1 must surface missing/out-of-order/malformed data rather than manufacture normal candles.

---

## 3. `MarketSnapshot`

**Producer:** E1  
**Consumers:** E2, E5, E6  
**Purpose:** current market and market-data-health observation.

Required fields:

- `schema_version`
- `symbol`
- `observed_at`
- `received_at`
- `health_status`
- `source`

Optional market fields when available/required:

- `last_price`
- `best_bid`
- `best_ask`
- `mark_price`
- `index_price`
- `funding_rate`
- `next_funding_at`
- `freshness_ms`

Rules:

- it contains market facts/health, not strategy opinions.
- stale/unknown provider state must map to non-healthy `health_status`.
- consumers may impose stricter freshness thresholds but may not convert stale data to healthy.

---

## 4. `StrategyDefinition`

**Semantic owner:** E2  
**Envelope/version authority:** E7  
**Consumers:** E2, E3, E6

Required fields:

- `schema_version`
- `strategy_id`
- `strategy_version`
- `name`
- `symbol`
- `required_timeframes`
- `parameters`
- `rules`
- `runtime_compatibility`
- `content_hash`
- `created_at`

Rules:

- declarative only; no arbitrary Python/shell/file/network/secret access.
- unsupported primitives/operators fail explicitly.
- same definition + same exact market/state boundary + same runtime version must yield the same E2 decision.
- `content_hash` identifies the immutable serialized strategy content.
- changing material strategy semantics without changing `strategy_version` is forbidden.

---

## 5. `Signal`

**Producer:** E2  
**Consumers:** E3, E5, E6

Required fields:

- `schema_version`
- `signal_id`
- `strategy_id`
- `strategy_version`
- `strategy_content_hash`
- `symbol`
- `evaluated_at`
- `direction` — `LONG | SHORT | NO_TRADE`
- `reason_codes`
- `market_boundary_ref`

Optional fields:

- `reference_price`
- `strategy_stop_level`
- `strategy_target_level`
- `max_hold_seconds`
- structured explanation metadata

Rules:

- a Signal is not an order and carries no live execution authority.
- no future candle/data beyond `evaluated_at` may influence it.
- reason codes must be deterministic for the same input state.

---

## 6. `TradeIntent`

**Producer:** E2  
**Consumer:** E5

Required fields:

- `schema_version`
- `intent_id`
- `signal_id`
- `strategy_id`
- `strategy_version`
- `symbol`
- `direction` — `LONG | SHORT`
- `generated_at`
- `market_boundary_ref`

Optional strategy-requested constraints:

- `entry_reference_price`
- `entry_style`
- `strategy_stop_level`
- `strategy_target_level`
- `max_hold_seconds`

Forbidden authority/content:

- no approved quantity;
- no approved leverage;
- no broker credentials;
- no exchange endpoint;
- no direct order command;
- no claim that risk has approved the trade.

A `TradeIntent` cannot be consumed directly by E4 for execution.

---

## 7. `RiskDecision`

**Producer:** E5  
**Consumers:** E4 gate logic, E6, E7

Required fields:

- `schema_version`
- `risk_decision_id`
- `intent_id`
- `strategy_id`
- `strategy_version`
- `decision` — `APPROVE | REJECT`
- `reason_codes`
- `risk_policy_version`
- `decided_at`
- `market_health_status`
- `account_state_status`
- `position_state_status`

Optional calculated fields:

- `approved_quantity`
- `approved_notional`
- `approved_margin`
- `approved_leverage`
- `margin_mode`
- `estimated_max_loss`
- `estimated_cost`
- `required_stop_level`
- `required_target_level`
- `max_hold_seconds`

Rules:

- approval is impossible while required market/account/order/position state is stale or unknown.
- rejected decisions remain auditable.
- approval does not itself instruct the broker; E5 must emit an `ApprovedTradePlan`.
- risk values must reference the exact policy version used.

---

## 8. `ApprovedTradePlan`

**Producer:** E5  
**Primary consumer:** E4  
**Secondary consumer:** E6

Required fields:

- `schema_version`
- `trade_plan_id`
- `risk_decision_id`
- `intent_id`
- `strategy_id`
- `strategy_version`
- `symbol`
- `direction` — `LONG | SHORT`
- `quantity`
- `leverage`
- `margin_mode`
- `entry_instruction`
- `protection_instruction`
- `created_at`
- `expires_at`
- `risk_policy_version`

Rules:

- it may exist only from `RiskDecision.decision=APPROVE`.
- it is the only strategy-originated object E4 may convert into an executable order request.
- E4 may reject an expired/incompatible plan but may not increase exposure or loosen risk bounds.
- changing quantity/leverage/protection beyond E5-approved bounds requires a new risk decision/plan.

---

## 9. `OrderRequest`

**Producer:** E4 execution adapter  
**Consumer:** E4 broker implementation

Required fields:

- `schema_version`
- `order_request_id`
- `trade_plan_id`
- `client_order_id`
- `symbol`
- `side`
- `order_type`
- `quantity`
- `created_at`

Conditional fields:

- `limit_price`
- `stop_price`
- `reduce_only`
- `time_in_force`

Rules:

- every request must be traceable to an approved trade plan or an E5-authorized position action.
- `client_order_id`/equivalent idempotency identity is stable for a single logical order.
- ambiguous timeout never authorizes blind duplicate submission.

---

## 10. `OrderResult`

**Producer:** E4  
**Consumers:** E5, E6

Required fields:

- `schema_version`
- `order_request_id`
- `client_order_id`
- `broker_order_id` when known
- `order_status`
- `observed_at`
- `execution_health_status`

Baseline `order_status` values:

- `PENDING`
- `OPEN`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELED`
- `REJECTED`
- `EXPIRED`
- `UNKNOWN`
- `RECONCILIATION_REQUIRED`

Optional fields:

- `requested_quantity`
- `filled_quantity`
- `average_fill_price`
- `reject_reason`

Rules:

- requested and filled quantity are never conflated.
- timeout/ambiguous acknowledgement maps to `UNKNOWN` or `RECONCILIATION_REQUIRED` until E4 proves broker truth.
- new exposure is blocked while reconciliation-required state affects position certainty.

---

## 11. `Fill`

**Producer:** E4  
**Consumers:** E5, E6; E3 uses equivalent semantics for replay parity

Required fields:

- `schema_version`
- `fill_id`
- `broker_order_id`
- `client_order_id`
- `trade_plan_id` or authorized position-action reference
- `symbol`
- `side`
- `quantity`
- `price`
- `filled_at`

Optional fields:

- `fee`
- `fee_currency`
- `liquidity_role`

Rules:

- fill quantity/price/time are actual broker/replay facts, never copied from requested values merely for convenience.
- duplicate fills must be detectable by stable identity or approved composite identity.

---

## 12. `Position`

**Shared contract:** E4 supplies broker exposure truth; E5 supplies lifecycle/risk interpretation.  
**Consumers:** E5, E6, E7

Required fields:

- `schema_version`
- `position_id`
- `symbol`
- `side`
- `actual_quantity`
- `average_entry_price`
- `opened_at`
- `broker_state_observed_at`
- `reconciliation_status`
- `lifecycle_state`

Optional fields:

- `unrealized_pnl`
- `realized_pnl`
- `current_stop_level`
- `current_target_level`
- `closed_at`

Baseline `reconciliation_status`:

- `CONSISTENT`
- `UNKNOWN`
- `MISMATCH`
- `RECONCILIATION_REQUIRED`

Baseline lifecycle states:

- `PENDING_ENTRY`
- `OPEN_UNPROTECTED`
- `OPEN_PROTECTED`
- `PROFIT_PROTECTED`
- `EXIT_REQUESTED`
- `CLOSED`
- `EMERGENCY`
- `RECONCILIATION_REQUIRED`

Ownership rule:

- E4 is authoritative for actual broker orders/fills/exposure.
- E5 is authoritative for risk/lifecycle interpretation and required protective actions.
- E6 persists/displays the state; it does not redefine either truth source.

---

## 13. `PositionAction`

**Producer:** E5  
**Consumers:** E4, E6

Required fields:

- `schema_version`
- `position_action_id`
- `position_id`
- `action`
- `reason_codes`
- `risk_policy_version`
- `created_at`

Baseline actions:

- `HOLD`
- `PROTECT`
- `MODIFY_PROTECTION`
- `EXIT`
- `EMERGENCY_EXIT`
- `PAUSE_LIVE`

Rules:

- ordinary `MODIFY_PROTECTION` must not widen loss risk beyond approved policy.
- protective quantity is based on actual filled/open quantity.

---

## 14. `RiskState`

**Producer:** E5  
**Consumers:** E4 exposure gate, E6, E7

Required fields:

- `schema_version`
- `risk_policy_version`
- `observed_at`
- `risk_status`
- `kill_switch_active`
- `new_exposure_allowed`
- `reason_codes`

Optional state:

- `trades_today`
- `open_position_count`
- `consecutive_losses`
- `peak_equity`
- `current_equity`
- `drawdown`

Baseline `risk_status`:

- `NORMAL`
- `DEGRADED`
- `LOCKED`
- `UNKNOWN`

Rule: `UNKNOWN`, `LOCKED`, or active kill switch implies `new_exposure_allowed=false`.

---

## 15. `TradeResult`

**Producer:** integrated E4/E5 close path  
**Consumers:** E3 analytics, E6

Required fields:

- `schema_version`
- `trade_result_id`
- `strategy_id`
- `strategy_version`
- `trade_plan_id`
- `position_id`
- `opened_at`
- `closed_at`
- `entry_quantity`
- `average_entry_price`
- `average_exit_price`
- `gross_pnl`
- `net_pnl`
- `total_fees`
- `exit_reason_codes`

Optional fields:

- `funding_cost`
- `slippage_cost`
- `r_multiple`

Rule: result must remain traceable to the exact strategy, plan, orders/fills, and risk policy involved.

---

## 16. `BacktestResult`

**Producer:** E3  
**Consumers:** E6, E7

Required identity/reproducibility fields:

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

Required core metrics:

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

Evidence sections when performed:

- long/short breakdown
- OOS result
- walk-forward result
- Monte Carlo result
- parameter robustness result
- regime result
- slippage/funding stress result

Rules:

- E3 must use E2 strategy runtime semantics, not a private strategy rewrite.
- missing validation stages are represented as not performed/`NOT_RUN`, not silently passed.
- result PASS does not authorize PAPER or LIVE by itself.

---

## 17. `ValidationDecision`

**Producer:** E3  
**Consumers:** E6, E7

Required fields:

- `schema_version`
- `validation_decision_id`
- `strategy_id`
- `strategy_version`
- `backtest_result_id`
- `validation_policy_version`
- `decision` — `PASS | FAIL | BLOCKED | NOT_RUN`
- `reason_codes`
- `decided_at`

Rules:

- `PASS` means only that the configured validation gate has sufficient passing evidence.
- `NOT_RUN` cannot be promoted to PASS.
- `BLOCKED` means a prerequisite prevents evaluation.
- failed/rejected evidence remains auditable.

---

## 18. `StrategyLifecycleState`

**Persistence/workflow owner:** E6  
**Transition authority:** E7

Baseline states:

- `DRAFT`
- `BACKTESTING`
- `REJECTED`
- `CANDIDATE`
- `PAPER`
- `READY_FOR_APPROVAL`
- `APPROVED`
- `LIVE`
- `DEGRADED`
- `RETIRED`

Baseline legal transitions:

- `DRAFT -> BACKTESTING | RETIRED`
- `BACKTESTING -> REJECTED | CANDIDATE`
- `CANDIDATE -> PAPER | REJECTED | RETIRED`
- `PAPER -> READY_FOR_APPROVAL | REJECTED | RETIRED`
- `READY_FOR_APPROVAL -> APPROVED | REJECTED | RETIRED`
- `APPROVED -> LIVE | RETIRED`
- `LIVE -> DEGRADED | RETIRED`
- `DEGRADED -> LIVE | RETIRED`

Hard rules:

- no `BACKTESTING -> LIVE`.
- rejected versions are retained.
- state transition must preserve actor, timestamp, previous state, new state, evidence/reason, and exact strategy version.
- `READY_FOR_APPROVAL -> APPROVED` requires the currently defined approval authority/evidence; for first LIVE use this includes explicit Product Owner approval.
- `APPROVED -> LIVE` also requires current runtime/risk/execution release conditions to remain satisfied.
- recovery `DEGRADED -> LIVE` requires explicit authorized resumption; it is never automatic merely because a new signal arrives.

---

## 19. `OperationalMode`

**Authoritative persisted owner:** E6  
**Consumers:** E4, E5, E7

Baseline modes:

- `RESEARCH`
- `PAPER`
- `SHADOW`
- `LIVE`
- `PAUSED`
- `LOCKED`

Required fields:

- `schema_version`
- `mode`
- `changed_at`
- `changed_by`
- `reason_codes`
- `approval_record_id` when required

Rules:

- UI labels are not authoritative mode changes.
- `LIVE` requires backend gate validation and explicit Product Owner authorization under current policy.
- `LOCKED` cannot be cleared by strategy output.
- risk or unknown-state conditions may block live order submission even while persisted mode says `LIVE`.

---

## 20. `HealthStatus`

**Producers:** E1, E4, E5 for their own health domains  
**Consumers:** E6, E7 and risk/execution gates

Baseline values:

- `HEALTHY`
- `DEGRADED`
- `UNHEALTHY`
- `UNKNOWN`

Rules:

- no false-green mapping: `UNKNOWN` is never displayed/treated as `HEALTHY`.
- health includes timestamp/source/reason codes.
- consumers may fail closed on `DEGRADED` depending on operation.

---

## 21. `ApprovalRecord`

**Producer:** authorized human action captured by E6 workflow  
**Consumers:** E6, E7, E4/E5 gating where applicable

Required fields:

- `schema_version`
- `approval_record_id`
- `approval_type`
- `subject_type`
- `subject_id`
- `subject_version` when versioned
- `actor`
- `decision` — `APPROVE | REJECT`
- `decided_at`
- `reason`

Rules:

- immutable audit record.
- real credentials are never stored in it.
- approval must bind to the exact strategy/release/mode subject, not a vague display label.
- presence of API credentials is not an approval record.

---

## 22. Release evidence status semantics

E7 release/integration checks use exactly:

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — evidence demonstrates the criterion is not satisfied.
- `BLOCKED` — prerequisite/contract/environment prevents evaluation.
- `NOT_RUN` — required executable verification has not been run in an allowed environment.
- `NOT_APPLICABLE` — criterion is explicitly outside the evaluated slice/gate.

Hard rule: `BLOCKED` and `NOT_RUN` are never treated as PASS.

---

## 23. Backtest / Paper / Live semantic parity

The architecture target is:

```text
one StrategyDefinition
        +
one E2 Strategy Runtime semantics
        |
        +--> E3 Backtest caller
        +--> Paper caller
        +--> Shadow/Live-compatible caller
```

Environment-specific execution/fill behavior may differ, but strategy decision semantics may not be privately reimplemented by E3, E4, or another live runtime.

---

## 24. Security and GitHub compute constraints

- No real secrets in any shared object, fixture, example, log, screenshot, issue, PR, or repository file.
- GitHub is source control/PR/Issue/docs/shared memory only.
- No GitHub Actions, GitHub CI, hosted runner, GitHub-triggered runner, scheduled backtest, E2E, bug reproduction, Monte Carlo, regression, performance/load test, or project-code execution.
- Verification runs locally or in another Product-Owner-approved non-GitHub environment.
- If unavailable, record `NOT_RUN` plus the exact local command.

---

## 25. Next materialization

Executable schemas/types must be introduced incrementally with the vertical slices:

1. Slice 1 first: `Candle`, `StrategyDefinition`, `Signal`, `BacktestResult`.
2. Slice 2: `ValidationDecision`, lifecycle/evidence references.
3. Slice 3: `TradeIntent`, `RiskDecision`, `ApprovedTradePlan`, `OrderRequest`, `OrderResult`, `Fill`, `Position`, `PositionAction`, `RiskState`, `TradeResult`.
4. Slice 4+: operational/approval/health refinements required for Shadow and Tiny Live.

Any executable representation must conform to this baseline or carry an E7-approved versioned deviation.