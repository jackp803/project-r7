"""Prepare UNAPPLIED UI additions; consume existing authenticated GET views."""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
OUT=BASE/'ui01-projection-unapplied-v1'
path=ROOT/'ui/src/App.tsx'
original=path.read_text(encoding='utf-8')
raw=original
def replace(before,after):
    global raw
    if raw.count(before)!=1:raise ValueError('Exact single frontend anchor required: '+before[:100])
    raw=raw.replace(before,after,1)

COMPONENTS='''type Observation={status:string;source:string;as_of:string|null;checked_at:string;reason_codes:string[];facts:unknown;financial_authority:'NONE'};
function ObservationTime({value,zone}:{value:string|null;zone:Zone}){
  return value===null?<span>未觀察</span>:<><time dateTime={value}>{utcDisplay(value,zone)}</time><small className="block"><code>{value}</code></small></>;
}
function Diagnostic({title,value,zone,testId,children}:{title:string;value:Observation;zone:Zone;testId:string;children?:ReactNode}){
  const labels:Record<string,string>={AVAILABLE:'已有來源觀測',NOT_CONFIGURED:'尚未設定',NOT_RUN:'尚未執行',UNAVAILABLE:'目前無法確認'};
  return <article className="detail" data-testid={testId}><h3>{title}</h3><p>{labels[value.status]??'未知狀態'} <code>{value.status}</code></p>
    {children}<dl><dt>資料來源</dt><dd><code>{value.source}</code></dd><dt>來源時點</dt><dd><ObservationTime value={value.as_of} zone={zone}/></dd><dt>本次讀取</dt><dd><ObservationTime value={value.checked_at} zone={zone}/></dd></dl>
    <Reasons codes={value.reason_codes}/><JsonDetail value={{facts:value.facts,financial_authority:value.financial_authority}} title="來源事實與權限範圍"/></article>;
}
function WorkerBudget({value}:{value:Observation}){
  return <><Fact label="設定的研究工作者數" value={object(value.facts).research_worker_count}/><p className="hint">這是本機設定值；記憶體額度與實際程序隔離仍須由原生診斷確認。</p></>;
}
function ProcessFacts({value,zone}:{value:Observation;zone:Zone}){
  const facts=object(value.facts);
  return <dl><dt>程序狀態</dt><dd>{healthStatus(facts.status)} <code>{text(facts.status)}</code></dd><dt>記錄狀態</dt><dd>{text(facts.recorded_state)}</dd>
    <dt>程序世代</dt><dd>{metric(facts.generation)} · <code>{text(facts.process_generation_id)}</code></dd><dt>首次啟動</dt><dd><ObservationTime value={typeof facts.started_at==='string'?facts.started_at:null} zone={zone}/></dd>
    <dt>原始心跳</dt><dd><ObservationTime value={typeof facts.heartbeat_at==='string'?facts.heartbeat_at:null} zone={zone}/></dd><dt>心跳序號</dt><dd>{metric(facts.heartbeat_sequence)}</dd><dt>程序設定雜湊</dt><dd><code>{text(facts.config_hash)}</code></dd></dl>;
}

'''
replace('function Overview(props:Common){',COMPONENTS+'function Overview(props:Common){')
replace('    <Panel title="操作界線">', '''    <Panel title="策略、研究與資源觀測"><Diagnostic title="已選策略與版本" value={data.strategy_subjects} zone={props.zone} testId="overview-strategy-subjects">
      <p className="hint">本機選擇與執行中綁定分開核對；不以登錄順序推定目前策略。</p>{rows(object(data.strategy_subjects.facts).items).map(row=><dl key={text(row.strategy_id)+':'+text(row.strategy_version)}><dt>策略／版本</dt><dd><code>{text(row.strategy_id)} / {text(row.strategy_version)}</code></dd><dt>內容雜湊</dt><dd><code>{text(row.content_hash)}</code></dd><dt>關係</dt><dd>本機設定的選擇 <code>{text(row.relationship)}</code></dd></dl>)}</Diagnostic>
      <Diagnostic title="研究狀態與最後階段" value={data.research_stage_counts} zone={props.zone} testId="overview-research-stage-counts">
        <p>來源保留的工作總數：{metric(object(data.research_stage_counts.facts).total_jobs)}；階段是最後持久記錄，並非正在執行的保證。</p>
        {rows(object(data.research_stage_counts.facts).items).map(row=><dl key={text(row.state)+':'+text(row.stage)}><dt>{text(row.state)} / {text(row.stage)}</dt><dd>{text(row.count)} 筆；<ObservationTime value={typeof row.last_observed_at==='string'?row.last_observed_at:null} zone={props.zone}/></dd></dl>)}</Diagnostic>
      <Diagnostic title="研究資源設定" value={data.resource_limits} zone={props.zone} testId="overview-resource-limits"><WorkerBudget value={data.resource_limits}/></Diagnostic>
      <Diagnostic title="最近保留的研究失敗" value={data.alerts} zone={props.zone} testId="overview-alerts">
        {rows(object(data.alerts.facts).items).map(row=><div key={text(row.alert_id)}><p><code>{text(row.run_id)}</code></p><ObservationTime value={typeof row.recorded_at==='string'?row.recorded_at:null} zone={props.zone}/><Reasons codes={row.reason_codes}/><small className="block"><code>{text(row.alert_id)}</code></small></div>)}
        {data.alerts.status==='AVAILABLE'&&rows(object(data.alerts.facts).items).length===0&&<p>目前沒有保留的研究失敗紀錄</p>}<a href="#health">查看告警與目前元件觀測</a></Diagnostic></Panel>
    <Panel title="操作界線">''')
