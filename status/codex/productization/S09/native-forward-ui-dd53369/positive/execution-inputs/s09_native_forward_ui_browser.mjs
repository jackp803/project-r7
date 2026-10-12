// Actual packaged Control Center only. No route mocks, injected stores or owner factories.
import {createRequire} from 'node:module';
import path from 'node:path';
import assert from 'node:assert/strict';
import {open,lstat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const [repo,origin,stage,output,scenario]=process.argv.slice(2);
assert.ok(['positive','oos-loss','insufficient-oos'].includes(scenario));
const expected={positive:['CANDIDATE','PASS'],'oos-loss':['REJECTED','FAIL'],'insufficient-oos':['BACKTESTING','BLOCKED']}[scenario];
assert.match(origin,/^http:\/\/127\.0\.0\.1:\d+$/);
assert.ok(['research-enqueue','research-result','paper-start','paper-pause','paper-closed','paper-denied'].includes(stage));
const require=createRequire(path.join(repo,'ui','package.json'));
const {chromium,expect}=require('@playwright/test');
const password=process.env.R7_SYNTHETIC_PASSWORD;
assert.ok(password&&password.length>=12);
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:960}});
const page=await context.newPage();
const remote=[];
await context.route('**/*',route=>{
  if(route.request().url().startsWith(origin+'/'))return route.continue();
  remote.push(route.request().url());return route.abort();
});
const read=async(route)=>{const response=await page.request.get(origin+route,{maxRedirects:0,timeout:5000});assert.equal(response.url(),origin+route);assert.equal(response.status(),200);return (await response.json()).data;};
const paperView=async()=>{
  const list=await read('/api/v1/paper/runs');assert.equal(list.items.length,1);
  return await read('/api/v1/paper/runs/'+encodeURIComponent(list.items[0].run_id));
};
let result={stage,passed:false,namespace:'FIXTURE',browser_version:browser.version(),remote_requests:0};
try{
  await page.goto(origin);
  await page.getByLabel('帳號',{exact:true}).fill('native-fixture-owner');
  await page.getByLabel('密碼',{exact:true}).fill(password);
  const loginPending=page.waitForResponse(r=>r.url()===origin+'/api/v1/auth/login'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登入',exact:true}).click();
  const loginResponse=await loginPending;assert.equal(loginResponse.status(),200);
  const loginBody=await loginResponse.json();assert.ok(loginBody.csrf_token);
  await expect(page.getByRole('heading',{name:'總覽',exact:true})).toBeVisible({timeout:10000});
  await expect(page.getByTestId('fixture-banner')).toContainText('FIXTURE');
  if(stage==='research-enqueue'){
    await page.getByRole('link',{name:'研究',exact:true}).click();
    const scan=page.waitForResponse(r=>r.url()===origin+'/api/v1/research/scan'&&r.request().method()==='POST');
    await page.getByRole('button',{name:'掃描收件匣',exact:true}).click();assert.equal((await scan).status(),200);
    await expect(page.getByText('r7-synthetic-fixture-input',{exact:true}).first()).toBeVisible();
    await page.getByLabel('提交 ID',{exact:true}).fill('r7-synthetic-fixture-input');
    await page.getByLabel('研究政策',{exact:true}).selectOption('r7-synthetic-fixture-policy');
    const enqueue=page.waitForResponse(r=>r.url()===origin+'/api/v1/research/runs'&&r.request().method()==='POST');
    await page.getByRole('button',{name:'排入研究',exact:true}).click();assert.equal((await enqueue).status(),202);
    await expect(page.getByText('QUEUED',{exact:true}).first()).toBeVisible();
    const jobs=await read('/api/v1/research/runs');assert.equal(jobs.items.length,1);assert.equal(jobs.items[0].state,'QUEUED');
    result={...result,research_job_id:jobs.items[0].run_id,research_state:'QUEUED',intake:'ACTUAL_NATIVE_OWNER'};
  }else if(stage==='research-result'){
    await page.getByRole('link',{name:'策略',exact:true}).click();
    await expect(page.getByText(expected[0],{exact:true}).first()).toBeVisible();
    const strategies=await read('/api/v1/strategies');assert.equal(strategies.items.length,1);
    assert.equal(strategies.items[0].current_lifecycle_state,expected[0]);
    const jobs=await read('/api/v1/research/runs');assert.equal(jobs.items.length,1);
    const job=await read('/api/v1/research/runs/'+encodeURIComponent(jobs.items[0].run_id));
    assert.equal(job.payload.evidence.sealed_oos,expected[1]);assert.ok(job.payload.owner_run_id);
    if(scenario==='insufficient-oos')assert.equal(job.payload.outcome.status,'BLOCKED');
    result={...result,research_job_id:jobs.items[0].run_id,owner_run_id:job.payload.owner_run_id,sealed_oos:expected[1],lifecycle:expected[0]};
  }else if(stage==='paper-denied'){
    assert.notEqual(scenario,'positive');
    const before=await read('/api/v1/paper/runs');assert.equal(before.items.length,0);
    await page.getByRole('link',{name:'策略',exact:true}).click();
    await page.getByRole('button',{name:'查看策略',exact:true}).click();
    const strategies=await read('/api/v1/strategies');assert.equal(strategies.items.length,1);
    const identity=strategies.items[0].identity;
    const subjectRoute='/api/v1/strategies/'+encodeURIComponent(identity.strategy_id)+'/'+encodeURIComponent(identity.strategy_version);
    const subject=await read(subjectRoute);assert.equal(subject.payload.current_lifecycle_state,expected[0]);
    const policies=await read('/api/v1/policies');const selected=policies.items.filter(p=>p.kind==='PAPER');
    assert.equal(selected.length,1);assert.equal(selected[0].workflow_authorized,true);assert.equal(selected[0].mode,'ACCELERATED_FIXTURE');
    await page.getByLabel('PAPER 政策',{exact:true}).selectOption(selected[0].policy_id);
    await expect(page.getByRole('button',{name:'開始 PAPER',exact:true})).toBeDisabled();
    const denied=await page.request.post(origin+'/api/v1/paper/runs',{maxRedirects:0,timeout:10000,
      headers:{Origin:origin,'x-r7-csrf':loginBody.csrf_token},
      data:{command_id:'native-noncandidate-denied-'+scenario,expected_revision:subject.revision,
        strategy_id:identity.strategy_id,strategy_version:identity.strategy_version,policy_id:selected[0].policy_id}});
    assert.equal(denied.url(),origin+'/api/v1/paper/runs');assert.equal(denied.status(),409);
    const rejection=await denied.json();assert.deepEqual(rejection.error.reason_codes,['CURRENT_OWNER_EVIDENCE_REQUIRED']);
    const after=await read('/api/v1/paper/runs');assert.equal(after.items.length,0);
    assert.deepEqual(await read(subjectRoute),subject);
    result={...result,lifecycle:expected[0],denial:rejection.error.reason_codes[0],paper_runs_before:0,paper_runs_after:0,registry_subject_unchanged:true};
  }else{
    if(stage==='paper-start'){
      await page.getByRole('link',{name:'策略',exact:true}).click();
      await page.getByRole('button',{name:'查看策略',exact:true}).click();
      const policies=await read('/api/v1/policies');const selected=policies.items.filter(p=>p.kind==='PAPER');
      assert.equal(selected.length,1);assert.equal(selected[0].workflow_authorized,true);assert.equal(selected[0].mode,'ACCELERATED_FIXTURE');
      await page.getByLabel('PAPER 政策',{exact:true}).selectOption(selected[0].policy_id);
      const start=page.waitForResponse(r=>r.url()===origin+'/api/v1/paper/runs'&&r.request().method()==='POST');
      await page.getByRole('button',{name:'開始 PAPER',exact:true}).click();assert.equal((await start).status(),200);
    }
    await page.getByRole('link',{name:'交易',exact:true}).click();
    await page.getByRole('button',{name:'查看 PAPER',exact:true}).click();
    let view=await paperView();let run=view.payload;
    assert.equal(run.namespace,'FIXTURE');assert.equal(run.mode,'ACCELERATED_FIXTURE');
    if(stage==='paper-start'){
      assert.equal(run.process_generation,0);assert.equal(run.runtime_status,'NOT_STARTED');assert.equal(run.closed_trades_count,0);
      await expect(page.getByText('NOT_STARTED',{exact:true}).first()).toBeVisible();
    }else if(stage==='paper-pause'){
      assert.equal(run.position.lifecycle_state,'OPEN_PROTECTED');assert.equal(run.process_generation,1);
      await expect(page.getByTestId('paper-position')).toContainText('OPEN_PROTECTED');
      const pause=page.waitForResponse(r=>r.url().endsWith('/pause')&&r.request().method()==='POST');
      await page.getByRole('button',{name:'停止新進場',exact:true}).click();assert.equal((await pause).status(),200);
      await expect(page.getByTestId('paper-entry-admission')).toContainText('PAUSED');
      view=await paperView();run=view.payload;assert.equal(run.entry_admission,'PAUSED');assert.equal(run.process_generation,1);
    }else{
      assert.equal(run.position.lifecycle_state,'CLOSED');assert.equal(run.process_generation,2);assert.equal(run.closed_trades_count,1);
      assert.equal(run.entry_admission,'PAUSED');assert.equal(run.forward_observations.real_elapsed_ns,0);
      await expect(page.getByTestId('paper-position')).toContainText('CLOSED');
      await expect(page.getByTestId('paper-entry-admission')).toContainText('PAUSED');
    }
    if(stage!=='paper-start'){
      assert.equal(run.forward_observations.real_elapsed_ns,0);
      await expect(page.getByTestId('paper-real-forward-seconds').locator('strong')).toHaveText('0');
    }
    result={...result,run_id:run.run_id,position:run.position,process_generation:run.process_generation,entry_admission:run.entry_admission,
      closed_trades_count:run.closed_trades_count,forward:run.forward_observations,binding:run.binding,runtime_status:run.runtime_status};
  }
  assert.equal(remote.length,0);
  const parent=await lstat(output);assert.ok(parent.isDirectory()&&!parent.isSymbolicLink());
  const pixels=await page.screenshot({fullPage:true});
  const destination=path.join(output,stage+'.png');const image=await open(destination,'wx',0o600);
  try{
    const opened=await image.stat();assert.ok(opened.isFile()&&opened.nlink===1);
    await image.writeFile(pixels);await image.sync();
    const current=await lstat(destination);const afterParent=await lstat(output);
    assert.ok(current.isFile()&&!current.isSymbolicLink()&&current.nlink===1&&current.ino===opened.ino&&current.dev===opened.dev);
    assert.ok(afterParent.isDirectory()&&!afterParent.isSymbolicLink()&&afterParent.ino===parent.ino&&afterParent.dev===parent.dev);
  }finally{await image.close();}
  console.log(JSON.stringify({...result,passed:true,remote_requests:remote.length,screenshot:stage+'.png',screenshot_sha256:'sha256:'+createHash('sha256').update(pixels).digest('hex')}));
}finally{await context.close();await browser.close();}
