// dz-agent-logique.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026) : la logique PURE du tiroir (/shared/dz-agent.js) et du répondeur des labs (/shared/dz-agent-cadre.js).
// Module ES sans DOM ni window à l'import (banc node frontend/shared/qa/agent_logique.test.mjs).
// Servi à l'identique depuis frontend/dist/shared/ (/shared/…).

export const VUES = ["quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library",
  "assets3d", "vectorlab", "photolab", "avatarlive", "settings"];
export const MAX_HISTORIQUE = 10;

const norm = (s) => String(s || "").replace(/\s+/g, " ").trim().toLowerCase();

// candidats : [{texte, titre, visible}] dans l'ordre du document ; rend l'index choisi ou -1
export function choisir(candidats, ancre, lang) {
  const vis = (candidats || []).map((c, i) => ({ ...c, i })).filter((c) => c.visible);
  const t = ancre && ancre.texte ? norm(ancre.texte[lang] || ancre.texte.fr) : "";
  if (!t) return vis.length ? vis[0].i : -1;
  const exact = vis.find((c) => norm(c.texte) === t || norm(c.titre) === t);
  if (exact) return exact.i;
  const debut = vis.find((c) => norm(c.texte).startsWith(t) || norm(c.titre).startsWith(t));
  if (debut) return debut.i;
  const proche = vis.find((c) => norm(c.texte).includes(t) || norm(c.titre).includes(t));
  return proche ? proche.i : -1;
}

// les candidats d'un sélecteur dans `doc` (la page, ou le document d'un lab) : [{noeud, texte, titre, visible}].
// libelle (facultatif, ex. ".dzNavLbl") : sélecteur RELATIF à l'élément trouvé, du sous-élément dont le texte sert
// à la comparaison (le rail : l'icône et le badge ne doivent pas brouiller le libellé). Ne touche qu'à `doc`.
export function candidats(doc, selecteur, libelle) {
  let n = [];
  try { n = Array.from(doc.querySelectorAll(selecteur)); } catch (e) { n = []; }
  return n.map((x) => {
    const r = x.getBoundingClientRect();
    let sous = null;
    try { sous = libelle ? x.querySelector(libelle) : null; } catch (e) { sous = null; }
    return { noeud: x, texte: (sous || x).textContent, titre: x.getAttribute("title") || "", visible: r.width > 0 && r.height > 0 };
  });
}

// un rectangle relevé DANS un cadre intégré → coordonnées de la page
export function composer(cadre, interne) {
  if (!cadre || !interne) return null;
  return { x: cadre.x + interne.x, y: cadre.y + interne.y, w: interne.w, h: interne.h };
}

// Bézier quadratique : le point de contrôle s'écarte perpendiculairement de 30 % de la distance (≤ 160 px)
export function courbe(a, b, t) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const d = Math.hypot(dx, dy);
  if (!d) return { x: a.x, y: a.y };
  const ecart = Math.min(160, d * 0.3);
  const c = { x: (a.x + b.x) / 2 - (dy / d) * ecart, y: (a.y + b.y) / 2 + (dx / d) * ecart };
  const u = 1 - t;
  return { x: u * u * a.x + 2 * u * t * c.x + t * t * b.x, y: u * u * a.y + 2 * u * t * c.y + t * t * b.y };
}

// ce que l'écran doit faire, dans l'ordre, pour une action rendue par /api/agent/demander
export function etapes(action, vueCourante) {
  if (!action) return [];
  if (action.type === "aller") return VUES.includes(action.cible) ? [{ faire: "aller", vue: action.cible }] : [];
  if (action.type === "guide") return /^[a-z0-9-]+$/.test(action.cible || "") ? [{ faire: "guide", chapitre: action.cible }] : [];
  if (action.type === "voir") return [{ faire: "voir" }];
  if (action.type === "point_xy") return Number.isFinite(action.x) && Number.isFinite(action.y) ? [{ faire: "pointer_xy" }] : [];
  if (action.type !== "point") return [];
  const out = [];
  if (action.ecran && !action.partout && VUES.includes(action.ecran) && action.ecran !== vueCourante) out.push({ faire: "aller", vue: action.ecran });
  if (action.reglages) out.push({ faire: "reglages", section: action.reglages });
  else out.push({ faire: "pointer" });
  return out;
}

