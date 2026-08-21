# E7 Current Task

- task_id: `E7-20260822-003`
- issued_at: `2026-08-22T03:01:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e6-registry-review-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003

## Objective

Perform a fresh exact-revision static/integration review of PR #16, the synchronized early Slice 2 E6 Strategy Registry / evidence-ingest / SQLite persistence skeleton, and decide whether PM may merge it into current `main`.

This task is static/source review only. It does **not** authorize project execution, provider calls, lifecycle expansion, PAPER/SHADOW/LIVE, or GitHub compute.

## Review inputs

- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- E6 branch: `agent/e6-platform`
- accepted E6 correction baseline: `4a845ff79ba48abb6122191a2cf8df7d52544475`
- synchronized source/tests/docs/platform-status revision: `207f6f87dd984c9dea5e4360e2f605e2c94b2bcf`
- observed PR head at PM audit: `df15109dcb8594b1182bf6fc09cb5ad6681d74b5`
- implementation-pin -> PR-head delta: `coordination/E6/STATUS.md` only
- E6 synchronization merge: `e3ad9b28ee819fa99aa3933c146e9e9fe02151e2`
- then-current main merged by E6: `bac41e860b5582f7a87d8992c803ce081dafcb35`
- executable verification: `NOT_RUN`

## Required review

1. Work only on `agent/e7-e6-registry-review-20260822` created from latest `main`.
2. Review actual PR #16 source/tests/docs; do not rely only on E6 STATUS claims.
3. Verify synchronization/integration scope:
   - PR branch history is non-destructive;
   - no force rewrite/destructive rebase evidence;
   - changed files are limited to E6-owned registry/storage/tests/docs/status;
   - no `contracts/**`, E1/E2/E3/E4/E5 production, `.github/workflows`, secret, or unrelated feature changes.
4. Recheck `E6-EVIDENCE-CONTRACT-001` against the accepted baseline. At minimum verify:
   - incomplete/incompatible BacktestResult fails before persistence;
   - all canonical identity/reproducibility/core metric fields required by current contracts are validated;
   - ValidationDecision requires canonical fields, exact decision enum, reason-code structure, and exact strategy/backtest binding;
   - invalid/unknown required enum/type/state fails closed;
   - caller-supplied `PASS` / `LOCAL_EXECUTION` metadata cannot bypass canonical evidence validation;
   - BacktestResult alone cannot authorize CANDIDATE without valid bound ValidationDecision evidence.
5. Compare key accepted implementation blobs/behavior to baseline `4a845ff...`. E6 reports the accepted blobs remain unchanged, including:
   - `src/registry/contract_validation.py` blob `954d21c021c0885554ee650acced17610d958a0e`;
   - `src/registry/service_base.py` blob `3889ac156358f58c5fc3380865ad73844b874c3c`;
   - verify other critical registry gate behavior has not regressed.
6. Verify lifecycle authority remains strictly capped to:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

   Confirm models, service transitions, persistence constraints, and migration do not expose PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED, or generic lifecycle transition authority.
7. Verify persistence/inbox safety remains coherent:
   - immutable strategy identity/version/content semantics;
   - append-only lifecycle audit behavior;
   - duplicate/idempotent intake versus conflicting identity fails closed;
   - default/unwired compatibility boundary does not manufacture executable PASS;
   - SQLite is an E6 implementation detail, not a shared-contract semantic change.
8. Verify this PR does **not** prematurely persist ApprovedTradePlan, OrderRequest, OrderResult, Fill, provider-native OKX `sz`, execution reconciliation, Demo execution facts, or other Slice 3 execution-audit surface.
9. Verify provider contract quantity is not reinterpreted as canonical BTC quantity.
10. Review deterministic test definitions for registry evidence validation, strategy inbox, lifecycle gating, and SQLite persistence. Do not execute tests in GitHub.
11. Treat any `PASS` fixture in tests as synthetic test input only; it must not be represented as project executable evidence.
12. Recheck repository synchronization against current `main` at review time. Coordination-only TASK commits issued after E6's implementation pin are not by themselves a reason to bounce E6 through another sync cycle. Require resynchronization only if there is meaningful production/shared-contract drift or an actual merge conflict affecting reviewed behavior.
13. Persist an E7 review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed E6 revision and observed PR head;
   - `E6-EVIDENCE-CONTRACT-001` disposition;
   - lifecycle/persistence/inbox/scope dispositions;
   - PR #16 merge recommendation;
   - executable verification `NOT_RUN`;
   - Gate A/B/C/D unchanged.
14. If static review passes and scope is coherent, state `PM MAY MERGE PR #16`. Do not treat that as Gate A PASS or as authorization for PAPER/APPROVED/SHADOW/LIVE.
15. If blocked, identify exact source condition and owner. Do not modify E6 implementation yourself.
16. Do not run project tests, migrations, GitHub Actions/CI/hosted runners, backtests, or provider requests. Do not create a Codex ticket without a locally reproduced executable defect.

## Acceptance

Task completes when Git contains an exact-revision E7 static review that either recommends PM merge PR #16 or keeps it blocked with a precise source/integration finding. Executable evidence remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- provider execution;
- lifecycle expansion;
- PAPER/SHADOW/LIVE advancement;
- GitHub compute/CI.

## Completion / status

Persist the review and STATUS, then stop and wait for PM. Do not merge PR #16 or start another task automatically.
