# État réel du Photolab (moteur photocraft 0.3.0 épinglé) — relevé du 20/10/2026

Base : worktree `photolab-maj`, HEAD 8f2ff3f2 (= origin/main, #392). Lecture seule, aucun fichier du dépôt modifié.
Sorties de travail dans ce dossier : `registre.json`, `bientot.json`, `bientot.md`, `etats.mjs` (sonde d'états).

Légende : **[mesuré]** = sortie d'un script ou lecture du code ; **[supposé]** = inférence non vérifiée.

---

## 1. Ce qui reste « bientôt » (grisé)

Outils lancés tels quels, sans échec :
- `python exporter_registre.py <worktree> registre.json` (python embarqué `%LOCALAPPDATA%/DeepotusVideoGen/runtime/python`) → « 776 commandes ».
- `node lister_bientot.mjs <worktree> <dossier>` → `bientot.json` / `bientot.md`.

**[mesuré]** 633 entrées de commande dans les menus générés, 45 outils. **93 éléments « bientôt »** :
91 entrées de menu + 1 outil + 1 onglet de panneau. Le 08/10 (spec, base 4dcae97f), il y en avait 284.

Détail complet : `bientot.md` (93 lignes). En résumé :

| Raison | Nb | Contenu |
|---|---:|---|
| `refuse:file.` | 37 | Ouvrir en tant que ; Exporter › (Préférences d'export, Web ancien, plans de travail en fichiers/PDF, calques en fichiers, compositions en fichiers, LUT, jeux de données, tracés vers Illustrator, rendu vidéo) ; Générer › ressources ; Placer lié ; Rassembler ; Automatisation › 9 (lots, droplet, recadrer-redresser, planche contact, changement de mode conditionnel, adapter l'image, correction d'objectif, HDR Pro, Photomerge) ; Scripts › 8 ; Importer › 3 (jeux de données, images vidéo, WIA) ; Imprimer, Imprimer un exemplaire ; Quitter |
| `refuse:window.` | 21 | Fenêtre › Organiser › 19 (`window.arrange.*`), Fenêtre › Actions, Fenêtre › Montage |
| `refuse:edit.presets` | 1 | `edit.presets.migratePresets` (chemin) |
| `absent_moteur` | 21 | `view.proofSetup.{custom, workingCmyk, internetStandardRgb, monitorRgb}` (4) ; `view.pixelAspectRatio.*` (9) + `view.pixelAspectRatioCorrection` ; `view.fitArtboardOnScreen` ; `view.show.{targetPath, artboardGuides, smartGuides, mesh, editPins}` ; `view.patternPreview` |
| `D9` | 6 | `edit.puppetWarp`, `layer.smartObjects.puppetWarp`, `filter.cameraRaw`, `filter.adaptiveWideAngle`, `filter.liquify`, `filter.vanishingPoint` |
| `sans_editeur_nomme` | 1 | `filter.other.custom` |
| `sans_ecran` | 4 | `layer.smartObjects.{relinkToFile, replaceContents, exportContents, convertToLinked}` — seul champ : `path:str` |
| `outil` | 1 | `outil.patch` (Pièce, J) — `mod-outils.js:19` `p2:false` |
| `panneau` | 1 | `panneau.actions` (aucun onglet Actions dans `index.html`) |

### 2. Comptes par famille d'id (des 93) [mesuré]

| Famille | Nb | | Famille | Nb |
|---|---:|---|---|---:|
| `window.arrange.*` | 19 | | `view.pixelAspectRatio.*` | 9 |
| `window.panel.*` | 2 | | `view.proofSetup.*` | 4 |
| `file.*` (racine) | 6 | | `view.show.*` | 5 |
| `file.export.*` | 10 | | `view.*` (racine) | 3 |
| `file.automate.*` | 9 | | `layer.smartObjects.*` | 5 |
| `file.scripts.*` | 8 | | `filter.*` | 5 |
| `file.import.*` | 3 | | `edit.*` (puppetWarp) | 1 |
| `file.generate.*` | 1 | | `edit.presets.*` | 1 |
| `outil.*` | 1 | | `panneau.*` | 1 |

Rien ne reste en `type.*`, `image.mode.*`, `edit.transform.*`, `edit.preferences.*`, `window.workspace.*`, `select.*`.

État complet des menus par famille, calculé par `etats.mjs` sur la fixture [mesuré] :
`file` 14 actifs / 37 bientôt ; `edit` 33 / 2 (+41 « inactif ») ; `view` 34 / 21 (+19 inactif) ; `window` 40 / 21 ;
`type` 14 / 0 (+30) ; `layer` 2 / 5 (+153) ; `filter` 0 / 5 (+70) ; `image` 1 / 0 (+60) ; `select` 1 / 0 (+24) ; `pl` 6 / 0.
« inactif » = commande du moteur avec `enabled:false` dans la fixture. **[supposé]** La fixture a été capturée SANS
document ouvert (671 des 776 commandes ont `enabled:false`). En vrai, l'écran lit `enabled` du moteur vivant, donc ces
entrées ne sont pas « bientôt ».

Remarque pour la comparaison **[mesuré]** : le moteur 0.3.0 a `view.proofSetup` (avec un champ `profile`),
`view.proofColors` et `view.gamutWarning`. Les 4 ids `view.proofSetup.*` absents sont donc des commandes du shell que
l'on pourrait composer. La spec du 08/10 les a pourtant écartés (§4 : « Format des pixels, épreuve CMJN (15) …
**Écarté** »). Les ids `edit.transform.warp`, `edit.perspectiveWarp` et `type.warpText` existent dans le registre.

---

## 3. Ce que l'écran fait LUI-MÊME (à ne jamais écraser lors d'une montée de version)

### 3.1 Les listes d'aiguillage (`frontend/photolab/js/mod-menus.js`)
- `REFUSES` (:12) est la copie en minuscules de `PREFIXES_REFUSES`. `PERMIS` (:17) est la copie de `PERMIS_REFUSES` (18 ids). Un banc relit le Python et compare les deux.
- `IDS_PREFERENCES_ECRAN` (:25, 23 ids), `IDS_MESURE` (:33, 7), `IDS_DOCUMENTS` (:40, 9), `IDS_IA` (:43, 2).
- `TRAITES_PAR_ECRAN` (:45-90). **[mesuré]** 139 ids, dont 33 seulement existent dans le registre du moteur. Les 106 autres sont des ids du shell ou de l'écran (`pl.*`). Répartition : `window.panel` 30, `window.workspace` 10, `edit.preferences` 18, `view` 13 + `view.show` 12 + `view.snapTo` 6 + `view.screenMode` 3, `file` 11 + `file.export` 2 + `file.import` 1, `type.*` 14, `edit.transform` 5 + `edit` 4, `edit.presets` 2, `layer` 2, `select` 1, `pl.*` 5.
  Les 33 présents au moteur sont interceptés par l'écran, qui ne les envoie JAMAIS au moteur. Ce sont `file.new`, `file.close*`, `saveACopy`, `revert`, `placeEmbedded`, `fileInfo`, `layer.quickExportAsPng`, `layer.exportAs`, `file.import.notes`, les 18 `edit.preferences.*`, `edit.keyboardShortcuts`, `edit.menus` et `edit.presets.{presetManager, exportImportPresets}`.
- `etatDe` (:155) : `TRAITES_PAR_ECRAN` → actif ; préfixe refusé et absent de `PERMIS` → bientôt ; inconnu du registre → bientôt.
- `actionEntree` (:255) : `TRAITES_PAR_ECRAN` ou `pl.*` → « ecran ».
- `aiguillage` : éditeurs sur mesure pour `curves`, `levels`, `filterGallery`, `image.mode.*`, `layer.newAdjustmentLayer.*` et les 11 `layer.layerStyle.*`.
- `mod-champs.js:28` `D9` (6 ids), `:34` `SANS_EDITEUR` (`filter.other.custom`). Y sont aussi `OPAQUES` et `CLES_CACHEES`.
- `menus.json` : 765 lignes du catalogue, tirées de `menu_catalog.rs` v0.3.0 et de `fr.tsv` au commit 3d23a708c2.
  L'écran y insère des entrées `pl.*` : Envoyer vers, app native, calque IA, détourer, À propos.

### 3.2 Modules, par nature

**Purement écran (aucune commande moteur)** [mesuré : aucun id moteur dans le source, ou seulement des ids d'aiguillage]
| Module | Ce qu'il fait | Stockage |
|---|---|---|
| `mod-espaces.js` (t151) | 7 espaces (Essentiel, Base, Graphisme et web, Mouvement, Peinture, Photo, Pixel art), dispositions par groupes et onglets, colonne repliée, barre d'outils sur 1 ou 2 colonnes, Nouveau / Supprimer / Réinitialiser / Verrouiller, Fenêtre › <panneau>, F5-F8 | `/api/photolab/espaces` → `photolab_espaces.py`, dont GROUPES / FOURNIS / MAX_PERSO sont une copie exacte (banc test_photolab_espaces) |
| `mod-preferences.js` (t159) | Édition › Préférences : 18 sections ; clés et bornes reprises de `prefs.get` / `prefs.set` de photocraft, mais **jamais** envoyées à `prefs.*` | `/api/photolab/preferences` → `photolab_preferences.py` SCHEMA (copie comparée par banc) |
| `mod-clavier.js` (t159) | Raccourcis clavier et Menus personnalisés (`edit.keyboardShortcuts`, `edit.menus`) | PL.prefs |
| `mod-modificateurs.js` (t159) | Fenêtre › Touches de modification (Maj / Ctrl / Alt armées pour le geste suivant) | — |
| `mod-recherche.js` (t156) | Édition › Rechercher (`edit.search`), une palette sur les menus actifs et les outils | — |
| `mod-raccourcis.js` | raccourcis du catalogue + Ctrl+Z, Ctrl+Maj+Z, Ctrl+Maj+I ajoutés | — |
| `mod-vue.js`, `mod-navigateur.js` | zoom par les paliers de photocraft, main, navigateur | — |
| `mod-proprietes.js` | panneau Propriétés en lecture seule | — |
| `mod-apropos.js` | À propos, licences (`/licences`) | — |
| `mod-cycle.js`, `mod-api.js`, `mod-gestes.js` | cycle inspecter → rendu (D1), file d'attente, répartiteur des gestes | — |

**Écran + moteur (l'écran porte une logique propre, le moteur calcule)**
| Module | Logique maison | Commandes moteur appelées |
|---|---|---|
| `mod-affichage.js` (t152) | zooms, symétrie de vue, modes d'écran, extras, grille, grille de pixels, contours, règles, aimantation, verrou des repères, aperçu pixel art = surcouches d'écran ; options en localStorage | seulement `view.newGuide` / `moveGuide` / `deleteGuide` (+ GET `/reperes`) |
| `mod-transformer.js` (t154) | session Ctrl+T : cadre, 8 poignées, point de référence, sous-modes contraints (Échelle, Rotation, Inclinaison, Déformation, Perspective), barre X/Y/L/H/angle | `edit.transform {layer, rect, quad, interpolation}`, aperçu sur copie par `/apercu` |
| `mod-deplacer.js` | aperçu CSS pendant le glisser | `edit.transform`, `layer.translate`, `layer.pickAt` |
| `mod-peinture.js` (t155) | 18 outils ; conversion d'unités (0..1 contre 0..100) ; contour d'aperçu | `paint.{stroke, pencil, backgroundEraser, magicEraser, cloneStamp, healingBrush, spotHealing, historyBrush, mixerBrush, blur, sharpen, smudge, dodge, burn, sponge, bucket, gradient}`, `cloneSource.*` |
| `mod-pinceaux.js` (t155) | panneaux Pinceaux, Paramètres (forme de la pointe seulement), Source de duplication, Outils prédéfinis | `brush.presets.list`, `brush.get`, `tools.setBrush`, `cloneSource.*`, `tool.presets.*` |
| `mod-texte.js` (t156) | éditeur posé sur la toile ; panneaux Caractère, Paragraphe, Glyphes et Styles ; `type.panels.*`, `type.fontPreviewSize.*` et `type.languageOptions.*` traités à l'écran | `type.create`, `type.edit`, `type.setStyle`, `type.info`, `type.fonts`, `type.insertText`, `type.antiAlias.*`, `type.orientation.*` |
| `mod-formes.js` (t156) | géométrie des gestes (Maj, Alt), aperçu du contour | `shape.create`, `shape.presets.place` |
| `mod-trace.js` (t156) | Plume (sommets, poignées), Sélection de tracé, panneau Tracés | `path.{set, list, info, delete, rename, fill, stroke, toSelection}`, `select.toWorkPath`, `shape.create`, `shape.edit` |
| `mod-mesure.js` (t160) | surcouche règle, comptage, notes, tranches ; panneaux Journal et Notes | `image.analysis.{rulerTool, recordMeasurements, selectDataPoints, straightenLayer}`, `count.*`, `notes.*`, `slice.*`, `measurementLog.{list, delete}` ; export CSV composé par le pont (`/mesures.csv`) ; import de notes par `/notes/importer` |
| `mod-galerie.js` (t157) | dossiers de vignettes, pile d'effets, réédition d'un filtre dynamique | `filter.filterGallery`, `filter.gallery.*`, `layer.smartFilter.setParams` ; vignettes `/galerie/vignettes` |
| `mod-masquer.js` (t157) | dialogue « Sélectionner et masquer » (`select.selectAndMask` n'existe pas au moteur) ; 7 vues ; touches F, X, P | `select.refineEdge`, `select.inverse`, `/masquer/apercu` |
| `mod-mode.js` (t158) | Image › Mode : coches, confirmation d'aplatissement, éditeurs Bichromie et Table des couleurs | les 12 `image.mode.*` rouverts un à un, profil INTÉGRÉ uniquement |
| `mod-documents.js` (t158) | onglets de documents, Tout fermer, Fermer les autres, Enregistrer une copie, Revenir, Export rapide, Placer incorporé, Infos fichier, Exporter le calque | `document.activate` ; routes `/copie`, `/revenir`, `/placer`, `/calque/exporter`, `/enregistrer` |
| `mod-fichier.js` | Nouveau, Ouvrir (Bibliothèque), Enregistrer, Exporter, Fermer | aucune commande `file.*` : routes `/nouveau`, `/ouvrir`, `/bibliotheque`, `/enregistrer` (le pont emploie `doc.new`, `doc.open`, `doc.save`, `doc.close`) |
| `mod-nuancier.js` (t153) | le Nuancier est une donnée Deepotus (le moteur n'a pas de commande de nuancier) | `tools.setColors` ; stockage `/nuancier` (`photolab_nuancier.py`, défaut copié de `etatDefaut()`) |
| `mod-gestionnaire.js` (t159) | dialogue du gestionnaire et échange en .json dans la page | `edit.presets.presetManager`, `edit.presets.exportImportPresets` (format `photocraft-presets` v1) |
| `mod-iacalque.js` (t191) | calque IA et détourage non destructif (fal, DzModelesIA) | `layer.select` ; routes `/calque/ia` et `/calque/detourer` (export du calque, `layer.setProps visible:false`, placement) |
| `mod-couches.js` (t153) | vue d'une ou deux couches composée à l'affichage (`doc.render` rend toujours le composite) | `channel.*`, `select.loadSelection`, `select.saveSelection` |
| `mod-calques.js` | verrous et groupes repliés gardés à l'écran (le moteur ne les relit pas) | `layer.*`, `layer.layerMask.*`, `layer.smartFilter.*`, `layer.linkLayers`, `layer.vectorMask.add` |
| `mod-historique.js` | clic sur un état = N annulations (`/historique`) ; table `ETATS_MOTEUR` (:36) des noms d'états relevés dans les sources 0.3.0 | — |
| Fidèles au moteur (peu de logique) | `mod-couleur`, `mod-pipette`, `mod-selection`, `mod-recadrer`, `mod-courbes` (LUT d'aperçu JS pendant le glisser, puis moteur), `mod-reglages`, `mod-styles`, `mod-presets`, `mod-compositions`, `mod-infos` | `tools.*`, `document.pixel`, `select.*`, `image.crop`, `layer.setAdjustment`, `layer.layerStyle.*`, `*.presets.*`, `layerComp.*` |

**Côté pont, compositions maison** (`photolab_moteur.py`) : vignettes, historique, aperçu sur COPIE
(`apercu`, `COMMANDES_APERCU` :565), histogramme, couches alpha, masques, aperçu du masque, catalogue et vignettes de la
galerie, `copie_document`, `exporter_calque`, `revenir`, `placer`, `reperes`, `analyse`, `journal_csv`,
`importer_notes`, vignettes de motifs et de préréglages, `elaguer_inspect`. Toutes reposent sur la forme actuelle de
`doc.inspect` et de `doc.render`.

---

## 4. Le pont backend et tout ce qui dépend de 0.3.0

### 4.1 `backend/app/services/photolab_moteur.py` (1503 lignes)
- `:25` `VERSION = "0.3.0"`.
- `:50-59` `chemin_cli()` : `PHOTOCRAFT_CLI` sinon `vendor/photocraft-{VERSION}/**/photocraft-cli.exe`.
- `:87` `PREFIXES_REFUSES` (16 préfixes, comparés en minuscules) : `file.`, `app.`, `automate.`, `plugin.`, `script`, `window.`, `help.`, `edit.preferences`, `edit.presets`, `edit.keyboardshortcuts`, `edit.menus`, `image.mode.`, `brush.presets.import`, `gradient.presets.import`, `prefs.`, `measurementlog.export`.
- `:93` `PERMIS_REFUSES` (18) : `file.close`, `closeAll`, `closeOthers`, `fileInfo`, les 12 `image.mode.*`, `edit.presets.presetManager`, `exportImportPresets`.
- `:99` `_EXT_FICHIER` et `:106` `_valeur_fichier` : refus de toute valeur qui ressemble à un fichier.
- `:112` `commande_autorisee(cid, params, registre, kind, etat)` : sans registre, tout est refusé ; sinon `PR.verifier` (liste blanche : commande connue, clés décrites, types, bornes).
- Registre mis en cache par (session, génération) (`:129-158`).
- **Protocole `serve` en stdio** :
  - `:415` lancement : `photocraft-cli serve --automation-read-root <DATA>/photolab --automation-write-root <DATA>/photolab`. Sous-dossiers `entrees`, `rendus`, `exports`.
  - Requête, une ligne JSON (`:341`) : `{"id": <entier croissant>, "method": "<méthode>", "params": {...}}\n`.
  - Réponse, une ligne JSON (`:363-376`) : `{"id": n, "ok": true, "result": ...}` ou `{"id": n, "ok": false, "error": "..."}`. `{"id": null, "ok": false}` = ligne illisible. Les lignes d'un autre id ou non JSON sont ignorées.
  - Une requête à la fois (verrou), délai de 60 s. Au-delà, kill puis relance avec `generation + 1`. La fin de stdin arrête le serveur.
  - `sequence()` enchaîne plusieurs étapes sous un seul verrou.
  - Méthodes réellement appelées [mesuré, `photolab_*.py` et `photolab_routes.py`] : `doc.inspect` 26, `engine.execute {command, params}` 22, `session.list` 16, `doc.render` 9, `doc.save` 6, `doc.close` 6, `doc.select` 4, `doc.open` 4, `engine.commands` 2, `doc.new` 2, `batch` 1, `app.save` 1 (app native).
- App native (`photolab_natif.py`) : `photocraft.exe --control <port> --control-token-file …`. Ligne d'authentification `{"method":"auth","params":{"token":…}}`, puis `app.open`, `app.save`, `ui.focus`, `app.quit` (`control_server.rs` v0.3.0, `:4`, `:55`).

### 4.2 `photolab_registre.py` (1115 lignes)
- Parseur de la grammaire « JSON-ish » `params` → champs typés. Méthodes `structurer` et `verifier`.
- **[mesuré]** 126 des 776 descriptions ne sont pas entièrement comprises (`ok:false`), par exemple `paint.stroke`, `type.create`, `edit.transform`, `shape.create`, `path.*`, `view.proofSetup`. Des validateurs ad hoc les couvrent.
- Points liés à 0.3.0 :
  - `:36-37` : « les guillemets échappés … le registre épinglé 0.3.0 n'en contient pas. **À revoir si le moteur change de version.** »
  - `:141` : « Supposé : le registre 0.3.0 n'emploie pas de couleur nue ».
  - `:225` `CORRECTIONS_CHAMPS` (exposure en EV).
  - `:252` `CLES_CHEMIN`.
  - `:258` `COMMANDES_TRACE`.
  - `:272` `KINDS` (noms internes des réglages dans `doc.inspect`).
  - `SCHEMAS` des structures internes (stops, courbes, niveaux, mixeur…).
  - `:694` `PROFILS_MODE` : « Profils intégrés du moteur 0.3.0 … relevé 09/10 ».
  - `:882` format `photocraft-presets` v1.
  - Les validateurs t153-t160 (`_v_comptage`, `_v_notes`, `_v_tranches`, `_galerie`, `_v_bichromie`…) figent des formes relevées sur 0.3.0.

### 4.3 `backend/app/api/photolab_routes.py` (1191 lignes) — 44 routes [mesuré]
`/etat` (`:108` version = `PM.VERSION`), `/commandes`, `/nouveau`, `/ouvrir`, `/executer`, `/inspecter`, `/rendu`, `/apercu`,
`/histogramme`, `/enregistrer`, `/session`, `/historique`, `/vignettes`, `/reperes`, `/motifs/{id}.png`,
`/presets/{genre}/vignette.png`, `/couches`, `/masques`, `/masquer/apercu`, `/galerie`, `/galerie/vignettes`, `/copie`,
`/calque/exporter`, `/revenir`, `/placer`, `/bibliotheque`, `/rendus/{nom}`, `/exports/{nom}`, `/natif/etat|ouvrir|reprendre`,
`/espaces`, `/preferences` (+ `/reinitialiser`), `/nuancier`, `/licences` (`:763` `vendor/photocraft-{VERSION}` ; `:833`
lit le manifeste), `/licences/{nom}`, `/analyse`, `/mesures.csv`, `/notes/importer`, `/calque/ia`, `/calque/detourer`.

### 4.4 Épinglage et fournisseur
- `vendor/photocraft.json` contient :
  - version 0.3.0, tag v0.3.0, dépôt `storytold/photocraft`, licence MIT OR Apache-2.0 ;
  - l'archive `photocraft-0.3.0-windows-x64-portable.zip`, de taille 65251740 et de sha256 `9997f7df…cd47e` ;
  - `dossier: vendor/photocraft-0.3.0`, l'archive des sources v0.3.0 ;
  - `fichiers` : 9 fichiers (taille et sha256 de chacun : `photocraft-cli.exe` `cd88dee7…`, `photocraft.exe` `51ee4ff6…`, licences, OFL, README, `portable.txt`).
- `scripts/vendor_photocraft.py` télécharge l'archive (par gh, sinon urllib). Il vérifie la taille et le sha256 AVANT d'extraire, extrait dans `vendor/photocraft-0.3.0/` et refuse les entrées hors du dossier.
- `scripts/verifier_vendor.py` vérifie fichier par fichier contre `fichiers` (un fichier en trop est un écart) et ignore `PhotoCraftData`. Il refuse une dépendance au CRT VC++ : « la 0.3.0 n'en dépend pas » (`:9`). L'option `--ecrire` régénère `fichiers`.
- `scripts/photocraft_catalogue.py` fabrique `menus.json` depuis `menu_catalog.rs` v0.3.0 et le `fr.tsv` épinglé : `COMMIT_FR = "3d23a708c2"` (`:10`), `BLOB_FR = "453fa2ad…"` (`:11`). Il refuse un fr.tsv d'une autre empreinte.
- `vendor/NOTICE-photocraft.txt` : tag v0.3.0, chemins `photocraft-0.3.0/...`, sources du commit 60224d3.

### 4.5 `backend/tests/photocraft_commandes_0.3.0.json`
- **[mesuré]** 776 entrées `{enabled, id, label, menu, params, shortcut}`. Familles : layer 191, filter 122, edit 75, image 64, type 56, file 48, select 31, view 23, channel 21, paint 18, layerComp 13, brush 12, gradient 11, pattern 10, shape 9, path 8, count 7, slice 7, timeline 7, plugin 5, style 5, tool 5, cloneSource 5, et quelques autres. 671 entrées ont `enabled:false`.
- Origine : créé par 5331c8f3 (t138, 08/10). Plan P3 `:107` : « copie octet pour octet de `scratchpad/t138/commands.json` ; vérifier qu'il contient 776 entrées ». C'est la sortie de la méthode `engine.commands` de `serve` (plan P3 `:21`). **[supposé]** Elle a été capturée sans document ouvert. Aucun script de régénération n'est dans le dépôt.
- Il est lu par `faux_photocraft.py:77-80` (`engine.commands` du faux moteur), par les bancs `test_photolab_registre` (`:147-149` : `== 776`), `formulaires`, `libelles`, `moteur`, `peinture`, et par les QA node `affichage`, `espaces`, `champs`.

### 4.6 Bancs
- `backend/tests/test_photolab_*.py` (29 bancs) : affichage, apercu, apropos, biblio, catalogue, ecran_api, envoi, espaces, fichier_mode, fidelite, formulaires, iacalque, installeur, lanceur, libelles, masques, mesure, moteur, natif, panneaux3, peinture, preferences, registre, reglages_moteur, routes, texte, textes, transformation, vendor.
  - Ceux qui ont une partie « vrai moteur » : fidelite, apercu, affichage, biblio, ecran_api, fichier_mode, formulaires, iacalque, masques, mesure, panneaux3, peinture, preferences, reglages_moteur, texte, transformation, natif, installeur.
  - Faux moteurs : `faux_photocraft.py`, `faux_natif.py`.
- `frontend/photolab/qa/*.test.mjs` : 35 bancs node (`run.mjs`).

### 4.7 Inventaire des points codés en dur pour 0.3.0 (ce que touchera une montée de version) [mesuré, `git grep`]
1. `photolab_moteur.py:25` `VERSION`. Il pilote `chemin_cli`, `photolab_natif.py:55`, `photolab_routes.py:108`, `:763` et `:833`.
2. `vendor/photocraft.json` en entier : nom d'archive, URL, taille, sha256, `dossier`, les 9 `fichiers` et leurs sha256, `fichiers_source`.
3. `vendor/NOTICE-photocraft.txt` : chemins `photocraft-0.3.0/...` et commit 60224d3.
4. `scripts/build-installer.ps1:234-235` : `vendor\photocraft-0.3.0`.
5. `scripts/guide/serve_guide.py:20` et `serve_guide_ia.py:27` : `vendor/photocraft-0.3.0`.
6. `scripts/vendor_photocraft.py` et `scripts/verifier_vendor.py` (docstrings, règle CRT « la 0.3.0 n'en dépend pas »).
7. `scripts/photocraft_catalogue.py:10-11` : `COMMIT_FR = "3d23a708c2"`, `BLOB_FR` ; la source « v0.3.0 » est écrite dans `menus.json:2-3`.
8. `backend/tests/photocraft_commandes_0.3.0.json` : le nom de fichier est référencé dans `faux_photocraft.py`, `test_photolab_registre` (776), `formulaires`, `libelles`, `moteur`, `peinture`, et `qa/affichage`, `qa/espaces`, `qa/champs`.
9. Bancs à valeurs figées :
   - `test_photolab_vendor.py:22-25` (version, tag, archive, taille) ;
   - `test_photolab_catalogue.py:21,23,45` (source v0.3.0, **765** lignes, commit 3d23a708c2 et blob 453fa2ad) ;
   - `test_photolab_routes.py:42` et `test_photolab_apropos.py:39` (« 0.3.0 ») ;
   - `test_photolab_installeur.py:134-159` et `test_photolab_moteur.py:61-64` (chemins `photocraft-0.3.0`) ;
   - `qa/apropos.test.mjs:14,41`.
10. Textes affichés :
    - `frontend/shared/i18n/photolab.json:91` (« Moteur photocraft 0.3.0 ») ;
    - `frontend/dist/shared/dz-i18n-dico.js` et `frontend/shared/dz-i18n-dico.js` (générés) ;
    - `mod-apropos.js:28` (repli `"0.3.0"`) ;
    - `ATTRIBUTION.md:3,5` ;
    - `backend/app/main.py:483` (commentaire).
11. Relevés implicites sur le comportement de 0.3.0, sans le numéro en dur mais à re-sonder :
    - `PROFILS_MODE`, `KINDS`, `CORRECTIONS_CHAMPS`, les SCHEMAS et validateurs t153-t160 ;
    - `ETATS_MOTEUR` (`mod-historique.js:36`) ;
    - les unités de `mod-peinture.js` ;
    - `mod-espaces` et `photolab_preferences` SCHEMA (noms des `prefs.get`) ;
    - les paliers de zoom de `mod-vue` ;
    - `menus.json` (765 lignes) ;
    - « `doc.render` rend toujours le composite », « `doc.inspect` ne rend pas les repères » (`mod-affichage`), les entrées désactivées par le moteur (`measurementLog.export`, `file.import.notes`) ;
    - la forme de `doc.inspect` qu'élague `elaguer_inspect`.

---

## 5. Lots de parité : faits et laissés de côté

**[mesuré]** Tous les lots L1-L10 (t151-t160) sont fusionnés sur main :
- #269 L1 ;
- #270 L2 ;
- #271 L3 ;
- #273 L4 ;
- #268 L5 ;
- #274 L6 ;
- #275 L7 ;
- #277 L8 ;
- #278 L9 ;
- #280 L10 ;
- plus #336 (t191, calque IA).

On passe de 284 éléments « bientôt » (spec, 08/10) à 93 aujourd'hui.

Passages explicites :
- **Bloqué moteur**
  - L5 `docs/superpowers/plans/2026-10-08-photolab-parite-l5-peinture.md:21` : « Pas de commande pour l'outil Pièce : il reste « bientôt » (Bloqué moteur). » et `:53` : « Pièce | reste « bientôt » | absente du moteur ». Les écarts liés aux clés absentes figurent en `:48` (`paint.bucket` sans Mode / Tous les calques) et en `:50` (`paint.spotHealing`).
  - L8 `…-l8-fichier-mode.md:54` : « Remplacer / Exporter le contenu | … le moteur ne lit ni n'écrit le contenu, et ne rend pas la transformation … | **Bloqué moteur** ».
  - L8 `:55` : « Lier de nouveau / Convertir en objet lié | … aucun lien vivant possible (moteur désactivé, Bibliothèque sans liens) | **Bloqué moteur** ».
  - L8 `:57-58` : « Restent « bientôt » : Ouvrir en tant que (écarté, `refuse:file.`) et les 4 commandes de contenu d'objet dynamique (bloquées, `sans_ecran` : leur seul champ est un chemin). »
- **Désactivé par le moteur, contourné par le pont** : L10 `…-l10-mesure.md`, section « Sondes » : « **`measurementLog.export` est désactivé par le moteur** (chemin ambiant) » et « **`file.import.notes` est désactivé par le moteur** (chemin ambiant) ». Contournement par `/mesures.csv` et `/notes/importer`.
- **Absent du moteur, fait à l'écran** : L7 `…-l7-masques-galerie.md:11` : « Sélectionner et masquer… (`select.selectAndMask`, absent du moteur → écran sur `select.refineEdge`) ».
- **Écarté par décision, sans lien avec le moteur** :
  - spec `…-bientot-inventaire.md:145` : Fenêtre › Organiser (19), « **Écarté** pour l'instant (un seul canevas) ».
  - spec `:147` : Format des pixels, épreuve CMJN (15), « **Écarté** (… reprendre si l'impression arrive) ».
  - spec `:156` : Automatisation, scripts, impression, vidéo, D9 (45), « **Écarté** ».
  - L2 `…-l2-affichage.md:40` : « Adapter le plan de travail, repères du plan de travail, maillage, épingles, aperçu du motif | **Écarté** ».
  - L2 `:41` : « … repères intelligents | restent « bientôt » ».
  - L4 `…-l4-transformation.md:25` : « Déformer (warp), Déformation de la marionnette | hors lot (warp : maillage ; marionnette : D9) ».
  - L1 `…-l1-espaces.md:27,93` : panneau Montage écarté (D9).
  - L9 `…-l9-preferences.md:60` : « Livrées : 24 sur 25 (Migrer reste « bientôt ») ».
  - L9 `:48` : « (gamut : le moteur n'a pas l'alerte) ». À noter : le registre 0.3.0 contient pourtant `view.gamutWarning`. **[supposé]** L'« alerte » visée est celle des préférences de la référence.
- **À revoir si le moteur change** : `photolab_registre.py:37` (cité au §4.2). Aucun autre passage « à rouvrir quand le moteur… » n'a été trouvé dans `docs/superpowers/plans/*photolab*` ni dans la spec (grep sur bloqué, absent du moteur, rouvrir, quand le moteur, nouvelle version, montée de version).

### À rouvrir si photocraft > 0.3.0 apporte… [supposé, liste de contrôle]
- un outil Pièce, `paint.patch` ou équivalent (1 outil) ;
- la lecture et l'écriture du contenu des objets dynamiques, ou des objets liés (4 entrées `sans_ecran`) ;
- des clés Mode / Tous les calques sur `paint.bucket` et `paint.spotHealing` ;
- des commandes moteur pour `view.proofSetup.custom|workingCmyk|internetStandardRgb|monitorRgb` (en partie composables dès aujourd'hui avec `view.proofSetup {profile}`) ;
- `measurementLog.export` et `file.import.notes` sans chemin ambiant ;
- un panneau Actions ou une automatisation (aujourd'hui écarté, D9) ;
- les commandes Warp, Puppet, Liquify (aujourd'hui D9 ou hors lot).
