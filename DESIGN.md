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

**Render queue (révision 11a, 20/07/2026 — remplace le Job Dock bas d'écran)**
— le dock permanent est supprimé : un studio de vidéos 9:16 verticales ne
sacrifie pas sa hauteur à une barre horizontale. À la place : icône « file »
en topbar + badge compteur N (pastille cyan, halo pulsé ~1.2 Hz pendant un
run, rouge fixe si un job failed non lu — lu = ouverture du panneau, persisté
localStorage), et panneau latéral DROIT 360 px en slide-in 320 ms `--ease`
(scrim cliquable, Esc ferme, `prefers-reduced-motion` → fade). Les JobCards
y gardent rename / clone / delete / preview, failed en tête. Poignée QA :
`window.__dzQueue`.

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
- **Empty queue panel** (ex-Job Dock) : message "*Nothing rendering. Press
  `▶ Run` in Studio or Quick.*" avec un 🐙 doux.
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

---

# 15. MÀJ 26/08/2026 — Handoff « Icônes Deepotus » (session claude.design) — FAIT FOI

> Collé tel quel depuis `Design d'icônes applicatives/design_handoff_icones_couleurs/design.md`.
> Les sections ci-dessous REMPLACENT toute section icônes / couleurs de catégorie /
> panneaux repliables antérieure de ce fichier — le §4 (tokens v1.7.2) reste comme
> histoire, il ne fait plus foi sur ces trois sujets. L'état d'implémentation réel
> est consigné en §15-bis, à la suite.

# Deepotus — Design spec : iconographie, couleurs par catégorie, zones escamotables

> **Comment intégrer ce fichier.** Ce document est écrit pour être collé dans
> `C:\Users\olivi\DeepotusVideo\design.md`. Les cinq sections numérotées ci-dessous sont
> autonomes : si `design.md` contient déjà une section icônes, couleurs ou panneaux
> repliables, **celles-ci les remplacent**. Rien d'autre dans le fichier existant n'est
> concerné.
>
> **Nature du livrable.** La maquette de référence est `Icônes Deepotus.dc.html` (livrée
> à côté de ce fichier). C'est un **prototype HTML de référence**, pas du code à copier :
> il montre l'apparence et le comportement attendus. Le travail consiste à **recréer ces
> designs dans l'environnement existant de la codebase** (React / Vite / Tailwind ou ce
> qui est en place), avec ses conventions, ses composants et sa librairie de styles.
>
> **Fidélité : haute (hifi).** Couleurs, tailles, durées et courbes d'animation sont
> définitives. Le tracé SVG de chaque icône est donné intégralement et doit être repris
> tel quel. Les libellés sont ceux de l'application et ne doivent pas être réécrits.

---

## 0. Périmètre de la mise à jour

Trois chantiers, dans cet ordre de dépendance :

| # | Chantier | Portée |
|---|---|---|
| 1 | **Jeu d'icônes « glyphe bicolore » (variante 1b)** | 27 icônes : 11 du bandeau de navigation, 10 du bandeau Card Forge, 6 de la barre horizontale |
| 2 | **Barre horizontale colorée à bords droits (variante 2a)** + **propagation de la teinte** | La barre `Game Assets` et **toute l'UI de la section pilotée** par l'onglet actif |
| 3 | **Chevrons de repli / expansion unifiés** | Tous les panneaux escamotables de l'application, sans exception |

---

## 1. Design tokens

### 1.1 Surfaces et texte (inchangés, rappelés pour référence)

```css
--srf-app:        #0a0c0f;  /* fond application */
--srf-panel:      #13171c;  /* bandeaux, panneaux latéraux */
--srf-raised:     #171c22;  /* onglet inactif, champ */
--srf-hover:      #181d23;  /* survol de ligne */
--srf-active:     #191f26;  /* ligne sélectionnée */
--brd-hard:       #20262d;  /* bordure de panneau */
--brd-soft:       #1c2229;  /* filet interne, séparateur */

--txt-hi:         #eef2f6;  /* libellé sélectionné */
--txt-base:       #cfd6dd;  /* libellé de navigation */
--txt-mid:        #8b959f;  /* icône au repos, libellé secondaire */
--txt-low:        #5f6873;  /* sous-titre mono, numéro d'étape */
--txt-faint:      #4d5661;  /* légende, zone vide */
```

Typographie : libellés en sans-serif système (`Helvetica Neue, Helvetica, sans-serif`),
12,5 px / 500 pour les entrées de navigation, 12 px / 400 pour les étapes Card Forge.
Toutes les métadonnées techniques (numéros d'étape, sous-titres, en-têtes de bandeau,
valeurs de mesure) en **IBM Plex Mono** 9,5 px, `letter-spacing: .12em` pour les en-têtes
en capitales.

### 1.2 Palette de catégories — la clé de voûte

Six teintes, **toutes à clarté et chroma identiques** en OKLCH. C'est ce qui empêche une
catégorie de dominer visuellement les autres : seule la teinte varie.

```css
--cat-3d:        oklch(.72 .13 255);  /* bleu     — 3D */
--cat-3dstudio:  oklch(.72 .13 300);  /* violet   — 3D Studio */
--cat-sprites:   oklch(.72 .13 200);  /* cyan     — Sprites 2D */
--cat-tuiles:    oklch(.72 .13 145);  /* vert     — Tuiles */
--cat-matieres:  oklch(.72 .13  80);  /* ambre    — Matières */
--cat-cartes:    oklch(.72 .13  25);  /* rouge    — Cartes */
```

