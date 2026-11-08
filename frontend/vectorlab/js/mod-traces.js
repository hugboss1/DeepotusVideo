// mod-traces.js — lot D1 « Tracés » (spec 2026-11-08-illustrator-vectorlab-inventaire.md) : les commandes de
// tracé reprises d'Illustrator, en opérations PURES sur le modèle. Règle de mod-bool : tout se CALCULE avant de
// muter — un refus ne laisse aucune trace ; l'UI les appelle par VL.executer (annulation comprise).
import { T } from "./mod-i18n.js";
import { contour_en_multi, multi_vers_d, cibles_b, polylignes_objet } from "./mod-bool.js";
import { chemin_parser, chemin_serialiser } from "./mod-doc.js";
import { forme_d } from "./mod-formes.js";
import { simplifier } from "./mod-crayon.js";
import { op_noeuds_aligner } from "./mod-noeuds.js";

// les types dont le contour se vectorise (un texte se vectorise d'abord par Texte › Convertir en courbes ; un
// groupe porte des enfants de styles différents : dégrouper d'abord)
const TYPES_TRACES = new Set(["rect", "ellipse", "path", "forme"]);

// une SOURCE d'ids neufs : les ids pris (groupes et enfants compris) relevés UNE fois avant toute mutation
function _idsNeufs(doc) {
  const pris = new Set();
  for (const c of doc.calques) (function v(objs) { for (const o of objs) { pris.add(o.id); if (o.type === "groupe") v(o.enfants || []); } })(c.objets);
  let n = 1;
  return () => { while (pris.has("o" + n)) n++; pris.add("o" + n); return "o" + n; };
}

function _traitPlein(o) {
  const s = o.style || {};
  return TYPES_TRACES.has(o.type) && !!s.contour && s.contour !== "none" && Number(s.epaisseur) > 0 && !s.pointilles;
}

// le style d'un objet SANS son trait principal (fond, opacité, effets, contours d'Apparence + gardés)
function _sansTrait(style) {
  const s = { ...(style || {}) };
  s.contour = "none";
  delete s.epaisseur; delete s.joint; delete s.pointilles;
  return s;
}

/* ── T1 (t422) Objet › Tracé › Vectoriser le contour ──
   Le trait principal devient un chemin plein de sa couleur (jointures et bouts RONDS : ceux de notre rendu,
   contour_en_multi) en coordonnées du document — le transform de l'objet est déjà appliqué. Un objet sans fond
   est remplacé par ce chemin ; un objet rempli devient un groupe [fond sans trait, contour vectorisé], à sa place,
   comme dans Illustrator. Les objets sans trait plein sont laissés tels quels ; si AUCUN n'en a : refus.
   -> les ids posés (chemins ou groupes), dans l'ordre de la sélection en peinture */
export function op_contour_vectoriser(doc, ids) {
  const cibles = cibles_b(doc, ids).filter((c) => _traitPlein(c.objet));
  if (!cibles.length) throw new Error(T("vectorlab.traces.sans_contour"));
  // tout se calcule d'abord : un aplatissement qui lève ne laisse aucune trace
  const calculs = cibles.map((c) => ({ ...c, d: multi_vers_d(contour_en_multi(c.objet)) }));
  if (calculs.some((c) => !c.d)) throw new Error(T("vectorlab.traces.sans_contour"));
  const neuf = _idsNeufs(doc);
  const poses = [];
  for (const c of calculs) {
    const s0 = c.objet.style || {};
    const style = { ..._sansTrait(s0), fond: s0.contour };
    delete style.contours;
    const chemin = { id: neuf(), type: "path", d: c.d, style };
    if (c.objet.nom) chemin.nom = c.objet.nom;
    const rempli = s0.fond !== undefined && s0.fond !== "none";
    let pose = chemin;
    if (rempli) {
      const fond = { ...c.objet, style: _sansTrait(s0) };
      pose = { id: neuf(), type: "groupe", style: {}, enfants: [fond, chemin] };
    }
    const i = c.calque.objets.indexOf(c.objet);
    c.calque.objets.splice(i, 1, pose);
    poses.push(pose.id);
  }
  return poses;
}

