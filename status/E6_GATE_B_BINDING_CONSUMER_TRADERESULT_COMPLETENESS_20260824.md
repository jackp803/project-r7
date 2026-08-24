# E6 Gate B Binding Consumer + TradeResult Completeness Handoff

**From:** E6 / Platform / Storage / Strategy Registry / Dashboard Engineer  
**To:** PM / E7 review queue  
**Task:** `E6-20260824-017`  
**Branch:** `agent/e6-gate-b-binding-consumer-traderesult-completeness-20260824`  
**Task-start main:** `70aac8dc972eb24a436ab4c86e2dc77d2f383bca`  
**Disposition:** `DONE / STATIC IMPLEMENTATION + TEST DEFINITIONS MATERIALIZED / EXECUTABLE NOT_RUN`

## 1. Objective

Implement only the two bounded E6 durability repairs requested by `E6-20260824-017`:

1. consume/persist/recover the accepted E5 `position-lifecycle-execution-binding-v0.1` companion and mechanically detect execution-evidence freshness mismatch;
2. require durable TradeResult referenced entry/exit OrderRequests, Fills and exit/protection PositionActions to exist with exact lineage before accepting the TradeResult as a complete durable graph.

No E5 state transition logic, E4 broker semantics, shared contracts, provider/private APIs, strategy promotion or release authority was added.

## 2. Binding durability / freshness

Additive migration:

```text
src/storage/migrations/0003_lifecycle_execution_binding.sql
```

It stores one immutable binding per exact lifecycle projection and preserves:

```text
lifecycle_execution_binding_id
lifecycle_projection_id
position_id
lifecycle_revision
execution_interpreted_at
execution_scope
execution_snapshot_hash
exact canonical payload/hash
```

The supported journal surface now accepts an already-canonical E5 binding. E6 validates only serialized shared-contract facts:

```text
schema_version = contracts-v0.1
profile = position-lifecycle-execution-binding-v0.1
scope = POSITION_LINKED_REDUCTION_ORDERS_V0_1
exact position/projection/revision/interpreted-time binding
exact order_evidence shape/order/count/hash fields
exact execution_snapshot_hash
exact posexecbind_ identity
```

E6 does not import E5 production modules and does not reproduce the E5 transition table.

For restart freshness, E6 mechanically recomputes the current durable reduction-order execution snapshot from only:

```text
OrderRequest.position_id == position_id
authorization_type == POSITION_ACTION
order_role in {PROTECTION_STOP, POSITION_EXIT, EMERGENCY_EXIT}
+ all durable OrderResult observations for those requests
+ all durable matching Fills for those requests
```

Entry-v0.1 plan-authorized OrderRequests/Fills are outside this binding scope and are not joined heuristically by `trade_plan_id`.

The recomputation mirrors the accepted PR #63/#64 canonical rules:

- OrderRequest full canonical JSON SHA-256;
- OrderResult pair `[observed_at, payload_hash]`, semantic UTC ordering then hash, all observations retained;
- Fill tuple `[fill_id, filled_at, payload_hash]`, semantic UTC ordering then fill_id;
- order evidence lexicographically sorted by `order_request_id`;
- exact count/latest timestamps/set hashes;
- exact snapshot material/hash.

Recovery behavior is fail closed:

```text
current projection binding missing -> not READY
binding invalid/conflicting -> not READY
current durable execution snapshot != latest E5 binding -> E5_EXECUTION_REINTERPRETATION_REQUIRED / not READY
new matching E5 re-attestation + binding -> may resume normal mechanical evaluation
```

This execution-evidence freshness axis remains independent of the existing newer-raw-Position `E5_REATTESTATION_REQUIRED` broker-fact freshness axis.

## 3. TradeResult referenced-object completeness

Before the supported E6 journal persists a TradeResult, it now mechanically requires the exact referenced graph already serialized by `trade-result-v0.1`:

```text
entry_order_request_ids
exit_order_request_ids
entry_fill_ids
exit_fill_ids
exit_authority_refs.position_action_id
```

Checks include:

- exact durable ApprovedTradePlan lineage;
- entry request plan/symbol/side and plan-authorized-entry boundary;
- entry Fill -> explicit referenced entry request by exact `client_order_id`;
- exit/protection request -> exact position/plan/symbol/risk/action/role lineage;
- exit/protection Fill -> exact referenced request/action/position/role lineage;
- exact exit-authority action/role mapping;
- every referenced request/action/Fill must exist;
- every referenced request/authority must be consumed by the corresponding referenced Fill/request set;
- no overlapping entry/exit Fill identity;
- `flat_position_observed_at == closed_at`.

No fee/PnL/quantity/domain state is recomputed by E6. Existing funding evidence and immutable TradeResult rules remain unchanged.

Recovery also rechecks any durable TradeResult reference graph. Missing references produce incomplete/non-READY recovery; mismatched/conflicting lineage produces fail-closed conflict/non-READY recovery.

## 4. Existing behavior preserved

Preserved from accepted E6 durability work:

- lifecycle vocabulary enforcement;
- lifecycle revision/predecessor/projection identity rules;
- broker-anchor ordering and raw Position re-attestation behavior;
- OrderResult append-only observation history/current projection;
- immutable runtime object identity/conflict behavior;
- funding allocation lineage/conflict behavior;
- immutable TradeResult payload/funding binding;
- early Strategy Registry lifecycle `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`;
- provider-private/secret rejection and no release-authority APIs.

## 5. Deterministic test definitions

Added/updated E6 definitions cover:

- matching binding normal evaluation;
- missing binding;
- projection/revision/time/profile/scope/hash mismatch;
- later PARTIALLY_FILLED/FILLED/CANCELED/EXPIRED/REJECTED execution truth;
- new POSITION_EXIT/EMERGENCY_EXIT evidence;
- binding duplicate replay;
- equal-time OrderResult conflict and immutable Fill/OrderRequest conflicts;
- equal-broker-anchor re-attestation with new matching binding;
- independent raw Position re-attestation requirement;
- entry execution outside binding scope;
- complete TradeResult referenced graph;
- missing entry/exit request, missing entry/exit Fill, missing PositionAction;
- referenced-object lineage/action-role mismatch;
- existing durability close/reopen definitions updated to materialize matching bindings and complete TradeResult references.

These are definitions only. They are not PASS evidence.

## 6. Contracts consumed

- `contracts-v0.1`
- `position-lifecycle-projection-v0.1`
- `position-lifecycle-execution-binding-v0.1`
- `trade-result-v0.1`
- ADR-0007
- ADR-0009
- accepted PR #63 freshness contract
- accepted PR #64 E5 binding producer

Contracts/ADRs produced or changed by E6:

```text
NONE
```

## 7. Local verification

```text
local_verification = NOT_RUN
```

No separate exact-revision Product-Owner/PM-approved Local Runner action was authorized. No unit/integration/restart/migration test, project runtime, provider request, GitHub Actions/CI, hosted runner, GitHub-triggered compute or Computer Adapter project workload was executed.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## 8. Security / live impact

- real secrets/credentials committed: `NONE`
- provider/private API/network work: `NONE`
- GitHub Actions/CI/workflow use: `NONE`
- lifecycle promotion/release authority: `NONE`
- PAPER/SHADOW/LIVE enablement: `NONE`

This task does not place orders or change risk/exposure semantics.

## 9. Release impact / stop

This static E6 completion does **not** claim:

```text
Restart/persistence = PASS
Paper E2E = PASS
Gate B / PAPER_READY = PASS
PAPER / SHADOW / LIVE authorization
```

Those remain subject to PM/E7 review and separately approved local executable evidence.

E6 stops after the terminal mailbox STATUS for `E6-20260824-017` is pushed and does not self-start another task.
