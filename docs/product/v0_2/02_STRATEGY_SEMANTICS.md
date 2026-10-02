# R7 v0.2 strategy capability and temporal semantics

This is an additive E2/E3/E5 specification. It does not declare these capabilities implemented. Preserve `contracts-v0.1`, DSL `0.1`, Runtime `0.1.0` and all legacy golden outputs. Add DSL `0.2` and a separate Runtime `0.2.0` profile in the existing runtime family. Never reinterpret a legacy definition under new defaults.

## STR-01 Capability negotiation

Implement a registry generated from the executable validators/operators and verified test inventory. Every entry contains capability_id, semantic_version, parameters, output type/units, supported timeframes, minimum history, missing-data behavior, arithmetic profile, implementation revision and verification refs. Separate `IMPLEMENTED`, `VERIFIED_REFERENCE`, `PAPER_AVAILABLE`, `LIVE_PROVIDER_AVAILABLE`; an indicator's existence does not imply a provider can execute its exits.

Publish a sanitized `capabilities/<instance_id>/<snapshot_hash>/manifest.json` plus `capabilities.json` to the drive and expose GET `/api/v1/capabilities`. A local pointer to the latest snapshot is convenience only; the submitted package binds an exact capability hash/runtime profile. Chat reads that snapshot before authoring. Missing capabilities return a structured gap receipt: requested feature/version, available version, source location, reason and re-evaluation conditions. Do not silently approximate EMA with SMA, drop a filter or install generated code.

A corrected/new runtime requires a fresh compatibility decision and research evidence. A package whose required runtime compatibility changes is a new immutable submission; retain previous BLOCKED history. No stale approval transfers to the new runtime.

## STR-02 Declarative envelope and grammar

The outer StrategyDefinition remains canonical: schema_version, strategy_id/version, name, symbol, required_timeframes, parameters, rules, runtime_compatibility, content_hash, created_at. DSL 0.2 materializes the following structure inside `rules` as a versioned profile; legacy DSL 0.1 stays routed to its own parser.

- `dsl_version`: exact `0.2`.
- `evaluation_timeframe`: one of the required timeframes.
- `features`: unique named typed expressions.
- `long`, `short`: boolean expressions; simultaneous true produces NO_TRADE with CONFLICTING_ENTRY_RULES, never arbitrary precedence.
- `exit_policy`: declarative requested constraints, owned/approved at the E5 boundary below.
- `behavior_profile`: exact `r7-closed-bar-v0.2`.

Expression forms are strict and mutually exclusive:
- decimal literal: `{ "kind":"decimal", "value":"1.5" }`.
- integer parameter: `{ "kind":"parameter", "name":"atr_window" }` with a schema-validated parameter domain.
- price/volume series: `{ "kind":"field", "timeframe":"4h", "field":"close" }`.
- named feature: `{ "kind":"feature", "name":"trend_fast" }`.
- lag: `{ "kind":"lag", "source":<series>, "bars":1 }`.
- indicator: `{ "kind":"indicator", "name":"EMA", "semantic_version":"r7-ema-v1", "source":<series>, "parameters":{"window":20}, "output":"value" }`.
- operator: `{ "kind":"operator", "name":"GT", "args":[<left>,<right>] }`.

ATR/ADX use a declared candle timeframe instead of a single source field; their parameter schemas explicitly require that timeframe. Compound MACD/Bollinger/Donchian outputs use enumerated output names, not attribute traversal. Features form an acyclic graph. Unknown keys, references, operator arity, units, primitive versions, negative lags and cycles are rejected. No eval/exec, user functions, file/network imports, shell strings or dynamic Python.

Required operators: GT, GTE, LT, LTE, EQ, AND, OR, NOT, ADD, SUB, MUL, DIV, ABS, MIN, MAX, CROSS_ABOVE, CROSS_BELOW and LAG. Expose rolling high/low through explicit ROLLING_MAX/MIN with `window` and `lag_bars`; Donchian is a convenience profile of high/low/mid. Reject mixed dimensional comparisons and additions. Division by zero is a typed invalid observation, not infinity. Boolean evaluation does not turn unavailable data into false: evaluate required features first; unavailable required data yields NO_TRADE/INSUFFICIENT_HISTORY or non-healthy input rejection.

Grammar limits: manifest 64 KiB, StrategyDefinition 256 KiB, AST nesting <=32, AST nodes <=4096, feature count <=128, window <=10000 bars, required timeframes <=4, lag <=10000. Limits are local security policy; a package cannot increase them. Decimal literals must be finite and have <=34 significant digits. Reject duplicate JSON keys, NaN/Infinity and binary-float financial inputs.

## STR-03 Arithmetic profile

