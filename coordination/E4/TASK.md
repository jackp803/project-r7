# E4 Current Task

- task_id: `E4-20260821-001`
- issued_at: `2026-08-21T00:04:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-execution-v2`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, E7 review `status/e7/POST_SLICE1_CONSTRUCTION_SYNC_REVIEW.md`

## Objective

Unblock E4 by abandoning the status-only diverged branch as an implementation base. Build the minimum bounded E4 execution/PaperBroker skeleton on a fresh PM-created branch from current `main`.

The old `agent/e4-execution` branch is retained as historical blocker evidence only. Do not force-update or delete it.

## Required actions

1. Work only on `agent/e4-execution-v2`, which PM creates from current `main` after issuing this task. Do not merge/rebase the old `agent/e4-execution` branch into it.
2. Implement the minimum E4-owned Broker abstraction and deterministic `PaperBroker` needed to consume an E5 `ApprovedTradePlan` and produce contract-shaped execution evidence.
3. Enforce the authority boundary: E4 accepts strategy-originated execution input only from a valid `ApprovedTradePlan`; E4 must not invent direction, quantity, leverage, margin mode, stop/target loosenings, or risk approval.
4. Implement E4-owned `OrderRequest`, `OrderResult`, and `Fill` handling consistent with `contracts-v0.1`, including:
   - stable `client_order_id` / idempotency identity per logical order;
   - requested quantity distinct from filled quantity;
   - partial fills;
   - actual fill facts distinct from requested values.
5. Ambiguous acknowledgement must fail closed:
   - timeout/ambiguous submit -> `UNKNOWN` or `RECONCILIATION_REQUIRED`;
   - no blind duplicate submission;
   - explicit query/reconcile-before-retry path.
6. Keep broker/order/fill/exposure truth in E4. Do not implement E5 lifecycle/risk interpretation.
7. Treat E5 `entry_instruction` / `protection_instruction` nesting as provisional. If the bounded PaperBroker cannot consume it without inventing shared semantics, report `CONTRACT MISMATCH` and stop that portion.
8. Add local-only deterministic test definitions covering at minimum:
   - ApprovedTradePlan-only authority;
   - stable idempotency;
   - partial fills;
   - ambiguous acknowledgement -> reconciliation;
   - reconcile/query before retry;
   - no exposure increase beyond approved plan.
9. Create an E4 -> E7 handoff and update `coordination/E4/STATUS.md` with exact branch HEAD, changed files, limitations, contract findings, and verification state.
10. No project tests unless a Product Owner-approved local environment exists. Otherwise `NOT_RUN` + exact local commands.

## Acceptance

- implementation and handoff are observable on `agent/e4-execution-v2`;
- old status-only branch remains untouched;
- no shared-contract modification;
- no Strategy/Risk decision logic in E4;
- no private Pionex API, credentials, real orders, SHADOW, or LIVE;
- ambiguous execution state fails closed;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` if local execution is unavailable.

This task does not authorize Gate B/PAPER_READY PASS.

## Writable scope

- `src/execution/**`
- `src/brokers/**`
- `tests/execution/**`
- `tests/brokers/**`
- E4-owned docs/status/handoff
- `coordination/E4/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E2/E3/E5/E6 production rewrites;
- production risk-policy decisions;
- Pionex private/live integration;
- credentials/secrets;
- GitHub compute/CI.

## Completion / status

Persist the bounded skeleton and handoff, update STATUS, then stop. Do not start private Pionex or another feature automatically.
