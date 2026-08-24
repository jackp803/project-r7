# E7 Current Task

- task_id: `E7-20260824-047`
- issued_at: `2026-08-24T16:24:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-position-lifecycle-ordering-contract-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A evidence PR #33, accepted Gate B in-memory chain through PR #55, accepted E6 durability blocker evidence PR #56

## Objective

Resolve only the E7-owned **canonical Position lifecycle projection ordering / durability semantic gap** exposed by `E6-20260824-010`.

Current accepted semantics split Position authority:

```text
E4 -> broker exposure truth / broker_state_observed_at
E5 -> lifecycle/risk interpretation / lifecycle_state
E6 -> persistence/recovery only
```

But accepted E5 lifecycle-only changes such as:

```text
OPEN_UNPROTECTED -> OPEN_PROTECTED
OPEN_* -> EXIT_REQUESTED
```

may change `lifecycle_state` without changing E4-owned `broker_state_observed_at`. E6 therefore cannot safely persist a single authoritative current Position projection across restart while also treating equal-time conflicting canonical payloads as fail-closed, unless E7 defines serialized lifecycle ordering/authority semantics.

Stop at contract/architecture decision, contract/ADR materialization if required, and exact E6 handoff. Do **not** implement E6 storage, E4/E5 production, full Paper E2E, provider/private APIs, approved-local execution, or PAPER/SHADOW/LIVE authorization.

## Accepted blocker evidence

```text
PR #56 merge = 649ae522b71f3992e48b81882662b6d7d0222324
E6 durability = BLOCKED / CONTRACT_OR_SEMANTIC_GAP
local executable verification = NOT_RUN
```

Independently inspect the blocker rather than assuming its diagnosis is correct.

At minimum inspect:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/README.md`, `contracts/SHARED_CONTRACTS_V1.md` Position/PositionAction semantics;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
- ADR-0005 and any lifecycle/recovery-relevant ADRs;
- current E5 `src/position/state_machine.py`, `protection_result.py`, `close.py`, protection producer and TradeResult lifecycle behavior;
- current E4 Position broker-truth surfaces read-only;
- accepted PR #55 integration definitions showing lifecycle projection;
- PR #56 blocker evidence;
- current E6 storage boundary/readme and `E6-20260824-010` requirements read-only.

## Required architecture decision

Classify the current shared semantics exactly as one of:

```text
BASELINE_SUFFICIENT_WITH_RULE_REFINEMENT
ADDITIVE_PROFILE_REQUIRED
BREAKING_CONTRACT_CHANGE_REQUIRED
BLOCKED / UNRESOLVED_ARCHITECTURE_CONFLICT
```

Do not add a field merely because it is convenient. Identify producer, consumer, ownership, serialization, compatibility, migration and replay consequences first.

The accepted solution must make the following deterministic without using E6 storage arrival order as domain authority:

```text
1. broker fact ordering
2. lifecycle interpretation ordering
3. construction of a current canonical/durable Position projection
4. stale lifecycle projection handling
5. equal-authority duplicate/idempotent handling
6. equal-order conflicting lifecycle payload handling
7. restart recovery of the exact authoritative state
```

### Required ownership constraints

Preserve:

- E4 remains authoritative for actual broker exposure/order/fill facts and `broker_state_observed_at` semantics;
- E5 remains authoritative for lifecycle/risk interpretation;
- E6 may persist/replay/project only according to shared rules and must not derive lifecycle from actions/fills/orders on restart;
- E7 owns the contract/versioning/release semantics.

Do not redefine SQLite row order, `persisted_at`, insertion sequence, or E6-local revision as E5 lifecycle authority.

### Candidate semantic shapes to evaluate, not assume

E7 may determine that a compatible solution requires, for example, an explicit serialized lifecycle observation/event identity, lifecycle observation timestamp, lifecycle revision/sequence, or a separately versioned lifecycle projection evidence profile. These are examples only; choose the minimal correct architecture.

If lifecycle ordering can instead be derived from already-canonical serialized E5 authority without changing contract meaning, document the exact deterministic rule and prove why it is not E6 reconstruction or arrival-order inference.

## Required durable/replay semantics

The resulting contract/rule must define at minimum:

- the canonical identity/key of a lifecycle projection/update;
- authoritative ordering material and who produces it;
- relation between lifecycle ordering and `broker_state_observed_at`;
- whether multiple lifecycle updates may legitimately share the same broker observation;
- idempotent replay semantics;
- stale update semantics;
- conflicting same-order authority semantics;
- behavior when lifecycle authority is missing/unknown/unsupported;
- how E6 recovers the current state without recomputation;
- how historical broker observations and lifecycle changes remain auditable;
- compatibility for existing historical Position objects that lack the new refinement, if an additive profile is chosen;
- whether current in-memory PR #55 behavior needs later E5/E4 producer adaptation or can remain valid unchanged.

