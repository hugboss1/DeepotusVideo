/* t344 (29/10/2026) — le RENDU partagé du 3D Studio : Texturé / Argile / Fil de fer, et la mise à l'échelle commune.
   Servi au banc « Comparer les moteurs » (comparer.js) et à l'aperçu agrandi du graphe (graphe_vues.js). Les matières
   d'origine sont gardées sur chaque maillage (userData.dzMatOrigine) : revenir à « Texturé » ne recharge rien. */
"use strict";
import * as THREE from "three";

export const ARGILE = new THREE.MeshStandardMaterial({ color: 0xb9b2a6, roughness: 0.9, metalness: 0 });
export const FIL = new THREE.MeshBasicMaterial({ color: 0x9fc3e8, wireframe: true });

export function appliquerRendu(racine, mode) {
  if (!racine) return;
  racine.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.userData.dzMatOrigine) o.userData.dzMatOrigine = o.material;
    o.material = mode === "argile" ? ARGILE : mode === "fil" ? FIL : o.userData.dzMatOrigine;
  });
}

/* ramène le modèle à une boîte de 1 posée au sol, centrée : une même pose de caméra vaut pour tous les modèles */
export function normaliser(racine) {
  racine.scale.setScalar(1);
  racine.position.set(0, 0, 0);
  racine.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(racine), t = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3());
  const s = 1 / (Math.max(t.x, t.y, t.z) || 1);
  racine.scale.setScalar(s);
  racine.position.set(-c.x * s, -b.min.y * s, -c.z * s);
  racine.updateMatrixWorld(true);
}
