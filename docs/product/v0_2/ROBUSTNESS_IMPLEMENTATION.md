# S07 research robustness and sealed OOS implementation

Authority remains the approved v0.2 specification at
`9fd277798b1c51d1bc79b29a61bec81b552efeb1`, especially RESEARCH-02/03/05/06.
This is an executable implementation description, not financial commissioning.

The E3 implementation lives in `src/validation/robustness/`; actual local
composition remains `application.research.service.ResearchService`. Selected
research accepts local policy references, a family identity and an explicit
unsigned 64-bit seed. It accepts no author-produced backtest, assessment or PASS.
Missing selected policies preserve the S06 diagnostic-only behavior.

## Immutable policy and data bindings

`ResearchPolicy` freezes namespace/generation, minimum closed samples per
development/walk-forward/final partition, USDT PnL and USDT-per-trade expectancy,
drawdown units and initial equity, loss streak, profit-factor null handling and
exact split/cost hashes. Thresholds reuse E3 `ValidationPolicy`. Fractional
drawdown is multiplied by the declared initial USDT equity before entering its
legacy amount-valued field; PERCENT is rejected. Insufficient samples and
undefined required evidence are product BLOCKED, while actual quantitative
criterion failure is FAIL. The legacy OOS evaluator's numeric decision is also
retained unchanged, including its legacy FAIL for insufficient trade counts.

Strict public schemas cover research, robustness and Monte Carlo policies.
Runtime checks additionally enforce finite Decimal34 representability,
cross-field units/hash bindings, order, budgets and source/namespace identity.
No fixture policy is installed as a LOCAL_RESEARCH default.

Split clocks are frozen from the strict manifest before financial decoding.
The resolver verifies full container bytes/schema/bounded row-group metadata,
then chooses row groups using only clock columns. Sealed-only price/rate groups
are not loaded. A straddling Parquet group can require native column decoding;
rows outside development are filtered before conversion into Python financial
values, normalization or E1 validation. Development records and their derived
logical hashes are verified; the full declared logical hash explicitly remains
`DEVELOPMENT_VERIFIED_SEALED_LOGICAL_PENDING`. This is not full dataset PASS.
Finalist freeze and durable read claim precede full financial normalization,
E1 verification and actual final replay. Only then is FULL_LOGICAL_VERIFIED
materialized with exact manifest/logical/container hashes in the assessment.

`DevelopmentBinding` contains frozen development-only candle tuples and
recorded funding events, with no reference to the original full dataset or
sealed payload. Actual E2 adapters further cut each training/evaluation window
at its own end. Feature warmup is not a scored trade interval. E3 retains its
next-observed-open/time/protective assumptions and E5 geometry; OHLC estimates
are not continuous runtime or provider replacement authorization.

## Declared finite algorithms

Neighborhood is the ordered Cartesian product of at most eight explicitly
typed bounded sets, with at most256 declared trials. Only parameters actually
referenced by the parsed E2 rules may be perturbed. Each variant has its exact
definition/content hash and immutable research identity; it is not inserted as
a second definition under an existing E6 canonical strategy/version. Invalid
semantic combinations retain their reason and count in the declared sensitivity
denominator. Every valid replay uses actual E2/E3, including insufficient and
unfavorable variants. Budgets are admitted before E2 execution and checked again
for every replay; at most256 replays/200000 evaluated candles are allowed by this
profile. Current source nested replay cost still needs S13/S15 measurement.

Walk-forward uses ordered explicit training/evaluation windows entirely within
development. Training windows may overlap; scored evaluation windows may not.
Boundary entries are purged using the frozen finite holding/label horizon,
and evaluation begins after the selected nonzero embargo. Each window selects
only adequate, quantitatively passing training variants by descending training
net PnL, then lexicographic variant hash. All training outcomes are retained.
Selected evaluation intervals are counted once, with per-window trades/costs
and aggregate actual E3 metrics. The selected pass fraction and any missing
eligible/sample evidence determine the reported window assessment.
The stitched aggregate is also checked against the selected research criteria;
loss streak/drawdown does not reset at a window boundary to manufacture PASS.

