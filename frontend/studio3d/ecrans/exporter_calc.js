/* t400 (31/10/2026) — le CALCUL de l'écran EXPORTER du 3D Studio, sans DOM ni three.js : il tourne sous node (banc
   qa/exporter.test.mjs). exporter.js ne fait que traduire ces décisions en éléments et en requêtes.

   Les sections du panneau de droite, relevées chez Sorceress (GAME ENGINE, WEB / THREE.JS) puis complétées de ce
   que le dépôt sait déjà faire : moteurs de l'Établi (mesh_export.CIBLES), scène Godot avec hitboxes (mouvement_rig),
   LOD (mesh_lod), conventions de textures (mesh_textures), conversions LOCALES (mesh_convert), impression 3D. Chaque
   action dit pourquoi elle est grisée — jamais un bouton mort sans phrase. */
"use strict";
import { T as T0 } from "./coque_calc.js";

export const T = T0;

/* les actions, par section ; `id` = la clé de libellé exp.<id> et le data-action du bouton */
export const SECTIONS = [
  { id: "moteur", actions: ["glb_maillage", "glb_pose", "glb_animation", "fbx", "godot", "unreal", "unity", "blender"] },
  { id: "web", actions: ["threejs"] },
  { id: "optimisation", actions: ["lod", "textures"] },
  { id: "impression", actions: ["impression"] },
  { id: "formats", actions: ["formats"] },
  { id: "bibliotheque", actions: ["ranger"] },
];
export const ACTIONS = SECTIONS.flatMap((s) => s.actions);
export const CIBLES_ETABLI = ["unreal", "unity", "blender"];
export const USAGES_LOD = ["mobile", "pc", "impression"];
export const NOMMAGES = ["standard", "unreal", "unity_urp", "unity_hdrp", "godot", "blender"];
/* les conversions PAYANTES (Meshy convert) ne sont jamais proposées ici : l'écran ne dépense rien */
export const FORMATS_PAYANTS = ["fbx", "usdz", "blend"];

/* ce que le serveur appellera le fichier (même règle que studio3d_export.nom_sur) : accents retirés, puis tout ce
   qui n'est ni lettre ASCII, ni chiffre, ni _ ni - devient « _ », 48 caractères au plus */
export function nomSur(nom, defaut = "modele") {
  const sur = (x) => String(x ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^\x00-\x7f]/g, "")
    .replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^[_-]+|[_-]+$/g, "").slice(0, 48);
  return sur(nom) || sur(defaut) || "modele";
}

/* l'aperçu du nom écrit pour une variante (« Heros_v2_pose.glb ») */
export function nomExport(nom, defaut, version, variante, ext = "glb") {
  return `${nomSur(nom, defaut)}_v${version}_${variante}.${ext}`;
}

/* les clips cochés, dans l'ordre du fichier ; aucun coché = tous (le serveur l'entend de même : `clips` absent) */
export function clipsCoches(clips, coches) {
  const set = new Set(coches || []);
  const choisis = (clips || []).filter((c) => set.has(c.nom)).map((c) => c.nom);
  return choisis.length && choisis.length < (clips || []).length ? choisis : null;
}

/* hitboxes Godot par défaut, d'après les RÔLES d'os (mouvement_rig.role) : la tête, le bassin et la première vertèbre
   reçoivent (hurt), les mains et les pieds frappent (hit). Une forme et un rayon que valider_hitboxes accepte. */
const HURT = ["tete", "bassin", "colonne"];
const HIT = ["main_g", "main_d", "pied_g", "pied_d"];
export function hitboxesParDefaut(os) {
  const out = [], vus = new Set();
  for (const o of os || []) {
    if (!o || !o.role || vus.has(o.role)) continue;
    if (HURT.includes(o.role)) out.push({ os: o.nom, forme: "capsule", rayon: o.role === "tete" ? 0.5 : 0.35, role: "hurt" });
    else if (HIT.includes(o.role)) out.push({ os: o.nom, forme: "capsule", rayon: 0.3, role: "hit" });
    else continue;
    vus.add(o.role);
  }
  return out;
}

/* chaque action : permise ou grisée, avec la raison (clé exp.raison_*) */
export function disponibilite(action, etat) {
  if (!etat) return { ok: false, raison: "exp.raison_modele" };
  const clips = (etat.clips || []).length;
  switch (action) {
    case "glb_animation": return clips ? { ok: true } : { ok: false, raison: "exp.raison_clips" };
    case "godot": return etat.a_squelette && hitboxesParDefaut(etat.os).length
      ? { ok: true } : { ok: false, raison: "exp.raison_squelette" };
    case "fbx": return etat.blender && etat.blender.dispo ? { ok: true } : { ok: false, raison: "exp.raison_blender" };
    default: return ACTIONS.includes(action) ? { ok: true } : { ok: false, raison: "exp.raison_modele" };
  }
}

/* le nom de fichier d'une réponse : Content-Disposition (filename="…" ou filename*=UTF-8''…), sinon `defaut` */
export function nomDeReponse(entete, defaut) {
  const h = String(entete || "");
  const etoile = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(h);
  if (etoile) { try { return decodeURIComponent(etoile[1].trim().replace(/^"|"$/g, "")); } catch { /* suite */ } }
  const simple = /filename="?([^";]+)"?/i.exec(h);
  return simple ? simple[1].trim() : defaut;
}

/* des octets lisibles (« 1,2 Mo » / « 1.2 MB ») */
export function octets(n, lg = "fr") {
  if (!(n >= 0)) return "—";
  const u = lg === "en" ? ["B", "KB", "MB", "GB"] : ["o", "Ko", "Mo", "Go"];
  let i = 0, v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  const s = i === 0 ? String(Math.round(v)) : v.toFixed(v < 10 ? 1 : 0);
  return (lg === "en" ? s : s.replace(".", ",")) + " " + u[i];
}

/* les formats locaux à proposer : la liste du serveur (mesh_convert.LOCAL_EXPORT) moins les payants, par prudence */
export function formatsLocaux(capacites) {
  return ((capacites && capacites.local_export) || []).filter((f) => !FORMATS_PAYANTS.includes(String(f).toLowerCase()));
}

/* le corps d'une variante GLB pour POST /api/studio3d/exporter/{job}/glb */
export function corpsGlb(variante, { version, nom, clipPose, coches, clips } = {}) {
  const c = { variante, version, nom: nom || undefined };
  if (variante === "pose" && clipPose != null) c.clip = clipPose;
  if (variante === "animation") {
    const k = clipsCoches(clips, coches);
    if (k) c.clips = k;
  }
  return c;
}
