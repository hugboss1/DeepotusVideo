// mod-repeter.js — lot D2 « Répéter et fusionner » (spec 2026-11-08-illustrator-vectorlab-inventaire.md, plan
// 2026-11-08-vectorlab-d2-repeter-fusionner.md) : les RÉPÉTITIONS et les FUSIONS VIVANTES d'Illustrator.
//
// Une répétition est un GROUPE qui porte sa recette : { repetition: { mode, params, empreinte }, enfants: [source,
// ...copies] }. Les copies sont STOCKÉES (l'export, l'impression, le serveur et une version plus ancienne les voient
// sans rien savoir des répétitions), marquées `genere: true`, d'ids `<groupe>_r<k>` (descendants `<copie>_<j>`) qui
// ne recroisent jamais les `o<n>` d'idLibre. `vivants_d2_rafraichir` passe après CHAQUE commande, appelé par
// derives_rafraichir (mod-vivants.js) : la source modifiée, les copies suivent dans la même étape d'historique.
// L'empreinte couvre la source ET les réglages : seule une empreinte changée coûte un recalcul. Une source disparue,
// ou un recalcul impossible, laisse le groupe à son dernier état — jamais une exception au rendu.
// Règle de mod-bool : tout se CALCULE avant de muter, un refus ne laisse aucune trace.
import { T } from "./mod-i18n.js";
import { polylignes_objet } from "./mod-bool.js";

const MAX_COPIES = 200;
const MODES = new Set(["radiale", "grille", "miroir"]);
const DECALAGES = new Set(["aucun", "brique_lignes", "brique_colonnes", "hexagones"]);
// au millionième : un pas arrondi au centième (34,64 pour √3 × 20) ouvrirait des jours dans un pavage
const nbc = (x) => String(Math.round(x * 1e6) / 1e6 + 0);

/* ── les points et la boîte d'un objet, transform compris (la géométrie des booléens) ── */
function _points(o) {
  let lignes;
  if (o.type === "image" || o.type === "cadre") {
    lignes = polylignes_objet({ type: "rect", x: o.x, y: o.y, w: o.w, h: o.h, transform: o.transform });
  } else {
    try { lignes = polylignes_objet(o); } catch (e) { return null; }
  }
  return lignes.flatMap((l) => l.points);
}
function _boite(o) {
  const pts = _points(o);
  if (!pts) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) {
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  if (!(x1 >= x0) || !(y1 >= y0)) return null;
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

/* ── réglages : défauts, bornes ── */
function _entier(v, min, max, cle) {
  const n = Number(v);
  if (!Number.isInteger(n) || n < min || n > max) throw new Error(T(cle, { min, max }));
  return n;
}
function _positif(v, cle) {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0 || n > 1e5) throw new Error(T(cle));
  return n;
}
function _fini(v, cle) {
  const n = Number(v);
  if (!Number.isFinite(n) || Math.abs(n) > 1e5) throw new Error(T(cle));
  return n;
}
// le pas de la grille, relu sur la boîte COURANTE de la source (elle peut grandir) : boîte + écart ; hexagones :
// à plat (plus large que haut) les colonnes se recouvrent d'un quart, en pointe ce sont les lignes
function _pas(p, b) {
  const plat = b.w >= b.h;
  let px = b.w + p.ecartX, py = b.h + p.ecartY;
  if (p.decalage === "hexagones") { if (plat) px = 0.75 * b.w + p.ecartX; else py = 0.75 * b.h + p.ecartY; }
  if (!(px > 0) || !(py > 0)) throw new Error(T("vectorlab.repeter.ecart"));
  return { px, py, plat };
}
function _params(mode, p, source, base = {}) {
  const v = { ...base, ...(p || {}) };
  if (mode === "radiale") {
    const b = _boite(source);
    return {
      nombre: _entier(v.nombre === undefined ? 8 : v.nombre, 2, 100, "vectorlab.repeter.nombre"),
      rayon: _positif(v.rayon === undefined ? Math.hypot(b.w, b.h) / 2 : v.rayon, "vectorlab.repeter.rayon"),
      orienter: v.orienter === undefined ? true : !!v.orienter,
    };
  }
  if (mode === "grille") {
    const lignes = _entier(v.lignes === undefined ? 3 : v.lignes, 1, 50, "vectorlab.repeter.lignes");
    const colonnes = _entier(v.colonnes === undefined ? 3 : v.colonnes, 1, 50, "vectorlab.repeter.colonnes");
    if (lignes * colonnes < 2) throw new Error(T("vectorlab.repeter.une_seule"));
    if (lignes * colonnes > MAX_COPIES) throw new Error(T("vectorlab.repeter.trop", { max: MAX_COPIES }));
    const decalage = v.decalage === undefined ? "aucun" : v.decalage;
    if (!DECALAGES.has(decalage)) throw new Error(T("vectorlab.repeter.decalage", { decalage }));
    const g = {
      lignes, colonnes,
      ecartX: _fini(v.ecartX === undefined ? 0 : v.ecartX, "vectorlab.repeter.ecart_invalide"),
      ecartY: _fini(v.ecartY === undefined ? 0 : v.ecartY, "vectorlab.repeter.ecart_invalide"),
      decalage, miroirLignes: !!v.miroirLignes, miroirColonnes: !!v.miroirColonnes,
    };
    return g;                                   // le pas se vérifie à la construction (_pas)
  }
  if (mode === "miroir") {
    const angle = _fini(v.angle === undefined ? 90 : v.angle, "vectorlab.repeter.angle");
    return {
      angle: ((angle % 360) + 360) % 360,      // 450° = 90°, -90° = 270°
      ecart: _fini(v.ecart === undefined ? 0 : v.ecart, "vectorlab.repeter.ecart_invalide"),
    };
  }
  throw new Error(T("vectorlab.repeter.mode", { mode }));
}

