# E7 Current Task

- task_id: `E7-20260824-050`
- issued_at: `2026-08-24T21:24:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-lifecycle-event-vocabulary-contract-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, ADR-0007, accepted PR #57/#58, PM review of E6-20260824-013

## Objective

Resolve only the shared-contract ambiguity blocking PM acceptance of the E6 Gate B durable Paper runtime implementation.

The specific boundary is restart-authoritative validation of `position-lifecycle-projection-v0.1` lifecycle vocabulary:

```text
E5 produces authoritative lifecycle interpretation
E6 validates/persists/replays it mechanically
```

The current profile says unsupported lifecycle state/event/kind is not restart-authoritative. Shared lifecycle states are enumerated in `contracts/SHARED_CONTRACTS_V1.md`, but the profile refers to the exact canonical E5 `PositionEvent` without exhaustively materializing the supported event vocabulary as a shared consumer contract. E6 must not invent that vocabulary, import E5 transition logic, or silently accept arbitrary unknown events as restart-authoritative.

Determine and materialize the minimum authoritative contract rule that lets E6 fail closed on unsupported lifecycle vocabulary while preserving E5 ownership of transition semantics.

## Required inspection

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `contracts/README.md`;
- `contracts/SHARED_CONTRACTS_V1.md`;
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`;
- `docs/adr/ADR-0007-position-lifecycle-projection-ordering.md`;
- current E5 `src/position/state_machine.py` and `src/position/lifecycle_projection.py` read-only;
- E6-013 branch `src/storage/_runtime_validation.py`, tests, handoff and terminal STATUS read-only;
- `coordination/E6/TASK.md` and E6-013 terminal branch STATUS;
- `status/RELEASE_GATES.md`, `status/INTEGRATION_STATUS.md`;
- GitHub Issue #59 as prior PM defect evidence only. PM has reclassified that initial bounded-bug diagnosis as superseded pending this E7 contract review; do not treat Issue #59 ownership/classification as authoritative.

## Required decision

Independently determine whether the existing accepted contract surface already provides sufficient, stable authority for E6 to validate lifecycle state/event vocabulary without importing or duplicating E5 implementation semantics.

### If existing contract is sufficient

Document the exact authoritative source/rule E6 must use, including:

- supported `lifecycle_state` vocabulary;
- supported `lifecycle_event` vocabulary for `TRANSITION`;
- `GENESIS` / `REATTESTATION` null-event rule;
- unknown/unsupported value fail-closed behavior;
- confirmation that E6 does **not** evaluate the full `(previous_state, event) -> next_state` transition table.

Do not change schema/profile versions merely for documentation if the existing baseline is already sufficient.

### If existing contract is insufficient

Materialize the smallest additive E7-owned contract/profile clarification needed so consumers can validate vocabulary deterministically. Prefer clarification under unchanged:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

unless a version change is genuinely required by compatibility semantics.

At minimum define an exhaustive supported serialized `PositionEvent` vocabulary or another equally explicit shared registry/reference rule. Unknown future values must fail closed until a later accepted version/profile explicitly supports them.

Do not move transition authority to E6. E5 remains responsible for producing valid lifecycle transitions and for state-machine semantics.

## E6 follow-up contract

Your output must make the E6 remediation mechanically bounded. E6 should be able to validate declared vocabulary/profile compatibility without:

- importing E5 production modules;
- replaying the E5 transition table;
- inferring lifecycle state from OrderResult/Fill/PositionAction;
- allocating lifecycle revisions/IDs;
- inventing a private E6 enum.

If the correct resolution requires more than a bounded additive contract/ADR clarification, stop with exact blocker evidence rather than broadening scope.

## Writable scope

E7-owned only:

- `contracts/**` only as strictly required for the decision;
- `docs/adr/**` only if the accepted architecture meaning must be clarified/versioned;
- `status/e7/**`;
- `status/RELEASE_GATES.md` and `status/INTEGRATION_STATUS.md` only for conservative reconciliation;
- `contracts/README.md` if registry documentation changes;
- `coordination/E7/STATUS.md` on the target branch.

Forbidden:

- E1-E6 production code/tests;
- E6 branch edits;
- provider/private API/network/credentials;
- strategy lifecycle promotion;
- `.github/workflows/**` or GitHub CI/compute;
- PAPER/SHADOW/LIVE authorization;
- changing E5 transition semantics unless a new blocker proves the existing E5 implementation conflicts with the accepted shared contract.

## Verification

This is static contract/architecture review only. Do not execute project code/tests.

Record:

```text
project_executable_verification = NOT_RUN
```

No GitHub Actions/CI/hosted runner/GitHub-triggered compute may be used. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- E7 gives an explicit authoritative answer for supported lifecycle vocabulary at the durable E5 -> E6 boundary;
- E6 can distinguish supported vs unsupported `lifecycle_state` / `lifecycle_event` without importing E5 production semantics or inventing an E6-private contract;
- unknown values fail closed;
- E5 retains transition/lifecycle authority;
- revision/predecessor/identity/broker-anchor semantics from PR #57 remain unchanged unless explicitly justified;
- any contract/profile/ADR change is minimal, versioned/registered as required, and compatible with `contracts-v0.1` unless a justified version decision says otherwise;
- release gates remain conservative; no executable `NOT_RUN` criterion becomes PASS;
- Gate B remains BLOCKED and PAPER/SHADOW/LIVE remain unauthorized.

### BLOCKED

If the existing E5 lifecycle model itself cannot be represented by a stable shared vocabulary without a wider architecture change, record the exact conflict and stop. Do not guess or edit E1-E6 production code.

## Completion / mailbox rule

Commit/push bounded contract/ADR/status evidence to `agent/e7-gate-b-lifecycle-event-vocabulary-contract-20260824`.

Update `coordination/E7/STATUS.md` on that target branch with terminal `DONE`, `PARTIAL`, or `BLOCKED`, including exact reviewed revisions and `project_executable_verification = NOT_RUN`.

Then stop. Do not self-start E6 remediation, Paper E2E integration, approved-local verification, Gate C, PAPER, SHADOW, LIVE, provider/private APIs, or another task.