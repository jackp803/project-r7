# Handoff — E6 Gate B Paper Runtime Durability

**From:** E6 / Platform / Storage / Strategy Registry / Dashboard Engineer  
**To:** E7 / Project Manager review queue  
**Branch:** `agent/e6-gate-b-paper-runtime-durability-v2-20260824`  
**Commit(s):** source/tests/docs head `95679067132d8fa3933b8534983e6d975d0d68ff`  
**Date:** 2026-08-24  
**Task:** `E6-20260824-013`  
**Disposition:** `DONE / STATIC IMPLEMENTATION MATERIALIZED / EXECUTABLE NOT_RUN`

### 1. Objective

Implement only the E6-owned durable Gate B Paper runtime persistence/restart/audit slice after the accepted `position-lifecycle-projection-v0.1` contract and E5 producer resolved PR #56's lifecycle-ordering blocker.

The implemented boundary is:

```text
already-canonical E4/E5 runtime payloads
+ E5 profiled Position lifecycle projections
-> E6 SQLite append-only runtime journal/current indexes
-> close/reopen
-> exact stored-payload recovery + fail-closed diagnostics
```

No runtime scheduler, E4/E5 domain behavior, provider/private API, dashboard expansion, strategy promotion or release authority is added.

### 2. What changed

#### Additive runtime schema

Added:

```text
src/storage/migrations/0002_paper_runtime_durability.sql
```

The migration is additive to the existing early Registry schema and creates append-only/immutable storage for:

- RiskDecision;
- ApprovedTradePlan;
- PositionAction;
- OrderRequest;
- Fill;
- `position-lifecycle-projection-v0.1` Position projection history + mechanical current pointer;
- raw/legacy Position broker-observation audit history;
- OrderResult observation history + mechanical current pointer;
- FundingAllocationEvidence + later duplicate-observation metadata;
- immutable TradeResult;
- sanitized conflict audit metadata.

Existing `0001_strategy_registry.sql` is unchanged.

#### Public storage surface

Added the explicit safe submodule surface:

```python
from storage.runtime import open_paper_runtime_journal
```

It returns `PaperRuntimeJournal`, not a SQLite connection or raw writer. Existing top-level `storage.__all__ == ["open_sqlite_platform"]` remains unchanged for the accepted Registry public boundary.

#### Exact canonical payload preservation

The journal stores canonical JSON plus payload SHA-256 and E6-owned lookup/order metadata. Recovery returns the exact stored JSON payload; it does not instantiate E4/E5 implementation classes or reconstruct financial/runtime truth.

Binary floats, secret-like fields and explicit provider-native fields are rejected from the supported canonical runtime journal surface.

#### Immutable/idempotent runtime facts

For RiskDecision, ApprovedTradePlan, PositionAction, OrderRequest and Fill:

```text
same canonical ID + identical canonical payload -> idempotent
same canonical ID + changed canonical payload -> durable conflict / fail closed
```

OrderRequest additionally keeps one `client_order_id` bound to one durable request. Fill lineage is checked mechanically against its durable request without generating broker facts.

#### Position lifecycle persistence

E6 consumes the exact E5-produced profile material:

```text
lifecycle_projection_id
lifecycle_revision
previous_lifecycle_projection_id
lifecycle_projection_kind
lifecycle_event
lifecycle_interpreted_at
lifecycle_source_broker_state_observed_at
```

Current Position advancement is mechanical only:

```text
GENESIS revision 0
-> contiguous revision + 1
-> exact predecessor ID
-> nondecreasing broker anchor
-> no equal-anchor E4 broker-fact conflict
```

E6 never calls E5 state transitions on persistence or restart and never allocates/repairs lifecycle revisions or IDs.

Gap, predecessor mismatch, same-revision conflict, projection-ID corruption and broker-anchor regression fail closed. Exact stale historical replay is idempotent and cannot replace the current projection.

A newer raw E4 broker observation beyond the latest E5 projection anchor is preserved separately and recovery reports:

```text
REATTESTATION_REQUIRED
```

The old lifecycle state is not copied onto newer broker facts. Legacy unprofiled Position observations are never made restart-authoritative by row/insertion order.

RFC3339 times are retained unchanged in canonical payload JSON. E6 uses a separate fixed-width UTC storage ordering key for Position/OrderResult indexes so fractional-second formatting cannot accidentally alter ordering semantics.

#### OrderResult observation history

OrderResult is append-only by request + normalized observation instant. Later observations may advance the mechanical current pointer; stale history remains auditable. Equal-time changed payload fails closed. UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED remain exact after restart.

#### Funding evidence

