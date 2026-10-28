// t353 (27/10/2026) — dz-prospects.js : l'écran « Prospects » (4e onglet du tiroir F1), joué sur un DOM simulé.
// Séries : sans_espace, liste_et_filtres, vide, ajout (refus email_perso puis 201), transitions_selon_statut, note_rdv,
// texte_hostile, export, effacement_saisie_erronee, opposition_saisie, oppose_sans_gestes, anglais, demontage.
// Lancer : node frontend/shared/qa/prospects.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-prospects.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const J = (x) => JSON.parse(JSON.stringify(x));
const tick = () => new Promise((r) => setTimeout(r, 10));

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; this.checked = false; }
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
const marque = (r, v) => tous(r, (x) => x.attrs["data-dz-prospects"] === v)[0];
const marques = (r, v) => tous(r, (x) => x.attrs["data-dz-prospects"] === v);

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
const FR = dzTde("fr"), EN = dzTde("en");
const reponse = (status, json) => ({ ok: status >= 200 && status < 300, status, json: async () => J(json === undefined ? {} : json) });

function monde({ lang = "fr", routes = {} } = {}) {
  const appels = [];
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
  const ctx = { window: win, document: doc, console, setTimeout, Date };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { win, appels, DzProspects: win.DzProspects, hote: new Noeud("div") };
}

const FICHE = (o = {}) => ({ id: "pr_00000001", nom: "Léa Martin", entreprise: "Studio Lune", role: "gérante", statut: "repondu",
  offre: "prestation", score: 70, base_legale: "interet_legitime_b2b", purge_le: "2029-10-27", signal: "veut des clips",
  source: { type: "web", url: "https://studio-lune.fr/contact", date: "2026-10-20", detail: "" },
  canaux: [{ type: "email", valeur: "lea@studio-lune.fr" }], consentements: [], historique: [{ quand: "2026-10-27T10:00:00", quoi: "creation", detail: "", qui: "utilisateur" }],
  prochaine_action: { texte: "relancer", le: "2026-11-03" }, dernier_contact_entrant: null, espace_demo: null, ...o });
const LISTE = { prospects: [FICHE(), FICHE({ id: "pr_00000002", nom: "Tom", entreprise: "", statut: "perdu", score: null, prochaine_action: null })],
  compte_par_statut: { repondu: 1, perdu: 1 }, oppositions: 3 };

// ---- sans_espace ---------------------------------------------------------------------------------------------------
{
  const m = monde();
  m.DzProspects.monter(m.hote, {});
  await tick();
  ok("1 sans espace : un message, aucun appel", marque(m.hote, "sans-espace")?.textContent === FR("prospects.vide.sans_espace") && m.appels.length === 0);
}

// ---- liste_et_filtres --------------------------------------------------------------------------------------------------
{
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, LISTE) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  const lignes = marques(m.hote, "ligne");
  ok("2.1 deux lignes", lignes.length === 2, lignes.length);
  ok("2.2 nom · entreprise, statut traduit", lignes[0].textContent.includes("Léa Martin · Studio Lune") && lignes[0].textContent.includes(FR("prospects.statut.repondu")));
  ok("2.3 méta : offre, score, prochaine action, purge", lignes[0].textContent.includes(FR("prospects.offre.prestation")) && lignes[0].textContent.includes("score 70")
    && lignes[0].textContent.includes("relancer") && lignes[0].textContent.includes("2029-10-27"));
  ok("2.4 registre global affiché", marque(m.hote, "registre").textContent === FR("prospects.registre.compte", { n: 3 }));
  ok("2.5 pastilles : tous + statuts présents seulement", marque(m.hote, "filtre-tous") && marque(m.hote, "filtre-repondu") && marque(m.hote, "filtre-perdu") && !marque(m.hote, "filtre-client"));
  marque(m.hote, "filtre-perdu").click(); await tick();
  ok("2.6 filtre perdu", marques(m.hote, "ligne").length === 1 && marque(m.hote, "filtre-perdu").attrs["aria-pressed"] === "true");
  marque(m.hote, "filtre-tous").click(); await tick();
  ok("2.7 retour à tous", marques(m.hote, "ligne").length === 2);
}

// ---- registre_illisible (relecture I2) ------------------------------------------------------------------------------
{
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, { ...LISTE, registre_mis_de_cote: 1 }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("2.8 registre mis de côté : averti", marque(m.hote, "registre-illisible")?.textContent === FR("prospects.registre.illisible", { n: 1 }));
}

// ---- vide -----------------------------------------------------------------------------------------------------------
{
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, { prospects: [], compte_par_statut: {}, oppositions: 0 }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("3 état vide", marque(m.hote, "vide")?.textContent === FR("prospects.vide.aucun"));
}

