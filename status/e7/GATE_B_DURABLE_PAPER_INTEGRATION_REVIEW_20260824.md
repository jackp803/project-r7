# Gate B Durable Paper Integration Review — E7-20260824-052

## Authority / scope

- task_id: `E7-20260824-052`
- target branch: `agent/e7-gate-b-durable-paper-integration-review-20260824`
- reviewed main: `3c4d8f38aa16bf06cc4e448238f4469d83c6c7b4`
- authoritative TASK blob: `2b63846436628f0d8b53b9a8a7a4e29096471a35`
- contract baseline: `contracts-v0.1 / BASELINE`
- accepted in-memory Gate B integration: PR `#55 / merge d6302eb89b9319bfd00d5c26e315bd2fe1923b65`
- lifecycle projection contract: PR `#57 / merge 5b203ea2e4a235dfb4575626f15e2409b6674c59`
- E5 lifecycle projection producer: PR `#58 / merge f5bbeaf1daef1fdeda28ea6d12482b3b26018cc8`
- lifecycle vocabulary clarification: PR `#60 / accepted on main`
- E6 durability implementation: PR `#61 / merge 42f6d015ea5c9387983a822820dde211608a249e`
- project executable verification: `NOT_RUN`

This task is static integration/release-definition work only. E7 did not execute project code, tests, migrations, Paper runtime, Local Runner actions, GitHub Actions/CI, provider/private APIs, credentials, PAPER, SHADOW, or LIVE behavior.

## Terminal disposition

