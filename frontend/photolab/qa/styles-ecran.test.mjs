// qa/styles-ecran.test.mjs — le dialogue Style de calque TEL QU'IL TOURNE (t138 B6) : faux DOM (qa/outils/faux-dom.mjs)
// et faux PL qui enregistre les commandes. Vérifie ce que les fonctions pures ne voient pas : page demandée cochée à
// l'ouverture, titre avec le nom du calque (data-dz-brut), commandes envoyées à OK (une à une, sans cycle, puis UN
// cycle), mémoire des seules étapes réussies avec son repère d'historique, Ctrl+Z -> « non relisible », calque visé
// figé, Réinitialiser, aperçu /apercu {etapes}, rendu réel qui efface l'aperçu, options de fusion relues, Transfert d'un
// groupe ; puis le panneau Calques (bouton fx, badge fx -> layer.select AVANT l'ouverture).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { installerFauxDom } from "./outils/faux-dom.mjs";
import { initStyles, defautsStyle, OPTIONS_FUSION } from "../js/mod-styles.js";
import { initCalques } from "../js/mod-calques.js";
import { construireMenus } from "../js/mod-menus.js";
import { fileFifo } from "../js/mod-cycle.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, typeof detail === "string" ? detail : JSON.stringify(detail)); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const json = (x) => JSON.stringify(x);
const pause = (ms = 5) => new Promise((r) => setTimeout(r, ms));

const doc = installerFauxDom();
// Image : chargée dès que src est posé (chargerImage attend onload).
globalThis.Image = class { set src(v) { this._src = v; setTimeout(() => this.onload && this.onload(), 0); } get src() { return this._src; } };
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));

const appels = [], apercus = [];
let cycles = 0, poses = 0, echecA = null;
let ouvert = null;
// Le faux moteur : chaque commande réussie ajoute « Layer Style: <kind> » à l'historique, relu par le cycle suivant.
// Comme mod-cycle : UNE file FIFO (la vraie, fileFifo) par laquelle passent /executer et /historique (Ctrl+Z) ;
// PL.executer = une tâche de la file par commande. Un échec du pont rejette PL.post (mod-api l'a déjà signalé).
let historique = ["Open"];
const PL = {
  etat: { doc: null, generation: 7 }, surDoc: [], surRendu: [],
  $: () => null, $$: () => [],
  api: (m, url, corps) => { apercus.push({ m, url, corps }); return Promise.resolve({ url: "/apercu.png", ms: 1, resultats: [] }); },
  file: fileFifo(),
  post: (url, corps) => {
    if (url === "/historique") { appels.push({ command: "historique", params: corps }); return Promise.resolve({}); }
    const { command, params } = corps;
    appels.push({ command, params });
    if (command === echecA) return Promise.reject(new Error("422"));
    historique = [...historique, "Layer Style: " + command.slice(command.lastIndexOf(".") + 1)];
    return Promise.resolve({});
  },
  executer: (command, params, { cycle = true } = {}) => PL.file(async () => {
    try { await PL.post("/executer", { command, params }); } catch (e) { return { ok: false }; }
    if (cycle) PL.cycle();
    return { ok: true, r: {} };
  }),
  cycle: () => { cycles++; if (PL.etat.doc) PL.etat.doc = { ...PL.etat.doc, history: historique.slice() }; return Promise.resolve(PL.etat.doc); },
  vue: { maxSideVoulu: () => 900, poserApercu: () => { poses++; } },
  prendreReglage: (e) => { if (ouvert && ouvert !== e) ouvert.fermer("annuler"); ouvert = e; },
  libererReglage: (e) => { if (ouvert === e) ouvert = null; },
  menus: { arbre: construireMenus(catalogue, [], [], "fr") },
};
initStyles(PL);

