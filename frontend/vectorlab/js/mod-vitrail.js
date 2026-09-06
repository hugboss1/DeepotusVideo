// mod-vitrail.js — le mode vitrail, refondu sur le handoff « Vectorlab
// Vitrail » du 06/09/2026 (design.dc.html du projet claude.design, lu en
// zip). Ce qui reste de la phase 5 : la FICHE ÉPINGLÉE (GET
// /api/vector/vitrail — style_vitrail.json, copie du skill), `generer_baie`
// et les trois presets (iris, rayons, halo), tous conservés tels quels ;
// les bancs qui les épinglent restent verts.
// Ce que le handoff apporte, MESURÉ contre l'existant :
//   - les panneaux se TRACENT AU GLISSER sur la page (fini les trois
//     prompt() de « Baie… ») — quatre motifs : arc, rosette, grille
//     losangée, plomb libre ;
//   - un panneau est UN groupe porteur de ses réglages (`vitrail: {…}`),
//     donc RETOUCHABLE après coup : gamme, plomb, joints, tirage —
//     `parserDoc` ne vérifie que la structure, le champ voyage avec le
//     document (mesuré) ;
//   - des GAMMES de verre (fiche + quatre du handoff + perso), six teintes
//     éditables (curseurs T/S/V de mod-couleur — le handoff propose HSL,
//     le dépôt a déjà HSV : écart déclaré) et une banque de verres nommés ;
//   - une rangée IA (POST /api/vector/illustration, appel LLM payant DIT
//     dans l'infobulle) qui pose des masses de verre vectorielles.
// Écarts déclarés vis-à-vis du handoff : pas d'outil « scale » (la
// sélection porte déjà poignées et rotation), pas d'outil de rail « ai »
// (la rangée du panneau suffit), l'outil mesure est CONSERVÉ, la
// bibliothèque et le bandeau applicatif de la maquette ne sont pas repris
// (ils existent, autrement, dans l'application).
import { op_ajouter, op_calque_ajouter, op_calque_reordonner,
         op_calque_renommer, op_redimensionner, idLibre, chemin_parser }
  from "./mod-doc.js";
import { hexVersRgb, rgbVersHex, rgbVersHsl, hslVersRgb }
  from "./mod-couleur.js";

const nb = (v) => Math.round(v * 100) / 100;

/* ═══════════ le hasard DÉTERMINISTE des verres (pur) ═══════════
   Le hash entier du handoff (imul/xor) : même graine → même vitrail,
   « nouveau tirage » = une autre graine. Aucun Math.random ici. */
export function hash01(n) {
  let x = Math.imul((n | 0) ^ 0x9e3779b9, 0x85ebca6b);
  x ^= x >>> 13; x = Math.imul(x, 0xc2b2ae35); x ^= x >>> 16;
  return (x >>> 0) / 4294967296;
}
export function teinteDe(teintes, i, graine) {
  return teintes[Math.floor(hash01(i * 31 + graine * 7919) * teintes.length)
                 % teintes.length];
}

/* ═══════════ gammes et banque du handoff (données pures) ═══════════
   La gamme « fiche » est injectée au runtime depuis l'endpoint (et depuis
   le JSON par le banc) : elle n'est PAS recopiée ici. */
export const GAMMES = {
  chartres: { titre: "Chartres",
    teintes: ["#1e3f7d", "#8c2331", "#c9a33f", "#e6e1cf", "#2a5f8c", "#6d1f2a"] },
  or: { titre: "Or & ambre",
    teintes: ["#c9922e", "#e2bb57", "#8a5a1e", "#f2e2b0", "#a3701f", "#d9a63c"] },
  foret: { titre: "Forêt",
    teintes: ["#1e5a43", "#2f7a52", "#8fae5c", "#d5ddc0", "#3d6f3a", "#12463a"] },
  aube: { titre: "Aube",
    teintes: ["#5a3f7a", "#8a4a72", "#c46f8a", "#e4c1cd", "#3d3560", "#7a4f96"] },
};
export const BANQUE_VERRES = [
  ["#1e56c8", "Bleu de cobalt"], ["#c0202f", "Rouge rubis"],
  ["#1f7a3a", "Vert émeraude"], ["#d8b12a", "Jaune d'argent"],
  ["#7b3f9d", "Pourpre"], ["#0d2b6b", "Bleu de nuit"],
  ["#7fb2e5", "Bleu ciel"], ["#8c2331", "Grenat"],
  ["#e08a3c", "Ambre"], ["#0f5c46", "Vert bouteille"],
  ["#c9d8a8", "Vert d'eau"], ["#e8e2d0", "Verre opalin"],
  ["#3a3f46", "Gris fumé"],
];

/* ═══════════ les quatre générateurs de panneau (purs) ═══════════
   Tous prennent (bbox, o) — o : {colonnes, rangees, plomb, arrondi,
   teintes, couleurPlomb, graine} — et rendent une liste d'objets du
   document (coordonnées absolues, dans la bbox). Les pièces de verre sont
   des paths fermés M/L/C (jamais de A : chemin_parser, les nœuds et les
   booléens ne lisent que M L C Q Z) ; le CADRE est un tracé fond none
   d'épaisseur plomb×1.8, comme generer_baie le fait déjà. */
const KAPPA = 0.5523;
function stVerre(o, fond) {
  return { fond, contour: o.couleurPlomb, epaisseur: o.plomb,
           joint: o.arrondi ? "round" : "miter" };
}
function stCadre(o) {
  return { fond: "none", contour: o.couleurPlomb,
           epaisseur: nb(o.plomb * 1.8),
           joint: o.arrondi ? "round" : "miter" };
}
const fmt = (pts) => "M " + pts.map((p) => nb(p[0]) + " " + nb(p[1]))
  .join(" L ") + " Z";
