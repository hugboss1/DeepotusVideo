/* La PLAQUE — étaler les pièces d'un modèle pour les VOIR, jamais pour les
   changer.

   LA RÈGLE QUI DOMINE CE MODULE, et elle n'est pas une intention :
   **l'étalement est un AFFICHAGE**. Rien ici ne fabrique de GLB, n'appelle de
   route, ni ne touche à la transformation propre d'une pièce. Le décalage vit
   dans un BERCEAU — un Group neuf, glissé entre la pièce et son parent — et
   la pièce garde sa `position`, son `quaternion` et son `scale` d'origine, au
   bit près.

   POURQUOI UN BERCEAU PLUTÔT QU'UN `piece.position.add(...)`, qui aurait tenu
   en une ligne. Parce que la porte d'écriture de l'Établi LIT `o.position` :
   le gizmo, sur `objectChange`, envoie au serveur `[o.position.x, y, z]`. Une
   pièce déplacée par l'étalement puis saisie au gizmo enverrait donc une
   translation qui INCLUT le décalage d'étalement — un modèle éclaté, écrit sur
   le disque, sans que rien ne grince. Le berceau rend ce mode de défaillance
   STRUCTURELLEMENT impossible : quoi que fasse l'Établi, il ne peut pas lire
   le décalage dans la pièce, puisqu'il n'y est pas. (L'Établi refuse en outre
   le gizmo tant que la plaque est affichée — deux gardes indépendantes pour
   le piège le plus cher de cette tâche.)

   AUCUN MILLIMÈTRE. Un GLB n'a pas d'échelle en mm : c'est
   `print3d.mettre_a_l_echelle(tris, cible_mm)` qui en fabrique une, au moment
   d'écrire un STL. Tout ce fichier compte donc en UNITÉS DU MODÈLE, et le
   plateau se dimensionne sur l'empreinte de l'étalement — pas sur les 256 mm
   de la Centauri Carbon 2. La graduation et la taille cible viennent plus
   tard ; les inventer ici mentirait. */
"use strict";
import * as THREE from "three";

/* La marge entre deux pièces, en fraction de la plus grande d'entre elles.
   CONSTANTE au sens qui compte : une seule valeur pour tout l'étalement, la
   même entre deux voisines de n'importe quelle étagère. Elle est RELATIVE
   parce qu'un GLB n'a pas d'échelle — 5 mm n'existent pas ici, et une marge
   absolue écarterait un modèle de 0,01 unité en poussière tout en collant
   les pièces d'un modèle de 100. */
const MARGE_RELATIVE = 0.12;

/* L'élancement de l'étalement : la largeur visée vaut ce facteur fois la
   racine de l'aire totale. À 1, l'empreinte tend vers le carré ; au-dessus,
   vers un bandeau. 1,2 donne trois à quatre pièces par rangée sur une dizaine
   de pièces de tailles voisines — ce que montre la vue de référence. */
const ELANCEMENT = 1.2;

/* L'angle d'or, en degrés. Deux pièces consécutives reçoivent ainsi des
   teintes maximalement écartées, et la teinte d'une pièce ne dépend QUE de
   son index de nœud glTF : elle est donc la même d'un étalement à l'autre,
   et la même après un rechargement du même modèle. Une palette énumérée
   aurait, elle, dépendu de l'ORDRE de la liste. */
const ANGLE_OR = 137.508;

/* Les trois axes, du nom que three.js leur donne. */
const AXES = ["x", "y", "z"];

/* Un modèle est APLATI quand l'étendue cumulée de ses pièces sur un axe tombe
   sous cette fraction du plus petit des deux autres. Voir axeEmpile(). */
const SEUIL_APLATI = 0.5;

/* Le plateau recule d'un cheveu derrière les pièces, en fraction de son côté.
   Sans lui, une pièce d'épaisseur NULLE — le cas mesuré ci-dessous — est
   exactement coplanaire avec la grille, et les deux clignotent. */
const RECUL_PLATEAU = 0.005;

/* Le plateau déborde de l'empreinte : une pièce posée au bord doit se lire
   COMME posée sur quelque chose, pas comme débordant dans le vide. */
const DEBORD_PLATEAU = 1.12;
const DIVISIONS_GRILLE = 24;

