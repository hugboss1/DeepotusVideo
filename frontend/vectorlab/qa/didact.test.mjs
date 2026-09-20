// didact.test.mjs — mod-didact : la fiche didactique d'une option (index →
// fiche par id DOM), le compte de mots de la phrase « pour un enfant de cinq
// ans », la validation d'une fiche et le HTML de l'encart.
import { fiche_pour, compter_mots, valider_fiche, didact_html, DIDACT_DELAI_MS, DIDACT_LARGEUR } from "../js/mod-didact.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };
{
  const index = [
    { id: "pxContour", titre: "Contour sombre", phrase: "Un trait sombre entoure ton dessin pour qu'il se détache du fond.", fichier: "pixelui.pxContour.webp", version: 1 },
    { id: "impDepouille", titre: "Dépouille", phrase: "Les côtés penchent un peu.", fichier: "impression.impDepouille.webp", version: 2 },
  ];
  ok("constantes : 900 ms, 320 px", DIDACT_DELAI_MS === 900 && DIDACT_LARGEUR === 320);
  ok("fiche_pour : par id DOM, sinon null", fiche_pour(index, "pxContour").titre === "Contour sombre" && fiche_pour(index, "zz") === null);
  ok("état vide : index null / [] / id vide → null", fiche_pour(null, "pxContour") === null && fiche_pour([], "pxContour") === null && fiche_pour(index, "") === null);
  ok("compter_mots : apostrophes et traits d'union collés, ponctuation ignorée", compter_mots("Un trait sombre entoure ton dessin pour qu'il se détache du fond.") === 12 && compter_mots("pixel-art, c'est joli !") === 3 && compter_mots("") === 0 && compter_mots(null) === 0);
  ok("valider_fiche : une fiche complète passe", valider_fiche(index[0]).length === 0, valider_fiche(index[0]).join(","));
  const longue = { id: "x", titre: "T", phrase: Array.from({ length: 26 }, (_, i) => "mot" + i).join(" "), fichier: "m.x.webp", version: 1 };
  ok("valider_fiche : phrase > 25 mots refusée", valider_fiche(longue).some((e) => /25/.test(e)));
  ok("valider_fiche : id, titre, fichier .webp/.png, version entier", valider_fiche({ id: "", titre: "", phrase: "a", fichier: "m.x.gif", version: "1" }).length === 4, valider_fiche({ id: "", titre: "", phrase: "a", fichier: "m.x.gif", version: "1" }).join(","));
  const h = didact_html({ id: "pxContour", titre: "Contour <b>", phrase: "a & b", fichier: "pixelui.pxContour.webp", version: 1 });
  ok("didact_html : image aide/<fichier> versionnée, titre et phrase échappés", h.includes('src="aide/pixelui.pxContour.webp?v=1"') && h.includes("Contour &lt;b&gt;") && h.includes("a &amp; b") && h.includes('class="vl-didact-titre"'));
}
if (echecs.length) { console.error("ECHECS didact :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA didact : PASS (8 controles)");
