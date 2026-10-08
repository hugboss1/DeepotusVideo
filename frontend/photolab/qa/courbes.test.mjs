// qa/courbes.test.mjs — Courbes et Niveaux sur mesure (t138 B4) : fonctions PURES de mod-courbes.js. LUT (niveaux,
// courbe du moteur), édition des points (règles du plan), composition des canaux, histogramme, curseur
// gris, et surtout : tout paramètre produit est admis par la liste blanche (entiers 0..255, x strictement croissants,
// 2..19 points ; niveaux bornés), un canal neutre n'est jamais envoyé.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as CO from "../js/mod-courbes.js";
import { lutNiveaux, lutCourbe, courbeMoteur, ajouterPoint, deplacerPoint, retirerPoint, pointProche,
  appliquerLuts, cheminHistogramme, normaliserNiveaux, normaliserPoints, gammaDepuisCurseur, curseurDepuisGamma,
  estLutIdentite, estCourbeIdentite, estNiveauxNeutres, paramsCourbes, paramsNiveaux, etatDepuisParams, etatNeutre,
  lutsCourbes, lutsNiveaux, versGrille, depuisGrille, horsGrille, MAX_POINTS, ECART_MIN, IDENTITE, CANAUX,
  COMMANDES, niveauxMoteur, lireTable, TAILLE_LUT } from "../js/mod-courbes.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const json = (x) => JSON.stringify(x);
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

// Ce que la liste blanche du pont exige d'une courbe (photolab_registre : 2..19 [x,y] entiers 0..255, x croissants).
function courbeAdmise(p) {
  if (!Array.isArray(p) || p.length < 2 || p.length > 19) return false;
  for (let i = 0; i < p.length; i++) {
    const q = p[i];
    if (!Array.isArray(q) || q.length !== 2 || !q.every((v) => Number.isInteger(v) && v >= 0 && v <= 255)) return false;
    if (i && !(q[0] > p[i - 1][0])) return false;
  }
  return true;
}
const CLES_NIV = ["inBlack", "gamma", "inWhite", "outBlack", "outWhite"];
function niveauxAdmis(n) {
  if (!n || typeof n !== "object" || Object.keys(n).some((k) => !CLES_NIV.includes(k))) return false;
  const e = (k, a, b) => n[k] === undefined || (Number.isInteger(n[k]) && n[k] >= a && n[k] <= b);
  return e("inBlack", 0, 253) && e("inWhite", 2, 255) && e("outBlack", 0, 255) && e("outWhite", 0, 255)
    && (n.gamma === undefined || (typeof n.gamma === "number" && n.gamma >= 0.01 && n.gamma <= 9.99));
}

// 1. lutNiveaux
{
  const id = lutNiveaux({});
  check("1.1 niveaux par défaut = identité", estLutIdentite(id) && id instanceof Uint8ClampedArray && id.length === 256);
  const l = lutNiveaux({ inBlack: 50, inWhite: 200 });
  check("1.2 entrée 50..200 : 50 -> 0, 200 -> 255, sous 50 noir, au-delà blanc", l[50] === 0 && l[200] === 255 && l[10] === 0 && l[250] === 255);
  check("1.3 entrée 50..200 : 125 -> 128 (milieu)", l[125] === 128, l[125]);
  const g = lutNiveaux({ gamma: 2 });
  check("1.4 gamma 2 éclaircit les tons moyens (64 -> 128)", g[64] === 128 && g[0] === 0 && g[255] === 255, g[64]);
  const s = lutNiveaux({ outBlack: 20, outWhite: 220 });
  check("1.5 sortie 20..220", s[0] === 20 && s[255] === 220);
  const inv = lutNiveaux({ outBlack: 255, outWhite: 0 });
  check("1.6 sortie inversée (noir 255, blanc 0) = négatif", inv[0] === 255 && inv[255] === 0 && inv[100] === 155);
  let mono = true; for (let i = 1; i < 256; i++) if (g[i] < g[i - 1]) mono = false;
  check("1.7 LUT de niveaux monotone", mono);
}

