"""Additive allowlisted history export. No trading client, permission or effects.

Public construction consumes only the protected historical read port. The
private snapshot/projector also supports explicitly labeled Paper owner source
fixtures for consumer/privacy tests; these do not prove a dispatch lifecycle.
"""
from dataclasses import asdict,dataclass,fields
import html,json,re

from application.cloud.feedback import FeedbackError,_decimal,_exact
from application.cloud.manifest import HASH,byte_hash,canonical_bytes,load_json,safe_component,utc
from application.cloud.protocol import ArtifactBundle
from storage.runtime_models import PaperRuntimeRecovery,StoredCanonicalObject
from storage._runtime_validation import canonical_payload

SCHEMA='r7-trading-summary-feedback-v0.3'
TOP={'schema_version','namespace','strategy','provenance','binding','references','closed_at','availability',
    'sample_count','funding','performance_policy','performance','actual_live','financial_authority','uncertainty'}
AMOUNTS=('gross_pnl','net_pnl','total_fees','funding_cost')
UNCERTAINTY=[
    'Historical canonical records are not current trading permission or a guarantee of future performance.',
    'Paper and fake-provider source fixtures do not establish actual LIVE performance.',
    'One closed trade is not an independent research or forward qualification sample.',
]
PAPER_BINDING=('implementation_hash','config_hash','risk_policy_hash','paper_policy_hash')
DISPATCH_BINDING=('implementation_hash','config_hash','risk_policy_hash','build_hash','capability_hash',
    'provider_profile_hash','executable_revision','config_generation','risk_generation','runtime_generation')
KINDS={('FIXTURE','PAPER_OWNER_SOURCE_FIXTURE','SIMULATED_MECHANICS'),
    ('FIXTURE','FAKE_PROVIDER_VERIFICATION','SIMULATED_MECHANICS'),
    ('LOCAL_RESEARCH','HISTORICAL_TRADING_OWNER','ACTUAL_OWNER')}


def _known_provenance(namespace,kind,execution):
    return all(isinstance(value,str) for value in (namespace,kind,execution)) and (namespace,kind,execution) in KINDS


def _hash(value):
    if not isinstance(value,str) or not HASH.fullmatch(value):raise FeedbackError('TRADING_FEEDBACK_HASH_INVALID')


def _count(value):
    if type(value) is not int or not 0<=value<=10000000:raise FeedbackError('TRADING_FEEDBACK_COUNT_INVALID')


def _amounts(value):
    _exact(value,AMOUNTS)
    for number in value.values():
        if number is None:raise FeedbackError('TRADING_FEEDBACK_EXACT_AVAILABLE_AMOUNT_REQUIRED')
        _decimal(number)


