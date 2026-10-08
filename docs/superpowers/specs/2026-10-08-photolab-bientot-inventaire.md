# Photolab — rendre actives les entrées « bientôt » : relevé et tableau d'écart

> Date : 08/10/2026. Base : `origin/main` 4dcae97f (Photolab P1-P5 livrés, t136-t140).
> Skill : `parite-photolab` (`~/.claude/skills/parite-photolab/`). Liste complète, élément par élément, avec le
> lot proposé : `2026-10-08-photolab-bientot-liste.md` (282 lignes, générée depuis le code de l'écran).
> Sources : code de l'écran (`frontend/photolab/js/mod-menus.js`, `mod-champs.js`, `mod-outils.js`, `index.html`),
> registre du moteur (`backend/tests/photocraft_commandes_0.3.0.json`, 776 commandes), code du shell photocraft
> v0.3.0 (`crates/ui-egui/src/menus.rs`, `workspace_ui.rs`), et **relevé en lecture seule dans l'application de
> retouche de référence installée sur le PC de l'utilisateur** (version 2026, interface française), le 08/10/2026.
>
> Demande de l'utilisateur (08/10, mot pour mot) : « creer un skill pour faire toutes les recherches nécessaires au
> fonctionnement des actions labellisées "bientot", sers toi de ma copie de photoshop 2026 lancée et installée sur mon
> pc actuellement pour lister et implémenter toutes les fonctionalités manquantes. y compris les différents
> environnements d'espaces de travail ».

## 1. Compte des éléments « bientôt »

Le recensement ne vient pas d'une liste tenue à la main : il est refait depuis le code réel de l'écran par
`scripts/lister_bientot.mjs`. Il couvre les menus générés (`construireMenus`), les outils `p2:false` et les onglets de
panneaux absents d'`index.html`.

| Catégorie | Éléments | Raison technique |
|---|---:|---|
| Menus générés, total | **237 / 631** | |
| · refusés par le pont, famille `window.*` (fenêtres, espaces, panneaux) | 61 | préfixe `window.` de `PREFIXES_REFUSES` |
| · refusés par le pont, famille `file.*` | 45 | préfixe `file.` |
| · refusés par le pont : préférences, raccourcis, menus, préréglages | 24 | `edit.preferences`, `edit.keyboardshortcuts`, `edit.menus`, `edit.presets` |
| · refusés par le pont : Image › Mode | 12 | `image.mode.` : le champ `profile` lit un chemin arbitraire (relevé t138) |
| · absents du moteur (commandes du SHELL de photocraft) | 77 | `view.*` 55, `type.*` 14, `edit.transform.*` / `edit.freeTransform` 6, `edit.search`, `select.selectAndMask` |
| · présents dans le moteur, sans écran possible au générique | 10 | fichier requis (6), autre document (1), opaques requis (1), fichier de déplacement / flamme (2) |
| · écartés D9 + nommés sans éditeur | 8 | décision D9 (6) ; `filter.other.custom`, `filter.convertForSmartFilters` |
| Outils `p2:false` | **34 / 45** | peinture, retouche, texte, formes, plume, tranches, règle, notes, comptage, sélection d'objet |
| Onglets de panneaux absents | **11 / 17** | Nuancier, Dégradés, Motifs, Caractère, Paragraphe, Histogramme, Infos, Actions, Compositions, Couches, Tracés |
| Boutons isolés (panneau Calques) | **2** | Lier, Masque (`bientot(` dans `mod-calques.js`) |
| **Total** | **284** | |

Le fait déterminant : **le moteur 0.3.0 sait faire bien plus que l'écran n'expose.** Un id absent du catalogue
du moteur est presque toujours une commande du shell egui, et il existe à côté une commande moteur réelle. Les
transformations passent par `edit.transform` (quadrilatère ou matrice), le pinceau par `paint.stroke` (liste de
points avec pression), le texte par `type.create`, les formes par `shape.create`, et les familles `path.*`,
`channel.*`, `layerComp.*`, `pattern.presets.*`, `gradient.presets.*`, `select.refineEdge`, `filter.gallery.*` (47)
et `view.newGuide` existent aussi. Rien dans ces lots n'oblige à calculer des pixels en JavaScript (D1 tenu).

## 2. Relevé de la référence : espaces de travail

Relevé en lecture seule, Loupe à 200 %, accord de l'utilisateur pour changer d'espace actif. Espace de départ :
« Graphique et web » ; il a été rétabli à la fin et vérifié par capture (même disposition, volet Couleur déplié,
onglet Bibliothèques actif). Seul le dialogue « Nouvel espace de travail » a été ouvert, puis fermé par Échap.
Une transformation manuelle (Ctrl+T) a servi à lire la barre d'options, puis a été annulée par Échap : l'historique
est resté sur « Annuler Nouveau calque de texte ». Aucun incident à signaler.

### 2.1 Le menu

Il est à deux endroits : Fenêtre › Espace de travail, et le sélecteur en haut à droite de la barre d'options. Ses
entrées, dans l'ordre :
- les espaces fournis : « Outils de base », « Les indispensables (par défaut) », « Graphique et web »,
  « Mouvement », « Peinture », « Photographie », l'espace actif étant coché ;
- séparateur ;
- « Réinitialiser <espace actif> » : le libellé porte le nom de l'espace ;
- « Nouvel espace de travail… » ;
- « Supprimer l'espace de travail… » ;
- séparateur ;
- « Raccourcis clavier et menus… » ;
- « Verrouiller l'espace de travail » (case à cocher).

Dans Fenêtre, une case à cocher par panneau. Les F‑touches relevées sont Actions Alt+F9, Calques F7, Couleur F6,
Informations F8 et Paramètres de pinceau F5. Puis viennent « Éditeur assisté par IA », « Options », « Outils »,
« Barre des tâches contextuelle », et la liste des documents ouverts.

### 2.2 Ce que chaque espace montre

Partout, la colonne de droite est un empilement de groupes à onglets. À sa gauche se trouve une colonne d'icônes
repliée : un clic sur une icône ouvre le groupe en volet flottant. La disposition ci-dessous a été lue à l'écran.
Les icônes de la colonne repliée n'ont pas de libellé : leur nom est déduit du dessin et de la liste du menu
Fenêtre, ce qui est signalé par « (?) ».

| Espace | Colonne repliée (icônes) | Groupes à onglets, de haut en bas | Particularités |
|---|---|---|---|
| Outils de base | Historique | Propriétés · Réglages │ Calques | barre d'outils RÉDUITE (≈ 16 emplacements au lieu de ≈ 22) |
| Les indispensables (défaut) | Historique (icône + libellé) | Couleur · Nuancier · Dégradés · Motifs │ Propriétés · Réglages · Bibliothèques │ Calques · Couches · Tracés | barre d'outils sur DEUX colonnes |
| Graphique et web | Historique · Couleur · Nuancier (groupe « Historique, Couleur, Nuancier, » ») | Caractère · Paragraphe · Glyphes │ Propriétés · Bibliothèques · Compositions de calques │ Calques | |
| Mouvement | Historique · Propriétés (?) · Paramètres de pinceau + Pinceaux (?) · Source de duplication (?) · Caractère + Paragraphe | Histogramme · Informations │ Bibliothèques · Réglages │ Calques · Couches | panneau **Montage** (timeline) en bas, sur toute la largeur |
| Peinture | Historique · Paramètres de pinceau · Source de duplication (?) · Outils prédéfinis (?) · un 5e (?) | Nuancier · Navigation │ Pinceaux │ Calques · Couches · Tracés | |
| Photographie | Historique · Propriétés · Informations · Source de duplication (?) | Histogramme · Navigation │ Réglages (préréglages Portraits / Paysage / Réparation de photos…, onglets « Paramètres prédéfinis » / « Réglages uniques ») · Bibliothèques │ Calques · Couches · Tracés | |

Comportements observés :
- **Chaque espace mémorise sa disposition modifiée.** En revenant à « Graphique et web », on retrouve le volet
  Couleur déplié et l'onglet Bibliothèques actif. « Réinitialiser » rend la disposition d'origine (non exécuté ici :
  conforme au libellé et au code amont).
- Changer d'espace change aussi la barre d'outils : réduite dans « Outils de base », sur deux colonnes dans « Les
  indispensables ».
- Le document et le zoom ne bougent pas ; seule la largeur du canevas suit celle de la colonne de panneaux.

### 2.3 Dialogues

- **Nouvel espace de travail** : champ « Nom » (prérempli « Sans titre-1 », sélectionné). Puis un cadre
  « Capture » : la position des panneaux est toujours enregistrée, et trois cases facultatives, décochées par défaut,
  ajoutent « Raccourcis clavier », « Menus » et « Barre d'outils ». Boutons « Enregistrer » et « Annuler ».
  Échap annule.
- **Supprimer l'espace de travail** (relevé de l'utilisateur) : liste déroulante de l'espace à supprimer, boutons
  « Supprimer » et « Annuler ». Il n'a pas été ouvert ni validé ici.

