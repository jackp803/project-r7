# E5 Current Task

- task_id: `E5-20260824-021`
- issued_at: `2026-08-24T16:47:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-position-lifecycle-projection-producer-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, ADR-0007, accepted Gate B in-memory chain through PR #55, E6 blocker PR #56, accepted lifecycle ordering contract PR #57

## Objective

Implement only the E5-owned canonical producer/composition surface for:

```text
exact E4 Position broker observation
+ prior position-lifecycle-projection-v0.1 Position when applicable
+ E5 lifecycle interpretation
-> next canonical position-lifecycle-projection-v0.1 Position
```

This task materializes E5 lifecycle ordering authority so E6 can later persist/recover current Paper Position state without inventing lifecycle precedence.

Stop at the E5 profiled Position producer and E5-owned deterministic test definitions. Do **not** implement E6 storage/migrations/restart, E4 broker behavior, E7 E2E/release work, provider/private APIs, approved-local execution, PAPER/SHADOW/LIVE authorization, or new shared contract semantics.

## Accepted prerequisites

```text
PR #57 merge = 5b203ea2e4a235dfb4575626f15e2409b6674c59
architecture classification = ADDITIVE_PROFILE_REQUIRED
profile = position-lifecycle-projection-v0.1
schema_version remains contracts-v0.1
Position lifecycle durability contract/rule = RESOLVED STATIC
E4 adaptation = NONE REQUIRED
E5 profiled lifecycle producer = IMPLEMENTATION GAP / THIS TASK
E6 durability = BLOCKED UNTIL THIS PRODUCER IS ACCEPTED
```

All executable Gate B criteria remain `NOT_RUN`. No prior source/static acceptance is executable PASS.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E5_RISK_POSITION.md`;
- `contracts/README.md`;
- `contracts/SHARED_CONTRACTS_V1.md` Position/PositionAction semantics;
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`;
- ADR-0007;
- current `src/position/state_machine.py`;
- current protection producer/result bridge;
- current close producer;
- current `src/position/trade_result.py`;
- accepted PR #55 integration definitions and PR #56 blocker evidence read-only;
- current relevant E5 position/safety tests.

### Contract-first rule

If implementing the producer requires a new shared field, event, enum, authority meaning, profile revision or lifecycle semantic not already defined by PR #57, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Do not modify `contracts/**` or ADRs in this task.

## Required production surface

Add an E5-owned producer under `src/position/**` that emits a canonical serialized Position declaring exactly:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

The API shape is E5 implementation scope, but it must provide explicit deterministic composition for `GENESIS`, `TRANSITION` and `REATTESTATION` without caller-supplied revision/ID authority.

`lifecycle_interpreted_at` must be an explicit input to the producer; do not hide wall-clock generation inside deterministic identity construction.

The producer must never import or call E6 storage to obtain/allocate lifecycle ordering.

## Required canonical field behavior

Every profiled Position must carry and validate:

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

Required invariants:

- `lifecycle_source_broker_state_observed_at == Position.broker_state_observed_at` exactly;
- `lifecycle_revision` is a non-negative integer owned/allocated by E5;
- E5 preserves all E4-owned broker Position facts from the exact source observation unchanged;
- E5 may set only E5-owned lifecycle interpretation/profile metadata within this task;
- unknown/unsupported Position lifecycle state/event/profile fails closed;
- timestamps are exact RFC3339 UTC `Z` values;
- `lifecycle_interpreted_at` represents interpretation after the source observation is available and must not predate the source `broker_state_observed_at`;
- no random UUID, database row ID, insertion order, `persisted_at`, or process arrival order may become canonical lifecycle identity/order.

## GENESIS behavior

For first durability-eligible projection:

```text
kind = GENESIS
lifecycle_revision = 0
previous_lifecycle_projection_id = null
lifecycle_event = null
```

Requirements:

- consume a fresh exact E4 Position observation plus an explicit valid E5 lifecycle interpretation;
- do not create GENESIS from storage arrival order or legacy-row position;
- no prior profiled Position is accepted for GENESIS;
- unknown lifecycle interpretation fails closed;
- preserve the source broker observation exactly.

This task does not invent a new migration policy for legacy Positions; it only provides the E5 producer needed by the accepted PR #57 migration rule.

## TRANSITION behavior

For a lifecycle-changing E5 event:

```text
kind = TRANSITION
lifecycle_revision = previous.lifecycle_revision + 1
previous_lifecycle_projection_id = previous.lifecycle_projection_id
lifecycle_event = exact canonical PositionEvent
```

Requirements:

- previous Position must be a valid `position-lifecycle-projection-v0.1` projection;
- recompute/validate the previous deterministic `lifecycle_projection_id` before using it as authority;
- exact `position_id` must match;
- current E4 broker anchor must not regress below the previous broker anchor;
- if broker timestamps are equal, E4-owned broker fact material must not conflict with the previous projection;
- derive the target lifecycle only through the existing canonical `transition(previous.lifecycle_state, event)` state machine; never accept an arbitrary caller-provided target state;
- invalid state/event edge fails closed;
- multiple legitimate transitions may reuse one unchanged broker observation.

At minimum the producer must compose with real existing E5 lifecycle outcomes/events for:

- `PROTECTION_VERIFIED`;
- `PROTECTION_FAILED`;
- `PROTECTION_LOST`;
- `PROFIT_PROTECTION_VERIFIED` where currently supported;
- ordinary `EXIT_REQUESTED`;
- emergency `EXIT_REQUESTED`;
- supported `STATE_UNKNOWN` / reconciliation transitions;
- `POSITION_CLOSED` only after the existing E5 TradeResult/authoritative-flat validation has successfully produced its closure outcome.

Do not duplicate the state machine inside the producer.

## REATTESTATION behavior

For a newer/equal exact broker observation with unchanged E5 lifecycle:

```text
kind = REATTESTATION
lifecycle_revision = previous.lifecycle_revision + 1
previous_lifecycle_projection_id = previous.lifecycle_projection_id
lifecycle_event = null
current.lifecycle_state = previous.lifecycle_state
```

Requirements:

- previous profile/identity/predecessor chain material must validate;
- exact `position_id` must match;
- broker anchor must be `>=` previous broker anchor;
- equal broker timestamp with changed broker fact material is conflict/fail-closed;
- newer broker observation may carry changed E4 broker facts, but E5 must explicitly re-attest the unchanged lifecycle state;
- E5 must not infer a new lifecycle state merely because broker facts changed.

## Stable projection identity

Implement the exact PR #57 algorithm:

1. take the complete serialized profiled Position payload except `lifecycle_projection_id`;
2. canonical values must already be normalized;
3. UTF-8 JSON, lexicographically sorted keys, compact separators;
4. SHA-256;
5. prefix lowercase digest with `posproj_`.

Required behavior:

```text
same exact canonical projection material -> same lifecycle_projection_id
any identity-bearing payload change -> different lifecycle_projection_id
```

The producer must not let callers supply the final projection ID or lifecycle revision directly.

## Previous-projection validation / fail-closed requirements

Reject at minimum:

- wrong/missing schema/profile version;
- missing/non-integer/negative lifecycle revision;
- invalid/mismatched deterministic projection ID;
- revision > 0 with missing predecessor ID;
- revision 0 with non-null predecessor;
- unknown kind/event/state;
- `lifecycle_source_broker_state_observed_at` mismatch;
- source `position_id` mismatch;
- broker timestamp regression;
- same broker timestamp with conflicting broker fact material;
- invalid canonical lifecycle transition;
- malformed/non-UTC timestamps;
- interpretation time earlier than source broker observation.

Do not attempt to repair corrupt previous authority by guessing.

## Integration with existing E5 outcomes

Do not introduce a parallel lifecycle engine.

Test definitions must demonstrate the producer consuming the actual canonical event/outcome semantics from existing E5 surfaces where available, including:

```text
interpret_protection_result(...)
authorize_close_position_action(...)
build_trade_result(...)
```

A generic internal producer may accept the exact canonical `PositionEvent`, but positive integration tests must obtain that event from the real current E5 outcome path rather than hand-inventing a substitute event for every case.

For final closure, the profiled `CLOSED` Position must use the exact later E4 authoritative flat Position facts already accepted by the TradeResult builder; this producer must not declare flatness itself.

## Required deterministic E5 tests

Add/update E5-owned definitions under `tests/position/**` and, only if strictly useful, E5-owned `tests/safety/**` covering at minimum:

- GENESIS revision 0/profile fields/identity;
- exact GENESIS replay identity;
- protection verified transition on the same broker observation;
- protection failed and protection lost transitions;
- profit-protection transition compatibility;
- ordinary EXIT_REQUESTED and emergency EXIT_REQUESTED using real close outcomes;
- STATE_UNKNOWN and supported reconciliation transition compatibility;
- final POSITION_CLOSED using real successful TradeResult closure outcome + exact flat E4 Position;
- REATTESTATION on a newer broker observation with unchanged lifecycle;
- equal broker observation may carry multiple lifecycle revisions when broker facts are unchanged;
- broker timestamp regression fails closed;
- same broker timestamp + changed broker fact material fails closed;
- invalid previous profile/ID/revision/predecessor fails closed;
- invalid state/event edge fails closed;
- deterministic `posproj_` identity and changed identity-bearing material changes ID;
- malformed/non-UTC/interpreted-before-source timestamps fail closed;
- no E6/storage arrival-order dependency;
- no provider/private credentials/network behavior;
- existing protection/close/TradeResult/state-machine behavior remains compatible.

Use sanitized deterministic fixtures only.

## Writable scope

E5-owned only:

- `src/position/**`;
- `src/risk/**` only if strictly required for compatibility and justified in STATUS;
- `tests/position/**`;
- E5-owned `tests/safety/**` only if strictly needed;
- `docs/position/**` if useful;
- E5-specific `status/**` evidence/handoff;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**`, ADR or E7 release files;
- `src/storage/**`, `src/platform/**`, migrations or E6 implementation;
- E4 execution/broker production;
- E1-E3 production;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- PAPER/SHADOW/LIVE authority changes.

## Executable verification

This is E5 implementation/test-definition work under the hard local-only policy.

Unless a separate exact-revision Local Runner action is explicitly approved, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI, hosted runners, GitHub-triggered compute, Computer Adapter, provider/private APIs or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- canonical E5 `position-lifecycle-projection-v0.1` producer is materialized;
- GENESIS/TRANSITION/REATTESTATION ordering and identity follow PR #57 exactly;
- real existing E5 lifecycle outcomes compose into the producer without a parallel state machine;
- exact E4 broker facts remain unmodified and broker ordering does not regress;
- stale/corrupt/conflicting authority fails closed;
- deterministic E5 test definitions cover required positive/failure paths;
- no E6 storage, E4 broker, shared-contract, provider or release scope is crossed;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted profile is insufficient to produce a safe canonical projection without new shared semantics;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a local revision/authority workaround.

Do not declare E6 durability, Restart/persistence, Paper E2E, Gate B/PAPER_READY PASS or any PAPER/SHADOW/LIVE authorization.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e5-gate-b-position-lifecycle-projection-producer-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E5/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E6 durability, E7 E2E, approved-local verification, Gate C, PAPER, SHADOW or LIVE.