/* L'état d'étalement, par vue. Une WeakMap et non une variable de module :
   l'Établi a DEUX canevas (A et B), et le jour où la plaque servirait en B,
   une variable unique ferait ranger l'une en croyant ranger l'autre. Et une
   vue oubliée n'y retient rien. */
const _etats = new WeakMap();

/* Les matériaux d'un objet, qu'il en porte un ou un tableau, jamais de trou.
   RECOPIÉ de selection.js plutôt qu'importé : trois lignes contre l'ouverture
   d'une surface publique sur un module dont le contrat est « sélectionner ».
   Les deux ne peuvent pas diverger dangereusement — c'est une lecture. */
const materiauxDe = (o) =>
  (Array.isArray(o.material) ? o.material : [o.material]).filter(Boolean);

/* ── la teinte d'une pièce ──────────────────────────────────────────────────
   `cle` est l'index de nœud glTF : un entier stable, celui-là même que le
   serveur sait nommer. */
export function couleurDePiece(cle) {
  const h = (((Number(cle) || 0) * ANGLE_OR) % 360) / 360;
  return new THREE.Color().setHSL(h, 0.62, 0.58);
}

/* ── dans QUEL PLAN étaler ─────────────────────────────────────────────────
   LA SECONDE ERREUR DE CETTE TÂCHE, et elle a été mesurée hors navigateur sur
   le GLB réel de l'utilisateur (assets3d/6e0a8a5f/model.v5.glb, 9,4 Mo).

   La première écriture étalait toujours dans le plan du SOL (x, z), en
   supposant des volumes posés sur un plateau d'imprimante. Or ses douze
   pièces sont des PLANS, et leurs cotes le disent :

     fond-matiere      x=0,0630   y=0,0880   z=0,0000
     illustration      x=0,0630   y=0,0880   z=0,0000
     cadre             x=0,0630   y=0,0880   z=0,0011      (les douze pareil)

   L'empreinte au sol d'une carte debout vaut donc largeur × ÉPAISSEUR, c'est
   à dire largeur × zéro. Passées au vrai rangeur, ces douze boîtes rendaient
   DOUZE ÉTAGÈRES D'UNE PIÈCE — douze plans coplanaires empilés le long de
   l'axe de vue, à 0,0076 l'un de l'autre. La caméra les regarde justement par
   cet axe : l'utilisateur aurait revu UNE carte, à peine éventée. Étaler des
   pièces qui se cachent les unes les autres n'étale rien.

   D'où : on étale dans le plan où les pièces ONT de l'étendue, et l'axe
   d'empilement est celui sur lequel elles n'en ont pas. Avec HYSTÉRÉSIS —
   on ne quitte le plancher (y) que pour un modèle FRANCHEMENT aplati, sans
   quoi un modèle quasi cubique verrait son plan basculer au gré du bruit de
   mesure, et deux chargements du même maillage ne se ressembleraient plus.

   PURE, et c'est ce qui la rend mesurable hors navigateur : elle ne lit que
   des {x, y, z}. */
export function axeEmpile(tailles) {
  const somme = { x: 0, y: 0, z: 0 };
  for (const t of tailles) for (const a of AXES) somme[a] += t[a] || 0;
  let mince = "x";
  for (const a of AXES) if (somme[a] < somme[mince]) mince = a;
  if (mince === "y") return "y";
  const autres = AXES.filter((a) => a !== mince).map((a) => somme[a]);
  return somme[mince] < SEUIL_APLATI * Math.min(...autres) ? mince : "y";
}

