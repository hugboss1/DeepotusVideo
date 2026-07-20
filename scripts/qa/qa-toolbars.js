/* Recette 11c toolbars — tooltips sombres 100 ms + JobCards du panneau queue.
   Q1  couche tooltip présente (style #dztip-style + poignée __dzTip).
   Q2  délai : rien à ~50 ms, tooltip visible à ~300 ms avec le bon texte.
   Q3  title natif suspendu pendant le survol (déplacé vers data-dztip).
   Q4  style : sombre (--bg-panel-2), max-width 280, fixed, z-index 400.
   Q5  clamp viewport : ne dépasse jamais le bord droit.
   Q6  texte long : wrap à 280 px max, toujours dans le viewport.
   Q7  mouseout -> tooltip masqué ET title restauré (compat recettes [title=]).
   Q8  mousedown -> title restauré immédiatement (un clic Puppeteer suffit).
   Q9  JobCards (jobs simulés) : colonne texte réelle (>=120px), titre uuid et
       méta uuid sur UNE ligne (ellipsis), erreur 1 ligne, rien ne déborde.
   Q10 tooltip du uuid méta = job_id complet.
   Q11 selects : libellé visible, jamais de tooltip custom par-dessus.
   Q12 clavier : Tab jusqu'à l'icône queue -> tooltip (focus-visible).
   Q13 au repos : tout [data-dztip] a retrouvé son [title] (compat QA).
   Jobs /api/jobs interceptés (1 running uuid-title, 1 done uuid-title,
   1 failed erreur longue) -> assertions déterministes, aucun job réel créé.
   DZ_BUNDLE=<chemin> : sert ce bundle à la place de celui déployé (recette
   AVANT déploiement) ; sans variable, teste l'app installée telle quelle.
   Run : NODE_PATH=<scratchpad>/node_modules node scripts/qa/qa-toolbars.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-toolbars');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const RUN_ID = '11111111-aaaa-bbbb-cccc-222222222222';
const DONE_ID = '33333333-dddd-eeee-ffff-444444444444';
const FAIL_ID = '55555555-9999-8888-7777-666666666666';
const LONG_ERR = 'QA simulated very long failure message that must stay on a single '
  + 'ellipsised line inside the 360px queue panel metadata row no matter what';
const FAKE_JOBS = JSON.stringify([
  { job_id: RUN_ID, status: 'processing', progress: 42, title: '',
    provider: 'seedance', aspect_ratio: '9:16', image_filename: '' },
  { job_id: DONE_ID, status: 'done', progress: 100, title: '',
    provider: 'sprite2d', duration_s: 12, image_filename: '' },
  { job_id: FAIL_ID, status: 'failed', progress: 7, title: 'qa_fail_toolbars',
    provider: 'seedance', error: LONG_ERR, image_filename: '' },
]);

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
  const KNOWN = /(images\/sheet\.png|\/video\b.*40[34]|40[34].*\/video|\/image\b.*404|ERR_ABORTED|Failed to load resource)/i;
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1600, height: 950 });

  const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
  await page.setRequestInterception(true);
  page.on('request', rq => {
    const u = rq.url();
    if (u.includes('/api/jobs') && !/\/(video|image)\b/.test(u)) {
      rq.respond({ status: 200, contentType: 'application/json', body: FAKE_JOBS });
    } else if (LOCAL_BUNDLE && u.includes('/assets/index-BEOJX8L5.js')) {
      rq.respond({ status: 200, contentType: 'application/javascript; charset=utf-8',
        body: fs.readFileSync(LOCAL_BUNDLE) });
    } else rq.continue();
  });

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(fid => {
    localStorage.setItem('dz_onboarded', '1');
    // le failed simulé est déjà « lu » -> badge cyan, title stable « 1 running »
    localStorage.setItem('dz_queue_seen_failed', JSON.stringify([fid]));
  }, FAIL_ID);
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
  await sleep(3000);

  /* Q1 — couche présente */
  const q1 = await page.evaluate(() => ({
    style: !!document.getElementById('dztip-style'),
    handle: !!window.__dzTip,
    visible: window.__dzTip ? window.__dzTip.state.visible : null,
  }));
  T('Q1 couche tooltip présente, invisible au repos',
    q1.style && q1.handle && q1.visible === false, JSON.stringify(q1));

  /* Q2 — délai 100 ms sur l'icône queue (1 running simulé) */
  const qbox = await page.evaluate(() => {
    const b = document.querySelector('button[title^="Render queue"]');
    if (!b) return null;
    const r = b.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, title: b.title };
  });
  T('Q2a icône queue trouvée (title "Render queue — 1 running")',
    !!qbox && qbox.title === 'Render queue — 1 running', JSON.stringify(qbox));
  await page.mouse.move(qbox.x, qbox.y);
  await sleep(40);
  const q2early = await page.evaluate(() => window.__dzTip.state.visible);
  await sleep(260);
  const q2late = await page.evaluate(() => window.__dzTip.state);
  T('Q2b rien avant ~50 ms, tooltip à ~300 ms avec le texte du title',
    q2early === false && q2late.visible === true && q2late.text === 'Render queue — 1 running',
    JSON.stringify({ early: q2early, late: q2late }));

  /* Q3 — natif suspendu pendant le survol */
  const q3 = await page.evaluate(() => {
    const b = document.querySelector('[data-dztip^="Render queue"]');
    return b ? { hasTitle: b.hasAttribute('title'), dztip: b.getAttribute('data-dztip') } : null;
  });
  T('Q3 title natif suspendu (data-dztip porte le texte)',
    !!q3 && !q3.hasTitle && q3.dztip === 'Render queue — 1 running', JSON.stringify(q3));

  /* Q4 — style sombre spec §7 */
  const q4 = await page.evaluate(() => {
    const t = document.querySelector('.dz-tip');
    const c = getComputedStyle(t);
    return { bg: c.backgroundColor, maxW: c.maxWidth, pos: c.position,
      z: c.zIndex, radius: c.borderRadius };
  });
  T('Q4 sombre #0f1c30, max-width 280, fixed, z 400',
    q4.bg === 'rgb(15, 28, 48)' && q4.maxW === '280px' && q4.pos === 'fixed' && q4.z === '400',
    JSON.stringify(q4));
  await page.screenshot({ path: path.join(OUT, 'tooltip-queue.png'),
    clip: { x: 1600 - 420, y: 0, width: 420, height: 120 } });

  /* Q5 — clamp bord droit (l'icône queue est près du bord) */
  const q5 = await page.evaluate(() => {
    const r = document.querySelector('.dz-tip').getBoundingClientRect();
    return { right: Math.round(r.right), vw: window.innerWidth };
  });
  T('Q5 clamp viewport (right <= vw-4)', q5.right <= q5.vw - 4, JSON.stringify(q5));

  /* Q6 — texte long : wrap 280 max, dans le viewport */
  await page.evaluate(() => {
    const host = document.querySelector('button[data-dztip^="Render queue"]').parentElement;
    const b = document.createElement('button');
    b.id = 'qa-long-tip';
    b.title = 'QA long tooltip — ' + 'lorem ipsum dolor sit amet consectetur '.repeat(8);
    b.textContent = '?';
    b.style.cssText = 'width:24px;height:24px';
    host.appendChild(b);
  });
  const lbox = await page.evaluate(() => {
    const r = document.getElementById('qa-long-tip').getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  await page.mouse.move(lbox.x, lbox.y);
  await sleep(300);
  const q6 = await page.evaluate(() => {
    const r = document.querySelector('.dz-tip').getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height),
      right: Math.round(r.right), vw: window.innerWidth,
      visible: window.__dzTip.state.visible };
  });
  T('Q6 long texte : visible, largeur <= 282, wrap (h > 30), dans le viewport',
    q6.visible && q6.w <= 282 && q6.h > 30 && q6.right <= q6.vw - 4, JSON.stringify(q6));
  await page.evaluate(() => document.getElementById('qa-long-tip').remove());

  /* Q7 — mouseout : masqué + title restauré */
  await page.mouse.move(760, 500);
  await sleep(200);
  const q7 = await page.evaluate(() => ({
    visible: window.__dzTip.state.visible,
    restored: !!document.querySelector('button[title="Render queue — 1 running"]'),
  }));
  T('Q7 mouseout -> masqué, title restauré', !q7.visible && q7.restored, JSON.stringify(q7));

  /* Q8 — mousedown restaure title immédiatement (compat clic Puppeteer) */
  await page.mouse.move(qbox.x, qbox.y);
  await sleep(300);
  await page.mouse.down();
  const q8mid = await page.evaluate(() => ({
    visible: window.__dzTip.state.visible,
    restored: !!document.querySelector('button[title^="Render queue"]'),
  }));
  await page.mouse.up();
  await sleep(700);
  const q8panel = await page.evaluate(() => window.__dzQueue.state.open);
  T('Q8 mousedown -> tooltip masqué + title déjà restauré ; le clic ouvre le panneau',
    !q8mid.visible && q8mid.restored && q8panel === true, JSON.stringify({ ...q8mid, panel: q8panel }));

  /* Q9 — JobCards : géométrie 2 rangées, une ligne partout, zéro débordement */
  const q9 = await page.evaluate(() => {
    const list = document.querySelector('.dzq-panel .scroll');
    const cards = [...list.querySelectorAll('div')].filter(d => {
      const cs = getComputedStyle(d);
      return cs.display === 'grid' && cs.gridTemplateColumns.split(' ').length === 3;
    });
    return cards.map(card => {
      const cr = card.getBoundingClientRect();
      const cols = getComputedStyle(card).gridTemplateColumns.split(' ').map(parseFloat);
      const uuid = [...card.querySelectorAll('.mono')].find(s => /^[0-9a-f-]{20,}/.test(s.textContent));
      const metaRow = uuid ? uuid.parentElement : null;
      const textBlock = metaRow ? metaRow.parentElement.getBoundingClientRect() : { width: 0, height: 999 };
      const spill = [...card.querySelectorAll('*')].filter(k => {
        const kr = k.getBoundingClientRect();
        return kr.width && (kr.right > cr.right + 1 || kr.left < cr.left - 1 || kr.bottom > cr.bottom + 1);
      }).length;
      const zero = [...card.children].filter(k => k.getBoundingClientRect().width === 0).length;
      return { h: Math.round(cr.height), col2: Math.round(cols[1]),
        metaRowH: metaRow ? Math.round(metaRow.getBoundingClientRect().height) : 999,
        uuidW: uuid ? uuid.clientWidth : 0,
        textW: Math.round(textBlock.width), textH: Math.round(textBlock.height),
        spill, zero,
        txt: (card.innerText || '').slice(0, 30) };
    });
  });
  const q9ok = q9.length === 3 && q9.every(c =>
    c.col2 >= 80 && c.h <= 120 && c.spill === 0 && c.zero === 0
    && c.metaRowH <= 20 && c.uuidW > 60 && c.textW >= 200 && c.textH <= 44);
  T('Q9 3 cards : bloc texte >= 200px / <= 2 lignes, rangée méta 1 ligne, uuid lisible, 0 débordement, 0 colonne nulle',
    q9ok, JSON.stringify(q9));
  await page.screenshot({ path: path.join(OUT, 'panel-cards.png'),
    clip: { x: 1600 - 380, y: 0, width: 380, height: 500 } });

  /* Q10 — tooltip du uuid méta = job_id complet */
  const ubox = await page.evaluate(id => {
    const s = [...document.querySelectorAll('.dzq-panel .mono')]
      .find(e => e.getAttribute('title') === id || e.getAttribute('data-dztip') === id);
    if (!s) return null;
    const r = s.getBoundingClientRect();
    return { x: r.x + Math.min(30, r.width / 2), y: r.y + r.height / 2 };
  }, RUN_ID);
  await page.mouse.move(ubox.x, ubox.y);
  await sleep(300);
  const q10 = await page.evaluate(() => window.__dzTip.state);
  T('Q10 tooltip uuid méta = job_id complet',
    q10.visible && q10.text === RUN_ID, JSON.stringify(q10));

  /* ferme le panneau (Esc masque aussi le tooltip) */
  await page.keyboard.press('Escape');
  await sleep(500);

  /* Q11 — selects/dropdowns (composant custom `re`, marqueur data-dzselect) :
     libellé visible, jamais de tooltip custom par-dessus. Le seul <select>
     natif de l'app (Optimize, Game Assets 3D) est couvert par l'exclusion
     SELECT de la couche tooltip. */
  let q11 = [], q11view = '';
  for (const view of ['Quick', 'Studio', 'Settings']) {
    await page.evaluate(v => {
      const b = [...document.querySelectorAll('aside nav button')]
        .find(x => (x.innerText || x.title || '').split('\n')[0] === v);
      b && b.click();
    }, view);
    await sleep(900);
    q11 = await page.evaluate(() => {
      const sels = [...document.querySelectorAll('[data-dzselect]')].filter(s => s.offsetParent);
      return sels.map(s => ({
        label: (s.querySelector('span') ? s.querySelector('span').textContent : '').trim(),
        w: s.offsetWidth, titled: s.hasAttribute('title'),
      }));
    });
    if (q11.length) { q11view = view; break; }
  }
  const q11ok = q11.length >= 1 && q11.every(s => s.label.length >= 1 && s.w >= 40 && !s.titled);
  T('Q11a dropdowns (' + q11view + ') : libellé sélectionné visible, sans title (' + q11.length + ' selects)',
    q11ok, JSON.stringify(q11.slice(0, 5)));
  const sbox = await page.evaluate(() => {
    const s = [...document.querySelectorAll('[data-dzselect]')].find(e => e.offsetParent);
    if (!s) return null;
    const r = s.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  let q11b = null;
  if (sbox) {
    await page.mouse.move(sbox.x, sbox.y);
    await sleep(300);
    q11b = await page.evaluate(() => window.__dzTip.state.visible);
  }
  T('Q11b survol dropdown -> aucun tooltip custom', q11b === false, JSON.stringify({ q11b }));

  /* Q12 — clavier : Tab jusqu'à l'icône queue -> tooltip focus-visible */
  /* 2 tentatives : l'app peut reprendre le focus (autofocus/poll) pendant la
     fenêtre d'affichage -> focusout masque légitimement ; on re-tabule. */
  let q12 = { reached: false, visible: false, text: '', active: '' };
  for (let attempt = 0; attempt < 2 && !(q12.reached && q12.visible); attempt++) {
    await page.mouse.move(4, 946);
    await page.keyboard.press('Escape');
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await sleep(150);
    let reached = false;
    for (let i = 0; i < 60 && !reached; i++) {
      await page.keyboard.press('Tab');
      reached = await page.evaluate(() => {
        const a = document.activeElement;
        const t = (a && (a.getAttribute('title') || a.getAttribute('data-dztip'))) || '';
        return t.startsWith('Render queue');
      });
    }
    await sleep(300);
    q12 = await page.evaluate(() => ({
      ...window.__dzTip.state,
      active: document.activeElement ? document.activeElement.tagName + '.' + (document.activeElement.className || '') : '',
    }));
    q12.reached = reached;
  }
  T('Q12 focus clavier icône queue -> tooltip visible',
    q12.reached && q12.visible && q12.text.startsWith('Render queue'), JSON.stringify(q12));

  /* Q13 — au repos : tout [data-dztip] a retrouvé son [title] */
  await page.mouse.move(4, 946);
  await page.keyboard.press('Escape');
  await sleep(200);
  const q13 = await page.evaluate(() => {
    const stolen = [...document.querySelectorAll('[data-dztip]')]
      .filter(e => !e.hasAttribute('title')).length;
    const titled = document.querySelectorAll('[title]').length;
    return { stolen, titled };
  });
  T('Q13 repos : 0 title volé, [title] disponibles pour les recettes',
    q13.stolen === 0 && q13.titled >= 5, JSON.stringify(q13));

  await browser.close();
  console.log('\n=== RESULT ===');
  console.log('PASS ' + R.pass.length + ' / FAIL ' + R.fail.length);
  if (errors.length) console.log('console errors:', errors.slice(0, 6));
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ pass: R.pass, fail: R.fail, errors }, null, 2));
  process.exit(R.fail.length || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
