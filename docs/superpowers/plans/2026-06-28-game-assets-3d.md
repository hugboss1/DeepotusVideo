# Game Assets (3D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** A new "Game Assets" category that turns an image into a downloadable 3D mesh via a selectable fal.ai engine (Tripo/Hunyuan3D/TRELLIS/Rodin/TripoSR; Meshy prepared), with multi-format export, individually-downloadable view shots, and an in-app rotatable preview.

**Architecture:** Backend `asset3d_service.py` orchestrates: upload image → optional Seedream multi-view → engine adapter (`fal_client.subscribe_async`) → download mesh formats + shots + poster → `JobRecord(provider="asset3d")`, behind `POST /api/assets/3d`. Frontend adds a `DzGameAssets` page in the nav + router, a vendored `<model-viewer>`, and a `MESHY_API_KEY` Settings field.

**Tech Stack:** FastAPI + `fal_client` (pytest for pure helpers/adapters); compiled bundle patched via count-guarded Python + `node --check` + deploy; vendored `@google/model-viewer`.

**Conventions:** runtime python `$py = %LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`; tests `& $py -m pytest backend/tests/<f> -v` (via `backend/conftest.py`); bundle `frontend/dist/assets/index-BEOJX8L5.js`, count-guarded patch → `node --check` → deploy to `%LOCALAPPDATA%\DeepotusVideoGen\...` → browser-test at http://127.0.0.1:8765/. Backend deploy: copy → `$app\backend\…`, restart uvicorn. Commit after each task.

---

## File Structure
- **Create** `backend/app/services/asset3d_service.py` — engine registry/adapters, `view_prompts`, `generate_asset3d` orchestrator.
- **Create** `backend/tests/test_asset3d_service.py` — pure-helper + adapter tests.
- **Modify** `backend/app/config.py` — `MESHY_API_KEY`.
- **Modify** `backend/app/api/routes.py` — `POST /api/assets/3d`, `GET /api/assets/3d/{job}/{fmt}`, `GET /api/assets/3d/{job}/shot/{i}`.
- **Modify** `backend/app/services/pricing.py` — `asset3d` op + rates.
- **Create** `frontend/dist/assets/model-viewer.min.js` — vendored viewer.
- **Modify** bundle — nav entry, router branch, `DzGameAssets` page, Settings `MESHY_API_KEY` field.

---

## Task 1: `view_prompts` + engine registry (backend, TDD)

**Files:** Create `backend/app/services/asset3d_service.py`; Create `backend/tests/test_asset3d_service.py`.

- [ ] **Step 1: Failing tests**
```python
# backend/tests/test_asset3d_service.py
from app.services.asset3d_service import view_prompts, ENGINES, build_engine_args, parse_engine_result

def test_view_prompts_count_and_subject():
    ps = view_prompts(3, "a knight")
    assert len(ps) == 3
    assert all("a knight" in p for p in ps)
    assert "front" in ps[0].lower() and "back" in ps[1].lower()

def test_view_prompts_clamped():
    assert len(view_prompts(0, "")) == 1
    assert len(view_prompts(9, "")) == 4

def test_engines_registry_has_fal_models():
    for k in ("tripo", "hunyuan", "trellis", "rodin", "triposr"):
        assert k in ENGINES and ENGINES[k]["endpoint"].startswith(("fal-ai/", "tripo3d/"))

def test_build_args_tripo_includes_image_and_format():
    args = build_engine_args("tripo", ["https://x/img.png"], {"format": "glb", "textures": True, "quality": "standard"})
    assert args["image_url"] == "https://x/img.png" or args.get("image_urls")
    assert "glb" in str(args).lower()

def test_parse_result_picks_mesh_and_textures():
    res = {"model_mesh": {"url": "https://x/m.glb"}, "textures": [{"url": "https://x/t.png"}]}
    out = parse_engine_result("rodin", res)
    assert out["mesh_url"].endswith(".glb") and out["texture_urls"] == ["https://x/t.png"]
```

