# E7 Current Task

- task_id: `E7-20260826-092`
- issued_at: `2026-08-26T23:25:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-shadow-temporal-ordering-remediation-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `E7-20260826-090`, `status/e7/ZERO_CAPITAL_SHADOW_REPLACEMENT_SESSION_RESULT_20260826.md`, qualified revision `ab725965e96cac7a9769fd1ab15a3e626f920b95`, `status/BLOCKERS.md`

## Objective

Diagnose and remediate the E7-owned cross-module temporal-ordering defect exposed by the fail-closed E7-090 replacement SHADOW session, using source/test/ADR work only.

This task does **not** authorize another provider session. Both prior SHADOW authorizations are consumed. No Local Job Request, provider request, credential operation, SHADOW/PAPER runtime, Gate D, LIVE, order action, account mutation, or capital exposure is allowed in E7-092.

## Authoritative incident evidence

E7-090 established:

```text
replacement authorization = CONSUMED / NO RETRY
HTTPS GETs = 9
private GETs = 6
public market GETs = 2
public provider-time GETs = 1
available_balance_is_zero = YES
permission = read_only
account level = 2
position mode = net_mode
dedicated subaccount = YES
clock = HEALTHY
mutation requests = 0
submit requests = 0
capital exposure = NONE
cycle_count_completed = 0
terminal_stop_reason = UNSAFE_PROVIDER_OR_RECONCILIATION_STATE
operational mode = LOCKED
```

PM source review identified the temporal-ordering path that must be independently verified by E7 before changing code:

1. AgentBridge revision `2ac9a79` captures its caller `evaluation_time` before invoking `ShadowComposition.run_cycle(...)`.
2. `ShadowComposition.run_cycle(...)` then performs E4 `OKXShadowProviderReader.observe(...)` internally.
3. E5 `derive_gate_c_risk_context(...)` correctly treats provider `observed_at > risk_evaluation_time` as unsafe (`GATE_C_SHADOW_OBSERVATION_TIME_INVALID`).
4. A real advancing clock can therefore supply E5 a pre-provider decision timestamp even when the just-read provider batch is otherwise safe.

Do not assume this is the only possible E7-090 blocking reason until source/test analysis confirms it. Preserve competing sanitized reason possibilities where evidence cannot distinguish them.

## Required remediation boundary

E7 owns the integration sequencing/API boundary. E7 must preserve all of the following:

- E5's temporal safety rule must **not** be weakened, bypassed, widened, or special-cased for SHADOW.
- Provider/account truth must be observed before the risk decision timestamp used to interpret that truth.
- Strategy/candle evaluation semantics must remain deterministic and must not be silently conflated with the later provider/risk decision timestamp.
- E4 read-only/no-submit semantics remain unchanged.
- E6 SHADOW checkpoint/recovery semantics remain unchanged.
- The public integration result must never expose TradeIntent/RiskDecision/ApprovedTradePlan or executable authority.
- Any reason material added for diagnostics must be stable sanitized reason codes only; never raw provider payloads, credentials, IDs, exact balances, exception messages containing sensitive data, or local paths.

E7 may choose the minimal safe implementation, including a deterministic injectable E7 clock seam or an explicit separation between strategy evaluation time and post-provider risk decision time. Do not merely replace the caller timestamp with a guessed/future timestamp, and do not hide the ordering issue by tolerating provider observations after the decision boundary.

## Required source/test work

Inspect at minimum:

- `src/integration/shadow_composition.py`;
- `src/risk/context_derivation.py` as read-only semantic authority unless an undefined contract is discovered;
- `src/brokers/okx_shadow.py` as read-only provider semantic authority unless an E7 adapter issue is discovered;
- E7 integration/E2E/safety tests covering SHADOW composition, freshness, restart/reconciliation, no-submit and reason codes;
- the E7-090 sanitized result;
- AgentBridge `2ac9a79` supervisor source only as an external consumer reference; do not modify `jackp803/agent-bridge` in this project task.

Implement the minimal E7-owned remediation and add/adjust tests so they define at least:

1. an advancing-clock case that reproduces the pre-provider decision-time ordering defect;
2. a healthy provider batch where the E5 risk decision timestamp is obtained only after provider observation and the temporal check does not falsely fail;
3. preservation of fail-closed behavior for genuinely future/contradictory provider timestamps;
4. preservation of finalized-candle/strategy evaluation semantics;
5. preservation of no-submit/no-mutation capability restrictions;
6. sanitized `ShadowCycleResult.reason_codes` or equivalent E7 evidence sufficient to distinguish provider-read degradation from risk/checkpoint/reconciliation rejection without sensitive material.

If the safest fix materially changes the E7 integration API, create/update an E7-owned ADR and enumerate all consumers, including the AgentBridge supervisor update required before any future authorized runtime. Do not silently create a compatibility shim that changes timing semantics without documentation.

## Verification boundary

Project/provider execution in E7-092 is not authorization to run another SHADOW session.

- Do not call OKX.
- Do not read credentials.
- Do not create `coordination/E7/LOCAL_JOB_REQUEST.json`.
- Do not reset/delete either consumption marker.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.
- If an approved local credential-free environment is available under existing governance, E7 may run only the relevant project unit/integration/safety tests that require no provider/credentials/runtime authorization.
- Otherwise record `NOT_RUN` and the exact local commands required. `NOT_RUN != PASS`.

No source/test result from this task authorizes a third SHADOW session. Any future provider session still requires new explicit Product Owner authority after remediation/requalification/operator-consumer review.

## Required durable evidence

Create:

`status/e7/SHADOW_TEMPORAL_ORDERING_REMEDIATION_20260826.md`

It must record:

- confirmed root cause vs remaining alternative reason codes;
- exact E7 source/API change and why E5 semantics were preserved;
- tests added/changed;
- local verification result or `NOT_RUN` + exact commands;
- whether an AgentBridge consumer update is required;
- whether the change creates a new executable candidate revision needing Gate C credential-free requalification;
- confirmation of zero provider requests, zero credentials, zero mutation/submit/capital exposure, no SHADOW/PAPER/Gate D/LIVE runtime.

## Writable scope

Only E7-owned integration/remediation surfaces, for example:

- `src/integration/shadow_composition.py`;
- `tests/integration/**`;
- `tests/e2e/**`;
- `tests/safety/**`;
- `docs/adr/**` when a material integration API change requires it;
- `status/e7/SHADOW_TEMPORAL_ORDERING_REMEDIATION_20260826.md`;
- `status/INTEGRATION_STATUS.md` if needed;
- `coordination/E7/STATUS.md`.

Do not modify E1-E6-owned production code, E5 temporal safety semantics, E4 provider allowlists/auth, credentials, AgentBridge source, local action catalog, Product Owner authorization artifacts, release-gate PASS criteria, or other-agent TASK/STATUS files.

## Completion

### DONE

Use `DONE` when the temporal-ordering root cause is established, the minimal E7-owned source/test remediation is complete, downstream consumer/requalification needs are explicit, and required evidence/status are committed/pushed. Local tests may be `NOT_RUN` only when the approved environment is unavailable; do not call that PASS.

### PARTIAL

Use `PARTIAL` when the E7-owned fix is complete enough to hand off but an external AgentBridge consumer change or local requalification dependency prevents the remediation from becoming an executable candidate.

### BLOCKED

Use `BLOCKED` only for an authoritative contract conflict or missing evidence that prevents safe remediation design.

Stop after E7-092. Do not self-start requalification, AgentBridge remediation, provider execution, a third SHADOW session, PAPER, Gate D, LIVE, provider mutation, order submission, or capital movement/exposure.
