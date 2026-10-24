"""Bounded diagnostic controller drains owned stdout BEFORE waiting for exit."""
from pathlib import Path
import json,os,subprocess,sys,time
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned

def bounded(argv):
    owned=spawn_owned(argv,cwd=Path.cwd(),limits=ResourceLimits(300),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    chunks=[];size=0;started=time.monotonic()
    try:
        fd=owned.process.stdout.fileno();os.set_blocking(fd,False)
        while True:
            if time.monotonic()-started>=300:raise RuntimeError('Diagnostic deadline exceeded')
            try:chunk=os.read(fd,min(65536,65537-size))
            except BlockingIOError:time.sleep(.02);continue
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
            if size>65536:raise RuntimeError('Bounded diagnostic output exceeded')
        code=owned.wait(timeout=3)
        if not owned.termination_report.reaped:raise RuntimeError('Actual owned process reap required')
        return code,b''.join(chunks),time.monotonic()-started
    finally:
        report=terminate_owned(owned,deadline_seconds=3);owned.process.stdout.close()
        if not report.reaped:raise RuntimeError('Owned diagnostic cleanup failed')

if __name__=='__main__':
    if sys.argv[1:] == ['--self-test']:
        code,raw,wall=bounded([sys.executable,'-c','import sys;sys.stdout.write("x"*16384);sys.stdout.flush()'])
        if code!=0 or raw!=b'x'*16384:raise RuntimeError('Pipe capacity regression')
        print(json.dumps(dict(status='OWNED_PIPE_DRAIN_REAP_PASS',bytes=len(raw),wall_seconds=wall)))
    elif not sys.argv[1:]:
        code,raw,wall=bounded([sys.executable,str(Path(__file__).with_name('produce_compact_trade_corpus_90_drained.py'))])
        sys.stdout.buffer.write(raw);print(json.dumps(dict(controller_status='REAPED',exit_code=code,wall_seconds=wall)),flush=True)
        raise SystemExit(code)
    else:raise ValueError('Fixed diagnostic only')
