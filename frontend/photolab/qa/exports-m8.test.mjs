// qa/exports-m8.test.mjs — t257 (Photolab M8, moteur photocraft 0.10) : formats neufs et exports. Formats d'Exporter
// (TIFF à calques, ORA, PDF), avertissements du moteur, préréglages d'export, ouvrir depuis l'ordinateur (route du
// fichier), Calques / Jeux de données en fichiers, Image › Variables, menus. Fonctions PURES ; réponses relevées sur le
// vrai moteur (backend/tests/test_photolab_formats_m8.py).
import { construireMenus, actionEntree, REFUSES, INSERTIONS_M8, IDS_EXPORTS_M8, TRAITES_PAR_ECRAN, NECESSITE_DOC } from "../js/mod-menus.js";
import { FORMATS_EXPORT, formatExport, libelleFormat, corpsExport, clesAvertissements, prereglageDe, idDePrereglage, rangerPrereglage,
  retirerPrereglage, PREREGLAGES_MAX, routeFichier, FORMATS_OUVERTURE, FORMATS_BIBLIOTHEQUE, ACCEPTES, IMPORT_MAX } from "../js/mod-fichier.js";
import { corpsCopie } from "../js/mod-documents.js";
import { corpsCalquesFichiers, corpsJeuxFichiers, calquesVariables, defsDe, jeuxDe, lignesDeJeux, separateurDe, sorteDe, TYPES_VARIABLE,
  FORMATS_LOT } from "../js/mod-exports.js";
import { traduireEtat } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const erreurDe = (f) => { try { f(); return null; } catch (e) { return e.cle || e.message; } };
const routes = readFileSync(new URL("../../../backend/app/api/photolab_routes.py", import.meta.url), "utf8");
const moteur = readFileSync(new URL("../../../backend/app/services/photolab_moteur.py", import.meta.url), "utf8");
const registrePy = readFileSync(new URL("../../../backend/app/services/photolab_registre.py", import.meta.url), "utf8");
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const tuple = (src, nom) => ((src.match(new RegExp(nom + " = \\(([^)]*)\\)")) || [])[1] || "").match(/"([^"]+)"/g).map((s) => s.slice(1, -1));

// 1. formats d'Exporter
const pont = tuple(routes, "FORMATS");
check("1.1 ORA, PDF et TIFF à calques proposés", ["ora", "pdf", "tif-calques"].every((id) => formatExport(id)));
check("1.2 chaque format est accepté par /enregistrer (FORMATS du pont)", FORMATS_EXPORT.every((f) => pont.includes(f.format)), pont);
check("1.3 ids uniques", new Set(FORMATS_EXPORT.map((f) => f.id)).size === FORMATS_EXPORT.length);
check("1.4 TIFF à calques -> format tif + calques", eq(corpsExport("tif-calques", "a"), { format: "tif", nom: "a", calques: true }));
check("1.5 TIFF plat : pas de calques", eq(corpsExport("tif", "a"), { format: "tif", nom: "a" }));
check("1.6 WebP : qualité ENTIÈRE (#7023 : un flottant serait ignoré par le moteur)", Number.isInteger(corpsExport("webp", "a", "72.6").quality)
  && corpsExport("webp", "a", "72.6").quality === 73);
check("1.7 PDF, ORA : sans qualité", !("quality" in corpsExport("pdf", "a")) && !("quality" in corpsExport("ora", "a")));
check("1.8 format inconnu refusé", erreurDe(() => corpsExport("heic", "a")) === "photolab.export.erreur.format");
check("1.9 libellés : clé traduite pour TIFF à calques et PDF, sigle sinon",
  libelleFormat(formatExport("pdf"), (k) => "T:" + k) === "T:photolab.export.pdf_page" && libelleFormat(formatExport("ora"), (k) => k) === "ORA");
check("1.10 Enregistrer une copie : TIFF à calques par id", eq(corpsCopie({ format: "tif-calques", nom: "c", destination: "telecharger" }),
  { format: "tif", nom: "c", destination: "telecharger", calques: true }));
check("1.11 Enregistrer une copie : PDF vers la Bibliothèque refusé", erreurDe(() => corpsCopie({ format: "pdf", destination: "bibliotheque" })) === "photolab.copie.erreur.biblio");

