# OKX SWAP Action-Role Capability Matrix — V0.1

> Profile identifier: `okx-swap-action-role-capability-v0.1`  
> Owner: E4 Trading Execution / Broker Integration  
> Task: `E4-20260829-026`  
> Baseline `main`: `a372949ea41c19539275a13b207c2fafd9c05ab5`  
> Status: `DESIGN BASELINE / DOCS ONLY / NOT EXECUTABLE AUTHORITY`

## 1. Purpose

This document defines the E4-owned provider capability vocabulary for the current OKX perpetual-SWAP target so a later provider translator can resolve one explicit action role to one explicit, proven provider capability row before dispatch.

It closes the FP-02 **design** gap only. It does not implement provider translation and grants no provider/private API, credential, mutation, order, runtime, Gate D, LIVE, or capital authority.

The core rule is:

```text
shared OrderRequest / PositionAction semantics
+ exact E4 provider/account/instrument capability facts
+ exact action role
-> one accepted capability row
-> later provider translation may proceed

anything missing / unknown / unsupported / unproven
-> fail closed before provider dispatch
```

A shared `reduce_only=true`, a caller boolean, a caller dictionary, a configured position mode, or FP-03 `LAST_PRICE` evidence is never by itself proof that an OKX provider field/value combination is valid.

## 2. Provider target and evidence baseline

Current target identity:

```text
provider                 = OKX
api_version              = V5
canonical instrument     = BTC_USDT_PERP
provider instrument      = BTC-USDT-SWAP
provider instrument type = SWAP
contract conversion      = current V1 direct linear/base-asset path only
margin baseline          = isolated
```

Current repository evidence establishes the following bounded facts:

- `src/brokers/okx_demo.py` accepts only `acctLv=2` and explicitly configures `net_mode | long_short_mode` for the current isolated BTC-USDT-SWAP **entry** adapter.
- Current entry materialization uses provider `tdMode=isolated`, provider `ordType=market`, provider `side=buy|sell`, provider `posSide=net` in `net_mode`, and provider `posSide=long|short` for entry in `long_short_mode`.
- Current entry provider quantity is recomputed from validated current SWAP metadata (`ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `maxMktSz` where present) and may round down but never above the E5-approved canonical BTC exposure.
- `src/brokers/okx_shadow.py` is production read-only, GET-only/default-deny, accepts only `acctLv=2` with expected `net_mode | long_short_mode`, and uses an isolated leverage query for `BTC-USDT-SWAP`.
- Existing submit-integrity tests prove that caller-mutated provider fields and caller-constructed materialization clones are rejected before transport on the existing bounded entry path.
- Existing shared protection/close profiles define canonical E4 order roles and side/quantity authority, but do **not** prove the OKX provider-native field set for those roles.

Historical provider-facing evidence is revision-bound and is not rebound to this matrix. This task performs no provider/private verification.

## 3. Capability-state vocabulary

These labels describe design evidence; they are not release states and are not shared E7 contract values.

| State | Meaning |
|---|---|
| `REPO_EVIDENCED` | Current repository code/tests define the stated mapping for the named bounded role. It is not new provider verification and does not grant runtime authority. |
| `UNRESOLVED_FAIL_CLOSED` | Provider-native semantics are not proven for the role/mode combination. A later translator must reject before dispatch. |
| `FORBIDDEN` | The combination contradicts the accepted SWAP baseline or imports unsupported Spot/other semantics. |
| `NOT_APPLICABLE` | The field has no semantic meaning for that role and must not be manufactured. |

For mutation roles, `REPO_EVIDENCED` still means only that repository mapping exists; actual provider mutation remains separately gated.

## 4. Provider-local fail-closed reason vocabulary

The later E4 resolver should use stable provider-local reason codes equivalent to the following. These are E4 implementation vocabulary, not new shared-contract enums.

| Reason | Trigger |
|---|---|
| `OKX_SWAP_CAPABILITY_PROFILE_UNSUPPORTED` | profile missing/unknown/not `okx-swap-action-role-capability-v0.1` |
| `OKX_SWAP_ACTION_ROLE_UNSUPPORTED` | role missing/unknown |
| `OKX_SWAP_INSTRUMENT_UNSUPPORTED` | canonical/provider instrument or `instType=SWAP` binding not exact |
| `OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED` | account level missing/unknown/not accepted `acctLv=2` |
| `OKX_SWAP_POSITION_MODE_UNSUPPORTED` | position mode missing/unknown/not accepted for the exact role row |
| `OKX_SWAP_MARGIN_MODE_UNSUPPORTED` | required margin mode missing/unknown/not `isolated` for the current mutation baseline |
| `OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN` | `tdMode=cash` or another Spot-only trade-mode semantic appears |
| `OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN` | provider endpoint/field/value combination is not explicitly defined by an accepted role row |
| `OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED` | caller boolean/mapping/claimed capability attempts to create capability authority |
| `OKX_SWAP_TRIGGER_BASIS_UNPROVEN` | protection path attempts to infer provider trigger basis from shared FP-03 `LAST_PRICE` evidence |
| `OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN` | exit role lacks FP-05 authoritative provider-native reducible-size proof |
| `OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT` | protection create/readback requires FP-11 multiplicity/current registry truth that is absent/unknown |
| `OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN` | any mutation is requested through the read-only reconciliation role |
| `OKX_SWAP_RECONCILIATION_REQUIRED` | an ambiguous provider outcome has not been reconciled; retry/mutation remains blocked |

Unknown provider field/value combinations must be rejected with `OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN`; omission/defaulting is not a compatibility strategy.

## 5. Summary action-role capability table

| Role | Upstream authority | Operation class | Canonical side | acctLv | Position mode | Margin | Quantity source | Shared `reduce_only` meaning | Provider-native fields | Status / mandatory fail-closed dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| `ENTRY` | exact E5 `ApprovedTradePlan`, `entry-v0.1`, `base-asset-v0.1` | `MUTATION: MARKET_ORDER_CREATE` | LONG -> BUY; SHORT -> SELL | `2` only | `net_mode`: repo-evidenced; `long_short_mode`: repo-evidenced for entry only | `isolated` | E5 approved canonical BTC max exposure -> current entry sizing metadata conversion | not an entry authority; provider `reduceOnly` must not be invented from shared absence | current bounded entry row: `instId`, `tdMode=isolated`, `clOrdId`, `side`, `posSide`, `ordType=market`, `sz`; no trigger/price/TIF | repository-evidenced entry mapping only; unknown account/mode/margin/metadata -> fail closed |
| `PROTECTION_STOP` | exact `protection-v0.1` `PositionAction.PROTECT` + parent plan + current Position + current FP-03 `ACTIONABLE` CREATE evidence | `MUTATION: PROTECTION_TRIGGER_CREATE` | LONG Position -> SELL; SHORT Position -> BUY | `2` is required baseline candidate, but role-specific provider row remains unproven | `net_mode`: unresolved; `long_short_mode`: unresolved | `isolated` baseline; provider role semantics unproven | exact current canonical protected exposure from PositionAction; provider role conversion must be separately proven | shared `true` is required canonical intent but does not prove any OKX native flag/value | endpoint/order-algorithm/trigger fields/trigger basis/posSide/native reduce semantics are explicitly unresolved | `UNRESOLVED_FAIL_CLOSED`; FP-03 does not select provider `triggerPxType`; FP-11 required for multiplicity/readback convergence |
| `POSITION_EXIT` | exact `close-v0.1` E5 `PositionAction.EXIT` + parent plan + current CONSISTENT Position | `MUTATION: REDUCE_POSITION_MARKET` | LONG Position -> SELL; SHORT Position -> BUY | `2` baseline candidate; role-specific row unproven | `net_mode`: unresolved; `long_short_mode`: unresolved | `isolated` baseline | exact current Position actual quantity, then FP-05 provider-native reducible sizing | shared `true` is canonical close intent only; provider native semantics unproven | shared order type is MARKET; exact OKX role field set/posSide/reduce field/native `sz` semantics unresolved | `UNRESOLVED_FAIL_CLOSED` until FP-05 + role mapping; never use original entry requested quantity |
| `EMERGENCY_EXIT` | exact `close-v0.1` E5 `PositionAction.EMERGENCY_EXIT` from E5-owned EMERGENCY lifecycle + parent plan + current CONSISTENT Position | `MUTATION: REDUCE_POSITION_MARKET_EMERGENCY` | LONG Position -> SELL; SHORT Position -> BUY | `2` baseline candidate; role-specific row unproven | `net_mode`: unresolved; `long_short_mode`: unresolved | `isolated` baseline | exact current Position actual quantity, then FP-05 provider-native reducible sizing | shared `true` is canonical close intent only; emergency does not waive provider proof | shared order type is MARKET; exact OKX field set/posSide/reduce field/native `sz` semantics unresolved | `UNRESOLVED_FAIL_CLOSED` until FP-05 + role mapping; emergency urgency never authorizes guessing |
| `READ_ONLY_RECONCILIATION` | explicit E4 read-only observation/reconciliation invocation under accepted operational governance; no trade authority is created | `GET: OBSERVATION_ONLY` | `NOT_APPLICABLE` | `2` only for accepted current Shadow config | expected `net_mode | long_short_mode`; exact observed mode must match explicit config | supported trading baseline expects isolated leverage; contradiction remains non-healthy | observation only; no order `sz` | `NOT_APPLICABLE`; must not appear as a mutation field | current production Shadow allowlist only: account config, USDT balance, positions, isolated leverage info, pending SWAP orders, SWAP fills, plus public time | `REPO_EVIDENCED` GET-only/default-deny; any POST/mutation or nonallowlisted private path -> fail closed |

## 6. Role details

### 6.1 `ENTRY`

**Purpose.** Create new exposure only from an exact E5-approved entry plan.

**Authority.** Exact `ApprovedTradePlan` using `entry-v0.1` and `base-asset-v0.1`; raw Signal/TradeIntent never qualifies.

**Operation class.** `MUTATION: MARKET_ORDER_CREATE`. The existing Demo adapter currently materializes this bounded role through `/api/v5/trade/order`, but that endpoint use is evidence for ENTRY only and must not be inherited by another role by analogy.

**Side semantics.** Canonical LONG -> BUY, SHORT -> SELL. Existing provider entry mapping is `buy|sell` respectively.

**Account/position modes.** `acctLv=2` only. Existing E4 entry config explicitly retains both `net_mode` and `long_short_mode`:

```text
net_mode:
  BUY/SELL -> posSide=net

long_short_mode entry:
  BUY  -> posSide=long
  SELL -> posSide=short
```

These exact mappings are role-scoped to ENTRY. They are not proof for protection/exit.

**Margin.** `tdMode=isolated`. `cash` is forbidden. Cross/multi-currency/portfolio assumptions are not accepted for this V0.1 row.

**Quantity.** E5-approved canonical BTC is an upper exposure bound. Provider `sz` must be recomputed from current validated linear SWAP metadata and never exceed the canonical bound. Caller sizing evidence is audit evidence only.

**Reduce-only.** Entry does not obtain authority from shared `reduce_only`; the current bounded entry body does not manufacture a provider reduce-only field. A future field addition requires an explicit role row.

**Provider-native fields.** Current bounded entry row requires the exact issued field set:

```text
instId = BTC-USDT-SWAP
tdMode = isolated
clOrdId = adapter-derived stable provider client ID
side = buy | sell
posSide = role/mode-specific mapping above
ordType = market
sz = provider contracts from validated current metadata
```

Executable price, stop, trigger and TIF fields are forbidden for `entry-v0.1` MARKET.

**Identity.** Existing stable E4 internal `client_order_id` -> deterministic legal OKX `clOrdId`. A direct caller clone or mutated materialization is not authority.

**Ambiguity.** Provider ACK is not Fill truth. Timeout/ambiguous outcome -> `RECONCILIATION_REQUIRED`; query/reconcile before any retry. No blind second create.

**Fail closed.** Unknown account level, unexpected mode, wrong margin, missing/stale/incompatible metadata, provider field mutation, pending orders, existing exposure, or untrusted materialization blocks dispatch.

**FP dependencies.** FP-05 does not govern new-entry sizing; current entry sizing exists. FP-11 becomes relevant after exposure exists and protection must be established/read back.

### 6.2 `PROTECTION_STOP`

**Purpose.** Establish the exact E5-authorized protective stop for already-open exposure.

**Authority.** All existing `protection-v0.1` authority/quantity/expiry/reconciliation/idempotency requirements, plus exact current `protection-trigger-validity-v0.1` evidence with:

```text
validity_status = ACTIONABLE
reason_codes = [PROTECTION_TRIGGER_ACTIONABLE]
order_role = PROTECTION_STOP
protection_operation = CREATE
```

**Operation class.** `MUTATION: PROTECTION_TRIGGER_CREATE` design vocabulary only. No provider endpoint or mutation path is approved by this matrix task.

**Side semantics.** LONG Position -> SELL protection; SHORT Position -> BUY protection.

**Account/position modes.** `acctLv=2` and isolated are the only baseline candidates, but neither `net_mode` nor `long_short_mode` has an accepted role-specific provider mutation row for protection. Both therefore remain `UNRESOLVED_FAIL_CLOSED` for provider dispatch.

**Quantity.** Exact current PositionAction quantity in canonical BTC. Entry requested quantity and parent plan maximum are not substitutes. Provider contract conversion/rounding for a protection role must be proven separately; current entry sizing code is not silently reused as role authority.

**Reduce-only.** Canonical `OrderRequest.reduce_only=true` expresses shared safety intent. It is not proof that an OKX native `reduceOnly` field is required, allowed, forbidden, omitted, or sufficient for this role/mode.

**Provider-native position/trigger fields.** Unresolved. In particular:

- ENTRY `posSide` mapping may not be copied by analogy;
- FP-03 `trigger_reference_semantic=LAST_PRICE` is shared pre-mutation geometry only;
- it does not select `triggerPxType`, `last`, `mark`, `index`, or any provider-native trigger basis;
- provider conditional/algo endpoint, trigger field names, order type, reduce field, attached-order/OCO semantics, and exact readback identity are unresolved until an accepted E4 provider capability row proves them.

**Identity.** Shared protection identity remains stable for `(position_action_id, PROTECTION_STOP)`. A future provider client identity must be deterministically bound to that exact logical action and issued by the adapter/capability boundary, not caller supplied.

**Ambiguity/readback.** Unknown/ambiguous create result -> reconciliation; no blind retry. FP-11 must later establish exactly-one intended active protection lineage and classify missing/multiple/orphan/external protection under the accepted ownership policy.

**Fail closed.** Missing/failed/stale FP-03 evidence, unsupported role field set, unknown provider trigger basis, unknown account/mode/margin facts, or absent/currently-unproven registry capability blocks mutation.

### 6.3 `POSITION_EXIT`

**Purpose.** Close/reduce an existing position under ordinary E5 EXIT authority.

**Authority.** Exact `close-v0.1` PositionAction.EXIT + exact parent plan + exact current CONSISTENT Position. Canonical role is `POSITION_EXIT`.

**Operation class.** `MUTATION: REDUCE_POSITION_MARKET` design vocabulary only.

**Side semantics.** LONG Position -> SELL; SHORT Position -> BUY.

**Account/position modes.** `acctLv=2` / isolated are baseline candidates. Provider-native field behavior for both `net_mode` and `long_short_mode` is unresolved for this role and therefore non-executable.

**Quantity.** Source is exact current Position actual quantity, not original entry requested quantity. Before provider translation, FP-05 must define and prove provider-native reducible sizing, lot/minimum/quantization/residual semantics against current metadata and provider exposure truth.

**Reduce-only.** Shared close request requires `reduce_only=true`; that is not equivalent to proven OKX provider-native compatibility. A translator must not assume field presence/value or omit it silently.

**Provider-native fields.** Shared `order_type=MARKET`; provider endpoint, exact `posSide`, exact reduce field behavior, provider `sz`, and any close-specific field set remain unresolved pending FP-02 executable implementation plus FP-05 sizing semantics.

**Identity.** Stable `(position_action_id, POSITION_EXIT)` logical identity. Materially newer Position/residual truth requires a new E5 action and therefore new logical order identity.

**Ambiguity/readback.** ACK/FILLED order state never proves flat Position by itself. Ambiguous outcome -> reconcile exact order/fills/Position; no blind retry. Definitive residual exposure returns through authoritative Position truth.

**Fail closed.** Unknown capability row or absent FP-05 reducible sizing -> `OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN` before dispatch.

**FP-11 relation.** Exit completion must not leave an orphan/duplicate protection state. Later registry/readback/cleanup semantics belong to FP-11/FP-04 and must be reconciled separately rather than inferred from the exit ACK.

### 6.4 `EMERGENCY_EXIT`

**Purpose.** Reduce/close an existing position under exact E5 EMERGENCY_EXIT authority. Urgency does not grant provider-parameter authority.

**Authority.** Exact `close-v0.1` PositionAction.EMERGENCY_EXIT produced from E5-owned EMERGENCY lifecycle truth + exact current CONSISTENT Position.

**Operation class.** `MUTATION: REDUCE_POSITION_MARKET_EMERGENCY` design vocabulary only.

**Side/quantity.** Same canonical mechanical direction as ordinary close: LONG -> SELL, SHORT -> BUY; quantity is exact current Position actual quantity. FP-05 still governs provider-native reducible sizing and residual semantics.

**Account/position/margin.** Same fail-closed provider capability requirements as `POSITION_EXIT`; no emergency bypass of unknown account/mode/margin/provider fields.

**Reduce-only/provider fields.** Shared `reduce_only=true` remains canonical safety intent only. Exact OKX field set is unresolved and must be proven role/mode specifically.

**Identity.** Stable `(position_action_id, EMERGENCY_EXIT)` logical identity; must remain distinct from ordinary exit.

**Ambiguity.** Emergency urgency never authorizes duplicate blind submit. Ambiguous outcome remains reconciliation-required until authoritative provider/Position truth converges.

**FP-11 relation.** Active protection cleanup/multiplicity remains separate provider truth and cannot be assumed from emergency close submission.

### 6.5 `READ_ONLY_RECONCILIATION`

**Purpose.** Observe account/instrument/order/fill/Position facts needed for health and reconciliation without creating trade authority.

**Authority.** Explicit read-only operational invocation and exact validated E4 read-only configuration. It does not require an E5 trade decision because it cannot mutate exposure, but its output may only be consumed under the existing E4/E5/E6 authority boundaries.

**Operation class.** `GET: OBSERVATION_ONLY`.

**Current allowlist.** The production Shadow reader currently permits only the exact fixed batch:

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP
GET /api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP
```

plus unauthenticated public provider time. Current production Shadow does **not** make a generic request surface reachable and does not expose submit/cancel/amend/close/mode/leverage mutation methods.

**Account/mode.** `acctLv=2`; expected mode may be `net_mode` or `long_short_mode`, but the exact observed account mode must match the explicit configuration. Configuration is expectation, not proof; provider observation must confirm it.

**Margin.** The accepted trading baseline is isolated and the current leverage observation is explicitly queried with `mgnMode=isolated`. A contradictory current provider state does not become mutation-capable.

**Quantity/reduce-only/side.** No order quantity, no `reduceOnly`, and no order-side mutation fields are applicable.

**Readback/checkpoint.** Pending/fill observations are reconciliation evidence. Stable checkpoints may prove already-reconciled recent fill windows, but unknown/new activity fails closed for automation.

**Fail closed.** Non-GET, nonallowlisted private path, write-capable credential permission, account/mode mismatch, clock skew, unknown provider facts, unexpected exposure/pending/fills, or any mutation request blocks the read-only capability.

## 7. Cross-role invariants

The later executable resolver must enforce all of these before any mutation materialization:

1. **Role is explicit.** Do not derive action role from side, order type, `reduce_only`, endpoint, or presence of a stop field.
2. **Provider identity is exact.** Only OKX V5 / `BTC_USDT_PERP` -> `BTC-USDT-SWAP` / `instType=SWAP` belongs to V0.1.
3. **No Spot transplantation.** `tdMode=cash` is always forbidden in this SWAP matrix. Spot-specific reduce/order/ccy assumptions are not defaults.
4. **Account facts are observed and matched.** Caller configuration declares expected state; it cannot replace current provider/account observation where the role requires provider truth.
5. **Mode is role-scoped.** Existing ENTRY `posSide` semantics do not prove protection/exit semantics.
6. **Margin is explicit.** Current mutation baseline is isolated. Unknown/cross/other mode is not silently coerced.
7. **Quantity source is role-scoped.** ENTRY uses E5 approved new-exposure upper bound; PROTECTION/EXIT use current actual open exposure authority; provider-native units are adapter facts.
8. **`reduce_only` is not provider compatibility proof.** Shared boolean intent never creates an OKX capability row.
9. **Provider field sets are closed sets.** Unknown provider field/value -> reject; do not omit/default to “make it work.”
10. **No caller-manufactured PASS.** A boolean like `provider_capable=True`, arbitrary mapping, or caller-constructed capability object cannot authorize dispatch.
11. **Adapter-issued materialization remains the trust boundary.** Later implementation should preserve the existing submit-integrity pattern where the issuing adapter/capability resolver owns immutable preparation facts and rejects clones/tampering.
12. **Ambiguous outcome is stable.** Reconciliation/readback precedes retry for every mutation role.
13. **Provider evidence is revision-bound.** Historical provider observations cannot prove this new matrix on another revision.

## 8. Dependency boundaries

### 8.1 FP-03 — trigger validity

`PROTECTION_STOP` requires exact current `protection-trigger-validity-v0.1` ACTIONABLE CREATE evidence immediately before mutation. This proves shared trigger geometry/currentness only.

It explicitly does **not** prove provider trigger basis or provider conditional-order fields.

### 8.2 FP-05 — provider-native close/residual sizing

`POSITION_EXIT` and `EMERGENCY_EXIT` remain non-executable at provider translation until FP-05 defines authoritative:

- current provider-native reducible quantity;
- contract/lot/minimum quantization;
- residual representation/wait/retry semantics;
- no over-reduction invariant;
- canonical/provider quantity traceability.

The original entry requested quantity is never accepted as a close substitute.

### 8.3 FP-11 — protection registry/multiplicity

`PROTECTION_STOP` later requires an authoritative registry/readback path proving intended protection lineage and allowed active count. Missing/multiple/orphan/unknown protection must fail closed under FP-11 plus the future FP-04 ownership policy.

Exit/emergency convergence must also reconcile protection cleanup/readback instead of assuming protection disappears because a close order was submitted.

## 9. Shared-contract boundary

This design does not prove a new shared E7 field/profile is necessary.

Existing shared facts are sufficient for the provider-local capability key:

- canonical `symbol`;
- E4 action role (`ENTRY` internal entry context or shared `order_role` for PositionAction requests);
- canonical `side` / Position side;
- canonical quantity/profile/unit/asset;
- E5 action/plan lineage;
- current Position truth;
- FP-03 evidence for protection;
- E4 provider/account/instrument observations/configuration.

Provider `tdMode`, `posSide`, provider reduce flags, trigger fields, provider order classes and contract `sz` remain E4-local adapter facts.

If later provider-specific work proves a cross-module authority fact is missing, E4 must submit a precise E7 contract change request rather than add it here or infer it from provider fields.

## 10. Smallest later executable implementation boundary

No executable change is made by E4-026. The smallest later E4 implementation should be one provider-local capability resolver, for example:

```text
src/brokers/okx_capabilities.py
```

with an internal immutable table keyed by exact facts such as:

```text
profile_version
provider/api version
canonical/provider instrument
role
account level
position mode
margin mode
```

Recommended behavior:

1. input types are validated E4 account/instrument observations and canonical E4 execution objects; do not accept a caller `compatible=True` boolean as authority;
2. resolver selects exactly one closed capability row or raises one stable fail-closed reason;
3. ENTRY may initially route through the already-defined repository-evidenced row;
4. READ_ONLY remains the current GET-only/default-deny Shadow surface and must not gain mutation methods;
5. PROTECTION_STOP remains blocked until exact provider conditional-order fields, mode semantics, trigger basis and FP-11 readback are accepted;
6. POSITION_EXIT/EMERGENCY_EXIT remain blocked until FP-05 provider-native reducible sizing plus exact role/mode field sets are accepted;
7. the resolved row is copied into adapter-owned immutable preparation facts; caller clones/tampering fail before transport;
8. endpoint/method allowlists are role-derived from the accepted row, not caller supplied;
9. provider materialization and submit remain separate phases; ambiguous outcome enters reconciliation, not automatic retry.

A later task may choose different internal names while preserving these semantics.

## 11. Required later deterministic credential-free tests

A later executable FP-02 implementation must add local-only deterministic tests covering at minimum:

1. every accepted action role resolves only through one accepted capability row;
2. unknown/missing profile, provider, instrument, role, account level, position mode or margin mode fails closed;
3. `acctLv=1|3|4`, Spot `tdMode=cash`, unknown `posMode`, cross/unknown mutation margin and unsupported instrument values reject before transport;
4. provider field set is exact; unknown/extra/missing role-sensitive fields fail closed before dispatch;
5. existing ENTRY net-mode mapping remains `posSide=net` and existing retained long/short ENTRY mapping remains direction-correct;
6. no ENTRY mapping is reusable as PROTECTION_STOP/POSITION_EXIT/EMERGENCY_EXIT by changing only side or `reduce_only`;
7. FP-03 shared `LAST_PRICE` evidence does not select/authorize a provider trigger basis or provider trigger field;
8. PROTECTION_STOP rejects while its provider role row or FP-11 registry/readback proof is unresolved;
9. POSITION_EXIT and EMERGENCY_EXIT reject until FP-05 supplies authoritative provider-native reducible sizing; original requested entry quantity never satisfies this dependency;
10. a caller boolean/mapping/constructed clone cannot manufacture capability PASS;
11. adapter-issued immutable preparation facts reject tampering/cross-adapter reuse as current submit-integrity behavior does;
12. ambiguous mutation ACK/result blocks retry until reconciliation/readback proves state;
13. READ_ONLY_RECONCILIATION remains GET-only/default-deny and exposes no submit/cancel/amend/close/set-mode mutation capability;
14. deterministic fixtures use fake/sanitized values only and require no provider network or credentials;
15. all existing E4 broker/execution safety regressions remain required on the approved local non-GitHub environment.

Expected future test surfaces may include:

```text
tests/brokers/test_okx_swap_capabilities.py
tests/brokers/test_okx_demo_adapter.py
tests/brokers/test_okx_submit_integrity.py
tests/brokers/test_okx_shadow.py
tests/brokers/test_okx_sizing.py
tests/execution/test_protection_trigger_consumer.py
tests/execution/test_close.py
```

Exact suite selection remains a later executable task and E7 qualification concern.

## 12. Verification and authority status

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK
provider/private requests        = 0
credentials                      = NONE
provider/account mutation        = 0
order submit/cancel/amend/close  = 0
SHADOW/PAPER runtime             = NOT_STARTED
10U live-fire                    = NOT_AUTHORIZED
Gate D / LIVE                    = NOT_AUTHORIZED
capital exposure                 = NONE
GitHub Actions/CI/hosted compute = NOT_USED
```

This matrix is design evidence only. `NOT_RUN` is not executable PASS and `REPO_EVIDENCED` is not new provider verification.