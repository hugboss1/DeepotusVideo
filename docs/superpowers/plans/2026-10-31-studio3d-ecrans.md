# 3D Studio à écrans + onglet 3D « Créer » + Décor (t387-t404)

Date : 31/10/2026. Demande de l'utilisateur, avec dix captures de
sorceress.games (3D Studio : Create, Texture, Rig, Refine, Animate ; TreeGen).
Relevé : `docs/superpowers/specs/2026-10-31-sorceress-3d-studio-inventaire.md`.
Conception et tableau d'écart : `docs/superpowers/specs/2026-10-31-studio3d-ecrans-design.md`
(décisions D1-D7, **à valider**).

## Méthode

C'est la méthode habituelle :

- **une session neuve par tâche**, sur une branche `chantier/studio3d-tNNN` partie de `origin/main` ;
- TDD et mutations ;
- preuve sur le backend 8799, en FR **et** en EN ;
- PR, puis installation vérifiée par `git hash-object` ;
- fiches du catalogue de l'assistant (skill `connaissance-agent`).

**Fichiers générés.** Ne jamais retoucher à la main :

- `studio3d.js`, `vues.js`, `fal.js`, `local.js`, `banc.js` et `lib3d/*` : générés par L9 ;
- `etabli.js` : généré par L8.

Les écrans neufs sont des modules à part dans `frontend/studio3d/ecrans/`. Le graphe ne reçoit que des crochets, par une saisie `scripts/i18n_l9/tNNN.py`.

**Bundle (onglet 3D de Game Assets).** Il se modifie par des maillons de queue. Le premier part de **dzapparence** : son inverse appelle `avant_dzapparence` en tête.

**Charte.**

- `dz-charte.css` (`--radius:0`) ;
- `dz-curseur.css` ;
- icônes Deepotus Glyph ;
- couleur `--cat-3dstudio` ;
- aucun rayon littéral (`charte_aplatir_rayons.py`).

**Dépenses.** Toute route payante suit la chaîne : clé 503 → bornes 400 → `confirme_cout` 409 → plafond « moteurs3d ».

**Calculs.** Ils restent purs et testables : poids, articulations et corrections en Python pur, avec un banc sur `backend/tests/_squelette_synthetique.py`. Les opérations côté navigateur sont dans des modules `*_calc.js` testés sous node.

## Lot A — Socle et Créer (P2)

**t387 Relevé des API 3D (T0).** Il porte sur la disponibilité réelle, le schéma et le prix de :

- Tripo P2, Tripo Smart Mesh, Tripo v3.1 ;
- Hunyuan 3D 3.1, TRELLIS 2, Rodin 2.0 ;
- Meshy 7 et Meshy 6, par la clé Meshy ;
- le rig Tripo ;
- `fal-ai/hunyuan-motion`, avec la forme du `dict` et le squelette ;
- Kimodo et GVHMR, à chercher sur fal ;
- le catalogue complet des animations Meshy, avec ses ids et catégories ;
- les modèles d'image de la texture : Nano Banana 2 / 2.1, GPT Image 2, Seedream 5 Lite.

La tâche met aussi à jour `balayage-fournisseurs-fal` et vérifie la licence d'ez-tree (code et textures).

Sortie : `docs/superpowers/specs/2026-11-xx-api-3d-releve.md` et la liste des réglages par moteur. Aucune dépense, sauf un tir de preuve par moteur sur devis accepté.

**t388 Coque du 3D Studio à écrans.** Contenu :

- `frontend/studio3d/index.html` charge `ecrans/coque.js` ;
- barre d'onglets à deux groupes : `Ouvrir · Importer` | `Préparer · Texture · Rig · Affiner · Animer · Exporter` | `Décor · Graphe` ;
- le second groupe est grisé sans modèle ouvert ;
- bandeau « Ouvert » : vignette, nom, badge RIGGÉ, nombre d'os et de sommets, version, point « non enregistré » ;
- état partagé `ouvert` ;
- liens profonds `?job=&ecran=` ;
- barre d'affichage commune : Fil, Plein, Texture, Texture + fil, Poids, centrage et rotation ;
- le graphe existant devient l'écran Graphe, chaque nœud renvoyant à son écran (D2).

Côté serveur : versions d'un job, `GET /api/studio3d/ouvert/{job}` et `POST …/version`. Bancs : écran (node) et routes.

**t389 Onglet 3D = Créer (D1).** Contenu :

