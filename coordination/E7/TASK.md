# E7 Current Task

- task_id: `E7-20260821-002`
- issued_at: `2026-08-21T08:37:00+08:00`
- state: `ACTIVE`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, ADR-0001, release gates

## Objective

Perform static review of the completed E4 bounded Broker/PaperBroker skeleton and resolve/classify the reported E4 <-> E5 `entry_instruction` translation gap without modifying E4/E5 domain code or silently redefining shared contracts.

E5 and E6 correction findings were already statically accepted in the prior E7 task and are not to be reopened unless this E4 review uncovers a concrete cross-contract regression.

## Review inputs

### E4

- branch: `agent/e4-execution-v2`
- implementation/handoff revision reported by E4: `53487a93f6f10d89723403b1a2e2426ba1c7e82a`
- status: `coordination/E4/STATUS.md` on the E4 branch
- handoff: `docs/execution/E4_TO_E7_HANDOFF.md`
- executable verification: `NOT_RUN`

### E5 boundary context

- corrected E5 revision: `cb65c951d59f6fd036bd61691d7e96d025e371c8`
- current E5 `entry_instruction` / `protection_instruction` nesting is explicitly provisional and is not an accepted independent shared contract.

### Existing contract baseline

`contracts-v0.1` requires an `ApprovedTradePlan.entry_instruction` and E4 `OrderRequest.order_type` plus conditional fields, but the current baseline does not explicitly define the inner entry-instruction mapping profile.

## Required actions

1. Statically review the E4 source/test/handoff changes and assign `PASS | FAIL | BLOCKED` for the bounded skeleton, including:
   - ApprovedTradePlan-only execution authority;
   - E4 does not invent direction, quantity, leverage, margin mode, protection loosening, or risk approval;
   - stable idempotency identity;
   - requested vs filled quantity separation;
   - partial-fill representation;
   - explicit fill facts;
   - overfill/exposure-cap fail closed;
   - ambiguous acknowledgement -> `UNKNOWN` or `RECONCILIATION_REQUIRED`;
   - no blind duplicate submit;
   - query/reconcile-before-retry;
   - broker/order/fill/exposure truth remains E4-owned;
   - no private Pionex / SHADOW / LIVE behavior.
2. Review the E4 test definitions for coverage of the above, but keep executable disposition `NOT_RUN` unless approved local evidence exists.
3. Review the reported `entry_instruction.style -> OrderRequest` gap and classify it using E7 integration taxonomy, at minimum distinguishing:
   - `CONTRACT MISMATCH` — canonical producer/consumer semantics are underspecified or incompatible;
   - `INTEGRATION GLUE GAP` — existing canonical semantics are sufficient and only an adapter is missing.
4. Perform a producer/consumer impact inventory for any required resolution:
   - producer: E5 ApprovedTradePlan serialization;
   - primary consumer: E4 execution translator/gateway;
   - secondary consumer/audit: E6 Registry/persistence where applicable;
   - E7 integration tests/evidence.
5. Do **not** modify `contracts/**` in this task. If a shared semantic clarification/version is required, produce an E7-owned contract-change proposal that states:
   - exact missing semantics;
   - proposed minimum fields/enums/conditional rules;
   - backward/forward compatibility impact;
   - whether this is additive-compatible or breaking;
   - proposed contract versioning treatment;
   - exact E4/E5/E6 follow-up owners/scopes;
   - required local integration tests.
6. If the gap is only integration glue and no shared contract change is required, document the exact bounded E4/E5 adapter responsibilities and follow-up scopes without editing their source.
7. Persist the E7 review/decision artifact and update `coordination/E7/STATUS.md` with:
   - E4 static disposition;
   - E4 <-> E5 boundary classification;
   - contract-change proposal path if applicable;
   - remaining blockers;
   - next-owner recommendations.
8. Keep Gate A/B/C/D unchanged. `STATIC PASS != EXECUTABLE PASS`; `NOT_RUN != PASS`.
9. Do not create a Codex bug ticket unless a concrete implementation defect has been locally reproduced. A contract/design gap is not a Codex bug.

## Acceptance

This task is complete only when Git contains:

- a static E4 disposition;
- a precise classification of the `entry_instruction` boundary gap;
- a bounded resolution proposal or adapter responsibility decision;
- explicit E4/E5/E6 impact inventory;
- no domain implementation rewrites;
- no unapproved shared-contract modification;
- executable evidence still `NOT_RUN` where appropriate;
- release gates still blocked.

## Writable scope

- E7-owned integration/status/review artifacts
- E7-owned contract-change proposal / architecture decision draft paths
- `coordination/E7/STATUS.md`

## Forbidden scope

- editing E4/E5/E6 production implementation;
- editing `contracts/**` in this task;
- enabling PAPER/SHADOW/LIVE;
- GitHub Actions/CI/runner/project compute;
- treating static review as executable evidence.

## Completion / status

Persist the review and any proposal, update STATUS, then stop and wait for PM. Do not start the follow-up correction automatically.
