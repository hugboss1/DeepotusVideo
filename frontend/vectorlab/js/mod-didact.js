// mod-didact.js — l'aide didactique animée (finitions UI, 20/09/2026) : une
// FICHE par option (titre, phrase « pour un enfant de cinq ans », animation
// à trois temps faite de vraies captures — aide/<module>.<id>.webp), montrée
// au survol long (900 ms, après la bulle courte de mod-infobulle) ou par un
// « ? » posé à côté de l'option. Le panneau lit aide/index.json ; une option
// sans fiche garde la bulle courte. Les fiches sont FABRIQUÉES par le skill
// didacticiel-option (jamais dessinées à la main). Partie pure en tête.
// t126 : Spritelab et Tilelab importent ce module (/vectorlab/js/mod-didact.js) avec LEUR dossier d'aide
// et le corps de page pour racine ; la CSS de l'encart vit dans spritelab.css pour eux.
import { T } from "./mod-i18n.js";
import { bulle_position } from "./mod-infobulle.js";
import { dzi } from "./mod-icones.js";

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

// la vue d'une fiche dans la langue de l'interface : titre_en / phrase_en / fichier_en quand la fiche les porte
export function fiche_langue(f, langue) {
  if (!f || langue !== "en" || !f.titre_en || !f.phrase_en || !f.fichier_en) return f;
  return { ...f, titre: f.titre_en, phrase: f.phrase_en, fichier: f.fichier_en };
}
const langue_page = () => (typeof window !== "undefined" && typeof window.dzLang === "function" ? window.dzLang() : "fr");

export function didact_html(f, aide = "aide/") {
  return `<img class="vl-didact-anim" src="${esc(aide)}${esc(f.fichier)}?v=${esc(f.version)}" width="${DIDACT_LARGEUR}" height="200" alt="">`
    + `<div class="vl-didact-titre">${esc(f.titre)}</div><div class="vl-didact-phrase">${esc(f.phrase)}</div>`;
}

// le dossier d'aide (relatif à la page, / final garanti), son index, et la racine observée pour poser les « ? »
export function didact_reglages({ aide = "aide/", racine = "#panneauCalques" } = {}) {
  const a = String(aide).endsWith("/") ? String(aide) : String(aide) + "/";
  return { aide: a, index: a + "index.json", racine };
}

