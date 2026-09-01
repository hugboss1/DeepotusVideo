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
  /* LES DEUX CAMÉRAS NAISSENT ENSEMBLE. Fabriquée en cours de route,
     l'orthographique arriverait APRÈS les trois objets qui retiennent une
     référence de caméra (OrbitControls, le gizmo, la synchronisation A/B) et
     qu'il faudrait alors penser à prévenir. Elle coûte une matrice.
     Le cadre (-1, 1, 1, -1) est une amorce : cadrer() le réécrit au premier
     modèle, redimensionner() en refait la largeur à chaque taille. */
  const cameraOrtho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 5000);
  cameraOrtho.position.copy(camera.position);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 2.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.4);
  key.position.set(3, 5, 2);
  scene.add(key);

  /* RÈGLE : toute clé de `api` se déclare ICI, `null` compris — c'est le seul
     endroit lisible où le contrat de forme existe, et s'il cesse d'être
     exhaustif il ne le redeviendra jamais.

     `camera` est la caméra ACTIVE — celle que la boucle rend, celle que le
     gizmo pique, celle que cadrer() pose. Elle POINTE sur l'une des deux
     suivantes et n'est jamais un troisième objet : au départ `api.camera ===
     api.cameraPerspective`, et projeter() la fait basculer. `projection` dit en
     toutes lettres laquelle est active — un lecteur ne doit pas avoir à le
     déduire d'un `isOrthographicCamera`.

     `vueCadrage` NE DIT PAS OÙ LA CAMÉRA REGARDE — son nom porte la nuance,
     l'ancien (`vue`) promettait l'inverse. C'est le nom du DERNIER CADRAGE :
     orienter() seul l'écrit, donc une orbite à la souris le laisse à « face »
     quand la caméra a tourné depuis longtemps. Il sert au recadrage, qui doit
     reprendre la MÊME direction, et au liseré du bouton pressé. Il ne dit PAS
     les axes écran : la seule source vraie en est `camera.matrixWorld`, et
     `orientationDe(api.vueCadrage).haut` serait faux dès la première orbite. */
  const api = { renderer, scene, camera, controls, racine: null, gltf: null,
                cameraPerspective: camera, cameraOrthographique: cameraOrtho,
                projection: "perspective", vueCadrage: "libre" };

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
      /* LES DEUX CAMÉRAS, et jamais `api.camera` seule : celle qui dort doit
         retrouver le bon cadre à l'instant où on bascule dessus, sans quoi le
         premier clic sur « Isométrique » après un redimensionnement rendrait
         un modèle étiré.
         L'aspect d'une ortho vit dans left/right (voir cadreOrtho) : lui écrire
         un `.aspect` ne lève rien et ne fait rien. On refait donc ses bords, à
         demi-hauteur CONSTANTE — top/bottom sont la mémoire du cadrage, et un
         redimensionnement n'a pas à y toucher. */
      api.cameraPerspective.aspect = w / h;
      api.cameraPerspective.updateProjectionMatrix();
      const o = api.cameraOrthographique;
      poserCadreOrtho(o, (o.top - o.bottom) / 2, w / h);
    }
  }
  (function boucle() {
    requestAnimationFrame(boucle);
    redimensionner();
    controls.update();
    /* LA GRADUATION EST DANS LA BOUCLE, et il le faut : le pas se déduit de
       l'ÉTENDUE VISIBLE, qui change à chaque molette et à chaque orbite. Posé
       une fois au cadrage, il deviendrait une trame trop fine au premier
       dézoom et un quadrillage de deux lignes au premier zoom — une règle
       qu'on cesse de pouvoir lire est une règle absente.
       Ce que chaque image paie est une poignée d'opérations flottantes :
       majRepere() ne RECONSTRUIT la géométrie que lorsque le pas ou le nombre
       de cases change, ce qui n'arrive qu'en franchissant un palier 1-2-5. Un
       banc compte les reconstructions et en trouve UNE pour trois appels au
       même zoom. */
    majRepere(api);
    /* `api.camera` et NON la variable `camera` de la fermeture : celle-ci
       reste la perspective pour toujours, et la boucle rendrait donc la
       perspective quoi qu'ait fait projeter() — une bascule sans effet, sans
       erreur, et sans banc rouge. */
    renderer.render(scene, api.camera);
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

/* La caméra est posée sur une direction FIXE, en fractions de `d`. Elle est
   déclarée ICI, et non écrite à la main dans position.set(), parce que les
   seuils de cadrage ci-dessous s'en DÉDUISENT : les deux ne peuvent donc plus
   diverger en silence — un 0,6 changé sans son seuil rendrait la garde
   anti-rognage fausse sans rien casser de visible. */
const DIR = { x: 0.6, y: 0.45, z: 1 };
const NORME_DIR = Math.hypot(DIR.x, DIR.y, DIR.z);          // 1,25

/* ── LE POINT DE VUE : cinq orientations, deux projections ──────────────────

   Les orientations NOMMÉES. `dir` est la direction où se POSE la caméra
   depuis le centre — elle regarde donc vers −dir — et `haut` la référence de
   « haut d'écran » dont la géométrie de cadrage a besoin.

   `haut` N'EST JAMAIS ÉCRIT DANS `camera.up`, ET C'EST UN PIÈGE MESURÉ.
   OrbitControls fige son repère à la CONSTRUCTION : ligne 406 du fichier
   vendorisé, `this._quat = new Quaternion().setFromUnitVectors(object.up,
   new Vector3(0, 1, 0))`, et update() ne le recalcule JAMAIS. Écrire
   `camera.up` après coup laisserait donc l'orbite tourner dans l'ANCIEN
   repère : le modèle pivoterait de travers sous la souris, sans erreur, sans
   console, sans banc rouge. `up` reste (0, 1, 0) pour la vie de la page, et un
   banc interdit à ce fichier de l'écrire.

   D'OÙ VIENT ALORS LE (0, 0, −1) DE « DESSUS » ? De la sécurité de pôle de
   three.js, et il est mesuré, pas supposé. Posée exactement au-dessus du
   centre, la caméra a une colatitude nulle ; `Spherical.setFromVector3` rend
   theta = atan2(0, 0) = 0 et `makeSafe()` relève phi à EPS = 1e-6, si bien que
   le décalage repart vers +Z. `lookAt` avec up = (0, 1, 0) rend alors la base
   (droite = +X, haut d'écran = −Z) : c'est exactement ce que décrit
   `haut: (0, 0, −1)`. Un banc le refait par un second chemin — lookAt
   reconstruit à la main — plutôt que de nous croire sur parole. Y poser
   (0, 1, 0), parallèle à `dir`, ferait un produit vectoriel NUL, donc une
   division par zéro, donc un NaN dans le cadre : écran noir, zéro erreur.

   PAS DE « DERRIÈRE », PAS DE « DESSOUS » : les faces opposées s'atteignent
   d'un demi-tour à la souris, et six boutons dans un coin de canevas se lisent
   moins bien que quatre.

   CE SONT LES AXES DU MODÈLE, et rien d'autre — ceux-là mêmes que le serveur
   nomme dans `axe_haut`. Ce module ne connaît aucun étalement et n'a pas à en
   connaître : à la page qui étale de dire, si elle le veut, laquelle de ces
   trois vues tombe en face de son plan. */
const HAUT_Y = { x: 0, y: 1, z: 0 };
const ORIENTATIONS = {
  /* « libre » EST la vue historique, au chiffre près : c'est elle que la
     tâche 3 a mesurée et dont le seuil 0,813 est sorti. */
  libre:  { dir: DIR,                   haut: HAUT_Y },
  /* ISOMÉTRIQUE au sens strict : (1, 1, 1) est la seule direction où les trois
     axes se projettent à la même longueur. La direction historique
     (0,6 · 0,45 · 1) est un trois-quarts, pas une isométrie — les confondre
     rendrait le mot faux sur le bouton. */
  iso:    { dir: { x: 1, y: 1, z: 1 },  haut: HAUT_Y },
  face:   { dir: { x: 0, y: 0, z: 1 },  haut: HAUT_Y },
  dessus: { dir: { x: 0, y: 1, z: 0 },  haut: { x: 0, y: 0, z: -1 } },
  profil: { dir: { x: 1, y: 0, z: 0 },  haut: HAUT_Y },
};

/* PURE — et c'est ce qui la rend mesurable hors navigateur : elle ne rend que
   des {x, y, z}. Un nom inconnu retombe sur la vue libre plutôt que de rendre
   `undefined`, qui ferait sauter cadrer() sur une lecture de `.dir`. */
export function orientationDe(nom) {
  return ORIENTATIONS[nom] || ORIENTATIONS.libre;
}

/* PURE. La demi-largeur projetée du PIRE cas — le cube de côté 2·rayon — en
   unités de rayon, pour une direction de vue et un haut d'écran donnés.

   Dérivation : la caméra regarde le centre depuis `dir`, donc son axe z vaut
   `dir` normalisée et son axe droit normalize(haut × zcam). La demi-largeur
   projetée d'une boîte de demi-côtés (hx, hy, hz) vaut Σ hi·|ri|, donc au plus
   rayon·(|rx| + |ry| + |rz|) pour le cube.

   GÉNÉRALISE la constante que la tâche 3 avait calculée à la main pour DIR
   seule, (DIR.x + DIR.z)/hypot(DIR.x, DIR.z) = 1,372 : un banc vérifie que
   cette fonction rend le MÊME nombre par ce chemin-ci, à 1e-15. Il fallait la
   généraliser, parce que le pire cas DÉPEND DE LA DIRECTION, et pas qu'un peu.
   MESURÉ : 1,371989 en vue libre, 1,414214 (√2) en isométrique, 1,000000 sur
   les trois vues d'axe. Le figer à 1,372 aurait rogné l'isométrie de 3,1 % en
   largeur sous le seuil et reculé les vues d'axe de 37 % pour rien.
   NE PAS CONFONDRE avec le triplet de cadrageDe (1,4269 / 1,6330 / 1,0000) :
   celui-là est la demi-HAUTEUR du même pire cas, et les deux se ressemblent
   assez pour être pris l'un pour l'autre. */
function demiLargeurPireCas(dir, haut) {
  const n = Math.hypot(dir.x, dir.y, dir.z);
  const z = { x: dir.x / n, y: dir.y / n, z: dir.z / n };
  /* Le produit vectoriel haut × zcam, écrit à la main : cette règle doit
     pouvoir tourner dans node, où le spécifieur « three » n'est pas résolu. */
  const rx = haut.y * z.z - haut.z * z.y;
  const ry = haut.z * z.x - haut.x * z.z;
  const rz = haut.x * z.y - haut.y * z.x;
  const m = Math.hypot(rx, ry, rz);
  return (Math.abs(rx) + Math.abs(ry) + Math.abs(rz)) / m;
}

/* PURE. TOUTE la décision de cadrage, en un appel et sans three.js — rendue
   séparément parce qu'un banc-miroir ne peut pas voir un calcul faux : il faut
   pouvoir l'EXÉCUTER sur des nombres.

   Rend { seuil, recul, demiHauteur }, où `demiHauteur` est la demi-hauteur
   VISIBLE au plan du centre. C'est la grandeur COMMUNE aux deux projections,
   et c'est elle qui permet à l'isométrique de recevoir le même cadrage que la
   perspective sans transposer une formule par analogie.

   Le cadrage VERTICAL est inchangé depuis la tâche 3 : une demi-hauteur de
   NORME_DIR·marge·rayon, soit 1,6875·rayon à la marge par défaut. Le facteur
   NORME_DIR n'est plus la norme d'une direction — les autres vues ont la leur
   — mais l'ÉCHELLE DE CADRAGE HÉRITÉE ; la changer déplacerait le cadrage de
   la vue libre, que la tâche 3 a mesuré et que la demande exige de conserver.
   Il tient debout pour les cinq vues : la demi-hauteur du pire cas vaut
   1,4269·rayon en libre, 1,6330 en isométrique et 1,0000 sur un axe, toutes
   sous 1,6875 — l'isométrie étant la plus juste, à 3,3 % de marge.

   La demi-largeur visible en vaut `aspect` fois autant, quand le pire cas en
   réclame demiLargeurPireCas·rayon : il y a donc rognage dès que aspect <
   demiLargeurPireCas/(NORME_DIR·marge), et LÀ SEULEMENT on élargit, du facteur
   exact qui manque, seuil/aspect. Au-dessus du seuil le cadrage ne bouge pas
   d'un pixel — le `: 1` le dit. Pour la vue libre le seuil vaut 0,813030, à la
   sixième décimale celui de la tâche 3.

   CE QUE L'ORTHOGRAPHIQUE CHANGE, et il fallait le mesurer : sous perspective
   ce critère compare des étendues AU PLAN DU CENTRE alors que le coin le plus
   PROCHE se projette plus loin, si bien que la correction ramenait le
   débordement à l'ordre de grandeur du vertical, pas à zéro. Une projection
   parallèle n'a pas de coin plus proche : le critère y est EXACT, et sous le
   seuil le cube du pire cas touche les deux bords à 1e-15. Un banc l'exécute
   sur les huit sommets.

   COMPARABILITÉ : le recul ne dépend QUE de l'aspect, de la vue et de la marge
   — jamais des proportions du modèle, alors qu'une largeur mesurée sur CE
   maillage aurait été plus fine. C'est délibéré : deux canevas de même aspect
   reçoivent le MÊME cadre, et leur échelle ne diffère plus que par `rayon`. Un
   terme mesuré par modèle aurait reculé le plus large des deux et fait croire
   qu'il était le plus petit. */
export function cadrageDe(rayon, aspect, marge, orientation) {
  const seuil = demiLargeurPireCas(orientation.dir, orientation.haut)
    / (NORME_DIR * marge);
  const recul = aspect < seuil ? seuil / aspect : 1;
  return { seuil, recul, demiHauteur: NORME_DIR * (rayon * marge * recul) };
}

/* PURE. Les quatre bords d'une caméra orthographique, d'une demi-hauteur et
   d'un aspect. C'EST ICI QUE L'ORTHO DIFFÈRE DE LA PERSPECTIVE : une
   perspective rend sa demi-hauteur en DISTANCE — reculer agrandit le champ —
   là où une ortho la rend en BORDS, reculer une ortho ne changeant
   strictement rien à son image. Transposer la formule de distance par analogie
   aurait donné une caméra qui ne cadre plus jamais rien. */
export function cadreOrtho(demiHauteur, aspect) {
  const dl = demiHauteur * aspect;
  return { left: -dl, right: dl, top: demiHauteur, bottom: -demiHauteur };
}

/* Pose les quatre bords sur la caméra. Séparé de cadreOrtho() pour que la
   règle reste pure et que l'écriture reste un effet. */
function poserCadreOrtho(cam, demiHauteur, aspect) {
  const c = cadreOrtho(demiHauteur, aspect);
  cam.left = c.left; cam.right = c.right;
  cam.top = c.top; cam.bottom = c.bottom;
  cam.updateProjectionMatrix();
}

/* PURE. Les plans de coupe, déduits de la distance PAR LE SCALAIRE HÉRITÉ,
   distance / NORME_DIR — et l'argument du paramètre n'est pas n'importe quelle
   distance, c'est celle que cadrer() construit. La tâche 3 posait
   `d = rayon·marge·recul / tan(fov/2)`, `near = max(d/1000, 0,001)`,
   `far = d·100`, et cette `d`-là N'ÉTAIT PAS la distance : la caméra se posait
   à `d·DIR`, de norme 1,25. Diviser ici est donc ce qui rend les deux plans
   IDENTIQUES à ceux d'avant cette tâche ; passer une distance mesurée ailleurs
   les déplacerait de 25 % sans que rien à l'écran ne le dise. Un banc les
   recalcule par le chemin de la tâche 3, sans mentionner NORME_DIR.
   Ils valent pour les deux projections. Vérification à la marge par défaut :
   distance = 4,0740·rayon, near = 0,00326·rayon, far = 325,9·rayon, quand le
   modèle occupe [distance − 1,733·rayon, distance + 1,733·rayon]. */
function coupeDe(distanceDeCadrage) {
  const d = distanceDeCadrage / NORME_DIR;
  return { near: Math.max(d / 1000, 0.001), far: d * 100 };
}

function poserCoupe(cam, distanceDeCadrage) {
  const c = coupeDe(distanceDeCadrage);
  cam.near = c.near;
  cam.far = c.far;
}

/* L'aspect, MESURÉ SUR LE DOM et non lu dans `camera.aspect` : ce dernier
   retarde d'une image (redimensionner() le pose) et n'existe pas sur une
   ortho. Lire clientWidth vide au passage le calcul de mise en page : la
   mesure reflète donc le style DÉJÀ POSÉ. */
export function aspectDe(api) {
  const cv = api.renderer.domElement;
  return (cv.clientWidth || 1) / (cv.clientHeight || 1);
}

/* ── LE REPÈRE : une graduation, trois axes à l'origine, zéro millimètre ────

   POURQUOI ICI, ET NON DANS LA PAGE. Une règle est un accessoire du REGARD,
   pas de l'écran qui regarde : posée dans le canevas partagé, elle vaut sous
   les DEUX projections sans qu'aucune page n'ait à s'en souvenir. C'est
   exactement ce que la demande réclame — « dans les deux modes de
   manipulation, une graduation visible ».

   AUCUN MILLIMÈTRE N'EST ÉCRIT ICI, et c'est structurel. Un GLB n'a PAS
   d'échelle : c'est `print3d.mettre_a_l_echelle(tris, cible_mm)` qui en
   fabrique une, au moment d'écrire un STL, en portant la plus grande dimension
   à la cible. Tout ce bloc compte donc en unités glTF ; la conversion est
   offerte séparément par echelleMm(), site canonique de la doctrine, et elle
   rend `null` tant que personne n'a posé de cible. */

/* Le nombre de pas VISÉS en travers de la hauteur visible. */
const DIVISIONS_VISEES = 10;

/* PURE. Le pas « rond » d'une graduation, en unités du modèle.

   1-2-5, ET PAR LE BAS. La suite 1, 2, 5 est celle des règles et des axes de
   graphique ; c'est l'arrondi PAR LE BAS qui décide de quelque chose ici, et
   il se démontre : avec `pas ≤ étendue/divisions`, la hauteur visible porte
   TOUJOURS au moins `divisions` pas. Arrondi au plus proche (seuils √2, √10,
   √50), le pas monterait jusqu'à √2·brut et la hauteur n'en porterait plus que
   7,07 dans le pire cas — une graduation qui se clairsème au moment même où
   l'on zoome pour lire est une graduation qui manque.

   CE QUE LE FACTEUR VAUT, EXACTEMENT. Pour n = brut/décade dans [1, 10), le
   rapport brut/pas vaut n sur [1, 2), n/2 sur [2, 5) et n/5 sur [5, 10) : il
   vit donc dans [1 ; 2,5). Le nombre de pas VISIBLES vit par conséquent dans
   [10 ; 25) à `divisions = 10`, quel que soit le zoom — c'est la seule
   promesse que cette fonction fait, et un banc balaie six décades pour la
   vérifier par un second chemin.

   `null` SUR UNE ÉTENDUE NULLE, et ce n'est pas de la politesse : log10(0)
   vaut −∞, `10 ** -Infinity` vaut 0, donc un pas nul, donc une grille de zéro
   ligne — c'est-à-dire rien à l'écran, sans la moindre erreur nulle part. */
export function pasGradue(etendue, divisions = DIVISIONS_VISEES) {
  if (!(etendue > 0) || !Number.isFinite(etendue)) return null;
  if (!(divisions > 0)) return null;
  const brut = etendue / divisions;
  const decade = Math.pow(10, Math.floor(Math.log10(brut)));
  const n = brut / decade;
  return (n >= 5 ? 5 : n >= 2 ? 2 : 1) * decade;
}

/* Les cases de part et d'autre de l'origine : plancher, plafond, quantum. */
const CASES_MIN = 48;
const CASES_MAX = 256;
const CASES_QUANTUM = 16;

/* PURE. Combien de cases la grille porte de CHAQUE CÔTÉ de l'origine.

   LA GRILLE EST CENTRÉE SUR L'ORIGINE, jamais sur le modèle : c'est l'origine
   que la demande veut voir, et une trame recentrée à chaque orbite ne serait
   plus un repère mais un tapis. `portee` est donc la distance qui va de
   l'origine au bord du champ, et le compte s'y ajuste.

   LE PLANCHER À 48 EST DÉRIVÉ, non choisi au doigt. La demi-hauteur visible
   vaut au plus 12,5 pas (voir pasGradue), donc la demi-largeur au plus
   12,5·aspect : 48 couvre les aspects jusqu'à 3,84, quand les trois aspects
   mesurés au banc valent 1,0437, 0,5218 et 2,8000. LE PLAFOND À 256
   borne le coût quand le modèle est posé loin de l'origine — au-delà la grille
   cesse de grandir, l'origine sort du champ, et seuls les chiffres restent.

   QUANTIFIÉ PAR 16 : sans cela le compte changerait à chaque image de zoom et
   la grille se reconstruirait soixante fois par seconde pour deux lignes. */
export function casesGraduees(pas, portee) {
  if (!(pas > 0) || !Number.isFinite(pas)) return 0;
  const brut = Math.max(0, Number(portee) || 0) / pas;
  const n = Math.ceil(brut / CASES_QUANTUM) * CASES_QUANTUM;
  return Math.max(CASES_MIN, Math.min(CASES_MAX, n));
}

/* PURE. LES MILLIMÈTRES PAR UNITÉ glTF — L'UNIQUE SOURCE DE MILLIMÈTRES DE
   TOUTE LA CHAÎNE NAVIGATEUR, et le site canonique de la doctrine.

   UN GLB N'A AUCUNE ÉCHELLE EN MILLIMÈTRES. Celle qui existe est fabriquée
   côté serveur par `print3d.mettre_a_l_echelle(tris, cible_mm)`
   (backend/app/services/print3d.py), et la règle y tient en une ligne :
   `s = cible_mm / plus_grande`, où `plus_grande` est la plus grande des trois
   dimensions de la boîte englobante. C'est CETTE règle qui est reprise ici, et
   un banc l'exécute des deux côtés — node contre Python — plutôt que de croire
   la présente phrase.

   `null` TANT QU'AUCUNE CIBLE N'EST POSÉE, et `null` aussi sur un maillage
   sans volume : afficher un chiffre en millimètres sur un modèle qui n'a pas
   d'échelle serait une règle qui MENT, ce qui est pire qu'une règle muette. La
   sévérité est celle de la Forge 3D des cartes (cardforge/js/core.js,
   `print3dFromStl`), qui refuse un `cible_mm` non numérique ou ≤ 0 ; on ne
   refuse pas plus doucement ici. */
export function echelleMm(plusGrandeDimension, cibleMm) {
  const cible = Number(cibleMm);
  const grande = Number(plusGrandeDimension);
  if (!Number.isFinite(cible) || !(cible > 0)) return null;
  if (!Number.isFinite(grande) || !(grande > 0)) return null;
  return cible / grande;
}

/* L'ÉTENDUE VISIBLE au plan de la cible, sous l'une OU l'autre projection —
   c'est elle que la graduation gradue.

   LES DEUX PROJECTIONS N'ONT PAS LA MÊME GRANDEUR, et les confondre serait le
   piège déjà nommé par cadreOrtho() : une ortho rend sa demi-hauteur en BORDS
   (reculer ne change rien à son image), une perspective la rend en DISTANCE.
   Le `zoom` divise dans les deux cas — c'est par lui qu'OrbitControls zoome une
   ortho, et le cadre calculé par cadrer() en serait sinon démenti.

   `api.cameraPerspective.fov` NOMMÉMENT, jamais `.fov` sur la caméra active :
   une ortho n'en a pas, la lecture rend `undefined`, la multiplication rend
   NaN et la graduation disparaît sans qu'aucune erreur ne remonte. Un banc
   interdit ce fichier de la seconde forme. */
export function etendueVisible(api) {
  const cam = api.camera;
  const zoom = cam.zoom || 1;
  const demiHauteur = cam.isOrthographicCamera
    ? ((cam.top - cam.bottom) / 2) / zoom
    : (cam.position.distanceTo(api.controls.target)
       * Math.tan((api.cameraPerspective.fov * Math.PI) / 360)) / zoom;
  return { demiHauteur, demiLargeur: demiHauteur * aspectDe(api) };
}

/* Les trois axes du MODÈLE, aux couleurs que le gizmo leur donne déjà : les
   réinventer ferait dire à un X rouge et à un X bleu la même chose sur le même
   écran. */
const COULEUR_AXE = { x: 0xd2544e, y: 0x62b56a, z: 0x4d7fd0 };
/* Les mêmes deux gris que le plateau du dépôt : une seconde palette de grille
   sur la même page se lirait comme une seconde échelle. */
const COULEUR_TRAME = 0x333941;
const COULEUR_TRAME_CENTRE = 0x5b636f;
/* Au-delà, la lecture n'est plus une lecture : on borne le nombre de marques
   plutôt que de fabriquer mille segments pour un rail qui en montre douze. */
const MARQUES_MAX = 24;

/* L'état du repère, par vue. Une WeakMap et non des clés d'`api` : le contrat
   de forme d'`api` est une surface publique, et trois champs de dessin n'y ont
   rien à faire. Une vue oubliée n'y retient rien. */
const _reperes = new WeakMap();

function libererLigne(o) {
  if (!o) return;
  if (o.parent) o.parent.remove(o);
  if (o.geometry) o.geometry.dispose();
  if (o.material) o.material.dispose();
}

/* Des segments COLORÉS PAR SOMMET : un seul objet pour les trois axes, un
   seul pour toutes les marques. Trois LineSegments monochromes auraient coûté
   trois appels de dessin pour la même image. */
function segmentsColores(points, couleurs, opacite) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(couleurs, 3));
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({
    vertexColors: true, transparent: true, opacity: opacite,
    /* Le repère ne s'écrit PAS dans le tampon de profondeur : il reste occulté
       par le maillage (depthTest est laissé actif) sans pour autant découper
       les faces transparentes qui passeraient derrière lui. */
    depthWrite: false }));
}

