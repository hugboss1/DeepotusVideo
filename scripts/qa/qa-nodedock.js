/* Recette nodedock — dock des nodes du Studio escamotable via « / ».
   N1  Studio : dock visible par défaut (260px), poignée cachée.
   N2  « / » replie : colonne 0px, dock opacity 0, poignée visible,
       canvas élargi (~+260px).
   N3  « / » re-déplie + focus auto du champ Search du dock.
   N4  « / » tapé DANS le Search : pas de toggle, caractère inséré.
   N5  Esc avec focus dans le dock -> replié.
   N6  clic poignée « NODES » -> rouvert.
   N7  clic croix du header -> replié.
   N8  persistance localStorage dz_studio_dock à travers reload (les 2 sens).
   N9  vue quick (hors Studio) : « / » inerte, pas d'erreur.
   N10 poignée QA window.__dzNodes {open, close, toggle, state}.
   N11 prefers-reduced-motion -> transition none sur la grille.
   Run : NODE_PATH=<scratchpad>/node_modules node scripts/qa/qa-nodedock.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-nodedock');
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 120000,
    args: ['--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding'],
  });
  const R = { pass: [], fail: [] };
  const T = (name, cond, extra) => {
    (cond ? R.pass : R.fail).push(name + (extra ? ' ' + extra : ''));
    console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? ' ' + extra : ''));
  };
  const errors = [];
  const KNOWN = /(images\/sheet\.png|\/video\b.*40[34]|40[34].*\/video|ERR_ABORTED|Failed to load resource)/i;
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1600, height: 950 });
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => {
    localStorage.setItem('dz_onboarded', '1');
    localStorage.removeItem('dz_studio_dock');
  });
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2200);
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'studio' } })));
  await sleep(1600);

  const geo = () => page.evaluate(() => {
    const g = document.querySelector('.dz-studio-grid');
    if (!g) return { grid: false };
    const cs = getComputedStyle(g);
    const cols = cs.gridTemplateColumns.split(' ').map(v => Math.round(parseFloat(v)));
    const canvas = g.children[1] ? Math.round(g.children[1].getBoundingClientRect().width) : 0;
    const handle = document.querySelector('.dz-dock-handle');
    const dockCS = g.children[0] ? getComputedStyle(g.children[0]) : null;
    return {
      grid: true, hidden: g.className.includes('dz-dock-hidden'), cols, canvas,
      dockOpacity: dockCS ? +dockCS.opacity : null,
      handleVisible: handle ? getComputedStyle(handle).display !== 'none' : false,
      transition: cs.transitionProperty,
      focusInDock: !!(document.activeElement && g.children[0] && g.children[0].contains(document.activeElement)),
      store: localStorage.getItem('dz_studio_dock'),
    };
  });

  /* N1 — état par défaut */
  let g1 = await geo();
  T('N1 dock visible par défaut (260px, poignée cachée)',
    g1.grid && !g1.hidden && g1.cols[0] === 260 && !g1.handleVisible, JSON.stringify(g1));
  await page.screenshot({ path: path.join(OUT, 'n1-default.png') });

  /* N10 — poignée QA */
  const n10 = await page.evaluate(() => window.__dzNodes && typeof window.__dzNodes.toggle === 'function' && window.__dzNodes.state);
  T('N10 window.__dzNodes {open,close,toggle,state}', !!n10 && n10.open === true, JSON.stringify(n10));

  /* N2 — « / » replie */
  const canvasBefore = g1.canvas;
  await page.keyboard.press('/');
  await sleep(450);
  let g2 = await geo();
  T('N2 « / » replie (colonne 0px, dock invisible, poignée visible)',
    g2.hidden && g2.cols[0] === 0 && g2.dockOpacity === 0 && g2.handleVisible && g2.store === '0',
    JSON.stringify(g2));
  T('N2 canvas élargi (~+260px)', g2.canvas - canvasBefore >= 240, `(${canvasBefore} -> ${g2.canvas})`);
  await page.screenshot({ path: path.join(OUT, 'n2-hidden.png') });

  /* N3 — « / » re-déplie + focus Search */
  await page.keyboard.press('/');
  await sleep(550);
  let g3 = await geo();
  T('N3 « / » re-déplie + focus du Search',
    !g3.hidden && g3.cols[0] === 260 && g3.focusInDock && g3.store === '1', JSON.stringify(g3));

  /* N4 — « / » dans le Search : pas de toggle, caractère inséré */
  await page.keyboard.type('img/');
  await sleep(250);
  const n4 = await page.evaluate(() => {
    const g = document.querySelector('.dz-studio-grid');
    const inp = g.children[0].querySelector('input');
    return { hidden: g.className.includes('dz-dock-hidden'), val: inp ? inp.value : null };
  });
  T('N4 « / » tapé dans le Search = caractère, pas de toggle',
    !n4.hidden && n4.val === 'img/', JSON.stringify(n4));

  /* N5 — Esc avec focus dans le dock -> replié */
  await page.keyboard.press('Escape');
  await sleep(450);
  let g5 = await geo();
  T('N5 Esc (focus dock) replie', g5.hidden && g5.cols[0] === 0, JSON.stringify({ hidden: g5.hidden, cols: g5.cols }));

  /* N6 — clic poignée -> rouvert */
  await page.click('.dz-dock-handle');
  await sleep(450);
  let g6 = await geo();
  T('N6 clic poignée NODES rouvre', !g6.hidden && g6.cols[0] === 260, '');
  await page.screenshot({ path: path.join(OUT, 'n6-reopened.png') });

  /* N7 — croix du header -> replié */
  await page.click('button[title^="Hide"]');
  await sleep(450);
  let g7 = await geo();
  T('N7 croix header replie', g7.hidden && g7.cols[0] === 0, '');

  /* N8 — persistance à travers reload (fermé puis ouvert) */
  await page.reload({ waitUntil: 'networkidle2' });
  await sleep(2000);
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'studio' } })));
  await sleep(1400);
  let g8a = await geo();
  T('N8 replié persisté après reload', g8a.grid && g8a.hidden && g8a.cols[0] === 0, JSON.stringify({ hidden: g8a.hidden, store: g8a.store }));
  await page.evaluate(() => window.__dzNodes.open());
  await sleep(450);
  await page.reload({ waitUntil: 'networkidle2' });
  await sleep(2000);
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'studio' } })));
  await sleep(1400);
  let g8b = await geo();
  T('N8 ouvert persisté après reload', g8b.grid && !g8b.hidden && g8b.cols[0] === 260, JSON.stringify({ hidden: g8b.hidden, store: g8b.store }));

  /* N9 — « / » inerte hors Studio */
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'quick' } })));
  await sleep(1200);
  await page.keyboard.press('/');
  await sleep(300);
  const n9 = await page.evaluate(() => ({
    grid: !!document.querySelector('.dz-studio-grid'),
    store: localStorage.getItem('dz_studio_dock'),
  }));
  T('N9 « / » inerte hors Studio', !n9.grid && n9.store === '1', JSON.stringify(n9));

  /* N11 — reduced-motion : pas de transition */
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'studio' } })));
  await sleep(1400);
  const n11 = await page.evaluate(() => {
    const g = document.querySelector('.dz-studio-grid');
    return g ? getComputedStyle(g).transitionProperty : null;
  });
  T('N11 reduced-motion = pas de transition', n11 === 'none', `(${n11})`);

  await browser.close();
  console.log('\n=== RESULT ===');
  console.log('PASS ' + R.pass.length + ' / FAIL ' + R.fail.length);
  if (errors.length) console.log('console errors:', errors.slice(0, 6));
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ pass: R.pass, fail: R.fail, errors }, null, 2));
  process.exit(R.fail.length || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
