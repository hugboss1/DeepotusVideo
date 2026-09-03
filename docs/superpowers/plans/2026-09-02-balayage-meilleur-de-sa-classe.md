# Balayage « meilleur de sa classe » — brief de la session fraîche

> **Pour l'agent qui ouvre cette session :** tu n'implémentes rien ici. Cette session
> **interroge**, catégorie par catégorie, puis **écrit des plans** (un par catégorie
> retenue, au format `superpowers:writing-plans`). L'implémentation viendra ensuite,
> par `superpowers:subagent-driven-development`, un plan à la fois.
>
> REQUIRED SUB-SKILL pour la phase d'écriture des plans : `superpowers:writing-plans`.
> Avant toute question à l'utilisateur, lis `PRODUCT.md`, `DESIGN.md` §1 et §5, et
> l'en-tête de `README.md` — c'est la vérité produit. Ce document ne la remplace pas.

**Demande de l'utilisateur, mot pour mot (02/09/2026)** : « je veux que tu me prépares
une nouvelle session toute fraîche dans laquelle nous allons effectuer un balayage
complet de l'application, catégorie par catégorie, pour lister toutes les évolutions à
prévoir pour être comparable à chaque logiciel meilleur de sa classe. tu me prépareras
un questionnaire par catégorie listant tout ce que tu connais des meilleurs logiciels
correspondant à chaque catégorie présente sur l'application, et tu commenceras à me
préparer un questionnaire pour préparer le développement de l'application mobile
compagnon de cette application pour pouvoir continuer le travail même si le pc est
éteint. »

---

## Comment mener la session — la règle du jeu

1. **Une catégorie par passe**, dans l'ordre du rail de navigation. On ne mélange pas.
2. Pour chaque catégorie : l'agent **relit ce que l'application fait aujourd'hui**
   (code, pas souvenir — `grep` les routes et les écrans), pose **le questionnaire**
   ci-dessous via `AskUserQuestion` (par lots de 4 au plus), et **consigne les
   réponses** dans une section « Réponses » ajoutée à ce fichier.
3. À la fin de chaque catégorie : une **liste d'évolutions triée en trois bacs** —
   *parité nécessaire* (sans quoi l'outil n'est pas crédible), *différenciant* (ce
   que les références ne font pas et que Deepotus peut faire parce qu'il est local,
   scriptable et multi-métier), *écarté* (et pourquoi). Pas de quatrième bac.
4. **Le mesuré prime sur le souvenir.** Si l'agent affirme qu'un logiciel de
   référence fait X, il le vérifie (documentation officielle, `WebFetch`) ou il
   écrit « de mémoire, à vérifier ». Ce dépôt a payé cher les affirmations non
   mesurées ; voir « Pièges hérités » en fin de document.
5. Le questionnaire mobile se traite **en dernier**, quand la carte des
   catégories est complète : on ne conçoit pas le compagnon d'une application dont
   on n'a pas fini de dessiner les contours.

---

## La carte de l'application, telle qu'elle est (02/09/2026)

**Rail de navigation — 11 entrées** (`DESIGN.md` §2.2) : Quick · Studio · Chapitres ·
Son & VFX · Montage · Scheduler · Templates · News · Library · Game Assets · Settings.

**Game Assets — 6 catégories teintées** (`DESIGN.md` §1.2) : 3D · 3D Studio (dont
l'Établi `/etabli`) · Sprites 2D · Tuiles · Matières · Cartes (Card Forge).

**Transverses** : la Bibliothèque unifiée (provenance, « Envoyer vers… » à dix
cibles), l'export impression 3D (STL/3MF en millimètres, `print3d`), la file de
rendu, les moteurs (fal, Meshy, Tripo, HeyGen, ElevenLabs, Anthropic/OpenAI/Gemini/
Ollama).

**Contraintes structurelles à garder en tête pour toutes les catégories** :
- application **locale**, backend FastAPI lié à `127.0.0.1:8765`, garde CSRF
  same-origin sur toute requête non-GET (`main.py`, v1.15.1) ;
- **clés API apportées par l'utilisateur**, stockées sur le PC ;
- données dans `%LOCALAPPDATA%\DeepotusVideoGenData`, indépendantes du code ;
- l'interface compilée (`frontend/dist`) est **patchée** par des scripts, pas
  rebâtie — toute évolution d'écran a un coût de patch (`README.md`, section
  « Patching the compiled UI »).

---

## Questionnaires par catégorie

