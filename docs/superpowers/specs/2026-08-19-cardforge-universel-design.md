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
| `deepotus-fragments` | gabarit hybride propre (arcane mystique × créature à évolutions), construit en phase 4 depuis la **carte type fournie par l'utilisateur** (« The Patriarch of the Old Houses », anatomie §7.2) | réponses de clarification + carte du 19/08 |
| Contour holographique « Sceau prismatique » | pack TRANSVERSAL famille de cadre + finition, très haute qualité, combinable avec tout archétype (§6.2bis) | demande utilisateur du 19/08 |
| Portée du Sceau prismatique | activable PAR SURFACE (écran / impression / 3D) ; « 3D uniquement en bout de chaîne » est une configuration de premier rang — celle de `deepotus-fragments` ; épaisseur réglable ; motifs/symboles incrustables dans l'hologramme | amendement utilisateur du 19/08 (relecture) |
| Verso personnalisé | image importée + un ou PLUSIEURS calques de texture/motif, édités comme le recto, présents dans l'export par couches et sur le dos de l'objet 3D (§6.2ter) | amendement utilisateur du 19/08 (relecture) |
| Phasage | 1 export-couches → 2 graphe → 3 archétypes/decks → 4 import + fragments | priorités 4 puis 5 ; chaque phase livrable seule |
| Moteurs Meshy 6 et 7 (amendement du 20/08) | le nœud `mesh3d` offre AUSSI `meshy-6` et `meshy-7` via l'**API Meshy directe** (MESHY_API_KEY de l'utilisateur, proxy `/api/meshy/*` + grilles de crédits + mock DÉJÀ livrés par le 3D Studio v2.1) — coût en CRÉDITS affiché avant, textures PBR (`enable_pbr`) et `texture_prompt` exposés, binaires rapatriés dans le nœud | demande utilisateur du 20/08 (« Meshy 3d (6 et 7) pour les textures ») ; grille officielle docs.meshy.ai : image-to-3d meshy-6/7 = 20 cr sans texture, 30 cr en 2k/4k, 35 cr en 8k, ultra (v7 seul) +5 cr |

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
| `meshy_service` (proxy sécurisé `/api/meshy/*`, grilles de crédits miroir JS↔PY, mock `MESHY_MOCK`, rapatriement) | moteurs `meshy-6` / `meshy-7` du nœud « mesh 3D » (API Meshy directe, clé utilisateur) ; la grille passe meshy-7 en HD + `ultra` (+5 cr) des DEUX côtés du miroir |
| Material Forge (`pbr_service`, `material_store`, export GLB) | nœuds « matière » de P9 |
| `gltf_builder` (`_BUILDERS` extensible, contexte verrouillé façon P8 `CTX_MESH`) | + un builder « extrusion de silhouette » (Ph2) + les extensions `KHR_materials_iridescence` / `KHR_materials_anisotropy` (§6.2bis — le model-viewer embarqué 3.3.3 les rend, vérifié sur les octets du bundle) |
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
  `coverage` % (la « profondeur » n'est PAS un champ du manifeste : c'est un choix de
  traitement 3D, elle appartient au graphe — tranché en revue de phase 1) ; global →
  deck/carte/format, `canvas_px`, dimensions mm,
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
Résultats sur disque : les nœuds GRATUITS (2a) écrivent à plat dans
`outputs/decks/{did}/forge3d/` (artefacts nommés) ; les nœuds à JOB (`mesh3d`, 2b)
écriront dans `forge3d/nodes/{nid}/` (GLB, aperçus, job.json) — amendé après la 2a.

### 5.2 Types de nœuds

