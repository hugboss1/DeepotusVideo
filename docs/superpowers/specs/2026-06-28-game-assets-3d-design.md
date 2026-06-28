# Game Assets (3D) — Design (image → 3D mesh, multi-engine)

> **Context:** A new top-level category in DeepotusVideoGen that turns a character/object image into a downloadable, game-ready **3D model**. Inspired by the fal.ai workflow (multi-view → Hyper3D), but with a **selectable 3D engine** (the fal-native models are ready out of the box; Meshy 6 is prepared via Settings). Reuses the app's fal plumbing (`fal_service.py`: `fal_client.upload_file_async` + `subscribe_async`), `FAL_KEY`, `JobRecord`, and job polling.

**Goal:** From a new **"Game Assets"** page, pick/upload an image → choose a 3D engine + options → generate a mesh → rotate it in-app and download it in formats for **Blender, Unity, Unreal, or 3D printing**.

**Tech stack:** FastAPI + `fal_client` (backend, pytest for pure helpers); compiled React bundle (count-guarded patches, `node --check`, deploy) + a **vendored** `<model-viewer>` for the live preview.

---

## 1. Selectable 3D engines

The engine is a dropdown; each option shows a one-line description (UI help) so the user can choose. Prices are per generation, from each provider's docs (encoded as **config-driven rates**, editable like the existing pricing, and shown in the cost pill).

| Engine | fal endpoint (verify at integration) | Cost / generation | Strength (UI description) | Ready in MVP |
|---|---|---|---|---|
| **Tripo3D v2.5** ⭐ default | `tripo3d/tripo/v2.5/image-to-3d` | $0.20 no-tex · $0.30 std-tex · $0.40 HD-tex | "Game-ready topology + clean UVs, broad export, optional rigging. Best all-round for game assets." | Yes (fal) |
| **Hunyuan3D v2** | `fal-ai/hunyuan3d/v2` | $0.16 white mesh · $0.48 textured | "Exceptionally clean geometry for characters & organic shapes; minimal cleanup." | Yes (fal) |
| **TRELLIS** | `fal-ai/trellis` | ~$0.16–$0.50 | "Best texture realism (Gaussian-splat); great for detailed, photoreal looks." | Yes (fal) |
| **Hyper3D Rodin** | `fal-ai/hyper3d/rodin` | $0.40 | "Professional surface realism; the engine from the reference workflow." | Yes (fal) |
| **TripoSR** | `fal-ai/triposr` | $0.07 | "Fastest & cheapest; rough prototype quality." | Yes (fal) |
| **Meshy 6** | Meshy API (not fal) | ~15–20 credits/model (Pro $20/mo ≈ 1000 cr → ≈ $0.30–0.40 textured) | "Most polished all-in-one (PBR, topology, rigging, great for printing). Needs a Meshy API key." | **Prepared** (Settings key + link), adapter stubbed |

All fal engines go through one `subscribe_async(endpoint, args)` path with an **engine adapter** that maps the common request (image URL, format, quality, textures, tpose) to that engine's argument names and reads its result URLs. Engines that don't support a requested export format fall back to GLB + local note.

## 2. Pipeline (backend `asset3d_service.py` + route)

`POST /api/assets/3d`, body `{ image_filename, engine, subject?, multiview:bool, views:N, quality, textures, tpose, formats:[...] }` → background job, poll via `GET /api/jobs/{job_id}` (`provider="asset3d"`).

