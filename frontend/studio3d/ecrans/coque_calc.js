/* t388 (31/10/2026) — le CALCUL de la coque du 3D Studio à écrans, sans DOM ni three.js : il tourne sous node
   (banc qa/ecrans.test.mjs). La coque (coque.js) ne fait que traduire ces décisions en éléments.

   Les écrans, en trois groupes séparés par un filet (relevé de Sorceress, D2 de la conception) :
     1. entrer      : Ouvrir, Importer ;
     2. transformer : Préparer, Texture, Rig, Affiner, Animer, Exporter — grisés sans modèle ouvert ;
     3. à part      : Décor (végétation, accessoires), Graphe (le graphe Meshy d'hier, en vue avancée).
   L'adresse porte l'état : `?job=<id>&version=<n>&ecran=<id>` — un lien profond ouvre le bon écran sur le bon modèle. */
"use strict";

export const T = (k, v) => (typeof globalThis.dzT === "function" ? globalThis.dzT("studio3decrans." + k, v) : k);
export const langue = () => (typeof globalThis.dzLang === "function" && globalThis.dzLang() === "en" ? "en" : "fr");

export const ECRANS = [
  { id: "ouvrir", groupe: 1, icone: "dz-action-ouvrir" },
  { id: "importer", groupe: 1, icone: "dz-action-importer" },
  { id: "preparer", groupe: 2, icone: "dz-lab3d-optimiser" },
  { id: "texture", groupe: 2, icone: "dz-lab3d-materiau" },
  { id: "rig", groupe: 2, icone: "dz-lab3d-rig" },
  { id: "affiner", groupe: 2, icone: "dz-outil-px-pinceau" },
  { id: "animer", groupe: 2, icone: "dz-cat-animation" },
  { id: "exporter", groupe: 2, icone: "dz-action-exporter" },
  { id: "decor", groupe: 3, icone: "dz-cat-decor" },
  { id: "graphe", groupe: 3, icone: "dz-media-graphe-depart" },
];
const IDS = new Set(ECRANS.map((e) => e.id));

/* le parcours « Envoyer vers … → » : l'écran qui suit chaque écran du groupe 2 */
export const SUIVANT = { preparer: "texture", texture: "rig", rig: "affiner", affiner: "animer", animer: "exporter" };

/* chaque nœud du graphe Meshy d'hier renvoie à l'écran qui reprend sa fonction (tableau d'écart) */
export const ECRAN_DU_NOEUD = {
  prompt: "ouvrir", ref: "ouvrir", preview: "ouvrir", texture: "texture", remesh: "preparer", rig: "rig",
  animate: "animer", export: "exporter", etabli: "preparer",
};

/* un écran du groupe 2 sans modèle ouvert est grisé ; les autres sont toujours permis */
export function permis(id, ouvert) {
  const e = ECRANS.find((x) => x.id === id);
  if (!e) return false;
  return e.groupe !== 2 || !!(ouvert && ouvert.job);
}

/* lit l'adresse : un écran inconnu ou interdit retombe sur Ouvrir (sans modèle) ou Préparer (avec) */
export function lireAdresse(search) {
  const p = new URLSearchParams(search || "");
  const job = (p.get("job") || "").replace(/[^\w.-]/g, "") || null;
  const v = parseInt(p.get("version") || "", 10);
  const version = Number.isFinite(v) && v >= 1 ? v : null;
  let ecran = p.get("ecran") || "";
  if (!IDS.has(ecran)) ecran = job ? "preparer" : "ouvrir";
  if (!permis(ecran, job ? { job } : null)) ecran = "ouvrir";
  return { job, version, ecran };
}

/* l'adresse d'un état ; l'ordre des clés est fixe (un lien se compare tel quel) */
export function ecrireAdresse({ job, version, ecran }) {
  const p = new URLSearchParams();
  if (job) p.set("job", job);
  if (job && version) p.set("version", String(version));
  if (ecran) p.set("ecran", ecran);
  const s = p.toString();
  return s ? "?" + s : "";
}

/* nombres à la française (espace fine insécable) ou à l'anglaise (virgule) */
export function nb(n, lg = langue()) {
  if (n == null || !Number.isFinite(Number(n))) return "—";
  const s = String(Math.round(Number(n)));
  const sep = lg === "en" ? "," : " ";
  return s.replace(/\B(?=(\d{3})+(?!\d))/g, sep);
}

