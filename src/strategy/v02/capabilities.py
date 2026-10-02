"""Executable validation inventory; availability never substitutes for evidence.

S03 has grammar implementations. Indicator execution and end-to-end runtime
qualification are separate work packages; all their admission flags fail closed.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from indicators.v02.common import ARITHMETIC_PROFILE
from strategy.runtime import RUNTIME_FAMILY, StrategyValidationError
from strategy.v02.ast import OPERATORS, OUTPUTS, PRIMITIVE_VERSIONS


def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _revision():
    root=Path(__file__).resolve().parent
    source_root=root.parents[1]
    digest=hashlib.sha256()
    files=list(source_root.rglob('*.py'))
    for path in sorted(files,key=lambda path:path.relative_to(source_root).as_posix()):
        relative=path.relative_to(source_root).as_posix()
        raw=path.read_bytes().replace(b'\r\n',b'\n')
        digest.update(relative.encode('ascii')+b'\x00'+raw+b'\x00')
    return 'sha256:'+digest.hexdigest()


@dataclass(frozen=True)
class CapabilitySnapshot:
    canonical_json: str
    snapshot_hash: str

    def as_dict(self):
        return json.loads(self.canonical_json)


@dataclass(frozen=True)
class CapabilityGap:
    capability_id: str
    requested_version: str | None
    available_version: str | None
    source_location: str
    reason: str
    reevaluation_conditions: tuple[str,...]


@dataclass(frozen=True)
class CompatibilityReport:
    status: str
    snapshot_hash: str
    gaps: tuple[CapabilityGap,...]
    execution_evidence: str='NOT_RUN'


def build_capability_snapshot() -> CapabilitySnapshot:
    revision=_revision()
    entries=[]
    for name,version in sorted(PRIMITIVE_VERSIONS.items()):
        parameters=({'fast':{'minimum':1,'maximum':10000},'slow':{'minimum':1,'maximum':10000},
                     'signal_window':{'minimum':1,'maximum':10000}} if name=='MACD' else
                    {'window':{'minimum':1,'maximum':10000}})
        if name=='BOLLINGER': parameters['k']={'type':'finite-decimal-string','exclusive_minimum':'0'}
        if name=='DONCHIAN': parameters['lag_bars']={'minimum':0,'maximum':10000,'default':1}
        entries.append({
            'capability_id':'indicator:'+name,'semantic_version':version,'parameters':parameters,
            'output_type':'Decimal','outputs':list(OUTPUTS[name]),
            'units':'dimensionless' if name in {'RSI','ADX'} else 'source' if name in {'SMA','EMA','MACD','BOLLINGER'} else 'price',
            'supported_timeframes':['1m','15m','1h','4h'],
            'minimum_history':{'SMA':'n','EMA':'n','RSI':'n+1','ATR':'n','ADX':'DI:n+1; ADX:2*n',
                               'MACD':'line:slow; signal/histogram:slow+signal_window-1',
                               'BOLLINGER':'n','DONCHIAN':'n+lag_bars'}[name],
            'missing_data_behavior':'NO_TRADE/INSUFFICIENT_HISTORY; no forward fill',
            'arithmetic_profile':ARITHMETIC_PROFILE,'implementation_revision':revision,
            'validator_available':True,'IMPLEMENTED':False,'VERIFIED_REFERENCE':False,
            'PAPER_AVAILABLE':False,'LIVE_PROVIDER_AVAILABLE':False,'verification_refs':[],
        })
    entries.append({'capability_id':'grammar:0.2','semantic_version':'r7-closed-bar-v0.2',
                    'operators':sorted(OPERATORS),'parameters':{},'output_type':'validated AST',
                    'units':'statically checked','supported_timeframes':['1m','15m','1h','4h'],
                    'minimum_history':'derived per feature','missing_data_behavior':'reject malformed input',
                    'arithmetic_profile':ARITHMETIC_PROFILE,'implementation_revision':revision,
                    'validator_available':True,'IMPLEMENTED':True,'VERIFIED_REFERENCE':False,
                    'PAPER_AVAILABLE':False,'LIVE_PROVIDER_AVAILABLE':False,'verification_refs':[]})
    document={'schema_version':'r7-capabilities-v0.2','runtime_family':RUNTIME_FAMILY,
              'runtime_profiles':['0.1.0','0.2.0'],
              'implementation_revision':revision,'capabilities':entries,
              'limits':{'ast_depth':32,'ast_nodes':4096,'features':128,'strategy_bytes':262144,
                        'window':10000,'lag':10000,'required_timeframes':4},
              'runtime_0_2_execution':'NOT_IMPLEMENTED','platform_verification':{
                  'Windows11':'NOT_RUN','Ubuntu24.04':'NOT_RUN','Ubuntu26.04':'NOT_RUN'}}
    raw=_canonical(document)
    return CapabilitySnapshot(raw,'sha256:'+hashlib.sha256(raw.encode('utf-8')).hexdigest())


def check_compatibility(definition,snapshot,*,required_snapshot_hash=None) -> CompatibilityReport:
    if not isinstance(snapshot,CapabilitySnapshot):
        raise TypeError('CapabilitySnapshot required')
    gaps=[]
    def gap(capability,requested,available,path,reason):
        gaps.append(CapabilityGap(capability,requested,available,path,reason,
                                  ('Require a new immutable submission bound to the current exact snapshot',
                                   'Execute fresh compatibility and research against the corrected runtime')))
    if required_snapshot_hash is not None and required_snapshot_hash!=snapshot.snapshot_hash:
        gap('snapshot',required_snapshot_hash,snapshot.snapshot_hash,'/capability_snapshot_hash','CAPABILITY_SNAPSHOT_MISMATCH')
        return CompatibilityReport('BLOCKED',snapshot.snapshot_hash,tuple(gaps))
    document=snapshot.as_dict()
    available={row['capability_id']:row for row in document['capabilities']}
    stack=[(definition,'',0)]
    count=0
    while stack:
        value,path,depth=stack.pop()
        count+=1
        if count>16384 or depth>128:
            gap('grammar','0.2','0.2',path,'COMPLEXITY_LIMIT')
            break
        if isinstance(value,dict):
            if value.get('kind')=='indicator':
                name=value.get('name')
                row=available.get('indicator:'+name) if isinstance(name,str) else None
                requested=value.get('semantic_version')
                if row is None: gap('indicator:'+str(name),requested,None,path,'UNSUPPORTED_FEATURE')
                elif requested!=row['semantic_version']:
                    gap(row['capability_id'],requested,row['semantic_version'],path,'UNSUPPORTED_VERSION')
                elif not row['IMPLEMENTED']:
                    gap(row['capability_id'],requested,row['semantic_version'],path,'NOT_IMPLEMENTED')
            for key,child in value.items():
                token=str(key).replace('~','~0').replace('/','~1')
                stack.append((child,path+'/'+token,depth+1))
        elif isinstance(value,list):
            stack.extend((child,path+'/'+str(i),depth+1) for i,child in enumerate(value))
    from strategy.v02.parser import parse_v02
    try:
        parse_v02(definition)
    except StrategyValidationError as error:
        if not gaps: gap('grammar','0.2','0.2','/',error.code)
    if not gaps:
        gap('runtime:0.2.0','0.2.0','0.2.0','/runtime_compatibility','EXECUTION_NOT_QUALIFIED')
    return CompatibilityReport('BLOCKED',snapshot.snapshot_hash,tuple(gaps))
