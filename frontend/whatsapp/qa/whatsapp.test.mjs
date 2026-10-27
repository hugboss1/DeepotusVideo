// qa/whatsapp.test.mjs — la page WhatsApp autonome (t311 tâche 7) jouée sous node : faux DOM, faux fetch, vrai
// dictionnaire assemblé (frontend/shared/dz-i18n-dico.js). Lancé par backend/tests/test_whatsapp_page.py.
//   node frontend/whatsapp/qa/whatsapp.test.mjs   -> « whatsapp : ok » (code 0) ou les ÉCHECS (code 1)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ICI = dirname(fileURLToPath(import.meta.url));
const PAGE = join(ICI, "..");
const SHARED = join(ICI, "..", "..", "shared");
let ko = 0, nb = 0;
function check(label, cond, detail = "") {
  nb++;
  if (!cond) { ko++; console.error("ECHEC :", label, typeof detail === "string" ? detail : JSON.stringify(detail)); }
}

// ── faux DOM ─────────────────────────────────────────────────────────────────────────────────────────────────────────
class Noeud {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase(); this.enfants = []; this.attrs = {}; this.ecoutes = {}; this._t = "";
    this.parent = null; this.value = ""; this.disabled = false; this.checked = false; this.hidden = false;
    this.className = ""; this._html = ""; this.style = {}; this.type = ""; this.placeholder = ""; this.title = "";
    const cl = new Set(); const me = this;
    this.classList = { add: (...c) => c.forEach((x) => cl.add(x)), remove: (...c) => c.forEach((x) => cl.delete(x)),
      toggle: (c, v) => { const on = v === undefined ? !cl.has(c) : !!v; if (on) cl.add(c); else cl.delete(c); return on; },
      contains: (c) => cl.has(c) || String(me.className).split(/\s+/).includes(c) };
  }
  get textContent() { return this._t + this.enfants.map((e) => e.textContent).join(""); }
  set textContent(v) { this._t = String(v); this.enfants = []; this._html = ""; }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = String(v); this.enfants = []; this._t = ""; }
  get firstChild() { return this.enfants[0] || null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  appendChild(e) { if (e.parent) e.remove(); e.parent = this; this.enfants.push(e); return e; }
  removeChild(e) { this.enfants = this.enfants.filter((x) => x !== e); e.parent = null; return e; }
  remove() { if (this.parent) this.parent.removeChild(this); }
  addEventListener(t, f) { (this.ecoutes[t] = this.ecoutes[t] || []).push(f); }
  removeEventListener(t, f) { this.ecoutes[t] = (this.ecoutes[t] || []).filter((g) => g !== f); }
  focus() {}
  select() {}
  scrollIntoView() {}
  declencher(t, ev = {}) { ev.target = ev.target || this; ev.preventDefault = () => {}; ev.stopPropagation = () => {};
    (this.ecoutes[t] || []).forEach((f) => f(ev)); }
}
function tous(n, pred, out = []) { if (pred(n)) out.push(n); n.enfants.forEach((e) => tous(e, pred, out)); return out; }
function attr(racine, k, v) { return tous(racine, (n) => n.getAttribute(k) !== null && (v === undefined || n.getAttribute(k) === String(v))); }
function un(racine, k, v) { return attr(racine, k, v)[0] || null; }
function visible(n) { for (let x = n; x; x = x.parent) if (x.hidden) return false; return true; }

const docEcoutes = {};
const body = new Noeud("body");
globalThis.window = globalThis;
globalThis.document = {
  body, visibilityState: "visible", documentElement: new Noeud("html"), readyState: "complete",
  createElement: (t) => new Noeud(t),
  querySelector: () => null,
  addEventListener: (t, f) => { (docEcoutes[t] = docEcoutes[t] || []).push(f); },
  removeEventListener: (t, f) => { docEcoutes[t] = (docEcoutes[t] || []).filter((g) => g !== f); },
};
function docEvenement(t) { (docEcoutes[t] || []).forEach((f) => f({ type: t })); }
const evenements = [];
window.dispatchEvent = (e) => { evenements.push(e); return true; };
window.addEventListener = () => {};
globalThis.CustomEvent = function (t, o) { this.type = t; this.detail = o && o.detail; };
const icones = new Set();
window.dzIcone = (cle) => { icones.add(cle); return '<svg data-cle="' + cle + '"></svg>'; };

// minuteries : setTimeout relevé, jamais lancé tout seul (la minuterie de 30 s, les délais d'abandon des appels, ceux
// de dz-plafonds) ; le banc déclenche lui-même ce qu'il veut
const minuteries = new Map(); let nMin = 0;
globalThis.setTimeout = (f, ms) => { nMin++; minuteries.set(nMin, { f, ms }); return nMin; };
globalThis.clearTimeout = (id) => { minuteries.delete(id); };
globalThis.setInterval = () => { throw new Error("setInterval interdit : minuterie par setTimeout"); };
globalThis.clearInterval = () => {};
function declencher(ms) { for (const [id, m] of [...minuteries]) if (m.ms === ms) { minuteries.delete(id); m.f(); } }
function differe() { let resoudre; const promesse = new Promise((r) => { resoudre = r; }); return { promesse, resoudre }; }

// console : aucune trace de texte de message
const traces = [];
for (const k of ["log", "info", "warn", "error", "debug"]) {
  const orig = console[k].bind(console);
  console[k] = (...a) => { traces.push(a.map(String).join(" ")); if (k === "error" && String(a[0]).startsWith("ECHEC")) orig(...a); };
}

// dictionnaire réel, dzT minimal (français) qui relève les clés absentes
vm.runInThisContext(readFileSync(join(SHARED, "dz-i18n-dico.js"), "utf8"));
const D = window.DZ_I18N; const absentes = new Set();
window.dzT = (cle, vars) => {
  const e = D[cle]; if (!e) { absentes.add(cle); return cle; }
  let s = e.fr; if (vars) s = s.replace(/\{(\w+)\}/g, (m, n) => (vars[n] != null ? String(vars[n]) : m)); return s;
};
window.dzLang = () => "fr";
const T = window.dzT;

// ── faux fetch ───────────────────────────────────────────────────────────────────────────────────────────────────────
let appels = []; let routes = {};
function rep(status, data) {
  return new Response(JSON.stringify(data === undefined ? {} : data), { status, headers: { "Content-Type": "application/json" } });
}
globalThis.fetch = window.fetch = async (url, o = {}) => {
  const u = String(url); const m = (o.method || "GET").toUpperCase();
  let corps = null; try { corps = o.body ? JSON.parse(o.body) : null; } catch (e) { corps = o.body; }
  const h = new Headers(o.headers || {});
  appels.push({ url: u, m, corps, plafond: h.get("X-DZ-Plafond") });
  const chemin = u.split("?")[0];
  for (const cle of [m + " " + u, m + " " + chemin]) {
    if (cle in routes) {
      const r = routes[cle]; const p = typeof r === "function" ? r(corps, h, u, o.signal) : r;
      const v = await (p && typeof p.then === "function" ? new Promise((res, rej) => {
        if (o.signal) o.signal.addEventListener("abort", () => rej(new DOMException("abandon", "AbortError")));
        p.then(res, rej);
      }) : p);
      return rep(v[0], v[1]);
    }
  }
  return rep(404, { detail: "inconnu " + m + " " + chemin });
};
function posts(chemin) { return appels.filter((a) => a.m === "POST" && a.url.split("?")[0] === chemin); }
async function attendre(n = 12) { for (let i = 0; i < n; i++) await new Promise((r) => setImmediate(r)); }

for (const f of ["whatsapp.js", "onglets-conversations.js", "onglets-gestion.js"]) {
  vm.runInThisContext(readFileSync(join(PAGE, f), "utf8"), { filename: f });
}
const W = window.__dzWhatsapp;
W.DELAI_MS = 29999;      // délai d'abandon des lectures, reconnaissable (la minuterie fait 30000)
check("0.1 window.__dzWhatsapp exposé", W && typeof W.demarrer === "function");

