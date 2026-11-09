# Lot « transverse » — skills Scenario.com (commit b96506d) lus pour les FICHES MODÈLE Deepotus

Lu en entier : scenario (SKILL + references/setup.md + shared-assets.md), scenario-model-comparison,
scenario-moderation, scenario-refine-loop, scenario-quality-gate, scenario-asset-analysis,
scenario-inspiration (SKILL + choose/moodboard/sources/widen), scenario-model-training (SKILL +
base-model-selection + dataset-curation), scenario-identity-library, scenario-video-editing,
scenario-video-assembly, scenario-video-color-grade (SKILL + keying/looks/ops/relight ; scripts
survolés), scenario-caption-studio, scenario-formats (SKILL + placement-specs). En plus, pour la
doctrine de choix de modèle : AGENTS.md § « Models and discovery » et docs/decisions.md du dépôt.

Convention : « Scenario.com » = la plateforme (pour ne pas confondre avec le module Scenario de
Deepotus). Étiquettes : [PROMPT] [PARAM] [PIÈGE] [CHOIX] [COÛT] [MÉTHODE].

---

## 0. Doctrine transverse de choix de modèle (synthèse, sources : scenario, AGENTS.md, decisions.md)

C'est la partie la plus transposable : elle dit COMMENT un agent doit choisir, pas QUEL modèle.

- [CHOIX] Règle d'auteur du dépôt : « Never name a generative model, whoever built it » — les skills
  ne nomment jamais un modèle génératif : la dispo diffère par équipe et « the generation named today
  is superseded within months ». Seuls les OUTILS déterministes maison (compositeur, concat, cut,
  split, resize, grid-maker, LUT, chroma-key…) sont nommés en dur, avec la raison écrite.
  → Pour Deepotus, la transposition n'est PAS « ne rien nommer » (nos fiches doivent nommer nos ids),
  mais : (1) l'agent choisit par CAPACITÉ (« lane ») puis lit la fiche ; (2) une fiche ne fige jamais
  un « gagnant » de façon permanente ; (3) les versions sont des DONNÉES de la fiche famille, pas son
  identité (une fiche par famille : « seedance », pas « seedance-2-5 »).
- [CHOIX] Deux outils de découverte distincts : `recommend` pour une CAPACITÉ (« recommend for a
  capability, search for a name »), `search` pour un nom connu ou un modèle privé. Un `search`
  formulé en capacité échoue : « image edit » a rendu 318 résultats indiscernables.
- [CHOIX] Vocabulaire de capacités (lanes) utilisé partout : txt2img, img2img, txt2video, img2video,
  video2video, audio2video, txt2audio, audio2audio, video2audio, txt23d, img23d, 3d23d, video23d.
  Les tables de lanes portent des capacités, jamais des chaînes de requête.
