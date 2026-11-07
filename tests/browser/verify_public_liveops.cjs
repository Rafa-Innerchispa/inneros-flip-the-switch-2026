// Browser verification of Public LiveOps Console & Real Switch Ping
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TEST_URL || 'http://192.168.1.5:8790/';
const evidenceDir = path.resolve('docs/evidence');
const artifactDir = path.resolve('C:/Users/hrlg/.gemini/antigravity/brain/56250828-9f3d-47ae-94bc-16cdb57b9c91');

if (!fs.existsSync(evidenceDir)) fs.mkdirSync(evidenceDir, { recursive: true });

async function run() {
  console.log(`Starting Public Browser QA against ${targetUrl}...`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    locale: 'en-US'
  });
  const page = await context.newPage();
  const report = {};

  try {
    // 1. Initial Load
    console.log('[1/6] Loading LiveOps Console in Chromium...');
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 15000 });
    const initialLang = await page.getAttribute('html', 'lang');
    console.log(`  Initial lang: ${initialLang}`);
    report.default_lang_en = (initialLang === 'en');
    await page.waitForSelector('#s-switch.ok, #s-switch.tcp', { timeout: 8000 });
    await page.screenshot({ path: path.join(evidenceDir, 'public_qa_01_loaded.png') });

    // 2. Public Ping #1
    console.log('[2/6] Executing Public Switch Ping #1 via Browser...');
    await page.click('#btn-op-ping');
    await page.waitForFunction(() => {
      const stage = document.getElementById('op-stage')?.textContent?.trim();
      return stage === 'COMPLETED' || stage === 'FAILED';
    }, { timeout: 15000 });

    const stage1 = await page.textContent('#op-stage');
    const cid1 = await page.textContent('#op-cid');
    const lat1 = await page.textContent('#op-latency');
    const log1 = await page.textContent('#op-log');
    console.log(`  Ping #1: Stage=${stage1}, CID=${cid1}, Latency=${lat1}`);
    report.ping1 = { stage: stage1, cid: cid1, latency: lat1, ok: stage1 === 'COMPLETED' };
    await page.screenshot({ path: path.join(evidenceDir, 'public_qa_02_ping1.png') });

    // 3. Verify Local AI is Gated (401 RESTRICTED)
    console.log('[3/6] Testing Unauthenticated Local AI (Expecting RESTRICTED)...');
    await page.click('#btn-op-ai');
    await page.waitForFunction(() => {
      const stage = document.getElementById('op-stage')?.textContent?.trim();
      return stage === 'RESTRICTED';
    }, { timeout: 8000 });
    const stageAI = await page.textContent('#op-stage');
    console.log(`  AI Gate Result: Stage=${stageAI} (Correctly protected)`);
    report.ai_gated = (stageAI === 'RESTRICTED');
    await page.screenshot({ path: path.join(evidenceDir, 'public_qa_03_ai_restricted.png') });

    // 4. Wait for IP Cooldown
    console.log('[4/6] Waiting 11 seconds for IP rate limit cooldown...');
    await page.waitForTimeout(11000);

    // 5. Public Ping #2
    console.log('[5/6] Executing Public Switch Ping #2 via Browser...');
    await page.click('#btn-op-ping');
    await page.waitForFunction(() => {
      const stage = document.getElementById('op-stage')?.textContent?.trim();
      return stage === 'COMPLETED' || stage === 'FAILED';
    }, { timeout: 15000 });

    const stage2 = await page.textContent('#op-stage');
    const cid2 = await page.textContent('#op-cid');
    const lat2 = await page.textContent('#op-latency');
    const log2 = await page.textContent('#op-log');
    console.log(`  Ping #2: Stage=${stage2}, CID=${cid2}, Latency=${lat2}`);
    report.ping2 = { stage: stage2, cid: cid2, latency: lat2, ok: stage2 === 'COMPLETED' };
    await page.screenshot({ path: path.join(evidenceDir, 'public_qa_04_ping2.png') });

    // 6. Validation
    report.unique_cids = (cid1 !== cid2 && cid1.startsWith('CID-') && cid2.startsWith('CID-'));
    report.both_passed = (report.ping1.ok && report.ping2.ok);

    console.log('\n=== PUBLIC QA SUMMARY ===');
    console.log(`Default Lang EN: ${report.default_lang_en}`);
    console.log(`Ping 1: ${report.ping1.stage} (${report.ping1.cid}, ${report.ping1.latency})`);
    console.log(`Ping 2: ${report.ping2.stage} (${report.ping2.cid}, ${report.ping2.latency})`);
    console.log(`Unique CIDs: ${report.unique_cids}`);
    console.log(`AI Gate RESTRICTED: ${report.ai_gated}`);
    console.log(`Overall Result: ${report.both_passed && report.unique_cids && report.ai_gated ? 'PASS' : 'FAIL'}`);

    // Sync evidence to artifact dir
    for (const f of ['public_qa_01_loaded.png', 'public_qa_02_ping1.png', 'public_qa_03_ai_restricted.png', 'public_qa_04_ping2.png']) {
      const src = path.join(evidenceDir, f);
      const dst = path.join(artifactDir, f);
      if (fs.existsSync(src)) fs.copyFileSync(src, dst);
    }

    fs.writeFileSync(path.join(evidenceDir, 'public_qa_report.json'), JSON.stringify(report, null, 2));

  } catch (err) {
    console.error('Browser QA Error:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

run();
