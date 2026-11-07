// envoi.js — t139 (Photolab P4, 08/10/2026) : une image envoyée par un autre écran (« Envoyer vers › Tile Lab » de la
// Bibliothèque ou du Photolab ; contrat frontend/shared/dz-envoi.js) devient la source de la tuile. Module chargé APRÈS
// tilelab.js : la poignée window.__tl (select) existe déjà.
import { recevoir } from "../shared/dz-envoi.js";

// t421 : un nom refusé est DIT dans le toast de l'écran (jamais une source vide en silence).
function dire(nom) {
  const el = typeof document !== "undefined" ? document.getElementById("toast") : null;
  if (!el || typeof globalThis.dzT !== "function") return;
  el.textContent = globalThis.dzT("commun.envoi.refuse", { nom });
  el.classList.remove("hidden"); el.classList.add("err");
  setTimeout(() => el.classList.add("hidden"), 4200);
}

export function appliquer(recu, tl) {
  if (recu && recu.refus) { dire(recu.refus); return false; }
  if (!recu || !tl || typeof tl.select !== "function") return false;
  tl.select(recu.image);
  return true;
}

if (typeof window !== "undefined" && window.document) appliquer(recevoir("tilelab"), window.__tl);
