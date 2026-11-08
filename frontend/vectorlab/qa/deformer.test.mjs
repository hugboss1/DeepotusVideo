// deformer.test.mjs — lot D3 « Déformer » (t460…) : les déformations vivantes de js/mod-deformer.js.
// T1 (t460) Le modèle vivant (groupe [source cachée, résultat généré], Modifier le contenu, Annuler, Décomposer) et
// l'Enveloppe par déformation prédéfinie (15 styles, courbure, distorsions, orientation).
// T2 (t461) Distorsion libre (bilinéaire sur les quatre coins) et Torsion (angle proportionnel à la distance au centre).
import { createRequire } from "node:module";
import { polylignes_objet, fournirMartinez, versMulti, aplatir_objet, aire_multi } from "../js/mod-bool.js";
import { op_deformer, op_deformation_regler, op_deformation_editer, op_deformation_annuler, STYLES_ENVELOPPE } from "../js/mod-deformer.js";
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
import { parserDoc, compilerSVG as docVersSvg } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const doc = (...objets) => ({ v: 1, taille: { w: 400, h: 400 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
const objets = (d) => d.calques[0].objets;
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const rect = (id, x = 100, y = 100, w = 200, h = 100, style = { fond: "#3a6fd0" }) => ({ id, type: "rect", x, y, w, h, style });
const pts = (o) => polylignes_objet(o).flatMap((l) => l.points);
const aire = (o) => aire_multi(versMulti(aplatir_objet(o)));
const resultat = (g) => g.enfants.filter((e) => e.genere);
// le point du résultat le plus proche d'un point voulu
const proche = (o, x, y) => pts(o).reduce((m, p) => Math.min(m, Math.hypot(p[0] - x, p[1] - y)), Infinity);
// l'ordonnée du tracé à l'abscisse x, côté haut (le plus petit y) ou bas
const yA = (o, x, haut = true) => { const v = pts(o).filter((p) => Math.abs(p[0] - x) < 1.2).map((p) => p[1]); return haut ? Math.min(...v) : Math.max(...v); };
const xA = (o, y, gauche = true) => { const v = pts(o).filter((p) => Math.abs(p[1] - y) < 1.2).map((p) => p[0]); return gauche ? Math.min(...v) : Math.max(...v); };

/* ── le modèle ── */
{
  const d = doc(rect("z", 0, 0, 10, 10), rect("a"), rect("y", 0, 300, 10, 10));
  const gid = op_deformer(d, ["a"], "enveloppe", { style: "arc", courbure: 50 });
  const g = objets(d)[1];
  ok("le groupe vivant prend la place de la source", g.id === gid && objets(d).map((o) => o.id).join() === `z,${gid},y`, objets(d).map((o) => o.id).join());
  ok("recette posée, réglages complétés", g.deformation && g.deformation.effet === "enveloppe" && g.deformation.params.style === "arc" && g.deformation.params.courbure === 50
     && g.deformation.params.orientation === "horizontale" && g.deformation.params.distH === 0 && g.deformation.params.distV === 0, JSON.stringify(g.deformation));
  ok("la source est gardée, CACHÉE, son style intact", g.enfants[0].id === "a" && g.enfants[0].cache === true && g.enfants[0].style.fond === "#3a6fd0");
  const R = resultat(g);
  ok("un résultat généré, chemin, id dérivé, style recopié", R.length === 1 && R[0].type === "path" && R[0].id === `${gid}_d1` && R[0].style.fond === "#3a6fd0" && !R[0].cache, JSON.stringify(R.map((r) => [r.id, r.type])));
  ok("le document reste valide", !refus(() => parserDoc(d)));
  const svg = docVersSvg(d);
  ok("le rendu SVG ne dessine pas la source cachée", !svg.includes('data-objet="a"') && svg.includes(`${gid}_d1`), svg.slice(0, 200));
  ok("rien à recalculer ensuite", derives_rafraichir(d) === 0);
  // vivant : la source change, le résultat suit
  g.enfants[0].w = 300;
  ok("la source change : un recalcul", derives_rafraichir(d) === 1);
  ok("le résultat suit (bord droit à x = 400)", pres(Math.max(...pts(resultat(objets(d)[1])[0]).map((p) => p[0])), 400, 0.5));
  // régler
  op_deformation_regler(d, gid, { courbure: -30 });
  ok("régler : la courbure change, le style reste", objets(d)[1].deformation.params.courbure === -30 && objets(d)[1].deformation.params.style === "arc");
  ok("régler : puis stable", derives_rafraichir(d) === 0);
  // un réglage écrit hors op (attribut générique) est suivi : l'empreinte couvre la recette
  objets(d)[1].deformation.params.courbure = 10;
  ok("réglage changé hors op : recalcul", derives_rafraichir(d) === 1);
  // la géométrie du groupe (Pathfinder, découpes) ne compte que le résultat, pas la source cachée
  ok("géométrie du groupe : la source cachée ne compte pas", polylignes_objet(objets(d)[1]).length === 1, polylignes_objet(objets(d)[1]).length);
  const av = JSON.stringify(d);
  ok("régler hors bornes : refus sans trace", !!refus(() => op_deformation_regler(d, gid, { courbure: 101 })) && JSON.stringify(d) === av);
  ok("régler un objet qui n'est pas une déformation : refus traduit", refus(() => op_deformation_regler(d, "z", {})) === T("vectorlab.deformer.pas_deformation", { id: "z" }));
}
{
  // Modifier le contenu : la source revient, le résultat se cache ; puis l'inverse, recalculé
  const d = doc(rect("a"));
  const gid = op_deformer(d, ["a"], "enveloppe", { style: "arc", courbure: 50 });
  op_deformation_editer(d, gid);
  const g = objets(d)[0];
  ok("modifier le contenu : source visible, résultat caché", !g.enfants[0].cache && resultat(g).every((r) => r.cache === true) && g.deformation.edition === true);
  ok("modifier le contenu : le SVG montre la source", docVersSvg(d).includes('data-objet="a"'));
  g.enfants[0].h = 200;                    // l'utilisateur modifie la source (Ctrl+clic)
  ok("pendant l'édition : pas de recalcul visible (le résultat reste caché)", (derives_rafraichir(d), resultat(objets(d)[0]).every((r) => r.cache === true)));
  op_deformation_editer(d, gid);
  const g2 = objets(d)[0];
  ok("fin de l'édition : source cachée, résultat visible et recalculé (hauteur 200)", g2.enfants[0].cache === true && !("edition" in g2.deformation)
     && resultat(g2).every((r) => !r.cache) && pres(Math.max(...pts(resultat(g2)[0]).map((p) => p[1])), 300, 0.5), JSON.stringify(g2.deformation));
}
{
  // Annuler la déformation : la source seule revient, visible ; Décomposer : le résultat seul reste
  const d = doc(rect("o1", 0, 0, 5, 5), rect("a"));
  const gid = op_deformer(d, ["a"], "enveloppe", { style: "arc", courbure: 50 });
  const copie = JSON.parse(JSON.stringify(d));
  op_deformation_annuler(d, gid);
  ok("annuler : la source revient à la place du groupe, visible", objets(d).map((o) => o.id).join() === "o1,a" && !("cache" in objets(d)[1]));
  op_derive_detacher(copie, gid);
  const g = objets(copie)[1];
  ok("décomposer : il ne reste que le résultat, en chemin ordinaire", g.id === gid && !g.deformation && g.enfants.length === 1 && g.enfants[0].type === "path"
     && !g.enfants[0].genere && !g.enfants[0].cache && /^o\d+$/.test(g.enfants[0].id) && g.enfants[0].id !== "o1", JSON.stringify(g.enfants.map((e) => e.id)));
}
{
  // plusieurs objets : chacun garde son style ; un texte seul est refusé
  const d = doc(rect("a"), { ...rect("b", 120, 120, 50, 50), style: { fond: "#e04040" } }, { id: "t", type: "texte", x: 0, y: 0, texte: "x", style: {} });
  const gid = op_deformer(d, ["a", "b"], "enveloppe", { style: "renflement", courbure: 40 });
  const R = resultat(objets(d).find((o) => o.id === gid));
  ok("deux objets : deux résultats, chacun son style", R.length === 2 && R[0].style.fond === "#3a6fd0" && R[1].style.fond === "#e04040", JSON.stringify(R.map((r) => r.style.fond)));
  const av = JSON.stringify(d);
  ok("un texte seul : refus traduit", refus(() => op_deformer(d, ["t"], "enveloppe", {})) === T("vectorlab.deformer.sans_geometrie"));
  ok("rien de sélectionné : refus", refus(() => op_deformer(d, [], "enveloppe", {})) === T("vectorlab.deformer.rien"));
  ok("effet inconnu : refus", !!refus(() => op_deformer(d, ["t"], "spirale", {})));
  ok("style inconnu : refus traduit", refus(() => op_deformer(d, [gid], "enveloppe", { style: "nuage" })) === T("vectorlab.deformer.style", { style: "nuage" }));
  ok("courbure non numérique : refus traduit", refus(() => op_deformer(d, [gid], "enveloppe", { courbure: "x" })) === T("vectorlab.deformer.pourcent", { min: -100, max: 100 }));
  ok("aucune trace après les refus", JSON.stringify(d) === av);
}

/* ── l'Enveloppe : rectangle 200 × 100 en (100, 100) → centre (200, 150) ── */
const env = (params, source = rect("a")) => { const d = doc(source); op_deformer(d, ["a"], "enveloppe", params); return resultat(objets(d)[0])[0]; };
{
  ok("15 styles", STYLES_ENVELOPPE.length === 15 && new Set(STYLES_ENVELOPPE).size === 15, STYLES_ENVELOPPE.join());
  const a0 = aire(rect("a"));
  ok("courbure 0 : chaque style rend la forme d'origine", STYLES_ENVELOPPE.every((s) => pres(aire(env({ style: s, courbure: 0 })), a0, a0 * 0.005)), STYLES_ENVELOPPE.map((s) => s + "=" + Math.round(aire(env({ style: s, courbure: 0 })))).join(" "));
  const arc = env({ style: "arc", courbure: 50 });
  ok("arc 50 % : le milieu du bord haut monte de 25 (50 % × h / 2)", pres(yA(arc, 200, true), 75, 0.6), yA(arc, 200, true));
  ok("arc : le bord bas monte d'autant", pres(yA(arc, 200, false), 175, 0.6), yA(arc, 200, false));
  ok("arc : les coins restent", proche(arc, 100, 100) < 0.6 && proche(arc, 300, 200) < 0.6);
  ok("arc : profil parabolique (au quart, 75 % de la flèche)", pres(yA(arc, 150, true), 100 - 25 * 0.75, 0.6), yA(arc, 150, true));
  const premier = pts(arc)[0], dernier = pts(arc)[pts(arc).length - 1];
  ok("arc : le tracé fermé ne répète pas son premier point", Math.hypot(premier[0] - dernier[0], premier[1] - dernier[1]) > 0.01);
  ok("arc négatif : le bord haut descend", yA(env({ style: "arc", courbure: -50 }), 200, true) > 100);
  const arche = env({ style: "arche", courbure: 60 });
  ok("arche : le bas ne bouge pas", pres(yA(arche, 200, false), 200, 0.6) && pres(yA(arche, 120, false), 200, 0.6), yA(arche, 200, false));
  ok("arche : le haut monte", yA(arche, 200, true) < 95);
  const gonfle = env({ style: "gonflement", courbure: 50 });
  ok("gonflement : les bords gonflent, les coins restent", xA(gonfle, 150, false) > 305 && yA(gonfle, 200, true) < 95 && proche(gonfle, 300, 200) < 0.6, `${xA(gonfle, 150, false)} ${yA(gonfle, 200, true)}`);
  ok("gonflement : l'aire augmente", aire(gonfle) > a0 * 1.05);
  const renfle = env({ style: "renflement", courbure: 50 });
  ok("renflement : le haut monte ET le bas descend", yA(renfle, 200, true) < 90 && yA(renfle, 200, false) > 210);
  const basArc = env({ style: "arc_bas", courbure: 50 });
  ok("arc inférieur : le haut ne bouge pas, le bas se courbe", pres(yA(basArc, 200, true), 100, 0.6) && yA(basArc, 200, false) > 210);
  const hautArc = env({ style: "arc_haut", courbure: 50 });
  ok("arc supérieur : le bas ne bouge pas, le haut se courbe", pres(yA(hautArc, 200, false), 200, 0.6) && yA(hautArc, 200, true) < 90);
  const drapeau = env({ style: "drapeau", courbure: 50 });
  ok("drapeau : une onde, le haut monte d'un côté et descend de l'autre", yA(drapeau, 150, true) < 100 && yA(drapeau, 250, true) > 100, `${yA(drapeau, 150, true)} ${yA(drapeau, 250, true)}`);
  const oeil = env({ style: "oeil", courbure: 50 });
  ok("œil de poisson : le centre gonfle, les coins restent", yA(oeil, 200, true) < 95 && proche(oeil, 100, 100) < 0.6);
  // orientation verticale : le même arc, sur les bords gauche et droit
  const vert = env({ style: "arc", courbure: 50, orientation: "verticale" });
  ok("orientation verticale : la flèche se mesure sur la largeur (50 % × 200 / 2)", pres(xA(vert, 150, true), 50, 0.6), xA(vert, 150, true));
  ok("orientation verticale : le bord gauche se courbe, le haut reste droit", xA(vert, 150, true) < 95 && pres(yA(vert, 200, true), 100, 0.6), `${xA(vert, 150, true)} ${yA(vert, 200, true)}`);
  // distorsions : un rectangle devient un trapèze
  const dh = env({ style: "arc", courbure: 0, distH: 50 });
  const hG = yA(dh, 101, false) - yA(dh, 101, true), hD = yA(dh, 299, false) - yA(dh, 299, true);
  ok("distorsion horizontale : le côté droit plus haut que le gauche (trapèze)", hD > hG * 1.5, `${hG} ${hD}`);
  const dv = env({ style: "arc", courbure: 0, distV: 50 });
  const lH = xA(dv, 101, false) - xA(dv, 101, true), lB = xA(dv, 199, false) - xA(dv, 199, true);
  ok("distorsion verticale : le bas plus large que le haut", lB > lH * 1.2, `${lH} ${lB}`);
  // tous les styles gardent un tracé fermé et valide à 100 %
  ok("chaque style à 100 % : un tracé fermé, sans NaN", STYLES_ENVELOPPE.every((s) => { const r = env({ style: s, courbure: 100 }); return /Z\s*$/.test(r.d) && !/NaN|Infinity/.test(r.d); }));
}

/* ── T2 (t461) Distorsion libre et Torsion ── */
const def = (effet, params, source = rect("a")) => { const d = doc(source); op_deformer(d, ["a"], effet, params); return { d, r: resultat(objets(d)[0])[0], g: objets(d)[0] }; };
{
  const a0 = aire(rect("a"));
  const id = def("distorsion", {});
  ok("distorsion : réglages par défaut, quatre coins à zéro", JSON.stringify(id.g.deformation.params) === '{"coins":[[0,0],[0,0],[0,0],[0,0]]}', JSON.stringify(id.g.deformation.params));
  ok("distorsion à zéro : la forme d'origine", pres(aire(id.r), a0, a0 * 0.005) && proche(id.r, 100, 100) < 0.01 && proche(id.r, 300, 200) < 0.01);
  const hg = def("distorsion", { coins: [[-20, -10], [0, 0], [0, 0], [0, 0]] }).r;
  ok("distorsion : le coin haut-gauche tiré suit exactement (80, 90)", proche(hg, 80, 90) < 0.01, proche(hg, 80, 90));
  ok("distorsion : les autres coins restent", proche(hg, 300, 100) < 0.01 && proche(hg, 300, 200) < 0.01 && proche(hg, 100, 200) < 0.01);
  const tous = def("distorsion", { coins: [[0, 0], [30, 0], [10, 40], [0, 0]] }).r;
  ok("distorsion : haut-droit et bas-droit suivent (330, 100) et (310, 240)", proche(tous, 330, 100) < 0.01 && proche(tous, 310, 240) < 0.01);
  // le milieu du bord haut suit la moyenne de ses deux coins (interpolation bilinéaire)
  ok("distorsion : le milieu du bord haut suit la moyenne des deux coins du haut", proche(tous, 215, 100) < 1.01, proche(tous, 215, 100));
  const d = doc(rect("a"));
  const avant = JSON.stringify(d);
  ok("distorsion : coins mal formés → refus traduit", refus(() => op_deformer(d, ["a"], "distorsion", { coins: [[0, 0], [1, 2]] })) === T("vectorlab.deformer.coins")
     && refus(() => op_deformer(d, ["a"], "distorsion", { coins: [[0, 0], [0, 0], [0, 0], [0, "x"]] })) === T("vectorlab.deformer.coins")
     && refus(() => op_deformer(d, ["a"], "distorsion", { coins: "non" })) === T("vectorlab.deformer.coins")
     && refus(() => op_deformer(d, ["a"], "distorsion", { coins: [[0, 0], [0, 0], [0, 0], [0, "5"]] })) === T("vectorlab.deformer.coins") && JSON.stringify(d) === avant);
  // le tableau de coins de l'appelant est copié : le modifier ensuite ne touche pas au document
  const coins = [[1, 1], [0, 0], [0, 0], [0, 0]];
  const dc = doc(rect("a"));
  op_deformer(dc, ["a"], "distorsion", { coins });
  coins[0][0] = 99;
  ok("distorsion : les coins sont copiés", objets(dc)[0].deformation.params.coins[0][0] === 1);
  // régler un coin garde les autres réglages… et l'effet reste la distorsion
  const g = def("distorsion", { coins: [[5, 5], [0, 0], [0, 0], [0, 0]] });
  op_deformation_regler(g.d, g.g.id, { coins: [[0, 0], [0, 0], [0, 0], [-7, 3]] });
  ok("distorsion réglée : le coin bas-gauche (93, 203)", proche(resultat(objets(g.d)[0])[0], 93, 203) < 0.01);
}
{
  const a0 = aire(rect("a"));
  const t0 = def("torsion", { angle: 0 });
  ok("torsion : réglage par défaut 45°", def("torsion", {}).g.deformation.params.angle === 45);
  ok("torsion 0 : la forme d'origine", pres(aire(t0.r), a0, a0 * 0.005) && proche(t0.r, 100, 100) < 0.01);
  const t90 = def("torsion", { angle: 90 }).r;
  // le coin le plus loin du centre (200, 150) tourne de l'angle entier : (100, 100) → (250, 50)
  ok("torsion 90° : le coin le plus éloigné a tourné de 90° autour du centre", proche(t90, 250, 50) < 0.6, proche(t90, 250, 50));
  // le milieu du bord haut (200, 100), à 50 px du centre sur 111,8 : il tourne de 90 × 50 / 111,8 ≈ 40.25°
  const mi = def("torsion", { angle: 90 }, { id: "a", type: "path", d: "M200 100 L300 100 L300 200 L100 200 L100 100 Z", style: { fond: "#888" } }).r;
  const p0 = pts(mi)[0];
  ok("torsion : l'angle croît avec la distance au centre (premier point exact)", pres(p0[0], 232.3057, 0.02) && pres(p0[1], 111.8379, 0.02), JSON.stringify(p0));
  ok("torsion : l'aire est gardée (rotation par anneaux)", pres(aire(t90), a0, a0 * 0.03), aire(t90));
  ok("torsion négative : sens inverse", proche(def("torsion", { angle: -90 }).r, 150, 250) < 0.6);
  const d = doc(rect("a"));
  ok("torsion : angle non numérique → refus traduit", refus(() => op_deformer(d, ["a"], "torsion", { angle: "x" })) === T("vectorlab.deformer.angle", { min: -3600, max: 3600 }));
}

if (echecs.length) {
  console.error(`deformer : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("deformer : ok");
