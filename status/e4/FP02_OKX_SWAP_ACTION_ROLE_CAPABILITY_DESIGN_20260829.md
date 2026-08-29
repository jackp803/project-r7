# E4 FP-02 OKX SWAP Action-Role Capability Design Handoff — 2026-08-29

## Handoff

**From:** E4 / Trading Execution / Broker Integration Engineer  
**To:** E7 / Project Manager  
**Branch:** `agent/e4-fp02-swap-action-role-capability-design-20260829`  
**Task:** `E4-20260829-026`  
**Baseline main revision:** `a372949ea41c19539275a13b207c2fafd9c05ab5`  
**Design artifact commit:** `734df6b75bb3e01b91f2222f8a67aceaf3b302e7`  
**Design profile:** `okx-swap-action-role-capability-v0.1`

### 1. Objective

Define the E4-owned FP-02 OKX V5 SWAP action-role capability vocabulary/table without executable changes, provider calls, credentials, mutation, runtime or capital exposure.

Primary artifact:

`docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`

### 2. Current provider/instrument baseline used

```text
provider                 = OKX
api_version              = V5
canonical instrument     = BTC_USDT_PERP
provider instrument      = BTC-USDT-SWAP
provider instType        = SWAP
current direct conversion = linear / ctValCcy=BTC path only
accepted account level   = acctLv=2 only
retained config modes    = net_mode | long_short_mode
mutation margin baseline = isolated
```

Repository evidence consumed:

- current bounded entry adapter/config/materialization in `src/brokers/okx_demo.py`;
- current read-only production Shadow surface in `src/brokers/okx_shadow.py`;
- current linear SWAP entry sizing metadata/conversion in `src/brokers/okx_sizing.py`;
- E4-owned adapter/sizing/shadow/submit-integrity tests;
- shared `contracts-v0.1`, execution object profiles, `protection-v0.1`, `close-v0.1`, Position lifecycle execution-evidence binding;
- accepted FP-02 gap audit and `bounded-live-fire-readiness-v0.1` sequencing.

Historical provider-facing evidence was treated only as historical evidence for its own revision. No provider claim is rebound to this design.

### 3. Complete role/capability table

| Role | Authority | Operation class | Side | Account / position mode | Margin | Quantity | Reduce-only/provider fields | Current design result |
|---|---|---|---|---|---|---|---|---|
| `ENTRY` | exact E5 ApprovedTradePlan, `entry-v0.1`, `base-asset-v0.1` | `MUTATION: MARKET_ORDER_CREATE` | LONG->BUY; SHORT->SELL | acctLv=2; `net_mode` and `long_short_mode` repository-evidenced for ENTRY only | isolated | E5-approved canonical BTC upper bound -> current metadata sizing; never round above bound | existing entry row uses `instId/tdMode/clOrdId/side/posSide/ordType/sz`; no trigger/price/TIF; do not invent reduce flag | `REPO_EVIDENCED` mapping only; still no authority from this docs task |
| `PROTECTION_STOP` | `protection-v0.1` PROTECT + parent plan + current Position + current FP-03 ACTIONABLE CREATE evidence | `MUTATION: PROTECTION_TRIGGER_CREATE` | LONG->SELL; SHORT->BUY | acctLv=2/isolated are baseline candidates; both `net_mode` and `long_short_mode` role-specific mutation mappings remain unproven | isolated baseline | exact current protected exposure; provider role conversion not inferred from entry sizing | shared `reduce_only=true` is intent only; endpoint/posSide/reduce field/order algorithm/trigger fields/trigger basis unresolved | `UNRESOLVED_FAIL_CLOSED`; shared LAST_PRICE never selects provider trigger basis; FP-11 readback/multiplicity dependency |
| `POSITION_EXIT` | exact `close-v0.1` EXIT + parent plan + current CONSISTENT Position | `MUTATION: REDUCE_POSITION_MARKET` | LONG->SELL; SHORT->BUY | acctLv=2/isolated candidates; net/long-short role mapping unproven | isolated baseline | exact current Position actual quantity; provider-native reducible sizing must come from FP-05 | shared `reduce_only=true` is not provider proof; provider `posSide`, reduce field, endpoint and native `sz` semantics unresolved | `UNRESOLVED_FAIL_CLOSED`; original entry requested quantity is forbidden as substitute |
| `EMERGENCY_EXIT` | exact `close-v0.1` EMERGENCY_EXIT from E5 EMERGENCY + current CONSISTENT Position | `MUTATION: REDUCE_POSITION_MARKET_EMERGENCY` | LONG->SELL; SHORT->BUY | same unresolved role-specific provider mapping as POSITION_EXIT | isolated baseline | exact current Position actual quantity + FP-05 provider-native reducible sizing | emergency urgency never waives provider field/mode proof | `UNRESOLVED_FAIL_CLOSED` until FP-05 + exact provider role row |
| `READ_ONLY_RECONCILIATION` | explicit E4 read-only observation/reconciliation invocation under accepted operational governance | `GET: OBSERVATION_ONLY` | N/A | acctLv=2; expected `net_mode|long_short_mode` must match observed account config | accepted trading baseline observes isolated leverage | no order quantity | GET-only/default-deny; no reduce/side/order mutation fields | `REPO_EVIDENCED`; existing fixed production Shadow GET set only; any mutation/nonallowlisted path forbidden |

