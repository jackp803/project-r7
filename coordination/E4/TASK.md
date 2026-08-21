# E4 Current Task

- task_id: `E4-20260821-008`
- issued_at: `2026-08-21T13:42:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-okx-demo-adapter-20260821`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, `docs/execution/OKX_DEMO_ADAPTER_SCOPE.md`, Product Owner OKX/sub-account decision, E7 finding `E4-OKX-FRESHNESS-HARDEN-001`

## Objective

Construct the next **Demo-first OKX provider adapter source layer** on top of the merged E4 canonical entry translation and deterministic sizing implementation.

This task authorizes bounded source construction for OKX Demo/private request preparation, authentication/signing, prerequisite reads, order request mapping, and reconciliation reads. It does **not** authorize executing provider requests from GitHub, using real credentials, sending Demo orders from this environment, using production trading mode, or advancing PAPER/SHADOW/LIVE.

## Accepted baseline

- PR #11 merged to `main` by PM; merge commit: `9679a224da3764ecbab7161e6c6f256ca46aecf7`
- E7 PR #11 review: `PASS / STATIC ONLY`
- E5 -> E4 boundary: `PASS / STATIC ONLY`
- E4 entry translator: `PASS / STATIC ONLY`
- OKX sizing/metadata safety: `PASS / STATIC ONLY`
- Broker/PaperBroker regression: `PASS / STATIC ONLY`
- executable verification: `NOT_RUN`
- release gates A/B/C/D: `BLOCKED`

## Required actions

1. Work only on `agent/e4-okx-demo-adapter-20260821`, created from current `main`. Preserve merged E4 behavior; do not force-rewrite history.
2. Recheck current official OKX API V5 documentation before provider-specific implementation. Record exact official references used.
3. Implement an E4-owned Demo-only/provider transport boundary that is testable with an injected/fake transport. No project test or provider request may execute on GitHub infrastructure.
4. Implement REST authentication/signature construction for private requests according to current official OKX rules. Secrets must be provided only through runtime injection/configuration; never hard-code, log, serialize, fixture, or commit real credentials.
5. Enforce Demo mode structurally:
   - every authenticated Demo request must include `x-simulated-trading: 1`;
   - an adapter configured for this task must reject production/live mode;
   - do not expose a convenience switch that silently falls back to production trading.
6. Implement provider request materialization only for the existing approved MARKET entry path:
   - canonical symbol `BTC_USDT_PERP` -> `BTC-USDT-SWAP`;
   - `tdMode = isolated`;
   - canonical `BUY/SELL` -> OKX lowercase `buy/sell`;
   - `ordType = market`;
   - provider `sz` must come only from the accepted E4 sizing audit, never from canonical BTC quantity directly;
   - no executable limit/stop/trigger/TIF invention.
7. Implement deterministic provider `clOrdId` mapping from E4 `client_order_id` with stable traceability and current OKX constraints. Current official documentation must be treated as authority; as of task issuance it describes case-sensitive alphanumeric IDs up to 32 characters and uniqueness among pending orders. Do not assume historical uniqueness.
8. Preserve idempotency and ambiguity semantics. A request timeout, connection break, malformed acknowledgement, unknown order acknowledgement, or otherwise ambiguous submit outcome must not permit blind resubmission.
9. Implement/query-model the minimum reconciliation reads needed after ambiguity, at least:
   - `GET /api/v5/trade/order` by `ordId` or `clOrdId`;
   - `GET /api/v5/account/positions` for `BTC-USDT-SWAP`;
   - fills retrieval sufficient to establish actual fills (`GET /api/v5/trade/fills` or current official equivalent);
   - pending-order visibility when needed for reconciliation.
   Provider order/fill/position facts must remain distinct from requested facts.
10. Implement fail-closed provider response parsing/mapping to existing E4 `OrderResult`/Fill/reconciliation semantics. Unknown/unrecognized order state, missing required IDs, inconsistent filled size, or contradictory position/order facts must yield `UNKNOWN`/`RECONCILIATION_REQUIRED` rather than optimistic success.
11. Implement prerequisite validation reads/modeling for the configured Demo account before new exposure. Validate rather than silently repair:
   - Demo environment marker/header;
   - account/position mode facts needed to map `posSide` correctly;
   - isolated trade-mode compatibility;
   - absence of conflicting/unreconciled position/order truth for the current fail-closed flow.
   Do not call `set-position-mode` or `set-leverage` automatically in this task. If exact required account/position mode cannot be safely derived from current authority, make it explicit configuration and fail closed when absent/mismatched.
