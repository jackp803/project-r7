# E6 Strategy Inbox / Registry / Persistence — Early Slice 2

> Owner: E6 Platform / Storage / Strategy Registry / Dashboard Engineer  
> Branch: `agent/e6-platform`  
> Contract baseline: `contracts-v0.1`  
> Phase: bounded executable skeleton; local verification remains `NOT_RUN`

## 1. Objective

Materialize enough E6 structure to receive a versioned StrategyDefinition, preserve compatibility/validation evidence, register immutable strategy versions, and persist the first research lifecycle states without treating unexecuted Slice 1 code as passing evidence.

Current integration target:

```text
StrategyDefinition intake
  -> E6 shared-envelope/security boundary
  -> E2 compatibility boundary
  -> DRAFT Registry record + compatibility evidence
  -> E3 BacktestResult / ValidationDecision evidence storage
  -> guarded lifecycle persistence
```

E6 does not implement Strategy DSL semantics, backtest statistics, exchange execution, risk decisions, or shared contract changes.

## 2. Authoritative semantics

E6 consumes:

- `contracts/SHARED_CONTRACTS_V1.md` (`contracts-v0.1`);
- `docs/adr/ADR-0001-canonical-contract-first-architecture.md`;
- `status/RELEASE_GATES.md`;
- E2 StrategyDefinition/runtime boundary;
- E3 BacktestResult and later ValidationDecision producer boundary.

The canonical identity remains:

```text
(strategy_id, strategy_version)
```

with immutable `content_hash` binding exact strategy content.

E2 and E3 branch implementations may be inspected for adapter planning, but branch/code existence is not PASS evidence. Their current Slice 1 handoffs report local verification `NOT_RUN`.

## 3. Technology choice

The early local persistence skeleton uses:

```text
Python stdlib
sqlite3
plain SQL migrations
unittest test definitions
```

Rationale:

- no additional framework/ORM dependency;
- works with the Python already used by E2/E3;
- simple local restart/migration testing;
- easy to replace behind `RegistryStore` later.

SQLite is an E6 implementation detail, not an E7 shared contract or permanent production database decision.

## 4. Intake boundary

`StrategyPlatformService.intake(...)` performs only E6-owned concerns before persistence:

- JSON/mapping intake;
- duplicate JSON-key rejection;
- required shared-envelope field presence;
- exact `schema_version == contracts-v0.1`;
- basic identity/runtime-compatibility envelope extraction;
- recursive secret-like key rejection;
- deterministic JSON persistence representation.

E6 deliberately does **not**:

- validate SMA/GT/LT/AND semantics;
- recompute E2 StrategyDefinition content hash;
- interpret Strategy rules;
- claim declared runtime compatibility is actual compatibility.

Those semantic checks belong behind `StrategyCompatibilityBoundary` and must be satisfied by E2.

The production-safe default boundary is `DeferredCompatibilityBoundary`, which emits:

```text
status = NOT_RUN
verification_kind = NOT_RUN
reason = E2_COMPATIBILITY_NOT_EXECUTED
```

Therefore an unwired E2 adapter cannot accidentally move a strategy out of DRAFT.

## 5. Registry model

### `strategy_versions`

Stores one immutable exact version:

```text
strategy_id
strategy_version
strategy_schema_version
content_hash
name
symbol
declared_runtime_family
declared_runtime_version
definition_json
upstream_created_at
registered_at
current_lifecycle_state
registry_revision
```

Guarantees:

1. `(strategy_id, strategy_version)` primary key.
2. same identity + same immutable content is idempotent.
3. same identity + conflicting hash/content fails closed.
4. database trigger prevents direct overwrite of immutable strategy fields.
5. current state is a read projection, not the only audit record.

### `compatibility_evidence`

Separates the compatibility judgment from how it was verified:

```text
status
verification_kind
checker
source_revision
environment
command
result_ref
reason_codes/details
```

This distinction is critical: `PASS` as a declaration/static result is not equivalent to an executed local PASS.

### `validation_evidence`

Stores separate canonical payloads for:

- `BACKTEST_RESULT`;
- `VALIDATION_DECISION`.

Each record binds to:

```text
strategy_id
strategy_version
strategy_content_hash
upstream_schema_version
upstream_object_id
producer
verification_status
verification_kind
source_revision/environment/command/result_ref
```