/* ── quelles pièces ─────────────────────────────────────────────────────────
   LES NŒUDS INDEXÉS LES PLUS BAS QUI PORTENT DE LA GÉOMÉTRIE.

   La première écriture prenait les plus HAUTS, et c'était faux — mesuré dans
   un navigateur sur le modèle réel de l'utilisateur : UN berceau, décalé de
   (0, 0), la carte debout et entière sur le plateau. Son arbre :

     Group      "carte3d"
       Object3D "etabli_correction" [gltf 13]
         Object3D "carte3d_1"       [gltf 12]
           Mesh "fond-matiere" [gltf 0] … douze maillages [gltf 0..11]

   Et ce n'est PAS un cas particulier : le nœud d'enveloppe vient de
   `mesh_edit.reparer`, qui en ajoute un À CHAQUE RÉPARATION. Tout modèle
   passé par « Réparer l'assise » — le cas courant — n'a qu'un seul nœud au
   sommet, et « le plus haut » n'y étale donc jamais rien.

   POURQUOI LE NŒUD, ET NON LE MAILLAGE. Étaler littéralement les maillages
   serait plus direct, et c'est un piège : chez GLTFLoader, un nœud à
   plusieurs primitives donne un Group pour le nœud et un Mesh par primitive,
   et ces Mesh n'ont PAS de `nodes` dans `parser.associations` — indexerNoeuds
   refuse délibérément de leur en inventer un. Ils n'ont donc aucune clé, or
   toute la plaque tient sur `indexGltf` : la teinte stable, l'œil, et ce que
   le serveur saura nommer le jour où on extrait. La pièce reste le NŒUD ; ses
   primitives voyagent avec lui. (Suivre la granularité du panneau aurait le
   même défaut par un autre bout : un MATÉRIAU n'est pas un volume — il peut
   traverser plusieurs maillages et n'en couvrir qu'une part —, si bien que ce
   troisième mode aurait dû mentir ou se rabattre en silence.)

   LE DANGER DE L'IMBRICATION RESTE GARDÉ, par l'argument symétrique de
   l'ancien : deux pièces imbriquées recevraient deux berceaux et le décalage
   de la fille s'ajouterait à celui de sa mère. Une pièce n'ayant, par
   définition, aucun nœud indexé porteur EN DESSOUS d'elle, elle n'en contient
   aucune. Un banc l'exécute plutôt que de croire cette phrase.

   LIMITE ASSUMÉE : un nœud indexé qui porte SA PROPRE géométrie et contient
   par ailleurs un nœud indexé porteur n'est pas une pièce — sa géométrie
   propre reste à sa place d'assemblage pendant que sa fille s'étale. Le cas
   demande un maillage parent d'un maillage, que ni Meshy, ni Tripo, ni
   mesh_edit ne produisent ; le remède (une pièce « le reste de ce nœud »)
   coûterait une décomposition que rien ne réclame. */
export function piecesDe(api) {
  const pieces = [];
  if (!api || !api.racine) return pieces;
  /* Qui porte de la géométrie, sous-arbre compris. UNE descente récursive
     pour tout l'arbre, plutôt qu'un traverse() par nœud candidat : la
     seconde forme est quadratique pour exactement la même réponse. */
  const porteurs = new Set();
  const marquer = (o) => {
    /* L'appel récursif est à GAUCHE du `||` : à droite, un sous-arbre entier
       cesserait d'être marqué dès qu'un frère aurait déjà répondu vrai. */
    let porte = !!(o.isMesh && o.geometry);
    for (const enfant of o.children) porte = marquer(enfant) || porte;
    if (porte) porteurs.add(o);
    return porte;
  };
  marquer(api.racine);
  api.racine.traverse((o) => {
    if (o === api.racine) return;
    if (!o.userData || o.userData.indexGltf === undefined) return;
    if (!porteurs.has(o)) return;
    let plusBas = false;
    for (const enfant of o.children) {
      enfant.traverse((n) => {
        if (n.userData && n.userData.indexGltf !== undefined
            && porteurs.has(n)) plusBas = true;
      });
    }
    if (plusBas) return;
    pieces.push(o);
  });
  return pieces;
}

/* ── le rangement, et il est DÉLIBÉRÉMENT bête ──────────────────────────────
   Des étagères, par ordre de surface décroissante. On ne cherche PAS
   l'optimalité : un rangement optimal est NP-difficile, et surtout il serait
   ILLISIBLE — les pièces changeraient de voisin au moindre changement de
   modèle. On cherche qu'on VOIE les douze pièces séparées, du plus gros au
   plus petit, à marge constante.

   FONCTION PURE, sans three.js ni DOM : c'est ce qui la rend mesurable hors
   navigateur. Elle prend des empreintes {cle, l, p} et rend des CENTRES de
   case, recentrés sur l'origine. */
