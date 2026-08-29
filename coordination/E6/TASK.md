# E6 Current Task

- task_id: `E6-20260829-026`
- issued_at: `2026-08-29T16:54:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-fp04-fp10-persistence-currentness-20260829`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, accepted `external-provider-object-ownership-reconciliation-v0.1`, accepted `external-manual-close-lifecycle-convergence-v0.1`, accepted Position lifecycle persistence/currentness semantics, merged E5 FP-04/FP-10 lifecycle-consumer static candidate, `status/PM_E5_031_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest **provider-neutral E6 immutable persistence / current-index / restart fail-closed consumer** for accepted FP-04 ownership/reconciliation evidence, accepted FP-10 close-convergence evidence, and the E5 reinterpretation decision produced from those profiles.

The platform must be able to persist immutable historical evidence, reconstruct the exact current projection after restart, detect stale/superseded/conflicting/missing reference chains mechanically, and refuse false-green current/closed presentation when the required current evidence chain cannot be proven.

This task may modify only E6-owned storage/platform/tests/status paths. It must not modify E5 lifecycle/risk policy, E4 provider/broker code, E7 shared contracts, AgentBridge, provider credentials/configuration, runtime authorization, or capital/live settings.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E6_PLATFORM.md`;
- accepted `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- accepted `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- accepted Position lifecycle projection/execution-binding profiles and existing E6 persistence for them;
- accepted `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md` only where FP-10 references terminal protection evidence;
- merged E5 provider-neutral FP-04/FP-10 consumer source/public result shape as repository evidence, without taking over E5 policy;
- current E6 SQLite/storage repository/migration/currentness patterns;
- `status/PM_E5_031_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Use existing E6 storage architecture and naming conventions. Add only the minimum persistence/repository/current-projection surfaces needed to support these immutable records:

1. FP-04 `ExternalProviderObjectOwnershipReconciliationEvidence` records;
2. FP-10 `ExternalManualCloseLifecycleConvergenceEvidence` records;
3. E5 external-close reinterpretation decision records/references sufficient to audit which exact FP-10 evidence and lifecycle authority were interpreted.

Do not create a new shared cross-module contract. Storage schema is E6-owned persistence representation only. If a shared field is genuinely missing, record a precise E7 change request and stop at PARTIAL rather than inventing semantics.

## Required persistence invariants

### Immutable history

- Accepted evidence/decision identity is immutable once inserted.
- Reusing an evidence/decision ID with different canonical content/hash must be rejected.
- Identical re-insert may be idempotent only if existing E6 persistence conventions allow exact-content idempotency; it must never overwrite materially different content.
- Historical superseded evidence must remain queryable/auditable; do not delete old rows to make current state look clean.

### Exact reference binding

Persist exact owner-supplied identity/reference/hash material needed to mechanically prove current chains, including as applicable:

- provider object/snapshot/generation refs from FP-04;
- ownership evidence ID/hash and supersession reference;
- FP-10 close-convergence evidence ID/hash and its exact provider Position, execution set, FP-04 set, FP-05 residual, terminal-protection, lifecycle projection/binding, runtime/project-generation references;
- E5 reinterpretation decision ID, exact FP-10 evidence ID, exact lifecycle projection/revision/binding reference, decision/event/next-state/reasons/currentness flags.

E6 must persist references/hashes; it must not manufacture provider identifiers, E5 lifecycle decisions, or missing execution lineage.

### Current projection / index

Define a deterministic current projection for a Position/provider-object lineage that:

- selects only evidence whose own immutable identity and supersession/reference chain are mechanically valid;
- never uses row insertion order, database row ID, wall-clock arrival time, or "latest file" heuristics as semantic authority;
- detects multiple competing unsuperseded heads and reports conflict/fail-closed rather than choosing one;
- treats a missing required referenced evidence record as incomplete/fail-closed;
- treats mismatched stored reference/hash/profile/schema identity as invalid/fail-closed;
- preserves distinction between historical record existence and current eligible evidence;
- does not infer `CURRENT_KNOWN_OWNED`, `LIFECYCLE_CLOSE_ELIGIBLE`, or `CLOSED` merely because a row exists.

Use accepted profile owner-supplied generations/currentness and exact supersession links where defined. E6 performs mechanical validation/current projection only; semantic ownership/flatness/lifecycle authority remains E4/E5/E7 as defined by accepted contracts.

### Restart fail-closed

After a storage reopen/restart, reconstructing current Position/external-close state must fail closed when any required current chain is absent, ambiguous, invalid, stale by stored authority reference, or internally conflicting.

At minimum, platform/current projection must not display or expose a false-green terminal state when:

- the FP-10 record required by the E5 decision is missing;
- the referenced FP-04 evidence set is incomplete/mismatched;
- the referenced lifecycle projection/binding identity no longer matches the decision/evidence chain;
- two unsuperseded FP-10 heads compete for the same Position/current authority generation;
- an E5 decision refers to an older/superseded FP-10 evidence object;
- terminal-protection or execution/reference hashes required by FP-10 are missing/mismatched;
- the persisted decision is not current under its exact referenced evidence generation.

Return an explicit degraded/reconciliation/currentness status through existing E6 patterns; do not fabricate an E5 transition or mutate lifecycle state to repair storage.

## E5 decision persistence boundary

The merged E5 candidate returns an E5-owned reinterpretation result with deterministic decision identity, decision, optional existing lifecycle event, next state, reason codes, close-eligible flag, TradeResult-evidence-incomplete flag, and evidence-current flag.

E6 may persist/audit that result and exact references. E6 must **not**:

- recalculate which lifecycle event E5 should choose;
- turn a stored `close_eligible=true` flag into a lifecycle transition by itself;
- infer provider flatness from persistence absence;
- invent missing Position/Fill/Order/protection evidence;
- overwrite the authoritative lifecycle projection outside existing accepted interfaces.

## Required schema/migration behavior

If the existing SQLite/platform schema requires migration:

- add an E6-owned deterministic migration following current migration conventions;
- preserve all existing rows/schema behavior;
- add unique/foreign/reference constraints where they can mechanically enforce immutable identity without redefining semantic contracts;
- avoid destructive migration or data rewrite;
- restart/migration ordering must be deterministic.

If a physical foreign key cannot represent an external reference safely, use explicit stored ref/hash + repository validation rather than inventing fake rows.

## Required tests to define

Add deterministic E6-owned tests covering at minimum:

- insert/read exact immutable FP-04 record;
- same FP-04 ID + different content rejected;
- insert/read exact immutable FP-10 record;
- same FP-10 ID + different content rejected;
- insert/read E5 reinterpretation decision bound to exact FP-10/lifecycle refs;
- missing FP-04 dependency causes current projection fail closed;
- missing FP-10 dependency causes E5-decision current projection fail closed;
- mismatched evidence hash/reference rejected or degraded;
- superseded FP-10 not selected as current;
- two competing unsuperseded FP-10 heads -> conflict/fail closed, no heuristic selection;
- insertion order does not change deterministic current selection/conflict result;
- restart/reopen preserves history and reconstructs the same current/degraded projection;
- persisted historical `LIFECYCLE_CLOSE_ELIGIBLE` row alone does not imply current/closed;
- persisted E5 `DECISION_CLOSE` with stale/missing referenced FP-10 does not display false green;
- TradeResult-evidence-incomplete flag remains auditable and is not silently cleared;
- no secret/provider-network/runtime dependency.

Use current E6 migration/storage test conventions. Do not execute via GitHub.

## Verification boundary

All executable verification is local-only. The authoritative LF-0 approved-local exact-revision preparation dependency remains blocked.

Therefore, unless an independently approved local execution path is explicitly available to this worker in current authoritative evidence:

```text
project executable verification = NOT_RUN / NOT PASS
```

Record exact Windows/local commands for the relevant bounded storage/platform/migration suites. Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

No provider/network/private API/credential access is needed or authorized:

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

`NOT_RUN` is not PASS.

## Required durable evidence

Create:

`status/e6/FP04_FP10_PERSISTENCE_CURRENTNESS_CONSUMER_20260829.md`

Document:

- task ID;
- exact source/migration/test files changed;
- accepted profiles consumed;
- immutable storage schema/repository behavior;
- current-head/conflict/supersession algorithm;
- restart fail-closed behavior;
- exact E5-decision persistence boundary;
- tests defined;
- local commands and result (`NOT_RUN` if unavailable);
- known limitations / downstream E4/E7 integration needs;
- no provider/credential/runtime/capital authority.

Update `coordination/E6/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E6-owned paths:

