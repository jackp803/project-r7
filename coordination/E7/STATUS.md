# E7 Status

- task_id: `E7-20260824-028`
- agent: `E7`
- state: `DONE`
- branch: `agent/e7-gate-b-protection-contract-20260824`
- wake_task_id_verified: `YES — latest main coordination/E7/TASK.md exactly matched E7-20260824-028 before work`
- reviewed_main: `6299df81c1fc0986e28f9fc6cd0a81fdb60d3a48`
- reviewed_task_blob: `8f54d1a28dc307645faa09ba7ef72a14dfcbe67b`
- contracts_baseline: `contracts-v0.1 / BASELINE`
- accepted_blocker: `E5-20260824-008 / CONTRACT_OR_SEMANTIC_GAP`
- blocker_pr: `#36 / merge d4467e50d300114401b7fda6d5d9f8b688d82638`
- blocker_artifact: `status/E5_GATE_B_FILL_PROTECTION_BLOCKER_20260824.md`
- contract_decision: `protection-v0.1 / ADDITIVE_COMPATIBLE_OBJECT_PROFILE`
- contract_set_version_bump: `NO`
- semantic_blocker: `RESOLVED BY CONTRACT`
- e5_downstream_sufficiency: `PASS STATIC`
- e4_downstream_sufficiency: `PASS STATIC`
- project_executable_verification: `NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION`
- local_job: `NOT_REQUESTED / NOT REQUIRED`
- github_compute: `NOT_USED`
- github_actions_ci_hosted_runner: `NOT_USED`
- provider_private_api: `NOT AUTHORIZED / NOT_SENT`
- exchange_credentials: `NOT_USED`
- paper_shadow_live: `UNAUTHORIZED`
- gate_a: `PASS / RESEARCH-INTEGRATION ONLY`
- gate_b: `BLOCKED / NOT YET PASS`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- actual_fill_protection_criterion: `BLOCKED pending E5/E4 implementation + local evidence`
- protection_failure_emergency_criterion: `BLOCKED pending implementation + local evidence`
- production_domain_changes: `NONE`
- domain_test_changes: `NONE`
- codex_ticket: `NONE`

## Persisted outputs

### Contract profile

`contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`

- commit: `ffc312098dc3bec326fc87a329c66d385d3cde6b`
- profile: `protection-v0.1`
- parent schema: `contracts-v0.1`
- exact actual protective quantity comes from known `Position.actual_quantity` with `reconciliation_status=CONSISTENT`;
- V1 quantity remains `base-asset-v0.1 / BASE_ASSET / BTC` for `BTC_USDT_PERP`;
- zero/unknown/unreconciled/mismatched or over-approved exposure fails closed for ordinary PROTECT;
- action binds exact `trade_plan_id`, `risk_decision_id`, risk policy, Position observation, quantity, and parent protection bounds;
- `MODIFY_PROTECTION` is not executable under this profile;
- parent `trade_plan_id` remains OrderRequest plan lineage, with additive immediate `position_action_id` authority lineage;
- protective request is deterministic `PROTECTION_STOP / STOP_MARKET / reduce_only=true`;
- request/submission is not `PROTECTION_VERIFIED`.

### ADR

`docs/adr/ADR-0004-actual-fill-protection-action-boundary.md`

- commit: `a6028bb7539045f64404c3cd50fd3c27ec1b1fb9`
- disposition: `ACCEPTED`
- records authority separation, actual-fill quantity decision, additive compatibility decision, OrderRequest lineage, lifecycle verification boundary, and rejected unsafe alternatives.

### Contract registry

`contracts/README.md`

- commit: `e9e715f4f410c394e2fbe819e041b47c62d21a5d`
- registers `PROTECTION_OBJECT_PROFILE_V0_1.md / protection-v0.1` as a compatible executable profile under `contracts-v0.1`.

### E7 decision evidence

`status/e7/GATE_B_PROTECTION_CONTRACT_DECISION_20260824.md`

- commit: `200081b0aa56f1e92ce30809affee18bee6b737b`
- records source/blocker evidence, compatibility reasoning, static producer/consumer sufficiency, release impact, and dependency-ordered follow-up boundaries.

## Contract decision

```text
actual broker/open exposure truth
-> E5 protection-v0.1 PositionAction.PROTECT
-> E4 deterministic protection OrderRequest
-> broker OrderResult/reconciliation
-> E5 PROTECTION_VERIFIED or failure lifecycle event
```

### Actual quantity

For ordinary initial protection:

```text
PositionAction.quantity = exact known canonical Position.actual_quantity
```

not requested entry quantity and not automatically the full ApprovedTradePlan quantity. Partial fills are therefore unambiguous.

The source Position must be `CONSISTENT`, positive, known, and exactly bound by position identity/observation/profile. An actual quantity above the parent ApprovedTradePlan maximum does not expand normal protection authority; it becomes an exceptional reconciliation/emergency condition.

### Approved bounds

For `PROTECT`, action stop/optional target/max-hold values equal the exact parent ApprovedTradePlan protection instruction. E4 may verify or reject; it cannot loosen or substitute those values.

V0.1 translates only the protective stop. Target/max-hold remain binding E5 lifecycle facts and are not silently converted into target/OCO/timer behavior.

### OrderRequest lineage

For a protection request:

```text
trade_plan_id      = parent plan lineage
authorization_type = POSITION_ACTION
position_action_id = immediate E5 executable authority
position_id        = exact position lineage
risk_decision_id   = exact parent risk lineage
order_role         = PROTECTION_STOP
```

Mechanical mapping:

```text
LONG -> SELL
SHORT -> BUY
order_type = STOP_MARKET
quantity = exact action canonical quantity
stop_price = exact approved stop
reduce_only = true
```

Provider-native contract counts/OKX `sz` remain downstream E4 adapter facts.

### Lifecycle

No action/request/submit shortcut exists to `OPEN_PROTECTED`.

```text
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
OPEN_UNPROTECTED + PROTECTION_FAILED   -> EMERGENCY
OPEN_PROTECTED/PROFIT_PROTECTED + PROTECTION_LOST -> EMERGENCY
```

Unknown/reconciliation-required truth cannot count as verified protection.

## Static downstream sufficiency

### E5 — PASS STATIC

A bounded E5 producer task can now implement:

```text
known CONSISTENT Position observation + exact ApprovedTradePlan
-> protection-v0.1 PositionAction.PROTECT
```

without inventing cross-module fields or provider units.

### E4 — PASS STATIC

After E5 materializes the producer, a bounded E4 consumer task can implement:

```text
PositionAction + exact parent ApprovedTradePlan + current normalized Position truth
-> deterministic protection OrderRequest
```

without selecting risk quantity, loosening bounds, or guessing lineage/unit semantics.

## Dependency order for PM tasking

E7 does not issue these tasks. Safe bounded order is:

1. E5 producer implementation for `protection-v0.1`.
2. E4 consumer/translation implementation after the producer shape exists.
3. E7 cross-module integration/safety test definitions after both interfaces materialize.
4. Explicitly authorized approved-local executable verification afterward.

## Verification / release safety

No project code was executed. No Local Job was requested. No GitHub Actions/CI/hosted runner, provider/private request, PaperBroker runtime, exchange credential, PAPER, SHADOW, or LIVE activity was used.

The shared semantic blocker is resolved, but neither the actual-fill protection release criterion nor Gate B is PASS.

## Completion

E7 completed only `E7-20260824-028` and stops on `DONE`. It does not start E5/E4 implementation, Paper E2E, provider/private work, Gate C, PAPER, SHADOW, LIVE, or another task automatically.
