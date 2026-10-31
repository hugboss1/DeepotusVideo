/* t405 (31/10/2026) — la POSE vivante de l'écran Animer : ce que three.js fait des décisions d'animer_calc.js, image
   par image, APRÈS l'AnimationMixer (aperçu gratuit, rien n'est écrit dans le modèle).

   - l'analyse du squelette ouvert : os par rôle (mêmes règles que mouvement_rig.py), chaînes bras / jambes pour l'IK,
     doigts par côté, os à ressort par famille (Jiggle, Hair, Cloth) avec leur queue de repos ;
   - le CLICHÉ de la pose animée (pris après chaque mise à jour du mixer) et sa restauration : l'IK, les doigts et la
     physique se posent chaque image SUR la pose animée, jamais les uns sur les autres ;
   - l'IK à deux os (ikDeuxOs) traduit en rotations : on « vise » chaque os pour amener son enfant au point calculé ;
   - les doigts repliés d'une prise (Gun, Sword) autour de l'axe dessus-de-main × doigt ;
   - les os à ressort (pasRessort) : la queue simulée devient une rotation de l'os.
   Aucun DOM ici : animer.js branche les boutons. */
"use strict";
import * as THREE from "three";
import { osParRole, chaineIK, classerPhysique, doigtsDe, pasRessort, ikDeuxOs, courbureDoigt, ANGLE_DOIGT, axeCourbure,
  FAMILLES } from "./animer_calc.js";

const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);
const arr = (v) => [v.x, v.y, v.z];
export function positionMonde(o) {
  o.updateWorldMatrix(true, false);
  return new THREE.Vector3().setFromMatrixPosition(o.matrixWorld);
}

/* Tourne `os` autour de sa tête pour que le point monde `de` (un de ses descendants) passe en `vers`. */
export function viser(os, de, vers) {
  const tete = positionMonde(os);
  const u = de.clone().sub(tete), v = vers.clone().sub(tete);
  if (u.lengthSq() < 1e-14 || v.lengthSq() < 1e-14) return;
  const dq = new THREE.Quaternion().setFromUnitVectors(u.normalize(), v.normalize());
  tournerMonde(os, dq);
}

/* applique la rotation MONDE `dq` à l'os (sa tête reste en place) */
function tournerMonde(os, dq) {
  const qw = os.getWorldQuaternion(new THREE.Quaternion());
  const qp = os.parent ? os.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
  os.quaternion.copy(qp.invert().multiply(dq.clone().multiply(qw))).normalize();
  os.updateMatrixWorld(true);
}

function profondeur(o) {
  let d = 0;
  for (let p = o.parent; p; p = p.parent) d++;
  return d;
}

/* Le squelette du modèle ouvert, lu UNE fois au chargement (pose de liaison). */
export function analyser(racine) {
  const os = [];
  racine.traverse((o) => { if (o.isBone && !os.includes(o)) os.push(o); });
  const liste = os.map((o) => ({ nom: o.name, profondeur: profondeur(o) }));
  const roles = osParRole(liste);
  const ch = (m, c) => { const ids = chaineIK(roles, m, c); return ids ? ids.map((i) => os[i]) : null; };
  const chaines = { bras_g: ch("bras", "g"), bras_d: ch("bras", "d"), jambe_g: ch("jambe", "g"), jambe_d: ch("jambe", "d") };
  const noms = os.map((o) => o.name);
  const fam = classerPhysique(noms);
  racine.updateMatrixWorld(true);
  const ressorts = [];
  for (const f of FAMILLES) {
    for (const i of fam[f]) {
      const b = os[i];
      const enfant = b.children.find((c) => c.isBone);
      let queue = null;
      if (enfant) queue = enfant.position.clone();
      else if (b.parent && b.parent.isBone) {            // un bout de chaîne : il prolonge son parent
        const t = positionMonde(b), p = positionMonde(b.parent);
        queue = b.worldToLocal(t.clone().add(t.clone().sub(p).multiplyScalar(0.6)));
      }
      if (!queue || queue.lengthSq() < 1e-14) continue;
      ressorts.push({ os: b, famille: f, queueLocale: queue, etat: null, profondeur: liste[i].profondeur });
    }
  }
  ressorts.sort((a, b) => a.profondeur - b.profondeur);
  const parProf = (ids) => ids.map((i) => os[i]).sort((a, b) => profondeur(a) - profondeur(b));
  const doigts = { g: parProf(doigtsDe(noms, "g")), d: parProf(doigtsDe(noms, "d")) };
  const main = { g: chaines.bras_g ? chaines.bras_g[2] : null, d: chaines.bras_d ? chaines.bras_d[2] : null };
  /* le DESSUS de chaque main : le haut du monde en pose de liaison, gardé dans le repère de la main */
  const hautMain = {};
  for (const c of ["g", "d"]) {
    if (main[c]) hautMain[c] = new THREE.Vector3(0, 1, 0).applyQuaternion(main[c].getWorldQuaternion(new THREE.Quaternion()).invert());
  }
  const familles = Object.fromEntries(FAMILLES.map((f) => [f, ressorts.filter((r) => r.famille === f).map((r) => r.os.name)]));
  return { os, roles, chaines, ressorts, doigts, main, hautMain, familles };
}

