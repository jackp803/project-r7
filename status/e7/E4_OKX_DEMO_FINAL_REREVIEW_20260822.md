# E7 Final Targeted Re-Review — OKX Demo Submit Integrity

- Task: `E7-20260822-001`
- Date: `2026-08-22`
- Review branch: `agent/e7-e4-okx-demo-final-rereview-20260822`
- Review baseline: latest `main` `730ef2e87054f5dbe370b4e72e50d6e03af1fc5c`
- PR: `#12 execution: add Demo-first OKX provider adapter`
- Exact reviewed E4 implementation/tests/docs/handoff revision: `99bf09461e32117001ce7e587be44dcc3d152ab2`
- Observed PR head: `25294d72920efab3011eb5060079bf2edca5d056`
- PR-head delta after implementation pin: `coordination/E4/STATUS.md` only
- Executable verification: `NOT_RUN`
- Actual provider requests/orders: `NOT_SENT`
- Provider retry: `STRUCTURALLY DISABLED / NOT AUTHORIZED`

## Executive disposition

All five prior E4 static safety findings are now closed at the reviewed source revision.

```text
E4-OKX-MATERIALIZATION-INTEGRITY-001   CLOSED / PASS STATIC
E4-OKX-ACCOUNT-MATRIX-001              CLOSED / PASS STATIC
E4-OKX-RETRY-PROVENANCE-001            CLOSED / PASS STATIC
E4-OKX-ORDER-ABSENCE-001               CLOSED / PASS STATIC
E4-OKX-ORDER-STATE-CONSISTENCY-001     CLOSED / PASS STATIC
```

Therefore:

```text
PR #12 source disposition: PASS / STATIC ONLY
PR #12 merge recommendation: PM MAY MERGE
next bounded stage: MAY BE approved-local connectivity/read-only dry integration only
Demo order submission: NOT AUTHORIZED
provider retry: NOT AUTHORIZED / SOURCE DISABLED
PAPER/SHADOW/LIVE: NOT ADVANCED
```

This is source/static acceptance only. It is not executable PASS and it does not authorize a Demo order.

## 1. `E4-OKX-MATERIALIZATION-INTEGRITY-001`

**Disposition: `CLOSED / PASS STATIC`**

The final correction closes the previous end-to-end submit bypass.

### Adapter-issued provenance

`OKXDemoAdapter.prepare_entry()` first uses the accepted materialization path, which validates prerequisites and submit-fresh metadata, recomputes sizing from the exact canonical `OrderRequest` plus current validated metadata, treats caller sizing as evidence only, and enforces:

```text
0 < effective canonical BTC <= E5-approved canonical BTC quantity
```

After successful materialization, the adapter registers an internal frozen `_IssuedOKXPreparation` containing copied trusted facts plus the exact issued `OKXOrderMaterialization` object instance.

The issued preparation binds:

- `order_request_id`;
- `trade_plan_id`;
- internal `client_order_id`;
- provider `clOrdId`;
- provider instrument;
- provider side;
- provider position side;
- provider order type;
- provider trade mode;
- provider contract quantity;
- effective canonical BTC quantity;
- E5-approved canonical BTC quantity;
- instrument metadata reference;
- instrument metadata observation time;
- metadata freshness-policy version;
- preparation time;
- Demo environment;
- account level;
- position mode.

Caller-visible dataclass equality is not provenance. `_authorize_submit()` looks up the preparation by object identity and additionally requires `issue.materialization is materialization`. A direct caller construction, clone, or cross-adapter materialization therefore fails before the idempotency cache and before transport.

The adapter retains the issued materialization as a strong reference inside the preparation registry, so the identity binding is not merely a transient value comparison.

### Semantic tamper detection

Before submit, `_authorize_submit()` compares the current public materialization semantic facts with the copied immutable issued facts. Materially altered identities, provider facts, quantities, or metadata reference/observation therefore fail closed.

It separately verifies:

```text
environment == demo
account level/position mode still match adapter config
provider instrument == BTC-USDT-SWAP
provider order type == market
provider trade mode == isolated
clOrdId == deterministic mapping from internal client_order_id
0 < effective canonical quantity <= approved canonical quantity
provider contract quantity > 0
```

### Trusted signed body

The actual provider body is not taken from caller `materialization.body`.

At submit, E4 re-derives a trusted body from `_IssuedOKXPreparation`:

```text
instId  = trusted provider instrument
tdMode  = trusted isolated mode
clOrdId = trusted deterministic provider client ID
side    = trusted buy/sell
posSide = trusted net/long/short
ordType = trusted market
sz      = trusted provider contract quantity
```

The caller-visible body must normalize exactly equal to this trusted body or submit fails before transport. The request passed to OKX signing uses the re-derived trusted body.