// ── données ──────────────────────────────────────────────────────────────────────────────────────────────────────────
const CID = "c1", EID = "e1", Q = "?espace=" + EID;
const ESPACES = { espaces: [{ id: EID, nom: "Boulangerie", actif: true, archive: false }, { id: "e2", nom: "Autre", actif: false, archive: false }], actif: EID };
function comptes(posee = true, relie = true) {
  return { espace: EID, plateformes: { whatsapp: { cle_plate: { nom: "KAPSO_API_KEY", posee } } },
    comptes: [{ id: CID, espace_id: EID, plateforme: "whatsapp", libelle: "WhatsApp", champs: [
      { nom: "WHATSAPP_PHONE_ID", secret: false, valeur: relie ? "pid1" : "" },
      { nom: "WHATSAPP_NUMERO", secret: false, valeur: relie ? "+33 1 23 45 67 89" : "" }] },
      { id: "cx", espace_id: EID, plateforme: "x", libelle: "X", champs: [] }] };
}
const CONVS = [
  { id: "k1", identite: "tel:33600000001", nom: "Léa", dernier_entrant: "2026-10-27T09:00:00+00:00", fenetre_ouverte: true, stop: false },
  { id: "k2", identite: "tel:33600000002", nom: "Marc", dernier_entrant: "2026-10-20T09:00:00+00:00", fenetre_ouverte: false, stop: false },
  { id: "k3", identite: "tel:33600000003", nom: "Zoé", dernier_entrant: null, fenetre_ouverte: false, stop: true },
  { id: "k4", identite: "bsuid:ABC", nom: null, dernier_entrant: "2026-10-27T08:00:00+00:00", fenetre_ouverte: true, stop: false },
];
const BROUILLONS = {
  "tel:33600000001": { etat: "attente", carte: { genre: "reponse_whatsapp", arguments: { texte: "Bonjour, nous ouvrons à 8 h." } }, cree_le: "2026-10-27T09:01:00+00:00", auto_jour: {} },
  "tel:33600000002": { carte: null, auto_jour: {}, traite_jusqu_a: "2026-10-20T09:00:00+00:00" },
  "tel:33600000099": { etat: "humain", carte: null, raison: "argent", cree_le: "2026-10-27T08:01:00+00:00" },
};
const ETAT = { accords: { "tel:33600000001": { date: "2026-10-01T00:00:00+00:00", source: "entrant" } },
  stops: { "tel:33600000003": "2026-10-02T00:00:00+00:00" }, desinscrits_marketing: { "tel:33600000002": "2026-10-03T00:00:00+00:00" },
  alias: { "bsuid:ABC": "tel:33600000099", "tel:33600000099": "bsuid:ABC" },
  compteur: { [new Date().toISOString().slice(0, 7)]: { sortants: 12, entrants: 30, service: 9 } },
  journal: [{ quand: "2026-10-26T10:00:00+00:00", sens: "sortant", identite: "tel:33600000002", type: "modele", categorie: "marketing", statut: "failed", id: "w1" },
    { quand: "2026-10-26T11:00:00+00:00", sens: "sortant", identite: "tel:33600000001", type: "texte", categorie: null, statut: "sent", id: "w2" }],
  plafond_mois: 1000, marche_defaut: "33", agent: { actif: true, mode: "brouillon" } };
const MESSAGES = { messages: [
  { id: "m3", identite: "tel:33600000001", sens: "sortant", type: "text", texte: "Avec plaisir", quand: "2026-10-27T09:05:00+00:00", statut: "read" },
  { id: "m2", identite: "tel:33600000001", sens: "entrant", type: "image", texte: null, quand: "2026-10-27T09:02:00+00:00", statut: null, media_id: "MED1" },
  { id: "m1", identite: "tel:33600000001", sens: "entrant", type: "document", texte: null, quand: "2026-10-27T09:01:00+00:00", statut: null, media_id: "DOC1" },
  { id: "m0", identite: "tel:33600000002", sens: "entrant", type: "text", texte: "Autre contact", quand: "2026-10-27T09:00:00+00:00", statut: null },
], suivant: null };
const MODELES = [
  { nom: "rappel_rdv", langue: "fr", categorie: "utility", parametres: "nommes", n_parametres: 2, noms_parametres: ["prenom", "heure"],
    statut: "approved", composants: { entete: "text", entete_variable: true, boutons: [{ index: 0, type: "quick_reply", parametre: false }, { index: 1, type: "url", parametre: false }] } },
  { nom: "promo", langue: "fr", categorie: "marketing", parametres: "positionnels", n_parametres: 1, noms_parametres: ["1"],
    statut: "approved", composants: { entete: "image", entete_variable: false, boutons: [] } },
];
MODELES.push({ nom: "trop_long", langue: "fr", categorie: "utility", parametres: "nommes", n_parametres: 1, noms_parametres: ["x".repeat(61)],
  statut: "approved", composants: { entete: null, entete_variable: false, boutons: [] } });
const MODELES_TOUS = MODELES.filter((m) => m.nom !== "trop_long").concat([{ nom: "vieux", langue: "fr", categorie: "marketing", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "rejected", composants: { entete: null, entete_variable: false, boutons: [] } },
  { nom: "attente", langue: "en", categorie: "utility", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "pending", composants: { entete: null, entete_variable: false, boutons: [] } }]);
const B = "/api/whatsapp/" + CID;
function routesBase(o = {}) {
  return {
    "GET /api/espaces": [200, ESPACES],
    "GET /api/comptes": [200, comptes(o.posee !== false, o.relie !== false)],
    ["GET " + B + "/conversations"]: [200, CONVS],
    ["GET " + B + "/brouillons"]: [200, BROUILLONS],
    ["GET " + B + "/etat"]: [200, ETAT],
    ["POST " + B + "/relire"]: [200, MESSAGES],
    ["GET " + B + "/modeles"]: (c, h, u) => [200, u.includes("tous=1") ? MODELES_TOUS : MODELES],
    ["POST " + B + "/envoyer"]: [200, { id: "wamid.1", statut: "accepted", devis: 0.01 }],
    ["POST " + B + "/brouillons/decider"]: [200, { envoi: { id: "wamid.2" }, brouillon: { etat: "envoye" } }],
    ["POST " + B + "/brouillons/rediger"]: [200, { etat: null, carte: null, motif: "sans_cle" }],
    ["POST " + B + "/fil"]: [200, { ok: true }],
    ["POST " + B + "/accords"]: [200, { ok: true }],
    ["POST " + B + "/stop"]: [200, { ok: true }],
    ["POST " + B + "/stop/lever"]: [200, { ok: true }],
    "GET /api/cost/pricing": [200, { whatsapp_meta_usd: { "33": { marketing: 0.08, utility: 0.03, authentication: 0.03, service: 0 },
      "1": { marketing: 0.025, utility: 0.004, authentication: 0.004, service: 0 } }, autre: 1 }],
    "POST /api/cost/pricing": (c) => [200, { whatsapp_meta_usd: c.whatsapp_meta_usd }],
  };
}
async function monter(o = {}) {
  appels = []; routes = Object.assign(routesBase(o), o.routes || {});
  const racine = new Noeud("main"); body.enfants = []; body.appendChild(racine);
  await W.demarrer(racine); await attendre();
  return racine;
}
const texteErreur = (r) => { const e = un(r, "data-dz-wa-erreur"); return e ? e.textContent : ""; };
async function ouvrirConv(r, identite) { const c = un(r, "data-dz-wa-conv", identite); c.declencher("click"); await attendre(); return c; }

