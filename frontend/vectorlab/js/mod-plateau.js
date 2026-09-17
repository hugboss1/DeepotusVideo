// mod-plateau.js — lot C côté UI : le panneau Grille (type, pas,
// subdivisions, orientation, origine, échelle — une commande op_grille par
// changement), le panneau Terrains (fiche, terrain courant du pinceau,
// définir/retoucher/retirer) et le panneau Plateau (générateur : rayon ou
// rectangle, taille, orientation, terrain, numérotation). Logique PURE en
// tête (banc node).
import { op_grille, terrains_de, op_terrain_definir, op_terrain_supprimer,
         op_plateau_generer } from "./mod-doc.js";
import { GRILLE_TYPES } from "./mod-grille.js";

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ── pur ── */
export function terrainLigne(cle, f, actif) {
  return `<div class="terrain${actif ? " actif" : ""}" data-terrain="${esc(cle)}"`
    + ` title="Clic : terrain courant du pinceau · double-clic : retoucher">`
    + `<i style="background:${esc(f.couleur)}"></i><span class="nom">${esc(f.nom)}</span>`
    + `<small>${+f.hauteur_mm} mm</small></div>`;
}
export function grilleLibelle(g, pasAffichage) {
  if (!g) return "⊞ " + pasAffichage;
  if (g.type === "hex") return `⊞ hex ${g.pas} ${g.orientation}`;
  if (g.type === "carree") return `⊞ ${g.pas}` + (g.sous > 1 ? ` ÷${g.sous}` : "");
  return `⊞ ${g.type} ${g.pas}`;
}