export function rangerEnEtageres(boites, marge) {
  const tri = [...boites].sort((a, b) => (b.l * b.p) - (a.l * a.p));
  const aire = tri.reduce((s, b) => s + b.l * b.p, 0);
  const plusLarge = tri.reduce((m, b) => Math.max(m, b.l), 0);
  /* La largeur visée ne descend JAMAIS sous la plus large des pièces : sinon
     celle-ci ouvrirait une étagère à elle seule à chaque tour, et l'étalement
     dégénérerait en colonne. */
  const cible = Math.max(plusLarge, Math.sqrt(aire) * ELANCEMENT);
  const places = [];
  let x = 0, z = 0, profondeurEtagere = 0, largeur = 0;
  for (const b of tri) {
    if (x > 0 && x + b.l > cible) {
      largeur = Math.max(largeur, x - marge);
      x = 0;
      z += profondeurEtagere + marge;
      profondeurEtagere = 0;
    }
    places.push({ cle: b.cle, x: x + b.l / 2, z: z + b.p / 2, l: b.l, p: b.p });
    x += b.l + marge;
    profondeurEtagere = Math.max(profondeurEtagere, b.p);
  }
  largeur = Math.max(largeur, x - marge);
  const profondeur = z + profondeurEtagere;
  /* Recentré sur l'origine : le plateau y est posé, et la caméra du canevas
     cadre sur la boîte englobante du modèle. Un étalement qui partirait dans
     un coin donnerait un plateau décentré sans rien y gagner. */
  for (const p of places) {
    p.x -= largeur / 2;
    p.z -= profondeur / 2;
  }
  return { places, largeur: Math.max(0, largeur),
           profondeur: Math.max(0, profondeur) };
}

/* ── la mise en place, DE BOUT EN BOUT et SANS three.js ─────────────────────
   Choisir le plan, ranger, et rendre le DÉCALAGE de chaque pièce. Tout ce que
   l'étalement décide vit ici.

   POURQUOI CETTE FONCTION EXISTE, et ce n'est pas du rangement de code : ces
   trois pas étaient écrits DANS etaler(), qui manipule des Object3D et ne
   tourne donc que dans un navigateur. Deux erreurs de suite y sont passées —
   les mauvaises pièces, puis le mauvais plan — parce qu'aucun banc ne pouvait
   les EXÉCUTER : un miroir de texte lit une ligne, il ne voit pas une carte
   rester debout. Séparée, la décision se mesure hors navigateur sur les cotes
   VRAIES du modèle de l'utilisateur, et un banc l'y tient.

   Elle ne prend que des nombres : [{cle, taille, centre, bas}], trois points
   {x, y, z}. Elle rend {axe, marge, largeur, profondeur, decalages}, où
   `decalages` va de la clé de pièce à un {x, y, z} exprimé DANS LE MONDE —
   c'est etaler() qui le ramènera dans l'espace du parent. */
export function disposer(mesurees) {
  const axe = axeEmpile(mesurees.map((m) => m.taille));
  const [a1, a2] = AXES.filter((a) => a !== axe);
  const plusGrande = Math.max(...mesurees.map(
    (m) => Math.max(m.taille[a1], m.taille[a2]))) || 1;
  const marge = MARGE_RELATIVE * plusGrande;
  const plan = rangerEnEtageres(mesurees.map(
    (m) => ({ cle: m.cle, l: m.taille[a1], p: m.taille[a2] })), marge);
  const parCle = new Map(plan.places.map((c) => [c.cle, c]));
  const decalages = new Map();
  for (const m of mesurees) {
    const place = parCle.get(m.cle);
    const d = { x: 0, y: 0, z: 0 };
    /* Les deux axes du PLAN portent le rangement, le troisième pose la pièce
       AU CONTACT du plateau — son minimum sur cet axe tombe à zéro. */
    d[a1] = place.x - m.centre[a1];
    d[a2] = place.z - m.centre[a2];
    d[axe] = -m.bas[axe];
    decalages.set(m.cle, d);
  }
  return { axe, marge, decalages,
           largeur: plan.largeur, profondeur: plan.profondeur };
}

