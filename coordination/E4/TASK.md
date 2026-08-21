# E4 Current Task

- task_id: `E4-20260821-010`
- issued_at: `2026-08-21T15:04:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-okx-demo-adapter-20260821`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, E7 review `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md`

## Objective

Correct only the five E7 blocking findings in PR #12 while preserving the accepted Demo/auth security, submit-freshness hardening, canonical/provider quantity separation, and broker-neutral safety behavior.

This is a source/test correction task only. It does **not** authorize provider execution, real credentials, production/live mode, a concrete network transport, account mutation, asset movement, or PAPER/SHADOW/LIVE advancement.

## Reviewed baseline

- PR: `#12 execution: add Demo-first OKX provider adapter`
- reviewed implementation revision: `b7031c52a38623c528ee9352276793d8110854e0`
- E7 review persisted on `main` via PR #13
- Demo environment/auth security: `PASS / STATIC ONLY`
- freshness hardening: `PASS / ACCEPT / STATIC ONLY`
- Broker/PaperBroker static compatibility: `PASS / STATIC ONLY`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`

## Blocking findings to correct

### 1. `E4-OKX-MATERIALIZATION-INTEGRITY-001`

`materialize_demo_market_order()` must not trust caller-constructible sizing quantities as authority.

Required correction:

- Re-establish provider sizing from the exact current `OrderRequest` plus the exact submit-validated `OKXInstrumentMetadata` at materialization time, using the accepted deterministic sizing policy.
- Provider `sz` used in the order body must come from that recomputation, not directly from caller-supplied `OKXEntrySizingAudit` fields.
- If a prior sizing/audit object remains an input, treat it only as evidence to compare against the recomputed result; any mismatch in trade-plan identity, side, metadata reference/observation, approved canonical quantity, provider contract quantity, effective canonical quantity, or conversion facts must fail closed.
- Preserve invariant `0 < effective_base <= E5-approved canonical BTC quantity`.
- Add deterministic tests for forged/tampered sizing audit, oversized `sz`, altered metadata, altered request quantity, and metadata/audit mismatch.

### 2. `E4-OKX-ACCOUNT-MATRIX-001`

Caller configuration must not make an impossible OKX account-level / position-mode combination acceptable.

Required correction:

- Recheck current official OKX V5 account-mode/position-mode documentation.
- Encode only combinations that are explicitly supported for the bounded `BTC-USDT-SWAP`, isolated, MARKET-entry flow.
- Reject Spot-only or any unsupported/uncertain combination before materialization.
- If the complete matrix cannot be established from current official authority, narrow V1 to the smallest explicitly documented supported subset and document the exact official basis. Do not guess.
- Add tests for every accepted combination and representative rejected combinations, including definitely incompatible Spot mode.

### 3. `E4-OKX-RETRY-PROVENANCE-001`

Caller-constructible `OKXReconciliationEvidence` must never authorize a second submit.

Required correction for this task:

- Prefer the fail-closed V1 policy: **provider retry remains structurally disabled** until an authoritative order-absence policy is separately accepted.
- `retry_entry()` must not be unlockable by caller-supplied/mutated/replayed evidence.
- If reconciliation evidence remains public data, it may report provider truth but must not itself be an execution authorization token.
- Do not introduce a retry token/MAC solely to bypass finding #4 below; retry remains disabled while authoritative absence semantics are unresolved.
- Add tests proving forged, mutated, replayed, or cross-materialization evidence cannot cause a second transport submit.

### 4. `E4-OKX-ORDER-ABSENCE-001`

Ordinary callers must not be able to configure arbitrary provider error codes as authoritative proof of order absence.

Required correction:

- Remove or neutralize caller-controlled `order_not_found_codes` as a retry-enabling authority.
- Do **not** canonicalize fixture/example code `51603` or any other code without current official provider authority accepted by E7.
- Until such authority exists, a non-success order lookup cannot prove absence for retry and must leave retry blocked.
- Reconciliation may still distinguish `found`, `unknown/not-proven`, and provider-error outcomes for audit purposes, but no unresolved/non-success outcome may authorize resubmit.
- Add tests showing arbitrary configured codes cannot enable retry.

### 5. `E4-OKX-ORDER-STATE-CONSISTENCY-001`

Known provider order states must be checked against size/fill facts before mapping to optimistic canonical states.

Required correction:

Define and enforce a fail-closed consistency table consistent with current official OKX semantics. At minimum:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled/mmp_canceled -> 0 <= accFillSz <= sz
```

Additional requirements:

- any accumulated fill greater than requested provider size fails closed;
- any positive canonical fill requires a valid fill/average price when that field is required by the current response model;
- unknown or contradictory state/fill combinations become `RECONCILIATION_REQUIRED` or explicit hard failure, never optimistic success;
- canceled states may preserve actual partial-fill truth rather than pretending zero fill;
- add contradiction tests for `filled` with underfill, `partially_filled` with zero/full fill, `live` with non-zero fill, and overfill.

## Required actions

1. Non-destructively synchronize the existing PR #12 branch with latest `main` before correction. Preserve branch history; no force rewrite.
2. Modify only E4-owned source/tests/docs/status needed for the five findings.
3. Preserve all previously accepted boundaries:
   - mandatory Demo-only environment and `x-simulated-trading: 1` on authenticated Demo requests;
   - runtime-only/redacted credentials;
   - private endpoint allowlist;
   - canonical BTC quantity distinct from provider `sz`;
   - `tdMode=isolated`, MARKET-only entry path;
   - no limit/stop/trigger/TIF invention;
   - no production/live fallback;
   - no account/position-mode/leverage mutation;
   - no withdrawal/deposit/funding/sub-account/internal transfer/balance-adjustment surface;
   - freshness policy `okx-instrument-metadata-freshness-v0.2` remains E4-local and fail closed.
4. Do not broaden provider endpoint scope or implement concrete networking.
5. Do not edit shared contracts or other-agent production code.
6. Update `docs/execution/E4_TO_E7_HANDOFF.md`, relevant E4 Demo docs, and `coordination/E4/STATUS.md` with exact corrected revision and disposition of each finding.
7. Keep executable verification local-only. Without an approved local environment, record `NOT_RUN` plus exact commands; do not run GitHub Actions/CI/hosted/project compute.
8. Push corrections to the existing PR #12 branch, then stop. Do not merge PR #12 yourself and do not start Demo connectivity/order execution.

## Acceptance

Static/source completion requires all five E7 findings to be addressed in source and deterministic test definitions, with no regression to previously accepted Demo/auth/freshness/broker boundaries. PR #12 remains pending E7 re-review. Actual Demo connectivity, Demo order submission, provider retry, PAPER/SHADOW/LIVE, and real-money execution remain unauthorized.

## Writable scope

- `src/execution/**`
- `src/brokers/**`
- `tests/execution/**`
- `tests/brokers/**`
- E4-owned docs/status/handoff
- `coordination/E4/STATUS.md`

## Forbidden scope

- `contracts/**` edits;
- E1/E2/E3/E5/E6 production rewrites;
- real credentials/secrets;
- production/live mode;
- actual provider requests/orders;
- concrete network transport;
- automatic account/position-mode/leverage mutation;
- asset movement APIs;
- arbitrary provider absence-code authority;
- enabling provider retry while absence semantics remain unresolved;
- PAPER/SHADOW/LIVE advancement;
- GitHub Actions/CI/hosted runner/project compute.

## Completion / status

Correct the five E7 findings, update handoff/STATUS, push to PR #12 branch, then stop and wait for PM/E7 re-review.
