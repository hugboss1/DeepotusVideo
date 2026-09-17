// grille.test.mjs — mod-grille (lot C) : normalisation, hex axial (centre,
// sommets, point→axial), lignes des quatre grilles bornées à la page,
// aimantation à la grille, garde de densité. Aucun DOM, aucun import de
// mod-doc (le module est feuille).
import { GRILLE_TYPES, grille_normaliser, hex_centre, hex_sommets, hex_d,
         hex_depuis_point, grille_d, grille_aimanter, grille_cellules }
  from "../js/mod-grille.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, e = 1e-6) => Math.abs(a - b) <= e;
const S3 = Math.sqrt(3);

/* ── normalisation ── */
{
  ok("types", JSON.stringify(GRILLE_TYPES) === JSON.stringify(["carree", "iso", "tri", "hex"]));
  const g = grille_normaliser({ type: "hex", pas: 32 });
  ok("défauts : sous 1, pointe, origine 0, échelle 1", g.sous === 1 && g.orientation === "pointe"
     && g.origine[0] === 0 && g.echelle[1] === 1, JSON.stringify(g));
  let refus = 0;
  for (const m of [null, { type: "octo", pas: 8 }, { type: "hex", pas: 0 }, { type: "carree", pas: 8, sous: 0 },
                   { type: "hex", pas: 8, orientation: "biais" }, { type: "hex", pas: 8, origine: [1] },
                   { type: "hex", pas: 8, echelle: [0, 1] }]) {
    try { grille_normaliser(m); } catch { refus++; }
  }
  ok("7 grilles malformées refusées", refus === 7, String(refus));
}
/* ── hexagones pointe ── */
{
  const g = grille_normaliser({ type: "hex", pas: 10 });
  const c00 = hex_centre(0, 0, g), c10 = hex_centre(1, 0, g), c01 = hex_centre(0, 1, g);
  ok("pointe : centre (0,0) à l'origine", pres(c00[0], 0) && pres(c00[1], 0));
  ok("pointe : (1,0) à √3·s en x", pres(c10[0], 10 * S3) && pres(c10[1], 0), c10.join(","));
  ok("pointe : (0,1) à (√3/2·s, 1,5·s)", pres(c01[0], 5 * S3) && pres(c01[1], 15), c01.join(","));
  const s = hex_sommets(0, 0, 10, "pointe");
  ok("6 sommets, le premier en haut (angle -90°)", s.length === 6 && pres(s[0][0], 0) && pres(s[0][1], -10), JSON.stringify(s[0]));
  ok("hex_d fermé, canonique 2 déc.", /^M -?\d/.test(hex_d(0, 0, 10, "pointe")) && hex_d(0, 0, 10, "pointe").endsWith("Z")
     && hex_d(0, 0, 10, "pointe").split(" L ").length === 6, hex_d(0, 0, 10, "pointe"));
  // point → axial : le centre de chaque cellule revient sur elle-même
  for (const [q, r] of [[0, 0], [3, -2], [-4, 5], [7, 7]]) {
    const [x, y] = hex_centre(q, r, g);
    const a = hex_depuis_point(x + 2, y - 3, g);           // près du centre
    ok(`point→axial (${q},${r})`, a.q === q && a.r === r, JSON.stringify(a));
  }
  // origine et échelle s'appliquent
  const g2 = grille_normaliser({ type: "hex", pas: 10, origine: [100, 50], echelle: [2, 1] });
  const c = hex_centre(1, 0, g2);
  ok("origine + échelle : (1,0) → (100 + 2·√3·10, 50)", pres(c[0], 100 + 20 * S3) && pres(c[1], 50), c.join(","));
  ok("inverse avec origine/échelle", (() => { const a = hex_depuis_point(c[0], c[1], g2); return a.q === 1 && a.r === 0; })());
}
/* ── hexagones plat ── */
{
  const g = grille_normaliser({ type: "hex", pas: 10, orientation: "plat" });
  const c10 = hex_centre(1, 0, g), c01 = hex_centre(0, 1, g);
  ok("plat : (1,0) à (1,5·s, √3/2·s)", pres(c10[0], 15) && pres(c10[1], 5 * S3), c10.join(","));
  ok("plat : (0,1) à (0, √3·s)", pres(c01[0], 0) && pres(c01[1], 10 * S3));
  const s = hex_sommets(0, 0, 10, "plat");
  ok("plat : premier sommet à droite (angle 0°)", pres(s[0][0], 10) && pres(s[0][1], 0));
  ok("plat : inverse", (() => { const a = hex_depuis_point(c10[0] + 1, c10[1] + 1, g); return a.q === 1 && a.r === 0; })());
}
/* ── cellules d'un plateau ── */
{
  ok("rayon 0 → 1 cellule ; rayon 1 → 7 ; rayon 2 → 19",
     grille_cellules({ mode: "rayon", rayon: 0 }).length === 1
     && grille_cellules({ mode: "rayon", rayon: 1 }).length === 7
     && grille_cellules({ mode: "rayon", rayon: 2 }).length === 19);
  const rect = grille_cellules({ mode: "rect", colonnes: 4, lignes: 3 });
  ok("rect 4×3 → 12 cellules, coordonnées entières distinctes", rect.length === 12
     && new Set(rect.map((c) => c.q + "," + c.r)).size === 12);
  let refus = 0;
  for (const m of [{ mode: "rayon", rayon: -1 }, { mode: "rect", colonnes: 0, lignes: 2 }, { mode: "x" }, { mode: "rayon", rayon: 80 }]) {
    try { grille_cellules(m); } catch { refus++; }
  }
  ok("4 spécifications refusées (dont rayon > 60)", refus === 4, String(refus));
}
/* ── lignes bornées à la page ── */
{
  const T = { w: 100, h: 50 };
  const dC = grille_d(grille_normaliser({ type: "carree", pas: 25 }), T);
  ok("carrée 25 : 3 verticales + 1 horizontale intérieures", (dC.match(/M/g) || []).length === 4, dC);
  const dS = grille_d(grille_normaliser({ type: "carree", pas: 25, sous: 5 }), T);
  ok("subdivisions ÷5 : 19 verticales + 9 horizontales", (dS.match(/M/g) || []).length === 28, (dS.match(/M/g) || []).length);
  const dansPage = (d, W, H) => d.split(/[ML]/).filter((p) => p.trim()).every((p) => {
    const [x, y] = p.trim().split(/\s+/).map(Number);
    return x >= -1e-6 && x <= W + 1e-6 && y >= -1e-6 && y <= H + 1e-6;
  });
  const dI = grille_d(grille_normaliser({ type: "iso", pas: 20 }), T);
  ok("iso : des lignes, toutes dans la page", (dI.match(/M/g) || []).length > 6 && dansPage(dI, 100, 50), dI.slice(0, 120));
  const dT = grille_d(grille_normaliser({ type: "tri", pas: 20 }), T);
  ok("tri : trois directions (des horizontales + des obliques), dans la page",
     /M 0 \d+(\.\d+)? L 100 \d+(\.\d+)?/.test(dT) && (dT.match(/M/g) || []).length > 6 && dansPage(dT, 100, 50), dT.slice(0, 120));
  const dH = grille_d(grille_normaliser({ type: "hex", pas: 10 }), T);
  ok("hex : des hexagones fermés couvrant la page", (dH.match(/Z/g) || []).length >= 30 && (dH.match(/Z/g) || []).length <= 80, (dH.match(/Z/g) || []).length);
  ok("trop dense → chaîne vide (garde de densité)", grille_d(grille_normaliser({ type: "hex", pas: 1 }), { w: 3000, h: 3000 }) === "");
}
/* ── aimantation à la grille ── */
{
  const c = grille_normaliser({ type: "carree", pas: 20, sous: 2 });
  ok("carrée ÷2 : 27,4 → 30 ; 12 → 10", grille_aimanter(c, 27.4, 12).join(",") === "30,10");
  const o = grille_normaliser({ type: "carree", pas: 20, origine: [5, 5] });
  ok("origine décalée : 27 → 25", grille_aimanter(o, 27, 27).join(",") === "25,25");
  const h = grille_normaliser({ type: "hex", pas: 10 });
  const [cx, cy] = hex_centre(2, 1, h);
  const a = grille_aimanter(h, cx + 1, cy + 1);
  ok("hex : près d'un centre → le centre", pres(a[0], cx, 1e-6) && pres(a[1], cy, 1e-6), a.join(","));
  const som = hex_sommets(cx, cy, 10, "pointe")[0];
  const b = grille_aimanter(h, som[0] + 0.5, som[1] - 0.5);
  ok("hex : près d'un sommet → le sommet", pres(b[0], som[0]) && pres(b[1], som[1]), b.join(","));
  const t = grille_normaliser({ type: "tri", pas: 20 });
  const p = grille_aimanter(t, 10.3, 17.1);
  ok("tri : sommet du réseau (10, 10√3)", pres(p[0], 10) && pres(p[1], 10 * S3), p.join(","));
  const i = grille_normaliser({ type: "iso", pas: 20 });
  const pi = grille_aimanter(i, 17.5, 9.8);
  ok("iso : sommet du réseau (√3·10, 10)", pres(pi[0], 10 * S3) && pres(pi[1], 10), pi.join(","));
}

if (echecs.length) {
  console.error("ECHECS grille :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA grille : PASS (33 controles)");
