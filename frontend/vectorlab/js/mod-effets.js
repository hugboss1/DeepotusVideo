// mod-effets.js — l'apparence avancée du lot F, côté PUR : les effets de
// calque compilés en <filter> (ombre, ombre interne, lueur, biseau, contour,
// incrustation — une liste ordonnée, chaînée dans un seul filtre), les 16
// modes de fusion du SVG, les motifs (hachures, points, damier, grille) en
// <pattern>, et le dégradé CONIQUE — absent du SVG — rendu en <pattern> de
// secteurs aux couleurs interpolées. Module FEUILLE.

const _HEX = /^#[0-9A-Fa-f]{6}$/;
const _hex = (v) => { if (!_HEX.test(String(v || ""))) throw new Error(`couleur #RRGGBB attendue : ${v}`); return String(v).toUpperCase(); };
const _n = (v, min, max, ou) => { const x = +v; if (!Number.isFinite(x) || x < min || x > max) throw new Error(`${ou} : entre ${min} et ${max}`); return x; };
const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

/* ── effets ── */
export const EFFETS = [
  { id: "ombre", libelle: "Ombre externe" },
  { id: "ombre_interne", libelle: "Ombre interne" },
  { id: "lueur", libelle: "Lueur externe" },
  { id: "biseau", libelle: "Biseau" },
  { id: "contour", libelle: "Contour" },
  { id: "incrustation", libelle: "Incrustation couleur" },
];
const _DEFAUTS = {
  ombre: { dx: 4, dy: 4, flou: 4, couleur: "#000000", opacite: 0.5 },
  ombre_interne: { dx: 3, dy: 3, flou: 3, couleur: "#000000", opacite: 0.6 },
  lueur: { flou: 6, couleur: "#FFD166", opacite: 0.8 },
  biseau: { profondeur: 3, flou: 2, lumiere: 135, opacite: 0.7 },
  contour: { largeur: 2, couleur: "#1F1512", opacite: 1 },
  incrustation: { couleur: "#9DB4D6", opacite: 1 },
};
export function effet_defaut(type) {
  if (!_DEFAUTS[type]) throw new Error(`effet inconnu : ${type}`);
  return { type, ..._DEFAUTS[type] };
}
export function effets_valider(liste) {
  if (!Array.isArray(liste)) throw new Error("effets : liste attendue");
  for (const e of liste) {
    if (!e || !_DEFAUTS[e.type]) throw new Error(`effet inconnu : ${e && e.type}`);
    if (e.flou !== undefined) _n(e.flou, 0, 200, "flou");
    if (e.dx !== undefined) _n(e.dx, -500, 500, "dx");
    if (e.dy !== undefined) _n(e.dy, -500, 500, "dy");
    if (e.opacite !== undefined) _n(e.opacite, 0, 1, "opacite");
    if (e.largeur !== undefined) _n(e.largeur, 0.1, 100, "largeur");
    if (e.profondeur !== undefined) _n(e.profondeur, 0.1, 100, "profondeur");
    if (e.lumiere !== undefined) _n(e.lumiere, 0, 360, "lumiere");
    if (e.couleur !== undefined) _hex(e.couleur);
  }
  return liste;
}
// chaque effet lit `courant` (le résultat précédent) et produit un nouveau
// résultat ; les effets « derrière » (ombre, lueur, contour) fusionnent le
// courant PAR-DESSUS, les effets « dedans » (ombre interne, biseau,
// incrustation) le remplacent
export function filtre_svg(id, effets) {
  effets_valider(effets);
  if (!effets.length) return "";
  let k = 0, courant = "SourceGraphic";
  const fe = [];
  const nom = () => `r${++k}`;
  for (const e0 of effets) {
    const e = { ..._DEFAUTS[e0.type], ...e0 };
    const op = +e.opacite;
    switch (e.type) {
      case "ombre": {
        const a = nom(), b = nom(), c = nom(), d = nom();
        fe.push(`<feGaussianBlur in="${courant}" stdDeviation="${+e.flou}" result="${a}"/>`,
          `<feOffset in="${a}" dx="${+e.dx}" dy="${+e.dy}" result="${b}"/>`,
          `<feFlood flood-color="${e.couleur}" flood-opacity="${op}" result="${c}"/>`,
          `<feComposite in="${c}" in2="${b}" operator="in" result="${d}"/>`);
        courant = _merge(fe, [d, courant], nom());
        break;
      }
      case "lueur": {
        const a = nom(), b = nom(), c = nom(), d = nom();
        fe.push(`<feMorphology in="${courant}" operator="dilate" radius="${Math.max(0.5, +e.flou / 2)}" result="${a}"/>`,
          `<feGaussianBlur in="${a}" stdDeviation="${+e.flou}" result="${b}"/>`,
          `<feFlood flood-color="${e.couleur}" flood-opacity="${op}" result="${c}"/>`,
          `<feComposite in="${c}" in2="${b}" operator="in" result="${d}"/>`);
        courant = _merge(fe, [d, courant], nom());
        break;
      }
      case "contour": {
        const a = nom(), c = nom(), d = nom();
        fe.push(`<feMorphology in="${courant}" operator="dilate" radius="${+e.largeur}" result="${a}"/>`,
          `<feFlood flood-color="${e.couleur}" flood-opacity="${op}" result="${c}"/>`,
          `<feComposite in="${c}" in2="${a}" operator="in" result="${d}"/>`);
        courant = _merge(fe, [d, courant], nom());
        break;
      }
      case "ombre_interne": {
        const a = nom(), b = nom(), c = nom(), d = nom(), f = nom();
        fe.push(`<feGaussianBlur in="${courant}" stdDeviation="${+e.flou}" result="${a}"/>`,
          `<feOffset in="${a}" dx="${+e.dx}" dy="${+e.dy}" result="${b}"/>`,
          `<feComposite in="${courant}" in2="${b}" operator="out" result="${c}"/>`,
          `<feFlood flood-color="${e.couleur}" flood-opacity="${op}" result="${d}"/>`,
          `<feComposite in="${d}" in2="${c}" operator="in" result="${f}"/>`);
        courant = _merge(fe, [courant, f], nom());
        break;
      }
      case "biseau": {
        const a = nom(), b = nom(), c = nom(), d = nom();
        fe.push(`<feGaussianBlur in="${courant}" stdDeviation="${+e.flou}" result="${a}"/>`,
          `<feSpecularLighting in="${a}" surfaceScale="${+e.profondeur}" specularConstant="0.8" specularExponent="16" lighting-color="#FFFFFF" result="${b}">`
          + `<feDistantLight azimuth="${+e.lumiere}" elevation="45"/></feSpecularLighting>`,
          `<feComposite in="${b}" in2="${courant}" operator="in" result="${c}"/>`,
          `<feComposite in="${courant}" in2="${c}" operator="arithmetic" k1="0" k2="1" k3="${op}" k4="0" result="${d}"/>`);
        courant = d;
        break;
      }
      case "incrustation": {
        const c = nom(), d = nom();
        fe.push(`<feFlood flood-color="${e.couleur}" flood-opacity="${op}" result="${c}"/>`,
          `<feComposite in="${c}" in2="${courant}" operator="in" result="${d}"/>`);
        courant = op >= 1 ? d : _merge(fe, [courant, d], nom());
        break;
      }
    }
  }
  return `<filter id="${esc(id)}" x="-25%" y="-25%" width="150%" height="150%" color-interpolation-filters="sRGB">${fe.join("")}</filter>`;
}
function _merge(fe, entrees, res) {
  fe.push(`<feMerge result="${res}">${entrees.map((i) => `<feMergeNode in="${i}"/>`).join("")}</feMerge>`);
  return res;
}
export const MODES_FUSION = ["normal", "multiply", "screen", "overlay", "darken", "lighten", "color-dodge", "color-burn",
  "hard-light", "soft-light", "difference", "exclusion", "hue", "saturation", "color", "luminosity"];

