# Windows normal product Paper usability checkpoint

Task `CODEX-R7-PRODUCTIZATION-MASTER-20261002`;branch `codex/r7-productization-master-20261002`;Master **IN_PROGRESS**. Executable `dd533694df21bd3608e58408d14b5b05255b4d21`;build `sha256:70e846e59a51c25b94183326e3cc0c245e54df78f31ffeda912b1791e582feab`;Python implementation `sha256:8d39e6f6adf87e18450ef6a7fc43dafee7f5b1ba43b1be20ac2c3781b4039fc6`.

## Package and ordinary user steps

Project root is `C:/Users/jackp/Desktop/交易機器人主體`. Package: `artifacts/r7-native-windows-S09-forward-ui-dd53369/dist/R7/R7.exe`. Portable archive: `artifacts/r7-native-windows-S09-forward-ui-dd53369/r7-product-0.2.0-windows-dd53369.zip`;SHA256 `sha256:080f81c1ff5010bcd604a00cd47735a35bf6ae5742533681c11748b5c5839c98`. Keep the whole R7 package together. The archive is local and is not committed to Git.

This demonstrated workflow uses explicit **FIXTURE** mode,synthetic market/policies,isolated account,local fake cloud and accelerated UTC. It carries zero real-forward time,real cloud acknowledgement or financial approval. Default ordinary `LOCAL_RESEARCH` Paper remains blocked by the accepted-release mappings below.

Use PowerShell;choose a fresh run folder inside the project. The parent directory is created normally;product commands create the protected profile/data. The fake cloud folder must remain fresh for `prepare-fixture`.

