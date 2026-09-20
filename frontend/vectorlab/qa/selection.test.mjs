// selection.test.mjs — mod-selection : l'outil Sélection de classe Affinity
// — déplacement contraint aux axes, cadre de sélection (inclus / touchés),
// boîte d'ancres, poignées d'une boîte, redimensionnement par poignée
// (proportions, depuis le centre), rotation d'ancres. Feuille.
import { contraindre_axe, cadre_selection, bbox_ancres, poignees_bbox, bbox_par_poignee, noeuds_tourner } from "../js/mod-selection.js";
import { chemin_parser, chemin_ancres } from "../js/mod-doc.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 250) : "")); };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
{
  ok("contraindre_axe : l'axe dominant garde son delta, l'autre tombe à 0 ; nul → nul", contraindre_axe(10, 3).join() === "10,0" && contraindre_axe(-2, 9).join() === "0,9" && contraindre_axe(0, 0).join() === "0,0");
  const boites = [{ id: "a", x: 0, y: 0, w: 10, h: 10 }, { id: "b", x: 50, y: 50, w: 10, h: 10 }, { id: "c", x: 8, y: 8, w: 30, h: 30 }];
  ok("cadre_selection inclus : seuls les objets entièrement dans le cadre", cadre_selection(boites, { x: -1, y: -1, w: 20, h: 20 }, "inclus").join() === "a");
  ok("cadre_selection touchés : tout objet qui chevauche", cadre_selection(boites, { x: -1, y: -1, w: 20, h: 20 }, "touches").join() === "a,c");
  ok("cadre_selection : cadre vide ou liste vide → [] ; mode inconnu → inclus", cadre_selection(boites, { x: 0, y: 0, w: 0, h: 0 }, "inclus").length === 0 && cadre_selection([], { x: 0, y: 0, w: 100, h: 100 }, "touches").length === 0 && cadre_selection(boites, { x: -1, y: -1, w: 20, h: 20 }, "zz").join() === "a");
  const an = chemin_ancres(chemin_parser("M 0 0 L 100 0 L 100 50 L 0 50"));
  const b = bbox_ancres(an, [1, 2]);
  ok("bbox_ancres : la boîte des ancres choisies ; une seule ancre → boîte nulle ; aucune → null", b.x === 100 && b.y === 0 && b.w === 0 && b.h === 50 && bbox_ancres(an, [0]).w === 0 && bbox_ancres(an, []) === null);
  const P = poignees_bbox({ x: 10, y: 20, w: 100, h: 50 });
  ok("poignees_bbox : 8 poignées dans l'ordre du cœur (haut-gauche, haut, haut-droit, droit, bas-droit, bas, bas-gauche, gauche) + rotation au-dessus du milieu haut", P.poignees.length === 8 && P.poignees[0].join() === "10,20" && P.poignees[1].join() === "60,20" && P.poignees[4].join() === "110,70" && P.poignees[7].join() === "10,45" && P.rotation[0] === 60 && P.rotation[1] < 20);
  const b0 = { x: 0, y: 0, w: 100, h: 50 };
  ok("bbox_par_poignee : coin bas-droit (4) tiré → largeur / hauteur ; côté droit (3) → largeur seule", (() => { const r = bbox_par_poignee(b0, 4, [150, 100]); const s = bbox_par_poignee(b0, 3, [150, 999]); return r.w === 150 && r.h === 100 && r.x === 0 && s.w === 150 && s.h === 50; })());
  ok("bbox_par_poignee proportions : coin → le plus grand facteur, l'autre côté suit", (() => { const r = bbox_par_poignee(b0, 4, [200, 60], { proportions: true }); return r.w === 200 && r.h === 100; })());
  ok("bbox_par_poignee centre : le centre reste fixe (coin haut-gauche tiré de −10,−10 → boîte 120 × 70 centrée)", (() => { const r = bbox_par_poignee(b0, 0, [-10, -10], { centre: true }); return r.x === -10 && r.y === -10 && r.w === 120 && r.h === 70; })());
  ok("bbox_par_poignee : jamais sous 1 × 1 ; poignée inconnue → boîte d'origine", bbox_par_poignee(b0, 4, [-500, -500]).w === 1 && JSON.stringify(bbox_par_poignee(b0, 9, [1, 1])) === JSON.stringify(b0));
  const segs = chemin_parser("M 0 0 L 100 0 C 120 0 140 20 140 40 L 0 40");
  const r = noeuds_tourner(segs, [1, 2], 100, 0, 90);
  const ar = chemin_ancres(r);
  ok("noeuds_tourner : les ancres choisies ET leurs poignées tournent autour du centre, les autres restent", pres(ar[1].x, 100) && pres(ar[1].y, 0) && pres(ar[2].x, 60) && pres(ar[2].y, 40) && pres(ar[2].entrante.x, 80) && pres(ar[2].entrante.y, 40) && ar[0].x === 0 && ar[3].x === 0, JSON.stringify(ar.map((a) => [a.x, a.y])));
  ok("noeuds_tourner : angle 0 ou aucune ancre → identique", JSON.stringify(noeuds_tourner(segs, [1], 0, 0, 0)) === JSON.stringify(segs) && JSON.stringify(noeuds_tourner(segs, [], 0, 0, 45)) === JSON.stringify(segs));
}
if (echecs.length) { console.error("ECHECS selection :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA selection : PASS (12 controles)");
