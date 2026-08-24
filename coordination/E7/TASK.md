# E7 Current Task

- task_id: `E7-20260824-040`
- issued_at: `2026-08-24T14:03:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-trade-result-integration-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, accepted Gate A evidence PR #33, Gate B static preflight PR #34, accepted protection chain PR #37-#45, accepted close/TradeResult contract PR #46, accepted E5 close producer PR #47, accepted E4 close consumer PR #48, accepted E5 TradeResult builder PR #49

## Objective

Perform only a bounded **STATIC cross-module integration / test-definition review** of the real Paper close-to-TradeResult chain after PR #49. Do not execute project code.

Review the actual production surfaces for:

```text
entry OrderRequest + entry Fill truth
+ E5 close/protection authority
+ E4 close/protection OrderRequest
+ PaperBroker Fill / residual-or-flat Position truth
+ E5 POSITION_CLOSED interpretation
+ E5 trade-result-v0.1 builder
```

Determine exactly which closure paths are now fully materialized and which still have an implementation/contract/evidence-producer gap before E6 persistence/restart/audit is started.

This task is not Gate B execution and must not claim PASS from static evidence.

## Accepted prerequisites

```text
PR #46 merge = d070ffc752d5c37c05aa4101ebc2f6add0c1ff48
close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1 = ACCEPTED STATIC CONTRACT PROFILE

PR #47 merge = e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15
E5 close producer = MATERIALIZED / executable NOT_RUN

PR #48 merge = 3f7bba953ece100d23c88b86b47df52696adb3a0
E4 close consumer + close Fill/residual-flat truth = MATERIALIZED / executable NOT_RUN

