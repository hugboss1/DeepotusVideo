# L'Établi — inspecteur 3D en bout de chaîne : parties, rig, versions, export moteurs

**Date :** 2026-08-29
**Statut :** design validé section par section — rien n'est codé
**Demande (verbatim) :** « revise la section 3d studio pour ajouter en bout de
chaine un visualisateur 3D sur un grand canva pour faire des corrections et des
séparations de parties du modéle ainsi que de visualiser les rigs du mesh pour
préparer la phase d'animation. le workflow actuel montre la chaine de bout en
bout, depuis le nouveau visualisateur je dois pouvoir sélectionner le modéle a
chacune de ses étapes pour pouvoir m'assurer que tout est bien cohérent et
eventuellement pouvoir l'exporter directement vers un lien vers blender, unity,
unreal, godot... »

**Suite différée :** `2026-08-29-etabli-phases-ulterieures.md` — les cinq
capacités que ce design écarte y sont analysées pour être reprises sans
réanalyse.

---

## 1. Ce que l'Établi sert à décider

Le 3D Studio livre aujourd'hui une chaîne complète — preview, texture, remesh,
rig, animations, export — et son graphe la montre bien. Ce qu'il ne donne pas,
c'est un endroit pour **regarder ce qui est sorti**. Un maillage se juge
aujourd'hui sur une vignette de 200 px et un compte de triangles.

Trois questions restent donc sans réponse au moment où elles comptent :

1. **Le modèle est-il cohérent d'une étape à l'autre ?** Le remesh a-t-il mangé
   la silhouette ? Le rig a-t-il déplacé l'origine ? La texture a-t-elle touché
   à la géométrie — ce qu'elle ne devrait jamais faire ?
2. **Le rig tient-il ?** Un bras qui tire l'oreille se voit sur un squelette et
   une carte de poids. Il ne se voit sur aucune vignette, et surtout pas avant
   d'avoir payé les animations qui l'utilisent.
3. **La pièce est-elle utilisable ailleurs ?** Un maillage qui ne rentre ni dans
   Blender ni dans Unity n'est pas un asset, c'est un fichier.

L'Établi répond aux trois, et il le fait **gratuitement** : tout ce qu'il
calcule est local. La seule dépense possible de tout ce design est une
conversion FBX à 1 crédit, optionnelle et confirmée (§8).

## 2. La contrainte tranchée d'emblée

Le seul moteur 3D embarqué est `<model-viewer>` 3.3.3
(`/assets/model-viewer.min.js`, 956 Ko), piloté par
`frontend/cardforge/js/mod-forge3d.js`.

**Ce qu'il sait faire — vérifié dans le bundle, pas supposé.** Les symboles
`materialFromPoint`, `positionAndNormalFromPoint`, `setAlphaMode`,
`availableAnimations`, `animationName` et `timeScale` y sont bien présents. Il
sait donc désigner un matériau au clic, en masquer par alpha, et jouer les clips
nommés avec vitesse et boucle. C'est plus que ce qu'on lui prête d'ordinaire.

**Ce qu'il n'expose nulle part :** le squelette, les poids d'influence, la pose
d'un os, les gizmos de manipulation, et l'isolation par *nœud* — il ne connaît
que le matériau. Or la demande porte exactement là.

### 2.1 Les trois options pesées

| | Option A — three.js seul | Option B — model-viewer + composition serveur | **Option C — retenue** |
|---|---|---|---|
| Interaction | complète | aucune (un aller-retour par clic) | complète |
| Test de pose, gizmos | oui | **impossible par construction** | oui |
| Qui écrit les fichiers | le navigateur | le serveur | **le serveur** |
| Testable par `run-tests.ps1` | non | oui | **oui** |
| Provenance versionnée | contournée | respectée | **respectée** |

L'option B est la doctrine du Plateau (§12) et elle est bonne pour lui ; elle ne
peut pas livrer cette demande-ci — un test de pose en direct exigerait un GLB
par pose.

L'option A livrerait tout, mais mettrait l'écriture des fichiers dans le
navigateur : `GLTFExporter` produirait des GLB que `run-tests.ps1` ne peut pas
vérifier, et qui contourneraient le registre `model.v{n}.glb` + `mesh_report`
sur lequel toute la phase D repose. On gagnerait une démonstration, on perdrait
la provenance.

