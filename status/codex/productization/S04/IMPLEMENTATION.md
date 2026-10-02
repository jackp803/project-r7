# S04 numerical source candidate

Task/spec/branch remain the existing v0.2 master. Initial 19 numerical tests
observed 34 intended assertion failure occurrences against the missing
implementation; six operator tests failed against missing execution. Additional
source-identity tests exposed missing numerical-file binding and CRLF-sensitive
identity; malformed timeframe/source-field tests exposed one failure and one
error. Fixes were minimal and the assertions retained.

Eight STR-04 families implement explicit Decimal34/HALF_EVEN seeds, Wilder
updates, independent MACD/ADX output warmup, population bands and lagged
Donchian. Scalar and series operators carry typed unavailable/invalid
observations. Missing boolean operands are evaluated before logical reduction;
division by zero cannot become an executable infinity or false signal.

Canonical E1 Candle is the only bar type. Gaps, identity/timeframe/alignment
faults, unfinished candles, missing sources and binary floats are unhealthy.
There is no fill/zero seed or gap recovery that silently resumes an unhealthy
prefix. Provenance binds bar identity/boundary, exact canonical prefix chain,
feature parameters/semantic profile and arithmetic profile.

Actual streaming state retains bounded windows and smoothing accumulators.
Batch replay shares the kernel; independent hand-derived golden vectors test
the arithmetic, while prefix parity tests exercise fresh batch versus retained
streaming state for all 17 outputs. Snapshot restoration replays verified
history and compares the entire expected cache; it never imports cached
numeric facts based only on a timestamp, prefix label or self-asserted hash.
Changed prefixes/parameters/arithmetic/cache are recomputed. Replay cost at
restart is intentional; no unverified fast hydration is claimed.

Local focused verification: 26 indicator tests and 49 strategy tests PASS,
zero failure/error/skip. Includes flat/gap/empty/insufficient cases for every
family/output, n=1, independent DI/ADX warmup, directional ties, both directions,
sqrt and division vectors, context independence, bounds, source identity and
bounded state after 1000 updates. Full exact-clean qualification follows the
source commit; no preemptive claim of full/platform qualification.

Capability identity now includes every numerical and v0.2 strategy module,
using canonical LF source bytes. Indicator execution is available through
this reference API; operational capabilities remain unavailable pending S05
E2 temporal integration and S06 owner-executed compatibility. No current
snapshot is published as a supported PAPER/LIVE contract.

SELF_REVIEW. Native Windows/Ubuntu parity, packages, real-cloud/provider and
forward evidence remain NOT_RUN. No trading startup/credentials/capital,
runtime LLM, GitHub compute or main merge.
