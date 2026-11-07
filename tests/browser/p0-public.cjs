// Production verification only: anonymous browser, at most two successful fixed PINGs.
// Never accepts an operator credential or performs authorized inference/device commands.
if(process.env.GITHUB_ACTIONS!=='true'||process.env.RUNNER_ENVIRONMENT!=='github-hosted')throw new Error('External GitHub-hosted runner required; do not launch a local browser.');
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const crypto=require('node:crypto');
const target='https://liveops.pcdoctor.ai/';
const out=path.resolve('artifacts/p0-public');
const report={target,started_at:new Date().toISOString(),vantage:'github-hosted-external',run_url:`https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`,checkout_commit:process.env.GITHUB_SHA,deployed_commit:null,credential_rotation:false,checks:[],pings:[],pageerrors:[],blocked_writes:[]};
function check(name,pass,detail){report.checks.push({name,status:pass?'PASS':'FAIL',detail});}
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
async function api(context,endpoint,method='GET'){
 const r=await context.request.fetch(target+endpoint,{method,timeout:15000,...(method==='POST'?{data:{topic:'safety'}}:{})});
 let value=null;if((r.headers()['content-type']||'').includes('application/json'))try{value=await r.json();}catch{}
 return {http:r.status(),challenge:r.headers()['cf-mitigated']==='challenge',value};
}
(async()=>{
 await fs.mkdir(out,{recursive:true});const browser=await chromium.launch();report.chromium=browser.version();
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US',serviceWorkers:'block'});const page=await context.newPage();page.setDefaultTimeout(10000);
 page.on('pageerror',e=>report.pageerrors.push(e.message));
 await context.route('**/*',route=>{const r=route.request(),u=new URL(r.url());if(!['GET','HEAD'].includes(r.method())&&!u.pathname.startsWith('/cdn-cgi/challenge-platform/')&&!(u.origin===new URL(target).origin&&['/api/liveops/ping','/api/liveops/test_ai'].includes(u.pathname))){report.blocked_writes.push({path:u.pathname,method:r.method()});return route.abort();}return route.continue();});
 try{
  const response=await page.goto(target,{waitUntil:'domcontentloaded',timeout:30000});report.https=await response.securityDetails();
  await page.locator('#console').waitFor({state:'visible',timeout:20000}).catch(()=>{});
  const present=await page.locator('#console').count();check('External public console loads',Boolean(present),{initial_http:response.status(),title:await page.title()});
  const status=await api(context,'api/liveops/status');const evidence=await api(context,'api/liveops/evidence');
  check('Public status JSON',status.http===200&&Boolean(status.value),{http:status.http,challenge:status.challenge});
  check('Public evidence JSON',evidence.http===200&&Array.isArray(evidence.value),{http:evidence.http,challenge:evidence.challenge});
  report.telemetry_timestamp=status.value?.telemetry_timestamp||null;
  report.components=Object.fromEntries(Object.entries(status.value?.components||{}).map(([k,v])=>[k,{status:v?.status,latency_ms:v?.latency_ms}]));
  report.archive={count:Array.isArray(evidence.value)?evidence.value.length:null,classifications:Array.isArray(evidence.value)?[...new Set(evidence.value.map(x=>x.classification))]:[],timestamps:Array.isArray(evidence.value)?[...new Set(evidence.value.map(x=>x.archive_timestamp))]:[]};
  // Independent negative HTTP probes; stop immediately if inference is unexpectedly allowed.
  for(const method of ['GET','POST']){for(const suffix of ['', '?token=invalid-qa-credential']){const r=await api(context,'api/liveops/test_ai'+suffix,method);check('Anonymous inference rejected '+method+(suffix?' bogus-query':''),[401,403].includes(r.http)&&!r.challenge&&r.value?.error==='OPERATOR_AUTH_REQUIRED',{http:r.http,challenge:r.challenge,error:r.value?.error||null});if(r.http===200){report.stop_reason='Unexpected anonymous inference acceptance; no further active calls';return;}}}
  if(!present){await page.screenshot({path:path.join(out,'external-blocked.png'),fullPage:true});for(const name of ['Two distinct verified PONG CIDs','Fresh public telemetry refresh','Historical records clearly separated','Desktop EN/ES and mobile views','No public URL credential capture'])check(name,false,'BLOCKED: external application not reached; no challenge bypass attempted.');return;}
  check('English default',await page.locator('html').getAttribute('lang')==='en');
  const html=await page.content(),candidate=await fs.readFile('site/index.html','utf8');report.rendered_html_sha256=hash(html);report.candidate_html_sha256=hash(candidate);
  check('No public URL credential capture',!html.includes('window.authenticateOperator')&&!html.includes('sessionStorage.setItem("inneros_operator_token"'), 'Inspects the actually served frontend, not repository CI.');
  await page.screenshot({path:path.join(out,'desktop-en-full.png'),fullPage:true});
  await page.locator('#btn-op-status').click();await page.waitForFunction(()=>['COMPLETED','FAILED','RESTRICTED'].includes(document.querySelector('#op-stage')?.textContent));await page.locator('#console').screenshot({path:path.join(out,'current-telemetry.png')});
  const fresh=await api(context,'api/liveops/status');check('Fresh public telemetry refresh',Boolean(fresh.value?.telemetry_timestamp&&fresh.value.telemetry_timestamp!==report.telemetry_timestamp),{before:report.telemetry_timestamp,after:fresh.value?.telemetry_timestamp});
  for(let i=0;i<2;i++){
   if(i)await page.waitForTimeout(11000);
   const start=Date.now(),promise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/liveops/ping',{timeout:22000});
   await page.locator('#btn-op-ping').click();const r=await promise;let value=null;try{value=await r.json();}catch{}
   await page.waitForFunction(()=>['COMPLETED','FAILED','RESTRICTED'].includes(document.querySelector('#op-stage')?.textContent),{timeout:22000});
   const cid=value?.correlation_id,reply=value?.agent_response||'',stamp=Date.parse(value?.timestamp||''),log=await page.locator('#op-log').innerText();
   const pass=r.status()===200&&value?.ok===true&&typeof cid==='string'&&/^CID-LIVE-PING-[A-F0-9]+$/.test(cid)&&reply.includes(cid)&&/\bPONG\b/.test(reply)&&stamp>=start-2000&&stamp<=Date.now()+2000&&Number.isFinite(value?.latency_ms)&&log.includes(cid)&&log.includes('PONG');
   report.pings.push({status:pass?'PASS':'FAIL',http:r.status(),correlation_id:pass?cid:null,latency_ms:value?.latency_ms,timestamp:value?.timestamp,exact_cid_in_pong:typeof cid==='string'&&reply.includes(cid)&&/\bPONG\b/.test(reply),transport:value?.transport,proof_scope:'Public server response and browser rendering; raw Mattermost sender/post identity not independently exposed.'});
   check('Browser PING '+(i+1)+' receives fresh correlated PONG',pass,{http:r.status(),error:value?.error||null});await page.locator('#console').screenshot({path:path.join(out,'ping-'+(i+1)+'.png')});
  }
  check('Two distinct verified PONG CIDs',report.pings.length===2&&report.pings.every(p=>p.status==='PASS')&&report.pings[0].correlation_id!==report.pings[1].correlation_id);
  await page.locator('#btn-op-ai').click();await page.waitForFunction(()=>['COMPLETED','FAILED','RESTRICTED'].includes(document.querySelector('#op-stage')?.textContent));check('Public AI button requires authorization',await page.locator('#op-stage').innerText()==='RESTRICTED');await page.locator('#console').screenshot({path:path.join(out,'inference-gated.png')});
  await page.locator('#btn-op-evidence').click();await page.waitForFunction(()=>['COMPLETED','FAILED','RESTRICTED'].includes(document.querySelector('#op-stage')?.textContent));check('Historical records clearly separated',report.archive.classifications.every(c=>c==='RECORDED_TEST_RESULT')&&/historical/i.test(await page.locator('#btn-op-evidence').innerText())&&/historical/i.test(await page.locator('#live-check-result').innerText()));await page.locator('#console').screenshot({path:path.join(out,'historical-records.png')});
  await page.goto(target+'?lang=es',{waitUntil:'domcontentloaded'});await page.locator('#console').waitFor();check('Spanish direct URL',await page.locator('html').getAttribute('lang')==='es');await page.screenshot({path:path.join(out,'desktop-es-full.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});const dims=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));check('Mobile 390px fits',dims.width>=dims.scrollWidth,dims);await page.screenshot({path:path.join(out,'mobile-es-full.png'),fullPage:true});check('No uncaught application JavaScript errors',report.pageerrors.length===0,report.pageerrors);
 }catch(e){check('Production browser verification completes',false,e.message.split('\n')[0]);await page.screenshot({path:path.join(out,'browser-error.png'),fullPage:true}).catch(()=>{});}
 finally{report.finished_at=new Date().toISOString();await context.close();await browser.close();await fs.writeFile(path.join(out,'results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({checks:report.checks,pings:report.pings,finished_at:report.finished_at},null,2));}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
