# Lot « video » — fiches modèle tirées des skills Scenario (scenario-labs/skills @ b96506d)

Lecture : SKILL.md + references/*.md + README.md (storyboard) de 14 skills ; scripts de
scenario-seedance-music-video parcourus seulement pour voir ce qu'ils vérifient.
Toutes les valeurs chiffrées sont « at authoring time » côté Scenario : à revérifier sur l'OpenAPI fal
avant de les inscrire au registre.

Rappel de l'état Deepotus (dz/fal_service.py VIDEO_MODELS, pricing.py) utilisé pour les correspondances :
- VIDEO_MODELS = image-to-video seulement (+ image de fin selon `end_image`), audio TOUJOURS coupé
  (`audio_param` forcé à False : « the app's pipeline owns audio »), pas de référence d'identité, pas
  de multi-plan, pas de text-to-video ; au-delà de la durée native, la pipeline rallonge par ffmpeg.
- Hors registre principal mais présents ailleurs : extension Veo 3.1 / 3.1 Fast (`extend_usd_per_s`),
  lip-sync Kling (`lipsync_usd_per_s`), `video_refs` (seedance-2.5-v2v, « Veo références », t335),
  VFX IA : minimax/h3-max/relight, minimax/h3-max/insert-video, kling o3 video-to-video/edit,
  flux-3/edit-video, ltx-2.3/reframe, topaz upscale, pixverse v5.5 effects.

---

## 1. scenario-video (transversal)

**Résumé.** Skill chapeau de la vidéo : boucle générique (choisir, lire le schéma, estimer, lancer,
attendre, revoir), règles de prompt communes à toutes les familles, édition, doublage, lip-sync,
plafonds de durée, clip musical en un passage. Famille : toutes (T2V, I2V, V2V, A2V).

**Faits utiles**
- [PROMPT] Un prompt vidéo = une direction de plan en phrases, pas en tags : taille de plan, décor,
  sujet + UNE action, UN mouvement de caméra lent nommé, source de lumière, style, puis une ligne son.
  « Named moves and concrete light survive generation; mood words do not. »
- [PROMPT] En image-to-video, l'image fixe déjà le look : ne prompter que mouvement, caméra et timing
  (« orbit left », « hold on the final pose ») ; changer UNE clause par nouvel essai.
- [PROMPT] Exclusions d'image toujours écrites : « no subtitles, no on-screen text » (un outil de
  sous-titres en ajoute, n'en retire aucun). Elles vont dans le prompt sauf si le schéma a `negativePrompt`.
- [PROMPT] Texte que le spectateur doit lire = composité au montage, jamais généré (« generated type drifts »).
- [PROMPT] Son : effets et ambiance en mots simples, dialogues entre guillemets, ne nommer QUE ce qui
  doit sonner.
- [PIÈGE] Écrire « no music » (ou nommer un genre/instrument) dans un prompt avec audio actif peut
  déclencher la modération propre à la bande son. Correctif : décrire le son diégétique positivement
  (« room tone, footsteps, one voice ») ou couper l'audio.
- [PIÈGE] Musique qui fuit malgré tout : relancer audio coupé et ajouter le son par un modèle SFX ou
  vidéo-vers-audio ; un modèle sans interrupteur audio ne peut pas faire ce rattrapage → changer de modèle.
- [PARAM] Image de départ = comment le plan s'OUVRE ; image de fin = comment il ATTERRIT, valable
  seulement avec une image de départ (« A first frame must be provided if a last frame is set », erreur 400).
- [PARAM] Image de référence = identité/look sans fixer aucun instant. Ouverture exacte → image de
  départ rendue ; personnage/produit récurrent → références. Beaucoup de schémas interdisent la paire.
- [PARAM] Audio de référence : guidance que le prompt doit « réclamer » (« the reference audio is her
  own voice, lip-synced » ; pour la musique : « the beat the cuts land on »), sinon ignoré, surtout
  à côté d'une référence de personnage.
- [PARAM] Aucun modèle vidéo ne prenait de LoRA : un style entraîné passe par une image générée avec
  la LoRA, donnée en image de départ ou en référence.
- [PARAM] Plafonds d'entrée : rejet et non rognage (« a 30.08 second reference against a 30.0 second
  limit fails »). Un `dry_run` propre n'est pas une preuve : comparer soi-même la durée réelle au plafond ;
  viser l'intérieur de la plage, pas le bord.
- [PARAM] Planchers aussi stricts que les plafonds : durée minimale lue dans le schéma (min, plus petite
  valeur d'enum, ou durée fixe : 5 s sur un membre à référence, 1-2 s ailleurs). Pour un élément VFX de
  1-2 s : rendre le plus court possible puis couper, ou demander plusieurs événements dans un clip
  (« three explosions, one after another ») puis découper.
- [MÉTHODE] Rallonger au-delà du plafond : prendre la DERNIÈRE image du clip rendu comme image de départ
  du suivant, écrire ce prompt d'après ce que montre l'image (positions, orientation, côté caméra) et non
  d'après le plan, puis concaténer en coupe franche.
- [MÉTHODE] Retouche dirigée ratée par un éditeur vidéo à prompt (recolor, échange d'accessoire) :
  éditer la première image avec un modèle image et re-rendre depuis elle en image de départ.
- [MÉTHODE] Doublage ≠ lip-sync : 1) doubler (garde voix/ton/timing, ne bouge pas la bouche ; omettre la
  langue source pour l'auto-détection ; `keyterms` en tableau pour protéger noms/marques), 2) extraire la
  piste, 3) lip-sync vidéo + piste. Écouter la sortie (survie de la piste d'origine non documentée).
- [PARAM] Lip-sync : champs `video`/`audio` ou `videoUrl`/`audioFile` ; contrôle de décalage de durée
  `syncMode`/`lipsyncMode` (`cut_off`, `loop`, `bounce`, `silence`, `remap`) ou booléen `loop`, selon membre.
  Un membre cité : clips 2 à 10 s en 720p-1080p.
- [CHOIX] Lip-sync : vidéo existante + nouvelle piste → membres video2video (redessinent la zone bouche,
  gardent le reste) ; image fixe + piste → avatars parlants img2video (inventent tout le mouvement ; ne
  rattrapent jamais un lip-sync raté, c'est une autre performance).
- [PIÈGE] Lip-sync « réussi » mais bouche immobile : visage petit, de profil, masqué ou flou → le modèle
  ne trouve rien, facture quand même. Pré-contrôle gratuit : la bouche doit se lire sur la première image ;
  sinon recadrer serré AVANT (un recadrage génératif qui élargit rétrécit le visage). Vérifier ensuite la
  résolution du recadrage contre le plancher du membre. Plusieurs visages : membre avec sélection du
  locuteur (`activeSpeaker`) ou recadrer sur un seul.
- [MÉTHODE] Contrôle lip-sync : planches contact source vs sortie (`ffmpeg -vf "fps=2"`) sur la zone bouche ;
  pixels identiques = visage non trouvé ; changer cadrage ou voie, pas la seed.
- [CHOIX] Chanson entière en un appel (audio2video) : membre testé 10 s à 6 min d'audio, sortie de la
  longueur du morceau ; membres « segment » plafonnés vers 20 s. Couper au passage livré d'abord (l'audio
  pèse sur le coût, la résolution aussi). Style preset ignore `styleImage` ; paroles = sous-titres incrustés
  (laisser vide si sous-titres au montage).
- [COÛT] Itérer au palier de résolution le moins cher et à la durée utile la plus courte, puis
  upscaler le clip gardé : re-rendre en plus haute résolution = nouvelle génération (peu de seeds,
  aucune ne garantit la reproduction entre paliers).
- [PIÈGE] Ne jamais porter un payload d'une famille à l'autre ; les générations retirées ne transmettent
  pas leurs contrôles propres (force de keyframe, enum fps) : relire le schéma du successeur.

**Correspondance Deepotus.** Concerne tous les ids vidéo ; règles directement applicables à l'agent
interne et au champ prompt I2V (prompt = mouvement seulement). Deepotus coupe déjà l'audio partout → la
règle « no music » ne joue que si un jour l'audio natif est ouvert. Manques : lip-sync de vidéo existante
autre que Kling (sync, latentsync… probablement sur fal), avatars parlants image+audio (Kling AI Avatar,
probablement sur fal), doublage vidéo (ElevenLabs dubbing, en direct), audio2video « chanson entière »,
upscale vidéo autre que Topaz. Paramètres non exposés : image de référence, audio de référence,
`syncMode`, `activeSpeaker`, `keyterms`.

**Propre à Scenario, non transposable.** `recommend`/`search`/`model_schema_get`/`model_run`/`jobs_wait`,
`dry_run` en CU, ids fixes `model_scenario-video-cut/split/concat/compose-video/audio-extract`, gating de plan
(`requires_plan_upgrade`).

---

## 2. scenario-seedance

**Résumé.** Contrat de la famille Seedance (ByteDance) 2.0 / 2.5 / Fast / Mini : un seul modèle qui
infère son mode d'après les entrées. Famille : T2V, I2V (début, début+fin), référence (R2V), édition et
extension V2V, audio natif.

**Faits utiles**
- [PARAM] Mode déduit des entrées : `prompt` seul = texte (`aspectRatio` 21:9 à 9:16 honoré) ;
  `image` = première image (`aspectRatio` IGNORÉ, la taille suit `resolution` et peut tomber « only near
  the ratio ») ; `image` + `lastFrameImage` (fin valable seulement avec début) ; `referenceImages` =
  identité/monde, pas l'état d'ouverture ; `referenceVideos` + prompt d'édition (exige `duration: -1`) ;
  extension inférée du libellé.
- [PARAM] `image` et tableaux de référence sont mutuellement exclusifs. `referenceVideos` (mouvement)
  et `referenceAudio` (timing/énergie ou voix) se combinent avec `referenceImages`. Sur 2.0 l'audio de
  référence exige une image ou vidéo de référence ; 2.5 l'accepte seul.
- [PARAM] Références toujours en tableau, même pour un seul élément (`["asset_x"]`).
- [PROMPT] Balises liées à l'ordre du tableau : `@image1` = `referenceImages[0]`, idem `@video1`,
  `@audio1`. Dire ce que chaque balise gouverne ET ce qu'elle laisse (« @image1 defines the bottle and
  label, nothing of the set »).
- [PROMPT] Pas de seed, masque ni paramètre caméra : caméra dans le prompt, UN mouvement dominant et
  UNE action par plan. Plusieurs actions = battements horodatés (« 0-2s … 2-4s … »), un par battement,
  le dernier finissant dans `duration`, le plan nommé comme « one continuous take ».
- [PROMPT] Audio de référence non revendiqué = ignoré (une voix générée surtout) : « @audio1 is her own
  voice; she speaks it to camera, lips in sync » ; musique : « the camera move and each action land on
  the beats of @audio1 ».
- [PIÈGE] Vidéo de référence = playblast 3D : chaque membre animé passe, une marche riggée revient raide
  ou glissante. Utiliser des capsules sans jambes + phrase « elles ne marquent que position, taille,
  rythme » pour laisser le modèle inventer la démarche.
- [PIÈGE] `duration` par défaut Auto : sur 2.5 un T2V a été chiffré comme le plafond de 30 s (« about
  four times its 8 second price ») ; toujours envoyer les secondes. Avec `referenceVideos`, Auto suit le
  clip de référence le plus long.
- [PARAM] Extension : `duration` = séquence AJOUTÉE, la sortie ne contient que cette queue (« a 10 s
  source with duration 15 returned 15 s of new footage ») → concaténer source + queue, lire la durée livrée.
  Libellé : « extend @video1 », ce qui tient (personnage, costume, lumière), l'action qui continue, pas de coupe.
- [PARAM] Plafonds par membre : 2.5 = 30 images, 10 vidéos, 10 audios de référence, 4 à 30 s, jusqu'à
  1080p ; 2.0 / Fast / Mini = 9 images, 3 vidéos, 3 audios, 4 à 15 s ; 4k sur 2.0 seul ; pas de
  `lastFrameImage` sur Mini.
- [COÛT] Prix : écart de 6× dans la famille pour un même job 4 s 480p → estimer le même job sur deux
  membres avant une série.
- [COÛT] Mode brouillon (2.5) : `draft: true` → aperçu 480p (`resolution` ignorée), finalisable en 1080p
  dans les 7 jours (voir fiche 3).
- [MÉTHODE] Règle de conditionnement : en mode référence, la 1re image s'ancre sur l'état de base du
  monde de référence, aucune formulation ne l'emporte. Ouverture précise → rendre une image fixe et la
  passer en `image`. Décider par plan avant de générer.
- [PARAM] `generateAudio` (défaut vrai) = un seul interrupteur sur toute la piste : il « score » aussi le
  plan. Une musique écrite dans un plan ne survit à aucune coupe (tonalité/tempo réinventés par plan).
- [PROMPT] Son des plans : « diegetic sound only: heels on tile, room tone » ; répliques entre guillemets,
  dimensionnées aux secondes du clip, locuteur nommé, diction en 2-3 mots.
- [PIÈGE] `OutputAudioSensitiveContentDetected` vient souvent d'une exclusion (« no music ») : relancer
  sur le même modèle avec le son nommé positivement avant de changer de fournisseur.
- [PIÈGE] `OutputVideoSensitiveContentDetected` (+ `PolicyViolation`, parfois « copyright ») = filtre de
  la famille sur le rendu : un frère Seedance refuse pareil, réessayer à l'identique re-bloque. Changer
  de fournisseur d'abord (même prompt, balises déplacées vers le champ de référence de l'autre).
  Personnage pris pour une PI existante = bloqué quelle que soit la formulation ; vocabulaire d'arme/
  violence (« axe », « blade », « eliminated ») déclenche même en dessin animé.
- [PIÈGE] Pas de légendes, prix, logos, UI générés : réserver l'espace, compositer en post.
- [MÉTHODE] Vérifier en regardant AVEC le son avant d'ajouter la musique.

**Correspondance Deepotus.** seedance-v1-pro, seedance-2, seedance-2-fast, seedance-2.5 (défaut) ;
`video_refs` « seedance-2.5-v2v ». Deepotus envoie déjà l'entier de durée (évite le piège Auto) et coupe
l'audio. Manques modèles : Seedance 2.5 reference-to-video (R2V, très probablement sur fal), Seedance
2.5 draft + draft-complete (à vérifier sur fal), Seedance 2.0 Mini, Seedance 2.5 en T2V. Manques
paramètres : `referenceImages`/`referenceVideos`/`referenceAudio` (hors t335), `draft`, 1080p sur 2.5
(retenu volontairement faute de prix publié), 4k sur 2.0, `aspectRatio` en T2V, extension Seedance.
Note : Deepotus déclare `ratios: None` sur 2.5 — conforme au fait « aspectRatio ignoré en I2V ».

**Propre à Scenario.** CU, `support@scenario.com`, `scenario-moderation` (bascule de fournisseur dans le
budget autorisé), ids `model_bytedance-*`.

---

## 3. scenario-seedance-drafts

**Résumé.** Explorer plusieurs prises Seedance 2.5 en brouillon 480p bon marché, les classer, puis
finaliser LA prise choisie en 1080p sans la régénérer. Famille : Seedance 2.5 (draft + draft-complete).

**Faits utiles**
- [PARAM] `draft: true` (booléen, 2.5) ; `resolution` ignorée pendant le brouillon. Finaliseur à part,
  entrée unique `draftVideo` (fichier scalaire) = l'asset du job brouillon lui-même.
- [PARAM] Fenêtre de finalisation : 7 jours après création ; au-delà, seule une régénération (= nouvelle prise).
- [CHOIX] Seedance n'a pas de seed : le brouillon est le SEUL moyen d'approuver une prise pas chère puis
  de livrer exactement celle-là. Re-lancer en 1080p = autre prise ; upscaler le 480p = copie molle.
- [COÛT] Brouillon ≈ rendu 480p ; brouillon + finalisation ≥ rendu 1080p direct (« 2,040 against 2,024 CU
  for a 15 second edit »). Rentable seulement grâce aux prises jetées : 5 prises 15 s + 1 finale
  « about 3,500 CU, against about 10,100 » ; une prise unique coûte PLUS cher en brouillon.
- [MÉTHODE] Estimer les deux payloads (brouillon et livraison) et poser l'arithmétique N brouillons +
  1 finalisation contre N finales avant de lancer.
- [PARAM] Pas de champ « nombre de sorties » : une prise = un appel identique. Durée = celle du plan
  (Auto = plafond 30 s facturé) ; édition = `-1`.
- [PARAM] Délais : brouillons d'édition 15 s = 7 à 8 min ; finalisation 1 à 3 min.
- [PIÈGE] La finalisation se télécharge en MOV (HEVC une fois) alors que les métadonnées disent MP4
  H.264 → composer par identifiant, vérifier le conteneur.
- [PIÈGE] Seul l'asset brouillon d'origine se finalise : pas une version avec musique, pas un trim, pas
  un ré-encodage. Mettre la musique de livraison UNE fois, sur la finalisation.
- [MÉTHODE] Revue de prises : 1) planche contact de tout le clip (`fps=2,scale=150:-1,tile=10x3` pour 15 s)
  → échange d'identité, costume, décor, accessoires ; 2) gros plans là où ça casse : mains en mouvement
  rapide, cheveux longs dans les rotations, visage à 4 instants, chaque accessoire compté contre sa
  référence ; 3) timing : 4 horodatages appariés contre la source.
- [PIÈGE] Les planches trouvent des défauts mais n'en excluent pas ; le comptage de pixels est faible
  (test « gant rouge » déclenché par une bougie) ; les défauts de mouvement échappent aux images
  échantillonnées → faire regarder les finalistes à vitesse réelle avant de payer.
- [MÉTHODE] Classer par variante, horodater chaque défaut, dire ce qui a été vérifié ou non.
- [MÉTHODE] Preuve de finalisation : 1080 de large, même fps et durée que le brouillon, images identiques
  au balayage.
- [PARAM] Pour poser une piste : longueur arrondie au pas de 0,1 s INFÉRIEUR (« a 4.04 s clip loses its
  last frame at 4.0 »), fps explicite (défaut 30 sinon).
- [PIÈGE] Erreur 429 de parallélisme : aucun job créé ; relancer les prises refusées au fil de l'eau.

**Correspondance Deepotus.** seedance-2.5. Manques modèles : endpoint draft + draft-complete (à vérifier
sur fal ; plausible car exposé par ByteDance). Manques paramètres : `draft`, nombre de prises / variantes
parallèles, conservation de l'id brouillon 7 jours, 1080p. Bonne idée transposable même sans draft : la
grille de revue (planche, gros plans, timing).

**Propre à Scenario.** CU chiffrés, `actionLimit`, `model_scenario-compose-video`, `asset_get` qui renvoie
first/lastFrame gratuitement.

---

## 4. scenario-seedance-storyboard

**Résumé.** Tenir un mouvement continu (danse, combat, sport) sur plusieurs plans Seedance : script
horodaté, planches personnage, storyboard crayon, images clés photo, puis un run scripté ou des runs
chaînés début/fin. Famille : Seedance 2.5 / 2.0 en référence ou début+fin.

**Faits utiles**
- [MÉTHODE] Règle unique : chaque plan finit dans la pose où commence le suivant (« pose chain »).
  Script : par plan numéro, taille, angle, objectif ou mouvement, 3 verbes d'action, pose d'entrée et
  de sortie. Couverture : master d'abord, tenir l'axe, gravir l'échelle des tailles, ponctuer (insert,
  réaction).
- [PROMPT] Chorégraphie en verbes horodatés et poses de bord, jamais en adjectifs (« dances energetically »).
  Nommer la position à l'écran en plus de la pose (une limite en miroir casse la coupe).
- [PROMPT] Action écrite comme de la physique : approche, contact, transfert de force, récupération ;
  traînée des matières souples (manches qui se posent un temps après les bras, poussière qui retombe).
- [PROMPT] Structure du prompt run scripté, 7 sections dans l'ordre : REFERENCE ROLES, GUIDES ARE NOT
  CONTENT, STARTING STATE, TIMELINE, CAMERA, MUST REMAIN UNCHANGED, CONSTRAINTS. En chaîné : seulement
  STARTING STATE, TIMELINE (1 battement), CAMERA, MUST REMAIN UNCHANGED, CONSTRAINTS sans l'audio.
- [PROMPT] TIMELINE : chaque entrée = horodatage + « Panel N » + taille/angle/objectif-mouvement +
  pose d'entrée + pose de sortie. Nommer la planche augmente sa fidélité (y compris ses défauts).
- [PROMPT] Une INTERDICTION ne marche pas, une DÉFINITION si : « planning guides drawn on paper by the
  director … not objects in the world ». Garder les deux moitiés (définition + liste d'exclusions).
- [PROMPT] CAMERA : seulement des machineries réelles (dolly, trépied), pas de dérive si statique, et un
  obturateur pour fixer le flou (« consistent with a 1/48 second shutter on 35mm film »).
- [PROMPT] MUST REMAIN UNCHANGED : invariants d'identité + comptage anatomique (« five fingers on each
  hand in every frame »). CONSTRAINTS : membres dupliqués, pieds qui glissent, téléportation, filigranes,
  ralenti, rampes de vitesse, arrêts sur image.
- [PROMPT] Son : « Diegetic sound only: heel taps on the boards, fabric, breath, room tone. » ; ajouter
  « a distant guitar » a fait échouer le job (`OutputAudioSensitiveContentDetected`) ; l'exclusion
  « No music » a aussi échoué ailleurs → ne nommer ni instrument ni omission.
- [PIÈGE] Storyboard photoréaliste ou crayon CHARGÉ = traité comme image : numéros de case brûlés
  (« leaked its panel numeral into 6 of 8 delivered shots »), flèches rendues comme objets. Storyboard
  crayon LÉGER : « 0 leaks in 93 opportunities » ; flèches douces et pâles OK.
- [MÉTHODE] Images clés photoréalistes (2-3) passées comme « concept art » : donnent le look et une
  source photo pour l'apparence. Une planche par personnage plutôt qu'une feuille combinée
  (`@image1` = A, `@image2` = B).
- [PARAM] Ratio du storyboard composé entre 0.4 et 2.5, sinon rejet opaque. Ratio = 16×colonnes /
  9×lignes : 4×2 = 3,56 échoue, 3×3 = 1,78 et 4×3 = 2,37 passent, 6 cases → 2×3 (1,19).
- [PARAM] Chaque case au ratio de livraison (un recadrage déplace les poses).
- [CHOIX] Run scripté unique si la séquence tient dans le plafond (30 s sur 2.5) ; nommer `aspectRatio`
  (défaut `adaptive` → un board portrait donne une vidéo portrait). Chaîné si plus long, contrôle par
  plan, ou ouverture sur une pose exacte : plan N = `image` image N-1, `lastFrameImage` image N ;
  N plans = N+1 images, N runs ; pas de `referenceImages` (les images sont la seule identité),
  `aspectRatio` ignoré.
- [PARAM] Plancher par run : « 4 whole seconds on 2.5 », secondes entières → 8 plans = 32 s minimum,
  12 = 48 s. Faire l'arithmétique avant de rendre les images.
- [PIÈGE] Un run scripté ne livre pas une coupe par horodatage : 11 passages scriptés → 0, 2, 2 et 6
  coupes détectées ; le reste devient mouvements de caméra. Des coupes « ressenties » se font au montage.
- [PIÈGE] En chaîné, la taille de plan ne peut pas changer à une jointure (même image des deux côtés) ;
  gravir l'échelle par mouvements de caméra DANS les plans.
- [PIÈGE] Personnage qui sort du cadre et revient dans un même run : perdu. Sorties/retours/changements
  hors champ → sur une image de bord chaînée ; le plan qui y mène ne nomme pas le détail changé.
- [PIÈGE] Dérive de costume d'une image de bord à l'autre (masque, cimier, finition métal) : chaque dérive
  tombe sur une coupe → revoir le JEU d'images ensemble, régénérer l'image fautive, pas le plan.
  Images de bord : prompt identique à l'octet, seule la clause de pose varie ; garder le cadrage ; garder
  une place de réserve dans le budget d'images.
- [PIÈGE] Prompt au-delà de `max_length` ou horodatages au-delà du plafond = 400, jamais rognés ;
  envoyer la longueur scriptée en `duration` (Auto indéfini sans clip de référence).
- [PIÈGE] Plan refusé à cause de l'audio (combat) : relancer `generateAudio: false` ; ne pas mélanger
  plans sonorisés et muets → master image seule, son posé sur le montage.
- [MÉTHODE] Contrôle : balayer à 2 i/s tout le clip (un marquage peut apparaître à mi-plan : échantillon
  à 10,5 s propre, flèche à 11,0 s) ; comparer dernière image sortante / première entrante par jointure ;
  si une fin livrée est meilleure que le dessin, l'utiliser comme image de départ suivante et réécrire
  STARTING STATE.
- [MÉTHODE] Contrôle qualité des cases en DEUX passes : score d'artefacts + « jeu des différences »
  contre la planche (comptes de mains/doigts/roues, partie-tout, livrée/costume, côté écran). Un score
  global de board (88, pass) masque des cases impossibles ; le score n'indique pas si une réparation a marché.
- [MÉTHODE] Réparer une case : découper, régénérer seule la case avec correction formulée POSITIVEMENT
  (« Both wheels the same rim design… »), recomposer ; ne pas re-tirer tout le board.
- [CHOIX] Défauts qui passent dans la vidéo : marquages lus comme objets, erreurs de plan (côté écran,
  livrée). Défauts souvent recalculés : géométrie d'accessoires/membres → une tentative de réparation, pas trois.
- [COÛT] Case réparée 47 CU contre 2730 CU de run vidéo ; dépense réelle du PR ≈ 26k CU contre 41k
  estimés → lire le compteur. Un test « plan seulement » gratuit a trouvé un bug que 5 runs payants
  n'avaient pas vu : tester à vide d'abord.
- [CHOIX] Modèle de board : texte lisible, respect de grille, entrée `referenceImages` (gpt-image-2 cité).
  Hauteur 1080 peut rater le `step` du modèle image, plafond de pixels total non déclaré.

**Correspondance Deepotus.** seedance-2.5 (et 2) en début+fin — c'est EXACTEMENT la voie chaînée,
déjà possible dans Deepotus (`end_image: True`) ; Plateau/Storyboard 3D et Scenario (méthodes) en
profitent. Images de bord : gpt-image-2(-fal), nano-banana-pro. Manques modèles : Seedance 2.5 R2V
(voie scriptée, jusqu'à 30 images de référence). Manques paramètres : `referenceImages`, `aspectRatio`
en mode référence, audio natif (coupé), `max_length` du prompt non affiché.

**Propre à Scenario.** Collections (`collection_create`…), `asset_quality_gate_run` (add-on Enterprise),
`model_scenario-image-slicer` / `compose-image` / `video-to-image-seq`, clean-room agents du README.

---

## 5. scenario-seedance-music-video

**Résumé.** Transformer un morceau maître en clip : analyse du morceau, paroles, histoire, images,
plans Seedance calés sur les sections, assemblage ffmpeg qui pose le master intact. Famille : Seedance + outillage local.

**Faits utiles**
- [MÉTHODE] 5 étapes : chanson, paroles, histoire (1 page montrée d'abord), images, vidéo ; le master
  fourni est la SEULE musique, aucun plan n'écrit la sienne.
- [CHOIX] Deux bandes : chanson seule → `generateAudio: false` partout, master recopié bit à bit ;
  chanson + son des plans → audio activé, prompts « diegetic sound only: … », mixage des clips sous le
  master au gain `sound` 0,1-0,3 (jusqu'à 1,0 si clips faibles ; bornes 0-4), refus si écrêtage.
- [MÉTHODE] song.py : empreinte, durée, loudness EBU R128, tempo (autocorrélation de l'enveloppe
  d'attaques), sections (changement de niveau qui tient ≥ 1,5 s, seuil 2 dB), candidats de coupe
  (attaques les plus fortes, espacées ≥ 2 s). Ce sont des suggestions : écouter.
- [MÉTHODE] build.py : chaque plan va jusqu'au suivant (pas de trous), `at` calé sur l'image la plus
  proche, `in` = rognage de tête ; échoue sur clip trop court, mix qui écrête, audio livré ≠ master.
- [PARAM] Générer chaque plan 1 à 2 s plus long que son créneau (poignée de coupe).
- [PROMPT] Caler une action sur un temps fort : horodater depuis le début du clip = temps du master −
  `at` du plan + rognage `in` prévu.
- [PROMPT] Forme de prompt qui a tenu (5 éléments) : rôle de chaque référence par balise (« @audio1 is
  timing only ») ; fonction de la section + objectif visuel en une ligne ; UN mouvement + UNE action ;
  état de fin explicite ; exclusions d'image + son par ses sources (« Silent footage. » si audio coupé).
- [PROMPT] Une image de départ n'a pas de balise : nommer ce qu'elle montre déjà et prompter le mouvement
  qui s'en éloigne. Un prompt décrivant une séquence fait couper le modèle à l'intérieur du clip.
- [PIÈGE] En mode référence, 4 tentatives payantes n'ont pas ouvert sur l'état voulu ; passer en première
  image a réglé au premier essai. Les plans en référence redémarrent chacun leur évolution → continuité
  cassée aux temps forts ; porter l'état par l'image de sortie du plan précédent.
- [PIÈGE] Juger une coupe sur une planche clairsemée : un mouvement continu ressemble à une coupe. Mesurer :
  réduire à ~160×90, différence absolue moyenne entre images consécutives, coupe = pic très au-dessus de
  la ligne de base.
- [PIÈGE] La légende automatique d'un asset est souvent fausse ; regarder le clip.
- [PIÈGE] Ratio demandé jamais exact (images et clips « land near it ») → recadrer au ratio de livraison.
- [PIÈGE] Ne pas rogner, normaliser, fondre ni ré-encoder le master soi-même.
- [PARAM] Un modèle à qui on demande 8 s ne rend pas toujours 8 s : lire durée/fps/nb d'images réels.
- [COÛT] Durée, résolution et vidéos de référence pèsent sur le coût ; images et audio de référence non.
- [MÉTHODE] Livrer après avoir regardé avec le son, puis muet. Questions à poser une fois : droits du
  morceau, ratio, longueur, son sous la chanson ou non, ce qui doit/ne doit pas apparaître, plafond de dépense.

**Correspondance Deepotus.** seedance-* en I2V ; Montage (pose de musique, coupe), music_service
(lyria, minimax-music…) pour la partition, stems htdemucs. Manques : analyse de structure du morceau
(sections/tempo/candidats de coupe) — transposable localement (numpy + ffmpeg, MIT, attribution
E. de Maistre) ; transcription de paroles chantées (Whisper existe côté STT). Paramètres : gain du son
des plans sous le master, poignée de coupe automatique, détecteur de coupes par différence d'images.

**Propre à Scenario.** Upload multipart `upload_asset_complete`, `metadata.preview` des transcriptions.

---

## 6. scenario-kling

**Résumé.** Famille Kling (Kuaishou), 18 membres spécialisés : V3 (Omni + T2V/I2V Standard/Pro/4K),
O1, 2.6, Motion Control, Lipsync, AI Avatar. Famille : T2V, I2V début/fin, multi-plan, éléments
(personnage cohérent), édition, transfert de mouvement, lip-sync, audio natif.

**Faits utiles**
- [CHOIX] Par tâche : tout-en-un à palier via `mode` = V3 Omni (`standard` 720p, `pro` 1080p, `4k`) ;
  T2V palier fixe = V3 T2V / 2.6 T2V Pro ; animer une image (+fin) = V3 I2V / O1 I2V / 2.6 I2V Pro ;
  personnages cohérents = O1 Reference Images, V3 I2V `elements` ; éditer/restyler = O1 Video Editing /
  Reference Video, Omni `videoReferenceType: "base"` ; mouvement d'une vidéo sur une image = Motion
  Control ; tête parlante = AI Avatar (image+audio) ou Lipsync (vidéo+audio/texte).
- [PARAM] V3 dédiés : `prompt` OU `multiPrompt` (tableau de `{prompt, duration}`), jamais les deux ;
  `shotType` (`customize`/`intelligent`) seulement sur V3 T2V et I2V 4K. Omni : `prompt` requis,
  `multiPrompt` = chaîne JSON jusqu'à 6 plans dont les durées somment `duration`.
- [PARAM] `duration` en CHAÎNE (`"5"`) sur la plupart ; Omni seul en nombre, 3 à 15. V3 dédiés jusqu'à
  15 s ; O1 et 2.6 s'arrêtent à 10.
- [PARAM] Élément = `frontalImage` + jusqu'à 4 `referenceImages` d'angles (les deux requis sur O1,
  optionnels sur V3 I2V où une `video` peut définir l'élément).
- [PARAM] Budgets de références qui fondent à côté d'une vidéo : O1 Reference Images 7 au total, O1
  vidéo 4, Omni `referenceImages` 7 → 4 avec `referenceVideo`. Balises `@Element1`, `@Image1` ; Omni :
  `<<<image_1>>>`, `<<<video_1>>>`.
- [PARAM] Clip de référence 3 à 10 s (Omni, O1 vidéo), 2 à 10 s (Lipsync). Omni `videoReferenceType`
  défaut `"feature"` (prête style et caméra) ; `"base"` édite le clip et ignore `duration` ; mode `4k`
  refuse toute vidéo de référence.
- [PARAM] `cfgScale` 0 à 1, défaut 0,5 : vers 0,8 pour fidélité au storyboard, vers 0,3 pour laisser inventer.
- [PROMPT] Ordre « réalisateur » : scène, sujet, action, UN mouvement de caméra, puis audio et style ;
  phrases naturelles > listes de tags ; les scènes complexes tiennent vers 5 s, pas 15.
- [PROMPT] Mouvements composés (« dolly in while orbiting ») : un dominant par plan, répartir le reste
  sur des plans `multiPrompt`.
- [PROMPT] Négatif surchargé : une courte liste d'artefacts guide, une longue rigidifie le mouvement.
- [PARAM] `generateAudio` : défaut vrai sur V3 dédiés et 2.6 T2V, faux sur Omni et 2.6 I2V, absent sur
  O1 (édition : `keepAudio`). Refusé à côté de la vidéo de référence Omni et à côté de `lastFrameImage`
  sur 2.6 I2V. Les membres 4K facturent à la seconde dans tous les cas.
- [PROMPT] Voix en chinois et anglais seulement (autres langues auto-traduites en anglais) ; dialogue entre
  guillemets, minuscules pour l'anglais parlé, MAJUSCULES pour les sigles.
- [PARAM] Lipsync : un fichier audio OU `text` + `voiceId`, jamais les deux.
- [PARAM] Motion Control : `image` personnage + `video` motrice ; `characterOrientation` indique quelle
  entrée porte le personnage et, en V2.6, plafonne la vidéo motrice (10 s si `image`, 30 si `video`) ;
  défauts différents selon membre → toujours le fixer ; `keepOriginalSound`.
- [PIÈGE] Aucun Kling n'étend : Omni `base` édite en place. Continuer = dernière image en départ d'un
  nouvel I2V puis concaténer.
- [COÛT] 4K = plusieurs fois Standard ; avatars : écart de 100× → estimer avant. Itérer en Standard ;
  pas de seed sur V3/O1/2.6 → re-rendre en 4K = nouvelle prise ; upscaler garde la prise.

**Correspondance Deepotus.** kling-v3-pro, kling-v3-standard, kling-v3-turbo-pro, kling-v4 ;
kling-lipsync ; VFX kling o3 video-to-video/edit ; kling video-to-audio (SFX). Manques modèles : V3 Omni,
V3 4K, O1 (I2V, Reference Images, Video Editing), 2.6, Motion Control V3/V2.6, AI Avatar (presque tous
probablement sur fal sous fal-ai/kling-video/…). Manques paramètres : `multiPrompt` / `multi_prompt` +
`shotType` (Kling 4.0 le porte aussi : `multi_prompt`, `middle_image_urls` hors registre), `elements`,
`cfgScale`, `videoReferenceType`, `characterOrientation`, `keepOriginalSound`, `text`+`voiceId` en lip-sync,
4K. Deepotus a le négatif sur V3 Pro/Std (cohérent avec « liste courte »).

**Propre à Scenario.** Ids `model_kling-*`, `dry_run` CU.

---

## 7. scenario-veo

**Résumé.** Google Veo 3.1 : quatre membres (3.1, Fast, Lite, Extend). Famille : T2V, I2V,
transition début→fin, référence (R2V) avec bascule ASSET/STYLE, extension, audio natif, négatif, seed.

**Faits utiles**
- [PARAM] Modes : texte (`aspectRatio` 16:9 ou 9:16) ; première image (une image mal proportionnée peut
  être recadrée) ; transition `image` + `lastFrameImage` (prompter UN mouvement continu) ;
  référence 1 à 3 `referenceImages`, `duration` VERROUILLÉE à 8 ; extension (membre dédié).
- [PARAM] `image` et `referenceImages` exclusifs. `referenceImagesType` sur 3.1 complet seulement :
  `ASSET` (défaut : sujets, objets, scènes) ou `STYLE` (palette, lumière, texture), s'applique à tout le
  tableau. Fast prend des références sans la bascule ; Lite n'en prend aucune.
- [PARAM] Communs aux trois générateurs : `negativePrompt`, `resolution` 720p/1080p, `duration` 4, 6
  ou 8, `seed`. `generateAudio` REQUIS sur tous et fait varier le prix.
- [PARAM] Extend : seulement `prompt`, `video`, `generateAudio`, `seed` ; source 16:9, petit côté 720p
  ou 1080p ; pas de 9:16.
- [COÛT] Lite ↔ 3.1 : environ 5× d'écart pour un même I2V ; une extension a coûté plus qu'une génération
  complète neuve → viser le plan en un passage de 8 s ; estimer sur deux membres.
- [PROMPT] Audio pris au pied de la lettre : répliques entre guillemets, effets préfixés `SFX:`,
  ambiance `Ambient noise:`. Sans direction audio, une bande arrive quand même (pas celle voulue).
  Silence voulu → `generateAudio: false`, pas « quiet » dans le prompt.
- [PROMPT] Prose au présent ordonnée cinématographie → sujet → action → contexte → style ; caméra et
  échelle de plan d'abord, UN arc principal, « roughly 90 to 250 words ». Plusieurs temps : lignes
  horodatées `[00:00-00:02] Medium shot...` dans la durée choisie.
- [PROMPT] Ne pas écrire le prompt comme une liste de négations : décrire la scène, réserver
  `negativePrompt` à ce qu'il faut décourager.
- [MÉTHODE] Itérer sur la formulation seule en gardant une `seed` fixe.

**Correspondance Deepotus.** veo-3.1-fal, veo-3.1-fast-fal, veo-3.1-lite-fal (début+fin via
`endpoint_fl`), jumeaux Google retirés le 22/10 ; extensions veo-3.1(-fast)-extend ; `video_refs`
« Veo références ». Deepotus expose seed et négatif (conforme). Manques modèles : Veo 3.1 T2V,
reference-to-video sur fal (probable : fal-ai/veo3.1/reference-to-video). Manques paramètres :
`referenceImagesType` ASSET/STYLE (hors t335 à vérifier), audio natif avec SFX:/Ambient noise: (coupé),
garde-fou « Extend = 16:9 seulement », « référence = 8 s seulement ».

**Propre à Scenario.** Ids `model_veo3-1*`.

---

## 8. scenario-wan

**Résumé.** Wan (Alibaba) 2.7 / 2.6 / 2.5 / 2.2 : un membre par tâche, noms de paramètres différents
entre générations. Famille : T2V, I2V, début+fin, extension, édition par instruction, Animate (transfert
de mouvement / remplacement de personne), Reframe, Outpainting, audio uploadé ou généré, multi-plan 2.6.

**Faits utiles**
- [CHOIX] Par tâche : T2V 2.7/2.6/2.5 ; I2V 2.7/2.6/2.5 ; étendre = 2.7 I2V (`video` + prompt, exclut
  `image`) ; restyler = 2.7 Video Edit ; personnage qui rejoue une vidéo = 2.2 Animate Move
  (`imageUrl` + `videoUrl`) ; remplacer la personne = 2.2 Animate Replace ; changer le ratio = 2.2 Reframe ;
  agrandir le cadre = 2.2 Outpainting.
- [PARAM] 2.7 : `resolution` 720p/1080p, `duration` entière 2 à 15, `aspectRatio` (16:9 à 3:4) en T2V
  seulement. 2.6/2.5 T2V : une chaîne `size` (« "1920*1080" »), durées sur grille (5/10/15 en 2.6 ;
  5/10 en 2.5) ; leurs I2V prennent `resolution`.
- [PARAM] Video Edit : source 2 à 10 s, `duration` optionnelle qui tronque. Reframe/Outpainting : pas de
  `duration` mais `numFrames` 81 à 241 à `framesPerSecond` 5 à 30 ; longueur source conservée seulement si
  `matchInputNumFrames` et `matchInputFramesPerSecond` vrais (défaut faux → 81 images à 16 i/s).
  Outpainting : jusqu'à 10 `refImageUrls` ; drapeaux `expandTop/Bottom/Left/Right` tous vrais par défaut.
- [PARAM] 2.7 I2V : `image` et `video` exclusifs ; `endImage` seulement avec `image`.
- [COÛT] 1080p ≈ 3× 720p sur 2.7 T2V.
- [PROMPT] T2V : scène complète en langage naturel (action, UN mouvement, lumière, tags de style).
  I2V : MOUVEMENT SEULEMENT, re-décrire l'image gaspille le prompt ; pas de changement de contenu en I2V.
  Video Edit : instructions, un changement clair par phrase avec cible précise + langage de préservation
  (« keep subject identity and camera path ») ; `referenceImage` = look cible.
- [PIÈGE] Texte lisible dans l'image peu fiable sur tous les membres ; artefacts dans `negativePrompt`
  (absent de Video Edit et Animate).
- [PROMPT] Multi-plan (2.6 seul) : `multiShots` vrai (défaut) mais actif SEULEMENT si
  `enablePromptExpansion` vrai ; ligne de style globale puis `Shot 1 [0-3s] ...`, `Shot 2 [3-7s] ...`,
  personnages et lieu continus. Aucun autre membre ne lit les crochets.
- [PARAM] `enablePromptExpansion` défaut vrai sur les générateurs (aide les prompts maigres, ajoute de
  la latence), faux sur Reframe/Outpainting.
- [PARAM] Audio : 2.7 livre TOUJOURS de l'audio (fichier `audio` fourni ou piste générée d'après le son
  décrit → prompter l'ambiance voulue) ; 2.6/2.5 : audio seulement depuis un fichier de 3 à 30 s,
  ≤ 15 Mo, que 2.6 lip-synchronise. Video Edit `audioSetting` : `origin` garde, `auto` régénère.
  Animate garde la piste source tant que `mergeAudio` vrai.

**Correspondance Deepotus.** wan-3.0 (I2V, `start_image_url`, 2..30 s, 480p-1080p, interrupteur `audio`,
seed). La skill ne couvre pas 3.0 : transposer prudemment la règle « I2V = mouvement seulement » et
« audio généré d'après le son décrit ». Manques modèles : Wan 2.7 Video Edit, 2.2 Animate Move/Replace,
2.2 Reframe, 2.2 Outpainting (VACE ; tous probablement sur fal), 2.6 multi-plan. Manques paramètres :
`negativePrompt` (registre wan-3.0 sans `negatif`), `enablePromptExpansion`, audio uploadé pour lip-sync,
multi-plan.

**Propre à Scenario.** Ids `model_wan-*`.

---

## 9. scenario-minimax-video

**Résumé.** MiniMax Hailuo : H3 (tout-en-un, audio stéréo), ligne H3 Max (texte, image, référence,
lip-sync + jumeaux Turbo), éditeurs Extend (+Turbo), Insert Video, Recast ; Hailuo 2.3 déprécié.
Famille : T2V, I2V début/fin, références image/vidéo/audio, éditions V2V.

**Faits utiles**
- [PARAM] H3 : texte (`aspectRatio` 21:9 à 9:16, défaut `adaptive`) ; `firstFrameImage` (forme suit
  l'image, ratio ignoré) ; + `lastFrameImage` (seulement avec le début) ; références `referenceImages`,
  `referenceVideos`, `referenceAudio` (guident sujet, style, mouvement, voix ; ratio appliqué).
- [PARAM] Images-clés et références jamais mélangées. `referenceAudio` jamais seul (≥ 1 image ou vidéo
  de référence). Tableaux même pour un élément.
- [PARAM] H3 : 9 images, 3 vidéos, 3 audios de référence (vidéos et audio 2 à 15 s chacun et au total),
  sortie 5 à 15 s, `768P` ou `2K`. Pas de seed sur H3 ni 2.3.
- [PARAM] 2.3 : `prompt` + `firstFrameImage` seulement ; couple contraint : 10 s seulement en 768p,
  1080p seulement en 6 s. `promptOptimizer` (défaut vrai) réécrit le prompt : le couper si la
  formulation doit passer telle quelle.
- [CHOIX] H3 = seul à mélanger les modes et (hors lip-sync) seul à atteindre 2K ; lent et cher, vidéos
  de référence facturées à la seconde. Max texte/image : plafond `768P`, `seed`, `promptExpansionMode`
  (`disabled`, `balanced`, `quality`) — `disabled` pour un prompt travaillé.
- [COÛT] Turbo = palier d'itération (mêmes entrées) : brouillon 480P sur Turbo, puis membre cher sur la
  prise gardée. Le brouillon valide composition et mouvement, pas les pixels finaux (autre membre ou
  résolution = nouvelle génération même seed).
- [PARAM] Extend (+Turbo) : ajoute 1 à 15 s ; source 1,625 à 60 s, ≤ 50 Mo, ratio 0,4 à 2,5 ;
  `output` `extended` (source + suite) ou `continuation` ; `referenceAudio` remplace la bande source comme
  guide ; `aspectRatio` autre que `auto` recadre ; 480P à 2K.
- [PIÈGE] `continuation` s'ouvre sur une copie des 1,625 dernières secondes de la source (39 images à
  24 i/s) puis dépasse un peu la demande (« 2 s gave 2.1 s, 3 s gave 3.5 s », facturé demandé) →
  couper à 1,7 s (1,6 garde une image source).
- [PROMPT] Extend : écrire ce qui se passe ENSUITE, jamais décrire la source ; `enablePromptExpansion`
  (défaut vrai) réécrit depuis la source.
- [PARAM] Insert Video : nouvelle scène 5 à 13 s puis reprise de l'original ; `startTime` et
  `resumeTime` requis (secondes source) ; `duration` = scène nouvelle seule ; ≤ 9 `referenceImages`,
  3 `referenceVideos` (facturées aux jetons) ; `colorMatch` actif par défaut ; `480p`/`768p` en minuscules.
- [PARAM] Recast : remplace jusqu'à 4 personnes d'après photos ; source 5 à 30 s, aucun plan > 15 s ;
  facturé PAR SECONDE DE SOURCE (rogner d'abord) ; une photo par personne, gauche→droite par défaut,
  prompt optionnel pour qui devient qui ; garde mouvement, caméra, coupes, audio ; `768P`/`1080P`.
  Mauvais outil pour un nouveau décor ou style.
- [PROMPT] Commandes caméra entre crochets dans le prompt : `[Push in]`, `[Pull out]`, `[Pan left]`,
  `[Tilt up]`, `[Truck right]`, `[Pedestal up]`, `[Zoom out]`, `[Shake]`, `[Tracking shot]`,
  `[Static shot]` ; jusqu'à 3 dans un crochet (`[Pan left, Pedestal up]`), crochets séparés = séquence.
- [PIÈGE] Plus de 2-3 indications de mouvement : fond qui ondule, textures qui scintillent. L'I2V dérive
  même sans demande → verrouiller (« Static camera, locked shot, tripod mounted »).
- [PROMPT] Reste en prose : caméra, sujet, action, scène, lumière/ambiance, style. Sur H3 le son vit dans
  le prompt (dialogues, SFX, ambiance), aucun paramètre audio.
- [PIÈGE] Casse des résolutions : H3 `768P`/`2K`, Insert `480p`/`768p`, Recast `768P`/`1080P`.

**Correspondance Deepotus.** h3-max (I2V, `prompt_expansion_mode` « balanced » forcé, résolutions
480p/768p/1080p en MAJUSCULES, seed) ; VFX minimax/h3-max/relight et insert-video. Écart à signaler :
la skill dit Max texte/image plafonné à `768P`, le registre Deepotus (OpenAPI fal relue) a 1080P →
re-vérifier. Manques modèles : H3 (non-Max, références + 2K + audio stéréo), H3 Max T2V, H3 Max
Reference, H3 Max lip-sync, Turbo (I2V / T2V), Extend (+Turbo), Recast, 2.3 (déprécié, à ne pas
ajouter). Tous probablement sur fal sous minimax/… Manques paramètres : `prompt_expansion_mode`
réglable (`disabled` pour prompts travaillés), 2K, références, `colorMatch`/`resumeTime` (vérifier la VFX insert).

**Propre à Scenario.** Ids `model_minimax-*`, cut au pas de 0,1 s de l'outil Scenario.

---

## 10. scenario-runway

**Résumé.** Runway : Gen4.5 génère (texte ou première image) ; Aleph 2 réécrit une vidéo réelle
(retirer, échanger, restyler, ré-éclairer) en gardant mouvement et audio. Famille : T2V, I2V, V2V.

**Faits utiles**
- [PARAM] Gen4.5 : `duration` 2 à 10 s ; `aspectRatio` en PAIRES DE PIXELS (`"1280:720"`, `"960:960"`),
  honoré seulement en 16:9 et 9:16 en mode texte ; autres formes (1:1, 4:3, 3:4, 21:9) via une première
  image de cette géométrie ; ratio ignoré avec `image`.
- [PROMPT] Mode texte : décrire visuel ET mouvement. Mode image : tout le prompt sur mouvement, caméra,
  atmosphère (ne pas re-décrire l'image).
- [PROMPT] Ordonner les temps explicitement (« kneels, then rises, camera cranes up ») ; multi-temps =
  8 à 10 s. Mouvements nommés simplement (locked camera, pan, dolly, tracking, orbit, crane), 1 ou 2
  par clip, prose au présent.
- [PARAM] Aleph 2 : source ≤ 30 s ET ≤ 16 Mo (limites séparées : les clips à fort débit butent sur la
  taille d'abord) ; jusqu'à 5 images de référence : `keyframes` (`uri` + `seconds` ou `at` 0-1) OU
  `promptImage` (`positionType` + `timestampSeconds`/`positionPercentage`), jamais les deux.
- [PROMPT] Aleph : énoncer l'édition (remove, swap, restyle, relight) ; tout ce qui n'est pas nommé
  persiste (« Keep everything else unchanged »). Aleph ne re-chorégraphie pas et n'ajoute pas de
  mouvement caméra → Gen4.5 si le mouvement doit changer.
- [COÛT] Aleph : coût médian 6× Gen4.5, écart de 15× selon la vidéo source ; latence médiane ~6 min.

**Correspondance Deepotus.** Aucun id Runway. Manques modèles : Gen4.5 I2V/T2V et Aleph 2 (présence sur
fal INCERTAINE — Runway passe surtout par son API propre ; à vérifier). Équivalents Deepotus d'Aleph :
VFX kling o3 edit, flux-3 edit-video, h3-max relight. Paramètres : `keyframes` d'édition épinglés dans le temps.

**Propre à Scenario.** Ids `model_runway-*`.

---

## 11. scenario-vidu

**Résumé.** Vidu (Shengshu) : un modèle par mode × palier (T2V, I2V, Reference2V ; Q3, Q2, Q1, 2.0),
15 membres. Famille : T2V, I2V, début→fin, références (jusqu'à 7), anime, amplitude de mouvement.

**Faits utiles**
- [PARAM] I2V : `generationType` `"image_to_video"` avec 1 image dans `images`, ou
  `"start_end_to_video"` avec 2 (ordre = début puis fin) ; le type DOIT correspondre au nombre d'images.
  Aucun I2V n'expose `aspectRatio` (géométrie des images).
- [PARAM] Reference2V : `images` jusqu'à 7 (identité, accessoires, palette), pas l'état d'ouverture.
  Q2 Pro seul prenait `videos` : jusqu'à 2 (une de 8 s ou deux de 5 s, 100 Mo, ratio 1:4 à 4:1).
- [PARAM] `seed` sur tous les membres. `audio` (défaut faux) = musique de fond, PAS du sound design ;
  sur la plupart des Q2, sans effet à 9-10 s.
- [PARAM] Paliers : Q3 1 à 16 s ; Q2 1 à 10 s (début/fin plafonné à 8) ; 2.0 I2V exactement 4 ou 8 s,
  8 seulement en 720p ; Q1 sans durée ni résolution ; 2.0 Reference2V sans durée.
- [PARAM] `movementAmplitude` (auto, small, medium, large) sur Q1 et 2.0 seulement ; `style` général/anime
  sur Q1 I2V seulement ; sur Q2/Q3 énergie et style dans le prompt. Turbo/Fast : moins de latence, mêmes plafonds.
- [COÛT] Durée et résolution multiplient le coût « several-fold on one member alone ».
- [PROMPT] T2V/I2V : paragraphe de 120 à 180 mots au présent, un seul plan : scène et lumière, 1-2
  mouvements, UN mouvement caméra en verbes simples, émotion en indices physiques (« her shoulders
  slump »), pas de coupe ; en I2V rien qui ne soit déjà dans l'image.
- [PROMPT] Reference2V : l'inverse, UNE phrase de 20 à 40 mots disant quel élément vient de quelle
  référence par position (« the character from image1 wearing the armor from image2… »).
- [PARAM] Longueur max du prompt 2000 à 5000 caractères selon membre.
- [PIÈGE] Pas de dialogue ni SFX à attendre (audio = musique seulement).

**Correspondance Deepotus.** Aucun id Vidu. Manques modèles : Vidu Q3 Pro (I2V, start-end, T2V),
Q2 Turbo/Pro, Reference2V (probablement sur fal sous fal-ai/vidu/…). Paramètres intéressants :
`movementAmplitude`, `style` anime, références multiples.

**Propre à Scenario.** Ids `model_vidu-*`.

---

## 12. scenario-luma-video

**Résumé.** Luma Ray : Ray 3.2 (texte ou images d'ancrage, boucle, HDR), Ray 3.2 Edit (restyle sous
contrôles structurels), Ray 3.2 Reframe (outpainting vers un autre ratio), Modify Video (éditions
budget). Famille : T2V, I2V début/fin, V2V.

**Faits utiles**
- [PARAM] Ray 3.2 : `duration` en chaîne avec unité `"5s"` ou `"10s"` ; `"10s"` refuse `loop`, `hdr`,
  `startFrame`, `endFrame`. `endFrame` seulement avec `startFrame`. `hdr` exige 720p ou 1080p (liste
  540p, 720p, 1080p) ; 6 ratios de 9:16 à 21:9.
- [COÛT] `duration`, `resolution`, `hdr` pèsent ; 1080p = plusieurs fois 720p en coût et attente.
- [PARAM] Échelle de force commune à 9 valeurs `adhere_1` … `reimagine_3` (adhere = proche, flex = restyle
  reconnaissable, reimagine = transforme) : `editStrength` sur Edit, `mode` sur Modify.
- [PARAM] Edit : guide `startFrame` OU `keyframes` (jusqu'à 64 couples image + index), bascules de
  conditionnement visage, pose, profondeur, normales, trajectoire, résolution, `hdr` ; ou
  `autoControls: true` à la place d'un `editStrength` manuel (exclusifs).
- [PARAM] Modify : `firstFrame` = copie éditée de la PREMIÈRE IMAGE DE LA SOURCE, pas une image de style ;
  source ≤ 30 s, 100 Mo ; pas de résolution.
- [COÛT] Edit vs Modify : écart proche de deux ordres de grandeur → payer Edit seulement si ses contrôles servent.
- [PROMPT] 50 à 300 mots de langage naturel autour du mouvement : sujet en pleine action, UN mouvement
  caméra nommé (slow push-in, handheld follow), UNE conséquence physique (gouttes, poussière) ; lumière
  concrète.
- [PROMPT] Avec `loop` : intensité de mouvement constante (pluie régulière, vapeur) pour que le cycle se ferme.
- [PROMPT] Reframe : décrire seulement les bords ajoutés, laisser le sujet d'origine.
- [PIÈGE] « vibrant », « whimsical », « hyper-realistic » dégradent la qualité dans cette famille.

**Correspondance Deepotus.** Aucun id Luma. Manques modèles : Ray 3.2 (I2V/T2V, boucle, HDR), Ray 3.2
Edit, Ray 3.2 Reframe, Modify Video (fal a eu luma-dream-machine ray-2 et modify ; Ray 3.2 à vérifier).
Équivalent Deepotus du Reframe : ltx-2.3/reframe (VFX). Paramètres absents : `loop`, `hdr`, échelle de force.

**Propre à Scenario.** Ids `model_luma-*`.

---

## 13. scenario-grok-imagine-video

**Résumé.** Grok Imagine (xAI) : Video 1.5 (texte + première image), 1.5 R2V (références), Edit Video,
Extend Video, + ancienne version non versionnée. Famille : T2V, I2V, R2V, V2V, audio natif non commutable.

**Faits utiles**
- [PARAM] Génération : 1 à 15 s, 1 à 4 `numOutputs`, 8 valeurs d'`aspectRatio` dont auto (texte →
  16:9 ; image → suit l'image). 1080p seulement en texte et première image de 1.5 ; R2V plafonné à 720p
  et « silently defaults to 480p ».
- [PARAM] R2V : ≤ 7 `referenceImages`, balises `@image1` (= `referenceImages[0]`, `<IMAGE_1>` marche
  aussi), une seule figure propre par référence (une référence chargée dilue le contrôle).
- [PARAM] Extend : 2 à 10 s NOUVELLES (`duration` = ajout). Edit : ni durée ni résolution ; source
  prétraitée à 8,7 s en 720p → rogner au segment d'abord.
- [PARAM] Aucun seed, négatif, ni paramètre caméra dans la famille. Ancienne version non versionnée :
  mêmes entrées, 720p max, moins chère.
- [CHOIX] `image` verrouille l'image 1 ; R2V porte personnes/produits/vêtements sans décider l'ouverture.
- [PROMPT] Audio natif sans paramètre : laissé sans consigne, la piste tend vers une musique générique →
  finir chaque prompt par des sons nommés (« Audio: rain on glass, distant traffic ») ou « no music »
  (NB : contredit la règle Seedance/générale — propre à Grok selon la skill).
- [PROMPT] Dialogue entre guillemets avec un verbe de diction → lip-sync (She says calmly: "We're live.").
- [PROMPT] Structure réalisateur : scène, caméra, style, mouvement, audio ; présent, un plan continu, UN
  mouvement dominant, actions physiques plutôt qu'émotions nommées ; « 80 to 150 words » touchant au
  moins trois couches. Édition : plus court, seulement ce qui change. Extension : pont (« the shot
  continues »), lumière et distribution conservées, audio redit.
- [PIÈGE] Directions contradictoires (« zoom in as the camera pulls back ») ou mouvements empilés.

**Correspondance Deepotus.** Aucun id Grok. Manques modèles : Grok Imagine Video 1.5 (I2V/T2V), R2V,
Edit, Extend (xAI grok-imagine-video présent sur fal à ma connaissance ; à vérifier). Paramètre notable :
`numOutputs` 1-4 (variantes en un appel).

**Propre à Scenario.** Ids `model_xai-*`.

---

## 14. scenario-gemini-omni

**Résumé.** Gemini Omni (Google), lignes Flash et 1.1 Flash : générateur texte/première image,
Reference-to-Video, Edit, Extend (1.1). Audio toujours généré. Famille : T2V, I2V (+fin en 1.1), R2V, V2V.

**Faits utiles**
- [PARAM] Générateur : `prompt` et/ou `image`, + jusqu'à 7 `referenceImages` optionnelles ; en 1.1
  `lastFrameImage` à côté d'`image` (exige la première image).
- [PARAM] R2V : 1 à 7 `referenceImages` requises, prompt optionnel ; en 1.1 une `referenceVideo` ≤ 3 s
  peut remplacer les images ou s'ajouter à 5 au plus.
- [PARAM] Edit : `video` + prompt de changement requis, 1 à 5 `referenceImages` optionnelles ; ni durée
  ni ratio (suit la source). Extend (1.1) : `video` requis, prompt optionnel, `duration` 3 à 10 (défaut 6)
  AJOUTÉE (« an 8 s clip plus 6 returns about 14 s »), pas d'`aspectRatio`.
- [PARAM] Générateurs : `duration` 3 à 10 (défaut 8), `aspectRatio` 16:9 ou 9:16. Flash d'origine 720p
  seulement ; 1.1 : `resolution` `360p` (brouillon rapide), `720p` défaut, `1080p` et `4k` SURÉCHANTILLONNÉS.
- [COÛT] Le palier ne change PAS le prix (même devis à 360p et 1080p, idem Extend) → un brouillon bon
  marché = durée plus courte, pas résolution plus basse. Coût selon durée, image de départ, références,
  clip source ; Edit = plus grand écart de coût et jobs ~2× plus longs.
- [PARAM] Ni seed ni négatif dans la famille.
- [PROMPT] Pas d'interrupteur audio : terminer par une ligne audio explicite (« crackling campfire,
  distant owls »), répliques entre guillemets ; sinon le modèle choisit. Sur Edit, NE PAS prompter
  l'audio (régénéré pour coller au nouveau look).
- [PROMPT] R2V : l'identité vient des images ; re-décrire l'apparence combat les images → dire « the
  character » / « the product » et dépenser les mots sur action, décor, caméra, son. Plusieurs angles
  d'un sujet resserrent la tenue ; sans prompt, les sujets apparaissent quand même.
- [PROMPT] Edit : mener par le changement (« make it winter », « swap the red car for a vintage blue
  Beetle »), cible concrète ; jamais de nouvelle chorégraphie, coupe ou mouvement caméra.
- [PROMPT] Avec une image de départ : décrire le mouvement qui la prolonge, pas une scène statique.
- [PIÈGE] Histoire multi-scènes en un run : 3-10 s tiennent UN temps continu ; au-delà Extend ou montage.
- [CHOIX] Générateur Flash classé premier en T2V au vote public ; 1.1 classé plus bas dans la recherche
  alors que plus récent → choisir par id et description, pas par rang.

**Correspondance Deepotus.** gemini-omni-flash (fal, v1.1 I2V), gemini-omni-flash-google. Écart
important : pricing.py chiffre 720p 0,10 $/s et 1080p 0,15 $/s (fal) / 0,11 et 0,15 (Google), alors que la
skill dit que le palier ne change pas le prix chez Scenario → à re-vérifier côté fal/Google (le prix peut
différer par revendeur). Rappel : 1080p et 4k sont suréchantillonnés. Manques modèles : Gemini Omni R2V,
Edit, Extend 1.1, T2V (probablement aux côtés de l'endpoint fal google/gemini-omni-flash/v1.1/…).
Manques paramètres : `referenceImages` à côté de l'image de départ, 360p (brouillon), 4k ; audio natif
non coupable → Deepotus ne peut pas le « couper » (`audio_param: None`) : la pipeline doit remplacer la piste.

**Propre à Scenario.** Ids `model_google-omni-*`.

---

## Règles transverses à reporter dans toutes les fiches vidéo Deepotus

1. I2V : prompt = mouvement, caméra, timing, ligne son ; ne pas re-décrire l'image (Wan, Runway, Vidu,
   Gemini, scenario-video).
2. UN mouvement caméra dominant, UNE action par plan ; plusieurs temps = horodatages dans la durée.
3. Image de fin seulement avec image de départ ; ratio ignoré dès qu'il y a une image de départ
   (Seedance, H3, Runway, Vidu, Wan 2.7) — cohérent avec `ratios: None` de plusieurs entrées.
4. Ouverture exacte → image de départ ; identité → références (jamais l'inverse).
5. Pas de texte lisible généré ; exclusions « no subtitles, no on-screen text ».
6. Audio natif : nommer les sons positivement, jamais « no music » (sauf Grok où la skill le conseille) ;
   pour Deepotus qui coupe l'audio, ce point devient : modèles SANS interrupteur (h3-max, gemini-omni,
   kling-v4, kling-v3-turbo-pro) livrent une piste à remplacer.
7. Continuation : dernière image → nouvelle image de départ, prompt écrit d'après l'image réelle.
8. Brouillon bon marché puis final : Seedance draft (finalisation même prise), Turbo MiniMax (composition
   seulement), Gemini (durée courte, pas résolution basse), Kling Standard puis upscale (pas re-rendu 4K).

---

## Tableau récapitulatif

| Skill | Ids Deepotus touchés | Nb faits | Manques (modèles) | Manques (paramètres) |
| --- | --- | --- | --- | --- |
| scenario-video | tous les ids vidéo, kling-lipsync, topaz | 27 | lip-sync autres que Kling, avatar image+audio, doublage, audio2video chanson | image/audio de référence, syncMode, activeSpeaker, keyterms |
| scenario-seedance | seedance-v1-pro, -2, -2-fast, -2.5, seedance-2.5-v2v | 22 | Seedance 2.5 R2V, 2.5 draft/complete, 2.0 Mini, 2.5 T2V | referenceImages/Videos/Audio, draft, 1080p 2.5, 4k 2.0, extension |
| scenario-seedance-drafts | seedance-2.5 | 17 | endpoint draft + draft-complete | draft, variantes parallèles, conservation id 7 j |
| scenario-seedance-storyboard | seedance-2.5, seedance-2 (début+fin), gpt-image-2, nano-banana-pro | 30 | Seedance 2.5 R2V (voie scriptée) | referenceImages, aspectRatio en référence, max_length prompt |
| scenario-seedance-music-video | seedance-*, music_service, htdemucs | 19 | analyse de structure du morceau, transcription de paroles chantées | gain son des plans, poignée de coupe, détecteur de coupes |
| scenario-kling | kling-v3-pro/-standard/-turbo-pro, kling-v4, kling-lipsync, kling o3 edit | 18 | V3 Omni, V3 4K, O1 (I2V/Ref/Edit), 2.6, Motion Control, AI Avatar | multiPrompt/shotType, middle_image_urls, elements, cfgScale, videoReferenceType, characterOrientation, 4K |
| scenario-veo | veo-3.1-fal/-fast-fal/-lite-fal, *-google (retirés), veo extend | 11 | Veo 3.1 T2V, R2V sur fal | referenceImagesType ASSET/STYLE, audio SFX:/Ambient noise:, garde 16:9 Extend / 8 s référence |
| scenario-wan | wan-3.0 (indirect) | 16 | Wan 2.7 Video Edit, 2.2 Animate Move/Replace, Reframe, Outpainting, 2.6 multi-plan | negativePrompt (wan-3.0), enablePromptExpansion, audio uploadé lip-sync |
| scenario-minimax-video | h3-max, VFX h3-max relight/insert | 19 | H3, H3 Max T2V/Reference/lip-sync, Turbo, Extend(+Turbo), Recast | prompt_expansion_mode réglable, 2K, références, écart 768P vs 1080P à vérifier |
| scenario-runway | aucun | 9 | Gen4.5, Aleph 2 (fal incertain) | keyframes d'édition épinglés |
| scenario-vidu | aucun | 11 | Q3 Pro, Q2 Turbo/Pro, Reference2V | movementAmplitude, style anime, références multiples |
| scenario-luma-video | aucun (reframe ≈ ltx-2.3) | 12 | Ray 3.2, Ray 3.2 Edit, Ray 3.2 Reframe, Modify Video | loop, hdr, échelle adhere/flex/reimagine |
| scenario-grok-imagine-video | aucun | 12 | Grok Imagine Video 1.5, R2V, Edit, Extend | numOutputs 1-4 |
| scenario-gemini-omni | gemini-omni-flash, gemini-omni-flash-google | 16 | Omni R2V, Edit, Extend 1.1, T2V | referenceImages + image, 360p, 4k ; prix par résolution à re-vérifier |