### 2.4 Chez photocraft (le code du shell v0.3.0)

`window.workspace.{essentials, photography, painting, pixelArt, graphicAndWeb, motion}` choisit un préréglage qui
ne fait qu'afficher ou masquer cinq panneaux (Navigateur, Couleur, Calques, Historique, Propriétés), dans un ordre
de groupes par défaut (`apply_workspace`). « Réinitialiser » réapplique l'espace actif. « Nouveau » et « Supprimer »
enregistrent les dispositions dans les préférences (`Preferences::workspaces`) ; « Supprimer » est grisé quand
aucun espace n'a été enregistré. « Verrouiller » est une case enregistrée dans les préférences. Le catalogue amont
a un espace « Pixel art » et n'a pas d'« Outils de base ».

## 3. Relevé de la référence : autres familles

- **Affichage** : Format d'épreuve ›, Couleurs d'épreuve Ctrl+Y, Couleurs non imprimables Maj+Ctrl+Y, Format des
  pixels ›, Correction du format des pixels (grisé), Options d'aperçu 32 bits… (grisé) │ zooms : Zoom avant / arrière,
  Adapter à l'écran, Adapter les calques, Adapter le plan de travail (grisé), 100 % Ctrl+1, 200 %, Taille
  d'impression, Taille réelle, Symétrie axe horizontal, Aperçu du motif │ Mode d'affichage › │ Extras Ctrl+H (coché),
  Afficher › │ Règles Ctrl+R │ Magnétisme Maj+Ctrl+; (coché), Accrocher à › │ Repères › │ Verrouiller les tranches,
  Effacer les tranches.
  - **Afficher ›** : Contours du calque, Contour de la sélection, Tracé cible Maj+Ctrl+H, Grille Ctrl+", Repères
    Ctrl+;, Repères de la zone de travail, Repères du plan de travail, Noms des plans de travail, Comptage, Repères
    commentés, Tranches, Annotations, Grille des pixels, Limites du carreau Aperçu du motif, puis Filet.
  - **Accrocher à ›** : Repères, Grille, Calques, Tranches, Limites du document, Tout, Sans.
  - **Repères ›** : Modifier les repères sélectionnés, Verrouiller les repères Alt+Ctrl+;, Effacer les repères (et
    leurs variantes), Nouveau repère…, Nouvelle disposition des repères…, Nouveaux repères de formes.
