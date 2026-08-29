# Protection Trigger Validity Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Companion profile identifier: `protection-trigger-validity-v0.1`  
> Companion to: `protection-v0.1` and future explicitly approved protection-modification profiles  
> Status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260829-099`

## 1. Purpose

`protection-v0.1` already defines the safe authority and quantity chain for initial protective stops:

```text
exact E4 Position truth
+ exact E5 ApprovedTradePlan / PositionAction.PROTECT
-> E4 PROTECTION_STOP OrderRequest
-> broker truth
-> E5 lifecycle interpretation
```

It does not define whether an intended stop trigger is still actionable against current market truth at the moment immediately preceding a protection create/replace attempt. That omission permits an otherwise lineage-valid stop to be prepared after price has already reached or crossed the intended trigger.

This profile adds a provider-neutral, deterministic, fail-closed validity-evidence boundary for that missing question. It does not choose E5 lifecycle policy and does not choose OKX provider trigger parameters.

The profile prevents this unsafe interpretation:

```text
valid protection authority + positive stop price
!= automatic permission to mutate a provider protection order
```

Execution still requires all existing `protection-v0.1` authority, quantity, reconciliation, idempotency and provider-capability checks.

## 2. Compatibility and versioning

Classification:

```text
ADDITIVE_COMPANION_PROFILE
schema_version = contracts-v0.1 / unchanged
protection_profile_version = protection-v0.1 / unchanged
companion_profile = protection-trigger-validity-v0.1
```

No existing shared profile is amended or reinterpreted.

Reasoning:

1. `contracts-v0.1` already defines `MarketSnapshot`, `Position`, `PositionAction`, `OrderRequest`, fail-closed state and E1/E4/E5 authority boundaries;
2. `protection-v0.1` already binds the exact Position observation, action identity, stop bound and canonical quantity but never defines current-market trigger geometry;
3. the missing object is evidence about whether a specific already-authorized trigger remains actionable at a specific current-market boundary;
4. legacy protection objects remain valid for their existing meaning but are not sufficient by themselves to prove trigger actionability;
5. consumers that require this profile must fail closed when the evidence is absent, unsupported, stale or no longer current;
6. no provider trigger-price type, risk threshold, quantity rule, lifecycle transition or existing object identity is changed.

No additional ADR is required because this profile fills an underspecified shared evidence boundary without changing architecture or authority direction.

## 3. Scope

V0.1 evaluates one intended protective-stop mutation for the canonical current instrument family:

```text
BTC_USDT_PERP
```

The evidence may be used for:

- initial `PROTECT` / `PROTECTION_STOP` create, when already executable under `protection-v0.1`;
- a future protection replacement only after a separate E7-approved executable `MODIFY_PROTECTION` profile exists.

This profile does **not** make baseline `MODIFY_PROTECTION` executable. A `REPLACE` validity result is only a prerequisite for a future separately authorized replacement path.

## 4. Shared evidence object

Canonical shared evidence object:

```text
ProtectionTriggerValidityEvidence
```

Required fields:

- `schema_version` — exactly `contracts-v0.1`
- `protection_trigger_validity_profile_version` — exactly `protection-trigger-validity-v0.1`
- `protection_trigger_validity_id` — deterministic identity defined in section 12
- `position_action_id` — exact E5 protection authority being screened
- `position_id` — exact current Position identity
- `position_side` — `LONG | SHORT`
- `position_authority_type` — `BROKER_POSITION_OBSERVATION | LIFECYCLE_PROJECTION`
- `position_authority_ref` — exact canonical reference/hash to the Position authority consumed
- `position_observed_at` — exact `Position.broker_state_observed_at`
- `position_reconciliation_status` — exactly the status consumed; actionability requires `CONSISTENT`
- `lifecycle_projection_id` — required when `position_authority_type=LIFECYCLE_PROJECTION`, otherwise `null`
- `lifecycle_revision` — required non-negative integer when `position_authority_type=LIFECYCLE_PROJECTION`, otherwise `null`
- `protection_operation` — `CREATE | REPLACE`
- `order_role` — exactly `PROTECTION_STOP`
- `stop_level` — positive finite canonical price decimal string copied from the exact E5 authority
- `market_snapshot_ref` — exact canonical E1 current-market observation/evidence reference
- `market_symbol` — exact canonical symbol; must match Position/action symbol
- `market_source` — exact E1 source identifier from the accepted observation
- `market_observed_at` — exact `MarketSnapshot.observed_at`
- `market_received_at` — exact `MarketSnapshot.received_at`
- `market_health_status` — exact E1 health status consumed
- `market_freshness_classification` — `FRESH | STALE | UNKNOWN`
- `market_freshness_ms` — copied `MarketSnapshot.freshness_ms` when present, otherwise `null`
- `trigger_reference_semantic` — exactly `LAST_PRICE` in V0.1
- `trigger_reference_price` — positive finite decimal string equal to the bound `MarketSnapshot.last_price`
- `evaluated_at` — RFC 3339 UTC timestamp captured after the bound market observation is accepted
- `validity_status` — `ACTIONABLE | FAIL_CLOSED`
- `reason_codes` — deterministic ordered reason sequence from section 9
- `handoff_category` — category from section 10

No provider credential, account identifier, provider order identifier, provider trigger parameter, raw provider response or provider-native contract quantity belongs in this object.

## 5. Required authoritative inputs

A producer of `ProtectionTriggerValidityEvidence` must consume all of the following as exact immutable inputs.

### 5.1 Current Position authority

At minimum:

```text
position_id
side
broker_state_observed_at
reconciliation_status
symbol
```

The Position must be the exact current E4-normalized broker observation used by E5/E4 for this mutation attempt.

When Gate B/restart-authoritative lifecycle state is relevant, the preferred binding is the exact current `position-lifecycle-projection-v0.1` object, including:

```text
lifecycle_projection_id
lifecycle_revision
lifecycle_source_broker_state_observed_at
```

and its existing execution-evidence freshness obligations remain independent. This profile never lets old trigger evidence make a stale lifecycle projection current.

### 5.2 Exact E5 protection authority

The evidence must bind the exact E5 authority carrying the intended stop, including:

```text
position_action_id
position_id
position_side
stop_level
position_observed_at
```

For current initial protection this is `protection-v0.1` `PositionAction.PROTECT` with `order_role=PROTECTION_STOP` after E4 translation.

If any authority-bearing field changes, prior trigger-validity evidence no longer applies.

### 5.3 Canonical current-market evidence

The market input must be an E1-owned canonical current `MarketSnapshot` for the same symbol. V0.1 requires:

```text
health_status = HEALTHY
last_price = known positive finite Decimal
```

and an E1-attested freshness result.

`market_freshness_classification=FRESH` means the current-market observation was accepted by the E1 source/normalizer under the currently authoritative source-specific freshness/clock policy. `STALE` or `UNKNOWN` is non-actionable.

The profile intentionally defines **no new numeric freshness threshold**. Current E1 OKX ticker normalization already has source-owned freshness/clock checks; future E1 sources may use their own E7-compatible policy. E5/E4 must not manufacture `FRESH` from an arbitrary timestamp or convert E1 stale/unknown data to healthy.

## 6. Trigger reference semantic

V0.1 supports exactly:

```text
trigger_reference_semantic = LAST_PRICE
trigger_reference_price    = MarketSnapshot.last_price
```

This is a **shared pre-mutation geometry reference**, not an OKX provider `triggerPxType` decision.

The profile does not authorize E4 to silently choose `last`, `mark`, `index`, or another provider trigger basis. Provider trigger-price type is an E4 capability/mapping dependency and must be covered by the provider-specific SWAP capability boundary before an actual mutation is permitted.

If the provider mapping cannot prove compatibility with the shared protection intent, E4 must reject execution rather than reinterpret this profile.

`mark_price`, `index_price`, bid/ask, candle close or another semantic may be added only by a later compatible E7 profile revision with explicit meaning. An unknown or unsupported semantic is fail closed.

## 7. Side-correct trigger geometry

Let:

```text
S = stop_level
P = trigger_reference_price
```

Both are positive finite canonical price decimals.

### 7.1 LONG Position

A protective sell stop remains actionable only when:

```text
S < P
```

If:

```text
S >= P
```

the trigger is already reached/crossed at the accepted reference boundary and is **not actionable for blind create/replace**.

### 7.2 SHORT Position

A protective buy stop remains actionable only when:

```text
S > P
```

If:

```text
S <= P
```

the trigger is already reached/crossed at the accepted reference boundary and is **not actionable for blind create/replace**.

### 7.3 Equality boundary

Equality is deliberately fail closed:

```text
LONG:  S == P -> ALREADY_BREACHED
SHORT: S == P -> ALREADY_BREACHED
```

The profile never assumes that an order placed exactly at the current reference can be safely established before the market has moved through it.

### 7.4 Invalid geometry/side

Unknown side, side/action contradiction, non-positive/non-finite stop/reference price, symbol mismatch, or an authority whose declared Position side does not match current Position truth is invalid evidence. These cases are distinct from a validly formed stop whose market relationship is already breached.

## 8. Temporal ordering and freshness

The deterministic evaluation sequence is:

```text
1. obtain/validate exact current Position authority
2. obtain/validate exact E5 protection authority
3. acquire and accept current E1 MarketSnapshot
4. capture evaluated_at after market acceptance
5. evaluate freshness/authority/geometry and emit evidence
6. immediately before mutation, reject if newer relevant evidence is already known
```

`evaluated_at` must not be precomputed before the current-market observation. At minimum:

```text
evaluated_at >= market_received_at
evaluated_at >= position_observed_at
evaluated_at >= PositionAction.created_at
```

The profile follows ADR-0010's general temporal principle: deterministic upstream evidence time and post-observation decision time are separate boundaries; a caller may not reuse an older pre-observation timestamp as if it were a current post-observation decision boundary.

E1 remains authoritative for provider-market timestamp/freshness/clock acceptance. This profile does not add a second numeric clock-skew tolerance.

### 8.1 Invalidation by newer market truth

If a newer accepted E1 `MarketSnapshot` for the same symbol is known before dispatch, any older trigger-validity evidence is stale for that mutation attempt and must be recomputed.

A later `evaluated_at` alone is **not** materially new market evidence.

### 8.2 Invalidation by newer Position/lifecycle truth

If a newer E4 Position observation exists, or a newer authoritative E5 lifecycle projection supersedes the bound projection, the prior trigger-validity evidence is stale and must not authorize mutation.

A newer Position observation requires fresh E5 interpretation/authority as already required by the Position lifecycle profiles; E4 must not merely substitute the new Position into an old action.

### 8.3 Invalidation by changed authority

Any changed `position_action_id`, stop level, Position side, position observation anchor, operation, symbol or supported trigger semantic requires new evidence.

## 9. Validity outcomes and reason vocabulary

`validity_status=ACTIONABLE` is allowed only when all required inputs are exact/current, E1 market evidence is healthy/fresh, temporal ordering is valid, the supported reference semantic is present, and side-correct geometry is strictly actionable.

For ACTIONABLE evidence:

```text
reason_codes = [PROTECTION_TRIGGER_ACTIONABLE]
handoff_category = NONE
```

All other results are `FAIL_CLOSED`.

Stable reason codes and meanings:

- `TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED` — requested/bound trigger-reference semantic is absent, unknown, or not `LAST_PRICE` in V0.1.
- `TRIGGER_REFERENCE_PRICE_UNKNOWN` — the supported canonical reference price is missing, non-finite, non-positive, or otherwise unusable.
- `MARKET_EVIDENCE_UNKNOWN` — E1 market observation/health/freshness cannot be established.
- `MARKET_EVIDENCE_STALE` — E1 classifies the bound observation as stale/non-current.
- `POSITION_AUTHORITY_MISMATCH` — Position ID/symbol/side/reconciliation/authority reference does not match the action/current truth.
- `POSITION_AUTHORITY_STALE` — newer Position/lifecycle authority is already known or the action is anchored to an older Position observation.
- `TEMPORAL_ORDER_INVALID` — evaluation time was not captured after required evidence boundaries.
- `TRIGGER_SIDE_OR_GEOMETRY_INVALID` — side or canonical numeric geometry is malformed/contradictory before market breach evaluation.
- `TRIGGER_ALREADY_BREACHED` — a validly formed LONG stop satisfies `S >= P`, or a validly formed SHORT stop satisfies `S <= P`, including equality.
- `PROTECTION_TRIGGER_ACTIONABLE` — all V0.1 preconditions pass and strict side-correct geometry remains actionable.

When more than one failure exists, reasons are emitted in the fixed order shown above, excluding `PROTECTION_TRIGGER_ACTIONABLE`. Consumers must not use list ordering to choose lifecycle policy; ordering exists only for deterministic evidence identity.

## 10. Fail-closed handoff categories

This profile reports evidence category only. It does not decide E5 lifecycle action.

Allowed values:

- `NONE` — only with `ACTIONABLE`.
- `REFRESH_MARKET_EVIDENCE_REQUIRED` — stale/unknown market evidence or invalid post-observation timing that can be resolved only by acquiring accepted current market evidence.
- `POSITION_RECONCILIATION_REQUIRED` — stale/mismatched Position authority, current Position inconsistency, or newer Position/lifecycle truth invalidating the bound action.
- `E5_PROTECTION_POLICY_REEVALUATION_REQUIRED` — trigger already breached, invalid side/geometry, or unsupported trigger-reference semantics after exact authority inputs are otherwise identified.

E5 remains the sole owner of whether the next lifecycle/risk response is:

```text
HOLD
EXIT
EMERGENCY_EXIT
RECONCILIATION_REQUIRED
another future approved protection action
PAUSE_LIVE / other existing policy outcome where applicable
```

E4 may reject the mutation and surface the evidence; it must not select those E5 outcomes.

If failures span more than one category, the evidence uses the most conservative deterministic precedence:

```text
POSITION_RECONCILIATION_REQUIRED
> REFRESH_MARKET_EVIDENCE_REQUIRED
> E5_PROTECTION_POLICY_REEVALUATION_REQUIRED
```

This precedence is only a routing category, not a lifecycle transition.

## 11. Already-breached and retry rule

`TRIGGER_ALREADY_BREACHED` means:

```text
same stop + same Position authority + accepted current market truth
-> no blind create
-> no blind replace
-> no immediate resubmit loop
```

The unchanged failing evidence is stable. Retrying the same mutation solely because time passed or the previous attempt was rejected is forbidden.

A new validity evaluation may be attempted only after materially new authority/evidence, such as:

1. a newer accepted E1 MarketSnapshot;
2. a newer authoritative E4 Position observation plus the required fresh E5 interpretation/action;
3. a new E5 `position_action_id` carrying materially changed, policy-valid protection authority;
4. a future provider-capability/reconciliation result explicitly required by the applicable execution path.

A new `evaluated_at` with otherwise identical action, Position authority and market snapshot is not materially new evidence and cannot make a breached trigger actionable.

## 12. Evidence identity and immutability

`protection_trigger_validity_id` is deterministic over the complete canonical evidence payload except the ID field itself.

Algorithm:

1. remove `protection_trigger_validity_id`;
2. serialize all remaining fields as canonical UTF-8 JSON with lexicographically sorted keys and compact separators;
3. financial decimals remain base-10 decimal strings and timestamps remain UTC `Z`;
4. compute SHA-256;
5. prefix the lowercase hex digest with:

```text
prottrigval_
```

Therefore:

```text
same exact authority + same exact market evidence + same evaluation/result -> same ID
changed authority/market/geometry/time/result -> different ID
same ID + changed payload -> conflict/corrupt evidence
```

The object is immutable evidence. It is never rewritten to claim a later market or Position observation.

## 13. E4 execution consumption rule

Before a provider protection mutation, E4 must require trigger-validity evidence that exactly matches the mutation's:

```text
position_action_id
position_id
position side/authority anchor
order_role
stop_level
symbol
operation
```

and must require:

```text
validity_status = ACTIONABLE
reason_codes = [PROTECTION_TRIGGER_ACTIONABLE]
handoff_category = NONE
```

If E4 already knows a newer relevant market or Position observation, it must reject the older evidence and require recomputation.

This is additive to, not a replacement for:

- `protection-v0.1` authority validation;
- action expiry;
- canonical quantity checks;
- Position reconciliation checks;
- idempotency/client-order identity;
- provider SWAP action-role capability checks;
- provider precision/quantity requirements;
- provider order-state reconciliation.

E4 may map shared protection intent to provider trigger fields only through an explicit provider capability boundary. This profile never authorizes Spot `tdMode=cash`, never removes SWAP `reduceOnly` semantics, never uses wallet dust as Position flatness, and never imports Spot algo-order `ccy` requirements.

## 14. E5 producer/policy rule

E5 owns protection policy and lifecycle interpretation.

A bounded E5 implementation may consume current Position authority plus E1 current-market evidence to produce or validate this shared trigger-validity evidence before handing protection authority to E4, or an approved cross-module validator may materialize the same deterministic object. Regardless of implementation location:

- E5 cannot treat stale/unknown market evidence as actionable;
- E5 cannot treat a breached trigger as successful protection;
- E5 alone chooses the policy response to a fail-closed handoff;
- a materially changed stop/policy requires a new E5 authority identity under the applicable protection profile;
- the existing rule against widening loss risk remains unchanged.

## 15. E1 dependency

E1 owns only canonical market facts and freshness/health.

For this profile E1 must provide, directly through `MarketSnapshot` or an authoritative equivalent current-market interface:

```text
symbol
observed_at
received_at
health_status
source
last_price
freshness_ms when available
```

E1 does not know Position side, does not judge protection geometry, and does not decide E5 policy.

The current OKX current-market normalizer already rejects stale/future-out-of-policy ticker observations and emits `HEALTHY` snapshots with canonical `last_price`; no E1 executable change is required merely to define this profile.

## 16. E6 persistence/display rule

A future E6 bounded follow-up may persist/display this evidence and its reason/handoff category.

E6 may:

- validate schema/profile/identity/hash;
- display exact provenance and timestamps;
- show ACTIONABLE vs FAIL_CLOSED and reason codes;
- identify that newer persisted market/Position evidence makes an older validity object non-current when the authoritative ordering facts are explicit.

E6 must not:

- recompute E5 lifecycle policy;
- decide a breached trigger means EXIT or EMERGENCY_EXIT;
- turn stale/unknown evidence into ACTIONABLE;
- rewrite an old evidence object to point at newer truth.

## 17. Deterministic test scenarios required downstream

Separate E5/E4 tasks must add deterministic local test definitions at minimum for:

1. `LONG_VALID` — LONG Position, fresh current market `P`, stop `S < P` -> ACTIONABLE.
2. `SHORT_VALID` — SHORT Position, fresh current market `P`, stop `S > P` -> ACTIONABLE.
3. `LONG_EQUALITY_BREACHED` — `S == P` -> FAIL_CLOSED / `TRIGGER_ALREADY_BREACHED`.
4. `SHORT_EQUALITY_BREACHED` — `S == P` -> FAIL_CLOSED / `TRIGGER_ALREADY_BREACHED`.
5. `LONG_CROSSED` — `S > P` -> FAIL_CLOSED / `TRIGGER_ALREADY_BREACHED`.
6. `SHORT_CROSSED` — `S < P` -> FAIL_CLOSED / `TRIGGER_ALREADY_BREACHED`.
7. `STALE_MARKET` — E1 stale/non-current classification -> FAIL_CLOSED / refresh required.
8. `UNKNOWN_MARKET` — missing/unhealthy/unknown current observation -> FAIL_CLOSED.
9. `STALE_POSITION_AUTHORITY` — newer Position observation or lifecycle projection exists -> old evidence rejected.
10. `POSITION_SIDE_MISMATCH` — action side/current Position side mismatch -> FAIL_CLOSED.
11. `UNSUPPORTED_TRIGGER_REFERENCE` — non-`LAST_PRICE` semantic under V0.1 -> FAIL_CLOSED.
12. `TEMPORAL_PRECOMPUTE_REJECTED` — evaluation time preceding market receipt/action/Position authority boundary -> FAIL_CLOSED.
13. `UNCHANGED_BREACH_RETRY_REJECTED` — same action + same Position authority + same market snapshot remains non-actionable; later clock time alone does not enable retry.
14. `NEW_MARKET_REEVALUATES` — newer accepted market snapshot invalidates prior evidence and yields a new deterministic evaluation.
15. `NEW_POSITION_INVALIDATES` — newer Position/lifecycle authority invalidates prior evidence and requires fresh E5 authority/interpretation.
16. `E4_EXACT_BINDING` — E4 rejects ACTIONABLE evidence whose action ID, Position anchor, stop, symbol, role or operation differs from the actual mutation.
17. `PROVIDER_BASIS_NOT_INFERRED` — shared LAST_PRICE geometry evidence does not silently create a provider trigger-price type; absent compatible E4 capability mapping blocks execution.

Tests are definitions only until executed in a Product-Owner-approved local environment.

## 18. Ownership

```text
E1 = canonical current-market observation, health and freshness facts
E5 = protection/risk policy, lifecycle response and authority changes
E4 = provider capability/parameter translation, exact evidence consumption and mutation rejection
E6 = optional persistence/display/audit only; no reinterpretation
E7 = shared profile/version/compatibility and cross-module integration acceptance
```

## 19. Verification and release consequence

E7-099 is a contract/docs task only.

```text
executable verification = NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK
project code/tests       = NOT_RUN
provider/private API     = NOT USED / NOT REQUIRED
credentials              = NOT READ / NOT REQUESTED / NOT REQUIRED
Product Owner authority  = NOT REQUIRED FOR THIS CONTRACT TASK
capital exposure         = NONE
```

This profile by itself does not make FP-03 implemented. FP-03 remains pending E5/E4 executable implementation and accepted local verification.

Any later E5/E4 executable change implementing this profile requires fresh approved-local credential-free requalification before its executable evidence can be accepted for the relevant release boundary.

No provider/private validation, SHADOW/PAPER runtime, provider mutation, order action, Gate D, LIVE or capital exposure is authorized by this profile.
