// mod-bool.js — booléens (phase 3) : aplatissement des objets en anneaux
// de points (tolérance 0,25 px), pont vers martinez (vendorisé, MIT —
// vendor/LICENSE-martinez.txt), opérations union/soustraction/intersection
// et division-métier. Le transform des objets est APPLIQUÉ à
// l'aplatissement (suites de rotate composées en matrice — les seules que
// nos opérations émettent).
import { chemin_parser, chemin_serialiser, idLibre } from "./mod-doc.js";

/* ── résolveur martinez : injecté au banc, window.martinez à l'écran ── */
let _mz = null;
export function fournirMartinez(m) { _mz = m; }
import { forme_d } from "./mod-formes.js";   // lot B : les formes s'aplatissent par leur d recalculé
function _martinez() {
  if (_mz) return _mz;
  if (typeof window !== "undefined" && window.martinez) {
    _mz = window.martinez;
    return _mz;
  }
  throw new Error("martinez indisponible (vendor/martinez.umd.js non chargé)");
}

const TOL = 0.25;

/* ── matrices 2D [a b c d e f] : x' = a x + c y + e ; y' = b x + d y + f ── */
const _IDENT = [1, 0, 0, 1, 0, 0];
function _mul(m, n) {
  return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
          m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
          m[0] * n[4] + m[2] * n[5] + m[4],
          m[1] * n[4] + m[3] * n[5] + m[5]];
}
function _matriceDe(transform) {
  let m = _IDENT;
  if (!transform) return m;
  const re = /rotate\(\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+))?\s*\)/g;
  let t;
  while ((t = re.exec(transform)) !== null) {
    const a = (+t[1]) * Math.PI / 180;
    const cx = +(t[2] || 0), cy = +(t[3] || 0);
    const cos = Math.cos(a), sin = Math.sin(a);
    // rotate(a cx cy) = translate(cx cy) rotate(a) translate(-cx -cy)
    const r = [cos, sin, -sin, cos,
               cx - cos * cx + sin * cy, cy - sin * cx - cos * cy];
    m = _mul(m, r);              // gauche → droite : le plus à droite s'applique en premier
  }
  return m;
}
const _pt = (m, x, y) => [m[0] * x + m[2] * y + m[4],
                          m[1] * x + m[3] * y + m[5]];

/* ── aplatissement des courbes ── */
function _plat_cubique(out, p0, p1, p2, p3, tol, prof = 0) {
  // plat si les contrôles collent à la corde (distance perpendiculaire)
  const dx = p3[0] - p0[0], dy = p3[1] - p0[1];
  const d1 = Math.abs((p1[0] - p0[0]) * dy - (p1[1] - p0[1]) * dx);
  const d2 = Math.abs((p2[0] - p0[0]) * dy - (p2[1] - p0[1]) * dx);
  const long = Math.hypot(dx, dy) || 1e-9;
  if (prof >= 16 || (d1 + d2) / long <= tol) { out.push(p3); return; }
  const mi = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  const p01 = mi(p0, p1), p12 = mi(p1, p2), p23 = mi(p2, p3);
  const p012 = mi(p01, p12), p123 = mi(p12, p23);
  const p0123 = mi(p012, p123);
  _plat_cubique(out, p0, p01, p012, p0123, tol, prof + 1);
  _plat_cubique(out, p0123, p123, p23, p3, tol, prof + 1);
}

function _polylignes_path(d, tol) {
  const segs = chemin_parser(d);
  const lignes = [];
  let cour = null;
  for (const s of segs) {
    if (s.c === "M") {
      if (cour && cour.points.length > 1) lignes.push(cour);
      cour = { points: [[s.p[0], s.p[1]]], ferme: false };
    } else if (!cour) {
      throw new Error("chemin sans M initial");
    } else if (s.c === "L") {
      cour.points.push([s.p[0], s.p[1]]);
    } else if (s.c === "C") {
      const p0 = cour.points[cour.points.length - 1];
      _plat_cubique(cour.points, p0, [s.p[0], s.p[1]], [s.p[2], s.p[3]],
                    [s.p[4], s.p[5]], tol);
    } else if (s.c === "Q") {
      // élévation de degré : quadratique → cubique équivalente
      const p0 = cour.points[cour.points.length - 1];
      const c = [s.p[0], s.p[1]], p3 = [s.p[2], s.p[3]];
      const c1 = [p0[0] + 2 / 3 * (c[0] - p0[0]), p0[1] + 2 / 3 * (c[1] - p0[1])];
      const c2 = [p3[0] + 2 / 3 * (c[0] - p3[0]), p3[1] + 2 / 3 * (c[1] - p3[1])];
      _plat_cubique(cour.points, p0, c1, c2, p3, tol);
    } else if (s.c === "Z") {
      cour.ferme = true;
      lignes.push(cour);
      cour = null;
    }
  }
  if (cour && cour.points.length > 1) lignes.push(cour);
  return lignes;
}

