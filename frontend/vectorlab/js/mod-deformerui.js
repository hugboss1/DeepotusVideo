// mod-deformerui.js — lot D3 « Déformer » (t465) : les déformations vivantes de mod-deformer.js dans l'interface.
// Les entrées du bloc Déformer du menu Vecteur sont des actions « repeter:def-<x> » : mod-repeterui.js (déjà résolu
// par mod-charpente) les délègue ICI, de même que la section vivante de l'onglet Apparence, « Options… » et
// Décomposer. Les dialogues reprennent l'aperçu en direct de D2 (dialogue_apercu). « Modifier le contenu » est un
// bouton de la section vivante, écouté par délégation sur le document (aucune édition de mod-apparence2.js).
import { T } from "./mod-i18n.js";
import { formulaire_dom } from "./mod-tracesui.js";
import { dialogue_apercu } from "./mod-repeterui.js";
import { op_deformer, op_deformation_regler, op_deformation_editer, op_deformation_annuler, STYLES_ENVELOPPE,
         STYLES_POINTES, boite_source } from "./mod-deformer.js";

const _esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
export const EFFETS_MENU = ["enveloppe", "distorsion", "torsion", "rugosite", "zigzag", "gonfler", "pointes"];
// les clés écrites en entier (le banc i18n suit chaque clé T())
const TITRES = {
  enveloppe: "vectorlab.deformer.d_enveloppe", distorsion: "vectorlab.deformer.d_distorsion", torsion: "vectorlab.deformer.d_torsion",
  rugosite: "vectorlab.deformer.d_rugosite", zigzag: "vectorlab.deformer.d_zigzag", gonfler: "vectorlab.deformer.d_gonfler",
  pointes: "vectorlab.deformer.d_pointes",
};
const NOMS_STYLES = {
  arc: "vectorlab.deformer.s_arc", arc_bas: "vectorlab.deformer.s_arc_bas", arc_haut: "vectorlab.deformer.s_arc_haut",
  arche: "vectorlab.deformer.s_arche", renflement: "vectorlab.deformer.s_renflement", coquille_bas: "vectorlab.deformer.s_coquille_bas",
  coquille_haut: "vectorlab.deformer.s_coquille_haut", drapeau: "vectorlab.deformer.s_drapeau", vague: "vectorlab.deformer.s_vague",
  poisson: "vectorlab.deformer.s_poisson", montee: "vectorlab.deformer.s_montee", oeil: "vectorlab.deformer.s_oeil",
  gonflement: "vectorlab.deformer.s_gonflement", pression: "vectorlab.deformer.s_pression", torsion: "vectorlab.deformer.s_torsion",
};
const NOMS_POINTES = {
  aucune: "vectorlab.deformer.p_aucune", triangle: "vectorlab.deformer.p_triangle", ouverte: "vectorlab.deformer.p_ouverte",
  cercle: "vectorlab.deformer.p_cercle", carre: "vectorlab.deformer.p_carre", barre: "vectorlab.deformer.p_barre",
};
const COINS = ["vectorlab.deformer.c_hg", "vectorlab.deformer.c_hd", "vectorlab.deformer.c_bd", "vectorlab.deformer.c_bg"];