export function historiqueBorne(h) {
  return (Array.isArray(h) ? h : [])
    .filter((t) => t && (t.role === "user" || t.role === "assistant") && typeof t.texte === "string")
    .slice(-MAX_HISTORIQUE);
}

// ── A5 : la vision en secours (capture de l'onglet, réponse en pixels de la capture) ──
export const COTE_MAX = 1280;

// la taille d'une capture réduite : grand côté ≤ max, proportions gardées, jamais agrandie
export function reduire(l, h, max = COTE_MAX) {
  if (!(l > 0 && h > 0)) return null;
  const k = Math.min(1, max / Math.max(l, h));
  return { l: Math.max(1, Math.round(l * k)), h: Math.max(1, Math.round(h * k)) };
}

// un point rendu en pixels de la capture → coordonnées de la fenêtre (vue : {l, h} au moment de la capture), borné
export function versEcran(a, vue) {
  if (!a || !vue || !(a.largeur > 0 && a.hauteur > 0) || !Number.isFinite(a.x) || !Number.isFinite(a.y)) return null;
  const x = Math.min(Math.max(0, a.x), a.largeur) * (vue.l / a.largeur);
  const y = Math.min(Math.max(0, a.y), a.hauteur) * (vue.h / a.hauteur);
  return { x: Math.round(x), y: Math.round(y) };
}

// l'image vient-elle de CET onglet ? même rapport largeur / hauteur que la fenêtre, à tol près
export function memeOnglet(l, h, vue, tol = 0.06) {
  if (!(l > 0 && h > 0) || !vue || !(vue.l > 0 && vue.h > 0)) return false;
  const r = vue.l / vue.h;
  return Math.abs(l / h - r) <= tol * r;
}

// l'élément à montrer sous un point : le plus proche ancêtre cliquable (6 niveaux au plus), sinon null
const CLIQUABLES = ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA", "LABEL", "SUMMARY"];
const ROLES = ["button", "tab", "menuitem", "link", "checkbox", "switch", "option"];
export function cliquable(n) {
  for (let x = n, i = 0; x && i < 6; x = x.parentElement, i++) {
    const role = x.getAttribute ? x.getAttribute("role") : null;
    if (CLIQUABLES.includes(x.tagName) || ROLES.includes(role)) return x;
  }
  return null;
}

// un montant en dollars, 4 décimales, virgule en français
export function prix(usd, lang) {
  const t = (Number(usd) || 0).toFixed(4);
  return lang === "en" ? t : t.replace(".", ",");
}

// C4 (spec 2026-10-19-agent-catalogue-design.md § 4) : les éléments visibles de l'écran ouvert, envoyés avec la
// question ; LIBELLÉS seulement, jamais le contenu de l'utilisateur, bornés :
// - un champ (input, textarea, select, contenteditable) ne donne jamais son texte : son infobulle, aria-label ou
//   placeholder seulement ;
// - seul un contrôle (button, a[href], role tab / menuitem / button) donne un texte : la première ligne non vide de
//   innerText (« Quick » et non « QuickGénérateurs en un clic »), écartée au-delà de 40 caractères (c'est alors du
//   contenu, l'aperçu d'un bloc par ex.) ;
// - toute zone marquée data-dz-agent-ignorer (grille de fichiers…) est exclue. Les nav sont GARDÉS ici (menus et
//   outils des labs) : la SPA exclut son rail par le prédicat exclure (/shared/dz-agent.js).
export const MAX_VISIBLES = 120;
const MAX_TEXTE = 80;
const MAX_LIBELLE = 40;
const SEL_VISIBLES = 'button, [role="tab"], [role="menuitem"], [role="button"], a[href], [title], [aria-label]';
const ROLES_CONTROLE = new Set(["tab", "menuitem", "button"]);
const court = (s) => String(s || "").replace(/\s+/g, " ").trim().slice(0, MAX_TEXTE);
const tag = (x) => String(x.tagName || "").toUpperCase();
function estChamp(x) {
  const g = tag(x), ce = x.getAttribute("contenteditable");
  return g === "INPUT" || g === "TEXTAREA" || g === "SELECT" || x.isContentEditable === true
    || (ce != null && ce !== "false");
}
function estControle(x) {
  const g = tag(x);
  return g === "BUTTON" || (g === "A" && x.getAttribute("href") != null) || ROLES_CONTROLE.has(x.getAttribute("role"));
}
function libelle(x) {
  if (estChamp(x) || !estControle(x)) return "";
  const brut = typeof x.innerText === "string" ? x.innerText : String(x.textContent || "");
  const ligne = brut.split("\n").map((l) => l.replace(/\s+/g, " ").trim()).find((l) => l) || "";
  return ligne.length > MAX_LIBELLE ? "" : ligne;
}

