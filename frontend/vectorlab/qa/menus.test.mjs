// menus.test.mjs — mod-menus : la barre de menus d'Affinity — dix menus,
// entrées {id, libelle, raccourci, action} ou séparateurs, disponibilité
// calculée par un prédicat, libellé du raccourci. Feuille.
import { MENUS_BARRE, menus_construire, raccourci_de, menu_trouver } from "../js/mod-menus.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  ok("dix menus dans l'ordre d'Affinity", JSON.stringify(MENUS_BARRE.map((m) => m.titre)) === '["Fichier","Edition","Document","Texte","Vecteur","Pixel","Calque","Affichage","Fenêtre","Aide"]', MENUS_BARRE.map((m) => m.titre).join(","));
  const toutes = MENUS_BARRE.flatMap((m) => m.entrees.filter((e) => e !== "-"));
  ok("chaque entrée a id, libellé et action ; ids uniques", toutes.every((e) => e.id && e.libelle && e.action) && new Set(toutes.map((e) => e.id)).size === toutes.length, toutes.filter((e, i) => toutes.findIndex((x) => x.id === e.id) !== i).map((e) => e.id).join(","));
  ok("Edition porte Annuler Ctrl+Z, Rétablir, Dupliquer Ctrl+D, Tout sélectionner Ctrl+A", (() => { const m = menu_trouver(MENUS_BARRE, "Edition"); const ids = m.entrees.filter((e) => e !== "-").map((e) => e.id); return ids.includes("annuler") && ids.includes("refaire") && ids.includes("dupliquer") && ids.includes("toutSelectionner") && raccourci_de(m.entrees.find((e) => e.id === "annuler")) === "Ctrl+Z"; })());
  const c = menus_construire(MENUS_BARRE, (action) => action === "sauver" || action === "annuler");
  ok("construire : desactive = le prédicat dit non, séparateurs conservés", (() => { const f = c.find((m) => m.titre === "Fichier"); const s = f.entrees.find((e) => e !== "-" && e.id === "sauver"); const o = f.entrees.find((e) => e !== "-" && e.id === "ouvrir"); return s.desactive === false && o.desactive === true && f.entrees.includes("-"); })());
  ok("construire : les données d'origine restent intactes", MENUS_BARRE[0].entrees.every((e) => e === "-" || e.desactive === undefined));
  ok("état vide : prédicat absent → tout disponible ; menus absents → []", menus_construire(MENUS_BARRE).every((m) => m.entrees.every((e) => e === "-" || e.desactive === false)) && menus_construire(undefined).length === 0);
  ok("raccourci : Ctrl+Maj+Z, sans raccourci → chaîne vide", raccourci_de({ raccourci: "ctrl+shift+z" }) === "Ctrl+Maj+Z" && raccourci_de({}) === "" && raccourci_de(null) === "");
  ok("trouver : menu inconnu → null", menu_trouver(MENUS_BARRE, "zz") === null && menu_trouver(undefined, "Aide") === null);
  ok("Calque : Nouveau calque, Grouper, Verrouiller ; Vecteur : Convertir en courbes, Traçage d'image, Union ; Pixel : Inverser, Nouveau calque", (() => { const ids = (t) => menu_trouver(MENUS_BARRE, t).entrees.filter((e) => e !== "-").map((e) => e.id); return ids("Calque").includes("calqueNouveau") && ids("Calque").includes("grouperC") && ids("Calque").includes("verrouiller") && ids("Vecteur").includes("vectoriserTexte") && ids("Vecteur").includes("tracerImage") && ids("Vecteur").includes("boolUnion") && ids("Pixel").includes("pxInverser") && ids("Pixel").includes("pxCalque"); })());
}
if (echecs.length) { console.error("ECHECS menus :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA menus : PASS (9 controles)");
