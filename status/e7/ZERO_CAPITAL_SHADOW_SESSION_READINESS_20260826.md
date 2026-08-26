# Zero-Capital SHADOW Session Readiness — E7-20260826-086

## Scope

- task_id: `E7-20260826-086`
- task_type: `STATIC / SOURCE / READINESS AUDIT + EXECUTION PLAN`
- qualified_executable_revision: `ab725965e96cac7a9769fd1ab15a3e626f920b95`
- Gate C: `PASS`
- Product Owner authorization: `status/PRODUCT_OWNER_ZERO_CAPITAL_SHADOW_AUTHORIZATION_20260826.md`
- PM Gate C acceptance: `status/PM_GATE_C_FINAL_REVIEW_20260826.md`
- release state: `status/RELEASE_GATES.md`

E7-086 executes no project/provider code, reads no credentials, creates no Local Job Request, and does not start PAPER, SHADOW, Gate D, or LIVE.

## Readiness verdict

```text
accepted_cross_module_shadow_cycle = SUPPORTED
architecture_or_domain_code_change_required = NO
qualified_executable_source_test_drift = NONE FOUND
bounded_session_execution_ready_via_registered_local_action = NO
execution_dependency = LOCAL_ACTION_NOT_REGISTERED
Gate C — SHADOW_READY = PASS / UNCHANGED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

The accepted E1/E2/E4/E5/E6/E7 implementation is sufficient to compose one fail-closed Shadow cycle and repeat such cycles under a bounded external session supervisor. The missing capability is not a domain architecture gap: the current AgentBridge catalog has no canonical action whose committed/operator-owned contract represents one 30-minute, maximum-300-HTTPS-GET SHADOW runtime session.

`GATE_C_OKX_PRODUCTION_READONLY` remains a one-shot production read-only verification action and must not be reinterpreted as a runtime session action.

A comparison from `ab725965e96cac7a9769fd1ab15a3e626f920b95` to current `main` found only governance/coordination/status/evidence changes and no production source or test-definition change, so the accepted executable baseline remains the qualified revision.

## Cross-module surface audit

### E1 — current market state / finality / freshness

Accepted surface: `src/market_data/current.py`.

- `normalize_okx_ticker` produces canonical `MarketSnapshot` and rejects stale observations above `5000 ms`, materially future timestamps, malformed prices, provider errors, and invalid bid/ask state.
- `normalize_okx_current_candles` exposes only provider-confirmed candles whose canonical close boundary has passed; unconfirmed/future candles are withheld and malformed/gapped ordering fails closed.
- `CurrentMarketState` rejects non-monotonic replacement of accepted current truth.
- `OkxPublicCurrentMarketSource` performs GET-only ticker/current-candle reads.
- E1's historical default base URL is `https://www.okx.com`, but the current source accepts an explicit `base_url`. The future session harness must construct the current-market source with exactly `https://openapi.okx.com` and fail before network traffic on any configured/confirmed host mismatch. No E1 code change is required.

### E2 — deterministic strategy runtime

Accepted surface: `src/strategy/runtime.py` consumed unchanged by `ShadowComposition`.

- schema baseline is `contracts-v0.1`;
- runtime family/version are explicit and deterministic;
- the accepted runtime consumes a parsed strategy, canonical finalized Candle sequence, and UTC evaluation boundary;
- E2 has no provider credential or submission responsibility;
- the current supported StrategyDefinition boundary uses exactly one required timeframe, so the session can obtain one current-candle page per cycle for the strategy timeframe.

### E4 — production read-only provider boundary

Accepted surface: `src/brokers/okx_shadow.py`.

- `OKXShadowProviderReader` is the accepted production read-only provider dependency;
- its public callable surface is `observe` only when admitted by E7 composition;
- authenticated requests are GET-only and default-deny outside the exact accepted private allowlist;
- each complete provider observation contains one public-time GET plus six private GETs;
- provider permission, account level, position mode, dedicated-subaccount status, zero/known balance truth, position exposure, isolated leverage, pending orders, recent fills/checkpoint and clock health are normalized into sanitized state;
- exact runtime balance is kept only in the in-memory `OKXShadowReadResult` and redacted from repr/durable public projection;
- credentials and prepared-request representations do not expose secret values.

