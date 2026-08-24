# ADR-0008 — Position Lifecycle Vocabulary Validation Boundary

- Status: `ACCEPTED`
- Date: `2026-08-24`
- Decision task: `E7-20260824-050`
- Authority: E7 Integration / Architecture / System QA / Release Engineer
- Parent contract: `contracts-v0.1`
- Projection profile: `position-lifecycle-projection-v0.1`
- Normative vocabulary: `contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`

## Context

ADR-0007 and `position-lifecycle-projection-v0.1` established E5-owned lifecycle revision/identity authority so E6 can persist/replay Position lifecycle projections without using database arrival order.

PM review of E6-20260824-013 exposed one narrower ambiguity: the projection profile required unsupported lifecycle state/event/kind to fail closed, but while lifecycle states were already enumerated in `contracts/SHARED_CONTRACTS_V1.md`, the supported serialized `PositionEvent` vocabulary was only referenced as the exact canonical E5 `PositionEvent` and not exhaustively published as a shared consumer contract.

E6 cannot safely solve that ambiguity by importing E5 code or inventing an E6-private enum.

## Decision

Keep unchanged:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

Publish `contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md` as the exhaustive normative consumer vocabulary for this profile.

This is a compatible contract clarification, not a new lifecycle model and not a breaking authority change.

## Shared consumer vocabulary

For this profile, restart-authoritative `lifecycle_state` is limited to the existing eight baseline Position lifecycle states.

For `TRANSITION`, restart-authoritative `lifecycle_event` is limited to the exhaustive thirteen-value list published in the vocabulary contract.

`GENESIS` and `REATTESTATION` require `lifecycle_event = null`.

Unknown state/event/kind fails closed and cannot advance the current durable Position projection.

## Authority boundary

E5 remains authoritative for the semantic transition relation:

```text
(previous lifecycle_state, lifecycle_event) -> next lifecycle_state
```

E6 is authorized only to perform mechanical shared-contract validation:

- profile/version membership;
- supported state/event/kind membership;
- event nullability by projection kind;
- existing revision/predecessor/identity/broker-anchor/replay/conflict checks.

E6 does not import or replay the E5 transition table, derive lifecycle from execution evidence, or allocate lifecycle authority.

## Compatibility

No existing accepted PR #57/#58 profiled Position changes identity or meaning.

No new serialized field is added.

A future event/state outside the published vocabulary remains unsupported for `position-lifecycle-projection-v0.1` until E7 explicitly publishes a later compatible/versioned contract decision. Consumers continue to fail closed in the meantime.

## E6 remediation consequence

The E6-20260824-013 branch may be remediated in bounded storage validation scope by checking exact vocabulary membership from the E7-owned contract. E6 does not need an E5 import and does not need a transition-table copy.

PM must still re-review that branch after remediation. Static materialization is not executable PASS evidence.

## Release impact

```text
Position lifecycle vocabulary semantic gap = RESOLVED STATIC
E6-013 PM acceptance = NO / remains pending remediation + re-review
Restart/persistence executable criterion = NOT_RUN
Paper E2E durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
project_executable_verification = NOT_RUN
```

No tests/project code were executed and no provider/private/release authority is introduced.