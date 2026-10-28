// t285b (T10b, 24/10/2026) — le tiroir F1 « Demander à Deepotus » : onglets « Demander » / « Campagnes » et carte
// « Ouvrir l'agent Campagnes ». Charge le VRAI /shared/dz-agent.js (module ES) sur un DOM simulé (classe Noeud reprise
// de campagnes.test.mjs), avec un faux window.DzCampagnes qui enregistre ses appels monter / demonter.
// Séries : optionsCampagnes, onglet_campagnes_monte_le_composant, carte_ouvrir_campagnes, demander_inchange_sans_balise,
// rechargement_reprend_la_conversation, copies_dist_identiques, cles_fr_en.
// Lancer : node frontend/shared/qa/agent-onglets.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";
import * as L from "../dz-agent-logique.js";

const ICI = new URL("../", import.meta.url);
const SRC_AGENT = process.env.DZ_AGENT_SRC ? new URL("file:///" + process.env.DZ_AGENT_SRC.replace(/\\/g, "/")) : new URL("dz-agent.js", ICI);
const DICO = readFileSync(new URL("dz-i18n-dico.js", ICI), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const attendre = async (cond, ms = 3000) => {
  const fin = Date.now() + ms;
  while (Date.now() < fin) { if (cond()) return true; await new Promise((r) => setTimeout(r, 5)); }
  return !!cond();
};
const tick = () => new Promise((r) => setTimeout(r, 15));
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ---- 1. optionsCampagnes et les lectures validées (logique pure) ------------------------------------------------------
ok("1.1 sans espace : orienteur, contexte f1, rien d'autre", egal(L.optionsCampagnes({}), { contexte: "f1", role: "orienteur" }), JSON.stringify(L.optionsCampagnes({})));
ok("1.2 sans argument", egal(L.optionsCampagnes(), { contexte: "f1", role: "orienteur" }));
ok("1.3 un espace : rôle campagnes et espace_id", egal(L.optionsCampagnes({ espace: "e1" }), { contexte: "f1", role: "campagnes", espace_id: "e1" }));
ok("1.4 brief et cid passent", egal(L.optionsCampagnes({ espace: "e1", brief: "Lance", cid: "c1" }),
  { contexte: "f1", role: "campagnes", espace_id: "e1", brief: "Lance", cid: "c1" }), JSON.stringify(L.optionsCampagnes({ espace: "e1", brief: "Lance", cid: "c1" })));
ok("1.5 brief vide ou blanc : absent", !("brief" in L.optionsCampagnes({ brief: "   " })) && !("brief" in L.optionsCampagnes({ brief: "" })));
ok("1.6 espace vide : orienteur sans espace_id", egal(L.optionsCampagnes({ espace: "", brief: "x" }), { contexte: "f1", role: "orienteur", brief: "x" }));
ok("1.7 jamais de surCid dans la logique pure", !("surCid" in L.optionsCampagnes({ espace: "e1" })));
ok("1.8 ongletLu : demander par défaut", L.ongletLu(null) === "demander" && L.ongletLu("x") === "demander" && L.ongletLu("campagnes") === "campagnes" && L.ongletLu("demander") === "demander");
ok("1.9 campagneLue : JSON valide", egal(L.campagneLue('{"cid":"c1","role":"campagnes","espace":"e1"}'), { cid: "c1", role: "campagnes", espace: "e1" }));
ok("1.10 campagneLue : orienteur sans espace", egal(L.campagneLue('{"cid":"c2","role":"orienteur","espace":""}'), { cid: "c2", role: "orienteur", espace: "" }));
ok("1.11 campagneLue : refuse le mauvais", [null, "", "{", "[]", '{"cid":"","role":"orienteur"}', '{"cid":"c1","role":"demonstrateur"}',
  '{"cid":"a b","role":"orienteur"}', '{"cid":"c1","role":"campagnes","espace":"e 1"}', '{"cid":12,"role":"orienteur"}'].every((x) => L.campagneLue(x) === null));
ok("1.12 l'action campagnes ne donne aucune étape (elle ne passe pas par executer)", egal(L.etapes({ type: "campagnes", cible: "agent", question: "q" }, "quick"), []));

// ---- le DOM simulé (repris de campagnes.test.mjs, complété pour le tiroir) ----------------------------------------------
let DOC = null;
class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; this.scrollTop = 0; this.scrollHeight = 0; this.style = {}; this.dataset = {}; this.disabled = false; }
  get firstChild() { return this.children[0] || null; }
  get parentNode() { return this.parent; }
  get parentElement() { return this.parent; }
  get lastElementChild() { return this.children[this.children.length - 1] || null; }
  get isConnected() { let x = this; while (x.parent) x = x.parent; return !!x.racine; }
  get title() { return this.getAttribute("title") || ""; }
  set title(v) { this.setAttribute("title", v); }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  append(...cs) { cs.forEach((c) => this.appendChild(c)); }
  insertBefore(c, ref) { if (!ref) return this.appendChild(c); if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.splice(this.children.indexOf(ref), 0, c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  remove() { if (this.parent) this.parent.removeChild(this); }
  replaceChildren(...cs) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = ""; cs.forEach((c) => this.appendChild(c)); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); }
  contains(x) { for (let y = x; y; y = y.parent) if (y === this) return true; return false; }
  focus() { DOC.activeElement = this; }
  getBoundingClientRect() { return { x: 0, y: 0, left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  scrollIntoView() {}
  setPointerCapture() {}
  // l'événement remonte jusqu'au document (le keydown global du tiroir l'écoute)
  fire(t, ev = {}) {
    let arret = false;
    const e = { type: t, target: this, key: "", shiftKey: false, isComposing: false, repeat: false, preventDefault() { this.empeche = true; }, stopPropagation() { arret = true; }, ...ev };
    for (let x = this; x && !arret; x = x.parent) (x.ec[t] || []).slice().forEach((f) => f(e));
    if (!arret && this.isConnected) (DOC.ec[t] || []).slice().forEach((f) => f(e));
    return e;
  }
  click() { return this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
  // sélecteurs simples seulement : tag, #id, [attr], [attr="v"] (et tag[attr="v"]) ; le reste ne trouve rien
  querySelectorAll(sel) {
    const m = /^([a-z0-9]*)(?:#([\w-]+))?(?:\[([\w-]+)(?:="([^"]*)")?\])?$/i.exec(String(sel).trim());
    if (!m) return [];
    const [, tag, id, attr, val] = m;
    return [...this.tous()].filter((x) => x !== this && (!tag || x.tagName === tag.toUpperCase()) && (!id || x.attrs.id === id)
      && (!attr || (attr in x.attrs && (val === undefined || x.attrs[attr] === val))));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
function nouveauDocument() {
  const html = new Noeud("html"); html.racine = true;
  const head = new Noeud("head"), body = new Noeud("body");
  html.append(head, body);
  const d = {
    ec: {}, head, body, documentElement: html, activeElement: body,
    createElement: (t) => new Noeud(t), createElementNS: (ns, t) => new Noeud(t),
    createTextNode: (t) => { const x = new Noeud("#text"); x._t = String(t); return x; },
    addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); },
    removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); },
    getElementById: (id) => html.querySelector("#" + id),
    querySelector: (s) => html.querySelector(s), querySelectorAll: (s) => html.querySelectorAll(s),
    elementsFromPoint: () => [],
  };
  return d;
}
const marque = (racine, v) => racine.querySelector(`[data-dz-agent="${v}"]`);

// ---- le monde : window, dzT du vrai dictionnaire, fetch scripté, faux DzCampagnes --------------------------------------
function dictionnaire() {
  const ctx = { window: {} };
  vm.createContext(ctx);
  vm.runInContext(DICO, ctx);
  return ctx.window.DZ_I18N;
}
const D = dictionnaire();
const dzT = (cle, vars) => {
  const e = D[cle];
  if (!e) return cle;
  let s = e.fr;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
  return s;
};
function stockage(init = {}) {
  const m = new Map(Object.entries(init));
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: (k) => { m.delete(k); }, _m: m };
}
const reponse = (status, json) => ({ ok: status >= 200 && status < 300, status, json: async () => JSON.parse(JSON.stringify(json)) });
const appels = [];
const convEspaces = {};          // cid -> espace_id réglé côté serveur
let reponseDemander = { texte: "Voilà.", actions: [] };
const ESPACES = { espaces: [{ id: "e1", nom: "Marque A", archive: false }, { id: "e2", nom: "Marque B", archive: false }, { id: "e3", nom: "Vieille", archive: true },
  { id: "e4", nom: "Démo · Lune", archive: false, type: "demonstration" }], actif: "e1" };     // t353 : e4 = un espace démonstration