/* ── un décalage du MONDE, ramené dans l'espace local d'un parent ──────────
   DERNIER MAILLON DE LA CHAÎNE DE PLACEMENT, et le plus discret. Un nœud glTF
   imbriqué sous un nœud qui tourne ou change d'échelle ne reçoit pas le
   décalage monde tel quel : posé sans conversion, il envoie la pièce
   ailleurs.

   ET IL DORT SUR LE MODÈLE COURANT. `mesh_edit._ROT["Y"]` est l'IDENTITÉ :
   sur une réparation en Y à l'échelle 1 — le cas mesuré — cette fonction est
   un no-op, et la remplacer par le décalage brut ne changerait pas un pixel.
   Le jour où l'utilisateur choisit « Z (Blender, Unreal) » dans le panneau
   Fiche, l'enveloppe de réparation porte une rotation de 90° et TOUTES les
   pièces vivent dessous : elle est alors la seule chose qui tienne. C'est
   pourquoi sa part calculatoire est PURE et exécutée au banc contre la
   matrice que `_matrice(_ROT["Z"], s, t)` produit vraiment — la leçon de
   `disposer`, appliquée au maillon qui restait hors de portée.

   POURQUOI LE BLOC 3×3 SUFFIT. Avec M = [A t ; 0 1], l'inverse vaut
   [A⁻¹ −A⁻¹t ; 0 1], si bien que M⁻¹·d − M⁻¹·0 = A⁻¹·d : la translation
   s'annule d'elle-même. On inverse donc A, et rien d'autre. (L'écriture
   précédente transformait deux points et soustrayait — le même nombre, par
   un chemin qui traînait la translation pour l'annuler ensuite.)

   `elements` est le tableau de 16 nombres de three.js, rangé en COLONNES. */
export function versLocalLineaire(elements, d) {
  const e = elements;
  const a = e[0], b = e[4], c = e[8];
  const f = e[1], g = e[5], h = e[9];
  const i = e[2], j = e[6], k = e[10];
  const co0 = g * k - h * j, co1 = h * i - f * k, co2 = f * j - g * i;
  const det = a * co0 + b * co1 + c * co2;
  /* Un parent écrasé à zéro sur un axe n'a pas d'inverse. On rend alors le
     décalage TEL QUEL plutôt que des NaN : une pièce mal placée se voit et se
     corrige, une pièce aux coordonnées NaN disparaît de l'écran sans un mot,
     et le modèle passerait pour cassé. */
  if (!det) return { x: d.x, y: d.y, z: d.z };
  const n = 1 / det;
  return {
    x: n * (co0 * d.x + (c * j - b * k) * d.y + (b * h - c * g) * d.z),
    y: n * (co1 * d.x + (a * k - c * i) * d.y + (c * f - a * h) * d.z),
    z: n * (co2 * d.x + (b * i - a * j) * d.y + (a * g - b * f) * d.z),
  };
}

function versLocal(parent, deltaMonde) {
  const d = versLocalLineaire(parent.matrixWorld.elements, deltaMonde);
  return new THREE.Vector3(d.x, d.y, d.z);
}

/* ── le plateau et sa grille ────────────────────────────────────────────────
   Il vit dans la SCÈNE et non dans le modèle : `vider()` de viewer.js ne
   retire que `api.racine`, et un plateau greffé au modèle disparaîtrait avec
   lui sans que personne ne l'ait rangé. Dans la scène, c'est ranger() qui en
   répond — et il le libère, géométrie et matériaux, sans quoi dix bascules
   laisseraient dix plateaux sur la carte.

   Il est dimensionné sur l'EMPREINTE de l'étalement, en unités du modèle.
   Aucune cote de plateau réel n'est écrite ici : voir l'en-tête du fichier. */
function poserPlateau(api, largeur, profondeur, marge, axe) {
  const cote = Math.max(largeur, profondeur, marge) * DEBORD_PLATEAU + marge;
  const groupe = new THREE.Group();
  groupe.name = "plaque-plateau";
  const socle = new THREE.Mesh(
    new THREE.PlaneGeometry(cote, cote),
    new THREE.MeshBasicMaterial({ color: 0x0e1116, transparent: true,
                                  opacity: 0.92 }));
  socle.rotation.x = -Math.PI / 2;
  /* Sous la grille d'un cheveu : coplanaires, les deux clignoteraient
     (z-fighting), et la grille est ce qui doit se lire. Le décalage est
     relatif au côté, faute d'échelle absolue dans un GLB. */
  socle.position.y = -cote * 0.0008;
  const grille = new THREE.GridHelper(cote, DIVISIONS_GRILLE, 0x5b636f, 0x333941);
  grille.material.transparent = true;
  grille.material.opacity = 0.55;
  groupe.add(socle);
  groupe.add(grille);
  /* LA GRILLE NAÎT DANS LE PLAN XZ, normale +Y — c'est la convention de
     GridHelper. On la fait basculer vers le plan d'étalement plutôt que d'en
     fabriquer trois : une rotation de +90° autour de X envoie la normale sur
     +Z, une de −90° autour de Z l'envoie sur +X. */
  if (axe === "z") groupe.rotation.x = Math.PI / 2;
  else if (axe === "x") groupe.rotation.z = -Math.PI / 2;
  /* Et il RECULE d'un cheveu : les pièces sont posées AU CONTACT du plateau
     (leur minimum sur l'axe d'empilement vaut zéro), or les pièces mesurées
     sur le modèle réel ont une épaisseur NULLE. Coplanaires, la carte et la
     grille clignoteraient. */
  groupe.position[axe] = -cote * RECUL_PLATEAU;
  api.scene.add(groupe);
  return groupe;
}

