/* Mesure de la barre du graphe du Studio (10/10/2026) — chaque bouton est-il dans sa colonne et au premier plan ?
   Ouvre le Studio, inspecteur DÉPLIÉ, à chaque largeur demandée ; pour chaque enfant visible de la barre, rend ses
   bords et ce que elementFromPoint trouve en son centre. Écrit un JSON sur stdout, rien d'autre.
   Run : NODE_PATH=<…>/scripts/qa/node_modules node scripts/qa/qa-studio-barre.js <base> [largeurs…]
   ex. : node scripts/qa/qa-studio-barre.js http://127.0.0.1:8823 1440x900 1680x945 */
const puppeteer = require('puppeteer-core');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const BASE = process.argv[2] || 'http://127.0.0.1:8823';
const TAILLES = (process.argv.length > 3 ? process.argv.slice(3) : ['1440x900']).map(t => t.split('x').map(Number));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.DZ_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', protocolTimeout: 120000,
  });
  const out = { erreurs: [], tailles: [] };
  try {
    const page = await browser.newPage();
    page.on('pageerror', e => out.erreurs.push('pageerror: ' + e.message));
    await page.setViewport({ width: TAILLES[0][0], height: TAILLES[0][1] });
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.evaluate(() => {
      localStorage.setItem('dz_onboarded', '1');
      localStorage.setItem('dz_studio_insp', '1');
      localStorage.setItem('dz_studio_dock', '1');
    });
    await page.goto(BASE + '/', { waitUntil: 'networkidle2', timeout: 60000 });
    await sleep(1500);
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'studio' } })));
    await page.waitForSelector('.dz-studio-grid', { timeout: 20000 });
    for (const [w, h] of TAILLES) {
      await page.setViewport({ width: w, height: h });
      await sleep(900);
      out.tailles.push(await page.evaluate((w, h) => {
        const g = document.querySelector('.dz-studio-grid');
        const centre = g.children[1], insp = g.lastElementChild, barre = centre.firstElementChild;
        const rc = centre.getBoundingClientRect(), ri = insp.getBoundingClientRect(), rb = barre.getBoundingClientRect();
        const enfants = [...barre.children].map(b => {
          const r = b.getBoundingClientRect();
          if (!r.width || !r.height) return null;
          const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return { tag: b.tagName, texte: (b.textContent || '').trim().slice(0, 40), gauche: r.left, droite: r.right,
            haut: r.top, bas: r.bottom, premier_plan: !!e && b.contains(e) };
        }).filter(Boolean);
        const bandeau = [...centre.children].find(c => c !== barre && getComputedStyle(c).position === 'absolute'
          && c.style.top && c.style.top.indexOf('--dz-gbar-h') >= 0);
        return { largeur: w, hauteur: h, inspecteur_deplie: !g.className.includes('dz-insp-hidden'),
          centre: [rc.left, rc.right], inspecteur: [ri.left, ri.right], barre: { haut: rb.top, bas: rb.bottom },
          var_barre: getComputedStyle(centre).getPropertyValue('--dz-gbar-h').trim(),
          bandeau_haut: bandeau ? bandeau.getBoundingClientRect().top : null, enfants };
      }, w, h));
    }
  } catch (e) {
    out.erreurs.push('exception: ' + (e && e.message || e));
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify(out));
})();
