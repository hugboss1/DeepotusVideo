# Lot « images » — fiches modèle tirées des skills Scenario (scenario-labs/skills b96506d)

Source : repo/skills/<skill>/SKILL.md (+ references/, README) lus en entier, 09/11/2026.
Les chiffres CU (Creative Units) sont des prix Scenario, PAS des prix fal : ils ne valent que comme
RATIOS entre paliers/membres. Tous les faits sont « at authoring time » côté Scenario : à revérifier
sur le schéma fal avant de les inscrire dans une fiche.

Rappel registre Deepotus (dz/image_providers.py, lu pour la correspondance) :
- `quality: "high"` est ÉCRIT en dur pour gpt-image-2(-fal), gpt-image-2.5-*(-fal) et ideogram-4.5 ;
  aucun palier brouillon n'est exposé.
- tailles = presets projet (`square`, `square_hd`, `portrait_4_3`, `portrait_16_9`,
  `landscape_4_3`, `landscape_16_9`) → `aspect_ratio` pour Nano Banana/flux-3/nano-banana-2.1,
  `image_size` pour seedream/ideogram/qwen/recraft ; OpenAI direct ramené à 1024² / 1536×1024 /
  1024×1536.
- `resolution` figée à 1K (nano-banana-2.1, flux-3) ; REF_MAX = 9 références ;
  GPT via fal n'envoie qu'UNE image en edit ; ideogram edit = `image_url` + `reference_image_urls`.
- `background: "transparent"` : Flare+Sunburst via fal, Flare seul en direct.
- seed : seulement `flux` (FLUX schnell). Aucun masque, aucun négatif, aucun `magicPrompt`,
  aucun `thinkingLevel`, aucune recherche web exposés.

---

## 1. scenario-image (socle transversal image)

**Résumé.** Règles communes à tous les modèles image : contrat par modèle (taille, longueur de
prompt, références), atteindre une taille exacte, rédaction du texte dans l'image et des edits.
Famille : txt2img / img2img / inpainting / outpainting, toutes familles.

**Faits**
- [PARAM] La taille n'a pas de forme commune : `width`/`height` avec min/max/step, enum
  (`aspectRatio`, `resolution` en MP ou paliers K, `size` mixte), ou ratio seul (taille exacte
  inatteignable). Pixels envoyés à un enum ou hors pas = rejet.
- [PARAM] Longueur max du prompt de « roughly 2000 characters to 32000 » selon le modèle : un prompt
  valide sur l'un est un 400 sur l'autre.
- [PIÈGE] Champ références : nom, plafond et cardinalité propres au modèle ; un champ nommé
  `referenceImages` peut être scalaire. Une chaîne nue envoyée à un champ tableau est IGNORÉE en
  silence (le run réussit sans la référence). Toujours une liste, même pour une seule image.
- [PROMPT] Plusieurs références → dire dans le prompt laquelle est laquelle.
- [PIÈGE] Un compteur (`numOutputs`/`num_images`) répète UN prompt → variations, pas un jeu.
  Un jeu (angles, poses, déclinaisons) = un appel par élément.
- [PIÈGE] Un membre peut remplacer en silence une taille sous son plancher : « 512x128 came back as
  1408x480 », sans erreur. Toujours relire largeur/hauteur du fichier rendu.
- [MÉTHODE] Taille exacte (icône 256², bannière 210×600) : générer à la taille atteignable la plus
  proche AU-DESSUS, au même ratio, puis redimensionner déterministe (`cover` = remplit et rogne au
  centre ; `stretch` = déforme ; `contain` = peut rendre plus petit que la boîte). Agrandir ne
  récupère pas de détail ; réduire masque le flou.
- [PARAM] Plusieurs membres sont à 1K par défaut avec un palier supérieur au schéma : poser
  explicitement la résolution / le palier de qualité pour un rendu neuf.
- [MÉTHODE] Pour garder une image validée en plus grand : upscaler l'image retenue, ne PAS relancer
  la recette (sans seed, c'est une nouvelle image ; même avec seed, il faut tous les champs
  identiques).
- [COÛT] Brouillon au palier le moins cher, puis upscale du gardé (au lieu d'un re-run haut palier).
- [PROMPT] Sortie trop littérale : séparer dans le prompt ce qui est FIXE et ce que le modèle peut
  inventer ; les détails inventés obéissent aussi aux contraintes fixes (pas de runes décoratives
  dans un brief sans texte).
- [PROMPT] Texte dans l'image : citer chaque chaîne entre guillemets + sa place (« the label reads
  'NORTH', top center ») ; peu de chaînes, courtes ; épeler lettre par lettre un mot qui se
  déforme. Texte non cité = reformulé.
- [CHOIX] Texte qui doit être exact à la lettre (prix, mentions légales) → compositing
  déterministe (overlay), jamais prompté.
- [PIÈGE] Prompt « film still », « cinematic » ou ratio écrit en prose (« 2.39:1 ») → bandes noires
  cuites dans l'image. Écrire « full frame edge to edge, no letterboxing, no black bars » et porter
  le ratio UNIQUEMENT par le champ de taille.
- [PROMPT] Peau visible : nommer la texture (pores visibles, duvet, léger reflet) sinon rendu lissé
  « retouché ».
- [PROMPT] Edit par instruction : nommer le changement ET épingler le reste (« keep its shape,
  fabric and shadow exactly » ; pour le texte : « change only the headline to 'X', same typeface,
  size and position »). Tout ce qui n'est pas nommé peut changer.
- [PIÈGE] Masques non interchangeables : l'un veut un canal alpha aux dimensions exactes de la
  source, l'autre un noir/blanc redimensionné ; les pixels « à peindre » diffèrent. Lire la
  description du champ masque du modèle.
- [MÉTHODE] Pas de masque sous la main : modèle de segmentation (phrase nominale ou boîte → un
  masque par objet) ; sinon édition par instruction en prose.
- [PIÈGE] « transparent background » dans le prompt : sortie opaque. Utiliser un champ
  `background` s'il existe, sinon détourage après coup.
- [PIÈGE] `aspectRatio` et `width`/`height` coexistent rarement ; champs inconnus rejetés : ne pas
  recopier un bloc de paramètres d'un modèle à l'autre.
- [PIÈGE] 403 « plan-restricted » : ne pas réessayer (équivalent Deepotus : clé manquante → autre
  modèle).

**Correspondance Deepotus.** Tous les ids image. Déjà conformes : listes `image_urls` toujours en
tableau (build_fal_image_request), sortie relue. Manques paramètres : aucun redimensionnement exact
post-génération côté façade (Deepotus a des presets, pas de taille pixel) ; pas de masque exposé
sur aucun id ; pas de palier résolution (1K figé) ; pas de champ « garder le cadre source ». Règles
« letterbox » et « texture de peau » à mettre dans le prompt-système de l'agent.

**Propre à Scenario.** `recommend`/`search`/`model_schema_get`/`dry_run`/`jobs_wait`, CU,
`model_scenario-resize-image`, `prompt_spark` : ne se transposent pas (seule l'idée « lire le schéma
fal avant chaque appel » et « estimer avant le lot » se transpose).

---

## 2. scenario-gemini-image (Nano Banana)

**Résumé.** Famille Gemini image de Google (Nano Banana) : génération et retouche par
instruction, fusion multi-références, extraction d'images d'une vidéo, ancrage Google Search.
Membres : 3.1 Flash, 3.0 Pro, 3.1 Lite.

**Faits**
- [PARAM] 3.1 Flash : résolution `512` à `4K`, défaut `1K` ; vidéo en entrée ; 4 niveaux de
  `thinkingLevel` ; Google Search.
- [PARAM] 3.0 Pro : `1K` à `4K`, défaut `2K` ; fait pour les edits complexes et la fusion
  multi-images ; Search oui ; pas de `thinkingLevel`.
- [PARAM] 3.1 Lite : 1K fixe, pas de champ `resolution` ; `thinkingLevel` = `MINIMAL` ou `HIGH` ;
  le plus rapide et le moins cher.
- [PARAM] Références « up to 14, an array even for one » ; `numOutputs` 1 à 4 ; ratios `21:9` à
  `9:16` + `auto` (défaut) ; prompt plafonné « near 250000 characters » (un brief complet tient).
- [PARAM] Flash seul : `video` (un clip ≈ 15 Mo, échantillonné à `videoFps`, défaut 1 i/s) pour
  tirer des images fixes d'une séquence ; `video` et références mutuellement exclusifs.
- [PARAM] Aucun masque, aucun seed, aucun négatif sur aucun membre : edits régionaux = phrases ;
  relancer = variation, jamais reproduction.
- [PARAM] `thinkingLevel` défaut `HIGH` (soigneux) sur Flash et Lite ; `MINIMAL` pour la vitesse
  sur des runs simples.
