import {test,expect,type Page} from '@playwright/test';
import path from 'node:path';

const origins={empty:'http://127.0.0.1:8766',research:'http://127.0.0.1:8767',paper:'http://127.0.0.1:8768',protected:'http://127.0.0.1:8769',temporal:'http://127.0.0.1:8770',approval:'http://127.0.0.1:8771',deployment:'http://127.0.0.1:8772'};
const password='explicit-test-only-password-123';
async function login(page:Page,profile:keyof typeof origins){
  await page.goto(origins[profile]);
  await page.getByLabel('帳號',{exact:true}).fill('local-owner');
  await page.getByLabel('密碼',{exact:true}).fill(password);
  await page.getByRole('button',{name:'登入',exact:true}).click();
  await expect(page.getByRole('heading',{name:'總覽',exact:true})).toBeVisible();
}

test('empty views use actual nulls, Traditional Chinese and persistent fixture labels',async({page})=>{
  const remote:string[]=[];
  page.on('request',request=>{if(!request.url().startsWith(origins.empty))remote.push(request.url());});
  await login(page,'empty');
  await expect(page.getByTestId('fixture-banner')).toContainText('FIXTURE');
  await expect(page.getByTestId('realized-pnl')).toContainText('未提供');
  await page.screenshot({path:path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser/overview.png'),fullPage:true});
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
  await page.screenshot({path:path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser/health.png'),fullPage:true});
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
  expect((await jobs.json()).data.items[0].state).toBe('CANCELED');
});

test('health distinguishes actual supervised control from an available queue without a worker',async({page})=>{
  await login(page,'research');await page.getByRole('link',{name:'健康',exact:true}).click();
  await expect(page.getByText('最近收到程序心跳',{exact:true})).toBeVisible();
  await expect(page.getByText('工作佇列可用；工作者尚未啟動',{exact:true})).toBeVisible();
  const response=await page.request.get(origins.research+'/api/v1/health');
  expect(response.status()).toBe(200);
  const actual=(await response.json()).data;
  expect(actual.control).toBe('PROCESS_RECENT_HEARTBEAT');
  expect(actual.research).toBe('QUEUE_AVAILABLE_WORKER_NOT_STARTED');
  expect(actual.live_authorized).toBe(false);
  await page.screenshot({path:path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser/supervised-health.png'),fullPage:true});
});

test('actual candidate PAPER start and pause retain run identity and show unavailable metrics',async({page})=>{
  await login(page,'paper'); await page.getByRole('link',{name:'策略',exact:true}).click();
  await page.getByRole('button',{name:'查看策略',exact:true}).first().click();
  await page.getByLabel('PAPER 政策',{exact:true}).selectOption('fixture-paper-policy');
  await page.getByRole('button',{name:'開始 PAPER',exact:true}).click();
  await page.getByRole('link',{name:'交易',exact:true}).click();
  await expect(page.getByText('ACCELERATED_FIXTURE',{exact:true}).first()).toBeVisible();
  await page.getByRole('button',{name:'查看 PAPER',exact:true}).first().click();
  await expect(page.getByText('NOT_STARTED',{exact:true}).first()).toBeVisible();
  await page.getByRole('button',{name:'停止新進場',exact:true}).click();
  await expect(page.getByTestId('paper-entry-admission')).toContainText('PAUSED');
  const runs=(await (await page.request.get(origins.paper+'/api/v1/paper/runs')).json()).data.items;
  expect(runs).toHaveLength(1); expect(runs[0].process_generation).toBe(0); expect(runs[0].metrics).toBeNull();
});

test('protected owner facts distinguish ACK/fill, remaining exposure and as-of state',async({page})=>{
  await login(page,'protected'); await page.getByRole('link',{name:'交易',exact:true}).click();
  await page.getByRole('button',{name:'查看 PAPER',exact:true}).first().click();
  await expect(page.getByTestId('paper-position')).toContainText('0.001');
  await expect(page.getByText('OPEN_PROTECTED',{exact:true}).first()).toBeVisible();
  await expect(page.getByText('委託 ACK 與實際成交',{exact:true})).toBeVisible();
  await expect(page.getByTestId('paper-freshness')).toContainText('LAST_KNOWN_GOOD');
  await page.getByRole('button',{name:'停止新進場',exact:true}).click();
  await expect(page.getByTestId('paper-position')).toContainText('0.001');
  const runs=(await (await page.request.get(origins.protected+'/api/v1/paper/runs')).json()).data.items;
  expect(runs[0].position.actual_quantity).toBe('0.001'); expect(runs[0].process_generation).toBe(1);
  await page.getByRole('heading',{name:'交易',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser/protected-paper.png'),fullPage:true});
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
  await page.screenshot({path:path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser/approval-preview.png'),fullPage:true});
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
  await page.screenshot({path:path.resolve(import.meta.dirname,'../../../../artifacts/S11-browser/deployment-pause.png'),fullPage:true});
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
