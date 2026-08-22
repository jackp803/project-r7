# E4 Status

- task_id: `E4-20260821-012`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-okx-demo-adapter-20260821`
- head_sha: `99bf09461e32117001ce7e587be44dcc3d152ab2` (source/tests/docs/handoff HEAD immediately before this status-only completion commit)
- summary: `Closed only the remaining E7 blocker E4-OKX-MATERIALIZATION-INTEGRITY-001 at the actual provider submit boundary. submit_entry now requires the exact adapter-issued preparation instance, verifies all public materialization semantics against immutable adapter-owned preparation facts, re-derives the signed provider body from trusted facts, and rejects direct construction, cross-adapter substitution, semantic mutation, or post-prepare body tampering before idempotency-cache access or transport. The four previously closed findings remain unchanged.`
- files_changed: `src/brokers/okx_demo.py; tests/brokers/test_okx_submit_integrity.py; docs/execution/OKX_DEMO_ADAPTER.md; docs/execution/E4_TO_E7_HANDOFF.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No Product Owner-approved local project execution environment was used. Required commands: python -m unittest discover -s tests/execution -p "test_*.py" -v ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Provider retry remains structurally disabled as previously accepted; no provider connectivity or execution was authorized.`
- handoff_path: `docs/execution/E4_TO_E7_HANDOFF.md`
- next_owner: `E7/PM for PR #12 targeted static re-review`

## Branch synchronization

Before this correction the existing PR #12 branch had diverged from latest `main`. E4 synchronized non-destructively using two-parent merge commit:

```text
64508c6f15be959cf8eabefed580a48cd3c964c0
```

Parents preserve:

- prior PR #12 branch HEAD `c151fa7c37adafbf9f93157d80cf4b763dd775e2`;
- then-current `main` `7c6522e5c52722f734c11c1772c0b2e86b81b51c`.

No force update, destructive rebase, or history rewrite was used.

## Remaining finding disposition

### `E4-OKX-MATERIALIZATION-INTEGRITY-001` — `CORRECTED / STATIC SOURCE`

Preparation-side sizing integrity from the previous revision is preserved. The final submit boundary now independently enforces adapter-issued authority.

`prepare_entry()` registers a frozen internal `_IssuedOKXPreparation` containing the exact trusted preparation facts:

- `order_request_id`;
- `trade_plan_id`;
- internal `client_order_id`;
- provider `clOrdId`;
- provider instrument;
- provider side;
- provider position side;
- `ordType=market`;
- `tdMode=isolated`;
- provider contract quantity;
- effective canonical BTC quantity;
- E5-approved canonical BTC quantity;
- instrument metadata reference and observation timestamp;
- metadata freshness policy version;
- preparation timestamp;
- Demo environment;
- account level and position mode.

The adapter retains the exact issued `OKXOrderMaterialization` object instance. Visible equality is insufficient: a caller-constructed clone is not an issued object and is rejected.

`submit_entry()` now performs `_authorize_submit()` before consulting `_submit_results` and before any transport operation.

Submit requires:

1. exact adapter-issued object identity;
2. exact semantic equality with frozen issued facts;
3. unchanged Demo/account/position-mode context;
4. deterministic `clOrdId` binding to internal client identity;
5. `0 < effective canonical BTC <= E5-approved canonical quantity`;
6. positive provider contract quantity;
7. exact equality between caller-visible `body` and a fresh body derived from trusted issued facts.

The body actually sent into REST signing is freshly derived from `_IssuedOKXPreparation`; `materialization.body` is comparison/audit data only and is never execution authority.

A provider `clOrdId` that has already been prepared cannot be reissued with materially different trusted preparation facts.

## Targeted deterministic test definitions

Added `tests/brokers/test_okx_submit_integrity.py` covering:

- mutate `body["sz"]` after `prepare_entry()` -> reject before transport;
- mutate `instId` -> reject before transport;
- mutate `side` -> reject before transport;
- mutate `posSide` -> reject before transport;
- mutate `ordType` -> reject before transport;
- mutate `clOrdId` -> reject before transport;
- direct caller-constructed clone -> reject before transport;
- materialization issued by another adapter -> reject before transport;
- materially changed facts under the same logical/client identity -> reject;
- materially different re-preparation under one provider `clOrdId` -> reject;
- valid adapter-issued preparation -> exact expected Demo MARKET isolated signed body;
- repeated submit of the same issued object -> idempotent result, no second transport call;
- provider effective canonical quantity remains `<=` E5-approved BTC bound.

These are definitions only. No test was executed in this environment.

## Four previously closed findings

Preserved without redesign:

- `E4-OKX-ACCOUNT-MATRIX-001` — `CLOSED / unchanged`
- `E4-OKX-RETRY-PROVENANCE-001` — `CLOSED / retry remains structurally disabled`
- `E4-OKX-ORDER-ABSENCE-001` — `CLOSED / no caller-configurable absence authority`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001` — `CLOSED / state-fill consistency checks unchanged`

## Accepted boundaries preserved

- Demo-only mode;
- mandatory `x-simulated-trading: 1` on authenticated requests;
- runtime-only/redacted credentials;
- bounded private endpoint allowlist;
- `acctLv=2` Futures mode with `net_mode | long_short_mode`;
- `tdMode=isolated`;
- MARKET-only entry;
- canonical BTC quantity remains distinct from OKX provider `sz`;
- freshness policy `okx-instrument-metadata-freshness-v0.2` unchanged;
- provider retry structurally disabled;
- no production/live fallback;
- no automatic account/position/leverage mutation;
- no withdrawal/deposit/funding/internal/sub-account transfer/balance-adjustment API;
- Broker/PaperBroker source behavior unchanged;
- shared contracts unchanged.

## Verification / execution state

```text
executable verification = NOT_RUN
provider requests/orders = NOT_SENT
GitHub Actions / CI      = NOT_USED
hosted runner/compute    = NOT_USED
PAPER/SHADOW/LIVE        = NOT_ADVANCED
```

Required Product Owner-approved local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No executable PASS is claimed.

## Completion boundary

The single TASK-authorized blocker correction is complete in static/source form. E4 stops here and does not merge PR #12, send a Demo request/order, add concrete networking, enable provider retry, or start another feature automatically.