Reference profile `r7-decimal34-v1`: Python Decimal, explicit local precision 34, ROUND_HALF_EVEN. No ambient context, platform locale or binary floating-point may change canonical signal/money/quantity values. Do not round intermediate indicator values to instrument tick size. E4 rounds actionable quantities/prices only at its existing provider boundary. Canonical JSON uses the existing strategy-hash convention; define canonical finite decimal text in the new profile and test equivalent serialization explicitly.

Statistical estimates may use a separately declared numerical backend, but final financial facts, policies and order sizes remain Decimal. Statistical algorithm/precision/seed/dependency identity is part of the result; no bit-exact portability claim without parity evidence.

Each numerical primitive has golden vectors, flat/monotone/gap/insufficient-data cases, both signs where relevant, and full-batch versus incremental-state equality tests. Runtime snapshots bind exact dataset prefix, feature parameters and numeric profile; invalid snapshots are recomputed from verified history, never trusted by timestamp alone.

## STR-04 Required indicator definitions

All windows use finalized, contiguous bars in the feature's timeframe and count observations, not wall-clock approximations. These are R7-specific declared semantics; do not claim equivalence to every charting platform.

| Primitive/profile | Exact computation and readiness |
|---|---|
| SMA / r7-sma-v1 | Arithmetic mean of the last n closes (or declared scalar source), first output after n valid observations. |
| EMA / r7-ema-v1 | alpha=2/(n+1); seed is SMA of first n valid source values; then alpha*x+(1-alpha)*previous. No zero seed. First output at n values. |
| RSI / r7-rsi-wilder-v1 | n close differences require n+1 closes. Seed average gain/loss as arithmetic means of first n positive/negative difference magnitudes; update `(prev*(n-1)+current)/n`. RSI=100-100/(1+avg_gain/avg_loss). Both zero ->50; only loss zero ->100; only gain zero ->0. |
| ATR / r7-atr-wilder-v1 | TR at first bar=high-low; later max(high-low, abs(high-prev_close), abs(low-prev_close)). Seed mean of first n TR values; Wilder update thereafter. First output after n bars. |
| ADX / r7-adx-wilder-v1 | First bar has no directional movement observation. For each subsequent bar: up=high-prev_high; down=prev_low-low; +DM=up iff up>down and up>0, otherwise0; -DM analogously, ties both0. Seed mean TR/+DM/-DM over the first n post-initial observations; Wilder update. DI=100*smoothed_DM/smoothed_TR, zero TR ->both DI0. DX=100*abs(+DI--DI)/(+DI+-DI), zero denominator ->0. Initial ADX is mean of first n available DX; Wilder update thereafter. With 0-indexed bars, first DI at t=n and first ADX at t=2n-1 (2n bars). |
| MACD / r7-macd-v1 | EMA(fast)-EMA(slow) using EMA definition above, fast<slow; signal=EMA(signal_window) of available MACD values; histogram=MACD-signal. Outputs `line`, `signal`, `histogram` have independent readiness. No filling unavailable signal values with0. |
| Bollinger / r7-bollinger-pop-v1 | middle=SMA(n); variance=sum((x-middle)^2)/n (population); stddev=Decimal sqrt in reference context; upper/lower=middle +/- k*stddev. k positive Decimal. Outputs `middle`, `upper`, `lower`, `stddev`. |
| Donchian / r7-donchian-v1 | upper=max(high), lower=min(low) over n bars ending at declared lag; middle=(upper+lower)/2. Default breakout profile lag_bars=1, deliberately excluding current decision bar. Outputs `upper`, `lower`, `middle`. |

Window parameters must be positive integers. MACD fast<slow; Bollinger k>0. ATR/ADX require high/low/close from the same canonical bars. OHLC envelope and interval integrity are E1 prerequisites. Source gaps invalidate readiness; there is no hidden forward fill. Warmup history may precede the scored sample, but scored returns/trades start only inside the requested interval.

CROSS_ABOVE(a,b) means previous a<=previous b AND current a>current b; CROSS_BELOW is previous a>=previous b AND current a<current b. Both observations must be valid and based on the immediately previous finalized bar of their defined series. Missing previous value never fabricates a crossover.

## STR-05 Multi-timeframe as-of semantics

Required timeframes remain 1m,15m,1h,4h. Canonical bars are UTC half-open intervals. For the v0.2 dataset profile, bars are aligned to UTC epoch multiples of their duration; explicitly reject or normalize a provider's differing session convention at E1. Never infer timezone from the UI language.

At decision boundary T, a feature may use only bars with close_time<=T, finalized=true and received/available_at<=the decision's recorded information boundary. The higher-timeframe value is the most recently available finalized value at T. A current unfinished 4h candle is forbidden even during a 15m evaluation. Store the exact source-bar identities in `market_boundary_ref`/feature provenance.

