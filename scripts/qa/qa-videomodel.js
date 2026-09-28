/* Recette W-a — nœud vidéo multi-modèles (plan 2026-07-22 §1).
   Mode SMOKE (DZ_BUNDLE=<bundle patché>) — AVANT déploiement, technique ch. 11 :
   le bundle worktree est servi par interception sur l'app installée ;
   /api/video-models est mocké (registre) et POST /api/generate est intercepté
   (capture du payload + réponse mock) → ZÉRO job réel, ZÉRO coût fal/google.
   P1 #13 (28/09/2026) : plus AUCUNE valeur recopiée — la version (APP_VERSION), le modèle par défaut
   (DEFAULT_VIDEO_MODEL) et le nombre de modèles sont LUS dans le dépôt ; en SMOKE le catalogue simulé est le
   VRAI GET /api/video-models du backend visé (DZ_BASE, tout rendu disponible) ; le coût attendu en W4 est celui
   que le SERVEUR calcule (POST /api/cost/estimate, op `video`). Précondition : une image dans la Library.
   W1  boot : libellé v<APP_VERSION> (bundle), zéro erreur de parse.
   W2  graphe QA solo (Image→Seedance←Text, →Render) injecté + ouvert.
   W3  panneau Generator : select Modèle (data-dzvmsel) en tête, « Défaut (<défaut>) »
       + un par modèle du catalogue, prix $/s dans les labels ; sélection Kling v3 Pro.
   W4  cost est. (RUNTIME) == le montant du serveur pour kling-v3-pro à 10 s.
   W5  Run solo → POST /api/generate intercepté : video_model="kling-v3-pro", max_usd (garde),
       final s'aligne sur le nœud (image + prompt amont intacts).
   W6  Quick : select Modèle présent ; PixVerse v6 choisi ; image Library
       sélectionnée ; Generate → payload video_model="pixverse-v6" (mock).
   W7  persistance : localStorage.dz_video_model === "pixverse-v6".
   W8  zéro erreur console inattendue.
   Mode E2E (DZ_E2E=1, sans DZ_BUNDLE) — APRÈS déploiement : /api/video-models
   RÉEL (les modèles du registre, fal+google available avec les clés), select alimenté par
   le backend ; les générations réelles de la recette se font via l'API (voir
   CR chantier), pas ici.
   Run : node scripts/qa/qa-videomodel.js [outdir]  (deps: scripts/qa/node_modules) */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
// P1 #13 (28/09/2026) : DZ_BASE vise un backend de PREUVE (ex. http://127.0.0.1:8799) ; défaut inchangé
const BASE = process.env.DZ_BASE || 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-videomodel');
const E2E = process.env.DZ_E2E === '1';
const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
const SMOKE = !!LOCAL_BUNDLE;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const api = async (p) => { const r = await fetch(BASE + p); return r.json(); };

/* P1 #13 (28/09/2026) : lu dans le DÉPÔT, jamais recopié (la table REG d'hier ignorait seedance-2.5 et inventait
   des durées). Le banc test_p1_qa_videomodel vérifie que ces lectures rendent ce que Python importe. */
const REPO = path.join(__dirname, '..', '..');
const lire = f => fs.readFileSync(path.join(REPO, f), 'utf8').replace(/\r\n/g, '\n');
const APP_VERSION = (lire('backend/app/config.py').match(/^APP_VERSION = "([^"]+)"/m) || [])[1] || '?';
const FAL = lire('backend/app/services/fal_service.py');
const DEFAULT_VIDEO_MODEL = (FAL.match(/^DEFAULT_VIDEO_MODEL = "([^"]+)"/m) || [])[1] || '?';
const I_VM = FAL.indexOf('VIDEO_MODELS: dict = {');
const BLOC_VM = I_VM >= 0 ? FAL.slice(I_VM, FAL.indexOf('\n}\n', I_VM)) : '';
const IDS_REPO = [...BLOC_VM.matchAll(/^    "([^"]+)": \{/gm)].map(m => m[1]);
/* SMOKE : le VRAI catalogue du backend visé, tout rendu disponible (le backend de preuve n'a pas de clé) */
let MOCK_MODELS = null;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  if (SMOKE) {
    const reel = await api('/api/video-models');
    MOCK_MODELS = Object.assign({}, reel, { models: (reel.models || []).map(m => Object.assign({}, m, { available: true })) });
  }
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

  /* W1 — boot + libellé bundle (APP_VERSION du dépôt) */
  const w1 = await page.evaluate(v => document.body.innerText.includes('v' + v), APP_VERSION);
  T('W1 boot : libellé v' + APP_VERSION + ' servi, zéro erreur de parse',
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
      /* R8og1 (27/09) : le select « Open graph » est devenu un bouton icône qui déroule un menu */
      const sel = document.querySelector('[aria-label="Ouvrir un graphe"]');
      if (!sel) return 'no-select';
      sel.click();
      await new Promise(r => setTimeout(r, 350));
      const opt = [...document.querySelectorAll('.dz-opengraph-item')].find(b => b.innerText.trim() === nm);
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
      // P1 #13 : le bouton DÉCLENCHEUR (qui affiche le choix courant) n'est pas une option
      const all = [...document.querySelectorAll('button')].filter(b0 => b0 !== btn);
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
  const CAT = MOCK_MODELS || await api('/api/video-models');
  const nOpt = (CAT.models || []).length + 1;
  T('W3 panneau : select Modèle, ' + nOpt + ' options, prix, sélection Kling',
    nc && w3a.present && (w3a.label || '').includes('Défaut (' + CAT.default + ')') && w3opts.count === nOpt
    && w3opts.hasPrix && w3opts.kling && pk === 'ok',
    JSON.stringify({ nc, ...w3a, ...w3opts, pk }));
  await page.screenshot({ path: path.join(OUT, 'w3-select.png') });

  /* W4 — cost est. (RUNTIME) suit le modèle : le montant que le SERVEUR calcule (op `video`, bornage natif et
     video_max_gen_s compris — la vignette en est le miroir depuis P1 #9) */
  const est = await (await fetch(BASE + '/api/cost/estimate', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind: 'campaign', ops: [{ kind: 'video', model: 'kling-v3-pro', duration_s: 10 }] }) })).json();
  const w4att = '$' + Number(est.total_usd).toFixed(2);
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
  T('W4 cost est. par modèle : ' + w4att + ' (kling 10 s, montant du serveur)',
    w4.val === w4att, JSON.stringify({ ...w4, attendu: w4att }));
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
    w5 = { got: genBodies.length - before, model: body && body.video_model, max: body && body.max_usd,
      img: body && body.image_filename, prompt: body && (body.custom_prompt || '').slice(0, 30) };
    T('W5 Run solo : POST /generate intercepté, video_model=kling-v3-pro, max_usd (garde de P1 #9)',
      w5.got === 1 && w5.model === 'kling-v3-pro' && w5.img === IMGN && typeof w5.max === 'number' && w5.max > 0
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
    T('E1 /api/video-models réel : ' + IDS_REPO.length + ' modèles (fal_service.py), défaut ' + DEFAULT_VIDEO_MODEL,
      JSON.stringify(ids) === JSON.stringify(IDS_REPO) && vm.default === DEFAULT_VIDEO_MODEL, JSON.stringify(ids));
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
