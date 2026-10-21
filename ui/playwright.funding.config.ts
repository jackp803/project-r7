import {defineConfig} from '@playwright/test';
import path from 'node:path';

const artifacts=path.resolve(process.env.R7_BROWSER_ARTIFACT_ROOT!);
export default defineConfig({
  testDir:'./qa',testMatch:'recorded-funding.case.ts',fullyParallel:false,workers:1,
  timeout:30_000,expect:{timeout:5_000},retries:0,
  outputDir:path.join(artifacts,'results'),
  reporter:[['line'],['json',{outputFile:path.join(artifacts,'results.json')}]],
  use:{browserName:'chromium',channel:process.env.R7_BROWSER_CHANNEL??'msedge',headless:true,
    viewport:{width:1440,height:960},actionTimeout:8_000,trace:'off',video:'off',screenshot:'off'},
  webServer:['pending','finalized'].map((profile,index)=>({
    command:`py -3.12 qa/serve_recorded_funding.py --profile ${profile} --port ${8780+index}`,
    url:`http://127.0.0.1:${8780+index}/api/v1/auth/status`,reuseExistingServer:false,
    timeout:90_000,stdout:'ignore',stderr:'pipe',
  })),
});
