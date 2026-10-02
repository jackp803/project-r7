import {afterEach,describe,expect,it,vi} from 'vitest';
import {ControlAPI,ControlError} from './api';

afterEach(()=>vi.unstubAllGlobals());
describe('same-origin authenticated command transport',()=>{
  it('binds CSRF and retains the exact caller command for retries without accepting an actor',async()=>{
    const fetcher=vi.fn(async()=>new Response(JSON.stringify({status:'COMPLETE'}),{status:200})); vi.stubGlobal('fetch',fetcher);
    const client=new ControlAPI(()=> 'fixture-csrf'); const command={command_id:'same-command',expected_revision:7,display_timezone:'UTC' as const,scan_interval:30};
    await client.command('/api/v1/settings/non-secret',command,'PUT'); await client.command('/api/v1/settings/non-secret',command,'PUT');
    const request=fetcher.mock.calls[0] as unknown as [string,RequestInit];
    expect(request[0]).toBe('/api/v1/settings/non-secret'); expect(request[1].credentials).toBe('same-origin');
    expect(request[1].body).toBe(JSON.stringify(command)); expect((request[1].headers as Record<string,string>)['X-R7-CSRF']).toBe('fixture-csrf');
    expect((fetcher.mock.calls[1] as unknown as [string,RequestInit])[1].body).toBe(request[1].body);
    expect(request[1].body).not.toContain('actor');
  });
  it('preserves sanitized conflict reasons and does not echo an arbitrary error body',async()=>{
    vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({error:{category:'CONFLICT',reason_codes:['RESOURCE_REVISION_CONFLICT'],correlation_id:'a'.repeat(32)}}),{status:409})));
    const client=new ControlAPI(()=> 'fixture-csrf'); await expect(client.read('/api/v1/settings')).rejects.toMatchObject({status:409,reasons:['RESOURCE_REVISION_CONFLICT']});
    vi.stubGlobal('fetch',vi.fn(async()=>new Response('fixture-secret-stack-trace',{status:500})));
    await expect(client.read('/api/v1/settings')).rejects.toMatchObject({reasons:['INVALID_SERVER_RESPONSE']});
  });
  it('cannot send a product command to a remote URL or without a CSRF proof',async()=>{
    const fetcher=vi.fn(); vi.stubGlobal('fetch',fetcher); const client=new ControlAPI(()=> '');
    await expect(client.command('https://remote.invalid',{})).rejects.toBeInstanceOf(ControlError);
    await expect(client.command('/api/v1/research/scan',{})).rejects.toBeInstanceOf(ControlError); expect(fetcher).not.toHaveBeenCalled();
  });
  it('reports a revoked server session separately from a wrong reauthentication password',async()=>{
    const invalidated=vi.fn();
    vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({error:{category:'AUTHORIZATION_REQUIRED',reason_codes:['AUTHORIZATION_REQUIRED'],correlation_id:'b'.repeat(32)}}),{status:401})));
    const client=new ControlAPI(()=> 'fixture-csrf',invalidated);
    await expect(client.read('/api/v1/settings')).rejects.toBeInstanceOf(ControlError); expect(invalidated).toHaveBeenCalledTimes(1);
    await expect(client.command('/api/v1/auth/reauthenticate',{password:'wrong-fixture-password'})).rejects.toBeInstanceOf(ControlError); expect(invalidated).toHaveBeenCalledTimes(1);
  });
});
