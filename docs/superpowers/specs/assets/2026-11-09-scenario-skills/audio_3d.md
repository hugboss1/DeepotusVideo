# Lot audio_3d — fiches modèle tirées des skills Scenario (scenario-labs/skills b96506d)

Lot : 16 skills (5 audio, 11 3D / mondes / textures / mouvement). Sources lues en entier : chaque
SKILL.md, plus references/ de scenario-patina-retexture (materials-manifest.md, film-config.md,
example-config.json), scenario-walkable-room (calibration.md, objects.md, viewer.md) et le README de
scenario-orbit-views. Registres Deepotus recoupés : dz/music_service.py (MUSIC_MODELS),
dz/elevenlabs_service.py (ELEVEN_MODELS), dz/sfx_service.py (SFX_MODELS), dz/stems_service.py,
dz/pricing.py (asset3d, meshy, uthana, tripo_segment), dz/catalogue_ia.py.

Rappel : les chiffres Scenario sont « at authoring time » et passent par l'API Scenario ; les noms de
champ (camelCase) sont ceux de Scenario, pas forcément ceux de fal (snake_case). Les noms fal cités
ci-dessous viennent des registres Deepotus.

---

## 1. scenario-audio (skill transverse audio)

**Résumé.** Carte de l'audio Scenario : trois voies de génération (musique, SFX, voix) + vidéo→son +
utilitaires (couper, scinder, extraire, composer) + stems. Règles transverses pour la parole, les
chansons et l'extension de morceau. Famille : txt2audio, audio2audio, video2audio.

**Faits**
- [PROMPT] SFX : nommer la source, la matière, l'action et l'espace acoustique, puis ce qu'il faut exclure (« no music », « no reverb »).
- [PROMPT] SFX : un seul événement par clip ; les variantes = runs séparés, pas plusieurs événements dans un prompt.
- [PROMPT] Musique courte (nappe) : genre, humeur, tempo, instrumentation dans un seul prompt ; durée/boucle dans les paramètres.
- [PROMPT] TTS : le champ texte ne porte QUE les mots à dire ; voix, langue, émotion, rythme vont dans des champs dédiés ou des balises inline.
- [PIÈGE] « say this angrily » dans le texte TTS : la consigne peut être prononcée. Utiliser les champs émotion/voix.
- [PIÈGE] Syntaxe des balises propre à CHAQUE modèle, même dans une famille : crochets `[whispers]`, chevrons `<sigh>`, parenthèses `(sighs)`, paires `<whisper>…</whisper>` ; certains n'en lisent aucune. Une balise mal orthographiée est lue à voix haute → copier la grammaire de la description du champ texte ; sans source, ne pas mettre de balise.
- [PIÈGE] Une balise juste est une demande, pas une garantie : deux runs identiques ont divergé. Faire écouter avant de valider, relancer si la balise a été ignorée.
- [PARAM] Dialogue multi-locuteurs : tableau de locuteurs, « up to 2 rows of a speaker label and a voice » ; texte en tours `Nom: réplique`, `Nom` = libellé exact ; ligne sans préfixe = suite du tour précédent ; le champ voix unique est ignoré dans ce mode.
- [MÉTHODE] Les noms de voix préréglées ne disent rien du genre/âge/ton : annoncer quelle voix joue qui et faire confirmer avant le run payant. Plus de 2 locuteurs → découper en prises de 2 max.
- [PARAM] Texte TTS plafonné : « 5000 characters on one member » ; dépassement = 400 (pas de troncature) ; c'est le facteur de prix → découper un long script aux frontières de tours et chiffrer la 1re prise.
- [PARAM] Langue : passer par le champ langue du schéma plutôt que la nommer dans le texte.
- [PROMPT] Chanson : le champ style porte genre, humeur, tempo, tonalité, style vocal, instrumentation ; le champ paroles porte les mots avec balises `[Verse]`, `[Chorus]`. Jamais de paroles dans le style (le modèle décrit une chanson au lieu de la chanter).
- [PARAM] Instrumental et paroles auto = DRAPEAUX quand ils existent ; demander en prose est peu fiable.
- [PIÈGE] Basculer le drapeau instrumental sur une relance donne une autre prise, pas « la même chanson sans voix » ; `seed` ne reproduit qu'à réglages identiques. Pour l'instrumental d'un morceau existant : modèle de cover audio2audio.
- [PARAM] Champs texte plafonnés par modèle et par champ ; dépassement = 400.
- [COÛT] Si un champ durée existe, il plafonne longueur ET prix ; sinon la feuille de paroles fixe les deux. Chiffrer avant, lancer en asynchrone (jobs de plusieurs minutes).
- [PARAM] Reproductibilité/lot selon le modèle : les « repaint » avaient `numOutputs` 1–4 et pas de seed ; les compositeurs par sections avaient `seed` et pas de `numOutputs`. Lire les deux avant de promettre.
- [MÉTHODE] Garder le même chanteur sur un repaint : lancer en lot (numOutputs) et choisir, pas relancer.
- [CHOIX] « Rallonger un morceau » = voie audio2audio d'extension (morceau + tableau `sections` ordonné, « up to 30 », chaque section garde une tranche source `sourceStartSeconds/sourceEndSeconds` ou génère `text` + `durationSeconds` + `positiveStyles`, `contextAdherence`). Ni repaint (durée conservée), ni nouveau text-to-music (perd le morceau).
- [COÛT] Extension : les tranches conservées sont facturées comme de l'audio généré de même durée.
- [PARAM] Stems : un stem nommé par run, voix comprise, pas d'option « instrumental » ; l'isolation de voix ne rend jamais le reste en 2e piste → un split voix/reste est un manque à signaler.
- [PIÈGE] WAV : se demande à la génération (champ format de sortie), pas par conversion au téléchargement.

**Correspondance Deepotus**
- Ids touchés : tout MUSIC_MODELS, ELEVEN_MODELS (eleven_multilingual_v2, eleven_v3, eleven_flash_v2_5), SFX_MODELS (elevenlabs-direct, elevenlabs-v2-fal, sonilo-1.1, mirelo-1.6, stable-audio-3-sfx, sonilo-video, mirelo-video, kling-v2a, hunyuan-foley, thinksound), stems htdemucs.
- Manques modèles : extension de chanson par sections (ElevenLabs Music Advanced / ACE-Step extend — non vérifié fal) ; TTS dialogue multi-locuteurs (Eleven v3 dialogue, probablement sur fal) ; speech-to-speech / voice changer ; dubbing ; transcription (Deepotus a peut-être Whisper ailleurs, hors registre lu).
- Manques paramètres : aucun champ « tableau de locuteurs » ; pas de `loop` exposé à l'écran (nommé mais jamais envoyé côté elevenlabs-v2-fal) ; pas de choix de format de sortie audio dans l'UI musique (elevenlabs-music fixe mp3_44100_128) ; pas de `numOutputs` musique.

**Propre à Scenario.** recommend/search/model_schema_get/model_run(dry_run, wait)/jobs_wait/asset_display et les utilitaires `model_scenario-audio-*` / `compose-video` : ne se transposent pas (Deepotus a ffmpeg local).

---

## 2. scenario-ace-step (ACE-Step 1.5)

**Résumé.** Famille de production musicale ACE-Step 1.5 : 9 membres, un par mode (Text to Music, Cover,
Repaint en Turbo et Quality ; Add Layer, Complete Track, Stem Extract en Quality seul). Famille :
chanson chantée / instrumental, édition audio.

