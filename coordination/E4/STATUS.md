# E4 Status

- task_id: `E4-20260824-011`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-gate-b-paper-funding-producer-20260824`
- baseline_main_sha: `599f1d7100a52b105af5d8a32437d44dbf7c2aa5`
- head_sha: `48252e7c7fd72a43618d256a7afdd8d725f3fa0c` (source/tests/docs/handoff HEAD immediately before this terminal STATUS-only commit)
- summary: `Implemented only the E4-owned provider-neutral local Paper funding-allocation-v0.1 producer. The registered immutable R7_PAPER_FUNDING_MODEL / paper-zero-funding-v0.1 positively asserts funding=0 for every instant in the exact authoritative [Position.opened_at, Position.broker_state_observed_at) interval and emits canonical ZERO_CONFIRMED FundingAllocationEvidence only from exact flat CONSISTENT same-position truth. Source material hash and fundev_<sha256> evidence identity are deterministic per the accepted profile; calculated_at is non-identity metadata. Unknown/unregistered/incomplete source or Position truth fails closed. No E5 consumer, E6 persistence, PROTECTION_STOP flat observer, provider/private, or release authority was implemented.`
- files_changed: `src/execution/funding.py; tests/execution/test_funding.py; docs/execution/PAPER_FUNDING_MODEL_V0_1.md; status/e4/E4_GATE_B_PAPER_FUNDING_PRODUCER_20260824.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No explicitly PM/Product-Owner-approved Local Runner action is available in this session for the exact clean target revision. Required Windows PowerShell commands from repository root: $env:PYTHONPATH="src" ; python -m unittest discover -s tests/execution -p "test_*.py" -v ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Executable evidence remains outstanding and NOT_RUN is not PASS. Separate PROTECTION_STOP same-position flat-truth implementation gap remains unchanged and outside this task.`
- handoff_path: `status/e4/E4_GATE_B_PAPER_FUNDING_PRODUCER_20260824.md`
- next_owner: `E7/PM for bounded static review; a later separately assigned E5 task may adapt TradeResult consumption only after PM acceptance`

## Wake / authority verification

Wake message task ID:

```text
E4-20260824-011
```

Latest `main:coordination/E4/TASK.md` matched exactly before implementation work began.

Authoritative files read first:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK was read; no other Agent TASK was read or executed.

## Branch baseline

At task start:

```text
main = 599f1d7100a52b105af5d8a32437d44dbf7c2aa5
agent/e4-gate-b-paper-funding-producer-20260824 = identical
```

No merge, rebase, force update, or history rewrite was required.

## Required dependency inspection

Read-only authority/dependency surfaces included:

- `contracts/README.md`
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`
- `docs/adr/ADR-0006-funding-allocation-evidence-boundary.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `src/brokers/base.py`
- current `src/brokers/paper.py`
- current `src/execution/models.py`
- E5 `src/position/trade_result.py` read-only
- current E4 broker/execution tests
- `status/RELEASE_GATES.md`
- accepted E7 PR #50/#51 review/contract evidence

Disposition:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The accepted funding profile is sufficient to emit canonical evidence without inventing any new shared serialized field, enum, currency meaning, financial formula, or authority boundary. E5's existing `FundingEvidence` remains a private helper and is not imported or replicated as the shared contract.

## Registered local Paper funding source

Exact immutable V0.1 semantics:

```text
source_kind = PAPER_MODEL
source = R7_PAPER_FUNDING_MODEL
source_version = paper-zero-funding-v0.1
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
status = ZERO_CONFIRMED
funding_cost = "0"
cost_currency = USDT
source_record_count = 0
```

Positive model assertions:

```text
zero_assertion = FUNDING_EQUALS_ZERO_FOR_EVERY_INSTANT_IN_EXACT_INTERVAL
completeness_assertion = MODEL_COMPLETE_THROUGH_EXACT_INTERVAL_END
```

This is explicit source authority, not empty-row inference. Missing rows, unavailable provider access, network failure, absent credentials or arbitrary/generic empty source state cannot produce ZERO_CONFIRMED.

## Exact final-position / interval boundary

The producer requires exact:

```text
ApprovedTradePlan.schema_version = contracts-v0.1
ApprovedTradePlan.trade_plan_id = non-empty canonical identity
ApprovedTradePlan.symbol = non-empty canonical symbol

