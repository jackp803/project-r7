# E4 Current Task

- task_id: `E4-20260830-037`
- issued_at: `2026-08-30T16:47:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-canonical-position-import-convergence-20260830`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted E7 canonical import architecture from merged PR #126, accepted E6 FP-11 timestamp remediation from merged PR #127, accepted E4 FP-02 reason aggregation from merged PR #128, closed-unmerged E4 canonical import PR #129, and approved-local qualification defect evidence for exact historical failing revision `bacb5205ac9b895bb968459f88f148323bcc5da6`

## Objective

Perform the smallest E4-only convergence needed to place the already accepted canonical Position import normalization onto the latest `main` **without overwriting or reverting the already-merged FP-02 reason-aggregation remediation or its STATUS/evidence**.

This is a merge-conflict/convergence task, not new feature work and not new architecture work.

The accepted canonical runtime namespace under `$env:PYTHONPATH='src'` is:

```text
src/<package> -> <package>.*
Position domain -> position.*
forbidden duplicate namespace -> src.position.*
```

## Starting point

Read latest `main` first. It must include merged PRs:

- `#126` E7 canonical Python import identity remediation;
- `#127` E6 FP-11 timestamp normalization remediation;
- `#128` E4 FP-02 reason aggregation remediation.

Do not reset or replace latest main with the old import-normalization branch.

Old accepted-but-conflicting branch / PR:

```text
branch = agent/e4-canonical-position-import-normalization-20260830
head = 3ef910c5bb98cf15a55d341a031ea4cca9f8a133
PR = #129 / CLOSED / NOT_MERGED
```

PR #129 was closed only because both E4 remediation branches replaced `coordination/E4/STATUS.md`; its production import patch was statically accepted.

## Exact production convergence

On a fresh branch from latest `main`, mechanically apply only the accepted import namespace normalization to these E4-owned production files:

```text
src/execution/protection_trigger.py
src/execution/external_close_evidence.py
src/execution/protection_registry_evidence.py
```

Required spelling change is only equivalent imports from:

```text
src.position.*
```

to:

```text
position.*
```

Do not alter functions, validators, type checks, reason codes, lifecycle semantics, provider semantics, authority validation, or financial behavior.

## Required regression definition

Carry forward the accepted E4 regression definition from the old branch:

```text
tests/execution/test_canonical_position_import_identity.py
```

The test must preserve strict identity expectations and genuine wrong-type rejection. Do not modify E7-owned `tests/integration/test_canonical_import_identity.py`.

## Preserve merged FP-02 remediation

The latest main contains accepted FP-02 reason aggregation. You must preserve exactly the merged semantics in:

```text
src/brokers/okx_action_capability.py
tests/brokers/test_okx_action_capability.py
status/e4/FP02_REASON_AGGREGATION_REMEDIATION_20260830.md
```

Do not modify or revert these paths unless a literal merge operation requires no-content-change metadata resolution; source/test content must remain identical to latest main.

`coordination/E4/STATUS.md` must describe the current convergence task and explicitly state that FP-02 reason aggregation remains merged/preserved.

## Writable scope

Only:

- `src/execution/protection_trigger.py`
- `src/execution/external_close_evidence.py`
- `src/execution/protection_registry_evidence.py`
- `tests/execution/test_canonical_position_import_identity.py`
- `status/e4/CANONICAL_POSITION_IMPORT_NORMALIZATION_20260830.md` (carry forward/update only if needed to identify converged main ancestry)
- `coordination/E4/STATUS.md`

Do not modify E4 FP-02 source/tests, E5/E6 production, E7 architecture/tests/contracts, provider/auth/config, AgentBridge, risk/capital policy, or CI.

## Verification

If an approved-local Windows execution surface is available, run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/execution -p 'test_canonical_position_import_identity.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_trigger_consumer.py' -v
python -m unittest discover -s tests/execution -p 'test_external_close_evidence.py' -v
python -m unittest discover -s tests/execution -p 'test_protection_registry_evidence.py' -v
python -m unittest discover -s tests/integration -p 'test_canonical_import_identity.py' -v
```

If approved-local execution is unavailable, record `NOT_RUN / NOT_PASS` and the exact commands. Do not use GitHub Actions/CI/hosted runners.

## Safety boundary

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process/runtime launch = 0
SHADOW/PAPER/LIVE = NOT_STARTED / NOT_AUTHORIZED
capital exposure = NONE
GitHub compute = NOT_USED
```

## Completion

1. Verify wake task ID exactly `E4-20260830-037`.
2. Start from latest main, not the old PR branch.
3. Apply only the accepted import normalization + E4 regression definition.
4. Preserve merged FP-02 reason aggregation unchanged.
5. Update `coordination/E4/STATUS.md`.
6. Commit and push `agent/e4-canonical-position-import-convergence-20260830`.
7. Stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Expected terminal state is `PARTIAL` if executable regression remains `NOT_RUN / NOT_PASS`; do not claim PASS without approved-local execution.

Do not self-start integrated qualification, provider verification, SHADOW/PAPER, bounded live fire, Gate D, LIVE, or capital work.
