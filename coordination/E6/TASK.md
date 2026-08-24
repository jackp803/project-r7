# E6 Current Task

- task_id: `E6-20260824-018`
- issued_at: `2026-08-24T23:18:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-b-binding-consumer-traderesult-completeness-20260824`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`, ADR-0009, accepted PR #61/#63/#64, E7-052 blocker evidence, PM static review of unaccepted `E6-20260824-017`

## Objective

Remediate only the two bounded fail-closed defects found during PM static review of `E6-20260824-017`.

Do not redesign the accepted binding consumer, TradeResult contract, E5 lifecycle semantics, E4 execution truth, shared contracts, release gates, provider/private APIs, or PAPER/SHADOW/LIVE authority.

`E6-20260824-017` is **not yet PM-accepted or merged**. Continue on the same target branch and preserve all otherwise-correct E6-017 implementation/tests outside this remediation.

## Defect A — invalid recovered TradeResult graph can remain READY

Current branch behavior in `src/storage/_lifecycle_execution_binding.py` can map some settled-contract reference-graph validation failures to:

```text
TRADE_RESULT_REFERENCED_GRAPH_INVALID
```

but `augment_recovery_with_binding_and_trade_result()` does not currently downgrade recovery status for that generic invalid reason. Therefore a pre-existing/legacy durable TradeResult with an invalid referenced graph can retain an underlying `READY` recovery claim.

Required fix:

- every TradeResult reference-graph validation failure must be non-READY on recovery;
- preserve deterministic severity where possible:
  - identity/lineage mismatch or conflict -> `CONFLICT`;
  - missing/incomplete/invalid/duplicate/unused/shape-invalid referenced graph -> `INCOMPLETE` or another existing stricter non-READY state;
- `TRADE_RESULT_REFERENCED_GRAPH_INVALID` itself must never coexist with `READY`;
- preserve existing binding freshness, Position re-attestation, UNKNOWN/reconciliation and funding rules.

Do not weaken validation merely to avoid the generic reason.

## Defect B — referenced PositionAction lineage is not fully mandatory

Current E6-017 reference-graph validation checks some PositionAction lineage fields only when the persisted value is non-null. E6 durable storage from the earlier slice can contain a PositionAction row whose minimal storage metadata exists while contract-required authority lineage is absent.

For a TradeResult reference graph, missing required authority lineage must fail closed rather than be skipped.

Mechanically enforce the settled profiles:

### `PROTECT / PROTECTION_STOP`

The referenced `protection-v0.1` PositionAction must have and exactly match the applicable parent/result lineage, including at minimum:

```text
position_id
trade_plan_id
risk_decision_id
risk_policy_version
symbol
action = PROTECT
protection_profile_version = protection-v0.1
```

### `EXIT / POSITION_EXIT` and `EMERGENCY_EXIT / EMERGENCY_EXIT`

The referenced `close-v0.1` PositionAction must have and exactly match the applicable parent/result lineage, including at minimum:

```text
position_id
trade_plan_id
risk_decision_id
risk_policy_version
strategy_id
strategy_version
symbol
action
close_profile_version = close-v0.1
```

Continue to validate the exact `position_action_id` / `order_role` authority reference and request/fill linkage.

E6 is performing contract-shape/identity/lineage validation only. Do not infer a PositionEvent or lifecycle transition from these fields.

## Required deterministic regression definitions

Add/update E6-owned storage tests proving at minimum:

1. a storage-level legacy/pre-fix TradeResult row whose reference graph fails with a generic invalid/duplicate/unused/shape reason cannot recover `READY`;
2. an existing referenced PROTECT PositionAction with a contract-required lineage field absent -> TradeResult persist/recovery fails closed;
3. an existing referenced EXIT or EMERGENCY_EXIT PositionAction with required parent/strategy/policy lineage absent or mismatched -> fails closed;
4. mismatch/conflict remains `CONFLICT` and missing/invalid completeness remains non-READY;
5. the valid complete closed graph from E6-017 remains definition-compatible;
6. all E6-017 lifecycle execution-binding freshness definitions remain unchanged/compatible.

Where current public persistence APIs correctly reject creation of the legacy-invalid row, a deterministic storage-level fixture/direct SQLite setup may represent a database produced before this remediation. Do not weaken the public API to construct the fixture.

## Writable scope

E6-owned only:

- `src/storage/**`;
- `tests/storage/**` and strictly necessary `tests/platform/**`;
- E6-owned status/handoff evidence;
- `coordination/E6/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / `docs/adr/**`;
- E1-E5/E7 production/tests;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- strategy promotion;
- PAPER/SHADOW/LIVE authorization.

If the settled profiles are insufficient to determine any required field mechanically, stop with `BLOCKED / CONTRACT_OR_SEMANTIC_GAP`, `next_owner = E7`, and exact evidence. Do not guess.

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

- no TradeResult referenced-graph validation failure can leave recovery `READY`;
- contract-required referenced PositionAction lineage is mandatory rather than optional;
- valid E6-017 binding freshness and complete-graph behavior is preserved;
- deterministic regression definitions are committed;
- no shared-contract/provider/private/CI/release scope is crossed;
- executable evidence is approved-local exact evidence or explicit `NOT_RUN` with commands;
- no Restart/persistence PASS, Paper E2E PASS, Gate B/PAPER_READY PASS, or PAPER/SHADOW/LIVE authorization is claimed.

### BLOCKED

If the fix requires undefined shared semantics or changing E5/E4 authority, record exact evidence, set `next_owner = E7`, and stop.

## Completion / mailbox rule

Commit/push the bounded remediation and terminal `coordination/E6/STATUS.md` with task_id `E6-20260824-018` to `agent/e6-gate-b-binding-consumer-traderesult-completeness-20260824` and stop.

Do not self-start E7 integration, approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, LIVE, or another task.