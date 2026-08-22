# Cardforge — phase 2d : la carte COMPLÈTE dans le graphe (recto+verso) + ergonomie du canvas

Demande utilisateur (22/08, verbatim résumé) : « rend le graphe logique avec les
couches exportées, je dois pouvoir reconstruire la carte entièrement dans le
graph, y compris la face verso — remonté comme l'atlas dans la section
export 3d » ; plus trois gestes d'ergonomie : en vue graphe, le cadre
inférieur de l'aperçu est superflu ; le rail des modules et la colonne carte
doivent être escamotables « comme dans le reste de l'application ». Puis la
phase 3.

**Lecture actée de « remonté comme l'atlas »** : le verso du graphe suit LES
CONVENTIONS de la carte deux-faces de l'Export 3D (P8) — mêmes règles de
miroir, d'enroulement et de lisibilité que l'atlas impose à ses îlots — pas
une injection du GLB P9 dans l'écran P8 (le pipeline P8 part de l'atlas, pas
d'un GLB). Si la revue ou l'utilisateur lit autrement, amender ICI d'abord.

## Faits de reconnaissance (les ancres qui décident — relues le 22/08)

- **P8 fait foi pour le verso** : recto plat +z sens direct / verso plat −z
  sens INVERSE (solid.py:532-545) ; `uv_back` MIROIR EN U (`hw - x`,
  solid.py:513-522 — « vu de -Z la droite de l'écran est -x ») = la carte se
  retourne GAUCHE-DROITE comme une vraie carte ; l'atlas pose les deux faces
  SANS retournement de pixels (mod-gltf.js:614-617), c'est la géométrie qui
  porte le miroir ; contrôle de lisibilité `face_orientation`
  (solid.py:610-649) ; tangentes : formule Lengyel w = signe de
  dot(cross(N,T),B) (gltf_builder.py:481-485, recopiée contract.py:409-460).
- **P9 aujourd'hui** : `side` normalisé (forge3d.py:454-457) mais consommé
  UNIQUEMENT comme sélecteur de fichier (`_layer_filename`
  forge3d_apercu.py:200-206 ; manifeste verso lu seulement pour la boîte
  mesh3d forge3d.py:1380-1387). Trois verrous structurels : `quad_mesh`
  normale +z figée (forge3d_scene.py:41), `PLANE_DEPTH_MM=(0.0,5.0)` et
  `TRANSFORM_Z_MM=(0.0,10.0)` (forge3d.py:123,179), rotation scalaire +z
  seulement (`_quat_z`, forge3d_scene.py:441-443). TANGENT constant
  `[1,0,0,-1]` valable pour le quad frontal (forge3d_scene.py:1015-1029).
- **Seed/palette recto-seuls** : `LAST_MANIFEST` = manifeste RECTO par
  doctrine (mod-forge3d.js:307-311, 632-648), boot recharge front
  (mod-forge3d.js:770), `couchesRestantes` filtre sur `man.side`
  (mod-forge3d.js:3753-3767), `defaultGraph` empile i×0,35 mm
  (mod-forge3d.js:261-275). `naitCouche` sait déjà poser `side` (:3812) —
  plomberie morte à réveiller.
- **Shell** : rail = core.js `buildRail` (:937-955) sur `#rail`
  (index.html:59), largeurs `--rail-w: 188px`/`--stage-w: 384px`
  (cardforge.css:26-27) dans la grille `.cf` (cardforge.css:94-95) ; la
  colonne carte `.stage` est CORE (index.html:63-81, core.js:995-1040,
  1528-1557) ; AUCUN escamotage manuel n'existe ; le patron de l'app =
  chevron + bascule de largeur + transition + contenu démonté replié
  (frontend/src/studio/shell.jsx:31-122) ; cardforge.css n'est PAS soumis à
  R4 (lint_cardforge.py:768-780 — R13 seulement) ; le harnais de contrat
  n'épingle que l'EXISTENCE de `#rail` (qa/contract.html:32, visuels
  display:none :15) ; persistance famille `dz_cf_*` (LS_VUE
  mod-forge3d.js:150, patron core.js:144-145).
- **P9 sections** : shell() empile 4 cartes (mod-forge3d.js:364-437) — export,
  Graphe 3D, « Construire » (:420-426), « Aperçu » (:428-435) ; `paintVue`
  (:1551-1588) bascule canvas/liste ; `hoteApercu` (:5102-5107) replie le
  viewer vers `#cf-forge3d-view` quand il n'y a pas d'hôte canvas ;
  `majSectionApercu` (:5145-5166) écrit « où il est parti ».

## Décision de conception du verso — UNE règle de placement, zéro nouveau maillage

Un élément dont la couche source est `side="back"` est construit DANS L'ESPACE
RECTO (mêmes `quad_mesh`/`relief_mesh`/fit mesh3d, mêmes UV, même TANGENT
local) puis posé par un TRS « verso » :

1. **rotation propre de 180° autour de +Y** composée à la rotation utilisateur
   (`R = R_y(π) ∘ R_z(rot_deg)`) — elle réalise d'un seul geste la normale
   −z, le miroir GAUCHE-DROITE physique (l'équivalent exact de `uv_back`,
   déterminant +1, enroulement préservé) et laisse le TANGENT local valide
   (le repère tourne en bloc — la règle w=−1 de forge3d_scene.py:1015-1029
   est LOCALE) ;
2. **z opposé** : la profondeur d'empilement et le `z_mm` d'un `transform`
   s'appliquent en NÉGATIF (la pile verso descend sous le plan médian z=0,
   symétrique de la pile recto — l'analogue du ±épaisseur/2 de P8,
   solid.py:496-498). Les CLAMPS ne changent pas : les valeurs restent ≥ 0,
   le SIGNE appartient à la règle de côté (aucun changement de vocabulaire,
   aucun octet du bloc miroir CF-FORGE3D-NODES).