**Option C — le navigateur voit et manipule, Python écrit.** Le canevas est en
three.js et fait tout l'interactif. Quand une correction est validée, il envoie
des **paramètres** — une liste de nœuds, une matrice, une cible d'export — et le
serveur écrit le GLB, l'ajoute au registre, lui calcule sa fiche.

La conséquence testable, qui est la raison du choix : un banc peut affirmer
« extraire les nœuds [3, 7] de `model.glb` produit un GLB dont
`print3d.lire_glb_triangles` voit N triangles et telle boîte englobante », sans
navigateur, dans le harnais habituel.

### 2.2 Sur le poids de three.js

Environ 800 Ko vendorisés — chiffre **à mesurer au moment du plan**, pas repris
d'un souvenir — face aux 956 Ko de `model-viewer.min.js` déjà servis. Ce n'est
pas une dépendance d'une nouvelle nature : `model-viewer` **embarque déjà
three.js**, il l'enferme derrière une API qui ne montre ni os ni nœud. C'est le
même moteur, exposé.

Vendorisation locale obligatoire, comme `model-viewer` : aucun CDN, l'app doit
fonctionner sans réseau.

## 3. Où ça vit

`/etabli` — page servie par FastAPI, vanilla, **hors du bundle minifié**, même
patron que `/studio3d`, `/atelier`, `/cardforge`, `/spritelab`. Aucune chirurgie
de `frontend/dist/assets/index-*.js`.

Le nom la distingue du **Plateau** (`2026-08-29-plateau-previsualisation-3d-design.md`) :
le Plateau cadre un plan avant un tir vidéo, l'Établi travaille un maillage avant
l'animation. Deux métiers, deux noms.

### 3.1 Le nœud 07 dans le graphe du 3D Studio

La demande dit « en bout de chaîne » et le graphe doit le montrer : un nœud
`07 · établi` après `06 · export`, et le câble qui l'y relie.

Le graphe de `/studio3d` a des coordonnées au pixel près dans une
`viewBox 0 0 740 330`, où le nœud `export` (x 608, largeur 132) occupe déjà le
bord droit. L'ajout impose donc d'élargir la `viewBox` à `0 0 892 330` et la
largeur CSS du `.graph`. **Le changement est confiné à trois constantes** —
`NODES`, `CABLES`, la `viewBox` — et aucune autre géométrie ne bouge. C'est dit
ici pour que personne ne le découvre en cours de route.

Second point d'entrée : le rail gauche, section « Étape suivante », à côté du
« 04 · Sprite Sheet → » existant.

## 4. Le grand canevas

`frontend/etabli/{index.html, etabli.js, etabli.css}` et une bibliothèque
partagée `frontend/lib3d/` (chargeur, aides caméra) — partagée délibérément,
voir §12.

three.js servi depuis `/assets/three/` : `three.module.js` plus quatre addons —
`GLTFLoader`, `OrbitControls`, `TransformControls`, et les décodeurs `meshopt` et
`DRACO`. Sans les décodeurs, un GLB compressé s'affiche noir au lieu de
s'afficher : ils ne sont pas un confort. **Pas de `GLTFExporter`** — c'est la
règle de l'option C, et son absence du bundle la rend impossible à enfreindre
par mégarde.

Disposition :

- **centre** — le canevas, tout l'espace ;
- **gauche** — la vie du modèle : ses étapes, dans l'ordre (§5) ;
- **droite** — quatre onglets : *Parties*, *Rig*, *Fiche*, *Export* ;
- **bas** — une barre d'état : fichier chargé, triangles, sha256, et
  **les modifications en attente d'écriture**.

### 4.1 Le seuil de charge, affiché

Un maillage texturé pèse vite 200 Mo. L'Établi lit d'abord la fiche
(`mesh_report`), affiche le compte de triangles **avant** de charger, et propose
la version décimée (`mesh_optimize`, preset `prop`) au-delà d'un seuil.

