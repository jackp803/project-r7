from pathlib import Path
import json,sys
from run_compact_trade_corpus_drained import bounded

art=Path(__file__).parent;mode=sys.argv[1]
if mode not in ('before','after'):raise ValueError('Fixed paired input required')
source=art/'compact-ninety-trade-corpus-drained-20261024'/('closed90-protected-before-steady.sqlite' if mode=='before' else 'controlled-source-snapshot.sqlite')
output=art/('compact-facts-D-closed90-'+mode+'-20261024')
code,raw,wall=bounded([sys.executable,str(art/'compact_fact_prototype.py'),'--source',str(source),'--output',str(output),'--candidate','D'])
sys.stdout.buffer.write(raw);print(json.dumps(dict(controller_status='REAPED',exit_code=code,wall_seconds=wall)),flush=True)
raise SystemExit(code)
