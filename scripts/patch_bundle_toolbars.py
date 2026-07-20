# -*- coding: utf-8 -*-
# scripts/patch_bundle_toolbars.py
"""Assert-guarded patcher : chantier 11c — toolbars (UI Shell Pro).

BASELINE : bundle POST-patch voiceprov (dernier patch en date).
Backup dédié : .js.bak_toolbars (état juste avant CE patch).

Deux volets (spec 11c + observation d'Olivier) :

1. Tooltips sombres (DESIGN.md §7 : « Tooltip — sombre, 100 ms delay,
   max-width 280 ») : couche globale déléguée sur document.
   - mouseover sur [title] -> l'attribut est déplacé vers data-dztip (le
     tooltip natif clair du navigateur ne peut plus apparaître), timer 100 ms
     puis .dz-tip positionné sous l'élément (clamp viewport, flip au-dessus
     si pas la place) ;
   - mouseout / mousedown / scroll / Escape -> masque ET RESTAURE title
     (compat recettes existantes qui sélectionnent par [title=...] : un clic
     Puppeteer déclenche mousedown, donc l'attribut revient aussitôt) ;
   - SELECT/OPTION exclus (spec : les selects gardent leur libellé visible,
     pas de couche par-dessus) ;
   - clavier : focusin :focus-visible -> même tooltip (a11y), focusout masque ;
   - prefers-reduced-motion -> pas de transition ;
   - poignée QA : window.__dzTip.state {visible, text}.

2. JobCards du panneau queue : la grille héritée du dock pleine largeur
   (52px 1fr 200px auto) se calcule en « 52px 0px 200px 92px » dans le
   panneau de 360 px (mesure Puppeteer) : la colonne texte tombe à 0 et le
   titre/uuid wrappe verticalement sur 3+ lignes. Refonte 2 rangées :
     rangée 1 : [thumb 52] [titre + méta, colonnes 2..3]
     rangée 2 : [statut/progress col 2] [actions col 3, calées à droite]
   + ellipsis 1 ligne sur titre (title= pour le tooltip), uuid et erreur.

z-index tooltip : 400 (au-dessus de la modale préviz 200 et du panneau 151).

Run : python scripts/patch_bundle_toolbars.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_toolbars")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ---------------------------------------------------------------------------
# Volet 1 — couche tooltip globale (CSS + délégation), IIFE module-scope.
# ---------------------------------------------------------------------------
TIP = (
    '(function(){try{'
    'if(!document.getElementById("dztip-style")){var st=document.createElement("style");st.id="dztip-style";st.textContent='
    "'.dz-tip{position:fixed;z-index:400;background:var(--bg-panel-2,#0f1c30);color:var(--ink-strong,#e6f1ff);"
    "border:1px solid var(--stroke-strong,#2a3c5e);border-radius:var(--r-sm,6px);padding:5px 9px;"
    "font-size:11.5px;line-height:1.45;max-width:280px;pointer-events:none;opacity:0;transform:translateY(2px);"
    "transition:opacity var(--dur-1,.12s) var(--ease,ease),transform var(--dur-1,.12s) var(--ease,ease);"
    "box-shadow:0 8px 24px #000c}"
    ".dz-tip.on{opacity:1;transform:none}"
    "@media (prefers-reduced-motion: reduce){.dz-tip{transition:none;transform:none}}';"
    'document.head.appendChild(st)}'
    'var dztEl=null,dztTmr=0,dztCur=null;'
    'function dztTip(){if(!dztEl){dztEl=document.createElement("div");dztEl.className="dz-tip";'
    'dztEl.setAttribute("role","tooltip");document.body.appendChild(dztEl)}return dztEl}'
    'function dztHide(){dztTmr&&(clearTimeout(dztTmr),dztTmr=0);'
    'if(dztCur&&dztCur.getAttribute&&dztCur.getAttribute("data-dztip")&&!dztCur.getAttribute("title"))'
    'dztCur.setAttribute("title",dztCur.getAttribute("data-dztip"));'
    'dztCur=null;dztEl&&dztEl.classList.remove("on")}'
    'function dztPlace(el,txt){var t=dztTip();t.textContent=txt;t.style.left="0px";t.style.top="0px";t.classList.add("on");'
    'var r1=el.getBoundingClientRect(),tw=t.offsetWidth,th=t.offsetHeight,vw=window.innerWidth,vh=window.innerHeight,'
    'lx=Math.max(8,Math.min(r1.left+r1.width/2-tw/2,vw-tw-8)),ty=r1.bottom+7;'
    'ty+th>vh-8&&(ty=Math.max(8,r1.top-th-7));t.style.left=Math.round(lx)+"px";t.style.top=Math.round(ty)+"px"}'
    'function dztArm(el,txt,steal){if(!txt)return;'
    'steal&&(el.setAttribute("data-dztip",txt),el.removeAttribute("title"));'
    'dztCur=el;dztTmr=setTimeout(function(){dztTmr=0;dztCur===el&&dztPlace(el,txt)},100)}'
    'document.addEventListener("mouseover",function(ev){'
    'var el=ev.target&&ev.target.closest?ev.target.closest("[title],[data-dztip]"):null;'
    'if(el===dztCur)return;dztHide();if(!el)return;'
    'var tg=el.tagName;if(tg==="SELECT"||tg==="OPTION"||(el.closest&&el.closest("select")))return;'
    'var ti=el.getAttribute("title");dztArm(el,ti||el.getAttribute("data-dztip"),!!ti)},!0);'
    'document.addEventListener("mouseout",function(ev){if(!dztCur)return;'
    'var to=ev.relatedTarget;if(to&&dztCur.contains&&dztCur.contains(to))return;'
    'if(ev.target===dztCur||(dztCur.contains&&dztCur.contains(ev.target)))dztHide()},!0);'
    'document.addEventListener("mousedown",function(){dztHide()},!0);'
    'window.addEventListener("scroll",function(){dztHide()},!0);'
    'document.addEventListener("keydown",function(ev){ev.key==="Escape"&&dztHide()},!0);'
    'document.addEventListener("focusin",function(ev){'
    'var el=ev.target&&ev.target.closest?ev.target.closest("[title],[data-dztip]"):null;'
    'if(!el||el===dztCur)return;var fv=!1;try{fv=el.matches(":focus-visible")}catch(_e){}if(!fv)return;'
    'var tg=el.tagName;if(tg==="SELECT"||tg==="OPTION")return;dztHide();'
    'var ti=el.getAttribute("title");dztArm(el,ti||el.getAttribute("data-dztip"),!!ti)},!0);'
    'document.addEventListener("focusout",function(){dztCur&&dztHide()},!0);'
    'window.__dzTip={get state(){return{visible:!!(dztEl&&dztEl.classList.contains("on")),'
    'text:dztEl?dztEl.textContent:""}}};'
    '}catch(_e){}})();'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # T01 : couche tooltip injectée juste avant le store 11a (module scope).
    a = "var dzqSt={open:!1,run:0,fail:0,subs:[]};"
    s = apply(s, a, TIP + a, "T01-tip-layer")

    # T02 : grille yd 2 rangées adaptée au panneau 360 (mesure : 1fr -> 0px).
    a = 'gridTemplateColumns:"52px 1fr 200px auto",gap:14,alignItems:"center",padding:"10px 12px"'
    r = 'gridTemplateColumns:"52px minmax(0,1fr) auto",gap:"8px 12px",alignItems:"center",padding:"10px 12px"'
    s = apply(s, a, r, "T02-grid")

    # T03 : bloc titre+méta étalé colonnes 2..3 (rangée 1).
    a = ('r.jsxs("div",{style:{minWidth:0},children:[r.jsx("div",'
         '{style:{display:"flex",alignItems:"center",gap:8},children:r.jsx(Hu,')
    r = ('r.jsxs("div",{style:{minWidth:0,gridColumn:"2 / -1"},children:[r.jsx("div",'
         '{style:{display:"flex",alignItems:"center",gap:8},children:r.jsx(Hu,')
    s = apply(s, a, r, "T03-textblock")

    # T04 : statut/progress -> rangée 2, colonne 2.
    a = 'r.jsxs("div",{style:{minWidth:0},children:[d&&r.jsxs(r.Fragment,{children:[r.jsx(Nu,'
    r = ('r.jsxs("div",{style:{minWidth:0,gridColumn:2,gridRow:2},'
         'children:[d&&r.jsxs(r.Fragment,{children:[r.jsx(Nu,')
    s = apply(s, a, r, "T04-status-row2")

    # T05 : actions -> rangée 2, colonne 3, calées à droite.
    a = 'r.jsxs("div",{style:{display:"flex",gap:4,position:"relative"},children:[f&&r.jsx(se,{name:"play"'
    r = ('r.jsxs("div",{style:{display:"flex",gap:4,position:"relative",'
         'gridColumn:3,gridRow:2,justifySelf:"end"},children:[f&&r.jsx(se,{name:"play"')
    s = apply(s, a, r, "T05-actions-row2")

    # T06 : uuid job en ellipsis 1 ligne (title= -> tooltip sombre au survol).
    # Le span provider passe en nowrap+flexShrink:0 : sans ça il wrappe sur 2
    # lignes dans le panneau étroit et étire toute la rangée méta à 32px
    # (align-items stretch) — c'est LUI qui faisait « wrapper » la ligne uuid.
    a = 'r.jsx("span",{children:e.provider}),"·",r.jsx("span",{className:"mono",children:e.id})'
    r = ('r.jsx("span",{style:{whiteSpace:"nowrap",flexShrink:0},children:e.provider}),"·",'
         'r.jsx("span",{className:"mono",title:e.id,style:{minWidth:72,overflow:"hidden",'
         'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:e.id})')
    s = apply(s, a, r, "T06-id-ellipsis")

    # T07 : message d'erreur en ellipsis 1 ligne (texte complet via tooltip).
    a = 'u&&r.jsxs("span",{style:{color:"var(--red)"},children:["· ",e.error]})'
    r = ('u&&r.jsxs("span",{title:e.error,style:{color:"var(--red)",minWidth:0,overflow:"hidden",'
         'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:["· ",e.error]})')
    s = apply(s, a, r, "T07-err-ellipsis")

    # T08 : la rangée méta ne wrappe plus (les spans ellipsisent dedans).
    a = 'style:{fontSize:11,color:"var(--ink-soft)",display:"flex",gap:8,marginTop:2}'
    r = 'style:{fontSize:11,color:"var(--ink-soft)",display:"flex",gap:8,marginTop:2,minWidth:0}'
    s = apply(s, a, r, "T08-metarow")

    # T09 : titre Hu — title= pour lire le titre complet via tooltip.
    a = 'textOverflow:"ellipsis",flex:"0 1 auto",minWidth:0},children:e})'
    r = 'textOverflow:"ellipsis",flex:"0 1 auto",minWidth:0},title:e,children:e})'
    s = apply(s, a, r, "T09-title-tip")

    # T10 : marqueur data-dzselect sur le déclencheur du Select custom `re`
    # (73 usages) — poignée stable pour les recettes (libellé visible, jamais
    # de tooltip par-dessus) et pour le harnais d'audit 11d.
    a = 'r.jsxs("button",{onClick:()=>s(!i),style:{width:"100%",height:30,'
    r = 'r.jsxs("button",{onClick:()=>s(!i),"data-dzselect":"1",style:{width:"100%",height:30,'
    s = apply(s, a, r, "T10-dzselect-marker")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (11c toolbars). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
