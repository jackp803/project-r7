# Gate C / SHADOW_READY Readiness Baseline — 2026-08-25

> Task: `E7-20260825-066`  
> Owner: E7 Integration / Architecture / System QA / Release  
> Baseline source: `main@bf1326861cfdc4eceabde32b7808126c9b70bf07`  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Gate A: `PASS`  
> Gate B: `PASS`  
> Gate C after this task: `BLOCKED / AUTHORIZED_WORK_IN_PROGRESS`  
> Gate D: `BLOCKED / NOT AUTHORIZED`  
> Project executable verification in this task: `NOT_RUN`  
> Provider/private network activity in this task: `NONE`

## 1. Authority and scope

Product Owner authorization dated `2026-08-25T11:34+08:00` permits governed work through a reviewable Gate C / SHADOW_READY result, including later provider/private **read-only** verification after safe local operator configuration. It does not authorize order placement, simulated order placement as Shadow evidence, account mutation, capital movement/exposure, LIVE, or GitHub-hosted/GitHub-triggered project compute.

This artifact is a static architecture/readiness baseline only. No project code, test suite, provider request, credential, PAPER runtime, SHADOW runtime, or LIVE runtime was executed in this task.

Authoritative repository observations used by this baseline include:

- `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md` — OKX is the active V1 target; dedicated R7 OKX sub-account is the operational account boundary; `BTC_USDT_PERP -> BTC-USDT-SWAP`; isolated margin intent.
- `contracts/SHARED_CONTRACTS_V1.md` — existing `MarketSnapshot`, `RiskDecision`, `OperationalMode`, `HealthStatus`, fail-closed, and approval semantics.
- `src/market_data/__init__.py` / `src/market_data/okx.py` — E1 currently exposes OKX **historical** candles only; live/current MarketSnapshot is explicitly out of scope of the current implementation.
- `src/brokers/okx_demo.py` / `docs/execution/OKX_DEMO_ADAPTER.md` — current E4 OKX adapter is Demo-only, uses an injected transport, can perform bounded private reads, and also contains `submit_entry()` / `POST /api/v5/trade/order` capability.
- `src/execution/gateway.py` — `prepare_entry_order()` is separable from `submit_approved_plan()`, but no persisted OperationalMode guard currently prevents Shadow composition from being wired to a submit-capable broker.
- `src/risk/engine.py` — E5 already rejects stale/unknown market, account, position, or order state, but the current `RiskContext` trusts externally supplied status/freshness booleans rather than deriving them from timestamped Gate C provider observations.
- `src/storage/runtime_models.py`, `docs/platform/E6_GATE_B_PAPER_RUNTIME_DURABILITY.md`, `src/registry/models.py` — E6 persistence is Paper/early-lifecycle focused; `OperationalMode` is defined in the shared contract but is not yet implemented as authoritative durable runtime state.
- current E7 integration/E2E/safety definitions cover Gate A/Gate B, not a Gate C Shadow no-submit composition.

Official OKX API V5 documentation was rechecked publicly on 2026-08-25. Current Global guidance uses `https://openapi.okx.com` for REST, requires regional domains for some registrations, defines `Read`, `Trade`, and `Withdraw` API-key permissions, requires the four private REST auth headers, and documents `x-simulated-trading: 1` for Demo requests. Provider behavior must be rechecked again immediately before any later credential-dependent run.

Official references:

- `https://www.okx.com/docs-v5/en/`
- `https://www.okx.com/docs-v5/log_en/`

## 2. Gate C provider/environment decision

### 2.1 Provider identity

Gate C provider target is settled by the active Product Owner architecture decision:

```text
provider              = OKX API V5
canonical instrument  = BTC_USDT_PERP
provider instrument   = BTC-USDT-SWAP
margin intent          = isolated
operational account    = dedicated R7 OKX sub-account
```

No Pionex private path is part of Gate C.

### 2.2 Gate C authoritative private environment

Gate C SHADOW is defined as **production-provider read-only observation of the dedicated R7 OKX sub-account**, not Demo order execution.

