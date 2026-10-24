from pathlib import Path
import subprocess,sys
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits

art=Path(__file__).parent;candidate=sys.argv[1]
if candidate not in ('B','C','D'):raise ValueError('Fixed finite candidate required')
suffix=sys.argv[2] if len(sys.argv)>2 else 'v1'
if suffix not in ('v1','v2','v3'):raise ValueError('Bounded fresh attempt required')
output=art/('compact-facts-prototype-'+candidate+'-'+suffix+'-20261024')
argv=[sys.executable,str(art/'compact_fact_prototype.py'),'--source',str(art/'e6-3600second-growth-v2-20261024/controlled-source-snapshot.sqlite'),
    '--output',str(output),'--candidate',candidate]
owned=spawn_owned(argv,cwd=Path.cwd(),limits=ResourceLimits(300),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
try:
    code=owned.wait(timeout=302);raw=owned.process.stdout.read(65537)
    if len(raw)>65536:raise ValueError('Bounded prototype output required')
    sys.stdout.buffer.write(raw)
    if not owned.termination_report.reaped:raise RuntimeError('Prototype process reap required')
    raise SystemExit(code)
finally:
    report=terminate_owned(owned,deadline_seconds=3);owned.process.stdout.close()
    if not report.reaped:raise RuntimeError('Prototype owned process cleanup failed')
