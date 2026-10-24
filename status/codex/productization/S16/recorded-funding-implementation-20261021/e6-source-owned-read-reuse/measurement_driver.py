"""Fresh complete readonly audit of one preserved actual source snapshot."""
from pathlib import Path
import hashlib,json,time
from storage.paper_history_audit import audit_paper_history_snapshot
from tools.verify_public_archive_volume import peak_memory

art=Path(__file__).parent;root=Path.cwd();source=art/'e6-256bar-recovery-20261024/controlled-source-snapshot.sqlite'
output=art/'e6-cold-audit-read-reuse-20261024'
if output.exists():raise RuntimeError('Fresh diagnostic path required')
output.mkdir();before='sha256:'+hashlib.sha256(source.read_bytes()).hexdigest()
original=json.loads((art/'e6-256bar-recovery-20261024/result.json').read_text())
# Resolve the actual captured single run, not an asserted result or new owner.
import sqlite3
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db:
    rows=db.execute('SELECT run_id FROM paper_process_runs LIMIT 2').fetchall()
if len(rows)!=1:raise RuntimeError('Actual single-run source required')
run_id=rows[0][0];phases=[]
def progress(value):
    if not phases or phases[-1]['phase']!=value.phase:
        phases.append(dict(phase=value.phase,verified_rows=value.verified_rows,wall_seconds=time.perf_counter()-started))
names=('src/storage/paper_process.py','src/storage/paper_state_codec.py','src/storage/paper_history_audit.py')
hashes={name:'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
started=time.perf_counter();cpu=time.process_time()
result=audit_paper_history_snapshot(source,run_id,on_progress=progress)
wall=time.perf_counter()-started;cpu=time.process_time()-cpu
after='sha256:'+hashlib.sha256(source.read_bytes()).hexdigest()
if after!=before:raise RuntimeError('Readonly diagnostic changed actual source')
if hashes!={name:'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}:raise RuntimeError('Source changed during audit')
value=dict(status='COMPLETE_COLD_SOURCE_SNAPSHOT_AUDIT_DIAGNOSTIC_NOT_RUNTIME_AUTHORITY_OR30DAY_PASS',
    snapshot_sha256=before,wall_seconds=wall,cpu_seconds=cpu,phases=phases,result=result,
    input_operations=original['inventory']['paper_process_operations']['rows'],reader_source_hashes=hashes,
    actual_provider_requests=0,elapsed_credit='NONE',native='NOT_QUALIFIED',**peak_memory())
(output/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(value),flush=True)
