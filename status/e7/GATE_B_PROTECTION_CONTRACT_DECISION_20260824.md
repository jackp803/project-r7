# Gate B Actual-Fill Protection Contract Decision — E7-20260824-028

## Authority / scope

- task_id: `E7-20260824-028`
- target branch: `agent/e7-gate-b-protection-contract-20260824`
- reviewed main: `6299df81c1fc0986e28f9fc6cd0a81fdb60d3a48`
- authoritative TASK blob: `8f54d1a28dc307645faa09ba7ef72a14dfcbe67b`
- parent contract: `contracts-v0.1 / BASELINE`
- prior execution profiles: `entry-v0.1`, `base-asset-v0.1`
- accepted blocker task: `E5-20260824-008 / CONTRACT_OR_SEMANTIC_GAP`
- blocker PR: `#36 / merge d4467e50d300114401b7fda6d5d9f8b688d82638`
- blocker artifact: `status/E5_GATE_B_FILL_PROTECTION_BLOCKER_20260824.md`
- project executable verification: `NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION`

No E4/E5/E6 production code, domain tests, provider adapter, Paper runtime, credential path, or release-gate execution was changed or run by this task.

## Decision

```text
E5-20260824-008 shared semantic blocker = RESOLVED BY CONTRACT
profile = protection-v0.1
parent schema_version = contracts-v0.1
contract-set version bump = NO
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Authoritative artifacts:

- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `docs/adr/ADR-0004-actual-fill-protection-action-boundary.md`
- `contracts/README.md` registry entry

## Why the parent version stays `contracts-v0.1`

The parent baseline already says:

- E4 may execute an E5-approved plan or E5-authorized PositionAction;
- protective quantity must follow actual filled/open quantity;
- E4 owns actual broker/fill/exposure truth;
- E5 owns risk/lifecycle/protection authority;
- `OrderRequest` must be traceable to plan or authorized action.

The missing part was an executable provider-neutral shape. `protection-v0.1` adds fields only when the new profile is declared; it does not reinterpret existing entry objects or legacy audit objects. Legacy objects remain non-executable for this new path and fail closed rather than being guessed or rewritten.

## Actual-fill quantity decision

For ordinary initial `PROTECT`, E5 must consume an exact normalized Position observation whose:

```text
reconciliation_status = CONSISTENT
actual_quantity > 0
```

and whose identity, timestamp, symbol, side, canonical quantity profile/unit/asset, and quantity are known.

The action quantity is:

```text
PositionAction.quantity = exact Position.actual_quantity
```

It is not requested entry quantity and not automatically the full ApprovedTradePlan quantity. Therefore a partial fill is represented exactly.

The quantity uses existing:

```text
base-asset-v0.1
BASE_ASSET
BTC for BTC_USDT_PERP
```

Provider-native contract counts / OKX `sz` remain E4 adapter facts.

Zero/negative/unknown/unreconciled/mismatched quantity cannot produce ordinary PROTECT. If actual exposure is greater than the parent ApprovedTradePlan maximum quantity, the plan is not silently expanded; ordinary PROTECT fails closed into the separately authorized reconciliation/emergency path.

## Protection authority / lineage decision

`protection-v0.1` PositionAction carries exact lineage to:

- `trade_plan_id`;
- `risk_decision_id`;
- `risk_policy_version`;
- `position_id`;
- exact `position_observed_at`;
- canonical symbol/side/quantity;
- exact parent protection instruction.

For initial `PROTECT`, stop, optional target, and max-hold values must equal the parent ApprovedTradePlan protection instruction.

The V0.1 executable path supports only `PROTECT`. Baseline `MODIFY_PROTECTION` remains a valid vocabulary value but is not execution-eligible until a future E7 profile defines side-aware monotonic tightening. This prevents ordinary modification from silently widening loss risk.

## E4 OrderRequest authority resolution

The parent `OrderRequest.trade_plan_id` remains required for every request and means parent-plan lineage.

A protection request additionally identifies the immediate E5 authority:

```text
authorization_type = POSITION_ACTION
position_action_id = <exact E5 action>
position_id        = <exact position>
risk_decision_id   = <parent risk lineage>
order_role         = PROTECTION_STOP
```

The V0.1 mechanical mapping is:

```text
LONG  -> SELL
SHORT -> BUY
order_type  = STOP_MARKET
quantity    = exact action quantity in canonical units
stop_price  = exact approved stop_level
reduce_only = true
limit_price = null
time_in_force = null
```

`client_order_id` is stable for the logical tuple `(position_action_id, PROTECTION_STOP)` or an equivalent deterministic collision-resistant identity.

E4 must validate the PositionAction against the exact parent ApprovedTradePlan and exact current E4-normalized Position truth. It may reject stale/mismatched inputs but cannot replace quantity, side, stop, target, or risk policy.

## Target / max-hold boundary

The action retains optional target and max-hold values because they are approved E5 bounds. This profile does not authorize E4 to invent a take-profit order, OCO linkage, or exit timer.

A later explicit PositionAction/profile or E5 lifecycle implementation is required for those executable behaviors. Their absence does not weaken the required protective stop.

## Lifecycle decision

The existing state machine is retained without semantic change.

Creating a PositionAction, preparing an OrderRequest, or calling submit is not protection verification.

The position remains:

```text
OPEN_UNPROTECTED
```

until broker truth proves the exact protective request is active/effective for the authorized quantity and bound with no reconciliation ambiguity and E5 consumes that verified evidence.

Then and only then:

```text
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
```

Definitive initial protection failure preserves:

```text
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
```

Previously verified protection loss preserves:

```text
OPEN_PROTECTED/PROFIT_PROTECTED + PROTECTION_LOST -> EMERGENCY
```

Unknown/unreconciled truth never counts as `PROTECTION_VERIFIED`.

## Static downstream sufficiency review

### E5 producer sufficiency — PASS STATIC

E5 can implement the next bounded producer task without inventing shared fields:

```text
known CONSISTENT Position observation
+ exact ApprovedTradePlan
-> protection-v0.1 PositionAction.PROTECT
```

The profile defines actual quantity, canonical units, source observation binding, plan/risk lineage, protection bounds, freshness, failure conditions, and legacy fail-closed behavior.

### E4 consumer sufficiency — PASS STATIC

E4 can implement the next bounded consumer task without choosing risk semantics:

```text
protection-v0.1 PositionAction
+ exact parent ApprovedTradePlan
+ current normalized Position truth
-> deterministic protective OrderRequest
```

The profile defines immediate authority, parent lineage, side, quantity, canonical unit/profile, order role/type, stop price, reduce-only behavior, idempotency identity requirement, and lifecycle verification boundary.

No deeper architecture/product decision is required before these bounded implementations.

## Dependency-ordered next bounded work

E7 does not assign tasks; PM remains tasking authority. The safe dependency order is:

1. **E5 producer implementation first**
   - materialize `protection-v0.1 PositionAction.PROTECT`;
   - bind exact Position observation + parent ApprovedTradePlan;
   - cover partial actual quantity, zero/unknown/unreconciled, over-approved exposure, exact bound copying, expiry, legacy profile rejection, and non-executable MODIFY_PROTECTION.
2. **E4 consumer/translation implementation second**
   - add the profile-specific PositionAction consumption path and additive OrderRequest/Fill lineage;
   - mechanically map to reduce-only `PROTECTION_STOP / STOP_MARKET`;
   - validate parent plan and current Position truth;
   - preserve deterministic idempotency/reconciliation;
   - do not add provider/private scope unless a separate task authorizes it.
3. **E7 integration/safety test-definition task after E5+E4 interfaces materialize**
   - partial fill -> exact protection quantity;
   - raw/requested quantity cannot substitute for actual quantity;
   - no risk-bound loosening;
   - request/submission does not equal PROTECTION_VERIFIED;
   - rejection/failure -> EMERGENCY;
   - unknown/reconciliation state blocks verification/retry;
   - exact plan/action/position lineage and idempotency.
4. **Later approved local-only executable evidence**
   - only after the implementations/test definitions exist and PM/Product Owner authorizes a bounded local verification task.

## Verification / safety

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
Local Job = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
provider/private API = NOT_SENT
exchange credentials = NOT_USED
PaperBroker runtime = NOT_RUN
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No executable PASS is claimed.

## Release impact

The contract/semantic blocker is resolved, but the release criterion is not.

```text
Required protection follows actual filled quantity = BLOCKED pending implementation + local evidence
Protection failure triggers emergency path = BLOCKED pending implementation + local evidence
Gate B = BLOCKED / NOT YET PASS
Gate C/D = BLOCKED / UNCHANGED
```

## Completion

`E7-20260824-028` is complete as a static contract/architecture decision. E7 stops after persisting the profile, ADR, registry update, evidence, and STATUS. It does not start E5/E4 implementation, Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
