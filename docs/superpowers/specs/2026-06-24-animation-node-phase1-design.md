# Animation Node — Phase 1 Design (Foundation)

> **Context:** Part of a 3-phase motion system for Studio overlays.
> - **Phase 1 (this spec):** the `Animation` node + a 2-keyframe (start→end) model + the render engine + a Favorites library.
> - **Phase 2:** multi-keyframe visual timeline editor + bézier easing curves.
> - **Phase 3:** preset/sticker library, element sequencing/transitions, advanced text effects (typewriter, per-character).
>
> This spec covers **Phase 1 only**. The data model is designed to extend to Phases 2–3 without rework.

**Goal:** A new `Animation` Studio node that superimposes animated **text / sticker / image** elements over a base render/image. Each element has explicit **start → end** position, scale (size), rotation and opacity, plus timing + easing, and is rendered to a video. A **Favorites library** lets the user quickly reuse configured elements, text-styles, and animation presets.

**Tech stack:** compiled React bundle (count-guarded string patches, `node --check`, deploy to repo + `%LOCALAPPDATA%\DeepotusVideoGen`), backend FastAPI with a new `animation_service.py` (Pillow per-frame compositor + ffmpeg), reusing the bundled design fonts + the emoji Pillow path from `template_service.py`.

---

## 1. Architecture

A new node **`Animation`** in a **new palette family `motion`** (its own **"Animations"** section in the node palette, separate from `compose`). *Implementation note:* the palette groups nodes by their `cat`; add `motion` to the category list/order so the new section renders.
- **Input port `base`** (`type:"av"`) — the render/clip (or image, via the existing image→av connect rule) to animate over. If nothing is connected, the engine uses a solid/transparent canvas at the render aspect.
- **Output port `out`** (`type:"av"`) — the composited animated video; connects to `Render` / `SpatialCompose` like any clip.
- **Pipeline position:** `Seedance/Render/Image → Animation → Render`. It is a compositor node, not part of SpatialCompose (keeps SpatialCompose focused on static layout; motion lives in its own node).

**Compile/run integration:** the Studio Run compiler (`Mh`/`dzCompose`) detects an `Animation` node feeding the render and emits an **animation job** via `POST /api/animate` with `{ base_source, aspect, fps, duration_s, elements[] }`. The job returns a `job_id`; the produced clip is consumed downstream exactly like a Seedance/HeyGen clip (so the existing Job Dock, Library, and "reopen in Studio" all work unchanged). `base_source` is resolved with the **same `srcFor()` resolver** dzCompose already uses (Seedance/Upload/Image/ExistingRender/NewsIllustration), so any clip can be the base.

---

## 2. Data model

Node props:

```js
Animation: {
  cat: "motion", title: "Animation", desc: "animate text & stickers over a clip",
  inPorts: [{ id: "base", type: "av" }],
  outPorts: [{ id: "out", type: "av" }],
  props: {
    durationS: 8,            // total composition length (defaults from the base if connected)
    fps: 30,
    elements: []             // see Element below; selected via props.selected (index)
  }
}
```

Element shape (one per "layer"):

```js
{
  id: "el_xxxx",
  type: "text" | "sticker" | "image",
  // content
  text: "DEEPOTUS",                       // type:text
  filename: "gen_ab12cd.png",             // type:sticker|image (uploaded/generated)
  // text style ("typo")
  style: { font: "JetBrains Mono", size: 64, color: "#00e5ff", stroke: 0, strokeColor:"#000",
           shadow: 0, align: "center", bg: null },
  // transform keyframes — x,y in % of canvas (0..100), scale multiplier, rotation deg, opacity 0..1
  from: { x: 50, y: 60, scale: 0.6, rotation: 0, opacity: 0 },
  to:   { x: 50, y: 40, scale: 1.0, rotation: 0, opacity: 1 },
  // timing (seconds)
  start: 0.0, dur: 0.8, hold: 2.0,
  easing: "easeOutBack",                  // linear|easeIn|easeOut|easeInOut|easeOutBack|easeOutBounce
  preset: null                            // optional: name of an animation preset applied to from/to
}
```

- `x`/`y` are **percent of canvas** so they survive aspect changes. `scale` is a multiplier of the element's natural size. After `start+dur` the element **holds** at `to` for `hold` seconds, then disappears (unless `hold` covers the rest of the duration).
- This 2-keyframe shape (`from`/`to`) is the degenerate case of the Phase-2 `keyframes[]` array, so Phase 2 migrates `from`/`to` → `keyframes:[{t:0,...from}, {t:1,...to}]` cleanly.

---

## 3. Inspector UI (Phase 1, pre-timeline)

Rendered in the Studio inspector (`Yh`) when `e.type==="Animation"`, as a new `DzAnimation({node, graph, set})` component:

- **Element list** — chips/rows for each element (icon by type + a label); buttons **+ Text / + Sticker / + Image**; select, reorder (↑/↓), delete.
- **Selected-element editor:**
  - **Content:** text field (text) or an image picker reusing `DzImageModel` + upload (sticker/image).
  - **Typo:** font picker (the bundled font list), size, color (the color-disc), stroke, shadow, align.
  - **Animation:** a **preset** dropdown (fade-in, slide-in ←/→/↑/↓, pop, zoom-in, ken-burns) that fills `from`/`to`; **easing** dropdown; **timing** fields (`start`, `dur`, `hold`).
  - **Transform:** numeric `from`/`to` for x/y/scale/rotation/opacity (kept in sync with the visual editor).