Dérivés, à générer **par calcul depuis la teinte active**, jamais en dur :

```css
--cat:        <teinte de la catégorie active>;   /* posée par le conteneur de section */
--cat-fill:   oklch(from var(--cat) l c h / .14);  /* fond de ligne active, pastille */
--cat-line:   oklch(from var(--cat) l c h / .55);  /* bordure d'élément actif */
--cat-ink:    #14181d;                             /* texte sur aplat de teinte */
```

Si `oklch(from …)` n'est pas disponible dans la cible de build, exposer trois variables
par catégorie (`--cat-3d`, `--cat-3d-fill`, `--cat-3d-line`) générées à la compilation.
Ne pas repasser par du hexadécimal saisi à la main : la cohérence de clarté serait perdue.

L'or historique `#e6b23c` **reste** la couleur de marque, mais son emploi est désormais
restreint à ce qui n'appartient à aucune catégorie : barre supérieure, compteur de crédits,
puce d'enregistrement, badges de version, rail de navigation global.

### 1.3 Mouvement

```css
--ease-panel:  cubic-bezier(.22, 1, .36, 1);   /* repli, glissement, remplissage */
--ease-pop:    cubic-bezier(.34, 1.56, .64, 1); /* enfoncement de bouton, rebond */

--dur-panel:   460ms;  /* largeur/hauteur de zone escamotable, rotation du chevron */
--dur-fill:    440ms;  /* balayage du remplissage d'onglet */
--dur-label:   200ms;  /* disparition des libellés au repli */
--dur-press:   170ms;  /* durée de l'état enfoncé */
```

Respecter `prefers-reduced-motion: reduce` : conserver les changements d'état, ramener
toutes les durées à `1ms` et supprimer les cascades décalées.

---

## 2. Système d'icônes — glyphe bicolore (variante 1b)

### 2.1 Règles de dessin

- Grille **24 × 24**, rendu à **18 px** dans les bandeaux, **16 px** dans le rail Card
  Forge, **17 px** dans la barre horizontale.
- **Masses pleines** (`fill="currentColor"`), aucun contour, sauf l'icône News dont
  l'objet même est un trait (`stroke-width: 2.6`).
- **Deux niveaux d'opacité** : le sujet à `1`, le support/contenant entre `.26` et `.45`.
  C'est ce contraste interne qui rend le glyphe lisible à 16 px sur fond sombre, là où un
  filaire se referme.
- Une découpe interne se fait par `fill-rule="evenodd"` dans le même `path`, **jamais**
  par un tracé peint en couleur de fond : le glyphe doit rester valide sur un aplat coloré.
- Couleur pilotée exclusivement par `currentColor` : au repos `--txt-mid`, actif
  `var(--cat)`, sur aplat `--cat-ink`.

### 2.2 Bandeau de navigation — 11 icônes

Chaque entrée : `viewBox="0 0 24 24" fill="currentColor"`, rendu 18 px.

| Entrée | Sens retenu | Tracé |
|---|---|---|
| **Quick** | éclair — générateur 1-shot | `<path d="M13.8 2.6 6 14.2h4.6L9.6 21.4 18 9.6h-4.8z"/>` |
| **Studio** | graphe de nœuds | `<path d="M8.4 11.2h3.2V6.4h4v1.6h-2.4V12H8.4zM11.6 12.8h3.2v3.6h2.4V18h-4v-3.6h-1.6z" opacity=".45"/><rect x="2.8" y="9.2" width="5.6" height="5.6" rx="1.4"/><rect x="15.6" y="4" width="5.6" height="5.6" rx="1.4"/><rect x="15.6" y="14.4" width="5.6" height="5.6" rx="1.4"/>` |
| **Chapitres** | livre ouvert + lecture | `<path d="M3.8 4h6.6a1.6 1.6 0 0 1 1.6 1.6V20a2.4 2.4 0 0 0-1.7-.7H3.8z" opacity=".38"/><path fill-rule="evenodd" d="M20.2 4h-6.6A1.6 1.6 0 0 0 12 5.6V20a2.4 2.4 0 0 1 1.7-.7h6.5zM14.6 9.4 18 11.4l-3.4 2z"/>` |
| **Son & VFX** | forme d'onde | `<rect x="3" y="10.4" width="2.2" height="3.2" rx="1.1" opacity=".45"/><rect x="7.2" y="7" width="2.2" height="10" rx="1.1"/><rect x="11.4" y="4.2" width="2.2" height="15.6" rx="1.1"/><rect x="15.6" y="8" width="2.2" height="8" rx="1.1"/><rect x="19.8" y="10.4" width="2.2" height="3.2" rx="1.1" opacity=".45"/>` |
| **Montage** | pistes + tête de lecture | `<rect x="3" y="5.6" width="10.4" height="2.6" rx="1.3" opacity=".45"/><rect x="3" y="10.7" width="14.6" height="2.6" rx="1.3" opacity=".45"/><rect x="3" y="15.8" width="7.6" height="2.6" rx="1.3" opacity=".45"/><rect x="18.6" y="3.4" width="2" height="17.2" rx="1"/>` |
| **Scheduler** | calendrier + horloge | `<rect x="3.2" y="5.4" width="17.6" height="14.8" rx="2" opacity=".3"/><path d="M3.2 7.4a2 2 0 0 1 2-2h13.6a2 2 0 0 1 2 2V10H3.2z"/><path d="M12.9 12.6h-1.8v3.5l2.7 1.6.9-1.5-1.8-1z"/>` |
| **Templates** | blocs de mise en page | `<rect x="3.2" y="4.2" width="8.2" height="15.6" rx="1.6"/><rect x="13.2" y="4.2" width="7.6" height="6.8" rx="1.6" opacity=".38"/><rect x="13.2" y="13" width="7.6" height="6.8" rx="1.6" opacity=".38"/>` |
| **News** | ondes RSS *(tracé, pas masse)* | `fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"` puis `<path d="M5 11.4a8.2 8.2 0 0 1 8.2 8.2" opacity=".4"/><path d="M5 5.4a14.2 14.2 0 0 1 14.2 14.2"/><circle cx="5.6" cy="18.6" r="1.4" fill="currentColor" stroke="none"/>` |
| **Library** | couches empilées | `<path d="M12 2.8 21 7.2 12 11.6 3 7.2z"/><path d="M12 13.6 4.6 10l-1.6.8L12 15.2l9-4.4-1.6-.8zM12 18.2 4.6 14.6l-1.6.8L12 19.8l9-4.4-1.6-.8z" opacity=".42"/>` |
| **Game Assets** | grille + volume | `<rect x="3.4" y="3.4" width="7.4" height="7.4" rx="1.4" opacity=".42"/><rect x="13.2" y="3.4" width="7.4" height="7.4" rx="1.4" opacity=".42"/><rect x="3.4" y="13.2" width="7.4" height="7.4" rx="1.4" opacity=".42"/><path d="M16.9 12.6 20.6 14.8v4.4l-3.7 2.2-3.7-2.2v-4.4z"/>` |
| **Settings** | curseurs de réglage | `<rect x="3" y="7" width="18" height="2.2" rx="1.1" opacity=".42"/><rect x="3" y="14.8" width="18" height="2.2" rx="1.1" opacity=".42"/><circle cx="15.2" cy="8.1" r="2.8"/><circle cx="8.8" cy="15.9" r="2.8"/>` |

