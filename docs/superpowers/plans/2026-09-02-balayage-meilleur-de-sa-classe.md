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
