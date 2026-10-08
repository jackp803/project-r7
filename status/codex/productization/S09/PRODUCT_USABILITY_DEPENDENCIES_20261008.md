# Normal product Paper flow: dependency and decision bundle

Task CODEX-R7-PRODUCTIZATION-MASTER-20261002 remains ACTIVE on
codex/r7-productization-master-20261002. This bundles the outstanding technical
decisions; it is not a request for credentials, capital or real trading.
Main was fetched: 9fd277798b1c51d1bc79b29a61bec81b552efeb1.

## Verified dependencies

Normal `src/application/entrypoints.py:create_local_app` composes LOCAL_RESEARCH
authentication, command ledger and LocalOwners. `local_owners.py:control_services`
installs actual E6/intake/research adapters and PaperReadControlPort, but no
PaperStartControlPort or PaperOwnerWorker. The current packaged CLI has no
Paper worker entry. The source UI qualification used qa/serve_fixture.py and
does not prove normal native composition.

`application/paper/owners.py:PaperOwnerComposition` is implemented and qualified
at ac0b889829777db884666f82bd2d18f2c38ba4cb. It opens actual same-store owners on
the owner thread, but needs a trusted current ReleaseBinding reader and selected
workflow. `storage/qualification.py` retains software-only owning receipts;
`application/platform/runtime_identity.py` reads observed running process facts.
Neither issues a qualified financial/runtime release.

The accepted `contracts/PRODUCT_RESEARCH_NATIVE_PROVENANCE_PROFILE_V0_2.md`
explicitly prohibits native inventory from asserting qualification or authorizing
Paper/LIVE. `registry/operational_authority.py:ReleaseBinding` requires exact
hashes, positive generations and SOURCE_QUALIFIED/NATIVE_QUALIFIED for
LOCAL_RESEARCH. The S12 QUALIFIED_PAPER_RELEASE_PROFILE_PROPOSAL.md is still
PROPOSED_NOT_ACTIVE; no PM/E6 acceptance receipt has been found in authoritative Git.

## Decisions needed for ordinary LOCAL_RESEARCH Paper

| Missing accepted decision | Minimum proposed decision / affected scope | User operation blocked |
|---|---|---|
| Owning qualification producer's fixed check inventory and platform scope | Accept explicit check IDs/order, exact subjects, required no-skip source/native/UI/owner-fault evidence; protected software receipt store, no caller PASS | Qualify/select an installed ordinary Paper release |
| Initial release kind and build mapping | Native-only NATIVE_QUALIFIED initially, bound to actual distribution inventory; SOURCE_QUALIFIED remains unavailable until its convention is accepted | Start ordinary source/native Paper without inventing a build identity |
| Config/risk/provider/account generation mapping | Accept canonical operational selection hash/generation, exact selected E5 policy/generation and isolated local simulator identity; preserve all E6 financial semantics | Bind a candidate and selected simulation workflow to a current release |
| Runtime generation mapping and currentness | Bind independent runtime-role supervisor generation/current source/build/config observation; owner effects retain existing E6/E5 fences | Admit Paper start and recover management under the current independent owner |

These are the precise PM/E6 mappings requested by the existing S12 proposal.
Acceptance must be recorded in Git. Codex will not mark the proposal accepted.
No separate E7 financial relaxation has been identified; actual LIVE/forward
requirements remain unchanged. If E6 requires a different mapping, its accepted
contract must specify it before ordinary issuance/admission is enabled.

## Already authorized work, without those decisions

APP-01/02 and OPS-01 authorize the issuer/store/reader implementation, normal
service wiring, selected workflow controls, independent worker and recovery.
An isolated immutable FIXTURE product acceptance mode is authorized by the
usability objective and UI-01/OPS-01. It uses ReleaseBinding release_kind FIXTURE,
actual research producers and normal product composition, conspicuous labeling
and no financial approvals. Implementing that mode is outstanding work, not a
PM blocker. Existing test-only private fixtures do not satisfy it.

Public first-run staging/research selection is being integrated and verified
through the normal CLI/API/research child. Next, wire the defined isolated
acceptance mode and normal Paper worker, fake market, pause/stop/restart and
publication using actual canonical services. The ordinary release mapping
decision can proceed independently; no idle waiting is authorized.

Ubuntu 24.04/26.04 native environment, real cloud connection/dataset and real-time
forward observation are still unexecuted. Windows/source and accelerated fixture
results cannot qualify these. No reliable real-money launch date or profitability
claim follows from executable test counts.
