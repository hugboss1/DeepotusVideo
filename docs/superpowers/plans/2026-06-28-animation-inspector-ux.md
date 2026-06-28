# Animation Inspector UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Add a live font visualizer (▲/▼ + ↑/↓), reuse `DzColorPicker` for text/stroke colors, and stop the inspector fields from overflowing the 340px right panel.

**Architecture:** Two count-guarded patches to `DzAnimation` in the compiled bundle. No backend changes. Each patch: Python `str.count==1` replace → `node --check` → deploy → browser-test at http://127.0.0.1:8765/.

**Tech Stack:** compiled React bundle (`frontend/dist/assets/index-BEOJX8L5.js`); reused in-bundle components: `DzColorPicker` (HSV popover), `cssFont`, `FONTS`, `patchStyle`, `O`, `le`.

---

## Task 1: Font visualizer + color pickers (restructured text-style block)

**Files:** Modify `frontend/dist/assets/index-BEOJX8L5.js`.

- [ ] **Step 1: Add the `fontStep` helper.** Count-guarded replace — anchor (end of the FONTS array, unique):
`"Abril Fatface","Cinzel"];`
→
`"Abril Fatface","Cinzel"];function fontStep(d){var i=FONTS.indexOf((cur.style&&cur.style.font)||"Anton");if(i<0)i=0;var n=(i+d+FONTS.length)%FONTS.length;patchStyle({font:FONTS[n]})}`

- [ ] **Step 2: Replace the whole text-style block** (font dropdown + 4-field grid) with the visualizer + Size/Stroke grid + two `DzColorPicker` rows. Anchor (the full current block, unique):
```
cur.type==="text"?r.jsxs("div",{children:[r.jsx(O,{label:"Font",children:r.jsx(re,{value:(cur.style&&cur.style.font)||"Anton",options:FONTS.map(function(ff){return{value:ff,label:ff}}),onChange:function(v){patchStyle({font:v})}})}),r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6},children:[r.jsx(O,{label:"Size",children:r.jsx(le,{mono:!0,value:String((cur.style&&cur.style.size)||80),onChange:function(v){patchStyle({size:Number(v)||0})}})}),r.jsx(O,{label:"Color",children:r.jsx(le,{mono:!0,value:(cur.style&&cur.style.color)||"#ffffff",onChange:function(v){patchStyle({color:v})}})}),r.jsx(O,{label:"Stroke",children:r.jsx(le,{mono:!0,value:String((cur.style&&cur.style.stroke)||0),onChange:function(v){patchStyle({stroke:Number(v)||0})}})}),r.jsx(O,{label:"Stroke color",children:r.jsx(le,{mono:!0,value:(cur.style&&cur.style.strokeColor)||"#000000",onChange:function(v){patchStyle({strokeColor:v})}})})]})]}):null,
```
Replacement:
```
cur.type==="text"?r.jsxs("div",{children:[r.jsxs("div",{tabIndex:0,onKeyDown:function(ev){if(ev.key==="ArrowUp"){ev.preventDefault();fontStep(-1)}else if(ev.key==="ArrowDown"){ev.preventDefault();fontStep(1)}},style:{display:"flex",alignItems:"center",gap:8,marginBottom:10,padding:8,borderRadius:8,border:"1px solid var(--stroke)",background:"var(--surface-2)",outline:"none"},children:[r.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:4},children:[r.jsx("button",{onClick:function(){fontStep(-1)},title:"Previous font",style:{width:24,height:20,borderRadius:4,cursor:"pointer",background:"var(--bg-base)",border:"1px solid var(--stroke)",color:"var(--ink)",fontSize:10,lineHeight:1},children:"▲"}),r.jsx("button",{onClick:function(){fontStep(1)},title:"Next font",style:{width:24,height:20,borderRadius:4,cursor:"pointer",background:"var(--bg-base)",border:"1px solid var(--stroke)",color:"var(--ink)",fontSize:10,lineHeight:1},children:"▼"})]}),r.jsxs("div",{style:{flex:1,minWidth:0,overflow:"hidden"},children:[r.jsx("div",{style:{fontFamily:cssFont((cur.style&&cur.style.font)||"Anton"),fontSize:26,lineHeight:1.15,color:"var(--ink)",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"},children:cur.text||"DEEPOTUS"}),r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",marginTop:2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:(cur.style&&cur.style.font)||"Anton"})]})]}),r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:6,minWidth:0},children:[r.jsx(O,{label:"Size",children:r.jsx(le,{mono:!0,value:String((cur.style&&cur.style.size)||80),onChange:function(v){patchStyle({size:Number(v)||0})}})}),r.jsx(O,{label:"Stroke",children:r.jsx(le,{mono:!0,value:String((cur.style&&cur.style.stroke)||0),onChange:function(v){patchStyle({stroke:Number(v)||0})}})})]}),r.jsx(O,{label:"Color",children:r.jsx(DzColorPicker,{value:(cur.style&&cur.style.color)||"#ffffff",onChange:function(i){patchStyle({color:i})}})}),r.jsx(O,{label:"Stroke color",children:r.jsx(DzColorPicker,{value:(cur.style&&cur.style.strokeColor)||"#000000",onChange:function(i){patchStyle({strokeColor:i})}})})]}):null,
```

