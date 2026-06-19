# DESIGN.md — Deepotus Video Gen, refonte premium + Node Studio

> Brief de design destiné à un agent design (Claude). Lis ce fichier en entier
> avant de produire des maquettes ou du code. Cible : faire passer l'app du
> stade "outil interne fonctionnel v1.7.2" à un **studio premium prod-ready**,
> avec un **éditeur de nœuds** comme surface principale pour les compositions
> complexes (montage multi-clips, mixage audio, post brandé).

Stack actuel à respecter : React 18 + Vite + Tailwind + `react-konva`. Backend
FastAPI exposant `/api/*` (Seedance, HeyGen, Composition, Layout-templates,
News, Jobs, Health). Ne propose pas de refonte backend — *seulement le client*.
Tous les endpoints existants doivent rester utilisables tels quels.

---

## 1. Contexte produit (1 paragraphe à mémoriser)

Studio Windows local pour générer des vidéos virales 9:16 (X / Reels / Shorts)
autour du memecoin Solana **deepotus**. L'utilisateur unique est le solo
founder du projet : ingénieur produit, exigeant sur l'esthétique, monte ~1
post/jour, parfois 5/jour en campagne. Pipelines : **Seedance** (image →
clip cinématique), **HeyGen** (avatar parlant), **Composition** (Seedance +
HeyGen), **Templates** (composition spatiale 9:16 type "news reel + avatar"),
**News** (RSS → script "prophet" → reel illustré → post), **Timeline**
(montage séquentiel multi-clips avec xfade, formats 9:16/1:1/16:9/4:5). Tout
est local, latence réseau = appels providers. Les rendus mettent 30 s à 3 min
(Seedance) ou 1 à 5 min (HeyGen). Le sentiment cible : **"je pilote un studio,
pas un formulaire"**.

---

## 2. Audit UI actuel (v1.7.2) — à lire avant de redessiner

État actuel : 5 onglets en haut (`🎬 Seedance / 🎤 HeyGen / ⚡ Composition /
🎨 Templates / 📰 News`), grille 4 colonnes (image picker · template selector
· generation form · jobs queue), header sticky avec health badge. Esthétique
**deep / cyan / violet / amber**, fond `#02060d`, glow doux. Pas mal mais
**plat et formulaire-centré**.

**À garder (acquis émotionnels)**

- La palette deep-water (`bio-cyan #00e5ff`, `bio-violet ~ #a855f7`, `glow-amber`,
  fond `#02060d`).
- Le wordmark "DEEPOTUS VIDEO" + 🐙, le footer "From the deep, for the deep".
- Le pattern de halo cyan sur les éléments actifs.
- La densité — l'utilisateur veut tout voir.

**À tuer / refondre**

- Les 5 onglets côte à côte → arbitraire, ne raconte pas le workflow.
- Le grid 4 colonnes figé : on ne voit jamais le résultat final pendant
  qu'on configure.
- Les formulaires verticaux à champs nus : aucune hiérarchie visuelle.
- La file d'attente isolée à droite : déconnectée du contexte de rendu.
- La barre de progression linéaire fade → manque de drame pour un rendu de
  3 min.
- Pas de canvas de prévisualisation. L'utilisateur ne voit le résultat qu'une
  fois rendu.
- Le `TemplateEditor` (canvas Konva) et le `TimelineEditor` (timeline Konva)
  vivent dans le même onglet sans transition — discoverability v1.7.1 patchée
  au bouton "🎬 Timeline", à intégrer proprement.

**La douleur silencieuse à résoudre** : le studio est puissant mais sa surface
est un fouillis de panneaux. La refonte doit transformer "remplir 4 formulaires
puis attendre" en "construire un graph, voir la preview, ship".

---

## 3. Direction visuelle premium

**Mot-clé** : *Editorial Lab*. Krea + Linear + Resolve, mais avec une identité
biolumineuse profonde — comme un sous-marin scientifique. Pas de
"neumorphism mou", pas de "glassmorphism pop-corn". On vise :

- **Surfaces** stratifiées (fond, panneau, panneau-élevé) avec des contrastes
  nets, pas des verres flous.
- **Typographie** double : un display géométrique pour les titres, un mono
  inflexible pour la data, un sans-serif neutre pour les corps.
