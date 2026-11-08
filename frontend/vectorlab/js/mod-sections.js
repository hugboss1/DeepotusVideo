// mod-sections.js — t459 : l'état ouvert / replié des sections INTERNES du panneau de droite.
// Les panneaux (Apparence +, Pixel…) reconstruisent leur contenu à chaque rendu (innerHTML) : leurs <details> sans id
// repartaient à l'état écrit dans le gabarit, donc une section ouverte se refermait dès qu'on y faisait un choix.
// Ici, chaque section est reconnue par une CLÉ (le panneau qui la contient + son titre sans compteur) ; le choix de
// l'utilisateur est retenu (localStorage dz_vl_sections) et réappliqué à chaque reconstruction, repérée par un
// MutationObserver : aucun panneau n'a à le savoir. Les sections À ID (une par panneau) restent à mod-panneaux.js.
const CLE = "dz_vl_sections";

// { panneau, texte } -> "panneau:titre" ; le titre perd ses compteurs (« · 2 », « · 20×30 ») et ses nombres
export function cle_section(d) {
  if (!d || !d.panneau) return null;
  const t = String(d.texte || "").split("·")[0].replace(/\d+/g, "#").replace(/\s+/g, " ").trim();
  return t ? `${d.panneau}:${t}` : null;
}
export function sections_lire(json) {
  let lu = null;
  try { lu = json ? JSON.parse(json) : null; } catch (e) { lu = null; }
  const out = {};
  if (lu && typeof lu === "object" && !Array.isArray(lu)) for (const [k, v] of Object.entries(lu)) if (typeof v === "boolean") out[k] = v;
  return out;
}
export function sections_poser(memoire, cle, ouvert) {
  if (!cle) return memoire;
  return { ...memoire, [cle]: !!ouvert };
}
export const sections_serialiser = (m) => JSON.stringify(m);
// une section qui vient d'être (re)construite prend l'état choisi par l'utilisateur, s'il en a choisi un
export function appliquer_section(d, memoire) {
  const k = cle_section(d);
  if (k && k in memoire) d.open = memoire[k];
  return d;
}

// le descripteur d'un <details> du DOM : l'ancêtre à id le plus proche, et le texte de son <summary>
function _decrire(el) {
  let p = el.parentElement;
  while (p && !p.id) p = p.parentElement;
  const s = el.querySelector(":scope > summary");
  return { panneau: p ? p.id : "", texte: s ? s.textContent : "", get open() { return el.open; }, set open(v) { el.open = v; } };
}

export function initSections(VL, racine = typeof document !== "undefined" ? document.querySelector("#panneauCalques") : null) {
  if (!racine || typeof MutationObserver === "undefined") return null;
  let memoire = {};
  try { memoire = sections_lire(localStorage.getItem(CLE)); } catch (e) { /* stockage indisponible */ }
  const lier = (el) => {
    if (el.id || el.dataset.secLie === "1") return;
    el.dataset.secLie = "1";
    const d = _decrire(el);
    appliquer_section(d, memoire);
    // seule une bascule FAITE PAR L'UTILISATEUR (clic ou Entrée / Espace sur le titre) est retenue : le navigateur émet
    // aussi « toggle » quand une section est insérée déjà ouverte, ou quand on lui applique la mémoire
    const titre = el.querySelector(":scope > summary");
    let voulu = false;
    if (titre) {
      titre.addEventListener("click", () => { voulu = true; });
      titre.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") voulu = true; });
    }
    el.addEventListener("toggle", () => {
      if (!voulu) return;
      voulu = false;
      const k = cle_section(_decrire(el));
      if (!k || memoire[k] === el.open) return;
      memoire = sections_poser(memoire, k, el.open);
      try { localStorage.setItem(CLE, sections_serialiser(memoire)); } catch (e) { /* stockage indisponible */ }
    });
  };
  const balayer = (n) => {
    if (n.nodeType !== 1) return;
    if (n.tagName === "DETAILS") lier(n);
    for (const el of n.querySelectorAll("details")) lier(el);
  };
  balayer(racine);
  new MutationObserver((muts) => { for (const m of muts) for (const n of m.addedNodes) balayer(n); })
    .observe(racine, { childList: true, subtree: true });
  if (VL) VL.sectionsEtat = () => ({ ...memoire });   // la preuve
  return true;
}