### E5 — provider-observation-derived risk state

Accepted surface: `src/risk/context_derivation.py` plus the existing risk engine.

- caller-provided safe flags are not accepted;
- E5 derives market/account/position/order safety from E1 `MarketSnapshot` and E4 `OKXShadowReadResult`;
- provider/API/environment identity, read-only permission, account level, position mode/subaccount classification, clock health, balance truth, position truth, isolated leverage, private GET count, pending orders, fill checkpoint and unreconciled fills are checked fail closed;
- unknown/stale/contradictory observation axes prevent new-exposure safety.

The future zero-capital session adds a stricter session-level rule: runtime available USDT must be explicitly classified exactly zero. A nonzero or unknown classification terminates the session; it never causes a funding or mutation action.

### E6 — OperationalMode.SHADOW / persistence / restart

Accepted surface: `src/storage/operational_mode.py`.

- `OperationalMode.SHADOW` is an authoritative persisted mode;
- Shadow checkpoints accept only a fixed sanitized schema and reject unexpected exposure, nonzero pending/unreconciled activity, unknown required truth, non-read-only permission, wrong environment/provider/instrument, or unsafe references;
- durable checkpoint material contains sanitized observation references/hashes rather than provider identifiers or exact balance;
- recovery after restart requires fresh reconciliation before Shadow planning becomes safe again;
- the store does not provide provider submission or LIVE promotion capability.

Before the first provider observation in the future session, `OperationalModeStore.recover()` must establish authoritative `SHADOW`. The session must not silently coerce an unsafe/unknown mode. Any separately governed local transition into SHADOW must use the accepted E6 audit/authority mechanism and the Product Owner authorization evidence before provider traffic.

### E7 — ShadowComposition / no-submit integration

Accepted surface: `src/integration/shadow_composition.py`.

- the composition admits the exact `OKXShadowProviderReader` and validates the provider public callable surface as exactly `{observe}`;
- Demo/submit-capable provider objects are rejected;
- no Broker, ExecutionGateway, OrderRequest, submit/cancel/amend/close/transfer capability is exposed;
- caller injection of the E4 fill checkpoint is not allowed;
- authoritative SHADOW mode and canonical finalized E1 candles are checked before provider observation;
- provider observation flows through E5 derivation and E6 sanitized checkpoint persistence;
- public cycle output contains non-authoritative Shadow planning evidence, not `TradeIntent`, `RiskDecision`, `ApprovedTradePlan`, or executable order authority.

Accepted integration/E2E/safety definitions additionally prove mode-before-transport behavior, GET-only batches, zero provider mutations, degraded-state rejection, unclosed/future-candle pretransport rejection, secret/raw-provider-data redaction, and restart requiring fresh provider reconciliation.

## Future session start prerequisites

All of the following must be established before the authorized session sends its first HTTPS GET:

1. The one-session Product Owner authorization is current and has not already been consumed by a prior started bounded session.
2. The dedicated local worktree is exactly `ab725965e96cac7a9769fd1ab15a3e626f920b95` and clean.
3. Execution is on the currently registered Product-Owner-approved Windows computer, not GitHub/hosted/GitHub-triggered compute.
4. The local secure/DPAPI credential surface exists and can be consumed without displaying, logging, copying, or persisting credential values.
5. E4 configured and operator-confirmed REST base URL are both exactly `https://openapi.okx.com`.
6. E1 current-market source is explicitly constructed with `base_url=https://openapi.okx.com`; its historical default must not be used implicitly for this authorized session.
7. The authoritative operational-mode store is available and its accepted E6 audit/recovery semantics can establish `SHADOW` before provider observation; conflict/unknown/unsafe mode stops pretransport.
8. The E2 StrategyDefinition is already parsed/compatible with `contracts-v0.1` and the accepted runtime version; the required timeframe is known before the network loop starts.
9. E5 policy/proposal inputs and counters are locally available and valid; unknown local risk state stops rather than being guessed.
10. A session-wide monotonic deadline and one shared HTTPS-GET budget are armed before any E1 or E4 network call.
11. Mutation and submit counters begin at zero, and the admitted dependency graph is revalidated as no-submit/no-mutation before the first provider call.
12. A sanitized durable session-evidence sink is available without requiring credentials, raw private responses, exact balance, UIDs, signatures, tokens/cookies, provider order/fill IDs, browser auth, or unnecessary local paths.

