# E7 Status

- task_id: `E7-20260821-008`
- agent: `E7`
- state: `DONE_PENDING_PM`
- branch: `agent/e7-e4-okx-sizing-review-20260821`
- review_scope: `PR #11 E5 ApprovedTradePlan -> E4 OrderRequest translation + deterministic local OKX BTC-USDT-SWAP sizing + Broker/PaperBroker regression`
- reviewed_e4_implementation: `c71bf9c66a7f37cedb8bbbcf3000591970a081eb`
- reviewed_pr_head: `aedb946c29e4e0695c3f020c90cdf0fcc8e9bd13`
- e5_to_e4_boundary: `PASS / STATIC ONLY`
- e4_entry_translator: `PASS / STATIC ONLY`
- okx_sizing_metadata_safety: `PASS / STATIC ONLY`
- broker_paperbroker_regression: `PASS / STATIC ONLY`
- metadata_freshness_300s: `NON_BLOCKING_HARDENING`
- pr11_merge_recommendation: `PASS — PM MAY MERGE PR #11`
- next_stage_recommendation: `YES — PM may issue a separate bounded OKX Demo/private adapter construction task after merge; this is not Demo execution/PAPER/SHADOW/LIVE/real-money authorization`
- executable_verification: `NOT_RUN`
- github_compute: `NOT_USED`
- contracts_changed_by_e7: `NO`
- e1_e6_production_code_changed_by_e7: `NO`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- blocking_findings: `NONE`
- non_blocking_finding: `E4-OKX-FRESHNESS-HARDEN-001`
- finding_owner: `E4 in future provider-adapter task`
- handoff_path: `status/e7/E4_OKX_SIZING_STATIC_REVIEW_20260821.md`
- next_owner: `PM`

## Producer authority verification

The missing prior E2/E5 review-artifact copy was not used as authority.

Actual merged producer code was verified directly on current `main`:

```text
E2 accepted revision: f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4
main src/strategy/trade_intent.py blob: d2e877cbdcf23058e020db2a2e0158811bcca51b

E5 accepted revision: e5f7088301a92deadfd9f6c416ae03b466c38a47
main src/risk/engine.py blob: ce07c4ccf7aa7b4d57d47a5b9a00fd3b60bf0c78
```

The main blobs match the reviewed accepted producer pins.

## E5 -> E4 boundary

Accepted profiled plan requirements include:

```text
schema_version = contracts-v0.1
symbol = BTC_USDT_PERP
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type = MARKET
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset = BTC
```

Mechanical translation is preserved:

```text
LONG -> BUY
SHORT -> SELL
MARKET -> MARKET
ApprovedTradePlan.quantity -> OrderRequest.quantity unchanged
```

`reference_price` remains advisory only. Executable limit/stop/trigger/TIF fields fail closed.

Shared `OrderRequest.quantity` remains canonical BTC and is not replaced with provider-native `sz`.

## OKX sizing / metadata safety

Provider mapping remains E4-local:

```text
BTC_USDT_PERP -> BTC-USDT-SWAP
```

Supported direct conversion requires current validated metadata consistent with:

```text
provider = OKX
instType = SWAP
ctType = linear
ctValCcy = BTC
state = live
```

Required numeric metadata are positive finite decimals and include `ctVal`, `ctMult`, `lotSz`, `minSz`, and `tickSz`; observation/reference/freshness-policy facts are also required.

Sizing is:

```text
base_per_contract = ctVal * ctMult
raw_contracts = approved_base_quantity / base_per_contract
provider_sz = floor(raw_contracts / lotSz) * lotSz
effective_base = provider_sz * base_per_contract
```

Safety invariant statically preserved:

```text
provider_sz > 0
provider_sz >= minSz
provider_sz is a lotSz multiple
0 < effective_base <= E5-approved canonical BTC quantity
```

No round-up path beyond the approved BTC bound was found.

## Official OKX recheck

