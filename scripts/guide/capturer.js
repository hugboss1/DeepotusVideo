/* Captures des scènes animées du guide (skill guide-deepotus, t171).
 *
 * Lit un PLAN (docs/guide/src/scenes/plans/<lot>.json), pilote Chrome sans fenêtre sur un backend de PREUVE
 * (jamais le 8765 de l'utilisateur), prend chaque capture en FR puis en EN, et écrit pour chaque scène
 * docs/guide/src/scenes/<scene>/scene.json + <capture>.<lang>.webp. Les repères (curseur, surlignage, ancre des
 * bulles) ne sont JAMAIS saisis à la main : ils désignent un élément par son libellé (« texte:Coffre ») ou un
 * sélecteur (« css:#btn »), et leurs coordonnées sont mesurées dans la page au moment de la capture.
 *
 *   NODE_PATH=<dépôt principal>/scripts/qa/node_modules node scripts/guide/capturer.js <plan.json> [base] [scene…]
 *
 * Plan : {"base": "http://127.0.0.1:8799", "scenes": [{
 *   "scene": "reglages/coffre", "taille": [1440, 900], "clip": "css:main" (facultatif),
 *   "titre": {"fr","en"}, "legende": {"fr","en"},
 *   "avant": [étapes], "captures": [{"nom": "a", "etapes": [étapes]}],
 *   "temps": [{"capture": 0, "duree": 2.4, "curseur": "texte:X", "clic": true, "surligne": "texte:Y", "voile": true,
 *              "ancre": "texte:Z", "bulle": {"fr","en"}}] }]}
 * Étapes : {"aller": "/chemin"}, {"clic": ref}, {"saisir": [ref, "texte"]}, {"touche": "Escape"}, {"attente": ms},
 *          {"js": "code exécuté dans la page"}, {"defiler": ref}.
 */
const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");

const RACINE = path.resolve(__dirname, "..", "..");
const SCENES = path.join(RACINE, "docs", "guide", "src", "scenes");
const CHROME = ["C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(p => fs.existsSync(p));
const pause = ms => new Promise(r => setTimeout(r, ms));

/* Un repère : la boîte (x, y, l, h) de l'élément VISIBLE le plus petit dont le texte vaut exactement le libellé. */
let LANG = "fr";
/* Un repère peut valoir pour les deux langues ("texte:Coffre") ou par langue ({"fr": "texte:Coffre", "en": "texte:Vault"}). */
const R = ref => (ref && typeof ref === "object" && !Array.isArray(ref)) ? ref[LANG] : ref;

/* `dans` : rectangle [x, y, l, h] où chercher (la zone capturée) — hors de lui, un homonyme ne compte pas. */
async function boite(page, ref, dans) {
  ref = R(ref);
  return page.evaluate((ref, dans) => {
    const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
      const ok = r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && r.bottom > 0 && r.top < innerHeight;
      return ok && (!dans || (r.right > dans[0] && r.x < dans[0] + dans[2] && r.bottom > dans[1] && r.y < dans[1] + dans[3])); };
    let el = null;
    if (ref.startsWith("css:")) el = [...document.querySelectorAll(ref.slice(4))].find(vis) || null;
    else if (ref.startsWith("texte:") || ref.startsWith("contient:")) {
      const exact = ref.startsWith("texte:"), t = ref.slice(ref.indexOf(":") + 1).trim().toLowerCase();
      const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
      const cands = [...document.querySelectorAll("button, a, [role=button], label, h1, h2, h3, h4, summary, span, div, p, li, td, th, input, select, textarea")]
        .filter(vis).filter(e => {
          const v = norm(e.innerText || e.value || e.placeholder || e.getAttribute("aria-label") || e.title);
          return exact ? v === t : v.includes(t);
        });
      cands.sort((a, b) => { const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(); return ra.width * ra.height - rb.width * rb.height; });
      el = cands[0] || null;
    }
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return [r.x, r.y, r.width, r.height];
  }, ref, dans || null);
}

async function etape(page, e) {
  if (e.aller) { await page.goto(BASE + e.aller, { waitUntil: "networkidle2", timeout: 45000 }); await pause(900); }
  if (e.clic) { const b = await boite(page, e.clic); if (!b) throw new Error("introuvable : " + JSON.stringify(e.clic));
    await page.mouse.click(b[0] + b[2] / 2, b[1] + b[3] / 2); await pause(e.apres || 700); }
  if (e.saisir) { const b = await boite(page, e.saisir[0]); if (!b) throw new Error("introuvable : " + JSON.stringify(e.saisir[0]));
    await page.mouse.click(b[0] + b[2] / 2, b[1] + b[3] / 2); await page.keyboard.type(R(e.saisir[1]), { delay: 15 }); await pause(500); }
  if (e.touche) { await page.keyboard.press(e.touche); await pause(400); }
  if (e.defiler) { await page.evaluate(ref => { const css = ref.startsWith("css:") ? ref.slice(4) : null;
    const el = css ? document.querySelector(css) : [...document.querySelectorAll("h2,h3,h4,button,div,section,label,span")]
      .find(x => (x.innerText || "").trim().toLowerCase() === ref.slice(ref.indexOf(":") + 1).trim().toLowerCase());
    if (el) el.scrollIntoView({ block: "center" }); }, R(e.defiler)); await pause(500); }
  if (e.js) { await page.evaluate(e.js); await pause(500); }
  if (e.attente) await pause(e.attente);
}

