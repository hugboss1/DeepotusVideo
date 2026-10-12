// qa/iacalque.test.mjs — t191 (G9) : le calque IA et « Retirer le fond du calque » du Photolab (mod-iacalque.js).
// Fonctions pures (corps de /calque/ia et /calque/detourer, refus AVANT tout POST, devis, prix), le tir (cycle puis
// sélection, une pose sans calque ne s'annonce jamais), le panneau TEL QU'IL TOURNE sous le faux DOM (aucun `disabled`
// pour une clé manquante, ses gestes n'atteignent ni la toile ni les raccourcis du document, anti-double tir), le bouton
// « IA » du pied du panneau Calques et les deux entrées ACTIVES du menu Calque.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { installerFauxDom } from "./outils/faux-dom.mjs";
import {
  TAILLES, taillePour, requete, requeteDetour, verifierCible, calquesCibles, verifierDetour, devisCorps, libellePrix,
  messageErreur, unSeulVol, executerPlan, initIaCalque, GESTES_GARDES, nomCalqueIa,
} from "../js/mod-iacalque.js";
import { construireMenus, REFUSES, NECESSITE_DOC, actionEntree, IDS_IA } from "../js/mod-menus.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, typeof detail === "string" ? detail : JSON.stringify(detail)); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const json = (x) => JSON.stringify(x);
const pause = (ms = 5) => new Promise((r) => setTimeout(r, ms));
const rejette = async (p) => { try { await p; return null; } catch (e) { return e; } };

// le document du banc : Fond (1), Calque 1 (2), Groupe (3) > Dans le groupe (4), Réglage (5)
const DOC = { width: 1600, height: 900, activeLayer: 2, layers: [
  { id: 5, name: "Réglage", kind: "Adjustment" },
  { id: 3, name: "Groupe", kind: "Group", children: [{ id: 4, name: "Dans le groupe", kind: "Pixel" }] },
  { id: 2, name: "Calque 1", kind: "Pixel" },
  { id: 1, name: "Fond", kind: "Pixel" }] };

// 1. pur
check("1.1 taillePour : 16:9 -> landscape_16_9, carré -> square_hd, portrait 2:3 -> portrait_4_3, vide -> square_hd",
  taillePour(DOC) === "landscape_16_9" && taillePour({ width: 500, height: 500 }) === "square_hd"
  && taillePour({ width: 400, height: 600 }) === "portrait_4_3" && taillePour(null) === "square_hd" && TAILLES.length === 5);
check("1.2 requete -> le corps EXACT de /calque/ia (prompt rogné, format, cible, détourage + sujet)",
  json(requete({ prompt: "  un chat ", modele: "flux", taille: "landscape_16_9", auDessusDe: 2, detourer: true, modeleDetour: "sam3-sujet", sujet: " le chat " }))
  === json({ prompt: "un chat", taille: "landscape_16_9", auDessusDe: 2, detourer: true, modele: "flux", modeleDetour: "sam3-sujet", sujet: "le chat" }));
check("1.3 requete sans détourage : ni modeleDetour ni sujet ; format inconnu -> square_hd ; nom gardé",
  json(requete({ prompt: "x", taille: "a4", auDessusDe: 1, sujet: "y", nom: " Mon calque " }))
  === json({ prompt: "x", taille: "square_hd", auDessusDe: 1, detourer: false, nom: "Mon calque" }));
const leve = (f) => { try { f(); return null; } catch (e) { return e.message; } };
check("1.4 prompt vide refusé ; détourage sans modèle refusé", leve(() => requete({ prompt: "  ", auDessusDe: 1 })) === "photolab.iacalque.prompt_vide"
  && leve(() => requete({ prompt: "x", auDessusDe: 1, detourer: true })) === "photolab.iacalque.detour_modele");
