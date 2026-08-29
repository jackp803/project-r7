# E6 FP-11 Projection Hash-Domain Remediation — 2026-08-29

## Task

```text
task_id = E6-20260829-029
agent = E6
target_branch = agent/e6-fp11-persistence-currentness-20260829
authoritative_main_at_task_start = eaa2b0ac62e6bc7ace283653a15775d32f8f0ee1
terminal_classification = PARTIAL
project executable verification = NOT_RUN / NOT_PASS
```

This task is the bounded remediation requested by `status/PM_E6_028_REVIEW_20260829.md`. It changes only the E6 FP-11 restart/currentness consumer and its E6 storage regression definitions. No shared contract, provider producer, E5 interpretation, lifecycle policy, migration semantics, provider capability, runtime authorization, or capital authority is changed.

## PM defect reproduced statically

The accepted E6 Paper writer `src/storage/_paper_runtime.py::_PaperRuntimeStore.persist_position_projection()` canonicalizes the complete lifecycle projection payload and writes that exact lifecycle-projection payload hash to both:

```text
paper_position_lifecycle_projections.payload_hash
paper_position_current_projection.payload_hash
```

E6-028 recovery incorrectly compared those two storage fields to the FP-11/current-authority `position_hash` domain. That mixed two independent evidence domains and could false-stale/conflict a correctly persisted lifecycle projection.

The two domains are now kept explicit:

```text
Position authority domain
  current["position_hash"]
  = canonical Position hash used by FP-11 and the E5 interpretation envelope

Lifecycle projection storage domain
  current["projection_payload_json"]
  current["projection_payload_hash"]
  = exact canonical payload JSON/hash produced with the same E6 canonical_payload()
    primitive used by _PaperRuntimeStore.persist_position_projection()
```

No Position hashing rule was changed.

## Exact source remediation

Changed source:

```text
src/storage/protection_registry_currentness.py
```

`_validate_authority(...)` now derives the lifecycle projection storage payload with the existing E6 `canonical_payload()` primitive and retains both domains independently:

```text
position_hash
projection_payload_json
projection_payload_hash
```

`recover(...)` now requires `paper_position_current_projection` to match the supplied owner-authoritative current projection on all of:

```text
position_id
lifecycle_projection_id
lifecycle_revision
broker_state_observed_at
projection_payload_hash
```

The selected immutable `paper_position_lifecycle_projections` row must separately match:

```text
position_id
lifecycle_revision
broker_state_observed_at
exact canonical projection payload_json
exact canonical projection payload_hash
```

Failure remains fail closed:

```text
current-index mismatch -> STALE / CURRENT_LIFECYCLE_PROJECTION_SUPERSEDED_OR_MISMATCHED
history metadata mismatch -> CONFLICT / FP11_LIFECYCLE_PROJECTION_INDEX_MISMATCH
history payload mismatch -> CONFLICT / FP11_LIFECYCLE_PROJECTION_PAYLOAD_MISMATCH
history payload-hash mismatch -> CONFLICT / FP11_LIFECYCLE_PROJECTION_HASH_MISMATCH
```

The FP-11 top-level `position_hash`, intended-lineage `position_hash`, and stored E5 interpretation `position_hash` continue to use only the canonical Position authority hash. They are not rebound to lifecycle projection storage hashes.

## Preserved E6-028 behavior

Unchanged behavior includes:

- immutable FP-11 evidence history;
- duplicate deterministic ID + changed payload conflict;
- explicit same-lineage supersession as the only current-head advancement mechanism;
- competing-head, missing-predecessor, cycle, disconnected-history and cross-lineage fail-closed handling;
- exact FP-04 dependency/reference/current-head validation;
- exact E5 decision/source evidence/material binding;
- current Position/lifecycle/provider-set/runtime material checks;
- non-green missing/multiple/orphan/external/conflict/stale/unknown states;
- FP-10 terminal-flat protection convergence dependency;
- false-green CLOSED prevention;
- mechanically fixed `provider_mutation_authorized = false`;
- mechanically fixed `cleanup_target_ref = null`.

Unchanged files/semantics include:

```text
src/storage/_paper_runtime.py
src/storage/migrations/0002_paper_runtime_durability.sql
src/storage/migrations/0006_protection_registry_currentness.sql
contracts/**
src/execution/**
src/position/**
```

## Regression definitions

Changed test definition:

```text
tests/storage/test_protection_registry_currentness.py
```

The lifecycle seed path now uses the real existing E6 writer instead of hand-inserting the projection/current rows:

```text
_open_paper_runtime_store(...)
-> _PaperRuntimeStore.persist_position_projection(...)
-> persist_lifecycle_execution_binding(...)
```

New bounded regression definitions cover:

1. a normal projection persisted by the existing Paper runtime writer remains acceptable to FP-11 restart/currentness when every dependency is exact;
2. lifecycle projection payload hash is evaluated in its own storage domain rather than substituted with Position authority hash;
3. corrupted `paper_position_current_projection.payload_hash` fails closed;
4. corrupted immutable lifecycle projection `payload_hash` fails closed;
5. corrupted immutable lifecycle projection `payload_json` fails closed;
6. current projection ID, revision, or broker-state observation anchor mismatch fails closed;
7. canonical Position-hash mismatch independently invalidates FP-11/E5 currentness;
8. the existing exact FP-11 + E5 + Position/lifecycle/FP-04/provider/runtime healthy-path requirement remains defined;
9. flat/CLOSED unresolved protection remains reconciliation-required through existing tests;
10. provider mutation/cleanup authority remains absent through existing tests.

These are definitions only. They were not executed through GitHub or any other unapproved environment.

## Verification truth

The active LF-0 exact-revision preparation blocker remains unchanged. No independently Product-Owner-approved local exact-revision execution path is available in this session.

Therefore:

```text
project executable verification = NOT_RUN / NOT_PASS
bounded FP-11 remediation regression = NOT_RUN / NOT_PASS
storage migration/restart regression = NOT_RUN / NOT_PASS
E4 FP-11 regression = NOT_RUN / NOT_PASS
E5 FP-11 regression = NOT_RUN / NOT_PASS
safety regression = NOT_RUN / NOT_PASS
```

Exact future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.storage.test_protection_registry_currentness -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest tests.execution.test_protection_registry_evidence -v
python -m unittest tests.position.test_protection_registry_policy -v
python -m unittest tests.safety.test_fp11_protection_registry_false_green -v
```

`NOT_RUN != PASS`.

## Authority and safety boundary

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

This remediation grants no provider, credential, runtime, mutation, cleanup, live-trading, or capital authority.

## Result / downstream

The bounded static remediation and regression definitions are materialized, but `DONE` is forbidden without approved-local exact-revision executable PASS evidence. Therefore task `E6-20260829-029` is `PARTIAL`.

Next integration/requalification remains a separate PM/E7 action after the approved-local exact-revision path is available. E6 stops here and does not self-start qualification, provider verification, SHADOW/PAPER, live-fire, Gate D, LIVE, mutation, or another task.
