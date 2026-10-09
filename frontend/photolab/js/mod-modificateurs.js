// mod-modificateurs.js — t159 (parité L9) : Fenêtre › Touches de modification. Un petit panneau flottant pour l'écran
// tactile ou le stylet : Maj, Ctrl, Alt. Un clic arme la touche pour le PROCHAIN geste, un double clic la tient
// jusqu'au clic suivant. Les gestes, clics et touches lisent alors `ev.shiftKey`, `ev.ctrlKey`, `ev.altKey` comme si la
// touche était enfoncée : les propriétés sont redéfinies sur l'événement en capture, AVANT tout module — aucun module
// n'a à connaître le panneau. Fonctions PURES exportées (qa/modificateurs.test.mjs).

export const TOUCHES = ["shift", "ctrl", "alt"];
export const PROPRIETE = { shift: "shiftKey", ctrl: "ctrlKey", alt: "altKey" };
// États d'une touche : "" (relâchée), "une" (le prochain geste), "tenue" (jusqu'à un nouveau clic).
export function suivant(etat, geste) {
  if (geste === "double") return "tenue";
  if (geste === "clic") return etat ? "" : "une";
  if (geste === "consomme") return etat === "une" ? "" : etat;
  return etat;
}
export const actives = (etats) => TOUCHES.filter((t) => etats[t]);
// Événements que le panneau modifie (les gestes de la toile, les clics, la molette, le clavier).
export const EVENEMENTS = ["pointerdown", "pointermove", "pointerup", "click", "dblclick", "wheel", "keydown", "keyup", "mousedown", "mouseup"];

export function initModificateurs(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const CLE = "dz-photolab-modificateurs";
  const etats = { shift: "", ctrl: "", alt: "" };
  let visible = false;
  try { visible = localStorage.getItem(CLE) === "1"; } catch (e) { /* stockage refusé : panneau caché */ }

  const panneau = document.createElement("div");
  panneau.className = "pl-modificateurs"; panneau.setAttribute("role", "toolbar");
  panneau.setAttribute("aria-label", T("photolab.modificateurs.titre"));
  const boutons = {};
  for (const t of TOUCHES) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "pl-mod"; b.dataset.touche = t;
    b.textContent = T("photolab.modificateurs." + t);
    b.title = T("photolab.modificateurs.aide");
    b.setAttribute("aria-pressed", "false");
    let minut = null;
    // clic simple différé : un double clic ne doit pas armer puis relâcher
    b.addEventListener("click", () => { clearTimeout(minut); minut = setTimeout(() => { etats[t] = suivant(etats[t], "clic"); maj(); }, 220); });
    b.addEventListener("dblclick", () => { clearTimeout(minut); etats[t] = suivant(etats[t], "double"); maj(); });
    boutons[t] = b; panneau.appendChild(b);
  }
  document.body.appendChild(panneau);

  function maj() {
    panneau.hidden = !visible;
    for (const t of TOUCHES) {
      boutons[t].classList.toggle("une", etats[t] === "une");
      boutons[t].classList.toggle("tenue", etats[t] === "tenue");
      boutons[t].setAttribute("aria-pressed", etats[t] ? "true" : "false");
    }
  }
  maj();

  // Les touches armées s'ajoutent aux événements, en capture, avant tout autre module.
  const horsPanneau = (ev) => !(ev.target && ev.target.closest && ev.target.closest(".pl-modificateurs"));
  for (const type of EVENEMENTS) {
    window.addEventListener(type, (ev) => {
      if (!horsPanneau(ev)) return;
      for (const t of actives(etats)) { try { Object.defineProperty(ev, PROPRIETE[t], { value: true, configurable: true }); } catch (e) { /* événement figé */ } }
      // un geste complet consomme les touches armées pour une fois
      if ((type === "pointerup" || type === "keyup") && actives(etats).some((t) => etats[t] === "une")) {
        setTimeout(() => { for (const t of TOUCHES) etats[t] = suivant(etats[t], "consomme"); maj(); }, 0);
      }
    }, { capture: true, passive: type !== "wheel" && type !== "keydown" });
  }

  PL.actions = PL.actions || {};
  PL.actions["window.panel.modifierKeys"] = () => {
    visible = !visible;
    if (!visible) for (const t of TOUCHES) etats[t] = "";
    try { localStorage.setItem(CLE, visible ? "1" : "0"); } catch (e) { /* facultatif */ }
    maj();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  };
  // coche dans Fenêtre
  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => {
    const voir = (entrees) => { for (const e of entrees || []) { if (e.type === "sous-menu") voir(e.entrees); else if (e.id === "window.panel.modifierKeys") e.coche = visible; } };
    for (const m of menus) voir(m.entrees);
    return menus;
  });
  PL.modificateurs = { get etats() { return { ...etats }; }, get visible() { return visible; } };
}
