# Constat — reprendre un jeu de cartes existant jusqu'à un nouveau deck (05/11/2026)

Parcours visé : importer un lot de cartes PNG, les retoucher une par une ou toutes pareil dans le Photolab, passer
par le Vectorlab si besoin, puis envoyer le résultat comme NOUVEAU deck du Card Forge sans toucher au lot d'origine.

Relevé fait sur le code (`main` 5e80724d) et sur un backend de preuve 8799 (données jetables, aucune clé, aucune
dépense), avec le fichier réel de l'utilisateur.

## Le matériau : `DEEPOTUS_RIPPLED_PNG_FR_ONLY.zip`

- 233 Mo, 93 PNG dans `FR_originals/` + `MANIFEST.csv`. Empreinte sha256 inchangée après extraction
  (`b090fcf3…bd5e`).
- Le manifeste liste aussi 140 fichiers `EN_versions_and_corrections` qui **ne sont pas dans le zip**.
- Mesuré sur les 93 fichiers, en RGB : **89 en 1060 × 1484** (5:7 exact, 424 DPI en Poker 63,5 × 88,9 mm) et
  **4 en 977 × 1610**, plus étroites et plus hautes. Un même deck ne peut pas tenir les deux sans recadrer ces 4 cartes.
- **Cartes FINIES** : titre et sous-titre sont dans les pixels, cadre doré compris, coins noirs jusqu'au bord.
  Ce ne sont pas des illustrations à habiller.
- **53 noms sur 93 portent un accent** (`adrian_veilleur_des_âmes_fracturées.png`).
- Aucun dos dans le lot.

## Ce qui marche

| Étape | Constat |
|---|---|
| Import dans la Bibliothèque | Le champ image est `multiple`. 93 cartes en 12 s environ (0,3 s pièce), noms et accents conservés, source « import ». `GET /api/images` en 0,07 s à 93 images. |
| Lignée | Une retouche enregistrée pointe vers son original (`parent`, relation `retouche`), `/api/library/lignee/…` remonte à la racine. L'original n'est jamais écrasé : `/ouvrir` copie, `/bibliotheque` écrit un nouveau fichier. |
| Photolab, une carte au nom ASCII | Ouverture, réglage, enregistrement dans la Bibliothèque : OK. |
| Traitement par lots | `Fichier › Automatisation › Traitement par lots` existe, une image par appel, sans toucher au document actif, lignée posée. Il exige une Action enregistrée. |
| Vectorlab, une carte au nom ASCII | `?img=` crée un document à la taille de la carte, l'image y est posée : OK. |
| Card Forge, jeu pleine carte | Un deck semé par API (`format` Poker fond perdu 0, `frame.family: "none"`, `type.slots: []`, `face.seeded: true`, table `nom`/`art`/`dos`, `map` art et dos) s'ouvre avec 6 cartes accentuées, carte 1/6, 424 DPI, sans cadre. Le moteur sait donc faire : **il manque la porte d'entrée, pas le moteur**. |

## Ce qui casse

1. **Les noms accentués bloquent 53 cartes sur 93.**
   - `POST /api/photolab/ouvrir` et `/actions/lot` : 400 « nom d'image refusé » (`_NOM_IMAGE`, ASCII seul,
     `backend/app/api/photolab_routes.py:36`).
   - `frontend/shared/dz-envoi.js:14` : `nomValide` refuse aussi. « Envoyer vers › Photolab / Vectorlab / Tile Lab »
     et `?img=` ouvrent le lab **vide, sans aucun message** (prouvé sur le Vectorlab).
   - `POST /api/images/{f}/rename` réécrit les accents en `_` (`routes.py:4191`).
2. **Le nom enregistré se dégrade** quand un appel à `/bibliotheque` ne passe pas `nom` (relevé par l'API) :
   `photolab_20261105-125234_544a527f-carte_technologique_futuriste_du_japon-png.png`. L'écran du Photolab nettoie le
   nom avant l'appel : l'utilisateur n'y est pas exposé par ce chemin. `_base_sure` retire aussi les accents du nom
   enregistré ; la lignée garde le nom d'origine.
3. **Un deck neuf recouvre la carte.** `POST /decks` puis table : `seedIfEmpty` pose le cadre « arcane » et 9 emplacements
   de texte. Une carte finie disparaît sous un second cadre.

## Ce qui manque

| Besoin | État |
|---|---|
| Notion de LOT | Aucune. Les projets de la Bibliothèque (#78) s'en approchent : n:n, filtre, projet actif qui range tout. L'import n'en crée pas, et ils n'ont pas d'ordre. |
| Sélection multiple dans la Bibliothèque | Aucune (0 case, menu « Envoyer vers » à l'unité). |
| Ouvrir un lot dans le Photolab, carte suivante | Aucun. Il faut repasser par le sélecteur à chaque carte. Pas d'indication « carte 3 / 93 ». |
| Traitement par lots ciblé | La grille liste TOUTE la Bibliothèque, filtre texte seul, sans projet. Les résultats ne sont rattachés à aucun lot et l'ordre est celui des clics. |
| Vectorlab → suite du parcours | Pas d'« Envoyer vers » (`__dzEnvoyerVers` absent du lab). L'export PNG donne `vector_<doc>_1x.png` **sans parent** : la lignée est rompue et le nom d'origine perdu. |
| Card Forge depuis N images | Aucun. « Envoyer vers › Cardforge » copie `img:<nom>` dans le presse-papiers, une image à la fois. Le rail Import ne prend qu'une carte (recto/verso) pour l'analyser. La table de données passe par un CSV écrit à la main. |
| Version à retenir | Rien ne dit quelle version d'une carte entre dans le deck quand il en existe plusieurs. |
| Dos | Le frame n'accepte qu'un dos propre au deck (`img:img_N.png`). Le `card.back` par carte, lui, accepte une image de la Bibliothèque : prouvé. Il manque le geste. |
| Format | Choisi à la main ; rien ne le déduit du rapport des images. Avec un fond perdu, `cover` étend l'image jusqu'à la toile : par calcul, la coupe retire environ 3 mm de chaque bord, donc une partie du cadre doré. Non essayé à l'impression. |

## Besoins ajoutés par l'utilisateur le 05/11

- Changer les noms et le type de bordure, ou importer une bordure faite dans le Photolab ou le Vectorlab, puis
  enregistrer ce design au catalogue pour le réutiliser, par exemple pour un autre client. Aujourd'hui, le catalogue
  existe mais retire les images importées, et aucune bordure image ne se pose sur toute la carte.
- Cartes finies seules, sans illustration propre : un même cadrage extrait l'intérieur de la carte (essai jetable
  réussi sur 6 cartes, 87 restent à contrôler ; 6,2-93,8 % en largeur, 14,5-84,5 % en hauteur).
- Cartes hexagonales recto verso, reliées entre elles par des liens, pour créer des relations entre cartes ou des
  plateaux qui se forment pendant la partie. Aucune prise en charge aujourd'hui : c'est un projet distinct.

## Conclusion

Le socle est sain (lignée, lots du Photolab, rendu pleine carte du Card Forge). L'écart est celui d'un **chantier** :
un correctif de noms, plus quatre écrans à relier par une notion de lot. La conception est à valider avant de coder.
