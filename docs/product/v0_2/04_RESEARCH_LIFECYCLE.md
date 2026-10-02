# R7 v0.2 research, lifecycle and trading specification

Authority: `00_EXECUTION_BASELINE.md`; existing E1/E2/E3/E4/E5/E6 meanings remain authoritative. This document specifies additions and stronger product gates, not a claim of profitable strategies.

## RESEARCH-01 Reproducible dataset service

Support local/cloud dataset manifests and an explicitly configured public-market-data acquisition path. Provider public data access and credentials/private access are distinct capabilities. Unit/acceptance tests are network-isolated fixtures; a user-requested public acquisition run records its exact source/endpoints/request budget. No paid data provider dependency or hidden network fallback.

Dataset manifest binds canonical symbol, timeframe(s), source instrument, UTC alignment, normalization version, ordered interval range, row counts, finalized coverage, missing/duplicate ranges, availability model, logical record hash, container-byte hashes and funding/cost evidence source. Validate E1 candle invariants before E2 use. Cached input is immutable. A newer dataset creates a new revision; it cannot rewrite a completed result's provenance.

Do not invent history for dates/instruments not available from the source. Missing historical funding is either BLOCKED for the required research profile or an explicitly labeled sensitivity assumption, never factual zero. Unsupported fee currency or uncertain contract units cannot become silent cost-free trading.

## RESEARCH-02 Frozen experiment and split plan

A ResearchRun binds submission, exact strategy/version/hash, E2 runtime/capability hash, executable revision, dataset versions, split plan, all policy hashes, cost model, random algorithm/seed, and source information cutoff. Every stage has attempt history, status, input hash, output hash, start/end, owner lease and reason codes.

Before running adaptive search, persist an ordered chronological split:
- development-training;
- development-validation/walk-forward/parameter stress;
- sealed final OOS.

Split intervals are half-open and non-overlapping for scored observations. Provide pre-sample warmup candles only as features; never count their trades in the scored interval. Purge evaluation labels/trades whose information or holding interval overlaps a training/evaluation boundary. If max holding/label horizon is unbounded, block a purged protocol until it is specified. Embargo duration and its rationale are policy inputs; no automatic zero embargo under an unspecified horizon.

Parameter selection, feature selection and robustness-driven revision may use only development partitions. Freeze the finalist definition/hash and policy before reading final OOS. Final OOS is evaluated last and cannot be repeatedly re-queried until something passes.

## RESEARCH-03 Trial ledger and Chat feedback

Maintain append-only experiment family/trial history, including failed/aborted variants, manual Chat revisions, policy changes and all dataset/holdout observations. Record trial_count and family selection procedure in reports. A hash change/new strategy version does not erase prior use of an OOS period. When Chat or a human reads the result and changes the strategy based on it, that holdout becomes development evidence for the next iteration; the next independent validation needs unobserved data or an explicitly labeled non-independent exploratory assessment.

No numeric threshold, bootstrap result or win rate proves profitability. Inference about future performance is labeled uncertainty, not a release warranty.

## RESEARCH-04 Actual pipeline

```
verified local package
-> E2 compatibility execution
-> E6 DRAFT -> BACKTESTING
-> dataset/split resolution
-> actual E3 historical replay calling actual E2
-> development validation and robustness
-> freeze finalist and policies
-> sealed OOS evaluation
-> E3 combined product assessment
-> E6 guarded REJECTED or CANDIDATE
-> immutable cloud report
```

A failed statistical criterion produces FAIL and an auditable rejection; missing prerequisite, unsupported feature, insufficient sample or unperformed stage produces BLOCKED/NOT_RUN at the job/assessment layer. They are not made into a passing or profitable candidate. Exact domain lifecycle remains canonical; no new lifecycle enums such as OOS_VALIDATING are introduced. That is a job stage only.

Backtest execution success is not statistical PASS. OOS payload `decision=PASS` supplied by an author is not evidence. E3 evaluation and E6 persistence must bind real local execution metadata and current product assessment, not trust user-provided status strings.

## RESEARCH-05 Policies, units and diagnostic mode

