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
| ENTRY | Actual E5 ApprovedTradePlan through ExecutionGateway; typed same-account flat positions/no pending orders; submit-current metadata | Existing shared E4 market conversion, fixed stable client ID, exact net/isolated fields; original canonical quantity never enlarged |
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
that its client ID equals the parent algo client ID. This checkpoint does not
yet normalize spawned child fills; missing child-binding implementation remains
a delivery gap to complete before the S12 runtime recovery assignment is done.
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
owner; actual application dispatch/publication composition is still pending.

Public protocol sources checked2026-10-03:
[OKX API reference](https://www.okx.com/docs-v5/) and
[current official English reference](https://app.okx.com/docs-v5/en/).
Native stop details expose ordIdList; successful ACK and algo trigger information
must be followed by actual order/fill/position observations. Current-account
capability and persistent LIVE authorization remain NOT_VERIFIED/NOT_AUTHORIZED.
