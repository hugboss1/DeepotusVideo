# HeyGen Quick picker + avatar/voice casting presets — design

Date: 2026-07-03
Status: approved (design), pending implementation plan
Scope tag: A + B + E (of a larger 4-part HeyGen wishlist — C and D deferred)

## 1. Problem / context

The user generates HeyGen avatar videos from the **Quick (1-shot)** page
(`nav id "quick"`, "1-shot generators"). Three concrete pains, all verified
against the current code (bundle `frontend/dist/assets/index-BEOJX8L5.js`, byte
-identical to the installed app, md5 `e146bcdd…`) and the live HeyGen account:

- **A — a specific voice is unreachable.** The voice **" xdynoMoney - Voice 1"**
  (note the leading space in its HeyGen name) exists in the account
  (`voice_id: Z32YLIMiuw7UvRLEbHqF`, English/male, has `preview_audio`) but sits
  at **index 1074 of 2329** in HeyGen's `/v2/voices` order. The Quick page voice
  selector renders `Y.slice(0,200)` — the first 200 voices only — with **no
  search**. So the voice is literally absent from the dropdown.
- **B — no avatar preview on Quick.** The Quick "Avatar" block already has an
  avatar **search** box but renders only a plain dropdown; there is **no preview
  image** of the chosen avatar. (The rich picker with a 9:16 preview + a ▶
  voice-preview button, `DzAvatarPick`, exists **only** in the Studio node
  inspector — not on Quick. This is why the user sees "lists load but no
  preview".)
- **E — no reusable avatar+voice "casting".** Choosing an avatar and a voice is
  re-done every time. The user wants to **save an avatar+voice pair under a name**
  (with a unique id), then reuse it in one click in **Quick and Studio** — e.g.
  save a "News Reel" casting, later pick it in Studio and only change the script.

Backend data is already sufficient: `GET /api/heygen/voices` returns
`voice_id, name, language, gender, preview_audio`; `GET /api/heygen/avatars`
returns `avatar_id, name, gender, avatar_type, preview_image_url`. Generation via
`POST /api/generate/heygen` works. Nothing about the *data* is broken — the gaps
are UI (A, B) and a missing persistence feature (E).

### Out of scope (explicitly)
- **C** — choosing HeyGen avatar model III/IV/V at generation. Separate slice.
- **D** — creating + animating new avatars "like on the HeyGen site". Separate
  project, needs HeyGen-API capability exploration first.
- Voice **favorites** (localStorage ★): dropped — presets cover reuse; search
  covers discovery. Keeps the patch smaller.
- Preset **rename**: YAGNI for v1 (delete + re-save). No PUT endpoint.
- Backend "surface my custom voices first": dropped — the `voice-design`
  marker matches 309 voices (not reliably the user's own), so it is not a clean
  signal. Search + presets solve the real need.

## 2. Goals / success criteria

On the **Quick** page, the user can:
1. Type "xdyno" in a voice search box and find " xdynoMoney - Voice 1".
2. Press ▶ next to the voice and hear its sample.
3. See a preview image of the selected avatar.
4. Press "💾 Save casting", give it a name → it is stored in the DB.

In **Studio** (HeyGenAvatar node), the user can pick that saved casting from a
"Casting" dropdown → the node's avatar + voice (+ speed) are filled in one
selection; only the script remains to edit.

Presets **survive a PC migration** (they live in `deepotus.db`, which the
export/import kit copies).

## 3. Backend design (`DeepotusVideo/backend/app`, editable Python)

### 3.1 New ORM model — `services/storage.py`
Add a table mirroring the existing `JobRecord`/`ScheduledPost` style. It is
auto-created on startup by `init_db()` → `Base.metadata.create_all` (create_all
adds new tables without touching existing ones; no manual migration needed).

```
class AvatarPreset(Base):
    __tablename__ = "avatar_presets"
    id: str  (uuid4, primary key, String(36))
    name: str  (String(120))
    avatar_id: str  (String(120))
    avatar_type: str  (String(20), default "avatar")   # "avatar" | "talking_photo"
    avatar_img: Optional[str]  (String(1000))          # preview_image_url snapshot
    voice_id: str  (String(120))
    voice_name: Optional[str]  (String(200))
    voice_prev: Optional[str]  (Text)                  # preview_audio URL snapshot
    voice_lang: Optional[str]  (String(40))
    speed: float  (Float, default 1.0)
    created_at: datetime  (default utcnow)
```
Note: `avatar_img`/`voice_prev` are cached HeyGen preview URLs. They are
signed/expiring URLs, so the UI must tolerate a stale/blank preview (fall back to
re-fetch from the live avatar/voice list by id when showing). The id fields
(`avatar_id`, `voice_id`) are the durable source of truth for generation.

### 3.2 Endpoints — `api/routes.py`
- `GET /api/heygen/presets` → `{ "presets": [ {id,name,avatar_id,avatar_type,
  avatar_img,voice_id,voice_name,voice_prev,voice_lang,speed,created_at}, … ] }`,
  newest first.
- `POST /api/heygen/presets` body `{name, avatar_id, avatar_type?, avatar_img?,
  voice_id, voice_name?, voice_prev?, voice_lang?, speed?}` → creates with a
  generated uuid, returns the full preset. Validation: `name`, `avatar_id`,
  `voice_id` required and non-empty.
- `DELETE /api/heygen/presets/{id}` → `{ "ok": true }` (404 if missing).

No auth (consistent with the rest of the local API). Uses
`async_session_factory` like the other routes. A Pydantic request model
(`AvatarPresetCreate`) goes in `models/schemas.py`.

## 4. Frontend design (patch of `frontend/dist/assets/index-BEOJX8L5.js`)

The frontend has **no source** — changes are targeted string patches to the
minified bundle (see the project's `frontend-compiled-only` playbook). Relevant
minified identifiers already located:

- Quick "Avatar" block (~offset 361.6k): section `ie` label `` `Avatar (${U.length})` ``.
  - `U` = avatars array, `C` = selected avatar_id, `Q` = avatar onChange,
    `S` = avatar search text, `L` = its setter.
  - `Y` = voices array, `ee` = selected voice_id, `ne` = voice onChange.
  - UI primitives: `ie` section, `O` field, `re` select, `le` input, `K` button.
  - Current voice field: `re({value:ee, options:Y.slice(0,200).map(...), onChange:ne})`.
- Studio picker `function DzAvatarPick({p,set})` (~offset 444k): loads
  `D.listHeygenAvatars()`/`D.listHeygenVoices()`, sets node props
  `avatar/avatarId/avatarImg/avatarType` and `voice/voiceId/voicePrev/voiceLang`,
  has `playVoice()` (`new Audio(p.voicePrev).play()`).
- API helper object `D` (has `listHeygenAvatars`, `listHeygenVoices`, `postJson`,
  and a `Ge(path,fallback)` fetch wrapper). Add `D.listPresets()`,
  `D.savePreset(body)`, `D.deletePreset(id)` (or call `D.postJson`/`Ge` inline).

### 4.1 Quick page — "Avatar" block changes
1. **B: avatar preview** — below the "Avatar" `re`, render a small 9:16 `<img>`
   (~120px tall) from `U.find(a=>a.avatar_id===C)?.preview_image_url`, with the
   `onLoad`→show / `onError`→hide guard (avoids the known "stays hidden after a
   later valid src" bug). Placeholder text when nothing selected.
2. **A: voice search** — add an `O({label:"Search voices", children: le({icon:"search",
   value:<vq>, onChange:<setVq>, placeholder:`Search ${Y.length} voices…`})})`
   above the voice `re`. Introduce a search state (React `x.useState`).
3. **A: voice list fix** — replace `Y.slice(0,200)` with
   `Y.filter(byQuery).slice(0,200)` so search reaches beyond the first 200. Query
   matches `name` (trim leading space) + `language` + `voice_id`,
   case-insensitive.
4. **A: ▶ voice preview** — next to the voice `re`, a `K({variant:"outline",
   size:"sm", icon:"play", onClick:playSel})` shown when the selected voice has
   `preview_audio`; `playSel` does `new Audio(sel.preview_audio).play().catch(()=>{})`.
5. **E: Casting dropdown + Save** — at the top of the block:
   - a `re` "Casting" whose options come from `GET /presets` (label = name);
     selecting one sets `C` (avatar) and `ee` (voice) via `Q`/`ne` (and applies
     `speed` if the Quick form exposes it).
   - a real **name input field** (`le`, an `O({label:"Casting name"})`) in the
     form + a `K` "💾 Save casting" button: on click, `POST /presets` with the
     typed name and the current avatar+voice (+ their cached name/img/prev/lang),
     then clear the field and refresh the casting list. The button is disabled
     when the name field is empty or no avatar/voice is selected. (No
     `window.prompt`.) A small "✕" to delete the currently-selected preset
     (`DELETE /presets/{id}`) may be included next to the Casting dropdown.

### 4.2 Studio `DzAvatarPick` changes (E only)
- Add a "Casting" `re` at the top of the "Avatar" section: options from
  `GET /presets`; on select, apply the preset to the node props:
  `set("avatarId", preset.avatar_id); set("avatarType", preset.avatar_type);
   set("avatarImg", preset.avatar_img||"");` plus resolve `avatar` display name
  from the loaded list if available; and
  `set("voiceId", preset.voice_id); set("voice", preset.voice_name||"");
   set("voicePrev", preset.voice_prev||""); set("voiceLang", preset.voice_lang||"");`
  and `set("speedX", preset.speed||1)`.
- No Save button in Studio (per decision — save happens in Quick).

### 4.3 Patch safety procedure
1. `cp` the bundle to a timestamped backup.
2. Apply each change with a Python script that asserts the anchor string occurs
   **exactly once** before replacing (fail loud otherwise).
3. Copy the patched bundle to a `.mjs` and run `node --check` (it is an ES
   module; Node is installed) — must pass.
4. Deploy: the repo `frontend/dist` is the source of record; the installed app at
   `%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist` is a copy. For live testing,
   copy the patched bundle into the install dir, restart the backend/app.
5. Reload and verify via the DOM (screenshots time out under load).

## 5. Testing plan

Backend (live — HeyGen key present in `%LOCALAPPDATA%\DeepotusVideoGenData\.env`):
- Start backend on :8765. `GET /api/heygen/presets` → empty list, table created.
- `POST` a preset → returns id; `GET` shows it; `DELETE` removes it.
- Confirm `avatar_presets` table exists in `deepotus.db`.

Frontend (installed app):
- Quick → "Search voices" `xdyno` → " xdynoMoney - Voice 1" appears → ▶ plays.
- Select an avatar → preview image shows.
- 💾 Save casting "News Reel" → appears in the Casting dropdown.
- Studio → HeyGenAvatar node → Casting → "News Reel" → node avatar+voice filled;
  change the script → generate → job succeeds.

## 6. Risks & rollback
- **Minified patch fragility** — mitigated by single-occurrence asserts +
  `node --check` + bundle backup. Rollback = restore the backup bundle.
- **Expiring preview URLs** — `avatar_img`/`voice_prev` snapshots may 404 later;
  UI falls back to id-based lookup / blank preview. Generation is unaffected
  (uses ids).
- **DB write on a shared file** — presets use the same session factory/engine as
  the rest of the app; low risk. New table only, no ALTER on existing tables.
- **`.env`/DB reload gotcha** — backend reads settings at boot; after adding the
  table, a running backend already has `create_all` applied on its own startup,
  so restart the backend once after deploying the new code.

## 7. Deliverable
Backend code + a single patched bundle, committed to `main` of
`hugboss1/DeepotusVideo` (schannel + Windows Credential Manager auth already
configured). Mirror the patched bundle into the install dir for the user to test.