- [ ] **Step 2: Run — expect failure**
Run: `& $py -m pytest backend/tests/test_asset3d_service.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** the module head:
```python
# backend/app/services/asset3d_service.py
"""Game Assets 3D: image -> (optional multi-view) -> 3D engine -> mesh + shots.
See docs/superpowers/specs/2026-06-28-game-assets-3d-design.md.
Per-engine arg/result shapes are verified against live fal calls (see route smoke)."""
from __future__ import annotations

_ANGLES = [
    "front view, full body, T-pose, plain neutral background",
    "back view, full body, plain neutral background",
    "left 3/4 side view, full body, plain neutral background",
    "right 3/4 side view, full body, plain neutral background",
]

def view_prompts(n: int, subject: str) -> list[str]:
    n = 1 if n < 1 else 4 if n > 4 else n
    subj = (subject or "the same character/object, consistent design").strip()
    return [f"{subj}, {a}" for a in _ANGLES[:n]]

# endpoint + how to map the common request -> the engine's fal arguments.
ENGINES = {
    "tripo":    {"endpoint": "tripo3d/tripo/v2.5/image-to-3d", "formats": ["glb", "fbx", "obj", "stl", "usdz"]},
    "hunyuan":  {"endpoint": "fal-ai/hunyuan3d/v2",            "formats": ["glb", "obj"]},
    "trellis":  {"endpoint": "fal-ai/trellis",                "formats": ["glb"]},
    "rodin":    {"endpoint": "fal-ai/hyper3d/rodin",          "formats": ["glb", "fbx", "obj", "stl", "usdz"]},
    "triposr":  {"endpoint": "fal-ai/triposr",                "formats": ["glb"]},
}

def build_engine_args(engine: str, image_urls: list[str], opts: dict) -> dict:
    fmt = (opts.get("format") or "glb").lower()
    primary = image_urls[0] if image_urls else None
    if engine == "rodin":
        return {"input_image_urls": image_urls, "geometry_file_format": fmt,
                "material": "PBR", "quality_mesh_option": opts.get("quality", "medium"),
                "TAPose": bool(opts.get("tpose")), "use_original_alpha": True, "preview_render": True}
    if engine in ("tripo",):
        a = {"image_url": primary, "texture": bool(opts.get("textures", True)),
             "output_format": fmt, "pbr": True}
        if len(image_urls) > 1:
            a["multiview_images"] = image_urls
        return a
    if engine in ("hunyuan",):
        return {"input_image_url": primary, "textured_mesh": bool(opts.get("textures", True)),
                "output_format": fmt}
    if engine in ("trellis", "triposr"):
        return {"image_url": primary, "output_format": fmt}
    return {"image_url": primary, "output_format": fmt}

def parse_engine_result(engine: str, res: dict) -> dict:
    """Extract mesh URL (+ extra format URLs) + texture URLs + preview image from
    whatever shape the engine returned. Tolerant of the common fal field names."""
    def _url(v):
        if isinstance(v, dict):
            return v.get("url") or v.get("file_url")
        if isinstance(v, str):
            return v
        return None
    mesh = None
    for key in ("model_mesh", "mesh", "model", "glb", "model_glb", "output"):
        if key in res and _url(res[key]):
            mesh = _url(res[key]); break
    meshes = {}
    for m in (res.get("model_meshes") or []):
        u = _url(m)
        if u:
            ext = u.rsplit(".", 1)[-1].split("?")[0].lower()
            meshes[ext] = u
    textures = [t for t in (_url(x) for x in (res.get("textures") or [])) if t]
    preview = None
    for key in ("preview_render", "rendered_image", "preview", "thumbnail"):
        if key in res and _url(res[key]):
            preview = _url(res[key]); break
    return {"mesh_url": mesh, "format_urls": meshes, "texture_urls": textures, "preview_url": preview}
```

- [ ] **Step 4: Run — expect pass.** `& $py -m pytest backend/tests/test_asset3d_service.py -v`.
- [ ] **Step 5: Commit** — `git -C C:/Users/olivi/DeepotusVideo add backend/app/services/asset3d_service.py backend/tests/test_asset3d_service.py && git -C C:/Users/olivi/DeepotusVideo commit -m "feat(assets3d): view prompts + engine registry/adapters"`

---

## Task 2: `MESHY_API_KEY` config + `asset3d` pricing op (backend, TDD)

**Files:** Modify `backend/app/config.py`; Modify `backend/app/services/pricing.py`; Modify `backend/tests/test_asset3d_service.py`.

- [ ] **Step 1:** In `config.py`, after `HEYGEN_API_KEY: str = ""` add:
```python
    MESHY_API_KEY: str = ""
