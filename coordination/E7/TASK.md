# E7 Current Task

- task_id: `E7-20260824-041`
- issued_at: `2026-08-24T14:15:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-funding-evidence-contract-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate A evidence PR #33, Gate B static preflight PR #34, accepted protection chain PR #37-#45, accepted close/TradeResult contract PR #46, accepted E5 close producer PR #47, accepted E4 close consumer PR #48, accepted E5 TradeResult builder PR #49, accepted E7 close-to-TradeResult blocker review PR #50

## Objective

Resolve only the shared **provider-neutral funding allocation evidence contract/semantic gap** identified and accepted from `E7-20260824-040` / PR #50.

Current accepted blocker:

```text
ordinary EXIT close-to-authoritative-flat = MATERIALIZED / executable NOT_RUN
EMERGENCY_EXIT close-to-authoritative-flat = MATERIALIZED / executable NOT_RUN
final TradeResult system chain = BLOCKED by missing governed funding evidence boundary/source
PROTECTION_STOP same-position flat truth = separate E4 implementation gap, not this task
Gate B = BLOCKED / NOT YET PASS
```

Define the governed cross-module evidence boundary that a real Paper/runtime producer can emit, E5 can consume for `trade-result-v0.1`, and E6 can later persist/audit without importing an E5-private DTO or inventing provider semantics.

This is a **STATIC CONTRACT / ARCHITECTURE task only**. Do not implement E4/E5/E6 production code and do not execute project code.

## Accepted evidence / reason for task

PR #50 accepted the E7 finding that current `src/position/trade_result.py::FundingEvidence` is explicitly E5-internal and not a shared/persisted contract. Current Broker/PaperBroker and E6 surfaces have no governed funding evidence producer/source. Cross-module use of the private E5 shape or an undocumented mapping is forbidden by contract-first governance.

The existing financial semantics already require:

```text
funding_evidence_status = ZERO_CONFIRMED | INCLUDED
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