// ── [1] en-tête et états vides ───────────────────────────────────────────────────────────────────────────────────────
let r = await monter({ posee: false });
check("1.1 sans clé Kapso : l'état vide « clé » est montré", un(r, "data-dz-wa-vide", "cle") && visible(un(r, "data-dz-wa-vide", "cle")));
check("1.2 sans clé Kapso : aucune conversation demandée", !appels.some((a) => a.url.includes("/conversations")));
check("1.3 la clé n'est jamais montrée (ni son nom technique)", !r.textContent.includes("KAPSO_API_KEY"));
r = await monter({ relie: false });
const vn = un(r, "data-dz-wa-vide", "numero");
check("1.4 aucun numéro relié : état vide « numéro » expliqué", vn && visible(vn) && vn.textContent.includes(T("whatsapp.vide.numero_titre")));
const allerA = un(r, "data-dz-wa-aller", "assistant");
check("1.5 lien vers l'assistant d'espace", !!allerA);
evenements.length = 0; allerA.declencher("click");
check("1.6 l'assistant ouvre Réglages (deepotus:navigate)", evenements.some((e) => e.type === "deepotus:navigate" && e.detail && e.detail.view === "settings"), evenements);
r = await monter();
const selE = un(r, "data-dz-wa-espace"), selN = un(r, "data-dz-wa-numero");
check("1.7 sélecteur d'espace rempli (actif choisi)", selE && selE.value === EID && selE.enfants.length === 2, selE && selE.enfants.length);
check("1.8 sélecteur de numéro : les comptes whatsapp reliés seulement", selN && selN.value === CID && selN.enfants.length === 1
  && selN.textContent.includes("+33 1 23 45 67 89"), selN && selN.textContent);
check("1.9 les routes /whatsapp portent ?espace=", appels.filter((a) => a.url.startsWith(B)).every((a) => a.url.includes("espace=" + EID)), appels.map((a) => a.url));
check("1.10 cinq onglets", ["conversations", "modeles", "contacts", "sante", "prix"].every((o) => un(r, "data-dz-wa-onglet", o)));

// ── [2] la liste des conversations ───────────────────────────────────────────────────────────────────────────────────
const conv = (id) => un(r, "data-dz-wa-conv", id);
const pastille = (id, p) => !!un(conv(id), "data-dz-wa-pastille", p);
check("2.1 quatre conversations", attr(r, "data-dz-wa-conv").length === 4);
check("2.2 fenêtre ouverte / fermée", pastille("tel:33600000001", "ouverte") && pastille("tel:33600000002", "fermee"));
check("2.3 STOP", pastille("tel:33600000003", "stop") && !pastille("tel:33600000001", "stop"));
check("2.4 brouillon en attente", pastille("tel:33600000001", "brouillon"));
check("2.5 entrée sans etat (traite_jusqu_a seul) : aucun brouillon", !pastille("tel:33600000002", "brouillon") && !pastille("tel:33600000002", "humain"));
check("2.6 « à reprendre » (humain) trouvé par l'alias bsuid -> tel", pastille("bsuid:ABC", "humain"));
check("2.7 nom du contact par textContent", conv("tel:33600000001").textContent.includes("Léa"));

// ── [3] le fil ───────────────────────────────────────────────────────────────────────────────────────────────────────
await ouvrirConv(r, "tel:33600000001");
const fil = un(r, "data-dz-wa-fil");
const bulles = attr(fil, "data-dz-wa-bulle");
check("3.1 POST relire (pas le GET messages)", posts(B + "/relire").length >= 1 && !appels.some((a) => a.url.includes("/messages")));
check("3.2 les bulles du contact seulement, dans l'ordre", bulles.length === 3 && bulles[0].getAttribute("data-dz-wa-bulle") === "entrant"
  && bulles[2].getAttribute("data-dz-wa-bulle") === "sortant" && !fil.textContent.includes("Autre contact"), bulles.length);
check("3.3 statut lu traduit", un(fil, "data-dz-wa-statut", "read") && un(fil, "data-dz-wa-statut", "read").textContent === T("whatsapp.statut.read"));
const img = un(fil, "data-dz-wa-media", "image");
check("3.4 image depuis la route média", img && img.tagName === "IMG" && img.getAttribute("src") === B + "/medias/MED1" + Q, img && img.attrs);
const lien = un(fil, "data-dz-wa-media", "lien");
check("3.5 autre média : lien de téléchargement", lien && lien.tagName === "A" && lien.getAttribute("href") === B + "/medias/DOC1" + Q && lien.hasAttribute("download"));
check("3.6 heure affichée", /\d{1,2}[:h]\d{2}/.test(bulles[2].textContent), bulles[2].textContent);

// ── [4] la saisie : fenêtre ouverte, boutons ─────────────────────────────────────────────────────────────────────────
check("4.1 fenêtre ouverte : saisie libre présente", !!un(r, "data-dz-wa-texte") && !un(r, "data-dz-wa-bandeau", "modeles"));
const ajouter = un(r, "data-dz-wa-bouton-ajouter");
for (let i = 0; i < 4; i++) { ajouter.declencher("click"); await attendre(2); }
check("4.2 au plus trois boutons", attr(r, "data-dz-wa-bouton-titre").length === 3, attr(r, "data-dz-wa-bouton-titre").length);
check("4.3 « Ajouter un bouton » grisé à trois", un(r, "data-dz-wa-bouton-ajouter").disabled === true);
check("4.4 validation : quatre boutons refusés", W.validerBoutons(["a", "b", "c", "d"]) === "whatsapp.saisie.trop_de_boutons");
check("4.5 validation : titre de 21 caractères refusé", W.validerBoutons(["x".repeat(21)]) === "whatsapp.saisie.titre_long");
check("4.6 validation : titres en double refusés", W.validerBoutons(["Oui", "Oui"]) === "whatsapp.saisie.titres_doubles");
check("4.7 validation : 1 à 3 titres de 20 au plus acceptés", W.validerBoutons(["Oui", "Non", "x".repeat(20)]) === null);
const titres = attr(r, "data-dz-wa-bouton-titre");
un(r, "data-dz-wa-texte").value = "Votre rendez-vous ?";
titres[0].value = "x".repeat(21); titres[0].declencher("input"); await attendre(2);
const cpt = attr(r, "data-dz-wa-compteur")[0];
check("4.8 compteur de caractères du titre", cpt && cpt.textContent.includes("21") && cpt.textContent.includes("20"), cpt && cpt.textContent);
appels = [];
un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("4.9 titre > 20 : rien n'est envoyé, message affiché", posts(B + "/envoyer").length === 0 && texteErreur(r) === T("whatsapp.saisie.titre_long"), texteErreur(r));
titres[0].value = "Oui"; titres[1].value = "Non"; titres[2].value = "";
un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
const env = posts(B + "/envoyer")[0];
check("4.10 envoi à boutons au format exact (titres vides ignorés)", env && JSON.stringify(env.corps) === JSON.stringify(
  { identite: "tel:33600000001", envoi: { type: "boutons", texte: "Votre rendez-vous ?", boutons: ["Oui", "Non"] } }), env && env.corps);
check("4.11 après l'envoi la saisie est vidée", un(r, "data-dz-wa-texte").value === "" && attr(r, "data-dz-wa-bouton-titre").length === 0);
un(r, "data-dz-wa-texte").value = "Simple"; appels = [];
un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("4.12 envoi texte au format exact", JSON.stringify(posts(B + "/envoyer")[0]?.corps) === JSON.stringify({ identite: "tel:33600000001", envoi: { type: "texte", texte: "Simple" } }));

// ── [5] le brouillon de l'agent ──────────────────────────────────────────────────────────────────────────────────────
const carte = un(r, "data-dz-wa-brouillon", "attente");
const zt = un(r, "data-dz-wa-brouillon-texte");
check("5.1 carte du brouillon avec le texte modifiable", carte && zt && zt.value === "Bonjour, nous ouvrons à 8 h.", zt && zt.value);
zt.value = "Bonjour Léa, nous ouvrons à 8 h."; appels = [];
un(r, "data-dz-wa-decider", "envoyer").declencher("click"); await attendre();
const dec = posts(B + "/brouillons/decider")[0];
check("5.2 « Envoyer » appelle decider avec le texte modifié", dec && JSON.stringify(dec.corps) === JSON.stringify(
  { identite: "tel:33600000001", decision: "envoyer", texte: "Bonjour Léa, nous ouvrons à 8 h." }) && dec.url.includes(Q), dec);
