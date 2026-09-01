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
  /* LES DEUX CAMÉRAS NAISSENT ENSEMBLE, et l'orthographique n'attend pas le
     premier clic sur « Isométrique ». Une caméra fabriquée en cours de route
     arriverait APRÈS OrbitControls, après le gizmo et après le câblage de la
     comparaison A/B — trois objets qui retiennent chacun une référence de
     caméra et qu'il faudrait alors penser à prévenir. Elles coûtent une
     matrice chacune ; le rendu n'en consomme qu'une.
     Le cadre (-1, 1, 1, -1) est une amorce, pas un choix : cadrer() le réécrit
     au premier modèle et redimensionner() en refait la largeur à chaque
     changement de taille. */
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
     api.cameraPerspective`, et projeter() la fait basculer. `projection` et
     `vue` disent en toutes lettres ce que la caméra active est en train de
     faire — un lecteur ne doit pas avoir à le déduire d'un
     `isOrthographicCamera`. */
  const api = { renderer, scene, camera, controls, racine: null, gltf: null,
                cameraPerspective: camera, cameraOrthographique: cameraOrtho,
                projection: "perspective", vue: "libre" };

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
         ET SURTOUT : une OrthographicCamera N'A PAS d'`aspect`. Lui en écrire
         un ne lève rien, ne fait rien et ne se voit nulle part — le modèle
         reste simplement déformé. Son aspect vit dans left/right, qu'on refait
         à demi-hauteur CONSTANTE : top/bottom sont la mémoire du cadrage, et
         un redimensionnement n'a pas à y toucher. */
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

   PAS DE « DERRIÈRE », PAS DE « DESSOUS ». Trois vues et une isométrique,
   ce que la demande dit ; les faces opposées s'atteignent d'un demi-tour à la
   souris, et six boutons dans un coin de canevas se lisent moins bien que
   quatre.

   ET RIEN ICI NE SUIT L'AXE D'EMPILEMENT DE LA PLAQUE. `axeEmpile` de
   plaque.js choisit son plan d'étalement d'après les pièces — y pour des
   volumes, z pour les cartes du modèle réel — si bien que « la vue qui regarde
   la plaque en face » n'est pas toujours « dessus ». Faire suivre les boutons
   ferait dire à « Dessus » qu'il regarde selon X un jour sur deux : un libellé
   qui ment. Les trois vues restent donc les axes DU MODÈLE, ceux-là mêmes que
   le serveur nomme dans `axe_haut` ; c'est l'Établi qui DIT laquelle des trois
   fait face à la plaque quand elle est étalée (voir VUE_DE_PLAQUE dans
   etabli.js). */
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
   généraliser, parce que le pire cas DÉPEND DE LA DIRECTION, et pas qu'un peu
   — MESURÉ : 1,371989 en vue libre, 1,414214 (√2) en isométrique, 1,000000
   sur les trois vues d'axe. Garder 1,372 partout aurait rogné l'isométrie de
   3,1 % en largeur sous le seuil, et reculé les vues d'axe de 37 % pour rien. */
export function largeurPireCas(dir, haut) {
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
   réclame largeurPireCas·rayon : il y a donc rognage dès que aspect <
   largeurPireCas/(NORME_DIR·marge), et LÀ SEULEMENT on élargit, du facteur
   exact qui manque, seuil/aspect. Au-dessus du seuil le cadrage ne bouge pas
   d'un pixel — le `: 1` le dit. Pour la vue libre le seuil vaut 0,813030, à la
   sixième décimale celui de la tâche 3.

   CE QUE LE PASSAGE À L'ORTHOGRAPHIQUE CHANGE, et il fallait le mesurer : sous
   perspective ce critère compare des étendues AU PLAN DU CENTRE alors que le
   coin le plus PROCHE se projette un peu plus loin encore, si bien que la
   correction ramenait le débordement à l'ordre de grandeur du vertical, pas à
   zéro. Une projection parallèle n'a pas de coin plus proche : sous
   l'orthographique le critère est EXACT, et sous le seuil le cube du pire cas
   touche les deux bords à 1e-15 près. Un banc l'exécute sur les huit sommets.

   COMPARABILITÉ : le recul ne dépend QUE de l'aspect, de la vue et de la marge
   — jamais des proportions du modèle, alors qu'une largeur projetée mesurée
   sur CE maillage aurait été plus fine. C'est délibéré. Deux canevas de même
   aspect reçoivent ainsi le MÊME cadre, et leur échelle ne continue de
   différer que par `rayon` — la normalisation qui rend deux modèles
   comparables à l'œil. Un terme mesuré par modèle aurait reculé le plus large
   des deux et fait croire qu'il était le plus petit : un cadrage qui diverge
   détruit une comparaison aussi sûrement que deux angles de vue différents. */
export function cadrageDe(rayon, aspect, marge, orientation) {
  const seuil = largeurPireCas(orientation.dir, orientation.haut)
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

/* PURE. Les plans de coupe, DÉDUITS de la distance de pose — et par le
   SCALAIRE HÉRITÉ, distance / NORME_DIR. Ce n'est pas une coquetterie
   d'écriture : la tâche 3 posait `d = rayon·marge·recul / tan(fov/2)` puis
   `near = max(d/1000, 0,001)` et `far = d·100`, et cette `d`-là N'ÉTAIT PAS la
   distance — la caméra était posée à `d·DIR`, de norme 1,25, si bien que la
   distance vraie valait 1,25·d. Diviser ici est donc ce qui rend les deux
   plans IDENTIQUES à ceux d'avant cette tâche ; écrire la distance vraie les
   déplacerait tous les deux de 25 %, sur un cadrage que la demande exige de
   conserver, et rien à l'écran ne le dirait. Un banc les recalcule par le
   chemin de la tâche 3 — rayon, marge, recul, fov — sans jamais mentionner
   NORME_DIR.

   Ils valent pour les deux projections : la profondeur qu'occupe une boîte de
   rayon `rayon` vue de `distance` ne dépend pas de la façon dont on la
   projette. Vérification à la marge par défaut : distance = 4,0740·rayon,
   near = 0,00326·rayon, far = 325,9·rayon, quand le modèle occupe
   [distance − 1,733·rayon, distance + 1,733·rayon]. */
export function coupeDe(distance) {
  const d = distance / NORME_DIR;
  return { near: Math.max(d / 1000, 0.001), far: d * 100 };
}

function poserCoupe(cam, distance) {
  const c = coupeDe(distance);
  cam.near = c.near;
  cam.far = c.far;
}

/* L'aspect du canevas, MESURÉ SUR LE DOM et non lu dans `camera.aspect` : ce
   dernier n'est rafraîchi qu'à la prochaine image par redimensionner() et
   retarderait donc d'un tour — et il n'existe pas du tout sur une ortho. Lire
   clientWidth vide au passage le calcul de mise en page, si bien que la mesure
   reflète le style DÉJÀ POSÉ. */
export function aspectDe(api) {
  const cv = api.renderer.domElement;
  return (cv.clientWidth || 1) / (cv.clientHeight || 1);
}

/* Cadre la caméra sur la boîte englobante. Indispensable : un modèle en mètres
   et un modèle en centimètres donneraient l'un un point, l'autre un mur — et
   deux étapes ne seraient pas comparables à l'œil.

   CONTRAT D'APPELANT : cette fonction mesure le DOM TEL QU'IL EST à l'appel.
   Ce qu'aucune lecture ne peut deviner, c'est ce que l'appelant s'apprête
   ENCORE à insérer : à lui d'appeler cadrer() quand le DOM a sa taille finale,
   sans quoi le cadrage est juste — pour une mise en page transitoire. */
export function cadrer(api, marge = 1.35) {
  if (!api.racine) return null;
  const boite = new THREE.Box3().setFromObject(api.racine);
  const taille = boite.getSize(new THREE.Vector3());
  const centre = boite.getCenter(new THREE.Vector3());
  const rayon = Math.max(taille.x, taille.y, taille.z) * 0.5 || 1;
  const aspect = aspectDe(api);
  const o = orientationDe(api.vue);
  const cadre = cadrageDe(rayon, aspect, marge, o);
  /* LA DISTANCE EST CELLE DE LA PERSPECTIVE, dans les deux cas — et
     `api.cameraPerspective.fov` explicitement, JAMAIS `api.camera.fov` : une
     OrthographicCamera n'a pas de `.fov`, le lire y rend `undefined`, la
     division rend NaN, `position.set` avale trois NaN et l'écran devient noir
     sans qu'aucune erreur ne remonte.
     Sous l'orthographique cette distance n'a AUCUN effet sur l'image — la
     projection est parallèle — mais elle en a deux ailleurs : les plans de
     coupe, et l'état sphérique d'OrbitControls, qui déduit son rayon de
     (position − cible) à chaque update(). Les deux caméras se cadrent donc à
     la MÊME distance, ce qui laisse à projeter() une bascule qui n'a plus qu'à
     reporter la pose — sans quoi il lui faudrait la RECALCULER, et ce calcul-là
     serait écrasé par le cadrage suivant. */
  const distance = cadre.demiHauteur
    / Math.tan((api.cameraPerspective.fov * Math.PI) / 360);
  const n = Math.hypot(o.dir.x, o.dir.y, o.dir.z);
  api.camera.position.set(
    centre.x + (distance * o.dir.x) / n,
    centre.y + (distance * o.dir.y) / n,
    centre.z + (distance * o.dir.z) / n);
  poserCoupe(api.camera, distance);
  /* LE ZOOM REPART À 1, sous les DEUX projections. OrbitControls zoome une
     ortho par `camera.zoom`, qui remettrait à l'échelle le cadre qu'on vient
     de calculer : « Face » atterrirait sur le grossissement du geste d'avant,
     et deux modèles chargés à la suite ne seraient plus comparables — ce que
     cadrer() existe pour garantir. La perspective ne se zoome pas ainsi
     aujourd'hui (la molette y déplace la caméra), mais l'invariant « après
     cadrer(), zoom vaut 1 » vaut mieux énoncé une fois pour les deux que vrai
     par accident sur l'une. */
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

   La première écriture reportait aussi la demi-hauteur visible au plan de la
   cible, pour que le modèle garde sa taille à l'écran d'une projection à
   l'autre. C'était juste, c'était mesuré, et c'était INOBSERVABLE : les trois
   appelants — appliquerVue(), synchroniser() et _ouvrirComparaison(), dans
   etabli.js — écrasent tous ce cadre à la ligne suivante, par
   orienter()→cadrer() ou par la recopie de synchronisation. Un calcul que
   personne ne regarde est une promesse qu'on croira tenue : on la RETIRE
   plutôt que de l'entretenir et de la garder. (Même doctrine que le `vides` de
   la plaque, rendu par le module et lu par personne, qu'une tâche précédente a
   fini par DIRE à l'écran plutôt que par laisser mourir.)

   LA POSE, ELLE, RESTE — parce qu'elle est OBSERVÉE. `api.controls.object =
   apres` fait aussitôt lire `apres.position` par OrbitControls : une caméra
   d'arrivée laissée à sa position d'origine ferait sauter le point de vue
   partout où la bascule n'est PAS suivie d'un cadrage, c'est-à-dire sur une
   vue sans modèle — le cas exact de _ouvrirComparaison(), qui projette la vue
   B avant de lui donner son GLB.

   CONTRAT D'APPELANT, donc : appeler cadrer() — ou orienter(), qui cadre —
   derrière. Sans modèle il n'y a rien à cadrer et le cadre reste celui d'avant,
   sans conséquence : la scène est vide, et le prochain charger() cadre.

   TROIS RÉFÉRENCES DE CAMÉRA VIVENT HORS DE CE MODULE, et chacune est une
   panne SILENCIEUSE si on l'oublie :
     — OrbitControls, construit avec la caméra. On lui repose `object`
       ci-dessous ; sans quoi les contrôles pilotent celle que plus personne ne
       rend, et la souris ne fait plus rien de visible.
     — TransformControls, qui garde SA référence pour dimensionner et piquer
       ses poignées. Il n'est pas connu d'ici : c'est à l'appelant de lui
       repasser `api.camera` — et à TOUS ses sites, y compris celui de la
       synchronisation A/B, qui projette la vue A quand c'est B qui bouge.
     — la synchronisation A/B elle-même, qui recopiait un `fov` qu'une ortho
       n'a pas.
   La boucle de rendu, elle, lit `api.camera` à chaque image : rien à y faire. */
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
   La vue nommée RECADRE, elle ne fait pas que pivoter — et c'est nécessaire,
   pas décoratif : le pire cas de largeur DÉPEND de la direction (1,372 en
   libre, 1,414 en isométrique, 1,000 sur un axe), si bien qu'un simple pivot
   laisserait l'isométrie rogner de 3,1 % sous le seuil et les vues d'axe
   reculées de 37 % pour rien. Le recadrage repose aussi la cible sur le centre
   du modèle : une vue nommée est un point de vue REMIS À ZÉRO, ce que son
   bouton promet. */
export function orienter(api, nom) {
  if (!ORIENTATIONS[nom]) return null;
  api.vue = nom;
  if (api.racine) { cadrer(api); return nom; }
  /* Pas de modèle : rien à cadrer, mais l'orientation se pose quand même — à
     la distance courante — sinon le premier chargement arriverait sur la vue
     d'avant et le bouton enfoncé mentirait.
     ET RIEN D'AUTRE : ni bords, ni zoom, ni plans de coupe. Il n'y a aucune
     boîte à cadrer, donc aucun de ces nombres n'a de valeur juste à écrire ; le
     cadre reste celui d'avant et la scène est vide. Le prochain charger()
     appelle cadrer(), qui les pose tous. */
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
