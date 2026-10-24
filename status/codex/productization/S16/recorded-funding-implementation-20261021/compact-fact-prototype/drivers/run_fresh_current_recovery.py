from pathlib import Path
import sys,json
from run_compact_trade_corpus_drained import bounded
code,raw,wall=bounded([sys.executable,str(Path(__file__).with_name('measure_fresh_current_recovery.py'))])
sys.stdout.buffer.write(raw);print(json.dumps(dict(controller_status='REAPED',exit_code=code,wall_seconds=wall)),flush=True)
raise SystemExit(code)