function construireAxes(portee) {
  const p = [], c = [];
  for (const axe of ["x", "y", "z"]) {
    const u = { x: 0, y: 0, z: 0 };
    u[axe] = portee;
    p.push(-u.x, -u.y, -u.z, u.x, u.y, u.z);
    const t = new THREE.Color(COULEUR_AXE[axe]);
    c.push(t.r, t.g, t.b, t.r, t.g, t.b);
  }
  return segmentsColores(p, c, 0.9);
}

/* Met la graduation à jour et NE RECONSTRUIT QUE CE QUI CHANGE.

   Le contrat est un mémo : tant que (pas, cases) ne bouge pas, elle ne fait
   que le calcul des deux règles pures et une comparaison. Quand il bouge, elle
   libère l'ancienne grille — géométrie ET matériau : dix paliers de zoom
   laisseraient sinon dix trames sur la carte, exactement la fuite que vider()
   existe pour empêcher.

   LE PAS EST DIT AU DEHORS par un évènement sur le canevas, et pas autrement :
   une trame sans échelle chiffrée n'est pas une graduation, mais ce module ne
   connaît aucun élément de page où l'écrire. Il crie ; la page écoute. */
export function majRepere(api) {
  const vue = etendueVisible(api);
  const pas = pasGradue(2 * vue.demiHauteur);
  if (!pas) return null;
  const cible = api.controls.target;
  /* La portée à couvrir : de l'origine jusqu'au bord du champ. La cible peut
     être loin de l'origine — une extraction, un modèle non recentré — et une
     grille dimensionnée sur le seul champ visible ne rejoindrait alors jamais
     le point dont elle prétend mesurer la distance. */
  const portee = Math.hypot(cible.x, cible.z)
    + Math.max(vue.demiHauteur, vue.demiLargeur);
  const cases = casesGraduees(pas, portee);
  let e = _reperes.get(api);
  if (!e) {
    e = { groupe: new THREE.Group(), trame: null, axes: null, marque: null,
          pas: 0, cases: 0 };
    e.groupe.name = "lib3d-repere";
    /* DANS LA SCÈNE, jamais dans le modèle : vider() ne retire que
       `api.racine`, et un repère greffé au modèle disparaîtrait au premier
       chargement sans que personne ne l'ait rangé. */
    api.scene.add(e.groupe);
    _reperes.set(api, e);
  }
  if (e.pas === pas && e.cases === cases) return e;
  e.pas = pas;
  e.cases = cases;
  libererLigne(e.trame);
  libererLigne(e.axes);
  const cote = 2 * cases * pas;
  e.trame = new THREE.GridHelper(cote, 2 * cases,
                                 COULEUR_TRAME_CENTRE, COULEUR_TRAME);
  e.trame.material.transparent = true;
  e.trame.material.opacity = 0.4;
  e.trame.material.depthWrite = false;
  e.axes = construireAxes(cases * pas);
  e.groupe.add(e.trame);
  e.groupe.add(e.axes);
  api.renderer.domElement.dispatchEvent(new CustomEvent("lib3d:graduation", {
    detail: { pas, cases, portee: cases * pas } }));
  return e;
}

