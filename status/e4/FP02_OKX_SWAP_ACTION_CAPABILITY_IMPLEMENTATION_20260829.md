# E4 FP-02 OKX SWAP Action Capability Implementation — 2026-08-29

- task_id: `E4-20260829-034`
- agent: `E4`
- target_branch: `agent/e4-fp02-action-capability-evidence-20260829`
- task-start baseline main: `f56240f039367c878fcf06ad2503d76d59585d9f`
- implementation_classification: `STATIC IMPLEMENTATION / TEST-DEFINITION CANDIDATE`
- executable_verification: `NOT_RUN / NOT_PASS`

## Scope / authority

This task implements only the E4-local deterministic FP-02 resolver described by:

- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md` (`okx-swap-action-role-capability-v0.1`);
- accepted `protection-trigger-validity-v0.1` and merged E4 FP-03 consumer;
- accepted `external-provider-object-ownership-reconciliation-v0.1` and merged E4 FP-04 producer/currentness;
- accepted `okx-swap-close-residual-sizing-v0.1` and merged E4 FP-05 sizing candidate;
- accepted `protection-registry-multiplicity-v0.1` and merged E4 FP-11 producer/currentness;
- merged E7 FP-16 runtime-preflight candidate only as an external authority boundary;
- `status/PM_E7_114_REVIEW_20260829.md`;
- active LF-0 exact-revision preparation blocker.

No shared contract, ADR, E5 policy, E6 persistence, E7 runtime/release semantics, provider transport/auth/signing/private API behavior, Product Owner authorization artifact, risk/leverage/capital threshold, or GitHub Actions/CI surface changed.

## Files changed

```text
src/brokers/okx_action_capability.py
tests/brokers/test_okx_action_capability.py
status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md
coordination/E4/STATUS.md
```

No `src/brokers/__init__.py` export was required.

## Provider-local states and reasons

The resolver uses only the accepted E4-local capability states:

```text
REPO_EVIDENCED
UNRESOLVED_FAIL_CLOSED
FORBIDDEN
NOT_APPLICABLE
```

`NOT_APPLICABLE` is also used explicitly for role dependencies that do not participate in the selected role; it is never upgraded into mutation authority.

Stable fail-closed reasons are the matrix vocabulary:

```text
OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED
OKX_SWAP_ACTION_ROLE_UNSUPPORTED
OKX_SWAP_INSTRUMENT_UNSUPPORTED
OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED
OKX_SWAP_POSITION_MODE_UNSUPPORTED
OKX_SWAP_MARGIN_MODE_UNSUPPORTED
OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN
OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN
OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED
OKX_SWAP_TRIGGER_BASIS_UNPROVEN
OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN
OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT
OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN
OKX_SWAP_RECONCILIATION_REQUIRED
```

The reason order is deterministic and provider-local; no shared enum was added.

## Pure input/evidence boundary

`src/brokers/okx_action_capability.py` adds:

```text
OKXActionCapabilityFacts
resolve_okx_swap_action_capability(...)
validate_okx_swap_action_capability_evidence(...)
okx_swap_action_capability_evidence_is_current(...)
expected_repo_fieldset(...)
canonical_okx_action_capability_hash(...)
```

The resolver accepts only supplied sanitized facts and performs no I/O. It binds:

```text
profile/action role
provider=OKX / api=V5
BTC_USDT_PERP -> BTC-USDT-SWAP / instType=SWAP
acctLv=2
position mode
margin mode
operation class
exact provider field-set ref/hash/generation when a repo-evidenced row exists
reconciliation classification
FP-03/FP-05/FP-11 ref/status/currentness only where applicable
caller capability assertion presence only so it can be rejected
```

It does not inspect credentials, account balances, raw provider payloads, filesystem paths, shell commands, process state, private tokens, or capital state.

## ENTRY repository-evidenced boundary

`ENTRY` is `REPO_EVIDENCED` only for the exact bounded current repository row:

```text
provider/api = OKX/V5
instrument = BTC_USDT_PERP -> BTC-USDT-SWAP / SWAP
acctLv = 2
margin/tdMode = isolated
operation = MUTATION: MARKET_ORDER_CREATE
position mode = net_mode | long_short_mode
```

The exact closed descriptor is derived from current E4 repository behavior:

```text
POST /api/v5/trade/order
fields = clOrdId, instId, ordType, posSide, side, sz, tdMode
instId = BTC-USDT-SWAP
ordType = market
tdMode = isolated
side = LONG->buy | SHORT->sell
net_mode posSide = net
long_short_mode ENTRY posSide = LONG->long | SHORT->short
sz source = validated current entry sizing metadata
```

The caller must supply an exact sanitized descriptor plus exact ref/hash/generation that matches the resolver's internal closed repository row. Extra, missing, mutated, unknown, or hash-mismatched role fields are not accepted as compatibility proof.

`REPO_EVIDENCED` here means only that the repository mapping exists. It is not provider verification, submit authority, runtime authority, or release authorization.

## Caller authority rejection

A supplied caller capability boolean/dictionary is never consumed as a positive proof. Any non-null caller capability assertion forces:

```text
UNRESOLVED_FAIL_CLOSED
OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED
```

The returned evidence records only that an assertion was present; the arbitrary caller payload is not serialized as authority.

## PROTECTION_STOP remains unresolved

`PROTECTION_STOP` has no positive provider-dispatch path in this implementation.

Even when supplied dependencies say:

```text
FP-03 = ACTIONABLE / CURRENT
FP-11 = CONVERGED_EXACTLY_ONE_INTENDED / CURRENT
```

the capability remains:

```text
UNRESOLVED_FAIL_CLOSED
```

because the current repository still does not prove the protection/algo endpoint, provider trigger field set, `triggerPxType`/trigger basis, protection-specific `posSide`, provider-native reduce-only behavior, or exact readback/cancel identity.

Shared FP-03 `LAST_PRICE` geometry is never provider trigger-basis proof. Missing/non-current FP-11 also emits `OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT`, but a current FP-11 registry still does not create provider capability.

No provider protection materialization is created.

## POSITION_EXIT / EMERGENCY_EXIT remain unresolved

Both close roles have no positive provider-dispatch path.

Current exact FP-05 sizing evidence can remove only the `OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN` dependency reason when its supplied ref/status/currentness is coherent. It cannot remove:

```text
OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN
```

because the repository still does not prove role-specific endpoint/fieldset, `posSide`, provider-native reduce-only behavior, or exact close semantics.

Emergency urgency creates no bypass. Original entry requested quantity is never used by this resolver as fresh reducible-exposure proof.

## READ_ONLY_RECONCILIATION repository-evidenced boundary

The role is `REPO_EVIDENCED` only for:

```text
operation = GET: OBSERVATION_ONLY
acctLv = 2
position mode = net_mode | long_short_mode
isolated baseline
closed GET-only/default-deny Shadow descriptor
```

The exact private allowlist is:

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP
GET /api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP
```