1. **Resolve input** → `FalSeedanceClient.upload_image()` → fal URL (or, for Meshy, pass the image per Meshy's API).
2. **Optional multi-view "boost"** (`multiview`, default **off** — the strong engines do single-image well): if on, run `views` (1–4) `fal-ai/bytedance/seedream/v4/edit` calls with angle prompts from `view_prompts(n, subject)` (front/back/¾-left/¾-right) → extra view URLs fed to the engine for consistency.
3. **3D engine** via the adapter for the chosen `engine`: produce **GLB always** (preview + interchange) plus any requested export formats (the engine's native `geometry_file_format`/equivalent; Tripo/Rodin/Hunyuan support FBX/OBJ/STL/USDZ — **exact options + whether one call returns multiple formats are verified against a live call during implementation**).
4. **Store + register:** download mesh files + the engine's preview/render image + textures to `outputs/assets3d/{job_id}/` (`model.glb`, `model.fbx`, …, `preview.png`). Register a `JobRecord` (`provider="asset3d"`; GLB in `final_video_path`; poster in `image_filename`; `cost_meta` JSON records engine + available formats).
5. **Serve:** `GET /api/assets/3d/{job_id}/{fmt}` streams `glb|fbx|obj|stl|usdz`.

## 3. Format → target-use mapping (UI)
GLB always; user multi-selects targets → formats: **Blender/Web** → `glb`; **Unity/Unreal** → `fbx` (GLB also imports); **Universal** → `obj`; **3D printing** → `stl`; **AR/USD** → `usdz`.

## 4. Frontend — new "Game Assets" category page
- **Nav:** add "Game Assets" to the top-level category array (with Quick/Studio/Episodes/Scheduler/Templates/News/Library/Settings).
- **Generator:** image source (reuse Library grid + upload) → **engine dropdown** (each option renders its one-line description as helper text + the cost) → optional **subject** → **multi-view boost** toggle (+ views slider when on) → **quality** / **textures** / **T-pose** → **target formats** multi-select → live **cost estimate** → **Generate** (gated on `FAL_KEY`, or `MESHY_API_KEY` for Meshy) → progress.
- **Results grid:** `asset3d` jobs as cards — poster image, name, **▶ rotate** (live `<model-viewer>` on the GLB), **Download ▾** (available formats).
- **Library:** "Renders" filtered to exclude `provider==="asset3d"`.

## 5. 3D preview — vendored `<model-viewer>`
Vendor `@google/model-viewer` minified ESM into `frontend/dist/assets/model-viewer.min.js` (committed, ~300 KB) and load it once; offline-capable for re-viewing. GLB in the viewer; engine preview image as poster; non-GLB exports are download-only.

## 6. Settings — Meshy preparation
Add a **`MESHY_API_KEY`** field to Settings (the same keys form that holds FAL/HeyGen/etc.), with helper text + a link to **https://www.meshy.ai/api**. Backend reads `settings.MESHY_API_KEY`; the Meshy engine adapter is **implemented as a thin module** (request/poll/download via Meshy's REST) but only active when the key is set — selecting Meshy without a key shows the same "key required" note pattern Seedance uses. This makes Meshy a config-flip, not a future rewrite.

## 7. Pricing
Add an `asset3d` op to `pricing.py`, engine-aware: `cost = (multiview ? N × seedream_edit_usd : 0) + engine_cost(engine, textures)`. Config-driven rates seeded from the table above (`tripo_usd`/`tripo_hd_usd`, `hunyuan_usd`/`hunyuan_tex_usd`, `trellis_usd`, `rodin_usd`, `triposr_usd`, `seedream_edit_usd`; Meshy shown as "≈ credits via your Meshy plan"). Surfaced in the cost pill + the live estimate on the page.

---

## 8. Scope / non-goals (MVP)
- One asset at a time; single source image (+ optional AI multi-view boost).
- Engines: all fal models wired; **Meshy prepared** (Settings key + adapter), exercised only if the user adds a key.
- Output: GLB always + chosen FBX/OBJ/STL/USDZ.
- **No** rigging/animation, retopology, or PBR-material editing in-app.
- **No** Studio-node version (guided generator; Studio still owns graphs).
- Library cross-listing, batch, delete/rename of 3D assets: later.

## 9. Risks / open questions
- **Per-engine API specifics** (exact endpoints, arg names, format options, result fields, multi-format-per-call) — **verified per engine against a live fal/Meshy call during implementation**; the adapter isolates these so one engine's quirks don't leak.
- **Cost** — surfaced live; default engine Tripo std-tex ≈ $0.30, multi-view off by default to keep it cheap.
- **Large files** stored per-job under `outputs/assets3d/{job_id}/`, streamed on download.

## 10. Testing
- Backend: pytest for `view_prompts(n, subject)` and each engine adapter's **argument assembler + result parser** (pure, mockable). Live smoke: a real Tripo 1-image generation → GLB + poster land under `outputs/assets3d/{id}/`.
- Frontend: browser — switch engines (descriptions + cost update), generate (GLB+STL), watch progress, rotate the preview, download both; asset appears in the grid; Settings shows the Meshy key field + link; Library Renders unaffected; no console errors.

---

## Sources (engine quality + pricing)
- fal model pages: [Tripo3D v2.5](https://fal.ai/models/tripo3d/tripo/v2.5/image-to-3d), [Hunyuan3D v2](https://fal.ai/models/fal-ai/hunyuan3d/v2), [Hyper3D Rodin](https://fal.ai/models/fal-ai/hyper3d/rodin), [TripoSR](https://fal.ai/models/fal-ai/triposr), [fal 3D models](https://fal.ai/3d-models)
- [Best 3D Model Generation APIs 2026 — 3DAI Studio](https://www.3daistudio.com/blog/best-3d-model-generation-apis-2026)
- [Best AI 3D Model Generators 2026 — TRELLIS vs Meshy vs Tripo](https://trellis2.app/blog/best-ai-3d-model-generator)
- Meshy: [API pricing](https://docs.meshy.ai/en/api/pricing), [credit costs](https://help.meshy.ai/en/articles/10000507-how-many-credits-does-each-generation-task-cost), [plans](https://www.meshy.ai/pricing), [3D AI price comparison — Sloyd](https://www.sloyd.ai/blog/3d-ai-price-comparison)