/* ── T2 (t423) Objet › Tracé › Simplifier… ──
   Le tracé est aplati (0,25 px) dans SES coordonnées (le transform reste porté par l'objet), réduit par
   Ramer–Douglas–Peucker (simplifier de mod-crayon) à une tolérance tirée de la précision, puis relissé en cubiques
   qui passent PAR les points gardés (Catmull-Rom). Un point dont la direction tourne de plus de ANGLE_COIN degrés
   reste un ANGLE : ses deux segments partent droits, comme le « seuil d'angle » d'Illustrator. `droites` rend des
   segments seulement. Jamais plus de points que l'original : sans gain, l'objet est laissé tel quel. */
const ANGLE_COIN = 60;
const TYPES_SIMPLIFIABLES = new Set(["path", "forme", "rect", "ellipse"]);

// points d'ancrage d'un d : par sous-chemin le M et chaque fin de segment ; un retour EXPLICITE au départ avant Z
// ne compte pas (c'est le même point)
export function compter_ancres(d) {
  let n = 0, sous = [], ferme = false;
  const fin = () => {
    if (ferme && sous.length > 1) {
      const a = sous[0], b = sous[sous.length - 1];
      if (Math.abs(a[0] - b[0]) < 1e-6 && Math.abs(a[1] - b[1]) < 1e-6) sous.pop();
    }
    n += sous.length; sous = []; ferme = false;
  };
  for (const g of chemin_parser(d)) {
    if (g.c === "M") { fin(); sous.push(g.p.slice(0, 2)); }
    else if (g.c === "Z") { ferme = true; fin(); }
    else sous.push(g.p.slice(-2));
  }
  fin();
  return n;
}

function _ancresAvant(o) {
  if (o.type === "path") return compter_ancres(o.d);
  if (o.type === "forme") return compter_ancres(forme_d(o));
  return 4;                                                   // rect, ellipse
}

const _egaux = (a, b) => Math.abs(a[0] - b[0]) < 1e-9 && Math.abs(a[1] - b[1]) < 1e-9;

// tourne de plus de ANGLE_COIN degrés en p (venant de a, allant vers b) ?
function _estCoin(a, p, b) {
  const ux = p[0] - a[0], uy = p[1] - a[1], vx = b[0] - p[0], vy = b[1] - p[1];
  const nu = Math.hypot(ux, uy), nv = Math.hypot(vx, vy);
  if (!nu || !nv) return true;
  const c = Math.max(-1, Math.min(1, (ux * vx + uy * vy) / (nu * nv)));
  return Math.acos(c) * 180 / Math.PI > ANGLE_COIN;
}

// une polyligne réduite → segments (M, L/C…, Z)
function _segments(pts, ferme, droites) {
  const n = pts.length, segs = [{ c: "M", p: [...pts[0]] }];
  const nSeg = ferme ? n : n - 1;
  const P = (i) => pts[((i % n) + n) % n];
  const coin = (i) => (!ferme && (i === 0 || i === n - 1)) || _estCoin(P(i - 1), P(i), P(i + 1));
  for (let i = 0; i < nSeg; i++) {
    const p1 = P(i), p2 = P(i + 1), c1Coin = coin(i), c2Coin = coin((i + 1) % n === 0 && !ferme ? n - 1 : i + 1);
    if (droites || (c1Coin && c2Coin)) { segs.push({ c: "L", p: [...p2] }); continue; }
    // voisins : à un angle, le voisin est le MIROIR de l'autre extrémité (tangente = la corde)
    const p0 = c1Coin ? [2 * p1[0] - p2[0], 2 * p1[1] - p2[1]] : P(i - 1);
    const p3 = c2Coin ? [2 * p2[0] - p1[0], 2 * p2[1] - p1[1]] : P(i + 2);
    const k = 1 / 6;
    segs.push({ c: "C", p: [p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k,
                            p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k, p2[0], p2[1]] });
  }
  if (ferme) segs.push({ c: "Z", p: [] });
  return segs;
}

