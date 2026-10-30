// t382 (30/10/2026, lot « Réglages : chemins & apparence ») — dz-apparence.js : la PALETTE de l'application, jouée
// avec un DOM, un localStorage et un fetch simulés. Séries :
//  A. logique pure : contraste WCAG, sombre/clair, jetons dérivés (mêmes noms partout), encre du bouton, contrôles AA
//     (tous les préréglages passent, une palette illisible est signalée), normalisation ;
//  B. application : Deepotus sombre = RIEN d'écrit ; un autre état écrit les jetons en style en ligne sur <html>,
//     data-theme et color-scheme, dans la coque ET dans chaque cadre de même origine (labs, cadre dans un cadre) ;
//     revenir au sombre efface tout, sans toucher un data-theme posé par quelqu'un d'autre ;
//  C. persistance : le cache local peint au chargement, le serveur fait foi (synchroniser), un choix est gardé en
//     local et envoyé au serveur, l'évènement storage d'un autre onglet est suivi ;
//  D. le panneau de Réglages › Apparence en FR et en EN : préréglages, six jetons (couleur + hexadécimal), aperçu,
//     contraste AA, « Personnalisée », hexadécimal refusé, échec d'enregistrement, « Réinitialiser » ; aucun innerHTML.
// Lancer : node frontend/shared/qa/apparence.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-apparence.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };
const dort = (ms) => new Promise((r) => setTimeout(r, ms));
const INNER = [];

