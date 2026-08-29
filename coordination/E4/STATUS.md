# E4 Status

- task_id: `E4-20260829-028`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-fp05-close-residual-sizing-design-20260829`
- baseline_main_sha: `466b167e32fc84e1906e0e80bae7c55e31a517fc`
- head_sha: `403fadbac68c06b2558a4e932d432c2cf12be194` (design/handoff HEAD immediately before this terminal STATUS-only commit)
- summary: `Completed only the docs/status FP-05 provider-local design baseline okx-swap-close-residual-sizing-v0.1. The design binds fresh E5 close authority to exact current canonical Position truth, exact current provider reducible exposure, FP-04 ownership/reconciliation, accepted FP-02 close-role capability, and current close-applicable metadata before any provider-native quantity can be calculated. It defines explicit fully/partially reducible and representable/unrepresentable residual states, forbids original ENTRY quantity or arithmetic residual from becoming current exposure truth, blocks unchanged residual retry loops, and requires authoritative post-action provider Position truth for residual/flatness. Unproven OKX close-specific field/position-mode/min/max/reduce semantics remain fail closed.`
- files_changed: `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md; status/e4/FP05_OKX_SWAP_CLOSE_RESIDUAL_SIZING_DESIGN_20260829.md; coordination/E4/STATUS.md`
- executable_source_changed: `NO`
- tests_changed: `NO`
- contracts_changed: `NO`
- shared_architecture_changed: `NO`
- shared_contract_change_required: `NO / none proven by this design`
- executable_verification: `NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK`
- blockers: `NONE for bounded design completion`
- handoff_path: `status/e4/FP05_OKX_SWAP_CLOSE_RESIDUAL_SIZING_DESIGN_20260829.md`
- gate_effect: `Design baseline only. No executable FP-05 PASS, provider/private verification, provider close capability, SHADOW/PAPER runtime, 10U live-fire, Gate D, LIVE or capital exposure is authorized or claimed.`

## Wake / authority verification

Wake task ID `E4-20260829-028` matched latest `main:coordination/E4/TASK.md` exactly before any implementation/write work.

Authoritative files read first:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK mailbox was read; no other Agent TASK mailbox was read or executed.

## Baseline / branch

At task start:

```text
main = 466b167e32fc84e1906e0e80bae7c55e31a517fc
target branch = did not exist
```

The target branch was created from that exact main revision. No merge, rebase, force update, destructive history rewrite, GitHub Actions, CI, hosted runner or GitHub-triggered compute was used.

## Required design evidence inspected

Read-only design inputs included:

- `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`
- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`
- `contracts/SHARED_CONTRACTS_V1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-05 / FP-10 evidence
- `status/PM_E7_107_REVIEW_20260829.md`
- current E4 `src/brokers/okx_sizing.py`, `src/brokers/okx_demo.py`, `src/execution/close.py`
- current E4-owned close/sizing tests

No provider web/documentation semantics were substituted for repository authority and no provider request was made.

## FP-05 design result

Created:

```text
docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md
profile = okx-swap-close-residual-sizing-v0.1
```

The design defines this authority hierarchy:

```text
E5 close-v0.1 PositionAction
-> exact current normalized Position.actual_quantity / observation
-> exact current provider-native reducible exposure
-> current FP-04 ownership/reconciliation
-> accepted exact FP-02 close-role capability row
-> current close-applicable provider metadata generation
-> accepted close step/lot/min/max constraints
-> bounded quantized provider-native close size
-> fresh post-action provider Position observation
-> explicit residual representability state
```

Original requested ENTRY quantity, plan maximum, stale local quantity, prior close requested quantity, local arithmetic remainder, ACK or terminal order status cannot override newer authoritative Position/provider truth.

## Residual states / behavior

Stable E4 provider-local states defined:

```text
FULLY_REDUCIBLE
PARTIALLY_REDUCIBLE
RESIDUAL_NONZERO_REPRESENTABLE
RESIDUAL_NONZERO_UNREPRESENTABLE
EXPOSURE_ALREADY_FLAT
REDUCIBLE_EXPOSURE_UNKNOWN
METADATA_STALE_OR_UNKNOWN
RECONCILIATION_REQUIRED
CLOSE_CAPABILITY_UNPROVEN
```

`EXPOSURE_ALREADY_FLAT` requires fresh authoritative provider/normalized Position zero-exposure truth. It cannot be inferred from ACK, FILLED/terminal order status, requested-size arithmetic, expected fills, missing local state or caller assertion.

A fresh positive non-representable residual is a stable fail-closed state. Unchanged Position/metadata/capability/ownership evidence cannot produce a tight/unbounded retry. A new close evaluation requires materially newer evidence and fresh applicable E5 close authority.

Ambiguous prior close outcome always enters reconciliation before any second logical close request.

## Metadata / provider-specific boundary

Current repository ENTRY sizing vocabulary (`ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `maxMktSz`, `tickSz`, state, metadata ref/observed-at/freshness, scheduled changes) is recorded as repository-evidenced ENTRY metadata vocabulary only.

