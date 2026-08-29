# E6 FP-11 Persistence / Currentness / Restart Consumer — 2026-08-29

## Task

```text
task_id = E6-20260829-028
agent = E6
terminal_classification = PARTIAL
reason = bounded source/migration/test definitions materialized; approved-local executable verification unavailable under active LF-0 blocker
project executable verification = NOT_RUN / NOT_PASS
target_branch = agent/e6-fp11-persistence-currentness-20260829
authoritative_main_at_task_start = c912d5630531ddd21a600d1790d2cf3f4ee40e41
```

The later `main` commit `ff0fa058ae0d96648e45739960b28d0e4726a3aa` is a PM idle-watchdog status-only update which explicitly preserves `E6-20260829-028` as the active task and does not alter the consumed FP-11/lifecycle contracts or E4/E5 implementation boundary. No unrelated sync/merge was introduced into the E6 work branch.

## Accepted authority consumed

This E6 slice consumes, without redefining:

- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`
  - `protection-registry-multiplicity-v0.1`;
  - immutable `ProtectionRegistryMultiplicityEvidence`;
  - deterministic `protregmul_...` identity;
  - exact active-protection set hash/generation/currentness;
  - explicit `supersedes_registry_evidence_id`;
  - exact E4 producer definition of same logical Position/intended-protection lineage;
  - `FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED` terminal bridge.
- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`.
- `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`.
- accepted FP-04 durable ownership rows from the prior E6 currentness slice.
- merged E4 FP-11 producer/static candidate in `src/execution/protection_registry_evidence.py` and strict boundary module.
- merged E5 FP-11 policy consumer/static candidate in `src/position/protection_registry_policy.py`.
- `status/PM_E5_033_REVIEW_20260829.md`.
- active LF-0 blocker `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

No shared contract, lifecycle event, provider identity, ownership classification, risk policy, mutation rule, or release criterion is created by E6.

## Exact E6-owned files changed

```text
src/storage/migrations/0006_protection_registry_currentness.sql
src/storage/protection_registry_currentness.py
tests/storage/test_protection_registry_currentness.py
status/e6/FP11_PERSISTENCE_CURRENTNESS_RESTART_20260829.md
coordination/E6/STATUS.md   # terminal mailbox update follows this handoff
```

`src/storage/__init__.py` is intentionally unchanged; the accepted `storage.__all__ == ["open_sqlite_platform"]` boundary remains intact. The new store is an explicit E6 module surface and does not expose raw SQLite mechanics through the package wildcard contract.

## Additive migration

`0006_protection_registry_currentness.sql` is additive after existing `0001`–`0005` migrations. Existing rows/tables are not rewritten or destroyed.

### Immutable FP-11 history

Table:

```text
protection_registry_multiplicity_evidence
```

Persists exact owner-supplied material including:

- `protection_registry_evidence_id`;
- Position ID/ref/hash/observation;
- E4-defined logical-lineage anchors (`position_action_id`, approved-plan ref, protection OrderRequest ref, client-order identity ref);
- E6 storage-only `lineage_key_hash` over those exact accepted anchor fields;
- intended-protection-lineage hash;
- provider identity/instrument/observation generation and observation/receipt times;
- observation coverage/currentness and complete active-protection set hash;
- lifecycle projection/execution-binding refs;
- represented runtime/process/config generation refs;
- multiplicity/registry state;
- exact predecessor `supersedes_registry_evidence_id`;
- canonical payload JSON/hash.

UPDATE/DELETE triggers make the history append-only. Same deterministic evidence ID + identical canonical content is replay-safe; same ID + materially different content is rejected and recorded through the existing E6 external-currentness conflict audit.

### Immutable E5 interpretation history

Table:

```text
protection_registry_policy_interpretations
```

The primary identity is:

```text
(decision_id, source_registry_evidence_id)
```

This is deliberate because accepted E5 decision identity uses the FP-11 **material hash** (which excludes evidence ID, supersession ID and `evaluated_at`), while audit must retain which exact immutable FP-11 evidence object was interpreted. A timestamp-only evidence reevaluation may therefore share an E5 decision ID but still requires a distinct exact source-evidence audit binding.

The row preserves:

- exact source FP-11 evidence ID/full hash/material hash;
- exact Position ref/hash/observation;
- lifecycle projection ID/revision and execution-binding ID;
- E5 decision/event/next-state/reasons;
- source dispositions/reasons;
- `healthy_protection`;
- `terminal_close_dependency`;
- `evidence_current`.

Persistence rejects any interpretation that attempts to carry:

```text
provider_mutation_authorized != false
cleanup_target_ref != null
```

E6 stores E5 output; it never derives a lifecycle event or provider cleanup target.

## Current-head / supersession algorithm

The current-head resolver uses only accepted owner-defined logical lineage plus explicit immutable supersession links.

Logical lineage is exactly the E4 producer definition:

```text
position_id
+ intended_protection_lineage.position_action_id
+ intended_protection_lineage.approved_trade_plan_ref
+ intended_protection_lineage.protection_order_request_ref
+ intended_protection_lineage.client_order_identity_ref
```

For that exact lineage, E6:

1. validates each stored canonical FP-11 payload/ID/hash/index;
2. follows `supersedes_registry_evidence_id` only;
3. requires a predecessor, when present, to exist and belong to the same owner-defined lineage;
4. rejects supersession cycles;
5. rejects multiple competing unsuperseded heads;
6. rejects disconnected same-lineage histories;
7. reports missing predecessor as `INCOMPLETE` rather than inventing continuity;
8. never selects by SQLite row ID, insertion order, `persisted_at`, `evaluated_at`, arrival time, or filename/latest-file heuristics.

A timestamp/new row without an explicit valid same-lineage supersession therefore remains another unsuperseded head and fails closed rather than replacing authority.

Historical rows remain queryable through `fp11_history(...)`; superseded evidence is never deleted to make current state look healthy.

## Exact dependency/currentness validation

For each FP-11 active-protection entry, restart recovery mechanically requires the referenced existing E6 FP-04 row to exist and bind the same:

- `ACTIVE_PROTECTION` object class;
- provider identity/instrument;
- provider observation generation;
- provider object/snapshot ref/hash;
- provider object observation time;
- ownership classification;
- ownership reconciliation status.

The referenced FP-04 object lineage must itself have one unambiguous current head. Missing predecessor -> `INCOMPLETE`; competing heads -> `CONFLICT`; referenced superseded FP-04 evidence -> `STALE`.

E6 does not upgrade an ownership classification and does not infer intended protection from similarity.

## Restart / read-model behavior

Entry point:

```text
open_protection_registry_currentness_store(path)
-> ProtectionRegistryCurrentnessStore.recover(current_owner_authority)
```

The caller supplies current owner-authoritative Position, intended lineage, lifecycle projection/binding, provider generation/set hash and represented runtime generation. E6 mechanically compares them to the durable FP-11 head.

The read model exposes explicit E6-only diagnostics:

```text
HEALTHY_UNIQUE_PROTECTION
RECONCILIATION_REQUIRED
STALE
UNKNOWN
INCOMPLETE
CONFLICT
```

`HEALTHY_UNIQUE_PROTECTION` is possible only when all of these are simultaneously proven:

- one exact unambiguous current FP-11 head;
- exact accepted FP-11 success tuple;
- complete/current provider set;
- exactly one current compatible FP-04 dependency bound to the exact intended lineage;
- exact current Position/ref/hash/broker observation;
- exact current lifecycle projection/revision;
- exact current lifecycle execution binding when represented;
- exact represented provider/runtime generation material;
- one exact current E5 interpretation bound to that FP-11 source;
- E5 `healthy_protection=true` and `evidence_current=true`;
- E5 next state equals the current already-protected lifecycle state;
- positive authoritative Position quantity;
- no FP-10 terminal-close dependency;
- `provider_mutation_authorized=false` and `cleanup_target_ref=null`.

Row existence alone is never sufficient.

The read model remains non-green when evidence is missing, stale, incomplete, unknown, superseded, hash/reference mismatched, lifecycle incompatible, has competing heads, or lacks a current E5 interpretation.

### Terminal / CLOSED protection convergence

If FP-11 carries:

```text
FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED
```

or current authoritative quantity is zero while an active protection object remains, the read model remains `RECONCILIATION_REQUIRED` and preserves `terminal_close_dependency=true`.

A persisted `CLOSED` lifecycle claim plus unresolved active protection cannot become healthy through storage. E6 does not delete/cancel/ignore provider objects and does not create an FP-10 terminal-clear claim.

## E5 interpretation boundary

E6 revalidates the accepted deterministic `e5protreg_...` decision identity against the exact E5 material and exact source FP-11 hashes. It does not:

- select the E5 lifecycle event;
- replay the E5 state machine;
- infer `PROTECTION_VERIFIED`/`PROTECTION_LOST`/`STATE_UNKNOWN`;
- choose a provider cleanup target;
- authorize create/cancel/replace;
- turn `healthy_protection=true` into mutation authority.

If the source FP-11 head or current Position/lifecycle/provider/runtime material changes, an older interpretation cannot produce healthy current presentation.

## Tests defined

`tests/storage/test_protection_registry_currentness.py` defines credential-free deterministic coverage for:

- exact immutable FP-11 insert/read/history/reopen;
- SQL UPDATE/DELETE immutability;
- same FP-11 ID + changed payload conflict;
- explicit same-lineage supersession;
- timestamp-only/new-row competing-head failure;
- competing materially different unsuperseded heads;
- missing predecessor;
- cross-lineage supersession rejection during the affected-lineage currentness derivation;
- supersession/canonical-index corruption fail-closed behavior;
- exact E5 interpretation binding;
- missing/stale interpretation non-green behavior;
- missing/multiple/orphan/external/conflicting/stale/incomplete/unknown registry evidence after restart;
- changed Position/provider/lifecycle/runtime authority invalidation;
- missing/superseded FP-04 dependency handling;
- flat/CLOSED unresolved-protection FP-10 terminal dependency;
- unknown/unavailable current authority;
- proof that E5 healthy interpretation never yields E6 provider mutation/cleanup authority.

These are test **definitions only** in this GitHub session.

## Verification

The active LF-0 exact-revision preparation dependency remains blocked. This worker has no independently approved local exact-revision execution surface.

Therefore:

```text
project executable verification = NOT_RUN / NOT_PASS
migration execution = NOT_RUN / NOT_PASS
storage tests = NOT_RUN / NOT_PASS
restart tests = NOT_RUN / NOT_PASS
E4 FP-11 tests = NOT_RUN / NOT_PASS
E5 FP-11 tests = NOT_RUN / NOT_PASS
safety tests = NOT_RUN / NOT_PASS
```

Exact future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.storage.test_protection_registry_currentness -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest tests.execution.test_protection_registry_evidence -v
python -m unittest tests.position.test_protection_registry_policy -v
python -m unittest tests.safety.test_fp11_protection_registry_false_green -v
```

No GitHub Actions/CI/hosted/GitHub-triggered runner or other remote substitute was used. `NOT_RUN != PASS`.

## Known limitations / downstream needs

- Source/migration/test definitions are a static candidate only until the exact target revision is prepared and executed on the Product-Owner-approved local path.
- E7 still owns cross-module integration/requalification and any release-gate interpretation.
- E4 still owns provider-specific observation/translation and any later provider mutation path.
- E5 still owns protection/lifecycle/risk interpretation.
- FP-10 terminal protection convergence remains a separate shared evidence path; E6 only preserves its dependency state.
- No historical executable qualification is rebound to this branch.

## Authority / safety state

```text
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
LF-2 = NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
protection query/create/cancel/amend/replace = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

This E6 task grants no provider, runtime, live-trading, capital, cleanup, or mutation authority.
