# Game Assets — Live Pipeline Canvas (design)

> **Context:** Extends the existing **Game Assets** category. Today, Generate posts to `/api/assets/3d` and the result shows as a card. The user wants the generation shown as a **live node graph** (like the fal.ai reference): input → per-angle Seedream views → 3D engine → response, each phase appearing in real time, each image node individually savable/exportable. Custom lightweight canvas (no React Flow).

**Goal:** After picking an image + options and hitting Generate, switch the page into a live, reference-style pipeline canvas that fills in node-by-node as the backend produces shots and the mesh — with per-node Download + Save-to-Library and a final 3D + multi-format export.

**Tech:** compiled bundle (count-guarded patches) — a custom canvas in `DzGameAssets`: absolutely-positioned node cards + an SVG bézier-edge layer, driven by polling `/api/jobs` + the existing `/api/assets/3d/{short}/manifest`. Small backend enhancement: per-phase progress reporting.

---

## 1. Backend — per-phase progress (small change)

`generate_asset3d(payload, job_id, on_step=None)` gains an optional **async callback** `on_step(step: str, pct: int)`, awaited at each phase: `("Uploading", 10)`, per view `("View i/N", …)`, `("Running {engine}", 60)`, `("Downloading mesh", 85)`, `("Complete", 100)`. The route passes an `on_step` that updates the job's `current_step` + `progress` (its own DB session). Node *fill* state still comes from the **manifest** (files on disk = ground truth); `current_step` is just the status label. No new endpoints — the manifest + `/api/jobs` already expose everything.

## 2. Frontend — view mode in `DzGameAssets`

A `mode` state: `"form"` (the current picker+options panel — unchanged) or `"canvas"`. On **Generate**: POST `/api/assets/3d`, capture the returned `job_id`, set `mode="canvas"` + `activeJob=job_id`. A **"← New asset"** button returns to `"form"`. The past-assets grid stays under the form; clicking an asset sets `activeJob` + `mode="canvas"` to re-open its canvas.

## 3. The canvas (custom, reference layout)

A relative-positioned container (auto-fit, scrollable; no zoom for MVP) with:

- **Nodes** (cards ~150×170): **Input** (left), a vertical **column of View nodes** (one per `views` when multi-view boost is on; none when off), the **Engine** node, the **Response** node (right). Positions computed from a small layout function (columns: input x=0, views x=1, engine x=2, response x=3; views stacked vertically).
- **Edges:** an absolutely-positioned full-size **SVG** layer drawing a **bézier curve** from each source node's right-port to each target's left-port (Input→each View, each View→Engine, Engine→Response; when multi-view off: Input→Engine→Response).
- **States** per node, derived from `manifest` + `job.status`:
  - Input → `done` as soon as `shot_0` exists (immediate).
  - View *i* → `running` (animated) until `shot_i` ∈ `manifest.shots`, then `done` (shows the image).
  - Engine → `running` once all views done & no GLB; `done` when `glb` ∈ `manifest.formats`.
  - Response → `done` when `job.status==="done"`; `failed` (red) when `job.status==="failed"` (show `job.error`).
- **Running animation:** running nodes get a pulsing border + a spinner; their incoming edges get an animated dash (CSS `stroke-dashoffset`), matching the reference.
- Polls `/api/jobs` (find `activeJob`) + `manifest` every ~1.5 s while not terminal; stops when done/failed.

## 4. Per-node save / export (the key ask)

- **Image nodes** (Input + each View): a **↓ Download** (`<a href=/api/assets/3d/{short}/shot/{i} download>`) and a **★ Save to Library** (POST `/shot/{i}/save`) — so every side view is individually reusable.
- **Response node:** the live **`<model-viewer>`** on the GLB (poster fallback = engine preview or shot_0), a **▶ Rotate / ▣ Poster** toggle, and **Download ▾** listing every format in `manifest.formats` (GLB/FBX/OBJ/STL/USDZ). A **Download All** affordation links each format.

## 5. Scope / non-goals
- Fixed pipeline layout (input → views → engine → response) — not a user-editable/draggable graph, no zoom/pan beyond container scroll.
- No new persistence: canvas state is derived from the job + manifest each poll (re-openable any time).
- Reuses the engine/multi-view/format logic already built; no change to the generation pipeline itself beyond the progress callback.

## 6. Testing
- Backend: pytest that `generate_asset3d` awaits `on_step` for each phase (mock the callback + the fal/download seams; assert the sequence Uploading→View→Running→Complete and that pct is monotonic).
- Frontend (browser): Generate with multi-view 3 + Tripo → the canvas appears; Input fills immediately; the 3 View nodes fill one-by-one as shots land (edges animate while running); the Engine then Response fill when the GLB lands; each View has working Download + Save-to-Library; Response rotates + downloads GLB; "← New asset" returns to the form; re-opening a past asset shows its finished canvas. No console errors.
