"""Public audit and UNAPPLIED drafts only; no additional qualification credit."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(BASE))
from retain_current_checkpoint import CapturedEvidence
from application.qualification import _sanitize
from application.platform.private_files import create_private_directory,write_private_new
from application.paper.qualification import artifact_bytes
from verify_qualified_backup_checkpoint import backup_output
REVISION='7d821f29837e95e46bcd5fe32f14d536a28c9aa8'
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def utc(value):return datetime.fromisoformat(value.replace('Z','+00:00'))

captured=CapturedEvidence(PROJECT)
queue=captured.document(BASE/'POSTCHECKPOINT_SOURCE_WORK_QUEUE.json')
refs={BASE/row['ref'] for row in queue['drafts']}
refs.update(PROJECT/row['project_ref'] for row in queue['additional_unapplied_drafts'])
refs.update(BASE/name for name in ('POSTCHECKPOINT_SOURCE_WORK_QUEUE.json','refresh_postcheckpoint_work_queue.py',
    'backup-history-retainer-final-review.json','backup-selection-shape-final-review.json',
    'correct_cloud10_draft_mapping.py','cloud10-before-correction-acceptance-cloud-trade-expanded-map.json',
    'cloud10-before-correction-final-acceptance-record-plan.json','cloud10-before-correction-POSTCHECKPOINT_LOCAL_MASTER_CHECKLIST.json',
    'retain_checkpoint_supplement.py','postqualification-power-interval-20261020.json'))
patches=list(BASE.glob('postcheckpoint*.patch'))
if not 1<=len(patches)<=32:raise ValueError('Bounded public source drafts required')
refs.update(patches)
for path in sorted(refs):captured.capture(path)
power=captured.document(BASE/'postqualification-power-interval-20261020.json')
if isinstance(power,dict):power=[power]
stages={name:BASE/(name+'-'+REVISION[:7]+'-first')/'checkpoint.json'
    for name in ('qualify','portable','headless','unattended','ordinary-idle')}
stages['qualified-backup']=backup_output(REVISION,'retry01')/'checkpoint.json'
times={}
for name,path in stages.items():
    row=captured.document(path)
    if row.get('revision')!=REVISION or row.get('passed') is not True:raise ValueError('Actual completed stage required')
    times[name]={key:row[key] for key in ('started_at','finished_at')}
intervals=[]
for event in power:
    start,end=utc(event['SleepTime']),utc(event['WakeTime'])
    overlap=[name for name,value in times.items() if utc(value['started_at'])<end and start<utc(value['finished_at'])]
    intervals.append(dict(sleep_utc=event['SleepTime'],wake_utc=event['WakeTime'],overlapping_completed_stages=overlap))
target=ROOT/'status/codex/productization/S12/current-windows-7d821f2-supplement'
prepared=[];bindings=[]
for number,(path,raw) in enumerate(sorted(captured.bytes.items(),key=lambda pair:pair[0].relative_to(PROJECT).as_posix()),1):
    ref='artifacts/a'+str(number).zfill(4)+path.suffix
    safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
    if path.suffix=='.log':safe=b'\n'.join(line.rstrip() for line in safe.split(b'\n'))
    prepared.append((ref,safe));bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),
        original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe),normalization='SANITIZED_LF;LOG_TRAILING_SPACE_REMOVAL_IF_LOG'))
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REVISION,
    scope='PUBLIC_AUDIT_AND_UNAPPLIED_SOURCE_DRAFTS_ONLY',qualification_credit='NONE',
    draft_execution='NONE',draft_acceptance='NOT_RUN',recorded_at=datetime.now(timezone.utc).isoformat(),
    recorded_power_intervals=intervals,completed_stage_times=times,
    power_scope='RECORDED_INTERVAL_COMPARISON_ONLY;NOT_A_GLOBAL_HOST_WAKE_GUARANTEE',
    backup_first_native_error_site='NOT_RECORDED;SOURCE_SHAPE_REPLAY_IS_SEPARATE',
    additional_public_requests=0,cumulative_public_requests=8,private_requests=0,credentials='NONE',
    provider_mutation=0,capital='NONE',github_compute='NOT_USED',artifacts=bindings)
create_private_directory(target);create_private_directory(target/'artifacts')
for ref,raw in prepared:write_private_new(target/ref,raw)
for ref,raw in prepared:
    if artifact_bytes(target,ref)!=raw:raise ValueError('Supplement readback differs')
raw=(json.dumps(disposition,indent=2)+'\n').encode();write_private_new(target/'disposition.json',raw)
if artifact_bytes(target,'disposition.json')!=raw:raise ValueError('Supplement disposition differs')
print(json.dumps(dict(retained_files=len(bindings),power_intervals=intervals,qualification_credit='NONE')))
