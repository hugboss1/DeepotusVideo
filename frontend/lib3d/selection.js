/* Sélection et isolation dans le canevas partagé.
   Ce module NE PARLE À AUCUNE ROUTE : isoler est un AFFICHAGE, il ne fabrique
   aucun GLB et ne touche pas le disque. C'est l'Établi qui, sur un clic
   explicite, enverra les index au serveur — et c'est Python qui écrira. Un
   banc de test_etabli_canevas.py interdit structurellement qu'une requête
   réseau apparaisse ici ; il vaut plus que le présent commentaire, qu'un
   copier-coller pressé enjamberait sans le voir. */
"use strict";
import * as THREE from "three";

/* Ce qu'un maillage ÉCARTÉ garde d'opacité. Masquer complètement ferait
   perdre le contexte — on ne saurait plus où la pièce retenue se situe dans
   son modèle ; un fantôme le garde. */
const OPACITE_FANTOME = 0.08;

/* Distance MAXIMALE, en pixels CSS, entre le poser et le relever du pointeur
   pour qu'un geste compte comme un clic. Voir designerAuClic() : c'est ce
   seuil qui sépare « je désigne » de « je tourne le modèle ». */
const TOLERANCE_CLIC = 4;

const _teinte = new THREE.Color(0x4da3ff);

/* Les matériaux d'un objet, qu'il en porte un ou un tableau, jamais de trou :
   `mesh.material` peut être null le temps d'un chargement partiel, et un
   tableau peut avoir des cases vides sur un GLB mal formé. */
const materiauxDe = (o) =>
  (Array.isArray(o.material) ? o.material : [o.material]).filter(Boolean);

/* ── le pont vers le vocabulaire du serveur ────────────────────────────────
   Le serveur raisonne en INDEX DE NŒUD glTF, three.js en objets. Le pont
   entre les deux existe déjà, et il est EXACT : le GLTFParser tient une Map
   `associations` — Object3D → { nodes, meshes, primitives } — qu'il remplit
   en construisant la scène (LU dans le GLTFLoader vendorisé, three 0.185.1 :
   `parser.associations.get( node ).nodes = nodeIndex`), puis RÉDUIT aux
   objets réellement entrés dans la scène. Celui qui a fabriqué les objets
   sait de quel nœud ils viennent : on le lui DEMANDE.

   L'heuristique par les NOMS — apparier `object.name` avec `json.nodes[i].name`
   — n'est ici qu'un repli, et un mauvais juge : un nœud SANS nom n'obtient
   jamais d'index ; deux nœuds de MÊME nom reçoivent les leurs dans l'ordre de
   parcours de la scène, qui n'est pas forcément le leur ; et GLTFLoader
   déduplique les noms (`createUniqueName`), si bien qu'un `Cube` peut devenir
   `Cube_1` dans l'objet et rester `Cube` dans le document. Or ce pont décide
   quel nœud le serveur EXTRAIRA : se tromper y écrit un GLB sur le mauvais
   maillage, sans que rien ne grince.

   D'où deux règles. La Map d'abord, le nom en secours seulement si elle n'a
   RIEN donné. Et la provenance déclarée dans `userData.indexGltfSource`, pour
   que celui qui enverra ces index sache sur quoi il s'appuie. */
export function indexerNoeuds(api) {
  if (!api || !api.racine) return;
  const parser = api.gltf && api.gltf.parser;
  const assoc = parser && parser.associations;
  let poses = 0;
  if (assoc && typeof assoc.get === "function") {
    api.racine.traverse((o) => {
      const lien = assoc.get(o);
      /* Pas de champ `nodes` : cet objet n'EST pas un nœud du document (la
         racine de scène, ou l'une des primitives d'un maillage à plusieurs
         primitives, qui n'ont qu'un `meshes`). Lui inventer un index serait
         exactement l'erreur que cette fonction existe pour éviter. */
      if (!lien || lien.nodes === undefined) return;
      o.userData = o.userData || {};
      /* On ÉCRASE sans condition : GLTFLoader recopie les `extras` du fichier
         dans userData, un GLB pourrait donc y avoir posé son propre
         `indexGltf`. La Map du chargeur fait autorité, pas le fichier. */
      o.userData.indexGltf = lien.nodes;
      o.userData.indexGltfSource = "associations";
      poses++;
    });
  }
  /* Tout ou rien : dès que la Map a parlé, on ne complète PAS les objets
     qu'elle a laissés de côté — elle les a laissés parce qu'ils ne sont pas
     des nœuds, et le repli par nom leur en collerait un. */
  if (poses) return;

  /* REPLI DÉCLARÉ — pour un chargeur qui n'aurait pas rempli la Map (une
     version antérieure, un GLB passé par un plugin exotique). Il vaut mieux
     qu'aucun index du tout, mais il se signale comme tel. */
  const doc = parser && parser.json;
  if (!doc || !doc.nodes) return;
  const parNom = new Map();
  doc.nodes.forEach((n, i) => {
    if (!n.name) return;
    if (!parNom.has(n.name)) parNom.set(n.name, []);
    parNom.get(n.name).push(i);
  });
  api.racine.traverse((o) => {
    const cands = parNom.get(o.name);
    if (!cands || !cands.length) return;
    o.userData = o.userData || {};
    o.userData.indexGltf = cands.shift();
    o.userData.indexGltfSource = "nom";
  });
}