but the serialized provider-neutral evidence object/profile and producer/consumer ownership are missing.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/README.md`, `contracts/SHARED_CONTRACTS_V1.md`;
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
- ADRs including ADR-0005;
- E5 `src/position/trade_result.py` read-only;
- E4 `src/brokers/base.py`, `src/brokers/paper.py` read-only;
- E6 current storage/platform interfaces read-only;
- PR #50 review artifact and current `status/RELEASE_GATES.md` / `status/INTEGRATION_STATUS.md`.

## Required decisions

### 1. Versioning / compatibility classification

Decide explicitly whether the funding evidence boundary is:

```text
ADDITIVE_PROFILE_REQUIRED
```

under parent `schema_version = contracts-v0.1`, or whether a stronger contract-version change is required.

Prefer additive compatibility only if existing object meanings are not reinterpreted. Record producer/consumer migration impact and fail-closed behavior for legacy objects without the profile.

### 2. Governed provider-neutral funding evidence object/profile

Define a serialized shared object/profile with an explicit profile identifier, for example a versioned funding-allocation evidence profile. Do not rely on the private E5 `FundingEvidence` dataclass as the shared contract.

At minimum resolve semantics for:

```text
schema_version
funding evidence profile version
stable funding_evidence_id
source / source_version
position_id
symbol
exact interval_start
exact interval_end
status = ZERO_CONFIRMED | INCLUDED
signed funding_cost when INCLUDED
cost / pnl currency compatibility
observed_at or calculated_at timestamp
stable identity / idempotency material
```

Also decide whether exact parent lineage such as `trade_plan_id`, risk decision/policy, or other identifiers are required for safe one-position binding. Do not omit lineage merely for convenience; document why each required identity is or is not necessary.

All monetary/quantity/time semantics must remain provider-neutral and use existing Decimal-string / RFC3339-Z conventions where applicable.

### 3. Completeness and zero-confirmation semantics

Define exactly what authorizes:

```text
ZERO_CONFIRMED
```

It must not mean merely “no funding row happened to be returned” unless the declared source contract proves that absence over the exact interval is complete and authoritative.

Define fail-closed behavior for at least:

- unknown/unavailable source;
- partial interval coverage;
- stale observation/calculation;
- source/version mismatch;
- position/symbol/lineage mismatch;
- unsupported currency;
- malformed/non-finite cost;
- contradictory zero vs non-zero evidence;
- duplicate/conflicting evidence IDs;
- overlapping or non-exact interval evidence if not explicitly supported.

If a non-final evidence state such as UNKNOWN/INCOMPLETE is represented, define whether it is a separate status/profile state or simply non-finalizable evidence. It must never allow TradeResult finalization.

### 4. Signed cost semantics

Preserve the already accepted financial meaning:

```text
positive funding_cost = cost
negative funding_cost = credit
ZERO_CONFIRMED effective cost = 0 only with explicit authoritative zero confirmation
```

For the current `linear-base-asset-pnl-v0.1` path, define the required currency relationship to `pnl_currency = USDT`. Do not invent conversion semantics unless a separately versioned conversion profile is explicitly required and in scope; otherwise unsupported currency must fail closed.

### 5. Exact interval semantics

Bind evidence to the exact final position interval used by `trade-result-v0.1`:

```text
interval_start = authoritative opened_at
interval_end   = authoritative closed_at / flat_position_observed_at
```

Define inclusivity/exclusivity sufficiently to prevent double allocation across adjacent positions or duplicate funding events. Define how deterministic ordering/deduplication works if the provider/runtime naturally supplies multiple funding events that are aggregated into one evidence object.

### 6. Producer / consumer / persistence ownership

Make an explicit architecture decision for each role:

- which domain owns authoritative funding source acquisition/allocation for Paper/runtime evidence;
- which domain serializes/emits the canonical evidence object;
- E5 consumes/validates but does not manufacture provider/runtime funding truth;
- E6 persists/replays/audits but does not invent execution/provider truth;
- E7 owns contract/version/release semantics.

Determine the **next implementation owner** after this contract task (expected candidates E4 or E6, but decide from actual source authority, not convenience).

For Paper mode, define how a legitimate provider-neutral source can produce `ZERO_CONFIRMED` or `INCLUDED` without provider credentials/private API. Do not authorize real exchange/private access in this task.

### 7. TradeResult compatibility

Specify how `trade-result-v0.1` consumes the new shared evidence and how current E5 internal validation code should be adapted later without changing accepted PnL semantics.

No final TradeResult may be produced when required canonical funding evidence is absent, incomplete, conflicting, stale, mismatched, or unsupported.

Do not implement the E5 adapter in this task; identify the exact later owner/scope if adaptation is required.

### 8. Persistence / restart expectations

Define enough serialization/idempotency/audit semantics so E6 can later durably store and restore the evidence without recomputing or silently changing it:

- immutable identity material;
- duplicate replay behavior;
- conflicting same-lineage evidence behavior;
- relationship to the one final TradeResult for a closed position;
- required timestamps/source metadata.

Do not implement E6 storage in this task.

## Contract / ADR outputs

Materialize the decision in E7-owned authoritative artifacts. Expected scope may include:

- a new or updated file under `contracts/**` for the funding evidence profile;
- `contracts/README.md` registry/versioning references;
- update to `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md` only where cross-reference/consumption semantics need clarification without weakening prior rules;
- a new/update ADR under `docs/adr/**` if the producer/ownership/versioning decision is architecture-significant;
- E7 review/status evidence;
- conservative `status/RELEASE_GATES.md` and `status/INTEGRATION_STATUS.md` reconciliation.

Do not modify E1-E6 production code or their domain tests.

## Required static checks / examples

Provide deterministic serialized examples or contract fixtures sufficient for later domain implementation to distinguish at least:

- valid `ZERO_CONFIRMED` exact-interval evidence;
- valid `INCLUDED` positive cost;
- valid `INCLUDED` negative credit;
- missing/unknown source fails closed;
- interval mismatch fails closed;
- position/symbol/lineage mismatch fails closed;
- unsupported currency fails closed;
- contradictory/conflicting duplicate evidence fails closed;
- exact same immutable material -> same evidence identity;
- material evidence change -> different identity or explicit reconciliation conflict.

Static examples are not executable PASS evidence.

## Separate known blocker — do not absorb it

PR #50 also found:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

Do not modify `src/brokers/**` or solve this E4 implementation gap in E7-041. Record it as the next independent dependency after the funding contract/producer sequence according to the accepted dependency order.

## Release-gate rules

This task cannot make Gate B PASS.

Preserve at minimum:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
ordinary/emergency close-to-flat = NOT_RUN / needs local evidence
Restart/persistence = BLOCKED
Paper E2E / durable TradeResult audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

A successful contract decision may change only the funding item from `CONTRACT_OR_SEMANTIC_GAP` to a precisely named `IMPLEMENTATION_GAP / next_owner=<domain>`; it is not executable PASS.

## Writable scope

E7-owned only:

- `contracts/**`;
- `docs/adr/**`;
- `docs/architecture/**` if strictly needed;
- E7-owned contract/integration fixture or static test-definition paths if useful;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md`;
- E7-specific `status/e7/**`;
- `coordination/E7/STATUS.md` on the target branch.

Forbidden:

- `src/brokers/**`, `src/execution/**`;
- `src/position/**`, `src/risk/**`;
- E6 storage/platform implementation;
- E1-E3 production;
- provider/private APIs, networking, credentials;
- GitHub Actions/CI/workflows;
- PAPER/SHADOW/LIVE authority.

## Executable verification

This is STATIC CONTRACT / ARCHITECTURE work only:

```text
project_executable_verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

Do not request Local Runner, execute project code, use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, Computer Adapter, provider/private APIs, or credentials.

`NOT_RUN` remains `NOT_RUN` and cannot become PASS from this task.

## Acceptance

### DONE

- a governed serialized provider-neutral funding evidence profile/object is defined;
- versioning/backward compatibility is explicit;
- ZERO_CONFIRMED/INCLUDED and signed-cost/currency semantics are exact;
- interval completeness, source authority and fail-closed rules are exact;
- stable identity/idempotency/conflict semantics are exact;
- E4/E5/E6/E7 producer/consumer/persistence ownership is explicit;
- the next domain implementation owner is named with bounded expected producer behavior;
- TradeResult consumption semantics are unambiguous without importing an E5-private DTO;
- no E1-E6 production or provider/private behavior is implemented;
- release state remains conservative and executable evidence remains NOT_RUN.

### BLOCKED

Use only if the existing parent contract/profile cannot accommodate the evidence boundary safely without a larger unresolved product/architecture decision. Record the exact contradiction, affected producers/consumers, and required PM/Product Owner decision. Do not invent a workaround.

## Completion / mailbox rule

Commit/push E7-owned contract/ADR/status evidence to `agent/e7-gate-b-funding-evidence-contract-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E7/STATUS.md` on that target branch, not main.

Then stop. Do not self-start the domain funding producer, E4 PROTECTION_STOP flat-truth remediation, E6 persistence, approved-local verification, Gate C, PAPER, SHADOW, or LIVE.