- [MÉTHODE] Lecture du résultat de `recommend` : lire `next_step.type` AVANT `ranked[0]` :
  `no_match` = arrêter, expliquer `unmet_requirements`, ne jamais relâcher en silence les exigences
  (ni un schéma valide ni un dry_run réussi ne l'annulent) ; `ask_user` = présenter les options ;
  `proceed` = prendre `specialty.model_id`, sinon le premier classé non marqué déprécié (« The
  ranking measures performance, not lifecycle »). Entrée `requires_plan_upgrade` : ne jamais la lancer.
- [MÉTHODE] Toujours le schéma avant le tir (`model_schema_get`) : noms exacts des champs, requis,
  défauts, plafonds ; champs marqués `cost_impact: true` = ceux qui bougent le prix.
- [COÛT] Devis exact avant tir (`dry_run: true`) sauf si l'utilisateur dit que le coût est égal :
  le chiffre de `recommend` est MODÉLISÉ (supposant les défauts) — il a annoncé 48,2 CU pour une
  exécution facturée 55. Coût réel = la ligne de job terminée (`cuCost`).
- [COÛT] Draft puis final, généralisé : générer au palier le moins cher du schéma « on which every
  rubric line can still be judged » (refine-loop) ; un changement de palier est une NOUVELLE
  génération (rejouer la recette du gardien au palier de livraison, ou upscaler le gardien avec un
  upscaler de fidélité). Cas cités dans le dépôt hors lot : Seedance 480p drafts → final 1080p
  (scenario-seedance-drafts), Marble 1.0 Draft → 1.1/1.1 Plus même seed (scenario-3d-worlds),
  Gemini Omni 360p « faster draft tier » (scenario-gemini-omni).
- [PIÈGE] Devis sur une entrée fictive : les fichiers sont résolus avant le devis, donc un
  `dry_run` avec un id d'asset bidon rend 404. Chiffrer une étape future via l'estimation modélisée,
  puis dry_run quand l'asset existe.
- [PIÈGE] `dry_run` chiffre sans VALIDER (assembly, reframe) : un payload peut être chiffré puis
  échouer ou rendre un cadrage faux.
- [PIÈGE] Erreur de transport sur un tir (pas de statut HTTP) : la requête a pu partir ; lister les
  jobs avant de relancer, sinon double facture.
- [PARAM] Dépassement d'un plafond (ex. `max_length` du prompt) = erreur 400, jamais une troncature.
- [PIÈGE] Valeur scalaire là où le schéma dit `array: true` : silencieusement ignorée (la
  référence ou la LoRA n'est pas utilisée). Preuve la moins chère : relire sur la sortie ce que le
  tir a consommé (`metadata.referenceImages`).
- [PIÈGE] Nom de champ fichier deviné : chaque modèle nomme le sien (`image`, `referenceImages`,
  `startImage`, `frontImage`, `video`) — copier le nom du schéma mot pour mot.
- [PIÈGE] Donner une vidéo/un audio/une 3D à un champ image : extraire une image fixe
  (`firstFrame`) quand le modèle veut une image.
- [MÉTHODE] Demande multi-étapes (« vidéo produit avec voix off », « concept → 3D ») : un
  planificateur (`plan_generation`) rend des étapes ordonnées avec outil + indice de modèle, sans rien
  lancer ; une étape unique va à `recommend`.
- [MÉTHODE] Préférences déclarées (« toujours 9:16 ») : mémoire par projet/utilisateur relue avant
  de générer ; l'écriture REMPLACE la couche entière (lire et fusionner d'abord).
- [MÉTHODE] `prompt_spark` : réécriture CONSULTATIVE d'un prompt maigre vers un prompt « on-model »,
  à appeler avec l'id du modèle visé ; à sauter pour un prompt délibéré.
- [COÛT] Jobs échoués remboursés, SAUF générations xAI arrêtées par la modération.
- [MÉTHODE] Les échecs 429 sont classés : concurrence (garder ≤ `actionLimit` jobs en vol), quota
  (le tir est refusé si son prix dépasse le reliquat — un `actionValue` bas veut dire « ce payload
  coûte trop », pas « crédits épuisés »), Relax mode (attente proportionnelle au coût du payload ;
  un payload lourd reste bloqué pendant qu'un moins cher passe). Une relance immédiate du même
  payload ne débloque jamais rien. Inconnu → ne pas inférer le comportement depuis son nom.

### Table capacité → modèle (ce que les skills de ce lot donnent réellement)

Le dépôt refuse par principe une table « capacité → nom de modèle génératif ». Ce que ce lot fournit :

| Capacité / besoin | Ce que dit Scenario.com | Ids Deepotus concernés |
|---|---|---|
| Choisir un modèle pour une capacité | `recommend(capability, prompt=mots de l'utilisateur)` puis schéma + dry_run | tous ; Deepotus n'a que `modeles_video` (liste) |
| Fournisseur bloqué (modération) | prendre le suivant chez un AUTRE fournisseur, même bande de coût (`max_cost_cu` ≈ coût du raté) | voir § moderation |
| Sévérité des filtres | Google (Gemini, Veo) le plus strict ; ByteDance, OpenAI, Ideogram, Hunyuan au milieu ; FLUX et Recraft les plus permissifs | nano-banana*, veo-3.1*, gemini-omni*, lyria* / seedance*, seedream-5-pro, gpt-image-*, ideogram-4.5, hunyuan* / flux*, recraft-4.1-vecteur |
| Base de LoRA (entraînement) | Flux 2 Dev (qualité max, 32B), Flux 2 Klein 9B (défaut production), Klein 4B (vitesse/coût), Z-Image (fidélité perso/style, photoréaliste, texte EN/ZH), Z-Image Turbo (inférence la moins chère, entraîner sur Z-Image), Qwen Image (texte, scènes complexes, sensible aux légendes), Flux 2 Edit / Qwen Edit (paires avant/après), Flux.1 / Kontext = legacy | flux, flux-3, qwen-image-3 (aucun entraînement dans Deepotus) |
| Upscale image | tag `image-upscale`, fidélité vs créatif | à vérifier côté Deepotus (Photolab/Montage) |
| Reframe vidéo génératif | Luma Ray 3.2 Reframe, Wan 2.2 Reframe (prix le plus haut de la chaîne) | wan-3.0 (pas de reframe exposé) |
| Sous-titres / transcription | Caption Studio (Whisper medium par défaut, large-v3) | aucun id |
| Segmentation objet vidéo | SAM (masques objet) ; detection pour cartes ControlNet | SAM 3 objets, matte |
| Étalonnage | LUT préréglée (≈150 `lutStyle`) OU recette locale numpy+ffmpeg → .cube | aucun modèle IA nécessaire |

---

## 1. scenario (skill cœur)

**Résumé.** Connexion au MCP Scenario.com et boucle de génération : scope, découverte (recommend /
search), schéma, devis, tir, attente, affichage/téléchargement, upload, classement en collections,
erreurs. Famille : transverse (toutes capacités : image, vidéo, 3D, audio).

**Faits utiles**
- [CHOIX] `recommend` pour une capacité, `search` pour un nom (voir § 0) ; `recommend` non scopé
  classe des modèles que l'équipe ne peut pas lancer ; redécouvrir les ids à chaque fois.
- [CHOIX] `recommend` peut tourner 30 s, parfois > 1 min : attendre ou rappeler, jamais retomber sur
  `search` pour une capacité.
- [MÉTHODE] Ordre : scope → découverte → schéma → (prompt_spark optionnel) → dry_run → tir → attente
  (jusqu'à 32 jobs par appel d'attente) → affichage → téléchargement.
- [PARAM] Modèle à `runs_as` = `lora` ou `composition` : ne jamais envoyer son id au tir ;
  `run_with.required_arguments` donne le vrai appel (modèle de base + câblage `loras`), à FUSIONNER
  avec ses entrées (« required_arguments alone discards your prompt »).
- [PARAM] `prompt_spark` prend l'id de la LoRA, pas celui de sa base.
- [PARAM] Champs fichier = ids d'asset, même s'ils s'appellent `...Url` ; une URL y est lue comme absente.
- [PIÈGE] Plafond dépassé (`max_length`) → 400, jamais tronqué.
- [PIÈGE] `array: true` reçu en scalaire → ignoré en silence (voir § 0).
- [PIÈGE] Image d'entrée de mauvais type → 400 `Unhandled image format` ; extraire `firstFrame`.
- [PIÈGE] Placeholder d'asset dans un devis → 404 ; chiffrer après création réelle.
- [PIÈGE] Erreur de transport → lister les jobs avant relance (double facture).
- [PIÈGE] `job_cancel` refuse la plupart des générations : prévoir les lots sans chemin d'abandon.
- [COÛT] `dry_run` = prix exact de CE payload ; `recommend` = devis aux valeurs par défaut.
- [COÛT] Échecs remboursés sauf xAI bloqué par modération.
- [COÛT] 429 quota : arrêter le lot, dry_run, proposer un membre moins cher ou moins de sorties.
- [COÛT] Relax mode : l'attente croît avec le coût du payload ; tout job d'un membre de l'équipe
  relance l'attente ; une tentative refusée est gratuite ; ne jamais renvoyer le même payload avant
  `remainingSeconds`.
- [PARAM] Upload : `file_size` préféré ; base64 inline seulement < 100 KB (une chaîne de 57K
  caractères retapée par l'agent s'est corrompue) ; HEIC accepté tel quel.
- [PARAM] Téléchargement : `format` convertit images (png/webp/jpg ; `gif` garde l'animation, `png`
  par défaut l'aplatit) et maillages (glb/fbx/obj) ; jamais de `format` pour vidéo/audio (400).
- [PARAM] `asset_get` gratuit : dimensions, durée, ids `firstFrame`/`lastFrame`.
- [MÉTHODE] Classement = partie de la livraison : collection créée vide puis ajout (lots de 49,
  doublons sautés) ; tags additifs, un doublon de tag = 400 → lire les tags avant.
- [MÉTHODE] (shared-assets) Réutiliser avant de recréer ; une recette/gabarit modifié en géométrie =
  nouvelle version ; reçu local de publication ; « publié » ≠ « uploadé ».
- [MÉTHODE] Préférences utilisateur mémorisées par projet ; relire avant de générer et après
  changement de projet.

**Correspondance Deepotus**
- Ids : tous. L'agent interne n'a que `modeles_video` (liste) → manquent les équivalents de
  `recommend` (capacité + mots de l'utilisateur → classement justifié), `model_schema_get` (plafonds
  par modèle : déjà dans VIDEO_MODELS/FAL_IMAGES), `dry_run` (Deepotus a `pricing.estimate` — c'est un
  devis MODÉLISÉ comme `recommend`, pas un prix exact rendu par le fournisseur), `plan_generation`
  (planificateur multi-étapes), mémoire de préférences (« toujours 9:16 »), `prompt_spark` (réécriture
  consultative par modèle — exactement ce que les fiches modèle doivent nourrir).
- Déjà présent dans Deepotus et aligné : refus AVANT dépense (503 clé manquante, 410 modèle retiré,
  refus « pas d'image de fin »), notes « seed unsupported -> dropped » / « negative_prompt
  unsupported -> dropped » (fal_service.build_fal_args) — équivalent du schéma qui écarte un champ ;
  attention, Deepotus ÉCARTE en note là où Scenario.com renvoie 400 : la fiche doit dire à l'agent de
  ne pas compter sur un champ écarté.
- Paramètres Deepotus non exposés : aucun équivalent de `cost_impact` par champ (savoir quels
  réglages bougent le prix) ; pas de garde « double tir après erreur réseau » visible ; pas de
  `firstFrame`/`lastFrame` gratuits pour chaîner (à vérifier côté Montage).
- Manques modèles : aucun (skill sans modèle nommé).

**Propre à Scenario.com, non transposable** : OAuth/MCP, team_id/project_id, CU, Relax mode,
collections/tags serveur, upload multipart présigné, `asset_display`.

---

## 2. scenario-model-comparison (bake-off)

**Résumé.** Comparer plusieurs modèles sur UN brief inchangé, critères pass/fail écrits avant le
premier tir payant, coût/temps/qualité mesurés côte à côte, livrés en tableau. Famille : transverse
(choix d'un défaut, test d'une nouvelle version contre le titulaire).

**Faits utiles**
- [MÉTHODE] 8 étapes : cadrer (1 brief, entrées, 3 à 5 critères pass/fail) → présélection
  (`recommend` limit ≤ 10 + modèles nommés par l'utilisateur ; garder 3 à 5) → normaliser (schémas)
  → chiffrer (dry_run chacun + outils utilitaires, porte budget) → tirer (tous lancés à la suite,
  `wait=false`, puis une seule attente) → mesurer → juger (planche contact + chaque asset en taille
  réelle) → livrer (une ligne par candidat, assets classés et tagués par id de modèle).
- [PROMPT] Même texte de prompt « byte for byte », mêmes références, même nombre de sorties.
- [PARAM] Épingler le nombre d'échantillons à 1 : un modèle dont le défaut est > 1 multiplie son coût.
- [PARAM] Tailles : prendre la plus proche du cible par modèle et NOTER la taille livrée (plus grand
  = plus cher et plus net, biaise le jugement).
- [PARAM] Couper toute expansion/optimisation de prompt (« compares its rewrite, not the brief ») ;
  si impossible, le dire dans le tableau.
- [PARAM] Seed : ne se compare pas entre modèles ; laisser vide, ou fixe seulement pour répéter un
  même candidat.
- [CHOIX] Turbo et Quality d'une même famille = deux candidats ; une LoRA tourne sur sa base (coût et
  temps de la base).
- [MÉTHODE] Équité : si une famille a un réglage prescrit (syntaxe de référence, curseur de force),
  deux lignes pour ce candidat : défauts ET réglé.
- [PIÈGE] Plafond de prompt trop court pour le brief exact : remplacer le candidat ou demander avant
  de changer le brief pour tous (jamais tronquer pour l'un).
- [COÛT] Porte budget : engagé + devis du prochain appel + réservations vérifiées pour le reste ≤
  plafond, avant CHAQUE appel payant ; si la planche a besoin de sorties pas encore existantes et sans
  borne vérifiée, ne pas lancer : proposer une dépense par étapes. Ne jamais lâcher un candidat en
  silence pour tenir le budget. `usage` = consommé, pas solde.
- [COÛT] Coût facturé = ligne de job ; temps = `updatedAt − createdAt` (file d'attente comprise),
  comparable seulement pour des tirs lancés dans la même minute.
- [MÉTHODE] Vidéo : comparer sur planches contact (extraction de frames), JAMAIS sur la première
  image ; audio et 3D sur l'asset lui-même.
- [MÉTHODE] Critères pass/fail littéraux (« the label text is legible », « no extra fingers ») ;
  une correspondance partielle n'est pas un pass ; preuve ambiguë = « non vérifié ».
- [MÉTHODE] Planche : ordre du tableau `images` = légende (l'outil n'a pas d'étiquettes),
  `columns` = nombre de candidats ; puis chaque sortie en taille réelle (la planche cache texte fin,
  halos, petite anatomie).
- [MÉTHODE] Gros lots : analyse par LLM-vision avec les critères verbatim comme instruction, un
  verdict par critère par image, pré-enregistrée avec les critères.
- [PIÈGE] Un seul échantillon par candidat sur un brief très variable : en faire 2-3 et le dire.
- [PIÈGE] Le gagnant n'est pas une constante : « never write the winning id into a skill or a
  pipeline as a fixed value » ; refaire quand le brief ou le catalogue change.
- [PIÈGE] Livrer la planche : le livrable est le TABLEAU (coût + critères) ; la planche est la preuve.

**Correspondance Deepotus**
- Ids : tous (en pratique image : flux*, nano-banana*, gpt-image-*, seedream-5-pro, ideogram-4.5,
  qwen-image-3 ; vidéo : seedance*, kling*, veo*, h3-max, wan-3.0, pixverse-v6, ltx-2.5-*).
- Manque fonctionnel (pas un modèle) : un OUTIL « bake-off » pour l'agent interne (même prompt, N
  ids, devis cumulé avec plafond, planche, tableau coût/temps/critères). Deepotus a les briques :
  pricing.estimate, Bibliothèque, catalogue_ia.lister.
- Paramètres Deepotus à vérifier/exposer pour l'équité : expansion de prompt (`enable_prompt_expansion`
  / `prompt_optimizer` chez fal, non vus dans les registres dz), nombre d'images (`num_images` :
  présent pour certains, absent pour flux-3/recraft → n appels), taille livrée réelle.

**Non transposable** : `model_scenario-grid-maker`, `jobs_wait`/`job_get` timestamps, collections.

---

## 3. scenario-moderation (refus, contournements légitimes)

**Résumé.** Diagnostiquer un refus : filtre fournisseur, porte IP de l'équipe, plan, liste noire ; le
traiter d'abord comme un problème de ROUTAGE (changer de fournisseur) puis de formulation. Pas un
moyen de produire du contenu interdit. Famille : transverse.

**Faits utiles**
- [MÉTHODE] Lire l'erreur réelle avant de réécrire : 4 échecs se ressemblent et seul le premier est
  une affaire de mots (modération fournisseur / porte IP / 403 plan / liste noire de l'équipe).
- [CHOIX] Filtres côté FOURNISSEUR : « the same prompt usually passes elsewhere in the catalog ».
- [CHOIX] Sévérité : Google (Gemini, Veo) bloque le plus de marques/personnages ; ByteDance, OpenAI,
  Ideogram, Hunyuan au milieu ; FLUX et Recraft les plus permissifs.
- [CHOIX] Prendre l'alternative chez un AUTRE fournisseur : les membres frères partagent le filtre.
  Le classement de recommandation mesure la performance, pas la sévérité du filtre.
- [CHOIX] Coût et sévérité sont indépendants : monter en gamme n'assouplit pas le filtre.
- [MÉTHODE] Alternatives : même capacité que le raté (txt2img / img2img si référence / img2video),
  plafond de coût un peu au-dessus du coût du raté, exclure soi-même le modèle raté.
- [MÉTHODE] Retester avec le prompt INCHANGÉ (le modèle seul varie) ; 2-3 alternatives à coût
  comparable ; si elles passent, le filtre était celui du fournisseur.
- [PROMPT] Trois déclencheurs qui s'additionnent (chacun souvent sous le seuil) : noms/traits de
  personnages reconnaissables (même les vôtres : le filtre ignore qui possède l'IP) ; langage
  d'intensité (« oversized », « huge », « massive » lus comme violence) ; ressemblance à une
  personne réelle (y compris comparaison « built like a heavyweight champion »).
- [PIÈGE] Deux déclencheurs = prompt au seuil : passe une fois, échoue la suivante ; une relance qui
  passe n'a rien réparé.
- [PIÈGE] Un LLM amont qui réécrit les prompts ajoute des intensifs et réintroduit le blocage à
  chaque tir : lui donner les règles 2 et 3 ci-dessous.
- [PROMPT] Récupération, du moins cher au plus cher : (1) changer de fournisseur sans toucher au
  prompt ; (2) décrire l'échelle par PROPORTION (« the blade is about as long as the forearm »)
  plutôt qu'intensité ; (3) retirer les noms reconnaissables et porter l'identité par une IMAGE DE
  RÉFÉRENCE (tient mieux le look de toute façon) ; supprimer les comparaisons à des personnes réelles ;
  (4) contraindre le réécrivain amont.
- [MÉTHODE] Puis STOP : si tous les fournisseurs refusent après une réécriture honnête, le filtre lit
  quelque chose de réel → le dire à l'utilisateur ; « Grinding out variants until one slips through is
  evasion ».
- [COÛT] Vidéo : plusieurs fournisseurs modèrent le RENDU fini → le clip refusé a été rendu en
  entier, et relancer le même payload le re-rend. Lire le coût du raté d'abord.
- [PARAM] Audio de vidéo jugé séparément (`OutputAudioSensitiveContentDetected`) : cause usuelle = un
  instrument ou un genre NOMMÉ, même dans une exclusion (« no music » et « a distant guitar » ont
  échoué ; « room tone, footsteps, a single voice » a passé). Décrire le son diégétique positivement,
  ne rien nommer à exclure ; si pas besoin de son, couper le champ audio (`generateAudio`) au lieu de
  demander le silence par le prompt.
- [COÛT] Blocage de politique généralement remboursé ; échecs remboursés sauf xAI bloqué ; vérifier
  plus tard la facture du jour.
- [PARAM] Porte IP d'équipe (Enterprise) : lit prompt + images d'entrée AVANT le tir (personnages
  fictifs, marques, sosies de célébrités, styles d'artistes, filtres maison) ; coûte 1 CU par
  génération + 1 CU par image d'entrée, même si bloqué ; aucun changement de modèle ne la lève. Un
  logo visible dans une image de référence est lu comme un nom.
- [MÉTHODE] Distinguer les portes : la porte d'équipe nomme un « intellectual-property risk », le
  fournisseur une « content policy violation » ; si ni l'un ni l'autre, un seul essai chez un autre
  fournisseur tranche.
- [PIÈGE] Un avertissement copyright sur une sortie livrée est informatif (asset livré) : revue
  avant usage commercial = décision de l'équipe.
- [PIÈGE] Liste de modèles vide ≠ modération (plan ou liste noire).

**Correspondance Deepotus**
- Ids par sévérité (voir § 0) : stricts = nano-banana, nano-banana-pro, nano-banana-2.1, veo-3.1
  (-fast/-lite, fal et google), gemini-omni-flash(-google), lyria3/lyria-3.5 ; médians = seedance-*,
  seedream-5-pro, gpt-image-* (direct et -fal), ideogram-4.5, hunyuan3d, hunyuan-foley ; permissifs
  = flux, flux-3, flux-3-max, recraft-4.1-vecteur. Non classés par la skill : kling-*, h3-max et
  minimax-music-*, wan-3.0, qwen-image-3, ltx-2.5-*, pixverse-v6, mureka, stable-audio, ElevenLabs,
  Meshy, Rodin, Tripo.
- Fait Deepotus déjà noté dans image_providers.py : « le filtre de sécurité côté OpenAI direct n'est
  pas la porte » sur gpt-image-2-fal → un JUMEAU de voie (direct vs fal) peut avoir un filtre
  différent ; la fiche doit proposer le jumeau comme premier recours, puis un autre fournisseur.
- xAI/Grok : absent de Deepotus (donc l'exception « pas de remboursement » ne s'applique pas).
- Paramètres Deepotus : `generate_audio` / `generate_audio_switch` existent (fal_service) → règle
  « couper l'audio plutôt que prompter le silence » directement applicable ; pas de champ de
  sévérité exposé (`enable_safety_checker`, `safety_tolerance` de certains endpoints fal ne sont pas
  dans les registres dz — à signaler sans les ouvrir par défaut).
- Manque fonctionnel : classification des erreurs de modération dans les refus Deepotus (message
  distinct « filtre du fournisseur X → essayer Y ») et prise en compte du coût d'un rendu refusé.

**Non transposable** : porte IP Enterprise, `teams_list.ipDetectionEnforcement`, listes noires
d'équipe, `scenario-report`.

---

## 4. scenario-refine-loop

**Résumé.** Boucle de QA convergente : rubrique avant de générer, petit lot, verdict écrit par asset,
correctif le moins cher par échec, plafond de tours. Famille : transverse (image surtout).

**Faits utiles**
- [MÉTHODE] Rubrique = lignes pass/fail vérifiables (« subject centered on a plain field »), jamais
  des mots de goût ; écrite AVANT de voir le lot (sinon elle hérite de ses défauts).
- [COÛT] Plus petit lot qui teste la recette, au palier de taille/qualité le moins cher où chaque
  ligne reste jugeable ; dry_run quand le coût compte.
- [MÉTHODE] Critique par LLM-vision, jusqu'à 10 images par appel, une instruction intégrant la
  rubrique et une forme de sortie fixe `<index>: pass|fail, <ligne échouée>`.
- [MÉTHODE] Routage des correctifs, du moins cher : défaut local → inpainting masqué (ou édition par
  instruction nommant UN changement si pas de masque) ; finition uniforme (grade, teinte, recadrage)
  → passe d'outil déterministe, pas de re-tirage ; contenu/composition/palette rendue → éditer la
  clause delta et relancer depuis la base approuvée ; dérive d'identité/style → resserrer
  l'énumération, ajouter/re-rôler des références ; tout échoue → CHANGER DE MODÈLE (redécouverte par
  capacité) en gardant le prompt.
- [MÉTHODE] Une variable par tour (prompt OU références OU modèle).
- [MÉTHODE] Régénérer depuis la base, jamais depuis la dernière tentative (la dérive se cumule).
- [MÉTHODE] Arrêt : un tour propre livre ; trois tours sans tour propre, ou une ligne qui échoue
  deux fois sous deux correctifs différents = rapport, pas re-tirage (« evidence about the model »).
- [COÛT] Palier : un changement de palier est une nouvelle génération (rejouer la recette du gardien
  au palier de livraison puis re-critiquer) OU upscaler le gardien avec un upscaler de fidélité.
- [PIÈGE] Jugements au coup d'œil non enregistrés ; demander au critique de « corriger » (il rend du
  texte) ; re-tirer tout le lot pour un échec ; boucle sans plafond (« failed jobs are reimbursed,
  unsatisfying ones are not »).
- [PIÈGE] Viser « mieux » au lieu du brief converge vers le générique et efface ce qui rendait la
  direction distinctive.

**Correspondance Deepotus** : tous ids image/vidéo. Deepotus a déjà des briques (banc atelier
proportion_qc qui appelle une vraie vision ; Recette) : la boucle et le tableau de routage sont à
mettre dans la doctrine de l'agent interne. Paramètres : masque d'inpainting non exposé sur la
plupart des ids image (nano-banana/gpt-image édition par instruction oui ; gpt-image accepte un masque
alpha — à vérifier dans image_providers) ; aucun upscaler image listé dans ce lot côté dz.
Manques modèles : un upscaler image de fidélité (fal en propose plusieurs, probablement dispo).

**Non transposable** : `asset_analyze` en tant qu'outil serveur, `asset_quality_gate_run`.

---

## 5. scenario-quality-gate

**Résumé.** Outil serveur qui note une image (pass/warn/fail, 0-100, raisons + suggestions), qualité
IA et conformité à un brief de marque configuré ; module Enterprise. Famille : transverse (image).

**Faits utiles**
- [COÛT] Lecture d'un verdict stocké gratuite ; nouvelle analyse facturée (« 1 CU as of this
  writing ») ; un appel « simple » sans verdict stocké se transforme en analyse facturée en silence ;
  `rerun` re-facture et écrase — seulement si le brief ou la sensibilité changent.
- [PARAM] `sensitivity` low/medium/high, ne s'applique qu'aux nouvelles analyses.
- [MÉTHODE] Appliquer TOUTES les suggestions pertinentes en une régénération (pas une par tour).
- [MÉTHODE] Défaut LOCAL sur image approuvée → inpainting ; défaut GLOBAL → régénération.
- [MÉTHODE] Barre de sortie et plafond fixés d'avance (pass, ou score ≥ 90 si nommé ; 3 tours) ; si
  les mêmes classes de défauts reviennent à score inchangé → changer de modèle ou réparer par masque.
- [PIÈGE] C'est un détecteur d'ARTEFACTS, pas de plausibilité : une voiture à deux roues différentes
  a eu 92 et pass. Ajouter un contrôle structurel maison : comptes et attaches (mains, doigts par
  main, membres, roues, chacun attaché à un corps), partie/tout (roue dans un passage de roue,
  reflet sous ce qui le projette), ce qui porte le poids.
- [PIÈGE] Il n'a jamais vu votre référence : comparer soi-même l'asset à sa référence point par point.
- [PIÈGE] Un composite fait la moyenne : une planche de 12 cases a eu 88/pass avec une case
  impossible → découper, noter chaque partie, réparer, recomposer.
- [PIÈGE] Le score bouge peu après réparation (92 avant et après) : relire la liste des défauts, pas
  le nombre.
- [PIÈGE] Image seulement (pas vidéo/3D/audio) ; une ré-upload identique garde son verdict (dédup
  par contenu).

**Correspondance Deepotus** : ids image (tous). Pas d'équivalent serveur ; le principe « artefacts ≠
plausibilité » et la liste de contrôles structurels sont à mettre dans les fiches et dans la critique
vision de Deepotus (proportion_qc). Manques modèles : aucun. Non transposable : add-on Enterprise,
briefs configurés, auto-détection.

---

## 6. scenario-asset-analysis

**Résumé.** Quatre outils d'extraction sur assets finis (légende, description de style réutilisable,
analyse libre, carte de contrôle) + recherche d'assets par texte/similarité/structure. Famille :
transverse (vision, contrôle, recherche).

**Faits utiles**
- [PARAM] Analyse libre : jusqu'à 10 images + 10 textes par appel pour UNE instruction ;
  `num_outputs` (1-5) = plusieurs réponses à la même instruction, PAS une par image.
- [PROMPT] Fixer dans l'instruction une forme de sortie par image (`<index>: pass|fail, <raison en
  moins de 12 mots>`, raison même pour les pass).
- [PARAM] Carte de contrôle (canny, depth, pose, segmentation… 10 modalités) : `remove_background`
  vrai par défaut → mettre faux quand la carte doit couvrir toute l'image.
- [PIÈGE] L'analyse lit un RENDU, pas le fichier : sur un SVG elle a dit « raster », décalé un
  `#101614` en `#131A18` et raté un tracé hors palette → parser le fichier pour couleurs/structure exactes.
- [CHOIX] Outil dédié (légende, description) plus rapide qu'un LLM instruit pour la même tâche.
- [MÉTHODE] La « synthèse promptable » d'une description de style se réinjecte telle quelle dans le
  prompt du lot suivant (tient le look sans entraînement) ; si elle n'est qu'un titre court, prendre
  la description longue.
- [PARAM] Recherche sémantique : ratio 0,5-0,8 pour l'ambiance, 1 = pur sens ; tri ignoré si ratio
  > 0 ; similarité d'image ratio 1 = sujet/ambiance, 0 = traits d'image (quasi-doublons, recadrages) ;
  exemples positifs ET négatifs (`like`/`unlike`).

**Correspondance Deepotus** : Bibliothèque (recherche CLIP t82), Vectorlab (SVG : la règle « parser
le fichier, pas le rendu » s'applique à recraft-4.1-vecteur), SAM 3, rembg/matte. Manques modèles :
préprocesseurs ControlNet (depth/pose/canny — dispo probable sur fal) si Deepotus veut du
conditionnement. Paramètres : pas de `remove_background` côté carte puisque pas de carte ; recherche
négative (`unlike`) absente de la recherche CLIP (à vérifier). Non transposable : outils serveur,
facturation CU.

---

## 7. scenario-inspiration (prime, widen, choose, board)

**Résumé.** Sortir de la réponse moyenne : amorcer (contraintes, axe ouvert, réflexes à exclure),
élargir (4 voies + tirages aléatoires), choisir (3-4 directions mutuellement exclusives), planche.
Famille : direction artistique, toutes images. Contient beaucoup de règles de PROMPT génériques.

**Faits utiles**
- [PROMPT] Adjectifs d'humeur et tags de qualité ne préservent RIEN : « Cinematic », « beautiful »,
  « stylized », « epic », « ultra sharp », « hyper detailed », « crisp », « 8K », « HDR ».
- [PROMPT] Ce qui survit dans un prompt : famille de formes, plage de valeurs, comportement des
  matières, densité de détail et zones de repos, direction et qualité de lumière, palette
  (dominante + secondaire + accent).
- [PROMPT] Cinq axes de mise en scène à nommer, sinon le modèle remplit par sa moyenne : cadrage,
  moment, objectif, heure du jour, lumière. Le défaut non dirigé : sujet centré face caméra, posé,
  éclairé uniformément, tout net, brillance « processed ».
- [PROMPT] Réécrire chaque anti-objectif en état POSITIF (« not cluttered » → « generous negative
  space, one subject centered ») ; une négation va dans `negative_prompt` seulement si le schéma en
  a un ; jamais « no X » dans le prompt.
- [PROMPT] Référence de style jointe → retirer les adjectifs de style du prompt (ils se battent) ;
  référence de structure jointe → le prompt porte style et palette, ne redit pas la mise en page ;
  sans référence → le prompt porte tous les axes.
- [PARAM] Réduire une planche à 3 à 6 références, chacune avec un rôle (style / structure / sujet) ;
  « Handing a model an 18-image board » est une erreur.
- [PIÈGE] Une référence de style ne peut imposer ni hex exact, ni typographie, ni placement d'objet,
  ni identité → couleurs par paramètre couleur si le schéma en a, texte/logo par compositing.
- [PIÈGE] Mélanger deux mondes de lumière (flash dur + fenêtre douce) : ils s'annulent à la génération.
- [PIÈGE] Nommer un artiste vivant = risque de droits ET de modération : nommer les attributs (épaisseur
  de trait, relation de palette, traitement des bords, structure de valeurs).
- [PIÈGE] Ne jamais chercher/nommer une marque qu'on veut évoquer : on obtient une contrefaçon.
- [MÉTHODE] Paire d'anti-référence : même sujet non dirigé (prompt dépouillé des adjectifs) puis
  dirigé (mêmes mots + axes nommés + grade), même seed si le schéma l'expose → montre la règle.
- [MÉTHODE] Randomiser l'OPÉRATEUR, jamais le sujet ; opérateurs : inversion de contrainte, injection
  de contrainte, bisociation, blend, fonction plutôt que surface, n-ième association, cross-brief.
- [MÉTHODE] Se demander une distribution (5-10 candidats avec probabilité estimée), écarter la tête,
  travailler la queue (Verbalized Sampling) ; ne jamais présenter ces chiffres comme mesures.
- [MÉTHODE] Choix : 2 options si l'utilisateur hésite déjà entre deux, 3-4 par défaut, 5 sur demande ;
  pas de leurres ; nommer l'axe avant les options ; libellés parallèles ; montrer les rejets ; issue de
  secours ; demander le choix puis la raison (facultative, avec poignées : lumière, palette, cadrage,
  sujet) ; « je n'arrive pas à choisir » = options trop proches.
- [MÉTHODE] Une fois le look juste, écrire la RECETTE : seed, prompt avec valeurs de slots, jeu de
  paramètres, ids de références.
- [MÉTHODE] Juger un lot sur 4 axes (silhouette, palette, matières, densité) + lisible en niveaux de
  gris, à distance, en mouvement ; une variable à la fois.
- [MÉTHODE] Sources web légitimes listées (Are.na, Met, Openverse, Cleveland, Wikimedia, AIC) ;
  Pinterest interdit aux agents (robots.txt) → demander à l'utilisateur.

**Correspondance Deepotus** : tous ids image et vidéo (règles de prompt génériques à mettre en tronc
commun des fiches). Concorde avec la skill Deepotus vitrail-mloda-polska (« jamais de nom
d'artiste »). Paramètres : `negative_prompt` exposé seulement où `negatif` est vrai (fal_service) —
la fiche doit dire où il existe ; références multiples (rôles style/structure/sujet) : à vérifier
par modèle image (nano-banana, seedream, gpt-image acceptent plusieurs images). Manques modèles :
aucun. Non transposable : `search` public avec `metadata.prompt`, collections, wildcard.py (outil
local transposable mais hors sujet fiches).

---

## 8. scenario-model-training (LoRA, clonage de voix)

**Résumé.** Entraîner un modèle perso quand un look doit tenir sur beaucoup d'assets et que les
références ne suffisent plus ; choix de la base, curation du jeu, epochs, devis. Famille : image
(LoRA) + voix.

**Faits utiles**
- [CHOIX] D'abord le test par références (style refs ou héros en sujet) : il a égalé une LoRA sur
  le même brief à prix par image comparable, pour le coût d'une génération ; entraîner seulement si
  ce test dérive sur l'ensemble. Pas d'entraînement pour un one-off ; chercher d'abord une LoRA publique.
- [CHOIX] La base est le choix irréversible : elle fixe plafond de qualité, vitesse et coût de TOUTES
  les futures générations ; « training is a one-time cost, inference is forever ».
- [CHOIX] Cheat sheet familles (voir § 0) : Flux 2 Dev (32B, détail et adhérence max, plus cher) ;
  Flux 2 Klein 9B (« strong default for production volume ») ; Klein 4B (quasi temps réel, moins
  cher) ; Z-Image (forte fidélité perso/style à bas coût, photoréaliste, texte EN/ZH) ; Z-Image Turbo
  (inférence la moins chère, fidélité d'entraînement moindre : entraîner sur Z-Image, la LoRA se
  transporte sur les variantes Z-Image — seule famille portable) ; Qwen Image (texte : panneaux, UI,
  HUD ; scènes complexes ; sensible aux légendes) ; Flux 2 Edit / Qwen Edit (paires avant/après ;
  Qwen Edit préfère « replace X with Y ») ; Flux.1 / Flux Kontext = legacy.
- [PIÈGE] Erreur `size mismatch`/`weight dimension` à la génération = mauvaise variante de base, pas
  un entraînement raté.
- [PARAM] Jeu : 5-15 images (styles jusqu'à ~20) ; ≥ 1024 px par côté ; un 12 ciblé bat 40 mélangés.
  Par type : personnage 5-15 (≥ 3 poses, angles variés, fonds variés, un seul perso) ; style 10-20
  (un seul style, sujets variés) ; multi-perso 8-15 ; objet 5-15 ; environnement 5-15 ; texture 10-15
  (lumière neutre) ; paires d'édition 5-15 paires.
- [PIÈGE] Jeu dérivé d'UNE image source (20 rendus du même visage) : le modèle apprend le rendu, et
  reproduit un même mauvais visage cohérent qui colle aux légendes → refaire le jeu, pas les epochs.
- [PROMPT] Légendes : « describe what should vary, never what must stay » ; perso/objet : mot
  déclencheur inventé (`KAEL_07`) en tête de chaque légende puis traits constants puis variables ;
  style : ne JAMAIS nommer le style ; paires : instructions avec un même verbe partout.
- [PARAM] Hyperparamètres selon taille : 5-10 img → lr 5e-5, 15-20 epochs, 20-30 répétitions ;
  10-25 → 1e-4, 10, 15-20 ; 25-50 → 2e-4, 6-8, 10-15.
- [PARAM] `sample_prompts` obligatoires sur un run multi-epoch, sinon un seul epoch final ; plafond
  par famille (8 sur Flux LoRA, 4 sur Flux.2/Qwen/ZImage) ; prompts hors jeu (mot déclencheur + pose
  ou décor nouveaux) ; « the strongest is rarely the last ».
- [COÛT] `epochs` = levier principal, linéaire ; toujours un devis (configure dry_run) avant `start` ;
  `stop` ne rembourse rien.
- [PARAM] Clonage de voix : même parcours, `modality: voice`, jeu `short_audio`/`long_audio`.

**Correspondance Deepotus** : ids touchés flux, flux-3, flux-3-max, qwen-image-3 (et la mention
kontext dans pricing.py) ; eleven_* pour la voix. Deepotus n'a AUCUN entraînement. Manques modèles :
Flux 2 Dev / Klein 9B / Klein 4B, Z-Image / Z-Image Turbo (inférence ET entraîneurs LoRA —
probablement dispo sur fal), Qwen Image Edit + entraîneur, Flux 2 Edit ; clonage de voix instantané
ElevenLabs (clé directe déjà présente). Paramètres non exposés : chargement de LoRA (`loras` /
`lora_scale`) sur les endpoints fal image. Non transposable : `recommend_training`, `model_create`,
`train`, page modèle web, plafonds de plan.

---

## 9. scenario-identity-library

**Résumé.** Cycle d'une identité nommée (personnage, accessoire) : interview → héros validé →
collection nommée `character: <nom>` / `props: <nom>` → planche → réutilisation comme références.
Famille : cohérence image (et vidéo par références).

**Faits utiles**
- [MÉTHODE] Interview avant génération : silhouette/proportions, palette (nom ou hex), 2-3 détails
  signatures, style de rendu, vues nécessaires ; une vue plein pied seule donne trop peu de détail aux
  gros plans → ajouter un gros plan de face et un profil exact.
- [CHOIX] UN seul modèle capable de références pour toute l'identité, choisi avant le premier tir ;
  un modèle sans champ de référence se disqualifie d'emblée ; « A different model per view » = erreur.
- [PROMPT] Héros = vue neutre plein pied sur fond uni, rien hors brief, pas de texte (isole mieux
  l'identité dans un slot de référence).
- [MÉTHODE] N'admettre que des images validées (une seule hors-modèle empoisonne tous les tirages
  suivants) ; vues en « baseline + delta », une génération par vue, chacune taguée par vue.
- [MÉTHODE] Refonte (tenue, coupe, âge) = nouvelle énumération + nouveau héros ; retirer les anciens
  membres sinon une requête nourrit les deux versions.
- [PARAM] Planche = assemblage (grille ≤ 100 images, ordre du tableau = mise en page), jamais
  générée ; sert d'une seule référence quand le modèle manque de slots ; sinon préférer les vues
  individuelles.
- [PIÈGE] Passer la planche comme image d'img2img = verrouillage de composition ; seulement en slot
  de référence.

**Correspondance Deepotus** : ids à références : nano-banana*, gpt-image-*, seedream-5-pro,
flux-3 (?), kling-v3/v4 (éléments), seedance-2.x (références), veo-3.1 (R2V), gemini-omni. Deepotus a
déjà la mémoire « Teaser CHARGE : cohérence des personnages » (edit d'identité, dérive = rejet) et la
Bibliothèque/collections : la convention de nommage et la règle « admission = porte » sont
transposables. Paramètres : nombre max de références par modèle (non porté par les registres dz —
à mettre dans chaque fiche). Manques modèles : aucun. Non transposable : grid-maker serveur, tags/
collections serveur.

---

## 10. scenario-video-editing (outils déterministes vidéo)

**Résumé.** Effets et opérations sur une vidéo existante par outils déterministes (LUT, grain,
chroma key, cut/split/resize/reverse, frames, calques), règle des « jumeaux » image/vidéo, reframe vs
resize, retouche d'une vidéo finie. Famille : post-production vidéo.

**Faits utiles**
- [PARAM] 18 effets image ont leur jumeau vidéo (mêmes réglages, champ `video`) ; LUT = `lutStyle`
  + `lutIntensity` ; Grain = `grainProfile` (22 profils, défaut `kodak_portra_400`).
- [PIÈGE] Les 22 profils de grain sont des LOOKS, pas des intensités ; certains adoucissent l'image.
- [PARAM] Extraction de frames : `extractAllFrames` sinon `frameInterval` (défaut 24 ≈ 1 img/s à
  24 fps) ; vérifier le compte = `nbFrames` ou `nbFrames/frameInterval` ; ordre des frames NON fiable
  (défaut confirmé) → reconstituer par planche contact contre la continuité.
- [PARAM] Chroma key : laisser `keyColor` vide (détection sur les bords) ; `webm` (VP9 alpha, défaut)
  pour web/moteurs, `mov` (ProRes 4444 alpha) pour montage ; `mp4` sans alpha exige une couleur de
  fond ; frange verte → `spillSuppression` (défaut 1, max) + `edgeShrink` 1-2 px ; trous → baisser
  `tolerance` (défaut 0,3) ; bord en escalier → `softness`/`edgeFeather` ; entrée ≤ 60 s.
- [PROMPT] Générer pour incruster : fond vert pur, plat, uniformément éclairé, sans ombre portée,
  sujet sans vert ; flou de mouvement et cheveux fins s'incrustent le plus mal → juger ces frames d'abord.
- [PIÈGE] Une découpe avec transparence ne sort JAMAIS en mp4 (alpha seulement en WebM ou ProRes
  4444 MOV) : convenir du conteneur avant le devis.
- [COÛT] Coût des outils vidéo = suit la DURÉE du clip → couper d'abord, étalonner ensuite.
- [CHOIX] Resize n'est pas reframe : `contain` (défaut), `stretch` (déforme), `cover` (recadre au
  centre) ; garder toute l'image en 16:9 → 9:16 exige un reframe GÉNÉRATIF (Luma Ray 3.2 Reframe, Wan
  2.2 Reframe), de loin le plus cher, ou un compositeur (bandes ou recadrage) bon marché.
- [PIÈGE] Plafonds de résolution des reframes : un schéma peut accepter un ratio vertical et un
  palier haut séparément mais refuser la paire au tir.
- [MÉTHODE] Retoucher une vidéo finie = éditer, pas regénérer : extraire la musique d'abord ; trouver
  les coupes par planche de frames ; split aux temps ; vérifier chaque segment ; concat dans le nouvel
  ordre ; ALLONGER un plan = prolonger depuis sa dernière image avec un modèle vidéo (aucun outil ne
  ralentit) ; changer un plan = regénérer ce plan seul.
- [MÉTHODE] Ordre d'une version courte : couper → redimensionner → étalonner (LUT ≈ 0,6) → grain en
  dernier (dimensionné pour la sortie).
- [PIÈGE] Étalonner chaque clip puis concaténer → les plans dérivent ; étalonner le master une fois.

**Correspondance Deepotus** : Montage, Son & VFX (post-traitement pile t276), matte_service
(rembg/matte, transparence : la règle WebM/ProRes vs mp4 est à vérifier dans les exports Deepotus
— cf. overlays alpha t282), extension depuis la dernière image = tous les ids vidéo à `end_image`/i2v.
Manques modèles : reframe vidéo génératif (Luma Ray Reframe — probablement dispo sur fal ; Wan Reframe
— probable), extension vidéo native (Veo extend, Seedance extend, Wan extend) si non exposée.
Paramètres non exposés : extension/prolongation explicite, reframe. Non transposable : ids
`model_scenario-*`, assets serveur ; Deepotus fait tout cela en ffmpeg local (ce qui est mieux).

---

## 11. scenario-video-assembly

**Résumé.** Monter des clips générés : concat (bout à bout + transitions), compositeur à timeline
absolue (calques image/vidéo/audio), captions en dernier ; contrat des champs. Famille : montage.

**Faits utiles**
- [PARAM] Concat : 2 à 50 clips ; transitions = objets `{type, duration}`, nombre = clips − 1 ;
  18 types (`fade` défaut = fondu enchaîné, `dissolve` différent, `none`) ; 0,1 à 5 s, défaut 0,5.
- [CHOIX] Coupes franches par défaut sauf si le brief demande qu'un plan coule dans le suivant.
- [PIÈGE] Concat a rendu un audio qui DÉRIVE par rapport à l'image (avec et sans transitions, défaut
  confirmé) → vérifier : durée sortie vs somme des entrées (chaque transition raccourcit jusqu'à sa
  durée), longueurs des flux audio et vidéo égales, un repère visible (coupe, bouche, impact) tombe
  sur son son. Dialogue à garder synchro → timeline par calques (chaque clip porte sa piste à son
  `startTime`).
- [PARAM] Compositeur : 1-50 calques, `startTime/endTime` = placement ; `trimStart/trimEnd` =
  QUANTITÉS rasées (jouer les 20 premières s d'une piste de 90 s = `trimEnd: 70`) ; pas de 0,1 s
  (pas de coupe à l'image près) ; au moins un calque vidéo (musique sur image fixe refusée) ; `fps`
  1-120, défaut 30 → le régler sur le `frameRate` mesuré des clips ; `volume` 0-2 et `mute` par calque.
- [PIÈGE] Calque d'overlay sans `width/height` explicites : une bande 560×80 est revenue en 1792×256
  sur un canevas 1920×1080 ; `fit` défaut `fill` étire.
- [PIÈGE] Pas de calque texte : titres, tiers inférieurs, cartons = PNG rendus composités.
- [PARAM] Un modèle vidéo à qui on demande 8 s ne rend pas toujours exactement 8 s → mesurer les
  durées réelles avant de calculer les `startTime`.
- [MÉTHODE] Sous-titrer le master fini, pas chaque clip ; baisser le volume du lit musical plutôt
  que couper le dialogue ; ne pas sous-titrer un master concat avant d'avoir vérifié la synchro.
- [MÉTHODE] Dossier de révision : master propre, sources, payload exact, durées mesurées, texte et
  réglages voix, PNG de titres + réglages, SRT corrigé ; réviser le calque demandé et re-sous-titrer
  depuis le master propre (jamais empiler des sous-titres sur un export brûlé).

**Correspondance Deepotus** : Montage + Chapitres (la mémoire « concat ffmpeg perd l'audio » rejoint
exactement ce défaut de Scenario.com — la règle de vérification est transposable). Ids : tous les
vidéo, en particulier `generated_duration` (fal_service) rejoint « la durée rendue ≠ demandée ».
Manques modèles : aucun. Paramètres : rien à exposer côté modèles. Non transposable : ids
`model_scenario-compose-video/concat`, Video Studio serveur.

---

## 12. scenario-video-color-grade

**Résumé.** Étalonnage/relight déterministe en code (numpy + ffmpeg, LUT .cube 33³), 21 looks
réglés, keying sélectif, appariement à une référence ; option préréglage LUT serveur (~150 styles).
Famille : post-production couleur — AUCUN modèle génératif.

**Faits utiles**
- [CHOIX] Préréglage d'abord si la source est LOG (couvre bien plus de caméras que le `decode_log`
  local, S-Log3 seulement) ou si un look de pellicule est demandé ; recette maison si le look doit
  être réglé/inventé, positionné (masques, relight, vignette, grain, halation), apparié à une
  référence, exporté en .cube, ou monté en showreel.
- [PIÈGE] Le noms des préréglages ne disent pas quelle entrée ils attendent → comparer 2-3 sur une
  image fixe avant la vidéo.
- [PIÈGE] L'outil LUT vidéo serveur a pu rendre du MPEG-4 Part 2 → réencoder en H.264
  (`-crf 18 -pix_fmt yuv420p -movflags +faststart`).
- [MÉTHODE] Test sur image fixe avant toute vidéo (secondes vs minutes) ; deux frames si mouvement ;
  vérifier que le nombre d'images de chaque rendu = source.
- [PARAM] Looks réglés sur source douce et légèrement désaturée ; sur source contrastée réduire
  contraste et saturation d'environ un tiers.
- [PARAM] Plages d'ops : balance +0,05 à +0,35 (chaud) ; contraste 0,15-0,45 normal, 0,75-0,9 dur ;
  levels noir 0,03-0,08 (délavé) ; saturation 0,4 bleach / 0,75 sourd / 1,1-1,35 riche ; split tone
  0,02-0,08 ; nuit américaine −0,9 à −1,5 stops ; vignette PI/6 à PI/3,5 ; grain 4-10 ; relight 0,3 à
  1 stop depuis le côté déjà éclairé.
- [PIÈGE] Le relight change le caractère de la lumière, jamais la géométrie ni les ombres portées ;
  peau sous lumière chaude vire vite à l'orange.
- [PIÈGE] Couleur conservée unique (N&B + rouge) : une clé couleur seule fuit sur peau/lèvres → masque
  objet par segmentation vidéo (une passe par objet, prompt nom court « red leather jacket ») + clé
  DANS le masque ; séparer par luminosité/saturation plutôt que teinte.
- [PIÈGE] Noms de films ou marques de pellicule comme noms de looks publics : noms descriptifs.
- [PIÈGE] `-shortest` avec audio un peu plus court : ffmpeg perd la dernière image, la boucle casse.
- [COÛT] 12 looks sur une boucle de 8 s = 112 CU en tout (2 masques + musique) ; les grades : 0.

**Correspondance Deepotus** : Montage/Son & VFX (post), SAM 3 objets (masques), matte. Directement
transposable en local (Deepotus a ffmpeg ; scripts MIT) : bibliothèque de looks .cube et ops
numériques. Manques modèles : segmentation VIDÉO texte → masque (SAM 2/3 vidéo, probablement dispo
sur fal) si SAM 3 Deepotus n'est qu'image. Non transposable : `lutStyle` serveur.

---

## 13. scenario-caption-studio

**Résumé.** Un outil : vidéo → transcription Whisper (ou SRT fourni) → sous-titres stylés brûlés,
piste soft et/ou .srt ; 18 langues de traduction, 7 préréglages. Famille : sous-titrage / transcription.

**Faits utiles**
- [PARAM] Trois sorties : brûlé (`video_image`, défaut), piste soft (`video_data`, texte brut sans
  style), `.srt` (`outputSrt`) ; passe SRT seule pour verrouiller les mots d'abord (même prix qu'un
  brûlage : achète de la certitude, pas des économies).
- [CHOIX] Table destination → réglages : short vertical (`tiktok-bouncy`/`word-pop`, karaoke si
  musique ; 3-5 mots par cue, 1 en karaoke ; position `middle`) ; pub (`modern-chip`/
  `minimal-underline` accent marque ; 3-7 mots ; bas ou haut) ; YouTube long (défaut ou
  `cinematic-fade` ; 2 lignes, 84 caractères = 2×42 « broadcast convention » ; bas ; SRT) ; ciné
  (`cinematic-fade`, cues de la longueur d'une phrase, ~6 s).
- [PIÈGE] `middle` = centre du cadre = la bouche d'une tête parlante centrée : recadrer le visage au
  tiers supérieur d'abord.
- [PIÈGE] Taille auto ≈ 30 px sur un 1080×1920 (illisible) → `fontSizePx` 60 à 90 en vertical.
- [PIÈGE] `tiktok-bouncy` a mis tout en MAJUSCULES → casse exacte (« LoRA ») via prompt de style ou
  thème, vérifier une image.
- [PARAM] Whisper `modelSize` : `medium` défaut (voix off propre), `large-v3` pour bruit, accents,
  jargon ; `.en` anglais seul ; `cost_impact`.
- [PROMPT] `transcriptionPrompt` = indice d'ORTHOGRAPHE (noms, marques, jargon), pas un champ de
  style ; ne garantit rien (un nom indiqué a été mal écrit deux fois) → vérifier chaque nom requis.
- [MÉTHODE] Si la narration a un script écrit, comparer la transcription au script (mots manquants,
  doublés, altérés) ; les temps des cues viennent de l'enregistrement réel, pas du nombre de mots.
- [PIÈGE] Correction par SRT : passer le TEXTE SRT en base64, pas un id d'asset (sinon succès facturé
  avec 0 sous-titre, `segment_count: 0`).
- [PIÈGE] 1 mot par cue sans préréglage animé = diaporama ; ne jamais finir une cue « pop » sur un mot
  d'une lettre (≈ 70 ms à l'écran).
- [PARAM] Langues CJK : environ un tiers des caractères par ligne des écritures latines.
- [MÉTHODE] Vérifier le rendu : planche à 2 i/s, lire orthographe/casse/placement ; écouter début/fin
  des cues ; échantillonner juste avant/après les frontières ; le dernier mot parlé survit.
- [PIÈGE] Mentions légales/CTA ≠ sous-titres : carton texte composité (formulation et durée verrouillées).

**Correspondance Deepotus** : pas d'id de transcription/sous-titrage dans les registres dz lus
(Dictée existe côté app ; voix eleven_* pour le script de référence). Manques modèles : Whisper /
Wizper (transcription) et un sous-titreur auto (probablement dispo sur fal) ; traduction de
sous-titres (LLM). Paramètres : taille de police, position, segmentation (mots/caractères/durée par
cue), casse — à exposer si Deepotus ajoute le sous-titrage. Non transposable :
`model_scenario-caption-studio`, `themeTsx`.

---

## 14. scenario-formats

**Résumé.** Décliner UN master validé en formats/placements : échelle de décision (resize, cover,
expand, reframe génératif, recomposition native), ordre des opérations, table de specs. Famille :
transverse image/vidéo (ratios, résolutions).

**Faits utiles**
- [CHOIX] Échelle, première marche qui convient : même ratio → resize ; ratio plus serré, bords
  sacrifiables → resize `cover` ; plus de canevas, composition intacte → expand/uncrop ; autre ratio
  recomposé → reframe génératif (variante qui protège le texte si lettrage) ; ratio lointain ou
  nouvelle hiérarchie → RECOMPOSER nativement (nouvelle génération avec le master en référence).
- [CHOIX] « 16:9 key art seldom survives to 9:16 by any amount of outpainting » → chaque ratio de
  livraison = sa propre composition.
- [MÉTHODE] Ordre : master validé sans texte à la plus grande taille → dériver chaque format du
  master (jamais d'un dérivé) → reframe/expand AVANT étalonnage et grain → upscale APRÈS un reframe
  vidéo (il rend à son palier, 1080p max, et jette l'upscale préalable) → mesurer → lettrer en dernier.
- [PIÈGE] Les enums de ratio sont approximatifs : un 4:5 est revenu en 29:36 → mesurer, finir par un
  resize exact.
- [PIÈGE] Re-prompter par format = « five cousins, not five formats » ; dériver du master lettré =
  texte re-rendu.
- [COÛT] Le reframe génératif coûte « tens of times an effect's price » → toujours un devis.
- [PARAM] Specs (valeurs 2026, à confirmer) : IG feed 1080×1080 / 4:5 1080×1350 ; story/reel/TikTok
  1080×1920 ; zone sûre 9:16 : dégager ~14 % haut, 35 % bas, 6-13 % par côté ; vignette YouTube
  1280×720 (badge durée en bas à droite, juger à 1/10) ; bannière YouTube 2560×1440 (bande ≈1546×423) ;
  X 1200×675, en-tête 1500×500 ; LinkedIn/OG 1200×627/630 ; Pinterest 1000×1500 ; icône d'app 1024
  (marque dans 80 % central) ; Steam (header 920×430, main 1232×706, small 462×174, vertical 748×896,
  library 600×900, hero 3840×1240) ; Play 1024×500 ; Amazon 1600² fond blanc pur ~85 % sans texte ;
  podcast/pochette 3000² ; print 300 dpi + 3 mm de fond perdu, texte à 5 mm de la coupe ; bannières
  IAB 300×250, 728×90, 300×600, 160×600, 320×50, 970×250.
- [PIÈGE] Bannières = ratios lointains sur petits canevas : recomposer, pas reframer.

**Correspondance Deepotus** : ids image à `aspect_ratio`/taille (nano-banana*, gpt-image-*,
seedream-5-pro, flux-3, ideogram-4.5, qwen-image-3) et vidéo à `ratios` (tous) ; façade
`aspect_ratio` #517 ; Campagnes/Scheduler (formats réseaux). La table de specs et la zone sûre 9:16
sont directement utiles aux fiches et à la planification. Manques modèles : outpaint/expand image
(Photoroom Expand, ou équivalents fal — probables), reframe génératif image/vidéo. Paramètres non
exposés : mesure automatique du ratio rendu vs demandé. Non transposable : `model_scenario-smart-
reframe`, `scenario-text-overlay`.

---

## Tableau récapitulatif

| Skill | Ids Deepotus touchés | Nb faits | Manques (modèles) | Manques (paramètres) |
|---|---|---|---|---|
| scenario (cœur) + doctrine § 0 | tous | 40 | — | `cost_impact` par champ ; devis exact fournisseur (Deepotus = modélisé) ; outils agent recommend/schéma/devis/plan/mémoire de préférences ; garde double-tir |
| scenario-model-comparison | tous (image et vidéo surtout) | 20 | — (outil bake-off manquant) | coupure expansion de prompt ; `num_images` uniforme ; taille livrée |
| scenario-moderation | nano-banana*, veo*, gemini-omni*, lyria* / seedance*, seedream, gpt-image*, ideogram, hunyuan* / flux*, recraft | 22 | — | classification d'erreur de modération ; `safety_tolerance`/`enable_safety_checker` fal ; coût d'un rendu refusé |
| scenario-refine-loop | tous image/vidéo | 12 | upscaler image de fidélité (fal, probable) | masque d'inpainting par modèle |
| scenario-quality-gate | ids image | 11 | — | (contrôle structurel maison) |
| scenario-asset-analysis | recherche CLIP, recraft-4.1-vecteur, SAM 3 | 8 | préprocesseurs ControlNet (fal, probable) | recherche négative `unlike` |
| scenario-inspiration | tous image/vidéo | 20 | — | `negative_prompt` par modèle ; rôles des références multiples |
| scenario-model-training | flux*, qwen-image-3, (kontext), eleven_* | 15 | Flux 2 Dev/Klein 9B/4B, Z-Image(+Turbo), Qwen Edit, Flux 2 Edit, entraîneurs LoRA (fal, probables), clonage voix ElevenLabs | chargement `loras`/`lora_scale` |
| scenario-identity-library | nano-banana*, gpt-image*, seedream, kling, seedance-2.x, veo-3.1, gemini-omni | 8 | — | nb max de références par modèle |
| scenario-video-editing | tous vidéo, matte, rembg | 14 | Luma Ray Reframe, Wan Reframe, extensions natives (fal, probables) | reframe, extension, conteneur alpha |
| scenario-video-assembly | tous vidéo | 9 | — | — (vérif. synchro concat) |
| scenario-video-color-grade | SAM 3, matte (post locale) | 12 | segmentation vidéo texte→masque (fal, probable) | — |
| scenario-caption-studio | eleven_* (script de référence) | 15 | Whisper/Wizper, sous-titreur auto (fal, probables) | police, position, segmentation, casse |
| scenario-formats | ids image à ratio, tous vidéo | 10 | expand/outpaint image, reframe génératif | mesure ratio rendu vs demandé |
