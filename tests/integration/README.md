# Integration Test Structure

> Owner: E7  
> Execution policy: **LOCAL-ONLY** or another Product-Owner-approved non-GitHub environment.

This directory contains cross-module integration test definitions. GitHub stores the tests; GitHub must not execute them.

## Hard prohibition

Do not add or rely on:

- GitHub Actions;
- `.github/workflows` project test/build jobs;
- GitHub-hosted runners;
- GitHub-triggered self-hosted runners;
- PR/push CI;
- scheduled GitHub jobs;
- GitHub-hosted bug reproduction, backtest, E2E, regression, Monte Carlo, failure injection, or performance testing.

If the current environment cannot run a required test, report `NOT_RUN` and the exact local command. Do not replace missing local runtime with GitHub CI.

## Planned suite layout

As executable code appears, prefer bounded files/directories such as:

```text
tests/integration/
  research/
    test_e1_e2_candle_boundary.*
    test_e2_e3_runtime_parity.*
    test_research_reproducibility.*
  registry/
    test_inbox_validation_registry.*
    test_strategy_version_immutability.*
  paper/
    test_trade_intent_risk_execution.*
    test_partial_fill_position_protection.*
    test_trade_result_persistence.*
  shadow/
    test_shadow_plan_no_live_submit.*
    test_reconciliation_monitoring.*
  parity/
    test_backtest_paper_live_strategy_semantics.*
```

File extensions/framework are intentionally not fixed until the implementation language/test stack is committed. E7 must not invent framework-specific commands before that exists.

## Slice 1 — Research integration

Required test definitions:

1. E1 Candle satisfies canonical UTC/timeframe/Decimal/closed-candle semantics.
2. E2 cannot observe a Candle whose close boundary is in the future.
3. Same StrategyDefinition + same exact market boundary + same runtime version -> same Signal.
4. E3 uses E2 Strategy Runtime semantics rather than a duplicate strategy implementation.
5. BacktestResult contains strategy hash, runtime version, dataset identity/hash, boundaries, and cost-model identity.
6. Look-ahead trap fixture fails if any future information leaks.

## Slice 2 — Research platform integration

Required test definitions:

1. strategy inbox binds immutable `(strategy_id, strategy_version, content_hash)`.
2. unsupported/invalid StrategyDefinition fails structurally.
3. failed ValidationDecision retains the strategy/version and evidence.
4. PASS validation can reach CANDIDATE but cannot skip to LIVE.
5. multiple versions cannot overwrite each other.
6. lifecycle transitions follow the canonical transition graph.

## Slice 3 — Paper integration

Required test definitions:

1. TradeIntent reaches E5 and cannot directly reach E4.
2. E5 REJECT produces no ApprovedTradePlan/order.
3. E5 APPROVE produces a bounded ApprovedTradePlan traceable to policy/version.
4. E4 accepts only approved executable inputs.
5. partial fills update actual position/protection quantity.
6. protection failure triggers emergency behavior.
7. stale market data blocks new exposure.
8. unknown order/position state blocks new exposure.
9. restart preserves required risk/position/audit state.
10. closed trade produces traceable TradeResult and persistence.

## Slice 4 — Shadow integration

Required test definitions:

1. live market/account state may be observed without live order submission.
2. full TradeIntent -> Risk -> ApprovedTradePlan path can be evaluated.
3. order submission is disabled in SHADOW.
4. reconciliation and monitoring expose degraded/unknown state.
5. presence of credentials does not enable LIVE.

## Slice 5 — Tiny Live preflight

Definitions may be committed before LIVE is permitted, but executable live tests require Product Owner authorization and an approved local environment.

Required preflight areas:

- exact strategy version binding;
- exact risk-policy binding;
- approval record binding;
- kill switch;
- idempotency/reconciliation;
- required protection;
- no unknown-state exposure;
- auditability;
- live-disable/default-safe startup.

## Evidence requirements

Every executed integration run must record:

```text
Revision:
Environment:
Command:
Result:
Relevant contract version:
Timestamp UTC:
Owner:
```

No fabricated test results are permitted.