async function faux(url, init = {}) {
  const u = String(url), m = init.method || "GET";
  appels.push({ url: u, methode: m, corps: init.body ? JSON.parse(init.body) : undefined });
  if (m === "GET" && u === "/api/agent/etat") return reponse(200, { moteurs: [{ moteur: "m1", nom: "Moteur 1", cout: "gratuit" }], voix: null });
  if (m === "GET" && u.startsWith("/api/espaces")) return reponse(200, ESPACES);
  if (m === "POST" && u === "/api/agent/demander") return reponse(200, reponseDemander);
  // relecture d'une conversation par le tiroir (son espace a pu être réglé par la porte / la carte « espace »)
  if (m === "GET" && u.startsWith("/api/agent/campagnes/")) {
    const cid = decodeURIComponent(u.slice("/api/agent/campagnes/".length));
    return reponse(200, { id: cid, role: "orienteur", espace_id: convEspaces[cid] || null, messages: [] });
  }
  return reponse(404, { detail: "route absente du banc : " + u });
}
const camp = { appels: [] };
const fauxDzCampagnes = {
  monter(hote, opts) {
    const champ = new Noeud("textarea"); champ.setAttribute("data-dz-camp", "champ"); champ.value = opts.brief || "";
    const racine = new Noeud("div"); racine.setAttribute("data-dz-campagnes", "1"); racine.appendChild(champ);
    hote.appendChild(racine);
    const { surCid, ...reste } = opts;
    const rec = { type: "monter", opts: reste, surCid, hote, champ, demonte: false };
    camp.appels.push(rec);
    return { cid: () => null, recharger() {}, demonter() { rec.demonte = true; camp.appels.push({ type: "demonter", de: rec }); racine.remove(); } };
  },
};
const montages = () => camp.appels.filter((a) => a.type === "monter");
const dernier = () => montages()[montages().length - 1];

const win = {
  dzT, dzLang: () => "fr", localStorage: stockage(), sessionStorage: stockage(),
  addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
  innerWidth: 1200, innerHeight: 800, isSecureContext: false,
  location: { href: "http://local.test/", origin: "http://local.test" }, history: { replaceState() {} }, open() {},
  matchMedia: () => ({ matches: false }), fetch: faux, DzCampagnes: fauxDzCampagnes,
};
globalThis.window = win;
globalThis.fetch = faux;
globalThis.location = win.location;
globalThis.MutationObserver = class { observe() {} disconnect() {} };
globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);