const calque = (id, effets, extra) => ({ id, name: "Calque " + id, kind: "Pixel", blend: "Normal", opacity: 1, fill: 1, ...(effets ? { effects: effets } : {}), ...extra });
const poserDoc = (actif, layers, index = 0) => { PL.etat.doc = { index, name: "essai", width: 800, height: 600, activeLayer: actif, layers, history: historique.slice() }; };
const boite = () => doc.body.tous((x) => x.className && String(x.className).includes("pl-styles"))[0];
const dans = (f) => { const b = boite(); return b ? b.tous(f) : []; };
const boutonOk = () => dans((x) => x.tagName === "BUTTON" && String(x.className).includes("principal"))[0];
const boutonAnnuler = () => dans((x) => x.tagName === "BUTTON" && x.className === "pl-bouton")[0];
const ligneStyle = (kind) => dans((x) => x.dataset && x.dataset.kind === kind)[0];
const caseStyle = (kind) => ligneStyle(kind).tous((x) => x.tagName === "INPUT" && x.type === "checkbox")[0];
const nomStyle = (kind) => ligneStyle(kind).tous((x) => x.tagName === "BUTTON")[0];
const champ = (cle, type) => { const l = dans((x) => x.dataset && x.dataset.cle === cle)[0]; return l ? l.tous((x) => x.tagName === (type === "select" ? "SELECT" : "INPUT") && (type === "select" || x.type === type))[0] : null; };
const titre = () => dans((x) => x.tagName === "H3")[0].textContent;
const note = () => dans((x) => x.tagName === "P" && x.className === "st-note")[0];
const memoire = (index, id) => ((PL.etat.styles["essai|" + index + "|7"] || {})[id]);
const saisir = (cle, v) => { const n = champ(cle, "number"); n.value = String(v); n.envoyer("change"); };
const surDoc = (d) => { PL.etat.doc = d; PL.surDoc.forEach((f) => f(d)); };

// 1. ouverture depuis le menu « Ombre portée… » : page choisie, case cochée, défauts du dialogue amont, titre
poserDoc(3, [calque(3)]);
PL.ouvrirStyles("dropShadow");
check("1.1 dialogue ouvert, une seule boîte", doc.body.tous((x) => String(x.className).includes("pl-styles")).length === 1);
check("1.2 11 lignes : options de fusion + 10 effets", dans((x) => x.dataset && x.dataset.kind).length === 11);
check("1.3 page Ombre portée (libellé du catalogue) et case cochée", titre() === "Ombre portée" && caseStyle("dropShadow").checked === true && caseStyle("stroke").checked === false, titre());
check("1.4 distance = 5 px, fusion = multiply", champ("distance", "number").value === "5" && champ("blend", "select").value === "multiply");
check("1.5 pas de mention « non relisible » (effet neuf)", note().hidden === true);
const nomTitre = dans((x) => x.className === "st-calque")[0];
check("1.6 titre « Style de calque — Calque 3 », nom en data-dz-brut", nomTitre && nomTitre.textContent === "Calque 3" && nomTitre.getAttribute("data-dz-brut") === "1"
  && boite().tous((x) => x.className === "pl-reglage-titre")[0].textContent === "photolab.calques.style — Calque 3");

// 2. aperçu : après le délai, /apercu {etapes} avec l'ombre portée complète sur le calque 3
await pause(320);
check("2.1 une demande d'aperçu", apercus.length === 1 && apercus[0].url === "/apercu", apercus.length);
check("2.2 étapes = l'ombre portée complète, calque 3", apercus[0] && json(apercus[0].corps.etapes) === json([{ command: "layer.layerStyle.dropShadow", params: { layer: 3, ...defautsStyle("dropShadow") } }])
  && apercus[0].corps.maxSide === 900, apercus[0] && apercus[0].corps);
await pause(10);
check("2.3 l'image d'aperçu est posée", poses === 1, poses);