/* ── l'inventaire que le panneau Parties affiche ───────────────────────────
   Trois granularités, parce que les moteurs ne découpent pas pareil : un
   modèle Meshy est souvent un nœud UNIQUE à plusieurs matériaux — le lister
   par nœud n'en montrerait qu'une ligne — quand un Tripo arrive en plusieurs
   nœuds. Aucune des trois ne suffit seule. */
export function inventaire(api) {
  const noeuds = [], maillages = [], materiaux = new Map();
  if (!api || !api.racine) return { noeuds, maillages, materiaux: [] };
  api.racine.traverse((o) => {
    if (o.userData && o.userData.indexGltf !== undefined) {
      noeuds.push({ nom: o.name || `noeud_${o.userData.indexGltf}`,
                    indexGltf: o.userData.indexGltf, uuid: o.uuid });
    }
    if (!o.isMesh || !o.geometry) return;
    const g = o.geometry;
    maillages.push({
      nom: o.name || "maillage", uuid: o.uuid,
      /* Compté ICI, à partir des tampons — jamais lu sur un disque. C'est ce
         qui autorise le panneau à l'interpoler tel quel : contrairement aux
         `triangles` du registre (tâche 4), ce nombre EST un nombre. */
      tris: Math.round((g.index ? g.index.count : g.attributes.position.count) / 3),
      indexGltf: o.userData ? o.userData.indexGltf : undefined,
    });
    for (const m of materiauxDe(o)) {
      if (!materiaux.has(m.uuid)) {
        materiaux.set(m.uuid, { nom: m.name || "matériau", uuid: m.uuid, objets: [] });
      }
      materiaux.get(m.uuid).objets.push(o.uuid);
    }
  });
  return { noeuds, maillages, materiaux: [...materiaux.values()] };
}

/* ── isoler : un affichage, et rien d'autre ────────────────────────────────
   Ce qui est retenu reste plein, le reste passe en fantôme. Rien de retenu
   veut dire « tout revoir » : la restauration n'est pas un second chemin, et
   ne peut donc pas diverger du premier. */
export function isoler(api, gardes, { fantome = OPACITE_FANTOME } = {}) {
  if (!api || !api.racine) return;
  const retenu = new Set(gardes || []);
  const tout = retenu.size === 0;
  api.racine.traverse((o) => {
    if (!o.isMesh) return;
    /* Un objet est retenu par son uuid (granularité « maillage ») ou par son
       index glTF (granularité « nœud »). Le MATÉRIAU, lui, se juge dans la
       boucle ci-dessous : un maillage à plusieurs matériaux peut n'en retenir
       qu'un seul, et c'est précisément le cas d'un Meshy.

       On REMONTE les parents, et ce n'est pas un raffinement : un nœud glTF
       peut n'être qu'un contenant, sans géométrie propre — le cas ordinaire
       d'un modèle hiérarchisé. Retenir ce nœud-là sans son sous-arbre
       n'isolerait RIEN, et passerait le modèle entier en fantôme : la
       granularité « nœud » serait offerte et inopérante. La remontée s'arrête
       à la racine du modèle, au-delà commence la scène du canevas.

       PIÈGE DE TYPE, pour qui viendra ensuite : `indexGltf` est un NOMBRE,
       alors qu'un `dataset.index` relu du DOM est une CHAÎNE. Un Set ne les
       confond pas — `new Set(["5"]).has(5)` est faux. Le panneau, lui, ne
       retient que des uuid, tous chaînes : la branche par index n'attend donc
       que des appelants qui passent de vrais nombres. */
    let objetRetenu = tout;
    for (let n = o; n && !objetRetenu; n = n.parent) {
      objetRetenu = retenu.has(n.uuid)
        || (n.userData && retenu.has(n.userData.indexGltf));
      if (n === api.racine) break;
    }
    for (const m of materiauxDe(o)) {
      const dedans = objetRetenu || retenu.has(m.uuid);
      /* LIMITE ASSUMÉE, et elle est réelle : on agit sur les MATÉRIAUX, or
         glTF les partage. Deux maillages qui se partagent un matériau, dont
         l'un est retenu et l'autre non, ne peuvent pas recevoir deux
         opacités — le dernier parcouru gagne, et l'isolation paraît « fuir »
         sur son voisin. On ne le corrige PAS : cloner les matériaux serait un
         autre métier (il faudrait aussi les libérer, et le vider() de
         viewer.js ne saurait pas retrouver des clones). On réduit la
         promesse : l'isolation est fidèle quand les pièces ne partagent pas
         leurs matériaux — le cas ordinaire d'un maillage découpé en nœuds ;
         sur un modèle qui les partage, elle montre ce qu'un réglage
         d'opacité peut montrer, pas davantage. */
      if (m.userData.opaciteOrigine === undefined) {
        /* Posé UNE fois, avant la première altération : relire l'opacité à
           chaque passage mémoriserait 0,08 dès la deuxième isolation, et
           « tout revoir » rendrait un modèle définitivement fantôme. */
        m.userData.opaciteOrigine = m.opacity;
        m.userData.transparentOrigine = m.transparent;
        m.userData.depthWriteOrigine = m.depthWrite;
      }
      m.transparent = dedans ? m.userData.transparentOrigine : true;
      m.opacity = dedans ? m.userData.opaciteOrigine : fantome;
      /* Sans cette ligne, un fantôme écrit quand même dans le tampon de
         profondeur et découpe des trous dans la pièce retenue qui passe
         derrière lui — l'isolation montrerait alors moins que rien. Restauré
         depuis l'origine, et non forcé à `true` : un matériau légitimement
         transparent n'écrivait déjà pas. */
      m.depthWrite = dedans ? m.userData.depthWriteOrigine : false;
      m.needsUpdate = true;
    }
  });
}

