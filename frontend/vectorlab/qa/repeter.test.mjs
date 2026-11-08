// repeter.test.mjs — lot D2 « Répéter et fusionner » (t450…) : les objets vivants de js/mod-repeter.js.
// T1 (t450) Répétition radiale : un groupe vivant [source, ...copies générées] ; les copies suivent la source dans
// la même étape (derives_rafraichir), seule une empreinte changée coûte un recalcul ; régler, décomposer, refus sans
// trace. Au passage : la matrice des booléens lit translate / scale / matrix / skew (les copies en dépendent).
// T2 (t451) Répétition en grille : lignes × colonnes au pas de la boîte de la source (+ écart), briques, miroirs
// alternés, pavage hexagonal sans jour ni recouvrement.
// T3 (t452) Répétition en miroir : la source et son reflet par un axe (angle, écart au bord de la source).
import { createRequire } from "node:module";
import { polylignes_objet, fournirMartinez, martinez, versMulti, aplatir_objet, aire_multi } from "../js/mod-bool.js";
import { op_repeter, op_repetition_regler } from "../js/mod-repeter.js";
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
import { parserDoc } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const doc = (...objets) => ({ v: 1, taille: { w: 400, h: 400 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
const objets = (d) => d.calques[0].objets;
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const boite = (o) => {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const l of polylignes_objet(o)) for (const [x, y] of l.points) {
    x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
  }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
};
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const carre = (id, x = 90, y = 40, extra = {}) => ({ id, type: "rect", x, y, w: 20, h: 20, style: { fond: "#c33" }, ...extra });
const tousIds = (d) => { const out = []; (function v(l) { for (const o of l) { out.push(o.id); if (o.type === "groupe") v(o.enfants || []); } })(objets(d)); return out; };

/* ── la matrice des booléens lit toute la liste de transformations SVG ── */
{
  const b1 = boite({ ...carre("a", 0, 0), transform: "translate(10 5)" });
  ok("translate(10 5) déplace le rect", pres(b1.x, 10) && pres(b1.y, 5), JSON.stringify(b1));
  const b2 = boite({ ...carre("a", 0, 0), transform: "matrix(-1 0 0 1 200 0)" });
  ok("matrix(-1 0 0 1 200 0) retourne le rect", pres(b2.x, 180) && pres(b2.w, 20), JSON.stringify(b2));
  const b3 = boite({ ...carre("a", 10, 10), transform: "scale(2)" });
  ok("scale(2) double depuis l'origine, sur les deux axes", pres(b3.x, 20) && pres(b3.w, 40) && pres(b3.y, 20) && pres(b3.h, 40), JSON.stringify(b3));
  const b4 = boite({ ...carre("a", 0, 0), transform: "scale(2 3)" });
  ok("scale(2 3) : deux facteurs", pres(b4.w, 40) && pres(b4.h, 60), JSON.stringify(b4));
  const b5 = boite({ ...carre("a", 0, 0), transform: "translate(100 0) rotate(90)" });
  ok("composition gauche → droite : rotate puis translate", pres(b5.x, 80) && pres(b5.y, 0), JSON.stringify(b5));
  const b6 = boite({ ...carre("a", 0, 0), transform: "skewX(45)" });
  ok("skewX(45) penche le rect", pres(b6.w, 40), JSON.stringify(b6));
  const b7 = boite({ ...carre("a", 0, 0), transform: "translate(5)" });
  ok("translate à un seul nombre : ty = 0", pres(b7.x, 5) && pres(b7.y, 0), JSON.stringify(b7));
  const b8 = boite({ ...carre("a", 0, 0), transform: "rotate(90 10 10)" });
  ok("rotate autour d'un centre inchangé", pres(b8.x, 0) && pres(b8.y, 0) && pres(b8.w, 20), JSON.stringify(b8));
}

/* ── T1 (t450) répétition radiale ── */
{
  const d = doc(carre("z", 0, 0), carre("a"), carre("y", 300, 300));
  const gid = op_repeter(d, ["a"], "radiale", { nombre: 8, rayon: 50 });
  const g = objets(d)[1];
  ok("le groupe vivant prend la place de la source (ordre de peinture gardé)", g && g.id === gid && objets(d).length === 3
     && objets(d)[0].id === "z" && objets(d)[2].id === "y", JSON.stringify(objets(d).map((o) => o.id)));
  ok("groupe : recette radiale posée", g.type === "groupe" && g.repetition && g.repetition.mode === "radiale"
     && g.repetition.params.nombre === 8 && g.repetition.params.rayon === 50 && typeof g.repetition.empreinte === "string");
  ok("8 enfants : la source puis 7 copies générées", g.enfants.length === 8 && g.enfants[0].id === "a" && !g.enfants[0].genere
     && g.enfants.slice(1).every((c, k) => c.genere === true && c.id === `${gid}_r${k + 1}`), JSON.stringify(g.enfants.map((e) => [e.id, e.genere])));
  const C = { x: 100, y: 100 };       // centre de la source (100, 50) + rayon vers le bas : la source est en haut
  const pos = g.enfants.map(boite);
  ok("chaque instance est sur le cercle de rayon 50", pos.every((b) => pres(Math.hypot(b.cx - C.x, b.cy - C.y), 50)), JSON.stringify(pos.map((b) => [b.cx, b.cy])));
  const ang = pos.map((b) => Math.atan2(b.cy - C.y, b.cx - C.x) * 180 / Math.PI);
  const pas = ang.slice(1).map((a, k) => ((a - ang[k]) % 360 + 360) % 360);
  ok("45° d'une instance à la suivante, dans le sens horaire", pas.every((p) => pres(p, 45)), JSON.stringify(pas));
  ok("orienter : la copie à 45° est tournée (boîte élargie)", pres(pos[1].w, 20 * Math.SQRT2), pos[1].w);
  ok("le document reste valide", !refus(() => parserDoc(d)), refus(() => parserDoc(d)));
  ok("ids uniques", new Set(tousIds(d)).size === tousIds(d).length);
}
{
  const d = doc({ ...carre("a"), x: 85, w: 30, y: 45, h: 10 });   // pas un carré : une rotation de 90° se verrait
  const gid = op_repeter(d, ["a"], "radiale", { nombre: 4, rayon: 50, orienter: false });
  const g = objets(d)[0];
  const pos = g.enfants.map(boite);
  ok("orienter faux : les copies restent droites", pos.every((b) => pres(b.w, 30) && pres(b.h, 10)), JSON.stringify(pos));
  ok("orienter faux : sur le cercle quand même", pres(pos[2].cx, 100) && pres(pos[2].cy, 150) && pres(pos[1].cx, 150) && pres(pos[1].cy, 100), JSON.stringify(pos));
  ok("orienter faux : réglage gardé", g.repetition.params.orienter === false);
  ok("gid rendu", gid === g.id);
}
{
  // rayon par défaut : la demi-diagonale de la source ; nombre par défaut 8 ; orienter par défaut vrai
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "radiale", {});
  const p = objets(d)[0].repetition.params;
  ok("défauts : nombre 8, rayon = demi-diagonale, orienter", p.nombre === 8 && pres(p.rayon, 10 * Math.SQRT2) && p.orienter === true, JSON.stringify(p));
}
{
  // la source garde son transform : la copie le compose APRÈS la rotation de la rosace
  const d = doc(carre("a", 90, 40, { transform: "rotate(30 100 50)" }));
  const gid = op_repeter(d, ["a"], "radiale", { nombre: 4, rayon: 50 });
  const c1 = objets(d)[0].enfants[1];
  ok("transform de la copie = rotation de rosace puis transform de la source", /^rotate\(90 100 100\) rotate\(30 100 50\)$/.test(c1.transform), c1.transform);
  ok("la source n'est pas touchée", objets(d)[0].enfants[0].transform === "rotate(30 100 50)");
  ok("gid", !!gid);
}
{
  // plusieurs objets : groupés d'abord en UNE source
  const d = doc(carre("a"), carre("b", 120, 40), carre("y", 300, 300));
  const gid = op_repeter(d, ["a", "b"], "radiale", { nombre: 3, rayon: 60 });
  const g = objets(d).find((o) => o.id === gid);
  ok("deux objets → une source groupée, 3 instances", g && g.enfants.length === 3 && g.enfants[0].type === "groupe"
     && g.enfants[0].enfants.map((e) => e.id).join() === "a,b", JSON.stringify(g && g.enfants[0]));
  ok("à la place du plus haut des deux", objets(d).map((o) => o.id).join() === `${gid},y`, objets(d).map((o) => o.id).join());
  const copie = g.enfants[1];
  ok("les descendants d'une copie ont des ids dérivés, générés", copie.enfants.every((e, j) => e.id === `${copie.id}_${j + 1}`), JSON.stringify(copie.enfants.map((e) => e.id)));
  ok("ids uniques (copies de groupe)", new Set(tousIds(d)).size === tousIds(d).length);
}
{
  // les liens vivants de la source ne se recopient pas : une copie ne suivrait pas la bonne source
  const d = doc(carre("x", 0, 0), { ...carre("a"), derive: { source: "x", decalage: 2, empreinte: "?" } });
  op_repeter(d, ["a"], "radiale", { nombre: 3, rayon: 40 });
  const g = objets(d)[1];
  ok("la source garde son lien", g.enfants[0].derive && g.enfants[0].derive.source === "x");
  ok("les copies n'ont pas de lien derive", g.enfants.slice(1).every((c) => !c.derive), JSON.stringify(g.enfants[1]));
}
/* ── vivant : la source change, les copies suivent ── */
{
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "radiale", { nombre: 4, rayon: 50 });
  ok("rien n'a changé : aucun recalcul", derives_rafraichir(d) === 0);
  const g = objets(d)[0];
  g.enfants[0].w = 40;                   // ce que ferait une op sur la source (Ctrl+clic)
  ok("la source a changé : un recalcul", derives_rafraichir(d) === 1);
  const b1 = boite(objets(d)[0].enfants[1]);
  ok("la copie à 90° suit : sa hauteur devient 40", pres(b1.h, 40) && pres(b1.w, 20), JSON.stringify(b1));
  ok("ensuite plus rien à recalculer", derives_rafraichir(d) === 0);
  // l'empreinte couvre AUSSI les réglages : un réglage écrit par une autre voie (attribut générique) est suivi
  objets(d)[0].repetition.params.nombre = 5;
  ok("réglage changé hors op : recalcul", derives_rafraichir(d) === 1 && objets(d)[0].enfants.length === 5, objets(d)[0].enfants.length);
}
{
  // répétition de répétition : la source intérieure change, la rosace intérieure PUIS l'extérieure suivent, en un passage
  const d = doc(carre("a"));
  const gi = op_repeter(d, ["a"], "radiale", { nombre: 2, rayon: 30 });
  const ge = op_repeter(d, [gi], "radiale", { nombre: 2, rayon: 100 });
  const ext = objets(d)[0];
  ok("répétition de répétition : la source extérieure est la rosace intérieure", ext.id === ge && ext.enfants[0].id === gi && !ext.enfants[1].repetition);
  ext.enfants[0].enfants[0].w = 40;
  ok("répétition de répétition : deux recalculs en un passage", derives_rafraichir(d) === 2);
  const copieExt = objets(d)[0].enfants[1];
  ok("répétition de répétition : la copie extérieure porte la source élargie", copieExt.enfants[0].w === 40, JSON.stringify(copieExt.enfants[0]));
  ok("répétition de répétition : la copie intérieure de la copie extérieure suit aussi", copieExt.enfants[1].w === 40, JSON.stringify(copieExt.enfants[1]));
  ok("répétition de répétition : stable ensuite", derives_rafraichir(d) === 0);
}
{
  // la source disparue (son id n'est plus en tête) : le groupe reste à son dernier état, sans exception
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "radiale", { nombre: 4, rayon: 50 });
  const g = objets(d)[0];
  g.enfants = g.enfants.slice(1);
  const avant = JSON.stringify(d);
  ok("source disparue : pas d'exception", !refus(() => derives_rafraichir(d)));
  ok("source disparue : groupe inchangé", JSON.stringify(d) === avant);
}
{
  // un recalcul qui échoue (source devenue non aplatissable) laisse les copies
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "radiale", { nombre: 4, rayon: 50 });
  const g = objets(d)[0];
  const copies = JSON.stringify(g.enfants.slice(1));
  g.enfants[0] = { id: "a", type: "inconnu" };
  ok("recalcul impossible : pas d'exception", !refus(() => derives_rafraichir(d)));
  ok("recalcul impossible : copies gardées", JSON.stringify(objets(d)[0].enfants.slice(1)) === copies);
}
/* ── régler ── */
{
  const d = doc(carre("a"));
  const gid = op_repeter(d, ["a"], "radiale", { nombre: 8, rayon: 50 });
  op_repetition_regler(d, gid, { nombre: 12 });
  const g = objets(d)[0];
  ok("régler 8 → 12 : 12 instances", g.enfants.length === 12 && g.repetition.params.nombre === 12);
  ok("régler garde les autres réglages", g.repetition.params.rayon === 50 && g.repetition.params.orienter === true);
  ok("régler : les instances sont à 30°", pres(boite(g.enfants[3]).cx, 100 + 50 * Math.cos(Math.PI * (-90 + 90) / 180)), boite(g.enfants[3]).cx);
  ok("régler : plus rien à recalculer ensuite", derives_rafraichir(d) === 0);
  const avant = JSON.stringify(d);
  ok("régler hors bornes : refus", !!refus(() => op_repetition_regler(d, gid, { nombre: 1 })));
  ok("régler hors bornes : aucune trace", JSON.stringify(d) === avant);
  ok("régler un objet qui n'est pas une répétition : refus traduit", refus(() => op_repetition_regler(doc(carre("b")), "b", { nombre: 4 })) === T("vectorlab.repeter.pas_repetition", { id: "b" }));
  ok("régler un id inconnu : refus", !!refus(() => op_repetition_regler(d, "nope", { nombre: 4 })));
}
/* ── décomposer ── */
{
  const d = doc(carre("o1", 0, 0), carre("a"));
  const gid = op_repeter(d, ["a"], "radiale", { nombre: 4, rayon: 50 });
  op_derive_detacher(d, gid);
  const g = objets(d)[1];
  ok("décomposer : plus de recette", g.id === gid && g.type === "groupe" && !g.repetition);
  ok("décomposer : plus de copie générée", g.enfants.every((e) => !e.genere));
  ok("décomposer : la source garde son id", g.enfants[0].id === "a");
  ok("décomposer : les copies ont des ids o<n> neufs", g.enfants.slice(1).every((e) => /^o\d+$/.test(e.id)), JSON.stringify(g.enfants.map((e) => e.id)));
  ok("décomposer : ids uniques", new Set(tousIds(d)).size === tousIds(d).length, tousIds(d).join());
  ok("décomposer : les copies ne bougent pas", pres(boite(g.enfants[2]).cy, 150));
  ok("décomposer : la source ne pilote plus rien", (() => { g.enfants[0].w = 40; derives_rafraichir(d); return pres(boite(g.enfants[2]).w, 20); })());
}
{
  // décomposer une répétition d'un GROUPE : les descendants des copies aussi reçoivent des ids neufs
  const d = doc(carre("a"), carre("b", 120, 40));
  const gid = op_repeter(d, ["a", "b"], "radiale", { nombre: 2, rayon: 50 });
  op_derive_detacher(d, gid);
  const ids = tousIds(d);
  ok("décomposer un groupe : aucun id dérivé ne reste", ids.every((i) => !i.includes("_r")), ids.join());
  ok("décomposer un groupe : ids uniques", new Set(ids).size === ids.length);
}
/* ── refus sans trace ── */
{
  const d = doc(carre("a"), { id: "t", type: "texte", x: 0, y: 0, texte: "x", style: {} });
  const avant = JSON.stringify(d);
  ok("rien de sélectionné : refus traduit", refus(() => op_repeter(d, [], "radiale", {})) === T("vectorlab.repeter.rien"));
  ok("id inconnu : refus", !!refus(() => op_repeter(d, ["nope"], "radiale", {})));
  ok("mode inconnu : refus", !!refus(() => op_repeter(d, ["a"], "spirale", {})));
  ok("nombre 1 : refus", !!refus(() => op_repeter(d, ["a"], "radiale", { nombre: 1 })));
  ok("nombre 101 : refus", !!refus(() => op_repeter(d, ["a"], "radiale", { nombre: 101 })));
  ok("nombre non entier : refus", !!refus(() => op_repeter(d, ["a"], "radiale", { nombre: 4.5 })));
  ok("rayon 0 : refus", !!refus(() => op_repeter(d, ["a"], "radiale", { rayon: 0 })));
  ok("rayon infini : refus", !!refus(() => op_repeter(d, ["a"], "radiale", { rayon: Infinity })));
  ok("rayon non numérique : refus", !!refus(() => op_repeter(d, ["a"], "radiale", { rayon: "abc" })));
  ok("texte seul : refus traduit (pas de géométrie)", refus(() => op_repeter(d, ["t"], "radiale", {})) === T("vectorlab.repeter.source_type"));
  ok("aucune trace après les refus", JSON.stringify(d) === avant);
  const v = doc(carre("a"));
  v.calques[0].verrou = true;
  ok("calque verrouillé : refus", !!refus(() => op_repeter(v, ["a"], "radiale", {})));
  // une copie générée n'est jamais une source
  const r = doc(carre("a"));
  const gid = op_repeter(r, ["a"], "radiale", { nombre: 3, rayon: 40 });
  ok("répéter une copie générée : refus", !!refus(() => op_repeter(r, [`${gid}_r1`], "radiale", {})));
  ok("le groupe vivant entier se répète, lui (répétition de répétition)", !refus(() => op_repeter(r, [gid], "radiale", { nombre: 2, rayon: 100 })));
}

