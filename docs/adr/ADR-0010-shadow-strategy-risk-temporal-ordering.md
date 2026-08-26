# ADR-0010 — SHADOW Strategy / Provider / Risk Temporal Ordering

- Status: `ACCEPTED / E7 REMEDIATION CANDIDATE`
- Date: `2026-08-26`
- Owner: `E7 Integration / Architecture / System QA / Release`
- Source incident: `E7-20260826-090`
- Remediation task: `E7-20260826-092`
- Prior qualified executable revision: `ab725965e96cac7a9769fd1ab15a3e626f920b95`

## Context

The bounded E7-090 zero-capital SHADOW replacement session failed closed after one complete nine-GET observation batch with sanitized terminal reason `UNSAFE_PROVIDER_OR_RECONCILIATION_STATE`. The session established zero available capital, read-only permission, expected account level/position mode/dedicated-subaccount classification, healthy provider clock, zero mutation requests and zero submit requests, but completed no SHADOW cycle.

Source review confirmed a cross-module temporal-ordering defect in the E7 integration boundary:

1. the AgentBridge supervisor captured one caller `evaluation_time` after E1 public market reads;
2. `ShadowComposition.run_cycle(...)` accepted that timestamp as `risk_evaluation_time`;
3. `run_cycle(...)` then performed E4 `OKXShadowProviderReader.observe(...)`;
4. E4 correctly stamped the new provider observation from its advancing UTC clock;
5. E7 then supplied the older caller timestamp to E5 `derive_gate_c_risk_context(...)`;
6. E5 correctly treats `provider observed_at > risk_evaluation_time` as `GATE_C_SHADOW_OBSERVATION_TIME_INVALID`.

The E5 rule is correct and must not be weakened. The integration defect is that one pre-provider timestamp was being used for two semantically different boundaries: deterministic strategy evaluation and post-provider risk interpretation.

The durable E7-090 session artifact did not persist the cycle's internal reason-code set, so the temporal defect is confirmed as a real failure path but cannot be proven to have been the only blocking condition in that specific session. Other sanitized provider/risk/checkpoint/reconciliation reasons therefore remain historically possible.

## Decision

SHADOW integration uses two distinct UTC time boundaries.

### 1. Strategy evaluation time

`strategy_evaluation_time` is supplied by the caller and defines the deterministic market/strategy boundary.

It is used for:

- finalized/future Candle validation;
- `StrategyRuntime.evaluate(...)`;
- `TradeIntent.generated_at`.

This preserves deterministic strategy semantics and prevents provider-read latency from silently changing which Candle boundary the strategy evaluated.

### 2. Provider observation

After validating the authoritative SHADOW operational mode, input shape and finalized Candle boundary, E7 invokes the E4 read-only `observe(...)` capability.

E4 remains authoritative for the provider observation's own `observed_at`, provider clock, account/position/order/fill facts, fixed GET allowlist and no-submit/no-mutation boundary.

### 3. Risk decision time

Only after E4 observation returns does E7 invoke `risk_time_provider()` and validate the returned UTC timestamp.

That post-observation timestamp is used for:

- E5 `derive_gate_c_risk_context(..., risk_evaluation_time=...)`;
- E5 `evaluate_trade_intent(..., decided_at=...)`.

If the risk decision timestamp precedes the strategy evaluation timestamp, E7 fails closed with `RISK_DECISION_PRECEDES_STRATEGY_EVALUATION`.

E5's existing temporal rule remains unchanged: a provider observation that is genuinely later than the post-observation risk timestamp remains unsafe and produces `GATE_C_SHADOW_OBSERVATION_TIME_INVALID`.

## E7 API

Preferred runtime call shape:

```python
composition.run_cycle(
    ...,
    strategy_evaluation_time=strategy_time,
    risk_time_provider=utc_now_provider,
)
```

The callback is invoked by E7 only after E4 provider observation completes.

For source compatibility, the prior `risk_evaluation_time=` keyword remains accepted as a deprecated alias for the strategy timestamp. When that alias is used without `risk_time_provider`, it retains the historical fixed decision-time semantics. It therefore does **not** remediate an advancing-clock runtime caller and must not be used by a future SHADOW supervisor.

Supplying both `strategy_evaluation_time` and the deprecated alias is rejected as `AMBIGUOUS_STRATEGY_EVALUATION_TIME`. Supplying the deprecated alias together with a new risk-time callback is rejected as `AMBIGUOUS_RISK_DECISION_TIME`.

## Sanitized integration diagnostics

`ShadowCycleResult.reason_codes` remains non-sensitive and gains stable E7 stage classifications:

- `E7_PROVIDER_READ_DEGRADED` — E4 returned a degraded provider observation;
- `E7_RISK_CONTEXT_UNSAFE` — E5 risk-context derivation returned one or more fail-closed reason codes;
- `E7_SHADOW_CHECKPOINT_NOT_RECORDED` — the cycle did not establish an accepted E6 SHADOW checkpoint.

Underlying stable domain reason codes remain preserved. A post-checkpoint reconciliation failure remains the existing sanitized `FRESH_SHADOW_RECONCILIATION_NOT_ESTABLISHED` E7 error code.

No raw provider payload, credential, account identifier, exact balance, provider order/fill identifier, signature, token/cookie, exception message containing sensitive material or local filesystem path is added to public/durable evidence.

## Unchanged boundaries

This decision does not modify:

- E5 temporal/fail-closed semantics;
- E4 provider authentication, GET allowlist, redaction or no-submit/no-mutation behavior;
- E6 OperationalMode/checkpoint/restart/reconciliation semantics;
- E1 Candle/finality/freshness contracts;
- E2 deterministic strategy-runtime semantics;
- shared `contracts-v0.1` object schemas;
- the public `ShadowCycleResult` authority boundary.

The composition still exposes no `TradeIntent`, `RiskDecision`, `ApprovedTradePlan`, broker submit surface or executable authority object.

## Consumers and migration

Known consumers are:

1. E7 integration/E2E/safety tests in `project-r7`;
2. AgentBridge `tools/run_zero_capital_shadow_session.py` at historical supervisor revision `2ac9a79`;
3. any future bounded SHADOW supervisor or integration harness invoking `ShadowComposition.run_cycle(...)`.

Before any future authorized provider session, AgentBridge must migrate from:

```python
risk_evaluation_time=evaluation_time
```

to an explicit separated call such as:

```python
strategy_evaluation_time=evaluation_time,
risk_time_provider=_utc_now,
```

The callback must remain an operator-owned UTC clock and must be invoked by E7 after E4 observation; the supervisor must not precompute or guess a later decision timestamp.

## Verification and release consequence

E7-092 changes executable integration source and tests. Therefore the remediation branch is a **new executable candidate**, not part of the existing Gate C qualified revision.

Before this candidate can replace `ab725965e96cac7a9769fd1ab15a3e626f920b95` for any future SHADOW runtime, governance requires at minimum:

- approved-local credential-free requalification of the affected Gate C project suites;
- AgentBridge consumer migration and operator review/verification against this ADR;
- release evidence reconciliation binding the exact new executable revision;
- new explicit Product Owner authority for any further provider/SHADOW session, because both prior bounded session authorizations are consumed.

Gate C's previously accepted PASS remains historical/current for its prior qualified revision until governance explicitly requalifies and accepts a replacement. This ADR by itself authorizes no provider execution, SHADOW/PAPER runtime, Gate D, LIVE, order action, provider/account mutation or capital exposure.
