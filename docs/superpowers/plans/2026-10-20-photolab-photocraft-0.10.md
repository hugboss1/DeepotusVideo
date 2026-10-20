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

### M5 — mesuré et fait (20/10)
- 20 commandes ouvertes (neuves 104) : 13 `path.*` (ancres, poignées, segments, conversion, ajout / suppression,
  `transform`, détourage set / clear, `style.copy/pasteFill/Stroke`) et 7 `type.*` (`createSelection`,
  `attachToPath`, `detachFromPath`, taille ± ×4). `hitTest`, `caret`, `navigate` restent fermées (saisie à l'écran).
- 9 outils (64 actifs) : groupe P = Plume, Plume libre, Plume de courbure, Ajout / Suppression / Conversion de point ;
  T = Texte, Texte vertical, Masques de texte H / V ; A = Sélection de tracé, Sélection directe. 8 icônes (544).
- Faits moteur : synchrones ; états « Drag Anchor Points », « Drag Direction Point », « Drag Segment »,
  « Convert Point », « Add / Delete Anchor Point », « Transform Path », « Clipping Path » / « Clear Clipping Path »,
  « Paste Fill », « Paste Complete Stroke », « Type Mask », « Change Type Size », « Type on a Path »,
  « Release Type from Path » ; copier le fond / contour ne fait AUCUN état ; un segment DROIT courbé se déplace avec
  ses ancres ; le détourage exige un tracé ENREGISTRÉ ; `path.info` n'a pas de `layer` (forme = calque actif) ;
  masque de texte vide = « Type Mask » sans sélection (l'écran n'envoie rien). **`coalesce`** (clé non documentée
  du moteur) : deux commandes de même clé = UN état (nom du premier) — Plume de courbure / libre = `path.set` (ou
  `shape.create`) + `path.moveAnchors {move:[0,0], curvature}` (le MOTEUR calcule les poignées, D1) ; texte sur
  tracé = `type.create` + `type.attachToPath`.
- Le shell amont ajuste la Plume libre (`fit_trace`) hors moteur : l'écran simplifie (RDP, Ajustement de courbe
  0,5..10 px, angles > 70°) et le moteur lisse. Menu contextuel des outils de tracé (toile et lignes du panneau
  Tracés) : sélection, remplir, contour, détourage, Transformer le tracé (dialogue numérique amont), fond / contour.
- Hors lot : Ajout / suppression automatique de la Plume (option amont active par défaut — changerait le clic de la
  Plume actuelle), Ctrl pendant la Plume (Sélection directe du tracé en cours), Transformation manuelle du tracé à la
  souris (Ctrl+T), autres calques de forme visibles comme cibles de la Sélection directe, Inverser le texte sur tracé.

## M6 — t255 · Panneau Actions (Q1 = oui, 20/10)
Enregistrer, rejouer, lister, éditer, couleur, conditions ; import/export `.atn` par la Bibliothèque en `data`
(jamais `path`) ; Fichier › Automatisation › Traitement par lots vers la Bibliothèque. Scripts et droplets
restent écartés.

