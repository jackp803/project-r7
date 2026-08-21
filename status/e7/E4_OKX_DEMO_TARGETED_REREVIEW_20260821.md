# E7 Targeted Re-Review — Corrected OKX Demo Adapter

- Task: `E7-20260821-012`
- Date: 2026-08-21
- Review branch: `agent/e7-e4-okx-demo-rereview-20260821`
- PR: `#12 execution: add Demo-first OKX provider adapter`
- Corrected implementation/tests/docs/handoff revision: `651541ba0da646f0c2ab69117219e2c8ca21247c`
- Observed PR head: `c151fa7c37adafbf9f93157d80cf4b763dd775e2`
- Executable verification: `NOT_RUN`
- Actual provider requests/orders: `NOT_SENT`

## Executive disposition

Four of the five prior E4 blocking findings are statically closed at the corrected revision. `E4-OKX-MATERIALIZATION-INTEGRITY-001` remains **BLOCKING** end-to-end.

```text
E4-OKX-MATERIALIZATION-INTEGRITY-001   BLOCKING / NOT CLOSED
E4-OKX-ACCOUNT-MATRIX-001              CLOSED / PASS STATIC
E4-OKX-RETRY-PROVENANCE-001            CLOSED / PASS STATIC
E4-OKX-ORDER-ABSENCE-001               CLOSED / PASS STATIC
E4-OKX-ORDER-STATE-CONSISTENCY-001     CLOSED / PASS STATIC
```

Therefore:

```text
PR #12 source disposition:  FAIL / BLOCKED
PR #12 merge recommendation: DO NOT MERGE
approved-local connectivity/read-only dry stage: NOT YET
Demo order submission: NOT AUTHORIZED
provider retry: NOT AUTHORIZED / STRUCTURALLY DISABLED
```

GitHub currently also reports PR #12 `mergeable=false`. The PR branch is behind current `main` by two coordination-only TASK commits, so repository synchronization must be rechecked after the remaining E4 source correction. That repository condition is secondary to the blocking materialization finding.

## 1. `E4-OKX-MATERIALIZATION-INTEGRITY-001`

**Disposition: `BLOCKING / NOT CLOSED`**  
**Owner: E4**

### What was fixed correctly

The corrected `materialize_demo_market_order()` no longer trusts the caller-provided `OKXEntrySizingAudit` as execution authority. It:

1. validates submit-time metadata;
2. recomputes sizing from the exact current `OrderRequest` plus validated metadata via `size_okx_market_entry()`;
3. compares the supplied sizing object against the recomputed sizing evidence;
4. requires `0 < effective_canonical_requested_quantity <= request.quantity`.

The corrected sizing layer also carries the provider conversion facts and enforces `maxMktSz` when supplied. Deterministic tests cover oversized forged sizing evidence, changed request quantity, altered metadata, and metadata-reference mismatch.

### Remaining end-to-end bypass

The execution boundary is still not structurally bound after materialization.

`OKXOrderMaterialization` is a normal caller-constructible frozen dataclass, but its `body` member is a mutable mapping created as a normal `dict`. `frozen=True` prevents assigning a new dataclass field; it does **not** prevent mutation of the contained mapping.

A caller can therefore:

```text
materialization = adapter.prepare_entry(...)
materialization.body["sz"] = "oversized-provider-contract-count"
adapter.submit_entry(materialization, ...)
```

`submit_entry()` signs and sends `materialization.body` directly. It does not revalidate that:

```text
body.sz == materialization.provider_contract_quantity
provider_contract_quantity == recomputed current sizing
body instId/side/posSide/ordType/clOrdId remain equal to the accepted materialization facts
```

More generally, a caller can directly construct an `OKXOrderMaterialization` and pass it to `submit_entry()` without ever going through `prepare_entry()` / `materialize_demo_market_order()`.

Thus the corrected recomputation is valid inside the materialization function, but it is not yet an end-to-end execution-authority guarantee. A first provider submit can still be fed caller-tampered provider-native request material.

### Required correction

E4 must make the submit boundary independently enforce the approved materialization, for example by one of these bounded designs:

- `submit_entry()` accepts the canonical `OrderRequest` + current validated metadata/prerequisites and performs/reuses the recomputation internally; or
- adapter `prepare_entry()` stores an adapter-owned immutable materialization fingerprint/token and `submit_entry()` requires an exact match; or
- materialization body is derived afresh at submit from immutable validated fields and is not caller-mutable execution authority.

