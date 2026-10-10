// impression_ids.test.mjs — défaut du 10/10 : deux éléments portaient id="impHauteurs"
// (table Pixel-art et champ du mode Calques) ; $("#impHauteurs") rendait la DIV,
// .value valait undefined et l'aperçu du mode Calques — le mode par défaut — levait
// « hauteur en mm invalide ». Le banc lit le gabarit du dialogue dans la source.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { hauteurs_par_calque } from "../js/mod-impression.js";
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../js/mod-impression.js"), "utf8");
const debut = src.indexOf("dlg.innerHTML = `<div class=\"vl-dlg-boite imp-boite\">");
const fin = src.indexOf("</div></div>`;", debut);
ok("gabarit du dialogue trouvé", debut > 0 && fin > debut);
const gabarit = src.slice(debut, fin);
const ids = [...gabarit.matchAll(/\bid="([^"$]+)"/g)].map((m) => m[1]);
const doubles = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
ok("aucun id en double dans le dialogue Impression 3D", doubles.length === 0, doubles.join(", "));
// le premier élément portant l'id lu par le mode Calques — c'est ce que rend $()
const m = src.match(/hauteurs_par_calque\(\$\("#([A-Za-z0-9_-]+)"\)\.value/);
ok("le mode Calques lit un champ par $(\"#…\").value", !!m);
const balise = m && gabarit.match(new RegExp(`<(\\w+)[^>]*\\bid="${m[1]}"[^>]*>`));
ok("le premier élément de cet id est un <input> texte valant 3", !!balise && balise[1] === "input" && /value="3"/.test(balise[0]), balise && balise[0]);
// la valeur du champ par défaut, sur un document simple à deux calques, donne une hauteur
if (balise && balise[1] === "input" && /value="/.test(balise[0])) {
  const h = hauteurs_par_calque(balise[0].match(/value="([^"]*)"/)[1], [{ nom: "Calque 1" }, { nom: "Calque 2" }]);
  ok("valeur par défaut → hauteur globale 3 mm", h.globale === 3, JSON.stringify(h));
}
// la table Pixel-art reste lue et écrite par son propre id (3 usages : lecture, remplissage, erreur)
const px = gabarit.match(/<div class="imp-pixelart imp-hauteurs" id="([^"]+)"/);
ok("la table Pixel-art a son id", !!px);
if (px) ok("la table Pixel-art est visée 3 fois par son id", src.split(`$("#${px[1]}")`).length - 1 === 3, px[1]);
if (echecs.length) { console.error("ECHECS impression_ids :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA impression_ids : PASS (7 controles)");
