# Position Lifecycle Execution Evidence Binding — V0.1

> Parent contract set: `contracts-v0.1`  
> Companion profile identifier: `position-lifecycle-execution-binding-v0.1`  
> Companion to: `position-lifecycle-projection-v0.1`  
> Status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260824-053`

## 1. Purpose

`position-lifecycle-projection-v0.1` already proves which exact E4 broker Position observation E5 interpreted by binding:

```text
lifecycle_source_broker_state_observed_at
== Position.broker_state_observed_at
```

It does not prove which Position-linked E4 OrderRequest / OrderResult / Fill execution evidence E5 had authoritatively interpreted when it emitted that lifecycle projection.

That missing freshness axis allows a durable store to retain an older `OPEN_PROTECTED` lifecycle projection while newer healthy protection execution truth such as `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `EXPIRED`, or `REJECTED` exists. E6 cannot repair this by mapping E4 execution statuses to E5 lifecycle states because that would duplicate E5 semantic authority.

This companion profile supplies the minimum serialized proof required for E6 to answer only:

> Is the latest persisted E5 lifecycle projection bound to the same exact Position-linked E4 execution evidence snapshot that is currently durable?

It does **not** tell E6 what lifecycle state any execution fact implies.

## 2. Compatibility / versioning decision

Classification:

```text
ADDITIVE_COMPANION_PROFILE
schema_version = contracts-v0.1 / unchanged
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1 / unchanged
companion_profile = position-lifecycle-execution-binding-v0.1
```

The existing lifecycle projection profile is not rewritten and existing `lifecycle_projection_id` identities do not change.

Reasoning:

1. the parent contracts already separate E4 execution truth, E5 lifecycle interpretation, and E6 persistence;
2. the missing fact is a previously undefined durability/freshness evidence binding, not a changed meaning of an existing field;
3. introducing required fields directly into `position-lifecycle-projection-v0.1` would change the identity material of already accepted projections;
4. a separate immutable 1:1 companion object preserves all accepted projection identities while allowing Gate B restart consumers to require the new evidence;
5. legacy projections remain valid historical/in-memory lifecycle objects, but a Gate B restart consumer requiring execution freshness must fail closed when the companion binding is absent;
6. no E4 order/fill semantics or E5 transition semantics are changed.

No set-wide schema bump is required.

## 3. Shared object

Canonical shared companion object:

```text
PositionLifecycleExecutionEvidenceBinding
```

Required fields:

- `schema_version` — exactly `contracts-v0.1`
- `lifecycle_execution_binding_profile_version` — exactly `position-lifecycle-execution-binding-v0.1`
- `lifecycle_execution_binding_id` — deterministic content-derived identity defined in section 11
- `position_id` — exact Position identity
- `lifecycle_projection_id` — exact `position-lifecycle-projection-v0.1` projection interpreted by E5
- `lifecycle_revision` — exact revision of that lifecycle projection
- `execution_interpreted_at` — exact `lifecycle_interpreted_at` of the bound lifecycle projection
- `execution_scope` — exactly `POSITION_LINKED_REDUCTION_ORDERS_V0_1`
- `order_evidence` — deterministic ordered sequence defined in section 6
- `execution_snapshot_hash` — deterministic hash of the complete normalized `order_evidence` snapshot defined in section 10

The binding is immutable and belongs to exactly one lifecycle projection.

## 4. Authority model

Authority remains unchanged:

```text
E4 = OrderRequest / OrderResult / Fill / broker Position truth
E5 = lifecycle/risk interpretation and declaration of what E4 evidence it interpreted
E6 = persistence, replay, hash/reference validation, and freshness comparison only
E7 = contract/version/integration/release authority
```

E5 alone produces `PositionLifecycleExecutionEvidenceBinding` as part of materializing one authoritative lifecycle interpretation.

E6 may persist and mechanically validate the binding, recompute the current durable execution snapshot from already-canonical E4 objects, and compare equality. E6 must not infer a `PositionEvent`, lifecycle state, protection condition, exit failure, flatness, or emergency state from the snapshot.

## 5. Gate B evidence scope

