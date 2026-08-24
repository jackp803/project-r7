# E5 Gate B Position Lifecycle Projection Producer — 2026-08-24

## Handoff

**Agent:** E5 / Risk Management & Position Lifecycle Engineer  
**Task:** `E5-20260824-021`  
**Branch:** `agent/e5-gate-b-position-lifecycle-projection-producer-20260824`  
**Baseline main:** `d4ad044566b64f160c29dbfb1cd7b1dd5da90925`  
**Implementation/test HEAD before this handoff:** `5789c6dab9dd9a09fd892def1f74b44cbd77cb59`  
**State:** `DONE`  
**Local verification:** `NOT_RUN`

## 1. Objective completed

This task materializes only the E5-owned canonical producer/composition boundary required by accepted `position-lifecycle-projection-v0.1`:

```text
exact E4 Position broker observation
+ exact prior profiled Position when applicable
+ E5 lifecycle interpretation/outcome
-> next canonical position-lifecycle-projection-v0.1 Position
```

The producer adds E5 lifecycle ordering/identity authority without changing E4 broker truth or implementing E6 persistence.

## 2. Contract-first disposition

Required inspection found:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The accepted profile and ADR-0007 fully define:

- E4 broker-fact authority;
- E5 lifecycle ordering authority;
- `GENESIS | TRANSITION | REATTESTATION`;
- lifecycle revision/predecessor rules;
- broker-anchor non-regression/equal-time conflict semantics;
- canonical event/state semantics;
- deterministic `posproj_` identity;
- E6 persistence/replay responsibility.

No shared field, event, enum, authority, persistence meaning or release semantics had to be invented by E5.

Contracts/ADRs changed:

```text
NONE
```

## 3. Files changed

```text
src/position/lifecycle_projection.py
src/position/__init__.py
tests/position/test_lifecycle_projection.py
status/E5_GATE_B_POSITION_LIFECYCLE_PROJECTION_PRODUCER_20260824.md
coordination/E5/STATUS.md   # terminal mailbox update follows this handoff
```

No `src/execution/**`, `src/brokers/**`, `src/storage/**`, contracts, ADR, E6, E7 release-gate, provider or workflow file is changed.

## 4. Canonical producer surface

The new E5 module exposes:

```text
build_position_lifecycle_genesis(...)
build_position_lifecycle_transition(...)
build_position_lifecycle_closed_transition(...)
build_position_lifecycle_reattestation(...)
validate_position_lifecycle_projection(...)
stable_lifecycle_projection_id(...)
```

It emits one canonical Position mapping with the accepted additive fields:

```text
position_lifecycle_projection_profile_version
lifecycle_projection_id
lifecycle_revision
previous_lifecycle_projection_id
lifecycle_projection_kind
lifecycle_event
lifecycle_interpreted_at
lifecycle_source_broker_state_observed_at
```

Profile remains:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

## 5. E4 broker fact preservation

The producer accepts an exact serialized Position observation and copies the current canonical Position broker fields unchanged.

E5 changes/adds only:

```text
lifecycle_state
position-lifecycle-projection-v0.1 metadata
```

For equal broker anchors, the producer compares the complete current canonical Position payload after excluding E5 lifecycle/profile fields.

Therefore:

```text
same broker_state_observed_at + identical broker facts
-> lifecycle-only revision is allowed

same broker_state_observed_at + changed broker facts
-> EQUAL_TIME_BROKER_FACT_CONFLICT / fail closed

older broker_state_observed_at
-> BROKER_OBSERVATION_REGRESSION / fail closed
```

A newer E4 broker observation may carry changed exposure/PnL facts, but E5 must explicitly re-attest lifecycle state; storage arrival order is never authority.

Unknown undeclared Position fields fail closed rather than being silently promoted into a durability-eligible canonical projection.

## 6. GENESIS

`build_position_lifecycle_genesis()` produces the first durability-eligible projection:

```text
lifecycle_revision = 0
previous_lifecycle_projection_id = null
lifecycle_projection_kind = GENESIS
lifecycle_event = null
```

The caller supplies the explicit E5 lifecycle interpretation and explicit UTC `lifecycle_interpreted_at`; no wall clock, database sequence, random UUID, or caller-supplied revision/ID is used.

A legacy/raw Position is not backfilled from storage order. A source already carrying lifecycle projection metadata is rejected by the GENESIS source boundary.

## 7. TRANSITION

`build_position_lifecycle_transition()` validates the exact prior profiled Position and derives:

```text
next revision = previous.lifecycle_revision + 1
previous_lifecycle_projection_id = exact previous lifecycle_projection_id
next lifecycle_state = transition(previous.lifecycle_state, lifecycle_event)
```

The canonical existing E5 state machine is called directly; no lifecycle transition table is duplicated.

This supports current real E5 outcome events including:

- `PROTECTION_VERIFIED`;
- `PROTECTION_FAILED`;
- `PROTECTION_LOST`;
- `EXIT_REQUESTED`;
- `STATE_UNKNOWN`;
- supported explicit reconciliation events;
- `PROFIT_PROTECTION_VERIFIED` where currently supported.

Invalid event/state edges fail closed.

## 8. CLOSED is structurally bound to TradeResult success

Generic transition deliberately rejects caller-supplied:

```text
POSITION_CLOSED
```

with:

```text
TRADE_RESULT_CLOSURE_OUTCOME_REQUIRED
```

Final closure must use:

```text
build_position_lifecycle_closed_transition(...)
```

which requires the exact current E5 `TradeResultBuildOutcome` and validates at minimum:

