# E4 Current Task

- task_id: `E4-20260829-026`
- issued_at: `2026-08-29T15:11:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp02-swap-action-role-capability-design-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, `status/PM_E7_103_REVIEW_20260829.md`, accepted mature-OKX failure-prevention baseline/audit

## Objective

Define the **FP-02 OKX SWAP action-role capability vocabulary/table** as an E4-owned design artifact so later executable provider translation can be implemented fail closed without transplanting Spot semantics or inventing provider parameters at runtime.

This is a docs/status-only E4 task. It does not authorize executable source/test changes, provider/private API access, credentials, provider/account mutation, order submission, SHADOW/PAPER runtime, capital exposure, 10U live-fire, Gate D, or LIVE.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- accepted `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- current shared Order/Fill/Position/protection/execution-evidence contracts relevant to action roles;
- current E4 OKX provider adapter/config/sizing/read-only code and E4-owned tests only as design evidence;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-02 row;
- `status/PM_E7_103_REVIEW_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required design artifact

Create:

`docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`

Use profile identifier:

`okx-swap-action-role-capability-v0.1`

The artifact must define a deterministic, fail-closed capability matrix for the currently supported provider target:

```text
provider = OKX API V5
canonical instrument = BTC_USDT_PERP
provider instrument = BTC-USDT-SWAP
margin mode baseline = isolated where current accepted provider semantics require it
account/position modes = only modes explicitly supported by current repository evidence; unsupported/unknown combinations fail closed
```

Do not claim current provider/private verification for the new matrix.

## Required action roles

At minimum classify these roles independently:

- `ENTRY`
- `PROTECTION_STOP`
- `POSITION_EXIT`
- `EMERGENCY_EXIT`
- `READ_ONLY_RECONCILIATION`

For every role, define:

1. purpose and required upstream authority;
2. allowed provider operation class (`GET` observation vs future mutation category only as design vocabulary);
3. canonical side/direction semantics;
4. position-mode assumptions (`net_mode`, any retained `long_short_mode`, or explicit unsupported state);
5. margin-mode requirements;
6. quantity source and unit expectations;
7. reduce-only applicability/forbidden/unknown semantics;
8. position-side/provider-side fields if applicable;
9. trigger/order-type/provider-native fields that are required, forbidden, or explicitly unresolved;
10. idempotency/client-order identity requirements;
11. reconciliation/readback requirements after ambiguous outcomes;
12. exact fail-closed reason for unsupported/unknown combinations;
13. dependency on FP-03 trigger-validity evidence for protection;
14. dependency on future FP-05 residual/close sizing for exit roles;
15. dependency on future FP-11 protection registry for protection multiplicity/readback.

Do not make a generic shared `reduce_only` flag equivalent to proven provider compatibility.

## Required matrix semantics

The matrix must explicitly prevent these mature-bot failure classes:

- Spot `tdMode=cash` semantics transplanted to SWAP;
- account/position mode guessed from configuration rather than proven/declared capability;
- `PROTECTION_STOP` using entry-side/provider fields by analogy;
- `POSITION_EXIT`/`EMERGENCY_EXIT` using requested entry quantity instead of authoritative reducible exposure;
- provider-native trigger basis inferred from shared `LAST_PRICE` FP-03 evidence;
- unknown provider field/value combinations silently omitted or defaulted;
- caller booleans/mappings manufacturing capability authority;
- mutation prepared when account/instrument/margin/position-mode capability facts are unknown.

## Deterministic implementation/test plan

Document the smallest later E4 executable implementation boundary and required credential-free tests, including at minimum:

- each action role maps only through an accepted capability row;
- unknown account level / position mode / margin mode fails closed;
- unsupported field combinations fail closed before provider dispatch;
- Spot-only values are rejected;
- protection cannot infer provider trigger basis from shared LAST_PRICE;
- exit/emergency exit cannot execute until FP-05 supplies authoritative provider-native reducible sizing semantics;
- no arbitrary caller assertion can create capability PASS;
- read-only reconciliation remains GET-only/default-deny;
- existing no-submit/no-mutation boundaries remain unchanged until separately authorized;
- deterministic fixtures require no provider network or credentials.

Do not implement these executable changes in this task.

## Shared-contract boundary

E4 may define E4-owned provider capability vocabulary/design under `docs/execution/**`, but must not modify `contracts/**` or redefine E5/E7 semantics.

If the capability design proves a new shared cross-module field/profile is necessary, record a precise E7 change request in the handoff and stop at design completion. Do not invent the shared contract.

## Required durable evidence

Create:

`status/e4/FP02_OKX_SWAP_ACTION_ROLE_CAPABILITY_DESIGN_20260829.md`

Record:

- task ID;
- design profile/version;
- current provider/instrument baseline used;
- complete role/capability table;
- unresolved provider-specific facts, if any;
- exact shared-contract dependency/proposal, if any;
- future deterministic implementation paths and test plan;
- relationship to FP-05 and FP-11;
- executable verification = `NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK`;
- provider requests = 0;
- credentials = NONE;
- mutation/order actions = 0;
- SHADOW/PAPER/live-fire runtime = NOT_STARTED;
- capital exposure = NONE;
- GitHub compute = NOT_USED.

Update `coordination/E4/STATUS.md` and commit/push the target branch.

## Verification boundary

This task executes no project code/tests:

```text
project executable verification = NOT_RUN / NOT REQUIRED
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER = NOT_STARTED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.

## Writable scope

Only:

- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`;
- `status/e4/FP02_OKX_SWAP_ACTION_ROLE_CAPABILITY_DESIGN_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not modify executable source/tests, `contracts/**`, other workers' files, provider credentials/config/private allowlists, AgentBridge/local action catalog, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or release criteria.

## Result classification

### DONE

Use DONE only if the FP-02 design matrix is complete, internally consistent with accepted E4/E7 semantics, explicitly fail closed on unknown/unsupported combinations, and contains a bounded deterministic implementation/test handoff without granting provider/runtime authority.

### PARTIAL

Use PARTIAL if a bounded provider/shared-contract ambiguity prevents a deterministic row from being defined. Record the exact ambiguity and required E7 dependency; do not guess provider semantics.

### BLOCKED

Use BLOCKED only if authoritative repository evidence is contradictory or insufficient to define a safe design even with explicit unresolved/fail-closed rows.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-026`, execute only this docs-only task, persist evidence, update STATUS, commit/push to the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start executable FP-02 implementation, FP-05, FP-11, provider verification, exact-revision preparation, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
