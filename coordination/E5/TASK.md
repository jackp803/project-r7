# E5 Current Task

- task_id: `E5-20260829-031`
- issued_at: `2026-08-29T16:32:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-fp04-fp10-lifecycle-consumer-20260829`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, accepted `external-provider-object-ownership-reconciliation-v0.1`, accepted `external-manual-close-lifecycle-convergence-v0.1`, accepted Position lifecycle/execution-binding profiles, `status/PM_E7_109_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest **provider-neutral E5 lifecycle consumer / reinterpretation boundary** required by FP-04 + FP-10 so external/manual/prior-generation exposure changes, positive residuals, contradictory execution/fill evidence, and non-converged terminal protection cannot silently produce a green/closed lifecycle state.

This task may modify only E5-owned source/tests/status. It must not modify shared contracts, E4 provider/broker code, E6 persistence, AgentBridge, provider configuration, credentials, runtime authorization, or capital/live settings.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E5_RISK_POSITION.md`;
- current E5 Position lifecycle implementation and tests;
- accepted Position lifecycle projection/execution-evidence profiles;
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md` only as an input evidence dependency;
- accepted E4 `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md` only as provider-local evidence vocabulary, without importing provider semantics into E5;
- `status/PM_E7_109_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Implement provider-neutral deterministic E5 functions/types under existing E5-owned paths, using the accepted shared profiles as authority.

At minimum provide:

1. validation/currentness checks for accepted FP-04 ownership/reconciliation evidence relevant to the Position/exposure interpretation;
2. validation/currentness checks for accepted FP-10 convergence evidence;
3. a deterministic E5 reinterpretation decision/consumer that maps valid current evidence into an E5-owned lifecycle response without manufacturing provider truth;
4. explicit fail-closed outcomes for unknown/stale/conflicting evidence;
5. deterministic reason codes / decision identity consistent with existing E5 conventions;
6. no network/provider/credential dependency.

Do not create a parallel shared contract. If existing shared evidence lacks a field genuinely required for deterministic E5 behavior, record the exact E7 change request and stop at PARTIAL rather than inventing it.

## Required semantic behavior

### Flatness / close eligibility

- `LIFECYCLE_CLOSE_ELIGIBLE` is input evidence only; E5 remains the transition owner.
- E5 may produce the existing accepted flat/closed lifecycle event/transition only when the exact current FP-10 evidence is valid and compatible with the exact current lifecycle authority.
- Terminal/FILLED order status alone must never close lifecycle.
- Missing local Position rows, zero pending orders, requested quantity arithmetic, or stale local ledger state must never close lifecycle.
- Positive exposure remains open.
- FP-05 `RESIDUAL_NONZERO_REPRESENTABLE` and `RESIDUAL_NONZERO_UNREPRESENTABLE` remain non-flat.

### External/manual/prior-generation exposure truth

- External/manual provider truth must not be silently adopted as current-generation execution lineage.
- A newer external/manual reduction/flatness observation must first produce/reuse the accepted E5 reinterpretation path required by FP-10.
- Current provider Position truth may change E5 lifecycle interpretation even when execution lineage remains external/manual, but only through current compatible FP-04/FP-10 evidence.
- Unknown/conflicting/external ownership states that require reconciliation/manual review must remain fail closed and must not create new exposure or mutation authority.

### Execution/fill ambiguity

- Contradictory or incomplete execution/fill evidence must not be discarded merely because provider Position is flat.
- If FP-10 requires execution/fill reconciliation, E5 must remain in a reconciliation/hold-safe lifecycle response rather than force `CLOSED`.
- TradeResult evidence completeness is separate from lifecycle flatness; E5 must not fabricate missing Fill/OrderRequest lineage.

### Protection convergence

- Flat exposure does not erase protection truth.
- Non-converged terminal protection evidence must block terminal lifecycle convergence where FP-10 requires it.
- E5 must not choose provider cleanup/cancel targets from FP-11/FP-10 evidence and must not authorize blind cancel-all.

