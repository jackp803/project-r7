# P0 Integrated Deterministic Safety Matrix — E7-20260829-111

## Authority and scope

- task: `E7-20260829-111`
- branch: `agent/e7-p0-integrated-safety-matrix-20260829`
- task baseline main at branch creation: `a099a5acd5cbc8fa9d89f107bae527ee6d5c41d0`
- purpose: credential-free cross-module deterministic test definitions for the LF-2 P0 safety seam
- executable verification in this task: `NOT_RUN / NOT_PASS`
- Local Job Request: `NONE`
- provider/private access: `NONE`
- credentials: `NONE`
- provider/account mutation: `0`
- submit/cancel/amend/close/protection provider actions: `0`
- SHADOW/PAPER: `NOT_STARTED / NOT_AUTHORIZED`
- bounded 10U live-fire: `NOT_AUTHORIZED`
- capital exposure: `NONE`
- GitHub Actions/CI/hosted/GitHub-triggered compute: `NOT_USED`

This matrix defines later local qualification evidence. It is not executable PASS and does not alter any release gate.

## Status vocabulary

| Status | Meaning |
|---|---|
| `STATIC_TEST_DEFINED` | A deterministic test definition exists in Git and can later run credential-free on an approved local exact revision. It has not been executed by E7-111. |
| `IMPLEMENTED_UNQUALIFIED` | Owner-level executable behavior exists on current main, but current integrated exact-revision local qualification is `NOT_RUN / NOT_PASS`. |
| `CONTRACT_ONLY` | The accepted profile/design exists but no current executable producer/consumer is qualified for the required runtime behavior. |
| `UNRESOLVED_PROVIDER_FACT` | Provider-native endpoint/field/mode/trigger/close semantics are intentionally unresolved and must fail closed. |
| `NOT_RUN / NOT_PASS` | No approved-local execution evidence exists for this E7-111 integrated matrix. This is never PASS. |

## E7-owned integrated test definitions

| Module | Role |
|---|---|
| `tests/integration/test_p0_integrated_failure_prevention.py` | FP-03 -> E4 binding, FP-04 -> FP-10, FP-05 -> FP-10, FP-11 -> E5 policy composition. |
| `tests/safety/test_p0_integrated_fail_closed.py` | No mutation/cleanup authority from unresolved capability, FP-10 eligibility, FP-11 non-green states, or contract-only runtime preflight. |
| `tests/e2e/test_p0_reconciliation_restart_e2e.py` | E4/E5/E6 FP-11 durable restart/currentness composition, false-green prevention, terminal-flat FP-10 dependency. |

All three are `STATIC_TEST_DEFINED / NOT_RUN / NOT_PASS`.

## Integrated P0 scenario matrix

### FP-03 — protection trigger validity / breached-stop safety

| ID | Scenario | Owner surfaces composed | Expected deterministic result | Classification |
|---|---|---|---|---|
| P0-FP03-01 | LONG stop equal to LAST_PRICE | E1 `MarketSnapshot` + E5 trigger-validity + E4 trigger consumer | `FAIL_CLOSED / TRIGGER_ALREADY_BREACHED`; E4 rejects create evidence | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-02 | LONG stop above LAST_PRICE | same | fail closed; no create/retry authority | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-03 | SHORT stop equal to LAST_PRICE | same | `FAIL_CLOSED / TRIGGER_ALREADY_BREACHED` | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-04 | SHORT stop below LAST_PRICE | same | fail closed | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-05 | Unchanged breached evidence with later wall-clock only | E5 currentness | remains non-actionable; timestamp alone cannot create retry authority | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-06 | Newer market truth after ACTIONABLE evidence | E5 evidence + E4 immediate pre-mutation binding | old evidence rejected as `E4_TRIGGER_VALIDITY_NOT_CURRENT` | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-07 | Newer Position/lifecycle authority | E5/E4 currentness | old evidence stale/non-current; refresh/reinterpret required | owner tests covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP03-08 | Provider trigger basis/type | FP-02 design + FP-03 shared profile | shared LAST_PRICE geometry does not select OKX trigger field/type | `UNRESOLVED_PROVIDER_FACT` |

### FP-04 — external/manual ownership and reconciliation

| ID | Scenario | Owner surfaces composed | Expected deterministic result | Classification |
|---|---|---|---|---|
| P0-FP04-01 | Exact current-generation exact snapshot/lineage | E4 FP-04 producer | only case eligible for `KNOWN_OWNED_CURRENT_GENERATION / CURRENT_KNOWN_OWNED`; still no mutation authority | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP04-02 | External/manual provider object | E4 FP-04 -> FP-10 | `EXTERNAL_UNTRACKED`; no adoption; E5 lifecycle reinterpretation required | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP04-03 | Prior-generation object | E4 FP-04 | provenance only; fresh reconciliation required | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP04-04 | Unknown/stale/conflicting ownership | E4 FP-04 | fail closed / reconciliation or manual review | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP04-05 | Missing local state or similarity only | FP-04 profile + E4 producer | cannot prove ownership | owner/profile covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP04-06 | New provider snapshot/generation | E4 FP-04 currentness | invalidates old evidence ID/currentness | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP04-07 | Uncertain ownership cleanup/cancel | FP-04 + FP-11/E5 policy | no cleanup target and no provider mutation authority | integrated FP-11 safety definition + `IMPLEMENTED_UNQUALIFIED` |