Thus post-prepare mutation of `sz`, `instId`, `side`, `posSide`, `ordType`, or `clOrdId` is no longer execution authority.

### Idempotency order of operations

`submit_entry()` calls `_authorize_submit()` before reading `_submit_results`. Consequently a caller-constructed clone cannot borrow a cached result, and an altered object cannot reach transport merely because it reuses a prior `clOrdId`.

The adapter also records a preparation fingerprint by `clOrdId` and rejects a later adapter-issued preparation under the same provider identity when trusted preparation facts are materially different.

## 2. Submit-integrity deterministic test definitions

`tests/brokers/test_okx_submit_integrity.py` contains local-only deterministic definitions for:

- post-prepare `sz` mutation -> reject before transport;
- post-prepare `instId` mutation -> reject before transport;
- post-prepare `side` mutation -> reject before transport;
- post-prepare `posSide` mutation -> reject before transport;
- post-prepare `ordType` mutation -> reject before transport;
- post-prepare `clOrdId` mutation -> reject before transport;
- direct caller-constructed clone -> reject before transport;
- cross-adapter materialization -> reject before transport;
- material change under the same client identity -> reject;
- materially different re-preparation under the same `clOrdId` -> reject;
- valid exact adapter-issued Demo MARKET/isolated body -> one provider transport call;
- repeated submit of the same exact issued object -> idempotent, no second transport call;
- canonical/provider quantity separation and `effective <= E5-approved` upper-bound preservation.

No test was executed during this GitHub review. Definitions were inspected statically only.

## 3. No alternate E4 submit/retry bypass

Reviewed `OKXDemoAdapter` transport sends comprise:

- authenticated private GET reads through `_private_get()`;
- public instrument metadata GET;
- the single provider order POST path inside `submit_entry()` after `_authorize_submit()`.

No alternate E4 resubmit/order-post method was found.

`retry_entry()` remains structurally disabled and unconditionally raises `OKXReconciliationError`. Reconciliation evidence remains audit-only and cannot authorize a second provider submit.

## 4. Previously closed findings — regression review

### `E4-OKX-ACCOUNT-MATRIX-001`

**Remains `CLOSED / PASS STATIC`.**

V1 remains deliberately narrowed to:

```text
acctLv = 2  (Futures mode)
posMode = net_mode | long_short_mode
tdMode = isolated
instrument = BTC-USDT-SWAP
```

Both adapter configuration and runtime prerequisites reject unsupported/uncertain combinations.

Current official OKX V5 documentation was rechecked on 2026-08-22. It continues to identify `acctLv=2` as Futures mode; FUTURES/SWAP support both net and long/short position modes in Futures mode; `isolated` is not available for the reviewed order path in multi-currency margin or portfolio margin modes. This narrowed V1 matrix remains conservative and coherent.

### `E4-OKX-RETRY-PROVENANCE-001`

**Remains `CLOSED / PASS STATIC`.**

Provider retry remains structurally disabled. No caller-fabricated, mutated, replayed, or cross-materialization reconciliation evidence can trigger a provider resubmit.

### `E4-OKX-ORDER-ABSENCE-001`

**Remains `CLOSED / PASS STATIC`.**

There is no caller-configurable `order_not_found_codes` surface. Provider non-success and successful-empty lookup do not become authoritative absence proof, and retry is disabled regardless.

No fixture/provider error code is promoted to R7 order-absence authority.

### `E4-OKX-ORDER-STATE-CONSISTENCY-001`

**Remains `CLOSED / PASS STATIC`.**

Known order-state/fill consistency remains fail-closed:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled          -> 0 <= accFillSz <= sz
mmp_canceled      -> 0 <= accFillSz <= sz
```

Overfill is a hard failure. Contradictory known states become `RECONCILIATION_REQUIRED`; positive fill requires average fill price; unknown state is never optimistic success.

## 5. Demo/auth/provider-boundary regression review

### Environment and authentication

**PASS / STATIC ONLY.**

Preserved:

- Demo-only configuration;
- global REST base fixed to `https://openapi.okx.com`;
- mandatory `x-simulated-trading: 1` for private request construction;
- OKX REST HMAC-SHA256/Base64 signature prehash semantics;
- runtime-injected credentials;
- redacted credential/request representations;
- no production/live fallback.

Current official OKX V5 documentation continues to document the same Demo REST domain and mandatory simulated-trading header.

### `clOrdId`

**PASS / STATIC ONLY.**

Provider identity remains:

```text
R7 + first 30 hex characters of SHA-256(internal client_order_id)
```

It is deterministic, alphanumeric and <=32 characters. Submit independently rechecks the mapping before signing.

Current official OKX V5 documentation continues to require up to 32 case-sensitive alphanumeric characters and pending-order uniqueness; historical uniqueness is not assumed.

