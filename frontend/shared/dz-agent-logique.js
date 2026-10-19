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
