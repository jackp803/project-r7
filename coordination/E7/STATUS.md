# E7 Status

- task_id: `E7-20260822-001`
- agent: `E7`
- state: `DONE_PENDING_PM`
- branch: `agent/e7-e4-okx-demo-final-rereview-20260822`
- review_target: `PR #12 execution: add Demo-first OKX provider adapter`
- reviewed_e4_revision: `99bf09461e32117001ce7e587be44dcc3d152ab2`
- observed_pr_head: `25294d72920efab3011eb5060079bf2edca5d056`
- implementation_pin_to_pr_head_delta: `coordination/E4/STATUS.md only`
- review_artifact: `status/e7/E4_OKX_DEMO_FINAL_REREVIEW_20260822.md`
- summary: `Final targeted static/security re-review closes E4-OKX-MATERIALIZATION-INTEGRITY-001 end-to-end. submit_entry now requires exact adapter-issued object identity, validates immutable issued semantic facts before idempotency-cache access, re-derives the signed provider body from adapter-owned trusted preparation facts, rejects caller-mutated body/provider fields before transport, rechecks deterministic clOrdId binding and canonical BTC upper-bound invariants, and preserves the four previously closed findings. PR #12 is statically acceptable for merge. Executable verification remains NOT_RUN; no provider request/order was sent.`

## Five finding dispositions

- `E4-OKX-MATERIALIZATION-INTEGRITY-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ACCOUNT-MATRIX-001`: `CLOSED / PASS STATIC`
- `E4-OKX-RETRY-PROVENANCE-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-ABSENCE-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001`: `CLOSED / PASS STATIC`

## Final submit-integrity disposition

Accepted source chain:

```text
canonical OrderRequest + submit-validated metadata
  -> recomputed OKX sizing
  -> caller sizing treated as evidence only
  -> adapter-issued OKXOrderMaterialization
  -> adapter-owned frozen _IssuedOKXPreparation
  -> submit_entry exact-object provenance check
  -> semantic fact / Demo / account / clOrdId / quantity checks
  -> trusted provider body re-derived from issued preparation
  -> caller-visible body must exactly equal trusted body
  -> trusted body signed
  -> transport
```

Static guarantees established:

- exact object instance must have been issued by the same adapter;
- dataclass equality/clone is not submit provenance;
- cross-adapter substitution fails;
- direct caller construction fails before cache/transport;
- changed semantic fields under the same logical identity fail;
- provider `clOrdId` is re-derived from internal `client_order_id` and rechecked;
- provider contract quantity remains positive;
- `0 < effective canonical BTC <= E5-approved canonical BTC quantity`;
- provider contract `sz` remains distinct from canonical BTC quantity;
- signed body is freshly re-derived from trusted adapter-owned preparation facts;
- mutations of `sz`, `instId`, `side`, `posSide`, `ordType`, or `clOrdId` fail before transport;
- materially different adapter preparation under the same `clOrdId` fails closed;
- provenance validation occurs before idempotency-cache access.

## Submit-integrity test-definition review

`tests/brokers/test_okx_submit_integrity.py` statically covers:

- post-prepare `sz` mutation rejection;
- `instId` mutation rejection;
- `side` mutation rejection;
- `posSide` mutation rejection;
- `ordType` mutation rejection;
- `clOrdId` mutation rejection;
- direct caller clone rejection;
- cross-adapter substitution rejection;
- same-client material change rejection;
- materially different re-preparation rejection;
- exact valid Demo MARKET isolated body;
- repeated-submit idempotency without a second transport send;
- canonical/provider quantity separation and approved BTC upper bound.

Executable result remains `NOT_RUN`; these definitions were not executed on GitHub.

## Regression dispositions

- demo_environment_auth_security: `PASS / STATIC ONLY`
- v1_account_matrix: `PASS / acctLv=2 Futures mode + net_mode|long_short_mode + tdMode=isolated`
- canonical_provider_quantity_separation: `PASS / STATIC ONLY`
- freshness_hardening: `PASS / STATIC ONLY / E4-LOCAL POLICY`
- provider_retry: `STRUCTURALLY DISABLED / PASS STATIC`
- order_absence_semantics: `FAIL-CLOSED / NO CALLER-CONFIGURABLE AUTHORITY / PASS STATIC`
- provider_response_normalization: `PASS / STATIC ONLY`
- broker_paperbroker_regression_static_compatibility: `PASS / UNCHANGED SOURCE`
- production_live_fallback: `ABSENT / PASS STATIC`
- account_position_leverage_mutation_surface: `ABSENT / PASS STATIC`
- withdrawal_deposit_funding_internal_subaccount_transfer_balance_adjustment_surface: `ABSENT / PASS STATIC`

## Current official OKX recheck

Rechecked on `2026-08-22` against official OKX V5 documentation.

Still consistent with reviewed bounded assumptions:

- Demo REST uses `https://openapi.okx.com` and private Demo requests require `x-simulated-trading: 1`;
- `acctLv=2` is Futures mode;
- FUTURES/SWAP support `net_mode` and `long_short_mode` in Futures mode;
- reviewed order path supports `tdMode=isolated`; isolated is not accepted for this path in multi-currency/portfolio modes;
- `market` is a valid SWAP order type;
- `clOrdId` is case-sensitive alphanumeric up to 32 characters and uniqueness is required among pending orders, not historical orders.

No new provider fact expands R7 authority. Provider retry remains disabled and Demo order submission remains unauthorized.

## Repository / PR disposition

Current PR #12 scope contains only:

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

Confirmed:

- shared contracts changed: `NO`;
- E1/E2/E3/E5/E6 production edits: `NO`;
- GitHub workflow/CI additions: `NO`;
- real credentials/secrets: `NONE FOUND`;
- unrelated feature expansion: `NO`;
- latest main at review: `730ef2e87054f5dbe370b4e72e50d6e03af1fc5c`;
- PR branch relative to latest main: `ahead 24 / behind 2`;
- latest-main-only delta: `coordination/E4/TASK.md` and `coordination/E7/TASK.md` only;
- production/shared-contract synchronization drift: `NONE`;
- GitHub current PR mergeable: `TRUE`.

## Merge / next stage

- pr_12_source_disposition: `PASS / STATIC ONLY`
- pr_12_merge_recommendation: `PM MAY MERGE`
- next_bounded_stage: `MAY BE APPROVED-LOCAL CONNECTIVITY / READ-ONLY DRY INTEGRATION ONLY`
- demo_order_authorization: `NOT_AUTHORIZED`
- provider_retry_authorization: `NOT_AUTHORIZED / SOURCE DISABLED`
- production_real_money_execution: `BLOCKED / NOT_AUTHORIZED`
- paper_shadow_live_advancement: `NONE`

The next read-only dry stage, if separately approved by PM/Product Owner, may validate connectivity/authentication read paths, account configuration reads and public/private read-only prerequisites in an approved local environment. It must not submit an order or enable retry.

## Verification / release state

- executable_verification: `NOT_RUN`
- actual_demo_provider_requests_orders: `NOT_SENT`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`

## Completion

E7 completed only `E7-20260822-001` and stops here.

E7 does not merge PR #12, does not start approved-local connectivity, does not execute provider requests, and does not start another task automatically. Next owner: `PM`.
