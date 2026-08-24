# E4 Current Task

- task_id: `E4-20260824-011`
- issued_at: `2026-08-24T14:36:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-paper-funding-producer-20260824`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`, ADR-0006, accepted Gate A PASS, accepted close/TradeResult chain PR #46-#50, accepted funding evidence contract PR #51

## Objective

Implement only the E4-owned **provider-neutral local Paper funding-allocation producer** required by `funding-allocation-v0.1`.

Bounded chain:

```text
exact parent plan lineage
+ exact authoritative final same-position flat Position truth
+ explicit versioned local Paper funding model
+ exact canonical [opened_at, closed_at) interval
-> complete normalized funding source assertion
-> canonical funding-allocation-v0.1 FundingAllocationEvidence
```

Stop at canonical E4 funding evidence production. Do **not** implement E5 TradeResult consumption/adaptation, E6 persistence/restart/audit, PROTECTION_STOP flat-truth remediation, E7 Paper E2E, provider/private APIs, Demo/live funding lookup, or PAPER/SHADOW/LIVE authorization.

## Accepted contract baseline

```text
PR #51
merge = 6950824f6e2e7842718fc29f5e0808f9d8e7b04e
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
next implementation owner = E4
```

The contract defines E4 as funding source/acquisition/completeness/allocation authority, E5 as consumer/TradeResult owner, E6 as persistence/replay/audit owner, and E7 as contract/version/release authority.

All executable Gate B evidence remains `NOT_RUN`; Gate B remains `BLOCKED`; PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E4_EXECUTION.md`;
- `contracts/README.md`;
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`;
- `docs/adr/ADR-0006-funding-allocation-evidence-boundary.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, execution/protection profiles read-only;
- current `src/brokers/base.py`, `src/brokers/paper.py`, `src/execution/models.py`;
- current E4 broker/execution tests;
- E5 `src/position/trade_result.py` read-only only to understand the later consumer boundary;
- current `status/RELEASE_GATES.md` / accepted PR #50/#51 evidence.

### Contract-first blocker rule

If the accepted funding profile is insufficient to produce canonical evidence without inventing a new shared serialized field/enum/financial meaning, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Do not modify `contracts/**`, ADRs, E5 code, E6 code, or create a parallel cross-module Funding DTO.

## Required behavior

### 1. Minimal Gate B Paper producer

Materialize a local, provider-neutral, credential-free E4 funding source/model for the first Paper path.

The minimum accepted model is an explicit immutable zero-funding model with registered source semantics such as:

```text
source_kind = PAPER_MODEL
source = R7_PAPER_FUNDING_MODEL
source_version = paper-zero-funding-v0.1
```

The exact source string may differ only if it is stable, documented, provider-neutral and deterministic. The model semantics must **affirmatively define funding = 0 for every instant in the requested exact interval**.

Do not infer zero from:

- an empty provider result;
- no network access;
- missing rows;
- timeout/unavailable state;
- an empty generic event list with no versioned zero-model assertion.

No provider credentials/private API/network access are allowed in this task.

### 2. Canonical input lineage / interval

The producer must bind evidence to an exact already-known closed position instance.

At minimum validate/derive from authoritative inputs:

```text
ApprovedTradePlan.schema_version = contracts-v0.1
ApprovedTradePlan.trade_plan_id
ApprovedTradePlan.symbol

final Position.schema_version = contracts-v0.1
final Position.position_id
final Position.symbol == plan.symbol
final Position.actual_quantity = 0
final Position.reconciliation_status = CONSISTENT
final Position.opened_at
final Position.broker_state_observed_at
```

For this producer:

```text
interval_start = final Position.opened_at
interval_end   = final Position.broker_state_observed_at
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
```

Require `interval_start < interval_end` and RFC3339 UTC `Z` timestamps.

Do not use symbol-level net exposure as a substitute for exact same-position flat truth. Do not treat `OrderStatus.FILLED` alone as closure proof. E4 does not emit lifecycle `POSITION_CLOSED` here.

### 3. ZERO_CONFIRMED output

