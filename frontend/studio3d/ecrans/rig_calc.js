/* t395 (31/10/2026) — le CALCUL de l'écran Rig, sans DOM ni three.js : il tourne sous node (banc qa/rig.test.mjs).

   Le squelette SMPL de 22 os (et les deux os de poitrine en option) est celui du service backend/app/services/
   rig_local.py — mêmes identifiants, même parenté : la liste ci-dessous en est la copie, et le banc Python vérifie
   qu'elles ne divergent pas. Les articulations sont des points [x, y, z] du repère de la scène glTF (Y en haut, face
   à +Z, gauche du personnage en +X) : c'est le repère que three.js affiche, et celui où le serveur cuit les sommets.

   Les gestes de l'ajustement (relevé de Sorceress) : un clic choisit une articulation, Maj+clic l'ajoute à la
   sélection, le gizmo la déplace ; MIROIR recopie le geste sur l'articulation symétrique (de l'autre côté de l'axe
   X = axe), ENFANTS entraîne toute la descendance ; Échap désélectionne. */
"use strict";

export const OS = [
  ["pelvis", null], ["spine_01", "pelvis"], ["spine_02", "spine_01"], ["spine_03", "spine_02"],
  ["neck_01", "spine_03"], ["head", "neck_01"],
  ["clavicle_l", "spine_03"], ["upperarm_l", "clavicle_l"], ["lowerarm_l", "upperarm_l"], ["hand_l", "lowerarm_l"],
  ["clavicle_r", "spine_03"], ["upperarm_r", "clavicle_r"], ["lowerarm_r", "upperarm_r"], ["hand_r", "lowerarm_r"],
  ["thigh_l", "pelvis"], ["calf_l", "thigh_l"], ["foot_l", "calf_l"], ["ball_l", "foot_l"],
  ["thigh_r", "pelvis"], ["calf_r", "thigh_r"], ["foot_r", "calf_r"], ["ball_r", "foot_r"],
];
export const POITRINE = [["breast_l", "spine_03"], ["breast_r", "spine_03"]];
const PARENTS = Object.fromEntries([...OS, ...POITRINE]);

/* les cinq ombrages de la barre d'affichage (Wire / Solid / Texture / Tex+Wire / Weights) */
export const OMBRAGES = ["fil", "solide", "texture", "texfil", "poids"];
/* les vues caméra de /lib3d/viewer.js (orienter) proposées par l'écran */
export const VUES = ["face", "profil", "dessus", "libre"];

export const ordre = (avecPoitrine = false) => [...OS, ...(avecPoitrine ? POITRINE : [])].map(([i]) => i);
export const parentDe = (id) => (id in PARENTS ? PARENTS[id] : null);
export const cote = (id) => (/_l$/.test(id) ? "l" : /_r$/.test(id) ? "r" : null);
export const paire = (id) => (cote(id) ? id.slice(0, -1) + (cote(id) === "l" ? "r" : "l") : null);

export function enfants(id, avecPoitrine = false) {
  return ordre(avecPoitrine).filter((i) => PARENTS[i] === id);
}

/* toute la descendance d'un os, dans l'ordre de la liste */
export function descendants(id, avecPoitrine = false) {
  const out = [];
  const pile = [id];
  while (pile.length) {
    const e = enfants(pile.pop(), avecPoitrine);
    out.push(...e);
    pile.push(...e);
  }
  return ordre(avecPoitrine).filter((i) => out.includes(i));
}

export function profondeur(id) {
  let d = 0, p = PARENTS[id];
  while (p && d < 64) { d++; p = PARENTS[p]; }
  return d;
}

export const miroirX = (p, axe = 0) => [2 * axe - p[0], p[1], p[2]];

const copie = (joints) => Object.fromEntries(Object.entries(joints || {}).map(([k, v]) => [k, [...v]]));

/* déplace les articulations `ids` de `delta` ; ENFANTS entraîne leurs descendants ; MIROIR recopie chaque
   articulation bougée sur sa symétrique (si celle-ci n'est pas elle-même dans le geste) et garde un os du milieu
   (bassin, colonne, cou, tête) sur l'axe. Rend une COPIE : l'état d'avant reste intact (annuler = le garder). */
export function deplacer(joints, ids, delta, { miroir = false, avecEnfants = false, axe = 0, avecPoitrine = false } = {}) {
  const out = copie(joints);
  const bouges = new Set((ids || []).filter((i) => out[i]));
  if (avecEnfants) for (const i of [...bouges]) for (const d of descendants(i, avecPoitrine)) if (out[d]) bouges.add(d);
  for (const i of bouges) out[i] = [out[i][0] + delta[0], out[i][1] + delta[1], out[i][2] + delta[2]];
  if (miroir) {
    for (const i of bouges) {
      const p = paire(i);
      if (p === null) out[i][0] = axe;
      else if (out[p] && !bouges.has(p)) out[p] = miroirX(out[i], axe);
    }
  }
  return out;
}