check("1.5 requeteDetour -> {layer, modele, sujet?}", json(requeteDetour({ calque: 2, modeleDetour: "bria-rmbg", sujet: " " })) === json({ layer: 2, modele: "bria-rmbg" }));
check("1.6 verifierCible : groupe, verrouillé, absent refusés ; réglage refusé au détourage seulement",
  leve(() => verifierCible(DOC, {}, 3)) === "photolab.iacalque.calque_groupe" && leve(() => verifierCible(DOC, { 2: { all: true } }, 2)) === "photolab.iacalque.calque_verrouille"
  && leve(() => verifierCible(DOC, {}, 99)) === "photolab.iacalque.calque_absent" && verifierCible(DOC, {}, 5).id === 5
  && leve(() => verifierCible(DOC, {}, 5, "detour")) === "photolab.iacalque.calque_reglage" && verifierCible(DOC, { 2: { all: false } }, 2).id === 2);
check("1.7 calquesCibles : haut -> bas, sans groupe ni verrouillé (le calque d'un groupe reste visable)",
  json(calquesCibles(DOC, { 1: { pixels: true } }).map((c) => c.id)) === json([5, 4, 2])
  && json(calquesCibles(DOC, {}, "detour").map((c) => c.id)) === json([4, 2, 1]));
check("1.8 verifierDetour : clé absente (dispo:false) et sujet exigé refusés AVANT tout POST",
  leve(() => verifierDetour({ detourer: true, modeleDetour: "bria-rmbg" }, { dispo: false, cle: "FAL_KEY" })) === "photolab.iacalque.detour_cle"
  && leve(() => verifierDetour({ detourer: true, modeleDetour: "sam3-sujet" }, { prompt: true })) === "photolab.iacalque.sujet_requis"
  && leve(() => verifierDetour({ detourer: false }, { dispo: false })) === null);
check("1.9 devisCorps : campagne image + détourage ; aucun devis sans modèle ; mode détour = détourage seul",
  json(devisCorps({ modele: "flux", detourer: true, modeleDetour: "bria-rmbg" })) === json({ kind: "campaign", ops: [{ kind: "image", model: "flux", n: 1 }, { kind: "detourage", modele: "bria-rmbg", images: 1 }] })
  && devisCorps({ modele: "" }) === null && json(devisCorps({ mode: "detour", modeleDetour: "x" })) === json({ kind: "campaign", ops: [{ kind: "detourage", modele: "x", images: 1 }] })
  && devisCorps({ mode: "detour" }) === null);
check("1.10 libellePrix : 0 $ payant = « à mesurer », jamais « gratuit » ; local à 0 $ = gratuit ; part à mesurer dite",
  libellePrix({ total_usd: 0, breakdown: [{ usd: 0, provider: "fal" }] }) === "photolab.iacalque.prix_a_mesurer"
  && libellePrix({ total_usd: 0, breakdown: [{ usd: 0, provider: "local" }] }) === "photolab.iacalque.gratuit"
  && libellePrix({ total_usd: 0.021, breakdown: [{ usd: 0.003, provider: "fal" }, { usd: 0, provider: "fal" }] }).endsWith("photolab.iacalque.prix_partiel")
  && libellePrix(null) === "photolab.iacalque.prix_inconnu");
check("1.11 messageErreur : 503 = clé absente, 402 = message du plafond", messageErreur(503, { detail: "FAL_KEY non configurée" }) === "photolab.iacalque.cle_absente"
  && messageErreur(402, { detail: { dz_plafond: { message: "plafond" } } }) === "plafond" && messageErreur(409, { detail: "aucun document" }) === "aucun document");
check("1.12 nomCalqueIa : la clé du dictionnaire (« IA — {debut} »)", nomCalqueIa("un phare sous la pluie") === "photolab.iacalque.nom_calque");