| kind | rôle | coût |
|---|---|---|
| `layer` | source : une couche du manifeste (ou le composite, ou une image importée) | — |
| `plane` | plan texturé : quad + basecolor de la couche (+ maps PBR si matière liée) | **gratuit** |
| `relief` | dalle en relief locale (l'« extrusion » v1, LIVRÉE en 2a) : grille déplacée par l'alpha de la couche — **solide fermé par construction** ; params `depth_mm`, `base_mm`, `grid` (un vrai suivi de contour marching-squares viendra si le besoin le prouve) | **gratuit** |
| `mesh3d` | image→3D — menu déroulant des **7 moteurs** : 5 fal (`asset3d_service`) + `meshy-6`/`meshy-7` (API Meshy directe via `meshy_service`, textures PBR + `texture_prompt`), options par moteur | **payant, prix affiché AVANT** ($ pour fal, crédits pour Meshy) |
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
- `relief` : géométrie LOCALE à P9 (`relief_mesh`/`quad_mesh` dans forge3d.py — décision
  2a : pas d'enregistrement dans `gltf_builder._BUILDERS`, le writer de scène de P9
  n'en a pas besoin et le domaine a zéro import pièce→pièce). La fermeture est
  TOPOLOGIQUE, déclarée par le constructeur (`closed: True/False` dans le dict) et
  prouvée une fois pour toutes par test unitaire — la route gate le STL sur ce drapeau,
  JAMAIS de re-mesure par requête (7 s + ~340 Mo de pic par élément au grid max,
  mesuré). `mesh_measures` reste l'instrument des tests.

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
- STL si l'assemblage est fermé — writer binaire LOCAL à P9 (décision 2a : réutiliser
  les builders P8 violerait le zéro-import-pièce→pièce constaté ; le writer fait ~20
  lignes, en mm, en-tête sans nom d'outil) ; refus MOTIVÉ sinon. 3MF : TRANCHÉ en 2b —
  **refus motivé permanent** (la copie de build_3mf est trop grosse pour la règle 8,
  STL couvre l'impression et GLB couvre le NFT ; à rouvrir seulement si un imprimeur
  couleur l'exige en phase 3+) ;
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

**Édition par manipulation directe (amendement utilisateur du 20/08, « canvas type
Figma ») — exigence de la phase 3 :** chaque zone d'une carte s'édite AUSSI directement
sur l'aperçu, pas seulement par les panneaux :
- **sélection au clic** d'un slot/zone sur l'aperçu (contour de sélection visible),
  **déplacement au drag**, **redimensionnement par poignées** (8 poignées : coins +
  bords), flèches clavier pour l'ajustement fin (pas 1 mm, Maj = 0,2 mm — patron déjà
  livré sur la fenêtre du cadre) ;
- **ajout d'éléments depuis une palette** : zone de texte, zone de statistique
  (étiquette + valeur, style par slot), calque d'image/motif — instanciés comme des
  objets Cardforge ORDINAIRES (slots P3 / calques P2), jamais un modèle figé ;
- **calques** : liste ordonnée visible (l'ordre z DANS les bornes du z gelé de chaque
  module), réordonnancement, verrouillage, œil de visibilité par élément ;
- les gestes écrivent par `M.patch` sous le jeton du module propriétaire (une entrée
  d'annulation PAR GESTE, jamais par pixel — patron HIST de la fenêtre du cadre) ;
- la **barre de fluidité §9.6** s'applique à CHAQUE nouvelle surface de manipulation.

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

### 6.2bis « Sceau prismatique » — contour holographique très haute qualité (transversal)

Pas un archétype de mise en page : un **pack famille-de-cadre + finition**, combinable
avec TOUT archétype (case « contour holographique » dans le panneau Cadre), mis en avant
par `deepotus-fragments`. Recherche du 19/08, chiffres vérifiés sur sources d'imprimeurs
réels et sur la spec Khronos ; support iridescence/anisotropy CONFIRMÉ dans le
model-viewer embarqué (v3.3.3, occurrences relevées dans le bundle).

**Une seule source de vérité : le TRACÉ VECTORIEL du contour** (le chemin que P2 dessine).
Trois rasterisations dérivées, jamais le même fichier :

| usage | cadre | résolution | anti-aliasing |
|---|---|---|---|
| masque imprimeur | coupe + FOND PERDU | vectoriel (spot) sinon 1 bit ≥ 600 dpi | **NON** (seuil 50 %) |
| masque 3D (iridescence) | coupe SEULE | 1024–2048 px | **OUI**, niveaux de gris pleine surface (pas d'alpha), espace LINÉAIRE |
| aperçu écran | toile | écran × dpr | oui |

*(Le piège des deux cadres est réel : un même PNG réutilisé décale le contour en 3D ou
fait déborder le foil en impression.)*

**a) Écran (painter P2, canvas 2D, DÉTERMINISTE)** — pile de rendu :
1. clip par le tracé du contour ; 2. base arc-en-ciel (dégradé linéaire ou conique HSL,
saturation 70-90 %, phase = f(pointeur) en aperçu) ; 3. bande de reflet
blanc-transparent en `overlay` ; 4. paillettes : champ de points au PRNG SEEDÉ
(mulberry32, seed = id de carte — jamais `Math.random`, règle du `prng` de P2) allumées
par `hash(x, y, floor(phase × N))`. **La phase du fichier livré est CANONIQUE (0.35) et
l'aperçu animé passe par elle** : l'utilisateur voit littéralement la frame livrée —
c'est ce qui garde la preuve d'empilement de §4.2 valable (le painter reste
déterministe à phase fixée). Référence visuelle du domaine : les holo-cards CSS de
simeydotme (gradients + masques + pointeur).

**b) Impression (P7)** — livrable « masque de foil » :
- vectoriel d'abord : couche spot nommée **« Foil »**, Overprint activé (conventions
  Mixam / MakePlayingCards / PrintNinja) ; repli raster : PNG/TIFF noir 100 % **sans
  anti-aliasing**, 600-1200 dpi, fond perdu inclus ;
- contraintes VALIDÉES EN VECTORIEL avant rasterisation (ajoutées au préflight P7
  existant) : trait ≥ 0,2 mm, espacement entre zones ≥ 0,25 mm, distance au trait de
  coupe ≥ 3,2 mm (variance de fabrication 1-2 mm : l'écran l'écrit) ;
- motif holo : **rainbow uni** imposé pour un filigrane fin — les motifs à grandes
  cellules (cracked ice, honeycomb) ont un pas supérieur à la largeur du trait ;
- l'écran DIT la limite produit relevée : chez certains imprimeurs le spot cold foil
  pur exclut la couleur sur la même face (le produit foil + CMJN existe, plus cher).

**c) 3D (P9 / `gltf_builder`)** — matériau iridescent physique :
- `KHR_materials_iridescence` dans **`extensionsUsed` uniquement, JAMAIS
  `extensionsRequired`** (un viewer sans support ignore proprement et rend la base —
  cas Unreal/glTFast documentés) : la base doit être belle seule (chrome poli) ;
