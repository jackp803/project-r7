# E7 Current Task

- task_id: `E7-20260821-001`
- issued_at: `2026-08-21T00:04:00+08:00`
- state: `ACTIVE`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, ADR-0001, release gates

## Objective

Perform static re-review of the completed E5 and E6 corrections while E4 restarts bounded construction on a fresh PM-created branch.

Do not wait for E4 to finish before reviewing E5/E6. Do not modify E4/E5/E6 domain code.

## Re-review inputs

### E5

- finding: `E5-RISK-UNKNOWN-001`
- reported corrected revision: `cb65c951d59f6fd036bd61691d7e96d025e371c8`
- current coordination status on main: `coordination/E5/STATUS.md`
- handoff: `status/E5_RISK_POSITION_HANDOFF.md`

### E6

- finding: `E6-EVIDENCE-CONTRACT-001`
- reported corrected revision: `4a845ff79ba48abb6122191a2cf8df7d52544475`
- current coordination status on main: `coordination/E6/STATUS.md`
- handoff: `status/E6_EARLY_SLICE2_HANDOFF.md`

### E4

- old `agent/e4-execution` remains historical blocker evidence;
- PM is issuing a fresh implementation branch/task separately;
- this E7 task does not require an E4 disposition beyond recording it as `IN_PROGRESS / NOT_REVIEWED_THIS_TASK`.

## Required actions

1. Re-review E5 corrected source/test definitions and confirm whether `E5-RISK-UNKNOWN-001` is statically resolved:
   - unknown/unsafe required status cannot be made permissive by companion booleans;
   - contradictory status/boolean combinations fail closed;
   - forged/unsafe `APPROVE` cannot become `ApprovedTradePlan`;
   - authority chain remains `TradeIntent -> RiskDecision -> ApprovedTradePlan`;
   - no shared-contract change or PAPER/LIVE expansion.
2. Re-review E6 corrected source/test definitions and confirm whether `E6-EVIDENCE-CONTRACT-001` is statically resolved:
   - all canonical BacktestResult required identity/reproducibility/core metric fields are required before promotable persistence;
   - all canonical ValidationDecision required fields are required;
   - invalid types/enums/bindings fail closed;
   - caller `PASS / LOCAL_EXECUTION` metadata cannot bypass contract-shape validation;
   - E6 does not implement E3 statistical methodology;
   - lifecycle remains capped at CANDIDATE.
3. Check changed-file scope and branch synchronization claims for both corrections.
4. Check for contract collisions, unsafe defaults, scope violations, and GitHub-compute violations.
5. Persist an E7-owned re-review artifact and update `coordination/E7/STATUS.md` with `PASS | FAIL | BLOCKED | NOT_RUN | NOT_APPLICABLE` dispositions and exact responsible owners.
6. Do not advance Gate A/B/C/D. Executable evidence remains `NOT_RUN` unless produced in an approved local environment.
7. If either correction is still defective, provide a bounded owner-specific finding. Do not rewrite domain code and do not create a Codex ticket without local reproduction.

## Acceptance

E7 must produce a repository-persisted static disposition for both findings and explicitly state:

- E5 finding resolved or still blocking;
- E6 finding resolved or still blocking;
- E4 remains outside this re-review and continues under its separate task;
- executable evidence remains `NOT_RUN`;
- release gates remain blocked.

## Writable scope

- E7-owned integration/status/review artifacts
- `coordination/E7/STATUS.md`

## Forbidden scope

- E4/E5/E6 domain implementation edits;
- shared contract changes without procedure;
- PAPER/SHADOW/LIVE enablement;
- GitHub Actions/CI/runner/project compute;
- treating static PASS as executable PASS.

## Completion / status

Persist the re-review, update STATUS, then stop and wait for PM. Do not start another integration task automatically.