The design does not assume those ENTRY limits automatically govern close roles. Future role-specific capability/metadata evidence must classify each required close fact as required/applicable/not-applicable/unresolved before it can control provider sizing.

Exact unresolved provider-specific facts remain fail closed, including:

- provider Position quantity/sign semantics for close sizing in `net_mode` / `long_short_mode`;
- exact close provider field set and role-specific `posSide` behavior;
- provider-native reduce-only field semantics;
- whether ENTRY `lotSz`, `minSz`, `maxMktSz` apply identically to reduction;
- any separate reduce/close maximum, below-minimum close exception, special full-close/dust mechanism or special endpoint/flag.

No current provider/private verification for those facts is claimed.

## Dependency boundaries

### FP-02

`POSITION_EXIT` and `EMERGENCY_EXIT` remain role-specific and currently provider-mutation `UNRESOLVED_FAIL_CLOSED`. FP-05 sizing design does not make either row executable. Spot/cash semantics and caller-manufactured capability authority remain forbidden.

### FP-04

Unknown/conflicting/external/prior-generation/stale provider exposure cannot become trusted reducible-size authority without accepted ownership/reconciliation evidence. FP-05 does not silently adopt external/manual exposure.

### FP-11

Reduced/flat Position truth does not erase or cancel provider protections. Protection multiplicity/ownership/cleanup remains FP-11 evidence/policy.

### FP-10

FP-10 remains downstream and later consumes authoritative reduced/flat Position truth, aggregate execution/fill evidence, FP-04 ownership/reconciliation, FP-11 protection convergence, and E5 lifecycle interpretation. FP-05 does not emit `RECONCILED_FLAT`, `CLOSED`, `POSITION_CLOSED`, lifecycle transitions or TradeResult.

## Future implementation/test handoff

The handoff defines the smallest later E4 provider-local executable component (`okx_close_sizing` or equivalent) and immutable sizing evidence. Required future credential-free tests cover:

- current exposure smaller than original entry quantity;
- external/manual/changed exposure blocking under unresolved FP-04 truth;
- no over-reduction;
- exact step/lot quantization;
- fully/partially reducible states;
- representable/unrepresentable residuals;
- no unchanged-residual retry;
- materially newer Position/metadata re-evaluation;
- zero/negative size rejection;
- stale/unknown/applicability-unproven metadata rejection;
- unknown capability rejection;
- ENTRY sizing evidence not accepted as close authority;
- ambiguous prior close reconciliation;
- ACK/terminal not equal flat;
- authoritative flat Position only;
- EMERGENCY_EXIT obeying identical proof requirements;
- deterministic/no-network/no-credential fixtures.

No executable implementation or test definition was added by E4-028.

## Verification / execution state

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER = NOT_STARTED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
FP-03 combined qualification = NOT_RUN / NOT_PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS. DONE here means only the bounded docs/status FP-05 design task is complete.

## Completion boundary

E4 stops at this terminal `DONE` status. E4 does not self-start executable FP-05 implementation, FP-02 executable translation, FP-10, FP-11 executable work, provider verification, exact-revision preparation, qualification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.