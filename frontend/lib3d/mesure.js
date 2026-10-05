/* La MESURE (tâche #89 PR C, plan-etabli T8) — trois règles pures, dans lib3d/ parce qu'elles
   sont générales. Aucune ne connaît three.js : elles prennent des {x, y, z} et rendent des
   nombres, ce qui les rend EXÉCUTABLES au banc dans node. */
"use strict";

/* La distance entre deux points, dans l'unité du modèle. La page la convertit par
   fmtMesure(), seul site qui sache s'il y a une échelle. */
export function distance(a, b) {
  return Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
}

/* Les composantes du segment sur les axes du repère, et sa norme : « combien en x, combien
   en z », pas seulement une diagonale. */
export function composantes(a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
  return { dx, dy, dz, norme: Math.hypot(dx, dy, dz) };
}

/* L'ANGLE ENTRE DEUX FACES, EN DEGRÉS — l'angle DIÈDRE de la matière, pas l'angle entre les
   normales : deux faces coplanaires font 180°, perpendiculaires 90°, face à face 0°. Une
   normale nulle ou absente n'a pas d'angle : `null`, jamais NaN. */
export function angleDeFaces(n1, n2) {
  if (!n1 || !n2) return null;
  const l1 = Math.hypot(n1.x, n1.y, n1.z), l2 = Math.hypot(n2.x, n2.y, n2.z);
  if (!(l1 > 0) || !(l2 > 0)) return null;
  const c = (n1.x * n2.x + n1.y * n2.y + n1.z * n2.z) / (l1 * l2);
  const borne = Math.max(-1, Math.min(1, c));
  return Math.round((180 - (Math.acos(borne) * 180) / Math.PI) * 1e6) / 1e6;
}