### 2.3 Bandeau Card Forge — 10 icônes

Rendu 16 px, alignées **à droite** de la ligne (le numéro d'étape occupe la gouttière
gauche).

| Étape | Sens retenu | Tracé |
|---|---|---|
| **01 Face** | recto : fenêtre d'illustration | `<rect x="5" y="3" width="14" height="18" rx="2.2" opacity=".3"/><rect x="7.4" y="5.4" width="9.2" height="8" rx="1.2"/>` |
| **02 Cadre** | double filet, centre évidé | `<path fill-rule="evenodd" d="M3.4 4.4h17.2v15.2H3.4zm2.8 2.8v9.6h11.6V7.2z"/><rect x="7.4" y="8.4" width="9.2" height="7.2" opacity=".3"/>` |
| **03 Typo** | lettre + ligne de base | `<path d="M12 3.6 19.6 18h-3.9L12 10.4 8.3 18H4.4z"/><rect x="8.4" y="13.4" width="7.2" height="2.4"/><rect x="4.4" y="19.8" width="15.2" height="1.8" rx=".9" opacity=".35"/>` |
| **04 Données** | tableau de champs | `<rect x="3.4" y="5" width="17.2" height="14" rx="2" opacity=".28"/><path d="M3.4 7a2 2 0 0 1 2-2h13.2a2 2 0 0 1 2 2v2.4H3.4z"/><rect x="6" y="11.8" width="5" height="1.9" rx=".9"/><rect x="13" y="11.8" width="5" height="1.9" rx=".9"/><rect x="6" y="15.3" width="5" height="1.9" rx=".9"/><rect x="13" y="15.3" width="5" height="1.9" rx=".9"/>` |
| **05 Volume** | plaques décalées = épaisseur | `<rect x="7.4" y="3.4" width="12.2" height="14.6" rx="2" opacity=".32"/><rect x="4.4" y="6.4" width="12.2" height="14.6" rx="2"/>` |
| **06 Matières** | sphère d'échantillon | `<circle cx="12" cy="12" r="8.6" opacity=".3"/><path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/>` |
| **07 Impression** | presse + feuille sortante | `<rect x="3.4" y="8" width="17.2" height="8" rx="1.8" opacity=".32"/><path d="M7 3.4h10V8H7z"/><rect x="7" y="13.6" width="10" height="7" rx="1.2"/>` |
| **08 Export 3D** | flèche sortante du bac | `<path d="M3.6 13.4h2.8v4.4h11.2v-4.4h2.8v6.2a1.8 1.8 0 0 1-1.8 1.8H5.4a1.8 1.8 0 0 1-1.8-1.8z" opacity=".32"/><path d="M12 2.6 17.2 8h-3.6v7.6h-3.2V8H6.8z"/>` |
| **09 Forge 3D** | cube + étincelle = génération | `<path d="M10.4 5.2 17.2 9v7.4l-6.8 3.8-6.8-3.8V9z" opacity=".32"/><path d="M10.4 5.2 17.2 9l-6.8 3.9L3.6 9z"/><path d="M19.6 2.2l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3-2.3-.9 2.3-.9z"/>` |
| **10 Import** | flèche entrante dans le bac | `<path d="M3.6 13.4h2.8v4.4h11.2v-4.4h2.8v6.2a1.8 1.8 0 0 1-1.8 1.8H5.4a1.8 1.8 0 0 1-1.8-1.8z" opacity=".32"/><path d="M12 15.8 6.8 10.4h3.6V2.8h3.2v7.6h3.6z"/>` |

**Deux définitions à confirmer avant implémentation** — signalées ici parce qu'elles
changent le dessin :

