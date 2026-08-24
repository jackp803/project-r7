# E5 Gate B Lifecycle Execution Evidence Binding Producer — 2026-08-24

- task_id: `E5-20260824-023`
- agent: `E5`
- state: `DONE`
- base_main_sha: `67be8a6f34fca77456e2d21f5d36473b36c4918b`
- target_branch: `agent/e5-gate-b-lifecycle-execution-binding-producer-20260824`
- local_verification: `NOT_RUN`
- next_owner: `PM/E7`

## Contract-first disposition

The accepted PR #63 contract/ADR is sufficient for the bounded E5 producer adaptation.

Consumed authority:

- `contracts-v0.1`
- `position-lifecycle-projection-v0.1`
- `POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`
- `position-lifecycle-execution-binding-v0.1`
- ADR-0007 / ADR-0008 / ADR-0009
- accepted E5 lifecycle projection producer PR #58

No new shared field, lifecycle event, enum, profile revision, E4 authority, or E6 authority was required. No contract/ADR change was made.

## Materialized E5 boundary

```text
one exact canonical position-lifecycle-projection-v0.1 Position
+ exact E4 OrderRequest evidence considered by E5
+ complete OrderResult observation sets considered by E5
+ complete Fill sets considered by E5
-> one immutable PositionLifecycleExecutionEvidenceBinding
```

The companion declares exactly:

```text
schema_version = contracts-v0.1
lifecycle_execution_binding_profile_version = position-lifecycle-execution-binding-v0.1
execution_scope = POSITION_LINKED_REDUCTION_ORDERS_V0_1
```

and binds exactly:

```text
position_id
lifecycle_projection_id
lifecycle_revision
execution_interpreted_at == lifecycle_interpreted_at
```

The existing lifecycle projection payload is not modified, and no accepted `lifecycle_projection_id` identity material is rewritten.

## Evidence scope

The producer includes only Position-linked reduction requests satisfying all of:

```text
OrderRequest.position_id == projection.position_id
OrderRequest.authorization_type == POSITION_ACTION
OrderRequest.order_role in {
  PROTECTION_STOP,
  POSITION_EXIT,
  EMERGENCY_EXIT
}
```

Clean pre-position entry requests with no PositionAction/position/order-role linkage remain outside V0.1 and are not joined by `trade_plan_id` heuristics.

Malformed PositionAction/reduction evidence, wrong Position lineage, unsupported role/authorization, unknown result request reference, or inconsistent Fill lineage fails closed rather than being silently dropped.

## Canonical snapshot and identity

The producer implements the PR #63 algorithms:

- complete canonical OrderRequest payload hash: `sha256:<hex>`;
- OrderResult logical pair set `(observed_at, payload_hash)`, sorted by semantic UTC `observed_at`, then hash;
- identical duplicate OrderResult observation replay is idempotent;
- equal `order_request_id + observed_at` with changed payload fails closed;
- Fill logical tuple set `(fill_id, filled_at, payload_hash)`, sorted by `filled_at`, then `fill_id`;
- identical duplicate Fill replay is idempotent;
- same `fill_id` with changed payload fails closed;
- exact counts and latest semantic timestamps are emitted;
- `order_evidence` is sorted lexicographically by `order_request_id`;
- `execution_snapshot_hash` is SHA-256 over exact `{execution_scope, position_id, order_evidence}` canonical material;
- `lifecycle_execution_binding_id` is `posexecbind_<sha256>` over the complete immutable binding excluding only the ID field.

Dataclass/Enum/Decimal/UTC-datetime E4 objects are deterministically serialized to contract boundary values. Binary floats, non-finite decimals, non-UTC/noncanonical timestamps, unsupported fields, non-string JSON keys, and unsupported value types fail closed rather than being normalized into another financial fact.

## Lifecycle authority preserved

The binding does not infer or replace E5 lifecycle semantics.

Existing projection functions remain unchanged. Bounded composition helpers call the already accepted E5 producer first and then bind the exact execution evidence for the resulting projection:

```text
GENESIS + binding
TRANSITION + binding
REATTESTATION + binding
```

A changed execution snapshot with unchanged lifecycle can therefore use an equal-broker-anchor `REATTESTATION` revision plus a new binding. A lifecycle-changing interpretation uses the existing canonical `TRANSITION` path plus a new binding.

No older projection or binding is mutated to claim later evidence.

## Test definitions materialized

`tests/position/test_lifecycle_execution_binding.py` defines deterministic coverage for:

- empty in-scope snapshot binding;
- OPEN_PROTECTED + PROTECTION_STOP OPEN evidence;
- later PARTIALLY_FILLED/FILLED result + Fill producing a changed snapshot/binding after E5 transition;
- CANCELED/EXPIRED/REJECTED protection evidence changing the snapshot;
- POSITION_EXIT and EMERGENCY_EXIT scope inclusion;
- equal-anchor REATTESTATION with newer execution evidence and unchanged lifecycle;
- collection-order-independent `order_evidence` ordering;
- deterministic OrderResult-set hashing and exact duplicate idempotency;
- deterministic Fill-set hashing and exact duplicate idempotency;
- conflicting equal-time OrderResult rejection;
- conflicting Fill identity rejection;
- request/result/fill lineage rejection;
- entry-v0.1 exclusion without `trade_plan_id` inference;
- binding schema/profile/scope/projection/revision/time mismatch rejection;
- duplicate OrderRequest identity conflict;
- binary-float rejection;
- unchanged accepted lifecycle projection identity and no E6/storage/provider/network dependency.

Existing E5 lifecycle projection, state-machine, protection, close, and TradeResult source files are unchanged by this task.

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: no separate Product-Owner/PM-approved Local Runner action pinned to this exact target revision is available in this session. No project code/tests were executed.

Exact future Windows PowerShell command from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## GitHub compute / security

- GitHub Actions / CI / hosted runner used: `NO`
- GitHub-triggered self-hosted compute used: `NO`
- arbitrary cloud project execution used: `NO`
- provider/private API/network used: `NO`
- credentials used/stored: `NO`
- E4 production changed: `NO`
- E6 storage/platform changed: `NO`
- contracts/ADR changed: `NO`
- E7 release files changed: `NO`
- PAPER/SHADOW/LIVE authority changed: `NO`

## Release impact / remaining separate work

```text
Durable execution truth -> E5 lifecycle freshness contract = RESOLVED STATIC by PR #63
E5 companion-binding producer = MATERIALIZED / executable NOT_RUN
E6 mechanical binding persistence/recovery consumer = SEPARATE / NOT DONE BY E5
E6 TradeResult referenced-object graph completeness = SEPARATE / STILL BLOCKED
Restart/persistence executable criterion = BLOCKED / NOT_RUN
Paper E2E durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops on `DONE` for `E5-20260824-023`. No E6 consumer work, E7 integration, approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, or LIVE is started by this task.
