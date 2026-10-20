# photocraft : écart v0.3.0 → main (3a896a5e, 19/10/2026)

Relevé en lecture seule. Clones superficiels de `v0.3.0` et de `main` (3a896a5e), plus des clones partiels (sparse) des tags `v0.5.0`, `v0.6.0`, `v0.7.0`, `v0.8.2`, `v0.9.0` et `v0.10.0` pour dater chaque changement. Aucun build, aucun binaire, aucun script du dépôt n'a été lancé.

Légende : **[mesuré]** = lu ou calculé dans le code source ; **[notes]** = lu dans les notes de version ou la ROADMAP ; **[doc]** = lu dans `docs/*.md` du dépôt ; **[GitHub]** = API issues, état au 20/10.

Livrables dans `amont\` :
- `photocraft_commandes_main.json` : registre complet de main, au format de notre `photocraft_commandes_0.3.0.json` (918 commandes).
- `commandes-diff.json` : `ajoutes`, `retires`, `renommes`, `params_changes` (avant/après, release du changement, clés ajoutées ou retirées), `labels_changes`, `menus_changes`, `raccourcis_changes` et `totaux` par release.
- Les outils (mini-expanseur de macros Rust en Python, hors dépôt) sont dans `scratchpad\outils\` : `extraire_cmds.py`, `produire.py`, `diff.py`. Il y a aussi `cmds_<tag>.json`, la liste reconstruite pour chaque tag.

---

## A. Commandes moteur

### Où est le registre
- `crates/engine/src/commands.rs` : `CommandSpec {id, label, menu, shortcut, params, enabled, run, journal}`, avec `build()` qui concatène `v.extend(crate::<module>::specs())` sur environ 80 modules `*_cmds.rs`. **[mesuré]**
- Les déclarations passent par des macros locales `spec!` (33 variantes), `cmd!`, `filter_cmd!`, `style_cmd!`, `stack_spec!`, `key_cmd!` et `gallery_specs!`, ou par des littéraux `CommandSpec {…}`. Il y a aussi des cas dynamiques :
  - la boucle `ADJ` génère `layer.newAdjustmentLayer.*` et `image.adjustments.*` ;
  - l'enum `GalleryFilter` (`crates/algo/src/artistic.rs`) génère `filter.gallery.*` ;
  - des `Box::leak(format!(…))` construisent certains params ;
  - des fonctions ou fermetures d'aide (`size_key`, `let spec = |…| CommandSpec{…}`) servent dans main. **[mesuré]**
- `engine.commands` (serve) appelle `Headless::command_list`, qui renvoie `command_specs()` dans l'ordre du registre. **[mesuré]**

### Comment j'ai reconstruit la liste de main (et sa fiabilité)
Sans compiler, un expanseur statique fait les opérations suivantes :
1. lexer Rust ;
2. expansion des `macro_rules!` du fichier ;
3. évaluation de `concat!`, `format!`, des `const` et `let` locaux, et de `Box::leak` ;
4. cas spéciaux pour la boucle `ADJ`, `GalleryFilter` et les fonctions d'aide ;
5. exclusion du code `#[cfg(test)]` (par exemple `test.panic`) ;
6. ordre reconstitué en suivant l'arbre des `specs()` depuis `build()`.

**Validation sur v0.3.0** : la liste reconstruite est **identique entrée par entrée, ordre compris, à notre JSON d'exécution (776/776)**. Cela vaut pour `id`, `label`, `menu`, `shortcut` et `params`, et même pour `enabled` grâce à la règle ci-dessous. Sur main, les 918 entrées sont résolues, sans aucune expression non évaluée.

Limites :
- `enabled` dépend de l'état de la session. Je l'ai déduit du nom de la garde : `always`, `native`, `has_pattern`, `has_swatches`, `has_groups` et les fermetures `|_| Ok(())` donnent `true` sans document ; tout le reste donne `false`. Cette règle reproduit exactement les 105 `true` de v0.3.0. Sur main, elle donne 162 `true`. C'est probable, mais non vérifié à l'exécution.
- Le vrai `engine.commands` de main ajoute en plus `disabledReason`, `needsDocument` et `keywords` (voir B). Ces champs ne sont **pas** dans notre format, donc pas dans le fichier.
- Lancer `photocraft-cli serve` 0.10.0 ne sert qu'à confirmer : il suffit de comparer son `engine.commands` à ce fichier.