// -> { d, avant, apres } ; d = null quand il n'y a rien à gagner (précision 100 %, ou pas moins de points)
export function simplifier_apercu(objet, { precision = 50, droites = false } = {}) {
  const avant = _ancresAvant(objet);
  const p = Math.max(0, Math.min(100, Number(precision)));
  if (!TYPES_SIMPLIFIABLES.has(objet.type) || p >= 100) return { d: null, avant, apres: avant };
  const local = { ...objet }; delete local.transform;          // la géométrie reste dans les coordonnées de l'objet
  const lignes = polylignes_objet(local);
  const tous = lignes.flatMap((l) => l.points);
  if (!tous.length) return { d: null, avant, apres: avant };
  const xs = tous.map((q) => q[0]), ys = tous.map((q) => q[1]);
  const diag = Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
  const tol = Math.max(0.05, (100 - p) / 100 * 0.04 * diag);
  const segs = [];
  for (const l of lignes) {
    let pts = l.points.filter((q, i, a) => i === 0 || !_egaux(q, a[i - 1]));
    if (l.ferme && pts.length > 1 && _egaux(pts[0], pts[pts.length - 1])) pts.pop();
    let r = l.ferme ? simplifier([...pts, pts[0]], tol).slice(0, -1) : simplifier(pts, tol);
    if (r.length < (l.ferme ? 3 : 2)) return { d: null, avant, apres: avant };   // le sous-chemin s'effondrerait
    segs.push(..._segments(r, l.ferme, droites));
  }
  const d = chemin_serialiser(segs);
  const apres = compter_ancres(d);
  return apres < avant ? { d, avant, apres } : { d: null, avant, apres: avant };
}

// -> ids simplifiés ; refus traduit (aucune trace) si rien n'est simplifiable ou si rien n'y gagne
export function op_simplifier(doc, ids, opts = {}) {
  const cibles = cibles_b(doc, ids).filter((c) => TYPES_SIMPLIFIABLES.has(c.objet.type));
  if (!cibles.length) throw new Error(T("vectorlab.traces.simplifier_rien"));
  const calculs = cibles.map((c) => ({ ...c, r: simplifier_apercu(c.objet, opts) })).filter((c) => c.r.d);
  if (!calculs.length) throw new Error(T("vectorlab.traces.simplifier_deja"));
  for (const c of calculs) {
    const o = c.objet;
    const neuf = o.type === "path" ? { ...o, d: c.r.d }
      : { id: o.id, type: "path", d: c.r.d, style: { ...(o.style || {}) },
          ...(o.nom ? { nom: o.nom } : {}), ...(o.transform ? { transform: o.transform } : {}) };
    c.calque.objets.splice(c.calque.objets.indexOf(o), 1, neuf);
  }
  return calculs.map((c) => c.objet.id);
}

/* ── T3 (t424) Objet › Tracé › Ajouter des points d'ancrage ──
   Un point au MILIEU de chaque segment (de Casteljau à t = 0,5 : la forme ne bouge pas), y compris le segment de
   fermeture implicite d'un sous-chemin fermé ; un retour explicite au départ avant Z (segment nul) n'en reçoit pas.
   Rectangle, ellipse et forme paramétrique deviennent d'abord des chemins (id, nom, style, transform gardés).
   « Supprimer des points d'ancrage » n'est pas ici : c'est la suppression LISSE de l'outil Nœud (noeud_supprimer_lisse),
   branchée au menu en T9. */
const KAPPA = 0.5522847498;

