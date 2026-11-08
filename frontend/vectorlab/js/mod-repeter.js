// mod-repeter.js — lot D2 « Répéter et fusionner » (spec 2026-11-08-illustrator-vectorlab-inventaire.md, plan
// 2026-11-08-vectorlab-d2-repeter-fusionner.md) : les RÉPÉTITIONS VIVANTES d'Illustrator.
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

/* ── vivant : appelé par derives_rafraichir après chaque commande ── */
export function vivants_d2_rafraichir(doc) {
  let n = 0;
  // les répétitions les plus profondes d'abord : une répétition de répétition lit une source déjà à jour
  const v = (objs) => {
    for (const o of objs || []) {
      if (o.type !== "groupe") continue;
      v(o.enfants);
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

// Décomposer : la répétition redevient un groupe ordinaire ; ses copies reçoivent des ids o<n> neufs
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
}
