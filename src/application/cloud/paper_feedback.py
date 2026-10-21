"""Allowlisted forward projection from an already attached actual PAPER owner.

Export never claims a process generation, grants authority or starts a runtime.
Research feedback retains its separate, unchanged versioned schema.
"""
import html,json,re
from decimal import Decimal
from application.cloud.feedback import FeedbackError,_exact,_reasons,_decimal
from application.cloud.manifest import HASH,byte_hash,canonical_bytes,load_json,safe_component,utc
from application.cloud.protocol import ArtifactBundle

SCHEMA='r7-paper-feedback-v0.2'
RECORDED_SCHEMA='r7-paper-feedback-v0.3'
TOP={'schema_version','run_id','namespace','strategy','source','binding','producer','created_at','observation',
    'assessment','performance_policy','performance','cost_conventions','live','broker_kind','financial_authority','artifact_links','uncertainty'}
NUMBERS=('actual_elapsed_seconds','actual_healthy_seconds','simulated_elapsed_seconds',
    'simulated_healthy_seconds','max_observed_gap_seconds','closed_trades')
METRICS=('net_pnl_usdt','expectancy_usdt_per_trade','max_drawdown_usdt','profit_factor')
UNCERTAINTY=['PAPER uses an isolated simulated account and does not establish LIVE performance or financial authority.',
    'Accelerated fixture duration is not actual forward observation.',
    'Closed-trade counts are not independent observations.']

def _number(value):
    if type(value) is not int or not 0<=value<=2**31-1:raise FeedbackError('PAPER_FEEDBACK_COUNT_INVALID')

def _hash(value):
    if not isinstance(value,str) or not HASH.fullmatch(value):raise FeedbackError('PAPER_FEEDBACK_HASH_INVALID')

