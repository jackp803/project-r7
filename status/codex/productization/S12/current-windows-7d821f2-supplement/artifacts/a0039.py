"""Refresh only the unapplied outside-Git draft index; grant no execution credit."""
from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent;project=base.parents[1]
path=base/'POSTCHECKPOINT_SOURCE_WORK_QUEUE.json'
value=json.loads(path.read_bytes())
refs={row['ref']:row for row in value['drafts']}
for name in ('authoring-test-drafts-final-review.json','postcheckpoint-cloud05-joined-e6-unapplied.patch',
    'postcheckpoint-trade02-joined-authority-unapplied.patch','postcheckpoint-joined-evidence-test-design.json',
    'cloud10-authoritative-clause-clarification.json','cloud10-map-correction-execution.json',
    'h16-genuine-close-owner-plan.json'):
    refs.setdefault(name,dict(ref=name))
for name,row in refs.items():
    row['sha256']='sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest()
value['drafts']=list(refs.values())
value['additional_unapplied_drafts']=[]
for ref in ('artifacts/k05-source-test-drafts-20261020/K05-test-design.json',
    'artifacts/k05-source-test-drafts-20261020/test_k05_readonly_history.py.unapplied',
    'artifacts/k05-source-test-drafts-20261020/test_k05_feedback_privacy.py.unapplied',
    'unapplied-source-drafts/fake-provider-funding-20261020/api-plan.json',
    'unapplied-source-drafts/fake-provider-funding-20261020/test_fixture_allocated_ledger_draft.py'):
    raw=(project/ref).read_bytes()
    value['additional_unapplied_drafts'].append(dict(project_ref=ref,sha256='sha256:'+hashlib.sha256(raw).hexdigest(),
        execution='NONE',acceptance_credit='NONE'))
path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(status=value['status'],drafts=len(value['drafts']),additional=len(value['additional_unapplied_drafts']))))
