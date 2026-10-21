"""Write actual completed checkpoint dispositions after all guarded executions."""
from datetime import datetime,timezone
import json,re,subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
revision,attempt=sys.argv[1:3]
backup_attempt=sys.argv[3] if len(sys.argv)==4 else 'first'
if (len(sys.argv) not in (3,4) or not re.fullmatch('[0-9a-f]{40}',revision)
        or not re.fullmatch('first|retry[0-9]{2}',attempt)
        or not re.fullmatch('first|retry[0-9]{2}',backup_attempt)):
    raise ValueError('Exact subject/attempt required')
if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=revision:raise ValueError('Recorded source candidate moved')
if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='codex/r7-productization-master-20261002':raise ValueError('Original branch required')
ref='status/codex/productization/S12/current-windows-'+revision[:7]+'/disposition.json'
d=json.loads((ROOT/ref).read_bytes());facts=d['identity'];paper=d['ordinary_windows_paper_software']
if d['executable_revision']!=revision or paper['status']!='PASS' or paper['groups_completed']!=7:raise ValueError('Retained complete actual software evidence required')
stages={}
for name in ('build','qualify','portable','headless','unattended','ordinary-idle','qualified-backup'):
    label=attempt if name=='qualify' else backup_attempt if name=='qualified-backup' else 'first'
    row=json.loads((BASE/(name+'-'+revision[:7]+'-'+label)/'checkpoint.json').read_bytes())
    if row.get('passed') is not True or row.get('revision')!=revision:raise ValueError('Every actual checkpoint stage must pass')
    stages[name]=row
guide=PROJECT/'deliveries'/('current-windows-'+revision[:7])
if json.loads((guide/'version.json').read_bytes())['identity']!=facts:raise ValueError('Actual delivery differs')
binding=json.loads((BASE/('acceptance-records-'+revision[:7]+'.json')).read_bytes())
memory=d['owning_resource_observation']
if memory.get('retention_mode') not in ('COMPLETE_OWNING_TREE_OBSERVER','HOST_AND_PQR05_ONLY'):
    raise ValueError('Explicit retained resource observation scope required')
if memory['retention_mode']=='HOST_AND_PQR05_ONLY':
    if (memory['peak_owned_rss_bytes'] is not None or memory['peak_owned_private_bytes'] is not None
            or memory['complete_owning_run']['process_memory_status']!='UNKNOWN_NOT_OBSERVED_FOR_THIS_ATTEMPT'):
        raise ValueError('Unobserved complete-run process memory must remain unknown')
    resource_text=f"""The complete owning run has no aggregate process-tree RSS/private measurement;
both full-run peaks remain UNKNOWN. Actual host-availability samples recorded
minimum {memory['minimum_host_available_bytes']}bytes. The separate native PQR05
finite one-Paper-owner/one-research-job/control window sampled peak RSS
{memory['pqr05_isolation']['sampled_peak_total_rss_bytes']}bytes and private memory
{memory['pqr05_isolation']['sampled_peak_total_private_bytes']}bytes. These slice
values are not full-run peaks; continuous sampling coverage and maximum capacity
remain NOT_ESTABLISHED. SOFT_LIMIT_ONLY remains explicit."""
else:
    resource_text=f"""The actual complete owning-tree observer recorded peak RSS
{memory['peak_owned_rss_bytes']}bytes and private memory {memory['peak_owned_private_bytes']}bytes;
minimum available host memory was {memory['minimum_host_available_bytes']}bytes.
This bounded sampled run establishes no maximum capacity or hard memory cap.
SOFT_LIMIT_ONLY remains explicit."""
portable=stages['portable'];now=datetime.now(timezone.utc).isoformat()
checkpoint=dict(executable_revision=revision,identity=facts,owning_software='PASS_FIXED_PROFILE7_OF7',
    receipt_ref=paper['receipt_ref'],execution_id=paper['execution_id'],commands=paper['commands'],
    source_case_executions=paper['tests_run'],failures=paper['failures'],errors=paper['errors'],skipped=paper['skipped'],
    native_first_run=portable['first_run'],archive_ref=portable['archive_ref'],archive_hash=portable['archive_hash'],
    installation_ref=portable['installation_ref'],files=portable['extracted_files'],
    headless=d['headless'],backup=d['backup'],real_public_data_research=d['real_public_data_research'],
    ordinary_financial_selection='ACTUAL_OPERATOR_UNSELECTED;SOFTWARE_IDLE_SELECTION_WORKFLOW_FALSE',ordinary_operator_paper='NOT_STARTED',real_forward='NOT_STARTED',
    launch_guide_ref=(guide/'README.md').relative_to(PROJECT).as_posix(),evidence_ref=ref,
    memory=memory,
    recorded_at=now)
