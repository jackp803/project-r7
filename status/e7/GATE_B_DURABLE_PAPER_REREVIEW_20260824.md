# Gate B Durable Paper Re-review — E7-20260824-057

## Authority / scope

- task_id: `E7-20260824-057`
- target branch: `agent/e7-gate-b-durable-paper-rereview-20260824`
- reviewed main: `c14e1c53a1a94bd05bd537ff2dc33e16a4f3b65f`
- authoritative TASK blob: `ec6f228ce74c66cadd5062a98850ac2cff2e05d8`
- contract baseline: `contracts-v0.1 / BASELINE`
- lifecycle projection: `position-lifecycle-projection-v0.1`
- execution freshness companion: `position-lifecycle-execution-binding-v0.1`
- E5 binding producer: PR `#64 / merge d36d1897ccb4ee06ed9a2dbf981dc4814d7a8541`
- E6 binding consumer + TradeResult remediation: PR `#65 / merge 43eeb2bba236a12d641a30a807eb120990b6e595`
- project executable verification: `NOT_RUN`

This task is static integration/release-definition work only. E7 did not execute project code, tests, migrations, Paper runtime, Local Runner, GitHub Actions/CI, provider/private APIs, credentials, PAPER, SHADOW, or LIVE behavior.

## Terminal static disposition

```text
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E5 lifecycle execution-binding producer = MATERIALIZED / executable NOT_RUN
E6 durable runtime + binding consumer = MATERIALIZED / executable NOT_RUN
E6 TradeResult referenced-object completeness remediation = MATERIALIZED / executable NOT_RUN
E7-052 false READY execution-freshness path = RESOLVED STATIC
E7-052 TradeResult graph-completeness defect = RESOLVED STATIC
new contract blocker = NONE FOUND
new domain implementation blocker = NONE FOUND for the reviewed Gate B durable slice
Restart/persistence executable criterion = NOT_RUN
Paper E2E durable audit executable criterion = NOT_RUN
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = YES
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Static/source acceptance is not executable PASS evidence.

## 1. E5 producer compatibility

PR #64 implements the accepted companion without changing lifecycle projection identity or authority.

The producer:

- keeps `schema_version=contracts-v0.1` and `position-lifecycle-projection-v0.1` unchanged;
- binds exactly `PROTECTION_STOP | POSITION_EXIT | EMERGENCY_EXIT` PositionAction-authorized requests;
- hashes the complete canonical OrderRequest payload;
- binds all canonical OrderResult observations by semantic `observed_at` plus payload hash;
- binds all canonical matching Fills by stable `fill_id`, `filled_at`, and payload hash;
- rejects equal-time changed OrderResult payload, changed Fill identity payload, request/client conflicts, out-of-scope PositionAction roles, and lineage mismatch;
- excludes clean pre-position entry-v0.1 requests rather than joining them by `trade_plan_id` heuristic;
- emits deterministic `execution_snapshot_hash` and `posexecbind_` identity;
- supplies GENESIS / TRANSITION / REATTESTATION composition helpers while preserving the accepted E5 lifecycle producer/state machine.

No E4 truth or E6 storage authority is absorbed by E5.

## 2. E6 mechanical consumer compatibility

PR #65 implements the companion as a storage/recovery consumer without importing E5 lifecycle semantics.

The E6 consumer:

- persists one immutable binding per exact lifecycle projection;
- validates exact position/projection/revision/interpreted-time/profile/scope binding;
- mechanically recomputes the current durable execution snapshot from the same fixed shared scope;
- uses the same canonical request/result/fill hashing and ordering rules as the contract/E5 producer;
- requires exact PositionAction/request/fill lineage;
- preserves exact duplicate replay;
- fails closed on identity/hash/reference/conflict mismatch;
- reports `E5_EXECUTION_REINTERPRETATION_REQUIRED` and a non-READY recovery when current durable execution snapshot differs from the latest E5 binding;
- keeps raw Position freshness as an independent `E5_REATTESTATION_REQUIRED` axis;
- does not map OrderStatus or Fill facts to PositionEvent/lifecycle state.

Therefore the E7-052 false READY path is statically closed:

```text
old OPEN_PROTECTED binding
+ later PARTIALLY_FILLED/FILLED protection truth
-> execution snapshot mismatch
-> non-READY / E5 reinterpretation required

