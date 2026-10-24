import {useEffect,useRef,useState,type FormEvent,type ReactNode} from 'react';
import {api,commandId,ControlError,type Envelope,type Schema} from './api';
import {approvalBlock,canPauseDeployment,deploymentActivationBlock,healthStatus,actualForwardSeconds,paperExposure,metric,object,progressLabel,reasonText,revision,rows,temporalFacts,text,utcDisplay,type Row} from './model';

type Zone='UTC'|'Asia/Taipei';
type Session=Schema['SessionView'];
type ProductCommand={command_id:string;expected_revision:number}&Row;
type RunCommand=(path:string,body:ProductCommand,method?:string)=>Promise<boolean>;
type Common={refresh:number;reload:()=>void;zone:Zone;session:Session;run:RunCommand;busy:boolean};
const screens=[['overview','總覽'],['research','研究'],['strategies','策略'],['trading','交易'],['health','健康'],['settings','設定']] as const;
const section=()=>screens.some(([key])=>key===location.hash.slice(1))?location.hash.slice(1):'overview';

function useView<T>(path:string,refresh:number,poll=true,enabled=true){
  const [snapshot,setSnapshot]=useState<{path:string;value:Envelope<T>}|null>(null);
  const [failure,setFailure]=useState<{path:string;error:ControlError}|null>(null);
  const [loading,setLoading]=useState(false);
  useEffect(()=>{
    if(!enabled)return; let stopped=false;let active=false;let controller:AbortController|undefined;
    const load=async()=>{
      if(active)return; active=true; controller=new AbortController(); setLoading(true);
      try{const value=await api.view<T>(path,controller.signal);if(!stopped){setSnapshot({path,value});setFailure(null);}}
      catch(error){if(!stopped)setFailure({path,error:error instanceof ControlError?error:new ControlError(0,['VIEW_UNAVAILABLE'])});}
      finally{active=false;if(!stopped)setLoading(false);}
    };
    void load(); const timer=poll?setInterval(()=>{if(document.visibilityState==='visible')void load();},30_000):null;
    return ()=>{stopped=true;controller?.abort();if(timer)clearInterval(timer);};
  },[path,refresh,poll,enabled]);
  return {value:snapshot?.path===path?snapshot.value:undefined,error:failure?.path===path?failure.error:null,loading};
}

function ErrorNotice({error}:{error:ControlError}){
  return <div className="notice error" role="alert"><strong>操作尚未完成</strong>{error.reasons.map(code=><p key={code}>{reasonText(code)} <code>{code}</code></p>)}
    {error.correlation&&<small>關聯 ID：<code>{error.correlation}</code></small>}</div>;
}
function Reasons({codes}:{codes:unknown}){
  const values=Array.isArray(codes)?codes.filter((v):v is string=>typeof v==='string'):[];
  return values.length?<div className="reasons">{values.map(code=><details key={code}><summary><code>{code}</code></summary><p>{reasonText(code)}</p></details>)}</div>:null;
}
function Badge({value}:{value:unknown}){return <span className="badge">{text(value)}</span>;}
function JsonDetail({value,title='原始擁有者證據'}:{value:unknown;title?:string}){
  return <details className="evidence"><summary>{title}</summary><pre>{JSON.stringify(value??null,null,2)}</pre></details>;
}
function Source({meta,zone,stale=false}:{meta:Schema['ViewMetadata'];zone:Zone;stale?:boolean}){
  return <details className="source"><summary>{stale?'上次成功讀取，非目前健康證明':'來源與時點'} · <code>{meta.current_or_last_known}</code> · {utcDisplay(meta.as_of,zone)}</summary>
    <dl><dt>來源</dt><dd><code>{meta.source}</code></dd><dt>資料截至 UTC</dt><dd><code>{meta.as_of??'未知'}</code></dd>
      <dt>讀取 UTC</dt><dd><code>{meta.observed_at}</code></dd><dt>來源新鮮度</dt><dd>{meta.freshness}</dd><dt>命名空間</dt><dd>{meta.namespace}</dd>
      <dt>執行版本</dt><dd><code>{meta.executable_revision??'未提供'}</code> · {meta.worktree}</dd><dt>程式雜湊</dt><dd><code>{meta.implementation_hash}</code></dd>
      <dt>設定雜湊／世代</dt><dd><code>{meta.config_hash}</code> / {meta.config_generation}</dd></dl></details>;
}
function Frame<T>({view,zone,children}:{view:ReturnType<typeof useView<T>>;zone:Zone;children:(data:T)=>ReactNode}){
  return <>{view.error&&<ErrorNotice error={view.error}/>} {!view.value?(view.loading?<p role="status">讀取實際來源…</p>:<p>尚無資料</p>):<>
    {children(view.value.data)}<Source meta={view.value.metadata} zone={zone} stale={!!view.error}/></>}</>;
}
function Panel({title,children}:{title:string;children:ReactNode}){return <section className="panel"><h2>{title}</h2>{children}</section>;}
function Fact({label,value,testId}:{label:string;value:unknown;testId?:string}){return <div className="fact" data-testid={testId}><span>{label}</span><strong>{metric(value)}</strong></div>;}
function Publication({value}:{value:unknown}){
  const publication=object(value);const state=text(publication.state);
  const labels:Record<string,string>={PENDING:'等待發布',LOCAL_STAGED:'僅暫存在本機，尚未取得目的端確認',
    CLOUD_ACKNOWLEDGED:'目的端位元組讀回已確認',UNAVAILABLE:'發布尚未確認；目的端不可用或讀回失敗',CONFLICT:'發布內容衝突；未取得確認'};
  return <><code>{state}</code><small className="block">{labels[state]??'尚未提供發布證據'}</small>
    {publication.artifact_hash!=null&&<small className="block"><code>{text(publication.artifact_hash)}</code></small>}</>;
}
function PageButtons({page,offset,setOffset}:{page:Schema['PageView'];offset:number;setOffset:(value:number)=>void}){
  return <div className="pagination"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-page.limit))}>上一頁</button>
    <small>此頁 {page.items.length} 筆；總筆數 {page.total??'未提供'}</small>
    <button disabled={offset>=100000||(page.total===null?page.items.length<page.limit:offset+page.limit>=page.total)} onClick={()=>setOffset(Math.min(100000,offset+page.limit))}>下一頁</button></div>;
}
function ReportHistory({path,props}:{path:string;props:Common}){
  const [offset,setOffset]=useState(0);
  const history=useView<Schema['PageView']>(`${path}/publications?limit=20&offset=${offset}`,props.refresh);
  return <Panel title="報告交付歷史"><div data-testid="report-publications">
    <p className="hint">確認狀態保留原始報告的目的端位元組讀回結果，不代表雲端目前可連線。排入時間不是目的端確認時間。</p>
    {props.session.namespace==='FIXTURE'&&<p className="hint">LOCAL_COPY_FIXTURE_ONLY：FIXTURE 僅驗證隔離本機複製；真實雲端 NOT_RUN。</p>}
    <Frame view={history} zone={props.zone}>{page=><><Badge value={page.status}/><Reasons codes={page.reason_codes}/>
      {page.items.length===0?<p>{page.status==='NOT_RUN'?'報告尚未產生':'此頁尚無已排入的報告'}</p>:<div className="table-wrap"><table><thead><tr><th>報告操作／原始來源</th><th>交付結果</th><th>原始報告雜湊</th><th>排入時間</th></tr></thead>
      <tbody>{rows(page.items).map(row=><tr key={text(row.operation_id)}><td><code>{text(row.operation_id)}</code><small className="block">{text(row.run_id)}</small>
        {row.run_revision!=null&&<small className="block">Checkpoint {text(row.run_revision)} · 程序世代 {text(row.process_generation)}</small>}</td>
        <td><Publication value={row}/><small className="block">交付嘗試 {text(row.attempts)}</small></td><td><code>{text(row.feedback_hash)}</code></td>
        <td>{utcDisplay(row.queued_at,props.zone)}<small className="block"><code>{text(row.queued_at)}</code></small></td></tr>)}</tbody></table></div>}
      <PageButtons page={page} offset={offset} setOffset={setOffset}/></>}</Frame></div></Panel>;
}
function Temporal({value}:{value:Row}){const facts=temporalFacts(value);return <dl><dt>評估週期</dt><dd>{facts.evaluation}</dd><dt>進場有效期間</dt><dd>{facts.validity}</dd><dt>最長持倉</dt><dd>{facts.maxHold}</dd></dl>;}

