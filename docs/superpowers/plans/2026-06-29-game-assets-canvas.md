# Game Assets Live Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Turn the Game Assets generation into a live node canvas (Input → per-angle View nodes → Engine → Response) that fills in real time, each image node savable/exportable.

**Architecture:** Backend `generate_asset3d` gains an `on_step` progress callback (route updates the job's current_step/progress). Frontend `DzGameAssets` gains a `mode` (form|canvas): Generate switches to a custom canvas (positioned node cards + SVG bézier edges) driven by polling `/api/jobs` + the existing `manifest`.

**Tech:** FastAPI + pytest; compiled bundle count-guarded patches + node --check + deploy.

---

## Task 1: backend per-phase progress callback (TDD)

**Files:** Modify `backend/app/services/asset3d_service.py`; Modify `backend/app/api/routes.py`; Modify `backend/tests/test_asset3d_service.py`.

- [ ] **Step 1: Failing test** — append:
```python
def test_generate_asset3d_reports_steps(tmp_path, monkeypatch):
    import asyncio
    from app.services import asset3d_service as A
    from app.config import settings
    monkeypatch.setattr(type(settings), "outputs_path", property(lambda self: tmp_path))
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    (tmp_path / "s.png").write_bytes(b"\x89PNG\r\n\x1a\n0")
    async def up(p): return "u"
    async def run(e, a): return {"mesh_url": "m", "format_urls": {}, "texture_urls": [], "preview_url": None}
    async def sd(u, p): return "v"
    monkeypatch.setattr(A, "_upload", up); monkeypatch.setattr(A, "_run_engine", run)
    monkeypatch.setattr(A, "_seedream_edit", sd); monkeypatch.setattr(A, "_download", lambda u, d: d.write_bytes(b"X") or True)
    steps = []
    async def on_step(label, pct): steps.append((label, pct))
    asyncio.run(A.generate_asset3d({"image_filename": "s.png", "engine": "triposr", "multiview": True, "views": 2, "formats": ["glb"]}, "j", on_step=on_step))
    labels = [x[0] for x in steps]
    assert any("Uploading" in l for l in labels) and any("View 1/2" in l for l in labels)
    assert any("Running" in l for l in labels) and labels[-1] == "Complete"
    pcts = [x[1] for x in steps]
    assert pcts == sorted(pcts) and pcts[-1] == 100
```
- [ ] **Step 2: Run — expect fail** (`generate_asset3d` has no `on_step`).
- [ ] **Step 3: Implement.** Change the signature to `async def generate_asset3d(payload, job_id, on_step=None):` and add a local helper at the top:
```python
    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)
```
Then `await _step(...)` at each phase: after `out_dir.mkdir` → `await _step("Uploading", 10)`; inside the multiview loop, before each `_seedream_edit` → `await _step(f"View {i}/{int(payload.get('views',3))}", 10 + int(40*i/max(1,int(payload.get('views',3)))))`; before the engine `_run_engine` → `await _step(f"Running {engine}", 60)`; before `return` → `await _step("Complete", 100)`.
- [ ] **Step 4: Run — expect pass.** Full suite green.
- [ ] **Step 5: Wire the route.** In `routes.py` `assets_3d._run`, define an `on_step` that updates the job and pass it:
```python
        async def on_step(label, pct):
            async with async_session_factory() as s2:
                jr2 = await s2.get(JobRecord, job_id)
                if jr2 is not None:
                    jr2.current_step = label; jr2.progress = int(pct); await s2.commit()
        r = await generate_asset3d(body, short, on_step=on_step)
```
- [ ] **Step 6: Deploy backend + restart.** Commit: `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): per-phase progress callback (on_step) for the live canvas"`

---

## Task 2: live canvas in DzGameAssets (bundle)

**Files:** Modify `frontend/dist/assets/index-BEOJX8L5.js` (extend `DzGameAssets`).

- [ ] **Step 1:** Add a `mode`/`activeJob` state and a `canvasView(job)` renderer; switch on Generate. Build the canvas as positioned node cards + an SVG bézier-edge overlay, polling `/api/jobs` (find activeJob) + `/api/assets/3d/{short}/manifest` every 1.5 s. Node set: Input, View_1..N (when `multiview`), Engine, Response. Node state from manifest+status (Input done when shot_0; View i done when i∈shots; Engine done when "glb"∈formats; Response done when status==="done", failed on "failed"). Running nodes pulse; running edges animate (CSS dashed). Image nodes (Input + Views) show the shot with **↓ Download** + **★ Save to Library** (`/shot/{i}/save`); Response shows `<model-viewer>` on the GLB + **▶ Rotate/▣ Poster** + **Download ▾** of `manifest.formats`. A **← New asset** button sets `mode="form"`. Clicking a past asset opens its canvas.
- [ ] **Step 2:** `node --check`; deploy; browser-test: Generate (multi-view 3, Tripo) → canvas appears; Input fills immediately; the 3 View nodes fill one-by-one with edges animating; Engine then Response fill when the GLB lands; each View Download + Save-to-Library work; Response rotates + downloads; ← New asset returns to the form; re-opening a finished asset shows its canvas. No console errors.
- [ ] **Step 3: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): live pipeline canvas (nodes + SVG edges + per-node save/export)"`

---

## Self-Review
**Spec coverage:** per-phase progress (T1) ✓; form→canvas mode + reference layout (T2) ✓; live fill from manifest+status (T2) ✓; running animation (T2) ✓; per-node Download+Save + Response export/rotate (T2) ✓; custom canvas, no React Flow (T2) ✓. **Placeholders:** T1 carries full code; T2 is one large component built incrementally with node --check + browser checks (the DzAnimation/DzGameAssets pattern), reusing the verified manifest/shot/format routes. **Consistency:** `on_step(label,pct)` signature matches route + test; node states map to the manifest fields (`shots`,`formats`) already returned.
