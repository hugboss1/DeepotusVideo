// mod-persona.js — D8 : UNE surface, deux personas — Vecteur, Pixel (relooking
// Affinity du 18/09 : l'export est un ONGLET de la pile, plus un persona).
// Le persona est une classe sur <body> (`persona-vecteur|pixel|export`) : le
// CSS montre les outils et panneaux de chacun, le document reste le même.
// Le persona Export réunit les exports EXISTANTS (SVG, PNG, Bible,
// Impression 3D) sans format nouveau : ses boutons délèguent au menu.

export const PERSONAS = [
  { id: "vecteur", libelle: "Vecteur", titre: "Dessin vectoriel : formes, chemins, nœuds, booléens, texte" },
  { id: "pixel", libelle: "Pixel", titre: "Retouche des calques image au pixel et mode pixel-art vers le Tilelab" },
];
export function persona_classe(id) {
  return `persona-${PERSONAS.some((p) => p.id === id) ? id : "vecteur"}`;
}
// à quel persona appartient un outil : la sélection est partagée par tous,
// les outils `px-*` sont ceux du persona Pixel, le reste est vectoriel
export function persona_de_outil(outil) {
  if (outil === "select" || outil === "tranche") return "tous";   // la tranche (export) est un onglet des deux personas
  if (String(outil || "").startsWith("px-")) return "pixel";
  return "vecteur";
}

export function initPersona(VL) {
  const { $, etat } = VL;
  etat.persona = "vecteur";
  const nav = $("#personas");
  if (nav) {
    nav.innerHTML = PERSONAS.map((p) =>
      `<button data-persona="${p.id}" class="${p.id === "vecteur" ? "actif" : ""}" title="${p.titre}">${p.libelle}</button>`).join("");
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

  /* ── le panneau Export : les exports existants, un bouton chacun ── */
  const hote = $("#panneauExport");
  function rendreExport() {
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const lignes = [
      ["expSvg", "SVG (serveur)", "Compile ici, stocké au serveur, servi sur export.svg"],
      ["expPng1", "PNG 1×", "PNG taille du document → Library"],
      ["expPng2", "PNG 2×", "PNG double → Library"],
      ["expPng4", "PNG 4×", "PNG quadruple → Library"],
      ["expBible", "→ Bible…", "Exporte en 2× vers les images d'inspiration d'une entité de la bible"],
      ["expPrint3d", "→ Impression 3D…", "Calques en relief, plateau de tuiles, logo — STL + 3MF"],
    ];
    hote.innerHTML = `<div class="ap-ligne"><label title="Compile sans le fond du document"><input type="checkbox" id="pexTransparent"${$("#expTransparent")?.checked ? " checked" : ""}/> fond transparent</label></div>`
      + lignes.map(([id, lib, titre]) => `<div class="ap-ligne"><button data-delegue="${id}" title="${titre}" style="flex:1">${lib}</button></div>`).join("")
      + `<p class="px-note">Les planches s'exportent depuis leur panneau (persona Vecteur).</p>`;
    hote.querySelectorAll("[data-delegue]").forEach((b) => b.addEventListener("click", () => {
      const cible = $("#" + b.dataset.delegue);
      if (cible) cible.click(); else VL.toast("export indisponible", true);
    }));
    $("#pexTransparent").addEventListener("change", (ev) => { const t = $("#expTransparent"); if (t) t.checked = ev.target.checked; });
  }
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendreExport(); };
  rendreExport();
}
