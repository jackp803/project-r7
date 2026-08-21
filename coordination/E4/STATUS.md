# E4 Status

- task_id: `E4-20260821-006`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-execution-v2`
- head_sha: `c71bf9c66a7f37cedb8bbbcf3000591970a081eb` (implementation + docs + handoff HEAD immediately before this status-only completion commit)
- summary: `Completed the bounded provider-neutral entry-v0.1 MARKET translator and deterministic local OKX BTC-USDT-SWAP instrument metadata/sizing layer. ApprovedTradePlan.quantity remains canonical BTC and provider contract sz remains a separate audit fact. Quantization only rounds down or rejects. Existing E4 idempotency/partial-fill/overfill/ambiguous-ack/reconciliation behavior was preserved. No OKX networking/private/Demo/account/auth/order submission was added.`
- files_changed: `src/execution/gateway.py; src/execution/models.py; src/brokers/okx_sizing.py; tests/execution/test_gateway.py; tests/brokers/test_paper_broker.py; tests/brokers/test_okx_sizing.py; docs/execution/OKX_SIZING_POLICY.md; docs/execution/E4_TO_E7_HANDOFF.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No Product Owner-approved local project execution environment was used. Required commands: python -m unittest discover -s tests/execution -p "test_*.py" -v ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Documentation gap: TASK references status/e7/E2_E5_PROFILE_CHAIN_STATIC_REVIEW_20260821.md, but that file was not present/searchable after synchronization. No substitute review was invented; implementation used the TASK's explicit accepted E2/E5 pins plus contracts/EXECUTION_OBJECT_PROFILES_V0_1.md and ADR-0002/0003.`
- handoff_path: `docs/execution/E4_TO_E7_HANDOFF.md`
- next_owner: `E7/PM`

## Branch synchronization

- prior E4 skeleton/history preserved;
- synchronized with then-current `main` `2bbe3726f7897f3ad2df0b67a58f9ba9829c17d4` using two-parent merge commit `2e0a60e3ba3e9fbe5f298fded2408988beb81fe0`;
- no force update, destructive rebase, or old-branch rewrite was used.

## Canonical entry translation

Accepted executable profile only:

```text
schema_version           = contracts-v0.1
symbol                   = BTC_USDT_PERP
entry profile            = entry-v0.1
entry order type         = MARKET
quantity profile         = base-asset-v0.1
quantity unit            = BASE_ASSET
quantity asset           = BTC
```

Mechanical mapping:

```text
LONG  -> BUY
SHORT -> SELL
MARKET -> MARKET
ApprovedTradePlan.quantity -> OrderRequest.quantity unchanged
```

`reference_price` remains advisory only. It never becomes `limit_price`, `stop_price`, `trigger_price`, or TIF. Missing/unknown profile, unsupported order type, invalid quantity profile/unit/asset, malformed quantity, expired/incompatible plan, or forbidden executable entry fields fail closed.

## OKX metadata / sizing policy

Configured mapping:

```text
BTC_USDT_PERP -> OKX BTC-USDT-SWAP
```

Freshness policy:

```text
version = okx-instrument-metadata-freshness-v0.1
max_age = 300 seconds
```

Required local metadata facts include provider/instrument identity, `instType`, `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, `state`, observation time/reference, and freshness-policy version.

Supported direct conversion only:

```text
provider = OKX
instType = SWAP
ctType   = linear
ctValCcy = BTC
state    = live
```

Formula:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_base    = provider_sz * base_per_contract
```

Required invariant:

```text
provider_sz >= minSz
provider_sz is a valid lotSz multiple
0 < effective_base <= E5-approved BTC quantity
```

Provider quantization never rounds up. Missing/stale/malformed/non-live/mismatched/unsupported metadata blocks sizing/new exposure.

## Canonical vs provider-native audit separation

`OKXEntrySizingAudit` keeps separate:

- canonical E5-approved BTC quantity/profile;
- provider requested contract quantity (`sz` semantics);
- effective canonical BTC quantity after round-down;
- provider/instrument identity;
- metadata reference/observation/freshness policy;
- base-per-contract used for conversion.

OKX contract count is not written into shared canonical `OrderRequest.quantity`.

## Official provider recheck

Current official OKX V5 API documentation was rechecked on 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- `GET /api/v5/public/instruments`
- `POST /api/v5/trade/order`

Reconfirmed for this scope: derivative order `sz` is contract count; derivative `lotSz/minSz` are contract units; MARKET is supported for SWAP; normal tradable state is `live`, while `post_only` is incompatible with MARKET.

Provider-specific `clOrdId` constraints were noted but provider request/client-ID mapping is explicitly not implemented in this task.

## Deterministic test definitions added/updated

- valid profiled MARKET plan -> mechanical OrderRequest;
- LONG/SHORT side mapping;
- advisory reference price never becomes executable price;
- missing/unknown profile rejection;
- unsupported order type / forbidden price-TIF rejection;
- malformed quantity / expired plan rejection;
- stable idempotency identity;
- existing partial fill / overfill behavior;
- ambiguous acknowledgement -> reconciliation required;
- query/reconcile-before-retry behavior retained;
- exact representable OKX quantity;
- round-down quantity;
- below-minimum/nonrepresentable rejection;
- lot/min size validation;
- stale/missing/malformed/non-tradable/mismatched metadata rejection;
- unsupported conversion rejection;
- provider sizing never exceeds canonical approved BTC;
- canonical quantity and provider contract quantity remain distinct.

## Verification / execution policy

- executable verification: `NOT_RUN`
- GitHub Actions / CI / hosted runner: `NOT_USED`
- no project test, broker simulation, API experiment, integration test, or recovery test was executed on GitHub
- no Gate B / PAPER_READY / Demo / SHADOW / LIVE PASS is claimed

## Provider / live / security status

- OKX public networking: `NOT_IMPLEMENTED`
- OKX private/Demo API: `NOT_IMPLEMENTED`
- authentication/signatures: `NOT_IMPLEMENTED`
- account/balance/leverage calls: `NOT_IMPLEMENTED`
- real/Demo order submission: `NOT_IMPLEMENTED`
- withdrawal/funding transfer/sub-account capital movement: `NOT_IMPLEMENTED / NOT EXPOSED`
- PAPER/SHADOW/LIVE enablement: `NOT AUTHORIZED / NOT IMPLEMENTED`
- credentials/secrets: `NONE ADDED`
- shared contracts: `UNCHANGED`

## Completion boundary

This task is complete within its bounded static/source scope. E4 stops here and does not start OKX Demo/private execution or another feature automatically.