For `execution_scope = POSITION_LINKED_REDUCTION_ORDERS_V0_1`, lifecycle-relevant execution evidence is every durable canonical E4 `OrderRequest` satisfying all of:

```text
OrderRequest.position_id == binding.position_id
OrderRequest.authorization_type == POSITION_ACTION
OrderRequest.order_role in {
  PROTECTION_STOP,
  POSITION_EXIT,
  EMERGENCY_EXIT
}
```

For every such request, the snapshot includes:

1. the exact immutable OrderRequest payload;
2. **all** durable OrderResult observations for that `order_request_id`;
3. **all** durable Fill objects belonging to that exact request and Position lineage.

This scope intentionally includes ordinary EXIT, EMERGENCY_EXIT, and PROTECTION_STOP because later execution observations for any of those roles can require fresh E5 interpretation before a prior lifecycle claim remains restart-authoritative.

### 5.1 Why full observation sets are used

The binding does not use only the latest OrderResult. A later-arriving historical observation or Fill is still execution evidence that was not proven covered by an older E5 interpretation. The full canonical observation/fill sets therefore provide a conservative append-safe durability frontier.

A new observation or Fill changes the snapshot even when its semantic timestamp is older than the current latest observation. E6 does not decide whether that fact is semantically irrelevant; fresh E5 interpretation/reattestation is required to make that determination.

### 5.2 Entry-path exclusion

Current `entry-v0.1` requests/fills are intentionally excluded from this V0.1 scope because the pre-position entry path is not uniformly bound by `position_id`; accepted entry Fill objects may legitimately lack `position_id`.

For the current Gate B durable open-position slice, restart-authoritative lifecycle durability begins from an exact canonical `position_id` and E4 Position observation. A future requirement to restart-authoritatively preserve `PENDING_ENTRY` across pre-position entry execution must receive an explicit E7 profile refinement before it can be considered `READY`; E6 must not guess the association from `trade_plan_id` alone.

## 6. Canonical `order_evidence` entry

One `order_evidence` item is required for every in-scope OrderRequest and contains exactly:

- `order_request_id`
- `order_role`
- `order_request_payload_hash`
- `order_result_observation_count`
- `order_result_observation_set_hash`
- `latest_order_result_observed_at` — `null` when no OrderResult exists
- `fill_count`
- `fill_set_hash`
- `latest_fill_at` — `null` when no Fill exists

`order_evidence` is sorted lexicographically by `order_request_id` before snapshot hashing and serialization.

### 6.1 OrderRequest payload hash

`order_request_payload_hash` is:

```text
sha256:<lowercase hex digest>
```

over the complete canonical OrderRequest JSON using UTF-8, lexicographically sorted field names, and compact separators.

### 6.2 OrderResult observation set

For the exact `order_request_id`, every canonical OrderResult observation is represented by the pair:

```text
(observed_at, payload_hash)
```

where `payload_hash` uses the same canonical JSON SHA-256 rule.

The pairs are sorted by:

```text
observed_at ascending, then payload_hash ascending
```

`order_result_observation_set_hash` is the SHA-256 hash of the canonical JSON array of those sorted pairs.

`order_result_observation_count` is the array length.

`latest_order_result_observed_at` is the maximum canonical `observed_at`, or `null` when the set is empty.

Equal `observed_at` with different canonical payload is a conflict and cannot produce a restart-ready snapshot. Identical duplicate observation is replay-safe and contributes only one logical pair.

### 6.3 Fill set

For the exact request, every canonical Fill must retain the accepted request/position/action/order-role lineage. Each Fill is represented by:

```text
(fill_id, filled_at, payload_hash)
```

The tuples are sorted by:

```text
filled_at ascending, then fill_id ascending
```

`fill_set_hash` is the SHA-256 hash of the canonical JSON array of those sorted tuples.

`fill_count` is the array length.

`latest_fill_at` is the maximum canonical `filled_at`, or `null` when the set is empty.

Same `fill_id` with changed canonical payload is conflict/fail closed. Exact duplicate replay is idempotent.

## 7. Relation to existing Position broker binding

The two freshness axes are independent and both are required for Gate B restart authority:

```text
Position broker-fact axis:
  lifecycle_source_broker_state_observed_at
  == exact E4 Position.broker_state_observed_at interpreted by E5

Position-linked execution-evidence axis:
  PositionLifecycleExecutionEvidenceBinding
  == exact normalized E4 OrderRequest/OrderResult/Fill snapshot interpreted by E5
```

A restart consumer may claim the latest lifecycle projection is fresh only when both axes are mechanically current and conflict-free.

A newer raw E4 Position observation still requires E5 re-attestation under `position-lifecycle-projection-v0.1` even if execution snapshot equality holds.

A changed execution snapshot likewise requires a new E5 lifecycle interpretation even when `broker_state_observed_at` has not changed.

## 8. E5 producer rule

For every lifecycle projection intended to be Gate B restart-authoritative, E5 must emit exactly one matching companion binding.

The binding must describe all in-scope E4 execution evidence that E5 actually consumed/considered for that lifecycle interpretation.

If execution evidence advances and E5 determines the lifecycle state changes, E5 emits:

```text
next TRANSITION lifecycle projection
+ new companion binding for that new projection
```

If execution evidence advances and E5 determines the lifecycle state remains unchanged, E5 emits:

```text
next REATTESTATION lifecycle projection
+ new companion binding for that new projection
```

The existing projection profile already permits REATTESTATION against an equal broker Position observation. This companion profile gives that equal-anchor re-attestation an explicit execution-freshness use without changing lifecycle semantics.

E5 must not mutate or replace the binding of an older lifecycle projection to claim it interpreted later evidence.

## 9. E6 mechanical recovery rule

For the latest contiguous valid lifecycle projection of one Position, E6 may return a restart-authoritative/ready claim only if all of the following hold:

1. exactly one valid companion binding exists for that `lifecycle_projection_id`;
2. `position_id`, `lifecycle_projection_id`, `lifecycle_revision`, and `execution_interpreted_at` exactly match the lifecycle projection;
3. every binding-referenced OrderRequest/OrderResult/Fill object exists durably and is canonical/conflict-free;
4. E6 recomputes the complete current durable V0.1 execution snapshot mechanically from the fixed evidence scope;
5. the recomputed snapshot is exactly equal to the bound snapshot and `execution_snapshot_hash`;
6. no unresolved E4 execution-object identity/time/lineage conflict exists;
7. the separate Position broker-observation freshness rules from `position-lifecycle-projection-v0.1` also pass;
8. existing UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED fail-closed rules remain satisfied.

If any condition fails, E6 must not report the old lifecycle projection as `READY`/restart-authoritative.

The E6-local diagnostic may be named, for example, `E5_EXECUTION_REINTERPRETATION_REQUIRED`, but the exact storage API enum is E6 implementation scope. The shared semantic is only:

```text
current durable execution snapshot != latest E5 bound snapshot
-> fresh E5 interpretation required
-> no false READY claim
```

E6 does not infer what the next lifecycle state should be.

## 10. Execution snapshot hash

`execution_snapshot_hash` is computed over canonical material:

```json
{
  "execution_scope": "POSITION_LINKED_REDUCTION_ORDERS_V0_1",
  "position_id": "<position_id>",
  "order_evidence": [ ...sorted canonical entries... ]
}
```

Algorithm:

1. serialize using UTF-8 JSON;
2. field names sorted lexicographically;
3. compact separators;
4. nested `order_evidence` already sorted by `order_request_id`;
5. compute SHA-256;
6. prefix with `sha256:`.

Therefore any newly durable in-scope OrderRequest, any new/different OrderResult observation, or any new/different Fill changes the snapshot hash.

Snapshot equality is a freshness proof only over durable canonical Gate B Paper execution evidence. It is not a provider-ledger completeness proof and does not authorize private/provider mode.

## 11. Binding identity / immutability

`lifecycle_execution_binding_id` is deterministic over the complete immutable binding payload except the ID field itself.

Algorithm:

1. remove `lifecycle_execution_binding_id`;
2. serialize the remaining complete binding as canonical UTF-8 JSON with sorted keys and compact separators;
3. compute SHA-256;
4. prefix the lowercase digest with:

```text
posexecbind_
```

Rules:

```text
same lifecycle projection + same exact execution snapshot -> same binding ID
same binding ID + changed payload -> corrupt/conflict
same lifecycle_projection_id + different binding ID/snapshot -> authority conflict
missing companion binding -> not restart-authoritative
```

There is exactly one immutable binding per restart-authoritative lifecycle projection.

## 12. Missing / unknown / conflict behavior

The following must fail closed and cannot yield a `READY` restart claim:

- missing companion binding;
- unsupported binding profile/scope;
- binding/projection ID or revision mismatch;
- binding time not equal to lifecycle interpretation time;
- referenced durable object missing;
- in-scope durable request absent from the binding snapshot;
- changed/new OrderResult observation after binding;
- changed/new Fill after binding;
- changed/new in-scope PositionAction-authorized request after binding;
- equal-time conflicting OrderResult;
- conflicting Fill identity/payload;
- conflicting OrderRequest identity/payload;
- binding identity conflict;
- snapshot hash mismatch;
- unknown/ambiguous/degraded execution state under existing rules;
- newer raw broker Position observation not covered by an E5 projection/reattestation.

Missing evidence is not interpreted as healthy, unchanged, protected, flat, or closed.

## 13. Deterministic scenarios

### A. Protection remains active

E5 emits `OPEN_PROTECTED` and a binding covering the exact PROTECTION_STOP request plus the authoritative OPEN OrderResult observation it interpreted.

If durable E4 execution snapshot remains byte-equivalent under this profile, the execution-freshness axis remains current. Other recovery criteria still apply.

### B. Later partial/full protection execution

After the binding, E4 emits a new PARTIALLY_FILLED or FILLED OrderResult and/or Fill.

The durable snapshot hash changes.

```text
old binding != current snapshot
-> E6 requires fresh E5 interpretation
-> E6 does not infer RECONCILIATION_REQUIRED or CLOSED
```

E5 may then emit the appropriate TRANSITION or REATTESTATION plus a new binding after consuming authoritative Position/close truth.

### C. Later inactive protection truth

After the binding, a CANCELED, EXPIRED, or REJECTED OrderResult is durable.

The snapshot changes and prevents the old `OPEN_PROTECTED` projection from being restart-ready.

E6 does not infer `PROTECTION_LOST` or `EMERGENCY`; E5 remains responsible for that interpretation.

### D. Ambiguous/degraded truth

UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED remains independently fail closed. Matching a binding never converts ambiguous E4 execution truth into healthy state.

### E. POSITION_EXIT / EMERGENCY_EXIT / PROTECTION_STOP

The same rule applies to all three order roles.

For POSITION_EXIT and EMERGENCY_EXIT, later partial fills, terminal failures, fills, or other observations may require E5 to retain `EXIT_REQUESTED`, enter `EMERGENCY`, enter reconciliation, or later close only after authoritative Position truth. E6 cannot decide among those outcomes.

For PROTECTION_STOP, later trigger/fill/inactive observations likewise affect lifecycle interpretation.

Therefore all three roles are in scope now; leaving explicit close roles outside the binding would reproduce the same authority gap already proven for protection.

## 14. Downstream ownership

Required dependency order after this contract is accepted:

```text
E7 contract + ADR resolution
-> E5 bounded producer adaptation:
   emit one position-lifecycle-execution-binding-v0.1 companion for each
   Gate B restart-authoritative lifecycle projection, using exact E4 evidence
-> E6 bounded mechanical consumer/recovery adaptation:
   persist binding, recompute snapshot, compare equality, fail closed on mismatch
-> E6 separate settled-contract repair:
   TradeResult referenced OrderRequest/Fill/PositionAction graph completeness
-> E7 durable Paper integration/E2E/safety re-review/definitions
-> PM-authorized approved-local Gate B verification
```

No E4 production contract change is required. Existing E4 canonical OrderRequest / OrderResult / Fill facts already provide the evidence material.

## 15. Security / release scope

This profile contains no provider-native payload, API credential, token, account secret, network instruction, capital authority, strategy promotion, or release authorization.

```text
project executable verification = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
provider/private API = NOT AUTHORIZED
```

Static contract resolution does not convert any executable criterion to PASS.
