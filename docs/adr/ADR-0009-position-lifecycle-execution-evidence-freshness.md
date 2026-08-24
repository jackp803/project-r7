# ADR-0009 — Position Lifecycle Execution-Evidence Freshness Boundary

- Status: `ACCEPTED`
- Date: `2026-08-24`
- Decision task: `E7-20260824-053`
- Authority: E7 Integration / Architecture / System QA / Release Engineer
- Parent contract: `contracts-v0.1`
- Lifecycle projection profile: `position-lifecycle-projection-v0.1`
- Companion profile: `position-lifecycle-execution-binding-v0.1`
- Canonical profile: `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`

## Context

E7-20260824-052 / PR #62 proved a durable authority gap after PR #61 materialized E6 Paper runtime persistence.

The existing lifecycle projection profile correctly binds E5 lifecycle interpretation to the exact E4 broker Position observation. E6 can therefore detect when newer raw Position truth exists beyond the latest E5 projection.

The profile does not bind E5 interpretation to Position-linked E4 execution observations. Consequently a later healthy protection OrderResult/Fill can coexist with an older E5 `OPEN_PROTECTED` projection while E6 has no shared authority to decide whether that evidence was interpreted.

Current E5 semantics prove that this matters:

```text
OPEN_PROTECTED + later PARTIALLY_FILLED/FILLED protection truth
-> fresh E5 interpretation required pending authoritative Position/close truth

OPEN_PROTECTED + later CANCELED/EXPIRED/REJECTED protection truth
-> fresh E5 interpretation required and may produce PROTECTION_LOST / EMERGENCY
```

The equivalent issue also exists for explicit `POSITION_EXIT` and `EMERGENCY_EXIT` execution observations: later fills, partial fills, terminal failures, or ambiguous truth may affect E5 lifecycle interpretation, but E6 must not infer the transition.

## Decision

Introduce an additive immutable 1:1 companion object:

```text
PositionLifecycleExecutionEvidenceBinding
profile = position-lifecycle-execution-binding-v0.1
```

under unchanged:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

Do not add required fields to the existing lifecycle projection payload because `lifecycle_projection_id` hashes the complete projection payload. Retrofitting a new required field would rewrite accepted projection identity material.

Instead, Gate B restart-authoritative recovery requires one immutable companion binding for the latest E5 lifecycle projection.

## 1. Evidence scope is mechanical, not semantic

The V0.1 scope is every canonical Position-linked E4 OrderRequest with:

```text
position_id = exact Position
authorization_type = POSITION_ACTION
order_role in {PROTECTION_STOP, POSITION_EXIT, EMERGENCY_EXIT}
```

For each request, the bound snapshot covers:

- exact OrderRequest payload hash;
- all canonical OrderResult observations;
- all canonical Fill objects for the request/Position lineage.

This is deliberately broader than the initial protection blocker so equivalent close/emergency gaps are not left unresolved.

Pre-position `entry-v0.1` execution is outside this companion because current entry objects are not uniformly `position_id`-linked. A future restart-authoritative `PENDING_ENTRY` design requires a separate E7 refinement; E6 cannot infer that association from `trade_plan_id` alone.

## 2. Freshness proof uses full deterministic evidence sets

The binding serializes one deterministic `order_evidence` entry per in-scope request and one `execution_snapshot_hash` over the full sorted set.

OrderResult observations are canonically ordered by semantic `observed_at`, not storage arrival. Fill evidence is ordered by `filled_at` and stable `fill_id`. New observations/fills alter the snapshot regardless of database insertion order.

This yields a conservative rule:

```text
current durable execution snapshot == latest E5 bound snapshot
-> execution-evidence freshness axis is current

current durable execution snapshot != latest E5 bound snapshot
-> fresh E5 interpretation required
-> old lifecycle projection cannot be reported READY
```

E6 never maps the changed execution fact to a PositionEvent or lifecycle state.

## 3. E5 remains interpretation authority

E5 alone emits the companion binding because only E5 can authoritatively state what E4 execution evidence it considered when materializing lifecycle state.

When execution evidence advances:

- if lifecycle changes, E5 emits the next `TRANSITION` projection plus its new binding;
- if lifecycle remains unchanged, E5 emits the next `REATTESTATION` projection plus its new binding.

