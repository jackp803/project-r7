# E4 Status

- task_id: `E4-20260821-010`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-okx-demo-adapter-20260821`
- head_sha: `651541ba0da646f0c2ab69117219e2c8ca21247c` (source/tests/docs/handoff HEAD immediately before this status-only completion commit)
- summary: `Corrected only the five E7 blocking findings for PR #12: materialization now recomputes provider sizing from the exact OrderRequest + submit-validated metadata; V1 account support is narrowed to acctLv=2 Futures mode with net/long-short position modes; caller-controlled order-absence codes are removed; provider retry is structurally disabled; and known OKX order states are checked against accFillSz/sz consistency before canonical mapping. Previously accepted Demo/auth/freshness/canonical-vs-provider safety boundaries are preserved.`
- files_changed: `src/brokers/okx_demo.py; src/brokers/okx_sizing.py; tests/brokers/test_okx_demo_adapter.py; tests/brokers/test_okx_demo_status_mapping.py; docs/execution/OKX_DEMO_ADAPTER.md; docs/execution/OKX_SIZING_POLICY.md; docs/execution/E4_TO_E7_HANDOFF.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No Product Owner-approved local project execution environment was used. Required commands: python -m unittest discover -s tests/execution -p "test_*.py" -v ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Provider retry remains intentionally disabled until a separately E7-accepted, current provider-authoritative order-absence policy exists; this is the required fail-closed V1 disposition, not a source-completion blocker.`
- handoff_path: `docs/execution/E4_TO_E7_HANDOFF.md`
- next_owner: `E7/PM for PR #12 static re-review`

## Branch synchronization

Before corrections the branch and main had diverged. E4 synchronized non-destructively with two-parent merge commit:

```text
0ff16394709710fd7ce26c9528f3c63ad8fb1518
```

Parents preserve:

- PR #12 prior branch HEAD `94ca2f861d9e7a51277c5c63ff20f730c7f19f92`;
- then-current `main` `ab9a75b0d24eb82cff35d028e349878fddd4b86b`.

No force update, destructive rebase, or branch-history rewrite was used.

## Finding disposition

### `E4-OKX-MATERIALIZATION-INTEGRITY-001` — `CORRECTED / STATIC`

`materialize_demo_market_order()` now:

1. submit-validates the exact metadata snapshot;
2. recomputes sizing from the exact current `OrderRequest` + metadata using `size_okx_market_entry()`;
3. treats caller `OKXEntrySizingAudit` as evidence only;
4. requires supplied audit == recomputed audit;
5. serializes provider `body.sz` only from the recomputed result.

The sizing audit now binds conversion facts including `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, optional `maxMktSz`, metadata ref/observation, provider contract quantity, and effective canonical quantity. Current `maxMktSz`, when present, is enforced.

Invariant preserved:

```text
0 < effective canonical BTC <= E5-approved OrderRequest.quantity
```

Deterministic test definitions cover forged/oversized sizing audit, falsified effective quantity, altered request quantity, altered metadata/conversion facts, and metadata/audit mismatch. Existing lot/min-size tests remain in `tests/brokers/test_okx_sizing.py`.

### `E4-OKX-ACCOUNT-MATRIX-001` — `CORRECTED / STATIC`

Current official OKX V5 account/order guidance was rechecked. V1 accepts only:

```text
acctLv = 2  (Futures mode)
posMode = net_mode | long_short_mode
tdMode = isolated
```

Rejected before materialization:

```text
acctLv = 1  Spot mode
acctLv = 3  Multi-currency margin
acctLv = 4  Portfolio margin
unsupported position modes
```

Official basis: Futures-mode FUTURES/SWAP supports net and long/short position modes; current place-order guidance states `isolated` is unavailable in Multi-currency margin and Portfolio margin modes.

No account/position-mode/leverage mutation was added.

### `E4-OKX-RETRY-PROVENANCE-001` — `CORRECTED / STATIC`

V1 provider retry is structurally disabled.

`OKXReconciliationEvidence` is audit data only. `retry_entry()` always raises `OKXReconciliationError` and never clears the prior ambiguous submit result or calls transport. Forged, mutated, replayed, or cross-materialization evidence cannot authorize a second provider submit.

### `E4-OKX-ORDER-ABSENCE-001` — `CORRECTED / STATIC`

Caller-controlled `order_not_found_codes` was removed from adapter configuration.

Non-success order lookup becomes:

```text
PROVIDER_ERROR_NOT_ABSENCE_PROOF
```

Success with empty data becomes:

```text
SUCCESS_EMPTY_NOT_ABSENCE_PROOF
```

Neither authorizes retry. No fixture/example error code, including `51603`, is accepted as repository order-absence authority.

### `E4-OKX-ORDER-STATE-CONSISTENCY-001` — `CORRECTED / STATIC`

Consistency table enforced before canonical status mapping:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled          -> 0 <= accFillSz <= sz
mmp_canceled      -> 0 <= accFillSz <= sz
```

