# Game Assets (3D) — Design (image → multi-view → Hyper3D mesh)

> **Context:** A new top-level category in DeepotusVideoGen that turns a single character/object image into a downloadable, game-ready **3D model**, mirroring the fal.ai workflow (Seedream V4 Edit multi-view → Hyper3D/Rodin). Reuses the app's existing fal.ai plumbing (`fal_service.py`: `fal_client.upload_file_async` + `subscribe_async`), `FAL_KEY`, `JobRecord`, and job polling.

**Goal:** From a new **"Game Assets"** page, pick/upload an image → choose options → generate a 3D mesh via fal.ai → rotate it in-app and download it in formats usable by **Blender, Unity, Unreal, or 3D printing**.

**Tech stack:** FastAPI + `fal_client` (backend, pytest for pure helpers); compiled React bundle (count-guarded patches, `node --check`, deploy) + a **vendored** `<model-viewer>` web component for the live 3D preview.

---

## 1. Pipeline (backend `asset3d_service.py` + route)

`POST /api/assets/3d`, body `{ image_filename, subject?, views:N, quality, tpose, formats:[...] }` → background job, poll via `GET /api/jobs/{job_id}` (`provider="asset3d"`).

1. **Resolve input** → upload to fal: a Library image (`images_path/filename`) or a fresh upload → `FalSeedanceClient.upload_image()` → fal URL.
2. **Multi-view** (`views` = 1–4, default 3): run N `fal-ai/bytedance/seedream/v4/edit` calls, each `{image_urls:[src], prompt: <angle prompt> + subject, image_size, num_images:1}`. Angle prompts come from a pure helper `view_prompts(n, subject)` → e.g. front / back / 3⁄4-left / 3⁄4-right, sliced to N. Returns N consistent view URLs (the source is also included as a reference view).
3. **Hyper3D** `fal-ai/hyper3d/rodin/v2` with `{input_image_urls:[views], geometry_file_format:"glb", material, quality_mesh_option:<quality>, TAPose:<tpose>, use_original_alpha:true, preview_render:true}`. GLB is always produced (preview + interchange).
4. **Export formats:** for each requested non-GLB format in `formats` (`fbx|obj|stl|usdz`), produce it from Rodin. **Implementation note:** Rodin supports these via `geometry_file_format`; first verify whether one call returns multiple formats (`model_meshes`) — if so, request all in one call; otherwise issue one targeted Rodin call per extra format. Each produced file is downloaded alongside the GLB.
5. **Store + register:** download `model_mesh` (GLB) + the `preview_render` image + any extra-format files + textures to `outputs/assets3d/{job_id}/` (`model.glb`, `model.fbx`, …, `preview.png`). Register a `JobRecord` (`provider="asset3d"`, GLB path in `final_video_path`, poster in `image_filename`, the available formats recorded in `cost_meta` JSON).
6. **Serve:** `GET /api/assets/3d/{job_id}/{fmt}` streams the requested file (`glb|fbx|obj|stl|usdz`); the poster is served like other images.

## 2. Format → target-use mapping (UI)

The user multi-selects **targets**, which map to formats; GLB is always generated for the live preview.
- **Real-time / Blender / Web** → `glb` (always).
- **Unity / Unreal** → `fbx` (native; GLB/glTF also imports).
- **Universal (Blender, DCC)** → `obj` (+ textures).
- **3D printing** → `stl` (geometry only).
- **AR / USD (optional)** → `usdz`.

## 3. Frontend — new "Game Assets" category page

- **Nav:** add a "Game Assets" entry to the top-level category list (the same array that holds Quick/Studio/Episodes/Scheduler/Templates/News/Library/Settings), rendering a new page component.
- **Generator panel:** image source (reuse the Library image grid for picking, plus an upload button) → optional **subject** text → **views** slider (1–4) → **quality** select → **T-pose** toggle → **target formats** multi-select → **Generate** (disabled without `FAL_KEY`, mirroring Seedance gating) → progress (poll the job).
- **Results grid:** past `asset3d` jobs as cards: the Hyper3D **poster image**, the model name, **▶ rotate** (opens the live `<model-viewer>` with the GLB), and a **Download ▾** menu listing the available formats. Delete + rename can reuse the Library patterns later (out of MVP scope).
- **Library:** the "Renders" category is filtered to **exclude** `provider==="asset3d"` so GLBs are never treated as `<video>`.

## 4. 3D preview — vendored `<model-viewer>`

Vendor Google's `@google/model-viewer` minified ESM build into `frontend/dist/assets/model-viewer.min.js` (≈300 KB, committed) and load it once (`<script type="module">`) so re-viewing works offline. The viewer uses the GLB; the Hyper3D `preview_render` image is the poster shown before/without the live viewer. Non-GLB exports are download-only (no live spin needed — GLB always covers preview).

## 5. Pricing

Add an `asset3d` op to `pricing.py`: `N × seedream_edit_usd + 1 × hyper3d_usd` (+ one `hyper3d_usd` per extra format if separate Rodin calls are needed), with config-driven rates (`seedream_edit_usd`, `hyper3d_usd`) editable like the existing rates, surfaced in the cost pill.

---

## 6. Scope / non-goals (MVP)
- One asset at a time; single source image (+ AI multi-view).
- Output: GLB always, plus user-chosen FBX/OBJ/STL/USDZ.
- **No** rigging/skeleton/animation, retopology, or PBR-material editing.
- **No** Studio-node version (Studio still owns node graphs; this is a guided generator).
- Library cross-listing, batch generation, delete/rename of 3D assets: later.

## 7. Risks / open questions
- **Rodin API specifics** — exact `geometry_file_format` options, whether `model_meshes` returns multiple formats per call, and result field names — **verified against a live fal.ai call during implementation** (a 1-view smoke), then the call count is optimized (prefer one multi-format call).
- **Cost** — multi-view + Hyper3D is materially pricier than a Seedance clip; the views slider + the cost pill keep it explicit. Default 3 views.
- **Large files** — GLB/FBX can be several MB; stored per-job under `outputs/assets3d/{job_id}/`, streamed on download, not held in memory.
- **Offline preview** — vendored `<model-viewer>` works offline for re-viewing; generation itself always needs internet (fal.ai).

## 8. Testing
- Backend: pytest for `view_prompts(n, subject)` (count, angle ordering, subject injection) and the Hyper3D argument assembler (pure, mockable). A live smoke: real 1-view generation → a GLB + poster land under `outputs/assets3d/{id}/`.
- Frontend: browser — Generate with 2 views + GLB+STL, watch progress, rotate the preview, download both formats; the asset appears in the Game Assets grid; Library Renders is unaffected; no console errors.
