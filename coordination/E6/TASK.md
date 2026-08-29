# E6 Current Task

- task_id: `E6-20260829-029`
- issued_at: `2026-08-29T18:55:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-fp11-persistence-currentness-20260829`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, accepted `protection-registry-multiplicity-v0.1`, merged E4 FP-11 producer static candidate, merged E5 FP-11 policy consumer static candidate, `status/PM_E6_028_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Remediate the bounded E6-owned FP-11 restart/currentness **hash-domain mismatch** identified by PM review of E6-20260829-028, without expanding scope.

Continue the existing unmerged branch `agent/e6-fp11-persistence-currentness-20260829`. Bring in latest `main` non-destructively as needed; do not force-push/rewrite history. Preserve the E6-028 implementation except for the minimum correction and regression definitions required by this task.

The defect is precise: existing `_PaperRuntimeStore.persist_position_projection()` stores the canonical **lifecycle projection payload hash** in `paper_position_lifecycle_projections.payload_hash` and `paper_position_current_projection.payload_hash`, while E6-028 `recover()` compares those storage hashes to the canonical **Position hash**. These are distinct evidence domains and must remain distinct.

No provider/network/credential/runtime/live authority is granted.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E6_PLATFORM.md`;
- `status/PM_E6_028_REVIEW_20260829.md`;
- `src/storage/_paper_runtime.py`, specifically normal `persist_position_projection()` hash/index semantics;
- `src/storage/migrations/0002_paper_runtime_durability.sql`;
- current branch `src/storage/protection_registry_currentness.py` and its tests/handoff;
- accepted position lifecycle projection/execution-binding profiles;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required remediation

Within E6-owned storage/test paths only:

1. keep canonical Position hash and canonical lifecycle-projection payload hash as separate values;
2. derive/validate the exact current lifecycle projection canonical payload hash from the supplied current lifecycle projection;
3. require `paper_position_current_projection` to match the exact current projection by at least:
   - `position_id`;
   - `lifecycle_projection_id`;
   - `lifecycle_revision`;
   - `broker_state_observed_at`;
   - lifecycle projection `payload_hash`;
4. require the selected `paper_position_lifecycle_projections` row to have exact canonical `payload_json` and `payload_hash` for the supplied current lifecycle projection;
5. keep FP-11 top-level `position_hash`, intended-lineage `position_hash`, and E5 interpretation `position_hash` bound to the canonical Position hash only;
6. do not weaken any existing FP-11 exact Position/lifecycle/binding/provider-set/runtime reference/currentness checks;
7. preserve append-only evidence, explicit supersession-chain selection, competing-head failure, FP-04 dependency checks, E5 decision binding, terminal-flat FP-10 dependency and false-green prevention;
8. keep `provider_mutation_authorized = false` and `cleanup_target_ref = null` mechanically enforced.

Do not solve the mismatch by changing existing `_PaperRuntimeStore.persist_position_projection()` semantics, migration-0002 semantics, lifecycle contracts, or Position hashing semantics. The FP-11 E6 consumer must integrate with the existing authoritative writer.

## Required regression tests to define

Add/adjust E6-owned deterministic tests covering at minimum:

- normal lifecycle projection persisted through the existing `_PaperRuntimeStore.persist_position_projection()` writer is accepted by FP-11 restart/currentness when all other exact current evidence matches;
- lifecycle projection payload hash is not compared to canonical Position hash;
- corrupted/mismatched `paper_position_current_projection.payload_hash` fails closed;
- corrupted/mismatched durable lifecycle projection `payload_json`/`payload_hash` fails closed;
- current projection ID/revision/broker observation mismatch fails closed;
- canonical Position hash mismatch still independently invalidates FP-11/E5 currentness;
- healthy FP-11 read model remains possible only with exact converged FP-11 + exact current E5 interpretation + exact current Position/lifecycle/FP-04/provider-set/runtime dependencies;
- flat/CLOSED with unresolved protection remains reconciliation-required;
- no provider/network/credentials/mutation dependency.

Prefer exercising the real existing E6 persistence writer rather than manually inserting a current projection row with invented hash semantics.

Do not execute tests through GitHub.

## Verification boundary

All executable verification remains local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless an independently approved local exact-revision execution path is explicitly present in current repository evidence:

```text
project executable verification = NOT_RUN / NOT_PASS
```

Record exact future Windows/local commands for the corrected FP-11 storage tests and relevant existing storage/runtime/FP-11 regressions. `NOT_RUN` is not PASS.

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
protection query/create/cancel/amend/replace = 0
order actions = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 = BLOCKED / UNCHANGED
LF-2 = NOT PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

## Required durable evidence

Create:

`status/e6/FP11_PROJECTION_HASH_DOMAIN_REMEDIATION_20260829.md`

Also update the existing E6-028 handoff if necessary so it no longer describes the defective hash comparison as accepted behavior.

Document the exact defect, corrected hash domains, files changed, regression definitions, exact future local commands/result, and authority/gate state.

Update `coordination/E6/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E6-owned paths:

- `src/storage/protection_registry_currentness.py`;
- `tests/storage/test_protection_registry_currentness.py`;
- `status/e6/FP11_PERSISTENCE_CURRENTNESS_RESTART_20260829.md` only if correction is needed;
- `status/e6/FP11_PROJECTION_HASH_DOMAIN_REMEDIATION_20260829.md`;
- `coordination/E6/STATUS.md`.

Do not modify `contracts/**`, migration-0002 semantics, E4/E5/E7 implementation/docs, provider transport/auth/config/credentials, AgentBridge/local action catalog, provider allowlists, Product Owner authorization artifacts, risk/lifecycle policy, release criteria, leverage/capital thresholds, or GitHub Actions/CI files.

## Result classification

### DONE
Use DONE only if remediation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL
Use PARTIAL if the static remediation and regression definitions are complete but executable verification remains `NOT_RUN / NOT_PASS`.

### BLOCKED
Use BLOCKED only if an authoritative contradiction prevents correcting the integration within E6 scope. If a shared semantic truly must change, record the precise dependency instead of inventing one.

## Completion

Read latest `main`, verify wake task ID `E6-20260829-029`, execute only this remediation task, persist evidence, update STATUS, commit/push the existing target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start E7 integration/requalification, exact-revision preparation, provider verification, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
