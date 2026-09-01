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

/* ── quelles pièces ─────────────────────────────────────────────────────────
   Les nœuds glTF les plus HAUTS, et eux seuls. Un nœud indexé vivant sous un
   autre nœud indexé recevrait un second berceau, et son décalage s'ajouterait
   à celui de son parent : la pièce partirait deux fois plus loin que sa
   voisine, pour une raison invisible. C'est aussi la granularité que le
   serveur extrait — une pièce de la plaque est une pièce qu'on peut séparer. */
export function piecesDe(api) {
  const hauts = [];
  if (!api || !api.racine) return hauts;
  api.racine.traverse((o) => {
    if (o === api.racine) return;
    if (!o.userData || o.userData.indexGltf === undefined) return;
    for (let n = o.parent; n && n !== api.racine; n = n.parent) {
      if (n.userData && n.userData.indexGltf !== undefined) return;
    }
    hauts.push(o);
  });
  return hauts;
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

/* Un déplacement exprimé dans le MONDE, ramené dans l'espace local d'un
   parent. Indispensable dès qu'un nœud glTF est imbriqué sous un nœud qui
   tourne ou change d'échelle : poser le décalage monde tel quel y enverrait
   la pièce ailleurs. On transforme deux points et on soustrait — la
   translation du parent s'annule, sa rotation et son échelle non. */
function versLocal(parent, deltaMonde) {
  const inv = new THREE.Matrix4().copy(parent.matrixWorld).invert();
  const origine = new THREE.Vector3(0, 0, 0).applyMatrix4(inv);
  return deltaMonde.clone().applyMatrix4(inv).sub(origine);
}

/* ── le plateau et sa grille ────────────────────────────────────────────────
   Il vit dans la SCÈNE et non dans le modèle : `vider()` de viewer.js ne
   retire que `api.racine`, et un plateau greffé au modèle disparaîtrait avec
   lui sans que personne ne l'ait rangé. Dans la scène, c'est ranger() qui en
   répond — et il le libère, géométrie et matériaux, sans quoi dix bascules
   laisseraient dix plateaux sur la carte.

   Il est dimensionné sur l'EMPREINTE de l'étalement, en unités du modèle.
   Aucune cote de plateau réel n'est écrite ici : voir l'en-tête du fichier. */
function poserPlateau(api, largeur, profondeur, marge) {
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
  api.scene.add(groupe);
  return groupe;
}

export function estEtalee(api) {
  return !!(api && _etats.has(api));
}

/* ── étaler ─────────────────────────────────────────────────────────────────
   Rend le compte rendu que le panneau affiche :
     { pieces: [{cle, nom, couleur}], teintes: Map(uuid → css),
       partages, largeur, profondeur }
   `teintes` couvre TOUT le sous-arbre de chaque pièce, pour que le panneau
   Parties sache peindre la pastille d'un maillage comme celle de son nœud. */
export function etaler(api) {
  if (!api || !api.racine) return null;
  /* Jamais deux étalements empilés : le second mesurerait des boîtes DÉJÀ
     décalées et enverrait les pièces deux fois plus loin. */
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
    const taille = boite.getSize(new THREE.Vector3());
    const centre = boite.getCenter(new THREE.Vector3());
    mesurees.push({
      piece, cle: piece.userData.indexGltf,
      nom: piece.name || `noeud_${piece.userData.indexGltf}`,
      l: taille.x, p: taille.z,
      cx: centre.x, cz: centre.z, bas: boite.min.y,
    });
  }
  if (!mesurees.length) return null;

  const plusGrande =
    Math.max(...mesurees.map((m) => Math.max(m.l, m.p))) || 1;
  const marge = MARGE_RELATIVE * plusGrande;
  const plan = rangerEnEtageres(
    mesurees.map((m) => ({ cle: m.cle, l: m.l, p: m.p })), marge);
  const parCle = new Map(plan.places.map((c) => [c.cle, c]));

  const etat = { berceaux: [], materiaux: [], plateau: null };
  const teintes = new Map();
  const usage = new Map();          // uuid de matériau → Set de clés de pièce
  const pieces = [];

  for (const m of mesurees) {
    const place = parCle.get(m.cle);
    const parent = m.piece.parent;
    const rang = parent.children.indexOf(m.piece);
    const berceau = new THREE.Group();
    berceau.name = `plaque_${m.cle}`;
    /* LE DÉCALAGE, ET IL EST TOUT ENTIER ICI. `berceau.position` et rien
       d'autre : la pièce garde sa pose au bit près, et la porte d'écriture
       de l'Établi, qui lit `o.position`, ne peut pas voir passer ce
       décalage. `-m.bas` pose chaque pièce SUR le plateau plutôt que de les
       laisser flotter à leur altitude d'assemblage. */
    berceau.position.copy(versLocal(parent,
      new THREE.Vector3(place.x - m.cx, -m.bas, place.z - m.cz)));
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

  etat.plateau = poserPlateau(api, plan.largeur, plan.profondeur, marge);
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
  return { pieces, teintes, partages, vides,
           largeur: plan.largeur, profondeur: plan.profondeur };
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
