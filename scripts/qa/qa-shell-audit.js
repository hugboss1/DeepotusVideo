/* Harnais d'audit shell 11d — débordements + alignements sur TOUTES les vues.
   Vues SPA : Quick, Studio, Chapitres, Scheduler, Templates, News, Library,
   Game Assets (3D + wrappers 3D Studio/Sprites 2D/Tuiles — leurs iframes sont
   audités via les pages standalone), Settings. Standalone : /spritelab/,
   /tilelab/, /atelier/, /studio3d/ (v2.1). DZ_BASE=<url> change le serveur
   cible (défaut http://127.0.0.1:8765).
   Scans par vue :
   - page-hscroll   : scroll horizontal de la page entière ;
   - viewport-spill : élément qui sort du viewport à gauche/droite ;
   - clip-spill     : élément (static/relative) qui déborde d'un ancêtre en
                      overflow hidden/clip -> contenu INATTEIGNABLE (les
                      ancêtres auto/scroll sont légitimes, on continue) ;
   - text-overflow  : feuille en overflow visible dont le texte dépasse la boîte ;
   - grid2-misalign : rangées .grid2, tops alignés à ±2 px ;
   - row-misalign   : rangées toolbar (flex row <=48px, >=3 enfants dont >=2
                      contrôles), centres verticaux alignés à ±2.5 px.
   Sortie : result.json + un screenshot annoté (outline rouge) par vue en
   défaut. Code sortie = nombre de vues en défaut (0 = vert) ; 99 = zéro vue
   en défaut MAIS erreurs console collectées (à lire dans result.json).
   ANGLES MORTS assumés (un « 0 finding » ne couvre pas) : feuilles inline
   (clientWidth=0) au scan text-overflow ; contenu coupé par le HAUT d'un
   clip ; ancêtres à opacity:0 (enfants scannés quand même) ; absolute dont
   le bloc conteneur saute un clippeur intermédiaire (viewport-spill borné
   trop tôt). Constat CR 20/07/2026 — à durcir si un cas réel apparaît.
   Options : DZ_BUNDLE=<chemin> sert ce bundle ; DZ_WEBROOT=<frontend/> sert
   les pages standalone depuis le repo (audit avant déploiement).
   Run : NODE_PATH=<scratchpad>/node_modules node scripts/qa/qa-shell-audit.js [outdir] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const BASE = process.env.DZ_BASE || 'http://127.0.0.1:8765';
const OUT = process.argv[2] || path.join(__dirname, 'shots-shell-audit');
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* Exclusions assumées (justifiées) — sélecteurs ancêtres ignorés par le scan. */
const IGNORE = [
  '.dz-tip',            // tooltip fixe, hors flux par design
  '.dz-studio-grid',    // canvas nodal pannable : le contenu déborde PAR DESIGN
  '[data-dzpreview]',   // régions des previews spatiaux (éditeur + minis) :
                        // représentation à l'échelle, labels clippés par design
];

