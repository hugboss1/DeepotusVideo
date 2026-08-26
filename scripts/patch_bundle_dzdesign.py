# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzdesign.py
"""Assert-guarded patcher : design 26/08 — icônes 1b, barre 2a, teinte --cat.

BASELINE : bundle POST-patch navrail (dernier patch en date).
Backup dédié : .js.bak_dzdesign (état juste avant CE patch).

Réf : DESIGN.md §15 (handoff « Icônes Deepotus », variante 1b + barre 2a).
Trois chantiers, chirurgicaux :

  S1  les icônes du rail de navigation — les entrées NOMMÉES de la carte
      d'icônes (zap, flow, film, wave, layers, calendar, grid, rss, folder,
      cog) sont remplacées par les tracés « glyphe bicolore » du handoff.
      Le remplacement se fait par ÉQUILIBRAGE DE PARENTHÈSES depuis
      `NOM:r.jsx` — jamais une regex sur du minifié.
  S2  Game Assets gagne SA PROPRE icône (`gamegrid`, grille + volume) au
      lieu de partager `grid` avec Templates ; l'entrée Uu bascule.
  S3  la barre du hub Game Assets passe en variante 2a : bords droits,
      gap de 1 px = séparateur, liséré bas permanent dans la teinte de la
      catégorie, remplissage balayé à l'activation, libellés verbatim sans
      emoji — et le CONTENEUR de section pose `--cat` + `data-category`,
      que toute l'UI en dessous hérite (DESIGN.md §15-3.2).

Les tokens `--cat-*` viennent de deepotus.tokens.css (importé par
theme-v2.css) ; le style de la barre est injecté par un <style id=__dzCatBar>
au premier rendu (aucune feuille externe nouvelle).

Run : python scripts/patch_bundle_dzdesign.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzdesign")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def entry_bounds(s, name, tag):
    """(debut, fin) de l'entrée `name:r.jsx…(...)` de la carte d'icônes,
    fin trouvée par équilibrage de parenthèses depuis l'appel r.jsx."""
    needle = name + ":r.jsx"
    n = s.count(needle)
    if n != 1:
        raise SystemExit(f"[{tag}] '{needle}' count={n} (want 1). Aborting.")
    start = s.index(needle)
    i = s.index("(", start)
    depth = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return start, i + 1
        elif c == '"':
            i = s.index('"', i + 1)
            while s[i - 1] == "\\":
                i = s.index('"', i + 1)
        i += 1
    raise SystemExit(f"[{tag}] parenthèses non refermées. Aborting.")


