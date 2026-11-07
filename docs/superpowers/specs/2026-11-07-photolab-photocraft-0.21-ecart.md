# Photolab ↔ photocraft 0.21 : relevé des différences et décisions (07/11/2026)

**But.** Monter le moteur du Photolab de photocraft 0.10.0 à **0.21.0** (release du 06/11, tag `v0.21.0`, commit
efb7ebd0c), sans rien retirer à l'écran, puis lister ce que la nouvelle version permet d'ajouter.

Marques : [mesuré] code, binaire ou banc ; [notes] notes de version ; [supposé] inférence.

## 1. Ce qui a été mesuré

| Point | Résultat |
|---|---|
| Versions couvertes | 0.11.1, 0.12, 0.13, 0.14, 0.15.1, 0.16, 0.17, 0.18, 0.19, 0.20.1, 0.20.2, 0.21.0 : 1 497 entrées de notes, 7 104 commits |
| Paquet Windows | `photocraft-0.21.0-windows-x64-portable.zip`, 134 361 814 o, sha256 `93b4e90a…`, recoupé avec SHA256SUMS.txt et le digest de l'API GitHub |
| Disque | 259 Mo contre 174 Mo pour la 0.10.0 (+85 Mo) ; `photocraft-cli.exe` passe de 76 à 117 Mo |
| Structure du zip | **à plat** depuis 0.18 (plus de dossier racine) ; 21 fichiers (13 OFL, ATTRIBUTION, NOTICE) ; aucun runtime Visual C++ |
| Commandes (`engine.commands` du vrai binaire) | 918 → **993** : **75 ajouts, 0 retrait**, 165 descriptions changées, 0 changement d'`enabled` |
| Écran (`test_photolab_non_regression`) | aucune entrée perdue sur le registre 0.21 |
| « Bientôt » | 105 entrées avant et après la montée |

## 2. Ruptures trouvées par les bancs sur le vrai moteur, et traitement