## Hard 30-minute and 300-GET enforcement

The future canonical local action must own one session supervisor around the accepted E1/E2/E4/E5/E6/E7 surfaces.

### Duration cap

```text
maximum elapsed duration = 1800 seconds
clock for enforcement = monotonic local clock
wall-clock evidence = UTC start/end timestamps
```

- Start the monotonic deadline before the first session/provider operation that can lead to network traffic.
- Check the remaining deadline before every HTTPS dispatch and before beginning each new Shadow cycle.
- Each network operation must use a timeout no greater than the remaining session deadline so a blocked request cannot extend the session beyond the authorized window.
- At or after the deadline, deny further dispatch and terminate with `SESSION_DURATION_LIMIT_REACHED`.
- Wall-clock timestamps are evidence only; enforcement must not rely on a mutable wall clock.

### Shared HTTPS GET cap

```text
maximum HTTPS GET attempts = 300
counter scope = all E1 + E4 HTTPS GET dispatch attempts in the session
increment timing = reserve/increment before dispatch
301st attempt = structurally denied
```

A single shared budget must wrap both E1 public market traffic and E4 read-only account/provider traffic. Failed/time-out dispatch attempts still consume the budget because they were attempted network operations.

For the current one-timeframe cycle shape, one complete cycle is expected to require:

```text
E1 ticker GET                 = 1
E1 current-candles GET        = 1
E4 public-time GET            = 1
E4 private GET allowlist      = 6
---------------------------------
expected complete-cycle GETs  = 9
```

Therefore a supervisor must not start a new full cycle unless at least nine GET slots remain. Under the current shape, at most 33 complete nine-GET cycles fit under the 300-GET cap (`297` attempts). The authoritative safety mechanism is the shared per-dispatch counter, not the derived cycle limit.

If a cycle stops early because of a fail-closed condition, the evidence must preserve the actual attempted counts; no retry is authorized merely to consume the remaining budget.

## Mandatory fail-closed stop conditions

The future session must terminate without scope expansion on any of the following:

- `AVAILABLE_BALANCE_IS_ZERO` is not explicitly true from the current observation;
- any unexpected BTC-USDT-SWAP position/exposure appears;
- pending-order count is nonzero or unknown;
- new/unreconciled fill activity is nonzero or unknown;
- provider permission is anything other than exactly `read_only`;
- provider/API/environment/hostname/account/subaccount/position-mode classification is invalid, contradictory, or unknown;
- provider clock is unhealthy/unknown or exceeds the accepted 5000 ms skew boundary;
- current market state is stale, future, nonhealthy, malformed, nonmonotonic, or required finalized candles are unavailable;
- isolated leverage truth is unknown/invalid under the accepted read-only semantics;
- E5 derivation/risk state is unknown or fail-closed;
- E6 operational mode is not authoritative SHADOW, recovery reports conflict/unsafe state, or fresh reconciliation requirements cannot be met;
- any submit or mutation capability becomes reachable, any non-GET request is constructed/attempted, or mutation/submit counters become nonzero;
- exact qualified revision or clean dedicated worktree can no longer be proven;
- the shared 300-GET budget is exhausted or a complete next cycle cannot fit in the remaining budget;
- the 1800-second monotonic deadline is reached;
- credential/provider-response/evidence handling cannot remain sanitized;
- any uncaught/unknown runtime/provider/storage exception prevents proving safe state.

