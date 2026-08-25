# E1 Current Task

- task_id: `E1-20260825-003`
- issued_at: `2026-08-25T12:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e1-gate-c-current-market-20260825`
- authority: `agents/E1_MARKET_DATA.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75 merge `c158c8ca4fd01fa9314dd2e7a1a9c0c0d2935624`, Product Owner Gate C / SHADOW-only authorization

## Objective

Close only the E1 Gate C implementation gap identified by `status/e7/GATE_C_READINESS_BASELINE_20260825.md`: provide a current OKX public market-state surface that produces the existing canonical `MarketSnapshot` and finalized current Candle inputs required by Shadow.

Provider scope is public OKX API V5 only. No account/private API, credentials, risk, execution, persistence, or Shadow runtime ownership belongs in this task.

## Required behavior

Implement within E1 ownership a bounded current/near-live polling surface for:

```text
canonical symbol = BTC_USDT_PERP
provider symbol  = BTC-USDT-SWAP
provider         = OKX API V5 public REST
```

Use only the Gate C public allowlist where needed:

```text
GET /api/v5/public/time
GET /api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/market/ticker?instId=BTC-USDT-SWAP
GET /api/v5/market/candles?instId=BTC-USDT-SWAP&bar=<1m|15m|1H|4H as requested>
```

Requirements:

1. Normalize current ticker/provider timestamps into the existing canonical `MarketSnapshot` contract; do not add strategy/risk opinions.
2. Preserve canonical UTC/Decimal semantics and provider/source identity.
3. Implement Gate C freshness semantics: a valid ticker/provider observation age `<= 5,000 ms` may be healthy if all other checks pass; missing/malformed timestamp, materially future timestamp outside clock tolerance, provider failure, or age `> 5,000 ms` must be non-healthy/typed failure rather than fake data.
4. Current candles must obey existing closed-candle rules. Only provider-finalized/confirmed candles whose interval is closed may be exposed as final strategy input; provisional/unclosed candles must not be silently promoted.
5. Handle non-monotonic public responses safely: a later-received but older provider observation must not replace newer accepted truth.
6. Keep symbol/timeframe mapping deterministic for supported project timeframes (`1m`, `15m`, `1h`, `4h`).
7. Provider errors, malformed payloads, unsupported symbol/timeframe, stale data, duplicates, gaps, and out-of-order data remain visible through structured failures/health metadata.
8. Do not introduce WebSocket in this task.
9. Do not make shared-contract changes. If the accepted `MarketSnapshot` contract proves insufficient, stop with exact evidence and request E7 review rather than inventing a parallel shared type.

## Tests

Add/update only E1-owned tests/fixtures proving at minimum:

- current ticker -> canonical MarketSnapshot normalization;
- healthy boundary and stale `> 5,000 ms` behavior;
- malformed/missing/future timestamp fail-closed behavior;
- older second response cannot overwrite newer truth;
- finalized candle accepted;
- unconfirmed/unclosed candle rejected or withheld;
- 1m/15m/1h/4h mapping;
- malformed/provider-error behavior does not produce valid zero observations.

Use injected/fake/sanitized provider responses. No real provider network request is required or authorized by this task.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, **credential-free** verification for this bounded task. If the approved local runner is available, run only the relevant E1 market-data test suite after implementation, for example:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/market_data -p "test_*.py" -v
```

No external provider network call is part of this verification. If approved-local execution is unavailable, record `NOT_RUN` with the exact command. `NOT_RUN != PASS`.

## Writable scope

Only E1-owned paths needed for this task:

- `src/market_data/**`;
- `tests/market_data/**`;
- bounded sanitized E1 fixtures/docs;
- `coordination/E1/STATUS.md`.

Forbidden:

- private/account/provider-auth APIs;
- credentials/secrets;
- E2-E7 production/tests;
- contracts/ADR changes;
- strategy/risk/execution semantics;
- persistence/OperationalMode ownership;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- PAPER/SHADOW runtime start;
- order submission/provider mutation;
- LIVE/capital exposure;
- unrelated cleanup.

## Acceptance

### DONE

- current OKX public MarketSnapshot/finalized-candle surface satisfies the Gate C baseline;
- owned tests define freshness/finality/non-monotonic/failure semantics;
- no private/provider mutation/credential path added;
- local evidence is PASS or explicitly `NOT_RUN` without misclassification;
- commit/push to target branch and terminal E1 STATUS.

### BLOCKED

If canonical MarketSnapshot semantics are insufficient or provider behavior requires a cross-module contract decision, stop with exact evidence and do not broaden scope.

## Completion

Execute only this TASK, update `coordination/E1/STATUS.md`, commit/push required work to the target branch, and stop. Do not self-start the next Gate C task.