function _dDe(o) {
  if (o.type === "path") return o.d;
  if (o.type === "forme") return forme_d(o);
  if (o.type === "rect") {
    const { x, y, w, h } = o;
    return chemin_serialiser([{ c: "M", p: [x, y] }, { c: "L", p: [x + w, y] }, { c: "L", p: [x + w, y + h] },
                              { c: "L", p: [x, y + h] }, { c: "Z", p: [] }]);
  }
  if (o.type === "ellipse") {
    const { cx, cy, rx, ry } = o, kx = rx * KAPPA, ky = ry * KAPPA;
    return chemin_serialiser([{ c: "M", p: [cx + rx, cy] },
      { c: "C", p: [cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry] },
      { c: "C", p: [cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy] },
      { c: "C", p: [cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry] },
      { c: "C", p: [cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy] }, { c: "Z", p: [] }]);
  }
  return null;
}

// les segments d'un d, chacun coupé en son milieu
export function points_ajouter_d(d) {
  const segs = chemin_parser(d), out = [];
  let depart = null, cur = null;
  const m = (a, b) => (a + b) / 2;
  for (const g of segs) {
    if (g.c === "M") { out.push(g); depart = cur = g.p.slice(0, 2); continue; }
    if (g.c === "Z") {
      if (cur && depart && !_egaux(cur, depart)) out.push({ c: "L", p: [m(cur[0], depart[0]), m(cur[1], depart[1])] });
      out.push(g); cur = depart; continue;
    }
    const [x0, y0] = cur;
    if (g.c === "L") {
      out.push({ c: "L", p: [m(x0, g.p[0]), m(y0, g.p[1])] }, g);
    } else if (g.c === "C") {
      const [x1, y1, x2, y2, x3, y3] = g.p;
      const ax = m(x0, x1), ay = m(y0, y1), bx = m(x1, x2), by = m(y1, y2), cx = m(x2, x3), cy = m(y2, y3);
      const dx = m(ax, bx), dy = m(ay, by), ex = m(bx, cx), ey = m(by, cy);
      out.push({ c: "C", p: [ax, ay, dx, dy, m(dx, ex), m(dy, ey)] }, { c: "C", p: [ex, ey, cx, cy, x3, y3] });
    } else if (g.c === "Q") {
      const [x1, y1, x2, y2] = g.p;
      const ax = m(x0, x1), ay = m(y0, y1), bx = m(x1, x2), by = m(y1, y2);
      out.push({ c: "Q", p: [ax, ay, m(ax, bx), m(ay, by)] }, { c: "Q", p: [bx, by, x2, y2] });
    }
    cur = g.p.slice(-2);
  }
  return chemin_serialiser(out);
}

// -> ids modifiés ; refus traduit (aucune trace) si la sélection ne contient aucun tracé ni forme
export function op_points_ajouter(doc, ids) {
  const cibles = cibles_b(doc, ids).filter((c) => TYPES_SIMPLIFIABLES.has(c.objet.type));
  if (!cibles.length) throw new Error(T("vectorlab.traces.points_rien"));
  const calculs = cibles.map((c) => ({ ...c, d: points_ajouter_d(_dDe(c.objet)) }));
  for (const c of calculs) {
    const o = c.objet;
    const neuf = o.type === "path" ? { ...o, d: c.d }
      : { id: o.id, type: "path", d: c.d, style: { ...(o.style || {}) },
          ...(o.nom ? { nom: o.nom } : {}), ...(o.transform ? { transform: o.transform } : {}) };
    c.calque.objets.splice(c.calque.objets.indexOf(o), 1, neuf);
  }
  return calculs.map((c) => c.objet.id);
}

/* ── T4 (t425) Objet › Tracé › Moyenne… ──
   Les nœuds choisis d'UN chemin vont à leur position moyenne, comme dans Illustrator : « horizontale » = même y
   (sur une ligne horizontale), « verticale » = même x, « deux » = au barycentre. Les poignées suivent leur nœud.
   C'est l'alignement au centre de mod-noeuds (centreV / centreH), qui refuse lui-même moins de deux nœuds. */
