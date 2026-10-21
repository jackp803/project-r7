# E6 current-facts recovery component — D remains incomplete

Explicit recover_current validates a marked run's root/binding, bounded physical
current chain, actual latest published operation/prefix, indexed unfinished tail,
current checkpoint/generation and E4 broker state. It uses one read snapshot and
releases that snapshot before broker domain validation. Concurrent actual E6
append test proves revision/tail cannot be mixed. No old-operation enumeration
or full-audit callback occurs. Unsupported older codec-only runs explicitly refuse
this API and retain their independent full reader.

The immutable result is tagged CURRENT_FACTS_ONLY. A valid current snapshot can
coexist with older corrupted history; the dedicated test requires the independent
full audit to reject that history and never calls the current result a historical
PASS or entry permit. Corrupt current tip/missing root refuse. No ordinary owner
has been switched to this method. The private audit proof and entry/healthy gates
are deliberately required before product integration.

Initial test syntax failure is retained but not counted as feature RED. Stable
missing-feature RED7cases, then53focused and277storage tests PASS,0fail/error/skip,
overlapping scopes. Source components only; no whole-product/native/time credit.
Continue D private proof/invalidation/bounded audit and integration, then E actual
whole-product capacity/new exact Windows qualification and original admission.