// 3. édition : taille 12, contour coché par son nom ; le calque actif change pendant le réglage (calque visé FIGÉ) ;
//    OK -> étapes une à une sans cycle, puis UN cycle ; mémoire avec repère d'historique
saisir("size", 12);
nomStyle("stroke").envoyer("click");
check("3.1 clic sur le nom : page Contour (pas « Contourner » du catalogue) et case cochée", titre() === "Contourner" || titre() === nomStyle("stroke").textContent, titre());
check("3.2 … case du contour cochée", caseStyle("stroke").checked === true);
PL.etat.doc = { ...PL.etat.doc, activeLayer: 8, layers: [calque(3), calque(8)] };      // clic dans le panneau Calques
cycles = 0;
boutonOk().envoyer("click");
await pause(10);
check("3.3 boîte retirée", !boite());
check("3.4 deux commandes /executer, dans l'ordre du dialogue (contour puis ombre portée)", json(appels.map((a) => a.command)) ===
  json(["layer.layerStyle.stroke", "layer.layerStyle.dropShadow"]), appels);
check("3.5 calque visé figé à l'ouverture (3, pas le nouvel actif 8)", appels.every((a) => a.params.layer === 3), appels.map((a) => a.params.layer));
check("3.6 ombre portée : tous ses paramètres, taille 12", appels[1] && json(appels[1].params) === json({ layer: 3, ...defautsStyle("dropShadow"), size: 12 }), appels[1]);
check("3.7 UN seul cycle à la fin", cycles === 1, cycles);
const m3 = memoire(0, 3);
check("3.8 mémoire du calque 3 (clé essai|0|7) : effets + repère d'historique relu après le cycle",
  m3 && m3.effets.dropShadow.params.size === 12 && m3.effets.stroke.actif === true
  && json(m3.marque) === json({ n: 3, libelle: "Layer Style: dropShadow" }), m3);

// 4. réouverture (le moteur rend les deux effets, historique inchangé) : paramètres de la mémoire ; décocher -> enabled:false
appels.length = 0; apercus.length = 0;
poserDoc(3, [calque(3, { enabled: true, items: [{ enabled: true, kind: "Stroke" }, { enabled: true, kind: "Drop Shadow" }] })]);
PL.ouvrirStyles();
check("4.1 bouton fx : premier effet présent (Contour) choisi, mémoire connue", caseStyle("stroke").checked && caseStyle("dropShadow").checked && note().hidden === true);
nomStyle("dropShadow").envoyer("click");
check("4.2 taille relue de la mémoire (12)", champ("size", "number").value === "12");
const c = caseStyle("dropShadow"); c.checked = false; c.envoyer("change");
boutonOk().envoyer("click");
await pause(10);
check("4.3 une seule commande : enabled:false + tous les paramètres", appels.length === 1 && json(appels[0].params) === json({ layer: 3, enabled: false, ...defautsStyle("dropShadow"), size: 12 }), appels);
check("4.4 rien n'a été envoyé à /apercu avant le délai", apercus.length === 0);
check("4.5 repère avancé (4 entrées)", memoire(0, 3).marque.n === 4);

// 5. Ctrl+Z : l'historique raccourcit -> la mémoire ne vaut plus, effets « non relisibles » aux défauts
historique = historique.slice(0, 3);
poserDoc(3, [calque(3, { enabled: true, items: [{ enabled: true, kind: "Stroke" }, { enabled: true, kind: "Drop Shadow" }] })]);
PL.ouvrirStyles("dropShadow");
check("5.1 après Ctrl+Z : mention « non relisible », taille par défaut (5, pas 12)", note().hidden === false && champ("size", "number").value === "5");
boutonAnnuler().envoyer("click");
historique = [...historique, "Brush"];          // Ctrl+Z puis un autre geste : même longueur qu'avant, autre entrée
poserDoc(3, [calque(3, { enabled: true, items: [{ enabled: true, kind: "Drop Shadow" }] })]);
PL.ouvrirStyles("dropShadow");
check("5.2 Ctrl+Z puis autre geste : toujours « non relisible »", note().hidden === false && champ("size", "number").value === "5");
boutonAnnuler().envoyer("click");

