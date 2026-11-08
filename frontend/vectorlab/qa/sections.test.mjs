// sections.test.mjs — t459 : les sections internes du panneau de droite (Effets, Fusion & contours, Remplissage +…,
// les <details> SANS id que les panneaux reconstruisent à chaque rendu) gardent leur état ouvert / replié choisi par
// l'utilisateur, d'un rendu à l'autre et d'une session à l'autre (localStorage dz_vl_sections).
import { cle_section, sections_lire, sections_poser, sections_serialiser, appliquer_section } from "../js/mod-sections.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
// un <details> factice : son panneau (l'ancêtre à id) et le texte de son <summary>
const sec = (panneau, texte, open = false) => ({ open, panneau, texte });

/* ── la clé : panneau + titre sans ses compteurs ── */
ok("clé : panneau et titre", cle_section(sec("panneauApparence2", "Fusion & contours")) === "panneauApparence2:Fusion & contours");
ok("clé : le compteur « · 2 » ne compte pas", cle_section(sec("panneauApparence2", "Effets · 2")) === cle_section(sec("panneauApparence2", "Effets")));
ok("clé : une dimension « · 20×30 » ne compte pas", cle_section(sec("panneauPixel", "Sélection · 20×30")) === "panneauPixel:Sélection");
ok("clé : un nombre dans le titre ne la change pas", cle_section(sec("panneauPixel", "Animation (12 images)")) === cle_section(sec("panneauPixel", "Animation (3 images)")));
ok("clé : deux panneaux, deux clés", cle_section(sec("panneauPixel", "Effets")) !== cle_section(sec("panneauApparence2", "Effets")));
ok("clé : blancs normalisés", cle_section(sec("panneauApparence2", "  Remplissage   +  ")) === "panneauApparence2:Remplissage +");
ok("clé : sans panneau ni titre → null", cle_section(sec("", "Effets")) === null && cle_section(sec("panneauApparence2", "  ")) === null && cle_section(null) === null);

/* ── la mémoire ── */
ok("lire : vide ou illisible → {}", JSON.stringify(sections_lire(null)) === "{}" && JSON.stringify(sections_lire("{pas du json")) === "{}" && JSON.stringify(sections_lire("[1,2]")) === "{}" && JSON.stringify(sections_lire("[true,false]")) === "{}");
ok("lire : seuls les booléens sont gardés", JSON.stringify(sections_lire('{"a:b":true,"c:d":"oui","e:f":false}')) === '{"a:b":true,"e:f":false}');
const m1 = sections_poser({}, "panneauApparence2:Effets", true);
ok("poser : une copie, pas une mutation", JSON.stringify(m1) === '{"panneauApparence2:Effets":true}');
const m0 = {};
sections_poser(m0, "x:y", true);
ok("poser : l'objet d'origine est intact", JSON.stringify(m0) === "{}");
ok("poser : sans clé → inchangé", sections_poser(m1, null, false) === m1);
ok("sérialiser puis relire : identique", JSON.stringify(sections_lire(sections_serialiser(m1))) === JSON.stringify(m1));

/* ── appliquer à une section qui vient d'être (re)construite ── */
{
  const d = sec("panneauApparence2", "Fusion & contours", false);
  appliquer_section(d, { "panneauApparence2:Fusion & contours": true });
  ok("appliquer : une section fermée par le gabarit se rouvre si l'utilisateur l'avait ouverte", d.open === true);
  const e = sec("panneauApparence2", "Couleurs globales", true);
  appliquer_section(e, { "panneauApparence2:Couleurs globales": false });
  ok("appliquer : une section ouverte par le gabarit reste fermée si l'utilisateur l'a fermée", e.open === false);
  const f = sec("panneauApparence2", "Styles d'objet", true);
  appliquer_section(f, {});
  ok("appliquer : jamais touchée par l'utilisateur → l'état du gabarit", f.open === true);
  const g = sec("panneauApparence2", "Effets · 3", false);
  appliquer_section(g, { "panneauApparence2:Effets": true });
  ok("appliquer : le compteur a changé, la section reste ouverte", g.open === true);
}

if (echecs.length) {
  console.error(`sections : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("sections : ok");