/* ── T2 (t451) répétition en grille : pas = boîte de la source + écart, briques, miroirs alternés, hexagones ── */
const pts = (o) => polylignes_objet(o).flatMap((l) => l.points.map(([x, y]) => `${Math.round(x * 100) / 100},${Math.round(y * 100) / 100}`));
{
  const d = doc(carre("a"));
  const gid = op_repeter(d, ["a"], "grille", { lignes: 3, colonnes: 4 });
  const g = objets(d)[0];
  ok("grille 3 × 4 : 12 instances, la source d'abord", g.enfants.length === 12 && g.enfants[0].id === "a"
     && g.enfants.slice(1).every((c, k) => c.id === `${gid}_r${k + 1}` && c.genere), JSON.stringify(g.enfants.map((e) => e.id)));
  ok("grille : réglages par défaut posés", JSON.stringify(g.repetition.params) === JSON.stringify(
     { lignes: 3, colonnes: 4, ecartX: 0, ecartY: 0, decalage: "aucun", miroirLignes: false, miroirColonnes: false }), JSON.stringify(g.repetition.params));
  // ordre ligne par ligne : la 7e copie (k = 7) est en ligne 1, colonne 3
  const b = boite(g.enfants[7]);
  ok("grille : pas = la boîte de la source, lignes puis colonnes", pres(b.x, 90 + 3 * 20) && pres(b.y, 40 + 20), JSON.stringify(b));
  ok("grille : les copies sont collées, sans recouvrement", pres(boite(g.enfants[1]).x, 110) && pres(boite(g.enfants[4]).y, 60));
  ok("grille : le document reste valide", !refus(() => parserDoc(d)));
  // la source grandit : le pas suit (il se relit à chaque recalcul, l'écart reste)
  g.enfants[0].w = 30;
  derives_rafraichir(d);
  ok("grille : la source s'élargit, le pas suit", pres(boite(objets(d)[0].enfants[1]).x, 120), boite(objets(d)[0].enfants[1]).x);
}
{
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "grille", {});
  ok("grille par défaut : 3 × 3", objets(d)[0].enfants.length === 9 && objets(d)[0].repetition.params.lignes === 3);
}
{
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "grille", { lignes: 2, colonnes: 2, ecartX: 10, ecartY: -5 });
  const e = objets(d)[0].enfants.map(boite);
  ok("écarts : 10 entre colonnes, -5 entre lignes (recouvrement voulu)", pres(e[1].x, 120) && pres(e[2].y, 55) && pres(e[3].x, 120) && pres(e[3].y, 55), JSON.stringify(e));
}
{
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "grille", { lignes: 3, colonnes: 2, decalage: "brique_lignes" });
  const e = objets(d)[0].enfants.map(boite);
  ok("brique par lignes : une ligne sur deux décalée d'un demi-pas", pres(e[2].x, 100) && pres(e[3].x, 120) && pres(e[4].x, 90) && pres(e[2].y, 60), JSON.stringify(e.map((b) => [b.x, b.y])));
}
{
  const d = doc(carre("a"));
  op_repeter(d, ["a"], "grille", { lignes: 2, colonnes: 3, decalage: "brique_colonnes" });
  const e = objets(d)[0].enfants.map(boite);
  ok("brique par colonnes : une colonne sur deux décalée d'un demi-pas", pres(e[1].y, 50) && pres(e[2].y, 40) && pres(e[1].x, 110) && pres(e[4].y, 70), JSON.stringify(e.map((b) => [b.x, b.y])));
}
{
  // un triangle rectangle à angle droit en haut à gauche : un miroir se voit
  const tri = { id: "a", type: "path", d: "M90 40 L110 40 L90 60 Z", style: { fond: "#c33" } };
  const d = doc(tri);
  op_repeter(d, ["a"], "grille", { lignes: 2, colonnes: 2, miroirColonnes: true });
  const g = objets(d)[0];
  const c1 = pts(g.enfants[1]);
  ok("miroir des colonnes : la colonne 1 est retournée de gauche à droite", c1.includes("130,60") && !c1.includes("110,60"), c1.join(" "));
  const c2 = pts(g.enfants[2]);
  ok("miroir des colonnes : la colonne 0 ne l'est pas", c2.includes("90,80") && !c2.includes("110,80"), c2.join(" "));
  const d2 = doc({ ...tri });
  op_repeter(d2, ["a"], "grille", { lignes: 2, colonnes: 2, miroirLignes: true });
  const l1 = pts(objets(d2)[0].enfants[2]);
  ok("miroir des lignes : la ligne 1 est retournée de haut en bas", l1.includes("110,80") && l1.includes("90,80") && !l1.includes("110,60"), l1.join(" "));
  ok("miroir des lignes : la ligne 0 ne l'est pas", pts(objets(d2)[0].enfants[1]).includes("110,60"), pts(objets(d2)[0].enfants[1]).join(" "));
  const d3 = doc({ ...tri });
  op_repeter(d3, ["a"], "grille", { lignes: 2, colonnes: 2, miroirLignes: true, miroirColonnes: true });
  const lc = pts(objets(d3)[0].enfants[3]);
  ok("les deux miroirs : la case (1, 1) est retournée deux fois", lc.includes("110,80") && lc.includes("130,80") && lc.includes("130,60") && !lc.includes("110,60"), lc.join(" "));
}
{
  // hexagones : pavage sans jour ni recouvrement, à plat (flat-top) puis en pointe (pointy-top)
  const M = martinez();
  const hex = (id, cx, cy, r, plat) => {
    const p = [];
    for (let k = 0; k < 6; k++) { const a = (plat ? 0 : 30) + 60 * k; p.push([cx + r * Math.cos(a * Math.PI / 180), cy + r * Math.sin(a * Math.PI / 180)]); }
    return { id, type: "path", d: "M" + p.map(([x, y]) => `${x} ${y}`).join(" L") + " Z", style: { fond: "#4a8" } };
  };
  for (const plat of [true, false]) {
    const d = doc(hex("h", 100, 100, 20, plat));
    op_repeter(d, ["h"], "grille", { lignes: 3, colonnes: 3, decalage: "hexagones" });
    const g = objets(d)[0];
    const multis = g.enfants.map((e) => versMulti(aplatir_objet(e)));
    let u = multis[0];
    for (const m of multis.slice(1)) u = M.union(u, m);
    const somme = multis.reduce((s, m) => s + aire_multi(m), 0);
    const nom = plat ? "hexagones à plat" : "hexagones en pointe";
    ok(`${nom} : 9 instances`, g.enfants.length === 9);
    ok(`${nom} : aucun recouvrement (aire de l'union = somme)`, Math.abs(aire_multi(u) - somme) <= somme * 0.001, `${aire_multi(u)} / ${somme}`);
    ok(`${nom} : aucun jour (un seul polygone, sans trou)`, u.length === 1 && u[0].length === 1, `${u.length} polygones, ${u[0] && u[0].length} anneaux`);
    // le pas exact (√3 r) : arrondi au centième, il ouvrirait un jour de 0,001 px par rangée
    const c = boite(g.enfants[3]), attendu = plat ? 100 + Math.sqrt(3) * 20 : 100 + 30;
    ok(`${nom} : pas exact au millionième`, Math.abs((plat ? c.cy : c.cy) - attendu) < 1e-5, `${c.cy} / ${attendu}`);
  }
  {
    // un écart s'ajoute au pas hexagonal (des hexagones espacés, pour un plateau à joints)
    const d = doc(hex("h", 100, 100, 20, true));
    op_repeter(d, ["h"], "grille", { lignes: 1, colonnes: 2, decalage: "hexagones", ecartX: 5, ecartY: 3 });
    const c = boite(objets(d)[0].enfants[1]);
    ok("hexagones espacés : 30 + 5 entre colonnes, demi-pas vertical avec l'écart", pres(c.cx, 135) && pres(c.cy, 100 + (Math.sqrt(3) * 20 + 3) / 2), JSON.stringify(c));
  }
}
{
  // régler la grille : les réglages fournis remplacent, les autres restent
  const d = doc(carre("a"));
  const gid = op_repeter(d, ["a"], "grille", { lignes: 2, colonnes: 2, ecartX: 4 });
  op_repetition_regler(d, gid, { colonnes: 5 });
  const g = objets(d)[0];
  ok("régler la grille : 2 × 5", g.enfants.length === 10 && g.repetition.params.ecartX === 4 && g.repetition.params.lignes === 2);
  // un réglage d'un autre mode n'a pas de sens ici : il est ignoré
  op_repetition_regler(d, gid, { nombre: 3 });
  ok("régler la grille avec un réglage radial : ignoré", objets(d)[0].enfants.length === 10 && !("nombre" in objets(d)[0].repetition.params));
}
{
  // refus sans trace
  const d = doc(carre("a"));
  const avant = JSON.stringify(d);
  ok("grille 0 ligne : refus traduit", refus(() => op_repeter(d, ["a"], "grille", { lignes: 0 })) === T("vectorlab.repeter.lignes", { min: 1, max: 50 }));
  ok("grille 51 colonnes : refus", !!refus(() => op_repeter(d, ["a"], "grille", { colonnes: 51 })));
  ok("grille 1 × 1 : refus (une seule instance)", refus(() => op_repeter(d, ["a"], "grille", { lignes: 1, colonnes: 1 })) === T("vectorlab.repeter.une_seule"));
  ok("grille 1 × 2 : accepté (essai)", !refus(() => op_repeter(JSON.parse(avant), ["a"], "grille", { lignes: 1, colonnes: 2 })));
  ok("grille 15 × 15 : refus (plus de 200)", refus(() => op_repeter(d, ["a"], "grille", { lignes: 15, colonnes: 15 })) === T("vectorlab.repeter.trop", { max: 200 }));
  ok("grille 10 × 20 = 200 : accepté (essai)", !refus(() => op_repeter(JSON.parse(avant), ["a"], "grille", { lignes: 10, colonnes: 20 })));
  ok("décalage inconnu : refus", !!refus(() => op_repeter(d, ["a"], "grille", { decalage: "spirale" })));
  ok("écart qui annule le pas : refus", refus(() => op_repeter(d, ["a"], "grille", { ecartX: -20 })) === T("vectorlab.repeter.ecart"));
  ok("écart non numérique : refus traduit", refus(() => op_repeter(d, ["a"], "grille", { ecartY: "x" })) === T("vectorlab.repeter.ecart_invalide"));
  ok("aucune trace après les refus", JSON.stringify(d) === avant);
}