/* ── les copies ── */
// une copie profonde SANS les liens vivants de la source (une copie suivrait la mauvaise source) ni recette (une
// copie de répétition est figée : seule la source se recalcule), ids dérivés de celui de la copie
function _copier(o, id) {
  const c = JSON.parse(JSON.stringify(o));
  const nettoyer = (x) => {
    delete x.derive; delete x.repetition; delete x.genere;
    if (x.type === "textechemin") { delete x.chemin; delete x.empreinte; }
    if (x.type === "groupe") for (const e of x.enfants || []) nettoyer(e);
  };
  nettoyer(c);
  const renommer = (x, i) => {
    x.id = i;
    if (x.type === "groupe") {
      (x.enfants || []).forEach((e, j) => renommer(e, `${i}_${j + 1}`));
      if (x.clip) x.clip = `${i}_1`;               // un groupe écrêté : son conteneur est le premier enfant
    }
  };
  renommer(c, id);
  c.genere = true;
  return c;
}
function _prefixer(o, t) { o.transform = o.transform ? `${t} ${o.transform}` : t; return o; }

function _copies(gid, mode, p, source) {
  const out = [];
  if (mode === "radiale") {
    const b = _boite(source);
    if (!b) throw new Error(T("vectorlab.repeter.source_type"));
    const sx = b.x + b.w / 2, sy = b.y + b.h / 2;
    const cx = sx, cy = sy + p.rayon;            // la source en haut du cercle, comme Illustrator
    for (let k = 1; k < p.nombre; k++) {
      const a = 360 * k / p.nombre;
      const c = _copier(source, `${gid}_r${k}`);
      if (p.orienter) _prefixer(c, `rotate(${nbc(a)} ${nbc(cx)} ${nbc(cy)})`);
      else {
        const r = a * Math.PI / 180, dx = sx - cx, dy = sy - cy;
        const nx = cx + dx * Math.cos(r) - dy * Math.sin(r), ny = cy + dx * Math.sin(r) + dy * Math.cos(r);
        _prefixer(c, `translate(${nbc(nx - sx)} ${nbc(ny - sy)})`);
      }
      out.push(c);
    }
  } else if (mode === "grille") {
    const b = _boite(source);
    if (!b) throw new Error(T("vectorlab.repeter.source_type"));
    const { px, py, plat } = _pas(p, b);
    const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
    const briqueL = p.decalage === "brique_lignes" || (p.decalage === "hexagones" && !plat);
    const briqueC = p.decalage === "brique_colonnes" || (p.decalage === "hexagones" && plat);
    let k = 0;
    for (let i = 0; i < p.lignes; i++) {
      for (let j = 0; j < p.colonnes; j++) {
        if (!i && !j) continue;                    // la case (0, 0) est la source
        const dx = j * px + (briqueL && i % 2 ? px / 2 : 0), dy = i * py + (briqueC && j % 2 ? py / 2 : 0);
        const c = _copier(source, `${gid}_r${++k}`);
        const mx = p.miroirColonnes && j % 2, my = p.miroirLignes && i % 2;
        // le miroir autour du centre de la source PUIS le déplacement (le préfixe le plus à gauche s'applique en dernier)
        if (mx || my) _prefixer(c, `matrix(${mx ? -1 : 1} 0 0 ${my ? -1 : 1} ${nbc(mx ? 2 * cx : 0)} ${nbc(my ? 2 * cy : 0)})`);
        if (dx || dy) _prefixer(c, `translate(${nbc(dx)} ${nbc(dy)})`);
        out.push(c);
      }
    }
  }
  else if (mode === "miroir") {
    // l'axe a la direction de l'angle (90° = vertical) ; sa normale (angle - 90°) pointe hors de la source : à 90°
    // vers la droite, à 0° vers le haut. Il passe à la plus grande avancée de la source le long de la normale, plus
    // l'écart — collé au bord, comme le miroir d'Illustrator.
    const pts = _points(source);
    if (!pts || !pts.length) throw new Error(T("vectorlab.repeter.source_type"));
    const a = p.angle * Math.PI / 180, nx = Math.sin(a), ny = -Math.cos(a);
    const d = Math.max(...pts.map(([x, y]) => x * nx + y * ny)) + p.ecart;
    // réflexion par la droite {X·n = d} : X' = X - 2 (X·n - d) n
    const m = [1 - 2 * nx * nx, -2 * nx * ny, -2 * nx * ny, 1 - 2 * ny * ny, 2 * d * nx, 2 * d * ny];
    const c = _copier(source, `${gid}_r1`);
    _prefixer(c, `matrix(${m.map(nbc).join(" ")})`);
    out.push(c);
  }
  if (out.length + 1 > MAX_COPIES) throw new Error(T("vectorlab.repeter.trop", { max: MAX_COPIES }));
  return out;
}
const _empreinte = (g) => JSON.stringify([g.enfants[0], g.repetition.mode, g.repetition.params]);