- [PROMPT] Phrases naturelles (sujet, décor, style), pas de listes de tags : « comma lists
  underperform ».
- [PROMPT] Edit : énoncer le changement + ce qui doit survivre (« keep the shoe's shape, colors,
  and branding unchanged; place it on a sunlit deck »).
- [PROMPT] Multi-références : rôles PAR POSITION (« image 1 is the character's face, image 2 the
  outfit, image 3 the background style ») ; sans rôles, les références se mélangent.
- [PROMPT] Verrou d'identité explicite : dire que les traits doivent être conservés pendant que
  pose / lumière / scène changent.
- [PROMPT] Texte : citer exactement + emplacement (« the title reads 'LUMEN', top third ») ; non
  cité = thème à illustrer, pas copie à rendre.
- [MÉTHODE] Mot qui se déforme : NE PAS relancer le design ; repasser l'image gardée en référence et
  épeler (« spelled L, U, M, E, N ») en ne changeant rien d'autre.
- [COÛT] La falaise de prix est ENTRE membres plus qu'entre résolutions : même edit 1K ≈ double
  sur Flash vs Lite, le 2K par défaut de Pro ≈ re-double ; Lite rend en moins de la moitié du
  temps.
- [COÛT] Search (`useGoogleSearch`) augmente le prix : ne le justifier que sur des sujets factuels
  réels, jamais pour du style.
- [PIÈGE] Champs non portables : `resolution` échoue sur Lite, `thinkingLevel` sur Pro, `video`
  hors Flash.
- [CHOIX] Lite pour itérer vite/pas cher ; Flash usage courant (et seul à lire la vidéo) ; Pro pour
  edits complexes et fusion multi-images.

**Correspondance Deepotus.** `nano-banana` (Gemini 2.5 Flash Image, ancien), `nano-banana-pro`
(≈ 3.0 Pro), `nano-banana-2.1` (vraisemblablement la ligne 3.1 Flash / « Nano Banana 2 » — à
confirmer). Manques modèles : **3.1 Lite** (probablement dispo sur fal, à signaler). Manques
paramètres : `resolution` (figée 1K sur nano-banana-2.1, absente sur pro → 2K par défaut côté
modèle ?) ; `thinkingLevel` ; `useGoogleSearch` (`enable_web_search` côté fal probable) ; entrée
`video` (Flash) ; REF_MAX Deepotus = 9 vs 14 annoncés ; `auto` comme ratio (Deepotus force un
ratio en t2i, le laisse au modèle en edit — cohérent avec la skill).

**Propre à Scenario.** Ids `model_google-gemini-*`, prix en CU, `dry_run` : non transposables.

---

## 3. scenario-gpt-image (GPT Image 2.5 Flare/Sunburst, 2, 1.5)

**Résumé.** Famille OpenAI : génération + edit par un seul prompt, références, masque alpha,
transparence, tailles pixel jusqu'à 4K, paliers de qualité jusqu'à `xhigh`/`max`.

**Faits**
- [PARAM] Prompt plafonné à 32000 caractères ; références jusqu'à 10 (tableau) ; `numOutputs` 1 à
  10.
- [PARAM] 2.5 Flare / Sunburst : `width`/`height` « 16 to 3840 px » ; `mask` PNG ; `quality` =
  auto, low, medium, high, xhigh, max ; fidélité réglée par le prompt seul.
- [PARAM] GPT Image 2 : même taille pixel et masque ; `quality` auto/low/medium/high seulement ;
  `background: transparent` REJETÉ.
- [PARAM] GPT Image 1.5 : `aspectRatio` auto/1:1/3:2/2:3 ; pas de masque ; quality high/medium/low
  (défaut high) ; `inputFidelity` : high verrouille, low réinterprète (seules les 5 premières
  références gardent la haute fidélité).
- [CHOIX] Flare = petit modèle rapide, qualité ≈ GPT Image 2 → travail courant. Sunburst = modèle
  de base, qualité > GPT Image 2 → texte dense de packaging, chiffres, schémas éclatés, edits qui
  doivent tenir la géométrie. Même contrat, même grille de prix.
- [CHOIX] GPT Image 2 = contrat 2.5 moins les deux paliers hauts, et son `high` coûte autant que
  leur `max` → tout travail neuf démarre sur 2.5.
- [CHOIX] 1.5 seulement pour `inputFidelity: low` (réinterpréter une référence) ou du 3:2/2:3 sans
  calcul de pixels. Détourage → membre 2.5.
- [COÛT] `quality` bouge le prix plus que la taille : 1024² = « 2, 3, 12, 20 and 45 CU » de low à
  max sur 2.5 ; GPT Image 2 : low 2, medium 12, high 45 ; `auto` = 12 partout ; 3840×2160 `max`
  Flare = 69 CU.
- [COÛT] Paliers : low pour brouillons, medium pour finals courants, high quand petit texte /
  légendes doivent rester lisibles ; xhigh/max seulement si le palier inférieur a raté une exigence
  précise (« a higher tier does not guarantee a better result »).
- [PIÈGE] `xhigh`/`max` envoyés à GPT Image 2 → 400 même en estimation.
- [PARAM] Grille OpenAI : chaque côté multiple de 16, grand côté ≤ 3840, ratio entre 1:3 et 3:1,
  pixels totaux entre 655 360 et 8 294 400 ; au-delà de 2560×1440 = expérimental.
- [PIÈGE] Hors grille : succès mais AUTRE taille, sans erreur : 3840×960 → 3840×1280 ;
  1000×1000 → 992×992 ; 3840×3840 → 2880×2880 sur Sunburst, refusé par Flare.
- [PARAM] Tailles sûres : 1024² (le plus rapide), 1536×1024, 1024×1536, 3840×2160 (4K), 2560×1088
  (vrai 21:9).
- [PIÈGE] Source d'edit hors 1:3–3:1 → rendue PADDÉE de bandes blanches (1326×313 → ≈2132×738,
  bandes ≈ 1/3 du cadre). Rogner après, ou passer par Ideogram (garde la taille source).
- [PARAM] Masque = PNG à la taille de la 1re référence, lu par l'ALPHA seul : transparent = édité,
  opaque = préservé ; blanc/noir RGB ignoré sans alpha. Le masque est une indication, pas un bord
  dur : recomposer l'edit sur l'original si une zone doit rester identique au pixel.
- [PARAM] Transparence 2.5 : alpha max 254 (jamais 255) ; halo de couleur sous les pixels
  transparents → toute surface qui perd l'alpha (JPEG, vignette, fond noir) montre un liseré.
  Garder PNG/WebP de bout en bout.
- [PROMPT] Détourage : « clean cutout with a crisp silhouette, fine edges and label text
  preserved, no halos, no restyling », puis inspecter l'alpha sur cheveux, verre, ombres.
- [PROMPT] Ordre = poids : style, médium, sujet, ambiance d'abord ; puis scène, détails, lumière,
  texte ; phrases naturelles. Nommer l'usage (pub, maquette UI, infographie, key art) pour régler
  le niveau de finition.
- [PROMPT] Photoréalisme : écrire « photorealistic » + textures concrètes (pores, usure du tissu,
  grain) ; personnes : cadrage, regard, ce que font les mains.
- [PROMPT] Brief détaillé = normalisé, pas embelli ; n'enrichir qu'un prompt générique ; ne jamais
  ajouter personnages, marques, slogans ou placements gauche/droite non demandés.
- [PIÈGE] Au-delà d'environ 7 exigences distinctes, certaines tombent en silence → base propre puis
  UNE modification ciblée par edit, en repassant la sortie précédente comme référence.
- [PROMPT] Edit : « change only X » + liste de ce qui survit, répétée à CHAQUE itération.
- [PROMPT] Références de style/ambiance ≠ cible d'edit ; rôle par index (« image 1 is the
  product, image 2 the palette »).
- [PROMPT] Texte : citer la copie exacte, épeler les mots difficiles, brief de mise en page (zone de
  chaque élément, rang de taille, ce qui reste vide), graisse et casse, nombre d'occurrences, et
  finir par « no extra words, no duplicate text ».
- [PIÈGE] Personnalités publiques nommées → refus ; décrire un archétype.
- [PARAM] Prompts complexes ≈ 2 minutes : attendre, ne pas relancer.
- [MÉTHODE] Héros produit avec titre : 3 brouillons `low` → choisir la composition → même prompt
  en `high`, 1 sortie → relire le texte avant de lancer en lot.

