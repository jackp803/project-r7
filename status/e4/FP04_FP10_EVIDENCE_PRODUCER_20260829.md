# E4 FP-04 / FP-10 Evidence Producer Handoff — 2026-08-29

## Handoff

**From:** E4 / Trading Execution / Broker Integration Engineer  
**To:** E5 / E6 / E7 / Project Manager  
**Task:** `E4-20260829-030`  
**Branch:** `agent/e4-fp04-fp10-evidence-producer-20260829`  
**Baseline main:** `efcd3631ad069cd50afd22abbb9dd8028e23d9ac`  
**Date:** `2026-08-29`

## 1. Objective

Implement only the provider-neutral E4 producer/assembler boundary required by the accepted shared profiles:

```text
external-provider-object-ownership-reconciliation-v0.1   (FP-04)
external-manual-close-lifecycle-convergence-v0.1         (FP-10)
```

The implementation consumes already-supplied in-memory provider/broker observations and owner-authoritative local references. It has no network transport, credential reader, provider mutation, order submit/cancel/amend/close behavior, SHADOW/PAPER runtime, or capital behavior.

## 2. What changed

### FP-04 producer

`src/execution/external_close_evidence.py` adds an immutable canonical FP-04 producer.

Inputs are explicit E4/provider observations plus explicit owner-authoritative local lineage/registry/current-generation facts. The producer:

- canonicalizes all hash/identity material;
- sorts shared evidence sequences according to the accepted profile;
- derives deterministic provider identity and snapshot hashes;
- emits deterministic `extownrec_<sha256>` identity;
- emits only accepted shared object-class / ownership / reconciliation / disposition / reason vocabularies;
- validates the completed object through the accepted E5 public FP-04 validator before returning it;
- supports explicit immutable supersession for the same provider-object lineage;
- exposes a material-currentness check that does not treat a later `evaluated_at` alone as refreshed authority.

The producer can emit a current-known-owned success only when the supplied current-generation evaluation has:

```text
exact provider-object binding
single-object multiplicity
at least one explicit owner-authoritative ownership claim
no contradictory/unknown lineage
all supplied registry evidence CURRENT
```

The success tuple is exactly:

```text
ownership_classification = KNOWN_OWNED_CURRENT_GENERATION
reconciliation_status = CURRENT_KNOWN_OWNED
required_dispositions = [NO_ACTION_CURRENT_KNOWN_OWNED]
reason_codes = [CURRENT_GENERATION_OWNERSHIP_PROVEN]
```

External/manual input remains `EXTERNAL_UNTRACKED`; prior-generation input remains `KNOWN_OWNED_PRIOR_GENERATION`; stale/unknown or contradictory inputs remain fail closed. No adoption decision is manufactured.

### FP-10 canonical assembler

`src/execution/external_close_evidence.py` also adds a provider-neutral FP-10 canonical payload assembler.

The assembler accepts only already-supplied facts:

- exact current provider Position observation;
- exact normalized canonical Position;
- execution/order/fill/reconciliation evidence units;
- complete referenced FP-04 evidence objects plus currentness classifications;
- optional FP-05 ref/hash/state;
- optional prior FP-11 registry ref/hash;
- terminal protection observation;
- exact lifecycle projection and lifecycle execution binding;
- project/runtime generation facts when applicable;
- an already-selected accepted FP-10 convergence-state/reason/disposition interpretation.

E4 does **not** choose an E5 lifecycle transition. It only rejects structurally unsafe/contradictory combinations and serializes the accepted shared evidence shape.

The assembler:

- validates exact provider/normalized Position ID, symbol, side, quantity and observation-anchor equality;
- rejects positive exposure presented as flat or close-eligible;
- rejects unrepresentable positive residual unless it is explicitly represented as `RESIDUAL_UNREPRESENTABLE_NOT_FLAT` with `BLOCK_CLOSE_RETRY_MUTATION`;
- rejects close eligibility unless provider Position is current and exact zero, normalized Position is `CONSISTENT`, execution evidence is current/compatible, terminal protection is clear, FP-04 evidence is current/nonconflicting, and the exact success tuple is used;
- keeps FP-05 residual state distinct from authoritative current Position flatness;
- keeps FP-11 terminal-protection convergence distinct from Position flatness;
- validates lifecycle projection/binding identities rather than manufacturing lifecycle evidence;
- canonicalizes execution/FP-04 sets and hashes;
- emits deterministic `extcloseconv_<sha256>` identity;
- supports explicit immutable supersession for the same Position lineage;
- validates the completed object through the accepted E5 public FP-10 validator before returning it.

