"""Apply exactly reviewed UI01 files AFTER aa2d evidence is committed cleanly."""
from pathlib import Path
import ast,hashlib,json,re,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.supervision import _local_path
BASELINE='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
MANIFEST='76f450c9fbb7f02537aafdcdde60fd5eec4d542c30e6aedec3b48aeed829f411'
EXPECTED={
 'src/application/control_api/dto.py','src/application/control_api/services.py',
 'src/application/control_api/owner_services.py','src/application/research/queue.py',
 'ui/src/App.tsx','ui/qa/control-center.spec.ts','ui/qa/serve_fixture.py',
 'tests/product/test_ui01_observations.py'}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(expected_head):
    if not re.fullmatch('[0-9a-f]{40}',expected_head) or expected_head==BASELINE:
        raise ValueError('Explicit subsequent clean evidence commit required')
    if (git('rev-parse','HEAD')!=expected_head or git('status','--porcelain')
            or git('branch','--show-current')!='codex/r7-productization-master-20261002'):
        raise ValueError('Preserved original clean branch required')
    subprocess.check_call(['git','merge-base','--is-ancestor',BASELINE,expected_head],cwd=ROOT)
    retained=ROOT/'status/codex/productization/S12/current-windows-aa2d00a/disposition.json'
    disposition=json.loads(retained.read_bytes())
    if (disposition['executable_revision']!=BASELINE or disposition['ordinary_windows_paper_software']['status']!='PASS'
            or disposition['ordinary_windows_paper_software']['groups_completed']!=7):
        raise ValueError('Complete baseline evidence must be retained first')
    for name in ('qualify','portable','headless','unattended','ordinary-idle','qualified-backup'):
        checkpoint=json.loads((BASE/(name+'-aa2d00a-first/checkpoint.json')).read_bytes())
        if checkpoint.get('passed') is not True or checkpoint.get('revision')!=BASELINE:
            raise ValueError('All baseline guarded executions must be complete')
    observer=json.loads((BASE/'owning-memory-aa2d00a-first/checkpoint.json').read_bytes())
    if not all(observer.get(key) is True for key in ('owning_passed','tree_reaped','monitor_stopped')):
        raise ValueError('Baseline owned processes and observation must be stopped')
    prepared=BASE/'ui01-projection-unapplied-v1'
    raw=(prepared/'manifest.json').read_bytes()
    if sha(raw)!=MANIFEST:raise ValueError('Reviewed exact UI01 manifest required')
    manifest=json.loads(raw);rows=manifest['records']
    if len(rows)!=8 or {r['ref'] for r in rows}!=EXPECTED:raise ValueError('Exact eight-file change required')
    writes=[]
    for row in rows:
        source=prepared/row['ref'];target=ROOT/row['ref'];_local_path(source);_local_path(target)
        if not target.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Contained source target required')
        data=source.read_bytes()
        if sha(data)!=row['after_sha256']:raise ValueError('Prepared bytes changed')
        previous=row['before_sha256']
        if previous is None:
            if target.exists():raise ValueError('New test must not overwrite existing work')
        elif not target.is_file() or sha(target.read_bytes())!=previous:
            raise ValueError('Current source changed since reviewed baseline')
        if target.suffix=='.py':ast.parse(data.decode('utf-8'))
        writes.append((target,data))
    if git('rev-parse','HEAD')!=expected_head or git('status','--porcelain'):
        raise ValueError('Source moved during read-only preparation')
    output=BASE/'ui01-projection-apply-first';create_private_directory(output)
    write_private_new(output/'before.json',(json.dumps(dict(head=expected_head,baseline=BASELINE,
        manifest_sha256=MANIFEST,files=rows,qualification_credit='NONE;NEW_SOURCE_UNQUALIFIED'),indent=2)+'\n').encode())
    for target,data in writes:
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for row in rows:
        if sha((ROOT/row['ref']).read_bytes())!=row['after_sha256']:raise ValueError('Applied readback differs')
    write_private_new(output/'checkpoint.json',(json.dumps(dict(status='EXACT_REVIEWED_UI01_PATCH_APPLIED',
        original_head=expected_head,files=8,qualification='NEW_SOURCE_UNQUALIFIED',
        next='Actual backend regressions; export API/types; typecheck/unit/build/browser; clean candidate qualification'),indent=2)+'\n').encode())
    print(json.dumps(dict(status='APPLIED',files=8,qualification='NEW_SOURCE_UNQUALIFIED')))
if __name__=='__main__':run(*sys.argv[1:])
