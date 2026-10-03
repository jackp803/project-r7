import {describe,expect,it} from 'vitest';
import {metric,utcDisplay,progressLabel,temporalFacts,revision,approvalBlock,deploymentActivationBlock,canPauseDeployment} from './model';

describe('truthful display and command prerequisites',()=>{
  it('keeps unavailable distinct from an actual zero and does no floating financial math',()=>{
    expect(metric(null)).toBe('未提供'); expect(metric('0')).toBe('0'); expect(metric('0.0000000000000000001')).toBe('0.0000000000000000001');
  });
  it('changes only explicit timezone display, not the source UTC identity',()=>{
    const source='2026-10-03T00:00:00Z';
    expect(utcDisplay(source,'UTC')).toContain('00:00:00');
    expect(utcDisplay(source,'Asia/Taipei')).toContain('08:00:00'); expect(source).toBe('2026-10-03T00:00:00Z');
    expect(utcDisplay('invalid','UTC')).toBe('未知');
  });
  it('never invents progress for a stage without measured total',()=>{
    expect(progressLabel(null,null)).toBe('未提供完成比例'); expect(progressLabel(3,5)).toBe('3 / 5');
    expect(progressLabel(6,5)).toBe('未提供完成比例');
  });
  it('separates four-hour evaluation, absolute entry validity and holding duration',()=>{
    const value=temporalFacts({definition:{rules:{evaluation_timeframe:'4h',exit_policy:{max_hold_seconds:14400}}},
      submission_validity:{from:'2026-10-03T00:00:00Z',until:'2026-10-03T04:00:00Z'}});
    expect(value.evaluation).toBe('4h'); expect(value.maxHold).toBe('14400 秒');
    expect(value.validity).toContain('2026-10-03T04:00:00Z');
    expect(temporalFacts({evaluation_timeframe:'4h'}).validity).toBe('未提供；不可從評估週期推定');
  });
  it('rejects unknown/unsafe revisions before sending a command',()=>{
    expect(revision(0)).toBe(0); for(const value of [null,-1,1.5,Number.MAX_SAFE_INTEGER+1,'3'])expect(()=>revision(value)).toThrow();
  });
  it('fixture approval is denied independently of a displayed canonical state',()=>{
    expect(approvalBlock('FIXTURE',{current_lifecycle_state:'READY_FOR_APPROVAL'})).toBe('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN');
    expect(approvalBlock('LOCAL_RESEARCH',{current_lifecycle_state:'READY_FOR_APPROVAL'})).toBe('FINANCIAL_ENVELOPE_NOT_COMMISSIONED');
  });
  it('confirmation uses an exact server preview and a changed strategy or revision invalidates it',()=>{
    const hash='sha256:'+'a'.repeat(64);
    const subject={identity:{strategy_id:'one',strategy_version:'1'},content_hash:hash,registry_revision:5,current_lifecycle_state:'READY_FOR_APPROVAL'};
    const preview={namespace:'LOCAL_RESEARCH',strategy_id:'one',strategy_version:'1',strategy_content_hash:hash,registry_revision:5,
      envelope_ref:'selected',envelope_hash:hash,risk_policy_hash:hash,financial_confirmation_available:true,
      release:{implementation_hash:hash,build_hash:hash,config_hash:hash,risk_policy_hash:hash,executable_revision:'a'.repeat(40)},
      envelope:{strategy_id:'one',strategy_version:'1',strategy_content_hash:hash,namespace:'LOCAL_RESEARCH',capital_ceiling_usdt:'100',risk_per_trade_usdt:'1'}};
    expect(approvalBlock('LOCAL_RESEARCH',subject,preview)).toBeNull();
    expect(approvalBlock('FIXTURE',subject,preview)).toBe('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN');
    expect(approvalBlock('LOCAL_RESEARCH',{...subject,registry_revision:6},preview)).toBe('APPROVAL_PREVIEW_SUBJECT_CHANGED');
    expect(approvalBlock('LOCAL_RESEARCH',subject,{...preview,strategy_version:'2'})).toBe('APPROVAL_PREVIEW_SUBJECT_CHANGED');
    expect(approvalBlock('LOCAL_RESEARCH',subject,{...preview,financial_confirmation_available:false})).toBe('CURRENT_APPROVAL_PROPOSAL_UNAVAILABLE');
    expect(approvalBlock('LOCAL_RESEARCH',subject,{...preview,release:{}})).toBe('CURRENT_APPROVAL_PROPOSAL_UNAVAILABLE');
    expect(approvalBlock('LOCAL_RESEARCH',{...subject,content_hash:undefined},{...preview,strategy_content_hash:undefined,
      envelope:{...preview.envelope,strategy_content_hash:undefined}})).toBe('APPROVAL_PREVIEW_SUBJECT_CHANGED');
  });
  it('deployment pause is separate from financial activation and exact current subject is required',()=>{
    const hash='sha256:'+'a'.repeat(64);const subject={identity:{strategy_id:'one',strategy_version:'1'},content_hash:hash,registry_revision:6,current_lifecycle_state:'LIVE'};
    const deployment={deployment_id:'deployment-'+'a'.repeat(64),strategy_id:'one',strategy_version:'1',strategy_content_hash:hash,
      registry_revision:6,lifecycle_state:'LIVE',namespace:'FIXTURE',financial_confirmation_available:false};
    expect(canPauseDeployment('FIXTURE',subject,deployment)).toBe(true);
    expect(deploymentActivationBlock('FIXTURE',subject,deployment)).toBe('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN');
    expect(canPauseDeployment('FIXTURE',{...subject,registry_revision:7},deployment)).toBe(false);
    expect(canPauseDeployment('FIXTURE',{...subject,current_lifecycle_state:'DEGRADED'},deployment)).toBe(false);
    expect(canPauseDeployment('FIXTURE',{...subject,content_hash:undefined},{...deployment,strategy_content_hash:undefined})).toBe(false);
    const approved={...subject,current_lifecycle_state:'APPROVED'};
    expect(deploymentActivationBlock('LOCAL_RESEARCH',approved,{...deployment,namespace:'LOCAL_RESEARCH',lifecycle_state:'APPROVED',financial_confirmation_available:true})).toBeNull();
    expect(deploymentActivationBlock('LOCAL_RESEARCH',approved,{...deployment,namespace:'LOCAL_RESEARCH',lifecycle_state:'APPROVED',financial_confirmation_available:true,registry_revision:5})).toBe('EXACT_DEPLOYMENT_SUBJECT_REQUIRED');
  });
});
