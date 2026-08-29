# E5 FP-11 Protection Registry Policy Consumer — 2026-08-29

## Task / result

```text
task_id = E5-20260829-033
agent = E5
state = PARTIAL
branch = agent/e5-fp11-protection-policy-consumer-20260829
base_main_sha = 90154be0bbe180d0aed1c372aad5a0f25283b59a
implementation_head_before_evidence = b0316dc659fcbbc839ce2df532bde0def36c7f2a
project executable verification = NOT_RUN / NOT_PASS
```

`PARTIAL` is required by the task because the bounded implementation and deterministic test definitions are materialized, but LF-0 approved-local exact-revision preparation remains blocked and no independently approved local exact-revision runner is available to this worker.

## Exact files changed by this task

Production / tests:

- `src/position/protection_registry_policy.py`
- `src/position/__init__.py`
- `tests/position/test_protection_registry_policy.py`
- `tests/safety/test_fp11_protection_registry_false_green.py`

Durable task evidence / mailbox:

- `status/e5/FP11_PROTECTION_REGISTRY_POLICY_CONSUMER_20260829.md`
- `coordination/E5/STATUS.md`

No `contracts/**`, E4/E6/E7 implementation/docs, provider adapter, transport/auth/config, AgentBridge, release criteria, risk-limit, leverage, capital-threshold, or GitHub Actions/CI file is modified.

## Accepted profiles / authority consumed

The E5 consumer is bounded by the already accepted repository authority:

- `contracts-v0.1`;
- `protection-registry-multiplicity-v0.1`;
- `protection-v0.1`;
- `position-lifecycle-projection-v0.1`;
- `position-lifecycle-execution-binding-v0.1`;
- FP-10 `external-manual-close-lifecycle-convergence-v0.1` only for the existing terminal-flat protection-convergence dependency;
- the merged E4 FP-11 provider-neutral producer/currentness candidate as static producer evidence, without importing provider mutation authority.

No parallel shared contract, provider-specific action type, cleanup command, new lifecycle state, or new shared PositionEvent is introduced.

## Implemented E5 interpretation boundary

```text
one exact current canonical Position/reference/hash
+ exact current E5 lifecycle projection
+ exact lifecycle execution binding when present
+ one immutable ProtectionRegistryMultiplicityEvidence
+ exact provider-set/current runtime generation references carried by accepted evidence
-> deterministic E5 protection/lifecycle interpretation
```

The result is E5-internal policy interpretation only. It carries no provider command, provider object cleanup target, create/cancel/replace authority, new-exposure approval, runtime authorization, or capital authority.

`ProtectionRegistryPolicyDecision` binds deterministic decision identity to material current Position/lifecycle/binding/FP-11 evidence and resulting existing E5 event/state/reasons. It records the exact source FP-11 evidence ID/hash for audit while using a material source hash that excludes only `protection_registry_evidence_id`, `supersedes_registry_evidence_id`, and `evaluated_at` so timestamp-only reevaluation cannot create a materially new E5 decision.

## Validation / currentness semantics

The consumer validates provider-neutral shared material without performing provider reads:

- exact FP-11 schema/profile/field set;
- deterministic `protregmul_...` evidence identity;
- exact intended-lineage field set and hash;
- exact Position ref/hash/id/observation binding;
- exact lifecycle projection ID/revision/reference;
- exact lifecycle execution-binding reference when present;
- exact provider identity/instrument/observation generation and provider-set hash;
- exact runtime/process/config generation references when present;
- canonical observed object sequence/count/hash;
- deterministic shared disposition/reason vocabulary and exact success tuple.

`fp11_registry_evidence_is_current()` fails closed when current Position, lifecycle projection, execution binding, provider observation generation/set hash, or runtime generation no longer matches the immutable FP-11 object. `provider_set_currentness_status != CURRENT` is never current.

A later evaluation timestamp alone is deliberately not a currentness axis. Materially newer Position/lifecycle/provider-set/FP-11/runtime truth invalidates an older E5 interpretation.

## Deterministic policy behavior

### Exact converged unique protection

Only the exact accepted success tuple:

```text
multiplicity_state = EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
registry_status = CONVERGED_EXACTLY_ONE_INTENDED
required_dispositions = [NO_ACTION_REGISTRY_CONVERGED]
reason_codes = [EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED]
```

can support a healthy unique-protection interpretation.

When the exact current lifecycle is already `OPEN_PROTECTED` or `PROFIT_PROTECTED`, the consumer preserves that state with no new lifecycle event. It does not fabricate `PROTECTION_VERIFIED` merely because FP-11 is converged, and it never creates provider mutation authority.

If the lifecycle authority is incompatible, stale or mismatched, the result is fail-closed reconciliation/reinterpretation rather than forcing either registry or lifecycle state to match.

### Missing protection

For exact complete/current:

```text
NO_ACTIVE_PROTECTION_OBSERVED
+ MISSING_PROTECTION_REINTERPRETATION_REQUIRED
```