**Seuil par défaut : 300 000 triangles ou 80 Mo de fichier, le premier atteint.**
Il est **configurable et montré à l'écran**, jamais caché — même doctrine que
les seuils d'`asset3d_qc` : c'est une convention de confort machine, pas une
loi. Franchir le seuil n'interdit rien ; cela propose la version allégée et
laisse le choix, en affichant les deux comptes.

## 5. Sélectionner le modèle à chacune de ses étapes

C'est le cœur de la demande, et la partie la moins visible du travail. Trois
registres racontent aujourd'hui la même histoire sans se parler :

| Source | Ce qu'elle porte | État |
|---|---|---|
| `MeshyTaskRecord` via `meshy_service.list_tasks()` | preview, texture, remesh, **rig**, animate, export — binaires rapatriés dans `outputs/meshy3d/<id>/`, servis par `/api/meshy3d/files/…` | existe |
| Registre `report.json` d'un job `assets3d` (`mesh_report.read_registry`) | `model.glb`, `model.v2.glb`… chacun avec sha256, triangles, bbox, inventaire de textures | existe |
| `model.opt.glb` (`mesh_optimize`) | la version décimée | existe |

Un service neuf **`mesh_sources.py`** les fond en une liste normalisée :

```json
{"source": "meshy|assets3d", "id": "...", "etape": "rig",
 "libelle": "04 · squelette", "url": "/api/...", "version": 2,
 "sha256": "...", "triangles": 30412, "date": "2026-08-29T..."}
```

Il **lit ce qui existe** : aucune table, aucune migration.

### 5.1 La comparaison A/B

Cliquer charge une étape. **Alt-cliquer charge la seconde en comparaison** :
deux vues côte à côte, caméras synchronisées, et sous elles la ligne d'écart
tirée des deux fiches `mesh_report` — triangles, dimensions, textures, sha256.

« M'assurer que tout est bien cohérent » cesse alors d'être une impression. Le
remesh a-t-il perdu 40 % de la silhouette ? La texture a-t-elle touché la
géométrie ? Le rig a-t-il déplacé l'origine ? Trois questions, trois réponses
chiffrées à l'écran.

## 6. Les corrections — le navigateur propose, Python écrit

Service neuf **`mesh_edit.py`**, stdlib pure, lisant le GLB avec le même lecteur
de chunks que `mesh_report._gltf_json` et `print3d._chunks`.

### 6.1 Quatre opérations

**`extraire(glb, nœuds) -> glb`** — garde un sous-ensemble de nœuds, élague les
accesseurs, bufferViews, matériaux et images devenus orphelins, reconstruit le
tampon en réalignant les décalages.

> **Propriété remarquable, et c'est elle qui rend l'opération sûre :** c'est une
> **recopie d'octets, jamais un décodage de géométrie**. Les bufferViews retenus
> sont copiés tels quels. L'extraction fonctionne donc sur un GLB Draco ou
> meshopt, là où `lire_glb_triangles` refuse honnêtement. La séparation de
> parties marche y compris sur les fichiers que le reste du dépôt ne sait que
> compter.

**`transformer(glb, {nœud: TRS}) -> glb`** — n'écrit que le JSON. Le tampon
binaire ressort **identique octet pour octet** ; c'est vérifiable au banc, et
c'est ce qui rend l'opération sûre sur un fichier de 200 Mo.

**`reparer(glb, axe_haut=, echelle=, recentrer=) -> glb`** — une matrice sur le
nœud racine. Le recentrage a besoin de la boîte englobante, donc de
`lire_glb_triangles` : sur un fichier compressé il refuse avec un message qui le
dit, pendant que les trois autres opérations passent. La dégradation est
partielle et explicite, jamais un échec global.

**`ecrire(job, glb, extra)`** — **jamais d'écrasement.** Le résultat part en
`model.v{n}.glb` via `asset3d_service.next_version()`, avec sa fiche
`mesh_report.write_report()`. Doctrine §2.1 du plan d'ensemble, inchangée.

### 6.2 Une seule provenance

Quand la source est une tâche Meshy sans job `assets3d` — elle vit dans
`outputs/meshy3d/<id>/`, qui n'a pas de registre — un job `assets3d` est **créé
pour l'accueillir**, et la fiche note d'où il vient. Une seule provenance, pas
deux modèles concurrents.

### 6.3 La règle d'or à l'écran

