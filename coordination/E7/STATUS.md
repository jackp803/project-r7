# E7 Status

- task_id: `E7-20260821-012`
- agent: `E7`
- state: `DONE / BLOCKED_WAITING_E4_CORRECTION`
- branch: `agent/e7-e4-okx-demo-rereview-20260821`
- review_target: `PR #12 execution: add Demo-first OKX provider adapter`
- reviewed_corrected_revision: `651541ba0da646f0c2ab69117219e2c8ca21247c`
- observed_pr_head: `c151fa7c37adafbf9f93157d80cf4b763dd775e2` (`coordination/E4/STATUS.md` successor only after corrected implementation pin)
- review_artifact: `status/e7/E4_OKX_DEMO_TARGETED_REREVIEW_20260821.md`
- summary: `Targeted re-review closes 4 of the 5 prior E4 blockers. Account matrix, retry provenance, order-absence authority, and order-state/fill consistency are statically closed. Materialization integrity remains blocking because submit_entry signs/sends caller-mutable/caller-constructible OKXOrderMaterialization.body without submit-time provenance/fingerprint/recomputation; post-prepare body.sz tampering can bypass the corrected materialization recomputation.`

## Finding dispositions

- `E4-OKX-MATERIALIZATION-INTEGRITY-001`: `BLOCKING / NOT CLOSED / E4 OWNER`
- `E4-OKX-ACCOUNT-MATRIX-001`: `CLOSED / PASS STATIC`
- `E4-OKX-RETRY-PROVENANCE-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-ABSENCE-001`: `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001`: `CLOSED / PASS STATIC`

## Regression dispositions

- demo_environment_auth_security: `PASS / STATIC ONLY`
- v1_account_matrix: `PASS / acctLv=2 Futures mode + net_mode|long_short_mode + tdMode=isolated`
- freshness_hardening: `PASS / STATIC ONLY / E4-LOCAL POLICY`
- provider_retry: `DISABLED / PASS STATIC`
- order_absence_semantics: `FAIL-CLOSED / NO CALLER CONFIG / PASS STATIC`
- provider_response_normalization: `PASS / STATIC ONLY`
- broker_paperbroker_regression_static_compatibility: `PASS / UNCHANGED SOURCE`
- canonical_provider_quantity_separation: `PASS INSIDE SIZING/MATERIALIZATION; END-TO-END SUBMIT BLOCKED BY MATERIALIZATION FINDING`
- asset_movement_account_mutation_surface: `ABSENT / PASS STATIC`

## Remaining blocking source condition

`materialize_demo_market_order()` now correctly recomputes sizing from the exact current `OrderRequest` and submit-validated metadata and rejects mismatching caller sizing evidence.

However, the resulting `OKXOrderMaterialization` is still caller-constructible and its `body` is a mutable `dict`. `submit_entry()` signs and sends `materialization.body` directly without proving that the body is the exact adapter-issued materialization or revalidating `sz`, `instId`, `side`, `posSide`, `ordType`, and `clOrdId` against the accepted immutable facts.

Therefore a caller can mutate `materialization.body["sz"]` after `prepare_entry()` or directly construct a materialization and reach the provider submit path without the corrected sizing recomputation governing the actual signed request.

Required E4 correction: bind provider submit to adapter-issued immutable/fingerprinted materialization or rederive/revalidate the provider request at submit time from the canonical request + current validated metadata. Add direct post-prepare body-tamper and caller-constructed-materialization tests.

## Official OKX recheck

Current official OKX V5 documentation was rechecked on 2026-08-21.

Accepted for the bounded matrix:

- `acctLv=2` is Futures mode;
- FUTURES/SWAP support `net_mode` and `long_short_mode` in Futures mode;
- official leverage/trading semantics explicitly support isolated SWAP operation for buy/sell and long/short position modes;
- `clOrdId` remains case-sensitive alphanumeric up to 32 characters and unique among current pending orders;
- Demo uses the global REST base with simulated-trading context/header;
- public instrument metadata exposes `upcChg` for `tickSz`, `minSz`, and `maxMktSz`; FUTURES/SWAP `minSz` change synchronously changes `lotSz`.

No current official provider error code is accepted as R7 order-absence authority; retry remains disabled, so this is fail-closed.

## Repository / PR state

- PR #12 corrected changed-file scope remains E4 code/tests/docs/status only.
- no `contracts/**` changes.
- no E1/E2/E3/E5/E6 production edits.
- no `.github/workflows` / CI additions.
- no real credentials/secrets found.
- no withdrawal/deposit/funding/sub-account/internal-transfer/balance-adjustment capability.
- corrected implementation pin -> current PR head changes only `coordination/E4/STATUS.md`.
- current PR branch relative to latest main: `ahead 18 / behind 2`.
- current-main-only delta from the PR merge base is coordination TASK files only.
- GitHub currently reports PR #12 `mergeable=false`.

## Test-definition review

Corrected definitions cover the four closed findings and the in-function portion of materialization integrity, including forged sizing evidence, changed request, changed metadata, invalid account modes, retry-evidence forgery/replay, arbitrary absence-code rejection, and contradictory state/fill combinations.

Still missing for materialization closure:

- mutate `body["sz"]` after `prepare_entry()` and prove submit is rejected;
- mutate `instId` / `side` / `posSide` / `ordType` / `clOrdId` after prepare and prove submit is rejected;
- directly caller-construct `OKXOrderMaterialization` and prove submit cannot bypass prepare/materialization authority.

No test was executed in GitHub.

## Merge / next-stage recommendation

- pr_12_merge_recommendation: `BLOCKED / DO NOT MERGE`
- next_approved_local_connectivity_readonly_dry_stage: `BLOCKED / NOT YET`
- demo_order_authorization: `NOT_AUTHORIZED`
- provider_retry_authorization: `NOT_AUTHORIZED / SOURCE DISABLED`
- real_money_execution: `BLOCKED / NOT_AUTHORIZED`
- executable_verification: `NOT_RUN`
- actual_demo_provider_requests_orders: `NOT_SENT`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`

## Next owner

`E4` must close `E4-OKX-MATERIALIZATION-INTEGRITY-001` at the actual provider submit boundary, add the missing deterministic tamper tests, synchronize PR #12 with current main, and return an exact corrected revision for E7 re-review.

E7 stops here and waits for PM/E4. No PR merge, provider call, local execution, or next-stage implementation is started automatically.