async function charger(session, suffixe) {
  DOC = nouveauDocument();
  globalThis.document = DOC;
  win.sessionStorage = session;
  win.__dzAgent = false;
  await import(SRC_AGENT.href + (suffixe ? "?" + suffixe : ""));
  const tiroir = DOC.getElementById("dzAgentTiroir");
  const bouton = DOC.body.querySelectorAll("button").find((b) => (b.attrs.class || "") === "dzAgentBtn");
  return { tiroir, bouton };
}
const etat = (t) => {
  const ongD = marque(t, "onglet-demander"), ongC = marque(t, "onglet-campagnes");
  return { ongD, ongC, panD: DOC.getElementById(ongD.attrs["aria-controls"]), panC: DOC.getElementById(ongC.attrs["aria-controls"]),
    sel: marque(t, "espace"), hote: marque(t, "hote-campagnes"), moteur: t.querySelector(`select[aria-label="${dzT("agent.moteur.libelle")}"]`) };
};

// ---- 2. onglet_campagnes_monte_le_composant ---------------------------------------------------------------------------
const S1 = stockage();
const { tiroir: T1, bouton: B1 } = await charger(S1, "");
{
  ok("2.0 le tiroir est monté", !!T1 && !!B1);
  const e = etat(T1);
  const liste = T1.querySelector('[role="tablist"]');
  ok("2.1 une liste d'onglets étiquetée", !!liste && liste.attrs["aria-label"] === dzT("agent.onglets.libelle"), liste && liste.attrs["aria-label"]);
  ok("2.2 deux onglets role=tab, libellés dzT", e.ongD.attrs.role === "tab" && e.ongC.attrs.role === "tab"
    && e.ongD.textContent === dzT("agent.onglet.demander") && e.ongC.textContent === dzT("agent.onglet.campagnes"), e.ongD.textContent + "/" + e.ongC.textContent);
  ok("2.3 Demander ouvert par défaut", e.ongD.attrs["aria-selected"] === "true" && e.ongC.attrs["aria-selected"] === "false"
    && !e.panD.hasAttribute("hidden") && e.panC.hasAttribute("hidden"));
  ok("2.4 panneaux role=tabpanel reliés", e.panD.attrs.role === "tabpanel" && e.panC.attrs.role === "tabpanel"
    && e.panD.attrs["aria-labelledby"] === e.ongD.attrs.id && e.panC.attrs["aria-labelledby"] === e.ongC.attrs.id);
  ok("2.5 le fil et la saisie de Demander sont dans son panneau", !!e.panD.querySelector('[role="log"]') && !!e.panD.querySelector("textarea"));
  ok("2.6 rien n'est monté au chargement de la page", montages().length === 0 && !appels.some((a) => a.url.startsWith("/api/espaces")));
  B1.click();
  await attendre(() => appels.some((a) => a.url === "/api/agent/etat"));
  await tick();
  ok("2.7 ouvrir le tiroir sur Demander ne monte rien", montages().length === 0);
  e.ongC.click();
  await tick();
  ok("2.8 l'onglet Campagnes ouvert", e.ongC.attrs["aria-selected"] === "true" && e.ongD.attrs["aria-selected"] === "false"
    && !e.panC.hasAttribute("hidden") && e.panD.hasAttribute("hidden"));
  ok("2.9 l'onglet est gardé dans sessionStorage", S1.getItem("dz_agent_onglet") === "campagnes", S1.getItem("dz_agent_onglet"));
  ok("2.10 le choix du moteur est masqué sur Campagnes", !!e.moteur && e.moteur.hasAttribute("hidden"));
  ok("2.11 monter appelé UNE fois, contexte f1, orienteur, sans espace", montages().length === 1
    && egal(montages()[0].opts, { contexte: "f1", role: "orienteur" }) && typeof montages()[0].surCid === "function", JSON.stringify(montages().map((m) => m.opts)));
  ok("2.12 monté dans l'hôte du panneau", montages()[0].hote === e.hote && e.panC.contains(e.hote));
  await attendre(() => e.sel.children.length >= 3);
  ok("2.13 les espaces NON archivés sont lus (GET /api/espaces)", appels.filter((a) => a.url.startsWith("/api/espaces")).map((a) => a.url).join() === "/api/espaces",
    appels.filter((a) => a.url.startsWith("/api/espaces")).map((a) => a.url).join());
  const opts = e.sel.children.map((o) => o.attrs.value);
  ok("2.14 « Aucun espace » d'abord, puis e1, e2 (et e4, démonstration : ses brouillons témoins) ; l'archivé absent", egal(opts, ["", "e1", "e2", "e4"]) && e.sel.children[0].textContent === dzT("agent.campagnes.sans_espace")
    && e.sel.children[1].textContent === "Marque A", JSON.stringify(opts));
  ok("2.15 jamais l'espace actif d'office : valeur vide", e.sel.value === "", e.sel.value);
  ok("2.16 le sélecteur est étiqueté", e.sel.attrs["aria-label"] === dzT("agent.campagnes.espace"));
  // choisir un espace : démonter, remonter (campagnes, espace), le texte en cours suit comme brief
  montages()[0].champ.value = "Mon brief";
  e.sel.value = "e2"; e.sel.fire("change");
  await tick();
  ok("2.17 changer d'espace démonte la conversation", montages()[0].demonte === true);
  ok("2.18 …et remonte en rôle campagnes avec espace_id, conversation NEUVE, brief repris", montages().length === 2
    && egal(montages()[1].opts, { contexte: "f1", role: "campagnes", espace_id: "e2", brief: "Mon brief" }), JSON.stringify(montages()[1] && montages()[1].opts));
  ok("2.19 pas encore de conversation : sélecteur libre", !e.sel.hasAttribute("disabled"));
  montages()[1].surCid("c9");
  ok("2.20 surCid d'une campagne avec espace : sélecteur verrouillé", e.sel.hasAttribute("disabled"));
  ok("2.21 cid, rôle, espace gardés (dz_agent_camp)", egal(JSON.parse(S1.getItem("dz_agent_camp") || "null"), { cid: "c9", role: "campagnes", espace: "e2" }), S1.getItem("dz_agent_camp"));
  // aller-retour sur Demander : pas de remontage
  e.ongD.click(); await tick();
  ok("2.22 retour sur Demander", e.ongD.attrs["aria-selected"] === "true" && e.panC.hasAttribute("hidden") && !e.moteur.hasAttribute("hidden") && S1.getItem("dz_agent_onglet") === "demander");
  e.ongC.click(); await tick();
  ok("2.23 Demander puis Campagnes : pas de remontage", montages().length === 2 && !montages()[1].demonte);
  ok("2.24 les espaces ne sont lus qu'une fois", appels.filter((a) => a.url.startsWith("/api/espaces")).length === 1);
  // clavier : flèches gauche / droite entre les onglets
  e.ongC.fire("keydown", { key: "ArrowLeft" });
  ok("2.25 flèche gauche : Demander, focus dessus", e.ongD.attrs["aria-selected"] === "true" && DOC.activeElement === e.ongD);
  e.ongD.fire("keydown", { key: "ArrowRight" });
  ok("2.26 flèche droite : Campagnes, focus dessus", e.ongC.attrs["aria-selected"] === "true" && DOC.activeElement === e.ongC);
  ok("2.27 tabindex itinérant", e.ongC.attrs.tabindex === "0" && e.ongD.attrs.tabindex === "-1");
  ok("2.28 toujours pas de remontage", montages().length === 2);
  // ↺ sur Campagnes : conversation neuve, espace remis à vide, sélecteur déverrouillé
  const nouvelle = T1.querySelector(`button[aria-label="${dzT("agent.tiroir.nouvelle")}"]`);
  nouvelle.click(); await tick();
  ok("2.29 ↺ sur Campagnes démonte puis remonte une conversation neuve", montages()[1].demonte === true && montages().length === 3
    && egal(montages()[2].opts, { contexte: "f1", role: "orienteur" }), JSON.stringify(montages()[2] && montages()[2].opts));
  ok("2.30 ↺ : espace vide, sélecteur déverrouillé, dz_agent_camp oublié", e.sel.value === "" && !e.sel.hasAttribute("disabled") && S1.getItem("dz_agent_camp") === null);
  montages()[2].surCid("c10");
  ok("2.31 une conversation orienteur ne verrouille rien", !e.sel.hasAttribute("disabled"));
  ok("2.32 …mais elle est gardée", egal(JSON.parse(S1.getItem("dz_agent_camp") || "null"), { cid: "c10", role: "orienteur", espace: "" }), S1.getItem("dz_agent_camp"));
}