/* Le maillage sous le curseur s'éclaire, les autres retrouvent leur émission
   d'origine — donc un seul surlignage à la fois, sans avoir à retenir le
   précédent. Même limite que ci-dessus sur les matériaux partagés. */
export function surligner(api, uuid) {
  if (!api || !api.racine) return;
  api.racine.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of materiauxDe(o)) {
      if (!m.emissive) continue;      /* un MeshBasicMaterial n'en a pas */
      if (m.userData.emissiveOrigine === undefined) {
        m.userData.emissiveOrigine = m.emissive.getHex();
      }
      m.emissive.setHex(o.uuid === uuid ? _teinte.getHex()
                                        : m.userData.emissiveOrigine);
      m.needsUpdate = true;
    }
  });
}

/* ── clic dans le canevas -> le maillage sous le curseur ───────────────────
   PIÈGE : OrbitControls écoute le MÊME canevas (viewer.js le construit avec
   le <canvas>). Sur un simple `pointerdown`, chaque début de rotation
   désignerait ce qui passe sous le curseur — on ne pourrait plus tourner le
   modèle sans le sélectionner, et le panneau se redessinerait à chaque geste.

   La sélection est donc VOLONTAIRE : bouton gauche (le droit ouvre le menu
   contextuel, le milieu fait le pan d'OrbitControls), même pointeur, et le
   relever doit se produire à moins de TOLERANCE_CLIC pixels du poser.
   Au-delà, le geste était une orbite : on ne désigne rien. */
export function designerAuClic(api, canvas, quand) {
  const ray = new THREE.Raycaster();
  const p = new THREE.Vector2();
  let depart = null;
  canvas.addEventListener("pointerdown", (ev) => {
    depart = ev.button !== 0 ? null
      : { x: ev.clientX, y: ev.clientY, id: ev.pointerId };
  });
  /* Un geste avorté (le navigateur reprend le pointeur pour un défilement,
     par exemple) n'a pas de relever : sans cette ligne, son poser resterait
     armé et le relever d'un geste ULTÉRIEUR serait mesuré depuis lui. */
  canvas.addEventListener("pointercancel", () => { depart = null; });
  canvas.addEventListener("pointerup", (ev) => {
    const d = depart;
    depart = null;
    if (!d || ev.button !== 0 || ev.pointerId !== d.id) return;
    if (Math.hypot(ev.clientX - d.x, ev.clientY - d.y) > TOLERANCE_CLIC) return;
    if (!api.racine) return;
    const r = canvas.getBoundingClientRect();
    p.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    p.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(p, api.camera);
    /* `intersectObject` rend les touches TRIÉES par distance ; le premier
       maillage de la liste est donc bien celui qu'on voit. Le `.find` saute
       ce qui n'en est pas un (une aide, un pivot). */
    const touche = ray.intersectObject(api.racine, true)
      .find((h) => h.object && h.object.isMesh);
    quand(touche ? touche.object : null);
  });
}