- **Couleur** : la palette deep-cyan reste, mais on l'utilise avec parcimonie
  — le cyan signale l'action en cours, le violet la dépendance/composition,
  l'amber l'attention, le vert le succès. **70 % de l'écran doit être neutre**
  (deep-900/950/ink) ; les accents font le travail émotionnel.
- **Motion** : tout est sous 200 ms sauf les apparitions de panneaux (300 ms,
  ease-out). Le halo "rendering" pulse à 1.2 Hz. Les nœuds connectés
  s'éclairent en cascade quand un run se propage.
- **Densité** : grille à 4 px de base, gap 12 / 16 / 24. Inspector dense
  mais structuré en sections collapsables.

Le résultat doit donner envie d'**ouvrir** l'app, pas de "vite faire un post".

---

## 4. Tokens (à proposer en valeurs définitives)

Reproduire et **affiner** les tokens existants (`packages/config/tailwind.preset.ts`
côté PROPHET-FORGE n'existe pas ici — c'est `tailwind.config.js` à la racine
`frontend/`). Le design agent doit livrer un fichier `tokens.css` (CSS vars)
+ une extension Tailwind.

### Couleur

| Token | Valeur cible (à valider) | Usage |
|---|---|---|
| `--bg-base` | `#02060d` | fond app |
| `--bg-panel` | `#0a1422` | cartes, panneaux |
| `--bg-panel-2` | `#0f1c30` | panneau élevé, hover row |
| `--bg-overlay` | `#02060dcc` | modal scrim |
| `--ink-strong` | `#e6f1ff` | titres, valeurs |
| `--ink` | `#b4c4d8` | corps |
| `--ink-soft` | `#6b7a92` | meta, labels |
| `--ink-muted` | `#3e4a60` | placeholder, dividers |
| `--stroke` | `#1a2740` | bordures par défaut |
| `--stroke-strong` | `#2a3c5e` | bordures focus |
| `--cyan` | `#00e5ff` | action primaire, runs in flight |
| `--cyan-soft` | `#00e5ff22` | halo, bg sélection |
| `--violet` | `#a855f7` | composition, dépendance, batch |
| `--amber` | `#fbbf24` | attention, sources image |
| `--green` | `#22c55e` | succès, validé |
| `--red` | `#ef4444` | erreur, destructif |
| `--node-image` | `#fbbf24` | port image |
| `--node-video` | `#00e5ff` | port video |
| `--node-audio` | `#22c55e` | port audio |
| `--node-av` | `#a855f7` | port video+audio (bundle) |
| `--node-text` | `#b4c4d8` | port text/string |
| `--node-data` | `#94a3b8` | port json/dict |

### Typographie

- **Display** : `Space Grotesk` (titres, wordmark) — déjà cohérent avec la
  vibe. Tailles : `28 / 22 / 18` (h1/h2/h3).
- **UI / corps** : `Inter` — `14 / 13 / 12` (body / dense / meta).
- **Mono** : `JetBrains Mono` — `12 / 11` (job_id, seeds, durées, deltas).

Tracking : `-0.01em` sur display, `0` sur corps, `+0.06em` uppercase pour les
labels de panneau (déjà fait, à garder).

### Espace / rayon / ombre

- Base 4. Grille `gap-3 / gap-4 / gap-6`.
- Rayons : `--r-sm 6`, `--r 10`, `--r-lg 14`, `--r-pill 999`.
- Ombres : `--shadow-1 0 1px 0 #ffffff08 inset, 0 8px 24px #0008` (panneau),
  `--shadow-glow 0 0 28px var(--cyan-soft)` (élément en run).

### Motion

- `--ease` `cubic-bezier(.2,.7,.2,1)`
- `--dur-1 120ms` (hover), `--dur-2 200ms` (état), `--dur-3 320ms` (panneau)
- `@keyframes halo-pulse` lit `--node-color` (déjà en place sur PROPHET-FORGE,
  reproduire ici).
- Tout `transition-all duration-300` improvisé est interdit — listes
  explicites de propriétés.

---

## 5. Architecture de l'information

Refonte de la navigation. Plus de 5 onglets côte à côte. À la place :

