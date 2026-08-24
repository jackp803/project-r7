# Gate B In-Memory Paper Close-to-TradeResult Integration Review — E7-20260824-045

## Authority / scope

- task_id: `E7-20260824-045`
- target branch: `agent/e7-gate-b-paper-trade-result-integration-20260824`
- reviewed main: `36e9c06ab4d614738bea9a2582e8493fdd3e6d9f`
- authoritative TASK blob: `10da19325df595d401392247fbaff4a694dcaa50`
- parent contract: `contracts-v0.1`
- profiles: `protection-v0.1`, `close-v0.1`, `trade-result-v0.1`, `linear-base-asset-pnl-v0.1`, `funding-allocation-v0.1`
- project executable verification: `NOT_RUN`

This task is static integration/test-definition work only. E7 did not execute project code, tests, Paper runtime verification, Local Runner actions, GitHub Actions/CI, hosted runners, provider/private APIs, credentials, PAPER, SHADOW or LIVE activity.

## Accepted prerequisite revisions reviewed

```text
PR #46 close/TradeResult contract
PR #47 E5 close producer
  merge e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15
PR #48 E4 close consumer + same-position residual/flat truth
  merge 3f7bba953ece100d23c88b86b47df52696adb3a0
PR #49 E5 TradeResult builder
  merge a9edc5db9f31efb0c4a8a0c33d54766093c70392
PR #51 funding-allocation-v0.1 contract
  merge 6950824f6e2e7842718fc29f5e0808f9d8e7b04e
PR #52 E4 canonical Paper ZERO_CONFIRMED funding producer
  merge 844395fce0504573b5ee4932e3aca09101998080
PR #53 E5 canonical funding consumer / audit binding
  merge 84d12e4b7ef3638af6690d38f07ce27d10c54fcd
PR #54 E4 PROTECTION_STOP same-position full-fill flat truth
  merge 62605e7abc86f13a1f3102d057aece3d72d465f1
```

All prerequisite executable verification remains `NOT_RUN`.

## Terminal static disposition

