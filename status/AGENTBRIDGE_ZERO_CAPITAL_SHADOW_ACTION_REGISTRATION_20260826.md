# AgentBridge Operator Registration — Zero-Capital SHADOW Session

- recorded_at: `2026-08-26T17:10:49+08:00`
- operator_state: `REGISTERED / ALLOWLISTED / NOT EXECUTED`
- canonical_action_id: `GATE_C_ZERO_CAPITAL_SHADOW_SESSION`
- AgentBridge_source_revision: `f3bf229`
- supervisor_source: `tools/run_zero_capital_shadow_session.py`
- supervisor_sha256: `86DA3F8AFF2D0549DC6961E85C638A9FD41A0E45023FF1BC07F1B2560C8A6280`
- qualified_project_revision: `ab725965e96cac7a9769fd1ab15a3e626f920b95`
- Product_Owner_authorization: `status/PRODUCT_OWNER_ZERO_CAPITAL_SHADOW_AUTHORIZATION_20260826.md`
- E7_readiness_contract: `status/e7/ZERO_CAPITAL_SHADOW_SESSION_READINESS_20260826.md`

## Registration result

```text
action defined locally                         = YES
action in project allowed_actions              = YES
action enabled                                 = YES
network_expected                               = YES
Local Runner process timeout                   = 1840 seconds
supervisor monotonic deadline                  = 1800 seconds
shared E1/E4 pre-dispatch GET limit            = 300
complete-cycle reservation                     = 9 GET slots
official REST hostname                         = openapi.okx.com only
non-GET / redirect / unknown-path dispatch     = DENIED
mutation request count required                = 0
submit request count required                  = 0
available capital required                     = exactly zero
active exact-revision worktree                 = ab725965e96cac7a9769fd1ab15a3e626f920b95
active worktree classification                 = CLEAN
single-session consumption marker              = ABSENT / AUTHORIZATION NOT CONSUMED
provider requests during registration          = 0
SHADOW runtime during registration             = NOT STARTED
```

## Fixed operator contract

The registered action executes only the operator-owned bounded supervisor. The Local Job
request supplies no executable, arguments, path, hostname, duration, budget, credential, or
provider capability. All such values are fixed in the local action definition/supervisor.

Before network traffic, the supervisor verifies Windows, the active AgentBridge worktree
registration, exact `HEAD`, clean worktree, secure local credential schema, exact configured
and operator-confirmed REST base URL, accepted account-level/position-mode configuration,
and an available sanitized evidence sink.

Immediately before the first possible session network operation it atomically creates the
single-session consumption marker. A pre-existing marker blocks a second execution. The
supervisor then establishes audited local `SHADOW` operational mode, constructs only the
accepted E1 current-market source, E4 read-only provider reader, E5 risk derivation, E6 mode
store and E7 no-submit `ShadowComposition`, and repeats bounded cycles under one shared
deadline/budget.

Every outbound attempt is reserved before dispatch. Failed/time-out GETs consume budget.
The next cycle is denied unless nine slots remain. Each request timeout is capped to remaining
monotonic session time. Both public and private traffic require HTTPS and hostname
`openapi.okx.com`; redirects, unknown paths and non-GET methods fail closed.

The balance response is classified in memory as zero/nonzero/unknown before composition use.
Nonzero or unknown stops the session. Provider/account safety, clock, market freshness and
finality, positions, leverage, pending orders, fill reconciliation, operational-mode recovery,
mutation/submit reachability, exact revision and evidence sanitation are all mandatory
fail-closed conditions.

Completion transitions the local operational mode to `PAUSED`; failure attempts a local
`LOCKED` transition. Durable stdout/local evidence contains classifications and counters only,
never credential values, exact balance, UID/mainUID, signatures, tokens/cookies, raw private
responses, provider order/fill IDs, browser auth, or unnecessary local paths.

## Verification

```text
targeted supervisor safety tests = 6 / PASS
full AgentBridge test suite       = 75 / PASS
configuration validation         = PASS
GitHub Actions / hosted compute  = NOT USED
project/provider code execution  = NOT RUN
credentials read                 = NO
provider traffic                 = NONE
authorization consumption        = NO
```

The six supervisor tests prove shared pre-dispatch counting, denial of the next attempt after
the cap, deadline enforcement and remaining-time timeout capping, shared public/private/time
counters, nonzero-balance fail-closed classification without amount persistence, hostname and
non-GET denial, and the nine-slot complete-cycle admission rule.

## PM / E7 handoff

The `LOCAL_ACTION_NOT_REGISTERED` dependency is resolved. PM may issue one fresh E7 execution
task using exactly `GATE_C_ZERO_CAPITAL_SHADOW_SESSION` and a unique request ID. E7 must still
verify the current authorization and operator evidence before creating the Local Job Request.

This registration grants no PAPER, recurring SHADOW, order submission, provider/account
mutation, capital movement/exposure, Gate D or LIVE authority.
