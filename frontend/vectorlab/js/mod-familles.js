// mod-familles.js — les familles d'outils d'Affinity (R-D6) : un bouton
// par famille montrant le membre courant, flyout vertical des membres.
// Feuille pure. `personas` : les personas où la famille est visible.
const m = (outil, nom, touche = "") => ({ outil, nom, touche });
export const FAMILLES = [
  { id: "deplacer", nom: "Déplacer", personas: ["vecteur", "pixel"], membres: [m("select", "Déplacer", "V")] },
  { id: "noeuds", nom: "Nœuds", personas: ["vecteur"], membres: [m("noeuds", "Nœud", "N"), m("coin", "Coin", "C")] },
  { id: "plume", nom: "Plume", personas: ["vecteur"], membres: [m("plume", "Plume", "P"), m("crayon", "Crayon", "B"), m("pinceauv", "Pinceau vectoriel", "J")] },
  { id: "formes", nom: "Formes", personas: ["vecteur"], membres: [m("rect", "Rectangle", "R"), m("ellipse", "Ellipse", "E"), m("ligne", "Ligne", "L"), m("forme", "Forme paramétrique", "F")] },
  { id: "constructeur", nom: "Constructeur", personas: ["vecteur"], membres: [m("constructeur", "Constructeur de formes", "S"), m("couteau", "Couteau", "X"), m("gomme", "Gomme vectorielle", "W")] },
  { id: "texte", nom: "Texte", personas: ["vecteur"], membres: [m("texte", "Texte", "T"), m("cadre", "Cadre de texte")] },
  { id: "image", nom: "Image", personas: ["vecteur", "pixel"], membres: [m("image", "Image (menu)"), m("recadrer", "Recadrer")] },
  { id: "degrade", nom: "Dégradé", personas: ["vecteur"], membres: [m("degrade", "Dégradé"), m("transparence", "Transparence", "Y")] },
  { id: "apparence", nom: "Apparence", personas: ["vecteur"], membres: [m("apparence", "Apparence (menu)")] },
  { id: "symbole", nom: "Symboles", personas: ["vecteur"], membres: [m("symbole", "Symboles (menu)")] },
  { id: "mesure", nom: "Mesure", personas: ["vecteur"], membres: [m("mesure", "Mesure", "M"), m("pipette", "Pipette", "I")] },
  { id: "tuiles", nom: "Tuiles", personas: ["vecteur"], membres: [m("tuiles", "Pinceau de tuiles", "K")] },
  { id: "planche", nom: "Plan de travail", personas: ["vecteur"], membres: [m("planche", "Plan de travail")] },
  { id: "ia", nom: "IA", personas: ["vecteur"], membres: [m("ia", "Illustration IA")] },
  { id: "pxselection", nom: "Sélection de pixels", personas: ["pixel"], membres: [m("px-selrect", "Sélection rectangle", "M"), m("px-lasso", "Lasso", "L"), m("px-baguette", "Baguette magique", "W")] },
  { id: "pxpinceau", nom: "Pinceau", personas: ["pixel"], membres: [m("px-pinceau", "Pinceau", "B"), m("px-gomme", "Gomme", "E"), m("px-cloner", "Tampon de clonage", "C")] },
  { id: "pxretouche", nom: "Retouche", personas: ["pixel"], membres: [m("px-flou", "Flou"), m("px-eclaircir", "Éclaircir (densité −)"), m("px-assombrir", "Assombrir (densité +)")] },
  { id: "pxseau", nom: "Seau", personas: ["pixel"], membres: [m("px-seau", "Pot de peinture", "G")] },
  { id: "pxart", nom: "Pixel-art", personas: ["pixel"], membres: [m("px-crayon", "Crayon pixel", "K"), m("px-ligne", "Ligne pixel", "I"), m("px-rectpx", "Rectangle pixel", "R")] },
  { id: "vue", nom: "Vue", personas: ["vecteur", "pixel"], membres: [m("main", "Main", "H"), m("loupe", "Loupe", "Z")] },
  { id: "tranche", nom: "Tranche", personas: ["vecteur", "pixel"], membres: [m("tranche", "Tranche d'export")] },
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
  return famille.membres.map((x) => ({ id: x.outil, libelle: `Outil ${x.nom}`, detail: x.touche, actif: x.outil === courant }));
}
export function touche_de(outil) {
  for (const f of FAMILLES) { const x = f.membres.find((y) => y.outil === outil); if (x) return x.touche; }
  return "";
}
