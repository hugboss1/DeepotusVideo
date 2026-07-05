# Atelier Chapitre — mini-films d'animation narrés (vision + P1) — design

Date: 2026-07-05
Status: P1 approved-pending-user-review; P2–P4 outlined for continuity
Référence analysée: « J'ai créé un outil pour générer des storyboards IA
automatiquement » — Frank Houbre (youtube pJyOlWOwEEc, transcript intégral
analysé le 2026-07-05)

## 1. La philosophie transposée (de la vidéo de référence)

Le principe directeur de l'outil de référence (utilisé pour produire l'animé
« Lost Garden ») : **verrouiller chaque étape avant de payer la suivante.**

1. Scénario posé et complet d'abord (import texte/Final Draft, ou co-écriture).
2. Dans le script, **sélectionner des zones** (mot/phrase) → clic droit →
   créer **Personnage / Lieu / Objet** → chaque entité rejoint un **moodboard**
   (description + images d'inspiration) → génération d'une **image de
   référence canonique** par entité (la « character sheet »).
3. Découpage automatique en scènes : **croquis volontairement basiques**
   (cadrage, action, mouvement de caméra, durée) — pas d'images finales.
   Script synchronisé avec le storyboard. Itération à volonté (durées,
   insertion de scènes, angles) — coût quasi nul.
4. Une fois le storyboard verrouillé : **production** — prompts auto-optimisés
   (durée, caméra, personnages réels injectés), génération vidéo, rushes,
   montage.

Transposition DeepotusVideoGen : ce workflow devient l'**Atelier Chapitre**,
alimenté par les briques existantes — Épisodes (`/episodes/extract-text`,
`/episodes/scenes` IA), FLUX/GPT image (`/images/generate`), Seedance
(image→vidéo, seeds), HeyGen v3 (image animée / cinématique — PR #5/#6),
ElevenLabs (narration), Studio (montage/effets/audio), Library, Scheduler.

## 2. Décisions structurantes (validées)

- **Architecture** : page dédiée **servie par le backend** (comme `/guide`) —
  HTML/JS/CSS propres dans `frontend/atelier/`, montée sur **`/atelier`**,
  même API et même thème sombre que l'app. AUCUNE chirurgie du bundle pour
  l'UI riche (sélection de texte, menus contextuels, timeline). Un lien nav
  dans le bundle = micro-patch optionnel en fin de phase.
- **Entités** : Personnages + Lieux + Objets, **bible persistante en DB**
  (migre avec le kit export/import), partagée entre chapitres.
- **Storyboard** : croquis d'abord (validation cadrage/rythme), images
  finales seulement après verrouillage.
- **Phasage** : P1 Script→Entités→Bible · P2 Storyboard · P3 Production ·
  P4 Post-production. Chaque phase = spec→plan→PR→validation.

## 3. Modèle de données (P1)

### Table `bible_entities`
- `id` (uuid PK), `kind` ("character"|"place"|"object"), `name` (unique par kind),
  `description` (Text), `ref_image` (Library filename de la référence générée),
  `seed` (Integer, nullable — le seed FLUX verrouillé de la référence),
  `style_notes` (Text, nullable — ex. "style anime, palette abyssale"),
  `inspiration_images` (Text JSON — filenames Library),
  `created_at`, `updated_at`.

### Table `chapters`
- `id` (uuid PK), `title`, `script_text` (Text),
  `spans` (Text JSON — [{start, end, text, entity_id}] : les zones marquées
  dans le script, offsets sur script_text),
  `series` (String nullable — pour regrouper les chapitres d'une même œuvre),
  `created_at`, `updated_at`.

Deux nouvelles tables → `create_all` suffit (pas d'ALTER).

## 4. API (P1)

- `GET/POST /api/bible/entities` · `PUT/DELETE /api/bible/entities/{id}` —
  CRUD; GET filtre `?kind=`.
- `POST /api/bible/entities/{id}/generate` — génère l'image de référence :
  prompt = description + style_notes (+ mention du kind), via le chemin FLUX
  de `/images/generate` étendu d'un **seed** ; body `{seed?: int,
  model?: str}` — sans seed → aléatoire, le **seed utilisé est stocké** sur
  l'entité avec le filename ; re-roll = nouveau seed ; « verrouiller » =
  conserver. L'image atterrit dans la Library (réutilisable partout).
- **Extension `/images/generate`** : accepte `seed` (passthrough fal FLUX,
  renvoyé dans la réponse). Les modèles GPT-image n'ont pas de seed → ignoré.
- `GET/POST /api/chapters` · `GET/PUT/DELETE /api/chapters/{id}` — CRUD
  (script + spans + série).
- Import de fichier : réutilise **`POST /episodes/extract-text`** (txt/docx/pdf).

## 5. UI `/atelier` (P1)

Fichiers : `frontend/atelier/index.html` + `atelier.css` + `atelier.js`
(vanilla, zéro build, servis statiquement ; variables CSS reprenant le thème).

Layout deux volets :
- **Gauche — le script** : liste des chapitres (créer/ouvrir/renommer,
  champ série) ; éditeur du chapitre (import fichier ou collage) ; les zones
  liées sont **surlignées** (couleur par kind). **Sélection de texte →
  menu flottant** « ➕ Personnage · ➕ Lieu · ➕ Objet · 🔗 Lier à… » (lier =
  rattacher la zone à une entité existante de la bible). Sauvegarde auto
  (debounce) du script + spans.
- **Droite — la bible** : onglets Personnages / Lieux / Objets ; cartes
  entité : nom, description (éditable), vignettes d'inspiration (choisies
  dans la Library via `/api/images`), **image de référence** générée, badge
  **seed** (re-roll 🎲 / verrouillé 🔒), bouton **Générer la référence**.
  Les entités sont globales (toute la série les voit).

Accès P1 : URL directe `http://127.0.0.1:8765/atelier` (+ lien depuis le
guide) ; le micro-patch nav du bundle viendra avec P2.

## 6. Phases suivantes (esquisse pour continuité)

- **P2 Storyboard** : table `shots` (chapter_id, ordre, texte-source [span],
  entités présentes, action, shot type, camera move, durée, croquis filename,
  prompt) ; découpage auto (LLM local via summarizer, comme
  `/episodes/scenes` méthode "ai" mais sortie enrichie plans + entités) ;
  croquis low-cost (FLUX schnell + suffixe de style « storyboard sketch,
  rough pencil ») ; vue timeline synchronisée script↔plans ; insertion/
  étirement/re-cadrage d'un plan.
- **P3 Production** : par plan, générer l'image finale (prompt + **références
  des entités présentes** + seeds) puis la vidéo : Seedance i2v (action/
  caméra) ou HeyGen v3 image-animée (dialogue/narration face caméra) ou
  cinématique ; narration ElevenLabs par plan (voix par personnage via
  castings) ; rushes dans la Library, jobs standard.
- **P4 Post-production** : assemblage → graphe Studio auto-généré
  (Concatenate + Effects + BGM + loudness), export, envoi Scheduler.

## 7. Risques & garde-fous

- **Cohérence des personnages** : seed + même modèle ≠ garantie parfaite
  (le seed fige le bruit, pas l'identité en i2v). Garde-fous P1 : référence
  canonique unique par entité + seed stocké ; P3 utilisera l'image de
  référence comme ancrage (i2v Seedance part de l'image ; HeyGen v3 anime
  l'image même) — c'est l'ancrage image, plus fiable que le seed seul.
- **Éditeur & offsets** : script en texte brut (textarea + calque de
  surlignage), spans par offsets — l'édition du texte décale les offsets →
  P1 recalcule les spans par recherche du texte de la zone (fallback:
  marquer la zone « orpheline » à re-lier).
- **`/atelier` hors bundle** : pas de régression possible sur l'app
  existante ; le seul point de contact est l'API.

## 8. Tests (P1)

- API : CRUD entités + chapitres ; generate-référence avec seed mocké
  (monkeypatch du client fal) → seed/filename stockés ; extension seed de
  /images/generate (validation du payload construit).
- UI : vérif manuelle guidée (import, sélection→entité, génération réf,
  persistance après restart, partage entre 2 chapitres).