/* Marque des points SUR le repère : pour chacun, la descente jusqu'au plan de
   la trame, puis les deux jambes qui rejoignent l'origine, chacune de la
   couleur de l'axe qu'elle longe. C'est la lecture graphique de « à quelle
   distance de l'origine », que trois nombres seuls ne donnent pas.

   Une petite croix marque le point lui-même : sans elle, un point posé sur le
   plan de la trame se confond avec le pied de sa propre descente. Sa taille
   est un quart de PAS — donc à l'échelle de la graduation, et non d'un modèle
   dont ce module ne connaît pas la taille. */
export function marquerAuRepere(api, points) {
  const e = api && _reperes.get(api);
  if (!e) return 0;
  libererLigne(e.marque);
  e.marque = null;
  const liste = (points || []).slice(0, MARQUES_MAX);
  if (!liste.length) return 0;
  const p = [], c = [];
  const pousser = (a, b, teinte) => {
    p.push(a.x, a.y, a.z, b.x, b.y, b.z);
    const t = new THREE.Color(teinte);
    c.push(t.r, t.g, t.b, t.r, t.g, t.b);
  };
  const croix = e.pas / 4;
  for (const q of liste) {
    const pied = { x: q.x, y: 0, z: q.z };
    pousser(q, pied, COULEUR_AXE.y);
    pousser(pied, { x: 0, y: 0, z: q.z }, COULEUR_AXE.x);
    pousser({ x: 0, y: 0, z: q.z }, { x: 0, y: 0, z: 0 }, COULEUR_AXE.z);
    for (const axe of ["x", "y", "z"]) {
      const a = { x: q.x, y: q.y, z: q.z }, b = { x: q.x, y: q.y, z: q.z };
      a[axe] -= croix;
      b[axe] += croix;
      pousser(a, b, COULEUR_AXE[axe]);
    }
  }
  e.marque = segmentsColores(p, c, 0.95);
  e.groupe.add(e.marque);
  return liste.length;
}

