import {test,expect,type Page} from '@playwright/test';
import path from 'node:path';
import {startPaperViaUI} from '../../tools/paper_start_browser.mjs';

const origins={empty:'http://127.0.0.1:8766',research:'http://127.0.0.1:8767',paper:'http://127.0.0.1:8768',protected:'http://127.0.0.1:8769',temporal:'http://127.0.0.1:8770',approval:'http://127.0.0.1:8771',deployment:'http://127.0.0.1:8772',failed:'http://127.0.0.1:8773',delivery:'http://127.0.0.1:8774','report-research':'http://127.0.0.1:8775','report-paper':'http://127.0.0.1:8776',versions:'http://127.0.0.1:8777'};
const artifacts=process.env.R7_BROWSER_ARTIFACT_ROOT?path.resolve(process.env.R7_BROWSER_ARTIFACT_ROOT):path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser');
const password='explicit-test-only-password-123';
async function login(page:Page,profile:keyof typeof origins){
  await page.goto(origins[profile]);
  await page.getByLabel('帳號',{exact:true}).fill('local-owner');
  await page.getByLabel('密碼',{exact:true}).fill(password);
  await page.getByRole('button',{name:'登入',exact:true}).click();
  await expect(page.getByRole('heading',{name:'總覽',exact:true})).toBeVisible();
}

test('research report history displays actual owner delivery and original hashes',async({page})=>{
  const origin=origins['report-research'];const remote:string[]=[];
  page.on('request',request=>{if(!request.url().startsWith(origin))remote.push(request.url());});
  await login(page,'report-research');await page.getByRole('link',{name:'研究',exact:true}).click();
  const jobs=await (await page.request.get(origin+'/api/v1/research/runs')).json();
  expect(jobs.data.items).toHaveLength(3);const states:string[]=[];
  for(const job of jobs.data.items){
    const response=await page.request.get(origin+'/api/v1/research/runs/'+job.run_id+'/publications');expect(response.status()).toBe(200);
    const report=(await response.json()).data.items[0];states.push(report.state);
    expect(report.run_id).toBe(job.owner_run_id);expect(report.run_id).not.toBe(job.run_id);
    await page.getByRole('row').filter({hasText:job.run_id}).getByRole('button',{name:'查看研究',exact:true}).click();
    const history=page.getByTestId('report-publications');await expect(history).toContainText('LOCAL_COPY_FIXTURE_ONLY');
    const row=history.getByRole('row').filter({hasText:report.operation_id});
    for(const key of ['state','artifact_hash','feedback_hash','queued_at','run_id'])await expect(row).toContainText(report[key]);
    await expect(history).toContainText('不代表雲端目前可連線');
    await page.screenshot({path:path.join(artifacts,'research-report-'+report.state+'.png'),fullPage:true});
  }
  expect(states.sort()).toEqual(['CLOUD_ACKNOWLEDGED','CONFLICT','LOCAL_STAGED']);expect(remote).toEqual([]);
});

test('paper report history preserves actual checkpoint producer and delivery states',async({page})=>{
  const origin=origins['report-paper'];await login(page,'report-paper');
  await page.getByRole('link',{name:'交易',exact:true}).click();
  const runs=await (await page.request.get(origin+'/api/v1/paper/runs')).json();expect(runs.data.items).toHaveLength(1);
  const run=runs.data.items[0];const response=await page.request.get(origin+'/api/v1/paper/runs/'+run.run_id+'/publications');
  expect(response.status()).toBe(200);const reports=(await response.json()).data.items;expect(reports).toHaveLength(3);
  await page.getByRole('button',{name:'查看 PAPER',exact:true}).click();const history=page.getByTestId('report-publications');
  await expect(history).toContainText('LOCAL_COPY_FIXTURE_ONLY');
  for(const report of reports){
    const row=history.getByRole('row').filter({hasText:report.operation_id});
    for(const key of ['state','artifact_hash','feedback_hash','queued_at'])await expect(row).toContainText(report[key]);
    await expect(row).toContainText('Checkpoint '+report.run_revision+' · 程序世代 '+report.process_generation);
  }
  expect(reports.map((row:any)=>row.state).sort()).toEqual(['CLOUD_ACKNOWLEDGED','CONFLICT','LOCAL_STAGED']);
  await page.screenshot({path:path.join(artifacts,'paper-report-history.png'),fullPage:true});
});

