// mod-infobulle.js — les bulles d'information de l'éditeur : au survol d'un
// élément à `title` (outils, menus, panneaux), une bulle stylée, centrée
// sous l'élément, bornée à la fenêtre, passe au-dessus si la place manque ;
// le title natif est neutralisé le temps du survol (pas de double bulle)
// et rendu au départ. La position et la coupe du texte sont PURES.

export function bulle_position(ancre, taille, fenetre, marge = 8) {
  let x = ancre.x + ancre.w / 2 - taille.w / 2;
  x = Math.max(marge, Math.min(fenetre.w - marge - taille.w, x));
  let dessous = ancre.y + ancre.h + marge + taille.h <= fenetre.h - marge;
  let y = dessous ? ancre.y + ancre.h + marge : ancre.y - marge - taille.h;
  if (!dessous && y < marge) { y = marge; }
  if (dessous && y < marge) y = marge;
  return { x, y, dessous };
}
// les tirets cadratins et les points médians des titles deviennent des lignes
export function texte_bulle(title) {
  const t = String(title || "").replace(/\s+/g, " ").trim();
  if (!t) return [];
  return t.split(/\s+[—·]\s+/).map((s) => s.trim()).filter(Boolean);
}

export function initInfobulle(VL) {
  const bulle = document.createElement("div");
  bulle.className = "infobulle";
  bulle.hidden = true;
  document.body.appendChild(bulle);
  let courant = null;
  const montrer = (el) => {
    const title = el.getAttribute("title");
    if (!title) return;
    el.dataset.tip = title;
    el.removeAttribute("title");
    courant = el;
    bulle.innerHTML = texte_bulle(title).map((l, i) => `<div class="${i ? "ib-suite" : "ib-tete"}">${l.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</div>`).join("");
    bulle.hidden = false;
    const r = el.getBoundingClientRect();
    const p = bulle_position({ x: r.left, y: r.top, w: r.width, h: r.height }, { w: bulle.offsetWidth, h: bulle.offsetHeight },
                             { w: window.innerWidth, h: window.innerHeight }, 8);
    bulle.style.left = p.x + "px"; bulle.style.top = p.y + "px";
    bulle.classList.toggle("dessus", !p.dessous);
  };
  const cacher = () => {
    if (courant && courant.dataset.tip !== undefined) { courant.setAttribute("title", courant.dataset.tip); delete courant.dataset.tip; }
    courant = null;
    bulle.hidden = true;
  };
  document.addEventListener("mouseover", (ev) => {
    const el = ev.target.closest && ev.target.closest("[title]");
    if (el === courant) return;
    cacher();
    if (el && !el.closest(".vl-dlg") && el.closest("#outils, #panneauCalques, .bar, #personas, #hintOutil, .exp-menu")) montrer(el);
  });
  document.addEventListener("mouseout", (ev) => {
    if (courant && !courant.contains(ev.relatedTarget)) cacher();
  });
  document.addEventListener("pointerdown", cacher, true);
  window.addEventListener("blur", cacher);
  VL.infobulle = { montrer, cacher, element: bulle };   // la preuve
}
