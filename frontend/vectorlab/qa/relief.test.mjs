// relief.test.mjs — mod-relief (lot H) : grille de hauteurs → plaque fermée
// (surface, socle, murs), gravure du tracé, découpe en dalles numérotées,
// sous-grille. Les volumes se mesurent ; l'étanchéité se compte par arêtes.
import { plaque, graver, dalles, sous_grille, ruban, tenons, cle } from "../js/mod-relief.js";
import { volume_de } from "../js/mod-extrude.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol) => Math.abs(a - b) <= tol;
// une plaque est étanche si chaque arête orientée (a→b) a son opposée (b→a)
function etanche(tris) {
  const cle = (p) => p.map((v) => Math.round(v * 1e6) / 1e6).join(",");
  const aretes = new Map();
  for (const [a, b, c] of tris) for (const [p, q] of [[a, b], [b, c], [c, a]]) {
    const k = cle(p) + ">" + cle(q);
    aretes.set(k, (aretes.get(k) || 0) + 1);
  }
  for (const [k, n] of aretes) {
    const [p, q] = k.split(">");
    if (n !== 1 || aretes.get(q + ">" + p) !== 1) return false;
  }
  return true;
}

/* ── plaque plate : 3×3 cellules de hauteur 10 m, 30 mm de large ── */
{
  const grid = new Array(9).fill(10);
  const tris = plaque(grid, 3, 3, { largeur_mm: 30, socle_mm: 2, mm_par_m: 0.1, exageration: 1, z_min: 0 });
  const v = volume_de(tris);
  ok("volume = 30 × 30 × (2 + 10·0,1) = 2700 mm³", pres(v, 2700, 1e-6), v);
  ok("z max = socle + hauteur = 3 mm ; z min = 0", pres(Math.max(...tris.flat().map((p) => p[2])), 3, 1e-9) && pres(Math.min(...tris.flat().map((p) => p[2])), 0, 1e-9));
  ok("étanche : chaque arête a son opposée", etanche(tris));
  ok("8 triangles de surface + 8 de fond + 4 côtés × 2 cellules × 2 = 32", tris.length === 32, tris.length);
  // exagération ×3 : la surface monte, le socle non
  const t3 = plaque(grid, 3, 3, { largeur_mm: 30, socle_mm: 2, mm_par_m: 0.1, exageration: 3, z_min: 0 });
  ok("exagération 3 : z max = 2 + 3", pres(Math.max(...t3.flat().map((p) => p[2])), 5, 1e-9));
  // z_min : la hauteur de référence — une grille entre 100 et 110 m avec z_min 100 donne le même solide
  const g2 = new Array(9).fill(110);
  ok("z_min soustrait : 110 m avec z_min 100 = 10 m", pres(volume_de(plaque(g2, 3, 3, { largeur_mm: 30, socle_mm: 2, mm_par_m: 0.1, exageration: 1, z_min: 100 })), 2700, 1e-6));
  // la hauteur de la plaque suit le ratio w/h de la grille : 4×2 cellules → 30 × 10 mm
  const g4 = new Array(8).fill(0);
  const t4 = plaque(g4, 4, 2, { largeur_mm: 30, socle_mm: 1, mm_par_m: 0.1, exageration: 1, z_min: 0 });
  ok("plaque 4×2 : 30 mm × 10 mm, socle seul → 300 mm³", pres(volume_de(t4), 300, 1e-6), volume_de(t4));
  let refus = 0;
  try { plaque([1, 2], 2, 1, { largeur_mm: 30, socle_mm: 1, mm_par_m: 0.1 }); } catch { refus++; }
  try { plaque(grid, 3, 3, { largeur_mm: 30, socle_mm: 0, mm_par_m: 0.1 }); } catch { refus++; }
  ok("refus : grille < 2×2 ; socle ≤ 0", refus === 2, String(refus));
}
/* ── gravure ── */
{
  const grid = new Array(25).fill(100);           // 5×5
  const g = graver(grid, 5, 5, [[[0, 2], [4, 2]]], 20, 0.6);   // une ligne horizontale au milieu
  ok("copie : l'original n'est pas touché", grid.every((v) => v === 100));
  ok("la ligne du milieu est abaissée de 20, les autres non", [10, 11, 12, 13, 14].every((i) => g[i] === 80) && [0, 4, 20, 24, 7].every((i) => g[i] === 100), g.join(","));
  ok("rayon 1,2 : les lignes voisines aussi", graver(grid, 5, 5, [[[0, 2], [4, 2]]], 20, 1.2)[7] === 80);
}
/* ── dalles ── */
{
  // 9 sommets = 8 cellules en x, 5 sommets = 4 cellules en y ; 3 cellules par dalle
  const d = dalles(9, 5, 3);
  ok("9×5 en dalles de 3 cellules : 3 × 2 = 6 dalles, bord PARTAGÉ (la dalle suivante repart du dernier sommet)", d.length === 6
     && d[0].x0 === 0 && d[0].w === 4 && d[1].x0 === 3 && d[1].w === 4 && d[2].x0 === 6 && d[2].w === 3
     && d[3].y0 === 3 && d[3].h === 2, JSON.stringify(d));
  ok("noms numérotés ligne_colonne", d[0].nom === "dalle_1_1" && d[1].nom === "dalle_1_2" && d[3].nom === "dalle_2_1", JSON.stringify(d.map((x) => x.nom)));
  ok("9×5 en dalles de 4 : 2 dalles côte à côte", dalles(9, 5, 4).length === 2 && dalles(9, 5, 4)[1].x0 === 4);
  ok("chaque dalle couvre ≥ 2 sommets par axe et la réunion couvre toute la grille",
     d.every((x) => x.w >= 2 && x.h >= 2) && Math.max(...d.map((x) => x.x0 + x.w)) === 9 && Math.max(...d.map((x) => x.y0 + x.h)) === 5, JSON.stringify(d));
  ok("une grille qui tient → une seule dalle", dalles(4, 4, 10).length === 1);
  const grid = [...Array(45).keys()];             // 9×5, valeur = index
  const sg = sous_grille(grid, 9, 5, d[1]);
  ok("sous-grille de la dalle 2 : w×h valeurs, première = index (x0 + y0·9)", sg.w === d[1].w && sg.h === d[1].h && sg.grid.length === sg.w * sg.h && sg.grid[0] === d[1].x0 + d[1].y0 * 9, JSON.stringify(sg).slice(0, 80));
}