// 2. le tir
const faux = (sur = {}) => {
  const j = { posts: [], cycles: 0, selections: [] };
  const d = {
    doc: () => DOC, verrous: () => ({ 1: { all: true } }),
    post: async (chemin, corps) => { j.posts.push([chemin, corps]); return sur.reponse !== undefined ? sur.reponse : { layer: 7, bounds: [0, 0, 1600, 900], usd: 0.003 }; },
    cycle: async () => { j.cycles++; },
    selectionner: async (id) => { j.selections.push(id); },
    infoDetour: async (id) => (sur.info || {})[id] || null,
  };
  return { d, j };
};
let f = faux();
let e = await rejette(executerPlan({ prompt: "x", auDessusDe: 3 }, f.d));
check("2.1 cible = groupe : refusé SANS appel", e && e.message === "photolab.iacalque.calque_groupe" && f.j.posts.length === 0);
e = await rejette(executerPlan({ prompt: "x", auDessusDe: 1 }, f.d));
check("2.2 cible verrouillée : refusée SANS appel", e && e.message === "photolab.iacalque.calque_verrouille" && f.j.posts.length === 0);
f = faux({ info: { "sam3-sujet": { prompt: true }, "bria-rmbg": { dispo: false, cle: "FAL_KEY" } } });
e = await rejette(executerPlan({ prompt: "x", auDessusDe: 2, detourer: true, modeleDetour: "sam3-sujet" }, f.d));
const e2 = await rejette(executerPlan({ prompt: "x", auDessusDe: 2, detourer: true, modeleDetour: "bria-rmbg" }, f.d));
check("2.3 sujet exigé / clé du détourage absente : refusés AVANT le POST (catalogue dispo:false)",
  e && e.message === "photolab.iacalque.sujet_requis" && e2 && e2.message === "photolab.iacalque.detour_cle" && f.j.posts.length === 0);
f = faux();
let r = await executerPlan({ prompt: "un phare", modele: "flux", taille: "landscape_16_9", auDessusDe: 2 }, f.d);
check("2.4 tir : UN POST /calque/ia avec le corps de requete(), puis un cycle, puis la sélection du nouveau calque (7)",
  json(f.j.posts) === json([["/calque/ia", { prompt: "un phare", taille: "landscape_16_9", auDessusDe: 2, detourer: false, modele: "flux" }]])
  && f.j.cycles === 1 && json(f.j.selections) === json([7]) && r.layer === 7);
f = faux({ reponse: { image: "gen_1.png" } });
e = await rejette(executerPlan({ prompt: "x", auDessusDe: 2 }, f.d));
check("2.5 réponse sans calque posé : lève (jamais « posé » annoncé), le nom de l'image est dit",
  e && e.message === "photolab.iacalque.pose_inconnue" && f.j.cycles === 0);
f = faux();
f.d.post = async () => { throw new Error("503 clé"); };
e = await rejette(executerPlan({ prompt: "x", auDessusDe: 2 }, f.d));
check("2.6 un échec du POST remonte tel quel (aucun cycle, aucune sélection)", e && e.message === "503 clé" && f.j.cycles === 0);
f = faux();
r = await executerPlan({ mode: "detour", calque: 2, modeleDetour: "bria-rmbg" }, f.d);
check("2.7 détour : POST /calque/detourer {layer, modele}", json(f.j.posts) === json([["/calque/detourer", { layer: 2, modele: "bria-rmbg" }]]) && r.layer === 7);
let n = 0;
const g = unSeulVol(async () => { n++; await pause(10); return 1; });
const [a1, a2] = await Promise.all([g(), g()]);
check("2.8 unSeulVol : le second appel pendant le vol ne relance rien", n === 1 && a1 === 1 && a2 === null && g.enVol === false);