/* ── motifs ── */
export const MOTIFS = [
  { id: "hachures", libelle: "Hachures" },
  { id: "points", libelle: "Points" },
  { id: "damier", libelle: "Damier" },
  { id: "grille", libelle: "Grille" },
];
const _MOTIF_DEFAUT = { pas: 8, angle: 45, epaisseur: 1, couleur: "#1F1512" };
export function motif_defaut(type) {
  if (!MOTIFS.some((m) => m.id === type)) throw new Error(`motif inconnu : ${type}`);
  return { type, ..._MOTIF_DEFAUT, angle: type === "hachures" ? 45 : 0 };
}
export function motif_valider(m) {
  if (!m || typeof m !== "object" || !MOTIFS.some((x) => x.id === m.type)) throw new Error(`motif inconnu : ${m && m.type}`);
  if (m.pas !== undefined) _n(m.pas, 0.5, 1000, "pas");
  if (m.angle !== undefined) _n(m.angle, -360, 360, "angle");
  if (m.epaisseur !== undefined) _n(m.epaisseur, 0.1, 100, "epaisseur");
  if (m.couleur !== undefined) _hex(m.couleur);
  if (m.fond !== undefined && m.fond !== "none") _hex(m.fond);
  return m;
}
export function motif_svg(id, m0) {
  const m = { ..._MOTIF_DEFAUT, ...motif_valider(m0) };
  const p = +m.pas, c = m.couleur, e = +m.epaisseur;
  const fond = m.fond && m.fond !== "none" ? `<rect x="0" y="0" width="${p}" height="${p}" fill="${m.fond}"/>` : "";
  let corps = "";
  switch (m.type) {
    case "hachures": corps = `<line x1="0" y1="${p / 2}" x2="${p}" y2="${p / 2}" stroke="${c}" stroke-width="${e}"/>`; break;
    case "points": corps = `<circle cx="${p / 2}" cy="${p / 2}" r="${Math.max(0.2, e)}" fill="${c}"/>`; break;
    case "damier": corps = `<rect x="0" y="0" width="${p / 2}" height="${p / 2}" fill="${c}"/><rect x="${p / 2}" y="${p / 2}" width="${p / 2}" height="${p / 2}" fill="${c}"/>`; break;
    case "grille": corps = `<line x1="0" y1="0" x2="${p}" y2="0" stroke="${c}" stroke-width="${e}"/><line x1="0" y1="0" x2="0" y2="${p}" stroke="${c}" stroke-width="${e}"/>`; break;
  }
  const rot = +m.angle ? ` patternTransform="rotate(${+m.angle})"` : "";
  return `<pattern id="${esc(id)}" patternUnits="userSpaceOnUse" width="${p}" height="${p}"${rot}>${fond}${corps}</pattern>`;
}