No stop condition may trigger an account change, funding action, order action, retry escalation, or broader provider capability.

## Required durable sanitized session evidence

The future runtime result must persist, at minimum:

```text
session_authorization_ref
session_id / request_id / canonical action_id
exact executable revision
clean-worktree classification
approved-local-Windows classification
start_timestamp_utc
end_timestamp_utc
elapsed_seconds
total_https_get_count
private_get_count
public_market_get_count
public_provider_time_get_count
MUTATION_REQUEST_COUNT=0
SUBMIT_REQUEST_COUNT=0
available_balance_is_zero = YES/NO/UNKNOWN only
provider/api/environment/hostname classifications
permission_category
account-level / position-mode / dedicated-subaccount classifications without IDs
market freshness/finality/health classification
position-known / unexpected-exposure classification
isolated-leverage-known/valid classification
pending-order classification/count
unreconciled-fill classification/count without provider IDs
operational mode/revision classification
checkpoint/reconciliation/restart classification as applicable
cycle_count_completed
terminal_stop_reason
session_result = COMPLETE / FAIL_CLOSED / BLOCKED
```

The durable evidence must also explicitly state that no credential value, exact balance, raw UID/mainUID, signature, token/cookie, browser authentication, raw private provider response, provider order/fill identifier, or unnecessary local filesystem path was persisted/displayed.

The exact balance must never be durable; only the zero/nonzero/unknown classification is permitted.

## Canonical AgentBridge execution dependency

Current catalog review:

```text
GATE_C_OKX_PRODUCTION_READONLY = REGISTERED / ONE-SHOT VERIFICATION ONLY
30-minute / 300-GET SHADOW session action = NOT REGISTERED
execution_dependency = LOCAL_ACTION_NOT_REGISTERED
```

Required operator capability:

> One deny-by-default canonical AgentBridge action that executes exactly one Product-Owner-authorized zero-capital SHADOW session on the registered local Windows computer, pins the clean qualified revision, consumes credentials only through the approved DPAPI/local secret boundary, pins both E1 and E4 provider traffic to `openapi.okx.com`, runs the accepted E1→E2→E4→E5→E6→E7 Shadow cycle without exposing execution authority, enforces a shared pre-dispatch maximum of 300 HTTPS GET attempts and a monotonic 1800-second deadline, forbids every mutation/submit path, stops on every mandatory fail-closed condition, and emits only the sanitized durable evidence defined above.

Proposed canonical identity for operator/PM review only:

```text
GATE_C_ZERO_CAPITAL_SHADOW_SESSION
```

This is a proposal only. E7-086 does not add it to `coordination/LOCAL_ACTION_CATALOG.md`, does not assume it is allowlisted, and does not create a Local Job Request.

## Execution boundary confirmation

```text
project code execution = NOT_RUN / NOT AUTHORIZED
provider requests = NONE
credentials = NOT READ / NOT REQUESTED / NOT USED
Local Job Request = NOT CREATED
GitHub Actions / CI / hosted runner / GitHub-triggered compute = NOT USED
PAPER runtime = NOT STARTED
SHADOW runtime = NOT STARTED
provider/order mutation = NONE
capital movement/exposure = NONE
Gate D / LIVE = NOT STARTED / NOT AUTHORIZED
```

`NOT_RUN` is not session PASS evidence. It records that E7-086 is the required static readiness/plan task only.

## Completion

```text
readiness_plan = COMPLETE
architecture_or_domain_change_required = NO
execution_dependency = LOCAL_ACTION_NOT_REGISTERED
next_owner = PM / OPERATOR GOVERNANCE
Gate C = PASS / UNCHANGED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

E7 stops after this readiness determination. It does not self-start implementation, operator allowlisting, Local Job execution, provider access, SHADOW runtime, Gate D, LIVE, remediation, or another task.