// 2. avertissements du moteur (doc.save `warnings`, relevés sur 0.10)
check("2.1 PDF aplati", eq(clesAvertissements(["PDF was saved flattened: layers, masks-as-editable and transparency are not preserved (#3401)"]),
  ["photolab.export.avert.aplati"]));
check("2.2 WebP : calques fusionnés, pertes, ppp — sans doublon", eq(clesAvertissements(["4 layer(s) flattened; layers, masks and blend modes are not kept",
  "lossy compression", "resolution (DPI) not supported; it will be dropped", "lossy compression"]),
  ["photolab.export.avert.aplati", "photolab.export.avert.pertes", "photolab.export.avert.dpi"]));
check("2.3 inconnu -> message générique ; rien -> rien", eq(clesAvertissements(["zorg"]), ["photolab.export.avert.autre"]) && eq(clesAvertissements(undefined), []));

// 3. préréglages d'export
const p1 = prereglageDe(" Web léger ", "webp", 70);
check("3.1 préréglage : nom rogné, format, qualité", eq(p1, { nom: "Web léger", format: "webp", quality: 70 }));
check("3.2 TIFF à calques : calques gardé, id retrouvé", eq(prereglageDe("C", "tif-calques", 90), { nom: "C", format: "tif", calques: true })
  && idDePrereglage({ format: "tif", calques: true }) === "tif-calques" && idDePrereglage({ format: "tif" }) === "tif");
check("3.3 nom vide ou > 64 refusé", erreurDe(() => prereglageDe("  ", "png")) === "photolab.export.prereglage.erreur.nom"
  && erreurDe(() => prereglageDe("x".repeat(65), "png")) === "photolab.export.prereglage.erreur.nom");
check("3.4 même nom (sans casse) remplacé à sa place", eq(rangerPrereglage([{ nom: "A", format: "png" }, { nom: "B", format: "jpg" }], { nom: "a", format: "ora" }),
  [{ nom: "a", format: "ora" }, { nom: "B", format: "jpg" }]));
const plein = Array.from({ length: PREREGLAGES_MAX }, (_, i) => ({ nom: "n" + i, format: "png" }));
check("3.5 51e refusé, remplacement admis à 50", erreurDe(() => rangerPrereglage(plein, { nom: "neuf", format: "png" })) === "photolab.export.prereglage.erreur.max"
  && rangerPrereglage(plein, { nom: "N3", format: "jpg" }).length === PREREGLAGES_MAX);
check("3.6 supprimer", eq(retirerPrereglage([{ nom: "A" }, { nom: "B" }], "A"), [{ nom: "B" }]));
check("3.7 PREREGLAGES_MAX = celui du pont", new RegExp("PREREGLAGES_MAX = " + PREREGLAGES_MAX + "\\b").test(routes));
check("3.8 format d'un préréglage inconnu -> aucun id", idDePrereglage({ format: "exe" }) === null);

// 4. ouvrir depuis l'ordinateur
check("4.1 FORMATS_OUVERTURE = copie de PM.FORMATS_OUVERTURE", eq(FORMATS_OUVERTURE, tuple(moteur, "FORMATS_OUVERTURE")));
check("4.2 ORA, Krita, Affinity, Paint.NET, EXR, DPX, DDS, raws -> /importer",
  ["a.ora", "b.KRA", "c.afphoto", "d.pdn", "e.exr", "f.dpx", "g.dds", "h.CR2", "i.nef", "j.dng", "k.psd", "l.tif"].every((n) => routeFichier(n, 10) === "importer"));
check("4.3 images que la Bibliothèque reçoit -> Bibliothèque d'abord", ["a.png", "b.JPG", "c.webp", "d.gif", "e.avif"].every((n) => routeFichier(n, 10) === "bibliotheque"));
check("4.4 HEIC/HEIF : refus nommé (Q3)", eq(routeFichier("x.heic"), { refus: "photolab.import.heic" }) && eq(routeFichier("x.HEIF"), { refus: "photolab.import.heic" }));
check("4.5 inconnu, sans extension -> refus", eq(routeFichier("x.exe"), { refus: "photolab.import.format" }) && eq(routeFichier("sans"), { refus: "photolab.import.format" }));
check("4.6 plus de 1 Gio -> refus (IMPORT_MAX = celui du pont)", eq(routeFichier("a.ora", IMPORT_MAX + 1), { refus: "photolab.import.trop_lourd" })
  && /IMPORT_MAX = 1024 \* 1024 \* 1024/.test(routes));