final Position.schema_version = contracts-v0.1
final Position.position_id = non-empty exact identity
final Position.symbol = ApprovedTradePlan.symbol
final Position.actual_quantity = 0
final Position.reconciliation_status = CONSISTENT
final Position.opened_at = RFC3339 UTC Z
final Position.broker_state_observed_at = RFC3339 UTC Z
opened_at < broker_state_observed_at
```

Optional `closed_at`, if supplied, must equal the authoritative flat observation time.

Canonical allocation is:

```text
interval_start = final Position.opened_at
interval_end = final Position.broker_state_observed_at
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
source_complete_through = interval_end
calculated_at >= interval_end
```

No symbol-level net exposure and no OrderStatus.FILLED value is accepted as a substitute for exact same-position flat Position truth. E4 does not emit lifecycle POSITION_CLOSED.

## Canonical FundingAllocationEvidence emission

`src/execution/funding.py` emits exactly:

```text
schema_version
funding_evidence_profile_version
funding_evidence_id
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
calculated_at
```

with:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
status = ZERO_CONFIRMED
funding_cost = "0"
cost_currency = USDT
```

No provider-native, credential, account, risk-decision, strategy-authority, persistence or release-mode fields are added.

## Source material hash

The exact normalized source assertion material is documented in:

```text
docs/execution/PAPER_FUNDING_MODEL_V0_1.md
```

It includes source/version, exact plan/position/symbol interval lineage, explicit zero/completeness assertions, completeness watermark, record count, status/cost/currency and interval semantics.

Hash algorithm:

```text
json.dumps(material, sort_keys=True, separators=(",", ":"))
-> UTF-8
-> SHA-256 lowercase hex
```

Therefore `source_material_hash` represents an explicit complete zero-model assertion and not an accidental empty response.

## Stable evidence identity

Normative identity material contains exactly the 17 accepted profile fields:

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

Identity algorithm:

```text
lexicographically sorted compact JSON
-> UTF-8
-> SHA-256
-> fundev_<lowercase hex>
```

`calculated_at` is excluded by design.

Consequences:

```text
same immutable allocation material -> same funding_evidence_id
later calculated_at only -> same funding_evidence_id
changed identity-bearing material -> different funding_evidence_id
```

No UUID/random identity and no producer-level last-write-wins conflict rule were introduced.

## Fail-closed behavior

No canonical evidence is emitted on:

- unsupported/missing schema;
- missing/blank/non-canonical lineage identifiers;
- plan/Position symbol mismatch;
- nonzero/malformed/non-finite final Position quantity;
- reconciliation status other than CONSISTENT;
- malformed/non-UTC timestamps;
- start >= end;
- optional closed_at conflict;
- calculated_at < interval_end;
- unregistered source kind/source/version;
- changed model zero/completeness assertion;
- unsupported status/funding cost/currency/record-count semantics;
- arbitrary/generic unknown source.

No unknown/unavailable source fallback to ZERO_CONFIRMED exists.

## Deterministic test definitions materialized

Added:

```text
tests/execution/test_funding.py
```

Definitions cover:

- exact canonical ZERO_CONFIRMED field set/values;
- explicit zero/completeness authority;
- deterministic source-material hash;
- exact 17-field funding evidence ID derivation;
- calculated_at exclusion;
- repeated immutable material idempotency;
- changed plan/position/symbol/interval identity;
- unsupported source/model semantics fail closed;
- non-flat and non-CONSISTENT Position fail closed;
- plan/Position symbol mismatch;
- missing/schema/time/interval failures;
- calculated-at boundary;
- optional closed_at consistency;
- no random UUID;
- no E5-private FundingEvidence import;
- no network/provider credentials/private API behavior;
- no provider/persistence/release fields;
- no mutation of producer inputs;
- existing PaperBroker order/fill behavior remains compatible.

Definitions only; none were executed.

## Verification / execution state

```text
local_verification = NOT_RUN
GitHub Actions / CI = NOT_USED
GitHub-hosted / GitHub-triggered runner = NOT_USED
Computer Adapter = NOT_USED
provider/private API = NOT_CALLED
credentials = NOT_USED
Paper runtime/test execution = NOT_RUN
```

Required future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## Separate blocker / downstream scope

Unchanged separate blocker:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

Not implemented in this task.

Also not implemented:

- E5 canonical funding-evidence consumer adaptation / TradeResult audit refs;
- E6 funding/runtime persistence, conflict state, restart/replay/audit;
- broker/provider ledger funding acquisition or INCLUDED source model;
- provider/private networking or credentials;
- full Paper E2E;
- approved-local Gate B execution.

## Completion boundary

This task does not claim:

```text
TradeResult finalization = PASS
Paper E2E = PASS
Restart/persistence = PASS
Gate B = PASS
PAPER_READY = PASS
PAPER / SHADOW / LIVE = AUTHORIZED
```

Current release meaning remains:

```text
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E4 stops after this terminal STATUS and does not self-start E5 consumer adaptation, PROTECTION_STOP flat-truth remediation, E6 persistence, E7 Paper E2E, approved-local verification, Gate C, PAPER, SHADOW, or LIVE.
