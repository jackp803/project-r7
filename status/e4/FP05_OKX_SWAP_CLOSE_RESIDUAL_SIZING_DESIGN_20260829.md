# E4 FP-05 OKX SWAP Close / Residual Sizing Design — 2026-08-29

## Handoff

**From:** E4 / Trading Execution / Broker Integration Engineer  
**To:** E7 / Project Manager / future bounded E4 implementation task  
**Branch:** `agent/e4-fp05-close-residual-sizing-design-20260829`  
**Task:** `E4-20260829-028`  
**Design profile:** `okx-swap-close-residual-sizing-v0.1`  
**Baseline main:** `466b167e32fc84e1906e0e80bae7c55e31a517fc`  
**Date:** `2026-08-29`

## 1. Objective

Define only the FP-05 provider-native close/reducible/residual sizing design for the current OKX V5 `BTC-USDT-SWAP` target.

The design prevents future `POSITION_EXIT` / `EMERGENCY_EXIT` translation from:

- using original requested ENTRY quantity as close authority;
- over-reducing exposure;
- reusing ENTRY sizing compatibility as close capability proof;
- silently rounding positive residual exposure to zero;
- looping on an unchanged non-representable residual;
- retrying after an ambiguous provider outcome without reconciliation;
- treating ACK/terminal order status as authoritative flat Position truth.

No executable source/test/provider/runtime work is part of this task.

## 2. What changed

Created the E4-owned design artifact:

`docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`

It defines:

1. exact quantity-authority hierarchy;
2. current canonical Position vs provider-native reducible exposure distinction;
3. provider-local close sizing evidence envelope;
4. close metadata/currentness binding;
5. explicit separation of repository-evidenced ENTRY metadata vocabulary from unresolved close-role applicability;
6. safe bounded quantization model that can never exceed current canonical/provider exposure;
7. stable residual-state vocabulary;
8. unchanged-evidence no-retry rule;
9. authoritative-flat-only rule;
10. FP-02 / FP-04 / FP-11 / FP-10 dependency boundaries;
11. deterministic future implementation/test handoff.

## 3. Files changed

- `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`
- `status/e4/FP05_OKX_SWAP_CLOSE_RESIDUAL_SIZING_DESIGN_20260829.md`
- `coordination/E4/STATUS.md` (terminal status update)

No executable source/tests or contracts are changed.

## 4. Contracts / accepted profiles consumed

