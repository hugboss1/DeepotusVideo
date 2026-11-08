// mod-traces.js — lot D1 « Tracés » (spec 2026-11-08-illustrator-vectorlab-inventaire.md) : les commandes de
// tracé reprises d'Illustrator, en opérations PURES sur le modèle. Règle de mod-bool : tout se CALCULE avant de
// muter — un refus ne laisse aucune trace ; l'UI les appelle par VL.executer (annulation comprise).
import { T } from "./mod-i18n.js";
import { contour_en_multi, multi_vers_d, cibles_b, polylignes_objet, aplatir_objet, versMulti, aire_multi, martinez }
  from "./mod-bool.js";
import { chemin_parser, chemin_serialiser, op_guide_ajouter } from "./mod-doc.js";
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
    if (o.fusion_vive && o.fusion_vive.trajectoire) proteges.add(o.fusion_vive.trajectoire);   // t454 : invisible par choix
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

/* ── T6 (t427) Objet › Tracé › Diviser les objets en dessous ──
   Le tracé idCouteau découpe chaque objet REMPLI (tracé ou forme, non verrouillé) peint SOUS lui — calques du
   dessous compris — puis disparaît, comme dans Illustrator :
     couteau fermé : chaque objet touché devient ses morceaux DEDANS et DEHORS (sans jour entre eux) ;
     couteau ouvert : l'objet est coupé le long du trait (bande de 0,05 px, invisible).
   Un objet que le couteau ne coupe pas (pas touché, ou entièrement dedans) reste tel quel. Les morceaux sont des
   chemins en coordonnées du document (transform appliqué), au style de leur objet, à sa place dans la pile. Les
   objets non remplis, textes, groupes et images ne sont pas découpés. -> ids des morceaux */
const BANDE_COUTEAU = 0.05;
const AIRE_MIN = 0.01;

export function op_diviser_dessous(doc, idCouteau) {
  let ci = -1, oi = -1;
  doc.calques.forEach((c, k) => { if (ci < 0 && !c.verrou) { const i = c.objets.findIndex((o) => o.id === idCouteau); if (i >= 0) { ci = k; oi = i; } } });
  const couteau = ci >= 0 ? doc.calques[ci].objets[oi] : null;
  if (!couteau || couteau.verrou || !TYPES_SIMPLIFIABLES.has(couteau.type)) throw new Error(T("vectorlab.traces.diviser_couteau"));
  const mz = martinez();
  const lignes = polylignes_objet(couteau);
  const ferme = lignes.length > 0 && lignes.every((l) => l.ferme);
  const coupe = ferme ? versMulti(aplatir_objet(couteau))
    : contour_en_multi({ ...couteau, style: { ...(couteau.style || {}), epaisseur: BANDE_COUTEAU } });
  const polys = (mp) => (mp || []).filter((poly) => poly && poly.length && aire_multi([poly]) > AIRE_MIN);
  // tout se calcule d'abord : [{ calque, objet, morceaux: [poly…] }]
  const plan = [];
  doc.calques.forEach((c, k) => {
    if (k > ci || c.verrou) return;
    const limite = k === ci ? oi : c.objets.length;
    for (let i = 0; i < limite; i++) {
      const o = c.objets[i];
      const s = o.style || {};
      if (o.verrou || !TYPES_SIMPLIFIABLES.has(o.type) || _sansCouleur(s.fond)) continue;
      const mp = versMulti(aplatir_objet(o));
      let morceaux;
      if (ferme) {
        const dedans = polys(mz.intersection(mp, coupe)), dehors = polys(mz.diff(mp, coupe));
        if (!dedans.length || !dehors.length) continue;           // pas touché, ou entièrement dedans
        morceaux = [...dedans, ...dehors];
      } else {
        morceaux = polys(mz.diff(mp, coupe));
        if (morceaux.length < 2) continue;                          // le trait ne le traverse pas
      }
      plan.push({ calque: c, objet: o, morceaux });
    }
  });
  if (!plan.length) throw new Error(T("vectorlab.traces.diviser_rien"));
  const neuf = _idsNeufs(doc);
  const poses = [];
  for (const { calque, objet, morceaux } of plan) {
    const nouveaux = morceaux.map((poly) => ({ id: neuf(), type: "path", d: multi_vers_d([poly]), style: { ...(objet.style || {}) } }));
    calque.objets.splice(calque.objets.indexOf(objet), 1, ...nouveaux);
    poses.push(...nouveaux.map((o) => o.id));
  }
  const cc = doc.calques[ci];
  cc.objets.splice(cc.objets.indexOf(couteau), 1);
  return poses;
}

/* ── T7 (t428) Objet › Tracé › Lignes et colonnes… ──
   La boîte RÉELLE de l'objet (transform appliqué) devient lignes × colonnes rectangles séparés par des gouttières
   (gouttiereLignes entre deux lignes, gouttiereColonnes entre deux colonnes), au style de l'objet, à sa place dans
   la pile, rangés ligne par ligne ; l'objet disparaît. `reperes` pose un repère sur chaque bord de colonne (v) et de
   ligne (h), sans doubler un repère existant. Pour les planches de cartes. -> ids des cellules */
