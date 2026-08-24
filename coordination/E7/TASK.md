# E7 Current Task

- task_id: `E7-20260824-057`
- issued_at: `2026-08-24T23:29:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-durable-paper-rereview-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B chain through PR #55, PR #57/#58 lifecycle projection contract/producer, PR #60 lifecycle vocabulary, PR #61 E6 durability, PR #62 blocker review, PR #63 execution-lifecycle freshness contract, PR #64 E5 binding producer, PR #65 E6 binding consumer + TradeResult completeness/remediation merge `43eeb2bba236a12d641a30a807eb120990b6e595`

## Objective

Perform only the bounded E7 **static durable Paper Gate B integration re-review** after all source remediations required by E7-052 have been merged.

Determine whether the merged main branch now defines one coherent, fail-closed, deterministic Gate B Paper durability path suitable for a later separately approved local executable verification.

Do not execute project code in this task and do not promote Gate B.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/README.md`, `contracts/SHARED_CONTRACTS_V1.md`;
- protection, close/TradeResult, funding, lifecycle projection/vocabulary, and lifecycle-execution-binding profiles;
- ADR-0005 through ADR-0009;
- accepted E4/E5 Paper in-memory integration surfaces through PR #55;
- E5 lifecycle projection producer and execution-evidence binding producer;
- E6 PR #65 durability/recovery implementation, migrations, tests, and fail-closed remediations;
- E7-052/E7-053 blocker/contract evidence;
- `tests/integration/**`, `tests/e2e/**`, `tests/safety/**` plus relevant E4/E5/E6 deterministic definitions;
- `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md`.

## Required review boundary

Re-review the complete durable graph:

```text
Strategy/Signal
-> TradeIntent
-> RiskDecision
-> ApprovedTradePlan
-> E4 Paper OrderRequest / OrderResult / Fill
-> E5 Position lifecycle projection + execution-evidence binding
-> PositionAction / protection / close / emergency
-> FundingAllocationEvidence
-> TradeResult
-> E6 durable journal / restart recovery / audit
```

Confirm statically at minimum:

1. E4 remains execution/broker truth authority, E5 remains lifecycle/risk interpretation authority, and E6 remains mechanical persistence/recovery only;
2. every restart-authoritative lifecycle projection requires one exact immutable `position-lifecycle-execution-binding-v0.1` companion;
3. the durable current Position-linked execution snapshot is mechanically recomputed using exact PR #63 scope/hash/order rules and stale/new evidence cannot preserve false `READY`;
4. equal-anchor E5 REATTESTATION plus new matching binding can restore only the execution-freshness axis without E6 lifecycle inference;
5. independent raw Position freshness remains fail closed;
6. partial/full protection Fill, canceled/expired/rejected protection truth, POSITION_EXIT, and EMERGENCY_EXIT evidence cannot be hidden across restart;
7. incomplete/conflicting lifecycle revision/predecessor/vocabulary/binding identity fails closed;
8. closed TradeResult durability requires exact complete referenced entry/exit OrderRequest, Fill, PositionAction, funding, parent-plan and Position lineage;
9. legacy/pre-fix invalid durable TradeResult graphs cannot recover `READY`;
10. ordinary EXIT, EMERGENCY_EXIT, and verified full PROTECTION_STOP paths can each close to deterministic TradeResult and recover the exact durable audit graph in the test definitions;
11. funding same-lineage conflicts cannot rewrite an accepted TradeResult;
12. UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED and corrupt/incomplete graphs never become healthy by inference;
13. pre-position `entry-v0.1` remains outside the lifecycle-execution-binding scope and is not heuristically joined by `trade_plan_id`;
14. no provider/private API, credentials, GitHub Actions/CI/compute, strategy promotion, PAPER/SHADOW/LIVE authority, or Gate C scope entered via the merged remediations.

## Required E7 integration/E2E/safety definitions

Update only E7-owned deterministic definitions as necessary under `tests/integration/**`, `tests/e2e/**`, and/or `tests/safety/**` so the future approved-local Gate B matrix uses the real accepted E5/E6 surfaces and covers at least:

- close/reopen with open protected Position + current binding + active/nonterminal order;
- later partial/full protection evidence -> re-interpretation required;
- later canceled/expired/rejected protection truth -> non-READY;
- equal-anchor REATTESTATION + new matching binding -> freshness restored mechanically;
- newer raw Position -> independent re-attestation required;
- ordinary EXIT -> funding -> TradeResult -> close/reopen exact audit;
- EMERGENCY_EXIT equivalent;
- verified full PROTECTION_STOP equivalent;
- missing/mismatched/conflicting binding and lifecycle gap/predecessor/vocabulary conflicts;
- missing/mismatched TradeResult referenced OrderRequest/Fill/PositionAction and legacy generic-invalid graph;
- funding same-lineage conflict + immutable TradeResult;
- incomplete/corrupt/ambiguous graph blocks healthy claims;
- entry-path exclusion;
- no GitHub CI/provider/private call.

Reuse real merged surfaces. Do not create a parallel fake strategy/risk/execution/storage implementation merely to make tests pass.

## Release/status reconciliation

Reconcile E7-owned `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md` to current Git evidence.

Unless a new static blocker is found, the conservative state must be:

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E5 lifecycle execution-binding producer = MATERIALIZED / executable NOT_RUN
E6 durability + binding consumer + TradeResult completeness = MATERIALIZED / executable NOT_RUN
Restart/persistence executable criterion = NOT_RUN
Paper E2E durable audit executable criterion = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No source-level acceptance may become executable PASS.

## Defect / blocker rule

If the re-review finds a reproducible implementation defect under a settled contract, record exact expected-vs-actual evidence and responsible owner/Codex boundary; do not rewrite another domain's production code.

If a new shared semantic/architecture gap remains, stop with `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and exact evidence.

If the source/integration definition is coherent and the only remaining Gate B blocker is approved-local executable evidence, terminal status must explicitly state:

```text
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION
```

while still keeping:

```text
Gate B = BLOCKED / NOT YET PASS
```

## Writable scope

E7-owned only:

- `tests/integration/**`;
- `tests/e2e/**`;
- cross-module `tests/safety/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- E7-specific evidence under `status/e7/**`;
- `coordination/E7/STATUS.md` on the target branch;
- `contracts/**` / `docs/adr/**` only if a genuinely new shared semantic blocker is proven; otherwise do not change them.

Forbidden:

- E1-E6 production/tests;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- strategy promotion or PAPER/SHADOW/LIVE authorization;
- approved-local project execution in this task.

## Executable verification

This task is static integration/release-definition work only.

Record:

```text
project_executable_verification = NOT_RUN
```

Do not run project code/tests and do not request Local Runner execution. Provide exact future local-only commands for the complete Gate B durable matrix. `NOT_RUN != PASS`.

## Acceptance

### DONE

- merged main through PR #65 is statically contract-coherent for the bounded Gate B durable Paper slice;
- no false READY path remains in the reviewed durability graph;
- deterministic E7 integration/E2E/safety definitions cover the real accepted surfaces;
- release/integration status is reconciled without false PASS;
- any remaining criterion requiring execution is explicitly `NOT_RUN` with exact commands;
- if executable evidence is the only remaining blocker, status says `READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION` while Gate B remains BLOCKED;
- no provider/private/CI/Gate C/PAPER/SHADOW/LIVE scope is introduced.

### BLOCKED

- an actual contract/architecture/implementation blocker prevents a coherent durable Paper definition;
- record exact evidence, responsible owner, and bounded next action;
- do not compensate with weakened safety or fake adapters.

## Completion / mailbox rule

Commit/push E7-owned definitions/status evidence to `agent/e7-gate-b-durable-paper-rereview-20260824`.

Write/push terminal `coordination/E7/STATUS.md` with task_id `E7-20260824-057` and stop.

Do not self-start approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, LIVE, or another task.