// t334 (A4 du lot Scenario, 29/10/2026) — la boîte « Passes Blender » (frontend/shared/dz-passes-plan.js), JOUÉE sur un
// faux DOM (aucune correspondance de texte dans le source) :
//   vide (plan sans scène → « Ouvrir le Plateau 3D »), Blender absent (le message du serveur dit quoi installer, le
//   bouton reste cliquable), versions (5 vignettes du dernier run, séquence = vidéos, choix d'un run précédent),
//   lancement (corps {sequence, passes} cochées, suivi du job jusqu'à « fini », toast, rechargement), refus (aucune
//   passe cochée ; 503 du serveur dit), annulation (POST …/annuler), vignettes des cartes (bouton act-passes posé une
//   seule fois après « Revue du plan », bande des passes du dernier run, clic → la boîte du plan).
// Lancer : node frontend/shared/qa/passes_plan.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-passes-plan.js", import.meta.url), "utf8");
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
const marque = (racine, m) => racine.querySelector(`[data-dz-passes='${m}']`);

function monde(routes) {
  const body = new Node("body");
  const docEc = {};
  const appels = [], toasts = [], ouverts = [];
  const document = {
    body,
    createElement: (t) => new Node(t),
    createElementNS: (_ns, t) => new Node(t),
    createTextNode: (t) => new Texte(t),
    addEventListener: (t, f) => { (docEc[t] = docEc[t] || []).push(f); },
    removeEventListener: (t, f) => { docEc[t] = (docEc[t] || []).filter((x) => x !== f); },
  };
  const ctx = {
    console, JSON, Promise, Error, Array, Object, String, Number, Math,
    document, location: { href: "/atelier/" },
    setTimeout: (f) => { setImmediate(f); return 1; },
    dzT: FR,
    toast: (m, err) => toasts.push([m, !!err]),
    open: (u) => ouverts.push(u),
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
  return { ctx, body, appels, toasts, ouverts, docEc, P: ctx.__dzPassesPlan };
}

const RUN = (i, seq = false) => ({ run: `20261029-1200${i}0-000${i}`, shot_id: "s1", date: `2026-10-29T12:00:${i}0`,
  sequence: seq, images: seq ? 19 : 1, largeur: seq ? 640 : 960, hauteur: seq ? 360 : 540, blender: "5.2.2", palette: "palette",
  profondeur: { proche_m: 3.26, loin_m: 12.15 },
  passes: Object.fromEntries(["clay", "look", "profondeur", "normales", "masques"].map((p) =>
    [p, { fichiers: [`${p}_000.png`], video: seq ? `${p}.mp4` : undefined, bibliotheque: `passe_s1_${p}.png` }])) });
const ETAT = (extra = {}) => Object.assign({ shot_id: "s1", blender: { dispo: true, version: "5.2.2" },
  scene: { id: "sc", nom: "plan 1", instances: 3, aspect: "16:9", keyframes: 2, anime: true, duree_s: 1.5 },
  runs: [RUN(2), RUN(1, true)], job: null, bornes: { fps: 12, images_max: 48 } }, extra);

// ── 1. plan sans scène ──
{
  const w = monde({ "GET /api/passes/plan/s1": () => ({ status: 200, json: ETAT({ scene: null, runs: [] }) }) });
  w.P.ouvrir({ shot: { id: "s1" }, numero: 1 });
  await ticks();
  const vide = marque(w.body, "vide");
  ok("1a sans scène : l'état vide explique (Plateau 3D) et la section Rendre est cachée",
     vide && !vide.hasAttribute("hidden") && vide.textContent.includes(FR("passesplan.vide.titre"))
     && marque(w.body, "sec-rendre").hasAttribute("hidden"));
  marque(w.body, "plateau").click();
  ok("1b « Ouvrir le Plateau 3D » mène au Plateau du plan", w.ctx.location.href === "/plateau/?shot=s1", w.ctx.location.href);
  ok("1c aucune version : la phrase le dit", !marque(w.body, "aucun").hasAttribute("hidden"));
}

// ── 2. Blender absent, versions, lancement suivi ──
{
  let etat = ETAT({ blender: { dispo: false, raison: "absent", installer: "Blender est introuvable : installez Blender 4.2 (blender.org)" } });
  let suivis = 0;
  const w = monde({
    "GET /api/passes/plan/s1": () => ({ status: 200, json: etat }),
    "POST /api/passes/plan/s1": () => ({ status: 202, json: { job: { id: "pb_1", statut: "attente", progression: 0, total: 5 } } }),
    "GET /api/passes/job/pb_1": () => (++suivis < 3
      ? { status: 200, json: { id: "pb_1", statut: "rendu", progression: 40, images: 2, total: 5, etape: "look" } }
      : { status: 200, json: { id: "pb_1", statut: "fini", progression: 100, images: 5, total: 5 } }),
  });
  let apres = 0;
  w.P.ouvrir({ shot: { id: "s1" }, numero: 4, toast: w.ctx.toast, apres: () => apres++ });
  await ticks();
  const bl = marque(w.body, "blender");
  ok("2a Blender absent : le message du SERVEUR (quoi installer) est montré, le bouton reste cliquable",
     bl.textContent.includes("blender.org") && !marque(w.body, "rendre").hasAttribute("disabled"), bl.textContent);
  ok("2b le prix dit « gratuit » avant le clic", marque(w.body, "prix").textContent === FR("passesplan.rendre.gratuit"));
  const tuiles = marque(w.body, "grille").children;
  ok("2c cinq vignettes du dernier run, dans l'ordre clay, look, profondeur, normales, masques",
     tuiles.length === 5 && tuiles.map((t) => t.getAttribute("data-dz-passes")).join() ===
       "tuile-clay,tuile-look,tuile-profondeur,tuile-normales,tuile-masques"
     && tuiles[2].children[0].getAttribute("src") === "/api/passes/fichier/s1/20261029-120020-0002/profondeur_000.png");
  tuiles[0].click();
  ok("2d un clic sur une vignette l'ouvre en grand", w.ouverts[0] === "/api/passes/fichier/s1/20261029-120020-0002/clay_000.png", w.ouverts);
  const runs = marque(w.body, "runs");
  ok("2e deux runs : le choix des rendus précédents est visible", !runs.hasAttribute("hidden") && runs.children.length === 2);
  runs.value = "1"; runs.dispatch("change");
  ok("2f le run précédent (séquence) montre des VIDÉOS et son résumé",
     marque(w.body, "grille").children[0].children[0].tagName === "VIDEO"
     && marque(w.body, "resume").textContent.includes("19"), marque(w.body, "resume").textContent);
  ok("2g la séquence est proposée (caméra animée) : la case est active",
     !marque(w.body, "sequence").hasAttribute("disabled"));
  marque(w.body, "passe-normales").checked = false;
  marque(w.body, "sequence").checked = true;
  etat = ETAT({ runs: [RUN(3)] });
  marque(w.body, "rendre").click();
  await ticks(80);
  const post = w.appels.find((a) => a.methode === "POST");
  ok("2h « Rendre les passes » : POST {sequence, passes cochées}", post && post.corps.sequence === true
     && post.corps.passes.join() === "clay,look,profondeur,masques", post && JSON.stringify(post.corps));
  ok("2i le job est suivi jusqu'à « fini » : toast, rechargement, rappel de l'hôte",
     suivis >= 3 && w.toasts.some((t) => t[0] === FR("passesplan.rendre.fini")) && apres === 1
     && marque(w.body, "grille").children.length === 5 && marque(w.body, "progres").hasAttribute("hidden"),
     JSON.stringify({ suivis, toasts: w.toasts, apres }));
  ok("2j après la fin, Annuler est caché et Rendre de nouveau actif",
     marque(w.body, "annuler").hasAttribute("hidden") && !marque(w.body, "rendre").hasAttribute("disabled"));
  // aucune passe cochée
  ["clay", "look", "profondeur", "normales", "masques"].forEach((p) => { marque(w.body, "passe-" + p).checked = false; });
  const avant = w.appels.length;
  marque(w.body, "rendre").click();
  await ticks();
  ok("2k aucune passe cochée : refus dit, rien envoyé", w.appels.length === avant
     && marque(w.body, "erreur").textContent === FR("passesplan.rendre.aucune"));
  // Échap ferme
  w.docEc.keydown.forEach((f) => f({ key: "Escape", preventDefault() {}, stopPropagation() {} }));
  ok("2l Échap ferme la boîte", !w.body.querySelector("[data-dz-passes='voile']"));
}

// ── 3. caméra fixe, 503 du serveur, annulation ──
{
  const w = monde({
    "GET /api/passes/plan/s1": () => ({ status: 200, json: ETAT({ scene: { id: "sc", nom: "p", instances: 1, aspect: "9:16", keyframes: 1, anime: false, duree_s: 0 }, runs: [] }) }),
    "POST /api/passes/plan/s1": () => ({ status: 503, json: { detail: "Blender est introuvable : installez Blender 4.2" } }),
  });
  w.P.ouvrir({ shot: { id: "s1" }, numero: 2 });
  await ticks();
  ok("3a caméra fixe : la séquence est grisée et décochée", marque(w.body, "sequence").hasAttribute("disabled")
     && marque(w.body, "scene").textContent === FR("passesplan.rendre.scene_fixe", { nom: "p", n: 1, aspect: "9:16", d: 0 }));
  marque(w.body, "rendre").click();
  await ticks();
  ok("3b 503 : le message du serveur est dit, le bouton redevient actif",
     marque(w.body, "erreur").textContent.includes("installez Blender 4.2") && !marque(w.body, "rendre").hasAttribute("disabled"));
}
{
  let annule = 0, suivis = 0;
  const w = monde({
    "GET /api/passes/plan/s1": () => ({ status: 200, json: ETAT({ job: suivis ? null : { id: "pb_2", statut: "rendu", progression: 20, images: 1, total: 5, etape: "clay" } }) }),
    "GET /api/passes/job/pb_2": () => { suivis++; return { status: 200, json: { id: "pb_2", statut: annule ? "annule" : "rendu", progression: 20, images: 1, total: 5, etape: "clay" } }; },
    "POST /api/passes/job/pb_2/annuler": () => { annule++; return { status: 200, json: { annule: true } }; },
  });
  w.P.ouvrir({ shot: { id: "s1" }, numero: 1, toast: w.ctx.toast });
  await ticks(10);
  ok("3c un job DÉJÀ en cours à l'ouverture est repris : progression et Annuler visibles",
     !marque(w.body, "progres").hasAttribute("hidden") && !marque(w.body, "annuler").hasAttribute("hidden")
     && marque(w.body, "progres-texte").textContent === FR("passesplan.rendre.progres", { k: 1, n: 5, passe: FR("passesplan.passe.clay") }),
     marque(w.body, "progres-texte").textContent);
  marque(w.body, "annuler").click();
  await ticks(60);
  ok("3d Annuler : POST …/annuler, le job finit « annule », toast dit", annule === 1
     && w.toasts.some((t) => t[0] === FR("passesplan.rendre.annule")), JSON.stringify(w.toasts));
}

// ── 4. les cartes de l'Atelier : bouton et bande ──
{
  const w = monde({ "GET /api/passes/chapitre/c1": () => ({ status: 200, json: { plans: { s1: RUN(2) } } }),
                    "GET /api/passes/plan/s1": () => ({ status: 200, json: ETAT() }) });
  const liste = new Node("div");
  for (const id of ["s1", "s2"]) {
    const carte = liste.appendChild(new Node("div"));
    carte.setAttribute("class", "shot-card"); carte.setAttribute("data-id", id);
    const thumb = carte.appendChild(new Node("div")); thumb.setAttribute("class", "thumb");
    const act = thumb.appendChild(new Node("div")); act.setAttribute("class", "entity-actions");
    const rev = act.appendChild(new Node("button")); rev.setAttribute("class", "btn ghost act-revue");
  }
  await w.P.vignettes(liste, "c1");
  await w.P.vignettes(liste, "c1");
  const b = liste.querySelectorAll(".act-passes");
  ok("4a un bouton « Passes Blender » par carte, posé UNE fois après « Revue du plan », libellé et glyphe",
     b.length === 2 && b[0].parentNode.children.indexOf(b[0]) === 1
     && b[0].getAttribute("aria-label") === FR("passesplan.carte.bouton")
     && b[0].children[0].children[0].getAttribute("href") === "/shared/icons/dz-icons.svg#dz-nav-panneau-calques");
  const bandes = liste.querySelectorAll("[data-dz-passes='bande']");
  ok("4b la bande des passes du dernier run sous la vignette du plan 1 seulement (5 miniatures), une seule fois",
     bandes.length === 1 && bandes[0].parentNode.parentNode.getAttribute("data-id") === "s1"
     && bandes[0].children.length === 5);
  bandes[0].click();
  await ticks();
  ok("4c un clic sur la bande ouvre la boîte du plan", !!w.body.querySelector("[data-dz-passes='voile']")
     && w.appels.some((a) => a.url === "/api/passes/plan/s1"));
}

ok("5 aucun innerHTML dans le code de la boîte", !/innerHTML/.test(SRC.replace(/\/\*[\s\S]*?\*\//g, "")));

if (echecs.length) { console.log(echecs.map((e) => "FAIL " + e).join("\n")); console.log(`${n - echecs.length}/${n}`); process.exit(1); }
console.log(`OK ${n}/${n}`);
