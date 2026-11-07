// mod-cadres.js — t417 (Photolab N7, photocraft 0.21) : Calque › Cadre. Un cadre est, pour doc.inspect, un simple groupe : seul
// layer.frame.info le reconnaît. L'écran grise selon le genre du calque actif et demande au moteur au moment du geste.
// Fonctions PURES exportées (qa/cadres-n7.test.mjs) ; moteur prouvé par backend/tests/test_photolab_n7.py.
import { trouverCalque } from "./mod-calques.js";
import { SOUS_MENU_CADRE } from "./mod-menus.js";

export const IDS_CADRE = SOUS_MENU_CADRE.ids, LIBELLES_CADRE = SOUS_MENU_CADRE.cles;

// Un cadre vide n'a rien à ajuster : le moteur le refuse, l'écran le dit avant.
export const peutAjuster = (info) => !!info && info.content != null;
// Convertir vise un calque de forme ou de texte ; le reste vise un groupe (peut-être un cadre : le moteur tranche).
export function cadreActif(id, calque) {
  if (!calque) return false;
  return id === "pl.cadre.convertir" ? calque.kind === "Shape" || calque.kind === "Type" : calque.kind === "Group";
}
export function decorerCadres(menus, calque) {
  const voir = (l) => l.map((e) => {
    if (e.type === "sous-menu") return { ...e, entrees: voir(e.entrees) };
    return e.type === "commande" && IDS_CADRE.includes(e.id) ? { ...e, etat: cadreActif(e.id, calque) ? "actif" : "inactif" } : e;
  });
  return menus.map((m) => ({ ...m, entrees: voir(m.entrees) }));
}
// Les calques qui peuvent devenir le contenu du cadre : tout sauf le cadre lui-même et ses parents directs.
export function contenusPossibles(doc, cadre) {
  const out = [];
  for (const c of (doc && doc.layers) || []) if (c.id !== cadre) out.push({ valeur: c.id, libelle: c.name });
  return out;
}
const CHAMPS = (i) => [
  { cle: "name", cleLibelle: "photolab.cadre.nom", type: "str", defaut: i.name || "" },
  { cle: "x", cleLibelle: "photolab.cadre.x", type: "number", min: -300000, max: 300000, defaut: i.frame[0], unite: "px" },
  { cle: "y", cleLibelle: "photolab.cadre.y", type: "number", min: -300000, max: 300000, defaut: i.frame[1], unite: "px" },
  { cle: "largeur", cleLibelle: "photolab.cadre.largeur", type: "number", min: 1, max: 300000, defaut: i.frame[2], unite: "px" },
  { cle: "hauteur", cleLibelle: "photolab.cadre.hauteur", type: "number", min: 1, max: 300000, defaut: i.frame[3], unite: "px" },
  { cle: "contour", cleLibelle: "photolab.cadre.contour", type: "number", min: 0, max: 288, defaut: i.stroke ? i.stroke.width || 0 : 0, unite: "px" },
];
export const champsCadre = CHAMPS;
// Dialogue -> layer.frame.set. Une rotation éventuelle (b, c de la matrice) reste celle du cadre ; le contour part en
// `stroke` (0 : aucun).
export function commandeCadre(info, v, couleur) {
  const t = info.transform;
  return { command: "layer.frame.set", params: { layer: info.layer, name: String(v.name || "").slice(0, 120) || info.name,
    transform: [Number(v.largeur), t[1], t[2], Number(v.hauteur), Number(v.x), Number(v.y)],
    stroke: Number(v.contour) > 0 ? { width: Number(v.contour), color: couleur } : null } };
}

export function initCadres(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const actif = () => (PL.etat.doc ? trouverCalque(PL.etat.doc.layers, PL.etat.doc.activeLayer) : null);
  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => decorerCadres(menus, actif()));

  async function infoCadre() {
    const c = actif();
    if (!c) return null;
    try { return await PL.get(`/cadres/${c.id}`, true); } catch (e) { PL.signaler(T("photolab.cadre.pas_un_cadre"), true); return null; }
  }
  PL.actions["pl.cadre.proprietes"] = async () => {
    const i = await infoCadre();
    if (!i) return;
    const fg = (PL.etat.couleurs && PL.etat.couleurs.fg) || "#000000";
    PL.ouvrirReglage({ id: "layer.frame.set", libelle: T("photolab.cadre.proprietes"), champs: CHAMPS(i) }, { apercu: false, versCommande: (v) => commandeCadre(i, v, fg) });
  };
  PL.actions["pl.cadre.contenu"] = async () => {
    const i = await infoCadre();
    if (!i) return;
    const valeurs = contenusPossibles(PL.etat.doc, i.layer);
    if (!valeurs.length) { PL.signaler(T("photolab.cadre.aucun_contenu"), true); return; }
    PL.ouvrirReglage({ id: "layer.frame.setContent", libelle: T("photolab.cadre.contenu"), champs: [] }, { apercu: false,
      choix: [{ cle: "content", libelle: T("photolab.cadre.calque_contenu"), valeurs }], versCommande: (p) => ({ command: "layer.frame.setContent", params: { ...p, layer: i.layer } }) });
  };
  const ajuster = (mode) => async () => {
    const i = await infoCadre();
    if (!i) return;
    if (!peutAjuster(i)) { PL.signaler(T("photolab.cadre.vide"), true); return; }
    PL.executer("layer.frame.fit", { layer: i.layer, mode });
  };
  PL.actions["pl.cadre.contenu_au_cadre"] = ajuster("contentToFrame");
  PL.actions["pl.cadre.cadre_au_contenu"] = ajuster("frameToContent");
  PL.actions["pl.cadre.convertir"] = () => { const c = actif(); if (c) PL.executer("layer.frame.convert", { layer: c.id }); };
}