// 2. courbes : un seul chemin, la spline naturelle du moteur (plus de Fritsch-Carlson hors moteur)
{
  check("2.1 identité (deux points)", estLutIdentite(lutCourbe(IDENTITE)));
  const plat = lutCourbe([[64, 100], [192, 100]]);
  check("2.2 constante avant le premier et après le dernier point", plat[0] === 100 && plat[255] === 100 && plat[128] === 100);
  const pts = [[0, 0], [64, 40], [128, 128], [192, 220], [255, 255]];
  const fc = lutCourbe(pts);
  check("2.3 la courbe passe par ses points (à 1 niveau près : table de 4096 cases du moteur)", pts.every(([x, y]) => Math.abs(fc[x] - y) <= 1), json(pts.map(([x]) => fc[x])));
  check("2.4 courbeMonotone retirée (inutilisée par l'écran)", !("courbeMonotone" in CO));
  // Un point très haut puis un plateau : la spline naturelle du moteur DÉBORDE (bornée à 255), comme photocraft ;
  // la LUT de l'aperçu JS doit déborder pareil, sinon le glisser montrerait autre chose que le rendu du moteur.
  const raide = [[0, 0], [30, 250], [60, 255], [255, 255]];
  const l = lutCourbe(raide), mr = courbeMoteur(raide);
  let pareil = true; for (let i = 0; i < 256; i++) if (Math.abs(l[i] - mr[i]) > 1) pareil = false;
  let monoR = true; for (let i = 1; i < 256; i++) if (l[i] < l[i - 1]) monoR = false;
  check("2.5 courbe raide : LUT = courbe dessinée (≤ 1 niveau), non monotone comme le moteur", pareil && !monoR);  const m = courbeMoteur([[0, 0], [128, 200], [255, 255]]);
  check("2.6 courbe du moteur : passe par (128, 200) et ses extrémités", Math.round(m[128]) === 200 && m[0] === 0 && m[255] === 255);
  // Contrôle d'une valeur de la spline naturelle à trois points calculée à la main (y'' = 0 aux bouts) :
  // m2[1] = r / b = (0.4331 - 1.5625) / (1/3) = -3.388 ; en x = 64/255, a = b = 0.5 :
  // y = 0.5·0.7843 + 0.375·3.388·h²/6 (h = 0.502) = 0.4455 -> 113.6.
  check("2.7 spline naturelle : valeur intermédiaire attendue", Math.abs(m[64] - 113.6) < 0.2, m[64]);
  const neg = courbeMoteur([[0, 255], [255, 0]]);
  check("2.8 courbe inversée", Math.round(neg[0]) === 255 && Math.round(neg[255]) === 0 && Math.round(neg[100]) === 155);
  check("2.9 points illisibles -> identité", estLutIdentite(lutCourbe("zorg")) && estLutIdentite(lutCourbe([[1]])));
}