test('empty views use actual nulls, Traditional Chinese and persistent fixture labels',async({page})=>{
  const remote:string[]=[];
  page.on('request',request=>{if(!request.url().startsWith(origins.empty))remote.push(request.url());});
  await login(page,'empty');
  await expect(page.getByTestId('fixture-banner')).toContainText('FIXTURE');
  await expect(page.getByTestId('realized-pnl')).toContainText('未提供');
  await page.screenshot({path:path.join(artifacts,'overview.png'),fullPage:true});
  await page.setViewportSize({width:1024,height:768});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  for(const screen of ['研究','策略','交易','健康','設定']){
    await page.getByRole('link',{name:screen,exact:true}).click();
    await expect(page.getByRole('heading',{name:screen,exact:true})).toBeVisible();
    await expect(page.getByTestId('fixture-banner')).toBeVisible();
  }
  await page.getByRole('link',{name:'健康',exact:true}).click();
  await expect(page.getByText('控制服務',{exact:true})).toBeVisible();
  await expect(page.getByText('控制介面可連線',{exact:true})).toBeVisible();
  await expect(page.getByText('尚未設定',{exact:true}).first()).toBeVisible();
  await page.screenshot({path:path.join(artifacts,'health.png'),fullPage:true});
  await page.getByRole('link',{name:'研究',exact:true}).click();
  await expect(page.getByText('尚無資料',{exact:true}).first()).toBeVisible();
  expect(remote).toEqual([]);
});

test('actual inbox scan, asynchronous enqueue and cooperative cancellation',async({page})=>{
  await login(page,'research'); await page.getByRole('link',{name:'研究',exact:true}).click();
  await page.getByRole('button',{name:'掃描收件匣',exact:true}).click();
  await expect(page.getByText('fixture-product',{exact:true}).first()).toBeVisible();
  await page.getByLabel('提交 ID',{exact:true}).fill('fixture-product');
  await page.getByLabel('研究政策',{exact:true}).selectOption('selected-fixture');
  await page.getByRole('button',{name:'排入研究',exact:true}).click();
  await expect(page.getByText('QUEUED',{exact:true}).first()).toBeVisible();
  await page.getByRole('button',{name:'停止研究',exact:true}).first().click();
  await expect(page.getByText('CANCELED',{exact:true}).first()).toBeVisible();
  const jobs=await page.request.get(origins.research+'/api/v1/research/runs');
  const actual=(await jobs.json()).data.items[0];expect(actual.state).toBe('CANCELED');
  const filter=page.getByRole('combobox',{name:'此頁工作狀態篩選',exact:true});
  await filter.selectOption('CANCELED');
  await expect(page.getByRole('row').filter({hasText:actual.run_id})).toHaveCount(1);
  await expect(page.getByTestId('research-job-filter-count')).toHaveText('此頁符合 1 / 已載入 1 筆');
  for(const state of ['QUEUED','CANCEL_REQUESTED']){
    await filter.selectOption(state);await expect(page.getByRole('row').filter({hasText:actual.run_id})).toHaveCount(0);
    await expect(page.getByText('此頁沒有符合篩選的工作',{exact:true})).toBeVisible();
  }
  await filter.selectOption('ALL');await expect(page.getByRole('row').filter({hasText:actual.run_id})).toHaveCount(1);
  const overviewRead=page.waitForResponse(r=>r.url()===origins.research+'/api/v1/overview'&&r.request().method()==='GET');
  await page.getByRole('link',{name:'總覽',exact:true}).click();const overview=(await (await overviewRead).json()).data;
  await assertDiagnostic(page,'overview-research-stage-counts',overview.research_stage_counts);
  const stages=page.getByTestId('overview-research-stage-counts');
  expect(overview.research_stage_counts.facts.items.some((row:any)=>row.state==='CANCELED')).toBe(true);
  for(const row of overview.research_stage_counts.facts.items){
    const label=stages.locator('dt').filter({hasText:new RegExp('^'+row.state+' / '+(row.stage??'未提供')+'$')});
    const fact=label.locator('xpath=following-sibling::dd[1]');await expect(fact).toContainText(String(row.count)+' 筆');
    await expect(fact.locator('time')).toHaveAttribute('datetime',row.last_observed_at);
  }
});

