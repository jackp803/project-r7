# E7 Current Task

- task_id: `E7-20260824-053`
- issued_at: `2026-08-24T22:18:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-execution-lifecycle-freshness-contract-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B in-memory chain through PR #55, PR #57/#58 lifecycle projection contract/producer, PR #60 lifecycle vocabulary clarification, PR #61 E6 durability merge `42f6d015ea5c9387983a822820dde211608a249e`, accepted BLOCKED E7 durable review PR #62 merge `383cc6bf622c10f441d082a36b03612a1a8f2a32`

## Objective

Resolve only the shared contract/architecture gap proven by `E7-20260824-052` at the durable boundary between newer E4 execution observations and E5 lifecycle interpretation.

The required result is the minimum E7-owned serialized freshness/evidence-binding rule that lets E6 determine mechanically whether persisted E4 execution truth relevant to a Position has already been incorporated into the latest restart-authoritative E5 lifecycle projection.

The rule must preserve:

```text
E4 = broker/order/fill execution truth authority
E5 = lifecycle/risk interpretation authority
E6 = persistence/recovery/mechanical freshness validation only
```

Do not execute project code and do not promote Gate B.

## Accepted blocker evidence

PR #62 accepted the E7-052 diagnosis:

```text
current E5 projection profile binds exact E4 Position broker observation
but does not bind later relevant E4 OrderResult/Fill interpretation freshness

OPEN_PROTECTED + later PARTIALLY_FILLED/FILLED protection truth
-> E5 requires STATE_UNKNOWN / RECONCILIATION_REQUIRED pending Position-close truth

OPEN_PROTECTED + later CANCELED/EXPIRED/REJECTED protection truth
-> E5 requires PROTECTION_LOST / EMERGENCY
```

Current E6 recovery can detect newer raw Position truth and ambiguous/degraded OrderResult truth, but cannot safely conclude whether healthy later `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `EXPIRED`, or `REJECTED` execution evidence has already been interpreted by E5. E6 must not import/copy E5 transition semantics or invent a private order-status-to-lifecycle rule.

The secondary E6 TradeResult referenced-object completeness defect recorded by E7-052 remains a later E6-owned implementation follow-up under settled contract. Do not fix or redesign that defect in this E7 task.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/README.md`, `contracts/SHARED_CONTRACTS_V1.md`;
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`;
- `contracts/POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`;
- protection, close/TradeResult and funding profiles;
- ADR-0005 through ADR-0008;
- E4 canonical OrderRequest / OrderResult / Fill shapes and PaperBroker observation behavior;
- E5 `src/position/protection_result.py`, close/result bridges, state machine, and lifecycle projection producer read-only;
- E6 merged PR #61 persistence/recovery implementation read-only;
- accepted E7-052 safety definitions `tests/safety/test_gate_b_durable_lifecycle_freshness.py`;
- `status/e7/GATE_B_DURABLE_PAPER_INTEGRATION_REVIEW_20260824.md`;
- current `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md`.

## Required contract decision

Define the smallest stable shared rule that answers this question without domain inference:

> For the latest E5 restart-authoritative lifecycle projection of one Position, what exact E4 execution evidence has E5 authoritatively interpreted, and how can E6 prove that no newer relevant durable execution evidence remains uninterpreted?

At minimum the decision must specify:

1. **serialized binding material** — exact IDs/timestamps/hashes/watermarks/references or another deterministic representation sufficient to bind E5 interpretation to E4 execution evidence;
2. **evidence scope** — which Position-linked OrderRequest / OrderResult observation / Fill facts are lifecycle-relevant for this Gate B durable slice, including at least protection-order truth demonstrated by E7-052;
3. **freshness ordering** — how later E4 execution observations are ordered and compared against the accepted E5 binding without using SQLite arrival order;
4. **missing/unknown behavior** — absent, partial, unsupported, conflicting, or ambiguous binding must fail closed and must never yield a false `READY` restart claim;
5. **producer authority** — E5 alone declares which exact execution evidence it interpreted when materializing a lifecycle projection or companion authoritative interpretation artifact;
6. **consumer authority** — E6 may only validate/reference/compare the declared binding against persisted E4 evidence; E6 must not decide which lifecycle transition an order/fill implies;
7. **relation to Position broker observation binding** — preserve existing `broker_state_observed_at` / `lifecycle_source_broker_state_observed_at` semantics and explain how the new execution-evidence axis composes with them;
8. **revision/identity impact** — state whether existing `position-lifecycle-projection-v0.1` can be compatibly extended, requires an additive companion profile/artifact, or requires a new profile/version; justify compatibility explicitly;
9. **idempotency/conflict rules** — duplicate identical evidence must be replay-safe; changed evidence under the same identity/binding must fail closed;
10. **future evidence** — a future E4 observation not proven covered by the latest E5 authoritative interpretation must force a bounded re-interpretation/reconciliation-required recovery state rather than silently remaining `READY`.