Materialize strict versioned schemas for DatasetProfile, SplitPlan, ResearchPolicy, RobustnessPolicy, PaperPromotionPolicy and DeploymentEnvelope. Reuse existing E3 ValidationPolicy/E5 RiskPolicy rather than creating conflicting duplicates. Each quantitative threshold declares units: e.g. drawdown USDT amount versus fraction of a specified initial equity, elapsed seconds versus bar count, and net return denominator. Never pass a percent into an amount-valued legacy field.

Required research promotion policy fields include minimum closed trades per partition, cost/funding model, net expectancy/PnL criterion, drawdown limit and units, maximum consecutive losses, profit-factor null handling, split/purge rules, robustness pass fraction, stress tolerance and sample-adequacy policy. All required values are locally selected and hashed before a run. Package references can choose only allowed preconfigured policies.

First-run default is `diagnostic_only`: research calculations and reports may run, but missing selected promotion/risk policy blocks CANDIDATE/PAPER/LIVE gates. Ship clearly labeled deterministic fixture policies to test positive/negative paths; never quietly install fixture thresholds as real financial policy. The user configures a real policy once in the commissioning workflow, not for every submitted strategy. Policy amendments create a new generation and require re-assessment; they cannot retroactively turn an old failure into PASS.

## RESEARCH-06 Robustness algorithms

Required: parameter-neighborhood replay, chronological walk-forward, cost/slippage/funding stress and seeded Monte Carlo. No strategy's requested robustness profile may skip mandatory local product stages.

Neighborhood: explicit finite typed parameter sets with bounds, ordering and a maximum trial budget. Preserve invalid combinations with reasons. Perturb on development data only; fixed seed where sampling is used. Each material strategy variant receives immutable variant identity/hash. Report all tested variants and sensitivity, not only the winner.

Walk-forward: ordered train/evaluation windows with purge/embargo and warmup treatment. Each window's selection can see only its training/development information. Aggregate each evaluation interval once; forbid accidental overlapping return double-counting. Report per-window exposure/trades/costs, instability and sample inadequacy. Avoid private reimplementation of E2 indicators.

Monte Carlo: require explicit algorithm version, seed, resample_count, sample source and dependence model. Offer trade permutation only as drawdown-order sensitivity (not evidence of positive expectancy), and moving-block bootstrap as a separately labeled dependence-aware sensitivity method. Record block length, RNG algorithm/version and statistical precision; same inputs/seed/backend reproduce the same output. Report distribution/quantiles, not a single favorable path. Empty/too-small samples are INSUFFICIENT_EVIDENCE, not zero-risk PASS.

Stress: apply explicit adverse cost/slippage/funding scenarios to actual trade/replay rules; list assumptions and preserve unfavorable outcomes. The product decision uses the configured policy and reports correlated tests/limitations. Finite computation budgets are enforced; canceled runs remain incomplete evidence.

## RESEARCH-07 Execution parity

Same exact StrategyDefinition and as-of inputs use the same E2 runtime in backtest/PAPER/LIVE. Costs/fills differ by execution model and are recorded. Existing next-open/no-look-ahead and conservative intra-bar behavior remain. Add explicit protective/time-exit parity coverage; a fill at an unavailable historical price is forbidden. Real market fills remain E4 observations, not backtest estimates.

## LIFE-01 Canonical lifecycle materialization

Retain the legal transitions from `contracts/SHARED_CONTRACTS_V1.md`. Use named methods and evidence gates, not arbitrary public transition APIs. Extend the actual E6 service/store; do not duplicate canonical lifecycle in application tables.

- DRAFT -> BACKTESTING: executed exact E2 compatibility evidence.
- BACKTESTING -> CANDIDATE: complete real E3 replay, required development/robustness and final OOS assessments, sufficient samples, exact profile/revision identities, and product gate PASS.
- BACKTESTING -> REJECTED: explicit quantitative decision/reasons, retained evidence.
- CANDIDATE -> PAPER: accepted research evidence, selected PAPER policy, eligible simulation runtime, no real broker mutation path.
- PAPER -> READY_FOR_APPROVAL: actual forward elapsed-time/trade-count/performance and runtime-health requirements satisfied. Synthetic accelerated clock cannot satisfy real forward qualification.
- READY_FOR_APPROVAL -> APPROVED: immutable human ApprovalRecord bound to exact strategy/release/deployment envelope.
- APPROVED -> LIVE: fresh provider/reconciliation/preflight/financial authority and explicit live activation in the secure local command workflow.
- LIVE -> DEGRADED: automatic fail-closed response is allowed; new exposure disabled, existing exposure still managed according to E5 policy.
- DEGRADED -> LIVE: explicit authorized resumption, never a new signal or process restart alone.
- RETIRED: no new entries, preserve history; retiring a strategy does not assert the broker is flat or delete outstanding protection.

