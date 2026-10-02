export type Row=Record<string,unknown>;
export const object=(value:unknown):Row=>value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Row:{};
export const rows=(value:unknown):Row[]=>Array.isArray(value)?value.map(object):[];
export const text=(value:unknown):string=>typeof value==='string'?value:typeof value==='number'?String(value):value===true?'是':value===false?'否':'未提供';
export const metric=(value:unknown):string=>value===null||value===undefined?'未提供':text(value);
export function revision(value:unknown):number{
  if(typeof value!=='number'||!Number.isSafeInteger(value)||value<0)throw new Error('RESOURCE_REVISION_UNAVAILABLE'); return value;
}
export function utcDisplay(value:unknown,timezone:'UTC'|'Asia/Taipei'):string{
  if(typeof value!=='string'||!/(Z|\+00:00)$/.test(value)||!Number.isFinite(Date.parse(value)))return '未知';
  return new Intl.DateTimeFormat('zh-TW',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(value))+' '+timezone;
}
export function progressLabel(completed:unknown,total:unknown):string{
  return typeof completed==='number'&&typeof total==='number'&&Number.isSafeInteger(completed)&&Number.isSafeInteger(total)&&completed>=0&&total>=completed&&total>0?`${completed} / ${total}`:'未提供完成比例';
}
export function temporalFacts(value:Row){
  const rules=object(object(value.definition).rules); const validity=object(value.submission_validity);
  const hold=value.max_hold_seconds??object(rules.exit_policy).max_hold_seconds;
  return {evaluation:text(value.evaluation_timeframe??rules.evaluation_timeframe),
    maxHold:hold===undefined||hold===null?'未提供':text(hold)+' 秒',
    validity:validity.until===undefined?'未提供；不可從評估週期推定':validity.until===null?'EVERGREEN；沒有宣告到期':text(validity.from)+' → '+text(validity.until)};
}
export function approvalBlock(namespace:string,_subject:Row):string{
  return namespace==='FIXTURE'?'FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN':'FINANCIAL_ENVELOPE_NOT_COMMISSIONED';
}
export const reasons:Record<string,string>={
  AUTHORIZATION_REQUIRED:'登入已失效或身分驗證未通過。請重新登入；既有 runtime 仍由本機服務管理。',
  RESOURCE_REVISION_CONFLICT:'資料版本已變更。請重新整理後確認目前內容，再送出新命令。',
  OWNER_COMMAND_CONFLICT:'目前擁有者的版本或命令狀態衝突。請查看最新證據。',
  NOT_CONFIGURED:'尚未完成本機設定。',OWNER_NOT_CONFIGURED:'這個服務尚未設定；沒有排入工作。',
  OPERATIONAL_OWNERS_NOT_CONFIGURED:'執行服務尚未設定，不能推定沒有部位或已允許交易。',
  FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN:'測試命名空間不能核准財務操作。',
  FINANCIAL_ENVELOPE_NOT_COMMISSIONED:'尚未提供受本機核准的資金與風險提案。',
  RESPONSE_UNKNOWN:'未收到可確認的回應。原命令可能已執行；請用相同命令重試核對。',
  COMMAND_IN_PROGRESS:'原命令仍在執行或等待租期到期。請稍後使用相同命令核對。',
  PAPER_RUNTIME_ATTACHMENT_REQUIRED:'PAPER 已受理，獨立 runtime 尚待接管；目前不代表已在運作。',
  RUNTIME_NOT_CONFIGURED:'真實 runtime 尚未設定，交易仍停用。',
  CONTROL_OPERATION_FAILED:'控制操作失敗。請保留關聯 ID 並查看服務診斷。',
  DTO_VALIDATION_FAILED:'輸入不符合目前版本的 API 契約。',
};
export const reasonText=(code:string)=>reasons[code]??'請展開來源證據，依此原因修正設定或等待核對。';
