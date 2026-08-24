# E6 Persistence / Migration Tests

These test definitions are executable in an approved local checkout. They have **not** been run by this GPT session.

Raw SQLite mechanics used by storage-mechanics tests are imported explicitly from `storage._sqlite_registry`; those helpers are internal/test-only and are not the supported production authority surface.

## Early Registry coverage

`test_public_persistence_boundary.py`, `test_registry_persistence.py`, and `test_lifecycle_evidence_authority.py` preserve the accepted early Slice 2 definitions for:

- public Registry storage authority boundary;
- migration/idempotence/restart behavior;
- immutable StrategyVersion content;
- exact early lifecycle edges `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`;
- SQL/Python lifecycle guards;
- durable E2/E3 evidence authority and canonical binding;
- fail-closed invalid/skipped transitions;
- `DRAFT / registry_revision 0` initial projection;
- append-only lifecycle history and transaction/concurrency behavior.

The Gate B Paper durability slice is additive and does not replace or expand these Registry lifecycle semantics.

## Gate B Paper runtime durability definitions

`test_paper_runtime_durability.py` defines:

- additive runtime migration coexistence with Registry data/schema;
- exact canonical round-trip for RiskDecision, ApprovedTradePlan, PositionAction, OrderRequest and Fill;
- immutable same-ID replay/conflict behavior;
- `position-lifecycle-projection-v0.1` GENESIS / TRANSITION / REATTESTATION persistence;
- contiguous lifecycle revision/predecessor/current-index behavior;
- gap, stale branch, predecessor mismatch and broker-anchor regression failure;
- newer raw broker Position truth requiring E5 re-attestation without synthetic lifecycle projection;
- legacy Position never becoming restart-authoritative by row order;
- append-only OrderResult observations and non-regressing current index;
- equal-time OrderResult conflict;
- funding replay/identity/lineage conflict behavior;
- immutable TradeResult + exact funding-evidence binding;
- database close/reopen recovery for open partial-fill, ambiguous/reconciliation-required, and closed/funded/TradeResult graphs;
- durable conflict recovery;
- bounded transaction rollback leaving no half-applied current projection;
- secret-like field rejection and absence of release-authority APIs.

`test_paper_runtime_conflict_and_time_ordering.py` adds focused definitions for:

- true `0001_strategy_registry.sql -> 0002_paper_runtime_durability.sql` additive migration;
- declared lifecycle-projection ID corruption -> durable conflict;
- declared funding evidence ID corruption -> durable conflict;
- fractional-second OrderResult ordering without RFC3339 lexical-order assumptions;
- fractional-second newer raw Position observation -> `REATTESTATION_REQUIRED`.

`tests/platform/test_paper_runtime_storage_surface.py` defines the supported `storage.runtime` public surface and rejects raw SQLite, provider-private, strategy-promotion, PAPER/SHADOW/LIVE and provider-submit capabilities.

Synthetic fixtures are deterministic test doubles only; they are **not** project executable PASS evidence.

## Local-only commands

From repository root on the Product-Owner-approved Windows environment:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Current result:

```text
NOT_RUN
```

Reason: this ChatGPT GitHub environment is not an explicitly approved local execution environment for project code.

Never use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud project execution, provider/private APIs, or credentials for these verification suites.
