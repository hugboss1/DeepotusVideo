/* LES SURPLOMBS — deux règles pures et un calque, dans lib3d/ parce que la
   question « cette face pend-elle dans le vide ? » n'a rien de propre à
   l'Établi (tâche T091, plan-etabli T16).

   LA CONVENTION EST CELLE DES SLICERS, et elle se lit à l'envers de l'intuition
   la première fois : la pente est mesurée DEPUIS L'HORIZONTALE, si bien que 90°
   est un mur vertical (qui s'imprime tout seul) et 0° un plafond plat (le pire
   cas). C'est le mot de la base de connaissance Prusa (« measured from the
   horizontal plane », vérifié le 05/10/2026). Un seuil de 45° veut donc dire :
   « peins ce qui est SOUS 45° ». */
import * as THREE from "three";

/* La pente d'une face, en degrés depuis l'horizontale — ou `null` quand la
   face regarde vers le haut (une face tournée vers le ciel n'a jamais besoin
   de support) ou que la normale est nulle. */
export function penteDepuisHorizontale(n, haut) {
  const ln = Math.hypot(n.x, n.y, n.z), lh = Math.hypot(haut.x, haut.y, haut.z);
  if (!(ln > 0) || !(lh > 0)) return null;
  const d = -(n.x * haut.x + n.y * haut.y + n.z * haut.z) / (ln * lh);
  /* d < 0 : la face regarde vers le haut. d = 0 est un MUR, et il vaut 90 —
     le dessin du plan le rendait null, son propre banc attendait 90. */
  if (!(d >= 0)) return null;
  const borne = Math.min(1, d);
  return Math.round(((Math.acos(borne) * 180) / Math.PI) * 1e6) / 1e6;
}

/* SOUS le seuil, strictement : à 45° pile, la face tient — c'est la borne que
   les slicers appellent « imprimable sans support ». */
export function estSurplomb(n, haut, seuilDeg) {
  const p = penteDepuisHorizontale(n, haut);
  return p !== null && p < seuilDeg;
}

/* Le CALQUE : un maillage translucide posé sur les seuls triangles en
   surplomb, dans le monde. Même mécanique que l'aperçu du couteau (des objets
   ajoutés à la scène, retirés au rangement) — jamais une couleur écrite dans
   le matériau de l'utilisateur, qui est PARTAGÉ entre pièces (la leçon des
   teintes de la plaque : la dernière parcourue gagne, et la couleur fuit).
   Un seuil ≤ 0 range le calque et rend null. */
const _calques = new WeakMap();
export function peindreSurplombs(api, seuilDeg, haut) {
  if (!api) return null;
  const ancien = _calques.get(api);
  if (ancien) {
    api.scene.remove(ancien);
    ancien.geometry.dispose();
    ancien.material.dispose();
    _calques.delete(api);
  }
  if (!(seuilDeg > 0) || !api.racine) return null;
  api.racine.updateMatrixWorld(true);
  const points = [];
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  const u = new THREE.Vector3(), v = new THREE.Vector3(), n = new THREE.Vector3();
  let vus = 0;
  api.racine.traverse((o) => {
    if (!o.isMesh || !o.geometry || !o.visible) return;
    const g = o.geometry, pos = g.attributes && g.attributes.position;
    if (!pos) return;
    const idx = g.index;
    const nb = idx ? idx.count : pos.count;
    for (let k = 0; k + 2 < nb; k += 3) {
      const i0 = idx ? idx.getX(k) : k;
      const i1 = idx ? idx.getX(k + 1) : k + 1;
      const i2 = idx ? idx.getX(k + 2) : k + 2;
      a.fromBufferAttribute(pos, i0).applyMatrix4(o.matrixWorld);
      b.fromBufferAttribute(pos, i1).applyMatrix4(o.matrixWorld);
      c.fromBufferAttribute(pos, i2).applyMatrix4(o.matrixWorld);
      u.subVectors(b, a); v.subVectors(c, a); n.crossVectors(u, v);
      vus++;
      if (!estSurplomb(n, haut, seuilDeg)) continue;
      points.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
    }
  });
  if (!points.length) return { triangles: 0, vus };
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  const calque = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
    color: 0xe08a2e, transparent: true, opacity: 0.75, side: THREE.DoubleSide,
    depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  calque.name = "surplombs";
  api.scene.add(calque);
  _calques.set(api, calque);
  return { triangles: points.length / 9, vus };
}
