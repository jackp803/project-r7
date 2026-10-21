import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {chromium} from '../../workspaces/project-r7-productization-master-20261002/ui/node_modules/playwright/index.mjs';
const [origin,revision,implementation,output]=process.argv.slice(2);
assert.match(origin,/^http:\/\/127\.0\.0\.1:\d+$/);
assert.match(revision,/^[0-9a-f]{40}$/);assert.match(implementation,/^sha256:[0-9a-f]{64}$/);
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const page=await browser.newPage();const remote=[];
 page.on('request',r=>{if(!r.url().startsWith(origin+'/'))remote.push(r.url());});
 await page.goto(origin);
 await page.getByLabel('帳號',{exact:true}).fill('local-owner');
 await page.getByLabel('密碼',{exact:true}).fill('explicit-test-only-password-123');
 const response=page.waitForResponse(r=>r.url()===origin+'/api/v1/overview'&&r.request().method()==='GET');
 await page.getByRole('button',{name:'登入',exact:true}).click();
 const actual=await response;assert.equal(actual.status(),200);const meta=(await actual.json()).metadata;
 assert.equal(meta.executable_revision,revision);assert.equal(meta.implementation_hash,implementation);assert.equal(meta.worktree,'CLEAN');
 await page.getByRole('heading',{name:'總覽',exact:true}).waitFor({state:'visible'});
 const footer=page.locator('footer');await footer.waitFor({state:'visible'});assert.match(await footer.innerText(),/R7 v0\.2/);
 const source=page.locator('details.source').first();await source.locator('summary').click();
 const field=label=>source.locator('dt').filter({hasText:new RegExp('^'+label+'$')}).locator('xpath=following-sibling::dd[1]');
 const visibleRevision=field('執行版本').locator('code');await visibleRevision.waitFor({state:'visible'});
 assert.equal(await visibleRevision.innerText(),revision);assert.equal(await field('程式雜湊').locator('code').innerText(),implementation);
 assert.equal(await page.getByTestId('fixture-banner').isVisible(),true);assert.deepEqual(remote,[]);
 await writeFile(output,JSON.stringify({passed:true,scope:'A08_ACTUAL_CURRENT_SOURCE_BROWSER_ONLY',
  product_version_visible:'R7 v0.2',full_revision_visible:revision,implementation_hash_visible:implementation,
  worktree:meta.worktree,fixture:true,financial_authority:'NONE',external_requests:remote.length},null,2)+'\n');
}finally{await browser.close();}
