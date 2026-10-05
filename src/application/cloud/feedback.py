"""Allowlisted Chat feedback from actual local research owner evidence.

No caller-supplied assessment can become research evidence. Performance is
local opt-in; private provider material is excluded regardless of that policy.
"""
from decimal import Decimal,InvalidOperation
import html
import json
import re

from application.cloud.manifest import HASH,byte_hash,canonical_bytes,load_json,safe_component,utc
from application.cloud.protocol import ArtifactBundle
from application.research.service import ResearchService


class FeedbackError(ValueError):pass


METRICS=('net_pnl','gross_pnl','total_fees','funding_cost','expectancy','max_drawdown','win_rate','profit_factor')
TOP={'schema_version','run_id','namespace','strategy','source','dataset','split','created_at','reason_codes',
     'training','development','robustness','sealed_oos','paper','live','performance_policy','holdout_observed',
     'artifact_links','uncertainty'}
STAGE={'status','sample_count','trial_count','reason_codes','performance'}


def _exact(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys):raise FeedbackError('FEEDBACK_FIELDS_INVALID')


def _count(value):
    if value is not None and (type(value) is not int or not 0<=value<=10000000):raise FeedbackError('FEEDBACK_COUNT_INVALID')
    return value


def _reasons(values):
    if not isinstance(values,(list,tuple)) or len(values)>128:raise FeedbackError('FEEDBACK_REASONS_INVALID')
    if any(not isinstance(value,str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,127}',value) for value in values):
        raise FeedbackError('FEEDBACK_REASONS_INVALID')
    return sorted(set(values))


def _decimal(value):
    if value is None:return None
    if not isinstance(value,str) or len(value)>128 or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]+)?',value):
        raise FeedbackError('FEEDBACK_EXACT_DECIMAL_REQUIRED')
    try:
        if not Decimal(value).is_finite():raise FeedbackError('FEEDBACK_EXACT_DECIMAL_REQUIRED')
    except InvalidOperation:raise FeedbackError('FEEDBACK_EXACT_DECIMAL_REQUIRED') from None
    return value


def _stage(status='NOT_RUN',*,backtest=None,reasons=(),trials=None,performance=False):
    return dict(status=status,sample_count=None if backtest is None else _count(backtest['total_trades']),
                trial_count=trials,reason_codes=_reasons(reasons),performance=None if not performance or backtest is None else
                {name:_decimal(backtest.get(name)) for name in METRICS})


