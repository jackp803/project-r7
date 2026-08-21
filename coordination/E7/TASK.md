# E7 Current Task

- task_id: `E7-20260821-009`
- issued_at: `2026-08-21T13:42:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, Product Owner OKX decision

## Objective

Hold after completing static/safety review of E4 PR #11. PR #11 has been merged by PM, and E4 now owns the next bounded Demo-first OKX provider-adapter construction task.

## Accepted current state

- PR #11 merge commit: `9679a224da3764ecbab7161e6c6f256ca46aecf7`
- E5 -> E4 boundary: `PASS / STATIC ONLY`
- E4 entry translator: `PASS / STATIC ONLY`
- E4 OKX sizing/metadata safety: `PASS / STATIC ONLY`
- Broker/PaperBroker regression: `PASS / STATIC ONLY`
- metadata freshness finding: `E4-OKX-FRESHNESS-HARDEN-001 / NON_BLOCKING for PR #11 / required before future Demo adapter acceptance`
- executable verification: `NOT_RUN`
- Gate A/B/C/D: `BLOCKED`

## Required actions

1. Do not modify E1-E6 domain code.
2. Do not start Demo-adapter review until PM replaces this HOLD after E4 posts fresh task/status/handoff evidence for `E4-20260821-008`.
3. Preserve the accepted E7 review artifact `status/e7/E4_OKX_SIZING_STATIC_REVIEW_20260821.md` and prior findings.
4. Do not advance Gate A/B/C/D.
5. Do not run provider requests, project tests, GitHub Actions, CI, hosted runners, or GitHub-triggered project compute.
6. Do not interpret E4 Demo-adapter source construction as authorization to send Demo or real-money orders.
7. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

- E7 remains idle while E4 performs bounded source construction;
- no domain/shared-contract modification;
- executable evidence remains `NOT_RUN`;
- real-money/PAPER/SHADOW/LIVE remains blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for PM to issue the next ACTIVE E7 review task after E4 completion. Do not start provider networking, review, or another task automatically.