3. x/y d'un `transform` verso : appliqués APRÈS le retournement dans le plan
   de la face regardée (x_mm pousse vers la droite DU VERSO vu de −z) — la
   règle qui rend l'édition WYSIWYG des deux côtés ; l'implémenteur le prouve
   au banc (positions monde via `glb_scene_mesh(world=True)`), pas à l'œil.
4. Contrôle de LISIBILITÉ à la P8 : un test qui mesure, sur les positions
   monde du quad verso, que « à droite de l'image » = « −x monde » (l'esprit
   de `face_orientation` solid.py:618-649, adapté aux quads P9).

### Task 1 : backend — la règle de côté (forge3d_apercu + forge3d_scene + tests)

**Files:** forge3d_apercu.py (élément/TRS), forge3d_scene.py (si le quat
composé demande un helper — sinon rien), forge3d.py (rien au vocabulaire),
test_cards_forge3d.py.

- [ ] RED : un graphe 2 couches (front plane z 0,35 + back plane z 0,35) →
      build3d → `glb_scene_mesh(world=True)` : le quad back a TOUS ses z < 0,
      le front tous > 0 ; normales monde opposées ; lisibilité verso
      (image-droite = −x) ; un `transform` verso x_mm=+5 pousse le centre
      vers −x monde ; STL mixte toujours prouvé-ou-refusé ; node-preview d'un
      élément back seul → 200 et z ≤ 0.
- [ ] Implémentation : `element_local` reçoit le côté (il a déjà la couche) ;
      `_node_trs` compose `R_y(π)` et NÉGATIVISE les z pour les chaînes back ;
      relief back extrude vers −z (par la rotation, pas par un maillage
      neuf) ; mesh3d back : même fit, même flip.
- [ ] Mutation : quat Y remplacé par X (le verso se retourne tête-bêche → la
      lisibilité rougit), signe du z oublié (chevauchement des piles),
      rot_deg composé dans le mauvais ordre.

### Task 2 : frontend — les deux manifestes, le seed complet, la palette

**Files:** mod-forge3d.js, mod-forge3d.css (si étiquette), test (pins+banc).

- [ ] `LAST_MANIFEST` garde sa doctrine (identité = recto) ; s'ajoute
      `MANIFEST_BACK` chargé au boot et à l'export (`layers_{label}_back.json`,
      404 toléré = pas de verso exporté, la palette le DIT).
- [ ] `defaultGraph` : paires recto PUIS paires verso (`side:"back"`), même
      escalier 0,35 ; en-têtes de nœuds montrent déjà « · verso » (le libellé
      dérive de side) — vérifier, sinon l'ajouter ; seedLayout : colonne
      couches verso SOUS les recto (lisible sans zoom).
- [ ] `couchesRestantes` propose LES DEUX côtés (suffixe « (verso) »),
      dédoublonnage PAR CÔTÉ ; `naitCouche` pose le side de l'entrée choisie.
