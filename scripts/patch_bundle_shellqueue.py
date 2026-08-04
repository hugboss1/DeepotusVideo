# -*- coding: utf-8 -*-
# scripts/patch_bundle_shellqueue.py
"""Assert-guarded patcher : chantier 11a — job queue à la demande (UI Shell Pro).

BASELINE : bundle POST-patch tilelab (dernier patch en date).
Backup dédié : .js.bak_shellqueue (état juste avant CE patch).

Le Job Dock bas d'écran disparaît du flux (révision assumée du DESIGN.md §5) :
- le composant dock `rg` devient un panneau latéral DROIT 360 px monté en
  portal (scrim cliquable + slide-in 320 ms var(--ease), Esc ferme,
  prefers-reduced-motion → fade, visibility gérée pour le focus clavier) ;
- la topbar gagne une icône « file » (signal) + badge compteur N running
  (pastille cyan, halo pulsé ~1.2 Hz pendant un run, rouge fixe si un job
  failed non lu — lu = panneau ouvert, persisté localStorage
  dz_queue_seen_failed) insérée avant la pieuvre « Replay onboarding » ;
- les JobCards `yd` existantes sont réutilisées telles quelles (Running puis
  Recent, failed triés en tête) ; les cards démo `eg` ne servent plus de
  fallback → vrai état vide (🐙, DESIGN.md §9) ;
- toutes les copies « Job Dock » (toast Studio compris) sont reformulées
  vers « render queue / queue icon » ;
- poignée QA : window.__dzQueue {open(), close(), toggle(), state}.

z-index : scrim 150 / panneau 151 (au-dessus du shell ≤100, sous la modale
préviz vidéo 200 qui doit rester cliquable par-dessus le panneau).

Run : python scripts/patch_bundle_shellqueue.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_shellqueue")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ---------------------------------------------------------------------------
# Code injecté en scope module, juste avant `function rg(`.
# Style ES5-hoistable (function/var) : le header (défini plus tôt dans le
# fichier) référence dzQBtn au render, après l'évaluation du module.
# ---------------------------------------------------------------------------
INJECT = (
    'var dzqSt={open:!1,run:0,fail:0,subs:[]};var dzqJobs=[];'
    'function dzqEmit(){for(var z1=0;z1<dzqSt.subs.length;z1++)try{dzqSt.subs[z1]()}catch(_e){}}'
    'function dzqSet(p1){Object.assign(dzqSt,p1),dzqEmit()}'
    'function dzqSeen(){try{return JSON.parse(localStorage.getItem("dz_queue_seen_failed")||"[]")}catch(_e){return[]}}'
    'function dzqMarkSeen(){var ids=[],z1;for(z1=0;z1<dzqJobs.length;z1++)dzqJobs[z1].status==="failed"&&ids.push(dzqJobs[z1].job_id);'
    'var sn=dzqSeen();for(z1=0;z1<ids.length;z1++)sn.indexOf(ids[z1])<0&&sn.push(ids[z1]);'
    'try{localStorage.setItem("dz_queue_seen_failed",JSON.stringify(sn.slice(-100)))}catch(_e){}dzqSet({fail:0})}'
    'function dzqOpen(v1){var nx=v1===void 0?!dzqSt.open:!!v1;dzqSet({open:nx}),nx&&dzqMarkSeen()}'
    'function dzqPub(ls){dzqJobs=Array.isArray(ls)?ls:[];var run=0,fids=[],z1;'
    'for(z1=0;z1<dzqJobs.length;z1++){var j1=dzqJobs[z1];j1.status!=="done"&&j1.status!=="failed"?run++:j1.status==="failed"&&fids.push(j1.job_id)}'
    'var sn=dzqSeen(),un=0;for(z1=0;z1<fids.length;z1++)sn.indexOf(fids[z1])<0&&un++;'
    'dzqSt.open&&un&&(dzqMarkSeen(),un=0);dzqSet({run:run,fail:un})}'
    'window.__dzQueue={open:function(){dzqOpen(!0)},close:function(){dzqOpen(!1)},toggle:function(){dzqOpen()},'
    'get state(){return{open:dzqSt.open,running:dzqSt.run,unreadFailed:dzqSt.fail}}};'
    'function dzqUse(){var h1=x.useState(0),s1=h1[1];return x.useEffect(function(){'
    'function f1(){s1(function(v1){return v1+1})}return dzqSt.subs.push(f1),'
    'function(){dzqSt.subs=dzqSt.subs.filter(function(z1){return z1!==f1})}},[s1]),dzqSt}'
    'function dzqEsc(op){x.useEffect(function(){if(!op)return;'
    'function f1(ev){ev.key==="Escape"&&dzqOpen(!1)}return window.addEventListener("keydown",f1),'
    'function(){window.removeEventListener("keydown",f1)}},[op])}'
    'function dzqEmpty(){return r.jsxs("div",{style:{padding:"34px 12px",textAlign:"center",color:"var(--ink-soft)",fontSize:12.5,lineHeight:1.7},'
    'children:[r.jsx("div",{style:{fontSize:26,marginBottom:8,opacity:.75},children:"🐙"}),'
    '"Nothing rendering.",r.jsx("br",{}),"Press ",'
    'r.jsx("b",{style:{color:"var(--ink)",fontWeight:600},children:"▶ Run"})," in Studio or Quick."]})}'
    'function dzQBtn(){var q1=dzqUse(),n1=q1.run,f1=q1.fail,show=n1>0||f1>0;'
    'return r.jsxs("div",{style:{position:"relative",display:"inline-flex"},children:['
    'r.jsx(se,{name:"signal",title:"Render queue — "+n1+" running"+(f1?", "+f1+" failed (new)":""),active:q1.open,onClick:function(){dzqOpen()}}),'
    'show?r.jsx("span",{className:"mono"+(f1?"":" dzq-pulse"),style:{position:"absolute",top:-3,right:-3,minWidth:14,height:14,padding:"0 3px",'
    'borderRadius:8,fontSize:9,lineHeight:"14px",textAlign:"center",background:f1?"var(--red)":"var(--cyan)",color:"#02060d",fontWeight:700,'
    'pointerEvents:"none"},children:f1||(n1>9?"9+":n1)}):null]})}'
    '(function(){try{if(!document.getElementById("dzq-style")){var st=document.createElement("style");st.id="dzq-style";st.textContent='
    "'.deepotus .dzq-scrim{position:fixed;inset:0;z-index:150;background:var(--bg-overlay);opacity:0;pointer-events:none;"
    "transition:opacity var(--dur-3) var(--ease)}"
    ".deepotus .dzq-scrim.on{opacity:1;pointer-events:auto}"
    ".deepotus .dzq-panel{position:fixed;top:0;right:0;bottom:0;width:360px;z-index:151;background:var(--bg-panel);"
    "border-left:1px solid var(--stroke-strong);box-shadow:-24px 0 48px #000a;display:flex;flex-direction:column;"
    "transform:translateX(102%);visibility:hidden;transition:transform var(--dur-3) var(--ease),visibility 0s linear var(--dur-3)}"
    ".deepotus .dzq-panel.on{transform:translateX(0);visibility:visible;transition:transform var(--dur-3) var(--ease)}"
    "@keyframes dzq-halo{0%,100%{box-shadow:0 0 0 0 var(--cyan-soft)}50%{box-shadow:0 0 0 5px var(--cyan-soft)}}"
    ".deepotus .dzq-pulse{animation:dzq-halo .833s ease-in-out infinite}"
    "@media (prefers-reduced-motion: reduce){.deepotus .dzq-pulse{animation:none}"
    ".deepotus .dzq-panel{transition:opacity var(--dur-2) var(--ease),visibility 0s linear var(--dur-2);transform:none;opacity:0}"
    ".deepotus .dzq-panel.on{transform:none;opacity:1}}"
    "html.no-halo .deepotus .dzq-pulse{animation:none}';"
    'document.head.appendChild(st)}}catch(_e){}})();'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # S01 : injection module-scope (store, hooks, bouton, CSS) + état open/Esc
    # câblés en tête de rg.
    a = "function rg({expanded:e,setExpanded:t,variant:n}){"
    r = INJECT + a + "const q3=dzqUse();dzqEsc(q3.open);"
    s = apply(s, a, r, "S01-inject+rg-head")

    # S02 : le poll de rg publie les jobs vers le store (badge topbar).
    a = "i(Array.isArray(c)?c:[])},[])"
    r = "i(Array.isArray(c)?c:[]),dzqPub(c)},[])"
    s = apply(s, a, r, "S02-poll-pub")

    # S03 : plus de fallback cards démo — vrai état vide.
    a = "v=w.length>0?w:eg"
    r = "v=w"
    s = apply(s, a, r, "S03-no-demo-fallback")

    # S04 : failed triés en tête de la liste Recent.
    a = 'k=v.filter(c=>c.status!=="running")'
    r = ('k=v.filter(c=>c.status!=="running")'
         '.sort((a3,b3)=>(a3.status==="failed"?0:1)-(b3.status==="failed"?0:1))')
    s = apply(s, a, r, "S04-failed-first")

    # S05 : le return de rg devient portal(scrim + panneau droit).
    a = ('return r.jsxs("div",{style:{height:e?280:64,background:"var(--bg-panel)",'
         'borderTop:"1px solid var(--stroke-strong)",boxShadow:"0 -8px 24px #0006",'
         'display:"flex",flexDirection:"column",'
         'transition:"height var(--dur-3) var(--ease)",minHeight:0},children:[')
    r = ('return Pu.createPortal(r.jsxs(r.Fragment,{children:['
         'r.jsx("div",{className:"dzq-scrim"+(q3.open?" on":""),onClick:function(){dzqOpen(!1)}}),'
         'r.jsxs("div",{className:"dzq-panel"+(q3.open?" on":""),role:"complementary",'
         '"aria-label":"Render queue",children:[')
    s = apply(s, a, r, "S05-return-portal")

    # S06 : header du panneau — bordure basse permanente (plus de e?).
    a = 'borderBottom:e?"1px solid var(--stroke)":0}'
    r = 'borderBottom:"1px solid var(--stroke)"}'
    s = apply(s, a, r, "S06-hdr-border")

    # S07 : libellé.
    a = '{className:"upper",children:"Job dock"}'
    r = '{className:"upper",children:"Render queue"}'
    s = apply(s, a, r, "S07-label")

    # S08 : caret expand/collapse -> bouton close.
    a = ('r.jsx(se,{name:e?"caret":"caretR",iconSize:11,onClick:()=>t(!e),'
         'title:e?"Collapse":"Expand"})')
    r = 'r.jsx(se,{name:"close",iconSize:12,onClick:function(){dzqOpen(!1)},title:"Close — Esc"})'
    s = apply(s, a, r, "S08-close-btn")

    # S09 : la liste (ex-branche expanded) devient inconditionnelle.
    a = ('e?r.jsxs("div",{className:"scroll",style:{flex:1,overflowY:"auto",'
         'padding:"8px 14px"}')
    r = ('r.jsxs("div",{className:"scroll",style:{flex:1,overflowY:"auto",'
         'padding:"8px 14px"}')
    s = apply(s, a, r, "S09-list-always")

    # S10 : état vide + section Running conditionnelle.
    a = 'r.jsx("div",{className:"upper",style:{padding:"4px 0"},children:"Running"})'
    r = ('v.length===0?dzqEmpty():null,g.length?'
         'r.jsx("div",{className:"upper",style:{padding:"4px 0"},children:"Running"})'
         ':null')
    s = apply(s, a, r, "S10-empty+running-hdr")

    # S11 : section Recent conditionnelle.
    a = 'r.jsx("div",{className:"upper",style:{padding:"12px 0 4px"},children:"Recent"})'
    r = ('k.length?'
         'r.jsx("div",{className:"upper",style:{padding:"12px 0 4px"},children:"Recent"})'
         ':null')
    s = apply(s, a, r, "S11-recent-hdr")

    # S12 : suppression de la branche collapsed (cards og horizontales).
    a = (']}):r.jsx("div",{style:{flex:1,padding:"0 14px",display:"flex",'
         'alignItems:"center",gap:10,overflowX:"auto"},children:[...g,...k]'
         '.slice(0,3).map(c=>r.jsx(og,{job:c,onPreview:()=>d({id:c.id,title:c.title}),'
         'onCopy:()=>y(c),onDelete:()=>a(c.id),onRename:p=>m(c.id,p)},c.id))})')
    r = ']})'
    s = apply(s, a, r, "S12-drop-collapsed")

    # S13 : fermeture de rg — panneau puis fragment puis portal(document.body).
    a = ",document.body)]})}function Hu("
    r = ",document.body)]})]}),document.body)}function Hu("
    s = apply(s, a, r, "S13-tail")

    # S14 : icône file + badge dans la topbar, avant la pieuvre.
    a = 'r.jsx(se,{name:"octopus",title:"Replay onboarding",onClick:o})'
    r = 'r.jsx(dzQBtn,{}),' + a
    s = apply(s, a, r, "S14-topbar-btn")

    # S15 : toast Studio reformulé (spec 11a).
    a = 'p("Still rendering in the background — check the Job Dock.")'
    r = 'p("Still rendering in the background — follow it from the queue icon up top.")'
    s = apply(s, a, r, "S15-toast-studio")

    # S16 : autres copies « Job Dock » (cohérence, le dock n'existe plus).
    for tag, a, r in [
        ("S16a-render-node",
         '" node, or find it in the Job Dock and Library."',
         '" node, or find it in the render queue (top bar) and Library."'),
        ("S16b-below",
         '" Watch the Job Dock below."',
         '" Watch the render queue (top bar icon)."'),
        ("S16c-fal-confirm",
         "this will queue in the Job Dock.",
         "this will queue in the render queue (top bar icon)."),
        ("S16d-reel-queued",
         '— watch the Job Dock.":"Illustration failed."',
         '— watch the render queue.":"Illustration failed."'),
        ("S16e-seedance-toast",
         'watch the Job Dock.");const V',
         'watch the render queue.");const V'),
        ("S16f-quick-hint",
         "— watch the Job Dock. The clip plays here",
         "— watch the render queue (top bar icon). The clip plays here"),
    ]:
        s = apply(s, a, r, tag)

    if "Job Dock" in s or "Job dock" in s:
        raise SystemExit("Il reste des occurrences de « Job Dock » non traitées. Aborting.")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (11a queue panel). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