```text
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E6 durability implementation = MATERIALIZED / executable NOT_RUN
PR #61 lifecycle vocabulary remediation = PASS STATIC
PR #61 immutable/ordering/funding mechanics = PASS STATIC for inspected boundaries
Durable Paper E4 execution-truth -> E5 lifecycle freshness = BLOCKED / CONTRACT_OR_SEMANTIC_GAP
Durable TradeResult reference completeness = BLOCKED / E6 IMPLEMENTATION DEFECT
Restart/persistence executable criterion = BLOCKED pending semantic remediation + later local evidence
Paper E2E durable audit executable criterion = BLOCKED
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = NO
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

The blocker is not an executable test failure. No project code was run.

## Static compatibility confirmed

The following accepted boundaries are coherent by source review:

1. E6 stores canonical IDs/payloads and does not regenerate E4/E5 canonical identities on restart.
2. E4 remains the authority for OrderRequest/OrderResult/Fill and broker Position facts.
3. E5 remains the authority for lifecycle interpretation, lifecycle revision, predecessor, event, and projection identity.
4. E6 does not call the E5 state machine or infer lifecycle from Order/Fill/Action rows.
5. `position-lifecycle-projection-v0.1` revision/predecessor/broker-anchor/conflict rules are persisted mechanically.
6. PR #60 vocabulary membership is mirrored in E6 storage validation; unsupported state/event/kind fails closed without importing E5 production modules.
7. newer raw E4 Position observation beyond the newest E5 projection produces `E5_REATTESTATION_REQUIRED` and does not synthesize a merged canonical Position.
8. OrderResult observations are append-only and preserve exact requested vs filled quantity.
9. `UNKNOWN`, `RECONCILIATION_REQUIRED`, `DEGRADED`, and Position non-CONSISTENT truth produce fail-closed recovery diagnostics.
10. funding allocation identity/lineage conflicts are not last-write-wins, and an immutable TradeResult cannot be silently rewritten by a later financial object.
11. PR #61 adds no provider/private API, credentials, GitHub CI/Actions, strategy lifecycle promotion, PAPER/SHADOW/LIVE authorization, or release authority.

These are static source findings only, not executable PASS evidence.

## Primary blocker — lifecycle projection freshness is not bound to newer E4 execution truth

### Accepted authority model

The durable Position projection currently binds E5 lifecycle interpretation to the exact E4 broker Position observation using:

```text
lifecycle_source_broker_state_observed_at
== Position.broker_state_observed_at
```

This correctly handles newer raw Position truth through `REATTESTATION_REQUIRED`.

However, the profile contains no shared authoritative material identifying which relevant E4 execution observations have already been consumed by E5 lifecycle interpretation, for example:

```text
OrderResult observation identity/time/status
Fill identity/time/set
protection OrderRequest identity
or another versioned execution-evidence watermark/reference
```

Therefore a later E4 OrderResult/Fill can be newer than the current E5 lifecycle projection without being detectable as lifecycle-stale from the serialized projection itself.

### Current E5 semantics prove this matters

`src/position/protection_result.py` explicitly treats a verified protection order that later becomes:

```text
PARTIALLY_FILLED | FILLED
```

as requiring authoritative Position close truth and applies fail-closed `STATE_UNKNOWN` semantics. From `OPEN_PROTECTED`, this means lifecycle interpretation becomes `RECONCILIATION_REQUIRED` until E5 receives sufficient authoritative truth.

The same E5 bridge maps a later definitive inactive protection state such as:

```text
CANCELED | EXPIRED | REJECTED
```

after `OPEN_PROTECTED` to:

```text
PROTECTION_LOST -> EMERGENCY
```

Thus a previously valid `OPEN_PROTECTED` lifecycle projection is not automatically restart-current merely because no newer raw Position observation has been stored.

### Current E6 recovery rule is insufficient

`src/storage/_paper_runtime.py::recover()` marks lifecycle freshness stale only when a newer raw Position observation exists beyond the current projection anchor.

For OrderResult truth it adds `ORDER_RECONCILIATION_REQUIRED` only when current order truth is:

```text
order_status = UNKNOWN | RECONCILIATION_REQUIRED
or
execution_health_status = UNKNOWN | DEGRADED
```

A later `PARTIALLY_FILLED / HEALTHY` or `CANCELED / HEALTHY` protection observation therefore does not by itself prevent:

```text
PaperRuntimeRecovery.status = READY
PaperRuntimeRecovery.restart_authoritative = true
```

when the latest persisted E5 lifecycle projection still says `OPEN_PROTECTED`.

### Accepted E6 test demonstrates the mismatch

`tests/storage/test_paper_runtime_durability.py::_persist_open_protection_graph()` persists:

```text
Position revision 0 = OPEN_UNPROTECTED
Position revision 1 = PROTECTION_VERIFIED -> OPEN_PROTECTED
later protection OrderResult = PARTIALLY_FILLED / HEALTHY / filled_quantity=0.0004
actual protection Fill = 0.0004
no newer E4 Position observation
no newer E5 lifecycle projection
```

Then:

```text
test_close_reopen_recovers_exact_open_partial_fill_graph
```

explicitly expects recovery `status == READY` after close/reopen.

That expectation is incompatible with the current E5 interpretation boundary and the accepted protection/close contracts, which require partial protection execution with unresolved residual truth to fail closed/reconcile rather than remain restart-authoritative `OPEN_PROTECTED`.

### Why this is a shared semantic gap, not an E6-local enum bug

E6 cannot safely repair this by maintaining a private table such as:

```text
PARTIALLY_FILLED -> lifecycle stale
CANCELED -> lifecycle stale
FILLED -> lifecycle stale
...
```

because whether an E4 execution observation changes E5 lifecycle depends on order role, previous E5 state, reconciliation evidence, Position truth, and the E5 state machine. Copying those rules into E6 would make persistence a lifecycle interpreter and violate ADR-0007/ADR-0008.

Likewise E6 cannot use row arrival order or timestamps alone to claim that every newer execution observation has or has not been interpreted by E5.

The missing authority must therefore be resolved through an E7-governed shared durability rule/profile refinement that lets a serialized E5 lifecycle projection prove the execution truth boundary it has interpreted, or an equally explicit versioned fail-closed mechanism.

Classification:

```text
CONTRACT_OR_SEMANTIC_GAP
next technical owner for contract decision = E7
```

E7-052 does not broaden into designing that follow-up contract after discovering the blocker.

## E7 blocker test definitions

Added:

```text
tests/safety/test_gate_b_durable_lifecycle_freshness.py
```

Commit:

```text
47fe8d4adc6939370aba4c7080eee580333c790c
```

The definitions use real accepted production surfaces:

- E5 `build_position_lifecycle_genesis(...)`;
- E5 `build_position_lifecycle_transition(...)`;
- E5 `build_protect_position_action(...)`;
- E4 `prepare_protection_order(...)`;
- real `PaperBroker` submit/query/fill/cancel truth;
- E5 `interpret_protection_result(...)`;
- E6 `open_paper_runtime_journal(...)` close/reopen/recovery.

They define two required fail-closed cases without inventing a new reason code:

1. verified protection -> later real partial protection Fill/`PARTIALLY_FILLED` -> E5 says `STATE_UNKNOWN / RECONCILIATION_REQUIRED`; restart must not claim `restart_authoritative` while persisted lifecycle remains older `OPEN_PROTECTED`;
2. verified protection -> later real `CANCELED` -> E5 says `PROTECTION_LOST / EMERGENCY`; restart must not claim `restart_authoritative` while persisted lifecycle remains older `OPEN_PROTECTED`.

These definitions are intentionally `NOT_RUN`. Current source review predicts the final `assertFalse(recovery.restart_authoritative)` is not satisfied by PR #61; that prediction is static blocker evidence, not an executable FAIL result.

## Secondary defect — closed durable graph does not validate TradeResult reference completeness

A separate settled-contract implementation defect is visible in PR #61.

`trade-result-v0.1` requires exact audit references including:

```text
entry_fill_ids
exit_fill_ids
entry_order_request_ids
exit_order_request_ids
exit_authority_refs
funding_evidence_id
```

E6 `persist_trade_result()` validates parent ApprovedTradePlan and FundingAllocationEvidence binding, but does not mechanically require the referenced OrderRequest/Fill/PositionAction rows to exist and match the TradeResult reference sets before the result becomes durable/recoverable.

The accepted E6 closed-recovery fixture itself constructs a TradeResult referencing:

```text
entry_fill_ids = [fill-entry-e6-001]
entry_order_request_ids = [ordreq-entry-e6-001]
```

without persisting those referenced entry objects, yet `test_close_reopen_recovers_exact_closed_projection_funding_and_trade_result` expects `recovery.status == READY`.

This violates the task requirement that incomplete/corrupt durable graphs block healthy/reconciled claims and the accepted `trade-result-v0.1` exact-audit-lineage semantics.

Classification:

```text
IMPLEMENTATION_DEFECT_UNDER_SETTLED_CONTRACT
responsible domain = E6 storage
bounded fix boundary = E6 / Codex after PM scheduling
```

E7 does not edit E6 production/tests in this task.

## Release impact

Because the primary lifecycle-freshness issue is a shared semantic gap, the current durable Paper slice is not yet ready for approved-local Gate B verification as one coherent system.

Canonical state after E7-052:

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E6 durability implementation = MATERIALIZED / executable NOT_RUN
Position lifecycle vocabulary = RESOLVED STATIC
Durable E4 execution truth -> E5 lifecycle freshness = BLOCKED / CONTRACT_OR_SEMANTIC_GAP
TradeResult durable reference completeness = BLOCKED / E6 IMPLEMENTATION DEFECT
Restart/persistence executable criterion = BLOCKED pending remediation
Paper E2E durable audit executable criterion = BLOCKED pending remediation
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = NO
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No existing executable `NOT_RUN` criterion is converted to PASS.

## Required bounded next actions

E7 does not assign or start these actions.

Safe dependency order for PM consideration:

```text
1. E7 — define the minimum shared lifecycle execution-evidence freshness/binding rule
2. E5 — bind emitted lifecycle projections to that accepted execution-truth boundary
3. E6 — mechanically validate/recover that binding and remediate TradeResult durable-reference completeness
4. E7 — complete/update durable integration/E2E/safety definitions against remediated accepted surfaces
5. PM-approved local Gate B durable matrix
```

The E6 fix must not import/copy E5 transition semantics. The E5 fix must not take E4 broker truth authority. The E7 contract decision must preserve the existing E4/E5/E6 authority split.

## Future local-only verification

Not run in E7-052. After blockers are remediated and an exact revision is explicitly approved for local execution, the complete Gate B matrix should include at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

If `tests/e2e` remains absent at the accepted remediated revision, E7 must materialize that bounded definition surface before the executable matrix rather than silently treating the missing suite as PASS.

## Verification / security / scope

```text
project_executable_verification = NOT_RUN
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
strategy lifecycle promotion = NONE
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production/test changes by E7 = NONE
contracts / ADR changes by E7 = NONE in E7-052
```

## Completion

E7-052 stops on `BLOCKED`. E7 does not self-start the lifecycle-freshness contract follow-up, E5/E6 remediation, complete Paper E2E definitions, approved-local verification, Gate C, provider/private API work, PAPER, SHADOW, LIVE, or another task.
