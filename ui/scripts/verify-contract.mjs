import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import openapiTS,{astToString} from 'openapi-typescript';

const source=await readFile(new URL('../../contracts/control_api_v0_2.openapi.json',import.meta.url));
if(source.length>2_000_000)throw new Error('Bounded local contract required');
const document=JSON.parse(source); const stack=[document];
while(stack.length){
  const item=stack.pop(); if(item&&typeof item==='object'){
    if('$ref' in item&&!item.$ref.startsWith('#/'))throw new Error('External schema reference forbidden');
    stack.push(...Object.values(item));
  }
}
const generated='/** Generated from the committed local R7 OpenAPI. Do not edit. */\n'+astToString(await openapiTS(document));
const target=new URL('../src/api.generated.ts',import.meta.url);
if(process.argv.includes('--write'))await writeFile(target,generated);
else if(await readFile(target,'utf8')!==generated)throw new Error('API type drift; run npm run types');
console.log(JSON.stringify({contract_sha256:createHash('sha256').update(source).digest('hex'),
  generated_sha256:createHash('sha256').update(generated).digest('hex'),status:'PASS'}));
