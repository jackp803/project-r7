# E6 Current Task

- task_id: `E6-20260822-004`
- issued_at: `2026-08-22T10:28:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, E7 review `status/e7/E6_REGISTRY_STATIC_REVIEW_20260822.md`

## Objective

Freeze the corrected PR #16 early Slice 2 Registry/persistence implementation while E7 performs a targeted exact-revision re-review of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`.

## Frozen evidence

- completed correction task: `E6-20260822-003`
- branch: `agent/e6-platform`
- correction source/tests/docs revision: `aab1639d6db1f94e915d1c4af3041be28e9a4b94`
- handoff refresh: `f1bcb971bf3161ea440859445aac32af487a774c`
- platform-status refresh: `80a9233fc126ba8df0e5a17659a8b3f12762abe9`
- observed PR #16 head after completion mailbox status: `42c5d56996e0c4ff0e96edfc591726d9f9f34963`
- latest main synchronized into E6 before correction: `06752b83c18f6579b06c1f3b7e1d5837a2d6949a`
- synchronization merge: `c3d756b46af547b4ea0bb36aa653cc8b9081163f`
- executable verification: `NOT_RUN`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Claimed correction pending E7 review

E6 reports that persistence now permits exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

and rejects every other early-state pair before authoritative projection mutation. Migration `0001_strategy_registry.sql` also contains a database-level `BEFORE INSERT` guard for the same edge allowlist. Deterministic local-only tests define legal-edge, forbidden direct-store, no-state-mutation, and forbidden direct-SQL scenarios; all remain `NOT_RUN`.

## Required actions

1. Do not modify PR #16 registry/storage/tests/docs implementation while E7 reviews the frozen revision.
2. Preserve `E6-EVIDENCE-CONTRACT-001` and all previously accepted Registry/Inbox/evidence behavior.
3. Do not add or redesign lifecycle states, generic transition authority, Slice 3 execution/provider persistence, dashboard scope, broker/API work, credentials, or asset movement.
4. Do not modify shared contracts or other-agent production code.
5. Keep executable verification `NOT_RUN`; do not use GitHub Actions/CI/hosted/project compute.
6. Do not resynchronize merely because PM issues coordination-only TASK commits after this HOLD. Resynchronize only if E7 identifies meaningful production/shared-contract drift or a real merge conflict affecting reviewed behavior.
7. If acknowledging HOLD, update only `coordination/E6/STATUS.md`.

## Acceptance

PR #16 remains frozen and unmerged pending E7 targeted re-review. No Gate advancement, lifecycle expansion, provider execution, PAPER/SHADOW/LIVE, or executable PASS is authorized.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E7/PM disposition. Do not merge PR #16 or start another E6 feature automatically.