// 3. le panneau sous le faux DOM
const doc = installerFauxDom();
const scene = doc.createElement("main"); scene.id = "scene";
const toile = doc.createElement("canvas"); toile.id = "toile";
scene.appendChild(toile); doc.body.appendChild(scene);
const vus = { toile: 0, docPointer: 0, docKey: 0 };
toile.addEventListener("pointerdown", () => { vus.toile++; });
doc.addEventListener("pointerdown", () => { vus.docPointer++; });
doc.addEventListener("keydown", () => { vus.docKey++; });
// le VRAI catalogue des modèles (shared/dz-modeles-ia.js) sur un faux fetch : un modèle SANS clé (dispo:false)
const CATAL = {
  image: [{ id: "flux", label: "FLUX", voie: "fal", usd: 0.003, unite: "image", dispo: false, cle: "FAL_KEY", sortie: "raster" },
    { id: "recraft-4.1-vecteur", label: "Recraft", voie: "fal", usd: 0.08, unite: "image", dispo: true, sortie: "svg" }],
  detourage_image: [{ id: "bria-rmbg", label: "Bria", voie: "fal", usd: 0.018, unite: "image", dispo: false, cle: "FAL_KEY", prompt: false },
    { id: "sam3-sujet", label: "SAM 3", voie: "fal", usd: 0.005, unite: "image", dispo: true, cle: "FAL_KEY", prompt: true }],
};
const fetches = [];
globalThis.window.fetch = async (url, opts) => {
  fetches.push([url, opts && opts.body]);
  const m = /nature=([a-z_]+)/.exec(url);
  if (m) return { ok: true, json: async () => ({ modeles: CATAL[m[1]] }) };
  return { ok: true, json: async () => ({ total_usd: 0.021, breakdown: [{ usd: 0.003, provider: "fal" }, { usd: 0.018, provider: "fal" }] }) };
};
globalThis.window.innerWidth = 1280; globalThis.window.innerHeight = 800;
vm.runInThisContext(readFileSync(join(racine, "..", "shared", "dz-modeles-ia.js"), "utf8"));
check("3.0 le vrai DzModelesIA est chargé", !!(globalThis.window.DzModelesIA && globalThis.window.DzModelesIA.remplir));
const posts = [], signaux = [];
let reponse = { layer: 9, bounds: [0, 0, 1600, 900], usd: 0.003, nom: "IA — un phare" };
const PL = {
  etat: { doc: DOC, verrous: {} }, surDoc: [], actions: {},
  $: (s) => (s === "#scene" ? scene : null), icone: () => "",
  signaler: (t, err) => signaux.push([t, !!err]),
  file: (fn) => fn(),
  api: async (m, chemin, corps) => { posts.push([m, chemin, corps]); await pause(15); return reponse; },
  cycle: async () => {}, executer: async () => ({ ok: true }),
};
initIaCalque(PL);
check("3.1 PL.actions pl.calque.ia / pl.calque.detourer branchées", typeof PL.actions["pl.calque.ia"] === "function" && typeof PL.actions["pl.calque.detourer"] === "function");
PL.iaCalque.ouvrir(2);
await pause(30);
const ui = PL.iaCalque.ui, boite = PL.iaCalque.boite;
check("3.2 le panneau est dans document.body, HORS de #scene (la toile n'est pas son ancêtre)", boite.parentNode === doc.body && !scene.contains(boite));
check("3.3 le prompt porte data-dz-ia, le calque visé est « Calque 1 » (2), la phrase « au-dessus de » est dite",
  ui.prompt.getAttribute("data-dz-ia") === "image" && ui.selCalque.value === "2" && ui.lieu.textContent === "photolab.iacalque.lieu");
const opts = (sel) => sel.tous((x) => x.tagName === "OPTION");
check("3.4 modèles : FLUX SANS clé reste CHOISISSABLE (aucun disabled), le modèle vectoriel n'est pas proposé",
  json(opts(ui.selModele).map((o) => o.value)) === json(["flux"]) && opts(ui.selModele).every((o) => !o.disabled) && ui.selModele.value === "flux");
check("3.5 détourage : le modèle sans clé reste choisissable ; le bouton n'est PAS grisé pour une clé",
  opts(ui.selDetour).length === 2 && opts(ui.selDetour).every((o) => !o.disabled) && ui.go.disabled === false);
