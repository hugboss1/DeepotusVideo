// mod-plateau.js — plateau (lot 1) : Image › Découper en hexagones… Le document du Photolab devient un jeu « plateau »
// du Card Forge par le dialogue partagé (/shared/dz-decoupe-hex.js : cadrage, grille, création du jeu).
//
// L'image à découper : le Photolab ne suit pas le nom d'origine du document dans la Bibliothèque (plusieurs documents,
// ouvertures par glisser-déposer, nouveaux documents…), donc il ENREGISTRE toujours (PL.enregistrerBibliotheque : un
// nouveau fichier de la Bibliothèque, lignée « retouche » tenue par le pont). Les tuiles en héritent leur lignée.
// L'aperçu du dialogue : un rendu demandé au moteur (POST /rendu), jamais le dessin de la vue, qui peut montrer un
// aperçu de transformation en cours.
import { ouvrirDecoupeHex } from "../../shared/dz-decoupe-hex.js";
import { nomDocument } from "./mod-fichier.js";

export const APERCU_MAX = 1024;      // plus grand côté de l'aperçu (le dialogue le redessine à sa taille)

function chargerImage(url) {
  return new Promise((ok, ko) => {
    const im = new Image();
    im.onload = () => ok(im);
    im.onerror = () => ko(new Error(url));
    im.src = url;
  });
}

// Image fournie au dialogue au moment de créer : le document enregistré. Un refus (null : déjà signalé par mod-api) devient
// une erreur affichée dans le dialogue.
export function fournisseurImage(PL, T) {
  return async function fournirImage() {
    const r = await PL.enregistrerBibliotheque();
    if (!r || !r.filename) throw new Error(T("photolab.plateau.erreur_enregistrement"));
    return r.filename;
  };
}

// -> {deck, tuiles} | null (annulé, ou pas de document). `ouvrir` et `charger` sont injectables (banc node).
export async function decouperHex(PL, T, { ouvrir = ouvrirDecoupeHex, charger = chargerImage } = {}) {
  const doc = PL.etat.doc;
  if (!doc) return null;
  let apercu;
  try {
    const r = await PL.post("/rendu", { maxSide: Math.min(APERCU_MAX, Math.max(doc.width, doc.height)) });
    apercu = await charger(r.url);
  } catch (e) {
    PL.signaler(T("photolab.rendu.echec"), true);
    return null;
  }
  return ouvrir({ largeur: doc.width, hauteur: doc.height, apercu, nomImage: nomDocument(doc.name), fournirImage: fournisseurImage(PL, T), T });
}

export function initPlateau(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.actions = PL.actions || {};
  PL.actions["pl.plateau.decouper"] = () => decouperHex(PL, T);
}