**Correspondance Deepotus.** `gpt-image-1`, `gpt-image-1-mini`, `gpt-image-2`, `gpt-image-2-fal`,
`gpt-image-2.5-flare(-fal)`, `gpt-image-2.5-sunburst(-fal)`. Manques modèles : **GPT Image 1.5**
(le seul à `inputFidelity`, probablement sur fal). Manques paramètres : `quality` (figé `high` →
pas de brouillon `low` à ~1/6 du prix, ni `xhigh`/`max`) ; taille pixel (Deepotus : 3 tailles
OpenAI, presets fal) → pas de 4K ni de 21:9 ; `mask` ; plusieurs références en edit (fal GPT
n'envoie qu'une image, alors que 10 sont possibles) ; `background` transparent en DIRECT pour
Sunburst (Deepotus le ferme d'après la doc OpenAI du 27/09, la skill dit « every tier » sur les
deux 2.5 — à revérifier) ; `inputFidelity`.

**Propre à Scenario.** Ids `model_openai-*`, CU, `dry_run` : non transposables.

---

## 4. scenario-grok-imagine-image (xAI Grok Imagine)

**Résumé.** Famille xAI : un même modèle fait t2i (références vides) et edit (références
remplies) ; force = texte lisible (affiches, packaging, infographies), photoréel par indices
caméra/lumière. Membres : 2.0, Quality, Image (non versionné).

**Faits**
- [PARAM] 2.0 : 14 ratios jusqu'à « 20:9 and 9:20 », défaut auto ; `quality` low/medium ;
  meilleur texte et edits.
- [PARAM] Quality : mêmes 14 ratios, défaut 1:1 ; rapide en 2k ; prix presque plat.
- [PARAM] Image : 10 ratios 2:1 à 1:2 ; le moins cher par image.
- [PARAM] Commun : prompt ≤ 10000 caractères ; références plafonnées à 3 ; `numOutputs` 1 à 10 ;
  `resolution` 1k ou 2k. Ni seed, ni masque, ni négatif, ni taille pixel.
- [PARAM] `aspectRatio` décide CE QUI EST DANS LE CADRE (pas un simple recadrage) ; en edit il est
  IGNORÉ, la sortie suit les proportions de la source.
- [COÛT] Itérer sur le membre non versionné ou 2.0 en `quality: low` à 1k ; dépenser un medium 2k
  sur les gardés. 2.0 en 2k t2i « well over a minute » contre quelques secondes pour les autres.
- [PROMPT] Copie verbatim entre guillemets, chacune avec un rôle (« the title reads … », « a line
  beneath reads … »), chaînes courtes, finir par « no other text » (sinon labels inventés).
- [PROMPT] Chiffres et statistiques réels en copie citée : les chiffres inventés paraissent
  plausibles.
- [PARAM] Petit texte → 2k ; relire en pleine taille avant de construire dessus.
- [PROMPT] Hors texte : brief court en langue naturelle (sujet, décor, composition, lumière,
  finition) « in 30 to 80 words » ; adjectifs qualité (« 8K », « masterpiece ») ignorés.
- [PIÈGE] Négatifs largement ignorés : formuler en positif (« clean empty background », pas « no
  clutter ») ; une seule esthétique par prompt.
- [MÉTHODE] Edit chirurgical : décrire seulement ce qui change + nommer ce qui reste ; UN edit par
  run, chaîné ; rôle de chaque référence (sujet, style, scène).
- [PIÈGE] Recadrer AVANT l'edit, jamais via `aspectRatio`.

**Correspondance Deepotus.** Aucun id. Manque modèle : **Grok Imagine Image 2.0 / Quality / Image**
(xAI ; présence sur fal probable pour au moins un membre, à signaler). Paramètres associés à
exposer si ajouté : `quality`, `resolution` 1k/2k, ratios étendus 20:9 / 9:20.

**Propre à Scenario.** Ids `model_xai-*`, CU : non transposables.

---

## 5. scenario-ideogram (Ideogram 4.5 et membres spécialisés)

**Résumé.** Famille de membres mono-tâche : 4.5 (génération à texte lisible, edits guidés), 4.5
Precise Edit (changer une chose), V3 Generate Transparent (alpha natif), V3 Layerize Text (texte
éditable), Character (identité), Remove Background.

**Faits**
- [PARAM] 4.5 : références « up to 5, the first is the source », `mask`, `aspectRatio` (auto,
  source, 25 ratios de 3:1 à 1:3), `resolution` 1K/2K, `quality`, `magicPrompt`, `numOutputs` ≤ 8.
- [PARAM] 4.5 Precise Edit : `image` (la sortie garde sa taille), `mask`, références ≤ 4 guides,
  `quality` défaut medium, `numOutputs` ≤ 8.
- [PARAM] V3 Generate Transparent : `negativePrompt` (le SEUL de la famille), 15 ratios,
  `renderingSpeed` (+FLASH), `expandPrompt`, seed.
- [PARAM] V3 Layerize Text : `image`, prompt optionnel, police par niveau (H1, H2, Body, Small) par
  nom OU fichier, jamais les deux ; seed. Sortie = base sans texte + blocs (rôle, position,
  contenu) → localisation.
- [PARAM] Character : `characterReferenceImage`, `styleType` (Auto, Fiction, Realistic),
  `renderingSpeed` (Default, Turbo, Quality), `image`+`mask` pour inpainting ; seed.
- [PARAM] Remove Background : `image` (10 Mo max) ; reconstruit les bords en transparence partielle
  (cheveux, fourrure, verre survivent).
- [PIÈGE] Masques inversés selon le membre : sur 4.5 et Precise Edit le BLANC = zone à éditer ; sur
  Character le NOIR repeint, le blanc reste.
- [PIÈGE] Casse : `renderingSpeed` en MAJUSCULES sur V3 Transparent, en Title case sur Character.
- [COÛT] `quality` = le cadran prix (very_low, low, medium, high) : « 7.75, 13.75, and 41.75 CU »
  pour low/medium/high ; very_low (Precise Edit) 3.75 ; MÊME prix à 1K et 2K et quelle que soit la
  taille de la source. `very_low` exige une image d'entrée.
- [COÛT] 4.5 est par défaut à `high`, son palier le plus cher : brouillons en low/medium. Precise
  Edit `high` = meilleur de plusieurs candidats, ×3 le prix.
- [PIÈGE] Les noms de paliers ne s'alignent pas entre familles : `high` Ideogram = plafond ; `high`
  GPT 2.5 = 3e palier sur 5, prix ≈ medium Ideogram. Comparer à PRIX égal, pas à nom égal.
- [PARAM] 2K observé : 2048² (1:1), 2560×1440 (16:9), 2880×1440 (2:1), 3072×1024 (3:1) → grand côté
  ≈ 3072, pas de 4K. 1K ≈ 1 MP (16:9 = 1280×720), uniquement pour 1:1, 4:5, 3:4, 2:3, 5:8, 9:16,
  1:2 et inverses.
- [PIÈGE] 3:1 en 1K passe l'estimation puis échoue au run ; ratio hors liste (4:1) = 400.
- [PARAM] Un `mask` exige `aspectRatio: "auto"`.
- [MÉTHODE] Edit qui garde la toile : `aspectRatio: "source"` (4.5) ou Precise Edit → taille
  source EXACTE même hors liste (1326×313 rendu 1326×313) ; `auto` reconstruit une scène 3072×1024.
  Indispensable pour planche de sprites, gabarit, mise en page.
