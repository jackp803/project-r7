# E6 Registry / Persistence / Lifecycle Skeleton

> Owner: E6 Platform / Storage / Strategy Registry / Dashboard Engineer  
> Phase: design / skeleton only  
> Baseline: `contracts-v0.1` on `main` at `ba2affa62c89d58bb9ffac054963579e434896e1`  
> Scope boundary: do not implement Slice 2 orchestration until E2 `StrategyDefinition` and E3 `BacktestResult` / `ValidationDecision` executable representations exist.

## 1. Objective

Prepare the minimum E6 platform shape needed for later Slice 2 integration without inventing E2 strategy semantics, E3 validation semantics, E5 risk policy, E4 execution behavior, or E7 cross-module contracts.

This skeleton covers only:

- Strategy Registry responsibilities;
- persistence responsibilities;
- strategy lifecycle persistence and transition enforcement;
- evidence/audit attachment points required for later integration.

It intentionally does **not** implement:

- Strategy Inbox orchestration;
- E2 parser/runtime calls;
- E3 backtest/validation calls;
- database migrations;
- ORM or database-engine selection;
- dashboard/UI;
- promotion-policy evaluation beyond the current E7 transition contract;
- paper/shadow/live operational control;
- approvals beyond reserving the contract attachment point;
- any live-trading path.

## 2. Authoritative inputs

E6 consumes, but does not redefine:

- `contracts/SHARED_CONTRACTS_V1.md` (`contracts-v0.1`);
- `docs/adr/ADR-0001-canonical-contract-first-architecture.md`;
- `status/RELEASE_GATES.md`;
- E2's future executable `StrategyDefinition` representation;
- E3's future executable `BacktestResult` and `ValidationDecision` representations.

The canonical strategy identity is:

```text
(strategy_id, strategy_version)
```

`content_hash` binds the immutable serialized strategy content to that identity.

## 3. Design invariants

### 3.1 Immutable strategy-version identity

The Registry must enforce these rules:

1. `(strategy_id, strategy_version)` is unique.
2. Re-registering the same identity with the same `content_hash` is idempotent.
3. Re-registering the same identity with a different `content_hash` is a conflict and must fail closed.
4. Once validation evidence is attached to a strategy version, material strategy content cannot be replaced in place.
5. A material strategy change requires a new `strategy_version`.
6. Rejected and retired versions remain queryable and auditable.

The Registry must never use display name as identity.

### 3.2 Evidence is version-bound

Every evidence attachment must identify the exact:

```text
strategy_id
strategy_version
```

Where the upstream contract exposes it, E6 should also validate the expected `strategy_content_hash` before accepting the evidence reference.

A backtest/validation result for one strategy version must never be displayed or used as evidence for another version.

### 3.3 Lifecycle is backend-authoritative

The front end may request a transition later, but only the backend lifecycle service may persist it.

A UI label, file move, query parameter, or client-supplied current state is never authoritative.

### 3.4 Lifecycle history is append-only

A lifecycle transition is an audit event, not an overwrite-only status mutation.

For every transition preserve at minimum:

- exact strategy identity;
- previous state;
- new state;
- timestamp;
- actor/source;
- reason/evidence reference;
- request/correlation identity when introduced.

A current-state projection may exist for efficient reads, but transition history remains the auditable record.

### 3.5 Fail closed

Unknown schema versions, conflicting content hashes, missing required evidence references, illegal lifecycle transitions, ambiguous current state, or persistence failure must not be interpreted as permission to promote a strategy.

## 4. Registry logical model

The following are **internal E6 logical records**, not new shared contracts. Field names may change before executable implementation as long as cross-module semantics remain unchanged.

### 4.1 StrategyVersionRecord

Purpose: immutable registry identity and minimal metadata for one strategy version.

Logical fields:

```text
strategy_id
strategy_version
strategy_schema_version
content_hash
name                    # projection only when supplied by canonical E2 object
symbol                  # projection only when supplied by canonical E2 object
created_at              # canonical upstream creation time
registered_at           # E6 persistence time
current_lifecycle_state # read projection; not the sole audit record
registry_revision       # internal optimistic-concurrency token
```

The executable representation must be derived from the actual E2 `StrategyDefinition`; E6 must not create a competing strategy DTO.

### 4.2 LifecycleTransitionRecord

Purpose: append-only state-change audit.

Logical fields:

```text
transition_id
strategy_id
strategy_version
previous_state
new_state
changed_at
changed_by
reason_codes / reason
primary_evidence_ref    # optional until a transition requires evidence
approval_record_id      # optional / required only where E7 policy requires it
registry_revision
```

### 4.3 EvidenceReferenceRecord

Purpose: bind external validation/research evidence to the exact strategy version without E6 redefining the evidence payload.

Logical fields:

```text
evidence_ref_id
strategy_id
strategy_version
evidence_type            # e.g. contract type name, not an E6 validity judgment
upstream_object_id
upstream_schema_version
upstream_content_hash     # when provided/meaningful
recorded_at
source_ref                # local artifact/object reference when architecture later defines it
```

E6 may persist the canonical upstream payload later, but the stored representation must preserve its original schema/version and must not normalize away `NOT_RUN`, `BLOCKED`, or failure evidence.

### 4.4 Approval attachment point

`ApprovalRecord` is already a shared E7 contract. E6 will later persist immutable approval records and bind them to lifecycle or operational-mode transitions.

No approval table/migration is materialized in this skeleton.