/* le bandeau « Ouvert » : ce qu'il montre d'une fiche serveur (studio3d_ouvert.fiche) */
export function bandeau(fiche, sale = false) {
  if (!fiche || !fiche.job) return { vide: true, texte: T("bandeau.vide") };
  const rig = fiche.rig || {};
  const morceaux = [];
  if (rig.rigge) morceaux.push(T("bandeau.os", { n: nb(rig.os) }));
  morceaux.push(T("bandeau.sommets", { n: nb(fiche.sommets) }));
  morceaux.push(T("bandeau.triangles", { n: nb(fiche.triangles) }));
  return {
    vide: false, nom: fiche.nom || fiche.job, rigge: !!rig.rigge, detail: morceaux.join(" · "),
    version: "v" + fiche.version + (fiche.derniere && fiche.derniere !== fiche.version ? "/" + fiche.derniere : ""),
    sale: !!sale, vignette: fiche.vignette || null,
  };
}

/* la galerie de l'écran Ouvrir : filtre, recherche, tri du plus récent */
export const FILTRES = ["tous", "rigges", "non_rigges", "personnages", "decor"];
/* des MOTS du nom (découpé sur tout ce qui n'est pas une lettre : « saule_moyen_1 » → saule, moyen) qui désignent un
   élément de décor ; les espèces du Décor (decor_calc.js) y sont, pour qu'un arbre rangé depuis le Décor y revienne */
const MOTS_DECOR = new Set(("arbre tree rocher rock caisse crate baril barrel tonneau plante plant buisson bush arbuste shrub "
  + "mur wall prop decor table chaise chair lampe lamp porte door herbe grass fleur flower souche stump "
  + "chene oak frene ash tremble aspen bouleau birch erable maple cerisier cherry saule willow pin pine epicea spruce "
  + "sapin fir palmier palm cocotier coconut bonsai treille trellis bruyere heather oyat baies berry").split(" "));
const mots = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z]+/).filter(Boolean);

export function estDecor(m) {
  if (m && m.categorie) return m.categorie === "decor";
  return !(m && m.rig && m.rig.rigge) && mots(m && m.nom).some((w) => MOTS_DECOR.has(w));
}

export function filtrer(modeles, filtre = "tous", recherche = "") {
  const q = String(recherche || "").trim().toLowerCase();
  return (modeles || []).filter((m) => {
    const rigge = !!(m.rig && m.rig.rigge);
    if (filtre === "rigges" && !rigge) return false;
    if (filtre === "non_rigges" && rigge) return false;
    if (filtre === "decor" && !estDecor(m)) return false;
    if (filtre === "personnages" && estDecor(m)) return false;
    if (!q) return true;
    return [m.nom, m.job, m.moteur].some((x) => String(x || "").toLowerCase().includes(q));
  });
}

export function compter(modeles) {
  const c = {};
  for (const f of FILTRES) c[f] = filtrer(modeles, f).length;
  return c;
}

/* ── écran Préparer ─────────────────────────────────────────────────────── */

/* la réduction en pour cent, arrondie à l'unité (« 93 % de réduction ») ; null si l'un des comptes manque */
export function reduction(avant, apres) {
  if (!(avant > 0) || !(apres >= 0)) return null;
  return Math.max(0, Math.round((1 - apres / avant) * 100));
}

/* le préréglage le plus proche d'une cible libre (le bouton allumé quand on bouge le curseur) */
export function presetProche(cibles, triangles) {
  if (!cibles || !cibles.length || !(triangles > 0)) return null;
  let m = cibles[0];
  for (const c of cibles) if (Math.abs(Math.log(c.triangles / triangles)) < Math.abs(Math.log(m.triangles / triangles))) m = c;
  return Math.abs(m.triangles - triangles) / m.triangles < 0.02 ? m.preset : null;
}

/* le curseur de triangles est logarithmique : 0..1000 → [mini, maxi] ; et l'inverse */
export function curseurVersTris(pos, mini, maxi) {
  const a = Math.log(Math.max(1, mini)), b = Math.log(Math.max(mini + 1, maxi));
  return Math.round(Math.exp(a + (b - a) * Math.min(1000, Math.max(0, pos)) / 1000));
}
export function trisVersCurseur(tris, mini, maxi) {
  const a = Math.log(Math.max(1, mini)), b = Math.log(Math.max(mini + 1, maxi));
  return Math.round(1000 * (Math.log(Math.min(maxi, Math.max(mini, tris))) - a) / (b - a));
}

/* une cible au-dessus du modèle n'a pas de sens (gltfpack ne crée pas de triangles) : bornée au compte d'origine */
export function cibleBornee(triangles, original) {
  if (!(original > 0)) return triangles;
  return Math.min(triangles, original);
}