- **Édition › Transformation ›** : Répéter Maj+Ctrl+T │ Homothétie, Rotation, Inclinaison, Distorsion, Perspective
  (les deux dernières grisées sur un calque de texte) │ Déformation, Fractionner la déformation horizontale ou
  verticale… Plus haut dans le même menu : Transformation manuelle Ctrl+T, Déformation de la marionnette (D9 chez
  nous), Déformation de perspective, Échelle basée sur le contenu Alt+Maj+Ctrl+C.
  - **Barre d'options de la transformation manuelle** : point de référence (grille 3 × 3), X et Y en px (bouton Δ
    pour les valeurs relatives), L et H en % (chaîne pour lier les deux), angle en °, inclinaisons H et V en °,
    Interpolation « Bicubique ». Échap annule.
- **Image › Mode ›** : Bitmap (grisé en RVB), Niveaux de gris, Bichromie (grisé), Couleurs indexées…, Couleurs RVB
  (coché), Couleurs CMJN, Couleurs Lab, Multicouche, 8 / 16 / 32 bits par couche, Table des couleurs… (grisé).
- Les autres familles (peinture, texte, formes, masques, fichiers) se relèvent dialogue par dialogue au début de
  chaque lot, selon la méthode du skill (§3 de `parite-photolab`). Le relevé exhaustif de 284 éléments en une seule
  séance aurait été peu fiable.

