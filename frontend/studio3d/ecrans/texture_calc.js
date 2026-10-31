/* t393 (31/10/2026) — le CALCUL de l'écran Texture (volet 1/2), sans DOM ni three.js : il tourne sous node
   (banc qa/texture.test.mjs). L'écran (texture.js) ne fait que traduire ces décisions en caméra, lumières et éléments.

   Relevé de Sorceress (§4 de l'inventaire) : rosace FRONT/BACK/LEFT/RIGHT/TOP/BOTTOM + quatre vues ¾, orbite par pas
   de 15/30/45/90°, éclairages Sans lumière (albédo pur) / Plat / Doux / 3 points / Vif avec deux curseurs (Bright,
   Ambient), cadre de capture au ratio choisi, modèle d'image, résolution 1K/2K/4K.

   Repère : y vers le haut, le modèle regarde +z (convention glTF). L'azimut 0 est la FACE (caméra sur +z), 90° la
   DROITE (caméra sur +x), 180° le DOS, 270° la GAUCHE. L'élévation monte de -89° (dessous) à +89° (dessus) : jamais
   ±90° pile, où la caméra perdrait son « haut » (OrbitControls basculerait). */
"use strict";

/* ── la rosace des vues ─────────────────────────────────────────────────── */
export const ELEVATION_MAX = 89;
export const VUES = [
  { id: "face", azimut: 0, elevation: 0 },
  { id: "dos", azimut: 180, elevation: 0 },
  { id: "gauche", azimut: 270, elevation: 0 },
  { id: "droite", azimut: 90, elevation: 0 },
  { id: "dessus", azimut: 0, elevation: ELEVATION_MAX },
  { id: "dessous", azimut: 0, elevation: -ELEVATION_MAX },
  /* les ¾ : à 45° de la face ou du dos, un peu au-dessus (20°) — une vue d'objet, pas un profil */
  { id: "avant_droite", azimut: 45, elevation: 20 },
  { id: "avant_gauche", azimut: 315, elevation: 20 },
  { id: "arriere_droite", azimut: 135, elevation: 20 },
  { id: "arriere_gauche", azimut: 225, elevation: 20 },
];
export const PAS = [15, 30, 45, 90];

export const vue = (id) => VUES.find((v) => v.id === id) || null;

const rad = (d) => (d * Math.PI) / 180;
const arrondi = (x) => Math.round(x * 1e9) / 1e9 + 0;   // + 0 : jamais de « -0 »

/* azimut ramené dans [0, 360) ; élévation bornée à ±ELEVATION_MAX */
export function normaliser({ azimut, elevation }) {
  const a = ((Number(azimut) % 360) + 360) % 360;
  const e = Math.max(-ELEVATION_MAX, Math.min(ELEVATION_MAX, Number(elevation) || 0));
  return { azimut: arrondi(a), elevation: arrondi(e) };
}

/* un cran d'orbite : dAz et dEl valent -1, 0 ou +1, multipliés par le pas (15/30/45/90) */
export function orbiter(pose, dAz, dEl, pas) {
  const p = PAS.includes(Number(pas)) ? Number(pas) : 45;
  return normaliser({ azimut: pose.azimut + dAz * p, elevation: pose.elevation + dEl * p });
}

/* la direction unitaire (du centre vers la caméra) d'une pose */
export function direction({ azimut, elevation }) {
  const a = rad(azimut), e = rad(elevation);
  return { x: arrondi(Math.cos(e) * Math.sin(a)), y: arrondi(Math.sin(e)), z: arrondi(Math.cos(e) * Math.cos(a)) };
}

/* la position de la caméra : centre + distance × direction */
export function positionCamera(centre, distance, pose) {
  const d = direction(pose);
  return { x: centre.x + distance * d.x, y: centre.y + distance * d.y, z: centre.z + distance * d.z };
}

