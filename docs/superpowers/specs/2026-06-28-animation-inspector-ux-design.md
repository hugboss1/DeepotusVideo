# Animation Inspector UX — Design (font visualizer + color picker + panel fit)

> **Context:** A focused UX pass on the `Animation` node inspector (`DzAnimation` in the compiled bundle), after Phases 1 & 2 shipped. No backend changes. Three changes, all in `frontend/dist/assets/index-BEOJX8L5.js`.

**Goal:** Make picking a typeface and colors fast and visual, and stop inspector fields from overflowing the right panel.

---

## 1. Typo (font) visualizer — replaces the font dropdown

Replace the current `re` font dropdown (text element editor) with a **visualizer**:
- A preview box rendering the element's text (or `"DEEPOTUS"` when empty) in the **currently-selected font** via `fontFamily` (all 14 design fonts are declared `@font-face` in the app and load on demand, so the real typeface shows).
- The font **name** beneath the preview.
- **▲ / ▼ buttons** that step to the previous/next font in the existing `FONTS` array and write `style.font` via `patchStyle({font})`. Wrapping (last → first).
- The box is **focusable** (`tabIndex:0`); **ArrowUp/ArrowDown** keys cycle the font too (mirrors the `DzAvatarPick` ↑/↓ nav). Each step re-renders the preview in the new typeface.

Only the text-element editor uses this (sticker/image elements have no font).

## 2. Color picker — reuse `DzColorPicker`

Replace the two color **text inputs** in the text-element editor (**Color** = `style.color`, **Stroke color** = `style.strokeColor`) with the existing HSV picker component already in the bundle:
`r.jsx(DzColorPicker,{value:(cur.style&&cur.style.color)||"#ffffff",onChange:function(i){patchStyle({color:i})}})` and likewise for `strokeColor`. This is the same picker TextOverlay/Ticker/BrandStrip use, so behavior and styling match the rest of Studio. No new color component is written.

## 3. Right-panel overflow fix

Root cause: the inspector panel is ~340px wide. The editor's multi-column field grids use `gridTemplateColumns:"1fr 1fr"` / `"1fr 1fr 1fr"`, and `1fr` resolves to `minmax(auto,1fr)` — the track will not shrink below its content's min width, so the grid grows past the panel (the `le` input inside is then stretched to ~188px by its `flex:1`). The shared `le` primitive is **not** the problem: its input already has `flex:1; min-width:0`, so it shrinks correctly once its grid cell can shrink.

Fix, applied to the `DzAnimation` editor grids only (no change to the shared `le`/`O` primitives):
- Change every editor grid template from `1fr …` to `repeat(N,minmax(0,1fr))` so tracks can shrink below content width. This covers the Color/Stroke-color 2-col grid, the Start/Dur/Hold 3-col grid, and the x/y/scale/rotation/opacity keyframe grid (`kfRow`).
- Add `minWidth:0` to those grid containers and a `maxWidth:100%; overflow-x:hidden` safety net on the `DzAnimation` root so nothing can visually spill even if a future field is added.

Verified live: with `minmax(0,1fr)`, each `le`'s already-present `flex:1; min-width:0` makes the inputs fill (and shrink with) their cell.

**Acceptance:** with an Animation + text element selected, no descendant of the inspector panel has a right edge beyond the panel's right edge (verified live in the browser). Font ▲/▼ and ↑/↓ change the preview typeface and persist `style.font`. The color swatches open the HSV picker and update `style.color`/`strokeColor` live.

---

## Scope / non-goals
- No backend changes; rendering already resolves `style.font`/`color`/`strokeColor`.
- Reuse `DzColorPicker` — do not build a new picker.
- Font list stays the existing `FONTS` array (no new fonts).
- No change to non-text elements, the timeline, scrub/play, or favorites beyond the field-fit fix.