**Tant que « écrire la version » n'a pas été cliqué, rien n'a bougé sur le
disque.** La barre du bas énumère les modifications en attente. Isoler, masquer,
poser un os, bouger un gizmo : tout cela est du regard, pas de l'écriture.

### 6.4 Trois granularités de sélection

Les moteurs ne découpent pas pareil — un modèle Meshy est souvent un nœud unique
à plusieurs matériaux, un Tripo plusieurs nœuds. L'Établi sélectionne donc **par
nœud, par maillage, ou par matériau**, au choix.

L'isolation est un affichage. L'extraction est ce qui écrit.

## 7. Le rig — instrument de lecture

### 7.1 Côté serveur, une seule fonction

**`rig_inventory(glb)`** — noms des os, hiérarchie, nombre, skins, clips et leurs
durées. Elle ne lit que le chunk JSON : instantanée, testable, et elle permet de
dire « ce maillage n'a pas de squelette » **avant** de télécharger 200 Mo pour le
découvrir. `mesh_report.gltf_inventory` compte déjà `skins` et `animations` ;
`rig_inventory` en est le détail.

### 7.2 Côté navigateur, tout le reste

three.js le fait nativement : os dessinés par-dessus le maillage
(`SkeletonHelper`), arbre cliquable alimenté par `rig_inventory`, chaîne
surlignée à la sélection, **heatmap des poids** peinte en couleurs de sommets sur
un matériau cloné (les données `JOINTS_0`/`WEIGHTS_0` sont décodées par
`GLTFLoader`), **test de pose** par rotation d'os avec retour à la pose de repos,
**lecture des clips** par `AnimationMixer` avec timeline, vitesse, boucle et pas
à l'image.

### 7.3 Ce que le rig ne fait pas ici

**Rien n'est écrit.** L'Établi ne crée pas d'animation : il juge celle qu'on a
payée, et il montre le rig raté avant qu'on la paie. La correction des poids et
la création de clips sont analysées dans le document des phases ultérieures.

Limite honnête à afficher : les rigs Meshy sont orientés humanoïdes. Un
personnage non humanoïde — une pieuvre, par exemple — peut recevoir un squelette
étrange. **C'est une donnée, pas un bug** : l'Établi la montre au lieu de la
lisser.

## 8. L'export, sans enjoliver

Ces quatre cibles ne sont pas des cibles réseau : ce sont des formats et des
conventions d'import. L'export écrit donc le bon format, avec le bon axe haut et
la bonne échelle, et une fiche d'import courte.

| Cible | Écrit localement | Axe / échelle écrits | Ce que fait l'importeur |
|---|---|---|---|
| **Blender 4** | GLB | Y-up, mètres (standard glTF) | convertit lui-même en Z-up (option « +Y up », active par défaut) |
| **Godot 4** | GLB | Y-up, mètres | Godot est Y-up : rien à convertir |
| **Unreal 5** | GLB | Y-up, mètres | Interchange convertit en Z-up et met à l'échelle centimètre |
| **Unity 6** | GLB + note | Y-up, 1 u = 1 m | **greffon requis** — glTFast, gratuit et standard |

> **Correction assumée sur une première rédaction de cette table.** Elle
> annonçait un axe Z et un facteur ×100 pré-cuits pour Unreal. C'est une
> erreur : ces importeurs convertissent **déjà** depuis le glTF standard, et
> pré-cuire la conversion produirait un modèle tourné deux fois et cent fois
> trop grand. Le défaut correct est donc le **glTF standard pour les quatre**,
> et ce que l'export apporte n'est pas une rotation mais le bon format, une
> échelle déclarée en mètres, la fiche d'import qui dit ce que le moteur va
> faire, et le chemin de dépôt.
>
> Les surcharges `axe_haut` et `echelle` restent offertes — elles servent aux
> pipelines qui désactivent la conversion à l'import — mais elles sont un
> choix explicite, jamais le défaut.

### 8.1 La vérité sur le FBX

**Le dépôt ne sait pas écrire de FBX, et ne le saura pas** : c'est un format
fermé d'Autodesk, hors de portée de la stdlib. Le vérifier a été rapide —
`asset3d_service` ne récupère de `.fbx` que ce que les fournisseurs livrent.