// les champs d'un dialogue, pré-remplis par des réglages ({} → les défauts de l'opération)
export function champs_deformation(effet, p = {}) {
  const nb = (id, lib, valeur, min, max, pas = 1) => ({ id, type: "nombre", libelle: T(lib), valeur, min, max, pas });
  if (effet === "enveloppe") return [
    { id: "style", type: "choix", valeur: p.style || "arc", options: STYLES_ENVELOPPE.map((s) => [s, T(NOMS_STYLES[s])]) },
    nb("courbure", "vectorlab.deformer.c_courbure", p.courbure ?? 50, -100, 100),
    { id: "orientation", type: "choix", valeur: p.orientation || "horizontale", options: [["horizontale", T("vectorlab.deformer.o_horizontale")], ["verticale", T("vectorlab.deformer.o_verticale")]] },
    nb("distH", "vectorlab.deformer.c_dist_h", p.distH ?? 0, -100, 100),
    nb("distV", "vectorlab.deformer.c_dist_v", p.distV ?? 0, -100, 100)];
  if (effet === "distorsion") {
    const c = p.coins || [[0, 0], [0, 0], [0, 0], [0, 0]];
    return c.flatMap((q, i) => [nb(`c${i}x`, COINS[i], q[0], -1e5, 1e5, 0.5), nb(`c${i}y`, COINS[i], q[1], -1e5, 1e5, 0.5)]);
  }
  if (effet === "torsion") return [nb("angle", "vectorlab.deformer.c_angle", p.angle ?? 45, -3600, 3600)];
  if (effet === "rugosite") return [nb("taille", "vectorlab.deformer.c_taille", p.taille ?? 5, 0, 1000, 0.5), nb("details", "vectorlab.deformer.c_details", p.details ?? 10, 0.1, 100, 0.5),
    { id: "lisse", type: "case", libelle: T("vectorlab.deformer.c_lisse"), valeur: !!p.lisse }, nb("graine", "vectorlab.deformer.c_graine", p.graine ?? 1, 0, 1e9)];
  if (effet === "zigzag") return [nb("taille", "vectorlab.deformer.c_taille", p.taille ?? 5, 0, 1000, 0.5), nb("cretes", "vectorlab.deformer.c_cretes", p.cretes ?? 4, 1, 100),
    { id: "lisse", type: "case", libelle: T("vectorlab.deformer.c_lisse"), valeur: !!p.lisse }];
  if (effet === "gonfler") return [nb("pourcent", "vectorlab.deformer.c_pourcent", p.pourcent ?? 30, -200, 200)];
  const choix = (id, v) => ({ id, type: "choix", valeur: v, options: STYLES_POINTES.map((s) => [s, T(NOMS_POINTES[s])]) });
  return [choix("debut", p.debut || "aucune"), choix("fin", p.fin || "triangle"), nb("echelle", "vectorlab.deformer.c_echelle", p.echelle ?? 100, 10, 1000)];
}
// les valeurs du formulaire → les réglages de l'opération (la distorsion regroupe ses huit nombres en quatre coins)
export function params_formulaire(effet, v) {
  if (effet !== "distorsion") return v;
  return { coins: [0, 1, 2, 3].map((i) => [Number(v[`c${i}x`]), Number(v[`c${i}y`])]) };
}
// la recette en une phrase (onglet Apparence)
export function resume_deformation(o) {
  const d = o && o.deformation;
  if (!d) return "";
  const p = d.params;
  if (d.effet === "enveloppe") return T("vectorlab.deformer.r_enveloppe", { style: T(NOMS_STYLES[p.style]), courbure: p.courbure });
  if (d.effet === "torsion") return T("vectorlab.deformer.r_torsion", { angle: p.angle });
  if (d.effet === "gonfler") return T("vectorlab.deformer.r_gonfler", { pourcent: p.pourcent });
  return T(TITRES[d.effet]);
}

/* ── T7 (t466) les quatre coins de la Distorsion libre, tirables sur la toile ── */
// les poignées d'une distorsion libre, en coordonnées du document : chaque coin de la boîte de la source + son
// déplacement ; rien pour un autre effet, ni en « Modifier le contenu »
export function poignees_deformation(g) {
  if (!g || !g.deformation || g.deformation.effet !== "distorsion" || g.deformation.edition) return [];
  const B = boite_source(g);
  if (!B) return [];
  const c = g.deformation.params.coins;
  return [[B.x, B.y], [B.x + B.w, B.y], [B.x + B.w, B.y + B.h], [B.x, B.y + B.h]]
    .map(([x, y], i) => ({ role: "coin" + i, x: x + c[i][0], y: y + c[i][1] }));
}
// le réglage que donne un coin tiré en (x, y), lu sur la déformation d'AVANT le geste ; null si sans objet
export function params_par_poignee_def(g, role, x, y) {
  const i = ["coin0", "coin1", "coin2", "coin3"].indexOf(role);
  const B = i >= 0 && g && g.deformation && g.deformation.effet === "distorsion" ? boite_source(g) : null;
  if (!B) return null;
  const base = [[B.x, B.y], [B.x + B.w, B.y], [B.x + B.w, B.y + B.h], [B.x, B.y + B.h]][i];
  const r2 = (v) => Math.round(v * 100) / 100;
  const coins = g.deformation.params.coins.map((q) => q.slice());
  coins[i] = [r2(x - base[0]), r2(y - base[1])];
  return { coins };
}