// 3. édition des points
{
  const a = ajouterPoint(IDENTITE, 100.4, 140.6);
  check("3.1 ajout : arrondi, trié, index rendu", a && json(a.points) === json([[0, 0], [100, 141], [255, 255]]) && a.index === 1);
  check("3.2 ajout refusé à moins de 4 d'un x existant", ajouterPoint(a.points, 102, 10) === null && ajouterPoint(a.points, 97, 10) === null);
  check("3.3 ajout admis à 4 exactement", ajouterPoint(a.points, 104, 10) !== null && ajouterPoint(a.points, 96, 10) !== null);
  check("3.4 ajout borné à 0..255", json(ajouterPoint(IDENTITE, 50, 999).points[1]) === json([50, 255])
    && json(ajouterPoint(IDENTITE, 60, -40).points[1]) === json([60, 0]));
  let p = IDENTITE.map((q) => q.slice());
  for (let x = 10; p.length < MAX_POINTS; x += 12) p = ajouterPoint(p, x, x).points;
  check("3.5 jusqu'à 19 points, pas un de plus", p.length === 19 && ajouterPoint(p, 250, 3) === null && courbeAdmise(p));
  const d = deplacerPoint(a.points, 1, 300, 80);
  check("3.6 déplacer : x strictement avant le voisin de droite", json(d[1]) === json([254, 80]));
  check("3.7 déplacer : x strictement après le voisin de gauche", json(deplacerPoint(a.points, 1, -9, 80)[1]) === json([1, 80]));
  check("3.8 extrémités : x figé, y libre", json(deplacerPoint(a.points, 0, 90, 30)[0]) === json([0, 30])
    && json(deplacerPoint(a.points, 2, 3, 200)[2]) === json([255, 200]));
  check("3.9 déplacer un index invalide -> null", deplacerPoint(a.points, 7, 1, 1) === null && deplacerPoint(a.points, -1, 1, 1) === null);
  check("3.10 déplacer ne modifie pas l'entrée", json(a.points) === json([[0, 0], [100, 141], [255, 255]]));
  check("3.11 retirer un point intérieur", json(retirerPoint(a.points, 1)) === json(IDENTITE));
  check("3.12 jamais une extrémité ni sous 2 points", retirerPoint(a.points, 0) === null && retirerPoint(a.points, 2) === null
    && retirerPoint(IDENTITE, 1) === null && retirerPoint(IDENTITE, 0) === null);
  check("3.13 point proche dans le rayon", pointProche(a.points, 103, 138, 9) === 1 && pointProche(a.points, 130, 10, 9) === -1);
  // Une rafale de gestes au hasard ne sort jamais de ce que le pont admet.
  let r = IDENTITE.map((q) => q.slice()), admis = true, graine = 7;
  const alea = () => { graine = (graine * 1103515245 + 12345) % 2147483648; return graine / 2147483648; };
  for (let k = 0; k < 2000; k++) {
    const t = alea(), x = alea() * 300 - 20, y = alea() * 300 - 20, i = Math.floor(alea() * r.length);
    const n = t < 0.4 ? (ajouterPoint(r, x, y) || {}).points : t < 0.8 ? deplacerPoint(r, i, x, y) : retirerPoint(r, i);
    if (n) r = n;
    if (!courbeAdmise(r)) { admis = false; break; }
  }
  check("3.14 2000 gestes au hasard : la courbe reste admise par la liste blanche", admis, json(r));
  check("3.15 normaliser : doublons de x, flottants, désordre, hors bornes", json(normaliserPoints([[300, 4.6], [10, 10], [10, 20], [-5, 3]]))
    === json([[0, 3], [10, 20], [255, 5]]));
  const trop = Array.from({ length: 30 }, (_, i) => [i * 8, i * 8]);
  check("3.16 normaliser : 30 points -> 19, extrémités gardées", (() => { const n = normaliserPoints(trop); return n.length === 19 && n[0][0] === 0 && n[18][0] === 232 && courbeAdmise(n); })());
}

// 4. appliquerLuts
{
  const src = { data: new Uint8ClampedArray([10, 20, 30, 40, 200, 100, 0, 255]), width: 2, height: 1 };
  const inv = new Uint8ClampedArray(256).map((_, i) => 255 - i);
  const r = appliquerLuts(src, { r: inv, b: inv });
  check("4.1 LUT par canal, une LUT absente = identité, alpha intact", json(Array.from(r.data)) === json([245, 20, 225, 40, 55, 100, 255, 255]));
  check("4.2 la source n'est pas modifiée, dimensions gardées", src.data[0] === 10 && r.width === 2 && r.height === 1 && r.data !== src.data);
}

// 5. composition des canaux comme le moteur
{
  const etat = { ...etatNeutre("courbes"), rvb: [[0, 0], [255, 128]], rouge: [[0, 255], [255, 0]] };
  const l = lutsCourbes(etat);
  check("5.1 Courbes : composite APRÈS le canal (rouge inversé puis assombri)", l.r[0] === 128 && l.r[255] === 0 && l.g[255] === 128 && l.b[0] === 0);
  const n = lutsNiveaux({ ...etatNeutre("niveaux"), rvb: { inWhite: 128 }, rouge: { outWhite: 100 } });
  check("5.2 Niveaux : canal APRÈS le composite", n.r[128] === 100 && n.r[255] === 100 && n.g[128] === 255 && n.b[64] === 128, [n.r[128], n.g[128], n.b[64]]);
}

