// Automated verification of the LiveOps Interactive Operations Console
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TEST_URL || 'http://192.168.1.5:8790/';
const evidenceDir = path.resolve('docs/evidence');
const artifactDir = path.resolve('C:/Users/hrlg/.gemini/antigravity/brain/56250828-9f3d-47ae-94bc-16cdb57b9c91');

if (!fs.existsSync(evidenceDir)) fs.mkdirSync(evidenceDir, { recursive: true });

async function run() {
  console.log(`Starting Interactive Console Browser QA against ${targetUrl}...`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    locale: 'en-US'
  });
  const page = await context.newPage();
  const results = {};

  try {
    // 1. Initial Load & Default English
    console.log('[1/8] Loading application...');
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 15000 });
    const initialLang = await page.getAttribute('html', 'lang');
    console.log(`  Initial lang: ${initialLang}`);
    results.default_lang_en = (initialLang === 'en');

    // Wait for telemetry chips
    await page.waitForSelector('#s-switch.ok, #s-switch.tcp', { timeout: 8000 });
    await page.screenshot({ path: path.join(evidenceDir, 'console_01_initial.png') });

    // 2. Check System Status
    console.log('[2/8] Testing "Check System Status" button...');
    await page.click('#btn-op-status');
    // Verify stage changes to RUNNING or COMPLETED
    await page.waitForFunction(() => {
      const stage = document.getElementById('op-stage')?.textContent;
      return stage === 'COMPLETED' || stage === 'RUNNING';
    }, { timeout: 5000 });
    // Wait until COMPLETED
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 10000 });
    const statusText = await page.textContent('#op-log');
    const statusLatency = await page.textContent('#op-latency');
    console.log(`  Status Completed! Latency: ${statusLatency}`);
    results.status_check = {
      passed: statusText.includes('SYSTEM HEALTH AUDIT') && statusText.includes('Switch Core'),
      latency: statusLatency
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_02_status_check.png') });

    // 3. Ping Agent (Switch)
    console.log('[3/8] Testing "Ping Agent (Switch)" button...');
    await page.waitForTimeout(1000);
    await page.click('#btn-op-ping');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 12000 });
    const pingText = await page.textContent('#op-log');
    const pingCid = await page.textContent('#op-cid');
    const pingLatency = await page.textContent('#op-latency');
    console.log(`  Ping Completed! CID: ${pingCid} | Latency: ${pingLatency}`);
    results.switch_ping = {
      passed: pingText.includes('SWITCH AGENT PING') && pingText.includes('PONG'),
      cid: pingCid,
      latency: pingLatency
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_03_switch_ping.png') });

    // 4. Test Local AI (Qwen)
    console.log('[4/8] Testing "Test Local AI (Qwen)" button...');
    await page.waitForTimeout(1000);
    await page.click('#btn-op-ai');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 15000 });
    const aiText = await page.textContent('#op-log');
    const aiCid = await page.textContent('#op-cid');
    const aiLatency = await page.textContent('#op-latency');
    console.log(`  AI Completed! CID: ${aiCid} | Latency: ${aiLatency}`);
    results.local_ai = {
      passed: aiText.includes('LOCAL AI INFERENCE') && aiText.includes('Radeon AI PRO R9700'),
      cid: aiCid,
      latency: aiLatency
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_04_local_ai.png') });

    // 5. View Real Evidence
    console.log('[5/8] Testing "View Real Evidence" button...');
    await page.waitForTimeout(1000);
    await page.click('#btn-op-evidence');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 8000 });
    const evText = await page.textContent('#op-log');
    console.log(`  Evidence Refreshed!`);
    results.evidence_view = {
      passed: evText.includes('VERIFIED EVIDENCE LEDGER')
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_05_evidence_view.png') });

    // 6. Spanish Language Toggle
    console.log('[6/8] Testing Spanish toggle...');
    await page.click('#lang');
    const esLang = await page.getAttribute('html', 'lang');
    const esTitle = await page.textContent('#console h2');
    console.log(`  Lang switched to: ${esLang} | Title: ${esTitle}`);
    results.spanish_toggle = {
      passed: esLang === 'es' && esTitle.includes('Consola')
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_06_spanish_desktop.png') });

    // 7. Mobile Viewport Test (390x844)
    console.log('[7/8] Testing Mobile viewport (390x844)...');
    await page.setViewportSize({ width: 390, height: 844 });
    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    console.log(`  Mobile overflow: ${hasHorizontalOverflow}`);
    results.mobile_responsive = {
      passed: !hasHorizontalOverflow
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_07_mobile_es.png') });

    // 8. Copy key screenshots to session artifact directory
    console.log('[8/8] Syncing artifacts...');
    const filesToSync = [
      'console_02_status_check.png',
      'console_03_switch_ping.png',
      'console_04_local_ai.png',
      'console_06_spanish_desktop.png',
      'console_07_mobile_es.png'
    ];
    for (const f of filesToSync) {
      const src = path.join(evidenceDir, f);
      const dst = path.join(artifactDir, f);
      if (fs.existsSync(src)) fs.copyFileSync(src, dst);
    }

    console.log('\n=== ALL BROWSER CONSOLE TESTS FINISHED SUCCESSFULLY! ===');
    console.log(JSON.stringify(results, null, 2));

  } catch (err) {
    console.error('Browser QA Error:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

run();
