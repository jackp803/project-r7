# Product native protection observation v0.2

This additive application composition consumes the unchanged E4 FP-04/FP-11
producers, E5 protection-result/registry interpreters and lifecycle/FP-12
builders. It introduces no provider mutation role, adoption, cancellation,
replacement, stop resizing or financial approval authority. Legacy profiles and
their fail-closed cases remain applicable.

## Native bounded inventory

The selected exact account and BTC-USDT-SWAP instrument are read through actual
current E6/E7 admission and issuer-local E4 read-only mechanical proofs. Each
request receives a new transient permit. The documented single-type pending
algo scopes are conditional, oco, chase, trigger, move_order_stop, iceberg, twap
and smart_iceberg. Their GET scope is additive; executable POST bodies remain
the previously accepted initial conditional-stop and market-order profiles.

Pages contain at most 100 objects. Full pages require an older-ID cursor and a
further request; duplicate, overlapping, forward, unordered or malformed rows
are rejected. Two complete scans must preserve identical original normalized
facts and independent full-row hashes. The bound is 128 total requests, 4,096
objects per scan and five seconds from the first request, with no automatic
retry. Errors, unsupported provider type responses, limit exhaustion or changed
scans never become empty or complete observations.

`CONVERGED_BOUNDED_READ_SCAN` means exhausted coverage of these pinned endpoint
scopes with the two observed scans equal. It is **not an atomic provider
snapshot** or a guarantee against a subsequent provider change. Its FP-11
COMPLETE mapping means this bounded scope was fully read; issuer currentness and
the original read interval remain mandatory. Original cTime/uTime are preserved
separately from request/receipt clocks. Missing optional uTime is explicit.
Unknown raw fields are not retained; their independent full-row hash detects
material drift. Documented mechanical fields are retained in native audit only.

Every object in these algo scopes is conservatively included as a possible
protection dependency. External/unsupported shapes are visible and block
convergence; they are never silently dropped or adopted. This profile does not
cover arbitrary provider products, instruments or additional future algo types.
A newly introduced type requires an updated, verified coverage profile.

## Actual protection interpretation

The original claimed PROTECTION_STOP intent, actual canonical request/action/
plan, historical source projection, current E5/FP-12 subject and fresh issuer-
bound native position/inventory must agree. The native position observation
must already have been projected through E5 and E6. Its quantity, price and
broker observation anchor must match the exact current canonical position.

An owned active stop requires strict native field comparison, original mapped
client identity, original provider algo identity and a fresh exact order query
published by the actual trading service. An ACK or inventory row alone cannot
promote protection. A matching committed identity without sufficient exact
readback remains ownership UNKNOWN. A verified account-wide E6 claim inventory
is compared before labeling another object EXTERNAL_UNTRACKED. Other locally
claimed identities and blank/unresolvable client identities remain UNKNOWN;
this original-position profile cannot adopt another deployment's object.
The additive `PRODUCT_CLAIM_INVENTORY_PROFILE_V0_2.md` replaces the historical
1000-claim cutoff with complete indexed keyset scans and a final atomic E6
generation fence. It never drops unresolved history or infers settlement.

FP-04 ownership evidence is produced from these actual observed facts and
immutable E6 claim/canonical lineage, then passed through the real FP-11
boundary. Quantity mismatch prevents intended-lineage convergence. E5 first
interprets the exact protection result; a candidate PROTECTION_VERIFIED
projection is accepted only if the real FP-11 consumer also preserves healthy
protection against its exact lifecycle/FP-12 binding. Duplicate, orphan, unknown
or conflicting evidence follows the real E5 reconciliation event. Definitive
cancellation and current missing protection follow E5 emergency policy.
An active single-order query conflicting with the current missing inventory
cannot retain a discarded initial PROTECTION_VERIFIED candidate. FP-11 is
reinterpreted against the actual original lifecycle: initial unprotected
exposure remains HOLD_SAFE, while previously protected exposure follows the
real PROTECTION_LOST event. The two observations are never combined into a
fabricated healthy state.

No interpretation closes a position, assumes a triggered stop filled, infers
flatness from an empty list, renews a source observation timestamp or grants
cleanup. Residual/exit/newer-flat/FP-10/funding settlement remain separate work.

## Durability and replay

Native inventory, original position clocks, FP-04 dependencies, FP-11 evidence,
source lifecycle projection and reason are retained in the existing E6 dispatch
position outbox. It remains on the existing database/claim/process-generation
graph; there is no second lifecycle database. Exact E5 projection plus complete
FP-12 binding are committed to that outbox before public canonical publication.

Management reuses the original stored raw position observation unchanged. It
does not overwrite its historical raw lifecycle field or manufacture another
broker observation. Partial publication is replayed through the same existing
owner writers without GET, POST, credential access or fresh observation clocks.
The receipt is immutable. Same observation time with different original native
material is a conflict; replay of identical material returns the original result.

## Qualification boundary

Tests use the actual E6/E7/E4/E5 implementations with a controlled fake provider.
They do not verify a real provider account, native secure vault, real forward
duration, cloud connection, final installation or trading activation. S12 stays
IN_PROGRESS until its remaining continuous-runtime/exit/settlement obligations
are implemented and qualified. Final product commissioning remains separate.

Provider source inspected on 2026-10-03:
[official OKX API documentation](https://www.okx.com/docs-v5/), GET Algo order
list, pagination, algo order state and algorithmic-order field definitions.