export function estEtalee(api) {
  return !!(api && _etats.has(api));
}

/* ── étaler ─────────────────────────────────────────────────────────────────
   Rend le compte rendu que le panneau affiche :
     { pieces: [{cle, nom, couleur}], teintes: Map(uuid → css),
       partages, vides, largeur, profondeur, axe }
   `teintes` couvre TOUT le sous-arbre de chaque pièce, pour que le panneau
   Parties sache peindre la pastille d'un maillage comme celle de son nœud.

   `axe` EST RENDU, et il ne l'était pas : c'est l'axe d'EMPILEMENT choisi par
   axeEmpile(), donc la normale du plan d'étalement — l'information sans
   laquelle personne, hors de ce module, ne peut dire laquelle des vues
   nommées du canevas regarde la plaque en face. Le calculer une seconde fois
   au-dehors serait le calculer avec d'autres boîtes ; on le rend. */
export function etaler(api) {
  if (!api || !api.racine) return null;
  /* Jamais deux étalements empilés : le second mesurerait des boîtes DÉJÀ
     décalées et enverrait les pièces deux fois plus loin.

     GARDE DÉFENSIVE, ET AUCUN APPELANT NE L'ATTEINT : basculerPlaque() teste
     `PLQ.active` avant d'appeler, et les deux états ne peuvent pas diverger
     — oublierPlaque() les remet à zéro ensemble. Elle est écrite pour qui
     appellerait etaler() deux fois de suite depuis ailleurs ; elle n'est donc
     pas mesurée, et il ne faut pas la lire comme si elle l'était. */
  if (_etats.has(api)) ranger(api);
  /* Les boîtes se lisent dans le monde : sans cette mise à jour, une pièce
     dont la matrice n'a pas encore été recalculée serait mesurée à sa pose
     d'avant. */
  api.racine.updateMatrixWorld(true);

  const mesurees = [];
  let vides = 0;
  for (const piece of piecesDe(api)) {
    const boite = new THREE.Box3().setFromObject(piece);
    /* Un nœud sans la moindre géométrie n'a pas d'empreinte : lui donner une
       case le ferait occuper de la place sur la plaque sans rien y montrer,
       et son œil ne commanderait rien de visible. On le compte, on ne
       l'étale pas. */
    if (boite.isEmpty()) { vides++; continue; }
    mesurees.push({
      piece, cle: piece.userData.indexGltf,
      nom: piece.name || `noeud_${piece.userData.indexGltf}`,
      taille: boite.getSize(new THREE.Vector3()),
      centre: boite.getCenter(new THREE.Vector3()),
      /* `boite.min` est gardé PAR RÉFÉRENCE, sans copie : la Box3 est locale
         à ce tour de boucle et personne ne la réécrit. (Un `.clone()` serait
         plus prudent, et un banc interdit ici le mot même de clone — la garde
         qui jure qu'aucun MATÉRIAU n'est cloné.) */
      bas: boite.min,
    });
  }
  if (!mesurees.length) return null;

  /* TOUTE la décision d'étalement, en un appel et sans three.js — c'est ce
     qui la rend mesurable hors navigateur (voir disposer). */
  const mise = disposer(mesurees);

  const etat = { berceaux: [], materiaux: [], plateau: null };
  const teintes = new Map();
  const usage = new Map();          // uuid de matériau → Set de clés de pièce
  const pieces = [];

  for (const m of mesurees) {
    const parent = m.piece.parent;
    const rang = parent.children.indexOf(m.piece);
    const berceau = new THREE.Group();
    berceau.name = `plaque_${m.cle}`;
    /* LE DÉCALAGE, ET IL EST TOUT ENTIER ICI. `berceau.position` et rien
       d'autre : la pièce garde sa pose au bit près, et la porte d'écriture
       de l'Établi, qui lit `o.position`, ne peut pas voir passer ce
       décalage. `-m.bas` pose chaque pièce SUR le plateau plutôt que de les
       laisser flotter à leur altitude d'assemblage. */
    const d = mise.decalages.get(m.cle);
    const decalage = new THREE.Vector3(d.x, d.y, d.z);
    berceau.position.copy(versLocal(parent, decalage));
    berceau.add(m.piece);
    parent.add(berceau);
    /* Le berceau reprend la PLACE de la pièce dans la fratrie. L'ordre de
       parcours n'est pas décoratif : c'est lui qui ordonne le panneau
       Parties, et une liste qui se réordonne quand on bascule la vue
       donnerait l'impression que le modèle a changé. */
    const j = parent.children.indexOf(berceau);
    parent.children.splice(j, 1);
    parent.children.splice(rang, 0, berceau);

    const teinte = couleurDePiece(m.cle);
    const css = `#${teinte.getHexString()}`;
    m.piece.traverse((o) => {
      teintes.set(o.uuid, css);
      if (!o.isMesh) return;
      for (const mat of materiauxDe(o)) {
        if (!usage.has(mat.uuid)) usage.set(mat.uuid, new Set());
        usage.get(mat.uuid).add(m.cle);
        if (!mat.color) continue;       /* un matériau sans couleur, au cas où */
        /* Posé UNE fois, avant la première altération — même dette et même
           remède que `opaciteOrigine` dans selection.js : relire la couleur
           à chaque étalement mémoriserait la TEINTE, et « Assemblé » rendrait
           un modèle définitivement colorié. */
        if (mat.userData.couleurOrigine === undefined) {
          mat.userData.couleurOrigine = mat.color.getHex();
          etat.materiaux.push(mat);
        }
        mat.color.copy(teinte);
        mat.needsUpdate = true;
      }
    });

    etat.berceaux.push({ berceau, piece: m.piece, parent, rang, cle: m.cle,
                         visible: m.piece.visible });
    pieces.push({ cle: m.cle, nom: m.nom, couleur: css, uuid: m.piece.uuid });
  }

  etat.plateau = poserPlateau(
    api, mise.largeur, mise.profondeur, mise.marge, mise.axe);
  _etats.set(api, etat);

  /* LA LIMITE, MESURÉE ET RENDUE — pas cachée. glTF PARTAGE les matériaux :
     deux pièces qui se partagent le leur ne peuvent pas recevoir deux
     couleurs, la dernière parcourue gagne, et la teinte « fuit » sur sa
     voisine. C'est exactement la limite d'`isoler()`, et on la traite
     pareil : on ne CLONE PAS (il faudrait aussi libérer les clones, et le
     `vider()` de viewer.js ne saurait pas les retrouver), on RÉDUIT LA
     PROMESSE et on la compte, pour que le panneau puisse la dire. La
     pastille de la liste, elle, ne ment jamais : elle est calculée, pas lue
     sur le maillage. */
  const partages = [...usage.values()].filter((s) => s.size > 1).length;
  return { pieces, teintes, partages, vides, axe: mise.axe,
           largeur: mise.largeur, profondeur: mise.profondeur };
}

