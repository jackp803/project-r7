# E6 Platform Status

> Owner: E6 Platform / Storage / Strategy Registry / Dashboard Engineer  
> Branch: `agent/e6-platform`  
> Contract baseline: `contracts-v0.1` / E7 Slice 0 merge `ba2affa62c89d58bb9ffac054963579e434896e1`

## Current phase

```text
Strategy Registry models/service        IMPLEMENTED_SKELETON / NOT_RUN
SQLite persistence + migration 0001     IMPLEMENTED_SKELETON / NOT_RUN
Strategy Inbox intake                   IMPLEMENTED_SKELETON / NOT_RUN
Schema envelope boundary                IMPLEMENTED_SKELETON / NOT_RUN
Actual E2 runtime compatibility adapter DEFERRED / NOT_RUN
BacktestResult evidence storage         IMPLEMENTED_SKELETON / NOT_RUN
ValidationDecision evidence storage     IMPLEMENTED_SKELETON / producer pending
DRAFT -> BACKTESTING                    IMPLEMENTED_GATE / NOT_RUN
BACKTESTING -> REJECTED                 IMPLEMENTED_GATE / NOT_RUN
BACKTESTING -> CANDIDATE                IMPLEMENTED_GATE / NOT_RUN
CANDIDATE -> PAPER/APPROVED/LIVE        NOT_IMPLEMENTED / BLOCKED
Dashboard/UI                            NOT_STARTED
```

## Critical interpretation rule

Code existence, a GitHub branch, a contract-shaped payload, or a `PASS` string is not executable evidence.

Current E2 and E3 Slice 1 handoffs explicitly report local verification as `NOT_RUN`. E6 therefore does not record any real E2/E3 PASS in repository state and does not claim Gate A/Slice 1 PASS.

Synthetic PASS fixtures in E6 tests exist only to exercise E6 gate logic and are not project evidence.

## Implemented structure

### Strategy Inbox / Registry

- accepts mapping/JSON StrategyDefinition intake;
- requires shared schema `contracts-v0.1` at the E6 envelope boundary;
- rejects duplicate JSON keys;
- rejects common secret-like fields before persistence;
- registers exact immutable `(strategy_id, strategy_version)` identity;
- same identity/same content is idempotent;
- same identity/conflicting content fails closed;
- stores current lifecycle projection plus append-only audit history.

E6 does not validate Strategy DSL semantics. The actual E2 compatibility/runtime validator remains behind `StrategyCompatibilityBoundary`.

The production-safe default boundary returns:

```text
status = NOT_RUN
verification_kind = NOT_RUN
```

so an unwired E2 adapter cannot accidentally become permission to advance lifecycle.

### Evidence storage

E6 stores separately:

- E2 compatibility evidence;
- E3 BacktestResult evidence;
- E3 ValidationDecision evidence;
- verification status/kind;
- source revision;
- local environment;
- local command;
- result reference.

A BacktestResult remains evidence data, not a promotion instruction.

### Lifecycle scope

Only these service transitions exist in this slice:

```text
DRAFT -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

`DRAFT -> BACKTESTING` requires explicit E2 local-execution PASS metadata.

`BACKTESTING -> CANDIDATE` requires:

1. stored exact-version BacktestResult;
2. stored E3 ValidationDecision bound to that BacktestResult;
3. `ValidationDecision.decision = PASS`;
4. local-execution PASS metadata for both stored evidence records;
5. exact strategy identity/content-hash match.

No service path exists for approval, PAPER, LIVE, degraded recovery, operational LIVE mode, or Product Owner authorization capture.

## Persistence

Current local-first implementation uses Python stdlib `sqlite3` plus plain SQL migration:

- `src/storage/migrations/0001_strategy_registry.sql`

Migration 0001 intentionally permits only:

```text
DRAFT | BACKTESTING | REJECTED | CANDIDATE
```

Database triggers prevent immutable strategy-content updates and lifecycle-history update/delete.

This SQLite choice is an E6 implementation detail for the early local MVP, not a shared contract or permanent production-database decision.

## Local verification

Result: `NOT_RUN`.

Reason: this ChatGPT GitHub environment is not the Product-Owner-approved local execution environment. No project code was executed here.

Required local commands from repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

After E1/E2/E3 reviewed revisions are assembled in an E7 local integration checkout, E7 must separately run the Slice 1 integration command/evidence before any real project PASS is attached to E6 lifecycle records.

## Security

- no real API keys, secrets, tokens, passwords, private keys, live `.env`, or credentials were added;
- Strategy Inbox rejects secret-like keys before storing accepted payloads;
- raw rejected secret-bearing payloads are not intentionally persisted;
- credentials never count as compatibility, validation, approval, or LIVE evidence.

## Restart / migration concerns

- migration/restart behavior is test-defined but remains `NOT_RUN`;
- intake registration, compatibility-evidence write, and receipt write are separate durable operations in this skeleton; a crash between them leaves a fail-closed DRAFT with missing evidence rather than an implicit PASS, but later hardening should make the complete intake audit transaction atomic;
- migration 0001 deliberately requires a later migration before PAPER/approval/LIVE states can exist;
- changing from SQLite later requires an E6 persistence adapter/migration plan without changing E7 shared semantics.

## Next integration conditions

1. E7 accepts the corrected E2 Slice 1 boundary and local E2 evidence exists.
2. E3 Slice 1/ValidationDecision producer is reviewed and local evidence exists.
3. E6 local Registry/migration tests run and pass.
4. E7 integrates the research slice and decides when real evidence may drive `BACKTESTING -> CANDIDATE`.

Until then, E6 can store `NOT_RUN/BLOCKED/FAIL` evidence safely but cannot manufacture promotion authority.
