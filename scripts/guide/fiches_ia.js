// fiches_ia.js (t193) — les trois temps des fiches didactiques, capturés dans Chrome sans fenêtre sur le backend de
// PREUVE du guide (serve_guide_ia.py : génération et détourage SIMULÉS, aucune dépense), en FR puis en EN.
//   t1 : l'état de départ ; t2 : l'option surlignée + son nom en pastille + le curseur (calque posé AU-DESSUS de la
//   page, retiré aussitôt) ; t3 : le résultat, APRÈS avoir déclenché l'option pour de vrai.
// Sortie : <dossier>/<id>.<lang>.t1|t2|t3.png, à assembler par assembler.py du skill didacticiel-option.
// Usage : NODE_PATH=<dépôt principal>/scripts/qa/node_modules node scripts/guide/fiches_ia.js <dossier> [id…]
// Données : serve_guide_ia.py + semer_calques_ia.py (document « Affiche à calques », photo « paysage-demo.png »).
const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");
const BASE = "http://127.0.0.1:8809";
const OUT = process.argv[2];
const SEULES = process.argv.slice(3);
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
const T = (v, l) => (v && typeof v === "object" && !Array.isArray(v) ? v[l] : v);

const VL_OUVRIR = [
  { js: "Object.keys(localStorage).filter(k => k.startsWith('dz_vl_brouillon')).forEach(k => localStorage.removeItem(k))" },
  { aller: "/vectorlab/" },
  { clic: "[data-carte], .carte, .doc-carte", texte: "Affiche à calques", attente: 3500 },
  { clic: "[data-onglet=\"calques\"]", attente: 600 },
  { js: "VL.zoomAjuster(); VL.etat.calqueActif = 'c2'; VL.rendre()", attente: 800 },
];
const PL_OUVRIR = [
  { js: "fetch('/api/photolab/espaces',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:1,actif:'essentiel',verrouille:false,modifs:{},perso:[]})}).then(r=>r.json())" },
  { js: "fetch('/api/photolab/executer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'file.closeAll',params:{}})}).then(r=>r.json())" },
  { aller: "/photolab/" },
  { texte: { fr: "Ouvrir depuis la Bibliothèque…", en: "Open from the Library…" }, contient: true, attente: 1800 },
  { saisir: "input.lib-recherche", valeur: "paysage", attente: 1500 },
  { texte: "paysage-demo.png", attente: 4500 },
];
const PROMPT = { fr: "un chat assis, illustration", en: "a sitting cat, illustration" };

const FICHES = [
  { id: "iacGo", zone: [70, 160, 832, 520], avant: [...VL_OUVRIR,
      { js: "VL.iaCalque.ouvrir('c2')", attente: 2500 },
      { saisir: "#iacPrompt", valeur: PROMPT }],
    cible: "#iacGo", chip: { fr: "Générer sur « Image »", en: "Generate on “Image”" },
    faire: [{ clic: "#iacGo", attente: 9000 }] },
  { id: "imDetourer", zone: [360, 160, 1080, 675], avant: [...VL_OUVRIR,
      { js: "VL.iaCalque.ouvrir('c2')", attente: 2500 },
      { saisir: "#iacPrompt", valeur: PROMPT },
      { clic: "#iacGo", attente: 9000 },
      { clic: "#iaCalqueDlg [data-act=\"fermer\"]", attente: 600 },
      { clic: "[data-onglet=\"image\"]", attente: 800 },
      { js: "const s = document.querySelector('#imDetourModele'); s.value = 'bria-rmbg'; s.dispatchEvent(new Event('change', {bubbles: true}))", attente: 1800 }],
    cible: "#imDetourer", chip: { fr: "Retirer le fond", en: "Remove the background" },
    faire: [{ clic: "#imDetourer", attente: 8000 }] },
  { id: "pl-calque-ia", zone: [0, 60, 1440, 840], avant: [...PL_OUVRIR],
    cible: "#pl-calque-ia", chip: { fr: "Nouveau calque IA…", en: "New AI layer…" },
    faire: [{ clic: "#pl-calque-ia", attente: 2500 },
      { saisir: ".pl-iac-prompt", valeur: PROMPT },
      { clic: ".pl-iacalque [data-act=\"lancer\"]", attente: 10000 },
      { clic: ".pl-iacalque [data-act=\"fermer\"]", attente: 800 }] },
  { id: "pl-iac-detourer", zone: [0, 60, 1440, 840], avant: [...PL_OUVRIR,
      { clic: "#pl-calque-ia", attente: 2500 },
      { saisir: ".pl-iac-prompt", valeur: PROMPT },
      { clic: ".pl-iacalque [data-act=\"lancer\"]", attente: 10000 },
      { js: "PL.actions['pl.calque.detourer']()", attente: 2500 },
      { js: "const s = document.querySelectorAll('.pl-iacalque select')[2]; s.value = 'bria-rmbg'; s.dispatchEvent(new Event('change', {bubbles: true}))", attente: 1800 }],
    t1sans: ".pl-iacalque",           // t1 : le calque à détourer, sans le panneau (caché le temps de la capture)
    cible: "#pl-iac-detourer", chip: { fr: "Retirer le fond", en: "Remove the background" },
    faire: [{ clic: "#pl-iac-detourer", attente: 10000 }, { clic: ".pl-iacalque [data-act=\"fermer\"]", attente: 800 }] },
];

