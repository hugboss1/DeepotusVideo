# -*- coding: utf-8 -*-
# scripts/patch_bundle_avnoeuds.py
"""Maillon de queue : les nœuds Studio « Recast » et « Voix → voix » d'Avatar live (t168b, 10/10/2026 ; spec
docs/superpowers/specs/2026-10-10-higgsfield-genjutsu-inventaire.md, G1 et G2). Les routes existent déjà
(/api/avatar-live/recast et /voix, garde des plafonds comprise) : le Studio les appelle comme il appelle /generate.

Ce qu'il pose (ancres uniques, relevées le 10/10 sur le bundle de main 86333d74) :
  - P1 le catalogue : `Recast` (famille gen) et `VoixVoix` (famille audio), une entrée vidéo `in`, une sortie `out` ;
  - P2 la palette : Recast après Variations, Voix → voix après Loudness ;
  - P3 l'inspecteur : DzAvRecastNode (modèle et son prix, Personnage, préréglage, consigne, résolution) et
    DzAvVoixNode (Personnage à voix clonée ; branché après un Recast, la voix part dans le MÊME job) ;
  - P4 la compilation (Mh) : un graphe qui contient un de ces nœuds part vers sa route AVANT les autres branches
    (sinon un nœud Upload enverrait le graphe vers la composition UGC) ; la source doit être un rendu existant ou
    une vidéo UGC (les deux portent un job) ;
  - P5 les définitions, juste avant Mh ;
  - P6 le devis du graphe (dzStudioOps) : `recast` à la seconde de source et `voix_sts`. La durée vient de la vidéo
    UGC (durationS posé à l'import) ou, pour un rendu existant (qui ne retient que son job), de GET /api/jobs/{id}
    lu par l'inspecteur et rangé dans `sourceDur` ; inconnue -> 30 s pour le Recast (son maximum), 60 s pour la voix ; la voix branchée après un Recast est comptée UNE fois ;
  - P7 la pastille des fournisseurs (fal.ai, ElevenLabs) ; P8 le tarif sur la carte du nœud ;
  - t168c (10/10) : l'interrupteur « Brouillon 480p » du nœud Recast (modèles à graine seulement, d'après le
    catalogue servi) : la route reçoit `brouillon`, le devis compte 480p ; on finalise depuis Avatar live › Recast.
Les hooks passent par l'alias `dzAvUS` (le compte de « x.useState( », sondé par plusieurs bancs, ne bouge pas).
Maillon de QUEUE, APRÈS avatar (dont il sonde le marqueur) ; `.js.bak_avnoeuds` le temps de l'écriture puis
SUPPRIMÉ ; `version` reste le dernier maillon. INVERSE : `avant_avnoeuds` dans backend/tests/_i18n_l1_aide.py, lu
sur les PAIRES d'ici. Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_avnoeuds.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_avnoeuds")
TAG = "avnoeuds"
MARKER = "function dzAvCompile("

SONDE_AMONT = [
    ("avatar", '{id:"avatarlive",', 1),
    ("dzgbar", '"data-dz-gbar":"1"', 1),
    ("dzsched", '"data-dz-debord":"1"', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dzcout", "dzRunMaxTake()", 3),
]

_CAT_A = 'Voiceover:{cat:"audio",title:dzT("studio.catalogue.voix_off_titre")'
_CAT_B = ('Recast:{cat:"gen",title:dzT("avatar.noeud.recast_titre"),desc:dzT("avatar.noeud.recast_desc"),'
          'inPorts:[{id:"in",type:"av"}],outPorts:[{id:"out",type:"av"}],'
          'props:{modele:"remplacer",personnage:"",prereglage:"",consigne:"",resolution:"",brouillon:!1}},'
          'VoixVoix:{cat:"audio",title:dzT("avatar.noeud.voix_titre"),desc:dzT("avatar.noeud.voix_desc"),'
          'inPorts:[{id:"in",type:"av"}],outPorts:[{id:"out",type:"av"}],props:{personnage:""}},')

_PAL_A = '"ImageGen","ImageEdit","Variations"]},{cat:"audio",types:["Voiceover","MusicTrack","AudioMix","Loudness"]}'
_PAL_B = ('"ImageGen","ImageEdit","Variations","Recast"]},{cat:"audio",types:["Voiceover","MusicTrack","AudioMix",'
          '"Loudness","VoixVoix"]}')

_INS_A = ':e.type==="HeyGenAvatar"?r.jsxs(r.Fragment,{children:[r.jsx(DzAvatarPick,{p:n,set:o})'
_INS_B = (':e.type==="Recast"?r.jsx(DzAvRecastNode,{p:n,set:o,graph:g,node:e})'
          ':e.type==="VoixVoix"?r.jsx(DzAvVoixNode,{p:n,set:o,graph:g,node:e})')

_CMP_A = 'if(!t)return{ok:!1,error:dzT("studio.compil.render_manquant")};const n=((u=t.props)==null?void 0:u.format)||"9:16"'
_CMP_B = ('if(!t)return{ok:!1,error:dzT("studio.compil.render_manquant")};{const __av=dzAvCompile(e);if(__av)return __av}'
          'const n=((u=t.props)==null?void 0:u.format)||"9:16"')

_DEF_A = "function Mh(e){var u,f,m,y,w,v,g,k,c,p;"
_DEFS = r"""var dzAvUS=x.useState,dzAvCat=null,dzAvCatP=null;
function dzAvCatLoad(){if(!dzAvCatP)dzAvCatP=Promise.all([fetch("/api/avatar-live/recast/modeles").then(function(q){return q.ok?q.json():null}),fetch("/api/avatar-live/personnages").then(function(q){return q.ok?q.json():null})]).then(function(a){dzAvCat={m:a[0]||{modeles:{},prereglages:[]},p:(a[1]&&a[1].personnages)||[]};return dzAvCat}).catch(function(){dzAvCatP=null;return null});return dzAvCatP}
function dzAvT(k,d){var v=dzT(k);return v===k?d:v}
function dzAvUsdS(v){var t=(Number(v)||0).toFixed(3).replace(/0$/,"");return"$"+t+"/s"}
function dzAvSrc(g,id){try{return Wt(g,id,"in")}catch(_e){return null}}
function dzAvSrcJob(s){return s&&(s.type==="ExistingRender"||s.type==="Upload")&&s.props&&s.props.jobId?{job_id:s.props.jobId}:null}
function dzAvDur(s,d,P){if(!s||!s.props)return d;if(s.type==="Upload"){var v=Number(s.props.durationS);return v>0?v:d}var sd=P&&P.sourceDur;return sd&&sd.job===s.props.jobId&&sd.s>0?sd.s:d}
function dzAvVoixApres(g,rc){return((g&&g.nodes)||[]).find(function(n){if(n.type!=="VoixVoix")return!1;var s=dzAvSrc(g,n.id);return!!s&&s.id===rc.id})||null}
function dzAvBr(P){if(!P.brouillon)return!1;var m=dzAvCat&&(dzAvCat.m.modeles||{})[P.modele];return!m||!!m.brouillon}
function dzAvP(n){return Object.assign({},(Me[n.type]&&Me[n.type].props)||{},n.props||{})}
function dzAvOps(g,n){var P=dzAvP(n),s=dzAvSrc(g,n.id);if(n.type==="Recast"){var sec=Math.min(dzAvDur(s,30,P),30),o=[{kind:"recast",modele:P.modele,resolution:dzAvBr(P)?"480p":(P.resolution||void 0),seconds:sec}];if(dzAvVoixApres(g,n))o.push({kind:"voix_sts",duration_s:sec});return o}if(s&&s.type==="Recast")return[];return[{kind:"voix_sts",duration_s:dzAvDur(s,60,P)}]}
function dzAvCompile(g){var ns=(g&&g.nodes)||[],rc=ns.find(function(n){return n.type==="Recast"}),vv=ns.find(function(n){return n.type==="VoixVoix"});if(!rc&&!vv)return null;if(rc){var P=dzAvP(rc),src=dzAvSrcJob(dzAvSrc(g,rc.id));if(!src)return{ok:!1,error:dzT("avatar.noeud.source_manquante")};var voix=!!dzAvVoixApres(g,rc),b={source:src,modele:P.modele,personnage_id:P.personnage||void 0,resolution:P.resolution||void 0,consigne:P.consigne||void 0,prereglage:P.prereglage||void 0,voix:voix||void 0,brouillon:dzAvBr(P)||void 0};return{ok:!0,summary:dzT(dzAvBr(P)?"avatar.noeud.resume_brouillon":voix?"avatar.noeud.resume_recast_voix":"avatar.noeud.resume_recast"),run:function(){return D.postJson("/avatar-live/recast",b)}}}var P2=dzAvP(vv),src2=dzAvSrcJob(dzAvSrc(g,vv.id));if(!src2)return{ok:!1,error:dzT("avatar.noeud.source_manquante")};if(!P2.personnage)return{ok:!1,error:dzT("avatar.noeud.personnage_manquant")};var b2={source:src2,personnage_id:P2.personnage};return{ok:!0,summary:dzT("avatar.noeud.resume_voix"),run:function(){return D.postJson("/avatar-live/voix",b2)}}}
function dzAvUseCat(){var st=dzAvUS(dzAvCat),c=st[0],setC=st[1];x.useEffect(function(){var on=!0;dzAvCatLoad().then(function(d){on&&d&&setC(d)});return function(){on=!1}},[]);return c}
function dzAvUseDur(graph,node,p,set){var s=dzAvSrc(graph,node.id),jid=s&&s.type==="ExistingRender"&&s.props&&s.props.jobId||"";x.useEffect(function(){if(!jid||(p.sourceDur&&p.sourceDur.job===jid))return;var on=!0;fetch("/api/jobs/"+encodeURIComponent(jid)).then(function(q){return q.ok?q.json():null}).then(function(j){var v=j&&Number(j.duration_real_s);on&&v>0&&set("sourceDur",{job:jid,s:Math.round(v*10)/10})}).catch(function(){});return function(){on=!1}},[jid])}
function dzAvPersos(c,voixSeule){return c.p.map(function(f){var a=!!(f.voix&&f.voix.voice_id);return{value:f.id,label:f.nom+(voixSeule&&!a?" — "+dzT("avatar.noeud.sans_voix"):"")}})}
function DzAvRecastNode({p,set,graph,node}){var c=dzAvUseCat();dzAvUseDur(graph,node,p,set);var ok=!!dzAvSrcJob(dzAvSrc(graph,node.id));if(!c)return r.jsx("div",{style:{padding:"12px 14px",fontSize:12,color:"var(--ink-soft)"},children:dzT("avatar.noeud.chargement")});var M=c.m.modeles||{},m=M[p.modele]||{},prix=m.prix_usd_s||{},rs=Object.keys(prix).filter(function(k){return k!=="source"});var hint=Object.keys(prix).map(function(k){return dzAvUsdS(prix[k])+(k==="source"?"":" "+dzT("avatar.recast.en_res",{res:k}))}).join(" · ");var opM=Object.keys(M).map(function(k){return{value:k,label:dzAvT("avatar.modele."+k,M[k].label)}});var opP=[{value:"",label:dzT("avatar.recast.aucun_perso")}].concat(dzAvPersos(c,!1));var opPre=[{value:"",label:"—"}].concat((c.m.prereglages||[]).map(function(q){return{value:q.id,label:dzAvT("avatar.prereglage."+q.id,q.label)}}));var opR=[{value:"",label:dzT("avatar.recast.res_source")}].concat(rs.map(function(k){return{value:k,label:k}}));return r.jsxs("div",{"data-dzavnode":"recast",style:{padding:"12px 14px"},children:[ok?null:r.jsx("div",{style:{fontSize:11.5,color:"var(--amber)",marginBottom:10},children:dzT("avatar.noeud.source_manquante")}),r.jsx(O,{label:dzT("avatar.recast.modele"),hint:hint,children:r.jsx(re,{value:p.modele,options:opM,onChange:function(v){set("modele",v)}})}),m.personnage===!1?null:r.jsx(O,{label:dzT("avatar.direct.personnage"),children:r.jsx(re,{value:p.personnage||"",options:opP,onChange:function(v){set("personnage",v)}})}),r.jsx(O,{label:dzT("avatar.recast.prereglages"),children:r.jsx(re,{value:p.prereglage||"",options:opPre,onChange:function(v){set("prereglage",v)}})}),m.consigne?r.jsx(O,{label:dzT("avatar.noeud.consigne"),children:r.jsx(le,{value:p.consigne||"",placeholder:"a red leather jacket",onChange:function(v){set("consigne",v)}})}):null,m.brouillon?r.jsx(O,{label:dzT("avatar.brouillon.bouton"),hint:dzT("avatar.noeud.brouillon_aide"),children:r.jsx(Ze,{checked:!!p.brouillon,onChange:function(v){set("brouillon",v)}})}):null,rs.length&&!(p.brouillon&&m.brouillon)?r.jsx(O,{label:dzT("avatar.recast.resolution"),children:r.jsx(re,{value:p.resolution||"",options:opR,onChange:function(v){set("resolution",v)}})}):null,r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",lineHeight:1.45},children:dzT("avatar.noeud.recast_aide")})]})}
function DzAvVoixNode({p,set,graph,node}){var c=dzAvUseCat();dzAvUseDur(graph,node,p,set);var s=dzAvSrc(graph,node.id),apres=!!s&&s.type==="Recast",ok=apres||!!dzAvSrcJob(s);if(!c)return r.jsx("div",{style:{padding:"12px 14px",fontSize:12,color:"var(--ink-soft)"},children:dzT("avatar.noeud.chargement")});return r.jsxs("div",{"data-dzavnode":"voix",style:{padding:"12px 14px"},children:[ok?null:r.jsx("div",{style:{fontSize:11.5,color:"var(--amber)",marginBottom:10},children:dzT("avatar.noeud.source_manquante")}),apres?r.jsx("div",{style:{fontSize:12,color:"var(--ink)",marginBottom:10,lineHeight:1.45},children:dzT("avatar.noeud.voix_apres_recast")}):r.jsx(O,{label:dzT("avatar.direct.personnage"),hint:dzAvUsdS(c.m.voix_usd_s),children:r.jsx(re,{value:p.personnage||"",options:[{value:"",label:"—"}].concat(dzAvPersos(c,!0)),onChange:function(v){set("personnage",v)}})}),r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",lineHeight:1.45},children:dzT("avatar.noeud.voix_aide")})]})}
function DzAvCostTag({node}){var c=dzAvUseCat();if(!c)return"—";if(node.type==="VoixVoix")return dzAvUsdS(c.m.voix_usd_s);var m=(c.m.modeles||{})[dzAvP(node).modele],pr=m&&m.prix_usd_s||{},ks=Object.keys(pr);return ks.length?dzAvUsdS(pr[ks[ks.length-1]]):"—"}
"""
_DEF_B = _DEFS + _DEF_A

_OPS_A = 'else if(T==="AvatarMaster")ops.push({kind:"heygen",minutes:1})});return ops}'
_OPS_B = ('else if(T==="Recast"||T==="VoixVoix")ops.push.apply(ops,dzAvOps(g,n));'
          'else if(T==="AvatarMaster")ops.push({kind:"heygen",minutes:1})});return ops}')

_PRV_A = 'else if(t==="HeyGenAvatar")add("HeyGen");'
_PRV_B = 'else if(t==="HeyGenAvatar")add("HeyGen");else if(t==="Recast")add("fal.ai");else if(t==="VoixVoix")add("ElevenLabs");'

_TAG_A = 'e.type==="HeyGenAvatar"?"$0.21":'
_TAG_B = 'e.type==="Recast"||e.type==="VoixVoix"?r.jsx(DzAvCostTag,{node:e}):e.type==="HeyGenAvatar"?"$0.21":'

PAIRES = [
    (_CAT_A, _CAT_B + _CAT_A),
    (_PAL_A, _PAL_B),
    (_INS_A, _INS_B + _INS_A),
    (_CMP_A, _CMP_B),
    (_DEF_A, _DEF_B),
    (_OPS_A, _OPS_B),
    (_PRV_A, _PRV_B),
    (_TAG_A, _TAG_B),
]


def lire(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def nl(s):
    """Le bundle est en CRLF sur disque : les définitions (sur plusieurs lignes) prennent ses fins de ligne."""
    return "\r\n" if "\r\n" in s else "\n"


def paires(s):
    e = nl(s)
    return [(a.replace("\n", e), b.replace("\n", e)) for a, b in PAIRES]


def crlf_homogene(s):
    return s.count("\n") == s.count("\r\n")


def appliquer(s):
    for k, (a, b) in enumerate(paires(s)):
        c = s.count(a)
        if c != 1:
            raise SystemExit(f"[{TAG}] paire {k} : ancre x{c} (attendu 1) : {a[:80]!r}. Aborting.")
        s = s.replace(a, b, 1)
    return s


def main():
    args = sys.argv[1:]
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application refusee.")
    sonder(s)
    if not crlf_homogene(s):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes dans le bundle d'entree. Aborting.")
    if "--check" in args:
        appliquer(s)
        print(f"[{TAG}] --check OK : {len(PAIRES)} paires uniques.")
        return
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
    s2 = appliquer(s)
    if s2.count(MARKER) != 1:
        raise SystemExit(f"[{TAG}] marqueur x{s2.count(MARKER)} apres application (attendu 1).")
    sonder(s2)
    if not crlf_homogene(s2):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes apres application. Aborting.")
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(PAIRES)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