check("5.3 les brouillons sont relus après la décision", appels.some((a) => a.m === "GET" && a.url.startsWith(B + "/brouillons")));
appels = [];
un(r, "data-dz-wa-decider", "rejeter").declencher("click"); await attendre();
check("5.4 « Rejeter »", JSON.stringify(posts(B + "/brouillons/decider")[0]?.corps) === JSON.stringify({ identite: "tel:33600000001", decision: "rejeter" }));
routes["POST " + B + "/brouillons/decider"] = [409, { detail: { message: "déjà en cours", code: "occupee" } }];
un(r, "data-dz-wa-decider", "envoyer").declencher("click"); await attendre();
check("5.5 409 occupee lisible", texteErreur(r) === T("whatsapp.refus.occupee"), texteErreur(r));
appels = [];
un(r, "data-dz-wa-rediger").declencher("click"); await attendre();
check("5.6 « Faire rédiger » : POST rediger {identite, langue}", JSON.stringify(posts(B + "/brouillons/rediger")[0]?.corps) === JSON.stringify({ identite: "tel:33600000001", langue: "fr" }));
check("5.7 motif sans_cle lisible", un(r, "data-dz-wa-info") && un(r, "data-dz-wa-info").textContent === T("whatsapp.motif.sans_cle"), un(r, "data-dz-wa-info")?.textContent);
for (const m of ["sans_cle", "plafond", "stop", "occupee", "sans_entrant", "moteur", "max_tours", "sans_carte", "declencheur", "carte"]) {
  check("5.8 motif " + m + " traduit", !!D["whatsapp.motif." + m]);
}
appels = [];
un(r, "data-dz-wa-fil-action", "prendre").declencher("click"); await attendre();
check("5.9 « Prendre le fil »", JSON.stringify(posts(B + "/fil")[0]?.corps) === JSON.stringify({ identite: "tel:33600000001", action: "prendre" }));
un(r, "data-dz-wa-fil-action", "rendre").declencher("click"); await attendre();
check("5.10 « Rendre le fil »", JSON.stringify(posts(B + "/fil")[1]?.corps) === JSON.stringify({ identite: "tel:33600000001", action: "rendre" }));

// ── [6] refus 409 et 402 sans dz-plafonds ────────────────────────────────────────────────────────────────────────────
for (const code of ["accord", "stop", "fenetre", "marketing", "plafond", "consentement", "prix", "bsuid_authentification", "occupee"]) {
  check("6.0 refus " + code + " traduit", !!D["whatsapp.refus." + code]);
}
routes["POST " + B + "/envoyer"] = [409, { detail: { message: "contact en STOP", code: "stop" } }];
un(r, "data-dz-wa-texte").value = "Encore"; un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("6.1 409 code stop : le message STOP", texteErreur(r) === T("whatsapp.refus.stop"), texteErreur(r));
routes["POST " + B + "/envoyer"] = [409, { detail: { message: "raison inconnue du serveur", code: "neuf" } }];
un(r, "data-dz-wa-texte").value = "Encore"; un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("6.2 409 code inconnu : le message du serveur", texteErreur(r).includes("raison inconnue du serveur"), texteErreur(r));
routes["POST " + B + "/envoyer"] = [402, { detail: { dz_plafond: { motif: "global", categorie: "whatsapp", message: "Plafond du mois atteint (whatsapp)" } } }];
un(r, "data-dz-wa-texte").value = "Encore"; un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("6.3 402 sans dz-plafonds : le message du plafond", texteErreur(r).includes("Plafond du mois atteint"), texteErreur(r));
routes["POST " + B + "/envoyer"] = [402, { detail: "Annulé : plafond" }];
un(r, "data-dz-wa-texte").value = "Encore"; un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("6.4 402 rendu par dz-plafonds (détail chaîne) affiché", texteErreur(r).includes("Annulé : plafond"), texteErreur(r));
routes["POST " + B + "/envoyer"] = [502, { detail: { message: "Kapso indisponible", code: "fournisseur" } }];
un(r, "data-dz-wa-texte").value = "Encore"; un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
check("6.5 502 : message du fournisseur", texteErreur(r).includes("Kapso indisponible"), texteErreur(r));
check("6.6 la saisie est gardée après un refus", un(r, "data-dz-wa-texte").value === "Encore");

// ── [7] fenêtre fermée, envoi de modèle en deux temps ────────────────────────────────────────────────────────────────
r = await monter();
await ouvrirConv(r, "tel:33600000002");
check("7.1 fenêtre fermée : saisie libre absente", !un(r, "data-dz-wa-texte") && !un(r, "data-dz-wa-bouton-ajouter"));
check("7.2 fenêtre fermée : bandeau « modèles seulement »", un(r, "data-dz-wa-bandeau", "modeles") && un(r, "data-dz-wa-bandeau", "modeles").textContent.includes(T("whatsapp.saisie.fenetre_fermee")));
un(r, "data-dz-wa-modele-ouvrir").declencher("click"); await attendre();
const choix = un(r, "data-dz-wa-modele-choix");
check("7.3 temps 1 : les modèles approuvés", choix && choix.enfants.length === 2 && appels.some((a) => a.url.startsWith(B + "/modeles") && !a.url.includes("tous=1")));
choix.value = "rappel_rdv|fr"; choix.declencher("change");
un(r, "data-dz-wa-modele-suivant").declencher("click"); await attendre();
check("7.4 paramètres nommés -> champs nommés", un(r, "data-dz-wa-param", "prenom") && un(r, "data-dz-wa-param", "heure") && !un(r, "data-dz-wa-param", "1"));
check("7.5 en-tête texte variable -> un champ d'en-tête", un(r, "data-dz-wa-entete", "text"));
check("7.6 payload pour le bouton de réponse rapide seulement", un(r, "data-dz-wa-payload", "0") && !un(r, "data-dz-wa-payload", "1"));
un(r, "data-dz-wa-param", "prenom").value = "Léa"; un(r, "data-dz-wa-param", "heure").value = "10 h";
un(r, "data-dz-wa-entete", "text").value = "Rappel"; un(r, "data-dz-wa-payload", "0").value = "CONFIRMER";
appels = [];
un(r, "data-dz-wa-modele-envoyer").declencher("click"); await attendre();
const em = posts(B + "/envoyer")[0];
check("7.7 envoi de modèle nommé au format exact", em && JSON.stringify(em.corps) === JSON.stringify({ identite: "tel:33600000002", envoi: {
  type: "modele", nom: "rappel_rdv", langue: "fr", parametres: { prenom: "Léa", heure: "10 h" },
  entete: { type: "text", texte: "Rappel" }, boutons: [{ index: 0, payload: "CONFIRMER" }] } }), em && em.corps);
un(r, "data-dz-wa-modele-ouvrir").declencher("click"); await attendre();
un(r, "data-dz-wa-modele-choix").value = "promo|fr"; un(r, "data-dz-wa-modele-choix").declencher("change");
un(r, "data-dz-wa-modele-suivant").declencher("click"); await attendre();
check("7.8 positionnel -> champ 1 ; en-tête image -> identifiant de média", un(r, "data-dz-wa-param", "1") && un(r, "data-dz-wa-entete", "image"));
appels = [];
un(r, "data-dz-wa-modele-envoyer").declencher("click"); await attendre();
check("7.9 paramètre vide : rien n'est envoyé", posts(B + "/envoyer").length === 0 && texteErreur(r) === T("whatsapp.modele.parametre_vide"), texteErreur(r));
un(r, "data-dz-wa-param", "1").value = "-20 %"; un(r, "data-dz-wa-entete", "image").value = "MEDIA42";
un(r, "data-dz-wa-modele-envoyer").declencher("click"); await attendre();
check("7.10 positionnel : liste ; en-tête média", JSON.stringify(posts(B + "/envoyer")[0]?.corps.envoi) === JSON.stringify({
  type: "modele", nom: "promo", langue: "fr", parametres: ["-20 %"], entete: { type: "image", media_id: "MEDIA42" } }), posts(B + "/envoyer")[0]?.corps);