const ptA = (cx, cy, r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
function arcPts(cx, cy, r, a0, a1, n = 5) {
  const out = [];
  for (let s = 0; s <= n; s++) out.push(ptA(cx, cy, r, a0 + (a1 - a0) * s / n));
  return out;
}

// ── arc plein cintre : lancettes du haut en deux couronnes + grille ──
export function generer_arc(b, o) {
  const out = [], archH = Math.min(b.w * 0.55, b.h * 0.5);
  const ys = b.y + archH, cx = b.x + b.w / 2, R = b.w / 2;
  const quartiers = Math.max(3, o.colonnes + 1), rIn = R * 0.5;
  let i = 0;
  for (let k = 0; k < quartiers; k++) {
    const a0 = Math.PI + k * Math.PI / quartiers;
    const a1 = Math.PI + (k + 1) * Math.PI / quartiers;
    out.push({ type: "path",
      d: fmt([...arcPts(cx, ys, R, a0, a1), ...arcPts(cx, ys, rIn, a1, a0)]),
      style: stVerre(o, teinteDe(o.teintes, i++, o.graine)) });
    out.push({ type: "path",
      d: fmt([[cx, ys], ...arcPts(cx, ys, rIn, a0, a1)]),
      style: stVerre(o, teinteDe(o.teintes, i++, o.graine + 3)) });
  }
  const bh = b.y + b.h - ys, cw = b.w / o.colonnes, rh = bh / o.rangees;
  for (let r = 0; r < o.rangees; r++) {
    for (let c = 0; c < o.colonnes; c++) {
      const x = b.x + c * cw, y = ys + r * rh;
      out.push({ type: "rect", x: nb(x), y: nb(y), w: nb(cw), h: nb(rh),
                 style: stVerre(o, teinteDe(o.teintes, i++, o.graine)) });
    }
  }
  // cadre : demi-ellipse en DEUX cubiques (kappa) + flancs + bas
  const ky = KAPPA * archH, kx = KAPPA * R, apex = b.y;
  out.push({ type: "path",
    d: `M ${nb(b.x)} ${nb(ys)}`
      + ` C ${nb(b.x)} ${nb(ys - ky)} ${nb(cx - kx)} ${nb(apex)}`
      + ` ${nb(cx)} ${nb(apex)}`
      + ` C ${nb(cx + kx)} ${nb(apex)} ${nb(b.x + b.w)} ${nb(ys - ky)}`
      + ` ${nb(b.x + b.w)} ${nb(ys)}`
      + ` L ${nb(b.x + b.w)} ${nb(b.y + b.h)}`
      + ` L ${nb(b.x)} ${nb(b.y + b.h)} Z`,
    style: stCadre(o) });
  return out;
}

// ── rosette : `rangees` couronnes de 2n secteurs + n pétales + moyeu ──
export function generer_rosette(b, o) {
  const out = [], cx = b.x + b.w / 2, cy = b.y + b.h / 2;
  const R = Math.min(b.w, b.h) / 2, n = Math.max(6, o.colonnes * 2);
  const anneaux = Math.max(1, Math.min(4, o.rangees));
  const rHub = R * 0.17, rPet = R * 0.74;
  let i = 0;
  for (let a = 0; a < anneaux; a++) {
    const r0 = rPet + (R - rPet) * a / anneaux;
    const r1 = rPet + (R - rPet) * (a + 1) / anneaux;
    for (let k = 0; k < n * 2; k++) {
      const a0 = k * 2 * Math.PI / (n * 2), a1 = (k + 1) * 2 * Math.PI / (n * 2);
      out.push({ type: "path",
        d: fmt([...arcPts(cx, cy, r1, a0, a1), ...arcPts(cx, cy, r0, a1, a0)]),
        style: stVerre(o, teinteDe(o.teintes, i++, o.graine + 501 + a)) });
    }
  }
  for (let k = 0; k < n; k++) {
    const a0 = k * 2 * Math.PI / n, a1 = (k + 1) * 2 * Math.PI / n;
    out.push({ type: "path",
      d: fmt([...arcPts(cx, cy, rPet, a0 + 0.02, a1 - 0.02),
              ptA(cx, cy, rHub, (a0 + a1) / 2)]),
      style: stVerre(o, teinteDe(o.teintes, i++, o.graine)) });
  }
  out.push({ type: "ellipse", cx: nb(cx), cy: nb(cy),
             rx: nb(rHub * 1.5), ry: nb(rHub * 1.5),
             style: stVerre(o, o.teintes[3 % o.teintes.length]) });
  out.push({ type: "ellipse", cx: nb(cx), cy: nb(cy), rx: nb(R), ry: nb(R),
             style: stCadre(o) });
  return out;
}

// ── grille losangée : fond plombé + losanges en quinconce, clampés ──
export function generer_grille(b, o) {
  const out = [];
  out.push({ type: "rect", x: nb(b.x), y: nb(b.y), w: nb(b.w), h: nb(b.h),
             style: { fond: o.couleurPlomb } });
  const cw = b.w / o.colonnes, rh = b.h / o.rangees;
  const cl = (q) => [Math.max(b.x, Math.min(b.x + b.w, q[0])),
                     Math.max(b.y, Math.min(b.y + b.h, q[1]))];
  let i = 0;
  for (let r = 0; r <= o.rangees; r++) {
    for (let c = 0; c <= o.colonnes; c++) {
      const cx = b.x + c * cw + (r % 2 ? cw / 2 : 0), cy = b.y + r * rh;
      out.push({ type: "path",
        d: fmt([[cx, cy - rh / 2], [cx + cw / 2, cy],
                [cx, cy + rh / 2], [cx - cw / 2, cy]].map(cl)),
        style: stVerre(o, teinteDe(o.teintes, i++, o.graine)) });
    }
  }
  out.push({ type: "rect", x: nb(b.x), y: nb(b.y), w: nb(b.w), h: nb(b.h),
             style: stCadre(o) });
  return out;
}

// ── plomb libre : grille de sommets chahutée (déterministe) ──
export function generer_plomb_libre(b, o) {
  const out = [], nc = o.colonnes + 1, nr = o.rangees;
  const cw = b.w / nc, rh = b.h / nr, v = [];
  for (let r = 0; r <= nr; r++) {
    v[r] = [];
    for (let c = 0; c <= nc; c++) {
      const jx = (hash01(r * 97 + c * 31 + o.graine) - 0.5) * cw * 0.92;
      const jy = (hash01(r * 57 + c * 131 + o.graine * 3) - 0.5) * rh * 0.92;
      const dec = r % 2 ? cw * 0.34 : 0;
      v[r][c] = [b.x + c * cw + (c === 0 || c === nc ? 0 : jx + dec),
                 b.y + r * rh + (r === 0 || r === nr ? 0 : jy)];
    }
  }
  let i = 0;
  for (let r = 0; r < nr; r++) {
    for (let c = 0; c < nc; c++) {
      out.push({ type: "path",
        d: fmt([v[r][c], v[r][c + 1], v[r + 1][c + 1], v[r + 1][c]]),
        style: stVerre(o, teinteDe(o.teintes, i++, o.graine)) });
    }
  }
  out.push({ type: "rect", x: nb(b.x), y: nb(b.y), w: nb(b.w), h: nb(b.h),
             style: stCadre(o) });
  return out;
}

export const MOTIFS = {
  arc: { titre: "Baie à arc", libelles: ["travées", "registres"],
         gen: generer_arc },
  rosette: { titre: "Rosette", libelles: ["pétales", "couronnes"],
             gen: generer_rosette },
  grille: { titre: "Grille losangée", libelles: ["colonnes", "rangées"],
            gen: generer_grille },
  plomb: { titre: "Plomb libre", libelles: ["colonnes", "rangées"],
           gen: generer_plomb_libre },
};

/* ═══════════ le panneau = UN groupe retouchable (pur) ═══════════ */
export function construire_panneau(motif, bbox, o) {
  const m = MOTIFS[motif];
  if (!m) throw new Error(`motif inconnu: ${motif}`);
  const enfants = m.gen(bbox, o);
  return { type: "groupe", style: {}, name: m.titre,
           vitrail: { motif, colonnes: o.colonnes, rangees: o.rangees,
                      plomb: o.plomb, arrondi: !!o.arrondi, gamme: o.gamme,
                      teintes: [...o.teintes], couleurPlomb: o.couleurPlomb,
                      graine: o.graine, bbox: { ...bbox } },
           enfants };
}

// bbox recalculée depuis les ENFANTS (pas depuis la méta, qui devient
// fausse dès qu'op_deplacer a décalé les coordonnées) — rect, ellipse,
// et les points des paths via chemin_parser (points de contrôle compris :
// pour nos cubiques kappa ils restent dans l'enveloppe).
export function bbox_enfants(enfants) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const pt = (x, y) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y);
                         x1 = Math.max(x1, x); y1 = Math.max(y1, y); };
  for (const e of enfants || []) {
    if (e.type === "rect") { pt(e.x, e.y); pt(e.x + e.w, e.y + e.h); }
    else if (e.type === "ellipse") {
      pt(e.cx - e.rx, e.cy - e.ry); pt(e.cx + e.rx, e.cy + e.ry);
    } else if (e.type === "path") {
      for (const s of chemin_parser(e.d)) {
        for (let k = 0; k + 1 < s.p.length; k += 2) pt(s.p[k], s.p[k + 1]);
      }
    }
  }
  if (!isFinite(x0)) throw new Error("panneau sans géométrie mesurable");
  return { x: nb(x0), y: nb(y0), w: nb(x1 - x0), h: nb(y1 - y0) };
}