Implement all other legal retirement/rejection edges from the canonical contract with exact actor/time/reason/evidence. An extension to product gates must be enforced in backend service/storage authority, not only hidden buttons.

## PAPER-01 Continuous runtime

Separate acquisition/scheduling, E2 evaluation, E5 risk, E4 PaperBroker, E5 lifecycle/protection and E6 persistence. Evaluate entries once per finalized boundary with durable idempotency keys. Replays after crash may recompute a signal but cannot create another logical entry. Keep account/execution histories and process/start generations separate.

PaperBroker simulates acknowledged orders, fills, partial fills, protection, funding and exits; it does not contact a real trading endpoint. Support both deterministic accelerated acceptance mode and real-time forward mode. UI/report explicitly identify which one ran. Only real elapsed forward mode can satisfy a real PaperPromotionPolicy; tests can demonstrate the state machine with fixture-only evidence namespaces.

If current public-market transport is unconfigured or stale, show NOT_CONNECTED/STALE and admit no new simulated exposure. Do not substitute a synthetic ticker silently. Stop/restart resumes from recorded orders/fills/positions; unknown state requires reconciliation rather than a reset balance.

## TRADE-01 LIVE-capable implementation

Implement actual production adapter code as needed, based on current primary provider documentation and existing accepted E4 capability profiles. Record endpoint/field/permission mappings and sanitized fake-response contract tests. Do not invent symbol precision, account mode, leverage, minimum size or protective-order support. Missing verified action capability prevents that action; a fake provider's success does not establish broker compatibility.

Runtime order: preflight -> fresh market/account/order/fill/position/protection observations -> E5-approved plan/action -> stable OrderRequest identity -> submission -> ACK-only state -> actual fills/position -> protection verification -> managed exit -> authoritative flat truth -> TradeResult. Query/reconcile ambiguous outcomes before any retry. No alternate client IDs to defeat idempotency.

Research and cloud code have no trading client reference. Risk checks use current data for every proposed new exposure. Monitoring/protection continues between entry bars; time exits cannot wait for the next4h bar. Client crash or network loss cannot guarantee that already accepted exchange orders disappear: preserve broker-native protection where verified and show local uncertainty honestly.

## TRADE-02 Deployment envelope and shutdown

DeploymentEnvelope binds strategy/version/hash, product executable hash/revision, capability/profile hashes, provider/account target reference, instrument, risk policy, capital ceiling, risk-per-trade, max positions, daily/aggregate-loss limits, permission/expiry/revocation and approver identity. All are explicit local commissioning values. Credentials never count as approval.

Stop-new-entries, stop-research, pause-runtime, emergency-exit-request and terminate-process are distinct commands. A process shutdown must not silently cancel protection or leave a position unmanaged. Require a visible E5-approved shutdown/handoff plan and report residual/unknown exposure. Immediate OS termination is tested as a fault, not advertised as a safe close-all command.

No funding, transfer, withdrawal, real provider-private verification, live order or capital operation is authorized by this implementation task. Code and tests continue without these prerequisites; actual commissioning is reported separately.

## EVID-01 Provenance and final acceptance

Every receipt/result/approval binds the smallest actual executable/config/dataset authority used. Later documentation or merges cannot transplant an executable PASS. The build/release hash is visible in UI. Report failed/errors/skips, actual elapsed PAPER time, synthetic-data labels and platform separately.

A product E2E must demonstrate both accepting and rejecting deterministic fixtures, but fixtures never populate the real deployment registry or create reusable approvals. A real research integration check must run an actual non-fixture dataset when explicitly available and keep its actual outcome even if all strategies fail. Missing data/cloud/native host is a named external gap, not simulated away.
