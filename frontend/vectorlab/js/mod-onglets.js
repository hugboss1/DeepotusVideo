// mod-onglets.js — la pile de droite d'Affinity (R3) : trois groupes
// d'onglets par persona ; un onglet ouvre une ou plusieurs sections
// <details id="…Details"> existantes ; l'onglet actif de chaque groupe
// est mémorisé par persona (dz_vl_onglets). Feuille pure.
const o = (libelle, ...sections) => ({ libelle, sections });
export const ONGLETS = {
  couleur: o("Couleur", "styleDetails"),
  echantillons: o("Échantillons", "echantillonsDetails"),
  trait: o("Trait", "traitDetails"),
  apparence: o("Apparence", "apparence2Details"),
  texte: o("Texte", "texteDetails"),
  calques: o("Calques", "calquesDetails"),
  trace: o("Tracé", "noeudsDetails", "formeDetails"),
  image: o("Image", "imageDetails"),
  planches: o("Planches", "planchesDetails"),
  grille: o("Grille", "grilleDetails"),
  plateau: o("Plateau", "plateauDetails"),
  carte: o("Carte", "carteDetails"),
  vitrail: o("Vitrail", "vitrailDetails"),
  stock: o("Stock", "assetsDetails"),
  transformer: o("Transformer", "transformerDetails"),
  navigateur: o("Navigateur", "navigateurDetails"),
  historique: o("Historique", "instantanesDetails"),
  reperes: o("Repères", "reperesDetails"),
  exporter: o("Exporter", "exportDetails", "exportPlusDetails"),
  pixel: o("Pixel", "pixelDetails"),
  histogramme: o("Histogramme", "histogrammeDetails"),
};
export const GROUPES = {
  vecteur: [["couleur", "echantillons", "trait", "apparence", "texte"],
            ["calques", "trace", "image", "planches", "grille", "plateau", "carte", "vitrail", "stock"],
            ["transformer", "navigateur", "historique", "reperes", "exporter"]],
  pixel: [["histogramme", "couleur"], ["calques", "pixel", "image", "stock"], ["navigateur", "transformer", "historique", "exporter"]],
};
const DEFAUTS = { vecteur: ["couleur", "calques", "transformer"], pixel: ["couleur", "calques", "navigateur"] };
export const onglets_de = (persona) => GROUPES[persona] || [];
export function onglet_de_section(detailsId) {
  for (const [id, x] of Object.entries(ONGLETS)) if (x.sections.includes(detailsId)) return id;
  return null;
}
function normaliser(persona, liste) {
  const g = GROUPES[persona];
  return g.map((groupe, i) => (Array.isArray(liste) && groupe.includes(liste[i])) ? liste[i] : DEFAUTS[persona][i]);
}
export function actif_lire(json) {
  let lu = null;
  try { lu = json ? JSON.parse(json) : null; } catch (e) { lu = null; }
  if (!lu || typeof lu !== "object") lu = {};
  const out = {};
  for (const persona of Object.keys(GROUPES)) out[persona] = normaliser(persona, lu[persona]);
  return out;
}
export const actif_de = (etat, persona) => (etat && etat[persona]) ? etat[persona].slice() : (GROUPES[persona] ? DEFAUTS[persona].slice() : []);
export function actif_poser(etat, persona, groupe, onglet) {
  const g = GROUPES[persona];
  if (!g || !g[groupe] || !g[groupe].includes(onglet)) return etat;
  const liste = actif_de(etat, persona);
  liste[groupe] = onglet;
  return { ...etat, [persona]: liste };
}
export const actif_serialiser = (etat) => JSON.stringify(etat);
export function sections_ouvertes(etat, persona) {
  if (!GROUPES[persona]) return [];
  return actif_de(etat, persona).flatMap((id) => ONGLETS[id].sections);
}
