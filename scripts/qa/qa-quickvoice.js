/* Recette V-a — Quick « Voice Over » (spec 2026-07-22-voiceover-quick-studio-design.md §5.4).
   Q1  onglet Voice Over présent (4 onglets Quick).
   Q2  panneau conforme §5.1 : garde ElevenLabs, textarea maxlength 2500,
       compteur 0/2500 + coût ~$0.0000, langue Français par défaut,
       « Voix par défaut de l'app » sélectionnée, voix listées, Générer désactivé.
   Q3  compteur/coût réactifs (chars × $0.00024, même constante que pricing.py),
       Générer activé quand texte non vide.
   Q4  préécoute : spy Audio.play/pause — ▶ joue le preview_url exact du
       catalogue, 2e voix stoppe la 1re, ZÉRO POST réseau pendant la préécoute.
   Q5  génération réelle fr → [data-dzvores=ok], <audio> jouable (play réel),
       mp3 servi (GET 200, >5 Ko), fichier listé par GET /api/audio,
       GET /api/jobs IDENTIQUE avant/après (aucun job créé).
   Q6  fichier visible dans Library → Audio.
   Q7  casting « QA-test » : sauvegarde (voix 2 + fr), settings JSON valide,
       reload app → toujours présent, applicable (resélectionne la voix).
   Q8  suppression du casting QA-test (cleanup) répercutée serveur.
   Q9a garde fournisseur simulée (mock fetch) resolved=voicebox : bandeau +
       Générer désactivé malgré un texte.
   Q9b resolved=null : panneau désactivé (pointer-events none, opacity .55).
   Q10 zéro erreur console inattendue sur tout le run.
   Run : NODE_PATH=<scratchpad>\node_modules node scripts/qa/qa-quickvoice.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-quickvoice');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const TEXT = 'La voix du studio Deepotus est prête pour la recette du chantier V-a. Tout roule.';

const api = async (p) => { const r = await fetch(BASE + p); return r.json(); };
const jobsSig = async () => {
  const j = await api('/api/jobs');
  const list = Array.isArray(j) ? j : (j.jobs || []);
  return { count: list.length, ids: list.map(x => x.id || x.job_id || '').sort().join(',') };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 180000,
    args: ['--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding',
      '--autoplay-policy=no-user-gesture-required'],
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
  let postCount = 0;
  page.on('request', rq => { if (rq.method() === 'POST' && rq.url().includes('/api/')) postCount++; });
  await page.setViewport({ width: 1600, height: 950 });
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2000);

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
  const openVoicePanel = async () => {
    await navTo('quick');
    await sleep(700);
    await clickTab('Voice Over');
    await page.waitForSelector('[data-dzquickvoice]', { timeout: 15000 });
    await page.waitForSelector('[data-dzprov]', { timeout: 20000 }).catch(() => {});
    await sleep(300);
  };

  /* Q1 — onglet présent */
  await navTo('quick');
  await sleep(700);
  const q1 = await page.evaluate(() => [...document.querySelectorAll('button')]
    .map(b => b.innerText.trim()).filter(t => /^(Seedance|HeyGen|Composition|Voice Over)$/.test(t)));
  T('Q1 onglet Voice Over présent (4 onglets)', q1.includes('Voice Over') && q1.length === 4, JSON.stringify(q1));

  /* Q2 — panneau conforme */
  await openVoicePanel();
  const q2 = await page.evaluate(() => {
    const P = document.querySelector('[data-dzquickvoice]');
    const ta = P.querySelector('[data-dztext]');
    const langBtn = P.querySelector('[data-dzselect]');
    return {
      prov: (P.querySelector('[data-dzprov]') || { getAttribute: () => null }).getAttribute('data-dzprov'),
      maxlen: ta ? ta.getAttribute('maxlength') : null,
      chars: (P.querySelector('[data-dzchars]') || {}).innerText,
      cost: (P.querySelector('[data-dzcost]') || {}).innerText,
      lang: langBtn ? langBtn.innerText.trim() : null,
      defSel: !!P.querySelector('[data-dzvoice="default"][data-dzsel="1"]'),
      nVoices: P.querySelectorAll('[data-dzplay]').length,
      genDisabled: (P.querySelector('[data-dzvogen]') || {}).disabled,
      castRow: !!P.querySelector('[data-dzcastrow]'),
    };
  });
  T('Q2 panneau conforme §5.1', q2.prov === 'elevenlabs' && q2.maxlen === '2500' && q2.chars === '0/2500'
    && q2.cost === '~$0.0000' && /Français/.test(q2.lang) && q2.defSel && q2.nVoices >= 10
    && q2.genDisabled === true && q2.castRow, JSON.stringify(q2));
  await page.screenshot({ path: path.join(OUT, 'q2-panel.png') });

  /* Q3 — compteur/coût réactifs */
  await setVal('[data-dztext]', TEXT);
  await sleep(300);
  const q3 = await page.evaluate(() => ({
    chars: document.querySelector('[data-dzchars]').innerText,
    cost: document.querySelector('[data-dzcost]').innerText,
    genDisabled: document.querySelector('[data-dzvogen]').disabled,
  }));
  const expCost = '~$' + (TEXT.length * 0.00024).toFixed(4);
  T('Q3 compteur + coût (constante pricing.py) + Générer activé',
    q3.chars === TEXT.length + '/2500' && q3.cost === expCost && q3.genDisabled === false,
    JSON.stringify({ ...q3, expCost }));

  /* Q4 — préécoute : spy Audio, exclusivité, zéro POST */
  await page.evaluate(() => {
    window.__plays = []; window.__pauses = [];
    const OP = Audio.prototype.play, OQ = Audio.prototype.pause;
    Audio.prototype.play = function () { window.__plays.push(this.src); return OP.apply(this, arguments); };
    Audio.prototype.pause = function () { window.__pauses.push(this.src); return OQ.apply(this, arguments); };
  });
  const voicesCat = await api('/api/voices');
  const catalog = {}; (voicesCat.voices || []).forEach(v => { catalog[v.voice_id] = v.preview_url; });
  const ids = await page.evaluate(() => [...document.querySelectorAll('[data-dzplay]')].slice(0, 2).map(b => b.getAttribute('data-dzplay')));
  postCount = 0;
  await page.evaluate(id => document.querySelector(`[data-dzplay="${id}"]`).click(), ids[0]);
  await sleep(500);
  await page.evaluate(id => document.querySelector(`[data-dzplay="${id}"]`).click(), ids[1]);
  await sleep(500);
  const q4 = await page.evaluate(ids2 => ({
    plays: window.__plays, pauses: window.__pauses,
    btn1: document.querySelector(`[data-dzplay="${ids2[0]}"]`).innerText.trim(),
    btn2: document.querySelector(`[data-dzplay="${ids2[1]}"]`).innerText.trim(),
  }), ids);
  const q4posts = postCount;
  T('Q4 préécoute : preview_url exacts, exclusivité, zéro POST',
    q4.plays.length === 2 && q4.plays[0] === catalog[ids[0]] && q4.plays[1] === catalog[ids[1]]
    && q4.pauses.includes(catalog[ids[0]]) && q4.btn1 === '▶' && q4.btn2 === '■' && q4posts === 0,
    JSON.stringify({ plays: q4.plays.length, pauses: q4.pauses.length, btn1: q4.btn1, btn2: q4.btn2, posts: q4posts }));
  await page.evaluate(id => document.querySelector(`[data-dzplay="${id}"]`).click(), ids[1]);
  await sleep(200);

  /* Q5 — génération réelle fr, zéro job créé.
     Voix premade du catalogue (2e carte) : la « Voix par défaut de l'app »
     du .env pointe une voix library → 402 payment_required sur le plan
     gratuit ElevenLabs (constat 22/07 — correctif .env hors périmètre V-a,
     le panneau affiche l'erreur inline dans ce cas, chemin d'erreur prouvé). */
  await page.evaluate(id => document.querySelector(`[data-dzvoice="${id}"]`).click(), ids[1]);
  await sleep(250);
  const jobsBefore = await jobsSig();
  await page.evaluate(() => document.querySelector('[data-dzvogen]').click());
  await page.waitForSelector('[data-dzvores]', { timeout: 90000 });
  const q5r = await page.evaluate(() => {
    const el = document.querySelector('[data-dzvores]');
    const audio = el.querySelector('audio');
    const mono = el.querySelector('.mono');
    return { kind: el.getAttribute('data-dzvores'), src: audio ? audio.getAttribute('src') : null,
      filename: mono ? mono.innerText.trim() : null, text: el.innerText.slice(0, 200) };
  });
  let playProof = { played: false }, served = { status: 0, bytes: 0 }, inAudioList = false;
  let jobsAfter = jobsBefore;
  if (q5r.kind === 'ok' && q5r.src) {
    playProof = await page.evaluate(async () => {
      const el = document.querySelector('[data-dzvores] audio');
      el.muted = true;
      await el.play();
      await new Promise(r => setTimeout(r, 400));
      const out = { played: !el.paused && el.currentTime > 0, t: el.currentTime };
      el.pause();
      return out;
    });
    const rsp = await fetch(BASE + q5r.src);
    const buf = await rsp.arrayBuffer();
    served = { status: rsp.status, bytes: buf.byteLength };
    const audioList = await api('/api/audio');
    inAudioList = JSON.stringify(audioList).includes(q5r.filename);
    jobsAfter = await jobsSig();
  }
  T('Q5 génération fr OK : audio jouable, mp3 servi, listé /api/audio, zéro job',
    q5r.kind === 'ok' && /^quick_vo-\d{6}\.mp3$/.test(q5r.filename || '') && playProof.played
    && served.status === 200 && served.bytes > 5000 && inAudioList
    && jobsAfter.count === jobsBefore.count && jobsAfter.ids === jobsBefore.ids,
    JSON.stringify({ kind: q5r.kind, filename: q5r.filename, played: playProof.played,
      served, inAudioList, jobs: jobsBefore.count + '->' + jobsAfter.count, err: q5r.kind === 'err' ? q5r.text : undefined }));
  T('Q5b mention Library → Audio affichée', q5r.kind === 'ok' && /Library → Audio/.test(q5r.text), JSON.stringify({ text: q5r.text.slice(0, 120) }));
  await page.screenshot({ path: path.join(OUT, 'q5-result.png') });

  /* Q6 — visible dans Library → Audio */
  await navTo('library');
  await sleep(1400);
  const audioTab = await page.evaluate(() => {
    // Onglets Library = "<Nom> <compte>" (ex. "Audio 12") — match \b, pas $.
    const b = [...document.querySelectorAll('main button')].find(x => /^audio\b/i.test(x.innerText.trim()));
    if (b) b.click(); return !!b;
  });
  await sleep(1600);
  const q6 = await page.evaluate(fn => ({
    found: document.body.innerText.toLowerCase().includes(fn.toLowerCase()),
  }), q5r.filename || 'quick_vo-');
  T('Q6 fichier visible dans Library → Audio', audioTab && q6.found, JSON.stringify({ audioTab, found: q6.found, filename: q5r.filename }));
  await page.screenshot({ path: path.join(OUT, 'q6-library.png') });

  /* Q7 — casting QA-test : save, settings JSON, reload, réapplication */
  await openVoicePanel();
  const id2 = ids[1];
  await page.evaluate(id => document.querySelector(`[data-dzvoice="${id}"]`).click(), id2);
  await sleep(250);
  await page.evaluate(() => document.querySelector('[data-dzcastsave]').click());
  await page.waitForSelector('[data-dzcastname]', { timeout: 5000 });
  await setVal('[data-dzcastname]', 'QA-test');
  await sleep(150);
  await page.evaluate(() => document.querySelector('[data-dzcastok]').click());
  let savedSel = false;
  for (let i = 0; i < 20; i++) {
    await sleep(400);
    savedSel = await page.evaluate(() => (document.querySelector('[data-dzcastrow] [data-dzselect]') || { innerText: '' }).innerText.includes('QA-test'));
    if (savedSel) break;
  }
  const st1 = await api('/api/atelier/settings');
  let castingsOk = false, castItem = null;
  try {
    const arr = JSON.parse((st1.settings || {}).voice_castings || '[]');
    castItem = arr.find(c => c && c.name === 'QA-test');
    castingsOk = Array.isArray(arr) && !!castItem && castItem.provider === 'elevenlabs'
      && castItem.voice_id === id2 && castItem.language === 'fr' && !!castItem.voice_name;
  } catch (_e) { castingsOk = false; }
  T('Q7a casting sauvé + settings voice_castings JSON valide', savedSel && castingsOk, JSON.stringify({ savedSel, castItem }));

  await page.reload({ waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2000);
  await openVoicePanel();
  await page.evaluate(() => document.querySelector('[data-dzcastrow] [data-dzselect]').click());
  await sleep(350);
  const applied = await page.evaluate(() => {
    const row = document.querySelector('[data-dzcastrow]');
    const opt = [...row.querySelectorAll('button')].find(b => b.innerText.trim() === 'QA-test');
    if (opt) opt.click(); return !!opt;
  });
  await sleep(500);
  const q7b = await page.evaluate(id => ({
    selShows: document.querySelector('[data-dzcastrow] [data-dzselect]').innerText.includes('QA-test'),
    voiceSel: !!document.querySelector(`[data-dzvoice="${id}"][data-dzsel="1"]`),
  }), id2);
  T('Q7b casting persistant après reload + applicable (resélectionne la voix)',
    applied && q7b.selShows && q7b.voiceSel, JSON.stringify({ applied, ...q7b }));
  await page.screenshot({ path: path.join(OUT, 'q7-casting.png') });

  /* Q8 — suppression (cleanup) répercutée serveur */
  await page.evaluate(() => document.querySelector('[data-dzcastdel]').click());
  let delOk = false;
  for (let i = 0; i < 20; i++) {
    await sleep(400);
    const st2 = await api('/api/atelier/settings');
    try { delOk = !JSON.parse((st2.settings || {}).voice_castings || '[]').some(c => c && c.name === 'QA-test'); } catch (_e) { delOk = false; }
    if (delOk) break;
  }
  const q8sel = await page.evaluate(() => document.querySelector('[data-dzcastrow] [data-dzselect]').innerText.trim());
  T('Q8 suppression QA-test répercutée serveur + select réinitialisé', delOk && /Casting…/.test(q8sel), JSON.stringify({ delOk, sel: q8sel }));

  /* Q9a — garde simulée resolved=voicebox */
  await page.evaluateOnNewDocument(() => {
    const of = window.fetch;
    window.fetch = function (u) {
      if (String(u).includes('/voice/providers')) {
        return Promise.resolve(new Response(JSON.stringify({ providers: [], configured: 'voicebox', resolved: 'voicebox' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      return of.apply(this, arguments);
    };
  });
  await page.reload({ waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(1800);
  await openVoicePanel();
  await setVal('[data-dztext]', 'test garde');
  await sleep(250);
  const q9a = await page.evaluate(() => ({
    prov: (document.querySelector('[data-dzprov]') || { getAttribute: () => null }).getAttribute('data-dzprov'),
    banner: /ElevenLabs seul/.test((document.querySelector('[data-dzprov="voicebox"]') || { innerText: '' }).innerText),
    genDisabled: (document.querySelector('[data-dzvogen]') || {}).disabled,
  }));
  T('Q9a resolved=voicebox : bandeau + Générer désactivé malgré texte',
    q9a.prov === 'voicebox' && q9a.banner && q9a.genDisabled === true, JSON.stringify(q9a));
  await page.screenshot({ path: path.join(OUT, 'q9a-voicebox.png') });

  /* Q9b — garde simulée resolved=null : panneau désactivé */
  await page.evaluateOnNewDocument(() => {
    const of = window.fetch;
    window.fetch = function (u) {
      if (String(u).includes('/voice/providers')) {
        return Promise.resolve(new Response(JSON.stringify({ providers: [], configured: '', resolved: null }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      return of.apply(this, arguments);
    };
  });
  await page.reload({ waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(1800);
  await openVoicePanel();
  const q9b = await page.evaluate(() => {
    const P = document.querySelector('[data-dzquickvoice]');
    const wrap = P.children[1];
    const cs = wrap ? getComputedStyle(wrap) : {};
    return {
      prov: (P.querySelector('[data-dzprov]') || { getAttribute: () => null }).getAttribute('data-dzprov'),
      msg: /Clé ElevenLabs manquante/.test(P.innerText),
      pe: cs.pointerEvents, op: Math.round(parseFloat(cs.opacity) * 100) / 100,
    };
  });
  T('Q9b resolved=null : message clé manquante + panneau désactivé',
    q9b.prov === 'none' && q9b.msg && q9b.pe === 'none' && q9b.op === 0.55, JSON.stringify(q9b));
  await page.screenshot({ path: path.join(OUT, 'q9b-nokey.png') });

  /* Q10 — console propre */
  T('Q10 zéro erreur console inattendue', errors.length === 0, errors.length ? JSON.stringify(errors.slice(0, 5)) : '');

  /* Cleanup best-effort : le mp3 de recette ne reste pas dans la Library
     (la preuve = result.json + screenshots + assertions API ci-dessus). */
  if (q5r.kind === 'ok' && q5r.filename) {
    await fetch(BASE + '/api/audio/' + encodeURIComponent(q5r.filename), { method: 'DELETE' }).catch(() => {});
  }

  await browser.close();
  console.log('\n=== RESULT ===');
  console.log('PASS ' + R.pass.length + ' / FAIL ' + R.fail.length);
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ pass: R.pass, fail: R.fail, errors }, null, 2));
  process.exit(R.fail.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
