"""Fresh E6 instance/fresh readonly connection; OS file cache uncontrolled."""
from contextlib import closing
from pathlib import Path
import hashlib,json,sqlite3,time
from storage.paper_process import PaperProcessJournal
from tools.verify_public_archive_volume import peak_memory

art=Path(__file__).parent;source=art/'compact-ninety-trade-corpus-drained-20261024/controlled-source-snapshot.sqlite'
output=art/'compact-fresh-current-recovery-20261024'
if output.exists():raise RuntimeError('Fresh diagnostic required')
output.mkdir();before=hashlib.sha256(source.read_bytes()).hexdigest();started=time.perf_counter();cpu=time.process_time()
with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,isolation_level=None)) as db:
    db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('PRAGMA foreign_keys=ON')
    run,=db.execute('SELECT run_id FROM paper_process_runs').fetchone();journal=PaperProcessJournal(db)
    current=journal.recover_current(run);wall=time.perf_counter()-started;used_cpu=time.process_time()-cpu
    if current.state['runtime']['position']['lifecycle_state']!='OPEN_PROTECTED' or len(current.state['runtime']['closed_trades'])!=90:raise RuntimeError('Actual protected head and90closed required')
    value=dict(status='FRESH_READONLY_E6_CURRENT_FACTS_DIAGNOSTIC_NOT_FULL_OWNER_RECOVERY_OR_NATIVE',wall_seconds=wall,cpu_seconds=used_cpu,
        profile='ORIGINAL_ENCODED_CHECKPOINT_NOT_COMPACT_PRODUCT_INTEGRATION',sqlite_connection='FRESH',python_decoded_cache='EMPTY',os_file_cache='UNCONTROLLED',
        history_verification=current.history_verification,history_permission=journal.history_audit_ready(run),
        current_revision=current.revision,current_state_bytes=len(current.state_json.encode()),closed_trades=90,
        snapshot_write_count=db.total_changes,source_sha256='sha256:'+before,actual_provider_requests=0,elapsed_credit='NONE',native='NOT_QUALIFIED',**peak_memory())
if before!=hashlib.sha256(source.read_bytes()).hexdigest():raise RuntimeError('Readonly source changed')
(output/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value),flush=True)