PR #49 merge = a9edc5db9f31efb0c4a8a0c33d54766093c70392
E5 authoritative-flat + trade-result-v0.1 builder = MATERIALIZED / executable NOT_RUN
```

All prior executable Gate B evidence remains `NOT_RUN`; Gate B remains `BLOCKED`; PAPER/SHADOW/LIVE remain unauthorized.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, protection/execution profiles and ADR-0005;
- E5 `src/position/close.py`, `src/position/protection.py`, `src/position/protection_result.py`, `src/position/trade_result.py`, `src/position/state_machine.py`;
- E4 `src/execution/gateway.py`, `src/execution/protection.py`, `src/execution/close.py`, `src/execution/models.py`;
- E4 `src/brokers/paper.py` and broker interface;
- accepted tests from PR #47/#48/#49;
- `status/RELEASE_GATES.md` and `status/INTEGRATION_STATUS.md`.

Do not accept worker/status prose as proof without checking callable production paths.

## Required review questions

### 1. Explicit ordinary EXIT chain

Prove statically whether one real callable chain exists using production APIs only:

```text
E5 close-v0.1 EXIT
-> E4 POSITION_EXIT request
-> PaperBroker submit + actual Fill(s)
-> same-position residual/flat Position observation
-> E5 build_trade_result(... current_lifecycle=EXIT_REQUESTED ...)
-> POSITION_CLOSED / CLOSED + canonical TradeResult
```

No synthetic replacement for the real E4 request/fill/flat-position path.

If fully materialized, classify the path at most:

```text
IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN
```

not PASS.

### 2. EMERGENCY_EXIT chain

Perform the same review for:

```text
EMERGENCY
-> E5 EMERGENCY_EXIT authority
-> E4 EMERGENCY_EXIT request
-> PaperBroker Fill(s)
-> authoritative flat Position
-> E5 POSITION_CLOSED + TradeResult
```

Preserve emergency reason/authority distinction.

### 3. PROTECTION_STOP full-close chain

Do not assume E5 unit-test injection of a flat Position proves system-level support.

Check whether current E4/PaperBroker production APIs can actually derive/query the required **same-position normalized final flat Position truth** after a real `PROTECTION_STOP` Fill with exact protection lineage.

In particular, inspect whether the current residual/flat observer supports `PROTECTION_STOP`, or only `POSITION_EXIT | EMERGENCY_EXIT`.

If protection Fill -> same-position flat truth is not callable through production E4/PaperBroker surfaces, keep the protection-triggered TradeResult path:

```text
BLOCKED / IMPLEMENTATION_GAP
next_owner = E4
```

Do not use symbol-level net exposure or a hand-constructed Position as a substitute.

### 4. Funding evidence producer boundary

E5 PR #49 uses a bounded internal `FundingEvidence` validation input. Determine whether Gate B Paper finalization currently has a real versioned provider-neutral producer/source for:

```text
ZERO_CONFIRMED
or
INCLUDED + funding_cost
```

covering the exact `[opened_at, closed_at]` position interval.

Classify precisely:

- `ALREADY_MATERIALIZED` if a real current Paper/runtime producer exists;
- `IMPLEMENTATION_GAP / next_owner=<E4 or E6>` if semantics are already sufficient but a producer/persistence path is missing;
- `CONTRACT_OR_SEMANTIC_GAP / next_owner=E7` if a shared serialized boundary is actually required before a domain can implement it.

Do not invent a provider Funding DTO in E7 tests merely to make the chain appear complete.

### 5. Entry evidence / identity binding

Verify E5 uses exact declared E4 entry OrderRequest identity plus Fill client/order lineage, not `trade_plan_id` alone, and that current one-position baseline remains contract-valid.

### 6. Fail-closed financial/lifecycle semantics

Verify statically that the integrated chain preserves at minimum:

- `OrderStatus.FILLED != flat Position proof`;
- `actual_quantity=0 + CONSISTENT + observation after latest exit Fill` required for `POSITION_CLOSED`;
- partial/under-close/over-close cannot finalize;
- duplicate Fill IDs cannot finalize;
- missing fee evidence cannot become zero silently;
- unsupported fee currency fails closed;
- missing funding evidence cannot become zero silently;
- LONG/SHORT PnL follows accepted Decimal profile;
- actual Fill prices are not charged again as slippage;
- deterministic TradeResult identity/idempotency;
- no E4 broker truth is rewritten by E5;
- no new exposure or live authority is introduced.

## Integration test definitions

Where the real production chain is already callable, add/update E7-owned static integration/safety test definitions under allowed E7 paths using the actual E4/E5 APIs rather than reimplementing them.

At minimum define the complete explicit ordinary EXIT and EMERGENCY_EXIT Paper paths if statically callable.

For any blocked path, do **not** create a synthetic passing test. Record the exact missing callable interface/producer and next owner.

## Release-gate reconciliation

Update E7-owned release/integration status conservatively.

A source-materialized full chain with no approved-local execution can move only from `BLOCKED / IMPLEMENTATION_GAP` to `NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` where appropriate.

Never change any criterion to PASS in this task.

Preserve at minimum:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Restart/persistence stays `BLOCKED` until E6 work is actually materialized.

## Writable scope

E7-owned only:

- `tests/integration/**`;
- `tests/e2e/**` only if test-definition placement is appropriate, no execution;
- cross-module E7-owned `tests/safety/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- E7-specific `status/e7/**` review/evidence;
- `coordination/E7/STATUS.md` on the target branch.

Do not modify E1-E6 production code, shared contracts/ADRs unless a genuine contract defect is discovered and the task terminates `BLOCKED` with an exact follow-up proposal rather than opportunistically redesigning scope.

## Executable verification

This task is STATIC REVIEW / TEST-DEFINITION ONLY.

```text
project_executable_verification = NOT_RUN / NOT REQUIRED FOR STATIC REVIEW
```

Do not request Local Runner, use GitHub Actions/CI, hosted runners, GitHub-triggered self-hosted compute, Computer Adapter, provider/private APIs, or credentials.

Static review may classify implementation readiness but never executable PASS.

## Acceptance

### DONE

- ordinary EXIT and EMERGENCY_EXIT callable chains are independently checked against real production APIs;
- PROTECTION_STOP full-close flat-truth support is independently checked, not assumed from E5 unit tests;
- funding evidence producer/source ownership is classified precisely;
- any remaining blocker has exact expected-vs-actual evidence and next owner;
- E7 integration/safety definitions use actual production APIs for unblocked paths;
- release statuses preserve `NOT_RUN != PASS` and Gate B remains BLOCKED;
- no project code executed and no GitHub compute used.

### BLOCKED

Use only if a genuine shared-contract/architecture contradiction prevents the review from giving a safe domain-owner disposition. Record exact conflict and affected producers/consumers.

## Completion / mailbox rule

Commit/push E7-owned tests/evidence/status to `agent/e7-gate-b-trade-result-integration-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E7/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E4 remediation, E6 persistence, approved-local verification, Gate C, PAPER, SHADOW, or LIVE.