Example required fixture: at 11:45 UTC on a 15m evaluation, the 08:00-12:00 UTC 4h candle is not available; use the latest finalized 04:00-08:00 bar, assuming it was actually received. At12:00, use08:00-12:00 only after finality/receipt. Alter all later bars and prove the earlier decision is unchanged. Batch replay, streaming PAPER and LIVE input adapters call the same E2 logic with the same as-of bundle.

E1 may derive 4h bars from lower-timeframe bars only when all expected constituent intervals are present/finalized and source/timeframe/normalization version are recorded. Never stitch across a gap silently. Historical availability may be modeled as candle close only when explicitly labeled `availability_model=historical_close_assumption`; such a replay does not prove real network latency behavior.

## STR-06 Four independent time meanings

Never confuse:
1. `evaluation_timeframe`: when signal evaluation occurs, e.g.4h.
2. `package_valid_from` / `package_valid_until`: when this submission/request may enter its intended operational workflow.
3. `entry_valid_until`: deadline for a particular proposed entry.
4. `max_hold_seconds`: maximum time since the first confirmed entry fill before E5 requests exit under current authority.

Package validity is in the package envelope. Hold/exit constraints are immutable strategy semantics and included in strategy hash. ApprovedTradePlan expiry remains the narrower E5 authority; none of these fields extend it.

An evergreen 4h strategy can be researched repeatedly under new immutable dataset/run identities and trade every finalized4h boundary after approval. A recommendation valid only for the next14400 seconds is a tactical submission: if validation/approval is unfinished when it expires, set the job/request result EXPIRED and issue no new entry. Do not shorten testing, fabricate forward evidence or auto-approve it. An expired strategy package may be explicitly archived for offline research, but no activation results from that research. Canonical lifecycle vocabulary is unchanged; EXPIRED is a request/job disposition, not an added StrategyLifecycleState.

A previously qualified strategy may be activated only through the local approved-deployment workflow. A cloud `activate=true`, copied ApprovalRecord, or Chat sentence is not authority. Timeframe4h does not mean holding exactly four hours; both are visible separately in UI.

## STR-07 Entry and exit semantics

Entry signal/TradeIntent is a proposal. E5 owns sizing/risk and E4 provider translation. The initial entry execution profile remains MARKET unless a separate accepted executable profile explicitly supports another order type.

Required exit-request forms: fixed protective stop price/distance; fixed target price or reward/risk multiple; ATR-multiple stop/target with the feature observation bound; max-hold time exit; deterministic trailing-distance proposal. E2 may produce declarative constraints/proposals; only E5 may emit PositionAction and approve a modification. Add a versioned exit-request profile instead of injecting provider-native fields into TradeIntent.

At first actual fill, persist the approved initial protection anchor and actual exposure. ATR anchoring uses the E5-approved observation, never a future candle. For LONG a loss stop must be below the actionable reference; SHORT above. Equality/crossing is rejected by existing FP-03 rules. Trailing high/low anchors update only from observations allowed by the approved exit profile; no widening the approved loss boundary. Partial fills use actual exposure and must not extend `max_hold_seconds` by resetting the original entry clock.

Protection monitoring, time exits, fill reconciliation and emergency handling are event/deadline-driven independently of entry candle evaluation. A4h strategy does not wait four hours to detect missing protection. In backtests with only OHLC, same-bar stop/target ambiguity uses the existing conservative stop-first rule; gap fills and modeled slippage are explicit. Do not pretend bar replay proves tick-exact trailing execution.

Backtest capability, PAPER capability and LIVE broker capability are separately checked. Unsupported provider-native trailing/amend/close/protection operations remain NON_EXECUTABLE for LIVE; no software-side approximation without an explicitly accepted capability profile. Implement and test required E4 surfaces using current official provider documentation during development; no real private calls or credentials in this task. A stub/raise-NotImplemented path is not LIVE-code-complete.

## STR-08 Authoring kit deliverables

Ship `docs/strategy/authoring-v0.2/` with schema/reference, current-capability reading instructions, exact JSON examples and submission/receipt instructions. Package the following examples with computed hashes using an executable offline authoring helper, not hand-invented hashes:
- valid legacy SMA definition (unchanged);
- 4h EMA/ADX/ATR trend strategy;
- 4h direction +15m Donchian entry strategy;
- a tactical validity-window example that expires safely;
- unsupported-feature example with a typed gap receipt.

Examples are test/research templates, not profitable recommendations, real approval or validation PASS. Include no currency amounts/position sizes that silently become a deployment envelope. Export a compact Chat-readable capability snapshot and result-summary schema to support the Chat -> drive -> R7 -> drive loop without an LLM inside R7.

## STR-09 Verification obligation

Before publishing a feature as supported: execute golden vectors; insufficient history; parameter bounds; missing bars; UTC boundaries; batch/incremental equality; prefix invariance; Windows/Linux signal parity; import compatibility; parser rejection; E3/E5 integration. Record actual supported runtime/capability versions and never copy the requested-feature list into a verified-capability response.