test('health shows a genuine owner failure with its original time and safe reason',async({page})=>{
  const overviewRead=page.waitForResponse(r=>r.url()===origins.failed+'/api/v1/overview'&&r.request().method()==='GET');
  await login(page,'failed');const overview=(await (await overviewRead).json()).data;
  const summary=page.getByTestId('overview-alerts');expect(overview.alerts.facts.items).toHaveLength(1);
  for(const original of overview.alerts.facts.items){
    const item=summary.getByTestId('overview-alert-item').filter({hasText:original.alert_id});
    await expect(item).toContainText(original.run_id);await expect(item.locator('time')).toHaveAttribute('datetime',original.recorded_at);
    for(const code of original.reason_codes)await expect(item).toContainText(code);
  }
  await assertDiagnostic(page,'overview-alerts',overview.alerts);
  await page.getByRole('link',{name:'健康',exact:true}).click();
  const response=await page.request.get(origins.failed+'/api/v1/alerts?limit=50&offset=0');
  expect(response.status()).toBe(200);
  const body=await response.json();
  expect(body.data.status).toBe('AVAILABLE');expect(body.data.total).toBe(1);
  const actual=body.data.items[0];
  expect(actual.recorded_at).not.toBe(body.metadata.observed_at);
  expect(actual.reason_codes).toEqual(['RuntimeError']);
  const card=page.getByTestId('research-failure-alert');
  await expect(card).toHaveCount(1);
  for(const value of [actual.run_id,actual.alert_id,actual.source,'FAILED','RuntimeError'])await expect(card).toContainText(value);
  await expect(card.locator('time')).toHaveAttribute('datetime',actual.recorded_at);
  await expect(page.getByText('保留的研究失敗紀錄；目前工作者狀態請看上方元件觀測。',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'上一頁',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'下一頁',exact:true})).toBeDisabled();
  expect(await page.locator('body').innerText()).not.toContain('SOURCE_ONLY_PRIVATE_BROWSER_CANARY');
  await page.screenshot({path:path.join(artifacts,'research-failure-history.png'),fullPage:true});
});

test('health distinguishes actual supervised control from an available queue without a worker',async({page})=>{
  await login(page,'research');
  const consumed=page.waitForResponse(r=>r.url()===origins.research+'/api/v1/health'&&r.request().method()==='GET');
  await page.getByRole('link',{name:'健康',exact:true}).click();
  const consumedBody=await (await consumed).json();
  await expect(page.getByText('最近收到程序心跳',{exact:true})).toBeVisible();
  await expect(page.getByText('工作佇列可用；工作者尚未啟動',{exact:true})).toBeVisible();
  const response=await page.request.get(origins.research+'/api/v1/health');
  expect(response.status()).toBe(200);
  const actual=(await response.json()).data;
  expect(actual.control).toBe('PROCESS_RECENT_HEARTBEAT');
  expect(actual.research).toBe('QUEUE_AVAILABLE_WORKER_NOT_STARTED');
  expect(actual.live_authorized).toBe(false);
  await assertDiagnostic(page,'health-component-control',consumedBody.data.components.control);
  expect(consumedBody.data.components.control.as_of).toBe(consumedBody.data.components.control.facts.heartbeat_at);
  await page.screenshot({path:path.join(artifacts,'supervised-health.png'),fullPage:true});
});

