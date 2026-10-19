// Development browser driver; actual UI commands, never a Paper authority.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

export async function startPaperViaUI(page,origin,expect){
  const route=origin+'/api/v1/paper/runs';
  const requests=[],responses=[];
  const sent=request=>{if(request.url()===route&&request.method()==='POST')requests.push(request);};
  const received=response=>{if(response.url()===route&&response.request().method()==='POST')responses.push(response);};
  page.on('request',sent);page.on('response',received);
  let state=null,ownerReadTimeouts=0;
  try{
    await page.getByRole('button',{name:'開始 PAPER',exact:true}).click();
    const pending=page.getByRole('button',{name:'使用原命令重試',exact:true});
    await expect.poll(async()=>{
      state=await page.getByText('伺服器收據：COMPLETE',{exact:true}).isVisible()?'COMPLETE':
        await pending.isVisible()?'PENDING':null;
      return state;
    },{timeout:20000}).not.toBeNull();
    assert.equal(requests.length,1);
    const original=requests[0].postData();assert.ok(original);
    const body=JSON.parse(original);
    assert.deepEqual(Object.keys(body).sort(),['command_id','expected_revision','policy_id','strategy_id','strategy_version']);
    assert.equal(typeof body.command_id,'string');assert.ok(Number.isInteger(body.expected_revision));
    if(state==='PENDING'){
      await expect(page.getByRole('alert')).toContainText('RESPONSE_UNKNOWN');
      // Wait for actual accepted owner evidence before retrying the original
      // command. No new command, run or direct owner operation is introduced.
      await expect.poll(async()=>{
        try{
          const response=await page.request.get(route,{maxRedirects:0,timeout:5000});
          assert.equal(response.url(),route);assert.equal(response.status(),200);
          const list=(await response.json()).data;assert.ok(Array.isArray(list.items));
          return list.items.length;
        }catch(error){
          if(error.name!=='TimeoutError')throw error;
          ownerReadTimeouts++;return 0;
        }
      },{timeout:20000}).toBe(1);
      const completed=page.waitForResponse(r=>r.url()===route&&r.request().method()==='POST',
        {timeout:10000});
      await pending.click();assert.equal((await completed).status(),200);
      await expect(page.getByText('伺服器收據：COMPLETE',{exact:true})).toBeVisible();
      assert.equal(requests.length,2);assert.equal(requests[1].postData(),original);
    }
    const final=responses.findLast(response=>response.request()===requests.at(-1));
    assert.ok(final);assert.equal(final.status(),200);
    const receipt=await final.json();assert.equal(receipt.command_id,body.command_id);
    assert.equal(receipt.status,'COMPLETE');assert.equal(receipt.expected_revision,body.expected_revision);
    assert.equal(receipt.resource,'strategy:'+body.strategy_id+':'+body.strategy_version);
    assert.ok(receipt.effect_ref.startsWith('paper:'));
    await expect(pending).toHaveCount(0);
    return {recovery:state==='PENDING'?'ORIGINAL_COMMAND_RETRY':'DIRECT_COMPLETE',receipt,
      request_count:requests.length,byte_identical_request:true,read_only_owner_poll_timeouts:ownerReadTimeouts,
      request_hash:'sha256:'+createHash('sha256').update(original).digest('hex')};
  }finally{page.off('request',sent);page.off('response',received);}
}
