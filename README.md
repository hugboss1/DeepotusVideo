# 🐙 Deepotus Video Gen — v1.15.1

Local Windows studio for generating 9:16 crypto/Web3 videos — Seedance clips,
HeyGen talking avatars, spatial compositions, and RSS→reel news posts — with a
node-based **Studio**, a **Scheduler**, a real-time **cost widget**, and
**bring-your-own** API keys. Everything runs on your machine; only provider
calls (fal.ai, HeyGen, ElevenLabs, Anthropic/OpenAI/Gemini) and your publishes
leave it.

## Repository layout
- **`backend/`** — FastAPI app (Python). Source of truth for `/api/*` and the
  app version (`app/config.py`). Frontend is served from here at `/`.
- **`frontend/dist/`** — the **compiled** React bundle (`assets/index-*.js`) +
  `index.html`. ⚠️ The React **source is not in this repo** — the app ships
  compiled-only, and UI changes are made by surgically patching the minified
  bundle. `package.json` is kept for reference.
- **`installer/deepotus.iss`** — Inno Setup script that packages the whole app
  into a one-file installer.
- **`scripts/`** — silent launcher + `build-installer.ps1` (full build).
- **`docs/guide/`** — illustrated FR/EN user guide (HTML + PDF), served in-app
  at `/guide`.
- **`assets/`** — brand logo/icons.

