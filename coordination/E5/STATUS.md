# E5 Status

- task_id: `E5-20260824-018`
- agent: `E5`
- state: `DONE`
- branch: `agent/e5-gate-b-funding-consumer-20260824`
- base_main_sha: `84d48e2da290365f4c896936ee790bc21a38aa5f`
- implementation_evidence_head_before_terminal_status: `2f0da456489774ad5d13ea53ab97f0b6008fef4d`
- summary: `Adapted the E5 trade-result-v0.1 finalization boundary to require and validate canonical funding-allocation-v0.1 FundingAllocationEvidence. The builder now validates exact schema/profile/source/completeness/plan/position/symbol/interval/status/cost/currency and 17-field content identity before POSITION_CLOSED, emits funding evidence profile/id/status audit references, and excludes calculated_at from financial TradeResult identity.`
- files_changed: `src/position/trade_result.py; tests/position/test_trade_result.py; status/E5_GATE_B_FUNDING_CONSUMER_20260824.md; coordination/E5/STATUS.md`
- contracts_changed: `NONE`
- adr_changed: `NONE`
- e4_or_broker_changed: `NO`
- e6_persistence_changed: `NO`
- lifecycle_enum_or_transition_table_changed: `NO`
- provider_private_behavior_added: `NO`
- paper_shadow_live_authority_changed: `NO`
- local_verification: `NOT_RUN`
- evidence_path: `status/E5_GATE_B_FUNDING_CONSUMER_20260824.md`
- next_owner: `PM/E7`

## Implemented boundary

```text
exact E4 entry/exit Fill + final flat Position truth
+ exact E5 exit/protection authority
+ canonical funding-allocation-v0.1 FundingAllocationEvidence
-> fail-closed funding validation
-> existing POSITION_CLOSED
-> canonical trade-result-v0.1 with funding audit binding
```

## Canonical funding consumer

Current Gate B `build_trade_result()` requires a serialized mapping with:

```text
schema_version = contracts-v0.1
funding_evidence_profile_version = funding-allocation-v0.1
```

plus all required profile fields. The old E5-private `FundingEvidence` helper remains legacy-only and cannot finalize a current Gate B TradeResult.

E5 production imports no E4 funding implementation.

## Validation materialized

Fail-closed checks cover:

- supported schema/profile;
- `source_kind = PAPER_MODEL | BROKER_LEDGER`;
- non-empty source/source_version;
- lowercase SHA-256 source-material hash shape;
- non-negative integer source record count;
- exact trade plan / position / symbol lineage;
- exact `[opened_at, closed_at)` interval and `START_INCLUSIVE_END_EXCLUSIVE` semantics;
- `source_complete_through >= interval_end`;
- `calculated_at >= interval_end`;
- shared timestamps serialized as RFC3339 UTC `Z` strings;
- `ZERO_CONFIRMED` => count 0, cost `"0"`, USDT;
- `INCLUDED` => count >=1, finite signed decimal-string cost, USDT;
- canonical `funding_evidence_id` recomputation over exactly the 17 E7-defined identity-bearing fields.

`calculated_at` is audit metadata only and is not identity-bearing.

## TradeResult audit / financial semantics

Every current Gate B result emits:

```text
funding_evidence_profile_version
funding_evidence_id
funding_evidence_status
```

`INCLUDED` also emits the exact signed `funding_cost`; `ZERO_CONFIRMED` keeps optional TradeResult funding_cost omitted while the evidence references preserve zero authority.

Existing formula remains:

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

No slippage double deduction was introduced.

## Identity behavior

```text
same allocation identity + later calculated_at only
-> same funding_evidence_id
-> same trade_result_id

changed identity-bearing funding material
-> different funding_evidence_id
-> different TradeResult candidate identity
```

This task validates one supplied object only. Cross-replay duplicate/conflict discovery and durable conflict handling remain E6/E7 scope.

## Closure safety preserved

The existing PR #49 boundaries remain fail closed for non-flat/unreconciled/stale Position truth, partial/over/under close, duplicate/cross-set Fill evidence, wrong plan/position/side/role/action lineage, exact entry-request binding failures, quantity conservation failures, missing Fill fees and unsupported fee currencies.

`POSITION_CLOSED` is applied only after all closure, funding and financial evidence validation succeeds.

## Tests materialized

`tests/position/test_trade_result.py` now defines canonical funding-consumer coverage for:

- ordinary EXIT and EMERGENCY_EXIT ZERO_CONFIRMED;
- funding profile/id/status TradeResult audit refs;
- PR #52 serialized shape compatibility without E4 funding import in E5 production;
- evidence ID recomputation/corruption;
- plan/position/symbol/interval mismatches;
- schema/profile/source/completeness/timestamp/hash failures;
- ZERO/INCLUDED/currency semantics;
- missing canonical funding evidence;
- legacy FundingEvidence bypass rejection;
- calculated_at-only idempotency;
- changed funding allocation identity;
- preserved flatness/Fill/quantity/fee/PnL/lifecycle safety.

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact target revision is exposed in this session. No project code/tests were executed.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## GitHub compute / security

- GitHub Actions / CI / hosted runner used: `NO`
- GitHub-triggered self-hosted compute used: `NO`
- arbitrary cloud project execution used: `NO`
- Computer Adapter used: `NO`
- provider/private request used: `NO`
- credentials used: `NO`

## Remaining separate blockers / release impact

```text
E4 Paper ZERO_CONFIRMED producer = MATERIALIZED / executable NOT_RUN
E5 canonical funding consumer = MATERIALIZED STATICALLY
PROTECTION_STOP -> same-position residual/flat Position truth = BLOCKED / E4 IMPLEMENTATION GAP
E6 durable Paper persistence/restart/audit = BLOCKED
E7 full Paper E2E = BLOCKED
approved-local Gate B verification = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops on `DONE` for `E5-20260824-018`. Do not self-start E4 protection-flat remediation, E6 persistence, E7 integration/E2E, approved-local verification, Gate C, PAPER, SHADOW, or LIVE.