```
┌─────────────────────────────────────────────────────────────┐
│  🐙 DEEPOTUS VIDEO  v1.7.2          [● fal ✓ heygen ✓ voice]│
├──────┬──────────────────────────────────────────────────────┤
│      │                                                      │
│ S    │                                                      │
│ I    │              WORKSPACE (varies by mode)              │
│ D    │                                                      │
│ E    │                                                      │
│ N    │                                                      │
│ A    │                                                      │
│ V    │                                                      │
│      │                                                      │
├──────┴──────────────────────────────────────────────────────┤
│            JOB DOCK (collapsible, full width)               │
└─────────────────────────────────────────────────────────────┘
```

**Sidebar (72 px collapsed, 240 px expanded)** — sections, pas d'onglets :

- **Quick** — 1-shot generators (Seedance · HeyGen · Composition). Pour les
  posts rapides solo.
- **Studio** — l'éditeur de nœuds (la pièce centrale, voir §6). C'est ici
  qu'on monte les vidéos complexes.
- **Templates** — galerie de templates spatiaux (post layouts type
  `tpl_news_reel`) + éditeur visuel Konva.
- **News** — pipeline RSS → script → reel. Conserve l'UI v1.7 mais redessinée.
- **Library** — la bibliothèque (images, audio, renders existants, captions).
- **Settings** — clés API, persona, paths, defaults.

**Job Dock (bottom)** — barre d'état permanente, hauteur 56 px collapsed,
360 px ouverte. Affiche jusqu'à 3 rendus en cours en cards horizontales
(progress + miniature + ETA), bouton **▴** pour étendre en liste complète.
Toujours visible, peu importe le mode actif. C'est là qu'on **renomme** un
rendu, qu'on le clone, qu'on le supprime, qu'on le rejoue en preview.

---

## 6. Node Studio — la pièce centrale

C'est la grande demande utilisateur : un **système de nœuds** pour composer
des montages et mixages complexes. À designer avec le soin d'un produit
n8n / TouchDesigner / Cavalry — mais cadré sur ce domaine vidéo.

### 6.1. Anatomie de l'écran

```
┌───────────┬──────────────────────────────────┬───────────────┐
│           │                                  │               │
│  PALETTE  │            CANVAS                │   INSPECTOR   │
│  (260)    │   nodes + edges, react-flow      │     (340)     │
│           │   like, infinite, zoom/pan       │               │
│           │                                  │               │
│           │                                  │               │
├───────────┴──────────────────────────────────┴───────────────┤
│  TOPBAR (graph name, run, preview, format selector, export)  │
└──────────────────────────────────────────────────────────────┘
```

- **Palette (gauche)** : nœuds groupés par catégorie. Drag-to-canvas, ou
  Cmd-K → command palette inline (Linear-style).
- **Canvas** : graphe orienté. Rendu via `react-flow` (à ajouter aux deps).
  Sélection multi (lasso), copier/coller, undo/redo, alignement auto, mini-map
  en bas-droite.
- **Inspector (droite)** : édite les props du nœud sélectionné. Si rien
  sélectionné, montre les props du **graph** (format de sortie 9:16/1:1/16:9/4:5,
  fps, durée totale calculée, audio master, render-name).
- **Topbar** : nom du graph (rename inline), boutons `▶ Run`, `◐ Preview`,
  selector format, `↓ Export JSON`, `↑ Import JSON`.

### 6.2. Catalogue de nœuds (à designer chacun)

Couleur de bordure = couleur de catégorie. Ports typés avec couleur (cf §4
node-*).

**Sources** (amber border)

- `Image` — picker → renvoie un port image. Props : filename, preview thumb.
- `Text` — éditeur multi-ligne → port text.
- `Existing render` — picker job existant → port video+audio (`av`), expose
  `duration_real_s` lue via `GET /api/jobs/{id}`.
- `Upload` — drop zone, fichier local → port `av` ou `image` selon type.
- `News item` — picker depuis le flux news → port `{title, link, image, essence}`
  (data).

**Generators** (cyan border)

- `Seedance` — entrée : image start (+ image end optionnelle, + prompt text).
  Sortie : `video` (clip muet). Props : style, durée (multiples de 5s),
  aspect_ratio, seed, extend_mode (loop/hold).
