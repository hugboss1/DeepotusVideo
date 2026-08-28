# Le Plateau — prévisualisation 3D, cadrage caméra et mouvements, avant tout tir payant

**Date :** 2026-08-29
**Statut :** design proposé — rien n'est codé, la demande était « réfléchis à »
**Demande (verbatim) :** « réfléchis à un visualisateur 3d avec cadrage camera et
toutes les fonctionalités qui s'y préterait pour préparer une scene avant tir 3d
réel (un émulateur d'environement 3d incorporant des versions simplifiés des
éléments 3d générer dans la scene) utilise le visualisateur existant dans
reforge3d comme grille de navigation mais fixe un cadre de camera pour permettre
de cadrer la scene et définir les mouvements de caméra. »

---

## 1. Ce que le Plateau sert à décider

Aujourd'hui, un plan se décide en prose : `shot.camera_move = "slow push-in"`,
`shot.shot_type = "medium"`. Personne ne voit le cadre avant de payer. La
génération vidéo découvre la composition en même temps que l'utilisateur.

Le Plateau inverse l'ordre : **on compose d'abord, gratuitement, en 3D**, et le
plan hérite de mesures au lieu d'intentions.

Trois décisions qu'il rend vérifiables plutôt que devinées :

1. **Le cadre.** Le sujet remplit-il vraiment un « gros plan » ? La question a
   une réponse chiffrée — la fraction de hauteur d'image qu'occupe sa boîte
   englobante — et cette fraction *détermine* `shot_type` au lieu d'être
   contredite par lui.
2. **Le mouvement.** « slow push-in » est une étiquette ; un déplacement de
   caméra de 6,2 m à 2,4 m en 4 s en est la mesure. Le Plateau produit la
   seconde et en **déduit** la première.
3. **La dépense.** Une scène se bloque avec des primitives (boîte, capsule,
   cylindre) **avant** qu'un seul maillage soit généré. Le Plateau est donc
   d'abord une porte de plus devant la dépense, dans la lignée directe de la
   phase D.

## 2. Le principe : proxys d'abord, maillages ensuite

Une instance de scène pointe vers l'une de trois choses, et c'est la même
scène qui traverse les trois états :

| État | Source du volume | Coût | Quand |
|---|---|---|:--:|
| **Proxy primitif** | `gltf_builder.build_mesh("cube"/"sphere"/"cylinder")`, mis à l'échelle des dimensions déclarées de l'entité | 0 $ | avant toute génération 3D |
| **Maillage allégé** | le GLB du job `assets3d`, décimé par `mesh_optimize` (preset `prop`, 2 500 tris) | 0 $ (gltfpack local) | dès qu'un maillage existe |
| **Maillage plein** | le GLB tel quel | 0 $ | contrôle final, si la machine suit |

C'est exactement ce que la demande appelle « versions simplifiées » — et le
dépôt a déjà les deux briques : `gltf_builder` sait fabriquer des primitives,
`mesh_optimize` sait décimer. Rien à installer.

**Conséquence produit :** on peut cadrer un chapitre entier, définir tous ses
mouvements de caméra et mesurer tous ses `shot_type` **pour 0 $**, puis ne
générer en 3D que les éléments que le cadre montre réellement. Un décor hors
champ ne se paie jamais.

## 3. Le visualiseur : celui de Cardforge, avec un cadre

La demande est explicite — reprendre le visualiseur existant. C'est
`<model-viewer>` 3.3.3, déjà embarqué (`/assets/model-viewer.min.js`), déjà
piloté par `frontend/cardforge/js/mod-forge3d.js` (`camera-controls`,
`auto-rotate`, capture par `toBlob()`).

Ce qu'il apporte gratuitement : orbite/pan/zoom à la souris, ombre au sol,
environnement neutre, et surtout `getCameraOrbit()` / `getCameraTarget()` /
`getFieldOfView()` — les trois valeurs dont un keyframe de caméra a besoin.

### 3.1 Le cadre n'est pas un rectangle dessiné par-dessus

