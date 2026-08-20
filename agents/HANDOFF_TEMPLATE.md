# Agent Handoff Template

Use this template whenever one GPT engineer hands work to another engineer, E7, Project Manager, or Codex.

## Handoff

**From:** E# / role  
**To:** E# / role / E7 / Project Manager / Codex  
**Branch:**  
**Commit(s):**  
**Date:**  

### 1. Objective

State the bounded objective that was worked on.

### 2. What changed

Summarize implemented behavior and important design choices.

### 3. Files changed

List repository paths changed.

### 4. Contracts consumed

List shared contracts/interfaces/schema versions relied on.

### 5. Contracts produced or changed

List outputs or proposed contract changes. If none, state `NONE`.

### 6. Local verification

**GitHub Actions / CI must not be used for this project. All verification is local-only.**

For each test or verification command, record:

- local command;
- local environment/runtime;
- result;
- relevant failure output if not passing.

Example:

```text
Command: pytest tests/strategy -q
Environment: local Windows / Python 3.x
Result: 84 passed
```

If the agent cannot execute the test in its current local environment, write:

```text
Result: NOT_RUN
Required local command: <exact command>
Reason: <why execution was unavailable>
```

Never invent a PASS result and never create a GitHub workflow merely to obtain test evidence.

### 7. Known limitations

State anything intentionally incomplete, simulated, provisional, or not yet validated.

### 8. Dependencies / blockers

Identify external module, contract, local runtime, user decision, exchange permission, or data dependency.

### 9. Required next action

State exactly who should act next and what they should do.

### 10. Security / secrets

Confirm:

- no real API key, API secret, token, credential, password, private key, or live `.env` value was committed;
- test fixtures/logs are sanitized;
- any required real secret remains local-only.

If any exposure occurred, stop and report it as an incident rather than continuing normal handoff.

### 11. GitHub compute policy

Confirm:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no backtest, bug reproduction, unit/integration/E2E test, performance test, or strategy job was executed on GitHub infrastructure.

### 12. Live-trading impact

State whether the change can alter exposure, order placement, position sizing, stop behavior, promotion status, or live enablement.

If yes, identify the relevant E5/E7/Product Owner gate.

### 13. Codex bug ticket, if applicable

For bounded implementation bugs only:

```text
BUG ID:
Expected:
Actual:
Reproduction:
Local failing test / command:
Writable scope:
Forbidden scope:
Architecture/contracts that must remain unchanged:
Required local regression verification:
```

Codex is a bug fixer only; it must not use GitHub CI to reproduce or verify the defect.