// ---- 3. carte_ouvrir_campagnes -----------------------------------------------------------------------------------------
{
  const e = etat(T1);
  // une campagne verrouillée en cours : la carte doit la remplacer par une conversation neuve
  e.sel.value = "e1"; e.sel.fire("change"); await tick();
  dernier().surCid("c11");
  ok("3.0 (préparation) campagne e1 verrouillée", e.sel.hasAttribute("disabled") && dernier().opts.espace_id === "e1");
  const avant = dernier();
  e.ongD.click(); await tick();
  reponseDemander = { texte: "C'est l'agent Campagnes qui s'en occupe.", actions: [{ type: "campagnes", cible: "agent", question: "Lance une campagne pour la rentrée" }] };
  const saisie = e.panD.querySelector("textarea");
  saisie.value = "Lance une campagne pour la rentrée";
  const envoyer = e.panD.querySelectorAll("button").find((b) => b.textContent === dzT("agent.tiroir.envoyer"));
  envoyer.click();
  await attendre(() => !!marque(T1, "ouvrir-campagnes"));
  const carte = marque(T1, "ouvrir-campagnes");
  ok("3.1 la réponse porte le bouton « Ouvrir l'agent Campagnes »", !!carte && carte.textContent === dzT("agent.action.campagnes") && carte.textContent !== "agent.action.campagnes",
    carte && carte.textContent);
  ok("3.2 la carte est dans le fil de Demander", !!carte && e.panD.contains(carte));
  const nbMonte = montages().length;
  if (carte) carte.click(); await tick();
  ok("3.3 clic : l'onglet Campagnes s'ouvre", e.ongC.attrs["aria-selected"] === "true" && !e.panC.hasAttribute("hidden") && S1.getItem("dz_agent_onglet") === "campagnes");
  ok("3.4 la conversation en cours est démontée", avant.demonte === true);
  ok("3.5 une conversation NEUVE est montée, brief = la question, orienteur, sans espace ni cid", montages().length === nbMonte + 1
    && egal(dernier().opts, { contexte: "f1", role: "orienteur", brief: "Lance une campagne pour la rentrée" }), JSON.stringify(dernier().opts));
  ok("3.6 le brief est prérempli dans le champ du composant", dernier().champ.value === "Lance une campagne pour la rentrée");
  ok("3.7 espace remis à vide, sélecteur déverrouillé, dz_agent_camp oublié", e.sel.value === "" && !e.sel.hasAttribute("disabled") && S1.getItem("dz_agent_camp") === null);
  ok("3.8 rien n'est envoyé tout seul (aucun POST à l'agent Campagnes)", !appels.some((a) => a.methode !== "GET" && a.url.startsWith("/api/agent/campagnes")));
  ok("3.8b le focus va au champ du composant", DOC.activeElement === dernier().champ);
  ok("3.9 la question a bien été posée à Demander", appels.filter((a) => a.url === "/api/agent/demander").length === 1);
  // l'espace choisi ensuite : le brief suit
  dernier().champ.value = "Lance une campagne pour la rentrée";
  e.sel.value = "e2"; e.sel.fire("change"); await tick();
  ok("3.10 choisir l'espace ensuite : le brief suit", egal(dernier().opts, { contexte: "f1", role: "campagnes", espace_id: "e2", brief: "Lance une campagne pour la rentrée" }), JSON.stringify(dernier().opts));
}