def validate_paper_feedback(value):
    recorded=isinstance(value,dict) and value.get('schema_version')==RECORDED_SCHEMA
    _exact(value,TOP|({'funding'} if recorded else set()))
    if value['schema_version'] not in (SCHEMA,RECORDED_SCHEMA):raise FeedbackError('PAPER_FEEDBACK_SCHEMA_INVALID')
    safe_component(value['run_id']);utc(value['created_at'])
    _exact(value['strategy'],('strategy_id','strategy_version','content_hash'))
    for name in ('strategy_id','strategy_version'):safe_component(value['strategy'][name])
    _hash(value['strategy']['content_hash'])
    source=value['source'];_exact(source,('executable_revision','implementation_hash','execution','worktree'))
    if source['executable_revision'] is not None and (not isinstance(source['executable_revision'],str)
            or not re.fullmatch('[0-9a-f]{40}',source['executable_revision'])):raise FeedbackError('PAPER_FEEDBACK_SOURCE_INVALID')
    _hash(source['implementation_hash'])
    if source['execution']!='LOCAL' or source['worktree'] not in ('CLEAN','DIRTY','UNAVAILABLE'):
        raise FeedbackError('PAPER_FEEDBACK_SOURCE_INVALID')
    _exact(value['binding'],('config_hash','risk_policy_hash','paper_policy_hash'))
    for number in value['binding'].values():_hash(number)
    _exact(value['producer'],('process_generation','process_instance_hash'))
    _number(value['producer']['process_generation'])
    if value['producer']['process_generation']==0:raise FeedbackError('PAPER_FEEDBACK_ACTUAL_PRODUCER_REQUIRED')
    _hash(value['producer']['process_instance_hash'])
    row=value['observation'];_exact(row,('mode','execution','started_at','observed_at',*NUMBERS))
    if (value['namespace'],row['mode'],row['execution']) not in (
            ('FIXTURE','ACCELERATED_FIXTURE','SIMULATED_MECHANICS'),('LOCAL_RESEARCH','REAL_TIME','ACTUAL_OWNER')):
        raise FeedbackError('PAPER_FEEDBACK_OBSERVATION_PROVENANCE_INVALID')
    for name in NUMBERS:_number(row[name])
    if row['actual_healthy_seconds']>row['actual_elapsed_seconds'] or row['simulated_healthy_seconds']>row['simulated_elapsed_seconds']:
        raise FeedbackError('PAPER_FEEDBACK_HEALTHY_DURATION_INVALID')
    if row['mode']=='ACCELERATED_FIXTURE' and (row['actual_elapsed_seconds'] or row['actual_healthy_seconds']):
        raise FeedbackError('PAPER_FEEDBACK_FIXTURE_REAL_DURATION_FORBIDDEN')
    if row['mode']=='REAL_TIME' and (row['simulated_elapsed_seconds'] or row['simulated_healthy_seconds']):
        raise FeedbackError('PAPER_FEEDBACK_REAL_SIMULATED_DURATION_FORBIDDEN')
    if row['started_at'] is None or row['observed_at'] is None:
        if row['started_at'] is not None or row['observed_at'] is not None or any(row[key] for key in NUMBERS):
            raise FeedbackError('PAPER_FEEDBACK_UNOBSERVED_DURATION_FORBIDDEN')
    elif utc(row['started_at'])>utc(row['observed_at']) or value['created_at']!=row['observed_at']:
        raise FeedbackError('PAPER_FEEDBACK_OBSERVATION_TIME_INVALID')
    assessment=value['assessment'];_exact(assessment,('status','reason_codes','run_revision','assessment_hash'))
    if assessment['status'] not in ('PASS','FAIL','BLOCKED'):raise FeedbackError('PAPER_FEEDBACK_ASSESSMENT_INVALID')
    _reasons(assessment['reason_codes']);_number(assessment['run_revision']);_hash(assessment['assessment_hash'])
    if value['performance_policy'] not in ('OPT_OUT','OPT_IN'):raise FeedbackError('PAPER_FEEDBACK_POLICY_INVALID')
    if value['cost_conventions']!=dict(slippage='IN_FILL_PRICE_NO_ADDITIONAL_DEDUCTION',
            funding_model='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1' if recorded else 'EXPLICIT_REGISTERED_PAPER_ZERO',account_scope='ISOLATED_PER_STRATEGY_RUN'):
        raise FeedbackError('PAPER_FEEDBACK_COST_CONVENTION_INVALID')
    if recorded:
        funding=value['funding']
        _exact(funding,('funding_model','source_kind','cost_basis','billing_disclosure','status','pending_allocations',
            'finalized_allocations','pending_since','wall_wait_seconds','observed_wait_seconds','wait_reason','flat_observation','latest_source','opportunities'))
        if (value['namespace']!='LOCAL_RESEARCH' or row['mode']!='REAL_TIME'
                or funding['funding_model']!='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1' or funding['source_kind']!='PAPER_MODEL'
                or funding['cost_basis']!='ACTUAL_ENTRY_FILL_NOTIONAL'
                or funding['billing_disclosure']!='PAPER_MODEL_NOT_EXCHANGE_ACCOUNT_BILL'
                or funding['status'] not in ('FUNDING_PENDING','FINALIZED','NO_FINANCIAL_SAMPLE')):
            raise FeedbackError('PAPER_FEEDBACK_FUNDING_PROFILE_INVALID')
        for key in ('pending_allocations','finalized_allocations','wall_wait_seconds','observed_wait_seconds'):_number(funding[key])
        if funding['finalized_allocations']!=row['closed_trades'] or funding['pending_allocations'] not in (0,1):
            raise FeedbackError('PAPER_FEEDBACK_FUNDING_COUNTS_INVALID')
        pending=funding['status']=='FUNDING_PENDING'
        if pending!=(funding['pending_allocations']==1):raise FeedbackError('PAPER_FEEDBACK_FUNDING_PENDING_INVALID')
        if pending:
            utc(funding['pending_since']);_reasons([funding['wait_reason']])
            _exact(funding['flat_observation'],('position_id','symbol','actual_quantity','broker_state_observed_at'))
            flat=funding['flat_observation'];safe_component(flat['position_id']);utc(flat['broker_state_observed_at'])
            if flat['symbol']!='BTC_USDT_PERP' or _decimal(flat['actual_quantity']) is None or Decimal(flat['actual_quantity'])!=0:
                raise FeedbackError('PAPER_FEEDBACK_FUNDING_FLAT_REQUIRED')
            if assessment['status']=='PASS' or 'FUNDING_FINALIZATION_PENDING' not in assessment['reason_codes']:
                raise FeedbackError('PAPER_FEEDBACK_PENDING_PASS_FORBIDDEN')
        elif (funding['pending_since'] is not None or funding['wait_reason'] is not None or funding['flat_observation'] is not None
                or funding['wall_wait_seconds'] or funding['observed_wait_seconds']):
            raise FeedbackError('PAPER_FEEDBACK_FUNDING_PENDING_INVALID')
        if not pending and (funding['status']=='FINALIZED')!=(funding['finalized_allocations']>0):
            raise FeedbackError('PAPER_FEEDBACK_FUNDING_COUNTS_INVALID')
        impact=funding['opportunities']
        categories=('valid_blocked','non_directional','other_gate_blocked','unresolved_financial','stale_or_invalid')
        _exact(impact,('evaluated_boundaries','last_boundary',*categories))
        for key in ('evaluated_boundaries',*categories):_number(impact[key])
        if sum(impact[key] for key in categories)!=impact['evaluated_boundaries']:
            raise FeedbackError('PAPER_FEEDBACK_FUNDING_COUNTS_INVALID')
        if impact['evaluated_boundaries']:utc(impact['last_boundary'])
        elif impact['last_boundary'] is not None:raise FeedbackError('PAPER_FEEDBACK_FUNDING_COUNTS_INVALID')
        latest=funding['latest_source'];_exact(latest,('status','reason_code','observed_at','coverage_start','complete_through','snapshot_hash'))
        if latest['status'] not in ('HEALTHY','UNAVAILABLE'):raise FeedbackError('PAPER_FEEDBACK_FUNDING_SOURCE_INVALID')
        if latest['status']=='HEALTHY':
            for key in ('observed_at','coverage_start','complete_through'):utc(latest[key])
            if latest['reason_code'] is not None or not isinstance(latest['snapshot_hash'],str) or not re.fullmatch('[0-9a-f]{64}',latest['snapshot_hash']):
                raise FeedbackError('PAPER_FEEDBACK_FUNDING_SOURCE_INVALID')
        else:
            _reasons([latest['reason_code']])
            keys=('observed_at','coverage_start','complete_through','snapshot_hash')
            if any(latest[key] is not None for key in keys):
                if not all(latest[key] is not None for key in keys):raise FeedbackError('PAPER_FEEDBACK_FUNDING_SOURCE_INVALID')
                for key in keys[:3]:utc(latest[key])
                if type(latest['snapshot_hash']) is not str or not re.fullmatch('[0-9a-f]{64}',latest['snapshot_hash']):
                    raise FeedbackError('PAPER_FEEDBACK_FUNDING_SOURCE_INVALID')
    if value['performance'] is not None:
        if value['performance_policy']!='OPT_IN' or not row['closed_trades']:
            raise FeedbackError('PAPER_FEEDBACK_AVAILABLE_PERFORMANCE_OPT_IN_REQUIRED')
        _exact(value['performance'],METRICS)
        for number in value['performance'].values():_decimal(number)
    if (value['live']!={'status':'NOT_RUN','performance':None} or value['broker_kind']!='PAPER_ONLY'
            or value['financial_authority']!='NONE' or value['artifact_links']!=[] or value['uncertainty']!=UNCERTAINTY):
        raise FeedbackError('PAPER_FEEDBACK_FINANCIAL_AUTHORITY_FORBIDDEN')
    return value