### FP-05 — close/residual sizing

| ID | Scenario | Owner surfaces composed | Expected deterministic result | Classification |
|---|---|---|---|---|
| P0-FP05-01 | Exact fresh current Position/provider reducible exposure | E5 close authority + E4 FP-04 + E4 FP-05 | provider-local sizing bounded to authoritative reducible exposure | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP05-02 | Fresh positive representable residual | E4 FP-05 -> FP-10 | `RESIDUAL_NONZERO_REPRESENTABLE`; lifecycle remains non-flat | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP05-03 | Fresh positive unrepresentable residual | E4 FP-05 | `RESIDUAL_NONZERO_UNREPRESENTABLE`; no provider size; newer evidence required before reevaluation | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP05-04 | Unknown/stale close capability | E4 FP-02 evidence -> E4 FP-05 | `CLOSE_CAPABILITY_UNPROVEN`; no provider size | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP05-05 | Unknown/stale metadata/applicability | E4 metadata + FP-05 | fail closed; no provider size | owner tests covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP05-06 | Shared `reduce_only=true` used as provider proof | shared close profile + FP-02 design | forbidden inference; provider-native semantics remain unresolved | `UNRESOLVED_PROVIDER_FACT` |
| P0-FP05-07 | ACK/FILLED or arithmetic remainder used as flat truth | E4 close/FP-05 + FP-10 | insufficient; authoritative fresh Position zero required | owner + integrated tests / `IMPLEMENTED_UNQUALIFIED` |

### FP-10 — external/manual close lifecycle convergence