- `HeyGen avatar` — entrée : text (script), choix avatar+voix dans props.
  Sortie : `av`.
- `News script` — entrée : `news item[]`. Sortie : text (script prophet) +
  data (essences). Toggle "use Anthropic summarizer".
- `News illustration` — entrée : `news item[]`. Sortie : video.

**Audio** (green border)

- `Voiceover (ElevenLabs)` — entrée text → sortie audio.
- `Music track` — entrée upload/existing → sortie audio, prop volume + loop.
- `Audio mix` — entrées audio[N] → sortie audio. Props : volumes, ducking dB,
  fade in/out.
- `Loudness norm` — entrée audio → sortie audio. Prop LUFS target.

**Edit / montage** (violet border)

- `Trim` — entrée `av` ou `video` → sortie même type, props : `start_s`, `end_s`,
  `length_mode: source|fixed`.
- `Extend` — entrée video → sortie video. Props : `target_s`, `mode: loop|hold`.
  C'est le fix Seedance 5s-step déjà en place.
- `Concatenate (xfade)` — entrées `av`[N] (ordonnées) → sortie `av`. Props
  par transition : type (`crossfade|cut|fadeblack|glitch|slide|flash`),
  `duration_s`. C'est l'équivalent du `tpl_timeline` actuel mais visuel.
- `Split` — entrée `av` → 2 sorties `av` (point de coupe).
- `Speed` — entrée video → sortie video. Prop factor.

**Composition** (cyan-deep border)

- `Spatial compose` — entrées : un slot par région (`reel`, `avatar`, `bg`…).
  Le nœud expose un **mini-éditeur Konva inline** dans l'inspector pour
  placer/redimensionner les régions sur le canvas 9:16. C'est l'équivalent du
  `TemplateEditor` actuel — *embedded as a node*. Sortie : `av`.
- `Brand strip` — entrée : data (mark + text) → sortie `image` (bande
  brandée à utiliser dans Spatial compose).
- `Text overlay` — entrée video → sortie video. Props : text, font, size,
  color, position, effect (pulse), timing (start/end).
- `Ticker` — entrée video + text → sortie video. Props : speed, direction.
- `Separator` — sortie `image`. Props : color, thickness.

**Master** (red border, max 1 par graph)

- `Avatar master` — input `av`. Marque ce clip comme **maître de durée** :
  c'est le fix anti-cut v1.7.2 surfacé visuellement. Props : `tail_pad_s`,
  `fade_out_s`. Quand présent, la sortie finale = `max(graph_duration,
  avatar_duration + tail_pad)`.

**Output** (white border)

- `Render` — entrée `av`. Props : format (9:16/1:1/16:9/4:5), fps, CRF,
  render-name, voice_mode (passthrough pour les sous-jobs). Click `▶ Run` →
  POST vers `/api/layout-templates/{...}/render` avec le template inline
  généré par sérialisation du graph (cf §6.5).

### 6.3. Ports & règles de connexion

| Port | Couleur | Type accepté |
|---|---|---|
| `image` | amber | `image` only |
| `video` | cyan | `video`, `av` (auto-extract video) |
| `audio` | green | `audio`, `av` (auto-extract audio) |
| `av` | violet | `av` only (preserve sync) |
| `text` | slate | `text` only |
| `data` | gray | `data` (json/dict) |

- Connexion invalide : l'edge devient rouge + tooltip "video → text non
  autorisé".
- Connexion partielle (`av` → `video` ou `audio`) : edge violet pointillé,
  indication "audio jeté" ou "video jetée".
- Cycle : interdit, l'edge ne se crée pas.

### 6.4. Interaction

- **Drag from port** → edge fantôme cyan. Drop sur port compatible → snap +
  flash success. Drop sur vide → ouvre la palette filtrée par type compatible.
- **Hover edge** → label durée propagée (ffprobe live pour les sources connues).
- **Right-click node** → menu : Duplicate / Detach / Disable / Pin / Delete.
- **Cmd-A** sélectionne tout, **Cmd-D** duplique, **G** group, **Shift+R**
  rename node, **F** frame on selection, **0** reset zoom.