type Observation={status:string;source:string;as_of:string|null;checked_at:string;reason_codes:string[];facts:unknown;financial_authority:'NONE'};
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

function Overview(props:Common){
  const view=useView<Schema['OverviewView']>('/api/v1/overview',props.refresh);
  return <Frame view={view} zone={props.zone}>{data=><>
    <div className="hero"><div><span className="eyebrow">本機研究與執行狀態</span><h2>先確認事實，再採取行動。</h2><p>控制介面在線不代表已允許交易；所有執行權限由本機擁有者重新驗證。</p></div><Badge value={data.mode}/></div>
    <div className="facts"><Fact label="排隊研究" value={data.queued_jobs}/><Fact label="執行中研究" value={data.running_jobs}/><Fact label="已實現損益（USDT）" value={data.realized_pnl_usdt} testId="realized-pnl"/><Fact label="未實現損益（USDT）" value={data.unrealized_pnl_usdt}/></div>
    <div className="columns"><Panel title="執行與曝險"><dl><dt>Runtime</dt><dd>{data.runtime_status}</dd><dt>已知曝險數量</dt><dd>{metric(data.exposure_quantity)}</dd><dt>LIVE 核准</dt><dd>{data.live_authorized?'伺服器報告已核准；仍須目前 admission':'未核准'}</dd><dt>雲端交付</dt><dd>{data.cloud_status}</dd></dl><Reasons codes={data.reason_codes}/></Panel>
    <Panel title="生命週期"><p>計數來自目前 E6 登錄，不是收益排名。</p>{data.lifecycle_counts?<dl>{Object.entries(data.lifecycle_counts).map(([state,count])=><div className="pair" key={state}><dt>{state}</dt><dd>{count}</dd></div>)}</dl>:<p>尚無資料</p>}</Panel></div>
    <Panel title="策略、研究與資源觀測"><Diagnostic title="已選策略與版本" value={data.strategy_subjects} zone={props.zone} testId="overview-strategy-subjects">
      <p className="hint">本機選擇與執行中綁定分開核對；不以登錄順序推定目前策略。</p>{rows(object(data.strategy_subjects.facts).items).map(row=><dl key={text(row.strategy_id)+':'+text(row.strategy_version)}><dt>策略／版本</dt><dd><code>{text(row.strategy_id)} / {text(row.strategy_version)}</code></dd><dt>內容雜湊</dt><dd><code>{text(row.content_hash)}</code></dd><dt>關係</dt><dd>本機設定的選擇 <code>{text(row.relationship)}</code></dd></dl>)}</Diagnostic>
      <Diagnostic title="研究狀態與最後階段" value={data.research_stage_counts} zone={props.zone} testId="overview-research-stage-counts">
        <p>來源保留的工作總數：{metric(object(data.research_stage_counts.facts).total_jobs)}；階段是最後持久記錄，並非正在執行的保證。</p>
        {rows(object(data.research_stage_counts.facts).items).map(row=><dl key={text(row.state)+':'+text(row.stage)}><dt>{text(row.state)} / {text(row.stage)}</dt><dd>{text(row.count)} 筆；<ObservationTime value={typeof row.last_observed_at==='string'?row.last_observed_at:null} zone={props.zone}/></dd></dl>)}</Diagnostic>
      <Diagnostic title="研究資源設定" value={data.resource_limits} zone={props.zone} testId="overview-resource-limits"><WorkerBudget value={data.resource_limits}/></Diagnostic>
      <Diagnostic title="保留的研究失敗摘要" value={data.alerts} zone={props.zone} testId="overview-alerts"><p>摘要最多顯示前 5 筆；來源保留總數：{metric(object(data.alerts.facts).total)}。</p>
        {rows(object(data.alerts.facts).items).map(row=><div key={text(row.alert_id)} data-testid="overview-alert-item"><p><code>{text(row.run_id)}</code></p><ObservationTime value={typeof row.recorded_at==='string'?row.recorded_at:null} zone={props.zone}/><Reasons codes={row.reason_codes}/><small className="block"><code>{text(row.alert_id)}</code></small></div>)}
        {data.alerts.status==='AVAILABLE'&&rows(object(data.alerts.facts).items).length===0&&<p>目前沒有保留的研究失敗紀錄</p>}<a href="#health">查看告警與目前元件觀測</a></Diagnostic></Panel>
    <Panel title="操作界線"><p>研究使用固定資料與政策。PAPER 使用隔離模擬帳戶；真實 forward 時間另行累積。LIVE、提供者與資金仍須獨立委任。</p><p>關閉此頁不代表停止 runtime 或平倉。停止新進場也會保留既有部位管理。</p></Panel>
  </>}</Frame>;
}

