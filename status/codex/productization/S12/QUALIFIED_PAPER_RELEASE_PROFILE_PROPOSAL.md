# S12 qualified PAPER release profile: PM/E6 decision draft

Task: `CODEX-R7-PRODUCTIZATION-MASTER-20261002`; baseline `r7-product-v0.2`.
Status: **PROPOSED_NOT_ACTIVE**. This document issues no qualified receipt,
PAPER authorization, financial permission or release acceptance.

## Concrete missing decision

`ReleaseBinding` validates exact identities, positive generations and the
`SOURCE_QUALIFIED`/`NATIVE_QUALIFIED` labels, but no production qualification
issuer or accepted qualification-to-field mapping currently exists. The accepted
`PRODUCT_RESEARCH_NATIVE_PROVENANCE_PROFILE_V0_2.md` expressly says its native
inventory cannot assert qualified release status or authorize PAPER/LIVE.

APP-01/APP-02 authorize an ordinary native PAPER owner without requiring
AgentBridge. They prohibit caller-supplied executable PASS and require actual
native process/configuration generations. Inventing a qualified release from
the current inventory, a `passed=true` JSON file, or control-process heartbeat
would assign unsupported meaning to those canonical release fields.

The read-only independent review identified the owning issuer/store/adapter as
ordinary implementation work, while the exact release profile and mappings need
a bounded PM/E6 decision. Source: `src/registry/operational_authority.py`,
`docs/product/v0_2/05_PRODUCT_OPERATIONS_UI.md`, and the accepted provenance
profile above. No canonical behavior has been changed to resolve this gap.

## Proposed bounded profile

Proposed identifier: `r7-qualified-paper-release-v0.2`.

Initially implement `NATIVE_QUALIFIED` for **ordinary LOCAL_RESEARCH PAPER** on
the actual tested installation/platform only. Keep `SOURCE_QUALIFIED` unavailable
until its source-build-hash convention is accepted. This limits the initial
decision to a measured native build already defined by the distribution profile.
An untested Ubuntu target stays unqualified; Windows evidence cannot substitute.

An internal owning qualification producer must execute a fixed accepted check
inventory, preserve each command outcome/cleanup/log and issue a receipt only
after every required check succeeds against the unchanged exact subject. A
command may select an existing receipt reference; it cannot submit a report,
status flag, alternate executable path or arbitrary command inventory.

Persist immutable receipts with an internal issuance capability in an existing
protected local owner store, without introducing a ninth product database. After
restart, an internal reader resolves that owned receipt and revalidates its
subject and artifacts. There is no import-qualification-PASS API or cloud path.

Proposed required software checks are: complete exact-clean credential-free
source/LF/FP regression with no skipped critical cases; verified native source,
binary, resources, migrations, dependency locks/licenses and assets; actual native
start/restart/fencing/recovery checks on the named target; exact UI asset binding
and required browser cases; and packaged ordinary PAPER-owner mechanics/fault
checks using an isolated immutable FIXTURE profile. Those new packaged PAPER
checks remain unimplemented/unexecuted. Fixture execution proves code mechanics
and cannot supply strategy profitability, real forward duration or workflow
authorization. The fixed profile must define its required IDs/order before the
issuer implementation can produce production qualified receipts.

## Proposed exact field mapping

| Existing ReleaseBinding field | Proposed actual source |
|---|---|
| namespace | LOCAL_RESEARCH; never relabel a FIXTURE journal/result |
| implementation_hash / executable_revision | Current measured native distribution source commitment/revision, matched to the owning qualification receipt |
| build_hash | Exact current `verify_distribution` build hash under `r7-native-distribution-v0.2` |
| capability_hash | Current actual `build_capability_snapshot().snapshot_hash` |
| config_hash | Canonical versioned operational selection: validated product-config commitment, selected simulation/promotion/risk commitments, original submission validity and selected isolated simulator identity; preserve the distinct supervisor product-config hash |
| config_generation | Durable operational-selection generation, incremented on any selected operational configuration change; no hardcoded fallback |
| risk_policy_hash / risk_generation | Current exact selected `ProductRiskPolicy` hash and its existing explicit generation |
| provider_profile_hash / provider_ref | Versioned PAPER-simulator profile tied to the selected explicit simulation policy; no provider-private endpoint/credential |
| account_ref | Explicit selected local simulator identity with the existing ISOLATED_PER_STRATEGY_RUN semantics; never a real provider account identifier |
| runtime_generation | Actual independently running runtime-role supervisor generation, with current source/build/config and observed owner health; never the control/research counter. Per-run E6 producer generations remain separate |
| release_kind | NATIVE_QUALIFIED only after the owning fixed-profile qualification receipt resolves and all current mappings remain exact |

Control/API PAPER start must use this read-only current-release adapter and the
existing selected candidate/risk/workflow checks. API reads never attach a
runtime or claim its process generation. The independent runtime owner attaches
accepted runs and preserves existing E6/E5 reconciliation and protection rules.

Qualification does not choose risk/capital, grant local workflow authorization,
mark a strategy READY_FOR_APPROVAL, replace E7/provider evidence, clear restored
inhibition or activate LIVE. Missing/changed receipt, target, source, build,
selected policy or current runtime owner must fail closed with a typed reason.
Restoration reauthorization remains a separate unresolved integration boundary.

## Requested PM/E6 decision

Accept or amend the proposed profile's qualification inventory/platform scope,
native-only initial release-kind policy, and the exact configuration/provider/
account/runtime-generation mapping before enabling production qualified-release
issuance. Bounded issuer/store/adapter and worker implementation with isolated
fixture verification already remain authorized under the existing master.
No real provider/cloud/forward/capital action is requested.

Until that decision, production qualified-release issuance and dependent release
admission remain blocked on the profile. Continue independent implementation
and isolated fixture verification while unresolved mappings fail closed; tested
source modules and native integrity retain their actual limited evidence.
S13 Ubuntu/systemd, S15 whole-product acceptance and S16 final audit remain open.
This draft is not a final product completion report or a new canonical contract.
