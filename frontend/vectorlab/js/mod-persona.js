// mod-persona.js — D8 : UNE surface, deux personas — Vecteur, Pixel (relooking
// Affinity du 18/09 : l'export est un ONGLET de la pile, plus un persona).
// Le persona est une classe sur <body> (`persona-vecteur|pixel|export`) : le
// CSS montre les outils et panneaux de chacun, le document reste le même.
// Le persona Export réunit les exports EXISTANTS (SVG, PNG, Bible,
// Impression 3D) sans format nouveau : ses boutons délèguent au menu.

import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
export const PERSONAS = [
  { id: "vecteur", libelle: T("vectorlab.persona.vecteur"), icone: "dz-nav-espace-vecteur", titre: T("vectorlab.persona.vecteur_titre") },
  { id: "pixel", libelle: "Pixel", icone: "dz-nav-espace-pixel", titre: T("vectorlab.persona.pixel_titre") },
];
export function persona_classe(id) {
  return `persona-${PERSONAS.some((p) => p.id === id) ? id : "vecteur"}`;
}
// à quel persona appartient un outil : la sélection est partagée par tous,
// les outils `px-*` sont ceux du persona Pixel, le reste est vectoriel
export function persona_de_outil(outil) {
  if (["select", "tranche", "main", "loupe", "recadrer", "image"].includes(outil)) return "tous";   // la tranche (export) est un onglet des deux personas
  if (String(outil || "").startsWith("px-")) return "pixel";
  return "vecteur";
}

/* t125 (07/10/2026) : le persona DEMANDÉ à l'ouverture — `?persona=` dans
   l'URL, sinon la demande à usage unique `dz_vl_persona` posée par le lanceur
   « Assets 2D » du hub Game Assets (l'iframe du Vectorlab a une URL fixe : la
   demande passe par le stockage, même origine). Inconnu ou illisible → rien. */
export function persona_demandee(search, lire) {
  const ok = (v) => (PERSONAS.some((p) => p.id === v) ? v : null);
  try { const u = new URLSearchParams(search || "").get("persona"); if (u) return ok(u); } catch { /* URL illisible */ }
  try { return ok(lire("dz_vl_persona")); } catch { return null; }
}

export function initPersona(VL) {
  const { $, etat } = VL;
  etat.persona = "vecteur";
  const nav = $("#personas");
  if (nav) {
    nav.innerHTML = PERSONAS.map((p) =>
      `<button data-persona="${p.id}" class="${p.id === "vecteur" ? "actif" : ""}" title="${p.titre}">${dzi(p.icone, 16)}${p.libelle}</button>`).join("");
  }
  function setPersona(id) {
    if (!PERSONAS.some((p) => p.id === id)) id = "vecteur";
    etat.persona = id;
    for (const p of PERSONAS) document.body.classList.toggle(persona_classe(p.id), p.id === id);
    document.querySelectorAll("#personas button").forEach((b) => b.classList.toggle("actif", b.dataset.persona === id));
    // un outil qui n'appartient pas au persona retombe sur la sélection
    const de = persona_de_outil(etat.outil);
    if (de !== "tous" && de !== id) VL.setOutil("select");
    VL.surPersona();
    if (etat.doc) VL.rendreOverlay();
  }
  VL.surPersona = VL.surPersona || (() => {});
  VL.setPersona = setPersona;
  document.querySelectorAll("#personas button").forEach((b) =>
    b.addEventListener("click", () => setPersona(b.dataset.persona)));
  setPersona("vecteur");
  // t125 : la demande du lanceur est CONSOMMÉE (un rechargement repart en Vecteur)
  const demande = persona_demandee(location.search, (k) => localStorage.getItem(k));
  try { localStorage.removeItem("dz_vl_persona"); } catch { /* stockage bloqué */ }
  if (demande && demande !== "vecteur") setPersona(demande);

  /* ── le panneau Export : les exports existants, un bouton chacun ── */
  const hote = $("#panneauExport");
  function rendreExport() {
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const lignes = [
      ["expSvg", T("vectorlab.persona.exp_svg"), T("vectorlab.persona.exp_svg_titre")],
      ["expPng1", "PNG 1×", T("vectorlab.persona.exp_png1_titre")],
      ["expPng2", "PNG 2×", T("vectorlab.persona.exp_png2_titre")],
      ["expPng4", "PNG 4×", T("vectorlab.persona.exp_png4_titre")],
      ["expBible", "Bible…", T("vectorlab.persona.exp_bible_titre"), "dz-nav-bible"],
      ["expPrint3d", T("vectorlab.persona.exp_print3d"), T("vectorlab.persona.exp_print3d_titre"), "dz-lab3d-impression-3d"],
    ];
    hote.innerHTML = `<div class="ap-ligne"><label title="${T("vectorlab.persona.transparent_titre")}"><input type="checkbox" id="pexTransparent"${$("#expTransparent")?.checked ? " checked" : ""}/> ${T("vectorlab.persona.transparent")}</label></div>`
      + lignes.map(([id, lib, titre, icone]) => `<div class="ap-ligne"><button data-delegue="${id}" title="${titre}" style="flex:1">${icone ? dzi(icone, 16) : ""}${lib}</button></div>`).join("")
      + `<p class="px-note">${T("vectorlab.persona.planches_note")}</p>`;
    hote.querySelectorAll("[data-delegue]").forEach((b) => b.addEventListener("click", () => {
      const cible = $("#" + b.dataset.delegue);
      if (cible) cible.click(); else VL.toast(T("vectorlab.persona.export_indispo"), true);
    }));
    $("#pexTransparent").addEventListener("change", (ev) => { const t = $("#expTransparent"); if (t) t.checked = ev.target.checked; });
  }
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendreExport(); };
  rendreExport();
}