check("4.7 le sélecteur accepte .ora et .png, pas .heic", ACCEPTES.includes(".ora") && ACCEPTES.includes(".png") && !ACCEPTES.includes(".heic"));
check("4.8 HEIC absent des deux listes", !FORMATS_OUVERTURE.includes("heic") && !FORMATS_BIBLIOTHEQUE.includes("heic"));

// 5. Calques / Jeux de données en fichiers
check("5.1 calques : png, visibles par défaut", eq(corpsCalquesFichiers({ format: "png", nom: " a " }), { format: "png", visibles: true, nom: "a" }));
check("5.2 calques : jpg avec qualité entière, tous les calques", eq(corpsCalquesFichiers({ format: "jpg", quality: "55.4", visibles: false, nom: "" }),
  { format: "jpg", visibles: false, nom: "", quality: 55 }));
check("5.3 calques : tif refusé (la Bibliothèque reçoit png/jpg)", erreurDe(() => corpsCalquesFichiers({ format: "tif" })) === "photolab.export.erreur.format"
  && eq(FORMATS_LOT, ["png", "jpg"]));
check("5.4 jeux : tous cochés -> aucune liste", !("jeux" in corpsJeuxFichiers({ format: "png" }, ["A", "B"], ["A", "B"])));
check("5.5 jeux : une partie -> la liste", eq(corpsJeuxFichiers({ format: "png" }, ["A", "B"], ["B"]).jeux, ["B"]));
check("5.6 jeux : aucun coché refusé", erreurDe(() => corpsJeuxFichiers({ format: "png" }, ["A"], [])) === "photolab.jeux.erreur.aucun");

// 6. Image › Variables
const layers = [{ id: 4, name: "Bonjour", kind: "Type" }, { id: 7, name: "Groupe", kind: "Group", children: [{ id: 3, name: "Rouge", kind: "Pixel" }] },
  { id: 2, name: "Background", kind: "Pixel" }];
const cal = calquesVariables(layers);
check("6.1 calques à plat, texte repéré", eq(cal.map((c) => [c.id, c.texte]), [[4, true], [7, false], [3, false], [2, false]]));
check("6.2 defs : visibilité et remplacement de texte", eq(defsDe([{ calque: "3", type: "visibility", nom: " rouge " }, { calque: "4", type: "textReplacement", nom: "titre" }], cal),
  [{ name: "rouge", layer: 3, type: "visibility" }, { name: "titre", layer: 4, type: "textReplacement" }]));
check("6.3 defs : nom vide, doublon, calque inconnu, texte sur pixels, pixels refusés",
  erreurDe(() => defsDe([{ calque: "3", type: "visibility", nom: "" }], cal)) === "photolab.variables.erreur.nom"
  && erreurDe(() => defsDe([{ calque: "3", type: "visibility", nom: "a" }, { calque: "2", type: "visibility", nom: "a" }], cal)) === "photolab.variables.erreur.double"
  && erreurDe(() => defsDe([{ calque: "99", type: "visibility", nom: "a" }], cal)) === "photolab.variables.erreur.calque"
  && erreurDe(() => defsDe([{ calque: "3", type: "textReplacement", nom: "a" }], cal)) === "photolab.variables.erreur.texte"
  && erreurDe(() => defsDe([{ calque: "3", type: "pixelReplacement", nom: "a" }], cal)) === "photolab.variables.erreur.type");
check("6.4 TYPES_VARIABLE = ceux du registre (pont)", eq(TYPES_VARIABLE, tuple(registrePy, "TYPES_VARIABLE")));
const defs = [{ name: "rouge", layer: 3, type: "visibility" }, { name: "titre", layer: 4, type: "textReplacement" }];
check("6.5 sortes : visibility / text", sorteDe("visibility") === "visibility" && sorteDe("textReplacement") === "text" && sorteDe("pixelReplacement") === null);
check("6.6 jeux : valeurs typées, variable sans valeur omise", eq(jeuxDe([{ nom: "Été", valeurs: { rouge: 1, titre: 42 } }, { nom: "Hiver", valeurs: { rouge: false } }], defs),
  [{ name: "Été", values: [{ variable: "rouge", kind: "visibility", value: true }, { variable: "titre", kind: "text", value: "42" }] },
    { name: "Hiver", values: [{ variable: "rouge", kind: "visibility", value: false }] }]));