await ouvrirConv(r, "tel:33600000003");
check("7.11 contact en STOP : ni saisie ni modèle, bandeau STOP", !un(r, "data-dz-wa-texte") && !un(r, "data-dz-wa-modele-ouvrir") && un(r, "data-dz-wa-bandeau", "stop"));
await ouvrirConv(r, "bsuid:ABC");
check("7.12 brouillon humain : carte « à reprendre », pas d'envoi direct", un(r, "data-dz-wa-brouillon", "humain") && !un(r, "data-dz-wa-decider", "envoyer") && un(r, "data-dz-wa-decider", "rejeter"));

// ── [8] rafraîchissement : 30 s, seulement onglet visible ────────────────────────────────────────────────────────────
const actifs = () => [...minuteries.values()].filter((i) => i.ms === 30000);
// tirer : la minuterie de 30 s part (elle quitte la file comme un vrai setTimeout échu)
function tirer() { for (const [id, m] of minuteries) if (m.ms === 30000) { minuteries.delete(id); return m.f; } return async () => {}; }
check("8.1 une minuterie de 30 s", actifs().length === 1, [...minuteries.values()].map((i) => i.ms));
appels = []; await tirer()(); await attendre();
check("8.2 le tic relit conversations, brouillons et le fil", appels.some((a) => a.url.startsWith(B + "/conversations")) && appels.some((a) => a.url.startsWith(B + "/brouillons")) && posts(B + "/relire").length === 1);
const tic = actifs()[0].f;
document.visibilityState = "hidden"; docEvenement("visibilitychange"); await attendre();
check("8.3 caché : la minuterie est arrêtée", actifs().length === 0);
appels = []; await tic(); await attendre();
check("8.4 caché : un tic attardé ne lit rien", appels.length === 0, appels.map((a) => a.url));
document.visibilityState = "visible"; docEvenement("visibilitychange"); await attendre();
check("8.5 visible : relu tout de suite et minuterie reposée", actifs().length === 1 && appels.some((a) => a.url.startsWith(B + "/conversations")));
{ // tic lent : jamais deux tics en parallèle, minuterie reprogrammée APRÈS la fin du tic
  const d = differe(); routes["GET " + B + "/conversations"] = () => d.promesse;
  const tour = tirer(); appels = [];
  const p1 = tour(); await attendre();
  check("8.6 pendant un tic lent : aucune minuterie en attente", actifs().length === 0);
  const p2 = tour(); await attendre();
  check("8.7 un second tic pendant le premier ne relit rien", appels.filter((a) => a.url.startsWith(B + "/conversations")).length === 1, appels.map((a) => a.url));
  d.resoudre([200, CONVS]); await p1; await p2; await attendre();
  check("8.8 tic fini : une seule minuterie reprogrammée", actifs().length === 1);
  routes["GET " + B + "/conversations"] = [200, CONVS];
}
{ // la fenêtre se ferme puis un STOP arrive pendant qu'on regarde le contact : la saisie change, la page dit pourquoi
  await ouvrirConv(r, "tel:33600000001");
  check("8.9 fenêtre ouverte au départ", !!un(r, "data-dz-wa-texte"));
  routes["GET " + B + "/conversations"] = [200, CONVS.map((c) => c.identite === "tel:33600000001" ? Object.assign({}, c, { fenetre_ouverte: false }) : c)];
  await tirer()(); await attendre();
  check("8.10 fenêtre fermée en cours de route : saisie retirée et message", !un(r, "data-dz-wa-texte") && un(r, "data-dz-wa-info").textContent === T("whatsapp.saisie.fenetre_vient_de_fermer"), un(r, "data-dz-wa-info").textContent);
  routes["GET " + B + "/conversations"] = [200, CONVS.map((c) => c.identite === "tel:33600000001" ? Object.assign({}, c, { fenetre_ouverte: false, stop: true }) : c)];
  await tirer()(); await attendre();
  check("8.11 STOP arrivé : bandeau et message", un(r, "data-dz-wa-bandeau", "stop") && un(r, "data-dz-wa-info").textContent === T("whatsapp.saisie.devenu_stop"));
  routes["GET " + B + "/conversations"] = [200, CONVS];
  await tirer()(); await attendre();
  W.effacer();
  appels = []; await tirer()(); await attendre();
  check("8.12 un tic sans changement ne dit rien", un(r, "data-dz-wa-info").textContent === "");
}

// ── [9] Modèles, Contacts, Santé ─────────────────────────────────────────────────────────────────────────────────────
un(r, "data-dz-wa-onglet", "modeles").declencher("click"); await attendre();
check("9.1 Modèles : tous les statuts (tous=1)", appels.some((a) => a.url.includes("/modeles") && a.url.includes("tous=1")) && attr(r, "data-dz-wa-modele-ligne").length === 4);
check("9.2 statut et catégorie traduits", un(un(r, "data-dz-wa-modele-ligne", "vieux"), "data-dz-wa-modele-statut").textContent === T("whatsapp.modele_statut.rejected")
  && un(r, "data-dz-wa-modele-ligne", "rappel_rdv").textContent.includes(T("whatsapp.categorie.utility")));
check("9.2b la minuterie ne tourne que sur Conversations", actifs().length === 0);
un(r, "data-dz-wa-onglet", "contacts").declencher("click"); await attendre();
check("9.3 Contacts : accords, STOP et désinscrits depuis GET etat", un(r, "data-dz-wa-accords").textContent.includes("tel:33600000001")
  && un(r, "data-dz-wa-stop-ligne", "tel:33600000003") && un(r, "data-dz-wa-desinscrits").textContent.includes("tel:33600000002"));
un(r, "data-dz-wa-accord-identite").value = "+33 6 12 34 56 78"; un(r, "data-dz-wa-accord-source").value = "formulaire"; appels = [];
un(r, "data-dz-wa-accord-ajouter").declencher("click"); await attendre();
check("9.4 accord saisi : identité normalisée et source", JSON.stringify(posts(B + "/accords")[0]?.corps) === JSON.stringify({ identite: "tel:33612345678", source: "formulaire" }));
un(r, "data-dz-wa-accord-identite").value = "tel:33600000005"; un(r, "data-dz-wa-accord-source").value = "  "; appels = [];
un(r, "data-dz-wa-accord-ajouter").declencher("click"); await attendre();
check("9.5 accord sans source : refusé avant l'envoi", posts(B + "/accords").length === 0 && texteErreur(r) === T("whatsapp.contacts.source_exigee"), texteErreur(r));
const ligneStop = un(r, "data-dz-wa-stop-ligne", "tel:33600000003");
const lever = un(ligneStop, "data-dz-wa-lever"), src = un(ligneStop, "data-dz-wa-lever-source");
check("9.6 lever un STOP : grisé sans source", lever.disabled === true);
src.value = "appel du 27/10"; src.declencher("input"); await attendre(2);
check("9.7 avec une source : permis", lever.disabled === false);
appels = []; lever.declencher("click"); await attendre();
check("9.8 POST stop/lever {identite, source}", JSON.stringify(posts(B + "/stop/lever")[0]?.corps) === JSON.stringify({ identite: "tel:33600000003", source: "appel du 27/10" }));
window.__dzDialogue = { confirmer: async () => true };     // le dialogue maison confirme (jamais de confirm natif)
un(r, "data-dz-wa-stop-identite").value = "tel:33600000007"; appels = [];
un(r, "data-dz-wa-stop-poser").declencher("click"); await attendre();
check("9.9b sans dialogue maison, rien n'est confirmé", await W.confirmer.call(null, "x").then(() => true) && (delete window.__dzDialogue, (await W.confirmer("x")) === false));
window.__dzDialogue = { confirmer: async () => true };
check("9.9 poser un STOP", JSON.stringify(posts(B + "/stop")[0]?.corps) === JSON.stringify({ identite: "tel:33600000007" }));
un(r, "data-dz-wa-onglet", "sante").declencher("click"); await attendre();
const sante = (k) => (un(r, "data-dz-wa-sante", k) || { textContent: "" }).textContent;
check("9.10 Santé : compteurs du mois contre le plafond", sante("sortants").includes("12") && sante("entrants").includes("30") && sante("service").includes("9")
  && sante("total").includes("42") && sante("total").includes("1000"), [sante("sortants"), sante("total")]);
