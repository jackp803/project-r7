# FP-03 Protection Trigger Contract Handoff — E7-20260829-099

## Scope

- task_id: `E7-20260829-099`
- objective: shared contract-first safety boundary for FP-03 only
- new profile: `protection-trigger-validity-v0.1`
- canonical artifact: `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`
- parent schema: `contracts-v0.1`
- existing protection profile: `protection-v0.1 / unchanged`
- existing lifecycle profiles: referenced / unchanged
- ADR created: `NO / not necessary`

This handoff defines only the shared evidence semantics needed to prevent protection create/replace attempts whose intended stop is already reached/crossed against accepted current market truth. It does not implement E5/E4 runtime behavior.

## Compatibility decision

```text
change_class = ADDITIVE_COMPANION_PROFILE
schema_version = contracts-v0.1 / unchanged
protection-v0.1 = unchanged
position-lifecycle-projection-v0.1 = unchanged
position-lifecycle-execution-binding-v0.1 = unchanged
```

No existing PositionAction, OrderRequest, Fill, Position or lifecycle identity is rewritten.

`protection-trigger-validity-v0.1` is separate immutable evidence. Legacy protection objects remain valid for their existing meaning but do not prove current trigger actionability.

## Normative V0.1 trigger rule

Shared pre-mutation reference semantic:

```text
trigger_reference_semantic = LAST_PRICE
trigger_reference_price = exact E1 MarketSnapshot.last_price
```

This is not an OKX provider `triggerPxType` selection.

Geometry:

```text
LONG  actionable only when stop_level < LAST_PRICE
SHORT actionable only when stop_level > LAST_PRICE

LONG  stop_level >= LAST_PRICE -> TRIGGER_ALREADY_BREACHED
SHORT stop_level <= LAST_PRICE -> TRIGGER_ALREADY_BREACHED
```

Equality is fail closed for both sides.

No Spot `tdMode=cash`, Spot-specific `reduceOnly` prohibition, wallet-dust flatness, or Spot algo-order `ccy` rule is imported.

## Required evidence boundary

The deterministic evidence binds:

- exact E5 `position_action_id` and intended `PROTECTION_STOP` operation;
- exact current Position identity/authority anchor and side;
- exact stop level;
- exact E1 current `MarketSnapshot` reference, source, observed/received timestamps and health/freshness facts;
- canonical `LAST_PRICE` reference value;
- post-observation `evaluated_at`;
- `ACTIONABLE | FAIL_CLOSED` result;
- stable reason codes and fail-closed handoff category.

A newer accepted market observation, newer Position/lifecycle authority, or changed E5 action invalidates older validity evidence before mutation.

## Already-breached / retry rule

Unchanged breached truth is a stable non-actionable state:

```text
same action
+ same Position authority
+ same market snapshot
+ same stop
-> no blind create/replace
-> no immediate resubmit loop
```

A later clock time by itself is not materially new evidence.

Re-evaluation requires materially new evidence/authority, such as a newer accepted E1 market observation, newer Position truth plus fresh E5 interpretation/action, or a new E5 PositionAction carrying changed valid protection authority.

## Fail-closed vocabulary

Primary stable reason vocabulary introduced by the profile:

- `PROTECTION_TRIGGER_ACTIONABLE`
- `TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED`
- `TRIGGER_REFERENCE_PRICE_UNKNOWN`
- `MARKET_EVIDENCE_UNKNOWN`
- `MARKET_EVIDENCE_STALE`
- `POSITION_AUTHORITY_MISMATCH`
- `POSITION_AUTHORITY_STALE`
- `TEMPORAL_ORDER_INVALID`
- `TRIGGER_SIDE_OR_GEOMETRY_INVALID`
- `TRIGGER_ALREADY_BREACHED`

Routing-only handoff categories:

- `NONE`
- `REFRESH_MARKET_EVIDENCE_REQUIRED`
- `POSITION_RECONCILIATION_REQUIRED`
- `E5_PROTECTION_POLICY_REEVALUATION_REQUIRED`

These categories are not lifecycle transitions.

## E5 implementation obligations

A separate bounded E5 task should implement the producer/policy side without provider calls.

Required obligations:

1. consume exact current Position authority and exact E1 current-market evidence;
2. never mark stale/unknown market evidence actionable;
3. bind the exact E5 protection action and stop level into `ProtectionTriggerValidityEvidence`;
4. enforce strict LONG/SHORT geometry and equality breach semantics;
5. treat breached/invalid trigger evidence as a fail-closed policy input, not successful protection;
6. choose the next E5 lifecycle/risk action only inside E5 authority;
7. require a new E5 action identity when protection policy/stop authority materially changes;
8. preserve the existing no-stop-widening rule;
9. never choose provider-native trigger parameters.

E5 must not infer that FAIL_CLOSED means one specific lifecycle action. Depending on authoritative policy/current truth E5 may later select HOLD, EXIT, EMERGENCY_EXIT, RECONCILIATION_REQUIRED, PAUSE_LIVE, or another separately approved action.

## E4 implementation obligations

A separate bounded E4 task should implement the consumer/execution side.

Required obligations:

1. require exact matching `protection-trigger-validity-v0.1` evidence immediately before a protection mutation;
2. reject missing/unsupported/FAIL_CLOSED evidence;
3. reject evidence if action ID, Position authority anchor, side, stop, symbol, role or operation differs from the actual mutation;
4. reject older evidence when newer relevant market or Position truth is already known;
5. never blindly submit/re-submit a breached trigger;
6. preserve existing `protection-v0.1` authority, quantity, reconciliation, idempotency and action-expiry checks;
7. keep provider trigger-price type and provider-native parameters inside an explicit OKX SWAP capability mapping;
8. fail closed if provider trigger-basis semantics cannot be proven compatible with the shared protection intent;
9. do not use this evidence as lifecycle/risk authority.

The current E4 action-role capability-matrix gap identified as FP-02 remains separate and must not be silently bundled into this contract task.

## E1 evidence dependency

E1 remains authoritative for current market facts, health and freshness.

Required current evidence fields are already available through the existing `MarketSnapshot` semantics / current OKX normalizer:

```text
symbol
observed_at
received_at
health_status
source
last_price
freshness_ms when available
```

Current E1 OKX ticker normalization rejects stale/future-out-of-policy observations and emits canonical healthy snapshots. No E1 executable change is required by E7-099 itself.

The new profile defines no new numeric freshness threshold. E5/E4 must consume E1-attested freshness rather than inventing a separate threshold in this contract.

## E6 follow-up

E6 persistence/display is optional for initial implementation but recommended as a separate bounded follow-up if operational visibility requires durable trigger-validity evidence.

E6 may persist/display:

- evidence identity/profile;
- Position/action/market provenance refs;
- evaluated timestamp;
- ACTIONABLE vs FAIL_CLOSED;
- reason codes;
- handoff category;
- whether newer explicit market/Position evidence makes the stored evidence non-current.

E6 must not recompute E5 policy, decide EXIT vs EMERGENCY_EXIT, or convert stale/unknown evidence to actionable.

## Deterministic downstream test scenarios

Separate E5/E4 implementation tasks must add tests for at least:

1. `LONG_VALID`: fresh market, LONG, `stop < last` -> ACTIONABLE.
2. `SHORT_VALID`: fresh market, SHORT, `stop > last` -> ACTIONABLE.
3. `LONG_EQUALITY_BREACHED`: `stop == last` -> `TRIGGER_ALREADY_BREACHED`.
4. `SHORT_EQUALITY_BREACHED`: `stop == last` -> `TRIGGER_ALREADY_BREACHED`.
5. `LONG_CROSSED`: `stop > last` -> breached/fail closed.
6. `SHORT_CROSSED`: `stop < last` -> breached/fail closed.
7. `STALE_MARKET`: E1 stale/non-current evidence -> fail closed / refresh required.
8. `UNKNOWN_MARKET`: missing/unhealthy/unknown observation -> fail closed.
9. `STALE_POSITION_EVIDENCE`: newer Position observation/lifecycle projection invalidates old evidence.
10. `MISMATCHED_SIDE`: action side/current Position side mismatch -> fail closed.
11. `UNSUPPORTED_TRIGGER_REFERENCE`: anything other than V0.1 `LAST_PRICE` -> fail closed.
12. `TEMPORAL_PRECOMPUTE`: evaluated time preceding required post-observation boundary -> fail closed.
13. `UNCHANGED_EVIDENCE_RETRY`: unchanged breached evidence cannot become retryable merely because time advanced.
14. `NEW_MARKET_REEVALUATION`: newer accepted E1 snapshot invalidates old evidence and permits deterministic reevaluation.
15. `NEW_POSITION_REQUIRES_NEW_AUTHORITY`: newer Position truth invalidates old action/evidence and requires fresh E5 interpretation/action.
16. `E4_BINDING_MISMATCH`: ACTIONABLE evidence for a different action/Position/stop/role/operation is rejected.
17. `PROVIDER_TRIGGER_BASIS_NOT_INFERRED`: shared LAST_PRICE evidence alone does not authorize a provider trigger-price type.

## Verification / authority boundary

```text
E7-099 executable verification = NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK
project code/tests              = NOT_RUN
Local Job Request               = NOT CREATED
provider/private API            = NOT CALLED / NOT REQUIRED
credentials                     = NOT READ / NOT REQUESTED / NOT USED
provider/account mutation       = NONE
order submit/cancel/amend/close = NONE
SHADOW runtime                  = NOT STARTED
PAPER runtime                   = NOT STARTED
capital exposure                = NONE
GitHub Actions/CI/hosted compute = NOT USED
```

This is not executable PASS evidence.

## Requalification consequence

After future E5/E4 executable implementation of this profile:

```text
fresh approved-local credential-free requalification = YES
```

Provider/private access is not required to implement or deterministically test the profile. Credentials are not required. Product Owner trading/runtime authority is not required for those offline implementation/test tasks.

Any later provider/private verification or actual protection mutation remains separately governed and may require explicit Product Owner authority and approved secure credentials. Capital exposure is not required for prevention implementation/testing.

## Completion boundary

E7-099 stops after the shared profile and this handoff. No E5/E4 implementation, E6 persistence work, provider validation, Local Job, SHADOW/PAPER runtime, Gate D, LIVE, mutation, order action or capital movement is started.