- **Status visuel par nœud** pendant un run :
  - `idle` : bordure stroke
  - `queued` : bordure stroke-strong + glow doux
  - `running` : halo pulsé couleur catégorie (réutilise le keyframe v1.7.1)
  - `succeeded` : bordure verte 600 ms puis retour idle
  - `failed` : bordure rouge persistante + petit ⚠ cliquable → error popover
- **Live propagation** : quand un nœud termine, son edge en aval s'éclaire en
  cascade. C'est la dopamine du studio.

### 6.5. Sérialisation & exécution

Le graph se sérialise en **un template inline** compatible avec l'endpoint
existant `POST /api/layout-templates/{template_id}/render` (qui accepte un
`template` inline depuis v1.6). Mapping :

- Nœuds `Spatial compose` → `regions[]` du template.
- Nœuds `Concatenate (xfade)` → `render_mode: "sequential"` + `regions[]` avec
  `act` ordonnés et `transition`.
- Nœud `Avatar master` → `audio.master_track: "from_slot:<slot>"` +
  `tail_pad_s`.
- Nœud `Render` → `canvas.width/height/fps`, `title`.
- Les sources concrètes (Image, Existing render, Upload, Seedance, HeyGen)
  remplissent les `slot_values` à l'exécution.

**Important** : les nœuds générateurs (`Seedance`, `HeyGen avatar`) ne sont
pas exécutés *avant* le render endpoint — ils sont laissés en `slot_values`
avec `source_kind: "seedance"|"heygen"` et le pipeline backend les résout en
parallèle (déjà en place). Le client n'a rien à orchestrer côté providers.

Le design agent doit prévoir l'UI mais **ne pas re-spécifier le backend**.

### 6.6. Templates de graph (starter packs)

Sur "New graph", proposer 4 starters :

1. **Seedance solo** — `Image → Seedance → Render`. Le plus simple.
2. **Avatar post** — `Text → HeyGen → Avatar master → Render`.
3. **News reel post** — `News item → News script → HeyGen → News illustration
   → Spatial compose (reel + avatar + brand) → Avatar master → Render`.
4. **Timeline montage** — `[Image → Seedance] × 4 → Concatenate xfade →
   (+ optional Music track + Audio mix) → Render`.

Chaque starter ouvre un graph pré-câblé que l'utilisateur n'a plus qu'à
remplir.

### 6.7. Preview (drame)

Le bouton `◐ Preview` (à côté de `▶ Run`) lance une **prévisualisation locale
basse-déf** : on prend uniquement les `Existing render` + `Upload` (rien à
générer chez les providers), et on rend un MP4 480 p offline. Coût ≈ 5 s,
zero $$, et l'utilisateur voit la composition avant de cramer $0.30+ chez
fal.ai. **C'est ce qui rend le studio premium.**

UI : la preview s'affiche dans une dock à droite (slide-in 320 ms), avec un
mini scrubber timeline.

---

## 7. Inventaire de composants (à designer)

Atomes :

- `Button` — variants : `primary` (cyan glow), `ghost`, `danger`, `outline`,
  `link`. Tailles `sm / md / lg`. États `idle / hover / active / loading /
  disabled`.
- `Input` — text, number, textarea. Avec slot left/right icon.
- `Select` — natif stylé + variant "command" (recherche inline, Linear-style).
- `Slider` — avec valeur affichée et ticks de référence.
- `Toggle` — switch + checkbox.
- `Tag / Chip` — pour les statuts (running, done, failed, batch).
- `Badge` — health badges du header (fal ✓ / heygen ✓ / voice ✓).
- `Tooltip` — sombre, 100 ms delay, max-width 280.
- `Progress` — linéaire avec gradient cyan→violet + variant "halo" circulaire
  pour les nœuds.
- `Avatar / Thumb` — vignette ronde (avatar HeyGen) / carrée (image / video
  poster).
- `Toast` — déjà en place, à reskinner : ombré, accents par type.

Molécules :

- `FileDropZone` — drag-drop image/audio/video. State idle / hover-active /
  uploading.
- `JobCard` — utilisé dans le Job Dock. Compact horizontal : thumb 56×56,
  titre (= `title || provider`), progress, ETA, actions (rename, clone,
  delete, open).