/* pose l'articulation `id` à `pos` (saisie de coordonnées ou gizmo) : le même geste que deplacer, par un delta */
export function poser(joints, id, pos, opts = {}) {
  if (!joints || !joints[id]) return copie(joints);
  const a = joints[id];
  return deplacer(joints, [id], [pos[0] - a[0], pos[1] - a[1], pos[2] - a[2]], opts);
}

/* les os à dessiner : un segment parent → enfant par articulation qui a un parent présent */
export function segmentsOs(joints, avecPoitrine = false) {
  return ordre(avecPoitrine).filter((i) => joints[i] && joints[PARENTS[i]]).map((i) => [joints[PARENTS[i]], joints[i], i]);
}

/* le squelette de référence, affiché À CÔTÉ du modèle (« SMPL OFFSET ») : le gabarit décalé en X */
export function decaler(joints, dx) {
  return Object.fromEntries(Object.entries(joints || {}).map(([k, v]) => [k, [v[0] + dx, v[1], v[2]]]));
}

/* le décalage du curseur (0..200) en unités de scène : un pour cent de la hauteur par cran */
export const decalageReference = (cran, hauteur) => (Number(cran) || 0) / 100 * (hauteur || 1);

/* le pas des boutons ±1 / ±5 de l'axe de symétrie : un cran = 0,5 % de la hauteur */
export const pasAxe = (hauteur, n) => Math.round((hauteur || 1) * 0.005 * n * 1e6) / 1e6;

/* l'axe de symétrie « auto » : le milieu des paires gauche/droite (sinon le milieu de la boîte) */
export function axeAuto(joints, boite) {
  const ps = ordre(true).filter((i) => cote(i) === "l" && joints && joints[i] && joints[paire(i)]);
  if (ps.length) return ps.reduce((s, i) => s + (joints[i][0] + joints[paire(i)][0]) / 2, 0) / ps.length;
  return boite ? (boite.min[0] + boite.max[0]) / 2 : 0;
}

/* les articulations manquantes ou invalides pour un envoi */
export function manquants(joints, avecPoitrine = false) {
  return ordre(avecPoitrine).filter((i) => !(joints && Array.isArray(joints[i]) && joints[i].length === 3
    && joints[i].every((c) => Number.isFinite(c))));
}

/* le corps de POST /api/studio3d/rig/appliquer/{job} : seulement les os envoyés, arrondis au micron */
export function corps(joints, { version = null, avecPoitrine = false } = {}) {
  const r = (v) => Math.round(v * 1e6) / 1e6;
  const j = {};
  for (const i of ordre(avecPoitrine)) if (joints[i]) j[i] = joints[i].map(r);
  const b = { joints: j, poitrine: !!avecPoitrine };
  if (version) b.version = version;
  return b;
}

/* deux squelettes diffèrent-ils (au-delà d'un micron) ? — le point « modifications non enregistrées » */
export function differe(a, b, avecPoitrine = false) {
  for (const i of ordre(avecPoitrine)) {
    const p = a && a[i], q = b && b[i];
    if (!p || !q) { if (p !== q) return true; continue; }
    if (p.some((c, k) => Math.abs(c - q[k]) > 1e-6)) return true;
  }
  return false;
}

/* la sélection après un clic : Maj+clic ajoute ou retire, un clic simple remplace, un clic dans le vide garde */
export function selectionner(sel, id, maj) {
  if (!id) return [...(sel || [])];
  if (!maj) return [id];
  return sel.includes(id) ? sel.filter((i) => i !== id) : [...sel, id];
}

/* la raison pour laquelle l'auto-rig IA ne peut pas partir (clé de traduction), ou "" — le devis du backend dit
   chaque porte (GET /api/assets/3d/{job}/rig/devis) */
export function refusIA(d) {
  if (!d) return "rigx.ia_refus_devis";
  if (!d.meshy) return "rigx.ia_refus_meshy";
  if (!d.fal) return "rigx.ia_refus_fal";
  if (!d.approuve) return "rigx.ia_refus_approuve";
  if (!d.texture) return "rigx.ia_refus_texture";
  return "";
}

/* l'arrondi d'une coordonnée affichée dans la fiche de l'os (millièmes de la hauteur, au moins le millimètre) */
export function decimales(hauteur) {
  return Math.max(3, Math.min(6, Math.ceil(-Math.log10(Math.max(1e-9, (hauteur || 1) / 1000)))));
}