/* ── DOM ── */
export function initPlateau(VL) {
  const { $, etat } = VL;
  const hG = $("#panneauGrille"), hT = $("#panneauTerrains"), hP = $("#panneauPlateau");

  function rendreGrille() {
    if (!etat.doc) { hG.innerHTML = ""; return; }
    const g = etat.doc.grille;
    hG.innerHTML = `
      <div class="ap-ligne"><span>Type</span>
        <select id="grType" title="Grille du document (sauvée avec lui) — « aucune » garde la grille carrée d'affichage">
          <option value=""${g ? "" : " selected"}>aucune (affichage)</option>
          ${GRILLE_TYPES.map((t) => `<option value="${t}"${g && g.type === t ? " selected" : ""}>${t}</option>`).join("")}
        </select></div>
      ${g ? `
      <div class="ap-ligne"><span>Pas</span>
        <input type="number" id="grPas" min="1" step="1" value="${g.pas}" title="Côté de maille, ou rayon de l'hexagone (px document)"/>
        ${g.type === "carree" ? `<input type="number" id="grSous" min="1" max="10" step="1" value="${g.sous}" title="Subdivisions"/>` : ""}
        ${g.type === "hex" ? `<select id="grOrient" title="Orientation"><option value="pointe"${g.orientation === "pointe" ? " selected" : ""}>pointe</option><option value="plat"${g.orientation === "plat" ? " selected" : ""}>plat</option></select>` : ""}
      </div>
      <div class="ap-ligne"><span>Origine</span>
        <input type="number" id="grOx" step="1" value="${g.origine[0]}" title="Origine X (px)"/>
        <input type="number" id="grOy" step="1" value="${g.origine[1]}" title="Origine Y (px)"/></div>
      <div class="ap-ligne"><span>Échelle</span>
        <input type="number" id="grSx" step="0.05" min="0.05" value="${g.echelle[0]}" title="Échelle X"/>
        <input type="number" id="grSy" step="0.05" min="0.05" value="${g.echelle[1]}" title="Échelle Y"/></div>` : ""}`;
    $("#grType").addEventListener("change", (e) => {
      const t = e.target.value;
      VL.executer(op_grille, t ? { type: t, pas: (g && g.pas) || 32 } : null);
    });
    if (!g) return;
    const patch = () => ({
      pas: Math.max(1, +$("#grPas").value || g.pas),
      sous: $("#grSous") ? Math.max(1, Math.round(+$("#grSous").value || 1)) : g.sous,
      orientation: $("#grOrient") ? $("#grOrient").value : g.orientation,
      origine: [+$("#grOx").value || 0, +$("#grOy").value || 0],
      echelle: [Math.max(0.05, +$("#grSx").value || 1), Math.max(0.05, +$("#grSy").value || 1)],
    });
    for (const id of ["grPas", "grSous", "grOrient", "grOx", "grOy", "grSx", "grSy"]) {
      const el = $("#" + id);
      if (el) el.addEventListener("change", () => VL.executer(op_grille, patch()));
    }
  }

  function rendreTerrains() {
    if (!etat.doc) { hT.innerHTML = ""; return; }
    const t = terrains_de(etat.doc);
    if (!t[etat.terrainCourant]) etat.terrainCourant = Object.keys(t)[0];
    hT.innerHTML = Object.entries(t).map(([k, f]) => terrainLigne(k, f, k === etat.terrainCourant)).join("")
      + `<div class="ap-ligne"><button id="terPlus" title="Nouveau terrain (clé, nom, couleur, hauteur mm)">＋ terrain</button>
         <button id="terMoins" title="Retirer la surcharge du terrain courant (un défaut revient à sa fiche)">− surcharge</button></div>`;
    hT.querySelectorAll(".terrain").forEach((el) => {
      el.addEventListener("click", () => { etat.terrainCourant = el.dataset.terrain; rendreTerrains(); });
      el.addEventListener("dblclick", () => retoucher(el.dataset.terrain));
    });
    $("#terPlus").addEventListener("click", () => {
      const cle = prompt("Clé du terrain ([a-z0-9_-]) :", "sable");
      if (!cle) return;
      retoucher(cle.trim().toLowerCase(), true);
    });
    $("#terMoins").addEventListener("click", () => VL.executer(op_terrain_supprimer, etat.terrainCourant));
  }
  function retoucher(cle, neuf) {
    const f = terrains_de(etat.doc)[cle] || { nom: cle, couleur: "#C2B280", hauteur_mm: 1 };
    const nom = prompt("Nom :", f.nom); if (nom === null) return;
    const couleur = prompt("Couleur hex :", f.couleur); if (couleur === null) return;
    const h = prompt("Hauteur d'extrusion (mm) :", String(f.hauteur_mm)); if (h === null) return;
    const avant = JSON.stringify(etat.doc.terrains || {});
    VL.executer(op_terrain_definir, cle, { nom, couleur: couleur.trim(), hauteur_mm: Math.max(0, +h || 0) });
    if (JSON.stringify(etat.doc.terrains || {}) !== avant || neuf) {
      etat.terrainCourant = cle;
      rendreTerrains();
    }
  }

  function rendrePlateau() {
    if (!etat.doc) { hP.innerHTML = ""; return; }
    const g = etat.doc.grille;
    hP.innerHTML = `
      <div class="ap-ligne"><span>Forme</span>
        <select id="plMode"><option value="rayon">disque (rayon)</option><option value="rect">rectangle</option></select>
        <input type="number" id="plN1" min="0" max="60" value="3" title="Rayon en tuiles / colonnes"/>
        <input type="number" id="plN2" min="1" max="120" value="4" title="Lignes (rectangle)" style="display:none"/></div>
      <div class="ap-ligne"><span>Hexagone</span>
        <input type="number" id="plPas" min="4" value="${g && g.type === "hex" ? g.pas : 40}" title="Rayon de l'hexagone (px) — ignoré si la grille hex existe"/>
        <select id="plOrient"><option value="pointe">pointe</option><option value="plat">plat</option></select></div>
      <div class="ap-ligne"><label><input type="checkbox" id="plNum"/> numéroter q,r</label>
        <button id="plGenerer" class="primaire" title="Pose la grille hexagonale (si absente, centrée) et un calque de tuiles du terrain courant — une commande, annulable">Générer le plateau</button></div>`;
    $("#plMode").addEventListener("change", (e) => {
      $("#plN2").style.display = e.target.value === "rect" ? "" : "none";
    });
    $("#plGenerer").addEventListener("click", () => {
      const mode = $("#plMode").value;
      const spec = { mode, pas: +$("#plPas").value, orientation: $("#plOrient").value,
                     terrain: etat.terrainCourant, numeroter: $("#plNum").checked };
      if (mode === "rayon") spec.rayon = Math.round(+$("#plN1").value);
      else { spec.colonnes = Math.round(+$("#plN1").value); spec.lignes = Math.round(+$("#plN2").value); }
      const r = VL.executer(op_plateau_generer, spec);
      if (r) {
        etat.calqueActif = r.calqueId;
        VL.setSelection([]);
        VL.setOutil("tuiles");
        VL.toast(`${r.tuiles.length} tuile(s) posées — pinceau actif`);
      }
    });
  }

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendreGrille(); rendreTerrains(); rendrePlateau(); };
  VL.grilleLibelle = grilleLibelle;
}
