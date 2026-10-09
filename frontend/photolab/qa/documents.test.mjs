// qa/documents.test.mjs — t158 (parité L8) : onglets, Fichier sûr, listes de choix, Image › Mode. Fonctions PURES.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ongletsDe, aConfirmer, peutRevenir, choixDocuments, choixTraces, traceParDefaut, corpsCopie, corpsCalque, motsCles,
  urlValide, infosModifiees, decorerDocuments, DOSSIERS_REVENIR, FORMATS_CALQUE, STATUTS_COPYRIGHT, MAX_TEXTE_INFO } from "../js/mod-documents.js";
import { cochesMode, decorerMode, doitConfirmerAplatir, paramsBichromie, paramsTable, DIRECTES, APLATISSENT, ENCRES_PAR_TYPE, TABLES,
  MODES, PROFONDEURS } from "../js/mod-mode.js";
import { avecChoix, choixInitiaux } from "../js/mod-dialogue-reglage.js";
import { construireMenus, REFUSES, PERMIS, IDS_DOCUMENTS, TRAITES_PAR_ECRAN, NECESSITE_DOC, actionEntree, aiguillage, cibleDialogue,
  rechercherEntree } from "../js/mod-menus.js";
import { CHOIX_ECRAN, sansEcran } from "../js/mod-champs.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const py = (f) => readFileSync(join(racine, "../../backend/app", f), "utf8");
const moteurPy = py("services/photolab_moteur.py"), registrePy = py("services/photolab_registre.py"), routesPy = py("api/photolab_routes.py");
const erreurDe = (f) => { try { f(); return null; } catch (e) { return e.cle || e.message; } };

// 1. onglets
const S = { active: 1, documents: [{ index: 0, name: "e99baeb8-herbe.png", dirty: true }, { index: 1, name: "photolab_20261009-101010_ciel-png.pcraft", dirty: false },
  { index: 2, name: "Sans titre", dirty: false }] };
const o = ongletsDe(S, true);
check("1.1 un onglet par document, ordre du moteur", o.map((x) => x.index).join() === "0,1,2", o);
check("1.2 noms nettoyés (empreinte, horodatage, extension)", o[0].nom === "herbe" && o[1].nom === "ciel", o);
check("1.3 actif = document actif de la session", o.filter((x) => x.actif).map((x) => x.index).join() === "1");
check("1.4 « modifié » : l'actif par l'écran, les autres par le moteur", o[1].modifie === true && o[0].modifie === true && o[2].modifie === false
  && ongletsDe(S, false)[1].modifie === false);
check("1.5 session vide ou absente -> aucun onglet", ongletsDe(null, true).length === 0 && ongletsDe({ documents: [] }, false).length === 0);
check("1.6 aConfirmer : tous les modifiés, ou tous sauf celui qu'on garde", aConfirmer(o).join() === "herbe,ciel" && aConfirmer(o, 1).join() === "herbe"
  && aConfirmer(ongletsDe(S, false), 0).length === 0);

