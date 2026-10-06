/* LE RIG, REGARDÉ (tâche T093, plan etabli-p4-p5 tâches 1 à 3). Ce module ne
   parle à aucune route et n'écrit rien : il montre le squelette, les poids et la
   déformation pour qu'on juge un rig AVANT de payer les animations qui
   l'utilisent. Créer des clips (U1) et repeindre les poids (U2) sont des phases
   ultérieures documentées — rien n'en est anticipé ici.

   Deux règles PURES en tête (l'arbre des os, la couleur d'un poids) : elles
   s'exécutent au banc sous node, sans three.js. */
"use strict";
import * as THREE from "three";

/* L'ARBRE DES OS, lu dans l'inventaire du serveur (`rig_inventory`), dans
   l'ordre d'un parcours en profondeur. LE CONTRAT de l'inventaire est respecté :
   `os[].parent` peut désigner un nœud ABSENT de la liste — la racine d'armature
   des exports Blender et Mixamo, qui n'est pas un os. Un parent introuvable fait
   donc une RACINE. Un cycle (fichier abîmé) ne boucle pas : chaque os n'est vu
   qu'une fois. */
export function arbreDesOs(os) {
  const parIndex = new Map(os.map((o) => [o.index, o]));
  const enfants = new Map();
  const racines = [];
  for (const o of os) {
    if (o.parent === null || o.parent === undefined || !parIndex.has(o.parent)) racines.push(o);
    else {
      if (!enfants.has(o.parent)) enfants.set(o.parent, []);
      enfants.get(o.parent).push(o);
    }
  }
  const sortie = [], vus = new Set();
  const visiter = (o, profondeur) => {
    if (vus.has(o.index)) return;
    vus.add(o.index);
    sortie.push({ index: o.index, nom: o.nom, profondeur });
    for (const e of enfants.get(o.index) || []) visiter(e, profondeur + 1);
  };
  for (const r of racines) visiter(r, 0);
  for (const o of os) visiter(o, 0);          /* ce qu'un cycle aurait laissé de côté */
  return sortie;
}

/* La COULEUR d'un poids : bleu = l'os n'influence pas ce sommet, rouge = il le
   tient seul. `indices` et `poids` sont les tableaux à plat de JOINTS_0 et
   WEIGHTS_0 (quatre par sommet) — un sommet peut citer le même os deux fois,
   d'où la SOMME, bornée à 1. */
export function couleursDePoids(indices, poids, n, idxOs) {
  const cols = new Float32Array(n * 3);
  for (let v = 0; v < n; v++) {
    let p = 0;
    for (let k = 0; k < 4; k++) if (indices[v * 4 + k] === idxOs) p += poids[v * 4 + k];
    p = Math.min(Math.max(p, 0), 1);
    cols[v * 3] = p;
    cols[v * 3 + 1] = 0.15;
    cols[v * 3 + 2] = 1 - p;
  }
  return cols;
}

const _peaux = (api) => {
  const p = [];
  if (api && api.racine) api.racine.traverse((o) => { if (o.isSkinnedMesh) p.push(o); });
  return p;
};

/* Le SQUELETTE, dessiné À TRAVERS la peau (depthTest coupé), dans la scène —
   jamais dans le modèle, que vider() libère au chargement suivant. */
export function poserSquelette(api) {
  retirerSquelette(api);
  const peaux = _peaux(api);
  if (!peaux.length) return { aSquelette: false, peaux };
  const aides = [];
  for (const p of peaux) {
    /* Une peau déformée sort de sa boîte d'origine : sans ceci three.js la
       retirerait de l'image au premier pli d'un bras hors champ. */
    p.frustumCulled = false;
    const aide = new THREE.SkeletonHelper(p.skeleton.bones[0] || p);
    aide.material.depthTest = false;
    aide.material.transparent = true;
    aide.renderOrder = 999;
    api.scene.add(aide);
    aides.push(aide);
  }
  api._aidesRig = aides;
  return { aSquelette: true, peaux };
}

export function retirerSquelette(api) {
  if (!api) return;
  for (const a of [...(api._aidesRig || []), ...(api._aideChaine ? [api._aideChaine] : [])]) {
    api.scene.remove(a);
    if (a.dispose) a.dispose();
  }
  api._aidesRig = [];
  api._aideChaine = null;
}

/* La CHAÎNE d'un os : l'os choisi et toute sa descendance, dessinés par-dessus
   en jaune, le reste du squelette éteint. Rend les noms de la chaîne. */
export function surlignerChaine(api, nomOs) {
  if (api._aideChaine) { api.scene.remove(api._aideChaine); api._aideChaine.dispose?.(); api._aideChaine = null; }
  for (const aide of api._aidesRig || []) aide.material.opacity = nomOs ? 0.25 : 1;
  let cible = null;
  if (nomOs) api.racine.traverse((o) => { if (o.isBone && o.name === nomOs && !cible) cible = o; });
  if (!cible) return [];
  const aide = new THREE.SkeletonHelper(cible);
  aide.material.depthTest = false;
  aide.material.transparent = true;
  aide.material.vertexColors = false;
  aide.material.color.set(0xf2c14e);
  aide.renderOrder = 1000;
  api.scene.add(aide);
  api._aideChaine = aide;
  const chaine = [];
  cible.traverse((b) => { if (b.isBone) chaine.push(b.name); });
  return chaine;
}

