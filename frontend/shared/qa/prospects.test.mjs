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

// ---- t354 : origine agent, information art. 14, qualification, recherche web -------------------------------------------
{
  const Q = { base: 45, ajustement: 10, raison: "studio actif", qui: "agent", le: "2026-10-28T10:00:00",
    details: [{ critere: "source_web", points: 15 }, { critere: "adresse_pro", points: 10 }],
    canaux_possibles: [{ canal: "email", mode: "auto_apres_porte", raison: "x" }, { canal: "x", mode: "manuel", raison: "y" }] };
  let fiche = FICHE({ statut: "propose", par_agent: true, informer_avant: "2026-01-01", score: 55, qualification: Q });
  const appels = [];
  const m = monde({ routes: {
    "GET /api/prospects/e1": () => reponse(200, { prospects: [fiche], compte_par_statut: { propose: 1 }, oppositions: 0 }),
    "POST /api/prospects/e1/pr_00000001/qualifier": (c) => { appels.push(c); fiche = { ...fiche, score: 45, qualification: { ...Q, ajustement: 0, raison: "", qui: "utilisateur" } }; return reponse(200, fiche); },
    "GET /api/prospects/recherche": () => reponse(200, { fournisseur: "anthropic", fournisseurs: [
      { id: "anthropic", configure: true, prix_usd: 0.01 }, { id: "tavily", configure: false, prix_usd: 0.008 },
      { id: "exa", configure: false, prix_usd: 0.007 }, { id: "serper", configure: false, prix_usd: 0.001 }] }),
    "POST /api/prospects/recherche/fournisseur": (c) => { appels.push(c); return reponse(200, { fournisseur: c.fournisseur, fournisseurs: [] }); },
    "POST /api/prospects/recherche/cle": (c) => { appels.push(c); return reponse(200, { fournisseur: "tavily", fournisseurs: [], ou: "coffre" }); },
  } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  ok("10.1 la ligne dit « proposé par l'agent »", marques(m.hote, "ligne")[0].textContent.includes(FR("prospects.liste.par_agent")));
  marques(m.hote, "ligne")[0].click(); await tick();
  const inf = marque(m.hote, "informer");
  ok("10.2 information art. 14 : date dite, en alerte une fois passée", inf && inf.textContent === FR("prospects.fiche.informer", { le: "2026-01-01" })
    && inf.attrs.class === "dzProspectsErreur", inf && inf.textContent);
  const q = marque(m.hote, "qualification");
  ok("10.3 qualification : score, barème, ajustement, raison, critères traduits", q && q.textContent.includes(FR("prospects.qualif.score", { score: 55, base: 45, ajustement: "+10" }))
    && q.textContent.includes("studio actif") && q.textContent.includes(FR("prospects.critere.source_web")), q && q.textContent);
  ok("10.4 canaux possibles : X en envoi manuel", q && q.textContent.includes(FR("prospects.qualif.manuel")));
  marque(m.hote, "qualifier").click(); await tick(); await tick();
  ok("10.5 recalculer : offre courante, sans ajustement", appels[0] && appels[0].offre === "prestation" && appels[0].ajustement === 0, JSON.stringify(appels));
  marque(m.hote, "retour").click(); await tick();
  marque(m.hote, "recherche").click(); await tick(); await tick();
  const sel = marque(m.hote, "recherche-fournisseur");
  ok("10.6 recherche web : fournisseur choisi, quatre au choix", sel && sel.value === "anthropic" && sel.children.length === 4);
  sel.value = "tavily"; sel.fire("change"); await tick();
  ok("10.7 choisir Tavily", appels.some((a) => a.fournisseur === "tavily" && !("valeur" in a)));
  marque(m.hote, "recherche-cle").value = "tvly-abc";
  marque(m.hote, "recherche-cle-enregistrer").click(); await tick();
  ok("10.8 poser la clé : envoyée, champ vidé, jamais affichée", appels.some((a) => a.valeur === "tvly-abc") && marque(m.hote, "recherche-cle").value === ""
    && !m.hote.textContent.includes("tvly-abc"));
}

// ---- t355 : séquences de la fiche (porte 2, planifier, copier et ouvrir, marquer envoyé, arrêt) --------------------------
{
  const SEQS = [
    { id: "sq_00000001", pid: "pr_00000001", canal: "email", statut: "proposee", motif: null, ouvrir: null,
      etapes: [{ rang: 0, objet: "Vos vidéos", texte: "Bonjour Léa", delai_jours: 0, statut: "brouillon", quand: null, due: false }] },
    { id: "sq_00000002", pid: "pr_00000001", canal: "x", statut: "planifiee", motif: null, ouvrir: "https://x.com/studiolune",
      etapes: [{ rang: 0, objet: "", texte: "Salut", delai_jours: 0, statut: "planifiee", quand: "2026-11-02T09:00:00+00:00", due: true },
               { rang: 1, objet: "", texte: "Relance", delai_jours: 4, statut: "planifiee", quand: "2026-11-06T09:00:00+00:00", due: false }] },
    { id: "sq_00000003", pid: "pr_00000001", canal: "email", statut: "annulee", motif: "fiche:repondu", ouvrir: null,
      etapes: [{ rang: 0, objet: "x", texte: "Ancien", delai_jours: 0, statut: "annulee", quand: null, due: false }] }];
  const appels = [];
  const ouverts = [];
  const routes = {
    "GET /api/prospects/e1": () => reponse(200, { prospects: [FICHE({ statut: "qualifie" })], compte_par_statut: { qualifie: 1 }, oppositions: 0 }),
    "GET /api/prospects/e1/sequences?pid=pr_00000001": () => reponse(200, { sequences: SEQS }),
    "POST /api/prospects/e1/sequences/sq_00000001/valider": () => { appels.push("valider"); return reponse(200, {}); },
    "POST /api/prospects/e1/sequences/sq_00000002/etapes/0/envoye": () => { appels.push("envoye"); return reponse(200, {}); },
    "POST /api/prospects/e1/sequences/sq_00000002/annuler": () => reponse(409, { detail: { code: "etat", message: "séquence « terminee » : rien à annuler" } }),
  };
  const m = monde({ routes });
  m.win.open = (u) => { ouverts.push(u); };
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marques(m.hote, "ligne")[0].click(); await tick(); await tick();
  const seqs = marques(m.hote, "sequence");
  ok("11.1 trois séquences, textes et objet affichés", seqs.length === 3 && seqs[0].textContent.includes("Bonjour Léa")
    && seqs[0].textContent.includes(FR("prospects.sequence.objet", { objet: "Vos vidéos" })), seqs.length);
  ok("11.2 statut traduit, étape « à envoyer maintenant »", seqs[0].textContent.includes(FR("prospects.seqstatut.proposee"))
    && seqs[1].textContent.includes(FR("prospects.sequence.due")));
  ok("11.3 « Valider » seulement sur la séquence proposée", marques(m.hote, "seq-valider").length === 1);
  ok("11.4 copier et ouvrir : seulement la prochaine étape d'un canal manuel", marques(m.hote, "seq-copier").length === 1 && marques(m.hote, "seq-envoye").length === 1);
  marque(m.hote, "seq-copier").click();
  ok("11.5 ouvre le profil du prospect", ouverts[0] === "https://x.com/studiolune", ouverts);
  ok("11.6 arrêt dit avec le statut traduit", marque(m.hote, "seq-motif").textContent === FR("prospects.sequence.arret", { statut: FR("prospects.statut.repondu") }));
  marque(m.hote, "seq-valider").click(); await tick(); await tick();
  ok("11.7 valider appelle la route", appels.includes("valider"));
  marque(m.hote, "seq-envoye").click(); await tick(); await tick();
  ok("11.8 marquer envoyé appelle la route de l'étape 0", appels.includes("envoye"));
  marques(m.hote, "seq-annuler")[1].click(); await tick(); await tick();
  ok("11.9 un refus est dit", marque(m.hote, "erreur").textContent.includes("rien à annuler"), marque(m.hote, "erreur").textContent);
  const en = monde({ lang: "en", routes });
  en.DzProspects.monter(en.hote, { espace_id: "e1" });
  await tick();
  marques(en.hote, "ligne")[0].click(); await tick(); await tick();
  ok("11.10 anglais", marque(en.hote, "seq-valider").textContent === EN("prospects.bouton.valider_seq") && EN("prospects.bouton.valider_seq") !== FR("prospects.bouton.valider_seq")
    && marques(en.hote, "sequence")[1].textContent.includes(EN("prospects.sequence.due")));
}

// ---- t356 : panneau « E-mail » (réglages, secret jamais affiché, pause, essai) -------------------------------------------
{
  const VUE = { mode: "smtp", expediteur: { nom: "Léa", adresse: "lea@deepotus.fr" }, identite: { raison_sociale: "Deepotus SAS", adresse_postale: "Paris" },
    smtp: { hote: "smtp.x.fr", port: 465, securite: "ssl", utilisateur: "lea" }, imap: { hote: "imap.x.fr", port: 993, utilisateur: "lea" },
    plafond_jour: 30, mdp_pose: true, brevo_pose: false, manques: [], pret: true, pause: { active: true, motif: "rebonds" },
    plafond_du_jour: 10, envoyes_du_jour: 3, taux_rebond: 0.1, erreur: { message: "identifiants SMTP refusés" } };
  const appels = [];
  const m = monde({ routes: {
    "GET /api/prospects/e1": () => reponse(200, LISTE),
    "GET /api/prospects/e1/email": () => reponse(200, VUE),
    "POST /api/prospects/e1/email": (c) => { appels.push(["regler", c]); return reponse(422, { detail: { code: "champ", message: "port : un entier de 1 à 65535" } }); },
    "POST /api/prospects/e1/email/secret": (c) => { appels.push(["secret", c]); return reponse(200, { ...VUE, mdp_pose: true }); },
    "POST /api/prospects/e1/email/reprendre": () => { appels.push(["reprendre"]); return reponse(200, { ...VUE, pause: { active: false, motif: "" } }); },
    "POST /api/prospects/e1/email/test": () => { appels.push(["test"]); return reponse(200, { envoye_a: "lea@deepotus.fr" }); },
  } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marque(m.hote, "email").click(); await tick(); await tick();
  ok("12.1 réglages lus dans les champs", marque(m.hote, "email-adresse").value === "lea@deepotus.fr" && marque(m.hote, "email-smtp_port").value === "465");
  const etat = marque(m.hote, "email-etat").textContent;
  ok("12.2 état : du jour, rebonds, pause traduite, erreur", etat.includes(FR("prospects.email.jour", { n: 3, plafond: 10 })) && etat.includes("10 %")
    && etat.includes(FR("prospects.email.pause", { motif: FR("prospects.emailpause.rebonds") })) && etat.includes("identifiants SMTP refusés"), etat);
  marque(m.hote, "email-mdp").value = "TresSecret";
  marque(m.hote, "email-mdp-enregistrer").click(); await tick(); await tick();
  ok("12.3 secret envoyé, champ vidé, jamais affiché", appels.some((a) => a[0] === "secret" && a[1].quoi === "mdp" && a[1].valeur === "TresSecret")
    && marque(m.hote, "email-mdp").value === "" && !m.hote.textContent.includes("TresSecret"));
  marque(m.hote, "email-enregistrer").click(); await tick(); await tick();
  const reg = appels.find((a) => a[0] === "regler");
  ok("12.4 enregistrer : corps complet, refus dit", reg && reg[1].smtp.port === 465 && reg[1].identite.raison_sociale === "Deepotus SAS"
    && marque(m.hote, "erreur").textContent.includes("port"), JSON.stringify(reg));
  marque(m.hote, "email-reprendre").click(); await tick(); await tick();
  ok("12.5 reprendre : appelé, plus de pause", appels.some((a) => a[0] === "reprendre") && !marque(m.hote, "email-pause"));
  marque(m.hote, "email-essai").click(); await tick(); await tick(); await tick();
  ok("12.6 essai : à l'expéditeur, dit", appels.some((a) => a[0] === "test") && marque(m.hote, "email-resultat").textContent === FR("prospects.email.essai_ok", { adresse: "lea@deepotus.fr" }));
}

// ---- t357 : étape WhatsApp à modèle, arrêt « fenetre » ------------------------------------------------------------------
{
  const SEQS = [{ id: "sq_00000009", pid: "pr_00000001", canal: "whatsapp", statut: "annulee", motif: "fenetre", ouvrir: null,
    etapes: [{ rang: 0, objet: "", texte: "aperçu", delai_jours: 0, statut: "annulee", quand: null, due: false,
      modele: { nom: "prospection_relance", langue: "fr", parametres: ["Léa"] } }] }];
  const m = monde({ routes: {
    "GET /api/prospects/e1": () => reponse(200, { prospects: [FICHE({ statut: "qualifie" })], compte_par_statut: { qualifie: 1 }, oppositions: 0 }),
    "GET /api/prospects/e1/sequences?pid=pr_00000001": () => reponse(200, { sequences: SEQS }) } });
  m.DzProspects.monter(m.hote, { espace_id: "e1" });
  await tick();
  marques(m.hote, "ligne")[0].click(); await tick(); await tick();
  ok("13.1 le modèle WhatsApp de l'étape est nommé", marque(m.hote, "etape-modele").textContent === FR("prospects.sequence.modele", { nom: "prospection_relance", langue: "fr" }));
  ok("13.2 arrêt « fenêtre de 24 h » expliqué", marque(m.hote, "seq-motif").textContent === FR("prospects.seqmotif.fenetre"));
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
