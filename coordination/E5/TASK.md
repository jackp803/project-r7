# E5 Current Task

- task_id: `E5-20260825-027`
- issued_at: `2026-08-25T13:39:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-c-risk-context-20260825`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75, accepted E1 current-market PR #76 merge `61ea28f8b6d3ea6cd54e0abb84299303d490a63d`, accepted E4 read-only Shadow reader PR #78 merge `562c4c324129557e5d565b1a37deb49d2c007429`, accepted E4 runtime-only balance handoff PR #79 merge `9de9a7f457f4c3d577229b9a667e8d14cc2226ee`, Product Owner Gate C / SHADOW-only authorization

## Objective

Close only the E5 Phase-2 Gate C gap identified by `status/e7/GATE_C_READINESS_BASELINE_20260825.md`: add a pure, broker-neutral derivation/validation layer that converts the accepted E1 current market observation and accepted E4 normalized read-only Shadow observation/runtime balance into the existing E5 `RiskContext` without trusting caller-asserted market/account/position/order safety flags.

Do not implement provider networking, authentication, persistence, execution, strategy logic, or new risk policy.

## Accepted inputs

The derivation may consume only already-normalized runtime facts needed for Gate C, including:

1. E1 canonical `MarketSnapshot` semantics from the accepted current-market surface;
2. E4 `OKXShadowReadResult` semantics:
   - sanitized observation facts only for provider/account/position/order health;
   - same-batch `runtime_available_balance` only for the existing `RiskContext.available_balance`;
3. E5-owned risk-runtime state/counters already required by existing risk policy, such as kill-switch state, trades today, consecutive losses, and drawdown;
4. an explicit UTC risk-evaluation time so freshness is evaluated at the actual decision boundary.

Do not parse OKX payloads, sign requests, inspect credentials, call provider endpoints, or accept a second independently supplied balance/safety flag that could contradict the accepted E4 batch.

## Required derivation semantics

Implement the smallest E5-owned pure surface that deterministically derives the existing `RiskContext` and, if useful, a bounded E5-local derivation result/reason-code wrapper. Do not create a new shared contract.

### Market

- Canonical symbol must be `BTC_USDT_PERP`.
- E1 `health_status` must be `HEALTHY` and required timestamps/freshness metadata must be valid.
- Re-evaluate freshness at the supplied risk-evaluation boundary; an observation older than the Gate C `5,000 ms` limit is stale even if it was healthy when E1 first produced it.
- Materially future, missing, malformed, contradictory, or non-monotonic time/freshness material must fail closed.
- Only then derive:
  - `market_health_status = HEALTHY`
  - `market_data_fresh = True`
- Otherwise derive an unsafe/non-healthy context; never upgrade stale/unknown data to healthy.

### Account

Derive account state as safe/known only when the accepted E4 batch is internally consistent and healthy, including all required accepted facts:

- sanitized observation health is `HEALTHY` with no blocking reason codes;
- production read-only Shadow environment/provider/instrument identity is the accepted Gate C identity;
- clock status is healthy and skew is within accepted policy;
- permission category is exactly `read_only`;
- account config/sub-account/account-mode facts are known/accepted;
- `usdt_balance_known = True` and same-batch runtime available balance exists as finite non-negative `Decimal`.

Only then derive:

- `account_state_status = KNOWN`
- `account_state_known = True`
- `available_balance =` the exact same-batch runtime Decimal

On any degradation, contradiction, missing balance, or invalid runtime balance, fail closed and do not expose a usable `RiskContext.available_balance`.

The exact balance remains runtime-sensitive. E5 must not log, persist, include in STATUS/handoff evidence, or create durable/public serialization for the real value.

### Position

Derive safe flat position state only when E4 reports current position truth known and no unexpected exposure.

Only then derive:

- `position_state_status = FLAT` (or existing E5-safe equivalent already accepted by the engine)
- `position_state_known = True`
- `open_position_count = 0`
- `same_symbol_position_open = False`

Unknown position truth, contradictory facts, or any unexpected/non-zero exposure must fail closed and must not be interpreted as flat.

### Order / recent execution activity

Derive safe order state only when E4 observation is healthy and proves:

- pending-order count is known and exactly zero;
- recent-fill/unreconciled activity is known and exactly zero under the accepted checkpoint semantics;
- no degraded provider/order/fill reason is present.

Only then derive:

- `order_state_status = KNOWN`
- `order_state_known = True`