/* Montre ou cache le repère ENTIER, et rend l'état d'AVANT — c'est ce retour
   qui permet à un appelant de le rétablir sans avoir à le supposer. Une
   photographie du canevas (la vignette de l'Établi) n'a pas à emporter la
   règle avec le maillage : une carte de bibliothèque montre un objet, pas un
   atelier. */
export function montrerRepere(api, visible) {
  const e = api && _reperes.get(api);
  if (!e) return false;
  const avant = e.groupe.visible;
  e.groupe.visible = !!visible;
  return avant;
}

/* Cadre la caméra sur la boîte englobante. Indispensable : un modèle en mètres
   et un modèle en centimètres donneraient l'un un point, l'autre un mur.

   CONTRAT D'APPELANT : elle mesure le DOM TEL QU'IL EST à l'appel. Ce
   qu'aucune lecture ne peut deviner, c'est ce que l'appelant s'apprête ENCORE
   à insérer — à lui d'appeler cadrer() quand le DOM a sa taille finale, sans
   quoi le cadrage est juste pour une mise en page transitoire. */
export function cadrer(api, marge = 1.35) {
  if (!api.racine) return null;
  const boite = new THREE.Box3().setFromObject(api.racine);
  const taille = boite.getSize(new THREE.Vector3());
  const centre = boite.getCenter(new THREE.Vector3());
  const rayon = Math.max(taille.x, taille.y, taille.z) * 0.5 || 1;
  const aspect = aspectDe(api);
  const o = orientationDe(api.vueCadrage);
  const cadre = cadrageDe(rayon, aspect, marge, o);
  /* LA DISTANCE EST CELLE DE LA PERSPECTIVE, dans les deux cas — et
     `api.cameraPerspective.fov` explicitement, JAMAIS `api.camera.fov` : une
     ortho n'a pas de `.fov`, le lire rend `undefined`, la division rend NaN,
     `position.set` avale trois NaN et l'écran devient noir sans qu'aucune
     erreur ne remonte.
     Sous l'orthographique cette distance n'a aucun effet sur l'image, mais elle
     en a deux ailleurs : les plans de coupe, et l'état sphérique
     d'OrbitControls, qui déduit son rayon de (position − cible) à chaque
     update(). Les deux caméras se cadrent donc à la MÊME distance, ce qui
     laisse à projeter() une bascule qui n'a plus qu'à reporter la pose. */
  const distance = cadre.demiHauteur
    / Math.tan((api.cameraPerspective.fov * Math.PI) / 360);
  const n = Math.hypot(o.dir.x, o.dir.y, o.dir.z);
  api.camera.position.set(
    centre.x + (distance * o.dir.x) / n,
    centre.y + (distance * o.dir.y) / n,
    centre.z + (distance * o.dir.z) / n);
  poserCoupe(api.camera, distance);
  /* LE ZOOM REPART À 1, sous les DEUX projections. OrbitControls zoome une
     ortho par `camera.zoom`, qui remettrait à l'échelle le cadre qu'on vient de
     calculer : « Face » atterrirait sur le grossissement du geste d'avant, et
     deux modèles chargés à la suite cesseraient d'être comparables. La
     perspective ne se zoome pas ainsi aujourd'hui, mais l'invariant vaut mieux
     énoncé une fois pour les deux que vrai par accident sur l'une. */
  api.camera.zoom = 1;
  if (api.camera.isOrthographicCamera) {
    poserCadreOrtho(api.camera, cadre.demiHauteur, aspect);
  } else {
    api.camera.updateProjectionMatrix();
  }
  api.controls.target.copy(centre);
  api.controls.update();
  return { taille, centre, rayon, demiHauteur: cadre.demiHauteur };
}