### Exact FP-04 Position binding hardening

Static review found that a generic `CURRENT` FP-04 row is insufficient for FP-10: the materially relevant `POSITION_EXPOSURE` ownership evidence must bind the exact provider Position snapshot used by the convergence evidence.

`src/execution/external_close_binding.py` is therefore the strict E4 FP-10 entry point. Before calling the canonical assembler it requires exactly one FP-04 `POSITION_EXPOSURE` evidence object whose following facts equal the FP-10 provider Position input:

```text
provider_identity_ref
provider_identity_hash
canonical_symbol
provider_instrument_ref
provider_snapshot_ref
provider_snapshot_hash
provider_observation_generation_id
provider_observed_at
provider_received_at
```

This binding check does not upgrade ownership classification or authorize mutation. It only prevents cross-snapshot/cross-generation evidence composition.

For future integration, E4 recommends using:

```text
src.execution.external_close_binding.build_external_manual_close_convergence_evidence
src.execution.external_close_binding.external_manual_close_convergence_evidence_is_current
```

as the FP-10 E4 producer/currentness boundary.

## 3. Files changed

Implementation/test-definition files:

- `src/execution/external_close_evidence.py`
- `src/execution/external_close_binding.py`
- `tests/execution/test_external_close_evidence.py`
- `tests/execution/test_external_close_binding.py`

Task evidence/status files:

- `status/e4/FP04_FP10_EVIDENCE_PRODUCER_20260829.md`
- `coordination/E4/STATUS.md`

No `contracts/**`, E5, E6, E7, provider transport/config, credential, risk-policy, release-gate, or AgentBridge file is changed.

## 4. Contracts consumed

- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`
- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`
- existing shared Position / OrderRequest / OrderResult / Fill semantics under `contracts-v0.1`
- accepted lifecycle projection and lifecycle execution binding profiles through their public validators
- accepted FP-05 provider-local state vocabulary only as referenced provider-local evidence

Relevant accepted implementation expectations inspected:

- E5 `src/position/external_close_policy.py`
- E5 `src/position/external_close_reinterpretation.py`
- E5 package public exports
- E6 `src/storage/external_close_currentness.py`
- `status/PM_E6_026_REVIEW_20260829.md`

## 5. Contracts produced or changed

```text
NONE
```

No shared schema, enum, lifecycle transition, E5 policy, E6 persistence rule, provider capability row, or E7 architecture is changed.

No shared-contract change request is required by the bounded implementation candidate.

## 6. Deterministic test definitions

`tests/execution/test_external_close_evidence.py` defines credential-free coverage for:

### FP-04

- exact current-known-owned success tuple;
- external/manual provenance remains external and is not adopted;
- prior runtime/generation provenance remains prior-generation and reconciliation-required;
- contradictory local lineage / provider-binding conflict fails closed;
- stale registry evidence cannot produce current-known-owned;
- unknown lineage cannot produce current-known-owned;
- materially changed provider snapshot/generation creates a new ID with explicit supersession and invalidates old currentness;
- canonical identity is invariant to mapping insertion order;
- a later evaluation timestamp alone cannot convert stale evidence into current-known-owned authority.

### FP-10

- terminal/FILLED-like execution evidence plus positive Position cannot become close-eligible;
- manual partial reduction remains external/non-flat and does not adopt lineage;
- positive representable residual remains non-flat;
- positive unrepresentable residual is explicit and blocks tight retry;
- flat Position with ambiguous execution remains reconciliation-required;
- flat Position with nonconverged terminal protection remains protection-convergence-required;
- exact flat/current/compatible chain can produce a shared-validator-consumable close-eligible evidence object;
- missing or generation-mismatched FP-04 cannot support close eligibility;
- provider, FP-04, FP-05, FP-11, or runtime evidence changes invalidate older material-currentness;
- canonical identity is invariant to mapping insertion order;
- explicit FP-10 supersession preserves prior immutable state;
- fixture surface contains no credentials/network/provider mutation capability.

`tests/execution/test_external_close_binding.py` additionally defines the exact Position-to-FP-04 binding regression:

- exact provider Position snapshot/generation/time matches one FP-04 `POSITION_EXPOSURE` object and can be consumed by E5 validation;
- different provider Position snapshot/generation is rejected before FP-10 assembly;
- absence of a matching `POSITION_EXPOSURE` FP-04 object is rejected even if another provider-object-class record exists;
- external/manual exact Position binding preserves external provenance;
- a newer provider Position generation invalidates prior FP-10 currentness.