Unknown/ambiguous lifecycle ordering must fail closed. Missing ordering authority must never be interpreted as a later/healthier/protected/closed state.

## Producer / consumer impact inventory

Record exact impacts for:

```text
E4 broker Position truth
E5 protection lifecycle result
E5 close lifecycle result
E5 TradeResult closure lifecycle
E6 persistence/current projection/restart
E7 integration/E2E/release evidence
```

If any E4/E5 production adaptation will be required after the contract decision, identify the exact next owner and bounded change. Do not implement it in this task.

If no E4/E5 adaptation is required and only E6 needs the accepted rule/profile, state that explicitly so PM can reissue the durability task.

## Contract / ADR materialization

If the decision changes or refines cross-module serialized semantics:

- update the appropriate E7-owned contract/profile registry;
- create/update an ADR when authority/order/replay semantics materially change;
- preserve `contracts-v0.1` compatibility rules honestly;
- do not disguise a breaking change as an additive profile;
- define exact version/profile identifiers if additive;
- define migration/legacy handling expectations for E6.

If no contract file change is necessary, persist a precise E7 architecture decision explaining why the baseline already contains sufficient authority and the exact rule E6 must follow.

## Required E7 test definitions / review evidence

This task is primarily STATIC CONTRACT / ARCHITECTURE work. Add contract/integration test definitions only where useful to express the ordering semantics, without running them.

At minimum the evidence must reason through deterministic cases for:

- same broker observation: OPEN_UNPROTECTED then valid OPEN_PROTECTED lifecycle change;
- same broker observation: valid later EXIT_REQUESTED lifecycle change;
- stale lifecycle update arriving after a newer lifecycle authority;
- exact replay of the same lifecycle authority;
- same lifecycle authority identity/order with changed lifecycle payload -> conflict;
- restart after multiple lifecycle-only changes returns the exact authoritative current lifecycle without E6 inference;
- broker exposure update and lifecycle update ordering remain independent but composable;
- unknown/missing lifecycle-order authority fails closed.

Definitions/evidence only. Do not execute project code.

## Release-gate reconciliation

`Restart/persistence preserves required state` remains `BLOCKED` until E6 implementation exists and later approved-local evidence passes.

`Paper E2E closes to TradeResult and persists audit` remains `BLOCKED`.

Do not convert any current `NOT_RUN` criterion to PASS.

If this task resolves the semantic gap, classify only:

```text
Position lifecycle durability contract/rule = RESOLVED STATIC
E6 durability implementation = NEXT DEPENDENCY / NOT YET MATERIALIZED
```

Gate B remains BLOCKED and PAPER remains unauthorized.

## Writable scope

E7-owned only:

- `contracts/**` if required;
- `docs/adr/**` if required;
- `docs/architecture/**` if required;
- E7-owned contract/integration test definitions if needed;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md` only for accurate static reconciliation;
- E7-specific `status/e7/**` evidence;
- `coordination/E7/STATUS.md` on the target branch.

Forbidden:

- E1-E6 production code;
- E6 migrations/storage implementation;
- provider/private API/network/credentials;
- GitHub Actions/CI/workflows;
- PAPER/SHADOW/LIVE authority changes.

## Executable verification

This task is **STATIC CONTRACT / ARCHITECTURE ONLY**.

Record:

```text
project_executable_verification = NOT_RUN
```

Do not request/run Local Runner, GitHub Actions/CI/hosted runners, GitHub-triggered compute, Computer Adapter, provider/private API, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- PR #56 blocker is independently confirmed or corrected;
- one explicit architecture classification is recorded;
- lifecycle projection ordering/authority/replay semantics are unambiguous enough for E6 durability without E6 domain inference;
- required contract/profile/ADR changes are materialized if needed;
- producer/consumer impacts and exact next owner are identified;
- release state remains truthful and no `NOT_RUN` becomes PASS;
- no E1-E6 production scope is crossed.

### BLOCKED

- a coherent lifecycle ordering model cannot be established without an unresolved product/authority conflict;
- persist exact conflicting requirements and escalate to PM/Product Owner;
- do not invent a local workaround.

## Completion / mailbox rule

Commit/push E7-owned contract/architecture/evidence/status to `agent/e7-gate-b-position-lifecycle-ordering-contract-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E7/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E6 implementation, full Paper E2E, approved-local verification, Gate C, PAPER, SHADOW or LIVE.