### 4. Key fail-closed design decisions

The design explicitly prevents:

- Spot `tdMode=cash` transplantation into BTC-USDT-SWAP;
- guessing account level/position mode from configuration without matching observed capability facts;
- copying ENTRY `posSide` semantics into protection/close roles;
- using original requested entry quantity for `POSITION_EXIT` or `EMERGENCY_EXIT`;
- treating shared `reduce_only=true` as equivalent to OKX-native compatibility;
- treating FP-03 `LAST_PRICE` as provider `triggerPxType` authority;
- silently omitting/defaulting unknown provider fields;
- a caller boolean/mapping/constructed clone manufacturing capability PASS;
- mutation preparation when account/instrument/margin/position-mode facts are unknown;
- blind retry after ambiguous mutation outcome.

Provider-local planned reason vocabulary is documented in the design artifact and remains E4 implementation scope, not a shared-contract enum.

### 5. Unresolved provider-specific facts

The following are intentionally unresolved and therefore fail closed:

1. exact provider mutation endpoint/order-algorithm/field set for `PROTECTION_STOP`;
2. exact OKX provider trigger reference/basis mapping for protection;
3. exact role-specific `posSide` and native reduce semantics for protection/exit/emergency under `net_mode` and `long_short_mode`;
4. provider-native protective quantity conversion constraints beyond the shared canonical quantity requirement;
5. provider-native reducible close quantity, lot/minimum/residual behavior for exit roles (FP-05);
6. provider protection multiplicity/readback/registry convergence (FP-11, with later FP-04 ownership semantics);
7. current real provider/account/instrument verification for this matrix revision/profile.

None is guessed in the design.

### 6. Shared-contract dependency / proposal

```text
new shared E7 contract field/profile required by this design = NO
```

Existing shared objects already carry sufficient cross-module authority for an E4-local provider capability key: canonical symbol/side/quantity, PositionAction/role lineage, current Position truth, and FP-03 evidence for protection.

Provider `tdMode`, `posSide`, native reduce flags, trigger fields, provider order classes and contract `sz` remain E4-local adapter facts.

If later provider implementation proves that a missing fact must be supplied by another module as authority rather than observed/derived inside E4, E4 must raise a precise E7 contract change request. No such change is invented here.

### 7. Future deterministic implementation paths and test plan

Smallest later E4 executable boundary:

```text
src/brokers/okx_capabilities.py   # suggested name only
```