Do not choose an implementation merely because it is easiest for E6. Prefer the least new shared material that fully preserves authority and auditability.

## Required scenario coverage

The contract must make the following cases deterministic for downstream E5/E6 work:

### A. Protected order remains active

An E5 projection claiming `OPEN_PROTECTED` may be restart-authoritative only when its declared execution-evidence binding proves the relevant protection truth it interpreted is not stale relative to durable E4 evidence.

### B. Later protection partial/full fill

A later relevant `PARTIALLY_FILLED` or `FILLED` OrderResult/Fill not covered by the latest E5 binding must prevent E6 from returning authoritative `READY` under the older protected lifecycle projection.

E6 does not infer the next lifecycle state; it only reports that fresh E5 interpretation is required.

### C. Later protection cancellation/inactive terminal truth

A later relevant `CANCELED`, `EXPIRED`, or `REJECTED` observation not covered by the latest E5 binding likewise invalidates a stale restart-ready claim without E6 inferring `EMERGENCY` itself.

### D. Ambiguous/degraded truth

Existing UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED fail-closed behavior must remain conservative and compose with the new rule.

### E. Close/emergency/exit applicability

Determine whether the same freshness problem applies to ordinary EXIT, EMERGENCY_EXIT, and PROTECTION_STOP close execution observations. If yes, include them in the minimum shared rule now. If not, document why their existing accepted durable lineage already proves interpretation freshness.

Do not leave a known equivalent gap merely because the initial failing definition is a protection case.

## Downstream ownership contract

Your output must give PM an explicit bounded dependency map, expected to be structurally similar to:

```text
E7 contract/ADR resolution
-> E5 producer adaptation, if required
-> E6 mechanical consumer/recovery adaptation
   + separate E6 TradeResult graph-completeness repair from E7-052
-> E7 durable Paper integration definitions/re-review
-> PM-authorized approved-local Gate B verification
```

Do not implement E5 or E6 production code in this task.

If no E5 serialization change is required, state the exact existing E5 artifact E6 can consume and why it is already authoritative.

## Writable scope

E7-owned only:

- `contracts/**` as strictly required;
- `docs/adr/**` as required for architecture/authority/versioning decision;
- `docs/architecture/**` if strictly useful;
- E7-owned `tests/integration/**`, `tests/e2e/**`, `tests/safety/**` only for contract definitions/fixtures needed to specify the new rule;
- `status/e7/**`;
- `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md` only for conservative reconciliation;
- `coordination/E7/STATUS.md` on the target branch.

Forbidden:

- E1-E6 production code/tests;
- direct E5 producer or E6 recovery fixes;
- provider/private API/network/credentials;
- `.github/workflows/**` or GitHub CI/compute;
- strategy lifecycle promotion;
- PAPER/SHADOW/LIVE authorization;
- weakening E5 risk/lifecycle semantics to make persistence easier.

## Verification

This is static contract/architecture work only.

Record:

```text
project_executable_verification = NOT_RUN
```

Do not run project code/tests and do not request Local Runner execution. `NOT_RUN != PASS`.

## Acceptance

### DONE

- the E4 execution-truth -> E5 lifecycle interpretation freshness boundary is explicit and mechanically testable by E6 without lifecycle inference;
- protection partial/full-fill and inactive terminal observation cases cannot remain falsely restart-authoritative under an older E5 projection;
- ordinary exit/emergency/protection-stop applicability is explicitly resolved;
- E4/E5/E6 authority boundaries remain unchanged;
- compatibility/versioning and identity/conflict semantics are explicit;
- downstream E5/E6 changes are bounded and assignable;
- E7-052 secondary E6 TradeResult completeness defect remains separately identified for E6 remediation;
- Gate B remains BLOCKED and no executable NOT_RUN criterion becomes PASS;
- PAPER/SHADOW/LIVE remain unauthorized.

### BLOCKED

If no bounded serialized rule can solve this without a materially wider lifecycle architecture change, record the exact conflict, affected producers/consumers, and required Product Owner/PM decision. Do not guess.

## Completion / mailbox rule

Commit/push bounded E7 contract/ADR/status evidence to `agent/e7-gate-b-execution-lifecycle-freshness-contract-20260824`.

Write/push terminal `coordination/E7/STATUS.md` on that target branch with task_id `E7-20260824-053` and stop.

Do not self-start E5/E6 adaptation, approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, LIVE, or another task.