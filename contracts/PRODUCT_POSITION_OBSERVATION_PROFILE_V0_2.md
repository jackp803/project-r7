# Product position observation and publication — v0.2

This additive E4 adapter/application profile is
`okx-product-position-readback-v0.2`. Canonical quantities, E5 lifecycle/FP12,
funding/TradeResult semantics and all v0.1 behavior remain unchanged.

## Native facts and clocks

The bounded reader queries BTC-USDT-SWAP only, with an optional single exact
native `posId`. Exactly one explicit SWAP/isolated/net/USDT row is required.
Signed native contracts normalize through current validated linear BTC contract
metadata using Decimal arithmetic. Nonzero exposure requires a positive average
entry price. Empty/error/duplicate/malformed/other-profile responses remain
unproven. An explicit zero row requires the previously selected native identity;
this observation alone cannot close a Position or settle a TradeResult.

The original native `uTime` is retained separately from actual request-start and
response-receive clocks. Native update time cannot be future-dated. A read must
finish within30 seconds and use current submit metadata. An unchanged position
can have an older native update time; only an actual newly performed owner-
admitted GET creates a new local observation. Parsing copied JSON or changing a
clock cannot renew an issued observation. Native IDs remain adapter audit data.

Official documentation checked2026-10-03:
[OKX positions and reconciliation](https://www.okx.com/docs-v5/trick_en/#positions).
The provider describes exact `posId` queries returning previously opened flat
positions and explains that `posId` can survive closing/reopening. Therefore it
is never substituted for the canonical E5 position-instance identity.

## Actual owner composition

`TradingService.read_position` requires the issuing E4 mechanical owner and a
current READ_ONLY_RECONCILIATION proof, actual E6/E7 MANAGE_EXISTING permission,
the selected production account hash when applicable, and the current dispatch
process. It obtains a separately issued admission for the actual GET and
rechecks owners after reading. FIXTURE uses only the bounded scripted driver.
Issuer identity, independent fingerprint, metadata, provider object and process
generation bind the returned observation; copied/mutated/expired observations
cannot be used. The retained receive clock expires after5 seconds and current
metadata requirements are checked independently.

Entry observation consumes the original durable entry claim, exact original
plan and complete canonical orders/results/fills. Native net quantity, average
price and update time must converge with actual entry facts. The existing E5
`product-entry-observation-v0.2` builder emits initial or reattested projections.
Its stable position mapping is exposed as data through
`product_entry_position_id`; it grants no financial authority. Recovery passes
both exact position and plan identities to the existing E6 owner.

A valid older FP12 with only `E5_EXECUTION_REINTERPRETATION_REQUIRED` may be
reinterpreted through the actual E5 builder using complete newer execution facts
and a fresh issued native position read. Missing/invalid/conflicting bindings or
other unresolved reasons remain blocked. A new native position identity or a
regressing original native update clock cannot replace the retained instance.

## Durable publication and initial-stop ambiguity

Migration0015 adds an immutable position observation/outbox and publication
receipts on the existing E6 dispatch connection. One atomic commit retains the
sanitized adapter audit plus exact raw Position/E5 projection/FP12 effects before
canonical publication. No native fields enter canonical financial objects and
no network operation crosses a SQLite write transaction. Current process leases
fence writes. Partial publication/restart replays the original immutable effects
through the existing canonical writers without another provider request.

The product profile permits one initial protective stop per canonical position,
with readback of the original committed request. Another committed initial-stop
claim for that account/position blocks a new request, even if a pending view is
empty. Historical claims without an instance binding block the account until
their original ambiguity is resolved; they cannot be treated as absence proof.
The same original operation can only reconcile. This adds no stop replacement,
amendment, blind cancellation or new protection authority.

## Acceptance boundary

Pure native parsing and actual E6/E7/E4/E5 SQLite/fake-provider tests verify these
mechanics. They do not prove real account compatibility, credential storage,
native commissioning or real forward operation. Continuous E2/E5 orchestration,
protection monitoring, residual/exit/newer-flat settlement, complete broker
funding truth and runtime/control projections remain separate S12 work. No
acknowledgement, empty response or native position ID grants closure or capital.