function Research(props:Common){
  const [submissionId,setSubmissionId]=useState(''); const [policy,setPolicy]=useState(''); const [selectedSubmission,setSelectedSubmission]=useState(''); const [selectedRun,setSelectedRun]=useState('');
  const [filter,setFilter]=useState('ALL'); const [jobFilter,setJobFilter]=useState('ALL'); const [offset,setOffset]=useState(0);const [jobsOffset,setJobsOffset]=useState(0); const [localError,setLocalError]=useState<ControlError|null>(null);
  const overview=useView<Schema['OverviewView']>('/api/v1/overview',props.refresh);
  const submissions=useView<Schema['PageView']>(`/api/v1/submissions?limit=50&offset=${offset}`,props.refresh);
  const jobs=useView<Schema['PageView']>(`/api/v1/research/runs?limit=50&offset=${jobsOffset}`,props.refresh);
  const policies=useView<Schema['PageView']>('/api/v1/policies',props.refresh);
  const detail=useView<Schema['OwnerObjectView']>('/api/v1/submissions/'+encodeURIComponent(selectedSubmission),props.refresh,false,!!selectedSubmission);
  const runDetail=useView<Schema['OwnerObjectView']>('/api/v1/research/runs/'+encodeURIComponent(selectedRun),props.refresh,true,!!selectedRun);
  const visibleJobs=rows(jobs.value?.data.items).filter(row=>jobFilter==='ALL'||row.state===jobFilter);
  const allowed=rows(policies.value?.data.items).filter(row=>row.kind==='RESEARCH');
  const enqueue=async(event:FormEvent)=>{event.preventDefault();setLocalError(null);try{
    const selected=await api.view<Schema['OwnerObjectView']>('/api/v1/submissions/'+encodeURIComponent(submissionId));
    const body:Schema['ResearchEnqueueDTO']={command_id:commandId(),expected_revision:revision(selected.data.revision),submission_id:submissionId,policy_id:policy};
    await props.run('/api/v1/research/runs',body);
  }catch(error){setLocalError(error instanceof ControlError?error:new ControlError(0,['RESOURCE_REVISION_UNAVAILABLE']));}};
  const scan=()=>{const current=overview.value?.data.scan_revision;if(current===null||current===undefined)return;
    void props.run('/api/v1/research/scan',{command_id:commandId(),expected_revision:revision(current)});};
  return <>
    <Panel title="收件匣與研究"><p>收件匣 → 相容性 → 資料集 → 開發回測 → 穩健性 → 密封 OOS → 決策。沒有量測總量的階段不顯示百分比。</p>
      <button disabled={props.busy||overview.value?.data.scan_revision==null} onClick={scan}>掃描收件匣</button><p className="hint">本機快照與登錄不等同遠端雲端已確認交付。未設定收件匣時無法掃描。</p>
      <form onSubmit={event=>void enqueue(event)}><label>提交 ID<input value={submissionId} required maxLength={96} pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*" onChange={e=>setSubmissionId(e.target.value)}/></label>
        <label>研究政策<select aria-label="研究政策" value={policy} required onChange={e=>setPolicy(e.target.value)}><option value="">請選擇已設定政策</option>{allowed.map(row=><option key={text(row.policy_id)} value={text(row.policy_id)}>{text(row.policy_id)}</option>)}</select></label>
        <button disabled={props.busy||!policy||!submissionId} type="submit">排入研究</button></form>{localError&&<ErrorNotice error={localError}/>}</Panel>
    <Panel title="已觀察的提交"><label className="compact">此頁狀態篩選<select value={filter} onChange={e=>setFilter(e.target.value)}>{['ALL','INTAKE_ACCEPTED','BLOCKED','REJECTED','INCOMPLETE_SYNC','EXPIRED','INSUFFICIENT_EVIDENCE','NOT_CONFIGURED'].map(value=><option key={value} value={value}>{value==='ALL'?'全部':value}</option>)}</select></label>
      {props.session.namespace==='FIXTURE'&&<p className="hint">FIXTURE 的目的端確認僅為隔離複製驗證；真實雲端連線另行驗收。</p>}
      <Frame view={submissions} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/>{rows(page.items).filter(row=>filter==='ALL'||row.state===filter||JSON.stringify(row.latest_observation).includes(filter)).length===0?<p>尚無資料</p>:<div className="table-wrap"><table><thead><tr><th>提交</th><th>處置</th><th>雲端發布</th><th>版本</th><th>來源</th></tr></thead><tbody>{rows(page.items).filter(row=>filter==='ALL'||row.state===filter||JSON.stringify(row.latest_observation).includes(filter)).map(row=><tr key={text(row.submission_id)}><td><code>{text(row.submission_id)}</code></td><td><Badge value={row.state}/><Reasons codes={object(row.latest_observation).reason?[object(row.latest_observation).reason]:[]}/></td><td><Publication value={row.publication}/></td><td>{text(row.revision)}</td><td><button onClick={()=>{setSelectedSubmission(text(row.submission_id));setSubmissionId(text(row.submission_id));}}>查看提交</button></td></tr>)}</tbody></table></div>}<PageButtons page={page} offset={offset} setOffset={setOffset}/></>}</Frame>
      {selectedSubmission&&<Frame view={detail} zone={props.zone}>{value=>{const manifest=object(value.payload?.author_manifest);return <div className="detail"><h3>提交 {selectedSubmission}</h3><dl><dt>作者假說</dt><dd>{text(manifest.research_hypothesis)}</dd><dt>宣告類型</dt><dd>{text(manifest.intent_class)}</dd><dt>有效期間（UTC 原文）</dt><dd>{JSON.stringify(manifest.validity??null)}</dd><dt>Manifest 雜湊</dt><dd><code>{text(value.payload?.manifest_hash)}</code></dd></dl><JsonDetail value={value.payload} title="提交、作者 manifest 與發布收據"/></div>;}}</Frame>}
    </Panel>
    <Panel title="研究工作"><label className="compact">此頁工作狀態篩選<select value={jobFilter} onChange={event=>setJobFilter(event.target.value)}>{['ALL','QUEUED','RUNNING','CANCEL_REQUESTED','CANCELED','COMPLETE','BLOCKED','FAILED','EXPIRED'].map(value=><option key={value} value={value}>{value==='ALL'?'全部工作':value+' · 工作狀態'}</option>)}</select></label><p data-testid="research-job-filter-count">此頁符合 {visibleJobs.length} / 已載入 {jobs.value?.data.items.length??0} 筆</p><p className="hint">停止研究採合作取消，保留輸入、已完成階段與 OOS 觀察紀錄。</p><Frame view={jobs} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/>{visibleJobs.length===0?<p>此頁沒有符合篩選的工作</p>:<div className="table-wrap"><table><thead><tr><th>工作 ID</th><th>狀態</th><th>實際階段</th><th>操作</th></tr></thead><tbody>{visibleJobs.map(row=><tr key={text(row.run_id)}><td><code>{text(row.run_id)}</code></td><td><Badge value={row.state}/><Reasons codes={row.reason_codes}/></td><td>{text(row.stage)}<small className="block">{progressLabel(row.completed_count,row.total_count)}</small></td><td><button onClick={()=>setSelectedRun(text(row.run_id))}>查看研究</button><button disabled={props.busy||!['QUEUED','RUNNING','CANCEL_REQUESTED'].includes(text(row.state))} onClick={()=>void props.run('/api/v1/research/runs/'+encodeURIComponent(text(row.run_id))+'/cancel',{command_id:commandId(),expected_revision:revision(row.revision)})}>停止研究</button></td></tr>)}</tbody></table></div>}<PageButtons page={page} offset={jobsOffset} setOffset={setJobsOffset}/></>}</Frame>
      {selectedRun&&<Frame view={runDetail} zone={props.zone}>{value=><div className="detail"><h3>研究 {selectedRun}</h3><Badge value={value.status}/><Reasons codes={value.reason_codes}/><JsonDetail value={value.payload?.evidence} title="樣本、成本、不確定性、試驗與 train / development / sealed OOS 來源"/><JsonDetail value={value.payload} title="階段、輸入與擁有者 lineage"/></div>}</Frame>}</Panel>
    {selectedRun&&<ReportHistory key={selectedRun} path={'/api/v1/research/runs/'+encodeURIComponent(selectedRun)} props={props}/>}
  </>;
}

