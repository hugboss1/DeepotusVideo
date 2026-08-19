# Cardforge universel — import, archétypes, export par couches, Forge 3D

Date : 2026-08-19 · Statut : validé en brainstorming (architecture A, phasage 1→2→3→4)
Précède : `2026-08-11-cardforge-design.md` (les 8 pièces d'origine, dont les règles restent en vigueur)

## 1. Objectif

Un workflow **linéaire, dans un seul écran**, de la création d'un deck hyper-personnalisable
jusqu'à une pièce 3D imprimable ou un artefact « qualité NFT » prêt pour la future
marketplace de deepotus.xyz (la marketplace elle-même est HORS périmètre ; le format de
sortie doit y être prêt) :

1. **créer ou importer** une carte de sa fabrication, l'éditeur **isolant les éléments
   constitutifs** (fond, bordure, zones occupées) ;
2. **habiller** avec les éléments existants (cadres, stats, typo) + un **catalogue
   d'archétypes de styles célèbres** + la **génération IA des cadres** (menu déroulant du
   modèle) ;
3. **sauvegarder comme deck custom nommé** — le premier : `deepotus-fragments` ;
4. **exporter par couches** (une PNG alpha par élément + manifeste) ;
5. **graphe de nœuds 3D** façon Meshy : chaque couche traitée séparément (plan texturé
   gratuit, extrusion locale gratuite, image→3D payant), matières Material Forge ;
6. **artefact final** : GLB + métadonnées NFT, STL/3MF imprimable.

Priorités utilisateur : **étage 4 d'abord, étage 5 ensuite**, tout le reste important.
Toutes les fonctionnalités Cardforge existantes s'appliquent aux decks custom ET aux
archétypes du catalogue.

## 2. Décisions actées

| Décision | Choix | Motif |
|---|---|---|
| Architecture | **A — deux nouvelles pièces dans le lab** (P9 Forge 3D, P10 Import) | pas de patch bundle, contrat des 8 pièces conservé, workflow en un écran |
| Catalogue de styles | **Archétypes génériques** — grammaire du genre, signatures 100 % originales | but NFT public : le trade dress des marques est attaquable (annexe légale §11) |
| Isolation à l'import | **Hybride** : analyse locale PIL gratuite par défaut + détourage IA opt-in (rembg fal ~0,003 $/image, prix affiché) | patron maison : gratuit par défaut, payant affiché |
| Archétypes 1re fournée | **7/8** : superstar, duel, créature, arcane, monstre, légende, gravée (sélection utilisateur) ; « taverne » en 2e fournée | clics de sélection du 19/08 |
| Archétype = point de départ, jamais un verrou | un modèle instancie un deck ORDINAIRE ; chaque élément reste éditable (ajout/retrait, couleur de fond, typo, corps… par slot) | amendement utilisateur du 19/08 |
| `deepotus-fragments` | gabarit hybride propre (arcane mystique × créature à évolutions), construit en phase 4 depuis la **carte type fournie par l'utilisateur** | réponses de clarification |
| Phasage | 1 export-couches → 2 graphe → 3 archétypes/decks → 4 import + fragments | priorités 4 puis 5 ; chaque phase livrable seule |

## 3. Architecture

### 3.1 Ce qui ne change pas