Pour chaque catégorie : *aujourd'hui* (une phrase, à revérifier dans le code) ·
*références* (ce que je connais des meilleurs — **de mémoire, à vérifier avant de
s'en servir comme argument**) · *questions*.

### 1. Quick — générateurs en un coup (Seedance · HeyGen · Composition)

**Aujourd'hui** : trois formulaires 1-shot vers fal (Seedance 2.5, Nano Banana Pro…),
HeyGen (avatar) et une composition ; sortie vers la file de rendu et la Bibliothèque.

**Références** : Runway (Gen-4, image→vidéo, brosse de mouvement, caméra), Kling
(app mobile, extensions de clip, lip-sync), Luma Dream Machine (keyframes début/fin,
« boards »), Pika (effets prêts, Pikaffects), HeyGen web (avatars, traduction vidéo,
avatar IV), CapCut (modèles viraux, auto-captions, tendances), Hailuo/MiniMax
(sujet référence).

**Questions**
1. Quel est le geste Quick le plus fréquent dans ta pratique réelle : image→clip,
   avatar parlant, ou composition ? Lequel te fait encore « remplir un formulaire » ?
2. Les références offrent **début + fin** (keyframes) et **extension** d'un clip
   existant. Lequel des deux te manque le plus ?
3. Une **galerie de presets** (caméra, mouvement, style) vaut-elle mieux qu'un
   champ prompt libre ? As-tu des presets que tu retapes à chaque fois ?
4. Faut-il un **mode comparaison** (même prompt, 2–4 moteurs, coût affiché avant
   tir) ? Le prix par moteur est déjà montré : suffit-il ?
5. Sous-titres automatiques et **lip-sync** : dans Quick, ou seulement au Montage ?
6. Que fais-tu d'un résultat raté : relance, variation, ou abandon ? Y a-t-il un
   « re-roll avec la même graine » qui te manque ?

### 2. Studio — l'éditeur de nœuds

**Aujourd'hui** : graphe de nœuds (image, vidéo, audio, 3D…), templates de graphe,
preview, exécution vers la file ; `DESIGN.md` §6 en fait « la pièce centrale ».

**Références** : ComfyUI (écosystème de nœuds, sous-graphes, gestion des modèles,
file), Weavy et Flora (nœuds multimodaux « créatifs », tableau infini), Blender
(geometry nodes, compositor, groupes de nœuds), Nuke (compositing, viewer multi-
canaux), Houdini (procédural, HDA), n8n (automatisation par nœuds, erreurs par
nœud, ré-exécution partielle).

**Questions**
1. Combien de nœuds a ton plus gros graphe utile ? Y a-t-il des **sous-graphes**
   que tu recopies à la main ?
2. **Ré-exécution partielle** : quand un nœud aval change, tout se relance-t-il ?
   Est-ce un coût réel (crédits) ou seulement du temps ?
3. Le **canevas infini** façon Flora (résultats posés à côté du graphe, comparés
   côte à côte) t'attire-t-il, ou préfères-tu le graphe strict ?
4. Faut-il des **nœuds de contrôle** (boucle sur une liste, condition, seed
   variable) pour produire des séries ?
5. Que manque-t-il à la **preview** : scrub, comparaison A/B, historique des
   versions d'un nœud ?
6. Souhaites-tu **exporter un graphe** comme recette réutilisable (et l'importer
   depuis un autre poste, ou depuis le mobile) ?

### 3. Chapitres — l'écriture (bible, épisodes, script)

**Aujourd'hui** : bible/épisodes/scènes, lien vers les générateurs d'images et de
scènes (option vitrail, planches DA), « Envoyer vers Bible ».

**Références** : Final Draft et Celtx (formats de script, révisions), Sudowrite et
NovelCrafter (bible de série, mémoire des personnages, « story bible » vivante),
Notion (base relationnelle personnages ↔ lieux ↔ scènes), Boords et Storyboarder
(storyboard → animatique, timing), Milanote (murs d'inspiration).

**Questions**
1. Ta bible est-elle **relationnelle** (un personnage apparaît dans N scènes, un
   lieu a M plans) ou une suite de fiches ? Que cherches-tu et ne trouves-tu pas ?
2. Un **storyboard → animatique** (planches enchaînées avec durée et voix témoin)
   te ferait-il gagner l'aller-retour avec le Montage ?
3. La **cohérence des personnages** entre générations (référence de visage, de
   costume, de palette) est-elle tenue ? Par quel mécanisme aujourd'hui ?
4. Écris-tu d'abord le texte puis les images, ou l'inverse ? L'outil doit-il
   forcer un ordre ?
5. Faut-il un **suivi de versions** du script (qui a changé quoi, retour arrière) ?
6. Les LLM branchés (Anthropic/OpenAI/Gemini/Ollama) servent-ils au polissage, à
   la génération, ou aux deux ? Où voudrais-tu qu'ils **n'interviennent pas** ?

### 4. Son & VFX — effets, particules, musique, voix

**Aujourd'hui** : 606 SFX CC0 locaux, 12 presets de particules simulés localement,
musique par fal (Lyria 3, Stable Audio 2.5, MiniMax, CassetteAI), voix et SFX
ElevenLabs, séquences animées prêtes.

**Références** : Epidemic Sound et Artlist (recherche par ambiance/tempo/stems),
Splice (packs, recherche par similarité), ElevenLabs (SFX depuis description,
voix, isolation), Adobe Audition et Reaper (édition, réduction de bruit, ducking
automatique), EmberGen et Boris Particle Illusion (particules temps réel), Adobe
Podcast (enhance), Suno/Udio (chanson complète avec paroles).

**Questions**
1. Le **ducking automatique** (musique qui baisse sous la voix) existe-t-il au
   Montage ? Est-ce là ou dans Son & VFX qu'il doit vivre ?
2. La recherche de SFX est-elle par **famille** seulement ? Une recherche par
   **similarité sonore** ou par description a-t-elle un sens pour 606 sons ?
3. Les particules : simulation locale suffisante, ou faut-il des **VFX composés
   sur la vidéo** (fumée derrière un sujet, éclairs sur un plan) ?
4. La musique : as-tu besoin de **stems** (piste sans batterie, sans voix) pour le
   montage, ou d'un rendu final suffit-il ?
5. **Nettoyage de voix** (bruit, réverbération) avant montage : manquant ?
6. La **bibliothèque sonore** est-elle la même que la Bibliothèque générale, ou une
   vue à part ? Ce qui te gêne aujourd'hui pour retrouver un son.

### 5. Montage — la timeline

**Aujourd'hui** : timeline multi-clips, sous-titres (transcription, incrustation),
rendu ffmpeg, réception depuis les autres écrans par « Envoyer vers Montage ».

**Références** : DaVinci Resolve (montage + étalonnage + Fairlight + Fusion dans
un seul outil, gratuit), CapCut (montage court vertical, auto-captions stylées,
tendances, retouche corps/visage), Descript (montage **par le texte**, suppression
des « euh », studio sound), Premiere (multicam, proxy, Sensei), Final Cut (magnetic
timeline), Opus Clip (découpe automatique en clips viraux avec score).

**Questions**
1. Montes-tu **par le texte** (Descript) ou par la forme d'onde ? Le premier
   couvrirait-il 80 % de tes montages courts ?
2. Les **sous-titres** : styles animés façon CapCut (mot par mot, emphase) —
   parité nécessaire ou gadget ?
3. **Étalonnage** : LUT et courbes, ou rien ? Le starter catalog a déjà des LUT.
4. **Multi-format** : un montage 9:16 se rejoue-t-il en 1:1 et 16:9 par recadrage
   intelligent (suivi de sujet), ou refais-tu trois montages ?
5. **Proxy / performance** : la timeline tient-elle des clips 4K ? Combien de
   pistes réelles ?
6. Faut-il des **transitions et titres** prêts (bibliothèque), ou les templates
   spatiaux suffisent-ils ?

### 6. Scheduler — programmation et publication

**Aujourd'hui** : programmation de posts (X, Telegram), calendrier, le skill
`deepotus-comms` remplit une semaine avec porte de validation humaine.

**Références** : Buffer et Later (file par canal, meilleur horaire, aperçu par
réseau), Metricool (planning + analytics + concurrents), Hootsuite (validation en
équipe), Postiz (open source, self-hosted, multi-canaux), Typefully (X en premier,
threads, analytics), Publer (recyclage de contenu).

**Questions**
1. Quels **canaux** manquent (Instagram, YouTube Shorts, TikTok, LinkedIn) et
   lesquels acceptes-tu de publier à la main depuis le téléphone (voir mobile) ?
2. Veux-tu des **analytics** rapatriées (vues, engagement par post) pour boucler
   sur la génération ? Depuis quelles API ?
3. La **validation humaine** avant publication : par post, par lot, par semaine ?
   Sur PC seulement, ou depuis le mobile ?
4. **Recyclage** : reprogrammer automatiquement ce qui a marché ?
5. **Aperçu fidèle** par réseau (rendu tel qu'il apparaîtra) : nécessaire ?
6. Que doit-il se passer quand le PC est **éteint** à l'heure d'un post ? (Point
   central du questionnaire mobile.)

### 7. Templates — mises en page spatiales

**Aujourd'hui** : galerie de templates (ex. `tpl_news_reel`), éditeur visuel Konva,
sélection multiple façon Figma dans Card Forge.

**Références** : Canva (des milliers de modèles, « magic resize », kit de marque),
Figma (auto-layout, composants, variables), Adobe Express (modèles animés), Placeit
(mockups), Kittl (typographie décorative).

**Questions**
1. **Kit de marque** (couleurs, polices, logos, ton) appliqué en un clic à tout
   template : existe-t-il ? Où vit-il aujourd'hui (Settings ? Chapitres ?) ?
2. **Redimensionnement magique** (9:16 → 1:1 → 16:9 avec réagencement) — parité ?
3. Faut-il des **composants** (un bandeau, un lower-third) partagés entre
   templates, comme Figma ?
4. Templates **animés** (entrées/sorties de texte) ou statiques + montage ?
5. Le pont **Figma** existe pour l'import : faut-il l'inverse (exporter un
   template vers Figma) ?
6. Combien de templates utilises-tu vraiment ? Une galerie ou cinq favoris ?

### 8. News — RSS → script → reel

**Aujourd'hui** : flux RSS, résumé LLM, script « prophet », reel ; publication.

**Références** : Feedly et Inoreader (flux, filtres, dédoublonnage, IA de tri),
Opus Clip et Pictory (article/vidéo longue → clips), InVideo AI (texte → vidéo
complète avec voix et stock), Perplexity (sources citées), Google Trends et
Exploding Topics (détection de sujets montants).

**Questions**
1. Le **tri** des sources : par mot-clé, par score LLM, par tendance ? Combien
   d'articles par jour passent le filtre ?
2. Un reel News doit-il **citer ses sources** à l'écran (crédibilité) ?
3. La **voix** du « prophet » : une seule persona, ou plusieurs selon le sujet ?
4. **Détection de tendance** (sujet qui monte) : à intégrer, ou hors périmètre ?
5. De l'article au reel, où **interviens-tu** à la main aujourd'hui, et où
   voudrais-tu ne plus intervenir ?
6. Doit-on garder l'historique des reels par source pour ne pas se répéter ?

### 9. Library — la Bibliothèque unifiée

**Aujourd'hui** : table `library_assets` (provenance par fonction et moteur),
chips par catégorie, sélecteur partagé (996 vignettes, recherche, import fichier
et Figma), « Envoyer vers… » dix cibles, chip « Établi » pour les versions de
maillage.

**Références** : Eagle (tags, couleurs dominantes, collections intelligentes,
duplicatas), Adobe Bridge et Lightroom (métadonnées, notation, filtres empilés),
Frame.io (revue, commentaires temporels, versions), Bynder (DAM, droits, expiration),
Immich (reconnaissance de visages, carte, self-hosted).

**Questions**
1. **Tags libres** et **notation** (étoiles) : manquants ? Les utiliserais-tu ?
2. **Collections** (un projet = un ensemble d'assets de toutes catégories) contre
   la vue par catégorie : laquelle est ta façon de penser ?
3. **Versions** : la Bibliothèque montre-t-elle la lignée (v1 → v5, quel écran a
   produit quoi) ? La tâche 6 du plan Établi (sous-groupes sous la génération
   mère) est-elle le modèle à généraliser ?
4. **Recherche** : par nom seulement ? Par contenu (couleur, sujet, texte dans
   l'image) ?
5. **Droits et provenance externe** : quand un asset vient de Figma ou d'un
   import, faut-il retenir la licence ?
6. **Nettoyage** : doublons, assets orphelins, poids sur disque — un tableau de
   bord ?

### 10. Game Assets — six catégories

#### 10a. Sprites 2D
**Aujourd'hui** : génération de sprites, particules, feuilles de sprites, visionneuse
animée, export ZIP et pack Unity.
**Références** : Aseprite (pixel art, calques, palettes, animation par tags), Spine
et DragonBones (squelette 2D, mesh deformation), TexturePacker (atlas, trim,
formats moteur), Pixel Composer (nœuds pour sprites), Retro Diffusion et Scenario
(génération contrainte à un style de jeu).
**Questions** : palette imposée · pixel-perfect (résolution native, pas d'upscale) ·
squelette vs images-clés · atlas avec métadonnées pour Godot/Unity/Unreal ·
cohérence d'un personnage sur 8 directions · post-traitement (outline, dither).

#### 10b. Tuiles
**Aujourd'hui** : génération de tuiles (Tile Lab).
**Références** : Tiled et LDtk (éditeurs de niveaux, auto-tiling, règles), Sprite
Fusion (web), Wang tiles / blob tilesets (47 tuiles), TileMill.
**Questions** : jeux de tuiles **raccordables** (bords compatibles, Wang) · auto-
tiling avec règles exportables vers LDtk/Tiled · tuiles isométriques et hexagonales
· seamless réel testé (le banc mesure-t-il la couture ?) · variations par tuile.

#### 10c. Matières
**Aujourd'hui** : textures PBR (8 cartes), matériaux tuilés, finitions
holographiques et verre dans le graphe Forge 3D.
**Références** : Substance 3D Designer/Sampler/Painter (procédural, photo → PBR,
peinture 3D), Quixel Mixer et Megascans, Materialize (open source, photo → cartes),
ArmorPaint, Poly Haven (bibliothèque CC0).
**Questions** : photo → PBR local · aperçu sur sphère/cube avec éclairage HDRI ·
export vers Blender/Unity/Unreal avec conventions de normales (DirectX/OpenGL) ·
bibliothèque de matières de départ (Poly Haven CC0, comme Kenney pour les sons) ·
matières **procédurales** (paramètres) vs images.

#### 10d. Cartes — Card Forge
**Aujourd'hui** : éditeur de cartes, export impression 300 DPI (fond perdu, zones
sûres, traits de coupe), decks par CSV, import et mesure d'un scan, sélection
multiple façon Figma, graphe Forge 3D (relief, extrude, GLB/STL).
**Références** : nanDECK (scripts de génération de masse), Component Studio et
Dextrous (données → cartes, export imprimeur), Squib (Ruby, données → PDF),
The Game Crafter et MakePlayingCards (gabarits imprimeur, contraintes de
fabrication), Canva (mise en page rapide), Tabletop Simulator / Tabletopia
(export pour test en ligne).
**Questions** : export **imprimeur** aux gabarits des fabricants (TGC, MPC, DriveThru)
· export **Tabletop Simulator** pour tester un deck · dos de cartes et recto/verso
alignés · équilibrage (statistiques du deck) · impression maison (imposition 9 par
A4 avec repères) · localisation d'un deck (langues).

#### 10e. 3D — les moteurs image → 3D
**Aujourd'hui** : Tripo, Meshy (6/7), fal (5 moteurs), chaîne Tripo puis Meshy
(volume depuis 4 vues, texture Meshy), prix affiché avant tir.
**Références** : Meshy (retopo, rig auto, animation), Tripo (multi-vues, texture
PBR, smart low-poly), Hunyuan3D (open, local possible), Rodin / Hyper3D (haute
fidélité, quad), Luma Genie, TripoSR / InstantMesh (local, rapide, moindre qualité).
**Questions** : génération **locale** (Hunyuan3D, TripoSR) pour le brouillon
gratuit · retopologie et **quad** pour l'animation · rig auto · comparaison des
moteurs sur le même sujet (déjà partiellement fait) · low-poly pour jeu (budget
de triangles cible) · texture PBR complète vs couleur de sommet.

#### 10f. 3D Studio et l'Établi — inspecter, réparer, préparer
**Aujourd'hui** (à jour du 02/09, lots A et B de la tâche 4 livrés) : `/studio3d`
(graphe de la chaîne 3D, nœud 07 · établi), l'Établi (inspecteur : versions, A/B
caméras synchronisées, Parties par nœud/maillage/matériau, gizmo, vue
isométrique et vues d'axe, graduation et lecture x/y/z, taille cible → mm ;
**plaque façon slicer** : règles graduées sur les bords, glisser aimanté,
flèches, rotation, plan de plaque `plaque.v<N>.json` distinct du modèle ;
**poser sur une face** en un clic ; **couteau** avec aperçu par plan de coupe,
capuchons, refus nommés ; réparer l'assise, transformer, extraire), `print3d`
(STL/3MF en mm, garde 256 mm Centauri Carbon 2, relief vitrail). **Restent du
plan Établi** : T5 extraction élément par élément (consomme le plan de plaque)
et T6 Bibliothèque hiérarchique (lignée par `noeud_avant` / `noeud_apres` et
`depuis` dans les fiches). Détail et dettes nommées dans
`2026-09-01-etabli-plaque-et-extraction.md`, « Task 4 — LIVRÉE ».
**Références** : Blender (tout, mais lourd), Meshmixer (réparation, séparation de
coques, creusage, supports), MeshLab (mesure, nettoyage, décimation), Microsoft
3D Builder (réparation en un clic), Netfabb (réparation industrielle, nesting),
**OrcaSlicer / Bambu Studio / PrusaSlicer** (préparation d'impression : voir
l'inventaire des outils *Prepare* dans
`2026-09-01-etabli-plaque-et-extraction.md`, Task 4), Formware (nesting résine).
**Questions**
1. L'Établi doit-il **devenir un mini-slicer** (jusqu'à l'aperçu de tranchage), ou
   s'arrêter à la préparation et laisser Orca/Bambu trancher ? Où passe la
   frontière pour toi : couteau oui, supports non ?
2. **Réparation** : coques non fermées, normales inversées, faces dupliquées —
   un « réparer en un clic » (3D Builder) est-il attendu ?
3. **Creusage** (hollow) avec trous de drainage pour la résine, **décimation** à un
   budget de triangles : parité ?
4. **Nesting** réel sur le plateau 256 mm (plusieurs pièces, rotation optimisée) ?
5. La plaque de l'Établi doit-elle **connaître la Centauri Carbon 2** (dimensions,
   zones exclues) et d'autres imprimantes, comme les profils de slicer ?
6. Envoi **direct** au slicer (ouvrir le 3MF dans Orca/Bambu par association de
   fichier — déjà prouvé pour le 3MF) contre envoi **réseau** à l'imprimante
   (Bambu LAN mode, Elegoo) : lequel vaut l'investissement ?

### 11. Settings — clés, persona, chemins, défauts

**Aujourd'hui** : clés API (fal, HeyGen, ElevenLabs, Meshy, LLM, X/Telegram, Figma),
persona, chemins, défauts, `DATA_ROOT`.

**Références** : 1Password / Bitwarden (secrets), Raycast et VS Code (préférences
recherchables, profils), Docker Desktop (diagnostics, export de configuration),
Obsidian (coffres multiples).

**Questions** : **profils** (perso / client / test) · **export-import** de la
configuration pour un second poste (et pour le mobile) · **diagnostic** en un
écran (clés valides, crédits restants par moteur, espace disque, version) ·
**coffre** chiffré pour les clés · quotas et **plafonds de dépense** par moteur ·
sauvegarde/restauration de `DATA_ROOT`.

---

## Questionnaire — l'application mobile compagnon

**Le point de départ, mot pour mot** : « pouvoir continuer le travail même si le PC
est éteint. »

**Ce que l'architecture actuelle impose, et qu'aucune réponse ne peut ignorer** :
- le backend est lié à `127.0.0.1` et **refuse toute requête non-GET dont l'origine
  n'est pas locale** (garde CSRF, `main.py`). Un téléphone sur le même Wi-Fi ne peut
  rien lui demander aujourd'hui, et c'est **voulu** (protection des crédits) ;
- les **clés API sont sur le PC** ; les moteurs (fal, Meshy…) sont des services en
  ligne — ce n'est pas le calcul qui exige le PC, c'est la **détention des clés** et
  des **données** ;
- les rendus lourds (ffmpeg, particules, print3d) tournent **sur le PC** ;
- les données vivent dans `%LOCALAPPDATA%\DeepotusVideoGenData` (plusieurs Go).

Donc « PC éteint » ne peut vouloir dire qu'une de ces trois choses, et **la première
question du questionnaire est de choisir** :

| Lecture | Ce que le mobile fait | Ce qu'il faut construire |
|---|---|---|
| **A. Le mobile est une télécommande** | consulte, valide, programme, relance ; le PC doit être **allumé** (ou en veille réveillable) | accès distant sûr au backend (Tailscale / WireGuard / relais chiffré), Wake-on-LAN, jeton d'appareil, **assouplissement ciblé de la garde CSRF** |
| **B. Le mobile est un poste autonome léger** | génère par les moteurs en ligne avec **ses propres copies des clés**, travaille sur une **sous-bibliothèque synchronisée** | synchronisation bidirectionnelle des assets et des états, résolution de conflits, stockage sûr des clés sur le téléphone |
| **C. Un relais toujours allumé porte le travail** | le PC et le mobile sont deux clients d'un **serveur** (NAS, mini-PC, VPS, cloud) qui détient données et clés | déplacer le backend vers un hôte permanent ; le PC devient un client riche ; c'est un changement d'architecture |

**Questions — à poser dans cet ordre**

*Le besoin réel*
1. Quand le PC est éteint, que veux-tu **faire** concrètement : valider des posts ?
   relancer un rendu raté ? écrire un chapitre ? générer une image ? trier la
   Bibliothèque ? Classe ces gestes par fréquence.
2. Parmi ces gestes, lesquels doivent **aboutir sans le PC** (le résultat existe
   quand tu rentres) et lesquels peuvent **attendre** (une file qui se vide au
   réveil du PC) ?
3. Le PC peut-il rester **allumé ou en veille réveillable** (Wake-on-LAN) ? Si oui,
   la lecture A couvre-t-elle 80 % du besoin ?

*Le choix d'architecture*
4. Entre A, B et C : laquelle correspond à ta façon de travailler ? As-tu déjà un
   hôte permanent (NAS, Raspberry, VPS) ?
5. Acceptes-tu de **dupliquer tes clés API** sur le téléphone (lecture B), ou
   doivent-elles rester sur une seule machine ?
6. Acceptes-tu qu'un **service tiers** (Tailscale, un relais) soit dans la chaîne,
   ou tout doit-il rester dans ton réseau ?

*La forme*
7. **PWA** (site installable, une base de code, notifications limitées sur iOS)
   ou **application native** (React Native / Flutter / Swift, notifications
   fiables, partage depuis d'autres apps) ? Sur quel téléphone es-tu ?
8. Le compagnon doit-il **recevoir des partages** (une photo, un lien, un article
   → envoyé vers Quick, News, Bibliothèque) ? C'est souvent le premier usage réel
   d'un compagnon.
9. **Notifications** : rendu terminé, post publié, échec — lesquelles ?

*La sécurité et les crédits*
10. Une action qui **dépense** (génération) doit-elle demander une confirmation
    supplémentaire sur mobile ? Un plafond par jour ?
11. Appairage : QR code affiché par le PC → jeton d'appareil révocable ? Combien
    d'appareils ?
12. Que se passe-t-il si le téléphone est **perdu** : révocation à distance depuis
    le PC suffit-elle ?

*La synchronisation (si B ou C)*
13. Quelle **part** de la Bibliothèque doit être sur le téléphone : tout (Go), les
    vignettes + à la demande, ou une sélection épinglée ?
14. Deux modifications concurrentes (PC et mobile) sur le même chapitre : dernier
    écrit gagne, fusion, ou verrou ?

*Le périmètre du premier lot*
15. Si le premier lot ne devait faire qu'**une** chose bien : laquelle ?

**Ce que je recommande d'instruire d'abord, et pourquoi** : la lecture **A** avec
Wake-on-LAN et appairage par QR est la seule qui ne duplique ni les clés ni les
données, et elle répond aux gestes les plus probables (valider, relancer,
programmer). Elle exige **une** décision de sécurité claire — ouvrir le backend à
un appareil appairé, par un tunnel chiffré, avec jeton révocable — et rien d'autre.
Les lectures B et C sont des projets d'architecture ; qu'on ne les lance pas sans
avoir mesuré que A ne suffit pas.

---

## Pièges hérités, valables pour toute la session

- **Le souvenir n'est pas une mesure.** Les références ci-dessus sont écrites de
  mémoire ; avant d'en faire un argument de plan, vérifier la fonctionnalité sur la
  documentation officielle et écrire la date de vérification.
- **Un plan par catégorie, pas un plan-monde.** Chaque plan issu de cette session
  suit `superpowers:writing-plans` et s'exécute seul.
- **L'interface compilée se patche.** Toute évolution d'écran du bundle a un coût
  (`scripts/patch_bundle_*.py`, chaîne par mtime, `repatch_all.py`) ; les écrans
  autonomes (`/etabli`, `/studio3d`, Card Forge) sont moins chers à faire évoluer.
  Le dire dans chaque plan.
- **Les bancs-miroirs et leurs trois temps** (appris sur l'Établi, 01–02/09) : lire
  ce qui est dessiné ou écrit, jamais le code qui prétend le produire ; vérifier que
  la surface sur laquelle on lit est la vraie ; compter les assertions, pas
  seulement les noms des tests.
- **Le navigateur voit et manipule, Python écrit.** Cette règle vaut pour toute
  catégorie qui produit un fichier.

---

## Réponses et bacs, catégorie par catégorie

> Section ajoutée par la session du 02–03/09/2026. Chaque catégorie : les
> réponses de l'utilisateur telles quelles, les références **vérifiées** (avec
> la date et la source) ou marquées « de mémoire », puis les trois bacs.

### R1. Quick — réponses (02–03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 02/09 : `routes.py`,
`fal_service.py` VIDEO_MODELS, `schemas.py` GenerateRequest, bundle `um`) :
quatre onglets (Seedance, HeyGen, Composition, Voice Over) ; 11 modèles
image → clip au registre (Seedance 1.0 Pro, 2.0, 2.0 Fast, 2.5, Kling v3 Pro et
Standard, PixVerse v6, Veo 3.1 ×4) avec prix estimé avant tir ; image de fin
acceptée par 6 modèles sur 11, graine par 3 sur 11 ; durée 3–60 s avec
allongement ffmpeg (boucle/gel) au-delà du natif ; listes fermées 3 styles,
11 caméras, 8 lumières + templates et constructeur de prompt ; presets
sauvegardables pour HeyGen seulement (`/heygen/presets`) ; lot de 1 à 8
variations sur UN modèle ; `source_graph` conservé pour « Reopen in Studio ».
Absents : extension générative d'un clip, lip-sync, sous-titres dans Quick
(ils vivent au Montage).

**Réponses**
1. Geste le plus fréquent : **image → clip**.
2. Début + fin : existe mais **mal exposé** ; extension générative : **absente**.
   Les deux manquent.
3. Presets : **galerie visuelle ET presets personnels** sauvegardables.
4. Comparaison multi-moteurs : **oui, mais au Studio** (pas dans Quick).
5. Sous-titres et lip-sync : **les deux dans Quick** (le clip sort prêt à poster).
6. Résultat raté : **je varie le prompt ou le modèle** — repartir du formulaire
   prérempli, pas rejouer à l'identique.
7. « Formulaire » : **les quatre onglets** le font encore ressentir.
8. Mouvement : **caméra chiffrée ET brosse de mouvement** souhaitées.

**Références vérifiées le 03/09/2026**
- Runway : la Motion Brush était **réservée à Gen-2**, retiré le 11 mai 2025 ;
  le contrôle caméra chiffré (gauche/droite, haut/bas, pan, tilt, roll, zoom)
  était **Gen-3 Alpha Turbo**, retiré le 30 juillet 2026 ; Gen-4 et Gen-4.5
  pilotent la caméra **par le prompt** (help.runwayml.com, résultats de
  recherche du 03/09 — les pages détaillées refusent la lecture automatique,
  HTTP 403). Le « Runway fait X » du brief est donc périmé.
- Kling (application) : Motion Brush jusqu'à **6 éléments** avec trajectoire
  dessinée + Static Brush ; contrôle caméra par « commandes absolues » sur
  6 axes (horizontal, vertical, zoom, pan, tilt, roll) + 4 master shots
  (kling.ai/quickstart, 03/09). Version de modèle et accès API : **non
  précisés** sur ces pages.
- fal, Kling v3 Pro image-to-video : `start_image_url`, `end_image_url`,
  `duration` 3–15, `elements` (références @Element), `shot_type`,
  `negative_prompt`, `cfg_scale`, `generate_audio` ; **pas** de
  `camera_control`, **pas** de `dynamic_masks`, **pas** de `seed` (fal.ai,
  03/09). Via fal, la brosse et la caméra chiffrée de Kling sont donc hors de
  portée aujourd'hui.
- fal, Veo 3.1 extend-video (et Fast) : `video_url` source **≤ 8 s** en
  720p/1080p, 16:9 ou 9:16 ; `prompt` ; extension 7 s par défaut ; audio
  généré par défaut (fal.ai, 03/09). `veo-3.1-fast-fal` est déjà au registre.
- fal, lip-sync : Kling LipSync audio-to-video (vidéo 2–10 s, audio 2–60 s,
  0,014 $/s), Sync Lipsync v2 (3 $/min) et v3, LatentSync (0,2 $ jusqu'à
  40 s), MuseTalk, veed/lipsync (fal.ai, 03/09).

**Bacs**

*Parité nécessaire*
- **P1 — Rouvrir dans Quick, prérempli.** Depuis la file et la Bibliothèque :
  image, prompt, modèle, paramètres rechargés dans l'onglet d'origine, prêts
  à varier (réponse 6). Le mécanisme existe pour le Studio (`source_graph`) ;
  Quick doit conserver sa propre recette de rendu.
- **P2 — Extension générative d'un clip.** Route `/generate/extend` sur
  Veo 3.1 extend-video (fal), depuis un rendu ; source ≤ 8 s (le refus dit
  pourquoi), prix avant tir, résultat dans la file et la Bibliothèque avec
  lignée vers le clip d'origine.
- **P3 — Image de fin exposée.** La DropZone « fin » de DESIGN §8.1, visible,
  grisée avec la raison quand le modèle ne l'accepte pas (5 modèles sur 11).
- **P4 — Sous-titres dans Quick.** Case « sous-titrer » qui enchaîne la
  transcription et l'incrustation existantes (`subtitle_service`) sur le
  rendu Quick, preset choisi dans la même liste que le Montage.
- **P5 — Lip-sync dans Quick.** Quand une voix off est jointe, option
  lip-sync fal (Kling LipSync par défaut, coût 0,014 $/s ajouté à l'estimé) ;
  le clip source doit tenir dans 2–10 s, le refus le dit.
- **P6 — Presets personnels sur les quatre onglets.** Généraliser
  `/heygen/presets` : enregistrer et rappeler un jeu complet (modèle, durée,
  caméra, lumière, prompt, voix).

*Différenciant*
- **D1 — Galerie visuelle de mouvements et de styles**, rendue UNE fois et
  localement : 11 caméras × 3 styles sur une image de marque, vignettes
  cliquables avant d'écrire ; aucune référence en ligne ne le fait sur les
  presets de l'utilisateur.
- **D2 — Curseurs caméra chiffrés traduits en prompt** pour tous les moteurs
  (Veo, Seedance, Kling via fal n'ont que le texte) : un même réglage
  pan/tilt/zoom devient la phrase caméra adaptée au modèle ; si l'API Kling
  directe entre un jour au registre, les mêmes curseurs alimentent
  `camera_control`.
- **D3 — Les quatre onglets en « studio »** selon DESIGN §8.1 (source à
  gauche 360 px, preview au centre, coût et Générer collés en bas) — à
  chiffrer onglet par onglet, car chacun est un patch du bundle.

*Écarté*
- **E1 — Comparaison multi-moteurs dans Quick** : voulue au Studio → traitée
  dans la catégorie Studio.
- **E2 — Re-roll à graine fixe** : 3 modèles sur 11 acceptent une graine et
  le geste réel est varier, pas rejouer.
- **E3 — Brosse de mouvement** : aucun accès via fal (mesuré), Runway l'a
  retirée ; revient à l'ordre du jour seulement si l'API Kling directe (clé
  séparée) est branchée.

**Coût de patch** : Quick vit dans le bundle (`um`) — P1, P3, P4, P5, P6, D1,
D2, D3 sont des patches `patch_bundle_*` chaînés ; P2 est surtout backend
(route + registre) plus un bouton sur la carte de rendu.

### R2. Studio — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : bundle — registre des
nœuds, compilateur `Mh` ; `routes.py` `/studio-graphs` ; `pipeline.py`) :
34 types de nœuds en 8 catégories (source, gen, edit, compose, audio, motion,
master, output) ; **un run = un job** — le compilateur exige un nœud Render et
compile tout le graphe en une seule soumission, sans cache par nœud ; réutiliser
un résultat passe par le nœud « Rendu existant », à la main ; graphes
sauvegardés en JSON serveur (liste, charger, enregistrer, supprimer), export
JSON, **pas d'import** ; état de travail conservé en session seulement
(`keepstate`) ; undo/redo, dock des nœuds par `/`, teinte par catégorie, ports
typés ; « Rouvrir dans Studio » recharge le `source_graph` d'un rendu ;
« Envoyer vers » pose une image en nœud Image ou un template en fond de
Spatial compose. Absents : sous-graphes, mini-map, lasso, nœuds de contrôle,
comparaison, historique par nœud.

**Réponses**
1. Taille : **moins de 10 nœuds**, pas de motif répété → sous-graphes inutiles.
2. Ré-exécution : **oui, des crédits perdus régulièrement** — un changement de
   finition repaie les générations amont.
3. Canevas : **graphe strict + panneau de comparaison** (pas de canevas infini).
4. Nœuds de contrôle : **non**, Variations et lot suffisent.
5. Preview : **scrub image par image, A/B de deux rendus, historique des rendus
   par nœud** — les trois.
6. Recette : **oui, import JSON + lancement paramétré** (nouvelles sources,
   depuis un autre écran ou le mobile).
7. Comparaison : **deux moteurs en bascule** (champion contre challenger).
8. Départ : **depuis un rendu ou une image de la Bibliothèque**, pas une
   galerie de recettes.

**Références vérifiées le 03/09/2026**
- ComfyUI : met en cache les sorties et ne ré-exécute que les nœuds dont une
  entrée ou un réglage a changé, en remontant depuis les nœuds de sortie ;
  un nœud peut redéfinir `IS_CHANGED` (docs.comfy.org, 03/09).
- n8n : exécutions partielles (« Execute step » exécute un nœud et les nœuds
  amont nécessaires) ; **épinglage des données** — la sortie d'un nœud est
  figée et substituée aux runs suivants au lieu de rappeler le service ;
  rechargement des données d'une exécution passée (docs.n8n.io, 03/09).
- Flora / Weavy (canevas infini) : de mémoire, non vérifié — écarté par la
  réponse 3, donc sans objet.

**Bacs**

*Parité nécessaire*
- **P1 — Épinglage du résultat d'un nœud de génération** (le mécanisme n8n,
  l'effet ComfyUI) : un nœud Seedance/HeyGen/ImageGen dont le résultat existe
  garde ce résultat tant que ses entrées et réglages n'ont pas changé ; le
  run suivant ne repaie que ce qui a bougé. Le bouton « épingler » figé à la
  main et l'indicateur « ce run coûte X (Y nœuds réutilisés) » avant tir.
  C'est la réponse à la perte de crédits (réponse 2). Backend : un job par
  nœud de génération, ou une empreinte des entrées stockée avec le rendu.
- **P2 — Historique des rendus par nœud** : la pile des résultats passés d'un
  nœud, choisir lequel alimente l'aval (réponse 5) ; s'appuie sur P1.
- **P3 — Import d'un graphe JSON** (l'export existe déjà) avec validation
  contre le registre des nœuds et remontée des sources manquantes.
- **P4 — Scrub image par image** dans la preview (le lecteur actuel lit, ne
  parcourt pas).

*Différenciant*
- **D1 — Recette lançable** : un graphe sauvegardé exposé comme recette dont
  seules les sources changent ; route « lancer la recette N avec ces assets »,
  appelable depuis la Bibliothèque, Quick, et le mobile (lecture A). Aucune
  référence de nœuds ne le fait vers un téléphone ; n8n le fait vers des
  webhooks, pas vers des médias.
- **D2 — Duel de moteurs** : un nœud de génération marqué « duel » tire sur
  deux modèles ; panneau de comparaison en bascule A/B avec coût réel et durée
  de chacun ; le gagnant devient le résultat épinglé (P1).
- **D3 — Départ depuis un rendu** : « Envoyer vers Studio » un rendu de la
  Bibliothèque pose un nœud Rendu existant dans un graphe neuf (l'image et le
  template le font déjà ; le rendu ne fait que rouvrir son graphe source).

*Écarté*
- **E1 — Sous-graphes et groupes** : graphes < 10 nœuds, aucun motif répété.
- **E2 — Canevas infini** façon Flora/Weavy : préférence pour le graphe strict.
- **E3 — Nœuds de contrôle (boucle, condition, variables)** : Variations et
  lot suffisent.
- **E4 — Comparaison à N > 2 moteurs** : le duel suffit ; le lot Quick reste
  là pour les variations d'un même moteur.

**Coût de patch** : tout le Studio vit dans le bundle (registre des nœuds,
`Mh`, panneau droit) — P1, P2, P4, D2, D3 sont des patches chaînés lourds
(P1 touche aussi `pipeline.py` et le modèle de job) ; P3 et D1 sont surtout
backend (`/studio-graphs` : import validé, route de lancement) plus un
bouton.

### R3. Chapitres — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `routes.py` — `/bible`,
`/chapters`, `/shots`, `/scenes`, `/episodes` ; `manuscript_agent.py`,
`board_service.py`, `shotcraft_service.py`, `image_providers.py`) : bible
d'entités de 6 sortes (personnage, lieu, objet, date, ambiance, décor) ;
ingestion d'un manuscrit en 4 passes LLM (découpe, extraction, consolidation
des alias, surlignage des mentions par chapitre) ; planche de référence
composite par entité — panneaux générés un à un, identité tenue par chaînage
Kontext, graine par panneau donc recette rejouable ; modèle 3D par entité ;
casting de voix suggéré. Chapitres : découpe en plans (LLM ou paragraphe)
avec le catalogue de 106 fiches motion-design, croquis FLUX par plan,
insertion, réordonnancement, scénario Fountain exporté, adaptation roman →
scénario, voix off par scène et par chapitre. Épisodes : import txt/docx/pdf,
découpe en scènes, rendu narré illustré (voix par scène + Ken Burns).
Nano Banana Pro est appelé avec **une seule** image de référence
(`image_urls: [image_url]`). Absents : lien plan ↔ entités, animatique depuis
les plans, versions du texte, réécriture à la demande, import Fountain/FDX,
exports docx/PDF, PDF du storyboard.

**Réponses**
1. Bible : **relationnelle** — personnage ↔ plans ↔ lieux ; chaque plan sait
   qui et où, la fiche liste ses apparitions et ses planches.
2. Animatique : **oui, depuis les plans du storyboard** (croquis + durée +
   voix témoin, avant toute génération payante).
3. Cohérence : **non, même les images dérivent** (visage, costume, palette).
4. Ordre : **les deux selon le projet**, aucun ordre imposé.
5. Versions : **oui, instantanés + retour arrière** à chaque passe LLM ou
   édition manuelle.
6. LLM : **polissage/réécriture à la demande** et **génération de scènes ou
   de dialogues** souhaités ; aucune zone interdite déclarée.
7. Sortie : **les quatre** — épisodes narrés 9:16, plans vidéo montés en film,
   le manuscrit lui-même (livre), reels courts.
8. Formats : **import Fountain/FDX, export docx/PDF mis en page, PDF du
   storyboard** — les trois.

**Références vérifiées le 03/09/2026**
- NovelCrafter, Codex : indexation automatique de chaque mention (nom,
  alias, pluriels), carte des mentions par entrée, liste d'exclusion et
  casse, champs personnalisés, « progressions » dans le temps
  (docs.novelcrafter.com, 03/09). L'application a déjà les mentions et les
  alias ; il lui manque le lien aux plans et les progressions.
- Boords, animatique : durée par image réglée sur une timeline, voix off
  téléversée (WAV/MP4, 20 Mo max) qui fixe la durée, export MP4 et PDF,
  champs de texte en sous-titres, plugin After Effects (boords.com,
  help.boords.com, 03/09).
- fal, Veo 3.1 reference-to-video : **1 à 9 images de référence** pour la
  constance du sujet, aussi sur Veo 3.1 Fast (fal.ai, 03/09). fal, Kling v3
  Pro : `elements` (références image/vidéo nommées @Element dans le prompt),
  vérifié en R1. fal, Nano Banana Pro : `image_urls` accepte plusieurs
  images ; l'application n'en passe qu'une (mesuré dans le code).
- Sudowrite, Final Draft, Celtx : de mémoire, non vérifiés — non utilisés
  comme argument.

**Bacs**

*Parité nécessaire*
- **P1 — Bible relationnelle** : table plan ↔ entités (qui, où, quoi) remplie
  par la découpe LLM (elle connaît déjà les entités du chapitre) et éditable
  à la main ; sur la fiche : apparitions par chapitre et par plan, planches,
  voix. Les mentions dans le texte existent, on les prolonge aux plans.
- **P2 — Versions du texte** : instantané automatique avant chaque passe LLM
  (adaptation, découpe, réécriture) et à chaque enregistrement manuel ;
  comparaison côte à côte et restauration. Table de versions par chapitre et
  par scène, jamais d'écrasement silencieux.
- **P3 — Cohérence multi-références** : passer à Nano Banana Pro **toutes**
  les vues de la planche (face, profil, corps, palette) au lieu d'une ; pour
  la vidéo, Veo 3.1 reference-to-video (jusqu'à 9 images) et les `elements`
  de Kling v3 ; mesurer la dérive avec un banc (distance d'identité entre le
  plan généré et la planche), pas au ressenti.
- **P4 — Animatique depuis les plans** : croquis (ou image) + durée par plan
  + voix témoin ElevenLabs → MP4 9:16 par ffmpeg, avant toute génération
  payante ; le rendu d'épisode existant fournit la mécanique (image fixe +
  voix + concaténation).
- **P5 — Import Fountain et FDX** : Fountain est un format texte à
  spécification publique ; FDX est le XML de Final Draft — un parseur pour
  chacun vers scènes et dialogues.
- **P6 — Exports docx/PDF du chapitre et du scénario, PDF du storyboard**
  (croquis, durée, fiche de plan, notes) : mise en page par code, comme
  l'export impression de Card Forge.

*Différenciant*
- **D1 — Réécriture et génération à la demande, dans le ton de la bible** :
  sélection → reformuler, resserrer, traduire, proposer une scène ou un
  dialogue, avec la bible et la persona injectées ; chaque passe crée une
  version (P2) et se refuse à écraser. Aucune référence ne relie la
  réécriture à une bible visuelle **et** à un casting de voix.
- **D2 — Un chapitre, quatre sorties** : épisode narré, film de plans, reel
  court, livre — depuis la même bible et le même storyboard ; la sortie
  « reel » découpe un extrait de 15–60 s avec ses plans déjà générés.
- **D3 — L'animatique s'ouvre au Montage** : chaque plan de l'animatique
  devient un clip de la timeline ; un plan généré remplace son croquis sans
  perdre le timing (le nœud de « Rendu existant » et la lignée de la
  Bibliothèque y servent).

*Écarté*
- **E1 — Ordre imposé texte → image ou image → texte** : réponse 4.
- **E2 — Zones interdites aux LLM** : aucune déclarée ; la garde est la
  version (P2), pas l'interdiction.
- **E3 — Progressions façon NovelCrafter** (évolution d'un personnage dans
  le temps) : non demandées ; la bible relationnelle (P1) suffit d'abord.

**Coût de patch** : Chapitres est un écran du bundle — P1 (fiche, plans),
P2 (comparaison), P4 (bouton animatique), D1 (menu de sélection) sont des
patches chaînés ; P3, P5, P6 et le moteur de D2 sont surtout backend
(services image, parseurs, exports par code).

### R4. Son & VFX — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `routes.py` `/audio/*`,
`/particles`, `/effects`, `/animate` ; `sfx_service.py`, `music_service.py`,
`particle_service.py`, `effects_engine.py`, `voice_providers.py`,
`montage_service.py` ; patches `sonvfx`, `sfxstudio`, `vfxrack`) : 606 SFX
CC0 par famille, recherche libre sur libellé FR et radical EN, génération
ElevenLabs 1–4 variations avec tags sidecar, tiroir Sons, rack audio par
clip au Montage (filtre, eq3, débruitage, dé-esseur, compresseur,
distorsion) et mesure de niveau ; 4 modèles de musique fal (Lyria 3 30 s
fixes 0,10 $ ; Stable Audio 2.5 5–190 s, graine, 0,06 $ ; MiniMax Music 2.6
paroles + instrumental 0,14 $ ; CassetteAI 5–180 s 0,04 $), écoute avant
achat ; voix ElevenLabs ou Voicebox local (Kokoro, Chatterbox) ; **ducking
auto déjà au Montage** (sidechaincompress, réglable) ; 12 presets de
particules simulés localement en sorties sprites ; nœud Animation (éléments
animés composités sur un clip) ; moteur Effets/Masque (LUT, filtres ffmpeg)
et rack VFX au Montage (catégories, recherche, favoris, vignette d'aperçu,
pile par clip, bornes t0/t1, rampe) ; puce Audio dans la Bibliothèque.
Absents : stems, isolation de voix, recherche par description ou similarité,
VFX derrière un sujet, chanson chantée exposée, clonage rattaché à la bible,
direction d'interprétation.

**Réponses**
1. Ducking : **aussi dans Son & VFX et Quick** (dès qu'une voix et une
   musique sont générées ensemble).
2. Recherche SFX : **description libre ET similarité sonore**.
3. VFX : **derrière ou devant un sujet détouré** (masque vidéo).
4. Stems : **oui, séparer une piste en stems**.
5. Voix : **isolation IA ET chaîne « améliorer » en un clic**.
6. Bibliothèque sonore : **le tiroir Sons doit être la vue de référence**
   (pré-écoute au survol, forme d'onde, tags, favoris) ; la puce Audio de
   la Bibliothèque est trop pauvre.
7. Chanson : **oui, avec paroles chantées** (éditeur de paroles structurées,
   persona).
8. Voix IA : **clonage rattaché à une entité, voix par personnage reprise
   automatiquement par le storyboard, direction d'interprétation** — les
   trois.

**Références vérifiées le 03/09/2026**
- fal, Demucs (`fal-ai/demucs`) : stems vocals, drums, bass, other, guitar,
  piano (modèle htdemucs_6s), choix des stems, sortie MP3 (fal.ai, 03/09).
- fal, BiRefNet v2 vidéo (`fal-ai/birefnet/v2/video`) : détourage vidéo,
  modèles General/Matting/Portrait, entrées mp4/mov/webm, sorties mp4, webm
  VP9, **ProRes 4444 (alpha)**, gif (fal.ai, 03/09). L'app a déjà BiRefNet
  image dans le nœud RemoveBG.
- ElevenLabs, Audio Isolation (`/v1/audio-isolation`) : voix extraite du
  fond (musique, réverbération, ambiance), fichiers ≤ 500 Mo et 1 h,
  facturé 1 000 caractères par minute (elevenlabs.io, 03/09).
- ElevenLabs, Eleven v3 audio tags : balises inline `[excited]`, `[whispers]`,
  `[pause]`, `[laughs]`…, utilisables avec les clones instantanés et
  professionnels ; API publique v3 disponible ; clonage instantané à partir
  de 1–2 min d'audio propre (elevenlabs.io, 03/09).
- fal, chanson avec paroles : MiniMax Music 2.0 (0,03 $/génération, paroles
  jusqu'à 3 000 caractères), MiniMax Music 3 (jusqu'à 5 min), ACE-Step
  (0,0002 $/s, `[verse]`/`[chorus]`/`[bridge]`, `[inst]` pour instrumental),
  DiffRhythm (paroles horodatées) (fal.ai, 03/09). MiniMax 2.6 est déjà au
  registre avec `lyrics: True`.
- CLAP (LAION, `laion/clap-htsat-unfused`) : embeddings texte ↔ audio pour
  la recherche par description et par similarité (huggingface.co, 03/09).
  **Contrainte** : modèle local = PyTorch/numpy, absents du Python embarqué
  (mémoire du 02/09) ; à servir par un service optionnel ou par un endpoint
  distant, pas dans le backend stdlib.
- Epidemic, Artlist, Splice, EmberGen, Adobe Podcast : de mémoire, non
  vérifiés — non utilisés comme argument.

**Bacs**

*Parité nécessaire*
- **P1 — Stems par Demucs (fal)** : bouton « séparer » sur une musique de
  la Bibliothèque → N pistes rangées avec lignée ; au Montage, chaque stem
  est une piste audio à volume propre.
- **P2 — Isolation de voix ElevenLabs** + **chaîne « améliorer »** préréglée
  (débruitage → eq → compresseur → normalisation, filtres ffmpeg déjà dans le
  rack) en un clic sur un clip ou une voix importée ; coût affiché pour
  l'isolation, gratuit pour la chaîne.
- **P3 — Le tiroir Sons comme vue de référence** : pré-écoute au survol,
  forme d'onde, tags éditables, favoris, filtre « mes sons / catalogue »,
  tri par date ; la puce Audio de la Bibliothèque s'y aligne.
- **P4 — Chanson chantée** : exposer les paroles structurées de MiniMax 2.6
  (déjà `lyrics: True`) avec un éditeur `[Verse]`/`[Chorus]` et la persona ;
  ajouter ACE-Step (le moins cher) et MiniMax Music 3 (jusqu'à 5 min) au
  registre `MUSIC_MODELS`, prix avant tir.
- **P5 — Direction d'interprétation** : balises Eleven v3 dans le champ
  de voix off (palette de balises cliquables, aperçu du texte balisé) ;
  Voicebox n'en a pas — le dire.

*Différenciant*
- **D1 — Ducking dès la génération** : dans Son & VFX et Quick, quand une
  voix et une musique sortent ensemble, le mix ducké est rendu (mécanique
  du Montage réutilisée) et pré-écouté sans timeline.
- **D2 — VFX derrière un sujet** : BiRefNet vidéo → matte alpha (ProRes
  4444), puis l'effet ou les particules se composent entre le fond et le
  sujet dans le rack VFX ; coût fal affiché ; le nœud RemoveBG image montre
  la voie.
- **D3 — Recherche par description et similarité** : index CLAP des 606 sons
  + générations, calculé une fois ; deux voies possibles — service local
  optionnel (Python complet, comme Voicebox) ou endpoint distant ; requête
  texte ou « comme celui-ci » ; le tiroir Sons affiche les voisins.
- **D4 — Voix par personnage, bout en bout** : clonage instantané
  ElevenLabs (ou Voicebox local) rattaché à l'entité de la bible ; le
  storyboard reprend la voix de chaque personnage plan par plan ; les
  balises v3 se règlent par personnage (tempérament par défaut).

*Écarté*
- **E1 — Génération de particules par IA** : la simulation locale gratuite
  fait le travail ; rien à payer.
- **E2 — VFX vidéo → vidéo par modèle (Kling O1, Runway)** : la voie masque
  + composition (D2) répond au besoin déclaré, moins chère et contrôlable.
- **E3 — Recherche par similarité SANS description** : les deux vont
  ensemble (même index CLAP), pas de bac séparé.

**Coût de patch** : le tiroir Sons et le rack VFX sont des couches injectées
(`frontend/patches/sfxstudio.js`, `vfxrack.js`) — moins chères que le bundle
minifié : P3, D1, D2 (rack), D3 (tiroir) s'y font ; P1, P2, P4, P5 sont des
routes + registres backend avec un bouton ; D4 touche Chapitres (bundle).

### R5. Montage — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `montage_service.py`,
`subtitle_service.py`, `transcribe_service.py`, `subtitle_ui.py`, routes
`/api/montage/*` et `/subtitles/*` ; `frontend/patches/son-vfx-montage.js`
4 871 lignes, `vfxrack.js`, patch `subs`) : 5 pistes fixes (V2 overlay/VFX,
V1 vidéo, A1 dialogue, A2 musique, A3 sfx) + S1 sous-titres ; canevas unique
par montage parmi 9:16, 16:9, 1:1, 4:5 ; 9 transitions xfade (cut, fondu,
dissolve, noir, glitch, slide, flash…) ; preview 480p gratuite, final 1080p ;
gains, fondus, automation de volume, ducking, « maître de durée » ; V2 :
overlays vidéo/image posés à leur position avec transformation ; S1 : 9
styles sur fontes embarquées, karaoké `\k` par mot gravé par libass,
transcription payante ou **calage gratuit du texte connu** sur l'audio,
vérificateur de lisibilité, import/export SRT ; rack VFX avec LUT ; une
seule sauvegarde de timeline (`montage_saved.json`) ; rendu vers la
Bibliothèque et attachable à un post. Absents : montage par le texte, styles
de sous-titres animés, réglages d'étalonnage, recadrage multi-format,
pistes dynamiques, titres animés, découpe automatique, projets multiples,
export EDL/XML.

**Réponses**
1. Montage par le texte : **les deux selon la source** — texte pour voix off
   et avatars, forme d'onde pour les clips générés muets.
2. Sous-titres animés façon CapCut : **parité nécessaire**.
3. Étalonnage : **LUT + réglages de base ET correspondance de couleur entre
   plans**.
4. Multi-format : **recadrage automatique avec suivi du sujet**.
5. Performance — trois points, dont un **défaut signalé** : « l'ordre des
   pistes doit pouvoir se déplacer verticalement manuellement, et le rendu
   doit rendre chaque piste, actuellement la piste overlay ou la piste
   musique n'est pas rendue » ; **pas assez de pistes** ; **lecture non
   fluide** dans la timeline.
6. Transitions et titres : **les deux** (titres animés prêts + transitions
   dynamiques).
7. Auto-clips : **oui, depuis mes épisodes et films ET depuis des vidéos
   externes**.
8. Aller-retour : **remplacer un clip par une nouvelle version sans perdre
   le montage, plusieurs projets nommés, export XML/EDL** — les trois.

**Le défaut signalé, à mesurer avant tout** : le code prétend rendre V2
(overlays, `montage_service.py` en-tête « Piste V2 ») et A2 (musique
bouclée) ; l'utilisateur constate qu'une des deux n'arrive pas au rendu.
Cette session n'a pas lancé le backend (interdit) : le défaut n'est **ni
reproduit ni expliqué**. Le plan Montage commence par un banc-miroir qui
lit le fichier rendu (ffprobe : pistes audio, image témoin de l'overlay),
pas le code qui prétend le produire.

**Références vérifiées le 03/09/2026**
- Descript : mots de remplissage détectés et soulignés dans le script,
  suppression en lot par le panneau AI Tools, langues EN/DE/**FR**/PT/IT
  (help.descript.com, 03/09) ; le montage par le texte y coupe la vidéo.
- CapCut : sous-titres automatiques mot par mot, styles animés (Glow,
  Trending, Word, Frame…), mouvement, rebond, emoji automatiques
  (capcut.com, 03/09).
- DaVinci Resolve : Smart Reframe réservé à Resolve **Studio** (payant),
  modes auto / pan seul / tilt seul, pensé pour les formats verticaux et
  carrés ; « color matching » cité comme fonction du Neural Engine sans
  détail relevé (blackmagicdesign.com, 03/09).
- fal, recadrage vidéo : Luma Ray 2 Reframe, Wan VACE Long Reframe (modes
  general / **human** / auto, scène par scène), LTX-2.3 Reframe — tous
  **génératifs** (ils inventent les bords manquants) plutôt qu'un suivi de
  sujet par recadrage (fal.ai, 03/09). Le suivi de sujet local (détection
  de visage image par image) demande un modèle hors stdlib — même
  contrainte que CLAP en R4.
- Opus Clip, Premiere Auto Reframe, Final Cut : de mémoire, non vérifiés.
- EDL (CMX 3600) et FCPXML : formats publics, de mémoire ; à vérifier sur
  l'import Resolve avant d'en faire un argument.

**Bacs**

*Parité nécessaire*
- **P0 — Chaque piste arrive au rendu** : banc-miroir sur le fichier rendu
  (V2 overlay visible sur une image témoin, A2 présente dans le mix, avec
  ffprobe et comparaison de pixels), puis correction ; **avant** toute autre
  évolution du Montage. Le défaut est signalé, pas encore mesuré.
- **P1 — Pistes dynamiques et réordonnables** : ajouter/retirer des pistes
  vidéo et audio, ordre vertical par glisser, le rendu compose dans l'ordre
  des pistes ; `SVM_TRACKS` cesse d'être une constante.
- **P2 — Sous-titres animés** : 3 à 5 styles mot par mot (rebond, emphase
  colorée, glow) rendus par libass (`\t` transformations ASS) à partir du
  calage par mot déjà présent ; emoji par mot-clé en option.
- **P3 — Montage par le texte** sur les pistes calées (voix off, avatars) :
  supprimer une réplique ou un « euh » dans l'éditeur de sous-titres retire
  le segment du clip lié ; détection des mots de remplissage en FR/EN par
  liste ; les clips muets restent en forme d'onde.
- **P4 — Étalonnage** : quatre curseurs (exposition, contraste, saturation,
  température) sous la LUT, par clip ou global, en filtres ffmpeg ; la
  vignette du rack VFX les prévisualise.
- **P5 — Projets nommés** : plusieurs timelines sauvegardées (liste, ouvrir,
  dupliquer, renommer), même mécanique que `/studio-graphs`.
- **P6 — Remplacer un clip par sa nouvelle version** : mêmes bornes, mêmes
  effets, lignée de la Bibliothèque ; complète la recette du Studio (R2 D1)
  et l'animatique (R3 D3).
- **P7 — Lecture fluide** : vignettes et formes d'onde précalculées par clip,
  proxy 480p par clip (le rendu preview existe déjà, il devient par clip),
  mesuré par un banc de fluidité (images par seconde de scrub).

*Différenciant*
- **D1 — Correspondance de couleur entre plans IA** : deux clips venus de
  moteurs différents alignés automatiquement (statistiques de couleur par
  plan, transfert local en ffmpeg/PIL) ; c'est le problème propre à un film
  de plans générés, qu'aucune référence grand public ne cible.
- **D2 — Recadrage multi-format avec suivi de sujet** : un montage 9:16
  rejoué en 1:1 et 16:9 ; suivi par détection de visage (service local
  optionnel) ou, pour les plans sans sujet, recadrage centré réglable ; les
  reframes génératifs de fal restent une option payante par clip.
- **D3 — Auto-clips depuis les épisodes, les films et les vidéos externes** :
  transcription + score LLM des moments, 3 à 5 extraits 15–60 s
  sous-titrés (P2), envoyés au Scheduler ; la persona note les moments.
- **D4 — Titres animés et transitions dynamiques dans la charte** : galerie
  de lower-thirds, titres et fins en tokens de marque, posés sur V2 ;
  transitions zoom, whip, morph en filtres ffmpeg ou en overlays précalculés.
- **D5 — Export EDL/FCPXML** de la timeline pour finir dans Resolve ou
  Premiere ; les sources locales sont référencées par chemin absolu.

*Écarté*
- **E1 — Multicam, proxies 4K** : sources 1080p générées ; hors pratique.
- **E2 — Recadrage génératif systématique** : payant par clip et inventif ;
  reste une option, pas la voie par défaut.
- **E3 — Retouche corps/visage façon CapCut** : hors du produit.

**Coût de patch** : le Montage est une couche injectée (`son-vfx-montage.js`,
4 871 lignes) plus le patch `subs` en queue de chaîne — moins cher que le
bundle minifié mais **fragile en chaîne** (avertissement du patch `subs` :
un patcher amont relancé seul efface les éditions aval). P0, P1, P3, P5, P6,
P7, D4 touchent cette couche et `montage_service.py` ; P2 est surtout
`subtitle_service.py` (ASS) ; P4, D1, D2, D3, D5 sont surtout backend.

### R6. Scheduler — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `marketing.py`,
`post_preview.py`, routes `/schedule*`) : posts programmés (draft →
scheduled → ready → posted/failed), boucle de publication toutes les 60 s
dans le backend, mode auto ou assisté par post ; **Telegram** et **X**
(tweepy, vidéo comprise) publient en automatique, YouTube et Instagram sont
« assistés » (légende + rendu à poster à la main) ; métriques publiques X
rapatriées pour les 10 derniers posts (budget de lecture du palier gratuit) ;
plan de la semaine généré par LLM (ou rotation déterministe sans clé) ;
aperçu PNG de la carte X et de la bulle Telegram ; vignette d'affiche du
rendu ; skill `deepotus-comms` : événements du site, légendes, rendus, porte
de validation humaine. Absents : Instagram, YouTube, TikTok en automatique ;
tableau de bord d'analytics ; validation depuis le mobile ; recyclage ;
créneaux par canal ; aperçus Reels/Shorts/TikTok ; brief de campagne
persistant ; séries récurrentes ; threads.

**Réponses**
1. Canaux : **Instagram Reels, YouTube Shorts et TikTok en automatique**, et
   **les canaux assistés conviennent si le téléphone les publie**.
2. Analytics : **tous les canaux publiés, avec un tableau de bord** ; le plan
   de la semaine s'en inspire.
3. Validation : « **par lot (la semaine), puis auto, et aussi depuis le
   mobile, plus rappel mobile pour les exceptions** ».
4. Recyclage : **proposition automatique à valider**.
5. Aperçu : **oui, avec les zones sûres de chaque réseau**.
6. PC éteint à l'heure d'un post : **le téléphone le publie**.
7. Horaires : **créneaux par canal + horaire proposé d'après mes métriques**.
8. Plan : **brief de campagne persistant, séries récurrentes, fil par sujet
   (thread X, série de posts)** — les trois.

**Références vérifiées le 03/09/2026**
- X API : palier gratuit **500 posts et 100 lectures par mois** par projet ;
  Basic 10 000 posts/mois ; Pro 1 M ; Enterprise à partir de 42 k$/mois
  (docs.x.com, devcommunity.x.com, 03/09). Les 100 lectures/mois bornent
  l'analytics X : 10 posts × 10 rafraîchissements, pas plus.
- Instagram (Meta) : publication par l'API réservée aux comptes
  **professionnels** (Business/Creator) ; reels publiables en média unique ;
  **50 posts par 24 h** ; accès Standard pour ses propres comptes, Advanced
  (revue d'app) pour les comptes d'autrui (developers.facebook.com, 03/09).
  Le compte deepotus étant le sien, l'accès Standard suffit — à confirmer
  sur le portail au moment du plan.
- YouTube Data API : `videos.insert` dans son propre seau de quota, **100
  envois par jour** par défaut ; 10 000 unités/jour pour le reste
  (developers.google.com, 03/09). Largement au-dessus des 5 posts/jour.
- TikTok Content Posting API (Direct Post) : client **non audité** =
  contenus en visibilité **SELF_ONLY**, compte privé obligatoire, 5
  utilisateurs par 24 h ; l'audit lève la restriction ; plafond ~15 posts
  par jour et par créateur (developers.tiktok.com, 03/09). Sans audit,
  l'automatique TikTok publie en privé — à dire dans le plan.
- Postiz : open source, auto-hébergeable, 30+ plateformes (X, Instagram,
  TikTok, YouTube, LinkedIn, Threads, Bluesky, Mastodon…), API
  (postiz.com, github.com, 03/09). Candidat naturel de **relais permanent**
  (lecture C du questionnaire mobile) plutôt que de réécrire cinq
  adaptateurs.
- Buffer, Later, Metricool, Hootsuite, Typefully, Publer : de mémoire, non
  vérifiés — non utilisés comme argument.

**Bacs**

*Parité nécessaire*
- **P1 — Trois adaptateurs automatiques** : Instagram Reels (Graph API,
  compte pro), YouTube Shorts (Data API, OAuth Google), TikTok Direct Post
  (audit à passer, sinon privé) ; chacun avec sa clé dans Settings, son
  quota affiché, son échec parlant. **Ou** Postiz auto-hébergé comme relais
  unique — à trancher avec la lecture mobile (R12).
- **P2 — Tableau de bord d'analytics** : vues, likes, partages,
  commentaires par post, par canal, par format ; X borné par 100
  lectures/mois (le dire), Telegram par les vues de canal, YouTube et
  Instagram par leurs API d'insights ; graphique par semaine.
- **P3 — Créneaux par canal** : file par réseau, créneaux réglables,
  proposition d'horaire d'après les métriques (P2) quand elles existent,
  créneaux par défaut sinon.
- **P4 — Aperçus Reels, Shorts, TikTok avec zones sûres** : gabarit
  d'interface superposé au rendu 9:16 (boutons, légende, barre) pour
  vérifier qu'aucun texte n'est caché ; dessinés par code comme la carte X.
- **P5 — Validation par lot** : le plan de la semaine validé une fois ; les
  posts partent seuls ; un post modifié après validation revient en
  attente. La validation **depuis le mobile** et le **rappel mobile** des
  exceptions sont portés par R12.

*Différenciant*
- **D1 — Le téléphone publie quand le PC est éteint** : le compagnon reçoit
  à l'avance vidéo + légende + heure ; il publie par l'app native (partage
  système) ou par l'API depuis le téléphone ; l'état revient au PC au
  réveil. Aucun planificateur grand public ne fait du téléphone un relais
  de publication d'un studio local. Détail en R12.
- **D2 — Brief de campagne persistant + séries récurrentes + fils** : le
  plan lit un brief (objectif, dates, messages, interdits), remplit des
  rubriques fixes, et sait publier un thread X ou une série liée ; le skill
  `deepotus-comms` s'appuie dessus au lieu de tout redemander.
- **D3 — Recyclage proposé** : d'après P2, les posts performants sont
  proposés en repost avec variation (nouvelle légende par LLM, autre
  format par le Montage), toujours à valider.

*Écarté*
- **E1 — Validation en équipe (Hootsuite)** : utilisateur unique.
- **E2 — Analytics concurrents (Metricool)** : hors périmètre.
- **E3 — Publication automatique TikTok en public sans audit** : impossible
  par l'API (mesuré) ; sans audit, c'est le téléphone (D1) qui publie en
  public.

**Coût de patch** : le Scheduler est un écran du bundle — P3, P4, P5, D2
(brief) touchent le bundle ; P1, P2, D3 et le moteur de D2 sont backend
(`marketing.py`, nouveaux adaptateurs, tables de métriques) ; D1 est
partagé avec le plan mobile.

### R7. Templates — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `template_service.py`,
routes `/layout-templates*`, `/branding*`, `backend/app/templates/*.json`,
`figma_import.py`, bundle) : un template est un JSON pur (canvas, régions
typées — `video_slot`, `separator`, `brand_strip`, texte… —, transitions,
audio, métadonnées) ; **9 templates livrés** immuables (news reel, alpha
reel 60/30/10, classic vstack, hstack dialogue, montage film, oracle +
lower-third, PIP avatar, trois actes, timeline) ; templates utilisateur
sous `assets/user_templates/` (liste, lire, slots, enregistrer, supprimer,
rendre) ; rendu **vidéo** par ffmpeg depuis les slots ; kit de marque
minimal (`/branding` : nom, sous-titre, couleur de marque, couleur
d'accent, logo, retour aux défauts deepotus) ; fontes embarquées (Anton,
Bebas Neue, Archivo Black, Abril Fatface…) ; import Figma d'un calque en
PNG ; éditeur visuel de régions (le bundle ne contient pas Konva : le
« Konva » de DESIGN §5 est une intention, pas une mesure). Absents :
plusieurs kits, réagencement multi-format, masques de région, composants
partagés, animations de région, texte adaptatif et effets de texte, rendu
image fixe, import Figma éditable, export vers Figma.

**Réponses**
1. Kit de marque : **plusieurs kits commutables** (deepotus, client, test).
2. Resize : « **1 + la possibilité de réagencer à la main et appliquer des
   masques (fenêtres ajourées avec des bords pleins arrondis sur un encart
   ajusté, etc.)** » — réagencement automatique par règles **et** manuel,
   **et** masques de région.
3. Composants : **oui, bibliothèque de composants** (modifier une fois,
   partout).
4. Animés : **les deux** — animations simples dans le template, riches au
   Montage.
5. Figma : **les deux** — importer un cadre comme template éditable et
   exporter vers Figma.
6. Usage : **la plupart des neuf selon le format** ; il faut des aperçus
   avec le contenu réel.
7. Texte : **adaptatif, effets (contour, ombre, dégradé, fond), texte sur
   courbe et typographie décorative** — les trois.
8. Image fixe : **oui, PNG/JPG du template avec ses slots remplis**.

**Références vérifiées le 03/09/2026**
- Canva : Brand Kit (logos, couleurs, polices, imagerie, templates,
  consignes en un lieu ; remplacement d'un logo dans tous les designs
  existants) ; Magic Switch / Magic Resize redimensionne un design en
  plusieurs formats en un clic (canva.com, 03/09).
- Figma REST API : arbre DOCUMENT → CANVAS → nœuds avec `constraints`
  relatives au cadre parent, `components` (mapping id → métadonnées),
  `exportSettings`, et l'endpoint `/v1/files/{key}/nodes?ids=` pour lire
  textes et géométrie (developers.figma.com, 03/09). L'import éditable est
  donc faisable en lecture ; l'**écriture** d'un fichier Figma n'est pas
  offerte par l'API REST — l'« export vers Figma » passe par un SVG ou un
  plugin, pas par l'API. Adobe Express, Placeit, Kittl : de mémoire, non
  vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Kits de marque multiples** : table de kits (nom, couleurs, polices
  embarquées ou importées, logo, ton/persona), kit actif par projet ;
  templates, sous-titres, titres, aperçus de posts lisent le kit actif ;
  `/branding` devient `/brand-kits`.
- **P2 — Réagencement multi-format** : chaque région porte ancres et
  contraintes (façon Figma) ; le template se rejoue en 9:16, 1:1, 16:9,
  4:5 ; réagencement manuel par format quand la règle ne suffit pas, les
  quatre canevas sauvegardés dans le même JSON.
- **P3 — Masques de région** : fenêtres ajourées à bords arrondis, encarts,
  formes (rond, arrondi, polygone, SVG) sur un slot vidéo ou image ; rendu
  ffmpeg par `alphamerge` d'un masque PNG dessiné par code.
- **P4 — Texte adaptatif et effets** : rétrécissement ou coupe pour tenir
  ; contour, ombre, dégradé, fond ; mesure de la largeur du texte avec la
  fonte embarquée (PIL) avant le rendu, jamais « à l'œil ».
- **P5 — Rendu image fixe** : PNG/JPG du template avec ses slots remplis,
  par le même compositeur que la vidéo (une image = une vidéo d'une image),
  rangé dans la Bibliothèque avec sa recette.
- **P6 — Aperçus avec le contenu réel** : la galerie rend chaque template
  avec les derniers assets de l'utilisateur, pas une vignette générique.

*Différenciant*
- **D1 — Bibliothèque de composants** : lower-third, bandeau, bande de
  marque définis une fois, instanciés dans N templates, mise à jour
  propagée ; un composant porte ses ancres (P2) et son animation (D2).
- **D2 — Animations de région** : entrée, sortie, durée par région (glisser,
  fondu, apparition du logo) rendues par ffmpeg ; les animations riches
  restent au Montage (R5 D4).
- **D3 — Import Figma éditable** : un cadre Figma devient un template
  (régions depuis les nœuds, textes, contraintes) ; l'export vers Figma se
  fait en SVG (les régions en groupes nommés) faute d'API d'écriture.
- **D4 — Texte sur courbe et typographie décorative** : tracé par code
  (PIL/SVG), pour les titres et les cartes de Card Forge, dans le kit.

*Écarté*
- **E1 — Modèles par milliers façon Canva** : neuf templates suffisent à
  l'usage déclaré ; c'est l'éditeur et les kits qui comptent.
- **E2 — Mockups façon Placeit** : hors du produit.
- **E3 — Écriture directe dans Figma par API** : non offerte (mesuré) ; le
  SVG remplace.

**Coût de patch** : l'éditeur de templates vit dans le bundle (régions,
panneau) — P2, P3, P4 (panneau), P6, D1, D2 (panneau), D3 sont des patches
chaînés ; P1, P5 et les moteurs de rendu (masques, texte, animations) sont
backend (`template_service.py`, ffmpeg, PIL).

### R8. News — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `news_service.py`,
`article_scraper.py`, `summarizer.py`, `news_illustration.py`, routes
`/news/*`, `personas/deepotus.json`) : sources RSS/Atom ou URL d'article,
persistées ; rafraîchissement quotidien, cache ; **dédoublonnage par
identifiant seulement**, tri du plus récent, plafond 300 items ; scraper
durci (consentement pré-accepté, AMP, lecteur proxy optionnel) ; résumé
multi-fournisseur (Anthropic > OpenAI > Gemini > Ollama, toujours
fail-safe) ; script « prophet » (cynique/humoristique) + légende depuis les
articles sélectionnés ; illustration animée ffmpeg 1080×1920 muette
(titres, ticker, fondus) composée avec l'avatar HeyGen ; persona deepotus
(mots-clés d'ambiance, couleurs, négatif, hashtags, templates) ; modes de
voix oracle/alpha/zen/memer dans les schémas. Absents : mots-clés et listes
noires, score, tendances, historique des sujets couverts, sources en
légende, images ou plans générés par article, chaîne automatique jusqu'au
Scheduler.

**Réponses**
1. Tri : **mots-clés et listes noires d'abord (gratuit), puis score LLM**.
2. Sources : **en légende seulement**.
3. Persona : **une persona, plusieurs modes selon le sujet** (le LLM choisit
   oracle/alpha/zen/memer, forçable).
4. Tendances : **les deux** — sujets croisés entre flux (gratuit, local) et
   signal X.
5. Intervention : **les quatre gestes** doivent devenir automatiques ou
   présélectionnés — choix des articles, script (toujours soumis mais
   proposé), images et mise en page, programmation du post.
6. Historique : **sujets déjà couverts marqués, sources équilibrées**.
7. Forme : **les quatre** — images générées par titre, plans vidéo par
   sujet, avatar présentateur, voix off + sous-titres animés sans avatar.
8. Langues : **une langue par reel, choisie au cas par cas**.

**Références vérifiées le 03/09/2026**
- Feedly : dédoublonnage quand le contenu se recouvre à **plus de 85 %** ;
  filtres de mute (mots-clés, entreprises, personnes, sujets, auteurs,
  sites) ; priorisation par sujets (docs.feedly.com, 03/09).
- Inoreader : filtres de doublons par URL, titre exact ou titre presque
  identique, fenêtre de 6 h à 1 mois ; règles (déclencheur, conditions,
  action) ; Pro (inoreader.com, 03/09).
- Google Trends API : **alpha** depuis juillet 2025, accès sur candidature,
  sans réponse garantie (developers.google.com, support.google.com, 03/09)
  → pas une base de plan.
- X API : 100 lectures/mois en gratuit (R6) → le « signal X » se limite à
  quelques requêtes par jour ou exige le palier Basic.
- Opus Clip, Pictory, InVideo, Perplexity, Exploding Topics : de mémoire,
  non vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Filtre gratuit puis score** : mots-clés, listes noires (sources,
  mots), fenêtre de fraîcheur ; dédoublonnage par titre presque identique
  (Inoreader) ou recouvrement de contenu (Feedly, 85 %) en plus de
  l'identifiant ; puis score LLM de pertinence pour la communauté (persona
  + brief de campagne de R6) sur ce qui reste ; les 3 à 5 meilleurs du
  jour en tête, le reste replié.
- **P2 — Historique et équilibre** : chaque reel publié mémorise ses sujets
  (entités, mots-clés) et sa source ; un article proche d'un sujet couvert
  est marqué ; le score pénalise la source sur-représentée.
- **P3 — Sources en légende** : nom du média, date, lien ajoutés à la
  légende du post par le pipeline.
- **P4 — Modes de voix par sujet** : le script prophet choisit son mode
  (oracle, alpha, zen, memer) d'après le sujet, affiché et forçable.

*Différenciant*
- **D1 — Chaîne article → post sans intervention** : sélection
  présélectionnée, script proposé (toujours visible), forme choisie
  (D2), légende avec sources, créneau du Scheduler — l'utilisateur ne fait
  que valider le lot (R6 P5) ; aucune référence ne relie flux, persona,
  génération et publication en local.
- **D2 — Quatre formes de reel** : illustration IA par titre (Nano Banana /
  FLUX dans la charte), plans Seedance par sujet, avatar présentateur
  (existant), voix off + sous-titres animés (R5 P2) sans avatar ; coût
  affiché par forme avant tir.
- **D3 — Tendances locales** : un sujet cité par N sources le même jour est
  marqué tendance (gratuit) ; signal X en option bornée par le quota.

*Écarté*
- **E1 — Sources à l'écran** : réponse 2, légende seulement.
- **E2 — Google Trends** : API en alpha sur candidature ; à revoir quand
  elle sera publique.
- **E3 — Reel bilingue systématique** : réponse 8.

**Coût de patch** : l'écran News est dans le bundle — P1 (filtres et
score affichés), P2 (marques), D1 (validation) sont des patches chaînés ;
les moteurs (filtres, score, historique, formes) sont backend
(`news_service.py`, `summarizer.py`, `news_illustration.py`).

