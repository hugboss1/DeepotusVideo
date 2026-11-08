# Scenario Explorations — relevé à jour (08/11/2026)

Suite du relevé du 27/10 (`2026-10-27-scenario-explorations-inventaire.md`, 83 pages, lot t330-t346 livré). Demande du 08/11 : extraire illustrations, skills, exemples et descriptions, en faire des agents de l'app classés, en FR/EN, documentés.

## Comment le relevé a été fait

- Index https://www.scenario.com/explorations : **94 explorations** (Explore 29 · Watch 27 · Create 22 · Play 16). Métadonnées lues dans le JSON embarqué de la page (titre, format, industries, médias, modèles).
- Les 94 pages récupérées par `curl` en lecture seule (rendu serveur), texte extrait localement. Bandeau cookies non accepté, aucun compte, aucun formulaire.
- Avec l'accord de l'utilisateur (08/11) : **93 skills ZIP** (3,4 Mo) et **84 PDF making-of** (217 Mo) téléchargés dans le scratchpad de session, ZIP vérifiés (chemins), **rien exécuté**. Non versés dans le dépôt.
- Analyse en trois lots par sous-agents (une fiche JSON par exploration, rédigée avec nos mots), fusionnée : `assets/2026-11-08-scenario-explorations/fiches.json`.

## Droits — ce qu'on peut reprendre

| Élément | Statut | Ce qu'on fait |
|---|---|---|
| Textes, illustrations, vidéos, PDF du site | aucune licence | **rien copié** : titres, résumés, méthodes et illustrations sont À NOUS (décision utilisateur 08/11) ; lien « source » vers la page Scenario |
| Skills ZIP déclarant `license: MIT` dans leur en-tête, ou publiés dans github.com/scenario-labs/skills (MIT) | MIT (45 sur 93) | adaptation possible du code et du texte **avec la mention** « © Scenario, licence MIT » dans le fichier repris |
| Autres skills ZIP | aucune licence (48) | on retient la **méthode** (étapes, contrôles, seuils), jamais le code ni le texte |
| Moteur | Scenario MCP payant | **non** : on branche les méthodes sur nos fournisseurs (fal surtout) — décision utilisateur 08/11 |

## Écart avec le relevé du 27/10

15 explorations absentes du relevé du 27/10 : `block-or-build`, `change-only-x-fashion`, `change-only-x-product`, `content-engine`, `coral-halo`, `edit-one-thing`, `fully-rigged`, `game-ua-ads`, `kinetic-film`, `party-delivery`, `playable-ads`, `side-pocket-defaistre`, `the-corridor`, `the-showroom`, `wang-tiles`.

## Répartition

| Famille | Nb | Écrans visés le plus souvent |
|---|---|---|
| Film fabriqué par un agent dans Blender | 12 | Scène Blender, Chapitres/Épisodes, Son & VFX |
| Mondes 3D interactifs | 11 | Scène Blender, Lib3D, Studio 3D / Établi / Matières / Forge 3D |
| Assets de jeu 3D | 10 | Lib3D, Scène Blender, Forge 3D |
| Jeux jouables | 9 | Lib3D, Studio 3D, Assets 2D |
| Previs Blender → image finale | 7 | Chapitres/Épisodes, Scène Blender, Montage |
| Publicités et formats courts | 7 | Campagnes, Montage, Studio |
| Édition vidéo en chaîne | 6 | Montage, Studio, Son & VFX |
| Assets de jeu 2D | 6 | Spritelab, Assets 2D, Tilelab |
| Personnages, jeu et voix | 5 | Chapitres/Épisodes, Son & VFX, Montage |
| Produit et e-commerce | 5 | Studio, Templates, Photolab |
| Motion design en code | 5 | Montage, Templates, Son & VFX |
| Retouche et références d'image | 4 | Studio, Photolab, Chapitres/Épisodes |
| Livre illustré et pédagogie | 3 | Son & VFX, Chapitres/Épisodes, Vectorlab |
| Comparatifs de modèles | 2 | Studio 3D, Établi, Forge 3D |
| Mode | 2 | Studio, Montage, Chapitres/Épisodes |

## Les 94 fiches (titre et résumé à nous)

Valeur 1-5 pour un utilisateur de DeepotusVideo ; effort S/M/L ; « déjà » = recouvrement avec t330-t346.

