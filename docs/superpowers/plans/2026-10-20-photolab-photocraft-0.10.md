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
- **Mesuré en M1 (20/10)** : `test_photolab_non_regression --commandes tests/photocraft_commandes_0.10.0.json` est
  ROUGE — 9 entrées qui marchent repasseraient « bientôt » (`edit.paste`, 3 `edit.pasteSpecial.*`,
  `edit.transform.flip*` ×2, `rotate180`, `rotate90Cw/Ccw`). Cause : 0.10 leur ajoute
  `"target":"pixels"|"mask"|"quickMask"|{"channel":i}=Channels panel target (…)`, que `photolab_registre.parser`
  lit comme un champ `?` OBLIGATOIRE (défaut en texte libre) → `sansEcran`. À corriger dans le parseur (un défaut
  texte = optionnel ; union de chaînes et d'objet) ou par `CORRECTIONS_CHAMPS`, puis le banc doit passer au vert.
- Seule différence entre la liste reconstruite (statique) et la capture réelle : les `params` des 24
  `layer.newAdjustmentLayer.*` — la capture fait foi.
- Fini quand : non-régression d'écran verte (aucune entrée perdue), 29 bancs + 35 QA verts sur 0.10.

### M2 — mesuré et fait (20/10)
Bascule : `vendor/photocraft.json` = 0.10.0 (manifeste candidat retiré), repli de version 0.10.0. Ruptures réelles
trouvées par les bancs sur le vrai moteur, et leur traitement — rien de ce que l'écran faisait n'est retiré :
- **Cible de canal** `target` (Coller, Symétrie, Rotation…) lue comme champ requis → 9 entrées grisées : forme exacte
  reconnue, opaque optionnelle (`photolab_registre._CIBLE_CANAL`). Non-régression d'écran verte sur 0.10.
- **142 commandes neuves fermées** (`photolab_neuves.py`) + champs opaques neufs des réglages (`eyedropper`,
  `replaceColor.points`) fermés par schéma : rien ne s'ouvre par la seule montée.
- **`doc.inspect` des calques de réglage** : `{kind, params}` (inverse exact des paramètres) au lieu de la variante
  interne. Pont (`kind_de`, `_colorise`) et écran (`kindDe`, `depuisInspect` via `variante10`) lisent les deux formes ;
  équivalence prouvée cas par cas sur les fixtures 0.3.0 et 0.10 (qa/reglages10). **Perte** : 0.10 ne dit plus QUEL
  LUT porte un Color Lookup — la liste n'en choisit aucun (le moteur garde le sien).
- **`layer.hideLayers` bascule** en 0.10 (un calque caché est remontré) : l'export d'un calque ne cache plus que le
  visible (sinon un calque caché par l'utilisateur reparaissait dans l'export). Banc 3i2.
- **Calque uni créé sur une sélection = masqué** en 0.10 : `_remplissage` lui rend un masque blanc (vues de
  Sélectionner et masquer, vignettes de masques).
- **Révéler la sélection** retire la sélection en 0.10 (comme Photoshop) ; une commande indisponible renvoie une erreur
  (« not available right now ») — le pont testait déjà `hasSelection` avant `select.deselect`.
- Parseur : `layer.select.layer` (`id|str | "name"`), `tools.setColors` (`"#rrggbb"|[r,g,b,a?]`) et le contour
  d'ombre portée corrigés explicitement → vérification identique à 0.3.0.
- Profils intégrés : + `aces-cg` (RVB), `dot-gain-20-compat` (gris). Libellés FR/EN de 11 paramètres et 6 valeurs
  neufs. Placer : frange bicubique d'1 px (Keys −0,75, amont 0.9) figée par version.
- `ETATS_MOTEUR` : noms inchangés dans les sources 0.10.0 (aucune régénération nécessaire).
- Licences : NOTICE amont 0.10.0 (+ libfacedetection, BSD-3-Clause, texte livré), les 4 autres textes identiques.

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