```
And after `has_heygen` (the property pattern) add:
```python
    @property
    def has_meshy(self) -> bool:
        return bool(self.MESHY_API_KEY.strip())
```

- [ ] **Step 2: Failing pricing test** — append to `test_asset3d_service.py`:
```python
def test_pricing_asset3d():
    from app.services.pricing import estimate
    r = estimate({"kind": "asset3d", "engine": "tripo", "textures": True, "multiview": True, "views": 3})
    assert r["total_usd"] > 0
    # tripo std-tex ~0.30 + 3 seedream edits; cheaper engine costs less
    cheap = estimate({"kind": "asset3d", "engine": "triposr", "multiview": False})["total_usd"]
    assert cheap < r["total_usd"]
```
- [ ] **Step 3: Run — expect fail** (`asset3d` kind not handled).
- [ ] **Step 4: Implement** — in `pricing.py` `estimate()`, add a branch (mirror `news_reel`); rates default from provider docs:
```python
    elif kind == "asset3d":
        engine = str(op.get("engine") or "tripo").lower()
        tex = bool(op.get("textures", True))
        rates = {"tripo": 0.30 if tex else 0.20, "triposr": 0.07,
                 "hunyuan": 0.48 if tex else 0.16, "trellis": 0.35, "rodin": 0.40}
        unit = rates.get(engine, 0.30)
        lines.append(_line("fal", f"3D mesh ({engine})", 1, "gen", unit))
        if op.get("multiview"):
            v = int(op.get("views", 3))
            lines.append(_line("fal", "Multi-view edits", v, "img", v * 0.03))
```
- [ ] **Step 5: Run — expect pass.** Full suite green.
- [ ] **Step 6: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): MESHY_API_KEY config + asset3d pricing op"`

---

## Task 3: `generate_asset3d` orchestrator (backend)

**Files:** Modify `backend/app/services/asset3d_service.py`; Modify tests.

- [ ] **Step 1: Failing test** (mock fal + downloads; assert files + return shape):
```python
def test_generate_asset3d_writes_files(tmp_path, monkeypatch):
    from app.services import asset3d_service as A
    from app.config import settings
    monkeypatch.setattr(type(settings), "outputs_path", property(lambda self: tmp_path))
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    (tmp_path / "src.png").write_bytes(b"\x89PNG\r\n\x1a\n0000")
    async def fake_upload(p): return "https://fal/" + A_Path(p).name  # noqa
    monkeypatch.setattr(A, "_upload", lambda p: _await("https://fal/src.png"))
    monkeypatch.setattr(A, "_run_engine", lambda eng, args: _await({"mesh_url": "https://x/m.glb", "format_urls": {}, "texture_urls": [], "preview_url": "https://x/p.png"}))
    monkeypatch.setattr(A, "_download", lambda url, dest: dest.write_bytes(b"FILE") or True)
    out = _await(A.generate_asset3d({"image_filename": "src.png", "engine": "triposr", "multiview": False, "formats": ["glb"]}, "job1"))
    d = tmp_path / "assets3d" / "job1"
    assert (d / "model.glb").exists() and (d / "shot_0.png").exists()
    assert out["glb"].endswith("model.glb")
```
*(helpers `_await`/`A_Path` are defined at the top of the test file: `import asyncio,pathlib as _p; A_Path=_p.Path; def _await(c): return asyncio.get_event_loop().run_until_complete(c) if asyncio.iscoroutine(c) else c`.)*