export function deformer_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? etat.selection.slice() : []);
  const obj = (id) => { const t = VL.objetDe(id); return t ? t.objet : null; };
  const defo = () => { const s = sel(); if (s.length !== 1) return null; const o = obj(s[0]); return o && o.deformation ? o : null; };
  const poser = (r) => { if (typeof r === "string") VL.setSelection([r]); };
  const A = { demander: (spec) => formulaire_dom(spec) };
  A.dialogue = (spec, appliquer) => dialogue_apercu(VL, A.demander, spec, appliquer);
  const creer = (effet) => ({
    peut: () => sel().length >= 1,
    faire: async () => {
      const ids = sel();
      const v = await A.dialogue({ titre: T(TITRES[effet]), champs: champs_deformation(effet) }, (d, x) => op_deformer(d, ids, effet, params_formulaire(effet, x)));
      if (v) poser(VL.executer(op_deformer, ids, effet, params_formulaire(effet, v)));
    },
  });
  const T_ = Object.fromEntries(EFFETS_MENU.map((e) => [e, creer(e)]));
  T_.options = { peut: () => !!defo(), faire: async () => {
    const g = defo();
    const e = g.deformation.effet;
    const v = await A.dialogue({ titre: T(TITRES[e]), champs: champs_deformation(e, g.deformation.params) }, (d, x) => op_deformation_regler(d, g.id, params_formulaire(e, x)));
    if (v) VL.executer(op_deformation_regler, g.id, params_formulaire(e, v));
  } };
  T_.editer = { peut: () => !!defo(), faire: () => VL.executer(op_deformation_editer, sel()[0]) };
  T_.annuler = { peut: () => !!defo(), faire: () => poser(VL.executer(op_deformation_annuler, sel()[0])) };
  A.action = (arg) => T_[arg] || { peut: () => false, faire: () => {} };
  // le geste d'un coin (comme les poignées de D2) : aperçu sur une copie du document d'avant, puis UNE exécution
  let geste = null;
  const rendre = () => { if (VL.rendre) VL.rendre(); };
  A.poignee = {
    debut: (role) => {
      const g = defo();
      if (!g || !poignees_deformation(g).some((p) => p.role === role)) return false;
      geste = { role, id: g.id, avant: etat.doc, g, params: null };
      return true;
    },
    bouger: (x, y) => {
      if (!geste) return;
      const p = params_par_poignee_def(geste.g, geste.role, x, y);
      try { const essai = JSON.parse(JSON.stringify(geste.avant)); op_deformation_regler(essai, geste.id, p); etat.doc = essai; geste.params = p; }
      catch (e) { etat.doc = geste.avant; geste.params = null; }
      rendre();
    },
    fin: () => {
      if (!geste) return;
      const g = geste;
      geste = null;
      etat.doc = g.avant;
      rendre();
      if (g.params) VL.executer(op_deformation_regler, g.id, g.params);
    },
  };
  // les coins dans l'overlay (outil Sélection) : le quadrilatère en pointillés et quatre disques tirables
  A.dessinerPoignees = (o, ov, ecranPt) => {
    if (etat.outil !== "select") return;
    const P = poignees_deformation(defo());
    if (!P.length) return;
    const e = P.map((p) => ecranPt(p.x, p.y));
    o.appendChild(ov("polygon", { points: e.map(([x, y]) => `${x},${y}`).join(" "), fill: "none", stroke: "#39b3d0", "stroke-dasharray": "4 4", "pointer-events": "none" }));
    P.forEach((p, i) => o.appendChild(ov("circle", { cx: e[i][0], cy: e[i][1], r: 6, fill: "#39b3d0", stroke: "#0d2a33", "stroke-width": 1.5,
      class: "poignee-vivant", "data-vivant": p.role, style: "pointer-events:auto;cursor:grab", "aria-label": T("vectorlab.deformer.poignee_coin") })));
  };
  A.sectionApparence = (o) => {
    if (!o || !o.deformation) return "";
    const ed = !!o.deformation.edition;
    return `<details open><summary class="px-tete">${_esc(T("vectorlab.deformer.a_titre"))}</summary>
        <div class="ap-ligne"><i class="px-note" style="flex:1">${_esc(resume_deformation(o))}</i><button id="a2VivantOptions">${_esc(T("vectorlab.repeter.a_options"))}</button><button id="a2DefEditer" class="${ed ? "actif" : ""}" title="${_esc(T("vectorlab.deformer.a_editer_titre"))}">${_esc(T(ed ? "vectorlab.deformer.a_editer_fin" : "vectorlab.deformer.m_editer"))}</button><button id="a2Detacher" title="${_esc(T("vectorlab.repeter.a_decomposer_titre"))}">${_esc(T("vectorlab.repeter.m_decomposer"))}</button></div>
      </details>`;
  };
  return A;
}

export function initDeformerUI(VL) {
  const A = deformer_actions(VL);
  VL.deformerUI = A;
  VL.actions = VL.actions || {};
  VL.actions.deformer = A;
  if (typeof document !== "undefined") {
    // « Modifier le contenu » de la section vivante : écouté par délégation (la section est reconstruite à chaque rendu)
    document.addEventListener("click", (ev) => {
      const b = ev.target && ev.target.closest && ev.target.closest("#a2DefEditer");
      if (b) { const r = A.action("editer"); if (r.peut()) r.faire(); }
    });
  }
  return A;
}
