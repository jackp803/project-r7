# E7 Current Task

- task_id: `E7-20260821-010`
- issued_at: `2026-08-21T14:30:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e4-okx-demo-review-20260821`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision

## Objective

Perform static security/integration review of E4 PR #12, the Demo-first OKX V5 provider-adapter source layer, before any merge or any approved-local Demo connectivity/order test is considered.

This task does **not** authorize provider execution, real credentials, GitHub compute, PAPER/SHADOW/LIVE, or real-money trading.

## Review inputs

- PR: `#12 execution: add Demo-first OKX provider adapter`
- branch: `agent/e4-okx-demo-adapter-20260821`
- E4 implementation/tests/docs/handoff revision: `b7031c52a38623c528ee9352276793d8110854e0`
- E4 task: `E4-20260821-008`
- parent E4 sizing layer merged at `9679a224da3764ecbab7161e6c6f256ca46aecf7`
- executable verification: `NOT_RUN`
- actual Demo/provider requests: `NOT_SENT`

## Required actions

1. Work only on fresh branch `agent/e7-e4-okx-demo-review-20260821` from latest `main`.
2. Review PR #12 changed-file scope. Reject any shared-contract change, E1/E2/E3/E5/E6 production rewrite, GitHub workflow/CI addition, secret/credential material, production/live fallback, account mutation, withdrawal/funding/sub-account transfer, or unrelated feature expansion.
3. Recheck current official OKX API V5 documentation and changelog for every provider-dependent assumption used by E4. At minimum verify:
   - current REST base-domain guidance for global Demo requests;
   - Demo requirement `x-simulated-trading: 1`;
   - REST authentication/signature prehash and timestamp requirements;
   - `clOrdId` legal character/length and uniqueness/query semantics;
   - `tdMode=isolated`, `side`, `posSide`, `ordType=market`, derivative `sz` semantics;
   - `GET /api/v5/account/config`, positions, pending orders, order details, fills;
   - public instrument metadata and scheduled-change fields used by freshness hardening.
   Use official OKX sources rather than community material when available.
4. Review credential/transport security:
   - credentials runtime-injected only;
   - request/repr/log surfaces do not casually expose secret/passphrase/API key;
   - authenticated requests always carry Demo header;
   - production/live configuration or alternate production fallback is impossible in this bounded adapter;
   - private endpoint allowlist contains only TASK-authorized reads/place-order path.
5. Review deterministic request materialization:
   - only accepted E4 MARKET entry path;
   - canonical `BTC_USDT_PERP -> BTC-USDT-SWAP` remains provider-local;
   - `tdMode=isolated`;
   - canonical BUY/SELL mapping is correct;
   - provider `sz` comes only from accepted sizing audit, never directly from canonical BTC quantity;
   - no limit/stop/trigger/TIF invention;
   - effective provider exposure never exceeds the E5-approved canonical BTC bound.
6. Review account/position prerequisites against current official semantics. Specifically classify whether all allowed `expected_account_level` / `expected_position_mode` combinations are valid for the configured isolated BTC-USDT-SWAP flow. Invalid combinations must fail closed before order preparation; explicit configuration must not make an impossible account-mode combination acceptable.
7. Review `clOrdId` mapping and idempotency binding. Confirm provider identity is stable/legal/traceable and that replay/retry cannot submit a materially different order under the same logical id without detection.
8. Perform a dedicated ambiguity/retry safety review. In particular verify that **caller-fabricated or mutated reconciliation evidence cannot authorize retry**. A plain caller-constructible evidence object is not sufficient provenance by itself. Retry authorization must be cryptographically/token-bound, adapter-issued, internally recomputed, or otherwise structurally tied to fresh provider queries and the exact materialization. If forged evidence can cause a second submit, classify as a BLOCKING safety defect owned by E4.
9. Review the exact reconciliation truth set and correlation:
   - order lookup by `clOrdId`/`ordId`;
   - positions for the target instrument;
   - fills correlated to the target order/client id;
   - pending orders correlated to the target client id;
   - requested/order/fill/position facts remain distinct;
   - unknown/contradictory states fail closed.
10. Review E4's `order_not_found_codes` limitation. Determine from current official documentation whether an exact stable order-absence code can be safely canonicalized. If not, keeping retry disabled is acceptable for source merge, but **actual Demo retry must remain blocked** until approved-local integration establishes authoritative absence semantics. Do not invent a code from community examples.
11. Review `E4-OKX-FRESHNESS-HARDEN-001` disposition. Confirm submit preparation requires a sufficiently fresh provider observation and that scheduled instrument changes cannot silently invalidate sizing. Classify the implemented 5-second submit freshness and 60-second change guard as `ACCEPT`, `NON_BLOCKING_HARDENING`, or `BLOCKING`; treat them as E4 safety policy, not provider guarantees.
12. Review response normalization:
   - place-order acknowledgement is not fill truth;
   - partial/filled/canceled/unknown provider states map fail closed;
   - provider contract fill quantity converts back to canonical BTC without overfill;
   - malformed/missing IDs, size contradictions, impossible fill price/state combinations produce `UNKNOWN`/`RECONCILIATION_REQUIRED` or an explicit hard failure, never optimistic success.
13. Review fake-transport deterministic test definitions for all above boundaries, including forged retry evidence/materialization tampering, incompatible account-mode combinations, secret-redaction surfaces, stale/scheduled-change metadata, and quantity upper-bound preservation. Do not execute tests in GitHub.
14. Persist an E7-owned review artifact and update `coordination/E7/STATUS.md` with separate dispositions:
   - Demo environment/auth security: `PASS | FAIL | BLOCKED`;
   - request/materialization/account prerequisites: `PASS | FAIL | BLOCKED`;
   - freshness hardening: `PASS | FAIL | BLOCKED`;
   - ambiguity/reconciliation/retry safety: `PASS | FAIL | BLOCKED`;
   - provider response normalization: `PASS | FAIL | BLOCKED`;
   - Broker/PaperBroker regression/static compatibility: `PASS | FAIL | BLOCKED`;
   - PR #12 merge recommendation;
   - exact findings/owners;
   - executable disposition `NOT_RUN`;
   - Gate A/B/C/D unchanged.
15. If static review passes, explicitly state whether PM may merge PR #12 and whether the **next separate stage may be an approved-local OKX Demo connectivity/dry integration test**. This must not be phrased as Demo order authorization unless all remaining absence/retry/account prerequisites are resolved and Product Owner explicitly authorizes such execution later.
16. Do not modify E1-E6 production code or shared contracts. Do not create a Codex bug ticket without locally reproduced executable failure.
17. Do not use GitHub Actions/CI/hosted runner/project compute and do not convert static PASS into executable PASS.

## Acceptance

Task is complete when Git contains a precise static security/integration review of PR #12, including explicit provenance/tamper review of retry evidence, official-provider fact recheck, merge recommendation, remaining prerequisites for approved-local Demo testing, and `NOT_RUN` executable evidence.

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
- PAPER/SHADOW/LIVE gate advancement;
- GitHub compute/CI.

## Completion / status

Persist the review and STATUS, then stop and wait for PM. Do not merge PR #12 and do not start provider execution automatically.
