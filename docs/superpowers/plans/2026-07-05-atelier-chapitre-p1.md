# Atelier Chapitre P1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `/atelier` P1 — chapter script editor with zone-selection → persistent seeded Character/Place/Object bible, per the approved spec `docs/superpowers/specs/2026-07-05-atelier-chapitre-design.md`.

**Architecture:** Two new DB tables (create_all only) + CRUD routes + a reference-image generation endpoint reusing the FLUX path with a new seed passthrough; UI is a clean vanilla HTML/JS page served by FastAPI at `/atelier` (like `/guide`) — zero bundle surgery.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), vanilla JS/CSS (atelier page), fal FLUX schnell (+seed), embedded python for tests.

**Environment:** repo `C:\Users\olivi\DeepotusVideo`, branch `feat/atelier-chapitre-p1`; test python `C:\Users\olivi\AppData\Local\DeepotusVideoGen\runtime\python\python.exe`; installed app for live checks.

---

### Task 1: Models — `BibleEntity` + `Chapter`

**Files:** Modify `backend/app/services/storage.py` (after `AvatarPreset` — note: this branch is off main, so insert after `ScheduledPost`).

- [ ] Add both models (String/Text/Integer/DateTime columns per spec §3: bible_entities{id,kind,name,description,ref_image,seed,style_notes,inspiration_images,created_at,updated_at}; chapters{id,title,script_text,spans,series,created_at,updated_at}). New tables only → `init_db()` creates them; no ALTER lists needed.
- [ ] Sanity: embedded python imports storage; both table names in `Base.metadata.tables`.

### Task 2: Failing API test

**Files:** Create `backend/tests/test_atelier.py`

- [ ] Self-contained async test (temp `DATABASE_URL`, `FAL_KEY=test` env before import, `sys.modules["fal_client"]` stub whose `subscribe_async` records arguments and returns `{"images":[{"url":"http://x/img.png"}],"seed":424242}`; stub httpx image download? routes download via httpx AsyncClient — instead stub at fal level AND monkeypatch the download by pre-writing? Simpler: the generate-entity endpoint implementation downloads via httpx — test patches `httpx.AsyncClient.get`? Cleaner: implement `_flux_generate(prompt, size, n, seed)` helper in routes that returns saved filenames+seed, and monkeypatch THAT in the endpoint test. Test asserts: CRUD entities (POST/GET?kind/PUT/DELETE), CRUD chapters (spans round-trip), `POST /api/bible/entities/{id}/generate` stores ref_image+seed (with seed passthrough honored), `/images/generate` FLUX branch builds arguments with seed (via the fal stub).
- [ ] Run → FAIL (routes absent). Commit test.

### Task 3: Routes + seed extension

**Files:** Modify `backend/app/api/routes.py`

- [ ] Extract the FLUX generation core into `async def _flux_generate(prompt, size, n, seed=None) -> dict{filenames, seed}` used by `/images/generate` (which gains optional `seed` in body and returns `seed`) — GPT-image path unchanged.
- [ ] `GET/POST /api/bible/entities`, `PUT/DELETE /api/bible/entities/{id}`, `POST /api/bible/entities/{id}/generate` (prompt = kind-prefix + description + style_notes; body {seed?, model?}; stores ref_image + seed used; `portrait_4_3` size for characters, `landscape_16_9` for places, `square` for objects).
- [ ] `GET/POST /api/chapters`, `GET/PUT/DELETE /api/chapters/{id}` (spans JSON round-trip).
- [ ] Run test → PASS. Commit.

### Task 4: `/atelier` page

**Files:** Create `frontend/atelier/index.html`, `frontend/atelier/atelier.css`, `frontend/atelier/atelier.js`; modify `backend/app/main.py` (mount, after the guide mount, `html=True`).

- [ ] index.html: two-pane layout (script left / bible right) matching the app's dark theme variables.
- [ ] atelier.js (vanilla): chapters list + editor (textarea + highlight overlay for spans); file import via `/api/episodes/extract-text`; selection → floating menu (create character/place/object or link to existing); bible tabs + entity cards (description, Library inspiration picker via `GET /api/images`, Générer 🎨 / re-roll 🎲 / seed lock 🔒 badge, delete); debounced autosave of chapter (script+spans); span re-anchoring by text search on edit (orphan marking fallback).
- [ ] `node --check` on atelier.js. Commit.

### Task 5: Live verify + finish

- [ ] Deploy: mirror backend files + `frontend/atelier/` into the installed app; restart backend; open `http://127.0.0.1:8765/atelier`.
- [ ] Smoke: create chapter → paste text → select word → create Personnage → describe → Générer (real FLUX, ~2-4s) → seed badge → re-roll → lock; entity visible from a second chapter; restart backend → all persisted.
- [ ] Run all 6 backend test suites (regressions). Push branch + PR. User validates in-app.
