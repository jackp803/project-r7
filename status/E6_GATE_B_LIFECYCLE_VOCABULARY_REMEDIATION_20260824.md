# E6 Gate B Lifecycle Vocabulary Durability Remediation

- task_id: `E6-20260824-015`
- agent: `E6`
- branch: `agent/e6-gate-b-paper-runtime-durability-v2-20260824`
- disposition: `DONE / STATIC REMEDIATION MATERIALIZED / EXECUTABLE NOT_RUN`
- authoritative main at task start: `5b07a6805de2e0df1f16d558eaff801d5c8be4c5`
- PR #60 accepted contract merge: `6141d93f5b80d1dc1a0e4231a3e453d09806bf40`
- latest-main synchronization merge: `eba37192d406ed03776f345363fef7b9daf6d6ae`
- remediation source commit: `eead5ca166ad1b6814075245a59dc8924d1b8cbc`
- remediation test-definition commit: `0989aabc8a47dfb94c554ed601d935087e60d0ff`

## Scope

This remediation changes only E6-owned restart-authoritative Position lifecycle vocabulary validation and deterministic storage test definitions. It consumes, without redefining, the accepted E7 vocabulary contract:

- eight supported `lifecycle_state` values;
- thirteen supported `TRANSITION.lifecycle_event` values;
- projection kinds exactly `GENESIS | TRANSITION | REATTESTATION`;
- `GENESIS` / `REATTESTATION` require `lifecycle_event = null`;
- `TRANSITION` requires one supported non-null event.

The local constants in `src/storage/_runtime_validation.py` are exact consumer mirrors of `contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`; they are not independent E6 lifecycle authority.

E6 does not import E5 production modules, copy the E5 transition table, infer lifecycle from execution rows, or allocate/repair lifecycle revisions, predecessors, or projection IDs.

## Fail-closed behavior

Before a Position projection can advance the durable current/restart-authoritative index:

- unsupported lifecycle state raises `UNSUPPORTED_LIFECYCLE_STATE`;
- unsupported transition event raises `UNSUPPORTED_LIFECYCLE_EVENT`;
- unsupported projection kind raises `INVALID_LIFECYCLE_PROJECTION_KIND`;
- existing null-event rules remain enforced.

All prior E6-013 revision/predecessor/identity/broker-anchor/replay/conflict/re-attestation behavior is preserved.

## Deterministic definitions

Added `tests/storage/test_paper_runtime_lifecycle_vocabulary.py` defining:

- unsupported valid-hash lifecycle state rejection with no current projection creation;
- unsupported valid-hash transition event rejection with prior current projection unchanged;
- all eight shared lifecycle states accepted mechanically by the consumer validator;
- all thirteen shared transition events accepted mechanically without reproducing the E5 transition table;
- GENESIS/REATTESTATION null-event rules retained;
- TRANSITION non-null-event and unknown-kind fail-closed rules retained.

These are definitions only in this task.

## Verification

```text
local_verification = NOT_RUN
```

No separate exact-revision Product-Owner/PM-approved Local Runner action was authorized. No project code, unit test, migration, restart flow, Paper runtime, GitHub Actions/CI/hosted runner, GitHub-triggered compute, provider/private API, credential, or Computer Adapter workload was executed.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## Scope / release safety

- shared contracts / ADR modifications by E6: `NONE`
- E1-E5 or E7 production modifications: `NONE`
- provider/private API/network/credentials: `NONE`
- strategy lifecycle expansion: `NONE`
- PAPER/SHADOW/LIVE authority: `NONE`
- GitHub Actions/CI/workflows: `NONE`

This task does not claim Restart/persistence PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or PAPER/SHADOW/LIVE authorization.
