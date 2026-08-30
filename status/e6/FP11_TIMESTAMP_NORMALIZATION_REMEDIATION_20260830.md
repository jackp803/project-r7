# E6 FP-11 Timestamp Normalization Remediation — 2026-08-30

## Authority / scope

```text
owner = E6 — Platform / Storage / Persistence Engineer
authority = Product Owner direct bounded defect remediation after approved-local credential-free qualification
source_qualification_revision = bacb5205ac9b895bb968459f88f148323bcc5da6
target_branch = agent/e6-fp11-timestamp-normalization-20260830
branch_base_main = 2fe9912429cad3eebebac1fa46f933b78f024b78
result = PARTIAL / STATIC FIX + REGRESSION DEFINITIONS COMPLETE / POST-FIX LOCAL EXECUTION NOT_RUN
```

This task addresses only the E6-owned FP-11 persistence/currentness/recovery timestamp-normalization defect reproduced by approved-local credential-free qualification. It does not change shared contracts, E4/E5/E7 code, provider semantics, runtime authority, mutation authority, or capital/release state.

## Reproduced qualification evidence supplied by Product Owner

Exact qualification revision:

```text
bacb5205ac9b895bb968459f88f148323bcc5da6
```

Observed approved-local credential-free qualification result:

```text
Phase 1:
11/16 commands PASS
212 passed
21 failed
8 errors
0 skipped

Phase 2:
10/14 suites PASS
828 passed
21 failed
8 errors
0 skipped
```

The bounded deterministic E6 root cause was explicitly identified as FP-11 storage/recovery timestamp normalization.

## Exact root cause

Existing E6 Paper lifecycle persistence already has an authoritative fixed-width storage-key representation:

```python
ordering_time(value)
-> value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
```

`validate_position_projection()` parses `broker_state_observed_at` and returns:

```text
broker_state_observed_at = ordering_time(parsed UTC instant)
```

`_PaperRuntimeStore.persist_position_projection()` therefore writes that six-fractional-digit value into both:

```text
paper_position_current_projection.broker_state_observed_at
paper_position_lifecycle_projections.broker_state_observed_at
```

Example:

```text
caller Position timestamp: 2026-08-29T10:10:05Z
stored lifecycle anchor:  2026-08-29T10:10:05.000000Z
```

The FP-11 `ProtectionRegistryCurrentnessStore.recover()` path previously compared these fixed-width storage keys directly against the raw caller `Position.broker_state_observed_at` string. Therefore semantically identical UTC instants with equivalent textual representations were reported as lifecycle currentness mismatch/conflict.

This was a storage-key comparison-domain defect. It was not a contract, provider, E5 lifecycle, or Position-hash defect.

## Fix

`src/storage/protection_registry_currentness.py` now reuses the existing E6 storage timestamp semantics instead of inventing a second timestamp policy:

```text
_validate_authority raw Position.broker_state_observed_at
-> existing FP-11 UTC parser
-> existing _runtime_validation.ordering_time()
-> position_observed_at_storage
```

Only the two Paper lifecycle storage-row comparisons use the storage-normalized value:

```text
paper_position_current_projection.broker_state_observed_at
paper_position_lifecycle_projections.broker_state_observed_at
```

The raw caller timestamp remains unchanged for all canonical payload/hash/reference domains:

```text
Position hash = unchanged
FP-11 top-level position_observed_at/hash = unchanged
intended-lineage position_observed_at/hash = unchanged
E5 interpretation position_observed_at/hash = unchanged
lifecycle projection canonical payload JSON/hash = unchanged
```

There is no fuzzy comparison, tolerance, prefix match, truncation, millisecond threshold, exception bypass, or parseable-means-equal rule. Two timestamps compare equal in the lifecycle storage-key domain only when strict UTC parsing maps both exact instants to the same existing fixed-width E6 storage representation.

A genuinely different instant remains stale/conflicting according to the existing current-index/history semantics.

## Regression definitions

Added:

```text
tests/storage/test_protection_registry_timestamp_normalization.py
```

Credential-free deterministic definitions cover:

1. no fractional seconds -> `.000000Z` storage key;
2. `.1Z` and `.100000Z` -> same `.100000Z` storage key;
3. `.123Z` and `.123000Z` -> same `.123000Z` storage key;
4. already fixed-width `.123456Z` remains `.123456Z`;
5. real existing `_PaperRuntimeStore.persist_position_projection()` writer followed by close/reopen/recover remains healthy when caller raw timestamp is semantically equal to the persisted fixed-width timestamp;
6. truly different current storage anchor remains `STALE` / fail closed;
7. malformed timestamp remains rejected and recovery returns explicit non-green `UNKNOWN`;
8. restart/recovery uses the canonical storage-key comparison path;
9. lifecycle canonical payload JSON/hash and current-index payload hash remain unchanged by timestamp storage normalization;
10. a newer storage anchor cannot false-green stale evidence;
11. `provider_mutation_authorized=false` and `cleanup_target_ref=null` remain preserved.

The existing `tests/storage/test_protection_registry_currentness.py` remains the directly affected full FP-11 persistence/currentness regression module and is intentionally not rewritten for unrelated concerns.

## Post-fix verification

No approved-local Windows checkout/execution surface is exposed to this ChatGPT session. GitHub Actions/CI/hosted/GitHub-triggered compute is forbidden and was not used.

Therefore the corrected branch has not received executable PASS evidence here:

```text
post_fix_local_regression = NOT_RUN / NOT_PASS
```

Exact future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests/storage -p 'test_protection_registry_timestamp_normalization.py' -v
python -m unittest discover -s tests/storage -p 'test_protection_registry_currentness.py' -v
python -m unittest discover -s tests/storage -p 'test_*.py' -v
```

The first command is the minimum bounded timestamp regression. The second is the directly affected FP-11 currentness suite. The third is the relevant E6 storage regression sweep.

`NOT_RUN` is not PASS. The prior qualification failure counts are reproduction evidence for `bacb520...`; they are not rebound as post-fix PASS evidence.

## Files changed

```text
src/storage/protection_registry_currentness.py
tests/storage/test_protection_registry_timestamp_normalization.py
status/e6/FP11_TIMESTAMP_NORMALIZATION_REMEDIATION_20260830.md
coordination/E6/STATUS.md
```

No migration or shared contract change is required.

## Safety / authority state

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
orders = 0
protection actions = 0
SHADOW/PAPER/LIVE = NOT_STARTED / NOT_AUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

## Handoff

Static E6 remediation and deterministic regression definitions are complete. Because post-fix approved-local execution is unavailable in this session, classification is `PARTIAL`, not `DONE`.

Next owner/action:

```text
Return to PM/E7 for integrated requalification after approved-local execution of the corrected exact revision.
```
