# Codex Current Task — R7 Productization

- task_id: `CODEX-R7-PRODUCTIZATION-P1-20261002`
- state: `ACTIVE`
- program: `R7 Productization V0.1`
- authority:
  - `status/PRODUCT_OWNER_CODEX_R7_PRODUCTIZATION_AUTHORIZATION_20261002.md`
  - `docs/product/R7_AUTONOMOUS_STRATEGY_TO_CAPITAL_V0_1.md`
  - `agents/README.md`
  - existing E1-E7 contracts/ADRs
- base: latest authoritative `main`
- execution: approved local Windows only; GitHub compute forbidden

## Mission

Implement P1 — Cloud Strategy Intake + application skeleton.

Create the first usable end-to-end product boundary:

```text
Cloud Drive synced folder
-> Strategy Package discovery
-> manifest/hash validation
-> durable idempotent local claim
-> E6 Strategy intake
-> application run/status record
-> sanitized result/receipt artifact back to Cloud Drive
```

This task must use the real existing E2/E6 contracts/boundaries where applicable.
Do not create parallel StrategyDefinition or Registry semantics.

## Required deliverables

### 1. Application package

Add an application layer under a clear top-level package such as:

```text
src/application/
```

with bounded modules for:

- product configuration;
- CloudArtifactTransport protocol;
- SyncedFolderCloudTransport;
- StrategyPackage/manifest envelope validation;
- local durable intake ledger;
- StrategyInboxService;
- ResultPublisher;
- application-level status/result models.

Exact filenames may differ if the final structure is cleaner, but all listed
capabilities must exist and remain application-layer code.

### 2. Cloud root configuration

Support a configurable `R7_CLOUD_ROOT`/equivalent application setting.

Do NOT hard-code a user path or cloud provider.

Required logical folders:

```text
inbox/strategies
datasets
research/runs
research/rejected
candidates
paper
live
reports
archive
```

Creation must be idempotent.

### 3. Manifest-last submission protocol

A completed submission directory contains:

```text
strategy.json
manifest.json
```

`manifest.json` is the final producer marker.

Validate:

- package schema version;
- non-empty submission/strategy/version identities;
- exact declared filenames;
- SHA-256;
- no path traversal;
- no absolute paths;
- no duplicate logical artifacts;
- no unexpected secret-like fields;
- immutable package identity.

If manifest is present but a referenced file is temporarily absent or hash
mismatched, classify `INCOMPLETE_SYNC` and allow a later retry. Do not convert
cloud-sync incompleteness into strategy REJECTED.

### 4. Durable intake ledger

Use local SQLite, separate from Cloud Drive.

Minimum durable states:

```text
DISCOVERED
INCOMPLETE_SYNC
CLAIMED
INTAKE_ACCEPTED
BLOCKED
PUBLISHED
```

The same immutable `submission_id + manifest hash` must never execute twice
after restart.

Same `submission_id` with changed immutable package material is a conflict and
must fail closed.

### 5. Real E2/E6 boundary consumption

For a complete package:

- parse/validate its actual StrategyDefinition through the accepted E2 boundary;
- route the exact definition into E6 Strategy Platform intake;
- preserve the current E6 compatibility/evidence semantics;
- do NOT fabricate LOCAL_EXECUTION PASS;
- do NOT promote to BACKTESTING/CANDIDATE in P1.

P1 proves intake, not research qualification.

### 6. Result/receipt publishing

Publish a sanitized immutable receipt under:

```text
research/runs/<submission_id>/
```

Minimum fields:

- receipt schema;
- submission ID;
- strategy ID/version/content hash;
- package manifest hash;
- intake state;
- local application/project revision when available;
- timestamps;
- deterministic reason codes;
- no credentials/raw provider material.

Publishing must be idempotent.

### 7. Product service entrypoint

Provide a callable application entrypoint/service that can perform one inbox
scan deterministically.

A continuous watcher/service loop may be added only if it is bounded,
interruptible and testable. P1 must not introduce trading/PAPER/provider
runtime.

### 8. Tests

Add local deterministic tests for at least:

- valid manifest/package;
- missing payload -> INCOMPLETE_SYNC;
- hash mismatch -> INCOMPLETE_SYNC;
- path traversal rejection;
- duplicate submission idempotence;
- same submission ID changed content -> conflict;
- restart preserves claim/no duplicate execution;
- unsupported/malformed StrategyDefinition -> BLOCKED;
- valid package reaches real E6 DRAFT intake without fabricated PASS;
- receipt publication;
- receipt contains no secret-like fields;
- cloud root initialization is idempotent;
- no GitHub/network/LLM/provider dependency.

## Non-goals / forbidden

P1 must NOT:

- add AI/LLM calls;
- add Google Drive-specific API/auth;
- add provider credentials;
- call OKX/private APIs;
- start PAPER/SHADOW/LIVE;
- implement CANDIDATE promotion;
- modify E2 strategy semantics;
- modify E3 validation semantics;
- weaken E6 evidence gates;
- create GitHub Actions/CI.

## Verification

Run focused application tests locally plus all directly affected existing
strategy/registry/storage tests.

Then run the complete credential-free project test matrix appropriate to the
current repository if available within approved local capability.

Persist:

- exact executable revision;
- commands;
- counts;
- failures/errors/skips;
- exact-clean before/after proof;
- scope diff;
- security scan for committed secrets;
- confirmation of zero provider/LLM/GitHub compute.

## Completion

On PASS:

1. commit/push implementation on a bounded Codex branch;
2. create `status/codex/R7_PRODUCTIZATION_P1_COMPLETION_20261002.md`;
3. include exact implementation revision and local evidence;
4. stop for PM static review.

Do not self-start P2 from this task. P2 will be issued after P1 acceptance so
the research orchestrator binds to the accepted intake interface.