check("9.11 Santé : échecs de livraison du journal", attr(un(r, "data-dz-wa-echecs"), "data-dz-wa-echec").length === 1);
check("9.12 Santé : désinscrits et modèles refusés", un(r, "data-dz-wa-sante", "desinscrits").textContent.includes("1") && un(r, "data-dz-wa-refuses").textContent.includes("vieux"));

// ── [10] Prix Meta ───────────────────────────────────────────────────────────────────────────────────────────────────
un(r, "data-dz-wa-onglet", "prix").declencher("click"); await attendre();
check("10.1 grille lue (deux marchés) et rappel « grille vide = aucun envoi »", attr(r, "data-dz-wa-prix-ligne").length === 2 && un(r, "data-dz-wa-prix-rappel").textContent === T("whatsapp.prix.rappel"));
const ligne1 = attr(r, "data-dz-wa-prix-ligne").find((l) => un(l, "data-dz-wa-prix-marche").value === "1");
un(ligne1, "data-dz-wa-prix-supprimer").declencher("click"); await attendre(2);
un(r, "data-dz-wa-prix-ajouter").declencher("click"); await attendre(2);
const neuve = attr(r, "data-dz-wa-prix-ligne").at(-1);
un(neuve, "data-dz-wa-prix-marche").value = "+44";
for (const [k, v] of [["marketing", "0.05"], ["utility", "0,02"], ["authentication", "0.02"], ["service", ""]]) un(neuve, "data-dz-wa-prix-col", k).value = v;
appels = [];
un(r, "data-dz-wa-prix-enregistrer").declencher("click"); await attendre();
const pp = posts("/api/cost/pricing")[0];
check("10.2 POST /api/cost/pricing : la grille ENTIÈRE au format exact (ligne supprimée absente)", pp && JSON.stringify(pp.corps) === JSON.stringify({ whatsapp_meta_usd: {
  "33": { marketing: 0.08, utility: 0.03, authentication: 0.03, service: 0 }, "44": { marketing: 0.05, utility: 0.02, authentication: 0.02 } } }), pp && pp.corps);
check("10.2b la grille est redessinée d'après la réponse", attr(r, "data-dz-wa-prix-ligne").length === 2);
const neuve2 = attr(r, "data-dz-wa-prix-ligne").at(-1);
un(neuve2, "data-dz-wa-prix-col", "marketing").value = "-1"; appels = [];
un(r, "data-dz-wa-prix-enregistrer").declencher("click"); await attendre();
check("10.3 tarif négatif : refusé avant l'envoi", posts("/api/cost/pricing").length === 0 && texteErreur(r) !== "");
un(neuve2, "data-dz-wa-prix-col", "marketing").value = "0.05"; un(neuve2, "data-dz-wa-prix-marche").value = "33"; appels = [];
un(r, "data-dz-wa-prix-enregistrer").declencher("click"); await attendre();
check("10.4 marché en double : refusé", posts("/api/cost/pricing").length === 0 && texteErreur(r) === T("whatsapp.prix.marche_double", { marche: "33" }), texteErreur(r));

// ── [11] 402 délégué à dz-plafonds.js ────────────────────────────────────────────────────────────────────────────────
let confirmations = 0;
window.__dzDialogue = { confirmer: async () => { confirmations++; return true; } };
vm.runInThisContext(readFileSync(join(SHARED, "dz-plafonds.js"), "utf8"), { filename: "dz-plafonds.js" });
check("11.0 dz-plafonds chargé (enveloppe de fetch)", !!window.__dzPlafonds);
r = await monter({ routes: { ["POST " + B + "/envoyer"]: (c, h) => h.get("X-DZ-Plafond") === "confirme" ? [200, { id: "wamid.9", statut: "accepted", devis: 0.08 }]
  : [402, { detail: { dz_plafond: { motif: "global", moteur: "", categorie: "whatsapp", deja_usd: 4.9, devis_usd: 0.2, plafond_usd: 5, message: "Plafond atteint" } } }] } });
await ouvrirConv(r, "tel:33600000001");
un(r, "data-dz-wa-texte").value = "Payant"; appels = [];
un(r, "data-dz-wa-envoyer").declencher("click"); await attendre(30);
const pl = posts(B + "/envoyer");
check("11.1 402 : le dialogue de dz-plafonds est ouvert puis la requête rejouée avec X-DZ-Plafond", confirmations === 1 && pl.length === 2 && pl[1].plafond === "confirme", pl);
check("11.2 rejouée et acceptée : aucun message d'erreur, saisie vidée", texteErreur(r) === "" && un(r, "data-dz-wa-texte").value === "", texteErreur(r));
{ // la boîte du plafond reste ouverte plus de 30 s : l'envoi n'a pas de délai d'abandon, la requête rejouée aboutit
  const dd = differe(); confirmations = 0;
  window.__dzDialogue = { confirmer: () => { confirmations++; return dd.promesse; } };
  un(r, "data-dz-wa-texte").value = "Payant lent"; appels = [];
  un(r, "data-dz-wa-envoyer").declencher("click"); await attendre(30);
  check("11.3 un envoi n'arme aucun délai d'abandon", ![...minuteries.values()].some((m) => m.ms === 29999), [...minuteries.values()].map((m) => m.ms));
  declencher(29999); declencher(30000); await attendre();       // l'horloge factice dépasse 30 s, boîte toujours ouverte
  dd.resoudre(true); await attendre(30);
  const pl2 = posts(B + "/envoyer");
  check("11.4 confirmé après 30 s : rejouée avec X-DZ-Plafond et acceptée", confirmations === 1 && pl2.length === 2 && pl2[1].plafond === "confirme"
    && texteErreur(r) === "" && un(r, "data-dz-wa-texte").value === "", [pl2.length, texteErreur(r)]);
  window.__dzDialogue = { confirmer: async () => true };
}

