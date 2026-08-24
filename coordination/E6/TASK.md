# E6 Current Task

- task_id: `E6-20260824-017`
- issued_at: `2026-08-24T22:55:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-b-binding-consumer-traderesult-completeness-20260824`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`, `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`, ADR-0007, ADR-0009, accepted E6 durability PR #61, accepted E7 blocker/review PR #62, accepted freshness contract PR #63, accepted E5 binding producer PR #64 merge `d36d1897ccb4ee06ed9a2dbf981dc4814d7a8541`

## Objective

Implement only the two bounded E6 durability repairs required before E7 may resume Gate B durable Paper integration review:

1. mechanically persist/validate/recover `position-lifecycle-execution-binding-v0.1` and fail closed when the current durable Position-linked execution snapshot differs from the latest E5 binding;
2. repair the settled-contract TradeResult durable referenced-object completeness defect identified by E7-052.

Do not redesign E5 lifecycle semantics, E4 execution truth, shared contracts, release gates, provider/private APIs, or PAPER/SHADOW/LIVE authority.

## Required baseline handling

Before editing:

- verify latest `main` `coordination/E6/TASK.md` task_id exactly matches `E6-20260824-017`;
- read latest `main`, including PR #63 contract/ADR and PR #64 E5 producer;
- preserve merged PR #61 durability behavior except where directly required by these two repairs;
- do not import E5 production transition logic into E6.

## Repair A — lifecycle execution binding consumer/recovery

E6 must support durable canonical `PositionLifecycleExecutionEvidenceBinding` under:

```text
schema_version = contracts-v0.1
lifecycle_execution_binding_profile_version = position-lifecycle-execution-binding-v0.1
execution_scope = POSITION_LINKED_REDUCTION_ORDERS_V0_1
```

Required behavior:

- persist immutable binding identity and exact canonical payload;
- enforce exactly one non-conflicting binding per lifecycle projection intended for restart authority;
- mechanically validate binding position/projection/revision/interpreted-time/profile/scope/hash identity;
- recompute the current durable execution snapshot from canonical Position-linked `OrderRequest` roles `PROTECTION_STOP | POSITION_EXIT | EMERGENCY_EXIT`, all durable `OrderResult` observations, and all durable matching `Fill` objects using the exact PR #63 canonical hash/count/order rules;
- compare exact recomputed snapshot equality against the latest E5 binding;
- any missing binding, missing referenced object, new/different in-scope request/result/fill, hash mismatch, identity/time/lineage conflict, or unsupported profile/scope must prevent `READY` / restart-authoritative recovery;
- use an E6 diagnostic such as `E5_EXECUTION_REINTERPRETATION_REQUIRED` when the durable snapshot is newer/different, without inferring the next lifecycle state;
- preserve the independent raw Position broker-freshness / E5 re-attestation rule from PR #61;
- preserve existing UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED fail-closed behavior.

E6 must not:

- infer `PositionEvent`, `OPEN_PROTECTED`, `EMERGENCY`, `CLOSED`, protection loss, exit success, or other E5 semantics from order/fill status;
- import/copy the E5 transition table;
- associate excluded pre-position entry evidence heuristically by `trade_plan_id`;
- allocate lifecycle revisions or binding authority.

## Repair B — TradeResult referenced-object completeness

Under the already accepted close/TradeResult contracts, a closed durable graph must not recover `READY` merely because parent ApprovedTradePlan and FundingAllocationEvidence exist.

Before accepting/persisting or treating a canonical TradeResult as a complete restart-ready closed graph, E6 must require every exact TradeResult-referenced execution/lifecycle object that the accepted TradeResult profile declares, including referenced:

- entry `OrderRequest` objects;
- exit/protection `OrderRequest` objects;
- referenced `Fill` objects;
- referenced exit/protection `PositionAction` objects;

and verify their exact IDs/lineage against the TradeResult and resolved trade/position lineage.

If any required referenced object is absent or mismatched, recovery must fail closed as incomplete/conflict and must not report `READY`.

Do not invent new TradeResult fields or semantics. If the accepted contract is insufficient to determine a required reference, stop with `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and exact evidence for E7.

## Required deterministic E6 test definitions

Add/update E6-owned storage tests covering at minimum:

### Binding consumer

1. valid latest projection + exact matching binding + unchanged durable execution snapshot remains eligible for normal recovery evaluation;
2. binding absent -> not READY;
3. binding projection/revision/time/profile/scope/hash mismatch -> fail closed;
4. later `PARTIALLY_FILLED`/`FILLED` protection OrderResult/Fill after binding -> old projection not READY;
5. later `CANCELED`/`EXPIRED`/`REJECTED` protection truth after binding -> old projection not READY;
6. new POSITION_EXIT or EMERGENCY_EXIT request/result/fill after binding -> old projection not READY until new E5 interpretation/binding;
7. equal canonical duplicate replay remains idempotent;
8. equal-time changed OrderResult, changed Fill identity, or changed OrderRequest identity remains conflict/fail closed;
9. equal-broker-anchor E5 REATTESTATION plus new matching binding restores freshness mechanically without E6 lifecycle inference;
10. newer raw Position broker observation remains independently re-attestation-required;
11. entry-v0.1 evidence remains outside the binding scope and is not heuristically joined.

### TradeResult completeness

12. closed graph with every TradeResult-referenced OrderRequest/Fill/PositionAction present and matching may continue normal recovery evaluation;
13. missing referenced entry OrderRequest -> not READY;
14. missing referenced exit/protection OrderRequest -> not READY;
15. missing referenced Fill -> not READY;
16. missing referenced PositionAction -> not READY;
17. referenced object exists but lineage/ID mismatches -> fail closed;
18. existing funding/TradeResult immutability and lifecycle durability tests remain definition-compatible.

Use canonical sanitized fixtures only.

## Writable scope

E6-owned only:

- `src/storage/**`;
- `tests/storage/**` and strictly necessary `tests/platform/**`;
- E6-owned durability docs/status evidence;
- `coordination/E6/STATUS.md` on the target branch.

Forbidden:

- `contracts/**`, `docs/adr/**`;
- E1-E5/E7 production code/tests;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- strategy promotion;
- PAPER/SHADOW/LIVE authorization.

## Executable verification

Local-only. Unless a separate exact-revision Product-Owner/PM-approved local action exists, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners/GitHub-triggered compute. `NOT_RUN != PASS`.

## Acceptance

### DONE

- E6 mechanically consumes the accepted PR #63/#64 binding without importing E5 lifecycle semantics;
- stale/new Position-linked execution evidence cannot leave an older lifecycle projection falsely `READY`;
- exact matching re-attested binding can restore the execution-freshness axis mechanically;
- TradeResult restart readiness requires complete exact referenced-object graph under the settled contract;
- deterministic regression definitions are materialized;
- PR #61 behavior outside the bounded repairs remains preserved;
- no shared-contract, provider/private, CI, release-promotion, or PAPER/SHADOW/LIVE scope is crossed;
- executable evidence is approved-local exact evidence or explicit `NOT_RUN` with commands;
- no Restart/persistence PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or PAPER/SHADOW/LIVE authorization is claimed.

### BLOCKED

If either repair requires undefined shared semantics, record exact evidence and `next_owner = E7`; do not guess.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e6-gate-b-binding-consumer-traderesult-completeness-20260824`.

Write/push terminal `coordination/E6/STATUS.md` on that target branch with task_id `E6-20260824-017` and stop. Do not self-start E7 integration, approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, or LIVE.