- overfill -> hard reconciliation failure;
- contradictory known state/fill -> `RECONCILIATION_REQUIRED`;
- unknown state -> `RECONCILIATION_REQUIRED`;
- positive fill requires valid average fill price in the current response model;
- canceled states preserve actual partial-fill canonical quantity.

Tests cover filled-underfill, partial-zero/full, live-nonzero, overfill, canceled partial fill, and unknown state.

## Previously accepted boundaries preserved

- Demo-only environment and mandatory `x-simulated-trading: 1`;
- runtime-only/redacted credentials;
- deterministic private REST signing;
- private endpoint allowlist;
- MARKET-only `BTC_USDT_PERP -> BTC-USDT-SWAP` materialization;
- `tdMode=isolated`;
- no limit/stop/trigger/TIF invention;
- canonical BTC quantity remains distinct from provider contract `sz`;
- stable legal provider `clOrdId`;
- no production/live fallback;
- no concrete network transport;
- no account/position/leverage mutation;
- no withdrawal/deposit/funding/internal/sub-account transfer/balance-adjustment API surface;
- freshness policy `okx-instrument-metadata-freshness-v0.2` remains fail closed;
- Broker/PaperBroker production behavior was not modified.

## Official OKX V5 recheck

Rechecked 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- account mode / account config;
- set position mode;
- `GET /api/v5/public/instruments`;
- `POST /api/v5/trade/order`;
- `GET /api/v5/trade/order`;
- `GET /api/v5/trade/orders-pending`;
- `GET /api/v5/account/positions`;
- `GET /api/v5/trade/fills`.

Current order-state semantics used by consistency validation: `live` has no fills, `partially_filled` is partially executed/active, `filled` is fully executed terminal, and canceled terminal states may retain partial fill facts.

## Verification / execution policy

- executable verification: `NOT_RUN`
- project/fake-transport tests: `NOT_RUN`
- provider requests/orders: `NOT_SENT`
- GitHub Actions / CI / hosted runner: `NOT_USED`
- Gate A/B/C/D: `UNCHANGED / BLOCKED`

Required approved-local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

## Security / live status

- real credentials/secrets: `NONE ADDED / NOT USED`
- concrete provider connectivity: `NOT IMPLEMENTED`
- actual Demo submit/retry: `NOT SENT / RETRY DISABLED`
- production/real-money mode: `REJECTED / NOT IMPLEMENTED`
- asset movement: `NOT EXPOSED`
- PAPER/SHADOW/LIVE: `NOT ADVANCED`
- shared contracts: `UNCHANGED`

## Completion boundary

The five E7 source blockers are corrected in source/test definitions. E4 stops here. PR #12 remains pending PM/E7 static re-review; E4 does not merge it, send Demo orders, enable provider retry, or start another feature automatically.
