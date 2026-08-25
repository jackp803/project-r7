# E6 Current Task

- task_id: `E6-20260825-024`
- issued_at: `2026-08-25T17:42:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-c-storage-export-compat-20260825`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B qualification, accepted E6 Gate C Phase-1 PR #77 merge `64eb6f6689cb6f3e2d067af029df36ac58f4a321`, accepted Gate C Phase-3 PR #81 merge `9b3370cbf29ce47abe048cc18860cc89b5fd532d`, failed credential-free qualification evidence PR #82, recovered exact storage failure evidence PR #83 merge `6461cfbed70f4d74910a36b5646b0557306d67a8`, Product Owner Gate C / SHADOW-only authorization

## Objective

Remediate only the E6-owned storage public-export compatibility regression exposed by the exact-revision Gate C credential-free qualification.

Authoritative executable failure recovered from `E7-20260825-069` / `E7-20260825-070`:

```text
suite      = tests/storage
result     = FAIL / 87 tests / exit 1
failure    = PublicPersistenceBoundaryTests.test_supported_storage_surface_exports_only_safe_factory
location   = tests/storage/test_public_persistence_boundary.py:131
assertion  = storage.__all__ == ["open_sqlite_platform"]
observed   = storage.__all__ additionally contains OperationalMode-related symbols
```

The accepted Gate B public persistence boundary remains authoritative and must not be weakened merely to make Gate C pass. E6-022 also required backward compatibility with accepted Gate B persistence.

## Required remediation

1. Preserve the accepted Gate B supported export contract:

```python
storage.__all__ == ["open_sqlite_platform"]
```

Do not change that assertion to accept the regression.

2. Preserve all accepted Gate C OperationalMode/SHADOW implementation semantics from PR #77:
   - durable RESEARCH/PAPER/SHADOW/LIVE/PAUSED/LOCKED distinction;
   - SHADOW transition audit;
   - sanitized Shadow checkpoint;
   - restart/fresh-reconciliation fail-closed behavior;
   - Paper evidence cannot satisfy Shadow truth;
   - Shadow evidence cannot authorize LIVE;
   - no automatic SHADOW -> LIVE;
   - no secret/exact-balance/provider-sensitive durable material.

3. Prefer the smallest E6-only compatibility fix. If possible, restore only the supported `storage.__all__` surface while preserving the existing explicit OperationalMode symbols/factory needed by the already-accepted E7 Shadow composition so that no E7 production change is required.

4. Do not remove or rename OperationalMode implementation APIs currently consumed by accepted E7 code unless unavoidable. If restoring the Gate B export boundary safely requires an E7 integration import/API change, stop `BLOCKED` with exact evidence; do not modify E7-owned code/tests.

5. Do not alter migrations, persistence schema, OperationalMode semantics, risk/execution/provider behavior, or release gates unless strictly required by this export-only regression. No new shared contract/ADR.

## Tests

Use E6-owned tests only. At minimum ensure the definitions cover:

- `storage.__all__` remains exactly `["open_sqlite_platform"]`;
- raw SQLite writer/connection/migration symbols remain unsupported publicly as before;
- OperationalMode/SHADOW persistence, audit, checkpoint, restart, redaction and no-LIVE semantics remain unchanged;
- existing accepted Gate B storage compatibility tests remain intact;
- no weakening/deletion of the failing public-persistence-boundary assertion;
- any explicit OperationalMode import path retained for accepted E7 composition remains resolvable without changing E7 code.

Do not modify E7 integration/E2E/safety tests in this task.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, credential-free verification for this bounded remediation. If the approved local runner is available, run only:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
```

No provider/private network, credentials, PAPER/SHADOW runtime, mutation, order submission or LIVE is authorized. If approved-local execution is unavailable, record `NOT_RUN` with the exact commands. `NOT_RUN != PASS`.

This task is remediation only. Even if local E6 suites PASS, the failed E7-069 full Gate C qualification remains authoritative until PM later issues a separate exact-revision requalification.

## Writable scope

Only E6-owned paths needed for this bounded fix:

- `src/storage/**`;
- `tests/storage/**` only if additional non-weakening regression coverage is needed;
- `tests/platform/**` only if required by the E6 storage boundary;
- bounded E6 docs/status evidence;
- `coordination/E6/STATUS.md`.

Forbidden:

- weakening/deleting the accepted Gate B public persistence boundary test;
- E1-E5/E7 production/tests;
- shared contracts/ADRs;
- provider/network/auth changes;
- risk/execution/strategy changes;
- real credentials/secrets;
- provider/private requests;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- unrelated cleanup.

## Acceptance

### DONE

- the exact storage export regression is remediated within E6 ownership;
- `storage.__all__` is restored to the accepted Gate B supported surface;
- accepted Gate C OperationalMode/SHADOW semantics and existing E7 dependency remain compatible;
- no test assertion is weakened to hide the failure;
- local verification is PASS or explicitly `NOT_RUN` without misclassification;
- commit/push required code/tests/evidence to the target branch and terminal STATUS.

### BLOCKED

Stop if a correct fix requires changing E7-owned composition/API usage or a shared contract/architecture decision. Persist exact evidence and do not broaden scope.

## Completion

Execute only this TASK, update `coordination/E6/STATUS.md`, commit/push required work to the target branch, and stop on DONE, PARTIAL, BLOCKED or HOLD acknowledgement. Do not self-start Gate C requalification, provider verification, SHADOW runtime, Gate D or LIVE work.