// t331 (A1 du lot Scenario, 29/10/2026) — la section « Blender ouvert » (frontend/shared/dz-blender-scene.js), JOUÉE sur
// un faux DOM (même faux DOM que passes_plan.test.mjs) :
//   état (pont prêt / exe absent : le message du serveur), cases (caméra, éclairage, blocking cochés, clés non),
//   « gratuit » affiché avant le clic, envoi (corps = {elements} SEULEMENT, jamais de code), refus (aucune case), 503 dit,
//   regard (image, légende, licences des assets importés), garder (corps {plan}, bouton grisé ensuite), retirer, et la
//   boîte des passes qui monte la section quand la boîte Blender est chargée.
// Lancer : node frontend/shared/qa/blender_scene.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-blender-scene.js", import.meta.url), "utf8");
const PASSES = readFileSync(new URL("../dz-passes-plan.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");
let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };
const ticks = async (k = 30) => { for (let i = 0; i < k; i++) await new Promise((r) => setImmediate(r)); };

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const FR = (cle, vars) => { let s = (D[cle] || {}).fr || cle; if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m)); return s; };

// ── un faux DOM minimal : éléments, attributs, classes, sélecteurs simples (.a, [x], [x='v'], tag, composés) ──
class Node {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parentNode = null;
    this._texte = ""; this.ec = {}; this.style = {}; this.checked = false; this.value = ""; this.muted = false; }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "style") this.style = { cssText: String(v) }; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; return c; }
  get textContent() { return this._texte + this.children.map((c) => c.textContent).join(""); }
  set textContent(t) { this._texte = String(t); this.children.forEach((c) => { c.parentNode = null; }); this.children = []; }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  dispatch(t, ev = {}) { (this.ec[t] || []).forEach((f) => f(Object.assign({ target: this, preventDefault() {}, stopPropagation() {} }, ev))); }
  click() { if (!this.hasAttribute("disabled")) this.dispatch("click"); }
  get classes() { return (this.attrs.class || "").split(/\s+/).filter(Boolean); }
  tous() { const out = []; const f = (e) => { e.children.forEach((c) => { out.push(c); f(c); }); }; f(this); return out; }
  querySelectorAll(sel) { return this.tous().filter((e) => correspond(e, sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
class Texte { constructor(t) { this.t = String(t); this.parentNode = null; this.children = []; }
  get textContent() { return this.t; } set textContent(v) { this.t = String(v); } tous() { return []; } }
function correspond(e, sel) {
  if (!(e instanceof Node)) return false;
  const re = /(\.[\w-]+)|(\[([\w-]+)(?:='([^']*)')?\])|^([a-z]+)/gi;
  let m, vu = false;
  while ((m = re.exec(sel))) {
    vu = true;
    if (m[1] && !e.classes.includes(m[1].slice(1))) return false;
    if (m[2] && (!e.hasAttribute(m[3]) || (m[4] != null && e.getAttribute(m[3]) !== m[4]))) return false;
    if (m[5] && e.tagName !== m[5].toUpperCase()) return false;
  }
  return vu;
}
const marque = (racine, m) => racine.querySelector(`[data-dz-blender='${m}']`);

function monde(routes, avecPasses = false) {
  const body = new Node("body");
  const appels = [], toasts = [];
  const document = {
    body, createElement: (t) => new Node(t), createElementNS: (_ns, t) => new Node(t), createTextNode: (t) => new Texte(t),
    addEventListener: () => {}, removeEventListener: () => {},
  };
  const ctx = {
    console, JSON, Promise, Error, Array, Object, String, Number, Math, document, location: { href: "/atelier/" },
    setTimeout: (f) => { setImmediate(f); return 1; }, dzT: FR, toast: (m) => toasts.push(m), encodeURIComponent,
    fetch: async (url, init = {}) => {
      appels.push({ url, methode: init.method || "GET", corps: init.body ? JSON.parse(init.body) : null });
      const f = routes[(init.method || "GET") + " " + url];
      const r = f ? f(init) : { status: 404, json: { detail: "inconnu" } };
      return { ok: r.status < 300, status: r.status, json: async () => r.json };
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  if (avecPasses) vm.runInContext(PASSES, ctx);
  return { ctx, body, appels, toasts, B: ctx.__dzBlenderScene };
}
const ETAT = () => ({ status: 200, json: { exe: { trouve: true, port: 9876 }, provenance: 0, installer: "Installez mcp-for-blender" } });

// ── 1. montée, état, cases, prix ──
{
  const w = monde({ "GET /api/blender/etat": ETAT });
  const hote = new Node("div");
  w.B.monter(hote, { shot: { id: "s1" }, numero: 2 });
  await ticks();
  ok("1a la section est posée avec son titre", marque(hote, "section") && hote.textContent.includes(FR("blenderscene.section.titre")));
  ok("1b état : pont prêt (port dit)", marque(hote, "etat").textContent === FR("blenderscene.etat.pret", { port: 9876 }),
     marque(hote, "etat").textContent);
  ok("1c caméra, éclairage, blocking cochés ; clés non",
     ["camera", "eclairage", "blocking"].every((k) => marque(hote, "element-" + k).checked) && !marque(hote, "element-cles").checked);
  ok("1d « gratuit » affiché avant tout clic", marque(hote, "prix").textContent === FR("blenderscene.section.gratuit"));
  ok("1e sans plan : rien n'est monté", w.B.monter(new Node("div"), {}) === null);
}

// ── 2. exe absent : le message du serveur ──
{
  const w = monde({ "GET /api/blender/etat": () => ({ status: 200, json: { exe: { trouve: false }, installer: "INSTALLER-ICI" } }) });
  const hote = new Node("div");
  w.B.monter(hote, { shot: { id: "s1" } });
  await ticks();
  ok("2a exe absent : le serveur dit quoi installer ; les boutons restent cliquables",
     marque(hote, "etat").textContent === "INSTALLER-ICI" && !marque(hote, "envoyer").hasAttribute("disabled"));
}

// ── 3. envoyer, refus, 503 ──
{
  let rep = { status: 200, json: { elements: ["camera", "eclairage", "blocking"], blocking: 3, cles: 0, camera: { focale_mm: 32.97 }, resume: {} } };
  const w = monde({ "GET /api/blender/etat": ETAT, "POST /api/blender/plan/s1/envoyer": () => rep });
  const hote = new Node("div");
  w.B.monter(hote, { shot: { id: "s1" }, toast: w.ctx.toast });
  await ticks();
  marque(hote, "element-cles").checked = true;
  marque(hote, "envoyer").click();
  await ticks();
  const a = w.appels.find((x) => x.url === "/api/blender/plan/s1/envoyer");
  ok("3a envoi : le corps ne porte QUE les éléments cochés",
     a && JSON.stringify(a.corps) === JSON.stringify({ elements: ["camera", "eclairage", "blocking", "cles"] }), a && JSON.stringify(a.corps));
  ok("3b le statut dit le blocking et la focale, un toast", marque(hote, "statut").textContent === FR("blenderscene.section.envoye", { n: 3, f: 33 })
     && w.toasts.includes(FR("blenderscene.section.envoye_toast")), marque(hote, "statut").textContent);
  ["camera", "eclairage", "blocking", "cles"].forEach((k) => { marque(hote, "element-" + k).checked = false; });
  const avant = w.appels.length;
  marque(hote, "envoyer").click();
  await ticks();
  ok("3c aucune case : refus dit, rien envoyé", w.appels.length === avant && marque(hote, "erreur").textContent === FR("blenderscene.section.aucun"));
  marque(hote, "element-camera").checked = true;
  rep = { status: 503, json: { detail: "Blender ne répond pas" } };
  marque(hote, "envoyer").click();
  await ticks();
  ok("3d 503 : le message du serveur est affiché, le bouton revient",
     marque(hote, "erreur").textContent === FR("blenderscene.section.ko", { msg: "Blender ne répond pas" })
     && !marque(hote, "envoyer").hasAttribute("disabled"));
}

// ── 4. regarder, garder, retirer ──
{
  const RID = "20261029-120000-abcd";
  const w = monde({
    "GET /api/blender/etat": ETAT,
    "POST /api/blender/regarder": () => ({ status: 200, json: { id: RID, url: "/api/blender/regard/" + RID,
      legende: "Through camera DZ_Camera.", licences: [{ id: "abc", titre: "Chaise", licence: "CC Attribution", auteur: "Ana" }] } }),
    ["POST /api/blender/regard/" + RID + "/garder"]: () => ({ status: 200, json: { nom: "blender_x.png", licence: "CC Attribution (Chaise — Ana)" } }),
    "POST /api/blender/nettoyer": () => ({ status: 200, json: { resume: { retires: 7 } } }),
  });
  const hote = new Node("div");
  w.B.monter(hote, { shot: { id: "s1" }, toast: w.ctx.toast });
  await ticks();
  marque(hote, "mode").value = "angles";
  marque(hote, "regarder").click();
  await ticks();
  const a = w.appels.find((x) => x.url === "/api/blender/regarder");
  ok("4a regarder : le mode choisi part", a && a.corps.mode === "angles", a && JSON.stringify(a.corps));
  ok("4b la capture, sa légende, les licences des assets importés",
     !marque(hote, "vue").hasAttribute("hidden") && marque(hote, "image").getAttribute("src").startsWith("/api/blender/regard/" + RID)
     && marque(hote, "legende").textContent.includes("DZ_Camera") && marque(hote, "licences").textContent.includes("CC Attribution (Ana)"),
     marque(hote, "licences").textContent);
  marque(hote, "garder").click();
  await ticks();
  const g = w.appels.find((x) => x.url.endsWith("/garder"));
  ok("4c garder : corps {plan}, statut avec la licence, bouton grisé",
     g && g.corps.plan === "s1" && marque(hote, "statut").textContent.includes("CC Attribution") && marque(hote, "garder").hasAttribute("disabled"));
  marque(hote, "retirer").click();
  await ticks();
  ok("4d retirer : le compte des objets DZ_ retirés", marque(hote, "statut").textContent === FR("blenderscene.section.retire", { n: 7 }));
}

// ── 5. la boîte des passes monte la section ──
{
  const w = monde({
    "GET /api/blender/etat": ETAT,
    "GET /api/passes/plan/s1": () => ({ status: 200, json: { shot_id: "s1", blender: { dispo: true, version: "5.2.2" }, scene: null, runs: [], job: null } }),
  }, true);
  w.ctx.__dzPassesPlan.ouvrir({ shot: { id: "s1" }, numero: 1 });
  await ticks();
  ok("5a la boîte « Passes Blender » contient la section « Blender ouvert »", !!marque(w.body, "section"));
}
// ── 7. t332 : l'aller-retour Plateau ↔ Blender ──
{
  const RID = "20261029-130000-beef";
  const PROP = { camera_nom: "DZ_Camera", keyframes: [{ t: 0 }, { t: 2 }], ecart_m: 0.4,
    avant: { focale_mm: 32.97, keyframes: 2 }, apres: { focale_mm: 50, keyframes: 2 } };
  const RET = { id: RID, date: "2026-10-29T13:00:00", camera_nom: "DZ_Camera", version: "5.2.0", bibliotheque: "blender_" + RID + ".png",
    cameras: [{ nom: "DZ_Camera", perspective: true, cles: 2 }, { nom: "Camera", perspective: true, cles: 0 }, { nom: "Ortho", perspective: false, cles: 0 }],
    objets: [{ nom: "DZ_Camera" }], proposition: PROP, blend_url: "/api/blender/retour/" + RID + "/blend",
    blend_nom: "blender_plan_" + RID + ".blend", vignette_url: "/api/blender/retour/" + RID + "/vignette" };
  let confirme = false;
  const w = monde({
    "GET /api/blender/etat": ETAT,
    "GET /api/blender/plan/s1/retours": () => ({ status: 200, json: { retours: [] } }),
    "POST /api/blender/plan/s1/aller": () => ({ status: 200, json: { camera: { focale_mm: 32.97 }, cles: 2, maquette: 3 } }),
    "POST /api/blender/plan/s1/reprendre": () => ({ status: 200, json: RET }),
    ["POST /api/blender/plan/s1/retour/" + RID + "/appliquer"]: (init) => {
      const c = JSON.parse(init.body);
      return { status: 200, json: { applique: !!c.confirmer, proposition: c.camera === "Camera"
        ? Object.assign({}, PROP, { keyframes: [], apres: { focale_mm: 50, keyframes: 0 } }) : PROP } };
    },
  });
  w.ctx.__dzDialogue = { confirmer: async () => confirme };
  const hote = new Node("div");
  w.B.monter(hote, { shot: { id: "s1" }, toast: w.ctx.toast });
  await ticks();
  ok("7a les deux boutons et « gratuit » avant le clic ; aucun retour encore : bloc caché",
     marque(hote, "aller").textContent === FR("blenderscene.ar.aller") && marque(hote, "reprendre").textContent === FR("blenderscene.ar.reprendre")
     && marque(hote, "ar-prix").textContent === FR("blenderscene.ar.gratuit") && marque(hote, "retour").hasAttribute("hidden"));
  marque(hote, "aller").click();
  await ticks();
  const a = w.appels.find((x) => x.url === "/api/blender/plan/s1/aller");
  ok("7b aller : corps vide, statut (focale, clés, maquette)", a && JSON.stringify(a.corps) === "{}"
     && marque(hote, "statut").textContent === FR("blenderscene.ar.envoye", { f: 33, k: 2, m: 3 }), marque(hote, "statut").textContent);
  marque(hote, "reprendre").click();
  await ticks();
  ok("7c reprendre : vignette, avant/après, caméras en perspective seulement, lien .blend",
     !marque(hote, "retour").hasAttribute("hidden") && marque(hote, "retour-image").getAttribute("src").startsWith(RET.vignette_url)
     && marque(hote, "retour-avant-apres").textContent === FR("blenderscene.ar.avant_apres", { fa: 33, fb: 50, ka: 2, kb: 2, d: 0.4 })
     && marque(hote, "retour-camera").children.length === 2 && marque(hote, "retour-blend").getAttribute("href") === RET.blend_url
     && marque(hote, "retour-resume").textContent.includes(RET.bibliotheque), marque(hote, "retour-avant-apres").textContent);
  const n0 = w.appels.length;
  marque(hote, "appliquer").click();
  await ticks();
  ok("7d appliquer refusé à la confirmation : rien n'est envoyé", w.appels.length === n0);
  marque(hote, "retour-camera").value = "Camera";
  marque(hote, "retour-camera").dispatch("change");
  await ticks();
  const p = w.appels[w.appels.length - 1];
  ok("7e une autre caméra : avant/après recalculé SANS confirmer", p.corps.camera === "Camera" && !("confirmer" in p.corps)
     && marque(hote, "retour-avant-apres").textContent.includes("2 → 0"), JSON.stringify(p.corps));
  confirme = true;
  marque(hote, "appliquer").click();
  await ticks();
  const q = w.appels[w.appels.length - 1];
  ok("7f confirmé : {camera, confirmer: true}, statut et toast", q.corps.confirmer === true && q.corps.camera === "Camera"
     && w.toasts.includes(FR("blenderscene.ar.applique_toast")), JSON.stringify(q.corps));
}
{
  const w = monde({ "GET /api/blender/etat": ETAT,
    "GET /api/blender/plan/s2/retours": () => ({ status: 200, json: { retours: [{ id: "20261029-130000-0000", cameras: [], objets: [],
      proposition: null, proposition_erreur: "aucune caméra", blend_url: "/b" }] } }) });
  const hote = new Node("div");
  w.B.monter(hote, { shot: { id: "s2" } });
  await ticks();
  ok("7g au montage : le dernier retour revient ; sans proposition, « Appliquer » est grisé et la raison dite",
     !marque(hote, "retour").hasAttribute("hidden") && marque(hote, "appliquer").hasAttribute("disabled")
     && marque(hote, "retour-avant-apres").textContent === FR("blenderscene.ar.sans_proposition", { msg: "aucune caméra" }));
}
ok("6 aucun innerHTML dans le code", !/innerHTML/.test(SRC.replace(/\/\*[\s\S]*?\*\//g, "")));

if (echecs.length) { console.log(echecs.map((e) => "FAIL " + e).join("\n")); console.log(`${n - echecs.length}/${n}`); process.exit(1); }
console.log(`OK ${n}/${n}`);