def validate_trading_feedback(value):
    _exact(value,TOP)
    if value['schema_version']!=SCHEMA:raise FeedbackError('TRADING_FEEDBACK_SCHEMA_INVALID')
    _exact(value['strategy'],('strategy_id','strategy_version','content_hash'))
    for key in ('strategy_id','strategy_version'):safe_component(value['strategy'][key])
    _hash(value['strategy']['content_hash'])
    p=value['provenance'];_exact(p,('kind','execution'))
    if not _known_provenance(value['namespace'],p['kind'],p['execution']):raise FeedbackError('TRADING_FEEDBACK_PROVENANCE_INVALID')
    paper=p['kind']=='PAPER_OWNER_SOURCE_FIXTURE'
    _exact(value['binding'],PAPER_BINDING if paper else DISPATCH_BINDING)
    for key,number in value['binding'].items():
        if key=='executable_revision':
            if not isinstance(number,str) or not re.fullmatch('[0-9a-f]{40}',number):raise FeedbackError('TRADING_FEEDBACK_REVISION_INVALID')
        elif key.endswith('_generation'):
            if type(number) is not int or not 1<=number<=2147483647:raise FeedbackError('TRADING_FEEDBACK_GENERATION_INVALID')
        else:_hash(number)
    _exact(value['references'],('run_hash','trade_plan_hash','position_hash','trade_result_hash','original_binding_hash'))
    for key,number in value['references'].items():
        if number is None and key in ('position_hash','trade_result_hash'):continue
        _hash(number)
    if value['closed_at'] is not None:utc(value['closed_at'])
    if value['availability'] not in ('AVAILABLE','UNAVAILABLE'):raise FeedbackError('TRADING_FEEDBACK_AVAILABILITY_INVALID')
    _count(value['sample_count'])
    if value['sample_count']!=(1 if value['availability']=='AVAILABLE' else 0):raise FeedbackError('TRADING_FEEDBACK_SAMPLE_INVALID')
    f=value['funding'];_exact(f,('source_kind','source_version','evidence_hash'))
    if value['availability']=='AVAILABLE':
        if f['source_kind'] not in ('PAPER_MODEL','BROKER_LEDGER'):raise FeedbackError('TRADING_FEEDBACK_FUNDING_INVALID')
        safe_component(f['source_version']);_hash(f['evidence_hash'])
        if value['references']['position_hash'] is None or value['references']['trade_result_hash'] is None or value['closed_at'] is None:
            raise FeedbackError('TRADING_FEEDBACK_CLOSED_REFERENCES_REQUIRED')
        if paper and (f['source_kind'],f['source_version'])!=('PAPER_MODEL','paper-zero-funding-v0.1'):
            raise FeedbackError('TRADING_FEEDBACK_PAPER_SOURCE_INVALID')
        if not paper and f['source_kind']!='BROKER_LEDGER':raise FeedbackError('TRADING_FEEDBACK_DISPATCH_LEDGER_REQUIRED')
        if f['source_kind']=='BROKER_LEDGER' and f['source_version']=='paper-zero-funding-v0.1':
            raise FeedbackError('TRADING_FEEDBACK_PAPER_MODEL_RELABEL_FORBIDDEN')
    elif f!=dict(source_kind=None,source_version=None,evidence_hash=None) or value['closed_at'] is not None:
        raise FeedbackError('TRADING_FEEDBACK_UNAVAILABLE_FUNDING_FORBIDDEN')
    if value['performance_policy'] not in ('OPT_IN','OPT_OUT'):raise FeedbackError('TRADING_FEEDBACK_POLICY_INVALID')
    if value['performance'] is not None:
        if value['performance_policy']!='OPT_IN' or value['availability']!='AVAILABLE':raise FeedbackError('TRADING_FEEDBACK_OPT_IN_REQUIRED')
        _amounts(value['performance'])
    if value['performance_policy']=='OPT_IN' and value['availability']=='AVAILABLE' and value['performance'] is None:
        raise FeedbackError('TRADING_FEEDBACK_AVAILABLE_AMOUNTS_REQUIRED')
    actual=p['kind']=='HISTORICAL_TRADING_OWNER' and value['availability']=='AVAILABLE'
    expected_live=dict(status='HISTORICAL_CANONICAL_RECORDS',performance=value['performance']) if actual else dict(status='NOT_RUN',performance=None)
    if (actual and f['source_kind']!='BROKER_LEDGER' or value['actual_live']!=expected_live
            or value['financial_authority']!='NONE' or value['uncertainty']!=UNCERTAINTY):
        raise FeedbackError('TRADING_FEEDBACK_AUTHORITY_OR_LIVE_PROVENANCE_INVALID')
    return value


@dataclass(frozen=True)
class _TradingFeedbackSnapshot:
    namespace:str
    provenance_kind:str
    execution:str
    original_run_id:str
    original_process_generation:int|None
    original_binding_json:str
    original_binding_hash:str
    canonical:PaperRuntimeRecovery
    canonical_graph_hash:str
    dispatch_binding_json:str|None=None


