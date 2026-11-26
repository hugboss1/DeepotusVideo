// t501 (26/11/2026) — dz-ig-commentaires.js : « Commentaires au mot-clé » de l'écran Croissance, joué sur un DOM simulé.
// Séries : rendu (compteur, extrait hostile en texte), sans_jeton, relever, gabarit, valider, envoi sans dialogue
// (rien ne part), envoi refusé au dialogue, envoi confirmé (UN brouillon, texte validé, confirme: true), Claude sur
// devis, aucune adresse de messagerie, démontage.
// Lancer : node frontend/shared/qa/ig-commentaires.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-ig-commentaires.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const J = (x) => JSON.parse(JSON.stringify(x));
const tick = () => new Promise((r) => setTimeout(r, 15));

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; }
  get firstChild() { return this.children[0] || null; }
  get parentNode() { return this.parent; }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
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
const marques = (r, v) => tous(r, (x) => x.attrs["data-dz-igcomm"] === v);
const marque = (r, v) => marques(r, v)[0];

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const dzT = (cle, vars) => {
  const e = D[cle];
  if (!e) return cle;
  let s = e.fr;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
  return s;
};
const reponse = (status, json) => ({ ok: status >= 200 && status < 300, status, json: async () => J(json === undefined ? {} : json) });

const HOSTILE = "<img src=x onerror=alert(1)> GUIDE";
function etatServeur() {
  return {
    disponible: true, scope: "instagram_business_manage_comments", reponses_jour: 0, plafond_jour: 30,
    posts: [{ post_id: "p1", title: "Le guide <b>", mot_cle: "GUIDE", au_mot_cle: 3, lus: 9, releve_le: "2026-11-26T10:00:00Z",
      brouillons: [
        { id: "aaaaaaaaaaa1", comment_id: "c1", extrait: HOSTILE, texte: "Merci !", source: "gabarit", statut: "a_valider", fautifs: [] },
        { id: "aaaaaaaaaaa2", comment_id: "c2", extrait: "guide stp", texte: "Merci, la bio.", texte_valide: "Merci, la bio.", source: "claude", statut: "valide", fautifs: [] },
        { id: "aaaaaaaaaaa3", comment_id: "c3", extrait: "GUIDE", texte: "", source: "", statut: "a_rediger", fautifs: [] },
        { id: "aaaaaaaaaaa4", comment_id: "c4", extrait: "", texte: "Merci.", source: "gabarit", statut: "envoye", fautifs: [] }] }],
  };
}

function monde({ dialogue = "aucun", disponible = true } = {}) {
  const appels = [];
  const win = {
    dzT,
    fetch: async (url, init = {}) => {
      const m = init.method || "GET";
      appels.push({ url: String(url), methode: m, corps: init.body ? JSON.parse(init.body) : undefined });
      if (String(url).startsWith("/api/instagram/commentaires/file")) {
        const e = etatServeur();
        e.disponible = disponible;
        return reponse(200, e);
      }
      if (String(url).endsWith("/brouillons/devis")) return reponse(200, { usd: 0.012, n: 1, disponible: true });
      return reponse(200, {});
    },
  };
  if (dialogue !== "aucun") win.__dzDialogue = { confirmer: async () => dialogue === "oui" };
  const doc = { createElement: (t) => new Noeud(t), getElementById: () => null, head: new Noeud("head"), documentElement: new Noeud("html") };
  const ctx = { window: win, document: doc, console };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  const hote = new Noeud("section");
  const inst = win.DzIgCommentaires.monter(hote, { espace: "e1" });
  return { win, hote, inst, appels };
}
const ecritures = (a) => a.filter((x) => x.methode !== "GET");