The existing lifecycle profile already allows equal-broker-anchor REATTESTATION. That mechanism now also carries a fresh companion execution binding when E5 reinterprets newer execution evidence without changing lifecycle state.

An older projection's binding is immutable and may not be replaced to claim later evidence was interpreted.

## 4. E6 remains mechanical persistence authority

E6 may:

- persist the binding;
- validate binding/projection identity and revision equality;
- validate canonical hashes/counts/timestamps/references;
- mechanically derive the current durable execution snapshot from the fixed shared scope;
- compare exact snapshot equality;
- return a local fail-closed diagnostic when equality is absent.

E6 must not:

- import/copy E5 transition tables;
- map OrderStatus/Fill behavior to lifecycle states;
- infer protection loss, exit failure, emergency, closure, or reconciliation lifecycle events;
- choose conflicting evidence by last-write-wins;
- update an old lifecycle projection/binding when new execution evidence arrives.

## 5. Position broker freshness remains a separate axis

Existing `position-lifecycle-projection-v0.1` semantics remain authoritative:

```text
newer raw E4 Position observation than latest E5 projection
-> E5 re-attestation/interpretation required
```

The new companion adds a second independent check:

```text
changed Position-linked E4 execution snapshot since latest E5 projection
-> E5 re-interpretation required
```

Gate B restart readiness requires both axes to be current and conflict-free.

## 6. Identity and conflict behavior

The companion binding has content-derived identity `posexecbind_<sha256>` over its complete payload except the ID field.

Rules:

```text
same projection + same exact snapshot -> idempotent replay
same binding ID + changed payload -> corrupt/conflict
same lifecycle_projection_id + different binding snapshot -> authority conflict
missing binding -> not restart-authoritative
changed/new request/result/fill after binding -> snapshot mismatch -> fresh E5 interpretation required
```

Identical E4 evidence replay is safe. Changed evidence under the same canonical identity fails closed.

## 7. Why a single latest-OrderResult watermark was rejected

A latest-status-only watermark would miss later-arriving historical OrderResult observations or Fill evidence that had not been proven interpreted by E5.

The full normalized observation/fill set is intentionally conservative and append-safe. It may require re-attestation for evidence that E5 ultimately determines does not change lifecycle; that conservative cost is preferable to letting E6 decide semantic irrelevance.

## 8. Why direct lifecycle projection extension was rejected

Adding new required fields directly to `position-lifecycle-projection-v0.1` would alter accepted `lifecycle_projection_id` material and create avoidable migration ambiguity.

A companion profile:

- preserves all existing lifecycle identities;
- adds exactly the missing freshness authority;
- lets legacy projections remain valid history;
- lets Gate B restart consumers fail closed unless the companion exists;
- avoids changing E4/E5/E6 domain authority.

## 9. Downstream dependency map

After this ADR/profile is accepted:

```text
E5
-> bounded producer adaptation to emit the companion binding with each
   Gate B restart-authoritative lifecycle projection

E6
-> bounded persistence/recovery adaptation to store/recompute/compare the binding
-> separate settled-contract TradeResult referenced-object completeness repair

E7
-> durable Paper integration/E2E/safety re-review and definition completion

PM
-> explicitly authorize exact approved-local Gate B verification
```

No E4 production contract adaptation is required because the canonical E4 OrderRequest / OrderResult / Fill objects already contain the required evidence material.

## 10. Release impact

This ADR resolves the shared semantic blocker only.

```text
Durable E4 execution truth -> E5 lifecycle freshness contract = RESOLVED STATIC
E5 binding producer adaptation = REQUIRED / NOT YET MATERIALIZED
E6 mechanical binding consumer/recovery adaptation = REQUIRED / NOT YET MATERIALIZED
E6 TradeResult graph-completeness defect = SEPARATE / STILL BLOCKED
Restart/persistence executable criterion = BLOCKED
Paper E2E durable audit executable criterion = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
project_executable_verification = NOT_RUN
```

No Local Runner, project-code execution, GitHub Actions/CI, hosted runner, provider/private API, credential, PAPER, SHADOW, or LIVE execution is used by this static decision.
