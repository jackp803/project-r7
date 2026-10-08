# Public first-run research setup

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002, same branch and v0.2 scope.
Implements OPS-01/APP-01 in 05_PRODUCT_OPERATIONS_UI.md. Continue the authorized
master inline; the product usability priority requires real normal composition.

The native/source CLI accepts an optional disjoint `--cloud-root` on
`init-profile`. It records the staging path without connecting, creating the
cloud directory, initializing a database or enabling Paper/LIVE.

`configure-research --config <absolute-config> --selection-profile <absolute-local-json>`
installs the existing exact `r7-owner-selections-v0.2` envelope. Supply operator
selected datasets and policies under the local data root first, using the
existing schemas. The config and selection profile must be outside cloud
staging. Canonical selection path comparison and an opened-file single-link
check reject ordinary path/hardlink aliases; the original-path reader still
rejects reparse points. The selection profile has the three fields and eleven
per-policy fields documented in
`docs/product/LOCAL_RESEARCH_WORKER_V0_2.md`.

The command checks the selection shape, bounded available local JSON references,
LOCAL_RESEARCH namespaces and selected staging root marker. It does not claim
policy compatibility, dataset normalization, OOS execution or candidate approval.
Every actual owner still validates those facts. Arbitrary code, PASS, approval,
Paper workflow and provider settings are not fields of this profile.

All control/research/runtime/cloud scope locks must be available. Restore
inhibition prevents configuration. An identical selection retry is idempotent;
a different existing selection is preserved and rejected. This initial setup
does not implement operational policy replacement/generation authority.

Normal user sequence, after a package containing this change is qualified:

1. `r7 init-profile --config <config> --data-root <local> --cloud-root <staging> --instance-id <id>`
2. Prepare the selected local dataset/policy artifacts and the explicit R7
   staging marker. Real cloud bridge commissioning remains separate.
3. `r7 configure-research --config <config> --selection-profile <local-selection-json>`
4. `r7 enroll-owner --config <config> --username <owner>`; enter a password twice
   in the protected interactive terminal.
5. `r7 serve --config <config> --desktop`; log in, scan the inbox and enqueue the
   selected submission/policy from Research.
6. In a separate terminal, `r7 research-worker --config <config>`.
7. Inspect the actual Research and Strategies views. A rejected or insufficient
   result is retained and never promoted by this setup command.

Source integration checks use the normal CLI, actual local authentication/API
entry, intake, queue and independently owned standard research child. Three
fresh, never-executed synthetic input sets cover actual candidate, OOS loss and
insufficient OOS sample outcomes. No CANDIDATE/PASS/Approval row is injected.
The LOCAL_RESEARCH source promotion requires an exact clean checkout, so the
three complete pipeline cases run after the candidate is committed. Precommit
development checks retain the actual dirty-source denial; no provenance is
patched to CLEAN. Native interactive enrollment, actual browser rendering,
real cloud/data, continuous Paper and Ubuntu acceptance remain separate.
