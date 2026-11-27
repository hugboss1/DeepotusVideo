// t492 (09/11/2026) — dz-croissance.js : l'écran « Croissance » (5e onglet du tiroir F1), joué sur un DOM simulé.
// Séries : tableau_rendu (compte, tuiles, régularité, gagnants, top), raisons, compte_absent, compte_erreur,
// titre_hostile_en_texte, filtre (période, espace), relever (200, 500), panne, anglais, demontage.
// t495 (26/11/2026) : niche (gagnants de la niche, enregistrer, choisir les fils, devis puis analyse sur accord, coût
// changé, plafond, raisons masquées, niche vide).
// Lancer : node frontend/shared/qa/croissance.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-croissance.js", import.meta.url), "utf8");
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
  fire(t) { (this.ec[t] || []).forEach((f) => f({ type: t, target: this, preventDefault() {} })); }
  click() { this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tous = (r, p) => [...r.tous()].filter(p);
const marques = (r, v) => tous(r, (x) => x.attrs["data-dz-croissance"] === v);
const marque = (r, v) => marques(r, v)[0];

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

function monde({ lang = "fr", tableau, releve = 200, panne = false, niche = null, recyclage = null, x = null } = {}) {
  const appels = [];
  const win = {
    dzT: dzTde(lang), dzLang: () => lang,
    fetch: async (url, init = {}) => {
      const m = init.method || "GET";
      appels.push({ url: String(url), methode: m, corps: init.body ? JSON.parse(init.body) : null });
      if (panne) throw new Error("réseau coupé");
      if (String(url).startsWith("/api/recyclage/")) return recyclage ? recyclage(String(url), m) : reponse(404, {});
      if (String(url) === "/api/espaces") return reponse(200, { actif: "e1", espaces: [{ id: "e1", nom: "Marque" }, { id: "e2", nom: "Client <b>" }, { id: "e3", nom: "Vieux", archive: true }] });
      if (String(url).startsWith("/api/schedule/croissance")) return typeof tableau === "function" ? tableau(String(url)) : reponse(200, tableau);
      if (String(url) === "/api/schedule/analytics/refresh") return reponse(releve, {});
      if (String(url).startsWith("/api/croissance/x/")) {   // t500 : la section « Mes posts X »
        const corps = init.body ? JSON.parse(init.body) : null;
        if (x) return x(String(url), m, corps);
        return reponse(200, { n: 0, usd: 0, posts: [], tarifs: { lecture: 0.005, post: 0.015, post_lien: 0.2, media: 0.005 },
          relu: { le: "2026-11-26" }, accord: { auto: false, plafond_usd: 0 } });
      }
      if (String(url).startsWith("/api/croissance/")) {
        const N = niche || {};
        const u = String(url).split("?")[0];
        if (u === "/api/croissance/gagnants") return reponse(N.gagnantsStatut || 200, N.gagnants || { seuil: 3, jours: 7, niche: [], gagnants: [] });
        if (u === "/api/croissance/niche") return m === "PUT" ? reponse(200, { niche: [] }) : reponse(200, N.niche || { fils: [] });
        if (u === "/api/croissance/enregistres") return reponse(N.enregistrerStatut || 200, { statut: "enregistre" });
        if (u.endsWith("/devis")) return reponse(200, N.devis || { usd: 0.0123, disponible: true, delai_s: 90 });
        if (u.endsWith("/analyse")) { const a = (N.analyses || []).shift() || [200, {}]; return reponse(a[0], a[1]); }
      }
      return reponse(404, {});
    },
  };
  const doc = { createElement: (t) => new Noeud(t), head: new Noeud("head"), documentElement: new Noeud("html") };
  const ctx = { window: win, document: doc, console, Date, parseInt, isFinite, Math, encodeURIComponent };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { win, appels, Dz: win.DzCroissance, hote: new Noeud("div") };
}

const post = (id, titre, vues, c) => ({ id, title: titre, channel: "instagram", format: "reel", espace_id: "e1", views: vues, engagement: 10,
  croissance: Object.assign({ jalons: { j1: null, j3: null, j7: null, j30: null }, jalon: null, vues: null, habituel: null, multiplicateur: null,
    gagnant: false, recul: 0, visionnage_s: null, raison: null }, c) });
const GAGNANT = post("g", "Stop aux essais gratuits", 20069, { jalons: { j1: 13960, j3: 16715, j7: 20069, j30: null }, jalon: 7, vues: 20069,
  habituel: 743, multiplicateur: 27, gagnant: true, recul: 10, visionnage_s: 23.3 });
const TABLEAU = {
  days: 30, espace_id: null, seuil_gagnant: 3, notes: {},
  totaux: { posts: 4, views: 1900000, likes: 1, comments: 1, shares: 1, saves: 1, engagement: 239000 },
  canaux: {},
  top: [GAGNANT, post("a", "<img src=x onerror=alert(1)>", 900, { jalons: { j1: 400, j3: null, j7: null, j30: null }, jalon: 1, vues: 400, habituel: 500, multiplicateur: 0.8, recul: 6 }),
    post("b", "Trop jeune", 40, { raison: "trop_tot" }), post("c", "Sans recul", 300, { raison: "peu_de_recul", recul: 3 }),
    post("d", "Sans relevé", 10, { raison: "sans_releve" })],
  gagnants: [GAGNANT],
  regularite: { jours: 30, jours_avec_post: 25, serie: 4, semaine: [0, 1, 2, 0, 1, 1, 1].map((p, i) => ({ jour: "2026-11-0" + (3 + i), posts: p })) },
  compte: { instagram: { username: "getripping", followers: 8931, reach: 763000, views: 1900000, interactions: 239000, follows: 8820,
    unfollows: 181, non_abonnes_pct: 96, jours: 30, illisibles: [] } },
};
const FR = dzTde("fr"), EN = dzTde("en");
const txt = (x) => (x ? x.textContent : "");

// ---- tableau_rendu ------------------------------------------------------------------------------------------------------
{
  const m = monde({ tableau: TABLEAU });
  const c = m.Dz.monter(m.hote);
  await tick(); await tick();
  const q = m.appels.find((a) => a.url.startsWith("/api/schedule/croissance"));
  ok("1.1 lit le tableau sur 30 jours, avec le fuseau du navigateur", !!q && /\?days=30&tz=-?\d+$/.test(q.url), q && q.url);
  ok("1.2 six tuiles de compte, nombres abrégés", marques(m.hote, "compte")[0] && txt(marque(m.hote, "compte-views")).startsWith("1,9 M")
    && txt(marque(m.hote, "compte-followers")).startsWith("8") && txt(marque(m.hote, "compte-non_abonnes_pct")).startsWith("96 %"),
    txt(marque(m.hote, "compte-views")) + " | " + txt(marque(m.hote, "compte-non_abonnes_pct")));
  ok("1.3 le compte est nommé avec sa fenêtre", txt(marque(m.hote, "compte")).includes(FR("croissance.compte.note", { nom: "getripping", n: 30 })));
  ok("1.4 trois tuiles de posts", txt(marque(m.hote, "posts-posts")).startsWith("4") && txt(marque(m.hote, "posts-engagement")).startsWith("239 k"), txt(marque(m.hote, "posts-engagement")));
  const reg = marque(m.hote, "regularite");
  ok("1.5 semainier : 7 cases, 5 marquées", tous(reg, (x) => (x.attrs.class || "") === "dzCroiJour").length === 7
    && tous(reg, (x) => "data-posts" in x.attrs).length === 5);
  ok("1.6 régularité en toutes lettres", txt(marque(m.hote, "regularite-texte")) === FR("croissance.regularite.jours", { n: 25, total: 30 }) + " · " + FR("croissance.regularite.serie", { n: 4 }));
  const gl = marques(marque(m.hote, "gagnants"), "post");
  ok("1.7 un gagnant : 27×, marqué", gl.length === 1 && txt(marque(gl[0], "multiplicateur")) === "27×" && marque(gl[0], "multiplicateur").hasAttribute("data-gagnant"));
  ok("1.8 l'habituel en infobulle", marque(gl[0], "multiplicateur").attrs.title === FR("croissance.post.habituel", { n: "743", jalon: 7 }), marque(gl[0], "multiplicateur").attrs.title);
  ok("1.9 jalons lus et temps de visionnage dans le détail", txt(gl[0]).includes(FR("croissance.jalon.j1", { n: "14 k" }))
    && txt(gl[0]).includes(FR("croissance.jalon.j7", { n: "20,1 k" })) && !txt(gl[0]).includes("J30")
    && txt(gl[0]).includes(FR("croissance.post.visionnage", { n: "23,3" })), txt(gl[0]));
  const tl = marques(marque(m.hote, "top"), "post");
  ok("1.10 cinq meilleurs posts, la note explique le ×", tl.length === 5 && txt(marque(m.hote, "top")).includes(FR("croissance.top.note")));
  ok("1.11 0,8× : pas un gagnant", txt(marque(tl[1], "multiplicateur")) === "0,8×" && !marque(tl[1], "multiplicateur").hasAttribute("data-gagnant"));
  ok("1.12 titre hostile posé en texte, aucun élément créé", txt(tl[1]).includes("<img src=x onerror=alert(1)>") && tous(m.hote, (x) => x.tagName === "IMG").length === 0);
  ok("1.13 raisons en clair", txt(marque(tl[2], "multiplicateur")) === FR("croissance.raison.trop_tot")
    && txt(marque(tl[3], "multiplicateur")) === FR("croissance.raison.peu_de_recul", { n: 3 })
    && txt(marque(tl[4], "multiplicateur")) === FR("croissance.raison.sans_releve"));
  const selE = marque(m.hote, "espace");
  ok("1.14 filtre d'espace : tous + les espaces vivants, nom en texte", selE.children.length === 3 && selE.children[0].textContent === FR("croissance.espace.tous")
    && selE.children[2].textContent === "Client <b>");
  selE.value = "e2"; selE.fire("change"); await tick();
  ok("1.15 changer d'espace relit avec espace_id", m.appels.some((a) => a.url.includes("&espace_id=e2")));
  const selP = marque(m.hote, "periode");
  selP.value = "7"; selP.fire("change"); await tick();
  ok("1.16 changer de période relit avec days=7 et garde l'espace", m.appels.some((a) => a.url.includes("days=7") && a.url.includes("espace_id=e2")));
  ok("1.17 aucune écriture tant qu'on ne relève pas", m.appels.every((a) => a.methode === "GET"));
  const avant = m.appels.length;
  marque(m.hote, "relever").click(); await tick(); await tick();
  ok("1.18 relever : POST refresh puis relecture", m.appels.slice(avant).filter((a) => !a.url.startsWith("/api/croissance/")).map((a) => a.methode + " " + a.url.split("?")[0]).join()
    === "POST /api/schedule/analytics/refresh,GET /api/schedule/croissance" && !marque(m.hote, "relever").hasAttribute("disabled"));
  c.recharger(); await tick();
  c.demonter();
  ok("1.19 démontage : la racine quitte l'hôte", m.hote.children.length === 0);
}

// ---- compte_absent, compte_erreur, illisibles, vides -------------------------------------------------------------------
{
  const vide = Object.assign({}, TABLEAU, { top: [], gagnants: [], compte: { instagram: null }, totaux: { posts: 0, views: 0, engagement: 0 } });
  const m = monde({ tableau: vide });
  m.Dz.monter(m.hote); await tick(); await tick();
  ok("2.1 aucun compte relié : le message dit où le relier", txt(marque(m.hote, "compte-absent")) === FR("croissance.compte.absent"));
  ok("2.2 aucun gagnant : le seuil est dit", txt(marque(m.hote, "gagnants")).includes(FR("croissance.vide.gagnants", { n: "3" })));
  ok("2.3 aucun post mesuré", txt(marque(m.hote, "top")).includes(FR("croissance.vide.top")));
  const m2 = monde({ tableau: Object.assign({}, vide, { compte: { instagram: null, erreur: true } }) });
  m2.Dz.monter(m2.hote); await tick(); await tick();
  ok("2.4 Instagram muet : dit, les posts restent", txt(marque(m2.hote, "compte-absent")) === FR("croissance.compte.erreur") && !!marque(m2.hote, "posts"));
  const ig = Object.assign({}, TABLEAU.compte.instagram, { views: null, non_abonnes_pct: null, illisibles: ["views", "follows_and_unfollows"] });
  const m3 = monde({ tableau: Object.assign({}, TABLEAU, { compte: { instagram: ig } }) });
  m3.Dz.monter(m3.hote); await tick(); await tick();
  ok("2.5 mesures refusées : tiret et note chiffrée", txt(marque(m3.hote, "compte-views")).startsWith("—")
    && txt(marque(m3.hote, "illisibles")) === FR("croissance.compte.illisibles", { n: 2 }));
}

// ---- panne, releve_erreur, anglais ---------------------------------------------------------------------------------------
{
  const m = monde({ panne: true });
  m.Dz.monter(m.hote); await tick(); await tick();
  ok("3.1 réseau coupé : erreur dite, rien ne casse", txt(marque(m.hote, "etat")) === FR("croissance.etat.erreur") && marque(m.hote, "etat").hasAttribute("data-erreur"));
  const m2 = monde({ tableau: TABLEAU, releve: 500 });
  m2.Dz.monter(m2.hote); await tick(); await tick();
  marque(m2.hote, "relever").click(); await tick(); await tick();
  ok("3.2 relevé refusé : dit, le bouton revient", txt(marque(m2.hote, "etat")) === FR("croissance.etat.releve_erreur") && !marque(m2.hote, "relever").hasAttribute("disabled"));
  const m3 = monde({ tableau: TABLEAU, lang: "en" });
  m3.Dz.monter(m3.hote); await tick(); await tick();
  ok("3.3 anglais : libellés et nombres", txt(marque(m3.hote, "compte-views")) === "1.9 M" + EN("croissance.compte.views")
    && txt(marque(m3.hote, "relever")) === EN("croissance.bouton.relever") && txt(marque(m3.hote, "regularite-texte")).includes("25 of 30"), txt(marque(m3.hote, "compte-views")));
  const lent = monde({ tableau: (url) => (url.includes("days=7") ? reponse(200, Object.assign({}, TABLEAU, { totaux: { posts: 77, views: 1, engagement: 1 } })) : new Promise((r) => setTimeout(() => r(reponse(200, TABLEAU)), 40))) });
  lent.Dz.monter(lent.hote);
  const sp = marque(lent.hote, "periode"); sp.value = "7"; sp.fire("change");
  await new Promise((r) => setTimeout(r, 90));
  ok("3.4 une réponse lente et périmée n'écrase pas la plus récente", txt(marque(lent.hote, "posts-posts")).startsWith("77"), txt(marque(lent.hote, "posts-posts")));
}

// ---- t495 : niche -----------------------------------------------------------------------------------------------------------
{
  const G1 = { id: "aaaa1111", fil_id: "fil_a", plateforme: "x", source_name: "X · @createur", title: "<script>x</script> Un tweet qui explose",
    link: "https://x.com/i/status/1005", published: "2026-11-24T10:00:00+00:00", mesure: "vues", valeur: 2500, habituel: 100,
    multiplicateur: 25, gagnant: true, enregistre: false, analyse: null };
  const G2 = Object.assign({}, G1, { id: "bbbb2222", title: "Reel", link: "javascript:alert(1)", mesure: "interactions", valeur: 440,
    habituel: 88, multiplicateur: 5, enregistre: true, analyse: { raisons: [{ critere: "accroche", present: true, secondes: 2, explication: "Une accusation d'entrée.", alertes: [] }],
      principales: ["accroche"], resume: "", usd: 0.01 } });
  const ANALYSE = { raisons: [
    { critere: "accroche", present: true, secondes: 1.5, explication: "Une question <b>directe</b>.", alertes: [] },
    { critere: "ennemi", present: true, secondes: null, explication: "", alertes: ["copie"] },
    { critere: "chiffre", present: false, secondes: null, explication: "Aucun chiffre.", alertes: [] },
    { critere: "promesse", present: true, secondes: null, explication: "Un gain de temps.", alertes: [] },
    { critere: "appel", present: false, secondes: null, explication: "", alertes: [] }], principales: ["ennemi", "accroche"], resume: "Court et frontal.", usd: 0.0123 };
  const N = { gagnants: { espace_id: "e1", seuil: 3, jours: 7, niche: [{ id: "fil_a" }], elements: 9, sans_habituel: 2, gagnants: [G1, G2] },
    niche: { espace_id: "e1", fils: [{ id: "fil_a", nom: "@createur", plateforme: "x", dans_niche: true }, { id: "fil_b", nom: "@autre <i>", plateforme: "instagram", dans_niche: false }] },
    devis: { usd: 0.0123, disponible: true, delai_s: 90 },
    analyses: [[409, { detail: { message: "coût", code: "cout", usd: 0.02 } }], [200, ANALYSE], [402, { detail: { code: "dz_plafond" } }]] };
  const m = monde({ tableau: TABLEAU, niche: N });
  m.Dz.monter(m.hote); await tick(); await tick(); await tick();
  const sec = marque(m.hote, "niche");
  ok("4.1 la section se lit sur /api/croissance/gagnants, sans écriture", !!sec && m.appels.some((a) => a.url === "/api/croissance/gagnants")
    && txt(sec).includes(FR("croissance.section.niche")) && txt(sec).includes(FR("croissance.niche.note", { n: "3", j: 7 })));
  const lignes = marques(sec, "niche-gagnant");
  ok("4.2 deux gagnants, dans l'ordre du serveur, multiplicateur et mesure", lignes.length === 2 && txt(marque(lignes[0], "multiplicateur")) === "25×"
    && txt(lignes[0]).includes(FR("croissance.niche.valeur_vues", { n: (2500).toLocaleString("fr-FR") })) && txt(lignes[1]).includes(FR("croissance.niche.valeur_interactions", { n: "440" }))
    && marque(lignes[0], "multiplicateur").attrs.title === FR("croissance.niche.habituel_vues", { n: "100" }), txt(lignes[0]));
  ok("4.3 titre hostile en texte ; lien https gardé, javascript: écarté", txt(lignes[0]).includes("<script>x</script>")
    && tous(m.hote, (x) => x.tagName === "SCRIPT").length === 0 && marque(lignes[0], "niche-lien").attrs.href === "https://x.com/i/status/1005"
    && !marque(lignes[1], "niche-lien") && marque(lignes[0], "niche-lien").attrs.rel.includes("noopener"));
  ok("4.4 déjà enregistré : bouton éteint", marque(lignes[1], "niche-enregistrer").hasAttribute("disabled")
    && txt(marque(lignes[1], "niche-enregistrer")) === FR("croissance.niche.enregistre"));
  marque(lignes[0], "niche-enregistrer").click(); await tick();
  const enr = m.appels.find((a) => a.url === "/api/croissance/enregistres");
  ok("4.5 enregistrer : POST {item_id}, bouton « enregistré »", enr && enr.methode === "POST" && enr.corps.item_id === "aaaa1111"
    && txt(marque(lignes[0], "niche-enregistrer")) === FR("croissance.niche.enregistre"), JSON.stringify(enr));
  marque(lignes[1], "niche-pourquoi").click(); await tick();
  ok("4.6 analyse gardée : affichée sans aucun appel", marques(lignes[1], "raison").length === 1
    && !m.appels.some((a) => a.url.includes("bbbb2222")) && txt(lignes[1]).includes(FR("croissance.analyse.secondes", { n: "2" })));
  const avantA = m.appels.length;
  marque(lignes[0], "niche-pourquoi").click(); await tick();
  ok("4.7 pourquoi : une zone de transcription et un bouton de devis, rien d'envoyé", !!marque(lignes[0], "analyse-transcription")
    && !!marque(lignes[0], "analyse-devis") && marque(lignes[0], "analyse-lancer").hasAttribute("hidden") && m.appels.length === avantA);
  marque(lignes[0], "analyse-transcription").value = "Arrête de payer.";
  marque(lignes[0], "analyse-devis").click(); await tick();
  const dv = m.appels.find((a) => a.url.endsWith("/devis") && a.url.includes("/gagnants/"));
  ok("4.8 devis gratuit : POST avec la transcription, montant sur le bouton", dv && dv.corps.transcription === "Arrête de payer."
    && !marque(lignes[0], "analyse-lancer").hasAttribute("hidden")
    && txt(marque(lignes[0], "analyse-lancer")) === FR("croissance.analyse.lancer", { usd: "0,0123" }) && !m.appels.some((a) => a.url.endsWith("/analyse")),
    txt(marque(lignes[0], "analyse-lancer")));
  marque(lignes[0], "analyse-lancer").click(); await tick();
  const a1 = m.appels.filter((a) => a.url.endsWith("/analyse"));
  ok("4.9 analyse : max_usd = le devis ; coût changé : nouveau montant à accepter", a1.length === 1 && a1[0].corps.max_usd === 0.0123
    && a1[0].corps.transcription === "Arrête de payer." && txt(marque(lignes[0], "analyse-etat")) === FR("croissance.analyse.cout", { usd: "0,02" })
    && txt(marque(lignes[0], "analyse-lancer")) === FR("croissance.analyse.lancer", { usd: "0,02" }), txt(marque(lignes[0], "analyse-etat")));
  marque(lignes[0], "analyse-lancer").click(); await tick();
  const a2 = m.appels.filter((a) => a.url.endsWith("/analyse"));
  const rs = marques(lignes[0], "raison");
  ok("4.10 second clic : max_usd = le nouveau montant ; la grille s'affiche", a2.length === 2 && a2[1].corps.max_usd === 0.02 && rs.length === 5
    && rs.map((r) => r.attrs["data-critere"]).join() === "accroche,ennemi,chiffre,promesse,appel");
  ok("4.11 principales marquées, absents grisés, copie masquée, HTML en texte", rs[0].hasAttribute("data-principale") && rs[1].hasAttribute("data-principale")
    && !rs[3].hasAttribute("data-principale") && rs[2].hasAttribute("data-absent") && txt(rs[1]).includes(FR("croissance.analyse.masquee"))
    && txt(rs[0]).includes("<b>directe</b>") && txt(rs[0]).includes(FR("croissance.grille.accroche")) && tous(m.hote, (x) => x.tagName === "B" && x.textContent === "directe").length === 0);
  ok("4.12 résumé et coût dits", txt(marque(lignes[0], "analyse-resume")) === "Court et frontal." && txt(lignes[0]).includes(FR("croissance.analyse.note", { usd: "0,0123" })));
  marque(lignes[1], "niche-pourquoi").click();
  // choisir les fils
  marque(sec, "niche-choisir").click(); await tick(); await tick();
  const cases = marques(sec, "niche-fil");
  ok("4.13 choisir les fils : tous les fils suivis, ceux de la niche cochés, noms en texte", cases.length === 2 && cases[0].checked === true
    && cases[1].checked === false && txt(marque(sec, "niche-editeur")).includes("@autre <i>"));
  cases[1].checked = true;
  marque(sec, "niche-poser").click(); await tick(); await tick();
  const put = m.appels.find((a) => a.methode === "PUT");
  ok("4.14 garder la niche : PUT des fils cochés, puis relecture", put && put.url === "/api/croissance/niche" && JSON.stringify(put.corps.fils) === '["fil_a","fil_b"]'
    && m.appels.filter((a) => a.url === "/api/croissance/gagnants").length >= 2, JSON.stringify(put));
  const selE = marque(m.hote, "espace");
  selE.value = "e2"; selE.fire("change"); await tick(); await tick();
  ok("4.15 l'espace choisi part dans la lecture de la niche", m.appels.some((a) => a.url === "/api/croissance/gagnants?espace_id=e2"));
  const l2 = marques(marque(m.hote, "niche"), "niche-gagnant");

  marque(l2[0], "niche-enregistrer").click(); await tick();
  ok("4.16 et dans les écritures", m.appels.filter((a) => a.url === "/api/croissance/enregistres").pop().corps.espace_id === "e2");
  ok("4.17 aucune analyse partie sans montant accepté", m.appels.filter((a) => a.url.endsWith("/analyse")).every((a) => typeof a.corps.max_usd === "number"));
}
{
  const m = monde({ tableau: TABLEAU, niche: { gagnants: { espace_id: "e1", seuil: 3, jours: 7, niche: [], gagnants: [] } } });
  m.Dz.monter(m.hote); await tick(); await tick();
  ok("4.18 niche vide : dit où choisir les fils", txt(marque(m.hote, "niche-etat")) === FR("croissance.niche.sans_fils"));
  const m2 = monde({ tableau: TABLEAU, niche: { gagnants: { espace_id: "e1", seuil: 3, jours: 7, niche: [{ id: "f" }, { id: "g" }], gagnants: [] } } });
  m2.Dz.monter(m2.hote); await tick(); await tick();
  ok("4.19 aucun gagnant : seuil, fenêtre et nombre de fils dits", txt(marque(m2.hote, "niche-etat")) === FR("croissance.niche.aucun", { n: "3", j: 7, f: 2 }));
  const m3 = monde({ tableau: TABLEAU, niche: { gagnantsStatut: 500 } });
  m3.Dz.monter(m3.hote); await tick(); await tick();
  ok("4.20 lecture refusée : dit, le reste de l'écran tient", txt(marque(m3.hote, "niche-etat")) === FR("croissance.niche.erreur") && !!marque(m3.hote, "posts"));
  const m4 = monde({ tableau: TABLEAU, lang: "en", niche: { gagnants: { espace_id: "e1", seuil: 3, jours: 7, niche: [], gagnants: [] } } });
  m4.Dz.monter(m4.hote); await tick(); await tick();
  ok("4.21 anglais", txt(marque(m4.hote, "niche")).includes(EN("croissance.section.niche")) && txt(marque(m4.hote, "niche-etat")) === EN("croissance.niche.sans_fils"));
}
// ---- t498 : recycler un gagnant -----------------------------------------------------------------------------------------
{
  const carte = (element, usd, texte = {}) => ({ type: "carte", genre: "devis", devis: usd, etat: "proposee",
    arguments: { element, redige: false, texte: Object.assign({ usd, disponible: true, raison: "" }, texte) } });
  const PROP = { cartes: [carte("carrousel", 0.012), carte("accroches", 0.004), carte("fil_x", 0.006),
    carte("branche", 0, { disponible: false, raison: "sans_plans" })] };
  let refusRedaction = false;
  const recy = (url, m) => {
    if (url.endsWith("/proposition")) return reponse(200, PROP);
    if (url.endsWith("/redaction")) return refusRedaction ? reponse(409, { detail: { message: "Le coût a changé : il dépasse le montant accepté.", code: "cout", usd: 1 } })
      : reponse(200, { accroches: ["a", "b", "c"], interdits: [] });
    if (url.endsWith("/brouillons")) return reponse(200, { brouillons: [{}, {}, {}], non_crees: [] });
    return reponse(404, {});
  };
  const m = monde({ tableau: TABLEAU, recyclage: recy });
  m.Dz.monter(m.hote); await tick(); await tick();
  const gl = marque(marque(m.hote, "gagnants"), "post");
  ok("5.1 le gagnant porte « Recycler ce gagnant », les autres non", txt(marque(gl, "recycler")) === FR("croissance.recyclage.bouton")
    && marques(marque(m.hote, "top"), "recycler").length === 1);
  marque(gl, "recycler").click(); await tick(); await tick();
  ok("5.2 la proposition est lue (GET), sans aucune écriture", m.appels.some((a) => a.url === "/api/recyclage/g/proposition" && a.methode === "GET")
    && !m.appels.some((a) => a.url.startsWith("/api/recyclage/") && a.methode === "POST"));
  const cartes = marques(gl, "recyclage-carte");
  ok("5.3 quatre cartes nommées, chacune avec son devis", cartes.length === 4 && txt(cartes[1]).includes(FR("croissance.recyclage.accroches"))
    && txt(cartes[1]).includes("0,004 $") && txt(cartes[0]).includes("0,01 $"), cartes.map(txt).join(" | "));
  ok("5.4 carte indisponible : raison dite, aucun bouton", txt(cartes[3]).includes(FR("croissance.raison_recyclage.sans_plans"))
    && !marque(cartes[3], "recyclage-accepter"));
  marque(gl, "recyclage-brouillons").click(); await tick();
  ok("5.5 brouillons avant toute carte acceptée : refusé sur place", txt(marque(gl, "recyclage-etat")) === FR("croissance.recyclage.rien")
    && !m.appels.some((a) => a.url.endsWith("/brouillons")));
  marque(cartes[1], "recyclage-accepter").click(); await tick(); await tick();
  const red = m.appels.find((a) => a.url.endsWith("/redaction"));
  ok("5.6 accepter : POST redaction de CET élément, au montant affiché", red && red.methode === "POST" && red.corps.element === "accroches"
    && red.corps.max_usd === 0.004, JSON.stringify(red));
  ok("5.7 rédigé : le bouton le dit et se fige", txt(marque(cartes[1], "recyclage-accepter")) === FR("croissance.recyclage.redige")
    && marque(cartes[1], "recyclage-accepter").hasAttribute("disabled"));
  marque(gl, "recyclage-brouillons").click(); await tick(); await tick();
  const br = m.appels.find((a) => a.url.endsWith("/brouillons"));
  ok("5.8 brouillons : les seuls éléments rédigés", br && br.methode === "POST" && JSON.stringify(br.corps) === '{"elements":["accroches"]}', JSON.stringify(br));
  ok("5.9 le nombre de brouillons est dit", txt(marque(gl, "recyclage-etat")) === FR("croissance.recyclage.crees", { n: 3 }));
  refusRedaction = true;
  marque(cartes[2], "recyclage-accepter").click(); await tick(); await tick();
  ok("5.10 refus du serveur : son message, le bouton revient", txt(marque(gl, "recyclage-etat")).startsWith("Le coût a changé")
    && marque(gl, "recyclage-etat").hasAttribute("data-erreur") && !marque(cartes[2], "recyclage-accepter").hasAttribute("disabled"));
  const m2 = monde({ tableau: TABLEAU, recyclage: () => reponse(409, { detail: { message: "Ce post n'est pas un gagnant", code: "sous_seuil" } }) });
  m2.Dz.monter(m2.hote); await tick(); await tick();
  const g2 = marque(marque(m2.hote, "gagnants"), "post");
  marque(g2, "recycler").click(); await tick(); await tick();
  ok("5.11 proposition refusée : le message du serveur, posé en texte", txt(marque(g2, "recyclage-etat")) === "Ce post n'est pas un gagnant"
    && !marque(g2, "recyclage-cartes"));
}

// ---- t500 : « Mes posts X » ------------------------------------------------------------------------------------------
{
  let devis = { n: 2, usd: 0.01, posts: [{}, {}], tarifs: { lecture: 0.005, post: 0.015, post_lien: 0.2, media: 0.005 },
    relu: { le: "2026-11-26" }, accord: { auto: false, plafond_usd: 0 } };
  const reps = [[409, { detail: { message: "coût", code: "cout", usd: 0.015 } }], [200, { releves: 3, usd: 0.015, lus: 3 }]];
  const xs = (u, meth, corps) => {
    if (u.endsWith("/x/devis")) return reponse(200, devis);
    if (u.endsWith("/x/releve")) { const r = reps.shift(); return reponse(r[0], r[1]); }
    if (u.endsWith("/x/accord")) return corps && corps.auto && !corps.plafond_usd ? reponse(400, { detail: "plafond" }) : reponse(200, { auto: corps.auto });
    return reponse(404, {});
  };
  const m = monde({ tableau: TABLEAU, x: xs });
  m.Dz.monter(m.hote); await tick(); await tick(); await tick();
  const sx = marque(m.hote, "x");
  ok("6.1 la section X lit son devis (GET), tarifs datés, aucun relevé parti", !!sx && m.appels.some((a) => a.url === "/api/croissance/x/devis" && a.methode === "GET")
    && txt(marque(sx, "x-tarifs")).includes("2026-11-26") && txt(marque(sx, "x-tarifs")).includes("0,20 $")
    && !m.appels.some((a) => a.url.endsWith("/x/releve")), txt(sx));
  ok("6.2 deux posts dus : le montant est sur le bouton", txt(marque(sx, "x-devis")) === FR("croissance.x.devis", { n: 2, usd: "0,01 $" })
    && txt(marque(sx, "x-relever")) === FR("croissance.x.relever", { usd: "0,01 $" }), txt(marque(sx, "x-relever")));
  marque(sx, "x-relever").click(); await tick(); await tick();
  const r1 = m.appels.filter((a) => a.url.endsWith("/x/releve"));
  ok("6.3 relevé : POST au montant du devis ; coût changé : nouveau montant à accepter", r1.length === 1 && r1[0].methode === "POST"
    && r1[0].corps.max_usd === 0.01 && txt(marque(sx, "x-relever")) === FR("croissance.x.relever", { usd: "0,015 $" }), JSON.stringify(r1));
  marque(sx, "x-relever").click(); await tick(); await tick();
  const r2 = m.appels.filter((a) => a.url.endsWith("/x/releve"));
  ok("6.4 second clic au nouveau montant ; l'écran se relit", r2.length === 2 && r2[1].corps.max_usd === 0.015
    && m.appels.filter((a) => a.url === "/api/croissance/x/devis").length >= 2);
  const s2 = marque(m.hote, "x");
  marque(s2, "x-auto").checked = true;
  marque(s2, "x-plafond").value = "0";
  marque(s2, "x-accord").click(); await tick(); await tick();
  const acc = m.appels.filter((a) => a.url.endsWith("/x/accord"));
  ok("6.5 accord auto sans plafond : refusé et dit", acc.length === 1 && acc[0].methode === "PUT" && acc[0].corps.auto === true
    && txt(marque(s2, "x-etat")) === FR("croissance.x.accord_erreur"), txt(marque(s2, "x-etat")));
  marque(s2, "x-plafond").value = "3";
  marque(s2, "x-accord").click(); await tick(); await tick();
  ok("6.6 accord avec plafond : enregistré", m.appels.filter((a) => a.url.endsWith("/x/accord")).pop().corps.plafond_usd === 3
    && txt(marque(s2, "x-etat")) === FR("croissance.x.accord_ok"));
  devis = Object.assign({}, devis, { n: 0, usd: 0 });
  const m2 = monde({ tableau: TABLEAU, x: xs });
  m2.Dz.monter(m2.hote); await tick(); await tick(); await tick();
  ok("6.7 rien de dû : aucun bouton de relevé", txt(marque(marque(m2.hote, "x"), "x-devis")) === FR("croissance.x.rien")
    && !marque(marque(m2.hote, "x"), "x-relever"));
  const m3 = monde({ tableau: TABLEAU, x: () => reponse(500, {}) });
  m3.Dz.monter(m3.hote); await tick(); await tick(); await tick();
  ok("6.8 devis illisible : dit, le reste de l'écran tient", txt(marque(marque(m3.hote, "x"), "x-etat")) === FR("croissance.x.erreur") && !!marque(m3.hote, "posts"));
}
{ // t500 : la carte du fil X dit ce que coûtera la mise en ligne
  const carteX = { type: "carte", genre: "devis", devis: 0.006, arguments: { element: "fil_x", redige: false,
    texte: { usd: 0.006, disponible: true, raison: "" }, publication: { usd_max: 0.305, usd_post: 0.015, usd_post_lien: 0.2 } } };
  const m = monde({ tableau: TABLEAU, recyclage: (u) => u.endsWith("/proposition") ? reponse(200, { cartes: [carteX] }) : reponse(404, {}) });
  m.Dz.monter(m.hote); await tick(); await tick();
  const gl = marque(marque(m.hote, "gagnants"), "post");
  marque(gl, "recycler").click(); await tick(); await tick();
  ok("6.9 la carte fil X : coût de mise en ligne X, lien compris", txt(marque(gl, "recyclage-publication-x"))
    === FR("croissance.recyclage.publication_x", { usd: "0,305 $", post: "0,015 $", lien: "0,20 $" }), txt(gl));
}

if (echecs.length) { console.log("ÉCHECS (" + echecs.length + "/" + n + ") :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("croissance : OK (" + n + " vérifications)");
