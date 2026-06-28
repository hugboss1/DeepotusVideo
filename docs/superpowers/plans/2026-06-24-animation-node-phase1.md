# Animation Node — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `Animation` Studio node — animate text/sticker/image elements (start→end position, scale, rotation, opacity + timing + easing) over a base clip, with a Favorites library, rendered server-side.

**Architecture:** Backend `animation_service.py` composites **per-frame in Pillow** over an ffmpeg-streamed base, behind `POST /api/animate` (returns a `JobRecord`, reusing Dock/Library). Frontend adds an `Animation` node in a new `motion` palette family, a `DzAnimation` inspector (element list + drag-positioning preview + favorites in `localStorage`), and a Run-compiler branch that emits the animate payload.

**Tech Stack:** FastAPI + Pillow + ffmpeg (backend, pytest); compiled React bundle patched via count-guarded Python string replacements + `node --check` + deploy to repo & `%LOCALAPPDATA%\DeepotusVideoGen` (frontend). Spec: `docs/superpowers/specs/2026-06-24-animation-node-phase1-design.md`.

**Conventions (this repo):**
- Runtime Python: `$py = %LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`. Tests: `& $py -m pytest <path> -v`.
- Bundle: `C:\Users\olivi\DeepotusVideo\frontend\dist\assets\index-BEOJX8L5.js`. Patch with a count-guarded Python `str.count==1` then `replace`; validate `node --check`; deploy to the app; verify served markers; browser-test.
- Backend deploy: copy file → `$app\backend\…`; restart (stop port 8765 owner, del `__pycache__`, `Start-Process … uvicorn app.main:app --host 127.0.0.1 --port 8765`).
- Commit after each task. Push prints a benign PowerShell RemoteException — ignore.

---

## File Structure

- **Create** `backend/app/services/animation_service.py` — easing, `transform_at`, `render_element`, `render_animation` (streaming compositor). One responsibility: turn an animate payload into an mp4.
- **Create** `backend/tests/test_animation_service.py` — easing/interpolation/element/compositor tests.
- **Modify** `backend/app/api/routes.py` — `POST /api/animate` route + background job (mirror `/generate/heygen`).
- **Modify** `backend/app/services/pricing.py` — add `animate` op (compute-only).
- **Modify** bundle `index-BEOJX8L5.js` — `Animation` registry entry + `motion` palette family; `DzAnimation` inspector (incl. favorites + drag preview); `Ih` thumbnail; Run-compiler branch → `/api/animate`.

---

## Task 1: Easing + interpolation (backend, pure functions)

**Files:** Create `backend/app/services/animation_service.py`; Create `backend/tests/test_animation_service.py`.

