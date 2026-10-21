import {test,expect} from '@playwright/test';
import path from 'node:path';

for(const [index,profile] of ['pending','finalized'].entries()){
  test(`controlled LOCAL recorded-funding ${profile} facts render without requests outside loopback`,async({page})=>{
    const origin=`http://127.0.0.1:${8780+index}`;const outside:string[]=[];
    page.on('request',request=>{if(!request.url().startsWith(origin+'/'))outside.push(request.url());});
    await page.goto(origin);
    await page.getByLabel('帳號',{exact:true}).fill('local-owner');
    await page.getByLabel('密碼',{exact:true}).fill('explicit-test-only-password-123');
    await page.getByRole('button',{name:'登入',exact:true}).click();
    await expect(page.getByRole('heading',{name:'總覽',exact:true})).toBeVisible();
    await page.getByRole('link',{name:'交易',exact:true}).click();
    const response=await page.request.get(origin+'/api/v1/paper/runs');expect(response.status()).toBe(200);
    const runs=(await response.json()).data.items;expect(runs).toHaveLength(1);
    await page.getByRole('button',{name:'查看 PAPER',exact:true}).click();
    const detail=await page.request.get(origin+'/api/v1/paper/runs/'+runs[0].run_id);expect(detail.status()).toBe(200);
    const run=(await detail.json()).data.payload;
    expect(run.funding.status).toBe(profile==='pending'?'FUNDING_PENDING':'FINALIZED');
    expect(run.closed_trades_count).toBe(profile==='pending'?0:1);
    const funding=page.getByTestId('paper-funding');await expect(funding).toBeVisible();
    await expect(funding).toContainText(run.funding.status);
    await expect(funding).toContainText('並非交易所按結算標記價計算的帳單');
    await expect(funding).toContainText('方向訊號不等於可交易機會');
    await expect(funding).toContainText('財務證據不足、風險未確認');
    if(profile==='pending'){
      await expect(funding).toContainText(run.funding.wait_reason);
      await expect(page.getByTestId('paper-position')).toContainText('E4 已確認平倉');
    }else{
      expect(run.funding.pending_allocations).toBe(0);expect(run.funding.finalized_allocations).toBe(1);
      expect(run.funding.latest_source.status).toBe('HEALTHY');
    }
    await page.screenshot({path:path.join(process.env.R7_BROWSER_ARTIFACT_ROOT!,`controlled-${profile}.png`),fullPage:true});
    expect(outside).toEqual([]);
  });
}