old OPEN_PROTECTED binding
+ later CANCELED/EXPIRED/REJECTED protection truth
-> execution snapshot mismatch
-> non-READY / E5 reinterpretation required
```

The same rule covers later `POSITION_EXIT` and `EMERGENCY_EXIT` execution evidence.

## 3. Equal-anchor re-attestation composition

The accepted lifecycle profile already allows `REATTESTATION` on the same exact broker Position observation.

PR #64 can emit a new REATTESTATION plus new companion after E5 considers later execution evidence without changing lifecycle state. PR #65 can persist the next lifecycle revision/binding and restore execution-freshness equality mechanically.

E7 added a cross-module definition using the real E5 producer, E4 close translator/PaperBroker and E6 journal:

`tests/integration/test_gate_b_durable_binding_integration.py`

This definition proves the intended sequence:

```text
E5 EXIT_REQUESTED projection + initial binding
-> later real E4 POSITION_EXIT OPEN execution truth
-> old binding stale / non-READY
-> E5 equal-anchor REATTESTATION + new binding
-> close/reopen may return READY when all other recovery conditions are satisfied
```

Executable result remains `NOT_RUN`.

## 4. TradeResult reference completeness remediation

The prior E7-052 defect is statically remediated by PR #65.

Before TradeResult persistence, E6 now mechanically requires all declared reference sets and their lineage to exist and match, including:

- `entry_order_request_ids`;
- `exit_order_request_ids`;
- `entry_fill_ids`;
- `exit_fill_ids`;
- `exit_authority_refs.position_action_id`;
- exact request/fill/action/position/plan/risk/role lineage;
- flat-position observation time consistency.

The bounded E6-018 remediation additionally requires settled profile lineage on referenced PositionActions and guarantees a legacy/corrupt recovered TradeResult graph cannot remain `READY`.

Missing references become non-READY/incomplete. Lineage conflicts become conflict/non-READY. E6 does not recompute PnL, fees, risk policy, lifecycle, or broker truth.

## 5. Funding / immutable TradeResult behavior

Accepted funding semantics remain coherent:

- canonical `funding-allocation-v0.1` evidence is immutable financial source truth;
- same allocation lineage with conflicting evidence fails closed and is never last-write-wins;
- TradeResult binds exact funding evidence ID/status/cost and exact position interval;
- same TradeResult identity with changed canonical payload conflicts;
- a later financial conflict cannot silently rewrite a durable result;
- recovery includes unresolved durable conflicts in non-READY status.

No new funding semantic gap was found.

## 6. Complete close-path composition

Static composition is coherent for all three accepted close mechanisms.

### Ordinary EXIT

```text
canonical upstream lineage
-> E5 lifecycle projection/binding
-> E5 EXIT authority / EXIT_REQUESTED
-> E4 reduce-only MARKET POSITION_EXIT
-> Paper Fill + same-position flat truth
-> E4 funding evidence
-> E5 TradeResult + POSITION_CLOSED/CLOSED projection
-> E5 closed-projection execution binding
-> E6 exact persistence
-> close/reopen exact projection/binding/funding/TradeResult audit graph
```

### EMERGENCY_EXIT

Same chain with E5 `EMERGENCY_EXIT` authority and E4 `EMERGENCY_EXIT` order role. E4 does not infer emergency state.

### Full verified PROTECTION_STOP

```text
OPEN_UNPROTECTED
-> real protection request/query
-> E5 PROTECTION_VERIFIED / OPEN_PROTECTED
-> E5 protected projection + execution binding
-> real full PROTECTION_STOP Fill
-> same-position authoritative flat Position truth
-> funding
-> E5 protection-stop TradeResult + CLOSED projection
-> closed execution binding
-> E6 durable exact graph
```

Partial protection remains fail closed under existing semantics; this review does not broaden residual-protection behavior.

E7 materialized `tests/e2e/test_gate_b_durable_paper_e2e.py` for these three close/reopen paths. Executable result remains `NOT_RUN`.

## 7. Restart freshness / corruption matrix

Static implementation plus domain/E7 definitions now cover or define:

- exact current binding -> normal mechanical recovery evaluation;
- missing binding -> non-READY;
- projection/revision/time/profile/scope/hash mismatch -> reject/non-READY;
- later partial/full protection truth -> reinterpretation required;
- later canceled/expired/rejected protection truth -> reinterpretation required;
- later POSITION_EXIT/EMERGENCY_EXIT execution truth -> reinterpretation required;
- equal-anchor re-attestation + new matching binding -> freshness restored;
- newer raw Position truth -> independent E5 re-attestation required;
- identical request/result/fill/binding replay -> idempotent;
- changed identity payload / equal-time execution conflict -> fail closed;
- unknown/reconciliation-required/degraded execution state -> existing fail-closed recovery;
- lifecycle revision/predecessor/broker-anchor/vocabulary conflict -> fail closed;
- missing/corrupt TradeResult references -> non-READY;
- funding conflict -> non-READY/no silent financial rewrite;
- entry-v0.1 remains outside the position-linked execution binding and is not heuristically joined.

The previous E7-052 safety definition was updated to consume real PR #64 binding production and PR #65 recovery rather than passing merely because a companion was missing:

`tests/safety/test_gate_b_durable_lifecycle_freshness.py`

Executable result remains `NOT_RUN`.

## 8. Upstream Strategy / Signal / TradeIntent boundary

The current Paper durability journal begins with durable RiskDecision / ApprovedTradePlan authority and retains exact `intent_id`, `strategy_id`, and `strategy_version` lineage. Current Gate B restart-authoritative Position execution binding is intentionally a post-position execution-evidence profile and does not infer pre-position entry association.

No new blocker is declared for the reviewed Gate B open-position/restart slice because accepted contracts do not require Signal/TradeIntent payloads to become the position execution-freshness authority. They remain upstream canonical evidence and exact IDs remain carried into RiskDecision/ApprovedTradePlan.

A future restart-authoritative `PENDING_ENTRY` workflow remains outside `position-lifecycle-execution-binding-v0.1` and requires explicit E7 refinement before it can claim READY. This limitation remains documented and fail closed.

## 9. Security / scope / release authority

Static inspection found no accepted PR #64/#65 change that:

- adds provider/private API/network access;
- requires or stores credentials/secrets;
- adds GitHub Actions/CI/hosted execution;
- grants strategy lifecycle promotion;
- grants PAPER/SHADOW/LIVE authority;
- weakens E5 risk/lifecycle authority;
- gives E6 lifecycle inference authority.

## 10. Gate B disposition

All known shared/domain implementation blockers identified by E7-052 for the current durable Paper slice are statically remediated.

The remaining Gate B blocker is executable evidence, not a newly discovered static architecture/implementation gap.

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E5 lifecycle execution-binding producer = MATERIALIZED / executable NOT_RUN
E6 durability + binding consumer + TradeResult completeness = MATERIALIZED / executable NOT_RUN
Restart/persistence executable criterion = NOT_RUN
Paper E2E durable audit executable criterion = NOT_RUN
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = YES
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Gate B must remain BLOCKED until PM explicitly authorizes an exact revision for approved-local execution and the required matrix produces durable PASS evidence.

## 11. Required later approved-local matrix

Not run in this task. After PM authorizes the exact accepted revision, run at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

These commands are not PASS evidence until actually executed in a Product-Owner/PM-approved local environment against an exact revision.

## 12. Verification record

```text
project_executable_verification = NOT_RUN
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
strategy lifecycle promotion = NONE
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production/test changes by E7 = NONE
new shared contract/ADR changes by E7 = NONE
```