// 2. Revenir
check("2.1 dossiers relus = DOSSIERS_REVENIR du pont", JSON.stringify(DOSSIERS_REVENIR) === JSON.stringify((moteurPy.match(/DOSSIERS_REVENIR = \(([^)]*)\)/) || [, ""])[1].match(/"[^"]+"/g).map((x) => x.slice(1, -1))));
check("2.2 peutRevenir : fichier du moteur sous entrees/ exports/ biblio/ natif/",
  ["entrees/a-b.png", "exports/x.pcraft", "biblio/photolab_1_a-png.pcraft", "natif/d-1.pcraft"].every(peutRevenir));
check("2.3 peutRevenir : document neuf, rendu, chemin hors liste ou remontée -> non",
  [null, undefined, "", "rendus/a.png", "C:/x.png", "/x.png", "exports/../x.png", 3].every((c) => !peutRevenir(c)));

// 3. listes de choix
const cd = choixDocuments(S, false);
check("3.1 choixDocuments : les AUTRES documents, nommés", cd.map((x) => x.valeur).join() === "0,2" && cd[0].libelle === "herbe", cd);
const cda = choixDocuments(S, true, (k, v) => k + ":" + v.nom);
check("3.2 avec l'actif : en premier, marqué", cda.length === 3 && cda[0].valeur === 1 && cda[0].libelle === "photolab.choix.ce_document:ciel", cda);
const dbl = choixDocuments({ active: 2, documents: [{ index: 0, name: "e99baeb8-herbe.png" }, { index: 1, name: "e99baeb8-herbe.png" }, { index: 2, name: "terre.png" }] }, false);
check("3.2b même nom deux fois : départagés par le rang", dbl.map((x) => x.libelle).join() === "herbe (1),herbe (2)", dbl);
check("3.3 un seul document -> aucun autre", choixDocuments({ active: 0, documents: [{ index: 0, name: "a" }] }, false).length === 0);
const ct = choixTraces({ paths: [{ name: "Ligne" }, { name: "Courbe" }], workPath: { knots: 2 } });
check("3.4 choixTraces : aucun, travail, puis les tracés enregistrés", ct.map((x) => x.valeur).join() === ",work,Ligne,Courbe", ct);
check("3.5 défaut : le tracé de travail, sinon le premier, sinon aucun", traceParDefaut(ct) === "work"
  && traceParDefaut(choixTraces({ paths: [{ name: "L" }] })) === "L" && traceParDefaut(choixTraces({ paths: [] })) === "");
check("3.6 avecChoix : la valeur choisie part telle quelle, « » n'envoie rien", JSON.stringify(avecChoix({ radius: 2 }, { path: "", source: 0 })) === '{"radius":2,"source":0}'
  && JSON.stringify(avecChoix({ a: 1 }, { path: "Ligne" })) === '{"a":1,"path":"Ligne"}');
check("3.7 choixInitiaux : défaut s'il est dans la liste, sinon la première valeur",
  JSON.stringify(choixInitiaux([{ cle: "path", valeurs: ct, defaut: "work" }, { cle: "mapDocument", valeurs: cda, defaut: 99 }, { cle: "x", valeurs: [] }])) === '{"path":"work","mapDocument":1,"x":""}');
check("3.8 CHOIX_ECRAN = les trois commandes à choix ; sansEcran ne les grise plus", CHOIX_ECRAN.size === 3
  && [...CHOIX_ECRAN].every((id) => sansEcran(id, [{ cle: "source", type: "docIndex", optionnel: false }]) === false));

// 4. corps des routes
check("4.1 corpsCopie : télécharger un PSD", JSON.stringify(corpsCopie({ format: "psd", nom: " ma copie ", destination: "telecharger" })) === '{"format":"psd","nom":"ma copie","destination":"telecharger"}');
check("4.2 corpsCopie : JPG vers la Bibliothèque, qualité bornée", JSON.stringify(corpsCopie({ format: "jpg", quality: "250", destination: "bibliotheque" }))
  === '{"format":"jpg","nom":"","destination":"bibliotheque","quality":100}');
check("4.3 corpsCopie : PSD vers la Bibliothèque refusé, format inconnu refusé", erreurDe(() => corpsCopie({ format: "psd", destination: "bibliotheque" })) === "photolab.copie.erreur.biblio"
  && erreurDe(() => corpsCopie({ format: "exe" })) === "photolab.export.erreur.format");
check("4.4 corpsCalque : échelle entière stricte 1..1000", JSON.stringify(corpsCalque({ format: "png", echelle: "250", layer: 7 })) === '{"format":"png","echelle":250,"nom":"","destination":"telecharger","layer":7}'
  && ["0", "1001", "12,5", "12.5", "abc", "-3"].every((e) => erreurDe(() => corpsCalque({ format: "png", echelle: e })) === "photolab.calque_export.erreur.echelle"));
check("4.5 corpsCalque : qualité pour jpg et webp seulement ; tif refusé", corpsCalque({ format: "webp", quality: 40 }).quality === 40
  && corpsCalque({ format: "png", quality: 40 }).quality === undefined && erreurDe(() => corpsCalque({ format: "tif" })) === "photolab.export.erreur.format");
check("4.6 FORMATS_CALQUE = FORMATS_CALQUE du pont", JSON.stringify(FORMATS_CALQUE) === JSON.stringify((routesPy.match(/FORMATS_CALQUE = \(([^)]*)\)/) || [, ""])[1].match(/"[^"]+"/g).map((x) => x.slice(1, -1))));
check("4.7 calque : un id non entier n'est pas envoyé", corpsCalque({ format: "png", layer: "3" }).layer === undefined && corpsCalque({ format: "png", layer: -1 }).layer === undefined);

// 5. Informations sur le fichier
check("5.1 motsCles : ; et , séparent, vides et doublons retirés", JSON.stringify(motsCles(" a; b ,, a ; c ")) === '["a","b","c"]' && motsCles("").length === 0);
check("5.2 urlValide : http(s) ou vide", urlValide("") && urlValide("https://exemple.org/l?x=1") && urlValide("http://a.b")
  && !urlValide("file:///C:/x") && !urlValide("javascript:alert(1)") && !urlValide("https://a b") && !urlValide("https://a\\b"));
const AV = { title: "T", author: "", authorTitle: "", description: "", keywords: ["a"], copyright: "", copyrightStatus: "unknown", copyrightUrl: "" };
check("5.3 rien de changé -> aucune clé (aucune étape)", Object.keys(infosModifiees(AV, { ...AV, keywords: "a" })).length === 0);
check("5.4 seules les clés changées partent", JSON.stringify(infosModifiees(AV, { ...AV, keywords: "a; b", author: "Moi", copyrightStatus: "publicDomain" }))
  === '{"author":"Moi","keywords":["a","b"],"copyrightStatus":"publicDomain"}');
check("5.5 bornes du pont : texte > 2000, 65 mots-clés, URL file:// -> erreurs", erreurDe(() => infosModifiees(AV, { ...AV, keywords: "a", title: "x".repeat(MAX_TEXTE_INFO + 1) })) === "photolab.infos.erreur.long"
  && erreurDe(() => infosModifiees(AV, { ...AV, keywords: Array.from({ length: 65 }, (_, i) => "m" + i).join(";") })) === "photolab.infos.erreur.mots"
  && erreurDe(() => infosModifiees(AV, { ...AV, keywords: "a", copyrightUrl: "file:///x" })) === "photolab.infos.erreur.url");
check("5.6 statuts = STATUTS_COPYRIGHT du pont", JSON.stringify(STATUTS_COPYRIGHT) === JSON.stringify((registrePy.match(/STATUTS_COPYRIGHT = \(([^)]*)\)/) || [, ""])[1].match(/"[^"]+"/g).map((x) => x.slice(1, -1))));

// 6. menus : entrées de l'écran, états décorés
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const reg = [...PERMIS, "image.adjustments.matchColor", "filter.distort.displace", "filter.render.flame", "edit.undo"].map((id) => ({ id, label: id, params: "{}", enabled: true, champs: [] }));
const arbre = construireMenus(catalogue, reg, REFUSES, "fr", (k) => k);
check("6.1 les 9 entrées de mod-documents sont traitées par l'écran et actives", IDS_DOCUMENTS.length === 9
  && IDS_DOCUMENTS.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id) && rechercherEntree(arbre, id) && rechercherEntree(arbre, id).etat === "actif"), IDS_DOCUMENTS.filter((id) => !rechercherEntree(arbre, id)));
check("6.1b les 12 entrées de Mode (sous préfixe refusé, PERMIS) ne sont plus « bientôt »",
  [...Object.values(MODES), ...Object.values(PROFONDEURS), "image.mode.colorTable"].every((id) => rechercherEntree(arbre, id) && rechercherEntree(arbre, id).etat === "actif"));
check("6.2 restent « bientôt » : Ouvrir en tant que, contenu d'objet dynamique (bloqué moteur)",
  ["file.openAs"].every((id) => rechercherEntree(arbre, id).etat === "bientot") && !IDS_DOCUMENTS.some((id) => /smartObjects|openAs/.test(id)));
check("6.3 les 12 entrées de Mode : aiguillage « mode », toujours un dialogue (8 bits compris)",
  Object.values(MODES).concat(Object.values(PROFONDEURS), ["image.mode.colorTable"]).every((id) => aiguillage(id) === "mode")
  && actionEntree({ type: "commande", id: "image.mode.bits8", etat: "actif", champs: [] }) === "dialogue"
  && cibleDialogue({ id: "image.mode.rgb", champs: [] }, { ouvrirMode() {} }) === "mode");
const dec = decorerDocuments(arbre, { nbDocs: 1, chemin: null });
check("6.4 un seul document, sans fichier : Fermer les autres et Revenir inactifs", rechercherEntree(dec, "file.closeOthers").etat === "inactif"
  && rechercherEntree(dec, "file.revert").etat === "inactif" && rechercherEntree(dec, "file.closeAll").etat === "actif");
const dec2 = decorerDocuments(arbre, { nbDocs: 2, chemin: "biblio/x.pcraft" });
check("6.5 deux documents, fichier relisible : actives", rechercherEntree(dec2, "file.closeOthers").etat === "actif" && rechercherEntree(dec2, "file.revert").etat === "actif");

// 6.6 chaque famille d'aiguillage est DISTRIBUÉE par le menu (sinon le clic tombe sur « bientôt » : défaut du t158)
const srcMenus = readFileSync(join(racine, "js/mod-menus.js"), "utf8");
const familles = [...srcMenus.match(/const OUVREURS = \{([\s\S]*?)\};/)[1].matchAll(/(\w+): "/g)].map((m) => m[1]);
check("6.6 activer() distribue chaque famille d'OUVREURS", familles.length >= 7 && familles.every((f) => srcMenus.includes(`cible === "${f}"`)),
  familles.filter((f) => !srcMenus.includes(`cible === "${f}"`)));

// 7. Image › Mode
const D = (mode, depth, n = 1) => ({ mode, depth, layers: Array.from({ length: n }, (_, i) => ({ id: i })) });
check("7.1 coches : mode et profondeur", [...cochesMode(D("Rgb", 8))].sort().join() === "image.mode.bits8,image.mode.rgb"
  && [...cochesMode(D("Indexed", 16))].sort().join() === "image.mode.bits16,image.mode.indexedColor" && cochesMode(null).size === 0);
const dm = decorerMode(arbre, D("Grayscale", 32));
check("7.2 decorerMode : Niveaux de gris et 32 bits cochés, RVB décoché, Table sans coche",
  rechercherEntree(dm, "image.mode.grayscale").coche === true && rechercherEntree(dm, "image.mode.bits32").coche === true
  && rechercherEntree(dm, "image.mode.rgb").coche === false && rechercherEntree(dm, "image.mode.colorTable").coche === undefined);
check("7.3 sans document : aucune coche", decorerMode(arbre, null) === arbre);
check("7.4 aplatir : Bitmap, Indexées, Multicouche avec plusieurs calques seulement",
  doitConfirmerAplatir("image.mode.indexedColor", D("Rgb", 8, 3)) && doitConfirmerAplatir("image.mode.multichannel", D("Rgb", 8, 2))
  && !doitConfirmerAplatir("image.mode.indexedColor", D("Rgb", 8, 1)) && !doitConfirmerAplatir("image.mode.cmyk", D("Rgb", 8, 4))
  && APLATISSENT.size === 3);
check("7.5 directes : 4 espaces, Multicouche, 3 profondeurs (pas de dialogue)", DIRECTES.size === 8 && !DIRECTES.has("image.mode.bitmap") && !DIRECTES.has("image.mode.duotone"));
check("7.6 ENCRES_PAR_TYPE = celui du pont", JSON.stringify(ENCRES_PAR_TYPE) === JSON.stringify(Object.fromEntries([...(registrePy.match(/ENCRES_PAR_TYPE = \{([^}]*)\}/) || [, ""])[1].matchAll(/"(\w+)": (\d)/g)].map((m) => [m[1], Number(m[2])]))));
check("7.7 TABLES = celui du pont", JSON.stringify(TABLES) === JSON.stringify((registrePy.match(/TABLES = \(([^)]*)\)/) || [, ""])[1].match(/"[^"]+"/g).map((x) => x.slice(1, -1))));
const E = [{ name: " Noir ", color: "#000000" }, { name: "Rouge", color: "#CC2200" }, { name: "Or", color: "#d4a017" }, { name: "Bleu", color: "#1f4e79" }];
check("7.8 bichromie : exactement autant d'encres que le type, noms rognés, couleurs en minuscules",
  JSON.stringify(paramsBichromie("duotone", E)) === '{"type":"duotone","inks":[{"name":"Noir","color":"#000000"},{"name":"Rouge","color":"#cc2200"}]}'
  && paramsBichromie("quadtone", E).inks.length === 4 && paramsBichromie("monotone", E).inks.length === 1);
check("7.9 bichromie : type inconnu, encre manquante, nom vide, couleur illisible -> erreurs",
  erreurDe(() => paramsBichromie("zorg", E)) === "photolab.bichromie.erreur.type" && erreurDe(() => paramsBichromie("tritone", E.slice(0, 2))) === "photolab.bichromie.erreur.encres"
  && erreurDe(() => paramsBichromie("monotone", [{ name: "  ", color: "#000000" }])) === "photolab.bichromie.erreur.nom"
  && erreurDe(() => paramsBichromie("monotone", [{ name: "N", color: "noir" }])) === "photolab.bichromie.erreur.couleur");
const TA = { colors: ["#000000", "#ffffff", "#ff0000"], transparent: null };
check("7.10 table : rien de changé -> aucune commande", paramsTable(TA, { colors: TA.colors.slice(), transparent: null }) === null);
check("7.11 table : seules les cases changées (entries) et la transparence changée",
  JSON.stringify(paramsTable(TA, { colors: ["#000000", "#ABCDEF", "#ff0000"], transparent: 2 })) === '{"entries":{"1":"#abcdef"},"transparent":2}'
  && JSON.stringify(paramsTable({ ...TA, transparent: 2 }, { colors: TA.colors, transparent: null })) === '{"transparent":null}');
check("7.12 table : un préréglage remplace tout ; inconnu refusé", JSON.stringify(paramsTable(TA, TA, "web")) === '{"table":"web"}'
  && erreurDe(() => paramsTable(TA, TA, "C:/x.act")) === "photolab.table.erreur.prereglage");

console.log(`documents : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