// 6. effet présent au moteur mais inconnu de la mémoire (autre calque, autre document de même nom)
appels.length = 0;
poserDoc(5, [calque(5, { enabled: true, items: [{ enabled: true, kind: "Outer Glow" }] })]);
PL.ouvrirStyles("outerGlow");
check("6.1 mention « non relisible » visible", note().hidden === false && note().textContent === "photolab.styles.non_relisible");
cycles = 0;
boutonOk().envoyer("click");
await pause(10);
check("6.2 OK sans retouche ni aperçu : aucune commande, aucun cycle", appels.length === 0 && cycles === 0, [appels, cycles]);
historique = ["Open"];
poserDoc(3, [calque(3, { enabled: true, items: [{ enabled: true, kind: "Drop Shadow" }] })], 1);    // « essai », index 1
PL.ouvrirStyles("dropShadow");
check("6.3 document de même nom à un autre index : rien de partagé (inconnu)", note().hidden === false);
boutonAnnuler().envoyer("click");

// 7. échec en 2e étape : la 1re (réussie, au moteur) entre en mémoire, la suite n'est pas envoyée
appels.length = 0;
poserDoc(6, [calque(6)]);
PL.ouvrirStyles(OPTIONS_FUSION);
const libOptions = String(catalogue.entrees.find((x) => x.id === "layer.layerStyle.blendingOptions").libelle_fr).replace(/…$/, "");
check("7.1 page Options de fusion (catalogue sans dictionnaire), sans case", titre() === libOptions && !ligneStyle(OPTIONS_FUSION).tous((x) => x.type === "checkbox").length);
saisir("opacity", 40);
nomStyle("bevelEmboss").envoyer("click");
nomStyle("satin").envoyer("click");
echecA = "layer.layerStyle.satin";
boutonOk().envoyer("click");
await pause(10);
check("7.2 trois étapes prévues, la 3e échoue : options, biseau, satin envoyés ; rien après", json(appels.map((a) => a.command)) ===
  json(["layer.layerStyle.blendingOptions", "layer.layerStyle.bevelEmboss", "layer.layerStyle.satin"]), appels.map((a) => a.command));
check("7.3 options de fusion : {layer, blend, opacity 40, fillOpacity}", json(appels[0].params) === json({ layer: 6, blend: "normal", opacity: 40, fillOpacity: 100 }));
const m6 = memoire(0, 6);
check("7.4 mémoire : le biseau (réussi) oui, le satin (échoué) non", m6 && m6.effets.bevelEmboss && !m6.effets.satin, m6);
appels.length = 0;
echecA = "layer.layerStyle.blendingOptions";
poserDoc(9, [calque(9)]);
PL.ouvrirStyles("stroke");
saisir("size", 9);
nomStyle(OPTIONS_FUSION).envoyer("click");
saisir("opacity", 30);
boutonOk().envoyer("click");
await pause(10);
check("7.5 première étape en échec : rien d'autre envoyé, aucune mémoire", appels.length === 1 && !memoire(0, 9), [appels.length, memoire(0, 9)]);
echecA = null;

// 8. Réinitialiser (Alt + Annuler) : retour à l'état d'ouverture, le dialogue reste ouvert
appels.length = 0;
poserDoc(3, [calque(3)]);
PL.ouvrirStyles("dropShadow");
saisir("distance", 40);
boutonAnnuler().envoyer("click", { altKey: true });
check("8.1 Réinitialiser : distance revenue à 5, dialogue ouvert, case toujours cochée", !!boite() && champ("distance", "number").value === "5" && caseStyle("dropShadow").checked);
boutonOk().envoyer("click");
await pause(10);
check("8.2 OK après Réinitialiser : l'ombre portée aux défauts", appels.length === 1 && appels[0].params.distance === 5, appels);

