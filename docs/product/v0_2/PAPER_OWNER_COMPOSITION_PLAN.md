# Trusted PAPER owner composition implementation plan

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002. Spec: APP-01/APP-02 in 05_PRODUCT_OPERATIONS_UI.md and S09/S12 in 06_EXECUTION_PLAN.md. Continue the existing approved master inline with TDD and verification skills; no new permission for routine implementation.

Build the actual same-store service factory required by the API start port and independent PaperOwnerWorker. Existing PaperService/E6/E5/PaperBroker semantics remain authoritative. The current release reader and HumanAuthenticator are trusted constructor dependencies. This component never creates a qualified ReleaseBinding, imports PASS, selects executable code, calls a provider, or grants LIVE authority. Production release profile/mappings remain PROPOSED_NOT_ACTIVE.

Files: src/application/paper/owners.py owns a validated immutable PaperOwnerSelection and thread-local PaperOwnerComposition.service context manager; tests/application/test_paper_owner_composition.py verifies actual canonical store/start/worker behavior and input/resource boundaries. Existing LocalOwners first-run defaults stay unconfigured until the owning release adapter is available; this is not ordinary native PAPER completion.

- [x] Write and execute failing tests for missing composition, strict immutable selections, wrong namespace/unknown/truthy fields, existing-store requirement, API start generation0, independent worker management and read isolation, cleanup, denied workflow and restoration inhibition.
- [x] Implement validation by reusing existing simulation/risk/promotion/validity parsers; open each E6/process/canonical connection on the service caller thread under ExitStack. Wire an owning resolver closure, selected PAPER policy and trusted current release/authenticator; no parallel model or private resolver overwrite.
- [x] Execute focused and affected actual worker/control/owner/regression cases; diagnose and fix ordinary defects with regression evidence.
- [ ] Obtain bounded independent review, preserve sanitized test evidence, commit a new source checkpoint on the same branch and qualify its exact-clean executable. Continue production release producer/adapter, packaged owner/current browser and remaining master work without relabeling FIXTURE as ordinary or real forward.

Constraints: all tests/builds run on local Windows within the project root; no hosted compute, runtime LLM/provider/private API/credential/capital or main merge. Source tests prove software/isolated FIXTURE mechanics only. Ubuntu24/26 and real cloud/data/forward/provider commissioning remain unexecuted.