For the explicit Paper zero model, emit canonical serialized evidence containing exactly the accepted fields and semantics:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
funding_evidence_id = deterministic fundev_<sha256>
source_kind = PAPER_MODEL
source = stable provider-neutral source id
source_version = immutable Paper model version
source_material_hash = stable SHA-256 hash of the normalized explicit zero-model assertion material
source_record_count = 0
source_complete_through >= interval_end
trade_plan_id = exact parent plan
position_id = exact final Position
symbol = exact canonical symbol
interval_start = exact Position.opened_at
interval_end = exact flat observation time
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
status = ZERO_CONFIRMED
funding_cost = "0"
cost_currency = USDT
calculated_at >= interval_end
```

For the first zero model, setting `source_complete_through = interval_end` is acceptable when the versioned model semantics prove completeness through the exact requested boundary.

### 4. Deterministic source material and evidence identity

Implement the profile's canonical identity rules exactly.

`funding_evidence_id` identity material includes exactly:

```text
schema_version
funding_evidence_profile_version
source_kind
source
source_version
source_material_hash
source_record_count
source_complete_through
trade_plan_id
position_id
symbol
interval_start
interval_end
interval_semantics
status
funding_cost
cost_currency
```

Use lexicographically sorted compact UTF-8 JSON, SHA-256, and prefix:

```text
fundev_
```

`calculated_at` is not identity-bearing.

The E4-owned `source_material_hash` must itself be deterministic from canonical zero-model source material and must not depend on random values or credentials. Document the exact normalized Paper-zero assertion material used for this source version so replay is reproducible.

### 5. Idempotency / conflict-safe behavior

At the producer level:

- exact same immutable allocation material -> exact same `funding_evidence_id`;
- later `calculated_at` alone -> same ID;
- changed plan/position/symbol/interval/source-version/source-material/status/cost material -> different ID;
- do not overwrite or choose between conflicting durable evidence; E6 conflict persistence is later scope;
- do not invent a last-write-wins rule.

### 6. Fail closed

Do not emit a valid canonical evidence object when any required producer input is unknown/incomplete/incompatible, including at minimum:

- missing/unsupported schema/profile semantics;
- blank plan/position/source identifiers;
- plan/Position symbol mismatch;
- non-flat final Position;
- `reconciliation_status != CONSISTENT`;
- malformed/non-UTC timestamps;
- `interval_start >= interval_end`;
- `calculated_at < interval_end`;
- unsupported source/model version;
- unsupported currency or non-canonical funding status/cost if any internal helper permits configurable source material;
- source completeness cannot be proven.

No fallback from unknown/unavailable source to ZERO_CONFIRMED is permitted.

### 7. Shared-boundary discipline

The producer may return a canonical serialized mapping/value conforming exactly to `FundingAllocationEvidence`, or use an E4-internal helper that serializes exactly to that shape.

Do not make E5 import an E4 implementation class and do not import E5-private `position.FundingEvidence` as the shared contract.

Do not add provider-native fields, credentials, account IDs, API signatures, risk decisions, strategy authority, persistence IDs, release flags or live-mode authority to the canonical evidence.

### 8. No scope absorption

Known separate blocker remains outside this task:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

Do not modify close observation roles or solve that gap in this task.

Do not adapt `build_trade_result()` in E5. That is the next bounded consumer dependency after PM accepts this producer.

## Required deterministic test definitions

Add E4-owned definitions covering at minimum:

- valid exact-interval Paper zero model -> canonical ZERO_CONFIRMED evidence;
- exact canonical required fields/profile/status/currency;
- same immutable material repeated -> same object identity / same `funding_evidence_id`;
- later `calculated_at` only -> same `funding_evidence_id`;
- changed plan ID / position ID / symbol / interval / source version -> changed evidence identity or fail-closed mismatch as appropriate;
- non-flat Position blocks evidence;
- unknown/mismatched reconciliation blocks evidence;
- plan/Position symbol mismatch blocks evidence;
- malformed/non-UTC/empty/zero-length interval blocks evidence;
- calculated time before interval end blocks evidence;
- an unavailable/unknown generic source cannot be treated as ZERO_CONFIRMED;
- source material hash is deterministic and changes when identity-bearing model material changes;
- no random UUID evidence identity;
- no dependency on E5-private FundingEvidence;
- no network/provider credentials/private API behavior;
- no provider-native/persistence/release-authority fields in emitted evidence;
- existing PaperBroker/order/fill/close behavior remains unchanged by the funding producer.

Use sanitized/fake fixtures only.

## Writable scope

E4-owned only:

- `src/brokers/**` and/or `src/execution/**` for the bounded funding source/producer;
- `tests/brokers/**` and/or `tests/execution/**`;
- `docs/execution/**` only if needed to document the exact Paper source-version semantics;
- E4-specific `status/**` handoff/evidence;
- `coordination/E4/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR changes;
- `src/position/**` / `src/risk/**`;
- E6 storage/platform;
- E1-E3 production;
- PROTECTION_STOP flat-observer changes in this task;
- provider/private network/API/credentials;
- Demo/live funding queries;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This remains implementation/test-definition work under the hard local-only policy. Unless an exact-revision Local Runner action is separately approved by PM/Product Owner, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- one explicit versioned local Paper funding model can produce canonical `funding-allocation-v0.1` evidence without provider/private access;
- ZERO_CONFIRMED is a positive complete model assertion, never empty-row inference;
- exact plan/position/symbol/interval/completeness semantics are enforced;
- evidence/source hashes and IDs are deterministic per contract;
- invalid/unknown/incomplete source or Position state fails closed;
- no E5/E6/E7/provider/release scope is crossed;
- deterministic E4 tests are materialized;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted funding profile cannot be implemented without a genuine shared semantic change;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround or parallel cross-module contract.

Do not declare TradeResult finalization, Paper E2E, Gate B/PAPER_READY, or any PAPER/SHADOW/LIVE mode PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e4-gate-b-paper-funding-producer-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E4/STATUS.md` on this target branch, not main.

Then stop. Do not self-start E5 consumer adaptation, PROTECTION_STOP flat-truth remediation, E6 persistence, approved-local verification, Gate C, PAPER, SHADOW or LIVE.