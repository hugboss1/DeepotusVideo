// qa/retouche-m3.test.mjs — t252 (Photolab M3, moteur photocraft 0.10) : Pièce, Déplacement basé sur le contenu,
// Tampon de motif, Supprimer, Œil rouge, symétrie de peinture, « Tous les calques » du Pot et du Correcteur localisé.
// Fonctions PURES de mod-peinture.js ; paramètres relevés sur le vrai moteur (backend/tests/test_photolab_peinture.py [4]).
import {
  OUTILS_PEINTURE, defautsPeinture, optionsPeinture, commandeTrait, commandeClic, commandePiece, dansBornes,
  axesSymetrie, commandeSymetrie, valeurSymetrie, SYMETRIQUES, MODES_SYMETRIE,
} from "../js/mod-peinture.js";
import { EMPLACEMENTS, outilDe } from "../js/mod-outils.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const o = (id, extra = {}) => ({ ...defautsPeinture(id), ...extra });
const P = [[1, 2], [3, 4]];

// 1. les cinq outils, dans les groupes de la référence (J : correcteurs, S : tampons), actifs
const NEUFS = { remove: "trait", patternStamp: "trait", redEye: "clic", patch: "piece", contentAwareMove: "piece" };
for (const [id, sorte] of Object.entries(NEUFS)) {
  check(`1.1 ${id} : outil de peinture de sorte « ${sorte} »`, OUTILS_PEINTURE[id] && OUTILS_PEINTURE[id].sorte === sorte, OUTILS_PEINTURE[id]);
  check(`1.2 ${id} : actif dans la barre (p2) avec une icône`, outilDe(id) && outilDe(id).p2 === true && /^dz-/.test(outilDe(id).icone), outilDe(id));
  check(`1.3 ${id} : des options, chacune avec un défaut dans ses bornes`, optionsPeinture(id).length > 0
    && optionsPeinture(id).every((x) => defautsPeinture(id)[x.cle] !== undefined
      && (x.type !== "nombre" || (defautsPeinture(id)[x.cle] >= x.min && defautsPeinture(id)[x.cle] <= x.max))), optionsPeinture(id));
}
const groupe = (premier) => EMPLACEMENTS.find((e) => e[0].id === premier).map((x) => x.id);
check("1.4 groupe J : Correcteur localisé, Correcteur, Supprimer, Pièce, Déplacement basé sur le contenu, Œil rouge (lettre J)",
  eq(groupe("spotHealing"), ["spotHealing", "healing", "remove", "patch", "contentAwareMove", "redEye"])
  && ["remove", "patch", "contentAwareMove", "redEye"].every((id) => outilDe(id).lettre === "J"), groupe("spotHealing"));
check("1.5 groupe S : Tampon de duplication puis Tampon de motif", eq(groupe("cloneStamp"), ["cloneStamp", "patternStamp"])
  && outilDe("patternStamp").lettre === "S", groupe("cloneStamp"));
check("1.6 plus aucun outil « bientôt » dans la barre", EMPLACEMENTS.flat().every((x) => x.p2), EMPLACEMENTS.flat().filter((x) => !x.p2).map((x) => x.id));

// 2. traits
let c = commandeTrait("remove", P, o("remove", { taille: 30, tousCalques: true, boucles: false, nouveauCalque: true }));
check("2.1 Supprimer -> paint.remove {points, size, sampleAllLayers, closeLoops, newLayer}", c && c.command === "paint.remove"
  && eq(c.params, { points: P, size: 30, sampleAllLayers: true, closeLoops: false, newLayer: true }), c);
c = commandeTrait("remove", P, o("remove"));
check("2.2 Supprimer par défaut : boucles fermées, ni tous les calques ni nouveau calque",
  c.params.closeLoops === true && c.params.sampleAllLayers === false && c.params.newLayer === false, c);
