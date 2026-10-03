import { defineConfig } from '@playwright/test';
import path from 'node:path';

const artifacts=path.resolve(import.meta.dirname,'../../../artifacts/S11-browser');
export default defineConfig({
  testDir: './qa', testMatch: '*.spec.ts', fullyParallel: false, workers: 1,
  timeout: 25_000, expect: {timeout: 4_000}, retries: 0,
  outputDir: path.join(artifacts,'results'),
  reporter: [['line'],['json',{outputFile:path.join(artifacts,'results.json')}]],
  use: {browserName:'chromium',channel:process.env.R7_BROWSER_CHANNEL??(process.platform==='win32'?'msedge':'chromium'),headless:true,viewport:{width:1440,height:960},actionTimeout:8_000,
    trace:'off',video:'off',screenshot:'off'},
  webServer: ['empty','research','paper','protected','temporal','approval','deployment'].map((profile,index)=>({
    command:`py -3.12 qa/serve_fixture.py --profile ${profile} --port ${8766+index}`,
    url:`http://127.0.0.1:${8766+index}/api/v1/auth/status`,reuseExistingServer:false,
    timeout:90_000,stdout:'ignore',stderr:'pipe',
  })),
});