- [ ] **Step 2: Run — expect fail.**
- [ ] **Step 3: Implement** the orchestrator with seams the test patches (`_upload`, `_run_engine`, `_download`):
```python
async def _upload(path):
    from app.services.fal_service import FalSeedanceClient
    return await FalSeedanceClient.upload_image(path)

async def _run_engine(engine, args):
    import fal_client
    ep = ENGINES[engine]["endpoint"]
    try:
        res = await fal_client.subscribe_async(ep, arguments=args, with_logs=False)
    except Exception as e:
        raise RuntimeError(f"fal.ai: {e}") from e
    return parse_engine_result(engine, res)

def _download(url, dest):
    import urllib.request
    with urllib.request.urlopen(url) as r:
        dest.write_bytes(r.read())
    return True

async def _seedream_edit(image_url, prompt):
    import fal_client
    res = await fal_client.subscribe_async("fal-ai/bytedance/seedream/v4/edit",
        arguments={"image_urls": [image_url], "prompt": prompt, "num_images": 1})
    imgs = res.get("images") or []
    return (imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else None)

async def generate_asset3d(payload: dict, job_id: str):
    import asyncio
    from app.config import settings
    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    formats = [f.lower() for f in (payload.get("formats") or ["glb"])]
    if "glb" not in formats:
        formats = ["glb"] + formats  # GLB always (preview)
    out_dir = settings.outputs_path / "assets3d" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    src = settings.images_path / payload.get("image_filename", "")
    src_url = await _upload(src)
    # shots: shot_0 = source, shot_1..N = multi-view
    import shutil
    shutil.copy2(src, out_dir / "shot_0.png")
    shots = ["shot_0.png"]
    image_urls = [src_url]
    if payload.get("multiview"):
        for i, pr in enumerate(view_prompts(int(payload.get("views", 3)), payload.get("subject", "")), 1):
            u = await _seedream_edit(src_url, pr)
            if u:
                _download(u, out_dir / f"shot_{i}.png")
                shots.append(f"shot_{i}.png")
                image_urls.append(u)

    primary_fmt = next((f for f in formats if f != "glb"), "glb")
    result = await _run_engine(engine, build_engine_args(engine, image_urls,
        {"format": "glb", "textures": payload.get("textures", True),
         "quality": payload.get("quality", "medium"), "tpose": payload.get("tpose")}))
    files = {}
    if result.get("mesh_url"):
        _download(result["mesh_url"], out_dir / "model.glb"); files["glb"] = str(out_dir / "model.glb")
    for ext, url in (result.get("format_urls") or {}).items():
        if ext in formats:
            _download(url, out_dir / f"model.{ext}"); files[ext] = str(out_dir / f"model.{ext}")
    # extra formats not returned in one call -> targeted re-export per engine
    for f in formats:
        if f != "glb" and f not in files and f in ENGINES[engine]["formats"]:
            r2 = await _run_engine(engine, build_engine_args(engine, image_urls, {"format": f, "textures": payload.get("textures", True)}))
            if r2.get("mesh_url"):
                _download(r2["mesh_url"], out_dir / f"model.{f}"); files[f] = str(out_dir / f"model.{f}")
    if result.get("preview_url"):
        _download(result["preview_url"], out_dir / "preview.png")
    return {"glb": files.get("glb"), "files": files, "shots": shots,
            "preview": str(out_dir / "preview.png"), "engine": engine}
```
- [ ] **Step 4: Run — expect pass.**
- [ ] **Step 5: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): generate_asset3d orchestrator (upload->multiview->engine->files+shots)"`

---

## Task 4: route + serve + live smoke (backend)

**Files:** Modify `backend/app/api/routes.py`.

