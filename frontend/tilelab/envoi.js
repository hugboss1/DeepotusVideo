// envoi.js — t139 (Photolab P4, 08/10/2026) : une image envoyée par un autre écran (« Envoyer vers › Tile Lab » de la
// Bibliothèque ou du Photolab ; contrat frontend/shared/dz-envoi.js) devient la source de la tuile. Module chargé APRÈS
// tilelab.js : la poignée window.__tl (select) existe déjà.
import { recevoir } from "../shared/dz-envoi.js";

export function appliquer(recu, tl) {
  if (!recu || !tl || typeof tl.select !== "function") return false;
  tl.select(recu.image);
  return true;
}

if (typeof window !== "undefined" && window.document) appliquer(recevoir("tilelab"), window.__tl);