/* l'inverse : la pose d'une caméra posée librement (après une orbite à la souris) */
export function poseDepuis(centre, position) {
  const dx = position.x - centre.x, dy = position.y - centre.y, dz = position.z - centre.z;
  const r = Math.hypot(dx, dy, dz) || 1;
  return normaliser({ azimut: (Math.atan2(dx, dz) * 180) / Math.PI, elevation: (Math.asin(dy / r) * 180) / Math.PI });
}

/* la vue nommée qui correspond à une pose (à un degré près), sinon null : le bouton allumé de la rosace */
export function vueDe(pose) {
  const p = normaliser(pose);
  const proche = (a, b) => Math.abs(a - b) < 1 || Math.abs(Math.abs(a - b) - 360) < 1;
  for (const v of VUES) {
    if (Math.abs(v.elevation) === ELEVATION_MAX && Math.abs(p.elevation - v.elevation) < 1) return v.id;
    if (proche(v.azimut, p.azimut) && Math.abs(v.elevation - p.elevation) < 1) return v.id;
  }
  return null;
}

/* ── les éclairages ─────────────────────────────────────────────────────── */
export const ECLAIRAGES = ["sans", "plat", "doux", "trois", "vif"];

/* intensités des lumières pour un mode ; `vif` (Bright) multiplie les directionnelles, `ambiant` l'hémisphère.
   `sans` = albédo pur : aucune lumière, les matières passent en « sans éclairage » (la couleur de base telle quelle). */
const BASE = {
  sans: { hemi: 0, cle: 0, appoint: 0, contre: 0 },
  plat: { hemi: 3.2, cle: 0, appoint: 0, contre: 0 },
  doux: { hemi: 1.8, cle: 0.8, appoint: 0.3, contre: 0 },
  trois: { hemi: 0.45, cle: 1.8, appoint: 0.7, contre: 1.1 },
  vif: { hemi: 2.4, cle: 2.4, appoint: 0.6, contre: 0.4 },
};
export function eclairage(mode, vif = 1, ambiant = 1) {
  const b = BASE[mode] || BASE.doux;
  const v = Math.max(0, Math.min(3, Number(vif))), a = Math.max(0, Math.min(3, Number(ambiant)));
  return { mode: BASE[mode] ? mode : "doux", sansLumiere: mode === "sans", hemi: arrondi(b.hemi * a),
    cle: arrondi(b.cle * v), appoint: arrondi(b.appoint * v), contre: arrondi(b.contre * v) };
}

/* ── le cadre de capture ────────────────────────────────────────────────── */
export const RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"];
export function ratioNombre(r) {
  const m = /^(\d+):(\d+)$/.exec(String(r || ""));
  return m && +m[2] > 0 ? +m[1] / +m[2] : 1;
}

/* le plus grand rectangle au ratio voulu dans la vue (moins une marge), centré, en pixels CSS entiers */
export function cadre(ratio, largeur, hauteur, marge = 0.06) {
  const L = Math.max(1, largeur) * (1 - 2 * marge), H = Math.max(1, hauteur) * (1 - 2 * marge);
  const k = ratioNombre(ratio);
  let w = L, h = L / k;
  if (h > H) { h = H; w = H * k; }
  w = Math.max(1, Math.round(w)); h = Math.max(1, Math.round(h));
  return { x: Math.round((largeur - w) / 2), y: Math.round((hauteur - h) / 2), w, h };
}

/* la taille de l'image capturée : le grand côté vaut `long` px (1536 par défaut, comme le cadre de Sorceress) */
export function tailleCapture(ratio, long = 1536) {
  const k = ratioNombre(ratio);
  return k >= 1 ? { w: long, h: Math.round(long / k) } : { w: Math.round(long * k), h: long };
}

/* ── le modèle d'image ──────────────────────────────────────────────────── */
export const RESOLUTIONS = ["1K", "2K", "4K"];

/* le modèle à présélectionner : le défaut du serveur s'il est dans la liste, sinon le premier. Un modèle sans clé
   reste choisissable (le refus 503 n'arrive qu'au lancement). */
export function modeleParDefaut(liste, defaut) {
  const ids = (liste || []).map((m) => m.id);
  if (defaut && ids.includes(defaut)) return defaut;
  return ids[0] || null;
}

