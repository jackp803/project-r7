# Gate B Position Lifecycle Vocabulary Contract Decision — E7-20260824-050

## Authority / scope

- task_id: `E7-20260824-050`
- target branch: `agent/e7-gate-b-lifecycle-event-vocabulary-contract-20260824`
- reviewed latest main: `20f46faf0067e17ba83fd57bd869f0cdc3a2b079`
- authoritative TASK blob: `d5579cc16497bc7b5870e81aefe16b2349326c77`
- contract baseline: `contracts-v0.1`
- projection profile: `position-lifecycle-projection-v0.1`
- accepted ordering contract PR #57 merge: `5b203ea2e4a235dfb4575626f15e2409b6674c59`
- accepted E5 projection producer PR #58 merge: `f5bbeaf1daef1fdeda28ea6d12482b3b26018cc8`
- reviewed E6-013 source/tests/docs head: `95679067132d8fa3933b8534983e6d975d0d68ff`
- reviewed E6-013 terminal STATUS: `DONE / executable NOT_RUN`
- PM acceptance before this decision: `NO / CONTRACT_OR_SEMANTIC_GAP`
- Issue #59: `SUPERSEDED / prior bounded-bug diagnosis not authoritative`
- project_executable_verification: `NOT_RUN`

This task is static contract/architecture review only. No project code/tests, Local Runner, GitHub Actions/CI/hosted runner, provider/private API, credentials, PAPER, SHADOW or LIVE runtime was used.

## Independent finding

The PM/E6 blocker is confirmed in a narrower form.

Existing shared authority was sufficient for:

- `lifecycle_state`: `contracts/SHARED_CONTRACTS_V1.md` exhaustively enumerates the baseline Position lifecycle states;
- `lifecycle_projection_kind`: `POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md` exhaustively defines `GENESIS | TRANSITION | REATTESTATION` and event nullability shape;
- revision/predecessor/identity/broker-anchor/replay/conflict semantics: PR #57 profile is explicit.

Existing shared authority was **not sufficient** for a storage consumer to validate `TRANSITION.lifecycle_event` membership without looking into E5 production code. The profile required an "exact canonical E5 PositionEvent" and required unsupported events to fail closed, but it did not publish the exhaustive accepted serialized event vocabulary as a shared consumer contract.

The reviewed E6-013 `validate_position_projection()` therefore checks:

```text
lifecycle_state -> non-empty string only
TRANSITION.lifecycle_event -> non-empty string only
```

while correctly checking projection kind/nullability and other profile mechanics. Hardcoding the E5 enum from implementation or importing E5 state-machine code into E6 would violate contract-first ownership.

## Decision

Resolution:

```text
EXISTING PROFILE SEMANTIC INTENT = CORRECT
SHARED CONSUMER VOCABULARY = INSUFFICIENTLY MATERIALIZED
RESOLUTION = COMPATIBLE NORMATIVE CLARIFICATION
schema_version = contracts-v0.1 / UNCHANGED
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1 / UNCHANGED
new serialized fields = NONE
Position lifecycle vocabulary contract = RESOLVED STATIC
```

Materialized normative companion:

`contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`

Architecture clarification:

`docs/adr/ADR-0008-position-lifecycle-vocabulary-validation-boundary.md`

## Exhaustive restart-authoritative lifecycle state vocabulary

For `position-lifecycle-projection-v0.1`:

```text
PENDING_ENTRY
OPEN_UNPROTECTED
OPEN_PROTECTED
PROFIT_PROTECTED
EXIT_REQUESTED
CLOSED
EMERGENCY
RECONCILIATION_REQUIRED
```

Unknown state fails closed and cannot become current/restart-authoritative.

## Exhaustive restart-authoritative `TRANSITION.lifecycle_event` vocabulary

```text
ENTRY_FILL_OBSERVED
ENTRY_TERMINATED
PROTECTION_VERIFIED
PROFIT_PROTECTION_VERIFIED
PROTECTION_FAILED
PROTECTION_LOST
EXIT_REQUESTED
EXIT_FAILED
POSITION_CLOSED
STATE_UNKNOWN
RECONCILED_FLAT
RECONCILED_OPEN_UNPROTECTED
RECONCILED_OPEN_PROTECTED
```

Unknown event fails closed and cannot become current/restart-authoritative.

## Projection-kind/event rule

```text
GENESIS       -> lifecycle_event = null
TRANSITION    -> lifecycle_event = one supported event above
REATTESTATION -> lifecycle_event = null
```

Unknown kind fails closed.

## Authority boundary

E5 remains authoritative for the full transition relation:

```text
transition(previous.lifecycle_state, lifecycle_event)
== current.lifecycle_state
```

E6 does **not** evaluate/copy/import that transition table.

E6 may mechanically validate only shared serialized rules:

- schema/profile compatibility;
- state/event/kind vocabulary membership;
- event nullability by kind;
- revision/predecessor/identity/broker-anchor/replay/conflict rules already defined by PR #57.

E6 must not infer lifecycle from OrderResult/Fill/PositionAction/TradeResult and must not allocate lifecycle revisions/IDs.

## Compatibility / future values

No accepted PR #57/#58 projection changes identity or meaning. No migration/backfill is required by this vocabulary clarification.

A future state/event outside the lists above is unsupported for restart-authoritative `position-lifecycle-projection-v0.1` until E7 explicitly publishes a later accepted version/profile rule. Consumers must fail closed until then; they may not silently learn new vocabulary from E5 source code.

## Bounded E6 remediation contract

The E6-013 remediation is now mechanically bounded and requires no E5 production import or transition-table duplication:

1. add exact membership validation for the eight shared lifecycle states;
2. add exact membership validation for the thirteen shared `TRANSITION.lifecycle_event` values;
3. retain existing `GENESIS` / `REATTESTATION` null-event checks;
4. reject unsupported state/event before current-projection advancement;
5. add deterministic storage definitions proving rejected unsupported values do not advance durable current state;
6. preserve all existing revision/predecessor/identity/broker-anchor/replay/conflict behavior.

This is an E6 storage-consumer implementation follow-up. E7 does not modify the E6 branch in this task.

## Release reconciliation

```text
Position lifecycle vocabulary contract = RESOLVED STATIC
E6 durability implementation = MATERIALIZED / PM REVIEW BLOCKED pending bounded remediation + PM re-review
Restart/persistence preserves required state = BLOCKED / executable criterion NOT_RUN
Paper E2E closes to TradeResult and persists audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No current executable `NOT_RUN` criterion becomes PASS.

## Completion

E7 completes only `E7-20260824-050`. No E6 remediation, Paper E2E, approved-local verification, Gate C, provider/private work, PAPER, SHADOW, LIVE or next task is started.