Reasoning:

1. `SHADOW` is an OperationalMode whose purpose is to consume live/provider truth while preventing order submission.
2. The active broker decision makes the dedicated R7 OKX sub-account the operational account boundary.
3. The existing Demo adapter is intentionally submit-capable in its own bounded construction scope; Gate C must be stricter than that capability.
4. Demo/private read evidence may remain useful as non-authoritative development evidence, but it cannot substitute for the production read-only account-state evidence required to call the system `SHADOW_READY`.

Therefore the Gate C credential-dependent environment is:

```text
OKX production/private REST
+ dedicated R7 sub-account
+ API key permission exactly read_only
+ no x-simulated-trading header
+ exact official regional REST domain matching the account registration
```

For OKX Global, current official documentation recommends `https://openapi.okx.com`. The local operator must confirm the account-registration region before credential-dependent verification because OKX currently documents separate regional API domains for some registrations. A mismatched/unknown regional domain is an `OPERATOR_ACTION_BLOCKER`; agents must not guess it.

The existing `OKXDemoAdapter` remains a separate Demo component and is **not** the object injected into the Gate C Shadow runtime.

## 3. Gate C acceptance definition

Gate C may be proposed as `PASS` to PM only when all criteria below have accepted evidence.

### C1 — Provider/environment identity

- Provider is exactly OKX API V5.
- Canonical `BTC_USDT_PERP` maps only to `BTC-USDT-SWAP`.
- Private Shadow observation is bound to the dedicated R7 sub-account.
- The configured API domain is the official domain for that account registration.
- Demo and production-read-only environments are explicit and cannot be silently interchanged.

### C2 — Authentication/signature/clock correctness

Private reads must use current OKX V5 semantics:

```text
OK-ACCESS-KEY
OK-ACCESS-SIGN
OK-ACCESS-TIMESTAMP
OK-ACCESS-PASSPHRASE
signature = Base64(HMAC-SHA256(secret, timestamp + METHOD + requestPath + body))
```

- Timestamp is ISO-8601 UTC with millisecond precision.
- `GET /api/v5/public/time` is checked before the private-read batch.
- R7 Gate C policy is stricter than the provider's documented 30-second rejection window: absolute local/provider clock skew must be `<= 5 seconds`; otherwise abort private verification and mark provider state unknown.
- Query parameters are part of the signed request path; GET has no request body.

### C3 — Credential source and permission boundary

- Credentials are configured only by the local operator in an ignored local secret store/configuration surface.
- Secret values never appear in command-line arguments, Git, chat, fixtures, screenshots, status artifacts, callback payloads, or persisted stdout/stderr.
- `GET /api/v5/account/config` must report API permission exactly `read_only` before any other private Gate C evidence is accepted.
- `trade` or `withdraw` permission is a hard abort even though the Shadow code path is supposed to have no submit capability.
- Raw API key, secret, passphrase, UID, main UID, API label, bound IP list, order IDs, and exact account balances are not durable public evidence.

### C4 — Exact Gate C read-only allowlist

Gate C V0.1 uses REST only. Any method/path not explicitly listed is denied.

#### Public, unauthenticated

```text
GET /api/v5/public/time
GET /api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/market/ticker?instId=BTC-USDT-SWAP
GET /api/v5/market/candles?instId=BTC-USDT-SWAP&bar=<required 1m|15m|1H|4H>
```

Only strategy-required timeframes may be requested by the Shadow composition.

