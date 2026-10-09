"""Record verified scoped evidence and honest normal-product usability state."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local

REVISION='af01b45f980882e64f3c83784d0a4da0731728ba'
SHORT=REVISION[:7]
REF=f'status/codex/productization/S09/public-research-setup-qualified-{SHORT}-py312'
MANIFEST=f'status/codex/productization/S09/public-research-setup-qualified-artifact-hashes-{SHORT}.json'
REPORT=f'status/codex/productization/S09/PRODUCT_USABILITY_CHECKPOINT_{SHORT}.md'
DEPENDENCIES='status/codex/productization/S09/PRODUCT_USABILITY_DEPENDENCIES_20261008.md'
sha=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()


def main():
    raw=read_local(REPO,MANIFEST,1024**2);manifest=json.loads(raw);snapshots={}
    for name,expected in manifest['files'].items():
        assert name.startswith(REF+'/') and '..' not in Path(name).parts
        assert Path(name).suffix in ('.json','.log','.py','.cs')
        content=read_local(REPO,name,64*1024**2);assert sha(content)==expected;snapshots[name]=content
    facts=json.loads(snapshots[REF+'/disposition.json'])
    build=json.loads(snapshots[REF+'/native-build/build-result.json'])
    assert facts['revision']==REVISION and facts['source']==dict(passed=True,tests=2052,commands=33,phase=dict(phase_1=247,phase_2=1805))
    assert facts['source_input_files']==625 and facts['new_component_cases']==11
    assert facts['native_scoped']==dict(passed=True,scenarios=25,commands=28,wrapper_stages=6,
        existing_scoped_scenarios=13,existing_scoped_commands=13,public_setup_scenarios=10,public_setup_commands=11,long_backup_scenarios=2,long_backup_commands=4)
    assert build['identity']==facts['native_build']
    assert facts['ordinary_native_paper']=='NOT_RUN' and facts['production_profile']=='PROPOSED_NOT_ACTIVE'
    assert facts['provider_requests']==0 and facts['credentials']=='NONE' and facts['capital']=='NONE'
    assert facts['source_awake_request']['restored'] and facts['native_awake_request']['restored']
    progress_path=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(progress_path.read_bytes())
    assert progress['state']=='IN_PROGRESS' and progress['qualified_executable_revision']==facts['accepted_prior_revision']
    package=BASE/f'r7-native-windows-S09-public-research-setup-{SHORT}'/'dist/R7'
    checkpoint=dict(status='NORMAL_SOURCE_RESEARCH_FLOW_PASS;FROZEN_SETUP_PASS;COMPLETE_PAPER_USER_FLOW_PENDING',
        executable_revision=REVISION,implementation_hash=facts['implementation_hash'],source_tests=2052,source_commands=33,
        phase_1=247,phase_2=1805,source_input_files=625,new_setup_flow_tests=11,development_affected_tests=51,
        failures=0,errors=0,skipped=0,native_build=facts['native_build'],native_scoped=facts['native_scoped'],
        native_package_location=str(package),normal_source_research_outcomes=['CANDIDATE','REJECTED','INSUFFICIENT_BLOCKED'],
        source_authentication='PUBLIC_ENROLLMENT_WITH_SYNTHETIC_HIDDEN_TTY_INPUT;NOT_NATIVE_INTERACTIVE_ENROLLMENT_PROOF',
        native_new_setup_scope='SELECTION_SHAPE_LOCAL_REFERENCE_NAMESPACE_ONLY;NO_NATIVE_RESEARCH_EXECUTION',
        complete_normal_paper_user_flow='PENDING_AUTHORIZED_FIXTURE_ENTRY_AND_WORKER_IMPLEMENTATION',
        ordinary_paper='PENDING_PM_E6_RELEASE_MAPPING_ACCEPTANCE',production_profile='PROPOSED_NOT_ACTIVE',
        browser='NOT_RUN_FOR_THIS_INCREMENT',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',real_cloud='NOT_RUN',
        real_dataset='NOT_RUN',real_forward='NOT_RUN',full_requirement_pass_claims=0,
        bounded_review=facts['bounded_review'],long_path_recovery=facts['long_path_recovery'],
        native_evidence_binding=facts['native_evidence_binding'],failed_native_probes=facts['failed_native_probes'],
        failed_prior_source_attempt=facts['failed_prior_source_attempt'],failed_backup_source_attempt=facts['failed_backup_source_attempt'],
        external_execution_binding_guard_tests=2,memory=facts['memory'],
        evidence_ref=REF+'/disposition.json',manifest_ref=MANIFEST,report_ref=REPORT,decision_bundle_ref=DEPENDENCIES,
        retained_files=len(manifest['files']),provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    progress['public_research_setup']=checkpoint
    progress.update(executable_revision=REVISION,qualified_executable_revision=REVISION,candidate_executable_revision=REVISION,
        active_step='S09/S12/S13 NORMAL_PRODUCT_PAPER_FLOW',
        next_step='Implement authorized explicit FIXTURE product profile, normal PaperStart owner composition and independent packaged Paper worker/fake-market input. Use actual research producers, UI, pause/controlled stop/restart/recovery/publication. Ordinary release mapping remains PM/E6 proposal; do not wait idly or invent acceptance.')
    progress['milestones'].update(M8='IN_PROGRESS',M10='IN_PROGRESS',M11='IN_PROGRESS')
    progress['status_semantics']=dict(milestones='FULL_PROGRAM_COMPLETION;NONE_PASS',
        steps='PAST_SCOPED_IMPLEMENTATION_AND_RECORDED_CHECKS;S_STEP_PASS_DOES_NOT_CLOSE_MILESTONE_OR_WHOLE_PRODUCT_ACCEPTANCE',
        correction='M8/M10/M11 changed from stale NOT_STARTED to IN_PROGRESS using existing packaging/cloud/scoped acceptance work; executable_revision reconciled to current scoped qualified executable.',
        full_requirement_acceptance='NONE_CLAIMED;WINDOWS_SOURCE_FIXTURE_EVIDENCE_DOES_NOT_SATISFY_UBUNTU_REAL_CLOUD_OR_FORWARD')
    progress['tests_executed'].append({**checkpoint,'step':'S09/S12/S13','phase':'PUBLIC_SETUP_AND_ACTUAL_NORMAL_SOURCE_RESEARCH_WITH_FROZEN_SETUP','status':'PASS'})
    progress['evidence_refs']+= [REF+'/disposition.json',REPORT,DEPENDENCIES]
    windows=progress['platforms']['windows-11-x86_64']
    windows.update(native_package_status='PASS',native_first_run_status='PASS',native_first_run_revision=REVISION,
        native_first_run_build_hash=facts['native_build']['build_hash'],native_archive_sha256=build['archive_sha256'],
        native_full_product_acceptance='NOT_RUN',native_package_scope='BUILD8_FIRST_RUN3_HISTORICAL2_SOURCE_AUTH_EMPTY_READ_DENIAL10_FROZEN_SETUP2_LONG_BACKUP;NORMAL_PAPER_FACTORY_WORKER_BROWSER_NOT_RUN',
        native_public_setup_status='PASS',native_public_setup_scenarios=10,native_public_setup_commands=11,
        current_source_ui_status='HISTORICAL_BOUND_FIXTURE_UNIT15_EDGE11_PASS;NEW_SETUP_INCREMENT_BROWSER_NOT_RUN')
    progress['current_source_ui_checkpoint'].update(status='HISTORICAL_SOURCE_UI_BOUND_ISOLATED_FIXTURE_PASS;NEW_SETUP_INCREMENT_BROWSER_NOT_RUN',
        current_revision_credit='NOT_TRANSFERRED_TO_NEW_SETUP_INCREMENT;ORIGINAL_EXECUTION_REVISION_AND_COUNTS_PRESERVED')
    assert all(progress['steps'][step]=='IN_PROGRESS' for step in ('S09','S12','S13','S14','S15'))
    assert all(value!='PASS' for value in progress['milestones'].values())
    assert read_local(REPO,MANIFEST,1024**2)==raw
    assert all(read_local(REPO,name,64*1024**2)==content for name,content in snapshots.items())
    progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    note=(f'Current product usability checkpoint: {REVISION}, same Master task/branch, IN_PROGRESS. '
        'Normal source public init/configure/enroll/login/scan/enqueue/independent research child produces actual synthetic candidate, OOS-loss rejection and insufficient blocked assessment. '
        'Eleven new setup/flow checks PASS; exact-clean full source33 commands/2052 execution instances PASS (247 focused+1805 full),625 bound inputs. '
        'Fresh Windows build and25 scoped native scenarios/28 commands PASS across6 stages, including10 actual frozen setup scenarios/11 CLI commands. '
        'The new native setup checks shape/local refs/namespace only; no current native auth enrollment/research/Paper worker/browser execution. '
        'Complete normal Paper user flow remains pending authorized FIXTURE entry/worker/fake-market integration; ordinary Paper release mapping remains PROPOSED_NOT_ACTIVE and requires Git PM/E6 acceptance. '
        'The three initial independent Important findings were reproduced and fixed by regression; no independent re-review/whole-product acceptance claim. '
        'A deterministic private backup long-path failure was diagnosed and fixed without weakening ACL, reparse, single-link, inventory, SQLite integrity or restore fences. Six new actual filesystem tests,32 affected checks,three repetitions of the original failure and2 frozen backup scenarios/4 CLI commands pass. Bounded backup re-review has0 remaining Critical/Important; source review only. Both prior failed048713a qualification attempts retained without acceptance credit. '
        'M8/M10/M11 stale NOT_STARTED states reconciled to IN_PROGRESS; prior S PASS means scoped implementation checks, not full M acceptance. '
        f'Launch/workflow/platform/decision details: {REPORT}. Evidence: {REF}/disposition.json. '
        'Continue normal Paper integration without milestone pause. Ubuntu24/26,real cloud/dataset/forward NOT_RUN;provider0,credentialsNONE,capitalNONE,GitHubcomputeNOT_USED,main mergeNOT_PERFORMED.\n\n')
    hand=REPO/'coordination/CODEX/HANDOFF.md'
    hand.write_text(note+'Historical checkpoint record follows; the entry above is authoritative for current work.\n\n'+hand.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    report=(f'# Normal product usability checkpoint\n\n'
        f'Task CODEX-R7-PRODUCTIZATION-MASTER-20261002 remains IN_PROGRESS on codex/r7-productization-master-20261002. '
        f'Exact executable: `{REVISION}`. Implementation: `{facts["implementation_hash"]}`. '
        f'Windows build: `{facts["native_build"]["build_hash"]}`. This is scoped engineering evidence; no whole-product or financial acceptance.\n\n'
        f'## Package and normal user steps\n\nWindows native folder: `{package}`. Archive: `{package.parents[1]/build["archive"]}`. '
        f'No Python/Node is needed on the product PATH. The executable is R7.exe. Keep user data/config outside the distribution and inside the project folder.\n\n'
        '1. Run `R7.exe init-profile --config <absolute local config> --data-root <absolute local data> --cloud-root <absolute disjoint staging root>`. Omit cloud-root if staging is not selected. This creates a nontrading diagnostic profile.\n'
        '2. Supply explicit local dataset/split/cost/research/robustness/risk inputs and an operator-local selection profile outside cloud staging. Prepare the exact selected staging marker; this does not connect a real cloud account. Follow `docs/product/v0_2/PUBLIC_RESEARCH_SETUP_FLOW.md` and its referenced schemas.\n'
        '3. Run `R7.exe configure-research --config <config> --selection-profile <operator local profile>`. It checks shape/namespace/local availability; actual research decides compatibility and outcome. Identical retry preserves selection; different selection requires a separate configuration workflow.\n'
        '4. Run `R7.exe enroll-owner --config <config> --username <local owner>` in a terminal and enter a new local password interactively. Then run `R7.exe serve --config <config> --desktop`. Log in to the local Control Center.\n'
        '5. Scan the selected strategy inbox, choose the configured research policy and enqueue the package. Run `R7.exe research-worker --config <config>` in another terminal to own research jobs independently. Read actual candidate/rejected/blocked results.\n'
        '6. Full Paper start/worker use from this normal profile is pending the integration below. This package is not an instruction to fund or launch real trading.\n\n'
        '## Actual workflow evidence\n\n'
        '| User operation | Actual current evidence | Remaining work |\n|---|---|---|\n'
        '| First setup/login | Frozen public init/configure; source normal enroll/login with synthetic hidden terminal input | Native interactive enrollment/browser end-to-end |\n'
        '| Isolated data/policy/cloud selection | Immutable public setup; actual Windows hardlink/cloud-origin rejection | Normal explicit FIXTURE acceptance profile; real cloud/data commissioning |\n'
        '| Strategy intake | Normal source app/API reads actual local-folder package through intake | Current native flow/browser round trip |\n'
        '| Research/robustness/sealed OOS | Normal source independent public research-worker and standard research child, actual owners | Current native complete research flow |\n'
        '| Candidate/rejected/insufficient | Actual synthetic candidate, actual OOS losses rejected, insufficient assessment blocked | Real selected dataset outcome; never infer real strategy quality |\n'
        '| Permitted Paper worker | Actual owner composition/worker components qualified separately | NORMAL ENTRY NOT WIRED; authorized FIXTURE implementation next |\n'
        '| Signal/risk/fill/protection/exit | Existing source isolated owner/component evidence | Normal entry + independent fake-market worker integration |\n'
        '| UI actual state | Prior source browser fixture execution retained at its original revision | New normal native user-flow browser execution |\n'
        '| Pause/controlled stop | Existing durable read/pause and source owner stop mechanics | Normal integrated runtime use/actual UI proof |\n'
        '| Restart/recovery | Existing source actual canonical worker recovery components | Normal packaged owner and resumed user-flow proof |\n'
        '| Results/receipts | Existing bounded historical native publication and research feedback | Actual newly integrated Paper run publication/recovery |\n\n'
        '## Composition and platform separation\n\n'
        'The normal product now contains public first-run research setup, local auth, command ledger, intake/research owners, independently launched research jobs, and Paper read/pause adapters. '
        'PaperStartControlPort, PaperOwnerComposition and PaperOwnerWorker are implemented components but not installed in normal create_local_app/runtime CLI. Private test composition cannot close that gap. '
        'No current native Paper worker or release issuer is implied by25 scoped native scenarios.\n\n'
        'Windows: current build, setup and existing scoped regressions PASS; complete normal Paper workflow pending. '
        'Ubuntu24.04/26.04: NOT_RUN, no native/WSL host attached. Minimum pending environment is approved local x86-64 Ubuntu24.04 and26.04 with native build dependencies, dedicated service account, local SQLite disk and selected disjoint roots. '
        'Use docs/product/NATIVE_UBUNTU_SERVICE_PLAN.md and docs/product/NATIVE_UBUNTU_SERVICE_ADMIN.md for the existing exact build/service-plan/apply/guarded-service/SSH commands after supplying actual host identities; no OS installation or cloud substitute is authorized here. '
        'Real cloud/dataset/real-time Paper: NOT_RUN. Local folders, synthetic data and accelerated FIXTURE evidence remain separately labeled.\n\n'
        f'## Concrete PM/E6 decisions\n\nSee `{DEPENDENCIES}` for exact program/contract locations, minimal mappings and blocked operations. '
        'Ordinary LOCAL_RESEARCH Paper needs accepted fixed qualification checks/platform inventory, initial release kind/build identity, operational config/risk/simulator/account generation mapping, and independent runtime currentness convention. '
        'S12 proposal remains PROPOSED_NOT_ACTIVE. Authorized explicit FIXTURE profile/normal service wiring/independent worker/fake market/pause/restart/publication work proceeds without those production decisions.\n\n'
        f'## Verification and limits\n\nFull source2052 instances/33 commands (phase1 247,phase2 1805),0 failures/errors/skips,625 unchanged bound public inputs. '
        'New source11 setup/normal research cases, affected development51, and two external execution-binding guards with five dependency mutations are separate counts. '
        'Windows25 scoped scenarios/28 commands comprise8 first-run,3 historical publication,2 source-created synthetic auth empty read/start denial,10 new frozen setup checks and2 actual long-path backup/verification scenarios. '
        'Private backup recovery adds6 actual long filesystem tests and32 affected regression checks; the original failed restored-generation backup passes3 repetitions. Bounded independent backup source re-review found0 remaining Critical/Important. Both earlier failed048713a qualification attempts are retained and grant no acceptance credit. '
        'The five completed native stages retain their original input closure; the final two backup scenarios use a separately bound repaired continuation. Two failed outer probes (missing import path and unprotected synthetic profile parent) occurred before any frozen product command and grant no acceptance credit. '
        'Source normal flow uses fresh unexecuted synthetic LOCAL_RESEARCH inputs, actual research owners, no injected candidate/PASS/approval or manual database rows. Its minimal UI fixture is not browser acceptance. '
        'Native setup inputs only demonstrate shape/local-reference/namespace validation, not financial policy validity. '
        'The independent initial review had0 Critical/3 Important findings; all three were reproduced and fixed by regressions. No independent re-review or S16 whole-product acceptance is claimed. '
        f'Fixed sanitized artifacts: `{REF}`; hashes: `{MANIFEST}`. Historical failed attempts remain evidence only. '
        'Provider requests0;real credentialsNONE;capitalNONE;runtimeLLM0;GitHubcomputeNOT_USED;main mergeNOT_PERFORMED. '
        'No reliable real-money date or profit guarantee follows from these engineering checks.\n')
    report_path=REPO/REPORT
    assert not report_path.exists()
    report_path.write_text(report,encoding='utf-8',newline='\n')
    print(json.dumps(dict(recorded=True,qualified_executable=REVISION,retained_files=len(manifest['files']),master='IN_PROGRESS')))


if __name__=='__main__':main()