Les règles du lab (spec du 11/08) restent toutes en vigueur : un module = 1 JS + 1 CSS +
1 py + 1 test ; identité par URL de script ; écriture par jeton sur son seul sous-arbre ;
**table z GELÉE** (les nouvelles pièces n'ont AUCUN painter) ; routeurs relatifs, un par
pièce ; blocs miroir JS↔Python comparés par tests de parité ; `cf_deploy.ps1` pour
atteindre l'app installée ; lint `lint_cardforge.py` (à étendre aux 2 modules, §9.4).

### 3.2 Les deux nouvelles pièces

- **P9 « Forge 3D »** — `frontend/cardforge/js/mod-forge3d.js` + `css/mod-forge3d.css` +
  `backend/app/services/cards/forge3d.py` + `backend/tests/test_cards_forge3d.py`.
  Sous-arbre : `doc.forge3d` (graphe compris). Panneau : export par couches (Ph1), graphe
  de nœuds + aperçu model-viewer + artefacts (Ph2). Aucun painter.
- **P10 « Import »** — id de module `capture` (`import` est un mot réservé Python : le
  fichier `import.py` serait inimportable et violerait la règle 1 du lint) :
  `mod-capture.js` / `mod-capture.css` / `capture.py` / `test_cards_capture.py`.
  Libellé à l'écran : « Import ». Sous-arbre : `doc.capture` (analyse publiée).
  Panneau : dépôt, réglages d'analyse, vignettes des couches isolées, envois vers
  l'IA opt-in. Aucun painter.

Ordre des onglets : … P7 Impression · P8 Export 3D · **P9 Forge 3D** · **P10 Import**
(P10 est aussi proposé au démarrage d'un deck vide : « importer une carte existante »).

### 3.3 Extensions du CORE (internes, même statut que `guides`)

1. **Rendu par couches** : `renderRaw(i, {only_z: [z…], paper: false})` — sous-ensemble de
   painters sur toile transparente, sans le support papier blanc. Non exposé aux modules
   par le jeton : seul le CORE (bouton de P9 via une API dédiée `CF.layers(i, side)`)
   l'appelle. `CF.cardBlob` étendu pour minter les blobs de couche (la provenance reste
   obligatoire pour `CF.download` / `M.api.blob`).
2. **Decks** : liste (`GET /decks` existe sans consommateur), ouverture d'un autre deck,
   **duplication** (`POST /api/cards/decks/{did}/duplicate`, ~15 lignes : read → nouveau
   did → write), création **depuis un modèle** (§6.2). Galerie de démarrage.

### 3.4 Publication inter-pièces (le patron `art_window`, généralisé)

P10 n'écrit JAMAIS chez les autres. Il publie son analyse dans `doc.capture` ; P1, P2 et
P3 offrent chacune un bouton « adopter » qui LIT cette publication (lecture tolérante,
valeurs manquantes = pas d'offre). Même mécanique que `frame.art_window` → `frameWindow()`
livrée le 19/08 : publication différée, gardée par comparaison, jamais de boucle.

### 3.5 Services réutilisés tels quels

| Service | Usage ici |
|---|---|
| `asset3d_service` (5 moteurs fal : tripo, hunyuan, trellis, rodin, triposr) | nœuds « mesh 3D » de P9 — menu déroulant + prix |
| Material Forge (`pbr_service`, `material_store`, export GLB) | nœuds « matière » de P9 |
| `gltf_builder` (`_BUILDERS` extensible, contexte verrouillé façon P8 `CTX_MESH`) | + un builder « extrusion de silhouette » (Ph2) |
| `CF.images` + patron `face.py:ai-models` (tarifs `pricing.py`) | menu déroulant de génération IA des cadres (Ph3) et vues (Ph2) |
| `pixel_ops.chroma_key`, `pbr_service._micro_contrast/stats/correlation` | briques d'isolation (Ph4) |
| rembg (fal `imageutils/rembg` 0,003 $/img, ou local si installé) | détourage IA opt-in (Ph4) |
| model-viewer vendored (`/assets/model-viewer.min.js`) | aperçu GLB dans P9 |

**Seule brique neuve côté services : l'assembleur multi-GLB** (§5.4) — identifié par la
recherche comme le chaînon manquant du dépôt.

## 4. Phase 1 — Export par couches (priorité n° 1)

### 4.1 Les couches

Six couches nommées par RÔLE + le composite, **recto et verso**, PNG alpha à `canvas_px`
exact :

| couche | painters (z) | contenu |
|---|---|---|
| `fond-matiere` | texture z10 | papier/matière sous l'illustration |
| `illustration` | face z20 | la pose (catalogue, importée ou IA) |
| `voile-matiere` | texture z30 | grain/voile au-dessus de l'illustration |
| `cadre` | frame z40 | corps du cadre + fenêtre |
| `typographie` | type z60 | tous les slots de texte |
| `ornements` | frame z70 | coins, gemme, ruban |
| `composite` | z10…z70 | la carte telle que livrée (référence de preuve) |

Une couche vide (module inactif) est quand même écrite (PNG transparent) et son manifeste
dit `coverage: 0` — l'absence se mesure, elle ne se devine pas.

### 4.2 La preuve d'empilement (le cœur de la fiabilité)

Une couche n'est digne de confiance que si l'empilement des couches REPRODUIT la carte.
- **Preuve client (stricte)** : le navigateur superpose ses propres couches en source-over
  sur fond papier et exige **zéro pixel d'écart** avec le composite rendu d'un trait —
  même moteur, même esprit que la passe témoin de la mesure de masquage de P1. Un painter
  qui poserait un mode de fusion non-empilable (`globalCompositeOperation` ≠ source-over,
  filtres) fait ÉCHOUER la preuve, et l'écran nomme la couche fautive au lieu de livrer
  un ZIP faux. Audit préalable des painters texture (z10/30) en début de phase.
- **Second avis backend (tolérance chiffrée)** : `forge3d.py` ré-empile les PNG en PIL
  (alpha-over) et publie l'écart mesuré au composite (± 1 niveau attendu : arrondis de
  prémultiplication différents entre moteurs). Les deux mesures partent dans le manifeste.
- Déterminisme requis : les bruits sont déjà seedés (`prng` de P2) ; les effets de bord
  des painters (noteMeasure, publishWindow) sont gardés par comparaison — rendus
  supplémentaires sans conséquence.

### 4.3 Route, stockage, manifeste

- `POST /api/cards/{did}/forge3d/layers` — multipart (patron `print.py:post_sheet`) :
  N PNG de couche + composite + JSON de preuve client. Le backend vérifie `canvas_px`
  (409 sinon), fait son second avis, estampille chaque PNG (pHYs, sRGB — patron
  `face.py:stamp_png`), écrit `outputs/decks/{did}/forge3d/layers/{side}/…` + le ZIP.
- **Manifeste** `layers.json`, schéma `card-3d/layers-manifest@1` : par couche → rôle,
  module, plage z, fichier, SHA-256, boîte des pixels non transparents (px et mm),
  `coverage` %, profondeur ; global → deck/carte/format, `canvas_px`, dimensions mm,
  pHYs, les deux mesures de preuve, date. Aucun nom de producteur (règle P8,
  `scrub_identity`).
- Bordereau chiffré à l'écran avant téléchargement (patron P8). Le ZIP est l'ENTRÉE
  officielle du graphe (Ph2) — et un livrable autonome pour Photoshop/After/etc.

## 5. Phase 2 — Le graphe de nœuds « Forge 3D » (priorité n° 2)

### 5.1 Modèle de données

`doc.forge3d.graph = {nodes: [{id, kind, …params}], edges: [{from, to, port?}]}` — même
forme que les graphes du Studio (compatibilité conceptuelle), mais exécuteur DÉDIÉ dans le
lab (l'exécuteur du Studio est enfoui dans le bundle compilé : réutilisation exclue par la
recherche). Le graphe vit dans le document → annulation, autosave et PATCH gratuits.
Résultats sur disque : `outputs/decks/{did}/forge3d/nodes/{nid}/` (GLB, aperçus, job.json).

### 5.2 Types de nœuds

| kind | rôle | coût |
|---|---|---|
| `layer` | source : une couche du manifeste (ou le composite, ou une image importée) | — |
| `plane` | plan texturé : quad + basecolor de la couche (+ maps PBR si matière liée) | **gratuit** |
| `extrude` | extrusion locale : silhouette alpha (+ height optionnelle) → **solide fermé** ; profondeur en mm | **gratuit** |
| `mesh3d` | image→3D via `asset3d_service` — menu déroulant des 5 moteurs, options par moteur | **payant, prix affiché AVANT** |
| `material` | matière Material Forge (existante `mat_…` ou générée) appliquée au nœud amont | gratuit (local) / payant si générée par IA |
| `transform` | position x/y en mm de carte, profondeur/écart z en mm, rotation, échelle | — |
| `assemble` | fusionne tous les amonts en UNE scène / UN GLB | — |
| `artifact` | sorties : GLB + metadata.json, STL/3MF si fermé, aperçu | — |

**Graphe par défaut auto-construit** dès qu'un export de couches existe : chaque couche →
`plane` empilé avec un écart de profondeur (effet parallaxe), 100 % gratuit, aperçu
immédiat. L'utilisateur monte en gamme nœud par nœud — l'esprit Meshy demandé.

### 5.3 Exécution

- Nœuds gratuits : synchrones côté backend (PIL + builders locaux).
- `mesh3d` : job en arrière-plan (patron `asset3d` : BackgroundTasks + polling), état par
  nœud affiché dans le graphe (`en file / en cours / servi / échec avec l'erreur
  littérale du fournisseur`). Prix unitaire depuis `pricing.py`, affiché sur le nœud et
  sommé en pied de graphe AVANT tout lancement.
- `extrude` : nouveau builder enregistré dans `gltf_builder._BUILDERS` par `setdefault`,
  contexte sous verrou (patron P8 `CTX_MESH`) ; maillage PROUVÉ fermé/imprimable par les
  mesures existantes (`mesh_report` : arêtes libres, volume signé).

### 5.4 L'assembleur multi-GLB (brique neuve)

`forge3d.py` : fusion pur-Python de N GLB en un seul — concaténation des buffers,
réindexation des accesseurs/vues/matériaux/textures, un nœud racine par élément (nommé
par le rôle de sa couche), transformations portées par les nœuds (jamais cuites dans les
positions pour les éléments GLB). Rigueur héritée de P8 : échelle physique en mètres +
dimensions dans `extras`, bornes d'accesseurs EXACTES, `scrub_identity` (aucun nom
d'outil), samplers CLAMP. Le GLB assemblé repasse par `glb_report` — le bordereau relit
les octets, il ne recopie pas l'intention.

### 5.5 L'artefact

- `model.glb` (la pièce NFT) + `preview.png` (capture model-viewer côté client, téléversée
  — règle « rien de la carte n'est rendu au serveur ») ;
- `metadata.json` **compatible ERC-721** : `name`, `description`, `image` (preview),
  `animation_url` (model.glb), `attributes` [{deck, carte, archétype, finition, rareté,
  éléments 3D, moteurs utilisés}] — prêt pour la marketplace future, couplé à rien ;
- STL / 3MF si l'assemblage est fermé (builders P8 réutilisés) ; refus MOTIVÉ sinon ;
- bordereau chiffré, stockage deck-local. Option d'inscription dans la Bibliothèque
  (JobRecord `provider="card3d"`) pour retrouver l'artefact hors du lab.

## 6. Phase 3 — Archétypes et decks custom

### 6.1 Un archétype = un modèle de deck, 100 % éditable après instanciation

Un modèle est un JSON servi par le backend (`GET /api/cards/models`, source unique côté
serveur — données, pas de table miroir) :
`{id, label, hint, format, frame: {family, réglages…}, type: {preset, slots…},
palette, finish, texture: {réglages}, elements: [éléments ajoutables]}`.

**Principe actté (amendement utilisateur) : le modèle SEED un deck ordinaire.** Après
instanciation, chaque élément est un objet Cardforge standard : les zones de contenu
(cases de stats, badges, rangées d'icônes) sont des **slots P3** — ajoutables,
supprimables, déplaçables, avec **plaque de fond colorée, police, corps, couleur,
alignement modifiables slot par slot** — jamais des dessins figés dans le cadre. Le cadre
(P2) ne porte que le décor : bordures, plaques, fenêtres, matières, aux réglages existants
(couleurs, métaux, coins, rareté…). Chaque modèle embarque sa **palette d'éléments**
(`elements`) dans laquelle l'utilisateur pioche pour en RAJOUTER (ex. une 7e stat, un 2e
bandeau) — ce sont des presets de slots.

**Extension P3 requise** : plaque de fond par slot (couleur + alpha + rayon), et typo par
slot si incomplet aujourd'hui — bloc miroir + test de parité, comme l'existant.

### 6.2 Les huit archétypes (zones en mm sur poker 63×88, issues de la recherche du 19/08)

Première fournée (sélection utilisateur) : **superstar, duel, créature, arcane, monstre,
légende, gravée**. Seconde fournée : taverne.

1. **Superstar du stade** — plaque à pans coupés 4,4→55×80 ; note géante 8,12 (12×9) ;
   position dessous ; drapeau/écusson en colonne gauche ; portrait 22,8 (36×38) ; bandeau
   nom 6,47 (51×7) ; grille 6 stats 2×3 8,56 (47×21, VIT/TIR/PAS/DRB/DEF/PHY) ; pied
   d'icônes. Typo Oswald/Barlow Condensed + Archivo (chiffres tabulaires). Or champagne,
   paliers argent/bronze, dorure/foil.
2. **Duel de chiffres** — bandeau titre 4,4 (55×8, rectangle, PAS d'ellipse) ;
   illustration 4,13 (55×31) ; tableau 5-7 lignes zébrées 4,51 (55×29), mêmes libellés
   sur tout le deck, valeurs tabulaires à droite ; pied référence « 12/32 ».
   Typo Nunito/Rubik + Titan One. Couleur dominante par paquet, papier mat.
3. **Créature à évolutions** — cartouche d'évolution 4,4 ; nom 19,4 ; PV+élément 44,4 ;
   illustration cadrée 6,11 (51×35) ; 1-2 attaques 6,51 (51×22, coût en icônes ⌀4 /
   dégâts à droite) ; pied faiblesse/résistance/retraite ; ligne légale + rareté
   cercle/losange/étoile. Typo Lato/PT Sans + Jost. Cadre par élément (SES éléments, SES
   teintes), holo « cosmos » pour les rares.
4. **Arcane mystique** — bordure 2,5 mm ; bandeau titre 4,3.5 (nom + coût en pastilles
   ⌀4, icônes d'écoles ORIGINALES) ; illustration 5,9.5 (53×39) ; ligne de type 4,49 ;
   boîte parchemin 4,54.5 (55×24, règles romain + ambiance italique) ; cartouche
   force/endurance 47,78. Typo Cinzel/Alegreya SC + EB Garamond. Roue de 4-6 écoles
   PROPRE.
5. **Monstre de duel** — cadre couleur pleine = catégorie (code propre, décalé de
   l'original) ; nom capitales 4.5,4.5 ; attribut ⌀7 à droite ; étoiles ALIGNÉES À
   DROITE 8,12.5 ; illustration CARRÉE 8,18.5 (47×47) ; type [CROCHETS] ; boîte d'effet ;
   ligne ATK/DEF à droite 6,81.5. Typo Spectral SC + Roboto Condensed + Saira Condensed.
6. **Légende du terrain** — recto photo pleine page (fond perdu), logo de collection
   4,4, bandeau nom 0,74 (63×10, aplat/diagonale), № en coin ; **verso à tableau de
   stats saisonnières** (lignes = saisons, TOTAL en gras) + bloc anecdote. Typo
   Anton/Archivo Black + Barlow. Bordure blanche vintage, parallèles chrome/holo
   génériques. (Seul archétype à verso spécifique — le dos P2 reste disponible.)
7. **Arcane gravée** — double filet 1,5/3 mm ; cartouche Chiffres ROMAINS 4,4 (55×8) ;
   illustration gravée au trait + aplats pochoir 4,13 (55×61, repérage décalé 0,2 mm
   volontaire) ; cartouche nom 4,75 (55×9, capitales espacées). Typo IM Fell/Cormorant
   SC. Vermillon/bleu/ocre/vert sur ivoire.
8. **Champion de taverne** *(2e fournée)* — cristal de coût ⌀11 en coin ; portrait
   ovale serti ; ruban de nom incurvé ; gemme de rareté ; boîte parchemin ; médaillons
   attaque/vie ⌀10 aux coins bas ; tout « sculpté ». Typo Grenze/Besley + Libre Franklin.

Chaque archétype impose : 1 famille P2 nouvelle (dessin procédural + entrée `FAMILIES`
des DEUX côtés + `FAM_FN` + `WIN_SHAPE`) et/ou réutilisation des 6 existantes, 1 preset
P3 nouveau (bloc miroir), palette, finition par défaut. Le contrôle de **distance de
silhouettes** de la QA P2 doit rester sain (une famille nouvelle trop proche d'une
existante dégrade le pire couple — mesuré, pas décrété).

### 6.3 Génération IA des cadres

Dans P2 (ou P10 pour un cadre importé) : « générer le décor de cadre par IA » — menu
déroulant du modèle (la liste vient de `GET /image-models` enrichie des tarifs, patron
`face.py:ai-models` ; JAMAIS de liste recopiée à l'écran), prompt pré-rempli par
l'archétype actif, l'image générée devient un décor de cadre (calque sous la fenêtre,
même mécanique qu'une matière de support importée). Prix affiché avant l'appel.

### 6.4 Decks custom, galerie, modèles perso

- Galerie de démarrage (CORE) : « nouveau deck depuis modèle » (les 8 + les modèles
  perso), « importer une carte » (→ P10), « reprendre un deck » (liste `GET /decks`,
  enfin consommée).
- Renommage : existe déjà (`PATCH {name}` + `#deckName`).
- **Duplication** : `POST /api/cards/decks/{did}/duplicate` (nouveau, ~15 lignes).
- **« Enregistrer comme modèle »** : sérialise les réglages du deck courant (format,
  frame, type, palette, texture — PAS les illustrations) dans un modèle perso
  (`{DATA_ROOT}/cardforge_models/`), qui apparaît dans la galerie. C'est ainsi que
  `deepotus-fragments` devient réutilisable.

## 7. Phase 4 — Import et isolation (P10)

### 7.1 Chemin

1. `POST /api/cards/{did}/capture/card` — corps brut (patron `texture.py:post_paper`),
   réduction à 4096 px max (constante partagée avec P1), recto (et verso optionnel).
2. **Analyse locale (PIL pur, gratuite)** :
   - *bordure* : balayage de gradient depuis les 4 bords → bande de bordure (épaisseur
     mm), couleur dominante, rayon de coin estimé ;
   - *zones occupées* : variance locale (`_micro_contrast` + `stats` par blocs) → boîtes
     de texte/stats candidates (position mm, densité) ;
   - *fond* : détourage par couleur dominante (`chroma_key` philosophie `bg_failed` :
     un fond non uni est REFUSÉ avec mesure, pas détouré de travers) ;
   - *palette* : quantification (`pixel_ops`).
   Chaque détection publie sa **confiance mesurée** (régularité de bande, uniformité de
   fond, netteté de boîte) — l'écran affiche le chiffre, jamais une certitude.
3. **Détourage IA opt-in** : rembg (fal 0,003 $/image, ou local si présent — même
   basculement que le pipeline sprite), prix affiché ; produit la couche « sujet ».
4. **Publication** : `doc.capture = {analyzed, border: {mm, color, radius_mm, confidence},
   boxes: […], bg: {color, confidence}, palette, layers: {…fichiers}}` ; les PNG isolés
   sont stockés deck-local et servis par le routeur de P10.
5. **Adoption** (chaque pièce chez elle, lecture tolérante) :
   - P1 « adopter l'illustration » → le sujet (ou le recadrage art) devient la pose ;
   - P2 « adopter la bordure » → famille + réglages LES PLUS PROCHES, **écart avoué**
     (« bande 2,1 mm ↔ famille sable 2,0 mm, teinte à 6 % ») ;
   - P3 « adopter les zones » → boîtes → slots de gabarit (éditables ensuite, §6.1).
6. Les couches importées entrent dans le manifeste de P9 comme sources de nœuds — une
   carte importée peut partir en 3D sans être reconstruite.

### 7.2 `deepotus-fragments` (la preuve de bout en bout)

Construit en clôture de phase 4, depuis la **carte type fournie par l'utilisateur**
(chemin à fournir au démarrage de l'implémentation) : import → isolation → gabarit
hybride (arcane mystique × créature à évolutions, palette Deepotus) → « enregistré comme
modèle » → export par couches → graphe (illustration en mesh 3D, cadre en extrusion
dorée Material Forge, typo en relief fin) → GLB + metadata.json + STL. Chaque étape du
workflow réel, mesurée. AUCUNE donnée personnelle réelle dans les gabarits (pseudonyme
fixe — incident du gauntlet précédent).

## 8. Doctrine d'erreurs (existante, appliquée aux nouveautés)

- Corps mal formé → jamais 500 (nettoyeurs par clé, patron `clean_options`).
- PIL/dépendance absente → 503 avec l'erreur littérale.
- Appel payant → prix AVANT, depuis `pricing.py`, jamais recopié.
- Échec fournisseur (fal/OpenAI/Meshy) → erreur littérale + préfixe fournisseur (patron
  toasts + lien de compte existant).
- Un nœud sans résultat → l'assembleur REFUSE avec motif (« le nœud illustration n'a pas
  servi son GLB »), il n'assemble pas un trou.
- Preuve d'empilement échouée → pas de ZIP ; la couche fautive est nommée.
- Fond non uni à l'import → refus mesuré du détourage local + proposition de l'option IA.

## 9. Tests et garde-fous

### 9.1 Nouveaux fichiers (un par pièce, règle 1)

- `test_cards_forge3d.py` : preuve d'empilement sur octets (stack == composite, les deux
  mesures) ; manifeste (schéma, SHA-256 recalculés, boîtes exactes sur images de
  synthèse) ; extrusion fermée/volume positif/imprimable (via `mesh_report`) ; GLB
  assemblé : bornes d'accesseurs exactes, `scrub_identity`, dimensions physiques,
  CLAMP ; metadata.json : schéma + attributs recalculables ; prix affichés = table
  `pricing.py` ; aucun 500.
- `test_cards_capture.py` : cartes SYNTHÉTIQUES à vérité connue (bordure de x mm posée
  par le test → mesure retrouvée, tolérance chiffrée ; boîtes de texte posées →
  retrouvées ; fond non uni → refus motivé) ; publication conforme ; adoption P2 :
  l'écart famille↔mesure est celui affiché.

### 9.2 Parité et miroirs

Toute table ajoutée en double (presets P3 étendus, familles P2 nouvelles) passe par les
blocs marqués + tests de parité existants. Les MODÈLES d'archétypes sont côté serveur
uniquement (données JSON) : pas de miroir, l'écran lit l'API.

### 9.3 CORE

Tests du rendu par couches dans le harnais QA JS (`test_core_contract.mjs`) : couche =
sous-ensemble exact des painters, toile transparente, provenance des blobs, et le
contrat inchangé pour tout le reste (aucune régression des 45 contrôles existants).

### 9.4 Lint et déploiement

`lint_cardforge.py` : ajouter `forge3d` et `capture` à la liste des modules (aucun painter
autorisé pour les deux) ; règle 1 exigée. `cf_deploy.ps1` couvre déjà les nouveaux
fichiers (il copie les arbres entiers). `index.html` du lab : deux onglets + scripts.

### 9.5 Option qualité (à décider en fin de phase 2)

Mini-gauntlet en duel aveugle de la Forge 3D contre Meshy (protocole certifié du 18/08 :
panneaux recadrés, critiques cloîtrés, cotes inversées) — recommandé avant toute
communication « qualité NFT professionnelle ».

## 10. Hors périmètre (nommé, pas tu)

- La marketplace NFT de deepotus.xyz (metadata.json y est prêt, rien n'y est couplé).
- Toute inscription on-chain (mint, wallet).
- `KHR_materials_emissive_strength` (émission > 1) — reste connu de P8.
- L'archétype « Champion de taverne » (2e fournée).
- Le rendu 3D des VERSOS dans le graphe (l'export par couches les livre ; l'assemblage
  recto/verso en un objet double-face est une extension naturelle de `assemble`, non
  requise pour la v1).

## 11. Annexe légale — les trois règles (recherche du 19/08)

1. **Copier la grammaire, jamais la signature.** Positions et rôles des zones : libres.
   Dos, cadres emblématiques, logos, polices propriétaires, iconographie précise (Poké
   Ball, écusson FUT, ellipse Top Trumps, dos marron à médaillon, symboles de mana/
   énergie, sceau doré, cristal bleu…) : à redessiner SYSTÉMATIQUEMENT en propre.
2. **Le test des 2 mètres.** Une carte imprimée vue à 2 m (ou en vignette 100 px) ne doit
   pas pouvoir être prise pour une carte officielle — sinon changer au moins deux
   éléments majeurs (teinte de cadre, forme des cartouches, iconographie, dos). Test
   documenté par archétype.
3. **Zéro actif tiers dans les gabarits.** Polices Google Fonts SIL/OFL uniquement ;
   aucun logo, marque, personnage, joueur, club, texte ou symbole existant — y compris
   dans les fichiers d'exemple et les noms internes (les archétypes se nomment par leur
   nom générique, jamais par la marque).

*Synthèse documentaire, pas un avis juridique ; faire valider les gabarits finaux par un
conseil en PI avant commercialisation.*
