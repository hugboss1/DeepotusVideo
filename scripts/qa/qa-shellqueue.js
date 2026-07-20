/* Recette 11a — queue panel (UI Shell Pro).
   Q1  dock absent du flux + workspace pleine hauteur (>= 888/950).
   Q2  icône « file » présente dans la topbar (title "Render queue — …").
   Q3  job réel GRATUIT (Sprite Lab, remove_bg none) -> badge >= 1 + pulse cyan.
   Q4  clic icône -> panneau .on (translateX(0)), header "Render queue",
       card Running du job réel visible.
   Q5  Esc -> panneau fermé (plus de .on, visibility hidden).
   Q6  clic scrim -> ferme aussi.
   Q7  0 job (interception /api/jobs -> []) -> état vide 🐙 "Nothing rendering."
   Q8  failed non lu -> badge ROUGE ; ouverture -> lu (badge plus rouge) ;
       reload -> toujours lu (localStorage dz_queue_seen_failed).
       Naturel si un failed existe dans les 40 derniers jobs, sinon interception.
   Q9  prefers-reduced-motion -> panneau en fade (transition opacity,
       transform none) + badge sans animation.
   Q10 poignée window.__dzQueue {open, close, toggle, state}.
   Cleanup : DELETE uniquement des jobs sprite2d créés par CE run.
   Run : NODE_PATH=<scratchpad>/node_modules node scripts/qa/qa-shellqueue.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-shellqueue');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function poll(fn, ok, ms, step) {
  const t0 = Date.now();
  for (;;) {
    const v = await fn();
    if (ok(v)) return v;
    if (Date.now() - t0 > ms) throw new Error('poll timeout: ' + JSON.stringify(v).slice(0, 300));
    await sleep(step || 1000);
  }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new',
    protocolTimeout: 240000,
    // le hub repasse en avant-plan pendant le job réel : sans ces flags, Chrome
    // throttle l'onglet backgroundé et le protocole CDP gèle (cf. run 1).
    args: ['--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding'],
  });
  const R = { pass: [], fail: [] };
  const T = (name, cond, extra) => {
    (cond ? R.pass : R.fail).push(name + (extra ? ' ' + extra : ''));
    console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? ' ' + extra : ''));
  };
  const errors = [], noise = [];
  const KNOWN = /(images\/sheet\.png|\/video\b.*40[34]|40[34].*\/video|ERR_ABORTED|Failed to load resource)/i;
  const wire = pg => {
    pg.on('pageerror', e => errors.push('pageerror: ' + e.message));
    pg.on('console', m => {
      if (m.type() !== 'error') return;
      (KNOWN.test(m.text()) ? noise : errors).push('console: ' + m.text());
    });
  };

  const jobsBefore = await (await fetch(BASE + '/api/jobs?limit=200')).json();
  const beforeIds = new Set(jobsBefore.filter(j => j.provider === 'sprite2d').map(j => j.job_id));

  /* ───────────── page hub principale ───────────── */
  const page = await browser.newPage();
  wire(page);
  await page.setViewport({ width: 1600, height: 950 });
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2800);

  /* Q1 — plus de dock dans le flux, workspace pleine hauteur */
  const q1 = await page.evaluate(() => {
    const inFlow = [...document.querySelectorAll('span')].filter(s =>
      /^(Job dock|Render queue)$/.test(s.textContent.trim()) && !s.closest('.dzq-panel'));
    const header = document.querySelector('header');
    const hh = header ? header.getBoundingClientRect().height : 0;
    const panel = document.querySelector('.dzq-panel');
    const cs = panel ? getComputedStyle(panel) : null;
    return {
      dockLabelsInFlow: inFlow.length,
      workspaceH: window.innerHeight - hh,
      panelExists: !!panel,
      panelVisibility: cs ? cs.visibility : null,
      panelWidth: cs ? cs.width : null,
    };
  });
  T('Q1 dock absent du flux', q1.dockLabelsInFlow === 0, `(labels=${q1.dockLabelsInFlow})`);
  T('Q1 workspace pleine hauteur', q1.workspaceH >= 888, `(${q1.workspaceH}px vs 830 avant)`);
  T('Q1 panneau monté fermé (visibility hidden)', q1.panelExists && q1.panelVisibility === 'hidden',
    `(vis=${q1.panelVisibility}, w=${q1.panelWidth})`);
  await page.screenshot({ path: OUT + '/after-studio.png' });

  /* Q2 — icône topbar */
  const q2 = await page.evaluate(() => {
    const btn = document.querySelector('button[title^="Render queue"]');
    if (!btn) return { found: false };
    const b = btn.getBoundingClientRect();
    const octo = document.querySelector('button[title="Replay onboarding"]');
    return { found: true, title: btn.title, x: b.x, y: b.y,
      beforeOcto: octo ? b.x < octo.getBoundingClientRect().x : null };
  });
  T('Q2 icône file en topbar', q2.found && q2.y < 56, JSON.stringify(q2));

  /* vue Quick sans dock */
  await page.evaluate(() => {
    const el = [...document.querySelectorAll('button, a, [role="button"], div')]
      .filter(e => e.childElementCount <= 3 && e.textContent.trim() === 'Quick')[0];
    if (el) el.click();
  });
  await sleep(1200);
  await page.screenshot({ path: OUT + '/after-quick.png' });

  /* Q10 — poignée QA */
  const q10a = await page.evaluate(() => window.__dzQueue && window.__dzQueue.state);
  await page.evaluate(() => window.__dzQueue.open());
  await sleep(450);
  const q10b = await page.evaluate(() => window.__dzQueue.state.open);
  await page.evaluate(() => window.__dzQueue.close());
  await sleep(450);
  const q10c = await page.evaluate(() => window.__dzQueue.state.open);
  T('Q10 __dzQueue open/close/state', !!q10a && q10b === true && q10c === false,
    JSON.stringify({ init: q10a, afterOpen: q10b, afterClose: q10c }));

  /* Q7 — état vide (interception -> []) */
  {
    const p7 = await browser.newPage();
    wire(p7);
    await p7.setViewport({ width: 1600, height: 950 });
    await p7.setRequestInterception(true);
    p7.on('request', rq => {
      if (rq.url().includes('/api/jobs')) {
        rq.respond({ status: 200, contentType: 'application/json', body: '[]' });
      } else rq.continue();
    });
    await p7.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p7.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
    await p7.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
    await sleep(2000);
    await p7.evaluate(() => window.__dzQueue.open());
    await sleep(600);
    const empty = await p7.evaluate(() => {
      const panel = document.querySelector('.dzq-panel');
      const txt = panel ? panel.innerText : '';
      // entêtes de section = .upper DANS la liste .scroll (le header du panneau
      // contient légitimement le badge « 0 running »)
      return { octo: txt.includes('🐙'), msg: /Nothing rendering/.test(txt),
        run: !!panel.querySelector('.scroll .upper'),
        badge: !!document.querySelector('.dzq-pulse') };
    });
    T('Q7 état vide 🐙 sans sections', empty.octo && empty.msg && !empty.run && !empty.badge,
      JSON.stringify(empty));
    await p7.screenshot({ path: OUT + '/after-empty.png' });
    await p7.close();
  }

  /* Q8 — failed non lu -> badge rouge -> lu après ouverture, persistant */
  {
    const failedNat = jobsBefore.slice(0, 40).some(j => j.status === 'failed');
    const p8 = await browser.newPage();
    wire(p8);
    await p8.setViewport({ width: 1600, height: 950 });
    if (!failedNat) {
      await p8.setRequestInterception(true);
      const FAKE = JSON.stringify([{ job_id: 'qa_fail_11a', status: 'failed', progress: 12,
        title: 'qa_failed_render', provider: 'seedance', error: 'QA simulated failure',
        image_filename: '', aspect_ratio: '9:16' }]);
      p8.on('request', rq => {
        if (rq.url().includes('/api/jobs')) {
          rq.respond({ status: 200, contentType: 'application/json', body: FAKE });
        } else rq.continue();
      });
    }
    await p8.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p8.evaluate(() => {
      localStorage.setItem('dz_onboarded', '1');
      localStorage.removeItem('dz_queue_seen_failed');
    });
    await p8.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
    await sleep(3200);
    const red1 = await p8.evaluate(() => {
      const btn = document.querySelector('button[title^="Render queue"]');
      const badge = btn && btn.parentElement.querySelector('span');
      return badge ? { bg: getComputedStyle(badge).backgroundColor, txt: badge.textContent } : null;
    });
    await p8.screenshot({ path: OUT + '/after-failed-badge.png' });
    await p8.evaluate(() => window.__dzQueue.open());
    await sleep(600);
    const red2 = await p8.evaluate(() => {
      const btn = document.querySelector('button[title^="Render queue"]');
      const badge = btn && btn.parentElement.querySelector('span');
      return { badgeBg: badge ? getComputedStyle(badge).backgroundColor : null,
        seen: localStorage.getItem('dz_queue_seen_failed') };
    });
    const isRed = c => !!c && /239,\s*68,\s*68/.test(c);
    T('Q8 badge rouge si failed non lu' + (failedNat ? ' (naturel)' : ' (simulé)'),
      isRed(red1 && red1.bg), JSON.stringify(red1));
    T('Q8 ouverture = lu (badge plus rouge, seen persisté)',
      !isRed(red2.badgeBg) && !!red2.seen && red2.seen.length > 2,
      JSON.stringify(red2).slice(0, 160));
    await p8.close();
  }

  /* Q9 — prefers-reduced-motion -> fade, pas de pulse */
  {
    const p9 = await browser.newPage();
    wire(p9);
    await p9.setViewport({ width: 1600, height: 950 });
    await p9.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
    await p9.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p9.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
    await p9.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(2000);
    const rm = await p9.evaluate(() => {
      const cs = getComputedStyle(document.querySelector('.dzq-panel'));
      return { transitionProp: cs.transitionProperty, transform: cs.transform };
    });
    T('Q9 reduced-motion = fade (opacity, transform none)',
      /opacity/.test(rm.transitionProp) && rm.transform === 'none', JSON.stringify(rm));
    await p9.close();
  }

  /* ── Q3-Q6 : job réel gratuit (Sprite Lab, remove_bg none) en DEUX fenêtres :
     extraction FRAÎCHE (source jamais extraite ≈ 4 s de job) puis génération.
     Le poll du panneau est à 2.5 s : une source déjà extraite (cache) peut
     finir avant le premier tick — d'où la préférence fraîche + double fenêtre. */
  const extractedSet = new Set(jobsBefore
    .filter(j => j.provider === 'sprite2d' && /extraction render/.test(j.title || ''))
    .map(j => (j.title.split('extraction render')[1] || '').trim().slice(0, 8)));
  const isVid = j => /\.(mp4|mov|webm|m4v|avi|mkv|gif)$/i.test(j.final_video_path || '');
  const okSrc = j => j.status === 'done' && j.provider !== 'sprite2d'
    && j.provider !== 'asset3d' && isVid(j);
  const render = jobsBefore.find(j => okSrc(j) && !extractedSet.has(j.job_id.slice(0, 8)))
    || jobsBefore.find(okSrc);
  if (!render) throw new Error('aucun render vidéo done disponible pour le job gratuit');
  console.log('source job gratuit: ' + render.job_id.slice(0, 8)
    + (extractedSet.has(render.job_id.slice(0, 8)) ? ' (cache extraction!)' : ' (fraîche)'));

  const badgeEval = () => page.evaluate(() => {
    const btn = document.querySelector('button[title^="Render queue"]');
    const badge = btn && btn.parentElement.querySelector('span');
    if (!badge) return null;
    return { txt: badge.textContent, pulse: badge.className.includes('dzq-pulse'),
      bg: getComputedStyle(badge).backgroundColor,
      anim: getComputedStyle(badge).animationName };
  });
  const grabBadge = async ms => {
    try {
      return await poll(badgeEval, v => v && parseInt(v.txt, 10) >= 1, ms, 350);
    } catch (e) { return null; }
  };
  const grabPanel = async () => {
    await page.click('button[title^="Render queue"]');
    await sleep(650);
    return page.evaluate(() => {
      const panel = document.querySelector('.dzq-panel');
      const cs = getComputedStyle(panel);
      return { on: panel.className.includes('on'), transform: cs.transform,
        visibility: cs.visibility, width: cs.width,
        header: /RENDER QUEUE/i.test(panel.innerText),
        running: [...panel.querySelectorAll('.scroll .upper')]
          .some(e => /running/i.test(e.textContent)),
        sprite: /Sprites/i.test(panel.querySelector('.scroll').innerText) };
    });
  };

  /* Le job gratuit est lancé en PUR API (pas de 2e onglet Puppeteer : les
     front-tab wars gelaient le protocole CDP). POST /api/assets/sprite
     extract_only = extraction locale gratuite, ~4-8 s sur source fraîche. */
  const launchFree = () => fetch(BASE + '/api/assets/sprite', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source: { kind: 'job', job_id: render.job_id },
      fps_sample: 10, max_frames: 40, remove_bg: 'none', extract_only: true,
      title: 'Sprites · extraction QA 11a',
    }),
  }).then(r => r.json());

  const j1 = await launchFree();
  if (!j1 || !j1.job_id) throw new Error('lancement extraction KO: ' + JSON.stringify(j1));
  console.log('job gratuit lancé:', j1.job_id.slice(0, 8));

  let q3 = await grabBadge(30000);
  if (q3) await page.screenshot({ path: OUT + '/after-badge-run.png' });
  let q4 = q3 ? await grabPanel() : null;
  if (q4) await page.screenshot({ path: OUT + '/after-panel-open.png' });
  T('Q3 badge compteur pendant le run', !!q3 && q3.pulse && /0,\s*229,\s*255/.test(q3.bg),
    JSON.stringify(q3));
  T('Q3 halo pulsé actif', !!q3 && q3.anim === 'dzq-halo', q3 ? `(anim=${q3.anim})` : '');
  T('Q4 panneau ouvert (translateX(0), 360px)',
    !!q4 && q4.on && q4.visibility === 'visible'
    && /matrix\(1,\s*0,\s*0,\s*1,\s*0,\s*0\)/.test(q4.transform)
    && q4.width === '360px', JSON.stringify(q4).slice(0, 200));
  T('Q4 card Running du job réel visible', !!q4 && q4.running && q4.sprite, '');

  /* Q5 — Esc ferme */
  await page.evaluate(() => window.__dzQueue.open());
  await sleep(600);
  await page.keyboard.press('Escape');
  await sleep(650);
  const q5 = await page.evaluate(() => {
    const panel = document.querySelector('.dzq-panel');
    return { on: panel.className.includes('on'), vis: getComputedStyle(panel).visibility };
  });
  T('Q5 Esc ferme le panneau', !q5.on && q5.vis === 'hidden', JSON.stringify(q5));
  await page.screenshot({ path: OUT + '/after-panel-esc.png' });

  /* Q6 — scrim cliquable */
  await page.evaluate(() => window.__dzQueue.open());
  await sleep(600);
  await page.mouse.click(600, 480);
  await sleep(650);
  const q6 = await page.evaluate(() => document.querySelector('.dzq-panel').className.includes('on'));
  T('Q6 clic scrim ferme le panneau', q6 === false, '');

  /* fin du job réel -> card en Recent */
  const doneJob = await poll(async () => {
    const js = await (await fetch(BASE + '/api/jobs?limit=60')).json();
    return js.find(j => j.provider === 'sprite2d' && !beforeIds.has(j.job_id));
  }, j => j && (j.status === 'done' || j.status === 'failed'), 240000, 2500);
  await sleep(3000);
  await page.evaluate(() => window.__dzQueue.open());
  await sleep(700);
  const rec = await page.evaluate(() => {
    const panel = document.querySelector('.dzq-panel');
    return {
      recent: [...panel.querySelectorAll('.scroll .upper')]
        .some(e => /recent/i.test(e.textContent)),
      sprite: /Sprites/i.test(panel.querySelector('.scroll').innerText),
    };
  });
  T('Recette job terminé visible en Recent', doneJob.status === 'done' && rec.recent && rec.sprite,
    `(job=${doneJob.status})`);
  await page.screenshot({ path: OUT + '/after-panel-recent.png' });

  /* cleanup strict */
  const jobsAfter = await (await fetch(BASE + '/api/jobs?limit=60')).json();
  const mine = jobsAfter.filter(j => j.provider === 'sprite2d' && !beforeIds.has(j.job_id));
  for (const j of mine) {
    await fetch(BASE + '/api/jobs/' + j.job_id, { method: 'DELETE' });
    console.log('cleanup: DELETE sprite2d ' + j.job_id.slice(0, 8));
  }

  await browser.close();
  console.log('\n=== RESULT ===');
  console.log('PASS ' + R.pass.length + ' / FAIL ' + R.fail.length);
  if (errors.length) console.log('console errors:', errors.slice(0, 6));
  fs.writeFileSync(OUT + '/result.json', JSON.stringify({ pass: R.pass, fail: R.fail, errors, noise }, null, 2));
  console.log('shots ->', OUT);
  process.exit(R.fail.length || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