// ---- 4. demander_inchange_sans_balise -----------------------------------------------------------------------------------
{
  const e = etat(T1);
  e.ongD.click(); await tick();
  const avant = appels.filter((a) => a.url === "/api/agent/demander").length;
  reponseDemander = { texte: "Ouvre le Studio.", actions: [{ type: "aller", cible: "studio" }] };
  const saisie = e.panD.querySelector("textarea");
  saisie.value = "Où est le Studio ?";
  saisie.fire("keydown", { key: "Enter" });
  await attendre(() => appels.filter((a) => a.url === "/api/agent/demander").length === avant + 1 && /Ouvre le Studio/.test(e.panD.textContent));
  await tick();
  const dern = appels.filter((a) => a.url === "/api/agent/demander").pop();
  ok("4.1 Entrée dans la saisie envoie à Demander, comme avant", !!dern && dern.corps.question === "Où est le Studio ?" && dern.corps.lang === "fr" && "moteur" in dern.corps && Array.isArray(dern.corps.historique),
    JSON.stringify(dern && dern.corps));
  ok("4.2 la réponse arrive dans le fil", /Ouvre le Studio\./.test(e.panD.textContent));
  const boutons = e.panD.querySelectorAll("button");
  ok("4.3 l'action « Y aller » est rendue", boutons.some((b) => b.textContent === dzT("agent.action.aller")));
  const cartes = e.panD.querySelectorAll('[data-dz-agent="ouvrir-campagnes"]');
  ok("4.4 un seul bouton « Ouvrir l'agent Campagnes » (celui de la réponse précédente), aucun pour celle-ci", cartes.length === 1, cartes.length);
  const nb = montages().length;
  ok("4.5 rien n'est monté par l'envoi Demander", montages().length === nb);
  // Entrée dans un autre champ (celui du composant) ne part pas vers Demander
  e.ongC.click(); await tick();
  dernier().champ.fire("keydown", { key: "Enter" });
  await tick();
  ok("4.6 Entrée hors de la saisie de Demander ne lui envoie rien", appels.filter((a) => a.url === "/api/agent/demander").length === avant + 1);
}

// ---- 4b. surcid_perime_ignore (revue T10b) : le surCid d'un composant DÉMONTÉ (POST / encore en vol) ne touche à rien -
{
  const e = etat(T1);
  e.ongC.click(); await tick();
  const nouvelle = T1.querySelector(`button[aria-label="${dzT("agent.tiroir.nouvelle")}"]`);
  const photo = () => ({ camp: S1.getItem("dz_agent_camp"), verrou: e.sel.hasAttribute("disabled"), espace: e.sel.value });
  // a) changement d'espace : l'ancienne conversation orienteur répond après coup
  nouvelle.click(); await tick();
  const a = dernier();
  e.sel.value = "e2"; e.sel.fire("change"); await tick();
  let avant = photo();
  a.surCid("vieux-a");
  ok("4b.1 changement d'espace : le surCid de l'ancien montage est ignoré", egal(photo(), avant) && S1.getItem("dz_agent_camp") === null, JSON.stringify(photo()));
  // b) ↺ : l'ancienne campagne (avec espace) répond après coup → ni verrou ni cid gardé
  nouvelle.click(); await tick();
  e.sel.value = "e1"; e.sel.fire("change"); await tick();
  const b = dernier();
  nouvelle.click(); await tick();
  avant = photo();
  b.surCid("vieux-b");
  ok("4b.2 ↺ : le surCid de l'ancien montage est ignoré (pas de verrou, rien de gardé)", egal(photo(), avant) && !e.sel.hasAttribute("disabled") && S1.getItem("dz_agent_camp") === null, JSON.stringify(photo()));
  // c) la carte de passage de main : idem
  e.sel.value = "e1"; e.sel.fire("change"); await tick();
  const c = dernier();
  const carte = marque(T1, "ouvrir-campagnes");
  if (carte) carte.click(); await tick();
  avant = photo();
  c.surCid("vieux-c");
  ok("4b.3 carte : le surCid de l'ancien montage est ignoré", !!carte && c.demonte && egal(photo(), avant) && !e.sel.hasAttribute("disabled") && S1.getItem("dz_agent_camp") === null, JSON.stringify(photo()));
  // le montage courant, lui, est toujours écouté
  dernier().surCid("c-courant");
  ok("4b.4 le surCid du montage courant compte toujours", egal(JSON.parse(S1.getItem("dz_agent_camp") || "null"), { cid: "c-courant", role: "orienteur", espace: "" }), S1.getItem("dz_agent_camp"));
}

