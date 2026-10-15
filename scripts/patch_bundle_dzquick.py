# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzquick.py
"""Maillon de queue : l'OPTIMISATION DU MENU QUICK (lot « Menus : Quick », t212-t216, 15/10/2026).

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-quick.md. Ce qu'il pose (ancres uniques, relevées le 15/10
sur 46b94085) :
  t212 — l'onglet Voix off noircissait toute l'application.
  - Q1-Q4 : dans `DzQuickVoice`, l'état du réglage de voix s'appelait `dzT` (patch_bundle_voicemodel). Ce nom local
    MASQUAIT la fonction de traduction globale `dzT`, que la traduction L2 (t142) a ensuite appelée dans le même rendu
    → « TypeError: dzT is not a function » au premier rendu. Il devient `dzTu` (le setter `dzSetT` ne masque rien).
  - G0 : `DzQuickGarde`, un ErrorBoundary minimal (classe sur x.Component), posé juste avant Quick (`function um(`) :
    une erreur d'onglet donne un encart d'alerte traduit (« Réessayer », « Revenir à Seedance ») au lieu de démonter
    toute l'application ;
  - G1-G2 : le contenu défilant de Quick est enveloppé par la garde, avec une clé PAR ONGLET (changer d'onglet repart
    d'une garde neuve) ; la barre d'onglets, hors de la garde, reste utilisable ;
  - G3 : une seconde garde autour de l'écran Quick entier (shell) : une erreur du rendu de Quick lui-même laisse le
    rail et les autres écrans utilisables.
  (Le même masquage, dans l'aperçu vivant du Montage — `var dzT=DzTracks.dzCss` de liveSync —, est corrigé dans la
  SOURCE de la couche, frontend/patches/son-vfx-montage.js, rafraîchie par scripts/refresh_layer.py --layer sonvfx.)
  t213 — la barre d'onglets débordait de la colonne de 360 px (« Composition », « Voiced… » coupés).
  - T1 : « Composition » passe par dzT (quick.onglet.composition, EN « Compositing ») ;
  - T2 : icônes seules (`flex:"0 0 auto"`), l'onglet actif garde son libellé dans un span en ellipse (`flex:1`) ;
    `title` (la bulle) et `aria-label` = libellé sur chaque bouton, la bulle « désactivé — clé requise » reste.
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 ».
Clés dzT « quick.garde.* » et « quick.onglet.composition » : frontend/shared/i18n/menus.json (FR/EN), assemblées par scripts/i18n_assembler.py.

Maillon de QUEUE, APRÈS dzespace (dont il sonde le marqueur) ; il garde un .js.bak_dzquick le temps de l'écriture puis
le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzquick` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzespace`.
Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_dzquick.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzquick")
TAG = "dzquick"
MARKER = "class DzQuickGarde "
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzespace", "function DzEspaceSel(", 1),
    ("encartsia", "function dzImgOpts(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# G0 — la garde d'onglet (une ligne : le code injecté par les maillons est minifié à la main)
GARDE = (
    'class DzQuickGarde extends x.Component{constructor(p){super(p);this.state={err:null}}'
    'static getDerivedStateFromError(e){return{err:e}}'
    'componentDidCatch(e,inf){try{console.error("[Quick] onglet",e,inf&&inf.componentStack)}catch(_e){}}'
    'render(){var self=this,e=this.state.err;if(!e)return this.props.children;'
    'var bt={fontSize:11.5,padding:"4px 10px",background:"var(--bg-panel)",color:"var(--ink-strong)",'
    'border:"1px solid var(--stroke)",borderRadius:4,cursor:"pointer"};'
    'return r.jsxs("div",{role:"alert","data-dz-quick-garde":"1",style:{margin:14,padding:12,'
    'border:"1px solid var(--red)",borderRadius:"var(--r-sm)",background:"var(--bg-panel-2)",fontSize:12,'
    'color:"var(--ink)"},children:[r.jsx("strong",{style:{color:"var(--red)",display:"block",marginBottom:6},'
    'children:self.props.ecran?dzT("quick.garde.ecran"):dzT("quick.garde.titre")}),r.jsx("div",{className:"mono",style:{fontSize:11,color:"var(--ink-soft)",'
    'marginBottom:10,wordBreak:"break-word"},children:String(e&&e.message||e).slice(0,200)}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,flexWrap:"wrap"},children:['
    'r.jsx("button",{type:"button",style:bt,onClick:function(){self.setState({err:null})},'
    'children:dzT("quick.garde.reessayer")}),'
    'self.props.onglet!=="seedance"&&r.jsx("button",{type:"button",style:bt,'
    'onClick:function(){self.props.retour&&self.props.retour()},children:dzT("quick.garde.retour")})]})]})}}'
)

PAIRES = [
    # t212 — Q1-Q4 : l'état du réglage de voix ne s'appelle plus dzT
    ('),dzT=dztS[0],dzSetT=dztS[1],',                                                                       # Q1
     '),dzTu=dztS[0],dzSetT=dztS[1],'),
    ('model:dzM,tune:dzT}',                                                                                 # Q2
     'model:dzM,tune:dzTu}'),
    ('settings:dzT&&Object.keys(dzT).length?dzT:void 0',                                                    # Q3
     'settings:dzTu&&Object.keys(dzTu).length?dzTu:void 0'),
    ('value:dzT,onChange:function(t2){dzSetT(t2)',                                                          # Q4
     'value:dzTu,onChange:function(t2){dzSetT(t2)'),
    # t212 — G0 la garde, avant Quick ; G1-G2 le défilant de Quick enveloppé, une clé par onglet
    ('function um({variant:e,activePersona:t}){',                                                           # G0
     GARDE + 'function um({variant:e,activePersona:t}){'),
    ('children:o==="voice"?[dzQpUI(),r.jsx(DzQuickVoice,{},"dzqv")]:[',                                      # G1
     'children:r.jsx(DzQuickGarde,{onglet:o,retour:function(){i("seedance")},'
     'children:o==="voice"?[dzQpUI(),r.jsx(DzQuickVoice,{},"dzqv")]:['),
    ('dzT("quick.prompt.ouvrir_generateur")})]})]})]}),o!=="voice"&&',                                       # G2
     'dzT("quick.prompt.ouvrir_generateur")})]})]})]},"dzqg-"+o)}),o!=="voice"&&'),
    # G3 — une seconde garde autour de l'ÉCRAN Quick dans le shell : une erreur levée par le rendu de Quick lui-même
    # (dzQpUI() est un appel de fonction, pas un composant : la garde d'onglet ne le voit pas) laisse le rail utilisable
    ('s==="quick"&&r.jsx(um,{variant:e,activePersona:z.find(F=>F.id===P)})',                                  # G3
     's==="quick"&&r.jsx(DzQuickGarde,{onglet:"seedance",ecran:!0,'
     'children:r.jsx(um,{variant:e,activePersona:z.find(F=>F.id===P)})},"dzqg-ecran")'),
    # t213 — T1-T2 : la barre d'onglets tient dans la colonne de 360 px. Icônes seules ; `title` (la bulle) et
    # `aria-label` = libellé sur chaque bouton (la bulle « désactivé — clé requise » des onglets sans clé reste) ;
    # l'onglet ACTIF garde son libellé, dans un span en ellipse ; « Composition » passe par dzT
    ('["comp","Composition","dz-cat-composition",',                                                          # T1
     '["comp",dzT("quick.onglet.composition"),"dz-cat-composition",'),
    ('title:je?dzT("quick.onglet.desactive",{nom:Z}):"",style:{flex:1,height:28,padding:"0 8px",'            # T2
     'background:o===B?"var(--bg-panel-2)":"transparent",border:o===B?"1px solid var(--stroke-strong)":'
     '"1px solid transparent",color:je?"var(--ink-muted)":o===B?"var(--ink-strong)":"var(--ink-soft)",'
     'borderRadius:"var(--r-sm)",cursor:je?"not-allowed":"pointer",fontSize:11.5,fontWeight:500,opacity:je?.55:1,'
     'display:"inline-flex",alignItems:"center",justifyContent:"center",gap:6},'
     'children:[r.jsx(X,{name:fe,size:12}),Z]},B))',
     'title:je?dzT("quick.onglet.desactive",{nom:Z}):Z,"aria-label":Z,style:{flex:o===B?1:"0 0 auto",minWidth:0,'
     'overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",height:28,padding:"0 8px",'
     'background:o===B?"var(--bg-panel-2)":"transparent",border:o===B?"1px solid var(--stroke-strong)":'
     '"1px solid transparent",color:je?"var(--ink-muted)":o===B?"var(--ink-strong)":"var(--ink-soft)",'
     'borderRadius:"var(--r-sm)",cursor:je?"not-allowed":"pointer",fontSize:11.5,fontWeight:500,opacity:je?.55:1,'
     'display:"inline-flex",alignItems:"center",justifyContent:"center",gap:6},'
     'children:[r.jsx(X,{name:fe,size:12,style:{flexShrink:0}}),o===B&&r.jsx("span",{style:{minWidth:0,'
     'overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:Z})]},B))'),
]


def lire(p):
    b = p.read_bytes()
    bom = b.startswith(b"\xef\xbb\xbf")
    return b.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, texte, bom):
    p.write_bytes((("﻿" if bom else "") + texte).encode("utf-8"))


def appliquer(s: str) -> str:
    for ancre, remplace in PAIRES:
        n = s.count(ancre)
        if n != 1:
            raise SystemExit(f"[{TAG}] ancre x{n} (attendu 1) : {ancre[:80]!r}")
        s = s.replace(ancre, remplace, 1)
    return s


def defaire(s: str) -> str:
    """L'inverse exact (lu par avant_dzquick dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paires)")
        return
    shutil.copyfile(BUNDLE, BAK)
    try:
        ecrire(BUNDLE, neuf, bom)
    except BaseException:
        shutil.copyfile(BAK, BUNDLE)                    # jamais un bundle à moitié écrit
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
