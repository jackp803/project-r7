# Explicit E2 DSL 0.2 / Runtime 0.2.0 profile

This additive profile preserves contracts-v0.1 and the legacy public
Runtime 0.1.0 constants and signal outputs. The router selects DSL 0.2 only
when explicitly requested; unknown DSL versions fail. Parsing a definition
does not authorize compatibility PASS, lifecycle promotion, PAPER or LIVE.

The authoring shape is `contracts/strategy_dsl_v0_2.schema.json`. Package
shape is separately `contracts/strategy_package_v0_2.schema.json`. E2 and
the cloud parser remain authoritative for semantics, security limits, units,
hashes, duplicate keys and path safety beyond JSON Schema's shape checks.

## Concrete grammar

Expression kinds are decimal, parameter, field, feature, lag, indicator and
operator. All objects reject unknown keys. Named features form a bounded DAG;
every declared feature is compiled, including unused ones. AST depth 32,
nodes 4096, features 128, windows/lags 10000 and required timeframes 4 are
fixed local limits. Serialized strategy input is at most 256 KiB; JSON
container depth is additionally bounded before decoding.

Parameters are signed 32-bit integers with ASCII identifiers. Window/lag
positions accept an integer or the explicit parameter reference. Financial
literals and positive exit values use finite decimal strings with at most
34 coefficient digits. Python underscores, binary floats and nonfinite values
are forbidden. Prices and volumes have different dimensions; scalar factors
can multiply them, but dimensionally mixed comparison/addition is rejected.

Indicator names are uppercase SMA, EMA, RSI, ATR, ADX, MACD, BOLLINGER and
DONCHIAN, with the exact semantic versions in the executable AST inventory.
ATR/ADX/DONCHIAN declare a candle timeframe. Other indicators declare a
single-timeframe source expression. ADX outputs value/plus_di/minus_di;
MACD line/signal/histogram; BOLLINGER middle/upper/lower/stddev;
DONCHIAN upper/lower/middle. Other indicators output value.

Operators use kind/name/args. ROLLING_MIN/MAX additionally require window
and lag_bars and have one series argument. LAG uses a series and a bounded
integer literal/parameter argument; the equivalent lag kind uses source/bars.
AND/OR/MIN/MAX take 2–128 arguments, ABS/NOT take one, and other operators
take two. Entry expressions must be boolean.

Exit policy has exactly stop, target, trailing, max_hold_seconds. Each may
be null. Stop supports fixed_price/fixed_distance with value, or atr_multiple
with named ATR feature and multiple. Target additionally supports reward_risk
with multiple. Trailing supports fixed_distance. Values/multiples are positive
Decimal strings. Maximum hold is an integer 1–31536000 seconds or null; this
is a bounded grammar domain, with no default trading duration. E5 retains
all authority over proposals, actual exposure, protection and exits.

## Hashing and availability

Only this new profile normalizes explicitly typed decimal strings before
the existing sorted compact UTF-8 JSON hash excluding content_hash. Signed
zero becomes `0`, trailing zeros are removed, fixed notation is used for
adjusted exponents -32 through 33, and bounded scientific notation elsewhere.
Legacy DSL hashes and captured signals retain their original behavior.

The capability snapshot is immutable canonical JSON with a SHA-256 digest
and a digest of the actual validator source files. Indicator validation
recognition is separate from IMPLEMENTED, VERIFIED_REFERENCE, PAPER_AVAILABLE
and LIVE_PROVIDER_AVAILABLE. S03 deliberately leaves numerical execution and
all operational availability unqualified. Later owner steps must bind actual
verification evidence before advancing those flags. Missing feature/version
receipts include source location, available version and re-evaluation conditions.
An exact snapshot mismatch fails closed; no previous approval transfers.

Source Windows results do not certify native packages, Linux numerical parity
or any provider operation. Capability publication and the API are later
application work, not implicit side effects of building a snapshot.
