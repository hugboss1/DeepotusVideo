# Lot « appliques_experts » — skills appliqués Scenario + survol des experts DCC / moteurs

Source : scenario-labs/skills @ b96506d (08/11/2026), licence MIT. Lecture du 09/11/2026.
Convention : « CU » = Creative Units Scenario (≈ crédits ; ordre de grandeur relatif, pas un prix fal).
Les ids Scenario cités (`model_openai-gpt-image-2-5-sunburst`, etc.) sont donnés tels quels pour
faire la correspondance avec les ids Deepotus.

---

# PARTIE 1 — Skills appliqués (lecture complète)

## 1. scenario-ad-variants

**Résumé.** Décliner une vidéo publicitaire existante en N variantes indépendantes (accroche, CTA,
carton final, format, retouche visuelle ciblée). Famille : montage / vidéo-édition (video2video) +
compositeur déterministe.

- [MÉTHODE] Chaque variante part de la SOURCE, jamais de la variante précédente ; une révision part
  de la variante choisie. Enregistrer par variante : source, delta voulu, invariants, texte exact,
  sortie, politique audio, payload réellement envoyé, job id, QA.
- [CHOIX] Texte (accroche/CTA/carton) = opération déterministe (carte texte rendue + composition),
  jamais un modèle génératif. Remplacement de fond/vêtement/objet = membre « video-edit »
  (video2video). Nouveau plan/concept = autre chantier (pub depuis image fixe).
- [PIÈGE] Sur une capture de gameplay, un remplacement de fond génératif peut altérer géométrie, UI
  ou mécanique : ne jamais présenter le résultat comme du gameplay fidèle ; « prompt de
  préservation = demande à vérifier, pas une garantie ».
- [PIÈGE] Ne jamais importer les limites de durée/longueur de prompt d'un autre fournisseur : lire
  le schéma du modèle choisi.
- [PIÈGE] Changer musique + étalonnage + accroche ensemble invalide une comparaison A/B « copie
  seule ». Pas de produit cartésien de variantes sauf demande.
- [PARAM] Compositeur Scenario : pas de 0,1 s (« seconds in 0.1 increments ») ; fps entier ; fit
  `contain` sinon recadrage non autorisé ; vérifier les images juste avant/à/après chaque borne
  (borne inclusive ou non inconnue).
- [MÉTHODE] QA d'une édition générative : planche-contact sur toute la durée + images autour des
  changements (pas seulement première/dernière) : identités, textes d'origine, objets hors zone,
  continuité d'action, audio. Si l'audio généré diffère, remettre la piste source SEULEMENT si
  l'image reste calée (une action retimée + audio d'origine ≠ synchro).
- [COÛT] Devis (dry run) de chaque payload exact avant lancement ; en cas d'échec ne relancer que la
  variante en échec (garder son label).

**Correspondance Deepotus.** Concerne le Montage + édition vidéo (aucun id video2video « edit » dans
le registre listé ; Kling O-series / Seedance edit / Runway Aleph-type seraient les candidats —
probablement sur fal). Paramètre absent : pas de notion de « variante + invariants » dans les
registres ; le compositeur Deepotus (ffmpeg local) couvre la partie texte.
**Propre à Scenario.** `model_scenario-compose-video`, `asset_get`, `jobs_wait`, `recommend`.

## 2. scenario-admin-analytics

Une ligne : rapports de consommation CU par modèle/utilisateur/projet (CSV, PDF, tableau de bord)
depuis l'API `usage` Scenario. Seul fait transposable : [MÉTHODE] un coût « modèle » ne somme pas
forcément au total consommé (remboursements, opérations non-modèle) ; ne pas forcer l'égalité,
afficher l'écart — utile pour les Dépenses réel/estimé de Deepotus. Rien sur les modèles eux-mêmes.

## 3. scenario-blender

**Résumé.** Piloter l'extension « Scenario for Blender » (serveur MCP local 127.0.0.1:9876) :
générer images, matériaux PBR, maillages 3D, vidéo, audio, panoramas 360 depuis la scène. Famille :
3D (img23d), matériaux, panorama, rendu-vers-vidéo.

- [PARAM] Couloirs (lanes) exposés : `image`, `video`, `3d`, `material`, `audio`, `render_image`,
  `render_video`, `edit3d`, `panorama` — bonne grille de familles pour un catalogue 3D.
- [MÉTHODE] Référence image depuis la scène : capture viewport/caméra/clip, ou maillage
  sélectionné exporté en GLB (`MESH`) comme entrée.
- [PIÈGE] Render Image / Render Video (rendu IA depuis la capture) : « le modèle copie le mouvement
  de la capture, membres compris » → pour un perso qui doit marcher/courir naturellement, bloquer
  en capsules (blockout), pas en mannequin articulé raté.
- [MÉTHODE] Panorama → placé comme World (HDRI) de Blender.
- [MÉTHODE] Résultat 3D jamais importé automatiquement : devis exact → accord → génération →
  application au curseur 3D après approbation (seule l'image s'importe seule).
- [COÛT] Devis gratuit (`estimate_cost`) avant toute génération, accord explicite sur le montant
  exact ; un devis ne sert qu'une fois et tout changement (modèle, entrée, scène) en exige un neuf.
- [PIÈGE] Ne jamais relancer une génération expirée côté client : interroger l'état du job (sinon
  double dépense).

**Correspondance Deepotus.** Imprimante 3D / Établi / Plateau 3D, ids meshy-6/7/7.1, rodin-2.5,
tripo, hunyuan3d, trellis-2, triposr (image→3D). Manques : couloir « material » (PBR à partir de
texte/image) et « panorama 360 » (HDRI génératif) — Deepotus a « Matières » et HDRI mais pas de
fiche modèle ; « edit3d » (retouche de maillage par IA) absent. Paramètre absent : devis gelé +
accord du montant exact (Deepotus a plafonds/estimé).
**Propre à Scenario.** Serveur MCP local, jetons bearer, `apply_result_application`.

## 4. scenario-storyboards

**Résumé.** BD, planches, storyboard, animatique : l'unité de génération est la CASE, jamais la
page. Famille : image txt2img/img2img avec références de personnage + lettrage en post.

- [MÉTHODE] Ordre : script (tableau de beats) → verrouillage du casting (une image héros approuvée
  par perso) → une génération par case → revue → lettrage en post → montage de page.
- [PROMPT] Chaque prompt = ligne de style + description de base du personnage + ligne de décor
  (lieu, heure) — **identiques à l'octet** entre cases — + la clause propre à la case (plan,
  action) + « clean art, no lettering, no speech bubbles ».
- [PROMPT] Étiqueter la case comme une liste de plans : numéro, valeur de plan, angle, objectif ou
  mouvement, puis action avec côté de cadre et orientation de chaque perso. Respecter l'axe (180°),
  monter l'échelle des valeurs avec la tension, ponctuer d'inserts/réactions.
- [PROMPT] La colonne action ne contient que ce qu'une caméra voit : pensée, odeur, passé → rien à
  l'écran ; les transformer en indice visible ou en récitatif.
- [PIÈGE] « Same character as before » : aucune mémoire entre appels, restater toute la base.
- [PIÈGE] Chaîner case N → case N+1 en référence : la dérive s'accumule ; ancrer chaque case sur le
  même héros approuvé.
- [PIÈGE] Changement durable (nouveau costume dès la case 4) : la référence ramène l'ancien
  costume → générer un 2e héros depuis le 1er, l'approuver, réécrire la base.
- [PIÈGE] Plusieurs héros dans une case : dire le rôle de chaque référence, vérifier que le plafond
  de références du modèle couvre le casting ; figurants génériques, non nommés.
- [PIÈGE] Paramètre « nombre de sorties » = même prompt répété : ne peut pas porter des clauses par
  case.
