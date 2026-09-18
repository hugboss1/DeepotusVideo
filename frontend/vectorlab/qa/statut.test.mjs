// statut.test.mjs — mod-statut : la barre d'état d'Affinity — phrase d'aide
// aux verbes en gras selon l'outil et la sélection, onglet de document
// « nom @ 73%* », pagination « 1 sur N ». Feuille.
import { phrase_statut, statut_html, onglet_document, pagination, verbes_gras } from "../js/mod-statut.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  const p0 = phrase_statut("select", 0, {});
  ok("sélection sans objet : cadre / cliquer / clic droit", p0.startsWith("**Glisser** pour utiliser un cadre de sélection") && p0.includes("**Cliquer** sur un objet"), p0);
  const p1 = phrase_statut("select", 2, {});
  ok("sélection avec 2 objets : « 2 objets sélectionnés » puis déplacer", p1.startsWith("2 objets sélectionnés.") && p1.includes("**Glisser** pour déplacer"), p1);
  ok("un seul objet : singulier", phrase_statut("select", 1, {}).startsWith("1 objet sélectionné."));
  ok("autre outil : la phrase de l'outil (les HINTS existants), verbes gras posés sur les infinitifs connus", phrase_statut("rect", 0, { rect: "glisser pour tracer · Maj contraint au carré" }) === "**Glisser** pour tracer · **Maj** contraint au carré", phrase_statut("rect", 0, { rect: "glisser pour tracer · Maj contraint au carré" }));
  ok("état vide : outil inconnu sans hint → chaîne vide", phrase_statut("zz", 0, {}) === "" && phrase_statut("zz", 0, null) === "");
  ok("html : échappe puis pose les <b>", statut_html("**Glisser** <x> & y") === "<b>Glisser</b> &lt;x&gt; &amp; y");
  ok("onglet : nom @ zoom, astérisque si sale", onglet_document({ name: "carte" }, 0.734, true) === "carte @ 73%*" && onglet_document({ name: "carte" }, 1, false) === "carte @ 100%");
  ok("onglet sans meta : « … »", onglet_document(null, 1, false) === "…");
  ok("verbes_gras (R6, bulles riches) : les verbes connus en tête de segment, y compris après une virgule ; texte vide → vide", verbes_gras("glisser les poignées, Maj contraint") === "**Glisser** les poignées, **Maj** contraint" && verbes_gras("") === "" && verbes_gras(null) === "");
  ok("pagination : planches ou page unique", pagination([], null) === "1 sur 1" && pagination([{ id: "a" }, { id: "b" }], "b") === "2 sur 2" && pagination([{ id: "a" }], "zz") === "1 sur 1" && pagination(undefined, null) === "1 sur 1");
}
if (echecs.length) { console.error("ECHECS statut :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA statut : PASS (10 controles)");