// ---- 4c. espace_regle_par_la_porte (relecture de branche) : une conversation orienteur dont l'espace a été réglé côté
// serveur (porte / carte « espace ») montre cet espace et verrouille le sélecteur ; un changement ne remonte rien.
{
  const e = etat(T1);
  const nouvelle = T1.querySelector(`button[aria-label="${dzT("agent.tiroir.nouvelle")}"]`);
  nouvelle.click(); await tick();
  dernier().surCid("c50");
  ok("4c.0 (préparation) orienteur sans espace : libre", !e.sel.hasAttribute("disabled") && e.sel.value === "");
  convEspaces.c50 = "e1";                       // la porte a réglé l'espace dans le composant
  const nb = montages().length;
  e.sel.value = "e2"; e.sel.fire("change");
  await attendre(() => e.sel.hasAttribute("disabled"), 500);
  await tick();
  ok("4c.1 changement tenté : relu sur le serveur, AUCUN remontage", montages().length === nb && !dernier().demonte);
  ok("4c.2 le sélecteur revient à l'espace de la conversation et se verrouille", e.sel.value === "e1" && e.sel.hasAttribute("disabled"), e.sel.value);
  ok("4c.3 l'espace est gardé avec la conversation", egal(JSON.parse(S1.getItem("dz_agent_camp") || "null"), { cid: "c50", role: "orienteur", espace: "e1" }), S1.getItem("dz_agent_camp"));
  // rafraîchi aussi dès qu'on approche le sélecteur (pointerdown / focus), avant tout choix
  nouvelle.click(); await tick();
  dernier().surCid("c51");
  convEspaces.c51 = "e2";
  e.sel.fire("pointerdown");
  await attendre(() => e.sel.hasAttribute("disabled"), 500);
  ok("4c.4 pointerdown sur le sélecteur : l'espace réglé est appris et verrouillé", e.sel.value === "e2" && e.sel.hasAttribute("disabled"), e.sel.value);
  // ↺ libère toujours
  nouvelle.click(); await tick();
  ok("4c.5 ↺ : conversation neuve, sélecteur libre", !e.sel.hasAttribute("disabled") && e.sel.value === "" && S1.getItem("dz_agent_camp") === null);
}

// ---- 5. DzCampagnes absent, puis rechargement de la page : la même conversation est remontée ----------------------------
{
  const S2 = stockage({ dz_agent_onglet: "campagnes", dz_agent_camp: JSON.stringify({ cid: "c42", role: "campagnes", espace: "e1" }) });
  delete win.DzCampagnes;
  const nb = montages().length;
  const { tiroir: T2, bouton: B2 } = await charger(S2, "recharge");
  const e = etat(T2);
  ok("5.1 rechargé : l'onglet gardé est Campagnes", e.ongC.attrs["aria-selected"] === "true" && !e.panC.hasAttribute("hidden"));
  ok("5.2 rien n'est monté avant l'ouverture du tiroir", montages().length === nb);
  B2.click(); await tick();
  const msg = marque(T2, "campagnes-indisponible");
  ok("5.3 DzCampagnes absent : un message clair (dzT), aucune erreur", !!msg && msg.textContent === dzT("agent.campagnes.indisponible") && msg.textContent !== "agent.campagnes.indisponible", msg && msg.textContent);
  // fermer, rendre le composant, rouvrir : la conversation gardée est remontée par son cid
  B2.click(); await tick();
  win.DzCampagnes = fauxDzCampagnes;
  B2.click(); await tick();
  ok("5.4 la conversation gardée est remontée (cid, rôle campagnes, espace)", montages().length === nb + 1
    && egal(dernier().opts, { contexte: "f1", role: "campagnes", espace_id: "e1", cid: "c42" }), JSON.stringify(dernier() && dernier().opts));
  ok("5.5 le message d'indisponibilité est parti", !marque(T2, "campagnes-indisponible"));
  await attendre(() => e.sel.children.length >= 3);
  await tick();
  ok("5.6 son espace est affiché et verrouillé", e.sel.value === "e1" && e.sel.hasAttribute("disabled"), e.sel.value);
}
win.DzCampagnes = fauxDzCampagnes;

// ---- 5b. rechargement d'une conversation orienteur dont l'espace a été réglé par la porte ------------------------------
{
  convEspaces.c77 = "e2";
  const S3 = stockage({ dz_agent_onglet: "campagnes", dz_agent_camp: JSON.stringify({ cid: "c77", role: "orienteur", espace: "" }) });
  const { tiroir: T3, bouton: B3 } = await charger(S3, "recharge2");
  const e = etat(T3);
  B3.click();
  await attendre(() => e.sel.hasAttribute("disabled") && e.sel.children.length >= 3, 500);
  await tick();
  ok("5b.1 remontée par son cid", egal(dernier().opts, { contexte: "f1", role: "orienteur", cid: "c77" }), JSON.stringify(dernier().opts));
  ok("5b.2 l'espace réglé côté serveur est lu, affiché et verrouillé", e.sel.value === "e2" && e.sel.hasAttribute("disabled"), e.sel.value);
  ok("5b.3 …et gardé", egal(JSON.parse(S3.getItem("dz_agent_camp") || "null"), { cid: "c77", role: "orienteur", espace: "e2" }), S3.getItem("dz_agent_camp"));
}

