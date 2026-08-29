# FP-16 Runtime Preflight Implementation — E7-20260829-112 + E7-20260829-113 remediation

## Authority / classification

- current remediation task: `E7-20260829-113`
- predecessor implementation task: `E7-20260829-112`
- branch: `agent/e7-fp16-runtime-preflight-implementation-20260829`
- accepted profile consumed unchanged: `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md` / `runtime-preflight-v0.1`
- PM review requiring remediation: `status/PM_E7_112_REVIEW_20260829.md`
- implementation classification: `IMPLEMENTED_UNQUALIFIED / REMEDIATED STATIC CANDIDATE`
- project executable verification: `NOT_RUN / NOT_PASS`
- FP-16 runtime-preflight tests: `NOT_RUN / NOT_PASS`
- LF-0: `BLOCKED / UNCHANGED`

This artifact supersedes only the E7-112 branch handoff interpretation for the PM-identified external-consumer participation defect. It does not change the accepted shared contract and creates no provider, process, runtime, order, Product Owner, or capital authority.

## E7-113 defect diagnosis

Accepted `runtime-preflight-v0.1` allows `external_consumer_evidence=null` only when the declared role proves that no external orchestrator materially participates.

The E7-112 evaluator previously computed material external participation from only:

```text
fixed unconditional role requirement OR supervisor_present
```

It did not include non-null caller-supplied `RuntimePreflightAuthority.external_consumer_authority` as a material participation fact. For conditional roles such as `CREDENTIAL_FREE_LOCAL_VERIFICATION` and `PROVIDER_READ_ONLY_OBSERVATION`, current external authority could therefore coexist with missing input external-consumer evidence without necessarily emitting `PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`.

PM classified that behavior as fail open. E7-113 changes only that participation predicate.

## Corrected external-consumer rule

The evaluator now requires external-consumer evidence when **any** of the following is true:

1. `runtime_role` is an accepted unconditional external-consumer role (`SHADOW_RUNTIME` or `BOUNDED_LIVE_FIRE_RUNTIME`);
2. `supervisor_present == true`;
3. caller-supplied current `external_consumer_authority` is non-null.

Equivalent implementation boundary:

```text
external participation required
  = fixed role requirement
 OR supervisor participation
 OR non-null current external-consumer authority
```

When participation is required and `external_consumer_evidence` is missing, the accepted existing reason is emitted:

```text
PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED
```

No new reason code, field, role, mode, authority type, or contract version is introduced.

When input external evidence is present, the pre-existing exact checks remain unchanged:

- exact external-consumer ID;
- exact generation ID;
- exact config hash;
- exact compatibility profile ref;
- exact compatibility evidence hash;
- `compatibility_status == ACCEPTED`;
- compatibility timestamp not later than evaluation time.

Evidence present with absent or mismatching current external authority remains fail closed because the exact comparison is against no/mismatching current authority. Historical or unsupported external-consumer evidence cannot become admissible by itself.

## Pure evaluator / no-authority boundary preserved

`src/integration/runtime_preflight.py` remains a pure provider-neutral admission-evidence interpreter over caller-supplied sanitized facts.

It performs no:

- network/provider I/O;
- private API access;
- credential access;
- process launch or restart;
- provider/account mutation;
- order/protection submit/cancel/amend/close;
- SHADOW/PAPER/live runtime start;
- capital movement or exposure.

`ELIGIBLE` remains admission evidence only. It is not provider authority, process-launch authority, restart execution, order authority, SHADOW/PAPER authority, bounded-live-fire authority, Gate D, LIVE, or capital authorization.

Deterministic identity, fixed reason ordering, role isolation, OperationalMode binding, heartbeat/supervisor/capability/reconciliation/dependency checks, authorization binding, and currentness recomputation behavior are unchanged except that current external-consumer authority now contributes to material-participation detection.

## E7-113 exact branch changes

- `src/integration/runtime_preflight.py`
  - corrected external participation predicate only;
  - E7-113 code commit: `1da35a78ef2fcd12b09f14ca4bfda0bf2f37b6c2`.
- `tests/integration/test_runtime_preflight_external_consumer_regression.py`
  - new deterministic regression definitions;
  - E7-113 test-definition commit: `0b0ffd84b295a6b9eec3cf9995c1c9a89ee7876c`.
- this evidence artifact;
- `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` only for future exact focused-test registration;
- `coordination/E7/STATUS.md` terminal E7-113 state.

`tests/safety/test_p0_integrated_fail_closed.py` remains unchanged by E7-113 because its existing role-transfer/no-authority-side-effect coverage remains applicable.

No shared contract/ADR, E1-E6 production code, E6 OperationalMode semantics/storage, provider adapter/auth/config/credentials, AgentBridge/local-action infrastructure, Product Owner authorization artifact, risk/leverage/capital threshold, LIVE/release policy, or GitHub Actions/CI file is modified.

## Deterministic regression definitions

`tests/integration/test_runtime_preflight_external_consumer_regression.py` defines the PM-requested cases:

1. credential-free + no supervisor + non-null current external authority + missing input external evidence -> `FAIL_CLOSED / PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`;
2. provider-read-only with the same authority/evidence mismatch -> fail closed;
3. credential-free with no external evidence and no current external authority -> remains eligible when all other synthetic facts are coherent;
4. exact current external evidence + exact current external authority -> remains admissible when all other facts are coherent;
5. external evidence with absent current authority -> fail closed;
6. stale/mismatched external generation -> fail closed;
7. incompatible external compatibility status -> fail closed;
8. SHADOW missing external evidence -> unconditional fail closed remains intact;
9. the remediation path creates no provider/network/credential/process/order/runtime/capital authority fields.

Existing E7-112 tests continue to define deterministic identity/currentness, role substitution/non-transferability, revision/worktree, OperationalMode, heartbeat, supervisor/restart, action allowlist, reconciliation, dependency, authorization, bounded-live-fire undefined-mode policy, and synthetic provider-role non-authority behavior.

## Verification boundary

E7-113 executes no project code or tests. The authoritative task explicitly keeps executable verification local-only while LF-0 remains blocked.

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

`NOT_RUN` is not PASS. Static remediation and merge review cannot establish executable qualification.

## Exact future approved-local commands

After the remediated candidate is merged, a future PM task binds the exact merged revision, approved-local infrastructure establishes that same revision `EXACT_CLEAN`, and a fresh execution task authorizes qualification, run from the approved Windows repository root:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests/integration -p 'test_runtime_preflight.py' -v
python -m unittest discover -s tests/integration -p 'test_runtime_preflight_external_consumer_regression.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
```

Then execute the focused P0 sequence and full 14-suite credential-free matrix in `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` on the same exact clean approved-local revision.

Actual test counts/results, exact revision, approved local OS/Python, exact-clean evidence, and zero provider/private/credential/mutation/process/order/runtime/capital/GitHub-compute facts must be recorded at execution time. Historical counts or another revision's PASS must not be reused.

## Remaining limitations / dependencies

- E7-113 remediation is still `IMPLEMENTED_UNQUALIFIED / NOT_RUN / NOT_PASS` until approved-local exact-revision execution exists.
- LF-0 exact-revision preparation infrastructure remains blocked and unchanged.
- E7-101 request/job identities remain terminal and non-reusable.
- FP-02 provider-native close/protection facts remain unresolved/fail closed.
- AgentBridge/operator launcher/supervisor production enforcement remains external and unchanged.
- provider read-only requires future Product Owner authority.
- SHADOW/PAPER remain unauthorized.
- bounded 10U live-fire remains unauthorized.
- Gate D / recurring LIVE remain blocked/unauthorized.
