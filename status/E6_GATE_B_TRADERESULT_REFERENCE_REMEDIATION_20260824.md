# E6 Gate B TradeResult Reference Remediation — E6-20260824-018

## Authority / scope

- task_id: `E6-20260824-018`
- agent: `E6`
- target_branch: `agent/e6-gate-b-binding-consumer-traderesult-completeness-20260824`
- authoritative main read: `575e43a7aabb9b09cb161a2ce9b9b449e49fdcd6`
- wake/main task_id match: `YES`
- parent unaccepted E6-017 terminal head: `d94432de7462064bb84b566043a1e368a4f5474f`
- contracts/ADR changed: `NONE`
- E1-E5/E7 production/tests changed: `NONE`

This remediation changes only the two PM-identified E6-017 fail-closed defects. The accepted lifecycle-execution-binding producer/consumer contract, E5 lifecycle authority, E4 execution truth, funding behavior, raw Position freshness, reconciliation behavior, and release authority remain unchanged.

## Defect A remediation — recovered invalid TradeResult graph

The supported `storage.runtime` surface now routes TradeResult persistence/recovery through a bounded E6 remediation validator layered on the E6-017 reference-graph validator.

Recovery preserves the existing deterministic reason where possible and applies fail-closed severity:

```text
identity / lineage mismatch or conflict -> CONFLICT
missing required reference / lineage    -> INCOMPLETE when underlying status was READY
generic duplicate / unused / shape-invalid graph
                                      -> TRADE_RESULT_REFERENCED_GRAPH_INVALID
                                      -> INCOMPLETE when underlying status was READY
```

Therefore `TRADE_RESULT_REFERENCED_GRAPH_INVALID` cannot coexist with a final `READY` recovery claim.

Existing stricter non-READY states such as reconciliation/re-attestation are preserved rather than cosmetically rewritten.

## Defect B remediation — mandatory referenced PositionAction lineage

After the E6-017 request/fill/reference shape validation succeeds, E6 now additionally requires the settled authority lineage on every TradeResult-referenced PositionAction.

For `PROTECT / PROTECTION_STOP`, the durable action must contain and exactly match:

```text
position_id
trade_plan_id
risk_decision_id
risk_policy_version
symbol
action = PROTECT
protection_profile_version = protection-v0.1
```

For `EXIT / POSITION_EXIT` and `EMERGENCY_EXIT / EMERGENCY_EXIT`, the durable action must contain and exactly match:

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

Missing required lineage fails closed as incomplete/invalid; mismatched lineage fails closed as conflict. E6 performs only contract-shape/identity/lineage checks and does not infer PositionEvent, lifecycle transition, protection state, close success, or emergency semantics.

## Deterministic regression definitions

`tests/storage/test_paper_runtime_reference_remediation.py` defines:

1. a direct-storage legacy TradeResult with duplicate referenced Fill IDs cannot recover READY and yields generic invalid + INCOMPLETE;
2. referenced PROTECT action missing required policy lineage is rejected before TradeResult persistence;
3. referenced EXIT action missing required strategy lineage is rejected;
4. referenced EMERGENCY_EXIT action with mismatched policy lineage is rejected;
5. a recovered durable PositionAction lineage mismatch yields CONFLICT;
6. a recovered durable PositionAction missing required lineage yields non-READY INCOMPLETE;
7. the valid complete E6-017 closed graph remains definition-compatible.

The existing `test_paper_runtime_binding_and_traderesult_completeness.py` definitions are not modified by this task and remain the regression surface for lifecycle execution-binding freshness, exact replay, new/different request/result/fill evidence, re-attestation, independent raw Position freshness, and entry-v0.1 scope exclusion.

## Verification

```text
local_verification = NOT_RUN
```

No separate exact-revision Product-Owner/PM-approved local action was authorized. No project tests, migrations, restart runtime, provider/private request, GitHub Actions/CI/hosted runner, GitHub-triggered compute, or other project executable workload was run.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## Release / safety boundary

- Restart/persistence PASS: `NOT CLAIMED`
- Paper E2E PASS: `NOT CLAIMED`
- Gate B / PAPER_READY PASS: `NOT CLAIMED`
- PAPER / SHADOW / LIVE authorization: `NONE`
- provider/private API/network/credentials: `NONE`
- GitHub Actions/CI/hosted compute: `NONE`

E6 stops after terminal status/mailbox persistence for this task.