# ── S1 : les tracés 1b, repris du handoff TELS QUELS (props React camelCase,
#         chaque glyphe porte SA couleur — le wrapper svg n'en pose aucune) ──
ICONS = {
    "zap":
        'zap:r.jsx("path",{fill:"currentColor",'
        'd:"M13.8 2.6 6 14.2h4.6L9.6 21.4 18 9.6h-4.8z"})',
    "flow":
        'flow:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("path",{d:"M8.4 11.2h3.2V6.4h4v1.6h-2.4V12H8.4zM11.6 12.8h3.2'
        'v3.6h2.4V18h-4v-3.6h-1.6z",opacity:".45"}),'
        'r.jsx("rect",{x:"2.8",y:"9.2",width:"5.6",height:"5.6",rx:"1.4"}),'
        'r.jsx("rect",{x:"15.6",y:"4",width:"5.6",height:"5.6",rx:"1.4"}),'
        'r.jsx("rect",{x:"15.6",y:"14.4",width:"5.6",height:"5.6",rx:"1.4"})]})',
    "film":
        'film:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("path",{d:"M3.8 4h6.6a1.6 1.6 0 0 1 1.6 1.6V20a2.4 2.4 0 0 0'
        '-1.7-.7H3.8z",opacity:".38"}),'
        'r.jsx("path",{fillRule:"evenodd",d:"M20.2 4h-6.6A1.6 1.6 0 0 0 12 '
        '5.6V20a2.4 2.4 0 0 1 1.7-.7h6.5zM14.6 9.4 18 11.4l-3.4 2z"})]})',
    "wave":
        'wave:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("rect",{x:"3",y:"10.4",width:"2.2",height:"3.2",rx:"1.1",opacity:".45"}),'
        'r.jsx("rect",{x:"7.2",y:"7",width:"2.2",height:"10",rx:"1.1"}),'
        'r.jsx("rect",{x:"11.4",y:"4.2",width:"2.2",height:"15.6",rx:"1.1"}),'
        'r.jsx("rect",{x:"15.6",y:"8",width:"2.2",height:"8",rx:"1.1"}),'
        'r.jsx("rect",{x:"19.8",y:"10.4",width:"2.2",height:"3.2",rx:"1.1",opacity:".45"})]})',
    "layers":
        'layers:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("rect",{x:"3",y:"5.6",width:"10.4",height:"2.6",rx:"1.3",opacity:".45"}),'
        'r.jsx("rect",{x:"3",y:"10.7",width:"14.6",height:"2.6",rx:"1.3",opacity:".45"}),'
        'r.jsx("rect",{x:"3",y:"15.8",width:"7.6",height:"2.6",rx:"1.3",opacity:".45"}),'
        'r.jsx("rect",{x:"18.6",y:"3.4",width:"2",height:"17.2",rx:"1"})]})',
    "calendar":
        'calendar:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("rect",{x:"3.2",y:"5.4",width:"17.6",height:"14.8",rx:"2",opacity:".3"}),'
        'r.jsx("path",{d:"M3.2 7.4a2 2 0 0 1 2-2h13.6a2 2 0 0 1 2 2V10H3.2z"}),'
        'r.jsx("path",{d:"M12.9 12.6h-1.8v3.5l2.7 1.6.9-1.5-1.8-1z"})]})',
    "grid":
        'grid:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("rect",{x:"3.2",y:"4.2",width:"8.2",height:"15.6",rx:"1.6"}),'
        'r.jsx("rect",{x:"13.2",y:"4.2",width:"7.6",height:"6.8",rx:"1.6",opacity:".38"}),'
        'r.jsx("rect",{x:"13.2",y:"13",width:"7.6",height:"6.8",rx:"1.6",opacity:".38"})]})',
    "rss":
        'rss:r.jsxs("g",{fill:"none",stroke:"currentColor",strokeWidth:"2.6",'
        'strokeLinecap:"round",children:['
        'r.jsx("path",{d:"M5 11.4a8.2 8.2 0 0 1 8.2 8.2",opacity:".4"}),'
        'r.jsx("path",{d:"M5 5.4a14.2 14.2 0 0 1 14.2 14.2"}),'
        'r.jsx("circle",{cx:"5.6",cy:"18.6",r:"1.4",fill:"currentColor",stroke:"none"})]})',
    "folder":
        'folder:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("path",{d:"M12 2.8 21 7.2 12 11.6 3 7.2z"}),'
        'r.jsx("path",{d:"M12 13.6 4.6 10l-1.6.8L12 15.2l9-4.4-1.6-.8zM12 '
        '18.2 4.6 14.6l-1.6.8L12 19.8l9-4.4-1.6-.8z",opacity:".42"})]})',
    "cog":
        'cog:r.jsxs("g",{fill:"currentColor",children:['
        'r.jsx("rect",{x:"3",y:"7",width:"18",height:"2.2",rx:"1.1",opacity:".42"}),'
        'r.jsx("rect",{x:"3",y:"14.8",width:"18",height:"2.2",rx:"1.1",opacity:".42"}),'
        'r.jsx("circle",{cx:"15.2",cy:"8.1",r:"2.8"}),'
        'r.jsx("circle",{cx:"8.8",cy:"15.9",r:"2.8"})]})',
}
GAMEGRID = (
    'gamegrid:r.jsxs("g",{fill:"currentColor",children:['
    'r.jsx("rect",{x:"3.4",y:"3.4",width:"7.4",height:"7.4",rx:"1.4",opacity:".42"}),'
    'r.jsx("rect",{x:"13.2",y:"3.4",width:"7.4",height:"7.4",rx:"1.4",opacity:".42"}),'
    'r.jsx("rect",{x:"3.4",y:"13.2",width:"7.4",height:"7.4",rx:"1.4",opacity:".42"}),'
    'r.jsx("path",{d:"M16.9 12.6 20.6 14.8v4.4l-3.7 2.2-3.7-2.2v-4.4z"})]}),'
)

