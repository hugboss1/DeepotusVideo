# Retours du 26/09 et champs IA — conception (26/09/2026)

Branche `chantier/retours-ia-26-09` depuis `main` = `e0ab545`. Quatre relevés
en lecture seule le 26/09 : rapports résumés ici, scripts de mesure dans le
scratchpad de la session (`avance/`, `inventaire/`). Décisions validées par
l'utilisateur le 26/09 (questions F, G variante, G périmètre, H, pastille).

## 0. Faits mesurés qui bornent la conception

- **Avance d'une image (A).** Mesurée image par image, avec des résultats
  identiques sous ffmpeg 9.0.1 (celui de l'app) et 8.1.1 (celui du PATH).
  Deux causes :
  - **(a)** `fps=` sans `start_time` : la première image après `-ss` a un pts
    local > 0, et `fps` ne comble pas le début. `trim` garde alors 29 images
    sur 30, et `setpts=PTS-STARTPTS` recule tout d'une image. C'est le cas dès
    que `in` ne tombe pas sur la grille du canevas, ou que la source est à
    25 / 29,97 i/s.
  - **(b)** La coupe franche est un `xfade` de 0,04 s (`_XFADE["cut"]`), non
    compensé entre deux plans jointifs. Chaque coupe avance tous les plans
    suivants de 0,04 s, de façon cumulée. Pire cas : 3 plans à 25 i/s
    = 31 images sur 90, 57 images jetées par `-r`, sous-titres ASS jamais
    affichés.

  Correctif essayé sur copie : `fps={fps}:start_time=0` (3 endroits), plus une
  amorce `tpad=start_mode=clone:start_duration=0.04` posée APRÈS les effets
  sur tout plan qui suit un plan en coupe (`seg_durs[k] += 0.04`). Résultat :
  30/30, 60/60, 90/90, première image = image `in`, ASS images 30 à 59.
  Les 18 bancs de référence sont verts sur `e0ab545`. Avec le correctif,
  26 contrôles sont rouges, tous attendus (chaînes `fps=25,` figées, commandes
  dorées de 81bfde3 / 62f0c75 / L6-T1, r5 de retours_grade qui fige
  l'avance 0 ≤ k ≤ 7).
- **Aperçu à l'arrêt (B).**
  - Le client envoie déjà `t = srcIn + (tête − start) × vitesse` : la vitesse
    « image la plus proche » est juste.
  - D-14 ne porte que sur les overlays V2, que le lecteur anime déjà (KF1,
    KF5 de `patch_bundle_montage.py`).
  - Manques réels :
    - `dzmGlBody` renvoie `null` sans effet actif ;
    - retime blend/flow ;
    - stabilisation D-16 ;
    - piste d'ajustement J1.
  - `vidstabtransform` indexe par image d'entrée et `optzoom=1` travaille sur
    toute la trajectoire : seul un décodage depuis 0 est fidèle.
- **Plein écran (C).**
  - `DzmScopes` porte `.dzm-scwin` par `createPortal` dans `.dzsvm`.
  - `svmFullscreen` met `.svm-frame` en plein écran : ce qui est hors de
    l'élément plein écran n'est pas peint.
  - La règle CSS `.dzsvm>.dzm-scwin` vise un enfant direct.
- **Upload 415 (D).** La chaîne minifiée de `uploadVideo` est unique dans le
  bundle et dans `.bak_montage`. Elle sert aussi la Library. Le serveur rend
  déjà `{detail:"Fichier vide ou illisible : …"}`.
- **Seedance (F).**
  - `seedance-2.5` (`bytedance/seedance-2.5/image-to-video`) est au registre
    `VIDEO_MODELS` depuis le 28/08 (`05696b0`), tarifé 0,2205 $/s en 480p et
    0,473 $/s en 720p. Mais `DEFAULT_VIDEO_MODEL = "seedance-v1-pro"`.
  - Doc fal lue le 26/09 :
    - endpoints i2v, t2v et reference-to-video ;
    - pas de variante fast / lite / pro ;
    - durée `auto` ou 4–30 s, pas de `seed` en entrée ;
    - `generate_audio` sans effet sur le prix.
  - 1080p cité à ≈ 1,164 $/s sans figurer dans la table : non retenu.
  - Aucune garde de coût sur `/generate`, `/generate/batch`,
    `/generate/composition` ni sur le rendu de layout.
  - L'estimation « Défaut » retombe sur 0,04 $/s hérité.
  - Le Scheduler et le Spritelab « Animer » n'envoient aucun modèle.
  - La scène « Seedance (animated) » des Chapitres retombe sur Ken Burns.
- **Champs IA (G/H).**
  - 36 champs IA relevés dans 12 vues et 6 iframes de même origine.
  - Le Studio (éditeur de nœuds) vit sous `.dz-studio-grid`. Le Studio 3D est
    lui aussi un graphe de nœuds.
  - Les pages à part chargent déjà `/shared/dialogue.js`, sauf le Vectorlab
    (`mod-dialogue.js`).
  - Aucun `SpeechRecognition` dans le dépôt. L'enregistreur D-26 (`getUserMedia`,
    `MediaRecorder`) et `transcribe_service` existent : Scribe 0,0067 $/min,
    whisper-1 0,006 $/min, exposés seulement pour les sous-titres.
- **Chaîne des patchers.**
  - Ce worktree n'a aucun `.bak_*`. Les `.bak_montage` et `.bak_dzcout`
    d'`epic-fermi-f6adf5` correspondent au même bundle (`c45244ef`, `cmp`
    nul) : les copier avec `cp -p`.
  - La chaîne est `montage` → `dzcout`.