The accepted `funding-allocation-v0.1` lineage key is enforced. Same financial allocation identity is idempotent even when later equivalent delivery has a newer `calculated_at`; the first canonical funding object remains immutable and the later observation can be represented only as audit metadata.

Different funding IDs for the same exact lineage key conflict and never use last-write-wins. Declared funding ID that does not match identity material is treated as durable corruption/conflict.

#### TradeResult

TradeResult is immutable. Persistence requires the exact durable ApprovedTradePlan and FundingAllocationEvidence binding and validates exact plan/position/symbol/interval/status/cost relationships. Current storage allows only one non-conflicting final result for the `(trade_plan_id, position_id)` closed lineage.

Recovery with a CLOSED Position but missing funding/result is `INCOMPLETE`; a result with no CLOSED authoritative projection is also not READY.

#### Recovery statuses

`PaperRuntimeRecovery` is E6-local and is not a shared DTO. It can report:

```text
READY
REATTESTATION_REQUIRED
RECONCILIATION_REQUIRED
INCOMPLETE
CONFLICT
```

These are storage/recovery diagnostics only; none create E5 lifecycle or E7 release authority.

### 3. Files changed

```text
src/storage/migrations/0002_paper_runtime_durability.sql
src/storage/runtime_models.py
src/storage/_runtime_validation.py
src/storage/_paper_runtime.py
src/storage/runtime.py
tests/storage/test_paper_runtime_durability.py
tests/storage/test_paper_runtime_conflict_and_time_ordering.py
tests/storage/README.md
tests/platform/test_paper_runtime_storage_surface.py
docs/platform/E6_GATE_B_PAPER_RUNTIME_DURABILITY.md
status/E6_GATE_B_PAPER_RUNTIME_DURABILITY_20260824.md
status/E6_STATUS.md
coordination/E6/STATUS.md
```

The last two status paths are written after this handoff commit.

### 4. Contracts consumed

- `contracts-v0.1` / `contracts/SHARED_CONTRACTS_V1.md`
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`
- `position-lifecycle-projection-v0.1`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `close-v0.1`
- `trade-result-v0.1`
- `linear-base-asset-pnl-v0.1`
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`
- `funding-allocation-v0.1`
- ADR-0005, ADR-0006, ADR-0007

### 5. Contracts produced or changed

```text
NONE
```

No shared field, enum, lifecycle meaning, authority meaning, DTO or profile is introduced by E6.

### 6. Local verification

Result:

```text
NOT_RUN
```

Reason: no separate exact-revision Product-Owner/PM-approved Local Runner action was authorized for this task. This GitHub/ChatGPT environment was used only for source/test-definition/document/status work.

Required future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

No PASS/test count is claimed.

### 7. Known limitations

- Implementation has only static/source review in this task; executable migration/restart/test behavior is `NOT_RUN`.
- The runtime journal is persistence/recovery only. It does not run the Paper runtime or orchestrate producers.
- Legacy unprofiled Position objects are historical/raw evidence only and require E5 GENESIS production before becoming restart-authoritative.
- A newer raw broker Position observation beyond the last profiled lifecycle anchor deliberately yields `REATTESTATION_REQUIRED`; E6 does not synthesize a projection.
- Durable conflicts remain fail closed; no conflict-resolution policy is invented by this slice.
- Provider/native audit persistence is outside this bounded task.

### 8. Dependencies / blockers

No remaining shared-contract blocker was found during static implementation after PR #57/#58.

Executable evidence remains absent. Therefore this handoff does **not** change:

```text
Restart/persistence criterion -> PASS
Paper E2E -> PASS
Gate B / PAPER_READY -> PASS
PAPER / SHADOW / LIVE authorization
```

Those remain subject to later E7 review/integration and explicitly approved local execution evidence.

### 9. Required next action

E6 stops after this task. The branch is ready for the normal PM/E7 review/integration sequence when scheduled. Approved-local verification must be a separate explicit action on an exact accepted revision.

### 10. Security / secrets

Confirmed:

- no real API key, API secret, token, credential, password, private key or live `.env` value was committed;
- fixtures are sanitized/deterministic;
- supported runtime persistence rejects secret-like fields;
- provider-native/private fields are outside this canonical durability slice;
- no provider/private request was sent.

### 11. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/E2E/restart/migration test was executed through GitHub infrastructure;
- no project executable workload was run by this task.

### 12. Live-trading impact

```text
NONE
```

This slice persists/replays Paper-stage canonical evidence only. It does not place orders, change risk sizing/protection, promote strategy lifecycle, enable PAPER, or grant SHADOW/LIVE authority.

### 13. Codex bug ticket

```text
NOT_APPLICABLE
```

No executable bug reproduction was performed and no bounded implementation defect is being delegated from this task.
