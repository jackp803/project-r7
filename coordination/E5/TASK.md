# E5 Current Task

- task_id: `E5-20260824-023`
- issued_at: `2026-08-24T22:42:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-lifecycle-execution-binding-producer-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, `contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`, `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`, ADR-0007, ADR-0008, ADR-0009, accepted lifecycle producer PR #58, accepted E7 freshness-contract PR #63 merge `f46e44288fe65d2eef863467617131c7869e5af1`

## Objective

Implement only the bounded E5 producer adaptation required by `position-lifecycle-execution-binding-v0.1`.

For each Gate B lifecycle projection that E5 intends to be restart-authoritative, E5 must be able to emit exactly one immutable canonical `PositionLifecycleExecutionEvidenceBinding` proving the exact Position-linked E4 reduction-order execution evidence that E5 consumed/considered for that lifecycle interpretation.

This task does **not** change E5 transition semantics, E4 execution truth, E6 persistence/recovery, TradeResult persistence, release gates, provider/private APIs, or PAPER/SHADOW/LIVE authority.

## Required baseline handling

Before editing:

- verify latest `main` `coordination/E5/TASK.md` task_id exactly matches `E5-20260824-023`;
- read latest `main`, including PR #63 contract/ADR;
- preserve the accepted `position-lifecycle-projection-v0.1` producer from PR #58 and all accepted protection/close/TradeResult semantics;
- do not rewrite accepted lifecycle projection IDs or add fields to existing profiled Position payloads.

## Shared contract to implement

Produce the exact companion profile:

```text
schema_version = contracts-v0.1
lifecycle_execution_binding_profile_version = position-lifecycle-execution-binding-v0.1
execution_scope = POSITION_LINKED_REDUCTION_ORDERS_V0_1
```

The binding must reference exactly one existing lifecycle projection through:

```text
position_id
lifecycle_projection_id
lifecycle_revision
execution_interpreted_at == lifecycle_interpreted_at
```

and must contain the deterministic `order_evidence` snapshot and `execution_snapshot_hash` defined by the E7 contract.

## Required E5 producer behavior

### 1. Deterministic companion builder

Materialize an E5-owned production surface that accepts:

- one exact canonical `position-lifecycle-projection-v0.1` lifecycle projection already produced by E5;
- the exact canonical in-scope E4 OrderRequest evidence E5 considered;
- the complete canonical OrderResult observation sets for those requests that E5 considered;
- the complete canonical Fill sets for those requests that E5 considered.

and emits one immutable canonical `PositionLifecycleExecutionEvidenceBinding`.

Do not import E6 storage implementation to compute the binding.

### 2. Evidence scope

Include every supplied canonical OrderRequest satisfying the shared V0.1 scope:

```text
OrderRequest.position_id == projection.position_id
OrderRequest.authorization_type == POSITION_ACTION
OrderRequest.order_role in {
  PROTECTION_STOP,
  POSITION_EXIT,
  EMERGENCY_EXIT
}
```

Reject/fail closed on incompatible request/Position lineage instead of silently dropping malformed in-scope evidence.

Do not heuristically include pre-position `entry-v0.1` evidence by `trade_plan_id`; entry restart authority is explicitly outside V0.1.

### 3. Exact canonical snapshot rules

Implement the contract exactly:

- OrderRequest complete canonical payload SHA-256;
- OrderResult logical set entries `(observed_at, payload_hash)` sorted by `observed_at`, then hash;
- Fill logical set entries `(fill_id, filled_at, payload_hash)` sorted by `filled_at`, then `fill_id`;
- exact counts and latest semantic timestamps;
- `order_evidence` sorted by `order_request_id`;
- `execution_snapshot_hash` over the exact canonical snapshot material;
- deterministic `posexecbind_<sha256>` identity over the complete binding payload excluding only the ID field.

Exact duplicate evidence is replay-safe. Conflicting same identity/time evidence fails closed. Binary floats/noncanonical unsupported values must not be silently normalized into a different financial fact.

### 4. E5 authority boundary

The binding declares what execution evidence E5 interpreted; it does not replace lifecycle interpretation.

Preserve:

```text
TRANSITION -> E5 transition semantics unchanged
REATTESTATION -> same lifecycle state, next revision, explicit E5 authority
GENESIS -> existing semantics unchanged
```

When execution evidence advances but lifecycle state remains unchanged, E5 must have a supported composition path to produce a new `REATTESTATION` projection plus its new companion binding. When execution evidence changes lifecycle state, E5 must have a supported composition path to produce the next `TRANSITION` plus its binding.

Do not mutate an older binding to claim later evidence was interpreted.

### 5. Fail-closed validation

At minimum reject:

- unsupported schema/profile/scope;
- lifecycle projection/profile mismatch;
- binding `position_id` / projection ID / revision / interpreted-time mismatch;
- OrderRequest outside the accepted role/authorization/Position scope when claimed as in-scope binding evidence;
- OrderResult whose `order_request_id` does not match its evidence entry;
- equal `observed_at` with different canonical OrderResult payload;
- Fill request/Position/action/order-role lineage mismatch;
- same `fill_id` with different payload;
- duplicate `order_request_id` with changed canonical request payload;
- noncanonical identity/hash material.

Do not infer healthy/protected/closed state from missing evidence.

## Required deterministic E5 test definitions

Add E5-owned definitions under `tests/position/**` covering at minimum:

1. deterministic empty in-scope snapshot binding for a valid projection when no reduction order exists yet;
2. OPEN_PROTECTED projection + PROTECTION_STOP OPEN observation -> exact deterministic binding;
3. later PARTIALLY_FILLED/FILLED OrderResult and Fill -> different new binding snapshot/ID after E5 interpretation;
4. CANCELED/EXPIRED/REJECTED protection evidence -> different new binding snapshot/ID;
5. POSITION_EXIT and EMERGENCY_EXIT are included by the same scope rules;
6. equal-broker-anchor REATTESTATION + newer execution evidence -> next projection revision plus new binding without changing lifecycle state;
7. order_evidence ordering is deterministic independent of caller collection order;
8. OrderResult observation set hashing is deterministic and exact duplicates are idempotent;
9. Fill set hashing is deterministic and exact duplicates are idempotent;
10. conflicting equal-time OrderResult fails closed;
11. conflicting Fill identity/payload fails closed;
12. request/result/fill lineage mismatch fails closed;
13. entry-v0.1 / pre-position evidence is not heuristically joined into V0.1;
14. existing lifecycle projection/transition/protection/close tests remain definition-compatible.

Use sanitized deterministic fixtures. Do not add E6 durability logic to E5 tests.

## Writable scope

E5-owned only:

- `src/position/**`;
- `tests/position/**`;
- strictly necessary E5 docs under `docs/position/**`;
- E5-specific status/handoff under `status/**`;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` or ADR changes;
- E4 production/tests;
- E6 storage/platform production/tests;
- E7 integration/release files;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- strategy promotion;
- PAPER/SHADOW/LIVE authorization.

If the accepted contract cannot be implemented without new shared semantics or an E4/E6 authority change, stop with:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

and provide exact evidence. Do not guess.

## Executable verification

Local-only. Unless a separate exact-revision Product-Owner/PM-approved local action is available, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners/GitHub-triggered compute. `NOT_RUN != PASS`.

## Acceptance

### DONE

- E5 can deterministically emit exactly one canonical execution-evidence companion for each lifecycle projection intended to be Gate B restart-authoritative;
- the companion exactly implements the PR #63 snapshot/hash/identity/evidence-scope contract;
- equal-anchor REATTESTATION can bind newer execution evidence without lifecycle inference by E6;
- existing E5 lifecycle/protection/close semantics and existing projection identities remain unchanged;
- deterministic E5 producer test definitions are materialized;
- no shared contract, E4/E6 implementation, provider/private, CI, or release authority scope is crossed;
- executable evidence is approved-local exact evidence or explicit `NOT_RUN` with commands;
- no Restart/persistence PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or PAPER/SHADOW/LIVE authorization is claimed.

### BLOCKED

If producing the exact binding requires undefined shared semantics, record exact expected-vs-actual evidence and stop with `next_owner = E7`.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e5-gate-b-lifecycle-execution-binding-producer-20260824`.

Write/push terminal `coordination/E5/STATUS.md` on that target branch with task_id `E5-20260824-023` and stop. Do not self-start E6 consumer work, E7 integration, approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, or LIVE.