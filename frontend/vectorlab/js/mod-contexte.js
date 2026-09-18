// mod-contexte.js — la barre contextuelle d'Affinity (R5) : le libellé de
// la sélection, les champs inline de l'outil courant (données : id, type,
// libellé, valeur, options), l'application PURE d'un changement (rend un
// patch à fusionner dans l'état), et les paramètres de l'appli
// (dz_vl_params). Feuille pure ; l'UI (mod-barrecontexte) traduit.
export function libelle_selection(objets) {
  const n = Array.isArray(objets) ? objets.length : 0;
  if (!n) return "Aucune sélection";
  if (n === 1) return `1 objet · ${objets[0] && objets[0].type ? objets[0].type : "objet"}`;
  return `${n} objets`;
}
const opts = (liste, id = "id", lib = ["nom", "libelle", "famille"]) => (Array.isArray(liste) ? liste : []).map((x) => ({ id: x[id], libelle: lib.map((k) => x[k]).find((v) => v) || String(x[id]) }));
const nombre = (id, libelle, valeur, min, max, pas = 1) => ({ id, type: "number", libelle, valeur: +valeur || 0, min, max, pas });
const select = (id, libelle, valeur, options) => ({ id, type: "select", libelle, valeur, options });
const MODES_PLUME = [{ id: "plume", nom: "Plume" }, { id: "intelligent", nom: "Intelligent" }, { id: "polygone", nom: "Polygone" }, { id: "ligne", nom: "Ligne" }];
const ACTIONS_PLUME = [["vif", "Vif"], ["lisse", "Lisse"], ["intelligent", "Intelligent"], ["fractionner", "Fractionner"], ["ouvrir", "Ouvrir"], ["fermer", "Fermer"], ["lisserCourbe", "Courbe lisse"], ["relier", "Relier"], ["inverser", "Inverser"]];
const ALIGN_NOEUDS = [["gauche", "⇤"], ["centreH", "⇔"], ["droite", "⇥"], ["haut", "⇧"], ["centreV", "⇕"], ["bas", "⇩"]];
const MODES_TRANCHE = [{ id: "document", nom: "Document" }, { id: "objets", nom: "Par objet" }, { id: "planches", nom: "Par planche" }, { id: "calques", nom: "Par calque" }, { id: "dessinees", nom: "Dessinées" }];
export function champs_de(outil, etat) {
  if (!etat || typeof etat !== "object") return [];
  const px = etat.px || {}, pv = etat.pinceauv || {};
  switch (outil) {
    case "select": {
      const sel = etat.selection || [];
      if (!sel.length) return [{ id: "configDoc", type: "bouton", libelle: "Configuration du document…" }, { id: "parametres", type: "bouton", libelle: "Paramètres de l'appli…" }];
      const tete = (etat.objets || [])[0] || {};
      const op = tete.style && tete.style.opacite !== undefined ? +tete.style.opacite : 1;
      const b = etat.bbox || {};
      const r2 = (v) => Math.round((+v || 0) * 100) / 100;
      return [nombre("selX", "X", r2(b.x), -1e5, 1e5, 0.5), nombre("selY", "Y", r2(b.y), -1e5, 1e5, 0.5), nombre("selW", "L", r2(b.w), 1, 1e5, 0.5), nombre("selH", "H", r2(b.h), 1, 1e5, 0.5), nombre("opacite", "Opacité %", Math.round(op * 100), 0, 100)];
    }
    case "plume": return [select("plumeMode", "Mode", (etat.plume || {}).mode || "plume", opts(MODES_PLUME)), ...ACTIONS_PLUME.map(([a, l]) => ({ id: "plume:" + a, type: "bouton", libelle: l }))];
    case "noeuds": return [...ACTIONS_PLUME.map(([a, l]) => ({ id: "plume:" + a, type: "bouton", libelle: l })), ...ALIGN_NOEUDS.map(([m, g]) => ({ id: "noeuds:al-" + m, type: "bouton", libelle: g, titre: "Aligner les nœuds : " + m })), { id: "aimantNoeuds", type: "bascule", libelle: "Magnétisme", valeur: etat.aimantNoeuds !== false }];
    case "forme": return [select("formeCourante", "Forme", etat.formeCourante, opts(etat.formes))];
    case "gomme": return [nombre("gommeLargeur", "Largeur", etat.gommeLargeur, 1, 500)];
    case "coin": return [nombre("coinRayon", "Rayon", etat.coinRayon, 0, 500)];
    case "crayon": case "pinceauv": return [select("pvProfil", "Profil", pv.profil, opts(etat.profils)), nombre("pvLargeur", "Largeur", pv.largeur, 1, 200)];
    case "px-pinceau": case "px-gomme": case "px-cloner": case "px-flou": case "px-eclaircir": case "px-assombrir": return [nombre("pxRayon", "Rayon", px.rayon, 1, 256), nombre("pxDurete", "Dureté", px.durete, 0, 1, 0.05)];
    case "px-seau": return [nombre("pxTolerance", "Tolérance", px.tolerance, 0, 255), { id: "pxGlobal", type: "bascule", libelle: "Global", valeur: !!px.global }];
    case "px-baguette": return [nombre("pxTolerance", "Tolérance", px.tolerance, 0, 255)];
    case "tuiles": return [select("terrainCourant", "Terrain", etat.terrainCourant, Object.entries(etat.terrains || {}).map(([id, t]) => ({ id, libelle: (t && t.nom) || id })))];
    case "texte": { const t = etat.typo || {}; return [select("typoCourante", "Police", t.courante, opts(t.polices))]; }
    case "tranche": return [select("trMode", "Mode", (etat.exportPlus || {}).mode || "document", opts(MODES_TRANCHE))];
    default: return [];
  }
}
const borne = (v, min, max) => Math.max(min, Math.min(max, Number.isFinite(+v) ? +v : min));
export function appliquer_champ(etat, id, valeur) {
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
    case "typoCourante": return { typo: { ...(e.typo || {}), courante: String(valeur) } };
    case "trMode": return { exportPlus: { ...(e.exportPlus || {}), mode: String(valeur) } };
    case "opacite": return { style: { opacite: borne(valeur, 0, 100) / 100 } };
    case "aimantNoeuds": return { aimantNoeuds: valeur === true || valeur === "true" || valeur === 1 };
    case "selX": return { bbox: { x: borne(valeur, -1e5, 1e5) } };
    case "selY": return { bbox: { y: borne(valeur, -1e5, 1e5) } };
    case "selW": return { bbox: { w: borne(valeur, 1, 1e5) } };
    case "selH": return { bbox: { h: borne(valeur, 1, 1e5) } };
    default: return {};
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