export function releverVisibles(doc, exclure = () => false, max = MAX_VISIBLES) {
  let noeuds = [];
  try { noeuds = Array.from(doc.querySelectorAll(SEL_VISIBLES)); } catch (e) { return []; }
  // la fenêtre : lue sur doc.defaultView s'il existe (un faux document sans vue n'est pas filtré)
  const vue = doc && doc.defaultView ? doc.defaultView : null;
  const largeur = vue && vue.innerWidth > 0 ? vue.innerWidth : Infinity;
  const hauteur = vue && vue.innerHeight > 0 ? vue.innerHeight : Infinity;
  const styleDe = vue && typeof vue.getComputedStyle === "function" ? (x) => vue.getComputedStyle(x) : null;
  const out = [], vus = new Set();
  for (const x of noeuds) {
    if (out.length >= max) break;
    try {
      if (exclure(x)) continue;
      // une zone marquée data-dz-agent-ignorer (grille de fichiers…) n'est jamais relevée
      if (typeof x.closest === "function" && x.closest("[data-dz-agent-ignorer]")) continue;
      const r = x.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0)) continue;
      if (!(r.bottom > 0 && r.top < hauteur && r.right > 0 && r.left < largeur)) continue;   // hors fenêtre
      if (styleDe && styleDe(x).visibility === "hidden") continue;
      const t = libelle(x);
      const i = court(x.getAttribute("title") || x.getAttribute("aria-label") || x.getAttribute("placeholder") || "");
      if (!t && !i) continue;
      const k = t + "\u0001" + i;
      if (vus.has(k)) continue;
      vus.add(k);
      out.push({ t, i });
    } catch (e) { /* un nœud illisible est sauté, le relevé continue */ }
  }
  return out;
}

// t260 : la place de la bulle « Demander ». « barre » (défaut) = ancrée dans la barre du haut de la coque ;
// « flottant » = déplaçable, position {x, y} (coin haut-gauche, px) gardée dans localStorage.
export const PLACES = ["barre", "flottant"];
export const MARGE_BULLE = 8;
export function placeLue(v) { return PLACES.includes(v) ? v : "barre"; }
export function positionLue(json) {
  try {
    const p = JSON.parse(json);
    return p && Number.isFinite(p.x) && Number.isFinite(p.y) ? { x: p.x, y: p.y } : null;
  } catch (e) { return null; }
}
// tient la bulle (taille {l, h}) dans la fenêtre {l, h}, à MARGE_BULLE px des bords ; trop grande : coin haut-gauche
export function borner(pos, taille, fenetre, marge = MARGE_BULLE) {
  const lim = (v, max) => Math.max(marge, Math.min(v, Math.max(marge, max - marge)));
  return { x: lim(pos.x, fenetre.l - taille.l), y: lim(pos.y, fenetre.h - taille.h) };
}
// un appui qui bouge de plus de 4 px est un déplacement, pas un clic
export function glisse(a, b, seuil = 4) { return Math.hypot(b.x - a.x, b.y - a.y) > seuil; }
