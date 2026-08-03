/* Recette W-c — champ « Gemini — modèle » dans Settings (plan 2026-07-22 §3).
   Mode SMOKE (DZ_BUNDLE=<bundle patché>) — AVANT déploiement :
   bundle worktree servi par interception ; GET /api/settings/keys mocké et
   POST /api/settings/keys intercepté (capture + réponse mock) → ZÉRO écriture
   dans le vrai .env.
   G1 boot : libellé v1.21.0, zéro erreur de parse.
   G2 Settings → API keys : rangée « Gemini — modèle » présente, hint
      gemini-flash-latest visible, sous la rangée Google Gemini.
   G3 saisie « gemini-2.0-flash » + Save → POST intercepté
      {name:GEMINI_MODEL, value:gemini-2.0-flash} + message « saved — restart ».
   G4 zéro erreur console inattendue.
   Mode E2E (DZ_E2E=1, sans DZ_BUNDLE) — APRÈS déploiement : rangée présente,
   GET /settings/keys RÉEL liste GEMINI_MODEL ; AUCUNE écriture déclenchée.
   Run : node scripts/qa/qa-geminimodel.js [outdir]  (deps: scripts/qa/node_modules) */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-geminimodel');
const E2E = process.env.DZ_E2E === '1';
const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
const SMOKE = !!LOCAL_BUNDLE;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const api = async (p) => { const r = await fetch(BASE + p); return r.json(); };