- [ ] **Step 1:** Add the route (mirror `/api/animate`): mint job, pre-register `JobRecord(provider="asset3d", status=GENERATING_VIDEO)`, run `generate_asset3d` via `asyncio.to_thread`-free (it's async) in the background task, on success update the record (`final_video_path=glb`, `image_filename="preview.png"`, `cost_meta=json{engine,files,shots}`, status DONE), on failure status FAILED + error. Gate: if engine != meshy require `settings.FAL_KEY` else 400; meshy requires `settings.has_meshy` (Meshy adapter is stubbed → 501 "Meshy not wired yet" for now).
```python
@router.post("/assets/3d")
async def assets_3d(body: dict, background_tasks: BackgroundTasks):
    from app.services.asset3d_service import generate_asset3d, ENGINES
    from app.services.storage import JobRecord, async_session_factory
    from datetime import datetime as _dt
    import json as _json
    engine = str(body.get("engine") or "tripo").lower()
    if engine == "meshy":
        raise HTTPException(501, "Meshy engine is prepared but not yet wired. Use a fal engine.")
    if engine not in ENGINES:
        raise HTTPException(400, f"Unknown engine: {engine}")
    if not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it in Settings.")
    job_id = str(uuid4()); short = job_id[:8]
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=10,
            title=(body.get("title") or f"3D · {engine}"), image_filename=f"asset3d_{short}",
            provider="asset3d", current_step="Generating 3D")); await s.commit()
    async def _run():
        try:
            r = await generate_asset3d(body, short)
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                jr.status = JobStatus.DONE.value; jr.progress = 100
                jr.final_video_path = r.get("glb"); jr.image_filename = "preview.png"
                jr.current_step = "Complete"; jr.completed_at = _dt.utcnow()
                jr.cost_meta = _json.dumps({"engine": r["engine"], "files": r["files"], "shots": r["shots"], "job": short})
                await s.commit()
        except Exception as e:
            logger.exception(f"asset3d {job_id} failed: {e}")
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr: jr.status = JobStatus.FAILED.value; jr.error = str(e); await s.commit()
    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "queued"}
```
- [ ] **Step 2:** Add serve routes:
```python
@router.get("/assets/3d/{job}/{fmt}")
async def get_asset3d_file(job: str, fmt: str):
    p = settings.outputs_path / "assets3d" / Path(job).name / f"model.{Path(fmt).name}"
    if not p.is_file(): raise HTTPException(404, "Not found")
    return FileResponse(p)

@router.get("/assets/3d/{job}/shot/{i}")
async def get_asset3d_shot(job: str, i: int):
    p = settings.outputs_path / "assets3d" / Path(job).name / f"shot_{int(i)}.png"
    if not p.is_file(): raise HTTPException(404, "Not found")
    return FileResponse(p)
```
- [ ] **Step 3: Deploy backend + restart.** Live smoke with the **cheapest** engine (TripoSR, ~$0.07), no multiview, using an existing Library image:
```powershell
$body = @{ engine="triposr"; image_filename="<an existing image>.png"; multiview=$false; formats=@("glb") } | ConvertTo-Json
$j=(iwr http://127.0.0.1:8765/api/assets/3d -Method POST -Body $body -ContentType application/json -UseBasicParsing).Content|ConvertFrom-Json
# poll /api/jobs for provider=asset3d -> done; confirm outputs/assets3d/<short>/model.glb + shot_0.png + preview.png
```
Expected: a `done` asset3d job; `model.glb` + `shot_0.png` exist. (If the live fal arg/result shape differs, fix `build_engine_args`/`parse_engine_result` for that engine — this is the verify-live step — and re-smoke.)
- [ ] **Step 4: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): /api/assets/3d route + file/shot serving + live smoke"`

---

## Task 5: vendor `<model-viewer>` + nav entry + router branch + page skeleton (bundle)

**Files:** Create `frontend/dist/assets/model-viewer.min.js`; Modify the bundle + `frontend/dist/index.html` (script include).

