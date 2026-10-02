import type {components} from './api.generated';
import {object} from './model';
export type Schema=components['schemas'];
export type Envelope<T>={metadata:Schema['ViewMetadata'];data:T};
export class ControlError extends Error{
  constructor(public status:number,public reasons:string[],public correlation:string|null=null){super(reasons.join(', '));}
}
export class ControlAPI{
  constructor(private csrf:()=>string,private invalidated:()=>void=()=>{}){}
  private async request<T>(path:string,method:string,body?:object,signal?:AbortSignal):Promise<T>{
    if(!path.startsWith('/api/v1/')||path.includes('://')||path.includes('#'))throw new ControlError(0,['LOCAL_API_PATH_REQUIRED']);
    const headers:Record<string,string>={Accept:'application/json'};
    if(body){headers['Content-Type']='application/json'; if(path!=='/api/v1/auth/login'){
      const proof=this.csrf(); if(!proof)throw new ControlError(403,['CSRF_REQUIRED']); headers['X-R7-CSRF']=proof;
    }}
    const controller=new AbortController(); const cancel=()=>controller.abort(); signal?.addEventListener('abort',cancel,{once:true});
    const timer=setTimeout(cancel,15_000);
    try{
      const response=await fetch(path,{method,credentials:'same-origin',headers,body:body?JSON.stringify(body):undefined,signal:controller.signal,redirect:'error',cache:'no-store'});
      const raw=await response.text(); if(raw.length>2_000_000)throw new ControlError(response.status,['RESPONSE_SIZE_LIMIT']);
      let value:unknown; try{value=JSON.parse(raw);}catch{throw new ControlError(response.status,['INVALID_SERVER_RESPONSE']);}
      if(!response.ok){
        const detail=object(object(value).error); const codes=Array.isArray(detail.reason_codes)?detail.reason_codes.filter((item):item is string=>typeof item==='string'&&/^[A-Z0-9_]{1,96}$/.test(item)):[];
        if(response.status===401&&!['/api/v1/auth/login','/api/v1/auth/reauthenticate'].includes(path)&&!codes.includes('REAUTHENTICATION_REQUIRED'))this.invalidated();
        throw new ControlError(response.status,codes.length?codes:['CONTROL_OPERATION_FAILED'],typeof detail.correlation_id==='string'&&/^[0-9a-f]{32}$/.test(detail.correlation_id)?detail.correlation_id:null);
      }
      return value as T;
    }catch(error){if(error instanceof ControlError)throw error; throw new ControlError(0,['RESPONSE_UNKNOWN']);}
    finally{clearTimeout(timer); signal?.removeEventListener('abort',cancel);}
  }
  read<T>(path:string,signal?:AbortSignal){return this.request<T>(path,'GET',undefined,signal);}
  async view<T>(path:string,signal?:AbortSignal):Promise<Envelope<T>>{
    const value=await this.read<Envelope<T>>(path,signal); const meta=object(value?.metadata);
    if(!['FIXTURE','LOCAL_RESEARCH'].includes(String(meta.namespace))||typeof meta.source!=='string'||typeof meta.observed_at!=='string'||!/^sha256:[0-9a-f]{64}$/.test(String(meta.config_hash))||!('data' in object(value)))throw new ControlError(0,['VIEW_PROVENANCE_UNAVAILABLE']);
    return value;
  }
  command<T=Schema['CommandReceipt']>(path:string,body:object,method='POST'){return this.request<T>(path,method,body);}
  login(body:Schema['LoginDTO']){return this.request<Schema['LoginView']>('/api/v1/auth/login','POST',body);}
}
export const csrfCookie=()=>{
  const value=document.cookie.split('; ').find(item=>item.startsWith('r7_csrf='));
  try{return value?decodeURIComponent(value.slice(8)):'';}catch{return '';}
};
export const api=new ControlAPI(csrfCookie,()=>window.dispatchEvent(new Event('r7-session-expired')));
export const commandId=()=>crypto.randomUUID();