const MOCK_KEY_LIST = {
  env_path: 'C:/mock/.env',
  keys: ['FAL_KEY', 'HEYGEN_API_KEY', 'ELEVENLABS_API_KEY', 'ANTHROPIC_API_KEY',
    'OPENAI_API_KEY', 'GEMINI_API_KEY', 'GEMINI_MODEL', 'MESHY_API_KEY']
    .map(k => ({ key: k, set: k === 'GEMINI_API_KEY', preview: k === 'GEMINI_API_KEY' ? 'AIza••••••abcd' : '' })),
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 300000,
    args: ['--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding'],
  });
  const R = { pass: [], fail: [] };
  const T = (name, cond, extra) => {
    (cond ? R.pass : R.fail).push(name + (extra ? ' ' + extra : ''));
    console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? ' ' + extra : ''));
  };
  const errors = [];
  const KNOWN = /(images\/sheet\.png|qa-mock|ERR_ABORTED|Failed to load resource)/i;
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1600, height: 950 });

  const keyWrites = [];
  await page.setRequestInterception(true);
  page.on('request', rq => {
    let pn = '';
    try { pn = new URL(rq.url()).pathname; } catch (_e) { return rq.continue(); }
    if (LOCAL_BUNDLE && pn.endsWith('/assets/index-BEOJX8L5.js')) {
      return rq.respond({ status: 200, contentType: 'application/javascript; charset=utf-8',
        body: fs.readFileSync(LOCAL_BUNDLE) });
    }
    if (SMOKE && pn === '/api/settings/keys' && rq.method() === 'GET') {
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify(MOCK_KEY_LIST) });
    }
    if (SMOKE && pn === '/api/settings/keys' && rq.method() === 'POST') {
      let body = {};
      try { body = JSON.parse(rq.postData() || '{}'); } catch (_e) {}
      keyWrites.push(body);
      const names = (body.entries || [body]).map(e => e && e.name).filter(Boolean);
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ ok: true, written: names, restart_required: true,
          message: 'Saved. Restart the backend for changes to apply.' }) });
    }
    if (E2E && pn === '/api/settings/keys' && rq.method() === 'POST') {
      // E2E : on n'écrit JAMAIS le vrai .env depuis le harnais.
      keyWrites.push({ blocked: true });
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ ok: true, written: [], restart_required: false, message: 'qa-mock' }) });
    }
    rq.continue();
  });

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2000);

  /* G1 — boot + libellé bundle */
  const g1 = await page.evaluate(() => document.body.innerText.includes('v1.21.0'));
  T('G1 boot : libellé v1.21.0 servi, zéro erreur de parse',
    g1 && errors.length === 0, JSON.stringify({ v: g1, errs: errors.slice(0, 2) }));

  /* G2 — Settings → API keys : rangée Gemini — modèle */
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('aside nav button')].find(x => /settings/i.test(x.innerText + ' ' + x.title));
    if (b) b.click();
  });
  await sleep(1000);
  /* Settings s'ouvre sur « Connected accounts » : cliquer l'onglet exact
     « API keys » du sous-menu SETTINGS, puis attendre la rangée Google Gemini. */
  await page.evaluate(() => {
    /* Les items du sous-menu SETTINGS sont des div sans role : cliquer la
       feuille texte exacte (l'évènement bouillonne jusqu'au handler React). */
    const t = [...document.querySelectorAll('*')]
      .find(x => x.children.length === 0 && (x.innerText || '').trim() === 'API keys');
    if (t) {
      const r0 = t.getBoundingClientRect();
      const opts = { bubbles: true, clientX: r0.x + r0.width / 2, clientY: r0.y + r0.height / 2 };
      t.dispatchEvent(new MouseEvent('mousedown', opts));
      t.dispatchEvent(new MouseEvent('mouseup', opts));
      t.dispatchEvent(new MouseEvent('click', opts));
    }
  });
  await page.waitForFunction(
    () => [...document.querySelectorAll('*')].some(el => el.children.length === 0
      && el.innerText && el.innerText.trim() === 'Google Gemini'),
    { timeout: 12000 }).catch(() => {});
  await sleep(400);
  const g2 = await page.evaluate(() => {
    const lab = [...document.querySelectorAll('*')].find(el => el.children.length === 0
      && el.innerText && el.innerText.trim() === 'Gemini — modèle');
    if (!lab) return { found: false };
    let row = lab.parentElement, depth = 0;
    while (row && depth < 7 && !(row.querySelector('input') && row.querySelector('button'))) {
      row = row.parentElement; depth++;
    }
    const googleRow = [...document.querySelectorAll('*')].find(el => el.children.length === 0
      && el.innerText && el.innerText.trim() === 'Google Gemini');
    const hint = row ? row.innerText : '';
    return { found: true, hasRow: !!row, hint: hint.slice(0, 200),
      hintOk: /gemini-flash-latest/.test(hint), googleAbove: !!googleRow,
      order: googleRow && lab ? (googleRow.getBoundingClientRect().top < lab.getBoundingClientRect().top) : null };
  });
  T('G2 Settings : rangée « Gemini — modèle » + hint alias, sous Google Gemini',
    g2.found && g2.hasRow && g2.hintOk && g2.googleAbove && g2.order === true,
    JSON.stringify({ ...g2, hint: (g2.hint || '').slice(0, 90) }));
  await page.screenshot({ path: path.join(OUT, 'g2-settings.png') });

  /* G3 — saisie + Save → POST capturé (SMOKE seulement) */
  if (SMOKE) {
    const typed = await page.evaluate(() => {
      const lab = [...document.querySelectorAll('*')].find(el => el.children.length === 0
        && el.innerText && el.innerText.trim() === 'Gemini — modèle');
      if (!lab) return 'no-label';
      let row = lab.parentElement, depth = 0;
      while (row && depth < 7 && !(row.querySelector('input') && row.querySelector('button'))) {
        row = row.parentElement; depth++;
      }
      if (!row) return 'no-row';
      const inp = row.querySelector('input');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, 'gemini-2.0-flash');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      const btn = [...row.querySelectorAll('button')].find(b => /save|sauver/i.test(b.innerText.trim()));
      if (!btn) return 'no-save';
      btn.click();
      return 'ok';
    });
    await sleep(1200);
    const wr = keyWrites[keyWrites.length - 1] || {};
    const entry = (wr.entries || [wr])[0] || {};
    const savedMsg = await page.evaluate(() => /GEMINI_MODEL saved/i.test(document.body.innerText));
    T('G3 Save → POST {name:GEMINI_MODEL, value:gemini-2.0-flash} + message restart',
      typed === 'ok' && keyWrites.length === 1 && entry.name === 'GEMINI_MODEL'
      && entry.value === 'gemini-2.0-flash' && savedMsg,
      JSON.stringify({ typed, writes: keyWrites.length, entry, savedMsg }));
    await page.screenshot({ path: path.join(OUT, 'g3-saved.png') });
  }

  /* E2E : la liste réelle contient GEMINI_MODEL ; aucune écriture émise */
  if (E2E) {
    const kl = await api('/api/settings/keys');
    const names = (kl.keys || []).map(k => k.key);
    T('E1 /api/settings/keys réel : GEMINI_MODEL dans l\'allowlist',
      names.includes('GEMINI_MODEL') && names.includes('GEMINI_API_KEY'),
      JSON.stringify({ n: names.length }));
    T('E2 aucune écriture .env déclenchée par le harnais', keyWrites.length === 0,
      JSON.stringify({ writes: keyWrites.length }));
  }

  /* G4 — console propre */
  T('G4 zéro erreur console inattendue', errors.length === 0, JSON.stringify(errors.slice(0, 4)));

  await page.screenshot({ path: path.join(OUT, 'final.png') });
  await browser.close();
  console.log(`\n${R.pass.length}/${R.pass.length + R.fail.length} OK` + (R.fail.length ? `\nFAILS:\n- ${R.fail.join('\n- ')}` : ''));
  process.exit(R.fail.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
