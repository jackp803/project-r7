# E7 Status

- task_id: `E7-20260821-010`
- agent: `E7`
- state: `DONE / BLOCKED_WAITING_E4_CORRECTION`
- branch: `agent/e7-e4-okx-demo-review-20260821`
- review_target: `PR #12 execution: add Demo-first OKX provider adapter`
- reviewed_implementation_revision: `b7031c52a38623c528ee9352276793d8110854e0`
- observed_pr_head: `94ca2f861d9e7a51277c5c63ff20f730c7f19f92` (`coordination/E4/STATUS.md` successor only after implementation pin)
- review_artifact: `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md`
- summary: `PR #12 is BLOCKED from merge. Demo authentication/environment isolation and submit-freshness hardening are statically acceptable, but request materialization can trust a forged sizing audit, the account-level/position-mode matrix is underconstrained, retry accepts caller-constructible reconciliation evidence, arbitrary configured absence codes can unlock retry without accepted provider authority, and known provider order states are not checked for state/fill consistency.`

## Dispositions

- demo_environment_auth_security: `PASS / STATIC ONLY`
- request_materialization_account_prerequisites: `FAIL / BLOCKING`
- freshness_hardening: `PASS / ACCEPT / STATIC ONLY`
- ambiguity_reconciliation_retry_safety: `FAIL / BLOCKING`
- provider_response_normalization: `FAIL / BLOCKING`
- broker_paperbroker_regression_static_compatibility: `PASS / STATIC ONLY`
- pr_12_merge_recommendation: `BLOCKED / DO NOT MERGE`
- next_approved_local_demo_connectivity_dry_stage: `BLOCKED / NOT YET`
- demo_order_authorization: `NOT_AUTHORIZED`
- real_money_execution: `BLOCKED / NOT_AUTHORIZED`
- executable_verification: `NOT_RUN`
- actual_demo_provider_requests: `NOT_SENT`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`

## Blocking findings

### `E4-OKX-MATERIALIZATION-INTEGRITY-001`

Owner: `E4`

`materialize_demo_market_order()` trusts caller-constructible `OKXEntrySizingAudit.provider_requested_contract_quantity` and a separately supplied effective canonical quantity instead of re-establishing the conversion from the exact current metadata/request. A forged audit can therefore decouple body `sz` from the E5-approved BTC exposure bound.

Required correction: recompute/verify sizing at materialization from the exact `OrderRequest` + current validated metadata, or use an integrity-bound/opaque adapter-issued sizing artifact. Add deterministic forged/tampered sizing tests.

### `E4-OKX-ACCOUNT-MATRIX-001`

Owner: `E4`

`expected_account_level` and `expected_position_mode` are independently configurable. Validation currently proves only “provider value equals caller configuration,” not that the configured combination is legal/supported for the bounded isolated BTC-USDT-SWAP flow.

Required correction: define a reviewed supported account-level/position-mode matrix or narrow V1 to an explicit supported combination; reject unsupported/uncertain combinations before materialization. At minimum Spot mode and other definitely incompatible combinations must not become valid merely through configuration.

### `E4-OKX-RETRY-PROVENANCE-001`

Owner: `E4`

`retry_entry()` accepts ordinary caller-constructible `OKXReconciliationEvidence` and checks only fields. There is no adapter-issued one-time token/MAC/internal fresh-query binding or exact materialization fingerprint. Forged evidence can authorize removal of the ambiguous result and a second submit.

Required correction: bind retry authorization to fresh provider queries and the exact materialization with enforceable adapter-owned provenance; add forged/mutated/replayed evidence and materialization-tamper tests.

### `E4-OKX-ORDER-ABSENCE-001`

Owner: `E4`

Default empty `order_not_found_codes` is fail-closed, but arbitrary caller configuration can turn a code such as test fixture `51603` into authoritative absence and unlock retry. This review did not find sufficient current official authority to canonicalize that code for this project.

Required correction: keep retry structurally disabled until an E7-reviewed/provider-authoritative absence policy exists, or make absence semantics a controlled validated adapter policy that ordinary callers cannot invent. Actual Demo retry remains blocked.

### `E4-OKX-ORDER-STATE-CONSISTENCY-001`

Owner: `E4`

Known provider states are mapped without enforcing state/fill consistency. Contradictions such as `filled` with `accFillSz < sz`, `partially_filled` with zero fill, or `live` with non-zero fill can be mapped optimistically.

Required correction: enforce a state/fill consistency table and fail closed to explicit hard failure or `RECONCILIATION_REQUIRED`; add deterministic contradiction tests.

## Accepted static boundaries

### Demo/auth security

Accepted statically:

- runtime-injected/redacted credentials;
- required Demo header on private request materialization;
- Demo-only environment configuration;
- bounded private endpoint allowlist;
- no production/live fallback in this source layer;
- no withdrawal/funding/sub-account-transfer/account-mode/position-mode/leverage mutation surface;
- no real credentials or secrets committed in reviewed scope.

### Freshness hardening

Accepted E4-local policy:

```text
policy = okx-instrument-metadata-freshness-v0.2
general cache/sizing ceiling = 300 seconds
submit observation age <= 5 seconds
scheduled sizing-change guard = 60 seconds
```

`upcChg` unknown parameters and already-effective changes fail closed; sizing-relevant `minSz/maxMktSz` changes inside the guard block submit materialization; `tickSz` does not manufacture MARKET price semantics. These durations are E4 safety policy, not provider guarantees and are not shared-contract semantics.

### Broker/PaperBroker compatibility

PR #12 does not modify the previously accepted broker-neutral `base.py`, `paper.py`, `gateway.py`, or `models.py`. Static compatibility remains PASS; executable regression evidence remains NOT_RUN.

## Provider fact recheck

Current official OKX API V5 documentation/changelog was rechecked for the assumptions used by this adapter, including the current global REST domain guidance, Demo header, REST authentication/signature material, `clOrdId`, account config/position modes, isolated MARKET request fields, derivative contract sizing, order/position/fill/pending read surfaces, current order-state meanings, and public instrument scheduled-change metadata.

No sufficiently stable current official source was accepted to make test fixture `51603` a canonical order-absence code for retry.

## Scope / repository integrity

PR #12 changed-file scope contains only E4 code/tests/docs/status. No shared-contract edit, E1/E2/E3/E5/E6 production rewrite, workflow/CI addition, real credential, provider asset-movement surface, or unrelated feature expansion was found.

The PR branch was observed behind latest main only by current coordination TASK changes; no producer/shared-contract drift was introduced by that delta. This does not override the five E4 source blockers above.

## Test-definition review

Existing fake-transport tests cover valid signing/Demo header, valid `clOrdId`, isolated MARKET body, valid quantity separation, account/config mismatch, existing exposure/pending-order blocks, ambiguity without blind ordinary resubmit, reconciliation reads, fail-closed default absence handling, response normalization basics, and freshness scheduling.

Required blocker tests are missing for:

- forged/mutated/replayed reconciliation evidence;
- exact materialization fingerprint mismatch;
- forged/tampered sizing audit with oversized provider `sz`;
- materially changed request/materialization under the same logical identity;
- invalid supported account-level/position-mode combinations;
- contradictory provider state/fill combinations.

No test was executed in GitHub.

## Next action

`E4` must correct the five blocking findings and push a revised PR #12 source/test/handoff revision. `E7` must statically re-review that revision before merge.

Do **not** start approved-local Demo connectivity/dry integration yet. After source correction + E7 static PASS, PM/Product Owner may separately decide whether to authorize an approved-local connectivity/dry stage. Actual Demo order submission and retry require separate explicit authorization and prerequisite resolution. Successful Demo behavior would still not advance PAPER/SHADOW/LIVE automatically.

E7 stops here and waits for PM. No PR merge, provider request, provider execution, or next-stage implementation was started by E7.