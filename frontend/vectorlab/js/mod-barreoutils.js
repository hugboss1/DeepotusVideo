// mod-barreoutils.js — la colonne d'outils d'Affinity (R2) : les boutons
// EXISTANTS de #outils sont réordonnés par famille (ils gardent leurs
// data-outil et leurs écouteurs), seul le membre courant de chaque
// famille est visible, l'icône fine remplace le glyphe, le triangle
// d'angle / l'appui long ouvrent le flyout vertical de la famille (rendu
// par mod-flyout), un raccourci qui choisit un membre replié fait
// basculer la famille. Le membre courant est mémorisé (dz_vl_familles).
import { FAMILLES, famille_de, membre_courant, choisir_membre, flyout_famille, touche_de } from "./mod-familles.js";
import { icone_svg } from "./mod-icones.js";

export function initBarreOutils(VL) {
  const { $, etat } = VL;
  const nav = $("#outils");
  if (!nav) return;
  const bouton = (outil) => nav.querySelector(`button[data-outil="${outil}"]`);
  let familles = {};
  try { familles = JSON.parse(localStorage.getItem("dz_vl_familles") || "{}") || {}; } catch (e) { familles = {}; }
  if (typeof familles !== "object" || Array.isArray(familles)) familles = {};

  // 1. réordonner : famille par famille, membre par membre ; un bouton hors famille reste à la fin
  for (const f of FAMILLES) for (const x of f.membres) {
    const b = bouton(x.outil);
    if (!b) continue;
    nav.appendChild(b);
    b.dataset.famille = f.id;
    if (f.membres.length > 1) b.classList.add("a-famille");
  }
  // 2. icônes fines + raccourci dans la bulle
  for (const b of nav.querySelectorAll("button[data-outil]")) {
    b.innerHTML = icone_svg(b.dataset.outil, 18);
    const t = touche_de(b.dataset.outil);
    if (t && !/\([A-Z]\)\s*$/.test(b.title)) b.title = `${b.title} (${t})`;
  }
  // 3. replier : seul le membre courant de chaque famille est visible
  function appliquer() {
    for (const f of FAMILLES) {
      const c = membre_courant(familles, f.id);
      for (const x of f.membres) { const b = bouton(x.outil); if (b) b.classList.toggle("outil-repli", x.outil !== c); }
    }
  }
  function montrer(outil) {
    if (!famille_de(outil)) return false;
    familles = choisir_membre(familles, outil);
    try { localStorage.setItem("dz_vl_familles", JSON.stringify(familles)); } catch (e) { /* stockage indisponible */ }
    appliquer();
    return true;
  }
  // 4. le flyout vertical de la famille — mod-flyout le rend et le positionne
  VL.familleOuvrir = (b) => {
    const f = famille_de(b.dataset.outil);
    if (!f || f.membres.length < 2 || !VL.flyout) return false;
    VL.flyout.ouvrirMenu(b, { titre: f.nom, entrees: flyout_famille(f, membre_courant(familles, f.id)), choisir: (e) => { montrer(e.id); VL.setOutil(e.id); } });
    return true;
  };
  if (VL.flyout && VL.flyout.armer) for (const b of nav.querySelectorAll("button[data-outil]")) VL.flyout.armer(b);
  // 5. un raccourci ou un module qui choisit un membre replié : la famille bascule
  const sOutil = VL.surOutil;
  VL.surOutil = () => { sOutil(); montrer(etat.outil); };
  // VL.flyout.ouvrir(nom) doit trouver un bouton VISIBLE (le menu se pose à côté) : montrer d'abord
  if (VL.flyout) { const oOuvrir = VL.flyout.ouvrir; VL.flyout.ouvrir = (nom) => { montrer(nom); return oOuvrir(nom); }; }
  appliquer();
  VL.familles = { etat: () => familles, montrer, bouton, visibles: () => [...nav.querySelectorAll("button[data-outil]")].filter((b) => b.offsetHeight > 0).map((b) => b.dataset.outil) };   // la preuve
}