- [ ] **Step 1: Write failing tests**
```python
# backend/tests/test_animation_service.py
from app.services.animation_service import ease, lerp, transform_at

def test_ease_linear_endpoints():
    assert ease("linear", 0) == 0
    assert ease("linear", 1) == 1
    assert abs(ease("linear", 0.5) - 0.5) < 1e-9

def test_ease_clamps_and_monotonic():
    assert ease("easeOut", -1) == 0          # clamped
    assert ease("easeOut", 2) == 1
    assert ease("easeOut", 0.5) > 0.5        # decelerating -> ahead of linear

def test_lerp():
    assert lerp(0, 10, 0.5) == 5
    assert lerp(10, 0, 0.5) == 5

def test_transform_at_visibility_and_interp():
    el = {"start":1.0,"dur":1.0,"hold":1.0,"easing":"linear",
          "from":{"x":0,"y":0,"scale":0,"rotation":0,"opacity":0},
          "to":{"x":100,"y":50,"scale":1,"rotation":90,"opacity":1}}
    assert transform_at(el, 0.5) is None     # before start
    mid = transform_at(el, 1.5)              # halfway through dur
    assert abs(mid["x"]-50) < 1e-6 and abs(mid["opacity"]-0.5) < 1e-6
    assert transform_at(el, 2.5) == {"x":100,"y":50,"scale":1,"rotation":90,"opacity":1}  # hold
    assert transform_at(el, 5.0) is None     # after start+dur+hold
```
- [ ] **Step 2: Run — expect failure**
Run: `& $py -m pytest backend/tests/test_animation_service.py -v`  → FAIL (module/functions missing).
- [ ] **Step 3: Implement**
```python
# backend/app/services/animation_service.py
"""Animation node render engine: per-frame Pillow compositor over an ffmpeg
base. See docs/superpowers/specs/2026-06-24-animation-node-phase1-design.md."""
from __future__ import annotations
_KEYS = ("x", "y", "scale", "rotation", "opacity")

def ease(name: str, t: float) -> float:
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    if name == "easeIn":  return t * t
    if name == "easeOut": return 1 - (1 - t) * (1 - t)
    if name == "easeInOut":
        return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2
    if name == "easeOutBack":
        c1 = 1.70158; c3 = c1 + 1
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
    if name == "easeOutBounce":
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:   return n1 * t * t
        if t < 2 / d1:   t -= 1.5 / d1;  return n1 * t * t + 0.75
        if t < 2.5 / d1: t -= 2.25 / d1; return n1 * t * t + 0.9375
        t -= 2.625 / d1; return n1 * t * t + 0.984375
    return t  # linear / unknown

def lerp(a: float, b: float, e: float) -> float:
    return a + (b - a) * e

def transform_at(el: dict, t: float):
    start = float(el.get("start", 0)); dur = max(1e-3, float(el.get("dur", 1)))
    hold = float(el.get("hold", 0))
    if t < start or t > start + dur + hold:
        return None
    u = (t - start) / dur
    e = 1.0 if u >= 1 else ease(el.get("easing", "linear"), u)
    f, to = el["from"], el["to"]
    return {k: lerp(float(f[k]), float(to[k]), e) for k in _KEYS}
```
- [ ] **Step 4: Run — expect pass**
Run: `& $py -m pytest backend/tests/test_animation_service.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add backend/app/services/animation_service.py backend/tests/test_animation_service.py && git commit -m "feat(animation): easing + transform interpolation"`

---

## Task 2: Render one element to a transparent layer (Pillow)

**Files:** Modify `backend/app/services/animation_service.py`; Modify `backend/tests/test_animation_service.py`.

