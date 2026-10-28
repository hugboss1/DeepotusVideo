# Scenario Explorations → DeepotusVideo : tableau d'écart (27/10/2026)

Relevé source : `2026-10-27-scenario-explorations-inventaire.md`.
État « chez nous » lu sur `origin/main` (PR #459). Statut proposé :
**À FAIRE** (écart réel, prioritaire), **COMPLÉTER** (existe en partie),
**GARDER** (déjà au niveau), **PLUS TARD / NON**.

## Positionnement en une phrase

Scenario vend une **plateforme cloud + MCP + skills** que l'agent de l'utilisateur
pilote ; DeepotusVideo est une **application locale intégrée** (labs, Bibliothèque,
Montage, Atelier, compagnon) où l'utilisateur pilote et où l'agent interne ne dépense
jamais sans devis. Nos forces : tout local, provenance et Bibliothèque, Établi,
exports moteurs (Godot/Unity/Unreal/Blender), Montage complet, compagnon mobile,
plafonds de dépense. Leurs forces : **la boucle Blender ↔ génération**, la **revue
chiffrée automatique**, la **recette publiée comme skill**, et le pilotage par MCP.

## A. Chapitres : mise en scène pré-render / pré-animation (lien MCP Blender)

| # | Chez eux | Aujourd'hui chez nous | Décision |
|---|---|---|---|
| A1 | Plugin Blender + MCP : l'agent pose proxys, caméras, lumières dans Blender 5.x | Plateau 3D three.js (`scene3d*.py`, `/api/scenes3d`) ; Blender seulement lancé pour importer un GLB (`mesh_export.ouvrir`) ; **aucun MCP** | **À FAIRE — pont « Scène Blender »** : `mcp-for-blender` (ex-blender-mcp, MIT, port 9876) piloté par le backend comme **client MCP** (SDK `mcp`, stdio, version épinglée, `DISABLE_TELEMETRY=true`, `BLENDER_MCP_SAFE_MODE=1`). Liste blanche : `get_scene_info`, `look`, `search_assets`, `import_asset` ; `generate_3d` derrière devis + `confirme_cout` ; `execute_blender_code` UNIQUEMENT avec gabarits générés par le backend (caméra + focale, 3 points, empty de blocking, clés). Étape 0 sans code : config Claude Code de l'utilisateur. |
| A2 | Aller-retour scène : plan du storyboard → layout Blender → capture caméra | Plateau ↔ plan (`vers-plan`, captures début/fin) | **À FAIRE** : export Plateau → gabarit Blender (mêmes caméras, focales, keyframes, GLB de la bible) et retour `.blend` + JSON caméras/objets vers le plan. Plateau reste l'éditeur léger ; Blender = étage « pro ». |
| A3 | Previs **colorée et nommée** ; le prompt nomme chaque forme | Captures Plateau non codées | **À FAIRE** : palette de proxys par entité de bible / matière, légende injectée dans le prompt de plan. Vaut pour Plateau ET Blender. |
| A4 | 4 versions par cut : clay Workbench / look EEVEE / still / film | Croquis FLUX → image de prod → vidéo | **COMPLÉTER** : rendu headless existant (`blender -b`) pour passes clay, profondeur, normales, masques ; vignettes dans la fiche du plan. |
| A5 | Style frames peintes sur les stills de previs, puis **video-to-video** Seedance (`@video1` clay + `@image1` still) | Veo 3.1 first-last frame depuis la borne Plateau ; `video_refs.py` (ref-to-video, elements Kling) **jamais appelé** | **À FAIRE** : brancher `video_refs.py` ; ajouter le mode « previs → plan » v2v (Seedance 2.5 via fal) avec clip de previs + style frames. |
| A6 | Durée mini des modèles : étirer/ré-accélérer, noir puis couper ; re-timing mesuré | — | **À FAIRE** : conform automatique avant envoi + recalage après (ffmpeg), dérive en images affichée. |
| A7 | Contrôles chiffrés : dérive ≤ 1 image, depth check, fidélité 9/10, Quality Gate | `identity_drift.py` (couleur, silhouette) | **COMPLÉTER** : « revue du plan » = dérive temporelle (corrélation de bords), profondeur previs vs rendu, note LLM « directeur artistique » par critère, liste de défauts ; ne jamais présenter la note comme une garantie. |
| A8 | Couverture : une prise recoupée en 13 angles ; 40 cuts avec couverture | Un plan = une caméra | **COMPLÉTER** : caméras de couverture par plan dans Plateau/Blender (plan large + contre-champ + gros plan), générées depuis la même scène. |
| A9 | Feuilles de référence par élément récurrent, données aux stills | Bible (vues, `model3d`), espaces de marque | **GARDER**, ajouter « élément récurrent » (accessoire canonique) à la bible. |
| A10 | Son calé sur la caméra (niveau = distance), musique par sections | Atelier audio, Montage, ducking | **PLUS TARD** : piste d'automation de volume dérivée de la caméra Blender/Plateau. |
| A11 | Grease Pencil → image finale | — | **PLUS TARD** : même pont (A1) + capture de la caméra ; option « traits par-dessus » dans le comparateur. |

## B. Game assets

| # | Chez eux | Aujourd'hui chez nous | Décision |
|---|---|---|---|
| B1 | Pixelate à grille exacte, Pixel Lock (porte d'approbation), Pose Keyframe | `pixel_ops.py`, Spritelab (découpe, planche, post) | **COMPLÉTER** : grille imposée par l'outil (jamais par le modèle) + étape « sprite approuvé » verrouillant palette et grille. |
| B2 | Animate Loop : 2 poses → Seedance 1re/dernière image → images → re-pixelisation → feuille + GIF | Champ IA `spritelab-anim` (vidéo → cadres) | **COMPLÉTER** : préréglage « boucle » (même pose aux deux bouts, garder 1 image sur 2–3, GIF). |
| B3 | 8 directions (5 dessinées + 3 miroirs) ; règle « ne jamais miroiter » si objet asymétrique | 4 directions depuis la planche de la bible | **À FAIRE** : 8 directions, miroir optionnel avec avertissement « objet tenu ». |
| B4 | VFX pixel en recettes JSON (palettes PICO-8, Endesga…) | Particules (port de `particle_service`), VFX vidéo | **COMPLÉTER** : export/import de préréglages VFX en JSON + palettes rétro dans Spritelab. |
| B5 | Parallaxe : une peinture large découpée en 5 calques (Layerize) | Tilelab, détourage | **À FAIRE** : « décor en calques » (Seedream Layerize via fal ou SAM) + export Godot ParallaxBackground. |
| B6 | Segmentation de maillage en pièces mobiles (Tripo Segmentation) | Établi (couper, booléen) manuel | **À FAIRE** : segmentation IA dans 3D Studio → pièces nommées, origine sur l'axe. |
| B7 | Budgets de triangles par rôle ; 3 densités natives 50k/8k/2k | LOD en chaîne mesuré (`mesh_lod.py`) | **COMPLÉTER** : préréglages de budget par rôle (prop, héros, décor web) + génération multi-densité. |
| B8 | Rig + Video/Text to Motion (Uthana, Cartwheel), retimage, hitboxes sur os | Rig Meshy + anims ; hitboxes 2D ; Établi U1 animation « à construire » | **À FAIRE** : vidéo → mouvement sur le rig (fal si dispo) ; hitboxes sur os à l'export Godot. |
| B9 | Banc comparatif multi-modèles (12 modèles image→3D, vues Clay/Wireframe, tableau) | 5 moteurs fal, QC, rapport | **COMPLÉTER** : « comparer les moteurs » sur une image, même éclairage, tableau tris/arêtes ouvertes/temps/coût. |
| B10 | Skybox 360 + HDRI EXR | Matières (HDRI de rendu) | **À VÉRIFIER** puis COMPLÉTER : génération de skybox 360 orientable (soleil où l'on veut). |
| B11 | Roblox Studio MCP + skills Roblox | Aucune trace | **PLUS TARD** (après Godot/Unity/Unreal). |
| B12 | Exports moteurs | Godot `.tres`, Phaser, Aseprite, Paper2D, Tiled, LDtk, GLB Unity/Unreal/Godot/Blender avec « Déposer » | **GARDER** — avance nette sur eux (ils montrent des démos, pas d'exports outillés). |

## C. Vidéo, personnages, voix

| # | Chez eux | Chez nous | Décision |
|---|---|---|---|
| C1 | Édition chaînée « change only X » avec `@video1 @image1`, brouillon 480p puis final | `vfx_ia.py` (12 gestes), Recast (brouillon 480p) | **GARDER**, ajouter la chaîne d'étapes (une sortie = entrée de la suivante) avec historique. |
| C2 | Localisation doublée + lèvres, 8 langues, contre-vérif par transcription | Traduction de sous-titres, Kling lipsync, HeyGen, ElevenLabs | **À FAIRE (chapitres)** : doublage par entité de bible (voix clonée) + lipsync + vérif Scribe/transcription. |
| C3 | Acteur unique au téléphone → plusieurs personnages | Recast (Wan Animate, Kling motion control) | **COMPLÉTER via le compagnon** : capter la prise au téléphone (L4.5 Capter) → Recast sur PC. |
| C4 | Comparateur wipe universel (O / C / pas à pas) | Comparaisons éparses | **À FAIRE** : composant commun de comparaison (avant/après, previs/rendu, moteurs), raccourcis O/C. |

## D. Transverse : ce qui fait leur valeur perçue

| # | Chez eux | Chez nous | Décision |
|---|---|---|---|
| D1 | Scenario MCP : l'agent de l'utilisateur pilote toute la plateforme | API agent `/api/agent/campagnes` (10 outils, pas de dépense) ; pas de MCP | **À FAIRE (stratégique)** : exposer DeepotusVideo comme **serveur MCP local** (lecture Bibliothèque/bible/plans, devis, lancement après confirmation), pour que Claude Code pilote l'app comme Scenario. |
| D2 | Recette publiée en skill ZIP + PDF making-of + prompts | Recette qui suit le rendu (t283, `/api/jobs/{id}/recette`), dépenses réel/estimé | **COMPLÉTER** : « Exporter la recette » d'un plan/asset en SKILL.md + PDF de fabrication (prompts, modèles, coûts réels, ratés). |
| D3 | Facture CU visible partout | Devis, plafonds, dépenses | **GARDER** ; afficher le coût cumulé par plan/chapitre dans l'Atelier. |
| D4 | Agent autonome « un prompt → film » | Agent interne sans dépense | **NON** en autonome ; OUI en « proposer un plan de génération chiffré » validé d'un clic. |

## Ordre recommandé

1. **A1 étape 0** (config Claude Code + Blender ouvert) → valider la boucle à la main.
2. **A5 + A6** (v2v previs → plan, conform) : le gain visible le plus fort pour les chapitres.
3. **A1 étapes 1–2 + A2 + A3** (pont backend, gabarits, previs codée).
4. **A7 + C4** (revue chiffrée + comparateur).
5. **B3, B1-B2, B6, B8** (game assets).
6. **D1** (DeepotusVideo comme serveur MCP), **D2**, puis le reste.

## Pièges à garder en tête

- Port 9876 partagé par l'add-on officiel (Blender Lab MCP, Blender 5.1+) et
  l'add-on communautaire : un seul actif, un seul client (pas Claude Code + backend).
- `execute_blender_code` = code arbitraire (CVE-2026-10688) : jamais de texte libre du LLM.
- Socket sans authentification : localhost seulement, jamais exposé au Wi-Fi du compagnon.
- Licences par asset (Sketchfab, Poly Pizza ≠ CC0) → provenance Bibliothèque.
- Blender en mode graphique pour le MCP ≠ `blender -b` headless du rendu : versions à aligner.
