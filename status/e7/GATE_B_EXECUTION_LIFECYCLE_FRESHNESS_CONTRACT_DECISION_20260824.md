# Gate B Execution-Truth / Lifecycle Freshness Contract Decision — E7-20260824-053

## Authority / scope

- task_id: `E7-20260824-053`
- target branch: `agent/e7-gate-b-execution-lifecycle-freshness-contract-20260824`
- authoritative wake/task match: `YES`
- parent contract: `contracts-v0.1 / BASELINE`
- existing lifecycle profile: `position-lifecycle-projection-v0.1 / unchanged`
- new companion profile: `position-lifecycle-execution-binding-v0.1`
- project executable verification: `NOT_RUN`

This task resolves only the shared E4 execution-evidence -> E5 lifecycle interpretation freshness boundary proven by E7-052 / PR #62. No project code/tests were executed and no E1-E6 production/tests were modified.

## Decision

```text
classification = ADDITIVE_COMPANION_PROFILE
shared semantic blocker from E7-052 = RESOLVED STATIC
schema_version = contracts-v0.1 / unchanged
position-lifecycle-projection-v0.1 = unchanged
lifecycle_projection_id identity material = unchanged
new companion object = PositionLifecycleExecutionEvidenceBinding
new profile = position-lifecycle-execution-binding-v0.1
```

Normative contract:

`contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`

Architecture decision:

`docs/adr/ADR-0009-position-lifecycle-execution-evidence-freshness.md`

Safety definition plan:

`tests/safety/GATE_B_LIFECYCLE_EXECUTION_BINDING_TEST_PLAN.md`

## Why companion rather than extending the existing projection

`position-lifecycle-projection-v0.1` computes `lifecycle_projection_id` from the complete immutable profiled Position payload. Adding a new required execution-binding field directly to the accepted projection would alter existing identity material.

The companion approach keeps every accepted projection ID valid and adds exactly the missing durability authority. Legacy projections remain historical/in-memory evidence, while a Gate B restart consumer requiring execution freshness fails closed if the companion is absent.

## Exact evidence scope

The companion binds every Position-linked canonical E4 request satisfying:

```text
position_id = exact Position
authorization_type = POSITION_ACTION
order_role in {
  PROTECTION_STOP,
  POSITION_EXIT,
  EMERGENCY_EXIT
}
```

For every request, the binding covers:

- exact OrderRequest canonical payload hash;
- all canonical OrderResult observations for the request;
- all canonical Fill objects for the exact request/Position lineage;
- deterministic observation/fill counts, set hashes and semantic latest timestamps.

The complete per-request set is normalized into one deterministic `execution_snapshot_hash`.

## Freshness rule

```text
latest durable in-scope E4 execution snapshot
== latest E5 companion binding snapshot
-> execution-evidence axis is current

latest durable in-scope E4 execution snapshot
!= latest E5 companion binding snapshot
-> fresh E5 interpretation required
-> old lifecycle projection cannot be restart READY
```

E6 does not infer which PositionEvent or lifecycle state the changed evidence implies.

A later-arriving historical OrderResult observation is also new unbound evidence and changes the full observation-set digest. E6 is not allowed to decide that such evidence is semantically irrelevant.

## Position broker observation relationship

Existing Position freshness remains independent:

```text
lifecycle_source_broker_state_observed_at
== exact E4 Position observation interpreted by E5
```

Gate B restart authority requires both:

```text
Position broker-observation freshness = current
Position-linked execution-evidence binding = current
```

A newer raw Position observation requires E5 re-attestation even if execution binding matches. New execution evidence requires E5 interpretation even if broker Position timestamp is unchanged.

## E5 producer semantics

E5 alone emits the companion binding.

When new execution evidence changes lifecycle:

```text
next TRANSITION lifecycle projection
+ new companion binding
```

When E5 consumes new execution evidence but lifecycle remains unchanged:

```text
next REATTESTATION lifecycle projection
+ new companion binding
```

The existing profile already permits REATTESTATION at an equal broker Position anchor, so no projection-profile version change is required.

An older companion is immutable and cannot be updated to claim later evidence was interpreted.

## E6 consumer semantics

E6 may only:

- persist binding payloads;
- validate profile/identity/revision/reference/hash/count/time rules;
- recompute the fixed shared execution snapshot from durable canonical E4 objects;
- compare exact equality;
- fail closed when equality or completeness is absent.

E6 must not map OrderStatus/Fill facts to E5 lifecycle transitions.

## Required scenario disposition

```text
A protected order remains active
= deterministic through exact snapshot equality

B later protection PARTIALLY_FILLED/FILLED
= snapshot changes; old OPEN_PROTECTED cannot remain READY

C later protection CANCELED/EXPIRED/REJECTED
= snapshot changes; old OPEN_PROTECTED cannot remain READY

D UNKNOWN/RECONCILIATION_REQUIRED/DEGRADED
= existing fail-closed behavior remains independent; binding cannot make it healthy

E POSITION_EXIT / EMERGENCY_EXIT / PROTECTION_STOP
= all included in V0.1 scope because all can receive later execution truth requiring E5 interpretation
```

E6 never infers CLOSED, EMERGENCY, RECONCILIATION_REQUIRED, EXIT_FAILED, or PROTECTION_LOST from snapshot mismatch.

## Entry-path boundary

Current pre-position `entry-v0.1` OrderRequest/Fill evidence is not uniformly `position_id`-linked and is excluded from V0.1 rather than heuristically joined by `trade_plan_id`.

A future restart-authoritative `PENDING_ENTRY` design requires an explicit E7 refinement. Until then that pre-position restart case is not eligible for READY under this companion profile.

## Identity / conflicts

```text
binding identity = posexecbind_<sha256 of complete binding except ID>
same projection + same snapshot = idempotent replay
same binding ID + changed payload = conflict
same lifecycle_projection_id + different binding snapshot = conflict
missing binding = not restart-authoritative
new/different request/result/fill = snapshot mismatch -> fresh E5 interpretation
```

No storage arrival order or last-write-wins rule is permitted.

## Downstream bounded dependency map

```text
E7 contract/ADR = DONE STATIC
-> E5 producer adaptation = REQUIRED
-> E6 mechanical binding persistence/recovery adaptation = REQUIRED
-> E6 separate TradeResult referenced-object completeness repair from E7-052 = STILL REQUIRED
-> E7 durable Paper integration/E2E/safety re-review = REQUIRED
-> PM-authorized approved-local Gate B verification = LATER / NOT STARTED
```

No E4 production contract change is required.

## Release state

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
execution-truth/lifecycle freshness shared semantic gap = RESOLVED STATIC
E5 companion binding producer = NOT YET MATERIALIZED
E6 companion binding consumer/recovery = NOT YET MATERIALIZED
E6 TradeResult graph completeness defect = BLOCKED / unchanged
Restart/persistence executable criterion = BLOCKED
Paper E2E durable audit executable criterion = BLOCKED
Gate B = BLOCKED / NOT YET PASS
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = NO
PAPER / SHADOW / LIVE = UNAUTHORIZED
project_executable_verification = NOT_RUN
```

No executable NOT_RUN criterion becomes PASS.

## Future approved-local commands

After E5/E6 remediation is accepted and PM authorizes an exact revision:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

If `tests/e2e` is absent at the accepted remediation revision, it must be materialized before Gate B verification; absence is not PASS.

## Verification / safety

```text
project executable verification = NOT_RUN
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
strategy lifecycle promotion = NONE
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production/test changes by E7 = NONE
```
