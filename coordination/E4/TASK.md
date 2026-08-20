# E4 Current Task

- task_id: `E4-20260820-002`
- issued_at: `2026-08-20T18:36:00+08:00`
- state: `ACTIVE`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, E7 review `status/e7/POST_SLICE1_CONSTRUCTION_SYNC_REVIEW.md`

## Objective

The previously reported E4 Broker/PaperBroker skeleton is not recoverable from repository evidence. This task now explicitly authorizes **new bounded construction** of the minimum E4 execution skeleton from the authoritative role contract and `contracts-v0.1`.

Build only the static/source skeleton needed for later Paper integration. Do not enter private Pionex or LIVE work.

## Required actions

1. Work on `agent/e4-execution` and synchronize it with the latest `main` before implementation. Preserve history; do not force-rewrite branch history. If a safe synchronization cannot be performed with the available Git tooling, report `BLOCKED` rather than inventing a workaround.
2. Implement the minimum E4-owned Broker abstraction and deterministic `PaperBroker` needed to consume an E5 `ApprovedTradePlan` and produce contract-shaped execution evidence.
3. Enforce the authority boundary: E4 accepts execution input only from a valid `ApprovedTradePlan` or an E5-authorized position action. E4 must not invent strategy direction, quantity, leverage, or risk limits.
4. Materialize E4-owned `OrderRequest`, `OrderResult`, and `Fill` handling consistent with `contracts-v0.1`:
   - stable `client_order_id` / idempotency for one logical order;
   - requested quantity and filled quantity remain distinct;
   - partial fills are representable;
   - actual fill facts are not copied from requested values merely for convenience.
5. Implement fail-closed ambiguous acknowledgement semantics:
   - timeout/ambiguous submit result -> `UNKNOWN` or `RECONCILIATION_REQUIRED`;
   - never blindly duplicate-submit after ambiguity;
   - expose an explicit reconciliation/query-before-retry path in the interface/skeleton.
6. Keep broker/exposure truth in E4. Do not implement E5 lifecycle/risk interpretation inside E4.
7. Treat E5's current nested `entry_instruction` / `protection_instruction` shape as provisional. If it is insufficient to implement the bounded PaperBroker path without inventing new shared semantics, report a `CONTRACT MISMATCH` in STATUS/handoff and stop that portion rather than silently stabilizing a new contract.
8. Add deterministic local-only test definitions covering at minimum:
   - ApprovedTradePlan-only authority;
   - stable idempotency identity;
   - partial fill representation;
   - ambiguous acknowledgement -> reconciliation required;
   - query/reconcile before retry;
   - no exposure increase beyond the approved plan.
9. Create/update an E4 -> E7 handoff and `coordination/E4/STATUS.md` with branch, exact HEAD SHA, changed files, limitations, and verification state.
10. Do not run project tests unless a Product Owner-approved local environment exists. Otherwise record `NOT_RUN` plus exact local commands.

## Acceptance

Static/source acceptance requires:

- observable E4 implementation and formal handoff in Git;
- no shared-contract modification;
- no Strategy/Risk decision logic inside E4;
- no private Pionex credentials/API calls/real orders;
- no LIVE/SHADOW enablement;
- ambiguous execution state fails closed;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` if local execution is unavailable.

This task does **not** authorize Gate B/PAPER_READY PASS.

## Writable scope

- `src/execution/**`
- `src/brokers/**`
- `tests/execution/**`
- `tests/brokers/**`
- E4-owned docs/status/handoff paths
- `coordination/E4/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E2/E3/E5/E6 production rewrites;
- production risk-policy decisions;
- Pionex private/live integration;
- credentials/secrets;
- GitHub compute/CI.

## Local verification

If/when an approved local environment is available, report the exact commands defined by the implementation. Prefer stdlib unittest-compatible commands where practical. Until then: `NOT_RUN`.

## Completion / status

When the bounded skeleton and handoff are persisted, update `coordination/E4/STATUS.md` and stop. Do not start private Pionex or another feature automatically.