plus public provider time.

Any mutation operation through this role returns:

```text
FORBIDDEN
OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN
```

No submit/cancel/amend/close/protection/set-mode mutation surface is added.

## Reconciliation / mode behavior

Mutation roles require supplied reconciliation classification `CURRENT`. Any other value remains non-authorizing and routes through `OKX_SWAP_RECONCILIATION_REQUIRED` before role-specific materialization.

Known Spot `margin_mode=cash` is explicitly `FORBIDDEN / OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN`. Other unsupported margin/account/position/instrument facts fail closed and are never coerced into the accepted row.

## Deterministic identity / currentness

The returned immutable provider-local evidence uses:

```text
capability_evidence_id = okxswapcap_<sha256>
```

over all material resolver facts and the derived state/reasons, excluding only the ID itself and `evaluated_at`.

Therefore:

```text
same material facts + later evaluated_at -> same identity / still materially current
changed role/instrument/mode/operation/fieldset hash or generation/dependency status -> different identity/currentness
```

No numeric TTL is invented. A wall-clock change alone cannot turn unresolved provider facts into `REPO_EVIDENCED` and cannot manufacture supersession.

## Deterministic tests defined

`tests/brokers/test_okx_action_capability.py` defines provider-free cases for:

- ENTRY exact `net_mode` row;
- ENTRY exact `long_short_mode` row;
- wrong canonical/provider instrument and non-SWAP;
- wrong/unknown account level;
- wrong/unknown position mode;
- Spot `tdMode/cash` forbidden behavior;
- caller capability assertion rejection;
- mutated/missing provider field set;
- FP-03 ACTIONABLE protection evidence remaining insufficient for provider trigger basis;
- PROTECTION_STOP remaining unresolved;
- POSITION_EXIT remaining unresolved even with coherent FP-05 sizing evidence;
- EMERGENCY_EXIT remaining unresolved with no urgency bypass;
- reconciliation-required and stale FP-05 facts remaining non-authorizing;
- READ_ONLY exact GET row and mutation rejection;
- deterministic identity and timestamp-only currentness;
- material generation invalidation;
- no provider/network/credential/runtime/capital dependency in the returned evidence.

No test was executed through GitHub.

## Verification / execution state

LF-0 approved-local exact-revision preparation remains blocked. No separately authoritative approved-local exact-revision PASS exists for this resulting branch revision.

```text
project executable verification = NOT_RUN / NOT_PASS
FP-02 capability resolver tests = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

Required future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.brokers.test_okx_action_capability -v
python -m unittest discover -s tests/brokers -p "test_okx_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

Result for all commands in this task: `NOT_RUN / NOT_PASS`.

Historical qualification evidence is revision-bound and is not rebound to this branch.

## Main movement during task

Task work began from exact `main` revision:

```text
f56240f039367c878fcf06ad2503d76d59585d9f
```

During implementation, `main` advanced to `75208bb33cf7385bb1cc63228bc4d606dbe2252e` only by PM stale-idle-watchdog revalidation. E4 re-read latest `main:coordination/E4/TASK.md`; task ID remained exactly `E4-20260829-034` with the same target branch/scope. No rebase/merge/force update was performed and no new scope was inferred from the unrelated watchdog commit.

## Security / authority boundary

```text
real secrets read/requested/committed = NO
provider/private request = 0
provider transport/auth/signing change = NO
provider/account/order/protection mutation = 0
runtime/process action = 0
risk/lifecycle policy change = NO
E6 persistence change = NO
shared contract/ADR change = NO
Product Owner trading authorization consumed = NO
capital movement/exposure = NONE
```

## Terminal classification

```text
bounded source implementation = COMPLETE
bounded deterministic test definitions = COMPLETE
approved-local executable verification = NOT_RUN / NOT_PASS
state = PARTIAL
```

`NOT_RUN != PASS`; therefore `DONE` is not claimed. E4 stops here and does not self-start provider verification, credential use, protection/exit mutation, exact-revision preparation, Local Job Requests, qualification execution, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, process action, order action, or capital movement/exposure.