| ID | Scenario | Owner surfaces composed | Expected deterministic result | Classification |
|---|---|---|---|---|
| P0-FP10-01 | Terminal/FILLED close order but positive Position | E4 execution evidence + FP-10 | not `LIFECYCLE_CLOSE_ELIGIBLE` | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-02 | External/manual partial reduction | FP-04 external ownership + FP-10 | remains open/reinterpretation; no silent order adoption | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-03 | Flat Position + ambiguous execution/fill evidence | E4 execution + FP-10 | `FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED` | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-04 | Flat Position + active/unresolved protection | FP-11 terminal dependency + FP-10 | `FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED`; no cleanup authorization | owner/E2E covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-05 | Exact fresh zero Position + current FP-04 + clear terminal protection + current lifecycle/binding | E4/E5/FP-04/FP-10/FP-11 | emits `LIFECYCLE_CLOSE_ELIGIBLE` evidence only | owner + safety definition / `IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-06 | `LIFECYCLE_CLOSE_ELIGIBLE` treated as direct lifecycle transition | FP-10 -> E5 | forbidden; E5 alone chooses event/transition | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-07 | Close eligibility treated as final TradeResult | FP-10 + `trade-result-v0.1` | forbidden; no fabricated fill lineage or TradeResult IDs | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP10-08 | New provider/FP-04/FP-05/FP-11/lifecycle/runtime evidence | FP-10 currentness | old convergence evidence invalid | owner tests covered + `IMPLEMENTED_UNQUALIFIED` |

### FP-11 — unique protection registry / multiplicity

| ID | Scenario | Owner surfaces composed | Expected deterministic result | Classification |
|---|---|---|---|---|
| P0-FP11-01 | Complete/current set with exactly one current-owned exact-lineage protection | E4 FP-04 + FP-11 evidence + E5 policy | only healthy unique-protection case; mutation authority remains false | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP11-02 | Complete/current set has zero protection | FP-11 -> E5 | missing/reinterpretation; no create authority from registry evidence | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP11-03 | Two current-owned protections for one intended lineage | FP-11 -> E5 | multiplicity conflict; no automatic winner or cleanup target | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP11-04 | Intended object + external/prior/orphan extra | FP-04 + FP-11 -> E5 | non-converged; no silent adoption/ignore | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP11-05 | Stale/incomplete/unknown/conflicting provider set/ownership | FP-04 + FP-11 -> E5 | non-green/reconciliation | owner tests + `IMPLEMENTED_UNQUALIFIED` |
| P0-FP11-06 | Flat/CLOSED Position + active external protection | FP-11 -> E5 -> FP-10 | false-green CLOSED reopened to reconciliation; terminal-close dependency explicit | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-FP11-07 | Any non-green registry evidence supplies provider cleanup target | FP-11/E5 | forbidden; `cleanup_target_ref=None`, mutation authority false | safety definition + `IMPLEMENTED_UNQUALIFIED` |

### E6 restart/currentness composition

| ID | Scenario | Owner surfaces composed | Expected deterministic result | Classification |
|---|---|---|---|---|
| P0-E6-01 | Real Paper lifecycle writer + FP-11 healthy exact chain | E5 lifecycle/binding + E4 FP-11 + E6 storage | lifecycle projection payload hash remains its own storage domain; Position authority hash remains independent; healthy exact chain recoverable | E6 owner + E7 E2E / `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-02 | Restart exact healthy chain | E6 persistence/recovery | same exact head can recover healthy; never mutation authority | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-E6-03 | Timestamp-only later FP-11 row without explicit supersession | E6 head selection | competing unsuperseded heads -> conflict before and after restart | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-E6-04 | Material explicit valid supersession | E6 append-only/head selection | only declared valid successor may become head | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-05 | Missing predecessor | E6 | incomplete/non-current | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-06 | Cycle or cross-lineage supersession | E6 | conflict/fail closed | owner tests covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-07 | Current-index or durable projection payload/hash corruption | E6 | stale/conflict; never healthy | E7 E2E + owner tests / `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-08 | Missing current E5 interpretation/binding | E5/E6 | non-green/incomplete/stale | owner tests covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-09 | Missing/stale FP-04 dependency | E4/E6 | non-green/incomplete | owner test covered + `IMPLEMENTED_UNQUALIFIED` |
| P0-E6-10 | Position/lifecycle/provider-set/runtime generation changes | E4/E5/E6 | old health invalidated | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |
| P0-E6-11 | Flat/CLOSED row exists while active external protection remains | E5 FP-11 + E6 restart + FP-10 dependency | `STATUS_RECONCILIATION_REQUIRED`, no false-green closed/protected state | `STATIC_TEST_DEFINED + IMPLEMENTED_UNQUALIFIED` |

### FP-16 runtime preflight and provider-capability unresolved facts

| ID | Scenario | Current evidence | Expected result | Classification |
|---|---|---|---|---|
| P0-FP16-01 | Runtime preflight executable producer/consumer | accepted `runtime-preflight-v0.1`; no `src/integration/runtime_preflight.py` | no executable runtime-preflight PASS can be claimed | `STATIC_TEST_DEFINED + CONTRACT_ONLY` |
| P0-FP16-02 | Role PASS reused for different role | runtime-preflight contract | forbidden; role admission non-transferable | `STATIC_TEST_DEFINED + CONTRACT_ONLY` |
| P0-FP16-03 | Missing/stale/dead heartbeat or wrong process/start generation | runtime-preflight contract | fail closed | `CONTRACT_ONLY` |
| P0-FP16-04 | Supervisor/watchdog absent/unknown/incompatible | runtime-preflight contract | non-authorizing where role requires it | `CONTRACT_ONLY` |
| P0-FP16-05 | Catalog registration without local allowlisting | runtime-preflight contract + active LF-0 blocker | not capability READY | `CONTRACT_ONLY / LF-0 BLOCKED` |
| P0-FP16-06 | External consumer/AgentBridge compatibility missing/stale | runtime-preflight contract | non-authorizing | `CONTRACT_ONLY` |
| P0-FP02-UNRESOLVED-01 | OKX protection endpoint/trigger basis/readback/cancel mapping | FP-02 design | no provider mutation path may be inferred | `UNRESOLVED_PROVIDER_FACT` |
| P0-FP02-UNRESOLVED-02 | OKX POSITION_EXIT/EMERGENCY_EXIT native field set/position-mode/reduce semantics | FP-02/FP-05 design | no provider close mutation path may be inferred | `UNRESOLVED_PROVIDER_FACT` |

## Owner-level deterministic modules required in later qualification

The E7 integrated files do not replace these owner suites. At minimum later exact-revision qualification must include:

- FP-03 E5: `tests/position/test_protection_trigger_validity.py`
- FP-03 E4: `tests/execution/test_protection_trigger_consumer.py`
- FP-04/FP-10 E4 evidence: `tests/execution/test_external_close_evidence.py`
- FP-10 E5 reinterpretation: `tests/position/test_external_close_reinterpretation.py`
- FP-05 E4: `tests/brokers/test_okx_close_sizing.py`
- FP-11 E4: `tests/execution/test_protection_registry_evidence.py`
- FP-11 E5: `tests/position/test_protection_registry_policy.py`
- FP-11 E6: `tests/storage/test_protection_registry_currentness.py`
- FP-10 E6 currentness: `tests/storage/test_external_close_currentness.py` and supersession companion
- lifecycle binding/restart: current relevant `tests/storage/test_paper_runtime_*` and `tests/position/test_lifecycle_*`
- E7 integrated: the three E7-owned files listed above.

No historical suite PASS is rebound to this new integration candidate.

## LF gate interpretation

```text
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
LF-3 = NOT_RUN / NOT_PASS
LF-4 = NOT_STARTED / future Product Owner provider-readonly authority required
LF-5 = SHADOW/PAPER NOT_STARTED / NOT_AUTHORIZED
LF-6 = bounded 10U live-fire NOT_STARTED / NOT_AUTHORIZED
Gate D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

E7-111 defines the deterministic composition needed to make a later LF-1/LF-2/LF-3 local qualification meaningful. It does not satisfy those gates by itself.
