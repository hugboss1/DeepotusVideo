// repeter.test.mjs — lot D2 « Répéter et fusionner » (t450…) : les objets vivants de js/mod-repeter.js.
// T1 (t450) Répétition radiale : un groupe vivant [source, ...copies générées] ; les copies suivent la source dans
// la même étape (derives_rafraichir), seule une empreinte changée coûte un recalcul ; régler, décomposer, refus sans
// trace. Au passage : la matrice des booléens lit translate / scale / matrix / skew (les copies en dépendent).
import { polylignes_objet } from "../js/mod-bool.js";
import { op_repeter, op_repetition_regler } from "../js/mod-repeter.js";
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
import { parserDoc } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

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

if (echecs.length) {
  console.error(`repeter : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("repeter : ok");