Piège à éviter : superposer un rectangle 16:9 sur un viewport carré ne montre
pas ce qui sera rendu — le champ vertical ne correspond pas. **On met l'ÉLÉMENT
au ratio cible** (letterbox du conteneur), de sorte que ce qu'on voit est le
cadre. Les guides (tiers, croix centrale, zone-titre, ligne d'horizon) sont des
tracés CSS par-dessus, jamais le cadre lui-même.

### 3.2 Une seule limite structurelle, dite d'emblée

`<model-viewer>` affiche **un** glTF par élément. Une scène de plusieurs objets
doit donc être **composée en un seul GLB** côté serveur. Ce n'est pas un
contournement : le GLB de scène devient un artefact versionné comme les autres,
téléchargeable, et sa fiche `mesh_report` (sha256, faces, poids) existe déjà.

L'alternative — three.js et un second moteur de rendu dans l'app — coûterait un
visualiseur de plus à maintenir pour un gain que la composition serveur donne
déjà. La demande dit d'ailleurs de réutiliser l'existant.

## 4. Modèle de données

### 4.1 Table `scenes3d`

```
id (uuid), chapter_id (idx, nullable), shot_id (idx, nullable), nom,
aspect ("16:9"|"9:16"|"1:1"|"2.39:1"), focale_mm (float, défaut 35),
capteur_mm (float, défaut 14.2 — hauteur Super-35),
instances (JSON), camera (JSON), keyframes (JSON),
glb_file, glb_version, created_at, updated_at
```

Table neuve → `create_all` suffit, aucune migration (patron `VectorDoc`).

### 4.2 Une instance

```json
{
  "id": "inst_01",
  "nom": "Lina",
  "source": {"kind": "proxy", "forme": "capsule", "dims": [0.5, 1.7, 0.4]},
  "entity_id": "char_lina",
  "asset3d_job": null,
  "niveau": "proxy",
  "transform": {"pos": [0, 0, 0], "rot": [0, 25, 0], "scale": 1.0},
  "couleur": "#8a8f98",
  "role": "sujet"
}
```

`role` (`sujet` | `decor` | `repere`) porte du sens : c'est le **sujet** dont on
mesure la hauteur à l'écran pour en déduire le `shot_type`, et c'est lui que la
caméra vise par défaut.

### 4.3 Un keyframe de caméra

```json
{"t": 0.0, "orbit": [35, 78, 6.2], "target": [0, 0.9, 0],
 "fov": 32.1, "easing": "ease-in-out"}
```

`orbit` = [θ°, φ°, rayon m] dans la convention `<model-viewer>`. `t` est en
secondes, borné par `shot.duration_s` quand la scène est liée à un plan : le
mouvement prévisualisé dure exactement ce que durera le clip.

## 5. Les mesures — ce qui distingue le Plateau d'un jouet

Toutes calculées côté serveur (`scene_service`), en géométrie pure, donc
testables sans navigateur.

### 5.1 Focale ↔ champ de vision

```
fov_vertical = 2 · atan(capteur_mm / (2 · focale_mm))
```

Un réalisateur pense en millimètres, `<model-viewer>` en degrés. Le Plateau
affiche les deux et convertit. Un 24 mm et un 85 mm ne cadrent pas pareil à
distance égale — c'est précisément ce qu'on vient prévisualiser.

### 5.2 `shot_type` mesuré, pas déclaré

On projette les 8 coins de la boîte englobante du **sujet** avec la caméra
courante, on en tire `h` = fraction de la hauteur d'image occupée :

| `h` | `shot_type` déduit |
|---|---|
| < 0,20 | `establishing` |
| 0,20 – 0,45 | `wide` |
| 0,45 – 0,75 | `medium` |
| 0,75 – 0,95 | `close-up` |
| > 0,95 | `extreme close-up` |

Les seuils sont **configurables et affichés** — c'est une convention de
cadrage, pas une loi de la nature, et le dire vaut mieux que le cacher (même
doctrine que les seuils de `asset3d_qc`).

Le Plateau ne réécrit jamais `shot.shot_type` en silence : il montre l'écart
(« tu as écrit *close-up*, le cadre donne *medium* ») et propose l'alignement.

### 5.3 Le mouvement, déduit des deltas

Entre le premier et le dernier keyframe, on compare Δrayon, Δθ, Δφ, Δfov,
Δtarget, et on retombe sur le **vocabulaire déjà utilisé par le storyboard**
(`schemas.CameraMove`, 11 valeurs) — surtout pas un vocabulaire parallèle :

| Delta dominant mesuré | `camera_move` |
|---|---|
| rayon ↓ | `slow push-in` |
| rayon ↑ | `slow pull-out` |
| \|Δθ\| ≥ 300° | `360-degree orbit` |
| target se déplace, rayon ~ constant | `tracking shot` |
| φ ↓ (caméra descend) | `crane shot descending` |
| rayon ↓ **et** fov ↑ (simultanés) | `dolly zoom (vertigo effect)` |
| \|Δθ\| grand sur < 0,5 s | `whip pan transition` |
| tout ~ constant | `static, locked-off` |

**Trois valeurs restent hors de portée, et il faut le dire** :
`handheld with subtle shake` (une texture de mouvement, pas une trajectoire —
elle s'ajoute par-dessus), `rack focus reveal` (exige une profondeur de champ
que `<model-viewer>` ne simule pas), `low angle dramatic` (un ATTRIBUT de
cadre, déduit de φ > 95°, pas un mouvement). Le Plateau les propose à la main
au lieu de prétendre les mesurer.

### 5.4 Le prompt de mouvement, écrit à partir des chiffres

Le §7.2 de la spec Magnific veut un prompt qui ne décrive **que** le mouvement.
Le Plateau le compose depuis les mesures — « slow dolly in from 6.2 m to 2.4 m,
subject held on the left third, eye-level, 35 mm » — et le dépose dans
`shot.motion_prompt`, où le lot 3 du plan d'ensemble l'attend déjà.

## 6. Le débouché : première et dernière image

C'est le gain le plus concret, et il tombe tout cuit.

`<model-viewer>.toBlob()` capture le viewport — la fonction « figer l'aperçu »
de Cardforge s'en sert déjà. Au premier et au dernier keyframe, cela donne
**deux images cadrées exactement** comme le clip doit commencer et finir.

Or le registre vidéo porte déjà `end_image: True` sur Seedance 1 Pro, 2, 2 Fast,
2.5 et les deux Kling v3. Ces modèles prennent une image de début **et** une de
fin. Le Plateau les fabrique.

```
scène composée → cadre 16:9 → keyframes → toBlob(t=0) + toBlob(t=fin)
   → Library (provenance « plateau »)
   → shot.keyframe_image + shot.keyframe_end
   → job vidéo image_filename + image_filename_end + motion_prompt
```

Prévisualiser un mouvement en 3D et livrer au modèle les deux bornes exactes de
ce mouvement, c'est un contrôle qu'aucun prompt textuel ne donne.

## 7. Fonctionnalités du Plateau

**Cadre**
aspects 16:9 / 9:16 / 1:1 / 2.39:1 · focale en mm (14–200) ↔ fov · guides tiers,
croix centrale, zone-titre, ligne d'horizon · hauteur d'œil · lecture continue
distance sujet / hauteur à l'écran / `shot_type` déduit.

**Scène**
ajouter une instance depuis la bible (entité → son maillage, ou une primitive
si elle n'en a pas encore), depuis un job `assets3d`, ou une primitive nue ·
position / rotation / échelle en champs numériques (précis et rejouables ; pas
de gizmo — `<model-viewer>` n'en a pas, et un chiffre se commente) · grille au
sol graduée en mètres · duplication · rôle sujet/décor/repère.

**Mouvement**
poser un keyframe = capturer l'état caméra courant · timeline calée sur
`shot.duration_s` · easing par segment · lecture en boucle · presets
(travelling avant, orbite 90°, grue descendante, plan fixe) · dérivation du
`camera_move` mesuré · avertissement quand le sujet sort du cadre pendant le
mouvement.

**Sorties**
GLB de scène (versionné, avec sa fiche `mesh_report`) · première et dernière
image vers la Library · `camera_move` + `shot_type` + `motion_prompt` vers le
plan · contact-sheet des keyframes en une planche PIL (patron `board_service`).

## 8. Où ça vit

**`/plateau`** — page servie par FastAPI, vanilla, comme `/atelier` et
`/cardforge`. **Aucune chirurgie du bundle minifié** : c'est la décision qui a
fait ses preuves sur l'Atelier, et une timeline de keyframes dans du React
minifié serait exactement le genre de chantier que le dépôt a appris à éviter.

Points de contact : un bouton « 🎥 Plateau » sur la carte de plan du storyboard
(`/atelier`, onglet Storyboard) et sur une fiche d'entité.

## 9. API

| Route | Rôle |
|---|---|
| `GET/POST /api/scenes3d` · `GET/PUT/DELETE /api/scenes3d/{id}` | CRUD |
| `POST /api/scenes3d/{id}/compose` | compose le GLB (proxys + maillages décimés) → `glb_file`, `glb_version` |
| `GET /api/scenes3d/{id}/scene.glb` | sert le GLB au visualiseur |
| `POST /api/scenes3d/{id}/mesure` | `{camera}` → `{h, shot_type, distance_m, focale_mm, fov}` |
| `POST /api/scenes3d/{id}/mouvement` | keyframes → `{camera_move, motion_prompt, avertissements}` |
| `POST /api/scenes3d/{id}/capture` | `{t, image_b64}` → dépose dans la Library (provenance `plateau`) |
| `POST /api/scenes3d/{id}/vers-plan` | applique au `shot` : `shot_type`, `camera_move`, `motion_prompt`, images de début/fin |

Tout est **local et gratuit**. La seule route qui peut coûter est celle qui
n'existe pas ici : la génération vidéo, qui reste derrière sa propre porte.

## 10. Phases

- **P1 — Scène et composition (0 $).** Table `scenes3d`, `scene_service` :
  primitives via `gltf_builder`, décimation via `mesh_optimize`, composeur GLB
  (N maillages, N nœuds transformés, un seul buffer). Banc à l'octet, patron
  `test_print3d.py` : un GLB composé se relit par `print3d.lire_glb_triangles`
  et ses boîtes tombent où les transformations le disent.
- **P2 — Cadre (0 $).** Page `/plateau`, viewer au ratio cible, guides,
  mesures `shot_type` / focale / distance. Banc sur la géométrie de projection
  (une caméra à 6 m d'un sujet de 1,7 m en 35 mm donne telle fraction — vérifié
  par le calcul, pas par une capture).
- **P3 — Mouvement (0 $).** Keyframes, lecture, dérivation du `camera_move`,
  `motion_prompt`. Banc : chaque ligne de la table §5.3 a son cas.
- **P4 — Pont vers le plan.** Captures début/fin vers la Library, application
  au `shot`. **Dépend du lot 2 du plan d'ensemble** (`shot.keyframe_image`) —
  P1 à P3 n'en dépendent pas et se livrent seuls.

## 11. Risques mesurés

| Risque | Mitigation |
|---|---|
| Une scène de 10 maillages pleins met le viewer à genoux | le niveau `proxy` est le DÉFAUT ; la décimation `prop` (2 500 tris) est le second ; le maillage plein est un choix explicite, avec le total de triangles affiché avant de composer |
| La capture `toBlob()` ne fait pas la même image que le modèle vidéo | elle n'y prétend pas : c'est un **cadrage**, pas un rendu. Le clip garde son propre style ; ce que la capture verrouille, c'est la composition et le point de départ/arrivée |
| Le `shot_type` déduit contredit celui écrit par l'agent | rien n'est réécrit en silence — l'écart est montré, l'alignement est un clic |
| Composer un GLB à la main est un nid à bugs d'octets | c'est pourquoi le banc lit le résultat avec `print3d.lire_glb_triangles`, le lecteur déjà éprouvé du dépôt : si la composition ment, le lecteur le voit |
| `<model-viewer>` absent (installation abîmée) | même repli que Cardforge : le message dit ce qui manque, et le GLB de scène reste téléchargeable |

## 12. Ce que ce design ne fait PAS

Dit franchement, pour que personne ne l'attende :

- **pas d'éclairage de scène** — l'environnement du viewer est neutre. La
  lumière reste décrite par `scene.lighting` et le prompt ; la prévisualiser
  demanderait un vrai moteur de rendu ;
- **pas de profondeur de champ**, donc pas de `rack focus` mesurable ;
- **pas d'animation de personnage** — les instances sont des volumes figés. Le
  Plateau cadre et déplace la caméra, il ne joue pas la scène ;
- **pas de gizmos de manipulation** — `<model-viewer>` n'en offre pas, et les
  champs numériques sont plus précis pour un cadre qu'on veut rejouable ;
- **pas de remplacement du storyboard** — le Plateau ALIMENTE le plan
  (`shot_type`, `camera_move`, `motion_prompt`, images de bornes), il ne le
  double pas.