export function trouver_panneau(doc, id) {
  for (const c of doc.calques) {
    const g = c.objets.find((x) => x.id === id);
    if (g) return (g.type === "groupe" && g.vitrail) ? g : null;
  }
  return null;
}

// COMMANDE : regénère le panneau `id` avec `patch` sur ses réglages, à
// l'endroit où il est AUJOURD'HUI (bbox des enfants). L'id du groupe et
// sa place dans l'ordre de peinture ne bougent pas.
export function op_panneau_regen(doc, id, patch = {}) {
  const g = trouver_panneau(doc, id);
  if (!g) throw new Error(`${id}: pas un panneau de verre`);
  const bbox = bbox_enfants(g.enfants);
  const o = { ...g.vitrail, ...patch, bbox };
  const neuf = construire_panneau(o.motif, bbox, o);
  g.vitrail = neuf.vitrail;
  g.enfants = neuf.enfants.map((e, k) => ({ ...e, id: `${id}p${k}` }));
  return id;
}

// COMMANDE : insère un panneau tracé au glisser — ids posés ici pour que
// les enfants soient adressables (data-objet) sans collision.
export function op_panneau_inserer(doc, calqueId, motif, bbox, o) {
  const id = idLibre(doc);
  const g = construire_panneau(motif, bbox, o);
  g.enfants = g.enfants.map((e, k) => ({ ...e, id: `${id}p${k}` }));
  return op_ajouter(doc, calqueId, { ...g, id });
}

