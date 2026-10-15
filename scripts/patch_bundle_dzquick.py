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
  t214 — la ligne figée « persona Deepotus prophet » devient un MENU des espaces/personas.
  - P0 : `DzQuickPersona` (useReducer + dzCtUse) liste `GET /api/espaces` (non archivés) avec avatar, nom du persona et
    mode de voix (aucun badge sans voiceMode explicite) ; un choix appelle `dzEspActiver(id)` (espace actif GLOBAL, une
    note le dit) ; « + Nouveau persona… » ouvre Réglages › Espaces ; recharge sur deepotus:espace-refresh ;
  - P1 : il remplace la ligne figée de Quick. Prompt (dzPromptAuto), voix (dzVoixSuit), galerie nm et vibes suivent
    déjà l'espace via dzCtCharger (maillon dzespace) ;
  - P2 : une vibe choisie absente de l'espace retombe sur la première vibe de l'espace (le sélecteur affichait « — »).
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 ».
Clés dzT « quick.garde.* », « quick.onglet.composition » et « quick.persona.* » : frontend/shared/i18n/menus.json (FR/EN), assemblées par scripts/i18n_assembler.py.

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

# t214 — P0 : le menu des personas/espaces de Quick. Les personas des espaces sont lus une fois chacun
# (`/api/espaces/{id}/persona`, cache dzQpPers vidé sur deepotus:espace-refresh) ; le badge de voix ne vient que d'un
# persona écran EXPLICITE (clé `ecran`, ou le preset livré de Deepotus) : le squelette rs() du shell pose « prophet »
# par défaut, on ne le montre pas. Aucun useState (compte figé 731), aucun « aria-label » (le banc des onglets repère
# ses paires ainsi).
QPERSONA = (
    'var dzQpPers={};function dzQpPersona(id){if(dzQpPers[id]!==void 0)return;dzQpPers[id]=null;'
    'fetch("/api/espaces/"+encodeURIComponent(id)+"/persona").then(function(r2){if(!r2.ok)throw new Error("HTTP "+r2.status);'
    'return r2.json()}).then(function(p){dzQpPers[id]=p||{};dzEspAvertir()},function(){dzQpPers[id]={};dzEspAvertir()})}'
    'function dzQpEntree(e,t){var p=dzQpPers[e.id],ec=p&&p.ecran&&p.ecran.id?p.ecran:null;'
    'if(!ec&&e.id==="deepotus"){try{ec=(Array.isArray(rm)?rm:[]).find(function(m){return m.id==="deepotus"})||null}catch(_e){}}'
    'if(e.actif&&t&&(ec?t.id===ec.id:!p))ec=Object.assign({},t,{voiceMode:ec?t.voiceMode:e.id==="deepotus"?t.voiceMode:""});'
    'return{id:e.id,espace:e.nom||e.id,nom:ec&&ec.name||p&&p.display_name||e.nom||e.id,avatar:ec&&ec.avatar||"dz-media-persona",'
    'voix:ec&&ec.voiceMode||"",couleur:e.couleur||"var(--brand)",actif:!!e.actif}}'
    'function DzQuickPersona({p:t}){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{ouvert:!1,busy:!1,err:""}),boite=x.useRef(null);dzCtUse();'
    'x.useEffect(function(){var f=function(){maj({})},g=function(){dzQpPers={};maj({})};dzEspAbonnes.push(f);'
    'window.addEventListener("deepotus:espace-refresh",g);'
    'dzEspCache||dzEspCharger().catch(function(){maj({err:dzT("espaces.erreur.lecture")})});'
    'return function(){dzEspAbonnes=dzEspAbonnes.filter(function(h){return h!==f});'
    'window.removeEventListener("deepotus:espace-refresh",g)}},[]);'
    'var liste=(dzEspCache&&dzEspCache.espaces||[]).filter(function(e){return!e.archive});'
    'x.useEffect(function(){liste.forEach(function(e){dzQpPersona(e.id)})});'
    'x.useEffect(function(){if(!st.ouvert)return;var dehors=function(ev){var b=boite.current;'
    'if(b&&b.contains&&ev&&ev.target&&b.contains(ev.target))return;maj({ouvert:!1})},'
    'echap=function(ev){ev&&ev.key==="Escape"&&maj({ouvert:!1})};document.addEventListener("mousedown",dehors);'
    'document.addEventListener("keydown",echap);return function(){document.removeEventListener("mousedown",dehors);'
    'document.removeEventListener("keydown",echap)}},[st.ouvert]);'
    'var ents=liste.map(function(e){return dzQpEntree(e,t)}),cur=ents.find(function(e){return e.actif})||'
    '(t?{id:t.id,nom:t.name,avatar:t.avatar||"dz-media-persona",voix:"",couleur:"var(--brand)",actif:!0}:null);'
    'function choisir(id){if(!dzEspCache||id===dzEspCache.actif){maj({ouvert:!1});return}maj({ouvert:!1,busy:!0,err:""});'
    'dzEspActiver(id).then(function(){maj({busy:!1})},function(e){maj({busy:!1,err:String(e&&e.message||e)})})}'
    'function nouveau(){maj({ouvert:!1});try{var u=new URL(window.location.href);u.searchParams.set("section","espaces");'
    'window.history.replaceState(null,"",u)}catch(_e){}try{window.dispatchEvent(new CustomEvent("deepotus:navigate",'
    '{detail:{view:"settings",section:"espaces"}}))}catch(_e){}}'
    'function badge(v){return v?r.jsx("span",{className:"mono","data-dz-brut":"1",style:{fontSize:10,color:"var(--ink-muted)",'
    'flexShrink:0},children:v}):null}'
    'function ligne(e,grand){return[r.jsx(X,{name:e.avatar,size:grand?14:12,style:{color:e.couleur,flexShrink:0}},"a"),'
    'r.jsxs("span",{style:{minWidth:0,flex:1,display:"flex",flexDirection:"column",textAlign:"left"},children:['
    'r.jsx("span",{"data-dz-brut":"1",style:{fontSize:11.5,color:"var(--ink-strong)",fontWeight:500,overflow:"hidden",'
    'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:e.nom}),grand&&e.espace&&e.espace!==e.nom&&r.jsx("span",'
    '{"data-dz-brut":"1",style:{fontSize:10,color:"var(--ink-muted)",overflow:"hidden",textOverflow:"ellipsis",'
    'whiteSpace:"nowrap"},children:e.espace})]},"n"),badge(e.voix)]}'
    'return r.jsxs("div",{ref:boite,"data-dz-qp":"1",style:{marginTop:10,position:"relative"},children:['
    'r.jsxs("button",{type:"button","data-dz-qp-ouvrir":"1",title:dzT("quick.persona.choisir"),"aria-haspopup":"listbox",'
    '"aria-expanded":!!st.ouvert,disabled:st.busy||!cur,onClick:function(){maj({ouvert:!st.ouvert})},style:{width:"100%",'
    'display:"flex",alignItems:"center",gap:8,padding:"6px 10px",background:"var(--bg-panel-2)",border:"1px solid '
    'var(--stroke)",borderRadius:"var(--r-sm)",cursor:st.busy?"wait":"pointer",color:"inherit",font:"inherit",'
    'opacity:st.busy?.6:1},children:[r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)",flexShrink:0},'
    'children:dzT("quick.persona.libelle")}),cur?ligne(cur,!1):null,r.jsx(X,{name:"dz-action-deplier",size:12,'
    'style:{color:"var(--ink-muted)",flexShrink:0,transform:st.ouvert?"rotate(180deg)":"none"}})]}),'
    'st.ouvert&&r.jsxs("div",{role:"listbox",style:{position:"absolute",left:0,right:0,top:"calc(100% + 4px)",zIndex:40,'
    'background:"var(--bg-panel)",border:"1px solid var(--stroke-strong)",borderRadius:"var(--r-sm)",'
    'boxShadow:"0 10px 30px rgba(0,0,0,.45)",padding:4,maxHeight:280,overflowY:"auto"},children:['
    'ents.map(function(e){return r.jsxs("button",{type:"button",role:"option","aria-selected":e.actif,'
    '"data-dz-qp-id":e.id,onClick:function(){choisir(e.id)},style:{width:"100%",display:"flex",alignItems:"center",'
    'gap:8,padding:"6px 8px",background:e.actif?"var(--bg-panel-2)":"transparent",border:"0",borderRadius:4,'
    'cursor:"pointer",color:"inherit",font:"inherit"},children:[ligne(e,!0),r.jsx("span",{style:{width:14,flexShrink:0,'
    'display:"inline-flex"},children:e.actif&&r.jsx(X,{name:"dz-action-valider",size:12,style:{color:"var(--brand)"}})})]},'
    '"dzqp-"+e.id)}),r.jsx("div",{style:{height:1,background:"var(--stroke)",margin:"4px 2px"}}),'
    'r.jsx("button",{type:"button","data-dz-qp-nouveau":"1",onClick:nouveau,style:{width:"100%",textAlign:"left",'
    'padding:"6px 8px",background:"transparent",border:"0",borderRadius:4,cursor:"pointer",fontSize:11.5,'
    'color:"var(--brand)"},children:dzT("quick.persona.nouveau")})]}),'
    'st.err&&r.jsx("div",{role:"alert",style:{fontSize:10.5,color:"var(--red)",marginTop:4},children:st.err}),'
    'r.jsx("div",{"data-dz-qp-note":"1",style:{fontSize:10.5,color:"var(--ink-muted)",marginTop:4},'
    'children:dzT("quick.persona.note")})]})}'
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
    # t214 — P0 le menu des personas, posé devant la garde ; P1 il remplace la ligne figée « persona Deepotus prophet »
    ('class DzQuickGarde extends x.Component{',                                                               # P0
     QPERSONA + 'class DzQuickGarde extends x.Component{'),
    ('t&&r.jsxs("div",{style:{marginTop:10,display:"flex",alignItems:"center",gap:8,padding:"6px 10px",'          # P1
     'background:"var(--bg-panel-2)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)"},children:['
     'r.jsx(X,{name:t.avatar||"dz-media-persona",size:12,style:{color:"var(--brand)"}}),r.jsx("span",{style:{fontSize:11,'
     'color:"var(--ink-soft)"},children:"persona"}),r.jsx("span",{style:{fontSize:11.5,color:"var(--ink-strong)",'
     'fontWeight:500},children:t.name}),r.jsx("span",{style:{flex:1}}),r.jsx("span",{className:"mono",style:{fontSize:10,'
     'color:"var(--ink-muted)"},children:t.voiceMode})]})',
     'r.jsx(DzQuickPersona,{p:t},"dzqpers")'),
    # P2 — au changement d'espace, une vibe choisie qui n'existe plus dans l'espace retombe sur la première de l'espace
    # (la génération le faisait déjà via M(), mais le sélecteur affichait « — »)
    # (un effet À PART, posé après celui du prompt : la paire C5 de dzespace reste intacte)
    ('},[dzCvQ]);function M(){',                                                                                # P2
     '},[dzCvQ]);x.useEffect(function(){if(I.length&&!I.some(function(z){return z.id===A}))V(I[0].id)},[dzCvQ]);'
     'function M(){'),
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