```powershell
$r7Project = 'C:\Users\jackp\Desktop\交易機器人主體'
$r7Executable = Join-Path $r7Project 'artifacts\r7-native-windows-S09-forward-ui-dd53369\dist\R7\R7.exe'
$r7Run = Join-Path $r7Project 'user-runs\fixture-dd53369'
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

Create your own local login through the hidden terminal prompt. Log into Control Center,scan the inbox,select `r7-synthetic-fixture-input` and `r7-synthetic-fixture-policy`,then queue research. In another PowerShell terminal,with the same executable/config variables,run `research-worker --config $r7Config --once`. The strategy view shows the actual owner result.

After stopping the control server with Ctrl+C,select Paper using `configure-paper --config $r7Config --selection-profile (Join-Path $r7Data 'fixture-inputs\paper-selection.json')`,then restart `serve --config $r7Config --desktop`. View the actual candidate,select its Paper policy and press **開始 PAPER**. Run `paper-worker --config $r7Config --maximum-ticks 2` in another terminal;this stops with a protected open position. Use **停止新進場**,then run `paper-worker --config $r7Config --maximum-ticks 4`;the fixture closes the existing position and retains pause. Omitting the tick bound runs continuously;Ctrl+C uses cooperative worker stop. The harness used bounded ManagedStop;it does not claim actual interactive Ctrl+C/control-server graceful-stop acceptance.

Worker reports are owner-generated and stay BLOCKED because real observation is zero. Use the research `owner_run_id` with `queue-research-feedback --config $r7Config --namespace FIXTURE --run-id OWNER_RUN_ID`,then bounded `publish-fixture-outbox --config $r7Config --limit 1` until no work remains. This stages bundles locally with zero remote acknowledgement. Full command guidance,including protected backup/restore,is in [the normal fixture guide](../../../../docs/product/v0_2/NORMAL_FIXTURE_PAPER_FLOW.md) and the package's FIRST_RUN.md. Use separate fresh run folders for `oos-loss` and `insufficient-oos`;do not change stored results or reuse an existing fixture folder.

## Actual user workflow evidence

| User operation | Current frozen Windows evidence |
| --- | --- |
| First setup and login |3 fresh public profiles;actual hidden TTY enrollment and browser login |
| Isolated data/policies/fake cloud |Public prepare-fixture/configure-research;immutable selections,explicit namespace |
| Strategy package intake |Actual inbox scan and durable accepted package |
| Research/robustness/independent OOS |Public native research worker and separate native child in all3 profiles |
| Candidate/rejection/insufficient evidence |CANDIDATE/PASS;REJECTED/FAIL;BACKTESTING/BLOCKED |
| Allowed Paper start |Actual positive candidate,selected policy;generation0/runtime NOT_STARTED before worker |
| Noncandidate Paper denial |Enabled policy and valid login;disabled UI plus authenticated409 CURRENT_OWNER_EVIDENCE_REQUIRED;0 runs and unchanged registry |
| Signal/risk/fill/protection/exit/journal |Existing owners;2 fills,1 closed trade;no injected state or factories |
| UI actual status |11 actual packaged browser stages;real_elapsed_ns0 displayed as seconds0 |
| Pause and controlled worker stop |Public pause and bounded ManagedStop;protected position remains managed |
| Restart/recover |Generation0→1→2;binding,position ID and first-fill anchor preserved |
| Results/receipts |2 actual BLOCKED Paper reports;performance opt-out;verified local bundles/remote ACK0 |
| Backup/restore |Actual protected state copied/fenced;original unchanged;restored worker rejected/inhibited |

The3 scenarios used38 recorded owned commands (27 CLI,11 browser),3 separate actual hidden TTY enrollments and7 owned control starts. All command trees reaped. Control-server cleanup was forced;no graceful control-stop credit. Visual review was self-review of the actual positive closed-paper screenshot;the new native proof drivers received self-review,not whole-Master independent acceptance.

## Product composition and remaining commissioning

The normal public entry uses the actual E1 dataset/replay,E2 declarative engine,E3 research/robustness/sealed OOS,E4 PaperBroker,E5 risk/protection and E6 registry/process/canonical journals. Intake,selected owners,independent research/Paper workers,feedback staging and backup/restore are wired into public CLI/API/UI entrypoints. Verification imports only observe state and identity;they do not inject runtime factories,candidates,PASS or Approval.

Fake private-provider/LIVE transports and fault seams elsewhere remain source-test evidence;this native flow does not grant them whole-product or financial acceptance. Real cloud and real-time ordinary Paper are separate commissioning steps. Selected fixture policy does not activate the ordinary release proposal.

| Platform / commissioning | State |
| --- | --- |
| Windows11 x86-64 |Current native3-outcome normal FIXTURE flow PASS;full native product acceptance incomplete |
| Ubuntu24.04 /26.04 x86-64 |NOT_RUN;no approved installed host/VM identified;Windows credit is not transferred |
| Real cloud /dataset |NOT_RUN;local fake staging/synthetic input only |
| Ordinary Paper /real-forward observation |NOT_RUN;PROPOSED_NOT_ACTIVE release mappings;actual elapsed0 |
| Real provider/credentials/capital |0/NONE/NONE;no live activation or money exposure |

An approved Ubuntu target must be actual24.04 or26.04 x86-64,with measured memory/disk,existing local CPython3.12 build runtime and pinned native dependencies;Node/build assets are required for UI compilation. systemd/SSH commissioning needs its separately approved local host/admin context. Do not install an OS or switch to hosted compute from this checkpoint. On each approved target separately,build with `python3.12 tools/build_product.py --output APPROVED_PROJECT_ARTIFACT_ROOT --expected-revision dd533694df21bd3608e58408d14b5b05255b4d21`,then run `python3.12 tools/verify_native_product.py --package-root ACTUAL_PACKAGE_ROOT --output FRESH_LOCAL_PROOF_ROOT` and the normal owner/service/restart/backup/access/capacity acceptance required by the existing [service plan](../../../../docs/product/NATIVE_UBUNTU_SERVICE_PLAN.md) and [administration guide](../../../../docs/product/NATIVE_UBUNTU_SERVICE_ADMIN.md). Those commands have not been executed on Ubuntu.

## Exact PM/E6 decisions and acceptance limits

The [current decision bundle](PRODUCT_USABILITY_DEPENDENCIES_20261008.md) requires Git acceptance of4 mappings:fixed qualification producer checks/platform scope;initial native release/build identity;config/risk/simulator generations;runtime generation/currentness. Each blocks ordinary qualification/Paper admission or recovery. Minimum proposal is explicit native-only qualification receipts bound to actual owner/distribution subjects,with no caller-supplied PASS. No E7 financial relaxation or real credential request is introduced.

Python bytes remain identical to full source `d3d849642f278ccd39723355367bf1030d8f0619` (2101 execution instances);current UI18 unit/11 source-browser checks stay at `9a48e09f877b46d5e6f0971cf6a47df8c0485859`. This is a new native build/normal-flow proof,not a new full Python run. Old25 native baseline scenarios remain scoped to d3 and were not silently transferred to this new build. All M1-M11 stay IN_PROGRESS;full requirement PASS0 pending the remaining requirement audit and mandatory evidence.

Public [disposition](native-forward-ui-dd53369/disposition.json) and [manifest](native-forward-ui-artifact-hashes-dd53369.json) retain106 sanitized artifacts with original/published hashes. Private profiles/auth/config/DB/datasets/backups/temp and binaries remain local and excluded. Provider requests0;credentialsNONE;capitalNONE;runtimeLLM0;GitHub computeNOT_USED;main mergeNOT_PERFORMED. All R7 folders are inside the project root.

Next:continue the same Master with the S16 requirement-by-requirement evidence audit and remaining authorized independent work. No earnings or real-money activation date is implied.