- `contracts-v0.1` / `SHARED_CONTRACTS_V1.md`
- `close-v0.1` / `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `position-lifecycle-execution-binding-v0.1`
- `bounded-live-fire-readiness-v0.1`
- `external-provider-object-ownership-reconciliation-v0.1` (FP-04)
- `protection-registry-multiplicity-v0.1` (FP-11)
- E4 `okx-swap-action-role-capability-v0.1` (FP-02)

No shared profile is modified.

## 5. Contracts produced or changed

`NONE`.

No new shared cross-module field/profile is proven necessary by FP-05 design.

The proposed sizing evidence is deliberately E4/provider-local. Existing shared authority is sufficient:

```text
E5 close PositionAction
+ exact current Position
+ E4 provider exposure truth
+ FP-04 ownership/reconciliation
+ FP-02 capability
+ E4 provider metadata/sizing evidence
-> provider-local sizing evaluation
```

If future E6/E7 requirements need the exact provider-local sizing object serialized as a shared cross-module artifact, E4 must request a separate E7 companion profile then; this task does not invent one.

## 6. Provider/instrument baseline used

```text
provider = OKX
api_version = V5
canonical_symbol = BTC_USDT_PERP
provider_instrument = BTC-USDT-SWAP
instrument_type = SWAP
canonical_quantity = base-asset-v0.1 / BASE_ASSET / BTC
margin baseline = isolated
account baseline candidate = acctLv=2
position modes = net_mode | long_short_mode only where exact FP-02 role row proves support
```

Current accepted FP-02 rows for `POSITION_EXIT` and `EMERGENCY_EXIT` remain provider-mutation `UNRESOLVED_FAIL_CLOSED` for both position modes. FP-05 does not make them executable.

## 7. Quantity authority hierarchy

The design uses this precedence:

```text
1. E5 close-v0.1 PositionAction canonical quantity authority
2. exact current normalized Position.actual_quantity / broker_state_observed_at
3. exact current provider-native reducible exposure observation
4. current FP-04 ownership/reconciliation evidence
5. accepted exact FP-02 close-role capability row
6. current close-applicable provider instrument metadata generation
7. accepted close lot/step/min/max rules
8. quantized provider-native requested close size
9. fresh post-action provider Position observation
10. residual representability classification
```

Lower layers cannot override contradictions in higher layers.

Original requested ENTRY quantity, plan quantity, stale local quantity, prior request quantity, or arithmetic remainder never override a newer current Position/provider observation.

## 8. Residual-state vocabulary

Stable E4 provider-local states:

- `FULLY_REDUCIBLE`
- `PARTIALLY_REDUCIBLE`
- `RESIDUAL_NONZERO_REPRESENTABLE`
- `RESIDUAL_NONZERO_UNREPRESENTABLE`
- `EXPOSURE_ALREADY_FLAT`
- `REDUCIBLE_EXPOSURE_UNKNOWN`
- `METADATA_STALE_OR_UNKNOWN`
- `RECONCILIATION_REQUIRED`
- `CLOSE_CAPABILITY_UNPROVEN`

Only a fresh authoritative provider/normalized Position observation may establish `EXPOSURE_ALREADY_FLAT`.

Order ACK, terminal status, requested quantity arithmetic, local expected fill arithmetic, or local lifecycle expectation cannot establish flatness.

## 9. Residual evaluation / retry rules

Positive fresh residual behavior:

```text
fresh positive residual
+ current capability/metadata makes a positive valid size representable
-> RESIDUAL_NONZERO_REPRESENTABLE
-> fresh E5 PositionAction still required before any later mutation
```

```text
fresh positive residual
+ no positive valid close size exists under accepted current close constraints
-> RESIDUAL_NONZERO_UNREPRESENTABLE
-> stable fail-closed state
-> no immediate/tight retry
```

Re-evaluation requires materially new evidence such as:

- newer provider Position generation;
- newer normalized Position observation;
- newer provider metadata generation;
- newly accepted role capability evidence;
- resolved FP-04 ownership/reconciliation evidence;
- fresh E5 close authority.

Unchanged residual + unchanged metadata/capability/ownership evidence must not generate a new provider mutation loop.

Ambiguous prior provider outcome always enters `RECONCILIATION_REQUIRED`; the same logical close must be queried/reconciled before any new request.

## 10. Metadata/currentness requirements

Current repository evidence provides ENTRY sizing vocabulary including:

- `ctVal`
- `ctMult`
- `ctValCcy`
- `ctType`
- `lotSz`
- `minSz`
- `maxMktSz`
- `tickSz`
- `state`
- metadata reference/observed-at/freshness policy
- scheduled `upcChg`

These names and ENTRY behavior are repository-evidenced. Their **close/reduction applicability is not automatically proven**.

Before controlling close sizing, each required provider fact/limit must be classified by an accepted E4 capability/metadata boundary as:

- `REQUIRED_FOR_CLOSE`
- `APPLICABLE_CONSTRAINT`
- `NOT_APPLICABLE_TO_CLOSE`
- `UNRESOLVED_FAIL_CLOSED`

Unknown/default omission is forbidden.

## 11. Exact unresolved provider-specific facts

The following remain unresolved and therefore fail closed for provider mutation:

1. exact provider Position quantity/sign semantics for close sizing per `net_mode` and `long_short_mode`;
2. exact OKX provider close field set for `POSITION_EXIT`;
3. exact OKX provider close field set for `EMERGENCY_EXIT`;
4. provider-native reduce-only field presence/value/omission semantics;
5. role-specific `posSide` behavior for close roles;
6. whether ENTRY `lotSz` is the complete close step rule;
7. whether ENTRY `minSz` applies identically to reductions;
8. whether ENTRY `maxMktSz` applies identically to reductions;
9. whether distinct close/reduce maximum constraints exist;
10. whether OKX has an applicable below-minimum full-residual close exception for this exact row;
11. any special provider full-close/dust mechanism;
12. any special close endpoint/flag not already proven by an accepted capability row.

The design does not guess any of these.

## 12. FP-02 dependency

FP-05 consumes `okx-swap-action-role-capability-v0.1` without changing it.

For `POSITION_EXIT` and `EMERGENCY_EXIT`:

- exact action role remains mandatory;
- account/mode/margin facts must resolve to an accepted capability row;
- Spot/cash semantics remain forbidden;
- generic shared `reduce_only=true` is not provider compatibility proof;
- caller booleans/mappings cannot manufacture capability PASS;
- EMERGENCY_EXIT urgency creates no bypass.

## 13. FP-04 dependency

Provider exposure whose ownership/currentness is ambiguous, conflicting, stale, external/untracked, prior-generation without accepted reconciliation, or blocked by FP-04 disposition cannot be used as trusted reducible-size authority.

FP-05 does not silently adopt external/manual exposure.

## 14. FP-11 dependency

Flat or reduced Position truth does not erase/cancel provider protection objects.

Any remaining/missing/multiple/orphan/unknown provider protection converges through FP-11 evidence/policy. FP-05 does not choose or cancel protection objects.

## 15. Downstream FP-10 dependency

FP-10 remains downstream of FP-04 + FP-05 and should consume FP-11 convergence where protection cleanup matters.

Future FP-10 lifecycle convergence may consume:

- authoritative current reduced/flat Position truth;
- aggregate Fill/execution evidence;
- FP-04 ownership/reconciliation;
- FP-11 registry/protection convergence;
- E5 lifecycle interpretation.

FP-05 itself never emits `RECONCILED_FLAT`, `CLOSED`, `POSITION_CLOSED`, or TradeResult.

## 16. Future deterministic implementation paths

Smallest later E4 executable boundary:

- provider-local `okx_close_sizing` component (name may vary);
- immutable `OKXCloseResidualSizingEvidence` or equivalent;
- exact current `close-v0.1` authority/Position binding;
- exact provider Position/reducible exposure input;
- exact FP-04 evidence input;
- adapter-issued/accepted FP-02 role capability row;
- exact close-applicable metadata generation;
- deterministic no-over-reduction quantization;
- explicit residual state;
- no network I/O inside sizing;
- provider dispatch remains separately gated/default-deny.

After executable implementation, fresh approved-local qualification is required on the exact integrated candidate.

## 17. Future credential-free test plan

At minimum test:

- current actual exposure smaller than original ENTRY requested quantity -> actual current exposure controls;
- provider exposure larger/different due partial/manual/external truth -> unresolved FP-04 ownership/reconciliation blocks unsafe sizing;
- provider-native request never exceeds exact reducible exposure;
- provider-effective canonical size never exceeds current E5/Position authority;
- exact close step/lot quantization boundary;
- full representability;
- partial representability;
- positive representable residual remains explicit;
- positive non-representable residual remains explicit/stable;
- unchanged non-representable residual does not retry;
- materially newer Position/metadata permits a new evaluation but not mutation without fresh E5 authority;
- zero/negative native size rejected;
- stale/unknown metadata rejected;
- close-limit applicability unknown rejected;
- unknown account/position/margin capability rejected;
- ENTRY sizing evidence cannot be reused as close capability authority;
- ambiguous prior close requires reconciliation;
- ACK/terminal order status does not establish flatness;
- only authoritative flat Position truth yields `EXPOSURE_ALREADY_FLAT`;
- EMERGENCY_EXIT obeys identical quantity/currentness/capability proofs;
- Spot/cash semantics rejected;
- caller capability assertions rejected;
- deterministic fixtures require no provider network/credentials.

Suggested later approved-local commands after implementation:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.brokers.test_okx_close_sizing -v
python -m unittest tests.execution.test_close -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

## 18. Local verification

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR DOCS-ONLY DESIGN TASK
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER = NOT_STARTED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.

## 19. Known limitations

- The accepted FP-02 close mutation rows are still unresolved/non-executable.
- Close-specific OKX field/mode/limit semantics listed in section 11 remain unverified.
- This task adds no executable sizing implementation or test definitions.
- No current provider/private verification is claimed.
- LF-0 remains blocked; current P0 executable qualification state is unchanged.

These limitations are intentionally fail closed and do not prevent the provider-local FP-05 design from being deterministic.

## 20. Dependencies / blockers

No blocker prevents design completion.

Future executable close support depends on:

1. accepted role-specific FP-02 provider capability row;
2. proven close-applicable metadata semantics;
3. FP-04 current ownership/reconciliation evidence;
4. fresh E5 `close-v0.1` authority;
5. later approved-local credential-free qualification;
6. separately authorized provider/private verification where provider facts require it.

## 21. Required next action

This handoff does not self-start another task.

A future separately assigned E4 executable FP-05 task may implement the provider-local sizing evaluator and deterministic tests after governance decides the required provider capability facts are sufficiently specified.

FP-10 remains downstream and should not infer lifecycle closure from this design alone.

## 22. Security / secrets

- no real API key/secret/passphrase/token/password/private key was read, requested or committed;
- no `.env` value was added;
- no provider response containing private credential material was persisted;
- no credentials are required for this design.

## 23. GitHub compute policy

- no GitHub Actions workflow was created or used;
- no GitHub-hosted/GitHub-triggered runner was used;
- no project code/test/provider simulation was executed on GitHub infrastructure;
- GitHub was used only for repository read/write/versioned evidence.

## 24. Live-trading impact

None.

```text
SHADOW/PAPER runtime = NOT_STARTED
provider mutation = 0
capital exposure = NONE
10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

`DONE` for E4-20260829-028 means docs-only design completion only.