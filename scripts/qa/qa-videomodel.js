/* Recette W-a — nœud vidéo multi-modèles (plan 2026-07-22 §1).
   Mode SMOKE (DZ_BUNDLE=<bundle patché>) — AVANT déploiement, technique ch. 11 :
   le bundle worktree est servi par interception sur l'app installée ;
   /api/video-models est mocké (registre) et POST /api/generate est intercepté
   (capture du payload + réponse mock) → ZÉRO job réel, ZÉRO coût fal/google.
   W1  boot : libellé v1.19.0 (bundle), zéro erreur de parse.
   W2  graphe QA solo (Image→Seedance←Text, →Render) injecté + ouvert.
   W3  panneau Generator : select Modèle (data-dzvmsel) en tête, 11 options
       (Défaut + 10), prix $/s dans les labels ; sélection Kling v3 Pro.
   W4  cost est. (RUNTIME) : $1.12 = 10 s × $0.112 (kling), plus de $0.18 dur.
   W5  Run solo → POST /api/generate intercepté : video_model="kling-v3-pro",
       final s'aligne sur le nœud (image + prompt amont intacts).
   W6  Quick : select Modèle présent ; PixVerse v6 choisi ; image Library
       sélectionnée ; Generate → payload video_model="pixverse-v6" (mock).
   W7  persistance : localStorage.dz_video_model === "pixverse-v6".
   W8  zéro erreur console inattendue.
   Mode E2E (DZ_E2E=1, sans DZ_BUNDLE) — APRÈS déploiement : /api/video-models
   RÉEL (10 modèles, fal+google available avec les clés), select alimenté par
   le backend ; les générations réelles de la recette se font via l'API (voir
   CR chantier), pas ici.
   Run : node scripts/qa/qa-videomodel.js [outdir]  (deps: scripts/qa/node_modules) */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-videomodel');
const E2E = process.env.DZ_E2E === '1';
const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
const SMOKE = !!LOCAL_BUNDLE;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const api = async (p) => { const r = await fetch(BASE + p); return r.json(); };

