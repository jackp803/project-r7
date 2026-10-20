"""Retain actual late supplements without rerunning completed product flows."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import _sanitize
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.supervision import _local_path
REV='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
FACTS=verify_distribution(BASE/'build-aa2d00a/dist/R7')
def guard():_guard(ROOT,REV,BASE/'build-aa2d00a/dist/R7',FACTS,fixed_profile(current_target()))
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
guard()
OUT=BASE/'supplements-aa2d00a-late-prepared';create_private_directory(OUT)
files={Path(__file__)}
probes=[]
for name,exit_code,count in (('str12-four-hour-owner-aa2d00a-first',1,1),('str12-four-hour-owner-aa2d00a-retry01',0,1),('ui01-observation-contract-aa2d00a-red01',1,4)):
    folder=BASE/name;checkpoint=json.loads((folder/'checkpoint.json').read_bytes())
    assert (checkpoint['exit_code']==exit_code and checkpoint['tree_reaped'] is True
            and checkpoint['source_and_tests_unchanged'] is True
            and checkpoint['implementation_hash']==FACTS['implementation_hash'])
    log=(folder/'source.log').read_text(encoding='utf-8')
    assert int(re.findall(r'Ran (\d+) tests? in ',log)[-1])==count
    files.update((folder/'checkpoint.json',folder/'source.log'))
    probes.append(dict(ref=name,exit_code=exit_code,source_case_executions=count,qualification_membership='NONE'))
paths=(
 'test_str12_four_hour_owner_aa2d00a.py',
 'test_str12_four_hour_owner_aa2d00a_before_entry_role_repair.py.unapplied',
 'test_ui01_observation_contract_aa2d00a_red.py',
 'ui01-projection-plan-aa2d00a/plan.json',
 'prepare_aa2d_supplements.py','prepare_ui01_projection_patch.py','prepare_ui01_frontend_patch.py',
 'retain_current_checkpoint_aa2d00a.py','record_power_interval_aa2d00a.ps1')
files.update(BASE/name for name in paths)
assert sha((BASE/paths[0]).read_bytes())=='sha256:e10d8ec9eccafbc65c46a506618978f1f49fac96d3afa3aaba11dab1a47b9d57'
assert sha((BASE/'test_ui01_observation_contract_aa2d00a_red.py').read_bytes())=='sha256:ebfdb2bdfdbb727a04b115bd8f7ba5f616e1e401e8c096f2a7b927afaf356b1f'
bindings=[]
for number,path in enumerate(sorted(files,key=lambda p:p.relative_to(PROJECT).as_posix()),1):
    _local_path(path)
    assert path.is_file() and path.stat().st_nlink==1 and path.stat().st_size<=8*1024**2
    original=path.read_bytes()
    text=_sanitize(original.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','')
    safe=('\n'.join(line.rstrip(' \t') for line in text.splitlines()).rstrip()+'\n').encode()
    suffix=path.suffix if path.suffix in ('.py','.json','.log','.md','.patch','.unapplied','.html') else '.txt'
    ref='a'+str(number).zfill(4)+suffix
    write_private_new(OUT/ref,safe)
    assert (OUT/ref).read_bytes()==safe
    bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(original),
        retained_ref=ref,retained_hash=sha(safe),normalization='PUBLIC_SANITIZATION_LF_TRAILING_WHITESPACE_ONLY'))
guard()
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,identity=FACTS,
    scope='SUPPLEMENTAL_ACTUAL_NATIVE_SOURCE_AND_STATIC_EVIDENCE_OUTSIDE_FIXED_RECEIPT',master='IN_PROGRESS',
    recorded_at=datetime.now(timezone.utc).isoformat(),qualification_membership='NONE',development_probes=probes,
    str12=dict(status='GENUINE_4H_RESEARCH_TO_SAME_REGISTRY_PAPER_RECOVERY_AND_MAX_HOLD_SOURCE_SUPPLEMENT_PASS',
        dataset='192_HOURLY_E1_TO_48_COMPLETE_FOUR_HOUR_BARS',
        lineage='ACTUAL_RESEARCH_CANDIDATE_REOPEN_SAME_REGISTRY_NORMAL_RESOLVER_TO_PAPER',
        lifecycle='ONE_ENTRY_ACK_FILL_PROTECTION_NO_BAR_SCHEDULER_NEW_GENERATION_RECOVERY_EXIT_CLOSED',
        initial_failure='TEST_ONLY_ORDER_ROLE_ASSUMPTION_AFTER_GENUINE_CLOSED;CANONICAL_GATEWAY_ROLE_IS_NULL',
        repair='EXACT_ORIGINAL_NONREDUCING_REQUEST_EQUALITY_WITHOUT_ORDER_ROLE_ASSUMPTION',
        real_forward_seconds=0,ordinary_operator_paper='NOT_STARTED',native_credit='NONE'),
    ui01=dict(status='REAL_MISSING_PROJECTIONS_DEMONSTRATED_RED;REPAIR_PLANNED_UNAPPLIED',
        cases=4,subtest_failures=14,errors=0,
        missing_fields=['overview.strategy_subjects','overview.research_stage_counts','overview.resource_limits','overview.alerts',
            'health.components','health.risk','health.execution','health.preflight','health.external_consumer',
            'settings.resource_limits','settings.clock_health','settings.backup','settings.transport_test','settings.credential_presence'],
        identity_regression='OBSERVATION_CLOCK_ADVANCED_WITHOUT_STATIC_CONFIG_COMMITMENT_CHANGE_PASS',
        plan_ref='ui01-projection-plan-aa2d00a/plan.json',
        ordinary_deterministic_remediation='CONTINUE_AFTER_CURRENT_EXACT_CANDIDATE_EVIDENCE_PERSISTED'),
    selected_static_reviews=[
        dict(reviewer='paper_adapter_map',subject='final_str12_test_e10d8ec',critical=0,important=0,execution='NONE'),
        dict(reviewer='pqr_inventory_map',subject='prepare_aa2d_supplements_d02defb',critical=0,important=0,execution='NONE'),
        dict(reviewer='qualification_review',subject='unapplied_UI_App_0748741',critical=0,important=0,execution='NONE')],
    retained_files=bindings,additional_public_requests=0,cumulative_public_requests=8,cumulative_public_responses=8,
    private_requests=0,credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED')
write_private_new(OUT/'disposition.json',(json.dumps(disposition,indent=2)+'\n').encode())
entries=[dict(ref=p.name,hash=sha(p.read_bytes())) for p in sorted(OUT.iterdir()) if p.is_file()]
write_private_new(OUT/'prepared-manifest.json',(json.dumps(dict(revision=REV,identity=FACTS,
    scope=disposition['scope'],artifacts=entries),indent=2)+'\n').encode())
guard()
print(json.dumps(dict(prepared_files=len(entries),actual_probes=len(probes),source_unchanged=True,qualification_credit='NONE')))