def validate_feedback(value):
    """Strict public schema. Unknown/freeform/private fields cannot be rendered."""
    _exact(value,TOP)
    if value['schema_version']!='r7-chat-feedback-v0.2' or value['namespace'] not in ('FIXTURE','LOCAL_RESEARCH'):
        raise FeedbackError('FEEDBACK_SCHEMA_INVALID')
    safe_component(value['run_id']);utc(value['created_at'])
    _exact(value['strategy'],('strategy_id','strategy_version','content_hash','runtime_family','runtime_version'))
    for name in ('strategy_id','strategy_version','runtime_family','runtime_version'):safe_component(value['strategy'][name])
    if not isinstance(value['strategy']['content_hash'],str) or not HASH.fullmatch(value['strategy']['content_hash']):raise FeedbackError('FEEDBACK_HASH_INVALID')
    _exact(value['source'],('executable_revision','implementation_hash','execution','worktree'))
    revision=value['source']['executable_revision']
    if revision is not None and (not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{40}',revision)):raise FeedbackError('FEEDBACK_SOURCE_INVALID')
    if not HASH.fullmatch(value['source']['implementation_hash']) or value['source']['execution']!='LOCAL' or value['source']['worktree'] not in ('CLEAN','DIRTY','UNAVAILABLE'):
        raise FeedbackError('FEEDBACK_SOURCE_INVALID')
    _exact(value['dataset'],('dataset_id','dataset_version','manifest_hash'))
    for name in ('dataset_id','dataset_version'):safe_component(value['dataset'][name])
    if not HASH.fullmatch(value['dataset']['manifest_hash']):raise FeedbackError('FEEDBACK_HASH_INVALID')
    _exact(value['split'],('policy_hash','training','development','sealed_oos'))
    if not HASH.fullmatch(value['split']['policy_hash']):raise FeedbackError('FEEDBACK_HASH_INVALID')
    for name in ('training','development','sealed_oos'):
        interval=value['split'][name];_exact(interval,('start','end'))
        if utc(interval['start'])>=utc(interval['end']):raise FeedbackError('FEEDBACK_SPLIT_INVALID')
    if value['performance_policy'] not in ('OPT_OUT','OPT_IN') or type(value['holdout_observed']) is not bool:raise FeedbackError('FEEDBACK_POLICY_INVALID')
    _reasons(value['reason_codes'])
    for name in ('training','development','robustness','sealed_oos'):
        row=value[name];_exact(row,STAGE)
        if row['status'] not in ('NOT_RUN','EXECUTED','PASS','FAIL','BLOCKED'):raise FeedbackError('FEEDBACK_STATUS_INVALID')
        _count(row['sample_count']);_count(row['trial_count']);_reasons(row['reason_codes'])
        if row['performance'] is not None:
            if value['performance_policy']!='OPT_IN':raise FeedbackError('FEEDBACK_OPT_IN_REQUIRED')
            _exact(row['performance'],METRICS)
            for number in row['performance'].values():_decimal(number)
        if row['status']=='NOT_RUN' and (row['sample_count'] is not None or row['performance'] is not None):raise FeedbackError('FEEDBACK_UNPERFORMED_METRICS')
    # This research exporter has no forward/runtime owner binding. No invented
    # PAPER duration or LIVE performance can enter this versioned projection.
    if value['paper']!={'status':'NOT_RUN','observation_seconds':None,'sample_count':None} or value['live']!={'status':'NOT_RUN','performance':None}:
        raise FeedbackError('FEEDBACK_UNBOUND_FORWARD_EVIDENCE')
    if value['artifact_links']!=[]:
        raise FeedbackError('FEEDBACK_LINK_INVALID')
    if value['uncertainty']!=['Historical research does not establish forward performance or financial authority.',
                              'Trial counts and closed-trade counts are not independent observations.']:
        raise FeedbackError('FEEDBACK_UNCERTAINTY_INVALID')
    return value


def build_research_feedback(service,run_id,*,performance_opt_in=False):
    if type(service) is not ResearchService or type(performance_opt_in) is not bool:raise FeedbackError('ACTUAL_LOCAL_RESEARCH_OWNER_REQUIRED')
    safe_component(run_id)
    report=service.report(run_id)
    inputs,input_hash=service.ledger._run(run_id)
    if report['run_id']!=run_id or report['inputs']!=inputs or report['namespace']!=inputs['namespace'] or inputs['namespace']!=service.namespace:
        raise FeedbackError('FEEDBACK_OWNER_LINEAGE_MISMATCH')
    strategy=inputs['strategy'];runtime=strategy['runtime_compatibility'];provenance=inputs['provenance'];dataset=inputs['dataset']
    robust=report['robustness'];product=report['product_assessment']
    row=next((row for row in service.journal.runs() if row['run_id']==run_id),None)
    if row is None or row['input_hash']!=input_hash:raise FeedbackError('FEEDBACK_OWNER_LINEAGE_MISMATCH')
    training_trials=None if robust is None else sum(len(window['training_variants']) for window in robust.get('walk_forward',{}).get('windows',[]))
    development_decision=None if robust is None else robust.get('development',{}).get('assessment')
    feedback=dict(schema_version='r7-chat-feedback-v0.2',run_id=run_id,namespace=inputs['namespace'],
        strategy={key:strategy[key] for key in ('strategy_id','strategy_version','content_hash')},
        source={key:provenance[key] for key in ('executable_revision','implementation_hash','execution','worktree')},
        dataset=dict(dataset_id=dataset['dataset_id'],dataset_version=dataset['dataset_version'],manifest_hash=inputs['dataset_manifest_hash']),
        split=dict(policy_hash=inputs['split_policy_hash'],**{key:inputs['split_policy'][key] for key in ('training','development','sealed_oos')}),
        created_at=row['created_at'],reason_codes=_reasons(report['reason_codes']),
        training=_stage('EXECUTED' if training_trials else 'NOT_RUN',trials=training_trials),
        development=_stage(development_decision['status'] if development_decision else 'EXECUTED' if report['backtest'] is not None else 'NOT_RUN',
            backtest=report['backtest'],reasons=() if development_decision is None else development_decision['reason_codes'],performance=performance_opt_in),
        robustness=_stage('NOT_RUN' if robust is None else robust['status'],reasons=() if robust is None else robust['reason_codes']),
        sealed_oos=_stage(report['sealed_oos'],backtest=None if product is None else product.get('sealed_backtest'),
            reasons=() if product is None else product['reason_codes'],trials=None if product is None else product.get('trial_count'),performance=performance_opt_in),
        paper=dict(status='NOT_RUN',observation_seconds=None,sample_count=None),live=dict(status='NOT_RUN',performance=None),
        performance_policy='OPT_IN' if performance_opt_in else 'OPT_OUT',holdout_observed=False,
        artifact_links=[],
        uncertainty=['Historical research does not establish forward performance or financial authority.',
                     'Trial counts and closed-trade counts are not independent observations.'])
    feedback['strategy'].update(runtime)
    exposes_oos=product is not None and product.get('sealed_backtest') is not None
    feedback['holdout_observed']=exposes_oos
    validate_feedback(feedback)
    if exposes_oos:
        from application.research.holdout import FrozenFinalist
        frozen=report['frozen_finalist']
        if frozen is None:raise FeedbackError('FEEDBACK_FINALIST_REQUIRED')
        # Bind the actual stored frozen object, not any copied report fields.
        row=service.ledger._db.execute('SELECT * FROM research_finalists WHERE run_id=?',(run_id,)).fetchone()
        if row is None:raise FeedbackError('FEEDBACK_FINALIST_REQUIRED')
        finalist=FrozenFinalist(row['finalist_id'],row['frozen_json'],row['frozen_hash'])
        actual=service.ledger.verify_finalist(finalist)
        stored=service.ledger.result(finalist)
        if actual!=frozen or stored is None or stored.as_dict()!=product:raise FeedbackError('FEEDBACK_OOS_LINEAGE_MISMATCH')
        period=actual['policies']['split']['sealed_oos']
        # Reserve observation before any report bytes can escape. A failed
        # publication remains conservatively observed; retries are idempotent.
        service.ledger.observe_holdout(actual['family_id'],period['start'],period['end'],kind='CHAT_OBSERVATION',reference_hash=byte_hash(canonical_bytes(feedback)))
    return feedback


def render_feedback(value):
    validate_feedback(value)
    body=html.escape(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2))
    return ('<!doctype html><html lang="zh-Hant"><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>R7 研究回饋</title><style>body{font-family:system-ui;max-width:80rem;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
            '<h1>R7 研究回饋</h1><p>歷史研究不代表未來績效；未執行階段保留 NOT_RUN。</p><pre>'+body+'</pre></html>').encode('utf-8')