- `NodeCard` — la carte d'un nœud sur le canvas. Header (icon + nom + statut),
  ports gauche/droite, preview optionnelle (thumb du média en sortie quand
  succeeded).
- `InspectorSection` — collapsable, label uppercase, dense fields à
  l'intérieur.
- `PortChip` — pastille couleur + type + sens (in/out).

Organismes :

- `Sidebar` — collapsable, sections actives, badge new/beta.
- `JobDock` — collapsable, dock bas full-width, 3 cards inline ou liste
  étendue.
- `CommandPalette` — Cmd-K, recherche fuzzy de nœuds, de templates, de jobs,
  de réglages.
- `NodePalette` — colonnes catégorisées + recherche.
- `GraphCanvas` — react-flow custom-themed.
- `Inspector` — panneau droit, contextuel (graph / node / edge).
- `TemplateCard` — galerie templates spatiaux : thumb + nom + tags + actions.
- `LibraryGrid` — bibliothèque assets : filtres (image/audio/video/render),
  tri (recent/name/size), preview hover.

---

## 8. Écrans clés — specs

### 8.1. Quick · Seedance / HeyGen / Composition

Garde l'esprit "1 formulaire 1 résultat" pour les posts solo. Refonte :

```
┌──────────────────┬──────────────────────────────┐
│  SOURCE          │                              │
│  ┌────────────┐  │                              │
│  │ DropZone   │  │       PREVIEW PANE           │
│  │ start img  │  │  (live thumb of selected     │
│  └────────────┘  │   image + ghost of expected  │
│  ┌────────────┐  │   output dimensions)         │
│  │ end img    │  │                              │
│  └────────────┘  │                              │
├──────────────────┤                              │
│  PARAMETERS      │                              │
│  Style    [...]  │                              │
│  Duration [10s]  │                              │
│  Seed     [..]   │                              │
│  Voice    [off]  │                              │
├──────────────────┤                              │
│  PROMPT          │                              │
│  [ textarea ]    │                              │
│  [ ▶ Generate ]  │                              │
└──────────────────┴──────────────────────────────┘
```

Largeur source 360, preview flex. Le bouton Generate occupe la base du
panneau source, sticky.

### 8.2. Studio (Node Editor)

Cf §6. Plus de détails :

- Topbar : `[graph-name 🖉]   [9:16 ▾]   [◐ Preview]   [▶ Run]   [↓ Export]`.
- Mini-map en bas droite du canvas, 160×96, scrim.
- Hint "press `/`" pour ouvrir la palette quand canvas vide.

### 8.3. Templates (galerie + éditeur spatial)

Galerie en grille (3 colonnes), chaque card = thumb 1:1.77, hover → actions
(Edit · Use · Duplicate · Delete). Templates built-in marqués 🔒 (read-only,
mais "Duplicate to edit").

Éditeur : canvas Konva 9:16 (ou format sélectionné), palette de régions à
gauche, properties à droite. Garde l'esprit actuel mais ré-applique tokens
et types. Bouton "Open in Studio" qui convertit le template en graph
`Spatial compose` pour passage en mode avancé.

### 8.4. News

Layout 2 colonnes : gauche = sources & feed (RSS list + add source, refresh,
defaults pack), droite = items (checkbox multi-select, image preview, essence
preview après scrape). En bas : panneau "Compose" → 3 boutons :
`Build script` · `Build illustration` · `Send to Studio` (ouvre un nouveau
graph "News reel post" pré-rempli avec les items cochés). Tail-pad et
ANTHROPIC summary derrière un toggle "Advanced".

### 8.5. Library

Tabs internes : `Images · Audio · Renders · Captions`. Grille thumbs avec
filtres (search, date, format, durée). Click → preview modal + actions (use
in graph, rename, delete). Renders affiche `title` en grand, `provider` en
meta.

### 8.6. Settings

Sections : `API keys` (masquées + Reveal), `Provider defaults` (voice IDs,
style defaults), `Paths` (auto-detected, override), `Persona` (lecture seule
de `deepotus.json` + bouton ouvrir le dossier), `News` (default summary words,
toggles, reader fallback), `Appearance` (motion off pour accessibility).

---