const src = readFileSync(join(racine, "js", "mod-iacalque.js"), "utf8");
check("3.6 source : le seul `disabled` posé suit le vol et la cible, jamais une clé", (src.match(/\.disabled\s*=/g) || []).length === 1
  && /ui\.go\.disabled = lancer\.enVol \|\| cible == null;/.test(src));
check("3.7 devis serveur : /api/cost/estimate, campagne image seule tant que la case est décochée", fetches.some(([u, b]) => u === "/api/cost/estimate"
  && b === json({ kind: "campaign", ops: [{ kind: "image", model: "flux", n: 1 }] })));
// (a) les gestes du panneau n'atteignent ni la toile ni le document
for (const t of ["pointerdown", "mousedown"]) ui.selModele.envoyer(t);
ui.caseDetour.envoyer("pointerdown");
check("3.8 pointerdown sur un contrôle du panneau : ni la toile ni le document ne le voient", vus.toile === 0 && vus.docPointer === 0, vus);
toile.envoyer("pointerdown");
check("3.9 témoin : un pointerdown sur la toile atteint bien ses écouteurs et le document", vus.toile === 1 && vus.docPointer === 1, vus);
// (b) les raccourcis globaux ne se déclenchent pas depuis un select / bouton du panneau
ui.go.envoyer("keydown", { key: "v" }); ui.selDetour.envoyer("keydown", { key: "Delete" });
check("3.10 une touche sur un bouton / une liste du panneau n'atteint pas les raccourcis du document", vus.docKey === 0, vus);
check("3.11 GESTES_GARDES couvre pointerdown, mousedown, wheel, keydown", ["pointerdown", "mousedown", "wheel", "keydown"].every((t) => GESTES_GARDES.includes(t)));
// sujet : la case + SAM 3 -> le champ sujet apparaît ; sans sujet, le tir est refusé AVANT tout POST
ui.caseDetour.checked = true; ui.caseDetour.envoyer("change");
ui.selDetour.value = "sam3-sujet"; ui.selDetour.envoyer("change");
check("3.12 case cochée + modèle à sujet : la ligne du détourage et le sujet se montrent", ui.ligneDetour.hidden === false && ui.sujet.hidden === false);
ui.prompt.value = "un phare";
ui.go.envoyer("click");
await pause(5);
check("3.13 sujet manquant : refusé AVANT tout POST, dit dans le panneau", posts.length === 0 && ui.etat.textContent === "photolab.iacalque.sujet_requis", [posts.length, ui.etat.textContent]);
// clé du détourage absente (dispo:false) : refusée avant tout POST
ui.selDetour.value = "bria-rmbg"; ui.selDetour.envoyer("change");
ui.go.envoyer("click");
await pause(5);
check("3.14 clé du détourage absente (catalogue dispo:false) : refusé avant tout POST", posts.length === 0 && ui.etat.textContent === "photolab.iacalque.detour_cle");
// anti-double tir : deux clics pendant le vol = UN POST
ui.caseDetour.checked = false; ui.caseDetour.envoyer("change");
ui.go.envoyer("click"); ui.go.envoyer("click");
await pause(5);
check("3.15 pendant le vol : bouton gris « en cours », un second clic ne relance rien", ui.go.disabled === true
  && ui.go.textContent === "photolab.iacalque.en_cours" && posts.length === 1);
await pause(40);
check("3.16 le POST /calque/ia part avec le format du document (16:9) et la cible", posts.length === 1
  && json(posts[0]) === json(["POST", "/calque/ia", { prompt: "un phare", taille: "landscape_16_9", auDessusDe: 2, detourer: false, modele: "flux" }]));
check("3.17 après le vol : bouton rendu, « posé » annoncé", ui.go.disabled === false && ui.etat.textContent === "photolab.iacalque.posee");
// une pose avalée (réponse sans calque) ne s'annonce JAMAIS
reponse = { image: "gen_x.png" };
ui.go.envoyer("click");
await pause(40);
check("3.18 réponse sans calque : erreur dite, jamais « posé »", posts.length === 2 && ui.etat.textContent === "photolab.iacalque.pose_inconnue"
  && signaux.some(([t, err]) => t === "photolab.iacalque.pose_inconnue" && err));
