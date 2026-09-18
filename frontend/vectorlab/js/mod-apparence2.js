// mod-apparence2.js — le panneau « Apparence + » du lot F et l'outil pinceau
// vectoriel : effets de calque (liste éditable), mode de fusion, contours
// multiples, remplissages avancés (conique, transparence, motifs),
// écrêtage, couleurs globales et harmonies, styles d'objet, symboles,
// texte + (cadre, alignement, texte sur chemin). Chaque geste = UNE
// commande via VL.executer sur les ops pures de mod-doc.
import { op_style, op_degrade_creer, op_degrade_transparence, op_motif_creer, op_ecreter, op_desecreter,
         op_couleur_globale_definir, op_couleur_globale_supprimer, op_style_definir, op_style_appliquer,
         op_style_supprimer, op_symbole_creer, op_instance_poser, op_symbole_detacher, op_symbole_supprimer,
         op_texte_en_cadre, op_texte_sur_chemin, op_textechemin_decalage, op_ajouter, op_supprimer } from "./mod-doc.js";
import { EFFETS, effet_defaut, MODES_FUSION, MOTIFS, motif_defaut } from "./mod-effets.js";
import { palette_harmonique, HARMONIES, op_palette_ajouter } from "./mod-couleur.js";
import { PROFILS, trait_profil } from "./mod-pinceauvec.js";
import { simplifier } from "./mod-crayon.js";