- [ ] **Step 1:** Download the pinned model-viewer ESM build into `frontend/dist/assets/model-viewer.min.js` (e.g. `@google/model-viewer@4.0.0/dist/model-viewer.min.js`) and add `<script type="module" src="/assets/model-viewer.min.js"></script>` to `frontend/dist/index.html` `<head>`. (Vendored → offline.)
- [ ] **Step 2:** Nav entry — count-guarded patch, anchor (end of nav array, unique):
`{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}]`
→ insert before it:
`{id:"assets3d",label:"Game Assets",icon:"cube",desc:"image → 3D model",new:!0},{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}]`
*(If `icon:"cube"` doesn't render, fall back to an existing icon name confirmed in the icon set, e.g. `"grid"`.)*
- [ ] **Step 3:** Router branch — anchor (unique): `s==="studio"&&r.jsx(Lh,{variant:e,onScheduleRender:` → prepend `s==="assets3d"&&r.jsx(DzGameAssets,{variant:e}),` immediately before it.
- [ ] **Step 4:** Inject a skeleton `DzGameAssets` component (module scope, before `function Mh(`): renders a titled page that lists past `asset3d` jobs (fetch `/api/jobs`, filter `provider==="asset3d"`) and a "Generate" placeholder. Enough to verify nav+router work.
```
function DzGameAssets({variant:e}){var js=x.useState([]),jobs=js[0],setJobs=js[1];x.useEffect(function(){fetch("/api/jobs").then(function(r){return r.json()}).then(function(a){setJobs((a||[]).filter(function(z){return z.provider==="asset3d"}))}).catch(function(){})},[]);return r.jsxs("div",{style:{padding:24,maxWidth:1100,margin:"0 auto"},children:[r.jsx("h2",{style:{color:"var(--ink-strong)"},children:"Game Assets · 3D"}),r.jsx("div",{style:{fontSize:12,color:"var(--ink-soft)",marginBottom:16},children:"Image → 3D model (Tripo / Hunyuan3D / TRELLIS / Rodin / TripoSR)"}),r.jsx("div",{children:jobs.length?jobs.length+" asset(s)":"No 3D assets yet."})]})}
```
- [ ] **Step 5:** `node --check`; deploy bundle + index.html; browser: the nav shows "Game Assets"; clicking it renders the page (no console errors); model-viewer custom element is defined (`customElements.get('model-viewer')`).
- [ ] **Step 6: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): vendored model-viewer + Game Assets nav/router + page skeleton"`

---

## Task 6: generator panel (bundle)

**Files:** Modify the bundle (extend `DzGameAssets`).

- [ ] **Step 1:** Add the generator: image source (reuse the Library image grid fetch `/api/images`, a thumbnail picker + an upload `<input type=file>` → `/api/images/upload`), an **engine** `re` dropdown whose options carry the description+cost (`[{value:"tripo",label:"Tripo3D v2.5 — game-ready topology, broad export (~$0.30)"},{value:"hunyuan",label:"Hunyuan3D — cleanest geometry (~$0.16–0.48)"},{value:"trellis",label:"TRELLIS — best textures (~$0.16–0.50)"},{value:"rodin",label:"Hyper3D Rodin — pro realism ($0.40)"},{value:"triposr",label:"TripoSR — fastest/cheapest ($0.07)"},{value:"meshy",label:"Meshy 6 — needs API key (Settings)"}]`), a **subject** input, a **multi-view boost** toggle + **views** slider (1–4) shown when on, **textures** toggle, **T-pose** toggle, a **target formats** multi-select (GLB always-on/disabled, + FBX/OBJ/STL/USDZ), a small live cost line, and a **Generate** button that POSTs `/api/assets/3d` then polls `/api/jobs` until the new asset3d job is done (refresh the list). Selecting `meshy` without a key shows a "Add a Meshy key in Settings" note and disables Generate.
- [ ] **Step 2:** `node --check`; deploy; browser: pick an image, choose engine (label shows description+cost), toggle options, Generate → a job appears and progresses. No console errors.
- [ ] **Step 3: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): Game Assets generator panel (engine picker + options + generate)"`

---

## Task 7: results grid — preview + downloads + shots (bundle)

**Files:** Modify the bundle (extend `DzGameAssets`).

- [ ] **Step 1:** Render past assets as cards from the job's `cost_meta` JSON (`{engine,files,shots,job}`): poster `<img src=/api/images/preview.png?...>` (served per job — use `/api/assets/3d/{job}/...`); a **▶ Rotate** button that swaps the poster for `<model-viewer src=/api/assets/3d/{job}/glb camera-controls auto-rotate ...>`; a **Download ▾** listing each available format (`<a href=/api/assets/3d/{job}/{fmt} download>`); and a **Shots** row: for each `shot_i` a thumbnail `<img src=/api/assets/3d/{job}/shot/{i}>` with a **Download** link and a **Save to Library** button (POST the shot to `/api/images/upload` via fetch+blob, or a small `/api/assets/3d/{job}/shot/{i}/save` that copies into `images_path`).
- [ ] **Step 2:** `node --check`; deploy; browser: a completed asset shows the poster, Rotate spins the GLB in `<model-viewer>`, each format downloads, each shot downloads + Save-to-Library adds it to the Library Images. No console errors.
- [ ] **Step 3: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): results grid — 3D preview, multi-format download, per-shot download/save"`

