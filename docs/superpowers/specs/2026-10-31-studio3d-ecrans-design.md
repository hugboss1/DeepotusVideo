# 3D Studio à écrans — conception depuis l'inventaire de Sorceress

> Inventaire : `2026-10-31-sorceress-3d-studio-inventaire.md` (relevé du
> 31/10/2026). Code lu sur `origin/main` 80a896dc (le dossier local `main` a
> plus de 1 250 commits de retard).
>
> **Équivalents chez nous :** Game Assets › 3D (`DzGameAssets` du bundle,
> maillons dzga3d et dzpose, `backend/app/services/asset3d_service.py`
> `ENGINES`) ; 3D Studio (`frontend/studio3d/`, graphe Meshy `studio3d.js`
> `NODES`/`CABLES`, généré par L9) ; Établi (`frontend/etabli/`, généré par
> L8, plus `mouvement.js` et `jeu.js` écrits à la main) ; services
> `mesh_lod`, `mesh_textures`, `mesh_export`, `mouvement_rig`, `uthana`,
> `meshy_service`, `pose3d`, `comparatif3d`.

## La demande, reformulée

1. L'onglet **3D** de Game Assets ne sert plus qu'à **générer le modèle de
   base**. Tout le reste part vers le **3D Studio**.
2. Le **3D Studio** quitte le graphe de nœuds comme interface principale. Il
   devient une suite d'**écrans**, un écran par étape, dans le design actuel
   (angles vifs, jetons de la charte, `--cat-3dstudio`). Les fonctions des
   nœuds sont reprises dans ces écrans.
3. Le 3D Studio intègre **toutes les fonctionnalités et tous les modèles**
   vus chez Sorceress.
4. Il ajoute un **éditeur de décor et d'environnement** : arbres et
   végétation façon TreeGen. Cet éditeur traite aussi un élément généré dans
   l'onglet 3D.

## Parcours cible

```
Game Assets › 3D (CRÉER)                          Game Assets › 3D Studio
┌──────────────────────────┐   « Ouvrir dans »    ┌─────────────────────────────────────────────────────────┐
│ modèles (multi) + roues  │ ───────────────────▶ │ OUVERT : vignette · nom · RIGGÉ · os · sommets · v12 ●   │
│ Image / Texte / Multi    │   Texture / Rig /    ├─────────────────────────────────────────────────────────┤
│ quantité · devis         │   Animer / Décor     │ Ouvrir · Importer │ Préparer · Texture · Rig · Affiner │
│ galerie + avant/après    │                      │                   │ · Animer · Exporter │ Décor │ Graphe│
└──────────────────────────┘                      └─────────────────────────────────────────────────────────┘
```

Chaque écran garde la mise en page **gauche / viewport / droite**, avec une
action principale en bas à droite : « Envoyer vers Rig → », « Envoyer vers
Animer → », etc. Un écran modifie le modèle ouvert en écrivant une **version
de plus** dans le job. Le bandeau montre la version et le point « modifications
non enregistrées ».

## Tableau d'écart