- liste des moteurs à cases, un job par moteur coché, devis total ;
- accordéon de réglages par moteur, décrit par `ENGINES[...].reglages` et validé par le serveur ;
- modes Image, Texte et Multi-images ;
- quantité de 1 à 4 ;
- encart A-pose avec sa planche ;
- galerie : Tous, Favoris, Riggés, Non riggés, Personnage, Décor, plus le curseur de grille, la recherche et le volet avant/après ;
- boutons « Ouvrir dans 3D Studio ▸ Texture · Rig · Animer · Décor ».

La rangée Optimiser / LOD / Textures est retirée (elle passe dans t392 et t400). Maillon de queue après dzapparence.

**t390 Nouveaux moteurs et réglages complets.** Selon t387 : Meshy 7/6 dans l'onglet 3D (le nœud `preview` du graphe s'y raccorde), puis les versions Tripo, Hunyuan, Trellis et Rodin trouvées, avec tous leurs réglages relevés. Pour chacune : prix dans `pricing.py`, et pose (t376) étendue.

## Lot B — Ouvrir, Importer, Préparer (P2)

**t391 Écrans Ouvrir et Importer.**

- **Ouvrir** : galerie des modèles (jobs de l'onglet 3D, imports, productions de l'Établi), avec les mêmes filtres que t389.
- **Importer** : GLB/glTF, OBJ, BVH ; FBX par `blender.exe -b` (conversion en GLB) ; Mixamo (FBX riggé) ; VRM.
- Mannequin de référence humanoïde fourni.
- Daz G8 noté pour plus tard.

**t392 Écran Préparer.**

- Fiche du modèle : sommets, triangles, maillages, matériaux.
- Vue Original / Les deux / Optimisé côte à côte.
- Préréglages Micro prop 500 → Max detail 200 k, curseur de triangles, Ré-optimiser : `DzOptimize` et gltfpack réutilisés.
- LOD (`mesh_lod`).
- Réparer et décimer : services de l'Établi.
- « Annuler le rig et revenir à l'original ».

## Lot C — Texture (P2)

**t393 Texture 1/2 : retexture IA et capture.**

- Retexture Meshy (`/assets/3d/{job}/texturer`, prompt, référence de style).
- Capture du modèle dans le viewport : rosace de 10 vues, orbite par pas de 15, 30, 45 ou 90°, éclairages Sans lumière / Plat / Doux / 3 points / Vif.
- « Bras en T pour la capture ».
- Génération d'une image de référence par nos modèles fal : choix du modèle, résolution, ratio, prompt par défaut chargeable.
- Rail des références sous le viewport.

**t394 Texture 2/2 : projection multi-vues et pinceaux.**