#### Private, authenticated read-only

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/trade/fills?instType=SWAP&instId=BTC-USDT-SWAP
```

`GET /api/v5/trade/order` is intentionally **not** in the initial Shadow allowlist. R7 itself must create no provider order in SHADOW. Unexpected provider pending orders, fills, or exposure are a fail-closed condition; a future need for per-order detail requires an explicit E7 allowlist revision rather than widening the client generically.

Private WebSocket is not required for Gate C V0.1 and is denied. A later WebSocket-read design would require a separate bounded review because login creates a long-lived authenticated channel with a broader provider operation surface.

### C5 — Exact mutation/submit denylist

Shadow provider access is default-deny:

```text
allowed HTTP method = GET only
allowed private paths = exact C4 list only
all other methods/paths = reject before transport
private WebSocket = disabled
```

This mechanically denies, including but not limited to:

- place/batch-place order;
- cancel/batch-cancel order;
- amend/batch-amend order;
- close position;
- algo/conditional/trigger order creation, cancellation, amendment;
- leverage mutation;
- position-mode/account-mode mutation;
- isolated margin add/reduce;
- collateral/trading-configuration mutation;
- transfer/sub-account transfer;
- withdrawal/deposit/funding movement;
- Demo balance adjustment;
- any future provider POST/PUT/PATCH/DELETE endpoint unless Gate C baseline is formally revised.

### C6 — Market-state freshness

Gate C requires E1 to produce the existing canonical `MarketSnapshot` contract from current OKX public data.

Baseline V0.1 acceptance thresholds:

- ticker/provider timestamp age at local observation: `<= 5,000 ms` -> eligible for `HEALTHY` if all other checks pass;
- missing/malformed timestamp, negative age beyond clock tolerance, provider error, or age `> 5,000 ms` -> non-healthy and E5 must reject new exposure planning;
- current candles must preserve existing canonical finality rules: provider-finalized/confirmed, closed interval, no future/unclosed candle influence;
- current public responses may arrive non-monotonically because OKX documents independent market-data caches; E1 must not treat an older second response as newer truth;
- instrument metadata used for provider-specific hypothetical sizing must satisfy the already-reviewed E4 freshness/scheduled-change guards; unknown/stale metadata blocks provider sizing.

### C7 — Provider truth reconciliation and fail-closed behavior

A Shadow observation cycle must bind one coherent evidence boundary containing at least:

- current MarketSnapshot / closed-candle boundary;
- account config and API permission;
- available USDT balance known-status;
- BTC-USDT-SWAP position truth;
- isolated leverage configuration;
- pending-order truth;
- recent-fill truth/checkpoint;
- observation timestamps and source identity.

The following force a fail-closed Shadow cycle:

- any read/auth/signature/provider error;
- clock skew above policy;
- `perm != read_only`;
- account/sub-account identity or account mode not as configured;
- unknown/unsupported position mode;
- non-isolated leverage/margin prerequisite for the planned path;
- malformed, stale, contradictory, or missing required response;
- unexpected non-zero provider position;
- unexpected pending order;
- new/unreconciled fill or other evidence of provider-side activity;
- any disagreement between current provider facts and persisted Shadow checkpoint.

Fail-closed means no provider mutation is attempted, provider state is marked unknown/degraded as appropriate, E5 receives non-safe context, and the cycle may be persisted only as blocked/degraded audit evidence.

### C8 — Shadow runtime semantics / no-submit invariant

The central Gate C invariant is:

> **A SHADOW runtime can observe provider/public/private state and can run Strategy -> Risk -> Execution planning, but no provider order-submission or account-mutation capability is reachable from the Shadow composition, even when valid credentials exist.**

Required architecture:

1. E6-authoritative persisted `OperationalMode.mode == SHADOW` is loaded before the cycle.
2. The Shadow runtime receives a dedicated E4 `ShadowProviderReader` with only the exact GET allowlist.
3. The Shadow runtime does **not** receive `OKXDemoAdapter`, `BrokerSubmitter`, `Broker.submit_order`, `ExecutionGateway.submit_approved_plan`, or any generic authenticated transport exposing non-GET requests.
4. E4 may expose a pure/hypothetical provider sizing/materialization planner for audit, but the returned object is non-submit authority and the Shadow component has no method that can transmit it.
5. Credentials do not change the dependency graph or enable a hidden submit branch.
6. Any attempted non-GET/private-path call is rejected before network transport and recorded only as sanitized safety evidence.
7. Credential-free tests must prove transport mutation count = `0` across healthy, failure, restart, and malicious/miswired scenarios.
8. Credential-dependent verification must additionally prove every actual outbound authenticated request belongs to the GET allowlist and provider mutation count = `0`.

### C9 — E5 risk veto

- Existing E5 fail-closed semantics remain authoritative.
- Market/account/position/order unknown or stale state must yield `REJECT` and `new_exposure_allowed=false` semantics.
- Gate C must not trust arbitrary caller booleans as proof of freshness/known state. A bounded pure E5 derivation/validation layer must derive RiskContext safety fields from timestamped normalized Shadow observations.
- No provider network client belongs in E5.

### C10 — E6 operational mode / persistence / audit / restart

E6 must implement the existing `OperationalMode` contract as authoritative durable state and keep runtime evidence separated by mode.

Required behavior:

- persist `RESEARCH`, `PAPER`, `SHADOW`, `LIVE`, `PAUSED`, `LOCKED` as distinct modes under the shared contract;
- Gate C work may enter only `SHADOW`; it may not infer `LIVE` from credentials, strategy state, or provider availability;
- persist sanitized Shadow cycle evidence/checkpoints without secrets or raw sensitive account identifiers;
- restart restores the exact mode and last accepted provider-observation checkpoint;
- restart with missing/contradictory provider evidence is fail-closed and requires fresh reconciliation before planning;
- Paper journal records cannot be silently reinterpreted as Shadow provider truth;
- Shadow records cannot be promoted into LIVE execution authority;
- no automatic `SHADOW -> LIVE` behavior exists.

### C11 — E7 Gate C executable evidence

Before Gate C can PASS, approved-local evidence must include:

- E1 current-market freshness/finality tests;
- E4 read-only authentication/permission/allowlist/denylist/redaction tests;
- E5 provider-observation-to-risk fail-closed tests;
- E6 OperationalMode/Shadow persistence/restart/separation tests;
- E7 cross-module Shadow integration/E2E/safety tests;
- a credential-free full Gate C matrix using fakes/sanitized fixtures;
- a separately authorized credential-dependent production read-only verification after operator setup;
- proof that no GitHub Actions/CI/hosted/GitHub-triggered compute was used;
- proof that no provider mutation or order submission occurred.

### C12 — Secret redaction / public-repository evidence

Durable evidence may include:

- source revision, local job/request ID, sanitized machine label, OS/Python version;
- provider = OKX, environment = production-read-only Shadow;
- configured regional hostname;
- instrument identity;
- API permission category = `read_only`;
- account level / position mode / sub-account classification without raw UIDs;
- clock skew in milliseconds;
- market age/freshness result;
- booleans/counts such as `balance_known`, `unexpected_exposure=false`, `pending_order_count=0`, `new_unreconciled_fill_count=0`;
- outbound endpoint names/methods and call counts;
- `mutation_request_count=0` / `submit_request_count=0`;
- PASS/FAIL reason codes.

Durable public evidence must not include raw credential values, raw UIDs/main UIDs, API labels, bound IP lists, exact account balances, provider order/fill IDs, or complete provider response bodies.

## 4. Current-state Gate C gap matrix

| Criterion | Current classification | Static evidence / gap |
|---|---|---|
| OKX provider + BTC-USDT-SWAP target | `SATISFIED_STATICALLY` | Active Product Owner broker decision is explicit. |
| Dedicated R7 sub-account boundary | `SATISFIED_STATICALLY` as architecture / `CREDENTIAL_DEPENDENT_EVIDENCE_GAP` operationally | Product baseline is explicit; no provider account has been read in this task. |
| Production read-only Shadow environment | `IMPLEMENTATION_GAP` | Current E4 adapter is `environment=demo` only. |
| OKX REST signature construction | `SATISFIED_STATICALLY` | `sign_okx_rest_request()` matches current OKX V5 HMAC/Base64 semantics. |
| Clock/server-time enforcement | `IMPLEMENTATION_GAP` / `TEST_DEFINITION_GAP` | Current adapter validates timestamp shape but does not perform server-time skew gating. |
| Runtime-only credential representation | `SATISFIED_STATICALLY` | `OKXCredentials` rejects empty values and redacts `repr`; no concrete transport currently logs them. |
| API permission exactly read-only | `IMPLEMENTATION_GAP` | Current `OKXAccountConfigSnapshot` parser does not capture/enforce current OKX `perm`. |
| Dedicated sub-account classification without raw-ID persistence | `IMPLEMENTATION_GAP` | Current parser captures `uid/mainUid`; it does not capture/enforce account `type`, nor define sanitized evidence projection. |
| Exact private GET allowlist | `IMPLEMENTATION_GAP` | Current `_ALLOWED_PRIVATE_PATHS` also permits order POST path and the client exposes submit. |
| Account balance read | `IMPLEMENTATION_GAP` | Required by current E5 `available_balance`; not exposed by current OKX adapter. |
| Leverage-info read | `IMPLEMENTATION_GAP` | Needed to validate isolated leverage prerequisite; not exposed by current adapter. |
| Positions/open orders/fills reads | `SATISFIED_STATICALLY` in Demo adapter / `IMPLEMENTATION_GAP` for production Shadow reader | Parsers/read methods exist but are coupled to Demo credentials/header/config. |
| Provider order submission unreachable | `CONTRACT_OR_ARCHITECTURE_GAP` at composition + `IMPLEMENTATION_GAP` | `OKXDemoAdapter.submit_entry()` and `ExecutionGateway.submit_approved_plan()` exist; no SHADOW dependency boundary blocks injection/reachability. Existing shared contracts are sufficient, but composition is not implemented. |
| Current OKX MarketSnapshot | `IMPLEMENTATION_GAP` | E1 public surface explicitly states live market state is out of scope; only historical candles exist. |
| Closed/current candle path for Shadow E2 runtime | `IMPLEMENTATION_GAP` | Historical loader exists; no bounded current/live public path is exported. |
| MarketSnapshot contract / stale semantics | `SATISFIED_STATICALLY` | `contracts-v0.1` already defines current market health/freshness and stale -> non-healthy semantics. |
| E2 deterministic strategy semantics | `SATISFIED_STATICALLY` | Existing E2 runtime remains provider-neutral; Gate C should reuse it unchanged. |
| E3 validation semantics | `SATISFIED_STATICALLY` / no Gate C implementation task | Gate C does not require a new strategy/backtest engine path. |
| E5 unknown/stale veto core | `SATISFIED_STATICALLY` | Current E5 engine rejects stale/unknown market/account/position/order inputs. |
| E5 trustworthy derivation from provider observation timestamps | `IMPLEMENTATION_GAP` / `TEST_DEFINITION_GAP` | Current `RiskContext` trusts externally supplied flags; no Gate C derivation layer binds them to normalized observations. |
| OperationalMode contract | `SATISFIED_STATICALLY` | `RESEARCH/PAPER/SHADOW/LIVE/PAUSED/LOCKED` already exist in `contracts-v0.1`. |
| E6 durable OperationalMode authority | `IMPLEMENTATION_GAP` | Current registry implementation is early lifecycle only; current runtime persistence is Paper-focused. |
| E6 Shadow audit/restart/mode separation | `IMPLEMENTATION_GAP` / `TEST_DEFINITION_GAP` | No Shadow journal/checkpoint/recovery surface exists. |
| E7 Shadow integration/E2E/safety definitions | `TEST_DEFINITION_GAP` | Current E7 test definitions are Gate A/Gate B oriented. |
| Credential-free Gate C executable evidence | `LOCAL_EXECUTION_EVIDENCE_GAP` | No Gate C implementation exists yet; this task intentionally ran no project code. |
| Credential-dependent production read-only evidence | `CREDENTIAL_DEPENDENT_EVIDENCE_GAP` | Not authorized in this baseline task and no operator credential setup was used. |
| Regional API-domain confirmation | `OPERATOR_ACTION_BLOCKER` for credential-dependent phase | Operator must confirm account registration region and official API hostname; agents must not infer it. |
| Read-only API key creation/configuration | `OPERATOR_ACTION_BLOCKER` for credential-dependent phase | Operator must create/configure a dedicated R7 sub-account read-only key locally; no secret may enter chat/Git. |
| LIVE disabled/unreachable proof | `TEST_DEFINITION_GAP` + later `LOCAL_EXECUTION_EVIDENCE_GAP` | Shared policy forbids LIVE, but no Gate C Shadow composition test yet proves submit path is structurally unreachable. |

## 5. Shared-contract / ADR conclusion

No `contracts/**` or ADR change is required in `E7-20260825-066`.

The existing baseline already defines:

- `MarketSnapshot` and stale/unknown health semantics;
- `RiskDecision` / E5 veto;
- `OperationalMode` including `SHADOW`;
- `HealthStatus`;
- approval/audit principles;
- fail-closed unknown state.

The proven deficiency is implementation/composition, not missing shared vocabulary. Gate C should not add `SHADOW` to `StrategyLifecycleState`; Shadow is an operational mode, while strategy lifecycle approval remains a separate concern.

A future contract/ADR change is required only if implementation proves that E4 normalized provider observations or E6 durable Shadow evidence cannot be bound unambiguously with existing contracts plus bounded owner-local records. Do not preemptively create a duplicate shared provider model.

## 6. Recommended task fan-out in dependency order

Only owners with real gaps are listed.

### Phase 1 — parallel foundation tasks

#### E1 — current OKX public market-state surface

Implement a bounded current/public OKX path that produces canonical `MarketSnapshot` plus current finalized candles for the existing strategy timeframes.

Required boundaries:

- public endpoints only;
- no credentials/private API;
- ticker timestamp/freshness calculation;
- stale/out-of-order/non-monotonic response handling;
- provider `confirm` finality preserved for candles;
- exact `BTC_USDT_PERP -> BTC-USDT-SWAP` mapping;
- local-only tests.

#### E4 — production read-only Shadow provider boundary

Create a separate read-only OKX Shadow client/reader rather than widening `OKXDemoAdapter`.

Required boundaries:

- production/private read-only environment with official regional-domain configuration;
- exact GET allowlist from C4;
- all other methods/paths rejected before transport;
- no Demo header in production Shadow;
- parse/enforce `perm=read_only` and sub-account/account-mode facts;
- server-time skew guard;
- balance + leverage-info reads added;
- sanitized observation projection;
- no submit/cancel/amend/mutation method on the Shadow client;
- optional pure hypothetical provider sizing/planning may exist, but no transport authority;
- local fake-transport tests prove mutation count zero.

Do not modify E5 risk rules or E6 operational mode in this task.

#### E6 — OperationalMode and Shadow persistence authority

Implement the existing `contracts-v0.1` OperationalMode authority and a mode-separated sanitized Shadow audit/restart journal.

Required boundaries:

- `SHADOW` persists distinctly from PAPER/LIVE;
- restart restores mode/checkpoint exactly;
- no automatic LIVE transition;
- no credentials/raw UIDs/exact balance/order IDs in durable public-facing evidence;
- unknown/restart mismatch remains fail closed;
- additive migration only; existing Gate B Paper durability semantics preserved;
- local-only storage/platform/registry tests.

### Phase 2 — after E1 + E4 normalized observation surfaces are stable

#### E5 — Gate C risk-context derivation

Add a pure broker-neutral derivation/validation layer that maps normalized timestamped Gate C market/account/position/order observations into the existing `RiskContext`.

Required boundaries:

- no provider network client in E5;
- no credential/provider endpoint knowledge beyond normalized facts;
- freshness/known booleans derived, not caller-asserted;
- unknown/stale/contradictory observation yields E5 reject/new-exposure-disabled semantics;
- current risk caps/kill switch remain unchanged;
- local-only risk tests.

### Phase 3 — after E1/E4/E5/E6 merge

#### E7 — Shadow composition + Gate C test definitions

Build the cross-module Shadow composition and integration/E2E/safety definitions.

Mandatory proofs:

- persisted mode is SHADOW;
- current E1 data -> unchanged E2 runtime -> E5 risk -> E4 prepare/hypothetical planning -> E6 audit;
- no submit-capable object is injected;
- synthetic valid credentials do not create a submit branch;
- malicious/miswired mutation attempts are rejected before transport;
- stale/auth/clock/provider/position/order/fill/restart failures fail closed;
- Paper/Shadow/Live storage and runtime evidence remain distinct;
- secret redaction;
- transport request audit contains GET allowlist only and zero mutation requests.

### Phase 4 — executable evidence

After all implementation/test PRs are reviewed and merged, E7 should receive a separate exact-revision Local Job task for the complete **credential-free** Gate C matrix. No suite should be executed from this baseline task.

### Phase 5 — local operator prerequisite + credential-dependent evidence

Only after credential-free evidence passes:

1. local operator configures the dedicated R7 OKX sub-account and creates a `read_only` API key;
2. local operator confirms the correct official regional REST domain and account mode/position mode;
3. secrets remain local and are never pasted into chat/Git;
4. E7 receives a separate exact-revision credential-dependent read-only verification task;
5. PM reviews both evidence classes before any Gate C PASS.

No E2 or E3 implementation task is recommended from this baseline because no Gate C-specific defect/gap was found in their owned semantics.

## 7. Credential-free approved-local verification matrix

This matrix is a **future plan**, not evidence from this task.

| Area | Minimum future command/suite | Required Gate C assertions |
|---|---|---|
| E1 current market | `python -m unittest discover -s tests/market_data -p "test_*.py" -v` | current ticker -> MarketSnapshot; freshness threshold; non-monotonic/stale fail closed; current finalized candles only |
| E4 reader/planner | `python -m unittest discover -s tests/brokers -p "test_*.py" -v` | exact GET allowlist; `perm=read_only`; regional/demo separation; clock guard; redaction; no POST path; hypothetical sizing only |
| E4 gateway regression | `python -m unittest discover -s tests/execution -p "test_*.py" -v` | prepare remains mechanical; Shadow does not call submit; Gate B behavior preserved |
| E5 risk | `python -m unittest discover -s tests/risk -p "test_*.py" -v` | provider-derived stale/unknown/contradictory facts reject; no caller freshness spoof |
| E6 persistence | `python -m unittest discover -s tests/storage -p "test_*.py" -v` | OperationalMode/Shadow journal persistence; restart; sanitized evidence; Paper/Shadow separation |
| E6 platform/registry | `python -m unittest discover -s tests/platform -p "test_*.py" -v` and `python -m unittest discover -s tests/registry -p "test_*.py" -v` | authoritative mode transitions/checks; no automatic LIVE; audit authority |
| E7 integration | `python -m unittest discover -s tests/integration -p "test_*.py" -v` | healthy Shadow vertical slice composes correctly; provider mutation transport count zero |
| E7 E2E | `python -m unittest discover -s tests/e2e -p "test_*.py" -v` | current provider inputs -> strategy/risk/plan/audit only; restart remains no-submit |
| E7 safety | `python -m unittest discover -s tests/safety -p "test_*.py" -v` | auth failure, stale data, clock skew, trade-permission key, unexpected exposure/order/fill, malformed state, malicious method/path all fail closed; secrets redacted |

A later E7 qualification task should freeze exact suite order/revision and determine whether Gate B regression suites must be rerun in the same qualification job. No executable claim is made here.

## 8. Credential-dependent approved-local verification plan

### 8.1 Operator prerequisites

Before E7 requests any credential-dependent Local Job, all must be true:

```text
dedicated R7 OKX sub-account = EXISTS
API key permission           = read_only only
Trade permission             = ABSENT
Withdraw permission          = ABSENT
regional REST domain         = OPERATOR CONFIRMED from account registration
account mode                 = configured/known (V1 expected Futures acctLv=2)
position mode                = explicitly configured as one reviewed supported mode
R7 target margin intent      = isolated
provider position            = expected flat for baseline Shadow verification
provider pending orders      = expected none
secret injection             = local ignored secret store only
```

Trusted-IP binding is required where the approved local environment has a stable egress IP. If IP restriction is not operationally feasible, record `IP_ALLOWLIST_UNAVAILABLE` and obtain PM/Product Owner review before the credential-dependent run rather than silently weakening the operator boundary.

### 8.2 Credential-dependent action

The later job must execute only a dedicated read-only verification entrypoint that has no generic arbitrary URL/method option and no order-submit dependency.

Expected actual provider requests are limited to C4. The job must abort immediately if any attempted outbound method is not GET or any path is not allowlisted.

### 8.3 Sanitized durable evidence

Persist only:

- task/request/job IDs and exact source revision;
- approved local environment metadata;
- provider/environment/hostname/instrument;
- server-time and clock-skew result;
- `perm=read_only` result;
- account level, position mode, and sanitized sub-account classification;
- `balance_known` boolean, not exact balance;
- position/pending-order/new-fill counts and safe/unsafe classification without provider IDs;
- market age/freshness classification;
- exact allowlisted endpoint names and call counts;
- `authenticated_GET_count`;
- `submit_request_count=0`;
- `mutation_request_count=0`;
- final PASS/FAIL reason codes;
- explicit redaction check result.

### 8.4 Hard abort conditions

Abort and report `BLOCKED`/`FAIL` without retrying a broader surface if any occur:

- secret appears in stdout/stderr/callback/durable artifact;
- API permission is not exactly `read_only`;
- account is not the operator-confirmed dedicated R7 sub-account;
- account mode/position mode is unsupported or mismatched;
- wrong/unknown regional API domain;
- authentication/signature error not attributable to a safely correctable local clock issue;
- clock skew `> 5s`;
- public market data stale/unknown;
- malformed/contradictory provider payload;
- unexpected nonzero exposure;
- pending provider order;
- unreconciled recent fill/provider activity;
- any code path attempts POST/PUT/PATCH/DELETE/private WS;
- any order/cancel/amend/account-mutation capability becomes reachable;
- clean exact-revision local execution/evidence conditions cannot be established.

No credential-dependent task may repair account mode, position mode, leverage, margin, balances, orders, or positions. Any such prerequisite is a local-operator action outside the job.

## 9. Security and redaction rules

Gate C adds no exception to the public-repository secret policy.

- Never commit `.env` or live local config.
- Never paste key/secret/passphrase into chat or task mailboxes.
- Never log authenticated headers or signature inputs containing secrets.
- Request objects may expose header **names** only in repr/logging, never values.
- Provider responses must be projected to sanitized facts before durable evidence.
- UID/mainUid/API label/IP list/order IDs/fill IDs/exact balances remain local-only unless a future security review approves a non-sensitive derivative.
- Synthetic credentials in tests must be obviously fake and must not resemble any real user secret.
- If a real secret reaches Git/chat/log evidence, stop normal work and treat it as a security incident.

## 10. Gate C disposition after E7-066

```text
Gate A — RESEARCH_READY = PASS
Gate B — PAPER_READY    = PASS
Gate C — SHADOW_READY   = BLOCKED / AUTHORIZED_WORK_IN_PROGRESS
Gate D — LIVE_READY     = BLOCKED / NOT AUTHORIZED

PAPER runtime  = NOT STARTED
SHADOW runtime = NOT STARTED
LIVE           = UNAUTHORIZED
provider/private call in E7-066 = NONE
credentials used in E7-066      = NONE
GitHub project compute          = NOT USED
```

Gate C is not close to a formal PASS yet: current main has concrete E1/E4/E5/E6 implementation gaps, E7 test-definition gaps, no credential-free Gate C execution evidence, and no credential-dependent read-only evidence.

The baseline itself is complete and provides PM a bounded fan-out plan. Later credential/account/domain setup is intentionally an operator prerequisite and does not block completion of this static baseline task.
