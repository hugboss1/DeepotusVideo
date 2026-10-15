# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzreglages.py
"""Maillon de queue : l'OPTIMISATION DU MENU RÉGLAGES (lot « Menus : Réglages », t219-t224, 15/10/2026).

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-reglages.md. Ce qu'il pose (ancres uniques, relevées le
15/10 sur 7a104ba2) :
  t219 — les pastilles de l'en-tête ouvraient Réglages › Comptes connectés. Elles faisaient `i&&i("settings")` et
  Réglages (`xm`) ne lisait sa rubrique qu'au montage (`vn("section")`, sinon « accounts ») : un Réglages déjà ouvert
  ne bougeait pas non plus.
  - R0 : `dzOuvrirReglages(section, aller)` écrit `?section=` (history.replaceState), émet `dz-reglages-section`
    {section}, puis appelle aller("settings") ; `dzReglagesEcoute(a)` écoute cet évènement (rubriques de `ym`
    seulement). Les deux sont posées devant `xm`, qui monte l'écoute dans un useEffect sans dépendance : Réglages
    déjà ouvert change de rubrique, un Réglages qui s'ouvre lit l'URL ;
  - R1 : la pastille des dépenses ouvre « pricing » (Tarifs et budget) ; R2 : les pastilles des clés (fal / HeyGen /
    voix) ouvrent « keys » (Clés d'API), comme leur bulle l'annonce ;
  - R3-R4 : la palette de commandes : « Réglages — comptes » → accounts, « Réglages — clés » → keys (l'aide est
    appelée APRÈS `n("settings")`, laissé intact : la paire G1 du maillon dzglyph le contient) ;
  - R5 : la bulle des dépenses annonce « Clic → Réglages → Tarifs et budget. ».
  t220 (16/10, relevé sur e9e47154) — Fournisseurs par défaut : les rôles proposaient des NOMS DE CLÉS et restaient
  dans le localStorage (« Enregistré localement ») ; aucun écran ne réglait ANTHROPIC_MODEL / OPENAI_MODEL ; le
  GEMINI_MODEL de Clés d'API était un champ de clé (chez l'utilisateur, il contient sa clé AIza…).
  - F0 : DzFournDefauts / DzFournModele / DzCleVersDefauts (+ aides dzFd*) devant `Em` ;
  - F1 : l'aide de la rubrique (fin du « Enregistré localement ») ; F2 : les lignes de rôle locales → DzFournDefauts
    (l'état `n` et la liste `s` d'Em restent, morts : retirer leur useState changerait le compte figé) ;
  - F3 : Diagnostic, l'alerte « contient une clé, pas un nom de modèle » à la place de l'aperçu ;
  - F4 : Clés d'API, la ligne GEMINI_MODEL renvoie vers Fournisseurs par défaut.
  Aucune paire ne doit recopier un remplacement de scripts/dzglyph_paires.json (vu : `size:"sm",icon:
  "dz-action-enregistrer",onClick` en est un — l'ordre des props de nos boutons l'évite).
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 ».
Clés dzT « reglages.pastille.* » (zone.objet.role : pas de « _ » dans la zone) : frontend/shared/i18n/menus.json (FR/EN), assemblées par scripts/i18n_assembler.py.

Maillon de QUEUE, APRÈS dzquick (dont il sonde le marqueur) ; il garde un .js.bak_dzreglages le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzreglages` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzquick`.
Les tâches suivantes du lot (t220-t223) AJOUTENT leurs paires ici : défaire d'abord avec le patcher de HEAD, éditer
PAIRES, puis réappliquer. Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_dzreglages.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzreglages")
TAG = "dzreglages"
MARKER = "function dzOuvrirReglages("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzquick", "class DzQuickGarde ", 1),
    ("dzespace", "function DzEspaceSel(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# R0 — les deux aides, posées devant Réglages (une ligne : le code injecté par les maillons est minifié à la main)
AIDES = (
    'function dzOuvrirReglages(section,aller){try{var u=new URL(window.location.href);u.searchParams.set("section",'
    'section);window.history.replaceState(null,"",u)}catch(_e){}try{window.dispatchEvent(new CustomEvent('
    '"dz-reglages-section",{detail:{section:section}}))}catch(_e){}if(typeof aller==="function")aller("settings")}'
    'function dzReglagesEcoute(aller){function h(ev){var k=ev&&ev.detail&&ev.detail.section;if(ym.includes(k))'
    'aller(k)}window.addEventListener("dz-reglages-section",h);return function(){'
    'window.removeEventListener("dz-reglages-section",h)}}'
)

XM = ('function xm({variant:e,personas:t=[],activePersonaId:n,setActivePersonaId:o,savePersona:i}){const[s,a]='
      'x.useState(()=>{const u=vn("section");return ym.includes(u)?u:"accounts"}),[l,d]=x.useState(null);')

PAIRES = [
    (XM,                                                                                                    # R0
     AIDES + XM + 'x.useEffect(function(){return dzReglagesEcoute(a)},[]);'),
    ('r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>i&&i("settings"),',                           # R1
     'r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>dzOuvrirReglages("pricing",i),'),
    ('title:dzT("coque.entete.ouvrir_cles"),onClick:()=>i&&i("settings"),',                                  # R2
     'title:dzT("coque.entete.ouvrir_cles"),onClick:()=>dzOuvrirReglages("keys",i),'),
    # R3-R4 : `n("settings")` reste tel quel (la paire G1 du maillon dzglyph le contient) ; l'aide vient APRÈS lui,
    # dans le même gestionnaire : l'URL est écrite avant que Réglages ne se monte (le rendu suit le gestionnaire)
    ('ings"),t()}},{l:dzT("coque.palette.reglages_cles")',                                                   # R3
     'ings"),t(),dzOuvrirReglages("accounts")}},{l:dzT("coque.palette.reglages_cles")'),
    ('ings"),t()}}].filter(l=>!i||',                                                                         # R4
     'ings"),t(),dzOuvrirReglages("keys")}}].filter(l=>!i||'),
    ('titre:t+dzT("reglages.depenses.clic_reglages")',                                                      # R5
     'titre:t+dzT("reglages.pastille.clic_tarifs")'),
]

# ── t220 : Fournisseurs par défaut branchés sur le serveur, modèles de texte réglables ─────────────────────────────
# F0 — les composants, posés devant `Em` (Réglages › Fournisseurs par défaut). Aucun useState (useReducer seulement).
#   DzFournDefauts : les lignes Image → vidéo / Avatar / Voix off en LECTURE SEULE (la clé servie et son état, lus sur
#   la santé du shell comme avant), les rôles Résumé News / Planificateur (un MOTEUR, liste du serveur, "" = auto,
#   POST /api/settings/provider-defaults puis relecture), une ligne DzFournModele par moteur configuré (ou fautif).
#   DzFournModele : la liste du fournisseur (GET …/modeles) + une saisie libre liées à la même valeur, Tester (POST
#   …/tester, ne dépense rien) et Enregistrer. Un modèle fautif (clé collée) n'est JAMAIS montré : champ vide, bord
#   rouge, alerte « contient une clé, pas un nom de modèle » ; Enregistrer reste actif (vide = défaut du code).
#   DzCleVersDefauts : la ligne « Gemini — modèle » de Clés d'API renvoie vers cette rubrique.
COMPOSANTS_F = (
    'function dzFdJson(R){return R.json().catch(function(){return{}}).then(function(d){if(!R.ok)throw new Error('
    'String(d&&d.detail||("HTTP "+R.status)));return d})}'
    'function dzFdPoster(corps){return fetch("/api/settings/provider-defaults",{method:"POST",headers:{"Content-Type":'
    '"application/json"},body:JSON.stringify(corps)}).then(dzFdJson)}'
    'function dzFdNom(d,id){var m=((d&&d.moteurs)||[]).find(function(x){return x.moteur===id});return m?m.nom:id}'
    'function dzFdTete(titre,aide){return r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:'
    '"var(--ink-strong)"},children:titre}),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)"},children:aide})]})}'
    'var dzFdLigne={display:"grid",gridTemplateColumns:"260px 1fr auto",gap:14,alignItems:"center",padding:"14px 18px",'
    'borderTop:"1px solid var(--stroke)"};'
    'function DzFournModele({m:m,relire:relire}){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,n)},{v:m.modele||"",liste:null,lisible:!1,msg:"",ton:"",busy:!1}),'
    'st=rs[0],maj=rs[1];'
    'x.useEffect(function(){var on=!0;fetch("/api/settings/provider-defaults/modeles?moteur="+encodeURIComponent(m.moteur))'
    '.then(dzFdJson).then(function(d){on&&maj({liste:d.modeles||[],lisible:!!d.lisible})}).catch(function(){on&&maj({liste:[],'
    'lisible:!1})});'
    'return function(){on=!1}},[m.moteur]);x.useEffect(function(){maj({v:m.modele||""})},[m.modele,m.fautif]);'
    'function fini(msg,ton){maj({busy:!1,msg:msg,ton:ton})}'
    'function enregistrer(){var c={};c[m.moteur]=st.v.trim();maj({busy:!0,msg:""});dzFdPoster({modeles:c}).then(function(){'
    'fini(dzT("commun.etat.enregistre"),"green");relire()}).catch(function(e){fini(String(e&&e.message||e),"red")})}'
    'function tester(){maj({busy:!0,msg:""});fetch("/api/settings/provider-defaults/tester",{method:"POST",headers:'
    '{"Content-Type":"application/json"},body:JSON.stringify({moteur:m.moteur,modele:st.v.trim()})}).then(dzFdJson)'
    '.then(function(d){fini({connu:dzT("reglages.fournisseurs.test_connu"),inconnu:dzT("reglages.fournisseurs.test_inconnu"),'
    'non_verifiable:dzT("reglages.fournisseurs.test_non_verifiable")}[d.etat]||String(d.etat),d.ok===!0?"green":'
    'd.ok===!1?"red":"amber")})'
    '.catch(function(e){fini(String(e&&e.message||e),"red")})}'
    'var liste=st.liste||[],opts=liste.map(function(n){return{value:n,label:n}});'
    'if(st.v&&liste.indexOf(st.v)<0)opts=[{value:st.v,label:st.v}].concat(opts);'
    'if(!opts.length)opts=[{value:"",label:st.liste===null?dzT("reglages.commun.chargement"):"—"}];'
    'var change=st.v.trim()!==(m.modele||"")||m.fautif;'
    'return r.jsxs("div",{"data-dzfourn":"modele-"+m.moteur,style:Object.assign({},dzFdLigne,{gridTemplateColumns:'
    '"260px 1fr"}),children:['
    'dzFdTete(dzT("reglages.fournisseurs.modele_de",{moteur:m.nom}),r.jsxs("span",{children:[r.jsx("span",{className:'
    '"mono",children:m.cle_modele}),m.fautif?r.jsx("span",{"data-dzfourn":"alerte",style:{color:"var(--red)"},children:'
    '" · "+dzT("reglages.fournisseurs.cle_dans_modele")}):null]})),'
    'r.jsxs("div",{style:{minWidth:0},children:[r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",minWidth:0},children:['
    'r.jsx("div",{style:{flex:"1 1 0",minWidth:0},children:r.jsx(re,{value:st.v,options:opts,onChange:function(v){'
    'maj({v:v||"",msg:""})}})}),'
    'r.jsx("input",{"data-dzfourn":"saisie",value:st.v,placeholder:dzT("reglages.fournisseurs.saisir_nom"),'
    'onChange:function(e){maj({v:e.target.value,msg:""})},style:{flex:"1 1 0",minWidth:110,boxSizing:"border-box",'
    'background:"var(--bg-base)",border:"1px solid "+(m.fautif?"var(--red)":"var(--stroke)"),borderRadius:"var(--r-sm)",'
    'padding:"6px 10px",color:"var(--ink-strong)",fontFamily:"var(--f-mono)",fontSize:12}}),'
    'r.jsx(K,{variant:"outline",size:"sm",onClick:tester,disabled:st.busy||!st.v.trim(),children:dzT("reglages.diag.tester")}),'
    'r.jsx(K,{variant:"primary",icon:"dz-action-enregistrer",size:"sm",onClick:enregistrer,disabled:st.busy||!change,'
    'children:dzT("reglages.commun.enregistrer")})]}),'
    'r.jsx("div",{"data-dzfourn":"etat",style:{fontSize:10.5,marginTop:6,color:st.ton==="red"?"var(--red)":'
    'st.ton==="green"?"var(--green)":st.ton==="amber"?"var(--amber)":"var(--ink-muted)"},children:st.msg||(st.liste===null'
    '?"…":st.lisible?dzT("reglages.fournisseurs.n_modeles",{n:liste.length}):dzT("reglages.fournisseurs.liste_illisible"))})]})]})}'
    'function DzFournDefauts({cles:t}){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,n)},{d:null,msg:"",err:!1}),st=rs[0],maj=rs[1];'
    'function charger(){return fetch("/api/settings/provider-defaults").then(dzFdJson).then(function(d){maj({d:d})})'
    '.catch(function(e){maj({msg:String(e&&e.message||e),err:!0})})}'
    'x.useEffect(function(){charger()},[]);'
    'function role(id,v){var c={};c[id]=v;maj({msg:""});dzFdPoster(c).then(function(){maj({msg:dzT("commun.etat.enregistre"),'
    'err:!1});charger()}).catch(function(e){maj({msg:String(e&&e.message||e),err:!0})})}'
    'var d=st.d,SV=[["video","reglages.defauts.video","reglages.defauts.video_aide","FAL_KEY"],["avatar",'
    '"reglages.defauts.avatar","reglages.defauts.avatar_aide","HEYGEN_API_KEY"],["voice","reglages.defauts.voix_off",'
    '"reglages.defauts.voix_off_aide","ELEVENLABS_API_KEY"]],RO=[["summarizer","reglages.defauts.resume",'
    '"reglages.defauts.resume_aide"],["planner","reglages.defauts.planif","reglages.defauts.planif_aide"]];'
    'return r.jsxs(r.Fragment,{children:['
    '...SV.map(function(s){var pose=(t||[]).includes(s[3]);return r.jsxs("div",{"data-dzfourn":"service-"+s[0],'
    'style:dzFdLigne,children:[dzFdTete(dzT(s[1]),dzT(s[2])),r.jsx("span",{className:"mono",style:{fontSize:11.5,'
    'color:"var(--ink-soft)"},children:s[3]}),r.jsx(te,{tone:pose?"green":"red",dot:!0,children:pose?'
    'dzT("reglages.defauts.pret"):dzT("reglages.defauts.manquant")})]},"s-"+s[0])}),'
    '...RO.map(function(ro){var R=(d&&d.roles&&d.roles[ro[0]])||{},dispo=R.available||[],pref=R.preference||"",'
    'opts=[{value:"",label:dzT("reglages.fournisseurs.auto",{moteur:R.active?dzFdNom(d,R.active):"—"})}].concat('
    'dispo.map(function(id){return{value:id,label:dzFdNom(d,id)}}));'
    'if(pref&&dispo.indexOf(pref)<0)opts.push({value:pref,label:dzFdNom(d,pref)+dzT("reglages.defauts.indisponible")});'
    'return r.jsxs("div",{"data-dzfourn":"role-"+ro[0],style:dzFdLigne,children:[dzFdTete(dzT(ro[1]),dzT(ro[2])),'
    '!d?r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)"},children:dzT("reglages.commun.chargement")}):'
    'dispo.length===0&&!pref?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},children:dzT("reglages.defauts.aucune_cle")}):'
    'r.jsx(re,{value:pref,options:opts,onChange:function(v){role(ro[0],v)}}),'
    'r.jsx(te,{tone:R.active?"green":"red",dot:!0,children:R.active?dzFdNom(d,R.active):dzT("reglages.defauts.manquant")})]},'
    '"r-"+ro[0])}),'
    '...((d&&d.moteurs)||[]).filter(function(m){return m.configure||m.fautif}).map(function(m){'
    'return r.jsx(DzFournModele,{m:m,relire:charger},"m-"+m.moteur)}),'
    'st.msg?r.jsx("div",{"data-dzfourn":"msg",style:{padding:"8px 18px",borderTop:"1px solid var(--stroke)",fontSize:11.5,'
    'color:st.err?"var(--red)":"var(--green)"},children:st.msg},"msg"):null]})}'
    'function DzCleVersDefauts({k:k,c:c}){return r.jsxs("div",{"data-dzfourn":"vers-defauts",style:{display:"grid",'
    'gridTemplateColumns:"180px minmax(0,1fr) auto",gap:14,alignItems:"center",padding:"14px 18px",borderTop:c?'
    '"1px solid var(--stroke)":"none"},children:[r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:'
    '"var(--ink-strong)"},children:k.label}),r.jsx("div",{className:"mono",style:{fontSize:10.5,color:"var(--ink-muted)"},'
    'children:k.k})]}),r.jsx("div",{style:{fontSize:11.5,color:"var(--ink-soft)"},children:'
    'dzT("reglages.fournisseurs.se_regle_ailleurs")}),r.jsx(K,{variant:"outline",size:"sm",onClick:function(){'
    'dzOuvrirReglages("defaults")},children:dzT("commun.action.ouvrir")})]})}'
)

EM = 'function Em(){const e=bt(),t=Fu.filter('
LIGNES_ROLES = (
    '...s.map((a,l)=>{const d=a.options.filter(f=>t.includes(f)),u=n[a.id]||d[0]||"";return r.jsxs("div",{style:'
    '{display:"grid",gridTemplateColumns:"260px 1fr auto",gap:14,alignItems:"center",padding:"14px 18px",borderTop:'
    '"1px solid var(--stroke)"},children:[r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:'
    '"var(--ink-strong)"},children:a.label}),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)"},children:a.hint})]'
    '}),d.length===0?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},children:dzT("reglages.defauts.aucune_cle")}):'
    'r.jsx(re,{value:u,options:d.map(f=>({value:f,label:f})),onChange:f=>i(a.id,f)}),r.jsx(te,{tone:d.length?"green":"red",'
    'dot:!0,children:d.length?dzT("reglages.defauts.pret"):dzT("reglages.defauts.manquant")})]},a.id)})'
)
DIAG_APERCU = ("'var(--ink-muted)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'},title:t?"
               "String(t.message||''):c.apercu,children:t?String(t.message||''):(c.apercu||'')})")
CLES_LIGNE = 'children:Fu.map((k,c)=>{const p=!!(e!=null&&e[k.health]),h=g[k.k];'

PAIRES += [
    (EM, COMPOSANTS_F + EM),                                                                                # F0
    ('dzT("reglages.defauts.aide_1"),r.jsx("span",{className:"mono",children:"backend/.env"}),'              # F1
     'dzT("reglages.defauts.aide_2")',
     'dzT("reglages.fournisseurs.aide")'),
    (LIGNES_ROLES, 'r.jsx(DzFournDefauts,{cles:t},"dzfourn")'),                                             # F2
    (DIAG_APERCU,                                                                                           # F3
     "(c.alerte?'var(--red)':'var(--ink-muted)'),overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'},"
     "title:t?String(t.message||''):c.apercu,children:t?String(t.message||''):(c.alerte?"
     "dzT(\"reglages.fournisseurs.cle_dans_modele\"):(c.apercu||''))})"),
    (CLES_LIGNE,                                                                                            # F4
     CLES_LIGNE + 'if(k.k==="GEMINI_MODEL")return r.jsx(DzCleVersDefauts,{k:k,c:c},k.k);'),
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
    """L'inverse exact (lu par avant_dzreglages dans _i18n_l1_aide)."""
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