### R9. Library — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `library_index.py`,
`storage.py` `LibraryAsset`, patches `libpicker`, `libprov`, `libsend`,
routes `/images`, `/assets/3d/*`, `/assets/sprite/*`) : table
`library_assets` par fichier — `source` (fonction productrice), `kind`,
`origin` (dépôt ou heuristique, dit à l'UI), `job_id`, `deck_id`, `doc_id`,
`created` ; chips de provenance sur Images et Renders ; sélecteur unifié
(vignettes réelles, recherche instantanée par nom, tri par date, import
fichier et Figma) ; menu « Envoyer vers… » à dix cibles ; onglets par
catégorie (Images, Renders, Audio, Sprites, 3D…) ; assets 3D avec
versions, comparaison, rapport, contrôle qualité, silhouettes ; Vectorlab
garde 10 versions par document. Absents : tags, favori/note, collections
ou projets, lignée pour images/rendus/sons, recherche par contenu,
licence/auteur, tableau de nettoyage, annotations, fiche complète (recette,
usages, coût cumulé).

**Réponses**
1. Tags et note : **les deux — tags libres + favori/étoiles**.
2. Collections : **par projet, toutes catégories mêlées** (la catégorie
   devient un filtre dans le projet).
3. Versions : **lignée pour tout asset, repliée sous la mère** (le modèle
   T6 de l'Établi généralisé).
4. Recherche : **par description, par couleur dominante, par similarité
   visuelle** — les trois.
5. Droits : **licence + source + auteur sur la fiche**.
6. Nettoyage : **tableau de bord + actions sûres** (corbeille, retour
   arrière).
7. Annotations : **notes et commentaires horodatés** (PC et mobile).
8. Fiche : **recette complète, actions et dérivés, usages en aval, coût
   cumulé de la lignée** — les quatre.

**Références vérifiées le 03/09/2026**
- Eagle : tags (dont auto-tag à l'entrée dans un dossier), recherche par
  couleur exacte ou tons proches, dossiers intelligents par règles,
  détection et fusion des doublons (en.eagle.cool, 03/09).
- Immich : recherche contextuelle par CLIP (modèle choisi dans les
  réglages, ré-indexation obligatoire au changement), doublons probables
  par distance d'embedding, visages par DBSCAN sur un modèle de
  reconnaissance (docs.immich.app, 03/09).
- Frame.io : commentaires horodatés (désactivables), annotations
  dessinées, **piles de versions** (versions empilées sans dossier, revue
  côte à côte), export des commentaires (help.frame.io, 03/09).
- fal : pas d'endpoint d'embedding CLIP texte ↔ image relevé (seul SAM 3
  « image/embed », qui sert la segmentation) (fal.ai, 03/09). La recherche
  par description et par similarité demande donc un modèle CLIP **local**
  (même contrainte numpy/torch que CLAP en R4 : service optionnel) ou un
  fournisseur d'embeddings multimodaux (Gemini/OpenAI, de mémoire, à
  vérifier avant le plan). La couleur dominante se calcule en PIL pur.
- Adobe Bridge/Lightroom, Bynder : de mémoire, non vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Tags, favori, étoiles** : colonnes sur `library_assets` (ou table
  de tags n:n), édition inline sur la vignette et la fiche, filtres par
  tag et par note dans tous les onglets et dans le sélecteur.
- **P2 — Projets** : entité projet (campagne, chapitre, deck) contenant des
  assets de toutes catégories ; un asset dans N projets ; vue par projet
  avec la catégorie en filtre ; « Envoyer vers » et les producteurs
  rangent dans le projet actif.
- **P3 — Lignée pour tout asset** : `parent_filename` + `relation`
  (retouche, extension, stems, version, détourage, recadrage) écrit par
  chaque producteur ; affichage replié sous la mère, comparaison côte à
  côte ; T6 de l'Établi en est le premier lot.
- **P4 — Fiche complète** : recette (modèle, prompt, graine, coût, durée,
  copiable et rejouable — les jobs la portent déjà en partie), usages en
  aval (posts, montages, chapitres, decks) par jointure sur `job_id`,
  `deck_id`, `doc_id`, coût cumulé de la lignée (P3), licence/source/auteur
  (P5).
- **P5 — Licence, source, auteur** : champs sur la fiche, remplis à
  l'import (fichier, Figma, catalogue CC0 automatiquement), avertissement
  visible quand la licence est inconnue.
- **P6 — Nettoyage** : tableau de bord (poids par catégorie et par projet,
  doublons exacts par empreinte, orphelins fichier ↔ index, rendus ratés)
  avec corbeille et retour arrière ; doublons proches quand D1 existe.
- **P7 — Couleur dominante** : calculée en PIL à l'indexation, filtre par
  teinte.

*Différenciant*
- **D1 — Recherche par description et similarité** : index d'embeddings
  image (CLIP local via service optionnel, ou fournisseur distant),
  partagé avec la recherche sonore de R4 D3 (même service) ; « comme
  celle-ci » et doublons proches en découlent.
- **D2 — Annotations horodatées** : notes et commentaires sur un rendu à
  un temps donné, depuis le PC et le mobile (R12), statut à revoir /
  validé / rejeté ; pile de versions façon Frame.io par la lignée (P3).
- **D3 — La Bibliothèque comme table de montage des projets** : le projet
  (P2) sait ce qui est publié, monté, imprimé ; un asset dit où il sert ;
  aucune référence DAM ne relie génération, montage et publication.

*Écarté*
- **E1 — Reconnaissance de visages** : un seul utilisateur, personnages
  générés ; la bible (R3) tient l'identité, pas la Bibliothèque.
- **E2 — Gestion des droits façon DAM d'entreprise (expiration, workflow
  d'approbation)** : utilisateur unique.

**Coût de patch** : l'écran Library est dans le bundle et ses greffes
(`libprov`, `libpicker`, `libsend`) sont en queue de chaîne — P1, P2, P3
(repli), P4 (fiche), P6 (tableau), D2 sont des patches chaînés ; les
tables, l'indexation (couleur, empreintes, embeddings) et les jointures
sont backend.

### R10a. Game Assets — Sprites 2D — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `sprite_service.py`,
`pixel_ops.py`, route `/assets/sprite`, patch `spritelab`,
`frontend/spritelab/`) : vidéo rendue ou importée → images (échantillon
fps, max images, filmstrip de sélection) → feuille (cellules 128/256/512,
alignement, colonnes), détourage none/api/local, chroma key, trim
animation ou serré ; pixel-art local PIL (réduction LANCZOS →
quantification palette preset ou adaptative MEDIANCUT → alpha binaire →
agrandissement NEAREST ; dither Bayer 4×4 ou Floyd-Steinberg) ; sorties
sheet.png, frames, preview.gif, manifest.json, **pack Unity** (JSON +
importateur C#), ZIP ; page autonome `/spritelab` (hors bundle). Absents :
palette verrouillée entre images, sortie native sans agrandissement, tags
d'animation et durée par image, outline/ombre/nettoyage, 8 directions,
squelette 2D, exports Godot/Unreal/atlas générique/Aseprite, génération
par prompt.

**Réponses**
1. Palette : **l'état actuel me va** (presets + adaptative, par image).
2. Pixel-perfect : **sortie native + aperçu à l'échelle entière**.
3. Animation : **les deux selon l'asset** — images-clés pour effets et
   objets, squelette 2D pour les personnages.
4. Export : **Godot, Unreal Paper2D, atlas façon TexturePacker, Aseprite**
   — les quatre.
5. Directions : **les deux selon l'asset** — 8 vues depuis la planche de la
   bible (image) ou depuis le modèle 3D de l'entité rendu en 8 angles.
6. Post-traitement : **outline 1 px, ombre portée et éclairage stylisé,
   nettoyage des pixels orphelins** — les trois.
7. Source : **génération image contrainte + pixelisation locale** (pas de
   nouveau moteur).
8. Éditeur : **réordonner/dupliquer/supprimer, durée par image et tags
   d'animation, pelure d'oignon et retouche pixel** — les trois.

**Références vérifiées le 03/09/2026**
- Aseprite : spécification publique du format `.ase/.aseprite`
  (`docs/ase-file-specs.md` : en-tête magique 0xA5E0, frames, calques,
  palette, **tags** avec direction de boucle et répétitions, slices)
  (github.com/aseprite, 03/09) ; le format est écrivable par code.
- Godot 4 : ressources `SpriteFrames` (animations nommées, fps, boucle),
  `AtlasTexture` (région dans une texture), importateur d'atlas
  (docs.godotengine.org, 03/09) ; un `.tres` est un texte.
- TexturePacker : format JSON Hash (lu par Phaser, PixiJS) — `frame`,
  `rotated`, `trimmed`, `spriteSourceSize`, `sourceSize`
  (codeandweb.com, 03/09).
- Retro Diffusion : générateur pixel-art dédié avec API (outils
  développeur, crédits) (retrodiffusion.ai, 03/09) — écarté par la réponse
  7, gardé en note.
- Spine, DragonBones, Pixel Composer, Scenario, Unreal Paper2D : de
  mémoire, non vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Sortie native + aperçu ×2/×4** : la feuille livrée à la taille du
  jeu (pas d'agrandissement), la visionneuse agrandit en NEAREST à
  l'échelle entière.
- **P2 — Tags d'animation et durée par image** : plusieurs animations
  nommées (idle, run, jump) dans une feuille, durée variable, écrites dans
  le manifeste et chaque export.
- **P3 — Exports** : Godot (`SpriteFrames` `.tres` + `AtlasTexture`),
  atlas JSON Hash façon TexturePacker (trim, rotation, sourceSize),
  Aseprite (`.ase` avec calques et tags, selon la spec publique), Unreal
  Paper2D (flipbook — format à relever avant le plan).
- **P4 — Post-traitement** : outline 1 px couleur choisie, ombre plate ou
  décalée, nettoyage des pixels orphelins et lissage des bords — en PIL
  pur, par image, avant la feuille.
- **P5 — Éditeur** : réordonner, dupliquer, supprimer ; pelure d'oignon ;
  retouche pixel (crayon, pipette, gomme) sur `/spritelab`.

*Différenciant*
- **D1 — 8 directions depuis la bible** : image (planche + Kontext / Nano
  Banana multi-références, R3 P3) ou modèle 3D de l'entité rendu sous 8
  angles puis pixelisé — l'identité vient de la bible, ce qu'aucun outil
  de sprites ne possède.
- **D2 — Génération contrainte + pixelisation locale** : prompt → image
  (style pixel-art dans le prompt, persona) → pipeline pixel local ; zéro
  moteur nouveau, coût = une image.
- **D3 — Squelette 2D pour les personnages** : découpe en pièces (détourage
  + segmentation), os et export Spine/DragonBones — à instruire après D1,
  le format Spine à relever.

*Écarté*
- **E1 — Palette verrouillée / palette de projet** : réponse 1.
- **E2 — Moteur pixel-art dédié (Retro Diffusion)** : réponse 7.

**Coût de patch** : `/spritelab` est autonome (hors bundle) — P1, P2, P5,
D1 (bouton) y sont bon marché ; P3, P4, D2 et le moteur de D1 sont backend
(`sprite_service.py`, `pixel_ops.py`, nouveaux exporteurs).

### R10b. Game Assets — Tuiles — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `pixel_ops.py`,
`frontend/tilelab/tilelab.js` 220 lignes, patch `tilelab`) : page autonome
`/tilelab` (sous-onglet du hub Game Assets, hors bundle) ; une image
(générée ou importée) devient une tuile **seamless** par décalage 50/50
fondu ou miroir 2×2 ; **score de raccord 0–100 mesuré** (moyenne des
différences absolues entre bords opposés, 0 = parfait) ; aperçu composite
2×2 plafonné à 512 px ; pipeline pixel-art local disponible. Absents :
jeux de tuiles à bords compatibles (Wang, blob), auto-tiling, exports
Tiled/LDtk/Godot, iso et hex, variations, aperçu 8×8, mesures de
répétition et d'éclairage, lien aux Matières et à la bible, peintre de
niveau.

**Réponses**
1. Jeux raccordables : **blob 47 (ou 16) généré depuis deux matières**,
   bords testés au score de raccord.
2. Export : **Tiled (.tsx), règles LDtk, Godot TileSet** — les trois.
3. Iso/hex : **les deux**, chacune avec masque et test de raccord.
4. Variations : **oui, 3 à 5 variantes + aperçu 8×8 à tirage aléatoire**.
5. Source : **depuis une matière du Material Forge, par prompt avec le
   style d'un lieu de la bible, par prompt libre** — les trois.
6. Mesures : **raccord, répétition (auto-corrélation), éclairage** — trois
   chiffres par tuile et par jeu.
7. Taille : **les deux selon le jeu** — pixel-art par le pipeline local,
   texturées par le seamless.
8. Peintre : **oui, un peintre minimal avec auto-tiling** (grille, pinceau
   de terrain, règle blob en direct, export PNG + carte JSON).

**Références vérifiées le 03/09/2026**
- Tiled : formats TMX/TSX en XML ; un `.tsx` est l'élément `<tileset>`
  (tilewidth, tileheight, tilecount, columns, image) sans `firstgid`
  (doc.mapeditor.org, 03/09) — écrivable par code.
- LDtk : auto-layers fondées sur des IntGrid, règles = motifs de grille
  (« peindre si la cellule vaut X et les voisines… ») dans
  `autoRuleGroups` des définitions de calque ; schéma JSON public ;
  export TMX possible (ldtk.io, 03/09).
- Godot 4 : `TileSet` avec terrains (terrain sets) et TileMapLayer
  (docs.godotengine.org, 03/09) ; le format `.tres` est texte.
- Blob 47 / Wang (cr31), Sprite Fusion, TileMill : de mémoire, non
  vérifiés — le nombre 47 vient du blob complet à 8 voisins avec coins,
  à confirmer contre la référence au moment du plan.

**Bacs**

*Parité nécessaire*
- **P1 — Jeu blob (47 ou 16) depuis deux matières** : génération des
  transitions par masque (les 47 masques dessinés par code) et mélange
  des deux tuiles seamless ; chaque tuile testée au score de raccord
  contre ses voisines légales, pas seulement contre elle-même.
- **P2 — Exports** : Tiled `.tsx` (tileset image + métadonnées), LDtk
  (tileset + `autoRuleGroups` pour le blob), Godot `TileSet` `.tres` avec
  terrains ; un banc lit chaque fichier écrit.
- **P3 — Variations et aperçu 8×8** : 3 à 5 variantes par tuile (graine ou
  perturbation locale), aperçu 8×8 à tirage aléatoire, la répétition se
  voit avant l'export.
- **P4 — Trois mesures** : raccord (existant), répétition
  (auto-corrélation sur la grille 8×8), éclairage (gradient moyen par
  tuile, écart dans le jeu) — affichées par tuile et par jeu, seuils
  nommés.
- **P5 — Iso et hex** : masques losange 2:1 et hexagone, raccord testé sur
  les bords correspondants, export dans les trois formats quand ils le
  supportent (Tiled : orientation ; Godot : formes de tuile).

*Différenciant*
- **D1 — Une matière = un tileset** : l'albedo d'une matière PBR du
  Material Forge devient la tuile de base ; la même matière habille la 3D
  et le niveau 2D — aucun outil de tuiles ne part d'une matière PBR
  locale.
- **D2 — Tuiles au style d'un lieu de la bible** : la planche et la
  palette du lieu (R3) contraignent le prompt du jeu de tuiles.
- **D3 — Peintre minimal avec auto-tiling** : grille, pinceau de terrain,
  règle blob appliquée en direct, export PNG + JSON ; teste le tileset
  sans quitter l'app.

*Écarté*
- **E1 — Éditeur de niveaux complet** : Tiled et LDtk restent les
  éditeurs ; le peintre (D3) ne fait que tester.

**Coût de patch** : `/tilelab` est autonome (hors bundle) — P3, P4, P5
(aperçus), D3 y sont bon marché ; P1, P2, D1, D2 et les moteurs de mesure
sont backend (`pixel_ops.py`, nouveaux exporteurs, lien `material_store`).

### R10c. Game Assets — Matières — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `pbr_service.py`,
`material_store.py`, routes `/materials/*`, patch `materialforge`,
page autonome `/materialforge/`) : génération depuis un prompt (modèle
image) ou une image de la Bibliothèque, rendue seamless (méthode au choix)
; **8 cartes dérivées en PIL pur** avec convolutions cycliques (le raccord
des cartes tient) : basecolor, normale (OpenGL par défaut, bascule
DirectX), rugosité, métallique, AO, hauteur, émissif, ORM glTF ; presets ;
dérivation re-réglable, duplication, vignette ; **7 ambiances** du viewport
(équirectangulaires servies), GLB d'aperçu avec sol de référence ; échelle
du score de raccord documentée ; export ZIP / GLB / glTF avec **conventions
de nommage `standard`, `unity_urp`, `unity_hdrp`, `unreal`, `godot`**, 8 ou
16 bits pour hauteur et normale, liste blanche de cartes, bordereau avant
téléchargement. Absents : delighting, redressement de perspective, entrée
depuis le téléphone, choix de la forme d'aperçu, HDRI personnels,
comparaison côte à côte, convention Blender explicite, catalogue de départ,
générateurs procéduraux, application par zone ou masques automatiques sur
un maillage, taille physique, finitions supplémentaires avec aperçu.

**Réponses**
1. Photo → PBR : **delighting, redressement de perspective + recadrage,
   entrée depuis le téléphone** — les trois.
2. Aperçu : **choix de la forme (sphère, cube, plan, cylindre, mon modèle),
   HDRI personnels, comparaison côte à côte** — les trois.
3. Export : **Blender, Unity URP/HDRP, Unreal, Godot** — Unity, Unreal et
   Godot existent déjà (mesuré) ; reste Blender et la preuve par banc.
4. Catalogue : **oui, une trentaine de matières CC0 embarquées**.
5. Procédural : **oui, une dizaine de générateurs paramétriques locaux**.
6. Peinture 3D : **les deux** — une matière par partie du maillage ET
   masques automatiques (cavités, arêtes).
7. Échelle : **seulement pour l'impression** (hauteur de la carte height en
   mm pour le relief).