- **05 Volume** est lu comme *épaisseur / relief physique de la carte* → plaques décalées.
  S'il s'agit du **tirage** (nombre d'exemplaires), l'icône doit devenir une pile de cartes.
- **09 Forge 3D** est lu comme *génération d'un volume* → cube + étincelle. Si l'étape est
  un simple réglage de relief, l'étincelle est à retirer.

### 2.4 Barre horizontale — 6 icônes, **bords droits**

Rendu 17 px. Ces six-là sont dessinées **sans aucun rayon** (`rx` supprimé partout),
en cohérence avec la barre à angles vifs de la section 3. Ne pas réutiliser les variantes
arrondies.

| Onglet | Sens retenu | Tracé |
|---|---|---|
| **3D** | cube isométrique = le modèle | `<path d="M12 2.8 20.6 7.4v9.2L12 21.2 3.4 16.6V7.4z" opacity=".34"/><path d="M12 2.8 20.6 7.4 12 11.9 3.4 7.4z"/>` |
| **3D Studio** | viewport + cube = la scène | `<rect x="2.6" y="4" width="18.8" height="16" opacity=".3"/><path d="M12 7.4 16.2 9.8v4.8L12 17l-4.2-2.4V9.8z"/>` |
| **Sprites 2D** | planche de sprites | `<rect x="3" y="5" width="18" height="14" opacity=".3"/><rect x="5.4" y="7.4" width="5.4" height="4.6"/><rect x="13.2" y="12" width="5.4" height="4.6"/>` |
| **Tuiles** | damier raccordable | `<rect x="3" y="4.8" width="8.4" height="6.6"/><rect x="12.6" y="4.8" width="8.4" height="6.6" opacity=".34"/><rect x="3" y="12.6" width="8.4" height="6.6" opacity=".34"/><rect x="12.6" y="12.6" width="8.4" height="6.6"/>` |
| **Matières** | sphère d'échantillon | `<circle cx="12" cy="12" r="8.6" opacity=".34"/><path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/>` |
| **Cartes** | cartes empilées | `<rect x="4.6" y="6.4" width="10.4" height="13.8" opacity=".34" transform="rotate(-10 9.8 13.3)"/><rect x="10.2" y="4.6" width="9.6" height="15"/>` |

**Deux niveaux de sens volontaires**, à préserver : *3D* et *3D Studio* partagent le même
cube, l'un seul, l'autre posé dans un viewport — la parenté est lisible. *Matières* garde
exactement la même sphère dans la barre horizontale et à l'étape 06 de Card Forge : même
objet, même glyphe, deux emplacements.

### 2.5 Livraison technique suggérée

Un module par famille, exportant des composants dont la couleur vient de `currentColor` et
la taille d'une prop `size` :

```
src/icons/nav/*        11 icônes de navigation
src/icons/forge/*      10 icônes Card Forge
src/icons/category/*    6 icônes de catégorie, bords droits
src/icons/chevron.tsx   le chevron unique de la section 4
```

Aucune icône ne porte de couleur en dur. Aucune n'est un fichier PNG.

---

## 3. Barre horizontale colorée et propagation de la teinte

### 3.1 La barre (variante 2a)

Structure : `display: grid; grid-template-columns: repeat(6, 1fr); gap: 1px;` sur un fond
`--brd-hard`, avec `border: 1px solid var(--brd-hard)`. Le `gap` de 1 px **est** le
séparateur : pas de bordure par bouton, pas de pastille flottante.

**`border-radius: 0` sur la barre et sur chaque onglet.** C'est la demande explicite : la
barre remplace les onglets à coins arrondis de la version actuelle.

Chaque onglet, hauteur **46 px**, `display:flex; align-items:center; justify-content:center; gap:7px` :

1. Un **liséré bas de 2 px** dans la teinte de la catégorie, `position:absolute; left:0; right:0; bottom:0`, **toujours visible, y compris inactif**. C'est le point central de la proposition : la couleur *identifie* la catégorie, elle ne signale pas seulement la sélection. Un utilisateur reconnaît « Tuiles » au vert avant de lire le mot.
2. Un **calque de remplissage** `position:absolute; inset:0; background: var(--cat-n); transform-origin: left center; transform: scaleX(0 → 1); transition: transform var(--dur-fill) var(--ease-panel)`.
3. L'icône (17 px, section 2.4) et le libellé (11,5 px / 500), tous deux en `position:relative` pour passer au-dessus du remplissage.

États :

| État | Icône + libellé | Fond |
|---|---|---|
| Inactif | `var(--cat-n)` pour l'icône, `--txt-mid` pour le texte | `--srf-raised` |
| Survol | idem, `--srf-hover` | — |
| **Actif** | `--cat-ink` (#14181d) | aplat `var(--cat-n)`, balayé de gauche à droite |
| Enfoncé | — | `transform: scale(.94) translateY(1px)` pendant `--dur-press`, courbe `--ease-pop` |

L'animation au clic est donc double et lisible : le bouton s'enfonce brièvement, l'aplat
de couleur balaie la largeur de l'onglet, glyphe et libellé s'inversent en sombre. Aucun
indicateur ne se déplace d'un onglet à l'autre — chaque onglet possède sa propre couleur,
un curseur glissant serait contradictoire.

Libellés, verbatim : `3D` · `3D Studio` · `Sprites 2D` · `Tuiles` · `Matières` · `Cartes`.

### 3.2 Propagation de la teinte dans la section pilotée

**C'est la partie à ne pas sous-traiter au CSS de chaque écran.** L'onglet actif pose une
seule variable sur le conteneur de la section, et tout ce qui est en dessous l'hérite :

```jsx
const CAT_HUE = {
  '3d': 'oklch(.72 .13 255)',
  '3d-studio': 'oklch(.72 .13 300)',
  'sprites-2d': 'oklch(.72 .13 200)',
  'tuiles': 'oklch(.72 .13 145)',
  'matieres': 'oklch(.72 .13 80)',
  'cartes': 'oklch(.72 .13 25)',
};

<section data-category={active} style={{ '--cat': CAT_HUE[active] }}>
  {/* toute l'UI de la section, y compris Card Forge, ne lit plus que var(--cat) */}
</section>
```

Ce qui **doit** basculer sur `var(--cat)` dans le corps de la section — en remplacement
de l'or `#e6b23c` actuel :

- Étape active du bandeau Card Forge : numéro, icône, fond `--cat-fill`, filet gauche de 2 px.
- En-têtes de sous-panneau et leur filet supérieur (`ÉPREUVE DE CONTRÔLE`, `ROBUSTESSE`, `DÉCOR DE CADRE PAR IA`, `FENÊTRE D'ILLUSTRATION`).
- Boutons primaires de la section (`Construire l'épreuve de contrôle`, `Générer le décor`, `Relancer le balayage`) : fond `--cat-fill`, bordure `--cat-line`, texte `--txt-hi`.
- Remplissage de curseur (`OPACITÉ DU DÉCOR`), poignée comprise.
- Cadre de sélection et poignées dans `FENÊTRE D'ILLUSTRATION`, liséré de la carte en aperçu.
- Puces de bascule actives (`600` dans DÉFINITION, `Repères`), anneau de focus clavier.
- Chevrons de repli **de la section** (voir 4.3).

Ce qui **ne bascule pas** et reste neutre ou en or de marque :

- Barre supérieure, compteur de crédits, badges de service (`fal`, `heygen`, `voice`, `v2.5.0`), puce d'enregistrement — hors périmètre de catégorie.
- Rail de navigation gauche global : il pilote des sections *frères*, pas la catégorie courante ; il conserve l'or.
- Tout texte courant, toute mesure, tout tableau de contrôle. **Les couleurs sémantiques restent sémantiques** : les ✓ verts et les ✗ rouges des tableaux de robustesse ne prennent jamais la teinte de catégorie, même quand la catégorie est verte ou rouge. Ils utilisent des tokens dédiés (`--ok`, `--fail`) qui doivent être introduits s'ils n'existent pas.

**Budget de couleur : ~10 % de la surface de la section au maximum.** La teinte marque les
points d'action et l'état actif. Un fond de panneau teinté, un texte courant teinté ou une
bordure de conteneur teintée sortent du cadre.

**Transition entre catégories** : la variable change, tout ce qui l'hérite anime sa couleur
sur `300ms ease`. Ne pas animer la position ou la taille pendant un changement d'onglet.

**Accessibilité.** Les six teintes ont la même clarté, ce qui garantit un contraste uniforme
mais **ne suffit pas** : la couleur ne doit jamais être le seul porteur d'information.
L'onglet actif porte aussi son aplat plein et son inversion de texte ; l'étape Card Forge
active porte aussi son filet gauche. À vérifier au moment de l'intégration : texte
`--cat-ink` sur aplat `var(--cat)` doit dépasser 4,5:1 pour les six teintes.

---

## 4. Chevrons de repli / expansion — un seul système, partout

Aujourd'hui l'application mélange plusieurs affordances de repli. La règle devient unique.

### 4.1 Le glyphe

Un chevron plein, 12 px, à angles nets, dans la même famille bicolore que le reste :

```html
<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
  <path d="M14.8 5.6 9 12l5.8 6.4z"/>
</svg>
```

Pointe vers la **gauche** à l'état déployé. Une seule icône dans toute la codebase ; toutes
les orientations sont obtenues par rotation.

### 4.2 Le bouton porteur

Carré de **22 × 22**, `border-radius: 6px` (le bouton, pas le glyphe), fond
`--cat-fill` — ou `--srf-active` hors contexte de catégorie —, glyphe en `var(--cat)`.
Cible tactile portée à 32 px par du padding transparent. `aria-expanded` obligatoire,
`aria-controls` pointant sur le panneau, `aria-label` explicite
(« Replier le bandeau Card Forge »).

### 4.3 Orientations, par type de zone

Le chevron **pointe toujours dans la direction du mouvement de fermeture**. Un seul
composant, une prop `edge` :

| `edge` | Zone concernée | Déployé | Replié |
|---|---|---|---|
| `left` | bandeau de navigation, bandeau Card Forge (rails de gauche) | `rotate(0deg)` | `rotate(180deg)` |
| `right` | panneaux d'inspection à droite (`DÉCOR DE CADRE PAR IA`, `FENÊTRE D'ILLUSTRATION`) | `rotate(180deg)` | `rotate(0deg)` |
| `down` | sections empilables verticalement (`ÉPREUVE DE CONTRÔLE`, `ROBUSTESSE`, groupes de formulaire) | `rotate(-90deg)` | `rotate(90deg)` |

Rotation : `transition: transform var(--dur-panel) var(--ease-panel)`. **La rotation du
chevron et le mouvement du panneau partagent durée et courbe** — c'est ce qui donne
l'impression que le chevron pousse le panneau.

### 4.4 Comportement de repli d'un rail horizontal

Le rail passe de **236 px à 62 px** (navigation) ou de **210 px à 58 px** (Card Forge).

- La **largeur seule** s'anime, sur `--dur-panel` / `--ease-panel`. `overflow: hidden` et
  `white-space: nowrap` sur le conteneur.
- Chaque ligne reste un `flex` à trois zones : icône `flex:none`, libellé `flex:1; min-width:0; overflow:hidden`, méta `flex:none`. **L'icône ne bouge pas d'un pixel** pendant le repli — c'est le repère qui rend l'état replié utilisable.
- Le libellé s'échappe : `opacity: 1 → 0` sur `--dur-label`, `translateX(0 → -22px)` sur `380ms`, avec un **décalage en cascade de 25 ms par ligne** de haut en bas.
- Les icônes rebondissent en cascade au même rythme (`scale: 1 → .74 → 1.08 → 1` sur 460 ms), ce qui donne à la fermeture une lecture de haut en bas plutôt qu'un effondrement en bloc.
- L'état replié doit servir de vraie navigation : `title` ou infobulle sur chaque icône, ligne active toujours marquée par son filet gauche de 2 px.

### 4.5 Comportement de repli d'une section verticale

`grid-template-rows: 1fr` → `0fr`, ou `height` animée depuis `scrollHeight`, sur
`--dur-panel` / `--ease-panel`. L'en-tête reste visible et cliquable **sur toute sa
largeur** (pas seulement sur le chevron). Le contenu passe en `opacity: 0` sur
`--dur-label`.

### 4.6 Inventaire à couvrir

Repérés sur l'écran `Game Assets` ; à balayer dans l'ensemble de l'application, l'objectif
étant qu'**aucune autre affordance de repli ne subsiste** :

1. Rail de navigation gauche (`edge: left`)
2. Bandeau d'étapes Card Forge 01–10 (`edge: left`)
3. Panneau `DÉCOR DE CADRE PAR IA` (`edge: right`)
4. Panneau `FENÊTRE D'ILLUSTRATION` (`edge: right`)
5. Bloc `ÉPREUVE DE CONTRÔLE — TRAITS DE COUPE ET MIRES` (`edge: down`)
6. Bloc `ROBUSTESSE — LES 12 FORMATS, LES 2 BORNES DU RAYON` (`edge: down`)
7. Barre de format / définition / fond perdu (`edge: down`)
8. Colonne d'aperçu de carte (`edge: left`)
9. Tout groupe de formulaire replié dans les autres sections

**Persistance** : l'état de chaque zone est mémorisé par utilisateur, clé
`deepotus.panel.<id>.collapsed`, restauré au chargement **sans animation** (poser l'état
final, puis réactiver les transitions à la frame suivante).

---

## 5. État applicatif

```ts
type CategoryId = '3d' | '3d-studio' | 'sprites-2d' | 'tuiles' | 'matieres' | 'cartes';

activeCategory: CategoryId          // onglet de la barre horizontale ; pose --cat
pressedTab:     CategoryId | null   // effacé après --dur-press (170 ms)
panels:         Record<string, boolean>   // id de zone → replié ; persisté
forgeStep:      number              // 1..10, étape Card Forge active
```

`activeCategory` doit vivre au niveau de la section, pas dans la barre : la barre en est le
contrôle, la section en est la consommatrice via `--cat`. Chaque catégorie conserve son
propre `forgeStep` et son propre état de panneaux si le produit le justifie ; sinon,
partagés.

---

## 6. Ordre d'implémentation conseillé

1. **Tokens** — poser `--cat-*`, les dérivés, les tokens de mouvement, `--ok` / `--fail`. Rien d'autre ne peut avancer proprement avant.
2. **Chevron unique** — un composant, prop `edge`, `aria-expanded`. Remplacer les affordances existantes une par une (section 4.6). Chantier le plus large, le plus mécanique.
3. **Icônes** — les 27 tracés, en trois modules. Substitution 1:1, aucun changement de layout.
4. **Barre 2a** — bords droits, gap de 1 px, liséré permanent, remplissage balayé.
5. **Propagation** — poser `--cat` sur le conteneur de section, puis remplacer `#e6b23c` par `var(--cat)` **uniquement** dans la liste de la section 3.2. Passer en revue chaque occurrence restante de l'or : soit elle est de marque, soit elle est un oubli.
6. **Persistance** des panneaux, restauration sans animation.
7. **Passe `prefers-reduced-motion`** et vérification des contrastes.

---

## 7. Fichiers de référence

| Fichier | Contenu |
|---|---|
| `Icônes Deepotus.dc.html` | Prototype interactif. Tour **1** : variantes `1a` (filaire technique) et `1b` (glyphe bicolore, **retenue**), les 27 icônes en situation, repli des deux bandeaux cliquable. Tour **2** : variante `2a`, barre horizontale colorée à bords droits, clic animé. La grille de correspondances en bas du tour 1 documente le sens de chaque icône. |

Ouvrir le fichier dans un navigateur, cliquer les chevrons et les onglets : les durées et
les courbes du prototype sont celles à reproduire.

---

# 15-bis. État d'implémentation du handoff (26/08/2026, Claude Code)

## Les deux définitions à confirmer — TRANCHÉES PAR LE CODE

- **05 Volume = épaisseur / relief physique** (pas le tirage) : la pièce P5 dit
  « Épaisseur, coins, maillage à 3 îlots UV, aperçu 3D et tourne-disque »
  (`frontend/cardforge/index.html:129`, `js/mod-solid.js`). → l'icône
  **plaques décalées est la bonne**, reprise telle quelle.
- **09 Forge 3D = génération d'un volume** (pas un réglage de relief — le
  relief, c'est P5) : « l'entrée du graphe 3D » (`index.html:149`), la voie
  Meshy réelle à crédits (mémoire phase 6). → **cube + étincelle gardés**.

## Correspondance des tokens (spec → codebase)

Le spec §1.1 nomme des surfaces `--srf-*` / `--txt-*` « inchangées » : dans la
codebase elles existent déjà sous d'autres noms (deepotus.tokens.css) et CE
SONT ELLES qui font foi — aucune surface n'a été redéfinie :
`--srf-app→--bg-base` · `--srf-panel→--bg-panel` · `--srf-raised→--bg-panel-2`
· `--brd-hard→--stroke` · `--brd-soft→--stroke` · `--txt-hi→--ink-strong` ·
`--txt-base→--ink` · `--txt-mid→--ink-soft` · `--txt-low/faint→--ink-muted`.
L'« or historique » du spec (#e6b23c) est en réalité `--accent:#f0b429` — la
règle (l'or = marque seulement) s'applique au token réel.

## Ce qui est LIVRÉ

1. **Tokens** (`frontend/shared/deepotus.tokens.css`, copié `dist/shared/`) :
   les 6 teintes `--cat-*` OKLCH, `--cat` (défaut = or de marque), dérivés
   calculés `--cat-fill/-line` (`oklch(from …)`), `--cat-ink`, `--ok/--fail`,
   tokens de mouvement (`--ease-panel/-pop`, `--dur-panel/fill/label/press`).
   Thème clair : mêmes teintes à clarté .52 (contraste). Le kill-switch
   `prefers-reduced-motion` global du fichier couvre déjà toutes les durées.
2. **Cardforge** (source `frontend/cardforge/`) : pose `--cat: var(--cat-cartes)`
   ; les 10 icônes 1b du rail (core.js `RAIL_SVG`, rendu 16 px, l'emoji des
   modules reste le repli sanscore) ; le chevron UNIQUE (`CF.chevronSVG`,
   bouton 22×22 r6 fond `--cat-fill`, rotation `--dur-panel`/`--ease-panel`)
   posé sur rail-fold, stage-fold et les colonnes P2 (garde `typeof`, patron
   T6-G) ; étape active du rail en teinte (fond `--cat-fill`, filet gauche
   2 px, numéro+icône `--cat`) ; `.btn.strong` en `--cat-fill/-line` ; focus
   ring `--cat-line`. **Arbitrage assumé : `.btn.primary` (la seule DÉPENSE)
   reste à l'or de marque — le coût est une sémantique de marque, pas de
   catégorie.** Suites core/frame/type vertes (14 s / 55 s / 681 s).
3. **Bundle** (`scripts/patch_bundle_dzdesign.py`, chaîné après navrail,
   backup `.bak_dzdesign`) : les 10 icônes nommées de la carte (zap, flow,
   film, wave, layers, calendar, grid, rss, folder, cog) remplacées par les
   tracés 1b — remplacement par équilibrage de parenthèses, jamais de regex ;
   Game Assets gagne SA clé `gamegrid` (grille+volume) au lieu de partager
   `grid` avec Templates ; la barre du hub passe en **2a** (grid 6×1fr,
   gap 1 px = séparateur, `border-radius:0`, liséré bas 2 px PERMANENT par
   catégorie, remplissage balayé `scaleX` 440 ms, glyphe+libellé inversés en
   `--cat-ink` sur l'aplat, `:active` scale .94, libellés verbatim sans
   emoji) ; le conteneur du hub pose `--cat` + `data-category` — toute la
   section en hérite.

## Fin du chantier (26/08, seconde passe) — TOUT le « reste » est soldé

4. **La cascade de repli du rail Cardforge** (§4.4) : `buildRail` pose
   `--ri` (le rang) sur chaque ligne ; l'étiquette s'échappe (opacité
   `--dur-label`, glissement −22 px / 380 ms, décalage 25 ms × rang,
   hauteur sur `--dur-panel`) et les icônes rebondissent en cascade
   (`dzRailPop` 1→.74→1.08→1 sur 460 ms). Le rebond n'est ARMÉ que par le
   geste (classe `.rail-anime` posée par `setFold`, retirée à 700 ms) : la
   restauration au chargement pose l'état final **sans animation** (§4.6).
5. **Zone 7 — la barre de format s'escamote** (`edge: down`) : chevron
   unique en bout de barre (`#fmtFoldBtn`, −90° déployé / 90° replié),
   `max-height` animée `--dur-panel`, contenu en `opacity --dur-label`,
   clé `dz_cf_fmt`, aria-expanded/controls — le même patron `setFold`
   que le rail et la scène.
6. **Le chevron du bundle unifié** (`patch_bundle_dzchevron.py`, chaîné
   après dzdesign) : les entrées `caret` (triangle bas) et `caretR`
   (triangle droit) de la carte d'icônes deviennent LE chevron du design —
   base pointe gauche, `caretR` = même tracé tourné 180°. Le bouton
   « Collapse » du rail de navigation pointe désormais dans la direction du
   mouvement de fermeture ; les en-têtes repliables du bundle et les
   flèches « suivant » partagent le même glyphe par rotation.
7. **Zone 9 — inventaire clos** : les clés d'état d'écran des pièces
   (`dz_cf_*`) ne portent plus AUCUNE affordance de repli non convertie —
   `type_mono` est un sélecteur de nombre de colonnes, `forge`/`deck*` des
   sélections de vue/document, `zoom` la loupe. Rail, scène, colonnes P2,
   barre de format : tous au chevron unique.
8. **La passe de contraste 4,5:1 : LES SIX PASSENT** (calcul WCAG,
   OKLCH→sRGB, texte `--cat-ink #14181d` sur aplat `oklch(.72 .13 h)`) :
   3D 7,18:1 · 3D Studio 6,87:1 · Sprites 7,65:1 · Tuiles 7,55:1 ·
   Matières 7,09:1 · Cartes 6,80:1.

**Écart assumé restant** (dit, pas caché) : la transition de teinte 300 ms
au changement de catégorie (§3.2) n'a pas de consommateur visible côté
bundle (les contenus de section sont des iframes qui posent leur propre
`--cat`) — à brancher le jour où un écran du hub lit `--cat` en direct.

## Ajout du 27/08/2026 — catégorie « Vectorlab » au rail (chantier pont cartes)

La famille s'agrandit d'une entrée de navigation, dans les règles du
handoff (§15-2 : grille 24×24, masses pleines `currentColor`, sujet à 1 /
support .26–.45, découpes evenodd, jamais de couleur en dur ni de PNG).

- **Icône `vectorpen`** — sens : courbe de Bézier + ancres + poignées,
  l'écho exact du mode nœuds de l'éditeur (ancres carrées à 45°). Sujet
  (opacité 1) : le ruban de courbe (bande pleine ~2,6 px entre deux
  cubiques) tendu de l'ancre bas-gauche à l'ancre haut-droite, plus les
  deux ancres. Support (.32) : la barre de poignée à −45° croisant le
  ventre de la courbe, terminée par deux pastilles rondes. Tracé complet :

  ```html
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <rect x="1.7" y="7.8" width="14" height="1.7" rx=".85"
          transform="rotate(-45 8.7 8.7)" opacity=".32"/>
    <circle cx="13.6" cy="3.7" r="2" opacity=".32"/>
    <circle cx="3.7" cy="13.6" r="2" opacity=".32"/>
    <path d="M4.1 18.6 C4.1 9 9 4.1 18.6 4.1 L18.6 6.7 C10.4 6.7 6.7 10.4 6.7 18.6 z"/>
    <rect x="3.4" y="16.6" width="4" height="4" transform="rotate(45 5.4 18.6)"/>
    <rect x="16.6" y="3.4" width="4" height="4" transform="rotate(45 18.6 5.4)"/>
  </svg>
  ```

- **Teinte `--cat-vectoriel`** : `oklch(.72 .13 340)` (rose vitrail),
  thème clair `oklch(.52 .12 340)` — mêmes clarté/chroma que les six
  teintes du §1.2, hue au milieu du plus grand arc libre de la roue
  (300→25), donc distincte d'au moins 40° de toute voisine. Ajoutée aux
  trois feuilles qui font système : `frontend/shared/deepotus.tokens.css`
  (source), sa copie servie `frontend/dist/shared/`, et la couche tokens
  du bundle `frontend/dist/theme-v2.css`. Le rail lui-même RESTE à l'or de
  marque (§3.2) : la teinte vit dans la surface `/vectorlab/`
  (vectorlab.css importe la feuille partagée et pose
  `--cat: var(--cat-vectoriel)`).

- **Entrée nav** : `{id:"vectorlab", label:"Vectorlab", icon:"vectorpen",
  desc:"Éditeur vectoriel & vitrail", new}` entre Game Assets et
  Settings ; la vue est une iframe `/vectorlab/` (bibliothèque sans
  `?doc`, éditeur avec). Posée par `scripts/patch_bundle_vectorlab.py`
  (queue de chaîne, backup `.bak_vectorlab`, jamais de repatch_all —
  mêmes DANGERS que cardforge).

# 15-ter. Ajout du 28/08/2026 — les animations de MENU du bundle (§4.4)

Le rail de navigation du bundle (composant `tg`) savait se replier mais
sans les animations du handoff : la largeur glissait sur les anciens
tokens (`--dur-3`), et surtout les libellés étaient DÉMONTÉS du DOM à
l'instant du repli (`!n&&…`) — aucune échappée ni cascade n'était même
jouable. `scripts/patch_bundle_dzrailmotion.py` (queue de chaîne, backup
`.bak_dzrailmotion`, marqueur `__dzNavMotion`) applique le patron du rail
Cardforge :

- **largeur** sur `--dur-panel`/`--ease-panel` (460 ms, la courbe du
  handoff) ; `overflow:hidden` sur l'aside ;
- **libellés toujours montés**, échappée `opacity --dur-label` +
  `translateX(-22px)/380 ms`, **décalage 25 ms × rang** (`--ri` posé par
  la ligne) ; badge « new » = méta masquée au repli ;
- **icônes** : rebond `dzNavPop` (1→.74→1.08→1 sur 460 ms) en cascade,
  **armé par le geste seulement** — classe `dzNavAnime` posée sur `<body>`
  (React repeint le className de l'aside à chaque bascule : une classe
  posée sur lui serait perdue par le rendu même qu'elle habille) par
  l'intercepteur de persistance du patch navrail, retirée à 700 ms ; la
  restauration `dz_nav_collapsed` au chargement pose l'état final SANS
  animation (§4.6) ;
- **l'icône ne bouge pas d'un pixel** (§4.4) : padding et alignement de
  ligne deviennent constants — le rail replié est aligné à gauche comme
  le prototype, plus centré ;
- `prefers-reduced-motion` : durées à 1 ms, cascade et rebond supprimés,
  états conservés (§1.3) — en plus du kill-switch global des tokens.

Écart assumé : les largeurs restent 232→64 (cotes réelles du bundle,
même règle de correspondance que §15-bis) — le prototype disait 236→62.
