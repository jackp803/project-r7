# E7 SHADOW Temporal-Ordering Remediation — 2026-08-26

## Scope

- task_id: `E7-20260826-092`
- target_branch: `agent/e7-shadow-temporal-ordering-remediation-20260826`
- incident_source: `E7-20260826-090`
- incident_artifact: `status/e7/ZERO_CAPITAL_SHADOW_REPLACEMENT_SESSION_RESULT_20260826.md`
- prior_qualified_executable_revision: `ab725965e96cac7a9769fd1ab15a3e626f920b95`
- remediation_code_test_candidate_revision: `63951625cb3ffd57bca0c58b06d7067db6973c2b`
- architecture_decision: `docs/adr/ADR-0010-shadow-strategy-risk-temporal-ordering.md`
- provider_execution_in_E7_092: `NONE / FORBIDDEN`
- local_job_request_in_E7_092: `NONE / FORBIDDEN`

## Root-cause determination

The E7-owned temporal-ordering defect is **CONFIRMED as a real fail-closed path**.

The prior qualified `ShadowComposition.run_cycle(...)` accepted one caller `risk_evaluation_time`, used it for deterministic Candle/strategy evaluation, then invoked E4 `OKXShadowProviderReader.observe(...)`, and afterward passed that older caller timestamp to E5 `derive_gate_c_risk_context(...)`.

The external AgentBridge `2ac9a79` supervisor confirms the relevant caller sequence:

```text
E1 public ticker/candle reads
-> caller evaluation_time = utc_now()
-> normalize market inputs at evaluation_time
-> ShadowComposition.run_cycle(... risk_evaluation_time=evaluation_time ...)
-> E4 observe() occurs inside composition afterward
```

E4 correctly stamps the provider observation from its own UTC clock at the start of `observe(...)`. E5 correctly and unchanged treats:

```text
provider observed_at > risk_evaluation_time
```

as:

```text
GATE_C_SHADOW_OBSERVATION_TIME_INVALID
```

Therefore an advancing real clock can produce a healthy just-read provider batch whose observation timestamp is later than the pre-provider caller decision timestamp. The defect is E7 integration sequencing, not E5 temporal safety.

### E7-090 historical attribution limit

The durable E7-090 session evidence contains only the supervisor-level terminal reason:

```text
UNSAFE_PROVIDER_OR_RECONCILIATION_STATE
```

and does not contain the internal `ShadowCycleResult.reason_codes` from that failed cycle. E7 therefore does **not** claim that temporal ordering was proven to be the exclusive E7-090 blocker.

Historically possible sanitized alternatives remain:

- provider-read degradation not surfaced in the supervisor summary;
- another E5 risk-context fail-closed reason;
- checkpoint not established for another safe reason;
- reconciliation/recovery state not accepted.

E7-090 did establish zero available capital, `read_only`, account level `2`, `net_mode`, dedicated sub-account classification, healthy provider clock, nine bounded GETs, zero mutation requests and zero submit requests. Those facts narrow but do not eliminate the alternative internal reason possibilities.

## E7-owned remediation

### Time-boundary separation

`src/integration/shadow_composition.py` now distinguishes:

1. `strategy_evaluation_time` — deterministic caller-supplied market/strategy boundary;
2. E4 provider observation — performed after input/finality validation;
3. post-observation `risk_time_provider()` — invoked by E7 only after E4 returns and used for E5 context derivation and RiskDecision time.

The resulting order is:

```text
validate SHADOW mode/input
-> validate finalized Candles at strategy_evaluation_time
-> E4 observe provider/account state
-> invoke risk_time_provider()
-> E5 derive risk context at post-observation risk time
-> E2 evaluate strategy at strategy_evaluation_time
-> build TradeIntent generated_at=strategy_evaluation_time
-> E5 RiskDecision decided_at=post-observation risk time
```

E7 also fails closed if the post-observation risk timestamp precedes the strategy timestamp:

```text
RISK_DECISION_PRECEDES_STRATEGY_EVALUATION
```

### Compatibility boundary

The old `risk_evaluation_time=` keyword remains only as a deprecated compatibility alias for the strategy timestamp. Without an explicit new risk clock it retains the historical fixed decision-time semantics. This prevents silent behavior changes for existing static/unit consumers but means it is **not** a valid remediation path for a real advancing-clock runtime.

Runtime consumers must migrate to:

```text
strategy_evaluation_time=<deterministic strategy boundary>
risk_time_provider=<UTC clock callback invoked by E7 after E4 observation>
```

Ambiguous mixed use fails closed with stable E7 codes.

### E5 semantics preserved

No E5 source or temporal rule was modified.

A genuinely contradictory case where provider `observed_at` remains later than the post-observation risk timestamp still reaches E5 and remains rejected as:

```text
GATE_C_SHADOW_OBSERVATION_TIME_INVALID
```

No tolerance was widened and no SHADOW special case was added.

### Other domain boundaries preserved

No E1-E6 production source was modified.

- E1 finalized Candle/freshness semantics: unchanged.
- E2 deterministic StrategyRuntime semantics: unchanged.
- E4 GET allowlist/auth/redaction/no-submit/no-mutation semantics: unchanged.
- E5 risk veto/temporal semantics: unchanged.
- E6 OperationalMode/checkpoint/restart/reconciliation semantics: unchanged.
- `contracts-v0.1`: unchanged.
- public E7 `ShadowCycleResult`: still exports no `TradeIntent`, `RiskDecision`, `ApprovedTradePlan` or executable authority object.

