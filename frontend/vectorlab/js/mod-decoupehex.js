// mod-decoupehex.js — plateau (lot 1) : Export › Découper en hexagones… Le document du Vectorlab devient un jeu
// « plateau » du Card Forge par le dialogue partagé (/shared/dz-decoupe-hex.js : cadrage, grille, création du jeu).
//
// L'image à découper est la RÉGION CADRÉE du document (le rectangle couvrant de la grille, au zoom et à la position
// choisis dans le dialogue), rastérisée sans lire la case « fond transparent » (la couleur de fond du document est
// gardée ; les zones sans fond sont aplaties sur du blanc par le serveur, à la découpe), à la résolution qui donne
// 300 ppp sur la grille, au plus 8192 px sur le plus grand côté de la région. Le dialogue poste alors un cadrage
// neutre : la région est déjà la bonne. Elle est déposée dans la Bibliothèque sous
// vector_<docId>_plateau_<AAAAMMJJ-HHMMSS>_<k>x.png (l'horodatage évite qu'un second export au même k écrase le
// premier : les tuiles d'un plateau gardent leur parent) : la lignée des tuiles remonte au document par ce nom.
// L'aperçu du dialogue est un rendu borné (APERCU_MAX), jamais le document à pleine taille.
import { ouvrirDecoupeHex } from "../../shared/dz-decoupe-hex.js";
import { cadrageCouvrant } from "../../shared/dz-decoupe-hex-logique.js";

export const COTE_MAX_PX = 8192;       // plus grand côté de l'image exportée (comme les autres exports du lab)
export const PPP_CIBLE = 300;
export const APERCU_MAX = 1024;        // plus grand côté de l'aperçu (le dialogue le redessine à sa taille)

/** Échelle d'export d'une région de w × h unités du document :
    k = min(8192 / max(w, h), cible / w), cible = ceil(largeurMm / 25.4 × 300) px de large. */
export function echelleDecoupe(w, h, largeurMm) {
  const cible = Math.ceil(largeurMm / 25.4 * PPP_CIBLE);
  const k = Math.min(COTE_MAX_PX / Math.max(w, h), cible / w);
  return Number.isFinite(k) && k > 0 ? k : 1;
}

/** Les ppp que l'export donnera réellement pour ce cadre {w, h} : 300, ou moins quand la borne de 8192 px mord. */
export function pppDecoupe(rect, largeurMm) {
  return rect.w * echelleDecoupe(rect.w, rect.h, largeurMm) / (largeurMm / 25.4);
}

/** AAAAMMJJ-HHMMSS (heure locale) : suffixe d'unicité du nom déposé. */
export function horodatage(d = new Date()) {
  const n = (v, l = 2) => String(v).padStart(l, "0");
  return `${n(d.getFullYear(), 4)}${n(d.getMonth() + 1)}${n(d.getDate())}-${n(d.getHours())}${n(d.getMinutes())}${n(d.getSeconds())}`;
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

export async function decouperHex(VL, T, { ouvrir = ouvrirDecoupeHex, versCanvas = blobVersCanvas, maintenant = () => new Date() } = {}) {
  if (enCours) return null;
  enCours = true;
  try {
    return await ouvrirDocument(VL, T, ouvrir, versCanvas, maintenant);
  } finally {
    enCours = false;
  }
}

async function ouvrirDocument(VL, T, ouvrir, versCanvas, maintenant) {
  const { etat } = VL;
  if (!etat.doc) return null;
  const { w, h } = etat.doc.taille;
  const kApercu = Math.min(1, APERCU_MAX / Math.max(w, h));
  const apercu = await versCanvas(await VL.rasteriser(kApercu, false));
  return ouvrir({
    largeur: w, hauteur: h, apercu,
    nomImage: (etat.meta && etat.meta.name) || etat.docId,
    ppp: pppDecoupe,
    fournirImage: async ({ largeurMm, hauteurMm, cadrage = {} }) => {
      // seule la région cadrée est rastérisée : le ppp est celui de la grille, quel que soit le zoom ou le rapport
      const rect = cadrageCouvrant(w, h, largeurMm, hauteurMm, cadrage.zoom, cadrage.x, cadrage.y);
      const nom = await VL.exporterPNG(echelleDecoupe(rect.w, rect.h, largeurMm),
        { suffixe: "_plateau_" + horodatage(maintenant()), opaque: true, cadre: rect });
      return { nom, cadrage: { zoom: 1, x: 0.5, y: 0.5 } };
    },
    T,
  });
}
