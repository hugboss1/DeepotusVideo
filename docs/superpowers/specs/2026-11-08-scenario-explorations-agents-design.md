# Méthodes Scenario → agents de DeepotusVideo : conception (08/11/2026)

**Statut : VALIDÉ par l'utilisateur le 08/11/2026 (« Oui, valide ») : 9 agents, écran « Méthodes » + tiroirs, illustrations captures + générées, ordre M0 → M1 → M2. Tâches t433-t443.**
Relevé : `2026-11-08-scenario-explorations-releve.md`. Fiches : `assets/2026-11-08-scenario-explorations/fiches.json` (94 fiches FR/EN à nous).
Décisions déjà prises le 08/11 : les 94 explorations (avec priorité aux nouvelles) ; nos propres visuels et textes ; nos fournisseurs (fal…) et pas le Scenario MCP ; téléchargement des ZIP et PDF autorisé, pour lecture seulement.

## 1. L'idée en une phrase

Chez Scenario, une exploration = un résultat + un skill d'agent. Chez nous, ça donne :
- une **méthode** : une fiche bilingue avec ses étapes, ses contrôles, ses pièges, des exemples de demandes et une illustration à nous ;
- cette méthode est **portée par un agent métier** de l'app, qui l'exécute avec les outils déjà en place (boîtes d'`agent_boites.py`, devis par message, plafonds) ;
- la méthode est **proposée là où elle sert**, dans l'écran concerné.

On ne crée pas 94 agents mais **9 agents métier** (le classement cohérent demandé). Chacun connaît les méthodes de sa famille.

## 2. Chez eux / chez nous / décision

| Chez Scenario | Chez nous aujourd'hui | Décision |
|---|---|---|
| Galerie de 94 explorations, filtres Play/Watch/Explore/Create | rien (seul le lot t330-t346 a repris des briques) | **Écran « Méthodes »** : galerie filtrable par famille, par écran de l'app et par média, en FR et EN ; le filtre Scenario est gardé comme simple étiquette |
| Un skill ZIP par exploration, exécuté par Claude Code + Scenario MCP | agents internes (boucle maison sur l'API Claude, devis par message) et agent `mcp` (Claude Code en lecture) | **9 agents métier** (§3), dont l'invite système est construite à partir des méthodes de leur famille ; ils passent par les fournisseurs de l'app |
| Illustration, film, PDF making-of | — | **Illustration à nous** pour chaque fiche (§6) ; lien « Voir l'original chez Scenario ↗ » ; aucun média de Scenario copié |
| Exemples de prompts | — | 2 ou 3 **exemples de demandes** par fiche : un clic les envoie à l'agent, préremplis |
| Make yours ↗ | — | Bouton **« Lancer avec l'agent »** sur la fiche : il ouvre l'agent métier avec la méthode chargée |
| Skills sous MIT (45 sur 93) | — | Code et texte adaptables, avec la mention « © Scenario, licence MIT » dans le fichier repris. Les 48 autres : on reprend seulement la méthode |

## 3. Les 9 agents métier

| # | Agent (FR / EN) | Familles (nb de fiches) | Écrans hôtes | Méthodes phares (valeur) |
|---|---|---|---|---|
| A1 | **Réalisateur** / Director | previs Blender (7) + film fait par un agent dans Blender (12) | Chapitres/Épisodes, Scène Blender, Plateau 3D | one-take-many-angles, the-last-lantern, sleeping-giant, impossible-rides, grease-pencil-to-final-frame |
| A2 | **Monteur** / Editor | édition vidéo en chaîne (6) + motion design en code (5) | Montage, Quick, Son & VFX | auto-edit, alter, video-color-grade, every-scenario, change-only-x, motion-loops |
| A3 | **Directeur d'acteurs** / Casting director | personnages, jeu et voix (5) | Studio, Son & VFX (voix), Avatar live | dotties-voice, one-more-take, a-cast-of-one, babel-tavern, same-moves-new-actor |
| A4 | **Retoucheur** / Retoucher | retouche et références (4) + mode (2) | Studio, Photolab | edit-one-thing, give-each-picture-a-job, change-only-x-fashion, impossible-fitting-room |
| A5 | **Déclinaisons produit** / Product variations | produit et e-commerce (5) | Studio, Templates, Espaces de marque | same-product-every-variation, change-only-x-product, maison-vespree |
| A6 | **Publicitaire** / Ad maker | publicités et formats courts (7) | Quick, Montage, Campagnes (en relais) | content-engine, game-to-trailer, game-ua-ads, the-showroom, playable-ads |
| A7 | **Artiste 2D de jeu** / 2D game artist | assets 2D (6) + jeux 2D jouables (4) | Spritelab, Tilelab, Assets 2D | iso-cycles, wang-tiles, pixel-vfx-forge, theme-swap, crimson-tower |
| A8 | **Artiste 3D de jeu** / 3D game artist | assets 3D (10) + mondes 3D (11) + jeux 3D (5) | Studio 3D, Établi, Matières, Forge 3D, Lib3D | mech-bay, material-worlds, quarantine-07, small-worlds-real-craft, island-builder |
| A9 | **Éditeur illustré** / Picture-book editor | livre illustré et pédagogie (3) | Card Forge, Vectorlab, Templates | the-picture-book, inside-a-heartbeat |

Les 2 fiches « comparatifs de modèles » (nine-models-one-brief, image-to-3d-benchmark) ne forment pas un agent. Elles deviennent l'outil transverse **Arbitre** (§4, B6), que tous les agents peuvent appeler.

Chaque agent = une entrée dans `agent_boites` (ses boîtes) + une invite système générée depuis ses fiches + la conversation déjà en place (devis par message, plafonds, carte d'accord avant toute dépense). Aucun agent ne dépense sans carte acceptée.

## 4. Briques transverses à construire d'abord

Ce sont les manques que les trois analyses relèvent le plus souvent. Sans elles, les agents ne feraient que réciter la méthode.

| Brique | Ce qu'elle fait | Existant à étendre | Agents qui l'utilisent |
|---|---|---|---|
| B1 **Revue chiffrée** | note une sortie image/vidéo/son par la vision Claude + des mesures : dérive, sauts, silhouette (IoU), transcription, LUFS | t337 (revue d'un plan) | tous |
| B2 **Ancre d'identité** | une image approuvée (fiche personnage, packshot, master produit) dont dérivent toutes les vues ; elle est transmise en référence à chaque génération | épingles Studio, Bible des Chapitres | A1, A3, A4, A5, A7 |
| B3 **Conformer et comparer** | aligner une sortie sur sa source (taille, cadence, durée), afficher un volet avant/après, mesurer la dérive image par image | t335 (Previs→plan) | A1, A2, A4 |
| B4 **Chaîne vidéo→vidéo** | éditions successives d'une prise approuvée, une seule chose changée par étape, avec historique | t335 | A2, A4, A5 |
| B5 **Texte en code + calage sur la musique** | titres, flèches, HUD et cartons composés par l'app, jamais par le modèle ; coupes calées sur les accents mesurés d'une piste | overlays du Montage (t282), Son & VFX | A2, A6, A9 |
| B6 **Arbitre** | comparatif équitable entre modèles (même entrée, réglages par défaut, aucun tri), avec registre coût/temps | t344 (3D seulement) | tous |
| B7 **Registre coût/temps** | devis avant chaque étape payante, puis coût réel et durée notés par tâche | plafonds, dépenses réel/estimé | tous |

Les manques 3D lourds (rig facial ARKit, monde en splats, configurateur, jeux jouables, pubs jouables multi-réseaux) restent dans les fiches comme méthodes **« à venir »**. Ils ne sont pas dans les lots ci-dessous.

## 5. Où les méthodes apparaissent dans l'app

- **Écran « Méthodes »** (menu principal, à côté de la Bibliothèque) : la galerie des 94 fiches, avec recherche et filtres (famille, écran, média, « faisable aujourd'hui / à venir »).
- **Dans chaque écran hôte** : un bouton « Méthodes » dans la barre d'outils ouvre un tiroir avec les fiches de cet écran (champ `cible_app`).
- **Assistant « Demander » (F1)** : il connaît le catalogue et répond à « comment je fais un plan-séquence à plusieurs angles ? » par la fiche et l'agent qui la porte.
- **Agent `mcp`** (Claude Code) : un outil de lecture `methodes_lire` lui donne les fiches.

Une fiche « à venir » s'affiche grisée avec la mention « pas encore dans l'app » : elle ne lance aucun agent.

## 6. Illustrations

Une illustration **à nous** par fiche, au format 16:10 en WebP :
- **fiche faisable aujourd'hui** : une capture réelle de l'écran hôte qui montre le résultat (même procédé que le guide et `didacticiel-option`) ;
- **fiche « à venir »** : une image générée par l'app (fal) à partir du champ `illustration` de la fiche, dans un style maison commun aux 94 fiches. Aucun nom d'artiste ni de marque, et aucune image de Scenario en référence.

## 7. FR/EN et documentation

- Les fiches sont déjà bilingues (`titre_*`, `resume_*`). Méthode, contrôles et exemples seront traduits en EN au lot M0. Le français reste la langue de référence (règle `traduction-deepotus`). Les libellés d'interface passent par `dzT` avec un dictionnaire `i18n/methodes.json`.
- **Guide** (`guide-deepotus`) : un chapitre « Méthodes et agents métier », puis une section par agent au fil des lots.
- **Connaissance de l'assistant** (`connaissance-agent`) : un catalogue `docs/agent/catalogue/methodes.json` et une ligne dans AGENT.md. AGENT.md est plafonné à 24 000 caractères et en compte déjà 23 980 : il faudra le resserrer.
- **Mentions** : un fichier `docs/licences/scenario-mit.md` liste chaque skill MIT repris, avec le texte de la licence.

## 8. Découpage proposé (à inscrire au suivi après validation)

| Lot | Contenu | Effort |
|---|---|---|
| M0 | catalogue `methodes` (données des 94 fiches FR/EN + API de lecture) + écran « Méthodes » + tiroir par écran + `methodes_lire` + doc | M |
| M1 | briques B1, B2, B3, B7 | L |
| M2 | agent A2 Monteur + B4 + B5 (auto-edit, video-color-grade, change-only-x, motion-loops) | L |
| M3 | agent A1 Réalisateur (s'appuie sur t331-t338) | M |
| M4 | agents A4 Retoucheur + A5 Déclinaisons produit | M |
| M5 | agent A3 Directeur d'acteurs | M |
| M6 | agent A6 Publicitaire (relais vers Campagnes) | M |
| M7 | agent A7 Artiste 2D (s'appuie sur t340-t341) | M |
| M8 | agent A8 Artiste 3D (s'appuie sur t342-t344) | L |
| M9 | agent A9 Éditeur illustré + B6 Arbitre | M |
| M10 | illustrations des 94 fiches + chapitre du guide complet | M |

Chaque lot suit la routine habituelle : TDD, bancs, preuve à l'écran dans les deux langues, PR, puis installation sur accord.

## 9. Questions ouvertes

1. 9 agents métier (proposé), ou un agent par exploration ?
2. Écran « Méthodes » dans le menu principal + tiroirs par écran (proposé), ou tiroirs seulement ?
3. Illustrations : captures réelles + images générées pour les fiches « à venir » (≈ 50 images à environ 0,04 $ ≈ 2 $), ou captures seulement ?
4. Ordre : M0 → M1 → M2 (le Monteur, le plus utile pour une app vidéo), ou un autre agent en premier ?