- [MÉTHODE] Échange de titre localisé : pas besoin de masque sur Precise Edit (medium sans masque
  n'a pas touché au reste).
- [CHOIX] Banc d'essai vs GPT 2.5 (un échantillon) : Ideogram 4.5 perturbe 2 à 4× MOINS de pixels
  hors zone éditée (texte d'enseigne, ajout/retrait d'objets) et respecte mieux un médium peint
  (aquarelle, gouache, crayon). GPT 2.5 gagne sur produit photoréel, suivi d'un brief personnage,
  changement de matière/couleur (« burnished gold » → laiton olive chez Ideogram, qui a aussi
  recoloré l'épée à garder).
- [PROMPT] Tout prompt d'edit : « keep everything else exactly the same » + liste de ce qui
  survit.
- [PIÈGE] La réécriture automatique du prompt (`magicPrompt`, `expandPrompt`) peut paraphraser la
  copie exacte → la COUPER dès qu'il y a du texte, citer chaque copie avec place et style. Elle ne
  s'applique qu'au t2i (4.5 structure de toute façon les edits).
- [CHOIX] Transparence : native (V3 Transparent) pour un élément isolé (icône, sticker, UI) ;
  détourage (4.5 puis Remove Background) quand la typo / la qualité priment. « transparent
  background » prompté sur 4.5 = opaque.
- [PIÈGE] Character : inpainting = `image` + `mask` ensemble, `characterReferenceImage` reste
  obligatoire, champs de taille ignorés.

**Correspondance Deepotus.** `ideogram-4.5` (t2i `ideogram/v4.5`, edit `ideogram/v4.5/edit` avec
`image_url` + `reference_image_urls`) ; pricing a déjà `ideogram_rmbg_usd`
(fal-ai/ideogram/remove-background). Manques modèles : **4.5 Precise Edit**, **V3 Generate
Transparent**, **V3 Layerize Text**, **Character** (probablement sur fal, au moins V3 et character
existaient chez fal). Manques paramètres : `quality` (figé high = 0,22 $ → aucun brouillon) ;
`magicPrompt`/`expand_prompt` (crucial pour le texte exact) ; `resolution` 1K/2K ; `aspectRatio:
source` (garder la toile) ; `mask` ; `num_images` > 1 (multi exposé ? oui par défaut) ; seed (V3).

**Propre à Scenario.** Ids `model_ideogram-*`, CU (« 1.75 CU under each estimate ») : non
transposables.

---

## 6. scenario-luma-image (Luma Uni-1)

**Résumé.** Famille Luma Labs à raisonnement : génération et edit dans un contrat ; une image
`source` fait basculer en edit ; références à rôles ; recherche web ; titre exact. Membres : Uni-1
Max, Uni-1.

**Faits**
- [PARAM] Create : `prompt` (+ `imageRef`), ratio respecté, défaut **3:2**. Edit : `source` +
  `prompt` (+ `imageRef`), sortie au ratio source sauf `aspectRatio` posé.
- [PARAM] Références : Max 9, standard 8, la source occupe une place en edit ; prompt 6000
  caractères ; 9 ratios de 1:3 à 3:1 ; sortie png (défaut) ou jpeg.
- [PARAM] `webSearch` (défaut false) : le modèle va chercher des visuels réels avant de générer →
  pour un lieu, produit ou style réel que le modèle peut ignorer.
- [PARAM] Ni seed, ni masque, ni taille pixel, ni compteur de sorties ; taille = ratio seul.
- [PARAM] Latence : modèles qui raisonnent avant rendu, « median latency near 90 seconds » ; un
  dépassement n'est pas un échec.
- [COÛT] Chaque référence ajoute du coût. Max ≈ 2,5× le standard pour une image 2K, à notes
  d'arène quasi identiques → tester les deux avant un lot.
- [PROMPT] Une référence n'est suivie que si le prompt dit QUOI en prendre (ressemblance, style,
  composition, palette, lumière, texture, ambiance) ; pas de curseur d'adhérence, l'influence
  monte avec la précision (« use the first reference for the exact colorway and stitching »).
  Un rôle par référence.
- [MÉTHODE] Réutiliser UNE référence canonique à chaque itération tient le personnage stable.
- [PROMPT] Create = une scène en prose (sujet, décor, lumière, ambiance, style) et TOUJOURS nommer
  la lumière, « the single biggest quality lever ».
- [PROMPT] Texte entre guillemets ; l'avantage du Max est l'écriture NON latine précise, pas le
  latin en général.
- [PROMPT] Edit : changement d'abord, puis verrou (« Change X to Y. Keep Z exactly as it is. ») ;
  une scène ou un changement par run.
- [PIÈGE] Référence de style passée en `source` → bascule en edit et la sortie colle à la
  référence.
- [PIÈGE] Create sans ratio = 3:2, pas carré.

**Correspondance Deepotus.** Aucun id. Manque modèle : **Luma Uni-1 / Uni-1 Max** (présence fal
incertaine — Luma Photon était sur fal ; à signaler). Paramètres à prévoir : `webSearch`,
distinction source / références.

**Propre à Scenario.** Ids `model_luma-*` : non transposables.

---

## 7. scenario-mai-image (Microsoft MAI Image 2.5)

**Résumé.** Famille Microsoft : générateurs (2.5, 2.5 Pro) et éditeurs par instruction (2.5 Edit,
2.5 Pro Edit) ; trait de famille = typographie lisible et bien placée.

**Faits**
- [PARAM] 2.5 : t2i, 11 ratios dont 21:9. 2.5 Pro : t2i, 8 ratios. 2.5 Edit : source en
  `referenceImages` (tableau d'UN). 2.5 Pro Edit : source en `image` (fichier unique), 8 ratios.
- [PARAM] Prompt 4096 caractères (2.5 et Edit), 5000 (paire Pro) ; `aspectRatio` enum défaut
  `auto` ; `numOutputs` 1 à 4 (chaque image coûte).
- [PARAM] Ni largeur/hauteur, ni seed, ni négatif, ni masque ; `auto` choisit le ratio d'après le
  prompt (générateurs) ou suit la source (éditeurs) → le laisser en edit sauf recadrage voulu.
- [PROMPT] Prose, pas de tags ; ordre de raisonnement : sujet, composition, matières, lumière,
  ambiance.
- [PROMPT] Copie exacte entre guillemets + rôle + style + place (« the headline 'GAME DAY' in bold
  condensed type across the top third ») ; non cité = paraphrasé ; regrouper les petits blocs de
  texte (ils se concurrencent).
- [PARAM] Texte réglé pour l'anglais ; sorties « near 1K » → prévoir un upscale pour impression /
  héros.
- [PIÈGE] Pilotage positif seulement ; explorer avec `numOutputs` 2 à 4 et affiner la phrase plutôt
  que chercher un seed.
- [PROMPT] Edit : d'abord ce qui ne change pas, puis UN changement nommant l'élément exact et son
  nouvel état, nouvelle copie entre guillemets (« change the sign to 'OPEN 24/7', same font and
  color »). Plusieurs changements = passes chaînées ; l'identité tient bien entre itérations.
- [COÛT] Edit et Pro Edit partagent une même entrée d'arène (top 3) mais Pro Edit ≈ 4× le prix →
  commencer par Edit.
- [PIÈGE] Champ source différent entre les deux éditeurs : un bloc porté de l'un à l'autre casse.
- [MÉTHODE] Pas de reproduction possible : garder l'image gagnante et l'éditer en avant.

**Correspondance Deepotus.** Aucun id. Manque modèle : **MAI Image 2.5 / Pro / Edit / Pro Edit**
(disponibilité fal inconnue, à signaler). Utile pour affiches à texte anglais.

**Propre à Scenario.** Ids `model_microsoft-*` : non transposables.

---

## 8. scenario-reve (Reve v2.1, Reve Remix)

**Résumé.** v2.1 = générateur/éditeur à raisonnement (top 2 arène t2i) ; Remix = compositeur
rapide et bon marché qui fond 1 à 6 images en une.

**Faits**
- [PARAM] v2.1 : t2i + img2img ; `references` optionnel ; prompt 4000 ; 18 ratios de 4:1 à 1:4,
  défaut auto.
- [PARAM] Remix : img2img seul ; `referenceImages` OBLIGATOIRE, 1 à 6 ; prompt 2560 ; 7 ratios
  16:9 à 9:16, défaut 3:2.
- [PARAM] Trois paramètres seulement (prompt, références, ratio) ; ni masque, ni seed, ni taille
  pixel, ni négatif, ni compteur.
- [PROMPT] v2.1 adresse les références par balise `<frame>N</frame>` numérotée à partir de **0**
  dans l'ordre du tableau ; indispensable dès qu'il y a plus d'une référence.
- [PIÈGE] Compter les frames à partir de 1 : `<frame>1</frame>` est la DEUXIÈME référence.
- [PROMPT] Remix : pas de balises ; nommer en clair (« the bottle from the first image, the
  lighting from the second »).
- [PROMPT] v2.1 récompense des instructions précises en langage simple plutôt que des mots-clés ;
  le budget de 4000 laisse place aux contraintes.
- [CHOIX] v2.1 : génération seule + edits précis (texte d'affiche, recoloration, matière,
  relight, restyle, fusion avec sujets cohérents). Remix : mélange photos/illustrations/assets en
  composite cohérent.
- [COÛT] v2.1 = plusieurs fois le prix d'un Remix et > 1 min au p50 contre ~20 s.
- [PIÈGE] Prompt v2.1 de 4000 réutilisé sur Remix → dépasse 2560.

**Correspondance Deepotus.** Aucun id. Manques modèles : **Reve v2.1** et **Reve Remix**
(Reve était présent sur fal en text-to-image/edit/remix — probablement dispo, à signaler).

**Propre à Scenario.** Ids `model_reve-*` : non transposables.

---

## 9. scenario-seedream (ByteDance Seedream 5.0 Pro/Lite/Flash, 4.5, Layerize)

**Résumé.** Génération, edit par références, texte exact (scripts non latins inclus), jeux
d'images liées en un run, édition d'un asset transparent sans perdre l'alpha, découpe en calques
(Layerize).

**Faits**
- [PARAM] 5.0 Pro : références ≤ 10 ; `width`/`height` exacts « 672 to 3136 px, step 16 » ;
  texte exact ; prompt 3500.
- [PARAM] 5.0 Lite : références ≤ 14 ; jusqu'à 4K ; rapide, pas cher ; prompt 2048.
- [PARAM] 5.0 Flash : références ≤ 10 ; 672–3136 pas de 16 ; le moins cher ; `background` garde
  l'alpha d'une référence.
- [PARAM] 4.5 : `size` (2K, 4K) + `aspectRatio` enum ; edits qui préservent le sujet ; `auto`
  suit la source.
- [PARAM] Layerize Pro / Flash : une `image` obligatoire ; `size` auto/1K/1.5K/2K ; ne génère
  jamais ; Flash sans `optimizePromptMode`.
- [PARAM] Mode déduit des entrées : références vides = t2i ; une ou plus = edit ou génération
  multi-références (rôle par position) ; tableau même pour une.
- [PARAM] Mode séquence (`sequentialImageGeneration: "auto"` + `maxImages`) sur Lite et 4.5 : un
  jeu lié en un run, entrées + sorties plafonnées à 15 ; PAS sur Pro.
- [COÛT] 2048² : « 4 CU on Flash, 6 on Lite, and 18 on Pro » ; Pro ≈ 2 min contre < 1 → itérer
  sur Flash/Lite, Pro pour les finals.
- [PARAM] `optimizePromptMode` (Pro, Pro Layerize) : `standard` raisonne d'abord (plus lent) ;
  `fast` même prix, suffisant quand une référence fixe déjà la composition.
- [PIÈGE] Flash : son schéma dit que `width`/`height` ne valent qu'en résolution Custom, mais il
  n'a pas ce champ : les pixels s'appliquent directement.
- [PARAM] Flash `background: "transparent"` CONSERVE l'alpha à travers un edit, ne détoure pas ;
  garde l'entourage transparent, pas la translucidité interne (verre à alpha 170 rendu quasi
  opaque).
- [PIÈGE] `background` défaut `opaque` : un restyle qui l'omet aplatit un détourage valide. Ne
  s'applique qu'avec EXACTEMENT une référence ayant déjà un canal alpha ; ignoré en silence sinon
  (t2i, JPEG aplati, deux références).
- [MÉTHODE] Vérifier l'alpha sur le fichier téléchargé : `Image.open(p).getchannel("A").getextrema()`
  doit commencer à 0 ; pas de canal A = aplati.
- [PROMPT] Texte (Pro) : citer les chaînes exactes, position + rang de taille, peu d'éléments à une
  ou deux tailles ; lettres DESSINÉES, pas composées → paragraphes et petits labels deviennent des
  formes ; copie au-delà (dates de tournée, crédits) → compositing dès le départ.
- [MÉTHODE] Mot déformé : épeler lettre par lettre après la chaîne citée au re-run ; s'il résiste →
  post-production.
- [PROMPT] Échange de copie sur référence : citer la nouvelle chaîne, épingler la position, exiger
  police/taille/couleur d'origine, tout le reste inchangé.
- [PARAM] Layerize : base + jusqu'à 16 calques PNG transparents, fond reconstruit derrière.
  Prompt vide = découpe auto ; liste énumérée (« headline, product, shadow, background ») >
  « all layers » ; `<bbox>x1 y1 x2 y2</bbox>` sur grille 0–1000, origine haut-gauche, pour
  confiner.
- [COÛT] Layerize : coût plat par run (pas par calque) côté Scenario ; poser `size` explicitement
  (auto hérite du palier source, qui bouge le prix).
- [PIÈGE] Calques rognés à leurs propres bornes avec bbox + z-index, pas alignés sur la toile ; pas
  d'export PSD.

**Correspondance Deepotus.** `seedream-5-pro` (t2i + edit, `image_size` preset). Pricing a déjà
`seedream_layerize_usd_calque` (fal **facture par calque** : 0,03375 $ < 1536², contrairement au
coût plat Scenario) et `seedream_edit_usd` (v4/edit, 3D). Manques modèles : **5.0 Lite**, **5.0
Flash**, **4.5** (probablement sur fal), Layerize Flash. Manques paramètres : taille pixel exacte
(672–3136 pas 16 ; Deepotus envoie un preset) ; mode séquence ; `background` transparent (Flash) ;
`optimizePromptMode` ; référence au-delà de 9.

**Propre à Scenario.** Ids `model_bytedance-*`, CU : non transposables.

---

## 10. scenario-image-editing (modèles outils : effets, upscale, recadrage, détourage)

**Résumé.** Retouche d'une image existante par modèles outils (un fichier, quelques curseurs, pas
de prompt) : 18 effets, upscalers, extension de toile, redimensionnement, découpe, calques,
détourage, vectorisation.