/* ── basculer de projection ────────────────────────────────────────────────
   CE QU'ELLE FAIT, ET CE QU'ELLE NE FAIT PLUS.

   Elle change la CAMÉRA ACTIVE et lui reporte la POSE de celle qu'elle
   remplace. Rien d'autre. Le CADRE — bords ou fov, zoom, plans de coupe —
   appartient à cadrer(), et n'est pas repris ici.

   La première écriture reportait aussi la demi-hauteur visible, pour que le
   modèle garde sa taille à l'écran d'une projection à l'autre. C'était juste,
   c'était mesuré, et c'était INOBSERVABLE : les trois appelants —
   appliquerVue(), synchroniser() et _ouvrirComparaison() — écrasent tous ce
   cadre à la ligne suivante. Un calcul que personne ne regarde est une
   promesse qu'on croira tenue : on la RETIRE.

   LA POSE, ELLE, RESTE, parce qu'elle est OBSERVÉE : `api.controls.object =
   apres` fait aussitôt lire `apres.position` par OrbitControls, et une caméra
   d'arrivée laissée à sa position d'origine ferait sauter le point de vue
   partout où la bascule n'est PAS suivie d'un cadrage — sur une vue sans
   modèle, le cas de _ouvrirComparaison().

   CONTRAT D'APPELANT : appeler cadrer() — ou orienter(), qui cadre — derrière.
   Sans modèle il n'y a rien à cadrer, la scène est vide, et le prochain
   charger() cadre.

   TROIS RÉFÉRENCES DE CAMÉRA VIVENT AILLEURS, et les oublier ne lève rien :
     — OrbitControls, construit AVEC la caméra. On lui repose `object`
       ci-dessous, sans quoi la souris pilote celle que plus personne ne rend.
     — TransformControls, qui garde la sienne pour tailler et piquer ses
       poignées. Inconnu d'ici : à l'appelant de lui repasser `api.camera`, à
       TOUS ses sites — celui de la synchronisation A/B compris, qui projette
       la vue A quand c'est B qui bouge.
     — la synchronisation A/B elle-même, qui recopiait un `fov`.
   La boucle de rendu lit `api.camera` à chaque image : rien à y faire. */