**Faits**
- [PARAM] Text to Music : `prompt` ou `lyrics` (l'un suffit) ; `duration` « 10 to 600 s (empty lets the model pick) » ; `bpm`, `keyscale` (ex. « C Major »).
- [PROMPT] `prompt` = légende de style d'une ligne (genre, humeur, instruments, production) ; plafonné « it caps at 512 characters » ; les mots vont dans `lyrics`.
- [PROMPT] Feuille de paroles : `[Verse]`, `[Chorus]`, consigne DANS la balise `[Bridge - whispered]`, chœurs entre (parenthèses), MAJUSCULES pour les lignes chantées à pleine voix.
- [PARAM] Sans voix = `instrumental: true`, pas « no vocals » dans la légende. Tempo et tonalité dans `bpm`/`keyscale`, pas dans le texte.
- [PARAM] Communs : `numOutputs` 1–4 (multiplie le coût), `thinking` (défaut true, passe de planification ; absent sur Stem Extract), `vocalLanguage` (défaut auto-détection). `guidanceScale` seulement sur le trio d'édition.
- [PARAM] AUCUN `seed` exposé dans la famille : deux repaints de la même fenêtre = deux prises, le chanteur peut changer. Faire des lots (`numOutputs`) et choisir.
- [PARAM] Stems / pistes : 12 valeurs fixes (vocals, backing_vocals, drums, bass, guitar, keyboard, percussion, strings, synth, fx, brass, woodwinds) — jamais de texte libre (« kick drum » refusé).
- [PARAM] Cover : `srcAudio` (+ `referenceAudio` qui donne genre/feel), `audioCoverStrength` : proche de 1 = fidèle à l'arrangement ; 0,5–0,6 = change de genre, le hook survit ; ~0,2 = n'emprunte que l'ambiance.
- [PARAM] Repaint : `repaintingStart`/`repaintingEnd` (secondes), `repaintingEnd: -1` = jusqu'à la fin ; durée totale conservée.
- [MÉTHODE] Changer des paroles chantées par Repaint : `prompt` qui commence par « Repaint the selected section with new sung lyrics: », `lyrics` = feuille COMPLÈTE avec la nouvelle section en place, `thinking: false`. Les trois ensemble. La voix de la section sera une nouvelle prise.
- [MÉTHODE] Corriger une ligne en gardant la voix : Cover avec `srcAudio` = prise entière, `lyrics` corrigées, `audioCoverStrength` 1, `numOutputs` jusqu'à 4 → écouter, localiser les bornes, couper la portion corrigée et la raccorder au master localement (ffmpeg). Aucune garantie de mots/voix/timing ; une différence de forme d'onde ne prouve rien.
- [PARAM] Add Layer : `srcAudio` + `trackName` + `prompt`, ajoute un stem calé en tonalité/tempo/groove, fenêtrable.
- [PARAM] Complete Track (Vocal2BGM) : `srcAudio` + `completeTrackClasses` + `prompt` ; marche mieux sur une source à mélodie et rythme nets.
- [CHOIX] Turbo = distillé, rapide, « costs half as much » ; Quality = checkpoint complet (fidélité, adhérence). Mêmes paramètres sauf `audioFormat` (mp3/wav/flac, seulement sur Repaint Turbo).
- [COÛT] Itérer en Turbo (paroles, structure, fenêtres), puis rejouer les paramètres retenus sur Quality. `duration` et `numOutputs` font le prix.
- [PIÈGE] Repaint ne change pas la longueur ; une version plus longue = voie d'extension (autre famille) ; une autre longueur = nouveau Text to Music.

**Correspondance Deepotus**
- Id touché : `ace-step` (fal-ai/ace-step, ACE-Step 1re génération : `tags` requis, pas de `prompt`, durée 5–240, seed oui, 0,0002 $/s).
- Manques modèles : ACE-Step 1.5 (Turbo/Quality), et ses modes Cover, Repaint, Add Layer, Complete Track, Stem Extract (fal a historiquement des endpoints ace-step audio-to-audio / extend / inpaint — probablement dispo, à vérifier).
- Manques paramètres : `bpm`, `keyscale`, `vocalLanguage`, `thinking`, `numOutputs`, `instrumental` explicite (registre dit instrumental True mais via tags), `audioFormat`.
- Note : Deepotus ace-step a une seed (v1), la 1.5 Scenario n'en a pas — ne pas promettre la reproductibilité si on migre.

**Propre à Scenario.** Ids `model_ace-step-1-5-*`, dry_run/jobs_wait, `model_scenario-audio-cut` : non transposables.

---

## 3. scenario-elevenlabs (ElevenLabs)

**Résumé.** 11 membres ElevenLabs, un job chacun : TTS (v3, Multilingual 2, Turbo 2.5), musique
(Music v2, Music Advanced v2), SFX (Sound Effects 2), Dubbing (v2 et ancien), Speech to Speech,
Voice Changer, Voice Isolator. Famille : voix, musique, SFX, doublage, transformation.

**Faits**
- [CHOIX] Parole expressive / dialogue → Eleven v3 (balises inline) ; narration à langue fixée → Multilingual 2 (`languageCode`) ; parole rapide/en masse → Turbo 2.5 (même forme, moins cher).
- [PROMPT] Eleven v3 lit des balises inline `[whispers]`, `[excited]`, `[sighs]` pour piloter le jeu instant par instant, sur « 70+ languages », et porte le dialogue multi-locuteurs.
- [PIÈGE] Multilingual 2 et Turbo 2.5 NE lisent PAS les balises (risque de lecture à voix haute) : la direction passe par `stability`, `styleExaggeration`, `speed` (0,7–1,2) ; `languageCode` ISO 639-1 (champ absent sur v3).
- [COÛT] Turbo ≈ « roughly half the other two per run ».
- [PARAM] Contrat voix commun : `voiceId` (voix clonée) gagne toujours ; `publicVoice` (21 préréglages) ignoré à côté ; rien = voix Adam.
- [PARAM] TTS : texte jusqu'à « 40,000 characters » (sur un membre) ; WAV seulement sur les membres TTS ; ailleurs MP3/Opus.
- [PARAM] `seed` pour la reproductibilité, SAUF Sound Effects 2, les deux Dubbing et Voice Isolator.
- [PARAM] Music v2 : `prompt` (humeur, genre, instruments, tempo), `durationSeconds` « 3 to 600 », `forceInstrumental` (la prose est peu fiable).
- [PARAM] Music Advanced v2 : `sections` obligatoire, « up to 30 », chacune `text`, `durationSeconds` 3–120, `positiveStyles`/`negativeStyles` (≤ 10 chacun), `contextAdherence` (haut = lié aux voisines).
- [PROMPT] Grammaire des sections : [crochets] = étiquette ([Verse]), {accolades} = consigne ({soft piano intro}), texte brut = chanté. Pas de drapeau instrumental sur Advanced : tout texte brut sera chanté.
- [PARAM] Aucune musique ElevenLabs n'a `numOutputs` : plusieurs prises = runs parallèles avec seeds distinctes (même coût, fichiers séparés). Deux `[Verse]` dans un run ≠ deux prises.
- [PIÈGE] Même seed + mêmes réglages = même musique ; relancer sans changer la seed ne donne pas une autre prise.
- [PARAM] Sound Effects 2 : `text`, `promptInfluence`, `loop`.
- [PARAM] Dubbing : `file` audio ou vidéo + `targetLang` requis ; vidéo en entrée → vidéo doublée en sortie. Auto-détection source : `sourceLang: "auto"` sur v2, chaîne vide sur l'ancien.
- [CHOIX] Dubbing v2 pour `keyterms` (noms, marques, jargon gardés tels quels) ; ancien Dubbing pour `numSpeakers` (0 = auto, jusqu'à 10), `dropBackgroundAudio`, `disableVoiceCloning`, `highestResolution`. Prix « differ several-fold ».
- [PIÈGE] Le doublage ne refait pas les lèvres : la piste change, l'image non.
- [PARAM] Speech to Speech / Voice Changer / Voice Isolator : `audio` seul (« up to 5 min »), pas de vidéo malgré les descriptions → extraire la piste, traiter, remuxer avec la vidéo muette.
- [PARAM] Voice Changer = Speech to Speech + `stability`, `similarityBoost`, `styleExaggeration`, `useSpeakerBoost`.
- [COÛT] Le coût suit le contenu : texte (TTS), `durationSeconds` (Music v2), `sections` (Advanced), durée de `file`/`audio` (doublage, voix).
- [PIÈGE] Ne pas transporter les plafonds d'un membre à l'autre (40 000 caractères, 600 s, 30 sections, 5 min sont chacun vrais d'une voie seulement).

**Correspondance Deepotus**
- Ids touchés : eleven_multilingual_v2 (max_chars 10 000, stability/similarity_boost/style/speed), eleven_v3 (max_chars 5 000, stability discrète 0/0,5/1), eleven_flash_v2_5 (40 000) ; elevenlabs-music-2.5 (fal elevenlabs/music/v2.5, 3–600 s, force_instrumental, seed) ; SFX elevenlabs-direct et elevenlabs-v2-fal (0,5–22 s, prompt_influence, loop) ; isolation de voix (pricing « isolate »).
- Écarts : Scenario cite « Turbo 2.5 », Deepotus a Flash v2.5 (successeur/équivalent bas coût) ; Scenario Music v2 vs Deepotus Music 2.5.
- Manques modèles : Music Advanced v2 (sections) — sur fal ? probablement via elevenlabs/music avec composition plan, à vérifier ; Dubbing v2 et Dubbing ; Speech to Speech / Voice Changer ; dialogue v3 multi-locuteurs (fal a « elevenlabs/text-to-dialogue/eleven-v3 » probablement).
- Manques paramètres : `languageCode` sur Multilingual/Flash (Deepotus passe la langue via la voix persona, pas le code ISO) ; `use_speaker_boost` ; `seed` TTS ; balises v3 non documentées dans l'UI ; `loop` SFX non exposé ; format WAV TTS (Deepotus fixe mp3_44100_128) ; `sections`/`negativeStyles` musique.

**Propre à Scenario.** Ids `model_elevenlabs-*`, upload_asset, `model_scenario-audio-extract`/`compose-video` : non transposables.

---

## 4. scenario-minimax-music (MiniMax Music 3.0 + Music Cover)

**Résumé.** Music 3.0 compose et chante une chanson complète (style + paroles), Music Cover reconstruit
un morceau téléversé dans un autre style en gardant la mélodie. Famille : chanson chantée,
instrumental, cover.

**Faits**
- [PARAM] `prompt` requis sur les deux, « 10 to 2,000 characters », STYLE seulement : genre, humeur, BPM, tonalité, timbre vocal, instrumentation.
- [PARAM] `lyrics` « up to 3,500 characters » ; c'est aussi la facture : « about 700 characters per billable minute », 1 à 5 minutes.
- [PROMPT] Balises de structure sur leur propre ligne : [Intro], [Verse], [Pre Chorus], [Chorus], [Hook], [Drop], [Bridge], [Inst], [Outro] (+ d'autres dans le schéma).
- [PROMPT] Saut de ligne = nouvelle ligne chantée ; ligne vide entre sections = pause ; 2 à 4 lignes par section chantent mieux qu'un paragraphe dense.
- [PROMPT] (Parenthèses) = indications de jeu, pas des mots chantés : (whispered), (belted), ou consigne courte dans [Inst]/[Solo].
- [PROMPT] Finir par [Outro] pour que le morceau se résolve au lieu de couper.
- [PROMPT] Anglais et mandarin chantent le plus régulièrement.
- [PARAM] `lyricsOptimizer: true` inverse le sens du champ : on y met un BRIEF en langage courant et le modèle écrit la feuille. Sans le drapeau, il chante ce que contient le champ (brief compris).
- [PIÈGE] Des paroles finies avec `lyricsOptimizer: true` sont réécrites.
- [PARAM] Instrumental : `isInstrumental: true` (pas « no vocals » en prose) ; le prompt est alors tout le brief.
- [PIÈGE] Faux passages instrumentaux avec des mots de remplissage → utiliser [Inst]/[Solo] + indication entre parenthèses.
- [CHOIX] Cover : garde la ligne mélodique, régénère genre/voix/instruments/production → changement de genre, pas un remix qui change l'air ; marche mieux avec voix et mélodie nettes ; pas de champ paroles (le prompt change le style, jamais les mots).
- [COÛT] Cover = prix fixe par run ; 3.0 = proportionnel à la feuille → comparer.
- [PARAM] Partagés : `prompt`, `sampleRate`, `bitrate`. Jobs de plusieurs minutes (asynchrone).
- [PIÈGE] Paroles dans `prompt` ou genre dans `lyrics` : il décrit une chanson ou chante votre brief.

**Correspondance Deepotus**
- Ids touchés : minimax-music-20 (v2 : prompt 10–2000 + lyrics_prompt 10–3000 requis), minimax-music-26 (v2.6, instrumental oui), minimax-music-3 (minimax/music-3 : prompt + lyrics requis, duration 1–300, seed). Mureka-9.5 partage le style de balises.
- Écart : le plafond paroles Deepotus `_MAX_LYRICS = 3500` concorde avec Scenario ; minimax-music-3 Deepotus marque instrumental False alors que Scenario 3.0 a `isInstrumental`.
- Manques modèles : MiniMax Music Cover (audio2audio) — probablement sur fal (minimax music cover / v2.x cover), à vérifier.
- Manques paramètres : `lyricsOptimizer` (paroles auto), `isInstrumental` sur music-3, `sampleRate`, `bitrate` ; logique de coût « 700 caractères par minute » absente du devis (prix à 0 « à mesurer »).

**Propre à Scenario.** `model_minimax-music-3-0`, upload_asset → asset id : non transposable (fal prend une URL).

---

## 5. scenario-sonilo (Sonilo V1.1)

**Résumé.** Famille SFX + musique instrumentale, sur deux axes : nature du son (SFX ou musique) et
retour (piste seule ou vidéo source avec la piste mixée, image intacte). Six membres. Famille :
txt2audio, video2audio, video2video.

**Faits**
- [CHOIX] Choisir le membre selon la LIVRAISON (piste nue vs clip fini) avant tout prompt.
- [PARAM] Text to SFX : `prompt`, `duration` « 1 to 180 seconds (default 8) », `audioFormat` (aac défaut, mp3, wav, flac ; wav/flac pour un pipeline de montage).
- [PARAM] Text to Music : `prompt`, `duration` « 1 to 600 (default 90) », `numSamples` 1–3.
- [PARAM] Vidéo en entrée « up to 360 seconds » ; `segments` jusqu'à 50 ; `startOffset` par pas de 10, `startOffset + duration` ≤ durée vidéo.
- [PARAM] `audioFormat` n'existe que sur les membres SFX ; sur le membre muxé il formate la piste séparée, l'audio de la vidéo reste AAC.
- [PROMPT] Sur les membres vidéo, l'image décide QUAND le son arrive, le prompt seulement À QUOI il ressemble ; l'audio d'origine du clip n'oriente jamais la génération.
- [PROMPT] Prompt vide valide et souvent le meilleur : le modèle légende le clip et couvre chaque scène.
- [PARAM] `segments` = prompts par plage, contigus : premier `start` = 0, chaque `end` = `start` suivant, dernier ≤ fin de vidéo. Plages trouées/chevauchantes = erreur.
- [PROMPT] Text to SFX sans contrôle temporel : un événement par run ; mots physiques plutôt qu'humeurs (hollow, muffled, punchy) ; ordre source → matière → espace → intensité ; intention de durée dans le texte ET dans le paramètre.
- [PARAM] Aucun membre n'a de seed : archiver les prises ; en musique `numSamples` donne jusqu'à 3 prises en un run.
- [PARAM] Membres « music mux » : remplacent toute la piste d'origine par défaut ; `keepSpeechVocal: true` isole la voix humaine (dialogue, narration, chant, foules) et y glisse la musique en ducking ; tout le non-vocal (moteurs, pas, ambiance, foley) est remplacé.
- [PIÈGE] Ne jamais scorer un clip après y avoir mixé du foley (le foley disparaît) : générer pistes SFX et musique séparées et mixer en post.
- [PIÈGE] `keepSpeechVocal` à false (défaut) sur un face-caméra : la narration disparaît.
- [PIÈGE] Aucun membre ne fait de parole, narration ou chant ; musique toujours instrumentale.
- [COÛT] Chaque bouton de durée coûte ; le coût suit la durée du clip.

**Correspondance Deepotus**
- Ids touchés : sonilo-1.1 (sonilo/v1.1/text-to-sound-effects, 0,5–180 s, défaut 8, audio_format wav fixe) ; sonilo-video (video-to-sound-effects, keep_speech_vocal nommé « voix »).
- Manques modèles : Sonilo Text to Music, Video to Music, Video to Video SFX, Video to Video music (mux) — même éditeur sur fal, probablement dispo (sonilo/v1.1/...), à vérifier.
- Manques paramètres : `segments` (prompts par plage), `numSamples`, `startOffset`, `duration` sur la voie vidéo ; choix du format (wav figé) — acceptable.
- Note : Deepotus envoie `keep_speech_vocal` sur video-to-sound-effects ; Scenario ne le cite que sur le membre music mux → vérifier le schéma fal.

**Propre à Scenario.** Ids `model_sonilo-*`, upload_asset : non transposables.

---

## 6. scenario-3d (skill transverse 3D)

**Résumé.** Chaîne 3D : image concept → image-to-3D → (UV, retexture, remesh) → rig/animation,
avec règles de budget polygonal, formats et textures. Couvre Hunyuan 3D, Meshy, Tripo, Trellis et les
membres « LLM-based » (GPT-6 Astra 3D, Claude Opus 5.5 3D). Famille : txt23d, img23d, 3d23d.

**Faits**
- [CHOIX] Préférer concept image puis image-to-3D au text-to-3D : catalogue plus large, plus de direction artistique.
- [PROMPT] Concept : un seul sujet centré sur fond uni.
- [PROMPT] Créature non bipède : à hauteur d'œil, de profil ou trois-quarts, toutes les pattes visibles et détachées du corps ; une vue de dessus cache le dessous des pattes et la hauteur du corps.
- [PROMPT] Bipède destiné au rig : T- ou A-pose, corps entier, vue de face, bras écartés du torse, fond uni.
- [PIÈGE] Référence sur fond chargé : le détourage garde les reflets du décor sur un sujet brillant, que l'image-to-3D cuit dans la texture → préférer une référence sur fond uni ; sinon détourer d'abord. Un sujet isolé compte, une découpe transparente non.
- [PARAM] Budget prop jeu : « Target 10k to 50k triangles » ; ne jamais supposer que les défauts y tiennent. Un nombre de quads n'est pas un nombre de triangles.
- [PARAM] Contrôles de faces : Tripo `faceLimit` et Meshy `targetPolycount` couvrent toute la plage (à 10k, une araignée a gardé pattes et griffes, un coffre son cadenas) ; Meshy Smart Topology plafonne à 15k ou 30k ; Hunyuan 3D `faceCount` « from 40k » ; Trellis `decimationTarget` « from 100k ». Remesher seulement sous le plancher du modèle.
- [PARAM] Membres LLM-based (GPT-6 Astra 3D, Claude Opus 5.5 3D) : 1 à 8 photos/rendus → maillage éditable à pièces nommées + PBR par pièce ; pour props et hard-surface, PAS personnages/créatures ; prix par `buildEffort` (standard, high défaut, maximum) ; `faceBudget` plafonne les triangles exportés.
- [COÛT] Ordre de grandeur : un membre LLM « 1,300 CU at its default effort », un générateur Tripo mono-image « 45 ».
- [PARAM] Text-to-3D LLM : nommer les pièces voulues dans le prompt (« lid », « body », « padlock » sont revenus comme noms de nœuds).
- [PARAM] Édition de maillage LLM : `sceneFile` = maillage, `images` vide, `prompt` = changement ; `buildEffort` standard pour une recoloration, high/maximum pour ajouter/remodeler.
- [PIÈGE] Recoloration : garde noms de pièces et nombre de faces. Remodelage non plafonné (`faceBudget` ignoré) : « a 4,817-triangle cat to 788,954 » → prévoir un remesh. Un matériau remplacé garde son ancien nom.
- [PARAM] Multi-vues Tripo : `leftImage` = gauche DU PERSONNAGE (nez vers la gauche du cadre) ; une planche étiquetée côté spectateur les inverse ; une paire inversée peut fusionner face et dos en une coque.
- [PARAM] Tripo `texture: false` = maillage nu, moins cher (texturer dans un DCC) ; `textureQuality` change le prix.
- [PARAM] `delight` retire l'éclairage cuit de la référence (défaut on) ; ne l'éteindre que si l'ombrage peint est le style. L'export reste un matériau éclairé ; « unlit » se règle à l'import.
- [PARAM] `pbr` : défaut off sur Tripo P2 (on force la texture, facturée), on sur 3.1 et le membre de texturage, qui ignorent alors les paramètres de texture.
- [PARAM] Seeds séparées géométrie/texture (`seed`, `textureSeed`) : garder `seed` + image, varier `textureSeed` pour des variantes de texture sur une même forme.
- [PARAM] `autoSize` (défaut off) met à l'échelle réelle en mètres ; les mètres sont dans la transformation de nœud du GLB, les dimensions lues restent normalisées (côté long 1,0) — pas une erreur.
- [PARAM] Pas de symétrie exposée chez Tripo : un résultat différent de l'app du fournisseur peut venir d'un réglage réservé à l'app.
- [MÉTHODE] Chaîne vers game-ready : 1) géométrie (multi-vues si possible, `texture: false`, `pbr: false`) 2) dépliage UV 3) retexture du maillage déplié 4) rig en dernier, sur la topologie livrée.
- [PIÈGE] Retexture : éviter un réglage qui refait les UV (perd le dépliage) ; préférer un membre « garder les UV existants ».
- [PARAM] Un dépliage UV acceptait jusqu'à « 30,000 faces » → plafonner le générateur dessous ou remesher avant.
- [MÉTHODE] Contrôle entre étapes : comparer nombre de faces, UV, dimensions, vignette. `hasUVs` prouve l'existence d'UV, pas un dépliage propre. Normales inversées (faces sombres) héritées par la suite ; échelle et pivot peuvent bouger entre étapes.
- [PARAM] Formats : nourrir l'étape suivante en GLB, sauf maillage quad (rester en FBX : glTF ne stocke que des triangles, un export GLB triangule).
- [PIÈGE] FBX pour Unity : « the FBX embedded only two images » → peut perdre des cartes PBR ; garder aussi le GLB.
- [CHOIX] Rig : bipède → rigger humanoïde (maillage + indice face/hauteur) ; non bipède → modèle avec `rigType` (quadruped, hexapod, octopod, avian, serpentine, aquatic) ; prop statique → segmentation de pièces, pas rig.
- [PARAM] Quads : Tripo P2/3.1 ont un interrupteur `quad` avec un plafond de faces plus bas ; sortie FBX.
- [PARAM] Riggers : acceptent GLB (souvent OBJ, FBX, STL), sans champ de format de sortie ; un rigger humanoïde plafonnait le fichier à 30 MB.
- [PARAM] `animation` d'un rigger = clip prédéfini retargeté, valeurs préfixées par type (`quadruped:walk`) ; par défaut seul le fichier animé revient, `includeRiggedModel` pour garder aussi le rig nu.
- [PIÈGE] Promettre un squelette nommé, un nombre d'influences ou des os d'ailes non documentés ; envoyer un bipède à un modèle `rigType` (pas de valeur biped).
- [CHOIX] Juste du mouvement sans squelette : motion transfer vidéo sur image fixe (voir vidéo).
- [PIÈGE] Segmentation en pièces : voie disputée ; un résultat vide d'une recherche ne prouve pas l'absence de capacité.

