import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
const repo=resolve(process.argv[2]),html=resolve(process.argv[3]),output=resolve(process.argv[4]);
const require=createRequire(join(repo,'ui/package.json'));
const {chromium}=require('@playwright/test');
mkdirSync(output);
const hash=raw=>'sha256:'+createHash('sha256').update(raw).digest('hex');
const report={scope:'Generated native feedback artifact visual QA; not a new Control Center browser qualification',
  started_at_utc:new Date().toISOString(),html_sha256:hash(readFileSync(html)),checks:[],provider_requests:0,cloud:'NOT_CONTACTED'};
let browser;
try {
  browser=await chromium.launch({channel:'msedge',headless:true});report.browser_version=browser.version();
  for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]) {
    const page=await browser.newPage({viewport:{width,height}});
    const network=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
    await page.goto(pathToFileURL(html).href);
    const rows=await page.locator('tbody tr').allTextContents();
    if(rows.length!==6||!rows[4].includes('PAPERNOT_RUN')||!rows[5].includes('LIVENOT_RUN'))throw Error('False or missing stage summary');
    if(await page.locator('details').getAttribute('open')!==null)throw Error('Detail must initially be collapsed');
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Horizontal overflow');
    const screenshot=name+'.png';await page.screenshot({path:join(output,screenshot),fullPage:true});
    await page.locator('summary').click();
    if(!await page.locator('pre').isVisible())throw Error('Detail cannot be opened');
    if(network.length)throw Error('Feedback contacted a network');
    report.checks.push({name,viewport:{width,height},stage_rows:6,detail_expandable:true,horizontal_overflow:false,
      external_requests:0,screenshot,screenshot_sha256:hash(readFileSync(join(output,screenshot))),passed:true});
    await page.close();
  }
  report.passed=true;
} finally {
  if(browser)await browser.close();
  report.finished_at_utc=new Date().toISOString();report.browser_closed=true;
  writeFileSync(join(output,'feedback-visual-qa.json'),JSON.stringify(report,null,2)+'\n');
}
console.log(JSON.stringify(report));
