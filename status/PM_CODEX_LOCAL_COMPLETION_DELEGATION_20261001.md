# PM Codex Local Completion Delegation — 2026-10-01

## Authority

Product Owner has explicitly delegated the local execution/remediation portion of project-r7 to Codex because the E7 chat execution surface is unavailable.

This delegation does **not** change architecture ownership, provider authority, capital authority, or live-release authority.

ChatGPT PM remains responsible for architecture/release adjudication and Git acceptance.
Codex is the local execution + bounded remediation engineer.

## Current executable candidate

```text
repository = jackp803/project-r7
current credential-free executable candidate = 782c886c73ec21ea3b2e2a782fd9c5947056317d
exact-clean = ESTABLISHED
exact-clean evidence = status/P0_REMEDIATION_EXACT_CLEAN_PREPARATION_20261001.md
qualification = NOT_RUN / NOT_PASS
```

## Codex mission

Drive the project through the complete credential-free deterministic qualification and remediation loop until one of the following terminal outcomes occurs:

1. COMPLETE_CREDENTIAL_FREE_PASS
2. ARCHITECTURE_OR_AUTHORITY_BLOCKED
3. EXTERNAL_PROVIDER_OR_CAPITAL_AUTHORITY_REQUIRED

Codex may:

- execute the complete credential-free qualification locally on Product-Owner-approved Windows;
- diagnose deterministic project defects;
- implement minimal fixes within existing accepted architecture/contracts;
- add or update regression tests inside the owning domain;
- create bounded codex remediation branches;
- commit and push remediation/evidence branches;
- re-run focused and full qualification after each deterministic fix;
- repeat until the complete credential-free qualification is green.

Codex must not silently redefine shared contracts or accepted architecture. If a true contract/architecture change is required, stop with ARCHITECTURE_OR_AUTHORITY_BLOCKED and return the exact conflict to PM.

## Qualification authority

Initial qualification must use:

`status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`

and exact revision:

`782c886c73ec21ea3b2e2a782fd9c5947056317d`

If the initial candidate fails and Codex changes executable code/tests:

- the old qualification result becomes historical;
- create a new committed executable candidate on a bounded branch;
- establish exact HEAD + CLEAN for that new candidate locally;
- run affected focused regressions;
- then run the complete Phase 1 manifest sequence;
- only if Phase 1 passes, run the complete 14-suite Phase 2 matrix;
- do not claim PASS from partial reruns.

## Existing architecture/safety invariants

Preserve:

- FP-02/03/04/05/10/11/16 accepted contracts and fail-closed semantics;
- canonical Python runtime namespace under PYTHONPATH=src;
- strict authority/type validation;
- E4 provider-native unresolved roles remain fail closed unless separately provider-qualified;
- E5 risk veto and lifecycle semantics;
- E6 currentness/persistence immutability rules;
- NOT_RUN != PASS;
- historical evidence is non-transferable across executable revisions.

## Prohibited without fresh Product Owner authority

```text
provider/private API
credentials
account mutation
order submission/cancel/amend/close/protection mutation
runtime trading process
SHADOW
PAPER
bounded live fire
Gate D
LIVE
capital exposure
GitHub Actions / hosted / GitHub-triggered compute
```

Do not ask for or inspect exchange credentials during credential-free completion.

## Completion definition for this delegation

`COMPLETE_CREDENTIAL_FREE_PASS` requires one exact committed executable revision with:

```text
Phase 1 = all focused commands PASS
Phase 2 = 14/14 suite directories PASS
same exact revision for all commands
clean approved-local Windows worktree
actual measured counts
provider requests = 0
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process/runtime launch = 0
SHADOW/PAPER/LIVE = NOT_STARTED
capital exposure = NONE
GitHub compute = NOT_USED
```

Codex must persist sanitized evidence and push the final branch.

Do not merge to main unless an explicit PM/Git task authorizes merge. Return the final passing branch/SHA to PM for acceptance.

## Project-completion boundary

This delegation completes the currently authorized **credential-free deterministic project stage**.

Provider qualification, runtime stages, SHADOW/PAPER, bounded live fire, Gate D and LIVE are later separately gated stages and are not authorized by this delegation.