function _reconstruire(g) {
  const source = g.enfants[0];
  g.enfants = [source, ..._copies(g.id, g.repetition.mode, g.repetition.params, source)];
  g.repetition.empreinte = _empreinte(g);
}

/* ── chercher ── */
function _trouver(doc, id) {
  for (const c of doc.calques) {
    const r = (function v(objs, parent) {
      for (const o of objs || []) {
        if (o.id === id) return { objet: o, calque: c, parent };
        if (o.type === "groupe") { const x = v(o.enfants, o); if (x) return x; }
      }
      return null;
    })(c.objets, null);
    if (r) return r;
  }
  return null;
}
function _idsPris(doc) {
  const pris = new Set();
  const v = (objs) => { for (const o of objs || []) { pris.add(o.id); if (o.type === "groupe") v(o.enfants); } };
  for (const c of doc.calques) v(c.objets);
  for (const s of Object.values(doc.symboles || {})) v(s.objets);
  return pris;
}
function _source_ids(doc) {
  const pris = _idsPris(doc);
  let n = 1;
  return () => { while (pris.has("o" + n)) n++; pris.add("o" + n); return "o" + n; };
}

/* ── T1 (t450) Objet › Répétition › Radiale ; T2 (t451) › Grille ; T3 (t452) › Miroir ──
   La sélection (objets du premier niveau d'un calque déverrouillé) devient la SOURCE — plusieurs objets sont
   d'abord groupés — et le groupe vivant prend la place du plus haut d'entre eux. -> id du groupe vivant */