/* ── dégradé conique ── */
export function couleur_interpoler(a, b, t) {
  const A = _hex(a), B = _hex(b), k = Math.min(1, Math.max(0, +t));
  const c = [0, 2, 4].map((i) => Math.round(parseInt(A.slice(1 + i, 3 + i), 16) * (1 - k) + parseInt(B.slice(1 + i, 3 + i), 16) * k));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("");
}
function _couleurA(stops, t) {
  const s = stops.slice().sort((p, q) => p.t - q.t);
  if (t <= s[0].t) return _hex(s[0].couleur);
  for (let i = 0; i + 1 < s.length; i++) {
    if (t <= s[i + 1].t) { const d = s[i + 1].t - s[i].t; return couleur_interpoler(s[i].couleur, s[i + 1].couleur, d > 0 ? (t - s[i].t) / d : 0); }
  }
  return _hex(s[s.length - 1].couleur);
}
const _r = (v) => Math.round(v * 1000) / 1000;
export function conique_secteurs(g, n = 72) {
  if (!g || !Array.isArray(g.stops) || !g.stops.length) throw new Error("conique : stops requis");
  const cx = +g.cx, cy = +g.cy, r = +g.r * 1.5, a0 = (+g.angle || 0) * Math.PI / 180;   // ×1,5 : les secteurs couvrent le carré
  const out = [];
  for (let i = 0; i < n; i++) {
    const t0 = i / n, t1 = (i + 1) / n;
    const b0 = a0 + t0 * 2 * Math.PI, b1 = a0 + t1 * 2 * Math.PI + 0.002;        // léger recouvrement : pas de fentes
    out.push({ d: `M ${_r(cx)} ${_r(cy)} L ${_r(cx + r * Math.cos(b0))} ${_r(cy + r * Math.sin(b0))} L ${_r(cx + r * Math.cos(b1))} ${_r(cy + r * Math.sin(b1))} Z`,
               couleur: _couleurA(g.stops, t0) });
  }
  return out;
}
export function conique_svg(id, g) {
  const r = +g.r, x = +g.cx - r, y = +g.cy - r;
  const secteurs = conique_secteurs(g, 72);
  return `<pattern id="${esc(id)}" patternUnits="userSpaceOnUse" x="${_r(x)}" y="${_r(y)}" width="${_r(2 * r)}" height="${_r(2 * r)}">`
    + secteurs.map((s) => `<path d="${s.d}" fill="${s.couleur}"/>`).join("") + `</pattern>`;
}