## 9. Patterns d'interaction transverses

- **Rendering progress** : barre linéaire + temps écoulé + ETA estimé
  (heuristique : Seedance 30 s/5 s clip, HeyGen 2 min/min de script). Quand
  on dépasse l'ETA × 1.5, badge "slow" amber discret.
- **Rename render** (cf v1.7.2) : inline edit dans la JobCard du dock, save
  on Enter ou blur. PATCH `/api/jobs/{id}`.
- **Fit to source / Anti-cut** : déjà en place backend. Côté UI, le nœud
  `Avatar master` est l'expression visible. Dans le Spatial-compose-node-
  inspector, un toggle "Use this clip as duration master" + slider tail-pad
  0-2 s.
- **Empty Job Dock** : message "*Nothing rendering. Press `▶ Run` in Studio
  or Quick.*" avec un 🐙 doux.
- **Provider down** : si `/api/health` reporte un provider off, les nœuds
  correspondants apparaissent dimmed + tooltip "Set HEYGEN_API_KEY in
  backend/.env to enable. Restart backend."
- **Confirm destructive** : `Delete render` → inline confirm dans la card
  (déjà ainsi), pas de modal full-screen.
- **Persistence** : tout le draft de graph + sélections persistent en
  localStorage (déjà le pattern `usePersistedState` v1.7.1). Le design ne doit
  jamais "perdre" un brouillon entre les onglets.
- **Toast cadence** : 1 toast par action, durée 3.2 s, action "undo"
  optionnelle pour delete.
- **Keyboard-first** : `/` palette de nœuds, `Cmd-K` palette globale,
  `Cmd-S` save graph, `Cmd-Enter` Run, `Esc` close inspector pop-ups.

---

## 10. États (à designer pour chaque écran)

| État | Comportement |
|---|---|
| **Empty Studio** | Canvas avec un onboarding doux : 4 cards starters cliquables + texte "Press `/` to add a node" |
| **Loading library** | Skeleton grids 8 items, shimmer cyan léger |
| **Generating (Seedance)** | Card preview pulse + label "Generating cinematic clip… ~30s" + estimate countdown |
| **Failed render** | Card en haut du dock, bordure rouge, message error (truncated 80c), boutons Retry / Clone & edit / Delete |
| **No FAL_KEY** | Bandeau permanent en haut "fal.ai key missing — Quick Seedance disabled. → Settings" |
| **No graph saved** | Indicateur "Unsaved" dans la topbar, badge orange à côté du nom |
| **Drag invalid** | Edge fantôme rouge + tooltip raison |

---

## 11. Responsive & accessibilité

Cible **desktop only** (Windows 1080 p / 1440 p). Le design n'a pas besoin
d'être mobile, mais doit :

