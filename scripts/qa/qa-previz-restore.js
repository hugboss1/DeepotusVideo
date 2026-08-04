/* T1 fix préviz — reproduction + non-régression du « panneau PRÉVIZ vide ».
   Cause suspectée : l'état du Sprite Lab (sheet affiché) est volatil ; toute
   navigation (subtab, vue, reload) remonte la page à blanc et rien ne
   ré-affiche un sheet terminé ni ne reprend une génération en cours.
   R1 standalone : génération réelle GRATUITE (remove_bg none) -> préviz anime (sanité).
   R2 reload après génération -> le sheet doit être restauré + animer.       [RED avant fix]
   R3 iframe hub fraîche -> dernier sheet restauré + anime.                  [RED avant fix]
   R4 reload PENDANT la génération -> reprise du poll puis préviz.           [RED avant fix]
   Ne touche PAS aux prefs d'Olivier (set .value sans event change).
   Cleanup : DELETE uniquement des jobs sprite2d créés par le run.
   Run : node qa-previz-restore.js */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const BASE = 'http://127.0.0.1:8765';
const OUT = 'C:/Users/olivi/AppData/Local/Temp/claude/D--olivi-deepotus-rippled/7b0f8d77-d97b-4c48-a687-cfd776d43568/scratchpad/shots-t1';
const PREFERRED_RENDER = '92b74f61';
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

  // snapshot pour un cleanup strict (on ne supprime que ce que CE run crée)
  const jobsBefore = await (await fetch(BASE + '/api/jobs?limit=200')).json();
  const beforeIds = new Set(jobsBefore.filter(j => j.provider === 'sprite2d').map(j => j.job_id));
  const render = jobsBefore.find(j => j.job_id.startsWith(PREFERRED_RENDER))
    || jobsBefore.find(j => j.status === 'done' && j.provider !== 'sprite2d'
        && j.provider !== 'asset3d'
        && /\.(mp4|mov|webm|m4v|avi|mkv|gif)$/i.test(j.final_video_path || ''));
  if (!render) throw new Error('aucun render vidéo done disponible');
  console.log('source: ' + render.job_id.slice(0, 8) + ' (' + (render.title || '') + ')');

  const animCheck = async (ctx) => {
    const p1 = await ctx.evaluate(() => ({ i: player.i, n: player.n,
      natural: player.imgs.filter(im => im.complete && im.naturalWidth > 0).length }));
    const h1 = await ctx.evaluate(() => document.querySelector('#cv').toDataURL().slice(-80));
    await sleep(700);
    const p2 = await ctx.evaluate(() => ({ i: player.i }));
    const h2 = await ctx.evaluate(() => document.querySelector('#cv').toDataURL().slice(-80));
    return { moved: p2.i !== p1.i, changed: h1 !== h2, frames: p1.natural + '/' + p1.n };
  };
  const state = ctx => ctx.evaluate(() => window.__sl && window.__sl.state).catch(() => null);

  /* ── R1 : standalone, génération réelle gratuite, préviz anime ── */
  await page.goto(BASE + '/spritelab/', { waitUntil: 'networkidle0', timeout: 30000 });
  await sleep(800);
  await page.evaluate(j => window.__sl.setSource(
    { kind: 'job', job_id: j.job_id, label: j.title || ('render ' + j.job_id.slice(0, 8)) }), render);
  const stx = await poll(() => state(page), s => s && s.extractShort && !s.busyExtract, 120000, 2000);
  T('R1 sonde extraite', stx.stripN > 0, `(frames: ${stx.stripN})`);
  // détourage 'none' SANS event change -> pref d'Olivier intacte
  await page.evaluate(() => { document.querySelector('#removeBg').value = 'none'; });
  await page.click('#genBtn');
  const stg = await poll(() => state(page), s => s && s.sheet && !s.busyGen, 180000, 2000);
  T('R1 sheet généré', !!stg.sheet, '(' + stg.sheet + ')');
  await sleep(1500);
  const a1 = await animCheck(page);
  T('R1 préviz anime (in-page)', a1.moved && a1.changed, JSON.stringify(a1));
  await page.screenshot({ path: OUT + '/r1_inpage_ok.png' });

  /* ── R2 : reload après génération -> restauration attendue ── */
  await page.reload({ waitUntil: 'networkidle0' });
  await sleep(3000);                       // laisse tourner un éventuel restore
  const st2 = await state(page);
  const empty2 = await page.evaluate(() =>
    !document.querySelector('#outEmpty').classList.contains('hidden'));
  await page.screenshot({ path: OUT + '/r2_apres_reload.png' });
  T('R2 sheet restauré après reload', !!(st2 && st2.sheet), '(sheet: ' + (st2 && st2.sheet) + ', placeholder visible: ' + empty2 + ')');
  if (st2 && st2.sheet) {
    const a2 = await animCheck(page);
    T('R2 préviz anime après reload', a2.moved && a2.changed, JSON.stringify(a2));
  } else {
    T('R2 préviz anime après reload', false, '(pas de sheet restauré)');
  }

  /* ── R3 : iframe hub fraîche -> dernier sheet restauré ── */
  await page.goto(BASE + '/', { waitUntil: 'networkidle0', timeout: 40000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle0' });
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate',
    { detail: { view: 'assets3d', subtab: 'sprites' } })));
  const fr = await poll(() => page.frames().find(f => f.url().includes('/spritelab/')), f => !!f, 15000);
  await sleep(3000);
  const st3 = await state(fr);
  await page.screenshot({ path: OUT + '/r3_iframe.png' });
  T('R3 sheet restauré dans l iframe', !!(st3 && st3.sheet), '(sheet: ' + (st3 && st3.sheet) + ')');
  if (st3 && st3.sheet) {
    const a3 = await animCheck(fr);
    T('R3 préviz anime dans l iframe', a3.moved && a3.changed, JSON.stringify(a3));
  } else {
    T('R3 préviz anime dans l iframe', false, '(pas de sheet restauré)');
  }

  /* ── R4 : reload PENDANT la génération -> reprise du poll ── */
  await page.goto(BASE + '/spritelab/', { waitUntil: 'networkidle0' });
  await sleep(800);
  await page.evaluate(j => window.__sl.setSource(
    { kind: 'job', job_id: j.job_id, label: j.title || ('render ' + j.job_id.slice(0, 8)) }), render);
  await poll(() => state(page), s => s && s.extractShort && !s.busyExtract, 120000, 2000);
  await page.evaluate(() => { document.querySelector('#removeBg').value = 'none'; });
  await page.click('#genBtn');
  await poll(() => state(page), s => s && s.busyGen, 10000, 300);   // POST parti
  await sleep(1200);
  await page.reload({ waitUntil: 'networkidle0' });                  // on abandonne la page en plein vol
  let st4 = null;
  try {
    st4 = await poll(() => state(page), s => s && s.sheet, 120000, 2000);
  } catch (e) { /* pas de reprise */ }
  await page.screenshot({ path: OUT + '/r4_reprise.png' });
  T('R4 reprise après reload en cours de génération', !!(st4 && st4.sheet), '(sheet: ' + (st4 && st4.sheet) + ')');

  /* ── cleanup : uniquement les jobs sprite2d créés par CE run ── */
  const jobsAfter = await (await fetch(BASE + '/api/jobs?limit=200')).json();
  const cleanup = [];
  for (const j of jobsAfter.filter(x => x.provider === 'sprite2d' && !beforeIds.has(x.job_id))) {
    const ok = (await fetch(BASE + '/api/jobs/' + j.job_id, { method: 'DELETE' })).ok;
    cleanup.push(j.job_id.slice(0, 8) + (ok ? ' ✓' : ' ✗'));
  }

  console.log(JSON.stringify({ pass: R.pass, fail: R.fail, cleanup,
    errors, knownNoise: noise.slice(0, 6) }, null, 1));
  await browser.close();
  if (R.fail.length || errors.length) process.exit(1);
})().catch(e => { console.error('HARNESS FAIL', e.message); process.exit(1); });