function scanPage(ignore) {
  const vw = innerWidth;
  const out = [];
  const short = el => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    else if (typeof el.className === 'string' && el.className.trim())
      s += '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.');
    const p = el.parentElement;
    if (p && p !== document.body) {
      let ps = p.tagName.toLowerCase();
      if (p.id) ps += '#' + p.id;
      else if (typeof p.className === 'string' && p.className.trim())
        ps += '.' + p.className.trim().split(/\s+/)[0];
      s = ps + '>' + s;
    }
    return s;
  };
  const vis = el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility !== 'visible' || +cs.opacity === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 2 && r.height > 2;
  };
  const flag = (type, el, detail) => out.push({ type, sel: short(el), detail, _el: el });

  const de = document.documentElement;
  if (de.scrollWidth > de.clientWidth + 1)
    out.push({ type: 'page-hscroll', sel: 'html', detail: `scrollWidth ${de.scrollWidth} > ${de.clientWidth}` });

  const els = [...document.querySelectorAll('body *')].filter(el =>
    !(el.closest('svg') && el.tagName.toLowerCase() !== 'svg')
    && !/^(SCRIPT|STYLE|LINK|META|BR|OPTION|IFRAME)$/.test(el.tagName)
    && !ignore.some(q => { try { return el.closest(q); } catch (e) { return false; } })
    && vis(el));

  for (const el of els) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);

    if ((r.right > vw + 1 || r.left < -1) && cs.transform === 'none' && cs.position !== 'fixed') {
      /* borne par les ancêtres clippants : un élément déjà contenu par un
         overflow hidden/auto n'est pas un débordement de viewport (le cas
         hidden inatteignable est traité par clip-spill). */
      let effL = r.left, effR = r.right, a2 = el.parentElement;
      while (a2 && a2 !== document.documentElement) {
        const acs2 = getComputedStyle(a2);
        if (acs2.overflowX !== 'visible') {
          const ar2 = a2.getBoundingClientRect();
          effL = Math.max(effL, ar2.left); effR = Math.min(effR, ar2.right);
        }
        a2 = a2.parentElement;
      }
      if (effR > effL && (effR > vw + 1 || effL < -1)) {
        flag('viewport-spill', el, `left ${Math.round(r.left)} right ${Math.round(r.right)} vw ${vw}`);
        continue;
      }
    }

    if (cs.position === 'static' || cs.position === 'relative') {
      let a = el.parentElement;
      while (a && a !== document.body) {
        const acs = getComputedStyle(a);
        const ox = acs.overflowX, oy = acs.overflowY;
        const ar = a.getBoundingClientRect();
        let hit = null;
        if (ox !== 'visible') {
          if ((ox === 'hidden' || ox === 'clip') && (r.right > ar.right + 2.5 || r.left < ar.left - 2.5))
            hit = `X hors de ${short(a)} (el ${Math.round(r.left)}..${Math.round(r.right)}, clip ${Math.round(ar.left)}..${Math.round(ar.right)})`;
        }
        if (!hit && oy !== 'visible') {
          if ((oy === 'hidden' || oy === 'clip') && r.bottom > ar.bottom + 2.5)
            hit = `Y hors de ${short(a)} (el bottom ${Math.round(r.bottom)}, clip ${Math.round(ar.bottom)})`;
        }
        if (hit) { flag('clip-spill', el, hit); break; }
        if (ox !== 'visible' || oy !== 'visible') break; // scrollable/clip légitime : on s'arrête là
        a = a.parentElement;
      }
    }

    if (!el.children.length && cs.overflowX === 'visible' && el.clientWidth > 0
      && el.scrollWidth > el.clientWidth + 2)
      flag('text-overflow', el, `scrollWidth ${el.scrollWidth} > clientWidth ${el.clientWidth}`);
  }

  for (const g of document.querySelectorAll('.grid2')) {
    if (!vis(g)) continue;
    const kids = [...g.children].filter(vis);
    const rows = [];
    kids.map(k => ({ k, top: k.getBoundingClientRect().top }))
      .sort((a, b) => a.top - b.top)
      .forEach(e => {
        const grp = rows.find(r0 => Math.abs(r0[0].top - e.top) < 6);
        grp ? grp.push(e) : rows.push([e]);
      });
    rows.forEach((row, ri) => {
      if (row.length < 2) return;
      const spread = row[row.length - 1].top - row[0].top;
      if (spread > 2) flag('grid2-misalign', g, `rangée ${ri} : tops étalés sur ${spread.toFixed(1)}px`);
    });
  }

  for (const el of els) {
    const cs = getComputedStyle(el);
    if (cs.display !== 'flex' || !cs.flexDirection.startsWith('row') || cs.flexWrap === 'wrap') continue;
    const r = el.getBoundingClientRect();
    if (r.height > 48 || r.height < 16) continue;
    const kids = [...el.children].filter(k => vis(k) && getComputedStyle(k).position !== 'absolute');
    if (kids.length < 3) continue;
    const ctl = kids.filter(k => /^(BUTTON|SELECT|INPUT)$/.test(k.tagName)
      || k.querySelector(':scope>[data-dzselect]') || k.hasAttribute('data-dzselect')).length;
    if (ctl < 2) continue;
    const centers = kids.map(k => { const kr = k.getBoundingClientRect(); return kr.y + kr.height / 2; });
    const spread = Math.max(...centers) - Math.min(...centers);
    if (spread > 2.5) flag('row-misalign', el, `centres verticaux étalés sur ${spread.toFixed(1)}px (${kids.length} enfants)`);
  }

  if (!document.getElementById('dz-audit-style')) {
    const st = document.createElement('style');
    st.id = 'dz-audit-style';
    st.textContent = '.dz-audit-flag{outline:2px solid #ef4444!important;outline-offset:-1px}';
    document.head.appendChild(st);
  }
  out.forEach(f => { if (f._el && f._el.classList) f._el.classList.add('dz-audit-flag'); });
  out.forEach(f => delete f._el);
  return out;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 180000,
    args: ['--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding'],
  });
  const errors = [];
  const KNOWN = /(images\/sheet\.png|\/video\b.*40[34]|40[34].*\/video|\/image\b.*404|ERR_ABORTED|Failed to load resource)/i;
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !KNOWN.test(m.text())) errors.push('console: ' + m.text()); });
  await page.setViewport({ width: 1600, height: 950 });

  /* DZ_BUNDLE : sert ce bundle. DZ_WEBROOT (chemin de frontend/) : sert les
     fichiers des pages standalone (spritelab/tilelab/atelier) depuis le repo
     — recette AVANT déploiement. */
  const LOCAL_BUNDLE = process.env.DZ_BUNDLE || '';
  const WEBROOT = process.env.DZ_WEBROOT || '';
  const MIME = { '.css': 'text/css', '.js': 'application/javascript', '.html': 'text/html' };
  if (LOCAL_BUNDLE || WEBROOT) {
    await page.setRequestInterception(true);
    page.on('request', rq => {
      const pn = new URL(rq.url()).pathname;
      if (LOCAL_BUNDLE && pn.endsWith('/assets/index-BEOJX8L5.js')) {
        return rq.respond({ status: 200, contentType: 'application/javascript; charset=utf-8',
          body: fs.readFileSync(LOCAL_BUNDLE) });
      }
      if (WEBROOT && /^\/(spritelab|tilelab|atelier|studio3d|meshy)\//.test(pn)) {
        const rel = pn.endsWith('/') ? pn + 'index.html' : pn;
        const fp = path.join(WEBROOT, rel.replace(/^\//, ''));
        if (fs.existsSync(fp)) {
          return rq.respond({ status: 200,
            contentType: (MIME[path.extname(fp)] || 'application/octet-stream') + '; charset=utf-8',
            body: fs.readFileSync(fp) });
        }
      }
      rq.continue();
    });
  }

  const reports = [];
  const audit = async label => {
    const findings = await page.evaluate(scanPage, IGNORE);
    /* iframes same-origin (Game Assets > Sprites 2D / Tuiles) : audit du
       document embarqué aussi — les débordements internes y vivent. */
    for (const f of page.frames()) {
      if (f === page.mainFrame() || !/spritelab|tilelab|atelier|studio3d/.test(f.url())) continue;
      try {
        const sub = await f.evaluate(scanPage, IGNORE);
        sub.forEach(x => { x.sel = 'iframe:' + x.sel; findings.push(x); });
      } catch (e) { /* frame détachée */ }
    }
    const shot = label.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.png';
    if (findings.length) await page.screenshot({ path: path.join(OUT, shot) });
    for (const f of page.frames()) {
      await f.evaluate(() =>
        document.querySelectorAll('.dz-audit-flag').forEach(e => e.classList.remove('dz-audit-flag')))
        .catch(() => {});
    }
    reports.push({ view: label, count: findings.length, findings: findings.slice(0, 40) });
    console.log((findings.length ? 'FAIL ' : 'PASS ') + label + ' — ' + findings.length + ' finding(s)');
    findings.slice(0, 8).forEach(f => console.log('   [' + f.type + '] ' + f.sel + ' — ' + f.detail));
  };

  /* — vues SPA — */
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
  await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
  await sleep(2500);

  const nav = async v => {
    await page.evaluate(v2 => {
      const b = [...document.querySelectorAll('aside nav button')]
        .find(x => (x.innerText || x.title || '').split('\n')[0] === v2);
      b && b.click();
    }, v);
    await sleep(1400);
  };

  for (const v of ['Quick', 'Studio', 'Chapitres', 'Scheduler', 'Templates', 'News', 'Library', 'Settings']) {
    await nav(v);
    await audit('view-' + v);
  }

  await nav('Game Assets');
  for (const tab of ['3D', '3D Studio', 'Sprites 2D', 'Tuiles']) {
    await page.evaluate(t => {
      const b = [...document.querySelectorAll('main button, button')]
        .find(x => (x.textContent || '').trim().endsWith(t));
      b && b.click();
    }, tab);
    await sleep(1600);
    await audit('ga-' + tab);
  }

  /* — pages standalone — */
  for (const u of ['/spritelab/', '/tilelab/', '/atelier/', '/studio3d/']) {
    await page.goto(BASE + u, { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
    await sleep(2000);
    await audit('standalone' + u.replace(/\//g, '-'));
  }

  /* — passe ÉTROITE 900px : cas connu « Action à animer » (Sprite Lab en
     iframe Game Assets sur fenêtre étroite : la grille .panes imposait
     980px de min et débordait). Rejouée sur les 3 pages standalone. — */
  await page.setViewport({ width: 900, height: 950 });
  for (const u of ['/spritelab/', '/tilelab/', '/atelier/', '/studio3d/']) {
    await page.goto(BASE + u, { waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
    await sleep(2000);
    await audit('narrow900' + u.replace(/\//g, '-'));
  }

  await browser.close();
  const bad = reports.filter(r => r.count > 0);
  console.log('\n=== RESULT ===');
  console.log('vues auditées: ' + reports.length + ' — en défaut: ' + bad.length
    + ' — findings: ' + reports.reduce((a, r) => a + r.count, 0));
  if (errors.length) console.log('console errors:', errors.slice(0, 6));
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ reports, errors }, null, 2));
  process.exit(bad.length ? Math.min(bad.length, 99) : (errors.length ? 99 : 0));
})().catch(e => { console.error('FATAL', e); process.exit(1); });
