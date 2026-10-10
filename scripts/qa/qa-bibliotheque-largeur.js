/* Mesure de la largeur de la Bibliothèque (10/10/2026) — l'écran tient-il dans la fenêtre ?
   Ouvre la Bibliothèque à chaque taille demandée, sur la puce Images puis sur la puce Audio (tiroir Sons) ; rend
   documentElement.scrollWidth, innerWidth, les bords de <main>, et le bord droit de chaque enfant visible de la barre
   d'outils, des pastilles de l'en-tête et (Audio) des boutons « Récents » / « Tous » du tiroir. La coque a
   overflow:hidden : scrollWidth reste égal à innerWidth même quand <main> déborde — d'où la mesure des bords.
   Écrit un JSON sur stdout, rien d'autre.
   Run : NODE_PATH=<…>/scripts/qa/node_modules node scripts/qa/qa-bibliotheque-largeur.js <base> [tailles…]
   ex. : node scripts/qa/qa-bibliotheque-largeur.js http://127.0.0.1:8837 1366x768 1440x900 */
const puppeteer = require('puppeteer-core');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const BASE = process.argv[2] || 'http://127.0.0.1:8837';
const TAILLES = (process.argv.length > 3 ? process.argv.slice(3) : ['1440x900']).map(t => t.split('x').map(Number));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.DZ_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 120000,
  });
  const out = { erreurs: [], mesures: [] };
  try {
    const page = await browser.newPage();
    page.on('pageerror', e => out.erreurs.push('pageerror: ' + e.message));
    await page.setViewport({ width: TAILLES[0][0], height: TAILLES[0][1] });
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.evaluate(() => localStorage.setItem('dz_onboarded', '1'));
    await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 60000 });
    await sleep(1500);
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'library' } })));
    await page.waitForSelector('[data-dz-biblio-barre], main', { timeout: 20000 });
    await sleep(1500);
    for (const vue of ['Images', 'Audio']) {
      await page.evaluate(v => {
        const b = [...document.querySelectorAll('main button')].find(x => (x.textContent || '').trim().startsWith(v));
        if (b) b.click();
      }, vue);
      await sleep(1200);
      for (const [w, h] of TAILLES) {
        await page.setViewport({ width: w, height: h });
        await sleep(900);
        out.mesures.push(await page.evaluate((vue, w, h) => {
          const m = document.querySelector('main'), rm = m.getBoundingClientRect();
          const bord = e => { const r = e.getBoundingClientRect(); return r.width && r.height ? r : null; };
          const lit = e => ({ texte: (e.textContent || '').trim().slice(0, 40) || e.tagName, droite: bord(e).right });
          const titre = [...m.querySelectorAll('div.display')].find(d => d.textContent.trim() === 'Bibliothèque'
            || d.textContent.trim() === 'Library');
          const barre = titre ? titre.parentElement : null;
          const enTete = m.querySelector('header');
          const pastilles = enTete ? [...enTete.querySelectorAll('span')].filter(s => /^(fal|heygen|voix|voice|v\d)/i
            .test((s.textContent || '').trim()) && bord(s)) : [];
          const filtres = vue === 'Audio' ? [...m.querySelectorAll('button, select')].filter(b => bord(b)
            && /^(Tous|All|Récents|Recent)/.test((b.textContent || '').trim().split('\n')[0])) : [];
          return { vue, largeur: w, hauteur: h, innerWidth: innerWidth,
            scrollWidth: document.documentElement.scrollWidth, main: [rm.left, rm.right],
            barre_marquee: !!(barre && barre.hasAttribute('data-dz-biblio-barre')),
            barre: barre ? [...barre.children].filter(bord).map(lit) : null,
            pastilles: pastilles.map(lit), filtres: filtres.map(lit),
            onglet_actif: vue };
        }, vue, w, h));
      }
    }
  } catch (e) {
    out.erreurs.push('exception: ' + (e && e.message || e));
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify(out));
})();