test('delivery separates local staging from actual byte-verified fixture-copy acknowledgment',async({page})=>{
  await login(page,'delivery');await page.getByRole('link',{name:'研究',exact:true}).click();
  const response=await page.request.get(origins.delivery+'/api/v1/submissions');expect(response.status()).toBe(200);
  const items=(await response.json()).data.items;
  const staged=items.find((row:any)=>row.publication.state==='LOCAL_STAGED');
  const acknowledged=items.find((row:any)=>row.publication.state==='CLOUD_ACKNOWLEDGED');
  const denied=items.find((row:any)=>['UNAVAILABLE','CONFLICT'].includes(row.publication.state));
  expect(items).toHaveLength(3);expect(staged).toBeTruthy();expect(acknowledged).toBeTruthy();expect(denied).toBeTruthy();
  const rowFor=(item:any)=>page.getByRole('row').filter({hasText:item.submission_id});
  await expect(rowFor(staged)).toContainText('僅暫存在本機，尚未取得目的端確認');
  await expect(rowFor(staged)).toContainText(staged.publication.artifact_hash);
  await expect(rowFor(acknowledged)).toContainText('目的端位元組讀回已確認');
  await expect(rowFor(acknowledged)).toContainText(acknowledged.publication.artifact_hash);
  await expect(rowFor(denied)).toContainText(denied.publication.state);
  await expect(rowFor(denied)).not.toContainText('目的端位元組讀回已確認');
  await expect(page.getByText('FIXTURE 的目的端確認僅為隔離複製驗證；真實雲端連線另行驗收。',{exact:true})).toBeVisible();
  await page.screenshot({path:path.join(artifacts,'cloud-delivery-states.png'),fullPage:true});
});

test('actual candidate PAPER start and pause retain run identity and show unavailable metrics',async({page})=>{
  const overviewRead=page.waitForResponse(r=>r.url()===origins.paper+'/api/v1/overview'&&r.request().method()==='GET');
  await login(page,'paper');const overview=(await (await overviewRead).json()).data;
  expect(overview.strategy_subjects.status).toBe('AVAILABLE');expect(overview.strategy_subjects.facts.items).toHaveLength(1);
  const selected=overview.strategy_subjects.facts.items[0];expect(selected.relationship).toBe('CONFIGURED_SELECTION');
  const subject=page.getByTestId('overview-strategy-subjects');
  const identity=subject.locator('dt').filter({hasText:/^策略／版本$/}).locator('xpath=following-sibling::dd[1]');
  await expect(identity).toHaveText(selected.strategy_id+' / '+selected.strategy_version);
  const content=subject.locator('dt').filter({hasText:/^內容雜湊$/}).locator('xpath=following-sibling::dd[1]');
  await expect(content).toHaveText(selected.content_hash);
  await assertDiagnostic(page,'overview-strategy-subjects',overview.strategy_subjects);
  await page.getByRole('link',{name:'策略',exact:true}).click();
  await page.getByRole('button',{name:'查看策略',exact:true}).first().click();
  await page.getByLabel('PAPER 政策',{exact:true}).selectOption('fixture-paper-policy');
  // Source-only response-loss injection: the real owner completes first.
  // Native acceptance never installs this route handler.
  const attempts:string[]=[];let originalReceipt:Record<string,unknown>|null=null;
  await page.route(origins.paper+'/api/v1/paper/runs',async route=>{
    if(route.request().method()!=='POST')return route.continue();
    attempts.push(route.request().postData()!);
    if(attempts.length!==1)return route.continue();
    const actual=await route.fetch({maxRedirects:0,maxRetries:0});expect(actual.status()).toBe(200);
    originalReceipt=await actual.json();await route.abort('failed');
  });
  const recovery=await startPaperViaUI(page,origins.paper,expect);
  expect(recovery.recovery).toBe('ORIGINAL_COMMAND_RETRY');
  expect(attempts).toHaveLength(2);expect(attempts[1]).toBe(attempts[0]);
  expect(recovery.receipt).toEqual(originalReceipt);
  await page.getByRole('link',{name:'交易',exact:true}).click();
  await expect(page.getByText('ACCELERATED_FIXTURE',{exact:true}).first()).toBeVisible();
  await page.getByRole('button',{name:'查看 PAPER',exact:true}).first().click();
  await expect(page.getByText('NOT_STARTED',{exact:true}).first()).toBeVisible();
  await page.getByRole('button',{name:'停止新進場',exact:true}).click();
  await expect(page.getByTestId('paper-entry-admission')).toContainText('PAUSED');
  const runs=(await (await page.request.get(origins.paper+'/api/v1/paper/runs')).json()).data.items;
  expect(runs).toHaveLength(1); expect(runs[0].process_generation).toBe(0); expect(runs[0].metrics).toBeNull();
  expect(recovery.receipt.effect_ref).toBe('paper:'+runs[0].run_id);
});

