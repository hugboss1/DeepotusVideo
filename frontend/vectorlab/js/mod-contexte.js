// mod-contexte.js — la barre contextuelle d'Affinity (R5) : le libellé de
// la sélection, les champs inline de l'outil courant (données : id, type,
// libellé, valeur, options), l'application PURE d'un changement (rend un
// patch à fusionner dans l'état), et les paramètres de l'appli
// (dz_vl_params). Feuille pure ; l'UI (mod-barrecontexte) traduit.
const TYPES_AFF = { texte: "vectorlab.contexte.type_texte", groupe: "vectorlab.contexte.type_groupe", forme: "vectorlab.contexte.type_forme", tuile: "vectorlab.contexte.type_tuile", cadre: "vectorlab.contexte.type_cadre", textechemin: "vectorlab.contexte.type_textechemin", ellipse: "vectorlab.contexte.type_ellipse" };
export function libelle_selection(objets) {
  const n = Array.isArray(objets) ? objets.length : 0;
  if (!n) return T("vectorlab.contexte.aucune_sel");
  if (n === 1) return T("vectorlab.contexte.sel_un", { type: objets[0] && objets[0].type ? (TYPES_AFF[objets[0].type] ? T(TYPES_AFF[objets[0].type]) : objets[0].type) : T("vectorlab.contexte.objet") });
  return T("vectorlab.contexte.sel_n", { n });
}
const opts = (liste, id = "id", lib = ["nom", "libelle", "famille"]) => (Array.isArray(liste) ? liste : []).map((x) => ({ id: x[id], libelle: lib.map((k) => x[k]).find((v) => v) || String(x[id]) }));
const nombre = (id, libelle, valeur, min, max, pas = 1) => ({ id, type: "number", libelle, valeur: +valeur || 0, min, max, pas });
const select = (id, libelle, valeur, options) => ({ id, type: "select", libelle, valeur, options });
const MODES_PLUME = [{ id: "plume", nom: T("vectorlab.contexte.plume") }, { id: "intelligent", nom: T("vectorlab.contexte.intelligent") }, { id: "polygone", nom: T("vectorlab.contexte.polygone") }, { id: "ligne", nom: T("vectorlab.contexte.ligne") }];
const ACTIONS_PLUME = [["vif", T("vectorlab.contexte.vif")], ["lisse", T("vectorlab.contexte.lisse")], ["intelligent", T("vectorlab.contexte.intelligent")], ["fractionner", T("vectorlab.contexte.fractionner")], ["ouvrir", T("vectorlab.contexte.ouvrir")], ["fermer", T("vectorlab.contexte.fermer")], ["lisserCourbe", T("vectorlab.contexte.courbe_lisse")], ["relier", T("vectorlab.contexte.relier")], ["inverser", T("vectorlab.contexte.inverser")]];
// G3 : le libellé (aria-label) est un mot, l'icône vient d'ICONES (al-*) — plus de glyphe flèche
const ALIGN_NOEUDS = [["gauche", T("vectorlab.contexte.al_gauche")], ["centreH", T("vectorlab.contexte.al_centre_h")], ["droite", T("vectorlab.contexte.al_droite")], ["haut", T("vectorlab.contexte.al_haut")], ["centreV", T("vectorlab.contexte.al_centre_v")], ["bas", T("vectorlab.contexte.al_bas")]];
const MODES_TRANCHE = [{ id: "document", nom: "Document" }, { id: "objets", nom: T("vectorlab.contexte.tr_objets") }, { id: "planches", nom: T("vectorlab.contexte.tr_planches") }, { id: "calques", nom: T("vectorlab.contexte.tr_calques") }, { id: "dessinees", nom: T("vectorlab.contexte.tr_dessinees") }];
import { T } from "./mod-i18n.js";
import { champs_texte, patch_texte } from "./mod-texte.js";
import { champs_pipette, appliquer_pipette } from "./mod-pipette.js";
/* 21/09 : les boutons d'une barre, regroupés par préfixe d'id (plume:*, noeuds:*, …) — un séparateur entre les groupes */
export function boutons_groupes(champs) {
  const out = [];
  let prec = null;
  for (const c of Array.isArray(champs) ? champs : []) {
    if (!c || c.type !== "bouton") continue;
    const pre = String(c.id).includes(":") ? String(c.id).split(":")[0] : "";
    if (!out.length || pre !== prec) out.push([]);
    out[out.length - 1].push(c);
    prec = pre;
  }
  return out;
}
export function champs_de(outil, etat) {
  if (!etat || typeof etat !== "object") return [];
  const px = etat.px || {}, pv = etat.pinceauv || {};
  switch (outil) {
    case "select": {
      const sel = etat.selection || [];
      const auto = { id: "selectionAuto", type: "bascule", libelle: T("vectorlab.contexte.sel_auto"), valeur: etat.selectionAuto !== false };
      if (!sel.length) return [auto, { id: "configDoc", type: "bouton", libelle: T("vectorlab.contexte.config_doc"), icone: "configDoc" }, { id: "parametres", type: "bouton", libelle: T("vectorlab.contexte.parametres"), icone: "parametres" }];
      const o0 = (etat.objets || [])[0];
      if (o0 && ["texte", "cadre", "textechemin"].includes(o0.type) && sel.length === 1) return [auto, ...champs_texte(o0.style || {}, (etat.typo || {}).polices)];
      const tete = (etat.objets || [])[0] || {};
      const op = tete.style && tete.style.opacite !== undefined ? +tete.style.opacite : 1;
      const b = etat.bbox || {};
      const r2 = (v) => Math.round((+v || 0) * 100) / 100;
      return [auto, nombre("selX", "X", r2(b.x), -1e5, 1e5, 0.5), nombre("selY", "Y", r2(b.y), -1e5, 1e5, 0.5), nombre("selW", T("vectorlab.contexte.sel_l"), r2(b.w), 1, 1e5, 0.5), nombre("selH", "H", r2(b.h), 1, 1e5, 0.5), nombre("opacite", T("vectorlab.contexte.opacite"), Math.round(op * 100), 0, 100)];
    }
    case "plume": return [select("plumeMode", "Mode", (etat.plume || {}).mode || "plume", opts(MODES_PLUME)), ...ACTIONS_PLUME.map(([a, l]) => ({ id: "plume:" + a, type: "bouton", libelle: l, icone: a }))];
    case "noeuds": return [...ACTIONS_PLUME.map(([a, l]) => ({ id: "plume:" + a, type: "bouton", libelle: l, icone: a })), ...ALIGN_NOEUDS.map(([m, g]) => ({ id: "noeuds:al-" + m, type: "bouton", libelle: g, icone: "al-" + m, titre: T("vectorlab.contexte.al_noeuds", { m: ({ gauche: T("vectorlab.contexte.m_gauche"), centreH: T("vectorlab.contexte.m_centreh"), droite: T("vectorlab.contexte.m_droite"), haut: T("vectorlab.contexte.m_haut"), centreV: T("vectorlab.contexte.m_centrev"), bas: T("vectorlab.contexte.m_bas") })[m] || m }) })), { id: "aimantNoeuds", type: "bascule", libelle: T("vectorlab.contexte.magnetisme"), valeur: etat.aimantNoeuds !== false }];
    case "forme": return [select("formeCourante", T("vectorlab.contexte.forme"), etat.formeCourante, opts(etat.formes))];
    case "gomme": return [nombre("gommeLargeur", T("vectorlab.contexte.largeur"), etat.gommeLargeur, 1, 500)];
    case "coin": return [nombre("coinRayon", T("vectorlab.contexte.rayon"), etat.coinRayon, 0, 500)];
    case "crayon": case "pinceauv": return [select("pvProfil", T("vectorlab.contexte.profil"), pv.profil, opts(etat.profils)), nombre("pvLargeur", T("vectorlab.contexte.largeur"), pv.largeur, 1, 200)];
    // lot 2 (Sprite Editor) : Forme rond / carré, Secondaire (clic droit ; vide = transparent = gomme), Pixel-parfait du crayon
    case "px-pinceau": return [nombre("pxRayon", T("vectorlab.contexte.rayon"), px.rayon, 1, 256), nombre("pxDurete", T("vectorlab.contexte.durete"), px.durete, 0, 1, 0.05), select("pxForme", T("vectorlab.contexte.forme"), px.forme || "rond", FORMES_PINCEAU), champSecondaire(px), champPipette(px)];
    case "px-gomme": return [nombre("pxRayon", T("vectorlab.contexte.rayon"), px.rayon, 1, 256), nombre("pxDurete", T("vectorlab.contexte.durete"), px.durete, 0, 1, 0.05), select("pxForme", T("vectorlab.contexte.forme"), px.forme || "rond", FORMES_PINCEAU)];
    case "px-crayon": return [{ id: "pxParfait", type: "bascule", libelle: T("vectorlab.contexte.pixel_parfait"), valeur: px.parfait !== false }, champSecondaire(px), champPipette(px)];
    case "px-cloner": case "px-flou": case "px-eclaircir": case "px-assombrir": return [nombre("pxRayon", T("vectorlab.contexte.rayon"), px.rayon, 1, 256), nombre("pxDurete", T("vectorlab.contexte.durete"), px.durete, 0, 1, 0.05)];
    case "px-seau": return [nombre("pxTolerance", T("vectorlab.contexte.tolerance"), px.tolerance, 0, 255), { id: "pxGlobal", type: "bascule", libelle: T("vectorlab.contexte.global"), valeur: !!px.global }, champPipette(px)];
    case "px-baguette": return [nombre("pxTolerance", T("vectorlab.contexte.tolerance"), px.tolerance, 0, 255)];
    case "tuiles": return [select("terrainCourant", "Terrain", etat.terrainCourant, Object.entries(etat.terrains || {}).map(([id, t]) => ({ id, libelle: (t && t.nom) || id })))];
    case "texte": { const t = etat.typo || {}; const o = (etat.objets || [])[0]; const st = o && ["texte", "cadre", "textechemin"].includes(o.type) ? (o.style || {}) : (t.styleDefaut || {}); return champs_texte(st, t.polices); }
    case "pipette": return champs_pipette(etat);   // 21/09 : le Sélecteur de couleur
    case "tranche": return [select("trMode", "Mode", (etat.exportPlus || {}).mode || "document", opts(MODES_TRANCHE))];
    default: return [];
  }
}
const borne = (v, min, max) => Math.max(min, Math.min(max, Number.isFinite(+v) ? +v : min));
const FORMES_PINCEAU = [{ id: "rond", libelle: T("vectorlab.contexte.rond") }, { id: "carre", libelle: T("vectorlab.contexte.carre") }];
const MODES_PIPETTE_CTX = [{ id: "exact", libelle: T("vectorlab.contexte.exacte") }, { id: "moyenne", libelle: T("vectorlab.contexte.moyenne") }, { id: "dominante", libelle: T("vectorlab.contexte.dominante") }];
const champPipette = (px) => select("pxPipetteMode", T("vectorlab.contexte.pipette"), px.pipetteMode || "moyenne", MODES_PIPETTE_CTX);   // lot 3 : depuis le modèle
const champSecondaire = (px) => ({ id: "pxSecondaire", type: "couleur", libelle: T("vectorlab.contexte.secondaire"), valeur: px.secondaire || null, titre: T("vectorlab.contexte.secondaire_titre") });
const _HEX6 = /^#[0-9A-Fa-f]{6}$/;
export function appliquer_champ(etat, id, valeur) {
  if (String(id).startsWith("pip")) return appliquer_pipette(etat, id, valeur);   // 21/09
  const e = etat || {};
  switch (id) {
    case "gommeLargeur": return { gommeLargeur: borne(valeur, 1, 500) };
    case "coinRayon": return { coinRayon: borne(valeur, 0, 500) };
    case "formeCourante": return { formeCourante: String(valeur) };
    case "plumeMode": return { plume: { ...(e.plume || {}), mode: ["plume", "intelligent", "polygone", "ligne"].includes(String(valeur)) ? String(valeur) : "plume" } };
    case "terrainCourant": return { terrainCourant: String(valeur) };
    case "pvProfil": return { pinceauv: { ...(e.pinceauv || {}), profil: String(valeur) } };
    case "pvLargeur": return { pinceauv: { ...(e.pinceauv || {}), largeur: borne(valeur, 1, 200) } };
    case "pxRayon": return { px: { ...(e.px || {}), rayon: borne(valeur, 1, 256) } };
    case "pxDurete": return { px: { ...(e.px || {}), durete: borne(valeur, 0, 1) } };
    case "pxTolerance": return { px: { ...(e.px || {}), tolerance: borne(valeur, 0, 255) } };
    case "pxGlobal": return { px: { ...(e.px || {}), global: valeur === true || valeur === "true" || valeur === 1 } };
    case "pxPipetteMode": return { px: { ...(e.px || {}), pipetteMode: ["exact", "moyenne", "dominante"].includes(String(valeur)) ? String(valeur) : "moyenne" } };
    case "pxForme": return { px: { ...(e.px || {}), forme: String(valeur) === "carre" ? "carre" : "rond" } };
    case "pxParfait": return { px: { ...(e.px || {}), parfait: valeur === true || valeur === "true" || valeur === 1 } };
    case "pxSecondaire": return { px: { ...(e.px || {}), secondaire: _HEX6.test(String(valeur || "")) ? String(valeur).toUpperCase() : null } };
    case "typoCourante": return { typo: { ...(e.typo || {}), courante: String(valeur) } };
    case "trMode": return { exportPlus: { ...(e.exportPlus || {}), mode: String(valeur) } };
    case "opacite": return { style: { opacite: borne(valeur, 0, 100) / 100 } };
    case "aimantNoeuds": return { aimantNoeuds: valeur === true || valeur === "true" || valeur === 1 };
    case "selectionAuto": return { selectionAuto: valeur === true || valeur === "true" || valeur === 1 };
    case "selX": return { bbox: { x: borne(valeur, -1e5, 1e5) } };
    case "selY": return { bbox: { y: borne(valeur, -1e5, 1e5) } };
    case "selW": return { bbox: { w: borne(valeur, 1, 1e5) } };
    case "selH": return { bbox: { h: borne(valeur, 1, 1e5) } };
    default: {
      if (String(id).startsWith("tx")) { const p = patch_texte(id, valeur, (e.typo || {}).polices); return Object.keys(p).length ? { styleTexte: p } : {}; }
      return {};
    }
  }
}
export const PARAMS_DEFAUT = Object.freeze({ bulles: true, grillePas: 8, aimant: true });
export function params_lire(json) {
  let lu = null;
  try { lu = json ? JSON.parse(json) : null; } catch (e) { lu = null; }
  const out = { ...PARAMS_DEFAUT };
  if (lu && typeof lu === "object") {
    if (typeof lu.bulles === "boolean") out.bulles = lu.bulles;
    if (typeof lu.aimant === "boolean") out.aimant = lu.aimant;
    if (Number.isFinite(+lu.grillePas) && +lu.grillePas >= 1 && typeof lu.grillePas !== "string") out.grillePas = +lu.grillePas;
  }
  return out;
}
export function params_poser(params, cle, valeur) {
  if (!(cle in PARAMS_DEFAUT)) return params;
  return { ...params, [cle]: cle === "grillePas" ? borne(valeur, 1, 512) : !!valeur };
}
export const params_serialiser = (p) => JSON.stringify(p);