### M6 — mesuré et fait (20/10)
- 18 commandes `actions.*` ouvertes (neuves 86). `photolab_registre._v_actions` / `verifier_etape` : formes clé par clé
  (nom 1..128, rang ≥ 0, couleur, condition parmi 33, `data` base64 ≤ 2 Mo, jamais `path`) ; Arrêt et étape .atn ne
  s'exécutent jamais seuls ; la Condition oui (lecture pas à pas). Deux clés du PONT : `until` (actions.play, segment)
  et `replace` (actions.insert, Modifier l'étape). `file.new` admis comme ÉTAPE seulement (PERMIS_ETAPES).
- Faits moteur : synchrones ; actions.record/stop/list/get = aucun état d'historique ; la lecture laisse UN état par
  étape jouée ; `failed` en cas d'échec (la commande répond ok) ; l'enregistrement capte tout `engine.execute`, les
  `batch` (Annuler = `edit.undo` enregistré) et `doc.new` (→ `file.new`), PAS doc.open / save / close / select ni les
  requêtes (list, info) ; **le moteur ne vérifie RIEN de ce qu'on insère** (`file.saveAs`, params faux) → la lecture
  est vérifiée EN PROFONDEUR par le pont (actions appelées, Conditions) avant tout pas ; `actions.load/save` avec
  `path` et `file.automate.batch` sont refusés en automation (« ambient filesystem paths ») ; `actions.load` remplace
  par défaut un jeu du même nom (`replace: true`) — l'écran charge en `replace: false` ; un nom en conflit devient
  « X 2 » ; l'export .atn laisse hors les étapes sans équivalent (`skipUnsupported`), `layer.select` compris.
- Les séquences internes du pont (vignettes, histogramme, repères, analyse) passent par `engine.execute` sur des COPIES
  et s'enregistraient : `SessionMoteur.sequence` suspend l'enregistrement (stop puis record {action}) — sauf
  `historique` (Annuler reste un geste enregistré, comme le moteur).
- Réserve `<données>/photolab/actions.json` (forme actions.get) réécrite après chaque édition, rejouée dans un moteur
  neuf (record + stop d'une action vide, insert, toggle, dialog, setColor, assignSet). Étapes refusées éteintes à
  l'arrêt et à l'import ; on ne peut pas les rallumer.
- Lecture pas à pas : une étape au dialogue allumé (commande à formulaire) ou un Arrêt coupe la lecture en segments ;
  l'écran ouvre le dialogue de la commande avec ses valeurs enregistrées (sans aperçu forcé) ou montre le message.
- Traitement par lots : une image par appel (`/actions/lot`), document copié sous entrees/, action jouée, enregistré
  sous exports/, refermé, déposé dans la Bibliothèque avec la lignée ; le document de l'utilisateur n'est pas touché.
- Hors lot : touches de fonction des actions (le moteur les lit dans les .atn mais ne les expose pas), options de
  lecture (accélérée / pas à pas / pause), dialogues des actions APPELÉES (le moteur les joue sans interface),
  scripts et droplets (D9), Nouveau jeu vide gardé par l'écran seulement (le moteur n'a pas de jeu sans action).

## M7 — t256 · Calques, historique, nuancier, Déformation
`removeBackground` local en option à côté du détourage IA (le nôtre reste) ; Relight, Couleur en alpha ;
`showOnly`, verrou de transparence, couleur d'étiquette, `mergeGroup`, `copyToDocument`, cadre, plan de
travail voisin, `layerStyle.*` neufs, `layerMask.edit` ; objets dynamiques (`convertToLayers`,
`updateChanged`, et les 4 `sans_ecran` par un fichier de la Bibliothèque copié sous la racine) ;
instantanés d'historique ; import/export .aco/.ase vers NOTRE nuancier ; Ctrl+T › Déformation
(`edit.transform.warpGrid`).

**t256 livrée en trois PR successives** (calques, puis historique + nuancier, puis Déformation).
PR 1 — calques (20/10) : 17 commandes ouvertes (neuves 86 -> 69) ; menus Calque / Filtre complétés par
`INSERTIONS_M7` (mod-menus : Retirer l'arrière-plan (local), Dupliquer vers un document, Couleur du calque, Fusionner
le groupe, Nouveau › Arrière-plan d'après un calque / Plan de travail voisin / Cadre, Objets dynamiques › Convertir en
calques, Rastériser › Style de calque, Rendu › Rééclairer, Autre › Couleur en alpha) ; panneau Calques : Alt-clic sur
l'œil (`showOnly`), couleur d'étiquette, « / » (`toggleLockTransparency`), double-clic sur le masque (`layerMask.edit`),
badge fx glissé (`transferEffects`, Alt : copie) ; Style de calque : Définir / Rétablir les valeurs par défaut
(`makeDefault` / `defaultFor`). Restent fermées : `layerStyle.replace` (le dialogue applique déjà effet par effet) et
les 5 commandes d'objets dynamiques à chemin (`relinkToFile`, `replaceContents`, `exportContents`, `convertToLinked`,
`updateChanged`) : **le moteur 0.10 les désactive en automation** (« uses ambient filesystem paths ») — Bloqué moteur.
Le moteur rend actif le document DESTINATAIRE de `copyToDocument` ; l'écran le suit (`PL.suivreDocumentActif`).
PR 2 — historique et nuancier (20/10) : 5 commandes ouvertes (neuves 69 -> 64) : instantanés dans le panneau
Historique (nouvel instantané, choisir = un état à son nom, renommer, supprimer ; `doc.inspect.snapshots`), Nouveau
document à partir de l'état actuel (le nouveau document devient actif, l'écran le suit). `history.undo/redo/selectState/
deleteState` restent fermées : le panneau annule déjà par /historique. Nuancier : Importer / Exporter .aco / .ase par
les routes `/nuancier/importer` et `/nuancier/exporter` (base64 : `swatches.export {path}` est désactivée en
automation) ; la bibliothèque du moteur n'est qu'un passage (vidée, remplie, exportée, remise aux défauts d'usine dans
UNE séquence) ; `swatches.*` restent fermées à /executer.
PR 3 — Déformer (20/10) : `edit.transform.warpGrid` ouverte (neuves 64 -> 63, taille Par défaut / 3 / 4 / 5) par la
route `/deformer/grille` (séquence hors enregistrement d'action : c'est de la géométrie, aucun état). Ctrl+T : bouton
« Déformer » de la barre (icône dz-edit-deformer-maillage, 547 icônes) -> maillage du moteur, ancres (qui emmènent leurs
poignées) et poignées à glisser, aperçu moteur (`edit.transform.warp` admis en aperçu), Ctrl+Z dans la session ; une
transformation libre déjà posée est reportée sur le maillage ; validation `edit.transform.warp {layer, warp,
interpolation}` = un état « Warp » (« Déformer »). Le menu Édition › Transformation › Déformer (styles prédéfinis,
dialogue générique) n'est pas touché.