test('protected owner facts distinguish ACK/fill, remaining exposure and as-of state',async({page})=>{
  await login(page,'protected'); await page.getByRole('link',{name:'交易',exact:true}).click();
  await page.getByRole('button',{name:'查看 PAPER',exact:true}).first().click();
  await expect(page.getByTestId('paper-position')).toContainText('0.001');
  await expect(page.getByText('OPEN_PROTECTED',{exact:true}).first()).toBeVisible();
  await expect(page.getByText('委託 ACK 與實際成交',{exact:true})).toBeVisible();
  await expect(page.getByTestId('paper-freshness')).toContainText('LAST_KNOWN_GOOD');
  const observed=(await (await page.request.get(origins.protected+'/api/v1/paper/runs')).json()).data.items;
  const original=observed[0];
  const evidence=page.locator('details.evidence').filter({has:page.getByText('E2 / E5 / E4 / E6 原始訊號、風險與保護事實',{exact:true})});
  await evidence.locator('summary').click();
  expect(JSON.parse(await evidence.locator('pre').innerText())).toEqual({Signal:original.last_signal,TradeIntent:original.last_intent,RiskDecision:original.risk_decision,Position:original.position,Protection:original.protection_request});
  const metrics=page.locator('details.evidence').filter({has:page.getByText('原始 E3 結果',{exact:true})});
  await metrics.locator('summary').click();expect(JSON.parse(await metrics.locator('pre').innerText())).toEqual(original.metrics);
  expect(observed[0].forward_observations.real_elapsed_ns).toBe(0);
  await expect(page.getByTestId('paper-real-forward-seconds').locator('strong')).toHaveText('0');
  await page.getByRole('button',{name:'停止新進場',exact:true}).click();
  await expect(page.getByTestId('paper-position')).toContainText('0.001');
  const runs=(await (await page.request.get(origins.protected+'/api/v1/paper/runs')).json()).data.items;
  expect(runs[0].position.actual_quantity).toBe('0.001'); expect(runs[0].process_generation).toBe(1);
  await page.getByRole('heading',{name:'交易',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(artifacts,'protected-paper.png'),fullPage:true});
});

test('stale settings show real backend conflict and keyboard form remains usable',async({page})=>{
  await login(page,'empty'); await page.getByRole('link',{name:'設定',exact:true}).click();
  const csrf=await page.evaluate(()=>document.cookie.split('; ').find(s=>s.startsWith('r7_csrf='))?.slice(8));
  const settings=(await (await page.request.get(origins.empty+'/api/v1/settings')).json()).data;
  const changed=await page.request.put(origins.empty+'/api/v1/settings/non-secret',{
    headers:{Origin:origins.empty,'X-R7-CSRF':csrf!},data:{command_id:'browser-other-tab',expected_revision:settings.revision,display_timezone:'UTC',scan_interval:45}});
  expect(changed.status()).toBe(200);
  await page.getByLabel('掃描間隔（秒）',{exact:true}).fill('46');
  await page.getByRole('button',{name:'儲存顯示設定',exact:true}).focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('alert')).toContainText('RESOURCE_REVISION_CONFLICT');
  await page.getByRole('button',{name:'重新整理',exact:true}).click();
  await expect(page.getByLabel('掃描間隔（秒）',{exact:true})).toHaveValue('45');
});

test('financial controls stay visibly denied by actual fixture backend even after reauth',async({page})=>{
  await login(page,'protected'); await page.getByRole('link',{name:'策略',exact:true}).click();
  await page.getByRole('button',{name:'查看策略',exact:true}).first().click();
  await expect(page.getByRole('button',{name:'確認財務核准',exact:true})).toBeDisabled();
  await expect(page.getByText('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',{exact:true}).first()).toBeVisible();
  const session=(await (await page.request.get(origins.protected+'/api/v1/auth/session')).json());
  const csrf=await page.evaluate(()=>document.cookie.split('; ').find(s=>s.startsWith('r7_csrf='))?.slice(8));
  const headers={Origin:origins.protected,'X-R7-CSRF':csrf!};
  const reauth=await page.request.post(origins.protected+'/api/v1/auth/reauthenticate',{headers,data:{command_id:'browser-reauth-denial',expected_revision:session.revision,password}});
  expect(reauth.status()).toBe(200);
  const denied=await page.request.post(origins.protected+'/api/v1/approvals',{headers,data:{command_id:'browser-forged-approval',expected_revision:0,
    strategy_id:'fixture-subject',strategy_version:'1',envelope_ref:'uncommissioned',decision:'APPROVE',reason_code:'USER_CONFIRMED',
    expected_strategy_hash:'sha256:'+'a'.repeat(64),expected_envelope_hash:'sha256:'+'b'.repeat(64)}});
  expect(denied.status()).toBe(403); expect((await denied.json()).error.reason_codes).toContain('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN');
});

