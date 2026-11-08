// mod-traces.js — lot D1 « Tracés » (spec 2026-11-08-illustrator-vectorlab-inventaire.md) : les commandes de
// tracé reprises d'Illustrator, en opérations PURES sur le modèle. Règle de mod-bool : tout se CALCULE avant de
// muter — un refus ne laisse aucune trace ; l'UI les appelle par VL.executer (annulation comprise).
import { T } from "./mod-i18n.js";
import { contour_en_multi, multi_vers_d, cibles_b } from "./mod-bool.js";

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