export function projeter(api, mode) {
  if (mode !== "perspective" && mode !== "orthographique") return null;
  if (api.projection === mode) return mode;
  const avant = api.camera;
  const apres = mode === "orthographique"
    ? api.cameraOrthographique : api.cameraPerspective;
  apres.position.copy(avant.position);
  apres.quaternion.copy(avant.quaternion);
  api.camera = apres;
  api.projection = mode;
  /* SANS CETTE LIGNE, les contrôles continuent de piloter la caméra reçue au
     constructeur : l'orbite déplace une caméra que plus personne ne rend, et
     l'écran se fige sans qu'aucune erreur ne remonte. */
  api.controls.object = apres;
  api.controls.update();
  return mode;
}

/* ── orienter : libre, isométrique, face, dessus, profil ────────────────────
   La vue nommée RECADRE, elle ne fait pas que pivoter, et c'est nécessaire :
   le pire cas de largeur dépend de la direction (voir cadrageDe), donc un
   simple pivot laisserait l'isométrie rogner et les vues d'axe reculées de
   37 % pour rien. Le recadrage repose aussi la cible sur le centre : une vue
   nommée est un point de vue REMIS À ZÉRO, ce que son bouton promet. */
export function orienter(api, nom) {
  if (!ORIENTATIONS[nom]) return null;
  api.vueCadrage = nom;
  if (api.racine) { cadrer(api); return nom; }
  /* Pas de modèle : rien à cadrer, mais l'orientation se pose quand même, à la
     distance courante — sinon le premier chargement arriverait sur la vue
     d'avant et le bouton enfoncé mentirait. ET RIEN D'AUTRE : ni bords, ni
     zoom, ni plans de coupe, aucun n'ayant de valeur juste à écrire sur une
     scène vide. Le prochain charger() les pose tous. */
  const o = ORIENTATIONS[nom];
  const cible = api.controls.target;
  const d = api.camera.position.distanceTo(cible) || 1;
  const n = Math.hypot(o.dir.x, o.dir.y, o.dir.z);
  api.camera.position.set(
    cible.x + (d * o.dir.x) / n,
    cible.y + (d * o.dir.y) / n,
    cible.z + (d * o.dir.z) / n);
  api.controls.update();
  return nom;
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
