# E7 Current Task

- task_id: `E7-20260820-002`
- issued_at: `2026-08-20T18:36:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, ADR-0001, release gates

## Objective

Hold after completing the post-Slice-1 static synchronization review. E4, E5, and E6 now have PM-issued correction/construction tasks. Do not pre-emptively re-review incomplete work and do not start a new integration slice.

## Current accepted review result

From `status/e7/POST_SLICE1_CONSTRUCTION_SYNC_REVIEW.md`:

- E4: `BLOCKED` — prior Broker/PaperBroker implementation was not recoverable from Git evidence;
- E5: `FAIL` — `E5-RISK-UNKNOWN-001`;
- E6: `FAIL` — `E6-EVIDENCE-CONTRACT-001`;
- executable evidence: `NOT_RUN`;
- Gate A/B/C/D remain `BLOCKED`.

## Required actions

1. Do not modify E4/E5/E6 domain code.
2. Do not re-review until PM issues a replacement ACTIVE E7 task after E4/E5/E6 provide fresh STATUS/handoff evidence.
3. Preserve the existing review artifact and findings unchanged unless a factual repository correction is necessary.
4. Do not advance any release gate.
5. Do not introduce GitHub Actions/CI/runner/project compute.
6. Update only `coordination/E7/STATUS.md` to acknowledge this HOLD task if needed.

## Acceptance

- E7 remains idle on integration work while E4/E5/E6 corrections are in progress;
- no domain rewrite;
- no contract change;
- no gate advancement;
- executable evidence remains `NOT_RUN`;
- no GitHub compute/CI.

## Writable scope

Only `coordination/E7/STATUS.md` for this HOLD task, unless required to correct a factual error in an existing E7 review artifact.

## Completion / status

Acknowledge HOLD and wait. PM will replace this TASK.md with an ACTIVE re-review task only after E4/E5/E6 repository evidence is ready.
