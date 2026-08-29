# E4 FP-02 OKX SWAP Action Capability Implementation — 2026-08-29

- task_id: `E4-20260829-035`
- agent: `E4`
- target_branch: `agent/e4-fp02-action-capability-evidence-20260829`
- task-start latest main: `8a3d9e8c83c1dacfb8d5bacab89b151224f693eb`
- predecessor task: `E4-20260829-034`
- PM review: `status/PM_E4_034_REVIEW_20260829.md`
- implementation_classification: `BOUNDED PROVENANCE REMEDIATION / TEST-DEFINITION CANDIDATE`
- executable_verification: `NOT_RUN / NOT_PASS`

## Scope / authority

E4-035 remediates only the PM-identified positive `REPO_EVIDENCED` provenance fail-open in the existing E4-034 FP-02 resolver.

The accepted design remains:

```text
okx-swap-action-role-capability-v0.1
```

No shared contract, ADR, provider transport/auth/signing/private API code, E5 policy, E6 persistence, E7 runtime/release logic, Product Owner authorization artifact, risk/leverage/capital threshold, Local Job Request, exact-revision preparation, or GitHub Actions/CI surface changed.

Files changed by the bounded remediation:

```text
src/brokers/okx_action_capability.py
tests/brokers/test_okx_action_capability.py
status/e4/FP02_OKX_SWAP_ACTION_CAPABILITY_IMPLEMENTATION_20260829.md
coordination/E4/STATUS.md
```

## PM defect remediated

E4-034 allowed `_fieldset_is_repo_evidenced(...)` to accept a positive row when a caller supplied:

```text
public expected descriptor
+ reproducible descriptor hash
+ any non-null fieldset ref
+ any non-null generation id
```

That meant arbitrary caller provenance strings could manufacture `REPO_EVIDENCED`.

E4-035 removes that positive path. Descriptor/hash correctness remains necessary, but is no longer sufficient.

## E4-owner-authoritative repository row identity

The resolver now owns one immutable canonical provenance tuple for each currently positive row:

```text
ENTRY / net_mode
ENTRY / long_short_mode
READ_ONLY_RECONCILIATION / net_mode
READ_ONLY_RECONCILIATION / long_short_mode
```

Each canonical row binds exactly:

```text
capability profile version
action role
position mode
exact repository fieldset descriptor
exact deterministic descriptor hash
exact stable E4-owned fieldset reference
exact stable E4-owned fieldset generation identifier
```

The stable refs are:

```text
e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:ENTRY:net_mode:v0.1
e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:ENTRY:long_short_mode:v0.1
e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:READ_ONLY_RECONCILIATION:net_mode:v0.1
e4-repo-fieldset:okx-v5:BTC-USDT-SWAP:READ_ONLY_RECONCILIATION:long_short_mode:v0.1
```

The corresponding stable generations are role/mode-specific values under:

```text
e4-repo-generation:okx-swap-action-role-capability-v0.1:<ROLE>:<MODE>:1
```

These values are repository identity only. They are not provider verification, mutation authority, runtime authority, credentials, or a release gate.

`expected_repo_fieldset_identity(...)` returns a defensive copy of resolver-owned canonical row material for deterministic consumers/tests. The positive resolver path independently recomputes/looks up its own canonical row and compares every supplied provenance field to it; callers cannot select arbitrary positive ref/generation strings.

## Positive capability rule after remediation

A positive ENTRY or READ_ONLY row now requires all of the following exact matches:

```text
provider/api/instrument/account/margin/role/mode/operation
+ canonical E4 owner row descriptor
+ canonical owner row descriptor hash
+ canonical owner row fieldset ref
+ canonical owner row generation id
+ existing reconciliation/caller-assertion gates
```

Any of the following fails closed:

```text
forged/arbitrary fieldset ref
forged/arbitrary generation
role/mode cross-use of another valid owner row
missing ref or generation
descriptor mutation
descriptor/hash mismatch
unknown/non-owner fieldset
caller capability assertion
```

The preferred existing reason remains:

```text
UNRESOLVED_FAIL_CLOSED
OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN
```

Caller capability booleans/dictionaries still force:

```text
UNRESOLVED_FAIL_CLOSED
OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED
```

## Evidence validator hardening

`validate_okx_swap_action_capability_evidence(...)` now also rejects a `REPO_EVIDENCED` claim unless its provider-local evidence ref/hash/generation and role/mode/operation/common identity facts match the resolver-owned canonical row.

Therefore a syntactically valid evidence object cannot claim `REPO_EVIDENCED` merely because it has no reason codes and a self-consistent public hash identity.

## ENTRY semantics unchanged

The only positive ENTRY rows remain the accepted existing repository mapping:

```text
provider/api = OKX/V5
canonical/provider instrument = BTC_USDT_PERP / BTC-USDT-SWAP / SWAP
acctLv = 2
margin/tdMode = isolated
operation = MUTATION: MARKET_ORDER_CREATE
position mode = net_mode | long_short_mode
POST /api/v5/trade/order
fields = clOrdId, instId, ordType, posSide, side, sz, tdMode
ordType = market
```

`net_mode` keeps `posSide=net`; ENTRY `long_short_mode` keeps LONG->long and SHORT->short. No new provider field or endpoint fact was added.

`REPO_EVIDENCED` remains repository mapping evidence only; it is not provider verification or order authority.

## READ_ONLY_RECONCILIATION semantics unchanged

The only positive read-only rows remain the accepted GET-only/default-deny observation surface for `net_mode | long_short_mode`.

The fixed allowlist remains account config, USDT balance, BTC-USDT-SWAP position, isolated leverage information, pending SWAP orders, SWAP fills, plus public provider time.

Any mutation operation through this role remains:

```text
FORBIDDEN
OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN
```

No submit/cancel/amend/close/protection/set-mode mutation surface was added.

## Unresolved provider semantics unchanged

The remediation does not create a positive provider row for:

```text
PROTECTION_STOP
POSITION_EXIT
EMERGENCY_EXIT
```

All remain:

```text
UNRESOLVED_FAIL_CLOSED
```

Specifically:

- FP-03 `LAST_PRICE` / ACTIONABLE shared geometry does not select provider `triggerPxType`, trigger basis, protection endpoint, protection `posSide`, native reduce-only behavior, or readback/cancel identity.
- FP-05 coherent sizing evidence can establish provider-local sizing constraints only; it does not prove endpoint, close `posSide`, native reduce-only behavior, or close fieldset.
- EMERGENCY_EXIT receives no provider-proof bypass.
- original entry requested quantity never substitutes for fresh actual reducible exposure.

## Deterministic identity / currentness

Capability evidence identity remains:

```text
capability_evidence_id = okxswapcap_<sha256>
```

`evaluated_at` is excluded from material identity/currentness.

Therefore:

```text
same material + later wall clock -> same identity/currentness
changed owner-row ref -> different identity / old evidence not current
changed owner-row generation -> different identity / old evidence not current
changed owner-row hash -> different identity / old evidence not current
```

A forged material change resolves fail closed rather than upgrading capability. No TTL was invented.

## Regression definitions

`tests/brokers/test_okx_action_capability.py` now uses resolver-owned canonical owner-row material instead of arbitrary positive fixture provenance.

Definitions cover at minimum:

- canonical ENTRY `net_mode` owner row -> `REPO_EVIDENCED`;
- canonical ENTRY `long_short_mode` owner row -> `REPO_EVIDENCED`;
- canonical READ_ONLY rows -> `REPO_EVIDENCED`;
- copied descriptor/hash + forged ref -> `UNRESOLVED_FAIL_CLOSED / OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN`;
- copied descriptor/hash + forged generation -> fail closed;
- valid owner-row provenance cross-used with wrong role or mode -> fail closed;
- descriptor mismatch or hash mismatch -> fail closed;
- missing ref or generation -> fail closed;
- caller capability assertions remain rejected;
- FP-03 protection still cannot prove provider trigger basis;
- PROTECTION_STOP remains unresolved;
- POSITION_EXIT remains unresolved with coherent FP-05 sizing;
- EMERGENCY_EXIT remains unresolved with no urgency bypass;
- reconciliation-required/stale facts remain non-authorizing;
- read-only mutation remains forbidden;
- time-only identity/currentness remains stable;
- ref/generation/hash material changes invalidate currentness;
- returned descriptor copies cannot mutate resolver-owned row material;
- no provider/network/credential/runtime/order/capital dependency is introduced.

No test was executed in this task.

## Verification / execution state

LF-0 approved-local exact-revision preparation remains blocked. No authoritative approved-local PASS exists for the resulting E4-035 revision.

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

All remain `NOT_RUN / NOT_PASS`. Historical qualification evidence is revision-bound and is not rebound to this branch.

## Security / authority boundary

```text
real secrets read/requested/committed = NO
provider/private network = NONE
provider transport/auth/signing change = NO
provider/account/order/protection mutation = 0
runtime/process action = 0
shared contract/ADR change = NO
Product Owner trading authorization consumed = NO
capital movement/exposure = NONE
```

## Terminal classification

```text
bounded provenance remediation = COMPLETE
bounded regression definitions = COMPLETE
approved-local executable verification = NOT_RUN / NOT_PASS
state = PARTIAL
```

`NOT_RUN != PASS`; therefore `DONE` is not claimed. E4 stops here and does not self-start provider verification, credential use, protection/exit mutation, exact-revision preparation, Local Job Requests, qualification execution, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, process action, order action, or capital movement/exposure.