- `src/storage/`;
- `src/platform/` only if a minimal current-projection/service surface is required by existing architecture;
- E6-owned migrations under the repository's current migration path;
- `tests/storage/`;
- `tests/platform/` only if directly required;
- `status/e6/FP04_FP10_PERSISTENCE_CURRENTNESS_CONSUMER_20260829.md`;
- `coordination/E6/STATUS.md`.

Do not modify:

- `contracts/**`;
- E4/E5/E7 implementation or docs;
- risk/Position lifecycle policy;
- provider adapter/broker code;
- AgentBridge/local action catalog;
- provider credentials/config/private allowlists;
- Product Owner authorization artifacts;
- risk limits/leverage/capital thresholds;
- release criteria;
- GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if the bounded implementation/test definitions are complete **and** all required executable verification was actually performed on an approved local environment with PASS evidence.

### PARTIAL

Use PARTIAL when source/migration/test implementation is complete but executable verification remains `NOT_RUN`, or when a precise shared-contract dependency prevents complete safe implementation without inventing semantics.

### BLOCKED

Use BLOCKED only if authoritative repository requirements are contradictory or implementation cannot safely proceed within E6 scope.

## Completion

Read latest `main`, verify wake task ID `E6-20260829-026`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start E4 provider work, E5 risk/lifecycle changes, E7 integration/requalification, exact-revision preparation, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
