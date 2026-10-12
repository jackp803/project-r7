# Windows normal product Paper usability checkpoint

Same task `CODEX-R7-PRODUCTIZATION-MASTER-20261002` and branch `codex/r7-productization-master-20261002`; full Master **IN_PROGRESS**. Current Windows executable `d36d916207b3a2ca4b1479c48c238e836def9dcb`; build `sha256:a0a62854493900a467a2da25b7b3ffacc2e74aec84639ccf14f323226c4eab89`; implementation `sha256:38da2066db07e23472e82070ccb9843d69bb442f5cb0a6643e29edd94c128d51`. Full source qualification actually executed at `b9667dffc6de71b3dc03e2be0f170ab39830d489`. All 638 qualified source inputs are identical in its metadata descendant d36; this is not a new full-source run at d36.

## Package and user startup

Paths below are relative to the user's project root `交易機器人主體`. Current executable: `artifacts/r7-native-windows-S16-research-validity-d36d916/dist/R7/R7.exe`. Portable archive: `artifacts/r7-native-windows-S16-research-validity-d36d916/r7-product-0.2.0-windows-d36d916.zip`; archive hash `sha256:ddffe736db5e053b4fad726579bea9354cbf7b329d92733476e4dced899564d7`. Keep the complete R7 directory together. Package binaries stay local; Git contains sanitized evidence.

The verified mode is explicitly **FIXTURE**: synthetic data/policies, isolated account, local fake cloud, accelerated observation. It has zero real-forward duration and zero remote acknowledgements. Ordinary LOCAL_RESEARCH Paper still requires the four accepted PM/E6 mappings below.

Open PowerShell in the project root and use a fresh run folder:

```powershell
$r7Project = (Get-Location).Path
$r7Executable = Join-Path $r7Project 'artifacts\r7-native-windows-S16-research-validity-d36d916\dist\R7\R7.exe'
$r7Run = Join-Path $r7Project 'user-runs\fixture-d36d916'
New-Item -ItemType Directory -Path $r7Run -ErrorAction Stop | Out-Null
$r7Config = Join-Path $r7Run 'product.json'
$r7Data = Join-Path $r7Run 'data'
$r7Cloud = Join-Path $r7Run 'synthetic-cloud'
& $r7Executable init-profile --config $r7Config --data-root $r7Data --cloud-root $r7Cloud --execution-mode FIXTURE
& $r7Executable prepare-fixture --config $r7Config --scenario positive
& $r7Executable configure-research --config $r7Config --selection-profile (Join-Path $r7Data 'fixture-inputs\selection.json')
& $r7Executable enroll-owner --config $r7Config --username local-owner
& $r7Executable serve --config $r7Config --desktop
```

Create the local login through the hidden password prompt. In Control Center, log in, scan the inbox, select `r7-synthetic-fixture-input` and `r7-synthetic-fixture-policy`, and queue research. In another terminal with the same executable/config variables run `research-worker --config $r7Config --once`. The strategy view displays the actual research outcome.

Stop the server before configuration; select Paper with `configure-paper --config $r7Config --selection-profile (Join-Path $r7Data 'fixture-inputs\paper-selection.json')`, then restart `serve --config $r7Config --desktop`. For the actual candidate select its policy and press **開始 PAPER**. Run `paper-worker --config $r7Config --maximum-ticks 2`; this stops with a protected position. Use **停止新進場**, then run `paper-worker --config $r7Config --maximum-ticks 4`; the fixture exits the position while retaining pause. Recorded stop acceptance is bounded public ManagedStop. Actual interactive Ctrl+C or graceful control-server stop was not verified here.

Use the actual research `owner_run_id` with `queue-research-feedback --config $r7Config --namespace FIXTURE --run-id OWNER_RUN_ID`, then bounded `publish-fixture-outbox --config $r7Config --limit 1` until no work remains. Reports are owner-generated; Paper assessment stays BLOCKED because real observation is zero. Staging gives no real cloud receipt. See [normal fixture guide](../../../../docs/product/v0_2/NORMAL_FIXTURE_PAPER_FLOW.md) and package FIRST_RUN.md for complete backup/restore guidance. Run `oos-loss` and `insufficient-oos` in separate fresh folders with their respective prepare-fixture scenario. Never edit stored research results.

## Actual user flow, current native package

| User operation | Actual Windows evidence | Remaining limit |
| --- | --- | --- |
| First setup and login | 3 new public profiles, actual hidden TTY enrollment and browser login | Full installer/platform acceptance pending |
| Isolated data, policies and transport | Public fixture and immutable research selection configuration | Synthetic data/local fake cloud only |
| Receive strategy | Actual inbox scan and durable accepted package | Real cloud commissioning NOT_RUN |
| Research, robustness and sealed independent OOS | Separate actual native research child in all 3 profiles | Full capacity/platform acceptance pending |
| Candidate, rejection and insufficient evidence | CANDIDATE/PASS; REJECTED/FAIL; BACKTESTING/BLOCKED | No injected candidate/PASS/Approval |
| Allowed Paper start | Positive candidate and actual selected policy, then separate worker | FIXTURE only; ordinary release proposed |
| Negative Paper start | Disabled UI plus authenticated 409 CURRENT_OWNER_EVIDENCE_REQUIRED | Zero runs and unchanged registry in both negatives |
| Signal, risk, fills, protection and exit | 2 canonical fills, 1 closed trade | Accelerated observation; zero real-forward time |
| Actual UI state | 11 packaged browser stages; elapsed seconds displayed as 0 | Self visual check, no independent whole-product acceptance |
| Pause and worker stop | Public pause and bounded ManagedStop; protected position retained | Control cleanup forced; no graceful-control credit |
| Restart and recovery | Worker generation 1 to 2; binding, position and first-fill anchor retained | Full fault/recovery matrix pending |
| Results and receipts | 2 actual BLOCKED Paper reports, performance OPT_OUT, local staged bundles | Remote ACK 0 |
| Backup and restore | Protected state preserved; original unchanged; restored worker inhibited | Cross-platform recovery pending |

