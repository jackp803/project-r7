# E7 Current Task

- task_id: `E7-20260824-026`
- issued_at: `2026-08-24T09:43:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-static-preflight-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A evidence review PR #33, `status/RELEASE_GATES.md`

## Objective

Propagate the accepted bounded Gate A decision into authoritative release-gate status and perform a **static-only Gate B / PAPER_READY preflight** against the latest `main`.

This task is not Paper execution and not Gate B executable verification. Do not run project code. Do not authorize PAPER, SHADOW, LIVE, provider/private API work, exchange credentials, or capital exposure.

## Accepted prerequisite

Gate A has been technically accepted for Research / Integration only:

```text
GATE_A = PASS
```

Accepted evidence:

```text
Gate A execution evidence PR #32
merge = 154b3164ce579672d601a23bbc17a485f3ebcbb1
execution branch head = 633261d58a4c86d7b6d760e23660b48c471bcc31
approved source revision = 4da559bbbb569ea4f32246a40ef35f4bd8477a71
127 local tests / zero failure or error

Gate A evidence review PR #33
merge = 429e8961dc4c32996e12fa7258c734571ea7d823
review branch head = e18f35b9513a4912390ed9920e98e9572be88cc7
review disposition = GATE_A = PASS / RESEARCH-INTEGRATION ONLY
```

Do not reinterpret this PASS as PAPER/LIVE authorization.

## Required work

### 1. Reconcile authoritative release-gate state

Read latest `status/RELEASE_GATES.md`, `status/INTEGRATION_STATUS.md`, the merged Gate A execution/review artifacts, and relevant role handoffs.

Update `status/RELEASE_GATES.md` so the Gate A section no longer says `BLOCKED` as the current disposition. Preserve the historical criteria text where useful, but record the accepted current Gate A decision with exact evidence references.

Do not silently convert unrelated Gate B/C/D criteria to PASS.

### 2. Gate B static preflight

Evaluate every current `Gate B — PAPER_READY` criterion in `status/RELEASE_GATES.md` against repository evidence on latest `main`.

At minimum inspect actual implementation/contracts/tests/handoffs for:

- `TradeIntent -> E5 RiskDecision` boundary;
- E5 rejection authority;
- `ApprovedTradePlan` as the only E4 strategy-originated execution input;
- E4 `PaperBroker` implementation and contract conformance;
- partial-fill quantity semantics;
- protection quantity following actual fill;
- protection-failure emergency behavior;
- stale/unknown market state exposure veto;
- unknown order/position state exposure veto;
- drawdown / daily / position / kill-switch enforcement;
- persistence/restart requirements across E5/E6;
- Paper E2E closure to `TradeResult` plus durable audit/persistence;
- GitHub compute prohibition.

Do not infer implementation from role descriptions. Inspect the actual repository code/tests/contracts/handoffs.

### 3. Classify every Gate B criterion

For each criterion, assign one evidence-preserving disposition such as:

```text
STATIC_READY_LOCAL_EXEC_REQUIRED
IMPLEMENTATION_GAP
INTEGRATION_TEST_DEFINITION_GAP
CONTRACT_OR_SEMANTIC_GAP
EVIDENCE_GAP
ALREADY_SATISFIED_STATICALLY
```

These are preflight classifications, not replacements for canonical `PASS/FAIL/BLOCKED/NOT_RUN` release evidence. Where executable proof is required and has not run, canonical release status remains `NOT_RUN` or `BLOCKED` as appropriate.

Identify the responsible owner for each genuine gap: E1, E2, E4, E5, E6, E7, or Codex only if an approved-design implementation defect is already reproducible.

### 4. Determine the next dependency sequence

Produce a minimal dependency-ordered Gate B plan. Separate:

- implementation work that must exist before testing;
- E7-owned integration/safety/E2E test definitions that are missing;
- local-only executable suites that can already be run once explicitly approved;
- blockers that require domain-owner work first.

Do not issue tasks to other agents yourself. PM remains the tasking authority.

### 5. Provider naming / scope drift check

The repository may contain historical provider naming in governance/release text while current execution work uses newer provider-specific adapters elsewhere. For this Gate B preflight, do not broaden into Gate C/private-provider implementation.

If provider naming is stale or inconsistent but does not affect Paper-only Gate B semantics, record it as documentation/governance drift for later E7/PM cleanup rather than rewriting unrelated Gate C scope in this task.

## No executable verification

For this task:

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC PREFLIGHT
```

Do not run unit tests, integration tests, E2E tests, backtests, migrations, provider calls, Local Runner actions, PaperBroker runtime, or any project command.

Do not treat this task's `NOT_RUN` as a failure of the already accepted Gate A evidence.

## Required outputs

Persist:

- updated `status/RELEASE_GATES.md` with accepted Gate A current state;
- `status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md` containing the criterion-by-criterion Gate B audit, actual evidence paths, owner/gap classification, and dependency-ordered next actions;
- update `status/INTEGRATION_STATUS.md` only if needed to reflect Gate A PASS / Gate B preflight state;
- update `coordination/E7/STATUS.md`.

## Allowed terminal dispositions

E7 must report one of:

```text
GATE_B_STATIC_PREFLIGHT = READY_FOR_BOUNDED_NEXT_TASKS
```

or

```text
GATE_B_STATIC_PREFLIGHT = BLOCKED_BY_UNRESOLVED_ARCHITECTURE_OR_CONTRACT
```

`READY_FOR_BOUNDED_NEXT_TASKS` does **not** mean Gate B PASS and does not authorize Paper execution. It only means PM has enough evidence to issue the next bounded implementation/test-definition/local-verification task(s).

## Safety / downstream state

Throughout this task:

- Gate A = PASS / RESEARCH-INTEGRATION ONLY;
- Gate B = not yet PASS;
- Gate C = BLOCKED / UNCHANGED;
- Gate D = BLOCKED / UNCHANGED;
- PAPER = UNAUTHORIZED unless a later Product Owner/PM task explicitly authorizes a controlled local Paper verification step;
- SHADOW / LIVE = UNAUTHORIZED;
- provider/private API = NOT AUTHORIZED;
- exchange credentials = NOT USED;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute = FORBIDDEN.

## Writable scope

E7-owned documentation/status only:

- `status/RELEASE_GATES.md`;
- `status/INTEGRATION_STATUS.md` if needed;
- `status/e7/**`;
- `coordination/E7/STATUS.md`.

Do not modify E1-E6 production/tests, shared contracts, integration test code, provider code, lifecycle semantics, strategy definitions, or AgentBridge in this task.

## Completion

Commit/push the static-preflight evidence to `agent/e7-gate-b-static-preflight-20260824`, update E7 STATUS, and stop. Do not start implementation, executable Gate B verification, provider work, PAPER, SHADOW, LIVE, or another task automatically.