function _points_ellipse(cx, cy, rx, ry, tol) {
  const r = Math.max(Math.abs(rx), Math.abs(ry), 1e-6);
  const pas = 2 * Math.acos(Math.max(-1, 1 - Math.min(tol, r) / r));
  // plancher 64 : le polygone INSCRIT sous-estime l'aire en ~(2π²/3)/n² —
  // à 64 l'erreur d'aire est ≤ 0,16 %, sous le contrat ±0,5 %
  const n = Math.max(64, Math.min(720, Math.ceil(2 * Math.PI / (pas || 0.1))));
  const pts = [];
  for (let k = 0; k < n; k++) {
    const a = 2 * Math.PI * k / n;
    pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  return pts;
}

/* polylignes d'un objet (matrice parent appliquée), SANS fermeture forcée —
   la voie du contour gonflé en dépend */
export function polylignes_objet(objet, tol = TOL, mParent = _IDENT) {
  const m = _mul(mParent, _matriceDe(objet.transform));
  const appl = (lignes) => lignes.map((l) => ({
    ferme: l.ferme, points: l.points.map(([x, y]) => _pt(m, x, y)) }));
  switch (objet.type) {
    case "rect": {
      const { x, y, w, h } = objet;
      return appl([{ ferme: true,
        points: [[x, y], [x + w, y], [x + w, y + h], [x, y + h]] }]);
    }
    case "ellipse":
      return appl([{ ferme: true,
        points: _points_ellipse(objet.cx, objet.cy, objet.rx, objet.ry, tol) }]);
    case "path":
      return appl(_polylignes_path(objet.d, tol));
    case "forme":
      return appl(_polylignes_path(forme_d(objet), tol));
    case "groupe": {
      const out = [];
      for (const e of objet.enfants || []) {
        out.push(...polylignes_objet(e, tol, m));
      }
      return out;
    }
    case "texte":
      throw new Error("texte : vectorisation hors périmètre — retire le "
                      + "texte de la sélection booléenne");
    default:
      throw new Error(`type non aplatissable: ${objet.type}`);
  }
}

/* anneaux FERMÉS (premier == dernier) — l'entrée des booléens */
export function aplatir_objet(objet, tol = TOL) {
  const anneaux = [];
  for (const l of polylignes_objet(objet, tol)) {
    if (l.points.length < 3) continue;
    const ring = l.points.slice();
    const p0 = ring[0], pn = ring[ring.length - 1];
    if (p0[0] !== pn[0] || p0[1] !== pn[1]) ring.push([p0[0], p0[1]]);
    anneaux.push(ring);
  }
  return anneaux;
}

/* ── anneaux ↔ multipolygone martinez ──
   Le multipolygone d'un objet = pli XOR de ses anneaux (sémantique
   pair-impair : un anneau intérieur devient un trou, quelle que soit son
   orientation — c'est aussi ce que nos divisions émettent). */
function _versMulti(anneaux) {
  const mz = _martinez();
  let mp = null;
  for (const ring of anneaux) {
    const p = [[ring]];
    mp = mp ? mz.xor(mp, p) : p;
  }
  return mp || [];
}

function _signee(pts) {           // aire signée d'un anneau SANS doublon final
  let s = 0;
  for (let k = 0; k < pts.length; k++) {
    const a = pts[k], b = pts[(k + 1) % pts.length];
    s += a[0] * b[1] - b[0] * a[1];
  }
  return s / 2;
}

function _dDePoly(poly) {
  // martinez ne garantit PAS l'opposition d'orientation des trous : on la
  // FORCE ici (extérieur positif, trous négatifs) — sans elle le rendu
  // nonzero peindrait les trous pleins et les aires s'additionneraient.
  const segs = [];
  poly.forEach((ring, idx) => {
    if (!ring || ring.length < 3) return;
    const clos = ring[0][0] === ring[ring.length - 1][0]
              && ring[0][1] === ring[ring.length - 1][1];
    let pts = clos ? ring.slice(0, -1) : ring.slice();
    if (pts.length < 3) return;
    const veutPositif = idx === 0;
    if ((_signee(pts) > 0) !== veutPositif) pts = pts.reverse();
    segs.push({ c: "M", p: [pts[0][0], pts[0][1]] });
    for (let k = 1; k < pts.length; k++) {
      segs.push({ c: "L", p: [pts[k][0], pts[k][1]] });
    }
    segs.push({ c: "Z", p: [] });
  });
  return chemin_serialiser(segs);
}
const _dDeMulti = (mp) => mp.map(_dDePoly).filter(Boolean).join(" ");

/* ── contour GONFLÉ d'un objet tracé (fond none) : union de
   quadrilatères par segment + disques aux sommets (joints/bouts ronds,
   comme notre rendu). C'est ce qui permet au réseau de plombs tracé à la
   plume de découper la plaque. ── */
function _disque(cx, cy, r, n = 24) {
  const pts = [];
  for (let k = 0; k < n; k++) {
    const a = 2 * Math.PI * k / n;
    pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  pts.push([pts[0][0], pts[0][1]]);
  return pts;
}

export function contour_en_multi(objet, tol = TOL) {
  return _contourEnMulti(objet, tol);
}

/* anneaux (aplatir_objet) → multi martinez — la sémantique evenodd des
   sous-chemins (XOR), exposée pour l'extrusion d'impression (phase 3) */
export function versMulti(anneaux) {
  return _versMulti(anneaux);
}

function _contourEnMulti(objet, tol) {
  const mz = _martinez();
  const w = (((objet.style || {}).epaisseur) || 1) / 2;
  let mp = null;
  const ajouter = (ring) => {
    const p = [[ring]];
    mp = mp ? mz.union(mp, p) : p;
  };
  for (const l of polylignes_objet(objet, tol)) {
    const pts = l.points;
    const nSeg = l.ferme ? pts.length : pts.length - 1;
    for (let k = 0; k < nSeg; k++) {
      const p = pts[k], q = pts[(k + 1) % pts.length];
      const dx = q[0] - p[0], dy = q[1] - p[1];
      const lg = Math.hypot(dx, dy);
      if (lg < 1e-9) continue;
      const nx = -dy / lg * w, ny = dx / lg * w;
      ajouter([[p[0] + nx, p[1] + ny], [q[0] + nx, q[1] + ny],
               [q[0] - nx, q[1] - ny], [p[0] - nx, p[1] - ny],
               [p[0] + nx, p[1] + ny]]);
    }
    for (const p of pts) ajouter(_disque(p[0], p[1], w));
  }
  return mp || [];
}

/* ── les opérations : tout se CALCULE avant de muter (un refus ne laisse
   aucune trace) ; le résultat remplace les opérandes à l'emplacement du
   plus BAS, son style copié ── */
function _ciblesOrdonnees(doc, ids) {
  const voulu = new Set(ids);
  const out = [];
  for (const c of doc.calques) {
    if (c.verrou) continue;
    c.objets.forEach((o, i) => {
      if (voulu.has(o.id)) out.push({ calque: c, objet: o, i });
    });
  }
  return out;
}

export function op_booleen(doc, ids, mode) {
  if (!["union", "soustraction", "intersection"].includes(mode)) {
    throw new Error(`booléen: mode inconnu ${mode}`);
  }
  const cibles = _ciblesOrdonnees(doc, ids);
  if (cibles.length < 2) {
    throw new Error("booléen: au moins deux objets déverrouillés");
  }
  const mz = _martinez();
  const multis = cibles.map((c) => _versMulti(aplatir_objet(c.objet)));
  let mp;
  if (mode === "union") {
    mp = multis[0];
    for (let k = 1; k < multis.length; k++) mp = mz.union(mp, multis[k]);
  } else if (mode === "intersection") {
    mp = multis[0];
    for (let k = 1; k < multis.length; k++) {
      mp = mz.intersection(mp, multis[k]);
      if (!mp || !mp.length) break;
    }
  } else {
    let autres = multis[1];
    for (let k = 2; k < multis.length; k++) autres = mz.union(autres, multis[k]);
    mp = mz.diff(multis[0], autres);
  }
  if (!mp || !mp.length) throw new Error("booléen: résultat vide");
  const bas = cibles[0];
  const indexBas = bas.i;         // le plus bas: rien de retiré avant lui
  for (const t of cibles) {
    const j = t.calque.objets.indexOf(t.objet);
    if (j >= 0) t.calque.objets.splice(j, 1);
  }
  const id = idLibre(doc);
  bas.calque.objets.splice(Math.min(indexBas, bas.calque.objets.length), 0,
    { id, type: "path", d: _dDeMulti(mp),
      style: { ...(bas.objet.style || {}) } });
  return id;
}

export function op_division(doc, ids) {
  const cibles = _ciblesOrdonnees(doc, ids);
  if (cibles.length < 2) {
    throw new Error("division: la plaque et au moins un découpeur");
  }
  const mz = _martinez();
  const plaque = cibles[0];       // le plus BAS = la plaque de verre
  const plaqueMp = _versMulti(aplatir_objet(plaque.objet));
  let cut = null;
  for (const t of cibles.slice(1)) {
    const o = t.objet;
    const fondPlein = o.style && o.style.fond && o.style.fond !== "none";
    const m = fondPlein ? _versMulti(aplatir_objet(o))
                        : _contourEnMulti(o, TOL);
    cut = cut ? mz.union(cut, m) : m;
  }
  const reste = mz.diff(plaqueMp, cut);
  if (!reste || !reste.length) {
    throw new Error("division: la découpe ne laisse aucun fragment");
  }
  const indexP = plaque.i;
  plaque.calque.objets.splice(plaque.calque.objets.indexOf(plaque.objet), 1);
  const nouveaux = [];
  reste.forEach((poly, k) => {
    const id = idLibre(doc);
    plaque.calque.objets.splice(
      Math.min(indexP + k, plaque.calque.objets.length), 0,
      { id, type: "path", d: _dDePoly(poly),
        style: { ...(plaque.objet.style || {}) } });
    nouveaux.push(id);
  });
  return nouveaux;
}

/* aire d'un MULTIPOLYGONE martinez, INDIFFÉRENTE à l'orientation des
   anneaux (la lib ne la garantit pas — piège déjà vu) : par polygone,
   |extérieur| − Σ|trous|. */
export function aire_multi(mp) {
  let total = 0;
  for (const poly of mp || []) {
    poly.forEach((ring, idx) => {
      if (!ring || ring.length < 3) return;
      const clos = ring[0][0] === ring[ring.length - 1][0]
                && ring[0][1] === ring[ring.length - 1][1];
      const pts = clos ? ring.slice(0, -1) : ring;
      const a = Math.abs(_signee(pts));
      total += idx === 0 ? a : -a;
    });
  }
  return total;
}

/* aire d'un jeu d'anneaux : somme SIGNÉE absolue (les trous, en
   orientation opposée, se soustraient) */
export function aire_de(anneaux) {
  let total = 0;
  for (const ring of anneaux) {
    let s = 0;
    for (let k = 0; k < ring.length - 1; k++) {
      s += ring[k][0] * ring[k + 1][1] - ring[k + 1][0] * ring[k][1];
    }
    total += s / 2;
  }
  return Math.abs(total);
}


/* ══════════ lot B : couteau, gomme, contour, atomes du Shape Builder ══════════
   Tout se CALCULE avant de muter ; les résultats sont des chemins (d issu de
   _dDeMulti, trous forcés en orientation opposée) qui prennent le style de
   la cible ; un refus ne laisse aucune trace. */
function _ciblesB(doc, ids) {
  const voulu = new Set(ids), out = [];
  for (const c of doc.calques) {
    if (c.verrou) continue;
    c.objets.forEach((o, i) => { if (voulu.has(o.id) && !o.verrou) out.push({ calque: c, objet: o, i }); });
  }
  if (!out.length) throw new Error("aucun objet déverrouillé dans la sélection");
  return out;
}
function _multiObjet(o) {
  const fond = o.style && o.style.fond;
  return (fond && fond !== "none") ? _versMulti(aplatir_objet(o)) : _contourEnMulti(o, TOL);
}
// nettoie ce que martinez laisse traîner : anneaux dégénérés (< 4 points,
// trous à 2 sommets vus après une union de disque) qui font perdre la moitié
// du quadrilatère suivant (mesuré : 250 au lieu de 500 sur la 4e arête)
const _propreB = (mp) => (mp || []).map((poly) => (poly || []).filter((ring) => ring && ring.length >= 4))
  .filter((poly) => poly.length && poly[0].length >= 4);
function _idLibreB(doc) {
  const pris = new Set();
  for (const c of doc.calques) (function v(objs) { for (const o of objs) { pris.add(o.id); if (o.type === "groupe") v(o.enfants || []); } })(c.objets);
  let n = 1;
  while (pris.has("o" + n)) n++;
  pris.add("o" + n);
  return "o" + n;
}
function _cheminDe(doc, mp, style, transform) {
  const o = { id: _idLibreB(doc), type: "path", d: _dDeMulti(mp), style: { ...(style || {}) } };
  if (o.style.fond === undefined || o.style.fond === "none") o.style.fond = style && style.contour ? style.contour : "#9DB4D6";
  if (transform) o.transform = transform;
  return o;
}
// remplace la cible par les chemins (un par multipolygone fourni), à sa place
function _remplacer(cible, doc, multis) {
  const neufs = multis.map((mp) => _cheminDe(doc, mp, cible.objet.style));
  cible.calque.objets.splice(cible.calque.objets.indexOf(cible.objet), 1, ...neufs);
  return neufs.map((o) => o.id);
}

export function op_couteau(doc, ids, ligne) {
  const mz = _martinez();
  const [x0, y0, x1, y1] = ligne.map(Number);
  const dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy);
  if (!(L > 1e-9)) throw new Error("couteau : tirer une droite");
  const ux = dx / L, uy = dy / L, nx = -uy, ny = ux, B = 1e5;
  const cote = (s) => [[[[x0 - ux * B, y0 - uy * B], [x0 + ux * B, y0 + uy * B],
                        [x0 + ux * B + nx * B * s, y0 + uy * B + ny * B * s], [x0 - ux * B + nx * B * s, y0 - uy * B + ny * B * s],
                        [x0 - ux * B, y0 - uy * B]]]];
  const gauche = cote(1), droite = cote(-1);
  const plan = [];
  for (const c of _ciblesB(doc, ids)) {
    let mp;
    try { mp = _multiObjet(c.objet); } catch { continue; }
    const a = _propreB(mz.intersection(mp, gauche)), b = _propreB(mz.intersection(mp, droite));
    if (a.length && b.length) plan.push({ c, morceaux: [a, b] });
  }
  if (!plan.length) throw new Error("le couteau ne coupe rien : la droite ne traverse aucune forme");
  const out = [];
  for (const { c, morceaux } of plan) out.push(..._remplacer(c, doc, morceaux));
  return out;
}

export function op_gomme(doc, ids, dTrait, largeur) {
  const mz = _martinez();
  if (!(largeur > 0)) throw new Error("gomme : largeur > 0 requise");
  const bande = _contourEnMulti({ type: "path", d: dTrait, style: { epaisseur: largeur } }, TOL);
  const out = [];
  for (const c of _ciblesB(doc, ids)) {
    let mp;
    try { mp = _multiObjet(c.objet); } catch { out.push(c.objet.id); continue; }
    if (!bande.length) { out.push(c.objet.id); continue; }
    const r = _propreB(mz.diff(mp, bande));
    const avant = Math.abs(aire_multi(mp)), apres = r.length ? Math.abs(aire_multi(r)) : 0;
    if (Math.abs(avant - apres) < 1e-6) { out.push(c.objet.id); continue; }    // intacte : rien à faire
    if (!r.length) { c.calque.objets.splice(c.calque.objets.indexOf(c.objet), 1); continue; }
    out.push(..._remplacer(c, doc, r.map((poly) => [poly])));
  }
  return out;
}

function _retraitB(mz, mp, d) {
  let out = mp;
  for (const poly of mp) for (const ring of poly) {
    const pts = ring.slice(0, -1);
    for (let k = 0; k < pts.length; k++) {
      const p = pts[k], q = pts[(k + 1) % pts.length];
      const ex = q[0] - p[0], ey = q[1] - p[1], lg = Math.hypot(ex, ey);
      if (lg < 1e-9) continue;
      const nx = -ey / lg * d, ny = ex / lg * d;
      out = _propreB(mz.diff(out, [[[[p[0] + nx, p[1] + ny], [q[0] + nx, q[1] + ny], [q[0] - nx, q[1] - ny], [p[0] - nx, p[1] - ny], [p[0] + nx, p[1] + ny]]]]));
      if (!out.length) return out;
      // le disque déborde d'1 % : ses tangentes ne coïncident plus avec les
      // bords du quadrilatère (la coïncidence exacte égarait martinez :
      // 483 mm² perdus aux quatre coins d'un carré gonflé, mesuré)
      out = _propreB(mz.diff(out, [[_disque(p[0], p[1], d * 1.01)]]));
      if (!out.length) return out;
    }
  }
  return out;
}
export function op_contour(doc, ids, decalage) {
  const mz = _martinez();
  const d = +decalage;
  if (!d) throw new Error("contour : décalage non nul requis (+ dehors, − dedans)");
  const out = [];
  for (const c of _ciblesB(doc, ids)) {
    const mp = _multiObjet(c.objet);
    let r;
    if (d > 0) {
      // dehors = complément du RETRAIT du complément : les différences
      // progressives sont robustes là où les unions successives de
      // quadrilatères et de disques perdaient des morceaux (mesuré : 11846,
      // 11616 au lieu de 12078 sur un carré de 100 gonflé de 5)
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const poly of mp) for (const ring of poly) for (const [x, y] of ring) {
        x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
      }
      const m = 3 * d;
      const boite = [[[[x0 - m, y0 - m], [x1 + m, y0 - m], [x1 + m, y1 + m], [x0 - m, y1 + m], [x0 - m, y0 - m]]]];
      const boiteInt = [[[[x0 - m + d, y0 - m + d], [x1 + m - d, y0 - m + d], [x1 + m - d, y1 + m - d], [x0 - m + d, y1 + m - d], [x0 - m + d, y0 - m + d]]]];
      const complement = _propreB(mz.diff(boite, mp));
      const retire = _retraitB(mz, complement, d);
      r = _propreB(retire.length ? mz.diff(boiteInt, retire) : boiteInt);
    } else {
      r = _retraitB(mz, mp, -d);
      if (!r.length) throw new Error("contour : le retrait vide la forme");
    }
    const neuf = _cheminDe(doc, r, c.objet.style);
    c.calque.objets.splice(c.calque.objets.indexOf(c.objet) + 1, 0, neuf);
    out.push(neuf.id);
  }
  return out;
}

