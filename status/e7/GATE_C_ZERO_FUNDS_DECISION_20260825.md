# Gate C Zero-Funds Decision — 2026-08-25

- task_id: `E7-20260825-075`
- owner: `E7 Integration / Architecture / System QA / Release`
- decision: `DONE / ZERO_BALANCE_SEMANTICS_ACCEPTED / next_owner=E4`
- executable/provider verification in this task: `NOT_PERFORMED / PROHIBITED`
- Gate C: `BLOCKED`
- SHADOW runtime: `NOT STARTED`
- Gate D / LIVE: `BLOCKED / NOT AUTHORIZED`

## 1. Scope and established sanitized evidence

This is a static provider-semantics and project-safety decision only. It does not execute project code, call OKX private endpoints, modify provider state, request credentials, or expose account-sensitive values.

The task-provided sanitized local evidence already established:

```text
REST hostname                 = openapi.okx.com
TLS/public-time read          = PASS
clock status                  = HEALTHY
provider permission           = read_only
account level                 = 2
position mode                 = net_mode
dedicated sub-account         = CONFIRMED
account authentication        = PASS
balance interpretation        = BALANCE_USDT_UNKNOWN
provider mutation             = NONE
order/transfer/withdraw       = NONE
credential disclosure         = NONE
```

Durable local evidence references: `JOB-7D0BC5AA6E72`, `JOB-EB98D5532783`.

No exact balance, credential, UID, raw provider response, provider order/fill identity, cookie, token, browser-auth material, or unnecessary user-specific path is recorded here.

## 2. Authoritative project behavior reviewed

Exact accepted provider boundary reviewed at source revision `83be94fbc4ee666156c2aaf7a7141b3eda9a4b4c`:

- `src/brokers/okx_shadow.py`
- `tests/brokers/test_okx_shadow.py`
- `contracts/SHARED_CONTRACTS_V1.md`
- `docs/adr/ADR-0003-okx-derivative-sizing-and-operational-boundary.md`
- `status/e7/GATE_C_READINESS_BASELINE_20260825.md`
- `src/brokers/okx_demo.py`
- `docs/execution/OKX_DEMO_ADAPTER.md`

Current production Shadow implementation requests exactly:

```text
GET /api/v5/account/balance?ccy=USDT
```

and currently treats anything other than exactly one `details` item whose `ccy == "USDT"` as `BALANCE_USDT_UNKNOWN`. Existing tests explicitly prove that an empty `details` list fails closed as unknown, while an explicit USDT detail with `availBal="0"` is known zero.

The shared contract requires unknown or inconsistent account state to fail closed and never become permission for new exposure. This decision therefore may narrow a provider-specific interpretation only where current official provider documentation makes the state unambiguous; all other shapes remain unknown.

## 3. Current official OKX V5 documentation reviewed

Official documentation was rechecked on 2026-08-25:

- `https://www.okx.com/docs-v5/en/`
- `https://www.okx.com/docs-v5/trick_en/`

The current `GET /api/v5/account/balance` documentation states that the endpoint retrieves assets with **non-zero balance** and supports filtering with `ccy`.

The current OKX V5 guidance further states that, for REST balance requests with `ccy` specified, a currency is returned regardless of whether its balance is zero or non-zero **as long as the user has possessed that currency before**.

These two documented rules jointly establish the narrow zero-funds case:

1. a positive/non-zero current USDT balance belongs to the endpoint's returned asset set;
2. an explicitly requested USDT with prior possession may still be returned with zero balance;
3. an explicitly requested USDT with no returned USDT detail can therefore represent the documented never-possessed/zero-current-balance case, not a positive available-USDT state.

The provider documentation does not authorize treating arbitrary malformed, contradictory, multi-match, wrong-currency, provider-error, or structurally missing account data as zero.

## 4. E7 decision

### 4.1 Accepted zero-balance semantic

E7 accepts a minimal provider-adapter interpretation for the exact read-only Gate C request:

```text
GET /api/v5/account/balance?ccy=USDT
```

A missing USDT detail may be normalized to known available USDT balance `0` **only** when all of the following are true:

- provider response is a successful OKX response (`code == "0"`);
- the response has the otherwise-valid account-balance envelope expected by the accepted Shadow reader;
- `details` is a valid sequence;
- `details` is empty, i.e. there is no contradictory returned currency item;
- the request was exactly scoped to `ccy=USDT`;
- the observation remains bound to the already-accepted authenticated production read-only Shadow path.

For that exact shape, the E4 adapter may set:

```text
usdt_balance_known        = true
runtime_available_balance = Decimal("0")
```

This is a provider-normalization rule, not permission to trade. A zero available balance naturally prevents positive capital-based new-exposure sizing and does not relax any other Gate C checks.

### 4.2 Fail-closed boundary retained

The following remain `BALANCE_USDT_UNKNOWN` or the existing malformed/provider error classification and must not be normalized to zero:

- provider error / non-success code;
- missing or malformed `data` envelope;
- wrong number/type of account objects under the accepted reader contract;
- `details` missing or not a sequence;
- a returned detail for a currency other than USDT despite the exact `ccy=USDT` request;
- duplicate USDT details;
- one USDT detail with missing, malformed, negative, non-finite, or otherwise invalid `availBal`;
- any response shape for which the exact request identity cannot be proven;
- any contradictory account/position/order/fill/provider truth.

Unknown remains unknown. This decision does not permit `None -> 0` as a general fallback.

## 5. Minimal implementation assignment

`next_owner = E4`.

E4 may implement only the provider-local normalization above and update its owned tests accordingly. E7 does not modify E4 production code in this task.

Minimum expected E4 regression coverage:

- exact `ccy=USDT` + valid envelope + empty `details` -> known `Decimal("0")`;
- exact `ccy=USDT` + one valid USDT detail with `availBal="0"` -> remains known zero;
- one valid positive USDT detail -> existing parsing unchanged;
- wrong-currency detail -> fail closed, not zero;
- duplicate USDT details -> fail closed;
- malformed detail/envelope/provider error -> fail closed;
- no widening of private endpoint/method allowlist;
- no mutation/submit capability introduced;
- durable/public evidence remains balance-redacted.

Executable verification after any E4 change remains local-only and requires a separately issued task/review path. This E7 task authorizes no execution.

## 6. Demo-path determination

A separately governed Demo route is **not required to resolve this specific zero-capital production balance semantic**, because current official production REST balance documentation provides sufficient normative authority for the narrow empty-`details` interpretation above.

Demo remains a separate environment and cannot substitute for production Gate C evidence. Current official OKX documentation requires a Demo Trading API key and `x-simulated-trading: 1` on Demo requests; the existing project Demo adapter is explicitly Demo-only and submit-capable. No Demo execution is authorized or started by this decision.

## 7. Release interpretation

```text
zero-funds provider semantic decision = ACCEPTED / NARROW EMPTY-DETAILS CASE ONLY
next_owner                             = E4
Gate C — SHADOW_READY                  = BLOCKED / E4 IMPLEMENTATION + SEPARATELY GOVERNED RE-VERIFICATION REQUIRED
SHADOW runtime                         = NOT STARTED
Gate D — LIVE_READY                    = BLOCKED / NOT AUTHORIZED
LIVE                                   = UNAUTHORIZED
```

The Product Owner does not need to deposit real funds merely to make USDT appear in the production sub-account for this semantic case.

## 8. Safety / infrastructure confirmation

No provider/private request, project-code execution, credential request, deposit, transfer, order, cancellation, account mutation, Trade/Withdraw permission change, capital exposure, PAPER/SHADOW runtime, Gate D/LIVE action, GitHub Actions/CI/hosted/GitHub-triggered compute, production source/test change, or other-agent STATUS change occurred in E7-075.