p=ROOT/'coordination/CODEX/PROGRESS.json';v=json.loads(p.read_bytes())
previous=v.get('current_windows_checkpoint')
history=v.setdefault('current_windows_checkpoint_history',[])
if previous and previous not in history:history.append(previous)
v['current_windows_checkpoint']=checkpoint
v.update(state='IN_PROGRESS',executable_revision=revision,candidate_executable_revision=revision,
    active_step='S16_CURRENT_WINDOWS_CHECKPOINT_AND_REMAINING_LOCAL_MASTER_CLAUSES')
v['next_step']='Preserve the newly qualified bffc Windows checkpoint and repaired UI01 source/browser proof. Complete semantic66+150 clause decisions and named independent local work. Preserve earlier K03/H01-H16-K05 source/native-producer evidence at original subjects; current STR12 genuine4h/A08 supplements are separately scoped. Old-PC/Ubuntu/real cloud/SSH/formal-policy and real-forward commissioning remain explicit and unselected; Master IN_PROGRESS.'
platform=v['platforms']['windows-11-x86_64'];platform['latest_exact_scoped_checkpoint']=checkpoint
platform.update(native_package_status='CURRENT_COMPLETE_OWNING_FIXED_SOFTWARE_PROFILE_PASS;MASTER_IN_PROGRESS',
    native_package_revision=revision,native_package_build_hash=facts['build_hash'],native_package_implementation_hash=facts['implementation_hash'],
    native_first_run_status='CURRENT_ACTUAL_FRESH_ZIP_PASS',native_first_run_revision=revision,
    native_first_run_scenarios=portable['first_run']['scenarios'],native_first_run_commands=portable['first_run']['commands'],
    native_first_run_build_hash=facts['build_hash'],native_archive_sha256=portable['archive_hash'][7:],
    native_full_product_acceptance='IN_PROGRESS;66_AND150_CONTRACT_CLAUSES_NOT_BLANKET_PASS')
v['windows_abi_type_lifetime_repair']['status']='REPAIRED;CURRENT_ACTUAL_COMPLETE_OWNING_PASS'
v['windows_abi_type_lifetime_repair']['qualified_executable_revision']=revision
for key in ('windows_qualification_helper_path_repair','paper_original_command_retry_checkpoint',
            'windows_research_isolation_fault_budget_repair'):
    if key in v:
        v[key].update(status='REPAIR_INCLUDED_IN_CURRENT_EXACT_COMPLETE_NATIVE_SOFTWARE_QUALIFICATION',
            qualified_executable_revision=revision,current_qualification_evidence_ref=ref)
if 'paper_original_command_retry_checkpoint' in v:
    v['paper_original_command_retry_checkpoint']['native_recovery_branch']='ONLY_ACTUAL_BRANCHES_RECORDED_IN_NATIVE_CLOSURE;SOURCE_RESPONSE_LOSS_TEST_IS_SEPARATE'
v['current_windows_checkpoint_20261019'].update(status='CURRENT_WINDOWS_CHECKPOINT_PASS_MASTER_IN_PROGRESS',
    last_built_candidate=revision,ordinary_paper='WINDOWS_SOFTWARE_QUALIFIED;OPERATOR_POLICIES_UNSELECTED;NO_OPERATOR_RUN',
    owning_pqr='ACTUAL_COMPLETE_PASS7_OF7',native_completion_evidence_ref=ref,
    source_inventory=dict(groups=7,commands=paper['commands'],source_commands=paper['commands']-6,
        source_case_executions=paper['tests_run']))