function FinancialApproval({record,props}:{record:Row;props:Common}){
  const [reference,setReference]=useState('');const [preview,setPreview]=useState<Envelope<Schema['ApprovalPreviewView']>|null>(null);
  const [error,setError]=useState<ControlError|null>(null);const [loading,setLoading]=useState(false);
  const [password,setPassword]=useState('');const [reauth,setReauth]=useState<Session|null>(null);const [confirmed,setConfirmed]=useState(false);
  const requestVersion=useRef(0);useEffect(()=>()=>{requestVersion.current++;},[]);
  const identity=object(record.identity);
  const block=preview&&preview.data.envelope_ref!==reference?'APPROVAL_PREVIEW_SUBJECT_CHANGED':approvalBlock(props.session.namespace,record,preview?.data);
  const reauthenticated=()=>!!reauth?.reauthenticated_until&&Date.parse(reauth.reauthenticated_until)>Date.now();
  const load=async(event:FormEvent)=>{event.preventDefault();const version=++requestVersion.current;setLoading(true);setError(null);setPreview(null);setConfirmed(false);try{
    const query=new URLSearchParams({envelope_ref:reference,expected_revision:String(revision(record.registry_revision))});
    const value=await api.view<Schema['ApprovalPreviewView']>('/api/v1/strategies/'+[text(identity.strategy_id),text(identity.strategy_version)].map(encodeURIComponent).join('/')+'/approval-preview?'+query);
    if(version===requestVersion.current)setPreview(value);
  }catch(cause){if(version===requestVersion.current)setError(cause instanceof ControlError?cause:new ControlError(0,['CURRENT_APPROVAL_PROPOSAL_UNAVAILABLE']));}
    finally{if(version===requestVersion.current)setLoading(false);}};
  const authenticate=async(event:FormEvent)=>{event.preventDefault();const supplied=password;setPassword('');setReauth(null);setConfirmed(false);setError(null);try{
    const current=await api.read<Session>('/api/v1/auth/session');
    setReauth(await api.command<Session>('/api/v1/auth/reauthenticate',{password:supplied,command_id:commandId(),expected_revision:revision(current.revision)}));
  }catch(cause){setError(cause instanceof ControlError?cause:new ControlError(0,['REAUTHENTICATION_REQUIRED']));}};
  const approve=async()=>{
    if(block||!preview||!confirmed)return;
    if(!reauthenticated()){setConfirmed(false);setReauth(null);setError(new ControlError(401,['REAUTHENTICATION_REQUIRED']));return;}
    const exact=preview.data;setConfirmed(false);
    await props.run('/api/v1/approvals',{command_id:commandId(),expected_revision:exact.registry_revision,
      strategy_id:exact.strategy_id,strategy_version:exact.strategy_version,envelope_ref:exact.envelope_ref,
      expected_strategy_hash:exact.strategy_content_hash,expected_envelope_hash:exact.envelope_hash,
      decision:'APPROVE',reason_code:'USER_CONFIRMED'} satisfies Schema['ApprovalDTO']);
  };
  return <div className="financial"><h3>確切版本的財務核准</h3><p>核准只適用於顯示的策略與提案。核准後仍需另外驗證部署；停止新進場會保留既有部位與保護管理。</p>
    <form onSubmit={event=>void load(event)}><label>本機提案參照<input value={reference} required maxLength={96} pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*" onChange={event=>{requestVersion.current++;setReference(event.target.value);setPreview(null);setConfirmed(false);setLoading(false);}}/></label><button disabled={loading||props.busy||!reference} type="submit">讀取核准提案</button></form>
    {preview?<><dl><dt>提案雜湊</dt><dd><code>{preview.data.envelope_hash}</code></dd><dt>執行版本</dt><dd><code>{text(preview.data.release.executable_revision)}</code></dd><dt>建置雜湊</dt><dd><code>{text(preview.data.release.build_hash)}</code></dd><dt>設定雜湊／代次</dt><dd><code>{text(preview.data.release.config_hash)}</code> / {text(preview.data.release.config_generation)}</dd><dt>風險政策雜湊</dt><dd><code>{preview.data.risk_policy_hash}</code></dd><dt>提案資金上限（USDT）</dt><dd>{text(preview.data.envelope.capital_ceiling_usdt)}</dd><dt>每筆風險上限（USDT）</dt><dd>{text(preview.data.envelope.risk_per_trade_usdt)}</dd><dt>單日／累積虧損上限（USDT）</dt><dd>{text(preview.data.envelope.daily_loss_limit_usdt)} / {text(preview.data.envelope.aggregate_loss_limit_usdt)}</dd><dt>帳戶／提供者參照</dt><dd>{text(preview.data.release.account_ref)} / {text(preview.data.release.provider_ref)}</dd><dt>到期（UTC 原文）</dt><dd>{text(preview.data.envelope.expires_at)}</dd></dl>
      <JsonDetail value={preview.data.product_assessment} title="實際樣本、密封 OOS 與不確定性證據參照"/><JsonDetail value={{envelope:preview.data.envelope,release:preview.data.release,risk_policy:preview.data.risk_policy,evidence_ref:preview.data.evidence_ref}} title="完整核准對象"/><Reasons codes={preview.data.reason_codes}/></>:<p>提案資金／風險額度：未提供；不得推定預設資金或槓桿。</p>}
    <form onSubmit={event=>void authenticate(event)}><label>重新驗證密碼<input type="password" autoComplete="current-password" value={password} maxLength={256} required onChange={event=>setPassword(event.target.value)}/></label><button type="submit" disabled={props.busy}>重新驗證身分</button></form>
    {reauth&&<p role="status">重新驗證有效至 {utcDisplay(reauth.reauthenticated_until,props.zone)}；伺服器仍會重新驗證目前提案。</p>}
    <label className="check"><input type="checkbox" checked={confirmed} disabled={!!block||!reauthenticated()||props.busy} onChange={event=>setConfirmed(event.target.checked)}/>我確認策略雜湊、資金與風險提案，以及剩餘曝險後果。</label>
    <button disabled={!!block||!confirmed||!reauthenticated()||props.busy} onClick={()=>void approve()}>確認財務核准</button>{block&&<Reasons codes={[block]}/>} {error&&<ErrorNotice error={error}/>}</div>;
}

function DeploymentControls({record,props}:{record:Row;props:Common}){
  const deployment=object(record.deployment);const envelope=object(deployment.envelope);
  const [evidenceRef,setEvidenceRef]=useState('');const [password,setPassword]=useState('');
  const [reauth,setReauth]=useState<Session|null>(null);const [confirmed,setConfirmed]=useState(false);const [error,setError]=useState<ControlError|null>(null);
  const block=deploymentActivationBlock(props.session.namespace,record,deployment);
  const reauthenticated=()=>!!reauth?.reauthenticated_until&&Date.parse(reauth.reauthenticated_until)>Date.now();
  const authenticate=async(event:FormEvent)=>{event.preventDefault();const supplied=password;setPassword('');setReauth(null);setConfirmed(false);setError(null);try{
    const current=await api.read<Session>('/api/v1/auth/session');
    setReauth(await api.command<Session>('/api/v1/auth/reauthenticate',{password:supplied,command_id:commandId(),expected_revision:revision(current.revision)}));
  }catch(cause){setError(cause instanceof ControlError?cause:new ControlError(0,['REAUTHENTICATION_REQUIRED']));}};
  const activate=async()=>{
    if(block||!confirmed||!evidenceRef)return;
    if(!reauthenticated()){setConfirmed(false);setError(new ControlError(401,['REAUTHENTICATION_REQUIRED']));return;}
    setConfirmed(false);
    await props.run('/api/v1/deployments/'+encodeURIComponent(text(deployment.deployment_id))+'/activate',{
      command_id:commandId(),expected_revision:revision(deployment.registry_revision),strategy_id:text(deployment.strategy_id),
      strategy_version:text(deployment.strategy_version),evidence_ref:evidenceRef} satisfies Schema['DeploymentActivateDTO']);
  };
  const pause=()=>{if(canPauseDeployment(props.session.namespace,record,deployment))void props.run('/api/v1/deployments/'+encodeURIComponent(text(deployment.deployment_id))+'/pause',{
    command_id:commandId(),expected_revision:revision(deployment.registry_revision),strategy_id:text(deployment.strategy_id),strategy_version:text(deployment.strategy_version)} satisfies Schema['DeploymentPauseDTO']);};
  return <div className="financial"><h3>原核准部署與新進場控制</h3><dl><dt>部署 ID</dt><dd><code>{text(deployment.deployment_id)}</code></dd><dt>目前登錄狀態</dt><dd>{text(deployment.lifecycle_state)}</dd><dt>原核准提案雜湊</dt><dd><code>{text(deployment.envelope_hash)}</code></dd><dt>資金／每筆風險上限（USDT）</dt><dd>{text(envelope.capital_ceiling_usdt)} / {text(envelope.risk_per_trade_usdt)}</dd></dl>
    <p>登錄狀態不代表程序正在運作。停止新進場不會取消保護、平倉或終止服務；剩餘曝險仍須由執行服務查回。</p>
    <button disabled={props.busy||!canPauseDeployment(props.session.namespace,record,deployment)} onClick={pause}>停止部署新進場</button>
    <JsonDetail value={deployment} title="原核准、版本與部署來源"/>
    {['APPROVED','DEGRADED'].includes(String(deployment.lifecycle_state))&&<><label>本機啟用證據參照<input value={evidenceRef} maxLength={96} pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*" onChange={event=>{setEvidenceRef(event.target.value);setConfirmed(false);}}/></label>
      <form onSubmit={event=>void authenticate(event)}><label>重新驗證部署密碼<input type="password" autoComplete="current-password" value={password} required maxLength={256} onChange={event=>setPassword(event.target.value)}/></label><button type="submit" disabled={props.busy}>重新驗證部署身分</button></form>
      <label className="check"><input type="checkbox" checked={confirmed} disabled={!!block||!reauthenticated()||!evidenceRef||props.busy} onChange={event=>setConfirmed(event.target.checked)}/>我確認目前版本與原核准額度，並要求伺服器重新驗證啟用條件。</label>
      <button disabled={!!block||!confirmed||!reauthenticated()||!evidenceRef||props.busy} onClick={()=>void activate()}>確認啟用部署</button>{block&&<Reasons codes={[block]}/>}</>}
    {error&&<ErrorNotice error={error}/>}</div>;
}