class Style {
  constructor() { this.p = {}; }
  setProperty(k, v) { this.p[k] = String(v); }
  removeProperty(k) { delete this.p[k]; }
  getPropertyValue(k) { return this.p[k] || ""; }
}
class Noeud {
  constructor(tag, doc) { this.tagName = String(tag).toUpperCase(); this.children = []; this.attrs = {}; this.ec = {};
                          this.parent = null; this.textContent = ""; this.disabled = false; this.value = "";
                          this.style = new Style(); this.ownerDocument = doc; }
  get firstChild() { return this.children[0] || null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  removeChild(c) { this.children.splice(this.children.indexOf(c), 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  emettre(t, ev) { (this.ec[t] || []).forEach((f) => f(Object.assign({ target: this, preventDefault() {} }, ev || {}))); }
  set innerHTML(_v) { INNER.push(this.tagName); }
}
const tous = (n, acc = []) => { acc.push(n); n.children.forEach((c) => tous(c, acc)); return acc; };
const texte = (n) => tous(n).map((x) => x.textContent).filter(Boolean).join(" | ");
const parAttr = (n, k, v) => tous(n).filter((x) => x.attrs && (v === undefined ? k in x.attrs : x.attrs[k] === v));
const un = (n, k, v) => parAttr(n, k, v)[0];

function documentFactice(nom) {
  const d = { nom, cadres: [], ec: {} };
  d.documentElement = new Noeud("html", d);
  d.createElement = (t) => new Noeud(t, d);
  d.querySelectorAll = (sel) => (sel === "iframe" ? d.cadres.slice() : []);
  d.addEventListener = (t, f) => { (d.ec[t] = d.ec[t] || []).push(f); };
  return d;
}
function cadre(docInterne) {
  const f = new Noeud("iframe");
  f.contentDocument = docInterne;
  return f;
}

function monde(lang, opts = {}) {
  const appels = [];
  const stock = Object.assign({}, opts.stock || {});
  const doc = documentFactice("coque");
  const ecouteurs = {};
  const w = {
    navigator: { language: lang },
    localStorage: { getItem: (k) => (k in stock ? stock[k] : null), setItem: (k, v) => { stock[k] = String(v); },
                    removeItem: (k) => { delete stock[k]; } },
    document: doc,
    addEventListener: (t, f) => { (ecouteurs[t] = ecouteurs[t] || []).push(f); },
    fetch: async (url, o) => {
      appels.push({ url, methode: (o && o.method) || "GET", corps: o && o.body ? JSON.parse(o.body) : undefined });
      const r = (opts.reponses || (() => ({ corps: { etat: { preset: "sombre" } } })))(url, o || {});
      return { ok: r.ok !== false, status: r.status || 200, json: async () => r.corps };
    },
    setTimeout, clearTimeout, console, Promise, JSON, Date, Object, Math, Number, String, Array, RegExp, parseInt,
  };
  w.window = w;
  w.top = w;
  w.globalThis = w;
  vm.createContext(w);
  vm.runInContext(DICO, w);
  w.dzLang = () => lang;
  w.dzT = (k, v) => {
    const e = w.DZ_I18N[k]; if (!e) return "⟦" + k + "⟧";
    return String(e[lang]).replace(/\{(\w+)\}/g, (m, x) => (v && v[x] != null ? String(v[x]) : m));
  };
  if (opts.avant) opts.avant(w, doc);
  vm.runInContext(SRC, w);
  return { w, doc, appels, stock, A: w.__dzApparence, emettre: (t, ev) => (ecouteurs[t] || []).forEach((f) => f(ev)) };
}

const PROP = (doc, k) => doc.documentElement.style.getPropertyValue(k);
const NB = (doc) => Object.keys(doc.documentElement.style.p).length;

// ───────────────────────────── A. logique pure ─────────────────────────────
{
  const { A } = monde("fr");
  ok("A0 window.__dzApparence existe", !!A);
  ok("A1 contraste noir/blanc = 21, identique = 1", Math.abs(A.contraste("#000000", "#ffffff") - 21) < 1e-9
     && Math.abs(A.contraste("#777777", "#777777") - 1) < 1e-9);
  ok("A2 contraste symétrique", A.contraste("#f0b429", "#151519") === A.contraste("#151519", "#f0b429"));
  ok("A3 préréglages dans l'ordre", JSON.stringify(A.ORDRE) === JSON.stringify(["sombre", "clair", "contraste", "deeplab"]));
  ok("A4 six jetons", JSON.stringify(A.JETONS) === JSON.stringify(["fond", "panneau", "texte", "accent", "succes", "erreur"]));
  ok("A5 chaque préréglage a ses six couleurs #rrggbb", A.ORDRE.every((p) => A.JETONS.every(
     (j) => /^#[0-9a-f]{6}$/.test(A.PRESETS[p].couleurs[j]))));
  ok("A6 sombre / clair d'après le fond", A.sombre(A.PRESETS.sombre.couleurs) && !A.sombre(A.PRESETS.clair.couleurs)
     && A.sombre(A.PRESETS.contraste.couleurs) && A.sombre(A.PRESETS.deeplab.couleurs));
  const gris = (h) => Object.assign({}, A.PRESETS.sombre.couleurs, { fond: h });
  ok("A6b le seuil sombre/clair tient sur les gris moyens", A.sombre(gris("#333333")) && A.sombre(gris("#6a6a6a"))
     && !A.sombre(gris("#8a8a8a")));
  const dc = A.deriver(A.PRESETS.clair.couleurs, "coque");
  const dl = A.deriver(A.PRESETS.clair.couleurs, "lab");
  ok("A7 mêmes jetons écrits dans la coque et dans un lab", JSON.stringify(Object.keys(dc).sort()) === JSON.stringify(Object.keys(dl).sort()));
  ok("A8 les jetons de base de la coque ET des labs", ["--bg-base", "--bg-panel", "--bg-panel-2", "--bg-panel-3", "--bg-overlay",
     "--well", "--stroke", "--stroke-strong", "--ink-strong", "--ink", "--ink-soft", "--ink-muted", "--accent", "--accent-soft",
     "--accent-ink", "--amber", "--amber-soft", "--cyan", "--cyan-soft", "--cyan-glow", "--green", "--green-soft", "--red",
     "--red-soft", "--slate", "color-scheme"].every((k) => k in dc), Object.keys(dc));
  ok("A9 la couleur de marque (logo) n'est jamais réécrite", !("--brand" in dc) && !("--brand-soft" in dc));
  ok("A10 fond, panneau, texte, accent, succès, erreur posés tels quels", dc["--bg-base"] === "#f2f0ec"
     && dc["--bg-panel"] === "#ffffff" && dc["--ink-strong"] === "#171512" && dc["--accent"] === "#a06a00"
     && dc["--amber"] === "#a06a00" && dc["--cyan"] === "#a06a00" && dc["--green"] === "#1f7a5c" && dc["--red"] === "#b03a28");
  ok("A11 color-scheme suit le fond", dc["color-scheme"] === "light"
     && A.deriver(A.PRESETS.deeplab.couleurs, "coque")["color-scheme"] === "dark");
  ok("A12 les encres sont entre le texte et le panneau, de plus en plus discrètes",
     A.contraste(dc["--ink-strong"], dc["--bg-panel"]) > A.contraste(dc["--ink"], dc["--bg-panel"])
     && A.contraste(dc["--ink"], dc["--bg-panel"]) > A.contraste(dc["--ink-soft"], dc["--bg-panel"])
     && A.contraste(dc["--ink-soft"], dc["--bg-panel"]) > A.contraste(dc["--ink-muted"], dc["--bg-panel"]));
  ok("A13 l'encre du bouton est la plus lisible sur l'accent", A.contraste(dc["--accent-ink"], "#a06a00") >= 4.5
     && A.contraste(A.deriver(A.PRESETS.sombre.couleurs, "coque")["--accent-ink"], "#f0b429") >= 4.5);
  ok("A14 panneau 3 : surface d'élévation dans la coque, puits dans un lab (sombre)",
     A.contraste(A.deriver(A.PRESETS.sombre.couleurs, "coque")["--bg-panel-3"], "#000000")
     > A.contraste(A.deriver(A.PRESETS.sombre.couleurs, "lab")["--bg-panel-3"], "#000000"));
  const fort = A.deriver(A.PRESETS.contraste.couleurs, "coque", true), mou = A.deriver(A.PRESETS.contraste.couleurs, "coque", false);
  ok("A15 « fort » rapproche les encres secondaires du texte", A.contraste(fort["--ink-soft"], fort["--bg-panel"])
     > A.contraste(mou["--ink-soft"], mou["--bg-panel"]));
  ok("A16 contraste élevé est « fort »", A.PRESETS.contraste.fort === true && !A.PRESETS.sombre.fort);
  for (const p of A.ORDRE) {
    const c = A.controles(A.PRESETS[p].couleurs, A.PRESETS[p].fort);
    ok(`A17 ${p} : tous les contrôles AA passent`, c.length === 7 && c.every((x) => x.ok),
       JSON.stringify(c.filter((x) => !x.ok)));
  }
  const ids = A.controles(A.PRESETS.sombre.couleurs).map((x) => x.id + ":" + x.seuil).join(",");
  ok("A18 les contrôles et leurs seuils (4,5 texte, 3 accent sur panneau)", ids ===
     "texte_fond:4.5,texte_panneau:4.5,secondaire_panneau:4.5,accent_panneau:3,bouton:4.5,succes_panneau:4.5,erreur_panneau:4.5", ids);
  const mauvais = A.controles(Object.assign({}, A.PRESETS.sombre.couleurs, { texte: "#3a3a3a", accent: "#202024" }));
  ok("A19 une palette illisible est signalée", mauvais.find((x) => x.id === "texte_panneau").ok === false
     && mauvais.find((x) => x.id === "accent_panneau").ok === false && mauvais.find((x) => x.id === "succes_panneau").ok === true);
  ok("A20 normaliser : préréglage", JSON.stringify(A.normaliser({ preset: "clair", couleurs: { fond: "#000000" } })) === '{"preset":"clair"}');
  const lib = A.normaliser({ preset: "libre", couleurs: Object.assign({}, A.PRESETS.clair.couleurs, { accent: "#AABBCC" }), fort: true });
  ok("A21 normaliser : libre en minuscules, fort gardé", lib && lib.couleurs.accent === "#aabbcc" && lib.fort === true);
  ok("A22 normaliser : refus", A.normaliser({ preset: "rose" }) === null && A.normaliser(null) === null
     && A.normaliser({ preset: "libre", couleurs: { fond: "#000000" } }) === null
     && A.normaliser({ preset: "libre", couleurs: Object.assign({}, A.PRESETS.clair.couleurs, { texte: "#fff" }) }) === null);
  ok("A23 couleursDe : le préréglage ou la palette libre", A.couleursDe({ preset: "deeplab" }).fond === "#02060d"
     && A.couleursDe(lib).accent === "#aabbcc" && A.couleursDe(null).fond === A.PRESETS.sombre.couleurs.fond);
}

// ───────────────────────────── B. application ─────────────────────────────
{
  const { A, doc } = monde("fr");
  const lab = documentFactice("lab"), sous = documentFactice("sous"), autre = documentFactice("autre");
  lab.cadres.push(cadre(sous));
  doc.cadres.push(cadre(lab));
  const etranger = new Noeud("iframe");
  Object.defineProperty(etranger, "contentDocument", { get() { throw new Error("origine différente"); } });
  doc.cadres.push(etranger);
  autre.documentElement.setAttribute("data-theme", "light");          // le Cardforge peut poser le sien
  doc.cadres.push(cadre(autre));
  A.appliquer({ preset: "sombre" });
  ok("B1 Deepotus sombre : rien d'écrit", NB(doc) === 0 && NB(lab) === 0 && doc.documentElement.getAttribute("data-theme") === null);
  A.appliquer({ preset: "clair" });
  ok("B2 clair : jetons en style en ligne sur <html> de la coque", PROP(doc, "--bg-base") === "#f2f0ec"
     && PROP(doc, "--ink-strong") === "#171512" && PROP(doc, "color-scheme") === "light");
  ok("B3 clair : data-theme=light sur la coque", doc.documentElement.getAttribute("data-theme") === "light");
  ok("B4 le lab (cadre de même origine) suit", PROP(lab, "--bg-base") === "#f2f0ec"
     && lab.documentElement.getAttribute("data-theme") === "light");
  ok("B5 un cadre dans un cadre suit aussi", PROP(sous, "--accent") === "#a06a00");
  ok("B6 le lab reçoit les jetons « lab » (panneau 3)", PROP(lab, "--bg-panel-3") === A.deriver(A.PRESETS.clair.couleurs, "lab")["--bg-panel-3"]);
  ok("B7 un cadre d'une autre origine est ignoré sans erreur", true);
  A.appliquer({ preset: "deeplab" });
  ok("B8 deeplab : data-theme=dark, jetons remplacés", doc.documentElement.getAttribute("data-theme") === "dark"
     && PROP(doc, "--accent") === "#00e5ff" && PROP(doc, "color-scheme") === "dark");
  A.appliquer({ preset: "sombre" });
  ok("B9 retour au sombre : tout est effacé (coque et labs)", NB(doc) === 0 && NB(lab) === 0 && NB(sous) === 0
     && doc.documentElement.getAttribute("data-theme") === null && lab.documentElement.getAttribute("data-theme") === null);
  ok("B10 un data-theme posé par un lab lui-même n'est pas effacé", autre.documentElement.getAttribute("data-theme") === "light");
  const nouveau = documentFactice("nouveau");
  A.appliquer({ preset: "contraste" });
  const f = cadre(nouveau);
  doc.cadres.push(f);
  A.suivreCadre(f);
  f.emettre("load");
  ok("B11 un lab chargé APRÈS reçoit la palette courante à son chargement", PROP(nouveau, "--bg-base") === "#000000");
}

// ───────────────────────────── C. persistance ─────────────────────────────
await (async () => {
  const LIBRE = { preset: "libre", couleurs: { fond: "#101010", panneau: "#1a1a1a", texte: "#f0f0f0", accent: "#33aaff",
                                               succes: "#44dd88", erreur: "#ff6655" } };
  const m = monde("fr", { stock: { "deepotus.apparence": JSON.stringify({ preset: "clair" }) },
                          reponses: (url, o) => (o.method === "POST" ? { corps: { etat: JSON.parse(o.body) } }
                                                                     : { corps: { etat: LIBRE } }) });
  ok("C1 au chargement, le cache local peint tout de suite", PROP(m.doc, "--bg-base") === "#f2f0ec");
  await dort(20);
  ok("C2 puis le serveur fait foi (GET)", m.appels.some((a) => a.url === "/api/reglages/apparence" && a.methode === "GET")
     && PROP(m.doc, "--accent") === "#33aaff");
  ok("C3 et le cache local est mis à jour", JSON.parse(m.stock["deepotus.apparence"]).preset === "libre");
  m.A.choisir({ preset: "deeplab" });
  ok("C4 un choix s'applique et se garde en local aussitôt", PROP(m.doc, "--accent") === "#00e5ff"
     && JSON.parse(m.stock["deepotus.apparence"]).preset === "deeplab");
  m.A.choisir({ preset: "contraste" });
  await dort(500);
  const posts = m.appels.filter((a) => a.methode === "POST");
  ok("C5 puis part au serveur, une fois (choix rapprochés regroupés)", posts.length === 1
     && posts[0].url === "/api/reglages/apparence" && posts[0].corps.preset === "contraste", JSON.stringify(posts));
  m.emettre("storage", { key: "deepotus.apparence", newValue: JSON.stringify({ preset: "clair" }) });
  ok("C6 un autre onglet change la palette : suivie", PROP(m.doc, "--bg-base") === "#f2f0ec");
  m.emettre("storage", { key: "autre", newValue: "x" });
  ok("C7 une autre clé est ignorée", PROP(m.doc, "--bg-base") === "#f2f0ec");
  m.A.reinitialiser();
  await dort(500);
  ok("C8 réinitialiser : sombre, rien d'écrit, gardé et envoyé", NB(m.doc) === 0
     && JSON.parse(m.stock["deepotus.apparence"]).preset === "sombre"
     && m.appels.filter((a) => a.methode === "POST").pop().corps.preset === "sombre");
  const k = monde("fr", { stock: { "deepotus.apparence": "{pas du json" } });
  ok("C9 un cache illisible ne casse rien", NB(k.doc) === 0);
})();

// ───────────────────────────── D. le panneau ─────────────────────────────
await (async () => {
  for (const lang of ["fr", "en"]) {
    let echoue = false;
    const m = monde(lang, { reponses: (url, o) => (o.method === "POST" ? (echoue ? { ok: false, status: 400,
      corps: { detail: "refusé par le banc" } } : { corps: { etat: JSON.parse(o.body) } }) : { corps: { etat: { preset: "sombre" } } }) });
    await dort(10);
    const hote = new Noeud("div", m.doc);
    m.A.monter(hote);
    const t = texte(hote);
    const L = lang === "fr"
      ? ["Palette", "Deepotus sombre", "Clair", "Contraste élevé", "Deep Lab", "Fond", "Panneau", "Texte", "Accent", "Succès",
         "Erreur", "Aperçu", "Contraste", "Réinitialiser"]
      : ["Palette", "Deepotus dark", "Light", "High contrast", "Deep Lab", "Background", "Panel", "Text", "Accent", "Success",
         "Error", "Preview", "Contrast", "Reset"];
    ok(`D1 ${lang} : libellés`, L.every((x) => t.includes(x)), L.filter((x) => !t.includes(x)));
    ok(`D2 ${lang} : aucune clé manquante`, !t.includes("⟦"), t.match(/⟦[^⟧]*⟧/g));
    if (lang === "en") ok("D3 en : aucun texte français", !/Réinitialiser|Aperçu|Panneau|Fond|Succès|Personnalisée/.test(t), t);
    const presets = parAttr(hote, "data-dz-apparence-preset");
    ok(`D4 ${lang} : quatre préréglages, chacun avec trois pastilles`, presets.length === 4
       && presets.every((b) => b.tagName === "BUTTON" && parAttr(b, "data-dz-apparence-pastille").length === 3));
    ok(`D5 ${lang} : le préréglage actif est marqué`, un(hote, "data-dz-apparence-preset", "sombre").getAttribute("aria-pressed") === "true"
       && un(hote, "data-dz-apparence-preset", "clair").getAttribute("aria-pressed") === "false");
    const couleurs = parAttr(hote, "data-dz-apparence-jeton"), hex = parAttr(hote, "data-dz-apparence-hex");
    ok(`D6 ${lang} : six sélecteurs de couleur et six champs hexadécimaux`, couleurs.length === 6 && hex.length === 6
       && couleurs.every((x) => x.tagName === "INPUT" && x.getAttribute("type") === "color")
       && un(hote, "data-dz-apparence-jeton", "fond").value === "#0a0a0c" && un(hote, "data-dz-apparence-hex", "texte").value === "#f2efe9");
    const ctl = parAttr(hote, "data-dz-apparence-controle");
    ok(`D7 ${lang} : sept contrôles de contraste, tous AA pour le sombre`, ctl.length === 7 && ctl.every((x) => x.getAttribute("data-ok") === "1"));
    const r1 = texte(un(hote, "data-dz-apparence-controle", "texte_fond"));
    ok(`D8 ${lang} : ratio écrit à la ${lang === "fr" ? "française (virgule)" : "anglaise (point)"}`,
       lang === "fr" ? /17,2\d\s?:\s?1/.test(r1) : /17\.2\d\s?:\s?1/.test(r1), r1);
    ok(`D9 ${lang} : un aperçu`, !!un(hote, "data-dz-apparence-apercu"));
    un(hote, "data-dz-apparence-preset", "clair").emettre("click");
    ok(`D10 ${lang} : cliquer un préréglage l'applique à l'app et le marque`, PROP(m.doc, "--bg-base") === "#f2f0ec"
       && un(hote, "data-dz-apparence-preset", "clair").getAttribute("aria-pressed") === "true"
       && un(hote, "data-dz-apparence-jeton", "fond").value === "#f2f0ec");
    const acc = un(hote, "data-dz-apparence-jeton", "accent");
    acc.value = "#0055aa";
    acc.emettre("input");
    ok(`D11 ${lang} : changer une couleur passe en palette « Personnalisée », appliquée en direct`,
       JSON.parse(m.stock["deepotus.apparence"]).preset === "libre" && PROP(m.doc, "--accent") === "#0055aa"
       && JSON.parse(m.stock["deepotus.apparence"]).couleurs.fond === "#f2f0ec"
       && texte(hote).includes(lang === "fr" ? "Personnalisée" : "Custom")
       && presets.every((b) => b.getAttribute("aria-pressed") === "false"));
    ok(`D12 ${lang} : le champ hexadécimal et l'aperçu suivent`, un(hote, "data-dz-apparence-hex", "accent").value === "#0055aa"
       && /0055aa/.test(tous(un(hote, "data-dz-apparence-apercu")).map((x) => x.getAttribute("style") || "").join(" ")));
    const txt = un(hote, "data-dz-apparence-jeton", "texte");
    txt.value = "#e0e0e0";
    txt.emettre("input");
    ok(`D13 ${lang} : un texte illisible est signalé (AA non atteint) et une alerte s'affiche`,
       un(hote, "data-dz-apparence-controle", "texte_panneau").getAttribute("data-ok") === "0"
       && !!un(hote, "data-dz-apparence-alerte") && un(hote, "data-dz-apparence-alerte").textContent.length > 5);
    const h = un(hote, "data-dz-apparence-hex", "succes");
    h.value = "vert";
    h.emettre("change");
    ok(`D14 ${lang} : un hexadécimal illisible est refusé, rien ne change`,
       JSON.parse(m.stock["deepotus.apparence"]).couleurs.succes === "#1f7a5c" && h.value === "#1f7a5c"
       && un(hote, "data-dz-apparence-statut").textContent.length > 3);
    h.value = "2E8B57";
    h.emettre("change");
    ok(`D15 ${lang} : un hexadécimal sans # est accepté`, JSON.parse(m.stock["deepotus.apparence"]).couleurs.succes === "#2e8b57");
    echoue = true;
    un(hote, "data-dz-apparence-preset", "deeplab").emettre("click");
    await dort(500);
    ok(`D16 ${lang} : un enregistrement refusé est dit`, texte(un(hote, "data-dz-apparence-statut")).includes("refusé par le banc"));
    echoue = false;
    un(hote, "data-dz-apparence-action", "reinitialiser").emettre("click");
    await dort(500);
    ok(`D17 ${lang} : « Réinitialiser » rend Deepotus sombre`, NB(m.doc) === 0
       && un(hote, "data-dz-apparence-preset", "sombre").getAttribute("aria-pressed") === "true"
       && un(hote, "data-dz-apparence-jeton", "fond").value === "#0a0a0c"
       && !un(hote, "data-dz-apparence-alerte"));
    const hote2 = new Noeud("div", m.doc);
    m.A.monter(hote2);
    m.A.choisir({ preset: "clair" });
    ok(`D18 ${lang} : un panneau monté suit un choix fait ailleurs`, un(hote2, "data-dz-apparence-preset", "clair")
       .getAttribute("aria-pressed") === "true");
    const premier = hote2.children[0], champ = un(hote2, "data-dz-apparence-hex", "texte");
    m.A.monter(hote2);
    m.A.monter(hote2);
    ok(`D20 ${lang} : la ref rappelée à chaque rendu garde LE MÊME panneau (champ en cours de saisie intact)`,
       parAttr(hote2, "data-dz-apparence-panneau").length === 1 && hote2.children.length === 1
       && hote2.children[0] === premier && un(hote2, "data-dz-apparence-hex", "texte") === champ);
    un(hote2, "data-dz-apparence-preset", "contraste").emettre("click");
    const f2 = un(hote2, "data-dz-apparence-jeton", "erreur");
    f2.value = "#ff8877";
    f2.emettre("input");
    const st2 = JSON.parse(m.stock["deepotus.apparence"]);
    ok(`D21 ${lang} : une couleur changée depuis « Contraste élevé » garde ses encres fortes`,
       st2.preset === "libre" && st2.fort === true && st2.couleurs.fond === "#000000", JSON.stringify(st2));
  }
  ok("D19 aucun innerHTML", INNER.length === 0, INNER);
})();

if (echecs.length) {
  console.log(echecs.map((e) => "  FAIL  " + e).join("\n"));
  console.log(`${n - echecs.length} PASS / ${echecs.length} FAIL`);
  process.exit(1);
}
console.log(`${n} PASS / 0 FAIL`);
