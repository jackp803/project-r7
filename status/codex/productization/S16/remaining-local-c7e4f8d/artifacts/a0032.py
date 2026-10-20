"""Engineering examples via actual offline authoring; no research/Paper credit."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,re,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.cloud.authoring import emit_package,AuthoringError
from application.cloud.manifest import canonical_bytes
from application.platform.private_files import create_private_directory,write_private_new
from strategy import compute_content_hash

examples=ROOT/'docs/strategy/authoring-v0.2/examples'
attempt=sys.argv[1]
if not re.fullmatch('[0-9]{2}',attempt):raise ValueError('Explicit bounded fresh attempt required')
stage=BASE/('required-authoring-examples-'+attempt);create_private_directory(stage)
base_revision='0c535ac0045a371d92e2bdd8f7d978d55131fd4d'
base_raw=subprocess.run(['git','show',base_revision+':docs/strategy/authoring-v0.2/examples/four-hour/strategy.json'],
    cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout
base=json.loads(base_raw)
def field(timeframe):return dict(kind='field',field='close',timeframe=timeframe)
def feature(name):return dict(kind='feature',name=name)
def op(name,*args):return dict(kind='operator',name=name,args=list(args))
def candle(name,version,output='value',**parameters):
    return dict(kind='indicator',name=name,semantic_version=version,timeframe='4h',output=output,parameters=parameters)

four=deepcopy(base);four.update(strategy_version='0.2.1',name='Engineering BTC4H EMA ADX ATR example',created_at='2026-10-20T00:00:00Z')
four['rules']['features'].update(adx=candle('ADX','r7-adx-wilder-v1',window=2),atr=candle('ATR','r7-atr-wilder-v1',window=2))
threshold=dict(kind='decimal',value='20')
four['rules']['long']=op('AND',op('GT',field('4h'),feature('trend')),op('GT',feature('adx'),threshold))
four['rules']['short']=op('AND',op('LT',field('4h'),feature('trend')),op('GT',feature('adx'),threshold))
four['rules']['exit_policy']['stop']=dict(kind='atr_multiple',feature='atr',multiple='2')

multi=deepcopy(base);multi.update(strategy_id='authoring-example-multitimeframe',strategy_version='0.2.1',
    name='Engineering 4H direction 15m Donchian example',created_at='2026-10-20T00:00:00Z',required_timeframes=['15m','4h'])
multi['rules']['evaluation_timeframe']='15m'
for name,output in (('channel_upper','upper'),('channel_lower','lower')):
    multi['rules']['features'][name]=dict(kind='indicator',name='DONCHIAN',semantic_version='r7-donchian-v1',
        timeframe='15m',output=output,parameters=dict(window=2,lag_bars=1))
multi['rules']['long']=op('AND',op('GT',field('4h'),feature('trend')),op('GT',field('15m'),feature('channel_upper')))
multi['rules']['short']=op('AND',op('LT',field('4h'),feature('trend')),op('LT',field('15m'),feature('channel_lower')))

results={};prepared={}
for name,definition in (('four-hour',four),('multitimeframe',multi)):
    results[name]=emit_package(definition,stage/name,submission_id='authoring-example-'+name,
        created_at='2026-10-20T00:00:00Z',created_by='offline engineering example',
        research_hypothesis='Engineering pipeline example only; not GPT research or profitability evidence')
    for filename in ('strategy.json','manifest.json'):prepared[examples/name/filename]=(stage/name/filename).read_bytes()

unsupported=deepcopy(base);unsupported.update(strategy_id='authoring-example-unsupported-feature',strategy_version='0.2.1',
    name='Intentionally unsupported engineering input',created_at='2026-10-20T00:00:00Z')
unsupported['rules']['features']['trend']['name']='UNAVAILABLE_FEATURE'
unsupported['content_hash']=compute_content_hash(unsupported)
try:emit_package(unsupported,stage/'must-not-exist',submission_id='authoring-example-unsupported-feature')
except AuthoringError as error:
    if error.code!='CAPABILITY_GAP':raise
    receipt=dict(code=error.code,gaps=list(error.gaps))
else:raise ValueError('Actual unsupported-feature rejection required')
if (stage/'must-not-exist').exists():raise ValueError('Rejected authoring created a package')
prepared[examples/'unsupported-feature/strategy.json']=canonical_bytes(unsupported)
prepared[examples/'unsupported-feature/gap_receipt.json']=canonical_bytes(receipt)
for path,raw in prepared.items():
    if not path.parent.exists():create_private_directory(path.parent)
    path.write_bytes(raw)
report=dict(scope='ACTUAL_OFFLINE_ENGINEERING_EXAMPLE_AUTHORING_ONLY',version='0.2.1',
    execution_evidence='NOT_RUN',research='NOT_RUN',paper='NOT_RUN',financial_authority='NONE',
    base_revision=base_revision,base_byte_hash='sha256:'+hashlib.sha256(base_raw).hexdigest(),
    helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    old_four_hour_content_hash=base['content_hash'],actual_authoring=results,actual_rejection=receipt,
    files=[dict(ref=p.relative_to(ROOT).as_posix(),sha256='sha256:'+hashlib.sha256(raw).hexdigest()) for p,raw in prepared.items()])
write_private_new(stage/'execution.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(dict(examples=list(results),actual_rejection=receipt['code'],execution_evidence='NOT_RUN')))
