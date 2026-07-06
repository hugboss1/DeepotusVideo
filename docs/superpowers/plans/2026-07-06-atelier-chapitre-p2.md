# Atelier Chapitre P2 — Storyboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Spec: §6 of `docs/superpowers/specs/2026-07-05-atelier-chapitre-design.md`.

**Goal:** Auto-découpage of a chapter into ordered storyboard shots (action, entités présentes, type de plan, mouvement caméra, durée) with cheap sketch generation per shot and an editable timeline in `/atelier` — the "film draft plays in front of you" step of the reference workflow.

**Architecture:** One new `shots` table + Atelier routes (découpage AI via `summarizer._chat_dispatch` like `_ai_scenes` but entity-aware, paragraph fallback, CRUD, sketch via `_flux_generate` with a storyboard-sketch style, reorder). UI: Script/Storyboard tabs in the atelier left pane, shot cards with editable fields, debounced PUT.

### Task 1: `Shot` model (storage.py) — id, chapter_id(idx), idx, source_text, action, entities(JSON), shot_type, camera_move, duration_s(Float), sketch_image, sketch_seed, prompt, timestamps. create_all only.
### Task 2: failing test `backend/tests/test_atelier_p2.py` — paragraph découpage on a 3-paragraph chapter (3 shots, idx order, source_text verbatim); CRUD (insert-after reindex, PUT fields, DELETE reindex); sketch with stubbed fal (seed honored + stored, sketch style + action + entity desc in prompt); reorder; découpe ai without LLM keys → explicit error.
### Task 3: routes — `GET /chapters/{cid}/shots`, `POST /chapters/{cid}/storyboard/decoupe {method,language}` (replaces shots), `POST /chapters/{cid}/shots {after_id?}`, `PUT /shots/{sid}`, `DELETE /shots/{sid}`, `POST /shots/{sid}/sketch {seed?}`, `POST /chapters/{cid}/storyboard/reorder {ids}`. `_ai_shots(script, bible, lang)` maps entity names→ids; shot_type ∈ {establishing, wide, medium, close-up, extreme close-up, over-shoulder, POV, insert}; camera_move ∈ CameraMove values; duration 3–12 s. Sketch prompt style: "rough storyboard sketch, loose pencil strokes, monochrome, composition lines only" + action + shot/camera + short entity descriptions. Run test → PASS → commit.
### Task 4: atelier UI — tabs Script|Storyboard (left pane); toolbar (🎬 Découper IA / paragraphe fallback, ＋ Plan, Σ durée); shot cards (croquis thumb + 🎨/🎲, n° + durée input, action textarea, type/caméra selects, chips entités, source excerpt in <details>, ↑ ↓ 🗑, ＋ insérer après); debounced PUT; node --check → commit.
### Task 5: deploy backend+atelier to installed app; STOP backend only (USER relaunches — never launch from sandbox); after relaunch verify découpage+sketch live; push + PR.
