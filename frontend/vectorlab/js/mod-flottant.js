// mod-flottant.js — t190-bis : les PANNEAUX FLOTTANTS posés DANS #stage (le dialogue IA du canevas #iaDialogue de
// mod-ia, le panneau « Image IA sur le calque » #iaCalqueDlg de mod-iacalque, l'éditeur de texte en place
// textarea.tx-editeur de mod-typo) gardent leurs gestes, quel que soit l'outil actif.
//
// Deux gardes, parce que les outils écoutent #stage de deux façons :
//   - en BULLE (l'outil Sélection de mod-tools, setPointerCapture dès le clic gauche) : garderClics(el) arrête les
//     gestes du panneau à lui-même (ses propres écouteurs, dont la poignée, ont déjà joué) ;
//   - en CAPTURE (Plume, Texte, Nœud, Pipette, Main/Loupe/Dégradé…, Pixel, pinceau vectoriel, tranches, Alt+glisser,
//     le panoramique de core.js) : ils jouent AVANT le panneau, garderClics arrive trop tard — chacun sort tout de
//     suite si dansPanneau(ev) (VL.dansPanneau, posé par core.js). Sans cela, ouvrir le panneau puis changer
//     d'outil le rendait inerte (stopPropagation + preventDefault + setPointerCapture de l'outil : le click partait
//     sur #stage).
// Seuls les gestes qui COMMENCENT un geste d'outil sont gardés (pointerdown, dblclick, contextmenu, molette) : un
// pointermove / pointerup commencé sur la scène et relâché au-dessus d'un panneau doit finir son geste.
//
// Module sans DOM à l'import (banc qa/panneaux_flottants.test.mjs) ; hors base L6, aucun texte affiché.

// ce qui est un panneau flottant : les deux dialogues (classe .ia-dlg), l'éditeur en place, et tout élément
// marqué par garderClics
export const PANNEAUX_FLOTTANTS = ".ia-dlg, .tx-editeur, [data-vl-flottant]";

// l'événement vient-il d'un panneau flottant ? (sa cible ou un de ses parents)
export function dansPanneau(ev) {
  const t = ev && ev.target;
  return !!(t && typeof t.closest === "function" && t.closest(PANNEAUX_FLOTTANTS));
}

// les gestes arrêtés au panneau, en bulle. Le CLAVIER aussi : le keydown global de core.js n'ignore que
// INPUT/TEXTAREA — sur une liste ou un bouton du panneau, Échap désélectionnait et une lettre changeait d'outil.
// Rien n'est preventDefault : la case, les listes et le texte gardent leur geste natif ; la molette ne zoome pas
// le canevas.
export const GESTES_GARDES = ["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel", "keydown"];
export function garderClics(el) {
  if (el.dataset) el.dataset.vlFlottant = "1";
  for (const t of GESTES_GARDES) {
    el.addEventListener(t, (ev) => ev.stopPropagation(), t === "wheel" ? { passive: true } : false);
  }
}

// un texte sûr dans un gabarit HTML (attribut ou contenu)
export const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