- [ ] **Step 3:** `node --check` the bundle; deploy to `%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js`.

- [ ] **Step 4: Browser-test.** Reload http://127.0.0.1:8765/, add an Animation + Text element. Confirm: the font visualizer shows the text rendered in the current typeface; clicking ▲/▼ (and ArrowUp/Down after focusing the box) changes the typeface AND persists `style.font`; the Color and Stroke-color swatches open the `DzColorPicker` HSV popover and update `style.color`/`strokeColor` live (drag-preview color changes). No console errors.

- [ ] **Step 5: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "feat(studio): Animation font visualizer + DzColorPicker for text/stroke colors"
```

---

## Task 2: Panel overflow fix (remaining grids + root safety net)

**Files:** Modify `frontend/dist/assets/index-BEOJX8L5.js`.

- [ ] **Step 1: kfRow grid → shrinkable.** Anchor (the `kfRow` grid, unique):
`function kfRow(){return r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6},children:[numField("x %","x")`
→
`function kfRow(){return r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:6,minWidth:0},children:[numField("x %","x")`

- [ ] **Step 2: Timing 3-col grid → shrinkable.** Anchor (the timing grid, unique — it precedes "Start s"):
`r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:6},children:[r.jsx(O,{label:"Start s"`
→
`r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"repeat(3,minmax(0,1fr))",gap:6,minWidth:0},children:[r.jsx(O,{label:"Start s"`

- [ ] **Step 3: Root safety net.** Anchor (the `DzAnimation` panel return, unique):
`return r.jsxs(ie,{label:"Animation",children:[r.jsxs("div",{style:{display:"flex",gap:6,marginBottom:8}`
→
`return r.jsx("div",{style:{maxWidth:"100%",overflowX:"hidden"},children:r.jsxs(ie,{label:"Animation",children:[r.jsxs("div",{style:{display:"flex",gap:6,marginBottom:8}`
And close the added wrapper: anchor the panel's closing (the favPanel tail, unique):
`,editor,favPanel()]})}`
→
`,editor,favPanel()]})})}`

- [ ] **Step 4:** `node --check`; deploy.

- [ ] **Step 5: Browser-test (overflow gone).** Reload, add Animation + Text element, open the timeline + all editor sections. Run a DOM check: for the inspector panel, **no descendant has `getBoundingClientRect().right` beyond the panel's right edge** (the same probe that found 24 overflowing nodes should now find 0). No console errors.

- [ ] **Step 6: Commit**
```bash
git -C C:/Users/olivi/DeepotusVideo commit -am "fix(studio): Animation inspector fields fit the panel (minmax grids + overflow-x guard)"
```

---

## Self-Review

**Spec coverage:** font visualizer replacing the dropdown, ▲/▼ + ↑/↓ keys, live preview (T1) ✓; reuse `DzColorPicker` for `color`+`strokeColor` (T1) ✓; overflow fix via `repeat(N,minmax(0,1fr))` on every DzAnimation grid (style 2-col in T1; kfRow + timing in T2) + root `overflow-x:hidden` (T2) ✓.

**Placeholder scan:** every step gives the exact anchor + exact replacement. No TODO/TBD.

**Type consistency:** `fontStep(d)` defined in T1-Step1 before its use in T1-Step2; uses `FONTS`/`patchStyle`/`cur` (all in DzAnimation scope). `DzColorPicker`/`cssFont` are module-level (hoisted), available in `DzAnimation`. The T2 root-wrapper adds exactly one `r.jsx("div",{...},children:…)` open and one matching `)` at the favPanel tail — balanced.
