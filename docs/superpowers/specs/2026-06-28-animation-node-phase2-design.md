# Animation Node — Phase 2 Design (Multi-keyframe timeline + bézier presets)

> **Context:** Part 2 of the 3-phase motion system for Studio overlays.
> - **Phase 1 (shipped):** the `Animation` node + a 2-keyframe (`from`/`to`) model + the render engine + a Favorites library. Commits `5db391e`..`c60b4e5` on `main`. Spec: `docs/superpowers/specs/2026-06-24-animation-node-phase1-design.md`.
> - **Phase 2 (this spec):** N-keyframe timeline editor + per-segment bézier-preset easing + a scrub/play preview, fully backward-compatible.
> - **Phase 3 (future):** preset/sticker library, element sequencing/transitions, advanced text effects (per-character/typewriter), per-property keyframe tracks.

**Goal:** Replace the fixed 2-keyframe (`from`/`to`) model with an **N-keyframe timeline** per element, add **per-segment cubic-bézier-preset easing**, and a **scrub/play preview** — without breaking any Phase 1 saved graph or favorite.

**Tech stack:** unchanged from Phase 1 — FastAPI + Pillow + ffmpeg (backend, pytest), compiled React bundle patched via count-guarded string replacements + `node --check` + deploy to repo & `%LOCALAPPDATA%\DeepotusVideoGen`. Bundle: `frontend/dist/assets/index-BEOJX8L5.js`.

---

## 1. Data model

Each element gains a `keyframes[]` array. The element timing window (`start`, `dur`, `hold`) is **unchanged**.

```js
{
  id, type, text?/filename?, style,            // unchanged from Phase 1
  start: 0.0, dur: 0.8, hold: 2.0,             // unchanged element timing window
  keyframes: [
    { t: 0.0, x, y, scale, rotation, opacity, easing: "easeOut" },  // easing = curve to the NEXT keyframe
    { t: 0.5, x, y, scale, rotation, opacity, easing: "overshoot" },
    { t: 1.0, x, y, scale, rotation, opacity }                       // last keyframe: easing ignored
  ],
  preset: null
}
```

- `t` = **normalized time 0..1** within the element's `dur` window (so keyframes survive a `dur` change). Keyframes are kept **sorted by `t`**; the first is normally `t:0`, the last `t:1`.
- Each keyframe is a **full transform snapshot** of the 5 props (`x`,`y` in % of canvas, `scale` multiplier, `rotation` deg, `opacity` 0..1). The 5 props move together — independent per-property tracks are Phase 3.
- A keyframe's `easing` describes the curve for the **segment from this keyframe to the next**. The last keyframe's `easing` is ignored.
- After the last keyframe (at `start+dur`), the element **holds** at the last keyframe's transform for `hold` seconds, then disappears (unchanged Phase 1 hold semantics).

**Backward compatibility (a hard requirement).** A normalizer resolves any element to a keyframe list:

```
kfsOf(el):
  if el.keyframes is a non-empty array: return el.keyframes (sorted by t)
  else: return [ {t:0, ...el.from, easing: el.easing||"linear"}, {t:1, ...el.to} ]
```

- Old graphs and favorites (which store `from`/`to`) render **identically** to Phase 1 via `kfsOf`.
- When an old element is **edited** in the new timeline, it is upgraded in place to `keyframes[]` (the synthesized 2-keyframe list becomes canonical; `from`/`to` are dropped).
- New elements are created directly with `keyframes:[{t:0,...},{t:1,...}]`.

---

## 2. Easing — named + bézier presets

The `easing` value on a keyframe is one of:
- a **named easing** from Phase 1: `linear | easeIn | easeOut | easeInOut | easeOutBack | easeOutBounce`, **or**
- a **cubic-bézier preset** name resolving to control points, e.g. `smooth (.4,0,.2,1)`, `anticipate`, `overshoot`, `easeInOutSine`, **or**
- a literal `cubic-bezier(a,b,c,d)` string.

Backend `ease(name, t)` gains a **cubic-bézier sampler**: given control points `(p1x,p1y,p2x,p2y)`, solve `x(s)=t` for `s` (Newton-Raphson with a bisection fallback, ~8 iterations) and return `y(s)`. A `_BEZIER` table maps preset names → control points; `cubic-bezier(...)` strings are parsed. Named Phase-1 easings keep their existing closed-form implementations. Unknown names fall back to `linear`.

**No drag-handle curve editor** (per scope decision) — presets only.

---

## 3. Backend render engine (`animation_service.py`, TDD)