| Chez eux (Sorceress) | Aujourd'hui chez nous | Décision |
|---|---|---|
| **Create** : liste de 9 modèles, multi-sélection (un job par modèle), total en crédits | GA 3D : un seul moteur par génération, 7 moteurs (`ENGINES`, `asset3d_service.py:87`) ; Meshy grisé (`meshyNoKey`) | **À faire** : liste à cases, un job par moteur coché, devis total avant `confirme_cout`. Meshy 7/6 rejoint la liste (clé Meshy) |
| Roue de réglages par modèle (Meshy : topologie, polycount, symétrie, pose, remesh, texture 2K/4K/8K, PBR, Ultra, Image Enhancement, Remove Lighting ; Tripo : texture HD, quad, face limit, auto size, alignement, orientation, geometry quality ; Trellis : résolution, texture size, steps, guidance, seed ; Rodin : densité, matériau, mode quad/raw, T/A-pose, format) | Réglages éparpillés : pose (dzpose), textures oui/non, nombre de vues ; réglages Meshy seulement dans les nœuds du graphe (`openEditor`) | **À faire** : un accordéon de réglages par moteur, décrit par le registre `ENGINES` (`reglages: [...]`), validé côté serveur. Les réglages Meshy des nœuds `preview`/`texture` passent ici |
| Modèles : Meshy 7, Meshy 6, Tripo P2, Tripo v3.1, Tripo Smart Mesh (low-poly), Hunyuan 3D 3.1, Pixal3D (maison), TRELLIS 2, Rodin 2.0 | tripo v2.5, tripo-h3.1, hunyuan v2, trellis, rodin, triposr, hunyuan-local | **À faire après relevé des API (T0)** : ajouter chaque version présente sur fal ou chez le fournisseur ; garder triposr et le local (gratuit). **Écarté** : Pixal3D (modèle privé de Sorceress) |
| Saisie Image / Text / Multi-Img (lot : une image = un modèle) ; quantité 1-4 | Image seule ; « multi-vues » = 1-4 vues générées par Seedream ; pas de quantité ; texte → 3D seulement dans le graphe Meshy et par Blender `/generer` | **À faire** : trois modes. Texte (Meshy text-to-3d, Tripo texte), Image, Multi-images (vraies photos d'un même sujet). Les vues Seedream restent une option du mode Image. Quantité 1-4 |
| Encart « Recommended pose » + planche A-pose téléchargeable | Choix de pose (t376) sans planche | **Adapté** : encart et planche (générée une fois, rangée dans `assets`) ; renvoi au choix de pose existant |
| Galerie : filtres All / Starred / Rigged / Unrigged, cartes par ligne, recherche, avant/après source ↔ rendu | Cartes avec `model-viewer`, renommer, supprimer, formats, impression | **À faire** : filtres (dont Personnage / Décor), favoris, curseur de grille, recherche, volet avant/après. Les boutons Edit Rig / Refine / Animate deviennent « Ouvrir dans 3D Studio ▸ Texture · Rig · Animer · Décor » |
| Vue détail : specs, Original / Both / Optimized, préréglages de 500 à 200 k triangles, curseur, Re-Optimize, téléchargements | `DzOptimize` (gltfpack), `DzLod`, `DzTex` sous chaque carte de GA 3D | **Déplacé** dans l'écran **Préparer** du 3D Studio. GA 3D garde seulement le téléchargement brut |
| Uploads (Pro) + mannequin UE5 calé SMPL | `/assets/3d/importer`, `/etabli/importer` sans écran | **À faire** : écran **Importer** (GLB, glTF, OBJ, BVH ; FBX par Blender en arrière-plan). Mannequin de référence fourni |
| Import Daz G8 (FBX + textures), Mixamo / UE / VRM / glTF « bientôt » | — | **À faire** : types glTF/GLB riggé, Mixamo (FBX), VRM. **Daz G8 plus tard** (FBX + TIFF, volumineux) |
| Bandeau « CURRENTLY OPEN » (version, modifications non enregistrées) ; second groupe d'onglets grisé sans personnage | Graphe : un job à la fois, pas de bandeau | **À faire** : bandeau commun aux écrans, état partagé `ouvert` (job, version, rig, sommets) |
| **Texture** : modèle d'image (Nano Banana 2 / 2.1 / 1, GPT Image 2, Seedream 5 Lite), résolution, ratio, capture, rosace de vues ¾, orbite par pas, éclairages Unlit/Flat/Soft/3-pt/Bright | Retexture Meshy `/assets/3d/{job}/texturer` sans bouton ; nœud `texture` du graphe | **À faire (1/2)** : retexture IA (Meshy retexture, prompt, référence de style), capture de référence au choix de vue et d'éclairage, génération d'image par nos modèles fal |
| Auto Texture 4 à 18 vues (prix par vue), projection sur le modèle, « From shaded mesh », « Generate with Progression » | — | **À faire (2/2)** : projection multi-vues sur l'atlas UV dans le navigateur (three.js : rendu par vue, image IA, projection pondérée par l'angle, fusion). Devis = N × prix de l'image |
| Pinceaux : gomme, estomper, soigner les coutures, combler, tout combler, débruiter (IA 2 cr), atlas UV à plat, fil de fer, visualiseur de fissures | — | **À faire (2/2)** : gomme, estomper, combler, tout combler, atlas UV à plat, fil de fer ; débruitage par un modèle d'image (devis). **Écarté** : enregistreur de débogage |
| **Rig** : auto-rig IA (Sorceress) ; semi-automatique gratuit : squelette SMPL de 22 os affiché, articulations à placer et ajuster (gizmo, miroir, enfants, Maj+clic), os de poitrine, recalcul des poids | Rig Meshy (`/v1/rigging`, nœud `rig`, `fal.js`) ; Établi › Rig en lecture (carte des poids en affichage, pose d'essai non enregistrée) | **À faire** : auto-rig IA (Meshy, plus Tripo si T0 le trouve) ET semi-automatique local. Placement guidé des articulations sur le gabarit SMPL, ajustement au gizmo, miroir G/D, recalcul des poids (chaleur d'os ou distance géodésique, en Python pur testable) |
| Ombrage Wire / Solid / Texture / Tex+Wire / Weights ; centrer (guide X = 0, nudge, auto) ; tourner (pas, fin) ; vues caméra | `rendu3d.js` : Texturé / Argile / Fil de fer | **À faire** : barre d'affichage commune aux écrans (5 modes), outils de centrage et de rotation |
| **Refine** : peinture des poids (Select Bone, Paint, Lasso, Pose IK), Set/Add/Subtract/Smooth/Blur, taille, force, falloff, miroir, isoler, polys libres, raccourcis | Rien (U2 « conditionnel » dans les phases ultérieures de l'Établi) | **À faire** : écran **Affiner**. Opérations sur les poids en module pur (node), interface three.js, une commande par geste, annuler/rétablir |
| Corrections : orphelins, confinement des membres, reconstruire l'épaule, coutures, guérison dynamique, correctif en un clic, test de pose sur une animation | — | **À faire** : quatre corrections en Python pur (banc sur squelette synthétique), correctif en un clic = enchaînement, test de pose avec les clips de l'écran Animer |
| **Animate** : bibliothèque (générés, favoris, collections), clips jouables | Ids Meshy tapés à la main ; `ACTIONS_RIG` connaît 5 actions | **À faire** : catalogue Meshy parcourable (relevé T0), recherche, favoris, collections, lecture sur le modèle ouvert |
| Texte → animation : HY-Motion, Kimodo (poses de début et de fin) ; vidéo → animation GVHMR ; durée, intensité, multi-modèles | Vidéo → mouvement Uthana (payant) ; reciblage BVH/GLB (`mouvement_rig.recibler`) ; pas de texte → mouvement | **À faire** : HY-Motion par fal (`fal-ai/hunyuan-motion`, sortie `dict` JSON plutôt que FBX) reciblé par `mouvement_rig` ; Kimodo et GVHMR si T0 les trouve ; Uthana gardé. `mouvement.js` déménage dans Animer |
| Drive Mode (WASD, physique), Jiggle / Hair / Cloth / Hands, IK Gun / Sword / Hand, Bind Pose | — | **À faire** : Bind Pose et Drive Mode (aperçu clavier, sans physique). **Plus tard** : physique jiggle / cheveux / tissu, poses d'armes |
| **Export** : maillage seul / pose / animation (.glb), paquet three.js (runtime + AGENT_INSTRUCTIONS.md), clip .json, réglages physiques | `mesh_export.CIBLES` (blender, godot, unreal, unity) dans l'Établi ; export Godot du mouvement ; impression 3D | **À faire** : écran **Exporter** qui réunit tout : GLB maillage, pose ou animation, FBX (Blender), Godot (.tscn), Unreal / Unity, paquet three.js, impression 3D, envoi en Bibliothèque |
| **TreeGen** : 21 espèces (arbres, arbustes, couvre-sol), taille, échelle, niveaux de branches, feuillage réel ou cartes, 12 formes de feuille, saisons, densité, taille, retombée, rameaux, écorce, teintes, graine, vent (force, vitesse, direction, frémissement), ciel, stats, export GLB + recette + runtime, import de recette | Rien | **À faire** : écran **Décor › Végétation** sur **ez-tree** (MIT, `@dgreenheck/ez-tree`) vendorisé dans `frontend/lib3d/` avec sa licence. Préréglages d'espèces ; vent par shader (runtime exporté) ; recette `.treegen.json` → `.decor.json` ; GLB + LOD cartes |
| — (Sorceress n'a pas de décor généré) | GA 3D génère aussi des props (`BESOINS_3D` prop, décor) | **À faire** : écran **Décor › Accessoire** pour un élément de l'onglet 3D : budget de triangles, pivot au sol, échelle réelle en mètres, variantes (teinte, échelle, graine), masque de vent par hauteur pour une plante générée, LOD et cartes, envoi au Plateau 3D |
| 3D Procedural Walk (créatures à pattes) | — | **Plus tard** (non relevé) |
| Graphe de nœuds | Graphe Meshy (`NODES` : prompt, ref, preview, texture, remesh, rig, animate, export, etabli) = interface principale | **Adapté** : le graphe devient l'écran **Graphe** (vue avancée, lignée du job, relance d'un nœud). Chaque nœud renvoie à son écran : preview → onglet 3D, texture → Texture, remesh → Préparer, rig → Rig, animate → Animer, export → Exporter, etabli → Établi |
| — | Établi : réparer, décimer, couper, booléens, pièces, impression | **Adapté** : l'Établi devient un écran du 3D Studio. Ses outils de maillage nourrissent Préparer. Son onglet Rig en lecture est remplacé par Rig et Affiner |
| Envoi d'un écran à l'autre (« Send to … → ») | « Envoyer vers » 3D = Impression 3D seulement | **À faire** : liens profonds `/studio3d/?job=…&ecran=rig` ; Bibliothèque › Envoyer vers : 3D Studio (écran au choix), Décor, Plateau 3D, Impression |

## Décisions (à valider)

**D1 — Rôle des deux onglets.** L'onglet 3D crée et range ; le 3D Studio
transforme. Les post-actions de GA 3D (Optimiser, LOD, Textures) déménagent
dans Préparer et Exporter. Une carte de GA 3D ne garde que le téléchargement
brut, l'impression et « Ouvrir dans 3D Studio ▸ … ».

**D2 — Le graphe reste, en vue avancée.** On ne supprime pas le graphe Meshy :
il sert de lignée et de relance. Il cesse d'être l'entrée. Le retirer tout à
fait se décidera après l'usage.

**D3 — Le rig se fait aussi en local.** L'auto-rig IA (Meshy, payant) reste.
Le rig semi-automatique et la peinture des poids sont calculés chez nous
(Python pur, banc sur squelette synthétique) : gratuits, hors ligne, sans
limite de faces.

**D4 — Texture en deux temps.** D'abord la retexture IA « moteur » (Meshy
retexture, une requête). Ensuite la projection multi-vues avec nos modèles
d'image fal et les pinceaux de retouche (le gros morceau, « alpha » chez
Sorceress aussi).

