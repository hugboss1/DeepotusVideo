// biblio.test.mjs — la page d'accueil bibliothèque (chantier 27/08) : la
// logique PURE de mod-biblio (parseTaille, docVierge, bibLigne, bibVide).
// Le DOM n'entre jamais ici — initBiblio n'est pas importé par le banc.
import { parseTaille, docVierge, bibLigne, bibVide }
  from "../js/mod-biblio.js";
import { parserDoc } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};

/* ── parseTaille : les écritures humaines de « L×H » ── */
{
  const t = parseTaille("640x960");
  ok("parseTaille 640x960", t.w === 640 && t.h === 960, JSON.stringify(t));
}
{
  const t = parseTaille("640×960");
  ok("parseTaille avec la croix typographique", t.w === 640 && t.h === 960);
}
{
  const t = parseTaille("  320 X 240  ");
  ok("parseTaille espaces + X majuscule", t.w === 320 && t.h === 240);
}
{
  let refus = 0;
  for (const mauvais of ["", "abc", "0x100", "-5x100", "9000x100", "100"]) {
    try { parseTaille(mauvais); } catch { refus++; }
  }
  ok("parseTaille refuse vide/NaN/≤0/>8192/sans séparateur", refus === 6,
     String(refus));
}

/* ── docVierge : le document neuf est accepté par parserDoc ── */
{
  const d = docVierge("Baie", 640, 960);
  let accepte = true;
  try { parserDoc(d); } catch (e) { accepte = false; }
  ok("docVierge passe parserDoc", accepte);
  ok("docVierge : v, nom, taille", d.v === 1 && d.nom === "Baie"
     && d.taille.w === 640 && d.taille.h === 960);
  ok("docVierge : un calque déverrouillé visible, sans objet",
     d.calques.length === 1 && d.calques[0].id === "c1"
     && d.calques[0].visible === true && d.calques[0].verrou === false
     && d.calques[0].objets.length === 0, JSON.stringify(d.calques));
}

/* ── bibLigne : la carte d'un document (échappement, vignette, badges) ── */
const meta = (sur) => ({
  id: "d1", name: "Baie", role: "decor", version: 3, vignette: true,
  chapter_id: null, deck_id: null, entity_id: null, liaison: false,
  updated_at: "2026-08-27T10:00:00", ...sur,
});
{
  const h = bibLigne(meta({ name: "Baie <script>alert(1)</script>" }));
  ok("bibLigne échappe le nom", h.includes("&lt;script&gt;")
     && !h.includes("<script>"), h.slice(0, 200));
}
{
  const h = bibLigne(meta({}));
  ok("bibLigne : vignette cache-bustée par la version",
     h.includes("/api/vector/docs/d1/vignette.png?v=3"), h);
  ok("bibLigne : les trois actions portent l'id",
     h.includes('data-bib-open="d1"') && h.includes('data-bib-dup="d1"')
     && h.includes('data-bib-del="d1"'), h);
}
{
  const h = bibLigne(meta({ vignette: false }));
  ok("bibLigne sans vignette : repli, jamais d'img cassée",
     !h.includes("vignette.png") && h.includes("bib-sans"), h);
}
{
  ok("bibLigne : badge chapitre",
     bibLigne(meta({ chapter_id: "ch1" })).includes("⚓"));
  ok("bibLigne : badge cartes",
     bibLigne(meta({ deck_id: "deck_1" })).includes("🂠"));
  ok("bibLigne : badge bibliothèque", bibLigne(meta({})).includes("◇"));
}

/* ── bibVide : l'état vide nomme les filtres actifs ── */
{
  ok("bibVide sans filtre invite à créer",
     bibVide("", "").includes("Aucun document"));
  const m = bibVide("baie", "decor");
  ok("bibVide nomme la recherche et le rôle",
     m.includes("baie") && m.includes("decor"), m);
}

if (echecs.length) {
  console.error("ECHECS biblio :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA biblio : PASS (14 controles)");