At minimum, deterministic tests must prove:

- mutating `body["sz"]` after `prepare_entry()` cannot cause a provider submit;
- mutating provider side/instrument/order type/`clOrdId` cannot cause a provider submit;
- a directly caller-constructed materialization cannot bypass sizing/account/freshness checks;
- the submitted provider contract quantity remains bound to the current E5-approved canonical BTC quantity.

## 2. `E4-OKX-ACCOUNT-MATRIX-001`

**Disposition: `CLOSED / PASS STATIC`**

The corrected adapter narrows V1 configuration to:

```text
acctLv = 2  (Futures mode)
posMode = net_mode | long_short_mode
tdMode = isolated
instrument = BTC-USDT-SWAP
```

`OKXDemoAdapterConfig` rejects account levels `1`, `3`, and `4`, and rejects position modes outside the explicit V1 matrix. Runtime prerequisites must also match the configured accepted matrix.

Current official OKX V5 documentation was rechecked on 2026-08-21. It identifies `acctLv=2` as Futures mode; FUTURES/SWAP support both net and long/short position modes in Futures mode; official leverage/trading examples explicitly describe SWAP isolated-margin operation for both buy/sell and long/short position modes. The V1 subset is therefore technically coherent and conservative for this bounded path.

No account/position/leverage mutation is introduced.

## 3. `E4-OKX-RETRY-PROVENANCE-001`

**Disposition: `CLOSED / PASS STATIC`**

Provider retry is now structurally disabled in source. `retry_entry()` unconditionally raises `OKXReconciliationError` and never calls the provider submit path.

Reconciliation evidence is explicitly audit-only. Corrected deterministic tests cover forged/mutated/replayed/cross-materialization evidence and assert transport request count does not increase.

Repeated ordinary `submit_entry()` after an ambiguous result still returns the stored result rather than issuing another request.

No hidden E4 retry/resubmit method was found in the reviewed adapter source.

## 4. `E4-OKX-ORDER-ABSENCE-001`

**Disposition: `CLOSED / PASS STATIC`**

Caller-configurable `order_not_found_codes` has been removed from `OKXDemoAdapterConfig`.

Order lookup behavior is now fail-closed:

```text
provider non-success -> PROVIDER_ERROR_NOT_ABSENCE_PROOF
successful empty data -> SUCCESS_EMPTY_NOT_ABSENCE_PROOF
```

Neither condition authorizes retry. Reconciliation always returns `retry_allowed=False`, and retry itself is structurally disabled.

The prior fixture/example code `51603` is retained only as a test input showing that an arbitrary provider error is **not** absence proof. It is not canonicalized as provider authority.

No current official OKX source was accepted here as a stable R7 order-absence authority; this is safe because retry remains disabled.

## 5. `E4-OKX-ORDER-STATE-CONSISTENCY-001`

**Disposition: `CLOSED / PASS STATIC`**

The corrected source implements the required state/fill consistency table:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled          -> 0 <= accFillSz <= sz
mmp_canceled      -> 0 <= accFillSz <= sz
```

Overfill is a hard failure. Contradictory known-state combinations become `RECONCILIATION_REQUIRED`. Positive accumulated fill requires a valid average fill price. Unknown states become `RECONCILIATION_REQUIRED`, never optimistic success. Canceled states preserve actual partial-fill quantity.

The corrected deterministic test definitions explicitly cover consistent and contradictory combinations, overfill, missing average price, and unknown states.

## Regression boundary review

### Demo environment / authentication

**PASS / STATIC ONLY**

Preserved:

- Demo-only environment configuration;
- REST base fixed to `https://openapi.okx.com`;
- mandatory `x-simulated-trading: 1` on private request preparation;
- OKX REST prehash/signature construction;
- runtime-only credentials with redacted representations;
- no production/live fallback.

Current official OKX documentation continues to identify the same global REST base for Demo, requires Demo request context/header, and documents the private REST authentication headers/signature scheme.

### Provider identity / `clOrdId`

**PASS / STATIC ONLY**, subject to the remaining materialization-integrity blocker above.

The provider client ID remains deterministic from the E4 internal client ID, alphanumeric, and at most 32 characters. Current OKX documentation states that `clOrdId` is case-sensitive alphanumeric up to 32 characters and unique among currently pending orders, with historical reuse possible after terminal state.

### Freshness hardening

**PASS / STATIC ONLY**

Preserved E4-local policy:

```text
metadata policy = okx-instrument-metadata-freshness-v0.2
general cache/sizing ceiling = 300 seconds
submit observation age <= 5 seconds
scheduled sizing-change guard = 60 seconds
```

Current official instrument metadata documents `upcChg` with `tickSz`, `minSz`, and `maxMktSz`; for FUTURES/SWAP a `minSz` change synchronously changes `lotSz`. Corrected source parses `maxMktSz`, validates it, and prevents a provider market size above it. Unknown scheduled-change parameters and already-effective changes fail closed.

The 5-second/60-second values remain internal E4 safety policy, not provider guarantees or shared-contract semantics.

### Canonical/provider quantity separation

**PASS through sizing/materialization function, but end-to-end submit still blocked by finding 001.**

Canonical quantity remains BTC under `base-asset-v0.1`; OKX `sz` remains provider contract quantity. The corrected sizing function recomputes provider contracts from current metadata and enforces the canonical upper bound.

### Account/asset-movement surface

**PASS / STATIC ONLY**

No account-mode, position-mode, leverage, withdrawal, deposit, funding transfer, internal/sub-account transfer, or balance-adjustment capability was added.

### Broker / PaperBroker regression

**PASS / STATIC COMPATIBILITY**

PR #12 still does not modify the broker-neutral `Broker`, `PaperBroker`, canonical execution gateway, or shared execution model implementation. Previously accepted idempotency/partial-fill/overfill/ambiguity behavior is therefore unchanged by this PR at source level.

Executable regression remains `NOT_RUN`.

## Repository / scope review

Current PR #12 changed files are limited to:

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
```

No `contracts/**` edit, E1/E2/E3/E5/E6 production rewrite, GitHub workflow/CI addition, real secret/credential material, or unrelated feature expansion was found.

Corrected implementation pin `651541ba...` to current PR head `c151fa7c...` changes only `coordination/E4/STATUS.md`; production/test/docs blobs are unchanged after the corrected implementation pin.

At re-review time GitHub reports PR #12 `mergeable=false`, with the PR branch `ahead 18 / behind 2` relative to current `main`. The two current-main-only commits modify only `coordination/E4/TASK.md` and `coordination/E7/TASK.md`. E4 should resynchronize after fixing the remaining blocker and E7 should recheck the resulting exact revision/scope.

## Test-definition review

Corrected fake-transport tests now cover:

- forged oversized sizing audit;
- changed request quantity invalidating prior sizing;
- altered metadata / metadata reference invalidating prior sizing;
- unsupported account-level/position-mode combinations;
- arbitrary absence-code configuration removed;
- non-success order lookup not proving absence;
- reconciliation never authorizing retry;
- forged/mutated/replayed/cross-materialization reconciliation evidence;
- known-state/fill contradiction matrix;
- overfill and missing average price;
- unknown state fail-closed;
- existing Demo/auth/freshness/quantity-separation boundaries.

Missing for closure of finding 001:

- post-prepare mutation of `OKXOrderMaterialization.body`, especially `body["sz"]`;
- direct caller construction of an `OKXOrderMaterialization` followed by `submit_entry()`;
- submit-time revalidation/fingerprint rejection for tampered `instId`, `side`, `posSide`, `ordType`, `clOrdId`, or `sz`.

No test was executed in GitHub.

## Final recommendation

`PR #12`: **DO NOT MERGE**.

E4 must close `E4-OKX-MATERIALIZATION-INTEGRITY-001` end-to-end at the actual provider submit boundary and add the missing deterministic tamper tests. After the correction, E4 should synchronize PR #12 with current `main` and return an exact revised implementation pin.

The next approved-local stage is **not yet authorized**. After a future E7 static PASS and merge, PM/Product Owner may separately consider an approved-local **connectivity/read-only dry integration** stage. That future stage still must not be interpreted as Demo order submission or provider retry authorization.

## Release / execution state

```text
Executable verification: NOT_RUN
Provider requests/orders: NOT_SENT
Provider retry: NOT_AUTHORIZED / DISABLED
Demo order submission: NOT_AUTHORIZED
Gate A: BLOCKED / UNCHANGED
Gate B: BLOCKED / UNCHANGED
Gate C: BLOCKED / UNCHANGED
Gate D: BLOCKED / UNCHANGED
```

E7 stops after this targeted re-review and waits for PM/E4 correction. No PR merge, provider call, local execution, or next implementation task was started.