function Strategies(props:Common){
  const [offset,setOffset]=useState(0); const [subject,setSubject]=useState<[string,string]|null>(null);const [policy,setPolicy]=useState('');
  const list=useView<Schema['PageView']>(`/api/v1/strategies?limit=50&offset=${offset}`,props.refresh);
  const detail=useView<Schema['OwnerObjectView']>('/api/v1/strategies/'+(subject?subject.map(encodeURIComponent).join('/'):'unselected'),props.refresh,false,!!subject);
  const policies=useView<Schema['PageView']>('/api/v1/policies',props.refresh);
  const allowed=rows(policies.value?.data.items).filter(row=>row.kind==='PAPER');
  return <><Panel title="不可變策略與 lineage"><p>每個版本保留內容雜湊與驗證歷史；未測試策略不建立收益排名。</p><Frame view={list} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/>{page.items.length===0?<p>尚無資料</p>:<div className="table-wrap"><table><thead><tr><th>策略／版本</th><th>週期</th><th>生命週期</th><th>內容雜湊</th><th>查看</th></tr></thead><tbody>{rows(page.items).map(row=>{const identity=object(row.identity);return <tr key={text(identity.strategy_id)+text(identity.strategy_version)}><td>{text(identity.strategy_id)}<small className="block">{text(identity.strategy_version)}</small></td><td>{text(row.evaluation_timeframe)}</td><td><Badge value={row.current_lifecycle_state}/></td><td className="hash"><code>{text(row.content_hash)}</code></td><td><button onClick={()=>{setSubject([text(identity.strategy_id),text(identity.strategy_version)]);setPolicy('');}}>查看策略</button></td></tr>;})}</tbody></table></div>}<PageButtons page={page} offset={offset} setOffset={setOffset}/></>}</Frame></Panel>
    {subject&&<Frame view={detail} zone={props.zone}>{value=>{const record=object(value.payload);const identity=object(record.identity);
      return <Panel title={'策略 '+text(identity.strategy_id)+' / '+text(identity.strategy_version)}><Badge value={record.current_lifecycle_state}/><dl><dt>不可變內容雜湊</dt><dd><code>{text(record.content_hash)}</code></dd><dt>登錄版本</dt><dd>{text(value.revision)}</dd><dt>作者提交來源</dt><dd>{text(object(record.author_metadata).submission_id)}</dd><dt>作者假說</dt><dd>{text(object(object(record.author_metadata).manifest).research_hypothesis)}</dd></dl>
        <Temporal value={{...record,submission_validity:object(object(record.author_metadata).manifest).validity}}/><JsonDetail value={record.definition} title="宣告、所需能力與出場規則原文"/><JsonDetail value={record} title="實際登錄與研究 lineage"/>
        <h3>PAPER 授權工作流程</h3><p>只接受目前候選與本機選定的模擬政策。受理不代表 runtime 已啟動，不能累積虛構的 real-forward 時間。</p>
        <form onSubmit={event=>{event.preventDefault();void props.run('/api/v1/paper/runs',{command_id:commandId(),expected_revision:revision(value.revision),strategy_id:text(identity.strategy_id),strategy_version:text(identity.strategy_version),policy_id:policy} satisfies Schema['PaperStartDTO']);}}>
          <label>PAPER 政策<select aria-label="PAPER 政策" value={policy} required onChange={e=>setPolicy(e.target.value)}><option value="">請選擇已設定政策</option>{allowed.map(row=><option value={text(row.policy_id)} key={text(row.policy_id)}>{text(row.policy_id)} · {text(row.mode)}</option>)}</select></label>
          <button type="submit" disabled={props.busy||record.current_lifecycle_state!=='CANDIDATE'||!allowed.some(row=>row.policy_id===policy&&row.workflow_authorized===true)}>開始 PAPER</button></form>
        {record.deployment?<DeploymentControls key={text(object(record.deployment).deployment_id)+':'+text(value.revision)} record={record} props={props}/>:<FinancialApproval key={text(identity.strategy_id)+':'+text(identity.strategy_version)+':'+text(record.content_hash)+':'+text(value.revision)} record={record} props={props}/>}
      </Panel>;}}</Frame>}
  </>;
}

