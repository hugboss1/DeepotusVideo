// mod-plateau.js — lot C côté UI : le panneau Grille (type, pas,
// subdivisions, orientation, origine, échelle — une commande op_grille par
// changement), le panneau Terrains (fiche, terrain courant du pinceau,
// définir/retoucher/retirer) et le panneau Plateau (générateur : rayon ou
// rectangle, taille, orientation, terrain, numérotation). Logique PURE en
// tête (banc node).
import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
import { op_grille, terrains_de, op_terrain_definir, op_terrain_supprimer,
         op_plateau_generer } from "./mod-doc.js";
import { GRILLE_TYPES } from "./mod-grille.js";
import { MOTIFS } from "./mod-effets.js";

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ── pur ── */
export function terrainLigne(cle, f, actif) {
  return `<div class="terrain${actif ? " actif" : ""}" data-terrain="${esc(cle)}"`
    + ` title="${T("vectorlab.plateau.terrain_aide")}">`
    + `<i style="background:${esc(f.couleur)}"></i><span class="nom">${esc(f.nom)}</span>`
    + (f.motif ? `<small class="motif" data-motif="${esc(f.motif)}">${esc(motifLibelle(f.motif))}</small>` : "")
    + `<small>${+f.hauteur_mm} mm</small></div>`;
}
/* t122 : le motif d'un terrain, par son libellé ; la saisie accepte le libellé ou l'identifiant, sans casse
   ni accent, et « aucun » / vide pour retirer le motif. null = saisie inconnue (le dialogue le dit). */
