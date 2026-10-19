"""Actual native07 at owning depth before a full run; no full PASS transfer."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,re,sys,uuid
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE.parent)]
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile,NATIVE_ASSERTIONS
from application.paper.qualification import artifact_bytes
from local_windows_qualification_awake import awake_request
from run_current_checkpoint import command
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
revision=sys.argv[1]
if not re.fullmatch('[0-9a-f]{40}',revision) or os.name!='nt':raise ValueError('Exact native Windows revision required')
revision_fact(ROOT,revision,True)
package=BASE/('build-'+revision[:7])/'dist/R7';facts=verify_distribution(package);target=current_target();profile=fixed_profile(target)
if facts['executable_revision']!=revision:raise ValueError('Exact executable revision differs')
_guard(ROOT,revision,package,facts,profile)
stage=BASE/('native07-depth-'+revision[:7]+'-first');create_private_directory(stage)
data=PROJECT/'artifacts'/('q-'+revision[:7]+'-depth');create_private_directory(data)
worker=data/'worker-logs';create_private_directory(worker)
execution=worker/('pqr-'+uuid.uuid4().hex);create_private_directory(execution)
output=execution/'PQR-07-native-artifacts'
assert len(str(output/'publication'))==len(str(PROJECT/'artifacts'/('q-'+revision[:7]+'-first')/'worker-logs'/('pqr-'+'0'*32)/'PQR-07-native-artifacts/publication'))
report=dict(revision=revision,passed=False,started_at=datetime.now(timezone.utc).isoformat(),facts=facts,
    helper_hash=sha(Path(__file__).read_bytes()),scope='ACTUAL_SCOPED_NATIVE07_AT_OWNING_DEPTH_ONLY',
    publication_root_chars=len(str(output/'publication')),additional_public_requests=0,cumulative_public_requests=8,
    private_requests=0,credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED')
with awake_request() as awake:
    try:
        command_result=command([sys.executable,'-X','utf8',ROOT/'tools/verify_paper_product.py','--package-root',package,
            '--output',output,'--group','PQR-07'],stage,'native07-owning-depth',1200)
        if command_result!={'group':'PQR-07','passed':True,'target':target,'provider_requests':0}:
            raise ValueError('Native command result differs')
        result=json.loads(artifact_bytes(output,'pqr-result.json'))
        captured={}
        for row in result['artifacts']:
            if row['ref'] in captured:raise ValueError('Duplicate native artifact')
            raw=artifact_bytes(output,row['ref'])
            if sha(raw)!=row['hash']:raise ValueError('Native artifact changed')
            captured[row['ref']]=raw
        observation_raw=captured['native-observations.json'];observation=json.loads(observation_raw)
        expected_assertions=[dict(assertion_id=name,status='PASS',evidence_ref='native-observations.json',
            evidence_hash=sha(observation_raw)) for name in NATIVE_ASSERTIONS['PQR-07']]
        if result['assertions']!=expected_assertions:raise ValueError('Mandatory native assertion inventory differs')
        if (observation['passed'] is not True or observation['group']!='PQR-07' or observation['target']!=target
                or observation['identity']!=facts or not observation['observations']
                or any(row.get('passed') is not True for row in observation['observations'])):
            raise ValueError('Actual native07 incomplete or subject differs')
        report.update(passed=True,artifact_root_ref=output.relative_to(PROJECT).as_posix(),
            native_result=result,native_observations_hash=sha(observation_raw))
    except BaseException as error:
        report.update(error_type=type(error).__name__)
    finally:
        _guard(ROOT,revision,package,facts,profile)
        if sha(Path(__file__).read_bytes())!=report['helper_hash']:raise ValueError('Preflight helper changed')
        report.update(source_unchanged=True,package_unchanged=True,finished_at=datetime.now(timezone.utc).isoformat(),awake=awake)
write_private_new(stage/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in report.items() if k not in ('native_result','awake')}))
raise SystemExit(0 if report['passed'] else 2)