/* ── ranger : rendre le modèle intact, SANS RECHARGER ────────────────────────
   Aucun `charger()`, aucun réseau : le GLB de l'utilisateur pèse plusieurs
   mégaoctets et repasserait par le verrou de sérialisation de l'Établi. Tout
   ce que l'étalement a posé, il le reprend — le berceau, la teinte, la
   visibilité, le plateau — et il le reprend DANS L'ORDRE INVERSE, la pièce
   retrouvant sa place exacte dans la fratrie. */
export function ranger(api) {
  const etat = api && _etats.get(api);
  if (!etat) return false;
  _etats.delete(api);
  for (const e of etat.berceaux) {
    e.piece.visible = e.visible;
    /* Le berceau a pu partir avec son modèle (un `vider()` entre-temps) :
       on ne rend alors que ce qui reste à rendre. */
    if (e.berceau.parent === e.parent) {
      e.parent.remove(e.berceau);
      e.parent.add(e.piece);
      const j = e.parent.children.indexOf(e.piece);
      e.parent.children.splice(j, 1);
      e.parent.children.splice(e.rang, 0, e.piece);
    }
    e.berceau.clear();
  }
  for (const mat of etat.materiaux) {
    if (mat.userData.couleurOrigine === undefined) continue;
    mat.color.setHex(mat.userData.couleurOrigine);
    /* EFFACÉ, et ce n'est pas de la coquetterie : laissé en place, il ferait
       sauter la mémorisation du prochain étalement (« déjà connu »), et ce
       matériau-là ne serait plus jamais restauré. */
    delete mat.userData.couleurOrigine;
    mat.needsUpdate = true;
  }
  if (etat.plateau) {
    etat.plateau.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      for (const mat of materiauxDe(o)) mat.dispose();
    });
    api.scene.remove(etat.plateau);
  }
  return true;
}