Stress replays actual trade/fill rules with explicit additional fee/slippage
BPS and an adverse recorded-funding scenario. The latter charges absolute
recorded event cost times the declared multiplier, even when the factual
baseline would credit the side; it is labeled sensitivity, not historical fact.
The selected stress PnL tolerance and research criteria retain negative outcomes.

Monte Carlo algorithm version is `r7-mc-v1`. RNG protocol is
SHA256_COUNTER_REJECTION_V1: hash `r7-mc-v02:` plus the seed and counter encoded
as eight-byte unsigned big-endian values; rejection before modulus removes
modulo bias. Trade permutation uses descending Fisher-Yates and assesses
drawdown order only. Its expectancy distribution is deliberately absent.
Moving-block bootstrap draws uniform starting indices for overlapping fixed
non-circular blocks, concatenates, then truncates to the original trade count.
It is conditional dependence sensitivity; dependence beyond the chosen block
is not modeled. Both methods are mandatory, with explicit sample source,
block/sample/effective-block adequacy, finite resampling/path budget, Decimal34,
empirical nearest-rank0.05/0.50/0.95 quantiles and rank-resolution metadata.
Empty/inadequate or arithmetic-overflow paths are BLOCKED with no invented
zero-risk distribution. Same inputs/seed/profile reproduce raw paths.

The algorithms do not remove selection bias or unobserved regimes and do not
prove future profitability. Correlated tests/finite samples remain limitations.
No theorem-based coverage or profit-confidence claim is made.

## Append-only trials and one final holdout

Application migration0003 stores experiment families/events, immutable
finalists, holdout observations and immutable results in the local research
job database. These tables contain no canonical lifecycle state. SQLite WAL,
FULL synchronization and short write transactions are used; replay occurs
outside database writer transactions.

Run/policy selection, manual Chat revisions and actual trial starts/outcomes
are appended. E3 emits a trial-start receipt before replay; the private app
recorder checks the current stage lease and stores each outcome as it occurs.
An interrupted stage retains prior results and the started incomplete trial,
even before a complete robustness result exists. Failed/expired job attempts
remain in ResearchJournal. Trial count is the number of distinct immutable
run/partition/variant identities, including invalid/inadequate/incomplete trials;
start/finish events do not double-count a trial. All selected grid/policy inputs
also remain frozen for unperformed stages. No failure is silently filtered out.

Freeze requires completed hash-verified robustness PASS bound to the exact
run input commitment, subject, namespace, selected policies and current source
implementation hash. A caller-constructed finalist must match the stored
immutable finalist bytes/hash. Author-side status strings are not evidence.

Before opening final prices, an atomic short transaction consumes the exact
symbol/time interval. Overlap uses parsed UTC clocks, including fractional
timestamps. Observations are shared across families/strategy hashes/dataset
names/versions within the same namespace, preventing holdout reset by renaming.
Fixture observations cannot poison LOCAL_RESEARCH. Chat/manual observations
also make overlapping periods previously observed. New independent evidence
requires an unobserved interval. Repeating an identical completed request reads
the original immutable report and does not replay or count a new holdout.

A consumed incomplete final evaluation remains BLOCKED after crash. Another
reader cannot publish a competing BLOCKED result over an owned evaluation.
The E3 combined result retains the canonical OOS decision, product adequacy,
all development/robustness/raw hashes, full source verification, family trial
count and exact policies/provenance. Quantitative losses are retained as FAIL;
insufficient final samples remain product BLOCKED.

## Remaining program and commissioning boundaries

S07 source assessment PASS does not yet promote E6: strategies remain
BACKTESTING, with an explicitly BLOCKED candidate gate until S08 materializes
the full guarded canonical lifecycle and exact trusted assessment persistence.
S08 must also reconcile a crash between E6 backtest persistence and the app
attempt receipt; identical upstream evidence must be recovered safely.
First-fill durable clocks/management scheduling remain S09. Source worker
dispatch/resource enforcement/native frozen bootstrapping remain S13/S15.

The actual available host is Windows11 x86-64 / CPython3.12.10. Native Ubuntu
targets/packages, actual data/cloud/forward PAPER/provider verification and
capital authority remain distinct NOT_RUN or commissioning gaps. Deterministic
FIXTURE positive/negative checks qualify mechanics only. No provider credentials,
private requests, trading runtime or capital are used by this implementation.
