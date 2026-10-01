# E7 Current Task

- task_id: `E7-20261001-118`
- issued_at: `2026-10-01T14:08:00+08:00`
- state: `ACTIVE`
- task_type: `P0 CREDENTIAL-FREE REMEDIATION REQUALIFICATION`
- qualification_revision: `782c886c73ec21ea3b2e2a782fd9c5947056317d`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `status/P0_REMEDIATION_EXACT_CLEAN_PREPARATION_20261001.md`, `status/P0_CREDENTIAL_FREE_REMEDIATION_REQUALIFICATION_BLOCKER_20260830.md`, `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`

## Objective

Execute and adjudicate the complete approved-local credential-free P0 remediation requalification for exact executable revision:

```text
782c886c73ec21ea3b2e2a782fd9c5947056317d
```

The exact-clean precondition is now satisfied by PM-accepted approved-local operator evidence.

This task is qualification only. It is not feature development, provider verification, runtime enablement, or live authorization.

## Mandatory first reads

Read latest authoritative `main` first, then read:

1. `README.md`
2. `agents/README.md`
3. `agents/E7_INTEGRATION.md`
4. only this E7 TASK
5. `status/P0_REMEDIATION_EXACT_CLEAN_PREPARATION_20261001.md`
6. `status/P0_CREDENTIAL_FREE_REMEDIATION_REQUALIFICATION_BLOCKER_20260830.md`
7. `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`
8. relevant current E7 qualification/status artifacts referenced by the manifest

Do not execute another Agent's TASK mailbox.

Before execution, verify this task ID exactly equals `E7-20261001-118`.

## Exact revision binding

All executable qualification commands must run against the already prepared approved-local Windows worktree whose:

```text
HEAD = 782c886c73ec21ea3b2e2a782fd9c5947056317d
WORKTREE = CLEAN
```

Recheck before testing:

```powershell
git rev-parse HEAD
git status --porcelain
git diff --exit-code
git diff --cached --exit-code
```

If any exact-revision or clean-worktree condition is no longer true:

`BLOCKED`

Do not switch to latest `main`, another branch, another SHA, or a locally modified candidate.

## Qualification sequence

Use `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` as the command authority.

### Phase 1

Run the complete focused P0 deterministic sequence in the manifest, in order, on the same exact revision and environment.

Record actual per-command:

- command/module identity;
- tests run;
- passed;
- failed;
- errors;
- skipped;
- exit code;
- time boundary/duration where available.

Every Phase 1 command must exit 0 for Phase 1 PASS.

If any Phase 1 command fails or errors:

- record all evidence already produced;
- classify qualification `FAIL / NOT_PASS`;
- do not infer PASS from unaffected modules;
- do not start provider/runtime/capital stages;
- follow the manifest's Phase-2 admission rule.

### Phase 2

Only if Phase 1 satisfies the manifest's admission requirement, run the complete current 14-suite matrix exactly as defined by the manifest on the same exact revision/worktree/environment.

Final credential-free PASS requires:

```text
all Phase 1 focused commands PASS
14 / 14 full suite directories PASS
same exact revision for every command
same approved-local clean worktree
actual measured counts
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW/PAPER/live runtime = NOT_STARTED
capital exposure = NONE
GitHub compute = NOT_USED
```

Do not reuse historical counts.

## Remediation-specific expectations

This run must actually exercise the merged remediation surfaces, including:

- E4 FP-02 deterministic complete reason aggregation while preserving state precedence/provenance fail-closed semantics;
- E6 FP-11 canonical storage timestamp comparison without weakening stale/conflict detection;
- canonical Python import identity under `PYTHONPATH=src`, including strict genuine wrong-type rejection;
- existing FP-03/04/05/10/11/16 composition and fail-closed behavior.

Passing only `storage`, `integration`, `e2e` and `safety` is insufficient.

## No project mutation during qualification

Do not modify executable candidate source/tests/contracts to make qualification pass.

If a deterministic defect is discovered:

1. preserve the failing evidence;
2. classify `FAIL / NOT_PASS`;
3. identify exact failing module/test/root-cause evidence if determinable;
4. stop qualification according to the manifest;
5. return control to PM for a new bounded remediation task.

Do not patch the qualification worktree.

## Durable evidence

Persist sanitized E7 qualification evidence on an E7-owned branch based on latest `main`, without changing the executable candidate.

Recommended branch:

`agent/e7-p0-remediation-requalification-20261001`

Allowed writes:

- `coordination/E7/STATUS.md`
- `status/e7/P0_REMEDIATION_REQUALIFICATION_20261001.md`
- only additional E7-owned qualification evidence artifacts if strictly necessary

Do not persist:

- local filesystem paths;
- secrets;
- provider tokens/signatures/cookies;
- unrelated shell history;
- private balances.

The durable result must explicitly bind every executable result to exact revision `782c886c73ec21ea3b2e2a782fd9c5947056317d`.

## Safety boundary

```text
GitHub Actions/CI/hosted/GitHub-triggered compute = FORBIDDEN
provider/private API = FORBIDDEN
credentials read/requested/used = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW = NOT_STARTED / NOT_AUTHORIZED
PAPER = NOT_STARTED / NOT_AUTHORIZED
bounded live fire = NOT_AUTHORIZED
Gate D = BLOCKED / NOT_AUTHORIZED
LIVE = UNAUTHORIZED
capital exposure = NONE
```

This task grants no authority beyond deterministic credential-free qualification.

## Terminal classification

`DONE` only if the complete manifest-qualified run passes and durable evidence is committed/pushed.

`PARTIAL` if execution occurred but the complete PASS condition is not established.

`BLOCKED` if exact revision/environment/qualification infrastructure prevents execution.

`NOT_RUN != PASS`.

## Completion

On terminal state:

1. update `coordination/E7/STATUS.md`;
2. persist sanitized qualification evidence;
3. commit and push the E7 evidence branch;
4. stop.

Do not self-start LF-3, provider read-only verification, SHADOW/PAPER, bounded live fire, Gate D, LIVE, provider mutation, order action, or capital movement.