// ---- 5c. t352 : l'onglet Veille monte dz-veille.js pour l'espace choisi ---------------------------------------------------
{
  const veilles = [];
  win.DzVeille = { monter(hote, opts) {
    const rec = { opts: { ...opts }, demonte: false, recharges: 0 };
    const racine = new Noeud("div"); racine.setAttribute("data-dz-veille", "racine"); hote.appendChild(racine);
    veilles.push(rec);
    return { recharger() { rec.recharges++; }, demonter() { rec.demonte = true; racine.remove(); } };
  } };
  const S4 = stockage();
  const nEsp0 = appels.filter((a) => a.url.startsWith("/api/espaces")).length;
  const { tiroir: T4, bouton: B4 } = await charger(S4, "veille");
  const ongV = marque(T4, "onglet-veille"), ongD4 = marque(T4, "onglet-demander"), ongC4 = marque(T4, "onglet-campagnes");
  const liste = T4.querySelector('[role="tablist"]');
  ok("5c.1 quatre onglets (t353), Veille traduit", !!ongV && liste.children.length === 4 && ongV.textContent === dzT("agent.onglet.veille")
    && ongV.attrs.role === "tab", ongV && ongV.textContent);
  const panV = DOC.getElementById(ongV.attrs["aria-controls"]);
  ok("5c.2 le panneau Veille est caché au départ", !!panV && panV.hasAttribute("hidden"));
  B4.click(); await tick();
  ongV.click(); await tick(); await tick();
  const selV = marque(T4, "espace-veille");
  ok("5c.3 Veille ouvert, gardé en session", ongV.attrs["aria-selected"] === "true" && !panV.hasAttribute("hidden")
    && S4.getItem("dz_agent_onglet") === "veille");
  ok("5c.4 monté sur l'espace actif (la veille ne fait que lire)", veilles.length === 1 && veilles[0].opts.espace_id === "e1"
    && selV.value === "e1", JSON.stringify(veilles.map((v) => v.opts)));
  ok("5c.5 l'espace archivé n'est pas proposé", !Array.from(selV.children).some((o) => o.getAttribute("value") === "e3"));
  selV.value = "e2"; selV.fire("change"); await tick();
  ok("5c.6 changer d'espace démonte puis remonte", veilles[0].demonte && veilles.length === 2 && veilles[1].opts.espace_id === "e2"
    && S4.getItem("dz_agent_veille") === "e2");
  ongD4.click(); await tick(); ongV.click(); await tick(); await tick();
  ok("5c.7 Demander puis Veille : pas de remontage", veilles.length === 2 && !veilles[1].demonte);
  const nouvelle = T4.querySelector(`button[aria-label="${dzT("agent.tiroir.nouvelle")}"]`);
  nouvelle.click(); await tick();
  ok("5c.8 ↺ sur Veille relit la veille", veilles[1].recharges === 1 && veilles.length === 2);
  const ongP4 = marque(T4, "onglet-prospects");
  const nEspAvantP = appels.filter((a) => a.url.startsWith("/api/espaces")).length;     // t353 suite : Prospects relit les siens
  ongV.fire("keydown", { key: "ArrowRight" });
  ok("5c.9 flèche droite depuis Veille : Prospects (t353)", ongP4.attrs["aria-selected"] === "true" && DOC.activeElement === ongP4);
  ongP4.fire("keydown", { key: "ArrowRight" });
  ok("5c.9b flèche droite depuis Prospects : retour à Demander (boucle)", ongD4.attrs["aria-selected"] === "true" && DOC.activeElement === ongD4);
  ongD4.fire("keydown", { key: "ArrowLeft" }); await tick(); await tick();
  ok("5c.10 flèche gauche depuis Demander : Prospects", ongP4.attrs["aria-selected"] === "true" && DOC.activeElement === ongP4);
  ongP4.fire("keydown", { key: "ArrowLeft" }); await tick(); await tick();
  ok("5c.10b flèche gauche depuis Prospects : Veille", ongV.attrs["aria-selected"] === "true" && DOC.activeElement === ongV);
  ongV.fire("keydown", { key: "ArrowLeft" });
  ok("5c.11 flèche gauche depuis Veille : Campagnes", ongC4.attrs["aria-selected"] === "true");
  ok("5c.12 les espaces ne sont lus qu'une fois pour les deux onglets", nEspAvantP === nEsp0 + 1, nEspAvantP - nEsp0);
  const S5 = stockage({ dz_agent_onglet: "veille", dz_agent_veille: "e2" });
  const avant = veilles.length;
  const { tiroir: T5, bouton: B5 } = await charger(S5, "veille2");
  B5.click(); await tick(); await tick();
  ok("5c.13 rechargé : Veille gardé, sur l'espace gardé", marque(T5, "onglet-veille").attrs["aria-selected"] === "true"
    && veilles.length === avant + 1 && veilles[veilles.length - 1].opts.espace_id === "e2", JSON.stringify(veilles.slice(avant).map((v) => v.opts)));
  delete win.DzVeille;
  const { tiroir: T6, bouton: B6 } = await charger(stockage({ dz_agent_onglet: "veille" }), "veille3");
  B6.click(); await tick(); await tick();
  ok("5c.14 sans dz-veille.js : un message, pas d'erreur", !!marque(T6, "veille-indisponible")
    && marque(T6, "veille-indisponible").textContent === dzT("agent.veille.indisponible"));
}

