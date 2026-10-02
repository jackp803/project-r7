# S06 research binding profile

Implementation under RESEARCH-01/02/04/05/07 and APP-01. The approved v0.2
specifications remain authoritative. This profile is source implementation;
native packaging, complete S07 robustness/OOS and S08 promotion follow.

## Fixed dataset input

`DatasetCatalog`/`DatasetResolver` consume only explicitly selected relative
JSON/Parquet files under a configured local root. There is no transport, network
fallback or provider/private client. Unknown fields, duplicate JSON keys,
binary floats, unsupported units and unsafe paths fail closed. Windows opened
handles and POSIX no-follow reads reuse the safe-file owner implementation.

Schemas: `contracts/dataset_profile_v0_2.schema.json`,
`split_policy_v0_2.schema.json`, `split_plan_v0_2.schema.json`,
`replay_cost_policy_v0_2.schema.json`. Runtime checks additionally enforce
cross-field ranges, chronological coverage, arithmetic and actual E1 integrity.

Candles use a pinned Arrow schema: ordered UTF-8 contract/symbol/timeframe,
UTC millisecond open/close, string OHLCV, Boolean finality, source, nullable UTC
millisecond receipt and nullable source record ID. Record order is immutable;
there is no sorting, forward fill or gap repair. E1 constructs/validates canonical
Candles before E2. Decimal inputs use the finite34-digit R7 profile. Millisecond
timestamps decode from epoch integers, independent of a Windows IANA database.

Each container has both SHA256 bytes and normalized ordered-record SHA256.
Logical records include source/finality/availability/identity and normalized
Decimal/time values. Dataset identity binds ordered timeframe and funding hashes;
the manifest also binds container hashes, units, source instrument, normalization,
UTC coverage and namespace. An existing catalog identity cannot change its
manifest. Resolved sequences/mappings are immutable. Hashing never authenticates
the factual accuracy of a user-selected external data source.

Current bounded source profile:64MiB/container,200000 rows/container,1024 row
groups,8192 rows and8MiB uncompressed/group/batch; max4 timeframe containers.
Arrow Thrift string/container limits are65536. Research admission measures
hardware/disk and retains S01 SOFT_LIMIT_ONLY memory truth. No hard memory cap
is claimed. S13/S15 own native worker dispatch and measured larger-run capacity.
PyArrow25.0.1 is pinned; official API checked2026-10-02:
https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html
Wheel/license/release locking remains S13 work.

Supported units are explicitly linear perpetual USDT/base prices, base volume
and quantity, USDT settlement. Contract-count/other-currency data is BLOCKED,
never assumed equivalent. Recorded funding has UTC events, rate string/source,
declared interval, exact coverage and both hashes. Missing events/coverage block.
MISSING funding is represented as unavailable, never factual zero. Actual rates
use a labeled entry-fill-price × base-quantity notional approximation in E3;
this is a replay estimate, not an exchange funding settlement observation.

## Frozen splits and actual owner execution

Split policy defines half-open training/development/sealed OOS, feature-only
warmup, bounded holding/label horizon and explicit embargo/rationale. Intervals
are ordered/non-overlapping and aligned. Entry eligibility ends before the
holding/label horizon; boundary-overlapping trades are excluded from scoring.
This conservative profile requires positive warmup/embargo and nonempty purged
partitions. The strategy cannot exceed the selected holding horizon. These
technical bounds do not install a financial promotion policy.

E3's existing `HistoricalReplayEngine` calls the actual explicit E2 v0.2 binding;
it never accepts precomputed author signals as research results. E2 owns as-of
selection and numeric semantics; E5 owns exit constraint/trailing geometry.
Legacy binding/version/output semantics remain unchanged. v0.2 results use
`e3-replay-v02-v1`, record warmup/scoring, fees/slippage/funding and exit model.
Next-open entries remain; stop precedes target when both touch. Trailing changes
apply from the next observed bar. Protective event time remains conservatively
labeled candle-close because OHLC event order is unknown; time exits use the
next observed open, never an invented intrabar quote. Coarse OHLC replay does
not prove between-bar management timing or provider protection modification.
S09 owns actual continuous PAPER management. Production trailing modification
authority remains unestablished under the current protection contract.

Cost policy is selected locally, finite, immutable and explicitly unit-bearing.
It caps replay evaluations (current maximum2000); it cannot provide quantity
or capital authority to E5/runtime. Changes create new hashed run inputs.
File edits after freeze cannot change an in-progress replay's selected costs.

Actual compatibility executes E2 on training-only as-of inputs and persists
the actual signal, source/data/capability identities and local provenance.
Only healthy rule results qualify execution; unavailable or invalid observations
(including division by zero) BLOCK. Parser acceptance/handler availability alone
never becomes compatibility PASS. Numerical handler inventory is generated from
the same actual dispatch callables. Reference qualification, platform, PAPER and
provider flags remain separate and conservative until trusted exact evidence is
materialized in S13/S15. A documentation or grammar capability list is not proof.

`ResearchJournal` stores immutable run inputs and append-only attempt generations,
owner lease, UTC start/end, reason codes and input/output hashes. Expired attempts
become ABORTED; fenced workers cannot finish another generation. Completed outputs
are replayed from verified durable hashes. Ordinary failures retain their attempt.
Long E2 execution occurs before short canonical E6 registration transactions.
E6 has the canonical lifecycle and evidence; application tables contain jobs only.
Fixture/real-research registry namespaces cannot mix or reclassify existing data.

S06 produces actual development diagnostics and E6 BacktestResult persistence.
The complete required robustness, finalist freeze and sealed OOS are NOT_RUN.
Missing selected promotion/risk policies are BLOCKED. No CANDIDATE/PAPER/LIVE
promotion is performed here. S07/S08 must enforce full product gates and retain
unfavorable outcomes. Fixture namespaces never constitute actual market research,
forward qualification, real provider support or reusable deployment approvals.
