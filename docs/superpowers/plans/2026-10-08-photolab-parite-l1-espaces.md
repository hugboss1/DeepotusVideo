# Photolab parité L1 (t151) — espaces de travail et Fenêtre › panneaux

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` §2 (espaces de la référence, capturés le 08/10) et §2.4
> (photocraft : `apply_workspace`). Skill `parite-photolab`. Base : origin/main 36718ff6, branche
> `chantier/photolab-parite-l1`. Écran pur : aucune commande moteur ; `window.*` reste refusé au moteur.

## Décisions de l'utilisateur (08/10, Q1-Q3)

- Q1 : sept espaces fournis, aux noms courants. Dans l'ordre : Essentiel (par défaut), Base, Graphisme et web,
  Mouvement, Peinture, Photo, Pixel art.
- Q2 : les espaces de l'utilisateur sont enregistrés dans le dossier de données Deepotus, par la route
  `/api/photolab/espaces`.
- Q3 : ordre des lots libre ; t155 a été fait d'abord.

## Ce qu'on reprend, ce qu'on adapte

| Chez eux | Chez nous | Décision |
|---|---|---|
| Groupes à onglets librement déplaçables et regroupables, colonne d'icônes repliée | Quatre groupes fixes : Couleur ; Propriétés \| Ajustements ; Pinceaux (4 onglets) ; Calques \| Historique \| Navigateur. Rail d'icônes. | **Adapté** : un espace décrit l'ORDRE des groupes, leur état (ouvert ; replié = rail seulement ; masqué) et l'onglet actif de chacun. Un onglet ne change pas de groupe. |
| Barre d'outils réduite (« Outils de base ») ou sur deux colonnes (« Les indispensables ») | Barre de 20 emplacements sur deux colonnes | **Repris** : 1 ou 2 colonnes ; jeu « base » de 15 emplacements (sans Lasso, Forme d'historique, Gomme, Goutte, Sélection de tracé) |
| Disposition modifiée mémorisée par espace ; « Réinitialiser <espace actif> » | — | **Repris** |
| Nouvel espace (Nom ; capture : panneaux toujours, plus Raccourcis, Menus, Barre d'outils en option) | — | **Adapté** : Nom + case « Barre d'outils ». Raccourcis et menus viendront avec L9. |
| Supprimer l'espace (liste, Supprimer / Annuler) ; grisé sans espace personnel | — | **Repris**. Supprimer l'espace actif ramène à Essentiel. |
| Verrouiller l'espace | — | **Adapté** : les changements de disposition restent permis mais ne sont plus mémorisés (l'espace revient tel quel). |
| Sélecteur en haut à droite | — | **Repris** : liste dans la barre de menus, à droite |
| Fenêtre › <panneau> coché quand le panneau est visible ; F5 à F8 | Les 4 entrées Pinceaux de t155 ouvrent le groupe | **Repris** pour les panneaux qui existent (Couleur F6, Propriétés, Ajustements, Calques F7, Historique, Navigation, Pinceaux, Paramètres F5, Source de duplication, Préréglages d'outils, Options, Outils). Les autres restent « bientôt » jusqu'à leur lot (L3, L6). |
| Mouvement : panneau Montage (timeline) | — | **Écarté** (D9 : la vidéo reste au Montage) |

Chaque espace fourni est une adaptation de la référence (§2.2) aux groupes qui existent ; les panneaux pas encore
construits sont sautés.

## Tâches

**A — route et service (backend)**
- A1 `app/services/photolab_espaces.py` : `etat_defaut()`, `valider(obj)` (liste blanche stricte), `lire()` (fichier
  absent ou illisible → défaut), `ecrire(obj)` (atomique). Fichier : `DATA_ROOT/photolab/espaces.json`.
- A2 routes `GET /api/photolab/espaces` et `PUT /api/photolab/espaces` (400 sur un corps refusé).
- A3 banc `tests/test_photolab_espaces.py` : défaut, aller-retour, refus (clé inconnue, id ou groupe hors liste,
  onglet d'un autre groupe, nom vide ou de plus de 64 caractères, plus de 20 espaces personnels, doublon), fichier
  corrompu, écriture atomique, garde des écritures hors de la boucle locale.

**B — module pur `js/mod-espaces.js`** (QA `qa/espaces.test.mjs`)
- B1 `GROUPES`, `PANNEAUX` (window.panel.* → groupe et onglet), `ESPACES_FOURNIS` (7), `BASE_EMPLACEMENTS`.
- B2 `dispositionDe(etat, id)`, `basculerPanneau(disposition, panneau)`, `panneauCoche(disposition, panneau)`,
  `nouvelEspace(etat, nom, disposition, avecOutils)`, `supprimerEspace(etat, id)`, `reinitialiser(etat)`,
  `choisir(etat, id)`, `memoriser(etat, disposition)` (rien si verrouillé).
- B3 `decorerMenus(menus, etat, t)` : sous-menu Espace de travail reconstruit (ordre, Base, espaces personnels,
  « Réinitialiser <nom> », Supprimer inactif sans espace personnel, coches), coches de Fenêtre › <panneau>.

**C — écran**
- C1 `appliquer(disposition)` sur le DOM (ordre des sections de `#panneaux`, `hidden`, onglets, boutons du rail,
  colonnes et emplacements de `#outils`, barres) ; `capturer()` ; relecture après chaque clic de rail ou d'onglet.