## 4. Tableau d'écart

| Famille | Chez eux (référence + photocraft) | Chez nous aujourd'hui | Décision |
|---|---|---|---|
| Espaces de travail (11 entrées `window.workspace.*`) | 6 espaces fournis + Réinitialiser / Nouveau / Supprimer / Verrouiller ; disposition mémorisée par espace ; sélecteur dans la barre du haut | une disposition fixe (3 groupes + rail) | **À faire, lot 1** : disposition DÉCRITE PAR DES DONNÉES (groupes, onglets, colonne repliée, barre d'outils 1 ou 2 colonnes) ; espaces Deepotus de mêmes noms (mots courants, voir Q1) ; un panneau pas encore construit est sauté, puis apparaît quand son lot arrive |
| Fenêtre › <panneau> (17 cases utiles) | case à cocher par panneau, F5-F9 | panneaux toujours visibles | **À faire, lot 1** pour les panneaux existants ; les autres s'activent avec leur lot |
| Fenêtre › Organiser (19) | mosaïques, flottantes, faire correspondre | un document visible à la fois (onglets) | **Écarté** pour l'instant (un seul canevas) |
| Affichage (41) | zooms, règles, grille, repères, extras, aimantation, modes d'écran | zoom par Ctrl+0/1 et molette (`mod-vue`), sans entrée de menu | **À faire, lot 2** : brancher les zooms existants, surcouches d'écran (règles, grille, grille de pixels, contours) ; repères par `view.newGuide` (enregistrés dans le document) |
| Format des pixels, épreuve CMJN (15) | vidéo anamorphique, épreuve écran | — | **Écarté** (hors besoin retouche web/vidéo carrée ; reprendre si l'impression arrive) |
| Panneaux absents (7 + 3 dans le lot 6) | Nuancier, Dégradés, Motifs, Histogramme, Infos, Couches, Compositions | — | **À faire, lot 3** : `tools.setColors`, `gradient.presets.*`, `pattern.presets.*`, route `/histogramme`, `document.pixel`, `channel.*`, `layerComp.*` |
| Transformation (6) | Ctrl+T, poignées, barre d'options X/Y/L/H/angle/inclinaison/interpolation | — | **À faire, lot 4** : poignées à l'écran → `edit.transform {quad|matrix}` à la validation ; aperçu CSS pendant le geste, rendu par le moteur ensuite (D1) |
| Peinture et retouche (23) | Pinceau, Crayon, Gommes, Tampon, Correcteurs, Densité, Flou/Netteté/Doigt, Dégradé, Pot ; Pinceaux, Paramètres de pinceau, Source de duplication | — | **À faire, lot 5** (P3b de la conception) : geste → `paint.*` avec la liste des points ; peut se scinder en 5a peinture / 5b retouche |
| Texte, formes, plume (32) | outils T, U, P, A ; Caractère, Paragraphe, Glyphes ; menu Texte | — | **À faire, lot 6** : `type.*`, `shape.*`, `path.*` |
| Masques et sélection avancée (4 + 2 boutons) | Lier, Masque, Sélectionner et masquer, Galerie de filtres, sélection d'objet | boutons grisés | **À faire, lot 7** : `layer.layerMask.*`, `select.refineEdge`, `filter.gallery.*`, `select.object` |
| Fichier et Image › Mode (29) | Enregistrer une copie, Revenir, Tout fermer, Export rapide, Exporter sous, Objets dynamiques, Mode | refusés (sécurité) | **À faire, lot 8** : par les routes Deepotus (Bibliothèque) ; Mode par liste blanche PAR COMMANDE, profil intégré uniquement (jamais un chemin), bancs de refus |
| Préférences, raccourcis, menus (26) | 18 sections de préférences, éditeur de raccourcis | refusés (le moteur écrirait ses préférences) | **À faire, lot 9** : préférences de l'ÉCRAN (stockage Deepotus), jamais `prefs.*` du moteur ; peut rester bas dans la file |
| Mesure, notes, tranches, comptage (7) | outils I/C secondaires, journal des mesures | — | **À faire, lot 10** (bas de file) : `count.*`, `notes.*`, `slice.*`, `image.analysis.rulerTool` |
| Automatisation, scripts, impression, vidéo, D9 (45) | lots, droplets, scripts, impression, timeline, Liquéfier… | — | **Écarté** (D9, et la vidéo reste au Montage) |

## 5. Lots proposés (suivi des chantiers, t151 → t160)

Les lots d'écran pur viennent d'abord. Ensuite ceux qui passent par des commandes moteur existantes, puis ceux qui
touchent au pont (sécurité). Les comptes se recoupent avec la colonne Lot de l'annexe.

| Tâche | Lot | Éléments | Nature | Taille |
|---|---|---:|---|---|
| t151 | L1 Espaces de travail + Fenêtre › panneaux | 28 | écran pur | M |
| t152 | L2 Affichage : zooms, règles, grille, repères, extras | 41 | écran + `view.newGuide` | M |
| t153 | L3 Panneaux Nuancier, Dégradés, Motifs, Histogramme, Infos, Couches, Compositions | 7 (+ leurs cases Fenêtre) | écran + moteur | L |
| t154 | L4 Transformation manuelle et Transformation › | 6 | écran + `edit.transform` | M |
| t155 | L5 Peinture et retouche (P3b) | 23 | écran + `paint.*` | L (scindable) |
| t156 | L6 Texte, formes, plume, tracés | 32 | écran + `type/shape/path.*` | L |
| t157 | L7 Masques, Sélectionner et masquer, Galerie de filtres | 4 + 2 boutons | écran + moteur | M |
| t158 | L8 Fichier sûr et Image › Mode sous liste blanche | 29 | pont + sécurité | M |
| t159 | L9 Préférences et raccourcis de l'écran | 26 | écran | M |
| t160 | L10 Mesure, notes, tranches, comptage | 7 | écran + moteur | S |
| — | Écartés | 79 | | |

Total : 203 éléments répartis en lots et 79 écartés, soit 282 ; les 2 boutons isolés du panneau Calques sont dans L7.

**Lot 1 en détail (t151).**
- `mod-espaces.js` (pur, testé sous node) : description de chaque espace par des données (groupes, onglets, ordre,
  colonne repliée, barre d'outils 1 ou 2 colonnes) ; état par espace (disposition modifiée), réinitialiser,
  enregistrer sous un nom, supprimer, verrouiller.
- L'écran construit `#panneaux` et `#rail` depuis cette description (aujourd'hui ils sont écrits en dur dans
  `index.html`).
- Fenêtre › Espace de travail et Fenêtre › <panneau> passent dans `TRAITES_PAR_ECRAN` ; `REFUSES` ne change pas
  (`window.` reste refusé au moteur).
- Sélecteur dans la barre d'options.
- Dialogues maison « Nouvel espace » (Nom + case « Barre d'outils » ; Raccourcis et Menus viendront avec L9) et
  « Supprimer » (liste, puis confirmation).
- Raccourcis F5-F9 pour les panneaux qui existent.
- Textes par dzT en FR et EN ; QA node, preuve sur 8799, fiche d'aide.

## 6. Questions à l'utilisateur avant de lancer t151

- **Q1 — Noms et liste des espaces.** Il y a deux listes :
  - celle de la référence : Outils de base, Les indispensables, Graphique et web, Mouvement, Peinture, Photographie ;
  - celle du catalogue photocraft : Essentiel, Photographie, Peinture, Pixel art, Graphisme et web, Mouvement.

  Proposition : les sept espaces, sous des mots courants : « Essentiel » (défaut), « Base », « Graphisme et web »,
  « Mouvement », « Peinture », « Photo », « Pixel art ». L'espace « Mouvement » n'a pas de panneau Montage chez nous :
  la vidéo reste au Montage (D9).
- **Q2 — Où enregistrer les espaces de l'utilisateur ?**
  - (a) dans le dossier de données Deepotus, par une petite route `/api/photolab/espaces` : durable, couvert par
    les bancs, suit une réinstallation ;
  - (b) dans le navigateur (localStorage) : plus simple, mais perdu si les données du navigateur sont effacées.

  Recommandation : (a).
- **Q3 — Ordre des lots** : celui du tableau ci-dessus, ou monter L5 (peinture) plus haut ?