### Totaux par release [mesuré]
| v0.3.0 | v0.5.0 | v0.6.0 | v0.7.0 | v0.8.2 | v0.9.0 | v0.10.0 | main |
|---|---|---|---|---|---|---|---|
| 776 | 817 | 851 | 858 | 892 | 909 | 918 | 918 |

- **Ajoutés : 142.** Retirés : **0**. Renommés : **0**. Aucun libellé de menu ni chemin de menu n'a disparu.
- Le changement est **strictement additif** pour les ids. Un pont écrit pour 0.3.0 ne perd aucune commande.
- 1 libellé a changé : `select.convertToShape` passe de « Convert Selection to Shape » à « Convert to Shape ».
- 1 raccourci a été ajouté : `edit.preferences.general`, Cmd+K.
- Les ajouts par release sont : 0.5 = 41, 0.6 = 34, 0.7 = 7, 0.8.2 = 34, 0.9 = 17, 0.10 = 9, main après 0.10 = 0.

### Résumé par famille [mesuré]
| famille | 0.3.0 | main | ajoutés | params modifiés |
|---|---|---|---|---|
| layer | 191 | 215 | 24 | 54 |
| filter | 122 | 124 | 2 | 4 |
| edit | 75 | 79 | 4 | 33 |
| image | 64 | 66 | 2 | 6 |
| type | 56 | 66 | 10 | 24 |
| file | 48 | 58 | 10 | 17 |
| select | 31 | 35 | 4 | 11 |
| view | 23 | 31 | 8 | 4 |
| paint | 18 | 26 | 8 | 16 |
| path | 8 | 21 | 13 | 1 |
| actions | 0 | 18 | 18 | 0 |
| swatches | 0 | 12 | 12 | 0 |
| history | 0 | 9 | 9 | 0 |
| document | 3 | 11 | 8 | 0 |
| brush / tools / channel / gradient | 12 / 4 / 21 / 11 | 15 / 9 / 22 / 12 | 3 / 5 / 1 / 1 | 6 / 1 / 1 / 1 |
| autres (layerComp, pattern, shape, timeline, slice, count, style, cloneSource, plugin, tool, notes, prefs…) | — | — | 0 | quelques-uns |

Ajouts par famille, avec la release d'apparition entre parenthèses :
- **layer (24)** : `copyToDocument`, `layerStyle.defaultFor/makeDefault/replace`, `removeBackground`, `showOnly` et `smartObjects.convertToLayers` (0.5) ; `fill.solidColor.set`, `layerStyle.transferEffects`, `setEffectsVisible`, `setLabelColor` et `toggleMaskOverlay` (0.6) ; `layerMask.edit`, `new.backgroundFromLayer` et `rasterize.layerStyle` (0.7) ; `artboard.addBeside`, `fill.pattern.set`, `mergeGroup`, `new.frame`, `selectInRect`, `smartObjects.updateChanged` et `toggleLockTransparency` (0.8.2) ; `smartFilter.transfer` (0.9) ; `list` (0.10).
- **actions (18)** : `record/stop/play/list/get/delete` (0.5) ; `move` (0.6) ; `rename` (0.7) ; `toggle` (0.8.2) ; `load/save` (.atn), `insert`, `conditional`, `dialog`, `assignSet`, `photoshopStep` et `stopMessage` (0.9) ; `setColor` (0.10).
- **path (13)** : `moveAnchors`, `moveHandle`, `bendSegment`, `convertPoint`, `transform`, `clippingPath.set/clear` et `style.copy/pasteFill/Stroke` (0.5) ; `addAnchor` et `deleteAnchor` (0.8.2).
- **swatches (12)**, tous en 0.6 : `list`, `add`, `delete`, `rename`, `move`, `use`, `reset`, `import`, `export`, `newGroup`, `renameGroup` et `deleteGroup`.
- **type (10)** : `hitTest`, `caret` et `navigate` (0.5) ; `createSelection` (masque de texte) et `increase/decreaseSize(More)` (0.8.2) ; `attachToPath` et `detachFromPath` (0.9).
- **file (10)** : `revealInFinder` (0.6) ; `exrParts` et `openExrParts` (0.7) ; `print.page`, `print.printers` et `printers` (0.9) ; `export.presets.list/get/save/delete` (0.10).
- **history (9)** : `deleteState` et `newDocument` (0.6) ; `undo`, `redo` et `new/rename/select/deleteSnapshot` (0.8.2) ; `selectState` (0.9).
- **document (8)** : `move` (0.5) ; `presets.list/get/save/delete` et `sampleColor` (0.6) ; `recent.list/add` (0.8.2).
- **paint (8)** : `patch`, `contentAwareMove`, `symmetryFromPath` et `symmetryDisable` (0.5) ; `patternStamp`, `redEye` et `setSymmetry` (0.6) ; `remove` (0.7).
- **view (8)** : `colorSamplers.add/move/delete/clear/list` (0.8.2) ; `setRulerOrigin` et `resetRulerOrigin` (0.9) ; `editGuide` (0.10).
- **tools (5)** : `increase/decreaseBrushSize/Hardness` (0.5) ; `rotateBrush` (0.8.2).
- **select (4)** : `float`, `drop` et `magneticLasso` (0.5) ; `loadLuminosity` (0.8.2).
- **edit (4)** : `transform.warpGrid` (0.5) ; `deleteAndFillSelection` (0.6) ; `fillHistory` et `installedProfiles` (0.8.2).
- **brush (3)** : `presets.setCurrent` et `presets.update` (0.6) ; `presets.importImage` (0.10).
- **filter (2)** : `render.relight` (0.5) ; `other.colorToAlpha` (0.6).
- **image (2)** : `perspectiveCrop` (0.8.2) ; `detectFaces` (0.10).
- **channel (1)** : `target.layerMask` (0.8.2).
- **gradient (1)** : `presets.stop` (0.6).