---

## Task 8: Settings — `MESHY_API_KEY` field + Library exclusion (bundle)

**Files:** Modify the bundle.

- [ ] **Step 1:** In the Settings keys form (the provider-keys list — grep the form that renders FAL/HeyGen/OpenAI key inputs), add a **Meshy API key** field bound to `MESHY_API_KEY` (same save path as the other keys → `POST /api/settings/keys`) with helper text + a link `https://www.meshy.ai/api`. Confirm the backend `/settings/keys` persists arbitrary keys (it writes the data-dir `.env`); if it whitelists keys, add `MESHY_API_KEY` to that list.
- [ ] **Step 2:** Library "Renders" exclusion — grep the Library `H` (renders) source and filter out `provider==="asset3d"` so 3D jobs never render as `<video>`.
- [ ] **Step 3:** `node --check`; deploy; browser: Settings shows the Meshy field + link and saves; Library Renders does not show 3D jobs as broken videos. No console errors.
- [ ] **Step 4: Commit** — `git -C C:/Users/olivi/DeepotusVideo commit -am "feat(assets3d): Settings Meshy key field + exclude 3D assets from Library renders"`

---

## Task 9: End-to-end verification + deploy

**Files:** none.

- [ ] **Step 1:** `& $py -m pytest backend/tests/test_asset3d_service.py -v` → green.
- [ ] **Step 2:** Browser E2E with a real cheap engine (TripoSR or Tripo no-tex), 1 view: pick a Library image → Generate → job completes → poster shows → Rotate spins the GLB → download GLB (+ STL if engine supports) → each shot downloads + Save-to-Library works → the asset persists after reload. No console errors.
- [ ] **Step 3:** Confirm bundle + backend deployed to `%LOCALAPPDATA%\DeepotusVideoGen`; backend restarted.
- [ ] **Step 4: Commit** any final tweaks.

---

## Self-Review

**Spec coverage:** selectable engines + descriptions + costs (T1 registry, T2 pricing, T6 dropdown) ✓; engine-adapter isolation (T1 build/parse) ✓; optional multi-view boost (T3) ✓; GLB-always + FBX/OBJ/STL/USDZ exports (T3 formats, T7 download) ✓; **individual shot downloads + Save to Library** (T3 shots, T7) ✓; vendored model-viewer preview (T5, T7) ✓; Meshy prepared via Settings key + 501 stub (T4 gate, T8 field) ✓; new category nav+router (T5) ✓; Library renders exclusion (T8) ✓; pricing op (T2) ✓.

**Placeholder scan:** backend tasks carry full code. The two "verify the live fal arg/result shape" notes (T3 build/parse, T4 smoke) are deliberate external-API verification with the adapter isolating changes — not vague TODOs. Frontend T6/T7/T8 specify exact wiring + the data contracts (`cost_meta` json, the serve routes) and reuse verified patterns (`re`, `O`, `le`, Library image grid, `/api/images/upload`, the nav/router anchors); the large page component is built incrementally with `node --check` + browser checks per task (same approach used for `DzAnimation`).

**Type consistency:** `ENGINES` keys (`tripo/hunyuan/trellis/rodin/triposr`) match across registry, `build_engine_args`, pricing rates, and the T6 dropdown. `generate_asset3d` returns `{glb,files,shots,preview,engine}`; the route stores `files`/`shots` in `cost_meta`; T7 reads exactly those. Serve routes `/{fmt}` and `/shot/{i}` match T7's hrefs.

**Risks:** real fal API arg/result shapes per engine (isolated in T1 adapters, verified in T4 smoke); the new full-page component is the biggest frontend lift (T6/T7) — built and browser-verified incrementally.