8. Finitions : **plus de finitions + aperçu temps réel**.

**Références vérifiées le 03/09/2026**
- Substance 3D Sampler : « Delight (AI powered) » retire l'éclairage de la
  basecolor, sans paramètre ; « Image to Material » inclut la passe de
  delighting (experienceleague.adobe.com, 03/09).
- Materialize (Bounding Box Software) : open source, image → cartes
  (hauteur, normale, métal…) sur GPU (github.com, 03/09) — code Unity,
  pas réutilisable en PIL, mais ses algorithmes sont lisibles.
- Poly Haven : assets **CC0** ; API publique sans clé, **usage commercial
  de l'API interdit sans licence** (accordée sur demande), en-tête
  Referer/User-Agent au nom du logiciel et attribution demandés
  (polyhaven.com, github.com/Poly-Haven, 03/09) → pour un catalogue
  embarqué, télécharger une fois au build (comme Kenney pour les sons) et
  attribuer, plutôt que d'appeler l'API depuis l'application.
- Quixel, ArmorPaint, Painter : de mémoire, non vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Delighting + redressement** : suppression du dégradé d'éclairage
  (estimation basse fréquence et division, PIL pur) et redressement de
  perspective par quatre coins (transformation PIL) avant la dérivation ;
  mesure : écart-type de luminance basse fréquence avant/après.
