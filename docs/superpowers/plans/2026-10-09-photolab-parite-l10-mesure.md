# Photolab parité L10 (t160) : mesure, comptage, notes, tranches

Base : `main` 3f939739. Branche `chantier/photolab-parite-l10`. Skill `parite-photolab`. Source : relevé
`specs/2026-10-08-photolab-bientot-inventaire.md` (lot 10).

## Périmètre (recensé par `lister_bientot.mjs`, 105 « bientôt » au départ)

12 éléments : outils Règle, Note, Comptage, Tranche, Sélection de tranche ; Fenêtre › Journal des mesures, Fenêtre ›
Notes ; Affichage › Afficher › Compteur, Notes, Tranches ; Affichage › Aimanter à › Tranches ; Fichier › Importer ›
Notes…. (Le suivi en comptait 7 ; les 4 entrées d'Affichage et l'import de notes vont avec.)

## Sondes du vrai moteur (copie portable, jamais l'installé)

- Règle : `image.analysis.rulerTool {start, end, protractor?}` rend `info {x, y, w, h, angle, l1, l2, length, units}` ;
  lecture sans paramètre ; `clear`. PAS d'étape d'historique ; propre à chaque document. `straightenLayer` -> « Straighten ».
- Comptage : `count.add|move|remove|clear|newGroup|deleteGroup|setGroup` rendent l'état complet (`groups` : couleur
  0..1, `points`, `markerSize` 1..10, `labelSize` 8..72, `visible`, `activeGroup`). Étapes « Count » (ajout, déplacement,
  retrait), « Clear Count », « New Count Group », « Delete Count Group », « Count Group Options ».
- Notes : `notes.add|set|delete|list` (index, auteur, texte, couleur, position, ouverte). Étapes « New Note »,
  « Edit Note », « Move Note », « Delete Note ». `doc.inspect.notes` ne rend ni couleur ni index : on lit `notes.list`.
- Tranches : `slice.new` (rect ou x/y/width/height + options), `slice.set` (rect admis), `divide`, `promote`, `delete`,
  `fromGuides`, `layer.newLayerBasedSlice`, `view.clearSlices`, `view.lockSlices` (verrouillées : `slice.new` refusé
  « slices are locked »). `slice.list` rend aussi les tranches AUTOMATIQUES (origin auto, id null). Étapes « Slice »,
  « Slice Options », « Divide Slice », « Promote to User Slice », « Delete Slice », « Slices From Guides »,
  « New Layer Based Slice », « Clear Slices ».
- Journal des mesures : `image.analysis.recordMeasurements {source}` ajoute des lignes ; `measurementLog.list|delete` ;
  le journal est celui de la SESSION (un autre document le voit), sans étape. **`measurementLog.export` est désactivé
  par le moteur** (chemin ambiant), même sans `path`.
- **`file.import.notes` est désactivé par le moteur** (chemin ambiant).