## 1. Décisions

### A — Horloge du rendu
- **A1.** `fps={fps}:start_time=0` partout où la chaîne V1 pose `fps` : le
  préfixe `sf`, la variante vitesse et la variante recadrage / zoom.
- **A2.** Une amorce clonée de 0,04 s est posée après les effets sur tout plan
  V1 qui suit directement un autre plan par une coupe. `seg_durs[k]` gagne
  0,04 s : l'offset du xfade tombe exactement sur `start`, et le total égale
  la timeline (`/render` comme `/measure`).
- **A3.** Les bancs dorés sont réécrits, et non assouplis. r5 de
  retours_grade passe à `|k| ≤ 1` avec un témoin positif qui prouve que
  l'ancienne chaîne donnait k = +1 image.
- **Écarts datés (hors lot).**
  - Un vrai fondu (τ > 0,04) avance encore le plan entrant et les suivants
    de τ : il faut des poignées de plan, c'est une autre décision.
  - Un trou suivi d'un plan en coupe avale la première image du plan.

### B — Aperçu étalonné à l'arrêt
- **B0.** `dzmGlBody` accepte le plan s'il a un effet actif, OU un retime avec
  une vitesse ≠ 1, OU `stab.on`, OU un clip J1 dont un effet est présent à la
  tête. La pastille dit ce qu'elle applique et ce qui manque.
- **B1. Retime blend / flow.** Le client ajoute `cadre.speed`,
  `cadre.retime` et `cadre.fps`. Le serveur prend une fenêtre alignée sur la
  grille (`m` = 2 images pour blend, 4 pour flow) et la même chaîne que le
  rendu (source unique `_RETIME`), puis sélectionne l'image à `t_local`.
- **B2. Stabilisation.**
  - Seulement si le `.trf` existe déjà (`MM.stab_path(p).exists()`) : le
    serveur n'analyse JAMAIS.
  - Décodage depuis 0, mêmes paramètres que `_v1_stab`, puis `trim`.
  - Plafond `t_src ≤ 20 s`. Au-delà, ou sans `.trf`, l'image est rendue sans
    stabilisation, avec l'en-tête `X-Dz-Grade-Note: stab-non-analysee` ou
    `stab-trop-loin` que la pastille affiche.
  - Le mtime du `.trf` entre dans la clé de cache.
  - Anti-rebond de 600 ms quand `stab` est posé.
- **B3. Piste J1.**
  - Le client envoie `cadre.adjust = [{start, end, effects}]` pour les clips
    J1 qui couvrent la tête, et `cadre.t_global`.
  - Le serveur extrait le bornage des lignes 4341–4357 dans
    `_adjust_bounded`, partagé avec le rendu (commande identique octet pour
    octet), et chaîne ces effets APRÈS la pile V1 et son masque.
  - Écart daté : au rendu, J1 touche aussi V2, les trous et les titres ; dans
    le lecteur, il ne touche que V1.
- **B4. Keyframes D-14.** Rien à ajouter dans grade-frame. Mesure Playwright
  à faire : un overlay à deux points d'échelle, tête arrêtée au milieu, on lit
  `transform` et `opacity`. Si la mesure dément, c'est un correctif du lecteur.
- **Écart daté.** Les effets et masques L5 des overlays V2 ne sont pas montrés
  dans le lecteur.

### C — Scopes en plein écran
- `DzmScopes` écoute `fullscreenchange`. La cible devient
  `document.fullscreenElement` quand `.dzsvm` le contient, sinon `.dzsvm`.