- recette **argent holographique** : baseColor [0.95, 0.95, 0.97], metallic 1.0,
  roughness 0.12, iridescenceFactor 1.0, iridescenceIor 1.8, épaisseur 200→900 nm ;
  recette **dorure holographique** : baseColor [1.0, 0.84, 0.55], IOR 1.6,
  200→600 nm ; clearcoat 1.0 / rugosité 0.06 par-dessus = le vernis laminé ;
- l'arc-en-ciel spatial vient d'une **`iridescenceThicknessTexture`** (canal G,
  linéaire) en secteurs radiaux N = 24-64 à 1024² — mip-stable, zéro moiré — plutôt
  que d'un réseau fin dans la normal map (dont la moyenne mip ÉTEINT l'effet à
  distance ; ne garder qu'une ondulation basse fréquence, période 32-64 texels) ;
- option « métal brossé » : `KHR_materials_anisotropy` strength 0.7-1.0, direction
  TANGENTE au périmètre (texture RG), l'attribut TANGENT étant déjà exporté ;
- rendu PROUVÉ dans le viewer embarqué : le test capture l'aperçu model-viewer du GLB
  de référence et vérifie que les franges varient avec l'angle (deux captures, deux
  distributions de teinte — mesure, pas déclaration).

**d) Portée, épaisseur, motifs incrustés (amendements de relecture) :**
- **Portée PAR SURFACE** : trois interrupteurs indépendants — écran / impression / 3D.
  « 3D uniquement » est une configuration de premier rang (le défaut du modèle
  `deepotus-fragments`) : l'écran et l'impression montrent alors le contour dans sa
  base calme (or/argent non holo), et SEUL le nœud 3D de bout de chaîne reçoit le
  matériau iridescent. L'écran dit toujours quelle portée est active.
- **Épaisseur réglable**, deux grandeurs distinctes nommées à l'écran : la LARGEUR de
  bande du filigrane (mm, 2D — validée ≥ 0,2 mm si la portée impression est active) et
  la PROFONDEUR d'extrusion du contour 3D (mm, réglée sur le nœud `extrude` du graphe).
- **Motif dans l'hologramme** : un ou PLUSIEURS calques de motif/symbole (image
  importée — ex. le sigle du poulpe —, motif du catalogue, ou texture Material Forge)
  encodés dans le canal G de l'`iridescenceThicknessTexture` (addition bornée des
  épaisseurs, ordre des calques = ordre d'addition) + ondulation normale douce : le
  symbole se RÉVÈLE dans les franges selon l'angle, comme un vrai foil à motif embarqué.
  Déterministe (mêmes calques → mêmes octets), aperçu 3D à l'appui.