export function op_repeter(doc, ids, mode, params = {}) {
  if (!MODES.has(mode)) throw new Error(T("vectorlab.repeter.mode", { mode }));
  const voulu = new Set(ids || []);
  if (!voulu.size) throw new Error(T("vectorlab.repeter.rien"));
  const cibles = [];
  for (const c of doc.calques) {
    for (const o of c.objets) if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
  }
  if (cibles.length !== voulu.size) {
    const genere = [...voulu].some((id) => { const t = _trouver(doc, id); return t && t.objet.genere; });
    throw new Error(T(genere ? "vectorlab.repeter.copie_generee" : "vectorlab.repeter.rien"));
  }
  if (cibles.some((t) => t.calque.verrou)) throw new Error(T("vectorlab.repeter.verrou"));
  // tout se calcule AVANT de muter
  const neuf = _source_ids(doc);
  const objs = cibles.map((t) => t.objet);
  const source = objs.length === 1 ? objs[0] : { id: neuf(), type: "groupe", style: {}, enfants: objs };
  if (!_boite(source)) throw new Error(T("vectorlab.repeter.source_type"));
  const p = _params(mode, params, source);
  const gid = neuf();
  const g = { id: gid, type: "groupe", style: {}, repetition: { mode, params: p, empreinte: "" }, enfants: [source] };
  _reconstruire(g);
  // muter : le groupe à la place du plus haut, les autres retirés
  const haut = cibles[cibles.length - 1];
  const idx = haut.calque.objets.indexOf(haut.objet);
  haut.calque.objets.splice(idx, 1, g);
  for (const t of cibles.slice(0, -1)) t.calque.objets.splice(t.calque.objets.indexOf(t.objet), 1);
  return gid;
}

// Options de répétition : les réglages fournis remplacent les anciens, les autres restent
export function op_repetition_regler(doc, id, params = {}) {
  const t = _trouver(doc, id);
  if (!t) throw new Error(T("vectorlab.repeter.introuvable", { id }));
  const g = t.objet;
  if (!g.repetition) throw new Error(T("vectorlab.repeter.pas_repetition", { id }));
  const p = _params(g.repetition.mode, params, g.enfants[0], g.repetition.params);
  const essai = { ...g, repetition: { ...g.repetition, params: p } };
  _reconstruire(essai);
  g.repetition = essai.repetition;
  g.enfants = essai.enfants;
}

/* ══ T4 (t453) Objet › Fusion › Créer ══
   Une fusion est un GROUPE { fusion_vive: { mode, etapes, pas, empreinte }, enfants: [A, ...intermédiaires, B] } :
   A (le plus bas) et B (le plus haut) restent éditables, les intermédiaires sont des chemins générés d'ids
   `<groupe>_f<k>`, en coordonnées du document (le transform de A et B est déjà appliqué). Recalcul par empreinte
   (A, B et réglages), comme les répétitions. */
const TYPES_FUSION = new Set(["rect", "ellipse", "path", "forme"]);
const MODES_FUSION = new Set(["etapes", "distance", "couleur"]);
const MAX_INTER = 200;

