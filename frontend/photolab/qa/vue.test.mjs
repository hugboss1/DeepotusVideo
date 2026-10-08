// qa/vue.test.mjs — fonctions pures du canevas (B2) : paliers de zoom, ajuster, conversions, zoom autour d'un point,
// taille de rendu, interprétation de la molette.
import { PALIERS, palier, ajuster, versDoc, versEcran, zoomAutour, tailleRendu, changementSensible, gesteMolette, panoramique, tuilesVisibles, toucheZoom, formaterZoom, ctrlSurPage } from "../js/mod-vue.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const proche = (a, b, e = 1e-9) => Math.abs(a - b) <= e;

// 1. paliers
check("1.1 25 paliers de 1 % à 6400 %", PALIERS.length === 25 && PALIERS[0] === 0.01 && PALIERS[24] === 64);
check("1.2 croissants", PALIERS.every((p, i) => i === 0 || p > PALIERS[i - 1]));
check("1.3 palier(1,+1)=2", palier(1, +1) === 2);
check("1.4 palier(1,-1)=0.6667", palier(1, -1) === 0.6667);
check("1.5 borne haute", palier(64, +1) === 64 && palier(100, +1) === 64);
check("1.6 borne basse", palier(0.01, -1) === 0.01 && palier(0.001, -1) === 0.01);
check("1.7 entre deux paliers", palier(0.55, +1) === 0.6667 && palier(0.55, -1) === 0.5);
check("1.8 tolérance flottante : 0.6667 -> 1 / 0.5", palier(0.6667, +1) === 1 && palier(0.6667000001, -1) === 0.5);

// 2. ajuster (marge par côté : 1920×1080 dans 1000×600, marge 16 -> min(968/1920, 568/1080))
const a = ajuster({ w: 1920, h: 1080 }, { w: 1000, h: 600 }, 16);
check("2.1 ajuster 1920×1080", proche(a, 968 / 1920, 1e-9), a);
check("2.2 le document tient dans la vue", 1920 * a <= 1000 - 32 + 1e-9 && 1080 * a <= 600 - 32 + 1e-9);
check("2.3 borné à 64", ajuster({ w: 1, h: 1 }, { w: 1000, h: 600 }) === 64);
check("2.4 borné à 0.01", ajuster({ w: 100000, h: 100000 }, { w: 100, h: 100 }) === 0.01);
check("2.5 vue plus petite que la marge -> 0.01", ajuster({ w: 10, h: 10 }, { w: 20, h: 20 }, 16) === 0.01);

// 3. conversions
const v = { z: 2.5, ox: 37, oy: -12 };
const d = versDoc(v, 300, 200);
check("3.1 versDoc", proche(d.x, (300 - 37) / 2.5) && proche(d.y, (200 + 12) / 2.5));
const e = versEcran(v, d.x, d.y);
check("3.2 aller-retour", proche(e.x, 300) && proche(e.y, 200));

// 4. zoomAutour garde le point fixe
for (const [z2, px, py] of [[4, 120, 80], [0.25, 500, 333], [64, 0, 0], [1, 77, 91]]) {
  const avant = versDoc(v, px, py);
  const w = zoomAutour(v, z2, px, py);
  const apres = versEcran(w, avant.x, avant.y);
  check(`4 zoomAutour z=${z2}`, proche(w.z, z2) && proche(apres.x, px, 1e-9) && proche(apres.y, py, 1e-9), JSON.stringify(w));
}
check("4.1 zoom borné", zoomAutour(v, 1000, 10, 10).z === 64 && zoomAutour(v, 0.0001, 10, 10).z === 0.01);
check("4.2 la vue d'origine n'est pas modifiée", v.z === 2.5 && v.ox === 37 && v.oy === -12);

// 5. taille de rendu
const D = { w: 1920, h: 1080 };
check("5.1 z 0.5 -> 960", tailleRendu(D, 0.5) === 960);
check("5.2 z 1 dpr 1 -> 1920", tailleRendu(D, 1, 1) === 1920);
check("5.3 z 2 -> 0 (taille réelle)", tailleRendu(D, 2) === 0);
check("5.4 6000×4000 z 1 -> 2048", tailleRendu({ w: 6000, h: 4000 }, 1) === 2048);
check("5.5 plancher 64", tailleRendu(D, 0.01) === 64);
check("5.6 jamais plus que le document", tailleRendu({ w: 500, h: 300 }, 2) === 500);
check("5.7 dpr compte : z 0.5 dpr 2 -> 1920", tailleRendu(D, 0.5, 2) === 1920);
check("5.8 document > 4096 et besoin > 2048 -> 2048", tailleRendu({ w: 5000, h: 100 }, 2) === 2048);
check("5.9 petit document : jamais sous sa taille", tailleRendu({ w: 20, h: 10 }, 1) === 20);

// 6. besoin d'un nouveau rendu : écart de plus de 25 %
check("6.1 identique", changementSensible(960, 960) === false);
check("6.2 +20 % : non", changementSensible(1000, 1200) === false);
check("6.3 +30 % : oui", changementSensible(1000, 1300) === true);
check("6.4 -30 % : oui", changementSensible(1000, 700) === true);
check("6.5 vers la taille réelle (0) : oui, jamais de division par 0", changementSensible(960, 0) === true && changementSensible(0, 0) === false);
check("6.6 pas de rendu précédent : oui", changementSensible(null, 960) === true);