ValidationDecision additionally binds to its exact stored BacktestResult parent.

E6 preserves `FAIL`, `BLOCKED`, and `NOT_RUN`; it never normalizes them to PASS.

### `strategy_intake_receipts`

Stores accepted-intake audit metadata and payload hash without adding credentials or arbitrary error payload dumps.

### `lifecycle_transitions`

Append-only transition ledger containing:

```text
previous_state
new_state
changed_at
changed_by
reason_codes
primary_evidence_id
expected_registry_revision
resulting_registry_revision
```

Database triggers reject UPDATE and DELETE of transition history.

## 6. Early lifecycle subset

Although E7 defines the complete lifecycle, this migration/service intentionally materializes only:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

Service-exposed transitions are exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

No generic public transition API exists.

Not available in this slice:

```text
CANDIDATE -> PAPER
PAPER -> READY_FOR_APPROVAL
READY_FOR_APPROVAL -> APPROVED
APPROVED -> LIVE
LIVE -> DEGRADED
DEGRADED -> LIVE
```

A later E7-reviewed migration/service extension is required before those states can be persisted through this platform path.

## 7. Gate predicates

### DRAFT -> BACKTESTING

Requires latest E2 compatibility evidence with all of:

```text
status = PASS
verification_kind = LOCAL_EXECUTION
checker = E2-owned boundary
source_revision present
environment present
command present
result_ref present
```

A structurally valid StrategyDefinition or an E2 branch commit alone cannot satisfy this gate.

### BACKTESTING -> REJECTED

Requires an explicit actor and at least one reason code. Optional evidence, when supplied, must bind to the exact strategy version.

Rejected strategy versions remain persisted and queryable.

### BACKTESTING -> CANDIDATE

Requires:

1. exact registered strategy/version/content hash;
2. stored E3 BacktestResult bound to that exact content;
3. stored E3 ValidationDecision bound to that BacktestResult;
4. `ValidationDecision.decision = PASS`;
5. BacktestResult verification = `PASS + LOCAL_EXECUTION` with complete local evidence metadata;
6. ValidationDecision verification = `PASS + LOCAL_EXECUTION` with complete local evidence metadata.

Therefore these are insufficient by themselves:

```text
BacktestResult JSON validates
ValidationDecision contains PASS
E3 branch exists
static review passes
GitHub commit exists
```

## 8. Why there is no approval/LIVE path

This slice intentionally stops at `CANDIDATE`.

The service has no public method such as:

```text
approve(...)
go_live(...)
promote_to_live(...)
transition(... arbitrary state ...)
```

Approval and LIVE require later E3/E4/E5/E7 evidence, operational-mode controls, Product Owner authorization, and additional migrations/tests. Implementing those now would create a bypass surface before the necessary evidence exists.

## 9. Persistence / concurrency behavior

`SQLiteRegistryStore.append_transition(...)` uses an immediate transaction and checks:

- authoritative current state;
- expected `registry_revision`;
- exact next revision;
- one-row conditional projection update.

The transition audit insert and current-state projection update commit atomically.

A stale writer or race fails closed with `ConcurrencyConflict`.

## 10. Restart and migration

Migration:

```text
src/storage/migrations/0001_strategy_registry.sql
```

Test definitions cover:

- migration idempotence;
- immutable-content trigger;
- append-only lifecycle trigger;
- restart persistence;
- Registry reconstruction.

Known hardening item: complete intake currently performs StrategyVersion, compatibility evidence, and receipt as separate durable operations. A crash between these writes leaves a fail-closed DRAFT/missing-evidence condition rather than a false PASS, but a later revision should make complete intake audit persistence atomic.

## 11. Security / redaction

Strategy Inbox rejects common credential-like key names, including prefixed forms such as:

```text
pionex_api_key
broker_api_secret
session_token
account_password
```

Rejected secret-bearing raw payloads should not be persisted or logged merely for debugging.

No credential can satisfy compatibility, validation, approval, or LIVE gates.

## 12. Test status

Defined local commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Current result:

```text
NOT_RUN
```

Reason: this ChatGPT GitHub environment is not the Product-Owner-approved local execution environment.

Synthetic local-PASS fixtures in these tests exercise E6 gate behavior only; they are not evidence that E2/E3/Slice 1 passed.

No GitHub Actions, GitHub CI, hosted runner, GitHub-triggered runner, or GitHub project compute was used.