/* ── T3 (t452) répétition en miroir : la source et son reflet par un axe (angle, écart) ── */
{
  // triangle rectangle, angle droit en haut à gauche ; axe vertical (90°) collé au bord droit (x = 110)
  const tri = () => ({ id: "a", type: "path", d: "M90 40 L110 40 L90 60 Z", style: { fond: "#c33" } });
  const d = doc(tri());
  const gid = op_repeter(d, ["a"], "miroir", {});
  const g = objets(d)[0];
  ok("miroir : la source et UN reflet", g.enfants.length === 2 && g.enfants[1].id === `${gid}_r1` && g.enfants[1].genere);
  ok("miroir : réglages par défaut (axe vertical, collé)", JSON.stringify(g.repetition.params) === JSON.stringify({ angle: 90, ecart: 0 }), JSON.stringify(g.repetition.params));
  const r = pts(g.enfants[1]);
  ok("miroir vertical collé : sommets reflétés par x = 110", r.includes("130,40") && r.includes("110,40") && r.includes("130,60") && !r.includes("110,60"), r.join(" "));
  ok("miroir : le document reste valide", !refus(() => parserDoc(d)));
  // l'écart éloigne l'axe : 10 → axe en x = 120, le reflet commence à x = 130
  const d2 = doc(tri());
  op_repeter(d2, ["a"], "miroir", { ecart: 10 });
  const b2 = boite(objets(d2)[0].enfants[1]);
  ok("miroir écart 10 : un jour de 20 entre la source et son reflet", pres(b2.x, 130) && pres(b2.w, 20), JSON.stringify(b2));
  // axe horizontal (0°) : au-dessus de la source (y = 40), le reflet monte
  const d3 = doc(tri());
  op_repeter(d3, ["a"], "miroir", { angle: 0 });
  const r3 = pts(objets(d3)[0].enfants[1]);
  ok("miroir horizontal : reflet au-dessus, par y = 40", r3.includes("90,40") && r3.includes("110,40") && r3.includes("90,20") && !r3.includes("110,20"), r3.join(" "));
  // axe à 45° : chaque sommet a son reflet exact par la droite de l'axe
  const d4 = doc(tri());
  op_repeter(d4, ["a"], "miroir", { angle: 45, ecart: 3 });
  const g4 = objets(d4)[0];
  const src = polylignes_objet(g4.enfants[0])[0].points, ref = polylignes_objet(g4.enfants[1])[0].points;
  const n = [Math.SQRT1_2, -Math.SQRT1_2];          // la normale de l'axe à 45°, hors de la source
  // l'axe : sa normale n pointe hors de la source ; il passe à (la plus grande avancée de la source le long de n) + écart
  const proj = (p) => p[0] * n[0] + p[1] * n[1];
  const axe = Math.max(...src.map(proj)) + 3;
  const reflet = (p) => { const t = proj(p) - axe; return [p[0] - 2 * t * n[0], p[1] - 2 * t * n[1]]; };
  ok("miroir à 45° : chaque sommet a son reflet par l'axe", src.every((p, k) => pres(reflet(p)[0], ref[k][0]) && pres(reflet(p)[1], ref[k][1])), JSON.stringify([src, ref]));
  ok("miroir à 45° : le reflet est du côté de la normale, au-delà de l'écart", ref.every((p) => proj(p) >= axe + 3 - 0.01), JSON.stringify(ref.map(proj)));
  // vivant : la source change, le reflet suit
  g.enfants[0].d = "M90 40 L120 40 L90 60 Z";
  derives_rafraichir(d);
  const r5 = pts(objets(d)[0].enfants[1]);
  ok("miroir vivant : l'axe suit le bord droit élargi (x = 120)", r5.includes("150,40") && r5.includes("120,40") && r5.includes("150,60"), r5.join(" "));
  // une source devenue sans aucun point : le reflet garde son dernier état (pas de transform NaN)
  const dn = doc(tri());
  op_repeter(dn, ["a"], "miroir", {});
  const refletAvant = JSON.stringify(objets(dn)[0].enfants[1]);
  objets(dn)[0].enfants[0] = { ...tri(), d: "M90 40" };      // un chemin réduit à un point isolé : aucun point
  derives_rafraichir(dn);
  ok("miroir : source sans géométrie → reflet gardé", JSON.stringify(objets(dn)[0].enfants[1]) === refletAvant, JSON.stringify(objets(dn)[0].enfants[1]));
  // régler
  op_repetition_regler(d, gid, { angle: 0 });
  ok("régler le miroir : l'angle change, l'écart reste", objets(d)[0].repetition.params.angle === 0 && objets(d)[0].repetition.params.ecart === 0);
  // refus
  const avant = JSON.stringify(doc(tri()));
  const d6 = doc(tri());
  ok("miroir : angle non numérique refusé", refus(() => op_repeter(d6, ["a"], "miroir", { angle: "x" })) === T("vectorlab.repeter.angle"));
  ok("miroir : écart non numérique refusé", refus(() => op_repeter(d6, ["a"], "miroir", { ecart: "x" })) === T("vectorlab.repeter.ecart_invalide"));
  ok("miroir : aucune trace après les refus", JSON.stringify(d6) === avant);
  // un angle au-delà d'un tour se ramène dans [0, 360)
  const d7 = doc(tri());
  op_repeter(d7, ["a"], "miroir", { angle: 450 });
  ok("miroir : 450° = 90°", objets(d7)[0].repetition.params.angle === 90 && pts(objets(d7)[0].enfants[1]).includes("130,60"));
  const d8 = doc(tri());
  op_repeter(d8, ["a"], "miroir", { angle: -90 });
  ok("miroir : -90° = 270°, axe vertical à GAUCHE (x = 90)", objets(d8)[0].repetition.params.angle === 270 && pts(objets(d8)[0].enfants[1]).includes("70,40") && !pts(objets(d8)[0].enfants[1]).includes("110,40"), pts(objets(d8)[0].enfants[1]).join(" "));
}

if (echecs.length) {
  console.error(`repeter : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("repeter : ok");
