# Animation Node — Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 2-keyframe (`from`/`to`) model with an N-keyframe timeline, add per-segment cubic-bézier-preset easing, and a scrub/play preview — fully backward-compatible with Phase 1.

**Architecture:** Backend `animation_service.py` gains a `kfs_of()` normalizer + a multi-keyframe `transform_at()` and cubic-bézier easings; `render_element`/`render_animation`/`/api/animate`/`Mh`/`srcFor` are untouched (they consume whatever `transform_at` returns). Frontend extends the existing `DzAnimation` bundle component: an active-keyframe model, a timeline strip of draggable dots, a scrub/play preview, and bézier-preset easings — all reading legacy elements through a JS `dzKfs()` normalizer.

**Tech Stack:** FastAPI + Pillow + ffmpeg (backend, pytest); compiled React bundle patched via count-guarded Python `str.count==1` replacements + `node --check` + deploy. Spec: `docs/superpowers/specs/2026-06-28-animation-node-phase2-design.md`.

**Conventions (this repo — verified during Phase 1):**
- Runtime Python: `$py = %LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`. Tests: from the repo root, `& $py -m pytest backend/tests/test_animation_service.py -v` (works via `backend/conftest.py`; pytest is installed in the runtime's `site-packages`).
- Bundle: `C:\Users\olivi\DeepotusVideo\frontend\dist\assets\index-BEOJX8L5.js`. Patch with a count-guarded Python script (write the script to a file, not a heredoc); validate `node --check`; deploy `Copy-Item` to `%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js`; browser-test at **http://127.0.0.1:8765/** via Claude-in-Chrome (drop nodes with a synthetic `DragEvent` carrying `dataTransfer["application/node-type"]`; drive the inspector via DOM).
- Backend deploy: copy changed files → `$app\backend\…`; restart (stop port 8765 owner, del `__pycache__`, relaunch `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765` with WorkingDirectory `$app\backend`).
- Bundle field primitives (in scope, module-level): `ie`=panel(label,defaultOpen,children), `O`=labeled row, `re`=select({value,options:[{value,label}],onChange}), `le`=input({mono,value,onChange}), `r`=jsx runtime, `x`=React (`x.useState`/`x.useRef`). Node updater inside `DzAnimation` is `o(key,val)` (writes `node.props[key]`).
- Commit after each task. `git push` / `git commit` print a benign PowerShell RemoteException on the LF→CRLF warning — the commit still lands; verify with `git log --oneline -1`.

---

## File Structure

- **Modify** `backend/app/services/animation_service.py` — add `_bezier_y_for_x` + `_BEZIER` + bézier branch in `ease()`; add `kfs_of()`; rewrite `transform_at()` for N keyframes. One responsibility unchanged: payload → mp4.
- **Modify** `backend/tests/test_animation_service.py` — bézier + multi-keyframe + legacy-regression tests.
- **Modify** bundle `index-BEOJX8L5.js` — `DzAnimation`: `dzKfs()` normalizer, active-keyframe state, rewired editor/preview/easing, timeline strip, scrub/play, favorites with `keyframes[]`.

---

## Task 1: Cubic-bézier easing (backend, TDD)

**Files:** Modify `backend/app/services/animation_service.py`; Modify `backend/tests/test_animation_service.py`.

- [ ] **Step 1: Write failing tests** — append to `test_animation_service.py`:
```python
def test_ease_cubic_bezier_endpoints():
    from app.services.animation_service import ease
    assert abs(ease("smooth", 0)) < 1e-6
    assert abs(ease("smooth", 1) - 1) < 1e-6
    assert abs(ease("cubic-bezier(0.4,0,0.2,1)", 0)) < 1e-6
    assert abs(ease("cubic-bezier(0.4,0,0.2,1)", 1) - 1) < 1e-6

def test_ease_cubic_bezier_midpoint_decelerates():
    from app.services.animation_service import ease
    y = ease("cubic-bezier(0.4,0,0.2,1)", 0.5)
    assert 0 < y < 1
    assert y > 0.5  # fast-out/slow-in -> ahead of linear at the midpoint

def test_ease_bezier_unknown_falls_back_linear():
    from app.services.animation_service import ease
    assert abs(ease("cubic-bezier(bad)", 0.5) - 0.5) < 1e-9
```

- [ ] **Step 2: Run — expect failure**
Run: `& $py -m pytest backend/tests/test_animation_service.py -k "bezier" -v` → FAIL (`smooth`/`cubic-bezier` return `t`).

- [ ] **Step 3: Implement** — in `animation_service.py`, insert these module-level helpers immediately **before** `def ease(`:
```python
def _bezier_y_for_x(p1x, p1y, p2x, p2y, x):
    """Cubic bezier with P0=(0,0), P3=(1,1): solve Bx(s)=x for s, return By(s)."""
    def bx(s): return 3 * (1 - s) ** 2 * s * p1x + 3 * (1 - s) * s * s * p2x + s ** 3
    def by(s): return 3 * (1 - s) ** 2 * s * p1y + 3 * (1 - s) * s * s * p2y + s ** 3
    def dbx(s): return 3 * (1 - s) ** 2 * p1x + 6 * (1 - s) * s * (p2x - p1x) + 3 * s * s * (1 - p2x)
    s = x
    for _ in range(8):
        err = bx(s) - x
        if abs(err) < 1e-6:
            break
        d = dbx(s)
        if abs(d) < 1e-6:
            break
        s -= err / d
        s = 0.0 if s < 0 else 1.0 if s > 1 else s
    if abs(bx(s) - x) > 1e-4:  # bisection fallback
        lo, hi = 0.0, 1.0
        for _ in range(40):
            s = (lo + hi) / 2
            if bx(s) < x:
                lo = s
            else:
                hi = s
    return by(s)


_BEZIER = {
    "smooth": (0.4, 0.0, 0.2, 1.0),
    "easeInOutSine": (0.45, 0.05, 0.55, 0.95),
    "anticipate": (0.36, 0.0, 0.66, -0.56),
    "overshoot": (0.34, 1.56, 0.64, 1.0),
}
```
Then in `ease(name, t)`, immediately **after** the clamp line `t = 0.0 if t < 0 else 1.0 if t > 1 else t`, add:
```python
    if name in _BEZIER:
        return _bezier_y_for_x(*_BEZIER[name], t)
    if isinstance(name, str) and name.startswith("cubic-bezier(") and name.endswith(")"):
        try:
            a, b, c, d = (float(v) for v in name[len("cubic-bezier("):-1].split(","))
            return _bezier_y_for_x(a, b, c, d, t)
        except Exception:
            return t
```

- [ ] **Step 4: Run — expect pass**
Run: `& $py -m pytest backend/tests/test_animation_service.py -v` → all PASS (existing 6 + 3 new).

- [ ] **Step 5: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo add backend/app/services/animation_service.py backend/tests/test_animation_service.py
git -C C:/Users/olivi/DeepotusVideo commit -m "feat(animation): cubic-bezier preset easings"
```

---

## Task 2: `kfs_of` + multi-keyframe `transform_at` (backend, TDD)

**Files:** Modify `backend/app/services/animation_service.py`; Modify `backend/tests/test_animation_service.py`.

- [ ] **Step 1: Write failing tests** — append:
```python
def test_kfs_of_legacy_from_to():
    from app.services.animation_service import kfs_of
    el = {"from": {"x": 0, "y": 0, "scale": 0, "rotation": 0, "opacity": 0},
          "to": {"x": 100, "y": 50, "scale": 1, "rotation": 90, "opacity": 1}, "easing": "easeOut"}
    kfs = kfs_of(el)
    assert len(kfs) == 2 and kfs[0]["t"] == 0 and kfs[1]["t"] == 1
    assert kfs[0]["x"] == 0 and kfs[1]["x"] == 100 and kfs[0]["easing"] == "easeOut"

def test_kfs_of_sorts_keyframes():
    from app.services.animation_service import kfs_of
    el = {"keyframes": [{"t": 1, "x": 9}, {"t": 0, "x": 1}, {"t": 0.5, "x": 5}]}
    ts = [k["t"] for k in kfs_of(el)]
    assert ts == [0, 0.5, 1]

def test_transform_at_multi_keyframe():
    from app.services.animation_service import transform_at
    el = {"start": 0, "dur": 2, "hold": 0, "keyframes": [
        {"t": 0, "x": 0, "y": 0, "scale": 1, "rotation": 0, "opacity": 0, "easing": "linear"},
        {"t": 0.5, "x": 100, "y": 0, "scale": 1, "rotation": 0, "opacity": 1, "easing": "linear"},
        {"t": 1, "x": 0, "y": 0, "scale": 1, "rotation": 0, "opacity": 0}]}
    a = transform_at(el, 0.5)   # u=0.25 -> halfway up segment 0..0.5
    assert abs(a["x"] - 50) < 1e-6 and abs(a["opacity"] - 0.5) < 1e-6
    b = transform_at(el, 1.0)   # u=0.5 -> the middle keyframe exactly
    assert abs(b["x"] - 100) < 1e-6
    c = transform_at(el, 1.5)   # u=0.75 -> halfway down segment 0.5..1
    assert abs(c["x"] - 50) < 1e-6

def test_transform_at_legacy_unchanged():
    from app.services.animation_service import transform_at
    el = {"start": 1, "dur": 1, "hold": 1, "easing": "linear",
          "from": {"x": 0, "y": 0, "scale": 0, "rotation": 0, "opacity": 0},
          "to": {"x": 100, "y": 50, "scale": 1, "rotation": 90, "opacity": 1}}
    assert transform_at(el, 0.5) is None
    mid = transform_at(el, 1.5)
    assert abs(mid["x"] - 50) < 1e-6 and abs(mid["opacity"] - 0.5) < 1e-6
    assert transform_at(el, 2.5) == {"x": 100, "y": 50, "scale": 1, "rotation": 90, "opacity": 1}
    assert transform_at(el, 5.0) is None
```

- [ ] **Step 2: Run — expect failure**
Run: `& $py -m pytest backend/tests/test_animation_service.py -k "kfs_of or multi_keyframe" -v` → FAIL (`kfs_of` missing; legacy `transform_at` ignores `keyframes`).

- [ ] **Step 3: Implement** — add `kfs_of` immediately **before** `def transform_at(`:
```python
def kfs_of(el: dict):
    """Normalize an element to a sorted keyframe list. Accepts the Phase-2
    `keyframes[]` shape or synthesizes one from the legacy `from`/`to`."""
    kfs = el.get("keyframes")
    if isinstance(kfs, list) and len(kfs) >= 2:
        return sorted(kfs, key=lambda k: float(k.get("t", 0)))
    f = el.get("from", {})
    to = el.get("to", {})
    base = {k: 0 for k in _KEYS}
    k0 = {**base, **f, "t": 0.0, "easing": el.get("easing", "linear")}
    k1 = {**base, **to, "t": 1.0}
    return [k0, k1]
```
Then **replace** the entire body of `transform_at` with:
```python
def transform_at(el: dict, t: float):
    start = float(el.get("start", 0))
    dur = max(1e-3, float(el.get("dur", 1)))
    hold = float(el.get("hold", 0))
    if t < start or t > start + dur + hold:
        return None
    kfs = kfs_of(el)
    u = (t - start) / dur
    if u >= 1:
        last = kfs[-1]
        return {k: float(last[k]) for k in _KEYS}
    i = 0
    while i < len(kfs) - 2 and u > float(kfs[i + 1]["t"]):
        i += 1
    a, b = kfs[i], kfs[i + 1]
    ta, tb = float(a["t"]), float(b["t"])
    span = max(1e-9, tb - ta)
    e = ease(a.get("easing", "linear"), (u - ta) / span)
    return {k: lerp(float(a[k]), float(b[k]), e) for k in _KEYS}
```

- [ ] **Step 4: Run — expect pass**
Run: `& $py -m pytest backend/tests/test_animation_service.py -v` → all PASS (legacy regression included).

- [ ] **Step 5: Deploy backend + live smoke** — copy `animation_service.py` → `$app\backend\app\services\`, restart backend, then:
```powershell
$body = @{ aspect="9:16"; fps=10; duration_s=2; base=$null; elements=@(@{type="text"; text="KF"; style=@{size=120;color="#00e5ff"}; start=0; dur=2; hold=0; keyframes=@(@{t=0;x=50;y=80;scale=1;rotation=0;opacity=0;easing="overshoot"},@{t=0.5;x=50;y=20;scale=1.4;rotation=0;opacity=1;easing="smooth"},@{t=1;x=50;y=50;scale=1;rotation=0;opacity=1})}) } | ConvertTo-Json -Depth 8
$j=(iwr http://127.0.0.1:8765/api/animate -Method POST -Body $body -ContentType application/json -UseBasicParsing).Content|ConvertFrom-Json
Start-Sleep 6; (iwr "http://127.0.0.1:8765/api/jobs" -UseBasicParsing).Content|ConvertFrom-Json|?{$_.job_id -eq $j.job_id}|Select status,final_video_path
```
Expected: a `done` job + `anim_<id>.mp4` that plays a 3-keyframe move (rises with overshoot, settles).

- [ ] **Step 6: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "feat(animation): multi-keyframe transform_at + kfs_of (legacy back-compat)"
```

---

## Task 3: Frontend — keyframe data model in `DzAnimation` (bundle)

**Files:** Modify `index-BEOJX8L5.js`. Use a count-guarded Python patch script; `node --check`; deploy; browser-test.

Goal: `DzAnimation` reads/writes `keyframes[]` with an **active-keyframe index**, backward-compatible with legacy `from`/`to`, and the easing dropdown becomes per-keyframe with bézier presets. (The visual timeline is Task 4; here the active keyframe is still chosen by the existing Start⟷End buttons, generalized to prev/next.)

- [ ] **Step 1: Add the JS normalizer + active-keyframe state.** Anchor (unique — the Phase-1 hooks line):
`var drag=x.useRef(null),boxRef=x.useRef(null);var fv=x.useState(0),favTick=fv[0],bumpFav=fv[1];`
Replace with the same text **followed by**:
```
var akS=x.useState(0),ak=akS[0],setAk=akS[1];
function dzKfs(el){var kf=el&&el.keyframes;if(kf&&kf.length>=2)return kf.slice().sort(function(a,b){return (a.t||0)-(b.t||0)});var f=(el&&el.from)||{},to=(el&&el.to)||{};return [{t:0,x:f.x||0,y:f.y||0,scale:f.scale!=null?f.scale:1,rotation:f.rotation||0,opacity:f.opacity!=null?f.opacity:0,easing:(el&&el.easing)||"linear"},{t:1,x:to.x!=null?to.x:50,y:to.y!=null?to.y:50,scale:to.scale!=null?to.scale:1,rotation:to.rotation||0,opacity:to.opacity!=null?to.opacity:1}];}
function curKfs(){return cur?dzKfs(cur):[];}
function akClamped(){var n=curKfs().length;return Math.max(0,Math.min(ak,n-1));}
```

- [ ] **Step 2: `mk(t)` emits keyframes.** Anchor (the Phase-1 factory return — unique):
`from:{x:50,y:60,scale:.6,rotation:0,opacity:0},to:{x:50,y:45,scale:1,rotation:0,opacity:1},start:0,dur:.8,hold:2,easing:"easeOutBack",preset:null};`
Replace with:
`keyframes:[{t:0,x:50,y:60,scale:.6,rotation:0,opacity:0,easing:"easeOutBack"},{t:1,x:50,y:45,scale:1,rotation:0,opacity:1}],start:0,dur:.8,hold:2,preset:null};`

- [ ] **Step 3: Rewrite the keyframe-patch helper to write `keyframes[ak]` (upgrading legacy on first edit).** Anchor (Phase-1 `patchKF` — unique):
`function patchKF(w,ob){if(!cur)return;var a=els.slice();a[sel]=Object.assign({},a[sel],kv(w,Object.assign({},a[sel][w]||{},ob)));setEls(a)}`
Replace with:
```
function patchAK(ob){if(!cur)return;var i=akClamped();var kfs=curKfs().map(function(k){return Object.assign({},k)});kfs[i]=Object.assign({},kfs[i],ob);var a=els.slice();var ne=Object.assign({},a[sel],{keyframes:kfs});delete ne.from;delete ne.to;a[sel]=ne;setEls(a)}
```

- [ ] **Step 4: Repoint the numeric keyframe fields, the preview, and the easing dropdown to the active keyframe.**
  4a. Anchor (Phase-1 `numField`): `function numField(label,w,key){return r.jsx(O,{label:label,children:r.jsx(le,{mono:!0,value:String((cur[w]&&cur[w][key]!=null)?cur[w][key]:0),onChange:function(v){patchKF(w,kv(key,Number(v)||0))}})})}`
  Replace with: `function numField(label,key){var k=curKfs()[akClamped()]||{};return r.jsx(O,{label:label,children:r.jsx(le,{mono:!0,value:String(k[key]!=null?k[key]:0),onChange:function(v){patchAK(kv(key,Number(v)||0))}})})}`
  4b. Anchor (Phase-1 `kfRow`): `function kfRow(w){return r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6},children:[numField("x %",w,"x"),numField("y %",w,"y"),numField("scale",w,"scale"),numField("rotation",w,"rotation"),numField("opacity",w,"opacity")]})}`
  Replace with: `function kfRow(){return r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6},children:[numField("x %","x"),numField("y %","y"),numField("scale","scale"),numField("rotation","rotation"),numField("opacity","opacity")]})}`
  4c. Anchor (Phase-1 preview transform read): `var tr=cur[mode]||{x:50,y:50,scale:1,rotation:0,opacity:1};` → Replace: `var tr=curKfs()[akClamped()]||{x:50,y:50,scale:1,rotation:0,opacity:1};`
  4d. Anchor (Phase-1 startDrag transform read): `var tr=cur[mode]||{};` → Replace: `var tr=curKfs()[akClamped()]||{};`
  4e. Anchor (Phase-1 `onMove` move-branch): `patchKF(mode,{x:round1(clamp01((ev.clientX-d.box.left)/d.box.width*100)),y:round1(clamp01((ev.clientY-d.box.top)/d.box.height*100))})` → Replace `patchKF(mode,` with `patchAK(` (drop the `mode,`). Apply the same `patchKF(mode,` → `patchAK(` replacement to the scale-branch and rot-branch in `onMove` (3 occurrences total — patch each by its surrounding unique text; use `replace` count==3 only if the literal `patchKF(mode,{` is identical, else patch the three distinct full expressions).
  4f. Anchor (Phase-1 easing dropdown — element-level): `r.jsx(O,{label:"Easing",children:r.jsx(re,{value:cur.easing||"linear",options:EAS.map(function(k){return{value:k,label:k}}),onChange:function(v){patch({easing:v})}})})`
  Replace with: `r.jsx(O,{label:"Easing (to next)",children:r.jsx(re,{value:(curKfs()[akClamped()]||{}).easing||"linear",options:EAS.map(function(k){return{value:k,label:k}}),onChange:function(v){patchAK({easing:v})}})})`
  4g. Anchor (Phase-1 easing list): `var EAS=["linear","easeIn","easeOut","easeInOut","easeOutBack","easeOutBounce"];`
  Replace with: `var EAS=["linear","easeIn","easeOut","easeInOut","easeOutBack","easeOutBounce","smooth","easeInOutSine","anticipate","overshoot"];`

- [ ] **Step 5: Repoint the Start⟷End toggle to prev/next active keyframe.** Anchor (Phase-1 toggle buttons block — the two buttons with `setMode("from")`/`setMode("to")`). Replace the two `r.jsx("button",...children:"◀ Start"})` and `...children:"End ▶"})` so they read:
```
r.jsx("button",{onClick:function(){setAk(Math.max(0,akClamped()-1))},style:{flex:1,fontSize:11,padding:"4px 0",borderRadius:6,cursor:"pointer",background:"var(--surface-2)",color:"var(--ink)",border:"1px solid var(--stroke)"},children:"◀ Prev kf"}),r.jsx("button",{onClick:function(){setAk(Math.min(curKfs().length-1,akClamped()+1))},style:{flex:1,fontSize:11,padding:"4px 0",borderRadius:6,cursor:"pointer",background:"var(--surface-2)",color:"var(--ink)",border:"1px solid var(--stroke)"},children:"Next kf ▶"})
```
Also replace the two editor calls `kfRow("from")` → `kfRow()` and `kfRow("to")` → remove the second keyframe block (the editor now shows ONE active keyframe). Anchor (Phase-1 editor keyframe section): the substring `r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",margin:"8px 0 2px"},children:"Start keyframe"}),kfRow("from"),r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",margin:"8px 0 2px"},children:"End keyframe"}),kfRow("to")`
Replace with: `r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",margin:"8px 0 2px"},children:"Keyframe "+(akClamped()+1)+" / "+curKfs().length}),kfRow()`

- [ ] **Step 6:** `node --check`; deploy; browser-test: add an Animation node + Text element; confirm the inspector shows "Keyframe 1 / 2", Prev/Next kf cycles the active keyframe, numeric fields + drag edit the active keyframe, the easing dropdown lists the bézier presets, and editing an element that started as legacy (load a Phase-1 saved graph) upgrades to keyframes without visual change. No console errors.

- [ ] **Step 7: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "feat(studio): DzAnimation keyframe model + per-keyframe easing (legacy back-compat)"
```

---

## Task 4: Frontend — timeline strip of draggable keyframe dots (bundle)

**Files:** Modify `index-BEOJX8L5.js` (extend `DzAnimation`).

- [ ] **Step 1: Add timeline helpers** (insert before `function previewBox(){`):
```
function addKf(){if(!cur)return;var kfs=curKfs().map(function(k){return Object.assign({},k)});var i=akClamped();var a=kfs[i],b=kfs[Math.min(kfs.length-1,i+1)];var nt=(a.t+b.t)/2;if(b===a)nt=Math.min(1,a.t+.1);var nk=Object.assign({},a,{t:nt});kfs.push(nk);kfs.sort(function(p,q){return p.t-q.t});var arr=els.slice();var ne=Object.assign({},arr[sel],{keyframes:kfs});delete ne.from;delete ne.to;arr[sel]=ne;setEls(arr);setAk(kfs.map(function(k){return k.t}).indexOf(nt))}
function delKf(){if(!cur)return;var kfs=curKfs();if(kfs.length<=2)return;var i=akClamped();var nk=kfs.slice(0,i).concat(kfs.slice(i+1));var arr=els.slice();arr[sel]=Object.assign({},arr[sel],{keyframes:nk});setEls(arr);setAk(Math.max(0,i-1))}
function moveKfT(i,nt){var kfs=curKfs().map(function(k){return Object.assign({},k)});var lo=i>0?kfs[i-1].t+.01:0,hi=i<kfs.length-1?kfs[i+1].t-.01:1;nt=Math.max(lo,Math.min(hi,nt));kfs[i]=Object.assign({},kfs[i],{t:Math.round(nt*1000)/1000});var arr=els.slice();var ne=Object.assign({},arr[sel],{keyframes:kfs});delete ne.from;delete ne.to;arr[sel]=ne;setEls(arr)}
function timelineStrip(){if(!cur)return null;var kfs=curKfs();return r.jsxs("div",{style:{marginBottom:8},children:[r.jsx("div",{ref:tlRef,onPointerMove:onTlMove,onPointerUp:onTlUp,style:{position:"relative",height:26,borderRadius:6,background:"var(--surface-2)",border:"1px solid var(--stroke)",touchAction:"none"},children:kfs.map(function(k,i){return r.jsx("div",{onPointerDown:function(ev){startTlDrag(ev,i)},onClick:function(){setAk(i)},title:"keyframe "+(i+1),style:{position:"absolute",left:(k.t*100)+"%",top:"50%",width:12,height:12,marginLeft:-6,marginTop:-6,borderRadius:"50%",background:i===akClamped()?"var(--amber)":"var(--cyan)",border:"1px solid #02060d",cursor:"grab"}},i)})}),r.jsxs("div",{style:{display:"flex",gap:6,marginTop:6},children:[r.jsx("button",{onClick:addKf,style:{flex:1,fontSize:11,padding:"4px 0",borderRadius:6,cursor:"pointer",background:"var(--surface-2)",border:"1px solid var(--stroke)",color:"var(--ink)"},children:"+ Keyframe"}),r.jsx("button",{onClick:delKf,disabled:kfs.length<=2,style:{flex:1,fontSize:11,padding:"4px 0",borderRadius:6,cursor:kfs.length<=2?"not-allowed":"pointer",background:"var(--surface-2)",border:"1px solid var(--stroke)",color:kfs.length<=2?"var(--ink-soft)":"var(--red)"},children:"− Keyframe"})]})]})}
```

- [ ] **Step 2: Add timeline drag refs + handlers.** Anchor (the active-keyframe state line added in Task 3): `var akS=x.useState(0),ak=akS[0],setAk=akS[1];` → append:
```
var tlRef=x.useRef(null),tlDrag=x.useRef(null);
```
Then insert before `function timelineStrip(){`:
```
function startTlDrag(ev,i){ev.stopPropagation();setAk(i);var box=tlRef.current.getBoundingClientRect();tlDrag.current={i:i,box:box};try{tlRef.current.setPointerCapture(ev.pointerId)}catch(e6){}}
function onTlMove(ev){var d=tlDrag.current;if(!d)return;moveKfT(d.i,(ev.clientX-d.box.left)/d.box.width)}
function onTlUp(ev){if(tlDrag.current){try{tlRef.current.releasePointerCapture(ev.pointerId)}catch(e7){}}tlDrag.current=null}
```

- [ ] **Step 3: Render the timeline above the preview.** Anchor (Phase-1 previewBox return wrapper): `return r.jsxs("div",{children:[r.jsxs("div",{style:{display:"flex",gap:6,marginBottom:6},children:[r.jsx("button",{onClick:function(){setAk(Math.max(0,akClamped()-1))}` (the Prev/Next row from Task 3, now the first child of previewBox).
Replace the leading `return r.jsxs("div",{children:[` of `previewBox` with `return r.jsxs("div",{children:[timelineStrip(),`.

- [ ] **Step 4:** `node --check`; deploy; browser-test: timeline shows a dot per keyframe; clicking a dot selects it (turns amber, editor follows); dragging a dot horizontally changes its time (re-render shows the dot move); **+ Keyframe** inserts a dot at the midpoint and selects it; **− Keyframe** removes it (disabled at 2). No console errors.

- [ ] **Step 5: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "feat(studio): multi-keyframe timeline strip (drag dots, add/remove keyframes)"
```

---

## Task 5: Frontend — scrub + play preview (bundle)

**Files:** Modify `index-BEOJX8L5.js` (extend `DzAnimation`).

- [ ] **Step 1: Add scrub state + a client-side sampler.** Anchor (timeline refs line from Task 4): `var tlRef=x.useRef(null),tlDrag=x.useRef(null);` → append:
```
var pvS=x.useState(0),pvT=pvS[0],setPvT=pvS[1];var playRef=x.useRef(null);
function sampleAt(el,u){var kfs=dzKfs(el);if(u>=1){return kfs[kfs.length-1]}var i=0;while(i<kfs.length-2&&u>kfs[i+1].t)i++;var a=kfs[i],b=kfs[i+1],span=Math.max(1e-9,b.t-a.t),e=dzEase(a.easing||"linear",(u-a.t)/span);return {x:a.x+(b.x-a.x)*e,y:a.y+(b.y-a.y)*e,scale:a.scale+(b.scale-a.scale)*e,rotation:a.rotation+(b.rotation-a.rotation)*e,opacity:a.opacity+(b.opacity-a.opacity)*e}}
function dzEase(n,t){t=t<0?0:t>1?1:t;if(n==="easeIn")return t*t;if(n==="easeOut")return 1-(1-t)*(1-t);if(n==="easeInOut")return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;if(n==="easeOutBack"){var c1=1.70158,c3=c1+1;return 1+c3*Math.pow(t-1,3)+c1*Math.pow(t-1,2)}return t}
function play(){if(playRef.current){cancelAnimationFrame(playRef.current);playRef.current=null;return}var t0=null;var step=function(ts){if(t0==null)t0=ts;var el=els[sel];var dur=(el&&el.dur)||.8;var u=((ts-t0)/1000)/dur;if(u>=1){setPvT(0);playRef.current=null;return}setPvT(u);playRef.current=requestAnimationFrame(step)};playRef.current=requestAnimationFrame(step)}
```
*(Note: `dzEase` is an approximate client-side preview — it covers the named easings; bézier presets fall back to linear in the preview only. The backend render is authoritative.)*

- [ ] **Step 2: Use the scrub transform when scrubbing/playing.** In `previewBox`, anchor: `var tr=curKfs()[akClamped()]||{x:50,y:50,scale:1,rotation:0,opacity:1};`
Replace with: `var scrubbing=pvT>0||playRef.current;var tr=scrubbing&&cur?sampleAt(cur,pvT):(curKfs()[akClamped()]||{x:50,y:50,scale:1,rotation:0,opacity:1});`

- [ ] **Step 3: Render the scrub slider + Play button** (inside `timelineStrip`, append after the +/− Keyframe row — anchor the closing of that row `children:"− Keyframe"})]})]})}` and insert before the final `]})}`):
Replace `children:"− Keyframe"})]})]})}` with:
```
children:"− Keyframe"})]}),r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center",marginTop:6},children:[r.jsx("button",{onClick:play,style:{fontSize:11,padding:"4px 8px",borderRadius:6,cursor:"pointer",background:"var(--surface-2)",border:"1px solid var(--stroke)",color:"var(--ink)"},children:"▶ Play"}),r.jsx("input",{type:"range",min:0,max:1,step:.01,value:pvT,onChange:function(ev){setPvT(Number(ev.target.value))},style:{flex:1}})]})]})}
```

- [ ] **Step 4:** `node --check`; deploy; browser-test: dragging the scrub slider moves the element along its keyframe path (interpolated, not snapped to a keyframe); **▶ Play** animates it 0→dur once and resets; numeric fields still edit the active keyframe when not scrubbing. No console errors.

- [ ] **Step 5: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "feat(studio): Animation scrub + play preview"
```

---

## Task 6: Frontend — favorites store `keyframes[]` (bundle)

**Files:** Modify `index-BEOJX8L5.js` (extend `DzAnimation`).

- [ ] **Step 1: Save the keyframe list in element/preset favorites.** Anchor (Phase-1 `saveFav`): the element branch `ff.elements=ff.elements.concat([{name:name,type:cur.type,text:cur.text,filename:cur.filename,style:cur.style,from:cur.from,to:cur.to,dur:cur.dur,hold:cur.hold,easing:cur.easing}])`
Replace with: `ff.elements=ff.elements.concat([{name:name,type:cur.type,text:cur.text,filename:cur.filename,style:cur.style,keyframes:curKfs(),dur:cur.dur,hold:cur.hold}])`
And the preset branch `ff.presets=ff.presets.concat([{name:name,from:Object.assign({},cur.from),to:Object.assign({},cur.to),easing:cur.easing,dur:cur.dur,hold:cur.hold}])`
Replace with: `ff.presets=ff.presets.concat([{name:name,keyframes:curKfs(),dur:cur.dur,hold:cur.hold}])`

- [ ] **Step 2: Apply keyframe favorites on insert/preset.** Anchor (Phase-1 `insertFavEl` defaults block): the run `ne.from=fe.from||{x:50,y:50,scale:1,rotation:0,opacity:0};ne.to=fe.to||{x:50,y:50,scale:1,rotation:0,opacity:1};ne.start=0;ne.dur=fe.dur!=null?fe.dur:.8;ne.hold=fe.hold!=null?fe.hold:2;ne.easing=fe.easing||"linear";ne.preset=null;`
Replace with: `ne.keyframes=fe.keyframes||dzKfs(fe);delete ne.from;delete ne.to;ne.start=0;ne.dur=fe.dur!=null?fe.dur:.8;ne.hold=fe.hold!=null?fe.hold:2;ne.preset=null;`
And anchor (Phase-1 `applyFavPreset`): `function applyFavPreset(p){if(!cur)return;var a=els.slice();a[sel]=Object.assign({},a[sel],{from:Object.assign({},p.from),to:Object.assign({},p.to),easing:p.easing||a[sel].easing,dur:p.dur!=null?p.dur:a[sel].dur,hold:p.hold!=null?p.hold:a[sel].hold});setEls(a)}`
Replace with: `function applyFavPreset(p){if(!cur)return;var a=els.slice();var ne=Object.assign({},a[sel],{keyframes:p.keyframes||dzKfs(p),dur:p.dur!=null?p.dur:a[sel].dur,hold:p.hold!=null?p.hold:a[sel].hold});delete ne.from;delete ne.to;a[sel]=ne;setEls(a)}`

- [ ] **Step 3:** `node --check`; deploy; browser-test: create a 3-keyframe element, save it as an element favorite and its motion as a preset; reload; insert the element favorite (all 3 keyframes restored) and apply the preset to a different element (its keyframes/timing copied). A Phase-1 favorite (with `from`/`to`) still inserts correctly via `dzKfs`. No console errors.

- [ ] **Step 4: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "feat(studio): Animation favorites carry keyframes[] (legacy back-compat)"
```

---

## Task 7: End-to-end verification + deploy

**Files:** none (verification).

- [ ] **Step 1:** Confirm bundle + backend are deployed to `%LOCALAPPDATA%\DeepotusVideoGen`; backend restarted.
- [ ] **Step 2: Backward-compat regression.** In a browser, open a saved Phase-1 graph that contains an Animation node (or recreate a 2-keyframe element), Run it, and confirm the rendered clip is **identical** to its Phase-1 output (legacy `from`/`to` path through `kfs_of`). Also `& $py -m pytest backend/tests/test_animation_service.py -v` → all green.
- [ ] **Step 3: New multi-keyframe E2E.** Build `Upload(video) → Animation → Render` with a Text element having **3 keyframes** (e.g. off-screen → overshoot to centre-large → settle), a `smooth` segment, and a sticker. Run. Extract a frame mid-second-segment and confirm via Pillow that the text/sticker are at the interpolated position (not at a keyframe), and the base shows through (corner ≠ solid `#02060d`).
- [ ] **Step 4: Timeline/scrub/favorites smoke.** Add/drag/delete keyframes on the timeline; scrub + Play; save & re-insert a keyframe favorite. No console errors throughout.
- [ ] **Step 5: Commit** any final tweaks. (Installer rebuild remains a separate, user-triggered step.)

---

## Self-Review

**Spec coverage:** keyframes[] model + normalized `t` + per-segment easing (T2, T3) ✓; backward-compat via `kfs_of`/`dzKfs` (T2, T3, T6) ✓; cubic-bézier presets + `cubic-bezier(...)` (T1, T3 dropdown) ✓; backend multi-keyframe sampling with legacy regression test (T2) ✓; timeline strip with draggable dots + add/remove (T4) ✓; scrub + play approximate preview (T5) ✓; favorites carry keyframes (T6) ✓; compile/route/render untouched (no task needed — verified in T7) ✓; non-goals (drag-handle curve editor, per-property tracks) correctly absent.

**Placeholder scan:** Backend steps carry complete code. Frontend steps give exact anchors (the Phase-1 injected strings, known verbatim) + exact replacement code; the only judgement note is the 3 `patchKF(mode,` → `patchAK(` occurrences in `onMove` (Step 4e) — patch each by its distinct surrounding expression. No `TODO`/`TBD`.

**Type consistency:** keyframe shape `{t,x,y,scale,rotation,opacity,easing?}` identical across backend `kfs_of`/`transform_at`, frontend `dzKfs`/`mk`/`sampleAt`, and favorites. `patchAK(ob)` (single-arg) replaces `patchKF(w,ob)` everywhere its callers were updated (numField, kfRow, onMove, easing). `curKfs()`/`akClamped()` used consistently. Backend `ease()` accepts named + `_BEZIER` keys + `cubic-bezier(...)`; the frontend dropdown only emits those names.

**Risks restated:** the `DzAnimation` refactor from `mode` (from/to) to `ak` (keyframe index) touches several Phase-1 anchors (T3) — each is an exact unique string; run `node --check` + browser-test after T3 before stacking T4–T6. Backend legacy regression is locked by `test_transform_at_legacy_unchanged`.