Bancs de départ sur 0.21 sans correction : 16 fichiers rouges, dont 2 déjà rouges sur 0.10 (`reglages_moteur` 3b, 3e :
fins de ligne d'un fichier témoin, hors lot).

| Rupture | Effet chez nous | Traitement |
|---|---|---|
| `layer.newFillLayer.*` **consomme la sélection** (0.21) | les vues de Sélectionner et masquer sortaient inversées ou vides | `_remplissage` reprend la sélection (`select.reselect`) |
| `edit.paste` **recale sur la toile** (`clampToCanvas` vrai par défaut, `center` ignoré) | image plus grande que la toile posée en haut à gauche (Placer, calque IA) | `clampToCanvas:false` dans `PM.placer` |
| 165 descriptions changées | la liste blanche suit le registre : des clés neuves s'ouvraient toutes seules et des champs existants devenaient illisibles (`"width":number`) | **gel** : `photolab_champs_geles.json` rend à 128 commandes leur lecture 0.10.0 exacte ; un lot ouvre une clé en retirant la commande |
| 75 commandes neuves | ouvertes par la seule montée | `COMMANDES_NEUVES_021`, fermées comme en 0.10 |
| Lecture d'une action = **un seul état** « Action: X » (0.21) | l'historique affichait le nom anglais | motif traduit ; **conservé** car c'est le comportement de référence |
| Recadrage qui agrandit : état « Content-aware Crop » | nom non traduit | clé ajoutée |
| Un document naît avec **un instantané de lui-même** (`history.options`, actif par défaut) | une ligne de plus dans l'Historique | conservé (comportement de référence) |
| `layer.new.frame` crée un vrai cadre (plus de masque de calque) | réponse enrichie | banc recalé |
| `edit.transform` rend `{layers, rect}` | aucun : l'écran ne lit que `rect` | banc recalé |
| `actions.list` rend aussi `sets` | aucun | banc recalé |
| Zip à plat | chemins des bancs et de la NOTICE | recalés ; le pont cherche le binaire par `rglob`, rien à changer |
| `doc.save` refuse une `quality` invalide (0.12), résolution hors 1..30000 refusée (0.21) | aucun rouge | — |

Défaut de `select.subject.sampleAllLayers` passé de vrai à faux en amont : le gel garde le défaut 0.10 dans le formulaire.

Non mesuré : les changements de rendu listés par les notes (Lumière tamisée, Blend If, Fill des huit modes spéciaux,
Dissolve, flou de pinceau, Dehaze, Reflet) ne font rougir aucun banc, mais nos bancs ne couvrent pas tous ces cas.

## 3. Ce que 0.21 permet maintenant (décision de l'utilisateur attendue)

Aucune de ces fonctions n'est ouverte par la montée.

| Lot | Contenu | Moteur | Taille |
|---|---|---|---|
| N1 Objets dynamiques | **Fait (t411)** : Remplacer le contenu, Exporter le contenu en PNG (composé : `editContents`, `doc.save`, `doc.close`). Écartés : Incorporer tous les liés (désactivé en automation), contenu SVG (la Bibliothèque ne reçoit pas de `.svg` ; Remplacer accepte une image, `updateSvg` n'apporte rien de plus) | `doc.replaceSmartObject` | S |
| N2 Texte | **Fait (t412)** : 20 jeux stylistiques et 9 styles de chiffres, cochés d'après le texte, Texte dans une forme (forme ou tracé de travail), polices favorites gardées par l'écran | `type.openType.*`, `type.fillPath` (`type.font.*` reste fermée : elle écrirait les préférences du moteur) | M |
| N3 Tracés et formes | **Fait (t413)** : opérations entre composants et fusion (menu des tracés), ajouter ou soustraire à la sélection, opération des outils de forme (nouveau calque ou composant du calque actif, ajouté au lot pour que les opérations servent), angles arrondis du triangle et du polygone, flèches du Trait | `path.setOperation`, `path.mergeShapeComponents`, `path.toSelection` (`mode`), `shape.create` / `shape.edit` | M |
| N4 Peinture | **Fait (t414)** : Mélangeur (Alt-clic pour charger, Charger et Nettoyer, options après le trait), outil Forme d'art d'historique avec son icône, source de l'historique dans le panneau, pinceau précédent / suivant (`,` `.`, Maj : premier / dernier). Restent fermés : `brush.mixer.sample`, `mixerState` | `paint.mixerLoad`, `brush.mixer.*`, `paint.artHistoryBrush`, `history.setSource`, `tools.*Brush` | M |
| N5 Historique et Actions | **Fait (t415)** : Effacer l'historique, Options d'historique, regroupement d'une lecture en un état (Options de lecture), options gardées et reposées à chaque démarrage du moteur. Écartés : Pas en avant / arrière (doublent Annuler / Rétablir), Nouveau jeu au moteur (ni suppression ni renommage d'un jeu vide : les jeux vides restent à l'écran), rythme de lecture (sans effet hors de l'app native), historique non linéaire (contredit le panneau) | `history.clear`, `history.options`, `actions.setHistory` | S |
| N6 Bibliothèques | **Fait (t416)** : import `.asl` et `.csh` depuis les panneaux Styles et Formes, export `.asl` d'un groupe, fichiers importés gardés et rejoués à chaque démarrage du moteur. Écartés : contours utilisateur (aucun champ Contour au dialogue Style de calque) | `style.presets.importAsl`, `exportAsl`, `shape.presets.importCsh` (par `/bibliotheques/*`, en `data`) | M |
| N7 Cadres | **Fait (t417)** : sous-menu Calque › Cadre (Propriétés, Remplacer le contenu, Ajuster le contenu au cadre, Ajuster le cadre au contenu, Convertir en cadre) ; un cadre vide est signalé avant le moteur | `layer.frame.*` | M |
| N8 Formats et exports | **Fait (t418)** : ouverture de XCF, DICOM, IFF, FITS, HDR, Cineon, QOI, PCX, XPM, ICO, Netpbm ; export JPEG XL sans perte, DDS, OpenEXR, DPX, Cineon, HDR, BMP, GIF, QOI ; compression TIFF et DDS. Le PDF porte déjà ses polices (`/Font`, `/ToUnicode`). JPEG XL et HEIC restent fermés à l'ouverture (moteur, brevets) | `doc.save` et ses options | M |
| N9 Longues opérations | **Fait (t419)** : filtres, Remplissage et Mise à l'échelle d'après le contenu en tâche de fond ; barre après 400 ms, Annuler ou Échap, image intacte en cas d'annulation ou d'échec. Le délai de 60 s du pont ne coupe plus un filtre long | `wait:false`, `jobs.list`, `jobs.cancel` | M |
| N10 Rendu GPU | **Écarté (t420) après mesure** : 6 pixels sur 1,92 million diffèrent de ±1 sous `--gpu` (document de 10 calques), export compris, donc plus d'identité à l'octet ; gain de 20 à 25 ms par rendu jusqu'à 2048 px, nul au-delà (aperçu réduit, composé par le CPU) ; premier rendu plus lent d'environ 1 s (RTX 2080 Ti) | `serve --gpu` | S |

Hors lots : `file.approveMemory` (sans objet en `serve` : `approveHighMemory` à l'ouverture suffit, à sonder sur un gros
PSD), `help.checkForUpdates` / `updates.status` (le moteur est épinglé, jamais mis à jour seul ; le mode headless répond
`supported:false`), `layer.xmpMetadata`, `layerComp.reorder`.

Toujours sans issue : les fonctions à interface interactive (Fluidité, Marionnette, Point de fuite, Camera Raw, D9),
`window.arrange.*` (un seul canevas), `view.*` absents, commandes à chemin ambiant hors de `doc.*`. Les modèles locaux
de matting et de sélection d'objet (0.17) ne sont pas dans le zip sous forme de fichiers séparés [mesuré] ; leur
installation reste à relire avant tout usage.

## 4. Règles gardées

- Une montée seule d'abord, sans aucune fonction neuve : les bancs et l'écran de non-régression en sont la preuve.
- `TRAITES_PAR_ECRAN` et les Préférences d'écran ne bougent pas.
- 0.10.0 reste sur le poste après l'installation tant que l'utilisateur ne décide pas de la retirer ; `build-installer`
  ne livre que la version épinglée.