test('registered financial proposal shows actual source and limits and never grants fixture consent',async({page})=>{
  await login(page,'approval');await page.getByRole('link',{name:'策略',exact:true}).click();
  await page.getByRole('button',{name:'查看策略',exact:true}).first().click();
  await page.getByLabel('本機提案參照',{exact:true}).fill('fixture-envelope');
  await page.getByRole('button',{name:'讀取核准提案',exact:true}).click();
  await expect(page.getByText('提案資金上限（USDT）',{exact:true})).toBeVisible();
  const financial=page.locator('.financial');
  await expect(financial.getByText('100',{exact:true})).toBeVisible();
  await expect(financial.getByText('帳戶／提供者參照',{exact:true})).toBeVisible();
  await expect(financial.getByText('fixture-account / fixture-paper',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'確認財務核准',exact:true})).toBeDisabled();
  await expect(financial.getByRole('checkbox')).toBeDisabled();
  await page.screenshot({path:path.join(artifacts,'approval-preview.png'),fullPage:true});
  await page.getByLabel('本機提案參照',{exact:true}).fill('unregistered');
  await expect(page.getByText('提案資金上限（USDT）',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'讀取核准提案',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('CURRENT_APPROVAL_PROPOSAL_UNAVAILABLE');
  await expect(page.getByRole('button',{name:'確認財務核准',exact:true})).toBeDisabled();
});

test('stop new entries uses actual E6 pause while fixture activation remains unavailable',async({page})=>{
  await login(page,'deployment');await page.getByRole('link',{name:'策略',exact:true}).click();
  await page.getByRole('button',{name:'查看策略',exact:true}).first().click();
  const stop=page.getByRole('button',{name:'停止部署新進場',exact:true});await expect(stop).toBeEnabled();
  await stop.click();
  await expect(page.getByText('NEW_ENTRIES_DISABLED_MANAGEMENT_RETAINED',{exact:true}).first()).toBeVisible();
  await expect(page.getByText('DEGRADED',{exact:true}).first()).toBeVisible();
  await expect(stop).toBeDisabled();
  await expect(page.getByRole('button',{name:'確認啟用部署',exact:true})).toBeDisabled();
  await expect(page.getByText('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',{exact:true}).first()).toBeVisible();
  await page.screenshot({path:path.join(artifacts,'deployment-pause.png'),fullPage:true});
});

test('revoked server session returns to login without inferring runtime shutdown',async({page})=>{
  await login(page,'empty');
  const session=(await (await page.request.get(origins.empty+'/api/v1/auth/session')).json());
  const csrf=await page.evaluate(()=>document.cookie.split('; ').find(s=>s.startsWith('r7_csrf='))?.slice(8));
  const logout=await page.request.post(origins.empty+'/api/v1/auth/logout',{headers:{Origin:origins.empty,'X-R7-CSRF':csrf!},
    data:{command_id:'browser-other-session-logout',expected_revision:session.revision}});
  expect(logout.status()).toBe(200); await page.getByRole('button',{name:'重新整理',exact:true}).click();
  await expect(page.getByRole('button',{name:'登入',exact:true})).toBeVisible();
});

test('actual four-hour declaration, tactical validity, holding clock and author context remain separate',async({page})=>{
  await login(page,'temporal'); await page.getByRole('link',{name:'研究',exact:true}).click();
  await page.getByRole('button',{name:'掃描收件匣',exact:true}).click();
  await expect(page.getByText('fixture-temporal',{exact:true})).toBeVisible();
  await page.getByRole('link',{name:'策略',exact:true}).click();
  await page.getByRole('row').filter({hasText:'fixture-v02-4h-tactical'}).getByRole('button',{name:'查看策略',exact:true}).click();
  await expect(page.getByText('明確的四小時策略測試',{exact:true})).toBeVisible();
  await expect(page.getByText('fixture-temporal',{exact:true})).toBeVisible();
  await expect(page.getByText('4h',{exact:true}).first()).toBeVisible();
  await expect(page.getByText('7200 秒',{exact:true})).toBeVisible();
  await expect(page.getByText('2026-10-03T00:00:00Z → 2026-10-03T04:00:00Z',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'開始 PAPER',exact:true})).toBeDisabled();
});

