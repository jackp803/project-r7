# E1 Current Task

- task_id: `E1-20260821-002`
- issued_at: `2026-08-21T10:07:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e1-market-data-okx`
- authority: `agents/E1_MARKET_DATA.md`, `agents/README.md`, `contracts-v0.1`, Product Owner decision `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`

## Objective

Migrate the V1 public market-data target from Pionex to OKX while preserving the canonical `contracts-v0.1` Candle contract and the already-reviewed closed-candle/no-manufactured-data semantics.

This is a provider-adapter migration only. Do not modify Strategy, Backtest, Risk, Registry, or Execution behavior.

## Product target

```text
Canonical instrument: BTC_USDT_PERP
OKX instrument:       BTC-USDT-SWAP
Canonical timeframes: 1m / 15m / 1h / 4h
Provider target:      OKX public market-data APIs
```

No new Pionex-specific development is authorized.

## Required actions

1. Work only on fresh branch `agent/e1-market-data-okx`, created by PM from the latest `main`. Do not rewrite or delete the historical reviewed Pionex branch/code merely to claim migration.
2. Implement an OKX public historical-candle adapter using official OKX public endpoints appropriate for historical SWAP candles.
3. Map only at the adapter boundary:
   - canonical `BTC_USDT_PERP` -> OKX `BTC-USDT-SWAP`;
   - canonical `1m / 15m / 1h / 4h` -> exact OKX provider bar labels required by the official API.
4. Preserve the existing canonical Candle fields/invariants from `contracts-v0.1`:
   - UTC timestamps;
   - half-open `[open_time, close_time)` semantics;
   - Decimal financial values internally / decimal-string interchange where serialized;
   - deterministic duplicate handling;
   - malformed/missing/out-of-order data surfaced, not manufactured;
   - only finalized/closed provider bars become canonical closed candles.
5. Normalize OKX candle finality using the provider's official finality/confirmation field. Do not infer a bar is final merely from local wall-clock time if provider finality says otherwise.
6. Preserve deterministic exact historical-range validation and pagination. Surface provider/network/API limit errors explicitly.
7. Add/update local-only test definitions covering at minimum:
   - symbol mapping;
   - timeframe mapping;
   - provider finality -> canonical `is_closed`;
   - ascending canonical output even if provider returns descending pages;
   - duplicate rejection/deterministic handling;
   - gap/missing-bar detection for an exact requested historical sequence;
   - malformed OHLCV rejection;
   - canonical schema_version remains `contracts-v0.1`;
   - no provisional/unconfirmed candle is accepted as final.
8. Add/update E1 documentation/handoff explaining the OKX mapping and any provider-specific pagination/finality constraints.
9. Update `coordination/E1/STATUS.md` with exact branch HEAD, changed files, source endpoint(s), mapping table, known limits, and verification state.
10. Do not run project code/tests unless a Product Owner-approved local environment exists. Otherwise record `NOT_RUN` plus exact commands.

## Acceptance

Static/source acceptance requires:

- OKX public historical adapter exists and is observable in Git;
- canonical Candle contract is unchanged;
- no shared-contract modification unless a real mismatch is reported and work stops;
- no private OKX API, account data, credentials, Demo/private orders, or execution code;
- no new Pionex-specific work;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` if no approved local environment exists.

## Writable scope

E1-owned paths only:

- `src/market_data/**`
- `tests/market_data/**`
- E1-owned docs/status/handoff paths
- `coordination/E1/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E2/E3/E4/E5/E6 production rewrites;
- private OKX/Pionex API logic;
- credentials/secrets;
- GitHub compute/CI;
- SHADOW/LIVE behavior.

## Local verification

If an approved local environment exists, use exact commands documented in the E1 handoff. Otherwise:

```text
NOT_RUN
```

A future public-network smoke test must use only OKX public market endpoints and must never require credentials.

## Completion / status

Persist the bounded OKX public-data migration and handoff, update STATUS, then stop. Do not start WebSocket/private/account/execution work automatically.