// ---- 5d. t353 : l'onglet Prospects monte dz-prospects.js pour l'espace choisi, jamais un espace démonstration ---------
{
  const montes = [];
  win.DzProspects = { monter(hote, opts) {
    const rec = { opts: { ...opts }, demonte: false, recharges: 0 };
    const racine = new Noeud("div"); racine.setAttribute("data-dz-prospects", "racine"); hote.appendChild(racine);
    montes.push(rec);
    return { recharger() { rec.recharges++; }, demonter() { rec.demonte = true; racine.remove(); } };
  } };
  const S7 = stockage();
  const { tiroir: T7, bouton: B7 } = await charger(S7, "prospects");
  const ongP = marque(T7, "onglet-prospects");
  ok("5d.1 onglet Prospects traduit", !!ongP && ongP.textContent === dzT("agent.onglet.prospects") && ongP.attrs.role === "tab");
  B7.click(); await tick();
  ongP.click(); await tick(); await tick();
  const selP = marque(T7, "espace-prospects");
  ok("5d.2 ouvert, gardé en session, monté sur l'espace actif", ongP.attrs["aria-selected"] === "true" && S7.getItem("dz_agent_onglet") === "prospects"
    && montes.length === 1 && montes[0].opts.espace_id === "e1" && selP.value === "e1", JSON.stringify(montes.map((v) => v.opts)));
  const valeurs = Array.from(selP.children).map((o) => o.getAttribute("value"));
  ok("5d.3 ni l'espace archivé ni l'espace démonstration", !valeurs.includes("e3") && !valeurs.includes("e4") && valeurs.includes("e2"), valeurs.join());
  ok("5d.4 l'espace démonstration reste proposé à la Veille", Array.from(marque(T7, "espace-veille").children).some((o) => o.getAttribute("value") === "e4"));
  selP.value = "e2"; selP.fire("change"); await tick();
  ok("5d.5 changer d'espace démonte puis remonte", montes[0].demonte && montes.length === 2 && montes[1].opts.espace_id === "e2"
    && S7.getItem("dz_agent_prospects") === "e2");
  const nouvelle = T7.querySelector(`button[aria-label="${dzT("agent.tiroir.nouvelle")}"]`);
  nouvelle.click(); await tick();
  ok("5d.6 ↺ sur Prospects relit la liste", montes[1].recharges === 1 && montes.length === 2);
  // t353 suite (M8) : un espace archivé depuis sort du sélecteur à la prochaine ouverture de l'onglet, et l'écran revient au défaut
  ESPACES.espaces[1].archive = true;
  marque(T7, "onglet-demander").click(); await tick();
  ongP.click(); await tick(); await tick();
  const vals2 = Array.from(selP.children).map((o) => o.getAttribute("value"));
  ok("5d.6b espace archivé depuis : retiré, l'écran remonté sur l'espace actif", !vals2.includes("e2") && vals2.includes("e1")
    && montes.length === 3 && montes[1].demonte && montes[2].opts.espace_id === "e1" && selP.value === "e1", vals2.join() + " " + montes.length);
  ESPACES.espaces[1].archive = false;
  delete win.DzProspects;
  const { tiroir: T8, bouton: B8 } = await charger(stockage({ dz_agent_onglet: "prospects" }), "prospects2");
  B8.click(); await tick(); await tick();
  ok("5d.7 sans dz-prospects.js : un message, pas d'erreur", !!marque(T8, "prospects-indisponible")
    && marque(T8, "prospects-indisponible").textContent === dzT("agent.prospects.indisponible"));
}

// ---- 6. copies_dist_identiques ------------------------------------------------------------------------------------------
for (const f of ["dz-agent.js", "dz-agent-logique.js"]) {
  const a = readFileSync(new URL(f, ICI)), b = readFileSync(new URL("../dist/shared/" + f, ICI));
  ok("6 copie dist identique : " + f, Buffer.compare(a, b) === 0);
}

// ---- 7. cles_fr_en ------------------------------------------------------------------------------------------------------
{
  const src = readFileSync(new URL("dz-agent.js", ICI), "utf8");
  const json = JSON.parse(readFileSync(new URL("i18n/agent.json", ICI), "utf8"));
  const cles = [...new Set(src.match(/"agent\.[a-z_]+\.[a-z_.]+"/g).map((s) => s.slice(1, -1)))];
  const manquent = cles.filter((k) => !(D[k] && D[k].fr && D[k].en) || !(json[k] && json[k].fr && json[k].en));
  ok("7.1 chaque clé agent.… employée existe en FR et EN (agent.json et dictionnaire assemblé)", cles.length > 20 && !manquent.length, manquent.join(", "));
  for (const k of ["agent.onglet.demander", "agent.onglet.campagnes", "agent.onglets.libelle", "agent.campagnes.espace",
    "agent.campagnes.sans_espace", "agent.campagnes.indisponible", "agent.action.campagnes"]) {
    ok("7.2 clé t285b employée et traduite : " + k, cles.includes(k) && !!(json[k] && json[k].fr && json[k].en), k);
  }
  ok("7.3 le titre de l'en-tête tient sur une ligne", /\.dzAgentTete h2\{[^}]*min-width:0[^}]*white-space:nowrap[^}]*text-overflow:ellipsis/.test(src));
  ok("7.4 le choix du moteur est borné en largeur", /\.dzAgentTete select\{[^}]*max-width:104px/.test(src));
}

if (echecs.length) {
  console.error("ÉCHECS (" + echecs.length + "/" + n + ") :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("agent-onglets : OK (" + n + " vérifications)");
process.exit(0);
