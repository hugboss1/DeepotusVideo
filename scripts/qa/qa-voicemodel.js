/* Recette W-b — modèles + précision ElevenLabs (plan 2026-07-22 §2).
   Mode SMOKE (DZ_BUNDLE=<bundle patché>) — AVANT déploiement, technique ch. 11 :
   le bundle worktree est servi par interception sur l'app installée ;
   /api/voice-models, /api/voices et /api/voice/providers sont mockés, et
   POST /api/audio/voiceover est intercepté (capture payload + réponse mock)
   → ZÉRO appel ElevenLabs, ZÉRO fichier Library, ZÉRO job.
   V1  boot : libellé v1.20.0 (bundle), zéro erreur de parse.
   V2  Quick Voice Over : select Modèle (data-dzvomsel), 4 options (Défaut+3)
       avec prix /1k ; défaut → maxlen 10000 ; Flash choisi → maxlen 40000,
       compteur /40000, 4 curseurs (data-dzvotune).
   V3  coût × multiplicateur : 100 chars → ~$0.0120 (flash 0.5×) puis
       ~$0.0240 (v3 1×, 1 seul curseur, maxlen 5000).
   V4  tune préchargé (localStorage dz_voice_tune) → Générer : payload
       {model:eleven_flash_v2_5, settings:{speed:1.1,style:0.2}} + résultat ok.
   V5  persistance : dz_voice_model=eleven_flash_v2_5.
   V6  picker : badge [professional] sur la voix non-premade, rien sur George.
   V7  ↺ Défauts : tunebox=defaults, payload suivant SANS settings.
   V8  Studio : graphe Text→Voiceover(model=eleven_v3, tune{stability:.3})→
       Render.audio ; panneau = select v3 + 1 curseur + reset ; Générer :
       payload model=eleven_v3 + settings{stability:.3} ; coût carte $0.0034.
   V9  zéro job créé (GET /api/jobs identique avant/après).
   V10 zéro erreur console inattendue.
   Mode E2E (DZ_E2E=1, sans DZ_BUNDLE) — APRÈS déploiement : /api/voice-models
   RÉEL (3 modèles, défaut eleven_multilingual_v2, flash à 0.5×) ; la
   génération réelle 2 modèles de la recette se fait via l'API (voir CR).
   Run : node scripts/qa/qa-voicemodel.js [outdir]  (deps: scripts/qa/node_modules) */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-voicemodel');
const E2E = process.env.DZ_E2E === '1';
const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
const SMOKE = !!LOCAL_BUNDLE;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const api = async (p) => { const r = await fetch(BASE + p); return r.json(); };

/* Miroir du registre backend (labels/prix = elevenlabs_service.ELEVEN_MODELS
   × pricing.py elevenlabs_model_mult sur base 0.00024). */
