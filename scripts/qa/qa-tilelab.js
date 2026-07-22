/* Recette 9e — QA Puppeteer : Tile Lab + chroma.
   Q1 hub : sous-onglet « Tuiles » présent et cliquable -> iframe /tilelab.
   Q2 run offset réel (image Library) : after <= before et after <= 10.
   Q3 run mirror : after == 0.
   Q4 run pixel-art chaîné : résultat gen_*.png + score numérique.
   Q5 Sprite Lab : option détourage « chroma » présente.
   Q6 E2E chroma GRATUIT sur le render d'Olivier (92b74f61) : job done,
      sheet présent, >= 10/15 frames détourées — le job est CONSERVÉ
      (dernier sheet restauré par le fix préviz).
   Cleanup : les tuiles de test sont retirées de la Library ; le job chroma
   reste. Run : node qa-tilelab.js */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const BASE = 'http://127.0.0.1:8765';
const OUT = 'C:/Users/olivi/AppData/Local/Temp/claude/D--olivi-deepotus-rippled/7b0f8d77-d97b-4c48-a687-cfd776d43568/scratchpad/shots-9e';
const RENDER8 = '92b74f61';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function poll(fn, ok, ms, step) {
  const t0 = Date.now();
  for (;;) {
    const v = await fn();
    if (ok(v)) return v;
    if (Date.now() - t0 > ms) throw new Error('poll timeout: ' + JSON.stringify(v));
    await sleep(step || 1000);
  }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new',
  });
  const page = await browser.newPage();
  const errors = [], noise = [];
  const KNOWN = /(images\/sheet\.png|\/video\b.*40[34]|40[34].*\/video|ERR_ABORTED|Failed to load resource)/i;
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => {
    if (m.type() !== 'error') return;
    (KNOWN.test(m.text()) ? noise : errors).push('console: ' + m.text());
  });
  await page.setViewport({ width: 1600, height: 950 });
  const R = { pass: [], fail: [] };
  const T = (name, cond, extra) => {
    (cond ? R.pass : R.fail).push(name + (extra ? ' ' + extra : ''));
    console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? ' ' + extra : ''));
  };
  const madeTiles = [];

  // image source : la plus "texture" possible, sinon la première
  const imgs = (await (await fetch(BASE + '/api/images')).json()).images || [];
  if (!imgs.length) throw new Error('Library vide');
  const srcImg = (imgs.find(i => /deepsea|jeu|plateau|fond|texture/i.test(i.filename))
    || imgs[0]).filename;
  console.log('image source: ' + srcImg);

  /* ══ Q1 — hub : sous-onglet Tuiles ══ */
  await page.goto(BASE + '/', { waitUntil: 'networkidle0', timeout: 40000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle0' });
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate',
    { detail: { view: 'assets3d' } })));
  await sleep(1500);
  const tabBtn = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => /Tuiles/.test(x.textContent));
    if (!b) return false;
    b.click(); return true;
  });
  T('Q1 sous-onglet Tuiles cliqué', tabBtn);
  const fr = await poll(() => page.frames().find(f => f.url().includes('/tilelab/')), f => !!f, 15000);
  const tl = await poll(() => fr.evaluate(() => !!window.__tl).catch(() => false), v => v, 10000);
  T('Q1 iframe /tilelab + __tl', !!tl);

  /* ══ Q2 — run offset réel ══ */
  await fr.evaluate(fn => window.__tl.select(fn), srcImg);
  await fr.evaluate(() => document.querySelector('#runBtn').click());
  const r1 = await poll(() => fr.evaluate(() => window.__tl.state).catch(() => null),
    s => s && s.result && !s.busy, 60000, 1000);
  T('Q2 offset : résultat', !!r1.result.filename, `(${r1.result.filename})`);
  T('Q2 offset : after <= before', r1.result.after <= r1.result.before,
    `(${r1.result.before} -> ${r1.result.after})`);
  T('Q2 offset : after <= 10', r1.result.after <= 10, `(${r1.result.after})`);
  madeTiles.push(r1.result.filename);
  await sleep(600);
  await page.screenshot({ path: OUT + '/q2_tilelab_offset.png' });

  /* ══ Q3 — run mirror ══ */
  await fr.evaluate(() => {
    const m = document.querySelector('#method');
    m.value = 'mirror'; m.dispatchEvent(new Event('change'));
    document.querySelector('#runBtn').click();
  });
  const r2 = await poll(() => fr.evaluate(() => window.__tl.state).catch(() => null),
    s => s && s.result && !s.busy && s.result.filename !== r1.result.filename, 60000, 1000);
  T('Q3 mirror : after == 0', r2.result.after === 0, `(${r2.result.after})`);
  madeTiles.push(r2.result.filename);

  /* ══ Q4 — pixel-art chaîné ══ */
  await fr.evaluate(() => {
    const m = document.querySelector('#method');
    m.value = 'offset'; m.dispatchEvent(new Event('change'));
    document.querySelector('#pixelOn').checked = true;
    document.querySelector('#pixelOn').dispatchEvent(new Event('change'));
    document.querySelector('#runBtn').click();
  });
  const r3 = await poll(() => fr.evaluate(() => window.__tl.state).catch(() => null),
    s => s && s.result && !s.busy && s.result.filename !== r2.result.filename, 60000, 1000);
  T('Q4 pixel : résultat gen_*', /^gen_/.test(r3.result.filename), `(${r3.result.filename}, after ${r3.result.after})`);
  T('Q4 pixel : score numérique', typeof r3.result.after === 'number' && isFinite(r3.result.after));
  madeTiles.push(r3.result.filename);
  await sleep(600);
  await page.screenshot({ path: OUT + '/q4_tilelab_pixel.png' });

  /* ══ Q5 — Sprite Lab : option chroma ══ */
  await page.goto(BASE + '/spritelab/', { waitUntil: 'networkidle0' });
  const chromaOpt = await page.evaluate(() =>
    !!document.querySelector('#removeBg option[value="chroma"]'));
  T('Q5 option chroma dans le Sprite Lab', chromaOpt);

  /* ══ Q6 — E2E chroma gratuit sur le render d'Olivier ══ */
  const jobs = await (await fetch(BASE + '/api/jobs?limit=200')).json();
  const render = jobs.find(j => j.job_id.startsWith(RENDER8));
  T('Q6 render source présent', !!render, '(' + RENDER8 + ')');
  if (render) {
    const d = await (await fetch(BASE + '/api/assets/sprite', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: { kind: 'job', job_id: render.job_id },
        fps_sample: 8, max_frames: 15, remove_bg: 'chroma',
        trim: 'animation', cell: { size: 256, align: 'center' },
        columns: 'auto', title: 'Sprites · chroma 9e (recette)',
      }),
    })).json();
    T('Q6 job chroma lancé', !!d.job_id, '(' + (d.job_id || '').slice(0, 8) + ')');
    const j = await poll(async () =>
      (await fetch(BASE + '/api/jobs/' + d.job_id)).json(),
      x => x.status === 'done' || x.status === 'failed', 180000, 2000);
    T('Q6 job chroma done', j.status === 'done', '(' + (j.error || 'ok') + ')');
    const short = d.job_id.slice(0, 8);
    const man = await (await fetch(BASE + '/api/assets/sprite/' + short + '/manifest')).json();
    const det = (man.frames || []).filter(f => f.bg_removed).length;
    T('Q6 sheet présent', !!(man.files && man.files.sheet));
    T('Q6 frames détourées >= 10/15', det >= 10, `(${det}/${(man.frames || []).length})`);
    // vitrine : le sheet chroma téléchargé pour la preuve
    const buf = Buffer.from(await (await fetch(BASE + '/api/assets/sprite/' + short + '/sheet')).arrayBuffer());
    fs.writeFileSync(OUT + '/q6_sheet_chroma.png', buf);
    console.log('sheet chroma conservé : ' + short + ' (dernier sheet -> restauré par la préviz)');
  }

  /* ══ cleanup : tuiles de test hors Library (le job chroma reste) ══ */
  const cleanup = [];
  for (const fn of madeTiles.filter(Boolean)) {
    const ok = (await fetch(BASE + '/api/images/' + encodeURIComponent(fn), { method: 'DELETE' })).ok;
    cleanup.push(fn + (ok ? ' ✓' : ' ✗'));
  }

  console.log(JSON.stringify({ pass: R.pass, fail: R.fail, cleanup,
    errors, knownNoise: noise.slice(0, 6) }, null, 1));
  await browser.close();
  if (R.fail.length || errors.length) process.exit(1);
})().catch(e => { console.error('HARNESS FAIL', e.message); process.exit(1); });
