// qa/plateau.test.mjs — plateau (lot 1) : Image › Découper en hexagones… (menu, grisé sans document, action, image fournie).
import { readFileSync } from "node:fs";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC, actionEntree } from "../js/mod-menus.js";
import { decouperHex, initPlateau } from "../js/mod-plateau.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const catalogue = JSON.parse(readFileSync(new URL("../donnees/menus.json", import.meta.url), "utf8"));
const tFr = (c) => (dico[c] ? dico[c].fr : c);
const tEn = (c) => (dico[c] ? dico[c].en : c);
const trouver = (l, id) => { for (const e of l) { if (e.id === id) return e; if (e.entrees) { const f = trouver(e.entrees, id); if (f) return f; } } return null; };

// 1. le menu
const fr = construireMenus(catalogue, [], REFUSES, "fr", tFr), en = construireMenus(catalogue, [], REFUSES, "en", tEn);
const eFr = trouver(fr, "pl.plateau.decouper"), eEn = trouver(en, "pl.plateau.decouper");
const image = fr.find((m) => m.nom === "Image");
check("1.1 dans le menu Image, une seule fois", eFr && image.entrees.includes(eFr) && image.entrees.filter((e) => e.id === "pl.plateau.decouper").length === 1);
check("1.2 libellés FR et EN", eFr.libelle === "Découper en hexagones…" && eEn.libelle === "Cut into hexagons…", [eFr.libelle, eEn.libelle]);
check("1.3 traitée par l'écran, document requis", TRAITES_PAR_ECRAN.has("pl.plateau.decouper") && NECESSITE_DOC.has("pl.plateau.decouper")
  && actionEntree(eFr) === "ecran" && eFr.etat === "actif");

// 2. l'action
const doc = { width: 4000, height: 2500, name: "e99baeb8-carte.png", layers: [] };
function fabrique({ avecDoc = true, enregistre = { filename: "photolab_x_carte.png" } } = {}) {
  const j = { posts: [], enregistrer: 0, signaux: [], ouvert: null };
  const PL = { etat: { doc: avecDoc ? doc : null }, actions: {},
    post: async (route, corps) => { j.posts.push([route, corps]); return { url: "/rendus/a.png" }; },
    signaler: (m, e) => j.signaux.push([m, !!e]),
    enregistrerBibliotheque: async () => { j.enregistrer++; return enregistre; } };
  const outils = { charger: async (u) => ({ width: 1024, height: 640, url: u }), ouvrir: async (o) => { j.ouvert = o; return { deck: { id: "d" }, tuiles: 12 }; } };
  return { PL, j, outils };
}
{
  const { PL, j, outils } = fabrique();
  const r = await decouperHex(PL, tFr, outils);
  check("2.1 le dialogue reçoit les dimensions et le nom du document", j.ouvert && j.ouvert.largeur === 4000 && j.ouvert.hauteur === 2500 && j.ouvert.nomImage === "carte", j.ouvert);
  check("2.2 aperçu = un rendu du moteur borné à 1024", j.posts[0][0] === "/rendu" && j.posts[0][1].maxSide === 1024 && j.ouvert.apercu.url === "/rendus/a.png", j.posts);
  check("2.3 rien n'est enregistré avant la création", j.enregistrer === 0);
  check("2.4 le résultat du dialogue est rendu", r && r.tuiles === 12);
  const nom = await j.ouvert.fournirImage({ largeurMm: 100, hauteurMm: 60 });
  check("2.5 fournirImage enregistre (nouveau fichier) et rend son nom", j.enregistrer === 1 && nom === "photolab_x_carte.png", nom);
}
{
  const { PL, j, outils } = fabrique({ enregistre: null });
  await decouperHex(PL, tFr, outils);
  let erreur = null; try { await j.ouvert.fournirImage({}); } catch (e) { erreur = e; }
  check("2.6 enregistrement refusé : une Error au message traduit", erreur instanceof Error && erreur.message === tFr("photolab.plateau.erreur_enregistrement") && erreur.message.length > 10, erreur && erreur.message);
}
{
  const { PL, j, outils } = fabrique({ avecDoc: false });
  const r = await decouperHex(PL, tFr, outils);
  check("2.7 sans document : rien", r === null && j.ouvert === null && j.posts.length === 0);
}
{
  const { PL, j, outils } = fabrique();
  PL.post = async () => { throw new Error("occupé"); };
  const r = await decouperHex(PL, tFr, outils);
  check("2.8 rendu impossible : signalé, dialogue non ouvert", r === null && j.ouvert === null && j.signaux.length === 1 && j.signaux[0][1] === true, j.signaux);
}
{
  const petit = { ...doc, width: 300, height: 200 };
  const { PL, j, outils } = fabrique(); PL.etat.doc = petit;
  await decouperHex(PL, tFr, outils);
  check("2.9 petit document : aperçu à sa taille", j.posts[0][1].maxSide === 300, j.posts);
}
{
  const { PL } = fabrique();
  globalThis.window = { dzT: (c) => c };
  initPlateau(PL);
  check("2.10 initPlateau pose l'action", typeof PL.actions["pl.plateau.decouper"] === "function");
  delete globalThis.window;
}

console.log(`${ok}/${ok + ko} vérifications`);
if (ko) { console.log("ECHEC"); process.exit(1); }
console.log("OK");
