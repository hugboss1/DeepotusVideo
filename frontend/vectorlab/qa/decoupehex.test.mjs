// qa/decoupehex.test.mjs — plateau (lot 1) : Export › Découper en hexagones… du Vectorlab (échelle d'export, nom déposé,
// export opaque, appel du dialogue partagé, bouton et libellés FR/EN).
import { readFileSync } from "node:fs";
import { echelleDecoupe, decouperHex, APERCU_MAX } from "../js/mod-decoupehex.js";
import { nomExportPNG, transparentExport } from "../js/mod-export.js";
import { grille } from "../../shared/dz-decoupe-hex-logique.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/vectorlab.json", import.meta.url), "utf8"));
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const source = readFileSync(new URL("../js/mod-export.js", import.meta.url), "utf8");

// 1. l'échelle : k = min(8192 / max(w, h), cible / w), cible = ceil(largeurMm / 25.4 × 300)
{
  const g = grille("hex_p90", 6, 4);
  const cible = Math.ceil(g.largeurMm / 25.4 * 300);
  const k = echelleDecoupe(1000, 700, g.largeurMm);
  check("1.1 document 1000 × 700, grille 6 × 4 hex_p90 : cible/w (300 ppp)", Math.abs(k - cible / 1000) < 1e-12 && k > 1, [k, cible]);
  check("1.2 largeur obtenue ≥ 300 ppp", Math.round(1000 * k) / (g.largeurMm / 25.4) >= 299.5, Math.round(1000 * k) / (g.largeurMm / 25.4));
  const gros = echelleDecoupe(4000, 1000, 600);                      // cible = 7087 px → 1.77 ; borne 8192/4000 = 2.048
  check("1.3 sous la borne : la cible gagne", Math.abs(gros - Math.ceil(600 / 25.4 * 300) / 4000) < 1e-12, gros);
  const borne = echelleDecoupe(1000, 700, 5000);                     // cible 59056 px → borne 8192/1000
  check("1.4 la borne 8192 px est respectée", Math.abs(borne - 8.192) < 1e-12 && Math.max(1000, 700) * borne <= 8192 + 1e-9, borne);
  const haut = echelleDecoupe(500, 2000, 5000);                      // plus grand côté = hauteur
  check("1.5 la borne porte sur le plus grand côté", Math.abs(haut - 4.096) < 1e-12 && 2000 * haut <= 8192 + 1e-9, haut);
  check("1.6 jamais nul ni non fini", [echelleDecoupe(10, 10, 0), echelleDecoupe(10, 10, NaN)].every((v) => Number.isFinite(v) && v > 0));
}

// 2. le nom déposé : vector_<docId>_plateau_<k>x.png, sûr pour un fichier, k à deux décimales
{
  check("2.1 nom entier inchangé (export existant)", nomExportPNG("abc", "", 2, false) === "vector_abc_2x.png");
  check("2.2 transparent : suffixe _t inchangé", nomExportPNG("abc", "", 2, true) === "vector_abc_2x_t.png");
  check("2.3 planche : suffixe de planche inchangé", nomExportPNG("abc", "_p1", 1, false) === "vector_abc_p1_1x.png");
  check("2.4 plateau : k à deux décimales", nomExportPNG("abc", "_plateau", 3.3711, false) === "vector_abc_plateau_3.37x.png", nomExportPNG("abc", "_plateau", 3.3711, false));
  check("2.5 plateau : k entier sans décimales", nomExportPNG("abc", "_plateau", 4, false) === "vector_abc_plateau_4x.png");
  check("2.6 nom sans caractère interdit", /^[A-Za-z0-9._-]+$/.test(nomExportPNG("abc", "_plateau", 3.3711, false)));
}

// 2bis. l'opacité : le plateau ne lit pas la case, les autres boutons la suivent
{
  check("2b.1 plateau : opaque même case cochée", transparentExport({ opaque: true }, true) === false);
  check("2b.2 plateau : opaque case décochée", transparentExport({ opaque: true }, false) === false);
  check("2b.3 autres boutons : suivent la case", transparentExport({}, true) === true && transparentExport({}, false) === false && transparentExport({ suffixe: "_p1" }, true) === true);
}

