# E4 Current Task

- task_id: `E4-20260829-032`
- issued_at: `2026-08-29T18:08:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp11-protection-registry-evidence-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `protection-registry-multiplicity-v0.1`, accepted `external-provider-object-ownership-reconciliation-v0.1`, merged E4 FP-04 producer/currentness candidate, accepted protection/lifecycle/execution-binding profiles, `status/PM_E4_031_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest deterministic **provider-neutral E4 FP-11 protection registry / multiplicity evidence producer** for shared `ProtectionRegistryMultiplicityEvidence` under `protection-registry-multiplicity-v0.1`.

Operate only on supplied in-memory/fixture facts. Do not call OKX or any provider endpoint, read credentials, query/create/cancel/amend/replace protection, select a cleanup target, mutate provider/account state, start SHADOW/PAPER/live runtime, or infer unresolved provider-native protection semantics.

The producer may normalize and mechanically evaluate the accepted shared multiplicity/currentness invariant. It must not decide E5 protection/lifecycle policy and must not persist/select durable current heads owned by E6.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- accepted `protection-v0.1`, position lifecycle projection, and lifecycle execution-binding profiles;
- merged E4 FP-04 producer/currentness surfaces in `src/execution/external_close_evidence.py`;
- current E4 protection/OrderRequest/client-order identity surfaces only as owner-authoritative reference material;
- `status/PM_E4_031_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Add E4-owned provider-neutral deterministic functions/types that consume:

1. one exact current canonical Position reference/hash/observation;
2. one exact owner-supplied `IntendedProtectionLineageReference` matching the accepted profile;
3. one exact `ObservedActiveProtectionSet` supplied as complete/current/incomplete/stale/unknown provider facts;
4. exact per-object current FP-04 `ACTIVE_PROTECTION` ownership evidence and exact lineage-binding facts;
5. lifecycle projection/execution-binding/runtime generation references when applicable;
6. an optional prior immutable FP-11 evidence object for explicit supersession.

Produce one immutable shared `ProtectionRegistryMultiplicityEvidence` with exact profile vocabulary, canonical set hash, deterministic `protregmul_<sha256>` identity, multiplicity state, registry status, deterministic dispositions/reasons, currentness helper, and explicit supersession.

Do not create or change a shared contract. If the accepted profile lacks a field/semantic required for safe production, record a precise E7 change request and stop at PARTIAL rather than inventing it.

## Required fail-closed semantics

### Provider-set completeness/currentness

- `COMPLETE + CURRENT + objects=[]` may produce only `NO_ACTIVE_PROTECTION_OBSERVED`; it is not healthy protection truth and must route to E5/lifecycle reinterpretation dispositions.
- `INCOMPLETE` must not be interpreted as zero or exactly-one.
- stale/unknown provider-set truth must produce `PROTECTION_SET_STALE` / `PROTECTION_SET_UNKNOWN` with refresh/blocking dispositions.
- active object count is the exact normalized set length; no provider object may be silently dropped to make the set converge.

### Exact single intended protection

`EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION + CONVERGED_EXACTLY_ONE_INTENDED` is allowed only when all accepted section-8 invariants are true simultaneously, including:

- exact current Position/intended-lineage references;
- complete/current provider set;
- exactly one active object;
- exact current/hash-valid FP-04 ownership bound to the same provider snapshot;
- ownership classification `KNOWN_OWNED_CURRENT_GENERATION`;
- reconciliation status `CURRENT_KNOWN_OWNED`;
- intended-lineage binding `EXACT_MATCH` with exact binding ref/hash;
- no extra object;
- no newer Position/provider/FP-04/lifecycle/runtime generation invalidating the evidence;
- deterministic identity/hash valid.

The converged success disposition must be exclusively `NO_ACTION_REGISTRY_CONVERGED`.

### Multiple/orphan/external/conflicting objects

- two or more active objects -> fail closed; do not choose newest/oldest/closest-price/client-ID winner;
- one intended object plus any additional object remains non-converged;
- external, prior-generation, orphan/not-matching object remains explicit and cannot be adopted by similarity;
- FP-04 conflict or ambiguous exact-lineage/object binding -> ownership conflict/manual-review path;
- unknown ownership or lineage binding must not be treated as a harmless extra object;
- uncertain cleanup authority requires `BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL`;
- no blind cancel-all and no blind create-another authority may be emitted.

### Terminal/flat interaction

If supplied Position/lifecycle truth is terminal/flat while active protection remains unresolved, preserve the provider objects and route through `FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED`. Do not erase protection because Position is flat and do not emit cleanup mutation authority.

## Canonicalization/currentness

Follow the accepted profile exactly:

- observed entries sorted lexicographically by `(provider_object_ref, provider_snapshot_hash, ownership_evidence_ref)`;
- complete provider-set hash binds provider identity/instrument/generation/observation coverage/currentness and every normalized entry;
- `protection_registry_evidence_id = protregmul_<sha256>` over complete canonical evidence except the ID field;
- materially changed Position/intended lineage/provider set/FP-04/lifecycle/runtime facts invalidate prior evidence;
- later `evaluated_at` alone must not refresh stale evidence or create a materially new supersession;
- explicit supersession must remain within the same logical Position/intended-lineage generation and must preserve immutable prior evidence.

Use only accepted reason/disposition/multiplicity/registry vocabularies. Do not invent numeric freshness/TTL thresholds.

## E5 / E6 boundary

E4 may mechanically produce FP-11 evidence and currentness only.

E4 must not:

- decide whether missing protection means PROTECT, REPLACE, EMERGENCY_EXIT, HOLD, or another lifecycle transition;
- cancel orphan/external/multiple protection objects;
- treat `NO_ACTIVE_PROTECTION_OBSERVED` as permission to create protection;
- persist/select current registry heads using E6 policy;
- turn converged registry evidence into provider mutation authority;
- treat static merged E4/E5/E6 candidates as executable PASS.

## Required tests to define

Add provider-free deterministic E4-owned tests covering at minimum:

- complete/current empty set -> `NO_ACTIVE_PROTECTION_OBSERVED` + reinterpretation/blocking dispositions, never converged;
- exact one current-owned exact-lineage object -> sole converged success tuple;
- exactly one current-owned but lineage `NOT_MATCH` -> non-converged;
- exactly one exact-lineage object but FP-04 stale/unknown/conflicting -> non-converged;
- two exact intended objects -> `MULTIPLE_ACTIVE_PROTECTIONS` and no winner selection;
- one intended + one external/prior/orphan object -> non-converged orphan/external path;
- ownership conflict -> manual-review path;
- incomplete provider set cannot become zero/exactly-one;
- stale/unknown provider set -> refresh/fail-closed state;
- terminal/flat Position plus unresolved active protection -> FP-10 terminal protection convergence disposition;
- exact set hash and evidence ID stable across equivalent mapping/input ordering;
- changed provider object/snapshot/FP-04/Position/lifecycle/runtime generation invalidates currentness and creates new immutable identity when superseded;
- later timestamp alone does not refresh evidence or justify supersession;
- no provider/network/credentials/mutation dependency.

Do not execute tests through GitHub.

## Verification boundary

All executable verification is local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless independently approved local execution authority is explicitly available in current repository evidence:

```text
project executable verification = NOT_RUN / NOT_PASS
```

Record exact future Windows/local commands for bounded FP-11 tests and relevant existing E4 FP-04/protection suites. `NOT_RUN` is not PASS.

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

## Required durable evidence

Create:

`status/e4/FP11_PROTECTION_REGISTRY_MULTIPLICITY_EVIDENCE_20260829.md`

Document task ID, exact source/test files changed, accepted profile inputs, provider-set normalization, exact-one invariant, multiplicity/orphan/conflict behavior, terminal/flat handling, canonical hash/identity/currentness/supersession behavior, tests defined, exact future local commands/result, limitations/downstream E5/E6 integration needs, and confirmation of zero provider/credential/runtime/capital authority.

Update `coordination/E4/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E4-owned paths:

- `src/execution/`;
- `src/brokers/` only if an existing provider-neutral protection-observation type belongs there and no transport behavior changes;
- `tests/execution/`;
- `tests/brokers/` only if directly required;
- `status/e4/FP11_PROTECTION_REGISTRY_MULTIPLICITY_EVIDENCE_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not modify `contracts/**`, E5/E6/E7 code/docs, provider transport/auth/config/credentials, AgentBridge/local action catalog, provider allowlists, release criteria, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if implementation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL

Use PARTIAL when implementation/test definitions are complete but executable verification remains `NOT_RUN`, or a precise shared-contract dependency prevents safe completion without invented semantics.

### BLOCKED

Use BLOCKED only for contradictory authoritative requirements or a safety dependency that prevents bounded implementation within E4 scope.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-032`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start provider verification, protection mutation/provider cleanup, E5 policy changes, E6 persistence, E7 integration/requalification, exact-revision preparation, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, order action, or capital movement/exposure.
