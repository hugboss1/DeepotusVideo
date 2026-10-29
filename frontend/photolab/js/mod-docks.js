// mod-docks.js — t371 (29/10/2026) : onglets des groupes de panneaux lisibles sur UNE ligne. L'en-tête défile à
// l'horizontale sans ascenseur visible (molette, onglet actif ramené en vue), un onglet trop long finit en ellipse avec
// son libellé complet en bulle, et un bouton « ⋯ » collé à droite liste tous les onglets dès que la ligne déborde.
// Le rendu (une ligne, marges --pad-2, poignée de la charte) est dans photolab.css. Fonctions PURES exportées
// (qa/docks.test.mjs).

// Largeur gardée à droite de la vue pour le bouton « ⋯ » (24 px de bouton) : un onglet ramené en vue n'est pas dessous.
export const RESERVE_PLUS = 24;

// Le contenu dépasse-t-il la vue ? (1 px de tolérance : arrondis des largeurs fractionnaires du navigateur)
export function deborde(largeurContenu, largeurVue) {
  return Number(largeurContenu) - Number(largeurVue) > 1;
}

// Défilement qui montre l'onglet [gauche, gauche + largeur] dans la vue [defil, defil + vue - reserve] en bougeant le
// moins possible ; un onglet plus large que la vue montre son bord gauche.
export function defilementPour(gauche, largeur, defil, vue, reserve = 0) {
  const utile = Math.max(0, vue - reserve);
  if (gauche < defil || largeur > utile) return gauche;
  if (gauche + largeur > defil + utile) return gauche + largeur - utile;
  return defil;
}

// Molette sur l'en-tête : le pavé horizontal l'emporte quand il domine, sinon la molette verticale fait défiler de
// côté ; borné à [0, max].
export function defilementRoue(defil, dx, dy, max) {
  const pas = Math.abs(dx) > Math.abs(dy) ? dx : dy;
  return Math.min(Math.max(defil + pas, 0), Math.max(0, max));
}

// Items du menu « ⋯ » : un par onglet au libellé non vide, dans l'ordre, avec son index d'origine.
export function entreesMenu(onglets) {
  return (onglets || [])
    .map((o, index) => ({ texte: String(o.texte || "").trim(), actif: !!o.actif, index }))
    .filter((o) => o.texte);
}

export function initDocks(PL) {
  const T = (cle) => (window.dzT ? window.dzT(cle) : cle);
  let menu = null, source = null;
  const fermerMenu = () => {
    if (menu) { menu.remove(); menu = null; }
    if (source) { source.setAttribute("aria-expanded", "false"); source = null; }
  };

  function ouvrirMenu(tete, bouton) {
    fermerMenu();
    const onglets = PL.$$(".onglet", tete);
    menu = document.createElement("div");
    menu.className = "groupe-menu"; menu.setAttribute("role", "menu");
    for (const e of entreesMenu(onglets.map((o) => ({ texte: o.textContent, actif: o.classList.contains("actif") })))) {
      const b = document.createElement("button");
      b.type = "button"; b.setAttribute("role", "menuitemradio"); b.setAttribute("aria-checked", e.actif ? "true" : "false");
      b.textContent = e.texte; b.classList.toggle("actif", e.actif);
      b.addEventListener("click", () => { fermerMenu(); onglets[e.index].click(); onglets[e.index].focus(); });
      menu.appendChild(b);
    }
    document.body.appendChild(menu);
    source = bouton; bouton.setAttribute("aria-expanded", "true");
    const r = bouton.getBoundingClientRect();
    menu.style.top = r.bottom + "px";
    menu.style.left = Math.max(0, Math.min(r.right - menu.offsetWidth, innerWidth - menu.offsetWidth)) + "px";
    (menu.querySelector(".actif") || menu.firstChild)?.focus();
  }
  document.addEventListener("pointerdown", (ev) => { if (menu && !menu.contains(ev.target) && !ev.target.closest(".groupe-plus")) fermerMenu(); }, true);
  document.addEventListener("keydown", (ev) => { if (menu && ev.key === "Escape") { ev.stopPropagation(); fermerMenu(); } }, true);
  window.addEventListener("resize", fermerMenu);

  for (const tete of PL.$$("#panneaux .groupe-tete")) {
    const plus = document.createElement("button");
    plus.type = "button"; plus.className = "groupe-plus"; plus.setAttribute("aria-haspopup", "menu"); plus.setAttribute("aria-expanded", "false");
    plus.innerHTML = PL.icone("dz-action-plus-options", 14);
    tete.appendChild(plus);
    plus.addEventListener("click", () => (menu ? fermerMenu() : ouvrirMenu(tete, plus)));

    // Mesure : débord de la ligne (bouton « ⋯ »), bulle des onglets coupés, onglet actif en vue. Relue quand la
    // largeur change (groupe déplié, langue basculée) ou qu'un onglet change d'état ou de texte.
    const mesurer = () => {
      plus.title = T("photolab.docks.plus"); plus.setAttribute("aria-label", plus.title);
      tete.classList.toggle("deborde", deborde(tete.scrollWidth, tete.clientWidth));
      for (const o of PL.$$(".onglet", tete)) {
        if (deborde(o.scrollWidth, o.clientWidth)) o.title = o.textContent.trim(); else o.removeAttribute("title");
      }
      const actif = PL.$(".onglet.actif", tete);
      // .groupe-tete est positionné (photolab.css) : offsetLeft de l'onglet se lit dans le contenu de l'en-tête
      if (actif) tete.scrollLeft = defilementPour(actif.offsetLeft, actif.offsetWidth, tete.scrollLeft,
        tete.clientWidth, tete.classList.contains("deborde") ? RESERVE_PLUS : 0);
    };
    tete.addEventListener("wheel", (ev) => {
      if (!tete.classList.contains("deborde")) return;
      ev.preventDefault();
      tete.scrollLeft = defilementRoue(tete.scrollLeft, ev.deltaX, ev.deltaY, tete.scrollWidth - tete.clientWidth);
    }, { passive: false });
    if (window.ResizeObserver) new ResizeObserver(mesurer).observe(tete);
    new MutationObserver(mesurer).observe(tete, { subtree: true, characterData: true, childList: true, attributeFilter: ["class"] });
    mesurer();
  }
}