**Faits**
- [PARAM] 18 effets à forme commune (`image` + 1 à 3 curseurs) : flou, aberration chromatique,
  correction colorimétrique, cristallisation, cubisme, désaturation, dissolve, dodge & burn,
  glow/bloom, grain, LUT 3D, oilify, parabolize, postérisation, netteté, solarisation, teinte,
  vignette.
- [PARAM] Plages propres à chaque outil : `posterizeThreshold` 0–1 (défaut 0,5) ; Color Correction
  température/contraste/saturation −100 à 100, `gamma` 0,2–2,2.
- [PIÈGE] Grain : profil enum de 22 valeurs (des LOOKS, pas des intensités, certains adoucissent) ;
  `grainColorTemp` 2000–10000, défaut 6500 PAS neutre : réchauffe et relève les noirs plus qu'une
  LUT discrète → le grain re-étalonne en douce.
- [PIÈGE] Défauts incohérents : Color Correction sans réglage = image inchangée mais facturée ;
  LUT et Posterize appliquent un défaut visible.
- [PIÈGE] `lutStyle` : 140+ chaînes exactes (une avec espace : `cgc_look_teal and orange`) ;
  `cgc_log_to_rec709_*` attend du log et sur-contraste un rendu normal ; LUT non réglée = défaut
  `teal_orange`, pas neutre.
- [PARAM] LUT discrète : `lutIntensity` ≈ 0,6.
- [MÉTHODE] Ordre du pipeline : remodeler/upscaler d'abord, puis étalonner, puis texture. Grain et
  netteté EN DERNIER, à la résolution de livraison (un resize ultérieur les efface) ; la LUT tolère
  la résolution.
- [COÛT] Effets à prix plat quelle que soit la taille ; upscale = prix selon pixels de sortie.
- [CHOIX] Upscale fidèle (Topaz, Recraft Crisp) quand il faut rester « on-model » ; créatif
  (Magnific Creative, Clarity) invente du détail et peut redessiner les traits fins → comparer à la
  source. Facteurs 2× à 16×, plafonds 4K–8K typiques.
- [CHOIX] Variantes dédiées pour textures raccordables (coutures) et panoramas 360 (continuité).
- [PARAM] Reframe (Gemini) : enum de ratio + palier 1K/2K/4K, prompt optionnel ; l'enum est
  approximatif (4:5 → 1856×2304 = 29:36) → resize `cover` derrière.
- [PARAM] Smart Reframe : largeur/hauteur exactes, protège texte, logos, palette ;
  `textDensity: DENSE` bien plus cher.
- [PARAM] Photoroom Expand : `outputWidth`/`outputHeight` exacts jusqu'à 4096 + seed. Photoroom
  Uncrop : reconstruit un sujet coupé par le bord.
- [MÉTHODE] Les reframes RE-RENDENT (recomposition générative, des dizaines de fois le prix d'un
  effet) : recadrer AVANT d'étalonner, sinon l'étalonnage revient réinterprété.
- [PIÈGE] Découper en tuiles ou extraire des calques AVANT d'étalonner → un run par morceau.
- [PIÈGE] Les effets lisent des nombres seulement : prompter « plus postérisé » ne fait rien.
- [PIÈGE] Un SVG vectorisé téléchargé par le chemin raster revient rastérisé : récupérer le
  fichier stocké.
- [CHOIX] Suppression de filigrane / texte incrusté : outil dédié (Photoroom Text Remover) plutôt
  qu'éditeur général.

**Correspondance Deepotus.** Hors ids génératifs ; touche le Photolab (photocraft local : effets,
LUT, grain), l'upscale fal (esrgan au pricing), le détourage (rembg local, bria, birefnet,
ideogram-rmbg, SAM 3), qwen-image-layered + seedream layerize (calques), recraft vecteur. Manques
modèles : upscalers fidèles/créatifs nommés (Topaz, Recraft Crisp, Clarity — plusieurs sur fal),
reframe/expand génératif (Bria expand, Ideogram reframe probablement sur fal), text remover.
Manques paramètres : ordre de pipeline non imposé.

**Propre à Scenario.** `model_scenario-*` (LUT, resize, slicer, grid-maker, reframe), prix plat
1 CU, `jobs_wait` : non transposables ; Deepotus fait ces effets en local.

---

## 11. scenario-multi-reference (une image, plusieurs références à un seul rôle)