/* ── t124 : le ruban, mur fermé qui suit le tracé à l'altitude enregistrée, base plate à z=0 ── */
{
  const plat = ruban([[0, 0, 5], [10, 0, 5]], 2);
  ok("ruban droit : étanche, volume = longueur × épaisseur × hauteur (100)", etanche(plat) && pres(volume_de(plat), 100, 1e-6), volume_de(plat));
  const ys = plat.flat().map((p) => p[1]), zs = plat.flat().map((p) => p[2]);
  ok("ruban droit : ±1 mm de part et d'autre, de 0 à 5", Math.min(...ys) === -1 && Math.max(...ys) === 1 && Math.min(...zs) === 0 && Math.max(...zs) === 5);
  const pente = ruban([[0, 0, 2], [10, 0, 6]], 2);
  ok("ruban en pente : le sommet suit l'altitude (volume 80)", etanche(pente) && pres(volume_de(pente), 80, 1e-6), volume_de(pente));
  const coude = ruban([[0, 0, 4], [10, 0, 4], [10, 10, 4], [10, 10, 4]], 1);
  ok("ruban coudé (doublon final ignoré) : étanche, volume ≈ 20 × 1 × 4", etanche(coude) && pres(volume_de(coude), 80, 0.6), volume_de(coude));
  let refus = 0;
  for (const f of [() => ruban([[0, 0, 1]], 1), () => ruban([[0, 0, 1], [1, 0, 1]], 0), () => ruban([[0, 0, 0], [1, 0, 0]], 1)]) { try { f(); } catch { refus++; } }
  ok("ruban : un point, épaisseur nulle, hauteur nulle → refus", refus === 3, refus);
}
/* ── t124 : tenons — logements creusés sous le socle, moitié dans chaque dalle, clés séparées ── */
{
  const plat = new Array(25).fill(0);          // 4 × 4 cellules de 10 mm, socle 3 → 4800 mm³
  const base = { largeur_mm: 40, socle_mm: 3, mm_par_m: 1, exageration: 1, z_min: 0 };
  const bord = plaque(plat, 5, 5, { ...base, logements: [{ i0: 3, j0: 1, ni: 1, nj: 2 }], prof_logement: 2 });
  ok("logement au bord : étanche, volume ôté = 10 × 20 × 2", etanche(bord) && pres(volume_de(bord), 4800 - 400, 1e-6), volume_de(bord));
  const fondPoche = bord.flat().filter((p) => p[2] === 2 && p[0] >= 30 && p[1] >= 20 && p[1] <= 30);
  ok("logement au bord : son plafond est à 2 mm, côté est (x 30→40), rangées 1-2 (y 10→30 depuis le sud) ; dedans, aucun autre sommet à 2 mm",
     fondPoche.length > 0 && bord.flat().filter((p) => p[2] === 2 && p[0] > 0 && p[0] < 40 && p[1] > 0 && p[1] < 40).every((p) => p[0] >= 30 && p[1] >= 10 && p[1] <= 30), fondPoche.length);
  const dedans = plaque(plat, 5, 5, { ...base, logements: [{ i0: 1, j0: 1, ni: 2, nj: 2 }], prof_logement: 2 });
  ok("logement intérieur : étanche, volume ôté = 20 × 20 × 2", etanche(dedans) && pres(volume_de(dedans), 4800 - 800, 1e-6), volume_de(dedans));
  // au bord SUD (rangée h−2) : le mur sud doit se couper au niveau de la poche
  const sud = plaque(plat, 5, 5, { ...base, logements: [{ i0: 1, j0: 3, ni: 2, nj: 1 }], prof_logement: 2 });
  ok("logement au bord sud : étanche, volume ôté = 20 × 10 × 2", etanche(sud) && pres(volume_de(sud), 4800 - 400, 1e-6), volume_de(sud));
  ok("sans logement : la plaque d'avant, à l'octet", JSON.stringify(plaque(plat, 5, 5, base)) === JSON.stringify(plaque(plat, 5, 5, { ...base, logements: [] })));

  // deux dalles côte à côte : 21 × 11 sommets, 10 cellules par dalle, cellule 5 mm
  const P2 = dalles(21, 11, 10);
  const T = tenons(P2, 5, 3);
  const A = T.par_dalle[P2[0].nom], B = T.par_dalle[P2[1].nom];
  ok("deux dalles : deux logements par moitié, contre l'arête commune", A.length === 2 && B.length === 2
     && A.every((r) => r.i0 + r.ni === 10) && B.every((r) => r.i0 === 0), JSON.stringify(T.par_dalle));
  ok("les deux moitiés se font face (mêmes rangées)", JSON.stringify(A.map((r) => [r.j0, r.nj])) === JSON.stringify(B.map((r) => [r.j0, r.nj])), JSON.stringify([A, B]));
  ok("profondeur = socle − 0,8 (2,2) ; clé = poche − 0,2 mm de jeu par face, hauteur − 0,2",
     pres(T.prof, 2.2, 1e-9) && T.cles.length === 2 && T.cles.every((c) => pres(c.lx, 2 * A[0].ni * 5 - 0.4, 1e-9) && pres(c.ly, A[0].nj * 5 - 0.4, 1e-9) && pres(c.h, 2.0, 1e-9)),
     JSON.stringify(T.cles));
  // deux dalles l'une sur l'autre : l'arête commune est horizontale, les poches s'allongent en x
  const PV = dalles(11, 21, 10), TV = tenons(PV, 5, 3);
  const H = TV.par_dalle[PV[0].nom], Bas = TV.par_dalle[PV[1].nom];
  ok("arête horizontale : poches kb × ka contre l'arête, en haut de la dalle du bas", H.length === 2
     && H.every((r) => r.j0 + r.nj === 10 && r.ni === 2 && r.nj === 1) && Bas.every((r) => r.j0 === 0 && r.ni === 2 && r.nj === 1)
     && TV.cles.every((c) => pres(c.lx, 9.6, 1e-9) && pres(c.ly, 9.6, 1e-9)), JSON.stringify(TV));
  const P4 = dalles(21, 21, 10), T4 = tenons(P4, 5, 3);
  ok("quatre dalles : quatre arêtes communes, deux clés chacune", T4.cles.length === 8
     && Object.values(T4.par_dalle).every((l) => l.length === 4), JSON.stringify(Object.values(T4.par_dalle).map((l) => l.length)));
  // la dalle de droite d'un découpage inégal n'a qu'une cellule : rien à y creuser (une moitié tomberait dans le vide)
  const Pn = dalles(12, 11, 10), Tn = tenons(Pn, 5, 3);
  ok("dalle d'une seule cellule de large : pas de logement, raison dite", Tn.cles.length === 0 && /étroite/.test(Tn.raison || ""), JSON.stringify(Tn));
  const Tm = tenons(P2, 5, 1.2);
  ok("socle trop mince : pas de logement, raison dite", Tm.cles.length === 0 && /socle/.test(Tm.raison || ""), JSON.stringify(Tm));
  const c = cle(9.6, 4.6, 2, 100, 50);
  const xs = c.flat().map((p) => p[0]);
  ok("clé : boîte étanche, volume lx × ly × h, posée en (100,50)", etanche(c) && pres(volume_de(c), 9.6 * 4.6 * 2, 1e-6) && Math.min(...xs) === 100, volume_de(c));
}
if (echecs.length) {
  console.error("ECHECS relief :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA relief : PASS (34 controles)");