// ── [13] réponses périmées, délai d'abandon, double clic ─────────────────────────────────────────────────────────────
{
  const CID2 = "c2", B2 = "/api/whatsapp/" + CID2;
  const deux = comptes(); deux.comptes.push({ id: CID2, espace_id: EID, plateforme: "whatsapp", libelle: "WhatsApp 2", champs: [
    { nom: "WHATSAPP_PHONE_ID", secret: false, valeur: "pid2" }, { nom: "WHATSAPP_NUMERO", secret: false, valeur: "+33 9 99 99 99 99" }] });
  const CONVS2 = [{ id: "z1", identite: "tel:33700000009", nom: "Numéro B", dernier_entrant: null, fenetre_ouverte: false, stop: false }];
  const ETAT2 = Object.assign({}, ETAT, { plafond_mois: 222, alias: {} });
  const dc = differe();
  r = await monter({ routes: { "GET /api/comptes": [200, deux],
    ["GET " + B2 + "/conversations"]: [200, CONVS2], ["GET " + B2 + "/brouillons"]: [200, {}], ["GET " + B2 + "/etat"]: [200, ETAT2] } });
  // A : un tic dont les conversations reviennent APRÈS le choix du numéro B
  routes["GET " + B + "/conversations"] = () => dc.promesse;
  const tourA = tirer(); const pA = tourA(); await attendre();
  const sel = un(r, "data-dz-wa-numero"); sel.value = CID2; sel.declencher("change"); await attendre();
  dc.resoudre([200, CONVS.concat([{ id: "kz", identite: "tel:33611111111", nom: "Fantôme A", fenetre_ouverte: true, stop: false }])]);
  await pA; await attendre();
  check("13.1 réponse de A arrivée après le choix de B : rien de A dans le DOM", !r.textContent.includes("Fantôme A") && !un(r, "data-dz-wa-conv", "tel:33600000001")
    && !!un(r, "data-dz-wa-conv", "tel:33700000009"), attr(r, "data-dz-wa-conv").map((n) => n.getAttribute("data-dz-wa-conv")));
  check("13.2 … ni dans S", W.S.cid === CID2 && W.S.convs.length === 1 && W.S.convs[0].identite === "tel:33700000009");
  check("13.3 une seule minuterie après le chassé-croisé", actifs().length === 1, actifs().length);
  // A : l'état revient après le choix de B
  const de = differe();
  routes["GET " + B + "/etat"] = () => de.promesse; routes["GET " + B + "/conversations"] = [200, CONVS];
  sel.value = CID; sel.declencher("change"); await attendre(4);
  sel.value = CID2; sel.declencher("change"); await attendre();
  de.resoudre([200, Object.assign({}, ETAT, { plafond_mois: 999 })]); await attendre();
  check("13.4 état de A arrivé après B : S.etat reste celui de B", W.S.etat && W.S.etat.plafond_mois === 222 && W.S.cid === CID2, W.S.etat && W.S.etat.plafond_mois);
  check("13.5 … et les conversations de A ne sont jamais relues ni montrées", !un(r, "data-dz-wa-conv", "tel:33600000001"));
  // Santé de A lente, puis B
  sel.value = CID; sel.declencher("change"); await attendre();
  routes["GET " + B + "/etat"] = [200, ETAT];
  const ds = differe(); routes["GET " + B + "/modeles"] = () => ds.promesse;
  un(r, "data-dz-wa-onglet", "sante").declencher("click"); await attendre(4);
  sel.value = CID2; sel.declencher("change"); await attendre();
  ds.resoudre([200, MODELES_TOUS]); await attendre();
  check("13.6 Santé de A arrivée après B : le panneau montre B", (un(r, "data-dz-wa-sante", "total") || { textContent: "" }).textContent.includes("222")
    && !(un(r, "data-dz-wa-refuses") || { textContent: "" }).textContent.includes("vieux"), (un(r, "data-dz-wa-sante", "total") || {}).textContent);
}
{ // une LECTURE qui ne répond jamais : message réseau ; un ENVOI muet n'est jamais abandonné (boutons grisés)
  r = await monter({ routes: { ["POST " + B + "/relire"]: () => new Promise(() => {}) } });
  W.DELAI_MS = 777;
  un(r, "data-dz-wa-conv", "tel:33600000001").declencher("click"); await attendre();
  check("13.7 une lecture arme un délai d'abandon", [...minuteries.values()].some((m) => m.ms === 777));
  declencher(777); await attendre();
  check("13.8 lecture muette : message réseau", texteErreur(r) === T("whatsapp.erreur.reseau"), texteErreur(r));
  routes["POST " + B + "/relire"] = [200, MESSAGES];
  const de2 = differe(); routes["POST " + B + "/envoyer"] = () => de2.promesse;
  un(r, "data-dz-wa-texte").value = "Silence"; un(r, "data-dz-wa-bouton-ajouter").declencher("click"); await attendre(2); appels = [];
  un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
  check("13.9 pendant l'envoi : Envoyer, modèle, zone, titres et « Ajouter un bouton » grisés", un(r, "data-dz-wa-envoyer").disabled && un(r, "data-dz-wa-modele-ouvrir").disabled
    && un(r, "data-dz-wa-texte").disabled && un(r, "data-dz-wa-bouton-ajouter").disabled && un(r, "data-dz-wa-bouton-titre").disabled && un(r, "data-dz-wa-rediger").disabled);
  check("13.10 un envoi n'arme aucun délai d'abandon", ![...minuteries.values()].some((m) => m.ms === 777));
  un(r, "data-dz-wa-envoyer").declencher("click"); await attendre();
  check("13.11 double clic : un seul POST", posts(B + "/envoyer").length === 1);
  declencher(777); await attendre();
  de2.resoudre([200, { id: "w", statut: "accepted" }]); await attendre();
  check("13.12 parti après une longue attente : « envoyé », jamais « réseau », boutons rendus", texteErreur(r) === "" && un(r, "data-dz-wa-info").textContent === T("whatsapp.saisie.envoye")
    && !un(r, "data-dz-wa-envoyer").disabled && !un(r, "data-dz-wa-bouton-ajouter").disabled && !un(r, "data-dz-wa-texte").disabled, [texteErreur(r), un(r, "data-dz-wa-info").textContent]);
  W.DELAI_MS = 29999;
  appels = []; un(r, "data-dz-wa-rediger").declencher("click"); await attendre();
  check("13.12b rediger, decider, fil, accords, stop, prix : aucun délai d'abandon",
    ["POST", "PUT"].every((m) => ["/envoyer", "/brouillons/decider", "/brouillons/rediger", "/fil", "/accords", "/stop", "/stop/lever"].every((x) => !W.lecture(m, B + x + "?espace=e1")))
    && !W.lecture("POST", "/api/cost/pricing") && W.lecture("POST", B + "/relire?espace=e1") && W.lecture("GET", "/api/espaces")
    && ![...minuteries.values()].some((m) => m.ms === 29999));
  // modèle : champs et bouton grisés pendant l'envoi
  r = await monter(); await ouvrirConv(r, "tel:33600000002");
  un(r, "data-dz-wa-modele-ouvrir").declencher("click"); await attendre();
  un(r, "data-dz-wa-modele-choix").value = "rappel_rdv|fr"; un(r, "data-dz-wa-modele-suivant").declencher("click"); await attendre();
  un(r, "data-dz-wa-param", "prenom").value = "A"; un(r, "data-dz-wa-param", "heure").value = "B"; un(r, "data-dz-wa-entete", "text").value = "C";
  const dm = differe(); routes["POST " + B + "/envoyer"] = () => dm.promesse;
  un(r, "data-dz-wa-modele-envoyer").declencher("click"); await attendre();
  check("13.12c pendant l'envoi du modèle : paramètres, en-tête, payloads et bouton grisés", un(r, "data-dz-wa-param", "prenom").disabled && un(r, "data-dz-wa-entete", "text").disabled
    && un(r, "data-dz-wa-payload", "0").disabled && un(r, "data-dz-wa-modele-envoyer").disabled && un(r, "data-dz-wa-modele-ouvrir").disabled);
  dm.resoudre([200, { id: "w" }]); await attendre();
  check("13.12d modèle parti : boîte fermée, « Envoyer un modèle » rendu", !un(r, "data-dz-wa-modele-envoyer") && !un(r, "data-dz-wa-modele-ouvrir").disabled);
  // rafraichir qui lève : la minuterie continue
  const vrai = W.onglets.conversations.rafraichir;
  W.onglets.conversations.rafraichir = async () => { throw new Error("panne"); };
  await tirer()(); await attendre();
  check("13.12e rafraichir lève : la minuterie est reprogrammée", actifs().length === 1, actifs().length);
  W.onglets.conversations.rafraichir = vrai;
  routes["POST " + B + "/envoyer"] = [200, { id: "w" }];
  await ouvrirConv(r, "tel:33600000001");
  // fil : grisé et protégé du double clic
  const df = differe(); routes["POST " + B + "/fil"] = () => df.promesse; appels = [];
  un(r, "data-dz-wa-fil-action", "prendre").declencher("click"); await attendre();
  check("13.13 fil : boutons grisés pendant l'appel", un(r, "data-dz-wa-fil-action", "prendre").disabled && un(r, "data-dz-wa-fil-action", "rendre").disabled);
  un(r, "data-dz-wa-fil-action", "rendre").declencher("click"); await attendre();
  check("13.14 fil : un seul appel à la fois", posts(B + "/fil").length === 1);
  df.resoudre([200, { ok: true }]); await attendre();
  check("13.15 fil : boutons rendus", !un(r, "data-dz-wa-fil-action", "prendre").disabled);
  // modèle au nom de paramètre trop long : écarté, comme côté serveur
  r = await monter(); await ouvrirConv(r, "tel:33600000002");
  un(r, "data-dz-wa-modele-ouvrir").declencher("click"); await attendre();
  check("13.16 un nom de paramètre > 60 car. écarte le modèle", un(r, "data-dz-wa-modele-choix").enfants.length === 2
    && !un(r, "data-dz-wa-modele-choix").textContent.includes("trop_long"));
  // Contacts et Prix : grisés, un seul appel
  un(r, "data-dz-wa-onglet", "contacts").declencher("click"); await attendre();
  const da = differe(); routes["POST " + B + "/accords"] = () => da.promesse; appels = [];
  un(r, "data-dz-wa-accord-identite").value = "tel:33600000005"; un(r, "data-dz-wa-accord-source").value = "papier";
  const ba = un(r, "data-dz-wa-accord-ajouter"); ba.declencher("click"); await attendre();
  check("13.17 Contacts : bouton grisé pendant l'appel", ba.disabled === true);
  ba.declencher("click"); await attendre();
  check("13.18 Contacts : un seul POST", posts(B + "/accords").length === 1);
  da.resoudre([200, { ok: true }]); await attendre();
  un(r, "data-dz-wa-onglet", "prix").declencher("click"); await attendre();
  const dp = differe(); routes["POST /api/cost/pricing"] = () => dp.promesse; appels = [];
  const be = un(r, "data-dz-wa-prix-enregistrer"); be.declencher("click"); await attendre();
  check("13.19 Prix : Enregistrer grisé pendant l'appel", be.disabled === true && un(r, "data-dz-wa-prix-ajouter").disabled === true);
  be.declencher("click"); await attendre();
  check("13.20 Prix : un seul POST", posts("/api/cost/pricing").length === 1);
  dp.resoudre([200, { whatsapp_meta_usd: {} }]); await attendre();
  check("13.21 Prix : rendu après la réponse", be.disabled === false);
}