- Rester utilisable à `1366×768` (sidebar collapsed par défaut sous 1500 px,
  inspector overlay au lieu d'inline).
- Supporter 200 % zoom OS (texte ne casse pas, ne tronque pas les actions
  critiques).
- A11y : focus ring `2 px solid var(--cyan)` jamais coupé, contraste AA sur
  tout texte ≥ 14 px, AAA sur titres. `prefers-reduced-motion: reduce` →
  désactive halo pulse et propagation cascade, conserve les transitions
  d'état (opacity only). Skip-links pour navigation clavier dans le Studio
  (J/K entre nœuds).
- Aria : nœuds = `role="treeitem"`+`aria-grabbed`, edges = décoratifs
  (`aria-hidden`), inspector = `role="region" aria-label="Node properties"`.

---

## 12. Livrables attendus du design agent

1. **Tokens** : `frontend/src/styles/tokens.css` + extension
   `frontend/tailwind.config.js`.
2. **Composants atomiques + molécules** dans `frontend/src/components/ui/`
   (Button, Input, Select, Slider, Toggle, Tag, Badge, Tooltip, Progress,
   Toast — déjà partiel, à reskinner).
3. **Layout shell** : `Sidebar`, `JobDock`, `CommandPalette`, nouvel
   `App.jsx` qui orchestre les modes.
4. **Node Studio** : `frontend/src/studio/`
   - `GraphCanvas.jsx` (react-flow wrapper themed)
   - `NodePalette.jsx`
   - `Inspector.jsx`
   - `nodes/*.jsx` un fichier par type de nœud
   - `graph-to-template.js` — sérialise un graph en template inline
   - `usePersistedGraph.js`
5. **Refonte des écrans** existants (Quick / Templates / News / Library /
   Settings) avec les nouveaux composants.
6. **Storybook ou page "/design"** listant tous les composants en isolation.
7. **3 maquettes haute-fi** statiques (`mockups/*.html` ou Figma) en
   référence pixel : `quick.html`, `studio.html`, `news.html`.

**Ne pas livrer** : refonte backend, refonte du système de persona / news
scraper / pipeline. Le client doit rester compatible avec l'API actuelle
sans rupture.

---

## 13. Inspirations & guard-rails

**À étudier** :

- Linear (densité, commande K, navigation latérale, qualité du focus ring)
- Krea (gestion du canvas + preview live + bibliothèque assets)
- n8n / Cavalry / TouchDesigner (ergonomie de nœuds, ports typés, mini-map)
- Arc Studio (transitions latérales, sidebars compactes)
- Resolve / Premiere (job dock + timeline)

**À éviter absolument** :

- Le look "AI tool 2023" : gradient mauve/rose, fond glassmorphism flou,
  hero "✨ Powered by AI" — non.
- Les emojis dans les boutons primaires (gardés ailleurs : 🎬 timeline,
  🐙 brand, mais pas dans `▶ Run`).
- Les modales lourdes : 90 % des confirmations doivent être inline.
- Les transitions > 400 ms.
- Les boutons "fantôme" sans bordure ni fond sur fond non-uniforme — on perd
  l'affordance.
- Les illustrations stock. Si une illustration est nécessaire (empty state),
  c'est une icône SVG custom dans la palette deep.

---

## 14. Plan d'attaque suggéré (pour le design agent)

1. **Tokens + atomes** (1 passe complète, validation visuelle sur une page
   /design).
2. **Layout shell** (Sidebar + JobDock + CommandPalette) — le squelette
   neuf.
3. **Quick** refondu sur le shell — petit risque, valide le système.
4. **Studio** — la pièce maîtresse. Commencer par les 4 starters câblés en
   dur, puis l'ajout/suppression de nœuds, puis la sérialisation.
5. **Templates / News / Library / Settings** dans cet ordre.
6. **Polish** : motion, halo cascade, empty states, raccourcis clavier,
   Storybook.

À chaque étape, prendre un screenshot et l'auto-critiquer contre les
guard-rails §13. Si ça ressemble à un "dashboard SaaS générique" : retravailler
jusqu'à ce que ça ressemble à un **studio**.

---

## Annexe — Mapping endpoints existants (référence rapide)

| Action UI | Endpoint |
|---|---|
| Health | `GET /api/health` |
| List images | `GET /api/images` |
| Upload image | `POST /api/images/upload` |
| Seedance generate | `POST /api/generate` |
| HeyGen generate | `POST /api/generate/heygen` |
| Composition | `POST /api/generate/composition` |
| List avatars | `GET /api/heygen/avatars` |
| List voices | `GET /api/heygen/voices` |
| List templates | `GET /api/layout-templates` |
| Save template | `POST /api/layout-templates` |
| **Render template (inline ok)** | `POST /api/layout-templates/{id}/render` |
| List jobs | `GET /api/jobs` |
| Get job (+ `duration_real_s`) | `GET /api/jobs/{id}` |
| **Rename render** | `PATCH /api/jobs/{id}` `{title}` |
| Delete job | `DELETE /api/jobs/{id}` |
| Job video | `GET /api/jobs/{id}/video` |
| News list / add / toggle / refresh / items | `/api/news/*` |
| News script | `POST /api/news/script` |
| News illustration | `POST /api/news/illustration` |

Tout le reste — exécution Seedance/HeyGen parallèle, anti-cut, audio mix,
auto-migration DB — est déjà géré côté backend. Le client n'orchestre rien
au-delà de la sérialisation graph→template inline.

---

*Fin du brief. Si une ambiguïté reste sur un comportement précis : choisis
la version qui rend le studio plus calme, plus dense, et plus rapide à
naviguer au clavier.*
