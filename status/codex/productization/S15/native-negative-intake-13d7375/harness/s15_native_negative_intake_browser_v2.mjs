import {createRequire} from 'node:module';
import path from 'node:path';
import assert from 'node:assert/strict';
import {open,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const [repo,origin,stage,output]=process.argv.slice(2);
assert.match(origin,/^http:\/\/127\.0\.0\.1:\d+$/);
assert.ok(['initial','partial-recovered','conflict'].includes(stage));
const require=createRequire(path.join(repo,'ui/package.json'));
const {chromium,expect}=require('@playwright/test');
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:960}});
const page=await context.newPage();const remote=[];
await context.route('**/*',route=>{if(route.request().url().startsWith(origin+'/'))return route.continue();remote.push(route.request().url());return route.abort();});
const read=async(route)=>{const response=await page.request.get(origin+route,{maxRedirects:0,timeout:5000});assert.equal(response.url(),origin+route);assert.equal(response.status(),200);return (await response.json()).data;};
let result={stage,passed:false,browser_version:browser.version(),namespace:'FIXTURE'};
try{
  await page.goto(origin);await page.getByLabel('帳號',{exact:true}).fill('native-fixture-owner');
  const password=process.env.R7_SYNTHETIC_PASSWORD;assert.ok(password?.length>=12);
  await page.getByLabel('密碼',{exact:true}).fill(password);
  const logged=page.waitForResponse(r=>r.url()===origin+'/api/v1/auth/login'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登入',exact:true}).click();assert.equal((await logged).status(),200);
  await expect(page.getByTestId('fixture-banner')).toContainText('FIXTURE');
  await page.getByRole('link',{name:'研究',exact:true}).click();
  if(stage==='partial-recovered')await page.waitForTimeout(5500); // actual wall clock bounded sync backoff; no clock injection
  const scanned=page.waitForResponse(r=>r.url()===origin+'/api/v1/research/scan'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'掃描收件匣',exact:true}).click();assert.equal((await scanned).status(),200);
  const views={};for(const name of ['partial','malformed','unsupported','expired'])views[name]=(await read('/api/v1/submissions/negative-'+name)).payload;
  const original=(await read('/api/v1/submissions/r7-synthetic-fixture-input')).payload;
  assert.equal(views.malformed.state,'BLOCKED');assert.equal(views.malformed.latest_observation.reason,'MALFORMED_JSON');
  assert.equal(views.unsupported.state,'BLOCKED');assert.equal(views.unsupported.latest_observation.reason,'UNSUPPORTED_PACKAGE_VERSION');
  assert.equal(views.expired.state,'EXPIRED');
  assert.equal(views.expired.latest_observation.reason,'SUBMISSION_EXPIRED');
  assert.equal(views.expired.receipt,null);
  assert.equal(original.state,'INTAKE_ACCEPTED');assert.equal(original.receipt.strategy_lifecycle,'DRAFT');
  const strategies=await read('/api/v1/strategies');assert.equal(strategies.items.length,1);
  assert.equal(strategies.items[0].current_lifecycle_state,'DRAFT');
  assert.equal(strategies.items[0].identity.strategy_id,'r7-synthetic-trend');
  assert.ok(strategies.items.every(item=>item.identity.strategy_id!=='r7-negative-expired-subject'));
  assert.equal((await read('/api/v1/research/runs')).items.length,0);
  assert.equal((await read('/api/v1/paper/runs')).items.length,0);
  if(stage==='initial')assert.equal(views.partial.state,'INCOMPLETE_SYNC');
  else assert.equal(views.partial.state,'INTAKE_ACCEPTED');
  let receiptUnchanged=null;
  if(stage==='conflict'){
    assert.equal(original.latest_observation.state,'CONFLICT');
    assert.equal(original.latest_observation.reason,'IMMUTABLE_SUBMISSION_CHANGED');
    const prior=JSON.parse(await readFile(path.join(output,'browser-initial.log'),'utf8'));
    receiptUnchanged=JSON.stringify(original.receipt)===JSON.stringify(prior.receipt);assert.ok(receiptUnchanged);
  }
  result={...result,malformed:views.malformed.state,partial:views.partial.state,unsupported:views.unsupported.state,
    expired:views.expired.state,expired_observation:views.expired.latest_observation,expired_receipt_absent:views.expired.receipt===null,
    distinct_expired_subject_absent:true,
    receipt:original.receipt,latest_observation:original.latest_observation?.state??null,receipt_unchanged:receiptUnchanged,
    canonical_strategies:1,canonical_lifecycle:'DRAFT',research_jobs:0,paper_runs:0};
  await expect(page.getByText('negative-malformed',{exact:true}).first()).toBeVisible();
  assert.equal(remote.length,0);
  const pixels=await page.screenshot({fullPage:true});const screenshot=stage+'.png';
  const file=await open(path.join(output,screenshot),'wx',0o600);
  try{await file.writeFile(pixels);await file.sync();}finally{await file.close();}
  console.log(JSON.stringify({...result,passed:true,remote_requests:0,screenshot,screenshot_sha256:'sha256:'+createHash('sha256').update(pixels).digest('hex')}));
}finally{await context.close();await browser.close();}