```text
outcome.event = POSITION_CLOSED
outcome.next_state = CLOSED
TradeResult.position_id = exact source Position.position_id
TradeResult.symbol = exact source Position.symbol
source Position.actual_quantity = 0
source Position.reconciliation_status = CONSISTENT
TradeResult.closed_at = source broker_state_observed_at
TradeResult.flat_position_observed_at = source broker_state_observed_at
broker anchor is non-regressing
```

Only after those checks does the producer apply the canonical `POSITION_CLOSED` state-machine transition.

This prevents a manually invented event from bypassing PR #49/#53 authoritative-flat, Fill, funding, fee and PnL validation.

## 9. REATTESTATION

`build_position_lifecycle_reattestation()` explicitly binds the previous E5 lifecycle state to an equal/newer E4 broker observation:

```text
lifecycle_revision = previous + 1
previous_lifecycle_projection_id = exact previous ID
lifecycle_projection_kind = REATTESTATION
lifecycle_event = null
lifecycle_state = previous lifecycle_state
broker_state_observed_at >= previous broker anchor
```

It does not copy lifecycle authority from the incoming E4-shaped source Position. The previous E5 lifecycle state is retained explicitly.

## 10. Projection validation and deterministic identity

A profiled Position fails closed on unsupported/malformed:

- schema/profile;
- lifecycle state/event/kind;
- negative/non-integer revision;
- GENESIS/non-GENESIS shape;
- predecessor ID shape;
- broker source anchor;
- UTC timestamps;
- interpretation before broker observation;
- canonical decimal serialization;
- deterministic projection ID;
- declared transition event/state incompatibility.

`lifecycle_projection_id` follows the accepted profile exactly:

```text
complete immutable serialized profiled Position
minus lifecycle_projection_id
-> sorted compact JSON
-> UTF-8
-> SHA-256
-> posproj_<lowercase hex>
```

Same exact projection produces the same identity. Lifecycle, broker fact, revision, predecessor, event or interpreted-time changes produce different identity material.

## 11. No caller/storage ordering authority

Public producer APIs intentionally expose no caller parameter for:

```text
lifecycle_revision
lifecycle_projection_id
```

The producer does not use/import:

- E6 storage/platform implementation;
- SQLite row IDs or insertion order;
- `persisted_at`;
- provider/network calls;
- credentials;
- random UUID identity.

Revision and projection identity remain E5-owned and are derived from exact prior projection + current canonical material.

## 12. Deterministic test definitions materialized

Added:

```text
tests/position/test_lifecycle_projection.py
```

Definitions cover at minimum:

- GENESIS revision `0` / null predecessor / deterministic ID;
- exact replay idempotency;
- real `interpret_protection_result()` `PROTECTION_VERIFIED` transition on the same broker observation;
- real protection failure/loss outcomes to `EMERGENCY`;
- profit-protection transition compatibility;
- real `authorize_close_position_action()` ordinary/emergency `EXIT_REQUESTED` outcomes;
- real `STATE_UNKNOWN` bridge result and supported reconciliation transition;
- real successful `build_trade_result()` outcome required for `POSITION_CLOSED`;
- generic caller-supplied `POSITION_CLOSED` rejection;
- exact flat Position/broker anchor preserved through CLOSED projection;
- REATTESTATION with newer broker facts and unchanged E5 lifecycle;
- multiple legitimate lifecycle revisions sharing one broker observation;
- broker timestamp regression fail closed;
- equal-time changed broker payload fail closed;
- corrupt profile/ID/revision/predecessor fail closed;
- invalid event/state edge fail closed;
- deterministic identity changes;
- malformed/non-UTC/early interpretation timestamps fail closed;
- source already profiled or unknown/provider-shaped fields fail closed;
- no storage/provider/release/caller revision/ID authority.

Positive integration definitions use current real E5 outcome surfaces rather than hand-authoring substitute success events for protection, close and final TradeResult closure.

## 13. Existing safety behavior

No E5 risk policy, protection rule, close authority, TradeResult formula, state-machine enum/transition table, broker behavior or funding meaning is changed.

Existing fail-closed behavior for unknown/reconciliation state remains unchanged.

## 14. Executable verification

Result:

```text
NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact target revision is exposed in this session. Static inspection is not executable PASS evidence.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN != PASS`.

No project code/test was executed by GitHub Actions, CI, hosted runner, GitHub-triggered self-hosted compute, arbitrary cloud compute, Computer Adapter, provider/private API, or credentialed environment.

## 15. Security / secrets

Confirmed:

- no API key, secret, token, password, private key or live `.env` value added;
- no provider/private API/network request performed;
- tests use only sanitized deterministic fixtures;
- no PAPER/SHADOW/LIVE activation field or authority added.

## 16. Release impact

This task changes implementation dependency status only; it does not change release authority:

```text
position-lifecycle-projection-v0.1 shared contract = ACCEPTED / prior PR #57
E5 lifecycle projection producer = MATERIALIZED STATICALLY / this task
E6 durable Paper persistence/restart/audit = NOT IMPLEMENTED BY E5 / later dependency
Restart/persistence preserves required state = BLOCKED pending E6 implementation + approved-local evidence
Paper E2E durable audit = BLOCKED
approved-local Gate B verification = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 does not claim persistence/restart, Paper E2E, Gate B or PAPER_READY PASS.

## 17. Next dependency / stop condition

This handoff is for PM/E7 review. E5 stops on `DONE` for `E5-20260824-021`.

Do not self-start:

- E6 persistence/migrations/restart/audit;
- E7 durability/E2E definitions;
- approved-local verification;
- provider/private work;
- Gate C;
- PAPER, SHADOW or LIVE.