/* ═══════════ générateur de baie HISTORIQUE (phase 5, conservé) ═══════ */
export function generer_baie(famille, params = {}) {
  const ancres = Object.values(famille.palette.ancres);
  const plomb = Object.values(famille.palette.contour)[0];
  const [bLo, bHi] = famille.bornes.part_bordure_ornementale;
  const {
    w = 640, h = 960, forme = "ogive", colonnes = 2, rangees = 3,
    marge = 24, epaisseurCadre = 18, epaisseurReseau = 10,
    epaisseurBordure = 8,
  } = params;
  const bordure = Math.max(bLo, Math.min(bHi, params.bordure ?? 0.08));
  const x0 = marge, x1 = w - marge, y0 = marge, y1 = h - marge;
  const W = x1 - x0, H = y1 - y0;
  const d = bordure * Math.min(W, H);
  const ys = forme === "ogive" ? y0 + 0.35 * H : y0 + d;
  const xi0 = x0 + d, xi1 = x1 - d, yi1 = y1 - d;

  // contour ogival : côtés + bas + deux arcs cubiques vers l'apex
  const ogiveD = (gx0, gx1, gys, gy1, apexY) => {
    const gcx = (gx0 + gx1) / 2, tw = gx1 - gx0, monte = gys - apexY;
    return `M ${nb(gx0)} ${nb(gys)} L ${nb(gx0)} ${nb(gy1)}`
      + ` L ${nb(gx1)} ${nb(gy1)} L ${nb(gx1)} ${nb(gys)}`
      + ` C ${nb(gx1)} ${nb(gys - 0.6 * monte)}`
      + ` ${nb(gcx + 0.25 * tw)} ${nb(apexY)} ${nb(gcx)} ${nb(apexY)}`
      + ` C ${nb(gcx - 0.25 * tw)} ${nb(apexY)}`
      + ` ${nb(gx0)} ${nb(gys - 0.6 * monte)} ${nb(gx0)} ${nb(gys)} Z`;
  };

  const verre = [];
  const cw = (xi1 - xi0) / colonnes, rh = (yi1 - ys) / rangees;
  for (let j = 0; j < rangees; j++) {
    for (let i = 0; i < colonnes; i++) {
      verre.push({ type: "rect", x: nb(xi0 + i * cw), y: nb(ys + j * rh),
                   w: nb(cw), h: nb(rh),
                   style: { fond: ancres[(j * colonnes + i) % ancres.length] } });
    }
  }
  if (forme === "ogive") {
    const gcx = (xi0 + xi1) / 2, tw = xi1 - xi0;
    const apexI = y0 + d, monteI = ys - apexI;
    verre.push({ type: "path",
      d: `M ${nb(xi0)} ${nb(ys)}`
        + ` C ${nb(xi0)} ${nb(ys - 0.6 * monteI)}`
        + ` ${nb(gcx - 0.25 * tw)} ${nb(apexI)} ${nb(gcx)} ${nb(apexI)}`
        + ` C ${nb(gcx + 0.25 * tw)} ${nb(apexI)}`
        + ` ${nb(xi1)} ${nb(ys - 0.6 * monteI)} ${nb(xi1)} ${nb(ys)} Z`,
      style: { fond: ancres[(rangees * colonnes) % ancres.length] } });
  }

  const contours = [];
  const sPlomb = (ep) => ({ fond: "none", contour: plomb, epaisseur: ep });
  if (forme === "ogive") {
    contours.push({ type: "path", d: ogiveD(x0, x1, ys, y1, y0),
                    style: sPlomb(epaisseurCadre) });
    contours.push({ type: "path", d: ogiveD(xi0, xi1, ys, yi1, y0 + d),
                    style: sPlomb(epaisseurBordure) });
  } else {
    contours.push({ type: "rect", x: x0, y: y0, w: W, h: H,
                    style: sPlomb(epaisseurCadre) });
    contours.push({ type: "rect", x: nb(xi0), y: nb(y0 + d),
                    w: nb(xi1 - xi0), h: nb(yi1 - (y0 + d)),
                    style: sPlomb(epaisseurBordure) });
  }
  for (let i = 1; i < colonnes; i++) {
    const mx = nb(xi0 + i * cw);
    contours.push({ type: "path", d: `M ${mx} ${nb(ys)} L ${mx} ${nb(yi1)}`,
                    style: sPlomb(epaisseurReseau) });
  }
  for (let j = 1; j < rangees; j++) {
    const my = nb(ys + j * rh);
    contours.push({ type: "path",
                    d: `M ${nb(xi0)} ${my} L ${nb(xi1)} ${my}`,
                    style: sPlomb(epaisseurReseau) });
  }
  return { verre, contours,
           params: { forme, colonnes, rangees, bordure, d: nb(d) } };
}

/* ═══════════ presets de motifs (phase 5, conservés) ═══════════ */
export function motif_iris(famille, cx, cy, s = 1) {
  const a = famille.palette.ancres;
  const X = (v) => nb(cx + v * s), Y = (v) => nb(cy + v * s);
  const p = (dd, fond) => ({ type: "path", d: dd, style: { fond } });
  return { type: "groupe", style: {}, enfants: [
    p(`M ${X(0)} ${Y(0)} C ${X(-18)} ${Y(-28)} ${X(-8)} ${Y(-52)}`
      + ` ${X(0)} ${Y(-56)} C ${X(8)} ${Y(-52)} ${X(18)} ${Y(-28)}`
      + ` ${X(0)} ${Y(0)} Z`, a.violet_profond),
    p(`M ${X(0)} ${Y(0)} C ${X(-30)} ${Y(-6)} ${X(-46)} ${Y(-24)}`
      + ` ${X(-44)} ${Y(-38)} C ${X(-26)} ${Y(-34)} ${X(-8)} ${Y(-18)}`
      + ` ${X(0)} ${Y(0)} Z`, a.violet_profond),
    p(`M ${X(0)} ${Y(0)} C ${X(30)} ${Y(-6)} ${X(46)} ${Y(-24)}`
      + ` ${X(44)} ${Y(-38)} C ${X(26)} ${Y(-34)} ${X(8)} ${Y(-18)}`
      + ` ${X(0)} ${Y(0)} Z`, a.violet_profond),
    p(`M ${X(-3)} ${Y(0)} L ${X(3)} ${Y(0)} L ${X(2)} ${Y(34)}`
      + ` L ${X(-2)} ${Y(34)} Z`, a.emeraude),
  ] };
}

