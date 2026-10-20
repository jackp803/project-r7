# Controlled allocated funding ledger source

This is an E4 source implementation profile under ADR-0006 and the unchanged
`funding-allocation-v0.1` contract. It defines only a local FIXTURE wire. It is
not an OKX endpoint, a claim about exchange bill completeness or position
allocation, or authority for a production/private provider connection.

The logical read is `GET /r7-fixture/v1/allocated-funding`. Trusted composition
supplies the exact original canonical plan/position/symbol, private source
account hash/provider/native position, and the half-open interval recovered
from the actual owner's flat observation. No HTTP input selects a source or
asserts completeness. Production composition must reject this source profile.
The fixture `account_hash` commits the original E6 run's selected provider_ref
and account_ref using the existing canonical SHA256 helper. It is a logical
source scope, not the ephemeral E4 account-configuration proof or an exchange
UID hash. Current runtime admission requires that same immutable run binding.

The wire profile is `r7-fixture-allocated-funding-page-v0.1`. Every page has
exactly: `profile`, `snapshot_id`, `snapshot_at`, `subject`, `coverage_start`,
`complete_through`, `page_index`, `cursor`, `next_cursor`, and `records`.
`subject` has exactly `trade_plan_id`, `position_id`, `symbol`, `account_hash`,
`provider_ref`, `native_position_id`, `interval_start`, and `interval_end`.
Every record has exactly `record_id`, `event_time`, `funding_cost`,
`cost_currency`, and `allocation`; allocation repeats the six non-interval
subject fields. The source explicitly guarantees complete per-position
allocation for that subject, with no quantity/rate/time apportionment by R7.

`coverage_start <= interval_start`, `complete_through >= interval_end`, and
`interval_end <= snapshot_at <= request_started_at <= received_at` are required.
The watermark cannot exceed snapshot time. Pages agree on snapshot/subject/
coverage/watermark. Page indices start at zero, returned cursors match the
requested cursor, and each non-null next cursor is distinct. A final null next
cursor affirmatively exhausts the complete snapshot. Last observed event time
is never a completeness watermark. Partial/error/unknown/missing pages fail.
Trusted composition supplies a zero-argument receive clock which is sampled
once after all pages and before source issuance; static datetimes serve unit
fixtures. A failed or regressed receive clock issues no allocation.

Reads are bounded to 16 pages, 1 MiB total canonical wire bytes, 1,000 total
records and 128-character plain decimal lexemes (no exponent). Identifiers
are bounded nonempty text. Each record's allocation must match the exact
subject, its currency must be USDT, and its event must be within declared
coverage. Record IDs are unique across the entire snapshot, even for excluded
boundary records. Event at interval start is included; at interval end excluded.
Rows are normalized in event-time/record-ID order, with exact ambient-context
independent signed-cost aggregation. Positive is a debit; negative is a credit.
Zero-valued or canceling rows remain INCLUDED with their real record count.
Only an affirmatively complete empty allocation is ZERO_CONFIRMED.

The E4 reader issues a frozen allocation bound to its exact source instance,
subject, complete wire hashes and normalized material; copied/replaced/foreign
objects cannot be consumed. A bounded local cache supports immediate producer
consumption. This is object provenance inside trusted composition, not a
cryptographic defense against arbitrary code execution in the process.
Canonical emission contains no raw native/account identifiers. Its source is
`R7_FIXTURE_ALLOCATED_FUNDING_LEDGER`, version
`r7-fixture-allocated-ledger-v0.1`, source kind BROKER_LEDGER. The source's name
and version remain explicitly fixture-only; PaperZero is never relabeled.

Material hashes bind original page content hashes, private scope commitment,
exact interval/coverage/snapshot and normalized allocated records. Receive and
calculation clocks are excluded from allocation identity. The canonical stable
funding ID uses the existing E4 helper, excluding calculated_at. Existing E6
lineage conflicts remain conflicts. Funding alone does not close a Position or
create a TradeResult, cancel a stop, or authorize a later runtime.

Implementation proceeds tests-first: pure E4 source/producer checks, actual
guarded FakeProductProvider acquisition and original-owner publication, then
owned-stop cleanup and E5 TradeResult. Pure tests have no native-owner credit.
Actual production ledger acquisition/completeness/event-time/position mapping
remains unsupported until separately specified and commissioned.
