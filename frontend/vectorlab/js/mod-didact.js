// mod-didact.js — l'aide didactique animée (finitions UI, 20/09/2026) : une
// FICHE par option (titre, phrase « pour un enfant de cinq ans », animation
// à trois temps faite de vraies captures — aide/<module>.<id>.webp), montrée
// au survol long (900 ms, après la bulle courte de mod-infobulle) ou par un
// « ? » posé à côté de l'option. Le panneau lit aide/index.json ; une option
// sans fiche garde la bulle courte. Les fiches sont FABRIQUÉES par le skill
// didacticiel-option (jamais dessinées à la main). Partie pure en tête.
import { bulle_position } from "./mod-infobulle.js";

export const DIDACT_DELAI_MS = 900;
export const DIDACT_LARGEUR = 320;
export const DIDACT_MOTS_MAX = 25;

export function fiche_pour(index, id) {
  if (!Array.isArray(index) || !id) return null;
  return index.find((f) => f && f.id === id) || null;
}

export function compter_mots(phrase) {
  if (!phrase) return 0;
  const m = String(phrase).match(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu);
  return m ? m.length : 0;
}

export function valider_fiche(f) {
  const e = [];
  if (!f || !f.id) e.push("id manquant");
  if (!f || !f.titre) e.push("titre manquant");
  const n = compter_mots(f && f.phrase);
  if (!n) e.push("phrase manquante");
  else if (n > DIDACT_MOTS_MAX) e.push(`phrase de ${n} mots (max ${DIDACT_MOTS_MAX})`);
  if (!f || !/\.(webp|png)$/i.test(String(f.fichier || ""))) e.push("fichier .webp ou .png attendu");
  if (!f || !Number.isInteger(f.version)) e.push("version entière attendue");
  return e;
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function didact_html(f) {
  return `<img class="vl-didact-anim" src="aide/${esc(f.fichier)}?v=${esc(f.version)}" width="${DIDACT_LARGEUR}" height="200" alt="">`
    + `<div class="vl-didact-titre">${esc(f.titre)}</div><div class="vl-didact-phrase">${esc(f.phrase)}</div>`;
}

/* ── DOM ── */
export function initDidact(VL) {
  let index = [];
  const encart = document.createElement("div");
  encart.id = "vlDidact"; encart.className = "vl-didact hidden";
  document.body.appendChild(encart);
  let timer = null, courant = null;

  function montrer(el) {
    const f = fiche_pour(index, el && el.id);
    if (!f) return false;
    if (VL.infobulle) VL.infobulle.cacher();
    courant = el;
    encart.innerHTML = didact_html(f);
    encart.classList.remove("hidden");
    const r = el.getBoundingClientRect();
    const p = bulle_position({ x: r.left, y: r.top, w: r.width, h: r.height }, { w: encart.offsetWidth, h: encart.offsetHeight },
                             { w: window.innerWidth, h: window.innerHeight }, 8);
    encart.style.left = p.x + "px"; encart.style.top = p.y + "px";
    return true;
  }
  function cacher() { clearTimeout(timer); timer = null; courant = null; encart.classList.add("hidden"); encart.innerHTML = ""; }

  const cible = (ev) => {
    let el = ev.target && ev.target.closest ? ev.target.closest("[id]") : null;
    while (el && !fiche_pour(index, el.id)) el = el.parentElement ? el.parentElement.closest("[id]") : null;
    return el;
  };
  document.addEventListener("pointerover", (ev) => {
    const el = cible(ev);
    clearTimeout(timer); timer = null;
    if (!el || el === courant) return;
    timer = setTimeout(() => { if (el.isConnected) montrer(el); }, DIDACT_DELAI_MS);
  }, true);
  document.addEventListener("pointerout", (ev) => {
    const el = cible(ev);
    if (el && !(ev.relatedTarget && (el.contains(ev.relatedTarget) || encart.contains(ev.relatedTarget)))) cacher();
  }, true);
  document.addEventListener("pointerdown", (ev) => { if (!encart.contains(ev.target) && !(ev.target.closest && ev.target.closest(".vl-didact-q"))) cacher(); }, true);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && courant) cacher(); }, true);

  // le « ? » à côté de chaque option qui a une fiche — posé après chaque rendu de panneau
  function poserQ() {
    for (const f of index) {
      const el = document.getElementById(f.id);
      if (!el || el.nextElementSibling && el.nextElementSibling.classList && el.nextElementSibling.classList.contains("vl-didact-q")) continue;
      const q = document.createElement("button");
      q.type = "button"; q.className = "vl-didact-q"; q.textContent = "?"; q.setAttribute("aria-label", "Aide : " + f.titre); q.dataset.pour = f.id;
      q.addEventListener("click", (ev) => { ev.stopPropagation(); if (courant === el) cacher(); else montrer(el); });
      el.insertAdjacentElement("afterend", q);
    }
  }
  let planifie = false;
  const obs = new MutationObserver(() => { if (planifie) return; planifie = true; setTimeout(() => { planifie = false; poserQ(); }, 50); });
  const racine = document.querySelector("#panneauCalques") || document.body;
  obs.observe(racine, { childList: true, subtree: true });

  fetch("aide/index.json").then((r) => (r.ok ? r.json() : [])).then((j) => { index = Array.isArray(j) ? j.filter((f) => valider_fiche(f).length === 0) : []; poserQ(); }).catch(() => { index = []; });

  VL.didact = { montrer, cacher, element: encart, get index() { return index; }, set index(v) { index = v; poserQ(); }, poserQ };
}