- **P2 — Aperçu** : forme au choix (sphère, cube, plan, cylindre, un GLB
  de la Bibliothèque), HDRI importé (.hdr/.exr converti en
  équirectangulaire LDR pour le viewport), comparaison côte à côte de deux
  matières sous la même ambiance.
- **P3 — Convention Blender** dans `naming_catalog` (Principled BSDF,
  OpenGL, noms de cartes), et un banc par convention qui lit l'archive
  écrite (noms, canaux ORM, signe Y de la normale).
- **P4 — Catalogue de départ** : ~30 matières CC0 (sols, murs, métaux,
  bois, tissus) téléchargées au build depuis Poly Haven avec attribution,
  poids mesuré (résolution 1K), rangées comme matières ordinaires.
- **P5 — Hauteur physique pour le relief** : mm de la carte height sur la
  fiche, consommé par `print3d` (relief vitrail).

*Différenciant*
- **D1 — Générateurs paramétriques locaux** : briques, carrelage, bois,
  métal brossé, bruit, cuir, tissu… seamless par construction, réglables
  en direct, cartes dérivées à la volée ; gratuits et hors ligne, là où
  Substance est payant et lourd.
- **D2 — Matière par partie + masques automatiques** : l'Établi connaît
  les parties d'un maillage ; une matière par partie, masques de cavités
  et d'arêtes calculés depuis la géométrie (AO et courbure) pour l'usure ;
  aperçu dans le viewport.
