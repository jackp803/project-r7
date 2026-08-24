# E4 Gate B Paper Funding Producer Handoff — 2026-08-24

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Project Manager  
**Branch:** `agent/e4-gate-b-paper-funding-producer-20260824`  
**Task:** `E4-20260824-011`  
**Baseline main:** `599f1d7100a52b105af5d8a32437d44dbf7c2aa5`  
**Implementation/tests/docs HEAD before this handoff:** `96a77786b221f2bc6e9575cc8bd378e4f23c43cb`  
**Date:** 2026-08-24

### 1. Objective

Implement only the E4-owned provider-neutral local Paper funding-allocation producer required by the accepted `funding-allocation-v0.1` profile:

```text
exact parent ApprovedTradePlan lineage
+ exact authoritative final same-position flat Position truth
+ explicit immutable local Paper zero-funding model
+ exact [opened_at, flat_observation) interval
-> canonical FundingAllocationEvidence / ZERO_CONFIRMED
```

The task stops at E4 canonical funding evidence production.

### 2. Contract-first disposition

Required inspection found:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The accepted `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md` and ADR-0006 fully define the required serialized shape, source/completeness authority, exact interval, status/cost semantics, source-material hashing, stable evidence identity, and fail-closed behavior.

E5's existing `src/position/trade_result.py::FundingEvidence` was inspected read-only and remains explicitly E5-private. E4 does not import it, recreate it as a cross-module DTO, or make E5 depend on an E4 implementation class.

### 3. What changed

Added an independent E4 execution-source module:

```text
src/execution/funding.py
```

It registers exactly one V0.1 Paper model:

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

The explicit immutable source assertions are:

```text
zero_assertion = FUNDING_EQUALS_ZERO_FOR_EVERY_INSTANT_IN_EXACT_INTERVAL
completeness_assertion = MODEL_COMPLETE_THROUGH_EXACT_INTERVAL_END
```

This is positive model authority. The producer never infers zero from an empty source result, missing rows, unavailable network, timeout, absent credentials, or a generic empty event list.

### 4. Exact authoritative input boundary

The producer validates at minimum:

```text
ApprovedTradePlan.schema_version = contracts-v0.1
ApprovedTradePlan.trade_plan_id = non-empty exact identity
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

If `closed_at` is present on the supplied final Position, it must exactly equal the authoritative flat `broker_state_observed_at`.

The producer does not accept symbol-level net exposure or `OrderStatus.FILLED` as a substitute for exact same-position flat truth, and it does not emit/apply E5 lifecycle `POSITION_CLOSED`.

### 5. Canonical interval and completeness

For the V0.1 Paper zero model:

```text
interval_start = final Position.opened_at
interval_end = final Position.broker_state_observed_at
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
source_complete_through = interval_end
```

The model semantics affirmatively define zero funding for every instant in:

```text
[interval_start, interval_end)
```

Because the registered model itself defines complete zero funding over every requested instant, setting `source_complete_through = interval_end` is the source-owned completeness assertion allowed by the accepted profile.

`calculated_at` must be UTC and `>= interval_end`.

### 6. Canonical emitted evidence

`produce_paper_zero_funding_evidence(...)` emits only the accepted serialized fields:

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

Current fixed values are:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
source_kind = PAPER_MODEL
source = R7_PAPER_FUNDING_MODEL
source_version = paper-zero-funding-v0.1
source_record_count = 0
source_complete_through = exact interval_end
interval_semantics = START_INCLUSIVE_END_EXCLUSIVE
status = ZERO_CONFIRMED
funding_cost = "0"
cost_currency = USDT
```

No provider-native, account, credential, risk-policy, strategy-authority, persistence, or release-mode fields are emitted.

### 7. Source material hash

The exact normalized zero-model assertion material is documented in:

```text
docs/execution/PAPER_FUNDING_MODEL_V0_1.md
```

It includes:

```text
assertion
completeness_assertion
cost_currency
funding_cost
interval_start
interval_end
interval_semantics
position_id
source
source_complete_through
source_kind
source_record_count
source_version
status
symbol
trade_plan_id
```

The producer uses:

```python
json.dumps(material, sort_keys=True, separators=(",", ":"))
```

then UTF-8 encoding and SHA-256. The resulting lowercase 64-hex digest is `source_material_hash`.

The hash therefore represents explicit complete zero authority for the exact allocation lineage/interval rather than an accidental empty result.

### 8. Canonical funding evidence identity

`funding_evidence_id` follows profile section 10 exactly.

Identity-bearing fields are exactly:

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

Algorithm:

```text
lexicographically sorted compact JSON
-> UTF-8
-> SHA-256
-> "fundev_" + lowercase hex digest
```

`calculated_at` is intentionally excluded from identity. Therefore:

```text
same immutable allocation material -> same funding_evidence_id
later calculated_at only -> same funding_evidence_id
changed identity-bearing material -> different funding_evidence_id
```

No random UUID is used.

The producer does not implement durable conflict selection or last-write-wins. E6 conflict-safe persistence/replay remains later scope.

