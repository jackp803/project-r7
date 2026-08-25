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

`test_paper_runtime_durability.py` preserves and updates the base durability definitions for:

- additive runtime migration coexistence with Registry data/schema, now including the additive lifecycle-execution-binding table;
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
- immutable TradeResult + exact funding-evidence binding + exact referenced entry/exit request/fill/authority graph;
- database close/reopen recovery for open partial-fill, ambiguous/reconciliation-required, and closed/funded/TradeResult graphs;
- exact current `position-lifecycle-execution-binding-v0.1` requirement for READY recovery;
- durable conflict recovery;
- bounded transaction rollback leaving no half-applied current projection;
- secret-like field rejection and absence of release-authority APIs.

`test_paper_runtime_binding_and_traderesult_completeness.py` defines the E6-20260824-017 repair regressions for:

- exact matching binding persistence/replay/recovery;
- missing binding -> not READY;
- binding projection/revision/interpreted-time/profile/scope/hash mismatch rejection;
- later PARTIALLY_FILLED/FILLED/CANCELED/EXPIRED/REJECTED evidence invalidating an older binding;
- new POSITION_EXIT / EMERGENCY_EXIT execution evidence invalidating an older binding;
- equal-time OrderResult and immutable Fill/OrderRequest identity conflicts;
- equal-broker-anchor E5 REATTESTATION plus a new matching binding restoring execution freshness mechanically;
- raw E4 Position freshness remaining a separate E5 re-attestation axis;
- entry-v0.1 OrderRequest/Fill evidence remaining outside the reduction-order binding scope with no trade-plan heuristic join;
- complete TradeResult referenced-object graph recovery;
- missing entry/exit OrderRequest, missing entry/exit Fill, missing PositionAction, and reference-lineage mismatch failing closed before durable TradeResult acceptance/READY recovery.

`test_paper_runtime_reference_remediation.py` defines the bounded E6-20260824-018 remediation regressions for:

- a legacy/direct-SQL TradeResult row with duplicate/shape-invalid referenced graph material never recovering `READY`;
- generic `TRADE_RESULT_REFERENCED_GRAPH_INVALID` downgrading a previously READY recovery to `INCOMPLETE`;
- referenced `PROTECT / PROTECTION_STOP` PositionAction requiring exact `protection-v0.1` parent/policy/symbol lineage;
- referenced `EXIT / POSITION_EXIT` and `EMERGENCY_EXIT / EMERGENCY_EXIT` PositionAction requiring exact `close-v0.1` parent/strategy/policy lineage;
- missing required PositionAction lineage recovering/persisting fail-closed as incomplete/invalid;
- mismatched required PositionAction lineage recovering as `CONFLICT`;
- the valid E6-017 complete closed graph remaining definition-compatible.

The E6-018 remediation does not alter the E6-017 lifecycle-execution-binding freshness definitions or E5 lifecycle semantics.

`test_paper_runtime_conflict_and_time_ordering.py` preserves focused definitions for:

- true additive migration from the Registry-only database to the current accepted migration inventory;
- declared lifecycle-projection ID corruption -> durable conflict;
- declared funding evidence ID corruption -> durable conflict;
- fractional-second OrderResult ordering without RFC3339 lexical-order assumptions;
- fractional-second newer raw Position observation -> `REATTESTATION_REQUIRED`.

## Gate C OperationalMode / Shadow durability definitions

`test_operational_mode_shadow.py` defines the bounded E6-20260825-022 credential-free storage regressions for:

- exact shared OperationalMode vocabulary `RESEARCH | PAPER | SHADOW | LIVE | PAUSED | LOCKED` as distinct durable values;
- `SHADOW` remaining operational mode state rather than StrategyLifecycleState;
- append-only/revisioned audited transition into SHADOW;
- no supported or SQL transition from a current non-LIVE mode into LIVE under the Gate C migration/surface;
- existing/legacy LIVE representation restoring distinctly but always as `LIVE_UNAUTHORIZED` on the Gate C surface;
- sanitized production-read-only OKX Shadow checkpoint identity and restart replay;
- restart requiring a newly accepted provider checkpoint before `shadow_planning_safe=true`;
- exact replay of a pre-restart checkpoint not masquerading as fresh provider evidence;
- missing/corrupt checkpoint recovery failing closed;
- Paper evidence never satisfying the Shadow provider-checkpoint requirement;
- credential/provider-presence-like fields and prohibited provider/account material being rejected rather than persisted;
- non-read-only permission, unknown required truth, unexpected exposure, pending orders, unreconciled fills, unhealthy market, or Demo classification never becoming an accepted Shadow checkpoint;
- additive/idempotent `0004_operational_mode_shadow.sql` behavior while retaining accepted Gate B data.

The Gate C storage surface does not perform provider/network/auth operations, derive E5 risk state, submit orders, mutate provider/account state, or authorize LIVE.

`tests/platform/test_paper_runtime_storage_surface.py` continues to define the supported Gate B `storage.runtime` public surface and rejects raw SQLite, provider-private, strategy-promotion, PAPER/SHADOW/LIVE and provider-submit capabilities.

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

Reason: Product Owner authorized credential-free approved-local verification for E6-20260825-022, but this ChatGPT GitHub session has no approved local runner/computer execution surface available. GitHub is not used as a substitute.

Never use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud project execution, provider/private APIs, or credentials for these verification suites.
