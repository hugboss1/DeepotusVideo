// t492 (09/11/2026) — dz-croissance.js : l'écran « Croissance » (5e onglet du tiroir F1), joué sur un DOM simulé.
// Séries : tableau_rendu (compte, tuiles, régularité, gagnants, top), raisons, compte_absent, compte_erreur,
// titre_hostile_en_texte, filtre (période, espace), relever (200, 500), panne, anglais, demontage.
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

function monde({ lang = "fr", tableau, releve = 200, panne = false } = {}) {
  const appels = [];
  const win = {
    dzT: dzTde(lang), dzLang: () => lang,
    fetch: async (url, init = {}) => {
      const m = init.method || "GET";
      appels.push({ url: String(url), methode: m });
      if (panne) throw new Error("réseau coupé");
      if (String(url) === "/api/espaces") return reponse(200, { actif: "e1", espaces: [{ id: "e1", nom: "Marque" }, { id: "e2", nom: "Client <b>" }, { id: "e3", nom: "Vieux", archive: true }] });
      if (String(url).startsWith("/api/schedule/croissance")) return typeof tableau === "function" ? tableau(String(url)) : reponse(200, tableau);
      if (String(url) === "/api/schedule/analytics/refresh") return reponse(releve, {});
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
  ok("1.18 relever : POST refresh puis relecture", m.appels.slice(avant).map((a) => a.methode + " " + a.url.split("?")[0]).join()
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

if (echecs.length) { console.log("ÉCHECS (" + echecs.length + "/" + n + ") :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("croissance : OK (" + n + " vérifications)");
