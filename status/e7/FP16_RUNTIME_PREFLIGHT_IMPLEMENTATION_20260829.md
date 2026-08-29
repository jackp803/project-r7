# FP-16 Runtime Preflight Implementation — E7-112 / E7-113 / E7-114

## Authority / classification

- current task: `E7-20260829-114`
- branch: `agent/e7-fp16-runtime-preflight-implementation-20260829`
- accepted profile: `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md` / `runtime-preflight-v0.1` / unchanged
- governing PM review: `status/PM_E7_113_REVIEW_20260829.md`
- implementation classification: `IMPLEMENTED_UNQUALIFIED / STATIC CANDIDATE`
- project executable verification: `NOT_RUN / NOT_PASS`
- FP-16 runtime-preflight tests: `NOT_RUN / NOT_PASS`
- LF-0: `BLOCKED / UNCHANGED`

E7-114 is governance/test-layout remediation only. It preserves the accepted E7-113 production source semantics and removes the E7-113 writable-scope violation. It creates no provider, process, runtime, order, Product Owner, release, or capital authority.

## Preserved source semantics

`src/integration/runtime_preflight.py` is unchanged by E7-114.

The E7-113 external-participation rule remains:

```text
external participation required
  = fixed unconditional role requirement
 OR supervisor_present
 OR external_consumer_authority is non-null
```

Therefore external-consumer evidence is required when:

1. the runtime role has the fixed unconditional requirement (`SHADOW_RUNTIME` or `BOUNDED_LIVE_FIRE_RUNTIME`);
2. a supervisor materially participates; or
3. caller-supplied current `RuntimePreflightAuthority.external_consumer_authority` is non-null.

When participation is required but matching `external_consumer_evidence` is absent, the existing accepted reason remains:

```text
PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED
```

When external evidence is present, the existing exact ID/generation/config/profile/evidence-hash/status/timestamp checks against current supplied authority remain unchanged. Evidence without current matching authority remains fail closed. No new reason code, field, role, mode, authority type, or shared-contract version is introduced.

## E7-114 governance/test-layout remediation

The PM accepted E7-113 source semantics but rejected merge because E7-113 created an unauthorized extra test file outside its exact writable list.

E7-114 corrects only that layout issue:

- preserves `src/integration/runtime_preflight.py` unchanged;
- consolidates the E7-113 external-consumer regression definitions into the already authorized existing module `tests/integration/test_runtime_preflight.py`;
- deletes `tests/integration/test_runtime_preflight_external_consumer_regression.py`;
- updates this handoff and the qualification manifest so no future command/reference targets the deleted file.

`tests/safety/test_p0_integrated_fail_closed.py` remains unchanged. The P0 matrix remains unchanged because it contained no stale reference to the deleted standalone regression module.

## Regression definitions now contained in the existing integration module

`tests/integration/test_runtime_preflight.py` now contains the existing FP-16 suite plus the consolidated external-consumer participation regressions covering at minimum:

1. credential-free + no supervisor + non-null current external authority + missing external evidence -> `FAIL_CLOSED / PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`;
2. provider-read-only with the same mismatch -> fail closed;
3. credential-free true no-external case -> `ELIGIBLE` only when both input evidence and current authority represent no external consumer and all other synthetic facts are coherent;
4. exact current external evidence + exact current external authority -> admissible when all other facts are coherent;
5. external evidence without current authority -> fail closed;
6. stale/mismatched external generation -> fail closed;
7. incompatible external status -> fail closed;
8. SHADOW missing external evidence -> unconditional fail closed remains intact;
9. regression paths create no provider/network/credential/process/order/runtime/capital authority fields.

Existing deterministic identity/currentness, role isolation, revision/worktree, OperationalMode, heartbeat, supervisor/restart, capability/allowlist, reconciliation, dependency, authorization, bounded-live-fire undefined-mode-policy, and no-authority-side-effect definitions remain in the same module.

## Pure evaluator / authority boundary

The FP-16 evaluator remains pure and provider-neutral. It performs no:

- network/provider I/O;
- private API access;
- credential access;
- process launch or restart;
- provider/account mutation;
- order/protection submit/cancel/amend/close;
- SHADOW/PAPER/live runtime start;
- capital movement or exposure.

`ELIGIBLE` remains admission evidence only and is not provider authority, process-launch authority, restart execution, order authority, SHADOW/PAPER authority, bounded-live-fire authority, Gate D, LIVE, or capital authorization.

## Verification boundary

E7-114 executes no project code or tests. LF-0 approved-local exact-revision preparation remains blocked.

```text
project executable verification = NOT_RUN / NOT_PASS
FP-16 runtime-preflight tests = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
process launch/restart = 0
order/protection actions = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not PASS.

## Exact future approved-local commands

Only after a future merged candidate is bound to an exact revision, approved-local infrastructure establishes that same revision as `EXACT_CLEAN`, and a fresh execution task authorizes qualification:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests/integration -p 'test_runtime_preflight.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
```

The external-consumer regressions are part of `test_runtime_preflight.py`; there is no separate regression-module command.

Then execute the focused P0 sequence and full 14-suite credential-free matrix recorded in `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` on the same exact clean approved-local revision. Actual counts/results must be measured then; historical PASS/counts must not be rebound.

## Remaining dependencies

- FP-16 remains `IMPLEMENTED_UNQUALIFIED / NOT_RUN / NOT_PASS` until approved-local exact-revision execution succeeds.
- LF-0 exact-revision preparation infrastructure remains blocked and unchanged.
- E7-101 request/job identities remain terminal and non-reusable.
- FP-02 provider-native close/protection facts remain unresolved/fail closed.
- AgentBridge/operator launcher/supervisor production enforcement remains external and unchanged.
- provider read-only requires future Product Owner authority.
- SHADOW/PAPER remain unauthorized.
- bounded 10U live-fire remains unauthorized.
- Gate D / recurring LIVE remain blocked/unauthorized.