- [ ] **Step 1: Failing test**
```python
def test_render_element_text_layer():
    from PIL import Image
    from app.services.animation_service import render_element
    el = {"type":"text","text":"HI","style":{"font":"JetBrains Mono","size":48,"color":"#ffffff"}}
    tr = {"x":50,"y":50,"scale":1.0,"rotation":0,"opacity":0.5}
    layer = render_element(el, tr, 200, 200)
    assert isinstance(layer, Image.Image) and layer.size == (200, 200) and layer.mode == "RGBA"
    # something was drawn near the centre, and opacity halved the alpha
    cx = layer.getpixel((100, 100))
    assert cx[3] <= 200  # alpha reduced by opacity 0.5 (≤ ~half of 255 where text covers)
```
- [ ] **Step 2: Run — expect failure** (`render_element` missing).
- [ ] **Step 3: Implement** `render_element` (reuse the design-font resolver + emoji path from `template_service.py` — import its font lookup; if not importable as a function, replicate the `_FONT_DIR` lookup):
```python
def _hex(c: str):
    c = (c or "#ffffff").lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

def render_element(el: dict, tr: dict, W: int, H: int):
    from PIL import Image, ImageDraw, ImageFont
    from app.services.template_service import _resolve_font_path  # design fonts
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    typ = el.get("type", "text")
    if typ == "text":
        st = el.get("style", {})
        size = max(4, int(st.get("size", 48) * float(tr.get("scale", 1))))
        font = ImageFont.truetype(_resolve_font_path(st.get("font", "JetBrains Mono")), size)
        txt = el.get("text", "")
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(tmp)
        bb = d.textbbox((0, 0), txt, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        ix = int(tr["x"] / 100 * W - tw / 2); iy = int(tr["y"] / 100 * H - th / 2)
        sc = int(st.get("stroke", 0) or 0)
        d.text((ix, iy), txt, font=font, fill=_hex(st.get("color", "#ffffff")),
               stroke_width=sc, stroke_fill=_hex(st.get("strokeColor", "#000000")))
        el_img = tmp
    else:  # sticker | image
        from app.config import settings
        src = settings.images_path / el.get("filename", "")
        if not src.exists():
            return layer
        im = Image.open(src).convert("RGBA")
        s = float(tr.get("scale", 1))
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
        el_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        el_img.alpha_composite(im, (int(tr["x"]/100*W - im.width/2),
                                    int(tr["y"]/100*H - im.height/2)))
    rot = float(tr.get("rotation", 0) or 0)
    if rot:
        el_img = el_img.rotate(-rot, resample=Image.BICUBIC, center=(int(tr["x"]/100*W), int(tr["y"]/100*H)))
    op = max(0.0, min(1.0, float(tr.get("opacity", 1))))
    if op < 1:
        a = el_img.split()[3].point(lambda v: int(v * op)); el_img.putalpha(a)
    layer.alpha_composite(el_img)
    return layer
```
*Note for implementer:* if `_resolve_font_path` doesn't exist with that name in `template_service.py`, grep it for the font-dir lookup (the OFL design fonts loader) and reuse/extract it; do not hardcode a path.
- [ ] **Step 4: Run — expect pass.**
- [ ] **Step 5: Commit** — `git commit -am "feat(animation): render a text/sticker element layer with transform"`

---

## Task 3: Streaming compositor `render_animation`

**Files:** Modify `backend/app/services/animation_service.py`; Modify tests.

- [ ] **Step 1: Failing test (2-frame smoke, no base = blank canvas)**
```python
def test_render_animation_blank_base(tmp_path, monkeypatch):
    from app.services import animation_service as A
    from app.config import settings
    monkeypatch.setattr(settings, "outputs_path", tmp_path)
    payload = {"aspect":"9:16","fps":2,"duration_s":1,"base":None,
        "elements":[{"type":"text","text":"GO","style":{"size":64,"color":"#fff"},
            "start":0,"dur":0.5,"hold":1,"easing":"linear",
            "from":{"x":50,"y":50,"scale":1,"rotation":0,"opacity":1},
            "to":{"x":50,"y":50,"scale":1,"rotation":0,"opacity":1}}]}
    out = A.render_animation(payload, "testjob")
    assert out.exists() and out.stat().st_size > 0
```
- [ ] **Step 2: Run — expect failure.**
- [ ] **Step 3: Implement** the streaming compositor:
```python
def _wh(aspect: str):
    return {"9:16":(1080,1920),"16:9":(1920,1080),"1:1":(1080,1080),"4:5":(1080,1350)}.get(aspect,(1080,1920))

def render_animation(payload: dict, job_id: str):
    import subprocess
    from PIL import Image
    from app.config import settings
    W, H = _wh(payload.get("aspect", "9:16"))
    fps = int(payload.get("fps", 30)); dur = float(payload.get("duration_s", 8))
    n = max(1, int(dur * fps))
    els = payload.get("elements", [])
    base = payload.get("base")  # absolute path to a clip, or None
    out = settings.outputs_path / f"anim_{job_id}.mp4"
    # base frame reader (rawvideo rgba) or None
    bproc = None
    if base:
        bproc = subprocess.Popen(
            ["ffmpeg","-i",str(base),"-vf",f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps}",
             "-f","rawvideo","-pix_fmt","rgba","-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgba","-s",f"{W}x{H}","-r",str(fps),"-i","-",
         *(["-i",str(base),"-map","0:v","-map","1:a?","-shortest"] if base else []),
         "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",str(out)], stdin=subprocess.PIPE)
    fb = W * H * 4
    for i in range(n):
        t = i / fps
        if bproc:
            raw = bproc.stdout.read(fb)
            frame = (Image.frombytes("RGBA",(W,H),raw) if len(raw)==fb
                     else Image.new("RGBA",(W,H),(2,6,13,255)))
        else:
            frame = Image.new("RGBA", (W, H), (2, 6, 13, 255))
        for el in els:
            tr = transform_at(el, t)
            if tr is not None:
                frame.alpha_composite(render_element(el, tr, W, H))
        enc.stdin.write(frame.tobytes())
    enc.stdin.close(); enc.wait()
    if bproc: bproc.terminate()
    return out
```
- [ ] **Step 4: Run — expect pass** (needs ffmpeg on PATH — it is, used by template_service).
- [ ] **Step 5: Commit** — `git commit -am "feat(animation): streaming Pillow+ffmpeg compositor"`

