# HeyGen Quick picker + casting presets — Implementation Plan

> **NOTE (audit de couture du 2026-08-21)** : plan d'origine, jamais
> resynchronisé — 4 extraits python divergent du code livré (mesure au
> repatriement v2.1.0, commit 7b80e17 : routes presets et scripts de bundle).
> En cas d'écart, le code livré fait foi.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the Quick page, add an avatar preview image, a searchable voice picker with a ▶ sample button, and a named avatar+voice "casting" preset (stored in the DB) that is also selectable from the Studio HeyGen node.

**Architecture:** Backend adds one SQLAlchemy table (`avatar_presets`) auto-created by `init_db()` plus three CRUD routes under `/api/heygen/presets`. Frontend is a **minified-bundle patch** (`frontend/dist/assets/index-BEOJX8L5.js`, no source) applied with single-occurrence-asserted Python replacements, validated with `node --check`.

**Tech Stack:** FastAPI + SQLAlchemy async + aiosqlite (Python), React compiled bundle (patched as text), httpx for tests, Node 22 for `node --check`.

---

## Environment (facts for every task)

- **Repo (edit + commit here):** `C:\Users\olivi\DeepotusVideo`, branch `feat/heygen-quick-picker-casting-presets` (already created; spec committed as `765fead`).
- **Python with deps (tests + local run):** `C:\Users\olivi\AppData\Local\DeepotusVideoGen\runtime\python\python.exe` (call it `$PY`). The system `python` (3.14) lacks the deps — do NOT use it.
- **Live app (for manual verification):** installed at `C:\Users\olivi\AppData\Local\DeepotusVideoGen`. Its backend dir and bundle are separate copies of the repo. After backend changes, mirror the edited `.py` files into `…\DeepotusVideoGen\backend\app\…` and restart the backend; after a bundle patch, copy the patched bundle into `…\DeepotusVideoGen\frontend\dist\assets\`.
- **HeyGen key** is present in `…\DeepotusVideoGenData\.env`, so live `/api/heygen/*` calls work.
- **Bundle path:** `frontend/dist/assets/index-BEOJX8L5.js` (~592 KB, one line, ES module).
- Run any bash command below from the repo root unless stated. `$PY` denotes the embedded python path above.

---

## File structure

- `backend/app/services/storage.py` — **modify**: add `AvatarPreset` ORM model (new table, no ALTER).
- `backend/app/models/schemas.py` — **modify**: add `AvatarPresetCreate` request model.
- `backend/app/api/routes.py` — **modify**: add `GET/POST/DELETE /heygen/presets`.
- `backend/tests/test_presets.py` — **create**: self-contained async API test (no pytest needed).
- `frontend/dist/assets/index-BEOJX8L5.js` — **modify** (patched): Quick avatar preview, voice search + ▶, casting dropdown + save; Studio node casting dropdown.
- `scripts/patch_bundle_presets.py` — **create**: the idempotent, assert-guarded bundle patcher (kept in-repo so the patch is reproducible and reviewable).

---

## PHASE 1 — Backend (presets API)

### Task 1: Failing API test

**Files:**
- Create: `backend/tests/test_presets.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_presets.py
"""Self-contained async test for the avatar-preset API.
Run: <embedded python> backend/tests/test_presets.py
Uses an isolated temp SQLite DB (DATABASE_URL env override) so it never
touches the real deepotus.db. Exits non-zero on failure."""
import asyncio, os, sys, tempfile, pathlib

# Isolate the DB BEFORE importing the app (engine is built at import time).
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport   # noqa: E402
from app.main import app                        # noqa: E402
from app.services.storage import init_db        # noqa: E402


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # empty
        r = await c.get("/api/heygen/presets")
        assert r.status_code == 200, r.text
        assert r.json()["presets"] == [], r.text

        # create
        body = {"name": "News Reel", "avatar_id": "av123",
                "avatar_type": "avatar", "avatar_img": "http://img/a.png",
                "voice_id": "Z32YLIMiuw7UvRLEbHqF",
                "voice_name": " xdynoMoney - Voice 1", "voice_prev": "http://a/p.mp3",
                "voice_lang": "English", "speed": 1.0}
        r = await c.post("/api/heygen/presets", json=body)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert pid and r.json()["name"] == "News Reel"

        # list has it
        r = await c.get("/api/heygen/presets")
        got = r.json()["presets"]
        assert len(got) == 1 and got[0]["id"] == pid
        assert got[0]["voice_id"] == "Z32YLIMiuw7UvRLEbHqF"

        # validation: missing avatar_id -> 422
        r = await c.post("/api/heygen/presets", json={"name": "x", "voice_id": "v"})
        assert r.status_code == 422, r.text

        # delete
        r = await c.delete(f"/api/heygen/presets/{pid}")
        assert r.status_code == 200 and r.json()["ok"] is True
        r = await c.get("/api/heygen/presets")
        assert r.json()["presets"] == []

        # delete missing -> 404
        r = await c.delete("/api/heygen/presets/nope")
        assert r.status_code == 404
    print("PRESETS TEST: PASS")

asyncio.run(main())
```

- [ ] **Step 2: Run it — expect FAIL**

Run:
```bash
PY="C:/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"
cd "C:/Users/olivi/DeepotusVideo" && "$PY" backend/tests/test_presets.py
```
Expected: an assertion or 404/405 failure on `GET /api/heygen/presets` (route absent). Non-zero exit.

- [ ] **Step 3: Commit the test**

```bash
cd "C:/Users/olivi/DeepotusVideo"
git add backend/tests/test_presets.py
git commit -m "test: failing API test for avatar-preset CRUD"
```

### Task 2: `AvatarPreset` ORM model

**Files:**
- Modify: `backend/app/services/storage.py` (add class after `ScheduledPost`, before the `_engine = …` line at ~line 91)

- [ ] **Step 1: Add the imports needed** — ensure `Float` is imported. The current import line is:
```python
from sqlalchemy import String, Integer, DateTime, Text, text
```
Replace it with:
```python
from sqlalchemy import String, Integer, Float, DateTime, Text, text
```

- [ ] **Step 2: Add the model** (insert immediately before `_engine = create_async_engine(`):

```python
class AvatarPreset(Base):
    """v1.16 — a saved avatar+voice 'casting' reusable across Quick and Studio.
    Stored in deepotus.db so it migrates with the export/import kit. The *_id
    fields are the durable source of truth; the cached preview URLs
    (avatar_img/voice_prev) are HeyGen signed URLs that may expire — the UI
    tolerates a blank/stale preview and re-resolves by id from the live list."""
    __tablename__ = "avatar_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    avatar_id: Mapped[str] = mapped_column(String(120))
    avatar_type: Mapped[str] = mapped_column(String(20), default="avatar")
    avatar_img: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    voice_id: Mapped[str] = mapped_column(String(120))
    voice_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    voice_prev: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_lang: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

No migration needed: `init_db()` runs `Base.metadata.create_all`, which creates new tables without altering existing ones.

- [ ] **Step 3: Sanity import check**

Run:
```bash
PY="C:/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"
cd "C:/Users/olivi/DeepotusVideo/backend" && DATABASE_URL="sqlite+aiosqlite:///./_probe.db" "$PY" -c "import sys;sys.path.insert(0,'.');from app.services.storage import AvatarPreset,Base;print('avatar_presets' in Base.metadata.tables)"
rm -f "C:/Users/olivi/DeepotusVideo/backend/_probe.db"
```
Expected: `True`.

### Task 3: `AvatarPresetCreate` request schema

**Files:**
- Modify: `backend/app/models/schemas.py` (append near the other request models, e.g. after `GenerateHeyGenRequest`)

- [ ] **Step 1: Add the model**

```python
class AvatarPresetCreate(BaseModel):
    """Create an avatar+voice casting preset."""
    name: str = Field(..., min_length=1, max_length=120)
    avatar_id: str = Field(..., min_length=1)
    avatar_type: Literal["avatar", "talking_photo"] = "avatar"
    avatar_img: Optional[str] = None
    voice_id: str = Field(..., min_length=1)
    voice_name: Optional[str] = None
    voice_prev: Optional[str] = None
    voice_lang: Optional[str] = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
```

Confirm `Field`, `Optional`, `Literal`, `BaseModel` are already imported in this file (they are — used by `GenerateHeyGenRequest`). If not, add them.

### Task 4: The three routes

**Files:**
- Modify: `backend/app/api/routes.py` (insert after the `list_heygen_voices` route, ~line 1361; import `AvatarPresetCreate` wherever request models are imported)

- [ ] **Step 1: Ensure the schema is imported.** Find the schemas import block near the top of `routes.py` and add `AvatarPresetCreate` to it (same import that brings in `GenerateHeyGenRequest`).

- [ ] **Step 2: Add the routes** (after the voices route):

```python
@router.get("/heygen/presets")
async def list_avatar_presets():
    """List saved avatar+voice casting presets (newest first)."""
    from app.services.storage import AvatarPreset, async_session_factory
    from sqlalchemy import select
    async with async_session_factory() as session:
        rows = (await session.execute(
            select(AvatarPreset).order_by(AvatarPreset.created_at.desc())
        )).scalars().all()
    return {"presets": [{
        "id": p.id, "name": p.name,
        "avatar_id": p.avatar_id, "avatar_type": p.avatar_type,
        "avatar_img": p.avatar_img,
        "voice_id": p.voice_id, "voice_name": p.voice_name,
        "voice_prev": p.voice_prev, "voice_lang": p.voice_lang,
        "speed": p.speed,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    } for p in rows]}


@router.post("/heygen/presets")
async def create_avatar_preset(body: AvatarPresetCreate):
    """Save an avatar+voice casting preset."""
    from app.services.storage import AvatarPreset, async_session_factory
    from uuid import uuid4
    pid = str(uuid4())
    async with async_session_factory() as session:
        session.add(AvatarPreset(
            id=pid, name=body.name.strip(),
            avatar_id=body.avatar_id, avatar_type=body.avatar_type,
            avatar_img=body.avatar_img,
            voice_id=body.voice_id, voice_name=body.voice_name,
            voice_prev=body.voice_prev, voice_lang=body.voice_lang,
            speed=body.speed,
        ))
        await session.commit()
    return {"id": pid, "name": body.name.strip(),
            "avatar_id": body.avatar_id, "avatar_type": body.avatar_type,
            "avatar_img": body.avatar_img,
            "voice_id": body.voice_id, "voice_name": body.voice_name,
            "voice_prev": body.voice_prev, "voice_lang": body.voice_lang,
            "speed": body.speed}


@router.delete("/heygen/presets/{preset_id}")
async def delete_avatar_preset(preset_id: str):
    """Delete a casting preset by id."""
    from app.services.storage import AvatarPreset, async_session_factory
    async with async_session_factory() as session:
        row = await session.get(AvatarPreset, preset_id)
        if not row:
            raise HTTPException(404, "Preset not found")
        await session.delete(row)
        await session.commit()
    return {"ok": True}
```

`HTTPException` and `router` are already imported/defined in this file.

- [ ] **Step 3: Run the API test — expect PASS**

Run:
```bash
PY="C:/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"
cd "C:/Users/olivi/DeepotusVideo" && "$PY" backend/tests/test_presets.py
```
Expected: `PRESETS TEST: PASS`, exit 0.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/olivi/DeepotusVideo"
git add backend/app/services/storage.py backend/app/models/schemas.py backend/app/api/routes.py
git commit -m "feat(backend): avatar+voice casting presets — model + /api/heygen/presets CRUD"
```

---

## PHASE 2 — Frontend bundle patch

All frontend changes go through **one reviewable patch script** that asserts each
anchor occurs exactly once. This makes the minified edit reproducible and safe to
re-run. Anchors below are copied verbatim from the current bundle.

### Task 5: The patch script (backup + Quick avatar preview [B])

**Files:**
- Create: `scripts/patch_bundle_presets.py`
- Modify (via script): `frontend/dist/assets/index-BEOJX8L5.js`

- [ ] **Step 1: Write the patcher with the first (avatar-preview) patch**

```python
# scripts/patch_bundle_presets.py
"""Idempotent, assert-guarded patcher for the HeyGen Quick/Studio picker.
Run: python scripts/patch_bundle_presets.py
Creates a .bak once, applies each patch, verifies each anchor occurs exactly
once. Safe to abort: it writes the file only after ALL patches succeed."""
import pathlib, shutil, sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")

def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)

def main():
    s = BUNDLE.read_text(encoding="utf-8")
    bak = BUNDLE.with_suffix(".js.bak")
    if not bak.exists():
        shutil.copy2(BUNDLE, bak)
        print("backup ->", bak)

    # ---- PATCH B: Quick avatar preview image after the "Avatar" select ----
    # Anchor: the Quick avatar dropdown field (renders the <select> for C).
    anchor_b = 'r.jsx(O,{label:"Avatar",children:r.jsx(re,{value:C,options:U.filter(B=>{const Z=S.trim().toLowerCase();return Z?`${B.name||""} ${B.avatar_id||""} ${B.avatar_type||""}`.toLowerCase().includes(Z):!0}).slice(0,200).map(B=>({value:B.avatar_id,label:`${B._kind==="talking_photo"?"📷 ":""}${B.name||B.avatar_id} ${B.gender?`· ${B.gender}`:""}`})),onChange:Q})})'
    preview_b = anchor_b + ',(()=>{const _a=U.find(B=>B.avatar_id===C);const _u=_a&&_a.preview_image_url;return r.jsx("div",{style:{marginTop:4,aspectRatio:"9 / 16",maxHeight:200,background:"#02060d",border:"1px solid var(--stroke)",borderRadius:8,overflow:"hidden",display:"flex",alignItems:"center",justifyContent:"center"},children:_u?r.jsx("img",{src:_u,alt:"avatar",onLoad:e=>{e.currentTarget.style.opacity=1},onError:e=>{e.currentTarget.style.opacity=0},style:{width:"100%",height:"100%",objectFit:"cover"}}):r.jsx("span",{style:{fontSize:10.5,color:"var(--ink-soft)",padding:8,textAlign:"center"},children:"Pick an avatar to preview"})})})()'
    s = apply(s, anchor_b, preview_b, "B-avatar-preview")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the patcher**

Run:
```bash
cd "C:/Users/olivi/DeepotusVideo" && python scripts/patch_bundle_presets.py
```
Expected: `backup -> …index-BEOJX8L5.js.bak` then `patched OK`. If it prints `anchor count=0`, the bundle differs — STOP and re-locate the anchor before continuing.

- [ ] **Step 3: Validate the bundle parses**

Run:
```bash
cd "C:/Users/olivi/DeepotusVideo/frontend/dist/assets"
cp index-BEOJX8L5.js _check.mjs && node --check _check.mjs && echo "NODE CHECK OK" && rm _check.mjs
```
Expected: `NODE CHECK OK`.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/olivi/DeepotusVideo"
git add scripts/patch_bundle_presets.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m "feat(quick): avatar preview image in the HeyGen picker [B]"
```

### Task 6: Quick voice search + ▶ sample + new state [A]

**Files:**
- Modify: `scripts/patch_bundle_presets.py`, `frontend/dist/assets/index-BEOJX8L5.js`

**Verified facts (from the current bundle, Quick component `um({variant:e,activePersona:t})`):**
- State is declared as destructured pairs. The avatar-search pair is `[S,L]=x.useState("")`, immediately followed by `,[J,de]=x.useState(!1)`. The last state pair before the first effect is `,[Ce,at]=x.useState(null);`.
- `re` (select) and `le` (input) both call `onChange(value)` with the **raw value** (not an event) — so setters like `Q`/`ne`/`L` are passed directly as `onChange`. New setters `Vq`/`Pn` therefore take the raw value.
- Avatars = `U`, voices = `Y`, selected avatar id = `C` (setter `Q`), selected voice id = `ee` (setter `ne`), avatar search text = `S`.

- [ ] **Step 1: Make the patcher re-runnable from the clean backup.** In `main()`, replace the read/backup block so re-runs are deterministic. Final `main()` head becomes:

```python
def main():
    bak = BUNDLE.with_suffix(".js.bak")
    if not bak.exists():
        shutil.copy2(BUNDLE, bak); print("backup ->", bak)
    else:
        shutil.copy2(bak, BUNDLE)  # restore clean base so all patches compose
    s = BUNDLE.read_text(encoding="utf-8")
```

- [ ] **Step 2: Add the new React state hooks (voice search `vq` + presets `pr`,`pn`).** Insert right after the avatar-search pair — exact anchor:

```python
    # ---- PATCH STATE: voice-search (vq) + preset (pr,pn) hooks in Quick (um) ----
    anchor_state = '[S,L]=x.useState(""),[J,de]=x.useState(!1)'
    add_state = '[S,L]=x.useState(""),[vq,Vq]=x.useState(""),[pr,Pr]=x.useState([]),[pn,Pn]=x.useState(""),[J,de]=x.useState(!1)'
    s = apply(s, anchor_state, add_state, "STATE-quick-hooks")
```

- [ ] **Step 3: Load presets once on mount.** Append a fetch effect right after the last state pair:

```python
    # ---- PATCH LOADER: fetch presets on mount into pr ----
    anchor_load = ',[Ce,at]=x.useState(null);'
    add_load = ',[Ce,at]=x.useState(null);x.useEffect(()=>{let on=!0;fetch("/api/heygen/presets").then(R=>R.ok?R.json():{presets:[]}).then(d=>{if(on)Pr((d&&d.presets)||[])}).catch(()=>{});return()=>{on=!1}},[]);'
    s = apply(s, anchor_load, add_load, "LOADER-quick-presets")
```

- [ ] **Step 4: Add the "Search voices" field** after "Search avatars":

```python
    # ---- PATCH A1: "Search voices" field ----
    anchor_a1 = 'r.jsx(O,{label:"Search avatars",children:r.jsx(le,{icon:"search",value:S,onChange:L,placeholder:`Search ${U.length} avatars…`})}),'
    add_a1 = anchor_a1 + 'r.jsx(O,{label:"Search voices",children:r.jsx(le,{icon:"search",value:vq,onChange:Vq,placeholder:`Search ${Y.length} voices…`})}),'
    s = apply(s, anchor_a1, add_a1, "A1-voice-search-field")
```

- [ ] **Step 5: Fix the voice dropdown to filter by `vq` (removes the 200-cap block) + add ▶.** Exact anchor:

```python
    # ---- PATCH A3: voice dropdown filtered by vq + ▶ preview ----
    anchor_a3 = 'r.jsx(O,{label:"Voice",children:r.jsx(re,{value:ee,options:Y.slice(0,200).map(B=>({value:B.voice_id,label:`${B.name||B.voice_id} ${B.language?`· ${B.language}`:""}`})),onChange:ne})})'
    add_a3 = 'r.jsx(O,{label:"Voice",children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:[r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:ee,options:Y.filter(B=>{const Z=(vq||"").trim().toLowerCase();return Z?`${B.name||""} ${B.language||""} ${B.voice_id||""}`.toLowerCase().includes(Z):!0}).slice(0,200).map(B=>({value:B.voice_id,label:`${(B.name||B.voice_id).trim()} ${B.language?`· ${B.language}`:""}`})),onChange:ne})}),(()=>{const _v=Y.find(B=>B.voice_id===ee);const _u=_v&&_v.preview_audio;return _u?r.jsx(K,{variant:"outline",size:"sm",icon:"play",title:"Preview voice",onClick:()=>{try{new Audio(_u).play().catch(()=>{})}catch(e){}}}):null})()]})})'
    s = apply(s, anchor_a3, add_a3, "A3-voice-filter-preview")
```

- [ ] **Step 6: Run patcher + `node --check`**

Run:
```bash
cd "C:/Users/olivi/DeepotusVideo" && python scripts/patch_bundle_presets.py
cd frontend/dist/assets && cp index-BEOJX8L5.js _check.mjs && node --check _check.mjs && echo "NODE CHECK OK" && rm _check.mjs
```
Expected: `patched OK` then `NODE CHECK OK`.

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/olivi/DeepotusVideo"
git add scripts/patch_bundle_presets.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m "feat(quick): searchable voices + ▶ sample + preset state [A]"
```

### Task 7: Quick casting dropdown + Save [E]

**Files:**
- Modify: `scripts/patch_bundle_presets.py`, `frontend/dist/assets/index-BEOJX8L5.js`

- [ ] **Step 1: (state already added in Task 6.)** `pr`/`Pr` (presets array), `pn`/`Pn` (casting-name input) and the once-on-mount preset loader were added in Task 6 Steps 2–3. Nothing to add here — proceed to the UI patch.

- [ ] **Step 2: Add the Casting UI** at the TOP of the `Avatar (${U.length})` section, right after the hidden file input. `le`/`re` pass the **raw value** to `onChange` (verified in Task 6), so the name field clears with `Pn("")`. Exact anchor:

```python
    # ---- PATCH E1 (Quick): casting dropdown + name field + Save/Delete ----
    anchor_e1 = 'r.jsx("input",{ref:et,type:"file",accept:"image/png,image/jpeg,image/webp",style:{display:"none"},onChange:B=>{var Z;dn((Z=B.target.files)==null?void 0:Z[0]),B.target.value=""}}),'
    cast_e1 = anchor_e1 + 'r.jsx(O,{label:`Casting (${pr.length})`,children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:[r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:"",options:[{value:"",label:pr.length?"— load a casting —":"— no casting saved —"},...pr.map(P=>({value:P.id,label:P.name}))],onChange:v=>{const P=pr.find(z=>z.id===v);if(P){Q(P.avatar_id);ne(P.voice_id)}}})}),r.jsx(K,{variant:"ghost",size:"sm",icon:"trash",title:"Delete first casting",disabled:!pr.length,onClick:()=>{const P=pr[0];if(P)fetch("/api/heygen/presets/"+P.id,{method:"DELETE"}).then(()=>fetch("/api/heygen/presets").then(R=>R.json()).then(d=>Pr((d&&d.presets)||[])))}})]})}),r.jsx(O,{label:"Save current as casting",children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:[r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(le,{value:pn,onChange:Pn,placeholder:"Casting name (e.g. News Reel)"})}),r.jsx(K,{variant:"outline",size:"sm",icon:"save",title:"Save casting",disabled:!pn.trim()||!C||!ee,onClick:()=>{const _a=U.find(z=>z.avatar_id===C)||{};const _v=Y.find(z=>z.voice_id===ee)||{};fetch("/api/heygen/presets",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:pn.trim(),avatar_id:C,avatar_type:_a.avatar_type||"avatar",avatar_img:_a.preview_image_url||"",voice_id:ee,voice_name:(_v.name||"").trim(),voice_prev:_v.preview_audio||"",voice_lang:_v.language||"",speed:1})}).then(R=>R.ok?R.json():null).then(()=>{Pn("");return fetch("/api/heygen/presets").then(R=>R.json()).then(d=>Pr((d&&d.presets)||[]))})}})]})}),'
    s = apply(s, anchor_e1, cast_e1, "E1-quick-casting")
```
`Q`/`ne` accept the raw id value (matching `re`'s onChange contract). The trash button deletes the most-recent preset (`pr[0]`, list is newest-first) — a full per-row manage UI is out of scope for v1.

- [ ] **Step 3: Run patcher + `node --check`** (same commands as Task 6 Step 6). Expected `NODE CHECK OK`.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/olivi/DeepotusVideo"
git add scripts/patch_bundle_presets.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m "feat(quick): save + load avatar/voice casting presets [E]"
```

### Task 8: Studio node casting dropdown [E]

**Files:**
- Modify: `scripts/patch_bundle_presets.py`, `frontend/dist/assets/index-BEOJX8L5.js`

- [ ] **Step 1: Load presets inside `DzAvatarPick`.** The component already has `x.useEffect(()=>{…listHeygenAvatars…listHeygenVoices…},[])`. Add a presets state + a fetch in that same effect. Anchor on the effect's avatar/voice loader inside `DzAvatarPick`:

```python
    # ---- PATCH E2a (Studio): load presets in DzAvatarPick ----
    anchor_e2a = 'const[list,setList]=x.useState(null),[voices,setVoices]=x.useState(null);'
    add_e2a = 'const[list,setList]=x.useState(null),[voices,setVoices]=x.useState(null),[presets,setPresets]=x.useState([]);x.useEffect(()=>{let on=!0;fetch("/api/heygen/presets").then(R=>R.ok?R.json():{presets:[]}).then(d=>{if(on)setPresets((d&&d.presets)||[])}).catch(()=>{});return()=>{on=!1}},[]);'
    s = apply(s, anchor_e2a, add_e2a, "E2a-studio-presets-load")
```

- [ ] **Step 2: Add the Casting `re` at the top of the node's Avatar section.** Anchor on the "Find avatar" field that opens the `DzAvatarPick` render:

```python
    # ---- PATCH E2b (Studio): casting dropdown wired to set() ----
    anchor_e2b = 'return r.jsxs(ie,{label:"Avatar",children:[r.jsx(O,{label:"Find avatar",'
    add_e2b = 'return r.jsxs(ie,{label:"Avatar",children:[r.jsx(O,{label:`Casting (${presets.length})`,children:r.jsx(re,{value:"",options:[{value:"",label:presets.length?"— load a casting —":"— no casting saved —"},...presets.map(P=>({value:P.id,label:P.name}))],onChange:v=>{const P=presets.find(z=>z.id===v);if(!P)return;set("avatarId",P.avatar_id);set("avatarType",P.avatar_type||"avatar");set("avatarImg",P.avatar_img||"");const _a=(list||[]).find(z=>z.avatar_id===P.avatar_id);if(_a)set("avatar",_a.avatar_name);set("voiceId",P.voice_id);set("voice",P.voice_name||"");set("voicePrev",P.voice_prev||"");set("voiceLang",P.voice_lang||"");set("speedX",P.speed||1)}})}),r.jsx(O,{label:"Find avatar",'
    s = apply(s, anchor_e2b, add_e2b, "E2b-studio-casting")
```

- [ ] **Step 3: Run patcher + `node --check`** (same as before). Expected `NODE CHECK OK`.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/olivi/DeepotusVideo"
git add scripts/patch_bundle_presets.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m "feat(studio): load avatar/voice casting presets on the HeyGen node [E]"
```

---

## PHASE 3 — Live verification & finish

### Task 9: Deploy to the installed app and verify end-to-end

**Files:** none (runtime verification)

- [ ] **Step 1: Mirror backend + bundle into the installed app**

```bash
SRC="C:/Users/olivi/DeepotusVideo"; DST="C:/Users/olivi/AppData/Local/DeepotusVideoGen"
cp "$SRC/backend/app/services/storage.py" "$DST/backend/app/services/storage.py"
cp "$SRC/backend/app/models/schemas.py"  "$DST/backend/app/models/schemas.py"
cp "$SRC/backend/app/api/routes.py"      "$DST/backend/app/api/routes.py"
cp "$SRC/frontend/dist/assets/index-BEOJX8L5.js" "$DST/frontend/dist/assets/index-BEOJX8L5.js"
echo "mirrored"
```

- [ ] **Step 2: Restart the backend** (kill the process holding :8765, then relaunch the app). The Settings/DB are a boot-time snapshot, so a restart is required for the new table + routes. Launch via `…\DeepotusVideoGen\scripts\launch-silent.vbs` (or the desktop shortcut).

- [ ] **Step 3: Live API smoke test against the running app**

```bash
PY="C:/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"
"$PY" - <<'PY'
import urllib.request,json
b="http://127.0.0.1:8765/api/heygen/presets"
print("GET", json.load(urllib.request.urlopen(b))["presets"])
PY
```
Expected: `GET []` (or existing presets). Confirms the route is live.

- [ ] **Step 4: Manual UI checks** (in the running app):
  - Quick → HeyGen mode → type `xdyno` in **Search voices** → " xdynoMoney - Voice 1" appears → press ▶ → sample plays.
  - Select an avatar → the **preview image** shows.
  - Type "News Reel" in the casting-name field → **💾 Save** → it appears in the **Casting** dropdown.
  - Studio → add/select a **HeyGenAvatar** node → **Casting** dropdown → "News Reel" → node's avatar + voice fill in.
  - Verify the DOM via the browser `javascript_tool` (screenshots time out under load).

- [ ] **Step 5: Confirm persistence** — the preset row exists in the DB:

```bash
PY="C:/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"
"$PY" - <<'PY'
import sqlite3,os
db=os.path.join(os.environ["LOCALAPPDATA"],"DeepotusVideoGenData","deepotus.db")
c=sqlite3.connect(db);print("presets:",c.execute("select name,voice_id from avatar_presets").fetchall())
PY
```
Expected: your "News Reel" row with `Z32YLIMiuw7UvRLEbHqF`.

### Task 10: Finish the branch

- [ ] **Step 1: Re-run the backend test once more** (regression):
```bash
PY="C:/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"
cd "C:/Users/olivi/DeepotusVideo" && "$PY" backend/tests/test_presets.py
```
Expected: `PRESETS TEST: PASS`.

- [ ] **Step 2: Push the branch and open a PR** (only after the user confirms the live checks look good):
```bash
cd "C:/Users/olivi/DeepotusVideo"
git push -u origin feat/heygen-quick-picker-casting-presets
```
Then use the finishing-a-development-branch skill to merge to `main` (schannel + Windows Credential Manager auth is configured).

---

## Notes / gotchas carried from project memory
- **Bundle patch fragility:** always single-occurrence assert + `node --check`; the `.bak` is the rollback. Keep the patcher in-repo so the edit is reproducible.
- **`<img onError=hide>` stale-visibility bug:** the avatar preview pairs `onError` (opacity 0) with `onLoad` (opacity 1) so a later valid src re-shows.
- **Expiring preview URLs:** `avatar_img`/`voice_prev` may 404 later; generation uses ids, so it is unaffected; the UI shows a blank/placeholder in that case.
- **Install dir reverts to repo:** uncommitted edits under `%LOCALAPPDATA%\DeepotusVideoGen` can be reset to the git state — the source of record is the repo; mirroring is only for live testing. Commit in the repo to persist.
- **Backend restart required** after backend changes: the process on :8765 holds a boot-time snapshot; kill + relaunch.