const _arr = (v) => Math.round(v * 1e6) / 1e6 + 0;

export function op_lignes_colonnes(doc, id, { lignes = 1, colonnes = 1, gouttiereLignes = 0, gouttiereColonnes = 0, reperes = false } = {}) {
  const nL = Number(lignes), nC = Number(colonnes), gL = Number(gouttiereLignes), gC = Number(gouttiereColonnes);
  if (![nL, nC].every((n) => Number.isInteger(n) && n >= 1 && n <= 100)) throw new Error(T("vectorlab.traces.lignes_nombre"));
  const [cible] = cibles_b(doc, [id]);
  const o = cible.objet;
  if (!TYPES_SIMPLIFIABLES.has(o.type)) throw new Error(T("vectorlab.traces.lignes_objet"));
  const pts = aplatir_objet(o).flat();
  const xs = pts.map((q) => q[0]), ys = pts.map((q) => q[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys), W = Math.max(...xs) - x0, H = Math.max(...ys) - y0;
  const w = (W - gC * (nC - 1)) / nC, h = (H - gL * (nL - 1)) / nL;
  if (!(gL >= 0) || !(gC >= 0) || !(w > 0) || !(h > 0)) throw new Error(T("vectorlab.traces.lignes_taille"));
  const neuf = _idsNeufs(doc);
  const cellules = [];
  for (let l = 0; l < nL; l++) for (let c = 0; c < nC; c++) {
    cellules.push({ id: neuf(), type: "rect", x: _arr(x0 + c * (w + gC)), y: _arr(y0 + l * (h + gL)), w: _arr(w), h: _arr(h),
                    style: { ...(o.style || {}) } });
  }
  cible.calque.objets.splice(cible.calque.objets.indexOf(o), 1, ...cellules);
  if (reperes) {
    const poser = (axe, v) => { const g = (doc.guides && doc.guides[axe]) || []; if (!g.some((x) => Math.abs(x - v) < 1e-6)) op_guide_ajouter(doc, axe, v); };
    for (let c = 0; c < nC; c++) { poser("v", _arr(x0 + c * (w + gC))); poser("v", _arr(x0 + c * (w + gC) + w)); }
    for (let l = 0; l < nL; l++) { poser("h", _arr(y0 + l * (h + gL))); poser("h", _arr(y0 + l * (h + gL) + h)); }
  }
  return cellules.map((x) => x.id);
}

/* ── T8 (t429) Pathfinder : les six opérations qui manquaient à op_booleen ──
   Sur la sélection en ordre de PEINTURE (dessous → dessus), transforms appliqués :
     exclusion            XOR de tous ; style de l'objet du dessus, à sa place ;
     soustraction_arriere le dessus moins tous les autres ; style du dessus ;
     decoupage            chaque objet moins tout ce qui est au-dessus de lui (sans fusion) ; contours retirés ;
     fusion               découpage, puis réunion des morceaux de même fond (au plus bas d'entre eux) ;
     recadrage            chaque objet (rogné par ceux d'au-dessus) ∩ l'objet du dessus, qui disparaît ;
     contour              chaque bord coupé là où il croise un autre bord → chemins OUVERTS sans fond, contour 1 px
                          de la couleur de l'ancien fond.
   Chaque objet est remplacé à sa place par ses résultats (ou retiré) ; tout se calcule d'abord. -> ids posés */
const _MODES_PF = new Set(["exclusion", "soustraction_arriere", "decoupage", "fusion", "recadrage", "contour"]);
const _polys = (mp) => (mp || []).filter((poly) => poly && poly.length && aire_multi([poly]) > AIRE_MIN);

// intersection des segments [a b] et [c d] : t sur ab, u sur cd (parallèles : null)
function _inter(a, b, c, d) {
  const rx = b[0] - a[0], ry = b[1] - a[1], sx = d[0] - c[0], sy = d[1] - c[1];
  const den = rx * sy - ry * sx;
  if (Math.abs(den) < 1e-12) return null;
  const qx = c[0] - a[0], qy = c[1] - a[1];
  return { t: (qx * sy - qy * sx) / den, u: (qx * ry - qy * rx) / den };
}

// un anneau fermé coupé aux points où il croise les autres anneaux -> polylignes ouvertes (ou l'anneau entier)
function _decouperAnneau(ring, autres) {
  const suite = [];                                   // [{ p, coupe }]
  for (let k = 0; k < ring.length - 1; k++) {
    const a = ring[k], b = ring[k + 1];
    const ts = [];
    for (const r2 of autres) for (let j = 0; j < r2.length - 1; j++) {
      const x = _inter(a, b, r2[j], r2[j + 1]);
      if (x && x.t >= -1e-9 && x.t < 1 - 1e-9 && x.u >= -1e-9 && x.u <= 1 + 1e-9) ts.push(Math.max(0, x.t));
    }
    ts.sort((p, q) => p - q);
    suite.push({ p: a, coupe: ts.length > 0 && ts[0] < 1e-9 });
    for (const t of ts) if (t >= 1e-9 && !(suite.length && suite[suite.length - 1].t === t)) suite.push({ p: [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], coupe: true, t });
  }
  const i0 = suite.findIndex((e) => e.coupe);
  if (i0 < 0) return [{ points: [...suite.map((e) => e.p), suite[0].p], ferme: true }];
  const tour = [...suite.slice(i0), ...suite.slice(0, i0), suite[i0]];
  const out = [];
  let cur = [tour[0].p];
  for (let k = 1; k < tour.length; k++) {
    cur.push(tour[k].p);
    if (tour[k].coupe) { if (cur.length > 1) out.push({ points: cur, ferme: false }); cur = [tour[k].p]; }
  }
  return out;
}

export function op_pathfinder(doc, ids, mode) {
  if (!_MODES_PF.has(mode)) throw new Error(`pathfinder : mode inconnu ${mode}`);
  const cibles = cibles_b(doc, ids);
  if (cibles.length < 2) throw new Error(T("vectorlab.bool.deux_objets"));
  const mz = martinez();
  const mps = cibles.map((c) => versMulti(aplatir_objet(c.objet)));
  const n = cibles.length, H = n - 1, st = (i) => cibles[i].objet.style || {};
  const reunion = (lst) => lst.reduce((acc, mp) => (acc ? mz.union(acc, mp) : mp), null);
  const remp = new Map();                              // objet -> [{ d, style }]
  const pose = (i, mp, style) => remp.set(cibles[i].objet, [...(remp.get(cibles[i].objet) || []), { d: multi_vers_d(mp), style }]);
  for (const c of cibles) remp.set(c.objet, []);
  const rogne = (i) => (i === H ? mps[i] : mz.diff(mps[i], reunion(mps.slice(i + 1))));
  if (mode === "exclusion" || mode === "soustraction_arriere") {
    const r = mode === "exclusion" ? mps.slice(1).reduce((acc, mp) => mz.xor(acc, mp), mps[0]) : mz.diff(mps[H], reunion(mps.slice(0, H)));
    if (!_polys(r).length) throw new Error(T("vectorlab.bool.resultat_vide"));
    pose(H, _polys(r), { ...st(H) });
  } else if (mode === "decoupage") {
    for (let i = 0; i < n; i++) { const r = _polys(rogne(i)); if (r.length) pose(i, r, _sansTrait(st(i))); }
  } else if (mode === "fusion") {
    const groupes = new Map();                         // fond -> { i (le plus bas), mp }
    for (let i = 0; i < n; i++) {
      const r = _polys(rogne(i)); if (!r.length) continue;
      const cle = JSON.stringify(st(i).fond ?? null), g = groupes.get(cle);
      if (g) g.mp = mz.union(g.mp, r); else groupes.set(cle, { i, mp: r });
    }
    for (const { i, mp } of groupes.values()) pose(i, _polys(mp), _sansTrait(st(i)));
  } else if (mode === "recadrage") {
    for (let i = 0; i < H; i++) {
      const dessus = mps.slice(i + 1, H);
      const base = dessus.length ? mz.diff(mps[i], reunion(dessus)) : mps[i];
      const r = _polys(mz.intersection(base, mps[H]));
      if (r.length) pose(i, r, _sansTrait(st(i)));
    }
    if (![...remp.values()].some((l) => l.length)) throw new Error(T("vectorlab.bool.resultat_vide"));
  } else {                                            // contour
    const anneaux = cibles.map((c) => aplatir_objet(c.objet));
    for (let i = 0; i < n; i++) {
      const autres = anneaux.filter((_, j) => j !== i).flat();
      const couleur = _sansCouleur(st(i).fond) || String(st(i).fond).startsWith("grad:") || String(st(i).fond).startsWith("motif:") ? "#000000" : st(i).fond;
      for (const ring of anneaux[i]) for (const pl of _decouperAnneau(ring, autres)) {
        const segs = pl.points.map((q, k) => ({ c: k ? "L" : "M", p: [q[0], q[1]] }));
        if (pl.ferme) segs.push({ c: "Z", p: [] });
        remp.set(cibles[i].objet, [...remp.get(cibles[i].objet), { d: chemin_serialiser(segs), style: { fond: "none", contour: couleur, epaisseur: 1 } }]);
      }
    }
  }
  const neuf = _idsNeufs(doc);
  const poses = [];
  for (const c of doc.calques) {
    if (!c.objets.some((o) => remp.has(o))) continue;
    c.objets = c.objets.flatMap((o) => {
      if (!remp.has(o)) return [o];
      return remp.get(o).map((x) => { const id = neuf(); poses.push(id); return { id, type: "path", d: x.d, style: x.style }; });
    });
  }
  return poses;
}