def build_paper_feedback(runtime,*,performance_opt_in=False):
    from application.paper.service import PaperRuntime
    from application.paper.assessment import assess_forward
    from application.research.evidence import capture_provenance
    from registry import EvidenceGateError
    if type(runtime) is not PaperRuntime or type(performance_opt_in) is not bool:
        raise FeedbackError('PAPER_FEEDBACK_CURRENT_ACTUAL_RUNTIME_REQUIRED')
    service=runtime.service;before=service.process.recover(runtime.run_id)
    if before.process_generation!=runtime.coordinator.generation:
        raise FeedbackError('PAPER_FEEDBACK_STALE_PROCESS_GENERATION')
    producer=service.process._db.execute('SELECT instance_id FROM paper_process_generations WHERE run_id=? AND generation=?',
        (runtime.run_id,before.process_generation)).fetchone()
    if producer is None or producer['instance_id']!=service._instance_id:
        raise FeedbackError('PAPER_FEEDBACK_CURRENT_PROCESS_INSTANCE_REQUIRED')
    try:actual=assess_forward(runtime,service.promotion)
    except EvidenceGateError:raise FeedbackError('PAPER_FEEDBACK_CURRENT_OWNER_EVIDENCE_REQUIRED') from None
    assessment=actual.as_dict()
    source=capture_provenance()
    if source['implementation_hash']!=before.binding['implementation_hash']:
        raise FeedbackError('PAPER_FEEDBACK_CURRENT_SOURCE_REQUIRED')
    row=service.process._run(runtime.run_id)
    value=dict(schema_version=SCHEMA,run_id=runtime.run_id,namespace=service.namespace,
        strategy=dict(strategy_id=before.binding['strategy_id'],strategy_version=before.binding['strategy_version'],
            content_hash=before.binding['strategy_content_hash']),
        source={key:source[key] for key in ('executable_revision','implementation_hash','execution','worktree')},
        binding={key:before.binding[key] for key in ('config_hash','risk_policy_hash','paper_policy_hash')},
        producer=dict(process_generation=before.process_generation,process_instance_hash=byte_hash(producer['instance_id'].encode('utf-8'))),
        created_at=assessment['observed_at'] or row['created_at'],
        observation=dict(mode=assessment['forward_mode'],execution=assessment['execution'],
            started_at=assessment['started_at'],observed_at=assessment['observed_at'],
            **{key:assessment[key] for key in NUMBERS}),
        assessment=dict(status=assessment['status'],reason_codes=_reasons(assessment['reason_codes']),
            run_revision=assessment['run_revision'],assessment_hash=actual.assessment_hash),
        performance_policy='OPT_IN' if performance_opt_in else 'OPT_OUT',
        cost_conventions=dict(slippage=assessment['slippage_convention'],funding_model=assessment['funding_model'],account_scope=assessment['account_scope']),
        performance={key:assessment[key] for key in METRICS} if performance_opt_in and assessment['closed_trades'] else None,
        live=dict(status='NOT_RUN',performance=None),broker_kind='PAPER_ONLY',financial_authority='NONE',
        artifact_links=[],uncertainty=list(UNCERTAINTY))
    if service.recorded_funding:
        from application.paper.funding_source import funding_status
        value['schema_version']=RECORDED_SCHEMA
        value['funding']=funding_status(before.state['runtime'],now=service.clock() if assessment['observed_at'] is None else utc(assessment['observed_at']))
    after=service.process.recover(runtime.run_id)
    if ((before.process_generation,before.revision,before.binding_json,before.state_json)!=
            (after.process_generation,after.revision,after.binding_json,after.state_json)
            or assessment['run_revision']!=before.revision):
        raise FeedbackError('PAPER_FEEDBACK_OWNER_SNAPSHOT_CHANGED')
    return validate_paper_feedback(value)