```text
ordinary EXIT in-memory close -> canonical TradeResult
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

EMERGENCY_EXIT in-memory close -> canonical TradeResult
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

full verified PROTECTION_STOP trigger -> canonical TradeResult
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

E4 funding producer -> E5 funding consumer compatibility
= PASS STATIC / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE

CONTRACT_OR_SEMANTIC_GAP = NO
E4/E5 IMPLEMENTATION_GAP IN THESE THREE IN-MEMORY PATHS = NO

Restart/persistence preserves required state
= BLOCKED / E6 IMPLEMENTATION_GAP

Paper E2E closes to TradeResult and persists audit
= BLOCKED / E6 DURABILITY + APPROVED-LOCAL E2E EVIDENCE

Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

`PASS STATIC` is not executable PASS evidence.

## 1. Ordinary EXIT path

The current real production API chain is coherent:

```text
exact CONSISTENT Position
-> E5 authorize_close_position_action(... EXIT ...)
-> E5 EXIT_REQUESTED outcome
-> E4 prepare_close_order(...)
-> POSITION_EXIT / MARKET / reduce_only / exact current quantity
-> PaperBroker.submit_order(...)
-> PaperBroker.record_fill(... actual full Fill + fee evidence ...)
-> PaperBroker.observe_position_after_close(...)
-> exact same-position actual_quantity=0 / CONSISTENT
-> E4 produce_paper_zero_funding_evidence(...)
-> canonical funding-allocation-v0.1 ZERO_CONFIRMED evidence
-> E5 build_trade_result(...)
-> POSITION_CLOSED / CLOSED
-> canonical trade-result-v0.1
```

Static invariants preserved:

- LONG close maps to SELL;
- request is `MARKET` and `reduce_only=true`;
- close quantity equals exact E5-authorized/current Position quantity;
- Fill retains exact plan/action/position/order-role lineage;
- `OrderStatus.FILLED` is not used as flat proof;
- final Position is same `position_id`, zero quantity and `CONSISTENT`;
- fees remain explicit;
- E4 canonical funding evidence is consumed directly by E5;
- TradeResult records exact `funding_evidence_profile_version`, `funding_evidence_id` and status;
- E5 owns `POSITION_CLOSED` and final result; E4 does not reinterpret risk semantics.

## 2. EMERGENCY_EXIT path

The same real chain composes with distinct E5/E4 authority:

```text
EMERGENCY Position
-> E5 EMERGENCY_EXIT PositionAction
-> EXIT_REQUESTED
-> E4 EMERGENCY_EXIT / MARKET / reduce_only request
-> real Paper Fill
-> same-position authoritative flat truth
-> canonical Paper funding evidence
-> E5 build_trade_result
-> POSITION_CLOSED / CLOSED
```

The emergency distinction remains immutable/auditable in:

- `PositionAction.action = EMERGENCY_EXIT`;
- E5 deterministic emergency reason sequence;
- `OrderRequest.order_role = EMERGENCY_EXIT`;
- Fill action/position/order-role lineage;
- final TradeResult `exit_reason_codes` and authority refs.

E4 does not manufacture or replace emergency reasons.

## 3. Full verified PROTECTION_STOP path

The previous E4 same-position flat-truth gap is closed by PR #54.

The current real production chain can establish the required protected lifecycle before the trigger:

```text
OPEN_UNPROTECTED Position
-> E5 build_protect_position_action(...)
-> E4 prepare_protection_order(...)
-> PaperBroker.submit_order(... OPEN ...)
-> PaperBroker.query_order(... exact OPEN truth ...)
-> E5 interpret_protection_result(...)
-> PROTECTION_VERIFIED / OPEN_PROTECTED
```

The integration definition projects only this E5-owned lifecycle outcome back onto the same Position instance. It does not modify E4-owned `position_id`, `actual_quantity`, `broker_state_observed_at`, or `reconciliation_status` facts.

Then:

```text
real full PROTECTION_STOP Fill
-> PaperBroker.observe_position_after_close(... protected same-position source ...)
-> exact full-fill + FILLED + HEALTHY + lineage/time/quantity checks
-> same-position actual_quantity=0 / CONSISTENT
-> E4 canonical Paper ZERO_CONFIRMED funding evidence
-> E5 build_trade_result(... exact PROTECT authority/request/fill ...)
-> exit_reason_codes = [PROTECTION_STOP_FILLED]
-> POSITION_CLOSED / CLOSED
```

No synthetic flat Position or synthetic funding object is used.

## 4. Partial / failed / ambiguous protection remains fail closed

Current production boundaries preserve these safety results:

- partial `PROTECTION_STOP` Fill may not emit ordinary `CONSISTENT` residual/flat truth under V0.1;
- zero/untriggered protection cannot emit flat truth;
- definitive rejected protection maps through E5 to `PROTECTION_FAILED -> EMERGENCY`, not CLOSED;
- ambiguous/degraded submit without accepted reconciliation cannot become `PROTECTION_VERIFIED`;
- ambiguous protection submit cannot produce definitive same-position closure truth;
- `FILLED` alone cannot replace the later same-position flat observation;
- missing/corrupt funding evidence cannot be interpreted as zero by E5;
- cross-plan/cross-position/action/Fill/funding lineage mismatch fails closed;
- quantity conservation and explicit fee evidence remain required.

## 5. Funding producer -> consumer compatibility

PR #52 E4 output is directly compatible with PR #53 E5 input.

Canonical positive path passes the actual mapping returned by:

```python
produce_paper_zero_funding_evidence(...)
```

directly into:

```python
build_trade_result(..., funding_evidence=evidence)
```

No E7 recreation of the mapping is used.

Static compatibility confirmed for:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
source_kind = PAPER_MODEL
source = R7_PAPER_FUNDING_MODEL
source_version = paper-zero-funding-v0.1
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
status = ZERO_CONFIRMED
funding_cost = "0"
cost_currency = USDT
exact trade_plan_id / position_id / symbol / interval
source_complete_through >= interval_end
canonical 17-field funding_evidence_id
```

`calculated_at` is audit metadata, not allocation identity. Reproducing the same immutable evidence with a later `calculated_at` keeps the same `funding_evidence_id`; E5 TradeResult identity likewise remains unchanged because it binds the immutable funding allocation identity material rather than the observation timestamp.

## 6. E7 deterministic definitions materialized

### Current positive integration definitions

`tests/integration/test_gate_b_paper_trade_result_integration.py`

Commit:

```text
0a7c89e35d4b3f53d831e24a258175e024383383
```

Covers:

- ordinary EXIT full real chain to canonical TradeResult;
- EMERGENCY_EXIT full real chain to canonical TradeResult;
- verified full PROTECTION_STOP real trigger/flat/funding/TradeResult chain;
- exact funding evidence audit refs;
- same immutable financial evidence with later `calculated_at` -> same funding and TradeResult identity;
- no provider/private/release-authority fields in positive evidence/result objects.

