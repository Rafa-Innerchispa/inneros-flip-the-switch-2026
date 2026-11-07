// Read-only Chromium audit. Never authenticates, sends application POSTs, or actuates hardware.
const {chromium}=require('playwright');
const AxeBuilder=require('@axe-core/playwright').default;
const fs=require('node:fs/promises');
const path=require('node:path');
const crypto=require('node:crypto');
const http=require('node:http');
const out=path.resolve(process.env.QA_ARTIFACT_DIR||'artifacts/browser-qa');
const target='https://liveops.pcdoctor.ai/';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const report={target,started_at:new Date().toISOString(),vantage:process.env.GITHUB_ACTIONS==='true'?'github-hosted-external':'unspecified',runner_environment:process.env.RUNNER_ENVIRONMENT||null,runner_os:process.platform,run_url:process.env.GITHUB_RUN_ID?`https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`:null,checkout_commit:process.env.GITHUB_SHA||null,checks:[],pageerrors:[],http_errors:[],blocked_application_writes:[]};
function result(name,ok,detail){report.checks.push({name,status:ok?'PASS':'FAIL',detail});}
function blocked(name,detail){report.checks.push({name,status:'BLOCKED',detail});}
const sensitive=(value)=>{const found=[];function walk(v,p=''){if(v&&typeof v==='object')for(const [k,x]of Object.entries(v)){if(/password|access_token|api_key|private_key|authorization|bearer/i.test(k)&&x)found.push(p+'.'+k);walk(x,p+'.'+k);}else if(typeof v==='string'&&(/-----BEGIN .*PRIVATE KEY-----/.test(v)||/\b(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{25,}|mm[a-z0-9]{24,})\b/.test(v)))found.push(p);}walk(value);return found;};
async function publicAudit(browser){
 const context=await browser.newContext({viewport:{width:1920,height:1080},locale:'en-US',timezoneId:'America/Guayaquil',serviceWorkers:'block',recordVideo:{dir:path.join(out,'public-video'),size:{width:1920,height:1080}}});
 const page=await context.newPage();page.setDefaultTimeout(8000);
 page.on('pageerror',e=>report.pageerrors.push(e.message));
 page.on('response',r=>{if(r.status()>=400){const u=new URL(r.url());report.http_errors.push({url:u.origin+(u.pathname.startsWith('/cdn-cgi/')?'/cdn-cgi/[ephemeral-challenge-path-redacted]':u.pathname),status:r.status()});}});
 await context.route('**/*',route=>{const req=route.request(),u=new URL(req.url());if(!['GET','HEAD'].includes(req.method())&&!u.pathname.startsWith('/cdn-cgi/challenge-platform/')){report.blocked_application_writes.push({path:u.pathname,method:req.method()});return route.abort();}return route.continue();});
 try{
  const response=await page.goto(target,{waitUntil:'domcontentloaded',timeout:30000});
  report.https={initial_status:response.status(),security:await response.securityDetails()};
  await page.locator('#home').waitFor({state:'visible',timeout:20000}).catch(()=>{});
  const appPresent=await page.locator('#home').count();
  report.public_title=await page.title();result('Public application renders from external Chromium',Boolean(appPresent),{initial_status:response.status(),title:report.public_title});
  const observed={};for(const endpoint of ['status','evidence']){try{const r=await context.request.get(target+'api/liveops/'+endpoint,{timeout:12000}),type=r.headers()['content-type']||'',json=type.includes('application/json');result('Public '+endpoint+' endpoint',r.ok()&&json,{http:r.status(),content_type:type,edge_challenge:r.headers()['cf-mitigated']==='challenge'});if(r.ok()&&json){const value=await r.json(),leaks=sensitive(value);result('No obvious credentials in '+endpoint,leaks.length===0,{sensitive_key_paths:leaks});if(!leaks.length){observed[endpoint]=value;await fs.writeFile(path.join(out,'public-api-'+endpoint+'.json'),JSON.stringify(value,null,2));}}else blocked('Credential review '+endpoint,'No application JSON available; response cannot certify data minimization.');}catch(e){result('Public '+endpoint+' endpoint',false,e.message.split('\n')[0]);}}
  for(const resource of ['api/operator','server.py','.env']){try{const r=await context.request.get(target+resource,{timeout:10000}),challenge=r.headers()['cf-mitigated']==='challenge'||(!appPresent&&(r.headers()['content-type']||'').includes('text/html'));if(challenge)blocked('Protection check '+resource,{http:r.status(),reason:'Edge challenge; application protection cannot be certified'});else result('Protection check '+resource,[401,403,404].includes(r.status()),{http:r.status()});}catch(e){blocked('Protection check '+resource,e.message.split('\n')[0]);}}

  if(!appPresent){await page.screenshot({path:path.join(out,'external-public-blocked.png'),fullPage:true});for(const name of ['Desktop EN/ES application views','Mobile application view','Live service states','Live API rendering and refresh','Live evidence and provenance','Public app accessibility','Physical operation controls'])blocked(name,'Application not reached; edge challenge or loading error. No CAPTCHA was solved and no protection was bypassed.');return;}
  const raw=await response.body();report.deployed_html_sha256=sha(raw);
  const source=await fs.readFile('site/index.html','utf8');report.matches_candidate_html=sha(raw.toString().replace(/\r\n/g,'\n'))===sha(source.replace(/\r\n/g,'\n'));

  report.live_components=observed.status?.components;report.archive_record_count=Array.isArray(observed.evidence)?observed.evidence.length:null;
  await page.locator('#s-chat.ok, #s-chat.tcp').waitFor({timeout:12000}).catch(()=>{});
  result('English default',await page.locator('html').getAttribute('lang')==='en');
  await page.screenshot({path:path.join(out,'desktop-en-full.png'),fullPage:true});
  await page.locator('.strip').screenshot({path:path.join(out,'telemetry-real.png')});
  await page.locator('#incident').screenshot({path:path.join(out,'records-real.png')});
  const firstTimestamp=observed.status?.telemetry_timestamp;let refreshed=null;const refreshPromise=page.waitForResponse(r=>r.url().endsWith('/api/liveops/status')&&r.status()===200,{timeout:18000}).then(r=>r.json()).catch(()=>null);
  for(const hash of ['#incident','#evidence','#architecture']){await page.locator('nav a[href="'+hash+'"]').click();result('Navigation '+hash,(new URL(page.url()).hash===hash));}
  const a11y=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();await fs.writeFile(path.join(out,'axe-public.json'),JSON.stringify(a11y,null,2));result('Automated WCAG checks',!a11y.violations.length,a11y.violations.map(v=>({id:v.id,impact:v.impact,count:v.nodes.length})));
  await page.locator('#lang').click();result('Spanish selector',await page.locator('html').getAttribute('lang')==='es');await page.screenshot({path:path.join(out,'desktop-es-full.png'),fullPage:true});
  refreshed=await refreshPromise;result('Automatic telemetry refresh',Boolean(refreshed?.telemetry_timestamp&&refreshed.telemetry_timestamp!==firstTimestamp),{first:firstTimestamp,second:refreshed?.telemetry_timestamp});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile-es-full.png'),fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,visibleNav:[...document.querySelectorAll('.navlinks a')].filter(e=>e.getClientRects().length).map(e=>e.textContent)}));result('Mobile has no horizontal overflow',mobile.scrollWidth<=mobile.width,mobile);result('Mobile section navigation visible',mobile.visibleNav.length>=4,mobile);
  const controls=await page.locator('button,input,form').evaluateAll(es=>es.map(e=>({tag:e.tagName,text:e.textContent,label:e.getAttribute('aria-label'),action:e.getAttribute('action')})));result('No public physical-operation controls',!controls.some(e=>/actuate|power|breaker|relay|reboot|shutdown|reset|hardware|physical|delete/i.test((e.text||'')+' '+(e.label||''))),controls);

  result('No uncaught JavaScript errors',!report.pageerrors.length,report.pageerrors);
 }catch(e){result('Public browser run completed',false,e.message.split('\n')[0]);await page.screenshot({path:path.join(out,'public-run-error.png'),fullPage:true}).catch(()=>{});}
 finally{await context.close();}
}
async function candidateAudit(browser){
 const html=await fs.readFile('site/index.html');
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html);});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 const context=await browser.newContext({viewport:{width:1440,height:900},locale:'en-US'});
 let fail=false,archiveError=false;
 await context.route('**/api/liveops/*',route=>{if(!['GET','HEAD'].includes(route.request().method()))return route.abort();if(route.request().url().endsWith('/status'))return route.fulfill({status:fail?503:200,contentType:'application/json',body:JSON.stringify({components:{switch_core:{status:'CONNECTED'},mattermost:{status:'CONNECTED'},qwen_local_rocm:{status:'ACTIVE_INFERENCE_READY'},human_safety_gate:{status:'POLICY_CONFIGURED'},evidence_ledger:{status:'UNKNOWN'}}})});return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(archiveError?[{error:'SYNTHETIC_QA_ARCHIVE_ERROR'}]:[])});});
 const page=await context.newPage();
 try{await page.goto(origin);await page.waitForFunction(()=>document.querySelector('#s-switch').classList.contains('ok'));
  await page.evaluate(()=>{const n=document.createElement('div');n.textContent='QA ONLY — LOCAL CANDIDATE / SYNTHETIC API CONTRACT — NOT LIVE TELEMETRY';n.style='position:fixed;bottom:0;left:0;right:0;z-index:9999;padding:10px;background:#fff;color:#000;font-weight:bold';document.body.append(n);});
  result('Candidate empty state contains no invented operation',(await page.locator('#operation-title').innerText()).includes('No verified operation'));
  await fs.mkdir(path.join(out,'candidate-qa-only'),{recursive:true});await page.screenshot({path:path.join(out,'candidate-qa-only','desktop-en.png'),fullPage:true});
  fail=true;await page.evaluate(()=>poll());result('Candidate removes stale healthy colors',await page.locator('.strip .dot.ok').count()===0);await page.screenshot({path:path.join(out,'candidate-qa-only','network-failure.png'),fullPage:true});
  fail=false;archiveError=true;await page.evaluate(()=>poll());result('Candidate archive errors are unavailable, not operations',(await page.locator('#operation-class').innerText())!=='Recorded test operation');
  await page.locator('#lang').click();await page.screenshot({path:path.join(out,'candidate-qa-only','desktop-es.png'),fullPage:true});
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:844});const dims=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));result('Candidate fits '+width+'px',dims.scrollWidth<=dims.width,dims);if(width===390){result('Candidate mobile navigation visible',await page.locator('.navlinks a:visible').count()>=4);await page.screenshot({path:path.join(out,'candidate-qa-only','mobile-es.png'),fullPage:true});}}
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();await fs.writeFile(path.join(out,'candidate-qa-only','axe.json'),JSON.stringify(axe,null,2));result('Candidate automated WCAG checks',!axe.violations.length,axe.violations.map(x=>({id:x.id,impact:x.impact,count:x.nodes.length})));
 }catch(e){result('Candidate browser contract completed',false,e.message);}
 finally{await context.close();await new Promise(resolve=>server.close(resolve));}
}
(async()=>{await fs.mkdir(out,{recursive:true});const browser=await chromium.launch();report.chromium=browser.version();try{await publicAudit(browser);await candidateAudit(browser);}finally{await browser.close();report.finished_at=new Date().toISOString();await fs.writeFile(path.join(out,'browser-results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({checks:report.checks,artifact_dir:out},null,2));}if(report.checks.some(x=>x.status==='FAIL'))process.exitCode=1;})().catch(e=>{console.error(e.message);process.exitCode=1;});
