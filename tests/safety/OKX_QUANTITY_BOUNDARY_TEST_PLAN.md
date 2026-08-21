# Local Safety Test Plan — OKX Quantity / Instrument Boundary

> Owner: E7 safety/integration  
> Provider target: OKX `BTC-USDT-SWAP`  
> Shared quantity profile: `base-asset-v0.1`  
> Execution policy: local / Product-Owner-approved non-GitHub environment only  
> Current result: `NOT_RUN`

## Purpose

Define fail-closed safety tests for translating an E5-approved canonical base-asset quantity into provider contract units without increasing exposure.

No private/Demo provider call is authorized by this file. Initial tests should use deterministic local fixtures/adapters until a later TASK explicitly authorizes approved provider integration.

## Canonical invariant

For every provider translation:

```text
0 < effective_canonical_quantity <= e5_approved_canonical_quantity
```

Provider quantization may round down or reject. It must never round up above the E5 bound.

## Deterministic instrument fixture fields

Safety fixtures must include explicit values for:

- provider;
- `instId`;
- `instType`;
- `ctVal`;
- `ctMult`;
- `ctValCcy`;
- `ctType`;
- `lotSz`;
- `minSz`;
- `tickSz`;
- `state`;
- metadata observation time;
- metadata policy version.

Do not use undocumented defaults for missing provider values.

## Test cases

### SAFE-OKX-QTY-001 — exact representable quantity

Given valid supported metadata and an approved canonical BTC quantity exactly representable in contracts:

Assert:

- provider contract quantity is the exact valid `lotSz` multiple;
- effective canonical quantity equals the approved quantity;
- shared OrderRequest quantity remains the original canonical base quantity;
- provider `sz` is kept separately as provider translation data.

### SAFE-OKX-QTY-002 — non-representable quantity rounds down only

Given an approved canonical quantity that converts to a non-`lotSz` contract count:

Assert:

- provider contracts are floored to the largest valid lot multiple;
- effective canonical exposure is less than or equal to approved exposure;
- residual quantity is reported/auditable;
- no compensating order is automatically created.

### SAFE-OKX-QTY-003 — round-up attempt is rejected

Inject a translator/rounding implementation that returns a provider size whose effective canonical quantity exceeds the E5 bound.

Assert fail closed before submit.

### SAFE-OKX-QTY-004 — below minimum rejects

If floor-to-lot result is below `minSz`:

Assert:

- no round-up to `minSz`;
- no order submit;
- explicit below-minimum/representability rejection.

### SAFE-OKX-QTY-005 — missing sizing metadata blocks

Remove each required sizing field one at a time:

- `ctVal`;
- `ctMult`;
- `ctValCcy`;
- `ctType`;
- `lotSz`;
- `minSz`.

Assert new exposure blocks.

### SAFE-OKX-QTY-006 — malformed/non-positive metadata blocks

Test zero, negative, non-finite, malformed-string, or incompatible values for sizing metadata.

Assert fail closed.

### SAFE-OKX-QTY-007 — stale metadata blocks

Use an instrument snapshot older than the active adapter metadata policy allows.

Assert:

- no provider request is created;
- stale state is explicit;
- caller cannot override stale metadata with a permissive boolean/string combination.

### SAFE-OKX-QTY-008 — provider identity mismatch blocks

Provide metadata for an instrument other than the configured mapping for `BTC_USDT_PERP`.

Assert fail closed.

### SAFE-OKX-QTY-009 — unsupported contract conversion blocks

Provide metadata whose contract type/value currency requires a conversion not approved by the V1 adapter profile.

Assert E4 rejects rather than inventing a price-dependent conversion.

### SAFE-OKX-QTY-010 — non-tradable state blocks MARKET

Test provider states including suspended/rebase/non-tradable/post-only-only state.

For `entry-v0.1/MARKET`, assert no new exposure request.

### SAFE-OKX-QTY-011 — tick size does not manufacture MARKET price

Provide valid `tickSz` and advisory reference price.

Assert:

- MARKET translation does not create/quantize an executable price;
- `reference_price` remains advisory.

### SAFE-OKX-QTY-012 — provider requested and filled contracts remain distinct

Simulate provider request `sz=N` followed by partial fills.

Assert:

- requested contracts and cumulative/individual fill contracts remain distinct;
- shared canonical `filled_quantity` is derived from actual fill facts, not copied from requested quantity;
- provider contract fill facts remain auditable.

### SAFE-OKX-QTY-013 — canonical fill never exceeds approved bound

Across one or multiple provider fills for the same approved entry:

Assert cumulative canonical filled base quantity never exceeds the E5 approved plan quantity.

Overfill or inconsistent provider truth enters reconciliation/error handling and blocks additional exposure.

### SAFE-OKX-QTY-014 — metadata reference is auditable

Assert every provider translation records the exact instrument metadata snapshot/reference and observation time used for sizing.

### SAFE-OKX-QTY-015 — account-mode/config unknown blocks

Simulate unknown/incompatible provider account mode or inability to verify required isolated operation.

Assert no new exposure.

### SAFE-OKX-QTY-016 — dedicated sub-account is not risk approval

Simulate a valid dedicated R7 sub-account identity with otherwise missing risk approval.

Assert execution remains blocked. Account isolation cannot substitute for ApprovedTradePlan/E5 authority.

### SAFE-OKX-QTY-017 — Withdraw/funding-transfer capability absent

Inspect the future OKX/R7 broker interface surface.

Assert no method/command exists for:

- withdrawal;
- funding transfer;
- sub-account capital movement.

### SAFE-OKX-QTY-018 — Demo success does not grant LIVE

Given successful local Demo-adapter simulation or later approved Demo result:

Assert no automatic:

- lifecycle approval;
- LIVE mode;
- Product Owner approval;
- Gate C/D PASS.

## Future local command

Exact executable command will be recorded after E4 implements the adapter safety suite under a new TASK.

Minimum expected form:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/safety -p "test_*okx*quantity*.py" -v
```

Current disposition:

```text
NOT_RUN
```

No GitHub Actions, hosted runner, GitHub-triggered runner, or provider/private test call may be used as a substitute.