export const cliche = (squ) => squ.os.map((o) => [o.position.clone(), o.quaternion.clone(), o.scale.clone()]);
export function restaurer(squ, c) {
  if (!squ || !c) return;
  squ.os.forEach((o, i) => { const x = c[i]; if (x) { o.position.copy(x[0]); o.quaternion.copy(x[1]); o.scale.copy(x[2]); } });
}

/* IK à deux os sur une chaîne [os 1, os 2, bout] vers `cible` (monde) ; `pole` (monde) oriente le pli d'un membre
   droit. Rend le résultat d'ikDeuxOs (atteint ou non). */
export function resoudreMembre(chaine, cible, pole) {
  const [b1, b2, b3] = chaine;
  const a = positionMonde(b1), b = positionMonde(b2), c = positionMonde(b3);
  const r = ikDeuxOs(arr(a), arr(b), arr(c), arr(cible), arr(pole));
  viser(b1, b, V(r.coude));
  viser(b2, positionMonde(b3), V(r.bout));
  return r;
}

/* Les doigts d'une main repliés selon la prise `p` (courbure par doigt), phalange après phalange. */
export function courberDoigts(squ, cote, p) {
  const main = squ.main[cote];
  if (!main || !squ.hautMain[cote]) return 0;
  const haut = squ.hautMain[cote].clone().applyQuaternion(main.getWorldQuaternion(new THREE.Quaternion()));
  let n = 0;
  for (const d of squ.doigts[cote]) {
    const enfant = d.children.find((c) => c.isBone);
    if (!enfant) continue;
    const f = positionMonde(enfant).sub(positionMonde(d));
    const axe = V(axeCourbure(arr(f), arr(haut)));
    const ang = courbureDoigt(d.name, p) * ANGLE_DOIGT * Math.PI / 180;
    if (axe.lengthSq() < 1e-9 || !ang) continue;
    tournerMonde(d, new THREE.Quaternion().setFromAxisAngle(axe, ang));
    n++;
  }
  return n;
}

/* Un pas de physique sur les os à ressort des familles actives (parents d'abord). */
export function pasPhysique(squ, actifs, reglages, dt) {
  for (const s of squ.ressorts) {
    if (!actifs[s.famille]) { s.etat = null; continue; }
    const b = s.os;
    b.updateWorldMatrix(true, false);
    const tete = new THREE.Vector3().setFromMatrixPosition(b.matrixWorld);
    const cible = s.queueLocale.clone().applyMatrix4(b.matrixWorld);
    s.etat = pasRessort(s.etat, arr(tete), arr(cible), reglages, dt);
    viser(b, cible, V(s.etat.queue));
  }
}

export const remettreRessorts = (squ) => { if (squ) for (const s of squ.ressorts) s.etat = null; };