- **Visual positioning canvas** — a preview box at the render aspect showing the base thumbnail + the element; a **`Start ⟷ End`** toggle; **drag** the element to set that keyframe's x/y, **corner handles** for scale, a **top handle** for rotation. Far better than typing x/y.
- **Scrub + Play** — a slider + play button that runs an **approximate client-side preview** (CSS transform of the element over the base thumbnail). This is a preview only; the authoritative output is the backend render.

---

## 4. Favorites library (added per user request)

A library of reusable building blocks the user accumulates, so frequently-used **elements**, **text-styles ("typos")**, and **animation presets** are one click away. Frontend-only, persisted in **`localStorage` key `dz_anim_favorites`** (JSON), mirroring the avatar-favorites pattern (`dz_fav_avatars`).

```js
dz_anim_favorites = {
  elements: [ { name, type, text?, filename?, style, from, to, dur, hold, easing } ],
  typos:    [ { name, style } ],                 // font/size/color/stroke/shadow/align only
  presets:  [ { name, from, to, easing, dur, hold } ]   // motion only, content-agnostic
}
```

UI in the Animation inspector:
- A **"★ Save"** split-button on the selected element → **Save as element / Save as typo / Save as animation preset** (prompts for a name).
- A **"Favorites" panel** (collapsible) with three groups (Elements / Typos / Presets), each a row of chips. Click a chip to **insert** (element → adds a copy to `elements[]`) or **apply** (typo → applies the style to the selected/new text element; preset → applies the motion to the selected element). Each chip has an `×` to remove.
- No backend; survives restarts via localStorage. (Phase 3 may promote this to a backend-synced library; out of scope here.)

---

## 5. Backend render engine

New module **`backend/app/services/animation_service.py`** + route **`POST /api/animate`**.

**Payload:** `{ base: <slot-source or null>, aspect, fps, duration_s, elements:[...] }` (the compiled node).

**Algorithm — per-frame Pillow compositor over an ffmpeg-streamed base:**
1. Resolve the base to a clip (reuse the slot resolver). Probe its dimensions/fps; fall back to the render aspect + a solid `#02060d` canvas if no base.
2. Stream base frames **rawvideo (RGBA) via an ffmpeg pipe** (frame-by-frame, low memory). For "no base", synthesize blank frames.
3. For each frame at time `t`: for each element (in order), compute the eased transform —
   `u = clamp((t - start)/dur, 0, 1); e = ease(easing, u); v = lerp(from, to, e)` (hold `to` after `start+dur`; not drawn before `start` or after `start+dur+hold`) — and **draw it with Pillow**: render text (reuse the design-font + emoji code from `template_service.py`) or load the sticker/image; apply `scale` (resize), `rotation` (`Image.rotate`), `opacity` (alpha), and paste at `(x%·W, y%·H)` centered.
4. Pipe composited RGBA frames into an ffmpeg encoder (H.264, the render's fps/aspect); **copy the base's audio** if present.
5. Save under `outputs/` + register a `JobRecord` (so Library/Dock/cost work). Save the source graph for "reopen in Studio".

**Easing functions** (Python, in the service): `linear, easeIn (t²), easeOut (1-(1-t)²), easeInOut, easeOutBack, easeOutBounce` — pure functions of `t∈[0,1]`.

**Why per-frame Python (not a pure ffmpeg filtergraph):** full control of **scale + rotation + eased curves + (Phase 3) per-character text effects**, and it reuses the existing Pillow text/emoji/font rendering. Trade-off: slower than ffmpeg-only (one decode+composite+encode pass) — acceptable for reel lengths (≤ ~15 s @ 30 fps ≈ ≤450 frames). A pure-ffmpeg fast-path (overlay with time expressions, for position+opacity-only elements) is a possible later optimization, noted as out of scope.

**Pricing:** add an `animate` op to `pricing.py` (compute-only, no external API) so the cost pill stays honest.

---

## 6. Scope / non-goals (Phase 1)

- **2 keyframes per element** (`from`/`to` + `hold`) — not multi-keyframe (Phase 2).
- **Preset easings + ~6 animation presets** — not a bézier curve editor (Phase 2).
- **Sticker = uploaded/generated image** — not a built-in sticker library (Phase 3).
- **Whole-element styling animated as one** — not per-character/typewriter (Phase 3).
- **Sequencing via per-element `start`** — not explicit A→B element transitions (Phase 3).
- The scrub preview is **approximate** (client-side CSS); the backend render is authoritative.

---

## 7. Risks / open questions

- **Compile integration** is the trickiest part: routing an `Animation` node through Run → `/api/animate` and feeding its output downstream. Mitigation: model it on the existing layout-render compile path (it already mints a job + saves the source graph).
- **Render performance:** per-frame Python on 1080×1920. Mitigation: frame-by-frame streaming (no full-video in memory), bounded by `duration_s`; show it in the cost/ETA. If too slow, add the ffmpeg fast-path for position/opacity-only elements.
- **Rotation + alpha quality** in Pillow (resampling) — use `Image.rotate(expand=True, resample=BICUBIC)` and premultiplied alpha to avoid fringing.
- **Visual drag-positioning** in the compiled bundle is the biggest frontend lift — it's a self-contained draggable-over-thumbnail widget. Confirmed **in Phase 1 scope** (design review); build order *within* the phase: numeric `from`/`to` fields first, then the drag/handles layer on the preview canvas.
