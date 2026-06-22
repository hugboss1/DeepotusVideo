# French Localization (EN canonical + FR overlay + onboarding language picker) — Implementation Plan

> **For the fresh session:** this is the ready-to-execute plan agreed on 2026-06-22. The notice/guide update is already done and shipped (commit 71681c6). This plan is **only** the in-app localization. Execute it in a clean session with a stable browser, because the language toggle needs a lot of live verification.

**Goal:** Ship the app in two fully-consistent languages — **EN (canonical)** and **FR** — with the user choosing the language **at startup in the onboarding** (and switchable later).

**Architecture:** The UI is a **compiled, minified React bundle** (`frontend/dist/assets/index-BEOJX8L5.js`) — there is **no React source** to rebuild with a real i18n framework. So the only realistic approach is a **runtime translation overlay**: an `EN → FR` dictionary applied to the live DOM (text nodes, placeholders, titles, aria-labels), re-applied on DOM mutations, gated by a `dz_lang` flag in `localStorage`. EN is the **canonical** language baked into the bundle; FR is produced by the overlay.

**Tech stack:** Python string-replacement patches on the minified bundle (the established workflow — see memory `frontend-compiled-only` / `build-packaging-workflow`), a small injected vanilla-JS i18n module, `localStorage`, a `MutationObserver`. Validate every bundle patch with `node --check`. Deploy to BOTH the repo (`C:\Users\olivi\DeepotusVideo`) and the app (`%LOCALAPPDATA%\DeepotusVideoGen`), then rebuild the installer once at the end (bump version ×4 + config.py + .iss + index.html splash, per `build-packaging-workflow`).

---

## Why this shape (read first)

- **The app is currently MIXED.** The base UI is English, but the features added in the 2026-06-21/22 session — the **Episodes** page (`DzEpisodes`) and the **audio Library / Music track** UI — were written in **French**. So "make EN canonical" is real work, not a no-op: those French strings must become English in the bundle, then FR is restored via the overlay.
- **The overlay is a translation layer, not real i18n.** It covers *interface text*. It will **not** translate user data or API responses (those are content, not UI), and coverage is **iterative** — the dictionary grows surface by surface. This was explicitly accepted by the user (2026-06-22) as the only feasible path for a compiled app.
- **Relevant maps to reuse:** `onboarding-settings-map` (onboarding components `Km/qm/Zm/bm/Tm`, the `Fu` steps array, channel/key state), `episodes-feature` (`DzEpisodes` strings), `audio-system` ("Importer un son", `MusicTrack`/`DzAudioPicker` inspector), `studio-run-compiler` + `scheduler-library-map` (Studio/Scheduler/Library strings), `frontend-compiled-only` (the patch model + `D.` api + `Te="/api"`).

---

## Phase 0 — Make the bundle canonical English

