# E5 Current Task

- task_id: `E5-20260824-014`
- issued_at: `2026-08-24T13:04:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-close-producer-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, accepted Gate A PASS, accepted protection chain PR #37-#45, accepted close/TradeResult contract PR #46

## Objective

Implement only the E5-owned **`close-v0.1` EXIT / EMERGENCY_EXIT PositionAction producer and immediate E5 lifecycle/reason semantics** defined by PR #46.

Bounded authority chain:

```text
exact current E4-normalized CONSISTENT Position truth
+ exact parent ApprovedTradePlan / risk lineage
+ E5-owned deterministic exit reason
-> close-v0.1 PositionAction.EXIT or PositionAction.EMERGENCY_EXIT
-> existing E5 EXIT_REQUESTED lifecycle intent
```

Stop at the E5 close-action/lifecycle-authority boundary. Do **not** implement E4 close OrderRequest translation, broker submission/fills, authoritative-flat closure, TradeResult construction, E6 persistence/restart/audit, full Paper E2E, provider/private APIs, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisite / contract decision

PM accepted E7-20260824-036 in PR #46:

```text
PR #46
merge = d070ffc752d5c37c05aa4101ebc2f6add0c1ff48
head = fb0e88466fd4db1ad5e4a8a2c4f3a9366d15dd31
classification = ADDITIVE_PROFILE_REQUIRED / MATERIALIZED
profiles = close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1
schema_version = contracts-v0.1
```

All prior executable Gate B evidence remains `NOT_RUN`. Gate B remains `BLOCKED` and PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E5_RISK_POSITION.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md` and ADR-0005;
- parent `contracts/SHARED_CONTRACTS_V1.md`, protection/execution profiles as needed for compatibility;
- current `src/position/**`, especially protection PositionAction patterns and state machine;
- current E4 normalized Position / execution model surfaces read-only;
- `status/RELEASE_GATES.md` and E7 close/TradeResult decision evidence;
- existing E5 risk/position/safety tests.

