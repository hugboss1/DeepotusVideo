/* Canevas 3D PARTAGÉ du dépôt.
   Il vit ici, et non dans /etabli, parce que la spec §12 écrit d'avance la
   condition de convergence : le jour où le Plateau réclame des gizmos, il
   migre vers CE canevas plutôt que d'en faire naître un second.

   CONTRAT D'HÔTE : le <canvas> passé à creerCanevas() doit recevoir une
   taille CSS explicite (par exemple width:100%;height:100% depuis la feuille
   de la page). C'est ce qu'implique le `updateStyle = false` de setSize() :
   le canevas ne se dimensionne PAS tout seul, il ne fait que lire la taille
   que la mise en page lui donne. Sans règle CSS, clientWidth/clientHeight
   retombent sur les 300x150 par défaut de l'élément. */
"use strict";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

export function creerCanevas(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14161a);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 5000);
  camera.position.set(2.5, 1.8, 3.2);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 2.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.4);
  key.position.set(3, 5, 2);
  scene.add(key);

  /* RÈGLE : toute clé de `api` se déclare ICI, `null` compris — c'est le seul
     endroit lisible où le contrat de forme existe, et s'il cesse d'être
     exhaustif il ne le redeviendra jamais. */
  const api = { renderer, scene, camera, controls, racine: null, gltf: null };

  function redimensionner() {
    const w = canvas.clientWidth || 1, h = canvas.clientHeight || 1;
    /* On compare le TAMPON DE DESSIN (canvas.width/height) à ce que setSize()
       y écrirait, soit floor(pixels CSS × pixelRatio) — et non aux pixels CSS
       eux-mêmes. MESURÉ dans un vrai navigateur avec setPixelRatio(2) : un
       canevas dimensionné en CSS affiche un tampon 800x600 pour un client
       400x300, donc la comparaison naïve reste vraie à CHAQUE image et
       relance setSize() + updateProjectionMatrix() en boucle pour toujours.
       (Le rendu restait correct : c'était du travail redondant, pas un bug
       visuel.) */
    const r = renderer.getPixelRatio();
    if (canvas.width !== Math.floor(w * r) || canvas.height !== Math.floor(h * r)) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
  }
  (function boucle() {
    requestAnimationFrame(boucle);
    redimensionner();
    controls.update();
    renderer.render(scene, camera);
  })();
  return api;
}

/* Un seul chargeur pour toute la page : les décodeurs Draco et meshopt
   coûtent un téléchargement et un pool de workers, inutile de les payer à
   chaque GLB. */
let _loader = null;
function loader() {
  if (_loader) return _loader;
  _loader = new GLTFLoader();
  const draco = new DRACOLoader();
  /* La RACINE du dossier draco, pas le sous-dossier gltf/ : mesuré et
     consigné dans dist/assets/three/VERSION.txt. */
  draco.setDecoderPath("/assets/three/addons/libs/draco/");
  _loader.setDRACOLoader(draco);
  _loader.setMeshoptDecoder(MeshoptDecoder);
  return _loader;
}

/* Libère la mémoire GPU. Charger dix étapes d'un maillage texturé sans
   disposer sature la carte en quelques minutes.
   Libère le MODÈLE, pas le CANEVAS : ce dernier n'a délibérément aucun
   démontage, les deux vues étant mises en cache pour la durée de vie de la
   page — et `enableDamping` exige de toute façon une boucle permanente. */
export function vider(api) {
  if (!api.racine) return;
  api.racine.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    const mats = Array.isArray(o.material) ? o.material : (o.material ? [o.material] : []);
    for (const m of mats) {
      for (const k of Object.keys(m)) {
        const v = m[k];
        if (v && v.isTexture) v.dispose();
      }
      m.dispose();
    }
  });
  api.scene.remove(api.racine);
  api.racine = null;
  /* `gltf` retient `parser`, donc `parser.json`, les ArrayBuffers du GLB
     ENTIER et le cache d'images : le laisser accroché garderait des centaines
     de Mo côté hôte après une libération censée tout rendre. Le mettre à null
     rend du même geste exactes les gardes en `api.gltf` des tâches suivantes,
     qui sinon franchiraient la garde sur une vue vidée pour aller déréférencer
     `api.racine`, nul. */
  api.gltf = null;
}

/* Cadre la caméra sur la boîte englobante. Indispensable : un modèle en
   mètres et un modèle en centimètres donneraient l'un un point, l'autre un
   mur — et deux étapes ne seraient pas comparables à l'œil.
   Le cadrage est DÉLIBÉRÉMENT invariant par aspect : la position ne dépend que
   de la boîte englobante, donc une vue A cadrée en pleine largeur reste cadrée
   à l'identique une fois réduite de moitié à l'ouverture de B — c'est
   précisément ce qui rend A et B comparables. Contrepartie mesurée : un
   canevas plus haut que large (aspect ≈ 0,75) peut rogner d'environ 35 %
   horizontalement ; la marge de 1,35 absorbe le cas courant. La vraie
   correction — tenir compte de l'aspect ET re-cadrer A à l'ouverture de B —
   appartient à la tâche 5, pas ici : un terme en 1/aspect posé seul cadrerait
   A et B à deux distances différentes et casserait la comparaison. */
export function cadrer(api, marge = 1.35) {
  if (!api.racine) return null;
  const boite = new THREE.Box3().setFromObject(api.racine);
  const taille = boite.getSize(new THREE.Vector3());
  const centre = boite.getCenter(new THREE.Vector3());
  const rayon = Math.max(taille.x, taille.y, taille.z) * 0.5 || 1;
  const d = (rayon * marge) / Math.tan((api.camera.fov * Math.PI) / 360);
  api.camera.position.set(centre.x + d * 0.6, centre.y + d * 0.45, centre.z + d);
  api.camera.near = Math.max(d / 1000, 0.001);
  api.camera.far = d * 100;
  api.camera.updateProjectionMatrix();
  api.controls.target.copy(centre);
  api.controls.update();
  return { taille, centre, rayon };
}

/* NON RÉ-ENTRANT — l'appelant doit sérialiser (le verrou appartient à
   ouvrirPrincipale(), tâche 4). Sur deux clics rapides dans la chronologie, le
   second vider() s'exécute pendant que le premier loadAsync est encore en vol,
   puis les DEUX font scene.add() : le perdant reste dans le graphe pour
   toujours, vider() ne retirant que `api.racine`. C'est exactement la fuite
   que cette fonction promet d'empêcher, déclenchée par un double-clic.
   À noter aussi : un loadAsync qui REJETTE laisse le canevas vide, le modèle
   précédent ayant déjà été vidé. */
export async function charger(api, url) {
  vider(api);
  const gltf = await loader().loadAsync(url);
  api.racine = gltf.scene;
  api.gltf = gltf;
  api.scene.add(api.racine);
  const cadre = cadrer(api);
  let tris = 0, maillages = 0;
  api.racine.traverse((o) => {
    if (!o.isMesh || !o.geometry) return;
    maillages++;
    const g = o.geometry;
    tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
  });
  return { tris: Math.round(tris), maillages, ...cadre };
}