- **`transform_at(el, t)` reworked** to sample N keyframes:
  1. `start`, `dur`, `hold` as today; `None` if `t < start` or `t > start + dur + hold`.
  2. `u = (t - start) / dur`. If `u >= 1`, hold at the **last** keyframe's transform.
  3. Otherwise find the bracketing segment `[kf_i, kf_{i+1}]` with `kf_i.t <= u <= kf_{i+1}.t`; `local = (u - kf_i.t) / (kf_{i+1}.t - kf_i.t)`; `e = ease(kf_i.easing, local)`; interpolate each of the 5 props between `kf_i` and `kf_{i+1}` with `lerp(...,e)`.
  4. Uses `kfsOf(el)` first, so a **legacy `from`/`to` element samples identically to Phase 1**.
- **`ease()`** gains the cubic-bézier sampler + preset table + `cubic-bezier(...)` parsing.
- `render_element` / `render_animation` are **unchanged** (they already consume whatever transform `transform_at` returns).
- **New pytest** (`test_animation_service.py`): multi-keyframe sampling at segment boundaries and mid-segment; a 3-keyframe element hitting each segment; cubic-bézier endpoints (`0→0`, `1→1`) + monotonic-ish interior; and a **regression test** that a legacy `from`/`to` element produces the same values as before.

---

## 4. Frontend — timeline + scrub/play (bundle, extends `DzAnimation`)

All additions live in the `DzAnimation` component (module-scoped in the bundle, next to the Phase-1 code).

- **Timeline strip** (per selected element): a horizontal track representing `0 → dur`, with a **draggable dot per keyframe** positioned at `kf.t`. Interactions:
  - click a dot → it becomes the **active keyframe**; the existing numeric `x/y/scale/rotation/opacity` fields and the drag-positioning preview now edit that keyframe.
  - drag a dot **horizontally** → change its `t` (clamped within neighbors; endpoints `t:0`/`t:1` may be pinned).
  - **+ Keyframe** → insert a keyframe at the current scrub head, snapshotting the **current interpolated transform** there (so adding a keyframe never jumps the motion).
  - **delete keyframe** (disabled when only 2 remain).
- The Phase-1 **Start⟷End toggle is generalized** into active-keyframe selection (the timeline dots replace the two buttons).
- **Scrub + Play:** a time slider drives a `previewT` (`useState`); the preview box renders the element interpolated at `previewT` via CSS transform. **Play** = a lightweight `requestAnimationFrame` loop looping `0 → dur` (and stop). This is an **approximate client-side preview**; the backend render stays authoritative.
- **Per-segment easing dropdown** gains the bézier presets and applies to the **active keyframe's outgoing segment** (`kf_i.easing`).
- **Backward-compat in the UI:** an element opened without `keyframes[]` is shown via `kfsOf` (2 dots); the first edit persists `keyframes[]` and drops `from`/`to`.

---

## 5. Compile / favorites — no structural change

- `Mh` (Run compiler), `srcFor`, and `POST /api/animate` are **untouched**: the Run payload still sends `elements`, now carrying `keyframes[]`; the backend handles both shapes via `kfsOf`.
- **Favorites** (`dz_anim_favorites`): reads resolve through `kfsOf`; new saves store `keyframes[]` (element + preset favorites carry the keyframe list / segment easings). Existing favorites keep working.

---

## 6. Scope / non-goals (Phase 2)

- **N keyframes per element**, each a full transform snapshot — not per-property tracks (Phase 3).
- **Cubic-bézier presets + `cubic-bezier(...)` strings** — not an interactive drag-handle curve editor (deferred).
- **Scrub + Play approximate preview** — backend render remains authoritative.
- No easing-curve graph visualization, no element-to-element transitions (Phase 3).
- Full **backward compatibility** is mandatory: every Phase 1 graph, favorite, and `/api/animate` payload must keep rendering unchanged.

---

## 7. Risks / open questions

- **Keyframe-`t` drag UX** in the compiled bundle (clamping, hit targets on a thin track) is the main frontend lift — mitigated by reusing the Phase-1 pointer-capture pattern from the drag-positioning preview.
- **Cubic-bézier solver correctness** — covered by endpoint + monotonicity tests; Newton + bisection fallback avoids divergence.
- **Backward-compat regressions** — covered by a dedicated legacy `from`/`to` sampling test and by leaving `render_element`/`render_animation`/compile/route paths untouched.
- **Scrub/Play performance** — rAF loop only updates one element's CSS transform; cheap. Stop on deselect/unmount to avoid leaks.