c = commandeTrait("patternStamp", P, o("patternStamp", { taille: 21, durete: 40, opacite: 80, flux: 90, fusion: "multiply", aligne: false, impressionniste: true }));
check("2.3 Tampon de motif -> paint.patternStamp, dureté/opacité/flux en 0..100", c && c.command === "paint.patternStamp"
  && eq(c.params, { points: P, size: 21, hardness: 40, opacity: 80, flow: 90, mode: "multiply", aligned: false, impressionist: true }), c);
check("2.4 aucun point -> null", commandeTrait("remove", [], o("remove")) === null);

// 3. clics : Œil rouge, Pot et Correcteur avec « Tous les calques »
const doc = { width: 100, height: 80 };
c = commandeClic("redEye", 10.7, 20.2, o("redEye", { pupille: 30, assombrir: 70 }), null, doc);
check("3.1 Œil rouge -> paint.redEye {x, y, pupilSize, darken} au pixel visé", c && c.command === "paint.redEye"
  && eq(c.params, { x: 10, y: 20, pupilSize: 30, darken: 70 }), c);
check("3.2 Œil rouge : défauts 50 / 50 (référence)", eq([defautsPeinture("redEye").pupille, defautsPeinture("redEye").assombrir], [50, 50]));
check("3.3 Œil rouge hors du document -> null", commandeClic("redEye", -1, 5, o("redEye"), null, doc) === null);
check("3.4 pupille bornée 1..100 (le moteur refuse 0)", optionsPeinture("redEye").find((x) => x.cle === "pupille").min === 1);
c = commandeClic("paintBucket", 3, 4, o("paintBucket", { tousCalques: true }), { fg: "#123456" }, doc);
check("3.5 Pot : « Tous les calques » -> sampleAllLayers", c.params.sampleAllLayers === true
  && optionsPeinture("paintBucket").some((x) => x.cle === "tousCalques") && defautsPeinture("paintBucket").tousCalques === false, c);
c = commandeTrait("spotHealing", P, o("spotHealing", { tousCalques: true }));
check("3.6 Correcteur localisé : « Tous les calques » -> sampleAllLayers", c.params.sampleAllLayers === true
  && optionsPeinture("spotHealing").some((x) => x.cle === "tousCalques") && defautsPeinture("spotHealing").tousCalques === false, c);
c = commandeTrait("spotHealing", P, o("spotHealing"));
check("3.7 Correcteur localisé par défaut : sampleAllLayers faux (comportement d'avant inchangé)", c.params.sampleAllLayers === false, c);

// 4. Pièce et Déplacement basé sur le contenu : un glisser de la sélection
c = commandePiece("patch", [12.4, -3.6], o("patch", { modePiece: "destination", contenu: true, structure: 6, couleurCa: 3, tousCalques: true }));
check("4.1 Pièce -> paint.patch {offset arrondi, mode, contentAware, structure, color, sampleAllLayers}", c && c.command === "paint.patch"
  && eq(c.params, { offset: [12, -4], mode: "destination", contentAware: true, structure: 6, color: 3, sampleAllLayers: true }), c);
c = commandePiece("contentAwareMove", [-5, 8], o("contentAwareMove", { modeDeplacement: "extend", structure: 2, couleurCa: 10 }));
check("4.2 Déplacement basé sur le contenu -> paint.contentAwareMove {offset, mode, structure, color, sampleAllLayers}",
  c && c.command === "paint.contentAwareMove" && eq(c.params, { offset: [-5, 8], mode: "extend", structure: 2, color: 10, sampleAllLayers: false }), c);
check("4.3 glisser de moins d'un pixel -> null (aucune commande)", commandePiece("patch", [0.3, -0.4], o("patch")) === null);
check("4.4 défauts de la référence : source / déplacer, structure 4, couleur 0",
  defautsPeinture("patch").modePiece === "source" && defautsPeinture("patch").structure === 4 && defautsPeinture("patch").couleurCa === 0
  && defautsPeinture("contentAwareMove").modeDeplacement === "move" && defautsPeinture("contentAwareMove").structure === 4);