- **D3 — Finitions nommées avec aperçu temps réel** : métal brossé, laque,
  cuir, émissif animé… dans le graphe Forge 3D, prévisualisées avant
  rendu.
- **D4 — Photo depuis le téléphone** : le compagnon (R12) envoie une photo
  de surface au Material Forge, qui redresse, délighte et dérive.

*Écarté*
- **E1 — Taille physique propagée aux moteurs** : réponse 7 ; seulement
  l'impression.
- **E2 — Appel de l'API Poly Haven depuis l'application** : interdit en
  usage commercial sans licence (mesuré) ; catalogue au build.

**Coût de patch** : `/materialforge/` est autonome (hors bundle) — P2, D1
(réglages), D2 (aperçu), D3 (aperçu) y sont bon marché ; P1, P3, P4, P5,
et les moteurs de D1, D2 sont backend (`pbr_service.py`, `material_store.py`,
`print3d.py`, banc par convention).

### R10d. Game Assets — Cartes (Card Forge) — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `services/cards/`
— `contract.py`, `print.py`, `data.py`, `capture.py`, `texture.py`,
`forge3d*.py`, `face.py` ; patch `cardforge` ; page autonome
`/cardforge/`) : domaine monté sous `/api/cards` en dix pièces ; **12
formats** de carte (poker US/EU, bridge, tarot, mini, carré, domino, carte
de visite, jumbo, micro) ; export impression **au pixel de nanDECK** à 300
ou 600 DPI, fond perdu, zones sûres, traits de coupe, **planches
d'imposition A4 et Letter**, profils ICC, papiers ; decks par CSV avec
quantités, filtres, tri (sémantique nanDECK LINK*) ; import d'une carte
existante (photo, scan, PNG) avec mesure ; textures 2D et PBR (8 cartes
via `pbr_service`) ; masque foil ; sélection multiple façon Figma ; graphe
Forge 3D (relief, extrusion, GLB/STL, aperçu, turntable, scène) ; audit,
art check, atlas, séries de style (affiche polonaise, vitrail) par skills.
Absents : gabarits imprimeur (MPC, TGC, DTC), export Tabletop Simulator /
Tabletopia, dos variables par carte, statistiques de deck, édition
tabulaire, import Sheets/Notion, localisation, jetons/boîte/présentoir,
génération d'art par ligne liée à la bible, livret, mockup, fiche produit.

