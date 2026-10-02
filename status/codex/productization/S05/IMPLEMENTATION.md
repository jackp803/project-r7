# S05 temporal/exit source candidate

Existing task/spec/branch preserved. Nine initial temporal/validity tests failed
against missing APIs; three E2 tests then observed missing profile dispatch.
Additional RED cases caught direct-bundle finality/immutability bypass, fractional
millisecond alignment, missing E1/E5 source identity binding and unbounded
visible financial input. Seven E2/E5 exit tests failed against missing consumers.
Further tests caught a time exit waiting for quotes, incomplete approved-plan
binding, permissive exit-request shapes and lost derived-series unit metadata.
Ordinary deterministic defects were fixed and assertions retained. One test
import temporarily duplicated legacy TestCases; the fixture import was corrected
to a module import before accepting counts. One missing-action assertion was
made explicit to turn its None indexing error into an intended failing assertion.

Actual canonical E1 -> additive E2 -> E5 paths now exist for as-of entry/ATR
requests, initial partial-exposure protection with FP-03 evidence and quantity-
bound close requests. Exact legacy E2 output/API constants remain unchanged.
At11:45 UTC15m evaluation excludes08:00–12:00 4h. At12:00 that4h bar becomes
available only after finality and receipt. Future modifications preserve the
entire earlier signal. Explicit historical availability is separately labeled.

Immutable first-fill/request/plan anchors prevent partial-fill clock reset and
stale approved-subject reuse. Deadline exits do not wait for quotes/entry bars.
Trailing proposals remain monotonic and explicitly NON_EXECUTABLE_PROFILE under
the existing E4 protection contract; no unsupported replacement is relabeled.
S09 owns durable runtime anchoring/event/restart integration; S06 owns actual
E3 dataset/research binding and generated executable/evidence capability state.

Focused local results:62 strategy,27 indicators,36 market-data and11 new E5
exit tests PASS, zero failures/errors/skips. Full exact-clean qualification
follows this source commit. Numerical/native Ubuntu parity and native builds
remain NOT_RUN. SELF_REVIEW; S16 independent review outstanding.

No credentials/private provider calls, real cloud/capital, runtime LLM,
GitHub compute, operational trading startup or main merge.