**Résumé.** Composer une image à partir de 4–5 références, chacune prêtant UNE chose (sujet, lieu,
pose, angle, style, lumière, palette, matière, expression, tenue, inspiration, mise en page) ;
corriger les fuites. Fait sur GPT Image 2.5 Sunburst (cartes et images) + Seedance 2.5 (films).

**Faits**
- [PROMPT] Gabarit : une phrase nommant le médium ; « Each reference picture has exactly one
  job: » ; puis une ligne par image « Image N (<ce qu'elle montre>) = <JOB> only. <ce qu'elle
  prête, concrètement>. Do not <ce qu'il faut laisser>. » ; puis cadrage, placement, ambiance,
  règles de texte.
- [PROMPT] Une référence prête TOUT ce qu'elle montre sauf contre-indication : pour chaque image,
  dire ce qu'il NE faut PAS prendre (raton laveur cuisinier en référence de style → le raton entre
  dans la scène).
- [PROMPT] Un seul job par image ; une image gardée mais inutile : « Image 4 = no job: ignore it
  completely. »
- [PROMPT] Un seul sujet principal par run (deux identités = attention divisée → composer
  séparément).
- [PROMPT] Le job le plus susceptible d'être ignoré EN PREMIER (souvent le Style), avec « This is
  the most important job » (scène argile revenue en chrome CG tant que la ligne Style était plus
  bas).
- [PROMPT] Prêter concrètement : « Copy its 3D render look, soft materials, warm bounce light » >
  « use its style ». Palette : nommer la couleur de chaque élément ; « palette only » recolore à
  peine.
- [PROMPT] Arbitrer les conflits : avec une carte Palette, la ligne Style ajoute « do not copy its
  colors » et les couleurs du sujet sont nommées depuis le nuancier ; si cela recolore le produit /
  l'animal de l'utilisateur → demander.
- [PROMPT] « Use only the idea of a gecko … Do not copy the photo's pose, lighting, colors or
  realism » quand la photo sujet ne doit pas survivre littéralement.
- [PROMPT] Texte cité exactement + « No extra words, no duplicate text » ; copie au pixel près →
  overlay.
- [MÉTHODE] Cartes propres : fonds unis, sans enseigne lisible ni logo ; générer une carte
  manquante en t2i, une idée par carte.
- [PARAM] 4–5 cartes tiennent sur les meilleurs membres, jusqu'à 10 sur certains ; non testé
  au-delà de 5. Certains schémas adressent les références par ordre (« Image 1 »), d'autres par
  balises (`@Image1`) ; un slot dédié (référence de style, contrôle de pose) prime sur le tableau.
- [MÉTHODE] Contrôle de fuite par image : son job est-il visible ? autre chose d'elle est-il
  visible ? Pose/Angle : pas de mannequin, pas de bois ; Style : ni sujet ni décor de la
  référence ; Expression : l'humeur a bougé, pas le visage ; Layout : la grille, pas les mots ;
  Palette : aucune couleur hors nuancier. Corriger en resserrant la ligne et relancer, jamais par
  retouche.
- [PIÈGE] Avant de réécrire une ligne pour un job ignoré : vérifier que la référence a bien été
  ENVOYÉE (chaîne nue → perdue en silence).
- [PIÈGE] Logo accidentel : panneaux générés à swooshes rouge/blanc/bleu lus comme une marque de
  soda → image refusée par l'image-to-video puis par l'éditeur. Dire ce que montrent les panneaux
  (vagues, nuages, grues).
- [PIÈGE] Référence contenant de vraies enseignes → refusée ; régénérer la carte « invented, blank
  signs, no logos ». Design protégé nommé (chaise célèbre) → refus : décrire un design original.
- [PIÈGE] Robe translucide refusée par le filtre ; « opaque, fully covered, high-necked » passe.
- [MÉTHODE] Animer le résultat : l'image sert de 1re frame ; le prompt vidéo ne porte AUCUN job,
  seulement mouvement, caméra, son (l'image contient déjà tout). Dérive (guitare qui change de
  couleur) → « almost static », lister ce qui ne doit pas changer, ne bouger que ce qui doit.
- [PARAM] Films de l'exploration : 6 s, 720p, son activé (Seedance 2.5).
- [MÉTHODE] 8 prompts gardés (claymation, pub sneaker, ukiyo-e, éditorial mode, pixel art 16-bit,
  tilt-shift, riso) = patrons par médium réutilisables tels quels dans une fiche
  (references/prompt-patterns.md).

**Correspondance Deepotus.** Tous les ids à références multiples : `nano-banana(-pro, -2.1)`
(liste ≤ 9), `seedream-5-pro`, `qwen-image-3`, `ideogram-4.5` (source + référence), `flux-3` ?
(multi False). Particulièrement **gpt-image-2.5-sunburst** — mais la voie fal Deepotus n'envoie
qu'UNE image en edit : la technique est impossible sur l'id utilisé par l'exploration. Côté vidéo :
`seedance-2.5` (6 s, 720p, audio). Manques paramètres : références multiples GPT ; slot de
référence de style dédié.

**Propre à Scenario.** `recommend features=["referenceImages"]`, `asset_get
metadata.referenceImages`, devis CU : non transposables (le contrôle « référence bien consommée »
se fait côté Deepotus en relisant la requête envoyée).

---

## 12. scenario-consistency (tenir un même look)

**Résumé.** Tenir un personnage / produit / style sur un jeu d'images ou en vidéo : prompt base +
delta, références, référence de style, carte de contrôle, référence-vers-vidéo, seed,
entraînement.

**Faits**
- [MÉTHODE] Durabilité croissante : prompt de base → images de référence → référence de style →
  carte de contrôle → modèle entraîné. Le seed ne résout pas la cohérence.
- [MÉTHODE] Méthode officielle : générer UNE référence forte, la passer en entrée de chaque scène,
  préférer les modèles à plus de slots de référence.
- [PROMPT] Base + delta : écrire tout ce qui ne change PAS, puis le seul changement dans une
  clause finale ; prompt identique à l'octet entre runs, seule la clause finale bouge.
- [PROMPT] Énumérer : géométrie du sujet, hauteur et angle caméra, taille et position dans le
  cadre, direction de la lumière, chaque sous-élément nommé et sa place, palette en noms ou hex,
  texte incrusté. Regarder la base d'abord (on n'énumère pas une teinte qu'on n'a pas vue).
- [MÉTHODE] Changement que TOUS les éléments doivent porter (nouvelle tenue, coupe) = base, pas
  delta : le faire une fois sur le héros, valider comme nouveau héros, ancrer le jeu dessus.
- [PIÈGE] Un `image` scalaire + `strength` = img2img, pas un slot de référence : ancre aussi la
  composition ; à la force par défaut, un fond uni écrase un delta de scène entière → un jeu de
  scènes exige un vrai champ de références.
- [MÉTHODE] Compléter les slots avec des plans validés « on-model » (collection).
- [PARAM] Certains membres « style reference » créent un style réutilisable au 1er run (id dans
  les métadonnées de sortie) passé ensuite en `styleId` à la place des images (exclusifs ;
  `styleMatch` precise/flexible ; 1 à 10 images) ; le 1er run doit porter les images.
- [PARAM] Champs palette RGB (`colors`) = préférences, pas contraintes : garder les hex dans le
  prompt aussi.
- [PIÈGE] Style ref = rendu, palette, trait ; PAS un personnage → l'associer à une référence de
  sujet.
- [PARAM] ControlNet : modalités `canny`, `tile`, `depth`, `blur`, `pose`, `gray`, `low-quality` ;
  `controlStrength` défaut 0,7, bande 0,3–0,8 ; ≈ 0,7 pour canny/depth/tile, 0,8–0,9 pour
  pose/gray/blur, rigide au-dessus de 0,9 ; `controlEnd` ≈ 0,65 verrouille la composition tôt puis
  laisse le prompt affiner.
- [PIÈGE] Ne jamais extraire la carte de contrôle pour l'attribut qui EST le delta (une carte de
  pose du héros verrouille la pose qu'on veut changer).
- [PARAM] Référence-vers-vidéo : tableau de références « 7 to 9 slots » sur les meilleurs membres
  (un facture au-delà de 4) ; `referenceVideo(s)` pour copier un mouvement, 3 à 15 s, parfois
  facturé à la seconde.
- [COÛT] Prouver l'identité au tirage le moins cher qui montre toute l'action : plus basse
  résolution À LA DURÉE DE LIVRAISON (un clip court cache la dérive tardive) ; « 80 CU against
  130 at the defaults ». Un tirage de preuve valide la recette, pas le rendu final.
- [PIÈGE] `image` (1re frame) et tableaux de références souvent exclusifs : un run à références
  démarre libre ; épingler la 1re frame = autre membre.