const MOCK_MODELS = {
  models: [
    { id: 'eleven_multilingual_v2', label: 'Multilingual v2 · qualité', max_chars: 10000,
      settings: ['stability', 'similarity_boost', 'style', 'speed'], mult: 1.0, usd_per_char: 0.00024, available: true },
    { id: 'eleven_v3', label: 'Eleven v3 · expressif', max_chars: 5000,
      settings: ['stability'], mult: 1.0, usd_per_char: 0.00024, available: true },
    { id: 'eleven_flash_v2_5', label: 'Flash v2.5 · rapide, −50 %', max_chars: 40000,
      settings: ['stability', 'similarity_boost', 'style', 'speed'], mult: 0.5, usd_per_char: 0.00012, available: true },
  ],
  default: 'eleven_multilingual_v2',
};
const MOCK_VOICES = {
  enabled: true, provider: 'elevenlabs',
  voices: [
    { voice_id: 'JBFqnCBsd6RMkjVDRZzb', name: 'George', category: 'premade', language: 'en',
      labels: { gender: 'male', accent: 'British', description: 'warm storyteller' }, preview_url: null },
    { voice_id: 'nPczCjzI2devNBz1zQrb', name: 'Brian', category: 'premade', language: 'en',
      labels: { gender: 'male', accent: 'American', description: 'deep resonant' }, preview_url: null },
    { voice_id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel', category: 'professional', language: 'en',
      labels: { gender: 'female', accent: 'American', description: 'calm narrator' }, preview_url: null },
  ],
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
  const KNOWN = /(images\/sheet\.png|qa-mock|qa_vo-|ERR_ABORTED|Failed to load resource)/i;
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1600, height: 950 });

  /* Interception : bundle worktree + mocks voix/modèles/voiceover (smoke). */
  const voBodies = [];
  await page.setRequestInterception(true);
  page.on('request', rq => {
    let pn = '';
    try { pn = new URL(rq.url()).pathname; } catch (_e) { return rq.continue(); }
    if (LOCAL_BUNDLE && pn.endsWith('/assets/index-BEOJX8L5.js')) {
      return rq.respond({ status: 200, contentType: 'application/javascript; charset=utf-8',
        body: fs.readFileSync(LOCAL_BUNDLE) });
    }
    if (SMOKE && pn === '/api/voice-models') {
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify(MOCK_MODELS) });
    }
    if (SMOKE && pn === '/api/voices') {
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify(MOCK_VOICES) });
    }
    if (SMOKE && pn === '/api/voice/providers') {
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ providers: [{ id: 'elevenlabs', label: 'ElevenLabs', ready: true }],
          configured: '', resolved: 'elevenlabs' }) });
    }
    if (SMOKE && pn === '/api/audio/voiceover' && rq.method() === 'POST') {
      let body = {};
      try { body = JSON.parse(rq.postData() || '{}'); } catch (_e) {}
      voBodies.push(body);
      return rq.respond({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ ok: true, filename: 'qa_vo-' + String(voBodies.length).padStart(6, '0') + '.mp3',
          url: '/api/audio/qa_vo-' + String(voBodies.length).padStart(6, '0') + '.mp3', size_kb: 12 }) });
    }
    if (SMOKE && /^\/api\/audio\/qa_vo-/.test(pn)) {
      return rq.respond({ status: 200, contentType: 'audio/mpeg', body: Buffer.from([0x49, 0x44, 0x33]) });
    }
    rq.continue();
  });

  const jobsBefore = ((await api('/api/jobs')).jobs || []).length;

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => {
    localStorage.setItem('dz_onboarded', '1');
    localStorage.removeItem('dz_voice_model');
    localStorage.setItem('dz_voice_tune', JSON.stringify({ speed: 1.1, style: 0.2 }));
  });
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2000);

  /* V1 — boot + libellé bundle */
  const v1 = await page.evaluate(() => document.body.innerText.includes('v1.20.0'));
  T('V1 boot : libellé v1.20.0 servi, zéro erreur de parse',
    v1 && errors.length === 0, JSON.stringify({ v: v1, errs: errors.slice(0, 2) }));

  const navTo = (label) => page.evaluate(l => {
    const b = [...document.querySelectorAll('aside nav button')].find(x => new RegExp(l, 'i').test(x.innerText + ' ' + x.title));
    if (b) b.click(); return !!b;
  }, label);
  const clickTab = (label) => page.evaluate(l => {
    const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === l);
    if (b) b.click(); return !!b;
  }, label);
  const setVal = (sel, val) => page.evaluate((s, v) => {
    const el = document.querySelector(s);
    if (!el) return false;
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  }, sel, val);
  /* Ouvre le select custom d'un wrapper et clique l'option par regex (un seul
     passage : le clic d'option referme le menu — pattern qa-videomodel W3). */
  const pickIn = async (wrapSel, rx) => {
    const res = await page.evaluate(async (ws, rxs) => {
      const rx2 = new RegExp(rxs, 'i');
      const wrap = document.querySelector(ws);
      if (!wrap) return 'no-wrap';
      const btn = wrap.querySelector('[data-dzselect]') || wrap.querySelector('button');
      if (!btn) return 'no-btn';
      btn.click();
      await new Promise(r => setTimeout(r, 450));
      const opt = [...document.querySelectorAll('button')].find(b => rx2.test(b.innerText.trim()));
      if (!opt) return 'no-option';
      opt.click();
      return 'ok';
    }, wrapSel, rx);
    await sleep(500);
    return res;
  };
  const quickState = () => page.evaluate(() => {
    const P = document.querySelector('[data-dzquickvoice]');
    const ta = P && P.querySelector('[data-dztext]');
    return P ? {
      maxlen: ta ? ta.getAttribute('maxlength') : null,
      chars: (P.querySelector('[data-dzchars]') || {}).innerText,
      cost: (P.querySelector('[data-dzcost]') || {}).innerText,
      selLabel: (P.querySelector('[data-dzvomsel]') || { innerText: '' }).innerText.trim().slice(0, 60),
      sliders: [...P.querySelectorAll('[data-dzvotune]')].map(d => d.getAttribute('data-dzvotune')),
      tunebox: (P.querySelector('[data-dzvotunebox]') || { getAttribute: () => null }).getAttribute('data-dzvotunebox'),
      reset: !!P.querySelector('[data-dzvotunereset]'),
    } : { missing: true };
  });

  /* V2 — Quick Voice Over : select Modèle + options + maxlen/curseurs */
  await navTo('quick');
  await sleep(900);
  await clickTab('Voice Over');
  await page.waitForSelector('[data-dzquickvoice]', { timeout: 15000 });
  await page.waitForSelector('[data-dzvomsel]', { timeout: 12000 }).catch(() => {});
  const v2a = await quickState();
  const v2opts = await page.evaluate(async () => {
    const wrap = document.querySelector('[data-dzvomsel]');
    if (!wrap) return { count: 0 };
    const btn = wrap.querySelector('[data-dzselect]') || wrap.querySelector('button');
    btn.click();
    await new Promise(r => setTimeout(r, 450));
    const all = [...document.querySelectorAll('button')].map(b => b.innerText.trim());
    const opts = all.filter(t => /^Défaut \(|\/1k/.test(t));
    const flash = [...document.querySelectorAll('button')].find(b => /^Flash v2\.5/.test(b.innerText.trim()));
    const out = { count: opts.length, hasPrix: opts.some(t => t.includes('$0.12/1k')), sample: opts.slice(0, 4) };
    if (flash) { flash.click(); out.pick = 'ok'; } else out.pick = 'no-option';
    return out;
  });
  await sleep(500);
  const v2b = await quickState();
  /* count === 5 : le bouton déclencheur (fermé) affiche aussi « Défaut (…) »
     et est compté avec les 4 options du menu (Défaut + 3 modèles). */
  T('V2 Quick : select Modèle, 4 options avec prix /1k, Flash → maxlen 40000 + 4 curseurs',
    !v2a.missing && v2a.maxlen === '10000' && /Défaut \(eleven_multilingual_v2\)/.test(v2a.selLabel)
    && v2opts.count === 5 && v2opts.hasPrix && v2opts.pick === 'ok'
    && v2b.maxlen === '40000' && /\/40000$/.test(v2b.chars)
    && v2b.sliders.join(',') === 'stability,similarity_boost,style,speed',
    JSON.stringify({ a: v2a, opts: v2opts, b: { maxlen: v2b.maxlen, chars: v2b.chars, sliders: v2b.sliders } }));
  await page.screenshot({ path: path.join(OUT, 'v2-quick-panel.png') });

  /* V3 — coût × multiplicateur + v3 = 1 curseur */
  const TEXT = 'x'.repeat(100);
  await setVal('[data-dztext]', TEXT);
  await sleep(300);
  const v3flash = await quickState();
  const pv3 = await pickIn('[data-dzvomsel]', '^Eleven v3');
  const v3v3 = await quickState();
  T('V3 coût : 100 chars → ~$0.0120 (flash 0.5×) puis ~$0.0240 (v3), 1 curseur, maxlen 5000',
    v3flash.cost === '~$0.0120' && pv3 === 'ok' && v3v3.cost === '~$0.0240'
    && v3v3.maxlen === '5000' && v3v3.sliders.join(',') === 'stability',
    JSON.stringify({ flash: v3flash.cost, v3: v3v3.cost, maxlen: v3v3.maxlen, sliders: v3v3.sliders }));

  /* V4 — Générer (Flash re-choisi) : payload model + settings préchargés.
     SMOKE seulement : en E2E ce clic déclencherait un VRAI appel ElevenLabs
     (la génération réelle de la recette se fait via l'API, voir CR). */
  const pback = await pickIn('[data-dzvomsel]', '^Flash v2\\.5');
  let v4 = {};
  if (SMOKE) {
    const before = voBodies.length;
    await page.evaluate(() => document.querySelector('[data-dzvogen]').click());
    await sleep(1500);
    const body = voBodies[before] || null;
    const resBox = await page.evaluate(() => {
      const b = document.querySelector('[data-dzvores]');
      return b ? { kind: b.getAttribute('data-dzvores'), text: b.innerText.slice(0, 80) } : null;
    });
    v4 = { got: voBodies.length - before, body, resBox };
    T('V4 Générer : payload model=eleven_flash_v2_5 + settings {speed:1.1, style:0.2}, résultat ok',
      pback === 'ok' && v4.got === 1 && body && body.model === 'eleven_flash_v2_5'
      && body.settings && body.settings.speed === 1.1 && body.settings.style === 0.2
      && body.name === 'quick_vo' && body.language === 'fr' && resBox && resBox.kind === 'ok',
      JSON.stringify({ pback, got: v4.got, model: body && body.model, settings: body && body.settings, resBox }));
  }

  /* V5 — persistance du modèle choisi */
  const v5 = await page.evaluate(() => ({
    model: localStorage.getItem('dz_voice_model'),
    tune: localStorage.getItem('dz_voice_tune'),
  }));
  T('V5 persistance : dz_voice_model=eleven_flash_v2_5, tune intact',
    v5.model === 'eleven_flash_v2_5' && /"speed":1\.1/.test(v5.tune || ''),
    JSON.stringify(v5));

  /* V6 — badge catégorie du picker (voix library/community rouvertes W-Q4).
     SMOKE seulement : les ids testés sont ceux du catalogue mocké. */
  const v6 = !SMOKE ? null : await page.evaluate(() => {
    const card = (id) => document.querySelector(`[data-dzvoice="${id}"]`);
    const rachel = card('21m00Tcm4TlvDq8ikWAM'), george = card('JBFqnCBsd6RMkjVDRZzb');
    return { rachel: rachel ? rachel.innerText : null, george: george ? george.innerText : null };
  });
  if (SMOKE) {
    T('V6 picker : badge [professional] sur Rachel, aucun badge sur George',
      !!v6.rachel && v6.rachel.includes('[professional]') && !!v6.george && !v6.george.includes('['),
      JSON.stringify({ rachel: (v6.rachel || '').slice(0, 60), george: (v6.george || '').slice(0, 50) }));
  }

  /* V7 — ↺ Défauts : tune vidé, payload suivant sans settings (SMOKE). */
  if (SMOKE) {
    await page.evaluate(() => document.querySelector('[data-dzvotunereset]').click());
    await sleep(400);
    const v7a = await quickState();
    const beforeV7 = voBodies.length;
    await page.evaluate(() => document.querySelector('[data-dzvogen]').click());
    await sleep(1200);
    const v7body = voBodies[beforeV7] || null;
    T('V7 ↺ Défauts : tunebox=defaults, payload sans settings, tune localStorage vidé',
      v7a.tunebox === 'defaults' && !v7a.reset && voBodies.length - beforeV7 === 1
      && v7body && !('settings' in v7body)
      && (await page.evaluate(() => localStorage.getItem('dz_voice_tune'))) === '{}',
      JSON.stringify({ tunebox: v7a.tunebox, hasSettings: v7body ? 'settings' in v7body : null }));
  }

  /* V8 — nœud Studio Voiceover : select + curseurs + payload des props */
  const GQA = 'qa-wb-node';
  const mkNode = (id, type, x, y, props) => ({ id, type, x, y, props: props || {} });
  const mkEdge = (id, from, fromPort, to, toPort) => ({ id, from, fromPort, to, toPort });
  const NODETEXT = 'qa wb voix off'; /* 14 chars → v3 : $0.0034 */
  await fetch(BASE + '/api/studio-graphs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: GQA, name: '[QA-WB] node', graph: { nodes: [
      mkNode('t1', 'Text', 60, 160, { value: NODETEXT }),
      mkNode('v1', 'Voiceover', 380, 160, { provider: 'elevenlabs', voice_id: '', voice_name: '', language: 'fr', filename: '', chars: 0, model: 'eleven_v3', tune: { stability: 0.3 } }),
      mkNode('r1', 'Render', 700, 160, { format: '9:16', fps: 30, crf: 20, name: 'qa_wb', voiceMode: 'passthrough' }),
    ], edges: [
      mkEdge('e1', 't1', 'out', 'v1', 'text'),
      mkEdge('e2', 'v1', 'out', 'r1', 'audio'),
    ] } }) });
  await navTo('studio');
  await sleep(900);
  await page.evaluate(() => window.dispatchEvent(new Event('dz-graphs-changed')));
  await sleep(700);
  const og = await page.evaluate(async (nm) => {
    const sel = [...document.querySelectorAll('[data-dzselect]')].find(b => /open graph|no saved graphs/i.test(b.innerText));
    if (!sel) return 'no-select';
    sel.click();
    await new Promise(r => setTimeout(r, 350));
    const opt = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === nm);
    if (!opt) return 'no-option';
    opt.click();
    return 'ok';
  }, '[QA-WB] node');
  await sleep(1200);
  const nc = await page.evaluate(() => {
    const cands = [...document.querySelectorAll('main div')].filter(d => {
      const t = (d.innerText || '').trim();
      return t.startsWith('Voiceover') && d.querySelectorAll('div').length < 30 && d.getBoundingClientRect().width > 100 && d.getBoundingClientRect().width < 340;
    });
    if (!cands.length) return false;
    const el = cands[cands.length - 1];
    const r0 = el.getBoundingClientRect();
    const opts = { bubbles: true, clientX: r0.x + r0.width / 2, clientY: r0.y + 14 };
    el.dispatchEvent(new MouseEvent('mousedown', opts));
    el.dispatchEvent(new MouseEvent('mouseup', opts));
    el.dispatchEvent(new MouseEvent('click', opts));
    return true;
  });
  await sleep(800);
  await page.waitForSelector('[data-dzvomsel]', { timeout: 12000 }).catch(() => {});
  const v8a = await page.evaluate(() => ({
    sel: (document.querySelector('[data-dzvomsel]') || { innerText: '' }).innerText.trim().slice(0, 50),
    sliders: [...document.querySelectorAll('[data-dzvotune]')].map(d => d.getAttribute('data-dzvotune')),
    tunebox: (document.querySelector('[data-dzvotunebox]') || { getAttribute: () => null }).getAttribute('data-dzvotunebox'),
    upstream: (document.querySelector('[data-dzvntext]') || { getAttribute: () => null }).getAttribute('data-dzvntext'),
  }));
  if (SMOKE) {
    /* Générer : SMOKE seulement (en E2E ce clic appellerait ElevenLabs). */
    const beforeV8 = voBodies.length;
    await page.evaluate(() => document.querySelector('[data-dzvngen]').click());
    await sleep(1500);
    const v8body = voBodies[beforeV8] || null;
    const v8after = await page.evaluate(() => ({
      file: (document.querySelector('[data-dzvnfile]') || { getAttribute: () => null }).getAttribute('data-dzvnfile'),
      cardCost: /\$0\.0034/.test(document.body.innerText),
    }));
    T('V8 nœud Studio : select v3 + 1 curseur + tune des props → payload + coût carte $0.0034',
      og === 'ok' && nc && /Eleven v3/.test(v8a.sel) && v8a.sliders.join(',') === 'stability'
      && v8a.tunebox === 'custom' && v8a.upstream === '1'
      && voBodies.length - beforeV8 === 1 && v8body && v8body.model === 'eleven_v3'
      && v8body.settings && v8body.settings.stability === 0.3 && v8body.script === NODETEXT
      && v8body.name === 'studio_vo' && !!v8after.file && v8after.cardCost,
      JSON.stringify({ og, nc, ...v8a, model: v8body && v8body.model, settings: v8body && v8body.settings, ...v8after }));
  } else {
    T('V8 nœud Studio (E2E) : panneau = select v3 + 1 curseur + tune des props',
      og === 'ok' && nc && /Eleven v3/.test(v8a.sel) && v8a.sliders.join(',') === 'stability'
      && v8a.tunebox === 'custom' && v8a.upstream === '1',
      JSON.stringify({ og, nc, ...v8a }));
  }
  await page.screenshot({ path: path.join(OUT, 'v8-node-panel.png') });

  /* V9 — zéro job réel */
  const jobsAfter = ((await api('/api/jobs')).jobs || []).length;
  T('V9 zéro job créé', jobsAfter === jobsBefore, JSON.stringify({ jobsBefore, jobsAfter }));

  /* E2E : catalogue réel post-déploiement */
  if (E2E) {
    const vm = await api('/api/voice-models');
    const ids = (vm.models || []).map(m => m.id);
    const flash = (vm.models || []).find(m => m.id === 'eleven_flash_v2_5') || {};
    T('E1 /api/voice-models réel : 3 modèles, défaut eleven_multilingual_v2',
      ids.length === 3 && vm.default === 'eleven_multilingual_v2', JSON.stringify(ids));
    T('E2 flash à 0.5× (usd_per_char 0.00012), disponible',
      Math.abs((flash.usd_per_char || 0) - 0.00012) < 1e-9 && flash.available === true,
      JSON.stringify(flash));
  }

  /* V10 — console propre */
  T('V10 zéro erreur console inattendue', errors.length === 0, JSON.stringify(errors.slice(0, 4)));

  await page.screenshot({ path: path.join(OUT, 'final.png') });
  await browser.close();
  console.log(`\n${R.pass.length}/${R.pass.length + R.fail.length} OK` + (R.fail.length ? `\nFAILS:\n- ${R.fail.join('\n- ')}` : ''));
  process.exit(R.fail.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
