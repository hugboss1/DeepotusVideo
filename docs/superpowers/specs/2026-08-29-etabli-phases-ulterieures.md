# L'Établi — phases ultérieures : ce qui est écarté, pourquoi, et comment le reprendre

**Date :** 2026-08-29
**Statut :** feuille de route durable — aucune de ces phases n'est engagée
**Document parent :** `2026-08-29-etabli-inspecteur-3d-design.md` (phases P1→P5,
validées et engagées)

---

## 0. À quoi sert ce document

Le design de l'Établi écarte cinq capacités. Un non-but qui n'est pas analysé
redevient une analyse à refaire : ce document existe pour que **la reprise
d'une de ces cinq phases ne coûte pas une réanalyse**.

Chaque phase y porte donc, une fois pour toutes : ce qu'elle recouvre
exactement, pourquoi elle est écartée aujourd'hui, ce dont elle dépend, ce que
le dépôt possède déjà qui la sert, l'approche technique **déjà pesée**, les
pièges connus, le critère de banc qui la prouverait, un ordre de grandeur, et
un **verdict** — car trois de ces cinq phases ne devraient probablement jamais
être construites, et le dire vaut mieux que de les relitiger tous les six mois.

### 0.1 État du dépôt au moment de l'écriture

Ce qui suit était vrai le 2026-08-29 ; un lecteur ultérieur vérifiera avant de
s'y fier.

- La chaîne 3D va de `preview` à `animations` (`/studio3d` + `meshy_service`,
  bases `rigging` et `animations` allowlistées).
- Les artefacts sont versionnés `model.v{n}.glb` avec registre `report.json`
  (`mesh_report`), jamais écrasés.
- Les lecteurs GLB éprouvés : `print3d.lire_glb_triangles` (monde, transforms
  appliqués, refus motivé sur compression), `mesh_optimize.glb_stats`,
  `mesh_report.gltf_inventory`.
- `gltf_builder` écrit des GLB **procéduraux** auto-suffisants ; il n'opère pas
  de chirurgie sur un GLB existant.
- Le Plateau (`2026-08-29-plateau-previsualisation-3d-design.md`) est **conçu,
  non construit**.
- Aucun écrivain FBX local, et il n'y en aura pas (format fermé Autodesk).

### 0.2 Les cinq phases en une ligne

| | Phase | Verdict | Déclencheur de reprise |
|---|---|---|---|
| **U1** | Création d'animation (clips, courbes) | **à construire** | dès qu'on veut *produire* une animation et non seulement la juger |
| **U2** | Peinture des poids d'influence | **conditionnel** | si la heatmap de P4 montre des défauts récurrents |
| **U3** | Sculpture et retopologie | **ne pas construire** — router dehors | jamais ; reprendre seulement l'aller-retour Blender |
| **U4** | Matériaux et UV | **scinder** : matériaux oui, UV non | matériaux dès qu'une teinte est à corriger |
| **U5** | Convergence du Plateau vers ce canevas | **quand le Plateau existera** | dès que le Plateau veut un gizmo |

---

## U1 — Création d'animation

### Ce que c'est

Poser des clés de rotation d'os dans le temps et **écrire un clip glTF** : un
`animations[i]` avec ses `samplers` (accesseur d'entrée = les temps, accesseur
de sortie = les valeurs) et ses `channels` (chacun visant
`node.rotation | translation | scale`).

### Pourquoi c'est écarté aujourd'hui

Parce que c'est la **première opération de tout le chantier qui ajoute des
données binaires** au lieu d'en recopier. La propriété qui rend `mesh_edit` sûr
— extraire et transformer sont des recopies d'octets, jamais des décodages —
ne tient plus. C'est un changement de nature, pas de volume : il mérite sa
phase.

### Ce dont elle dépend

P4 (rig affiché, test de pose). Le geste d'auteur *existe déjà* à la fin de
P4 : poser un os. U1 n'ajoute que « enregistrer cette pose à l'instant t ».

### Ce que le dépôt a déjà

- `AnimationMixer` lit les clips (P4) — le même mixer relit ce qu'on écrit ;
- `rig_inventory` liste clips et durées ;
- `mesh_report.gltf_inventory` compte `animations` — un banc a donc déjà de quoi
  vérifier qu'un clip est apparu ;
- **le vocabulaire de keyframe du Plateau** : `{"t": float, "easing": str}`.
  **À réutiliser tel quel**, surtout pas à réinventer — deux modèles de timeline
  concurrents dans le même dépôt seraient exactement la dette que ce document
  cherche à éviter.

### Approche pesée

Le navigateur enregistre des poses en JSON —
`[{"t": 0.0, "os": {"spine": [x,y,z,w], …}}, …]` — et **le serveur écrit**,
conformément à la règle de l'option C. Un module `mesh_anim.py` ajoute au
document glTF les accesseurs de temps (scalaire, avec `min`/`max` — le glTF les
**exige** sur l'entrée d'un sampler) et de valeurs (vec4 pour les quaternions),
puis les samplers et channels.

