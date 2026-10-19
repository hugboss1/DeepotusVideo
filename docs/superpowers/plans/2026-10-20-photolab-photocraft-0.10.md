# Plan : Photolab à jour de photocraft 0.10.0 (20/10/2026)

Relevé et décisions : `docs/superpowers/specs/2026-10-20-photolab-photocraft-0.10-ecart.md`.
Skills : `lab-externe-deepotus` (moteur, pont, installation), `parite-photolab` (entrées « bientôt »),
`traduction-deepotus`, `didacticiel-option`, `guide-deepotus`.
Suivi : lot « Photolab photocraft 0.10 », tâches t249-t259. Une tâche à la fois, dans l'ordre :
M1 → M2 sont des prérequis ; M3 à M8 sont indépendantes entre elles une fois M2 fusionnée ; M9-M10 ferment.

Règles communes : TDD, mutations, preuve sur 8799 en FR et EN, compte rendu, PR, installation par table
hash-object. **Garde « ne rien écraser »** : le banc de non-régression d'écran de M1 tourne à chaque tâche.

## M0 — t249 · Relevé et plan (FAIT 20/10)
Spec d'écart, annexes `specs/photocraft-0.10/`, outils `scripts/photocraft_releve/`, ce plan.

## M1 — t250 · Moteur 0.10.0 épinglé + liste des commandes + banc de non-régression
- **Avant tout** : instantané `backend/tests/photolab_etats_0.3.0.json` des états des 633 entrées, 45 outils et
  panneaux (scripts `exporter_registre.py` + `lister_bientot.mjs`), et banc `test_photolab_non_regression`.
- Accord de l'utilisateur pour télécharger `photocraft-0.10.0-windows-x64-portable.zip` (84 828 713 o) depuis la
  release officielle ; sha256 recoupé avec `SHA256SUMS.txt`. `vendor/photocraft.json` 0.10.0 (fichiers + sha).
- Capturer `engine.commands` du VRAI binaire → `backend/tests/photocraft_commandes_0.10.0.json` ; le comparer à
  `photocraft_commandes_main-reconstruit.json` ; écrire `scripts/photocraft_commandes.py` (régénération).
- Une seule constante de version (pont, routes, `verifier_vendor.py`, `build-installer.ps1`, guide) ; bancs
  qui lisent le JSON par ce nom unique.
- Fini quand : l'ancien et le nouveau moteur cohabitent le temps de M2, bancs vendor/catalogue verts.

## M2 — t251 · Pont adapté à 0.10 et fidélité rejouée
- `doc.save` : rattachement et document actif restauré (revoir t139, Enregistrer dans la Bibliothèque) ;
  `index` strict ; champs `disabledReason`/`needsDocument`/`keywords` tolérés ; `--control` : auth < 10 s.
- `PREFIXES_REFUSES` / `PERMIS_REFUSES` relus contre la nouvelle liste amont des refus en automation ;
  `photolab_registre.py` re-sondé (`CORRECTIONS_CHAMPS`, `CLES_CHEMIN`, `KINDS`, `PROFILS_MODE`), liste blanche
  régénérée ; les 142 commandes neuves restent refusées tant qu'un lot ne les ouvre pas.
- Bancs de fidélité, aperçu, peinture, texte, transformation, masques, mesure rejoués contre le CLI 0.10 ;
  chaque écart de pixels consigné (espacement retouche, bicubique, Niveaux, Postériser…).
- `ETATS_MOTEUR` de l'historique régénéré depuis les sources 0.10. Retrait du moteur 0.3.0.
- Fini quand : non-régression d'écran verte (aucune entrée perdue), 29 bancs + 35 QA verts sur 0.10.

## M3 — t252 · Retouche : Pièce, Déplacement basé sur le contenu, Tampon de motif, Œil rouge, Supprimer
`paint.patch`, `contentAwareMove`, `patternStamp`, `redEye`, `remove` sur le modèle de `mod-peinture` ;
symétrie de peinture (`paint.setSymmetry`…) ; clés Mode et Tous les calques du Pot et du Correcteur localisé
si les params 0.10 les offrent. L'outil Pièce sort de « bientôt ».

## M4 — t253 · Sélection, recadrage, échantillons
Lasso magnétique, Rectangle 1 rangée / 1 colonne, Recadrage de perspective (`image.perspectiveCrop`),
Remplissage d'après le contenu au recadrage, Échantillonneur de couleur (`view.colorSamplers.*`, lecture dans
le panneau Infos), Rotation de la vue (écran), `select.float/drop`, `select.loadLuminosity`.

## M5 — t254 · Plume et texte
Sélection directe, Plume libre et de courbure, Ajout/Suppression/Conversion de point (`path.*`),
`path.transform`, tracé de détourage, copier/coller fond et contour ; Texte vertical, Masques de texte H/V
(`type.createSelection`), texte sur tracé, taille ± (raccourcis). `mod-trace` et `mod-texte` étendus.

## M6 — t255 · Panneau Actions (Q1 = oui, 20/10)
Enregistrer, rejouer, lister, éditer, couleur, conditions ; import/export `.atn` par la Bibliothèque en `data`
(jamais `path`) ; Fichier › Automatisation › Traitement par lots vers la Bibliothèque. Scripts et droplets
restent écartés.

## M7 — t256 · Calques, historique, nuancier, Déformation
`removeBackground` local en option à côté du détourage IA (le nôtre reste) ; Relight, Couleur en alpha ;
`showOnly`, verrou de transparence, couleur d'étiquette, `mergeGroup`, `copyToDocument`, cadre, plan de
travail voisin, `layerStyle.*` neufs, `layerMask.edit` ; objets dynamiques (`convertToLayers`,
`updateChanged`, et les 4 `sans_ecran` par un fichier de la Bibliothèque copié sous la racine) ;
instantanés d'historique ; import/export .aco/.ase vers NOTRE nuancier ; Ctrl+T › Déformation
(`edit.transform.warpGrid`).

## M8 — t257 · Formats et exports
Ouvrir depuis la Bibliothèque : ORA, Krita, Affinity, Paint.NET, EXR (parties), DPX, DDS, raws (HEIC selon
Q3) ; enregistrer : TIFF à calques, WebP, ORA, PDF d'une page ; Calques en fichiers et jeux de données par
`doc.exportLayers`/`doc.exportDataSets` vers la Bibliothèque (sort des `file.export` « bientôt ») ;
préréglages d'export (`file.export.presets.*`). Garde #7025 (document actif) et #7023 (`quality` entier).

## M9 — t258 · Libellés : fr.tsv amont en repli
`photocraft_catalogue.py` lit `fr.tsv` de v0.10.0 (plus le commit 3d23a708c2) ; libellés FR/EN des commandes
neuves ; nos 412 libellés restent prioritaires ; attribution ajoutée.

## M10 — t259 · Installation, licences, aide
`build-installer.ps1` (vendor 0.10.0 vérifié), NOTICE et nouvelles attributions (traductions, rgb.txt,
libfacedetection, icônes), À propos ; fiches didactiques des outils neufs ; chapitre Photolab du guide.