// 6. histogramme
{
  const h = new Array(256).fill(0); h[0] = 100; h[255] = 25;
  const d = cheminHistogramme(h, 256, 100);
  check("6.1 chemin fermé, part de la base", d.startsWith("M0 100") && d.endsWith("Z"));
  check("6.2 la case la plus haute touche le haut", d.includes("L0 0 L1 0"));
  check("6.3 racine carrée : 25 sur 100 -> mi-hauteur", d.includes("L255 50 L256 50"), d.slice(-40));
  check("6.4 histogramme vide ou absent : base plate, sans NaN", !/NaN/.test(cheminHistogramme(null, 256, 100)) && !/NaN/.test(cheminHistogramme(new Array(256).fill(0), 10, 10)));
  check("6.5 mise à l'échelle en largeur", cheminHistogramme(h, 512, 100).includes("L510 50 L512 50"));
}

// 7. niveaux bornés comme le registre
{
  check("7.1 défauts", json(normaliserNiveaux({})) === json({ inBlack: 0, gamma: 1, inWhite: 255, outBlack: 0, outWhite: 255 }) && estNiveauxNeutres({}));
  const n = normaliserNiveaux({ inBlack: 300, inWhite: -4, gamma: 50, outBlack: -3, outWhite: 999 });
  check("7.2 bornes : inBlack ≤ 253, inWhite ≥ inBlack + 2, gamma 9.99, sorties 0..255", n.inBlack === 253 && n.inWhite === 255 && n.gamma === 9.99 && n.outBlack === 0 && n.outWhite === 255, json(n));
  const m = normaliserNiveaux({ inBlack: 100, inWhite: 50 });
  check("7.3 noir au-delà du blanc : écart de 2 rétabli", m.inBlack === 100 && m.inWhite === 102);
  check("7.4 entiers, gamma à deux décimales", json(normaliserNiveaux({ inBlack: 3.6, gamma: 1.2345, outWhite: "200" })) === json({ inBlack: 4, gamma: 1.23, inWhite: 255, outBlack: 0, outWhite: 200 }));
  check("7.5 gamma minuscule borné à 0.01, illisible -> 1", normaliserNiveaux({ gamma: 0 }).gamma === 0.01 && normaliserNiveaux({ gamma: "zorg" }).gamma === 1);
  let admis = true;
  for (const v of [{ inBlack: 1e9 }, { inWhite: -1e9 }, { gamma: NaN }, { inBlack: 254, inWhite: 1 }, { outBlack: "x" }]) if (!niveauxAdmis(normaliserNiveaux(v))) admis = false;
  check("7.6 saisies hostiles -> toujours admis", admis);
}

// 8. curseur gris (gamma) et son inverse
{
  check("8.1 gamma 1 : au milieu de noir..blanc", curseurDepuisGamma(1, 0, 255) === 127.5 && curseurDepuisGamma(1, 50, 150) === 100);
  check("8.2 milieu -> gamma 1", gammaDepuisCurseur(127.5, 0, 255) === 1);
  check("8.3 aller-retour (gamma 0.5, 2, 3.3)", [0.5, 2, 3.3].every((g) => Math.abs(gammaDepuisCurseur(curseurDepuisGamma(g, 20, 230), 20, 230) - g) <= 0.01));
  check("8.4 curseur vers le noir = gamma > 1 (éclaircit)", gammaDepuisCurseur(60, 0, 255) > 1 && gammaDepuisCurseur(200, 0, 255) < 1);
  check("8.5 bornes : 0.01..9.99, jamais NaN", gammaDepuisCurseur(-50, 0, 255) <= 9.99 && gammaDepuisCurseur(999, 0, 255) >= 0.01 && Number.isFinite(gammaDepuisCurseur(5, 5, 5)));
}

