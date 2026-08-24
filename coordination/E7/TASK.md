# E7 Current Task

- task_id: `E7-20260824-036`
- issued_at: `2026-08-24T12:44:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-close-trade-result-contract-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A evidence PR #33, Gate B static preflight PR #34, protection chain PR #37-#44, accepted E4 protection Fill-lineage PR #45

## Objective

Perform the bounded E7 **cross-module close-to-TradeResult architecture/contract decision** now that protection-origin PaperBroker Fill lineage is materialized.

Determine the exact provider-neutral authority and truth chain required to move from an open E5-managed Position through an ordinary or emergency close to canonical `TradeResult`, without allowing E4 to invent risk/exit authority or E5/E6 to invent broker truth.

This task is architecture/contract/static-review work only. Do not implement E4/E5/E6 production behavior and do not execute project code.

## Accepted prerequisite state

```text
PR #45
merge = e18fc08d110b0addb77229b1bf47cd7632548427
head = f8f85923a7dea0c47d7e5f1da46bc0c92a462368
PaperBroker protection Fill lineage = MATERIALIZED
local executable verification = NOT_RUN

Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Restart/persistence = BLOCKED
Paper E2E / TradeResult durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

All prior `NOT_RUN` remains `NOT_RUN`.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/SHARED_CONTRACTS_V1.md`, execution/protection profiles and ADR-0004;
- canonical `TradeResult`, `Position`, `PositionAction`, `OrderRequest`, `OrderResult`, and `Fill` semantics;
- E5 position state machine and current protection producer/result bridge;
- E4 execution gateway, protection translator, execution models, current PaperBroker and PR #45 Fill-lineage behavior;
- E6 current storage/runtime persistence surface;
- `status/RELEASE_GATES.md` and latest Gate B review artifacts.

Independently determine whether the current shared contracts are sufficient for an executable close path. Do not assume that baseline enum names such as `EXIT`, `EMERGENCY_EXIT`, or `POSITION_CLOSED` already define a safe executable payload.

## Required architecture decisions

Resolve at minimum the following boundaries.

### 1. Exit authority

Define how E5 authorizes ordinary `EXIT` and `EMERGENCY_EXIT` from exact current Position truth, including required lineage, actual close quantity, side, position observation/reconciliation state, reason codes, freshness/expiry semantics, and risk-policy binding.

The decision must ensure:

- close quantity follows actual known open exposure, not original requested entry quantity;
- an exit action cannot create or increase exposure;
- E4 may validate/reject authority but may not choose a larger quantity or invent an exit reason;
- unknown/mismatched/reconciliation-required position truth fails closed;
- ordinary exit and emergency exit remain distinguishable and auditable.

### 2. E4 mechanical close translation

Define the provider-neutral mapping from an E5-authorized close action to canonical `OrderRequest` and the required immediate-authority lineage.

Decide exact order-role vocabulary, idempotency identity, reduce-only semantics, side mapping, quantity source, and supported order type/profile for the bounded Paper path. Do not add provider-native OKX/Pionex fields.

### 3. Close Fill truth and lifecycle closure

Define how E4 exit/protection-trigger fills become authoritative close facts for E5 Position lifecycle.

Address at minimum:

- ordinary explicit exit fills;
- emergency exit fills;
- a protective stop Fill that itself reduces/closes the position;
- partial close versus complete flat position;
- prevention of double counting the same Fill/order truth;
- when `POSITION_CLOSED` is allowed versus when reconciliation remains required.

A `FILLED` order alone must not be treated as proof of a flat position if authoritative position truth is inconsistent or unknown.

### 4. Canonical TradeResult production boundary

The baseline says `TradeResult` is produced by the integrated E4/E5 close path. Define the exact inputs and closure prerequisites needed to construct one canonical result, including:

- exact strategy/version, trade_plan_id, position_id and risk-policy lineage;
- authoritative entry Fill set and exit Fill set;
- opened_at / closed_at source;
- entry quantity and average entry price;
- average exit price;
- gross PnL / net PnL / total fees and optional funding/slippage semantics;
- deterministic exit reason codes from E5 lifecycle authority;
- stable TradeResult identity/idempotency;
- explicit rule that incomplete, ambiguous, duplicated, or unreconciled Fill/Position evidence cannot produce a final TradeResult.

Do not fabricate finance formulas or cost semantics if the current baseline is underspecified; version/profile them explicitly or return a blocker.

### 5. Contract/profile decision

Classify the current baseline as exactly one of:

```text
BASELINE_SUFFICIENT_WITH_STATIC_MAPPING
ADDITIVE_PROFILE_REQUIRED
CONTRACT_OR_SEMANTIC_GAP
```

If an additive E7-owned profile/ADR is required to make the boundary executable, materialize only the minimum provider-neutral contract/profile and registry/ADR changes needed. Preserve `schema_version = contracts-v0.1` only if compatibility is genuinely additive; otherwise stop on a precise versioning blocker rather than forcing compatibility.

Do not implement E4/E5/E6 production code in this task.

### 6. Safe implementation dependency order

After the architecture decision, identify exact bounded next owners in dependency order. Distinguish at least:

- E5 close-action producer/lifecycle semantics;
- E4 close-order consumer and Fill truth;
- integrated TradeResult construction ownership/boundary;
- E6 durable runtime persistence/restart/audit;
- E7 Paper E2E definitions;
- later approved-local Gate B verification.

Do not assign multiple workers concurrently when one interface depends on another unfinished interface.

## Gate B evidence rule

This task may refine blockers/dependency text only where justified. It must not convert any executable `NOT_RUN` to PASS.

At completion, at minimum:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Restart/persistence = BLOCKED unless new implementation already exists
Paper E2E / TradeResult durable audit = BLOCKED unless the full implementation already exists
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

## Writable scope

E7-owned paths only:

- `contracts/**` only if the decision requires an E7-owned additive profile/version clarification;
- `docs/adr/**` only for the bounded close/TradeResult architecture decision;
- `status/e7/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md` for blocker/dependency reconciliation;
- `tests/integration/**` / cross-module `tests/safety/**` only if static definitions are necessary to express the decided boundary;
- `coordination/E7/STATUS.md` on the target branch.

Do not modify E1-E6 production code or domain-owned unit tests.

## Executable verification

This task is **STATIC / CONTRACT / ARCHITECTURE ONLY**.

Do not run project code and do not request Local Runner actions. Record:

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

No GitHub Actions/CI/hosted runner/GitHub-triggered compute, Computer Adapter, provider/private API, credentials, PAPER, SHADOW, or LIVE activity.

## Acceptance

### DONE

- the safe close-to-TradeResult authority/truth boundary is explicitly resolved;
- current contracts are classified and any minimum E7-owned profile/ADR needed is materialized without hidden domain implementation;
- ordinary exit, emergency exit, protection-triggered close, partial close, authoritative flatness, and TradeResult closure are unambiguous enough for bounded E5/E4/E6 implementation tasks;
- exact dependency order and next owner are identified;
- Gate B remains correctly BLOCKED and prior `NOT_RUN` remains `NOT_RUN`.

### BLOCKED

- a genuine semantic/versioning contradiction prevents a safe decision within the baseline;
- record exact expected-vs-actual contract evidence and affected producers/consumers;
- do not patch E4/E5/E6 production to hide it.

## Completion / mailbox rule

Commit/push bounded E7 contract/ADR/evidence/status changes to `agent/e7-gate-b-close-trade-result-contract-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E7/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E5/E4 implementation, E6 persistence, full Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.