def render_paper_feedback(value):
    validate_paper_feedback(value)
    detail=html.escape(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2))
    row=value['observation']
    cells=[('模式',row['mode']),('執行來源',row['execution']),('實際觀察秒數',row['actual_elapsed_seconds']),
        ('模擬觀察秒數',row['simulated_elapsed_seconds']),('已平倉交易數',row['closed_trades']),('實際評估',value['assessment']['status'])]
    if value['schema_version']==RECORDED_SCHEMA:
        funding=value['funding'];cells.extend([('資金費率模型',funding['funding_model']),('費率計費基礎',funding['cost_basis']),
            ('財務結算',funding['status']),('待結算筆數',funding['pending_allocations']),('等待秒數',funding['wall_wait_seconds']),
            ('等待原因',funding['wait_reason']),('最新來源',funding['latest_source']['status'])])
    table=''.join('<tr><th>'+html.escape(label)+'</th><td>'+html.escape(str(actual))+'</td></tr>' for label,actual in cells)
    policy='績效未公開（預設）' if value['performance_policy']=='OPT_OUT' else '本機使用者已選擇公開可用績效；尚無平倉交易時仍保留 null'
    return ('<!doctype html><html lang="zh-Hant"><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>R7 PAPER 回饋</title><style>body{font-family:system-ui;max-width:75rem;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}th,td{text-align:left;padding:.5rem}</style>'
        '<h1>R7 PAPER 回饋</h1><p>PAPER 使用隔離模擬帳戶；模擬時間不代表實際 forward，結果不提供 LIVE 或資金權限。</p>'
        '<p>'+policy+'</p><table>'+table+'</table><details><summary>完整可核對資料</summary><pre>'+detail+'</pre></details></html>').encode('utf-8')

def paper_feedback_bundle(value):
    validate_paper_feedback(value);raw=canonical_bytes(value);strategy=value['strategy']
    logical='reports/feedback/paper/'+strategy['strategy_id']+'/'+strategy['strategy_version']+'/'+byte_hash(raw)[7:]
    return ArtifactBundle(logical,{'feedback.json':raw,'report.html':render_paper_feedback(value)})

def validate_paper_feedback_publication(logical_path,payloads):
    if set(payloads)!={'feedback.json','report.html'}:raise FeedbackError('PAPER_FEEDBACK_BUNDLE_INVALID')
    document=load_json(payloads['feedback.json'],256*1024);expected=paper_feedback_bundle(document)
    if expected.logical_path!=logical_path or dict(expected.payloads)!=payloads:raise FeedbackError('PAPER_FEEDBACK_BUNDLE_INVALID')