**Réponses**
1. Imprimeur : **MPC, TGC, DriveThruCards, et l'imposition maison** — les
   quatre.
2. Tabletop : **TTS et Tabletopia**.
3. Recto/verso : **dos variables par carte + planche verso en miroir**.
4. Données : **statistiques, édition tabulaire, import Sheets/Notion, et
   le CSV reste** — les quatre.
5. Langues : **FR + EN par colonnes avec traduction LLM proposée**, à
   valider carte par carte.
6. Forge 3D : **jetons et pions, boîte (tuck box) et plateau, présentoir
   imprimé en 3D** — les trois.
7. Art : **prompt par ligne + style de série + bible**, coût du deck avant
   tir.
8. Autour : **livret de règles PDF, mockup marketing, fiche produit et
   export boutique** — les trois.

**Références vérifiées le 03/09/2026**
- MakePlayingCards : poker 2,5 × 3,5 in, upload **822 × 1122 px** à
  300 DPI, fond perdu 1/8 in (36 px), zone sûre 36 px de plus
  (makeplayingcards.com, 03/09).
- The Game Crafter : coupe à 1/8 in (37 px), zone sûre à 1/4 in (75 px),
  300 DPI ; **API développeur** `/api/deck` (thegamecrafter.com, 03/09).
- DriveThruCards : fond perdu 1/8 in obligatoire, zone sûre 1/8 in dans
  la coupe (2,25 × 3,25 in), mise en page 2,75 × 3,75 in, **PDF/X-1a:2001**
  polices incorporées, **sans traits de coupe** (drivethrucards.com, 03/09).
- Tabletop Simulator : deck en collage **10 colonnes × 7 lignes**, objet
  JSON (ObjectStates, Transform, Nickname…) dans Saved Objects
  (kb.tabletopsimulator.com, 03/09).
- nanDECK, Component Studio, Dextrous, Squib, Tabletopia : de mémoire
  (nanDECK est la référence mesurée du dépôt, au pixel).

**Bacs**

*Parité nécessaire*
- **P1 — Gabarits imprimeur** : profils MPC (822 × 1122, fond perdu 36 px),
  TGC (37/75 px) et DTC (PDF/X-1a, 2,75 × 3,75 in, sans traits) dans
  `contract.py`, export PNG par carte nommé recto/verso pour MPC et TGC,
  PDF multi-pages pour DTC ; un banc mesure les pixels écrits contre les
  chiffres ci-dessus.
- **P2 — Tabletop Simulator et Tabletopia** : collage 10 × 7 (recto + dos)
  et JSON d'objet ; format Tabletopia à relever avant le plan.
- **P3 — Dos variables + miroir** : colonne « dos » dans le CSV, planche
  verso imposée en miroir avec test d'alignement (repères imprimés).
- **P4 — Données** : statistiques (histogrammes par colonne numérique et
  catégorielle), grille éditable dans l'app (écrit le CSV), import depuis
  Google Sheets (CSV publié) et Notion (export CSV ou API).
- **P5 — Localisation** : colonnes par langue, rendu et export par langue,
  texte adaptatif (R7 P4), traduction LLM proposée et validée carte par
  carte.

*Différenciant*
- **D1 — Art du deck depuis le CSV et la bible** : prompt par ligne,
  style de série (skills existants), personnages de la bible (R3 P3),
  coût total avant tir, génération en lot avec lignée dans la Bibliothèque
  ; aucun outil de cartes ne relie données, bible et génération.
- **D2 — Objets 3D du jeu** : jetons et pions extrudés depuis une carte ou
  une entité, boîte dépliée (PDF avec plis) aux dimensions du deck,
  présentoir STL pour la Centauri — via le Forge 3D et `print3d`.
- **D3 — Autour du deck** : livret de règles PDF (texte → mise en page
  avec images des cartes), mockup marketing (rendu 3D du deck en main ou
  sur table, scène du Forge 3D), fiche produit exportable.

*Écarté*
- **E1 — Scripts de génération façon nanDECK** : la sémantique est déjà
  portée par l'UI (décision du dépôt).
- **E2 — API The Game Crafter pour envoyer le deck** : gabarits d'abord ;
  l'envoi automatique demande un compte et une clé — à instruire plus
  tard si P1 ne suffit pas.

**Coût de patch** : `/cardforge/` est autonome (hors bundle) — P3, P4
(grille, histogrammes), P5, D1 (bouton), D3 y sont bon marché ; P1, P2 et
les moteurs (exports, miroir, traduction, objets 3D, PDF) sont backend
(`services/cards/*`, `print3d.py`).

### R10e. Game Assets — 3D, les moteurs image → 3D — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `asset3d_service.py`
ENGINES et BESOINS_3D, `meshy_service.py`, `mesh_optimize.py`,
`mesh_sources.py`, `pricing.py`, `frontend/meshy/meshy.client.js`, route
`/assets3d/engines`) : **6 moteurs fal** — Tripo v2.5 (multi-vues 4, PBR,
5 formats), Tripo H3.1 (le seul avec budget de faces, quad et graine),
Hunyuan3D v2, Trellis, Hyper3D Rodin (le seul à demander une T-pose),
TripoSR (0,07 $, brouillon) — prix par moteur de 0,07 à 0,48 $ affiché
avant tir, grisé sans clé ; matrice besoin → moteur (hero = Tripo H3.1
pour le volume puis **texture Meshy** depuis les mêmes 4 vues) ; 4 vues
quasi-orthographiques générées par un modèle image ; **Meshy par proxy
sécurisé** (clé jamais côté client) avec remesh, convert, resize,
uv-unwrap, **rigging, animations**, retexture — crédits estimés avant
action, binaires rapatriés ; décimation locale gratuite par gltfpack (8
presets, micro 500 → ultra 100 000, Game Ready 10 000) avec stats
avant/après ; versions, comparaison, rapport, QC, silhouettes IoU ;
`print3d` STL/3MF. Absents : génération locale, retopologie locale, rig
par Tripo, LOD en chaîne, mesure de perte après décimation, budget par
usage, export PBR aux conventions moteur, cuisson locale, matière du
Forge appliquée au modèle, conversion locale de formats, vues depuis la
bible, retouche des vues avant tir, photos depuis le téléphone, banc de
référence par sujet.

**Réponses**
1. Local : **oui, un service local optionnel** (comme Voicebox) ; carte
   graphique **non précisée**.
2. Retopo : **les deux** — fournisseur (Tripo H3.1, Meshy remesh) quand
   disponible, local sinon.
3. Rig : **rig auto + animations de base par le fournisseur**, GLB animé
   rapatrié et montré.
4. Comparaison : **un banc de référence par sujet type** (personnage,
   objet, véhicule), la matrice s'en nourrit.
5. Low-poly : **LOD en chaîne, mesure de la perte, budget par usage** — les
   trois.
6. Texture : **PBR exporté aux conventions moteur, résolution + cuisson
   locale, matière du Forge appliquée** — les trois.
7. Formats : **conversion locale de tout modèle**.
8. Vues : **depuis la planche de la bible, contrôle et retouche avant
   tir, photos réelles depuis le téléphone** — les trois.

**Références vérifiées le 03/09/2026**
- Meshy API : rigging (modèles humanoïdes texturés, **≤ 300 000 faces**,
  remesh d'abord sinon), animations de marche/course incluses, remesh
  (cibles glb, fbx, obj, usdz, blend, stl, 3mf), retexture
  (docs.meshy.ai, 03/09). Le proxy de l'app allowliste déjà ces chemins et
  le client JS les expose (mesuré) — le rig Meshy est donc **déjà
  atteignable** ; ce qui manque est de le relier au flux fal (`assets3d`)
  et d'afficher le GLB animé.
- Tripo API : Smart Mesh (retopo triangles 500–50 000, **quad 500–25 000**),
  auto-rig avec `rig-check`, 100+ mouvements prédéfinis, API asynchrone
  avec push (developers.tripo3d.ai, 03/09). L'app passe par fal pour
  Tripo : le rig Tripo demande l'API directe (clé Tripo séparée).
- Hunyuan3D 2.1 (local) : **10 Go de VRAM** pour la forme, 21 Go texture,
  29 Go les deux ; RTX 30 ou plus récent ; versions communautaires
  optimisées à 3–6 Go ; Python 3.10, PyTorch 2.5 (github.com/Tencent-Hunyuan,
  03/09). Sans la carte graphique de l'utilisateur, le service local
  reste conditionnel.
- TripoSR, InstantMesh, Luma Genie, quadriflow/Instant Meshes : de
  mémoire, non vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Rig et animations reliés au flux** : un modèle `assets3d` (fal)
  envoyé au rig Meshy (remesh automatique au-delà de 300 000 faces,
  crédits affichés), GLB animé rapatrié, lu dans le viewport, exporté ;
  Tripo rig en option si l'API directe entre un jour.
- **P2 — LOD en chaîne + mesure de perte** : 3 niveaux gltfpack exportés
  ensemble (nommage moteur), fidélité par niveau mesurée (IoU de
  silhouettes déjà présent, écart de normales), budget proposé par usage
  (mobile, PC, impression).
- **P3 — Export PBR aux conventions moteur** : `naming_catalog` des
  Matières (R10c) appliqué aux textures d'un modèle ; résolution choisie ;
  cuisson locale AO/normales (PIL, cyclique) quand le moteur ne les livre
  pas.
- **P4 — Conversion locale de formats** : GLB → OBJ/STL déjà en partie
  (print3d) ; FBX et USDZ demandent un outil embarqué (à choisir et
  mesurer : le format FBX est propriétaire, l'écriture libre est
  partielle — à dire dans le plan).
- **P5 — Contrôle des vues avant tir** : les 4 vues affichées, rejouables
  une à une, détourables, avant de payer le moteur 3D.

*Différenciant*
- **D1 — Vues depuis la planche de la bible** : les 4 vues d'une entité
  viennent de sa planche de référence (identité tenue, R3), pas d'un
  prompt neuf ; le modèle 3D rejoint la fiche de l'entité (déjà prévu par
  `/bible/entities/{id}/model3d`).
- **D2 — Banc de référence par sujet type** : personnage, objet, véhicule
  générés une fois sur chaque moteur, mesurés (triangles, IoU, poids,
  coût, durée), résultats rangés ; la matrice besoin → moteur cite ses
  chiffres.
- **D3 — Matière du Forge sur le modèle** : habiller un modèle nu avec une
  matière locale, par partie (R10c D2).
- **D4 — Service GPU local optionnel** partagé : Hunyuan3D pour le
  brouillon, CLAP (R4) et CLIP (R9) pour la recherche, retopo locale —
  un seul serveur à côté de l'app, détecté s'il tourne ; conditionné à
  la carte graphique (RTX 30+, 10 Go pour la forme).
- **D5 — Photos réelles depuis le téléphone** : 4 photos d'un objet
  tourné envoyées par le compagnon (R12) → détourage → moteur multi-vues.

*Écarté*
- **E1 — Génération locale sans service optionnel** : PyTorch n'entre pas
  dans le Python embarqué ; toujours un service à côté.
- **E2 — API Tripo directe** : fal suffit pour la génération ; à revoir si
  le rig Tripo devient nécessaire.

**Coût de patch** : `/studio3d` et le client Meshy sont autonomes (hors
bundle) — P1, P5, D1 (bouton), D2 (affichage) y sont bon marché ; l'écran
« 3D » du hub (DzGameAssets) est dans le bundle — P2, P3 (options) y
coûtent un patch ; les moteurs (LOD, cuisson, conversion, banc, service
local) sont backend.

### R10f. Game Assets — 3D Studio et l'Établi — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : plan
`2026-09-01-etabli-plaque-et-extraction.md` « Task 4 — LIVRÉE », `mesh_report.py`,
`mesh_edit.py`, `mesh_cut.py`, `print3d.py`, `frontend/etabli/`,
`frontend/studio3d/`) : `/studio3d` (graphe de la chaîne 3D, nœud 07 ·
établi) ; l'Établi — inspecteur (versions, A/B caméras synchronisées,
Parties par nœud/maillage/matériau, gizmo, vue isométrique et vues d'axe,
graduation et lecture x/y/z, taille cible → mm), **plaque façon slicer**
(règles graduées, glisser aimanté, flèches, rotation, plan de plaque
`plaque.v<N>.json`), **poser sur une face**, **couteau** (aperçu par plan,
capuchons, refus nommés), réparer l'assise, transformer, extraire ; fiche
de maillage (sha256, textures, boîte, **bords ouverts et arêtes
non-manifold → « fermé » ou non**, silhouettes) ; `print3d` STL/3MF en mm,
garde 256 mm Centauri Carbon 2, relief vitrail ; guide utilisateur FR/EN
(HTML + PDF) avec le chapitre impression 3D ; **campagnes de mutations dans
le dépôt** (77 + 45). Restent du plan : T5 extraction élément par élément,
T6 Bibliothèque hiérarchique, T4-bis (Measure, booléens, connecteurs,
auto-arrange, auto-orient), deux dettes (lecteurs d'accesseurs `sparse`,
contradiction assise/recentrer non dite), lecture chiffrée du glisser.
Absents : réparation en un clic, creusage et drainage, décimation dans
l'Établi, nesting vrai, profils d'imprimante, aperçu de tranchage,
lexique et guide de démarrage.

**Réponses**
1. Frontière : **préparation + aperçu de tranchage indicatif**, et, mot
   pour mot : « **un guide style tutoriel débutant pour accompagner
   l'utilisateur dans ses premières manipulations et préparations avant
   l'export vers le slicer. lexique explicatif avec des ressources liées
   aux meilleures pratiques enregistrées sur le net par type
   d'impressions, de machines, de slicer, et de filament, bref un vrai
   petit guide FR-EN pour démarrer** ».
