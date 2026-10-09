# Photolab parité L9 (t159) : préférences, raccourcis, menus, préréglages, touches de modification

Base : `main` d8202cf9. Branche `chantier/photolab-parite-l9`. Skill `parite-photolab`. Source : relevé
`specs/2026-10-08-photolab-bientot-inventaire.md` (ligne « Préférences, raccourcis, menus (26) »).

## Périmètre (recensé par `lister_bientot.mjs`, 129 « bientôt » au départ)

25 entrées de menu (26 au suivi) : Édition › Préférences (18), Édition › Préréglages (3), Édition › Raccourcis clavier
(et Fenêtre › Espace de travail › Raccourcis clavier), Édition › Menus, Fenêtre › Touches de modification.

## Décisions de l'utilisateur (09/10/2026)

- Q1 : les sections sans objet dans Deepotus (Disques de travail, Performances, Extensions, Valeurs Raw, Intégrations
  d'IA, Journal de l'historique) existent et disent en une phrase qui s'en charge.
- Q2 : préférences, raccourcis et menus dans le dossier de données Deepotus (`<données>/photolab/preferences.json`),
  route à liste blanche stricte comme `/espaces` ; les options d'Affichage et les préférences de Texte déjà gardées par
  le navigateur y sont reprises au premier chargement.
- Q3 : préréglages exportés par téléchargement d'un `.json`, importés depuis un `.json` du PC lu par la page et envoyé
  comme DONNÉES (jamais un chemin), taille et forme vérifiées par le pont.

## Sondes du vrai moteur (copie portable dans le scratchpad, jamais l'installé)

- `prefs.get` rend 25 sections ; les énumérations et bornes viennent des messages de `prefs.set` (« must be one of… »,
  « within a..b ») : elles sont reprises TELLES QUELLES par le schéma de l'écran (mêmes clés, mêmes valeurs).
- `edit.keyboardShortcuts {list}` : 779 commandes, 93 raccourcis ; `edit.menus {}` : `{colors, hidden}`. L'écran n'appelle
  ni l'un ni l'autre (ils écrivent les préférences du moteur) : ses menus sont générés, ses raccourcis lus du catalogue.
- `edit.presets.presetManager` : `list|rename|delete|move` sur `brushes|customShapes|patterns`, par `index`, erreur
  claire hors bornes ; `exportImportPresets` : export = `{format:"photocraft-presets", version:1, brushes, customShapes}`
  (préréglages UTILISATEUR seulement), import refuse un autre format.
- **En mode `serve`, rien n'est persisté** : un pinceau enregistré disparaît à la relance du moteur (36 → 37 → 36),
  `prefs.set` n'écrit aucun fichier. Le gestionnaire de préréglages agit donc sur la session (comme tous les panneaux
  de préréglages depuis t153) ; l'export / import est le moyen de les garder — dit dans le dialogue.