an existing protected lifecycle claim is no longer safely established. For `OPEN_PROTECTED` or `PROFIT_PROTECTED`, the consumer reuses the already accepted E5 `PROTECTION_LOST` event, producing the existing `EMERGENCY` transition.

If the current lifecycle is already unprotected/emergency/exiting/reconciling, the consumer returns a bounded hold-safe/policy-required result with no provider mutation authority. FP-11 absence is never itself permission to emit or execute `PROTECT`.

### Multiple protection objects

`MULTIPLE_ACTIVE_PROTECTIONS` always fails closed into existing reconciliation semantics. The E5 decision contains no winning provider object, cancel target or cleanup target. No newest/closest/first object selection exists.

### Orphan / external / prior-generation object

`ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT` remains non-healthy and requires reconciliation. Existing external/prior provider objects are not adopted into current intended lineage by symbol, side, quantity, price or identifier similarity.

### Ownership conflict / unknown

`OWNERSHIP_CONFLICT_PRESENT`, unknown lineage/ownership and non-converged manual-review states remain fail closed. The consumer preserves the shared source dispositions/reasons and does not convert them to mutation authority.

### Stale / incomplete / unknown provider set

`PROTECTION_SET_STALE`, `PROTECTION_SET_UNKNOWN`, incomplete coverage, unknown coverage, stale currentness or exact reference mismatch cannot become healthy protection. They route through existing E5 reconciliation semantics.

### Terminal / flat interaction with FP-10

If FP-11 carries:

```text
FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED
```

the consumer preserves that dependency and never treats flat canonical Position truth as sufficient to erase unresolved provider protection.

A stale local `CLOSED` claim plus unresolved active protection uses the already accepted:

```text
CLOSED + STATE_UNKNOWN -> RECONCILIATION_REQUIRED
```

path, preventing a false-green terminal lifecycle state. E5 does not select or authorize provider cleanup/cancel targets.

## Tests defined

`tests/position/test_protection_registry_policy.py` defines provider-free deterministic coverage for:

1. exact current converged FP-11 + compatible protected lifecycle preserves the healthy protected interpretation with no new event/mutation authority;
2. converged FP-11 + incompatible `OPEN_UNPROTECTED` lifecycle fails closed and never fabricates `PROTECTION_VERIFIED`;
3. stale/missing lifecycle execution-binding authority invalidates otherwise converged FP-11;
4. complete/current missing protection while lifecycle claims protected -> existing `PROTECTION_LOST -> EMERGENCY` path;
5. missing protection while already unprotected does not authorize a PROTECT/provider mutation;
6. multiple active protections -> reconciliation, no winner/cleanup target;
7. one intended object plus an external extra -> fail closed, no adoption;
8. ownership conflict and unknown ownership/lineage -> reconciliation/manual-review-safe interpretation;
9. stale/incomplete/unknown provider-set truth never becomes healthy;
10. changed Position, provider observation generation or lifecycle binding invalidates prior interpretation;
11. materially changed FP-11 evidence invalidates the old interpretation;
12. timestamp-only reevaluation does not create a materially new E5 decision;
13. flat/CLOSED + unresolved active external protection preserves FP-10 terminal convergence dependency and re-enters reconciliation rather than remaining false-green CLOSED;
14. same exact inputs are deterministic.

`tests/safety/test_fp11_protection_registry_false_green.py` additionally defines E5-owned safety coverage that:

- flat Position + unresolved active protection cannot remain false-green `CLOSED`;
- multiple protection truth cannot select a cleanup target or claim healthy protection.

These definitions use deterministic fixtures only. No provider/network/credential access is required.

## Executable verification

Authoritative LF-0 approved-local exact-revision preparation remains blocked. No approved local exact-revision runner is exposed to this worker.

```text
project executable verification = NOT_RUN / NOT_PASS
```

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.position.test_protection_registry_policy -v
python -m unittest tests.safety.test_fp11_protection_registry_false_green -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN` is not PASS. GitHub Actions/CI/hosted/GitHub-triggered compute was not used.

## Known limitations / downstream needs

- This task does not qualify the E4 FP-11 producer or this E5 consumer executable behavior; approved-local exact-revision PASS evidence remains required later.
- This task does not persist/select FP-11 registry heads; E6 durability/currentness remains separate owner scope.
- This task does not perform E7 cross-module integration/requalification.
- FP-11 evidence does not authorize provider mutation. Any later provider protection create/cancel/replace/cleanup requires separate exact E5 action authority plus E4 capability/provider/runtime/release authority.
- Terminal/flat unresolved protection remains an FP-10 convergence dependency; this task does not clean it up.
- No new autonomous missing-protection recovery policy was invented. Where existing lifecycle semantics do not uniquely authorize an action, the consumer holds/reconciles rather than emitting provider mutation authority.

No shared-contract change request is required by the bounded static implementation.

## Authority / security boundary

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

E5 stops on `PARTIAL` for `E5-20260829-033` after writing terminal mailbox status. It does not self-start provider mutation/cleanup, E6 persistence, E7 integration/requalification, exact-revision preparation, provider verification, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, order action, or capital movement/exposure.