// rendu
{
  const M = monde();
  await tick();
  ok("rendu_file_par_espace", M.appels[0].url === "/api/instagram/commentaires/file?espace_id=e1", M.appels[0].url);
  ok("rendu_un_post", marques(M.hote, "post").length === 1);
  ok("rendu_titre_en_texte", M.hote.textContent.includes("Le guide <b>"));
  ok("rendu_extrait_hostile_en_texte", marque(M.hote, "extrait").textContent === HOSTILE);
  ok("rendu_compteur", marque(M.hote, "compteur").textContent.includes("3 commentaire(s) au mot-clé sur 9"), marque(M.hote, "compteur").textContent);
  ok("rendu_deux_brouillons_a_decider", marques(M.hote, "brouillon").length === 2);
  ok("rendu_un_seul_bouton_envoyer", marques(M.hote, "envoyer").length === 1);
  ok("rendu_gabarit_et_claude_si_attente", marque(M.hote, "gabarit") && marque(M.hote, "claude"));
  ok("rendu_mot_cle_en_valeur", marque(M.hote, "mot").value === "GUIDE");
  ok("rendu_aucune_ecriture", ecritures(M.appels).length === 0);
}
// sans jeton
{
  const M = monde({ disponible: false });
  await tick();
  ok("sans_jeton_dit_la_permission", marque(M.hote, "etat").textContent.includes("instagram_business_manage_comments")
     && marque(M.hote, "etat").getAttribute("data-erreur") === "1");
}
// relever, gabarit, valider
{
  const M = monde();
  await tick();
  marque(M.hote, "relever").click(); await tick();
  ok("relever_post", ecritures(M.appels).some((x) => x.url === "/api/instagram/commentaires/posts/p1/relever" && x.methode === "POST"));
  marque(M.hote, "gabarit").click(); await tick();
  ok("gabarit_post", ecritures(M.appels).some((x) => x.url.endsWith("/posts/p1/brouillons/gabarit")));
  const zone = marques(M.hote, "texte")[0];
  zone.value = "Merci beaucoup !";
  marques(M.hote, "valider")[0].click(); await tick();
  const v = ecritures(M.appels).find((x) => x.url.endsWith("/brouillons/aaaaaaaaaaa1/valider"));
  ok("valider_un_brouillon_avec_le_texte_relu", v && v.corps.texte === "Merci beaucoup !", JSON.stringify(v));
  marque(M.hote, "mot").value = "RECETTE";
  marque(M.hote, "poser-mot").click(); await tick();
  const pm = ecritures(M.appels).find((x) => x.url.endsWith("/posts/p1/mot-cle"));
  ok("poser_mot_cle", pm && pm.methode === "PUT" && pm.corps.mot_cle === "RECETTE");
  ok("aucun_envoi_implicite", !ecritures(M.appels).some((x) => x.url.endsWith("/envoyer")));
}
// envoi sans dialogue : rien ne part
{
  const M = monde({ dialogue: "aucun" });
  await tick();
  marque(M.hote, "envoyer").click(); await tick();
  ok("envoi_sans_dialogue_rien_ne_part", !M.appels.some((x) => x.url.endsWith("/envoyer")));
}
// envoi refusé au dialogue
{
  const M = monde({ dialogue: "non" });
  await tick();
  marque(M.hote, "envoyer").click(); await tick();
  ok("envoi_refuse_rien_ne_part", !M.appels.some((x) => x.url.endsWith("/envoyer")));
}
// envoi confirmé
{
  const M = monde({ dialogue: "oui" });
  await tick();
  marque(M.hote, "envoyer").click(); await tick();
  const e = M.appels.filter((x) => x.url.endsWith("/envoyer"));
  ok("envoi_confirme_un_seul_brouillon", e.length === 1 && e[0].url === "/api/instagram/commentaires/posts/p1/brouillons/aaaaaaaaaaa2/envoyer", JSON.stringify(e));
  ok("envoi_texte_valide_et_confirme", e[0] && e[0].corps.texte === "Merci, la bio." && e[0].corps.confirme === true, JSON.stringify(e[0]));
  marque(M.hote, "claude").click(); await tick();
  const c = M.appels.filter((x) => x.url.endsWith("/brouillons/claude"));
  ok("claude_sur_devis_accord_du_montant", M.appels.some((x) => x.url.endsWith("/brouillons/devis")) && c.length === 1 && c[0].corps.max_usd === 0.012, JSON.stringify(c));
  ok("aucune_adresse_de_messagerie", !M.appels.some((x) => /messages|private/i.test(x.url)));
  M.inst.demonter();
  ok("demontage", M.hote.children.length === 0);
}

if (echecs.length) { console.log("ÉCHECS (" + echecs.length + "/" + n + ")\n - " + echecs.join("\n - ")); process.exit(1); }
console.log("OK " + n + " cas");