## Tableau chez eux / chez nous / décision

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Préférences (18 sections) | un dialogue, liste des sections à gauche, Précédent / Suivant, OK / Annuler, Réinitialiser | un dialogue Deepotus, mêmes sections et même ordre ; chaque entrée de menu ouvre SA section ; OK enregistre (route), Annuler ne change rien ; « Réinitialiser les préférences » (confirmé) | **Repris** |
| Paramètres | sélecteur, interpolation, zoom molette, placer… | Zoom avec la molette ; Placer : redimensionner, toujours en objet dynamique | **Adapté** (3 réglages qui agissent) |
| Interface | thème, couleur et bordure du plan de travail, infobulles, couleurs des menus, langue, taille | Couleur du fond de la toile (5 + personnalisée), bordure (ombre / trait / aucune), infobulles, couleurs des menus ; Langue et thème : « Réglages de Deepotus » | **Adapté** |
| Espace de travail | onglets, grands onglets, mémoriser les modifications… | grands onglets, mémoriser les modifications d'espace (mod-espaces) ; « ouvrir dans des onglets » écarté : sans onglets l'écran n'aurait plus aucun moyen de changer de document | **Adapté** (2) |
| Outils | Maj pour changer d'outil, défilement au-delà, zoom centré… | Maj pour changer d'outil (`prefMaj`, déjà prévu), défilement au-delà du document, zoom sur le point cliqué au centre | **Repris** (3) |
| Journal de l'historique | journal en métadonnées / fichier | section explicative : l'Historique du document, rien n'est écrit dans le fichier | **Adapté (Q1)** |
| Gestion des fichiers | extensions, aperçus, fichiers récents… | Extension en minuscules (noms d'export) | **Adapté** (1) |
| Exportation | format et lieu de l'exportation rapide, métadonnées | Format de l'exportation rapide (PNG, JPG, GIF, WEBP) + qualité JPG ; lieu : demander / téléchargement | **Adapté** |
| Performances, Disques de travail, Extensions, Valeurs Raw, Intégrations d'IA | moteur, disques, modules | section explicative (moteur géré par Deepotus, dossier de données, aucun module, ouverture par la Bibliothèque, pilotage = celui de Deepotus) | **Adapté (Q1)** |
| Curseurs | outils de peinture (4), autres (2), réticule, couleur d'aperçu | les mêmes, appliqués au curseur de la toile | **Repris** |
| Transparence et gamut | taille et couleurs du damier | taille (aucun, petit, moyen, grand) et couleurs (« thème », 9 + personnalisées) du damier de la vue ; défaut « thème » = l'aspect d'avant t159 | **Repris** (gamut : le moteur n'a pas l'alerte) |
| Unités et règles | unité des règles | unité des règles (7), conversion par la résolution du document | **Repris** (1) |
| Repères, grille et tranches | couleur et style des repères, de la grille, pas, subdivisions | couleur et style (trait, tirets, points) des repères et de la grille, pas + unité, subdivisions ; tranches : t160 | **Repris** |
| Texte | aperçu des polices, Échap valide… | Taille de l'aperçu des polices (la même que Texte › Taille de l'aperçu), Échap valide le texte | **Adapté** (2) |
| Commandes avancées | trackpad, curseurs déroulants | section explicative : le navigateur rapporte les gestes, rien à régler | **Adapté (Q1)** |
| Raccourcis clavier | jeux, Menus de l'application / des panneaux / Outils, conflits, Résumer | une liste filtrable : commandes des menus (Ctrl / Alt / F1-F12) et outils (une lettre) ; saisie de la combinaison, conflit nommé et « Accepter » qui retire l'autre, Par défaut, Tout par défaut, Résumer = téléchargement d'un .html | **Adapté** (un jeu personnel, pas de jeux nommés) |
| Menus | masquer un élément, couleur, « Afficher tous les éléments » | les mêmes, appliqués par le décorateur des menus ; Préférences et Menus… ne se masquent pas | **Repris** |
| Gestionnaire de préréglages | types, liste, renommer, supprimer, déplacer | Pinceaux, Formes personnalisées, Motifs (les 3 du moteur) ; renommer, supprimer (confirmé), monter / descendre | **Repris** (session du moteur) |
| Exporter / importer des préréglages | fichiers | téléchargement d'un `.json` ; import d'un `.json` du PC envoyé en données, vérifié par le pont | **Repris (Q3)** |
| Migrer les préréglages | depuis une version précédente | lit un CHEMIN de préférences d'une autre version : rien à migrer dans Deepotus | **Écarté** (`refuse:edit.presets` resserré) |
| Touches de modification | panneau Maj / Ctrl / Alt pour l'écran tactile | panneau flottant : un clic = la prochaine action, double clic = tenue ; les gestes et les clics lisent la touche comme si elle était enfoncée | **Repris** |

Livrées : 24 sur 25 (Migrer reste « bientôt »).

## Pont

- `photolab_preferences.py` : schéma (sections, clés, types, énumérations, bornes, couleurs `#rrggbb`), `raccourcis`
  (id → combinaison normalisée, `""` = retiré), `menus` (`masques`, `couleurs`), `reprise` (options d'Affichage et
  préférences de Texte) ; valider = liste blanche STRICTE, défauts complétés, fichier atomique. Copie JS du schéma
  comparée par le banc.
- Routes `GET/PUT /api/photolab/preferences`, `POST /api/photolab/preferences/reinitialiser`.
- `PERMIS_REFUSES` + `edit.presets.presetManager` (action, kind énumérés, index entier, nom borné) et
  `edit.presets.exportImportPresets` (action, kinds, `data` : format, version, listes, ≤ 2 Mo, ≤ 500 éléments, aucune clé
  `path` / `file` à aucune profondeur). `edit.presets.migratePresets` reste refusée.

## Écran

- `mod-preferences.js` (schéma, `normaliser`, `appliquer` aux modules, dialogue à sections), `mod-clavier.js` (éditeurs
  Raccourcis et Menus, fonctions pures : conflits, résumé), `mod-modificateurs.js` (panneau, propriétés d'événement
  redéfinies en capture), gestionnaire et export / import dans `mod-presets.js`.