test('two actual immutable versions remain independent in list and selected detail',async({page})=>{
  const origin=origins.versions;const remote:string[]=[];
  page.on('request',request=>{if(!request.url().startsWith(origin))remote.push(request.url());});
  await login(page,'versions');await page.getByRole('link',{name:'策略',exact:true}).click();
  const response=await page.request.get(origin+'/api/v1/strategies?limit=50&offset=0');
  expect(response.status()).toBe(200);const listing=(await response.json()).data;
  expect(listing.total).toBe(2);expect(listing.items).toHaveLength(2);
  const candidate=listing.items.find((row:any)=>row.current_lifecycle_state==='CANDIDATE');
  const draft=listing.items.find((row:any)=>row.current_lifecycle_state==='DRAFT');
  expect(candidate).toBeTruthy();expect(draft).toBeTruthy();
  expect(candidate.identity.strategy_id).toBe(draft.identity.strategy_id);
  expect(candidate.identity.strategy_version).not.toBe(draft.identity.strategy_version);
  expect(candidate.content_hash).not.toBe(draft.content_hash);
  await expect(page.getByTestId('fixture-banner')).toBeVisible();
  for(const item of [candidate,draft]){
    const row=page.getByRole('row').filter({hasText:item.content_hash});
    await expect(row).toHaveCount(1);
    await expect(row).toContainText(item.identity.strategy_id);
    await expect(row).toContainText(item.identity.strategy_version);
    await expect(row).toContainText(item.current_lifecycle_state);
  }
  const firstPage=await (await page.request.get(origin+'/api/v1/strategies?limit=1&offset=0')).json();
  const secondPage=await (await page.request.get(origin+'/api/v1/strategies?limit=1&offset=1')).json();
  expect(firstPage.data.total).toBe(2);expect(secondPage.data.total).toBe(2);
  expect(firstPage.data.items).toHaveLength(1);expect(secondPage.data.items).toHaveLength(1);
  expect(firstPage.data.items[0].identity).not.toEqual(secondPage.data.items[0].identity);
  const captured=new Map<string,unknown>();
  for(const [index,item] of [candidate,draft,candidate].entries()){
    const identity=item.identity;
    const route='/api/v1/strategies/'+encodeURIComponent(identity.strategy_id)+'/'+encodeURIComponent(identity.strategy_version);
    const actual=await page.request.get(origin+route);expect(actual.status()).toBe(200);
    const detail=(await actual.json()).data;const record=detail.payload;
    expect(record.content_hash).toBe(item.content_hash);
    expect(record.current_lifecycle_state).toBe(item.current_lifecycle_state);
    const observed=page.waitForResponse(r=>r.url()===origin+route&&r.request().method()==='GET');
    await page.getByRole('row').filter({hasText:item.content_hash}).getByRole('button',{name:'查看策略',exact:true}).click();
    expect((await observed).status()).toBe(200);
    const title='策略 '+identity.strategy_id+' / '+identity.strategy_version;
    const heading=page.getByRole('heading',{name:title,exact:true});await expect(heading).toBeVisible();
    const panel=page.locator('section.panel').filter({has:heading});
    for(const value of [item.content_hash,item.current_lifecycle_state,
                        record.author_metadata.submission_id,record.author_metadata.manifest.research_hypothesis]){
      await expect(panel).toContainText(value);
    }
    const declaration=panel.locator('details.evidence').filter({has:page.getByText('宣告、所需能力與出場規則原文',{exact:true})});
    await declaration.locator('summary').click();expect(JSON.parse(await declaration.locator('pre').innerText())).toEqual(record.definition);
    const lineage=panel.locator('details.evidence').filter({has:page.getByText('實際登錄與研究 lineage',{exact:true})});
    await lineage.locator('summary').click();expect(JSON.parse(await lineage.locator('pre').innerText())).toEqual(record);
    const other=item===candidate?draft:candidate;
    await expect(page.getByRole('heading',{name:'策略 '+other.identity.strategy_id+' / '+other.identity.strategy_version,exact:true})).toHaveCount(0);
    await expect(page.getByRole('button',{name:'開始 PAPER',exact:true})).toBeDisabled();
    if(captured.has(route))expect(detail).toEqual(captured.get(route));else captured.set(route,detail);
    await page.screenshot({path:path.join(artifacts,'two-versions-selected-'+index+'-'+identity.strategy_version+'.png'),fullPage:true});
  }
  const after=await (await page.request.get(origin+'/api/v1/strategies?limit=50&offset=0')).json();
  expect(after.data).toEqual(listing);expect(remote).toEqual([]);
});

