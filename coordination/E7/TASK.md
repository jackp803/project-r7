# E7 Current Task

- task_id: `E7-20260821-012`
- issued_at: `2026-08-21T16:02:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e4-okx-demo-rereview-20260821`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, prior review `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md`

## Objective

Perform a targeted static/security re-review of corrected PR #12 and determine whether all five prior E4 blocking findings are closed without regression before PR #12 may be merged or any approved-local OKX Demo connectivity stage may be considered.

This task does **not** authorize provider execution, real credentials, GitHub compute, Demo order submission, provider retry, PAPER/SHADOW/LIVE, or real-money trading.

## Review inputs

- PR: `#12 execution: add Demo-first OKX provider adapter`
- corrected branch: `agent/e4-okx-demo-adapter-20260821`
- corrected implementation/tests/docs/handoff revision: `651541ba0da646f0c2ab69117219e2c8ca21247c`
- current PR head after status completion: `c151fa7c37adafbf9f93157d80cf4b763dd775e2`
- prior E7 review artifact: `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`

## Findings requiring closure

1. `E4-OKX-MATERIALIZATION-INTEGRITY-001`
2. `E4-OKX-ACCOUNT-MATRIX-001`
3. `E4-OKX-RETRY-PROVENANCE-001`
4. `E4-OKX-ORDER-ABSENCE-001`
5. `E4-OKX-ORDER-STATE-CONSISTENCY-001`

## Required actions

1. Work only on fresh branch `agent/e7-e4-okx-demo-rereview-20260821` from latest `main`.
2. Compare the corrected PR #12 source against the exact prior findings. Do not rely only on E4 STATUS claims.
3. Re-review materialization integrity:
   - provider sizing used for `body.sz` must be recomputed from the exact current `OrderRequest` plus exact submit-validated metadata;
   - a caller-provided prior sizing/audit object, if retained, must be evidence-only and any mismatch must fail closed;
   - tampered request quantity, metadata, conversion facts, effective canonical quantity, or provider contract quantity must not survive materialization;
   - `0 < effective_base <= E5-approved canonical BTC quantity` must remain invariant.
4. Re-review the V1 account-level/position-mode matrix against **current official OKX V5 documentation**. E4 claims only `acctLv=2` with `net_mode | long_short_mode` and `tdMode=isolated` is accepted. Confirm this is a technically coherent explicitly supported subset for the bounded `BTC-USDT-SWAP` path and that unsupported/uncertain account modes fail closed. If official semantics do not support this exact narrowed subset, classify BLOCKING rather than guessing.
5. Re-review retry provenance:
   - provider retry must be structurally disabled in source;
   - caller-constructible, mutated, replayed, cross-materialization, or fabricated reconciliation evidence must not cause a second transport submit;
   - no hidden alternate retry/resubmit path may bypass the disabled policy.
6. Re-review order-absence authority:
   - caller-controlled `order_not_found_codes` or equivalent retry-enabling provider-code configuration must be absent/neutralized;
   - no fixture/example code may be canonicalized without current official authority;
   - non-success or empty order lookup must not prove absence or authorize retry.
7. Re-review order-state/fill consistency. Require at minimum:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled/mmp_canceled -> 0 <= accFillSz <= sz
```

   Overfill, underfill/invalid known-state combinations, missing required average fill price for positive fill, or unknown states must fail closed or become `RECONCILIATION_REQUIRED`, never optimistic success. Canceled states may retain real partial-fill quantity.
8. Recheck deterministic test definitions for all five fixes, including forged/tampered sizing evidence, invalid account combinations, forged/replayed reconciliation evidence, arbitrary absence-code attempts, and contradictory state/fill cases. Do not execute tests in GitHub.
9. Recheck previously accepted boundaries for regression:
   - Demo-only environment and mandatory `x-simulated-trading: 1`;
   - runtime-only/redacted credentials;
   - bounded private endpoint allowlist;
   - canonical BTC quantity separate from OKX contract `sz`;
   - `tdMode=isolated`, MARKET-only path;
   - submit-time metadata freshness hardening;
   - no production/live fallback;
   - no account/position/leverage mutation;
   - no withdrawal/deposit/funding/sub-account/internal transfer/balance-adjustment surface;
   - Broker/PaperBroker behavior unchanged.
10. Recheck PR #12 repository scope for shared-contract collision, other-agent production edits, secrets, GitHub workflow/CI additions, or unrelated feature expansion.
11. Persist a new E7 re-review artifact and update `coordination/E7/STATUS.md` with separate disposition for each of the five findings, regression boundaries, PR #12 merge recommendation, executable `NOT_RUN`, actual provider request state, and Gate A/B/C/D unchanged.
12. If and only if all five findings are statically closed, state whether PM may merge PR #12. Separately state whether the **next bounded stage may be approved-local connectivity/read-only dry integration**. Do not authorize Demo order submission or retry merely because static source passes.
13. If any blocker remains, identify the exact source condition and owner. Do not merge PR #12 or start another implementation task.
14. Do not modify E1-E6 production code or shared contracts. Do not create a Codex ticket without locally reproduced executable failure.
15. Do not use GitHub Actions/CI/hosted runner/project compute and do not turn static PASS into executable PASS.

## Acceptance

Task is complete when Git contains an exact-revision targeted re-review that either:

- closes all five findings and gives a precise PR #12 merge/next-stage recommendation; or
- keeps PR #12 blocked with exact remaining source findings.

Executable evidence remains `NOT_RUN`, provider requests remain `NOT_SENT`, provider retry remains unauthorized, and Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- actual provider calls/orders;
- real credentials/secrets;
- production/live trading;
- automatic account/leverage/position-mode mutations;
- asset movement;
- provider retry enablement;
- PAPER/SHADOW/LIVE gate advancement;
- GitHub compute/CI.

## Completion / status

Persist the targeted re-review and STATUS, then stop and wait for PM. Do not merge PR #12 or start provider execution automatically.