- C2 sélecteur dans la barre de menus ; dialogues maison Nouvel espace et Supprimer ; `PL.actions` ; coche dans le
  rendu des menus ; raccourcis F-touches sans document.
- C3 textes fr/en (une seule traduction par texte français) ; dictionnaire assemblé régénéré.

**D — preuve** : bancs figés à mettre à jour ; mutations ; preuve 8799 (sept espaces, réinitialiser, nouveau,
supprimer, verrouiller, rechargement de la page = espace et dispositions conservés) ; fiche didactique du sélecteur ;
recompter (233 → 215 entrées de menu « bientôt »).

## Relevé d'exécution (08/10/2026)

**Bancs.**
- `test_photolab_espaces` : 51/51 (service, routes, copie JavaScript).
- QA node : séries vertes, dont la nouvelle `espaces` (62). Le banc `aide` admet l'id `pl-espace`.
- `test_photolab_textes` : 7/7. Les noms interdits sont lus dans le dictionnaire et les clés d'erreur sont écrites en
  entier, plutôt que d'ajouter des exceptions.
- Bancs Photolab et `test_i18n_l0` : verts, hors les 7 rouges d'environnement connus (identiques sur origin/main).

**Mutations** : 14 sur 14 tuées, sources restaurées et vérifiées par `cmp`.
- Écran : verrou, `completer`, masquer au lieu de replier, nom d'un espace fourni, Supprimer inactif, entrées `pl.*`
  envoyées au moteur, Fenêtre › Outils non traité, liste Pinceaux vide, raccourcis sans document.
- Pont : onglet d'un autre groupe, 21 espaces, écriture sans validation, nom « Peinture », fichier corrompu.

**Preuve sur 8799** (gestes et dialogues réels, vrai backend jetable) :
- Les 7 espaces s'appliquent : Essentiel = l'écran d'avant ; Base = 15 outils et une colonne ; Peinture = Couleur,
  Pinceaux, Calques ; Photo = Ajustements devant.
- Un repli par le rail est mémorisé par espace, conservé au changement d'espace, puis effacé par Réinitialiser.
- Nouvel espace : le vrai dialogue (Nom, case Barre d'outils) ; l'espace est enregistré sur le serveur.
- Rechargement de la page : l'espace personnel est actif, avec sa disposition.
- Le menu Fenêtre montre les coches, et le sous-menu Espace de travail son ordre (« Réinitialiser Retouche portrait »).
- Verrou : la disposition revient telle quelle. Fenêtre › Historique (clic dans le menu). F7 trois fois : ouvrir,
  masquer (le bouton du rail disparaît), rouvrir. Fenêtre › Outils : la barre se cache puis revient.
- Supprimer : le vrai dialogue, retour à Essentiel. Un nom d'espace fourni est refusé.
- Écran en anglais vérifié (sélecteur, sous-menu), puis retour au français.

**Défauts trouvés à l'écran et corrigés.**
- Un espace qui ouvrait le groupe Pinceaux laissait sa liste vide : l'onglet était déjà devant, donc aucun clic ne la
  chargeait. Corrigé par `PL.montrerPinceaux` ; épingle 7.1 et mutation M8.
- Le « ? » de l'aide du sélecteur tombait en bas à gauche de la page : le sélecteur est maintenant dans une boîte fixe.

**Recomptage** `lister_bientot.mjs` : 215 entrées de menu + 16 outils + 11 onglets + 2 boutons = 244 (262 avant).
Le panneau Montage de l'espace Mouvement est écarté (D9).

**Fiche didactique** « Espace de travail » (`pl-espace`) : l'encart s'ouvre au survol, avec l'animation de 320 px.