# ── S3 : la barre 2a — préambule injecté (teintes, tracés bords droits,
#         feuille), ancien bloc tb+rangée, bloc neuf ────────────────────────
PREAMBLE = (
    'var __dzCatHue={"3d":"var(--cat-3d)","studio3d":"var(--cat-3dstudio)",'
    '"sprites":"var(--cat-sprites)","tiles":"var(--cat-tuiles)",'
    '"materials":"var(--cat-matieres)","cards":"var(--cat-cartes)"};'
    'var __dzCatSVG={'
    '"3d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<path d="M12 2.8 20.6 7.4v9.2L12 21.2 3.4 16.6V7.4z" opacity=".34"/>'
    '<path d="M12 2.8 20.6 7.4 12 11.9 3.4 7.4z"/></svg>\','
    '"studio3d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<rect x="2.6" y="4" width="18.8" height="16" opacity=".3"/>'
    '<path d="M12 7.4 16.2 9.8v4.8L12 17l-4.2-2.4V9.8z"/></svg>\','
    '"sprites":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<rect x="3" y="5" width="18" height="14" opacity=".3"/>'
    '<rect x="5.4" y="7.4" width="5.4" height="4.6"/>'
    '<rect x="13.2" y="12" width="5.4" height="4.6"/></svg>\','
    '"tiles":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<rect x="3" y="4.8" width="8.4" height="6.6"/>'
    '<rect x="12.6" y="4.8" width="8.4" height="6.6" opacity=".34"/>'
    '<rect x="3" y="12.6" width="8.4" height="6.6" opacity=".34"/>'
    '<rect x="12.6" y="12.6" width="8.4" height="6.6"/></svg>\','
    '"materials":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<circle cx="12" cy="12" r="8.6" opacity=".34"/>'
    '<path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/></svg>\','
    '"cards":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<rect x="4.6" y="6.4" width="10.4" height="13.8" opacity=".34" '
    'transform="rotate(-10 9.8 13.3)"/>'
    '<rect x="10.2" y="4.6" width="9.6" height="15"/></svg>\'};'
    '(function(){try{if(document.getElementById("__dzCatBar"))return;'
    'var st=document.createElement("style");st.id="__dzCatBar";st.textContent='
    '".dzCatBar{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;'
    'background:var(--stroke);border:1px solid var(--stroke);margin:14px 24px 0}"+'
    '".dzCatTab{position:relative;height:46px;display:flex;align-items:center;'
    'justify-content:center;gap:7px;border:0;border-radius:0;'
    'background:var(--bg-panel-2);color:var(--ink-soft);cursor:pointer;'
    'font-size:11.5px;font-weight:500;overflow:hidden;'
    'transition:transform var(--dur-press,170ms) var(--ease-pop,ease)}"+'
    '".dzCatTab:hover{background:var(--bg-panel)}"+'
    '".dzCatTab:active{transform:scale(.94) translateY(1px)}"+'
    '".dzCatTab .dzCatIco{display:flex;position:relative}"+'
    '".dzCatTab .dzCatIco svg{width:17px;height:17px;color:var(--cat)}"+'
    '".dzCatTab .dzCatLbl{position:relative}"+'
    '".dzCatTab .dzCatEdge{position:absolute;left:0;right:0;bottom:0;height:2px;'
    'background:var(--cat)}"+'
    '".dzCatTab .dzCatFill{position:absolute;inset:0;background:var(--cat);'
    'transform-origin:left center;transform:scaleX(0);'
    'transition:transform var(--dur-fill,440ms) var(--ease-panel,ease)}"+'
    '".dzCatTab.on .dzCatFill{transform:scaleX(1)}"+'
    '".dzCatTab.on .dzCatIco svg,.dzCatTab.on .dzCatLbl{color:var(--cat-ink,#14181d)}";'
    'document.head.appendChild(st)}catch(e){}})();'
)