replace("const [filter,setFilter]=useState('ALL');", "const [filter,setFilter]=useState('ALL'); const [jobFilter,setJobFilter]=useState('ALL');")
replace("  const allowed=rows(policies.value?.data.items).filter(row=>row.kind==='RESEARCH');","  const visibleJobs=rows(jobs.value?.data.items).filter(row=>jobFilter==='ALL'||row.state===jobFilter);\n  const allowed=rows(policies.value?.data.items).filter(row=>row.kind==='RESEARCH');")
replace('<Panel title="研究工作"><p className="hint">', '''<Panel title="研究工作"><label className="compact">此頁工作狀態篩選<select value={jobFilter} onChange={event=>setJobFilter(event.target.value)}>{['ALL','QUEUED','RUNNING','CANCEL_REQUESTED','CANCELED','COMPLETE','BLOCKED','FAILED','EXPIRED'].map(value=><option key={value} value={value}>{value==='ALL'?'全部工作':value+' · 工作狀態'}</option>)}</select></label><p data-testid="research-job-filter-count">此頁符合 {visibleJobs.length} / 已載入 {jobs.value?.data.items.length??0} 筆</p><p className="hint">''')
replace("{page.items.length===0?<p>尚無資料</p>:<div className=\"table-wrap\"><table><thead><tr><th>工作 ID</th>","{visibleJobs.length===0?<p>此頁沒有符合篩選的工作</p>:<div className=\"table-wrap\"><table><thead><tr><th>工作 ID</th>")
replace('{rows(page.items).map(row=><tr key={text(row.run_id)}><td><code>{text(row.run_id)}</code></td><td><Badge value={row.state}', '{visibleJobs.map(row=><tr key={text(row.run_id)}><td><code>{text(row.run_id)}</code></td><td><Badge value={row.state}')
replace('<Reasons codes={data.reason_codes}/></>}</Frame></Panel>\n    <Panel title="告警">', '''<Reasons codes={data.reason_codes}/><p className="hint">程序存活與財務准入分開判定。以下保留各元件的原始心跳時間，不以讀取時間替代。</p>
      {([['control','控制程序觀測'],['research','研究程序觀測'],['runtime','交易程序觀測'],['cloud','雲端程序觀測'],['coordinator','調度程序觀測']] as const).map(([role,title])=><Diagnostic key={role} title={title} value={data.components[role]} zone={props.zone} testId={'health-component-'+role}><ProcessFacts value={data.components[role]} zone={props.zone}/></Diagnostic>)}
      {([['risk','風控觀測'],['execution','執行與核對觀測'],['preflight','Preflight 觀測'],['external_consumer','外部消費者觀測']] as const).map(([key,title])=><Diagnostic key={key} title={title} value={data[key]} zone={props.zone} testId={'health-'+key}/>)}</>}</Frame></Panel>
    <Panel title="告警">''')
replace('<dt>PAPER runtime 設定</dt><dd>{text(data.paper_runtime_enabled)}</dd></dl></>}</Frame></Panel>', '''<dt>PAPER runtime 設定</dt><dd>{text(data.paper_runtime_enabled)}</dd></dl>
      <Diagnostic title="研究資源設定" value={data.resource_limits} zone={props.zone} testId="settings-resource-limits"><WorkerBudget value={data.resource_limits}/></Diagnostic>
      {([['clock_health','時鐘健康'],['backup','備份目的地'],['transport_test','連線測試'],['credential_presence','憑證存在狀態']] as const).map(([key,title])=><Diagnostic key={key} title={title} value={data[key]} zone={props.zone} testId={'settings-'+key}/>)}
      <p className="hint">開啟此頁不會測試外部連線、讀取憑證或執行備份。未觀測的資訊維持未知。</p></>}</Frame></Panel>''')
target=OUT/'ui/src/App.tsx'
if target.exists():raise ValueError('Fresh frontend target required')
target.parent.mkdir(parents=True)
target.write_text(raw,encoding='utf-8',newline='\n')
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
manifest['records'].append(dict(ref='ui/src/App.tsx',before_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),after_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PREPARED_UNAPPLIED',ref='ui/src/App.tsx',after_sha256=manifest['records'][-1]['after_sha256'])))