p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
p=ROOT/'coordination/CODEX/HANDOFF.md'
intro=f'''# Current Windows checkpoint completed; Master continues - {now}

Same task/branch, source candidate {revision}.
Actual complete fixed owning PQR PASS7/7, {paper['commands']}commands,
{paper['tests_run']}source-case executions, failures/errors/skips0. Exact native
software readback passed; receipt{paper['receipt_ref']}.
All owned trees reaped. This is fixed software qualification, not full Master
acceptance or selection of operator financial policies.

Actual new ZIP install PASS{portable['extracted_files']}files/8scenarios9commands;
no copied auth/config, PATHempty/PYTHONPATHunset/Nodeunavailable. Native one-entry
coordinator start/duplicate/stop/child+coordinator crash/recovery PASS. Same actual
qualified ordinary diagnostic profile automatically took engineering package
through intake/research/BLOCKED and durable report without manual enqueue/worker
or report commands. Formal policy absent; no candidate/ordinary operator Paper/
real-forward promotion. Ordinary control/research/runtime idle bootstrap, duplicate,
runtime crash recovery and all-role stop/restart also PASS with workflow=false,
no run, no market acquisition and no new financial permission.
Private complete owning-store backup/verify/restore/
rebackup and four-way original/captured/restored/reback file+receipt equality
PASS. The actual protected runtime selection also matches across all four stores,
with its original generation/config commitment and workflow=false preserved;
restored native admission denied/RESTORED_INHIBITED.

Evidence{ref}; actual launch guide{checkpoint['launch_guide_ref']}.
Archive{portable['archive_ref']}; hash{portable['archive_hash']}.
Exact66+150 case/command/source bindings retained separately; review actual
per-clause dispositions, never turn supporting counts into blanket PASS.
Continue remaining local Master gaps listed in PROGRESS. Preserve this qualified
executable when subsequent code changes; do not transfer qualification to them.
Old target/Ubuntu24.04+26.04/cloud/selected formal policies/real-forward samples
remain distinct. Cumulative public8/8, additional0, private0, credentialsNONE,
mutation0/capitalNONE/GitHubcomputeNOT_USED. No OS configuration or main merge.
Historical records preserved below.

---

'''
p.write_text(intro+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
p=ROOT/'status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'
p.write_text(f'''# R7 Master partial completion record

**IN_PROGRESS — current Windows checkpoint completed; Master is not complete.**
Task `CODEX-R7-PRODUCTIZATION-MASTER-20261002`; branch
`codex/r7-productization-master-20261002`; spec `r7-product-v0.2` at
`7d1f447c8a9e8b46dc5ecc7bf0a78e1d63680812`. Recorded{now}.
Source Git HEAD at generation and exact executable revision: `{revision}`.
Subsequent evidence/document commits do not change this executable identity.
Implementation `{facts['implementation_hash']}`; build `{facts['build_hash']}`.

## Ordinary Windows Paper software

Complete actual fixed owning qualification PASS7/7; {paper['commands']}commands,
{paper['tests_run']}supporting source-case executions, failures/errors/skips0.
Receipt `{paper['receipt_ref']}`; execution `{paper['execution_id']}`.
The installed native software readback verified this exact subject. This is
fixed software qualification, not whole-Master acceptance or financial permission.

Actual native isolated acceptance covered research candidate/rejection/insufficient
evidence and Paper entry/ACK/fill/protection/pause/restart/exit/authoritative flat;
expiry/cancel, nine faults, research/protection isolation, qualification/current
release refusal boundaries and durable owner-report/publication recovery.
These required isolated scenarios remain distinct from an operator strategy run.
The ordinary LOCAL_RESEARCH coordinator also bootstrapped control/research/runtime,
rejected a duplicate, recovered the verified runtime child and stopped/restarted
all roles with its actual owning receipt. Software-only serialization inputs kept
Paper workflow=false, no market acquisition, no strategy promotion or Paper run.
Actual operator research/Paper/risk policies remain unselected; real forward has
not started. Existing successful FIXTURE flows do not replace this distinction.

The Windows per-call ctypes input-type leak was reproduced and minimally repaired.
Changed-byte reads, atomic staging and actual hardware sampling remain fresh;
no source-content cache, global-cache clearing or admission threshold change.
{resource_text}
Historical standby/memory failures and prior scoped successes remain retained at
`status/codex/productization/S12/c3-interim-and-ctypes-repair-20261019/`.
The full b53 helper-build path failure remains at
`status/codex/productization/S12/current-windows-b53ad6d-failed/`; the1e99 native
first-response failure remains at
`status/codex/productization/S12/current-windows-1e99e09-native07-depth/`.
Its actual backend command completed in29.090128s against a15s UI deadline.
The verifier now uses the existing visible pending-original-command retry,
checking identical POST bytes, original revision/receipt and the sole run.
The source response-loss regression is separately labeled; native evidence
claims only the actual recovery branch recorded by its current browser closure.
The local publication helper's private build path was shortened without removing
any identity/complete-runtime inventory checks or changing OS path settings.
The full e48 failure remains at
`status/codex/productization/S12/current-windows-e48f318-failed/`:
its source checks and nine native fault cases passed, but no actual inner
research target was sampled during the strict isolation fault. That attempt
did not qualify. The test's explicit timeout input changed from1s to5s within
the existing observation/resource bounds; production/default timeout and strict
target/protection/cleanup requirements stayed unchanged. The strict same-depth
preflight is separate historical evidence with no full qualification credit.
This current full owning qualification supplies its own actual isolation proof.

## Actual public data and research

Keyless OKX public read-only capture made8requests/8responses cumulatively;
additional requests in this continuation0, private requests0.468BTC4H candles and
234funding records cover2026-08-01T00:00Z through2026-10-18T00:00Z, no observed
gaps/duplicates. Manifest
`sha256:d5a0ae299c78045ff87e321fad7cab50fa73ebb6565f4a4e7f7b439d9cb41f18`.

No qualifying GPT strategy package was found. The actual engineering baseline is
`authoring-example-four-hour@0.2.0`, hash
`sha256:034645d0279cbff987828f59d7ba9a7791f2c9dc4774d1a76b91587bab87bcc7`.
Native normal intake/research actually completed with
`BLOCKED/MISSING_PROMOTION_POLICY` at BACKTESTING. The durable report retained
that real refusal; it did not promote the engineering package. Independent final
OOS, robustness promotion and real forward remain NOT_RUN. Train/development/sealed
periods and engineering fee5bps/slippage2bps assumptions remain explicit; actual
funding data is preserved. These are not selected ordinary operator policies or
GPT research/profitability evidence.

## Headless operation and recovery

One native run-product entry manages selected service roles without browser,
Chat or Codex as a runtime dependency. Native tests covered start, duplicate,
cooperative/repeated stop, control and coordinator crashes, descendant cleanup,
ordinary idle runtime crash/restart and unchanged unauthorized workflow.
The same qualified diagnostic store automatically scanned/enqueued/researched
the engineering input and queued its actual durable report, without manual
worker/enqueue/report commands. Publication stayed PENDING, no remote ACK invented.
Positive operator Paper trading remains unstarted until its actual gates are met.
No host startup, sleep or security setting changed. OS boot registration is not
installed; normal user startup uses the single documented entry.

## Portable Windows candidate and private backup

ZIP `{portable['archive_ref']}`; checksum `{portable['archive_hash']}`.
Actual fresh installation `{portable['installation_ref']}` extracted
{portable['extracted_files']}byte-identical files.8first-run scenarios/9commands
passed with empty PATH, unset PYTHONPATH, no Node and fresh unconfigured auth;
no copied developer configuration, credentials or another machine's authority.
Actual native capability export and the labeled engineering author package form
the Chat authoring kit at
`artifacts/current-windows-20261019/portable-{revision[:7]}-first/chat-authoring-kit/`.
Actual launch/first-setup and target checklist: `{checkpoint['launch_guide_ref']}`
and the packaged FIRST_RUN.md/HEADLESS_LOCAL_OPERATIONS.md.

Native backup/verify/restore/rebackup of this complete owning and diagnostic
store passed four-way file and receipt equality. Restored software admission was
denied; RESTORED_INHIBITED preserved, no cloud/runtime authority restored.
Hardware evidence applies to the measured current32GB-class Windows development
host. It does not certify the reported24GB target or maximum concurrent load.

## Remaining Master and external acceptance

| Area | Disposition |
| --- | --- |
| M1–M11 | IN_PROGRESS; component evidence does not close whole milestones |
| S01–S08, S10–S11 | Existing scoped PASS retained in PROGRESS |
| S09, S12–S16 | Remaining clause/platform/final acceptance IN_PROGRESS |
| Exact66+legacy150 records | Actual case/command/source/receipt bindings retained; per-clause semantic review remains, no blanket PASS |
| Remaining local work | Final semantic66+150 clause review and named independent checks. UI01 actual source/backend/browser repair is included in this newly qualified candidate. Earlier K03/H01-H16-K05 component evidence retains original subjects; current STR12 and A08 source supplements remain outside fixed receipt membership. No native remote ACK or cross-platform acceptance inferred. |
| Original target PC | External native commissioning pending;24GB is user-reported, no hardware screenshot requested |
| Ubuntu24.04/26.04 x86-64 | Native build/install/service/reboot NOT_RUN; Windows evidence does not transfer |
| Real cloud | Account setup/connection/actual remote ACK external, no credentials accessed |
| Formal policies and elapsed samples | Unselected/unstarted; no demonstration policy substitutes for real review |
| LIVE | Code/fake-provider tests and actual activation are separate; real LIVE/keys/capital NOT_AUTHORIZED and NOT_STARTED |

Evidence: `{ref}`. Public capture/research:
`status/codex/productization/S12/public-readonly-c62b11a/`.
Continue remaining authorized local Master work while preserving this exact
qualified executable. Later source changes need their own release qualification.
Runtime LLM calls0, private requests0, provider mutation0, credentialsNONE,
capitalNONE, GitHubcomputeNOT_USED. No main merge or actual trading activation.
''',encoding='utf-8',newline='\n')
print(json.dumps(dict(recorded=revision,evidence_ref=ref,master='IN_PROGRESS')))