Expected semantics:

- immutable closed table keyed by exact provider/API/instrument/role/account level/position mode/margin mode;
- inputs come from validated E4 account/instrument observations and canonical execution objects;
- no caller `compatible=True` or arbitrary mapping can create authority;
- exactly one accepted row or deterministic fail-closed reason;
- resolved row becomes adapter-owned immutable preparation fact;
- endpoint/method/field allowlist derives from the accepted row;
- ENTRY may route through current repository-evidenced mapping;
- READ_ONLY remains current GET-only/default-deny;
- PROTECTION_STOP remains blocked until exact trigger/order fields and FP-11 readback are accepted;
- exits remain blocked until FP-05 reducible sizing and exact provider field rows are accepted;
- ambiguity enters reconciliation before retry.

Required later credential-free local tests include:

- every role resolves only through one accepted row;
- unknown account level/position mode/margin mode fails closed;
- Spot-only values reject before dispatch;
- exact provider field-set enforcement;
- ENTRY mode mappings remain role-scoped;
- protection cannot infer provider trigger basis from FP-03 LAST_PRICE;
- exit/emergency reject without FP-05 provider-native reducible sizing;
- caller assertion/clone cannot manufacture PASS;
- read-only remains GET-only/default-deny;
- existing submit-integrity/idempotency/reconciliation regressions remain intact;
- no provider network or credentials required for deterministic fixtures.

Suggested later test surface:

```text
tests/brokers/test_okx_swap_capabilities.py
tests/brokers/test_okx_demo_adapter.py
tests/brokers/test_okx_submit_integrity.py
tests/brokers/test_okx_shadow.py
tests/brokers/test_okx_sizing.py
tests/execution/test_protection_trigger_consumer.py
tests/execution/test_close.py
```

No test/source changes were made in E4-026.

### 8. Relationship to FP-05 and FP-11

FP-02 provides provider action-role vocabulary needed before safe provider mapping.

```text
FP-02
-> later E4 provider capability implementation
-> FP-05 provider-native close/residual sizing
-> FP-11 provider protection mapping/readback
```

`POSITION_EXIT` and `EMERGENCY_EXIT` remain non-executable until FP-05 resolves authoritative provider-native reducible sizing/residual behavior.

`PROTECTION_STOP` remains non-executable at provider mutation until its exact provider trigger/order mapping is proven and FP-11 later supplies intended active-protection multiplicity/readback convergence; FP-04 will govern ownership of external/orphan objects.

### 9. Local verification

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK
```

No project code/tests were executed.

### 10. Security / secrets

```text
provider requests = 0
private API = NONE
credentials = NONE
real secrets read/requested/used = NO
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER/live-fire runtime = NOT_STARTED
capital exposure = NONE
```

No credentials or secret values were added to repository artifacts.

### 11. GitHub compute policy

```text
GitHub Actions/CI = NOT_USED
GitHub-hosted runner = NOT_USED
GitHub-triggered self-hosted runner = NOT_USED
GitHub compute = NOT_USED
```

GitHub was used only for source/document collaboration and branch commits.

### 12. Live-trading impact

This docs-only matrix cannot alter exposure, place orders, change position sizing, mutate protection, enable runtime, or authorize live trading.

```text
10U live-fire = NOT_AUTHORIZED
Gate D = NOT_AUTHORIZED
LIVE = NOT_AUTHORIZED
```

### 13. Required next action

E7/PM may statically review this E4-owned design. Do not treat design acceptance as executable PASS.

A later separately dispatched E4 executable FP-02 task may implement the provider-local capability resolver after governance chooses the integrated P0 sequencing. That later executable revision requires approved-local credential-free verification and fresh exact-revision qualification under the accepted readiness profile.

E4-026 stops here and does not self-start executable FP-02, FP-05, FP-11, provider verification, SHADOW/PAPER, live-fire, Gate D or LIVE.