/* Recette navrail — nav repliable en rail d'icônes, état persisté.
   V1 nav dépliée par défaut : 232px, labels + descriptions visibles.
   V2 clic « Collapse » : 64px, icônes seules (descriptions absentes),
      tooltips = labels, workspace élargi (~+168px).
   V3 reload -> reste repliée (localStorage dz_nav_collapsed = "1").
   V4 clic « Expand » : 232px, descriptions de retour.
   V5 reload -> reste dépliée ("0").
   Run : NODE_PATH=<scratchpad>/node_modules node scripts/qa/qa-navrail.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-navrail');
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
    localStorage.removeItem('dz_nav_collapsed');
  });
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2200);

  const geo = () => page.evaluate(() => {
    const aside = document.querySelector('aside');
    const main = document.querySelector('main');
    return {
      nav: Math.round(aside.getBoundingClientRect().width),
      main: main ? Math.round(main.getBoundingClientRect().width) : 0,
      desc: aside.innerText.includes('1-shot generators'),
      tooltips: [...aside.querySelectorAll('nav button')].slice(0, 3).map(b => b.title),
      store: localStorage.getItem('dz_nav_collapsed'),
    };
  });

  /* V1 — défaut déplié */
  let v1 = await geo();
  T('V1 nav dépliée par défaut (232px, descriptions visibles)',
    v1.nav === 232 && v1.desc && v1.tooltips.every(t => !t), JSON.stringify({ nav: v1.nav, desc: v1.desc }));

  /* V2 — collapse */
  await page.click('button[title="Collapse"]');
  await sleep(500);
  let v2 = await geo();
  T('V2 rail 64px, icônes seules, tooltips actifs',
    v2.nav === 64 && !v2.desc && v2.tooltips.join(',') === 'Quick,Studio,Chapitres' && v2.store === '1',
    JSON.stringify({ nav: v2.nav, tooltips: v2.tooltips, store: v2.store }));
  T('V2 workspace élargi (~+168px)', v2.main - v1.main >= 150, `(${v1.main} -> ${v2.main})`);
  await page.screenshot({ path: path.join(OUT, 'v2-rail.png') });

  /* V3 — reload : repliée persistée */
  await page.reload({ waitUntil: 'networkidle2' });
  await sleep(2000);
  let v3 = await geo();
  T('V3 repliée persistée après reload', v3.nav === 64 && v3.store === '1', JSON.stringify({ nav: v3.nav, store: v3.store }));

  /* V4 — expand */
  await page.click('button[title="Expand"]');
  await sleep(500);
  let v4 = await geo();
  T('V4 Expand -> 232px + descriptions', v4.nav === 232 && v4.desc && v4.store === '0', JSON.stringify({ nav: v4.nav, store: v4.store }));
  await page.screenshot({ path: path.join(OUT, 'v4-expanded.png') });

  /* V5 — reload : dépliée persistée */
  await page.reload({ waitUntil: 'networkidle2' });
  await sleep(2000);
  let v5 = await geo();
  T('V5 dépliée persistée après reload', v5.nav === 232 && v5.store === '0', JSON.stringify({ nav: v5.nav, store: v5.store }));

  await browser.close();
  console.log('\n=== RESULT ===');
  console.log('PASS ' + R.pass.length + ' / FAIL ' + R.fail.length);
  if (errors.length) console.log('console errors:', errors.slice(0, 6));
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ pass: R.pass, fail: R.fail, errors }, null, 2));
  process.exit(R.fail.length || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
