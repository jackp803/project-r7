# OKX product action-role mechanics v0.2

Additive E4 profile `okx-product-action-role-capability-v0.2`; close sizing
`okx-product-close-residual-sizing-v0.2`. The v0.1 action-role, trigger-basis
and close-sizing public entry points remain pinned and reject this new profile.
This document defines mechanical translation and observation only. Repository
evidence and synthetic HTTP tests do not verify an actual account or authorize
production requests, financial exposure, native process admission or deployment.

The initial profile is OKX V5 / linear BTC-USDT-SWAP / BASE_ASSET BTC to CONTRACT,
account level2 / net_mode / isolated. Regional hosts, hedge/cross modes, other
instruments and unsupported combinations have no executable translation here.
The trusted production transport separately requires exact operator-confirmed
`https://www.okx.com`, verified TLS, bounded responses and allowlisted endpoints.

| Role | Required canonical owner facts | Native translation/readback |
|---|---|---|
| ENTRY | Actual E5 ApprovedTradePlan through ExecutionGateway; issuer-bound current same-account flat positions/no pending orders; submit-current metadata | Existing shared E4 market conversion, fixed stable client ID, exact net/isolated fields; original canonical quantity never enlarged |
| PROTECTION_STOP CREATE | Actual E5 PositionAction/FP03 actionable current LAST_PRICE; current E5 OPEN_UNPROTECTED; actual current complete empty FP11 bound to exact action/plan/request/trigger | Conditional reduceOnly stop, native last, market execution-1; exact tick/lot representation, actual current position quantity, no silent rounding |
| POSITION_EXIT | Actual current E5 close-v0.1 action, same plan/position, current FP04 owned reducible exposure and exact metadata/applicability binding | Shared FP05 arithmetic under explicit new versions; reduceOnly market size no larger than canonical authority/provider reducible exposure |
| EMERGENCY_EXIT | Actual E5 emergency close authority and the same FP04/FP05 gates | Same reduceOnly fieldset and bounds; no override of reconciliation or sizing failures |
| READ_ONLY_RECONCILIATION | Exact instrument/order/algo scope through trusted composed transport | Observation only; errors/empty responses never prove absence or permit a retry |

Mechanical proofs are issuer-local objects bound to typed account facts, exact
metadata, role and generation. Account observations expire after30 seconds;
submit metadata retains the existing5-second bound. Changing account/metadata
invalidates issued proofs. Copies, arbitrary mappings/PASS/booleans and in-place
fact mutation cannot substitute for an issuer record. An E4 preparation is
immutable, locally issued, expires after at most1 second and never grants HTTP
authority. E6 current consent, E7 current process proof and durable dispatch
ownership remain separate gates immediately before a real effect.

Entry prerequisite observation has the explicit
`okx-product-entry-prerequisites-v0.2` profile. Its exact typed account/position/
pending-order snapshot is independently hashed and expires after5 seconds.
The trusted E4 observation producer supplies its original read timestamp; caller
PASS, missing/copy/mutated proofs and stale snapshots are rejected. Issuance and
submit recheck the same capability generation. Metadata/account changes invalidate
the observation proof; the preparation cannot outlive it. This pure data proof
does not make a synthetic observation real or grant HTTP authority.

FP11 empty-set interpretation does not itself authorize protection. The separate
actual E5 protection action and FP03 consumer must pass. Missing protection from
OPEN_PROTECTED/PROFIT_PROTECTED still follows PROTECTION_LOST to EMERGENCY;
this profile does not restore OPEN_UNPROTECTED or cancel duplicates/orphans.
Trailing replacement/amendment and provider-setting mutation are not executable.

Market order readback verifies native instrument/mode/side/type/size/reduceOnly,
stable client ID and known provider ID before using the existing canonical
parser. Partial fills remain partial; native zero average price is interpreted
as unavailable only with zero fill. Matching fill rows must have exact order,
side and unique trade identities; contract-to-BTC conversion and signed fees
reuse the canonical parser. ACK produces PENDING with zero fills, never OPEN,
FILLED, protected, flat or CLOSED authority. Private rejection text is discarded.

Stop readback verifies exact conditional/last/market/reduceOnly/size fields and
native algo identity. ACTIVE is distinct from TRIGGERED_REQUIRES_CHILD_ORDER.
The one verified child ID comes from native ordIdList, not from an assumption
that its client ID equals the parent algo client ID. Explicit
`okx-product-stop-child-readback-v0.2` interpretation verifies the spawned market
order and complete matching fills. Parent OrderResult retains the native algo
identity; Fill retains its actual native child identity and original internal
client/plan/position/action/role. Filled quantity and price must reconcile exactly
with actual child fills, whose timestamps cannot be in the future.
Unsupported split child orders, unknown/error states and lookup emptiness fail
closed. Triggered algo size is never a canonical fill or newer flat evidence.

E6 provider dispatch records are additive to existing canonical durability.
An immutable run binds exact owner subject/release/approval/activation hashes;
namespace cannot change. Process generations fence older writers. Immutable
intents reserve provider/account/client ID historically across runs, preventing
the provider's pending-only client-ID uniqueness from becoming a retry policy.
The first dispatch claim commits with synchronous=FULL before I/O. Concurrent
connections can obtain one claim only. Every later claimant and recovered
DISPATCHING/OBSERVED operation requires fresh readback, with no second POST
permission. Sanitized append-only observations are not position or financial
authority. The existing E6 canonical journal remains the domain publication
owner. An additive immutable outbox commits exact canonical effects with the
sanitized provider observation; partial publication replays existing E6 writers
without another provider request. Child IDs are retained separately in sanitized
native lineage. A restored `okx-product-durable-readback-v0.2` context is data
only and cannot pass issuer-owned submit checks.

Application composition rechecks actual current E6 consent/original envelope and
selected E5 policy, E7 process identity, current canonical E5 plan/action/position
hashes and issuer-owned E4 preparation before the committed claim and again before
I/O. FIXTURE can compose only the concrete scripted provider; it cannot compose
the production transport/secure reader. Constructor performs no I/O or secret
read. Every readback obtains fresh current-owner admission; errors/emptiness never
permit a second POST. An unresolved prior entry claim for the same exact provider/
account blocks new entry even if another snapshot reports empty prerequisites.
Only explicit durable zero-fill rejection or exact E6-authoritative CLOSED truth
with settled TradeResult and terminal orders can clear that historical barrier;
fresh current E4 prerequisites and financial admission still remain necessary.
The first profile bounds account entry history verification at1,000 claims and
fails closed beyond that; archival/settlement indexing is an explicit persistent-
runtime capacity gap, not a reason to drop history or infer absence.

The application dispatch/normalization/publication checkpoint is not S12
completion. Actual continuous orchestration/projections, full residual/exit and
newer-flat matrix, financial control integration and native OS/provider
commissioning remain separately required or explicit non-executable gaps.

Public protocol sources checked2026-10-03:
[OKX API reference](https://www.okx.com/docs-v5/) and
[current official English reference](https://app.okx.com/docs-v5/en/).
Native stop details expose ordIdList; successful ACK and algo trigger information
must be followed by actual order/fill/position observations. Current-account
capability and persistent LIVE authorization remain NOT_VERIFIED/NOT_AUTHORIZED.
