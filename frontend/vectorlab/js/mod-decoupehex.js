// mod-decoupehex.js — plateau (lot 1) : Export › Découper en hexagones… Le document du Vectorlab devient un jeu
// « plateau » du Card Forge par le dialogue partagé (/shared/dz-decoupe-hex.js : cadrage, grille, création du jeu).
//
// L'image à découper est le document lui-même, rastérisé sans lire la case « fond transparent » (la couleur de fond du
// document est gardée ; les zones sans fond sont aplaties sur du blanc par le serveur, à la découpe), à la
// résolution qui donne 300 ppp sur la grille choisie, au plus 8192 px sur le plus grand côté. Elle est déposée dans la
// Bibliothèque sous vector_<docId>_plateau_<k>x.png : la lignée des tuiles remonte au document par ce nom.
// L'aperçu du dialogue est un rendu borné (APERCU_MAX), jamais le document à pleine taille.
import { ouvrirDecoupeHex } from "../../shared/dz-decoupe-hex.js";

export const COTE_MAX_PX = 8192;       // plus grand côté de l'image exportée (comme les autres exports du lab)
export const PPP_CIBLE = 300;
export const APERCU_MAX = 1024;        // plus grand côté de l'aperçu (le dialogue le redessine à sa taille)

/** Échelle d'export : k = min(8192 / max(w, h), cible / w), cible = ceil(largeurMm / 25.4 × 300) px de large. */
export function echelleDecoupe(w, h, largeurMm) {
  const cible = Math.ceil(largeurMm / 25.4 * PPP_CIBLE);
  const k = Math.min(COTE_MAX_PX / Math.max(w, h), cible / w);
  return Number.isFinite(k) && k > 0 ? k : 1;
}

/** Le blob PNG de l'aperçu, dessiné dans un canevas (le dialogue le redessine à sa taille). */
async function blobVersCanvas(blob) {
  const im = await createImageBitmap(blob);
  const cv = document.createElement("canvas");
  cv.width = im.width;
  cv.height = im.height;
  cv.getContext("2d").drawImage(im, 0, 0);
  if (im.close) im.close();
  return cv;
}

// -> {deck, tuiles} | null (annulé, ou pas de document). `ouvrir` et `versCanvas` sont injectables (banc node).
let enCours = false;       // un seul dialogue : un second clic pendant le rendu de l'aperçu ou le dialogue est ignoré

export async function decouperHex(VL, T, { ouvrir = ouvrirDecoupeHex, versCanvas = blobVersCanvas } = {}) {
  if (enCours) return null;
  enCours = true;
  try {
    return await ouvrirDocument(VL, T, ouvrir, versCanvas);
  } finally {
    enCours = false;
  }
}

async function ouvrirDocument(VL, T, ouvrir, versCanvas) {
  const { etat } = VL;
  if (!etat.doc) return null;
  const { w, h } = etat.doc.taille;
  const kApercu = Math.min(1, APERCU_MAX / Math.max(w, h));
  const apercu = await versCanvas(await VL.rasteriser(kApercu, false));
  return ouvrir({
    largeur: w, hauteur: h, apercu,
    nomImage: (etat.meta && etat.meta.name) || etat.docId,
    fournirImage: ({ largeurMm }) => VL.exporterPNG(echelleDecoupe(w, h, largeurMm), { suffixe: "_plateau", opaque: true }),
    T,
  });
}