### Paramètres modifiés : 186 commandes [mesuré]
Les modifications ont été mesurées sur la chaîne `params` (doc lisible), pas sur un schéma.
- 110 modifications sont additives (nouvelles clés).
- 75 ne touchent que le texte, une plage ou une valeur par défaut documentée.
- 1 seule fait disparaître des clés de la doc : `select.convertToShape` perd `fill` et `name` (0.9). Le code les accepte toujours (`selection_to_shape` les relaie) ; seule la doc les a perdues, et `tolerance` est désormais bornée à 0.5..10.

Changements de comportement à surveiller pour un pont 0.3.0 :
- `paint.cloneStamp`, `healingBrush`, `spotHealing`, `dodge`, `burn`, `sponge`, `blur`, `sharpen`, `smudge` et `historyBrush` (0.5) : la valeur par défaut de `spacing` passe de `25` à « l'espacement des Réglages de forme », et `size` est bornée à 1..5000. **Le rendu peut différer à paramètres implicites égaux.** `paint.cloneStamp` ne documente plus de retour `{"damage"}`.
- `file.export.saveForWebLegacy` : la valeur par défaut de `matte` passe de `#ffffff` à `none` (0.9, #4115), et celle de `metadata` change.
- `file.export.colorLookupTables` : la plage de `size` passe de 2..256 à 2..129 (0.6).
- `layer.pickAt` : `list` renvoie désormais les calques **visibles** au point, et non plus « tout calque ayant des pixels » (0.9).
- `gradient.presets.apply` : la plage de `scale` passe de 10..150 à 1..1000 (main).
- Ajouts de valeurs, sans rupture :
  - `file.new` : alias `grayscale`, bornes explicites et arrondi des tailles (0.6) ;
  - `image.imageSize` et `file.automate.fitImage` : nouveaux modes de rééchantillonnage `automatic`, `bicubicSmoother` et `bicubicSharper` ;
  - `layer.select` : mode `remove` et sélection par `name` ou `occurrence` (0.9) ;
  - `select.colorRange` : `skinTones` ;
  - `select.refineEdge` : sorties `newDocument` et `newDocumentWithMask` (0.8.2) ;
  - `channel.target` : `mask` et `vectorMask` ;
  - `path.stroke` : `tool` accepte 17 outils ;
  - `image.applyImage` : `layer` par nom.
- Validation stricte (main, `param_check.rs`) : `layer.hideLayers` et `layer.showLayers` **refusent une clé inconnue**. Les autres commandes l'ignorent encore. **[doc]**
- `document.inspect` / `doc.inspect` : uniquement des clés ajoutées (`snapshots`, `uuid`, `labelColor`, `hasVectorMask`, `vectorMaskEnabled`, `symmetry`, `instances`, `fileName`…), aucune retirée. **[mesuré, `inspect.rs`]**

---

## B. Protocole, CLI et paquets

### `photocraft-cli serve` (JSON par ligne)
L'enveloppe est inchangée :
- requête `{"id","method","params"}` ;
- réponse `{"id","ok","result"|"error"}` ;
- les erreurs restent des **chaînes**, avec les mêmes variantes `AutomationError` (`{0}`, `I/O: {0}`, `bridge:`, `app:`). Il n'y a pas de codes d'erreur numériques. **[mesuré]**

| Changement | Release | Impact pour un pont 0.3.0 |
|---|---|---|
| Nouvelles méthodes `doc.place`, `doc.exportLayers`, `doc.exportDataSets` et `doc.importDataSets` (équivalents « capability-scoped » de `file.placeEmbedded`, `layersToFiles`, `dataSetsAsFiles` et `variableDataSets`, toujours refusés en automation) | 0.8.2 [mesuré] | additif |
| `engine.commands` : chaque ligne gagne `disabledReason` et `needsDocument` (0.8.2, #3664), plus `keywords` (0.10, #5060). Le filtre porte aussi sur `keywords`. | 0.8.2 / 0.10 [mesuré] | additif ; un parseur strict des clés casserait |
| `doc.save` : nouveaux `tiffLayers` et `tgaBits`. Depuis 0.9, une sauvegarde vers un format qui « contient tout le document » (PSD, PSB, .pcraft, ORA sans perte) **rattache le document à ce fichier et le marque propre**. En 0.3.0, seul `.pcraft` le faisait, et le document sauvé devenait actif ; désormais le document actif est **restauré**. Le message d'erreur sans `path` mentionne OpenRaster et la liste des pertes. | 0.5 → 0.9 [mesuré] | **comportement modifié** : vérifier nos hypothèses (t139 : « rattaché au fichier par chaque doc.save ») |
| `doc.open` : un modèle s'ouvre « Sans titre » sans chemin ; une source en lecture seule n'est pas rattachée ; `warnings` inclut les polices manquantes | 0.5 / 0.8.2 [mesuré] | additif ou bénin |
| `index` invalide (négatif, non entier) : **erreur** au lieu de retomber sur le document actif | 0.9 (#4160) [mesuré] | peut casser un appel laxiste |
| `actions.play` : chaque étape est réautorisée par `authorize_engine_step` | 0.5 [mesuré] | sécurité |
| Liste des commandes refusées en automation : `file.automate.cropAndStraightenPhotos`, `layer.smartObjects.editContents/convertToLayers/saveContents` et `image.applyDataSet` sont désormais autorisées. Nouveaux refus sur chemin ambiant : `actions.load/save`, `brush.presets.importAbr/importImage`, `gradient.presets.importGrd`, `plugin.install`, `plugin.reload`, `swatches.import/export` et `edit.keyboardShortcuts` (sauf en passant `data`). `edit.installedProfiles` est refusée. `file.export.renderVideo` passe par la racine d'écriture. | 0.5–0.10 [mesuré `workspace.rs`] | — |
| Chemins : un chemin **absolu** sous la racine est accepté (comparaison textuelle) ; avant, seuls les chemins relatifs l'étaient | 0.7 (#2176) [doc + notes] | assouplissement |
| Variables `PHOTOCRAFT_AUTOMATION_READ/WRITE_ROOT` : la doc de main précise qu'elles **ne valent pas** pour `serve` ni `mcp` ; il faut passer les drapeaux | doc main | nous passons déjà les drapeaux |
| Plafonds de transport : 1 Mio par requête, 8 Mio par réponse, 256 étapes par `batch`, aperçu ≤ 2048 px et 64 Mpx | inchangés | — |

Sous-commandes de `photocraft-cli` : toujours `convert`, `info`, `run`, `batch`, `droplet`, `commands`, `mcp` et `serve`, sans aucune suppression. **[mesuré]**
- `convert` et `run` gagnent `--tiff-layers`, `--tga-bits` et `--dpx-bits`.
- `batch` gagne `--action` et accepte les `.atn` ou un set Actions.
- Les drapeaux de `serve` sont inchangés : `--port`, `--control-token(-file)` et `--automation-read/write-root`.
- Le produit s'écrit désormais « PhotoCraft » dans le texte `USAGE`.

### Application `photocraft --control` (canal de contrôle)
- **Authentification dans les 10 s** après connexion, sinon fermeture (0.10, #4965). Un second `auth` répond `already authenticated`. **[notes + doc]**
- Fichier de jeton : un fichier lisible par le groupe ou les autres est **refusé**, mais seulement sur Unix (`#[cfg(unix)]`). Sur Windows, aucun contrôle d'ACL n'a été ajouté. **[mesuré `security.rs`]**
- Délai de réponse de 60 s. Les deux messages se distinguent : `timeout: not run` (renvoyable sans risque) et `timeout: no reply in 60s` (déjà lancé). Les connexions inactives sont fermées après 30 s. **[doc]**
- Méthodes `ui.*` : nombreux champs nouveaux dans `ui.set` (`rotation`, `colorPanel`, `brushPicker*`, `gradientBlendMode/Classic`, `shapeStroke`, `camTransformOnDrop`, `layerFilter`, `cropOverlay*`, `cropFill`, `cropShield`, `eyedropperSample*`, `strokeTrace`, `tileGrid`…). `ui.menu.invoke` accepte désormais `params`. Il y a de nouvelles boîtes de dialogue pilotables (`discard` pour l'invite d'enregistrement, `shell`, `newCropPreset`…). `ui.pointer` gagne `tool`. `ui.pointer`, `click`, `move`, `key` et `screenshot` **valident tout** : un champ inconnu devient une erreur (0.8.2, #2449). **[doc]**
- Langue : `prefs.set {"path":"interface.language","value":"fr"}` change la langue à chaud. **[doc]**
- Nouveaux drapeaux de l'exe : `--new-instance`, `--present-mode`, `--frame-latency`, `--stroke-trace`, `--in-window-menus`, `--safegpu`, `--help`, plus les variables d'environnement correspondantes. **[mesuré]**
- **Instance unique Windows/Linux** (0.10, #3708) : un lancement avec des fichiers est transmis à l'instance déjà ouverte, puis le processus se termine. Un lancement avec `--control` est **exclu** de ce mécanisme (`skip_reason`), donc notre `photolab_natif` n'est pas touché. En revanche, un photocraft.exe lancé sans `--control` (par exemple « Ouvrir dans photocraft ») rejoindrait l'instance de l'utilisateur. **[mesuré `single_instance.rs`]**
- Les sauvegardes de secours vont dans `%LOCALAPPDATA%\Photocraft\Recovery` et la géométrie dans `ui.ron` (0.10). En mode portable, rien ne s'écrit dans `%APPDATA%` ni `%LOCALAPPDATA%`. **[doc + `portable.txt`]**

### Archives Windows (`packaging/windows/package.ps1`, main) [mesuré]
- **`photocraft-<v>-windows-<arch>-portable.zip`** contient `photocraft.exe`, `photocraft-cli.exe`, `portable.txt`, `README.md`, `LICENSE-MIT`, `LICENSE-APACHE` (et `LICENSE` si présent), plus un `OFL-<famille>.txt` par police craft-fonts embarquée. Les builds officiels définissent `CRAFT_FONTS_DIR` ; le mécanisme existait déjà en 0.3.0.
- **Aucune DLL**. Liaison `+crt-static` : **pas de redistribuable VC++**, comme en 0.3.0.
- Seul ajout au build : `--features heif` sur les deux exe depuis 0.5.0. Il s'agit du décodeur HEVC pur Rust `heic-rs =0.1.4` (MIT/Apache). La doc de la crate signale que **HEVC est soumis à brevets selon les juridictions** : c'est une décision de distributeur.
- MSI : assistant WiX (UI et Util ext), dossier d'installation mémorisé dans `HKLM\Software\PhotoCraft\InstallDir`, ouverture proposée pour `.pdn`, `.ora`, `.kra` et `.krz`. Refus explicite de Windows 7 et 8 (0.8.2). Le contenu du zip portable n'a pas d'autre changement.
- Licences et NOTICE : NOTICE gagne 1 ligne. ATTRIBUTION ajoute :
  - les catalogues de traduction `crates/ui-egui/src/i18n/*.tsv` (MIT OR Apache-2.0, `LICENSE-translations.txt`) ;
  - la table X11 `rgb.txt` (MIT) ;
  - les poids **libfacedetection** (`crates/algo/data/libfacedetection.bin`) ;
  - la palette Solarized (MIT) ;
  - de nouvelles icônes (Lucide ISC, dérivées ou originales) ;
  - une icône « Magnetic Lasso » adaptée de Noun Project (Lil' Seal) : **à vérifier si nous embarquons les icônes de l'amont**.

---

## C. Fonctionnalités de l'interface et du moteur

### Mesures dans le code [mesuré]
- **Outils** (`enum Tool`, `ui-egui/src/state.rs`) : 43 en 0.3.0, 67 dans main. Ajouts :
  - 0.5 : MagneticLasso, Patch, ContentAwareMove, MixerBrush, VerticalType, DirectSelection ;
  - 0.6 : PatternStamp, RedEye, RotateView ;
  - 0.7 : Remove, Single Row et Single Column Marquee ;
  - 0.8.2 : Artboard, PerspectiveCrop, ColorSampler, ColorReplacement, Freeform et Curvature Pen, Add, Delete et Convert Point, type masks H et V, Frame ;
  - rien après 0.8.2.
  
  La ROADMAP compte 56/68 outils Photoshop au 11/10, et la doc de parité de main 59/68. **[notes/doc]**
- **Panneaux** : 32 entrées `window.panel.*` dans le catalogue de menus en 0.3.0 comme dans main. L'**ensemble est identique**, mais le contenu s'est approfondi (Actions, Nuancier, Historique avec instantanés, filtre du panneau Calques). La ROADMAP annonce 30/35. **[mesuré/notes]**
- **Espaces de travail** : les mêmes 10 entrées `window.workspace.*` (Essentials, Graphic & Web, Motion, Painting, Photography, Pixel Art, New, Delete, Reset, Lock). **[mesuré]**
- **Menus** : 627 → 632 ids dans `menu_catalog.rs`, soit +`file.openExrParts`, `layer.new.backgroundFromLayer`, `layer.rasterize.layerStyle`, `layer.smartObjects.convertToLayers` et `type.antiAlias.none`. La ROADMAP annonce 628/628, puis 631/631. **[mesuré]**
- Le shell egui est passé de **134 à 344 fichiers** dans `crates/ui-egui/src`. L'essentiel du travail est côté shell. **[mesuré]**
- **Localisation française** : `crates/ui-egui/src/i18n/fr.tsv` apparaît en **0.5.0** (2 566 lignes) et **existe dans le tag v0.10.0** (3 218 lignes ; main : 3 254, environ 3 194 entrées).
  - Format TSV `contexte<TAB>source anglaise<TAB>traduction`, avec 12 surcharges `@id` de commande.
  - Licence MIT OR Apache-2.0, traductions « clean-room ».
  - Le catalogue est compilé dans le binaire (`catalog!("fr")`, `complete_menus: true`).
  - C'est **purement du shell** : les messages du moteur et les `label` d'`engine.commands` restent en anglais.
  - Le fichier peut servir de **dictionnaire de libellés pour notre Photolab**, licence compatible, attribution à garder.
  - Autres langues ajoutées depuis 0.3.0 : de, fr, id, it, ko, pt-br (0.5), el, nl, pl, uk (0.6), hu, tr, vi (0.8.2), sr (0.9).

### Par domaine : moteur (pilotable par `serve`) ou shell seul
| Domaine | Nouveautés (release) | Moteur / shell |
|---|---|---|
| Formats en ouverture | HEIC/HEIF (0.5) ; Affinity .af/.afphoto/.afdesign/.afpub, SVG en calques de forme, Paint.NET .pdn, RAF Fuji, NEF compressé (0.6) ; OpenRaster .ora en lecture et écriture, EXR multi-parties et Cryptomatte, DNG avec pertes (0.7) ; Krita .kra en composite (0.8.2) puis avec calques (0.9), GIF animé en calques vidéo (0.8.2) ; DPX, DDS, Canon CR3 en aperçu seulement, RW2 compressé, `.xmp` Camera Raw (0.9) ; TIFF Lab, EXR ACEScg (0.10). **AVIF : toujours non (#463 ouvert). PDF en ouverture : non.** | moteur (`doc.open` ; `io`, `codecs`) |
| Formats en enregistrement | TIFF à calques (0.5), WebP avec pertes (VP8 pur Rust, 0.5), ORA (0.7), TGA 32 bits, DPX (0.9), CMYK TIFF et JPEG (0.9), **PDF d'une page aplatie avec ICC** (0.10, #3401) | moteur (`doc.save`, `convert`) |
| PSD | Nombreux correctifs d'interopérabilité et de sécurité ; oracle Photoshop 145 → 188 fichiers sur 256 (0.10) ; filtres dynamiques Camera Raw (0.5), Galerie de filtres éditable (0.10). **L'écriture n'est toujours pas fiable pour Photoshop** (ci-dessous). | moteur |
| Camera Raw | Histogramme, clipping et oscilloscopes (0.5) ; fenêtre dédiée, ouverture des raws d'abord dans Camera Raw (0.6) ; xmp (0.9) ; annuler/rétablir (0.10). La commande `filter.cameraRaw` existait déjà. | **commande moteur** pour l'application des réglages ; le dialogue, les scopes et l'invite à l'ouverture sont **shell** (`ui.menu.invoke params.ui`, desktop uniquement) |
| Liquify / Puppet / Warp / Perspective / Vanishing Point | Robustesse, Alt pour inverser (0.6), maillage qui suit le contour, éditeur de plans Vanishing Point à l'écran (0.8.2), bicubique façon Photoshop, warp en arrière-plan (0.9). Seule nouvelle commande : `edit.transform.warpGrid` (0.5). | moteur pour `filter.liquify`, `edit.puppetWarp`, `edit.perspectiveWarp` et `filter.vanishingPoint` ; l'édition interactive est **shell** |
| Select and Mask / sélections | Magnetic Lasso (0.5, `select.magneticLasso`) ; Color Range au modèle Photoshop (0.6), Skin Tones (0.9) ; Select and Mask : aperçu dans les modes de vue, Refine Edge Brush, sortie vers un nouveau document (0.8.2) ; Object Finder (0.9). `select.subject`, `sky` et `focusArea` existaient. | moteur pour `select.refineEdge` et les nouvelles sorties ; Refine Edge Brush et aperçu **shell** |
| Retouche | Patch, Content-Aware Move (0.5) ; Pattern Stamp, Red Eye (0.6) ; Remove (0.7) ; Content-Aware Fill au recadrage (0.10, `image.crop contentAware`) | **moteur** (`paint.patch`, `contentAwareMove`, `patternStamp`, `redEye`, `remove`) ; outils et transformation au dépôt côté shell |
| Texte | hitTest, caret, navigate (0.5) ; masque de texte, taille ± (0.8.2) ; texte sur tracé (0.9) ; Warp Text en direct ; traitement des polices manquantes | moteur pour `type.*` ; saisie en ligne shell |
| Formes / plume | Points d'ancrage et poignées : `path.*` (0.5, 0.8.2) ; Freeform, Curvature, Convert Point (0.8.2) ; contrainte à 45° (0.10) ; options de contour des formes (`ui.set shapeStroke`) | moteur pour `path.*` et `shape.*` ; les outils Plume sont shell |
| Actions / scripts | Actions enregistrables et rejouables (0.5), édition (0.6–0.8.2), **import/export Photoshop .atn** (0.9), mode Bouton, sous-dossiers en Batch (0.10). Scripts : ExtendScript **refusé** (0.10). | **moteur** (`actions.*`, `file.automate.batch`, CLI `batch --action`) ; panneau shell. `actions.load/save` avec `path` refusés en automation (passer `data`) |
| IA | Remove Background (0.5, `layer.removeBackground`), Relight (0.5, `filter.render.relight`), détection de visages libfacedetection (0.10, `image.detectFaces`). **Aucune IA générative.** La ROADMAP estime l'IA à 10 %. | moteur |
| Nuancier, préréglages | Nuancier .aco/.ase (0.6), préréglages de document (0.6), préréglages d'export (0.10), import de pointe depuis une image (0.10) | moteur (`swatches.*`, `document.presets.*`, `file.export.presets.*`) |
| Historique | Instantanés, sélection d'état, nouveau document depuis un état | moteur (`history.*`) |
| Préférences / interface | Mise en page Apparence/Présentation/Options (0.9), thèmes (Solarized, Breeze, Soft…), Assombrir/Éclaircir l'interface, menus dans la fenêtre, 168 réglages dont 26 inopérants (0.10) | **shell** (sauf `prefs.*`) |
| Impression | Liste des imprimantes Windows, GDI (0.9) | moteur pour `file.print*` (sauf `file.printers`, en violation d'accès sur une Windows Insider, #7123) ; dialogue shell |

---

## D. Ruptures et régressions connues qui comptent pour un intégrateur

### Écriture PSD [GitHub + ROADMAP]
L'écriture PSD reste le point noir. La ROADMAP indique que « PSDs we write are not yet reliably accepted by Photoshop ».
- Ouverts « critical » : #1281 (Photoshop 26.6 refuse de rouvrir), #6968 (`type.edit` produit des PSD qui **font planter Photoshop 27.10**), #7698 (PSD non ouvrable dans Photoshop 2021 et Photopea).
- Une vingtaine d'issues « high » liées au PSD. Les plus notables :
  - #4654 : padding Lr16, Unity refuse le fichier ;
  - #4814 : modes Indexé, Bitmap et Duotone non conservés ;
  - #7697 : en CMYK, le composite est reséparé ;
  - #6542 : un calque Light lu comme Luminosité/Contraste ;
  - #6774 : couleurs HSB perdues ;
  - #4085 : objets dynamiques non ouvrables ;
  - #6267 : filtres dynamiques non pris en charge supprimés.
- Le PSB de plus de 4 Go échoue sur Windows (#375, ouvert).

### Robustesse générale
- 1 688 issues ouvertes au 20/10, dont 62 « priority: critical », surtout des plantages au démarrage, au redimensionnement ou au collage.
- #7858 : sur Windows, une sauvegarde native revient à l'état précédent après une coupure de courant.
- #7223 : Image › Trim et Duplicate plantent au-delà de 2^30 px.
- #4804 (régression) : les images indexées s'ouvrent en RVB.

### CLI et headless
- **#7437 (critical)** : `run --out` et `convert` **écrasent silencieusement le fichier d'entrée**. Nous n'utilisons que `serve`, mais c'est à savoir.
- #7025 (high) : avec `index`, `doc.place`, `exportLayers`, `exportDataSets` et `importDataSets` **laissent ce document actif**, alors que `doc.save` restaure le document actif.
- #7023 : la `quality` de `doc.save` en flottant (`85.0`) ou en chaîne est **ignorée silencieusement** (WebP sans perte) ; 0 et 500 sont bornés.
- #1637 (high) : ouvrir, ajuster et exporter une photo de 12 Mpx en headless demande environ 790 Mio.

### Performances [ROADMAP + notes]
- 3 budgets de performance tenus sur 25, inchangés en 0.10.
- Plantage GPU à 150 calques mentionné dans la ROADMAP.
- Sur Windows, WARP est préféré à GL pour éviter une fenêtre noire (0.10).

### Valeurs par défaut modifiées sans changement d'id (voir A)
Ces changements peuvent modifier les pixels produits à paramètres implicites :
- l'espacement des outils de retouche et d'exposition (0.5) ;
- le `matte` par défaut de Save for Web (0.9) ;
- l'interpolation de Free Transform et Warp, bicubique Keys −0.75 (0.9) ;
- Niveaux, Postériser, Luminosité/Contraste et les compositions CMYK et Lab réalignés sur les oracles Photoshop (0.10) ;
- Gradient Map en luminosité W3C (0.10).

Il faut donc **regénérer nos bancs figés** en cas de montée de version.

### Bilan pour notre pont
1. **Rien n'est retiré ni renommé** : les 776 ids 0.3.0 existent toujours, avec la même étiquette (sauf 1) et le même menu.
2. Points à adapter :
   - `doc.save` rattache et marque propres aussi les PSD, PSB et ORA, et ne change plus le document actif ;
   - `index` est validé strictement ;
   - les lignes d'`engine.commands` ont 2 ou 3 clés de plus ;
   - le canal `--control` impose l'authentification en moins de 10 s ;
   - `ui.*` valide strictement ses champs ;
   - quelques valeurs par défaut de `params` ont changé.
3. Le paquet Windows ne gagne ni DLL ni prérequis. La seule nouveauté de dépendance est le décodeur HEIC (question de brevets HEVC). Le nouveau fichier `fr.tsv` (0.5+) est réutilisable sous MIT/Apache.
