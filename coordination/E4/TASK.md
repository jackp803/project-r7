# E4 Current Task

- task_id: `E4-20260829-028`
- issued_at: `2026-08-29T16:06:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp05-close-residual-sizing-design-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, accepted `okx-swap-action-role-capability-v0.1`, accepted FP-04/FP-11 shared profiles, `status/PM_E7_107_REVIEW_20260829.md`, mature-OKX failure-prevention baseline/audit

## Objective

Define the **FP-05 provider-native close/reducible/residual sizing design** for the current OKX BTC-USDT-SWAP target so later `POSITION_EXIT` and `EMERGENCY_EXIT` translation cannot use original requested entry quantity, over-reduce exposure, loop forever on an unrepresentable residual, or silently treat a provider-quantity mismatch as flat.

This is a docs/status-only E4 design task. It does not authorize executable source/test changes, provider/private API access, credentials, provider/account mutation, order submission/cancel/amend/close, SHADOW/PAPER runtime, capital exposure, 10U live-fire, Gate D, or LIVE.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- accepted `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- accepted E4 `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`;
- current shared Position / close / OrderRequest / execution-evidence profiles relevant to exit quantity authority;
- accepted `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md` only where current provider exposure ownership/reconciliation affects reducible quantity certainty;
- accepted `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md` only where post-close residual/protection convergence must remain explicit;
- current E4 sizing/provider adapter code and E4-owned tests as repository evidence only;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-05 and FP-10 rows;
- `status/PM_E7_107_REVIEW_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required design artifact

Create:

`docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`

Use profile identifier:

`okx-swap-close-residual-sizing-v0.1`

The design must remain E4/provider-local. Do not modify `contracts/**` or redefine E5 lifecycle/risk semantics. If a new shared cross-module authority field/profile is genuinely required, record a precise E7 change request in the handoff and stop at design completion.

## Required quantity-authority model

Define a deterministic hierarchy for exit sizing that distinguishes at minimum:

1. E5-authorized canonical close intent / PositionAction quantity semantics;
2. exact current authoritative canonical Position exposure actually observed/reconciled;
3. provider-native reducible exposure representation for the exact supported account/instrument/position-mode row;
4. current validated instrument metadata needed to convert canonical BTC exposure into provider-native close quantity units;
5. provider lot/minimum/step/max constraints relevant to close/reduce operations;
6. quantized provider-native requested close size;
7. post-action provider observation of remaining actual exposure;
8. representable vs non-representable residual state.

Original requested ENTRY quantity, original planned quantity, stale local quantity, or arithmetic remainder from a prior request must never override newer authoritative actual Position/provider exposure truth.

## Required fail-closed sizing semantics

The design must explicitly prevent:

- closing from original requested entry quantity instead of actual current exposure;
- treating entry-sizing compatibility as proof of close-sizing compatibility;
- rounding a close quantity upward beyond authoritative reducible exposure;
- sending zero/negative/non-representable provider quantity;
- silently rounding a positive residual to zero and declaring flat;
- repeated close requests against an unchanged unrepresentable residual;
- blind retries after ambiguous provider outcome;
- using stale provider metadata after a newer metadata generation is required;
- using provider exposure whose FP-04 ownership/reconciliation truth is unknown/conflicting;
- using a generic shared `reduce_only=true` flag as proof of provider-native close field compatibility;
- allowing emergency urgency to bypass sizing/currentness/capability proof;
- declaring lifecycle `CLOSED` solely because a close order was ACKed/terminal.

## Required residual-state vocabulary

Define stable E4 provider-local states equivalent in intent to:

- `FULLY_REDUCIBLE`
- `PARTIALLY_REDUCIBLE`
- `RESIDUAL_NONZERO_REPRESENTABLE`
- `RESIDUAL_NONZERO_UNREPRESENTABLE`
- `EXPOSURE_ALREADY_FLAT`
- `REDUCIBLE_EXPOSURE_UNKNOWN`
- `METADATA_STALE_OR_UNKNOWN`
- `RECONCILIATION_REQUIRED`

You may refine names if E4 conventions require it, but preserve the semantic distinctions.

Only authoritative provider/Position truth may establish `EXPOSURE_ALREADY_FLAT`; an order status, requested quantity arithmetic, or local ledger expectation is insufficient.

## Required residual behavior

For any positive residual after a close/reduce attempt or observation:

- if provider-representable, a later fresh E5/E4-authorized close may target only the fresh current reducible exposure;
- if non-representable under current validated provider metadata, represent it as a stable fail-closed residual state;
- unchanged residual truth must not create a tight/unbounded retry loop;
- a retry/replan requires materially newer provider Position/metadata/reconciliation evidence and fresh applicable authority;
- do not invent provider dust-writeoff, force-close, transfer, margin, or special endpoint semantics;
- do not infer lifecycle `CLOSED` until authoritative flat Position truth and later FP-10 lifecycle convergence semantics are satisfied.

## Required metadata/currentness binding

Define the minimum exact metadata evidence required before provider-native close quantity can be calculated. Reuse current repository vocabulary where valid, but do not assume that entry metadata fields or limits automatically govern exit roles unless current repository evidence proves that fact.

The design must explicitly distinguish:

- metadata facts already repository-evidenced for the bounded SWAP sizing implementation;
- fields/limits whose applicability to close/reduce roles remains unresolved and therefore fail closed;
- metadata generation/currentness identity;
- canonical BTC quantity vs provider-native contract/order quantity;
- deterministic conversion/rounding traceability.

Do not claim current provider/private verification for unresolved close metadata semantics.

## Position-mode / capability dependency

Consume accepted `okx-swap-action-role-capability-v0.1` exactly:

- `POSITION_EXIT` and `EMERGENCY_EXIT` remain role-specific;
- account/position/margin mode must bind to an accepted capability row;
- unproven close/provider field combinations remain non-executable;
- emergency exit does not manufacture capability authority;
- Spot/cash semantics are forbidden;
- caller assertions cannot manufacture provider capability.

This task may design the sizing evidence needed by those roles but must not convert an unresolved capability row into executable provider support.

## FP-04 dependency

When provider exposure ownership/currentness is ambiguous, external, conflicting or unreconciled, close sizing whose correctness depends on exact owned/reducible quantity must fail closed and require fresh reconciliation/policy authority.

Do not silently adopt external/manual exposure.

## FP-11 / FP-10 relationship

FP-05 must define only sizing/residual semantics.

It must explicitly state:

- flat exposure does not silently erase provider protection objects;
- post-close protection cleanup/convergence belongs to FP-11/FP-10 sequencing;
- FP-10 lifecycle convergence will later consume authoritative flat/reduced Position truth, aggregate fill/execution truth where required, current FP-04 ownership/reconciliation, FP-11 protection convergence, and E5 lifecycle interpretation;
- FP-05 does not itself emit `CLOSED` or choose lifecycle transitions.

## Deterministic future implementation/test handoff

Document the smallest later E4 executable implementation boundary and credential-free tests, including at minimum:

- actual current exposure smaller than original requested entry quantity -> close size uses actual current exposure;
- actual current exposure larger/different due partial/manual/external truth -> unresolved ownership/reconciliation blocks unsafe sizing until policy permits;
- provider-native conversion never exceeds authoritative reducible exposure;
- exact lot/step quantization boundary;
- positive representable residual remains explicit;
- positive non-representable residual remains explicit and stable;
- unchanged non-representable residual does not retry;
- fresh materially changed Position/metadata may permit a new sizing evaluation;
- zero/negative provider size rejected;
- stale/unknown metadata rejected;
- unknown account/position/margin capability rejected;
- entry sizing evidence cannot be reused as close capability authority by analogy;
- ambiguous prior close result requires reconciliation before another request;
- ACK/terminal order status does not establish flatness;
- emergency exit obeys the same quantity/currentness/capability proof;
- deterministic fixtures require no provider network or credentials.

Do not implement executable changes or test definitions in this task.

## Required durable evidence

Create:

`status/e4/FP05_OKX_SWAP_CLOSE_RESIDUAL_SIZING_DESIGN_20260829.md`

Record:

- task ID;
- design profile/version;
- provider/instrument baseline;
- quantity authority hierarchy;
- residual-state vocabulary and transition/evaluation rules;
- metadata/currentness requirements;
- exact unresolved provider-specific facts;
- exact dependency on FP-02, FP-04, FP-11 and downstream FP-10;
- any shared-contract change request, if genuinely required;
- future implementation/test paths;
- executable verification = `NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK`;
- provider requests = 0;
- credentials = NONE;
- mutation/order actions = 0;
- SHADOW/PAPER/live-fire runtime = NOT_STARTED;
- capital exposure = NONE;
- GitHub compute = NOT_USED.

Update `coordination/E4/STATUS.md` and commit/push the target branch.

## Verification boundary

This task executes no project code/tests:

```text
project executable verification = NOT_RUN / NOT REQUIRED
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER = NOT_STARTED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
FP-03 combined qualification = NOT_RUN / NOT_PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.

## Writable scope

Only:

- `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`;
- `status/e4/FP05_OKX_SWAP_CLOSE_RESIDUAL_SIZING_DESIGN_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not modify executable source/tests, `contracts/**`, other Workers' files, provider credentials/config/private allowlists, AgentBridge/local action catalog, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or release criteria.

## Result classification

### DONE

Use DONE only if the FP-05 design is complete, fail closed on unknown/unrepresentable quantity/currentness states, preserves E5/E7 lifecycle/risk authority, and contains a bounded future implementation/test handoff without granting provider/runtime/capital authority.

### PARTIAL

Use PARTIAL if a bounded provider/shared-contract ambiguity prevents deterministic close/residual sizing semantics. Record the exact ambiguity and required E7 dependency; do not guess provider semantics.

### BLOCKED

Use BLOCKED only if authoritative repository evidence is contradictory or insufficient to define a safe design even with explicit unresolved/fail-closed rows.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-028`, execute only this docs-only task, persist evidence, update STATUS, commit/push to the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start executable FP-05 implementation, FP-02 executable translation, FP-10, FP-11 executable work, provider verification, exact-revision preparation, qualification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