Current official OKX API V5 documentation was rechecked during this review for:

- `ctVal`
- `ctMult`
- `ctValCcy`
- `ctType`
- `lotSz`
- `minSz`
- `tickSz`
- instrument `state`
- derivative `sz`

Current public `BTC-USDT-SWAP` metadata was also checked through the official public instruments endpoint and is compatible with the reviewed direct class at review time:

```text
ctType=linear
ctVal=0.01
ctMult=1
ctValCcy=BTC
lotSz=0.01 contracts
minSz=0.01 contracts
tickSz=0.1
state=live
```

Provider facts must be reverified again at future implementation/execution time.

## Metadata freshness classification

`okx-instrument-metadata-freshness-v0.1 / 300 seconds` is classified:

```text
NON_BLOCKING_HARDENING
```

Rationale:

- explicit and versioned E4-local policy;
- no shared-contract leakage;
- missing/future/stale data fails closed;
- PR #11 has no provider networking/order submission;
- sizing still has identity/type/state/unit and exposure-upper-bound guards.

Future Demo/private adapter acceptance must strengthen freshness handling so 300 seconds is not treated as a provider stability guarantee. Submit-time refresh or equivalent proof is preferred, and official `upcChg/effTime` scheduled instrument changes must invalidate/shorten cached metadata when relevant.

Finding:

```text
E4-OKX-FRESHNESS-HARDEN-001
owner: E4
blocking for PR #11 merge: NO
required before future Demo/private adapter acceptance: YES
```

## Broker / PaperBroker regression

Static PASS confirmed for:

- stable idempotency identity;
- safety fingerprint includes canonical quantity profile/unit/asset;
- requested and filled quantities remain distinct;
- partial fills;
- overfill rejection;
- ambiguous acknowledgement -> `RECONCILIATION_REQUIRED`;
- no blind duplicate submit;
- explicit broker query/reconciliation before retry;
- retry re-checks order/position truth;
- fabricated reconciliation evidence rejection.

Broker interface exposes no withdrawal, funding-transfer, or sub-account-capital-movement capability.

## PR #11 scope / merge readiness

Changed-file scope contains only E4 coordination/docs/source/tests:

```text
coordination/E4/STATUS.md
docs/execution/E4_TO_E7_HANDOFF.md
docs/execution/OKX_SIZING_POLICY.md
src/brokers/base.py
src/brokers/okx_sizing.py
src/brokers/paper.py
src/execution/gateway.py
src/execution/models.py
tests/brokers/test_okx_sizing.py
tests/brokers/test_paper_broker.py
tests/execution/test_gateway.py
```

No shared contracts, E1/E2/E3/E5/E6 production code, GitHub workflow/CI file, secret/credential file, or asset-movement implementation is in the PR changed-file set.

At review time PR #11 is `mergeable=true`.

The E4 branch is behind latest main by 2 commits, but those commits modify only:

```text
coordination/E4/TASK.md
coordination/E7/TASK.md
```

No producer/domain/contract delta exists in that behind set, so it is not a static merge blocker.

## Executable / release disposition

```text
Executable verification: NOT_RUN
```

Future local commands documented by E4:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

They were not run in this GitHub environment.

No GitHub Actions, CI, hosted runner, GitHub-triggered runner, broker simulation, project test, or API experiment was used as executable verification.

No Gate A/B/C/D advancement occurred.

## Next-stage boundary

PM may merge PR #11 based on this static/source review.

After merge, PM may separately authorize bounded construction of a Demo-first OKX provider adapter, including current metadata retrieval, provider request mapping, client-order-ID constraints, account-mode/isolated prerequisite validation, and fail-closed reconciliation semantics.

That recommendation does not authorize current provider networking, real-money execution, PAPER/SHADOW/LIVE transition, withdrawal/funding movement, or release-gate PASS.

E7 stops here and waits for PM. No PR merge or provider networking is started automatically.