**Barre de qualité mesurable** : trait vectoriel ≥ 0,2 mm vérifié avant tout export ;
aperçu == fichier (phase canonique) ; preuve d'empilement inchangée ; GLB : extension
dans `extensionsUsed`, franges angulaires mesurées dans le viewer embarqué, dégradation
propre confirmée en désactivant l'extension ; motif incrusté : relu dans le canal G du
fichier livré, pas dans l'intention.

### 6.2ter Verso personnalisé (amendement de relecture)

Le dos de carte sort du seul catalogue (7 dos P2) : `back: "custom"` —
- **une image importée** (même chemin d'import que le recto : dépôt/collage local,
  réduction 4096 px, stockage local au deck) ;
- **un ou PLUSIEURS calques** au-dessus : motif du catalogue P2, texture importée, ou
  matière Material Forge — chacun avec opacité, échelle, fusion (les modes de fusion
  autorisés restent ceux qui EMPILENT : source-over/multiply-précomposé, pour ne pas
  casser la preuve d'empilement) ;
- édité dans P2 (le dos appartient au cadre), aperçu par le bouton recto/verso
  existant ; le verso custom est SAUVÉ dans les modèles de deck (celui de
  `deepotus-fragments` en fait partie).

Conséquences en aval, déjà couvertes par construction : l'export par couches livre le
verso (§4.1 — recto ET verso) ; en 3D, **l'assemblage pose le composite verso sur la
face arrière** de la carte (plan texturé par défaut — voir §10 amendé), et le verso
peut recevoir ses propres nœuds de traitement comme le recto.

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

**Sources OFFICIELLES fournies le 20/08 (les gabarits du jeu réel) :**
- `C:\Users\olivi\Downloads\DEEPOTUS_FRAGMENTS_Cahier_de_regles_v0AB.docx` — cahier de
  règles illustré (versions 0/A/B, 2-6 joueurs) : 3 ressources (**Attention = cyan**,
  **Reconnaissance = or**, Influence), camps **S**ystème (or) / **C**ommunauté (cyan) /
  **N**eutre (gris) + marque **⬡ Bilderberg** (losange violet, 2 Chambres), **9
  familles de cartes** (Personnage, Puissance, Puissance déployable, Lieu, Région,
  Chambre, Système, Équipe, Apex), codex complet ~90 cartes (camp, A, R, capacité).
- `C:\Users\olivi\Downloads\DOSSIER_FABRICANT_DEEPOTUS_FRAGMENTS.pdf` — dossier de
  fabrication : 92 faces uniques + 1 dos commun (`homme_mystique_dans_un_cadre_doré`),
  source PNG **1060×1484 px, ratio 5:7 exact, ≈354 dpi**, fond perdu 3 mm, zone de
  sécurité 5 mm, CMJN ISO Coated v2 ; **format recommandé par le dossier : poker
  63×88 mm (5:7 exact, « option par défaut conseillée »)** — le 70×120 tarot
  imposerait un recadrage ; finitions à chiffrer : pelliculage mat/lin, **vernis
  sélectif UV, dorure à chaud** (le Sceau prismatique §6.2bis et le masque de foil P7
  parlent la langue du fabricant). Anatomie officielle d'une face : **badge de camp
  (S/C/N)** + ⬡ le cas échéant, **valeur A (cyan)** et **valeur R (or)**, **titre**,
  **capacité** (texte). Le dossier signale lui-même le risque juridique des
  personnalités réelles à remplacer par des archétypes — l'annexe légale §11
  s'applique telle quelle.

Le modèle `deepotus-fragments` doit donc offrir ces zones en SLOTS éditables (badge de
camp, pastilles A/R aux couleurs canoniques, titre, boîte de capacité, ⬡ optionnel) et
sa palette d'éléments reprend le vocabulaire du jeu (les stats personnalisées de
l'amendement §6.1 : une zone « valeur A », une zone « valeur R », une ligne de type…).

**Carte type fournie le 19/08** : « The Patriarch of the Old Houses / He Who Guards the
Aged Walls » = **« Le Patriarche des Vieilles Maisons »** du codex (Puissance, camp
Système, A 3 / R 1, synergie Le Capital) — l'une des 92 faces. Portrait gravé sombre,
filigrane or à instruments. Anatomie mesurée sur l'image (1060×1484 px, 5:7 = poker
63×88), à recaler sur le FICHIER dès que son chemin est fourni (suggestion :
`.superpowers/samples/patriarch.png`, hors dépôt) :