// couleurs : #rgb ou #rrggbb seulement (un dégradé, un motif, une couleur globale ne s'interpolent pas)
function _rvb(c) {
  const m = typeof c === "string" && /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(c.trim());
  if (!m) return null;
  const h = m[1].length === 3 ? m[1].split("").map((x) => x + x).join("") : m[1];
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}
const _hexDe = (v) => "#" + v.map((x) => Math.round(x).toString(16).padStart(2, "0")).join("");
// le style d'un intermédiaire : celui de A avant mi-chemin, celui de B ensuite, puis couleurs et nombres interpolés
function _styleFusion(sa = {}, sb = {}, t) {
  const s = JSON.parse(JSON.stringify(t < 0.5 ? sa : sb));
  for (const k of ["fond", "contour"]) {
    const a = _rvb(sa[k]), b = _rvb(sb[k]);
    if (a && b) s[k] = _hexDe(a.map((v, i) => v + (b[i] - v) * t));
  }
  for (const k of ["epaisseur", "opacite"]) {
    const a = Number(sa[k]), b = Number(sb[k]);
    if (sa[k] !== undefined && sb[k] !== undefined && Number.isFinite(a) && Number.isFinite(b)) {
      s[k] = Math.round((a + (b - a) * t) * 1e6) / 1e6;
    }
  }
  return s;
}