/* LES POIDS en couleurs de sommets, sur un matériau CLONÉ : peindre l'original
   abîmerait le modèle affiché, et la couleur survivrait au changement d'os.
   Rend le nombre de sommets que l'os influence. */
export function peindrePoids(api, nomOs) {
  let touches = 0;
  for (const o of _peaux(api)) {
    const idxOs = o.skeleton.bones.findIndex((b) => b.name === nomOs);
    const g = o.geometry, si = g.attributes.skinIndex, sw = g.attributes.skinWeight;
    if (!si || !sw) continue;
    const cols = couleursDePoids(si.array, sw.array, si.count, idxOs);
    for (let v = 0; v < si.count; v++) if (cols[v * 3] > 0) touches++;
    g.setAttribute("color", new THREE.BufferAttribute(cols, 3));
    if (!o.userData.matOrigine) o.userData.matOrigine = o.material;
    const m = (Array.isArray(o.userData.matOrigine) ? o.userData.matOrigine[0] : o.userData.matOrigine).clone();
    m.vertexColors = true;
    m.map = null;
    m.needsUpdate = true;
    if (o.material !== o.userData.matOrigine && o.material.dispose) o.material.dispose();
    o.material = m;
  }
  return touches;
}

export function retirerPoids(api) {
  for (const o of _peaux(api)) {
    if (!o.userData.matOrigine) continue;
    if (o.material.dispose) o.material.dispose();
    o.material = o.userData.matOrigine;
    o.userData.matOrigine = null;
    o.geometry.deleteAttribute("color");
  }
}

/* LA POSE D'ESSAI. Le repos est mémorisé AVANT toute rotation — sans lui,
   « remettre » serait impossible. Une rotation est RELATIVE au repos (en
   degrés, autour des axes locaux de l'os) : on lit l'écart à la pose du
   fichier, pas une pose absolue. Rien n'est écrit. */
export function memoriserRepos(api) {
  const repos = new Map();
  if (api && api.racine) api.racine.traverse((o) => { if (o.isBone) repos.set(o.uuid, o.quaternion.clone()); });
  api._poseRepos = repos;
  return repos.size;
}

export function remettreRepos(api) {
  arreterClip(api);
  if (!api._poseRepos) return;
  api.racine.traverse((o) => {
    const q = api._poseRepos.get(o.uuid);
    if (q) o.quaternion.copy(q);
  });
}

export function tournerOs(api, nomOs, degX, degY, degZ) {
  if (!api._poseRepos) memoriserRepos(api);
  arreterClip(api);
  const d = THREE.MathUtils.degToRad;
  let fait = false;
  api.racine.traverse((o) => {
    if (fait || !o.isBone || o.name !== nomOs) return;
    const repos = api._poseRepos.get(o.uuid) || o.quaternion.clone();
    const delta = new THREE.Quaternion().setFromEuler(new THREE.Euler(d(degX || 0), d(degY || 0), d(degZ || 0)));
    o.quaternion.copy(repos).multiply(delta);
    fait = true;
  });
  return fait;
}

/* LES CLIPS livrés avec le fichier : les juger au lieu de les deviner. UN
   mixeur par modèle, UNE boucle pour le module — la version du plan lançait une
   boucle d'animation de plus à chaque rendu du panneau, qui ne s'arrêtait jamais. */
const _actifs = new Set();
let _boucle = false;
let _avant = 0;
function _demarrer() {
  if (_boucle) return;
  _boucle = true;
  _avant = performance.now();
  /* performance.now() et non THREE.Clock, déprécié en r185 (avertissement à
     chaque chargement, mesuré sous node le 06/10). */
  (function tic() {
    requestAnimationFrame(tic);
    const t = performance.now(), dt = Math.min(0.1, (t - _avant) / 1000);
    _avant = t;
    for (const api of _actifs) if (api._mixeur) api._mixeur.update(dt);
  })();
}

export function lecteurClips(api) {
  arreterClip(api);
  const clips = (api.gltf && api.gltf.animations) || [];
  api._mixeur = clips.length ? new THREE.AnimationMixer(api.racine) : null;
  api._clips = clips;
  if (clips.length) { _actifs.add(api); _demarrer(); }
  return clips.map((c, i) => ({ i, nom: c.name || `clip_${i}`, duree: Number(c.duration.toFixed(2)) }));
}

export function jouerClip(api, i, vitesse) {
  if (!api._mixeur || !api._clips[i]) return false;
  api._mixeur.stopAllAction();
  api._mixeur.timeScale = Number(vitesse) > 0 ? Number(vitesse) : 1;
  api._mixeur.clipAction(api._clips[i]).reset().play();
  return true;
}

export function vitesseClip(api, vitesse) {
  if (api._mixeur && Number(vitesse) > 0) api._mixeur.timeScale = Number(vitesse);
}

export function arreterClip(api) {
  if (api && api._mixeur) api._mixeur.stopAllAction();
}

/* Tout ranger au changement de modèle : les aides vivent dans la SCÈNE, le
   mixeur tient le modèle sortant. */
export function rangerRig(api) {
  if (!api) return;
  retirerSquelette(api);
  arreterClip(api);
  _actifs.delete(api);
  api._mixeur = null;
  api._clips = [];
  api._poseRepos = null;
}