// 7. molette
const g1 = gesteMolette({ deltaX: 0, deltaY: -100, ctrlKey: true, altKey: false, shiftKey: false });
check("7.1 Ctrl+molette = zoom, vers le haut agrandit", g1.type === "zoom" && g1.facteur > 1, JSON.stringify(g1));
check("7.2 Ctrl+molette vers le bas réduit", gesteMolette({ deltaY: 100, ctrlKey: true }).facteur < 1);
const g3 = gesteMolette({ deltaY: -3, altKey: true });
check("7.3 Alt = ×1,05 par cran", g3.type === "zoom" && proche(g3.facteur, 1.05) && proche(gesteMolette({ deltaY: 3, altKey: true }).facteur, 1 / 1.05));
const g4 = gesteMolette({ deltaX: 0, deltaY: 40 });
check("7.4 molette = panoramique vertical", g4.type === "pan" && g4.dx === 0 && g4.dy === -40, JSON.stringify(g4));
const g5 = gesteMolette({ deltaX: 0, deltaY: 40, shiftKey: true });
check("7.5 Maj = horizontal", g5.type === "pan" && g5.dx === -40 && g5.dy === 0, JSON.stringify(g5));
check("7.6 deltaX natif conservé", gesteMolette({ deltaX: 12, deltaY: 0 }).dx === -12);

// 8. panoramique
const p = panoramique({ z: 2, ox: 10, oy: 20 }, 5, -7);
check("8.1 panoramique", p.z === 2 && p.ox === 15 && p.oy === 13);

// 9. damier : seules les tuiles visibles sont dessinées (C1 : à 6400 % le document fait 122880 px de large)
const fen = { w: 1000, h: 700 };
const borne = (Math.ceil(fen.w / 8) + 2) * (Math.ceil(fen.h / 8) + 2);
const compte = (r) => Math.max(0, r.i1 - r.i0 + 1) * Math.max(0, r.j1 - r.j0 + 1);
const gros = tuilesVisibles({ z: 64, ox: -50000, oy: -30000 }, { w: 1920, h: 1080 }, fen, 8);
check("9.1 6400 % : tuiles bornées par la vue", compte(gros) > 0 && compte(gros) <= borne, compte(gros));
const bord = tuilesVisibles({ z: 64, ox: -121900, oy: -69000 }, { w: 1920, h: 1080 }, fen, 8);
check("9.2 6400 % au bord du document : borné aussi", compte(bord) <= borne, compte(bord));
check("9.3 document hors vue : aucune tuile", compte(tuilesVisibles({ z: 1, ox: 2000, oy: 0 }, { w: 100, h: 100 }, fen, 8)) === 0 && compte(tuilesVisibles({ z: 1, ox: -500, oy: 0 }, { w: 100, h: 100 }, fen, 8)) === 0);
const p9 = tuilesVisibles({ z: 0.5, ox: 10, oy: 10 }, { w: 100, h: 50 }, fen, 8);
check("9.4 petit document entier : 7×4 tuiles", p9.i0 === 0 && p9.i1 === 6 && p9.j0 === 0 && p9.j1 === 3, JSON.stringify(p9));
const p10 = tuilesVisibles({ z: 1, ox: -17, oy: 0 }, { w: 100, h: 16 }, fen, 8);
check("9.5 document rogné à gauche : première tuile partielle", p10.i0 === 2 && p10.i1 === 12, JSON.stringify(p10));
const p11 = tuilesVisibles({ z: 1, ox: 950, oy: 0 }, { w: 400, h: 16 }, fen, 8);
check("9.6 document rogné à droite : s'arrête au bord de la vue", p11.i0 === 0 && p11.i1 === 6, JSON.stringify(p11));

// 10. touches de zoom : e.code d'abord (AZERTY : le chiffre 0 donne key "à"), e.key en repli
check("10.1 AZERTY Ctrl+0", toucheZoom({ key: "à", code: "Digit0" }) === "ajuster");
check("10.2 AZERTY Ctrl+1 (key &)", toucheZoom({ key: "&", code: "Digit1" }) === "cent");
check("10.3 pavé numérique", toucheZoom({ key: "0", code: "Numpad0" }) === "ajuster" && toucheZoom({ key: "1", code: "Numpad1" }) === "cent"
  && toucheZoom({ key: "+", code: "NumpadAdd" }) === "plus" && toucheZoom({ key: "-", code: "NumpadSubtract" }) === "moins");
check("10.4 = et -", toucheZoom({ key: "=", code: "Equal" }) === "plus" && toucheZoom({ key: "-", code: "Minus" }) === "moins");
check("10.5 repli sur key sans code", toucheZoom({ key: "0" }) === "ajuster" && toucheZoom({ key: "+" }) === "plus" && toucheZoom({ key: "_" }) === "moins");
check("10.6 autres touches : rien", toucheZoom({ key: "a", code: "KeyA" }) === null && toucheZoom({ key: "Enter", code: "Enter" }) === null);

// 11. affichage du zoom selon la langue
check("11.1 fr", formaterZoom(0.5, "fr") === "50 %" && formaterZoom(1, "fr") === "100 %");
check("11.2 fr virgule décimale", formaterZoom(0.5146, "fr") === "51,46 %");
check("11.3 en", formaterZoom(0.5146, "en") === "51.46%" && formaterZoom(1, "en") === "100%");

// 12. M2 : maxSide 0 = grand côté du document (pas de rendu redondant)
check("12.1 0 -> 1920 sur un document 1920 : identique", changementSensible(0, 1920, 0.25, 1920) === false && changementSensible(1920, 0, 0.25, 1920) === false);
check("12.2 960 -> 0 sur 1920 : oui", changementSensible(960, 0, 0.25, 1920) === true);

// 13. M1 : Ctrl+molette ne zoome jamais la page (même hors canevas) ; Ctrl+touche de zoom aussi
check("13.1 ctrlSurPage", ctrlSurPage({ ctrlKey: true }) === true && ctrlSurPage({ ctrlKey: false }) === false && ctrlSurPage({}) === false);

console.log(`vue : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
