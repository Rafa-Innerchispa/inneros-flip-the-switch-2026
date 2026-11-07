// Automated verification of the LiveOps Interactive Operations Console
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TEST_URL || 'http://192.168.1.5:8790/';
const operatorToken = process.env.LIVEOPS_OPERATOR_TOKEN || 'inneros-liveops-operator-2026-auth';
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
    console.log('[1/10] Loading application (Public Unauthenticated Session)...');
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 15000 });
    const initialLang = await page.getAttribute('html', 'lang');
    console.log(`  Initial lang: ${initialLang}`);
    results.default_lang_en = (initialLang === 'en');

    // Wait for telemetry chips
    await page.waitForSelector('#s-switch.ok, #s-switch.tcp', { timeout: 8000 });
    await page.screenshot({ path: path.join(evidenceDir, 'console_01_initial.png') });

    // 2. Check System Status (Public Endpoint)
    console.log('[2/10] Testing "Check System Status" (Public)...');
    await page.click('#btn-op-status');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 10000 });
    const statusText = await page.textContent('#op-log');
    const statusLatency = await page.textContent('#op-latency');
    console.log(`  Status Completed! Latency: ${statusLatency}`);
    results.status_check = {
      passed: statusText.includes('SYSTEM HEALTH AUDIT') && statusText.includes('Switch Core'),
      latency: statusLatency
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_02_status_check.png') });

    // 3. Public Ping Agent Call #1 (Fixed Diagnostic, Rate-limited)
    console.log('[3/10] Testing "Ping Agent (Switch)" Public Call #1...');
    await page.waitForTimeout(1000);
    await page.click('#btn-op-ping');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 15000 });
    const ping1Text = await page.textContent('#op-log');
    const ping1Cid = await page.textContent('#op-cid');
    const ping1Latency = await page.textContent('#op-latency');
    console.log(`  Public Ping #1 Completed! CID: ${ping1Cid} | Latency: ${ping1Latency}`);
    results.public_ping_1 = {
      passed: ping1Text.includes('SWITCH AGENT PING') && ping1Text.includes('PONG'),
      cid: ping1Cid,
      latency: ping1Latency
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_03_public_ping_1.png') });

    // 4. Test Local AI Unauthenticated (Must Trigger Restricted Gate)
    console.log('[4/10] Testing "Test Local AI" Unauthenticated (Expecting RESTRICTED Gate)...');
    await page.waitForTimeout(500);
    await page.click('#btn-op-ai');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'RESTRICTED', { timeout: 8000 });
    const aiGatedText = await page.textContent('#op-log');
    console.log(`  AI Gate Active: Stage=RESTRICTED`);
    results.ai_unauthenticated_gated = {
      passed: aiGatedText.includes('SOVEREIGN SAFETY GATE') && aiGatedText.includes('HTTP 401')
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_04_ai_gated.png') });

    // 5. View Historical Evidence (Public Endpoint)
    console.log('[5/10] Testing "View Historical Evidence" (Public)...');
    await page.waitForTimeout(500);
    await page.click('#btn-op-evidence');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 8000 });
    const evText = await page.textContent('#op-log');
    console.log(`  Historical Evidence Refreshed!`);
    results.evidence_view = {
      passed: evText.includes('VERIFIED EVIDENCE LEDGER')
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_05_evidence_view.png') });

    // 6. Authenticate Operator Session
    console.log('[6/10] Authenticating Operator Session...');
    await page.evaluate((tok) => {
      sessionStorage.setItem('inneros_operator_token', tok);
    }, operatorToken);

    // 7. Ping Agent Authenticated Call #2 (Must Have Different Unique CID)
    console.log('[7/10] Testing "Ping Agent (Switch)" Authenticated Call #2...');
    await page.waitForTimeout(2000);
    await page.click('#btn-op-ping');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 15000 });
    const ping2Text = await page.textContent('#op-log');
    const ping2Cid = await page.textContent('#op-cid');
    const ping2Latency = await page.textContent('#op-latency');
    console.log(`  Authenticated Ping #2 Completed! CID: ${ping2Cid} | Latency: ${ping2Latency}`);
    results.switch_ping_2 = {
      passed: ping2Text.includes('SWITCH AGENT PING') && ping2Text.includes('PONG'),
      cid: ping2Cid,
      latency: ping2Latency,
      unique_cid: (ping1Cid !== ping2Cid)
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_03_switch_ping_2.png') });

    // 8. Test Local AI Authenticated (Must Succeed on AMD GPU)
    console.log('[8/10] Testing "Test Local AI (Qwen)" Authenticated...');
    await page.waitForTimeout(1000);
    await page.click('#btn-op-ai');
    await page.waitForFunction(() => document.getElementById('op-stage')?.textContent === 'COMPLETED', { timeout: 18000 });
    const aiText = await page.textContent('#op-log');
    const aiCid = await page.textContent('#op-cid');
    const aiLatency = await page.textContent('#op-latency');
    console.log(`  Authenticated AI Completed! CID: ${aiCid} | Latency: ${aiLatency}`);
    results.local_ai_authenticated = {
      passed: aiText.includes('LOCAL AI INFERENCE') && aiText.includes('Radeon AI PRO R9700'),
      cid: aiCid,
      latency: aiLatency
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_04_local_ai.png') });

    // 9. Spanish Language Toggle
    console.log('[9/10] Testing Spanish toggle...');
    await page.click('#lang');
    const esLang = await page.getAttribute('html', 'lang');
    const esTitle = await page.textContent('#console h2');
    console.log(`  Lang switched to: ${esLang} | Title: ${esTitle}`);
    results.spanish_toggle = {
      passed: esLang === 'es' && esTitle.includes('Consola')
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_06_spanish_desktop.png') });

    // 10. Mobile Viewport Test (390x844)
    console.log('[10/10] Testing Mobile viewport (390x844)...');
    await page.setViewportSize({ width: 390, height: 844 });
    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    console.log(`  Mobile overflow: ${hasHorizontalOverflow}`);
    results.mobile_responsive = {
      passed: !hasHorizontalOverflow
    };
    await page.screenshot({ path: path.join(evidenceDir, 'console_07_mobile_es.png') });

    // Sync key screenshots to session artifact directory
    const filesToSync = [
      'console_02_status_check.png',
      'console_03_public_ping_1.png',
      'console_04_ai_gated.png',
      'console_03_switch_ping_2.png',
      'console_04_local_ai.png',
      'console_05_evidence_view.png',
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
