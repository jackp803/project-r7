# E6 FP-04 / FP-10 Persistence + Currentness Consumer — 2026-08-29

- task_id: `E6-20260829-026`
- agent: `E6`
- result: `PARTIAL / IMPLEMENTATION + TEST DEFINITIONS MATERIALIZED / EXECUTABLE NOT_RUN / NOT_PASS`
- target_branch: `agent/e6-fp04-fp10-persistence-currentness-20260829`
- authoritative_main_at_task_start: `db20f61cfbd54a1467aba28f30ee33ec23ab7727`
- task_id_match: `YES`
- source_test_head_before_evidence: `004b0430eaa4ed1d23950640f581f68051833676`
- provider_requests: `0`
- private_api: `NONE`
- credentials: `NONE`
- provider_account_mutation: `0`
- order_actions: `0`
- PAPER_SHADOW_runtime: `NOT_STARTED`
- bounded_live_fire: `NOT_AUTHORIZED`
- Gate_D_LIVE: `BLOCKED / UNAUTHORIZED`
- capital_exposure: `NONE`
- GitHub_Actions_CI_hosted_compute: `NOT_USED`

## Scope implemented

E6 added only provider-neutral durable storage/currentness mechanics for accepted FP-04, FP-10 and the merged E5 external-close reinterpretation result shape.

### Additive migration

`src/storage/migrations/0005_external_close_currentness.sql` adds append-only/immutable tables for:

- FP-04 `ExternalProviderObjectOwnershipEvidence` history;
- FP-10 `ExternalManualCloseLifecycleConvergenceEvidence` history;
- E5 external-close reinterpretation decision audit envelopes bound to exact FP-10/lifecycle references;
- E6-local append-only immutable conflict audit.

Existing `0001` through `0004` migrations are not modified. The migration does not alter shared contracts, provider semantics, risk policy, execution semantics, lifecycle transition semantics, or release gates.

### Provider-neutral persistence API

`src/storage/external_close_currentness.py` materializes an explicit E6 storage submodule without changing the accepted top-level `storage.__all__` boundary.

The store:

- persists exact canonical FP-04 and FP-10 payloads and exact E5 decision audit envelopes;
- revalidates deterministic FP-04 `extownrec_*`, FP-10 `extcloseconv_*`, and E5 `e5extclose_*` identities;
- preserves exact payload JSON/hash and replay-idempotence;
- rejects same deterministic ID with changed canonical content and records a durable conflict;
- exposes complete immutable histories;
- never calls provider/network/auth code;
- never derives provider ownership, provider flatness, lifecycle event, lifecycle next state, cleanup target, retry/cancel/replace authority, new-exposure authority, TradeResult lineage, or capital authority.

## Currentness / restart rules

Currentness is derived only from accepted owner-supplied immutable material and exact durable references. It does not use SQLite row IDs, insertion order, `persisted_at`, wall-clock arrival order, or newest-file heuristics.

### FP-10 current head

For one exact `position_id`:

- explicit `supersedes_close_convergence_evidence_id` links form the only FP-10 supersession graph;
- one unique unsuperseded head is required;
- competing unsuperseded heads fail closed as `CONFLICT`;
- cycles/disconnected contradictory history fail closed;
- missing predecessor material is `INCOMPLETE` rather than silently guessed current.

### FP-04 referenced currentness

For one logical FP-04 provider-object lineage:

```text
(provider_object_class, provider_identity_ref, provider_object_ref)
```

- explicit `supersedes_ownership_evidence_id` links determine historical/current relation;
- one unique unsuperseded FP-04 head is required;
- a referenced superseded FP-04 row degrades the current FP-10 projection and requires reconciliation;
- competing heads are conflict;
- missing predecessor is incomplete;
- E6 does not upgrade or manufacture ownership classification.

### Exact reference/hash chain

Recovery mechanically checks the current FP-10 against:

- exact referenced FP-04 payload hashes/object refs/snapshot hashes and mechanically derived supersession currentness;
- exact current E6 Position lifecycle projection ID/revision/hash;
- exact lifecycle execution-binding hash and execution snapshot hash;
- exact current FP-10 payload hash used by the E5 decision envelope;
- exact E5 decision lifecycle projection ref/ID/revision and lifecycle execution-binding ref/ID;
- E5 `evidence_current`, `close_eligible`, and `trade_result_evidence_incomplete` values as owner-produced audit facts, without recalculating their domain meaning.

