# Photolab ↔ photocraft 0.10 : relevé des différences et décisions (20/10/2026)

**But.** Mettre à jour le Photolab d'après la dernière version de photocraft (https://github.com/storytold/photocraft,
main 3a896a5e du 19/10, dernière release **v0.10.0 du 18/10**) SANS écraser ce que le Photolab fait aujourd'hui :
on rend actives les fonctions qui ne marchent pas encore chez nous et que l'amont sait désormais faire.

Sources (annexes dans `photocraft-0.10/`) :
- `releve-photolab.md` : état réel de l'écran et du pont sur origin/main 8f2ff3f2 (scripts du skill parite-photolab) ;
- `bientot-2026-10-20.md` : les 93 éléments encore « bientôt », avec leur raison ;
- `releve-amont.md` : comparaison v0.3.0 → main (code, notes de version, issues) ;
- `commandes-diff-0.3.0-main.json` : ajouts, paramètres changés, release d'apparition ;
- `photocraft_commandes_main-reconstruit.json` : les 918 commandes de main, au format de notre JSON 0.3.0,
  reconstruites par `scripts/photocraft_releve/` (contrôle : 776/776 identiques sur v0.3.0). `enabled` est estimé.

Marques : [mesuré] code ou script ; [notes] notes de version ; [supposé] inférence.

## 1. Où en est le Photolab (moteur épinglé 0.3.0)

- Moteur `photocraft-cli 0.3.0` piloté en `serve` stdio par `backend/app/services/photolab_moteur.py` ;
  776 commandes dans `backend/tests/photocraft_commandes_0.3.0.json` ; 44 routes `/api/photolab`.
- Lots faits : P0-P5 (t135-t140), parité L1-L10 (t151-t160), calque IA (t191).
- **Reste « bientôt » : 93** [mesuré] sur 633 commandes de menus, 45 outils et 1 panneau :

| Raison | Nb | Contenu |
|---|---:|---|
| `refuse:file.` | 37 | export (10 : calques en fichiers, jeux de données, rendu vidéo…), automatisation (9), scripts (8), import (3), Ouvrir en tant que, Imprimer… |
| `refuse:window.` | 21 | 19 `window.arrange.*` (un seul canevas, écarté), panneaux Actions et Montage |
| `absent_moteur` | 21 | `view.proofSetup.*` (4), `view.pixelAspectRatio.*` (10), `fitArtboardOnScreen`, `patternPreview`, `view.show.{targetPath, artboardGuides, smartGuides, mesh, editPins}` |
| `D9` | 6 | Marionnette ×2, Camera Raw, Grand angle adaptatif, Fluidité, Point de fuite |
| `sans_ecran` | 4 | `layer.smartObjects.{relinkToFile, replaceContents, exportContents, convertToLinked}` (champ `path`) |
| autres | 4 | Migrer les préréglages, Filtre personnalisé, **outil Pièce** (bloqué moteur), **panneau Actions** |

- Ce que le Photolab fait LUI-MÊME et qu'aucune montée ne doit écraser [mesuré] : `TRAITES_PAR_ECRAN`
  (139 ids, `mod-menus.js:45-90`), espaces de travail (`/espaces`), préférences d'écran (18 sections, jamais
  `prefs.*`), raccourcis/menus, surcouches d'Affichage, Ctrl+T, Sélectionner et masquer (`select.refineEdge`),
  Galerie, Image › Mode sous liste blanche, Nuancier stocké côté Deepotus, gestes Fichier par les routes
  (jamais `file.*`), Bibliothèque/Envoyer vers, calque IA et détourage, journal CSV et import de notes
  composés par le pont, `ETATS_MOTEUR` de l'historique.
- Points codés en dur pour 0.3.0 : ~30 (liste complète : `releve-photolab.md` §4), dont `VERSION` du pont,
  `vendor/photocraft.json`, `NOTICE`, `build-installer.ps1:234`, `photocraft_catalogue.py` (fr.tsv au commit
  3d23a708c2), `verifier_vendor.py`, le nom du JSON de commandes lu par une douzaine de bancs et QA,
  les textes « 0.3.0 » de l'À propos et d'`ATTRIBUTION.md`. **Aucun script ne régénère le JSON des commandes.**

## 2. Ce que photocraft a ajouté depuis 0.3.0

Versions : 0.5.0 (08/10), 0.6.0, 0.7.0, 0.8.2, 0.9.0, **0.10.0 (18/10)**, puis main. 2 508 commits.

**Moteur** [mesuré] : 776 → 918 commandes ; **142 ajouts, 0 retrait, 0 renommage** (aucune commande 0.3.0 ne
disparaît : rien de ce que le Photolab appelle ne casse par son id). Par famille :