async function assertDiagnostic(page:Page,testId:string,value:any){
  const card=page.getByTestId(testId);await expect(card).toBeVisible();
  await expect(card).toContainText(value.status);await expect(card).toContainText(value.source);
  for(const [label,at] of [['來源時點',value.as_of],['本次讀取',value.checked_at]]){
    const field=card.locator('dt').filter({hasText:new RegExp('^'+label+'$')}).locator('xpath=following-sibling::dd[1]');
    if(at===null){await expect(field.locator('time')).toHaveCount(0);await expect(field).toHaveText('未觀察');}
    else{await expect(field.locator('time')).toHaveAttribute('datetime',at);await expect(field.locator('code')).toHaveText(at);}
  }
  const evidence=card.locator('details.evidence');await evidence.locator('summary').click();
  expect(JSON.parse(await evidence.locator('pre').innerText())).toEqual({facts:value.facts,financial_authority:'NONE'});
}

test('UI01 diagnostic views show exact consumed facts and preserve explicit unknowns',async({page})=>{
  const remote:string[]=[];page.on('request',request=>{if(!request.url().startsWith(origins.empty))remote.push(request.url());});
  const overviewRead=page.waitForResponse(r=>r.url()===origins.empty+'/api/v1/overview'&&r.request().method()==='GET');
  await login(page,'empty');const overview=(await (await overviewRead).json()).data;
  for(const [key,testId] of [['strategy_subjects','overview-strategy-subjects'],['research_stage_counts','overview-research-stage-counts'],['resource_limits','overview-resource-limits'],['alerts','overview-alerts']]){
    await assertDiagnostic(page,testId,overview[key]);
  }
  expect(overview.strategy_subjects.status).toBe('NOT_CONFIGURED');expect(overview.research_stage_counts.status).toBe('NOT_CONFIGURED');
  await expect(page.getByTestId('overview-resource-limits')).toContainText(String(overview.resource_limits.facts.research_worker_count));
  const healthRead=page.waitForResponse(r=>r.url()===origins.empty+'/api/v1/health'&&r.request().method()==='GET');
  await page.getByRole('link',{name:'健康',exact:true}).click();const health=(await (await healthRead).json()).data;
  for(const role of ['control','research','runtime','cloud','coordinator'])await assertDiagnostic(page,'health-component-'+role,health.components[role]);
  for(const key of ['risk','execution','preflight','external_consumer']){
    expect(health[key].status).toBe('UNAVAILABLE');expect(health[key].as_of).toBeNull();expect(health[key].facts).toEqual({});
    await assertDiagnostic(page,'health-'+key,health[key]);
  }
  const settingsRead=page.waitForResponse(r=>r.url()===origins.empty+'/api/v1/settings'&&r.request().method()==='GET');
  await page.getByRole('link',{name:'設定',exact:true}).click();const settings=(await (await settingsRead).json()).data;
  for(const key of ['resource_limits','clock_health','backup','transport_test','credential_presence'])await assertDiagnostic(page,'settings-'+key.replace('resource_limits','resource-limits'),settings[key]);
  expect(settings.backup.status).toBe('NOT_CONFIGURED');expect(settings.transport_test.status).toBe('NOT_RUN');
  expect(settings.credential_presence.status).toBe('UNAVAILABLE');expect(settings.credential_presence.facts).toEqual({});
  expect(remote).toEqual([]);
  await page.screenshot({path:path.join(artifacts,'ui01-settings-observations.png'),fullPage:true});
});