/* ── DOM ── */
export function initDidact(VL = {}, opts = {}) {
  const R = didact_reglages(opts);
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
    encart.innerHTML = didact_html(f, R.aide);
    encart.classList.remove("hidden");
    const r = el.getBoundingClientRect();
    const p = bulle_position({ x: r.left, y: r.top, w: r.width, h: r.height }, { w: encart.offsetWidth, h: encart.offsetHeight },
                             { w: window.innerWidth, h: window.innerHeight }, 8);
    encart.style.left = p.x + "px"; encart.style.top = p.y + "px";
    return true;
  }
  function cacher() { clearTimeout(timer); timer = null; courant = null; encart.classList.add("hidden"); encart.innerHTML = ""; }

  // l'option sous un élément : son [id] à fiche, ou celle que désigne un « ? »
  const remonter = (e) => {
    if (e && e.classList && e.classList.contains("vl-didact-q")) return document.getElementById(e.dataset.pour);
    let el = e && e.closest ? e.closest("[id]") : null;
    while (el && !fiche_pour(index, el.id)) el = el.parentElement ? el.parentElement.closest("[id]") : null;
    return el;
  };
  // t126 : l'option sous le pointeur par GÉOMÉTRIE — un bouton désactivé du Spritelab / Tilelab porte
  // `pointer-events: none` (.btn:disabled, mesuré sur « Rendre seamless » sans source) : ni pointerover ni
  // elementsFromPoint ne le voient, la fiche ne s'ouvrait qu'au « ? ». On garde l'option dont le rectangle
  // contient le point ET que l'élément du dessus contient ou est (une modale posée dessus l'écarte).
  const parGeometrie = (x, y, dessus) => {
    if (!dessus) return null;
    for (const f of index) {
      const el = document.getElementById(f.id);
      if (!el) continue;
      const r = el.getBoundingClientRect();
      if (r.width && r.height && x >= r.left && x <= r.right && y >= r.top && y <= r.bottom && (dessus === el || dessus.contains(el) || el.contains(dessus))) return el;
    }
    return null;
  };
  let vise = null;
  document.addEventListener("pointermove", (ev) => {
    if (!index.length) return;
    const pile = document.elementsFromPoint(ev.clientX, ev.clientY);
    if (pile.length && encart.contains(pile[0])) return;                 // on lit l'encart : il reste
    let el = null;
    for (const e of pile) { el = remonter(e); if (el) break; }
    if (!el) el = parGeometrie(ev.clientX, ev.clientY, pile[0]);
    if (el === vise) return;
    vise = el; clearTimeout(timer); timer = null;
    if (!el) { if (courant) cacher(); return; }
    if (el === courant) return;
    timer = setTimeout(() => { if (el.isConnected && vise === el) montrer(el); }, DIDACT_DELAI_MS);
  }, true);
  document.addEventListener("pointerdown", (ev) => { if (!encart.contains(ev.target) && !(ev.target.closest && ev.target.closest(".vl-didact-q"))) cacher(); }, true);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && courant) cacher(); }, true);

  // le « ? » à côté de chaque option qui a une fiche — posé après chaque rendu de panneau. t126 : un champ
  // dans un <label> en colonne (Spritelab, Tilelab : « Méthode » puis le select) passait le « ? » à la ligne
  // et décalait la grille — le « ? » rejoint alors la LÉGENDE, enveloppée avec lui dans un <span>
  const deja = (id) => [...document.querySelectorAll(".vl-didact-q")].some((q) => q.dataset.pour === id && q.isConnected);
  function legende(el) {
    const lab = el.parentElement;
    if (!lab || lab.tagName !== "LABEL" || !/^(SELECT|INPUT|TEXTAREA)$/.test(el.tagName)) return null;
    const cs = getComputedStyle(lab);
    if (!((cs.display === "flex" || cs.display === "inline-flex") && cs.flexDirection.startsWith("column")) && cs.display !== "grid") return null;
    const t = [...lab.childNodes].find((n) => n.nodeType === 3 && n.nodeValue.trim());
    if (!t) return null;
    const sp = document.createElement("span");
    sp.className = "vl-didact-legende";
    lab.insertBefore(sp, t); sp.appendChild(t);
    // les petites unités (« px », « % … ») qui suivaient la légende restent avec elle
    while (sp.nextSibling && sp.nextSibling !== el && !(sp.nextSibling.nodeType === 1 && /^(SELECT|INPUT|TEXTAREA)$/.test(sp.nextSibling.tagName))) sp.appendChild(sp.nextSibling);
    return sp;
  }
  function poserQ() {
    for (const f of index) {
      const el = document.getElementById(f.id);
      if (!el || deja(f.id)) continue;
      const q = document.createElement("button");
      q.type = "button"; q.className = "vl-didact-q"; q.innerHTML = dzi("dz-action-aide", 16); q.title = T("vectorlab.didact.aide", { titre: f.titre }); q.setAttribute("aria-label", T("vectorlab.didact.aide", { titre: f.titre })); q.dataset.pour = f.id;
      q.addEventListener("click", (ev) => { ev.stopPropagation(); ev.preventDefault(); const cible = document.getElementById(f.id); if (courant === cible) cacher(); else montrer(cible); });
      const sp = legende(el);
      if (sp) sp.appendChild(q); else el.insertAdjacentElement("afterend", q);
    }
  }
  let planifie = false;
  const obs = new MutationObserver(() => { if (planifie) return; planifie = true; setTimeout(() => { planifie = false; poserQ(); }, 50); });
  const racine = document.querySelector(R.racine) || document.body;
  obs.observe(racine, { childList: true, subtree: true });

  fetch(R.index).then((r) => (r.ok ? r.json() : [])).then((j) => { index = Array.isArray(j) ? j.map((f) => fiche_langue(f, langue_page())).filter((f) => valider_fiche(f).length === 0) : []; poserQ(); }).catch(() => { index = []; });

  VL.didact = { montrer, cacher, element: encart, get index() { return index; }, set index(v) { index = v; poserQ(); }, poserQ };
}