// 9. paramètres envoyés : jamais de canal neutre, toujours admis
{
  check("9.1 courbes neutres -> {}", json(paramsCourbes(etatNeutre("courbes"))) === "{}");
  const e = { ...etatNeutre("courbes"), bleu: [[0, 0], [128, 160], [255, 255]] };
  check("9.2 canal bleu seul -> {blue}", json(paramsCourbes(e)) === json({ blue: [[0, 0], [128, 160], [255, 255]] }));
  const rvb = { ...etatNeutre("courbes"), rvb: [[0, 10], [64, 50], [128, 128], [192, 210], [255, 250]] };
  const p = paramsCourbes(rvb);
  check("9.3 composite -> points seulement, admis", Object.keys(p).join() === "points" && courbeAdmise(p.points));
  check("9.4 points sur la diagonale = neutre (pas envoyé)", estCourbeIdentite([[0, 0], [100, 100], [255, 255]]) && json(paramsCourbes({ rvb: [[0, 0], [100, 100], [255, 255]] })) === "{}");
  check("9.5 complet (calque de réglage) : les 4 canaux", Object.keys(paramsCourbes(e, { complet: true })).sort().join() === "blue,green,points,red");
  check("9.6 niveaux neutres -> {}", json(paramsNiveaux(etatNeutre("niveaux"))) === "{}");
  const nv = paramsNiveaux({ ...etatNeutre("niveaux"), rvb: { inBlack: 12, gamma: 1.4, inWhite: 240 }, vert: { outWhite: 200 } });
  check("9.7 niveaux : composite au haut, canal sous green, neutres absents",
    nv.inBlack === 12 && nv.gamma === 1.4 && nv.inWhite === 240 && niveauxAdmis(nv.green) && nv.green.outWhite === 200 && !("red" in nv) && !("blue" in nv), json(nv));
  const aller = etatDepuisParams("niveaux", nv);
  check("9.8 aller-retour params -> état -> params (niveaux)", json(paramsNiveaux(aller)) === json(nv));
  const pc = { points: [[0, 0], [90, 120], [255, 255]], red: [[0, 20], [255, 235]] };
  check("9.9 aller-retour params -> état -> params (courbes)", json(paramsCourbes(etatDepuisParams("courbes", pc))) === json(pc));
  check("9.10 canaux de l'écran -> clés de commande et d'histogramme", json(CANAUX.map((c) => [c.id, c.courbe, c.niveaux, c.histo]))
    === json([["rvb", "points", null, "l"], ["rouge", "red", "red", "r"], ["vert", "green", "green", "g"], ["bleu", "blue", "blue", "b"]]));
  check("9.11 commandes destructives", COMMANDES.courbes === "image.adjustments.curves" && COMMANDES.niveaux === "image.adjustments.levels");
}

// 10. grille
{
  check("10.1 versGrille : sortie 255 en haut", json(versGrille([0, 0], 256)) === json({ x: 0, y: 256 }) && json(versGrille([255, 255], 256)) === json({ x: 256, y: 0 }));
  check("10.2 depuisGrille borne à 0..255", json(depuisGrille(-10, 300, 256)) === json([0, 0]) && json(depuisGrille(128, 128, 256)) === json([127.5, 127.5]));
  check("10.3 hors grille au-delà de 12 px seulement", !horsGrille(-11, 50, 256) && horsGrille(-13, 50, 256) && horsGrille(50, 269, 256) && !horsGrille(256, 256, 256));
  check("10.4 ECART_MIN = 4, MAX_POINTS = 19 (registre)", ECART_MIN === 4 && MAX_POINTS === 19);
}