## Tableau chez eux / chez nous / décision

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Règle | glisser = ligne, Alt depuis une extrémité = rapporteur, Maj = 45°, barre X Y L A L1 L2, Redresser le calque, Effacer | les mêmes gestes ; la barre lit `rulerTool` (unités de l'échelle de mesure) ; Redresser (`straightenLayer`), Effacer | **Repris** |
| Comptage | clic = marque numérotée, Alt-clic = retire, glisser une marque = déplace ; groupes (nom, couleur, taille des marques et des numéros, visibilité), Effacer | les mêmes ; marques dessinées par l'écran d'après `countTool` | **Repris** |
| Note | clic = note, glisser l'icône = déplacer ; barre Auteur, Couleur, Tout effacer, panneau Notes | les mêmes ; l'auteur est retenu par navigateur | **Repris** |
| Panneau Notes | texte de la note choisie, précédente / suivante, supprimer | le même ; le texte s'enregistre à la sortie du champ (`notes.set`) | **Repris** |
| Tranche | glisser = tranche utilisateur (Maj carré), Tranches d'après les repères | les mêmes ; `slice.new`, `slice.fromGuides` | **Repris** |
| Sélection de tranche | clic choisit, glisser déplace, poignées redimensionnent, Suppr supprime, double clic = Options (nom, type, URL, cible, message, alt, fond), Diviser, Promouvoir | les mêmes (`slice.set` rect et options, `delete`, `divide`, `promote`) | **Repris** |
| Journal des mesures | tableau, Enregistrer les mesures, sélection de lignes, supprimer, exporter | tableau des colonnes choisies (`selectDataPoints`), Enregistrer (`recordMeasurements`), supprimer les lignes choisies, Tout effacer ; **export CSV composé par le pont** depuis `measurementLog.list` (téléchargement) | **Adapté** (export) |
| Affichage › Compteur / Notes / Tranches | montrer ou cacher | interrupteurs d'écran (mod-affichage, gardés dans les préférences) | **Repris** |
| Aimanter à › Tranches | | bords des tranches utilisateur parmi les cibles d'aimantation | **Repris** |
| Fichier › Importer › Notes | les notes d'un fichier | le moteur désactive la commande : les notes d'un AUTRE DOCUMENT OUVERT copiées par le pont (`notes.list` puis `notes.add`) | **Adapté** |

Livrées : 12 sur 12.

## Pont

- `GET /analyse` : règle, comptage, notes, tranches et échelle en UNE séquence (ce que la surcouche dessine).
- `GET /mesures.csv` : CSV du journal (colonnes choisies, séparateur `;`, UTF-8 avec BOM pour un tableur).
- `POST /notes/importer {document}` : notes d'un autre document ouvert, copiées dans l'actif.
- Liste blanche : textes des notes et options des tranches (`url`, `alt`, `message`, `target`, `cellText`, `name`)
  sont du TEXTE rangé dans le document (jamais lu comme chemin) — vérifiés clé par clé et bornés, comme `file.fileInfo`.

## Écran

`mod-mesure.js` (outils Règle, Comptage, Note, Tranche, Sélection de tranche, barres d'options, surcouche SVG),
`mod-journal.js` (panneaux Journal des mesures et Notes) ; onglets « Mesures » et « Notes » dans le groupe Infos ;
crochets mod-affichage (3 interrupteurs, aimantation), mod-historique (noms d'étapes), mod-menus, mod-espaces.

## Relevé d'exécution (09/10/2026)

**Pont.** `photolab_registre` : vérificateurs clé par clé de `count.*` (7), `notes.add|set|delete`, `slice.new|set|promote|
delete|divide`, `measurementLog.delete` (le registre résume leurs formes alternatives et refusait 10 formes légitimes,
dont une note « voir a/b.png » prise pour un fichier). `photolab_moteur` : `analyse`, `journal_csv`, `importer_notes`.
Routes `/analyse`, `/mesures.csv`, `/notes/importer`. Clés d'affichage reprises (`compteur`, `notes`, `tranches`) dans
la liste blanche des préférences ; groupe Infos + `mesures`, `notes` (photolab_espaces).

**Écran.** `mod-mesure` (5 outils, barres d'options, surcouche SVG, panneaux Mesures et Notes, import de notes) ;
onglets Mesures / Notes (index.html) ; crochets mod-affichage (3 interrupteurs, aimantation aux tranches, outil Tranche
aimanté), mod-menus (`IDS_MESURE`), mod-espaces (`PANNEAUX`), mod-historique (20 noms d'étapes), mod-outils (5 outils actifs).

**Faits du moteur en plus des sondes.** Vider un journal VIDE est refusé (« the Measurement Log is empty ») : le bouton
est grisé. Le CSV suit les colonnes choisies par source (`dataPoints`), Histogramme compris.

**Défauts trouvés à la preuve.** Glisser une note ou une tranche cumulé pas à pas : la surcouche est relue PENDANT le
glisser (cycle du geste précédent) et le pas perdu -> déplacement calculé depuis l'origine du geste
(`positionNote`, `deplacerRect`) ; un clic qui choisit une tranche faisait une étape « Slice Options » (`rectChange`) ;
la note posée n'était pas celle du panneau (l'index était ramené à la dernière note connue avant la relecture) ;
le texte ne recevait pas le focus ; points de la règle en 99.99999… (`arrondirPoint`) ; « -0 » dans le CSV et le
tableau ; la Tranche ne s'aimantait pas (absente d'`OUTILS_AIMANTES`) ; colonne Source en anglais -> nom de l'outil.
« Notes » est aussi « Release notes » (Réglages) : clé d'onglet propre, en contexte, posée par le script.
Piège de preuve : volet masqué = fenêtre 0 × 0 -> la vue se recale à 1 % et toute tolérance d'écran devient énorme
(chaque clic « attrape » une marque) ; `resize_window` 1400 × 900 avant les gestes.

**Bancs.** `test_photolab_mesure` 104/104 (vrai moteur) ; QA `mesure` 37 ; bancs figés mis à jour : affichage 1.3,
2.10, 2.15, 2.16 (+2.16b), 7.1, 7.3 ; espaces 1.2, 1.10, 5.4 ; outils 1.5, 2.14 ; test_photolab_espaces 1c. Série
photolab + i18n verte (hors `apropos`, `installeur`, `reglages_moteur`, rouges par nature dans un worktree).
Mutations 20/20 tuées (10 pont, 10 écran), sources vérifiées par `cmp`.

**Preuve** (vrai backend jetable, gestes PointerEvent sur la toile, FR puis EN) : règle 200 px puis rapporteur 90°
par Alt, aucune étape ; comptage (3 marques numérotées, glisser, Alt-clic, nouveau groupe, taille) ; notes (pose,
focus, texte « / », précédente, glisser 148 × 118, panneau) ; tranches (glisser, choisir sans étape, déplacer, poignée,
options par double clic avec une URL, Suppr, diviser 2 × 2, promouvoir une automatique, d'après les repères, message
« verrouillées ») ; journal (enregistrer règle et comptage, tableau traduit, export CSV de la ligne choisie, supprimer) ;
Affichage › Compteur / Notes / Tranches (surcouche vide puis rendue, coches) ; aimantation au bord 150 ; import des
2 notes de A dans B (bornée à 99 × 79, fermées) ; barres, onglets et panneaux en anglais.

**Recomptage** `lister_bientot.mjs` : 93 (105 avant) = 12 entrées livrées.

**Fiche d'aide.** Aucune : les cinq outils sont dans les menus déroulants des emplacements Recadrage et Pipette
(fiches existantes par emplacement), sans id propre à viser.