- [PIÈGE] Ne jamais passer la planche de turnaround en slot : la vidéo anime la grille ; slots =
  plans individuels propres (pose neutre, sans accessoires de scène).
- [PROMPT] Vidéo à références : prompter l'ACTION, pas l'apparence ; re-décrire le personnage
  combat les images. Adresser par ordre (« Image 1 turns toward the camera, moving as in Video
  1 ») selon la famille.
- [MÉTHODE] Contrôle de dérive vidéo : extraire ≈ 2 images/s (pas de `frameInterval` = fps/2
  arrondi, 12 à 24 i/s) ; un défaut apparu à 11,0 s passait un contrôle à 10,5 s. Juger chaque
  frame par sous-élément : gagné/perdu/recoloré/déformé = dérive ; une partie qui bouge avec
  l'action = animation.
- [CHOIX] Entraîner quand un personnage revient sur des centaines d'images, quand 4+ identités
  partagent des scènes, ou quand chaque run exige le même style ; un modèle par personnage + un
  pour le style (un seul modèle dérive sur ce qu'il a le moins vu).
- [MÉTHODE] Scènes multi-personnages : générer chaque identité seule contre sa base, puis
  composer par edit.
- [PIÈGE] Sprites/frames d'animation par génération image frame à frame : dérive de proportions →
  passer par la vidéo.
- [PIÈGE] Seed pour faire correspondre deux prompts : ne transfère rien ; « same as before » :
  aucune mémoire ; chaîner sortie → sortie : la dérive se cumule → ancrer chaque élément au même
  héros validé.

**Correspondance Deepotus.** Atelier DA (planches, chaînage d'identité par edit — le docstring
d'image_providers.py fait exactement le « chaînage » que la skill déconseille pour un JEU), mémoire
« Teaser CHARGE cohérence personnages ». Ids : tous les edit image ; vidéo à références
(`seedance-2*`, `kling-v3/v4`, `veo-3.1`, `wan-3.0`). `flux` est le seul seed. Manques
paramètres : ControlNet (aucun id ne l'expose) ; référence de style dédiée / `styleId` ;
`referenceVideo` (à vérifier côté lot vidéo).

**Propre à Scenario.** `asset_detect`, collections, `model_scenario-video-to-image-seq`,
entraînement LoRA Scenario, `job_get verbose` : non transposables.

---

## 13. scenario-product-shots (photo produit fidèle)

**Résumé.** Packshots, scènes lifestyle, héros, déclinaisons à partir d'une VRAIE photo produit,
étiquette/logo/forme exacts, contrôle qualité bloquant.

**Faits**
- [MÉTHODE] Le produit n'est jamais généré depuis un texte : partir de la photo réelle ; la
  fidélité est une porte, pas un espoir.
- [MÉTHODE] Deux voies : outils packshot déterministes (détourage, fond, ombre, relight) ;
  placement génératif par éditeur à instruction.
- [MÉTHODE] Inventaire unique de la source (texte d'étiquette, géométrie, matières, couleurs),
  réutilisé à chaque contrôle.
- [PROMPT] Preserve-first : « The exact can from the reference image, proportions and colors
  unchanged, the label reads 'SUMMIT COLD BREW', no other text, standing on a wet slate counter,
  morning side light, shallow depth of field. » Nommer placement, surface, lumière.
- [PIÈGE] « label unchanged » seul laisse la typo au hasard : citer la copie existante de
  l'étiquette (texte déjà présent seulement) et la relire lettre par lettre.
- [PROMPT] Ombres et reflets font le réalisme ; un détourage collé sans ombre flotte → outil qui
  reconstruit l'ombre, ou la nommer (« soft contact shadow falling right »).
- [MÉTHODE] Contrôle : lecture lettre par lettre ; étiquette dérivée = échec → relancer depuis la
  SOURCE avec clause resserrée (copie épelée, « no other text »), jamais depuis la sortie dérivée.
  Texte illisible à la résolution de sortie = non vérifié : upscaler et recontrôler, ou le
  signaler.
- [MÉTHODE] Une scène par run ; « même scène, 4 angles » = 4 runs.
- [PIÈGE] Source = capture d'écran d'un recadrage → fidélité plafonnée ; demander l'original.
- [PIÈGE] Prix, promesses, promo promptés dans l'image → overlay (réglementation et langues
  changent plus vite que les plans).
- [PIÈGE] Détourer et perdre l'ombre réelle : restager avec ombre.
- [PARAM] Packshot : fond hex de marque, marges selon la spec de la place de marché (à confirmer).
- [CHOIX] Relight avec verrou de couleur de marque ; upscalers « produit » pour les gardés.

**Correspondance Deepotus.** Edit image : `gpt-image-2.5-*` (meilleur sur produit photoréel selon
le banc Ideogram), `nano-banana-pro`, `seedream-5-pro`, `ideogram-4.5` ; détourage (rembg, bria,
ideogram-rmbg). Manques modèles : outil packshot (cutout + staging + ombre, ex. Bria/Photoroom
sur fal probable), relight (IC-Light sur fal probable). Manques paramètres : aucun contrôle
automatique « relecture d'étiquette » (vision) dans Deepotus.

**Propre à Scenario.** `asset_analyze`, `text_inputs`, collections, `recommend next_step` : non
transposables (le contrôle par vision se transpose via Claude/OpenAI vision de Deepotus).

---

## 14. scenario-text-overlay (texte exact composité)

**Résumé.** Le texte qui doit être exact (accroches, CTA, prix, mentions légales, lower thirds,
cartons de fin) est rendu de façon déterministe en PNG transparent puis composité sur
l'image/vidéo. Payload JSON + Mustache strict.

**Faits**
- [CHOIX] Les modèles dérivent sur la typo (et d'une frame à l'autre en vidéo) : tout texte exact
  → overlay, jamais généré.
- [PARAM] Deux types : calque texte (`text_template`) ou calque riche HTML/CSS (`html_template` :
  dégradés, contours, ombres, cartes), jamais les deux.
- [PARAM] Calque texte : `font_family` (Google Fonts) OU `font_url` (ttf/otf/woff/woff2), jamais
  les deux ; `font_weight` 100–900 ; `size` 4–2048 px ; `color` #RRGGBB ; `align` ;
  `bbox` exactement une boîte dans la toile ; `line_height` 0,5–4,0 (1,2) ; `letter_spacing` ;
  `overflow` wrap/clip/shrink.
- [PARAM] Toile 1 à 8192 px par côté ; riche : `device_scale_factor` 0,5–4,0 (2,0 pour net
  rétina).
- [PIÈGE] `overflow: wrap` avec une boîte stricte → le texte déborde en bas ; utiliser `shrink`
  (tient ou échoue bruyamment) ou `clip`.
- [PIÈGE] Mustache strict : variable manquante = échec ; `{{var}}` échappe le HTML (`&`, `<`, `>`
  rendus en entités) → `{{{var}}}` pour le brut ; dans les sections, pas de contrôle strict.
- [MÉTHODE] Toute chaîne variable dans `variables` (localisation = éditer une valeur, jamais un
  nouveau gabarit) ; payload embarqué dans le PNG (chunk tEXt) → reproductible depuis le fichier.
- [PROMPT] Brief de l'image/vidéo de fond : réserver la zone du carton calme et SANS texte (tiers
  droit sombre, bande haute vide) pendant toute la durée du carton.
- [PARAM] Toile à la résolution de destination (compositing 1:1, sans flou de mise à l'échelle).
- [PIÈGE] Polices et images en URL distantes → rendu dépendant du réseau ; les inliner en data:.
- [MÉTHODE] Vérifier le PNG aplati sur un fond contrasté (texte clair sur transparent = aperçu
  blanc).
- [CHOIX] Choix de police selon le sens : sans condensée grasse = crie (accroche, prix, CTA) ;
  sans géométrique/grotesque légère = neutre et premium (mentions, lower thirds) ; serif =
  éditorial/patrimoine ; arrondie = amical. Une famille par carton, hiérarchie par graisse et
  taille ; juger à la taille de destination.

**Correspondance Deepotus.** Pas un modèle : concerne Templates (masques + texte, t74), Montage
(titres), Card Forge, Vectorlab. Transposable comme RÈGLE d'agent (« ne jamais prompter un prix ou
une mention légale ; passer par le calque texte »). Manques paramètres : aucun.

**Propre à Scenario.** `model_scenario-compose-image/-video`, `upload_asset`, `asset_update` :
non transposables (Deepotus compose localement, ffmpeg/Pillow — l'inverse de la règle Scenario).

---

## 15. scenario-brand-kit (identité visuelle)

**Résumé.** Identité décidée puis rendue : spec (palette, typo, règles) avant tout run, logo
généré UNE fois en vrai SVG, variantes par édition des fills, applications qui référencent la
marque approuvée, planche.

**Faits**
- [MÉTHODE] Spec d'abord : 4 à 6 hex avec rôle (primary, ink, paper, accent), l'accent sur chaque
  asset (un 2e accent = aucun) ; 2 familles de police avec graisses et rôles ; une ligne de voix ;
  zone de protection et taille mini du logo ; 3 règles « jamais » (étirer, recolorer hors palette,
  composer le wordmark dans une autre police).
- [PROMPT] Les prompts citent les hex de la spec VERBATIM ; couleurs non nommées dérivent chaudes
  ou froides selon le run.
- [PROMPT] Logo vectoriel : le prompt doit exiger « a real editable SVG and not a raster » (c'est
  cette clause qui oriente vers le générateur vectoriel).
- [PROMPT] Une idée sur ce que fait la marque, réduite jusqu'à se lire en une couleur à taille de
  favicon : géométrie plate et fermée, peu de couleurs, hex de la spec, nom pour le wordmark ; dire
  quoi éviter (dégradé mesh, étincelles, éclair gratuit, globe) sinon le modèle prend ses défauts.
- [MÉTHODE] 3 candidats, chacun sur une MÉTHODE de construction différente (≤ 2 combinées) :
  monogramme fusionné à la métaphore, verbe du produit en symbole, deux idées en une, espace
  négatif à double lecture, géométrie sur grille → couvrir un axe plutôt que re-tirer une idée.
- [COÛT] Tour des candidats en mode « coût » (2 sur 3 seront jetés).
- [MÉTHODE] Contrôle : nom lu lettre par lettre, géométrie fermée et centrée, pas de ressemblance
  avec une marque existante ; palette vérifiée en parsant les fills du SVG (pas sur le rendu).
  Échec = relancer avec prompt resserré, jamais retoucher la sortie.
- [MÉTHODE] Variantes (mono, inversé, fond papier) = édition des fills du SVG maître, jamais
  régénération (change aussi la géométrie). Ne jamais upscaler un raster du logo.
- [PIÈGE] Variante identique à l'octet au maître → fusionne avec lui (même id).
- [PROMPT] Applications : une par run, scène subordonnée à la marque, aucun lettrage ni fausse UI
  dans le cadre (« the exact logo from the reference, unaltered, centered on… ») ; marque abîmée →
  même edit avec la marque approuvée comme vérité terrain.
- [MÉTHODE] Icônes : référence de style (rasters de la marque) au 1er icône puis `styleId` sur les
  suivants.
- [MÉTHODE] Planche : chaque calque à largeur/hauteur explicites avec `contain` (fill étire et viole
  « never stretch ») ; toile dimensionnée pour la plus petite légende (1920×1080 → légendes ≈ 10 px)
  ; chaque calque rendu depuis le SVG maître à sa taille ; panneau de construction dessiné depuis
  le SVG, jamais généré.
- [PIÈGE] Une « police » générée est une image de police : le vrai texte se compose (overlay) ; seul
  le wordmark est dessiné une fois puis réutilisé comme artwork.

**Correspondance Deepotus.** `recraft-4.1-vecteur` (SVG, t2i seul — pas de membre « style » à
`styleReferenceImages`), Vectorlab (édition SVG, recolorations), Espaces de marque t200-t211 (kits),
applications via edits GPT/Nano Banana. Manques modèles : **Recraft avec style de référence /
style id** (Recraft v3 « create style » sur fal probable) ; vectorisation d'un raster (Recraft
vectorize sur fal probable). Manques paramètres : `colors` (palette RGB Recraft) non exposé ;
pas de style id persistant.

**Propre à Scenario.** collections, `asset_analyze`, `model_scenario-compose-image`, `curl` de
l'URL stockée : non transposables.

---

## Constats transverses (pour les fiches)

1. **Le palier de qualité est LE levier de coût et Deepotus l'a figé à `high`** (GPT 2.5 ×4,
   GPT 2, Ideogram 4.5). La skill GPT donne un ratio ≈ 1:1,5:6:10:22 (low→max) ; Ideogram 4.5 high
   ≈ 3× medium. Une fiche ne peut pas recommander « brouillon low puis final high » tant que le
   paramètre n'est pas exposé.
2. **Règles de prompt communes à TOUTES les familles** (candidates à un tronc commun de fiche) :
   prose, pas de tags ; texte cité + rôle + place + « no other text / no extra words, no duplicate
   text » ; épeler un mot récalcitrant en repassant l'image gardée ; edit = « change only X » +
   liste de ce qui survit répétée à chaque passe ; une modification par passe ; références à rôle
   par position (ou `<frame>0</frame>` chez Reve) ; négatifs → formulés en positif ; « transparent
   background » prompté = opaque ; ratio dans le champ, jamais en prose (bandes noires).
3. **Contrats divergents par membre** : références (3 Grok, 4–5 Ideogram, 6 Remix, 8–9 Luma,
   10 GPT/Seedream Pro, 14 Gemini/Seedream Lite) ; prompt (2048 → 250 000) ; garde du cadre
   (Ideogram `source` garde la taille exacte, GPT padde de blanc, Grok/MAI suivent la source).
4. **Le texte exact (prix, légal) ne doit jamais être prompté** : overlay — règle absente de
   l'agent Deepotus.
5. **Absence de seed** sur toutes les familles sauf Ideogram V3/Character et Photoroom : la
   cohérence passe par base + delta et référence unique, pas par chaînage sortie→sortie (que
   l'Atelier DA pratique).

## Tableau récapitulatif

| skill | ids Deepotus touchés | nb faits | manques (modèles) | manques (paramètres) |
|---|---|---|---|---|
| scenario-image | tous les ids image | 22 | — | masque, taille pixel exacte + resize, palier résolution, garde du cadre source |
| scenario-gemini-image | nano-banana, nano-banana-pro, nano-banana-2.1 | 17 | Gemini 3.1 Lite (fal probable) | resolution 512–4K, thinkingLevel, Google Search, entrée vidéo, 14 réf. (Deepotus 9) |
| scenario-gpt-image | gpt-image-1, -1-mini, -2, -2-fal, -2.5-flare(-fal), -2.5-sunburst(-fal) | 32 | GPT Image 1.5 (fal probable) | quality low…max (figé high), taille pixel/4K/21:9, mask, multi-réf en edit fal, inputFidelity, transparent direct Sunburst |
| scenario-grok-imagine-image | aucun | 12 | Grok Imagine Image 2.0 / Quality / Image (fal probable pour un membre) | quality, resolution 1k/2k, ratios 20:9–9:20 |
| scenario-ideogram | ideogram-4.5 (+ ideogram rmbg au pricing) | 23 | 4.5 Precise Edit, V3 Transparent, V3 Layerize Text, Character (fal probable) | quality (figé high), magicPrompt off, resolution, aspectRatio source, mask, seed (V3) |
| scenario-luma-image | aucun | 13 | Luma Uni-1 / Uni-1 Max (fal incertain) | webSearch, source vs références |
| scenario-mai-image | aucun | 11 | MAI Image 2.5 / Pro / Edit / Pro Edit (fal inconnu) | — |
| scenario-reve | aucun | 10 | Reve v2.1, Reve Remix (fal probable) | balises `<frame>N</frame>` |
| scenario-seedream | seedream-5-pro (+ layerize, v4 edit au pricing) | 22 | Seedream 5.0 Lite, 5.0 Flash, 4.5, Layerize Flash (fal probable) | taille pixel 672–3136, mode séquence, background transparent (Flash), optimizePromptMode |
| scenario-image-editing | (Photolab local, esrgan, rembg/bria/birefnet/ideogram-rmbg, qwen-layered, seedream layerize, recraft) | 22 | upscalers Topaz/Recraft Crisp/Clarity, reframe/expand génératif, text remover (fal probable) | ordre de pipeline |
| scenario-multi-reference | nano-banana*, seedream-5-pro, qwen-image-3, ideogram-4.5, gpt-image-2.5-sunburst(-fal), seedance-2.5 | 20 | — | multi-réf GPT via fal (1 seule image envoyée), slot style dédié |
| scenario-consistency | tous edits image (Atelier DA), flux (seed), seedance/kling/veo/wan à références | 24 | — | ControlNet, référence de style / styleId, referenceVideo |
| scenario-product-shots | gpt-image-2.5-*, nano-banana-pro, seedream-5-pro, ideogram-4.5, détourages | 13 | outil packshot + ombre, relight (fal probable) | contrôle étiquette par vision |
| scenario-text-overlay | (Templates, Montage, Card Forge — pas de modèle) | 13 | — | — (règle d'agent à ajouter) |
| scenario-brand-kit | recraft-4.1-vecteur, Vectorlab, edits GPT/Nano Banana | 15 | Recraft style de référence / style id, Recraft vectorize (fal probable) | `colors` palette, styleId |