function Trading(props:Common){
  const [offset,setOffset]=useState(0);const [selected,setSelected]=useState('');
  const live=useView<Schema['TradingView']>('/api/v1/trading',props.refresh);
  const list=useView<Schema['PageView']>(`/api/v1/paper/runs?limit=50&offset=${offset}`,props.refresh);
  const detail=useView<Schema['OwnerObjectView']>('/api/v1/paper/runs/'+encodeURIComponent(selected),props.refresh,true,!!selected);
  return <><Panel title="真實執行來源"><Frame view={live} zone={props.zone}>{data=><><Badge value={data.mode}/><Badge value={data.status}/><div className="facts"><Fact label="已實現損益（USDT）" value={data.realized_pnl_usdt}/><Fact label="未實現損益（USDT）" value={data.unrealized_pnl_usdt}/><Fact label="核對狀態" value={data.reconciliation}/></div><p>未知部位不是已平倉；ACK 也不是實際成交。</p><Reasons codes={data.reason_codes}/></>}</Frame></Panel>
    <Panel title="PAPER 隔離模擬帳戶"><p>ACCELERATED_FIXTURE 與 REAL_TIME 分開記錄，不能當作 LIVE。原始數值保持 Decimal 字串。</p><Frame view={list} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/>{page.items.length===0?<p>尚無資料</p>:<div className="table-wrap"><table><thead><tr><th>Run ID</th><th>模擬模式</th><th>程序事實</th><th>新進場</th><th>查看</th></tr></thead><tbody>{rows(page.items).map(row=><tr key={text(row.run_id)}><td><code>{text(row.run_id)}</code></td><td><Badge value={row.mode}/></td><td>{text(row.runtime_status)}<small className="block">世代 {text(row.process_generation)}</small></td><td>{text(row.entry_admission)}</td><td><button onClick={()=>setSelected(text(row.run_id))}>查看 PAPER</button></td></tr>)}</tbody></table></div>}<PageButtons page={page} offset={offset} setOffset={setOffset}/></>}</Frame></Panel>
    {selected&&<Frame view={detail} zone={props.zone}>{value=>{const run=object(value.payload);const metrics=object(run.metrics);const binding=object(run.binding);const funding=object(run.funding);const source=object(funding.latest_source);const impact=object(funding.opportunities);const exposure=paperExposure(run);const history=object(run.history);const audit=object(history.last_observation);
      return <Panel title={'PAPER '+selected}><Badge value={run.mode}/><Badge value={run.runtime_status}/><p data-testid="paper-freshness">{detail.value?.metadata.current_or_last_known} · {utcDisplay(run.broker_observed_at,props.zone)}</p>
        <dl><dt>策略／版本</dt><dd>{text(binding.strategy_id)} / {text(binding.strategy_version)}</dd><dt>策略雜湊</dt><dd><code>{text(binding.strategy_content_hash)}</code></dd><dt>帳戶範圍</dt><dd>{text(run.account_scope)}</dd><dt>新進場</dt><dd data-testid="paper-entry-admission">{text(run.entry_admission)}</dd><dt>核對</dt><dd>{text(run.reconciliation)}</dd></dl>
        <div data-testid="paper-position" className="notice"><strong>已知剩餘曝險</strong><p>數量 {metric(exposure.quantity)} · 狀態 <span>{text(exposure.status)}</span></p><p>{exposure.pendingFlat?'E4 已確認平倉；E5／E6 財務結算尚待完整資金費率證據，不列為已發布關閉交易。':'保護管理來源：實際 E5／E6 部位投影。'}程序目前健康仍須獨立確認；此頁不接管 runtime。</p></div>
        {run.funding!==undefined&&<section data-testid="paper-funding"><h3>Paper 資金費率與結算</h3><Badge value={funding.status}/><p>公開已結算實際費率 × 模擬進場成交名目額；這是 Paper 模型，並非交易所按結算標記價計算的帳單。</p><div className="facts"><Fact label="待結算筆數" value={funding.pending_allocations}/><Fact label="已完成財務結算" value={funding.finalized_allocations}/><Fact label="平倉後等待秒數" value={funding.wall_wait_seconds}/><Fact label="實際觀測等待秒數" value={funding.observed_wait_seconds}/></div><p>等待原因：{text(funding.wait_reason)} · 最新來源：{text(source.status)} · {text(source.reason_code)}</p><p>來源觀測：{utcDisplay(source.observed_at,props.zone)} · 完整至：{utcDisplay(source.complete_through,props.zone)}。缺失費率不當成零；待結算期間暫停下一筆進場。</p><div className="facts"><Fact label="其他風控合格、僅資金費率阻擋" value={impact.valid_blocked}/><Fact label="財務證據不足、風險未確認" value={impact.unresolved_financial}/><Fact label="其他准入條件拒絕" value={impact.other_gate_blocked}/></div><p>每個封閉策略週期最多記錄一次；方向訊號不等於可交易機會，未確認項目不計為錯失交易或獲利。</p><JsonDetail value={run.funding} title="原始資金費率與待結算證據"/></section>}
        {run.history!==undefined&&<section data-testid="paper-history"><h3>歷史證據核驗</h3><p>{audit.status==='HISTORY_VERIFIED_IN_CURRENT_INSTANCE'?'最近一次觀測已完成核驗；目前准入仍須由執行程序重新確認。':audit.status==='HISTORY_AUDIT_FAILED'?'歷史證據核驗失敗；暫停新進場與健康時間累計。':'歷史證據待核驗；暫停新進場與健康時間累計。'}</p><p>既有保護、平倉與待資金費率結算繼續。這是最近觀測，不能作為目前的進場許可。</p><Fact label="最近核驗觀測時間" value={utcDisplay(audit.observed_at,props.zone)}/><JsonDetail value={run.history} title="最近歷史核驗診斷"/></section>}
        <button className="danger" disabled={props.busy||run.entry_admission==='PAUSED'} onClick={()=>void props.run('/api/v1/paper/runs/'+encodeURIComponent(selected)+'/pause',{command_id:commandId(),expected_revision:revision(value.revision)})}>停止新進場</button>
        <p className="hint">這不會平倉、取消保護或停止服務。已在途的成交仍須核對；既有管理繼續由原 runtime 負責。</p><Reasons codes={value.reason_codes}/>
        <h3>委託 ACK 與實際成交</h3><p className="hint">最近最多 {text(run.orders_limit)} 筆委託（總數 {text(run.orders_total)}），每筆顯示最後最多 {text(run.fills_limit)} 筆成交。原始 ACK 時點不會被目前狀態覆寫。</p>
        {rows(run.orders).length===0?<p>尚無資料</p>:<div className="table-wrap"><table><thead><tr><th>Client order ID／角色</th><th>原始 ACK</th><th>目前狀態</th><th>實際成交量</th><th>成交證據</th></tr></thead><tbody>{rows(run.orders).map(row=><tr key={text(row.client_order_id)}><td><code>{text(row.client_order_id)}</code><small className="block">{text(row.role)}</small></td><td>{text(row.original_ack_status)}<small className="block">{utcDisplay(row.original_ack_at,props.zone)}</small></td><td>{text(row.current_status)}<small className="block">{utcDisplay(row.current_observed_at,props.zone)}</small></td><td>{metric(row.actual_filled_quantity)}</td><td><JsonDetail value={row.fills} title={'成交 '+text(row.fill_count)+' 筆'}/></td></tr>)}</tbody></table></div>}
        <h3>已發布結果與觀察</h3><div className="facts"><Fact label="已發布關閉交易" value={run.closed_trades_count}/><Fact label="E3 淨損益（USDT）" value={metrics.net_pnl}/><Fact label="實際 forward 秒數" value={actualForwardSeconds(run.forward_observations)} testId="paper-real-forward-seconds"/></div><p>成本慣例：{text(run.cost_convention)}。成交價已含滑價，未再扣一次；未實現損益未提供時維持未知。</p>
        <JsonDetail value={run.metrics} title="原始 E3 結果"/><JsonDetail value={run.forward_observations} title="真實時間與來源觀察"/><JsonDetail value={{Signal:run.last_signal,TradeIntent:run.last_intent,RiskDecision:run.risk_decision,Position:run.position,Protection:run.protection_request}} title="E2 / E5 / E4 / E6 原始訊號、風險與保護事實"/>
      </Panel>;}}</Frame>}
    {selected&&<ReportHistory key={selected} path={'/api/v1/paper/runs/'+encodeURIComponent(selected)} props={props}/>}
  </>;
}