## M8 — t257 · Formats et exports
Ouvrir depuis la Bibliothèque : ORA, Krita, Affinity, Paint.NET, EXR (parties), DPX, DDS, raws (HEIC selon
Q3) ; enregistrer : TIFF à calques, WebP, ORA, PDF d'une page ; Calques en fichiers et jeux de données par
`doc.exportLayers`/`doc.exportDataSets` vers la Bibliothèque (sort des `file.export` « bientôt ») ;
préréglages d'export (`file.export.presets.*`). Garde #7025 (document actif) et #7023 (`quality` entier).

### M8 — mesuré et fait (20/10)
Sondé sur le vrai moteur 0.10 : `doc.exportLayers {dir, format, prefix, visibleOnly, quality, tiffLayers}` et
`doc.exportDataSets {dir, format, dataSets, naming}` écrivent sous la racine (refus de `..` et d'un absolu), REFUSENT
d'écraser (« AlreadyExists ») et ignorent une clé inconnue ; leur `quality` est sur **0..12** (au-delà : borné, 50 = 100),
celle de `doc.save` sur 1..100 ; #7025 confirmé (`index` -> ce document reste actif) ; #7023 confirmé (`quality: 80.0` ->
WebP sans perte en silence). `doc.save` : ORA (rattache le document), PDF (avertissement « saved flattened »), TIFF
`tiffLayers` relu avec ses calques ; ouverture ORA, TIFF à calques, DPX, TGA, DDS ; PDF jamais en ouverture.
**Bloqués moteur** (désactivés en automation, « ambient filesystem paths ») : `file.exrParts` / `file.openExrParts`
(EXR multi-parties : `doc.open` seul), `file.export.presets.*` (préréglages d'export) -> gardés par Deepotus.
Image › Variables : le registre écrit `{defs:[…]}` sans guillemets (illisible) et le moteur ne vérifie presque rien ->
vérification clé par clé au pont (visibilité, remplacement de texte ; `pixelReplacement` = un chemin, refusé).
Livré : Fichier › Ouvrir depuis l'ordinateur… (route `/importer`, octets bruts, extensions `PM.FORMATS_OUVERTURE`,
1 Gio, HEIC refusé nommément — Q3 non tranchée ; ce que la Bibliothèque reçoit y passe d'abord) ; Exporter : ORA, PDF
d'une page, TIFF à calques, avertissements du moteur traduits, préréglages (`/export/prereglages`) ; Calques en
fichiers (`/calques/fichiers`) et Jeux de données en fichiers (`/jeux/fichiers`) déposés dans la Bibliothèque (lignée
« retouche », dossier `sorties/<lot>` effacé) ; Importer › Jeux de données variables (`/jeux/importer`, CSV en texte) ;
Image › Variables › Définir… / Jeux de données…, Image › Appliquer un jeu de données… (mod-exports). « bientôt » 89 -> 86.
Restent : Préférences d'exportation (préférences du moteur), Ouvrir en tant que… (chemin), HEIC (Q3).

## M9 — t258 · Libellés : fr.tsv amont en repli
`photocraft_catalogue.py` lit `fr.tsv` de v0.10.0 (plus le commit 3d23a708c2) ; libellés FR/EN des commandes
neuves ; nos 412 libellés restent prioritaires ; attribution ajoutée.

## M10 — t259 · Installation, licences, aide
`build-installer.ps1` (vendor 0.10.0 vérifié), NOTICE et nouvelles attributions (traductions, rgb.txt,
libfacedetection, icônes), À propos ; fiches didactiques des outils neufs ; chapitre Photolab du guide.
