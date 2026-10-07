/* Plateau 3D — le calcul PUR de l'écran (t127, 07/10/2026).
   Le MÊME calcul que backend/app/services/scene3d.py, pour ce que l'écran doit faire à chaque image sans aller-retour
   (lire l'orbite de la caméra, convertir focale ↔ champ, interpoler les keyframes pendant la lecture). Les MESURES
   (h, shot_type, mouvement) restent au serveur : une seule autorité. Le banc tests/test_plateau_ecran.py exécute ce
   module sous node et le compare à scene3d.py sur des cas tirés — un désaccord fait rougir.
   Conventions de la spec (orbite <model-viewer>) : θ autour de +Y depuis +Z, φ depuis +Y, r en mètres, fov vertical. */
"use strict";

export const EASINGS = ["linear", "ease-in", "ease-out", "ease-in-out"];
export const ASPECTS = { "16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1, "2.39:1": 2.39 };
const RAD = Math.PI / 180;

export function fovDeFocale(focaleMm, capteurMm = 14.2) {
  const f = Number(focaleMm), c = Number(capteurMm);
  if (!(f > 0) || !(c > 0)) throw new Error("focale ou capteur hors bornes");
  return 2 * Math.atan(c / (2 * f)) / RAD;
}
export function focaleDeFov(fovDeg, capteurMm = 14.2) {
  const a = Number(fovDeg), c = Number(capteurMm);
  if (!(a > 0) || !(a < 180) || !(c > 0)) throw new Error("fov ou capteur hors bornes");
  return c / (2 * Math.tan(a * RAD / 2));
}
export function positionCamera(orbit, target) {
  const [th, ph, r] = orbit.map(Number), t = th * RAD, p = ph * RAD;
  return [target[0] + r * Math.sin(p) * Math.sin(t), target[1] + r * Math.cos(p), target[2] + r * Math.sin(p) * Math.cos(t)];
}
/* l'orbite d'une caméra posée en `pos` qui regarde `target` — l'inverse de positionCamera. `thetaPres` (facultatif) :
   l'angle qu'on veut prolonger, pour qu'une orbite qui a dépassé 180° ne retombe pas à −180° (une orbite de 360° doit
   pouvoir s'écrire 0 → 360, comme l'interpole le serveur). */
export function orbitDeCamera(pos, target, thetaPres) {
  const d = [pos[0] - target[0], pos[1] - target[1], pos[2] - target[2]];
  const r = Math.hypot(d[0], d[1], d[2]);
  if (!(r > 1e-9)) throw new Error("caméra confondue avec sa cible");
  let th = Math.atan2(d[0], d[2]) / RAD;
  const ph = Math.acos(Math.max(-1, Math.min(1, d[1] / r))) / RAD;
  if (Number.isFinite(thetaPres)) th += 360 * Math.round((thetaPres - th) / 360);
  return [th, ph, r];
}
export function ease(u, nom) {
  if (nom === "ease-in") return u * u;
  if (nom === "ease-out") return 1 - (1 - u) * (1 - u);
  if (nom === "ease-in-out") return u * u * (3 - 2 * u);
  return u;
}
export function interpoler(kfs, t) {
  if (!Array.isArray(kfs) || !kfs.length) throw new Error("au moins un keyframe");
  const fige = (k) => ({ orbit: k.orbit.slice(), target: k.target.slice(), fov: k.fov });
  if (kfs.length === 1 || t <= kfs[0].t) return fige(kfs[0]);
  if (t >= kfs[kfs.length - 1].t) return fige(kfs[kfs.length - 1]);
  for (let i = 0; i < kfs.length - 1; i++) {
    const a = kfs[i], b = kfs[i + 1];
    if (a.t <= t && t <= b.t) {
      const u = ease((t - a.t) / (b.t - a.t), a.easing || "ease-in-out"), l = (x, y) => x + (y - x) * u;
      return { orbit: a.orbit.map((v, j) => l(v, b.orbit[j])), target: a.target.map((v, j) => l(v, b.target[j])), fov: l(a.fov, b.fov) };
    }
  }
  return fige(kfs[kfs.length - 1]);
}
/* le plus grand rectangle au ratio `aspect` dans (w, h) — le cadre EST l'élément (spec §3.1), jamais un dessin */
export function cadreDans(w, h, aspect) {
  const W = Math.max(0, w), H = Math.max(0, h);
  return W / H > aspect ? { w: Math.round(H * aspect), h: Math.round(H) } : { w: Math.round(W), h: Math.round(W / aspect) };
}
/* les presets de mouvement (spec §7) : deux keyframes depuis l'état courant, sur `duree` secondes */
export function preset(nom, cam, duree) {
  const a = { t: 0, orbit: cam.orbit.slice(), target: cam.target.slice(), fov: cam.fov, easing: "ease-in-out" };
  const b = { t: duree, orbit: cam.orbit.slice(), target: cam.target.slice(), fov: cam.fov, easing: "ease-in-out" };
  if (nom === "travelling") b.orbit[2] = Math.max(0.3, a.orbit[2] * 0.4);
  else if (nom === "orbite90") b.orbit[0] = a.orbit[0] + 90;
  else if (nom === "grue") { a.orbit[1] = 50; b.orbit[1] = 88; }
  else if (nom !== "fixe") throw new Error("preset inconnu");
  return nom === "fixe" ? [a] : [a, b];
}
export function trianglesProxy(forme) {
  /* le nombre de triangles des géométries three de l'écran (segments fixés dans plateau.js) — pour le total
     affiché AVANT de composer ; le GLB composé utilise les primitives du serveur, son rapport fait foi */
  return { boite: 12, sphere: 2 * 24 * 16 - 2 * 24, cylindre: 4 * 24, capsule: 2 * 24 * (2 * 8 + 1) }[forme] || 0;
}
