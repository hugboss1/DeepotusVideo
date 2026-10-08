// dz-envoi.js — t139 (08/10/2026) : le contrat « Envoyer vers » entre les écrans de Deepotus (même origine).
//
// L'expéditeur (menu « Envoyer vers… » du bundle, __dzEnvoi) pose dans la fenêtre de l'application :
//     window.__dzEnvoiImg = { cible: "photolab" | "vectorlab" | "tilelab", image: "<nom dans la Bibliothèque>", t: Date.now() }
// puis navigue vers l'écran. L'écran (une iframe) le CONSOMME à son chargement : une seule ouverture, et un envoi
// resté en plan (écran jamais ouvert) ne ressurgit pas des heures plus tard. `?img=<nom>` dans l'URL de l'écran passe
// avant (ouverture directe, page ouverte seule).
//
// Module ES sans dépendance : importé par les labs (chemin relatif), et par les bancs sous node. Une copie octet pour
// octet est servie depuis frontend/dist/shared/ (vérifié par le banc test_photolab_envoi).

export const DUREE_MS = 120000;
// Le nom d'une image de la Bibliothèque : jamais de séparateur de dossier (les routes revérifient de toute façon).
const NOM = /^[A-Za-z0-9_][A-Za-z0-9._ -]{0,180}$/;

export function nomValide(nom) {
  return typeof nom === "string" && NOM.test(nom);
}

// La fenêtre qui porte l'envoi : celle de l'application (le haut de la pile d'iframes), ou null si elle est d'une autre
// origine (lire une de ses propriétés lève) ou absente.
export function porteurDe(fenetre) {
  try {
    const haut = fenetre && fenetre.top;
    if (!haut) return null;
    void haut.__dzEnvoiImg;
    return haut;
  } catch (e) {
    return null;
  }
}

// -> { image, via: "url" | "envoi" } ou null. Consomme l'envoi destiné à `cible` (frais ou périmé : il ne servira plus) ;
// un envoi destiné à un AUTRE écran est laissé intact.
export function lireEnvoi(search, porteur, cible, maintenant = Date.now()) {
  let parUrl = null;
  try { parUrl = new URLSearchParams(search || "").get("img"); } catch (e) { parUrl = null; }
  if (nomValide(parUrl)) return { image: parUrl, via: "url" };
  let e = null;
  try { e = porteur ? porteur.__dzEnvoiImg : null; } catch (err) { return null; }
  if (!e || typeof e !== "object" || e.cible !== cible) return null;
  try { delete porteur.__dzEnvoiImg; } catch (err) { /* porteur gelé : l'âge le rendra caduc */ }
  const age = maintenant - Number(e.t);
  if (!(age >= 0 && age <= DUREE_MS) || !nomValide(e.image)) return null;
  return { image: e.image, via: "envoi" };
}

// L'URL sans son paramètre `img` (après l'ouverture : recharger la page ne rouvre pas l'image une seconde fois).
export function sansImg(href) {
  try {
    const u = new URL(href);
    u.searchParams.delete("img");
    return u.pathname + (u.search ? u.search : "") + u.hash;
  } catch (e) {
    return null;
  }
}

// Recevoir pour l'écran courant (navigateur) : lit l'URL et la fenêtre de l'application, nettoie l'URL.
export function recevoir(cible, fenetre = window) {
  const r = lireEnvoi(fenetre.location.search, porteurDe(fenetre), cible);
  if (r && r.via === "url") {
    const propre = sansImg(fenetre.location.href);
    try { if (propre) fenetre.history.replaceState(fenetre.history.state, "", propre); } catch (e) { /* sans historique */ }
  }
  return r;
}