// ── [14] relecture finale : « repris » (Prendre le fil) et brouillon incertain ────────────────────────────────────────
{
  const BR = JSON.parse(JSON.stringify(BROUILLONS));
  BR["tel:33600000002"] = Object.assign({}, BR["tel:33600000002"], { pris: true });
  BR["tel:33600000001"] = Object.assign({}, BR["tel:33600000001"], { incertain: true });
  window.__dzDialogue = { confirmer: async () => true };
  r = await monter({ routes: { ["GET " + B + "/brouillons"]: [200, BR] } });
  check("14.1 pastille « repris » dans la liste (entrée sans etat, pris seul)", pastille("tel:33600000002", "repris") && !pastille("tel:33600000001", "repris"));
  const tete = (k) => un(r, "data-dz-wa-fil-action", k);
  const reprisVisibles = () => attr(r, "data-dz-wa-pastille", "repris").filter(visible).length;
  await ouvrirConv(r, "tel:33600000002");
  check("14.2 contact repris : seul « Rendre le fil » visible, pastille « repris » aussi dans l'en-tête",
    visible(tete("rendre")) && !visible(tete("prendre")) && reprisVisibles() === 2, reprisVisibles());
  await ouvrirConv(r, "tel:33600000001");
  check("14.3 contact non repris : seul « Prendre le fil » visible, pas de pastille d'en-tête",
    visible(tete("prendre")) && !visible(tete("rendre")) && reprisVisibles() === 1, reprisVisibles());
  check("14.4 brouillon incertain : avertissement visible", !!un(r, "data-dz-wa-incertain") && un(r, "data-dz-wa-incertain").textContent.includes(T("whatsapp.brouillon.incertain")));
  const BR2 = JSON.parse(JSON.stringify(BR)); BR2["tel:33600000001"].pris = true;
  routes["POST " + B + "/fil"] = [502, { detail: { message: "thread_control_in_progress", code: "thread_control_in_progress" } }];
  routes["GET " + B + "/brouillons"] = [200, BR2];
  tete("prendre").declencher("click"); await attendre();
  check("14.5 Kapso refuse « prendre » : erreur affichée, brouillons relus, le bouton devient « Rendre le fil »",
    texteErreur(r) !== "" && visible(tete("rendre")) && !visible(tete("prendre")), texteErreur(r));
  let conf = 0;
  window.__dzDialogue = { confirmer: async () => { conf++; return true; } };
  routes["POST " + B + "/brouillons/decider"] = (c) => (c && c.confirme_incertain === true
    ? [200, { envoi: { id: "wamid.3" }, brouillon: { etat: "envoye" } }] : [409, { detail: { message: "peut-être parti", code: "incertain" } }]);
  appels = [];
  un(r, "data-dz-wa-decider", "envoyer").declencher("click"); await attendre(30);
  const ds = posts(B + "/brouillons/decider");
  check("14.6 409 incertain : confirmation (dialogue maison) puis renvoi avec confirme_incertain",
    conf === 1 && ds.length === 2 && ds[0].corps.confirme_incertain === undefined && ds[1].corps.confirme_incertain === true, ds.map((d) => d.corps));
  window.__dzDialogue = { confirmer: async () => false };
  routes["POST " + B + "/brouillons/decider"] = [409, { detail: { message: "peut-être parti", code: "incertain" } }];
  appels = [];
  un(r, "data-dz-wa-decider", "envoyer").declencher("click"); await attendre(30);
  check("14.7 confirmation refusée : un seul appel, rien renvoyé, brouillon gardé (message)",
    posts(B + "/brouillons/decider").length === 1 && un(r, "data-dz-wa-info").textContent === T("whatsapp.brouillon.incertain_garde"));
  check("14.8 catégorie utility libellée « utilitaire »", T("whatsapp.categorie.utility") === "utilitaire" && T("whatsapp.prix.col_utility") === "Utilitaire"
    && T("whatsapp.prix.col_service") === "Conversation de service");
  window.__dzDialogue = { confirmer: async () => true };
}

// ── [12] hygiène ─────────────────────────────────────────────────────────────────────────────────────────────────────
check("12.1 toutes les clés dzT employées existent", absentes.size === 0, [...absentes]);
const MOTS = ["Bonjour", "Avec plaisir", "Payant", "Simple", "Encore", "Votre rendez-vous", "Léa, nous"];
check("12.2 aucun texte de message dans la console", !traces.some((t) => MOTS.some((m) => t.includes(m))), traces.filter((t) => MOTS.some((m) => t.includes(m))));
const SRC = ["whatsapp.js", "onglets-conversations.js", "onglets-gestion.js"].map((f) => readFileSync(join(PAGE, f), "utf8")).join("\n");
const sansCommentaires = SRC.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'\\])\/\/.*$/gm, "$1");
const litteraux = [...sansCommentaires.matchAll(/"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)'/g)].map((m) => m[1] ?? m[2]);
const francais = litteraux.filter((s) => /[àâçéèêëîïôûùüÿœ]/i.test(s) || /\b(le|la|les|des|une|aucun|envoyer|modèle|contact|fenêtre)\b/i.test(s) && /\s/.test(s));
check("12.3 aucun texte français en dur hors dico", francais.length === 0, francais.slice(0, 8));
const BLANCHE = new Set(["Accept", "Accept-Language", "Content-Type"]);
const majuscules = litteraux.filter((x) => /^[A-Z][a-z]/.test(x) && !BLANCHE.has(x));
check("12.3b aucun littéral à majuscule initiale hors liste blanche (en-têtes HTTP)", majuscules.length === 0, majuscules.slice(0, 8));
check("12.4 aucune console.log dans la page", !/console\.(log|info|debug)\(/.test(sansCommentaires));
check("12.5 icônes de la suite seulement (relevées)", [...icones].every((k) => /^dz-[a-z0-9-]+$/.test(k)) && icones.size > 0, [...icones]);

if (ko) { console.error(`ECHEC : ${ko}/${nb}`); process.exit(1); }
process.stdout.write(`whatsapp : ok (${nb} vérifications)\n`);
process.exit(0);
