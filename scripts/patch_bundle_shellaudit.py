# -*- coding: utf-8 -*-
# scripts/patch_bundle_shellaudit.py
"""Assert-guarded patcher : chantier 11d — corrections issues du harnais
d'audit qa-shell-audit.js (débordements mesurés sur l'app installée).

BASELINE : bundle POST-patch toolbars (11c).
Backup dédié : .js.bak_shellaudit (état juste avant CE patch).

Corrections (chaque cas = finding mesuré, voir scripts/qa/shots-shell-audit) :

1. Templates — inspecteur REGION (x/y/w/h) : la grille « 1fr 1fr » ne peut
   pas descendre sous le min-content des inputs (~220 px/colonne) et pousse
   la 2e colonne HORS VIEWPORT (mesuré : right 1683 pour vw 1600).
   -> tracks minmax(0,1fr) + data-dzregion + CSS min-width:0 scopé.

2. Templates — rangée de tags des cards : spans en flex, wrap coupé à vif
   par l'overflow hidden de la card (X et Y). -> une seule ligne texte
   ellipsisée, texte complet dans title (tooltip sombre 11c).

3. Settings — colonne libellés des clés (220 px) : `K · why` et
   `current: préview-masquée` débordent en overflow visible (scrollWidth
   300 > clientWidth 180). -> ellipsis + title.

(Le débordement connu « Action à animer » du Sprite Lab est corrigé dans
frontend/spritelab/spritelab.css — source non minifiée, pas de patch bundle :
minimums de .panes 980 px -> 800 px, couvert par la passe étroite 900 px du
harnais.)

Run : python scripts/patch_bundle_shellaudit.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_shellaudit")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# CSS scopé : les enfants de la grille REGION peuvent rétrécir sous leur
# min-content (sinon les tracks minmax(0,1fr) ne suffisent pas).
CSS = (
    '(function(){try{if(!document.getElementById("dzaudit-style")){'
    'var st=document.createElement("style");st.id="dzaudit-style";st.textContent='
    "'[data-dzregion] div,[data-dzregion] label{min-width:0}';"
    'document.head.appendChild(st)}}catch(_e){}})();'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # A01 : CSS injecté en module-scope (même point d'ancrage que 11a/11c).
    a = "var dzqSt={open:!1,run:0,fail:0,subs:[]};"
    s = apply(s, a, CSS + a, "A01-css")

    # A02 : grille REGION -> tracks compressibles + marqueur.
    a = '("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8},children:[r.jsx(O,{label:"x"'
    r = ('("div",{"data-dzregion":"1",style:{display:"grid",'
         'gridTemplateColumns:"minmax(0,1fr) minmax(0,1fr)",gap:8},children:[r.jsx(O,{label:"x"')
    s = apply(s, a, r, "A02-region-grid")

    # A03 : tags des cards Templates -> 1 ligne ellipsisée + tooltip.
    a = ('r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",display:"flex",gap:4},'
         'children:f.tags.map(y=>r.jsxs("span",{children:["· ",y]},y))})')
    r = ('r.jsx("div",{title:f.tags.join(" · "),style:{fontSize:10.5,color:"var(--ink-soft)",'
         'overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",minWidth:0},'
         'children:f.tags.map(y=>"· "+y).join(" ")})')
    s = apply(s, a, r, "A03-card-tags")

    # A04 : Settings — `K · why` ellipsisé.
    a = ('r.jsxs("div",{className:"mono",style:{fontSize:10.5,color:"var(--ink-muted)"},'
         'children:[k.k," · ",k.why]})')
    r = ('r.jsxs("div",{className:"mono",title:k.k+" · "+k.why,'
         'style:{fontSize:10.5,color:"var(--ink-muted)",overflow:"hidden",'
         'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:[k.k," · ",k.why]})')
    s = apply(s, a, r, "A04-key-why")

    # A05 : Settings — préview masquée ellipsisée.
    a = ('r.jsxs("div",{className:"mono",style:{fontSize:10,color:"var(--ink-soft)",marginTop:2},'
         'children:["current: ",h.preview]})')
    r = ('r.jsxs("div",{className:"mono",title:h.preview,'
         'style:{fontSize:10,color:"var(--ink-soft)",marginTop:2,overflow:"hidden",'
         'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:["current: ",h.preview]})')
    s = apply(s, a, r, "A05-key-preview")

    # A06/A07 : Settings « Connected accounts » — DEUXIÈME copie du composant
    # de rangée de clés (colonne 180px) : b.k et z.preview débordaient
    # (scrollWidth 300 > clientWidth 180, harnais). Mêmes ellipsis.
    a = 'r.jsx("div",{className:"mono",style:{fontSize:10,color:"var(--ink-muted)"},children:b.k})'
    r = ('r.jsx("div",{className:"mono",title:b.k,style:{fontSize:10,color:"var(--ink-muted)",'
         'overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:b.k})')
    s = apply(s, a, r, "A06-acct-key")

    a = 'r.jsx("div",{className:"mono",style:{fontSize:10,color:"var(--ink-soft)"},children:z.preview})'
    r = ('r.jsx("div",{className:"mono",title:z.preview,style:{fontSize:10,color:"var(--ink-soft)",'
         'overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:z.preview})')
    s = apply(s, a, r, "A07-acct-preview")

    # A08/A09 : marqueur data-dzpreview sur les régions des previews spatiaux
    # (éditeur + miniatures de cards) : représentations À L'ÉCHELLE — leurs
    # labels ($DEEPOTUS, r_sep…) sont clippés PAR DESIGN par la région.
    # Exclusion documentée côté harnais ([data-dzpreview]).
    a = 'style:{position:"absolute",left:H,top:F,width:I,height:A,border:'
    r = '"data-dzpreview":"1",' + a
    s = apply(s, a, r, "A08-region-editor")

    a = ('borderRadius:3,boxSizing:"border-box",overflow:"hidden",'
         'containerType:"inline-size",border:"1px solid rgba(255,255,255,.05)"}')
    r = a + ',"data-dzpreview":"1"'
    s = apply(s, a, r, "A09-region-mini")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (11d shell-audit fixes). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
