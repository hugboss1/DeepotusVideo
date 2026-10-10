import { T } from "./mod-i18n.js";
// mod-familles.js — les familles d'outils d'Affinity (R-D6) : un bouton
// par famille montrant le membre courant, flyout vertical des membres.
// Feuille pure. `personas` : les personas où la famille est visible.
const m = (outil, nom, touche = "") => ({ outil, nom, touche });
export const FAMILLES = [
  { id: "deplacer", nom: T("vectorlab.familles.deplacer"), personas: ["vecteur", "pixel"], membres: [m("select", T("vectorlab.familles.deplacer"), "V")] },
  { id: "noeuds", nom: T("vectorlab.familles.noeuds"), personas: ["vecteur"], membres: [m("noeuds", T("vectorlab.familles.noeud"), "N"), m("coin", T("vectorlab.familles.coin"), "C")] },
  { id: "plume", nom: T("vectorlab.familles.plume"), personas: ["vecteur"], membres: [m("plume", T("vectorlab.familles.plume"), "P"), m("crayon", T("vectorlab.familles.crayon"), "B"), m("pinceauv", T("vectorlab.familles.pinceauv"), "J")] },
  { id: "formes", nom: T("vectorlab.familles.formes"), personas: ["vecteur"], membres: [m("rect", "Rectangle", "R"), m("ellipse", "Ellipse", "E"), m("ligne", T("vectorlab.familles.ligne"), "L"), m("forme", T("vectorlab.familles.forme"), "F")] },
  { id: "constructeur", nom: T("vectorlab.familles.constructeur_famille"), personas: ["vecteur"], membres: [m("constructeur", T("vectorlab.familles.constructeur"), "S"), m("couteau", T("vectorlab.familles.couteau"), "X"), m("gomme", T("vectorlab.familles.gomme"), "W")] },
  { id: "texte", nom: T("vectorlab.familles.texte"), personas: ["vecteur"], membres: [m("texte", T("vectorlab.familles.texte"), "T"), m("cadre", T("vectorlab.familles.cadre"))] },
  { id: "image", nom: "Image", personas: ["vecteur", "pixel"], membres: [m("image", "Image (menu)"), m("recadrer", T("vectorlab.familles.recadrer"))] },
  { id: "degrade", nom: T("vectorlab.familles.degrade"), personas: ["vecteur"], membres: [m("degrade", T("vectorlab.familles.degrade")), m("transparence", T("vectorlab.familles.transparence"), "Y")] },
  { id: "apparence", nom: T("vectorlab.familles.apparence"), personas: ["vecteur"], membres: [m("apparence", T("vectorlab.familles.apparence_menu"))] },
  { id: "symbole", nom: T("vectorlab.familles.symboles"), personas: ["vecteur"], membres: [m("symbole", T("vectorlab.familles.symboles_menu"))] },
  { id: "mesure", nom: T("vectorlab.familles.mesure"), personas: ["vecteur"], membres: [m("mesure", T("vectorlab.familles.mesure"), "M"), m("pipette", T("vectorlab.familles.pipette"), "I")] },
  { id: "tuiles", nom: T("vectorlab.familles.tuiles"), personas: ["vecteur"], membres: [m("tuiles", T("vectorlab.familles.tuiles_pinceau"), "K")] },
  { id: "planche", nom: T("vectorlab.familles.planche"), personas: ["vecteur"], membres: [m("planche", T("vectorlab.familles.planche"))] },
  { id: "ia", nom: T("vectorlab.familles.ia"), personas: ["vecteur"], membres: [m("ia", T("vectorlab.familles.ia_illustration"))] },
  { id: "pxselection", nom: T("vectorlab.familles.pxselection"), personas: ["pixel"], membres: [m("px-selrect", T("vectorlab.familles.px_selrect"), "M"), m("px-lasso", "Lasso", "L"), m("px-baguette", T("vectorlab.familles.px_baguette"), "W")] },
  { id: "pxpinceau", nom: T("vectorlab.familles.px_pinceau"), personas: ["pixel"], membres: [m("px-pinceau", T("vectorlab.familles.px_pinceau"), "B"), m("px-gomme", T("vectorlab.familles.px_gomme"), "E"), m("px-cloner", T("vectorlab.familles.px_cloner"), "C")] },
  { id: "pxretouche", nom: T("vectorlab.familles.pxretouche"), personas: ["pixel"], membres: [m("px-flou", T("vectorlab.familles.px_flou")), m("px-eclaircir", T("vectorlab.familles.px_eclaircir")), m("px-assombrir", T("vectorlab.familles.px_assombrir"))] },
  { id: "pxseau", nom: T("vectorlab.familles.pxseau"), personas: ["pixel"], membres: [m("px-seau", T("vectorlab.familles.px_seau"), "G")] },
  { id: "pxart", nom: "Pixel-art", personas: ["pixel"], membres: [m("px-crayon", T("vectorlab.familles.px_crayon"), "K"), m("px-ligne", T("vectorlab.familles.px_ligne"), "I"), m("px-rectpx", T("vectorlab.familles.px_rectpx"), "R")] },
  { id: "vue", nom: T("vectorlab.familles.vue"), personas: ["vecteur", "pixel"], membres: [m("main", T("vectorlab.familles.main"), "H"), m("loupe", T("vectorlab.familles.loupe"), "Z")] },
  { id: "tranche", nom: T("vectorlab.familles.tranche"), personas: ["vecteur", "pixel"], membres: [m("tranche", T("vectorlab.familles.tranche_export"))] },
];
export const familles_de = (persona) => FAMILLES.filter((f) => f.personas.includes(persona));
export const famille_par_id = (id) => FAMILLES.find((f) => f.id === id) || null;
export const famille_de = (outil) => FAMILLES.find((f) => f.membres.some((x) => x.outil === outil)) || null;
export function membre_courant(etat, familleId) {
  const f = FAMILLES.find((x) => x.id === familleId);
  if (!f) return null;
  const v = etat && etat[familleId];
  return f.membres.some((x) => x.outil === v) ? v : f.membres[0].outil;
}
export function choisir_membre(etat, outil) {
  const f = famille_de(outil);
  if (!f) return etat;
  return { ...(etat || {}), [f.id]: outil };
}
export function flyout_famille(famille, courant) {
  if (!famille) return [];
  return famille.membres.map((x) => ({ id: x.outil, libelle: T("vectorlab.familles.outil", { nom: x.nom }), detail: x.touche, actif: x.outil === courant }));
}
export function touche_de(outil) {
  for (const f of FAMILLES) { const x = f.membres.find((y) => y.outil === outil); if (x) return x.touche; }
  return "";
}