check("4.5 structure 1..7, couleur 0..10 (bornes du moteur)", ["patch", "contentAwareMove"].every((id) => {
  const s = optionsPeinture(id).find((x) => x.cle === "structure"), k = optionsPeinture(id).find((x) => x.cle === "couleurCa");
  return s.min === 1 && s.max === 7 && k.min === 0 && k.max === 10;
}));
check("4.6 un autre outil n'est pas une pièce -> null", commandePiece("brush", [5, 5], o("brush")) === null);
check("4.7 dansBornes : dedans, bord, dehors, sans bornes", dansBornes([10, 10, 20, 5], 15, 12) && dansBornes([10, 10, 20, 5], 10, 10)
  && !dansBornes([10, 10, 20, 5], 31, 12) && !dansBornes(null, 1, 1));

// 5. symétrie de peinture (état du DOCUMENT dans le moteur, doc.inspect.symmetry)
check("5.1 Pinceau, Crayon et Gomme portent l'option Symétrie (amont : Brush, Pencil, Eraser)", SYMETRIQUES.every((id) => optionsPeinture(id).some((x) => x.cle === "symetrie" && x.doc))
  && eq([...SYMETRIQUES].sort(), ["brush", "eraser", "pencil"]));
check("5.2 valeurs : aucune, 4 axes du moteur, tracé de travail", eq(MODES_SYMETRIE, ["aucune", "vertical", "horizontal", "dual", "diagonal", "trace"]));
check("5.3 valeurSymetrie : aucune / mode / tracé", valeurSymetrie({}) === "aucune" && valeurSymetrie({ symmetry: { mode: "dual" } }) === "dual"
  && valeurSymetrie({ symmetry: { mode: "path", source: "work" } }) === "trace" && valeurSymetrie(null) === "aucune");
check("5.4 commandeSymetrie", eq(commandeSymetrie("vertical"), { command: "paint.setSymmetry", params: { mode: "vertical" } })
  && eq(commandeSymetrie("aucune"), { command: "paint.symmetryDisable", params: {} })
  && eq(commandeSymetrie("trace"), { command: "paint.symmetryFromPath", params: { name: "work" } }) && commandeSymetrie("zorg") === null);
// axes : horizontal 0°, diagonal 45°, vertical 90°, double = vertical + horizontal (amont paint/src/symmetry.rs), coupés au document
const proche = (a, b) => a.length === b.length && a.every((s, i) => s.every((v, j) => Math.abs(v - b[i][j]) < 1e-6));
check("5.5 vertical au centre : une ligne x = 50 du haut au bas", proche(axesSymetrie({ mode: "vertical", center: [50, 40], rotation: 0 }, 100, 80), [[50, 0, 50, 80]]),
  axesSymetrie({ mode: "vertical", center: [50, 40], rotation: 0 }, 100, 80));
check("5.6 horizontal : y = 40", proche(axesSymetrie({ mode: "horizontal", center: [50, 40], rotation: 0 }, 100, 80), [[0, 40, 100, 40]]));
check("5.7 double : vertical PUIS horizontal", proche(axesSymetrie({ mode: "dual", center: [50, 40], rotation: 0 }, 100, 80), [[50, 0, 50, 80], [100, 40, 0, 40]]),
  axesSymetrie({ mode: "dual", center: [50, 40], rotation: 0 }, 100, 80));
check("5.8 diagonale à 45° coupée au document", proche(axesSymetrie({ mode: "diagonal", center: [40, 40], rotation: 0 }, 100, 80), [[0, 0, 80, 80]]),
  axesSymetrie({ mode: "diagonal", center: [40, 40], rotation: 0 }, 100, 80));
check("5.9 tracé, aucune, ou axe hors du document : pas de ligne", eq(axesSymetrie({ mode: "path", source: "work" }, 100, 80), [])
  && eq(axesSymetrie(null, 100, 80), []) && eq(axesSymetrie({ mode: "horizontal", center: [50, -5], rotation: 0 }, 100, 80), []));

console.log("retouche-m3 :", ok, "ok,", ko, "echec(s)");
if (ko) process.exit(1);
