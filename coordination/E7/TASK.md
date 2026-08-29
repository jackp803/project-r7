# E7 Current Task

- task_id: `E7-20260829-098`
- issued_at: `2026-08-29T13:13:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-mature-okx-failure-gap-audit-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, Product Owner instruction on 2026-08-29 to incorporate lessons from a mature OKX BTC bot, `status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`, accepted E7-095/E7-096 release provenance, `status/RELEASE_GATES.md`, `status/BLOCKERS.md`

## Objective

Perform a **repository-grounded, docs/status-only cross-module failure-prevention gap audit** against FP-01 through FP-16 in:

`status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`

The Product Owner supplied operational incident history from a separate, mature OKX Spot bot. Your job is **not** to copy Spot implementation details into project-r7. Project-r7 currently targets OKX `BTC-USDT-SWAP`; translate each incident into the correct perpetual/instrument-mode safety invariant and determine whether current R7 contracts/source/tests/evidence already cover it.

This task is an audit and handoff task only. Do not change executable source, tests, contracts, runtime behavior, provider configuration, AgentBridge, risk thresholds, execution semantics, or release criteria in E7-098.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/E4_EXECUTION.md`;
- `agents/E5_RISK_POSITION.md`;
- `agents/E6_PLATFORM.md`;
- `status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`;
- current relevant `contracts/**`, `docs/adr/**`, `src/brokers/**`, `src/execution/**`, `src/risk/**`, `src/position/**`, `src/storage/**`, `src/platform/**`, `src/integration/**`;
- current relevant `tests/brokers/**`, `tests/execution/**`, `tests/risk/**`, `tests/position/**`, `tests/storage/**`, `tests/platform/**`, `tests/integration/**`, `tests/e2e/**`, `tests/safety/**`;
- accepted local qualification/provider/release evidence under `status/e7/**`, `status/RELEASE_GATES.md`, and current blockers.

Do not read or execute another Worker's `coordination/<ID>/TASK.md`.

## Mandatory classification

For every FP item `FP-01` through `FP-16`, assign exactly one status:

- `IMPLEMENTED_AND_LOCALLY_VERIFIED`
- `IMPLEMENTED_NOT_LOCALLY_VERIFIED`
- `PARTIAL`
- `MISSING`
- `NOT_APPLICABLE_TO_SWAP`

Rules:

1. `IMPLEMENTED_AND_LOCALLY_VERIFIED` requires both concrete implementation evidence **and accepted local executable evidence already committed in Git** that materially covers the failure mode. Source/test definitions alone are insufficient.
2. `IMPLEMENTED_NOT_LOCALLY_VERIFIED` requires concrete implementation but no accepted local executable evidence sufficient for that exact failure mode.
3. `PARTIAL` means some invariant is implemented/tested but a meaningful edge of the failure class remains uncovered.
4. `MISSING` means no adequate implementation/control exists.
5. `NOT_APPLICABLE_TO_SWAP` may be used only for the literal Spot-specific mechanism. You must still identify the corresponding SWAP substitute invariant and classify that substitute separately within the same FP row/narrative.
6. `NOT_RUN != PASS`. Do not infer coverage from historical tests that did not exercise the relevant semantics.

## Required audit dimensions

For each FP item record:

- failure class;
- Spot-specific lesson vs SWAP-applicable invariant;
- current R7 implementation paths/classes/functions/contracts;
- current test-definition paths;
- accepted local verification evidence, if any;
- current classification;
- exact residual risk/gap;
- exact owner: E4 / E5 / E6 / E7 / external AgentBridge/operator;
- smallest safe follow-up task;
- whether the follow-up changes executable source;
- whether a new credential-free local qualification would be required after that change;
- whether provider/private API access would be required;
- whether credentials would be required;
- whether Product Owner authority would be required;
- whether capital exposure would be required (expected `NO` for all prevention implementation/test tasks unless a later separately authorized runtime phase says otherwise).

## Specific failure classes that must not be lost in aggregation

Even if multiple FP items map to one existing subsystem, audit these explicitly:

- startup operational-mode drift / environment-default ambiguity;
- instrument/account/margin/position-mode order-parameter capability matrix;
- protection trigger already breached before create/replace;
- manual/external provider order/fill/position reconciliation policy;
- lot/minimum/reducible-quantity residual handling without retry storms;
- current-state reporting provenance/freshness;
- desync/reconciliation lock vs financial kill-switch separation;
- provider/local clock-skew preflight;
- state-aware watchdog/restart recovery;
- partial-fill/aggregate-close/manual-flat lifecycle correctness;
- unique protection registry/linkage;
- pending/acknowledged execution not mutating fill-derived position truth;
- invalidation of stale pre-reconcile snapshots;
- bounded stable waiting/retry states;
- staged breakeven/trailing/profit-protection maturity;
- exact runtime identity/revision/mode/heartbeat preflight.

## Do not over-apply Spot fixes

Explicitly reject literal transplantation where inappropriate, including:

- `tdMode=cash` as a SWAP rule;
- Spot-specific prohibition of `reduceOnly` as a SWAP rule;
- BTC wallet dust tolerance as the direct SWAP flatness definition;
- Spot algo-order `ccy` requirements as a generic SWAP requirement.

Instead identify the exact OKX SWAP capability/precision/position-mode invariant R7 needs.

## Required durable evidence

Create:

`status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md`

It must contain:

1. an executive summary with counts by classification;
2. a complete FP-01..FP-16 matrix;
3. a prioritized list of only the residual gaps, ranked:
   - `P0_PRE_PROVIDER_RUNTIME`
   - `P1_PRE_PAPER_OR_SHADOW`
   - `P2_PRE_LIVE`
   - `P3_OPERATIONAL_HARDENING`
4. recommended bounded next tasks by owner;
5. explicit statement of which items are already sufficiently covered and must **not** be reimplemented;
6. explicit statement of which historical Spot fixes are non-applicable literally;
7. confirmation that this audit made no executable/runtime change.

Update `coordination/E7/STATUS.md` on the task branch.

Optionally update `status/INTEGRATION_STATUS.md` only if needed to record a non-promotional audit state. Do not change release-gate PASS/FAIL criteria or promote/demote a gate in E7-098.

## Verification / execution boundary

E7-098 is static repository/evidence review only.

- Do not execute project code or tests.
- Do not create `coordination/E7/LOCAL_JOB_REQUEST.json`.
- Do not call OKX or any provider.
- Do not read/request/use credentials.
- Do not start SHADOW or PAPER runtime.
- Do not reset/delete/reuse either consumed SHADOW authorization marker.
- Do not mutate provider/account state.
- Do not submit/cancel/amend/close orders.
- Do not move or expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.
- Do not modify AgentBridge source/config.

Record executable verification as:

```text
NOT_RUN / NOT REQUIRED FOR DOCS-ONLY STATIC GAP AUDIT
```

This is not executable PASS evidence.

## Current release/runtime boundary remains unchanged

```text
historical provider-qualified Gate C revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
current ADR-0010 credential-free requalified baseline = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
provider-facing verification on 8fbf5fca... = NOT_RUN / NOT_INFERRED
AgentBridge ADR-0010 consumer migration = external dependency / not yet accepted
first SHADOW authorization = CONSUMED / NO RETRY
replacement SHADOW authorization = CONSUMED / NO RETRY
third/replacement SHADOW authority = NOT GRANTED / PRODUCT OWNER REQUIRED
PAPER runtime = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
capital exposure = NONE
```

E7-098 grants no new provider/runtime authority.

## Writable scope

Only:

- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md`;
- `status/INTEGRATION_STATUS.md` only if needed for non-promotional audit state;
- `coordination/E7/STATUS.md`.

Do not modify production source, tests, contracts, ADRs, E1-E6 files, AgentBridge, local action catalog, Product Owner authorization artifacts, or release-gate criteria.

## Completion

### DONE

Use `DONE` when FP-01..FP-16 are all classified with repository/evidence citations, residual gaps are prioritized, and bounded owner-specific follow-up tasks are recommended without implementing them.

### PARTIAL

Use `PARTIAL` if one or more failure classes cannot be classified because authoritative implementation/evidence is ambiguous, but the rest of the audit is complete.

### BLOCKED

Use `BLOCKED` only if repository contradictions prevent a safe audit classification.

Stop after E7-098. Do not self-start E4/E5/E6 remediation, executable test work, provider verification, AgentBridge migration, a third SHADOW session, PAPER, Gate D, LIVE, mutation, order action, or capital movement/exposure.