/* Miroir du registre backend (labels/prix = pricing.py video_usd_per_s). */
const REG = [
  ['seedance-v1-pro', 'Seedance 1.0 Pro', 'fal', { '720p': 0.054, '1080p': 0.124 }],
  ['seedance-2', 'Seedance 2.0', 'fal', { '720p': 0.3034, '1080p': 0.682 }],
  ['seedance-2-fast', 'Seedance 2.0 Fast', 'fal', { '720p': 0.2419 }],
  ['kling-v3-pro', 'Kling v3 Pro', 'fal', { '*': 0.112 }],
  ['kling-v3-standard', 'Kling v3 Standard', 'fal', { '*': 0.084 }],
  ['pixverse-v6', 'PixVerse v6', 'fal', { '720p': 0.045, '1080p': 0.09 }],
  ['veo-3.1-fast-fal', 'Veo 3.1 Fast (fal)', 'fal', { '*': 0.10 }],
  ['veo-3.1-google', 'Veo 3.1 (Google)', 'google', { '*': 0.40 }],
  ['veo-3.1-fast-google', 'Veo 3.1 Fast (Google)', 'google', { '*': 0.15 }],
  ['veo-3.1-lite-google', 'Veo 3.1 Lite (Google)', 'google', { '*': 0.10 }],
];
const MOCK_MODELS = {
  models: REG.map(([id, label, provider, usd]) => ({
    id, label, provider, available: true, durations: [4, 6, 8],
    ratios: ['9:16', '16:9'], resolutions: ['720p', '1080p'],
    end_image: id.startsWith('seedance') || id.startsWith('kling'),
    seed: false, audio_included: provider === 'google', usd_per_s: usd,
  })),
  default: 'seedance-v1-pro',
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
  const KNOWN = /(images\/sheet\.png|\/video\b.*40[34]|40[34].*\/video|ERR_ABORTED|Failed to load resource|qa-mock)/i;
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1600, height: 950 });

  /* Interception : bundle worktree + mocks registre/generate (mode smoke). */
  const genBodies = [];
  await page.setRequestInterception(true);
  page.on('request', rq => {
    let pn = '';
    try { pn = new URL(rq.url()).pathname; } catch (_e) { return rq.continue(); }
    if (LOCAL_BUNDLE && pn.endsWith('/assets/index-BEOJX8L5.js')) {
      return rq.respond({ status: 200, contentType: 'application/javascript; charset=utf-8',
        body: fs.readFileSync(LOCAL_BUNDLE) });
    }
    if (SMOKE && pn === '/api/video-models') {
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify(MOCK_MODELS) });
    }
    if (SMOKE && pn === '/api/generate' && rq.method() === 'POST') {
      let body = {};
      try { body = JSON.parse(rq.postData() || '{}'); } catch (_e) {}
      genBodies.push(body);
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ job_id: 'qa-mock-' + genBodies.length, status: 'queued', message: 'qa' }) });
    }
    if (SMOKE && /^\/api\/jobs\/qa-mock-/.test(pn)) {
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ job_id: pn.split('/').pop(), status: 'done', progress: 100 }) });
    }
    rq.continue();
  });

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.evaluate(() => localStorage.removeItem('dz_video_model'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2000);

  /* W1 — boot + libellé bundle */
  const w1 = await page.evaluate(() => document.body.innerText.includes('v1.19.0'));
  T('W1 boot : libellé v1.19.0 servi, zéro erreur de parse',
    w1 && errors.length === 0, JSON.stringify({ v: w1, errs: errors.slice(0, 2) }));

  const navTo = (label) => page.evaluate(l => {
    const b = [...document.querySelectorAll('aside nav button')].find(x => new RegExp(l, 'i').test(x.innerText + ' ' + x.title));
    if (b) b.click(); return !!b;
  }, label);
  const openGraph = async (name) => {
    await navTo('studio');
    await sleep(900);
    await page.evaluate(() => window.dispatchEvent(new Event('dz-graphs-changed')));
    await sleep(700);
    const opened = await page.evaluate(async (nm) => {
      const sel = [...document.querySelectorAll('[data-dzselect]')].find(b => /open graph|no saved graphs/i.test(b.innerText));
      if (!sel) return 'no-select';
      sel.click();
      await new Promise(r => setTimeout(r, 350));
      const opt = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === nm);
      if (!opt) return 'no-option';
      opt.click();
      return 'ok';
    }, name);
    await sleep(1200);
    return opened;
  };
  const clickNodeCard = async (title) => {
    const ok = await page.evaluate((tt) => {
      const cands = [...document.querySelectorAll('main div')].filter(d => {
        const t = (d.innerText || '').trim();
        return t.startsWith(tt) && d.querySelectorAll('div').length < 30 && d.getBoundingClientRect().width > 100 && d.getBoundingClientRect().width < 340;
      });
      if (!cands.length) return false;
      const el = cands[cands.length - 1];
      const r0 = el.getBoundingClientRect();
      const opts = { bubbles: true, clientX: r0.x + r0.width / 2, clientY: r0.y + 14 };
      el.dispatchEvent(new MouseEvent('mousedown', opts));
      el.dispatchEvent(new MouseEvent('mouseup', opts));
      el.dispatchEvent(new MouseEvent('click', opts));
      return true;
    }, title);
    await sleep(700);
    return ok;
  };
  /* Ouvre le select custom du wrapper donné et clique l'option par regex.
     Tolère un menu déjà ouvert/refermé (toggle) : 2 tentatives. */
  const pickModel = async (wrapSel, rx) => {
    for (let k = 0; k < 2; k++) {
      const res = await page.evaluate(async (ws, rxs) => {
        const rx2 = new RegExp(rxs, 'i');
        const findOpt = () => [...document.querySelectorAll('button')].find(b => rx2.test(b.innerText.trim()));
        let opt = findOpt();
        if (!opt) {
          const wrap = document.querySelector(ws);
          if (!wrap) return 'no-wrap';
          const btn = wrap.querySelector('[data-dzselect]') || wrap.querySelector('button');
          if (!btn) return 'no-btn';
          btn.click();
          await new Promise(r => setTimeout(r, 400));
          opt = findOpt();
        }
        if (!opt) return 'no-option';
        opt.click();
        return 'ok';
      }, wrapSel, rx);
      if (res === 'ok') { await sleep(500); return res; }
      await sleep(400);
      if (k === 1) return res;
    }
  };

  /* W2 — graphe QA solo injecté + ouvert */
  const imgs = await api('/api/images');
  const firstImg = (Array.isArray(imgs) ? imgs : imgs.images || [])[0];
  const IMGN = firstImg ? firstImg.filename : null;
  const GQA = 'qa-wa-solo';
  const mkNode = (id, type, x, y, props) => ({ id, type, x, y, props: props || {} });
  const mkEdge = (id, from, fromPort, to, toPort) => ({ id, from, fromPort, to, toPort });
  await fetch(BASE + '/api/studio-graphs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: GQA, name: '[QA-WA] solo', graph: { nodes: [
      mkNode('i1', 'Image', 60, 80, { filename: IMGN || 'missing.png' }),
      mkNode('t1', 'Text', 60, 260, { value: 'qa wa pumpfun prompt' }),
      mkNode('s1', 'Seedance', 380, 160, { model: '', style: 'cinematic', durationS: 10, aspect: '9:16', seed: 4421, extendMode: 'loop' }),
      mkNode('r1', 'Render', 700, 160, { format: '9:16', fps: 30, crf: 20, name: 'qa_wa', voiceMode: 'passthrough' }),
    ], edges: [
      mkEdge('e1', 'i1', 'out', 's1', 'image'),
      mkEdge('e2', 't1', 'out', 's1', 'prompt'),
      mkEdge('e3', 's1', 'out', 'r1', 'in'),
    ] } }) });
  const og = await openGraph('[QA-WA] solo');
  T('W2 graphe QA solo injecté + ouvert', og === 'ok' && !!IMGN, JSON.stringify({ og, img: IMGN }));

  /* W3 — select Modèle du panneau Generator */
  const nc = await clickNodeCard('Seedance');
  await page.waitForSelector('[data-dzvmsel]', { timeout: 12000 }).catch(() => {});
  const w3a = await page.evaluate(() => {
    const w = document.querySelector('[data-dzvmsel]');
    return { present: !!w, label: w ? w.innerText.trim().slice(0, 60) : null };
  });
  /* Un seul passage : ouvrir le menu, inventorier les options, cliquer Kling
     (pas de double toggle — le clic d'option referme le menu). */
  let w3opts = { count: 0, hasPrix: false, kling: false }, pk = 'skip';
  if (w3a.present) {
    const one = await page.evaluate(async () => {
      const wrap = document.querySelector('[data-dzvmsel]');
      const btn = wrap.querySelector('[data-dzselect]') || wrap.querySelector('button');
      btn.click();
      await new Promise(r => setTimeout(r, 450));
      const all = [...document.querySelectorAll('button')];
      const opts = all.map(b => b.innerText.trim()).filter(t => /Défaut \(|\$[\d.]+\/s/.test(t));
      const kl = all.find(b => /^Kling v3 Pro/.test(b.innerText.trim()));
      const out = { count: opts.length, hasPrix: opts.some(t => t.includes('$0.11/s')),
        kling: !!kl };
      if (kl) { kl.click(); out.pk = 'ok'; } else out.pk = 'no-option';
      return out;
    });
    w3opts = one; pk = one.pk;
    await sleep(600);
  }
  T('W3 panneau : select Modèle, 11 options, prix, sélection Kling',
    nc && w3a.present && /Défaut \(seedance-v1-pro\)/.test(w3a.label || '') && w3opts.count === 11
    && w3opts.hasPrix && w3opts.kling && pk === 'ok',
    JSON.stringify({ nc, ...w3a, ...w3opts, pk }));
  await page.screenshot({ path: path.join(OUT, 'w3-select.png') });

  /* W4 — cost est. (RUNTIME) suit le modèle : 10 s × $0.112 = $1.12 */
  await page.evaluate(() => {
    const h = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === 'RUNTIME');
    if (h) h.click();
  });
  await sleep(400);
  const w4 = await page.evaluate(() => {
    const lab = [...document.querySelectorAll('span')].find(s0 => s0.innerText.trim() === 'cost est.');
    if (!lab) return { val: 'introuvable' };
    const sibs = [...lab.parentElement.children];
    return { val: (sibs[sibs.indexOf(lab) + 1] || { innerText: '' }).innerText.trim() };
  });
  T('W4 cost est. par modèle : $1.12 (kling 10s), plus de $0.18 dur',
    w4.val === '$1.12', JSON.stringify(w4));
  await page.screenshot({ path: path.join(OUT, 'w4-cost.png') });

  /* W5 — Run solo : payload intercepté porte video_model=kling-v3-pro */
  let w5 = { skipped: true };
  if (SMOKE) {
    const before = genBodies.length;
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => /^run$/i.test((x.innerText || '').trim()));
      if (b) b.click();
    });
    await sleep(2500);
    const body = genBodies[before] || null;
    w5 = { got: genBodies.length - before, model: body && body.video_model,
      img: body && body.image_filename, prompt: body && (body.custom_prompt || '').slice(0, 30) };
    T('W5 Run solo : POST /generate intercepté, video_model=kling-v3-pro',
      w5.got === 1 && w5.model === 'kling-v3-pro' && w5.img === IMGN
      && /qa wa pumpfun/.test(w5.prompt || ''), JSON.stringify(w5));
  }

  /* W6 — Quick : select + payload */
  await navTo('quick');
  await sleep(1500);
  await page.waitForSelector('[data-dzvmsel]', { timeout: 12000 }).catch(() => {});
  const w6a = await page.evaluate(() => ({ present: !!document.querySelector('[data-dzvmsel]') }));
  const pkq = await pickModel('[data-dzvmsel]', '^PixVerse v6');
  /* Start image : sélection EXPLICITE via le dropdown (l'affichage par défaut
     ne garantit pas que le state w est rempli). */
  const w6img = await page.evaluate(async (fn) => {
    const lab = [...document.querySelectorAll('*')].find(el => el.children.length === 0 && /^Start image$/i.test((el.innerText || '').trim()));
    const zone = lab ? lab.parentElement : document;
    const btn = zone.querySelector('[data-dzselect]') || [...zone.querySelectorAll('button')][0];
    if (!btn) return 'no-btn';
    btn.click();
    await new Promise(r => setTimeout(r, 450));
    const opt = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === fn);
    if (!opt) return 'no-option';
    opt.click();
    return 'ok';
  }, IMGN);
  await sleep(600);
  let w6 = { skipped: true };
  if (SMOKE) {
    const before = genBodies.length;
    const clicked = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => /generate seedance/i.test((x.innerText || '').trim()));
      if (!b || b.disabled) return { clicked: false, found: !!b, disabled: b ? b.disabled : null };
      b.click();
      return { clicked: true };
    });
    await sleep(2500);
    const uiErr = await page.evaluate(() => {
      const m = document.body.innerText.match(/Pick a start image[^\n]*|Failed:[^\n]*/i);
      return m ? m[0] : null;
    });
    const body = genBodies[before] || null;
    w6 = { got: genBodies.length - before, model: body && body.video_model,
      img: w6img, ...clicked, uiErr };
    T('W6 Quick : select présent, payload video_model=pixverse-v6',
      w6a.present && pkq === 'ok' && w6.got === 1 && w6.model === 'pixverse-v6',
      JSON.stringify({ ...w6a, pkq, ...w6 }));
  } else {
    T('W6 Quick : select présent (E2E, payload non déclenché)', w6a.present && pkq === 'ok',
      JSON.stringify({ ...w6a, pkq }));
  }
  await page.screenshot({ path: path.join(OUT, 'w6-quick.png') });

  /* W7 — persistance du choix Quick */
  const w7 = await page.evaluate(() => localStorage.getItem('dz_video_model'));
  T('W7 persistance : dz_video_model=pixverse-v6', w7 === 'pixverse-v6', JSON.stringify({ w7 }));

  /* E2E : le registre réel répond avec les clés (post-déploiement) */
  if (E2E) {
    const vm = await api('/api/video-models');
    const ids = (vm.models || []).map(m => m.id);
    const av = Object.fromEntries((vm.models || []).map(m => [m.id, m.available]));
    T('E1 /api/video-models réel : 10 modèles, défaut seedance-v1-pro',
      ids.length === 10 && vm.default === 'seedance-v1-pro', JSON.stringify(ids));
    T('E2 clés : fal ET google available',
      av['seedance-2'] === true && av['veo-3.1-lite-google'] === true, JSON.stringify(av));
  }

  /* W8 — console propre */
  T('W8 zéro erreur console inattendue', errors.length === 0, JSON.stringify(errors.slice(0, 4)));

  await page.screenshot({ path: path.join(OUT, 'final.png') });
  await browser.close();
  console.log(`\n${R.pass.length}/${R.pass.length + R.fail.length} OK` + (R.fail.length ? `\nFAILS:\n- ${R.fail.join('\n- ')}` : ''));
  process.exit(R.fail.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