**Not tracked** (see `.gitignore`): the bundled embedded **Python runtime**
(`runtime/`, ~137 MB) and **ffmpeg** (`bin/`, ~193 MB) — fetched at build time;
the built installer (it's a Release asset); and any secrets. **Your API keys
and database are never in this repo** — they live per-machine in
`%LOCALAPPDATA%\DeepotusVideoGenData`.

## Use it on any machine (easiest)
Download the latest installer from the **[Releases](../../releases)** page and
run it. It's self-contained (bundles Python + ffmpeg, zero prerequisites),
installs to `%LOCALAPPDATA%\DeepotusVideoGen`, and preserves your data across
reinstalls. After install, launch from the desktop shortcut and paste your keys
in **Settings → API keys**.

## Build from source
`powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1` —
downloads the embedded Python + ffmpeg, installs backend deps, and compiles the
installer (auto-installs Inno Setup 6 via winget if missing). Needs a build
Python on PATH matching the embeddable minor version.
> Note: `scripts\build-installer.ps1` (`$StageRoot`) and `installer\deepotus.iss`
> (`StageDir`, `OutputDir`) contain machine-specific paths — adjust them for
> your machine before building.

## Required API keys (bring-your-own)
**fal.ai** is required (images + video). Optional: **HeyGen** (avatars),
**ElevenLabs** (voiceover), **Anthropic/OpenAI/Gemini** or local **Ollama**
(news summaries, marketing plans, AI script polish), **X/Telegram**
(auto-publish). See `backend/.env.example`.

---

> Historical changelog (v1.8.0 and earlier) below.

# 🐙 Deepotus Video Gen — v1.8.0 "Reef Edition"

## 🆕 What's new in v1.8.0

Major UI refonte (Direction B — "Reef") shipped from the Claude Design handoff.
The old 5-tab grid is gone; everything now lives in a Sidebar shell with a
permanent JobDock and a brand-red Deepotus logo.

| Feature | Description |
|---|---|
| **Sidebar shell** | Collapsible left nav (Quick · Studio · Scheduler · Templates · News · Library · Settings), persistent JobDock at the bottom, sticky topbar with health badges + ⌘K command palette. |
| **🌊 Node Studio** | New visual graph editor — drag nodes, connect typed ports (image / video / audio / av / text / data), 30+ node types across 7 categories (Sources / Generators / Audio / Edit / Composition / Master / Output), 4 starter graphs (Seedance solo · Avatar post · News reel · Timeline), live `▶ Run` cascade with halo pulse, `◐ Preview` local-only path, mini-map, inspector. |
| **📅 Scheduler** | Week calendar of scheduled posts + per-post draggable node graph (`Render` → `Caption` → one `Channel` node per target). Bridge from Studio: a `Render` node has a "Schedule this render" CTA that drops a draft on tomorrow's slot. |
| **🐙 Splash + Onboarding** | Animated red rotating logo splash (~2.5s), then 5-step wizard (Welcome / Persona / Providers / Channels / Ready). Replayable from the topbar 🐙 or ⌘K. |
| **👤 Personas** | Persona creator wizard (voice, vocabulary, brand bible). Multiple personas per install; the active one is selectable in Settings and surfaces as a chip in Quick. |
| **🔌 Connected accounts** | Settings → Connected accounts: credential blocks for X / Telegram / YouTube / Instagram with Connect / Manage / Disconnect / Test-post actions. |
| **🎨 Token system** | New `tokens.css` (surfaces, ink, stroke, brand red, cyan / violet / amber / green accents, node port colors, radii, shadows, motion). Single source of truth, themable via the Tweaks panel. |
| **🖼 Library uploads** | Drag-drop or button upload on the Images tab. New uploads get a brand-red border + "NEW" badge. |
| **✨ Prompt generator** | Modal with deterministic ingredient picker (subject / mood / motion / lens / palette / detail) + optional backend `/api/prompt/build` refinement, plus a curated prompt-template gallery in Quick. |

No new backend deps. No new DB columns. Backend version bump only (`/api/health` → `1.8.0`). The legacy `src/components/` (ImagePicker, GenerationForm, …) is kept on disk for rollback but no longer routed.

Upgrade via `scripts/upgrade-from-v1.7.2.ps1` (data-preserving, rebuilds the frontend).

---

> v1.7.2 base below.

# 🐙 Deepotus Video Gen — v1.7.2 "Anti-Cut + Rename Edition"

## 🆕 What's new in v1.7.2

| Feature | Description |
|---|---|
| **No more avatar cut-off** | The renderer no longer truncates a talking avatar. In a **post template** (e.g. `tpl_news_reel`) the output length is now driven by the avatar's *real* duration (`audio.master_track: "from_slot:avatar"` + a tunable `tail_pad_s`), not a fixed canvas duration. In the **timeline**, a clip's own audio (avatar voice) is now carried through the montage, delayed to its position, and never dropped. |
| **Per-clip length mode** | Each timeline clip has **Fixed** (trim/pad to a set length, the old behaviour) or **Source** (play the clip's full real duration — never trims the avatar). |
| **🎯 Fit to source** | One click reads a picked *existing* render's exact duration (ffprobe), locks the clip to it and sets the avatar gauge — so the animation clips can be calibrated to match. |
| **Tail-pad fine-tune** | Per-clip (timeline) and per-template (`audio.tail_pad_s`, news-reel default 0.8s) slider adds a safety pad so the last word/syllable always lands before any fade-out. |
| **Rename renders** | A **Render name** field in the Timeline tab labels the job at creation; the **Job Queue** has an inline rename on any render. Names show in the queue and the "existing" clip/audio pickers. |

`GET /api/jobs/{id}` now returns `duration_real_s` (ffprobe of the final video) and `title`; `PATCH /api/jobs/{id}` renames a render. New DB column `title` (auto-migrated, data-preserving). No new deps.

---

> v1.7.1 base below.

# 🐙 Deepotus Video Gen — v1.7.1 "News-to-Video + Timeline Edition"

## 🆕 What's new in v1.7.1

| Feature | Description |
|---|---|
| **🎬 Timeline editor** | Templates tab → **🎬 Timeline**: a simple Remotion-style montage. Order clips by drag, resize each clip's length (5s steps for Seedance), pick a transition between each (crossfade / cut / fade-black / glitch / slide / flash), **split** a clip in two, choose output **format** (9:16 / 1:1 / 16:9 / 4:5), optional **audio track** (upload/existing, volume), duration-vs-avatar gauge. |
| **Seedance length fit** | Seedance generates ≤10s natively; longer targets (5s increments, up to 60s) are extended via ffmpeg (loop / hold) to match a HeyGen avatar. |
| **Chain → finalise** | The timeline renders to a job (queue) reusable via the **"existing"** source in any post template (e.g. `tpl_news_reel`). |
| **Persistence** | The template draft, slot inputs, timeline structure & sources persist across edit↔render, tab switches and reloads (localStorage + inline render). |

Built-ins: `tpl_timeline`, `tpl_montage_film` (+ the v1.6 layout templates). New Python deps unchanged from v1.7 (`feedparser`, `trafilatura`); no new frontend deps. Upgrade via `scripts/upgrade-from-v1.6.ps1` (data-preserving).

---

> v1.7 base below.

# 🐙 Deepotus Video Gen — v1.7 "News-to-Video Edition"

**Cinematic UGC video generator** for the deepotus Solana memecoin X account. Multi-provider with composition, custom avatars, a visual node template editor, and a daily news-to-video pipeline.

Pipelines:
- **Seedance 2.0** (fal.ai) — image-to-video cinematic clips
- **HeyGen** — talking avatar videos from scripts (with **custom photo avatars**)
- **Composition** — combine both into one video (sequential transition OR split-screen)
- **🎨 Templates** — design reusable multi-clip 9:16 layouts in a visual editor, fill slots with Seedance/HeyGen/uploads/existing renders, render to a single MP4
- **📰 News** — scrape RSS/Atom feeds + article URLs, select headlines, auto-generate a deepotus-voice script + an animated news reel, compose into a post-ready 9:16 MP4

Stack: Python FastAPI · React + Vite + Tailwind + react-konva · SQLite · ffmpeg · fal.ai · HeyGen · ElevenLabs · feedparser · trafilatura.

---

## 🆕 What's new in v1.7

| Feature | Description |
|---|---|
| **📰 News tab** | Manage RSS/Atom feeds + single-article URLs (persisted, `assets/news/`). In-app **daily auto-refresh** while running + manual Refresh. Searchable, checkbox-selectable headline list. |
| **News → script** | Selected headlines → deepotus-voice spoken script (voice mode, FR/EN, length, optional angle) + suggested caption/hashtags. Deterministic + persona-driven. |
| **Brand scrub** | Ingested headlines are scrubbed of hype vocabulary (moon/lambo/1000x/LFG/hodl…, inflection-tolerant) so external text never breaks brand voice — independent of persona config. |
| **News reel (ffmpeg)** | Branded 1080×1920 animated reel: wordmark + per-headline cards (timed fades, drift, accent) + scrolling ticker. Reuses the v1.6 effects engine — no heavy deps. Remotion is an optional engine hook. |
| **One-click Build post** | News reel + HeyGen avatar reading the script, composed via the built-in `tpl_news_reel` template → final post MP4 + caption. |

New Python deps: `feedparser`, `trafilatura`. **After upgrading, run `pip install -r requirements.txt --upgrade` in the backend venv** (the upgrade script does this for you). No auto-posting — the app produces the MP4 + caption; you post to IG/X manually.

---

## 🆕 What's new in v1.6

| Feature | Description |
|---|---|
| **🎨 Templates tab** | A visual node editor (react-konva). Drag region presets onto a 1080×1920 canvas, snap to a 60px grid, set z-index, save reusable JSON templates. 6 built-ins ship pre-loaded. |
| **Layout templates** | `video_slot` / `image_slot` / `text_slot` / `text` / `brand_strip` regions with cover/contain/stretch/crop fit modes, per-region audio volume, fades, and `-14 LUFS` loudness. |
| **Slot-based render** | Render mode: fill each slot with a Seedance generation, a HeyGen avatar, an upload, or text → all slots resolve in parallel → ffmpeg composites a 1080×1920 H.264 MP4. |
| **Voice-mode propagation** | A template-level voice mode (Oracle/Alpha/Zen/Memer) flows into every generated sub-clip that didn't set its own. |
| **🖥️ Desktop launcher** | A Desktop shortcut runs `scripts/launch.ps1` — Step 1 walks you through setting API keys, Step 2 starts the services. |

The 6 built-in templates: classic vstack 50/50, alpha reel 60/30/10, oracle full + lower-third, three-act sequential, PIP corner avatar, hstack left/right dialogue. Built-ins are immutable; saving over one creates a fresh `tpl_user_*` copy. New endpoints are namespaced under `/api/layout-templates` (the existing `/api/templates` Seedance prompt-template endpoint is unchanged).

---

## 🆕 What's new in v1.5

| Feature | Description |
|---|---|
| **📸 Photo Avatar Upload** | Drag-drop a photo (PNG/JPG/WEBP, max 10MB) → HeyGen creates a custom talking avatar in 10-30s. Use it like any HeyGen avatar. Cost: ~$0.20 per avatar creation. |
| **🧠 Universal PromptBuilder** | One Builder that adapts to where you are: HeyGen → generates **scripts** from intent (with voice mode tone); Composition → generates **both sides** (Seedance prompt + HeyGen script) coherently per layout. |
| **Layout-aware coherence** | Composition Builder knows the difference: Sequential → avatar sets up + Seedance pays off; Split → avatar narrates + Seedance shows in parallel. |
| **HeyGen Builder voice modes** | All 4 brand voice modes (Oracle / Alpha / Zen / Memer) produce structurally distinct scripts (hook + body + sign-off). Vocabulary filter still applies. |

### How the Universal Builder works

In **HeyGen mode**: Click "🧠 Show builder" → type your intent → pick voice mode + max words → the builder generates a structured 3-part script (hook, body, sign-off) in your chosen tone. The script auto-fills the Script textarea + caption.

In **Composition mode**: Same UI, but the Builder calls `/api/prompt/build-composition` which produces BOTH a Seedance prompt AND a HeyGen script with explicit coherence:
- **Sequential layout**: Avatar's last words are a transition cue ("Watch.", "Now.", "Look."). Seedance prompt is the visual payoff.
- **Split layout**: Avatar narrates what Seedance is showing simultaneously.

### What's still in v1.5 from earlier versions

From v1.4: Provider tabs (Seedance/HeyGen/Composition), HeyGen integration, composition pipeline (sequential + split-vstack + split-hstack), avatar/voice dropdowns, queue provider badges.
From v1.3.1: Voice modes, vocabulary filter, persona-aware ElevenLabs.
From v1.3: Batch multi-seeds, compare grid, bulk batch delete.
From v1.2: Templates (20), Builder, first-last frame transitions, Job clone/delete.

---

## 🔑 Get your HeyGen API key

1. Go to https://app.heygen.com/api (Settings → API → New Key)
2. Copy the key (format: `sk_V2_hgu_...`)
3. ⚠️ The key is shown once — copy before closing the modal
4. Pricing: pay-as-you-go in credits. Avatar V ~6 credits/min video. Minimum top-up $5.

---

## ⬆️ Upgrade to v1.6

### Recommended — single upgrade from v1.4 (or v1.5) → v1.6

`upgrade-from-v1.4.ps1` is a **full self-contained** upgrade: it backs up your install to `<path>.bak.<timestamp>`, swaps in the v1.6 codebase, and **preserves your user data** — `backend\.env`, `assets\images\`, `assets\outputs\`, `backend\deepotus.db`, and `backend\app\personas\deepotus.json` (never overwritten). No DB migration step (the DB auto-migrates on startup; v1.6 adds no new columns). It works from a v1.4 or v1.5 install.

```powershell
cd D:\olivi\telechargements
Expand-Archive deepotus-video-gen-v1.6.zip -DestinationPath . -Force
cd deepotus-video-gen
powershell -ExecutionPolicy Bypass -File .\scripts\upgrade-from-v1.4.ps1 -TargetPath "C:\Users\olivi\X-content\deepotus-video-gen"
```

### Older installs (v1.0–v1.3)

Use the **migrate** script (backs up, fresh-installs v1.6, restores your data):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\migrate-from-v1.ps1 -InstallPath "C:\path\to\your\old\install"
```

### After upgrading — install the new frontend dependency

v1.6 adds **react-konva** (the visual editor). After any upgrade path, install frontend deps once:

```powershell
cd C:\Users\olivi\X-content\deepotus-video-gen\frontend
npm install
```

### Set up the Desktop launcher (optional, recommended)

```powershell
cd C:\Users\olivi\X-content\deepotus-video-gen
powershell -ExecutionPolicy Bypass -File .\scripts\create-desktop-shortcut.ps1
```

This adds a **"Deepotus Video Gen"** Desktop shortcut that runs `scripts\launch.ps1`: it walks you through API keys first (opens `backend\.env`), then starts the services. You can also launch manually with `.\scripts\run.ps1`.

Hard-reload the browser (Ctrl+F5). The header should show `v1.6` and a **🎨 Templates** tab.

---

## 🎬 How to use the new providers

### HeyGen mode (avatar video)
1. Click **🎤 HeyGen** in the provider tabs
2. Right panel loads your avatars + voices automatically
3. Pick an avatar (the dropdown shows name/gender)
4. Pick a voice (English + French voices available depending on your account)
5. Write a script (≤4900 chars)
6. Optional: pick a voice mode (Oracle/Alpha/Zen/Memer) — adjusts the tone of the auto-generated caption
7. Click **🎤 Generate Avatar Video**
8. The queue shows the job with a **🎤 HG** badge

### Composition mode (Seedance + HeyGen combined)
1. Click **⚡ Composition** in the provider tabs
2. Pick a **Seedance start image** (left panel) — this becomes the animation side
3. Pick a **Seedance template** (mid panel)
4. Pick an **avatar + voice** (right panel)
5. Write a **script** for the avatar
6. Choose a **layout**:
   - **Sequential**: avatar speaks → cyan flash → Seedance animation plays
   - **Split vstack**: Seedance animation on top, avatar reading on bottom (reaction style)
   - **Split hstack**: Seedance left, avatar right
7. For split modes: choose **audio source** (default: HeyGen avatar voice)
8. Click **🐙 Generate Composition**
9. Both clips generate in parallel (~30-90s), then ffmpeg composes them
10. The queue shows the composition with a **⚡ COMP** badge

### Estimated costs
- Seedance only: ~$0.30 per 5s clip
- HeyGen only: ~$0.40 per 5s avatar clip (varies with avatar engine)
- Composition: ~$0.70 (both costs combined; ffmpeg compositing is free, runs locally)

---

## 🚀 Fresh install (Windows)

This is the **bulletproof** sequence — works on Windows 10/11 with Python 3.13, fresh node, antivirus quirks.

### Prerequisites

- **Python 3.10+** — https://python.org/downloads/  
  ⚠️ Check "Add Python to PATH" during install. If `python` opens Microsoft Store, disable the stubs in `Settings > Apps > Advanced > App execution aliases`.
- **Node.js 20+** — https://nodejs.org
- **ffmpeg** — install steps below

### 1. Extract

```powershell
cd C:\Users\YourName\Projects
Expand-Archive deepotus-video-gen-v1.2.zip -DestinationPath . -Force
cd deepotus-video-gen
```

### 2. Install ffmpeg (one-time)

```powershell
New-Item -ItemType Directory -Force -Path C:\ffmpeg | Out-Null
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile C:\ffmpeg\ffmpeg.zip
Expand-Archive C:\ffmpeg\ffmpeg.zip -DestinationPath C:\ffmpeg -Force
$ffmpegDir = (Get-ChildItem C:\ffmpeg -Directory | Where-Object { $_.Name -match "ffmpeg" } | Select-Object -First 1).FullName
[Environment]::SetEnvironmentVariable("PATH", "$ffmpegDir\bin;" + [Environment]::GetEnvironmentVariable("PATH","User"), "User")
```

**Close PowerShell, reopen.** Verify with `ffmpeg -version`.

### 3. Antivirus exclusion (only if you have Avast/Norton/McAfee)

In your AV settings, add this folder to "trusted folders" / "exclusions":
- `C:\Users\YourName\Projects\deepotus-video-gen`
- `C:\Users\YourName\AppData\Local\npm-cache`

This avoids `EFTYPE` / `EPERM` errors during npm install.

### 4. Install dependencies

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

cd ..\frontend
npm install
cd ..

Write-Host "INSTALL COMPLETE" -ForegroundColor Green
```

### 5. Add your fal.ai key

```powershell
notepad backend\.env
```

Paste after `FAL_KEY=`. Save, close.

### 6. Launch

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
```

Browser opens at `http://localhost:5173` after ~10s.

---

## ⬆️ Upgrade from v1.1

If you already have v1.1 installed somewhere, you can patch it without losing your data:

```powershell
# From the v1.2 folder (the new extract)
powershell -ExecutionPolicy Bypass -File .\scripts\upgrade-from-v1.1.ps1 -TargetPath "C:\path\to\v1.1\install"

# Then upgrade Python deps in the existing venv
cd C:\path\to\v1.1\install\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
```

The DB auto-migrates on next start — your existing jobs are preserved with `seed: null` (you can't clone them with seed, but everything else works).

---

## 🎬 How to use the new features

### First-last frame transitions
1. Click **"Set End (transition)"** in the image picker (top of left panel)
2. Click any image — it becomes the END frame (violet border)
3. Switch back to **"Set Start"** and pick the start frame
4. Generate — the pipeline auto-routes to Seedance Lite (the variant that supports first-last frame)

### Prompt Builder (free-text → structured prompt)
1. In the Config panel, switch to **"🧠 Builder"** tab
2. Type your intent in plain English/French (e.g. "phone showing chart pumping with shocked face in dark room")
3. Toggle "Inject deepotus DNA" if you want the system to add mascot/deep-sea/brand cues automatically
4. Click **"✨ Generate prompt"** — the result fills the textarea
5. Edit the prompt directly in the textarea if you want
6. Hit **Generate Video** — the builder prompt is used instead of templates

The builder detects camera moves, lighting, and pacing from your text:
- "neon", "cyberpunk" → cyan/magenta neon lighting
- "shocked", "react", "fast" → fast pacing + handheld camera
- "underwater", "abyssal" → bioluminescent lighting
- "push in", "approach" → slow push-in camera
- + 20 more keyword patterns

### Clone for A/B variations
1. Open any completed job in the Queue panel
2. Click **"🔁 Clone"** at the bottom
3. The form pre-fills with the same image, seed, style, prompt
4. Tweak anything you want (prompt, lighting, duration…)
5. Generate — same seed = comparable outputs

### Delete jobs
1. Open a job, click **"🗑"** at the bottom
2. Confirm in the inline dialog
3. DB record + video + audio + caption files are removed

---

## 🔑 Where to get API keys

### fal.ai (required) — pay-per-use
1. Sign up: https://fal.ai
2. Dashboard → Keys → Create new key
3. Pricing: Pro Seedance ~$0.40/5s 1080p, Lite Seedance ~$0.18/5s — **Lite is cheaper, use it for transitions**
4. Add credits via card

### ElevenLabs (optional) — voiceover FR/EN
1. Sign up: https://elevenlabs.io
2. Free tier: ~10k chars/month
3. Settings → API Keys → Copy
4. Default voices in `.env`:
   - EN: `21m00Tcm4TlvDq8ikWAM` (Rachel)
   - FR: `ThT5KcBeYPX3keUQqHPh` (Dorothy)

---

## 📊 Pricing estimate (10 videos/day, mix of Pro and Lite)

| Service | Avg/video | Per day | Per month |
|---|---|---|---|
| fal.ai Seedance (mix Pro/Lite) | ~$0.30 | ~$3.00 | ~$90 |
| ElevenLabs (~30 chars VO) | ~$0.01 | ~$0.10 | ~$3 |
| **Total** | **~$0.31** | **~$3.10** | **~$93** |

(Verify current pricing on fal.ai/ElevenLabs.)

---

## 🔧 Troubleshooting

**Backend "No module named greenlet"**  
→ Already fixed in v1.2 requirements. If migrating from v1.1: `pip install -r requirements.txt --upgrade`.

**`pip install` fails with C++ compiler errors**  
→ Python 3.13 + old version pins. v1.2 uses `>=` ranges that pull prebuilt wheels. Make sure you're using the v1.2 `requirements.txt`.

**npm install fails with `EFTYPE` or `EPERM`**  
→ Antivirus (Avast/Defender) is blocking. Add the project folder to exclusions in your AV settings, then `npm cache clean --force` and retry.

**`python` opens Microsoft Store**  
→ `Settings > Apps > Advanced > App execution aliases` → disable `python.exe` and `python3.exe`. Or use `py` everywhere.

**`ffmpeg` not found**  
→ Re-do step 2 of the install. After install, **close and reopen PowerShell** to refresh PATH.

**fal.ai job fails with "Invalid endpoint"**  
→ Check your fal.ai dashboard — confirm the model is available in your region/account. Try without an end image first (uses Pro endpoint, more universally available).

**End image not working**  
→ Seedance Lite requires both images to be similar dimensions/aspect. Use images of the same aspect ratio for best results.

**DB auto-migration fails**  
→ Manually delete `backend/deepotus.db` (you'll lose old jobs, but it's a fresh start).

---

## 🛠 Development notes

- **Adding more templates**: edit `backend/app/personas/deepotus.json`, restart backend. JSON schema mirrors `PromptTemplate` in `schemas.py`.
- **Adding more personas** (e.g. for Rippled, Werner Wilfre): copy `deepotus.json` to `your_persona.json`, edit, change `Pipeline(persona_id="...")` in `routes.py:20`.
- **Builder keyword detection**: extend dictionaries in `prompt_engine.py` (`CAMERA_KEYWORDS`, `LIGHTING_KEYWORDS`, `PACING_KEYWORDS`).
- **DNA elements**: customize in `prompt_engine.py` `DEEPOTUS_DNA` dict.

---

🐙 **From the deep, for the deep.**