// 9. rendu réel arrivé après l'aperçu : il n'y a plus d'aperçu à effacer (Annuler ne relance pas de cycle)
poserDoc(3, [calque(3)]);
PL.ouvrirStyles("colorOverlay");
await pause(320); await pause(10);
ouvert.surRenduReel();               // un cycle (zoom, autre commande) vient de poser le rendu réel
cycles = 0; appels.length = 0;
boutonAnnuler().envoyer("click");
check("9.1 Annuler après un rendu réel : aucun cycle de plus", cycles === 0 && appels.length === 0 && !boite(), cycles);
PL.ouvrirStyles("colorOverlay");
await pause(320); await pause(10);
cycles = 0;
boutonAnnuler().envoyer("click");
check("9.2 Annuler avec un aperçu à l'écran : un cycle (rendu réel)", cycles === 1, cycles);
PL.ouvrirStyles("satin");
PL.ouvrirStyles("stroke");
check("9.3 une seule boîte à la fois", doc.body.tous((x) => String(x.className).includes("pl-styles")).length === 1);
boutonAnnuler().envoyer("click");

// 10. le calque change pendant que le dialogue est ouvert : options de fusion relues ; calque disparu : fermeture
poserDoc(3, [calque(3)]);
PL.ouvrirStyles(OPTIONS_FUSION);
surDoc({ ...PL.etat.doc, layers: [calque(3, null, { opacity: 0.5, blend: "Screen" })] });
check("10.1 opacité changée au panneau Calques : relue dans le dialogue (50, screen)", champ("opacity", "number").value === "50" && champ("blend", "select").value === "screen");
appels.length = 0;
boutonOk().envoyer("click");
await pause(10);
check("10.2 … et ce n'est pas un changement du dialogue (rien envoyé)", appels.length === 0, appels);
PL.ouvrirStyles(OPTIONS_FUSION);
saisir("opacity", 20);
surDoc({ ...PL.etat.doc, layers: [calque(3, null, { opacity: 0.7 })] });
check("10.3 saisie de l'utilisateur gardée si le calque change ailleurs", champ("opacity", "number").value === "20");
surDoc({ ...PL.etat.doc, layers: [calque(4)] });
check("10.4 calque visé disparu : dialogue fermé", !boite());

// 11. groupe en Transfert : passThrough toujours listé, même après avoir choisi un autre mode et changé de page
poserDoc(12, [calque(12, null, { blend: "Pass Through", children: [] })]);
PL.ouvrirStyles(OPTIONS_FUSION);
const valeurs = () => champ("blend", "select").children.map((o) => o.value);
check("11.1 groupe : passThrough en tête, choisi", valeurs()[0] === "passThrough" && valeurs().length === 28 && champ("blend", "select").value === "passThrough");
const sel = champ("blend", "select"); sel.value = "multiply"; sel.envoyer("change");
nomStyle("stroke").envoyer("click"); nomStyle(OPTIONS_FUSION).envoyer("click");
check("11.2 après Multiply et un aller-retour de page : passThrough toujours proposé", valeurs()[0] === "passThrough" && champ("blend", "select").value === "multiply");
boutonAnnuler().envoyer("click");
poserDoc(3, [calque(3)]);
PL.ouvrirStyles(OPTIONS_FUSION);
check("11.3 calque simple : 27 modes, pas de Transfert", !valeurs().includes("passThrough") && valeurs().length === 27);
boutonAnnuler().envoyer("click");
PL.etat.doc = null;
check("11.4 sans document : rien ne s'ouvre", PL.ouvrirStyles("dropShadow") === null && !boite());

