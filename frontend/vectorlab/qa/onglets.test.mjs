// onglets.test.mjs — mod-onglets : la pile de droite d'Affinity — trois
// groupes d'onglets par persona, chaque onglet ouvre des sections
// <details>, onglet actif mémorisé (dz_vl_onglets). Feuille.
import { ONGLETS, GROUPES, onglets_de, onglet_de_section, actif_lire, actif_poser, actif_de, sections_ouvertes, actif_serialiser } from "../js/mod-onglets.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  const v = onglets_de("vecteur"), p = onglets_de("pixel");
  ok("Vecteur : 3 groupes de 5 / 9 / 5 onglets ; Pixel : 2 / 4 / 4 (Histogramme en tête, R6)", v.length === 3 && v.map((g) => g.length).join() === "5,9,5" && p.map((g) => g.length).join() === "2,4,4" && p[0][0] === "histogramme", v.map((g) => g.length).join() + " | " + p.map((g) => g.length).join());
  ok("persona inconnu : []", onglets_de("zz").length === 0);
  const tousIds = Object.keys(ONGLETS);
  ok("chaque onglet a un libellé et ≥ 1 section ; chaque onglet des groupes existe", tousIds.every((id) => ONGLETS[id].libelle && ONGLETS[id].sections.length >= 1) && Object.values(GROUPES).flat(2).every((id) => ONGLETS[id]));
  ok("une section n'appartient qu'à un onglet", (() => { const s = tousIds.flatMap((id) => ONGLETS[id].sections); return new Set(s).size === s.length; })());
  ok("onglet_de_section : styleDetails → couleur, exportPlusDetails → exporter, inconnu → null", onglet_de_section("styleDetails") === "couleur" && onglet_de_section("exportPlusDetails") === "exporter" && onglet_de_section("zz") === null);
  const e0 = actif_lire(null);
  ok("défauts : couleur / calques / transformer en Vecteur, couleur / calques / navigateur en Pixel ; JSON illisible → défauts", actif_de(e0, "vecteur").join() === "couleur,calques,transformer" && actif_de(e0, "pixel").join() === "couleur,calques,navigateur" && actif_de(actif_lire("{oops"), "vecteur")[0] === "couleur");
  const e1 = actif_lire('{"vecteur":["trait","stock","zz"],"pixel":"non"}');
  ok("lire : un onglet hors de son groupe ou inconnu retombe sur le défaut, une valeur non tableau aussi", actif_de(e1, "vecteur").join() === "trait,stock,transformer" && actif_de(e1, "pixel").join() === "couleur,calques,navigateur", actif_de(e1, "vecteur").join());
  const e2 = actif_poser(e0, "vecteur", 1, "planches");
  ok("poser : nouvel objet, l'ancien intact ; hors groupe → inchangé", actif_de(e2, "vecteur")[1] === "planches" && actif_de(e0, "vecteur")[1] === "calques" && actif_poser(e2, "vecteur", 1, "couleur") === e2 && actif_poser(e2, "zz", 0, "couleur") === e2);
  ok("sections_ouvertes : celles des onglets actifs, rien d'autre", (() => { const s = sections_ouvertes(e2, "vecteur"); return s.includes("styleDetails") && s.includes("planchesDetails") && s.includes("transformerDetails") && !s.includes("calquesDetails") && s.length === 3; })(), sections_ouvertes(e2, "vecteur").join());
  ok("sections_ouvertes : Pixel par défaut = styleDetails, calquesDetails, navigateurDetails ; persona inconnu → []", sections_ouvertes(e0, "pixel").join() === "styleDetails,calquesDetails,navigateurDetails" && sections_ouvertes(e0, "zz").length === 0);
  ok("sérialiser → relisible", actif_de(actif_lire(actif_serialiser(e2)), "vecteur")[1] === "planches");
  ok("exporter réunit Export et Export + ; tracé réunit Nœuds et Forme", ONGLETS.exporter.sections.join() === "exportDetails,exportPlusDetails" && ONGLETS.trace.sections.join() === "noeudsDetails,formeDetails");
}
if (echecs.length) { console.error("ECHECS onglets :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA onglets : PASS (12 controles)");