// 11. relecture statique : branchements, jetons, aucune couleur en dur
{
  const src = readFileSync(join(racine, "js/mod-courbes.js"), "utf8");
  check("11.1 réutilise la coquille du dialogue générique", /coquilleReglage\(PL,/.test(src) && /PL\.prendreReglage\(/.test(src) && /PL\.libererReglage\(/.test(src));
  check("11.2 aperçu JS par poserApercu, référence = dernier rendu réel", /PL\.vue\.poserApercu\(image, reference\.maxSide\)/.test(src) && /!rendu\.apercu\) dernierReel = rendu/.test(src));
  check("11.3 aperçu moteur au relâchement (/apercu), OK par PL.executer", /"\/apercu"/.test(src) && /PL\.executer\(id, editeur\.params\(\)\)/.test(src));
  check("11.4 histogramme demandé une fois à l'ouverture", (src.match(/\/histogramme\?/g) || []).length === 1);
  check("11.5 cible (B5) -> layer.setAdjustment", /PL\.executer\("layer\.setAdjustment", \{ layer: cible\.id/.test(src));
  check("11.6 API des éditeurs exportée pour B5", /export function construireEditeurCourbes\(conteneur, opts/.test(src) && /export function construireEditeurNiveaux\(conteneur, opts/.test(src) && /export function construireEditeurTon\(/.test(src));
  const core = readFileSync(join(racine, "js/core.js"), "utf8");
  check("11.7 core.js : initCourbes après initDialogueReglage", core.indexOf("initCourbes(PL)") > core.indexOf("initDialogueReglage(PL)") && core.indexOf("initDialogueReglage(PL)") > 0);
  const css = readFileSync(join(racine, "photolab.css"), "utf8");
  const bloc = css.slice(css.indexOf("t138 B4"));
  check("11.8 CSS B4 : aucune couleur en dur", bloc.length > 100 && !/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/.test(bloc));
  check("11.9 teintes des canaux par jetons", /--pl-canal-rouge: var\(--red\)/.test(bloc) && /--pl-canal-bleu: var\(--blue\)/.test(bloc));
}

// 13. formules du MOTEUR (adjust.rs levels_q, tables de 4096 cases) — valeurs de l'amont, tests.rs
{
  // levels_matches_photoshop : gamma 2.0 continu (sans quantum), écart ≤ 4 niveaux ; gamma 0.5 exact.
  const g2 = [[1, 4], [8, 30], [16, 55], [32, 90], [64, 128], [128, 181], [192, 221], [224, 239]];
  const ecarts = g2.map(([x, ps]) => Math.round(niveauxMoteur({ gamma: 2 }, x / 255, null) * 255) - ps);
  check("13.1 gamma 2 (pied d'ombre) : Photoshop à 4 niveaux près", ecarts.every((e) => Math.abs(e) <= 4), json(ecarts));
  check("13.2 gamma 0.5 exact : (x/255)² ", [0, 32, 64, 128, 192, 255].every((x) => Math.round(niveauxMoteur({ gamma: 0.5 }, x / 255, null) * 255) === Math.round((x / 255) ** 2 * 255)));
  check("13.3 extrémités et identité", niveauxMoteur({ gamma: 2.5 }, 0, null) === 0 && Math.round(niveauxMoteur({ gamma: 2.5 }, 1, null) * 255) === 255
    && Math.abs(niveauxMoteur({}, 0.37, null) - 0.37) < 1e-9);
  // levels_work_on_whole_levels : entrée 44..214, gamma 1.78, en 8 bits par la table de 4096 cases, à 1 niveau près.
  const l = lutNiveaux({ inBlack: 44, inWhite: 214, gamma: 1.78 });
  const ps = [[44, 0], [45, 7], [46, 10], [47, 17], [48, 20], [52, 37], [69, 88], [100, 137], [214, 255]];
  const e2 = ps.map(([v, w]) => l[v] - w);
  check("13.4 niveaux entiers (44..214, gamma 1.78) : Photoshop à 1 niveau près", e2.every((e) => Math.abs(e) <= 1), json(e2));
  check("13.5 quantum hostile -> courbe continue", [0, NaN, -3].every((q) => niveauxMoteur({ inBlack: 44, inWhite: 214, gamma: 1.78 }, 0.2, q) === niveauxMoteur({ inBlack: 44, inWhite: 214, gamma: 1.78 }, 0.2, null)));
  check("13.6 table de 4096 cases, lecture interpolée", TAILLE_LUT === 4096 && lireTable([0, 1], 0.25) === 0.25 && lireTable([0, 1], 7) === 1);
  // Courbes par 4096 cases : à 1 niveau près de la spline évaluée directement en chaque niveau.
  const pts = [[0, 0], [60, 30], [128, 140], [200, 230], [255, 255]];
  const t = lutCourbe(pts), d = courbeMoteur(pts);
  let max = 0; for (let i = 0; i < 256; i++) max = Math.max(max, Math.abs(t[i] - d[i]));
  check("13.7 courbe : table 4096 ≈ spline directe (≤ 1 niveau)", max <= 1, max);
  const tampon = new Uint8ClampedArray(8);
  const r = appliquerLuts({ data: new Uint8ClampedArray([1, 2, 3, 4, 5, 6, 7, 8]), width: 2, height: 1 }, {}, tampon);
  check("13.8 appliquerLuts réutilise le tampon fourni", r.data === tampon && tampon[4] === 5);
}

// 14. relecture statique des corrections de la relecture B4
{
  const src = readFileSync(join(racine, "js/mod-courbes.js"), "utf8");
  check("14.1 glisser : aperçu moteur annulé (minuterie + en vol)", /if \(!fin\) \{\s*\/\/[^\n]*\n\s*clearTimeout\(minuterie\); demander\.annuler\(\); coq\.occupe\(false\);/.test(src));
  check("14.2 OK / Entrée relit les saisies en cours", /valider: \(\) => \{ editeur\.lireSaisies\(\); fermer\("ok"\); \}/.test(src) && (src.match(/lireSaisies\(\) \{/g) || []).length === 2);
  check("14.3 cible : aucun aperçu, éditeur en mode cible (relâchement seul)", /const avecApercu = !cible;/.test(src) && /if \(!avecApercu \|\| !apercuActif\(\) \|\| !luts\) return;/.test(src)
    && /cible: !!cible/.test(src) && (src.match(/opts\.cible && !fin\)\) return;/g) || []).length === 2);
  check("14.4 tampon / ImageData réutilisés, cache vidé à la fermeture", /appliquerLuts\(src, lutsAttente, imageDonnees\.data\)/.test(src) && /cachePixels = null;/.test(src));
  check("14.5 pointercancel / lostpointercapture terminent la prise", (src.match(/lostpointercapture/g) || []).length >= 2 && /fin\(ev, true\)/.test(src));
  check("14.6 grille : role application + aide des gestes", /role: "application"/.test(src) && /aria-description", T\("photolab\.courbes\.aide"\)/.test(src));
}

// 12. Ctrl+M / Ctrl+L : le catalogue les porte, l'entrée est un « dialogue » et l'aiguillage B1 mène ici
{
  const { actionEntree, cibleDialogue } = await import("../js/mod-menus.js");
  const cat = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
  const rac = (id) => ((cat.entrees || []).find((e) => e.id === id) || {}).raccourci;
  check("12.1 catalogue : Courbes = Cmd+M, Niveaux = Cmd+L", rac("image.adjustments.curves") === "Cmd+M" && rac("image.adjustments.levels") === "Cmd+L");
  const json1 = (cle) => ({ cle, type: "json" });
  const courbes = { id: "image.adjustments.curves", etat: "actif", champs: ["points", "red", "green", "blue"].map(json1) };
  const niveaux = { id: "image.adjustments.levels", etat: "actif", champs: [{ cle: "inBlack", type: "number", min: 0, max: 253 }, json1("red")] };
  const dispo = { ouvrirCourbes() {}, ouvrirNiveaux() {}, ouvrirReglage() {} };
  check("12.2 Courbes : dialogue -> courbes", actionEntree(courbes) === "dialogue" && cibleDialogue(courbes, dispo) === "courbes");
  check("12.3 Niveaux : dialogue -> niveaux", actionEntree(niveaux) === "dialogue" && cibleDialogue(niveaux, dispo) === "niveaux");
}

console.log(`courbes : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
