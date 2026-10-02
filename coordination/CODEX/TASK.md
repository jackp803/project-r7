# Codex Current Task — R7 Master Productization

- task_id: `CODEX-R7-PRODUCTIZATION-MASTER-20261002`
- issued_at: `2026-10-02`
- state: `ACTIVE`
- supersedes: `CODEX-R7-PRODUCTIZATION-P1-20261002`
- repository: `jackp803/project-r7`
- execution_model: `CONTINUOUS M1 -> M11`
- local_execution: `Product-Owner-approved Windows only`
- GitHub_compute: `FORBIDDEN`

## Authority

Read before implementation:

1. `agents/README.md`
2. `status/PRODUCT_OWNER_CODEX_R7_MASTER_PRODUCTIZATION_AUTHORIZATION_20261002.md`
3. `docs/product/R7_AUTONOMOUS_STRATEGY_TO_CAPITAL_V0_1.md`
4. `docs/product/R7_MASTER_PRODUCT_ARCHITECTURE_V0_1.md`
5. `docs/product/R7_CODEX_MASTER_EXECUTION_PLAN_V0_1.md`
6. `docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md`
7. referenced shared contracts/ADRs/current owner implementations

GitHub `main` at task start is the source of truth.

## Mission

Complete the entire R7 V0.1 product implementation.

The required final product flow is:

```text
Chat-authored Strategy Package
-> Cloud Drive
-> local R7 intake
-> Backtest
-> independent OOS
-> parameter robustness
-> walk-forward
-> Monte Carlo
-> REJECTED or CANDIDATE
-> continuous PAPER
-> READY_FOR_APPROVAL
-> exact Product Owner approval model
-> LIVE-capable runtime
-> execution/protection/reconciliation architecture
-> performance reporting
-> Cloud Drive result feedback
-> usable Control Center
-> packaged Windows product
```

R7 must not require an embedded LLM or paid LLM API.

## Execution instruction

Do not stop after M1.

Execute milestones M1 through M11 from:

`docs/product/R7_CODEX_MASTER_EXECUTION_PLAN_V0_1.md`

in order.

For each milestone:

1. inspect existing implementation before adding code;
2. implement the smallest architecture-conformant surface;
3. add/strengthen tests;
4. run focused tests locally;
5. run relevant regressions locally;
6. fix deterministic defects and rerun until green;
7. establish an exact committed executable checkpoint;
8. persist milestone evidence;
9. if milestone gate PASS, continue automatically to the next milestone.

No PM wake message is required between passing milestones.

## Branch

Create/use:

`codex/r7-productization-master-20261002`

from latest authoritative `main`.

Do not merge `main`.

Do not force push after evidence checkpoints exist.

## Key product architecture

```text
GitHub       = code/contracts/evidence plane
Cloud Drive  = strategy/dataset/result artifact plane
Local R7     = authoritative runtime state and compute
```

Required Cloud transport for V0.1:

`SyncedFolderCloudTransport`

behind:

`CloudArtifactTransport`

Do not hard-code a Google Drive/OneDrive path.

Local active SQLite must be outside the cloud root.

## Existing domain boundary

Do not replace:

```text
E1 market truth
E2 strategy semantics
E3 backtest/validation
E4 broker/execution
E5 risk/position
E6 persistence/registry
E7 contracts/integration/release
```

Application orchestration composes these domains.

## Frontend/product target

Implement a usable local Control Center:

```text
Overview
Research
Strategies
Trading
Health
Settings
```

Recommended stack is Python/FastAPI backend plus React/TypeScript/Vite frontend,
served locally.

Normal product operation must not require Git, PowerShell, PYTHONPATH or manual
JSON inspection.

## Windows product target

Final normal launch:

```text
R7.exe
-> initialize/recover local product
-> start backend/supervisor
-> open Control Center
-> scan Cloud inbox
-> continue configured RESEARCH/PAPER work
```

Research/PAPER operation requires no provider credential.

## LIVE implementation boundary

Complete M9 credential-free LIVE-capable code and fake-provider tests.

Do NOT consume real credentials/provider/private/capital authority.

Real activation is a later Product Owner gate and is not required to finish this
master implementation task.

## Evidence

Persist per milestone:

```text
status/codex/productization/M01_COMPLETION_20261002.md
...
status/codex/productization/M10_COMPLETION_20261002.md
```

and final:

`status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md`

Evidence after a tested executable checkpoint must not rebind that checkpoint.

## Required final acceptance

Use:

`docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md`

as the product Definition of Done.

M11 must exercise at minimum:

- valid strategy -> CANDIDATE;
- weak strategy -> REJECTED;
- malformed strategy -> BLOCKED;
- partial cloud sync -> later exactly-once processing;
- CANDIDATE -> PAPER -> READY_FOR_APPROVAL;
- full PAPER entry/protection/exit/flat TradeResult;
- restart recovery;
- cloud result publication;
- Control Center visibility;
- packaged Windows launch;
- credential-free LIVE path fail-closed.

## Stop conditions

Stop only for the exact classes defined by the master execution plan:

- ARCHITECTURE_REVIEW_REQUIRED
- LOCAL_CAPABILITY_UNAVAILABLE
- EXTERNAL_DEPENDENCY_REQUIRED
- SECURITY_INCIDENT

Provider/credential/capital absence does NOT block completion of credential-free
LIVE-capable implementation.

Do not stop for ordinary failing tests or implementation defects; fix them.

## Final return

Return only after M11 or genuine blocker with:

```text
MASTER_RESULT
branch
final branch HEAD
final qualified executable
M1-M11 results
full test totals
Windows packaging result
product acceptance result
known limitations
real provider requests
LLM API calls
credentials
capital exposure
GitHub compute
```

Then stop for PM final review.

Do not activate real money.