A newer FP-04 head, newer FP-10 superseding head, newer lifecycle projection/current pointer, missing referenced dependency, hash mismatch, competing head, or stale/missing E5 decision therefore cannot remain restart-current.

## False-green prevention

`LIFECYCLE_CLOSE_ELIGIBLE` is persisted only as immutable FP-10 input evidence. E6 does not translate it into `CLOSED`.

`closed_presentation_allowed` is true only when all mechanically current storage conditions hold and the already-persisted authoritative lifecycle projection itself is `CLOSED`, with the exact current E5 decision also bound to the current FP-10/lifecycle chain and carrying `next_state=CLOSED`, `close_eligible=true`, `evidence_current=true`.

Therefore:

- historical FP-10 close eligibility alone cannot display CLOSED;
- an E5 close decision bound to a superseded FP-10 cannot display CLOSED;
- persisted lifecycle CLOSED without a current complete E5/FP-10 reference chain is explicitly degraded with `FALSE_GREEN_CLOSED_PRESENTATION_BLOCKED`;
- `TRADE_RESULT_EVIDENCE_INCOMPLETE` remains separately auditable and is never fabricated or cleared by E6.

## Deterministic test definitions

`tests/storage/test_external_close_currentness.py` and `tests/storage/test_external_close_currentness_supersession.py` define credential-free storage mechanics for:

1. exact FP-04 insert/read/replay;
2. same FP-04 ID + changed payload conflict;
3. exact FP-10 insert/read/replay;
4. same FP-10 ID + changed payload conflict;
5. exact E5 decision -> FP-10 -> lifecycle projection/binding binding without E6 transition application;
6. missing FP-04 dependency -> fail closed;
7. E5 decision with absent FP-10 dependency -> fail closed;
8. FP-10 referenced FP-04 payload-hash mismatch -> conflict;
9. explicit FP-10 supersession selects the unsuperseded head, not arrival order;
10. competing unsuperseded FP-10 heads -> conflict in either insertion order;
11. restart preserves immutable history and reconstructs the same current projection;
12. historical `LIFECYCLE_CLOSE_ELIGIBLE` alone does not become CLOSED;
13. stale E5 close decision after a newer FP-10 cannot false-green CLOSED;
14. `TRADE_RESULT_EVIDENCE_INCOMPLETE` remains auditable;
15. additive/idempotent migration inventory including `0005`;
16. no provider/network/mutation surface on the E6 store;
17. newer FP-04 for the same provider object invalidates an FP-10 still referencing the superseded FP-04;
18. newer accepted lifecycle projection/current pointer invalidates the older FP-10/lifecycle decision chain;
19. a newer FP-10 carrying changed normalized Position, FP-05, FP-11, terminal-protection and runtime-generation refs supersedes the older decision without arrival-order heuristics.

These are test definitions only. They were not executed in this GitHub session.

## Verification classification

LF-0 remains an active approved-local exact-revision infrastructure blocker per:

`status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`

No Product-Owner-approved local runner/exact-revision execution surface is available to this E6 session. Project executable verification therefore remains:

```text
local_verification = NOT_RUN
result = NOT_PASS
```

Exact future approved-local Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.storage.test_external_close_currentness -v
python -m unittest tests.storage.test_external_close_currentness_supersession -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
```

`NOT_RUN != PASS`.

No Python/unit/integration/safety/migration/restart project command was executed here. No GitHub Actions, GitHub-hosted runner, GitHub-triggered runner, provider/private network, credentials, Paper/Shadow runtime, order mutation, live-fire, Gate D, LIVE, or capital exposure was used.

## Terminal classification

Task acceptance requires local approved executable PASS for `DONE`. The bounded E6 implementation and deterministic test definitions are materialized, but executable qualification is unavailable under the active LF-0 blocker.

```text
E6-20260829-026 = PARTIAL
implementation = MATERIALIZED
executable qualification = NOT_RUN / NOT_PASS
FP-04 / FP-10 qualification = NOT CLAIMED PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

E6 stops after persisting terminal mailbox status and does not self-start provider-specific producers, runtime qualification, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, or another task.