## Sanitized diagnostic improvement

`ShadowCycleResult.reason_codes` now adds stable E7 stage classifications while preserving underlying domain reason codes:

```text
E7_PROVIDER_READ_DEGRADED
E7_RISK_CONTEXT_UNSAFE
E7_SHADOW_CHECKPOINT_NOT_RECORDED
```

A post-checkpoint reconciliation failure remains the existing sanitized E7 error:

```text
FRESH_SHADOW_RECONCILIATION_NOT_ESTABLISHED
```

These classifications distinguish provider degradation, risk-context rejection and failure to establish a checkpoint/reconciliation boundary without exposing provider payloads, credentials, exact balances, IDs, signatures, tokens/cookies, raw exception messages or local paths.

## Test-definition changes

### `tests/integration/test_gate_c_shadow_composition.py`

Added/updated definitions for:

- reproduction of the old pre-provider decision-time defect using unchanged E5 derivation;
- an advancing provider clock with a risk callback that asserts all seven E4 observation requests completed before the risk clock is invoked;
- healthy post-observation risk timing with no false `GATE_C_SHADOW_OBSERVATION_TIME_INVALID`;
- genuinely future/contradictory provider observation remaining fail closed;
- stage-specific sanitized E7 reason codes for provider degradation vs risk/checkpoint rejection;
- preservation of healthy non-authoritative Shadow planning/checkpoint behavior.

### `tests/e2e/test_gate_c_shadow_no_submit_e2e.py`

Updated the E7 timing fixture to use explicit `strategy_evaluation_time` plus `risk_time_provider` while preserving:

- restart requiring fresh provider reconciliation;
- exact E4 public-time + six-private-GET read-only path;
- zero mutation requests;
- no submit-capable integration surface.

### Existing safety coverage preserved

`tests/safety/test_gate_c_shadow_composition_safety.py` remains compatible through the deprecated fixed-time alias and continues to define:

- unclosed/future Candle rejection before provider transport;
- submit-capable Demo adapter rejection;
- no capability expansion / no caller-forged fill checkpoint;
- provider degradation flowing fail closed;
- invalid provider domain rejection;
- E6 missing/corrupt state fail-closed behavior;
- redaction/no-authority assertions.

## Local verification

```text
local_verification = NOT_RUN
reason = current ChatGPT/GitHub environment is not the Product-Owner-approved local Windows project execution environment; E7-092 explicitly forbids creating a Local Job Request
GitHub Actions / CI / hosted runner = NOT USED / FORBIDDEN
```

Exact approved-local PowerShell commands required:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/integration -p 'test_gate_c_shadow_composition.py' -v
python -m unittest discover -s tests/e2e -p 'test_gate_c_shadow_no_submit_e2e.py' -v
python -m unittest discover -s tests/safety -p 'test_gate_c_shadow_composition_safety.py' -v
```

`NOT_RUN != PASS`. No test result is fabricated or interpreted as qualification evidence.

## Downstream consumer dependency

```text
AgentBridge_consumer_update_required = YES
```

Historical AgentBridge supervisor `tools/run_zero_capital_shadow_session.py` at revision `2ac9a79` still calls:

```text
risk_evaluation_time=evaluation_time
```

Before any future authorized SHADOW runtime, its consumer boundary must be migrated and independently verified to use explicit separated timing, for example:

```text
strategy_evaluation_time=evaluation_time
risk_time_provider=_utc_now
```

The clock callback must be passed into E7 and invoked there after E4 observation. AgentBridge must not precompute a guessed/future decision timestamp.

E7-092 does not modify `jackp803/agent-bridge`.

## Qualification consequence

```text
new_executable_candidate = YES
candidate_revision = 63951625cb3ffd57bca0c58b06d7067db6973c2b
Gate_C_credential_free_requalification_required = YES
current_Gate_C_PASS_for_prior_qualified_revision = UNCHANGED
new_candidate_qualified = NO
```

Because executable integration source and Gate C tests changed, the remediation candidate requires approved-local credential-free Gate C requalification before it can replace `ab725965e96cac7a9769fd1ab15a3e626f920b95` as an accepted executable revision.

Any future provider/SHADOW session also requires:

1. completed AgentBridge consumer migration/review;
2. accepted exact-revision project requalification/reconciliation;
3. new explicit Product Owner authority, because both prior bounded SHADOW authorizations are consumed.

E7-092 itself does not authorize or start requalification, AgentBridge execution, or another provider session.

## Safety / execution confirmation

```text
provider_requests = 0
credentials_read_requested_used = 0 / NONE
mutation_requests = 0
submit_requests = 0
capital_exposure = NONE
SHADOW_runtime = NOT STARTED
PAPER_runtime = NOT STARTED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
GitHub_project_compute = NOT USED
```

No consumption marker was reset/deleted/modified. No third SHADOW session, order action, provider/account mutation, capital movement, PAPER, Gate D or LIVE work was performed.

## E7 disposition

The E7-owned remediation is complete enough for handoff, but it is not yet an executable accepted replacement because:

- required approved-local project verification/requalification is `NOT_RUN`; and
- the external AgentBridge runtime consumer still requires migration to the explicit timing API.

Therefore E7-092 is suitable for terminal `PARTIAL`, with no further execution self-started.