Le FBX n'est donc proposé que **là où il existe déjà** :

- un `model.fbx` déjà présent dans le dossier du job (Meshy, Tripo et Rodin le
  livrent quand le moteur le supporte) ;
- ou une conversion `openapi/v1/convert` sur une tâche Meshy — base déjà
  allowlistée dans `meshy_service.ALLOWED_BASES` — **1 crédit, derrière la porte
  de coût habituelle, jamais en silence**.

Unity est le seul des quatre moteurs que cela gêne, et son contournement
(glTFast) est gratuit et standard.

### 8.2 Les quatre gestes, avec leur honnêteté respective

**Préparer** — écrit le fichier converti plus un `import.md` de quelques lignes
(axe, échelle, greffon éventuel, ce que contient le fichier).

**Ouvrir l'application** — chemin d'exécutable dans les Settings, même patron que
`print3d.ouvrir_dans_slicer`. Ce geste est **réellement** un « ouvrir » pour
Blender (`--python-expr` importe le glTF au lancement). Pour Unity, Unreal et
Godot, « ouvrir l'app sur un fichier » n'existe pas — ils importent par dossier.
Le bouton s'y nomme donc « ouvrir le projet », ce qu'il fait vraiment. Un libellé
par cible, pas un libellé qui ment pour trois cibles sur quatre.

**Déposer dans le projet** — dossier surveillé par moteur (`Assets/` d'un projet
Unity, `Content/` d'un Unreal, un dossier de projet Godot), configuré une fois
dans les Settings.

> C'est la **seule fonction de tout ce design qui écrit hors de `outputs/`**, et
> elle mérite sa garde. Le chemin doit être configuré explicitement, exister, et
> être confirmé une fois ; aucune valeur par défaut. Et surtout : avant de
> déclarer le dépôt réussi, le dossier cible est sondé par
> `fs_guard.probe_write_visibility()` — le canari né de l'incident MSIX de
> juin-juillet 2026, où des écritures semblaient réussir tout en partant dans un
> overlay invisible. Déposer un asset dans un projet Unity est exactement ce
> cas-là. Un dépôt qui ne se voit pas est un dépôt raté, et il doit le dire.

**Copier l'URL locale** — une ligne, pour les importeurs qui acceptent une URL ou
pour passer le fichier à une autre machine du réseau.

## 9. API

| Route | Rôle |
|---|---|
| `GET /api/etabli/sources` | la chronologie unifiée des étapes (§5) |
| `GET /api/etabli/rig` | inventaire du squelette d'une source (§7.1) |
| `POST /api/etabli/extraire` | `{source, nœuds}` → nouvelle version + fiche |
| `POST /api/etabli/transformer` | `{source, transforms}` → nouvelle version + fiche |
| `POST /api/etabli/reparer` | `{source, axe, échelle, recentrer}` → nouvelle version + fiche |
| `POST /api/etabli/export` | `{source, cible}` → fichier + `import.md` |
| `POST /api/etabli/ouvrir` | `{cible}` → lance l'application (Settings) |
| `POST /api/etabli/deposer` | `{source, cible}` → écrit dans le dossier du projet, canari vérifié |

Tout est local et gratuit, à la seule exception de la conversion FBX Meshy
(§8.1), qui passe par le proxy existant et sa porte de coût.

## 10. Phases

- **P1 — Le socle serveur, sans une ligne d'UI.** `mesh_edit.py` et
  `mesh_sources.py`. Bancs à l'octet, patron `test_print3d.py` : extraire les
  nœuds d'un GLB fabriqué par `gltf_builder.build_glb` et relire le résultat
  avec `print3d.lire_glb_triangles` (triangles et bbox conformes) ; vérifier
  qu'un `transformer` laisse le tampon binaire identique octet pour octet ;
  vérifier qu'un GLB compressé **passe l'extraction et refuse le recentrage**,
  avec le message qui le dit ; vérifier que `mesh_sources` fond les trois
  registres sans en inventer un quatrième.
- **P2 — Le canevas.** Vendorisation three.js (poids mesuré et noté), page
  `/etabli`, chargement, chronologie des étapes, comparaison A/B synchronisée,
  seuil de charge, nœud `07 · établi` et élargissement de la `viewBox` dans
  `/studio3d`.
- **P3 — Parties.** Sélection par nœud / maillage / matériau, isolation,
  masquage, gizmos `TransformControls`, extraction et transformation avec
  écriture versionnée derrière le bouton d'écriture.
- **P4 — Rig.** `rig_inventory`, squelette, arbre, chaîne surlignée, heatmap des
  poids, test de pose, lecture des clips.
- **P5 — Export.** Les quatre cibles, la fiche d'import, l'ouverture
  d'application, le dépôt projet avec canari, l'URL locale, et le FBX quand il
  existe.

**Coût API du chantier : 0 $**, la conversion FBX Meshy (1 crédit) étant
optionnelle, confirmée, et stubbée aux bancs.

## 11. Risques mesurés

| Risque | Mitigation |
|---|---|
| Un second moteur de rendu à maintenir | version épinglée, servie localement comme `model-viewer`, point d'entrée unique `frontend/lib3d/` partagé avec le Plateau |
| Un GLB de 200 Mo met le canevas à genoux | fiche lue d'abord, triangles affichés **avant** chargement, version décimée proposée au-delà d'un seuil montré |
| La chirurgie GLB est un nid à bugs d'octets | le banc relit le résultat avec `print3d.lire_glb_triangles`, le lecteur déjà éprouvé : si la chirurgie ment, le lecteur le voit |
| Écrire hors de `outputs/` | chemin explicite, existant, confirmé, sans défaut — **et sondé au canari `fs_guard`** avant de déclarer le succès |
| Un GLB compressé casse une opération | l'extraction et la transformation passent (recopie d'octets) ; seul le recentrage refuse, et il le dit |
| Un rig Meshy humanoïde sur une créature qui ne l'est pas | c'est une donnée : l'Établi la montre |
| Le test de pose pris pour de l'animation | rien n'est écrit, et un bouton remet la pose de repos |
| L'élargissement de la `viewBox` casse le graphe | changement confiné à `NODES`, `CABLES` et la `viewBox` ; aucune autre coordonnée ne bouge |