**Correspondance Deepotus**
- Ids touchés : meshy-6/7/7.1 (+ rig/animation Meshy), rodin-2.5, tripo (h3.1, p1, p2), hunyuan3d 2.1/3.1, trellis-2, triposr, Tripo segmentation (tripo3d/tripo/segment), Meshy texture, conversion Meshy, LOD gltfpack, Hunyuan local.
- Manques modèles : GPT-6 Astra 3D et Claude Opus 5.5 3D (membres Scenario propriétaires « LLM-based », pas sur fal a priori) ; Tripo 3.1 / Tripo multi-view ; Tripo texturing ; Tencent Texture Edit ; riggers non bipèdes (`rigType`, ex. Tripo animate/rig — probablement sur fal) ; UV unwrap IA.
- Manques paramètres : `textureSeed`, `delight`, `autoSize`, `quad`, `faceLimit` / `targetPolycount` explicites par moteur dans l'UI (à vérifier côté asset3d_service), `leftImage/rightImage` multi-vues, `includeRiggedModel`.

**Propre à Scenario.** recommend/`requires_plan_upgrade`, CU, `capture_3d_view`, asset_download `format` conversion, scenario-blender : non transposables.

---

## 7. scenario-meshy (Meshy)

**Résumé.** Boîte à outils Meshy : générateurs (7 Image to 3D, 7 Multi Image to 3D, T2 Smart Topology,
6 Text-to-3D) et utilitaires GLB→GLB (Retexture, Remesh, UV Unwrap, Rigging, Animation). Famille :
img23d, txt23d, 3d23d.

