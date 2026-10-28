// t352 (27/10/2026) — dz-veille.js : l'écran « Veille » (3e onglet du tiroir F1), joué sur un DOM simulé.
// Séries : sans_espace, vide_puis_collecte, conflit_409, rapport_rendu (matrice, douleurs, angles, demandes, limites),
// citation_hostile_en_texte, anglais, sonde_en_cours, import (200, 413), demontage.
// Lancer : node frontend/shared/qa/veille.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-veille.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const J = (x) => JSON.parse(JSON.stringify(x));
const tick = () => new Promise((r) => setTimeout(r, 10));

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; }
  get firstChild() { return this.children[0] || null; }
  get parentNode() { return this.parent; }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(v) { throw new Error("innerHTML interdit"); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  focus() {}
  fire(t) { (this.ec[t] || []).forEach((f) => f({ type: t, target: this, preventDefault() {} })); }
  click() { this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tous = (r, p) => [...r.tous()].filter(p);
const marque = (r, v) => tous(r, (x) => x.attrs["data-dz-veille"] === v)[0];

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const dzTde = (lang) => (cle, vars) => {
  const e = D[cle];
  if (!e) return cle;
  let s = e[lang] || e.fr;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
  return s;
};
const reponse = (status, json) => ({ ok: status >= 200 && status < 300, status, json: async () => J(json === undefined ? {} : json) });

function monde({ lang = "fr", routes = {} } = {}) {
  const appels = [], minuteries = [];
  const win = {
    dzT: dzTde(lang), dzLang: () => lang,
    fetch: async (url, init = {}) => {
      const m = init.method || "GET";
      appels.push({ url: String(url), methode: m, corps: init.body ? JSON.parse(init.body) : undefined });
      const f = routes[m + " " + url];
      return f ? f(init.body ? JSON.parse(init.body) : undefined) : reponse(404, { detail: "absent : " + url });
    },
  };
  const doc = { createElement: (t) => new Noeud(t), head: new Noeud("head"), documentElement: new Noeud("html") };
  const ctx = { window: win, document: doc, console, setTimeout: (f, ms) => { minuteries.push({ f, ms }); return minuteries.length; },
    clearTimeout: (i) => { if (minuteries[i - 1]) minuteries[i - 1].annulee = true; } };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { win, doc, appels, minuteries, DzVeille: win.DzVeille, hote: new Noeud("div") };
}

const RAPPORT = {
  version: 1, date: "2026-10-27", espace_id: "e1", classement: "auto",
  volumes: { brut: 120, gardes: 9, par_source: { hn: 5, appstore: 4 }, par_concurrent: { runway: 6, kling: 3 }, periode: ["2026-01-02", "2026-10-01"] },
  matrice: { runway: { prix_credits: { f: 3, F: 1, i: 2 }, coherence: { f: 1, F: 0, i: 1 } }, kling: { prix_credits: { f: 1, F: 0, i: 1 }, qualite_sortie: { f: 0, F: 2, i: 0 } } },
  douleurs: [{ theme: "prix_credits", n: 4, n3: 1, auteurs: 4, concurrents: ["runway", "kling"], chez_nous: "regle",
    preuve: { fr: "Réglages › Dépenses", en: "Settings › Spending" },
    citations: [{ texte: "<img src=x onerror=alert(1)> credits burn", url: "https://news.ycombinator.com/item?id=1", date: "2026-06-01", source: "hn", concurrent: "runway" },
      { texte: "lien piégé", url: "javascript:alert(1)", date: "2026-06-02", source: "hn", concurrent: "kling" }] }],
  angles: [{ theme: "prix_credits", n: 4, preuve: { fr: "Réglages › Dépenses", en: "Settings › Spending" },
    angle: { fr: "Vous voyez le prix avant de cliquer.", en: "You see the price before you click." } }],
  forces: [{ theme: "qualite_sortie", n: 2, concurrents: ["kling"], citations: [] }],
  demandes: [{ theme: "apprentissage", n: 3, auteurs: 3, citations: [], chez_nous: "inconnu", statut: "a_decider" }],
  limites: ["classement automatique par mots-clés : à relire avant de citer"],
};
const FR = dzTde("fr"), EN = dzTde("en");

// ---- sans_espace ---------------------------------------------------------------------------------------------------
{
  const m = monde();
  m.DzVeille.monter(m.hote, {});
  await tick();
  ok("1.1 sans espace : message, aucune requête", marque(m.hote, "sans-espace") && m.appels.length === 0);
  ok("1.2 sans espace : boutons grisés", marque(m.hote, "lancer").hasAttribute("disabled") && marque(m.hote, "importer").hasAttribute("disabled"));
}

// ---- vide_puis_collecte, conflit_409 ------------------------------------------------------------------------------------
{
  let collectes = 0, etat = null;
  const m = monde({ routes: {
    "GET /api/veille/e1": () => reponse(200, { etat, rapport: null, veilles: [] }),
    "POST /api/veille/e1/collectes": () => { collectes++; if (collectes > 1) return reponse(409, { detail: "x" }); etat = { etat: "en_cours", date: "2026-10-27", journal: ["hn runway : +12"] }; return reponse(202, { date: "2026-10-27" }); },
  } });
  m.DzVeille.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("2.1 aucune veille : état vide", marque(m.hote, "vide") && marque(m.hote, "vide").textContent === FR("veille.vide.aucune"));
  ok("2.2 la note dit lecture seule et gratuit", marque(m.hote, "note").textContent === FR("veille.collecte.note"));
  marque(m.hote, "lancer").click(); await tick(); await tick();
  ok("2.3 lancer : POST collectes", m.appels.some((a) => a.methode === "POST" && a.url === "/api/veille/e1/collectes"));
  ok("2.4 en cours : état et dernière ligne du journal", marque(m.hote, "etat").textContent.includes(FR("veille.etat.en_cours", { date: "2026-10-27" }))
    && marque(m.hote, "etat").textContent.includes("hn runway : +12"), marque(m.hote, "etat").textContent);
  ok("2.5 en cours : bouton grisé, sonde programmée", marque(m.hote, "lancer").hasAttribute("disabled") && m.minuteries.some((t) => !t.annulee && t.ms === 3000));
  etat = { etat: "fini", date: "2026-10-27" };
  m.minuteries.filter((t) => !t.annulee).pop().f(); await tick();
  ok("2.6 la sonde relit : fini", marque(m.hote, "etat").textContent === FR("veille.etat.fini", { date: "2026-10-27" }) && !marque(m.hote, "lancer").hasAttribute("disabled"));
  marque(m.hote, "lancer").click(); await tick(); await tick();
  ok("2.7 conflit_409 : message en erreur", marque(m.hote, "etat").hasAttribute("data-erreur")
    && marque(m.hote, "etat").textContent === FR("veille.etat.conflit"), marque(m.hote, "etat").textContent);
}
{
  const m = monde({ routes: {
    "GET /api/veille/e1": () => reponse(200, { etat: null, rapport: null, veilles: [] }),
    "POST /api/veille/e1/collectes": () => reponse(409, { detail: "x" }),
  } });
  m.DzVeille.monter(m.hote, { espace_id: "e1" });
  await tick();
  marque(m.hote, "lancer").click(); await tick();
  ok("2.8 conflit_409 dit tel quel", marque(m.hote, "etat").hasAttribute("data-erreur") && marque(m.hote, "etat").textContent === FR("veille.etat.conflit"));
}

// ---- rapport_rendu, citation_hostile_en_texte ----------------------------------------------------------------------------
{
  const m = monde({ routes: { "GET /api/veille/e1": () => reponse(200, { etat: { etat: "fini", date: "2026-10-27" }, rapport: RAPPORT, veilles: [] }) } });
  m.DzVeille.monter(m.hote, { espace_id: "e1" });
  await tick();
  for (const s of ["bref", "matrice", "douleurs", "angles", "forces", "demandes", "limites"]) ok("3.1 section " + s, !!marque(m.hote, s));
  ok("3.2 classement automatique signalé", marque(m.hote, "classement").textContent === FR("veille.classement.auto"));
  const cellules = tous(marque(m.hote, "matrice"), (x) => x.tagName === "TD");
  ok("3.3 matrice : f/F", cellules.some((c) => c.textContent === "3/1"), cellules.map((c) => c.textContent).join(","));
  ok("3.4 matrice : le max de la ligne en gras", cellules.filter((c) => c.hasAttribute("data-max")).map((c) => c.textContent).includes("3/1"));
  const th = tous(marque(m.hote, "matrice"), (x) => x.tagName === "TH").map((x) => x.textContent);
  ok("3.5 matrice : thèmes traduits, colonnes vides absentes", th.includes(FR("veille.theme.prix_credits")) && !th.includes(FR("veille.theme.droits_licence")), th.join("|"));
  ok("3.6 matrice : runway d'abord (le plus de verbatims)", th.indexOf("runway") < th.indexOf("kling"));
  const dl = marque(m.hote, "douleurs");
  ok("3.7 douleur : compte et preuve", dl.textContent.includes(FR("veille.douleur.compte", { n: 4, n3: 1, auteurs: 4, concurrents: "runway, kling" }))
    && dl.textContent.includes("Réglages › Dépenses"), dl.textContent);
  ok("3.8 citation_hostile_en_texte : aucun IMG, le texte est là", !tous(m.hote, (x) => x.tagName === "IMG").length && dl.textContent.includes("<img src=x onerror=alert(1)>"));
  const liens = tous(dl, (x) => x.tagName === "A");
  ok("3.9 seul le lien https est cliquable, en noopener", liens.length === 1 && liens[0].attrs.href === "https://news.ycombinator.com/item?id=1"
    && liens[0].attrs.rel === "noopener noreferrer" && liens[0].attrs.target === "_blank", JSON.stringify(liens.map((l) => l.attrs)));
  ok("3.10 angle en français", marque(m.hote, "angles").textContent.includes("Vous voyez le prix avant de cliquer."));
  ok("3.11 demandes : la règle « à décider »", marque(m.hote, "demandes").textContent.includes(FR("veille.demande.regle"))
    && marque(m.hote, "demandes").textContent.includes(FR("veille.demande.ligne", { theme: FR("veille.theme.apprentissage"), n: 3 })));
  ok("3.12 aucun bouton qui publie ou écrit", !tous(m.hote, (x) => x.tagName === "BUTTON").some((b) => /publi|envoy|send|post/i.test(b.textContent)));
}
{
  const m = monde({ lang: "en", routes: { "GET /api/veille/e1": () => reponse(200, { etat: null, rapport: { ...RAPPORT, classement: "importe" }, veilles: [] }) } });
  m.DzVeille.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("4.1 anglais : angle, preuve, thème, classement", marque(m.hote, "angles").textContent.includes("You see the price before you click.")
    && marque(m.hote, "douleurs").textContent.includes("Settings › Spending") && marque(m.hote, "douleurs").textContent.includes(EN("veille.theme.prix_credits"))
    && marque(m.hote, "classement").textContent === EN("veille.classement.importe"));
  ok("4.2 anglais : boutons", marque(m.hote, "lancer").textContent === EN("veille.bouton.lancer"));
}

// ---- import (200, 413), demontage --------------------------------------------------------------------------------------
{
  let rapport = null, statut = 200;
  const m = monde({ routes: {
    "GET /api/veille/e1": () => reponse(200, { etat: null, rapport, veilles: [] }),
    "POST /api/veille/e1/importer": (corps) => { if (statut !== 200) return reponse(statut, { detail: "trop" }); rapport = RAPPORT; return reponse(200, { date: "2026-10-27", lignes: 9, ignorees: 1 }); },
  } });
  const inst = m.DzVeille.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("5.1 le champ est caché", marque(m.hote, "dossier").hasAttribute("hidden"));
  marque(m.hote, "importer").click();
  ok("5.2 Importer… montre le champ", !marque(m.hote, "dossier").hasAttribute("hidden") && !marque(m.hote, "valider-import").hasAttribute("hidden"));
  marque(m.hote, "valider-import").click(); await tick();
  ok("5.3 champ vide : aucune requête", !m.appels.some((a) => a.url.endsWith("/importer")));
  marque(m.hote, "dossier").value = "  C:\\Campagnes\\_veille\\2026-10-27  ";
  marque(m.hote, "valider-import").click(); await tick(); await tick(); await tick();
  const ap = m.appels.find((a) => a.url === "/api/veille/e1/importer");
  ok("5.4 POST importer avec le dossier nettoyé", ap && ap.corps.dossier === "C:\\Campagnes\\_veille\\2026-10-27", JSON.stringify(ap));
  ok("5.5 importé : rapport affiché et message", !!marque(m.hote, "douleurs") && marque(m.hote, "etat").textContent === FR("veille.import.fait", { n: 9, ignorees: 1, date: "2026-10-27" }), marque(m.hote, "etat").textContent);
  statut = 413;
  marque(m.hote, "importer").click();
  marque(m.hote, "dossier").value = "x";
  marque(m.hote, "valider-import").click(); await tick(); await tick();
  ok("5.6 413 : trop gros", marque(m.hote, "etat").textContent === FR("veille.erreur.trop_gros") && marque(m.hote, "etat").hasAttribute("data-erreur"));
  inst.demonter();
  ok("5.7 démonté : plus rien dans l'hôte", m.hote.children.length === 0);
}

// ---- relecture finale : deux relectures qui se chevauchent ne doublent rien ----------------------------------------------
{
  const m = monde({ routes: { "GET /api/veille/e1": async () => { await tick(); return reponse(200, { etat: { etat: "en_cours", date: "2026-10-27", journal: [] }, rapport: RAPPORT, veilles: [] }); } } });
  const inst = m.DzVeille.monter(m.hote, { espace_id: "e1" });
  inst.recharger(); inst.recharger();
  await tick(); await tick(); await tick(); await tick();
  ok("7.1 relectures chevauchées : une seule section douleurs", tous(m.hote, (x) => x.attrs["data-dz-veille"] === "douleurs").length === 1,
    tous(m.hote, (x) => x.attrs["data-dz-veille"] === "douleurs").length);
  ok("7.2 une seule sonde vivante", m.minuteries.filter((t) => !t.annulee).length === 1, m.minuteries.filter((t) => !t.annulee).length);
  inst.demonter();
}

// ---- t368 : le volet « Concurrents » ---------------------------------------------------------------------------------
{
  const K = { pubs: { runway: [{ texte: "<img src=x onerror=alert(1)> Gen-4", debut: "2026-10-10", lien: "javascript:alert(1)" },
                               { texte: "Pro plan", debut: "", lien: "https://www.facebook.com/ads/library/?id=2" }] },
    pages: [{ concurrent: "runway", url: "https://runwayml.com/pricing", change: true, diff: "-Standard 12 $\n+Standard 15 $" },
            { concurrent: "kling", url: "https://kling.ai/pricing", change: false, diff: "" }],
    serp: { mots_cles: { "générateur vidéo ia": [{ rang: 1, domaine: "capcut.com", concurrent: null }, { rang: 3, domaine: "runwayml.com", concurrent: "runway" }],
                         "studio ia": [{ rang: 2, domaine: "blog.example", concurrent: null }] } } };
  const m = monde({ routes: { "GET /api/veille/e1": () => reponse(200, { etat: null, rapport: RAPPORT, veilles: [] }),
                              "GET /api/veille/e1/concurrents": () => reponse(200, K) } });
  m.DzVeille.monter(m.hote, { espace_id: "e1" });
  await tick(); await tick(); await tick();
  const v = marque(m.hote, "concurrents");
  ok("8.1 volet affiché après le rapport", !!v && v.textContent.includes(FR("veille.concurrents.pubs", { nom: "runway", n: 2 })), v && v.textContent);
  ok("8.2 page changée : le diff en texte", v && v.textContent.includes("+Standard 15 $") && !v.textContent.includes("kling.ai"), v && v.textContent);
  ok("8.3 SERP : rang des concurrents, ou aucun", v && v.textContent.includes(FR("veille.concurrents.serp", { mot: "générateur vidéo ia", rangs: "runway #3" }))
    && v.textContent.includes(FR("veille.concurrents.serp_aucun", { mot: "studio ia" })), v && v.textContent);
  ok("8.4 texte hostile jamais interprété, lien https seul cliquable", v && !tous(v, (x) => x.tagName === "IMG").length
    && tous(v, (x) => x.tagName === "A").map((a) => a.attrs.href).join() === "https://www.facebook.com/ads/library/?id=2");
  const m2 = monde({ routes: { "GET /api/veille/e1": () => reponse(200, { etat: null, rapport: RAPPORT, veilles: [] }) } });
  m2.DzVeille.monter(m2.hote, { espace_id: "e1" });
  await tick(); await tick(); await tick();
  ok("8.5 rien à montrer (404) : pas de volet, le rapport reste", !marque(m2.hote, "concurrents") && !!marque(m2.hote, "douleurs"));
}

// ---- les clés employées existent, sans mot « publier » ------------------------------------------------------------------
{
  const cles = [...new Set((SRC.match(/"veille\.[a-z_]+\.[a-z_]+"/g) || []).map((s) => s.slice(1, -1)))];
  const manquent = cles.filter((k) => !(D[k] && D[k].fr && D[k].en));
  ok("6.1 chaque clé employée est traduite", cles.length > 20 && !manquent.length, manquent.join(", "));
  ok("6.2 aucune route d'écriture hors collecte et import", !/\/api\/(planif|scheduler|generate|agent)/.test(SRC));
}

if (echecs.length) {
  console.error("ÉCHECS (" + echecs.length + "/" + n + ") :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("veille : OK (" + n + " vérifications)");
process.exit(0);