function Health(props:Common){
  const [alertOffset,setAlertOffset]=useState(0);
  const view=useView<Schema['HealthView']>('/api/v1/health',props.refresh);const alerts=useView<Schema['PageView']>(`/api/v1/alerts?limit=50&offset=${alertOffset}`,props.refresh);
  const capabilities=useView<Schema['CapabilitiesView']>('/api/v1/capabilities',props.refresh);
  const components=[['control','控制服務'],['research','研究工作者'],['runtime','交易程序'],['storage','本機儲存'],['cloud','雲端連線'],['market','市場資料'],['provider','交易提供者']] as const;
  return <><Panel title="個別元件與依賴"><p>HTTP 在線、單元測試通過或缺少 GPU 都不能決定是否可以交易。未觀察的程序健康保持未知。</p><Frame view={view} zone={props.zone}>{data=><><div className="health-grid">{components.map(([name,label])=><Fact key={name} label={label} value={healthStatus(data[name])}/>)}</div><dl><dt>提供者請求</dt><dd>{data.provider_requests}</dd><dt>Runtime LLM 呼叫</dt><dd>{data.runtime_llm_calls}</dd><dt>LIVE 核准</dt><dd>{text(data.live_authorized)}</dd><dt>GPU</dt><dd>非必要；不以缺少 GPU 判定失敗</dd></dl><Reasons codes={data.reason_codes}/><p className="hint">程序存活與財務准入分開判定。以下保留各元件的原始心跳時間，不以讀取時間替代。</p>
      {([['control','控制程序觀測'],['research','研究程序觀測'],['runtime','交易程序觀測'],['cloud','雲端程序觀測'],['coordinator','調度程序觀測']] as const).map(([role,title])=><Diagnostic key={role} title={title} value={data.components[role]} zone={props.zone} testId={'health-component-'+role}><ProcessFacts value={data.components[role]} zone={props.zone}/></Diagnostic>)}
      {([['risk','風控觀測'],['execution','執行與核對觀測'],['preflight','Preflight 觀測'],['external_consumer','外部消費者觀測']] as const).map(([key,title])=><Diagnostic key={key} title={title} value={data[key]} zone={props.zone} testId={'health-'+key}/>)}</>}</Frame></Panel>
    <Panel title="告警"><Frame view={alerts} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/><p>保留的研究失敗紀錄；目前工作者狀態請看上方元件觀測。</p>{page.items.length?<>{rows(page.items).map(alert=><article className="notice error" key={text(alert.alert_id)} data-testid="research-failure-alert"><h3>研究失敗</h3><dl><dt>作業</dt><dd><code>{text(alert.run_id)}</code></dd><dt>來源</dt><dd>研究工作佇列 <code>{text(alert.source)}</code></dd><dt>記錄時間</dt><dd><time dateTime={text(alert.recorded_at)}>{utcDisplay(alert.recorded_at,props.zone)}</time></dd><dt>狀態</dt><dd>{text(alert.state)}</dd><dt>告警識別</dt><dd><code>{text(alert.alert_id)}</code></dd></dl><Reasons codes={alert.reason_codes}/></article>)}<JsonDetail value={page.items} title="實際告警原文"/></>:<p>{page.status==='AVAILABLE'?'目前沒有研究失敗紀錄':'尚無資料'}</p>}{page.status==='AVAILABLE'&&<PageButtons page={page} offset={alertOffset} setOffset={setAlertOffset}/>}</>}</Frame></Panel>
    <Panel title="能力與缺口"><Frame view={capabilities} zone={props.zone}>{value=><><p>快照 <code>{value.snapshot_hash}</code></p><p>IMPLEMENTED、reference 驗證、PAPER 與 provider 可用性是不同證據；不互相替代。</p><div className="table-wrap"><table><thead><tr><th>能力</th><th>版本</th><th>已實作</th><th>Reference</th><th>PAPER</th><th>Provider</th></tr></thead><tbody>{rows(value.snapshot.capabilities).map(row=><tr key={text(row.capability_id)}><td>{text(row.capability_id)}</td><td>{text(row.semantic_version)}</td><td>{text(row.IMPLEMENTED)}</td><td>{text(row.VERIFIED_REFERENCE)}</td><td>{text(row.PAPER_AVAILABLE)}</td><td>{text(row.LIVE_PROVIDER_AVAILABLE)}</td></tr>)}</tbody></table></div><JsonDetail value={value.snapshot} title="確切能力、時間框架、warmup 與驗證來源"/></>}</Frame></Panel></>;
}

function Settings(props:Common&{setZone:(value:Zone)=>void}){
  const view=useView<Schema['SettingsView']>('/api/v1/settings',props.refresh,false);const datasets=useView<Schema['PageView']>('/api/v1/datasets',props.refresh,false);const policies=useView<Schema['PageView']>('/api/v1/policies',props.refresh,false);
  const [zone,setZone]=useState<Zone>('UTC');const [interval,setIntervalValue]=useState('');const [base,setBase]=useState<number|null>(null);
  useEffect(()=>{if(view.value){setZone(view.value.data.display_timezone);setIntervalValue(String(view.value.data.scan_interval));setBase(view.value.data.revision);}},[view.value]);
  const save=async(event:FormEvent)=>{event.preventDefault();if(base===null)return;
    if(await props.run('/api/v1/settings/non-secret',{command_id:commandId(),expected_revision:revision(base),display_timezone:zone,scan_interval:Number(interval)} satisfies Schema['SettingsDTO'],'PUT'))props.setZone(zone);
  };
  return <><Panel title="顯示與掃描設定"><Frame view={view} zone={props.zone}>{data=><><form onSubmit={event=>void save(event)}><label>顯示時區<select value={zone} onChange={e=>setZone(e.target.value as Zone)}><option value="UTC">UTC</option><option value="Asia/Taipei">Asia/Taipei（UTC+08:00）</option></select></label><label>掃描間隔（秒）<input type="number" min={1} max={86400} step={1} required value={interval} onChange={e=>setIntervalValue(e.target.value)}/></label><button disabled={props.busy||base===null} type="submit">儲存顯示設定</button></form><p className="hint">顯示偏好不更動 UTC 原始資料或金融政策。背景更新不會替您重新核准過期的編輯版本。</p><dl><dt>本機資料根</dt><dd><code>{data.local_data_root}</code></dd><dt>雲端根</dt><dd><code>{data.cloud_root??'NOT_CONNECTED'}</code></dd><dt>Canonical SQLite</dt><dd><code>{data.database_path}</code></dd><dt>控制位址</dt><dd>{data.control_api_host}:{data.control_api_port}</dd><dt>診斷模式</dt><dd>{text(data.diagnostic_only)}</dd><dt>PAPER runtime 設定</dt><dd>{text(data.paper_runtime_enabled)}</dd></dl>
      <Diagnostic title="研究資源設定" value={data.resource_limits} zone={props.zone} testId="settings-resource-limits"><WorkerBudget value={data.resource_limits}/></Diagnostic>
      {([['clock_health','時鐘健康'],['backup','備份目的地'],['transport_test','連線測試'],['credential_presence','憑證存在狀態']] as const).map(([key,title])=><Diagnostic key={key} title={title} value={data[key]} zone={props.zone} testId={'settings-'+key}/>)}
      <p className="hint">開啟此頁不會測試外部連線、讀取憑證或執行備份。未觀測的資訊維持未知。</p></>}</Frame></Panel>
    <Panel title="首次設定與委任"><p>管理者須在本機首次設定中建立；沒有預設密碼，也沒有 HTTP 註冊入口。</p><dl><dt>遠端存取</dt><dd>本機 loopback；透過已建立的 SSH tunnel 存取。直接 LAN 委任尚未提供。</dd><dt>提供者憑證</dt><dd>介面不讀取或顯示秘密值。實際提供者尚未委任。</dd><dt>程序與資源預算</dt><dd>需在本機完整設定與原生程序診斷中確認；瀏覽器不管理程序樹。</dd><dt>備份與服務停止</dt><dd>需由本機一致性備份／受管理關機流程處理。停止新進場不代表可以直接終止服務。</dd></dl></Panel>
    <Panel title="已選定資料集"><Frame view={datasets} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/>{page.items.length?<JsonDetail value={page.items} title="資料集版本、hash、cutoff 與 MANIFEST_ONLY 範圍"/>:<p>尚無資料</p>}</>}</Frame></Panel>
    <Panel title="已選定政策"><Frame view={policies} zone={props.zone}>{page=><><Reasons codes={page.reason_codes}/>{page.items.length?<JsonDetail value={page.items} title="本機政策識別與不可變 hash"/>:<p>尚無資料</p>}</>}</Frame></Panel></>;
}

