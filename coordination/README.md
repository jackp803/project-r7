# Agent Coordination Mailbox Protocol

This directory is the Git-based coordination channel between the Project Manager (PM) and E1-E7.

## Goal

The Product Owner should not need to copy long prompts or handoff reports between seven ChatGPT conversations.

The normal loop is:

```text
PM writes/updates coordination/E?/TASK.md
        ↓
Product Owner tells that chat: "Read your TASK.md and execute it."
        ↓
Agent reads TASK.md from GitHub
        ↓
Agent performs only that task within its authority/scope
        ↓
Agent updates coordination/E?/STATUS.md
        ↓
PM reads STATUS.md + repository evidence
        ↓
PM reviews and, when appropriate, replaces TASK.md with the next task
```

Git history preserves prior TASK/STATUS revisions, so the current files may be replaced each cycle without losing audit history.

## Ownership

- `coordination/E1/TASK.md` ... `coordination/E7/TASK.md`: PM-owned command files. Domain agents MUST NOT rewrite their TASK file.
- `coordination/E1/STATUS.md` ... `coordination/E7/STATUS.md`: agent-owned status files. PM may read/review them but normally does not rewrite the agent's status report.
- Agent domain code remains owned by the corresponding role contract in `agents/`.
- Shared contracts remain governed by E7 and `contracts/`.

## Mandatory Task Header

Every TASK.md must contain:

- `task_id`
- `issued_at`
- `state: ACTIVE | HOLD | WAITING`
- authoritative baselines / required revisions
- objective
- required actions
- acceptance criteria
- writable scope
- forbidden scope
- local verification requirements
- handoff/status requirements

If any required instruction conflicts with `agents/README.md`, the role contract, canonical contracts, ADRs, or release gates, the agent must STOP and report `BLOCKED` in STATUS.md instead of guessing.

## Mandatory Status Header

Every STATUS.md must contain:

- `task_id`
- `agent`
- `state: DONE | PARTIAL | BLOCKED | NOT_STARTED`
- `branch`
- `head_sha`
- `summary`
- `files_changed`
- `contracts_changed`
- `local_verification`
- `not_run`
- `blockers`
- `handoff_path`
- `next_owner`

A chat message saying "done" is not completion evidence unless the status and relevant code/docs are committed to GitHub.

## Completion Rule

An agent may mark its own task `DONE`, but it may not promote a release gate unless its authority explicitly allows that decision.

`DONE` means only that the agent believes the current TASK.md acceptance criteria are satisfied and has persisted evidence for review.

Executable evidence remains subject to the project local-only execution policy:

```text
NOT_RUN != PASS
```

GitHub Actions, hosted runners, GitHub-triggered runners, scheduled GitHub compute, and GitHub-hosted project tests/backtests remain forbidden.

## Task Replacement Rule

The PM may replace TASK.md only after reviewing the current STATUS.md and repository evidence, or when explicitly cancelling/superseding a task.

Each replacement must use a new `task_id`.

Recommended ID format:

```text
E6-20260820-002
E7-20260820-004
```

The previous task remains recoverable through Git history.

## Product Owner Interaction

After this protocol is on `main`, the Product Owner normally only needs to send one short instruction to a role chat:

```text
讀取 main 上 coordination/E6/TASK.md，依照內容執行。完成後更新 coordination/E6/STATUS.md 並 commit/push。
```

For E7, replace `E6` with `E7`, etc.

The PM can then reconstruct project state directly from GitHub without requiring the Product Owner to copy the full agent response between chats.

## Optional Local Chat Dispatch Extension

`tools/chat-dispatcher/` can automate only the wake-up step above from the Product Owner's Windows machine.

```text
GitHub TASK change
    ↓
local dispatcher
    ↓
registered agent ChatGPT conversation
    ↓
agent reads TASK.md itself
```

When the agent later writes a terminal `STATUS.md`, the same local dispatcher can wake the PM conversation for review.

This extension does **not** change authority or verification semantics:

- GitHub TASK/STATUS and repository evidence remain authoritative;
- a dispatched ChatGPT message is not completion evidence;
- the dispatcher does not perform project tests/backtests;
- it does not create or use GitHub Actions/CI/hosted runners/GitHub-triggered project compute;
- executable verification remains local-only and governed by the TASK and project policy;
- the dispatcher is portable and may monitor other projects through its local `config.json` without changing this R7 protocol.