### Currentness / supersession

A materially newer relevant input must invalidate any prior E5 reinterpretation decision, including newer:

- provider/normalized Position truth;
- FP-04 ownership/reconciliation evidence;
- FP-10 convergence evidence;
- lifecycle projection/execution binding;
- runtime/process/config generation where represented by accepted shared evidence.

A later evaluation timestamp alone must not refresh stale evidence.

## Required tests to define

Add deterministic E5-owned tests covering at minimum:

- terminal close order but Position still positive -> no close;
- partial/manual reduction -> lifecycle remains open/reinterpreted, not closed;
- positive representable residual -> no close;
- positive non-representable residual -> explicit fail-closed non-flat response;
- current valid FP-10 `LIFECYCLE_CLOSE_ELIGIBLE` + compatible current lifecycle authority -> existing accepted E5 flat/close transition path;
- flat provider truth + execution/fill reconciliation required -> no forced close;
- flat provider truth + non-converged terminal protection -> no terminal close convergence;
- external/manual flat truth -> reinterpretation path without silent execution-lineage adoption;
- stale/mismatched FP-04 evidence -> fail closed;
- stale/mismatched FP-10 evidence -> fail closed;
- newer provider/FP-04/FP-10/lifecycle truth invalidates prior reinterpretation decision;
- missing local Position row != flat;
- no pending order != flat;
- TradeResult evidence incomplete does not cause fabricated execution lineage;
- deterministic provider-free fixtures only.

Where appropriate, add E5 safety tests under `tests/safety/` for false-green closure prevention.

## Verification boundary

All executable verification is local-only. The current LF-0 approved-local exact-revision preparation dependency remains blocked.

Therefore, unless an already-approved local execution path is independently available to this worker under current authoritative evidence:

```text
project executable verification = NOT_RUN / NOT PASS
```

Record the exact commands that must later run locally, for example the relevant bounded `tests/position`, `tests/risk`, and `tests/safety` suites. Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

No provider/network/private API/credential access is needed or authorized.

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

`NOT_RUN` is not PASS.

## Required durable evidence

Create:

`status/E5_FP04_FP10_LIFECYCLE_CONSUMER_20260829.md`

Document:

- task ID;
- exact source/test files changed;
- accepted profiles consumed;
- deterministic lifecycle reinterpretation semantics;
- fail-closed/currentness behavior;
- exact tests defined;
- local commands and result (`NOT_RUN` if unavailable);
- known limitations / downstream E4/E6/E7 needs;
- no provider/credential/runtime/capital authority.

Update `coordination/E5/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E5-owned paths:

- `src/position/`
- `src/risk/` only if a minimal shared E5 helper is genuinely required by existing architecture;
- `tests/position/`
- `tests/risk/` only if directly required;
- `tests/safety/` for E5-owned false-green/reconciliation scenarios;
- `status/E5_FP04_FP10_LIFECYCLE_CONSUMER_20260829.md`;
- `coordination/E5/STATUS.md`.

Do not modify:

- `contracts/**`;
- E4/E6/E7 implementation or docs;
- provider adapter/broker code;
- AgentBridge/local action catalog;
- provider credentials/config/private allowlists;
- Product Owner authorization artifacts;
- risk limits/leverage/capital thresholds;
- release criteria;
- GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if the bounded implementation/test definitions are complete **and** all required executable verification was actually performed on an approved local environment with PASS evidence.

### PARTIAL

Use PARTIAL when source/test implementation is complete but executable verification remains `NOT_RUN`, or when a precise cross-contract dependency prevents full completion without inventing semantics.

### BLOCKED

Use BLOCKED only if authoritative repository requirements are contradictory or implementation cannot safely proceed within E5 scope.

## Completion

Read latest `main`, verify wake task ID `E5-20260829-031`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start E4 provider work, E6 persistence, E7 integration, exact-revision preparation, requalification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