| Famille | Ajouts marquants |
|---|---|
| retouche (`paint.*`) | `patch` (Pièce), `contentAwareMove`, `patternStamp`, `redEye`, `remove`, symétrie de peinture (`setSymmetry`, `symmetryFromPath`, `symmetryDisable`) |
| sélection, recadrage | `select.magneticLasso`, `select.float/drop`, `select.loadLuminosity`, `image.perspectiveCrop`, Remplissage d'après le contenu au recadrage (`image.crop contentAware`) |
| tracés (`path.*`, +13) | ancres et poignées (`moveAnchors`, `moveHandle`, `bendSegment`, `convertPoint`, `addAnchor`, `deleteAnchor`), `path.transform`, tracé de détourage, copier/coller fond et contour |
| texte (`type.*`, +10) | masque de texte (`createSelection`), texte sur tracé (`attachToPath`/`detachFromPath`), taille ± , `hitTest`/`caret`/`navigate` |
| calques (`layer.*`, +24) | `removeBackground`, `mergeGroup`, `showOnly`, `toggleLockTransparency`, `setLabelColor`, `copyToDocument`, `new.frame`, `artboard.addBeside`, `new.backgroundFromLayer`, `rasterize.layerStyle`, `layerStyle.{replace, transferEffects, makeDefault}`, `layerMask.edit`, `smartObjects.{convertToLayers, updateChanged}`, `smartFilter.transfer`, `fill.*.set` |
| filtres, IA locale | `filter.render.relight`, `filter.other.colorToAlpha`, `image.detectFaces` ; **aucune IA générative** |
| actions (`actions.*`, +18, famille neuve) | enregistrer, rejouer, lister, éditer, conditions ; import/export `.atn` (0.9) ; `actions.load/save` avec `path` refusés en automation (passer `data`) |
| historique (`history.*`, +9) | annuler/rétablir, instantanés, sélection d'état, nouveau document depuis un état |
| nuancier (`swatches.*`, +12) | nuancier du moteur, import/export .aco/.ase |
| préréglages | `document.presets.*`, `document.recent.*`, `file.export.presets.*`, `brush.presets.{update, setCurrent, importImage}`, `gradient.presets.stop` |
| affichage | `view.colorSamplers.*` (échantillonneur de couleur), `view.editGuide`, origine des règles |
| transformation | `edit.transform.warpGrid` (Déformation) |
| fichiers | `file.exrParts`/`openExrParts`, imprimantes, `edit.installedProfiles` |