let BASE = "http://127.0.0.1:8799";

async function scene(browser, s, lang) {
  LANG = lang;
  const [W, H] = s.taille || [1440, 900];
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.evaluate(l => { localStorage.setItem("dz_onboarded", "1"); localStorage.setItem("dz_lang", l); }, lang);
  await page.goto(BASE + (s.url || "/"), { waitUntil: "networkidle2", timeout: 45000 });
  // l'écran de démarrage (poulpe) couvre la page plusieurs secondes et INTERCEPTE les clics : on attend que le
  // point (40, 120) du rail appartienne vraiment au rail
  if (!s.url || s.url === "/") {
    await page.waitForFunction(() => { const a = document.querySelector("aside"); const e = document.elementFromPoint(40, 120);
      return a && e && a.contains(e); }, { timeout: 30000, polling: 250 });
  }
  await pause(1200);
  for (const e of s.avant || []) await etape(page, e);
  const dossier = path.join(SCENES, ...s.scene.split("/"));
  fs.mkdirSync(dossier, { recursive: true });
  const temps = JSON.parse(JSON.stringify(s.temps));
  let clip = null;
  for (let k = 0; k < s.captures.length; k++) {
    const c = s.captures[k];
    for (const e of c.etapes || []) await etape(page, e);
    await page.evaluate(() => document.getAnimations().forEach(a => { try { a.finish(); } catch (_) {} }));
    await pause(300);
    if (s.clip && !clip) { clip = await boite(page, s.clip); if (!clip) throw new Error("clip introuvable : " + s.clip);
      clip = clip.map(Math.round); }
    const box = clip ? { x: clip[0], y: clip[1], width: clip[2], height: clip[3] } : { x: 0, y: 0, width: W, height: H };
    await page.screenshot({ path: path.join(dossier, `${c.nom}.${lang}.webp`), type: "webp", quality: 88, clip: box });
    // les repères des temps qui montrent cette capture, mesurés MAINTENANT, ramenés au repère du clip
    for (const t of temps.filter(t => t.capture === k)) {
      for (const cle of ["curseur", "surligne", "ancre"]) {
        if (!t[cle] || Array.isArray(t[cle])) continue;
        const b = await boite(page, t[cle], [box.x, box.y, box.width, box.height]);
        if (!b) throw new Error(`${s.scene} [${lang}] repère introuvable : ${JSON.stringify(t[cle])}`);
        const x = b[0] - box.x, y = b[1] - box.y;
        if (cle === "curseur") t[cle] = [Math.round(x + b[2] / 2), Math.round(y + b[3] / 2)];
        else if (cle === "ancre") t[cle] = [Math.round(x + b[2] / 2), Math.round(y + b[3])];
        else { const m = 6; t[cle] = [Math.max(0, Math.round(x - m)), Math.max(0, Math.round(y - m)),
          Math.round(Math.min(b[2] + 2 * m, box.width - Math.max(0, x - m))), Math.round(Math.min(b[3] + 2 * m, box.height - Math.max(0, y - m)))]; }
      }
    }
  }
  await page.close();
  return { temps, taille: clip ? [clip[2], clip[3]] : [W, H] };
}

(async () => {
  const plan = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  BASE = process.argv[3] || plan.base || BASE;
  if (/:8765\b/.test(BASE)) throw new Error("jamais le 8765 de l'utilisateur : un backend de preuve");
  const seules = process.argv.slice(4);
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", protocolTimeout: 120000,
    args: ["--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
      "--force-color-profile=srgb", "--hide-scrollbars"] });
  try {
    for (const s of plan.scenes) {
      if (seules.length && !seules.includes(s.scene)) continue;
      const fr = await scene(browser, s, "fr"), en = await scene(browser, s, "en");
      const sortie = { titre: s.titre, legende: s.legende,
        captures: s.captures.map(c => ({ fr: `${c.nom}.fr.webp`, en: `${c.nom}.en.webp` })),
        taille: fr.taille, temps: fr.temps };
      if (JSON.stringify(en.temps) !== JSON.stringify(fr.temps) || JSON.stringify(en.taille) !== JSON.stringify(fr.taille)) {
        sortie.temps_en = en.temps; sortie.taille_en = en.taille;
      }
      fs.writeFileSync(path.join(SCENES, ...s.scene.split("/"), "scene.json"), JSON.stringify(sortie, null, 2) + "\n");
      console.log("scène", s.scene, "OK", fr.taille.join("×"));
    }
  } finally { await browser.close(); }
})().catch(e => { console.error(e.message || e); process.exit(1); });
