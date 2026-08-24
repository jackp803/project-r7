# E6 Gate B Paper Runtime Durability — V0.1

> Task: `E6-20260824-013`  
> Owner: E6 Platform / Storage  
> Contract baseline: `contracts-v0.1`  
> Position durability profile: `position-lifecycle-projection-v0.1`  
> Executable verification: `NOT_RUN`

## Scope

This slice persists already-canonical Gate B Paper runtime truth and restores it after SQLite close/reopen. It does not run the Paper runtime, call E4/E5 producers, recalculate domain state, access a provider, promote a strategy, or grant PAPER/SHADOW/LIVE authority.

Supported composition surface:

```python
from storage.runtime import open_paper_runtime_journal
```

The returned `PaperRuntimeJournal` owns persistence/recovery only. Raw SQLite connection/migration mechanics remain internal.

## Durable coverage

The additive `0002_paper_runtime_durability.sql` migration stores/indexes:

- RiskDecision;
- ApprovedTradePlan;
- `position-lifecycle-projection-v0.1` Position projections;
- raw/legacy Position broker observations as non-restart-authoritative audit evidence;
- PositionAction;
- OrderRequest;
- append-only OrderResult observations plus a mechanical current index;
- Fill;
- FundingAllocationEvidence;
- immutable TradeResult;
- sanitized conflict audit metadata.

Canonical payload JSON and SHA-256 payload hashes are retained. Storage row IDs, persistence timestamps and indexes are storage metadata only and never replace canonical IDs.

## Position lifecycle authority

E6 consumes the E5-produced fields:

```text
lifecycle_projection_id
lifecycle_revision
previous_lifecycle_projection_id
lifecycle_projection_kind
lifecycle_event
lifecycle_interpreted_at
lifecycle_source_broker_state_observed_at
```

E6 does not call the E5 state machine during persistence or recovery.

Current Position selection is mechanical:

```text
GENESIS revision 0
-> exact contiguous revision + 1
-> exact predecessor ID
-> nondecreasing E4 broker anchor
-> no equal-anchor broker-fact conflict
-> highest accepted contiguous revision
```

Exact stale historical replay remains audit history and cannot replace current. Gaps, predecessor mismatch, same-revision conflicts, projection-ID corruption and broker-anchor regression fail closed.

A raw newer E4 Position observation does not inherit the old E5 lifecycle state. Recovery reports `REATTESTATION_REQUIRED` while preserving the last exact E5 projection and the newer raw broker evidence separately.

Legacy unprofiled Position payloads are never promoted into restart-authoritative state by insertion order.

## Immutable/idempotent facts

RiskDecision, ApprovedTradePlan, PositionAction, OrderRequest and Fill use canonical ID + exact canonical payload semantics:

```text
same ID + same payload -> idempotent replay
same ID + changed payload -> conflict / fail closed
```

`client_order_id` remains unique to one durable OrderRequest. Fill lineage is checked mechanically against the durable request; E6 does not invent execution truth.

TradeResult is immutable and unique for the current `(trade_plan_id, position_id)` closed lineage. Persistence requires the exact durable funding evidence referenced by the result and checks the accepted funding lineage/status/cost binding. A later write cannot silently rewrite PnL, fees, exit reasons, quantity or funding binding.

## Funding durability

`funding-allocation-v0.1` is stored separately from TradeResult.

The lineage key is exactly:

```text
(
  funding_evidence_profile_version,
  trade_plan_id,
  position_id,
  symbol,
  interval_start,
  interval_end,
  interval_semantics
)
```

Rules:

```text
same evidence ID + same allocation identity -> idempotent
same evidence ID + changed identity -> fail closed
different evidence ID + same lineage key -> conflict / no last-write-wins
```

`calculated_at` is observation metadata and is excluded from financial allocation identity. A later equivalent observation may be recorded in the funding observation audit, but the first canonical funding object is not overwritten.

## Mutable observations

OrderResult is append-only by `(order_request_id, observed_at)`.

- later authoritative observation may advance the current index;
- stale observation remains audit history only;
- equal observation time with changed canonical payload fails closed;
- UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED remain exact after restart.

Raw Position broker observations are also append-only audit evidence. They do not become E5 lifecycle projections.

## Recovery view

`PaperRuntimeRecovery` is an E6-local storage view, not a shared DTO. It returns exact stored canonical payloads and one fail-closed diagnostic status:

```text
READY
REATTESTATION_REQUIRED
RECONCILIATION_REQUIRED
INCOMPLETE
CONFLICT
```

The diagnostic does not mutate or synthesize any canonical object.

Closed recovery requires the exact CLOSED profiled Position plus FundingAllocationEvidence and TradeResult binding. Missing/conflicting graph material remains fail closed.

## Existing Registry compatibility

The migration is additive. Existing `0001_strategy_registry.sql`, `open_sqlite_platform(...)` and the early Registry lifecycle remain unchanged:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

This task does not add PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED or RETIRED strategy transitions.

## Security

Canonical persistence rejects secret-like field names recursively. No API key, secret, passphrase, password, private key, token or credential is required by the runtime journal. Provider/private network access is not part of this slice.

## Verification

Deterministic definitions are under:

```text
tests/storage/test_paper_runtime_durability.py
tests/platform/test_paper_runtime_storage_surface.py
```

They are intentionally not executed in this GitHub/ChatGPT environment.

Exact future approved-local Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Current executable result:

```text
NOT_RUN
```

No GitHub Actions/CI/hosted runner, GitHub-triggered compute, provider/private API, credential, PAPER, SHADOW or LIVE execution is used by this task.
