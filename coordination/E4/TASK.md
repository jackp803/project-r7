# E4 Current Task

- task_id: `E4-20260821-012`
- issued_at: `2026-08-21T16:19:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-okx-demo-adapter-20260821`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, E7 targeted re-review `status/e7/E4_OKX_DEMO_TARGETED_REREVIEW_20260821.md`

## Objective

Close the **single remaining** E7 blocker in PR #12: `E4-OKX-MATERIALIZATION-INTEGRITY-001` at the actual provider submit boundary.

Four prior findings are already statically closed by E7 and must not be reopened or redesigned:

- `E4-OKX-ACCOUNT-MATRIX-001` — CLOSED / PASS STATIC
- `E4-OKX-RETRY-PROVENANCE-001` — CLOSED / PASS STATIC
- `E4-OKX-ORDER-ABSENCE-001` — CLOSED / PASS STATIC
- `E4-OKX-ORDER-STATE-CONSISTENCY-001` — CLOSED / PASS STATIC

This is a source/test correction task only. It does **not** authorize provider execution, real credentials, concrete networking, Demo order submission, provider retry, production/live mode, account mutation, asset movement, PAPER/SHADOW/LIVE, or any release-gate advancement.

## Reviewed baseline

- PR: `#12 execution: add Demo-first OKX provider adapter`
- corrected implementation previously reviewed: `651541ba0da646f0c2ab69117219e2c8ca21247c`
- prior PR head: `c151fa7c37adafbf9f93157d80cf4b763dd775e2`
- E7 targeted re-review persisted on `main` via PR #14
- executable verification: `NOT_RUN`
- actual provider requests/orders: `NOT_SENT`
- provider retry: `STRUCTURALLY DISABLED`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Remaining blocker

### `E4-OKX-MATERIALIZATION-INTEGRITY-001`

E7 confirmed that `materialize_demo_market_order()` now correctly recomputes sizing from the exact current `OrderRequest` plus submit-validated metadata and treats caller sizing evidence as evidence-only.

The remaining bypass is after preparation:

- `OKXOrderMaterialization` is caller-constructible;
- its `body` mapping can be mutated after `prepare_entry()`;
- `submit_entry()` currently signs/sends caller-supplied `materialization.body` directly;
- therefore post-prepare tampering of `sz`, `instId`, `side`, `posSide`, `ordType`, or `clOrdId`, or direct construction of a materialization, can bypass the preparation authority unless submit independently proves provenance/integrity.

## Required correction

1. Non-destructively synchronize the existing PR #12 branch with latest `main` before source correction. Preserve history; no force update/destructive rebase.
2. Make the **submit boundary independently enforce adapter-issued preparation authority**. The final request signed/sent by `submit_entry()` must not trust a caller-mutable `body` or an unproven caller-constructed materialization.
3. Use one bounded fail-closed design, for example:
   - adapter-owned issued-materialization registry/fingerprint with exact semantic binding and submit-time body re-derivation; or
   - submit-time re-derivation/revalidation from adapter-owned canonical prepared facts; or
   - another equally strong design that E7 can statically prove prevents direct-construction and post-prepare tamper bypass.
4. Whatever design is chosen, `submit_entry()` must prove that the submitted request is bound to the exact preparation facts, including at minimum:
   - `order_request_id`;
   - `trade_plan_id`;
   - internal `client_order_id`;
   - provider `clOrdId`;
   - provider instrument;
   - provider side;
   - provider position side;
   - `ordType=market`;
   - provider contract quantity;
   - effective canonical quantity;
   - E5-approved canonical quantity;
   - instrument metadata reference and observation;
   - current accepted Demo/account/freshness preparation context.
5. The actual signed provider request body must be **derived afresh from trusted immutable/adapter-owned facts or proven exact against them**. A mutable caller mapping must never be execution authority.
6. Direct caller construction of `OKXOrderMaterialization` without an adapter-issued preparation must fail closed before any transport send.
7. Cross-materialization substitution or materially changed content under the same logical/client identity must fail closed before any transport send.
8. Preserve the invariant:

```text
0 < provider effective canonical BTC <= E5-approved OrderRequest.quantity
```

and preserve canonical BTC quantity as distinct from OKX provider `sz`.
9. Preserve all already accepted boundaries without redesign:
   - Demo-only mode and mandatory `x-simulated-trading: 1`;
   - runtime-only/redacted credentials;
   - bounded private endpoint allowlist;
   - V1 account matrix `acctLv=2`, `net_mode | long_short_mode`, `tdMode=isolated`;
   - MARKET-only path;
   - freshness policy `okx-instrument-metadata-freshness-v0.2`;
   - provider retry structurally disabled;
   - no caller-configurable order-absence authority;
   - state/fill consistency checks;
   - no production/live fallback;
   - no account/position/leverage mutation;
   - no withdrawal/deposit/funding/internal/sub-account transfer/balance-adjustment surface;
   - Broker/PaperBroker source behavior unchanged.
10. Add deterministic local-only tests proving at minimum:
   - mutate `body["sz"]` after `prepare_entry()` -> rejected before transport;
   - mutate `instId` -> rejected before transport;
   - mutate `side` -> rejected before transport;
   - mutate `posSide` -> rejected before transport;
   - mutate `ordType` -> rejected before transport;
   - mutate `clOrdId` -> rejected before transport;
   - direct caller-constructed materialization -> rejected before transport;
   - cross-materialization/replayed preparation cannot submit materially different facts;
   - valid adapter-issued preparation still produces the exact expected Demo MARKET isolated request;
   - no provider quantity can exceed the E5-approved canonical BTC upper bound.
11. Do not broaden endpoint scope, add a concrete transport, or implement any actual provider connectivity.
12. Do not edit `contracts/**` or E1/E2/E3/E5/E6 production code.
13. Update E4 docs/handoff and `coordination/E4/STATUS.md` with the exact correction design, revised source/tests/docs revision, branch synchronization evidence, and `NOT_RUN` verification state.
14. Executable verification remains local-only. Without a Product Owner-approved local environment, record `NOT_RUN` plus exact commands. Do not use GitHub Actions/CI/hosted/project compute.
15. Push only the bounded correction to the existing PR #12 branch, then stop. Do not merge PR #12 and do not start Demo connectivity/order execution.

## Acceptance

Static/source completion requires the provider submit boundary to reject all caller-constructed/tampered materialization paths before transport and to derive/prove the exact signed provider request from adapter-issued trusted facts. The four already-closed findings must remain closed. PR #12 remains pending E7 re-review; executable evidence remains `NOT_RUN`; provider execution remains unauthorized.

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
- actual provider requests/orders;
- concrete network transport;
- production/live mode;
- provider retry enablement;
- arbitrary order-absence authority;
- automatic account/position/leverage mutation;
- asset-movement APIs;
- PAPER/SHADOW/LIVE advancement;
- GitHub Actions/CI/hosted runner/project compute.

## Completion / status

Close only `E4-OKX-MATERIALIZATION-INTEGRITY-001`, update STATUS/handoff, push to PR #12 branch, then stop and wait for PM/E7 re-review.