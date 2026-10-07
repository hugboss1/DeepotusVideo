# -*- coding: utf-8 -*-
# scripts/patch_bundle_assets2d.py
"""Patcher assert-gardé : la carte-lanceur « Assets 2D » du hub Game Assets (t125, spec
docs/superpowers/specs/2026-09-19-sorceress-sprite-suite-design.md, ligne « Lanceur »).

BASELINE : bundle versionné de main après t119 (c75e276b) — la plupart des maillons récents n'ont pas de .bak sur
cette machine, le bundle commis fait foi. Backup dédié : .js.bak_assets2d (état juste avant CE patch), créé au premier
passage. Au prochain bump de version : archiver .bak_version HORS de frontend/dist/assets puis relancer
patch_bundle_version.py seul — `version` reste le DERNIER maillon.

Ce que le patch pose (ancres uniques, mesurées le 07/10/2026) :
  * `DzAssets2D` (défini juste avant `DzGameAssetsHub`) : « Choisir un outil », quatre cartes — Sprite Lab, Tile Lab,
    Pixel (Vectorlab), Card Forge — chacune avec sa vignette (l'icône de sa catégorie), sa phrase, « Ouvrir » et
    « Guide ». « Ouvrir » bascule l'onglet du hub (sprites / tiles / cards) ; Pixel pose la demande à usage unique
    `dz_vl_persona = "pixel"` (lue et effacée par mod-persona du Vectorlab, même origine) puis navigue vers la vue
    vectorlab. « Guide » ouvre le chapitre du guide quand il existe (Card Forge, c18) ; sinon le bouton est GRISÉ avec
    une infobulle qui le dit (un bouton se grise, il ne disparaît pas — et l'aide de ces outils est la tâche t126).
    Pas de vidéos tutorielles (spec : le guide PDF existe).
  * le hub : un onglet « Assets 2D » (`a2d`) entre « 3D Studio » et « Sprites 2D », accepté au montage et par
    l'événement relais `deepotus:assets-subtab` ; sa teinte et son icône dans `__dzCatHue` / `__dzCatSVG`, plus
    celles de la carte Pixel (`--cat-vectoriel`, DESIGN.md §15) ; la grille des onglets passe de 6 à 7 colonnes.
  * `vectorlab` entre dans la liste blanche des vues de `deepotus:navigate` (`Yu`) : sans elle, « Ouvrir » de la
    carte Pixel restait sans effet.

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_assets2d.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_assets2d")
TAG = "assets2d"

MARKER = "function DzAssets2D("
MARKER_ATTENDU = 1

SVG_A2D = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="1.4"/>'
           '<rect x="13" y="3" width="8" height="8" rx="1.4" opacity=".45"/><rect x="3" y="13" width="8" height="8" rx="1.4" '
           'opacity=".45"/><rect x="13" y="13" width="8" height="8" rx="1.4"/></svg>')
SVG_PIXEL = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="15" width="6" height="6"/>'
             '<rect x="9" y="9" width="6" height="6"/><rect x="15" y="3" width="6" height="6"/><rect x="9" y="15" width="6" '
             'height="6" opacity=".35"/><rect x="15" y="9" width="6" height="6" opacity=".35"/></svg>')

ANCRE_DEF = 'function DzGameAssetsHub({variant:e}){'
ANCRE_HUE = '"cards":"var(--cat-cartes)"};var __dzCatSVG={'
ANCRE_INIT = 'return t==="sprites"||t==="tiles"||t==="studio3d"||t==="materials"||t==="cards"?t:"3d"}'
ANCRE_RELAIS = ('if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"||d.subtab==="studio3d"||'
                'd.subtab==="materials"||d.subtab==="cards")setTab(d.subtab)')
ANCRE_ONGLET = 'tb("studio3d","3D Studio"),tb("sprites","Sprites 2D")'
ANCRE_PANNEAU = ':tab==="sprites"?r.jsx("iframe",{src:"/spritelab/"'

CARTE = ('style:{display:"flex",flexDirection:"column",gap:10,padding:16,borderRadius:12,'
         'background:"var(--bg-panel)",border:"1px solid var(--stroke)",minHeight:0}')

DZ_A2D = (
    'function DzAssets2D({go}){'
    'function vl(){try{localStorage.setItem("dz_vl_persona","pixel")}catch(e1){}'
    'window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"vectorlab"}}))}'
    'var C=['
    '{id:"sprites",t:"Sprite Lab",p:"Une image ou une vidéo devient des cadres puis une planche de sprites : directions, '
    'squelette, hitboxes, exports pour le moteur.",o:function(){go("sprites")},g:""},'
    '{id:"tiles",t:"Tile Lab",p:"Tuiles sans raccord, blob 47 / 16, variantes et formes, feuilles exportées vers Tiled, '
    'LDtk et Godot.",o:function(){go("tiles")},g:""},'
    '{id:"pixel",t:"Pixel — Vectorlab",p:"Retouche au pixel : ligne de temps des cadres, tuile iso 2:1 et ses diagonales, '
    'rastériser une image générée.",o:vl,g:""},'
    '{id:"cards",t:"Card Forge",p:"Cartes à jouer : gabarits imprimeur, dos et mire, langues, art en lot, livret.",'
    'o:function(){go("cards")},g:"/guide/fr.html#c18"}];'
    'return r.jsxs("div",{className:"dzA2d",style:{flex:1,minHeight:0,overflow:"auto",padding:"16px 2px"},children:['
    'r.jsx("div",{style:{fontSize:12,letterSpacing:".08em",textTransform:"uppercase",color:"var(--ink-soft)",'
    'marginBottom:12},children:"Choisir un outil"},"t"),'
    'r.jsx("div",{className:"dzA2dG",style:{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(230px,1fr))",'
    'gap:14},children:C.map(function(c){'
    'return r.jsxs("div",{className:"dzA2dC","data-outil":c.id,' + CARTE[:-1] + ',"--cat":__dzCatHue[c.id]||"var(--accent)"},'
    'children:['
    'r.jsx("div",{"aria-hidden":"true",style:{height:72,borderRadius:8,display:"flex",alignItems:"center",'
    'justifyContent:"center",background:"var(--cat-fill,var(--bg-base))",color:"var(--cat)"},'
    'children:r.jsx("span",{style:{width:40,height:40,display:"flex"},'
    'dangerouslySetInnerHTML:{__html:__dzCatSVG[c.id]||""}})},"v"),'
    'r.jsx("div",{style:{fontSize:15,fontWeight:600,color:"var(--ink)"},children:c.t},"n"),'
    'r.jsx("div",{style:{fontSize:12,lineHeight:1.45,color:"var(--ink-soft)",flex:1},children:c.p},"p"),'
    'r.jsxs("div",{style:{display:"flex",gap:8},children:['
    'r.jsx(K,{variant:"primary",size:"sm",onClick:c.o,title:"Ouvrir "+c.t,children:"Ouvrir"},"o"),'
    'c.g?r.jsx("a",{href:c.g,target:"_blank",rel:"noopener",style:{textDecoration:"none"},'
    'children:r.jsx(K,{variant:"outline",size:"sm",title:"Le chapitre « "+c.t+" » du guide",children:"Guide ↗"})},"g")'
    ':r.jsx(K,{variant:"outline",size:"sm",disabled:!0,"aria-disabled":"true",style:{opacity:.45,cursor:"not-allowed"},'
    'title:"Pas encore de chapitre « "+c.t+" » dans le guide",children:"Guide ↗"},"g")]},"a")]},c.id)})},"g")]})}')
# « Guide ↗ » et non « Guide » : le libellé seul est épinglé x1 dans le bundle par test_montage_bundle (EC1, l'entrée
# du guide amont) ; la flèche dit d'ailleurs que le lien ouvre un onglet. `K` ne grise pas un bouton `disabled`
# (opacité 1, curseur main — mesuré à l'écran le 07/10/2026) : le style le fait.

# A7 : la rangée d'onglets est une grille de SIX colonnes fixes (dzdesign) — le septième onglet passait à la ligne
# (mesuré à l'écran, 1280 px : « Cartes » seul sur une seconde rangée).
ANCRE_GRILLE = '.dzCatBar{display:grid;grid-template-columns:repeat(6,1fr);'
# A8 : `deepotus:navigate` n'accepte que les vues de la liste blanche `Yu`, où `vectorlab` manquait (la barre
# latérale l'ouvre par un autre chemin) — « Ouvrir » de la carte Pixel restait sans effet (mesuré à l'écran).
# Effet de bord voulu : `?view=vectorlab` devient une URL d'ouverture valide, comme les autres vues.
ANCRE_VUES = 'Yu=["quick","studio","assets3d","episodes","sonvfx","montage","scheduler","templates","news","library","settings"]'

PATCHES = [
    ("A1-def", ANCRE_DEF, DZ_A2D + ANCRE_DEF, 1),
    ("A2-teintes", ANCRE_HUE,
     '"cards":"var(--cat-cartes)","a2d":"var(--cat-sprites)","pixel":"var(--cat-vectoriel)"};var __dzCatSVG={'
     + '"a2d":\'' + SVG_A2D + '\',"pixel":\'' + SVG_PIXEL + '\',', 1),
    ("A3-init", ANCRE_INIT, ANCRE_INIT.replace('||t==="cards"?', '||t==="cards"||t==="a2d"?'), 1),
    ("A4-relais", ANCRE_RELAIS, ANCRE_RELAIS.replace('||d.subtab==="cards")', '||d.subtab==="cards"||d.subtab==="a2d")'), 1),
    ("A5-onglet", ANCRE_ONGLET, 'tb("studio3d","3D Studio"),tb("a2d","Assets 2D"),tb("sprites","Sprites 2D")', 1),
    ("A6-panneau", ANCRE_PANNEAU, ':tab==="a2d"?r.jsx(DzAssets2D,{go:setTab},"pa2")' + ANCRE_PANNEAU, 1),
    ("A7-grille-7", ANCRE_GRILLE, ANCRE_GRILLE.replace("repeat(6,1fr)", "repeat(7,1fr)"), 1),
    ("A8-vue-vectorlab", ANCRE_VUES, ANCRE_VUES.replace('"settings"]', '"settings","vectorlab"]'), 1),
]

SPEC_CHAR_DELTA = 3407       # mesurés le 07/10/2026 (« — », « ↗ », « à »… : 17 octets de plus que de caractères)
SPEC_BYTE_DELTA = 3424

# les voisins des ancres et les maillons de queue
SONDE_AMONT = [
    ("hub", "function DzGameAssetsHub(", 1),
    ("dzdesign", "var __dzCatHue=", 1),
    ("cardforge", 'tb("cards","Cartes")', 1),
    ("asset3dlod", "function DzLod(", 1),
    ("srclbl", "Object.assign(__dzSrcLbl,", 2),
]


def lire(p):
    """Le mode texte MENT sur les fins de ligne (mémoire du 07/09/2026) : on lit et on écrit en OCTETS."""
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp, _n in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8")) for _t, a, rp, _n in PATCHES)
    return dc, db


def apply(s, anchor, replacement, tag, n=1):
    c = s.count(anchor)
    if c != n:
        raise SystemExit(f"[{tag}] anchor count={c} (want {n}). Aborting.")
    return s.replace(anchor, replacement)


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(f"[garde-chaine] backup aval detecte : {other.name} (plus recent que {bak.name}). "
                             f"Utilise `python scripts/repatch_all.py --from {TAG}`.")


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def main():
    args = sys.argv[1:]
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(f"[{TAG}] parite spec rompue : {dc} car / {db} o, spec {SPEC_CHAR_DELTA} / {SPEC_BYTE_DELTA}.")
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)

    if "--check" in args:
        if s.count(MARKER):
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application "
                             "refusee.")
        sonder(s)
        for tag, a, _r, n in PATCHES:
            if s.count(a) != n:
                raise SystemExit(f"[{TAG}] --check : ancre {tag} x{s.count(a)} (attendu {n}).")
        print(f"[{TAG}] --check OK : {len(PATCHES)} ancres, delta {dc} car / {db} o.")
        return

    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present dans {src.name} : double application refusee.")
    sonder(s)
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    avant_c, avant_o = len(s), len(s.encode("utf-8"))
    for tag, a, r_, n in PATCHES:
        s = apply(s, a, r_, tag, n)
    if s.count(MARKER) != MARKER_ATTENDU:
        raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)} apres application (attendu {MARKER_ATTENDU}).")
    if (len(s) - avant_c, len(s.encode("utf-8")) - avant_o) != (dc, db):
        raise SystemExit(f"[{TAG}] delta mesure != delta spec.")
    ecrire(BUNDLE, s, bom)
    print(f"[{TAG}] applique : {len(PATCHES)} sections, +{dc} car / +{db} o.")


if __name__ == "__main__":
    main()
