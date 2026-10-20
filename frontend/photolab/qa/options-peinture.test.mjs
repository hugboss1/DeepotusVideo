// qa/options-peinture.test.mjs — t155 : la VRAIE barre d'options (initOutils) sous le faux DOM. Choisir un outil de
// peinture montre ses réglages à lui ; changer une liste, une case, un nombre ou un choix l'écrit dans les réglages DE
// CET OUTIL (PL.optionsPeintureDe), jamais dans PL.etat.options des sélections. (Mutation M12 : une liste qui ne gardait
// pas sa valeur survivait aux bancs purs.)
import { installerFauxDom } from "./outils/faux-dom.mjs";
import { initOutils } from "../js/mod-outils.js";
import { defautsPeinture } from "../js/mod-peinture.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }

const doc = installerFauxDom();
const classes = (n) => String(n.className || "").split(/\s+/);
// La barre d'outils écrit ses boutons par innerHTML (« <span class="ico"></span> ») et les relit par querySelector :
// ce banc complète le faux DOM partagé pour ces deux usages seulement (balises plates, une classe, un type).
const creer = doc.createElement;
doc.createElement = (tag) => {
  const n = creer(tag);
  Object.defineProperty(n, "innerHTML", { set(v) {
    n.textContent = "";
    for (const m of String(v).matchAll(/<(\w+)((?:\s+[\w-]+="[^"]*")*)\s*>/g)) {
      const c = doc.createElement(m[1]);
      for (const a of m[2].matchAll(/([\w-]+)="([^"]*)"/g)) { if (a[1] === "class") c.className = a[2]; else if (a[1] === "type") c.type = a[2]; else c.setAttribute(a[1], a[2]); }
      n.appendChild(c);
    }
  } });
  n.querySelector = (sel) => (sel.startsWith(".") ? n.tous((x) => classes(x).includes(sel.slice(1)))[0] : n.tous((x) => x.tagName === sel.toUpperCase())[0]) || null;
  return n;
};
const outils = doc.createElement("div"); outils.id = "outils";
const options = doc.createElement("div"); options.id = "options";
const toile = doc.createElement("canvas"); toile.id = "toile";
doc.body.append(outils, options, toile);
const ids = { "#outils": outils, "#options": options, "#toile": toile };
const PL = {
  etat: { outil: "move", doc: null },
  $: (sel, racine) => (racine ? racine.tous((n) => sel.startsWith(".") && classes(n).includes(sel.slice(1)))[0] || null : ids[sel] || null),
  $$: (sel, racine) => (racine || doc).tous((n) => n.tagName === sel.toUpperCase()),
  icone: () => "",
  signaler() {},
};
const reglages = {};
PL.optionsPeintureDe = (id) => (reglages[id] = reglages[id] || defautsPeinture(id));
initOutils(PL);

const champ = (cle) => options.tous((n) => n.dataset && n.dataset.cle === cle)[0];
const controle = (cle, tag) => champ(cle).tous((n) => n.tagName === tag)[0];

check("1.1 choisir le Pinceau", PL.choisirOutil("brush") === true && PL.etat.outil === "brush");
// t252 : + la symétrie de peinture (état du document, option `doc`)
check("1.2 la barre montre les 7 réglages du Pinceau", options.tous((n) => n.dataset && n.dataset.cle).map((n) => n.dataset.cle).join() === "taille,durete,fusion,opacite,flux,lissageTrait,symetrie");
const sel = controle("fusion", "SELECT");
check("1.3 la liste du mode montre la valeur courante", sel && sel.value === "normal", sel && sel.value);
sel.value = "multiply"; sel.envoyer("change");
check("1.4 changer la liste écrit dans les réglages du Pinceau", reglages.brush.fusion === "multiply", reglages.brush.fusion);
check("1.5 … et pas dans les options des sélections", PL.etat.options.fusion === undefined && PL.etat.options.mode === "replace");
const t = controle("taille", "INPUT");
t.value = "9000"; t.envoyer("change");
check("1.6 un nombre est borné (taille 1..5000) et gardé", reglages.brush.taille === 5000 && t.value === 5000, reglages.brush.taille);

PL.choisirOutil("eraser");
const choix = champ("modeGomme").tous((n) => n.tagName === "BUTTON");
check("2.1 Gomme : deux boutons Pinceau / Crayon", choix.length === 2);
choix[1].envoyer("click");
check("2.2 un choix écrit dans les réglages de la Gomme", reglages.eraser.modeGomme === "crayon", reglages.eraser.modeGomme);
const histo = controle("historique", "INPUT");
histo.checked = true; histo.envoyer("change");
check("2.3 une case écrit dans les réglages de la Gomme", reglages.eraser.historique === true);
check("2.4 le Pinceau garde ses réglages (chaque outil les siens)", reglages.brush.fusion === "multiply" && reglages.brush.taille === 5000 && reglages.eraser.taille === 13);

PL.choisirOutil("brush");
check("3.1 revenir au Pinceau : la barre relit SES réglages", controle("fusion", "SELECT").value === "multiply" && controle("taille", "INPUT").value === 5000);
PL.choisirOutil("magicWand");
check("3.2 un outil de sélection garde la barre des sélections", !!champ("tolerance") && !champ("fusion"));

// t252 : la Symétrie est un état du DOCUMENT (moteur) : la liste lit et écrit par son lien (t253 : PL.liensOptions,
// généralisé à l'angle de la vue), jamais dans les réglages de l'outil.
const demandes = [];
PL.liensOptions = { symetrie: { lire: () => "dual", ecrire: (v) => { demandes.push(["symetrie", v]); } } };
PL.choisirOutil("brush");
const sym = controle("symetrie", "SELECT");
check("4.1 la liste Symétrie montre l'état du document", sym && sym.value === "dual", sym && sym.value);
sym.value = "vertical"; sym.envoyer("change");
check("4.2 la changer demande au document (PL.liensOptions.symetrie), pas aux réglages du Pinceau",
  JSON.stringify(demandes) === JSON.stringify([["symetrie", "vertical"]]) && reglages.brush.symetrie === undefined, JSON.stringify(demandes));
PL.choisirOutil("pencil");
check("4.3 le Crayon montre la même symétrie du document", controle("symetrie", "SELECT").value === "dual");
PL.choisirOutil("blur");
check("4.4 un outil qui ne la suit pas (Flou) n'a pas l'option", !champ("symetrie"));

// t253 : l'angle de la Rotation de la vue passe par le même lien (mod-vue), le champ nombre l'écrit, rien n'est rangé
const angles = [];
PL.liensOptions.rotationVue = { lire: () => 30, ecrire: (x) => { angles.push(x); } };
PL.choisirOutil("rotateView");
const ang = controle("rotationVue", "INPUT");
check("5.1 la Rotation de la vue montre l'angle de la vue", ang && Number(ang.value) === 30, ang && ang.value);
ang.value = "200"; ang.envoyer("change");
check("5.2 l'angle saisi est borné à 180 et écrit par le lien, pas dans les options", JSON.stringify(angles) === "[180]" && PL.etat.options.rotationVue === undefined, JSON.stringify(angles));

console.log(`options-peinture : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