**Protocole `serve`** [mesuré] : enveloppe inchangée, erreurs toujours en chaînes. Ajouts : `doc.place`,
`doc.exportLayers`, `doc.exportDataSets`, `doc.importDataSets` (0.8.2) ; `engine.commands` gagne
`disabledReason`, `needsDocument`, `keywords`. **Changements de comportement à absorber** :
- `doc.save` (0.9) rattache et marque propre aussi PSD/PSB/ORA, et restaure le document actif (contredit
  l'hypothèse t139) ;
- un `index` invalide est une erreur (0.9) au lieu du document actif ;
- `ui.*` refuse les champs inconnus ; `--control` exige l'authentification sous 10 s (0.10) ;
- `layer.hideLayers/showLayers` refusent une clé inconnue ;
- pixels : espacement des outils de retouche, matte de Save for Web, interpolation bicubique de Ctrl+T/Warp,
  Niveaux, Postériser, Luminosité/Contraste, CMJN/Lab, Courbe de transfert de dégradé recalés sur Photoshop
  → **nos bancs de fidélité figés doivent être régénérés** (comparaison au CLI 0.10 lui-même, règle D1).

**Formats** [mesuré/notes] — ouverture : HEIC/HEIF, Affinity, Paint.NET, ORA, Krita (calques), EXR multi-parties,
DPX, DDS, raws en plus ; enregistrement : TIFF à calques, WebP avec pertes, ORA, TGA 32 bits, DPX, CMJN TIFF/JPEG,
**PDF d'une page**. Toujours ni AVIF ni PDF en ouverture.

**Interface amont (shell egui)** : outils 43 → 67 (Lasso magnétique, Pièce, Déplacement basé sur le contenu,
Mélangeur, Texte vertical, Sélection directe, Tampon de motif, Œil rouge, Rotation de la vue, Supprimer,
Rectangle 1 rangée / 1 colonne, Plan de travail, Recadrage de perspective, Échantillonneur, Remplacement de
couleur, Plume libre et de courbure, Ajout/Suppression/Conversion de point, Masques de texte H/V, Cadre) ;
mêmes 32 panneaux et 10 espaces ; menus 627 → 632 ; **`fr.tsv` livré** dans v0.10.0
(`crates/ui-egui/src/i18n/fr.tsv`, 3 218 lignes, MIT OR Apache-2.0).

**Paquet Windows** : `photocraft-0.10.0-windows-x64-portable.zip`, 84 828 713 octets, `SHA256SUMS.txt` dans la
release ; toujours aucune DLL ni VC++ (lien statique). Nouvelles attributions à reporter (traductions,
`rgb.txt` X11, poids libfacedetection, icônes dont une Noun Project).

**Risques amont** (D) : écriture PSD encore non fiable pour Photoshop (#1281, #6968, #7698) ; 1 688 issues
dont 62 critiques ; `run --out`/`convert` écrasent l'entrée (#7437, nous n'utilisons que `serve`) ;
`doc.place`/`exportLayers` laissent le document indexé actif (#7025) ; `quality` flottante ignorée (#7023) ;
≈ 790 Mio pour 12 Mpx en headless (#1637).

## 3. Croisement : ce qui peut maintenant marcher chez nous

| Chez nous aujourd'hui | Ce que 0.10 apporte | Décision |
|---|---|---|
| Outil **Pièce** « bientôt » (bloqué moteur) | `paint.patch` | **Activer** (M3) |
| Panneau **Actions** « bientôt » (D9) | `actions.*` complet, `.atn`, `batch --action` | **Question Q1** : rouvrir D9 pour Actions (pas les scripts) |
| 4 objets dynamiques `sans_ecran` | `convertToLayers`, `updateChanged` ; `editContents` autorisé ; `replace/export/relink` toujours par `path` | Activer ce qui ne prend pas de chemin ; les 4 restants par un fichier de la Bibliothèque copié sous la racine (M7) |
| `file.export` (10) refusés | `doc.exportLayers`, `doc.exportDataSets` (méthodes `serve` bornées aux racines) | Calques en fichiers et jeux de données vers la Bibliothèque (M8) |
| Ctrl+T sans Déformation (hors lot L4) | `edit.transform.warpGrid` | Ajouter le mode Déformation (M7) |
| Pot de peinture / Correcteur localisé sans Mode ni Tous les calques (L5) | à revérifier dans les params 0.10 (186 commandes aux params enrichis) | Activer les clés si présentes (M3) |
| Nuancier stocké chez Deepotus | `swatches.*` | **Garder le nôtre** ; ajouter import/export .aco/.ase par `data` (M7) |
| Historique : `ETATS_MOTEUR` relevés à la main | `history.*`, instantanés | Instantanés et Nouveau document depuis l'état ; régénérer `ETATS_MOTEUR` (M7) |
| Détourage du calque IA (fal, payant) | `layer.removeBackground` local, gratuit | **Ajouter** une option locale à côté, sans retirer la nôtre (M7) |
| 45 outils | 24 outils de plus côté amont | Ajouter ceux qui ont une commande moteur (M3-M5) |
| Libellés FR maison (412) | `fr.tsv` amont | Dictionnaire de **repli** seulement ; nos libellés restent prioritaires (M9) |
| Ouverture/enregistrement PSD, PNG, JPEG, .pcraft… | HEIC, ORA, Krita, Affinity, PDN, EXR, DPX, DDS ; PDF, TIFF calques, WebP | Liste blanche d'extensions élargie, par la Bibliothèque (M8) |
| `view.*` absents (21), `window.arrange.*`, D9 interactifs (Fluidité, Marionnette, Point de fuite, Camera Raw) | toujours shell-only ou sans commande | **Inchangés** (restent « bientôt ») — Q2 pour les D9 |

## 4. Règles de la mise à jour (garde « ne rien écraser »)

1. **Une montée de moteur d'abord, seule** (M1-M2), avant toute fonction neuve ; épingler **v0.10.0** (release
   signée par SHA256SUMS), jamais main.
2. **Banc de non-régression d'écran** : instantané des états des 633 entrées, 45 outils et panneaux AVANT la
   montée ; après, aucune entrée active ne repasse « bientôt » ou inactive, aucun id de `TRAITES_PAR_ECRAN`
   n'est envoyé au moteur, les 18 préférences d'écran restent hors `prefs.*`.
3. Toute fonction déjà faite chez nous garde son module ; l'apport amont s'ajoute en option ou en repli,
   jamais en remplacement silencieux.
4. Régénérer les bancs figés en comparant au CLI 0.10 lui-même (D1) et consigner chaque écart de pixels.
5. Le téléchargement du binaire (≈ 85 Mo) se fait avec l'accord explicite de l'utilisateur, en début de M1.

## 5. Questions à trancher

- **Q1** — Rouvrir le panneau **Actions** (enregistrer/rejouer/.atn, sans scripts ExtendScript ni droplets) ?
  Proposition : oui, en M6.
- **Q2** — Les interactifs D9 (Fluidité, Marionnette, Point de fuite, Camera Raw) restent écartés ; le moteur
  sait les APPLIQUER mais l'édition est dans le shell egui. Proposition : les laisser, ou les ouvrir par le
  repli « app native » (déjà en place) — à décider plus tard.
- **Q3** — Formats : activer HEIC (décodeur pur Rust, HEVC soumis à brevets selon le pays) ? Proposition : non par
  défaut, oui pour les autres formats.