### 9. Fail-closed behavior

The producer emits no canonical evidence on at least:

- unsupported plan or Position schema;
- missing or blank plan/position/symbol identity;
- surrounding-whitespace mutation of exact lineage identifiers;
- plan/Position symbol mismatch;
- nonzero, malformed, NaN or infinite final Position quantity;
- reconciliation status other than `CONSISTENT`;
- malformed/non-UTC timestamps;
- zero-length or reversed interval;
- conflicting optional `closed_at`;
- `calculated_at < interval_end`;
- unregistered source kind;
- unregistered source identifier;
- unregistered source version;
- changed zero assertion or completeness assertion;
- unsupported interval semantics;
- unsupported status/cost/currency/record-count semantics;
- arbitrary/generic source objects.

There is no fallback from unknown/unavailable source state to `ZERO_CONFIRMED`.

### 10. Files changed

```text
src/execution/funding.py
tests/execution/test_funding.py
docs/execution/PAPER_FUNDING_MODEL_V0_1.md
status/e4/E4_GATE_B_PAPER_FUNDING_PRODUCER_20260824.md
coordination/E4/STATUS.md   # terminal worker mailbox update follows this handoff
```

No `src/brokers/paper.py`, Broker interface, shared model, E5/E6/E7 production code, contracts, ADRs, release gates, or provider adapter was changed.

### 11. Contracts consumed

- `contracts-v0.1`
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- ADR-0006
- existing shared Position / ApprovedTradePlan semantics

### 12. Contracts produced or changed

```text
NONE
```

No shared field, enum, currency meaning, financial formula, identity rule, or authority boundary was changed.

### 13. Deterministic test definitions materialized

Added:

```text
tests/execution/test_funding.py
```

Definitions cover:

- valid exact-interval Paper zero model -> canonical `ZERO_CONFIRMED` evidence;
- exact required field set/profile/status/currency;
- positive zero-model assertion and completeness material;
- exact source-material SHA-256 recomputation;
- exact 17-field evidence identity and `calculated_at` exclusion;
- same immutable material -> same object/ID;
- later calculation timestamp only -> same ID;
- changed plan ID / position ID / matched symbol / interval -> changed ID;
- unsupported source/source version/model assertion/completeness/status/cost/currency/record count -> fail closed;
- arbitrary generic source -> fail closed;
- non-flat/malformed position -> fail closed;
- UNKNOWN/MISMATCH/RECONCILIATION_REQUIRED -> fail closed;
- plan/Position symbol mismatch -> fail closed;
- schema/missing/blank/timestamp/interval errors -> fail closed;
- optional `closed_at` consistency;
- calculation time boundary;
- no random UUID;
- no E5-private FundingEvidence dependency;
- no network/provider credential behavior;
- no provider-native/persistence/release fields;
- input mappings remain unmodified;
- existing PaperBroker order/fill surface compatibility.

Definitions only; no project code/tests were executed in this task.

### 14. Local verification

```text
Result: NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved Local Runner action is available in this session for the exact clean target revision.

Required future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

`NOT_RUN` is not PASS evidence and does not promote any Gate B criterion.

### 15. Known limitations / dependencies

Intentionally not implemented:

- E5 adaptation of `build_trade_result()` to consume canonical `funding-allocation-v0.1` and emit funding evidence audit references;
- E6 immutable funding/Position/Action/Order/Fill/TradeResult persistence, conflict tracking, restart/replay/audit;
- `PROTECTION_STOP -> same-position residual/flat Position truth` remediation;
- provider/broker ledger funding acquisition or `INCLUDED` model;
- provider/private API/network/credentials;
- full Paper E2E;
- approved-local Gate B execution.

Separate blocker remains unchanged:

```text
PROTECTION_STOP -> same-position residual/flat Position truth
= BLOCKED / E4 IMPLEMENTATION_GAP
```

This task intentionally does not absorb it.

### 16. Required next action

E7/PM should perform bounded static review of this producer. After PM accepts the producer, the dependency order in the accepted funding contract calls for a separate bounded E5 consumer adaptation task. E4 does not assign or start that work.

### 17. Security / secrets

Confirmed:

- no API key, secret, token, password, private key, signature secret, account ID, or live `.env` value was added;
- no provider/private API or network request was made;
- model/test values are local deterministic Paper semantics only;
- no real funding/provider evidence is claimed.

### 18. GitHub compute policy

Confirmed:

```text
GitHub Actions / CI = NOT_USED
GitHub-hosted runner = NOT_USED
GitHub-triggered self-hosted runner = NOT_USED
GitHub project-code execution = NOT_USED
Computer Adapter = NOT_USED
```

GitHub was used only for repository read/write collaboration.

### 19. Live-trading / release impact

```text
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
SHADOW = UNAUTHORIZED
LIVE = UNAUTHORIZED
provider/private API = NOT AUTHORIZED
```

This source module does not submit orders or alter exposure. It only produces local canonical Paper funding evidence when supplied exact authoritative final flat Position truth.

### 20. Codex bug ticket

```text
NONE
```
