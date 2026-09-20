// familles.test.mjs — mod-familles : les familles d'outils d'Affinity —
// par persona, membre courant, flyout vertical « Outil X · R », bascule
// par raccourci. Feuille.
import { FAMILLES, famille_de, famille_par_id, familles_de, membre_courant, choisir_membre, flyout_famille, touche_de } from "../js/mod-familles.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  ok("Vecteur : 16 familles dans l'ordre, Pixel : 9 (R7 : Dégradé, Plan de travail, Vue, Retouche, Image partagée)", familles_de("vecteur").length === 16 && familles_de("pixel").length === 9 && familles_de("vecteur")[0].id === "deplacer" && familles_de("pixel")[2].id === "pxselection" && familles_de("pixel")[1].id === "image", familles_de("vecteur").map((f) => f.id).join(",") + " | " + familles_de("pixel").map((f) => f.id).join(","));
  ok("Déplacer et Tranche sont dans les deux personas", familles_de("pixel").some((f) => f.id === "deplacer") && familles_de("pixel").some((f) => f.id === "tranche"));
  ok("famille_de : crayon → plume (3 membres), px-lasso → pxselection, inconnu → null", famille_de("crayon").id === "plume" && famille_de("plume").membres.length === 3 && famille_de("px-lasso").id === "pxselection" && famille_de("zz") === null);
  ok("membres uniques dans toutes les familles", (() => { const t = FAMILLES.flatMap((f) => f.membres.map((m) => m.outil)); return new Set(t).size === t.length; })());
  const e0 = {};
  ok("membre courant : le premier par défaut ; famille inconnue → null", membre_courant(e0, "plume") === "plume" && membre_courant(e0, "formes") === "rect" && membre_courant(e0, "zz") === null && membre_courant(undefined, "plume") === "plume");
  const e1 = choisir_membre(e0, "crayon");
  ok("choisir : la famille du membre le retient, l'état d'origine intact", membre_courant(e1, "plume") === "crayon" && membre_courant(e0, "plume") === "plume");
  ok("choisir un outil inconnu : état inchangé ; une valeur étrangère retombe sur le premier", choisir_membre(e1, "zz") === e1 && membre_courant({ plume: "zz" }, "plume") === "plume");
  const fl = flyout_famille(famille_par_id("formes"), "ellipse");
  ok("flyout : « Outil X », raccourci en détail, le courant marqué, id = outil", fl.length === 4 && fl[0].libelle === "Outil Rectangle" && fl[0].detail === "R" && fl[1].actif === true && fl[1].id === "ellipse" && fl.filter((x) => x.actif).length === 1, JSON.stringify(fl));
  ok("état vide : famille null → [], id inconnu → null", famille_par_id("zz") === null && flyout_famille(null, "x").length === 0 && flyout_famille(undefined, "x").length === 0);
  ok("touche_de : R pour rect, vide pour ia", touche_de("rect") === "R" && touche_de("ia") === "" && touche_de("zz") === "");
}
if (echecs.length) { console.error("ECHECS familles :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA familles : PASS (10 controles)");