- [ ] Vignettes : déjà side-aware par nom de fichier — pin.
- [ ] Banc : seed complet 2×6 couches → 26 nœuds/25 arêtes ; palette vide des
      deux côtés quand tout est posé ; naissance verso câblée.

### Task 3 : core — rail et colonne carte escamotables

**Files:** core.js, cardforge.css, index.html (2 boutons), qa/test_core_contract.mjs (pins), qa/contract.html si un ancrage manque.

- [ ] Patron shell.jsx transposé vanilla : bouton chevron dans `.rail` (bas ou
      tête) → classe `rail-replie` sur `.cf` → `--rail-w` étroit (~46px,
      `.ri-t` masqué, numéros+icônes seuls) ; bouton dans `.stage-head` →
      `stage-replie` → `--stage-w` bande étroite (~36px) au contenu démonté
      (canvas/boutons cachés, un chevron vertical pour rouvrir) ; transitions
      de largeur ; AUCUNE règle hors cardforge.css (R4 n'y mord pas, R13 si).
- [ ] Persistance `dz_cf_rail` / `dz_cf_stage` (patron LS_VUE — présentation,
      jamais dans le document).
- [ ] Pins contrat : les deux boutons existent, la classe bascule, le storage
      écrit ; le harnais garde ses display:none (zéro géométrie affirmée).
- [ ] Octets core.js/index.html vérifiés après édition (leçon 19/08 : NUL/CRLF).

### Task 4 : P9 — la vue canvas se suffit (sections basses escamotées)

**Files:** mod-forge3d.js, mod-forge3d.css, test.

- [ ] En VUE canvas : les sections « Construire » (:420-426) ET « Aperçu »
      (:428-435) sont MASQUÉES — leurs fonctions vivent dans le nœud artefact
      (Construire, figer, bordereau, viewer T5/T6). GARDE : si le canvas n'a
      PAS d'hôte artefact (`.cf-forge3d-art-view` absent — graphe vide ou
      artefact supprimé), la section « Aperçu » RESTE visible (seul hôte du
      viewer — `hoteApercu` :5102 y replie déjà). Bascule vers liste : tout
      revient (`remonteApercu` :1586 inchangé).
- [ ] Le masquage vit dans `paintVue` (le dispatcher d'état de vue — :1551),
      classe `.hidden` sur les `<section>` parentes ; `majSectionApercu`
      inchangé (il ne parle qu'en vue liste).
- [ ] Pins : source (paintVue masque/démasque les DEUX ids avec la garde) +
      banc si extractible.

### Task 5 : intégration 2d

- [ ] Suite `-Filter cards` 10/10, lint intégral 0, `--geom`, `node --check`.
- [ ] cf_deploy -Backend + -Check 0 écart (pas de bundle cette phase — le
      patch card3d ne bouge pas).
- [ ] Navigateur (les vérifs DOM/réseau du patron 2c ; volet masqué assumé) :
      seed complet recto+verso visible, naissance verso, build3d gratuit
      (planes seuls) → GLB deux faces (octets : deux quads, z signés — via
      l'API), escamotage rail/stage (classes+storage), vue canvas sans les
      deux sections basses, bascule liste = tout revient.
- [ ] Plan+mémoire+push. Restes à l'œil ajoutés à la liste 2 min (lisibilité
      verso au viewer, largeur repliée agréable).

## Auto-revue du plan

- Le miroir gauche-droite par R_y(π) est ÉQUIVALENT à `uv_back` de P8 (même
  transformation physique, portée par la géométrie au lieu des UV — l'atlas
  P8 ne retourne pas ses pixels non plus, mod-gltf.js:614-617). Le test de
  lisibilité (Task 1) est la preuve, pas l'intention.
- Aucun changement de vocabulaire ni de clamps → le bloc miroir et le bundle
  restent intacts ; la 409-collision, les jobs payants, la Bibliothèque ne
  sont pas touchés.
- Les quatre tâches sont indépendantes deux à deux (1↔2 couplées par le seed,
  3 et 4 isolées) ; l'ordre 1→2→3→4→5 minimise les rebases.
- Risques nommés : composition de quaternions (ordre R_y∘R_z — banc, pas
  l'œil) ; core.js gelé (registre intouché, octets vérifiés) ; le harnais de
  contrat ne doit JAMAIS recevoir de géométrie (display:none conservé).
