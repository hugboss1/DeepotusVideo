# -*- coding: utf-8 -*-
# scripts/patch_bundle_nodedock.py
"""Assert-guarded patcher : dock des nodes du Studio escamotable via « / ».

BASELINE : bundle POST-patch shellqueue (11a, dernier patch en date).
Backup dédié : .js.bak_nodedock (état juste avant CE patch).

Le hint « press / » (header du dock) et « / nodes » (canvas) existaient sans
AUCUN handler clavier. Ce patch les rend vrais :
- « / » replie/déplie le dock des nodes (colonne 260 px -> 0 px animée,
  le canvas récupère la largeur) ; inactif quand le focus est dans un
  input/textarea/select/contenteditable ; actif uniquement si le Studio
  est monté (présence de .dz-studio-grid) ;
- réouverture à la souris : poignée « NODES » sur le bord gauche du canvas
  (visible seulement dock replié) + bouton croix dans le header du dock ;
- ouverture via « / » -> focus du champ Search du dock ; Esc avec le focus
  dans le dock le replie ;
- état persisté localStorage dz_studio_dock ("1" ouvert par défaut) ;
- prefers-reduced-motion -> pas d'animation ;
- poignée QA : window.__dzNodes {open(), close(), toggle(), state}.

Architecture : store module-scope dzdSt (pattern dzqSt du 11a) ; la classe
du conteneur grid est calculée au render depuis dzdSt ET togglée en direct
par dzdOpen (classList) pour réagir sans re-render React.

Run : python scripts/patch_bundle_nodedock.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_nodedock")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


CSS = (
    ".dz-studio-grid{transition:grid-template-columns .28s cubic-bezier(.22,.61,.36,1)}"
    ".dz-studio-grid.dz-dock-hidden{grid-template-columns:0px 1fr 340px!important}"
    ".dz-studio-grid>div:first-child{min-width:0;overflow:hidden;transition:opacity .18s ease}"
    ".dz-studio-grid.dz-dock-hidden>div:first-child{opacity:0;pointer-events:none}"
    ".dz-dock-handle{position:absolute;left:0;top:64;z-index:5;display:inline-flex;align-items:center;gap:5px;"
    "padding:7px 9px 7px 7px;background:var(--bg-panel);border:1px solid var(--stroke);border-left:0;"
    "border-radius:0 8px 8px 0;cursor:pointer;color:var(--ink-soft);font-family:var(--f-mono);font-size:10px;"
    "letter-spacing:.5px;transition:color .15s ease,border-color .15s ease}"
    ".dz-dock-handle:hover{color:var(--ink-strong);border-color:var(--stroke-strong)}"
    ".dz-studio-grid:not(.dz-dock-hidden) .dz-dock-handle{display:none}"
    "@media (prefers-reduced-motion: reduce){.dz-studio-grid,.dz-studio-grid>div:first-child{transition:none}}"
)

# ---------------------------------------------------------------------------
# S1 — store + listener + CSS, module-scope (var/function hoistables),
# injectés juste avant Dh (util topologique du Studio).
# ---------------------------------------------------------------------------
INJECT = (
    'var dzdSt={open:function(){try{return localStorage.getItem("dz_studio_dock")!=="0"}catch(_e){return!0}}(),subs:[]};'
    'function dzdEmit(){for(var z1=0;z1<dzdSt.subs.length;z1++)try{dzdSt.subs[z1]()}catch(_e){}}'
    'function dzdOpen(v1){var nx=v1===void 0?!dzdSt.open:!!v1;if(nx===dzdSt.open)return;dzdSt.open=nx;'
    'try{localStorage.setItem("dz_studio_dock",nx?"1":"0")}catch(_e){}'
    'var g1=document.querySelector(".dz-studio-grid");g1&&g1.classList.toggle("dz-dock-hidden",!nx);'
    'nx&&setTimeout(function(){try{var i1=document.querySelector(".dz-studio-grid>div:first-child input");i1&&i1.focus()}catch(_e){}},300);'
    'dzdEmit()}'
    'window.__dzNodes={open:function(){dzdOpen(!0)},close:function(){dzdOpen(!1)},toggle:function(){dzdOpen()},'
    'get state(){return{open:dzdSt.open}}};'
    'window.addEventListener("keydown",function(ev){'
    'if(ev.key==="Escape"){var a1=document.activeElement,g2=document.querySelector(".dz-studio-grid");'
    'if(g2&&dzdSt.open&&a1&&g2.children[0]&&g2.children[0].contains(a1)){a1.blur();dzdOpen(!1)}return}'
    'if(ev.key!=="/"||ev.metaKey||ev.ctrlKey||ev.altKey)return;'
    'var t1=ev.target,tg=(t1&&t1.tagName||"").toLowerCase();'
    'if(tg==="input"||tg==="textarea"||tg==="select"||(t1&&t1.isContentEditable))return;'
    'if(!document.querySelector(".dz-studio-grid"))return;'
    'ev.preventDefault();dzdOpen()});'
    '(function(){try{var st=document.createElement("style");st.textContent=\'' + CSS + '\';'
    'document.head.appendChild(st)}catch(_e){}})();'
)


def main():
    s = BUNDLE.read_text(encoding="utf-8")
    if "dz-studio-grid" in s:
        raise SystemExit("Bundle déjà patché (dz-studio-grid présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)

    # S1 : injection module-scope avant Dh.
    a = "function Dh(e){const t=Object.fromEntries"
    s = apply(s, a, INJECT + a, "S1-store")

    # S2 : classe pilotée par l'état sur le conteneur grid du Studio
    # (className inséré juste avant style).
    full_anchor = ('r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"260px 1fr 340px",'
                   'height:"100%",minHeight:0,background:"var(--bg-base)"},children:[r.jsx(Ah,{variant:e,onPickStarter:')
    full_repl = ('r.jsxs("div",{className:"dz-studio-grid"+(dzdSt.open?"":" dz-dock-hidden"),'
                 'style:{display:"grid",gridTemplateColumns:"260px 1fr 340px",'
                 'height:"100%",minHeight:0,background:"var(--bg-base)"},children:[r.jsx(Ah,{variant:e,onPickStarter:')
    s = apply(s, full_anchor, full_repl, "S2-grid-class")

    # S3 : poignée de réouverture dans le canvas (avant le bloc zoom).
    a = ('r.jsxs("div",{style:{position:"absolute",left:12,bottom:12,zIndex:4,display:"flex",gap:4,'
         'background:"var(--bg-panel)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",padding:2},'
         'children:[r.jsx(se,{name:"minus",size:26,')
    r = ('r.jsxs("button",{className:"dz-dock-handle",title:"Nodes — press /",'
         'onClick:function(){window.__dzNodes&&window.__dzNodes.open()},'
         'children:[r.jsx(X,{name:"flow",size:11}),"NODES"]}),') + a
    s = apply(s, a, r, "S3-handle")

    # S4 : bouton de repli dans le header du dock (à côté de « press / »).
    a = ('children:[r.jsx("span",{className:"upper",children:"Nodes"}),'
         'r.jsx("span",{style:{fontFamily:"var(--f-mono)",fontSize:10,color:"var(--ink-muted)"},children:"press /"})]')
    r = ('children:[r.jsx("span",{className:"upper",children:"Nodes"}),'
         'r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:6},children:['
         'r.jsx("span",{style:{fontFamily:"var(--f-mono)",fontSize:10,color:"var(--ink-muted)"},children:"press /"}),'
         'r.jsx(se,{name:"close",size:22,iconSize:11,title:"Hide — /",'
         'onClick:function(){window.__dzNodes&&window.__dzNodes.close()}})]})]')
    s = apply(s, a, r, "S4-header-close")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (nodedock « / »). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