export function motifLibelle(id) {
  const m = MOTIFS.find((x) => x.id === id);
  return m ? m.libelle : "";
}
export function motifDepuisSaisie(s) {
  const n = (v) => String(v || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();
  const v = n(s);
  if (v === "" || v === "aucun") return "";
  const m = MOTIFS.find((x) => n(x.id) === v || n(x.libelle) === v);
  return m ? m.id : null;
}
export function grilleLibelle(g, pasAffichage) {
  if (!g) return String(pasAffichage);                 // l'icône dz-edit-grille est posée par core (majBoutonGrille)
  if (g.type === "hex") return `hex ${g.pas} ${g.orientation}`;
  if (g.type === "carree") return `${g.pas}` + (g.sous > 1 ? ` ÷${g.sous}` : "");
  return `${g.type} ${g.pas}`;
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
        <select id="grType" title="${T("vectorlab.plateau.grille_aide")}">
          <option value=""${g ? "" : " selected"}>${T("vectorlab.plateau.aucune_affichage")}</option>
          ${GRILLE_TYPES.map((t) => `<option value="${t}"${g && g.type === t ? " selected" : ""}>${t}</option>`).join("")}
        </select></div>
      ${g ? `
      <div class="ap-ligne"><span>${T("vectorlab.plateau.pas")}</span>
        <input type="number" id="grPas" min="1" step="1" value="${g.pas}" title="${T("vectorlab.plateau.pas_aide")}"/>
        ${g.type === "carree" ? `<input type="number" id="grSous" min="1" max="10" step="1" value="${g.sous}" title="Subdivisions"/>` : ""}
        ${g.type === "hex" ? `<select id="grOrient" title="Orientation"><option value="pointe"${g.orientation === "pointe" ? " selected" : ""}>${T("vectorlab.plateau.pointe")}</option><option value="plat"${g.orientation === "plat" ? " selected" : ""}>${T("vectorlab.plateau.plat")}</option></select>` : ""}
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.plateau.origine")}</span>
        <input type="number" id="grOx" step="1" value="${g.origine[0]}" title="${T("vectorlab.plateau.origine_x")}"/>
        <input type="number" id="grOy" step="1" value="${g.origine[1]}" title="${T("vectorlab.plateau.origine_y")}"/></div>
      <div class="ap-ligne"><span>${T("vectorlab.plateau.echelle")}</span>
        <input type="number" id="grSx" step="0.05" min="0.05" value="${g.echelle[0]}" title="${T("vectorlab.plateau.echelle_x")}"/>
        <input type="number" id="grSy" step="0.05" min="0.05" value="${g.echelle[1]}" title="${T("vectorlab.plateau.echelle_y")}"/></div>` : ""}`;
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
      + `<div class="ap-ligne"><button id="terPlus" title="${T("vectorlab.plateau.terrain_plus_aide")}">${dzi("dz-action-ajouter", 16)}${T("vectorlab.plateau.terrain")}</button>
         <button id="terMoins" title="${T("vectorlab.plateau.surcharge_aide")}">${dzi("dz-action-reinitialiser", 16)}${T("vectorlab.plateau.surcharge")}</button></div>`;
    hT.querySelectorAll(".terrain").forEach((el) => {
      el.addEventListener("click", () => { etat.terrainCourant = el.dataset.terrain; rendreTerrains(); });
      el.addEventListener("dblclick", () => retoucher(el.dataset.terrain));
    });
    $("#terPlus").addEventListener("click", async () => {
      const cle = await VL.dialogue.saisir(T("vectorlab.plateau.cle_q"), { valeur: "sable", titre: T("vectorlab.plateau.nouveau_terrain") });
      if (!cle) return;
      retoucher(cle.trim().toLowerCase(), true);
    });
    $("#terMoins").addEventListener("click", () => VL.executer(op_terrain_supprimer, etat.terrainCourant));
  }
  async function retoucher(cle, neuf) {
    const f = terrains_de(etat.doc)[cle] || { nom: cle, couleur: "#C2B280", hauteur_mm: 1 };
    const nom = await VL.dialogue.saisir(T("vectorlab.plateau.nom_q"), { valeur: f.nom, titre: T("vectorlab.plateau.terrain_titre", { cle }) }); if (nom === null) return;
    const couleur = await VL.dialogue.saisir(T("vectorlab.plateau.couleur_q"), { valeur: f.couleur, titre: T("vectorlab.plateau.terrain_titre", { cle }) }); if (couleur === null) return;
    const h = await VL.dialogue.saisir(T("vectorlab.plateau.hauteur_q"), { valeur: String(f.hauteur_mm), titre: T("vectorlab.plateau.terrain_titre", { cle }) }); if (h === null) return;
    // t122 : le motif, dit par son libellé ; une saisie inconnue est redemandée en le disant, jamais avalée
    const choix = "aucun, " + MOTIFS.map((m) => m.libelle.toLowerCase()).join(", ");
    let motif = null, question = T("vectorlab.plateau.motif_q", { choix }), valeur = motifLibelle(f.motif) || "aucun";
    while (motif === null) {
      const s = await VL.dialogue.saisir(question, { valeur, titre: T("vectorlab.plateau.terrain_titre", { cle }) }); if (s === null) return;
      motif = motifDepuisSaisie(s);
      if (motif === null) { question = T("vectorlab.plateau.motif_inconnu", { s, choix }); valeur = s; }
    }
    const avant = JSON.stringify(etat.doc.terrains || {});
    VL.executer(op_terrain_definir, cle, { nom, couleur: couleur.trim(), hauteur_mm: Math.max(0, +h || 0), motif });
    if (JSON.stringify(etat.doc.terrains || {}) !== avant || neuf) {
      etat.terrainCourant = cle;
      rendreTerrains();
    }
  }

  function rendrePlateau() {
    if (!etat.doc) { hP.innerHTML = ""; return; }
    const g = etat.doc.grille;
    hP.innerHTML = `
      <div class="ap-ligne"><span>${T("vectorlab.plateau.forme")}</span>
        <select id="plMode"><option value="rayon">${T("vectorlab.plateau.disque")}</option><option value="rect">rectangle</option></select>
        <input type="number" id="plN1" min="0" max="60" value="3" title="${T("vectorlab.plateau.n1_aide")}"/>
        <input type="number" id="plN2" min="1" max="120" value="4" title="${T("vectorlab.plateau.n2_aide")}" style="display:none"/></div>
      <div class="ap-ligne"><span>${T("vectorlab.plateau.hexagone")}</span>
        <input type="number" id="plPas" min="4" value="${g && g.type === "hex" ? g.pas : 40}" title="${T("vectorlab.plateau.pl_pas_aide")}"/>
        <select id="plOrient"><option value="pointe">${T("vectorlab.plateau.pointe")}</option><option value="plat">${T("vectorlab.plateau.plat")}</option></select></div>
      <div class="ap-ligne"><label><input type="checkbox" id="plNum"/> ${T("vectorlab.plateau.numeroter")}</label>
        <button id="plGenerer" class="primaire" title="${T("vectorlab.plateau.generer_aide")}">${T("vectorlab.plateau.generer")}</button></div>`;
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
        VL.toast(T("vectorlab.plateau.tuiles_posees", { n: r.tuiles.length }));
      }
    });
  }

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendreGrille(); rendreTerrains(); rendrePlateau(); };
  VL.grilleLibelle = grilleLibelle;
}