12. Address `E4-OKX-FRESHNESS-HARDEN-001` before future Demo adapter acceptance:
   - the existing 300-second TTL must not be treated as a provider stability guarantee;
   - sizing/request materialization must require a fresh provider metadata observation at or immediately before the submit preparation boundary;
   - inspect current official scheduled-instrument-change fields such as `upcChg` / `effTime` when present and invalidate/shorten cached metadata when relevant;
   - if current official semantics are insufficient for a safe automated invalidation rule, fail closed/document the limitation rather than inventing one.
13. Keep account configuration mutations outside this bounded task. Account mode is initially set through Web/App per current OKX guidance. Leverage/position-mode setters may be modeled as explicitly forbidden/not-called capabilities, but must not be invoked automatically.
14. Do not add or expose withdrawal, deposit, funding transfer, sub-account capital movement, internal transfer, asset movement, or balance-adjustment capability. Demo balance-adjustment APIs are also outside scope.
15. Do not implement real-money/live execution. Production credentials/endpoints/mode must remain rejected in this bounded adapter.
16. Preserve existing E4/PaperBroker safety behavior and canonical/provider quantity separation. No path may increase provider exposure above the E5-approved BTC upper bound.
17. Add deterministic local-only tests with fake transport covering at minimum:
   - signature/canonical request construction using fake credentials;
   - Demo header always present and production mode rejected;
   - MARKET isolated order payload mapping;
   - provider `sz` sourced from accepted sizing audit only;
   - stable legal `clOrdId` mapping and traceability;
   - account/position-mode prerequisite mismatch fails closed;
   - stale/scheduled-change-risk metadata fails closed or is refreshed before materialization;
   - successful acknowledgement parsing without conflating acknowledgement with fill truth;
   - timeout/ambiguous acknowledgement -> reconciliation-required;
   - query-before-retry using order + position/fill truth;
   - partial fill / filled / canceled / unknown-state mapping;
   - malformed/contradictory provider responses fail closed;
   - no withdrawal/funding/asset-movement surface;
   - no provider quantity exceeds the E5-approved canonical BTC bound.
18. Update E4 docs/handoff and `coordination/E4/STATUS.md` with exact source revision, changed files, official OKX facts, environment guard, account-mode assumptions, reconciliation behavior, freshness-hardening disposition, and verification state.
19. Executable verification is local-only. If no Product Owner-approved local environment is available, record `NOT_RUN` plus exact commands. Do not use GitHub Actions/CI/hosted runners/project compute.

## Allowed endpoint/code surface for this task

Source construction may model/build requests for the minimum Demo execution/reconciliation path, subject to current official docs:

- public instrument metadata required by sizing;
- private account configuration/position reads required to validate prerequisites;
- `POST /api/v5/trade/order` request construction for Demo MARKET entry;
- `GET /api/v5/trade/order`;
- `GET /api/v5/trade/orders-pending` when needed;
- `GET /api/v5/account/positions`;
- `GET /api/v5/trade/fills` or current official equivalent required for fill truth.

Do not broaden this list without reporting a blocker/need in STATUS.

## Acceptance

Static/source acceptance requires:

- Demo-only environment enforcement is fail closed;
- secrets remain runtime-only and absent from Git;
- auth/signing/request serialization are deterministic;
- account/position prerequisites are validated, not silently mutated;
- provider `clOrdId` is legal, deterministic, and traceable to internal idempotency identity;
- metadata freshness hardening finding is addressed for submit preparation;
- ambiguous submit cannot cause blind duplicate order placement;
- reconciliation queries provider order/position/fill truth before retry;
- provider statuses/fills are mapped fail closed;
- canonical BTC quantity remains distinct from provider contract `sz`;
- no withdrawal/funding/asset movement capability;
- no real-money/live execution path is enabled;
- no shared-contract change unless a genuine blocker is reported and work stops;
- executable evidence remains `NOT_RUN` without approved local execution;
- Gate A/B/C/D remain blocked.

## Writable scope

E4-owned paths only:

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
- production/live trading mode;
- actual provider execution from GitHub;
- automatic account-mode/position-mode/leverage mutation;
- withdrawal/deposit/funding/sub-account transfer/balance-adjustment APIs;
- PAPER/SHADOW/LIVE gate advancement;
- GitHub Actions/CI/hosted runner/project compute.

## Completion / status

Persist the bounded Demo-first adapter construction, tests, docs and handoff, update STATUS, then stop. Do not send Demo orders, do not start live execution, and do not begin another feature automatically.
