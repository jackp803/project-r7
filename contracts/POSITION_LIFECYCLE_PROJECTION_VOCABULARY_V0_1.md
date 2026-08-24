# Position Lifecycle Projection Vocabulary — V0.1

> Parent contract set: `contracts-v0.1`  
> Applies to profile: `position-lifecycle-projection-v0.1`  
> Status: `BASELINE / NORMATIVE COMPANION`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260824-050`

## 1. Purpose

This file is the exhaustive shared consumer vocabulary for restart-authoritative `position-lifecycle-projection-v0.1` Position objects.

It resolves only the serialized vocabulary boundary between:

```text
E5 -> produces authoritative lifecycle interpretation
E6 -> validates/persists/replays it mechanically
```

It does not move lifecycle transition authority to E6 and does not change E5 state-machine semantics.

The parent versions remain unchanged:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

No new serialized field is introduced.

## 2. Compatibility decision

The original profile already required an exact canonical E5 lifecycle state/event and required unsupported vocabulary to fail closed, but it did not exhaustively publish the `PositionEvent` values as a shared consumer contract.

Therefore the accepted resolution is a compatible normative clarification under the existing profile, not a breaking contract change and not a new projection profile.

For restart-authoritative use, the supported vocabulary of `position-lifecycle-projection-v0.1` is frozen by this file. A future lifecycle state/event outside these lists requires a later E7-approved profile/version before it can become restart-authoritative. Consumers must not silently extend this list from E5 source code.

## 3. Supported serialized `lifecycle_state`

For `position-lifecycle-projection-v0.1`, `Position.lifecycle_state` must be exactly one of:

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

This is the same baseline Position lifecycle-state vocabulary already defined in `contracts/SHARED_CONTRACTS_V1.md`.

Any other value is unsupported for this profile and fails closed before the projection can become current/restart-authoritative.

## 4. Supported serialized `lifecycle_event`

For a `TRANSITION` projection, `lifecycle_event` must be exactly one of:

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

These values are the exhaustive serialized `PositionEvent` vocabulary accepted by `position-lifecycle-projection-v0.1`.

Any other non-null value is unsupported and fails closed before persistence/current-projection advancement.

This shared list is a vocabulary contract only. It does not authorize E6 to decide whether a particular event is valid from a particular previous lifecycle state.

## 5. Projection-kind / event shape

Supported `lifecycle_projection_kind` values remain exactly:

```text
GENESIS
TRANSITION
REATTESTATION
```

Event rules are normative:

```text
GENESIS      -> lifecycle_event = null
TRANSITION   -> lifecycle_event = one supported value from section 4
REATTESTATION -> lifecycle_event = null
```

Unknown projection kinds fail closed.

A non-null event on `GENESIS` or `REATTESTATION` is invalid even if that event string is in the supported event vocabulary.

A null event on `TRANSITION` is invalid.

## 6. E5 transition authority remains unchanged

E5 remains responsible for producing semantically valid lifecycle transitions, including the rule:

```text
transition(previous.lifecycle_state, lifecycle_event)
== current.lifecycle_state
```

E5 may implement and test the full transition table in `src/position/**`.

E6 must not:

- import E5 production modules merely to validate restart vocabulary;
- copy/reimplement the E5 `(previous_state, event) -> next_state` transition table;
- infer lifecycle from OrderResult, Fill, PositionAction, TradeResult, or storage arrival order;
- allocate lifecycle revisions, predecessor IDs, or projection IDs.

The shared durability contract gives E6 authority only to validate declared profile/vocabulary/shape/order/identity/reference rules that are explicitly serialized and shared.

## 7. Mechanical E6 validation boundary

For one proposed restart-authoritative projection, E6 may mechanically require all of the following without becoming lifecycle authority:

1. `schema_version == contracts-v0.1`;
2. `position_lifecycle_projection_profile_version == position-lifecycle-projection-v0.1`;
3. `lifecycle_projection_kind` is in the three-value list in section 5;
4. `lifecycle_state` is in the exhaustive state list in section 3;
5. event nullability matches section 5;
6. a `TRANSITION.lifecycle_event` is in the exhaustive event list in section 4;
7. revision/predecessor/identity/broker-anchor/replay/conflict rules from `POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md` hold.

E6 does not need to know the E5 transition table to enforce these consumer checks.

## 8. Unknown / unsupported vocabulary

Unknown or unsupported values are never treated as a later, healthier, protected, exiting, closed, or otherwise authoritative state.

Required behavior:

```text
unknown lifecycle_state -> reject/fail closed
unknown TRANSITION lifecycle_event -> reject/fail closed
unknown lifecycle_projection_kind -> reject/fail closed
```

A rejected payload must not advance the current restart-authoritative Position projection.

E6 may preserve rejected/conflicting evidence for diagnostics if its storage design supports that, but it must not promote it to current authoritative state.

## 9. Replay / identity impact

This clarification does not change any existing `position-lifecycle-projection-v0.1` identity, ordering, predecessor, broker-anchor, stale, duplicate, gap, conflict, or re-attestation semantics.

In particular:

- `lifecycle_projection_id` remains content-derived from the complete immutable profiled Position payload except the ID field itself;
- `lifecycle_revision` remains E5-owned and contiguous per `position_id`;
- E4 remains authoritative for `broker_state_observed_at` and broker facts;
- E6 still cannot use database row order or arrival time as lifecycle authority.

No accepted PR #57/#58 projection needs to be rewritten merely because this vocabulary registry is now explicit.

## 10. Consumer implementation consequence

The bounded E6 remediation after this decision is a vocabulary membership check against this E7-owned contract plus the existing structural/profile rules.

It is not an E5 state-machine port.

E6 may define local constants mirroring these exact shared lists only as an implementation of this contract; those constants are not an independent E6 enum/authority and must be updated only through accepted E7 contract change.

## 11. Future vocabulary changes

A future lifecycle state/event that is not listed here is unsupported by `position-lifecycle-projection-v0.1` for restart-authoritative durability.

Before such a value can be accepted durably, E7 must explicitly review compatibility and publish a later accepted profile/version or other unambiguous versioned shared rule. Consumers must continue to fail closed until then.

## 12. Release / verification impact

```text
Position lifecycle vocabulary contract = RESOLVED STATIC
E6 durability implementation = PM REVIEW BLOCKED pending bounded remediation/re-review
Restart/persistence executable criterion = NOT_RUN
Paper E2E durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
project_executable_verification = NOT_RUN
```

No project code or tests are executed by this contract decision.