**D5 — Animer par fal d'abord.** HY-Motion (`fal-ai/hunyuan-motion`) pour le
texte → mouvement, sortie JSON reciblée par `mouvement_rig` (pas de lecteur
FBX embarqué). La bibliothèque Meshy devient parcourable. Uthana reste pour la
vidéo. Toute route payante passe par devis, `confirme_cout` et le plafond
« moteurs3d ».

> **Révision de D5 après le relevé des API (t387, `2026-10-31-api-3d-releve.md`).** La licence de HY-Motion
> (« Tencent HY-MOTION 1.0 Community License ») exclut l'UE et le Royaume-Uni ; GVHMR interdit l'usage commercial ;
> Kimodo n'a pas d'API officielle. Le texte → mouvement passe donc d'abord par **Meshy Text to Motion** (API
> directe : « prime » en FBX, « swift » en BVH, lisible par `mouvement_rig`), HY-Motion n'étant gardé qu'après avis
> de l'utilisateur. Le rig Meshy est aussi sur fal (`fal-ai/meshy/rigging`, 0,20 $) ; fal n'a pas de rig Tripo.

**D6 — Décor sur ez-tree.** Végétation procédurale gratuite et
reproductible (graine + recette), vendorisée en licence MIT, exportée en GLB
avec un petit runtime de vent. Un accessoire généré dans l'onglet 3D s'ouvre
dans Décor › Accessoire.

**D7 — Fichiers générés.** `studio3d.js` (L9) et `etabli.js` (L8) ne se
retouchent pas à la main. Les écrans neufs sont des **modules à part**
(`frontend/studio3d/ecrans/*.js`, comme `comparer.js` ou `mouvement.js`),
chargés par `index.html`. Le graphe ne reçoit que des crochets par la saisie
L9. Le bundle (GA 3D) se modifie par un maillon de queue après dzapparence.

## Lots proposés

Ordre par valeur ; chaque tâche est livrable seule (voir le plan
`docs/superpowers/plans/2026-10-31-studio3d-ecrans.md`).

- **A — Socle et Créer** : relevé des API (T0), coque à écrans, onglet 3D =
  Créer, nouveaux moteurs.
- **B — Ouvrir, Importer, Préparer.**
- **C — Texture** (1/2 retexture IA, 2/2 projection et pinceaux).
- **D — Rig et Affiner** (rig, peinture des poids, corrections).
- **E — Animer et Exporter.**
- **F — Décor** (végétation, accessoire).
- **G — Établi intégré et clôture.**
