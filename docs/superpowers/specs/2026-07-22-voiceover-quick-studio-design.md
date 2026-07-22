# Chantiers V-a / V-b — Voice-over : onglet Quick + nœud Studio (ElevenLabs v1)

Brief validé par Olivier le 22/07/2026 (AskUserQuestion 3/3) :
casting = **presets nommés globaux**, périmètre v1 = **ElevenLabs seul**
(Voicebox reste intact côté backend mais n'est PAS exposé dans Quick/Studio),
process = **spec relue avant implémentation**, V-a prouvé avant V-b.

## 1. Résumé

Générer une voix off SEULE (zéro image/vidéo) depuis deux surfaces :
- **V-a — Quick** : 4e onglet « Voice Over » — texte bref → mp3 dans
  Library → Audio, avec choix de la voix (liste défilante + préécoute) et
  castings sauvegardables.
- **V-b — Studio** : réanimer le nœud `Voiceover` existant (aujourd'hui
  inerte) : il lit le texte du nœud amont (port `text`), offre le même
  sélecteur voix/casting/préécoute, et sa piste est mixée dans la vidéo
  finale du Render.

Découverte de cadrage : le backend voix v1.26 (façade ElevenLabs/Voicebox,
`GET /voices`, `POST /audio/voiceover` avec `voice_id`, réglage
`voice_provider`) est **déjà livré et testé**. V-a est un chantier ~100 %
frontend (patch bundle) ; V-b ajoute un petit maillon backend (champ
`voiceover` des requêtes de render → `FFmpegMerger.merge(audio_path=…)`,
paramètre qui existe déjà mais n'est jamais alimenté).

## 2. Décisions actées

| Sujet | Décision |
|---|---|
| Fournisseurs v1 | ElevenLabs uniquement dans l'UI. Pas de select fournisseur dans Quick/Studio, pas de préécoute Voicebox, pas d'E2E Voicebox. Le backend provider-aware reste tel quel. |
| Casting | Presets nommés globaux, persistés serveur dans `atelier_settings.voice_castings` (clé/valeur existante, **zéro migration**). Partagés entre Quick et le nœud Studio. |
| Génération Quick | Synchrone (`POST /audio/voiceover`, pattern éprouvé du flux Chapitres) — pas de job asynchrone : un texte bref sort en secondes, et le résultat est déjà listé par Library → Audio. |
| Architecture UI | Pas de page standalone `/voicelab` : le nœud Studio impose la chirurgie bundle, donc le sélecteur de voix (`DzVoicePicker`) est construit UNE fois dans le bundle (V-a) et réutilisé par le panneau du nœud (V-b). |
| Préécoute | `new Audio(preview_url)` sur les `preview_url` du catalogue ElevenLabs (déjà utilisés par le casting Atelier). Aucune génération, aucun endpoint nouveau. |

## 3. Périmètre v1 / non-objectifs

Dans le périmètre : onglet Quick, nœud Studio, DzVoicePicker, castings,
mixage VO au Render (Seedance + HeyGen), harnais QA, mise à jour du guide
(`docs/guide/fr.html` annonce déjà un bouton « voice » dans Quick qui
n'existe pas — V-a le rend vrai, reformulé).

Non-objectifs v1 (suites en §9) : exposition Voicebox dans l'UI, préécoute
Voicebox (échantillon généré localement), import du casting personnages
Atelier, posts audio-only dans le Scheduler, ducking automatique
musique/voix (v1 : amix plat existant, musique déjà à −14 dB par défaut).

## 4. Existant (état des lieux)

- `backend/app/api/routes.py:1116` `POST /audio/voiceover`
  `{script, language?: en|fr, name?, voice_id?}` → mp3 dans le dossier audio
  (`{name}-{6 chiffres}.mp3`), réponse `{ok, filename, url, size_kb}`.
  Provider-aware via `VoiceoverService.generate_long`. La docstring ne
  mentionne pas `voice_id` mais la route le lit (l.1137) — docstring à
  rafraîchir au passage.
- `routes.py:1157` `GET /voices` → catalogue du provider actif, items
  `{voice_id, name, category, language, labels, preview_url}` (ElevenLabs :
  labels riches + `preview_url` non nul).
- `routes.py:3516` `GET /voice/providers` → `{providers, configured,
  resolved}` : la garde v1 de l'UI lit `resolved`.
- `routes.py:3576` `PUT /atelier/settings` : upsert `{key: value}`, valeur
  stockée `str(v or "")` → le front DOIT envoyer les castings comme **chaîne
  JSON** (`JSON.stringify`), jamais un objet (sinon repr Python illisible).
- `ffmpeg_service.py:71` `FFmpegMerger.merge(video, audio_path, …,
  music_path, music_volume_db, keep_video_audio)` : `audio_path` est LA
  piste voiceover (docstring l.82), mixée en `amix normalize=0` avec musique
  bouclée et audio vidéo. Jamais alimentée par `pipeline.py` (3 appels :
  l.310/457/551, tous `music_*` seulement).
- Bundle (`frontend/dist/assets/index-BEOJX8L5.js`, seul artefact — pas de
  source React) :
  - Quick = composant `um`, 3 modes, anchor unique
    `["seedance","heygen","comp"].includes(B)?B:"seedance"`.
  - Registre nœuds `Me{}` : `Voiceover:{cat:"audio", inPorts:[{id:"text",
    type:"text"}], outPorts:[{id:"out",type:"audio"}], props:{voice:"Adam ·
    oracular", stability:.6}}` — déclaré, présent dans la palette et le
    dock « / », icône et libellé de carte gérés, MAIS : pas de branche
    d'inspecteur (`Yh`), pas d'appel API, pas de `filename`, coût en dur
    `$0.04`, et le compilateur audio du Render le traverse sans capture
    (`else if(g3.type==="Voiceover")g3=Wt(e,g3.id,"text")`).
  - Nœuds source `Text` et `Prompt` sortent `type:"text"` → l'ancre amont
    demandée existe déjà.
  - Anchor d'insertion du panneau : `label:"Loop to render duration"})})]}):
    e.type==="Seedance"?r.jsxs(ie,{label:"Generator"` (fin du panneau
    MusicTrack, count==1).
- Pricing : `pricing.py` kind `"elevenlabs"` = `chars ×
  elevenlabs_usd_per_char (0.00024)`. Pas d'endpoint d'estimation dédié →
  coût affiché calculé côté client avec la même constante (commentaire de
  patch pointant pricing.py).
- `.env` data : `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID_EN/FR` déjà
  renseignés chez Olivier (vérifié présence 22/07, sans lire les valeurs).

## 5. Chantier V-a — Quick « Voice Over »

Patch : `scripts/patch_bundle_quickvoice.py` (baseline = bundle courant
post-11d/version v1.16.0). Zéro changement backend fonctionnel (seule la
docstring de `/audio/voiceover` est rafraîchie pour mentionner `voice_id`).

### 5.1 UI

- Mode `voice` ajouté : `["seedance","heygen","comp","voice"]` + bouton
  d'onglet « Voice Over ». ⚠ Le tableau des boutons d'onglets Quick n'a pas
  encore été isolé avec un anchor unique : première étape d'implémentation =
  repérage au DevTools/Puppeteer sur l'app installée, PUIS écriture du patch
  (unicité vérifiée par occurrences `-o`, pas par lignes — les lignes du
  bundle dépassent 100 k caractères).
- Panneau (haut → bas) :
  1. Garde fournisseur : `GET /voice/providers` → `resolved ===
     "elevenlabs"` : puce « ElevenLabs » ; `"voicebox"` : bandeau « v1 gère
     ElevenLabs seul — change le Fournisseur de voix dans Réglages » +
     Générer désactivé ; `null` : panneau désactivé « clé ElevenLabs
     manquante (Réglages → Clés) », pattern des tuiles disabled existantes.
  2. Textarea script, `maxlength 2500` (= taille d'un chunk
     `generate_long` : « texte bref », un seul appel ElevenLabs), compteur
     chars + coût estimé `chars × $0.00024`.
  3. Langue `fr | en` (défaut `fr`), envoyée explicitement.
  4. `DzVoicePicker` (§5.2), entrée « Voix par défaut de l'app » en tête
     (= `voice_id` omis → `ELEVENLABS_VOICE_ID_{FR,EN}`), sélectionnée par
     défaut.
  5. Rangée casting (§5.3).
  6. Bouton « Générer la voix » (désactivé si script vide) → spinner →
     `POST /audio/voiceover {script, language, voice_id?, name:"quick_vo"}`.
  7. Résultat : `<audio controls>` (pattern Chapitres) + nom de fichier +
     mention « disponible dans Library → Audio ». Erreur 400/502 : message
     inline rouge avec le texte serveur.

### 5.2 DzVoicePicker (composant partagé V-a/V-b)

- Données : `GET /voices` au premier affichage, cache en mémoire + bouton ↻.
- Liste verticale défilante (~240 px), une carte par voix : nom + labels
  utiles (genre/accent/âge/description si présents) + bouton ▶.
- Préécoute : UNE instance `Audio` globale — jouer une voix stoppe la
  précédente ; ▶ grisé si `preview_url` absent (cas Voicebox futur) ;
  AUCUNE requête de génération.
- Sélection au clic (bord accent) ; expose `{voice_id, name}` au parent.
- Filtre texte en tête de liste (utile dès >12 voix).

### 5.3 Castings

- Clé serveur `voice_castings` (via `GET/PUT /atelier/settings` existants),
  valeur = chaîne JSON :
  `[{"name":"Narrateur FR","provider":"elevenlabs","voice_id":"…",
  "voice_name":"…","language":"fr"}]`.
- UI : select « Casting… » (appliquer = sélectionne voix + langue) ; bouton
  « ★ Sauver » (petit input nom inline ; nom existant = écrase) ; « ✕ »
  supprime le casting sélectionné. Save/delete = réécriture complète de la
  liste (read-modify-write, volumes minuscules).
- `provider` est stocké dès la v1 pour que les castings Voicebox futurs
  cohabitent sans migration.

### 5.4 Recette V-a (tout doit être vert)

1. Quick affiche l'onglet « Voice Over » ; panneau conforme §5.1.
2. Texte court fr → 200, `<audio>` jouable, fichier présent dans
   `GET /api/audio` ET visible dans Library → Audio.
3. **Aucun job créé** : `GET /api/jobs` identique avant/après génération.
4. Préécoute : ▶ joue le `preview_url` (spy sur `Audio.play` dans le
   harnais), zéro POST réseau ; lancer une 2e voix stoppe la 1re.
5. Casting « QA-test » sauvé → reload app → toujours présent et applicable ;
   `GET /atelier/settings` contient `voice_castings` (JSON valide).
6. Harnais `scripts/qa/qa-quickvoice.js` (Puppeteer, points 1-5 + garde
   fournisseur simulée par mock de fetch) : N/N vert. Tests backend
   existants inchangés (aucune modif backend).

## 6. Chantier V-b — Nœud Studio Voiceover

Patchs : `scripts/patch_bundle_voicenode.py` (baseline = post-quickvoice).
Backend : petit maillon « voiceover jusqu'au merge ».

### 6.1 Frontend

- Props étendues : `provider:"elevenlabs", voice_id:"", voice_name:"",
  language:"fr", filename:"", chars:0` (chars = longueur du texte amont à la
  dernière génération, pour le coût).
- Panneau d'inspecteur (nouvelle branche à l'anchor « fin MusicTrack », §4) :
  - Texte amont lu via `Wt(graph, node.id, "text")` : extrait affiché
    (~80 chars) ; si aucun nœud Text/Prompt relié → « Relie un nœud
    Text/Prompt à l'entrée text » + Générer désactivé (pas de textarea
    local : l'ancre amont est la source de vérité).
  - Langue + `DzVoicePicker` + rangée casting (mêmes composants que V-a).
  - « Générer la voix » → `POST /audio/voiceover {script:texte_amont,
    language, voice_id?, name:"studio_vo"}` → `set("filename", …)` +
    `<audio controls>` d'aperçu (pattern du panneau MusicTrack).
- Compilateur audio du Render (fonction unique, §4) : la branche Voiceover
  capture `vo={file: props.filename}` quand `filename` est renseigné (miroir
  de la capture MusicTrack), puis continue la remontée comme aujourd'hui.
  Payload des renders : `voiceover:{file}` envoyé aux côtés de `music`.
- Coût de carte : remplacer le `$0.04` en dur par `chars × $0.00024`
  (constante locale alignée sur pricing.py, commentée).
- Le nœud reste utilisable sans Render : Générer + aperçu suffisent (le mp3
  est de toute façon dans Library → Audio).

### 6.2 Backend

- `schemas.py` : `voiceover: Optional[dict] = None` (`{"file": <nom dans le
  dossier audio>}`) sur `GenerateRequest` (l.150) et `GenerateHeyGenRequest`
  (l.217), à côté de `music`.
- `pipeline.py` : `_resolve_voiceover()` miroir de `_resolve_music` (l.116 :
  validation « nom de fichier existant dans le dossier audio », pas de
  volume — VO à 0 dB en v1) ; passer `audio_path=vo_path` aux 3 sites
  d'appel de `merge` (l.310/457/551). Site HeyGen : `keep_video_audio`
  inchangé (avatar qui parle + VO = mix voulu si l'utilisateur branche les
  deux). Pré-vérification d'implémentation : confirmer par grep qu'aucun des
  3 sites n'alimente déjà `audio_path`.
- Test `backend/tests/test_render_voiceover.py` (script autonome, python
  embarqué de l'app installée) : `_resolve_voiceover` (fichier valide /
  absent / traversée de chemin) + `merge` réel (ffmpeg : préfixer le PATH
  avec `bin/` de l'app installée ou `installer/_cache/ffmpeg-x/…/bin`) sur
  un mp4 `lavfi testsrc` 1 s + mp3 court → ffprobe : piste AAC présente ;
  non-régression : requête sans `voiceover` → sortie identique à avant.

> **Note d'implémentation (22/07, chantier V-b).** Le cadrage §6.2 visait les
> 3 sites `merge` de pipeline.py — la vérification d'implémentation a montré
> que le graphe de la recette pt 2 (source ExistingRender) compile vers le
> **chemin template** (`renderLayoutTemplate` → `render_template`), pas vers
> ces 3 sites. Extension livrée en conséquence : `voiceover` aussi sur
> `TemplateRenderRequest`, et post-merge `_apply_voiceover_post` (sortie
> `template_<job>_vo.mp4`, l'audio du composite — BGM/master — est conservé
> sous la VO). Côté bundle, la capture se fait UNE fois dans la façade
> `renderLayoutTemplate` via `dzGraphVoiceover(graph)` (même marche que le
> compilateur audio, ports in/a/src/text) : les trois branches template (UGC,
> montage, spatial) sont couvertes par un seul anchor ; les payloads directs
> `/generate` et `/generate/heygen` reçoivent le même champ. Au passage, le
> site merge Seedance alimentait DÉJÀ `audio_path` (VO persona quand
> `voiceover_enabled` — jamais le cas depuis le Studio, qui envoie `!1`) : un
> fichier explicite **remplace** la synthèse persona, pas de double piste.

### 6.3 Recette V-b (tout doit être vert)

1. Graphe `Text → Voiceover` : le panneau montre l'extrait amont, Générer
   produit l'audio DU TEXTE AMONT (pas d'un champ local) ; sans nœud texte
   relié, Générer est désactivé avec le message.
2. Graphe avec source `ExistingRender` + `Voiceover` (+ `MusicTrack`) →
   Render : la vidéo finale contient la VO (ffprobe : piste audio ; écoute :
   VO audible par-dessus la musique). Zéro coût Seedance (source existante).
3. Coût de carte dynamique (chars × tarif), plus de `$0.04` en dur.
4. Castings créés en V-a visibles/applicables depuis le nœud.
5. `scripts/qa/qa-voicenode.js` N/N vert + `test_render_voiceover.py` vert +
   tests voix existants (`test_voice_providers.py`, `test_voiceover.py`)
   verts.

## 7. QA & déploiement (procédure connue)

- Patchs en bout de chaîne : baselines documentées en docstring, garde-chaîne
  du CR chantier 11 respectée (jamais rejouer un patch ancien isolément).
- Unicité des anchors vérifiée par OCCURRENCES (`-o`), pas par lignes.
- Déploiement : `GET /api/jobs` idle → copie repo → app installée (mêmes
  chemins relatifs) → relance breakaway `explorer.exe launch-silent.vbs`
  (JAMAIS stop/launch depuis le shell : incident overlay MSIX) →
  `scripts/dz_postdeploy_probe.ps1` (health `fs_virtualized=false` + sonde
  upload) → QA Puppeteer sur l'app installée (un seul onglet, Chrome
  système, `localStorage.dz_onboarded=1`).
- Bump du libellé de version via `patch_bundle_version.py` à chaque
  livraison (numérotation décidée au commit, convention des chantiers).
- Guide `docs/guide/fr.html` + `en.html` : section Quick mise à jour (V-a).

## 8. Risques & mitigations

- **Anchors des onglets Quick pas encore isolés** → étape de repérage
  obligatoire avant d'écrire le patch (échec = abort count!=1, jamais de
  patch approximatif).
- **`patch_bundle_voiceprov.py` perdu** (le select Réglages v1.26 est dans
  le bundle mais son patcher n'a jamais été committé) → tâche séparée déjà
  créée (chip 22/07) ; non bloquant ici : nos baselines partent du bundle
  ACTUEL.
- **`resolved ≠ elevenlabs`** (Voicebox lancé par Olivier + réglage
  voicebox) → garde §5.1 : bandeau + Générer désactivé, comportement défini.
- **Textes longs** → maxlength 2500 v1 (un chunk), le flux Chapitres reste
  la voie pour les narrations longues.
- **Préécoute sans `preview_url`** → bouton grisé (jamais de génération
  implicite).

## 9. Suites (hors v1)

1. Exposer Voicebox dans Quick/Studio : select fournisseur, préécoute par
   échantillon généré localement + cache (`outputs/audio/_previews/`) —
   APRÈS la réconciliation des données Voicebox forkées
   (`LocalCache\Local\Voicebox`, session dédiée, GO acquis le 20/07).
2. Import de castings depuis le casting personnages de l'Atelier.
3. Ducking musique sous la voix (sidechaincompress) au Render.
4. Posts audio-only dans le Scheduler si le besoin apparaît.
