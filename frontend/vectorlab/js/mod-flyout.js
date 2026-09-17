// mod-flyout.js — les menus DÉTACHÉS de la barre d'outils de gauche : un
// bouton à menu porte une marque d'angle ; clic droit, clic sur l'angle ou
// appui long ouvre le menu à côté du bouton (un seul à la fois, Échap ou
// clic dehors le ferme). Menu Forme : les sept formes, la courante marquée
// — choisir active l'outil Forme (pose au clic ou au glisser). Menu
// Symboles : poser une instance de chaque symbole, ou en créer un depuis la
// sélection. La partie haute est PURE.
import { FORMES } from "./mod-formes.js";
import { op_symbole_creer, op_instance_poser } from "./mod-doc.js";

const GLYPHES = { polygone: "⬠", hexagone: "⬡", etoile: "☆", engrenage: "⚙", fleche: "➜", donut: "◎", spirale: "๑" };
export function flyout_formes(formes, courante) {
  return (formes || []).map((f) => ({ id: f.id, libelle: f.nom, glyphe: GLYPHES[f.id] || "◇", actif: f.id === courante }));
}
export function flyout_symboles(symboles) {
  const entrees = Object.entries(symboles || {}).map(([id, s]) => ({ id, libelle: s.nom || id, detail: `${(s.objets || []).length} objet${(s.objets || []).length > 1 ? "s" : ""}`, action: "poser" }));
  if (!entrees.length) entrees.push({ id: "", libelle: "aucun symbole", detail: "", action: "", desactive: true });
  entrees.push({ id: "", libelle: "Créer depuis la sélection", detail: "", action: "creer" });
  return entrees;
}
export function flyout_position(bouton, taille, fenetre, marge = 6) {
  let x = bouton.x + bouton.w + marge;
  if (x + taille.w > fenetre.w - marge) x = bouton.x - marge - taille.w;
  let y = bouton.y;
  if (y + taille.h > fenetre.h - marge) y = Math.max(marge, fenetre.h - marge - taille.h);
  return { x, y };
}

export function initFlyout(VL) {
  const { $, etat } = VL;
  const hote = document.createElement("div");
  hote.id = "flyout"; hote.hidden = true;
  document.body.appendChild(hote);
  let ouvertPour = null, timerLong = 0;
  const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  function fermer() { hote.hidden = true; hote.innerHTML = ""; ouvertPour = null; }
  function ouvrir(bouton, titre, entrees, surChoix) {
    if (ouvertPour === bouton) { fermer(); return; }
    fermer();
    ouvertPour = bouton;
    hote.innerHTML = `<div class="fo-titre">${esc(titre)}</div>` + entrees.map((e, i) =>
      `<button class="fo-item${e.actif ? " actif" : ""}" data-i="${i}" ${e.desactive ? "disabled" : ""}>${e.glyphe ? `<span class="fo-glyphe">${e.glyphe}</span>` : ""}<span class="fo-lib">${esc(e.libelle)}</span>${e.detail ? `<small>${esc(e.detail)}</small>` : ""}</button>`).join("");
    hote.hidden = false;
    const r = bouton.getBoundingClientRect();
    const p = flyout_position({ x: r.left, y: r.top, w: r.width, h: r.height }, { w: hote.offsetWidth, h: hote.offsetHeight }, { w: window.innerWidth, h: window.innerHeight }, 6);
    hote.style.left = p.x + "px"; hote.style.top = p.y + "px";
    hote.querySelectorAll(".fo-item").forEach((b) => b.addEventListener("click", () => { const e = entrees[+b.dataset.i]; fermer(); surChoix(e); }));
  }
  const menus = {
    forme: (b) => ouvrir(b, "Forme paramétrique", flyout_formes(FORMES, etat.formeCourante), (e) => {
      etat.formeCourante = e.id; VL.setOutil("forme");
      VL.toast(`forme « ${e.libelle} » : cliquer pour la poser (rayon 40) ou glisser depuis le centre`);
      if (VL.surSelection) VL.surSelection();          // le panneau Forme reflète le choix
    }),
    symbole: (b) => ouvrir(b, "Symboles", flyout_symboles(etat.doc && etat.doc.symboles), (e) => {
      if (e.action === "poser") { const id = VL.executer(op_instance_poser, etat.calqueActif, e.id, 24, 24); if (id) { VL.setOutil("select"); VL.setSelection([id]); } }
      else if (e.action === "creer") {
        if (!etat.selection.length) { VL.toast("sélectionner d'abord les objets du symbole", true); return; }
        const sid = VL.executer(op_symbole_creer, etat.selection.slice(), undefined);
        if (sid) VL.toast(`symbole ${sid} créé — le menu Symboles le pose`);
      }
    }),
  };
  // le bouton Symboles (persona Vecteur) — il n'est qu'un menu
  {
    const b = document.createElement("button");
    b.dataset.outil = "symbole"; b.dataset.menu = "symbole"; b.className = "a-menu"; b.title = "Symboles — poser une instance ou créer un symbole depuis la sélection (menu)"; b.textContent = "⧈";
    b.addEventListener("click", (ev) => { ev.stopPropagation(); menus.symbole(b); });
    $("#outils").appendChild(b);
  }
  const bForme = $('#outils [data-outil="forme"]');
  if (bForme) { bForme.dataset.menu = "forme"; bForme.classList.add("a-menu"); }
  for (const b of document.querySelectorAll("#outils [data-menu]")) {
    b.addEventListener("contextmenu", (ev) => { ev.preventDefault(); menus[b.dataset.menu](b); });
    b.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      const r = b.getBoundingClientRect();
      // l'angle bas-droit (10 px) ouvre tout de suite ; ailleurs, un appui long
      if (ev.clientX > r.right - 12 && ev.clientY > r.bottom - 12) { ev.preventDefault(); ev.stopPropagation(); menus[b.dataset.menu](b); b.dataset.angle = "1"; return; }
      timerLong = setTimeout(() => { menus[b.dataset.menu](b); b.dataset.angle = "1"; }, 400);
    });
    b.addEventListener("pointerup", () => clearTimeout(timerLong));
    b.addEventListener("pointerleave", () => clearTimeout(timerLong));
    b.addEventListener("click", (ev) => { if (b.dataset.angle) { delete b.dataset.angle; ev.stopImmediatePropagation(); ev.preventDefault(); } }, true);
  }
  document.addEventListener("pointerdown", (ev) => { if (!hote.hidden && !hote.contains(ev.target) && !(ouvertPour && ouvertPour.contains(ev.target))) fermer(); }, true);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !hote.hidden) { fermer(); ev.stopImmediatePropagation(); } }, true);
  VL.flyout = { ouvrir: (nom) => menus[nom] && menus[nom]($(`#outils [data-menu="${nom}"]`)), fermer, element: hote };   // la preuve
}
