from pathlib import Path
import subprocess,sys
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
argv=[sys.executable,str(Path(__file__).with_name('produce_compact_trade_corpus_90_diag2.py'))]
owned=spawn_owned(argv,cwd=Path.cwd(),limits=ResourceLimits(300),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
try:
    code=owned.wait(timeout=302);raw=owned.process.stdout.read(65537)
    if len(raw)>65536:raise RuntimeError('Bounded diagnostic output required')
    sys.stdout.buffer.write(raw)
    if not owned.termination_report.reaped:raise RuntimeError('Diagnostic reap required')
    raise SystemExit(code)
finally:
    report=terminate_owned(owned,deadline_seconds=3);owned.process.stdout.close()
    if not report.reaped:raise RuntimeError('Diagnostic cleanup failed')