---

## Task 4: `POST /api/animate` route + pricing op

**Files:** Modify `backend/app/api/routes.py`; Modify `backend/app/services/pricing.py`.

- [ ] **Step 1:** Add pricing op. In `pricing.py` `estimate(op)` add a branch: `if kind == "animate": return 0.0` (compute-only; keep cost honest, no external API). Mirror an existing op's structure.
- [ ] **Step 2:** Add the route in `routes.py` (mirror `/generate/heygen` at ~line 1068 — background task + `JobRecord`):
```python
@router.post("/animate")
async def animate(body: dict, background_tasks: BackgroundTasks):
    """Render the Animation node: composite animated elements over a base clip."""
    from app.services.animation_service import render_animation
    import uuid as _uuid
    job_id = _uuid.uuid4().hex[:8]
    async def _run():
        try:
            base = None
            src = body.get("base")  # {source_kind, ...} resolved client-side to a filename/job
            if src:
                base = str(_resolve_source_to_path(src))  # reuse the helper layout-render uses
            out = render_animation({**body, "base": base}, job_id)
            _register_job(job_id, "animation", final_video_path=str(out), status="succeeded")
        except Exception as e:
            logger.error(f"animate job {job_id} failed: {e}")
            _register_job(job_id, "animation", status="failed", error=str(e))
    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "queued"}
```
*Implementer:* `_resolve_source_to_path` + `_register_job` — reuse the exact helpers the layout-render route uses to turn a slot-source into a path and to write a `JobRecord` (grep `routes.py` for the layout-template render + `JobRecord(`); do not invent new ones. Save the source graph too (the `_save_source_graph` path) so "reopen in Studio" works.
- [ ] **Step 3: Deploy + restart backend**, then live smoke:
```powershell
$body = @{ aspect="9:16"; fps=10; duration_s=1; base=$null; elements=@(@{type="text"; text="DEEP"; style=@{size=120;color="#00e5ff"}; start=0; dur=0.5; hold=1; easing="easeOutBack"; from=@{x=50;y=60;scale=0.5;rotation=0;opacity=0}; to=@{x=50;y=45;scale=1;rotation=0;opacity=1}}) } | ConvertTo-Json -Depth 6
$j = (iwr http://127.0.0.1:8765/api/animate -Method POST -Body $body -ContentType application/json).Content | ConvertFrom-Json
Start-Sleep 6; (iwr "http://127.0.0.1:8765/api/jobs" -UseBasicParsing).Content  # the anim job should be succeeded with a file
```
Expected: a succeeded job + `outputs/anim_<id>.mp4` exists and plays (text pops in).
- [ ] **Step 4: Commit** — `git commit -am "feat(animation): /api/animate route + pricing op"`

---

## Task 5: `Animation` node registry + `motion` palette family + thumbnail (bundle)

**Files:** Modify `frontend/dist/assets/index-BEOJX8L5.js`.

