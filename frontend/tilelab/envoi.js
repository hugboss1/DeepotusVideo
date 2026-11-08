// envoi.js — t139 (Photolab P4, 08/10/2026) : une image envoyée par un autre écran (« Envoyer vers › Tile Lab » de la
// Bibliothèque ou du Photolab ; contrat frontend/shared/dz-envoi.js) devient la source de la tuile. Module chargé APRÈS
// tilelab.js : la poignée window.__tl (select) existe déjà.
import { recevoir } from "../shared/dz-envoi.js";

// t421 : un nom refusé est DIT dans le toast de l'écran (jamais une source vide en silence).
function dire(nom) {
  const el = typeof document !== "undefined" ? document.getElementById("toast") : null;
  const t = globalThis.dzT;
  if (!el || typeof t !== "function") return;
  el.textContent = t("commun.envoi.refuse", { nom });
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
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
