# E7 Current Task

- task_id: `E7-20260822-001`
- issued_at: `2026-08-22T02:35:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e4-okx-demo-final-rereview-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, prior review artifacts in `status/e7/`

## Objective

Perform the final targeted static/security re-review of corrected PR #12 and determine whether `E4-OKX-MATERIALIZATION-INTEGRITY-001` is now closed end-to-end at the actual provider submit boundary without regression to the four previously closed findings or accepted Demo safety boundaries.

This task does **not** authorize provider execution, real credentials, GitHub compute, Demo order submission, provider retry, PAPER/SHADOW/LIVE, or real-money trading.

## Review inputs

- PR: `#12 execution: add Demo-first OKX provider adapter`
- E4 branch: `agent/e4-okx-demo-adapter-20260821`
- final corrected implementation/tests/docs/handoff revision: `99bf09461e32117001ce7e587be44dcc3d152ab2`
- current PR head after status completion: `25294d72920efab3011eb5060079bf2edca5d056`
- latest E4 task completed: `E4-20260821-012`
- previous targeted review: `status/e7/E4_OKX_DEMO_TARGETED_REREVIEW_20260821.md`
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED`

## Previously closed findings — must remain closed

- `E4-OKX-ACCOUNT-MATRIX-001` — `CLOSED / PASS STATIC`
- `E4-OKX-RETRY-PROVENANCE-001` — `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-ABSENCE-001` — `CLOSED / PASS STATIC`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001` — `CLOSED / PASS STATIC`

## Finding requiring final closure

- `E4-OKX-MATERIALIZATION-INTEGRITY-001`

## Required actions

1. Work only on fresh branch `agent/e7-e4-okx-demo-final-rereview-20260822` from latest `main`.
2. Review the exact E4 corrected source at `99bf09461e32117001ce7e587be44dcc3d152ab2`; do not rely only on E4 STATUS claims.
3. Verify submit-boundary provenance/integrity directly in source:
   - `submit_entry()` must reject a materialization not issued by that exact adapter instance;
   - caller-visible dataclass equality must not be sufficient provenance;
   - direct caller construction or a clone must fail before idempotency cache access and before transport;
   - cross-adapter substitution must fail;
   - materially altered semantic fields under the same logical/client identity must fail;
   - provider `clOrdId` must remain deterministically bound to internal `client_order_id`.
4. Verify the actual signed/sent provider request body is re-derived from trusted adapter-owned immutable preparation facts or proven exactly equivalent before signing. Caller-mutated `materialization.body` must never be execution authority.
5. Confirm submit rejects post-prepare mutation of at least:
   - `sz`;
   - `instId`;
   - `side`;
   - `posSide`;
   - `ordType`;
   - `clOrdId`.
6. Confirm all trusted submit facts remain bound to the accepted preparation context, including:
   - order/trade-plan/internal-client identities;
   - provider identity/side/position-side/order type/trade mode;
   - provider contract quantity;
   - effective canonical quantity;
   - E5-approved canonical quantity;
   - instrument metadata reference/observation;
   - Demo environment;
   - accepted account level/position mode;
   - freshness policy context.
7. Confirm invariant remains:

```text
0 < effective canonical BTC <= E5-approved canonical BTC quantity
```

and canonical BTC quantity remains distinct from OKX provider contract `sz`.
8. Inspect `tests/brokers/test_okx_submit_integrity.py` and verify deterministic definitions cover post-prepare body tamper, direct caller construction/clone, cross-adapter substitution, same-client material change, materially different re-preparation, valid exact Demo MARKET isolated body, repeated-submit idempotency, and quantity upper bound. Do not execute tests in GitHub.
9. Recheck no bypass exists through another E4 submit/resubmit/retry method. Provider retry must remain structurally disabled.
10. Recheck the four previously closed findings and prior accepted boundaries for regression:
   - V1 account matrix `acctLv=2`, `net_mode | long_short_mode`, `tdMode=isolated`;
   - no caller-configurable order-absence authority;
   - state/fill consistency fail-closed behavior;
   - Demo-only environment and mandatory `x-simulated-trading: 1`;
   - runtime-only/redacted credentials;
   - bounded private endpoint allowlist;
   - MARKET-only path;
   - submit-time metadata freshness hardening;
   - no production/live fallback;
   - no account/position/leverage mutation;
   - no withdrawal/deposit/funding/sub-account/internal transfer/balance-adjustment surface;
   - Broker/PaperBroker behavior unchanged.
11. Recheck PR #12 current branch against latest `main`: repository synchronization, changed-file scope, shared-contract collisions, other-agent production edits, secrets, workflow/CI additions, and unrelated feature expansion.
12. Persist a new E7 final re-review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed E4 revision and observed PR head;
   - `E4-OKX-MATERIALIZATION-INTEGRITY-001` disposition;
   - explicit confirmation that the other four findings remain closed or exact regression blocker;
   - Demo/auth/freshness/quantity/account/retry/response-normalization dispositions;
   - PR #12 merge recommendation;
   - executable verification `NOT_RUN`;
   - actual provider request state `NOT_SENT`;
   - Gate A/B/C/D unchanged.
13. If and only if all five findings are statically closed and scope is coherent, state that PM may merge PR #12. Separately state whether the next bounded stage may be **approved-local connectivity/read-only dry integration only**. Static PASS must not authorize Demo order submission or provider retry.
14. If any blocker remains, identify the exact source condition and owner; keep PR #12 `DO NOT MERGE`.
15. Do not modify E1-E6 production code or shared contracts. Do not create a Codex ticket without locally reproduced executable failure.
16. Do not run provider requests, project tests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.

## Acceptance

Task completes when Git contains an exact-revision final re-review that either closes `E4-OKX-MATERIALIZATION-INTEGRITY-001` with all four prior findings still closed and gives a precise merge/next-stage recommendation, or keeps PR #12 blocked with an exact remaining condition.

Executable evidence remains `NOT_RUN`; provider requests remain `NOT_SENT`; provider retry and Demo order submission remain unauthorized; Gate A/B/C/D remain blocked.

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

Persist the final targeted re-review and STATUS, then stop and wait for PM. Do not merge PR #12 or start provider execution automatically.