| zone | mesure (mm) | rôle |
|---|---|---|
| filigrane double | filets à ~2,1 et ~3,2 du bord, instruments de coin, médaillons de mi-chant | famille P2 nouvelle « filigrane-instrument », **Sceau prismatique** (§6.2bis) par défaut |
| titre | y 4,4–11,5, deux lignes, capitales or ESPACÉES, capitale ~2,8 | slot P3 (Cinzel/Cormorant SC), or #d8b76a |
| anneau de halo | centre (31,4 ; 27,1), rayon ~13,9, trait fin or | élément AJOUTABLE de la palette du modèle (position/rayon réglables) |
| illustration | pleine carte sous les cartouches (full-art, fenêtre = toile) | pose P1, gravure sombre |
| épithète | y ~76–78,5, une ligne, serif or, casse mixte | slot P3 |
| palette | noirs #0b0a08–#141210, ors #8a6a2e→#d8b76a | palette du modèle |

Modèle `deepotus-fragments` = format poker_eu, full-art, famille « filigrane-instrument »
+ Sceau prismatique **en portée « 3D uniquement »** (§6.2bis-d — écran et impression en
or calme), slots titre/épithète ci-dessus, palette d'éléments : anneau de halo,
cartouche à chiffres romains (arcane gravée), blason, badge PV et bloc d'attaques
(créature à évolutions) — le tout ajoutable et modifiable slot par slot (§6.1).

**Parcours guidé à l'instanciation du modèle** (amendement de relecture) :
1. **importer l'illustration** (dépôt direct P1, ou carte complète via P10 + adoption) ;
2. **choisir ou importer le type de bordure** : famille du catalogue, bordure isolée
   d'une carte importée (P10 → « adopter »), ou décor généré par IA (§6.3) ;
3. **régler le Sceau prismatique** : portée (3D seule par défaut ici), largeur de bande,
   profondeur d'extrusion, motif(s) incrusté(s) dans l'hologramme (sigle Deepotus…) ;
4. **éditer le verso** : image importée + calques de texture/motif (§6.2ter).

Parcours de preuve, en clôture de phase 4 : import de la carte type → isolation →
gabarit hybride → « enregistré comme modèle » → export par couches → graphe
(illustration en mesh 3D, filigrane en extrusion + matériau Sceau prismatique, typo en
relief fin doré) → GLB + metadata.json + STL + masque de foil imprimeur. Chaque étape du
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

### 9.6 Barre de fluidité des manipulations à la souris (amendement du 20/08, transversal)

Constat utilisateur (20/08) : latence et impression d'imprécision sur les cadres
manipulés à la souris. Cause mesurée dans le code : chaque `pointermove` fait un
`M.patch` complet (clone + `core:doc` diffusé à TOUS les modules, jusqu'à ~1000
événements/s sur une souris gamer) — l'aperçu du CORE, lui, est déjà coalescé au rAF
(`invalidate`). La barre, applicable à TOUTE surface de drag existante ou future
(fenêtre du cadre P2, pose P1, slots P3, texture P4, impression P7, solide P6, et
chaque surface de l'édition directe §6.1 à venir) :

1. **≤ 1 `M.patch` par frame d'animation pendant un geste** : l'état du geste vit en
   variable locale, un rAF applique le dernier état ; le `pointerup` applique l'état
   FINAL exact (aucune perte de précision) ;
2. **feedback local immédiat** (la mini-carte/l'overlay se redessine à chaque
   événement — c'est bon marché), le document suit au rythme des frames ;
3. **poignées ≥ 12 px** de zone de saisie à l'écran, curseurs contextuels
   (`move`, `nwse-resize`…), `touch-action: none` sur les surfaces de drag ;
4. **une entrée d'annulation par geste** (déjà la règle — la conserver) ;
5. **octets sains** : aucun octet NUL brut ni retour CRLF dans les sources du lab (le
   `"\x00"` littéral s'écrit ÉCHAPPÉ) — contrôle au lint (règle nommée).

## 10. Hors périmètre (nommé, pas tu)

- La marketplace NFT de deepotus.xyz (metadata.json y est prêt, rien n'y est couplé).
- Toute inscription on-chain (mint, wallet).
- `KHR_materials_emissive_strength` (émission > 1) — reste connu de P8.
- L'archétype « Champion de taverne » (2e fournée).
- ~~Le rendu 3D des versos~~ — ENTRÉ AU PÉRIMÈTRE par l'amendement verso (§6.2ter) :
  l'assemblage pose le composite verso sur la face arrière (plan texturé par défaut) ;
  seul le traitement par nœuds AVANCÉ du verso (mesh 3D par élément de dos) reste une
  extension ultérieure.

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
