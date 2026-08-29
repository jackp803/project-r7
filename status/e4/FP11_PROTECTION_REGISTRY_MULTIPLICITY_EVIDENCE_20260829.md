# E4 FP-11 Protection Registry / Multiplicity Evidence Implementation — 2026-08-29

- task_id: `E4-20260829-032`
- agent: `E4`
- target_branch: `agent/e4-fp11-protection-registry-evidence-20260829`
- baseline_main_sha: `74bafe9bd52f95a2fe1b5d26ba0f3b0c7fffe7a0`
- implementation_classification: `STATIC IMPLEMENTATION / TEST-DEFINITION CANDIDATE`
- executable_verification: `NOT_RUN / NOT_PASS`

## 1. Scope / authority

This task implements only the provider-neutral deterministic FP-11 evidence boundary accepted by:

- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`
- `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`
- merged E4 FP-04 producer/currentness surfaces in `src/execution/external_close_evidence.py`
- `status/PM_E4_031_REVIEW_20260829.md`

No shared contract, E5 policy, E6 persistence/current-head policy, E7 release rule, provider transport/authentication/configuration, provider allowlist, runtime authorization, risk limit, leverage, capital threshold, or Product Owner authorization artifact changed.

## 2. Files changed

```text
src/execution/protection_registry_evidence.py
src/execution/protection_registry_evidence_boundary.py
tests/execution/test_protection_registry_evidence.py
tests/execution/test_protection_registry_evidence_boundary.py
status/e4/FP11_PROTECTION_REGISTRY_MULTIPLICITY_EVIDENCE_20260829.md
coordination/E4/STATUS.md   (terminal update follows this handoff commit)
```

## 3. Producer boundary

`src/execution/protection_registry_evidence.py` adds provider-neutral deterministic types/functions:

```text
FP04ActiveProtectionDependency
ProtectionRegistryMultiplicityInput
canonical_protection_registry_json(...)
canonical_protection_registry_hash(...)
active_protection_set_hash(...)
build_protection_registry_multiplicity_evidence(...)
validate_protection_registry_multiplicity_evidence(...)
protection_registry_multiplicity_evidence_is_current(...)
```

The producer consumes only already-supplied in-memory facts:

```text
exact canonical Position ref + payload
exact IntendedProtectionLineageReference
exact ObservedActiveProtectionSet
one exact FP-04 ACTIVE_PROTECTION dependency per observed object
lifecycle projection / execution-binding refs when applicable
runtime process/start/config refs when applicable
optional prior immutable FP-11 evidence
```

It performs no network I/O and contains no provider request, query, create, cancel, amend, replace, cleanup, authentication, credential, account mutation, order action, or runtime startup surface.

## 4. Intended protection lineage

The implementation validates the exact accepted `IntendedProtectionLineageReference` field set and binds it mechanically to the supplied current Position:

```text
position_ref
position_hash
position_id
position_observed_at
position_side
position_quantity_ref
position_action_ref / hash / id
approved_trade_plan_ref / hash
risk_decision_ref
optional protection OrderRequest ref/hash
optional client-order identity
optional lifecycle projection / execution binding
optional trigger validity
optional all-or-none runtime process/start/config generation
ownership_reconciliation_generation_ref
```

A Position hash/ref/ID/observation/side mismatch cannot be upgraded into registry convergence. Lifecycle/runtime generation references must match the intended lineage when supplied. E4 does not infer a replacement PositionAction or lifecycle response.

## 5. Observed provider protection-set normalization

Only FP-04 object class `ACTIVE_PROTECTION` is admitted.

Each normalized entry carries exactly the shared profile fields:

```text
provider_object_ref
provider_snapshot_ref
provider_snapshot_hash
provider_object_observed_at
ownership_evidence_ref
ownership_evidence_hash
ownership_classification
ownership_reconciliation_status
intended_lineage_binding_status
intended_lineage_binding_ref
intended_lineage_binding_hash
```

Entries are sorted lexicographically by:

```text
(provider_object_ref, provider_snapshot_hash, ownership_evidence_ref)
```

No object is discarded because another object looks newer, closer in trigger price, or more familiar by identity.

The complete observed-set hash is computed over exactly:

```text
provider_identity_ref
provider_instrument_ref
provider_observation_generation_id
provider_observed_at
observation_coverage_status
provider_set_currentness_status
all normalized sorted objects
```

using canonical UTF-8 JSON with sorted keys / compact separators and `sha256:` prefix.

`provider_received_at` remains an evidence field/temporal boundary but is not inserted into the section-12 set-hash material because the accepted profile does not include it there.

## 6. Exact FP-04 dependency binding

Every observed active protection object must have exactly one matching full FP-04 dependency; extras and omissions fail closed.

For each entry the producer verifies:

```text
FP-04 profile = external-provider-object-ownership-reconciliation-v0.1
provider_object_class = ACTIVE_PROTECTION
ownership evidence hash exact
ownership classification exact
reconciliation status exact
provider identity ref/hash exact
canonical symbol exact
provider instrument exact
provider observation generation exact
provider object ref exact
provider snapshot ref/hash exact
provider object observed_at exact
currentness observation exact
```

The merged E4 FP-04 currentness helper is then applied to the full ownership evidence / observation / context. A stale/superseded FP-04 object cannot satisfy exact-one convergence.

## 7. Deterministic fail-closed precedence

The implementation evaluates fail-closed evidence before ordinary counting:

1. Position/intended-lineage mismatch;
2. lifecycle/runtime generation stale or mismatched;
3. provider observation `INCOMPLETE` / `UNKNOWN`;
4. provider set `STALE` / `UNKNOWN`;
5. stale FP-04 evidence;
6. FP-04 ownership conflict;
7. exact active-object count and object classification/binding;
8. terminal/flat Position interaction;
9. local protected lifecycle contradiction routing.

No numeric freshness/TTL threshold is invented.

## 8. Missing protection

A complete/current set with zero entries emits only the missing-protection evidence path:

```text
multiplicity_state = NO_ACTIVE_PROTECTION_OBSERVED
registry_status = MISSING_PROTECTION_REINTERPRETATION_REQUIRED
```

with E5 policy reinterpretation and exposure/create-replace blocking dispositions. It does not emit provider create authority and it does not claim the Position is healthy/protected.

When local lifecycle says `OPEN_PROTECTED` or `PROFIT_PROTECTED`, non-converged registry evidence additionally routes lifecycle protection-state reinterpretation.

## 9. Sole converged exact-one tuple

The only converged tuple is:

```text
multiplicity_state = EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
registry_status = CONVERGED_EXACTLY_ONE_INTENDED
required_dispositions = [NO_ACTION_REGISTRY_CONVERGED]
reason_codes = [EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED]
```

It requires simultaneously:

- Position/intended lineage current and exact;
- complete/current provider set;
- exactly one object;
- exact current FP-04 evidence for the same provider object/snapshot/generation;
- `ownership_classification = KNOWN_OWNED_CURRENT_GENERATION`;
- `ownership_reconciliation_status = CURRENT_KNOWN_OWNED`;
- FP-04 no-action success disposition only;
- `intended_lineage_binding_status = EXACT_MATCH` with exact binding ref/hash;
- no lifecycle/runtime currentness mismatch;
- valid canonical set hash and `protregmul_<sha256>` evidence identity.

The tuple is registry evidence only. It creates no E5 lifecycle transition and no provider mutation authority.

## 10. Multiple / orphan / external / prior / conflict behavior

Two or more active objects always remain represented and route multiplicity convergence. No automatic winner is selected.

One intended object plus an external, prior-generation, orphan/not-matching, unknown, or conflicting extra object remains non-converged.

External/prior/not-matching objects retain explicit reasons/dispositions and uncertain cleanup remains blocked. E4 does not adopt by symbol/side/price/client-ID similarity and does not emit blind cancel-all or create-another authority.

FP-04 ownership conflict routes:

```text
OWNERSHIP_CONFLICT_PRESENT
OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED
OWNERSHIP_MANUAL_REVIEW_REQUIRED
BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL
```

## 11. Strict ambiguity boundary

`src/execution/protection_registry_evidence_boundary.py` is the strict E4 integration entry point for FP-11 production/currentness.

It preserves the base producer's canonical evidence shape and only strengthens the task-required ambiguous path:

```text
FP-04 ownership/reconciliation UNKNOWN
or intended-lineage binding UNKNOWN
-> keep the base stale/unknown fail-closed classification
-> add OWNERSHIP_MANUAL_REVIEW_REQUIRED disposition
-> add PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED reason
-> recompute deterministic protregmul_<sha256> identity
-> revalidate the complete shared evidence object
```

It does not select a cleanup target or E5 policy. It also performs a second material-change check after this strict normalization so an already-strict ambiguous evidence object cannot be superseded merely by changing `evaluated_at`.

Recommended consumer surface:

```text
src.execution.protection_registry_evidence_boundary.build_protection_registry_multiplicity_evidence
src.execution.protection_registry_evidence_boundary.protection_registry_multiplicity_evidence_is_current
```

## 12. Terminal / flat interaction

If supplied current Position truth is flat (`actual_quantity == 0`) or lifecycle is `CLOSED` while active provider protection remains, every observed object is preserved.

The evidence adds:

```text
FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED
```

and remains non-converged for protection cleanup. A previously exact-one current-owned intended protection does not remain falsely green after terminal/flat Position truth.

FP-11 does not cancel/erase the protection and does not emit cleanup mutation authority.

## 13. Identity, currentness and supersession

`protection_registry_evidence_id` is deterministic over the complete canonical evidence payload except the ID field itself:

```text
protregmul_<sha256>
```

Material currentness compares all accepted evidence-bearing fields while intentionally ignoring only:

```text
protection_registry_evidence_id
supersedes_registry_evidence_id
evaluated_at
```

Therefore a later clock value alone does not refresh an otherwise unchanged evidence object.

Material changes that invalidate old evidence include changed:

- Position ref/hash/observation;
- intended protection lineage;
- provider object/set/snapshot/generation;
- FP-04 ownership evidence/currentness;
- lifecycle projection/execution binding;
- runtime process/start/config generation.

Explicit supersession requires the same logical Position/intended-protection lineage anchor and a material evidence change. Historical evidence is immutable.

## 14. Tests defined

Added provider-free deterministic definitions:

```text
tests/execution/test_protection_registry_evidence.py
tests/execution/test_protection_registry_evidence_boundary.py
```

Coverage includes:

- complete/current empty set -> missing-protection reinterpretation, never converged;
- exact one current-owned exact-lineage object -> sole success tuple;
- current-owned but `NOT_MATCH` -> orphan/non-converged;
- FP-04 stale/unknown/conflicting -> non-converged;
- two exact intended objects -> multiple, no winner;
- intended + external/prior object -> multiple/non-converged;
- incomplete set cannot become zero/exact-one;
- stale/unknown provider set -> fail-closed refresh state;
- terminal/flat Position + active protection -> FP-10 terminal convergence disposition;
- set hash/evidence ID stable across equivalent input ordering;
- provider snapshot change invalidates prior currentness and creates new immutable superseding identity;
- Position/lifecycle/runtime/FP-04 material changes invalidate old evidence;
- timestamp-only reevaluation does not refresh material currentness and cannot justify supersession;
- strict UNKNOWN ownership/lineage ambiguity routes explicit manual review;
- evidence contains no credential/network/provider-mutation authority fields.

No project code or test command was executed in this task session.

## 15. Future approved-local verification

Required after an authoritative approved-local exact-clean candidate is available:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.execution.test_protection_registry_evidence -v
python -m unittest tests.execution.test_protection_registry_evidence_boundary -v
python -m unittest tests.execution.test_external_close_evidence -v
python -m unittest tests.execution.test_protection -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest tests.brokers.test_paper_broker_protection_stop_flat_truth -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Current result:

```text
project executable verification = NOT_RUN / NOT_PASS
```

LF-0 approved-local exact-revision preparation remains blocked by the active infrastructure blocker. Historical test evidence is revision-bound and is not rebound to this branch.

## 16. Known limitations / downstream dependencies

- This implementation does not query any provider active-protection set. A later authorized observer must supply complete/current normalized provider facts.
- Provider-native protection endpoint, trigger basis, `posSide`, reduce-only behavior, native quantity, readback and cancel semantics remain unresolved under FP-02 and are not inferred here.
- E5 must consume FP-11 evidence and decide policy/lifecycle response; E4 does not choose PROTECT/REPLACE/EMERGENCY_EXIT/HOLD.
- E6 may persist and mechanically validate immutable FP-11 evidence/currentness, but E4 does not select durable current heads.
- A cleanup/cancel action requires separate exact provider-object authority/capability and is outside this task.
- Static implementation/test definitions are not executable PASS until approved-local exact-revision verification runs successfully.

## 17. Security / provider / runtime state

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
protection query/create/cancel/amend/replace = 0
order actions = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 = BLOCKED / UNCHANGED
LF-2 = NOT PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

No real secret was read, requested, logged or committed.

## 18. Terminal classification

Source implementation and deterministic test definitions are complete within E4 scope, but required executable verification did not run because the approved-local exact-revision path remains unavailable.

```text
state = PARTIAL
reason = implementation/test definitions complete; executable verification NOT_RUN / NOT_PASS
```

E4 stops after terminal STATUS and does not self-start provider verification, protection mutation/cleanup, E5 policy work, E6 persistence, E7 requalification, exact-revision preparation, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, order action, or capital movement/exposure.