Interpolation `LINEAR` par défaut, `STEP` en option. `CUBICSPLINE` est écarté :
il triple la taille de l'accesseur de sortie (tangente entrante, valeur,
tangente sortante) pour un gain que la pose main-levée ne justifie pas.

### Le piège connu, écrit d'avance

**Les sauts de signe de quaternion.** Deux clés successives peuvent décrire la
même rotation avec des quaternions de signes opposés ; un lecteur glTF interpole
naïvement et le membre part faire le tour dans le mauvais sens. La correction
est côté serveur, à l'écriture : si `dot(q_précédent, q) < 0`, écrire `-q`.
C'est trois lignes, et c'est invisible tant qu'on n'a pas vu un bras se
retourner.

Second piège : un clip qui vise un nœud absent du `skin` produit un fichier
valide qui n'anime rien. Le serveur refuse une cible hors squelette.

### Ce qu'un banc prouverait

Écrire un clip de deux clés sur un GLB rigué connu, puis : `gltf_inventory`
compte une animation de plus ; les accesseurs relus donnent les temps attendus
et des quaternions normés ; deux clés en opposition de signe ressortent
hémisphère-continues ; une cible hors squelette est refusée avec un message.

### Ordre de grandeur

Moyen. Un module `mesh_anim.py`, deux routes, une timeline dans le panneau Rig.

### Verdict

**À construire** — c'est la seule suite qui fait que « préparer la phase
d'animation » débouche sur quelque chose d'écrit, et non seulement de jugé.

---

## U2 — Peinture des poids d'influence

### Ce que c'est

Corriger `WEIGHTS_0` et `JOINTS_0` par sommet : quel os tire quelle partie du
maillage, et à quelle force.

### Pourquoi c'est écarté aujourd'hui

Deux raisons franches. D'abord, c'est de la **vraie chirurgie d'attributs de
géométrie** — écrire dans un accesseur de sommets, là où P1→P5 ne touche que le
JSON ou recopie des octets. Ensuite, on ne sait pas encore si le besoin existe :
la heatmap de P4 est précisément l'instrument qui le dira.

### Ce dont elle dépend

P4 seulement.

### Contraintes glTF à ne pas redécouvrir

- `WEIGHTS_0` est un **vec4** : quatre influences par sommet au maximum dans le
  socle. Au-delà il faut `WEIGHTS_1`, que beaucoup de moteurs ignorent.
- Les poids d'un sommet **doivent sommer à 1**. Un fichier qui viole cette règle
  s'affiche correctement chez l'un et explose chez l'autre.
- Le `componentType` peut être `FLOAT` (5126), `UNSIGNED_BYTE` (5121) ou
  `UNSIGNED_SHORT` (5123) **normalisé**. Écrire du flottant dans un accesseur
  normalisé en octets produit un maillage en confettis. Lire le type avant
  d'écrire, toujours.

### Approche pesée

Brosse dans le navigateur sur les attributs déjà décodés par `GLTFLoader` ;
renvoi d'un **diff épars** `{index_sommet: {joints, poids}}` plutôt que de
l'accesseur entier — un maillage de 500 000 sommets ne transite pas par une
requête JSON. Le serveur renormalise, refuse les `NaN`, respecte le
`componentType` d'origine, et écrit une nouvelle version.

### Ce qu'un banc prouverait

Après repeinte : tout sommet somme à 1 (à 1e-4 près) ; le `componentType` est
inchangé ; le nombre de sommets est inchangé ; un diff contenant un `NaN` est
refusé.

### Ordre de grandeur

Moyen à grand — l'écriture est cadrée, c'est l'ergonomie de brosse qui coûte.

### Verdict

**Conditionnel, avec un critère mesurable.** Si la heatmap de P4 révèle des
défauts récurrents sur les rigs Meshy, U2 se paie tout seul. Si les rigs sont
sains, U2 est un ornement coûteux. **Décider sur la donnée que P4 aura produite,
pas sur l'intuition.**

---

## U3 — Sculpture et retopologie

### Ce que c'est

Modifier la géométrie elle-même : déformer, ajouter de la matière, refaire le
maillage.

### Verdict, d'abord

**Ne pas construire.** Ce n'est pas un arbitrage de calendrier, c'est un
arbitrage de nature : la sculpture est un produit à part entière — Blender et
ZBrush y ont chacun des décennies — et la retopologie est **déjà disponible dans
la chaîne** :

- `openapi/v1/remesh` chez Meshy, avec topologie quad et polycount cible, déjà
  câblé dans le nœud `03 · topologie` du 3D Studio ;
- `mesh_optimize` / gltfpack en local et gratuit, pour la décimation.

Construire un sculpteur dans l'Établi reviendrait à concurrencer Blender avec
un canevas de 800 Ko. Ce serait perdu d'avance et personne n'en a besoin.

### Ce qu'il faut construire à la place, si le besoin apparaît

**L'aller-retour.** P5 exporte déjà vers Blender en un clic ; ce qui manque est
le chemin du retour :

> Un bouton « importer une version corrigée » qui accepte un GLB revenu de
> Blender, calcule sa fiche `mesh_report`, et l'**ajoute au registre du job**
> comme `model.v{n}.glb` — jamais un écrasement, exactement comme les autres
> versions.