### Current safety definitions

`tests/safety/test_gate_b_paper_trade_result_safety.py`

Commit:

```text
f396e2d53628b5385954db099dcb406cb2d7a66a
```

Covers:

- FILLED without later same-position flat proof cannot finalize;
- partial PROTECTION_STOP cannot emit closure truth;
- untriggered protection cannot emit closure truth;
- terminal rejected protection enters EMERGENCY rather than CLOSED;
- ambiguous/degraded protection cannot verify/close without reconciliation;
- missing/corrupt funding evidence cannot become zero;
- cross-plan/position/Fill/funding mismatch fails closed;
- quantity conservation and fee evidence remain required;
- TradeResult carries no persistence/restart/release-authority claim.

### Superseded historical blocker definitions

The older `tests/integration/test_gate_b_close_trade_result_chain.py` encoded the pre-PR #52/#54 expected blockers. It was retired as an executable test module and now points to the current definitions.

Commit:

```text
5d30146cb373d6bce52c4b17f6d5ccea1d7dabce
```

Git history retains the historical blocker evidence without polluting future approved-local suites with stale expectations.

## 7. No durable/restart claim

This task does not implement or prove:

- durable `RiskDecision` / `ApprovedTradePlan` Paper authority persistence;
- durable `Position` / lifecycle projection;
- durable `PositionAction`;
- durable `OrderRequest` / `OrderResult` and reconciliation state;
- durable `Fill` set and deduplication;
- durable `FundingAllocationEvidence` and conflict ledger;
- durable `TradeResult`;
- restart recovery of open/protected/exiting positions or orders;
- immutable post-restart audit replay;
- full Paper runtime scheduling/operation.

Current E6 storage remains early Slice 2 Registry persistence only.

## 8. Exact next E6 durability boundary

E7 does not assign or implement this work. The next bounded PM dependency is E6 Paper runtime persistence/restart/audit.

At minimum the durable graph must preserve exact canonical identities and immutable payloads for:

```text
strategy_id + strategy_version
risk_decision_id
trade_plan_id
position_id + lifecycle/reconciliation projection
position_action_id
order_request_id + client_order_id + broker_order_id when known
OrderResult observation/reconciliation status
fill_id + exact request/action/position/order-role lineage
funding_evidence_id + funding lineage key + source/material identity
trade_result_id + exact funding_evidence_id binding
```

Required funding conflict/idempotency rule after restart:

```text
same funding_evidence_id + identical identity material
-> idempotent replay

same funding_evidence_id + different identity material
-> corrupt/conflict / fail closed

different funding_evidence_id for same exact funding lineage key
-> reconciliation conflict / never last-write-wins

durable TradeResult already referencing one funding_evidence_id
+ later conflicting evidence
-> do not mutate/rewrite the TradeResult silently
```

Restart must restore the exact authoritative graph rather than recompute identities or infer zero/flat/closed/verified state from missing rows.

## 9. Release-gate impact

Canonical state after this static review:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path          = NOT_RUN
Drawdown/daily/position/kill-switch                 = NOT_RUN
ordinary EXIT in-memory close -> TradeResult        = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
EMERGENCY_EXIT in-memory close -> TradeResult       = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
PROTECTION_STOP in-memory close -> TradeResult      = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
funding producer -> consumer chain                  = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
Restart/persistence preserves required state        = BLOCKED / E6 IMPLEMENTATION_GAP
Paper E2E closes to TradeResult and persists audit  = BLOCKED / E6 DURABILITY + LOCAL E2E EVIDENCE
Gate B                                             = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE                              = UNAUTHORIZED
```

No `NOT_RUN` is promoted to PASS.

## 10. Future approved-local commands

Not run in this task. After E6 durability prerequisites are accepted and PM explicitly authorizes local execution, relevant commands include:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

These commands are not PASS evidence until executed in a Product Owner-approved local environment against an exact approved revision.

## Verification / scope

```text
project_executable_verification = NOT_RUN
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
contracts / ADR changes by E7 = NONE
Codex ticket = NONE
```

## Completion

E7-20260824-045 completes only the static in-memory Paper close-to-TradeResult integration review/test-definition task. E7 does not self-start E6 persistence/restart/audit, approved-local verification, Gate C, PAPER, SHADOW or LIVE.