Any pending order, new/unreconciled fill, checkpoint regression/unknown state, or provider degradation must fail closed.

### E5-owned risk state

- Preserve current `RiskPolicy`, caps, sizing, loss limits, daily-trade limits, drawdown rules, consecutive-loss rules, no-martingale rules, and kill-switch semantics unchanged.
- E5-owned counters/state may be inputs, but validate their type/range exactly as current risk engine requires.
- `new_exposure_allowed` must never become true merely because a caller says so. It must be derived false whenever market/account/position/order derivation is unsafe or kill switch is active; otherwise preserve existing E5 policy semantics.
- Do not loosen `_validate_context`, `RiskPolicy`, `RiskDecision`, `ApprovedTradePlan`, position lifecycle, or protection rules to make Gate C pass.

## Fail-closed / contradiction requirements

At minimum, reject/derive unsafe context for:

- stale E1 market observation at decision time;
- future/malformed/contradictory market timing;
- E1 symbol mismatch or non-healthy status;
- degraded E4 observation;
- permission not exactly read-only;
- account/config/balance unknown;
- `usdt_balance_known=True` but runtime balance absent or invalid;
- unexpected exposure or position unknown;
- pending order count nonzero/unknown;
- new or unreconciled fill activity nonzero/unknown;
- E4 observation identity/environment/instrument mismatch;
- E4 `HEALTHY` status contradicted by blocking reason codes or unsafe facts;
- invalid E5 risk counters/drawdown/kill-switch state.

Do not silently coerce contradictions into a safe `RiskContext`.

## Tests

Add/update only E5-owned credential-free tests proving at minimum:

- healthy E1 + healthy E4 same-batch balance + safe E5 counters deterministically derives a fully safe existing `RiskContext`;
- exact runtime Decimal flows into `RiskContext.available_balance` without appearing in loggable/public handoff material;
- 5,000 ms market boundary accepted and `>5,000 ms` rejected at E5 decision time;
- stale/future/malformed/identity-mismatched market observation fails closed;
- degraded E4 observation fails closed even if a runtime balance was parsed earlier in that same batch;
- missing/invalid runtime balance cannot produce `account_state_known=True`;
- unexpected exposure cannot become FLAT;
- pending order/new fill/unknown activity cannot become safe order state;
- contradictions between E4 health and contained facts fail closed;
- kill switch/counter/policy behavior remains unchanged;
- no caller-supplied market/account/position/order safe booleans can bypass derivation;
- downstream existing risk evaluation rejects an unsafe derived context and can consume the healthy derived context without changing existing risk-policy semantics.

Use only sanitized/fake runtime objects. No provider network or credential use.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, credential-free verification for this bounded task. If available, run only relevant E5 suites, for example:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No real provider/private request is part of this task. If approved-local execution is unavailable, record `NOT_RUN` with exact commands. `NOT_RUN != PASS`.

## Writable scope

Only E5-owned paths needed for this task:

- `src/risk/**`;
- `tests/risk/**`;
- `tests/safety/**` only for E5-owned bounded risk derivation scenarios;
- bounded `docs/risk/**`;
- E5 status/handoff artifacts;
- `coordination/E5/STATUS.md`.

Forbidden:

- E1/E2/E3/E4/E6/E7 production/tests;
- provider request/auth/signature/payload parsing;
- storage/migrations/OperationalMode ownership;
- shared contracts/ADR changes;
- credentials/secrets;
- provider/private real requests;
- order submission/provider mutation;
- changes to risk caps/policy intended to loosen acceptance;
- PAPER/SHADOW runtime start;
- LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- unrelated cleanup.

## Acceptance

### DONE

- Gate C normalized observations deterministically derive existing `RiskContext` without caller-asserted safety flags;
- stale/unknown/contradictory provider observations fail closed;
- same-batch runtime balance is used safely and remains non-public/non-durable;
- existing E5 policy/veto behavior is preserved;
- test definitions cover healthy and fail-closed paths;
- local evidence is PASS or explicitly `NOT_RUN` without misclassification;
- commit/push to target branch and terminal E5 STATUS.

### BLOCKED

If the accepted E1/E4 normalized surfaces cannot support trustworthy derivation without changing a shared contract or another owner's production code, stop with exact evidence for E7/PM and do not broaden scope.

## Completion

Execute only this TASK, update `coordination/E5/STATUS.md`, commit/push required work to the target branch, and stop. Do not self-start E7 composition, provider verification, SHADOW runtime, Gate C qualification, or LIVE work.