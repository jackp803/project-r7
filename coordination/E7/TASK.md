# E7 Current Task

- task_id: `E7-20260820-001`
- issued_at: `2026-08-20T16:53:00+08:00`
- state: `ACTIVE`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, ADR-0001, release gates

## Objective

Establish a repository synchronization checkpoint for the post-Slice-1 construction line by reviewing E4/E5/E6 evidence and persisting the integration result in GitHub.

## Required actions

1. Read `coordination/E4/STATUS.md`, `coordination/E5/STATUS.md`, and `coordination/E6/STATUS.md` after those agents update them.
2. If E4 branch/handoff is still missing, mark the E4 portion `BLOCKED` and do not reconstruct its work from chat memory.
3. Statically review E5 Risk/Position skeleton against `contracts-v0.1`, especially:
   - `TradeIntent -> RiskDecision -> ApprovedTradePlan` authority;
   - fail-closed unknown/reconciliation behavior;
   - provisional entry/protection instruction shape not becoming a silent shared contract;
   - no PAPER/LIVE authority.
4. Statically review E6 early Slice 2 skeleton, especially:
   - no shared-semantic redefinition;
   - default E2 compatibility remains fail-closed `NOT_RUN`;
   - BacktestResult shape alone cannot promote lifecycle;
   - `CANDIDATE` requires explicit valid E3 decision/evidence;
   - no lifecycle path beyond CANDIDATE.
5. If E4 evidence is present, statically review Broker/PaperBroker / Order-Fill-reconciliation skeleton and the E4<->E5 boundary.
6. Check for shared-contract collisions, scope violations, unsafe defaults, fail-open behavior, approval bypass, and GitHub-compute violations.
7. Persist the review in E7-owned status/review paths and update `coordination/E7/STATUS.md`.
8. Keep all executable evidence as `NOT_RUN` unless produced in an approved local environment.

## Acceptance

E7 must provide a repository-persisted disposition for E4/E5/E6 using `PASS | FAIL | BLOCKED | NOT_RUN | NOT_APPLICABLE`, identify responsible owner for every blocker/finding, and must not advance Gate A/B/C/D without required executable evidence.

## Writable scope

E7-owned integration/status/review paths plus `coordination/E7/STATUS.md`.

## Forbidden scope

- rewriting E4/E5/E6 domain implementations;
- changing shared contracts without contract-change procedure;
- enabling PAPER/SHADOW/LIVE;
- GitHub Actions/CI/runner/project compute;
- treating `NOT_RUN` as PASS.

## Completion / status

When complete, update `coordination/E7/STATUS.md` with review artifact paths, findings, blockers, current release gates, and next-owner recommendations. Then wait for PM review before taking the next task.