If current E7-owned contract semantics are insufficient or contradictory for this producer, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP`, record exact expected-vs-actual evidence and `next_owner = E7`. Do not invent a parallel shared DTO or privately redefine close-v0.1.

## Required behavior

### 1. Exact supported actions and source lifecycle

Materialize executable `close-v0.1` producer behavior for exactly:

```text
EXIT
EMERGENCY_EXIT
```

Ordinary `EXIT` is allowed only from exact current lifecycle state:

```text
OPEN_UNPROTECTED
OPEN_PROTECTED
PROFIT_PROTECTED
```

`EMERGENCY_EXIT` is allowed only from exact current lifecycle state:

```text
EMERGENCY
```

Fail closed for `PENDING_ENTRY`, `EXIT_REQUESTED`, `CLOSED`, `RECONCILIATION_REQUIRED`, unknown/unsupported states, or wrong action/state combinations.

### 2. Actual current exposure is authoritative

A close action may be produced only from an exact current normalized Position observation satisfying the accepted profile, including:

- `schema_version = contracts-v0.1`;
- exact non-empty `position_id` and canonical symbol;
- `side = LONG | SHORT`;
- `reconciliation_status = CONSISTENT`;
- positive finite `actual_quantity`;
- canonical `base-asset-v0.1 / BASE_ASSET` quantity semantics and expected base asset;
- exact UTC `broker_state_observed_at`;
- compatible parent plan symbol/direction/quantity profile;
- current actual quantity does not exceed parent ApprovedTradePlan maximum approved quantity.

Set exactly:

```text
PositionAction.quantity = Position.actual_quantity
```

Never use original requested entry quantity, plan maximum, or provider-native contract count as the close quantity.

Unknown, zero, negative, non-finite, mismatched, stale/unverifiable, `UNKNOWN`, `MISMATCH`, or `RECONCILIATION_REQUIRED` position truth must not produce ordinary executable close authority.

### 3. Exact close-v0.1 payload and lineage

Produce the accepted profile fields without changing shared contracts. The action must carry exact accepted lineage/semantics including at minimum:

```text
schema_version = contracts-v0.1
close_profile_version = close-v0.1
position_action_id
position_id
action = EXIT | EMERGENCY_EXIT
reason_codes
risk_policy_version
trade_plan_id
risk_decision_id
strategy_id
strategy_version
symbol
position_side
source_lifecycle_state
position_observed_at
position_reconciliation_status = CONSISTENT
quantity
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset
close_order_type = MARKET
created_at
expires_at
```

Exact parent-plan invariants must hold for trade plan, risk decision, strategy/version, risk policy, symbol/direction and quantity semantics.

Parent entry-plan TTL is lineage only after exposure exists. It must not be reused as close-action expiry. `expires_at` is the independent close-action freshness boundary and must be later than `created_at`.

### 4. Deterministic E5 reason semantics

`reason_codes` must be a non-empty deterministic E5-owned sequence and part of action identity.

Do not allow E4/provider/broker data to invent or replace E5 exit reasons.

For this bounded producer, materialize deterministic safe semantics sufficient to distinguish at least:

- ordinary requested exit;
- emergency exit from an already-EMERGENCY lifecycle state.

If existing E5 reason vocabulary already has more specific accepted reason codes, preserve/reuse it. Do not invent provider-specific reasons or broaden strategy logic.

The same exact logical authority inputs must yield the same reason sequence and same `position_action_id`; any authority-bearing change must change the action identity.

### 5. Deterministic action identity / freshness

`position_action_id` must be stable/idempotent for one logical close authorization and must change when authority-bearing material changes, including at minimum:

- EXIT vs EMERGENCY_EXIT;
- parent plan/risk decision;
- position ID/side/source lifecycle state;
- position observation timestamp;
- exact close quantity/profile/unit/asset;
- reason codes;
- risk policy version.

Repeated delivery of the same action is idempotent. A newer Position observation, residual quantity, changed emergency reason, or other authority change requires a new action identity.

### 6. Lifecycle intent is explicit but never claims closure

Producing/accepting a close action must explicitly map through the existing E5 state machine to:

```text
OPEN_UNPROTECTED / OPEN_PROTECTED / PROFIT_PROTECTED + EXIT_REQUESTED -> EXIT_REQUESTED
EMERGENCY + EXIT_REQUESTED -> EXIT_REQUESTED
```

The producer may return a bounded E5-owned outcome/decision object if needed, but must not redefine the shared state machine or create a cross-module DTO.

Do not emit/apply `POSITION_CLOSED` in this task. Prepared action, later OrderRequest, submit acknowledgement, or future `OrderStatus.FILLED` is not proof of flatness.

Preserve existing:

```text
EXIT_REQUESTED + EXIT_FAILED -> EMERGENCY
```

but do not implement E4 result/failure interpretation or broker orchestration in this task.

### 7. No exposure/risk escalation

The close producer must never:

- create/increase exposure;
- choose quantity larger than exact current actual exposure;
- widen or reset risk limits;
- bypass current risk/position unknown-state rules;
- silently convert ordinary EXIT into EMERGENCY_EXIT or vice versa;
- treat a new request/intent identity as a reason to bypass lifecycle/risk locks.

### 8. Provider-neutral scope

Do not add OKX/Pionex/private-provider fields, contract counts, network calls, credentials, signatures, provider-native order IDs, or execution behavior.

## Required deterministic tests

Add E5-owned definitions covering at minimum:

- valid `OPEN_UNPROTECTED -> EXIT` action carries exact current actual quantity and exact parent lineage;
- valid `OPEN_PROTECTED -> EXIT` and `PROFIT_PROTECTED -> EXIT` preserve semantics;
- valid `EMERGENCY -> EMERGENCY_EXIT` is distinct/auditable;
- wrong action/lifecycle combinations fail closed;
- zero/negative/non-finite quantity fails closed;
- unknown/mismatch/reconciliation-required Position truth fails closed;
- actual quantity greater than parent approved maximum fails closed;
- plan/risk/strategy/symbol/direction/quantity-profile mismatch fails closed;
- close action uses independent expiry rather than parent entry TTL;
- same exact authority inputs produce deterministic `position_action_id` and reason sequence;
- changed action type, source observation, quantity, reason, or risk lineage changes identity;
- action creation advances only to `EXIT_REQUESTED`, never `CLOSED`;
- no `POSITION_CLOSED` claim is possible without later authoritative flat Position truth;
- existing protection producer/result and state-machine behavior remain compatible;
- no provider-native or credential fields are introduced.

Use sanitized/fake fixtures only. Do not encode E4 broker submission, TradeResult formulas, E6 persistence, or E7 release semantics into E5 unit tests.

## Writable scope

E5-owned paths only:

- `src/position/**`;
- `src/risk/**` only if strictly required for E5-owned close reason/risk validation without changing policy values;
- `tests/position/**`;
- `tests/risk/**` only if needed for compatibility;
- E5-owned `tests/safety/**` only where appropriate;
- E5-specific `status/**` evidence/handoff;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` or ADR edits;
- `src/execution/**` / `src/brokers/**`;
- E6 persistence/registry;
- E2/E3 production;
- shared contract/model expansion outside E5-owned implementation unless terminating on a genuine E7 blocker;
- E4 close OrderRequest translation/submission/fills;
- authoritative-flat closure or TradeResult builder;
- provider/private networking or credentials;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This is implementation/test-definition work. Project execution remains local-only.

If no explicitly PM/Product-Owner-approved Local Runner action exists for the exact clean target revision, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- `close-v0.1` EXIT / EMERGENCY_EXIT producer is materialized under the accepted contract without shared-contract drift;
- close quantity equals exact current known Position.actual_quantity;
- exact parent/risk/strategy/position lineage and deterministic E5 reason semantics are preserved;
- action identity/freshness is deterministic and fail closed;
- lifecycle intent reaches only `EXIT_REQUESTED`, never falsely `CLOSED`;
- invalid/unknown/reconciliation-required truth cannot produce safe close authority;
- no E4/E6/provider/private/TradeResult/release-authority scope is crossed;
- deterministic tests are materialized;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with exact commands.

### BLOCKED

- accepted close-v0.1 semantics cannot be safely materialized without a genuine shared-contract change or unresolved cross-role dependency;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround or parallel DTO.

Do not declare close-to-TradeResult implementation complete, Paper E2E PASS, Gate B/PAPER_READY PASS, or any PAPER/SHADOW/LIVE authority.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence to `agent/e5-gate-b-close-producer-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E5/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E4 close consumer, E5 TradeResult builder, E6 persistence, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.