def feedback_bundle(value):
    validate_feedback(value)
    raw=canonical_bytes(value);strategy=value['strategy']
    logical='reports/feedback/'+strategy['strategy_id']+'/'+strategy['strategy_version']+'/'+byte_hash(raw)[7:]
    return ArtifactBundle(logical,{'feedback.json':raw,'report.html':render_feedback(value)})


def validate_feedback_publication(logical_path,payloads):
    if set(payloads)!={'feedback.json','report.html'}:raise FeedbackError('FEEDBACK_BUNDLE_INVALID')
    document=load_json(payloads['feedback.json'],256*1024)
    expected=feedback_bundle(document)
    if expected.logical_path!=logical_path or dict(expected.payloads)!=payloads:raise FeedbackError('FEEDBACK_BUNDLE_INVALID')


def queue_feedback(service,run_id,*,performance_opt_in=False):
    from application.research.evidence import now_utc
    feedback=build_research_feedback(service,run_id,performance_opt_in=performance_opt_in)
    return service.journal.enqueue_feedback(feedback,now_utc())


def flush_feedback(journal,transport,*,limit,fault_hook=None):
    from application.research.evidence import ResearchJournal
    from application.cloud.publisher import PublishSummary
    from application.cloud.protocol import CloudError
    if type(journal) is not ResearchJournal:raise FeedbackError('ACTUAL_RESEARCH_JOURNAL_REQUIRED')
    items=journal.pending_feedback_publications(limit)
    counts=dict(local_staged=0,cloud_acknowledged=0,unavailable=0,conflicts=0)
    for operation,bundle,expected in items:
        try:
            receipt=transport.publish(bundle,operation)
            if fault_hook is not None:fault_hook('AFTER_UPLOAD_BEFORE_ACK')
            if receipt.operation_id!=operation or receipt.artifact_hash!=expected or receipt.status not in ('LOCAL_STAGED','CLOUD_ACKNOWLEDGED'):
                raise CloudError('UNAVAILABLE','FEEDBACK_TRANSPORT_RECEIPT_INVALID')
            journal.record_feedback_publication(operation,receipt.status,artifact_hash=receipt.artifact_hash)
            counts['local_staged' if receipt.status=='LOCAL_STAGED' else 'cloud_acknowledged']+=1
        except CloudError as error:
            status='CONFLICT' if error.code=='CONFLICT' else 'UNAVAILABLE'
            journal.record_feedback_publication(operation,status)
            counts['conflicts' if status=='CONFLICT' else 'unavailable']+=1
    return PublishSummary(len(items),**counts)