- Texture auto en 4 / 6 / 8 / 10 / 12 / 16 / 18 vues, avec un devis par vue.
- Capture, puis image IA par vue en parallèle, puis projection sur l'atlas UV pondérée par l'angle, puis fusion.
- « Depuis le maillage ombré ».
- Pinceaux : gomme, estomper, combler, tout combler, débruiter (IA, sur devis).
- Atlas UV à plat (peint / GLB d'origine), fil de fer.
- Annuler / rétablir.

Calculs dans `ecrans/texture_calc.js`, testés sous node.

## Lot D — Rig et Affiner (P2)

**t395 Écran Rig (D3).**

- Auto-rig IA : Meshy `/v1/rigging` (reprise du nœud `rig` et de `fal.js`), plus Tripo si t387 le trouve.
- Rig semi-automatique local :
  - gabarit SMPL de 22 os affiché à côté du modèle (décalage réglable) ;
  - articulations à placer puis ajuster au gizmo, avec miroir G/D, enfants entraînés, Maj+clic et Échap ;
  - os de poitrine en option ;
  - « Recalculer les poids » : service `rig_local.py`, chaleur d'os ou distance, Python pur.
- Liste des os et fiche de l'os.
- Résultat écrit en version (GLB riggé).

**t396 Écran Affiner 1/2 : peinture des poids.**

- Outils : Choisir l'os (1), Peindre (2), Lasso (3), Pose (P, poignées IK).
- Opérations : Fixer R, Ajouter A, Retirer S, Lisser D, Flouter F.
- Réglages : taille, force, atténuation (linéaire / douce / constante), miroir (M), isoler (5), polys sans poids, clic droit pour assigner.
- Raccourcis Sorceress repris : `[ ]`, Ctrl/Maj + molette.
- Annuler / rétablir, enregistrement en version.

Opérations pures dans `ecrans/poids_calc.js`.

**t397 Affiner 2/2 : corrections automatiques.**

1. Orphelins : îlots de poids.
2. Confinement des membres, avec sa force, et reconstruction de l'épaule.
3. Coutures : collier de N anneaux, « seulement les déformées ».
4. Guérison dynamique sur un clip.

Plus le « correctif en un clic » (batterie de poses d'amplitude) et le test de pose avec les clips d'Animer. Service `poids_corrections.py` en Python pur.

## Lot E — Animer et Exporter (P2)

**t398 Animer 1/2 : bibliothèque.**

- Catalogue Meshy parcourable (relevé t387) : recherche, catégories, favoris, collections, lecture sur le modèle ouvert, application par `/v1/animations`.
- Déménagent ici, depuis l'Établi, `mouvement.js` (reciblage BVH/GLB, retimage, boucle, sur place) et la vidéo → mouvement Uthana.
- Pose de liaison.

**t399 Animer 2/2 : texte → mouvement (D5).**

- Meshy Text to Motion (API directe, « swift » en BVH, « prime » en FBX), lu par `mouvement_rig` : la licence de
  HY-Motion exclut l'UE (relevé t387) ; HY-Motion par fal seulement après avis de l'utilisateur.
- La sortie `dict` est reciblée par `mouvement_rig`.
- Kimodo (poses de début et de fin) et GVHMR si disponibles.
- Plusieurs modèles cochables, devis, plafond.
- Mode conduite : aperçu ZQSD/WASD, sans physique.

**t400 Écran Exporter.**

- GLB : maillage seul, pose, animation.
- FBX par Blender.
- Godot `.tscn` (avec hitboxes du mouvement).
- Unreal / Unity (`mesh_export.CIBLES`), conventions de textures (`DzTex`).
- Paquet three.js : GLB, clip, manifeste, runtime minimal, `AGENT_INSTRUCTIONS.md`.
- Impression 3D.
- Bibliothèque, avec « Envoyer vers » étendu : 3D Studio (écran au choix), Décor, Plateau 3D, Impression.

## Lot F — Décor (P2)

**t401 Décor 1/2 : végétation procédurale (D6).**

- ez-tree vendorisé dans `frontend/lib3d/eztree/`, avec sa licence et ses textures.
- Espèces :
  - arbres : chêne, frêne, tremble, bouleau, érable, cerisier, saule, pin, épicéa, sapin, palmier, cocotier, arbre nu, bonsaï, treille ;
  - arbustes et couvre-sol : 8 espèces.
- Taille et échelle en mètres, niveaux de branches.
- Feuillage réel ou cartes, 12 formes de feuille, saisons, densité, taille, retombée, rameaux.
- Écorce et teintes, graine, « nouvelle variante ».
- Vent : force, vitesse, direction, frémissement.
- Fiche : hauteur, envergure, triangles, feuilles.
- Export : GLB, recette `.decor.json`, paquet avec runtime de vent ; import de recette ; envoi en Bibliothèque.

**t402 Décor 2/2 : accessoire généré.**

- Un élément de l'onglet 3D s'ouvre dans Décor › Accessoire.
- Budget de triangles par rôle (`mesh_lod.ROLES`), pivot au sol, échelle réelle.
- Variantes (teinte, échelle, graine).
- Masque de vent par hauteur, pour une plante générée.
- LOD et cartes.
- Envoi au Plateau 3D.

## Lot G — Établi intégré et clôture (P2)

**t403 Établi dans le 3D Studio.**

- L'Établi devient l'écran « Établi » de la coque. Il n'y a plus de `location.href` ni de `#goEtabli`.
- Son onglet Rig en lecture renvoie à Rig et Affiner.
- Ses outils de maillage sont cités depuis Préparer.
- Changements par la saisie L8.

**t404 Clôture.**

- FR/EN de tous les écrans.
- Catalogue de l'assistant : fiches de chaque écran.
- Guide : chapitre « Créer et préparer un personnage 3D », « Décor ».
- Installation vérifiée.
- Captures avant/après.

## Ordre conseillé

1. t387, puis t388 : le socle d'abord.
2. t389 et t390, qui suivent t387.
3. t391 et t392.
4. t393, t395 et t398 : indépendants, ils peuvent courir en parallèle, chacun dans son module d'écran.
5. t396 puis t397 ; t394 ; t399 ; t400.
6. t401, possible dès t388, puis t402.
7. t403, puis t404.