OLD_HUB = (
    'function tb(id,lbl){var on=tab===id;return r.jsx("button",{'
    'onClick:function(){setTab(id)},style:{fontSize:12,padding:"6px 14px",'
    'borderRadius:7,border:"1px solid "+(on?"var(--cyan)":"var(--stroke)"),'
    'background:on?"rgba(77,216,230,.12)":"var(--bg-panel)",'
    'color:on?"var(--cyan)":"var(--ink-soft)",cursor:"pointer"},children:lbl},id)}'
    'return r.jsxs("div",{style:{display:"flex",flexDirection:"column",'
    'height:"100%",minHeight:0},children:[r.jsxs("div",{style:{display:"flex",'
    'gap:8,padding:"14px 24px 0",flex:"0 0 auto"},children:['
    'tb("3d","\U0001f9ca 3D"),tb("studio3d","\U0001f419 3D Studio"),'
    'tb("sprites","\U0001f9e9 Sprites 2D"),tb("tiles","\U0001f9f1 Tuiles"),'
    'tb("materials","✨ Matières"),tb("cards","\U0001f0cf Cartes")]},"tabs")'
)

NEW_HUB = (
    'function tb(id,lbl){var on=tab===id;return r.jsxs("button",{'
    'className:"dzCatTab"+(on?" on":""),"aria-pressed":on?"true":"false",'
    'onClick:function(){setTab(id)},style:{"--cat":__dzCatHue[id]||"var(--accent)"},'
    'children:[r.jsx("span",{className:"dzCatFill","aria-hidden":"true"}),'
    'r.jsx("span",{className:"dzCatIco","aria-hidden":"true",'
    'dangerouslySetInnerHTML:{__html:__dzCatSVG[id]||""}}),'
    'r.jsx("span",{className:"dzCatLbl",children:lbl}),'
    'r.jsx("span",{className:"dzCatEdge","aria-hidden":"true"})]},id)}'
    'return r.jsxs("div",{"data-category":tab,style:{display:"flex",'
    'flexDirection:"column",height:"100%",minHeight:0,'
    '"--cat":__dzCatHue[tab]||"var(--accent)"},children:['
    'r.jsxs("div",{className:"dzCatBar",style:{flex:"0 0 auto"},children:['
    'tb("3d","3D"),tb("studio3d","3D Studio"),tb("sprites","Sprites 2D"),'
    'tb("tiles","Tuiles"),tb("materials","Matières"),'
    'tb("cards","Cartes")]},"tabs")'
)


def main():
    s = BUNDLE.read_text(encoding="utf-8")
    if "__dzCatBar" in s:
        raise SystemExit("Bundle déjà patché (__dzCatBar présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)

    # S1 — les 10 entrées nommées de la carte d'icônes
    for name, new in ICONS.items():
        a, b = entry_bounds(s, name, f"S1-{name}")
        s = s[:a] + new + s[b:]
        print(f"S1 {name}: {b - a} -> {len(new)} o")

    # S2 — l'icône propre de Game Assets (clé neuve + entrée Uu)
    a, _ = entry_bounds(s, "zap", "S2-place")
    s = s[:a] + GAMEGRID + s[a:]
    s = apply(s,
              '{id:"assets3d",label:"Game Assets",icon:"grid"',
              '{id:"assets3d",label:"Game Assets",icon:"gamegrid"',
              "S2-uu")
    print("S2 gamegrid: pose +", len(GAMEGRID), "o")

    # S3 — la barre 2a + la pose de --cat sur le conteneur du hub
    s = apply(s, "var __dzManif3d={};function DzGameAssetsHub(",
              "var __dzManif3d={};" + PREAMBLE + "function DzGameAssetsHub(",
              "S3-preambule")
    s = apply(s, OLD_HUB, NEW_HUB, "S3-barre")
    print("S3 barre 2a: ok")

    BUNDLE.write_text(s, encoding="utf-8", newline="")
    print("bundle écrit :", len(s), "o")


if __name__ == "__main__":
    main()