const _MOYENNE = { horizontale: ["centreV"], verticale: ["centreH"], deux: ["centreH", "centreV"] };

export function op_noeuds_moyenne(doc, id, indices, axe) {
  const modes = _MOYENNE[axe];
  if (!modes) throw new Error(`moyenne : axe inconnu ${axe}`);
  for (const m of modes) op_noeuds_aligner(doc, id, indices, m);
}

/* ── T5 (t426) Objet › Tracé › Nettoyer… ──
   Sur tout le document (calques et objets verrouillés exceptés), retire au choix :
     isoles      un chemin sans aucun segment (seulement des M / Z) ;
     invisibles  un tracé ou une forme sans fond ET sans contour (contour none ou épaisseur 0), sans contour
                 d'Apparence + ;
     textesVides un texte, un cadre ou un texte sur chemin dont le contenu n'a que des blancs.
   PROTÉGÉS : le guide d'un texte sur chemin (textechemin.chemin) et la source d'un contour vivant (derive.source),
   souvent invisibles par choix ; le contenu d'un groupe écrêté (le masque est fait pour ne pas se peindre). Un
   groupe que le nettoyage vide part avec. Rien à retirer → refus traduit (VL.executer ne garde alors aucune trace).
   -> { isoles, invisibles, textesVides } */
const _TRACES_FORMES = new Set(["path", "rect", "ellipse", "forme"]);
const _TEXTES = new Set(["texte", "cadre", "textechemin"]);
const _sansCouleur = (v) => v === undefined || v === null || v === "" || v === "none";

function _isole(o) {
  if (o.type !== "path") return false;
  try { return chemin_parser(o.d).every((g) => g.c === "M" || g.c === "Z"); } catch (e) { return false; }
}
function _invisible(o) {
  if (!_TRACES_FORMES.has(o.type)) return false;
  const s = o.style || {};
  const trait = !_sansCouleur(s.contour) && !(s.epaisseur !== undefined && Number(s.epaisseur) <= 0);
  return _sansCouleur(s.fond) && !trait && !(Array.isArray(s.contours) && s.contours.length);
}
const _texteVide = (o) => _TEXTES.has(o.type) && !String(o.contenu || "").trim();

export function op_nettoyer(doc, { isoles = true, invisibles = true, textesVides = true } = {}) {
  const proteges = new Set();
  for (const c of doc.calques) (function v(l) { for (const o of l) {
    if (o.type === "textechemin" && o.chemin) proteges.add(o.chemin);
    if (o.derive && o.derive.source) proteges.add(o.derive.source);
    if (o.type === "groupe") v(o.enfants || []);
  } })(c.objets);
  const compte = { isoles: 0, invisibles: 0, textesVides: 0 };
  // une liste nettoyée, calculée SANS muter (null = inchangée)
  const nettoyer = (liste) => {
    let change = false;
    const out = [];
    for (const o of liste) {
      if (o.verrou || proteges.has(o.id)) { out.push(o); continue; }
      if (isoles && _isole(o)) { compte.isoles++; change = true; continue; }
      if (invisibles && _invisible(o)) { compte.invisibles++; change = true; continue; }
      if (textesVides && _texteVide(o)) { compte.textesVides++; change = true; continue; }
      if (o.type === "groupe" && o.clip === undefined) {
        const enf = nettoyer(o.enfants || []);
        if (enf) {
          change = true;
          if (enf.length) out.push({ ...o, enfants: enf });
          continue;
        }
      }
      out.push(o);
    }
    return change ? out : null;
  };
  const neufs = doc.calques.map((c) => (c.verrou ? null : nettoyer(c.objets)));
  if (!compte.isoles && !compte.invisibles && !compte.textesVides) throw new Error(T("vectorlab.traces.nettoyer_rien"));
  doc.calques.forEach((c, k) => { if (neufs[k]) c.objets = neufs[k]; });
  return compte;
}