2. Réparation : **les deux — un clic, et le détail si je veux** (le bouton
   fait tout, le panneau dit ce qu'il a fait, annulable).
3. Creusage : **creusage + drainage + décimation dans l'Établi**.
4. Nesting : **auto-arrange vrai** (rotation, espacement, plusieurs
   plateaux).
5. Profils : **profils d'imprimante (Centauri Carbon 2 par défaut + autres)
   ET import des profils d'Orca/Elegoo Slicer**.
6. Envoi : **l'association de fichier suffit**.
7. Outils 4-bis : **Measure, connecteurs du couteau, booléens, auto-orient**
   — les quatre, dans cet ordre.
8. Reste : **T5, T6, lecture chiffrée du glisser, et les deux dettes** —
   tout.

**Références vérifiées le 03/09/2026**
- OrcaSlicer, section *Prepare* : inventaire relevé le 02/09 dans le plan
  Établi (Move, Rotate, Scale, Lay on face, Auto-orient/arrange, Split,
  Cut avec connecteurs dovetail/dowel/plug/snap, Mesh boolean, Measure,
  Emboss, peintures, variable layer height, assembly view).
- Elegoo Centauri Carbon 2 : LAN Only + IP + code d'accès dans Elegoo
  Slicer (qui sait lancer l'impression) ; OrcaSlicer n'envoie que le
  fichier, pas « upload and print » (wiki.elegoo.com,
  github.com/OrcaSlicer, 03/09). Écarté par la réponse 6, gardé en note.
- Microsoft 3D Builder : **déprécié en juillet 2024**, retiré du Store
  (des installations résiduelles subsistent) (learn.microsoft.com, 03/09).
- Autodesk Meshmixer : plus développé ni supporté (2017), encore
  téléchargeable (autodesk.com, 03/09). Les deux références « réparation
  en un clic » du brief sont en fin de vie : l'Établi peut prendre la
  place.
- MeshLab, Netfabb, Formware, Bambu Studio, PrusaSlicer : de mémoire, non
  vérifiés.

**Bacs**

*Parité nécessaire*
- **P1 — Réparer en un clic + détail** : trous bouchés (boucles de bord →
  capuchons, mécanique du couteau), normales unifiées (orientation
  cohérente par propagation), faces dupliquées et sommets confondus
  retirés ; compte rendu par action, version écrite par `mesh_edit`
  (seule plume), annulable ; le banc lit le maillage réparé (fermé ou
  non, mesuré par `mesh_report`).
- **P2 — Profils d'imprimante** : Centauri Carbon 2 par défaut (256 mm,
  hauteur, zones exclues), autres à la main, **import** des profils
  d'OrcaSlicer/Elegoo Slicer installés (JSON lus, jamais écrits) ; la
  garde 256 mm devient une propriété du profil.
- **P3 — Auto-arrange vrai** : placement avec rotation et espacement,
  débordement sur un second plateau ; heuristique par boîtes puis
  silhouettes (nesting 2D en Python pur, mesuré au taux d'occupation).
- **P4 — Creusage + drainage + décimation** : paroi en mm (offset vers
  l'intérieur, Python pur — lourd, à mesurer sur 100 000 triangles),
  trous placés au clic sur la plaque, décimation gltfpack reliée à
  l'Établi.
- **P5 — Measure** : deux points → distance, deux faces → angle, avec le
  repère de T3.
- **P6 — T5 extraction + T6 Bibliothèque hiérarchique + lecture chiffrée
  du glisser + les deux dettes** : le reste du plan Établi, tel quel.

*Différenciant*
- **D1 — Guide de démarrage FR/EN dans l'Établi** : tutoriel pas à pas
  (premières manipulations → export), **lexique** (assise, surplomb,
  support, brim, raft, remplissage, couture, rétraction…), ressources
  liées par type d'impression, machine, slicer et filament — vérifiées et
  datées, jamais « de mémoire » ; livré dans le guide (chapitre 20 étendu)
  et en aide contextuelle dans l'écran. Aucun préparateur ne guide un
  débutant.
- **D2 — Aperçu de tranchage indicatif** : couches simulées (sans G-code)
  pour voir surplombs et zones à supporter avant d'ouvrir le slicer ;
  coloration des surplombs par angle dans le viewport.
- **D3 — Connecteurs du couteau** : téton, queue d'aronde, cheville posés
  sur le plan de coupe, géométrie ajoutée aux deux moitiés.
- **D4 — Booléens** : union, différence, intersection en Python pur
  (algorithme à choisir et mesurer ; le plan dira son coût en temps sur
  des maillages de 50 000 triangles).
- **D5 — Auto-orient** : orientation proposée par surface de support et
  surplombs, appliquée par le mécanisme « poser sur une face ».

*Écarté*
- **E1 — Mini-slicer complet, peinture de supports, hauteurs de couche
  variables** : métier du slicer, réponse 1.
- **E2 — Envoi réseau à l'imprimante et suivi** : réponse 6 ; l'association
  de fichier suffit.

**Coût de patch** : l'Établi et `/studio3d` sont autonomes (hors bundle)
— bon marché ; T6 touche l'onglet Établi de la Bibliothèque (bundle) ;
tout le reste est backend (`mesh_edit.py`, `mesh_cut.py`, `mesh_report.py`,
`print3d.py`, nouveaux modules `mesh_repair`, `nesting`, `hollow`) avec
campagnes de mutations comme précédent.

### R11. Settings — réponses (03/09/2026)

**Ce que le code fait aujourd'hui** (relu le 03/09 : `config.py`, routes
`/settings/keys`, `/settings/provider-defaults`, `/atelier/settings`,
`/persona`, `/health`, `/cost/*`, `/branding`) : clés dans un fichier
`.env` **en clair** sous `DATA_ROOT` (fal, ElevenLabs, HeyGen, Meshy,
Figma, Anthropic, OpenAI, Gemini, Telegram, X ×4), jamais renvoyées en
clair (état « définie » + aperçu masqué) ; défauts par fournisseur ;
réglages Atelier ; persona ; santé (version, fournisseurs joignables,
Voicebox détecté) ; **coûts** : estimation avant tir, usage cumulé
**estimé** par fournisseur depuis les jobs finis, **soldes en direct**
quand l'API les expose (HeyGen crédits, ElevenLabs caractères), grille de
prix éditable ; kit de marque minimal. Absents : profils, export/import
chiffré, diagnostic en un écran (test des clés, disque, journal),
plafonds de dépense, coffre chiffré, sauvegarde, test de clé à
l'enregistrement, guides par fournisseur, recherche dans les réglages,
vérification de mise à jour.

**Réponses**
1. Profils : **non**.
2. Export/import : **archive chiffrée avec clés et défauts** (mot de
   passe), pour un second poste et le mobile.
3. Diagnostic : **clés testées en direct, crédits et soldes par moteur,
   disque/poids/version/journal, dépenses du mois par moteur et par
   catégorie** — les quatre.
4. Plafonds : **par moteur et global, mensuels, confirmation au
   dépassement** (alerte à 80 %).
5. Coffre : **mot de passe maître**.
6. Sauvegarde : **export manuel à la demande** vers un dossier choisi.
7. Saisie : **test à l'enregistrement, guide par fournisseur, recherche
   dans les réglages** — les trois.
8. Mises à jour : **vérification + notes + téléchargement en un clic**.

**Références et contraintes (03/09/2026)**
- 1Password/Bitwarden, Raycast, VS Code, Docker Desktop, Obsidian : de
  mémoire, non vérifiés — non utilisés comme argument.
- **Contrainte mesurée** : le Python embarqué est stdlib pure (numpy
  absent, mesuré le 27/08 et rappelé dans `print3d.py`) ; la stdlib n'a
  **pas d'AES**. Un coffre à mot de passe maître exige soit une
  bibliothèque (`cryptography`, roue Windows à embarquer au build — à
  mesurer), soit DPAPI par `ctypes` (stdlib, lié au compte Windows, sans
  mot de passe). Le plan Settings commence par cette mesure ; l'archive
  chiffrée (réponse 2) partage la même décision.
- GitHub Releases : l'API publique `releases/latest` donne version et
  notes (de mémoire, API publique stable ; à vérifier au plan avec un
  appel réel). L'installeur est déjà l'asset de Release (README).
- Dépenses : le registre existant est **estimé** (grille de prix ×
  paramètres) ; seuls HeyGen et Meshy renvoient un coût réel consommé.
  Le tableau de bord doit dire « estimé » ou « réel » par ligne.

**Bacs**

*Parité nécessaire*
- **P1 — Diagnostic en un écran** : test en direct de chaque clé (appel
  léger par fournisseur, vert/rouge avec le message), soldes (`/cost/
  balances` étendu), disque et poids de `DATA_ROOT` par catégorie (R9 P6),
  version, journal des dernières erreurs ; un seul écran, rafraîchi à la
  demande.
- **P2 — Plafonds de dépense** : budget mensuel par moteur et global,
  compteur depuis `/cost/usage` (estimé) + coûts réels quand connus,
  alerte à 80 %, confirmation inline au dépassement avant tout tir ; la
  garde vit dans le backend (route de génération), pas seulement dans
  l'UI.
- **P3 — Test de clé à l'enregistrement + guide par fournisseur** : au
  clic « enregistrer », l'appel de test dit si la clé marche ; à côté, le
  lien où créer la clé, le plan et le coût, FR/EN (vérifiés et datés).
- **P4 — Vérification de mise à jour** : `releases/latest` interrogé au
  démarrage (une fois par jour), bandeau + notes de version, téléchargement
  de l'installeur en un clic ; l'utilisateur lance l'installeur.
- **P5 — Export manuel des données** : copie de `DATA_ROOT` (base +
  assets) vers un dossier choisi, avec manifeste et vérification
  d'intégrité (sha256 par fichier), progression affichée.

*Différenciant*
- **D1 — Coffre à mot de passe maître + archive chiffrée** : les clés
  chiffrées au repos, déverrouillées au lancement ; la même clé chiffre
  l'archive de configuration exportée pour un second poste ou le mobile
  (R12) ; la décision technique (bibliothèque embarquée ou DPAPI) est la
  première tâche du plan, mesurée.
- **D2 — Dépenses par catégorie, réel contre estimé** : le tableau de
  bord distingue ce que l'app a estimé de ce que le fournisseur a
  facturé, par moteur et par catégorie du rail ; aucune référence
  grand public ne rapproche les deux.
- **D3 — Recherche dans les réglages** : un champ qui filtre tous les
  réglages (clés, défauts, kits, profils d'imprimante, plafonds) et
  ouvre la bonne section, façon VS Code.

*Écarté*
- **E1 — Profils de configuration** : réponse 1.
- **E2 — Sauvegarde programmée** : réponse 6 ; export manuel seulement.
- **E3 — Coffres multiples façon Obsidian** : un seul `DATA_ROOT`.

**Coût de patch** : l'écran Settings est dans le bundle — P1, P2 (alertes),
P3, P4 (bandeau), D3 sont des patches chaînés ; les moteurs (tests de
clés, plafonds, export, coffre, mise à jour) sont backend (`config.py`,
`env_service`, `pricing.py`, nouveau module de coffre).

### R12. L'application mobile compagnon — réponses (03/09/2026)

**Ce que l'architecture impose, remesuré le 03/09** (`config.py`,
`main.py`, `routes.py`) : `HOST = "127.0.0.1"`, `PORT = 8765` ; garde CSRF
`_csrf_origin_guard` — les requêtes non-GET dont l'`Origin` n'est pas
127.0.0.1 / localhost / ::1 sont refusées (403), **les requêtes sans
`Origin` (curl, application native) passent** ; `_require_localhost` sur
les routes des clés (`/settings/keys`) refuse tout client non loopback
même si HOST était ouvert ; clés dans `.env` en clair sous `DATA_ROOT` ;
données locales de plusieurs Go ; aucun appairage, aucun jeton d'appareil
dans le code. La boucle du Scheduler tourne dans le backend : PC éteint,
rien ne part.

**Réponses**
1. Besoin réel, par fréquence : **1) valider ou reporter des posts,
   publier à la main ; 2) relancer, varier, cloner un rendu ; 3) écrire
   ou relire un chapitre, annoter un rendu ; 4) envoyer une photo, un
   lien, une idée vers l'app**.
2. Doit aboutir sans le PC : **la publication à l'heure, une génération
   par moteur en ligne, l'écriture**.
3. PC allumé ou réveillable : **non — le PC est vraiment éteint (portable,
   déplacements)**. La lecture A est donc **hors sujet** : la
   recommandation du brief (A d'abord) tombe sur ce fait, mesuré par la
   réponse.
4. Architecture : **B — le téléphone travaille seul** ; pas d'hôte
   permanent déclaré.
5. Clés : **oui, par l'archive chiffrée de Settings (R11 D1),
   déverrouillée par mot de passe**, stockées dans le coffre système du
   téléphone.
6. Sync : **seulement dans mon réseau (Wi-Fi maison), sync au retour** ;
   aucun service tiers.
7. Forme : **native, iPhone ET Android** (réponse « 1+2 ») — donc une base
   de code multiplateforme native, ou deux apps ; le plan chiffre.
8. Partages entrants : **photo → Bibliothèque/Quick/Material Forge/3D ;
   lien ou article → News ; texte ou idée → Chapitres ou brief** — les
   trois.
9. Notifications : **rendu terminé ou échoué, post à publier / publié /
   échoué, plafond approché ou dépassé, synchronisation terminée ou en
   conflit** — les quatre.
10. Dépenses : **confirmation avec coût affiché + plafond journalier
    propre au mobile**.
11. Appairage : **QR + jeton révocable, plusieurs appareils** (tablette,
    second téléphone, jusqu'à cinq nommés).
12. Téléphone perdu : **révocation + rappel de régénérer les clés chez
    chaque fournisseur** (liste avec liens vers chaque console).
13. Bibliothèque : **index complet (vignettes) + projets épinglés en
    entier**.
14. Conflits : **verrou — un chapitre « emporté » est en lecture seule
    sur le PC**, libéré au retour.
15. Générations sur le téléphone seul : **images et retouches, clips
    vidéo et extension, voix off et musique, texte par LLM** — tout.
16. Premier lot : **publier à l'heure et valider le lot de la semaine**.

**Références vérifiées le 03/09/2026**
- Web Share Target (recevoir un partage dans une PWA) : Android/Chrome
  avec PWA installée ; **pas sur iOS Safari** (developer.mozilla.org,
  web.dev, bugs.webkit.org, 03/09) → la réponse 8 sur iPhone exige une
  application **native**, ce que la réponse 7 dit déjà.
- Web Push iOS : seulement pour les web apps ajoutées à l'écran d'accueil
  depuis 16.4, sur geste utilisateur (webkit.org, 03/09) — sans objet en
  natif, gardé pour mémoire.
- Réseaux (R6) : X gratuit 500 posts/mois ; Instagram 50 posts/24 h en
  compte pro ; YouTube 100 envois/jour ; TikTok privé sans audit — les
  mêmes bornes valent depuis le téléphone, avec les **mêmes jetons**
  (dupliqués par l'archive).
- Exécution en arrière-plan à heure fixe sur iOS (publier à 9 h 00 sans
  ouvrir l'app) : **de mémoire, à vérifier au plan** — iOS ne garantit pas
  une tâche de fond à l'heure exacte ; la voie sûre est une notification
  locale à l'heure qui ouvre l'app et publie au premier plan, la
  publication silencieuse restant un objectif mesuré, pas promis. Android
  (WorkManager, alarmes exactes) est plus permissif — à vérifier aussi.
- Postiz (R6) reste le candidat si un relais permanent revenait un jour
  (lecture C) ; écarté ici par les réponses 4 et 6.

**Ce que B veut dire, sans détour**
- Le téléphone est un **second poste** avec son propre magasin (base
  locale, coffre de clés, cache d'assets), qui parle aux **mêmes
  fournisseurs** avec les **mêmes clés**, et qui produit les **mêmes
  fichiers** (rendus, posts, chapitres, recettes) que le PC.
- La **synchronisation** est un protocole maison sur le Wi-Fi maison :
  découverte du PC (mDNS), jeton d'appareil, transfert des assets et des
  états dans les deux sens, verrous par chapitre, journal des conflits.
  Le backend doit **écouter sur le LAN** (HOST configurable, plus
  127.0.0.1 seul) **et** exiger le jeton d'appareil sur toute route hors
  loopback ; `_require_localhost` reste tel quel : le téléphone ne lit
  **jamais** les clés depuis le backend, il les reçoit par l'archive
  chiffrée (R11 D1). La garde CSRF laisse passer les requêtes sans
  `Origin` (mesuré) : ce n'est pas une brèche tant que le jeton est exigé
  — le plan le pose en première tâche.
- Les **plafonds** (R11 P2) et le **registre des coûts** deviennent
  partagés : le téléphone compte ses tirs, le PC les fond au retour ; le
  plafond journalier mobile est local au téléphone.
- Le **Scheduler** (R6 D1) devient bicéphale : le lot validé est copié
  sur le téléphone avec vidéos, légendes, heures et jetons ; le
  téléphone publie (ou rappelle) à l'heure ; l'état revient au PC.

**Bacs**

*Parité nécessaire (ce sans quoi le compagnon ne tient pas)*
- **P1 — Appairage et jeton** : QR affiché par le PC (adresse LAN + secret
  à usage unique), jeton d'appareil révocable, jusqu'à cinq appareils
  nommés dans Settings ; le backend écoute sur le LAN et refuse toute
  requête non loopback sans jeton ; `_require_localhost` intact.
- **P2 — Archive chiffrée → coffre du téléphone** : la même archive que
  R11 D1 (mot de passe maître), lue par le téléphone, clés dans
  Keychain/Keystore ; révocation depuis le PC + liste des clés à faire
  tourner avec les liens des consoles.
- **P3 — Premier lot : le Scheduler dans la poche** : lot de la semaine
  validé sur le téléphone, publication à l'heure (X, Telegram par API ;
  Instagram, YouTube, TikTok par API quand les adaptateurs de R6 P1
  existent, sinon par partage vers l'app native du réseau), notification
  à l'heure, état renvoyé au PC ; le comportement en arrière-plan est
  **mesuré** sur iPhone et Android avant d'être promis.
- **P4 — Synchronisation LAN au retour** : index complet des vignettes,
  projets épinglés copiés en entier, rendus et générations du téléphone
  rapatriés avec leur recette et leur lignée (R9 P3), verrous de
  chapitre, journal des conflits, notification de fin.
- **P5 — Notifications** : rendu terminé/échoué, post à publier/publié/
  échoué, plafond, synchronisation — natives.
- **P6 — Dépenses** : coût affiché et confirmation par tir, plafond
  journalier mobile, compteur fondu au registre du PC.

*Différenciant*
- **D1 — Générer dans la poche, ranger au retour** : images, clips (avec
  extension), voix, musique, texte LLM par les mêmes moteurs, les
  résultats rangés dans la Bibliothèque du PC avec recette et lignée à la
  synchronisation ; « Rouvrir dans Quick » (R1 P1) marche des deux côtés.
  Aucun studio local n'a de second poste mobile qui produit les mêmes
  fichiers.
- **D2 — Partages entrants triés** : photo, lien, texte reçus par le
  partage système et rangés vers Bibliothèque/Quick/Material Forge/3D,
  News, Chapitres/brief — chaque cible reprend la mécanique de son écran.
- **D3 — Écrire hors ligne sous verrou** : chapitre « emporté » en
  lecture seule sur le PC, édité sur le téléphone, versionné (R3 P2),
  libéré au retour ; annotations horodatées (R9 D2).
- **D4 — Recette lançable depuis le téléphone** (R2 D1) : un graphe
  sauvegardé lancé avec de nouvelles sources depuis le mobile, exécuté
  par le téléphone (moteurs en ligne) ou mis en file pour le PC.

*Écarté*
- **E1 — Lecture A (télécommande + Wake-on-LAN)** : le PC est vraiment
  éteint ; ne pas construire un tunnel pour un PC absent.
- **E2 — Lecture C (relais permanent)** : pas d'hôte, aucun service tiers
  voulu ; Postiz reste une note.
- **E3 — PWA** : Web Share Target absent sur iOS (mesuré) et coffre
  système hors de portée ; natif.
- **E4 — Fusion automatique des textes** : verrou choisi ; plus simple et
  sans surprise.
- **E5 — Effacement à distance des clés** : contredit « seulement dans
  mon réseau » ; révocation + rotation à la place.

**Coût** : le compagnon est un **nouveau dépôt** (application native
multiplateforme) plus, côté PC : LAN + jeton (backend), archive chiffrée
(R11 D1), routes de synchronisation et de verrou, Scheduler bicéphale —
tout backend, sans patch du bundle sauf la page d'appairage dans Settings
(un patch). Le plan mobile se découpe en lots : P1+P2 (socle), P3 (premier
lot), P4+P5+P6, puis D1–D4 ; chaque lot mesure ce qu'iOS et Android
permettent réellement avant de le promettre.