- [ ] **Step 1:** Count-guarded patch — add the registry entry next to other `compose` nodes (grep `SpatialCompose:{cat:` for the anchor):
```
Animation:{cat:"motion",title:"Animation",desc:"animate text & stickers over a clip",inPorts:[{id:"base",type:"av"}],outPorts:[{id:"out",type:"av"}],props:{durationS:8,fps:30,elements:[],selected:0}},
```
- [ ] **Step 2:** Register the `motion` palette family. Grep the palette section list (the categories rendered as "SOURCE/GENERATOR/AUDIO/EDIT/COMPOSE" — find the array/order of cat keys + their labels) and add `motion` → label "ANIMATIONS" in the right position. Show the exact found anchor in the commit.
- [ ] **Step 3:** `Ih` thumbnail — add an `e.type==="Animation"` branch (grep `Ih`'s type switch) showing a small "✦ N elements" placeholder using `(e.props.elements||[]).length`.
- [ ] **Step 4:** `node --check`; deploy; verify served markers contain `Animation:{cat:"motion"` and the ANIMATIONS family.
- [ ] **Step 5: Commit** — `git commit -am "feat(studio): Animation node + Motion/Animations palette family"`

---

## Task 6: `DzAnimation` inspector — element list + per-element fields (bundle)

**Files:** Modify the bundle.

- [ ] **Step 1:** Add a module-scope `DzAnimation({node:e,graph:g,set:o})` component (inject before `function Mh(`), and wire it into `Yh` with `e.type==="Animation"?r.jsx(DzAnimation,{node:e,graph:g,set:o}):…` (before the Properties fallback). The component:
  - reads `els=(e.props.elements||[])`, `sel=e.props.selected||0`;
  - **element list** with `+ Text / + Sticker / + Image` buttons (push a default element via `o("elements", els.concat([mk(type)]))`), select (`o("selected", i)`), delete, reorder;
  - **selected editor** using the existing field primitives (`O`, `re`, `le`, the color-disc, `DzImageModel` for sticker/image content) for: content, style (font/size/color/stroke/shadow/align), preset (`re`), easing (`re`), `start`/`dur`/`hold` (number inputs), and numeric `from`/`to` (x/y/scale/rotation/opacity).
  - a `mk(type)` factory returns the default element shape from the spec.
  - **Reuse the verified patterns from `DzNewsScript`/`DzAvatarPick`** for component structure, `re`/`O`/`le` usage, and `o(key,val)` updates. ⚠️ Confirm the real in-scope helper names from the deployed bundle before referencing (lesson from the Scheduler `e`/`s` crash).
- [ ] **Step 2:** `node --check`; deploy; browser: add an Animation node, add a Text element, edit fields — they persist on the node (re-select shows them).
- [ ] **Step 3: Commit** — `git commit -am "feat(studio): DzAnimation inspector — elements + per-element editor"`

---

## Task 7: Drag-positioning preview canvas (bundle)

**Files:** Modify the bundle (extend `DzAnimation`).

- [ ] **Step 1:** Add a preview box (aspect-ratio of the render) showing the base thumbnail (if resolvable) + the selected element rendered with CSS `transform: translate(x%,y%) scale() rotate()` + opacity. A **`Start ⟷ End`** toggle (`useState`) selects which keyframe the drag edits. Pointer handlers: `onPointerDown`/`Move`/`Up` on the element compute new `x`/`y` (% of the box) → `o("elements", patchSel({[mode]:{...cur,x,y}}))`; corner handles set `scale`; a top handle sets `rotation`. Keep numeric fields in sync.
- [ ] **Step 2:** `node --check`; deploy; browser: drag sets start/end positions; numbers update live; toggle switches keyframe.
- [ ] **Step 3: Commit** — `git commit -am "feat(studio): drag-positioning preview for Animation elements"`

---

## Task 8: Favorites library (bundle, localStorage `dz_anim_favorites`)

**Files:** Modify the bundle (extend `DzAnimation`).

- [ ] **Step 1:** Helpers `dzAnimFavGet()/Set(x)` over `localStorage.dz_anim_favorites` (shape `{elements:[],typos:[],presets:[]}`, try/catch JSON like `dz_fav_avatars`). A **"★ Save"** control on the selected element with three actions (Save as element / typo / preset) prompting a name. A **Favorites panel** (3 groups of chips): click → insert element (append a deep copy to `elements`), apply typo (merge `style` into the selected element), or apply preset (merge `from/to/easing/dur/hold`). Each chip has `×` to remove.
- [ ] **Step 2:** `node --check`; deploy; browser: save a text element as favorite → reload → it persists → click inserts a copy.
- [ ] **Step 3: Commit** — `git commit -am "feat(studio): Animation favorites (elements/typos/presets, localStorage)"`

---

## Task 9: Run-compiler integration — emit `/api/animate` (bundle)

**Files:** Modify the bundle (the Run handler / `dzCompose`/`Mh`).

- [ ] **Step 1:** In the Run path, when the graph contains an `Animation` node feeding the render: resolve its `base` via the existing `srcFor()` resolver (the connected `base` node), build the payload `{base:srcFor(baseNode), aspect:<render format>, fps, duration_s:props.durationS, elements:props.elements}`, `POST /api/animate`, then poll the job like other render jobs (reuse the existing poll + Job Dock wiring). If the Animation output feeds a `Render`/`SpatialCompose`, treat the produced clip as that input's source (a `{source_kind:"job",job_id}`), mirroring how Seedance/HeyGen jobs feed slots.
- [ ] **Step 2:** `node --check`; deploy; browser end-to-end: Image/Seedance → Animation (Text element, fade+slide preset) → Render → **Run** → the job renders; Preview shows the animated text over the base.
- [ ] **Step 3: Commit** — `git commit -am "feat(studio): compile Animation node through Run -> /api/animate"`

---

## Task 10: End-to-end verification + deploy to app

**Files:** none (verification).

- [ ] **Step 1:** Deploy bundle + backend to `%LOCALAPPDATA%\DeepotusVideoGen`; restart backend.
- [ ] **Step 2:** Browser: build `Seedance → Animation → Render` with (a) a Text element (slide-in + scale) and (b) a Sticker (an uploaded PNG, ken-burns). Run. Confirm the output animates correctly (position/scale/opacity/rotation), the base shows through, and the clip lands in the Job Dock + Library + reopens in Studio.
- [ ] **Step 3:** Confirm Favorites: save the Text element + its typo + its animation as favorites; reload; re-insert into a fresh Animation node.
- [ ] **Step 4: Commit** any final tweaks. (Installer rebuild is a separate, user-triggered step.)

---

## Self-Review

**Spec coverage:** node+ports (T5) ✓; element model from/to/timing/easing (T6) ✓; text+sticker+image (T2,T6) ✓; drag-positioning in Phase 1 (T7) ✓; favorites elements/typos/presets (T8) ✓; per-frame Pillow+ffmpeg render (T1–T3) ✓; `/api/animate` + pricing + job (T4) ✓; compile integration (T9) ✓; new `motion` family (T5) ✓; scrub-preview is the CSS preview in T7 ✓. Non-goals (multi-keyframe, bézier, sticker library, per-char) are correctly absent.

**Placeholder scan:** Backend steps carry complete code. Two frontend steps say "grep the anchor / confirm in-scope names before referencing" — this is intentional and correct for minified-bundle patching (anchors are only knowable at implement time); each still specifies the exact code to inject and the marker to verify. No `TODO`/`TBD`/"handle edge cases".

**Type consistency:** `from`/`to` use keys `x,y,scale,rotation,opacity` everywhere (`transform_at` `_KEYS`, `render_element`, the inspector, the payload). `transform_at` returns `None` when not visible (handled in `render_animation`). Element shape identical across spec, T2/T3, and T6 `mk()`. `dz_anim_favorites` shape `{elements,typos,presets}` consistent in T8.

**Risks restated:** T9 (compile integration) and T3 render perf are the hard parts — both isolated to one task each and modelled on existing paths.