### MARKET / isolated / quantity separation

**PASS / STATIC ONLY.**

The bounded path remains:

```text
BTC_USDT_PERP -> BTC-USDT-SWAP
MARKET -> market
tdMode = isolated
canonical BTC quantity != provider contract sz
```

Provider `sz` is derived from current validated sizing metadata and is carried separately from canonical BTC exposure. No limit/stop/trigger/TIF execution field is introduced.

### Freshness hardening

**PASS / STATIC ONLY / E4-local policy.**

Preserved policy:

```text
metadata policy = okx-instrument-metadata-freshness-v0.2
general cache/sizing ceiling = 300 seconds
submit-preparation observation age <= 5 seconds
scheduled sizing-change guard = 60 seconds
```

The freshness policy/version, observation timestamp and preparation time are copied into adapter-owned preparation context. Current instrument metadata validation and scheduled-change fail-closed behavior are unchanged.

The 5-second/60-second values remain internal safety policy, not OKX provider guarantees or shared-contract semantics.

### Asset movement / account mutation

**PASS / STATIC ONLY.**

No withdrawal, deposit, funding transfer, internal/sub-account transfer, balance adjustment, account-mode mutation, position-mode mutation, or leverage mutation capability is added.

### Broker / PaperBroker

**PASS / STATIC COMPATIBILITY.**

PR #12 does not modify the broker-neutral Broker, PaperBroker, canonical execution gateway, or shared execution model source. Existing Broker/PaperBroker behavior is unchanged at source level. Executable regression remains `NOT_RUN`.

## 6. Repository / PR scope

Current PR #12 changed-file scope is limited to E4 status/docs/provider adapter/sizing and broker test definitions:

```text
coordination/E4/STATUS.md
docs/execution/E4_TO_E7_HANDOFF.md
docs/execution/OKX_DEMO_ADAPTER.md
docs/execution/OKX_SIZING_POLICY.md
src/brokers/okx_demo.py
src/brokers/okx_sizing.py
tests/brokers/test_okx_demo_adapter.py
tests/brokers/test_okx_demo_status_mapping.py
tests/brokers/test_okx_sizing.py
tests/brokers/test_okx_submit_integrity.py
```

No:

- `contracts/**` change;
- E1/E2/E3/E5/E6 production rewrite;
- `.github/workflows` or CI addition;
- real credential/secret material;
- concrete production/live transport fallback;
- account/asset-movement feature expansion;
- unrelated product feature expansion.

Exact implementation pin `99bf09461e32117001ce7e587be44dcc3d152ab2` to observed PR head `25294d72920efab3011eb5060079bf2edca5d056` changes only `coordination/E4/STATUS.md`; reviewed source/tests/docs therefore remain pinned.

At final re-review time:

```text
latest main = 730ef2e87054f5dbe370b4e72e50d6e03af1fc5c
PR branch vs latest main = ahead 24 / behind 2
GitHub mergeable = true
```

The two latest-main-only commits relative to the PR merge base modify only:

```text
coordination/E4/TASK.md
coordination/E7/TASK.md
```

There is no production/shared-contract drift in that synchronization delta. Repository synchronization is therefore not a static merge blocker.

## 7. Merge / next-stage recommendation

All five E4 findings are statically closed and PR scope is coherent.

**PM MAY MERGE PR #12.**

This recommendation means only that the reviewed source is statically acceptable for merge. It does not claim executable validation.

After merge, PM/Product Owner may separately authorize the next bounded stage as:

```text
approved-local OKX Demo connectivity/read-only dry integration only
```

That next stage may validate connectivity, authentication/read paths, account configuration reads, instrument metadata reads and other expressly read-only prerequisites in an approved local environment.

It must **not** be interpreted as authorization for:

- Demo order submission;
- provider retry;
- production/live trading;
- real-money execution;
- account/position/leverage mutation;
- withdrawal/funding/asset movement;
- PAPER/SHADOW/LIVE gate advancement.

Any future Demo order test requires a separate explicit Product Owner/PM authorization and must not be inferred from this static PASS.

## 8. Release / execution state

```text
Executable verification: NOT_RUN
Provider requests/orders: NOT_SENT
Provider retry: NOT_AUTHORIZED / STRUCTURALLY DISABLED
Demo order submission: NOT_AUTHORIZED
Real-money execution: BLOCKED / NOT AUTHORIZED
GitHub project compute: NOT_USED
Gate A: BLOCKED / UNCHANGED
Gate B: BLOCKED / UNCHANGED
Gate C: BLOCKED / UNCHANGED
Gate D: BLOCKED / UNCHANGED
```

E7 stops after this final targeted re-review and waits for PM. E7 does not merge PR #12, does not start local connectivity, and does not start provider execution automatically.
