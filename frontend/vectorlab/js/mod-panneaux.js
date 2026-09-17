// mod-panneaux.js — l'état ouvert / replié des sections du panneau de
// droite (une par lot, toutes en <details>), par id ; relu et écrit en
// JSON (localStorage côté UI, clé dz_vl_panneaux), défauts sûrs, appliqué
// à des objets {id, open} (les <details> du DOM). Module FEUILLE.

export const PANNEAUX_DEFAUT = Object.freeze({
  vitrailDetails: false, styleDetails: true, apparence2Details: true, formeDetails: true, noeudsDetails: false,
  instantanesDetails: false, pixelDetails: true, exportDetails: true, exportPlusDetails: true, imageDetails: true,
  reperesDetails: false, grilleDetails: false, plateauDetails: false, planchesDetails: false, carteDetails: false,
  assetsDetails: false, calquesDetails: true,
});
export function etat_lire(json) {
  const out = { ...PANNEAUX_DEFAUT };
  let lu = null;
  try { lu = json ? JSON.parse(json) : null; } catch (e) { lu = null; }
  if (lu && typeof lu === "object") {
    for (const [k, v] of Object.entries(lu)) if (k in PANNEAUX_DEFAUT && typeof v === "boolean") out[k] = v;
  }
  return out;
}
export function etat_poser(etat, id, ouvert) {
  if (!(id in PANNEAUX_DEFAUT)) throw new Error(`panneau inconnu : ${id}`);
  return { ...etat, [id]: !!ouvert };
}
export const etat_serialiser = (etat) => JSON.stringify(etat);
export function appliquer(etat, details) {
  for (const d of details || []) if (d && d.id in etat) d.open = etat[d.id];
  return details;
}
export function initPanneaux(VL) {
  const CLE = "dz_vl_panneaux";
  let etat = PANNEAUX_DEFAUT;
  try { etat = etat_lire(localStorage.getItem(CLE)); } catch (e) { /* stockage indisponible */ }
  const tous = [...document.querySelectorAll("#panneauCalques details[id]")];
  appliquer(etat, tous);
  for (const d of tous) {
    d.addEventListener("toggle", () => {
      if (!(d.id in PANNEAUX_DEFAUT)) return;
      etat = etat_poser(etat, d.id, d.open);
      try { localStorage.setItem(CLE, etat_serialiser(etat)); } catch (e) { /* stockage indisponible */ }
    });
  }
  VL.panneauxEtat = () => etat;            // la preuve
}
