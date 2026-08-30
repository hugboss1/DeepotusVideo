/* QA 3D Studio Meshy (v2.1) — captures de recette + checks fonctionnels.
   Rejoue le parcours complet sur le simulateur (MESHY_MOCK=1) :
   1. idle           — écran au repos, journal persisté, estimé affiché ;
   2. confirm        — modale de coût AVANT lancement (règle produit) ;
   3. run            — série en cours : nœud IN_PROGRESS, câble animé, ETA ;
   4. done           — 7 phases SUCCEEDED, consommé = estimé, solde décrémenté ;
   5. hub            — onglet « 🐙 3D Studio » du hub Game Assets (iframe).
   Sort en erreur si un état attendu n'est pas atteint. Viewport 1440×900
   (le $preview de la maquette DeepOtus Studio.dc.html).
   Run : node scripts/qa/qa-studio3d.js [outdir]   (DZ_BASE pour le serveur) */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = process.env.DZ_BASE || 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-studio3d');
const sleep = ms => new Promise(r => setTimeout(r, ms));

let failures = 0;
function check(label, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'} ${label}${detail ? ' — ' + detail : ''}`);
  if (!ok) failures++;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 180000,
    args: ['--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding'],
  });
  const page = await browser.newPage();
  const errors = [];
  const KNOWN = /(Failed to load resource|ERR_ABORTED)/i;
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1440, height: 900 });

  const $t = sel => page.$eval(sel, el => el.textContent.trim()).catch(() => null);

  /* — 1 · idle — */
  await page.goto(BASE + '/studio3d/', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(1800);
  /* 9 depuis « 07 · établi » : la porte vers /etabli. Elle ne porte PAS de
     .node-st — le contrôle 4 (« toutes les phases SUCCEEDED ») compte donc
     toujours 8 états, et il le doit : la porte n'est pas une phase. */
  check('idle: 9 nœuds + 9 câbles',
    await page.$$eval('.node', n => n.length) === 9
    && await page.$$eval('#cables path', n => n.length) === 9);
  const est = await $t('#mEstimate');
  check('idle: estimé affiché AVANT toute action', /\d+ cr/.test(est), est);
  check('idle: bouton de lancement porte le coût',
    ((await $t('#btnRun')) || '').includes(est), await $t('#btnRun'));
  check('idle: solde API affiché', /cr/.test(await $t('#mBalance') || ''), await $t('#mBalance'));
  await page.screenshot({ path: path.join(OUT, '1-idle.png') });

  /* — 2 · modale de confirmation (coût détaillé AVANT lancement) — */
  await page.click('#btnRun');
  await sleep(400);
  const lines = await page.$$eval('#confirmLines .prow', r => r.length);
  check('confirm: détail ligne à ligne', lines >= 5, `${lines} lignes`);
  check('confirm: total = estimé', (await $t('#confirmTotal')) === est,
    `${await $t('#confirmTotal')} vs ${est}`);
  await page.screenshot({ path: path.join(OUT, '2-confirm.png') });

  /* — 3 · série en cours — attendre l'état STABLE (le client pose
     IN_PROGRESS, le 1er poll mock peut répondre PENDING pendant ~2,5 s) */
  await page.click('#confirmGo');
  /* progression > 0 = IN_PROGRESS confirmé par un poll (pas l'instant
     transitoire client → PENDING file d'attente → IN_PROGRESS) */
  await page.waitForFunction(
    () => /IN_PROGRESS [1-9]\d* %/.test(document.querySelector('#nst-preview')?.textContent || ''),
    { timeout: 30000 });
  check('run: maillage IN_PROGRESS avec progression', true, await $t('#nst-preview'));
  check('run: câble actif animé (classe flow)',
    await page.$eval('#cable-k1', p => p.classList.contains('flow')));
  check('run: ETA restante', ((await $t('#mEta')) || '').startsWith('reste'), await $t('#mEta'));
  await page.screenshot({ path: path.join(OUT, '3-run.png') });

  /* — 4 · série terminée — */
  await page.waitForFunction(
    () => document.querySelector('#mEta')?.textContent === 'série terminée',
    { timeout: 120000 });
  await sleep(1000);
  const states = await page.$$eval('.node-st', els => els.map(e => e.textContent));
  check('done: toutes les phases SUCCEEDED',
    states.every(s => s.includes('SUCCEEDED')), states.join(' | '));
  const used = await $t('#mUsed');
  check('done: consommé = estimé (mock fidèle à la grille)', used === est, `${used} vs ${est}`);
  check('done: journal peuplé', await page.$$eval('#journal .jrow', r => r.length) === 4);
  check('done: aperçu model-viewer chargé', !!(await page.$('#previewBox model-viewer')));
  await page.screenshot({ path: path.join(OUT, '4-done.png') });

  /* — 5 · hub Game Assets → onglet 3D Studio — */
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2200);
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('aside nav button')]
      .find(x => (x.innerText || '').split('\n')[0] === 'Game Assets');
    b && b.click();
  });
  await sleep(1300);
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')]
      .find(x => (x.textContent || '').trim().endsWith('3D Studio'));
    b && b.click();
  });
  await sleep(2200);
  check('hub: iframe /studio3d/ montée',
    !!(await page.$('iframe[title="3D Studio"]')));
  await page.screenshot({ path: path.join(OUT, '5-hub.png') });

  await browser.close();
  if (errors.length) console.log('console errors:', errors.slice(0, 5));
  console.log(`\n=== RESULT === ${failures} échec(s), erreurs console: ${errors.length}`);
  process.exit(failures ? 1 : (errors.length ? 99 : 0));
})().catch(e => { console.error('FATAL', e); process.exit(1); });
