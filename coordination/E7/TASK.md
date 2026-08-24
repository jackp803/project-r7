# E7 Current Task

- task_id: `E7-20260824-028`
- issued_at: `2026-08-24T10:50:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-protection-contract-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A evidence PR #33, Gate B static preflight PR #34, E5 risk-limit evidence PR #35, E5 actual-fill protection blocker PR #36

## Objective

Resolve the shared contract/semantic blocker that prevents the Gate B actual-fill protection path from being safely implemented across E5 -> E4.

Accepted blocker:

```text
E5-20260824-008
state = BLOCKED
blocker = CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Authoritative blocker evidence:

```text
PR #36
merge = d4467e50d300114401b7fda6d5d9f8b688d82638
artifact = status/E5_GATE_B_FILL_PROTECTION_BLOCKER_20260824.md
```

Current release state remains:

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

This is a contract/architecture task. It is not an E4/E5 implementation task and does not authorize Paper runtime or provider/private API activity.

## Required inspection

Read latest `main` and at minimum:

- `agents/README.md` and `agents/E7_INTEGRATION.md`;
- `contracts/SHARED_CONTRACTS_V1.md`;
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`;
- relevant ADRs;
- `status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md`;
- `status/E5_GATE_B_FILL_PROTECTION_BLOCKER_20260824.md`;
- current E5 `ApprovedTradePlan` / position lifecycle semantics;
- E4 `src/execution/models.py` and `src/execution/gateway.py` as read-only producer/consumer evidence;
- current shared `OrderRequest`, `Fill`, `Position`, and `PositionAction` semantics.

Do not assume the blocker report's suggested field names are the final design. E7 owns the contract decision.

## Required contract decision

Define the minimum shared/provider-neutral semantics needed for this chain:

```text
actual broker/replay fill/open exposure truth
-> E5 provider-neutral protection authorization
-> E4 mechanical executable request translation
-> broker result/fill/reconciliation
-> E5 lifecycle verification/failure handling
```

The accepted design must unambiguously cover at least:

1. **Actual protective quantity**
   - protection quantity is derived from known actual filled/open exposure, never merely requested quantity;
   - partial fills are representable without ambiguity;
   - zero/negative/unknown/unreconciled quantity fails closed;
   - actual exposure above the E5-approved maximum cannot silently expand risk authority.

2. **Canonical quantity semantics**
   - define whether `PositionAction` carries explicit `quantity_profile_version / quantity_unit / quantity_asset` fields, or an equally unambiguous normative binding to the existing `base-asset-v0.1` semantics;
   - provider-native contract counts/OKX `sz` remain E4 adapter facts, not E5/shared protection quantities.

3. **Approved protection-bound binding**
   - protection authorization must preserve the already-approved E5 stop/target/max-hold/risk bounds from the exact approved plan/policy;
   - ordinary protection modification must never loosen loss risk without a new authorized E5 decision under an explicitly supported policy;
   - define the minimum traceability needed to prove which `trade_plan_id`, `risk_decision_id`, risk policy, and position/execution truth the action is bound to.

4. **E4 request traceability / authority**
   - resolve the current inconsistency where `OrderRequest` requires `trade_plan_id` while the shared rule also permits an E5-authorized position action;
   - define how an E4 executable protection/exit request identifies the authorizing `position_action_id` and its parent plan/risk lineage;
   - keep E4 translation mechanical: it may quantize/provider-map safely, but must not invent quantity, side, stop/target bounds, or risk authority.

5. **Protection action shape and lifecycle meaning**
   - define enough shared semantics for `PROTECT` and, if necessary for compatibility, `MODIFY_PROTECTION` to be consumed by E4;
   - distinguish "protection requested/submitted" from `PROTECTION_VERIFIED`;
   - preserve `OPEN_UNPROTECTED` until verification;
   - preserve existing `PROTECTION_FAILED` / `PROTECTION_LOST` -> `EMERGENCY` semantics for later implementation;
   - no direct request-created shortcut to `OPEN_PROTECTED`.

6. **Compatibility/versioning**
   - decide whether this is an additive compatible object-profile refinement under `contracts-v0.1` or requires a contract-version change;
   - explain backward compatibility for existing historical/research objects;
   - legacy objects without the new protection profile must fail closed for the new executable protection path rather than being guessed/upgraded in place.

## Deliverables

Persist an authoritative E7-owned contract/profile refinement sufficient for downstream E5 and E4 implementation. Use the smallest coherent change set.

Expected writable scope:

- `contracts/**`;
- `docs/adr/**` only if the change is material enough to require an ADR;
- E7-owned `status/e7/**` / `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only as needed to record the blocker resolution;
- `coordination/E7/STATUS.md`.

Do not modify E4/E5/E6 production implementation or their domain tests in this task. Do not implement provider adapters or Paper orchestration.

If contract test definitions are needed to make serialization/compatibility semantics explicit, they may be added only in E7-owned integration/shared-contract test scope and must not execute on GitHub.

## Static review requirements

Before declaring the blocker resolved, verify the contract design is sufficient for both downstream owners:

### E5 must be able to implement

```text
known actual fill/open exposure
-> bounded provider-neutral PositionAction/protection authorization
```

without inventing cross-module fields.

### E4 must be able to implement

```text
accepted E5 PositionAction
-> deterministic provider-neutral OrderRequest
```

without choosing risk quantity, loosening stop/target bounds, or guessing lineage/unit semantics.

Identify exact bounded follow-up tasks and owner order after the contract is accepted. Expected order is E5 producer implementation first, then E4 consumer/translation implementation, unless the reviewed contract demonstrates a safer dependency order.

## Executable verification

This task is primarily contract/static work. Do not execute project code merely to claim contract acceptance.

If executable contract tests are genuinely required and an exact-revision approved local action exists, use only that local-only path and record exact evidence. Otherwise:

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

`NOT_RUN` must not be represented as executable PASS.

Forbidden:

- GitHub Actions / CI / hosted runner / GitHub-triggered compute;
- arbitrary cloud execution;
- provider/private API requests;
- exchange credentials;
- Paper/Shadow/Live runtime.

## Acceptance

Allowed terminal outcomes:

### DONE

- shared contract/profile semantics are sufficient and authoritative for the actual-fill protection E5 -> E4 path;
- compatibility/versioning decision is explicit;
- no risk authority is weakened;
- actual quantity and approved protection bounds are unambiguous;
- OrderRequest/PositionAction traceability is coherent;
- lifecycle remains fail closed until protection verification;
- exact next bounded owners/tasks are identified;
- Gate B remains BLOCKED pending implementation and local evidence.

### BLOCKED

- a product/policy decision is required from Product Owner, or a deeper unresolved architecture conflict prevents a safe contract definition;
- exact unresolved decision is recorded without guessing.

Do not declare the actual-fill protection criterion PASS and do not declare Gate B/PAPER_READY PASS.

## Completion

Update `coordination/E7/STATUS.md`, commit/push the bounded contract/evidence changes to `agent/e7-gate-b-protection-contract-20260824`, and stop. Do not self-start E5/E4 implementation, Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.