- Le portail change de cible. La géométrie est recadrée à la cible (affichage
  seul, rien n'est mémorisé), et un geste en cours est abandonné.
- L'écouteur est retiré au démontage.
- CSS : `.dzsvm>.dzm-scwin, .dzsvm .svm-frame>.dzm-scwin`.
- Tout vit dans `montage.js` et `montage.css`. On rejoue ensuite montage puis
  dzcout, et on réaligne les compteurs (`useState(` 578 → 579, règle CSS
  comptée exactement 1).

### D — Message d'upload
Une section du maillon `montage` remplace, dans `uploadVideo`,
`{ok:!1,error:`HTTP ${n.status}`}` par une lecture du JSON :
`detail`, sinon `HTTP <code>`. L'ancre complète est unique, et le motif court
(×2) n'est jamais utilisé seul. Le Studio (nœud UGC) et la Library en
profitent tous les deux.

### E — Upload vide `f331277e`
Aucune action de notre part : l'effacement est définitif. L'utilisateur le
retire par la corbeille 🗑 de sa carte.

### F — Seedance 2.5 par défaut, avec garde
- **F1.** `DEFAULT_VIDEO_MODEL = "seedance-2.5"`. Le Scheduler, le Spritelab
  et le « Défaut » du Quick en héritent. `test_video_models.py` est réécrit.
- **F2.** Pricing : un modèle vide se résout en `DEFAULT_VIDEO_MODEL` via
  `video_rate`, jamais en 0,04 hérité. On corrige aussi l'estimation épisodes
  et le plan marketing. On retire le commentaire « audio-off pricing column »
  pour 2.5.
- **F3. Garde serveur.**
  - `/generate`, `/generate/batch`, `/generate/composition` et le rendu de
    layout calculent leur estimation.
  - Ils refusent en 402 si elle dépasse `max_usd` envoyé par le client, OU
    le plafond `video_max_usd_per_request` de `pricing.json` (défaut 10 $).
  - Le détail du refus nomme le montant.
- **F4.** La durée GÉNÉRÉE par fal est plafonnée à
  `video_max_gen_s` (défaut 10 s). Au-delà, ffmpeg prolonge comme
  aujourd'hui.
- **F5. Bundle** (section du maillon `montage`, pins réalignés) :
  - la prop par défaut du nœud passe à `"seedance-2.5"` ;
  - le repli de `dzVmCost` passe au tarif 2.5 ;
  - `dzVmRates` 2.5 existe déjà.
  - Les graphes déjà enregistrés gardent leur modèle.
- **Écarts datés.**
  - 2.5 n'accepte pas de seed : les variations de `/generate/batch` ne sont
    plus reproductibles, et le `negative_prompt` est ignoré.
  - Le ratio suit l'image de départ.
  - La scène « Seedance (animated) » des Chapitres reste en Ken Burns : pas de
    génération ajoutée dans ce lot, le libellé le dit.
  - Le 1080p n'est pas ouvert.
- **Interdiction :** AUCUNE génération fal dans les bancs ni les preuves
  (espion sur `FalSeedanceClient`).

### G — Champs IA : liseré + holographique, variante B
- **Couche unique** : `frontend/shared/dz-champ-ia.js`, copiée à l'octet près
  dans `frontend/dist/shared/`.
  - Chargée par une balise `<script>` dans `frontend/dist/index.html` et dans
    les `index.html` des pages à part : Atelier, Cardforge, Material Forge,
    Spritelab, Vectorlab.
  - Elle injecte son propre `<style>`, sans toucher au bundle.
- **Marquage** :
  - Un `MutationObserver` pose `data-dz-ia` d'après une table de règles
    déclarative : sélecteurs, repli par libellé pour le Prompt et le Script du
    Quick.
  - Il ignore `.dz-studio-grid` et le Studio 3D (graphes de nœuds).
  - L'attribut `data-dz-ia` posé à la main est honoré.
- **Périmètre validé : les générations média**, soit environ 24 champs.
  - **Inclus :**
    - Quick : Prompt vidéo, Script HeyGen, Motion prompt ;
    - Chapitres : Prompt d'illustration ×2 ;
    - Atelier : style global, style DA, description d'entité, style d'entité,
      action de plan ;
    - Son & VFX : musique, paroles, SFX ;
    - Montage : Sons ;
    - Templates : prompt IA ;
    - Library : image ;
    - Game Assets : sujet 3D ;
    - Spritelab `#animPrompt` ;
    - Material Forge `#prompt` ;
    - Cardforge : face, décor, texture ;
    - Vectorlab `#iaTexte`, `#vitIaPrompt`.
  - **Exclus :**
    - textes de voix TTS ;
    - consignes LLM : brief du Scheduler, Persona, script et fountain de
      l'Atelier, auto-clips, générateur de prompt ;
    - textes publiés ;
    - recherches.
  - La table finale est remesurée à l'écran par l'implémenteur, avec capture.
- **Habillage (variante B)** :
  - Au repos, un liseré `conic-gradient` violet #8b5cf6 → bleu #3b82f6 →
    orange #f97316, fixe, avec un halo flou faible.
  - Au focus (`:focus-within`), rotation lente (6 s) et reflet holographique
    (dégradé irisé en `mix-blend-mode:screen` qui balaie en 5,5 s, trame fine).
  - Avec `prefers-reduced-motion: reduce`, tout est figé.
  - Le texte reste à son contraste d'origine.
  - Le champ n'est pas déplacé : on utilise un habillage enveloppant ou des
    pseudo-éléments sur un conteneur posé autour, sans casser la mise en page
    hôte.
- **Barre du champ** : un badge « IA », une pastille de modèle et le bouton
  micro.
- **Pastille de modèle : miroir du choix de la vue.**
  - Elle liste les modèles du type de génération (`/api/video-models`,
    `/api/image-models`).
  - Un modèle dont la clé manque est grisé, avec un `title`
    « clé FAL_KEY absente ».
  - Elle est synchronisée dans les deux sens avec le sélecteur natif de la vue
    (même valeur, coût affiché comme la vue), par un adaptateur par règle.
  - Là où la vue n'offre pas de choix (SFX, musique, 3D, Spritelab,
    Scheduler), elle montre le modèle réellement utilisé, grisée, avec un
    `title` qui l'explique.