Three current native outcomes passed in 38 recorded owned commands: 27 CLI and 11 browser, plus 3 actual TTY enrollments and 7 owned control starts. All owned process trees reaped and awake request restored. Bounded execution/TTY readiness review has 0 Critical/Important findings and no reviewer execution; visual review is SELF. Operator usage/interrupted-prompt diagnostics are retained separately and receive no passing-command credit.

## Formal services and platform separation

Formal CLI/API/UI composition uses actual E1 dataset/replay, E2 declarative engine, E3 research/robustness/sealed OOS, E4 PaperBroker, E5 risk/protection and E6 registry/process/canonical journals. Authentication, intake, selected research/Paper owners, independent workers, feedback staging and backup/restore are wired into product entrypoints. Verification reads actual state/identity; it supplies no owner factories or terminal facts. Other fake private-provider/LIVE transports and fault seams remain separately scoped source-test evidence.

| Platform or commissioning | Status |
| --- | --- |
| Windows 11 x86-64 | Current normal FIXTURE 3/3 PASS; full native product acceptance incomplete |
| Ubuntu 24.04 / 26.04 x86-64 | NOT_RUN; no approved installed target identified |
| Real cloud / real dataset | NOT_RUN |
| Ordinary Paper / real-forward observation | NOT_RUN; release mapping PROPOSED_NOT_ACTIVE; actual elapsed 0 |
| Real provider / credentials / capital | 0 / NONE / NONE |

Ubuntu needs an approved existing x86-64 target of each required release, measured memory/disk, CPython 3.12 and pinned build dependencies; Node and UI dependencies for compilation. systemd/SSH needs the separately approved host/admin context. On each target, check out the exact candidate cleanly, then execute `python3.12 tools/build_product.py --output APPROVED_PROJECT_ARTIFACT_ROOT --expected-revision d36d916207b3a2ca4b1479c48c238e836def9dcb` and `python3.12 tools/verify_native_product.py --package-root ACTUAL_PACKAGE_ROOT --output FRESH_LOCAL_PROOF_ROOT`, followed by the owner/service/recovery/access/capacity acceptance in [service plan](../../../../docs/product/NATIVE_UBUNTU_SERVICE_PLAN.md) and [administration guide](../../../../docs/product/NATIVE_UBUNTU_SERVICE_ADMIN.md). Ubuntu commands have not executed. No OS installation or hosted compute is authorized by this report.

## Exact PM/E6 decisions and outstanding work

The [decision bundle](PRODUCT_USABILITY_DEPENDENCIES_20261008.md) specifies affected files, minimum mappings and blocked operations: (1) fixed qualification producer inventory/platform checks; (2) initial native release/build identity; (3) config/risk/simulator/account generations; (4) independent runtime generation/currentness/recovery. Git acceptance remains absent on fetched main `9fd277798b1c51d1bc79b29a61bec81b552efeb1`. These block ordinary qualification, Paper admission or recovery. No E7 financial relaxation is requested or applied.

Exact-clean source b966 executed 33 commands / 2,115 instances, phase 1 247 and phase 2 1,868, zero failures/errors/skips, 638 unchanged inputs. Its seven request-expiry regressions passed after bound fail-first verification. The implementation is included in this d36 native package, but expiry-specific native scenarios are **NOT_RUN**. Current native normal 3/3 are fresh executions; historical 13d negative-intake 5/5 is not transferred to d36. UI source checks remain 18 unit/11 browser at unchanged 9a48e09 inputs; no new source-UI execution is claimed.

Remaining independent Master work includes current native request-expiry/intake scenarios, full recovery/resource-pressure/capacity tests, requirement-by-requirement coverage and whole-branch review. All M1-M11 remain IN_PROGRESS; no full requirement PASS is claimed. External Ubuntu, accepted release mappings and real cloud/data/forward evidence remain separate.

Public [disposition](native-current-user-flow-d36d916/disposition.json) and [manifest](native-current-user-flow-artifact-hashes-d36d916.json) retain 106 sanitized artifacts with original/published hashes. Private profiles/auth/config/databases/datasets/backups and binaries are excluded. Provider requests 0; credentials NONE; capital NONE; runtime LLM 0; GitHub compute NOT_USED; main merge NOT_PERFORMED. Project data stays beneath the project root. No profitability or real-money launch date follows from fixture or regression counts.