### Film fabriqué par un agent dans Blender

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [sleeping-giant](https://www.scenario.com/explorations/sleeping-giant/) | Watch | Continuité entre les plans / Continuity across cuts | Court métrage où le monde ne dérive plus entre les plans : mise en place Blender, storyboards, une image approuvée servant d'ancre aux images clés animées. | 5 | M | MIT | t333 previs colorée + t338 couverture de plan : partiel |
| [last-order](https://www.scenario.com/explorations/last-order/) | Watch | Plan-séquence Blender / One-take Blender shot | Un agent construit seul un plan continu de 10 s dans Blender : enseignes lisibles, matériaux mouillés, ciel 360 et accessoires générés, avec images de test et timelapse. | 4 | L | — | t331-t332 pont Blender : partiel ; t334 passes EEVEE : partiel |
| [hold-on](https://www.scenario.com/explorations/hold-on/) | Watch | Court métrage feutrine / Felt stop-motion short | Court métrage muet en laine feutrée fait par un agent : fiches de marionnettes, guides Blender colorés, images de début et de fin par plan, animation sur deux. | 4 | M | — | t333 previs colorée + t334 passes clay : partiel |
| [hadal](https://www.scenario.com/explorations/hadal/) | Watch | Court-métrage Blender autonome / Autonomous Blender short | Un agent construit seul un film d'horreur sous-marin de 30 s dans Blender : blocage en gris, objets générés, matériaux, revue des rendus d'essai qui modifie la scène. | 4 | M | — | t331-t332 pont Blender, t334 passes, t337 revue chiffrée : partiel fort |
| [blender-2d-animation](https://www.scenario.com/explorations/blender-2d-animation/) | Explore | Animer une fois, rhabiller / Animate once, reskin | Une scène de plateforme 2D animée une seule fois dans Blender avec des cartes d'images en profondeur ; un nouveau thème ne demande qu'un nouveau jeu d'images. | 4 | M | MIT | t341 parallaxe Tilelab : partiel ; t340 boucle sprites : partiel |
| [neon-drift](https://www.scenario.com/explorations/neon-drift/) | Watch | Film de course autonome / Autonomous racing clip | Un agent seul réalise un clip de course de 15 s dans Blender : véhicule généré découpé en pièces, effets calés sur la conduite, son et revue des rendus. | 3 | L | — | t342 pièces mobiles + t331-t332 pont Blender : partiel |
| [the-corridor](https://www.scenario.com/explorations/the-corridor/) | Watch | Jouer en 3D, finir en vidéo / Block in 3D, finish in video | La performance est décidée dans un moteur 3D avec un acteur riggé corps et visage ; le modèle vidéo ne fait que finir l'image, puis réparations plan par plan. | 3 | L | MIT | t335 Previs→plan + t343 mouvement sur rig : partiel |
| [paper-harbor](https://www.scenario.com/explorations/paper-harbor/) | Watch | Diorama en papier filmé / Filmed paper diorama | Un port en papier plié construit à l'échelle miniature dans Blender, art et sons générés, puis relu par analyse d'image et corrigé par des changements mesurés. | 3 | L | — | t337 revue chiffrée : partiel ; t334 passes EEVEE : partiel |
| [pavilion](https://www.scenario.com/explorations/pavilion/) | Watch | Archviz de midi au soir / Archviz noon to dusk | Un film d'architecture en trois plans (midi, heure dorée, crépuscule) construit par un agent dans Blender, puis ré-éclairé lors d'une seconde passe ciblée. | 3 | L | — | t334 passes : partiel ; t343 mouvement sur rig : partiel |
| [lamplight-deep](https://www.scenario.com/explorations/lamplight-deep/) | Watch | Prouver un film en images clés / Prove a film in keyframes | Avant de tout rendre, un agent bâtit le monde dans Blender, finit sept images clés par IA, compose l'interface exacte et finit un seul plan animé. | 3 | M | — | t334 passes EEVEE + t335 Previs→plan + t337 revue chiffrée : largement |
| [twenty-minutes](https://www.scenario.com/explorations/twenty-minutes/) | Watch | Personnage construit en direct / Character built on camera | Un plan unique où un personnage passe du dessin au maillage, au rig, aux vêtements puis à la marche, avec une horloge qui affiche le vrai temps de fabrication. | 3 | M | — | t343 mouvement sur rig : partiel ; t335 previs→plan : partiel |
| [party-delivery](https://www.scenario.com/explorations/party-delivery/) | Watch | Rue générée dans Unreal / Generated street in Unreal | Une ruelle construite par agent dans un moteur 3D : façades plates en cartes avec cartes de matière dérivées, quelques bâtiments 3D affleurant le mur, accessoires issus de photos produit. | 2 | L | — |  |

### Mondes 3D interactifs

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [kumo-ramen](https://www.scenario.com/explorations/kumo-ramen/) | Explore | Diorama vivant en coupe / Living cutaway diorama | Une échoppe 3D en coupe, animée par personnages et machines : un asset généré par objet, casting validé avant la 3D, code pour tout ce qui doit être exact. | 3 | L | MIT | t344 comparatif image→3D : partiel ; t343 mouvement sur rig : partiel |
| [paper-city](https://www.scenario.com/explorations/paper-city/) | Explore | Théâtre de papier / Paper theatre | Un monde en papier déchiré découpé en couches générées séparément avec une référence de matière commune, empilées en parallaxe, plus vignettes animées sur fond transparent. | 3 | M | MIT | t341 parallaxe Tilelab : partiel |
| [island-builder](https://www.scenario.com/explorations/island-builder/) | Play | Ville miniature jour-nuit / Day-night toy town | Une île de bâtiments générés qui apparaissent sur des parcelles ; une clé couleur sur les vitres sombres allume les fenêtres à la tombée de la nuit. | 3 | M | — | t342 pièces mobiles + budgets de triangles : partiel |
| [celestial-orrery](https://www.scenario.com/explorations/celestial-orrery/) | Explore | Maquette scientifique artisanale / Handcrafted science model | Un modèle 3D interactif piloté par de vraies données, d'aspect fait main : l'IA produit textures, matières, fond et son ; Blender construit le mécanisme précis par script. | 2 | L | MIT | t344 comparatif image→3D + t331-t332 pont Blender : partiel |
| [last-repair-shop](https://www.scenario.com/explorations/last-repair-shop/) | Explore | Réparation pas à pas / Step-by-step repair | Une machine ouverte et réparée étape par étape dans une scène 3D interactive, construite en vraie géométrie à pièces nommées, puis refilmée dans d'autres ambiances. | 2 | L | MIT | t342 pièces mobiles : partiel |
| [open-house](https://www.scenario.com/explorations/open-house/) | Explore | Photo vers pièce praticable / Photo to walkable room | Une photo d'intérieur devient une pièce 3D où l'on marche ; les petits objets sont effacés, reconstruits en 3D avec leurs sons de chute et replacés avec physique. | 2 | L | MIT |  |
| [park-atlas](https://www.scenario.com/explorations/park-atlas/) | Explore | Lieu réel en miniature / Real place in miniature | Un lieu réel devient un monde miniature 3D dans le navigateur : plan et relief viennent de données ouvertes, l'IA ne génère que figurines, sculptures repères et matières héros. | 2 | L | MIT |  |
| [the-stones-remember](https://www.scenario.com/explorations/the-stones-remember/) | Explore | Visite historique restituée / Restored heritage visit | Visites narrées de sites historiques restitués à une date : bible sourcée, panoramas peints sur un guide à l'échelle, inscriptions issues d'une police, vue actuelle en regard. | 2 | L | — |  |
| [the-room-remembers](https://www.scenario.com/explorations/the-room-remembers/) | Explore | Une pièce, six époques / One room, six eras | Une architecture fixe meublée à six époques : chaque mobilier généré objet par objet depuis une image de style d'époque, converti en 3D et placé contre des panneaux mesurés. | 2 | L | — | t331-t332 pont Blender : partiel |
| [build-a-reef](https://www.scenario.com/explorations/build-a-reef/) | Play | Récif qui pousse / A reef that grows | Un habitat 3D jouable dans le navigateur où les coraux poussent selon des règles procédurales et où des animaux générés nagent selon des règles de déplacement. | 2 | L | — | t344 comparatif image→3D : partiel |
| [the-drifting-afternoon](https://www.scenario.com/explorations/the-drifting-afternoon/) | Explore | Diorama d'étang animé / Animated pond diorama | Un petit diorama 3D orbitable : image validée avant chaque maillage, objets séparés à budget de faces, mouvement et saisons ajoutés en code. | 2 | M | MIT | t342 budgets triangles : partiel |

### Assets de jeu 3D

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [mech-bay](https://www.scenario.com/explorations/mech-bay/) | Create | Mechs à pièces échangeables / Swappable mech parts | Un rendu de mech éclaté en planches de pièces isolées, chacune passée en 3D puis ajustée par la géométrie, pour échanger jambes, bras ou tête entre modèles. | 4 | M | MIT | t342 pièces mobiles : partiel ; t343 mouvement sur rig : partiel |
| [fully-rigged](https://www.scenario.com/explorations/fully-rigged/) | Watch | Personnage riggé complet / Fully rigged character | Chaîne de création d'un personnage de jeu en couches vérifiées : pièces séparées, corps basse définition riggé jusqu'aux doigts, visage à 52 formes ARKit, mouvements tirés de vidéos. | 3 | L | — | t343 mouvement sur rig : partiel |
| [apex-livery-studio](https://www.scenario.com/explorations/apex-livery-studio/) | Create | Livrées sur un maillage / Liveries on one mesh | Un véhicule généré une seule fois, découpé en panneaux nommés ; chaque livrée devient une fiche de données (couleurs, finitions, logos vectoriels) cuite dans un GLB à l'export. | 3 | L | MIT | t342 pièces mobiles : partiel (découpe en pièces, pas de livrée) |
| [rover-foundry](https://www.scenario.com/explorations/rover-foundry/) | Create | Configurateur de véhicule / Vehicle configurator | Un rover modulaire équipé par systèmes, habillé de finitions à trois matériaux et posé dans plusieurs mondes, exportable en image, GLB ou fichier Blender. | 3 | L | — | t342 pièces mobiles : partiel ; t346 export de recette : partiel |
| [coral-halo](https://www.scenario.com/explorations/coral-halo/) | Watch | Recaler un rig automatique / Refit an auto rig | Un personnage généré puis riggé sur le squelette standard d'Unreal voit ses articulations replacées dans son propre corps, pour que les animations du moteur ne l'étirent plus. | 3 | M | — | t343 mouvement sur rig : partiel |
| [material-worlds](https://www.scenario.com/explorations/material-worlds/) | Create | Six finitions, un modèle / Six finishes, one model | Un même modèle 3D, géométrie et UV figées, rhabillé en plusieurs finitions par textures raccordables générées par rôle de surface, avec comparateur avant/après. | 3 | M | MIT |  |
| [small-worlds-real-craft](https://www.scenario.com/explorations/small-worlds-real-craft/) | Explore | Du lourd au low poly / From heavy to low poly | Accessoires stylisés passés d'une phrase à un concept, puis à un modèle très détaillé, puis reconstruits en quelques milliers de triangles avec détail cuit en textures. | 3 | M | — | t342 pièces mobiles + budgets triangles : partiel fort |
| [quarantine-07](https://www.scenario.com/explorations/quarantine-07/) | Explore | Kits d'assets séquentiels / Sequential asset kits | Bibliothèque d'objets post-apocalyptiques cohérente : chaque design validé en image, quatre vues assorties, puis trois maillages de densités différentes, pièces mobiles séparées. | 3 | S | — | t342 pièces mobiles + budgets triangles : partiel |
| [two-rulers](https://www.scenario.com/explorations/two-rulers/) | Explore | Modéliser avec une règle / Model from a ruler | Reconstruire fidèlement un concept en 3D sans se fier aux vues dessinées : mesurer un maillage généré utilisé comme règle, ou résoudre la caméra du concept lui-même. | 2 | L | MIT | t344 comparatif image→3D : partiel |
| [saint-seiya](https://www.scenario.com/explorations/saint-seiya/) | Explore | Armure qui s'assemble / Self-assembling armour | Un personnage revêt une armure pièce par pièce au défilement : maillage armé segmenté en parties, corps nu dessous, chaque pièce volant vers sa position d'origine. | 2 | M | MIT | t342 pièces mobiles : partiel |

### Jeux jouables

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [pit-tactics](https://www.scenario.com/explorations/pit-tactics/) | Play | Kit de jeu tactique isométrique / Isometric tactics game kit | Tout l'habillage d'un jeu tactique isométrique au tour par tour : unités animées dans quatre diagonales, variantes, effets en feuilles, décors intacts et détruits, tuiles et sons. | 3 | M | — | t340 Pixel Lock + Boucle, t336/t339 Spritelab : partiel |
| [full-self-flying](https://www.scenario.com/explorations/full-self-flying/) | Play | Jeu de conduite web / Browser driving game | Un petit jeu de voiture three.js écrit par un agent autour de 24 assets générés : voiture 3D, ciel 360, sprites et décor allégés sous un mégaoctet. | 3 | M | — | t342 budgets de triangles : partiel ; t344 comparatif image→3D : partiel |
| [hibana](https://www.scenario.com/explorations/hibana/) | Play | Combattants depuis la vidéo / Fighters from video | Un jeu de combat 3D web où chaque combattant part d'une image et chaque coup d'une courte vidéo convertie en animation sur squelette. | 3 | M | — | t343 mouvement sur rig (Uthana) : partiel |
| [scroll-courier](https://www.scenario.com/explorations/scroll-courier/) | Play | Jeu pixel depuis la vidéo / Pixel game from video | Petit jeu de plateforme pixel généré : sprite verrouillé sur une grille exacte, cycles animés en vidéo puis reconstruits sur sa palette, décors en couches de parallaxe. | 3 | S | MIT | t340 Pixel Lock + t341 parallaxe Tilelab : largement |
| [graveyard-waves](https://www.scenario.com/explorations/graveyard-waves/) | Play | Jeu Roblox tout généré / Fully generated Roblox game | Un jeu de survie par vagues sur Roblox dont chaque modèle, squelette, texture, ciel, son et musique est généré, avec une porte mesurée à chaque étape. | 2 | L | MIT | t342 budgets triangles + t343 mouvement sur rig : partiel |
| [lamplighter](https://www.scenario.com/explorations/lamplighter/) | Play | Niveau 3D objet par objet / 3D level, object by object | Un niveau de jeu web en Three.js où chaque primitive est remplacée par un objet généré : un concept par objet, image→3D à budget, héros rigué, nettoyage Blender, compression. | 2 | L | MIT | t342 budgets triangles + t344 comparatif : partiel |
| [mirror-keeper](https://www.scenario.com/explorations/mirror-keeper/) | Play | Puzzle diorama en 3D / 3D diorama puzzle | Un puzzle de rayon lumineux sur plateau en diorama : style validé d'abord, un maillage par objet, règles sur grille ASCII vérifiées par un solveur. | 2 | L | MIT | t342 budgets triangles : partiel |
| [little-lights](https://www.scenario.com/explorations/little-lights/) | Play | Mini-planète légère / Lightweight tiny planet | Un jeu sur une petite planète sphérique : objets posés selon la normale, déplacements sur grands cercles, et optimisation agressive des GLB animés. | 2 | M | MIT | t342 budgets triangles : partiel |
| [side-pocket-defaistre](https://www.scenario.com/explorations/side-pocket-defaistre/) | Play | Jeu rétro marchand / Retro shoppable game | Un jeu de billard 16 bits jouable où le moteur fixe toutes les coordonnées, l'IA peint l'art pour s'y caler, et de vrais produits renvoient vers la boutique. | 1 | L | MIT |  |

### Previs Blender → image finale

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [one-take-many-angles](https://www.scenario.com/explorations/one-take-many-angles/) | Create | Une prise, treize angles / One take, thirteen angles | Une prise continue refilmée en une seule génération sous treize angles, à partir d'une étude caméra Blender et d'une liste de plans numérotée ; coupes mesurées après coup. | 5 | M | MIT | t333/t338 previs + couverture de plan : partiel ; t335 previs→plan : partiel |
| [the-last-lantern](https://www.scenario.com/explorations/the-last-lantern/) | Watch | Long film piloté par blockout / Blockout-driven long film | Film généré de deux minutes en 40 coupes : playblast gris Blender pour caméra et timing, une image finie par coupe pour le look, planches pour l'identité. | 5 | M | MIT | t333/t338 previs + couverture : partiel ; t335 previs→plan : partiel ; t337 revue chiffrée : partiel |
| [impossible-rides](https://www.scenario.com/explorations/impossible-rides/) | Create | Caméra Blender, rendu cinéma / Blender camera, cinema finish | Une étude de caméra Blender sur un véhicule devient un film réaliste ou stylisé ; une image maîtresse fixe l'identité, chaque vue dérive de son image Blender. | 4 | M | MIT | t335 Previs→plan + t331-t332 pont Blender : partiel |
| [grease-pencil-to-final-frame](https://www.scenario.com/explorations/grease-pencil-to-final-frame/) | Explore | Animatique vers image finale / Animatic to final frame | Une animatique Grease Pencil rendue dans un nouveau style par vidéo→vidéo, en gardant chaque clé à son image grâce au contournement des durées minimales et à une mesure du décalage. | 4 | S | — | t335 Previs→plan vidéo→vidéo : partiel (sans gestion des durées minimales ni mesure du décalage) |
| [block-or-build](https://www.scenario.com/explorations/block-or-build/) | Explore | Bloquer ou modéliser / Block or build | Règle de choix des doublures dans une previs Blender destinée à un modèle vidéo : modéliser ce qui doit être exact, laisser des capsules sans jambes pour ce qui marche. | 3 | S | MIT | t335 Previs→plan + t333/t338 previs colorée : partiel |
| [mirage-house](https://www.scenario.com/explorations/mirage-house/) | Create | Visite d'architecture restylée / Restyled architecture walkthrough | Une seule visite Blender en couleurs unies est restylée en huit univers visuels, même trajectoire de caméra, pour une comparaison côte à côte. | 3 | S | MIT | t335 Previs→plan : partiel |
| [previs-to-picture](https://www.scenario.com/explorations/previs-to-picture/) | Watch | Previs colorée vers image finale / Colour-coded previs to picture | Une previs Blender codée par couleurs devient un plan photoréaliste : couleurs nommées dans les prompts, images de style, passe vidéo-vers-vidéo gardant caméra et timing. | 3 | S | — | t333/t338 previs colorée + t335 Previs→plan + t337 revue chiffrée : largement |

### Publicités et formats courts

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [content-engine](https://www.scenario.com/explorations/content-engine/) | Create | Remake de format court / Short-format remake | Reprendre la mécanique d'une vidéo verticale qui marche (accroche, compteur qui monte, retournement, chute) et la remplir avec sa propre idée ; textes dessinés en code. | 5 | L | — |  |
| [game-to-trailer](https://www.scenario.com/explorations/game-to-trailer/) | Watch | Bande-annonce depuis un jeu / Game into movie trailer | Un petit jeu simple transformé en bande-annonce de film d'environ 50 s : personnages refaits en 3D, parodie de genre, un plan par image, montage calé sur une chanson unique. | 5 | M | — |  |
| [game-ua-ads](https://www.scenario.com/explorations/game-ua-ads/) | Watch | Pubs de jeu mobile / Mobile game ads | Une pub vidéo d'acquisition pour jeu mobile à durée exacte : plateau généré, prises animées, logique du jeu vérifiée et interface composée par-dessus. | 5 | M | MIT |  |
| [the-showroom](https://www.scenario.com/explorations/the-showroom/) | Watch | Pub auto montée au rythme / Beat-cut car ad | Pub auto de 30 à 45 s : voiture et interprète verrouillés en référence, une image de départ par plan, montage sur les accents mesurés d'une musique générée. | 5 | M | — |  |
| [playable-ads](https://www.scenario.com/explorations/playable-ads/) | Play | Pubs jouables HTML5 / HTML5 playable ads | Une tranche de jeu de 35 à 45 s en un seul fichier HTML, avec main d'indice, bouton muet et carte de fin, emballée et testée pour neuf régies. | 4 | L | MIT |  |
| [tap-to-install](https://www.scenario.com/explorations/tap-to-install/) | Watch | Gameplay codé pour pubs / Coded gameplay for ads | Des pubs verticales de jeux mobiles où un moteur déterministe joue le gameplay avec des sprites générés, la vidéo IA ne servant qu'aux plans peints et moments forts. | 4 | L | MIT |  |
| [fan-cam](https://www.scenario.com/explorations/fan-cam/) | Play | Supporters cachés dans la foule / Fans hidden in a crowd | Une immense photo de tribune où l'on plante une douzaine de supporters par retouches locales recollées sous masque, chacun animé en gros plan réagissant à l'écran géant. | 2 | M | MIT |  |

### Édition vidéo en chaîne

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [auto-edit](https://www.scenario.com/explorations/auto-edit/) | Watch | Montage auto du face-caméra / Talking-head auto edit | Un selfie brut devient un montage fini par instructions écrites : coupes sur les mots, texte derrière la tête, décor reconstruit, bruitages et musique calée sur le mot clé. | 5 | M | MIT |  |
| [alter](https://www.scenario.com/explorations/alter/) | Explore | Retoucher une prise filmée / Rework a filmed take | Une même prise vidéo déclinée en variantes alignées image par image : objet remplacé, acteur ou décor changé, ou rendu entièrement restylé, avec brouillon basse définition puis contrôles mesurés. | 5 | M | MIT | t335 Previs→plan vidéo→vidéo + t337 revue chiffrée : partiel |
| [video-color-grade](https://www.scenario.com/explorations/video-color-grade/) | Explore | Étalonnage en code / Colour grading in code | Étalonner une vidéo par mathématiques de couleur écrites et réglées par l'agent, cuites en LUT .cube, avec relighting, couleur sélective sous masque et bobine comparative. | 5 | S | MIT |  |
| [continuity-heist](https://www.scenario.com/explorations/continuity-heist/) | Watch | Film à embranchements / Branching film | Un court film interactif à trois choix et 27 fins, où personnages et accessoires restent cohérents grâce à des références fixes et des plans-ponts entre images réelles. | 4 | L | MIT |  |
| [green-screen-to-any-scene](https://www.scenario.com/explorations/green-screen-to-any-scene/) | Explore | Fond vert vers n'importe où / Green screen anywhere | Un sujet tourné une fois sur fond vert est détouré, posé sur plusieurs décors puis réintégré par une passe d'édition vidéo qui refait reflets, ombre et couleur. | 4 | M | — |  |
| [change-only-x](https://www.scenario.com/explorations/change-only-x/) | Create | Chaîne d'éditions vidéo / Chained video edits | Un plan de jeu modifié par éditions successives, chacune partant de la précédente et ne changeant qu'un élément ; feuilles de personnage obligatoires pour tout nouvel arrivant. | 4 | S | — | t335 Previs→plan vidéo→vidéo + t337 revue chiffrée : partiel |

### Assets de jeu 2D

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [crimson-tower](https://www.scenario.com/explorations/crimson-tower/) | Play | Kit de jeu à défilement / Side-scroller asset kit | Sprites pixel animés tirés de clips vidéo, couches de niveau pour parallaxe, texture murale rendue raccordable et sons, pour un jeu de plateforme vu de profil. | 4 | M | MIT | t340 Pixel Lock + Boucle sprites, t341 parallaxe Tilelab : partiel |
| [pixel-vfx-forge](https://www.scenario.com/explorations/pixel-vfx-forge/) | Create | Effets pixel par recette / Recipe-based pixel VFX | Effets visuels pixel (explosions, sorts, portails) décrits comme une recette en couches de chaleur découpées en bandes de couleur, rendus localement gratuitement et prévisualisés sur un personnage. | 4 | M | — | t340 Pixel Lock : voisin |
| [theme-swap](https://www.scenario.com/explorations/theme-swap/) | Play | Re-thématiser un jeu / Re-theme a game | Habiller un jeu 2D pour Halloween ou Noël en éditant chaque planche d'origine, une planche de thème en seconde référence : mises en page et collisions restent identiques. | 4 | M | — |  |
| [sketch-to-asset](https://www.scenario.com/explorations/sketch-to-asset/) | Explore | Du croquis à la carte / Sketch to card | Un croquis au crayon sert d'image de référence : le rendu garde sa pose, devient une carte de jeu à relief et matières, et un modèle 3D texturé. | 4 | M | — | t344 comparatif image→3D : partiel |
| [iso-cycles](https://www.scenario.com/explorations/iso-cycles/) | Create | Sprites huit directions / Eight-direction sprites | Feuilles de sprites isométriques marche, course, attente et attaque en huit directions : cinq angles dessinés, animés en vidéo, bouclés, pixelisés et trois directions obtenues par miroir. | 4 | S | — | t340 Pixel Lock + Boucle, t336/t339 Spritelab : largement |
| [wang-tiles](https://www.scenario.com/explorations/wang-tiles/) | Create | Sol pixel sans grille / Grid-free pixel ground | Seize tuiles de Wang à bords assortis découpées dans une seule texture pixel art générée : la répétition disparaît, exports prêts pour les moteurs. | 4 | S | — | t340 Pixel Lock : partiel |

### Personnages, jeu et voix

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [dotties-voice](https://www.scenario.com/explorations/dotties-voice/) | Watch | Diriger un court dialogué / Directing a dialogue short | Un court métrage animé avec répliques parlées : style commun du casting, décors ré-éclairés avant le mouvement, prompts minutés à la seconde et corrections ciblées. | 5 | M | MIT | t337 revue chiffrée d'un plan : partiel |
| [babel-tavern](https://www.scenario.com/explorations/babel-tavern/) | Play | Une voix, huit langues / One voice, eight languages | Des personnages parlants doublés en plusieurs langues avec la même voix et le même visage : voix verrouillée sur la première prise, jeux de mots réécrits, synchro labiale contrôlée. | 4 | L | MIT |  |
| [a-cast-of-one](https://www.scenario.com/explorations/a-cast-of-one/) | Create | Un acteur, plusieurs rôles / One performer, many roles | Une seule prise téléphone par rôle devient plusieurs personnages distincts : le corps est retransféré depuis une fiche personnage, la voix changée en gardant mots et rythme. | 4 | M | MIT |  |
| [one-more-take](https://www.scenario.com/explorations/one-more-take/) | Create | Diriger une actrice générée / Directing a generated actor | Une interprète inventée redit la même réplique sous des indications variées (langue, ton, identité, époque) ; portrait, voix et texte fixés une fois, chaque prise vérifiée par transcription. | 4 | M | MIT |  |
| [same-moves-new-actor](https://www.scenario.com/explorations/same-moves-new-actor/) | Explore | Même danse, autres acteurs / Same dance, new actors | Une chorégraphie filmée une fois par une silhouette grise neutre, puis rejouée par huit personnages dessinés, pose pour pose, chacun placé là où l'original démarre. | 4 | M | — | t335 vidéo→vidéo : partiel |

### Produit et e-commerce

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [change-only-x-product](https://www.scenario.com/explorations/change-only-x-product/) | Create | Variantes produit en chaîne / Chained product variants | Un plan produit unique est retouché plusieurs fois, une seule chose à la fois, en gardant le mouvement de caméra identique image par image pour comparer les étapes. | 4 | M | — |  |
| [same-product-every-variation](https://www.scenario.com/explorations/same-product-every-variation/) | Explore | Toutes les déclinaisons produit / Every product variant | Une photo maître par produit, puis une édition par élément changé : couleurs, matières, pierres ou verres, sans que le produit dérive, plus des essayages sur mannequins. | 4 | M | — |  |
| [bottled](https://www.scenario.com/explorations/bottled/) | Create | Flacon exact partout / Exact bottle everywhere | Lancement d'un parfum inventé où le flacon, défini en chiffres et rendu en 3D, reste identique dans chaque décor généré, avec étiquette typographiée recollée par perspective. | 3 | L | — |  |
| [one-sole](https://www.scenario.com/explorations/one-sole/) | Create | Lancement d'une chaussure / A footwear drop | Une chaussure inventée modélisée une fois en 3D, puis déclinée en coloris, matières, univers de campagne, boucles et fiches produit, toujours en éditant un rendu du modèle. | 3 | L | — |  |
| [maison-vespree](https://www.scenario.com/explorations/maison-vespree/) | Explore | Univers de marque luxe / Luxury brand world | Une maison de luxe inventée, de la bible de marque à la campagne : le produit est modélisé une fois, chaque scène est générée étiquette vierge puis l'étiquette exacte posée. | 3 | M | — |  |

### Motion design en code

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [every-scenario](https://www.scenario.com/explorations/every-scenario/) | Watch | Clip à typographie cinétique / Kinetic lyric video | Un clip musical où des plans générés restent intacts et où un moteur de code dessine textes et formes devant et derrière la chanteuse grâce à un masque de personne. | 5 | L | — |  |
| [eight-ways-to-edit](https://www.scenario.com/explorations/eight-ways-to-edit/) | Watch | Huit styles de montage / Eight editing styles | Une même matière montée selon huit grammaires (calme, cinétique, documentaire, bande-annonce, tutoriel, schéma, papier découpé, survolté), chacune réglant rythme, coupes, voix, lettrage et musique. | 4 | L | — |  |
| [kinetic-film](https://www.scenario.com/explorations/kinetic-film/) | Watch | Film typographique en code / Kinetic type film in code | Film de lancement en typographie cinétique où chaque image est calculée par une page web à partir d'une feuille de temps ; seuls musique et sons sont générés. | 4 | M | MIT |  |
| [motion-loops](https://www.scenario.com/explorations/motion-loops/) | Create | Boucles animées en code / Seamless code loops | Des fonds et animations de formes écrits en code, fonctions pures du temps sur 12 s, recolorables et vérifiés pour boucler sans couture. | 4 | S | MIT | t340 préréglage Boucle sprites : partiel |
| [one-logo-42-worlds](https://www.scenario.com/explorations/one-logo-42-worlds/) | Watch | Logo dans mille mondes / One logo, many worlds | Un logo fixe rebondit pendant que tout le décor change de style à chaque atterrissage ; image et musique synthétisée lisent la même horloge. | 3 | M | — |  |

### Retouche et références d'image

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [edit-one-thing](https://www.scenario.com/explorations/edit-one-thing/) | Watch | Retouche ciblée vérifiée / Verified single edit | Formuler une retouche d'image en une seule modification plus la liste de ce qui doit rester, puis prouver par carte des différences et superposition que rien d'autre n'a bougé. | 5 | S | — |  |
| [give-each-picture-a-job](https://www.scenario.com/explorations/give-each-picture-a-job/) | Explore | Une mission par référence / One job per reference | Composer une image à partir de quatre ou cinq références en donnant à chacune un rôle unique et en précisant ce qu'il ne faut pas lui prendre, puis l'animer. | 5 | S | — |  |
| [full-circle](https://www.scenario.com/explorations/full-circle/) | Explore | Nouveaux angles par la 3D / New angles through 3D | Une seule image vue sous 25 angles : maillage brut tiré de l'image, caméras Blender autour, puis repeinte de chaque vue en argile dans le style d'origine. | 4 | M | MIT | t334 passes clay + t331-t332 pont Blender : partiel |
| [wish-you-were-here](https://www.scenario.com/explorations/wish-you-were-here/) | Explore | Zoom infini en boucle / Looping infinite zoom | Une chaîne de photos carrées emboîtées où l'on zoome sans fin : vues rapprochées agrandies depuis le centre, vues larges peintes vers l'extérieur, cadres qui cachent les raccords. | 3 | M | MIT |  |

### Livre illustré et pédagogie

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [the-picture-book](https://www.scenario.com/explorations/the-picture-book/) | Create | Album illustré multistyle / Multi-style picture book | Un album jeunesse aux personnages constants, redessiné dans plusieurs techniques, texte composé hors image en plusieurs langues, avec lecture à voix haute contrôlée. | 4 | M | — |  |
| [inside-a-heartbeat](https://www.scenario.com/explorations/inside-a-heartbeat/) | Explore | Mécanisme expliqué par étapes / A mechanism in stages | Un battement de cœur pédagogique en six étapes et quatre couches : structure modélisée en code et vérifiée contre des sources, planches finies par IA, flèches tracées depuis le modèle. | 2 | L | — |  |
| [little-paper-voyage](https://www.scenario.com/explorations/little-paper-voyage/) | Explore | Histoire en papier défilante / Scrolling paper story | Une page-livre où le défilement promène une caméra sur des scènes en papier découpé ; personnages en pièces détachées pour rester identiques d'un acte à l'autre. | 2 | M | MIT |  |

### Comparatifs de modèles

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [nine-models-one-brief](https://www.scenario.com/explorations/nine-models-one-brief/) | Create | Comparatif image équitable / Fair image bake-off | Neuf modèles d'image, même consigne vérifiable, même entrée, une sortie chacun aux réglages par défaut, grilles non recadrées et registre de coût et de temps. | 4 | S | — | t344 comparatif (3D seulement) : principe voisin |
| [image-to-3d-benchmark](https://www.scenario.com/explorations/image-to-3d-benchmark/) | Explore | Juger un maillage 3D / Judging a 3D mesh | Comparer des modèles image→3D sur la même image en deux épreuves séparées (haute définition, budget fixe), rendus identiques en argile et mesures de triangles et de forme. | 3 | S | — | t344 comparatif image→3D : largement couvert ; t342 budgets : partiel |

### Mode

| Exploration | Filtre | Titre FR / EN | Résumé (FR) | V | E | Lic. | Déjà |
|---|---|---|---|---|---|---|---|
| [change-only-x-fashion](https://www.scenario.com/explorations/change-only-x-fashion/) | Create | Ne changer qu'une pièce / Change one piece only | Une vidéo de mode retouchée en chaîne : chaque édition vidéo→vidéo part de la précédente et ne modifie qu'un élément, mouvement et caméra restant intacts. | 4 | M | — | t337 revue chiffrée d'un plan : partiel |
| [impossible-fitting-room](https://www.scenario.com/explorations/impossible-fitting-room/) | Create | Lookbook combinatoire / Combinatorial lookbook | Un éditorial de mode en grille personne × tenue × décor : chaque image part de trois références séparées, puis marche et boucle vidéo, avec un comparatif de coût. | 4 | M | MIT |  |

## Manques de l'app qui reviennent (synthèse des trois lots)

- Revue chiffrée automatique d'une sortie (dérive, sauts, silhouette, transcription, loudness) — étendre t337 au-delà des plans.
- Image ancre / fiche personnage / packshot de référence dont dérivent toutes les vues (identité stable).
- Conformer et comparer : aligner une sortie sur sa source (taille, cadence, durée) et volet avant/après.
- Chaîne d'éditions vidéo→vidéo à partir d'une prise approuvée, une seule chose changée par étape.
- Texte, flèches, étiquettes, HUD et cartons composés en CODE, jamais dessinés par le modèle.
- Montage calé sur les accents mesurés d'une musique.
- Devis avant chaque étape payante + registre coût/temps par tâche.
- 3D : pièces nommées par segmentation, rig facial ARKit, vidéo→mouvement, export web compressé (meshopt/WebP) avec rapport de poids.
- Agent qui monte une scène Blender complète sur un brief avec boucle d'images test et revue par la vision.