def _project_feedback_snapshot(snapshot,*,performance_opt_in=False):
    if type(snapshot) is not _TradingFeedbackSnapshot or type(performance_opt_in) is not bool:
        raise FeedbackError('TRADING_FEEDBACK_ACTUAL_CAPTURE_REQUIRED')
    if (not _known_provenance(snapshot.namespace,snapshot.provenance_kind,snapshot.execution)
            or not isinstance(snapshot.original_binding_json,str)
            or byte_hash(snapshot.original_binding_json.encode())!=snapshot.original_binding_hash
            or type(snapshot.canonical) is not PaperRuntimeRecovery
            or byte_hash(canonical_bytes(asdict(snapshot.canonical)))!=snapshot.canonical_graph_hash):
        raise FeedbackError('TRADING_FEEDBACK_CAPTURE_CHANGED')
    graph=snapshot.canonical;binding=json.loads(snapshot.original_binding_json)
    paper=snapshot.provenance_kind=='PAPER_OWNER_SOURCE_FIXTURE'
    if paper:
        from storage.paper_process import _binding
        _binding(binding)
        if snapshot.dispatch_binding_json is not None or binding['namespace']!=snapshot.namespace:
            raise FeedbackError('TRADING_FEEDBACK_PAPER_CAPTURE_INVALID')
        strategy=dict(strategy_id=binding['strategy_id'],strategy_version=binding['strategy_version'],content_hash=binding['strategy_content_hash'])
        public_binding={key:binding[key] for key in PAPER_BINDING}
    else:
        from registry.operational_authority import ReleaseBinding
        if snapshot.dispatch_binding_json!=snapshot.original_binding_json or binding['namespace']!=snapshot.namespace or binding['execution']!=snapshot.execution:
            raise FeedbackError('TRADING_FEEDBACK_DISPATCH_CAPTURE_INVALID')
        release=ReleaseBinding(**binding['release'])
        if release.namespace!=snapshot.namespace:raise FeedbackError('TRADING_FEEDBACK_DISPATCH_NAMESPACE_INVALID')
        strategy=dict(binding['identity'],content_hash=binding['strategy_content_hash'])
        public_binding={key:binding['release'][key] for key in DISPATCH_BINDING}
    for field in fields(graph):
        value=getattr(graph,field.name)
        for item in value if isinstance(value,tuple) else (value,):
            if isinstance(item,StoredCanonicalObject):
                unused,raw,commitment=canonical_payload(item.payload)
                if raw!=item.payload_json or commitment!=item.payload_hash:raise FeedbackError('TRADING_FEEDBACK_CANONICAL_BYTES_CHANGED')
    if (graph.approved_trade_plan is None or graph.strategy_id!=strategy['strategy_id'] or graph.strategy_version!=strategy['strategy_version']):
        raise FeedbackError('TRADING_FEEDBACK_STRATEGY_LINEAGE_INVALID')
    result=None if graph.trade_result is None else graph.trade_result.payload
    position=None if graph.current_position_projection is None else graph.current_position_projection.payload
    available=(graph.status=='READY' and result is not None and position is not None and position['lifecycle_state']=='CLOSED')
    funding=dict(source_kind=None,source_version=None,evidence_hash=None);performance=None;closed_at=None
    if available:
        matches=[row for row in graph.funding_evidence if row.canonical_id==result['funding_evidence_id']]
        if len(matches)!=1:raise FeedbackError('TRADING_FEEDBACK_EXACT_FUNDING_REQUIRED')
        actual=matches[0];document=actual.payload
        if (result['trade_plan_id']!=graph.trade_plan_id or result['position_id']!=graph.position_id
                or document['trade_plan_id']!=graph.trade_plan_id or document['position_id']!=graph.position_id):
            raise FeedbackError('TRADING_FEEDBACK_CLOSED_LINEAGE_INVALID')
        funding=dict(source_kind=document['source_kind'],source_version=document['source_version'],evidence_hash=actual.payload_hash)
        closed_at=result['closed_at']
        if performance_opt_in:performance={key:result[key] for key in ('gross_pnl','net_pnl','total_fees')}|dict(funding_cost=document['funding_cost'])
    def reference(value):return None if value is None else byte_hash(value.encode('utf-8'))
    actual=snapshot.provenance_kind=='HISTORICAL_TRADING_OWNER' and available
    value=dict(schema_version=SCHEMA,namespace=snapshot.namespace,strategy=strategy,
        provenance=dict(kind=snapshot.provenance_kind,execution=snapshot.execution),binding=public_binding,
        references=dict(run_hash=reference(snapshot.original_run_id),trade_plan_hash=reference(graph.trade_plan_id),
            position_hash=reference(graph.position_id),trade_result_hash=reference(None if graph.trade_result is None else graph.trade_result.canonical_id),
            original_binding_hash=snapshot.original_binding_hash),closed_at=closed_at,availability='AVAILABLE' if available else 'UNAVAILABLE',
        sample_count=1 if available else 0,funding=funding,performance_policy='OPT_IN' if performance_opt_in else 'OPT_OUT',performance=performance,
        actual_live=dict(status='HISTORICAL_CANONICAL_RECORDS',performance=performance) if actual else dict(status='NOT_RUN',performance=None),
        financial_authority='NONE',uncertainty=list(UNCERTAINTY))
    return validate_trading_feedback(value)