// 3. l'appel du dialogue
function fabrique({ taille = { w: 1000, h: 700 }, nom = "Mon plateau" } = {}) {
  const j = { ouvert: null, exports: [], apercus: [] };
  const VL = {
    etat: { doc: { taille }, docId: "d1", meta: { name: nom } },
    rasteriser: async (k, transparent) => { j.apercus.push([k, transparent]); return { blob: true }; },
    exporterPNG: async (k, opts) => { j.exports.push([k, opts]); return "vector_d1_plateau_" + k + "x.png"; },
  };
  const outils = {
    versCanvas: async (blob, k) => ({ canvas: true, k }),
    ouvrir: async (o) => { j.ouvert = o; return { deck: { id: "x" }, tuiles: 24 }; },
  };
  return { VL, j, outils };
}
{
  const { VL, j, outils } = fabrique();
  const r = await decouperHex(VL, (c) => c, outils);
  check("3.1 dimensions et nom du document", j.ouvert.largeur === 1000 && j.ouvert.hauteur === 700 && j.ouvert.nomImage === "Mon plateau", j.ouvert);
  check("3.2 aperçu : rastérisation opaque, bornée", j.apercus.length === 1 && j.apercus[0][1] === false && j.apercus[0][0] > 0 && j.apercus[0][0] <= 1 && j.ouvert.apercu.canvas === true, j.apercus);
  check("3.3 le résultat du dialogue est rendu", r && r.tuiles === 24);
  check("3.4 rien n'est exporté avant la création", j.exports.length === 0);
  const g = grille("hex_p90", 6, 4);
  const nom = await j.ouvert.fournirImage({ largeurMm: g.largeurMm, hauteurMm: g.hauteurMm });
  const attendu = echelleDecoupe(1000, 700, g.largeurMm);
  check("3.5 fournirImage : export au k attendu, suffixe _plateau, OPAQUE", j.exports.length === 1 && j.exports[0][0] === attendu && j.exports[0][1].suffixe === "_plateau" && j.exports[0][1].opaque === true, j.exports);
  check("3.6 le nom rendu est celui du serveur", nom === "vector_d1_plateau_" + attendu + "x.png", nom);
}
{
  const { VL, j, outils } = fabrique({ taille: { w: 8000, h: 6000 } });
  await decouperHex(VL, (c) => c, outils);
  check("3.7 grand document : l'aperçu est borné à APERCU_MAX", Math.abs(j.apercus[0][0] * 8000 - APERCU_MAX) < 1e-9, j.apercus);
}
{
  const { VL, outils } = fabrique();
  let ouverts = 0;
  outils.ouvrir = async () => { ouverts++; await new Promise((r) => setTimeout(r, 20)); return null; };
  const [, b] = await Promise.all([decouperHex(VL, (c) => c, outils), decouperHex(VL, (c) => c, outils)]);
  check("3.10 double clic : un seul dialogue", ouverts === 1 && b === null, ouverts);
  await decouperHex(VL, (c) => c, outils);
  check("3.11 le verrou est relâché après coup", ouverts === 2, ouverts);
}
{
  const { VL, j, outils } = fabrique();
  VL.etat.doc = null;
  const r = await decouperHex(VL, (c) => c, outils);
  check("3.8 sans document : rien", r === null && j.ouvert === null);
}
{
  const { VL, j, outils } = fabrique();
  VL.rasteriser = async () => { throw new Error("svg illisible"); };
  let err = null; try { await decouperHex(VL, (c) => c, outils); } catch (e) { err = e; }
  check("3.9 rastérisation impossible : l'erreur remonte (toast du garde), dialogue non ouvert", err && err.message === "svg illisible" && j.ouvert === null);
}

// 4. le bouton et le câblage
{
  check("4.1 bouton #expPlateau dans le menu Export, après #expPng4", /id="expPng4"[\s\S]*?id="expPlateau"/.test(html) && html.indexOf("expPlateau") < html.indexOf("expTransparent"));
  check("4.2 libellé et infobulle FR/EN", ["vectorlab.export.plateau", "vectorlab.export.plateau_titre"].every((c) => dico[c] && dico[c].fr.trim() && dico[c].en.trim() && dico[c].fr !== dico[c].en), Object.keys(dico).filter((c) => c.includes("plateau")));
  check("4.3 libellé FR attendu", dico["vectorlab.export.plateau"].fr === "Découper en hexagones…" && dico["vectorlab.export.plateau"].en === "Cut into hexagons…");
  check("4.4 câblage : clic -> garde(decouperHex), exporterPNG lit l'option opaque", /\$\("#expPlateau"\)\.addEventListener\("click", garde\(/.test(source) && /transparentExport\(opts, \$\("#expTransparent"\)\.checked\)/.test(source));
  check("4.5 les boutons existants ne passent pas l'option", /exporterPNG\(1\)/.test(source) && /exporterPNG\(2\)/.test(source) && /exporterPNG\(4\)/.test(source));
}

console.log(`${ok}/${ok + ko} vérifications`);
if (ko) { console.log("ECHEC"); process.exit(1); }
console.log("OK");