export function App(){
  const [session,setSession]=useState<Session|null>(null);const [authStatus,setAuthStatus]=useState<Schema['AuthStatusView']|null>(null);const [boot,setBoot]=useState(true);
  const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [authError,setAuthError]=useState<ControlError|null>(null);const [screen,setScreen]=useState(section);
  const [refresh,setRefresh]=useState(0);const [zone,setZone]=useState<Zone>('UTC');const [busy,setBusy]=useState(false);const [flash,setFlash]=useState<Schema['CommandReceipt']|ControlError|null>(null);
  const [pending,setPending]=useState<{path:string;body:ProductCommand;method:string}[]>([]);
  const reload=()=>setRefresh(value=>value+1);
  useEffect(()=>{const change=()=>setScreen(section());window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change);},[]);
  useEffect(()=>{const invalidated=()=>{if(session){setSession(null);setAuthError(new ControlError(401,['AUTHORIZATION_REQUIRED']));}};window.addEventListener('r7-session-expired',invalidated);return()=>window.removeEventListener('r7-session-expired',invalidated);},[session]);
  useEffect(()=>{void (async()=>{try{setAuthStatus(await api.read('/api/v1/auth/status'));setSession(await api.read('/api/v1/auth/session'));}catch(error){if(error instanceof ControlError&&error.status!==401)setAuthError(error);}finally{setBoot(false);}})();},[]);
  useEffect(()=>{if(session)void api.view<Schema['SettingsView']>('/api/v1/settings').then(value=>setZone(value.data.display_timezone)).catch(()=>{});},[session]);
  const login=async(event:FormEvent)=>{event.preventDefault();setBusy(true);setAuthError(null);const supplied=password;setPassword('');try{
    await api.login({username,password:supplied,command_id:commandId(),expected_revision:0});setSession(await api.read('/api/v1/auth/session'));setScreen('overview');location.hash='overview';
  }catch(error){setAuthError(error instanceof ControlError?error:new ControlError(0,['AUTHORIZATION_REQUIRED']));}finally{setBusy(false);}};
  const run:RunCommand=async(path,body,method='POST')=>{
    if(busy)return false;setBusy(true);setFlash(null);try{
      const receipt=await api.command(path,body,method);
      if(receipt.command_id!==body.command_id||!['COMPLETE','QUEUED','PAUSED'].includes(receipt.status))throw new ControlError(0,['RECEIPT_UNVERIFIED']);
      setFlash(receipt);setPending(values=>values.filter(value=>value.body.command_id!==body.command_id));reload();return true;
    }catch(error){const failure=error instanceof ControlError?error:new ControlError(0,['RESPONSE_UNKNOWN']);setFlash(failure);
      const uncertain=failure.status===0||failure.status===500||failure.reasons.some(value=>['COMMAND_IN_PROGRESS','PAPER_CONTROL_UNAVAILABLE'].includes(value));
      if(uncertain)setPending(values=>values.some(value=>value.body.command_id===body.command_id)?values:[...values,{path,body,method}]);
      else setPending(values=>values.filter(value=>value.body.command_id!==body.command_id));return false;
    }finally{setBusy(false);}
  };
  const logout=async()=>{if(!session)return;setBusy(true);try{const current=await api.read<Session>('/api/v1/auth/session');await api.command('/api/v1/auth/logout',{command_id:commandId(),expected_revision:current.revision});setSession(null);setFlash(null);}catch(error){setAuthError(error instanceof ControlError?error:new ControlError(0,['AUTHORIZATION_REQUIRED']));}finally{setBusy(false);}};
  const common:Common|undefined=session?{refresh,reload,zone,session,run,busy}:undefined;
  const name=screens.find(([key])=>key===screen)?.[1]??'總覽';
  return <div className={session?'layout':'login-layout'}>
    {session&&<aside><a className="brand" href="#overview"><b>R7</b><span>本機控制中心<small>RESEARCH / OPERATIONS</small></span></a><nav aria-label="主要頁面">{screens.map(([key,label])=><a key={key} href={'#'+key} aria-label={label} aria-current={key===screen?'page':undefined}><span>{label}</span><small>{key.toUpperCase()}</small></a>)}</nav><div className="sidebar-note">持久化與執行管理在本機服務。<br/>瀏覽器不是 runtime 擁有者。</div></aside>}
    <main><header><div><span className="eyebrow">PROJECT R7 · LOCAL CONTROL</span><h1>{session?name:'登入本機控制中心'}</h1></div>{session&&<div className="toolbar"><span>{session.actor} · {zone}</span><button onClick={reload}>重新整理</button><button disabled={busy} onClick={()=>void logout()}>登出</button></div>}</header>
      {(session?.namespace??authStatus?.namespace)==='FIXTURE'&&<div className="fixture-banner" data-testid="fixture-banner"><strong>FIXTURE 測試命名空間</strong><span>隔離模擬資料 · 不代表真實 forward、提供者操作或資金核准</span></div>}
      {boot?<p role="status">讀取登入狀態…</p>:!session?<section className="login panel"><div className="login-mark">R7</div><h2>您的本機研究工作站</h2><p>資料留在本機。登入後查看實際策略、證據與執行狀態。</p>{authStatus&&!authStatus.configured?<div className="notice">尚未建立管理者。請先完成本機首次設定；沒有預設密碼。</div>:<form onSubmit={event=>void login(event)}><label>帳號<input value={username} autoComplete="username" maxLength={96} required onChange={e=>setUsername(e.target.value)}/></label><label>密碼<input type="password" autoComplete="current-password" value={password} maxLength={256} required onChange={e=>setPassword(e.target.value)}/></label><button className="primary" disabled={busy} type="submit">登入</button></form>}{authError&&<ErrorNotice error={authError}/>}<small>僅限 loopback／既有 SSH tunnel。登入不授予交易權限。</small></section>:<>
        {flash instanceof ControlError?<ErrorNotice error={flash}/>:flash&&<div className="notice" role="status"><strong>伺服器收據：{flash.status}</strong><p>命令 <code>{flash.command_id}</code> · 效果 <code>{flash.effect_ref??'未提供'}</code> · 資源版本 {flash.resource_revision}</p><Reasons codes={flash.reason_codes}/></div>}
        {pending.length>0&&<div className="notice"><strong>待核對原命令</strong><p>原操作可能已生效。重試保留命令 ID、內容與原版本，不建立替代操作。</p>{pending.map(item=><p key={item.body.command_id}><code>{item.body.command_id}</code> <button disabled={busy} onClick={()=>void run(item.path,item.body,item.method)}>使用原命令重試</button></p>)}</div>}
        {common&&(screen==='overview'?<Overview {...common}/>:screen==='research'?<Research {...common}/>:screen==='strategies'?<Strategies {...common}/>:screen==='trading'?<Trading {...common}/>:screen==='health'?<Health {...common}/>:<Settings {...common} setZone={setZone}/>)}
      </>}<footer>R7 v0.2 · 所有來源時點使用 UTC 儲存 · 實際模式、權限與資料缺口以擁有者證據為準</footer></main>
  </div>;
}