C'est petit — une route d'upload, un appel à `write_report`, une entrée de
registre — et c'est cela, la vraie fonctionnalité. Elle transforme Blender en
outil de l'atelier au lieu d'en faire une impasse.

Piège à noter : un GLB revenu de Blender a très probablement perdu le `skin` si
l'utilisateur n'a pas exporté les armatures. La fiche doit **comparer les
`skins` avant/après** et avertir — sinon un rig payé disparaît en silence.

### Ordre de grandeur

Petit, pour l'aller-retour seul.

---

## U4 — Matériaux et UV

Une seule ligne dans les non-buts, mais **trois choses de coûts très
différents**. Les scinder est l'essentiel de l'analyse.

### U4a — Facteurs de matériau · **oui, et c'est bon marché**

`baseColorFactor`, `metallicFactor`, `roughnessFactor`, `emissiveFactor`,
`alphaMode`, `doubleSided` : tout cela vit dans `materials[]`, **en JSON pur**.
L'opération a exactement la même propriété de sûreté que `transformer` — le
tampon binaire ressort identique octet pour octet — et se glisse dans
`mesh_edit` sans rien changer à son architecture.

> **Piège à ne pas retomber dedans :** glTF exige des facteurs de couleur
> **linéaires**, l'interface donne du sRGB. `gltf_builder._srgb_to_linear`
> existe déjà et fait la conversion. **Le réutiliser**, ne pas le réécrire :
> une conversion oubliée donne des couleurs délavées que personne ne
> soupçonnera d'être un bug d'unité.

Ordre de grandeur : petit. Un banc trivial : changer une teinte, vérifier que
le tampon binaire est inchangé et que le facteur relu est bien la valeur
linéarisée.

### U4b — Remplacement de texture · **possible, moyen**

Remplacer les octets d'une image, c'est remplacer un `bufferView` : les octets
autour sont recopiés, celui-là est substitué, les décalages sont réalignés.
Cousin direct d'`extraire`. Le piège est la taille — remplacer une 4K par une
1K change la longueur du tampon, donc **tous** les décalages suivants.

Ordre de grandeur : moyen.

### U4c — Édition des UV · **non**

Dépliage, coutures, empaquetage : un éditeur à part entière. Et là encore le
dépôt a déjà la sortie — `openapi/v1/uv-unwrap` est **déjà dans
`ALLOWED_BASES`** et n'attend qu'un appel, tandis que Blender le fait mieux que
quiconque.

**Router dehors, ne pas construire.**

---

## U5 — Convergence du Plateau vers le canevas de l'Établi

### Ce que c'est

Faire migrer le Plateau de `<model-viewer>` vers le canevas three.js partagé,
pour qu'il gagne les gizmos et la scène multi-objets sans composition serveur.

### Le déclencheur, écrit d'avance

**Dès que le Plateau veut déplacer un décor à la main.** Sa conception actuelle
assume des champs numériques précisément parce que `<model-viewer>` n'a pas de
gizmo ; c'est un choix raisonné, pas une préférence. Le jour où le placement à
la main devient le geste dominant, le calcul s'inverse.

Second déclencheur : quand la recomposition serveur du GLB de scène à chaque
retouche devient le goulot d'étranglement.

### Ce que la migration gagne

Plus d'aller-retour de composition à chaque édition · gizmos de placement ·
sélection par instance · et la possibilité de **voir le squelette d'un
personnage à l'intérieur d'un cadre** — ce qu'aucun des deux outils ne sait
faire seul aujourd'hui.

### Ce qu'elle risque de perdre — le vrai piège

**La capture.** `<model-viewer>.toBlob()` donne au Plateau ses images de
première et dernière frame, qui partent nourrir `shot.keyframe_image` et
`shot.keyframe_end` d'un rendu vidéo **payant**. En three.js l'équivalent est
une relecture explicite du canevas du renderer, et elle doit rester **exacte au
pixel** : même ratio letterbox, mêmes dimensions. Une capture qui dérive de
quelques pixels décale la composition que le modèle vidéo reçoit.

Second point, moins visible : `<model-viewer>` fournit un environnement neutre
et son éclairage image. three.js n'en a pas par défaut — sans une carte
d'environnement (addon `RoomEnvironment` ou équivalent servi localement), la
matière ne ressemble plus à ce qu'elle était, et les jugements de cadrage se
feraient sur une image plus sombre.

### Ce qui est déjà en place pour que ce jour coûte peu

`frontend/lib3d/` — le chargeur et les aides caméra y vivent **dès P2**,
partagés, précisément pour cela.

### Précondition

Le Plateau doit exister. Au 2026-08-29 il est conçu, non construit, et **ses
phases P1 à P3 ne dépendent en rien** du présent design.

### Ordre de grandeur

Moyen, et entièrement dans le frontend.

---

## Ce que ce document n'autorise pas

Il décrit des reprises possibles ; il n'en engage aucune. Chaque phase reprise
repasse par la porte habituelle du dépôt : brainstorming, design validé, plan,
puis exécution — et chacune déclare sa dépense avant de la faire.
