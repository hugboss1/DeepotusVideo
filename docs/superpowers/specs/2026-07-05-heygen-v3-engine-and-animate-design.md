# HeyGen v3: engine choice (C) + create/animate avatars (D) — design

Date: 2026-07-05
Status: approved decisions (placement, defaults, scope) — C implemented first, D second
Refs: https://developers.heygen.com/reference/create-video · /reference/get-video · /endpoint-version-comparison

## Context — HeyGen API v3 (researched 2026-07-05)

- `POST /v3/videos` (same `x-api-key` auth) is a discriminated union:
  - `type:"avatar"` — avatar_id + (script+voice_id | audio_url | audio_asset_id);
    optional `engine: {type:"avatar_iii"|"avatar_iv"|"avatar_v"}` (default IV),
    `motion_prompt` (photo avatars), `expressiveness: high|medium|low` (IV),
    `resolution: 4k|1080p|720p`, `aspect_ratio: "9:16"|"16:9"|"1:1"|"4:5"|…`,
    `background {type:"color",value:"#hex"}`, `voice_settings{speed 0.5–1.5,…}`.
    avatar_v accepts optional `reference_look_id`. avatar_iii = digital-twin /
    photo-avatar looks only (no motion_prompt/expressiveness).
  - `type:"image"` — image via url | asset_id | **base64** + script/voice ⇒
    animate ANY image (library stills!) with motion_prompt/expressiveness.
  - `type:"cinematic_avatar"` — `prompt` (1–10k chars) + `avatar_id:[1–3 look ids]`
    + optional `references` (≤3 videos, ≤9 images), `duration 4–15s` or
    `auto_duration`, `enhance_prompt`. No script/voice.
- Poll `GET /v3/videos/{id}` → status pending|processing|completed|failed,
  `video_url` (presigned), thumbnail_url, duration.
- ⚠️ **v1/v2 endpoints sunset 2026-10-31.** The app is v2 everywhere; a full
  migration is a separate future task ([[heygen-v2-sunset]] to be created).

## Decisions (user-validated)

- **C placement:** engine selector in Quick AND the Studio HeyGen node, and the
  engine is stored in the casting preset (avatar+voice+engine in one pick).
- **C default:** **no engine selected ⇒ legacy v2 pipeline unchanged** (zero
  regression / cost surprise). Picking III/IV/V opts that generation into v3.
- **D scope:** (1) Image→animated-avatar: any Library image + motion prompt +
  expressiveness via v3 `type:"image"` (engine IV/V), savable as a casting;
  (2) **Cinematic mode**: `type:"cinematic_avatar"` prompt-driven, 1–3 looks,
  optional reference images, 4–15 s.

## C — engine choice (branch `feat/heygen-v3-engine-choice`)

### Backend
- `heygen_service.py`:
  - `generate_video_v3(script, avatar_id, voice_id, *, engine, aspect_ratio,
    speed, background_color, motion_prompt=None, expressiveness=None,
    title=None) -> video_id` — POST `/v3/videos` `type:"avatar"`; speed clamped
    to 0.5–1.5 (v3 limit); resolution "1080p"; background color mapped.
  - `poll_video_status_v3(video_id, poll_every_s=4, timeout_s=600) -> dict`
    (returns the v3 payload with `video_url`) mapping completed/failed.
- `schemas.GenerateHeyGenRequest` += `engine: Optional[Literal["avatar_iii",
  "avatar_iv","avatar_v"]] = None`, `motion_prompt: Optional[str] = None`,
  `expressiveness: Optional[Literal["high","medium","low"]] = None`.
- `pipeline.run_heygen`: `if request.engine:` → v3 generate+poll (download via
  the same `download_video`); else the untouched v2 path.
- `AvatarPreset` += `engine` (String(20), nullable). Existing DBs get it via
  the auto-migrate list: add `AVATAR_PRESETS_COLUMNS = [("engine","VARCHAR(20)")]`
  and `("avatar_presets", AVATAR_PRESETS_COLUMNS)` in `_auto_migrate`'s loop.
  Presets routes accept/return `engine`.
- Test `backend/tests/test_engine_v3.py`: schema accepts engine; presets CRUD
  round-trips engine; v3 request-body builder shape (no live HeyGen call).

### Frontend (patcher `scripts/patch_bundle_engine.py`)
- **Quick**: state `[eng,Eng]`; "Moteur" select under Voice:
  `["", "Auto (pipeline actuel)"] / avatar_iii "Avatar III" / avatar_iv
  "Avatar IV (motion)" / avatar_v "Avatar V (max)"`; POST `/generate/heygen`
  gains `engine: eng||void 0`. Casting save body += `engine: eng||""`;
  casting load applies `Eng(P.engine||"")` (+ feedback line mentions engine).
- **Studio node** (`DzAvatarPick`): "Moteur" select bound to node prop
  `engine` (`set("engine",v)`); casting load in the node sets it too.
- **Run compiler** (`Mh` HeyGen branch): body += `engine:(s.props&&s.props.engine)||void 0`.

## D — create + animate (branch `feat/heygen-animate-image`, after C merges)

### Backend
- `heygen_service.generate_image_video_v3(image_path, script, voice_id, *,
  engine="avatar_iv", motion_prompt, expressiveness, aspect_ratio, speed,
  background_color) -> video_id` — `type:"image"` with **base64** payload read
  from the Library file (no asset upload roundtrip).
- `heygen_service.generate_cinematic_v3(prompt, look_ids, *, reference_images,
  duration_s|auto, aspect_ratio, resolution) -> video_id` — `type:"cinematic_avatar"`;
  reference images as base64 from Library files.
- Routes `POST /generate/heygen-image` and `POST /generate/heygen-cinematic`
  (+ request models) → pipeline jobs (provider HEYGEN, normal job dock/Library flow).
- Casting presets can point at an image: reuse `avatar_presets` with
  `avatar_type:"image"` and `avatar_id = image filename` (avatar_img = its
  `/api/images/<f>` URL) so an animated character is one casting pick.
- Test: request-body builders (base64 read, cinematic refs), presets with
  avatar_type image.

### Frontend
- **Quick (HeyGen mode)** gains a "Source" mini-toggle: `Avatar` (existing) /
  `Image animée` / `Cinématique`:
  - *Image animée*: Library-image dropdown (reuses the existing image list `u`)
    + preview, `motion_prompt` textarea, `expressiveness` select, engine IV/V →
    POST `/generate/heygen-image`. "Save casting" stores avatar_type image.
  - *Cinématique*: prompt textarea (with char counter), 1–3 look ids picked
    from the avatar list, up to 3 reference images from the Library,
    duration slider 4–15 s or Auto → POST `/generate/heygen-cinematic`.
- **Studio**: the HeyGen node accepts `sourceKind:"image"` props (imageFilename,
  motionPrompt, expressiveness) — set by loading an image-casting; the run
  compiler routes to `/generate/heygen-image` when `sourceKind==="image"`.

## Risks
- v3 talking-photo ids under `type:"avatar"` are undocumented → keep talking
  photos on the v2 path even when an engine is picked (engine selector shows a
  hint); image-type covers the same need better anyway.
- Engine credit costs differ (V > IV) — the cost estimate endpoint keeps its
  heygen rate; a per-engine pricing refinement is out of scope.
- Presigned v3 video_url expiry unknown → download immediately in the pipeline
  (already the pattern).

## Future (noted, not in scope)
- Full v2→v3 migration before 2026-10-31 (listing, upload, translate, status).
- Per-engine cost estimates; avatar_v reference_look_id UI.
