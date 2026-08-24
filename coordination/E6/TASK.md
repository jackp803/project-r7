# E6 Current Task

- task_id: `E6-20260824-015`
- issued_at: `2026-08-24T21:40:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-b-paper-runtime-durability-v2-20260824`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, `contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`, ADR-0007, ADR-0008, accepted E7 task `E7-20260824-050`, PR #60 merge `6141d93f5b80d1dc1a0e4231a3e453d09806bf40`, prior E6 durability task `E6-20260824-013`

## Objective

Remediate only the bounded lifecycle-vocabulary validation gap in the existing E6 Gate B durability branch so PM can re-review the complete E6 durability slice.

Do not redesign durability, lifecycle semantics, contracts, or release authority.

## Required baseline handling

Before editing:

- verify the authoritative main TASK task_id exactly matches `E6-20260824-015`;
- read latest `main` including PR #60 accepted contract/ADR;
- bring the accepted latest `main` contract state into `agent/e6-gate-b-paper-runtime-durability-v2-20260824` without modifying E7-owned contract/ADR meaning;
- preserve all accepted E6-013 durability implementation outside this remediation unless a directly related defect is required to satisfy the new contract.

## Required remediation

In E6-owned storage validation only:

1. enforce exact membership for restart-authoritative `lifecycle_state` using the eight values in `POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`;
2. enforce exact membership for `TRANSITION.lifecycle_event` using the thirteen values in that contract;
3. preserve `GENESIS` and `REATTESTATION` requirement `lifecycle_event = null`;
4. reject unsupported lifecycle state/event/kind before a payload can advance durable current/restart-authoritative Position state;
5. add deterministic E6 storage test definitions showing rejected unsupported vocabulary does not create/replace the current projection;
6. preserve all existing revision/predecessor/identity/broker-anchor/replay/conflict/re-attestation behavior from E6-013.

E6 may mirror the exact shared vocabulary as local validation constants implementing the accepted E7 contract. Those constants are not independent E6 authority.

## Explicit boundary

Do **not**:

- import E5 production modules to validate vocabulary;
- copy or evaluate the E5 `(previous_state, event) -> next_state` transition table;
- infer lifecycle state from OrderResult, Fill, PositionAction, TradeResult, or storage arrival order;
- allocate/repair lifecycle revisions, predecessor IDs, or projection IDs;
- modify `contracts/**`, `docs/adr/**`, or E1-E5/E7 production code;
- add provider/private API/network/credentials;
- add `.github/workflows/**` or GitHub CI/compute;
- enable or claim PAPER/SHADOW/LIVE authority.

If the accepted vocabulary contract still proves insufficient to implement this mechanically, stop with `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and exact evidence; do not guess.

## Required deterministic test definitions

At minimum define coverage for:

- unsupported `lifecycle_state` on an otherwise canonical valid-hash projection -> structured reject, no current projection advancement;
- unsupported `TRANSITION.lifecycle_event` after a valid predecessor -> structured reject, prior valid current projection unchanged;
- supported lifecycle states/events remain accepted under existing structural/order rules;
- GENESIS/REATTESTATION null-event rules remain enforced;
- existing E6 durability/storage/platform/registry test definitions remain compatible.

No PM or worker may convert unexecuted definitions into PASS.

## Writable scope

E6-owned only, preferred minimum:

- `src/storage/_runtime_validation.py`;
- `tests/storage/test_paper_runtime_durability.py` and/or `tests/storage/test_paper_runtime_conflict_and_time_ordering.py`;
- strictly necessary E6 durability docs/status evidence;
- `coordination/E6/STATUS.md` on the target branch.

Other existing E6 durability files may be touched only if strictly required by this remediation.

## Executable verification

Local-only. Unless a separate exact-revision Product-Owner/PM-approved local execution action exists, record:

```text
local_verification = NOT_RUN
```

with exact Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

No GitHub Actions/CI/hosted runner/GitHub-triggered compute may be used. `NOT_RUN != PASS`.

## Acceptance

### DONE

- unsupported shared lifecycle state/event vocabulary fails closed before durable current advancement;
- supported vocabulary behavior remains mechanically compatible with the accepted profile;
- E5 transition authority remains untouched;
- E6-013 durability behavior outside this remediation is preserved;
- deterministic regression test definitions are committed;
- no forbidden scope is crossed;
- executable evidence is either approved-local exact evidence or explicit `NOT_RUN` with commands;
- no Restart/persistence PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or PAPER/SHADOW/LIVE authorization is claimed.

### BLOCKED

If implementing the accepted vocabulary still requires undefined shared semantics or wider architecture change, record exact evidence and `next_owner = E7` and stop.

## Completion / mailbox rule

Commit/push the bounded remediation and evidence to `agent/e6-gate-b-paper-runtime-durability-v2-20260824`.

Write/push terminal `coordination/E6/STATUS.md` on that target branch with task_id `E6-20260824-015` and stop. Do not self-start E7 integration, approved-local verification, Paper E2E, Gate C, provider/private APIs, PAPER, SHADOW, or LIVE.