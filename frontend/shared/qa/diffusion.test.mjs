// t328 tâche 5 (27/10/2026) — dz-diffusion-whatsapp.js : le panneau de diffusion WhatsApp de l'inspecteur du post, joué
// sur un DOM simulé avec un faux fetch (aucun réseau). dz-plafonds.js est chargé dans le même monde : il enveloppe fetch
// et pose son dialogue sur le 402 du plafond, comme dans la SPA.
// Séries : modele_sans_parametres, modele_nomme (et positionnel), audience_vide, plafond_402 (refusé, accepté),
// incertain_409 (dialogue refusé, accepté, pas_incertaine), suivi (compteurs, relire), sans_dialogue, perime, delai,
// liste_explicite, anglais, jamais_de_numero.
// Lancer : node frontend/shared/qa/diffusion.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-diffusion-whatsapp.js", import.meta.url), "utf8");
const PLAF = readFileSync(new URL("../dz-plafonds.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };
const tick = async (k = 4) => { for (let i = 0; i < k; i++) await new Promise((r) => setTimeout(r, 5)); };

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; this.disabled = false; this.type = ""; }
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
  click() { if (!this.disabled) this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tous = (r, p) => [...r.tous()].filter(p);
const attr = (r, a, v) => tous(r, (x) => a in x.attrs && (v === undefined || x.attrs[a] === v));
const un = (r, a, v) => attr(r, a, v)[0] || null;

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
const rep = (status, json) => new Response(JSON.stringify(json === undefined ? {} : json), { status, headers: { "Content-Type": "application/json" } });

// un monde : window = global (dz-plafonds remplace window.fetch, le panneau appelle fetch)
function monde({ lang = "fr", routes = {}, dialogue = [] , sansDialogue = false } = {}) {
  const appels = [], dialogues = [], evenements = [], longs = [];
  const reponses = dialogue.slice();
  const ctx = {
    console, Response, Headers, Request, URL, AbortController, CustomEvent: class { constructor(t) { this.type = t; } },
    location: { href: "http://127.0.0.1:8000/" },
    sessionStorage: { getItem() { return null; }, setItem() {} },
    setTimeout: (f, ms) => { if (ms === 30000) { longs.push(f); return 0; } if (ms >= 2500) return 0; return setTimeout(f, ms); },
    clearTimeout: (i) => { if (i) clearTimeout(i); },
  };
  ctx.window = ctx;
  ctx.dzT = dzTde(lang);
  ctx.dzLang = () => lang;
  ctx.dispatchEvent = (e) => { evenements.push(e.type); };
  ctx.document = { createElement: (t) => new Noeud(t), body: new Noeud("body"), documentElement: new Noeud("html") };
  if (!sansDialogue) ctx.__dzDialogue = { confirmer: (m, o) => { dialogues.push({ m, o }); return Promise.resolve(reponses.length ? reponses.shift() : false); } };
  ctx.fetch = async (url, init = {}) => {
    const m = init.method || "GET";
    const h = init.headers instanceof Headers ? init.headers : new Headers(init.headers || {});
    appels.push({ url: String(url), methode: m, corps: init.body ? JSON.parse(init.body) : undefined, plafond: h.get("X-DZ-Plafond") });
    const f = routes[m + " " + url];
    return f ? f(init.body ? JSON.parse(init.body) : undefined, h) : rep(404, { detail: "absent : " + url });
  };
  vm.createContext(ctx);
  vm.runInContext(PLAF, ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, appels, dialogues, evenements, longs, hote: new Noeud("div"), API: ctx.__dzDiffusionWhatsapp };
}

const MODELES = [
  { nom: "promo_simple", langue: "fr", categorie: "utility", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "approved", meta_id: "m1", composants: { entete: null, boutons: [] } },
  { nom: "bienvenue", langue: "fr", categorie: "marketing", parametres: "nommes", n_parametres: 2, noms_parametres: ["prenom", "code"], statut: "approved", meta_id: "m2", composants: { entete: null, boutons: [] } },
  { nom: "rappel", langue: "en", categorie: "utility", parametres: "positionnels", n_parametres: 2, noms_parametres: ["1", "2"], statut: "approved", meta_id: "m3", composants: { entete: null, boutons: [] } },
  { nom: "affiche", langue: "fr", categorie: "marketing", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "approved", meta_id: "m4", composants: { entete: "image", boutons: [] } },
  { nom: "sans_meta", langue: "fr", categorie: "utility", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "approved", meta_id: "", composants: { entete: null, boutons: [] } },
  { nom: "refuse", langue: "fr", categorie: "utility", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "rejected", meta_id: "m6", composants: { entete: null, boutons: [] } },
  { nom: "entete_var", langue: "fr", categorie: "utility", parametres: "positionnels", n_parametres: 0, noms_parametres: [], statut: "approved", meta_id: "m7", composants: { entete: "text", entete_variable: true, boutons: [] } },
];
const GET = "GET /api/schedule/p1/diffusion", RELIRE = "GET /api/schedule/p1/diffusion?relire=1", PUT = "PUT /api/schedule/p1/diffusion";
const CONF = "POST /api/schedule/p1/diffusion/confirmer", MOD = "GET /api/whatsapp/c_wa/modeles?espace=esp_a";
const VIDE = { config: null, audience: null, devis: null, refus: null, etat: null };
const CFG = (modele, parametres, extra = {}) => ({ compte: "c_wa", modele, parametres, statut: "configuree", n_identites: null, ...extra });
const O = { compte: "c_wa", espace: "esp_a" };
const options = (h) => attr(h, "value").filter((x) => x.tagName === "OPTION").map((x) => x.attrs.value);

// ---- modele_sans_parametres ----------------------------------------------------------------------------------------
{
  let corps = null;
  const m = monde({ routes: {
    [GET]: () => rep(200, VIDE), [MOD]: () => rep(200, MODELES),
    [PUT]: (b) => { corps = b; return rep(200, { config: CFG({ nom: "promo_simple", langue: "fr", categorie: "utility" }, []), audience: { n: 3, ecartes: { accord: 2, stop: 1, marketing: 0, bsuid: 0 } }, devis: { usd: 0.045, lignes: [] }, post: { id: "p1" } }); },
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  ok("1.1 GET de la diffusion puis des modèles du compte (espace en paramètre)", m.appels[0].url === "/api/schedule/p1/diffusion" && m.appels[1].url === "/api/whatsapp/c_wa/modeles?espace=esp_a", JSON.stringify(m.appels));
  ok("1.2 seuls les modèles approuvés, avec identifiant Meta, sans en-tête média ni en-tête texte variable",
    JSON.stringify(options(m.hote)) === JSON.stringify(["promo_simple|fr", "bienvenue|fr", "rappel|en"]), JSON.stringify(options(m.hote)));
  ok("1.3 la catégorie est affichée (option et ligne)", un(m.hote, "data-dz-diffusion-categorie").textContent === FR("diffusion.modele.categorie", { categorie: FR("diffusion.categorie.utility") })
    && m.hote.textContent.includes(FR("diffusion.modele.option", { nom: "bienvenue", langue: "fr", categorie: FR("diffusion.categorie.marketing") })));
  ok("1.4 sans paramètre : la note, aucun champ", un(m.hote, "data-dz-diffusion-note", "sans_parametre") && !attr(m.hote, "data-dz-diffusion-param").length);
  ok("1.5 pas encore de config : l'audience viendra après l'enregistrement, bouton libre", m.hote.textContent.includes(FR("diffusion.audience.apres"))
    && !un(m.hote, "data-dz-diffusion-enregistrer").disabled);
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("1.6 PUT au format EXACT", JSON.stringify(corps) === JSON.stringify({ modele: { nom: "promo_simple", langue: "fr" }, parametres: [] }), JSON.stringify(corps));
  ok("1.7 audience « 3 contacts » et écartés avec leurs raisons", un(m.hote, "data-dz-diffusion-audience").textContent.includes(FR("diffusion.audience.n", { n: 3 }))
    && un(m.hote, "data-dz-diffusion-ecartes").textContent === FR("diffusion.audience.ecartes", { n: 3, detail: FR("diffusion.ecarte.accord", { n: 2 }) + ", " + FR("diffusion.ecarte.stop", { n: 1 }) }),
    un(m.hote, "data-dz-diffusion-audience").textContent);
  ok("1.8 devis en dollars (0,045 $)", un(m.hote, "data-dz-diffusion-devis").textContent === FR("diffusion.devis.montant", { montant: "0,045" }), un(m.hote, "data-dz-diffusion-devis")?.textContent);
  ok("1.9 message d'enregistrement et relecture de la liste des posts demandée", un(m.hote, "data-dz-diffusion-msg").textContent === FR("diffusion.etat.enregistree")
    && m.evenements.includes("deepotus:schedule-recharger"));
  ok("1.10 idempotent : remonter le même nœud pour le même post ne relit rien", await m.API.monter(m.hote, "p1", O) === null && m.appels.filter((a) => a.url.startsWith("/api/schedule")).length === 2);
}

// ---- modele_nomme (et positionnel) ---------------------------------------------------------------------------------
{
  const corps = [];
  const m = monde({ routes: {
    [GET]: () => rep(200, VIDE), [MOD]: () => rep(200, MODELES),
    [PUT]: (b) => { corps.push(b); return rep(200, { config: CFG({ nom: b.modele.nom, langue: b.modele.langue }, b.parametres), audience: { n: 5, ecartes: { accord: 0, stop: 0, marketing: 1, bsuid: 2 } }, devis: { usd: 1.2, lignes: [] } }); },
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  const sel = un(m.hote, "data-dz-diffusion-modele");
  sel.value = "bienvenue|fr"; sel.fire("change");
  const champs = attr(m.hote, "data-dz-diffusion-param");
  ok("2.1 modèle nommé : un champ par nom, libellé nommé", champs.map((c) => c.attrs["data-dz-diffusion-param"]).join(",") === "prenom,code"
    && m.hote.textContent.includes(FR("diffusion.parametre.nomme", { nom: "prenom" })));
  ok("2.2 catégorie marketing affichée", un(m.hote, "data-dz-diffusion-categorie").textContent.includes(FR("diffusion.categorie.marketing")));
  champs[0].value = "Ana"; champs[0].fire("input");
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("2.3 un paramètre vide : refus dit, aucun PUT, la saisie est gardée", !corps.length && un(m.hote, "data-dz-diffusion-erreur").textContent === FR("diffusion.parametre.vide")
    && attr(m.hote, "data-dz-diffusion-param")[0].value === "Ana");
  const ch2 = attr(m.hote, "data-dz-diffusion-param");
  ch2[1].value = "X1"; ch2[1].fire("input");
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("2.4 PUT nommé : objet {prenom, code}", JSON.stringify(corps[0]) === JSON.stringify({ modele: { nom: "bienvenue", langue: "fr" }, parametres: { prenom: "Ana", code: "X1" } }), JSON.stringify(corps));
  ok("2.5 écartés : désinscrits du marketing et identités non confirmées", un(m.hote, "data-dz-diffusion-ecartes").textContent
    === FR("diffusion.audience.ecartes", { n: 3, detail: FR("diffusion.ecarte.marketing", { n: 1 }) + ", " + FR("diffusion.ecarte.bsuid", { n: 2 }) }));
  ok("2.6 après PUT : le modèle rangé reste choisi, ses paramètres pré-remplis", un(m.hote, "data-dz-diffusion-modele").value === "bienvenue|fr"
    && attr(m.hote, "data-dz-diffusion-param").map((c) => c.value).join(",") === "Ana,X1");
  const s2 = un(m.hote, "data-dz-diffusion-modele");
  s2.value = "rappel|en"; s2.fire("change");
  const pos = attr(m.hote, "data-dz-diffusion-param");
  pos[0].value = "lundi"; pos[0].fire("input"); pos[1].value = "9h"; pos[1].fire("input");
  ok("2.7 positionnel : libellé « Paramètre 1 »", m.hote.textContent.includes(FR("diffusion.parametre.position", { nom: "1" })));
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("2.8 PUT positionnel : liste ordonnée", JSON.stringify(corps[1]) === JSON.stringify({ modele: { nom: "rappel", langue: "en" }, parametres: ["lundi", "9h"] }), JSON.stringify(corps[1]));
}

// ---- audience_vide -------------------------------------------------------------------------------------------------
{
  let puts = 0;
  const m = monde({ routes: {
    [GET]: () => rep(200, { config: CFG({ nom: "bienvenue", langue: "fr", categorie: "marketing" }, { prenom: "A", code: "B" }), audience: { n: 0, ecartes: { accord: 4, stop: 0, marketing: 0, bsuid: 0 } }, devis: { usd: 0, lignes: [] }, refus: null, etat: { statut: "configuree", incertain: false } }),
    [MOD]: () => rep(200, MODELES), [PUT]: () => { puts++; return rep(200, {}); },
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  ok("3.1 audience vide : « 0 contacts », message d'alerte", un(m.hote, "data-dz-diffusion-audience").textContent.includes(FR("diffusion.audience.n", { n: 0 }))
    && un(m.hote, "data-dz-diffusion-vide").textContent === FR("diffusion.audience.vide"));
  ok("3.2 bouton « Enregistrer la diffusion » grisé ; un clic ne part pas", un(m.hote, "data-dz-diffusion-enregistrer").disabled === true
    && un(m.hote, "data-dz-diffusion-enregistrer").hasAttribute("disabled"));
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("3.3 aucun PUT", puts === 0);
  ok("3.4 le modèle rangé est choisi et ses paramètres pré-remplis", un(m.hote, "data-dz-diffusion-modele").value === "bienvenue|fr"
    && attr(m.hote, "data-dz-diffusion-param").map((c) => c.value).join(",") === "A,B");
  const s = un(m.hote, "data-dz-diffusion-modele"); s.value = "promo_simple|fr"; s.fire("change");
  ok("3.5 un autre modèle choisi : le bouton se libère (l'audience change avec la catégorie)", un(m.hote, "data-dz-diffusion-enregistrer").disabled === false);
}

// ---- incertain_409 : le dialogue (refusé, accepté), pas_incertaine -------------------------------------------------
const INCERTAIN = { config: CFG({ nom: "promo_simple", langue: "fr", categorie: "utility" }, [], { statut: "envoi", incertain: true }), audience: { n: 3, ecartes: {} }, devis: { usd: 0.05, lignes: [] },
  etat: { statut: "envoi", broadcast_id: "b1", n: 3, incertain: true, attente_confirmation: false, compteurs: {} } };
{
  let posts = 0, corps = null, etat = INCERTAIN;
  const m = monde({ dialogue: [false, true], routes: {
    [GET]: () => rep(200, etat), [MOD]: () => rep(200, MODELES),
    [CONF]: (b) => { posts++; corps = b; etat = { ...INCERTAIN, etat: { statut: "sending", broadcast_id: "b2", n: 3, incertain: false, compteurs: { sent: 1 } } }; return rep(200, { diffusion: { broadcast_id: "b2", statut: "sending", n: 3, incertain: false }, post: { id: "p1", status: "posted" } }); },
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  ok("4.1 incertaine : explication et « Confirmer l'envoi », aucun formulaire", un(m.hote, "data-dz-diffusion-incertain", "incertain")?.textContent === FR("diffusion.incertain.texte")
    && un(m.hote, "data-dz-diffusion-confirmer").textContent === FR("diffusion.action.confirmer") && !un(m.hote, "data-dz-diffusion-modele")
    && !m.appels.some((a) => a.url.includes("/modeles")));
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick();
  ok("4.2 le dialogue maison est ouvert, son texte AVERTIT des autres canaux (N3), danger", m.dialogues.length === 1 && m.dialogues[0].m === FR("diffusion.confirmer.texte")
    && /autres canaux/.test(m.dialogues[0].m) && m.dialogues[0].o.danger === true && m.dialogues[0].o.ok === FR("diffusion.confirmer.ok"), JSON.stringify(m.dialogues));
  ok("4.3 refusé : rien ne part", posts === 0);
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick(6);
  ok("4.4 accepté : POST {confirme_incertain: true} exact", posts === 1 && JSON.stringify(corps) === JSON.stringify({ confirme_incertain: true }), JSON.stringify(corps));
  ok("4.5 après l'envoi : relu, suivi « en cours d'envoi », message, liste des posts relue", un(m.hote, "data-dz-diffusion-statut", "sending")
    && un(m.hote, "data-dz-diffusion-msg")?.textContent === FR("diffusion.etat.confirmee") && m.evenements.includes("deepotus:schedule-recharger")
    && !un(m.hote, "data-dz-diffusion-confirmer"), m.hote.textContent);
}
{
  let gets = 0;
  const m = monde({ dialogue: [true], routes: {
    [GET]: () => { gets++; return rep(200, gets === 1 ? INCERTAIN : { ...INCERTAIN, etat: { statut: "completed", n: 3, incertain: false, compteurs: { sent: 3 } } }); },
    [CONF]: () => rep(409, { detail: { message: "aucune diffusion à l'issue incertaine à confirmer pour ce post : publiez-le normalement", code: "pas_incertaine" } }),
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick(6);
  ok("4.6 409 pas_incertaine : message du serveur, diffusion relue (terminée)", gets === 2 && un(m.hote, "data-dz-diffusion-erreur")?.textContent.startsWith("aucune diffusion")
    && un(m.hote, "data-dz-diffusion-statut", "completed"), m.hote.textContent);
}
{
  // PUT refusé 409 « incertain » / « deja_lancee » : la diffusion est relue et le suivi montre la confirmation
  let gets = 0;
  const m = monde({ routes: {
    [GET]: () => { gets++; return rep(200, gets === 1 ? VIDE : INCERTAIN); }, [MOD]: () => rep(200, MODELES),
    [PUT]: () => rep(409, { detail: { message: "une diffusion de ce post est déjà lancée : elle ne se modifie plus", code: "deja_lancee" } }),
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick(6);
  ok("4.7 PUT 409 deja_lancee : relu, suivi incertain avec « Confirmer l'envoi », message gardé", gets === 2 && un(m.hote, "data-dz-diffusion-confirmer")
    && un(m.hote, "data-dz-diffusion-erreur")?.textContent.startsWith("une diffusion"), m.hote.textContent);
}
{
  const m = monde({ routes: { [GET]: () => rep(200, { ...INCERTAIN, etat: { ...INCERTAIN.etat, incertain: true, attente_confirmation: true } }) } });
  await m.API.monter(m.hote, "p1", O); await tick();
  ok("4.8 en attente de confirmation (Kapso dit brouillon) : son explication", un(m.hote, "data-dz-diffusion-incertain", "attente")?.textContent === FR("diffusion.incertain.attente"));
}

// ---- plafond_402 : le dialogue de dz-plafonds (refusé, accepté) ----------------------------------------------------
const PLAFOND = { detail: { dz_plafond: { motif: "global", message: "Ce tir dépasserait le plafond mensuel. Confirmez pour tirer quand même, ou relevez le plafond.", deja_usd: 9, devis_usd: 2, plafond_usd: 10 } } };
{
  let posts = 0;
  const m = monde({ dialogue: [true, false], routes: { [GET]: () => rep(200, INCERTAIN), [CONF]: () => { posts++; return rep(402, PLAFOND); } } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick(8);
  ok("5.1 402 : le dialogue du plafond (dz-plafonds) suit la confirmation", m.dialogues.length === 2 && m.dialogues[1].o.titre === "Plafond de dépense mensuel", JSON.stringify(m.dialogues.map((d) => d.o)));
  ok("5.2 plafond refusé : un seul POST, le message « annulé » dit dans le panneau, bouton rendu", posts === 1
    && /Annulé : rien n'a été envoyé/.test(un(m.hote, "data-dz-diffusion-erreur")?.textContent || "") && un(m.hote, "data-dz-diffusion-confirmer").disabled === false,
    un(m.hote, "data-dz-diffusion-erreur")?.textContent);
}
{
  let essais = [];
  const m = monde({ dialogue: [true, true], routes: {
    [GET]: () => rep(200, essais.length > 1 ? { ...INCERTAIN, etat: { statut: "sending", n: 3, incertain: false, compteurs: {} } } : INCERTAIN),
    [CONF]: (b, h) => { essais.push(h.get("X-DZ-Plafond")); return essais.length === 1 ? rep(402, PLAFOND) : rep(200, { diffusion: { statut: "sending" }, post: {} }); },
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick(10);
  ok("5.3 plafond accepté : la même requête rejouée avec X-DZ-Plafond: confirme, puis suivi relu", JSON.stringify(essais) === JSON.stringify([null, "confirme"])
    && un(m.hote, "data-dz-diffusion-statut", "sending"), JSON.stringify(essais) + " " + m.hote.textContent);
}

// ---- suivi : statut, compteurs, coût réel, relire ------------------------------------------------------------------
{
  const urls = [];
  const SUIVI = { config: CFG({ nom: "promo_simple", langue: "fr" }, [], { statut: "completed" }), audience: { n: 10, ecartes: {} }, devis: { usd: 0.5, lignes: [] },
    etat: { statut: "completed", broadcast_id: "b1", n: 10, incertain: false, attente_confirmation: false, compteurs: { total: 10, sent: 8, failed: 1, suppressed: 1, delivered: 7, read: 4, livres: 7, lus: 5 }, reel_usd: 0.4 } };
  const m = monde({ routes: { [GET]: () => { urls.push("g"); return rep(200, SUIVI); }, [RELIRE]: () => { urls.push("r"); return rep(200, SUIVI); } } });
  await m.API.monter(m.hote, "p1", O); await tick();
  const txt = (k) => un(m.hote, "data-dz-diffusion-compteur", k)?.textContent;
  ok("6.1 statut « terminée » et destinataires", un(m.hote, "data-dz-diffusion-statut", "completed").textContent
    === FR("diffusion.statut.ligne", { statut: FR("diffusion.statut.completed") }) + " · " + FR("diffusion.suivi.n", { n: 10 }));
  ok("6.2 compteurs : envoyés, livrés, lus (relecture complète d'abord), échecs, retirés du marketing",
    txt("envoyes") === FR("diffusion.compteur.envoyes", { n: 8 }) && txt("livres") === FR("diffusion.compteur.livres", { n: 7 }) && txt("lus") === FR("diffusion.compteur.lus", { n: 5 })
    && txt("echecs") === FR("diffusion.compteur.echecs", { n: 1 }) && txt("retires") === FR("diffusion.compteur.retires", { n: 1 }), [txt("envoyes"), txt("lus")].join("|"));
  ok("6.3 coût réel en dollars, aucun bouton de confirmation", un(m.hote, "data-dz-diffusion-reel").textContent === FR("diffusion.suivi.reel", { montant: "0,40" }) && !un(m.hote, "data-dz-diffusion-confirmer"));
  un(m.hote, "data-dz-diffusion-relire").click(); await tick();
  ok("6.4 « Relire » : GET ?relire=1", urls.join("") === "gr", urls.join(""));
}

// ---- sans_dialogue -------------------------------------------------------------------------------------------------
{
  let posts = 0;
  const m = monde({ sansDialogue: true, routes: { [GET]: () => rep(200, INCERTAIN), [CONF]: () => { posts++; return rep(200, {}); } } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick();
  ok("7.1 sans boîte de dialogue : rien ne part, la raison est dite", posts === 0 && un(m.hote, "data-dz-diffusion-erreur")?.textContent === FR("diffusion.confirmer.sans_dialogue"));
}

// ---- perime : une réponse périmée est ignorée ----------------------------------------------------------------------
{
  let lacher = null, gets = 0;
  const m = monde({ routes: {
    [GET]: () => { gets++; return rep(200, { ...INCERTAIN, etat: { statut: "completed", n: 1, incertain: false, compteurs: { sent: 1 } } }); },
    [RELIRE]: () => new Promise((ok) => { lacher = () => ok(rep(200, { ...INCERTAIN, etat: { statut: "failed", n: 1, incertain: false, compteurs: {} } })); }),
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-relire").click(); await tick();          // relecture lente en vol
  ok("8.0 pendant la relecture : l'état de chargement", !!un(m.hote, "data-dz-diffusion-note", "chargement"));
  const m2 = m.hote.__dzDiffusion;
  m2.jeton++;                                                              // une lecture plus récente a pris la main
  lacher(); await tick();
  ok("8.1 la réponse périmée n'est pas rendue", !un(m.hote, "data-dz-diffusion-statut", "failed"));
}

// ---- delai : 30 s sans réponse -------------------------------------------------------------------------------------
{
  const m = monde({ routes: { [GET]: () => new Promise(() => {}) } });
  m.API.monter(m.hote, "p1", O); await tick();
  ok("9.1 une minuterie de 30 s est posée", m.longs.length === 1);
  m.longs[0](); await tick();
  ok("9.2 au délai : message, bouton « Relire »", un(m.hote, "data-dz-diffusion-erreur")?.textContent === FR("diffusion.erreur.delai") && !!un(m.hote, "data-dz-diffusion-relire"));
}
{
  // la confirmation n'est jamais abandonnée : au délai, un message d'attente ; la réponse tardive est rendue
  let lacher = null;
  const m = monde({ dialogue: [true], routes: { [GET]: () => rep(200, INCERTAIN), [CONF]: () => new Promise((ok) => { lacher = () => ok(rep(502, { detail: { message: "Kapso injoignable", code: "reseau" } })); }) } });
  await m.API.monter(m.hote, "p1", O); await tick();
  un(m.hote, "data-dz-diffusion-confirmer").click(); await tick();
  ok("9.3 pendant l'envoi : « Confirmer » grisé", un(m.hote, "data-dz-diffusion-confirmer").disabled === true);
  m.longs[m.longs.length - 1](); await tick();
  ok("9.4 au délai de la confirmation : message d'attente, pas d'abandon", un(m.hote, "data-dz-diffusion-erreur")?.textContent === FR("diffusion.erreur.attente"));
  lacher(); await tick();
  ok("9.5 la réponse tardive (502) est dite", un(m.hote, "data-dz-diffusion-erreur")?.textContent === "Kapso injoignable");
}

// ---- liste_explicite, jamais_de_numero ------------------------------------------------------------------------------
{
  let puts = 0;
  const cfg = CFG({ nom: "promo_simple", langue: "fr", categorie: "utility" }, [], { n_identites: 2, identites: ["tel:+33612345678", "tel:+33700000000"] });
  const m = monde({ dialogue: [false, true], routes: {
    [GET]: () => rep(200, { config: cfg, audience: { n: 2, ecartes: {} }, devis: { usd: 0.03, lignes: [] }, etat: { statut: "configuree" } }),
    [MOD]: () => rep(200, MODELES), [PUT]: () => { puts++; return rep(200, { config: { ...cfg, n_identites: null }, audience: { n: 9, ecartes: {} }, devis: { usd: 0.1, lignes: [] } }); },
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  ok("10.1 la liste rangée est COMPTÉE, jamais affichée (aucun numéro)", m.hote.textContent.includes(FR("diffusion.audience.liste", { n: 2 })) && !/\+?33\d{6,}|\d{8,}/.test(m.hote.textContent), m.hote.textContent);
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("10.2 enregistrer élargit la liste : confirmation demandée ; refusée, rien ne part", puts === 0 && m.dialogues[0]?.m === FR("diffusion.liste.texte", { n: 2 }));
  un(m.hote, "data-dz-diffusion-enregistrer").click(); await tick();
  ok("10.3 acceptée : PUT", puts === 1);
}

// ---- anglais -------------------------------------------------------------------------------------------------------
{
  const m = monde({ lang: "en", routes: {
    [GET]: () => rep(200, { config: CFG({ nom: "promo_simple", langue: "fr", categorie: "utility" }, []), audience: { n: 3, ecartes: { accord: 1, stop: 0, marketing: 0, bsuid: 0 } }, devis: { usd: 0.045, lignes: [] }, etat: { statut: "configuree" } }),
    [MOD]: () => rep(200, MODELES),
  } });
  await m.API.monter(m.hote, "p1", O); await tick();
  ok("11.1 EN : titre, bouton, audience, écartés", m.hote.textContent.includes(EN("diffusion.panneau.titre")) && un(m.hote, "data-dz-diffusion-enregistrer").textContent === "Save the broadcast"
    && un(m.hote, "data-dz-diffusion-audience").textContent.includes("3 contacts") && un(m.hote, "data-dz-diffusion-ecartes").textContent === "1 left out: 1 without recorded consent",
    m.hote.textContent);
  ok("11.2 EN : devis « Quote: $0.045 », catégorie traduite", un(m.hote, "data-dz-diffusion-devis").textContent === "Quote: $0.045"
    && un(m.hote, "data-dz-diffusion-categorie").textContent === "Category: utility");
  const m2 = monde({ lang: "en", dialogue: [false], routes: { [GET]: () => rep(200, INCERTAIN) } });
  await m2.API.monter(m2.hote, "p1", O); await tick();
  un(m2.hote, "data-dz-diffusion-confirmer").click(); await tick();
  ok("11.3 EN : explication, bouton et dialogue en anglais (avertit des autres canaux)", un(m2.hote, "data-dz-diffusion-confirmer").textContent === "Confirm the send"
    && /other channels not yet sent/.test(m2.dialogues[0]?.m || "") && un(m2.hote, "data-dz-diffusion-incertain").textContent === EN("diffusion.incertain.texte"));
}

// ---- compte absent, modèles illisibles, refus d'audience ------------------------------------------------------------
{
  const m = monde({ routes: { [GET]: () => rep(200, VIDE) } });
  await m.API.monter(m.hote, "p1", {}); await tick();
  ok("12.1 sans compte : note, aucun appel aux modèles", un(m.hote, "data-dz-diffusion-note", "modeles")?.textContent === FR("diffusion.modele.sans_compte") && m.appels.length === 1);
  const m2 = monde({ routes: { [GET]: () => rep(200, { ...VIDE, refus: "consentement" }), [MOD]: () => rep(502, { detail: { message: "clé Kapso absente", code: "cle" } }) } });
  await m2.API.monter(m2.hote, "p1", O); await tick();
  ok("12.2 modèles illisibles : la raison du serveur ; refus d'audience dit", un(m2.hote, "data-dz-diffusion-note", "modeles")?.textContent === FR("diffusion.modele.illisible", { detail: "clé Kapso absente" })
    && m2.hote.textContent.includes(FR("diffusion.audience.refus", { detail: FR("diffusion.refus.consentement") })) && !un(m2.hote, "data-dz-diffusion-enregistrer"));
  const m3 = monde({ routes: { [GET]: () => rep(409, { detail: "ce post doit viser un et un seul compte WhatsApp de son espace pour une diffusion" }) } });
  await m3.API.monter(m3.hote, "p1", O); await tick();
  ok("12.3 GET refusé (409 texte) : message et « Relire »", un(m3.hote, "data-dz-diffusion-erreur")?.textContent.startsWith("ce post doit viser") && !!un(m3.hote, "data-dz-diffusion-relire"));
}

if (echecs.length) { console.log(`ÉCHEC ${echecs.length}/${n}\n  - ` + echecs.join("\n  - ")); process.exit(1); }
console.log(`OK ${n}/${n} (diffusion WhatsApp, FR et EN)`);
