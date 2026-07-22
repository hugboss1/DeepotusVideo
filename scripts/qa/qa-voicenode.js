/* Recette V-b — nœud Studio « Voiceover » (spec 2026-07-22 §6.3).
   V1  graphe Text→Voiceover : le panneau montre l'extrait AMONT (~80c),
       Générer activé (fournisseur elevenlabs).
   V2  Générer → data-dzvnres=ok, studio_vo-XXXXXX.mp3, listé /api/audio,
       <audio> jouable, ZÉRO job créé.
   V3  coût de carte dynamique : chars × $0.00024 sur la carte du nœud
       (plus de $0.04 en dur) après génération (props.chars).
   V4  casting global (créé via l'API comme en V-a) visible/applicable
       depuis le panneau du nœud : voix resélectionnée dans le picker.
   V5  Voiceover sans nœud texte relié : message « Relie un nœud
       Text/Prompt » + Générer désactivé.
   V6  préécoute du picker depuis le nœud : spy Audio.play, preview_url
       exact, zéro POST réseau.
   VE  (DZ_E2E=1, post-déploiement) ExistingRender→SpatialCompose→Render +
       MusicTrack + Voiceover → Run réel : +1 job template UNIQUEMENT (zéro
       sous-job seedance/heygen = zéro coût fal), final *_vo.mp4, ffprobe
       piste AAC, volumedetect prouve une piste non silencieuse.
   V7  garde fournisseur mockée resolved=voicebox : bandeau + Générer off.
   V8  zéro erreur console inattendue.
   Options : DZ_BUNDLE=<chemin> sert ce bundle (smoke AVANT déploiement) ;
   DZ_E2E=1 active VE (nécessite le backend V-b déployé).
   Run : NODE_PATH=<node_modules avec puppeteer-core> node scripts/qa/qa-voicenode.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-voicenode');
const E2E = process.env.DZ_E2E === '1';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const TEXT = 'Le nœud Studio parle enfin : chantier V-b, mixage au render vérifié.';

const api = async (p) => { const r = await fetch(BASE + p); return r.json(); };
const jobsList = async () => {
  const j = await api('/api/jobs');
  return Array.isArray(j) ? j : (j.jobs || []);
};
const jobsSig = async () => {
  const list = await jobsList();
  return { count: list.length, ids: list.map(x => x.id || x.job_id || '').sort().join(',') };
};
const FF = (exe, args) => {
  let r = spawnSync(exe, args, { encoding: 'utf8', timeout: 60000 });
  if (r.error) {
    const alt = path.join(process.env.LOCALAPPDATA || '', 'DeepotusVideoGen', 'bin', exe + '.exe');
    r = spawnSync(alt, args, { encoding: 'utf8', timeout: 60000 });
  }
  return r;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 300000,
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

  /* DZ_BUNDLE : sert le bundle patché AVANT déploiement (technique ch. 11). */
  const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
  if (LOCAL_BUNDLE) {
    await page.setRequestInterception(true);
    page.on('request', rq => {
      const pn = new URL(rq.url()).pathname;
      if (pn.endsWith('/assets/index-BEOJX8L5.js')) {
        return rq.respond({ status: 200, contentType: 'application/javascript; charset=utf-8',
          body: fs.readFileSync(LOCAL_BUNDLE) });
      }
      rq.continue();
    });
  }

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2000);

  const navTo = (label) => page.evaluate(l => {
    const b = [...document.querySelectorAll('aside nav button')].find(x => new RegExp(l, 'i').test(x.innerText + ' ' + x.title));
    if (b) b.click(); return !!b;
  }, label);

  /* ── préparation : graphes QA injectés par l'API (localhost only) ── */
  const G1 = 'qa-vb-wired', G1B = 'qa-vb-noline', G2 = 'qa-vb-render';
  const mkNode = (id, type, x, y, props) => ({ id, type, x, y, props: props || {} });
  const mkEdge = (id, from, fromPort, to, toPort) => ({ id, from, fromPort, to, toPort });
  const saveGraph = (id, name, nodes, edges) =>
    fetch(BASE + '/api/studio-graphs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, name, graph: { nodes, edges } }) }).then(r => r.json());

  await saveGraph(G1, '[QA-VB] wired', [
    mkNode('t1', 'Text', 70, 120, { value: TEXT }),
    mkNode('v1', 'Voiceover', 380, 120, { provider: 'elevenlabs', voice_id: '', voice_name: '', language: 'fr', filename: '', chars: 0 }),
    mkNode('r1', 'Render', 700, 120, { format: '9:16', fps: 30, crf: 20, name: 'qa_vb', voiceMode: 'passthrough' }),
  ], [
    mkEdge('e1', 't1', 'out', 'v1', 'text'),
    mkEdge('e2', 'v1', 'out', 'r1', 'audio'),
  ]);
  await saveGraph(G1B, '[QA-VB] no-line', [
    mkNode('v1', 'Voiceover', 380, 120, { provider: 'elevenlabs', voice_id: '', voice_name: '', language: 'fr', filename: '', chars: 0 }),
    mkNode('r1', 'Render', 700, 120, { format: '9:16', fps: 30, crf: 20, name: 'qa_vb2', voiceMode: 'passthrough' }),
  ], [
    mkEdge('e1', 'v1', 'out', 'r1', 'audio'),
  ]);

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

  /* V1 — extrait amont + Générer activé */
  const og1 = await openGraph('[QA-VB] wired');
  const nc1 = await clickNodeCard('Voiceover');
  await page.waitForSelector('[data-dzvntext]', { timeout: 12000 }).catch(() => {});
  // La garde fournisseur est asynchrone : attendre la résolution (bouton
  // activé) avant de figer l'assertion — sinon course au premier rendu.
  await page.waitForFunction(() => {
    const b = document.querySelector('[data-dzvngen]');
    return b && !b.disabled;
  }, { timeout: 15000 }).catch(() => {});
  const v1 = await page.evaluate((txt) => {
    const t = document.querySelector('[data-dzvntext]');
    return {
      state: t ? t.getAttribute('data-dzvntext') : null,
      showsExtract: t ? t.innerText.includes(txt.slice(0, 40)) : false,
      genDisabled: (document.querySelector('[data-dzvngen]') || {}).disabled,
      hasPicker: !!document.querySelector('[data-dzvoicelist]'),
      hasCastRow: !!document.querySelector('[data-dzvncastrow]'),
    };
  }, TEXT);
  T('V1 panneau nœud : extrait amont + Générer activé + picker + castings',
    og1 === 'ok' && nc1 && v1.state === '1' && v1.showsExtract && v1.genDisabled === false
    && v1.hasPicker && v1.hasCastRow, JSON.stringify({ og1, nc1, ...v1 }));
  await page.screenshot({ path: path.join(OUT, 'v1-panel.png') });

  /* V6 — préécoute depuis le nœud : spy Audio, zéro POST */
  await page.evaluate(() => {
    window.__plays = [];
    const OP = Audio.prototype.play;
    Audio.prototype.play = function () { window.__plays.push(this.src); return OP.apply(this, arguments); };
  });
  const cat = await api('/api/voices');
  const catMap = {}; (cat.voices || []).forEach(v => { catMap[v.voice_id] = v.preview_url; });
  const pid = await page.evaluate(() => {
    const b = document.querySelector('[data-dzplay]');
    return b ? b.getAttribute('data-dzplay') : null;
  });
  postCount = 0;
  await page.evaluate(id => document.querySelector(`[data-dzplay="${id}"]`).click(), pid);
  await sleep(600);
  const v6 = await page.evaluate(() => ({ plays: window.__plays }));
  T('V6 préécoute nœud : preview_url exact, zéro POST',
    v6.plays.length === 1 && v6.plays[0] === catMap[pid] && postCount === 0,
    JSON.stringify({ plays: v6.plays.length, posts: postCount }));
  await page.evaluate(id => document.querySelector(`[data-dzplay="${id}"]`).click(), pid).catch(() => {});

  /* V2 — génération réelle du texte AMONT, zéro job créé */
  const jobsBefore = await jobsSig();
  await page.evaluate(() => document.querySelector('[data-dzvngen]').click());
  await page.waitForSelector('[data-dzvnres]', { timeout: 90000 });
  const v2r = await page.evaluate(() => {
    const el = document.querySelector('[data-dzvnres]');
    const audio = el.querySelector('audio');
    const f = el.querySelector('[data-dzvnfile]');
    return { kind: el.getAttribute('data-dzvnres'), src: audio ? audio.getAttribute('src') : null,
      filename: f ? f.getAttribute('data-dzvnfile') : null, text: el.innerText.slice(0, 200) };
  });
  let played = { played: false }, inAudioList = false, jobsAfter = jobsBefore;
  if (v2r.kind === 'ok' && v2r.src) {
    played = await page.evaluate(async () => {
      const el = document.querySelector('[data-dzvnres] audio');
      el.muted = true;
      await el.play();
      await new Promise(r => setTimeout(r, 400));
      const out = { played: !el.paused && el.currentTime > 0 };
      el.pause();
      return out;
    });
    inAudioList = JSON.stringify(await api('/api/audio')).includes(v2r.filename);
    jobsAfter = await jobsSig();
  }
  T('V2 génération du texte amont : ok, mp3 listé, audio jouable, zéro job',
    v2r.kind === 'ok' && /^studio_vo-\d{6}\.mp3$/.test(v2r.filename || '') && played.played
    && inAudioList && jobsAfter.count === jobsBefore.count && jobsAfter.ids === jobsBefore.ids,
    JSON.stringify({ kind: v2r.kind, filename: v2r.filename, played: played.played, inAudioList,
      jobs: jobsBefore.count + '->' + jobsAfter.count, err: v2r.kind === 'err' ? v2r.text : undefined }));
  await page.screenshot({ path: path.join(OUT, 'v2-result.png') });

  /* V3 — coût de carte dynamique (chars × 0.00024) */
  const expCost = '$' + (TEXT.length * 0.00024).toFixed(4);
  // La rangée « cost est. » (Qh) vit dans la section RUNTIME de l'inspecteur,
  // repliée par défaut (rendu conditionnel) : la déplier d'abord.
  await page.evaluate(() => {
    const h = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === 'RUNTIME');
    if (h) h.click();
  });
  await sleep(400);
  const v3 = await page.evaluate((ec) => {
    const lab = [...document.querySelectorAll('span')].find(s0 => s0.innerText.trim() === 'cost est.');
    if (!lab) return { txt: 'rangée cost est. introuvable', hasDyn: false, hasHard: false };
    const sibs = [...lab.parentElement.children];
    const val = (sibs[sibs.indexOf(lab) + 1] || { innerText: '' }).innerText.trim();
    return { txt: 'cost est. = ' + val, hasDyn: val === ec, hasHard: val === '$0.04' };
  }, expCost);
  T('V3 coût carte dynamique ' + expCost + ' (plus de $0.04)',
    v3.hasDyn && !v3.hasHard, JSON.stringify(v3));
  await page.screenshot({ path: path.join(OUT, 'v3-card.png') });

  /* V4 — casting global applicable depuis le nœud (état settings restauré) */
  const st0 = await api('/api/atelier/settings');
  const originalCastings = (st0.settings || {}).voice_castings || '';
  const premade = (cat.voices || [])[1] || (cat.voices || [])[0];
  let arr0 = [];
  try { arr0 = JSON.parse(originalCastings || '[]'); } catch (_e) { arr0 = []; }
  const withQa = arr0.filter(c => c && c.name !== 'QA-vb').concat([{
    name: 'QA-vb', provider: 'elevenlabs', voice_id: premade.voice_id,
    voice_name: premade.name || premade.voice_id, language: 'en',
  }]);
  await fetch(BASE + '/api/atelier/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice_castings: JSON.stringify(withQa) }) });
  await page.reload({ waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(1800);
  await openGraph('[QA-VB] wired');
  await clickNodeCard('Voiceover');
  await page.waitForSelector('[data-dzvncastrow]', { timeout: 12000 });
  const applied = await page.evaluate(async () => {
    const row = document.querySelector('[data-dzvncastrow]');
    const sel = row.querySelector('[data-dzselect]');
    if (!sel) return 'no-select';
    sel.click();
    await new Promise(r => setTimeout(r, 350));
    const opt = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'QA-vb');
    if (!opt) return 'no-option';
    opt.click();
    return 'ok';
  });
  await sleep(700);
  const v4 = await page.evaluate((vid) => ({
    voiceSel: !!document.querySelector(`[data-dzvoice="${vid}"][data-dzsel="1"]`),
    selShows: (document.querySelector('[data-dzvncastrow] [data-dzselect]') || { innerText: '' }).innerText.includes('QA-vb'),
  }), premade.voice_id);
  T('V4 casting global applicable depuis le nœud (voix resélectionnée)',
    applied === 'ok' && v4.voiceSel && v4.selShows, JSON.stringify({ applied, ...v4 }));
  await page.screenshot({ path: path.join(OUT, 'v4-casting.png') });

  /* V5 — pas de nœud texte relié : garde + Générer désactivé */
  const og5 = await openGraph('[QA-VB] no-line');
  const nc5 = await clickNodeCard('Voiceover');
  await page.waitForSelector('[data-dzvntext]', { timeout: 12000 }).catch(() => {});
  const v5 = await page.evaluate(() => {
    const t = document.querySelector('[data-dzvntext]');
    return { state: t ? t.getAttribute('data-dzvntext') : null,
      msg: t ? /Relie un nœud Text\/Prompt/.test(t.innerText) : false,
      genDisabled: (document.querySelector('[data-dzvngen]') || {}).disabled };
  });
  T('V5 sans texte relié : message + Générer désactivé',
    og5 === 'ok' && nc5 && v5.state === '0' && v5.msg && v5.genDisabled === true, JSON.stringify(v5));
  await page.screenshot({ path: path.join(OUT, 'v5-guard.png') });

  /* VE — E2E render (post-déploiement uniquement) */
  let veJobId = null;
  if (E2E && v2r.kind === 'ok') {
    const jl = await jobsList();
    // Un vrai RENDER .mp4 (les jobs sprites/3D « done » pointent des PNG).
    const donej = jl.find(j => (j.status === 'done')
      && /\.mp4$/i.test(j.final_video_path || j.video_path || '')
      && !/sprite|asset3d/i.test(j.provider || ''));
    const audios = await api('/api/audio');
    const alist = (audios.audio || audios || []);
    // Musique : un fichier local RÉEL et lisible (ffprobe) — la Library peut
    // contenir des mp3 corrompus (ex. résidu qa_rachel_check du test 402).
    const AUDIO_DIR = path.join(process.env.LOCALAPPDATA || '', 'DeepotusVideoGenData', 'assets', 'audio');
    const music = (Array.isArray(alist) ? alist : []).map(a => a.name || a.filename || a)
      .filter(n => typeof n === 'string' && n !== v2r.filename)
      .find(n => {
        const fp = path.join(AUDIO_DIR, n);
        if (!fs.existsSync(fp) || fs.statSync(fp).size < 8000) return false;
        const pr = FF('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', fp]);
        return /audio/.test(pr.stdout || '');
      });
    const tplsRaw = await api('/api/layout-templates');
    const tpls = Array.isArray(tplsRaw) ? tplsRaw : (tplsRaw.templates || []);
    let pick = null, port = 'reel';
    for (const tm of tpls) {
      const tpl = tm.regions ? tm : await api('/api/layout-templates/' + encodeURIComponent(tm.template_id || tm.id));
      const vids = (tpl.regions || []).filter(r0 => r0.type === 'video_slot');
      if (tpl.render_mode !== 'sequential' && vids.length === 1) {
        pick = { id: tpl.template_id || tpl.id || tm.template_id || tm.id, slot: vids[0] };
        port = vids[0].default_provider === 'heygen' ? 'avatar' : 'reel';
        break;
      }
    }
    if (!donej || !pick) {
      T('VE préparation E2E (job done + template 1-slot disponibles)', false,
        JSON.stringify({ donej: !!donej, pick: !!pick, music: !!music }));
    } else {
      const nodes = [
        mkNode('er', 'ExistingRender', 60, 80, { jobId: donej.id || donej.job_id, durationS: 8 }),
        mkNode('sc', 'SpatialCompose', 380, 80, { templateId: pick.id }),
        mkNode('rd', 'Render', 700, 80, { format: '9:16', fps: 30, crf: 20, name: 'qa_vb_e2e', voiceMode: 'passthrough' }),
        mkNode('tx', 'Text', 60, 320, { value: TEXT }),
        mkNode('vo', 'Voiceover', 380, 320, { provider: 'elevenlabs', voice_id: '', voice_name: 'Voix par défaut de l\'app', language: 'fr', filename: v2r.filename, chars: TEXT.length }),
      ];
      const edges = [
        mkEdge('e1', 'er', 'out', 'sc', port),
        mkEdge('e2', 'sc', 'out', 'rd', 'in'),
        mkEdge('e3', 'tx', 'out', 'vo', 'text'),
      ];
      if (music) {
        nodes.push(mkNode('mt', 'MusicTrack', 380, 480, { volumeDb: -14, loop: true, filename: music }));
        edges.push(mkEdge('e4', 'vo', 'out', 'mt', 'src'));
        edges.push(mkEdge('e5', 'mt', 'out', 'rd', 'audio'));
      } else {
        edges.push(mkEdge('e4', 'vo', 'out', 'rd', 'audio'));
      }
      await saveGraph(G2, '[QA-VB] render', nodes, edges);
      const ogE = await openGraph('[QA-VB] render');
      const sigBefore = await jobsSig();
      const ranBtn = await page.evaluate(() => {
        const b = [...document.querySelectorAll('button')].find(x => /(^|\s)Run(\s|$)/.test(x.innerText.trim()) && x.getBoundingClientRect().y < 120);
        if (b) b.click(); return !!b;
      });
      await sleep(2500);
      await page.evaluate(() => {
        const b = [...document.querySelectorAll('button')].find(x => /^(Run|Confirm|Lancer|Queue)/i.test(x.innerText.trim()) && x.getBoundingClientRect().y > 120);
        if (b) b.click();
      }).catch(() => {});
      await page.screenshot({ path: path.join(OUT, 've-run.png') });
      let newJobs = [], waited = 0;
      while (waited < 30000) {
        await sleep(1500); waited += 1500;
        const now = await jobsList();
        newJobs = now.filter(j => !sigBefore.ids.includes(j.id || j.job_id));
        if (newJobs.length) break;
      }
      const parent = newJobs.find(j => (j.provider || '') === 'template') || newJobs[0];
      veJobId = parent && (parent.id || parent.job_id);
      let done = null;
      waited = 0;
      while (veJobId && waited < 300000) {
        await sleep(3000); waited += 3000;
        const now = await jobsList();
        const cur = now.find(j => (j.id || j.job_id) === veJobId);
        if (cur && cur.status === 'done') { done = cur; break; }
        if (cur && cur.status === 'failed') { done = cur; break; }
      }
      const allNow = await jobsList();
      const delta = allNow.filter(j => !sigBefore.ids.includes(j.id || j.job_id));
      const subProviders = delta.filter(j => (j.id || j.job_id) !== veJobId).map(j => j.provider);
      const finalPath = done && (done.final_video_path || '');
      let probe = { aac: false, mean: null };
      if (done && done.status === 'done' && finalPath && fs.existsSync(finalPath)) {
        const pr = FF('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,codec_name', '-of', 'json', finalPath]);
        try {
          const st = JSON.parse(pr.stdout || '{}').streams || [];
          probe.aac = st.some(s0 => s0.codec_type === 'audio' && s0.codec_name === 'aac');
        } catch (_e) {}
        const vd = FF('ffmpeg', ['-i', finalPath, '-af', 'volumedetect', '-f', 'null', '-']);
        const m = /mean_volume:\s*(-?[\d.]+) dB/.exec((vd.stderr || '') + (vd.stdout || ''));
        probe.mean = m ? parseFloat(m[1]) : null;
      }
      T('VE render E2E : job template done, zéro sous-job généré, final *_vo.mp4, AAC, non silencieux',
        ranBtn && done && done.status === 'done' && subProviders.every(p0 => !/seedance|heygen/i.test(p0 || ''))
        && /_vo\.mp4$/.test(finalPath) && probe.aac && probe.mean !== null && probe.mean > -50,
        JSON.stringify({ ranBtn, status: done && done.status, err: done && done.error, subProviders,
          finalPath: (finalPath || '').split(/[\\/]/).pop(), probe, music: music || 'aucune (VO directe)' }));
      await page.screenshot({ path: path.join(OUT, 've-done.png') });
    }
  } else if (E2E) {
    T('VE sauté : V2 a échoué en amont', false, '');
  } else {
    console.log('SKIP VE (DZ_E2E != 1 — smoke pré-déploiement)');
  }

  /* V9 — finition V-a : hint « about to call fal.ai » absent en mode voice,
     toujours présent en mode Seedance (colonne droite de Quick). */
  await navTo('quick');
  await sleep(800);
  const clickTab = (label) => page.evaluate(l => {
    const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === l);
    if (b) b.click(); return !!b;
  }, label);
  await clickTab('Voice Over');
  await sleep(600);
  const hintVoice = await page.evaluate(() => /about to call/.test(document.body.innerText));
  await clickTab('Seedance');
  await sleep(600);
  const hintSeedance = await page.evaluate(() => /about to call/.test(document.body.innerText));
  T('V9 hint fal.ai : absent en mode voice, présent en Seedance',
    !hintVoice && hintSeedance, JSON.stringify({ hintVoice, hintSeedance }));
  await page.screenshot({ path: path.join(OUT, 'v9-quick-voice.png') });

  /* V7 — garde fournisseur mockée (voicebox) */
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
  await page.reload({ waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(1800);
  await openGraph('[QA-VB] wired');
  await clickNodeCard('Voiceover');
  await page.waitForSelector('[data-dzvntext]', { timeout: 12000 }).catch(() => {});
  const v7 = await page.evaluate(() => ({
    banner: /ElevenLabs seul/.test((document.querySelector('[data-dzvnprov="voicebox"]') || { innerText: '' }).innerText),
    genDisabled: (document.querySelector('[data-dzvngen]') || {}).disabled,
  }));
  T('V7 resolved=voicebox : bandeau + Générer désactivé', v7.banner && v7.genDisabled === true, JSON.stringify(v7));

  /* V8 — console propre */
  T('V8 zéro erreur console inattendue', errors.length === 0, errors.length ? JSON.stringify(errors.slice(0, 5)) : '');

  /* ── cleanup best-effort : données réelles restaurées ── */
  await fetch(BASE + '/api/atelier/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice_castings: originalCastings }) }).catch(() => {});
  for (const g of [G1, G1B, G2]) {
    await fetch(BASE + '/api/studio-graphs/' + g, { method: 'DELETE' }).catch(() => {});
  }
  if (v2r.kind === 'ok' && v2r.filename) {
    await fetch(BASE + '/api/audio/' + encodeURIComponent(v2r.filename), { method: 'DELETE' }).catch(() => {});
  }
  if (veJobId) {
    await fetch(BASE + '/api/jobs/' + veJobId, { method: 'DELETE' }).catch(() => {});
  }

  await browser.close();
  console.log('\n=== RESULT ===');
  console.log('PASS ' + R.pass.length + ' / FAIL ' + R.fail.length);
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ pass: R.pass, fail: R.fail, errors, e2e: E2E }, null, 2));
  process.exit(R.fail.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
