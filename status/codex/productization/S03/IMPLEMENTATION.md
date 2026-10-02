# S03 source candidate

Task CODEX-R7-PRODUCTIZATION-MASTER-20261002; spec r7-product-v0.2 at
9fd277798b1c51d1bc79b29a61bec81b552efeb1. Latest main was fetched and is unchanged.

Explicit additive E2 DSL/runtime routing, bounded typed DAG/unit validation,
new-profile Decimal normalization, two strict authoring schemas and immutable
capability snapshots are implemented. Existing runtime constants remain 0.1.0;
four complete legacy signal goldens were captured from the pre-change
79dd31b8e4ff9bd33df6fc7730371b3adc039543 executable and pass unchanged.

Initial nine new parser tests observed fifteen assertion failure occurrences
and one error against the unsupported profile. Implementation exposed one
deterministic exception-wrapping defect; its existing financial-float rejection
test failed until structured errors were allowed to propagate. Additional
capability/security tests observed seven failures and two errors: missing
capability registry, unbounded/deep/invalid UTF-8 JSON, malformed parameter name,
and Python underscore numeric notation. They are fixed and covered. Schema
tests first failed because authoring schemas were missing. Two test setup
mistakes (unused nonexistent fixture import and incorrectly placed test lines)
were corrected before accepting results, without weakening assertions.

Forty-one strategy tests now pass on local CPython 3.12.10 with zero failures,
errors or skips. Exact-clean full candidate qualification follows this source
commit; this document does not assert that qualification has already passed.

The capability snapshot separates recognition from execution. Numerical
indicators remain NOT_IMPLEMENTED until S04; reference/PAPER/LIVE availability
remains false until corresponding executed owner/platform evidence exists.
Gap receipts bind exact requested/available versions, JSON source location and
new-submission/re-evaluation conditions. No compatibility PASS is synthesized.

SELF_REVIEW only. S16 fresh independent review and native platform/build
qualification remain outstanding. No private provider calls, credentials,
capital, runtime LLM calls, GitHub compute, trading startup or main merge.