The bundle must be 100% English first (the user's step 1: "assure-toi que tout est bien en anglais, sinon corrige").

**Files:** `frontend/dist/assets/index-BEOJX8L5.js` (patch), then deploy + `node --check`.

- [ ] **0.1 Inventory the French strings.** Grep the bundle for French markers: `é è à ê î ô ç` inside string literals, plus known tokens: `"Épisodes"`, `"Importer un son"`, `"Générer la narration"`, `"Par paragraphe"`, `"Par l'IA"`, `"Générer le découpage"`, `"Générer toutes les illustrations"`, `"Assembler l'épisode"`, `"Envoyer au Scheduler"`, `"Image fixe"`, `"Piste audio"`, `"Boucler sur la durée"`, `"Téléverser"`, `"Voix"`, `"Langue"`, `"Titre du chapitre"`, `"Texte du chapitre"`, `"Storyboard"`, `"Ajouter une scène"`, `"Banques audio libres"`, plus the nav label `{id:"episodes",label:"Épisodes"...}`. Produce the full EN↔FR pair list — this list IS the seed of the Phase-2 dictionary.
- [ ] **0.2 Replace each French literal with its English canonical** in the bundle (count-guarded `replace`, one at a time or batched in a Python script with explicit counts). Examples: `"Épisodes"`→`"Episodes"`, `"Importer un son"`→`"Upload sound"`, `"Générer la narration"`→`"Generate narration"`, `"Par paragraphe"`→`"By paragraph"`, `"Par l'IA"`→`"By AI"`, `"Assembler l'épisode"`→`"Assemble episode"`, `"Envoyer au Scheduler"`→`"Send to Scheduler"`, `"Image fixe"`→`"Still"`, `"Piste audio"`→`"Music track"`, `"Boucler sur la durée"`→`"Loop to duration"`, etc. Keep the EN labels identical to what the updated **EN guide** (docs/guide/en.html, ch. 6 & 7) already describes, so doc and UI match.
- [ ] **0.3 Backend French strings that surface in the UI.** `routes.py` / `pipeline.py` error/detail messages added for episodes/audio may be French (e.g. "Aucun LLM configuré…", "Le découpage IA a échoué…"). Convert user-facing ones to English; the FR overlay will translate them like any string. (Keep logs as-is.)
- [ ] **0.4 `node --check` the bundle, deploy to app, hard-reload, eyeball Episodes + audio in English.** Commit: `i18n(phase0): canonical English — convert Episodes + audio UI strings to EN`.

---

## Phase 1 — The i18n runtime engine

A small module that swaps EN→FR in the DOM when `dz_lang==="fr"`.

**Files:** new `frontend/dist/assets/dz-i18n.js` (or inline in `index.html` before the bundle `<script>`); referenced from `index.html`.

- [ ] **1.1 The module skeleton.** Expose `window.DZ_I18N = { dict:{...}, lang, apply(), set(lang) }`.
  - `dict`: a flat `{ "<EN string>": "<FR string>" }` map (filled in Phase 2). Keys are the exact rendered EN strings.
  - `lang`: read from `localStorage.dz_lang` (default `"en"`).
  - `translateNode(root)`: walk with a `TreeWalker` over `SHOW_TEXT`; for each text node whose trimmed value is a dict key, replace it (preserve surrounding whitespace). Also handle attributes: `placeholder`, `title`, `aria-label`, and `value` on buttons/inputs of type button/submit. Skip `<script>/<style>` and any node marked `data-dz-noi18n`.
  - `apply()`: if `lang==="fr"`, `translateNode(document.body)`.
  - A `MutationObserver` on `document.body` (childList+subtree) that calls `translateNode` on added nodes — debounced (e.g. `requestAnimationFrame` batch) to avoid thrash. Guard against re-translating (translating FR→FR is a no-op since FR strings aren't dict keys, but keep a WeakSet of processed nodes for perf).
  - `set(lang)`: persist to `localStorage`, set `document.documentElement.lang`, then either `apply()` (→fr) or **reload** (→en, simplest way to restore canonical text). Reload-on-switch is acceptable and robust; revisit only if jarring.
- [ ] **1.2 Wire it.** Add `<script src="/assets/dz-i18n.js"></script>` in `index.html` **before** the bundle module, and call `DZ_I18N.apply()` once on `DOMContentLoaded` and again right after React first mounts (reuse the splash's `MutationObserver` on `#root`, or a `setTimeout` fallback). Keep the splash text (`index.html`) translatable too, or hardcode it bilingually.
- [ ] **1.3 Verify** the engine with a 3-entry stub dict (e.g. translate the nav "Library"→"Bibliothèque") before building the full dictionary. `node --check` n/a (separate file) but lint by loading the app with `dz_lang=fr`.

---

## Phase 2 — The dictionary (EN → FR), by surface

The bulk. Build it **surface by surface**, verifying each in the browser. Seed from Phase 0.1.

**File:** the `dict` in `dz-i18n.js`.

Order (highest-value first):
- [ ] **2.1 Shell & nav:** sidebar items (Library, Quick, Studio, Templates, News, Scheduler, Episodes, Settings), top-bar pills, Job Dock, command palette.
- [ ] **2.2 Onboarding:** every step's copy (the `Fu` steps array + `Km/qm/Zm/bm/Tm` — see `onboarding-settings-map`). This is where the language picker lives (Phase 3), so it must read well in both.
- [ ] **2.3 Quick** (Seedance/HeyGen/voiceover modes), **Library** (incl. audio tab + free-music banner), **Settings** (API keys, Personas, Provider defaults, Branding, Connected accounts).
- [ ] **2.4 Studio** (palette node names, inspector labels, starter graphs), **Templates**, **Scheduler** (plan/import/inspector/emoji-pack labels), **News**.
- [ ] **2.5 Episodes** (all 4 steps) — the FR strings from Phase 0 are the exact translations; just map EN→FR back.
- [ ] **2.6 Toasts, errors, confirmations, empty states.** Add a **completeness pass**: with `dz_lang=fr`, click through every screen and grep the visible DOM for any remaining ASCII-only English sentence; add missing keys. Log what's intentionally left (e.g. provider names, code tokens).

> Tip: keep keys short and exact. For strings with interpolation (e.g. `"3 scenes"`), the overlay can't match dynamic parts — translate the static frame only, or mark those nodes `data-dz-noi18n` and accept English, or handle the few important ones with a regex rule set kept separate from the flat dict.

---

## Phase 3 — Language picker in the onboarding (+ switch later)

**Files:** the bundle (onboarding component + Settings), `dz-i18n.js`.

- [ ] **3.1 Onboarding step.** Add a **language choice** as the FIRST onboarding step (or a prominent control on the welcome step): two big buttons **English / Français** (flag or label). On click → `DZ_I18N.set(lang)` then continue. Because it's step 1, the rest of the onboarding immediately renders in the chosen language. Patch into the `Fu` steps array / the onboarding component (`Km` et al. — `onboarding-settings-map`).
- [ ] **3.2 Settings toggle.** Add a "Language / Langue" row in **Settings** (near Branding) with EN/FR — calls `DZ_I18N.set`. So users can switch after onboarding.
- [ ] **3.3 Optional top-bar switch.** A small `EN|FR` toggle in the header for discoverability.
- [ ] **3.4** Ensure first-run default: if `dz_lang` unset, the onboarding language step sets it; if onboarding was skipped, default `en`.

---

## Phase 4 — Verify, then ship

- [ ] **4.1 Live matrix test:** for EACH surface (2.1–2.6), load in EN then FR, confirm correct text, no layout breakage (FR is ~15–20% longer — watch buttons/nav truncation), no untranslated leftovers, and that switching mid-session works (reload path for →EN).
- [ ] **4.2 Persistence:** `dz_lang` survives restart; the splash + onboarding honor it.
- [ ] **4.3 Regression:** EN mode is byte-for-byte the canonical UI (overlay inert when `lang==="en"`).
- [ ] **4.4 Rebuild the installer** once (version bump ×4 + config.py + .iss + `index.html` splash version), stage + ISCC, recycle the superseded `.exe` (keep one on the Bureau). Update the **guide** if any label changed from what ch. 6/7 describe.
- [ ] **4.5 Update memories:** new `i18n-localization` memory (the engine, the dict location, how to add a language), update `frontend-compiled-only` + `onboarding-settings-map`.

---

## Risks & limits (tell the user up front)

- **Coverage is iterative** — first pass covers the main surfaces; deep/rare strings get added over time. Not a defect; the nature of a DOM overlay on a compiled app.
- **Dynamic/interpolated text** (counts, names, API messages) may stay English unless special-cased.
- **Layout:** French is longer; expect a few truncations to fix with the dictionary wording or minor CSS.
- **Maintenance:** every NEW English string added later needs a FR dict entry, or it shows in English under FR. Document this in the `i18n-localization` memory.
- **A third language later** = add another dict + a third onboarding button; the engine already supports it (`dz_lang` is free-form).

## Out of scope

- Translating the **guide** (already bilingual: `docs/guide/{en,fr}.html`).
- Translating generated **content** (captions, scripts, narration) — that's the LLM/persona's job and already language-aware.
