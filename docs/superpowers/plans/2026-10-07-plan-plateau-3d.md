# Plan d'exécution — le Plateau 3D (t127)

**Spec :** `docs/superpowers/specs/2026-08-29-plateau-previsualisation-3d-design.md`
**Date :** 07/10/2026
**Décisions de l'utilisateur (07/10) :**
- visualiseur = le **canevas three.js partagé** `frontend/lib3d/viewer.js` (celui de l'Établi, dont l'en-tête prévoit la
  convergence du Plateau), et non `<model-viewer>` comme l'écrit la spec §3. Conséquence : la scène se monte objet par
  objet dans le navigateur ; le **GLB de scène composé côté serveur reste une SORTIE** (P1 : artefact versionné et
  téléchargeable, `mesh_report`), il n'est plus le moyen d'affichage ;
- portée = **P1 à P4 en entier**. P4 dépendait du « lot 2 » (`shot.keyframe_image`), jamais construit : le `Shot` gagne
  les colonnes qu'il faut (migration légère).

## Écarts assumés par rapport à la spec (datés ici, repris dans la spec)

| Spec | Ici | Pourquoi |
|---|---|---|
| §3 `<model-viewer>`, un GLB par élément | canevas `lib3d` (three r185), une scène d'objets | décision du 07/10 ; la focale devient exacte (caméra perspective three), le cadre est l'élément lui-même |
| §3.1 orbite `<model-viewer>` [θ°, φ°, r] | même convention gardée pour les keyframes (θ autour de Y depuis +Z, φ depuis +Y) | le vocabulaire de la spec et les bancs restent valables |
| §6 `toBlob()` de `<model-viewer>` | `canvas.toBlob()` du rendu three (preserveDrawingBuffer ou rendu forcé avant capture) | même rôle : un cadrage, pas un rendu |

## Tâches

### PR A — serveur (`chantier/plateau-previz-3d`)

- **T1 — Géométrie pure** `backend/app/services/scene3d.py` (aucune E/S) :
  `fov_de_focale(focale_mm, capteur_mm)`, `focale_de_fov`, `position_camera(orbit, target)`,
  `projeter(points, camera, aspect)`, `mesure(scene, camera)` → `{h, shot_type, distance_m, focale_mm, fov, dans_cadre}`,
  seuils §5.2 configurables, `interpoler(keyframes, t)` avec easing, `mouvement(keyframes, scene, duree)` →
  `{camera_move, motion_prompt, avertissements, deltas}` (table §5.3 : une ligne = un cas de banc ; les trois valeurs
  hors de portée ne sont jamais rendues par la mesure, `low angle dramatic` est un ATTRIBUT signalé).
- **T2 — Composeur GLB** : proxys (boîte, sphère, cylindre, capsule) mis à l'échelle des `dims`, maillages de jobs
  `assets3d` décimés (`mesh_optimize`, preset prop) ; N nœuds transformés, un seul buffer. Banc : relu par
  `print3d.lire_glb_triangles`, les boîtes tombent où les transformations le disent.
- **T3 — Table `scenes3d` + routes** (CRUD, `compose`, `scene.glb`, `mesure`, `mouvement`, `capture` → Library
  provenance `plateau`, `vers-plan`). Gratuites et locales ; validation des entrées (400 nommés).
- **T4 — `Shot`** : colonnes `motion_prompt`, `image_end` (migration légère) ; `vers-plan` écrit `shot_type`,
  `camera_move`, `motion_prompt`, `image` (début) et `image_end` (fin) — rien en silence : la réponse dit l'écart avant /
  après, l'écran le montre et demande.

### PR B — écran (empilée sur A)

- **T5 — Page `/plateau`** (vanilla, comme `/etabli`) : canevas au ratio cible (letterbox), guides CSS (tiers, croix,
  zone-titre, horizon), focale mm ↔ fov, lecture continue (distance, h, `shot_type` mesuré via `/mesure`).
- **T6 — Scène** : instances (primitive, job `assets3d`, entité de la bible), champs numériques pos/rot/échelle,
  rôle, duplication, grille au sol graduée, total de triangles affiché avant composition.
- **T7 — Mouvement** : keyframe = état caméra courant, timeline calée sur `shot.duration_s`, easing, lecture en
  boucle, presets, `camera_move` dérivé + avertissement « sujet hors cadre ».
- **T8 — Sorties et pont** : composer/télécharger le GLB, captures début/fin → Library, « Appliquer au plan » (écart
  montré), bouton « 🎥 Plateau » sur la carte de plan du storyboard (`/atelier`).

## Bancs

`test_scene3d.py` (géométrie pure : focale, projection vérifiée par le calcul, chaque ligne §5.3), `test_scene3d_glb.py`
(composition relue à l'octet), `test_scene3d_routes.py` (routes, data-dir temporaire, Library, `vers-plan`),
`test_plateau_ecran.py` (page : structure + modules sous node quand c'est pur). Mutations sur chaque tâche.
