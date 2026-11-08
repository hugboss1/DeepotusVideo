// Plateau, lot 1 (tâche 4) — la galerie jouée avec son filtre « Tous / Plateaux ». Les VRAIES fonctions de core.js
// (galDecksList, galDrawDecks, galSyncFiltre, galEnsure, GAL_SKELETON) sont extraites du fichier livré et jouées dans un
// `vm` devant un DOM minimal ; seuls le réseau (jsonNamed) et les dehors de la galerie sont des doublures.
// Lancer : node frontend/cardforge/qa/galerie_plateau.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };

const SRC = readFileSync(new URL("../js/core.js", import.meta.url), "utf8").replace(/\r\n/g, "\n");
function fonction(nom) {
  const k = SRC.indexOf("function " + nom + "(");
  if (k < 0) throw new Error("fonction absente : " + nom);
  const i = SRC.indexOf("{", k);
  let prof = 0;
  for (let j = i; j < SRC.length; j++) {
    if (SRC[j] === "{") prof++;
    else if (SRC[j] === "}" && --prof === 0) return SRC.slice(k, j + 1);
  }
  throw new Error("accolades : " + nom);
}
const morceau = (re) => { const m = SRC.match(re); if (!m) throw new Error("morceau absent : " + re); return m[0]; };

/* ── un DOM minimal ── */
const registre = {};
let boutonsFiltre = [];
class FE {
  constructor(tag) {
    this.tag = tag; this.className = ""; this.dataset = {}; this.children = []; this.attrs = {}; this.listeners = {};
    this._text = ""; this.disabled = false;
    const me = this;
    this.classList = {
      toggle(c, on) { const s = new Set(me.className.split(/\s+/).filter(Boolean)); if (on) s.add(c); else s.delete(c); me.className = [...s].join(" "); },
      contains(c) { return me.className.split(/\s+/).includes(c); },
    };
  }
  set textContent(t) { this._text = String(t); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(h) {
    this.children = []; this._text = "";
    if (!h) return;
    for (const m of h.matchAll(/<(\w+)[^>]*\bid="(\w+)"/g)) registre[m[2]] = registre[m[2]] || new FE(m[1]);
    boutonsFiltre = [...h.matchAll(/data-filtre="(\w+)"/g)].map((m) => { const b = new FE("button"); b.dataset.filtre = m[1]; return b; });
  }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  setAttribute(k, v) { this.attrs[k] = v; }
  closest(sel) { return sel === "button[data-filtre]" && this.dataset.filtre ? this : null; }
  clic(cible) { (this.listeners.click || []).forEach((f) => f({ target: cible || this })); }
}
const tous = (e, f, out = []) => { if (f(e)) out.push(e); e.children.forEach((c) => tous(c, f, out)); return out; };

/* ── le réseau : une doublure pilotée ── */
const MIXTE = [
  { id: "deck_00000001", name: "Plat", created: "2026-01-01T00:00:00Z", updated: "2026-01-02T00:00:00Z", categorie: "plateau" },
  { id: "deck_00000002", name: "Simple", created: "2026-01-01T00:00:00Z", updated: "2026-01-03T00:00:00Z", categorie: "" },
  { id: "deck_00000003", name: "Autre", created: "2026-01-01T00:00:00Z", updated: "2026-01-04T00:00:00Z" },
];
const PLATEAUX = MIXTE.slice(0, 1);
const appels = [];
let reponse = (path) => (path.includes("categorie=plateau") ? { decks: PLATEAUX, total: 1 } : { decks: MIXTE, total: 3 });
const jsonNamed = async (m, path) => { appels.push(path); return reponse(path); };

const code = [
  "const GAL_DECKS_MAX = 24;", "let GAL_DECKS = null, GAL_DECKS_REQ = null;", "let GAL_DECKS_TOTAL = 0;",
  morceau(/const GAL_SKELETON = \(\) =>[\s\S]*?'<\/div><\/div>';/),
  ...["galEl", "galNote", "galDate", "galMsg", "galDecksList", "galSyncFiltre", "galDrawDecks", "galEnsure"].map(fonction),
  morceau(/let GAL_FILTRE = "tous";/),
  "globalThis.__t = { galEnsure, etat: () => ({ GAL_DECKS, GAL_FILTRE, GAL_DECKS_TOTAL }) };",
].join("\n");
const ctx = vm.createContext({
  console, Promise, Date, isFinite, Math, Array, String, Number,
  hasDOM: true, OFFLINE: false, DOC: { id: "deck_00000001" }, DID_RE: /^deck_[0-9a-f]{8}$/,
  dzT: (k, v) => "⟦" + k + (v ? JSON.stringify(v) : "") + "⟧", icone: () => "", jsonNamed,
  isPlain: (v) => v !== null && typeof v === "object" && !Array.isArray(v),
  closeGallery() {}, galImport() {}, galImages() {}, galDuplicate() {}, galSaveToggle() {}, galSaveModel() {}, galOpenDeck() {},
  document: {
    createElement: (t) => new FE(t), body: new FE("body"),
    querySelector: (s) => registre[s.replace(/^#/, "")] || null,
    querySelectorAll: (s) => (s.startsWith("#galFiltre") ? boutonsFiltre : []),
  },
});
ctx.el = (s) => ctx.document.querySelector(s);
vm.runInContext(code, ctx, { filename: "core.js(galerie)" });
const T = ctx.__t;
const vide = () => new Promise((r) => setTimeout(r, 0));
const badges = () => tous(registre.galDecks, (e) => e.className === "cf-gal-badge").length;
const lignes = () => registre.galDecks.children.filter((c) => c.tag === "button").length;

T.galEnsure();
const gf = registre.galFiltre;
ok("0.1 le squelette crée le filtre et ses deux boutons", !!gf && boutonsFiltre.length === 2 && !!registre.galDecks);
const bPlat = boutonsFiltre.find((b) => b.dataset.filtre === "plateau");
const bTous = boutonsFiltre.find((b) => b.dataset.filtre === "tous");

/* 1. clic sur « Plateaux » alors que GAL_DECKS est NUL : ne lève pas, demande ?categorie=plateau */
ok("1.0 départ : GAL_DECKS est nul", T.etat().GAL_DECKS === null);
let leve = null;
try { gf.clic(bPlat); } catch (e) { leve = e; }
await vide(); await vide();
ok("1.1 le clic avec GAL_DECKS nul ne lève pas", leve === null, leve && leve.message);
ok("1.2 la requête porte categorie=plateau", appels.length === 1 && /\/cards\/decks\?limit=24&categorie=plateau$/.test(appels[0]), appels.join());
ok("1.3 une ligne, avec son badge", lignes() === 1 && badges() === 1, lignes() + "/" + badges());
ok("1.4 le bouton Plateaux est pressé, l'autre non", bPlat.attrs["aria-pressed"] === "true" && bTous.attrs["aria-pressed"] === "false");

/* 2. « Tous » : requête sans categorie, liste mixte, badge sur le seul plateau */
gf.clic(bTous); await vide(); await vide();
ok("2.1 la requête n'a pas de categorie", !/categorie/.test(appels[1]) && /limit=24$/.test(appels[1]), appels[1]);
ok("2.2 trois lignes, UN badge (le plateau seul)", lignes() === 3 && badges() === 1, lignes() + "/" + badges());
ok("2.3 le badge porte la clé « Plateau »", tous(registre.galDecks, (e) => e.className === "cf-gal-badge")[0].textContent === "⟦cartes.plateau.badge⟧");

/* 3. résultat filtré vide : le message dédié ; « Tous » vide garde le message d'origine */
reponse = () => ({ decks: [], total: 0 });
gf.clic(bPlat); await vide(); await vide();
ok("3.1 filtre vide : « aucun plateau »", registre.galDecks.textContent === "⟦cartes.plateau.aucun⟧", registre.galDecks.textContent);
gf.clic(bTous); await vide(); await vide();
ok("3.2 « Tous » vide : pas le message des plateaux", registre.galDecks.textContent !== "⟦cartes.plateau.aucun⟧");

/* 4. le total est celui du SERVEUR pour le filtre (1 plateau montré sur 5) */
reponse = () => ({ decks: PLATEAUX, total: 5 });
gf.clic(bPlat); await vide(); await vide();
ok("4.1 la note de total vient du serveur", /gal_total/.test(registre.galDecks.textContent) && /"total":5/.test(registre.galDecks.textContent), registre.galDecks.textContent);

/* 5. réponse d'un filtre abandonné : écartée */
let lacher;
const attente = new Promise((r) => { lacher = r; });
reponse = (path) => (path.includes("categorie=plateau") ? attente : { decks: MIXTE, total: 3 });
gf.clic(bPlat);                       // demande lente (plateaux)
gf.clic(bTous);                       // l'utilisateur change d'avis
await vide(); await vide();
lacher({ decks: PLATEAUX, total: 1 });
await vide(); await vide(); await vide();
ok("5.1 la liste finale est celle de « Tous »", lignes() === 3, lignes());

console.log(`${n - echecs.length}/${n} vérifications`);
if (echecs.length) { echecs.forEach((e) => console.log("  KO  " + e)); process.exit(1); }
console.log("OK");
