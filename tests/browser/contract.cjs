// Pure DOM unit tests. SYNTHETIC QA inputs only; no browser, network or device access.
const {parseHTML}=require('linkedom');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=path.resolve(process.argv[2]||'site/index.html');
const out=path.resolve(process.argv[3]||'artifacts/browser-unit');
const html=fs.readFileSync(source,'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const tests=[];
async function setup(search=''){
  const {document}=parseHTML(html);
  const state={status:'ok',evidence:'empty',policy:true};
  const fixture=()=>({components:{switch_core:{status:'CONNECTED'},mattermost:{status:'CONNECTED'},qwen_local_rocm:{status:'ACTIVE_INFERENCE_READY'},human_safety_gate:state.policy?{status:'POLICY_CONFIGURED'}:{},evidence_ledger:{status:'UNKNOWN'}}});
  const context=vm.createContext({document,window:{location:{search}},localStorage:{getItem:()=>null,setItem:()=>{}},URLSearchParams,AbortController,setTimeout,clearTimeout,setInterval:()=>0,fetch:async url=>{
    if(url.endsWith('/status')){if(state.status==='network-error')throw new Error('SYNTHETIC_QA_NETWORK_ERROR');return {ok:state.status==='ok',json:async()=>fixture()};}
    return {ok:true,json:async()=>state.evidence==='error'?[{error:'SYNTHETIC_QA_ARCHIVE_READ_ERROR'}]:[]};
  }});
  vm.runInContext(script,context);
  await new Promise(resolve=>setImmediate(resolve));
  return {document,state,poll:()=>vm.runInContext('poll()',context)};
}
async function check(name,fn){try{const detail=await fn();tests.push({name,status:'PASS',detail});}catch(e){tests.push({name,status:'FAIL',detail:e.message});}}
function assert(ok,message){if(!ok)throw new Error(message);}
(async()=>{
  await check('Fresh visit defaults to English',async()=>{const s=await setup();assert(s.document.documentElement.lang==='en','Default language is not English');});
  await check('Spanish query and language selector work',async()=>{const s=await setup('?lang=es');assert(s.document.documentElement.lang==='es','Spanish query ignored');s.document.querySelector('#lang').click();assert(s.document.documentElement.lang==='en','Language selector did not switch back');});
  await check('Empty evidence does not invent an operation',async()=>{const s=await setup();assert(s.document.querySelector('#operation-title').textContent.includes('No verified operation'),'Empty evidence shown as an operation');});
  await check('Failed telemetry removes previous healthy colors',async()=>{const s=await setup();s.state.status='http-error';await s.poll();assert(!s.document.querySelector('#s-switch').classList.contains('ok'),'Old healthy indicator survives telemetry failure');assert(s.document.querySelector('[data-i18n=sSwitch]').textContent.includes('Unavailable'),'Failure remains indefinitely Checking');});
  await check('One failed endpoint preserves the other valid empty response',async()=>{const s=await setup();s.state.status='network-error';await s.poll();assert(s.document.querySelector('#evidence-records').textContent.includes('No recorded events'),'Valid empty evidence response was discarded with failed telemetry');});
  await check('Archive error sentinel is not a recorded test operation',async()=>{const s=await setup();s.state.evidence='error';await s.poll();assert(s.document.querySelector('#operation-class').textContent!=='Recorded test operation','Archive error is mislabeled as recorded operation');assert(s.document.querySelector('#evidence-records').textContent.includes('unavailable'),'Archive error lacks unavailable state');});
  await check('Missing policy telemetry does not claim configured policy',async()=>{const s=await setup();s.state.policy=false;await s.poll();assert(s.document.querySelector('[data-i18n=sGate]').textContent!=='Policy configured','Policy configured is claimed without supporting telemetry');});
  fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'unit-results.json'),JSON.stringify({classification:'SYNTHETIC_QA_CONTRACT_ONLY',source,at:new Date().toISOString(),tests},null,2));
  for(const t of tests)console.log(t.status+' '+t.name+(t.detail?' — '+t.detail:''));
  if(tests.some(t=>t.status==='FAIL'))process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1;});