- [PIÈGE] Case d'action bloquée par modération (arme, combat) : adoucir la clause de CETTE case
  (dé-emphaser l'arme), relancer depuis la base.
- [CHOIX] Si le style vient d'un LoRA sans champ de référence adapté : garder le LoRA pour le héros
  et un modèle à références pour les cases, en restatant la ligne de style.
- [COÛT] Animatique : n'animer (image→vidéo, un clip par plan) que des cases approuvées — l'image
  est bon marché, la vidéo non. Si le mouvement doit traverser les coupes, chaîner pose de sortie →
  pose d'entrée (Seedance storyboard), sinon la performance repart de zéro à chaque coupe.

**Correspondance Deepotus.** Ids image à références : nano-banana(-pro, -2.1), gpt-image-1/2/2.5,
seedream-5-pro, flux-3 ; vidéo pour l'animatique : seedance-2/2.5, kling-v3/v4, veo-3.1. Paramètre
absent dans les registres : « plafond de références » par modèle et « rôle » de chaque référence.
**Propre à Scenario.** LoRA de style publics, `model_run`, `jobs_wait`, outil grille.

## 5. scenario-fan-cam

**Résumé.** Insérer une personne (photo) dans un plan « caméra de stade / jumbotron » puis l'animer.
Famille : image edit identitaire (img2img multi-réf) → image-to-video.

- [MÉTHODE] Deux étages : (1) édition image identitaire → plan fixe 16:9 « diffusion TV » ;
  (2) image-to-video depuis ce plan approuvé. **La photo est une référence d'identité, jamais
  l'image de départ** (sinon on anime un portrait, pas une retransmission).
- [COÛT] L'étage 1 est bon marché, l'étage 2 non → toutes les décisions se valident sur le plan fixe.
- [PROMPT] Grammaire « broadcast » explicite aux deux étages : longue focale compressant la foule
  floue devant/derrière, projecteurs durs ou stroboscopes d'arène, léger flou de bougé, caméra qui
  « cherche » et recadre ; sujet en plan moyen, décentré, dans la foule, à hauteur de caméra TV.
  Sujet centré bien éclairé à hauteur d'yeux = « séance photo dans un stade ».
- [PROMPT] Donner un ARC à la réaction (inattentif → remarque la caméra/l'écran → réaction voulue),
  en plusieurs temps (multi-beat) dans un seul clip ; un seul mouvement de caméra (recadrage lent).
- [PROMPT] Édition : « no text, logos, or graphics in frame » ; plaque sans texte.
- [PIÈGE] Le texte généré (panneaux, jumbotron) apparaît malgré le négatif, surtout **en fin de
  clip** → vérifier image du milieu et de fin ; tout graphisme (score, logo chaîne) en post.
- [PIÈGE] Relancer depuis le clip dérivé au lieu du plan approuvé : les erreurs s'additionnent.
- [PARAM] `duration` souvent un enum fixe ; les paliers qui atteignent la durée voulue sont très
  écartés en prix → comparer les devis par candidat.
- [PIÈGE] Visages réels → filtres fournisseurs plus fréquents ; refuser célébrités/inconnus.
- [MÉTHODE] Contrôle d'identité : inventaire des traits (géométrie du visage, implantation, teint,
  tenue) ; tout changement = échec ; vérifier première, milieu, dernière image.
- [MÉTHODE] Déclinaisons 9:16 / 1:1 depuis le master 16:9 ; un « resize » vidéo génératif
  outpainte (n'est pas un recadrage) ; recadrage centré coupe un sujet décentré → positionner sur
  un canevas 9:16.

**Correspondance Deepotus.** Image edit : nano-banana-pro/-2.1, gpt-image-2(.5), seedream-5-pro,
qwen-image-3 ; vidéo : kling-v3/v4, seedance-2/2.5, veo-3.1, h3-max. Paramètre manquant : nombre de
références images par modèle d'édition ; « temps » (multi-beat) non formalisé.
**Propre à Scenario.** `recommend`, collections, `model_scenario-video-to-image-seq`.

## 6. scenario-reel-recast

**Résumé.** Refaire une vidéo virale (danse, Reel, TikTok) avec un autre interprète en gardant
chorégraphie, timing, caméra, cadrage, et la chanson d'origine. Famille : video2video « edit mode »
de Seedance avec références images.

- [PARAM] Seedance edit mode : la vidéo source = `@video1` (dans `referenceVideos`), images de
  référence `@image1..n` dans l'ordre de `referenceImages`, `duration: -1` (= durée de la source),
  `generateAudio: false`, `draft: true` pour les essais (480x854) puis « completion » 1080x1920 des
  seuls choix.
- [PARAM] Sortie observée : source 30 fps → **sortie 24 fps** ; durée à quelques images près
  (« 14.87 s gave 14.71 s, 6.00 s gave 6.04 s ») → planifier depuis la sortie, pas la source.
- [COÛT] Brouillons edit mode : « 366 CU for 15 s, 148 CU for 6 s » ; N prises par tenue ; ne
  « compléter » en 1080p que les élues.
- [PROMPT] Recette qui a tenu (3 tenues, 9 prises) :
  1. Échange : « Edit @video1: replace the dancing woman with the woman from @image1 » (+ « wearing
     the dress from @image2 », + « redecorate the room as shown in @image3 »).
  2. Liste « Keep from @video1 exactly » : la pièce (murs, sol, fenêtre), position/hauteur/objectif/
     cadrage caméra, sa taille, proportions, place dans le cadre, la lumière, la chorégraphie avec
     chaque geste au même timing.
  3. Liaison de la planche : « @image1 is a character reference sheet… use it for her face, hair and
     outfit. Take nothing else from @image1: no panels, labels or text. » (planche entière, pas
     découpée). Si une autre image donne la tenue : planche = visage+cheveux seulement ; image tenue =
     « only the dress: nothing of the mannequin, the background, the logos or any text ».
  4. Garder la tenue d'origine : « replace only the dancing woman's face and hair ».
  5. Nommer les détails fragiles (cheveux : attache, longueur, ne passe jamais devant l'épaule ;
     gants ; accessoires). Non nommés, ils dérivent (gants disparus, queue de cheval basculée).
- [PIÈGE] Toute plaque qui apporte sa propre caméra casse les proportions (l'interprète est rendu à
  l'échelle de la source). Plaque de décor générée en txt2img ou éditée avec une 2e scène en
  référence = échec. Ce qui marche : éditer la `firstFrame` de la vidéo avec elle-même comme seule
  référence (retirer la danseuse, garder murs/sol/fenêtre/caméra/lumière, ajouter la déco, centre du
  sol dégagé, sortie à la taille exacte de l'image) puis vérifier par superposition (blend average)
  que murs/sol/fenêtre coïncident à quelques pixels près.
- [PROMPT] Plaque passée en dernière référence : « this same room seen from this same camera, with
  only the decoration changed; the decorations are fixed props … never move, morph, multiply or
  overlap her ».
- [PIÈGE] Mettre le nouvel interprète DANS la plaque → il apparaît en double à l'arrière-plan.
- [PIÈGE] Chaque édition re-rend l'interprète : changer seulement la pièce = nouvelles prises.
- [MÉTHODE] La chanson ne passe jamais par la génération : extraire l'audio, muter la référence,
  remettre la chanson sur les finales. Décalage variable par run (ex. 83 ms en avance, 57 ms en
  retard) : mesurer par corrélation d'enveloppe audio + enveloppe de mouvement (différence
  d'images), caler sur la danse (pas sur l'audio de la source), pas de 0,1 s.
- [MÉTHODE] Revue des brouillons : source et brouillon côte à côte à 4 instants alignés.

**Correspondance Deepotus.** seedance-2, seedance-2-fast, seedance-2.5 (si edit mode/réf vidéo
exposé). Manques : paramètres `referenceVideos`, `duration: -1`, `draft`/completion, syntaxe
`@video1/@imageN` non exposés dans VIDEO_MODELS (à vérifier sur fal : Seedance 2 « reference-to-
video » existe probablement). Montage Deepotus sait déjà extraire/remuxer l'audio (ffmpeg).
**Propre à Scenario.** `model_scenario-audio-extract`, `-video-cut`, `-compose-video`, CU.

## 7. scenario-thumbnails

**Résumé.** Miniatures / couvertures vidéo (YouTube, store) lisibles à petite taille, texte exact,
personnages fidèles. Famille : txt2img à référence de personnage + overlay texte déterministe.

- [MÉTHODE] Promesse visuelle en une phrase ; un sujet focal, une action, une zone calme pour le
  texte dimensionnée aux mots réels (pas « la moitié du cadre » par défaut).
- [PROMPT] Décrire sujet, action, composition, palette, médium, lumière concrètement ; nommer le rôle
  de chaque référence et les traits qui doivent rester fixes ; plaque sans texte ni boss en double.
- [CHOIX] txt2img avec référence quand c'est une NOUVELLE composition utilisant un perso ; img2img
  seulement pour éditer/restyler une composition existante (ne pas supposer un contrat
  image-source/strength).
- [PIÈGE] Texte : plaque propre puis overlay exact ; si l'utilisateur veut du lettrage généré,
  contrôle caractère par caractère. Un logo est un asset à préserver, pas un mot à faire épeler.
- [PIÈGE] Un exemple de style n'est pas une source de personnage (sinon substitution d'identité).
- [PARAM] Générer à un ratio/taille supportés puis redimensionner ; jamais étirer ou rogner un perso
  pour tomber sur les dimensions.
- [MÉTHODE] Revue à taille réelle (1280x720) ET en aperçu ≈120 px de large (test de stress) ;
  vérifier que le trait identitaire (ex. l'œil unique du boss) n'est pas masqué.
- [MÉTHODE] Une identité modifiée (nombre d'yeux, silhouette) se corrige par édition ciblée depuis la
  plaque acceptée, pas en ajoutant du texte ni en repartant de zéro. Nouveau titre = nouvel overlay,
  pas nouvelle génération.

**Correspondance Deepotus.** Ids image : flux-3, nano-banana-pro, gpt-image-2(.5), ideogram-4.5
(fort en texte), seedream-5-pro, qwen-image-3. Paramètre absent : pas de champ « références » typé
par rôle ni de contrôle « aperçu réduit » dans le pipeline.
**Propre à Scenario.** `model_scenario-compose-image`, `scenario-text-overlay`.

## 8. scenario-ugc

**Résumé.** Vidéo « UGC » (créateur filmé au téléphone) : tête parlante, témoignage, démo produit,
voix off sans visage, vertical. Famille : avatar parlant (img2video + audio), lipsync (video2video),
motion control, vidéo à audio natif, TTS.

- [CHOIX] Couloirs : portrait + audio → membres « talking avatar » ; vidéo existante + nouveaux
  mots → lipsync (audio OU `text`, jamais les deux) ; enregistrement réel + autre visage → motion
  control (image du perso + vidéo pilote, `keepOriginalSound`) ; créateur généré parlant → vidéo à
  audio natif (Veo, Seedance, Kling) ; voix off → b-roll txt2video + TTS.
- [PARAM] Motion control : la sortie est à la taille propre du membre, l'image ne prête que son
  orientation.
- [PROMPT] Dialogue entre guillemets avec la diction nommée (rythme, ton, UN geste). Terminer chaque
  prompt de dialogue par « no subtitles, no on-screen text » (pas une garantie : un membre à audio
  natif a sous-titré quand même).
- [PIÈGE] Certains avatars hallucinent des sous-titres charabia qu'aucun négatif ne supprime ; ceux
  qui ont un interrupteur coûtent « plusieurs fois plus » → choisir le membre selon ce critère.
- [PARAM] Débit oral ≈ 2,5 mots/s (25 s ≈ 60 mots) mais avatars observés à **1,76–1,94 mots/s** ;
  un membre a complété un script de 60 mots par 21 s de silence → chronométrer le clip rendu, couper
  les silences ou le script.
- [PROMPT] Registre UGC dans chaque prompt visuel : cadrage à hauteur de téléphone, lumière
  disponible, vrai lieu encombré, texture de peau naturelle, une légère dérive à main levée max.
  À proscrire : dolly, lumière dorée en contre, anamorphique, étalonnage, peau retouchée.
- [PROMPT] Avatar : mains vides, décor sans produits (les avatars inventent props et étiquettes).
- [PARAM] Démo produit : image→vidéo 3–5 s, un micro-mouvement ; `aspectRatio` respecté ou non avec
  une image de départ dépend du membre (note de schéma parfois fausse) → lire largeur/hauteur rendues.
- [MÉTHODE] Script en 6 temps : accroche, contexte, moment produit, preuve, retournement, clôture
  (CTA doux) ; écrire pour la bouche (contractions, pas de slogans allitératifs).
- [PIÈGE] Un long plan b-roll de 40 s dérive et coûte cher à refaire → clips par temps ; tête
  parlante = une prise, découpée au montage.
- [PIÈGE] Recadrer un master paysage en 9:16 : composer vertical d'emblée (recadrer l'image source
  avant génération).
- [COÛT] Avatars/lipsync : prix très dispersés → devis systématique.
- [MÉTHODE] Produit jamais généré (photo réelle) ; jamais de chiffres/témoignages inventés.

**Correspondance Deepotus.** HeyGen (avatars), eleven_* (TTS), veo-3.1, seedance-2/2.5, kling-v3/v4
(audio natif), images→vidéo pour inserts. Manques probables (sur fal) : lipsync dédiés (Kling
lipsync, Sync, LatentSync), Kling « motion control », avatars fal (OmniHuman, Kling avatar).
Paramètres absents : interrupteur sous-titres, `keepOriginalSound`, débit mots/s mesuré.
**Propre à Scenario.** Captioner Scenario, compositeur, collections.

## 9. scenario-report

Une ligne : rédiger des rapports de bug/demandes pour le dépôt Scenario (caviardage, trace ids).
[MÉTHODE] transposable : un rapport reproductible cite id du modèle, paramètres exacts envoyés,
erreur verbatim, horodatage UTC. Rien sur les modèles.

## 10. scenario-team-admin

Une ligne : gouvernance d'équipe (liste blanche/noire de modèles, plafonds CU par membre, clés API).
Idée transposable : [MÉTHODE] liste d'autorisation de modèles par projet, et retirer un modèle de
base retire les modèles entraînés dessus. Rien sur l'usage des modèles.

## 11. scenario-workflows

Une ligne : exécuter des workflows Scenario (graphes de modèles) via MCP. Faits transposables :
- [PIÈGE] Le plafond de longueur de prompt d'un nœud n'apparaît qu'à l'exécution (« observed as low
  as 4000 characters ») → valider par dry run et raccourcir, ne pas relancer à l'identique.
- [PIÈGE] Un tableau passé là où un scalaire est attendu (ou l'inverse) est ignoré silencieusement
  ET facturé.
- [COÛT] Un job parent de workflow affiche 0 ; le coût réel est dans les jobs enfants ; une boucle
  forEach est devisée pour UNE itération (multiplier).

## 12. scenario-chatgpt-pet-create

**Résumé.** Créer un « pet » ChatGPT/Codex : planche de sprites transparente 192x208 par case,
8 colonnes, 9 états animés (v1 1536x1872) + 2 rangées de 16 directions de regard (v2 1536x2288).
Famille : génération image à références (une RANGÉE par appel) + découpe/assemblage locaux.

- [CHOIX] Modèles nommés explicitement, dans cet ordre : **GPT Image 2.5 « Sunburst »**, puis
  **Nano Banana 2.1** ; motif : « both keep one character across a row of eight poses from a
  reference image ».
- [PARAM] Sunburst : `referenceImages` tableau jusqu'à 10 ; `width`/`height` de 16 à 3840 par pas de
  16 ; `background` (`opaque` utilisé) ; `quality` laissé par défaut.
- [PIÈGE] Sunburst élargit tout seul les formats extrêmes : « asked for 3584x512, it returned
  3584x1200 » → hauteur ≥ largeur/3. Règle de taille du script : largeur = min(3840, poses × 448),
  hauteur = max(512, largeur/3 arrondie au multiple de 16) ; 1 pose = 1024x1024.
- [PARAM] Nano Banana 2.1 : jusqu'à 14 `referenceImages`, `aspectRatio` en préréglages (`4:1` pour
  ≤ 4 poses, `8:1` au-delà, `1:1` pour l'image unique).
- [PARAM] Références utilisateur ≤ 6 (« leaves room for the base, contact sheet and look
  references (10 max) »).
- [COÛT] Devis : 13,75 CU la base, 13,75–17,75 CU par bande (plus large = plus cher), 6,75 CU le
  Pixel Snapper ; pet pixel v2 complet ≈ 198 CU (≈ 216 si running-left généré) ; prévoir 2–3 rangées
  à refaire. Le `cuCost` du job peut omettre des options (Quality Gate) : se fier au devis.
- [MÉTHODE] Le modèle ne dessine jamais la planche entière : une rangée par génération, les scripts
  détectent chaque pose par ses formes et la placent (les modèles ne tiennent pas une grille au
  pixel). Base (identité) d'abord, approuvée, puis rangées avec base + photos en références ;
  `idle` et `running-right` d'abord (contrôle identité/allure) ; `running-left` dépend de
  `running-right` (ou miroir si le perso est symétrique).
- [PROMPT] Base : « <nom>, an animated pet companion: <notes>. One full-body character, centered,
  facing the viewer… Compact proportions that read at 192 by 208 pixels: a large head, a clear face,
  bold shapes, few tiny details. Style: … » + fond de clé + interdits.
- [PROMPT] Bande : « Draw exactly N full-body poses of the same character in one horizontal row,
  left to right in animation order, evenly spaced with clear empty background between neighbors,
  every pose fully inside the image with a margin » + « Same character as the reference image in
  every pose… Same size in every pose, standing on the same ground line, except where the action
  itself lifts the character ». Prompt de reprise : préfixe « Exactly N poses, every one fully
  separated from its neighbors and none touching the image edge ».
- [PROMPT] Fond de clé chromatique : « one perfectly flat <couleur hex> fill from edge to edge, with
  no gradient, texture, floor, shadow, glow or vignette. No <couleur> or similar color anywhere on
  the character ». Clé choisie contrastée (perso rose → vert, jamais magenta ; défaut magenta).
- [PROMPT] Interdits : « No text, numbers, labels, frames, grid lines or borders. No speed lines,
  motion blur, dust, shadows, sparkles, or any effect floating apart from the character ».
- [PROMPT] Styles prêts à l'emploi (texte du script) : pixel (« one-pixel dark outline, small fixed
  palette, flat cel shading, hard stepped edges, no anti-aliasing »), plush, clay, sticker,
  flat-vector, 3d-toy, painterly, match (« exactly the style of the reference images »),
  brand-inspired (« never its logo, wordmark or any readable text »).
- [PROMPT] Regard : droite/gauche = bords de l'IMAGE (spectateur), jamais ceux du perso ; corps,
  pieds, taille fixes, seuls yeux/tête/haut du corps bougent ; ne jamais faire pivoter/incliner/
  rétrécir le sprite entier ; un élément latéral reste du même côté dans toutes les poses.
- [MÉTHODE] Pixel-perfect : Pixel Snapper UNE fois sur la base approuvée (24 couleurs par défaut,
  seed fixe), puis grille ×8/4/2/1 et palette imposées à toute la planche ; ne pas snapper chaque
  image (grilles différentes + coût par image).
- [PIÈGE] Accepter une rangée avec avertissement non lu (pose coupée par le bord, pose en trop,
  pixels couleur-clé dans le perso) → images cassées au montage.
- [PIÈGE] Même échec deux fois : changer d'approche (pose plus simple, phrase ajoutée, moins
  d'accessoires) au lieu de relancer le même prompt. Ne jamais dessiner d'images par code.
- [MÉTHODE] Contrôles mesurés : hauteur ±8 % (avertissement) / 15 % (erreur) vs idle ; saut ≥ 8 px
  et atterrissage à ≤ 12 px de la ligne de sol ; directions de regard ≤ 26 px de l'ancre, largeur
  ≤ 1,5× ; verdicts écrits par direction (observé + preuve).

**Correspondance Deepotus.** gpt-image-2.5-sunburst(-fal), nano-banana-2.1 : présents. Spritelab /
Sprites natif. Manques : « Pixel Snapper » (outil de snapping grille+palette — à chercher sur fal,
sinon local) ; paramètres `background: opaque/transparent`, `quality`, plafond de références (10 /
14) et contrainte « hauteur ≥ largeur/3 » non portés par FAL_IMAGES.
**Propre à Scenario.** Scripts pet_*.py (MIT, réutilisables localement), collections, CU.

## 13. scenario-chatgpt-pet-update

**Résumé.** Modifier un pet existant (rangée cassée, nouvelle tenue, ajout des directions v2).
Même famille et même ordre de modèles (Sunburst puis Nano Banana 2.1).

- [PIÈGE] Envoyer la planche entière comme référence : « it reads as a grid of small frames and the
  model copies the grid » → donner l'image idle agrandie + la bande de la rangée.
- [PIÈGE] Quand c'est le MOUVEMENT/la direction de l'ancienne rangée qui est faux, retirer
  l'ancienne bande des références (« the model copies what it is shown ») et décrire le changement.
- [MÉTHODE] Nouvelle apparence (écharpe…) = édition de l'image d'identité (« Edit the character in
  the reference image: <change>. Keep everything else identical: proportions, face, palette,
  outline, style and pose ») puis régénération de TOUTES les rangées ; l'ancienne planche fixe la
  taille.
- [COÛT] Réparer sans générer ce qui est géométrique (pixels résiduels, rangée qui saute) : 0 appel.
  Une rangée = un appel ; les autres sont recopiées à l'octet.

**Correspondance Deepotus.** Idem pet-create (Spritelab). Rien de neuf côté registre.

## 14. scenario-game-assets

**Résumé.** Art de jeu : sprites, icônes, props, tilesets/autotiles, isométrique, pixel art, UI,
parallaxe ; détourage, upscale, nettoyage pixel, export PNG. Famille : image (spécialisés + généraux)
+ outils (détourage, upscale, snap).

- [CHOIX] Transparence : préférer un générateur à alpha natif (évite une passe de détourage facturée
  par icône) ; sinon traiter la sortie comme opaque.
- [PROMPT] Ne JAMAIS écrire « transparent background » à un modèle de diffusion (sortie opaque) ;
  demander « plain background » (se détoure proprement) ; à un modèle alpha natif, décrire le sujet
  seul, sans le mot transparent.
- [PROMPT] Exemple de gabarit : « health potion, corked glass bottle, glowing red liquid, bold
  outline, centered, plain background » ; pour une série, ne varier QUE l'objet, gabarit fixe.
- [PARAM] Paramètre « nombre d'échantillons » = variantes d'un même objet ; objets différents =
  runs séparés.
- [MÉTHODE] Cohérence de style : même `seed` sur le lot ; **désactiver l'expansion/réécriture de
  prompt** quand le schéma l'expose (elle réécrit chaque prompt indépendamment) ; références de
  direction artistique ; LoRA entraîné sur l'art du projet en dernier recours.
- [PIÈGE] Référence pour série de variations (bouton, panneau, icônes) : rogner aux bornes de
  l'objet (le padding transparent est lu comme composition → échelle/décalage qui dérivent), retirer
  ombres portées/lueurs/biseaux (reviennent épaissis/doublés/fusionnés ; les réappliquer en moteur),
  un seul objet sur fond uni (plusieurs objets → hybride), dire quelles parties sont fonctionnelles
  (9-slice : milieux étirables, coins fixes) puis vérifier.
- [PIÈGE] Alpha : frange semi-transparente après détourage ; halo de lueur large sur certains
  modèles alpha natifs ; intérieur incohérent (verre vide percé à alpha 0 sur un objet, opaque sur
  l'autre). Vérifier par mesure (bbox alpha) et non à l'œil.
- [MÉTHODE] Isométrique : choisir la grille avant le style (2:1 diamant ≠ hexagone projeté) ; même
  projection, ancre, direction de lumière et côté d'ombre ; empreinte au sol ≠ silhouette (arbres et
  bâtiments dépassent) ; tester une petite carte assemblée avant le lot. Gabarits 1024x1024, ancre
  au sol (512, 704) ; sol continu = éclairage plat sans dégradé/vignette/ombre par tuile.
- [PARAM] Remplissage masqué : lire la polarité du masque et le champ image de base dans le schéma ;
  le canevas de base doit avoir taille et position du masque ; si le canevas est opaque, ne pas
  demander de sortie transparente en même temps (contradiction) — extraire l'alpha après.
- [CHOIX] « Low-poly » style (mot de style 2D) ≠ maillage low-poly (image→3D : vérifier si le modèle
  expose une cible de polygones/topologie, sinon remesh séparé) ; l'image source d'un 3D veut un
  ombrage plat, silhouette nette, fond uni.
- [PARAM] Tileset pixel (Retro Diffusion type) : enum `style` (tileset complet, transition
  2 terrains via `extraPrompt`/`extraImage`, tuile unique, variation, objet) ; `width`/`height` =
  UNE tuile, pas la planche ; promet un set Wang simple, pas un blob 47 tuiles → mapper sur les
  règles d'autotile du moteur et tester une carte.
- [MÉTHODE] Parallaxe : jamais « layers/parallax » dans un seul prompt (renvoie une image de couches
  empilées). Deux voies : (a) découper une peinture finie avec un outil de séparation en plans
  (`separationInstruction` = règle de découpe, `maxLayers` et inpainting influent sur le prix ;
  élargir la peinture AVANT de découper, l'outpainting remplirait les trous des découpes) ;
  (b) un plan par génération, caméra/horizon/lumière/palette fixes, dire ce que le plan ne doit PAS
  contenir (« no ground, no sky »), largeur = viewport + amplitude de défilement.
- [PIÈGE] Texte sur assets (lettrage) : une même recette réussit un mot et rate l'autre → plusieurs
  échantillons par run, hex exacts dans le prompt quand la palette dérive.
- [PIÈGE] Photo-upscaler sur du pixel art invente de la texture ; JPG sans alpha → PNG.

**Correspondance Deepotus.** Images (flux, gpt-image-*, nano-banana-*, recraft-4.1-vecteur), rembg
local, matte, Tilelab, Vectorlab, Assets 2D. Manques probables : générateur alpha natif (gpt-image
`background: transparent` — paramètre non exposé ; fal a aussi des modèles « transparent » type
Recraft/Ideogram), Retro Diffusion (pixel/tileset — à vérifier sur fal), outil de séparation en
plans (Qwen-Image-Layered probablement sur fal), upscalers pixel-safe. Paramètres absents : seed et
« prompt expansion off » par modèle, masque + polarité, nombre d'échantillons.
**Propre à Scenario.** Gabarits isométriques uploadés, `model_scenario-compose-image`, LoRA training.

## 15. scenario-sprite-animation

**Résumé.** Animer de l'art 2D de jeu : cycles 4/8 directions, planches, GIF, VFX en boucle, boucle
parfaite depuis une image, extraction d'images d'une vidéo, découpe moteur. Famille : modèle
d'animation pixel spécialisé, grand modèle image « haute adhérence » (planche unique), vidéo
first+last frame / keyframes, outils.

- [CHOIX] Table de routage : cycles pixel/VFX à canevas verrouillé → modèle d'animation spécialisé
  (Retro Diffusion Animation) ; grille exacte / nombre d'images choisi / temps scriptés → grand
  modèle image haute adhérence en UNE planche (famille GPT Image) ; boucle depuis une image →
  vidéo first+last frame ; poses à des instants donnés → vidéo à keyframes ; perso multi-directions →
  planche de poses puis un clip image→vidéo first+last par direction et par cycle.
- [PARAM] Retro Diffusion Animation : enum `style` verrouille le canevas (`four_angle_walking`,
  `walking_and_idle` 48 px ; `small_sprites` 32 px ; `vfx` 24–96 px) — « a requested 64px walk cycle
  is a schema violation » ; `returnSpritesheet` (GIF → PNG planche) avec MÊME seed que l'aperçu ;
  la référence `image` est convertie en RGB sans transparence ; l'enum est tout le vocabulaire de
  mouvement (brief d'attaque → cycle générique sans l'arme). Retro Diffusion Plus : `inputPalette`
  (palette de référence), plafond 384 px (4:3 max 384x288), `removeBg` faux par défaut.
- [PARAM] Planche unique GPT Image : `width`/`height` pas de 16 (2048/4 = cases de 512),
  `numOutputs`, `referenceImages`, `quality`, `background` (`auto|opaque|transparent`, transparent en
  « Preview »), **pas de `seed`**. Même planche 2048² haute qualité : « 15 CU on the family's two
  newest members and 59 CU on the member before them » (devis `recommend` à 12 CU par défaut →
  toujours deviser le payload exact). Les membres les plus récents absents de `recommend`, présents
  en recherche par nom.
- [PROMPT] Spécifier la grille pour le pipeline : lignes×colonnes ≤ 6x6 (16 images = 4x4, jamais
  2x8), canevas divisible par la grille, une échelle, une caméra, une orientation, une ligne de sol,
  temps par plage d'images, dernière image = première, marges généreuses, pas d'étiquettes. Pas de
  consignes de GIF (le modèle rend des images fixes).
- [PIÈGE] Dérive de position entre rangées (pieds à 487/447/400 px ; centre ±59 px) : ni le langage
  d'ancrage (« invisible ground line » → le modèle DESSINE la ligne) ni un gabarit en référence ne la
  corrigent ; corriger en post (ligne de base médiane par rangée, centrage horizontal du corps, sur
  canevas élargi 640x512 pour 512).
- [PIÈGE] Une plage de temps nommant un seul état final peut revenir comme une pose tenue (images
  13–16 identiques) → compter les poses distinctes avant découpe.
- [MÉTHODE] Boucle depuis une image fixe : même image en first ET last frame + mouvement EXPLICITE
  (« weight shifts, cloak sways; the character stays in place ») — image identique sans mouvement
  nommé = image figée. Si un drapeau loop natif existe, ne pas l'envoyer AVEC l'end frame (dry run
  accepte, l'exécution échoue).
- [MÉTHODE] Contrôle de raccord : delta absolu moyen entre images consécutives (base de mouvement)
  vs delta au raccord ; boucle fermée si raccord ≤ base de la fenêtre. Les modèles image→vidéo
  re-rendent l'image d'entrée : l'image 0 diverge souvent (grand delta 0→1) → chercher la meilleure
  fenêtre en excluant l'image 0 avant de relancer ; une seule relance (nouvelle seed ou mouvement
  reformulé).
- [PARAM] Cadence sprite : générer à 8–12 fps si exposé (cycle = 8–16 images) plutôt que décimer.
  Repères : marche 8 images à 7–10 fps, course 6–8 à 9–12, idle 4–8 à 4–6, attaque 6–10 à 8–12 jouée
  une fois ; lisible dès ≈64 px de haut, 32–48 px = retouche.
- [PARAM] GIF : délais quantifiés à 10 ms → fps diviseur de 100 (10, 20, 25) ; 12 fps devient 10 ;
  l'assembleur duplique/supprime des images pour tenir la durée (8→7, 16→20). Livrable moteur en mp4
  ou planche PNG, GIF = aperçu.
- [PIÈGE] Vidéo : aucun couloir vidéo n'émet d'alpha ; un `background` vidéo peut COMPOSITER un fond
  (couleur/image/vidéo) ; `mov` ≠ alpha sauf ProRes 4444 ; WebM VP9 ou ProRes 4444 seuls porteurs
  d'alpha (MP4 jamais) ; un VP9 demandé est revenu sans alpha. Détourage par image extraite plus
  propre que détourage vidéo. Mode HD d'un détoureur = no-op silencieux sous son seuil d'entrée.
- [PIÈGE] Un modèle vidéo peut ignorer `aspectRatio` et la résolution et se caler sur sa grille
  latente : « a 4:3 720p request came back 1088x800 » → mesurer le fichier, redimensionner `cover`.
- [PARAM] Couloirs vidéo vus : keyframes sur grille 24 fps (FLUX.3 Keyframes), start+end + enum fps
  (LTX), preset de style + seed (PixVerse). Couper la réécriture de prompt (« expansion/optimizer »)
  quand la formulation exacte porte le perso ou le mouvement.
- [PIÈGE] Beaucoup de schémas vidéo (et certains image) n'ont pas de seed → reproductibilité par
  asset, pas par run.
- [PIÈGE] Burst au-delà de la concurrence : refus 429, ou sur certains couloirs vidéo jobs acceptés
  puis en échec (remboursés) → lancer par vagues.
- [PIÈGE] Modération sur une attaque : essayer un autre grand modèle image avec la même spec de
  grille plutôt que d'adoucir les temps.
- [MÉTHODE] Pixel : snapper chaque image individuellement (même nombre de couleurs, même seed), puis
  UNE palette commune construite sur toutes les images (sinon scintillement) via un outil Pixelate
  avec `colorPalette` + un `pixelGridSize` divisant la taille ; snapper ≈ 5 CU/tuile ; sur des images
  déjà au pixel natif le snapper peut ruiner l'image (384x288 → 69x52) → sonder une image d'abord.
  Upscale par multiple entier uniquement.
- [PARAM] Modèles pixel faibles en comptage exact (« a five-child campfire came back as four »
  malgré 3 stratégies) → itérer l'image fixe sur un budget séparé.

**Directional cycles (référence).** [PROMPT] « treadmill » (« starts walking in place and keeps
walking for the whole clip, stays centered and does not travel across the frame ») ; une phrase
d'orientation par prompt + négatif nommant le MAUVAIS angle (profil pour les diagonales, face/3-4
pour un profil) ; négatif de base « camera movement, zoom, travelling across the frame, ground
shadow, drop shadow, background change, extra characters, blur, 3D render » (+ « slowing down,
stopping, standing still » pour la locomotion) ; « Locked static camera, flat solid <clé>
background, no ground shadow ». [PARAM] last frame épinglé pour idle/attaque (retour au repos) ;
laissé libre pour marche/course diagonales courtes (sinon le modèle démarre et s'arrête dans le
clip) ; vues de dos en course : 5 s plutôt que 3 s + last frame épinglé + « runs away from the
viewer toward the top-right corner » + ce qui reste visible ; face/dos (S/N) : « never comes closer:
stays the same size » (un golem a grandi ×1,45). Figure à 58 % d'un carré 960 px, pieds à 82 %
(0,52 pour un dragon quadrupède) ; ce qui sort du cadre est coupé net. [CHOIX] membre i2v avec
champ end image, négatif, aspect carré, durées ≈3 et 5 s, non déprécié ; « 24 CU for a 3 s clip »
au palier standard vs 55 CU affichés par défaut par `recommend` ; les membres moins chers sans ces
champs zoomaient, recadraient ou dérivaient le fond. Seuil de raccord : < 0,5 propre, 0,5–0,8 à
vérifier, > 0,8 en marche/course = fenêtre de recherche trop courte. Import moteur : Unity Sprite
Mode Multiple, Filter Point, Compression None, pivot (x/w, 1−y/h) ; Godot 4 filtre Nearest,
AnimatedSprite2D, `flip_h` pour les miroirs ; Phaser `pixelArt: true`.

**Correspondance Deepotus.** Spritelab / Sprites (natif, exports, directions, hitboxes), i2v
first+last : kling-v3-pro (image de fin), seedance-2(.5), veo-3.1, ltx-2.5-fast/pro, pixverse-v6,
flux-3-max ; image planche : gpt-image-2(.5). Manques : Retro Diffusion Animation/Plus (probablement
pas sur fal — à vérifier), FLUX.3 Keyframes (champ keyframes), Pixelate/Snapper (local possible).
Paramètres absents : `background` gpt-image, `numOutputs`, `fps` de génération, drapeau loop natif,
« prompt expansion off », champ négatif par modèle vidéo, garde « loop + end frame exclusifs ».
**Propre à Scenario.** Outils `model_scenario-grid-maker`, `-image-slicer`, `-video-to-image-seq`,
`-image-seq-to-video`, `-resize-image/-video` ; défaut d'ordre des `assetIds`.

## 16. scenario-side-view-game-kit

**Résumé.** Art complet d'un jeu de plates-formes vue de côté : sprites pixel animés (héros,
ennemis) et couches de niveau (fond, plan moyen, texture murale, plate-forme, props). Famille :
txt2img à références + image→vidéo first/last frame + finition locale (clé, boucle, palette).

- [CHOIX] Image : forte adhérence de mise en page, entrée référence, option fond transparent, et la
  taille 1536x1024 — un modèle pixel spécialisé plafonne souvent bien en dessous → prendre le
  suivant dans le classement. Vidéo : i2v avec champ `endImage`.
- [PARAM] Payload vidéo de la build : `startImage`, `endImage`, `duration: "3"` (chaîne),
  `aspectRatio: "1:1"`, `generateAudio: false`, `negativePrompt` ; marche d'ennemi armé :
  `cfgScale: 0.7`.
- [PARAM] Tableau des clips : course/marche = première image seule, 3 s ; idle, attaques, fente,
  tir, blessure = première = dernière (même image), 3 s ; vrille aérienne = image de saut aux deux
  bouts, 3 s. Tous carrés, son coupé.
- [PIÈGE] Image de fin sur une locomotion courte = accélération/décélération dans le clip (boucle
  impossible).
- [PIÈGE] Ennemi armé qui balance son arme en marchant (raccord 1,44× la base). Correctif :
  « His arms stay still … never lifts, swings or twirls it » + termes d'arme au négatif
  (« swinging the weapon, raising the {weapon}, attacking, twirling ») + guidance 0,7 → 0,42×.
- [PROMPT] Image deux poses (txt2img) : « Pixel art game sprite sheet, two poses of the same
  character side by side, full body, on a perfectly flat solid magenta (#FF00FF) background, no
  shadows on the ground, no text » + Character + silhouette lisible + « Camera: classic 2D
  side-scrolling platformer, pure side profile view, orthographic, no perspective » + poses gauche/
  droite + style (« 1px dark outline, limited palette of about 24 colors, soft top-left lighting,
  no pink, no purple, no magenta anywhere on the character, each figure about 60% of the image
  height »). 1536x1024, qualité haute, opaque, 2 sorties.
- [PROMPT] Fin commune à chaque clip : « always faces right in a pure side profile… never turning
  toward the camera… stays centered and does not travel across the frame. Locked static camera,
  flat solid magenta background, no ground shadow, crisp pixel art, same character design as the
  first frame » ; négatif « front view, three-quarter view, facing the camera, turning around,
  camera movement, zoom, traveling across the frame, ground shadow, drop shadow, background change,
  extra characters, blur, 3D render ».
- [PIÈGE] Rose/violet sur le perso = mangé par la clé magenta ; un coup d'arme rapide prend une
  teinte violette de flou de bougé → « no motion blur, the weapon keeps its colors » + négatif
  « purple or magenta tint on the weapon ». Traînée blanche / nuage de poussière → blocs solides
  après clé : retirer l'image.
- [PIÈGE] Combat bloqué par modération : relancer le payload INCHANGÉ sur un autre fournisseur
  (avec `endImage`) avant d'adoucir.
- [PIÈGE] « seamless tileable » ne tuile pas de façon fiable → fondu croisé des bords en local
  (12 % par axe). Plate-forme : demandée 1536x384, rendue 1536x512 (le modèle a imposé son format).
- [PROMPT] Couches de niveau (5 par niveau) : fond 1920x1152 opaque (« Keep the lower third and the
  middle of the image darker and lower contrast so characters on top of it stay readable »), plan
  moyen 1920x1152 transparent (« The entire center… completely empty and transparent »), texture
  1024² opaque, plate-forme transparente (« top edge is perfectly straight and flat »), props
  1536x1024 (« wide empty gaps between them so they never touch »). Palettes terminées « on
  near-black ».
- [PIÈGE] Art de niveau à échelle rétro (384x224) refusé au premier test de jeu ; 1920x1152 dessiné
  à 2× l'a remplacé.
- [PARAM] Résultats : héros 56 px, palette 28 couleurs ; raccords course 0,32×, idle 0,28× ;
  clip rendu en 1440 px depuis une première image 960 (le modèle peut monter en résolution).
- [COÛT] Devis par payload distinct (première image seule / épinglée / guidance changée) ; niveau 1
  validé en jeu avant de générer les autres.

**Correspondance Deepotus.** Spritelab, Tilelab, Assets 2D ; vidéo first+last : kling-v3-pro,
seedance-2(.5), ltx-2.5, veo-3.1 (selon champ image de fin) ; image : gpt-image-2(.5), nano-banana.
Paramètres absents : `negativePrompt` et `cfgScale` vidéo par modèle, `generateAudio` explicite,
`background` transparent image.
**Propre à Scenario.** Scripts locaux (MIT) réutilisables : reframe_stills, side_sprites,
process_env.

## 17. scenario-kinetic-film

**Résumé.** Film de lancement / teaser en typographie cinétique : tout le mouvement est du code
(moteur JS), Scenario fournit musique au tempo exact, kit de SFX et images clés. Famille : musique
(txt2audio avec BPM), SFX, image clé.

- [CHOIX] Musique : modèle dont le schéma a une entrée **tempo** (`bpm`), un interrupteur
  **instrumental** et une **durée** ; « a tempo the model is told beats a tempo you hope for » ;
  aucun membre avec tempo → arrêt (ne pas générer sur correspondance partielle). Deux prises à
  172 BPM ont mesuré 172,0.
- [PROMPT] Musique : genre + BPM + structure en mesures (« Eight bars of tense intro… then a huge
  drop ») + instrumentation + « No vocals. Ends on one hard final hit » ; sous la limite de longueur
  du schéma ; 2 prises, ≈ 15 s de plus que le film.
- [PIÈGE] Ne pas croire le tempo d'une piste générée : mesurer sur la fenêtre utilisée avec le BPM
  attendu (sinon détection à la moitié : 172 lu 86) ; la grille globale peut être décalée de
  2,5 temps.
- [CHOIX] SFX : modèle dédié avec durée et prompt négatif ; 1 sortie par son (certains membres
  sortent 2 par défaut) ; durées courtes (chaque seconde coûte) ; négatif « music, speech, voice,
  reverb wash, background noise ». Kit de 12 sons avec durées (whoosh 0,7 s, impact 1,2 s,
  impact_big 2,2 s, hit 0,5 s, key 0,3 s, riser 2,2 s, logo_hit 3 s…) et prompts types.
- [PROMPT] Images : écrire en directeur artistique (style, plan, sujet, lumière, palette, contenu de
  chaque tiers) ; ne jamais demander d'espace vide (« calm darker band for title text » → bande
  grise littérale) ; assombrir en post.
- [PIÈGE] « No watermark » avec une image de référence attachée → bloqué comme suppression de
  filigrane ; écrire « no text, no logos ».
- [PIÈGE] Véhicules, vêtements, produits générés portent de vraies marques (logo de scooter) →
  inspecter à 100 %.
- [PARAM] Image : 16:9, ≥ 2K (≥ 2048 px de large) ; cohérence : 1re image en référence des
  suivantes (« same character, same city as the reference image ») ; payload exemple
  `referenceImages`, `aspectRatio: "16:9"`, `resolution: "2K"`, `numOutputs: 1`.
- [MÉTHODE] Mixage à −14 LUFS / −1 dBTP ; ducking de la musique sous les gros impacts.

**Correspondance Deepotus.** Musique : minimax-music-*, stable-audio-25/3, lyria3/3.5,
elevenlabs-music-2.5, ace-step, mureka-9.5, cassetteai ; SFX ElevenLabs, hunyuan-foley ; image :
flux-3, nano-banana-pro, seedream-5-pro, gpt-image-2(.5). Paramètres absents à vérifier : `bpm`
(registre MUSIC_MODELS : quels modèles l'acceptent ?), `instrumental`, nombre de sorties, négatif
SFX.
**Propre à Scenario.** Moteur JS, render/finish.py (code, pas modèles).

## 18. scenario-kinetic-music-video

**Résumé.** Clip musical en typographie cinétique / motion design à partir d'une chanson : feuille
de personnage, image de style par plan, séquences générées (actions, danse calée, lipsync) tissées
dans un moteur JS déterministe. Famille : image à références, i2v, audio→vidéo (lipsync), vidéo à
références image+audio, correction lipsync (video2video), édition audio (ACE-Step).

- [MÉTHODE] Feuille de sujet d'abord (turnaround, expressions, détails) depuis les références
  (img2img), puis recadrer des références d'identité (visage, plein pied 3/4) ; prompt avec
  identité, tenue/matières, style de rendu avec NOTs explicites (« not Pixar, not chibi »),
  lumière cohérente avec les décors.
- [MÉTHODE] Une image de style par plan au ratio du canevas, puis l'animer : « better looks and
  consistency than text-to-video » ; validation du look au prix d'une image.
- [PROMPT] Image de style : style nommé explicitement, composition avec espace négatif pour le texte
  (« framed on the right third, left two thirds empty » ; en 9:16 visage ≈ 40 % de la hauteur),
  décor compositable (vide noir + liseré dur, cyclo couleur unie, blanc high-key), « No text, no
  letters, no logos ». En plan lipsync, rien ne cache la bouche (micro, main, accessoire).
- [PROMPT] Plan vidéo (5 parties) : rôle de chaque entrée `@image`/`@audio` (« Animate this exact
  image, keep its exact art style of… ») ; UNE action dominante avec repères temporels en secondes
  du clip ; UN mouvement de caméra ; décor et lumière tenus constants ; exclusions (« No text, no
  captions, no logos, no watermark, no other people. Silent footage. »).
- [PARAM] Durée via le champ `duration`, jamais dans le prompt (« recommend read "under 10 s" there
  as a latency limit »).
- [PIÈGE] Ne jamais envoyer la chanson à un modèle vidéo : modération
  « InputAudioSensitiveContentDetected », et `generateAudio:true` peut reproduire la voix et faire
  échouer le job. Utiliser stems vocaux et pistes de beat synthétiques.
- [MÉTHODE] Danse calée : vidéo à référence image + référence audio = piste de percussion
  synthétique (« @audio1 is a percussion timing guide: every hit lands exactly on the kicks and
  snares ») puis beat-warp local (alignement natif lâche ; warp = 14/14 pics à 160 ms).
- [MÉTHODE] Lipsync préféré : audio→vidéo depuis l'image de style + tranche de stem vocal (WAV, pas
  MP3 : délai d'amorce). Prompt « precise, expressive lip sync, strong mouth shapes on every
  syllable », bouche visible, mains hors champ. Alternative : vidéo à référence audio puis modèle de
  correction lipsync (mode « cut-off »).
- [PARAM] Audio→vidéo : audio plafonné à 10 s (« an 11 s slice failed with a 400, and so did a
  slice of exactly 10.0 s ») → tranches ≤ 9,9 s ; clips rendus quelques images plus courts.
- [PARAM] Clips rendus à 24 fps, ≈ 0,04 s plus longs que demandé ; mode référence-image (feuille +
  recadrage) tient l'identité à 720p.
- [PIÈGE] Recadrage de référence plein pied trop étroit (largeur/hauteur < 0,4) refusé par le
  contrôle de référence d'un membre alors que le dry run l'avait devisé → padder vers le ratio du
  canevas.
- [PIÈGE] Sol brillant demandé → dégradé gris ; le texte incrusté par le modèle n'est jamais
  utilisable.
- [COÛT] Ancres relatives à 720p (1 image de style = 1) : clip 6 s ≈ 20, clip 10 s ≈ 35, passe de
  correction lipsync ≈ 13, clip complet mixte ≈ 500 ; 1080p ≈ **2,5×** le prix 720p. Réel : 17 images
  + 17 vidéos + 6 lipsync ≈ 6k CU à 720p ; remake 9:16 1080p (24 images, 27 clips) ≈ 15k CU.
  Devis possible avant toute image en mettant une photo uploadée à la place de chaque image de style
  (les devis ont égalé la facture).
- [PIÈGE] Ne jamais recadrer 16:9 → 9:16 (garde < 1/3 de la largeur, upscale ×1,8–2,7) : régénérer
  au bon ratio les plans qui doivent remplir le cadre (accroche, lipsync, final), fenêtrer les autres.
- [PIÈGE] Modèles de chanson et noms accentués : un prénom français chanté « her vape » → écrire le
  nom phonétiquement dans la feuille envoyée ; durée demandée ≈ 2:00 rendue 3:04 puis 2:14 après
  raccourcissement + indication « about 2 minutes, very short intro ». « 130 BPM » mesuré 98.
- [MÉTHODE] Édition de bande-son (ACE-Step Cover/Repaint) : feuille identique sauf le mot ciblé
  (sinon le modèle chante autrement d'autres lignes) ; Repaint ne garantit ni même chanteur ni même
  mélodie ; épeler phonétiquement les acronymes ; fondus 10–30 ms ; un « half-time bridge » a
  transformé une prise en ballade.
- [MÉTHODE] Transcription : Whisper large-v3 (horodatage mot) > wav2vec/MMS sur le chant (MMS
  ≈ 200 ms en retard) ; séparer la voix (Demucs) avant d'aligner.
- [MÉTHODE] Contrôle lipsync mesuré : corrélation ouverture de bouche / RMS vocal ≈ 0,5 bon,
  0,1–0,2 faible.

**Correspondance Deepotus.** Vidéo : seedance-2/2.5 (références image+audio), kling-v3/v4,
veo-3.1, wan-3.0, gemini-omni-flash, h3-max ; audio→vidéo lipsync : manque probable (OmniHuman,
Kling avatar, Wan-S2V, Sync lipsync — probablement sur fal) ; musique ace-step (Cover/Repaint ?),
stems htdemucs (présent). Paramètres absents : `referenceAudio`, plafond audio 10 s, mode lipsync
cut-off, `generateAudio` forcé à faux.
**Propre à Scenario.** Moteur three.js, sous-agents par section, scripts de contrôle.

## 19. scenario-motion-loops

**Résumé.** Boucles de motion design en code (Canvas 2D, 12 s, couleurs de marque) ; Scenario ne
fait que le sujet (mascotte/produit détouré). Famille : img2img/txt2img avec fond transparent,
i2v optionnel + détourage vidéo.

- [PROMPT] Détourage mascotte : « The mascot from the reference image, full body, three-quarter
  view, a light floating pose, cut out on a transparent background with clean edges, no shadow, no
  text » ; préférer un membre à fond transparent natif, sinon détourage après.
- [PIÈGE] Halo au contour visible sur tons sombres → régénérer ; relever le seuil/bord du
  détoureur.
- [PROMPT] Plan animé de la mascotte : « the mascot waves and turns its head, plain flat
  background, locked-off camera, no cuts » (fond uni + caméra fixe = détourage propre).
- [PARAM] Détourage vidéo : WebM VP9 avec alpha (ProRes 4444 pour le montage) ; ffmpeg doit décoder
  avec `-c:v libvpx-vp9` sinon l'alpha est perdu.
- [CHOIX] Ne jamais faire une boucle avec un modèle vidéo (« A generated clip's last frame rarely
  meets its first ») : boucle en code.

**Correspondance Deepotus.** Montage/overlays alpha (t282), rembg/matte. Rien à ajouter au
registre ; confirme l'usage « boucle en code ».

## 20. scenario-video-ads

**Résumé.** Couche « réalisateur » d'une pub vidéo neuve depuis une photo produit : brief,
concept, storyboard chiffré, images fixes, animation, contrôle de fidélité, audio, assemblage.
Famille : image edit (composite produit), i2v, musique au BPM, TTS.

- [MÉTHODE] Le produit n'est jamais généré (photo réelle en première image ou composée dans une
  image approuvée) ; le texte jamais généré (logo, prix, mentions en overlay).
- [PROMPT] i2v : mouvement d'abord, tempo indiqué (« slow push-in over 4 seconds »), puis état du
  sujet, puis atmosphère ; immobilité du produit énoncée positivement UNE fois (« the bottle rests
  fixed in place ») — « Negative commands ("do not morph") do nothing and can trip filters ».
  Chaque prompt est autonome (le modèle ignore les plans voisins). Détail le plus difficile en
  premier.
- [PARAM] Mouvements fiables tous modèles : push-in, dolly, pan, tilt, tracking, pull-back,
  handheld (toujours avec un degré : « subtle handheld drift ») ; à budgéter en reprises : orbite,
  grue, rack focus, whip pan. Tempo lent par défaut (masque ce que le modèle rend mal).
- [MÉTHODE] Plan qui doit FINIR sur le produit intact : générer le mouvement inverse depuis la photo
  en première image puis inverser le clip (dernière image = photo intacte par construction).
- [CHOIX] Première image quand le plan doit s'ouvrir dessus ; images de référence quand seules
  identité/monde/palette doivent tenir.
- [PARAM] Durées : 3–5 s pour les plans produit critiques, 5–10 s pour la couverture, +1–2 s de
  marge de coupe ; jamais un long plan à la durée max du schéma. Enchaînement sans coupe : images
  approuvées N et N+1 en first/last frame (jamais une dernière image rendue).
- [PARAM] `generateAudio: false` (bande-son faite au montage).
- [PROMPT] Lumière fixée à l'image fixe : fond sombre pour verre/liquide, contre-jour pour
  transparence, lumière rasante pour texture, grandes sources douces pour peinture/métal poli,
  liseré pour séparation, heure dorée pour carrosserie. Regard vers le produit attire l'attention ;
  regard caméra seulement pour adresse directe/CTA ; mains en prise naturelle, jamais sur
  l'étiquette.
- [COÛT] Planchers de reprises (hypothèses de planification) : 3 générations par plan produit
  utilisable, 5–10 pour mouvement complexe/liquide/tissu, jusqu'à 20 avec visages/mains → éviter
  l'humain sauf besoin. Indicateur : coût par plan utilisable ; recaler après le premier plan.
- [MÉTHODE] Contrôle de fidélité : extraire première/milieu/dernière + image où le sujet est le plus
  grand ; « jeu des différences » contre la référence (texte d'étiquette, géométrie du logo,
  bouchon, silhouette, matière, teinte) ; ajouter des RATIOS mesurés (longueur/hauteur, taille
  d'étiquette) que les listes de traits ratent ; échec → régénérer depuis la même image avec clause
  d'immobilité resserrée, jamais depuis la sortie dérivée.
- [PARAM] Voix off 2–2,5 mots/s : 8–12 mots en 6 s, 30–35 en 15 s, 60–70 en 30 s ; musique au BPM
  de la grille de coupe ; ducking 12–18 dB ; −14 LUFS social, −24 LKFS CTV.

**Correspondance Deepotus.** Vidéo i2v : tous les ids vidéo ; image edit : nano-banana-pro,
gpt-image-2(.5), seedream-5-pro, flux-3 ; voix eleven_* ; musique (BPM). Manque : outil « reverse
video » (trivial en ffmpeg local). Paramètres absents : enum caméra (certains schémas), `seed`.
**Propre à Scenario.** `asset_analyze` (vision), compositeur, `usage`.

## 21. scenario-game-ua-ads

**Résumé.** Pub d'acquisition (UA) pour jeu mobile qui « joue » comme du gameplay : plateau généré,
prises vidéo, toute l'UI compositée. Famille : image (plateau, états), i2v first/last frame,
SFX/musique, video-to-audio.

- [PROMPT/PIÈGE] Jamais de texte, chiffres, valeurs de portes, boutons ou MAIN dessinés par le
  modèle : emplacements vides, compositing ensuite (« the model cannot hold numbers »).
- [PIÈGE] Les modèles vidéo ignorent les barrières : lave et pièces traversent une goupille fermée.
  Un seul mouvement visible par chemin ; préférer chutes et couloirs droits (un tuyau/coude invite
  un raccourci hors du tuyau) ; nommer l'état de chaque barrière (« coins stay inside the glass »)
  et ce qui reste immobile.
- [MÉTHODE] Étapes chaînées : une image d'état par étape, chacune ÉDITÉE depuis la précédente
  (mêmes comptes) ; chaque prise épinglée first frame = état N, last frame = état N+1, un mouvement
  visible. Épingler la dernière image verrouille aussi la caméra (non épinglée, une prise a dérivé
  en push-in). Masquer seulement ce qui change ; une édition peut modifier hors masque → recoller
  la seule zone masquée.
- [CHOIX] Plateau à mouvements exacts (match-3, tri, fusion, vis) : scripté entièrement depuis des
  pièces découpées ; la vidéo ne donne que l'ambiance (« No video take swapped two gems »).
- [PIÈGE] Caméra : une seule, verrouillée, qualité finale ; pas de push-in sur un plateau chargé
  (tuyaux, portes se déforment) ; demander une prise plus longue et garder la partie propre ; faire
  se poser les prises épinglées 1 s avant la fin.
- [PIÈGE] Sujet qui grandit : les membres vidéo gonflent/rétrécissent contre les images épinglées →
  scripter la croissance ou épingler une image par taille.
- [PIÈGE] « every other cat stays perfectly still in its idle pose » nécessaire, sinon toute la
  foule réagit à l'unisson ; une prise ne peut pas viser une case précise → zoomer la première
  image sur la case.
- [PIÈGE] Archétype qui dérive vers un personnage réel (conducteur → casquette rouge, moustache,
  chemise bleue) : nommer un look original, vérifier l'image ; prise signalée IP → reformuler
  génériquement, sinon faire le temps en calques.
- [CHOIX] Son : un impact sur chaque évènement visible ; un passage video-to-audio ajoute de
  l'incident mais rate les évènements ; musique générée séparément sans nappes d'ambiance ; bruits
  d'animaux par un modèle SFX (« speech models cannot meow »).
- [PARAM] Plateau généré au canevas de livraison (1080x1920, 1080x1350, 1080x1080, 1920x1080) ;
  sujet de la promesse ≥ 4 % de la largeur ; chiffres HUD ≥ 72 px sur 1080.

**Correspondance Deepotus.** Image edit (nano-banana-pro, gpt-image-2.5, qwen-image-3 pour
retouches masquées), i2v first+last (kling-v3-pro, seedance-2.5, veo-3.1, ltx-2.5), SFX
ElevenLabs, hunyuan-foley (video-to-audio). Paramètres absents : masque d'édition image,
first/last frame imposés pour ce cas.
**Propre à Scenario.** Compositeur (≤ 50 couches dont 49 audio), scripts check_take/render_tracks.

## 22. scenario-playable-ads

**Résumé.** Pub jouable HTML5 (≤ 2 Mo Meta) reconstruisant la boucle de jeu en code depuis un
enregistrement ; Scenario génère plaque, planches de sprites, logo, rendu propre pour 3D, maillage
3D, texture, SFX, musique. Famille : img2img multi-réf, img23d, txt2audio.

- [PARAM] Réglages qui ont marché : plaque img2img 2–3 images de référence, haute qualité,
  1152x2048 ; planches de sprites img2img fond transparent 1536x1024 en 3x2 cases ; rendu propre
  pour 3D 1024², un objet, fond gris moyen uni, vue 3/4 ; texture tileable txt2img 1024² ; SFX
  0,3–2,5 s ; musique boucle instrumentale 30 s. ≤ 4 jobs en vol.
- [PROMPT] Plaque : « Remove: … » (chaque perso/objet/effet/chiffre/HUD avec sa position) + « Keep
  exactly the same: … » (décor, cadrage, caméra) + « Fill where characters were with matching
  floor; nothing on the floor » ; images floues : « the frames are small and a little soft: redraw
  at full detail, same design ».
- [PROMPT] Planches : « Strict 3 columns by 2 rows, exactly one element per cell, generous empty
  transparent space, nothing crossing a cell border, no grid lines, no labels » ; numéroter chaque
  case avec sa direction de vue ; variantes de couleur « match the pieces in the reference frames
  exactly; only the color changes » ; panneaux vierges, chiffres en code ; 2 planches (persos,
  props) plutôt qu'une chargée. Découpe par blobs (la grille n'est jamais exacte).
- [PROMPT] Musique : « Starts immediately at full energy on the first beat, no intro, no fade in, no
  outro, loops seamlessly ». SFX à attaque instantanée ; variantes = même prise à une autre vitesse,
  pas un nouveau job.
- [PARAM] Image→3D pour pub : limite de faces ≈ 6 000 si exposée, texture standard, **pas de PBR,
  pas de delighting** (garde l'éclairage cuit pour un matériau non éclairé), alignement à l'image si
  offert. Constats : « 7.7k triangles came back for a 6,000-face limit » ; GLB 1,6 Mo avec texture
  JPEG 2048² → réduire à 512 ; ≈ 10° d'écart en lacet malgré l'alignement ; UV glTF → `flipY =
  false` ; supprimer les normales, `MeshBasicMaterial`.
- [MÉTHODE] Style d'assets fournis : 2–4 fichiers de référence (≤ 2048 px), style écrit en mots
  (palette, trait, ombrage, proportions, angle caméra) dans chaque prompt + « match the line weight,
  shading, palette and proportions of the reference sprites exactly; same camera angle and scale;
  only the subject is new » ; 3D à côté de modèles fournis = même budget de sommets (10k–30k pour
  un mobile) et même taille de texture.
- [PARAM] Conversions : FBX/OBJ/BLEND/USD → un GLB ; GLB Draco à réexporter sans Draco ; GLB
  multi-pièces à joindre ; maillage riggé → rendre les clips en images (planche).

**Correspondance Deepotus.** Image : nano-banana-pro/-2.1, gpt-image-2.5 ; 3D : meshy-6/7/7.1,
tripo, rodin-2.5, hunyuan3d, trellis-2 ; musique/SFX. Paramètres absents : `face_limit`/polycount
cible, PBR on/off, delighting, alignement à l'image d'entrée.
**Propre à Scenario.** Runtime PA, qa.py, pack_glb.py (MIT, réutilisable pour un export web).

## 23. scenario-comic-creator

**Résumé.** BD / manga / roman graphique (3 à 900 pages), cadeau personnalisé ou BD d'entreprise ;
décisions verrouillées dans l'ordre histoire → direction → style → casting → script → pages →
revue. Famille : image à références multiples, page entière par génération, lettrage intégré ou
en overlay.

- [CHOIX] Unité = la PAGE entière (le modèle dessine cases, gouttières, bulles ensemble) — sauf
  webtoon vertical, animation, ou case qui échoue toujours (contraste avec scenario-storyboards qui
  génère par case).
- [CHOIX] Modèle le mieux classé, à la **qualité maximale** pour le tour de style, les fiches et les
  pages finales, même si le classement suggère un palier inférieur ; ne pas changer de modèle en
  cours de livre (le look dérive) ; un modèle sans champ de référence image ne peut porter les
  fiches.
- [COÛT] Épreuve à qualité moyenne puis finale à qualité max : l'épreuve garde mise en page,
  contenu, bulles et mots, ≈ 1/10 du prix final ; qualité la plus basse ≈ 1/17 du prix et ≈ 20 %
  plus rapide (pas pour l'épreuve). Une page qualité max ≈ 70–100 s ; pages lancées ensemble
  finissent ensemble. Plafond : ≤ 4 générations qualité max par page (lane courte).
- [PIÈGE] Jamais d'édition en chaîne (« Editing an edit melts faces and costumes ») ; jamais une
  épreuve comme référence ; finale = génération neuve depuis prompt et références d'origine ; une
  seed ne reproduit qu'avec tous les champs identiques (la qualité change → cadrage/visages
  changent).
- [PROMPT] Longueur : 600–1 000 mots une fois le gabarit établi (300–1 700 observés) — « Length is
  the checklist the model follows » ; sections : direction artistique (2 influences nommées, règles
  dures, liste FORBIDDEN), anatomie, décor, lumière (source unique motivée, où tombent les ombres),
  casting + fiche + état, équipement par case, mise en page (nombre de cases, disposition, sens de
  lecture), cases (caméra, phase d'action, regard, expression, mots exacts, locuteur), références
  numérotées par rôle, règles.
- [PROMPT] Référence par rôle : « Reference 1 sets line, color, paper and lettering only, never its
  characters or composition… References 2 and 3 set identity only… never their pose, expression or
  backdrop ». ≈ 5 références par page ; chaque fiche de plus peut déplacer le style.
- [PROMPT] Ligne d'ouverture : « The drawing style decides everything. Commit to it with the
  confidence, limits and imperfections of a real artist's hand, never a generic polished digital
  illustration. »
- [PROMPT] Trois niveaux : simple (→ illustration « cosy » stock), « mood » (→ peinture cinéma
  sombre stock), dirigé (2 influences + matière/outil + 3 règles dures + FORBIDDEN + un choix propre
  à l'histoire). Test : sur 11 directions, 4 ont gardé une identité, 4 sont revenues en peinture
  sombre ; règles + FORBIDDEN en ont sauvé 3. Bibliothèque de directions prêtes (Mignola,
  Pratt/Muñoz, Urasawa/Otomo, Hergé/Chaland, Blake/Sempé…) ; si le modèle ou la détection IP refuse
  un nom, garder les traits et les règles, retirer le nom.
- [PROMPT] « A word in the prompt draws what it names » : « no gray » fait apparaître du gris, un
  mot de saison ajoute du feuillage, « faintly » une 3e teinte → énoncer la règle positivement
  (« two inks, black and orange, on white paper ») et retirer tout mot contraire. Un « night » dans
  le paragraphe de style annule une ligne TIME du matin.
- [PROMPT] Ligne TIME avant la case 1, répétée là où elle compte ; bloc décor identique mot pour mot
  entre pages du même lieu ; comptes > 4 non fiables en petite case (« three in front, three
  behind ») ; tailles relatives au corps ; costumes répétés dans chaque case ; mots imprimés dans la
  casse qui sera imprimée ; chaque conteneur de texte décrit comme un objet (« a round white
  balloon, tail to Mara, reading: … »).
- [MÉTHODE] Table défaut → clause (remplacer la clause, ne pas empiler l'historique) : lampes
  allumées après « no fire » → nommer la seule source ; cavalier fusionné à la monture → ordre,
  écart, rêne comme une ligne visible ; deux mains identiques → main gauche à l'écran à gauche,
  pouces vers l'intérieur ; accessoire long qui rétrécit → longueur vs corps à chaque case ; texte à
  supprimer → « X says nothing: no balloon ». Deux réécritures sans effet → résiduel accepté.
- [MÉTHODE] Lettrage : tester sur les 2 pages les plus bavardes ; tout exact → lettrage intégré (une
  langue) ; sinon overlay (bulles vides dimensionnées au nombre de mots). Réparation de texte seule
  par un modèle d'édition de texte en place, une seule fois.
- [MÉTHODE] Photo → fiche stylisée une fois, approuvée ; ensuite la FICHE est la référence (« A
  photo pulls pages toward photographic rendering ») ; « sets face, hair and build, never pose,
  clothes or background » ; photo ≈ 2 000 px côté long. Fiche : visage calme, face/dos, une pose
  expressive, accessoires ; âge par repère tête/corps ; changement durable = 2e fiche.
- [PARAM] Taille : ≈ 1 500 px de large écran, ≈ 2 500 px A4 300 dpi ; ratio portrait le plus proche
  autorisé ; lire la taille réelle (un modèle peut rendre moins) ; marges souvent ignorées (bulles
  dans les cases, jamais au bord).
- [COÛT] Devis avec de vrais ids d'assets (un id inventé fait échouer le dry run) ; les références
  modifient légèrement le prix.

**Correspondance Deepotus.** Ids image multi-réf : nano-banana-pro, nano-banana-2.1,
gpt-image-2(.5) (qualité low/medium/high), seedream-5-pro, flux-3, qwen-image-3 (édition de texte),
ideogram-4.5 (lettrage). Paramètres absents : `quality` (épreuve vs finale) selon modèle, plafond
et rôle des références.
**Propre à Scenario.** build_book.py (PDF, MIT), évaluateurs-agents, collections.

## 24. scenario-blender-2d-animation

**Résumé.** Plan 2D (plate-forme, cinématique) monté dans Blender à partir d'images générées
(cartes plates en profondeur, caméra orthographique, physique) ; un « look » = 10 générations.
Famille : txt2img à référence + i2v (cycle de course).

- [MÉTHODE] Une image concept (« capture d'écran du jeu fini ») fixe le look ; les 8 autres images
  la prennent en référence ; le clip de course part de la pose de repos recadrée, JAMAIS du concept.
- [PROMPT] Concept : « In-game screenshot of a premium polished 2D side-scrolling mobile
  platformer… Scene, strictly side view, layered for parallax: [sky]; [far]; [mid]; a ground strip
  … with a clear flat walkable top edge… No text, no UI, no logo, no HUD » ; couches nommées dans
  l'ordre d'empilement.
- [PROMPT] Couches (édition, concept en référence) : « [Role] layer… in exactly the same art style,
  colors and [light] as the reference screenshot, on a fully transparent background… Everything
  above [its top] is completely transparent: no [layers behind]. No [layers in front], no
  characters, no text. Wide panoramic layer, strictly side view. »
- [PARAM] Tailles : ciel 2560x1440 opaque (« ONLY THE SKY ») ; lointain et moyen 3072x1152
  transparents ; sol 2048x768 (« flat, level walkable top edge… at about 30% from the top », « no
  rounded end caps ») ; premier plan 3072x1024 ; props 2048x1536 ; arbre 1024x1536 (« NO [fruit]
  in the crown ») ; héros 1536x1024 opaque magenta 2 prises ; concept 1536x864 2 prises.
- [PROMPT] Course i2v 5 s : « like a treadmill… stays centered and does not travel across the
  frame. Locked static camera, no zoom, flat solid magenta background that never changes, no ground,
  no ground shadow… no motion blur » — chacun de ces termes a corrigé un échec. Une période propre =
  9–12 images à 24 fps.
- [PIÈGE] Fond qui dérive pendant le clip (magenta → rouge → jaune → vert) : clé par couleur de bord
  et fenêtre de boucle loin des zones roses/rouges du perso.
- [PIÈGE] Un repère large (arche, château) en bout de couche est coupé au tuilage → contenu réparti
  sur toute la largeur.
- [CHOIX] Image : entrée référence + fond transparent + largeur/hauteur exactes ; si le premier
  choix est un spécialiste d'un autre style (pixel pour du cartoon peint), prendre le suivant.
- [COÛT] Un dry run citant un asset pas encore créé renvoie 404 → deviser le concept, estimer le
  reste, puis deviser chaque payload quand son entrée existe.

**Correspondance Deepotus.** Plateau 3D / Tilelab / Spritelab ; image gpt-image-2(.5),
nano-banana ; vidéo i2v. Paramètres absents : fond transparent, tailles libres exactes (beaucoup de
modèles fal n'acceptent que des préréglages).
**Propre à Scenario.** build_scene.py (Blender, MIT), mesures locales.

## 25. scenario-workflow-authoring

**Résumé.** Créer/éditer des graphes de workflow Scenario (editor_info), importer des graphes
Weavy/ComfyUI. Famille : orchestration, pas de modèle propre.

- [PIÈGE] Plusieurs assets branchés sur le champ référence d'un modèle = UNE génération conditionnée
  par tous (10 photos produit → 1 image mélangée), pas 10 éditions → boucle forEach. Dry run d'une
  boucle = prix d'UNE itération.
- [MÉTHODE] Import ComfyUI : checkpoint/LoRA/VAE/sampler/latent repliés dans le nœud modèle ; seuls
  seed, cfg, steps, largeur/hauteur/batch passent s'ils ont le MÊME sens dans le schéma cible (« cfg
  and guidance can mean different things ») ; un nom de checkpoint (`flux1-dev.safetensors`)
  désigne une famille, pas un fichier ; prendre le membre le plus récent non déprécié.
- [MÉTHODE] Nœud LLM : n'en ajouter que si l'utilisateur demande de l'écriture (légende,
  réécriture, variantes) — « llm nodes are the top authoring failure mode ».

**Correspondance Deepotus.** Atelier nœuds IA (t272) : règles transposables (boucle par item,
mapping de paramètres par sens, pas de nœud LLM superflu). Pas d'id touché.

---

# PARTIE 2 — Survol des experts DCC et moteurs (87 skills)

Familles : dcc/blender (15), dcc/maya (11), dcc/zbrush (9), game-engines/godot (14), roblox (14),
unity (14), unreal (10). Seul ce qui touche aux sorties génératives et à leur import est relevé.

## Maillages image→3D : ce que disent les experts (synthèse multi-familles)

- [PIÈGE] Échelle arbitraire : un GLB généré arrive « unit-boxed » (≈ 0,95 unité, Roblox), origine
  au centre → s'enfonce dans le sol ; hauteurs relevées 0,56 m à 8,1 m sans rapport avec l'objet
  (« a toy robot at 1.96 m », Godot). Correctif : manifeste par asset (`category`, `height_m` ou
  `longest_m`, `source`) → mise à l'échelle sur la hauteur cible, pivot au centre de la base, scale
  appliquée (1,1,1). Les fichiers IA se déclarent « Khronos glTF Blender I/O » : seul le manifeste
  permet de les reconnaître.
- [PIÈGE] Orientation : glTF Y-up, avant +Z ; Roblox LookVector −Z → lacet 180° ; Blender Z-up,
  avant −Y ; ZBrush : ne tourner qu'en présence d'un indice Z-up.
- [PIÈGE] Matériaux : tous `doubleSided`, `metallicFactor` 1.0 avec métal peint partiel, cartes JPEG
  2048 (Roblox) ou 4K (Godot) ; 2 à 35 matériaux ; 8/12 fichiers utilisent clearcoat, transmission,
  ior ou specular, que Godot 4.7.2 ignore sans avertir. Réimport glTF→Blender via Separate Color perd
  metallic/roughness (Metallic 0, Roughness 0,5) ; Unity n'assigne pas metallic/roughness depuis un
  FBX ; une image packée sans extension n'est pas importée par Unity (asset non texturé, aucun
  avertissement).
- [PARAM] Triangles observés : 917 à 181k (Godot, 12 fichiers, 3 au-dessus de 3× le budget) ;
  Tripo P2 robot 53 076, Meshy T2 héros 15 092, Hitem3D phare 986 642 sans matériau ; « Tripo, Meshy
  and Hitem3D files arrived unit-boxed, pivot centered, double-sided, metallic 1.0, 4K maps, 15k to
  1M triangles » ; un expert remaille d'abord à 6k–8k triangles.
- [PARAM] Budgets par catégorie (politique Godot : triangles LOD0 / matériaux / côté texture) :
  défaut 5 000 / 4 / 1024 ; petits objets 3 000 ; meuble 10 000 / 6 ; jouet 20 000 / 8 ; véhicule
  40 000 / 12 / 2048 ; héros 60 000 / 12 / 2048 ; rejet au-delà de 3× le budget. Roblox : 20 000
  triangles par maillage, 4 000 par accessoire, texture 256 px par 2x2x2 studs (puissance de 2 ;
  max 4096 en lieu, ColorMap avatar 1024, autres cartes avatar 256), 4 influences par sommet, ≤ 10
  composants par accessoire. Pub jouable mobile : 10k–30k sommets.
- [PIÈGE] Topologie : « triangle soup », trous (« pinholes »), coques fines, bouche/yeux fusionnés
  sur les persos, vêtements fusionnés, symétrie très basse si posé, faces lamina, arêtes à 3 faces.
  Remplissage automatique insuffisant (« hole filling closed 4 of 24 borders ») ; Roblox exige
  étanche ; ZBrush : « A generated or scanned mesh is a form reference, not topology to repair »
  (DynaMesh après épaississement, Tri2Quad).
- [MÉTHODE] Finition IA standard (Blender/Maya/ZBrush) : audit → retopo (QuadriFlow, repli voxel
  remesh à 1/250 de la taille si soupe de triangles) → UV → **cuire les cartes DEPUIS le maillage
  généré d'origine** (pas la copie voxel) → PBR → export préréglé → réimport et comparaison.
  Matériau box-projeté (sans UV) possible pour props rigides avant UV.
- [MÉTHODE] Export par moteur (préréglages mesurés) : Unity FBX scale ALL ; Unreal FBX scale NONE
  (cm) ; Godot GLB ; Roblox FBX scale UNITS ; web GLB meshopt + WebP ; USDZ textures 2048 ; STL en mm
  (×1000). Collision : hull convexe plafonné à 64 sommets (le hull complet d'une table générée de
  17 500 triangles = 12 270 faces ouvertes) ; LOD par décimation (souder les coutures UV d'abord).
- [MÉTHODE] Import Godot : `generate_lods`, `create_shadow_meshes`, textures extraites puis
  réduites à 2048 en VRAM, cull back sur matériaux simple face, StaticBody box/convex/trimesh.
- [CHOIX] Unreal : Nanite par éligibilité (opaque/masqué statique), pas par nombre de triangles ;
  pas sur translucide ni morph targets ; collision simple toujours requise.
- [MÉTHODE] Rig : un seul os racine, pas d'os feuilles, actions nommées comme les clips ; jeux
  FACS/ARKit/visèmes. Persos riggés générés (scenario-3d « Rigging and animation ») → retarget.

## Sprites, textures, audio générés : ce que disent les experts

- [MÉTHODE] Godot 2D : détecter l'échelle et la phase de pixel, snapper si décalé, recaler chaque
  clip sur sa ligne de pieds, vérifier la frange de couleur-clé en filtrage linéaire ; manifeste
  `frames, w, h, ground` ; demander la taille pixel native et la couleur-clé.
- [MÉTHODE] Unity 2D : un seul PPU pour tous les sprites (défaut pixel 16 PPU, 320x180), filtre
  Point, compression None (pages d'atlas pixel non compressées), pivots au pixel entier.
- [MÉTHODE] Textures PBR : tuilables, carrées, puissance de 2, normales OpenGL, métal 0 ou 1,
  empaquetage de canaux (albedo+hauteur, normale+rugosité) pour Terrain3D ; Unity mobile signale
  2048 au-dessus d'un plafond 1024.
- [PIÈGE] Audio IA : MP3 « chauds » (un fichier −8,4 LUFS, crête +0,99 dB) avec silence de
  remplissage → trim + loudnorm 2 passes pour les longs, niveau par crête pour les one-shots
  (loudnorm a raté de 3 LU sur 0,5 s) ; cibles −18 LUFS SFX/voix/musique, −24 ambiance (Godot) ;
  Roblox 48 kHz, < 20 Mo, < 7 min ; SFX en WAV mono.
- [PARAM] Flipbooks VFX : grilles 2x2, 4x4 ou 8x8 (Roblox).

## Blender blockout → vidéo (seul expert DCC qui parle directement de modèles vidéo)

- [CHOIX] Doublure selon la famille vidéo (test « Sky Islands », 1 prise par case) : Seedance 2.5
  (référence vidéo, suit le mouvement de près) → capsules « featured » (les membres articulés donnent
  une marche courte même avec une clause de course ; capsules → vraie course) ; H3 Max (3D-to-video,
  lit chaque proxy littéralement) → articulé ou featured, peu sensible au style, vérifier l'ordre en
  gros plan ; LTX 2.3 (rendu-réel, une image d'entrée) → tout style, la première image porte
  l'identité, mais laisse des proxies visibles.
- [PROMPT] Grammaire Seedance (« motion first ») : en-tête « The reference video is rehearsal
  footage… No shape, proportion, silhouette or surface in the video belongs in the final frame » ;
  casting par rôle et mouvement ; licence de proportion ; AUCUN mot de géométrie (box, cone, proxy,
  mannequin) ; queue d'exclusion courte ; planche de style déclarée (« take its art style, palette,
  materials and lighting, nothing else… never draw its gutters or a grid ») ; bloc de style en
  dernier (palette hex par rôle, lumières).
- [PROMPT] Grammaire H3 Max : clause d'autorité (« if text and video disagree, the video wins »),
  table de remplacement par classe (forme + couleur → objet réel), une ligne par héros avec sa
  direction, clause de re-rendu (aucune couleur plate/gris/primitive) ; limite de prompt **2 000
  caractères** sur H3 Max (wrapper du plugin compris : 1 466 car. refusés, ≈ 800 passés).
- [PARAM] Clips de 10–15 s gardent caméra et mise en page ; 20–30 s dérivent (personnages perdus,
  gros plans inventés) → plusieurs captures courtes. Playblast mannequin gris refusé par le filtre
  d'entrée d'un fournisseur ; couleurs d'identité saturées ou teinte globale acceptées.
- [PARAM] Plugin Render Video : capture silencieuse 1280x720 ; jusqu'à 15 assets de style ; durée
  par défaut du modèle conservée (6 s devisés à 5 s).

## Une ligne par famille

- **dcc/blender** (15) : routeur + sculpture, retopo, UV/cuisson, texturing, cheveux, rig,
  animation, previs, geometry nodes, éclairage, grease pencil, hard-surface, blockout, export ;
  utile : finition IA, préréglages d'export, porte `deliverable` (Roblox 20 000 tris).
- **dcc/maya** (11) : modélisation, retopo-UV (P18 « AI-generated character to animation-ready
  mesh » : intake tris/lamina/symétrie, gabarit ajusté, cavités bouche/yeux, test de déformation
  coude 130°, UV 4096), rig, déformation, lookdev, FX, groom, rendu, pipeline FBX ; entrée générée
  attendue en FBX/OBJ (glTF « à vérifier »).
- **dcc/zbrush** (9) : sculpture, perso/créature, hard-surface, stylisé, peinture/rendu, pose/
  impression 3D (STL/3MF en mm), retopo-export (Z6 : GLB → OBJ, triage, Weld + Tri2Quad, couleurs →
  polygroupes pour séparer les pièces fusionnées), automatisation.
- **game-engines/godot** (14) : 2D (art généré vérifié avant import), monde 3D (P8 import GLB IA par
  manifeste), audio (`prepare_ai_audio`), automatisation (dépôt de 200 GLB dont 12 image→3D) ; le
  reste (archi, gameplay, multijoueur, perf, rendu, shaders, UI, VFX) sans lien modèle.
- **game-engines/roblox** (14) : assets (triage GLB IA, studs, −Z, étanchéité, accessoires),
  animation (rigs/mouvements générés), environnement (MaterialVariants depuis textures PBR
  générées, skybox 6 faces), VFX-audio (flipbooks, audio 48 kHz) ; reste = code, réseau,
  monétisation.
- **game-engines/unity** (14) : 2D (PPU, Point, None), animation (FBX de scenario-3d), mobile
  (compression ASTC/ETC2), audit d'import (`model.scale_large`, normal map mal typée) ; reste =
  code, UI, perf, web, monde.
- **game-engines/unreal** (10) : import FBX/USD/glTF en masse (Nanite par éligibilité, collision,
  LOD), matériaux, monde, cinématiques ; maillages générés renvoyés à la finition DCC ; aucun réglage
  propre aux modèles génératifs.

**Correspondance Deepotus (Partie 2).** Fiches 3D (meshy-6/7/7.1, rodin-2.5, tripo h3.1/p1/p2,
hunyuan3d 2.1/3.1, trellis-2, triposr) : ajouter à chaque fiche une rubrique « sortie attendue »
(échelle arbitraire, pivot centré, double face, metallic 1.0, textures 2K–4K, plage de triangles) et
une étape « normalisation » (hauteur cible, pivot base, budget de catégorie, réduction de texture,
avant +Z/−Z). Manques cités : **Hitem3D** (absent de Deepotus ; probablement sur fal), segmentation
de pièces (scenario-3d), « Meshy T2 » (nom de palier à rapprocher de meshy-6/7). Paramètres
absents : `face_limit`, taille de texture, PBR on/off, delighting, symétrie, alignement à l'image,
format de sortie (GLB/FBX/OBJ/USDZ). Vidéo : H3 Max (= h3-max) limite de prompt 2 000 caractères ;
LTX 2.3 cité (Deepotus a ltx-2.5) ; Seedance 2.5 en référence vidéo.

---

# Tableau récapitulatif

| Skill | Ids Deepotus touchés | Nb faits | Manques (modèles) | Manques (paramètres) |
| --- | --- | --- | --- | --- |
| ad-variants | vidéo (édition), Montage | 8 | video2video « edit » (Kling O-series, Seedance edit) | variante + invariants, pas 0,1 s |
| admin-analytics | — (Dépenses) | 1 | — | — |
| blender | meshy-*, rodin-2.5, tripo, hunyuan3d, trellis-2 | 7 | matériau PBR génératif, panorama 360, edit3d | devis gelé + accord du montant exact |
| storyboards | nano-banana-*, gpt-image-*, seedream-5-pro, flux-3 ; seedance, kling, veo | 12 | — | plafond et rôle des références |
| fan-cam | nano-banana-pro/2.1, gpt-image-2.5, seedream ; kling, seedance, veo, h3-max | 10 | — | nb de références d'édition, multi-temps |
| reel-recast | seedance-2, -2-fast, -2.5 | 12 | Seedance edit / reference-to-video (fal ?) | referenceVideos, duration −1, draft/completion, tags @ |
| thumbnails | flux-3, nano-banana-pro, gpt-image-2(.5), ideogram-4.5, seedream, qwen-image-3 | 8 | — | références typées, contrôle à taille réduite |
| ugc | HeyGen, eleven_*, veo-3.1, seedance, kling | 12 | lipsync dédiés, Kling motion control, avatars (OmniHuman) | interrupteur sous-titres, keepOriginalSound |
| report | — | 1 | — | — |
| team-admin | — | 1 | — | — |
| workflows | — | 3 | — | plafond de prompt par modèle (≥ 4 000 car.) |
| chatgpt-pet-create | gpt-image-2.5-sunburst, nano-banana-2.1 | 17 | Pixel Snapper (outil) | background, quality, refs 10/14, hauteur ≥ largeur/3 |
| chatgpt-pet-update | idem | 4 | — | — |
| game-assets | flux, gpt-image-*, nano-banana-*, recraft-4.1-vecteur ; rembg, matte | 16 | générateur alpha natif, Retro Diffusion, séparation en plans, upscaler pixel | seed, expansion de prompt off, masque + polarité, nb d'échantillons |
| sprite-animation | gpt-image-2(.5), kling-v3-pro, seedance, veo, ltx-2.5, pixverse-v6, flux-3-max | 30 | Retro Diffusion Animation/Plus, FLUX.3 Keyframes, Pixelate/Snapper | background, numOutputs, fps, loop natif, négatif vidéo, expansion off |
| side-view-game-kit | gpt-image-2(.5), nano-banana ; kling-v3-pro, seedance, ltx, veo | 15 | — | negativePrompt, cfgScale vidéo, generateAudio, background |
| kinetic-film | minimax-music, stable-audio, lyria, eleven-music, ace-step, mureka ; SFX ; flux-3, nano-banana-pro | 11 | — | bpm, instrumental, nb de sorties, négatif SFX |
| kinetic-music-video | seedance, kling, veo, wan-3.0, gemini-omni-flash, h3-max ; ace-step ; htdemucs | 21 | audio→vidéo lipsync (OmniHuman, Wan-S2V, Sync), correction lipsync | referenceAudio, plafond audio 10 s, mode cut-off |
| motion-loops | rembg/matte, i2v | 5 | — | — |
| video-ads | tous ids vidéo ; image edit ; eleven_* ; musique | 13 | reverse vidéo (local) | enum caméra, seed |
| game-ua-ads | image edit ; i2v first+last ; SFX, hunyuan-foley | 11 | — | masque d'édition, first/last imposés |
| playable-ads | nano-banana-*, gpt-image-2.5 ; meshy, tripo, rodin, hunyuan3d, trellis-2 ; musique/SFX | 9 | — | face_limit, PBR, delighting, alignement |
| comic-creator | nano-banana-pro/2.1, gpt-image-2(.5), seedream, flux-3, qwen-image-3, ideogram-4.5 | 18 | — | quality épreuve/finale, plafond et rôle des références |
| blender-2d-animation | gpt-image-2(.5), nano-banana ; i2v | 9 | — | fond transparent, tailles libres |
| workflow-authoring | — (Atelier nœuds) | 3 | — | — |
| Experts DCC + moteurs (87) | 3D (meshy, rodin, tripo, hunyuan3d, trellis-2, triposr), h3-max, ltx, seedance-2.5, audio | ≈ 35 | Hitem3D, segmentation de pièces | face_limit, taille de texture, PBR, orientation, format, normalisation post-import |