/* ── ce que l'étalement a DÉPLACÉ, pour qui doit lire des coordonnées ────────
   Le décalage d'étalement d'un objet, exprimé DANS LE MONDE, et zéro hors
   plaque. Elle vit ICI et non chez l'appelant, et c'est le fond de l'affaire :
   le berceau est un détail INTERNE de ce module — c'est etaler() qui le glisse
   entre la pièce et son parent, et lui seul qui sait où il est. Une page qui
   le retrouverait en supposant « le berceau est le parent de la pièce »
   énoncerait un invariant que rien ne lui garantit ; le jour où l'étalement
   glisserait un second Group (une teinte, un socle par pièce, l'imbrication
   qu'évoque déjà le commentaire de piecesDe), ses coordonnées deviendraient
   fausses DU DÉCALAGE EXACT — donc plausibles, avec l'autorité du chiffre.

   ICI, RIEN N'EST DEVINÉ : `etat.berceaux` retient déjà `{berceau, piece,
   parent}`, les trois objets dont la réponse a besoin, et montrerPiece() s'en
   sert deux lignes plus bas.

   POURQUOI CE N'EST PAS UNE SOUSTRACTION NAÏVE. Le berceau porte un décalage
   LOCAL ; sous un parent qui tourne ou change d'échelle — le cas d'une
   réparation en Z, où `_ROT["Z"]` n'est plus l'identité — le décalage MONDE en
   diffère. Avec `berceau.matrixWorld = parent.matrixWorld · T(d)`, la
   différence des deux colonnes de translation vaut `A_parent · d` : la
   translation du parent s'annule d'elle-même, et il reste le décalage exact.
   C'est la même algèbre que versLocalLineaire, prise dans l'autre sens.

   `etale: true` DIT que la lecture n'a PAS pu être corrigée — un nœud qui
   CONTIENT des pièces, dont la boîte englobe des pièces déjà envolées. On le
   marque plutôt que de le taire : un chiffre douteux annoncé vaut mieux qu'un
   chiffre faux muet.

   ELLE NE MODIFIE RIEN, comme tout ce module : elle LIT trois matrices. */
export function decalageEtalement(api, objet) {
  const zero = new THREE.Vector3();
  const etat = api && _etats.get(api);
  if (!etat) return { decalage: zero, etale: false };
  /* On remonte jusqu'à une pièce INSCRITE dans l'état — pas jusqu'à un objet
     qui ressemblerait à une pièce. Les pièces ne s'imbriquent pas (piecesDe
     l'assure), donc au plus une correspond. */
  const parPiece = new Map(etat.berceaux.map((e) => [e.piece, e]));
  let n = objet;
  while (n && !parPiece.has(n)) n = n.parent;
  const e = n && parPiece.get(n);
  /* Un berceau détaché — un vider() passé par là — ne décrit plus rien. */
  if (!e || e.berceau.parent !== e.parent) return { decalage: zero, etale: !e };
  return {
    decalage: e.berceau.getWorldPosition(new THREE.Vector3())
      .sub(e.parent.getWorldPosition(new THREE.Vector3())),
    etale: false,
  };
}

/* L'œil de la liste. `visible` de three.js, et rien d'autre : ni opacité (qui
   passerait par les matériaux, donc par la limite du partage), ni retrait de
   la scène (qui ferait perdre sa place à la pièce). Restauré par ranger(). */
export function montrerPiece(api, cle, visible) {
  const etat = api && _etats.get(api);
  if (!etat) return false;
  const e = etat.berceaux.find((x) => x.cle === Number(cle));
  if (!e) return false;
  e.piece.visible = !!visible;
  return true;
}