// ---- ajout ----------------------------------------------------------------------------------------------------------
{
  let essai = 0, liste = { prospects: [], compte_par_statut: {}, oppositions: 0 };
  const m = monde({ routes: {
    "GET /api/prospects/e1": () => reponse(200, liste),
    "POST /api/prospects/e1": (c) => {
      essai++;
      if (essai === 1) return reponse(409, { detail: { code: "email_perso", message: "l'intérêt légitime B2B exige une adresse professionnelle" } });
      const f = FICHE({ id: "pr_00000009", statut: "propose", nom: c.nom });
      liste = { prospects: [f], compte_par_statut: { propose: 1 }, oppositions: 0 };
      return reponse(201, f);
    } } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marque(m.hote, "ajouter").click(); await tick();
  ok("4.1 formulaire, aide de la base légale", !!marque(m.hote, "formulaire") && marque(m.hote, "aide-base").textContent === FR("prospects.aide.base"));
  ok("4.2 date du jour par défaut, base à choisir", /^\d{4}-\d{2}-\d{2}$/.test(marque(m.hote, "champ-date").value) && marque(m.hote, "champ-base").value === "");
  marque(m.hote, "champ-nom").value = "Zoé";
  marque(m.hote, "champ-email").value = "zoe@gmail.com";
  marque(m.hote, "champ-url").value = "https://agence-z.fr";
  marque(m.hote, "champ-base").value = "interet_legitime_b2b";
  marque(m.hote, "formulaire").fire("submit"); await tick();
  const post = m.appels.filter((a) => a.methode === "POST")[0];
  ok("4.3 corps envoyé : source, base, canaux", post && post.corps.source.type === "web" && post.corps.source.url === "https://agence-z.fr"
    && post.corps.base_legale === "interet_legitime_b2b" && post.corps.canaux.length === 1 && post.corps.canaux[0].valeur === "zoe@gmail.com"
    && post.corps.score === null, JSON.stringify(post && post.corps));
  const err = marque(m.hote, "erreur");
  ok("4.4 refus email_perso affiché avec son code", err.attrs["data-code"] === "email_perso" && err.textContent.includes("adresse professionnelle"));
  marque(m.hote, "champ-base").value = "consentement";
  marque(m.hote, "formulaire").fire("submit"); await tick(); await tick();
  ok("4.5 créé : la fiche s'ouvre", marque(m.hote, "fiche")?.attrs["data-id"] === "pr_00000009");
}

// ---- transitions_selon_statut, note_rdv, texte_hostile, export, effacement ------------------------------------------
{
  let fiche = FICHE({ nom: "<img src=x onerror=alert(1)>", source: { type: "web", url: "javascript:alert(1)", date: "2026-10-20" } });
  const m = monde({ routes: {
    "GET /api/prospects/e1": () => reponse(200, { prospects: [fiche], compte_par_statut: { [fiche.statut]: 1 }, oppositions: 0 }),
    "POST /api/prospects/e1/pr_00000001/statut": (c) => { fiche = { ...fiche, statut: c.statut }; return reponse(200, { prospect: fiche, note: "plafond_espaces" }); },
    "DELETE /api/prospects/e1/pr_00000001?inscrire_opposition=0": () => { return reponse(200, { efface: "pr_00000001" }); },
  } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marques(m.hote, "ligne")[0].click(); await tick();
  const tr = marque(m.hote, "transitions");
  const noms = tr.children.map((b) => b.attrs["data-dz-prospects"]);
  ok("5.1 répondu : rdv, client, perdu (l'opposition a son propre bouton)", noms.join() === "statut-rdv,statut-client,statut-perdu", noms.join());
  ok("5.2 texte hostile posé en texte", marque(m.hote, "fiche").textContent.includes("<img src=x onerror=alert(1)>"));
  ok("5.3 source javascript: jamais un lien", !tous(marque(m.hote, "source"), (x) => x.tagName === "A").length);
  const exp = marque(m.hote, "exporter");
  ok("5.4 export : lien de téléchargement", exp.tagName === "A" && exp.attrs.href === "/api/prospects/e1/pr_00000001/export" && exp.attrs.download === "prospect-pr_00000001.json");
  marque(m.hote, "statut-rdv").click(); await tick(); await tick();
  ok("5.5 rdv : la note du serveur est traduite", marque(m.hote, "note")?.textContent === FR("prospects.note.plafond_espaces")
    && marque(m.hote, "transitions").children.map((b) => b.attrs["data-dz-prospects"]).join() === "statut-client,statut-perdu");
  marque(m.hote, "effacer").click();
  marque(m.hote, "effacer-erronee").checked = true;
  marque(m.hote, "effacer-confirmer").click(); await tick();
  ok("5.6 effacement « saisie erronée » : sans inscription", m.appels.some((a) => a.methode === "DELETE" && a.url.endsWith("?inscrire_opposition=0")));
  ok("5.7 aucun appel ne publie ni n'envoie", !m.appels.some((a) => /schedule|whatsapp|fire|envoyer/i.test(a.url)));
}

// ---- oppose_sans_gestes ---------------------------------------------------------------------------------------------------
{
  const f = FICHE({ statut: "oppose", nom: "", entreprise: "", canaux: [] });
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, { prospects: [f], compte_par_statut: { oppose: 1 }, oppositions: 1 }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marques(m.hote, "ligne")[0].click(); await tick();
  ok("6 opposé : ni transition, ni modification, ni consentement ; export et effacement restent",
    !marque(m.hote, "transitions") && !marque(m.hote, "modifier") && !marque(m.hote, "consent-ajouter") && !marque(m.hote, "opposer")
    && !!marque(m.hote, "exporter") && !!marque(m.hote, "effacer") && marque(m.hote, "fiche").textContent.includes(FR("prospects.fiche.anonyme")));
}

// ---- opposition_saisie ------------------------------------------------------------------------------------------------
{
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, LISTE),
    "POST /api/prospects/oppositions": (c) => reponse(200, { inscrit: c.identifiant === "paul@agence-m.fr" }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marque(m.hote, "opposition-saisir").click(); await tick();
  marque(m.hote, "opposition-identifiant").value = "paul@agence-m.fr";
  marque(m.hote, "opposition-inscrire").click(); await tick();
  ok("7 opposition inscrite", marque(m.hote, "opposition-resultat").textContent === FR("prospects.opposition.inscrite")
    && m.appels.some((a) => a.url === "/api/prospects/oppositions" && a.corps.identifiant === "paul@agence-m.fr"));
}

// ---- mineurs (t353 suite, 28/10) : serveur injoignable, nom de la démo, retrait du registre ---------------------------
{
  const m = monde({ routes: { "GET /api/prospects/e1": () => { throw new TypeError("Failed to fetch"); } } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  const err = tous(m.hote, (x) => x.attrs.class === "dzProspectsErreur")[0];
  ok("9.1 serveur injoignable : l'erreur est dite", err && err.textContent === FR("prospects.erreur.reseau"), err && err.textContent);
}
{
  const f = FICHE({ statut: "rdv", espace_demo: "esp_0000abcd" });
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, { prospects: [f], compte_par_statut: { rdv: 1 }, oppositions: 0,
    espaces_demo: { esp_0000abcd: "Démo · Studio Lune" } }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marques(m.hote, "ligne")[0].click(); await tick();
  const d = marque(m.hote, "espace-demo");
  ok("9.2 la fiche nomme l'espace démo, pas son id", d && d.textContent.includes("Démo · Studio Lune") && !d.textContent.includes("esp_0000abcd"), d && d.textContent);
}
{
  const m = monde({ routes: { "GET /api/prospects/e1": () => reponse(200, LISTE),
    "POST /api/prospects/oppositions/retirer": (c) => c.identifiant === "olga@agence-o.fr"
      ? reponse(409, { detail: "cette personne s'est opposée elle-même" }) : reponse(200, { retire: c.identifiant === "erreur@exemple.fr" }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marque(m.hote, "opposition-saisir").click(); await tick();
  marque(m.hote, "opposition-identifiant").value = "erreur@exemple.fr";
  marque(m.hote, "opposition-retirer").click(); await tick();
  ok("9.3 saisie erronée retirée", marque(m.hote, "opposition-resultat").textContent === FR("prospects.opposition.retiree")
    && m.appels.some((a) => a.url === "/api/prospects/oppositions/retirer" && a.corps.identifiant === "erreur@exemple.fr"));
  marque(m.hote, "opposition-identifiant").value = "personne@exemple.fr";
  marque(m.hote, "opposition-retirer").click(); await tick();
  ok("9.4 absent du registre : dit", marque(m.hote, "opposition-resultat").textContent === FR("prospects.opposition.absente"));
  marque(m.hote, "opposition-identifiant").value = "olga@agence-o.fr";
  marque(m.hote, "opposition-retirer").click(); await tick();
  ok("9.5 opposition de la personne : le refus est dit", marque(m.hote, "erreur").textContent.includes("opposée elle-même"));
}

// ---- anglais, demontage -----------------------------------------------------------------------------------------------
{
  const m = monde({ lang: "en", routes: { "GET /api/prospects/e1": () => reponse(200, LISTE) } });
  const c = m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("8.1 anglais", marque(m.hote, "ajouter").textContent === EN("prospects.bouton.ajouter") && EN("prospects.bouton.ajouter") !== FR("prospects.bouton.ajouter")
    && marques(m.hote, "ligne")[0].textContent.includes(EN("prospects.statut.repondu")));
  c.demonter();
  ok("8.2 démonté", m.hote.children.length === 0);
}

if (echecs.length) {
  console.error("ÉCHECS (" + echecs.length + "/" + n + ") :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("prospects : OK (" + n + " vérifications)");
process.exit(0);