const SNS = "http://www.w3.org/2000/svg";
export const OUTILS3 = [
  { id: "pinceauv", touche: "j", titre: "Pinceau vectoriel à profil — largeur, profil et angle dans Apparence + (J)" },
];
export const HINTS3 = {
  pinceauv: "dessiner : le trait devient un chemin fermé rempli, à la largeur et au profil choisis (plat, fuseau, calligraphie)",
};
const _num = (v, defaut) => { const x = +String(v ?? "").replace(",", "."); return Number.isFinite(x) ? x : defaut; };
const _hex = (v, defaut) => (/^#[0-9A-Fa-f]{6}$/.test(String(v || "")) ? String(v).toUpperCase() : defaut);
export const EFFET_CHAMPS = {
  ombre: [{ cle: "dx", lib: "dx" }, { cle: "dy", lib: "dy" }, { cle: "flou", lib: "flou" }, { cle: "couleur", lib: "couleur" }, { cle: "opacite", lib: "opacité" }],
  ombre_interne: [{ cle: "dx", lib: "dx" }, { cle: "dy", lib: "dy" }, { cle: "flou", lib: "flou" }, { cle: "couleur", lib: "couleur" }, { cle: "opacite", lib: "opacité" }],
  lueur: [{ cle: "flou", lib: "flou" }, { cle: "couleur", lib: "couleur" }, { cle: "opacite", lib: "opacité" }],
  biseau: [{ cle: "profondeur", lib: "profondeur" }, { cle: "flou", lib: "flou" }, { cle: "lumiere", lib: "lumière °" }, { cle: "opacite", lib: "opacité" }],
  contour: [{ cle: "largeur", lib: "largeur" }, { cle: "couleur", lib: "couleur" }, { cle: "opacite", lib: "opacité" }],
  incrustation: [{ cle: "couleur", lib: "couleur" }, { cle: "opacite", lib: "opacité" }],
};
const _BORNES = { flou: [0, 200], dx: [-500, 500], dy: [-500, 500], opacite: [0, 1], largeur: [0.1, 100], profondeur: [0.1, 100], lumiere: [0, 360] };
export function lire_effet(type, champs) {
  const base = effet_defaut(type);
  const out = { type };
  for (const { cle } of EFFET_CHAMPS[type]) {
    if (cle === "couleur") { out.couleur = _hex(champs.couleur, base.couleur); continue; }
    const [lo, hi] = _BORNES[cle];
    let v = _num(champs[cle], base[cle]);
    if (cle === "opacite" && v > 1) v = v / 100;              // 0..100 accepté
    out[cle] = Math.max(lo, Math.min(hi, v));
  }
  return out;
}
export function libelle_effet(e) {
  const lib = (EFFETS.find((x) => x.id === e.type) || { libelle: e.type }).libelle;
  const p = [];
  if (e.dx !== undefined) p.push(`${e.dx},${e.dy}`);
  if (e.flou !== undefined) p.push(`flou ${e.flou}`);
  if (e.largeur !== undefined) p.push(`${e.largeur} px`);
  if (e.profondeur !== undefined) p.push(`${e.profondeur}`);
  return `${lib}${p.length ? " · " + p.join(" · ") : ""}`;
}
export function contours_lire(liste) {
  return (liste || []).map((c) => ({ couleur: _hex(c.couleur, null), epaisseur: _num(c.epaisseur, 0) }))
    .filter((c) => c.couleur && c.epaisseur > 0);
}
export const nom_valide = (s) => String(s || "").trim().replace(/\s+/g, "-").replace(/[^A-Za-z0-9_-]/g, "");
const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

export function initApparence2(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauApparence2");
  etat.pinceauv = { largeur: 8, profil: "fuseau", angle: 45 };
  const stage = $("#stage");

  // l'outil dans la barre (persona Vecteur)
  for (const o of OUTILS3) {
    const b = document.createElement("button");
    b.dataset.outil = o.id; b.title = o.titre; b.textContent = "✒";
    b.addEventListener("click", () => VL.setOutil(o.id));
    $("#outils").appendChild(b);
  }
  // la mesure du texte du navigateur (injectée à la compilation des cadres)
  const cv = document.createElement("canvas"), cx = cv.getContext("2d");
  VL.mesureTexte = (texte, s = {}) => {
    cx.font = `${s.graisse || "normal"} ${Number(s.corps || 16)}px ${s.police || "Segoe UI"}`;
    return cx.measureText(String(texte || "")).width + (Number(s.interlettrage || 0) * String(texte || "").length);
  };

  const objet = () => (etat.selection.length === 1 ? (VL.objetDe(etat.selection[0]) || {}).objet || null : null);
  const style = () => { const o = objet(); return o ? (o.style || {}) : etat.styleCourant; };
  const patch = (p) => { if (etat.selection.length) VL.executer(op_style, etat.selection.slice(), p); else { Object.assign(etat.styleCourant, p); rendre(); } };

  /* ── outil pinceau vectoriel ── */
  let geste = null;
  stage.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0 || !etat.doc || etat.outil !== "pinceauv") return;
    ev.stopPropagation(); ev.preventDefault();
    geste = { points: [VL.docPt(ev.clientX, ev.clientY)] };
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    geste.points.push(VL.docPt(ev.clientX, ev.clientY));
    const t = $("#ovTmp");
    if (!t) return;
    t.innerHTML = "";
    const g = document.createElementNS(SNS, "g");
    g.setAttribute("transform", `translate(${etat.tx} ${etat.ty}) scale(${etat.zoom})`);
    const p = document.createElementNS(SNS, "path");
    try { p.setAttribute("d", trait_profil(geste.points, etat.pinceauv)); } catch (e) { return; }
    p.setAttribute("fill", etat.styleCourant.fond && etat.styleCourant.fond !== "none" ? etat.styleCourant.fond : "#1F1512");
    p.setAttribute("opacity", "0.6");
    g.appendChild(p); t.appendChild(g);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const g = geste; geste = null;
    const t = $("#ovTmp"); if (t) t.innerHTML = "";
    const pts = simplifier(g.points, 1 / etat.zoom);
    if (pts.length < 2) return;
    try {
      const d = trait_profil(pts, etat.pinceauv);
      const fond = etat.styleCourant.fond && etat.styleCourant.fond !== "none" ? etat.styleCourant.fond : "#1F1512";
      const id = VL.executer(op_ajouter, etat.calqueActif, { type: "path", d, style: { fond, contour: "none" } });
      if (id) VL.setSelection([id]);
    } catch (e) { VL.toast(e.message, true); }
  }, true);

  /* ── panneau ── */
  const pastille = (id, hex, titre) => `<button class="nu-pastille" id="${id}" data-hex="${hex}" style="background:${hex}" title="${titre}"></button>`;
  function rendre() {
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const o = objet(), s = style(), sel = etat.selection.length, d = etat.doc;
    const effets = s.effets || [], contours = s.contours || [];
    const globales = d.couleursGlobales || {}, styles = d.styles || {}, symboles = d.symboles || {};
    const fondHex = typeof s.fond === "string" && /^#/.test(s.fond) ? s.fond : "#9DB4D6";
    // Texte + : l'objet de TÊTE de la sélection (un texte + un chemin sélectionnés → « sur le chemin »)
    const o1 = sel ? ((VL.objetDe(etat.selection[0]) || {}).objet || null) : null;
    const texteSel = o1 && ["texte", "cadre", "textechemin"].includes(o1.type);
    const nInst = (sid) => { let n = 0; const v = (objs) => { for (const x of objs || []) { if (x.type === "instance" && x.symbole === sid) n++; if (x.type === "groupe") v(x.enfants); } }; d.calques.forEach((c) => v(c.objets)); return n; };
    hote.innerHTML = `
      <details open><summary class="px-tete">Effets${effets.length ? ` · ${effets.length}` : ""}</summary>
        ${effets.map((e, i) => `<div class="a2-effet" data-i="${i}"><div class="ap-ligne"><b style="flex:1">${esc(libelle_effet(e))}</b><button data-fx-x="${i}" title="Retirer">✕</button></div>
          <div class="a2-champs">${EFFET_CHAMPS[e.type].map(({ cle, lib }) => cle === "couleur"
            ? pastille(`fxc${i}`, e.couleur || "#000000", "Couleur de l'effet")
            : `<label title="${lib}"><i>${lib}</i><input type="number" step="any" data-fx="${i}" data-cle="${cle}" value="${e[cle] ?? ""}"/></label>`).join("")}</div></div>`).join("")}
        <div class="ap-ligne"><select id="a2FxType">${EFFETS.map((e) => `<option value="${e.id}">${e.libelle}</option>`).join("")}</select>
          <button id="a2FxPlus" ${sel ? "" : "disabled"} title="Ajoute l'effet à la sélection">＋</button></div>
      </details>
      <details><summary class="px-tete">Fusion &amp; contours</summary>
        <div class="ap-ligne"><span>Fusion</span><select id="a2Fusion" ${sel ? "" : "disabled"}>${MODES_FUSION.map((m) => `<option${(s.fusion || "normal") === m ? " selected" : ""}>${m}</option>`).join("")}</select></div>
        ${contours.map((c, i) => `<div class="ap-ligne"><span>${i + 1}</span>${pastille(`ctc${i}`, c.couleur, "Couleur du contour")}<input type="number" step="0.5" min="0.5" data-ct="${i}" value="${c.epaisseur}" title="Épaisseur"/><button data-ct-x="${i}" title="Retirer">✕</button></div>`).join("")}
        <div class="ap-ligne"><span></span><button id="a2CtPlus" ${sel ? "" : "disabled"} title="Ajoute un contour supplémentaire (derrière, plus large)">＋ contour</button></div>
      </details>
      <details><summary class="px-tete">Remplissage +</summary>
        <div class="ap-ligne"><button id="a2Conique" ${sel === 1 ? "" : "disabled"} title="Dégradé conique centré sur l'objet">◔ conique</button>
          <button id="a2Transp" ${sel ? "" : "disabled"} title="Dégradé de transparence (masque de gauche à droite)">◧ transparence</button>
          <button id="a2MasqueX" ${s.masque ? "" : "disabled"} title="Retire le masque de transparence">✕</button></div>
        <div class="ap-ligne"><select id="a2MotifType">${MOTIFS.map((m) => `<option value="${m.id}">${m.libelle}</option>`).join("")}</select>
          <input type="number" id="a2MotifPas" min="1" value="8" title="Pas (px)"/><input type="number" id="a2MotifAngle" step="15" value="45" title="Angle (°)"/>
          <button id="a2Motif" ${sel ? "" : "disabled"} title="Remplit la sélection d'un motif (couleur du contour courant)">motif</button></div>
        <div class="ap-ligne"><button id="a2Ecreter" ${sel >= 2 ? "" : "disabled"} title="Coller dans : le PREMIER objet sélectionné rogne les autres">⊂ coller dans</button>
          <button id="a2Liberer" ${o && o.type === "groupe" && o.clip ? "" : "disabled"} title="Libère les objets rognés">libérer</button></div>
      </details>
      <details ${Object.keys(globales).length ? "open" : ""}><summary class="px-tete">Couleurs globales</summary>
        ${Object.entries(globales).map(([n, h]) => `<div class="ap-ligne">${pastille(`glob_${n}`, h, "Changer la teinte partout")}<b style="flex:1">${esc(n)}</b>
          <button data-glob-fond="${n}" ${sel ? "" : "disabled"} title="Fond de la sélection = cette couleur globale">fond</button><button data-glob-contour="${n}" ${sel ? "" : "disabled"} title="Contour = cette couleur">contour</button><button data-glob-x="${n}" title="Supprimer (les références deviennent des hex)">✕</button></div>`).join("")}
        <div class="ap-ligne"><input type="text" id="a2GlobNom" placeholder="nom" style="flex:1"/>${pastille("a2GlobHex", fondHex, "Couleur à enregistrer")}<button id="a2GlobPlus" title="Enregistre une couleur globale">＋</button></div>
        <div class="ap-ligne"><select id="a2Harm">${HARMONIES.map((h) => `<option value="${h.id}"${etat.harmonie && etat.harmonie.type === h.id ? " selected" : ""}>${h.libelle}</option>`).join("")}</select><button id="a2HarmGen" title="Génère l'harmonie depuis la couleur de fond et l'ajoute à la palette du document">harmonie</button></div>
        <div class="px-palette" id="a2HarmPal">${(etat.harmonie ? etat.harmonie.pal : []).map((c) => `<button class="px-pastille" data-couleur="${c}" style="background:${c}" title="${c} — clic : fond de la sélection"></button>`).join("")}</div>
      </details>
      <details ${Object.keys(styles).length ? "open" : ""}><summary class="px-tete">Styles d'objet</summary>
        ${Object.keys(styles).map((n) => `<div class="ap-ligne"><b style="flex:1">${esc(n)}</b><button data-st-app="${n}" ${sel ? "" : "disabled"} title="Applique (copie) ce style à la sélection">appliquer</button><button data-st-x="${n}" title="Supprimer le style">✕</button></div>`).join("")}
        <div class="ap-ligne"><input type="text" id="a2StNom" placeholder="nom du style" style="flex:1"/><button id="a2StPlus" ${sel ? "" : "disabled"} title="Enregistre l'apparence de la sélection sous ce nom">＋</button></div>
      </details>
      ${texteSel ? `<details open><summary class="px-tete">Texte +</summary>
        ${o1.type === "texte" && sel === 1 ? `<div class="ap-ligne"><span>Cadre</span><input type="number" id="a2CadreW" min="1" value="200" title="Largeur"/><input type="number" id="a2CadreH" min="1" value="100" title="Hauteur"/><button id="a2EnCadre" title="Le texte devient un cadre à paragraphes">→ cadre</button></div>` : ""}
        ${o1.type === "cadre" && sel === 1 ? `<div class="ap-ligne"><span>Aligner</span><select id="a2Aligner">${["gauche", "centre", "droite", "justifie"].map((a) => `<option${(s.aligner || "gauche") === a ? " selected" : ""}>${a}</option>`).join("")}</select></div>
        <div class="ap-ligne"><span>Interl.</span><input type="number" id="a2Interligne" step="0.05" min="0.5" value="${s.interligne || 1.25}" title="Interligne (× corps)"/><input type="number" id="a2Retrait" min="0" value="${s.retrait || 0}" title="Retrait de première ligne (px)"/></div>` : ""}
        ${o1.type !== "textechemin" ? `<div class="ap-ligne"><button id="a2SurChemin" ${sel === 2 ? "" : "disabled"} title="Sélectionner le texte PUIS un chemin : le texte suit le chemin (le d est copié)">→ sur le chemin</button></div>` : ""}
        ${o1.type === "textechemin" && sel === 1 ? `<div class="ap-ligne"><span>Décalage</span><input type="range" id="a2Decalage" min="0" max="100" value="${o1.decalage || 0}"/><b id="a2DecalageVal">${o1.decalage || 0} %</b></div>` : ""}
      </details>` : ""}
      <details ${etat.outil === "pinceauv" ? "open" : ""}><summary class="px-tete">Pinceau vectoriel (J)</summary>
        <div class="ap-ligne"><span>Largeur</span><input type="number" id="a2PvL" min="0.5" step="0.5" value="${etat.pinceauv.largeur}"/><select id="a2PvP">${PROFILS.map((p) => `<option value="${p.id}"${etat.pinceauv.profil === p.id ? " selected" : ""}>${p.libelle}</option>`).join("")}</select></div>
        <div class="ap-ligne"><span>Angle</span><input type="number" id="a2PvA" step="5" value="${etat.pinceauv.angle}" title="Angle de la plume (calligraphie)"/></div>
      </details>`;
    lier();
  }
  function lier() {
    const on = (id, ev, fn) => { const e = $("#" + id); if (e) e.addEventListener(ev, fn); };
    const s = style();
    // effets
    on("a2FxPlus", "click", () => patch({ effets: (s.effets || []).concat(effet_defaut($("#a2FxType").value)) }));
    hote.querySelectorAll("[data-fx-x]").forEach((b) => b.addEventListener("click", () => patch({ effets: (s.effets || []).filter((_, i) => i !== +b.dataset.fxX) })));
    hote.querySelectorAll("input[data-fx]").forEach((inp) => inp.addEventListener("change", () => {
      const i = +inp.dataset.fx, effets = (s.effets || []).map((e) => ({ ...e }));
      const champs = { ...effets[i], [inp.dataset.cle]: inp.value };
      effets[i] = lire_effet(effets[i].type, champs);
      patch({ effets });
    }));
    (s.effets || []).forEach((e, i) => on(`fxc${i}`, "click", (ev) => VL.ouvrirNuancier(e.couleur || "#000000", (hex) => {
      const effets = (s.effets || []).map((x) => ({ ...x })); effets[i] = lire_effet(e.type, { ...effets[i], couleur: hex }); patch({ effets });
    }, ev.target)));
    // fusion, contours
    on("a2Fusion", "change", (ev) => patch({ fusion: ev.target.value === "normal" ? null : ev.target.value }));
    on("a2CtPlus", "click", () => patch({ contours: (s.contours || []).concat({ couleur: "#1F1512", epaisseur: ((s.contours || [])[0] || { epaisseur: (s.epaisseur || 2) }).epaisseur + 4 }) }));
    hote.querySelectorAll("[data-ct-x]").forEach((b) => b.addEventListener("click", () => { const c = (s.contours || []).filter((_, i) => i !== +b.dataset.ctX); patch({ contours: c.length ? c : null }); }));
    hote.querySelectorAll("input[data-ct]").forEach((inp) => inp.addEventListener("change", () => { const c = (s.contours || []).map((x) => ({ ...x })); c[+inp.dataset.ct].epaisseur = inp.value; patch({ contours: contours_lire(c) }); }));
    (s.contours || []).forEach((c, i) => on(`ctc${i}`, "click", (ev) => VL.ouvrirNuancier(c.couleur, (hex) => { const cs = (s.contours || []).map((x) => ({ ...x })); cs[i].couleur = hex; patch({ contours: contours_lire(cs) }); }, ev.target)));
    // remplissage +
    on("a2Conique", "click", () => {
      const b = VL.bboxSelectionDoc(); if (!b) return;
      const base = typeof s.fond === "string" && /^#/.test(s.fond) ? s.fond : "#9DB4D6";
      const sel = etat.selection.slice();
      VL.executer((doc) => { const id = op_degrade_creer(doc, { type: "conique", cx: b.x + b.w / 2, cy: b.y + b.h / 2, r: Math.max(b.w, b.h) / 2, angle: 0,
        stops: [{ t: 0, couleur: base }, { t: 0.5, couleur: "#FFFFFF" }, { t: 1, couleur: base }] }); op_style(doc, sel, { fond: `grad:${id}` }); });
    });
    on("a2Transp", "click", () => { const b = VL.bboxSelectionDoc(); if (b) VL.executer(op_degrade_transparence, etat.selection.slice(), b); });
    on("a2MasqueX", "click", () => patch({ masque: null }));
    on("a2Motif", "click", () => {
      const m = { ...motif_defaut($("#a2MotifType").value), pas: Math.max(1, _num($("#a2MotifPas").value, 8)), angle: _num($("#a2MotifAngle").value, 45),
                  couleur: _hex(s.contour, "#1F1512") };
      const sel = etat.selection.slice();
      VL.executer((doc) => { const id = op_motif_creer(doc, m); op_style(doc, sel, { fond: `motif:${id}` }); });
    });
    on("a2Ecreter", "click", () => { const [c, ...reste] = etat.selection; const gid = VL.executer(op_ecreter, c, reste); if (gid) VL.setSelection([gid]); });
    on("a2Liberer", "click", () => { const ids = VL.executer(op_desecreter, etat.selection[0]); if (ids) VL.setSelection(ids); });
    // couleurs globales
    hote.querySelectorAll("[id^='glob_']").forEach((b) => b.addEventListener("click", (ev) => VL.ouvrirNuancier(b.dataset.hex, (hex) => VL.executer(op_couleur_globale_definir, b.id.slice(5), hex), ev.target)));
    hote.querySelectorAll("[data-glob-fond]").forEach((b) => b.addEventListener("click", () => patch({ fond: `glob:${b.dataset.globFond}` })));
    hote.querySelectorAll("[data-glob-contour]").forEach((b) => b.addEventListener("click", () => patch({ contour: `glob:${b.dataset.globContour}`, epaisseur: s.epaisseur || 2 })));
    hote.querySelectorAll("[data-glob-x]").forEach((b) => b.addEventListener("click", () => VL.executer(op_couleur_globale_supprimer, b.dataset.globX)));
    on("a2GlobHex", "click", (ev) => VL.ouvrirNuancier(ev.target.dataset.hex, (hex) => { ev.target.dataset.hex = hex; ev.target.style.background = hex; }, ev.target));
    on("a2GlobPlus", "click", () => { const n = nom_valide($("#a2GlobNom").value); if (!n) { VL.toast("nom de couleur globale requis", true); return; } VL.executer(op_couleur_globale_definir, n, $("#a2GlobHex").dataset.hex); });
    on("a2HarmGen", "click", () => {
      const base = typeof s.fond === "string" && /^#/.test(s.fond) ? s.fond : "#9DB4D6";
      const type = $("#a2Harm").value;                 // lu AVANT la commande : le panneau se re-rend
      let pal;
      try { pal = palette_harmonique(base, type); } catch (e) { VL.toast(e.message, true); return; }
      etat.harmonie = { type, pal };                    // les pastilles survivent au re-rendu
      VL.executer((doc) => { for (const c of pal) { try { op_palette_ajouter(doc, c); } catch (e) { /* déjà présente */ } } });
      VL.toast(`harmonie ${type} : ${pal.join(" ")}`);
    });
    hote.querySelectorAll("#a2HarmPal [data-couleur]").forEach((b) => b.addEventListener("click", () => patch({ fond: b.dataset.couleur })));
    // styles
    on("a2StPlus", "click", () => { const n = nom_valide($("#a2StNom").value); if (!n) { VL.toast("nom de style requis", true); return; } VL.executer(op_style_definir, n, style()); });
    hote.querySelectorAll("[data-st-app]").forEach((b) => b.addEventListener("click", () => VL.executer(op_style_appliquer, etat.selection.slice(), b.dataset.stApp)));
    hote.querySelectorAll("[data-st-x]").forEach((b) => b.addEventListener("click", () => VL.executer(op_style_supprimer, b.dataset.stX)));
    // symboles
    // texte +
    on("a2EnCadre", "click", () => VL.executer(op_texte_en_cadre, etat.selection[0], _num($("#a2CadreW").value, 200), _num($("#a2CadreH").value, 100)));
    on("a2Aligner", "change", (ev) => patch({ aligner: ev.target.value }));
    on("a2Interligne", "change", (ev) => patch({ interligne: Math.max(0.5, _num(ev.target.value, 1.25)) }));
    on("a2Retrait", "change", (ev) => patch({ retrait: Math.max(0, _num(ev.target.value, 0)) }));
    on("a2SurChemin", "click", () => { const [t, c] = etat.selection; VL.executer(op_texte_sur_chemin, t, c); VL.setSelection([t]); });
    on("a2Decalage", "input", (ev) => { $("#a2DecalageVal").textContent = ev.target.value + " %"; });
    on("a2Decalage", "change", (ev) => VL.executer(op_textechemin_decalage, etat.selection[0], +ev.target.value));
    // pinceau vectoriel
    on("a2PvL", "change", (ev) => { etat.pinceauv.largeur = Math.max(0.5, _num(ev.target.value, 8)); });
    on("a2PvP", "change", (ev) => { etat.pinceauv.profil = ev.target.value; });
    on("a2PvA", "change", (ev) => { etat.pinceauv.angle = _num(ev.target.value, 45); });
  }
  void op_supprimer;

  // les ACTIONS des symboles — appelées par le menu détaché Symboles (la section du panneau est partie)
  VL.actions = VL.actions || {};
  VL.actions.symboles = {
    detacher: () => { const ids = VL.executer(op_symbole_detacher, etat.selection[0]); if (ids) VL.setSelection(ids); },
    supprimer: (sid) => VL.executer(op_symbole_supprimer, sid),
    instanceSel: () => { const t = etat.selection.length === 1 && VL.objetDe(etat.selection[0]); return !!(t && t.objet.type === "instance"); },
  };
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendre(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendre(); };
  const suivantOutil = VL.surOutil;
  VL.hints = Object.assign(VL.hints || {}, HINTS3);
  VL.surOutil = () => { suivantOutil(); if (VL.majStatut) VL.majStatut(); else { const h = $("#hintOutil"); if (h && HINTS3[etat.outil]) h.textContent = HINTS3[etat.outil]; } };
  rendre();
}