## 12. Frontière avec le Plateau

Le dépôt aura deux visualiseurs 3D. Qu'ils s'ignorent serait une dette ; qu'ils
fusionnent serait une erreur.

**Mutualisé, et en Python** — la décimation `mesh_optimize`, les artefacts
versionnés `model.v{n}.glb`, la fiche `mesh_report`, la provenance Library, et le
module d'écriture GLB introduit ici.

**Non mutualisé — le moteur de rendu.** Le Plateau a besoin d'un letterbox, d'une
orbite et de `toBlob()` : `model-viewer` fait exactement cela, et l'en déloger
serait du travail pour rien. L'Établi a besoin de désigner un nœud, dessiner des
os et poser une articulation : `model-viewer` ne l'expose pas.

**La condition de convergence, écrite d'avance.** Si le Plateau réclame un jour
des gizmos de placement — et il les réclamera dès qu'on voudra bouger un décor à
la main — **il migre vers le canevas de l'Établi, pas l'inverse**. Pour que ce
jour-là coûte peu, le chargeur et les aides caméra vivent dès maintenant dans
`frontend/lib3d/`, partagé, plutôt qu'enfouis dans la page. L'analyse de cette
migration est en phase ultérieure U5.

## 13. Ce que ce design ne fait PAS

Dit franchement pour que personne ne l'attende — **et analysé en détail dans
`2026-08-29-etabli-phases-ulterieures.md`, pour que la reprise ne coûte pas une
réanalyse** :

| | Écarté ici | Repris en |
|---|---|---|
| Création d'animation, courbes, clips | oui | **U1** |
| Peinture des poids d'influence | oui | **U2** |
| Sculpture et retopologie | oui | **U3** (avec une recommandation de ne pas le construire) |
| Édition des matériaux et des UV | oui | **U4** (matériaux : peu cher ; UV : à router dehors) |
| Convergence du Plateau vers ce canevas | oui | **U5** |

L'Établi, lui, reste ce qu'il annonce : un endroit pour **regarder** un maillage,
en **séparer** des parties, en **corriger** l'assise, en **juger** le rig, et
l'**emmener** dans un moteur.
