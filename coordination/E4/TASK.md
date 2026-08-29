# E4 Current Task

- task_id: `E4-20260829-031`
- issued_at: `2026-08-29T17:37:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp05-close-residual-sizing-implementation-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `okx-swap-action-role-capability-v0.1`, accepted `okx-swap-close-residual-sizing-v0.1`, accepted FP-04 ownership/reconciliation profile and merged E4 producer candidate, existing E5 `close-v0.1` PositionAction/current Position semantics, `status/PM_E4_030_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest deterministic **FP-05 OKX SWAP close/residual sizing evaluator and immutable provider-local sizing evidence** described by `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`.

This task is provider-free. It operates only on supplied in-memory/fixture facts. It must not call OKX or any network endpoint, read credentials, submit/cancel/amend/close orders, mutate provider/account state, retry an ambiguous close, start SHADOW/PAPER/live runtime, or infer unproven close-role capability/metadata semantics.

The evaluator produces sizing/representability evidence only. It does not dispatch an order and does not create E5 lifecycle authority.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`;
- `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`;
- current E4 close consumer / provider-neutral execution authority binding;
- current OKX deterministic sizing/metadata types only as repository evidence;
- accepted FP-04 ownership/reconciliation profile and merged E4 FP-04 producer/currentness helper;
- current E5 `close-v0.1` PositionAction and canonical Position quantity semantics;
- `status/PM_E4_030_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Add E4-owned deterministic functions/types that consume supplied facts and produce an immutable E4-local evidence object equivalent to `OKXCloseResidualSizingEvidence` under profile `okx-swap-close-residual-sizing-v0.1`.

At minimum bind:

1. exact action role `POSITION_EXIT | EMERGENCY_EXIT` and exact E5 PositionAction identity;
2. exact current canonical Position ID/observation/actual quantity and quantity profile/unit/asset;
3. exact current provider Position/reducible-exposure snapshot/ref/hash/generation/observation;
4. exact current FP-04 Position-exposure ownership evidence/ref/classification/reconciliation/currentness;
5. exact accepted FP-02 capability row/reference for the close role;
6. exact close-applicable instrument metadata generation/reference/freshness/applicability proof;
7. provider-local conversion/lot/step/min/max facts only when explicitly proven applicable to that close role;
8. raw provider close size, quantized provider close size and effective canonical close quantity when calculable;
9. sizing/residual state, deterministic reason codes, evaluation time and deterministic evidence ID/hash.

Do not create a new shared contract. This evidence remains E4/provider-local. If safe implementation needs an undefined shared field/semantic, record a precise E7 change request and stop at PARTIAL rather than inventing it.

## Required evaluation order / fail-closed behavior

Preserve the accepted FP-05 precedence:

1. validate exact E5 close action profile/role;
2. bind to exact current canonical Position observation and exact current quantity;
3. unresolved prior close outcome -> `RECONCILIATION_REQUIRED` before sizing;
4. FP-04 missing/stale/conflicting/external-without-accepted-disposition -> no sizing authority;
5. provider Position/reducible exposure unknown -> `REDUCIBLE_EXPOSURE_UNKNOWN`;
6. fresh authoritative zero exposure -> `EXPOSURE_ALREADY_FLAT`, with no close request produced;
7. provider/canonical exposure mismatch -> `RECONCILIATION_REQUIRED`;
8. unaccepted/unproven exact close-role FP-02 capability -> `CLOSE_CAPABILITY_UNPROVEN`;
9. missing/stale/conflicting/unproven close-applicable metadata -> `METADATA_STALE_OR_UNKNOWN`;
10. only then calculate bounded provider-native representability;
11. never round upward beyond authoritative reducible exposure or E5/current Position canonical authority;
12. after any future mutation, arithmetic remainder is not residual authority; a fresh provider Position observation is required.

No Spot-specific rule or ENTRY-only `minSz/maxMktSz/posSide/reduceOnly` assumption may be transplanted into close roles without an explicit accepted close-role applicability proof.

## Required sizing states

Implement the accepted provider-local vocabulary exactly:

- `FULLY_REDUCIBLE`
- `PARTIALLY_REDUCIBLE`
- `RESIDUAL_NONZERO_REPRESENTABLE`
- `RESIDUAL_NONZERO_UNREPRESENTABLE`
- `EXPOSURE_ALREADY_FLAT`
- `REDUCIBLE_EXPOSURE_UNKNOWN`
- `METADATA_STALE_OR_UNKNOWN`
- `RECONCILIATION_REQUIRED`
- `CLOSE_CAPABILITY_UNPROVEN`