/* ── géométrie : les sous-chemins de A et B mis en correspondance point à point ── */
function _sousChemins(o) {
  return polylignes_objet(o).filter((l) => l.points.length >= 2).map((l) => {
    const p = l.points.map(([x, y]) => [x, y]);
    const a = p[0], z = p[p.length - 1];
    if (l.ferme && p.length > 2 && Math.abs(a[0] - z[0]) < 1e-9 && Math.abs(a[1] - z[1]) < 1e-9) p.pop();
    return { ferme: !!l.ferme, points: p };
  });
}
function _aireSignee(p) {
  let s = 0;
  for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; s += a[0] * b[1] - b[0] * a[1]; }
  return s / 2;
}
// N points également espacés le long du tracé (fermé : le segment de fermeture compte)
function _reechantillonner(p, ferme, N) {
  const q = ferme ? p.concat([p[0]]) : p;
  const cum = [0];
  for (let i = 1; i < q.length; i++) cum.push(cum[i - 1] + Math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]));
  const L = cum[cum.length - 1];
  if (!(L > 0)) return Array.from({ length: N }, () => [p[0][0], p[0][1]]);
  const pas = ferme ? L / N : L / (N - 1);
  const out = [];
  let j = 1;
  for (let k = 0; k < N; k++) {
    const s = Math.min(k * pas, L);
    while (j < q.length - 1 && cum[j] < s) j++;
    const u = cum[j] > cum[j - 1] ? (s - cum[j - 1]) / (cum[j] - cum[j - 1]) : 0;
    out.push([q[j - 1][0] + (q[j][0] - q[j - 1][0]) * u, q[j - 1][1] + (q[j][1] - q[j - 1][1]) * u]);
  }
  return out;
}
const _ecart2 = (a, b, s) => { let e = 0; const n = a.length; for (let i = 0; i < n; i++) { const p = a[i], q = b[(i + s) % n]; e += (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2; } return e; };
// B mis dans le sens de A, et (fermé) tourné pour que chaque point vise son plus proche partenaire
function _aligner(a, b, ferme) {
  if (!ferme) return _ecart2(a, b.slice().reverse(), 0) < _ecart2(a, b, 0) ? b.slice().reverse() : b;
  let q = Math.sign(_aireSignee(a)) * Math.sign(_aireSignee(b)) < 0 ? b.slice().reverse() : b;
  let meilleur = 0, min = Infinity;
  for (let s = 0; s < q.length; s++) { const e = _ecart2(a, q, s); if (e < min - 1e-9) { min = e; meilleur = s; } }
  return q.slice(meilleur).concat(q.slice(0, meilleur));
}
const _centre = (p) => [p.reduce((s, q) => s + q[0], 0) / p.length, p.reduce((s, q) => s + q[1], 0) / p.length];
function _paires(A, B) {
  const la = _sousChemins(A), lb = _sousChemins(B);
  const out = [];
  for (let i = 0; i < Math.max(la.length, lb.length); i++) {
    // un sous-chemin sans partenaire se réduit vers son propre centre
    const a = la[i] || { ferme: lb[i].ferme, points: lb[i].points.map(() => _centre(lb[i].points)) };
    const b = lb[i] || { ferme: la[i].ferme, points: la[i].points.map(() => _centre(la[i].points)) };
    const ferme = a.ferme || b.ferme;
    let pa = a.points, pb = b.points;
    if (pa.length !== pb.length) {                 // sommets en nombre différent : rééchantillonnés
      const N = Math.max(32, pa.length, pb.length);
      pa = _reechantillonner(pa, ferme, N); pb = _reechantillonner(pb, ferme, N);
    }
    out.push({ ferme, a: pa, b: _aligner(pa, pb, ferme) });
  }
  return out;
}
function _dInter(paires, t) {
  return paires.map(({ ferme, a, b }) => "M" + a.map((p, i) =>
    `${nbc(p[0] + (b[i][0] - p[0]) * t)} ${nbc(p[1] + (b[i][1] - p[1]) * t)}`).join(" L") + (ferme ? " Z" : "")).join(" ");
}

function _paramsFusion(p = {}, base = {}) {
  const v = { ...base, ...p };
  const mode = v.mode === undefined ? "etapes" : v.mode;
  if (!MODES_FUSION.has(mode)) throw new Error(T("vectorlab.fusion.mode", { mode }));
  return {
    mode,
    etapes: _entier(v.etapes === undefined ? 5 : v.etapes, 1, MAX_INTER, "vectorlab.fusion.etapes"),
    pas: _positif(v.pas === undefined ? 20 : v.pas, "vectorlab.fusion.pas"),
  };
}
// le nombre d'intermédiaires : fixé (étapes), un tous les `pas` px entre les centres (distance), ou assez pour que
// deux voisins ne diffèrent pas de plus de 4 niveaux sur un canal (couleur lissée) ; 1 à 200
function _nombreInter(f, A, B) {
  let n = f.etapes;
  if (f.mode === "distance") {
    const a = _boite(A), b = _boite(B);
    n = Math.round(Math.hypot(b.x + b.w / 2 - a.x - a.w / 2, b.y + b.h / 2 - a.y - a.h / 2) / f.pas) - 1;
  } else if (f.mode === "couleur") {
    let delta = 0;
    for (const k of ["fond", "contour"]) {
      const a = _rvb((A.style || {})[k]), b = _rvb((B.style || {})[k]);
      if (a && b) for (let i = 0; i < 3; i++) delta = Math.max(delta, Math.abs(a[i] - b[i]));
    }
    n = Math.ceil(delta / 4) - 1;
  }
  return Math.min(MAX_INTER, Math.max(1, n));
}
const _empreinteFusion = (g) => JSON.stringify([g.enfants[0], g.enfants[g.enfants.length - 1], g.fusion_vive.mode, g.fusion_vive.etapes, g.fusion_vive.pas]);
function _reconstruireFusion(g) {
  const A = g.enfants[0], B = g.enfants[g.enfants.length - 1];
  const paires = _paires(A, B);
  const n = _nombreInter(g.fusion_vive, A, B);
  const inter = [];
  for (let k = 1; k <= n; k++) {
    const t = k / (n + 1);
    inter.push({ id: `${g.id}_f${k}`, type: "path", d: _dInter(paires, t), style: _styleFusion(A.style, B.style, t), genere: true });
  }
  g.enfants = [A, ...inter, B];
  g.fusion_vive.empreinte = _empreinteFusion(g);
}

// A et B : exactement deux formes (rect, ellipse, chemin, forme) du premier niveau d'un calque déverrouillé ;
// le groupe prend la place de la plus haute. -> id du groupe
export function op_fusionner(doc, ids, opts = {}) {
  const voulu = new Set(ids || []);
  if (voulu.size !== 2) throw new Error(T("vectorlab.fusion.deux"));
  const cibles = [];
  for (const c of doc.calques) for (const o of c.objets) if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
  if (cibles.length !== 2) {
    const genere = [...voulu].some((id) => { const t = _trouver(doc, id); return t && t.objet.genere; });
    throw new Error(T(genere ? "vectorlab.repeter.copie_generee" : "vectorlab.fusion.deux"));
  }
  if (cibles.some((t) => t.calque.verrou)) throw new Error(T("vectorlab.repeter.verrou"));
  if (cibles.some((t) => !TYPES_FUSION.has(t.objet.type))) throw new Error(T("vectorlab.fusion.type"));
  const f = _paramsFusion(opts);
  const g = { id: _source_ids(doc)(), type: "groupe", style: {}, fusion_vive: { ...f, empreinte: "" },
              enfants: [cibles[0].objet, cibles[1].objet] };
  _reconstruireFusion(g);                          // tout se calcule AVANT de muter
  const haut = cibles[1];
  haut.calque.objets.splice(haut.calque.objets.indexOf(haut.objet), 1, g);
  cibles[0].calque.objets.splice(cibles[0].calque.objets.indexOf(cibles[0].objet), 1);
  return g.id;
}

/* ── vivant : appelé par derives_rafraichir après chaque commande ── */
export function vivants_d2_rafraichir(doc) {
  let n = 0;
  // les répétitions les plus profondes d'abord : une répétition de répétition lit une source déjà à jour
  const v = (objs) => {
    for (const o of objs || []) {
      if (o.type !== "groupe") continue;
      v(o.enfants);
      if (o.fusion_vive && Array.isArray(o.enfants) && o.enfants.length >= 2) {
        // A ou B disparu (le bout est un intermédiaire) : dernier état gardé
        if (o.enfants[0].genere || o.enfants[o.enfants.length - 1].genere) continue;
        if (_empreinteFusion(o) === o.fusion_vive.empreinte) continue;
        try {
          const essai = { ...o, fusion_vive: { ...o.fusion_vive } };
          _reconstruireFusion(essai);
          o.enfants = essai.enfants;
          o.fusion_vive = essai.fusion_vive;
          n++;
        } catch (e) { /* forme devenue impossible à fusionner : dernier état gardé */ }
        continue;
      }
      if (!o.repetition || !Array.isArray(o.enfants) || !o.enfants.length) continue;
      if (o.enfants[0].genere) continue;            // la source a disparu : dernier état gardé
      if (_empreinte(o) === o.repetition.empreinte) continue;
      try {
        const essai = { ...o, repetition: { ...o.repetition } };
        _reconstruire(essai);
        o.enfants = essai.enfants;
        o.repetition = essai.repetition;
        n++;
      } catch (e) {
        /* recalcul impossible (source devenue sans géométrie…) : dernier état gardé, retenté au prochain */
      }
    }
  };
  for (const c of doc.calques) v(c.objets);
  return n;
}

// Décomposer : la répétition ou la fusion redevient un groupe ordinaire ; ses copies et intermédiaires reçoivent
// des ids o<n> neufs
export function repetition_decomposer(doc, g) {
  const neuf = _source_ids(doc);
  const renommer = (x) => {
    x.id = neuf();
    if (x.type === "groupe") {
      for (const e of x.enfants || []) renommer(e);
      if (x.clip && x.enfants && x.enfants[0]) x.clip = x.enfants[0].id;
    }
  };
  for (const e of g.enfants.slice(1)) { if (e.genere) { delete e.genere; renommer(e); } }
  delete g.repetition;
  delete g.fusion_vive;
}
