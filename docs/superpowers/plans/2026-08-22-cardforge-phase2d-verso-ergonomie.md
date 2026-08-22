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

   > **Amendé (T1, à l'implémentation)** : le demi-tour passe par le **MILIEU
   > de la carte**, pas par l'origine locale. Nos maillages naissent à
   > `x ∈ [0, w_mm]` (`quad_mesh`/`relief_mesh`, coin de coupe à l'origine) et
   > un nœud glTF tourne autour de SON origine : `R_y(π)` seul enverrait le
   > verso à `x ∈ [−w_mm, 0]` — les deux faces CÔTE À CÔTE au lieu de
   > superposées, une « carte » deux fois trop large, sans qu'aucun test de
   > normale ni de signe de z ne s'en aperçoive. Le retournement est donc
   > `(x, y, z) → (w_mm − x, y, −z)`, soit le même `R_y(π)` plus un `+w_mm` en
   > x DANS LA TRANSLATION du nœud. Ce n'est pas un ajout : c'est LA
   > formulation juste de « retourner la carte », et les trois effets des
   > points 1-3 (normale, miroir, z opposé) en tombent tous les trois — une
   > seule application (`trs_de_face`) au lieu de trois règles à garder
   > d'accord entre elles.
2. **z opposé** : la profondeur d'empilement et le `z_mm` d'un `transform`
   s'appliquent en NÉGATIF (la pile verso descend sous le plan médian z=0,
   symétrique de la pile recto — l'analogue du ±épaisseur/2 de P8,
   solid.py:496-498). Les CLAMPS ne changent pas : les valeurs restent ≥ 0,
   le SIGNE appartient à la règle de côté (aucun changement de vocabulaire,
   aucun octet du bloc miroir CF-FORGE3D-NODES).

   > **Dit, pas corrigé (N6, revue adverse T1)** — un `transform` chaîné
   > ÉCRASE le `depth_mm` du plan, y compris à son défaut `z_mm = 0`
   > (`_node_trs` : « `translate` REMPLACE cette translation »). C'est le
   > comportement de la 2a, il vaut des DEUX côtés, et il a une conséquence
   > que l'écran doit assumer : poser un `transform` neuf (donc à z 0) sur un
   > plan recto ET sur son jumeau verso ramène les deux faces COPLANAIRES à
   > z = 0. Hors périmètre de la T1 (ce serait un changement de sémantique du
   > `transform`, pas une règle de côté) ; écrit ici pour que la T2 et
   > l'écran ne le découvrent pas comme une surprise.
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

- [x] RED : un graphe 2 couches (front plane z 0,35 + back plane z 0,35) →
      build3d → `glb_scene_mesh(world=True)` : le quad back a TOUS ses z < 0,
      le front tous > 0 ; normales monde opposées ; lisibilité verso
      (image-droite = −x) ; un `transform` verso x_mm=+5 pousse le centre
      vers −x monde ; STL mixte toujours prouvé-ou-refusé ; node-preview d'un
      élément back seul → 200 et z ≤ 0.
- [x] Implémentation : `element_local` reçoit le côté (il a déjà la couche) ;
      `_node_trs` compose `R_y(π)` et NÉGATIVISE les z pour les chaînes back ;
      relief back extrude vers −z (par la rotation, pas par un maillage
      neuf) ; mesh3d back : même fit, même flip.
- [x] Mutation : quat Y remplacé par X (le verso se retourne tête-bêche → la
      lisibilité rougit), signe du z oublié (chevauchement des piles),
      rot_deg composé dans le mauvais ordre.

> **Livré (T1)** — la règle vit dans `forge3d_scene.trs_de_face` +
> `_quat_face`, consommée aux **trois** sorties qui placent quelque chose :
> `_node_trs` (nœud d'un élément local), le parent de fusion de
> `_merge_external` (un mesh3d verso) et `apply_fit_inplace` (les sommets
> CUITS du STL, qui n'a pas de nœud pour porter un transform — l'oublier là
> aurait donné deux vérités pour la même carte, le défaut que le transform
> local a déjà coûté une fois en 2b). La DÉCISION (`side == "back"`) reste
> chez les deux fabriques d'élément (`element_local`, `_element_externe`), la
> MÉCANIQUE dans le module scène. Un élément verso porte TOUJOURS un `trs`,
> même sans nœud `transform` : le retournement EST un placement.
> `x_mm`/`z_mm` : le SIGNE appartient à la règle de côté, les bornes n'ont pas
> bougé d'un chiffre. Banc : 5 tests, dont le verdict de **P8 lui-même**
> (`solid.face_orientation`) rendu sur les positions MONDE du GLB P9 —
> `ok: True`, zéro miroir des deux côtés. 97 → 102 verts.

> **Ronde de revue adverse (T1) — la géométrie tenait, LE FILET AVAIT DES
> TROUS.** Verdict : FIX-FIRST, aucun octet de la règle touché. 102 → 104.
>
> · **S1, le seul sérieux** — l'ORDRE de composition à la sortie **STL**
>   n'était épinglé nulle part : un mutant qui retourne AVANT de tourner
>   sortait 102/102 VERT en imprimant une pièce à **52,96 mm** de l'aperçu,
>   bordereau `written: true`. Les trois tests qui touchaient au verso
>   passaient tous à côté (l'un sans `transform`, l'autre en plans donc STL
>   refusé, le troisième ne lisant pas le STL). Correctif : un relief verso
>   qui traverse un `transform` à **37°**, dont le STL est comparé au **GLB de
>   la même construction** (mm contre m, 5 µm de tolérance). Portée MESURÉE et
>   écrite dans le test : cet accord est le SEUL juge de l'inversion, il voit
>   aussi l'oubli, et il ne peut PAS voir une faute de PIVOT (elle déplace les
>   deux sorties du même montant — c'est le jumeau recto qui la tient).
> · **M2 — ma justification de 1b6eb37 était FAUSSE**, et le message de ce
>   commit reste faux dans l'historique : la séparation des deux ordres vaut
>   `2·|sin(rot_deg)|`, donc les angles DÉGÉNÉRÉS sont **0 et 180**, et 90 est
>   au contraire celui qui sépare le MIEUX. 30° est gardé (loin des deux
>   dégénérescences, x et y tous deux non nuls) et la docstring dit désormais
>   la vraie raison.
> · **M3 — deux nœuds/matériaux HOMONYMES** dans un GLB recto+verso
>   (`['cadre', 'cadre']` → Blender importe `cadre.001`, un moteur qui
>   déduplique par nom de matériau FUSIONNE les deux faces). Le nom d'un
>   élément dérive maintenant d'`forge3d_apercu.nom_element` — UNE règle, les
>   deux points d'appel — avec suffixe `_verso`, et `elements_detail` gagne
>   une clé `side`, **uniquement au verso** : GLB recto seul vérifié au
>   sha256, `74d8a2ee…8ef3` / 387 172 o AVANT et APRÈS.
> · **N4** — la tolérance d'empreinte (1e-9 m) cassait sur les formats
>   impériaux (jumbo 88,9 mm laisse 1,5e-9 m de résidu float32) : élargie à
>   1e-8 et le test est désormais PARAMÉTRÉ `poker_eu` + `jumbo`, donc la
>   tolérance est exercée. `_exporter_couches` tire sa trame de `geom_of`.
> · **N5** — la docstring surclamait `face_orientation` : un imposteur
>   `R_x(π)` cohérent le passe (toute rotation de 180° dans le plan préserve
>   `det_img·det_scr`). Portée corrigée — ce sont `_sens_image_droite` et
>   l'empreinte qui portent la distinction gauche-droite / tête-bêche.
> · Hors périmètre, CONSIGNÉ : **N7** (`-0.0` dans le JSON d'un nœud),
>   **N8** (l'aperçu d'un nœud mesh3d sert le GLB BRUT du moteur, non placé —
>   pré-existant 2c), **N6** (voir §Décision point 2).
>
> Mutation, ronde 2 (fichier entier à chaque fois) : `stl_ordre_inverse` tué
> par la NOUVELLE assertion (−44,27 contre +8,686 mm) ; `stl_sans_retournement`
> aussi (6,04 contre 8,686) ; `demi_tour_au_coin` tué par le jumeau recto
> (−63,0 contre 0,0), la nouvelle assertion passant — comme documenté ;
> `nom_sans_verso` tué par 3 tests ; témoin inerte SURVIVANT (104/104).

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

**Files:** core.js, cardforge.css, index.html (1 bouton — voir note), qa/test_core_contract.mjs (pins), qa/contract.html si un ancrage manque.

> **Amendé (T3)** : le plan disait « index.html (2 boutons) » — FAUX pour le
> rail : `buildRail()` fait `rail.innerHTML = ""` à chaque rendu, un bouton
> statique y serait effacé au premier `show()`. Le chevron du rail se crée
> DANS `buildRail` (patron maison : tout le rail est construit en JS, classe
> `rail-fold` et PAS `rail-item` — `syncPanels` balaie `.rail-item` pour
> marquer la pièce active, replier n'est pas choisir) ; seul le chevron de la
> colonne carte est statique dans index.html (patron `.stage-head` :
> `guidesBtn`/`sideBtn`/`shotBtn`), câblé dans `wireStage`.

> **CLOSE (T3 — 683876a + de49bfd, revue combinée : MERGEABLE AS-IS).**
> Largeurs repliées 46 px (rail, numéro-sur-icône) / 36 px (carte, contenu
> DÉMONTÉ + libellé vertical), clés `dz_cf_rail`/`dz_cf_stage` (« 1 » replié,
> ABSENTE dépliée — l'état par défaut n'écrit jamais), `initFold` AVANT
> `buildRail` (aucun éclair — core.js chargé synchrone, boot à
> DOMContentLoaded, avant la première peinture), rouvrir rejoue
> `drawPreview(false)` (patron du thème — mesuré : toile 59×80 repliée →
> 181×246 rouverte). **Guerre media-query tranchée : replié GAGNE** — la
> requête ≤900 px re-déclare des VARIABLES sur `:root` au lieu de figer la
> grille, et une variable posée sur `.cf` la bat pour son sous-arbre (mesuré
> à 418 px de viewport : `46px 36px …`). Le réviseur a re-vérifié jusqu'au
> vivant : `.click()` de mod-data fonctionne sur bouton masqué, géométrie de
> mod-face lue en direct dans les handlers (jamais cachée), registre CF gelé
> intouché, parité d'octets repo↔app sur les 4 fichiers déployés, batterie
> 58 ok dont 9 pins d'escamotage, aria/titres dans les deux sens, `removeItem`
> et jamais « 0 ». 2 mutants tués + contrôle assumé (les PIXELS repliés se
> jugent à l'œil, le harnais reste aveugle à la géométrie — display:none).

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