- **Règle E-12** : tout bouton a un `title`. On grise, on n'échange jamais
  deux boutons par ternaire.

### H — Dictée : navigateur + repli payant
- **Micro** (`title` « Dicter — reconnaissance vocale du navigateur »).
- **Voie 1 : `SpeechRecognition` / `webkitSpeechRecognition`**, si présent.
  - `lang` = langue du document (fr-FR par défaut), `interimResults`.
  - Le texte est inséré AU CURSEUR, avec un événement `input` natif (setter du
    prototype) pour que React voie la valeur.
  - État d'écoute visible : liseré accéléré, pastille rouge qui bat, texte
    « À l'écoute… ». On arrête par clic ou par Échap.
  - Le `title` signale que l'audio part au service du navigateur.
- **Voie 2 : repli payant**, si la voie 1 est absente ou échoue (`network`,
  `not-allowed` hors micro).
  - Enregistrement par `MediaRecorder` (patron D-26), puis
    `POST /api/dictation/estimate` pour connaître la durée et le coût.
  - Un dialogue maison annonce « Transcrire 12 s par ElevenLabs Scribe
    ≈ 0,0013 $ ? ». Rien ne part sans « Oui ».
  - Ensuite `POST /api/dictation` avec `max_usd` = le montant affiché. Le
    serveur recalcule et refuse en 402 s'il dépasse.
  - Le fournisseur est celui dont la clé existe (Scribe, puis whisper-1). Sans
    clé, le micro est grisé en voie 2, avec un `title`.
  - Nouvelle route : l'utilisateur relancera le backend.
- **Interdiction :** aucune transcription réelle dans les bancs (espion sur
  `transcribe`). Une preuve payante ne se fait qu'avec l'accord explicite de
  l'utilisateur, montant annoncé.

## 2. Bancs et preuves
- **Un banc par processus**, lu par son code de sortie, avec le python
  embarqué. Règles de chaque banc :
  - `check(label, cond, detail)` ;
  - des assertions négatives avec témoin positif ;
  - un état vide ;
  - la faute n°6.
- **Bancs neufs ou étendus :**
  - avance : mesure image par image avec les deux ffmpeg ;
  - retours_grade (B) ;
  - edition (B0, C) ;
  - bundle (C, D, F5) ;
  - video_models / pricing / garde (F) ;
  - champ_ia (couche G/H sous DOM simulé, plus non-dérive des deux copies) ;
  - dictation (route, 402, espion) ;
  - banc croisé client/serveur à la clôture.
- **Harnais de mutations** en octets, avec `--pre-vol`, sur le modèle de
  `mutations_retours_l6.py`.
- **Preuves écran** sur 8799 (Playwright et Chrome) :
  - rendu de 3 plans en coupe à 30/30/30 ;
  - aperçu retime / J1 ;
  - scopes en plein écran ;
  - message 415 lisible ;
  - champs IA au repos et au focus (captures par vue) ;
  - pastille grisée sans clé ;
  - dictée avec `--use-fake-device-for-media-stream`, où la voie 1 est
    mesurée dans Chrome.

### I — GPT Image 2.5 (ajout validé le 27/09)
Quatre entrées `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst` (OpenAI) et `-flare-fal`, `-sunburst-fal` (fal), qualité `high`, 0,053 $/image ; routage des `-fal` avant le préfixe `gpt-image` ; sprites/pixel-art/tuiles partent d'une image de la Library (générateur global) et sont couverts par le registre. Détail : plan `2026-09-27-plan-retours-ia.md` §I.
