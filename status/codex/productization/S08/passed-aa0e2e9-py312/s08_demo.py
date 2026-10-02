from pathlib import Path
from dataclasses import asdict
import hashlib,json,sys,sqlite3
from contextlib import closing
root=Path(__file__).resolve().parent.parent/'workspaces'/'project-r7-productization-master-20261002'
sys.path.insert(0,str(root)); sys.path.insert(0,str(root/'src'))
from application.research.service import ResearchService
from storage.platform import open_sqlite_platform
from tests.application.test_research_robustness import selected
from tests.application.test_product_assessment_binding import risk_fixture
from tests.validation.robustness_fixtures import subject
from tests.application.dataset_fixtures import encoded
from tests.registry.test_operational_lifecycle_v02 import OperationalLifecycleTests,CANONICAL_EDGES
from registry.models import CANONICAL_LIFECYCLE_STATES,LifecycleTransitionRecord
from registry import InvalidTransition
revision='aa0e2e9431374a6838359d04ef80bc7df5cb0d38'
destination=Path(__file__).resolve().parent/'r7-productization-S08-fixtures-aa0e2e9'
if destination.exists(): raise RuntimeError('Never overwrite existing fixture evidence')
destination.mkdir()
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def adverse(rows):
    for index,row in enumerate(rows[32:]):
        row.update(open=str(1000000+index),high=str(1000002+index),low=str(999999+index),close=str(1000001+index))
summaries=[]
for kind,expected,state in (('positive','PASS','CANDIDATE'),('quantitative-negative','FAIL','REJECTED'),
                            ('insufficient-final','BLOCKED','BACKTESTING'),('missing-risk','PASS','BACKTESTING')):
    target=destination/kind; selected(target,adverse if kind=='quantitative-negative' else None)
    if kind=='insufficient-final':
        policy=json.loads((target/'research.json').read_text()); policy['minimum_closed_trades']['sealed_oos']=100
        (target/'research.json').write_bytes(encoded(policy))
    kwargs=dict(submission_id='qualified-'+kind,definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',
        cost_policy_ref='cost.json',research_policy_ref='research.json',robustness_policy_ref='robustness.json',family_id='fixture-family',seed=42)
    if kind!='missing-risk':
        (target/'risk.json').write_bytes(encoded(risk_fixture())); kwargs['risk_policy_ref']='risk.json'
    with ResearchService(local_root=target,database_path=target/'research.sqlite',registry_path=target/'registry.sqlite',
                         namespace='FIXTURE',owner_id='qualified-fixture') as service:
        outcome=service.run(**kwargs); report=service.report(outcome.run_id)
        assert outcome.status==expected and outcome.strategy_lifecycle==state
        assert report['provenance']['worktree']=='CLEAN' and report['provenance']['executable_revision']==revision
        assert report['product_assessment']['sealed_dataset_verification']['scope']=='FULL_LOGICAL_VERIFIED'
        assert service.run(**kwargs)==outcome
        save(target/'research-report.json',report); save(target/'trial-ledger.json',service.ledger.events('fixture-family'))
    with open_sqlite_platform(target/'registry.sqlite',research_namespace='FIXTURE') as e6:
        save(target/'owner-product-record.json',asdict(e6.product_assessment(outcome.run_id)))
    summaries.append(dict(scenario=kind,status=expected,lifecycle=state,candidate_gate=report['candidate_gate']['status'],
        executable_revision=revision,closed_sealed_trades=report['product_assessment']['sealed_backtest']['total_trades'],
        trial_count=report['product_assessment']['trial_count'],replays=report['robustness']['budget']['replays'],
        phase_attempts=len(report['attempts']),report_sha256=hashlib.sha256((target/'research-report.json').read_bytes()).hexdigest()))
save(destination/'summary.json',summaries)
case=OperationalLifecycleTests('runTest'); target=destination/'lifecycle-mechanics'; target.mkdir()
api,research,case.run_id,identity,boundary,auth,clock,release,envelope=case.fixture(target)
matrix=[]; illegal=[]; audits=[]
with research:
    assert research.report(case.run_id)['provenance']['worktree']=='CLEAN'
    for source in CANONICAL_LIFECYCLE_STATES:
        with case.platform(target,research,case.run_id,boundary,source) as e6:
            case.build(e6,identity,source,auth)
            for new in CANONICAL_LIFECYCLE_STATES:
                if (source,new) in CANONICAL_EDGES: continue
                current=e6.get_strategy(identity)
                transition=LifecycleTransitionRecord('illegal-'+source+'-'+new,identity,source,new,clock[0].isoformat(),
                    'fixture',('FORBIDDEN',),None,current.registry_revision,current.registry_revision+1)
                try: e6._store.append_transition(transition)
                except InvalidTransition: illegal.append(dict(source=source,target=new,status='REJECTED_AS_REQUIRED'))
                else: raise AssertionError('Illegal canonical edge accepted')
    for index,(source,new) in enumerate(sorted(CANONICAL_EDGES)):
        if (source,new)==('BACKTESTING','REJECTED'):
            matrix.append(dict(source=source,target=new,status='PASS',evidence_ref='quantitative-negative/research-report.json')); continue
        name='edge-'+str(index)
        with case.platform(target,research,case.run_id,boundary,name) as e6:
            case.build(e6,identity,source,auth); before=e6.get_strategy(identity)
            after=case.apply(e6,identity,new,auth)
            assert after.current_lifecycle_state==new and after.registry_revision==before.registry_revision+1
            assert after.definition_json==before.definition_json
        with closing(sqlite3.connect(target/(name+'.sqlite'))) as db:
            db.row_factory=sqlite3.Row
            rows=[dict(row) for row in db.execute('SELECT * FROM lifecycle_transitions ORDER BY resulting_registry_revision')]
            approvals=[dict(row) for row in db.execute('SELECT * FROM human_approvals')]
            gates=[dict(row) for row in db.execute('SELECT * FROM lifecycle_owner_evidence')]
            receipts=[dict(row) for row in db.execute('SELECT * FROM lifecycle_command_receipts')]
        audits.append(dict(scenario=name,transitions=rows,approvals=approvals,owner_evidence=gates,command_receipts=receipts))
        matrix.append(dict(source=source,target=new,status='PASS',scope='FIXTURE_SIMULATED_MECHANICS',audit_ref=name))
assert len(matrix)==19 and len(illegal)==81
save(target/'edge-matrix.json',dict(executable_revision=revision,namespace='FIXTURE',
    operational_runtime_started=False,provider_requests=0,real_forward='NOT_RUN',legal=matrix,illegal=illegal))
save(target/'owner-audits.json',audits); save(target/'selected-envelope.json',envelope)
print(json.dumps(dict(scenarios=summaries,legal_edges=len(matrix),illegal_pairs=len(illegal)),indent=2))