async function centre(page, css, texte, lang, contient) {
  return page.evaluate((css, t, contient) => {
    const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    let el;
    if (t) {
      const n = (s) => (s || "").replace(/\s+/g, " ").trim();
      el = [...document.querySelectorAll("button, a, div, span, li, h3, h4, p")].filter(vis)
        .filter((e) => (contient ? n(e.innerText).includes(t) : n(e.innerText) === t))
        .sort((a, b) => a.getBoundingClientRect().width * a.getBoundingClientRect().height - b.getBoundingClientRect().width * b.getBoundingClientRect().height)[0];
    } else el = [...document.querySelectorAll(css)].find(vis);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return [r.x, r.y, r.width, r.height];
  }, css || "", texte ? T(texte, lang) : "", !!contient);
}

async function etape(page, e, lang) {
  if (e.aller) { await page.goto(BASE + e.aller, { waitUntil: "networkidle2", timeout: 45000 }); await pause(1500); }
  if (e.js) await page.evaluate(e.js);
  if (e.clic || e.texte) {
    const b = await centre(page, e.texte ? null : e.clic, e.texte, lang, e.contient);
    if (!b) throw new Error("introuvable : " + JSON.stringify(e.texte || e.clic));
    await page.mouse.click(b[0] + b[2] / 2, b[1] + b[3] / 2);
  }
  if (e.saisir) {
    const b = await centre(page, e.saisir, null, lang);
    if (!b) throw new Error("introuvable : " + e.saisir);
    await page.mouse.click(b[0] + b[2] / 2, b[1] + b[3] / 2);
    await page.keyboard.type(T(e.valeur, lang), { delay: 10 });
  }
  await pause(e.attente || 600);
}

async function geste(page, cible, chip) {
  await page.evaluate((cible, chip) => {
    const el = document.querySelector(cible);
    const r = el.getBoundingClientRect();
    const c = document.createElement("div");
    c.id = "__fiche_geste";
    c.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483647";
    const m = 6;
    c.innerHTML = `<div style="position:fixed;left:${r.x - m}px;top:${r.y - m}px;width:${r.width + 2 * m}px;height:${r.height + 2 * m}px;`
      + `border:4px solid #F5C451;border-radius:10px;box-shadow:0 0 0 4000px rgba(0,0,0,.35)"></div>`
      + `<div style="position:fixed;left:${Math.max(8, Math.min(innerWidth - 420, r.x))}px;top:${r.y > 90 ? r.y - m - 52 : r.y + r.height + m + 10}px;`
      + `background:#F5C451;color:#1F1512;font:700 26px/1.2 'Segoe UI',sans-serif;padding:8px 16px;border-radius:999px;white-space:nowrap">${chip}</div>`
      + `<svg style="position:fixed;left:${r.x + r.width / 2}px;top:${r.y + r.height / 2}px" width="40" height="52" viewBox="0 0 20 26">`
      + `<path d="M1 1 L1 20 L6 15 L10 24 L13 23 L9 14 L16 14 Z" fill="#fff" stroke="#000" stroke-width="1.4"/></svg>`;
    document.body.appendChild(c);
  }, cible, chip);
  await pause(300);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: "new",
    args: ["--force-color-profile=srgb", "--hide-scrollbars"] });
  try {
    for (const f of FICHES) {
      if (SEULES.length && !SEULES.includes(f.id)) continue;
      for (const lang of ["fr", "en"]) {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
        await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
        await page.evaluate((l) => { localStorage.setItem("dz_onboarded", "1"); localStorage.setItem("dz_lang", l); }, lang);
        for (const e of f.avant) await etape(page, e, lang);
        const [x, y, width, height] = f.zone;
        const clip = { x, y, width, height };
        const nom = (k) => path.join(OUT, `${f.id}.${lang}.t${k}.png`);
        if (f.t1sans) await page.evaluate((s) => document.querySelectorAll(s).forEach((e) => { e.dataset.ficheVis = e.style.visibility; e.style.visibility = "hidden"; }), f.t1sans);
        await page.screenshot({ path: nom(1), clip });
        if (f.t1sans) await page.evaluate((s) => document.querySelectorAll(s).forEach((e) => { e.style.visibility = e.dataset.ficheVis || ""; }), f.t1sans);
        await geste(page, f.cible, T(f.chip, lang));
        await page.screenshot({ path: nom(2), clip });
        await page.evaluate(() => document.getElementById("__fiche_geste").remove());
        for (const e of f.faire) await etape(page, e, lang);
        await page.screenshot({ path: nom(3), clip });
        await page.close();
        console.log("fiche", f.id, lang, "OK");
      }
    }
  } finally { await browser.close(); }
})().catch((e) => { console.error(e.message || e); process.exit(1); });
