# E7 Current Task

- task_id: `E7-20260821-008`
- issued_at: `2026-08-21T13:31:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e4-okx-sizing-review-20260821`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, Product Owner OKX decision

## Objective

Perform static integration/safety review of E4 PR #11, covering the accepted E5 ApprovedTradePlan -> E4 canonical OrderRequest translation and deterministic local OKX BTC-USDT-SWAP sizing boundary before PR #11 may be merged.

This task does **not** authorize OKX private/Demo networking or executable verification in GitHub.

## Review inputs

- PR: `#11 execution: add canonical entry translation and OKX sizing layer`
- branch: `agent/e4-execution-v2`
- E4 implementation/docs/handoff revision: `c71bf9c66a7f37cedb8bbbcf3000591970a081eb`
- E4 handoff: `docs/execution/E4_TO_E7_HANDOFF.md`
- upstream E2 producer accepted and merged via PR #9
- upstream E5 producer accepted and merged via PR #10
- parent schema: `contracts-v0.1`
- entry profile: `entry-v0.1 / MARKET`
- quantity profile: `base-asset-v0.1 / BASE_ASSET / BTC`
- executable verification: `NOT_RUN`

## Required actions

1. Work only on fresh branch `agent/e7-e4-okx-sizing-review-20260821` from latest `main`.
2. Statically review the E5 -> E4 boundary against the merged producer code and canonical execution profiles. Confirm at minimum:
   - only a valid ApprovedTradePlan crosses into E4;
   - `entry_instruction.profile_version=entry-v0.1` and `order_type=MARKET` are required;
   - `LONG -> BUY`, `SHORT -> SELL`, `MARKET -> MARKET` are purely mechanical;
   - advisory `reference_price` cannot become executable limit/stop/trigger/TIF;
   - shared `OrderRequest.quantity` preserves the canonical BTC quantity/profile and never becomes OKX contract `sz`.
3. Review E4 OKX metadata validation and sizing logic against ADR-0003 and the canonical profile. Confirm:
   - configured mapping is isolated to E4/provider scope: `BTC_USDT_PERP -> BTC-USDT-SWAP`;
   - required metadata identity/type/value/lot/min/tick/state/reference/observation fields are validated;
   - metadata freshness policy is explicit/versioned and fail closed;
   - unsupported, stale, missing, malformed, provider/instrument-mismatched, or non-tradable metadata blocks new exposure;
   - only the reviewed direct conversion class is accepted;
   - `base_per_contract = ctVal * ctMult` is used only when current metadata proves the required BTC-denominated supported conversion.
4. Recheck current official OKX API V5 documentation for the provider-dependent facts used by E4, especially `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, instrument `state`, and derivative order `sz`. Use official OKX sources when available.
5. Review quantization safety:

```text
raw_contracts = approved_base_quantity / base_per_contract
provider_sz   = floor_to_valid_lot(raw_contracts, lotSz)
effective_base = provider_sz * base_per_contract
```

Require:

```text
provider_sz >= minSz
0 < effective_base <= E5-approved canonical BTC quantity
```

Any path that rounds up beyond the approved bound is a blocking safety defect.
6. Confirm canonical and provider-native audit facts remain separate and provider contract counts are not written into shared canonical quantity fields.
7. Review preservation of the previously accepted Broker/PaperBroker safety behavior: stable idempotency identity, requested-vs-filled separation, partial fill support, overfill rejection, ambiguous acknowledgement -> reconciliation required, and query/reconcile-before-retry.
8. Review deterministic test definitions for the above boundaries. Do not execute tests in GitHub.
9. Check PR #11 changed-file scope for shared-contract collision, E5 risk-authority leakage, unsafe defaults, secret exposure, provider asset-movement capability, GitHub workflow/CI additions, or unintended historical-evidence deletion.
10. Explicitly classify the hard-coded E4 metadata freshness policy (`okx-instrument-metadata-freshness-v0.1`, currently 300 seconds) as `ACCEPT`, `NON_BLOCKING_HARDENING`, or `BLOCKING`, with rationale. Do not move the TTL into shared contracts merely for convenience.
11. Account for the E4 status note that the prior E2/E5 review artifact path was not present after synchronization. Verify the actual merged E2/E5 producer revisions and canonical contracts directly; do not treat a missing documentation copy as producer authority.
12. Persist an E7 review artifact and update `coordination/E7/STATUS.md` with:
   - E5->E4 boundary disposition `PASS | FAIL | BLOCKED`;
   - E4 entry translator disposition;
   - OKX sizing/metadata safety disposition;
   - Broker/PaperBroker regression-static disposition;
   - PR #11 merge recommendation;
   - exact findings and owners;
   - executable disposition `NOT_RUN`;
   - Gate A/B/C/D unchanged.
13. If static review passes, state whether PM may merge PR #11 and whether the next bounded stage may begin. The next stage, if recommended, must still keep real-money execution blocked; distinguish an OKX Demo/private adapter construction recommendation from any PAPER/SHADOW/LIVE authorization.
14. Do not modify E1-E6 production code, shared contracts, or PR #11 implementation under this review task. Do not create a Codex ticket without a locally reproduced defect.
15. Do not use GitHub Actions/CI/hosted runner/project compute and do not convert static PASS into executable PASS.

## Acceptance

Task is complete when Git contains a precise static/safety review of PR #11 with a merge recommendation and exact next-stage recommendation while executable evidence remains `NOT_RUN` and release gates remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- OKX private/Demo API implementation;
- credentials/secrets;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI;
- treating source/static review as executable verification.

## Completion / status

Persist the review, update STATUS, then stop and wait for PM. Do not merge PR #11 yourself and do not start provider networking automatically.