## 5. Lifecycle state machine

E6 will implement exactly the E7 baseline states:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
PAPER
READY_FOR_APPROVAL
APPROVED
LIVE
DEGRADED
RETIRED
```

Baseline legal transitions:

```text
DRAFT              -> BACKTESTING | RETIRED
BACKTESTING        -> REJECTED | CANDIDATE
CANDIDATE          -> PAPER | REJECTED | RETIRED
PAPER              -> READY_FOR_APPROVAL | REJECTED | RETIRED
READY_FOR_APPROVAL -> APPROVED | REJECTED | RETIRED
APPROVED           -> LIVE | RETIRED
LIVE               -> DEGRADED | RETIRED
DEGRADED           -> LIVE | RETIRED
```

Hard behavior:

- `BACKTESTING -> LIVE` is impossible.
- rejected strategy versions are retained.
- `READY_FOR_APPROVAL -> APPROVED` must later validate the E7-defined approval/evidence prerequisites.
- `APPROVED -> LIVE` must later validate runtime/risk/execution release conditions.
- `DEGRADED -> LIVE` requires explicit authorized resumption and is never signal-driven.

For this skeleton, only the static transition graph is considered stable. Evidence predicates are intentionally deferred until E2/E3 executable contracts and the relevant E7 Slice 2 gate are available.

## 6. Proposed service boundaries

These are conceptual E6 ports, not executable shared interfaces yet.

### StrategyRegistry

Responsibilities:

- register exact strategy identity/version metadata;
- enforce identity/content-hash uniqueness;
- return current registry projection;
- list historical/rejected/retired versions;
- never mutate strategy semantics.

Conceptual operations:

```text
register(strategy_definition)
get(strategy_id, strategy_version)
list_versions(strategy_id)
attach_evidence(evidence_object_or_reference)
```

The actual function signatures must consume the future E2/E3 executable contract representations or adapters approved by E7.

### LifecycleService

Responsibilities:

- load authoritative current state from persistence;
- validate requested edge against the E7 state graph;
- later evaluate required evidence/approval predicates;
- append transition audit record;
- atomically update current-state projection;
- reject stale/concurrent transitions.

Conceptual operation:

```text
transition(strategy_identity, expected_current_state, requested_state, actor, evidence_refs)
```

### RegistryStore

Responsibilities:

- durable storage for registry identity/projection;
- uniqueness and optimistic-concurrency guarantees;
- transactional write of transition + current projection;
- restart-safe reconstruction.

Database technology is intentionally deferred.

## 7. Persistence behavior to preserve when implementation starts

The first real persistence implementation should support:

1. unique `(strategy_id, strategy_version)` constraint;
2. immutable content-hash conflict rejection;
3. append-only lifecycle transition history;
4. transactionally consistent current-state projection;
5. evidence references bound to exact strategy version;
6. rejected/retired history retention;
7. restart recovery of registry state;
8. optimistic concurrency or equivalent stale-write rejection;
9. schema migration/version tracking;
10. rollback on partial transition/audit failure.

No migration files are created yet because the executable language/runtime, DB choice, and final E2/E3 object representations are not yet materialized.

## 8. Performance/result separation

When E6 later stores result views, Backtest, Paper/Forward, Shadow, and Live evidence/results must remain separately typed/labeled.

This skeleton does not define a performance schema and must not merge these result domains into one aggregate record.

## 9. Security / redaction

- No real API key, API secret, token, password, private key, live `.env`, or credential may enter Registry metadata, evidence references, audit records, fixtures, examples, logs, screenshots, or UI output.
- Strategy content must remain declarative and secret-free according to the E2/E7 contract.
- Future payload persistence must preserve redaction boundaries rather than logging raw arbitrary objects on errors.
- Credential presence must never imply approval or LIVE eligibility.

## 10. Deferred decisions

The following remain intentionally unresolved:

- concrete programming language/runtime for E6 platform code;
- SQLite/PostgreSQL/other database choice;
- ORM/query layer;
- migration framework;
- whether canonical upstream payloads are stored inline or by content-addressed reference;
- executable DTO/adapters for E2 and E3 contracts;
- Slice 2 orchestration API shape;
- approval service implementation;
- operational-mode implementation;
- dashboard technology.

These should be decided only when the consuming/producing executable contracts and local runtime are available.

## 11. Slice 2 entry conditions

E6 may move from skeleton to implementation when E7 integration confirms at least:

1. E2 has an executable `StrategyDefinition` representation conforming to `contracts-v0.1`;
2. E2 exposes the runtime-compatible strategy identity/content hash needed by E3/E6;
3. E3 has an executable `BacktestResult` representation conforming to `contracts-v0.1`;
4. E3 has the Slice 2 `ValidationDecision` representation/policy boundary needed for promotion;
5. E7 confirms any additive contract changes and Slice 2 evidence expectations.

Then the intended integration path is:

```text
Strategy Inbox
  -> E2 compatibility/validation
  -> E3 backtest/validation
  -> Validation Evidence
  -> E6 Strategy Registry
```

## 12. Verification status

No project code, migration, database, or executable test is introduced by this document.

Current result:

```text
Design review: DOCUMENTED
Executable verification: NOT_RUN
Reason: skeleton contains no executable E6 implementation yet
```

When implementation begins, all DB migration, Registry, lifecycle, restart, UI/backend, and integration tests must run locally only. GitHub Actions/CI/hosted runners remain forbidden.