/* la résolution réellement envoyée : celle demandée si le modèle la prend, sinon la première qu'il prend */
export function resolutionPermise(modele, resolution) {
  const r = (modele && modele.resolutions) || ["1K"];
  return r.includes(resolution) ? resolution : r[0];
}

/* ── le rail des références ─────────────────────────────────────────────── */
/* du plus récent au plus ancien ; la référence choisie pour la retexture : celle demandée si elle existe encore,
   sinon la plus récente GÉNÉRÉE (une planche de style téléversée n'est choisie que si on la désigne) */
export function trierRail(refs) {
  return [...(refs || [])].sort((a, b) => String(b.cree_le || "").localeCompare(String(a.cree_le || "")) || String(b.id).localeCompare(String(a.id)));
}
export function referenceChoisie(refs, voulue) {
  const l = trierRail(refs);
  if (voulue && l.some((r) => r.id === voulue)) return voulue;
  const g = l.find((r) => r.sorte === "generee");
  return g ? g.id : null;
}

/* ── les montants ───────────────────────────────────────────────────────── */
export function usd(n, lg = "fr") {
  if (n == null || !Number.isFinite(Number(n))) return "—";
  const v = Number(n);
  const s = v < 0.1 ? v.toFixed(3) : v.toFixed(2);
  return lg === "en" ? "$" + s : s.replace(".", ",") + " $";
}

/* ── t394 : les dispositions de la TEXTURE AUTO (projection multi-vues) ──────────────────────────────────────────
   Relevé de Sorceress (§4 de l'inventaire) : 4 vues (36 cr), 6, 8 en anneau, 10, 12 « détail » (quatre côtés puis
   les moitiés haute et basse zoomées), 16 (pas de 22,5°), 18 « sphère complète » (anneau + plongée + contre-plongée
   + pôles). Chez nous chaque vue est UNE image du modèle d'image choisi : le devis vaut N × le prix d'une image.
   Une pose : azimut et élévation (le repère de la rosace), `zoom` (1 = le modèle entier, 2 = la moitié) et
   `decalage` (la cible monte ou descend de decalage × rayon : les moitiés haute et basse de la disposition 12). */
export const DISPOSITIONS = [4, 6, 8, 10, 12, 16, 18];

const pose = (azimut, elevation, zoom = 1, decalage = 0) => ({ azimut, elevation, zoom, decalage });
const anneau = (n, elevation = 0, depart = 0) => Array.from({ length: n }, (_, i) => pose(arrondi(depart + (360 * i) / n), elevation));
const POLES = [pose(0, ELEVATION_MAX), pose(0, -ELEVATION_MAX)];

export function poses(n) {
  switch (Number(n)) {
    case 4: return anneau(4, 15);
    case 6: return [...anneau(4, 10), ...POLES];
    case 8: return anneau(8, 10);
    case 10: return [...anneau(8, 10), ...POLES];
    case 12: return [...anneau(4, 10), ...anneau(4, 15).map((p) => ({ ...p, zoom: 2, decalage: 0.5 })),
      ...anneau(4, -15).map((p) => ({ ...p, zoom: 2, decalage: -0.5 }))];
    case 16: return anneau(16, 10);
    case 18: return [...anneau(8, 0), ...anneau(4, 45, 45), ...anneau(4, -45, 45), ...POLES];
    default: return [];
  }
}

/* le prix d'UNE image chez un modèle du registre (4K compte double là où le modèle le prend), puis le devis d'une
   disposition : N × ce prix. Le serveur refait ce calcul (POST /devis action « lot ») avant tout envoi. */
export function prixImage(modele, resolution) {
  if (!modele || !Number.isFinite(Number(modele.usd))) return null;
  return Number(modele.usd) * (resolution === "4K" && (modele.resolutions || []).includes("4K") ? 2 : 1);
}
export function devisDisposition(n, modele, resolution) {
  const p = prixImage(modele, resolution);
  const k = poses(n).length;
  return p == null || !k ? null : { vues: k, usd: Math.round(p * k * 1e6) / 1e6 };
}