No test was executed by this ChatGPT session.

## 7. Local verification

Executable verification is required for task `E4-20260829-030`, but the current authoritative approved-local exact-revision infrastructure remains blocked by the existing LF-0 preparation blocker. This conversation has no Product-Owner-approved local execution action.

```text
Result: NOT_RUN / NOT_PASS
Reason: approved-local exact-revision execution path unavailable in this conversation; GitHub compute is forbidden
```

Required local Windows PowerShell commands after an authoritative exact-clean candidate is available:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.execution.test_external_close_evidence -v
python -m unittest tests.execution.test_external_close_binding -v
python -m unittest tests.position.test_external_close_reinterpretation -v
python -m unittest tests.storage.test_external_close_currentness -v
python -m unittest tests.storage.test_external_close_currentness_supersession -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Any later integrated candidate requires the then-current E7/PM-selected full credential-free qualification matrix on that exact revision. Historical PASS evidence must not be rebound to this branch.

## 8. Known limitations

- This is an implementation **candidate** with test definitions; it is not executable-qualified because tests are `NOT_RUN`.
- The producer consumes already-supplied normalized provider facts. It does not discover/fetch provider objects.
- E4 does not implement or infer OKX `POSITION_EXIT`, `EMERGENCY_EXIT`, protection, `posSide`, provider reduce-only, close lot/minimum, dust/full-close, or other unresolved mutation semantics here.
- The FP-04 evaluation context accepts owner-authoritative current/prior/external/conflict classification inputs; it cannot independently prove a runtime generation without the corresponding supplied runtime/lineage facts. Unknown/conflicting generation inputs fail closed.
- The FP-10 assembler does not select an E5 convergence/lifecycle policy result. Callers must supply an accepted convergence-state/reason/disposition interpretation; E4 rejects false-green structural combinations.
- Lifecycle-close eligibility remains separate from `trade-result-v0.1` eligibility. This task never manufactures missing external/manual Fill lineage.
- Provider Position omission/zero-row semantics remain provider-specific and are not invented.

## 9. Dependencies / blockers

Implementation dependency status:

```text
shared contract contradiction = NONE OBSERVED
E5 consumer shape = STATICALLY MATCHED
E6 persistence shape = STATICALLY MATCHED
provider/private dependency = NONE for deterministic implementation/tests
```

Executable qualification blocker:

```text
LF-0 exact-revision approved-local infrastructure = BLOCKED / UNCHANGED
project verification for this branch = NOT_RUN / NOT_PASS
```

This blocker is infrastructure/evidence authority only. It is not a request for trading, provider, credential, runtime, or capital authority.

## 10. Required next action

E4 stops after this task.

After PM/E7 static review and after approved-local exact-revision preparation is available, the responsible integration/qualification task should run the exact E4/E5/E6 deterministic matrices on one exact integrated revision. E4 does not self-start that qualification or another FP task.

## 11. Security / secrets

Confirmed:

```text
real API key/secret/passphrase/token/password/private key committed = NO
credential reader added = NO
raw private provider payload persisted = NO
provider auth/signature material added = NO
fixtures = sanitized / deterministic / credential-free
```

## 12. GitHub compute policy

Confirmed:

```text
GitHub Actions workflow created = NO
GitHub Actions / CI used = NO
GitHub-hosted runner used = NO
GitHub-triggered self-hosted runner used = NO
project code/test execution on GitHub = NO
```

GitHub was used only for repository reads/writes/branch collaboration.

## 13. Provider / runtime / live-trading impact

This task grants no execution authority.

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW runtime = NOT_STARTED
PAPER runtime = NOT_STARTED
10U bounded live-fire = NOT_AUTHORIZED / NOT_STARTED
capital exposure = NONE
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

The code only constructs deterministic evidence objects from facts supplied by a later authorized observer/orchestrator. It contains no provider transport.

## 14. Terminal classification

```text
source implementation = COMPLETE FOR BOUNDED TASK
credential-free test definitions = COMPLETE FOR BOUNDED TASK
approved-local executable verification = NOT_RUN / NOT_PASS
terminal task state = PARTIAL
```

`PARTIAL` is used only because task completion requires executable PASS for `DONE`; `NOT_RUN != PASS`. No implementation blocker or shared-contract contradiction is claimed.
