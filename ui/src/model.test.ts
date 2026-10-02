import {describe,expect,it} from 'vitest';
import {metric,utcDisplay,progressLabel,temporalFacts,revision,approvalBlock} from './model';

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
});
