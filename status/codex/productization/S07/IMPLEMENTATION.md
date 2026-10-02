# S07 implementation checkpoint

Task CODEX-R7-PRODUCTIZATION-MASTER-20261002 continues inline on the existing
branch. S07 builds on qualified S06 source d33d89159ce41bd9d2a283ac63ce08c7d85ae3e0.
Executable qualification and fixture reports are recorded separately after a
new exact-clean source commit; this file alone is not a qualification result.

Implementation: E3-owned strict selected research/robustness/Monte Carlo
profiles; actual E2/E3 neighborhood/walk-forward/stress, deterministic trade
permutation versus conditional moving-block sensitivity; append-only durable
trials/Chat observations, freeze/read fencing and actual E3 final assessment.
ResearchService now composes the real owner pipeline with local references and
explicit family/seed, preserves diagnostic defaults and leaves E6 BACKTESTING
pending S08. Exact algorithm/limits are documented in
docs/product/v0_2/ROBUSTNESS_IMPLEMENTATION.md.

Observed TDD RED, followed by corrected GREEN: missing Monte Carlo6 tests;
ambient Decimal precision metadata; missing robustness/walk-forward10 tests;
missing holdout ledger6 tests; pre-admission replay occurred, a concurrent
reader published over the owned OOS, unstructured Decimal overflow; missing
ResearchService selected interface; policy amendment reused a colliding E6
upstream backtest identity; missing strict policy schemas; premature sealed
price normalization; missing trial-start receipts on interruption; missing
full verified source summary; wrong upstream input commitment accepted freeze.
An additional RED/GREEN covers a stitched loss streak exceeding the selected
limit although each separate window's shorter streak passes.
Subsequent focused runs cover the repairs. Full exact-clean qualification is
the acceptance gate, with original LF/FP tests unchanged.

Test setup correction: an invalid-OOS fixture initially failed in its test
helper's eager full resolver, before exercising ResearchService. The test now
constructs valid selected policies first, then writes exact invalid sealed
Parquet/manifest bytes; the intended premature-decoding assertion failed and
then passed. Implementation correction: a broad return replacement briefly
changed the persistence return instead of the final replay return. Owner tests
exposed it; the two functions now retain their correct separate return types.
Neither intermediate run is a qualification PASS.

Ruling: full declared logical verification is explicitly deferred until
finalist freeze, while container-byte commitment and development-only logical
verification precede adaptive replay — retaining eager full financial decoding
would violate the stronger v0.2 sealing requirement. Cost if wrong: a later
full input failure consumes the holdout without usable evidence; it is BLOCKED,
never a fresh retry or financial PASS.

Ruling: holdout exposure survives renamed families/strategy hashes and consumes
incomplete reads — otherwise repeated selection could masquerade as independent
evidence. Cost if wrong: conservative reuse is blocked even where a human would
claim the earlier incomplete read was innocuous; use genuinely unobserved data.

Ruling: the current canonical lifecycle is deliberately left BACKTESTING until
the immediately following S08 owner-gate work — a source financial assessment
is not permission to bypass canonical E6. Cost if wrong: promotion waits for
its authoritative backend gate; no fixture/real trading activation is created.

Windows source evidence never qualifies native Ubuntu, real dataset/cloud,
forward PAPER/provider compatibility or capital. All real private requests0,
credentials NONE, runtime trading/SHADOW/PAPER/LIVE NOT_STARTED, capital NONE,
runtime LLM calls0, GitHub compute NOT_USED. All new artifacts are under the
user project folder; no worktrees were put on the desktop root.
