# Additive strategy exit-request implementation profile v0.2

Authority: approved product v0.2 STR-06/07. Semantic owners E2/E5; parent
contracts-v0.1 and existing protection-v0.1 / close-v0.1 remain unchanged.
Status: IMPLEMENTATION_CANDIDATE, subject to S16 independent review before merge.
This does not authorize operational PAPER/LIVE, providers or capital.

## E2 request

`r7-exit-request-v0.2` is immutable canonical JSON: schema_version,
exit_request_profile_version, strategy_id/version/content_hash, symbol,
direction, market_boundary_ref, observed_at, reference_price, exit_policy,
feature_anchors. Unknown fields and mixed expression forms are rejected.
There is no account, quantity, leverage, risk budget or approval field.

E2 produces the request from its actual healthy entry signal and as-of
feature observations. ATR anchors contain finite value, exact semantic
version, the same market_boundary_ref and a non-future observed_at. They are
not replaced with newer bars at fill or subsequent protection evaluation.
The request's hash identifies a proposal; it proves neither authorship nor
E5 approval.

## E5 constraints and first-fill anchor

Fixed price/distance, ATR multiple and reward/risk requests resolve under the
Decimal34 profile. LONG loss stops are strictly below the reference; SHORT
above. Targets have opposite geometry. Nonpositive/equal/crossed constraints
are rejected. Reward/risk needs an explicit stop; no risk amount is invented.

E5 consumes an already approved parent plan and exact E4-normalized Position.
Requested stop/target must match the approved instructions; a mismatch requires
E5 re-evaluation rather than rewriting approval. Initial protection and close
reuse actual canonical E5 builders and quantity/reconciliation checks.

At the first actual fill, the durable runtime must persist the immutable
request hash, exact parent-plan hash, position/plan identity, first_fill_at,
actual initial reference and approved stop/target. This source profile creates
that anchor; S09 owns transactional persistence/restart/event integration.
Never reconstruct an absent first-fill anchor from an arbitrary later partial
fill. Partial fills use current actual exposure but preserve the original
clock and approved geometry. The hold deadline is the first-fill time plus
the narrower requested/approved maximum hold.

Submission validity and entry expiry govern new entries. They do not cancel
required management of existing exposure. A holding deadline may issue an E5
EXIT_REQUESTED even when market data is unavailable; it needs current consistent
exposure and approved lineage, not a new4h entry candle. E4 retains execution
checks. EXIT_REQUESTED is not broker-flat truth.

## Protection and trailing

Initial PROTECT consumes actual exposure and actual FP-03 trigger-validity
evidence. It never claims PROTECTION_VERIFIED. Quote-triggered stop/target exits
use E5 close-v0.1; E3 retains existing conservative stop-first OHLC ambiguity.

Trailing high/low observations are accepted only from current E1 MarketSnapshot
under its freshness classification. Proposals are side-aware and monotonic:
LONG max(previous proposal, high-water minus distance); SHORT min(previous
proposal, low-water plus distance). No proposal loosens the original approved
loss bound. A proposal is not a verified provider stop.

Baseline MODIFY_PROTECTION remains NON_EXECUTABLE_PROFILE. This implementation
does not relabel it protection-v0.1 or bypass E4. S12 must assess any separately
accepted executable modification profile/provider capability. Unsupported LIVE
surfaces remain explicitly NON_EXECUTABLE; operational availability is separate
from reference/backtest/PAPER capability and real authorization.

## As-of observations

E2 input is an immutable AsOfBundle of canonical E1 candles. Both constructor
and factory enforce finality, UTC alignment, contiguous visible history and
receipt cutoff. Missing received_at requires explicitly labeled
historical_close_assumption. Future/incomplete bars do not participate in the
signal or market-boundary hash. Candle aggregation requires every finalized
constituent and records source/target timeframe, normalization version and
an exact constituent digest.

For CROSS the previous observation uses the immediately previous finalized
series bar (evaluation clock for mixed timeframes). Without a recorded later
previous information boundary, its information cutoff is conservatively its
close time. Unavailable previous observations yield no entry; no late-arriving
higher-timeframe value is inserted into that earlier observation.
