# Portable Chat Dispatch Layer

This directory contains a Windows-local dispatcher that bridges Git-based agent mailboxes to existing ChatGPT conversations.

It is deliberately project-agnostic. One dispatcher process can monitor multiple repositories and multiple agent chats.

## Problem it solves

ChatGPT Projects can share context between chats, but there is no supported API for one existing ChatGPT chat to call another existing chat directly. The dispatcher therefore uses Git as the authoritative coordination plane and the local Windows machine only as a wake-up transport.

```text
PM chat
  -> writes coordination/<agent>/TASK.md
  -> GitHub/main
  -> local dispatcher notices new task_id/state
  -> opens the registered agent chat
  -> sends the standard wake prompt
  -> agent reads TASK.md from GitHub and works
  -> agent updates STATUS.md and pushes
  -> local dispatcher notices terminal status
  -> wakes the PM chat
  -> PM reviews evidence and decides the next TASK
```

The dispatcher never treats ChatGPT UI text as project evidence. It does not scrape or parse ChatGPT output. Git TASK/STATUS files and repository evidence remain authoritative.

## Portability

`config.json` contains all project-specific information:

- local repository path
- Git remote and branch
- coordination root
- PM chat URL
- agent IDs and chat URLs
- task states that should trigger dispatch
- terminal status states
- optional project-specific prompt suffix

To add a new project, add one object to the `projects` array. No dispatcher code change is required.

The only mailbox convention assumed by the current adapter is:

```text
<coordination_root>/<agent_id>/TASK.md
<coordination_root>/<agent_id>/STATUS.md
```

## Requirements

- Windows
- PowerShell 5.1 or later
- Git available on PATH
- each monitored repository already cloned locally
- the configured Git remote can fetch the selected branch
- the default browser is already signed in to ChatGPT
- each target conversation URL is recorded once in `config.json`

No GitHub Actions, hosted runner, OpenAI API, or local LLM is required.

## Setup

1. Copy `config.example.json` to `config.json`.
2. Replace every `repo_path` and `chat_url` placeholder.
3. Start in safe mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\dispatcher.ps1 -ConfigPath .\config.json
```

The default `prepare_only` mode opens the correct chat and copies the wake prompt to the clipboard, but does not press Enter.

4. Test one cycle with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\dispatcher.ps1 -ConfigPath .\config.json -Once
```

5. When the routing is proven correct, optional zero-click UI dispatch can be enabled:

```json
{
  "dispatch_mode": "auto_send",
  "allow_unsafe_ui_automation": true
}
```

`auto_send` uses foreground Windows keystroke automation after opening the registered ChatGPT URL. It is not an official ChatGPT chat-to-chat API and can fail if focus is stolen, the browser/UI behavior changes, or the page has not finished loading. Keep `prepare_only` as the recovery mode.

6. To start the dispatcher automatically at Windows sign-in without admin rights:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-startup.ps1 -ConfigPath .\config.json
```

## Dispatch semantics

For a task to wake an agent:

- `TASK.md` must contain a parseable `task_id` field;
- `TASK.md` must contain a parseable `state` field;
- that state must be listed in the project's `dispatch_states`;
- that exact `project|agent|task_id` must not have been dispatched before.

A PM wake occurs when:

- the current `STATUS.md` has the same `task_id` as the current task;
- the status is one of the configured terminal states;
- that exact terminal status has not already notified PM.

Dispatcher deduplication is stored locally in `.dispatcher-state.json` and is not committed.

## R7 compatibility

The R7 mailbox protocol already provides the correct authority split: PM owns `TASK.md`, each agent owns `STATUS.md`, and executable evidence remains subject to the project's local-only rules. This dispatcher does not change those ownership boundaries.

For R7, keep:

```json
"dispatch_states": ["ACTIVE", "HOLD"],
"terminal_status_states": ["DONE", "COMPLETED", "PARTIAL", "BLOCKED"]
```

The `COMPLETED` value is accepted because current R7 STATUS files use it in addition to the originally documented `DONE` form.

## Security and operating rules

- Do not put ChatGPT credentials, cookies, GitHub tokens, or passwords in `config.json`.
- Only `https://chatgpt.com/...` URLs are accepted by the current UI adapter.
- The dispatcher sends only the standard wake instruction. It does not transfer full task content through the UI.
- The agent must read the authoritative TASK file itself.
- Do not use this layer to bypass ChatGPT rate limits, product restrictions, confirmations, or safety controls.
- Do not use browser/UI extraction of ChatGPT output as evidence; project state must come back through the repository mailbox.
- For projects where automated UI input is not acceptable, keep `prepare_only` or replace the transport adapter with a supported API/runtime later.

## Future adapters

The Git mailbox and deduplication model are intentionally separate from the ChatGPT UI transport. A future version can replace the wake transport with any supported mechanism without changing project mailboxes, for example:

- a supported ChatGPT/MCP action if targeted existing-chat dispatch becomes available;
- Codex/local agent execution;
- an OpenAI API worker;
- another RPA transport;
- a human-confirmed desktop notification transport.

The repository remains the authority regardless of transport.