def build_trading_feedback(reader,run_id,trade_plan_id,*,performance_opt_in=False):
    from storage.trading_feedback import _TradingFeedbackReader
    if type(reader) is not _TradingFeedbackReader or type(performance_opt_in) is not bool:
        raise FeedbackError('TRADING_FEEDBACK_PROTECTED_READ_PORT_REQUIRED')
    actual=reader.snapshot(run_id,trade_plan_id)
    snapshot=_TradingFeedbackSnapshot(namespace=actual.namespace,
        provenance_kind='FAKE_PROVIDER_VERIFICATION' if actual.namespace=='FIXTURE' else 'HISTORICAL_TRADING_OWNER',
        execution=actual.execution,original_run_id=run_id,original_process_generation=None,
        original_binding_json=actual.original_binding_json,original_binding_hash=byte_hash(actual.original_binding_json.encode()),
        canonical=actual.canonical,canonical_graph_hash=byte_hash(canonical_bytes(asdict(actual.canonical))),dispatch_binding_json=actual.original_binding_json)
    return _project_feedback_snapshot(snapshot,performance_opt_in=performance_opt_in)


def render_trading_feedback(value):
    validate_trading_feedback(value)
    detail=html.escape(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2))
    return ('<!doctype html><html lang="zh-Hant"><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>R7 歷史交易摘要</title><h1>R7 歷史交易摘要</h1><p>歷史紀錄不提供交易或資金權限。'
        'Paper／模擬提供者結果不代表真實 LIVE 績效；金額預設不公開。</p><pre>'+detail+'</pre></html>').encode('utf-8')


def trading_feedback_bundle(value):
    validate_trading_feedback(value);raw=canonical_bytes(value);strategy=value['strategy']
    logical='reports/feedback/trading/'+strategy['strategy_id']+'/'+strategy['strategy_version']+'/'+byte_hash(raw)[7:]
    return ArtifactBundle(logical,{'feedback.json':raw,'report.html':render_trading_feedback(value)})


def validate_trading_feedback_publication(logical_path,payloads):
    if set(payloads)!={'feedback.json','report.html'}:raise FeedbackError('TRADING_FEEDBACK_BUNDLE_INVALID')
    expected=trading_feedback_bundle(load_json(payloads['feedback.json'],256*1024))
    if expected.logical_path!=logical_path or dict(expected.payloads)!=payloads:raise FeedbackError('TRADING_FEEDBACK_BUNDLE_CHANGED')