export function motif_rayons(famille, cx, cy, r = 80, n = 8) {
  const ambre = famille.palette.ancres.ambre_dore;
  const enfants = [];
  for (let k = 0; k < n; k++) {
    const t = -Math.PI / 2 + 2 * Math.PI * k / n;
    enfants.push({ type: "path",
      d: `M ${nb(cx)} ${nb(cy)} L ${nb(cx + r * Math.cos(t))}`
        + ` ${nb(cy + r * Math.sin(t))}`,
      style: { fond: "none", contour: ambre, epaisseur: 6 } });
  }
  return { type: "groupe", style: {}, enfants };
}

export function motif_halo(famille, cx, cy, r = 60) {
  const ambre = famille.palette.ancres.ambre_dore;
  return { type: "groupe", style: {}, enfants: [
    { type: "ellipse", cx: nb(cx), cy: nb(cy), rx: nb(r), ry: nb(r),
      style: { fond: "none", contour: ambre, epaisseur: 6 } },
    { type: "ellipse", cx: nb(cx), cy: nb(cy), rx: nb(r * 1.25),
      ry: nb(r * 1.25),
      style: { fond: "none", contour: ambre, epaisseur: 3 } },
  ] };
}

/* ═══════════ l'UI : le panneau Vitrail du handoff ═══════════ */
export function initVitrail(VL) {
  const { $, etat } = VL;
  let famille = null;

  // réglages du PROCHAIN panneau — la gamme perso persiste (léger, local)
  const regl = { motif: "arc", colonnes: 4, rangees: 6, plomb: 6,
                 arrondi: false, gamme: "chartres", slot: null,
                 perso: null, iaBusy: false, iaMsg: "", iaErr: false };
  try {
    const p = JSON.parse(localStorage.getItem("dz_vl_teintes") || "null");
    if (Array.isArray(p) && p.length === 6) regl.perso = p;
  } catch (e) { /* stockage indisponible */ }
  if (!regl.perso) regl.perso = [...GAMMES.chartres.teintes];

  function gammes() {
    const out = {};
    if (famille) {
      out.fiche = { titre: "Fiche épinglée",
                    teintes: Object.values(famille.palette.ancres) };
    }
    Object.assign(out, GAMMES);
    out.perso = { titre: "Gamme personnalisée", teintes: regl.perso };
    return out;
  }
  function couleurPlomb() {
    return famille ? Object.values(famille.palette.contour)[0] : "#1F1512";
  }
  function panneauSel() {
    if (etat.selection.length !== 1 || !etat.doc) return null;
    return trouver_panneau(etat.doc, etat.selection[0]);
  }
  function optsCourants(g) {
    const src = g ? g.vitrail : regl;
    const table = gammes();
    const teintes = src.gamme === "perso" ? regl.perso
      : (table[src.gamme] || table.chartres || GAMMES.chartres).teintes;
    return { colonnes: src.colonnes, rangees: src.rangees,
             plomb: src.plomb, arrondi: !!src.arrondi, gamme: src.gamme,
             teintes: g && src.gamme === "perso" ? src.teintes : teintes,
             couleurPlomb: couleurPlomb(),
             graine: g ? src.graine : (etat.doc ? idLibre(etat.doc).length
                                       + Date.now() % 9973 : 41) };
  }
  function retoucher(patch) {
    const g = panneauSel();
    if (g) {
      // les teintes suivent la gamme demandée au moment du geste
      const o = optsCourants(null);
      VL.executer(op_panneau_regen, g.id,
                  { ...patch, teintes: patch.gamme || patch.teintes
                    ? (patch.teintes || (gammes()[patch.gamme]
                                         || GAMMES.chartres).teintes)
                    : g.vitrail.teintes, couleurPlomb: o.couleurPlomb });
    }
    rendrePanneau();
  }

  /* ── le tracé au glisser : mod-tools appelle ceci au pointerup ── */
  VL.vitrailInserer = (bbox) => {
    if (!etat.doc || bbox.w < 24 || bbox.h < 24) {
      VL.toast("panneau trop petit — glissez une zone d'au moins 24 px");
      return;
    }
    const o = optsCourants(null);
    const id = VL.executer(op_panneau_inserer, etat.calqueActif,
                           regl.motif, bbox, o);
    if (id) {
      VL.setOutil("select");
      VL.setSelection([id]);
      VL.toast(`${MOTIFS[regl.motif].titre} posée — le panneau Vitrail`
               + " retouche le panneau sélectionné (gamme, plomb, tirage)");
    }
  };

  /* §8.5 du handoff : le bouton « Poser une baie d'exemple » du panneau
     Calques vide — la bbox reprend les proportions de la démo du
     prototype (110,90,384,600 sur 604×831). */
  VL.vitrailExemple = () => {
    if (!etat.doc) return;
    const W = etat.doc.taille.w, H = etat.doc.taille.h;
    const bbox = { x: Math.round(W * 0.18), y: Math.round(H * 0.11),
                   w: Math.round(W * 0.64), h: Math.round(H * 0.72) };
    const id = VL.executer(op_panneau_inserer, etat.calqueActif,
                           "arc", bbox, optsCourants(null));
    if (id) { VL.setOutil("select"); VL.setSelection([id]); }
  };

  function calqueParNom(doc, nom, sousQui) {
    let c = doc.calques.find((x) => x.nom === nom);
    if (!c) {
      const id = op_calque_ajouter(doc, nom);
      c = doc.calques.find((x) => x.id === id);
      if (sousQui) {
        const iRef = doc.calques.findIndex((x) => x.nom === sousQui);
        if (iRef >= 0) op_calque_reordonner(doc, id, iRef);
      }
    }
    return c;
  }

  function insererMotif(fabrique) {
    const cx = etat.doc.taille.w / 2, cy = etat.doc.taille.h / 2;
    const g = fabrique(famille, cx, cy);
    const id = VL.executer(op_ajouter, etat.calqueActif, g);
    if (id) VL.setSelection([id]);
  }

  /* ── IA : POST /api/vector/illustration (appel LLM payant, DIT) ── */
  /* La pose des tracés de l'IA — UNE seule voie d'écriture au document,
     partagée par le champ du panneau (§9 du handoff) et par le dialogue du
     canevas (mod-ia). Rend le nombre de tracés posés. Le groupe est mis à
     l'échelle sur un carré de 60 % du petit côté de la page, centré. */
  VL.iaPoser = (d, q) => {
    const formes = (d && (d.formes
      // rétro-compat : l'ancienne route rendait `paths:[{d,fill}]`
      || (Array.isArray(d.paths) ? d.paths.map((p) => ({
        type: "path", d: p.d, style: { fond: p.fill } })) : null))) || [];
    if (!etat.doc || !formes.length) return 0;
    const vb = d.viewbox && d.viewbox.length === 4 ? d.viewbox
      : [0, 0, 100, 100];
    const cote = Math.min(etat.doc.taille.w, etat.doc.taille.h) * 0.6;
    // AUCUN `transform` sur le groupe (remontée du 07/09/2026 : « je dois
    // pouvoir la sélectionner et la déplacer ou redimensionner comme toute
    // autre forme »). Un `scale` de groupe faisait valoir un déplacement de
    // 100 px du document 100 × k à l'écran, et l'outil Nœuds ne mordait pas
    // sur des tracés exprimés dans un autre repère. Les formes sont donc
    // posées au repère du viewBox, puis MISES À L'ÉCHELLE PAR LA COMMANDE
    // DE REDIMENSIONNEMENT elle-même : la même que les poignées, déjà
    // testée, qui réécrit les COORDONNÉES. Le groupe sort du geste sans
    // transformation, comme un rectangle tracé à la main.
    const groupe = { type: "groupe", style: {},
      name: String(q || "illustration").slice(0, 24),
      enfants: formes.map((f) => JSON.parse(JSON.stringify(f))) };
    const id = VL.executer((doc) => {
      const gid = op_ajouter(doc, etat.calqueActif, groupe);
      const av = { x: vb[0], y: vb[1], w: vb[2] || 100, h: vb[3] || 100 };
      const k = cote / Math.max(av.w, av.h);
      op_redimensionner(doc, [gid], av, {
        x: (etat.doc.taille.w - av.w * k) / 2,
        y: (etat.doc.taille.h - av.h * k) / 2,
        w: av.w * k, h: av.h * k });
      return gid;
    });
    if (id) { VL.setSelection([id]); VL.setOutil("select"); }
    return id ? formes.length : 0;
  };

  async function iaLancer() {
    const champ = $("#vitIaPrompt");
    const q = (champ && champ.value || "").trim();
    if (!q) { regl.iaMsg = "décrire d'abord l'illustration";
              regl.iaErr = true; rendrePanneau(); return; }
    regl.iaBusy = true; regl.iaMsg = "génération…"; regl.iaErr = false;
    rendrePanneau();
    try {
      const r = await fetch("/api/vector/illustration", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: q }) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      const n = VL.iaPoser(d, q);
      regl.iaBusy = false; regl.iaErr = false;
      regl.iaMsg = `${n} tracés posés (${d.provider})`;
    } catch (e) {
      regl.iaBusy = false; regl.iaErr = true;
      regl.iaMsg = String(e.message || e).slice(0, 120);
    }
    rendrePanneau();
  }

  /* ── rendu du panneau ── */
  const sw3 = (t) => `linear-gradient(90deg,${t[0]} 0 33%,${t[1] || t[0]}`
    + ` 33% 66%,${t[2] || t[0]} 66% 100%)`;
  function rendrePanneau() {
    const hote = $("#panneauVitrail");
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const g = panneauSel();
    const src = g ? g.vitrail : regl;
    const table = gammes();
    const teintesActives = src.gamme === "perso"
      ? (g ? src.teintes : regl.perso)
      : (table[src.gamme] || GAMMES.chartres).teintes;
    const lib = (MOTIFS[g ? src.motif : regl.motif]
                 || MOTIFS.arc).libelles;
    const ancres = famille ? Object.entries(famille.palette.ancres) : [];
    const plombHex = couleurPlomb();

    hote.innerHTML = `
      <div class="vit-portee ${g ? "vit-portee-sel" : ""}">${g
        ? `panneau sélectionné · ${MOTIFS[src.motif].titre}`
        : "réglages du prochain panneau"}</div>
      <div class="ap-ligne"><span>Motif</span>
        <span class="vit-motifs">${Object.entries(MOTIFS).map(([k, m]) => `
          <button class="vit-mbtn ${!g && regl.motif === k ? "actif" : ""}"
                  data-motif="${k}"
                  title="${m.titre} — choisir puis GLISSER une zone sur la page">
            <svg viewBox="0 0 24 24" fill="currentColor"
                 ><use href="#v-${k}"></use></svg></button>`).join("")}
        </span></div>
      <div class="ap-ligne"><span>${lib[0]}</span>
        <span class="vit-step"><button data-pas="colonnes:-1">−</button
          ><b>${src.colonnes}</b><button data-pas="colonnes:1">+</button></span>
      </div>
      <div class="ap-ligne"><span>${lib[1]}</span>
        <span class="vit-step"><button data-pas="rangees:-1">−</button
          ><b>${src.rangees}</b><button data-pas="rangees:1">+</button></span>
      </div>
      <div class="ap-ligne"><span>Plomb</span>
        <input id="vitPlomb" type="range" min="2" max="16" step="1"
               value="${src.plomb}"/>
        <b class="vit-num">${src.plomb}</b></div>
      <div class="ap-ligne"><span>Joints</span>
        <label class="vit-joint"><input id="vitArrondi" type="checkbox"
          ${src.arrondi ? "checked" : ""}/> arrondis</label></div>
      <div class="vit-portee">gamme de verre</div>
      <div class="vit-gammes">${Object.entries(table).map(([k, gm]) => `
        <button class="vit-gsw ${src.gamme === k ? "actif" : ""}"
                data-gamme="${k}" title="${gm.titre}"
                style="background:${sw3(gm.teintes)}"></button>`).join("")}
      </div>
      <div class="vit-gnom">${(table[src.gamme] || GAMMES.chartres).titre}</div>
      <div class="ap-ligne"><span>Teintes</span>
        <span class="vit-slots">${teintesActives.map((c, i) => `
          <button class="vit-tsw ${regl.slot === i ? "actif" : ""}"
                  data-slot="${i}" title="teinte ${i + 1} · ${c}"
                  style="background:${c}"></button>`).join("")}
        </span></div>
      ${regl.slot !== null && regl.slot < teintesActives.length ? (() => {
        const hex = teintesActives[regl.slot];
        let hsl = { h: 210, s: 60, l: 40 };
        try { hsl = rgbVersHsl(hexVersRgb(hex)); } catch (e) { /* garde */ }
        const cs = (o) => rgbVersHex(hslVersRgb(o));
        const piste = (grad) => `background:${grad}`;
        return `
      <div class="vit-slotEd">
        <div class="vit-slotTete">
          <span class="vit-prev" style="background:${hex}"></span>
          <span>teinte ${regl.slot + 1} · ${hex}</span>
          <button id="vitSlotX" title="fermer">×</button></div>
        <div class="ap-ligne"><span>Teinte</span>
          <input class="vit-tsv" data-tsv="h" type="range" min="0" max="360"
                 step="1" value="${hsl.h}" style="${piste(
                   "linear-gradient(90deg,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00)")}"/></div>
        <div class="ap-ligne"><span>Satur.</span>
          <input class="vit-tsv" data-tsv="s" type="range" min="0" max="100"
                 step="1" value="${hsl.s}" style="${piste(
                   `linear-gradient(90deg,${cs({ h: hsl.h, s: 0, l: hsl.l })},${
                     cs({ h: hsl.h, s: 100, l: hsl.l })})`)}"/></div>
        <div class="ap-ligne"><span>Clarté</span>
          <input class="vit-tsv" data-tsv="l" type="range" min="6" max="94"
                 step="1" value="${hsl.l}" style="${piste(
                   `linear-gradient(90deg,${cs({ h: hsl.h, s: hsl.s, l: 6 })},${
                     cs({ h: hsl.h, s: hsl.s, l: 50 })},${
                     cs({ h: hsl.h, s: hsl.s, l: 94 })})`)}"/></div>
        <div class="ap-ligne"><span>Hex</span>
          <input id="vitHex" type="text" value="${hex}"/></div>
        <div class="vit-banque">${BANQUE_VERRES.map(([c, nom]) => `
          <button class="vit-bsw" data-verre="${c}" title="${nom}"
                  style="background:${c}"></button>`).join("")}</div>
      </div>`; })() : ""}
      ${g ? `<div class="ap-ligne">
        <button id="vitTirage" class="vit-large"
          title="Rejoue la répartition des teintes avec une autre graine — même motif, mêmes réglages">Nouveau tirage du verre</button></div>` : ""}
      <div class="ap-ligne"><span>IA</span>
        <input id="vitIaPrompt" type="text"
               placeholder="décrire une illustration…"/>
        <button id="vitIaGo" ${regl.iaBusy ? "disabled" : ""}
          title="Illustration vectorielle par le modèle de langage configuré (Réglages) — APPEL PAYANT sur votre clé, quelques centièmes de centime ; pose des masses de verre en un groupe">${regl.iaBusy ? "…" : "IA"}</button></div>
      ${regl.iaMsg ? `<div class="vit-iamsg ${regl.iaErr ? "err" : ""}"
        >${regl.iaMsg}</div>` : ""}
      ${ancres.length ? `
      <div class="vit-portee">palette de la fiche</div>
      <div class="vit-palette" title="La palette de la fiche épinglée — clic : applique à la sélection (ou au style courant)">
        ${ancres.map(([nom, hex]) => `<button class="vit-sw" data-hex="${hex}"
           title="${nom} ${hex}" style="background:${hex}"></button>`).join("")}
        <button class="vit-sw vit-plomb" data-hex="${plombHex}" data-contour="1"
           title="plomb ${plombHex} (contour)"
           style="background:${plombHex}"></button>
      </div>
      <div class="ap-ligne"><span>Motifs</span>
        <button id="vitIris" title="Iris stylisé (groupe)">⚜</button>
        <button id="vitRayons" title="Rayons solaires géométriques (groupe)">☀</button>
        <button id="vitHalo" title="Halo rayonnant (groupe)">◎</button>
      </div>` : ""}`;

    /* ── câblage ── */
    hote.querySelectorAll(".vit-mbtn").forEach((b) =>
      b.addEventListener("click", () => {
        regl.motif = b.dataset.motif;
        VL.setOutil("vitrail");
        rendrePanneau();
        VL.toast(`${MOTIFS[regl.motif].titre} : glissez une zone sur la`
                 + " page pour poser le panneau");
      }));
    hote.querySelectorAll("[data-pas]").forEach((b) =>
      b.addEventListener("click", () => {
        const [cle, dv] = b.dataset.pas.split(":");
        const bornes = { colonnes: [1, 12], rangees: [1, 14] };
        const cible = g ? g.vitrail : regl;
        const v = Math.max(bornes[cle][0],
          Math.min(bornes[cle][1], cible[cle] + (+dv)));
        if (v === cible[cle]) return;
        if (g) retoucher({ [cle]: v });
        else { regl[cle] = v; rendrePanneau(); }
      }));
    const pl = $("#vitPlomb");
    if (pl) pl.addEventListener("change", () => {
      if (g) retoucher({ plomb: +pl.value });
      else { regl.plomb = +pl.value; rendrePanneau(); }
    });
    const ar = $("#vitArrondi");
    if (ar) ar.addEventListener("change", () => {
      if (g) retoucher({ arrondi: ar.checked });
      else { regl.arrondi = ar.checked; rendrePanneau(); }
    });
    hote.querySelectorAll(".vit-gsw").forEach((b) =>
      b.addEventListener("click", () => {
        regl.gamme = b.dataset.gamme; regl.slot = null;
        if (g) retoucher({ gamme: regl.gamme });
        else rendrePanneau();
      }));
    hote.querySelectorAll(".vit-tsw").forEach((b) =>
      b.addEventListener("click", () => {
        const i = +b.dataset.slot;
        if (regl.gamme !== "perso" || (g && g.vitrail.gamme !== "perso")) {
          // éditer une teinte bascule en gamme perso, copie de l'active
          regl.perso = [...teintesActives];
          regl.gamme = "perso";
        }
        regl.slot = regl.slot === i ? null : i;
        if (g && regl.slot !== null) retoucher({ gamme: "perso",
                                                 teintes: regl.perso });
        else rendrePanneau();
      }));
    const poseTeinte = (hex) => {
      regl.perso = regl.perso.map((c, k) => (k === regl.slot ? hex : c));
      try { localStorage.setItem("dz_vl_teintes",
                                 JSON.stringify(regl.perso)); }
      catch (e) { /* stockage indisponible */ }
      if (g) retoucher({ gamme: "perso", teintes: regl.perso });
      else rendrePanneau();
    };
    hote.querySelectorAll(".vit-tsv").forEach((r) =>
      r.addEventListener("change", () => {
        const hex = teintesActives[regl.slot];
        let hsl;
        try { hsl = rgbVersHsl(hexVersRgb(hex)); }
        catch (e) { hsl = { h: 210, s: 60, l: 40 }; }
        hsl[r.dataset.tsv] = +r.value;
        poseTeinte(rgbVersHex(hslVersRgb(hsl)));
      }));
    const hx = $("#vitHex");
    if (hx) hx.addEventListener("change", () => {
      const v = hx.value.trim();
      if (/^#?[0-9a-fA-F]{6}$/.test(v)) {
        poseTeinte(v.startsWith("#") ? v : "#" + v);
      }
    });
    const sx = $("#vitSlotX");
    if (sx) sx.addEventListener("click", () => {
      regl.slot = null; rendrePanneau(); });
    hote.querySelectorAll(".vit-bsw").forEach((b) =>
      b.addEventListener("click", () => poseTeinte(b.dataset.verre)));
    const tir = $("#vitTirage");
    if (tir) tir.addEventListener("click", () =>
      retoucher({ graine: (g.vitrail.graine * 31 + 7) % 99991 }));
    const iaGo = $("#vitIaGo");
    if (iaGo) iaGo.addEventListener("click", iaLancer);
    const iaIn = $("#vitIaPrompt");
    if (iaIn) iaIn.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") iaLancer(); });
    hote.querySelectorAll(".vit-sw").forEach((b) =>
      b.addEventListener("click", async () => {
        const patch = b.dataset.contour
          ? { contour: b.dataset.hex } : { fond: b.dataset.hex };
        Object.assign(etat.styleCourant, patch);
        if (etat.selection.length) {
          const { op_style } = await import("./mod-doc.js");
          VL.executer(op_style, etat.selection.slice(), patch);
        }
      }));
    const bIris = $("#vitIris"), bRay = $("#vitRayons"), bHalo = $("#vitHalo");
    if (bIris) bIris.addEventListener("click",
      () => insererMotif((f, x, y) => motif_iris(f, x, y, 1.4)));
    if (bRay) bRay.addEventListener("click",
      () => insererMotif((f, x, y) => motif_rayons(f, x, y, 110, 8)));
    if (bHalo) bHalo.addEventListener("click",
      () => insererMotif((f, x, y) => motif_halo(f, x, y, 80)));
  }

  fetch("/api/vector/vitrail").then((r) => r.ok ? r.json() : null)
    .then((d) => { famille = d && d.famille; rendrePanneau(); })
    .catch(() => { famille = null; rendrePanneau(); });

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendrePanneau(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendrePanneau(); };
}