- Crochets : `mod-vue` (molette, défilement au-delà, damier, fond, bordure, curseurs), `mod-affichage` (couleurs,
  styles, pas, unités des règles, stockage repris), `mod-outils` (`prefMaj`, lettres personnalisées), `mod-raccourcis`
  (combinaisons personnalisées), `mod-menus` (masques, couleurs, raccourcis affichés), `mod-documents` (onglets,
  format d'export, extension), `mod-espaces` (mémoriser), `mod-texte` (aperçu, Échap), Placer (options envoyées).

## Bancs

`test_photolab_preferences.py` (schéma, refus, route, préréglages sur le vrai moteur), QA `preferences`, `clavier`,
`modificateurs` ; bancs figés mis à jour ; `lister_bientot.mjs` : 129 → 104.

## Relevé d'exécution (09/10/2026)

**Écarts au plan.** Défauts propres à Deepotus pour garder l'aspect d'avant t159 : damier « theme » (valeur ajoutée),
bordure « line » (photocraft : dropShadow). `openDocumentsAsTabs` retiré (voir le tableau). Exportation rapide :
`gif` retiré (le pont n'exporte pas ce format) ; lieu `ask | download | library` (photocraft : `ask | sameFolder`).
Aperçu des polices sans « off » (l'écran montre toujours un aperçu).

**Faits du moteur.** Un import de préréglage du même nom REMPLACE (aucun doublon). `presetManager move` : `index` ->
`to` dans la liste aplatie que `list` rend. Les 7 sections sans objet n'ont aucune clé dans le schéma (le pont refuse
`prefs.performance`, banc 2b).

**Pont.** `photolab_preferences` (schéma, raccourcis, menus, affichage, texte ; lire / écrire / réinitialiser),
routes `/preferences` (GET, PUT, POST réinitialiser), `PERMIS_REFUSES` + gestionnaire et échange (`_v_gestionnaire`,
`_v_echange` : index, noms bornés, données sans clé ni valeur de fichier, 2 Mo, 500 préréglages, profondeur 12),
`placer(objet_dynamique, reduire)`.

**Écran.** `mod-preferences` (dialogue à 18 sections, `PL.prefs`, reprise du navigateur, infobulles), `mod-clavier`
(Raccourcis clavier : commandes et outils, conflit nommé et retiré, réservés, Résumer en .html ; Menus : masquer,
couleur, « Afficher tous les éléments de menu »), `mod-modificateurs` (panneau, propriétés d'événement redéfinies en
capture), `mod-gestionnaire` (gestionnaire, export / import). Crochets : `mod-vue` (molette, damier, bordure,
défilement borné, zoom centré), `mod-affichage` (couleurs et styles, pas, règles dans l'unité, options reprises),
`mod-outils` (lettres, curseurs), `mod-peinture` / `mod-gestes` (pointe, réticule), `mod-documents` (exportation rapide,
extension, Placer), `mod-espaces` (mémoriser), `mod-texte` (aperçu, langue, Échap), `mod-menus` (entrées visibles,
couleurs), `mod-presets` / `mod-pinceaux` (relecture après le gestionnaire).

**Défauts trouvés en route.** Clés du dictionnaire en camelCase (refusées par test_i18n_l0) -> `snake` ; libellés
d'unités et de styles oubliés (QA 3.1) ; « Points » FR déjà traduit « Dots » -> « Points typographiques », et EN
« Points » refusé en chaîne (2.6) -> « Typographic points » ; couleurs de menu en dur (zones 4.3) -> jetons ;
noms de touches français littéraux -> dictionnaire.

**Bancs.** `test_photolab_preferences` 113/113 (vrai moteur) ; mutations 20/20 tuées (B8 et B9 ont d'abord survécu, attrapées par une seconde garde -> cas 4d « valeur anodine » et 4e2 « par le préfixe », puis série rejouée en entier), sources vérifiées par `cmp` ; QA `preferences` 49 ; bancs figés : espaces 5.1
(Raccourcis actif), menus 7.3 (18 permis), fichier_mode 1d (`data` de l'échange exemptée), i18n l0/l1/l2 verts.
`apropos` 3, `installeur` 2, `reglages_moteur` 2 rouges : mêmes comptes sur `main` nu (worktree détaché).

**Preuve sur 8796** (vrai backend jetable, gestes par le DOM, FR puis EN ; capture d'écran impossible, volet masqué) :
reprise du navigateur au premier chargement ; Préférences › Repères (grille rouge en tirets, 2 cm / 2 subdivisions =
38,4 px d'écran relevés) ; damier grand rouge relu au pixel sur un document transparent ; fond personnalisé ;
infobulle coupée puis rendue ; Raccourcis : Ctrl+Alt+J donné à Niveaux puis à Courbes (conflit nommé, retiré), Ctrl+Z
réservé, Ctrl+Alt+J ouvre Courbes ; Menus : Niveaux masqué, Courbes en rouge, « Afficher tous les éléments » ; Touches
de modification (une, tenue, relâchée) lues par la toile ; gestionnaire (descendre, renommer, supprimer confirmé) ;
export intercepté puis import d'un pinceau supprimé, fichier étranger et clé `path` refusés ; lettre K -> Pinceau,
curseur précis, molette qui zoome, défilement borné, Placer sans objet dynamique ni réduction, exportation rapide JPG
vers la Bibliothèque ; dialogue, Raccourcis et panneau en anglais.

**Recomptage** `lister_bientot.mjs` : 105 (129 avant) = 24 entrées livrées.

**Fiche d'aide.** Aucune : entrées de menu et dialogues, sans outil ni bouton à id stable à viser.