/* ── Shape Builder : les ATOMES (régions élémentaires) de N formes ── */
export function atomes(multis) {
  const mz = _martinez();
  let at = [];
  for (const S of multis) {
    const neufs = [];
    let reste = S;
    for (const a of at) {
      const inter = _propreB(mz.intersection(a, S)), diff = _propreB(mz.diff(a, S));
      if (inter.length && Math.abs(aire_multi(inter)) > 1e-9) neufs.push(inter);
      if (diff.length && Math.abs(aire_multi(diff)) > 1e-9) neufs.push(diff);
      if (reste.length) reste = _propreB(mz.diff(reste, a));
    }
    if (reste.length && Math.abs(aire_multi(reste)) > 1e-9) neufs.push(reste);
    at = neufs;
  }
  return at;
}
export function point_dans_multi(mp, x, y) {
  let dedans = false;
  for (const poly of mp) for (const ring of poly) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) dedans = !dedans;
    }
  }
  return dedans;
}
export function op_constructeur(doc, ids, points, mode = "fusionner") {
  const mz = _martinez();
  const cibles = _ciblesB(doc, ids);
  const at = atomes(cibles.map((c) => _multiObjet(c.objet)));
  const choisis = at.filter((a) => (points || []).some((p) => point_dans_multi(a, p.x, p.y)));
  if (!choisis.length) throw new Error("constructeur : aucun atome sous le clic");
  const garde = mode === "retirer" ? at.filter((a) => !choisis.includes(a)) : choisis;
  if (!garde.length) throw new Error("constructeur : il ne resterait rien");
  let r = garde[0];
  for (const a of garde.slice(1)) r = _propreB(mz.union(r, a));
  const bas = cibles[0];
  const neuf = _cheminDe(doc, r, bas.objet.style);
  for (const c of cibles.slice().reverse()) c.calque.objets.splice(c.calque.objets.indexOf(c.objet), 1);
  bas.calque.objets.splice(Math.min(bas.i, bas.calque.objets.length), 0, neuf);
  return neuf.id;
}