// 13. OK puis Ctrl+Z tout de suite : les étapes forment UNE tâche de la file FIFO ; le Ctrl+Z (PL.historique passe par
//     PL.file -> /historique) arrive après la DERNIÈRE étape, jamais entre deux (il annulerait un effet à moitié posé).
appels.length = 0; cycles = 0;
historique = ["Open"];
poserDoc(3, [calque(3)]);
PL.ouvrirStyles("dropShadow");
nomStyle("stroke").envoyer("click");
nomStyle("innerGlow").envoyer("click");
boutonOk().envoyer("click");
PL.file(() => PL.post("/historique", { annuler: 1 }));           // Ctrl+Z tapé dans la foulée
await pause(10);
check("13.1 ordre dans la file : les trois étapes, PUIS l'annulation", json(appels.map((a) => a.command)) ===
  json(["layer.layerStyle.stroke", "layer.layerStyle.innerGlow", "layer.layerStyle.dropShadow", "historique"]), appels.map((a) => a.command));
check("13.2 un seul cycle après les étapes", cycles === 1, cycles);
const srcStyles = readFileSync(join(racine, "js/mod-styles.js"), "utf8");
check("13.3 mod-styles : une tâche PL.file qui poste /executer, plus de PL.executer étape par étape",
  /PL\.file\(async/.test(srcStyles) && /PL\.post\("\/executer"/.test(srcStyles) && !/PL\.executer\(/.test(srcStyles));

// 12. panneau Calques : bouton fx et badge « fx » (double-clic -> layer.select puis cycle, PUIS le dialogue)
const corpsCalques = doc.createElement("div"); doc.body.appendChild(corpsCalques);
const journal = [];
const PC = {
  etat: { doc: null, vignettes: {} }, surDoc: [], surVignettes: [],
  $: (s) => (s === "#corpsCalques" ? corpsCalques : null), $$: () => [],
  icone: () => "",                         // G4 : PL.icone est synchrone (dzIcone)
  executer: (command, params, opts) => { journal.push(["executer", command, params, opts]); return Promise.resolve({ ok: true }); },
  cycle: () => { journal.push(["cycle"]); PC.etat.doc = { ...PC.etat.doc, activeLayer: 2 }; return Promise.resolve(PC.etat.doc); },
  ouvrirStyles: (k) => { journal.push(["ouvrirStyles", k, PC.etat.doc.activeLayer]); },
};
initCalques(PC);
const docC = { index: 0, name: "c", activeLayer: 1, layers: [calque(2, { enabled: true, items: [{ enabled: true, kind: "Stroke" }] }), calque(1)] };
PC.etat.doc = docC;
PC.surDoc.forEach((f) => f(docC));
const badges = corpsCalques.tous((x) => x.className === "cq-fx");
check("12.1 un badge fx, sur la seule ligne à effets", badges.length === 1 && badges[0].parentNode.dataset.id === "2");
badges[0].envoyer("dblclick");
await pause(5);
check("12.2 double-clic sur le badge d'un calque non actif : layer.select {cycle:false}, cycle, puis dialogue sur ce calque",
  json(journal) === json([["executer", "layer.select", { layer: 2, mode: "replace" }, { cycle: false }], ["cycle"], ["ouvrirStyles", null, 2]]), journal);
journal.length = 0;
PC.etat.doc = { ...docC, activeLayer: 2 };
PC.surDoc.forEach((f) => f(PC.etat.doc));
corpsCalques.tous((x) => x.className === "cq-fx")[0].envoyer("dblclick");
await pause(5);
check("12.3 calque déjà actif : dialogue tout de suite, sans layer.select", json(journal) === json([["ouvrirStyles", null, 2]]), journal);
journal.length = 0;
// G4 : le bouton « fx » porte l'icône dz-edit-effet (plus de texte « fx »)
const bFx = corpsCalques.tous((x) => x.tagName === "BUTTON" && x.dataset.icone === "dz-edit-effet")[0];
check("12.4 bouton fx du pied actif avec un document", bFx && bFx.disabled === false && !bFx.classList.contains("bientot"));
bFx.envoyer("click");
check("12.5 bouton fx -> PL.ouvrirStyles()", journal.length === 1 && journal[0][0] === "ouvrirStyles");

console.log(`styles-ecran : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