check("6.7 jeux : nom vide, doublon, texte trop long refusés",
  erreurDe(() => jeuxDe([{ nom: " ", valeurs: {} }], defs)) === "photolab.jeux.erreur.nom"
  && erreurDe(() => jeuxDe([{ nom: "A", valeurs: {} }, { nom: "A", valeurs: {} }], defs)) === "photolab.jeux.erreur.double"
  && erreurDe(() => jeuxDe([{ nom: "A", valeurs: { titre: "x".repeat(4001) } }], defs)) === "photolab.jeux.erreur.texte");
check("6.8 jeux du moteur -> lignes", eq(lignesDeJeux([{ name: "A", values: [{ kind: "visibility", value: false, variable: "rouge" }] }]),
  [{ nom: "A", valeurs: { rouge: false } }]));
check("6.9 séparateur deviné", separateurDe("a;b;c\n1,2;3") === ";" && separateurDe("a,b\n") === "," && separateurDe("a\tb") === "\t" && separateurDe("") === ",");
check("6.10 « Apply Data Set \"Été\" » traduit avec le nom", traduireEtat('Apply Data Set "Été"', null, (k, v) => (k === "photolab.historique.appliquer_jeu" ? "Appliquer « " + v.nom + " »" : k))
  === "Appliquer « Été »");

// 7. menus : l'insertion et les entrées de l'écran
const cat = (chemin, id) => ({ chemin, id, libelle_fr: id, libelle_en: id, raccourci: null });
const catalogue = { entrees: [cat(["File"], "file.new"), cat(["File"], "file.open"), cat(["File"], "file.openAs"),
  cat(["File", "Export"], "file.export.exportAs"), cat(["File", "Export"], "file.export.layersToFiles"), cat(["File", "Export"], "file.export.dataSetsAsFiles"),
  cat(["File", "Export"], "file.export.exportPreferences"), cat(["File", "Import"], "file.import.variableDataSets"),
  cat(["Image", "Variables"], "image.variables.define"), cat(["Image", "Variables"], "image.variables.dataSets"), cat(["Image"], "image.applyDataSet")] };
const registre = catalogue.entrees.map((e) => ({ id: e.id, enabled: false, champs: [] }));
const menus = construireMenus(catalogue, registre, REFUSES, "fr", (k) => k);
const fichier = menus.find((m) => m.nom === "File").entrees;
const k = fichier.findIndex((e) => e.id === "file.open");
check("7.1 « Ouvrir depuis l'ordinateur… » juste après Ouvrir…, active sans document", fichier[k + 1] && fichier[k + 1].id === "pl.importer"
  && fichier[k + 1].etat === "actif" && actionEntree(fichier[k + 1]) === "ecran" && !NECESSITE_DOC.has("pl.importer"), fichier.map((e) => e.id));
check("7.2 INSERTIONS_M8 : une seule entrée, clé de texte au dictionnaire", INSERTIONS_M8.length === 1 && INSERTIONS_M8.every((x) => x.cle in dico));
const tout = (l) => l.flatMap((e) => (e.type === "sous-menu" ? tout(e.entrees) : [e]));
const plat = tout(menus.flatMap((m) => m.entrees));
check("7.3 Calques / Jeux en fichiers, Importer des jeux, Variables : actifs, servis par l'écran, document requis",
  IDS_EXPORTS_M8.every((id) => { const e = plat.find((x) => x.id === id); return e && e.etat === "actif" && actionEntree(e) === "ecran" && TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id); }),
  IDS_EXPORTS_M8.map((id) => [id, (plat.find((x) => x.id === id) || {}).etat]));
check("7.4 Préférences d'exportation et Ouvrir en tant que… restent « bientôt » (préférences du moteur ; chemin)",
  plat.find((x) => x.id === "file.export.exportPreferences").etat === "bientot" && plat.find((x) => x.id === "file.openAs").etat === "bientot");

// 8. textes : chaque clé de t257 a un français et un anglais non vides
const cles = Object.keys(dico).filter((c) => /^photolab\.(menu\.importer|export\.(tiff_calques|pdf_page|avert|prereglage)|import\.|lot\.|calques_fichiers|jeux|variables|historique\.appliquer_jeu)/.test(c));
check("8.1 52 clés de t257, fr et en non vides", cles.length === 52 && cles.every((c) => dico[c].fr && dico[c].en), cles.length);

console.log(`exports-m8 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