// Échap ferme et le panneau quitte le document
ui.prompt.envoyer("keydown", { key: "Escape" });
check("3.19 Échap ferme le panneau", boite.parentNode === null);
// « Retirer le fond » : le mode détour vise le calque actif, prompt et modèle d'image cachés
reponse = { layer: 11, bounds: [0, 0, 10, 10], usd: 0.018, original: 2 };
PL.iaCalque.retirerFond(2);
await pause(30);
check("3.20 Retirer le fond : panneau en mode détour (prompt et modèle cachés, ligne du détourage visible)",
  ui.prompt.hidden === true && ui.ligneModele.hidden === true && ui.ligneDetour.hidden === false && ui.lieu.textContent === "photolab.iacalque.lieu_detour");
PL.iaCalque.fermer();
PL.iaCalque.retirerFond(5);
check("3.21 un calque de réglage n'est pas proposé au détourage (cible repliée sur un calque de pixels)", ui.selCalque.value !== "5"
  && signaux.some(([t]) => t === "photolab.iacalque.calque_reglage"));
PL.iaCalque.fermer();

// 4. le bouton « IA » du pied du panneau Calques, et les entrées du menu Calque
const calques = readFileSync(join(racine, "js", "mod-calques.js"), "utf8");
check("4.1 mod-calques : le bouton du pied porte data-act=\"ia\", est dans le pied et ouvre PL.iaCalque",
  /bIa\.dataset\.act = "ia";/.test(calques) && /pied\.append\([^)]*\bbIa\b/.test(calques) && /bIa\.addEventListener\("click", \(\) => \{ if \(PL\.iaCalque\) PL\.iaCalque\.ouvrir\(actif\(\)\); \}\);/.test(calques));
const catalogue = JSON.parse(readFileSync(join(racine, "donnees", "menus.json"), "utf8"));
const menus = construireMenus(catalogue, [{ id: "layer.duplicate", params: "{}", champs: [] }], REFUSES, "fr", (k) => k);
const calque = menus.find((m) => m.nom === "Layer");
const k = calque.entrees.findIndex((x) => x.id === "layer.duplicate");
const ia = calque.entrees[k + 1], det = calque.entrees[k + 2];
check("4.2 Calque › « Nouveau calque IA… » puis « Retirer le fond du calque », juste après Dupliquer, ACTIVES (pas « bientôt »)",
  ia && ia.id === "pl.calque.ia" && ia.etat === "actif" && ia.libelle === "photolab.menu.calque_ia"
  && det && det.id === "pl.calque.detourer" && det.etat === "actif" && det.libelle === "photolab.menu.retirer_fond", [ia, det]);
check("4.3 un clic va à l'écran (PL.actions), grisées sans document", actionEntree(ia) === "ecran" && actionEntree(det) === "ecran"
  && IDS_IA.every((id) => NECESSITE_DOC.has(id)));
check("4.4 le catalogue amont (menus.json) reste intact : 765 lignes, aucune entrée pl.*", catalogue.entrees.length === 765
  && !catalogue.entrees.some((x) => String(x.id || "").startsWith("pl.")));
const html = readFileSync(join(racine, "index.html"), "utf8");
check("4.5 index.html charge dz-modeles-ia.js et dz-champ-ia.js (après dz-plafonds.js, avant les modules)",
  html.indexOf('src="/shared/dz-plafonds.js"') < html.indexOf('src="/shared/dz-modeles-ia.js"')
  && html.indexOf('src="/shared/dz-modeles-ia.js"') < html.indexOf('src="/shared/dz-champ-ia.js"')
  && html.indexOf('src="/shared/dz-champ-ia.js"') < html.indexOf('src="js/core.js"'));

console.log(`iacalque : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