**Faits**
- [PARAM] 7 Image to 3D : `image` 1–4 ; `ultraMode` = UNE seule image ; maillage brut par défaut.
- [PARAM] 7 Multi Image to 3D : `image` 1–4, première = vue de face ; remesh pendant le run, `savePreRemeshedModel` garde le GLB brut.
- [PARAM] T2 Smart Topology : topologie prête à animer ; `targetPolycount` « caps at 15,000 ».
- [PARAM] 6 Text-to-3D : `prompt` « 600 chars » ; `shouldRemesh` off par défaut ; texture toujours (pas d'interrupteur).
- [PARAM] Défauts divergents : `enablePbr` true sur Image to 3D, false sur Multi Image et Retexture.
- [PIÈGE] Règle muette : l'image bat le texte. `textureImage` écrase `texturePrompt` (texte ignoré, pas mélangé) ; les deux exigent `shouldTexture` on.
- [PARAM] Retexture : EXACTEMENT un parmi `textStylePrompt`, `imageStyle`, `multiviewImage` (1–4 vues, première = face) ; géométrie intacte ; garder les entrées « near 30K polys » ; `enableOriginalUv`.
- [PARAM] `textureResolution` 2k/4k/8k ; à 8k les cartes PBR reviennent en 4K sans carte d'émission (Meshy 7 n'en produit jamais) ; 8k seulement avec topologie triangle quand on remeshe.
- [PARAM] `poseMode` en minuscules `"a-pose"` ou `"t-pose"` : à poser sur tout personnage destiné au rig.
- [MÉTHODE] Générer brut, raffiner exprès : `shouldRemesh` off sur 7 Image to 3D (recommandé par le schéma), puis Remesh pour le polycount.
- [PIÈGE] `targetPolycount` sur le générateur ne fait rien si `shouldRemesh` est off.
- [PARAM] Remesh : `targetPolycount` « 100 to 300,000 », `resizeHeight` en mètres (0 garde l'échelle), `originAt`, topologie.
- [PARAM] UV Unwrap : refuse « above 44,000 faces » → Remesh d'abord.
- [CHOIX] `ultraMode` = géométrie plus fine, plus cher, une image ; si les faces cachées comptent plus que le micro-détail, mettre le budget dans 4 vues.
- [COÛT] « the single-image Meshy 7 p50 ran three times the multi-image one » → chiffrer avant les lots.
- [CHOIX] Rigging et Animation sont des ALTERNATIVES : Animation rigge en interne puis applique `actionId` (bibliothèque docs.meshy.ai/en/api/animation-library). Rigging seul pour un GLB riggé pour ses propres clips.
- [PARAM] Animation : `postProcessOperation` `change_fps` (`postProcessFps` 24, 25, 30, 60) ou `extract_armature`. Rigging et Animation : `heightMeters` = vraie taille du personnage.
- [PIÈGE] Rigging puis Animation = un job gâché. Chaîne d'ids d'entrée : chaque étape prend l'asset 3D de la précédente dans `model`.
- [PIÈGE] Une photo seule doit quand même être passée en tableau.

**Correspondance Deepotus**
- Ids touchés : meshy-6, meshy-7, meshy-7.1, meshy-motion (rig + animation, en crédits Meshy, remesh exigé > 300 000 faces), texturage Meshy (texture_resolution), conversion Meshy.
- Manques modèles : Meshy T2 Smart Topology ; Meshy 7 Multi Image to 3D (si non branché) ; Meshy UV Unwrap ; Meshy Remesh exposé comme outil propre (Deepotus l'utilise seulement en préalable du rig). Meshy est appelé en direct (clé Meshy) ; sur fal, Meshy existe en partie (fal-ai/meshy/...), à vérifier.
- Manques paramètres : `ultraMode`, `poseMode`, `shouldRemesh`/`targetPolycount`, `savePreRemeshedModel`, `textureImage` vs `texturePrompt`, `enableOriginalUv`, `resizeHeight`, `originAt`, `postProcessOperation`/`postProcessFps`, `heightMeters`.

**Propre à Scenario.** `requires_plan_upgrade` / 403 de plan, CU : non transposables.

---

## 8. scenario-rodin (Rodin Hyper3D Gen-2.5)

**Résumé.** Famille Deemos : image-to-3D et text-to-3D en lane complète et Fast, plus Bang!
(découpe d'un maillage fini en pièces + retexture). Famille : img23d, txt23d, 3d23d.

**Faits**
- [PARAM] `images` : tableau même pour une image, « up to 5 », chaque entrée = vue du MÊME sujet, jamais un autre concept.
- [PROMPT] Prompt facultatif sur les membres image : vide, Rodin l'écrit d'après les images.
- [PARAM] Communs : `qualityMeshOption` (topologie + budget en une chaîne, ex. « 18K Quad »), `material` (PBR, Shaded, All, None), `textureDelight` (retire l'éclairage cuit), `TAPose` (pose T ou A pour rig — le schéma ne choisit pas entre les deux), `seed` 0–65535.
- [PARAM] Lane complète : `tier` de Gen-2.5-Extreme-Low à Gen-2.5-Extreme-High (« Extreme High bills double ») ; `addons: "HighPack"` (chaîne) ; `geometryInstructMode: "creative"` ; `isSymmetric` ; `isMicro` actif seulement en Extreme High.
- [PARAM] Lane Fast : `tier` Gen-2.5-Minimum / Extreme-Low / Low à prix fixe ; `highPack` booléen ; `enableCreativeMode` ; maillages « capped at 20K » derrière un défaut Auto.
- [PARAM] HighPack = textures 4K + géométrie haute densité, en supplément ; sur un maillage Quad « multiplies faces about 16 times ».
- [PIÈGE] Une charge utile ne passe jamais d'une lane à l'autre telle quelle (addons vs highPack, geometryInstructMode vs enableCreativeMode, enums de tier disjoints).
- [PIÈGE] Valeurs d'enum exactes (« Gen-2.5-Medium », « 18K Quad »), pas « medium ».
- [PARAM] Les membres texte n'ont pas les interrupteurs image (`useOriginalAlpha`, `previewRender`).
- [PARAM] Bang! : `model` (asset 3D) + `image` requis, `prompt` optionnel ; `strength` 2–12 (défaut 5, plus haut = plus de pièces) ; `material` défaut PBR ; `resolution` Basic = 2K, High = 4K ; plusieurs minutes ; coûte plus qu'un run générateur.
- [CHOIX] Fast pour les brouillons bon marché, lane complète pour le final.
- [PIÈGE] Jobs lane complète de plusieurs minutes : un timeout n'est pas un échec.

**Correspondance Deepotus**
- Ids touchés : rodin-2.5 (hyper3d ; 0,40 $ dans pricing asset3d ; aussi dans Blender generate_3d).
- Manques modèles : Rodin Gen-2.5 Fast, Rodin Text to 3D, Bang! (segmentation + retexture) — fal héberge Rodin (fal-ai/hyper3d/rodin), Gen-2.5 et Bang! probablement, à vérifier.
- Manques paramètres : `tier`, `qualityMeshOption`, `material`, `textureDelight`, `TAPose`, `addons`/HighPack, `isSymmetric`, `geometryInstructMode`, `seed`, multi-images (5 vues).

**Propre à Scenario.** `model_rodin-hyper3d-v2-5`, dry_run/jobs_wait : non transposables.

---

## 9. scenario-sparc3d (Sparc3D / Hitem3D)

**Résumé.** Image-to-3D sans texte : 1 à 4 photos → maillage étanche (watertight). Ligne de base
(objets/props) et ligne Portrait (têtes et bustes), en 2.1 et 2.0. Famille : img23d.

**Faits**
- [PROMPT] Aucun prompt : les images sont toute la direction artistique ; un sujet centré sur fond uni convertit le mieux.
- [PARAM] `images` 1–4, POSITIONNEL : face, puis dos, gauche, droite. Une vue de profil en slot 1 est lue comme la face.
- [PARAM] `requestType` : 1 = maillage nu, 3 (défaut) = texturé.
- [PARAM] `resolution` : `1536fast`/`1536pro` (2.1), `1536profast`/`1536pro` (2.1 Portrait), `1536`/`1536pro` (2.0), absent sur 2.0 Portrait. Défaut : 2.1 = fast, 2.1 Portrait = pro.
- [PARAM] `face` : « 100K to 2M, default 2M » (absent sur 2.0) ; 500K pour un asset léger, 2M haute fidélité.
- [PARAM] `pbr` (défaut true) inerte sans sortie texturée (requestType 1).
- [COÛT] `requestType`, `resolution`, `pbr` bougent le prix, « spanning four times on one member ».
- [PARAM] Durées longues : « medians near 17 to 21 minutes », quartile lent au-delà de 30 min.
- [CHOIX] Portrait = spécialiste têtes/visages, pas un palier de qualité supérieure ; jamais pour créature ou prop.
- [CHOIX] Maillage étanche → impression 3D, AR/VR, assets jeu.
- [PIÈGE] Aucun champ ne choisit le conteneur (GLB, OBJ, STL, FBX annoncés) : vérifier le format livré.
- [PARAM] Note scenario-3d : pas de contrôle de faces sous 100K → remesher pour un budget jeu.

**Correspondance Deepotus**
- Ids touchés : aucun.
- Manques modèles : Sparc3D 2.1 / 2.0 et Portrait (Hitem3D) — présence sur fal incertaine (à vérifier) ; candidat pour l'Imprimante 3D (maillage étanche).
- Manques paramètres : sans objet (famille absente).

**Propre à Scenario.** `model_hitem-sparc-3d-2-1` : non transposable.

---

## 10. scenario-3d-worlds (mondes navigables / Gaussian splats)

**Résumé.** Environnements explorables en 3D Gaussian splats : World Labs Marble (1.0 Draft, 1.1,
1.1 Plus), pipeline Hunyuan HY World (image→skybox→splat, multi-vues→splat), TripoSplat (un objet).
Famille : monde 3D, splat.

**Faits**
- [CHOIX] Choisir par l'entrée : texte → Marble ; une image plate ou 360 → Marble (`isPano: true` si 360) ; 2–8 photos d'une scène → Marble ; vidéo de déambulation → Marble ou HY Multi-view to Splat ; beaucoup de photos recouvrantes → HY Multi-view (« 2 to 64 ») ; une photo d'un lieu → HY Image to Skybox puis Skybox to Splat ; une photo d'objet → TripoSplat (détourage auto).
- [PIÈGE] TripoSplat veut UN objet propre, les autres une SCÈNE : viser l'un avec le sujet de l'autre est l'échec principal.
- [PARAM] `images` et `video` mutuellement exclusifs ; `isPano` seulement avec exactement une image ; un équirectangulaire sans `isPano` est lu comme photo plate.
- [MÉTHODE] Marble : les trois paliers ont les mêmes entrées, mêmes entrées + même `seed` = même monde sur chaque palier → itérer en Draft (« about a minute »), puis rejouer à l'identique en 1.1 ou 1.1 Plus.
- [COÛT] Écart de coût entre paliers « more than tenfold ».
- [PARAM] Marble : `splatResolution` (`100k`, `500k`, `full`) ; `disableRecaption: true` empêche Marble de réécrire le prompt ; 1.1 Plus agrandit le monde quand la scène le permet. Export splat + maillage triangle ou collider.
- [PIÈGE] Changer/omettre la seed entre brouillon et palier final = un autre monde.
- [PARAM] HY Image to Skybox (modèle image) : photo → panorama équirectangulaire 2:1 ; `backend` `full` (fidélité) vs `qwen` (vitesse/coût).
- [PARAM] HY Skybox to Splat : entrée `panorama` ; `applyNavTraj`, `applyUpRoute`, `applyReconIteration` (défaut true) font coût et temps ; `maxSteps` n'améliore qu'à la marge.
- [PARAM] Skybox to Splat : « close to an hour at median » ; un timeout n'est pas un échec.
- [CHOIX] HY Multi-view to Splat : rapide et bon marché, idéal quand la caméra bouge dans une scène statique avec parallaxe.
- [PIÈGE] Pas d'UV ni de topologie éditable dans un splat ; pour des polygones → générateurs de maillage.
- [PARAM] HY World : restriction géographique (« geo restriction tag ») — disponibilité selon région/équipe.
- [PARAM] Sortie finale `.spz`.

**Correspondance Deepotus**
- Ids touchés : aucun (Deepotus a un « Plateau 3D » et un storyboard 3D SAM 3, pas de splats).
- Manques modèles : World Labs Marble (fal ? incertain), HunyuanWorld (fal a eu « hunyuan-world » image-to-panorama — probable), TripoSplat (incertain).
- Manques paramètres : sans objet.

**Propre à Scenario.** `model_worldlabs-*`, `model_hunyuan-world-*`, viewer asset_display : non transposables.

---

## 11. scenario-skyboxes (skybox / panoramas 360)

**Résumé.** Génération de panoramas équirectangulaires 360 sans couture via des modèles dédiés + un
upscaler qui préserve la couture. Famille : txt2img/img2img panorama.

**Faits**
- [CHOIX] Toujours un modèle skybox dédié, jamais un modèle image générique : bords qui ne bouclent pas, pôles étalés.
- [PARAM] Skybox Flux : texte → 360, préréglages de `style`, correction automatique couture et pôles, image de référence optionnelle + `strength`. Champs : prompt, style, negativePrompt, image, strength, numOutputs, geometryEnforcement, seed.
- [PIÈGE] `negativePrompt` inerte tant que `negativePromptStrength` = 0.
- [PARAM] Skybox Flux sortie par défaut « 1536x768 » ; lire les vraies dimensions sur l'asset.
- [PARAM] Skybox GPT : texte → 360 guidé par « up to 10 reference images », préréglages qualité, largeur/hauteur jusqu'à 3840 px ; le catalogue annonce aussi bande cubemap 6:1 et croix 4:3 mais le schéma n'a que width/height.
- [PIÈGE] Skybox GPT avec un ratio ≠ 2:1 en attendant de l'équirectangulaire : garder 2:1 (ex. 2048×1024).
- [PARAM] HunyuanWorld Image to Skybox : une photo d'un lieu → skybox 360.
- [PARAM] Upscale skybox : « 2x to 8x » en préservant la couture ; `baseModel` défaut FLUX.1-dev (stylisé), option Krea (réalisme) ; `strength` défaut 0,6 invente du détail → baisser pour « même panorama, plus grand ».
- [COÛT] L'upscale peut coûter plusieurs fois la génération ; prendre le plus petit facteur qui atteint la cible.
- [MÉTHODE] Itérer l'ambiance : garder la seed du meilleur, ne changer que `style` ; garder la composition en changeant le rendu : repasser le favori en `image` avec `strength` 0,2–0,4 ; ambiance d'après un concept → Skybox GPT + références.
- [PIÈGE] Lutter contre la distorsion couture/pôle par le prompt : relever `geometryEnforcement` au-dessus de 0, seulement si la distorsion est visible.
- [PIÈGE] Upscaler générique = couture cassée.
- [MÉTHODE] Contrôle gratuit de la couture : colonne la plus à gauche vs la plus à droite quasi identiques ; des colonnes à un quart de tour diffèrent d'un ordre de grandeur de plus.

**Correspondance Deepotus**
- Ids touchés : aucun id skybox ; seul un modèle image générique pourrait être détourné (à proscrire).
- Manques modèles : Skybox Flux / Skybox GPT (propriétaires Scenario, non transposables) ; équivalents fal probables : HunyuanWorld image-to-panorama, éventuels LoRA 360 Flux — à vérifier ; upscaler qui préserve la couture (absent).
- Manques paramètres : `geometryEnforcement`, ratio 2:1 imposé, contrôle de couture automatique (vérif colonnes, facile en local Pillow).

**Propre à Scenario.** `model_scenario-skybox-*`, `model_sc-upscale-flux-skybox` : modèles maison, non transposables tels quels.

---

## 12. scenario-textures (textures et matériaux)

**Résumé.** Textures tuilables (seamless) depuis texte/références, packs thématiques, upscale qui
préserve la tuile, conversion en matériau et extraction de cartes PBR (PATINA). Famille :
txt2img/img2img texture, PBR.

**Faits**
- [PARAM] Scenario Texture : prompt (indice « tileable » ajouté automatiquement), `width`/`height` « 16 to 3840 in multiples of 16 », `quality`, `seed`, jusqu'à 10 `referenceImages` (style), `eraseSeam` (off par défaut) + `overlap`/`featherRadius` pour inpainter la couture sur les deux axes.
- [PARAM] LoRA Flux.1 thématiques (sols, marbre, béton, murs de pierre, planches, brique, terre cuite, peint main, cybernétique, réaliste).
- [PARAM] Upscale texture : `upscaleFactor` 2 (minimum) à 8 ; préréglages precise/balanced/creative (mêmes curseurs strength/controlnet) ; re-rendu → léger glissement tonal, `precise` + strength basse le minimise ; comparer à la source.
- [PARAM] Texture Converter : image plate → matériau, curseurs `raised`, `shiny`, `polished`, `angular` + `invert` du relief.
- [PARAM] PATINA Image to Maps (img2img) : base color, normal, roughness, metalness, height, chacune un asset nommé par `metadata.type` (`texture-albedo`, `texture-normal`, `texture-smoothness`, `texture-metallic`, `texture-height`).
- [PIÈGE] La demande de roughness revient étiquetée « smoothness » : vérifier la convention avant câblage.
- [CHOIX] Texture plate → extracteur 2D de cartes (un appel img2img) ; maillage → modèles de texturage 3D (Tripo 3.0 Texturing, Tencent Texture Edit, Meshy 7 Retexture) avec PBR activé.
- [PIÈGE] Faire passer une texture plate par un modèle 3D juste pour les cartes PBR.
- [MÉTHODE] Générer près de 1024, puis upscaler 2–8× ; ne pas générer énorme directement (plafond 3840).
- [PARAM] Moteurs de jeu : textures carrées puissance de 2 ; choisir 1024 ou 2048 délibérément.
- [PIÈGE] Upscaler générique sur une texture tuilable : casse la répétition.
- [COÛT] Le coût de l'upscale suit les pixels de sortie ; monter le facteur exprès.
- [MÉTHODE] Itérer : même seed + prompt modifié, ou `referenceImages` pour verrouiller un style.
- [MÉTHODE] Contrôle tuile gratuit : colonne gauche vs droite et ligne haut vs bas ne diffèrent pas plus que des colonnes voisines ; planche 2×2 auto-tuilée révèle toute couture.

**Correspondance Deepotus**
- Ids touchés : modèles image génériques (flux, seedream-5-pro, nano-banana…) utilisés pour Matières ; Matières a des générateurs locaux, delighting, hauteur (mémoire « Matières »). Export textures PIL (pricing asset3d_textures), Meshy texture.
- Manques modèles : PATINA (Image to Maps, Material) — Patina AI sur fal ? incertain ; générateur seamless dédié avec effacement de couture ; upscaler tuilable ; Tripo texturing / Tencent Texture Edit (Hunyuan3D texture — fal probable).
- Manques paramètres : `eraseSeam`/`overlap`/`featherRadius` ; tuilage forcé ; contrôle de tuile automatique (facile en local).

**Propre à Scenario.** `model_scenario-texture`, LoRA `sc:texture`, `model_sc-upscale-flux-texture`, `model_sc-texture-converter` : maison Scenario.

---

## 13. scenario-patina-retexture (PATINA Material + Blender)

**Résumé.** Retexturer en PBR un maillage aux couleurs plates : grouper ses matériaux en familles
physiques, générer un matériau PATINA tuilable par famille, câbler les 5 cartes dans Blender sans
toucher la géométrie ; film avant/après optionnel. Famille : txt2img matériau PBR + DCC.

**Faits**
- [MÉTHODE] Grouper les matériaux par nature physique (plâtre, cèdre, terre cuite, céramique émaillée, laiton, acier peint, verre, toile, asphalte, feuillage) ; une famille sert plusieurs variantes de couleur (couleur d'origine gardée en teinte). « A 41-material diorama needed 14 families ».
- [PROMPT] Si le maillage modélise déjà briques, tuiles ou planches : prompter la matière d'UN élément (argile cuite, cèdre patiné), jamais le motif (sinon le motif est doublé).
- [PROMPT] Prompt (requis, « 2048 characters ») : surface physique plate, éclairage uniforme, seamless, sans objet ni signalétique ni éclairage de scène. Ex. « aged lime plaster wall, fine mineral grain, flat, evenly lit, seamless ».
- [PARAM] `maps` = tableau même pour une entrée (chaîne nue ignorée) ; garder les 5 par défaut.
- [PARAM] `width`/`height` « 512 to 2048 in steps of 16 », 1024 par défaut ; `tileSize` (128 ≈ 1024 px) suit : 256 pour 2048, sinon la fenêtre de répétition ne correspond plus.
- [PARAM] `upscaleFactor` 2 ou 4 agrandit seulement les cartes prédites ; `tilingMode` restreint la répétition à un axe (planches, tôle ondulée) ; `numOutputs` jusqu'à 4 ; `enablePromptExpansion` on par défaut → l'éteindre si le prompt est délibéré ; `seed` fixe par famille.
- [COÛT] « One 1024x1024 five-map set was 17 CU » ; 14 familles = 238 CU ; `width`, `height`, `maps`, `upscaleFactor`, `numOutputs` font le prix.
- [PIÈGE] Sortie = 6 assets (texture de base + 5 cartes) ; identifier par `metadata.type`, jamais par position.
- [PIÈGE] Carte étiquetée smoothness mais VALEURS de roughness (un laiton brossé plus sombre qu'un gris mat) : trancher sur une famille de finition connue avant d'activer `roughness_is_smoothness`.
- [PARAM] Manifeste : `tile_span` (mètres par répétition : 0,3 détail main, 1–2 murs/pavés), `normal_strength` 0,25, `bump_distance` 0,002 (hauteur en bump, jamais de déplacement), plages `roughness` [0,3, 0,7] et `metalness` [0, 0] (laiton [0,8, 1]), `basecolor_mode` tint (garde la palette) ou replace.
- [PARAM] Familles nommées ceramic/enamel/plastic → couche coat ; glass → coat + transmission IOR 1,46 ; leaf → subsurface.
- [MÉTHODE] Projection UV dédiée `PatinaUV` par axe dominant de face à l'échelle objet ; hachage de géométrie vérifié inchangé.
- [PIÈGE] Un export glTF aplatit le graphe de shader calibré → baker avant export moteur ; le .blend est le livrable.
- [MÉTHODE] Contrôle : auto-tuiler chaque basecolor en 2×2 ; bordure visible → vérifier `tileSize`, régénérer avec une autre seed ou recadrer l'intérieur.
- [MÉTHODE] Film comparatif : même caméra, lumières, exposition, coupe ; pilote demi-résolution d'abord ; EEVEE 24 échantillons, 12 i/s interpolés à 24 pour mouvements lents (~1 s/image 2368×1332) ; valider sur une planche à 2 i/s, pas une image par plan.
- [PIÈGE] Relancer une famille parce que l'attente a expiré : vérifier la liste des jobs d'abord.

**Correspondance Deepotus**
- Ids touchés : indirectement Matières / Établi matériaux Blender / Forge3D (mémoire : « matériaux Blender », « Matières générateurs »).
- Manques modèles : PATINA Material (prompt → matériau PBR 5 cartes) — disponibilité fal incertaine ; équivalent possible : image seamless + extracteur de cartes local.
- Manques paramètres : `tileSize`, `tilingMode` (un axe), `maps` sélectives, polarité roughness/smoothness, `tile_span` en mètres.

**Propre à Scenario.** Ids PATINA, CU, collections Scenario, upload multipart : non transposables. Les scripts Blender (inventory/apply/film) sont réutilisables (MIT) mais ne parlent pas à un modèle.

---

## 14. scenario-video-to-motion (vidéo → animation 3D)

**Résumé.** Capture de mouvement sans marqueurs depuis une vidéo : soit votre personnage auto-riggé et
animé, soit le mouvement seul sur un squelette standard (Mixamo, MetaHuman). Famille : video23d.

**Faits**
- [CHOIX] Trois sorties : (a) votre maillage auto-riggé et animé (le rig est celui du modèle, pas le vôtre) ; (b) mouvement seul sur squelette nommé (Mixamo/MetaHuman) quand le perso est déjà riggé ; (c) drapeau « animation seule » sur un membre maillage. Décider la sortie AVANT le membre.
- [PIÈGE] Attendre le mouvement sur le rig existant du personnage : les membres maillage rigguent de zéro → membre « motion only » + retarget.
- [PARAM] Le fichier « motion only » peut contenir un maillage gabarit : l'omettre au retarget.
- [PIÈGE] Même nom de champ, sens différent : `characterFile` = maillage 3D chez l'un, image de référence chez l'autre (dont le maillage est `characterModel`). Se fier au type, pas au nom.
- [PARAM] Formats : FBX par moteur (`fbx-blender`, `fbx-unreal`, `fbx-roblox`, scènes Maya) chez l'un, `glb`/`fbx` (fbx pour Unity) chez un autre, aucun champ chez un 3e. Choisir la cible DANS le run ; une conversion après coup n'est pas garantie de garder l'animation.
- [PIÈGE] FBX ASCII rejeté par l'ancien importeur FBX de Blender → nouvel importeur ; vérifier l'animation importée.
- [PARAM] Réglages utiles : `moveInPlace` (locomotion pilotée par le code), `loop`, cadence (`frameRate`/`fps`/`targetFps`), nettoyage d'images-clés, axes `forward`/`up` si le mouvement arrive tourné ou couché.
- [PARAM] `numPeople` (plusieurs personnes) et capture du visage : coûtent plus.
- [PROMPT] Footage : une personne, corps entier tout le clip, pieds visibles, caméra fixe, personne ne passe devant ; vêtements amples/accessoires cachent les articulations.
- [PARAM] Plafonds : un membre « capped it at 30 seconds and about 30 MB », un autre exigeait largeur/hauteur paires. Absence de plafond ≠ illimité.
- [COÛT] Le prix suit la durée du clip : couper au mouvement livré.
- [MÉTHODE] Pas de footage : générer la performance en vidéo (un personnage corps entier, fond uni, caméra verrouillée, action décrite temps par temps).
- [PIÈGE] Cible humaine : créatures/non-bipèdes à vérifier image par image, souvent passe DCC.
- [MÉTHODE] Contrôle : orientation, pieds au sol, point de boucle sans saut ; résultat couché/de côté → essayer les axes avant d'accuser la capture.

**Correspondance Deepotus**
- Ids touchés : Uthana video-to-motion (pricing `uthana_v2m_usd_s` 0,05 $/s, clé Uthana directe), meshy-motion (animation par bibliothèque, pas depuis vidéo).
- Manques modèles : autres membres video23d (ex. motion only Mixamo/MetaHuman type DeepMotion, Move AI — hors fal a priori) ; vérifier ce qu'Uthana expose (squelette, formats).
- Manques paramètres : `moveInPlace`, `loop`, `fps`, `forward`/`up`, cible FBX par moteur, `numPeople`, visage (à recouper avec le service Uthana de Deepotus, non lu ici).

**Propre à Scenario.** recommend `video23d`, `next_step`/`ask_user`, scenario-video-editing : non transposables.

---

## 15. scenario-orbit-views (vues orbitales cohérentes)

**Résumé.** Voir un sujet sous de nouveaux angles via un intermédiaire 3D : maillage nu → rendus
« argile » grise posés sur le sol d'un panorama → repeinture de chaque vue par un modèle image à
références. Famille : img23d + img2img à références + skybox.

**Faits**
- [CHOIX] Ne pas demander « vu de dos » à un modèle image : il devine la géométrie, chaque angle dérive en taille, pose, contact au sol. Passer par un maillage.
- [PIÈGE] Repeintures indépendantes sur fond uni : « scale drifted 7 to 53 percent between views ».
- [PROMPT] Image source : un sujet, corps entier avec marge, fond uni, caméra connue (un peu au-dessus de l'œil, tournée d'environ 30°).
- [PARAM] Image-to-3D en géométrie seule (texture inutile).
- [PROMPT] Panorama de fond dans le même style : « viewpoint standing in the middle of an open empty floor at eye level… no people » ; sol plat et ouvert tout autour.
- [PARAM] Anneau de 16 caméras à 22,5° + vue de dessus ; « caméra zéro » trouvée par balayage d'IoU de silhouette puis vérifiée à l'œil (faible sur sujets symétriques : un robot à 0,55).
- [PARAM] Repeinture : modèle avec `referenceImages`, exactement 2 références [layout, source], 1024 carré, palier qualité haut, fond opaque.
- [PROMPT] Gabarit de repeinture : Image 1 = cadre final exact (argile grise sur le sol, ombre portée, angle voulu), Image 2 = référence de design ; repeindre l'argile en {quoi} d'après Image 2 (identité, matières, couleurs) ; suivre l'argile exactement (silhouette, pose, proportions, position, taille, angle) ; contact au sol nommé ; garder l'ombre et le fond d'Image 1 ; éclairer avec la scène ; « No gray clay left, no extra characters or objects, no text ». Ajouter une ligne pour les parties jamais vues (bouclier dans le dos, nombre de sacs).
- [PIÈGE] 3e référence (vue précédente du même angle) : ses erreurs sont copiées (un sac en plus sur toutes les vues de dos).
- [PIÈGE] Passe « harmonize » sur une vue finie : recadre et casse l'alignement.
- [PIÈGE] Coller le sujet sur une photo de fond plate : il flotte, l'horizon ne bouge pas.
- [MÉTHODE] Version sans fond : détourer la MÊME image repeinte + ombre Blender du rendu argile ; vérifier la couverture du corps d'argile.
- [MÉTHODE] Planche contact de toutes les vues ; ne régénérer que les ratées (une relance corrige souvent).
- [COÛT] Le devis d'une repeinture couvre une vue : multiplier par le nombre de vues.

**Correspondance Deepotus**
- Ids touchés : modèles image à références (nano-banana(-pro/-2.1), gpt-image-*, seedream-5-pro, flux-3) ; image-to-3D (tripo, hunyuan3d, trellis, meshy) ; Deepotus a « vues » 3D (pricing `asset3d_views`, seedream edit par vue) et Pose 3D.
- Manques modèles : générateur de skybox (voir §11).
- Manques paramètres : sans objet modèle ; la méthode (argile + 2 références) est transposable à la fonction « vues » de Deepotus.

**Propre à Scenario.** upload multipart, jobs_wait 32 ids : non transposables ; scripts Blender réutilisables (MIT).

---

## 16. scenario-walkable-room (photo → pièce navigable)

**Résumé.** Une photo d'intérieur → monde splat complet + objets reconstruits en 3D à saisir, lancer et
entendre, dans un navigateur (pipeline image-blaster). Famille : img2img (plate, découpes) + monde
single-image + img23d + SFX.

**Faits**
- [MÉTHODE] Étapes : inventaire (description littérale + objets mobiles avec boîte, support, taille, matières ; 2–3 par pièce) → plate (édition de suppression seule) → découpes (une édition par objet sur la photo ORIGINALE) → monde (single-image world sur la plate) → objets (img23d PBR) → sons → assemblage local.
- [PROMPT] Plate : « remove the following from the image: the {object} on the {support}, {where}; … » et rien d'autre.
- [PIÈGE] Les éditions de suppression recolorent parfois au lieu d'effacer, ou emportent les voisins (tous les coussins d'un banc) → liste plus étroite, 2 sorties et choisir, ou abandonner l'objet.
- [PROMPT] Découpe : « Isolate the {object}… Reproduce it exactly… White background, centered, tight crop, studio lighting. No other objects… no shadows on the ground » + nommer ce qui repose dessus pour l'exclure ; carré ~1K.
- [PIÈGE] Découper depuis la plate : l'objet n'y est plus.
- [CHOIX] Objets : uniquement des mobiles isolés (lampes, coussins, bols, vases, lanternes, tables d'appoint, chaises) ; jamais canapés, tapis, rideaux, éléments fixés ; éviter plantes, verre, objets qui en portent d'autres (l'image-to-3D ferme le feuillage en coque pleine).
- [PARAM] Monde : plate, splats pleine résolution, `seed` fixe pour toutes les pièces, prompt décrivant la pièce SANS les objets.
- [PARAM] Objets : PBR on, « about 50,000 » faces ; choisir le GLB par `mimeType` model/gltf-binary, jamais par ordre de sortie ; web : 15 000–20 000 triangles, textures WebP 1K, Meshopt.
- [PIÈGE] Métalness PBR de l'image-to-3D : laque et émail reviennent en métal (rendu chrome) → metalness 0 sauf vrai métal.
- [PROMPT] Sons : « Four separate one-shot impacts, each followed by a full second of silence: {objet, matière} {renversé/lâché} onto {sol}, {caractère}. Close-miked, dry room, no music, no voices. » ~6 s par objet ; découper sur silence (silencedetect -38 dB, trous 0,2 s), garder 2–4 coups, fondu, normaliser.
- [PIÈGE] Le monde n'est pas métrique : caméra photo ≈ 1 m du sol mesuré (0,9–1,1) ; plafonds 2,7–3,3 m ; tailles objets à ±10 %.
- [PIÈGE] Restyles d'une même photo : champ de vision « from about 50 to 76 degrees » selon le monde → ajuster l'objectif par monde.
- [MÉTHODE] Calibration : RANSAC du sol, mise à niveau, échelle par ratio taille estimée/projetée, objectif par corrélation de luminance, heightfield 4 cm / 2 cm, objets replacés via la profondeur juste derrière le bas de la boîte.
- [PIÈGE] Échec « result-download » d'un job 3D = erreur plateforme : vérifier puis relancer une fois à l'identique, pas changer la charge utile.
- [MÉTHODE] Viewer : Spark (splats LOD paginés) + Rapier ; props rigides endormis à leur place ; son seulement si vitesse > ~0,45 m/s, pas tenu, et pas de son < 150 ms.
- [MÉTHODE] Restyles : éditer la photo en ouvrant le prompt par l'architecture fixe (fenêtres, porte, plan, caméra, objectif) avant finitions/mobilier/lumière.

**Correspondance Deepotus**
- Ids touchés : édition image (nano-banana*, gpt-image-*, seedream-5-pro, flux-3) pour plate et découpes ; img23d (tripo, hunyuan3d, meshy, trellis) ; SFX (elevenlabs, sonilo-1.1, mirelo-1.6, stable-audio-3-sfx) ; SAM 3 objets (storyboard 3D) pour l'inventaire.
- Manques modèles : modèle de monde single-image (Marble, HunyuanWorld — §10).
- Manques paramètres : sans objet modèle ; gabarits de prompt plate/découpe/impacts directement réutilisables.

**Propre à Scenario.** Collections, `parallel-custom-jobs` 429, upload multipart : non transposables.

---

## Tableau récapitulatif

| Skill | Ids Deepotus touchés | Nb faits | Manques (modèles) | Manques (paramètres) |
|---|---|---|---|---|
| scenario-audio | MUSIC_MODELS, ELEVEN_MODELS, SFX_MODELS, htdemucs | 25 | extension par sections ; TTS dialogue ; speech-to-speech ; dubbing ; transcription | tableau de locuteurs, `loop` SFX non exposé, format audio, numOutputs musique |
| scenario-ace-step | ace-step | 16 | ACE-Step 1.5 Turbo/Quality ; Cover, Repaint, Add Layer, Complete Track, Stem Extract | bpm, keyscale, vocalLanguage, thinking, numOutputs, audioFormat, instrumental explicite |
| scenario-elevenlabs | eleven_multilingual_v2, eleven_v3, eleven_flash_v2_5, elevenlabs-music-2.5, elevenlabs-direct, elevenlabs-v2-fal, isolation | 22 | Music Advanced (sections), Dubbing v2/ancien, Speech to Speech, Voice Changer, dialogue v3 | languageCode, use_speaker_boost, seed TTS, balises v3 documentées, loop SFX, WAV TTS, sections/negativeStyles |
| scenario-minimax-music | minimax-music-20/26/3, (mureka-9.5) | 15 | MiniMax Music Cover | lyricsOptimizer, isInstrumental sur music-3, sampleRate, bitrate, coût 700 car./min |
| scenario-sonilo | sonilo-1.1, sonilo-video | 16 | Sonilo Text/Video to Music, Video-to-Video SFX et music mux | segments, numSamples, startOffset, duration vidéo |
| scenario-3d | meshy-6/7/7.1, rodin-2.5, tripo h3.1/p1/p2, hunyuan3d, trellis-2, triposr, tripo segment, meshy texture | 33 | GPT-6 Astra 3D / Claude Opus 5.5 3D (maison), Tripo 3.1 + multi-view + texturing, Tencent Texture Edit, riggers rigType, UV unwrap IA | textureSeed, delight, autoSize, quad, faceLimit/targetPolycount, leftImage/rightImage, includeRiggedModel |
| scenario-meshy | meshy-6/7/7.1, meshy-motion, meshy texture/convert | 19 | T2 Smart Topology, Multi Image to 3D, UV Unwrap, Remesh en outil | ultraMode, poseMode, shouldRemesh/targetPolycount, savePreRemeshedModel, textureImage, enableOriginalUv, resizeHeight, originAt, postProcess*, heightMeters |
| scenario-rodin | rodin-2.5 | 13 | Gen-2.5 Fast, Text to 3D, Bang! | tier, qualityMeshOption, material, textureDelight, TAPose, HighPack, isSymmetric, geometryInstructMode, seed, 5 vues |
| scenario-sparc3d | aucun | 12 | Sparc3D 2.1/2.0 + Portrait (Hitem3D) | — (famille absente) |
| scenario-3d-worlds | aucun | 15 | Marble 1.0/1.1/1.1 Plus, HunyuanWorld (skybox, splat, multi-vues), TripoSplat | — (famille absente) |
| scenario-skyboxes | aucun | 14 | Skybox Flux/GPT (maison), HunyuanWorld image→skybox, upscaler à couture | geometryEnforcement, ratio 2:1, contrôle de couture |
| scenario-textures | modèles image génériques, Matières, export textures, meshy texture | 15 | PATINA Image to Maps, générateur seamless, upscaler tuilable, Tripo texturing / Tencent Texture Edit | eraseSeam/overlap/featherRadius, contrôle de tuile |
| scenario-patina-retexture | (Matières, Établi matériaux Blender) | 17 | PATINA Material | tileSize, tilingMode, maps sélectives, polarité roughness, tile_span |
| scenario-video-to-motion | Uthana v2m, meshy-motion | 14 | membres motion-only Mixamo/MetaHuman | moveInPlace, loop, fps, forward/up, cible FBX par moteur, numPeople, visage |
| scenario-orbit-views | modèles image à références, img23d, asset3d_views | 15 | skybox (§11) | — (méthode) |
| scenario-walkable-room | édition image, img23d, SFX, SAM 3 | 18 | monde single-image (§10) | — (méthode) |
