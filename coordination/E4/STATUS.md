# E4 Status

- task_id: `E4-20260829-031`
- agent: `E4`
- state: `PARTIAL`
- branch: `agent/e4-fp05-close-residual-sizing-implementation-20260829`
- baseline_main_sha: `e9e8aa6674bc5696a194e61e2e0dc1b4b75ef86c`
- head_sha: `08b9549049714670b5c6e6fe15b2fdecf9a05195` (source/tests/handoff HEAD immediately before this terminal STATUS-only commit)
- summary: `Implemented the bounded provider-free E4 FP-05 OKX close/residual sizing evaluator and immutable provider-local sizing evidence. The evaluator preserves exact close-v0.1 authority/current Position binding, exact FP-04 provider Position ownership/currentness, explicit FP-02 close-role capability proof, exact close-metadata applicability binding, deterministic floor quantization/no-over-reduction, post-action provider-observation-only residual truth, stable unrepresentable residual handling, material currentness and immutable supersession. Current real POSITION_EXIT/EMERGENCY_EXIT provider capability remains UNRESOLVED_FAIL_CLOSED; test REPO_EVIDENCED rows are deterministic hypothetical proof fixtures only. Executable verification remains NOT_RUN because approved-local exact-revision infrastructure is blocked.`
- files_changed: `src/brokers/okx_close_sizing.py; src/brokers/okx_close_sizing_binding.py; tests/brokers/test_okx_close_sizing.py; tests/brokers/test_okx_close_sizing_binding.py; tests/brokers/test_okx_close_sizing_currentness.py; status/e4/FP05_CLOSE_RESIDUAL_SIZING_IMPLEMENTATION_20260829.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- shared_architecture_changed: `NO`
- e5_policy_changed: `NO`
- e6_persistence_changed: `NO`
- provider_transport_changed: `NO`
- executable_verification: `NOT_RUN / NOT_PASS`
- blockers: `Executable qualification only: LF-0 approved-local exact-revision preparation remains blocked/unavailable. Source/test-definition scope is complete.`
- handoff_path: `status/e4/FP05_CLOSE_RESIDUAL_SIZING_IMPLEMENTATION_20260829.md`
- gate_effect: `Implementation candidate only. FP-05 executable PASS, provider close capability, LF-2 closure, SHADOW/PAPER, 10U bounded live-fire, Gate D and LIVE are not claimed or authorized.`

## Wake / authority verification

Wake task ID `E4-20260829-031` matched latest `main:coordination/E4/TASK.md` exactly before implementation/write work.

Read first from latest `main`:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK mailbox was read; no other Worker TASK mailbox was read or executed.

## Baseline / branch

At task start:

```text
main = e9e8aa6674bc5696a194e61e2e0dc1b4b75ef86c
target branch = did not exist
```

The branch was created from that exact revision. No merge, rebase, force update, destructive history rewrite, GitHub Actions, CI, hosted runner or GitHub-triggered compute was used.

## Implemented FP-05 boundary

The task-facing provider-local implementation is:

```text
src/brokers/okx_close_sizing.py
src/brokers/okx_close_sizing_binding.py
```

It operates only on supplied in-memory facts and emits no provider request.

Evaluation precedence is fail closed:

```text
exact close-v0.1 authority / role
-> exact source/current Position lineage
-> unresolved prior close outcome check
-> exact current FP-04 Position ownership/currentness
-> exact current provider reducible exposure / normalized canonical quantity
-> exact flat or mismatch interpretation
-> explicit close-role FP-02 capability proof
-> exact metadata ref/hash/generation + close-applicability proof
-> deterministic floor quantization and no-over-reduction checks
-> provider-local FP-05 sizing state/evidence
```

No lower-precedence arithmetic can override an earlier authority/currentness/conflict failure.

## Residual / flat semantics

The evaluator distinguishes `PRE_ACTION` and `POST_ACTION_RESIDUAL`.

For post-action evaluation, the original PositionAction remains bound to the original source Position. Current residual/flatness comes only from a fresh same-lineage Position/provider observation. The implementation never treats:

```text
old Position quantity - requested/ACKed close quantity
```

as authoritative residual truth.

Fresh exact provider/canonical zero can produce only provider-local:

```text
EXPOSURE_ALREADY_FLAT
```

It does not emit E5 lifecycle `CLOSED`, `POSITION_CLOSED`, `RECONCILED_FLAT`, TradeResult or provider cleanup authority.

A positive unrepresentable residual remains:

```text
RESIDUAL_NONZERO_UNREPRESENTABLE
```

with no provider request size and, on post-action residual evidence, an explicit newer-evidence requirement before a future re-evaluation/mutation path.

## Capability / metadata fail-closed behavior

Current accepted design still states real provider mutation rows for:

```text
POSITION_EXIT = UNRESOLVED_FAIL_CLOSED
EMERGENCY_EXIT = UNRESOLVED_FAIL_CLOSED
```

The implementation does not upgrade them. It can calculate representability only from an explicitly supplied typed proof for one exact close role. Test fixtures marked `REPO_EVIDENCED` are hypothetical deterministic proof fixtures only and are not rebound to real OKX provider capability.

The strict binding layer requires one exact metadata/applicability tuple:

```text
instrument metadata ref/hash/generation
+ metadata applicability proof ref/hash/generation
```

before any close conversion/step/min/max can control sizing. ENTRY-only metadata applicability is rejected.

## States implemented

Exactly:

- `FULLY_REDUCIBLE`
- `PARTIALLY_REDUCIBLE`
- `RESIDUAL_NONZERO_REPRESENTABLE`
- `RESIDUAL_NONZERO_UNREPRESENTABLE`
- `EXPOSURE_ALREADY_FLAT`
- `REDUCIBLE_EXPOSURE_UNKNOWN`
- `METADATA_STALE_OR_UNKNOWN`
- `RECONCILIATION_REQUIRED`
- `CLOSE_CAPABILITY_UNPROVEN`

They remain E4 provider-local evidence/routing facts, not lifecycle states or mutation authority.

## Tests defined

Added provider-free deterministic definitions:

- `tests/brokers/test_okx_close_sizing.py`
- `tests/brokers/test_okx_close_sizing_binding.py`
- `tests/brokers/test_okx_close_sizing_currentness.py`

They cover full/partial representability, fresh positive residual, unrepresentable residual, exact flat truth, unknown/stale/conflicting inputs, external ownership without adoption, unresolved capability, close metadata applicability, ambiguous prior outcome, no-over-reduction quantization, exact metadata binding, material currentness invalidation, timestamp-only non-refresh, explicit supersession, deterministic identity and EMERGENCY_EXIT parity.

## Verification / execution state

No approved-local execution action is available because LF-0 exact-revision preparation remains blocked.

```text
project executable verification = NOT_RUN / NOT_PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
LF-2 = NOT PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

Required later approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_okx_close_sizing*.py" -v
python -m unittest tests.execution.test_close -v
python -m unittest discover -s tests/execution -p "test_external_close*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

All remain `NOT_RUN / NOT_PASS`. Historical qualification is not rebound to this branch.

## Security / authority boundary

```text
real secrets read/requested/committed = NO
provider/private network = NONE
provider transport/mutation path added = NO
risk/lifecycle policy change = NO
E6 persistence/current-head logic change = NO
shared contract change = NO
runtime/live/capital authority = NONE
```

## Terminal classification / stop

```text
bounded source implementation = COMPLETE
bounded deterministic test definitions = COMPLETE
approved-local executable verification = NOT_RUN / NOT_PASS
state = PARTIAL
```

`NOT_RUN != PASS`, so `DONE` is not claimed. E4 stops at this task and does not self-start provider verification, FP-02 provider translation, E7 integration/requalification, exact-revision preparation, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