These states are evidence/routing facts only and do not authorize provider mutation or lifecycle transition.

## Quantization / safety invariants

When calculable, require all of:

```text
provider_requested_close_size > 0
provider_requested_close_size <= exact authoritative provider reducible exposure
provider_effective_canonical_quantity <= E5-authorized close quantity
provider_effective_canonical_quantity <= exact current Position.actual_quantity
all role-proven step/lot constraints satisfied
all role-proven min/max constraints satisfied
```

If no positive valid provider size exists for positive fresh exposure, classify explicit `RESIDUAL_NONZERO_UNREPRESENTABLE`; do not round the residual to zero and do not create retry authority.

## Currentness / supersession

Provide deterministic currentness behavior so materially newer or changed action/Position/provider snapshot/FP-04/capability/metadata facts invalidate prior sizing evidence. A later `evaluated_at` alone must not refresh stale evidence.

If immutable supersession is represented, bind the exact prior sizing evidence identity and require same logical Position/role lineage.

## Required tests to define

Add provider-free E4-owned deterministic tests covering at minimum:

- exact current close action + Position + provider exposure + current FP-04 + proven close capability + close-applicable metadata -> `FULLY_REDUCIBLE` when exactly representable;
- valid strict subset -> `PARTIALLY_REDUCIBLE`;
- fresh post-action positive residual representable -> `RESIDUAL_NONZERO_REPRESENTABLE`;
- positive residual with no positive valid close size -> `RESIDUAL_NONZERO_UNREPRESENTABLE`, no retry authority;
- fresh exact zero provider/canonical exposure -> `EXPOSURE_ALREADY_FLAT`, no provider request size;
- unknown provider reducible exposure -> `REDUCIBLE_EXPOSURE_UNKNOWN`;
- stale/conflicting Position/provider/FP-04 -> fail closed;
- external/manual FP-04 without accepted close disposition -> fail closed;
- unproven POSITION_EXIT/EMERGENCY_EXIT capability -> `CLOSE_CAPABILITY_UNPROVEN`;
- ENTRY-only constraint evidence cannot satisfy close-role applicability;
- stale/missing close metadata -> `METADATA_STALE_OR_UNKNOWN`;
- unresolved prior outcome -> `RECONCILIATION_REQUIRED` and no sizing;
- quantization never exceeds provider reducible exposure or E5/current Position canonical authority;
- below-minimum/dust-style positive exposure is explicit unrepresentable unless close-role proof says otherwise;
- changed Position/provider/FP-04/capability/metadata invalidates old evidence;
- later timestamp alone does not refresh old evidence;
- deterministic evidence identity independent of mapping insertion order;
- zero provider/network/credentials/mutation surface.

Do not execute tests through GitHub.

## Verification boundary

All executable verification remains local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless independently approved local execution authority is explicitly available in current repository evidence:

```text
project executable verification = NOT_RUN / NOT_PASS
```

Record exact future Windows/local commands for the bounded FP-05 tests and relevant existing execution/broker/position regressions. `NOT_RUN` is not PASS.

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 = BLOCKED / UNCHANGED
LF-2 = NOT PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

## Required durable evidence

Create:

`status/e4/FP05_CLOSE_RESIDUAL_SIZING_IMPLEMENTATION_20260829.md`

Document task ID, exact source/test files changed, accepted design/profile inputs, evaluator/evidence semantics, sizing-state precedence, quantization/currentness/supersession behavior, exact tests defined, future local commands/result, known limitations/provider-specific facts still unresolved, and confirmation that no provider/credential/runtime/capital authority was used.

Update `coordination/E4/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E4-owned paths:

- `src/execution/`;
- `src/brokers/` only for deterministic provider-local sizing/metadata helpers without transport behavior;
- `tests/execution/`;
- `tests/brokers/` only if directly required;
- `status/e4/FP05_CLOSE_RESIDUAL_SIZING_IMPLEMENTATION_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not modify `contracts/**`, E5/E6/E7 code/docs, provider transport/auth/config/credentials, AgentBridge/local action catalog, release criteria, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if implementation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL

Use PARTIAL when implementation/test definitions are complete but executable verification remains `NOT_RUN`, or a precise accepted-contract/provider-capability dependency prevents safe completion without invented semantics.

### BLOCKED

Use BLOCKED only for contradictory authoritative requirements or a safety dependency that prevents bounded implementation within E4 scope.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-031`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start provider verification, mutation translation/dispatch, FP-11 cleanup, E7 integration/requalification, exact-revision preparation, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, order action, or capital movement/exposure.
