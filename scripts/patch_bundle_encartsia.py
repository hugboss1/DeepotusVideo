# -*- coding: utf-8 -*-
# scripts/patch_bundle_encartsia.py
"""Maillon de queue : les sélecteurs de modèle du bundle s'alignent sur le catalogue unique (t183, G1, plan
« Génération IA enrichie », 11/10/2026).

Décision de l'utilisateur (11/10/2026) : un modèle dont la clé manque reste TOUJOURS choisissable dans tout
sélecteur, avec son prix et la mention dzT("ia.cle.a_ajouter", {cle}) (« clé X à ajouter dans Réglages ») ; le
serveur refuse le tir en 503 AVANT toute dépense. Seule exception gardée de t182 : un modèle vectoriel (sortie
"svg") n'apparaît jamais dans un sélecteur raster.

Ce qu'il pose (ancres uniques, relevées le 11/10 sur le bundle de origin/main 5195eaee) :
  - E1 deux aides au niveau module, posées juste avant DzImgModelSel : `dzImgLbl(m)` (libellé · prix par image
    · mention de clé) et `dzImgOpts(d)` (les entrées RASTER de `tous` de /api/image-models — le catalogue unique —,
    rangées par voie : fal d'abord, puis votre clé OpenAI… ; repli sur `models` pour un serveur d'avant t182) ;
  - E2 DzImgModelSel (nœuds ImageGen / ImageEdit / Variations / Duel du Studio) lit `dzImgOpts` au lieu de `models` ;
  - E3 DzImageModel (le modèle d'image global : Library, Chapitres, News, Planificateur, Réglages) idem ;
  - E4 DzVideoModelSel (Quick, nœud Seedance) : la mention « · clé manquante » devient « · clé X à ajouter dans
    Réglages » (GEMINI_API_KEY pour Veo Google, FAL_KEY sinon) — le modèle y était déjà choisissable ;
  - E5 DzVoModelSel (Voice Over) : idem avec ELEVENLABS_API_KEY ;
  - E6-E8 Game Assets 3D : la liste des moteurs (`var ENG=[{value:"tripo"…`, prix « ~$ » écrits en dur) et la table
    `var RATES={…}` cèdent la place au registre servi par GET /api/assets3d/engines (libellé, coût texturé et
    brouillon de pricing.estimate, disponibilité) : un cache de MODULE (`dzEngCat`, aucun useState ajouté) rempli
    au montage du panneau — le rendu suivant est demandé par le setter d'état EXISTANT (setPP). Un moteur fal sans
    clé reste choisissable avec la mention « clé FAL_KEY à ajouter dans Réglages » (/assets/3d refuse en 503 avant la
    garde de dépense) ; un moteur local arrêté le dit (« service local à démarrer »). Meshy n'est plus listé ici :
    /assets/3d le refusait toujours (501, il vit dans le 3D Studio) ; une valeur sauvegardée « meshy » garde son
    avertissement.
Le composant `re` (select custom du bundle) n'a pas de groupes : la voie se lit dans l'ORDRE des options et dans
le libellé (« (via fal) », « (OpenAI) ») ; les en-têtes de voie sont dans la liste de la pastille (dz-champ-ia).
Aucun useState ajouté (compte figé 731), aucun DzTracks.

t185 (G3, 11/10/2026) — le port `end` du nœud Seedance (déclaré au registre, lu par AUCUN compilateur jusque-là) est
compilé, et le sélecteur du nœud le sait :
  - E9 `dzFinImg(graphe, id)` au niveau module (posée juste avant WtAll) : le nom de fichier de l'image branchée sur
    l'entrée `end` (même forme que l'entrée `image` : Wt(…,"end") puis dzIsImgNode), sinon undefined ;
  - E10-E13 les quatre compilateurs qui lisent l'entrée `image` d'un Seedance envoient aussi `image_filename_end` :
    le tir seul (Mh -> POST /generate), l'Enchaînement (Concatenate -> créneaux du gabarit tpl_studio_montage), la
    moitié animation de la composition UGC (créneau `anim`) et la Composition spatiale (dzCompose -> créneaux du
    gabarit) ; undefined disparaît du JSON : sans `end` branché, le payload est celui d'avant ;
  - E14 Quick › Composition (POST /generate/composition) envoie l'image de fin du Quick (dzEndOK) côté Seedance ;
    `||void 0` : sans image de fin, la clé est ABSENTE du JSON (payload d'avant, octet pour octet) ;
  - E18-E21 (relecture) : `end` branché sur une image SANS fichier -> refus dzT("studio.compil.fin_vide") dans les
    quatre compilateurs, comme l'image de départ (jamais un rendu muet sans image de fin) ;
  - E15-E17 le panneau du nœud passe `fin` (et `finVide` : `end` branché sur une image sans fichier -> rappel
    dzT("studio.compil.fin_vide") en ambre) à DzVideoModelSel : les modèles qui acceptent une image de fin (`fl` de
    /api/video-models, nature video_fl) viennent EN TÊTE ; si le modèle courant n'en accepte pas, un bandeau
    dzT("studio.video.fl_absent") et l'action en un clic dzT("studio.video.fl") (Veo 3.1 Fast fal) — le modèle ne
    change JAMAIS en silence, seul le clic appelle onChange. Sans `fin` (Quick, Épisodes, Réglages), rendu inchangé.
Les clés studio.video.fl, studio.video.fl_absent, studio.compose.fin, studio.compil.fin_vide vivent dans studio.json (saisie L2, entrées D de
scripts/i18n_l2/studio_ia.py).

Maillon de QUEUE, APRÈS dzguide (dont il sonde le marqueur) ; comme lui, il garde un .js.bak_encartsia le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_encartsia` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici : une seule source), appelé EN TÊTE de `avant_dzguide`.
Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_encartsia.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_encartsia")
TAG = "encartsia"
MARKER = "function dzImgOpts("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzguide", 'g:"/guide/#cardforge"}', 1),
    ("i18nfix", 'dzT("scheduler.mode.assiste")', 1),
    ("dzbiblio", '"data-dz-biblio-barre":"1"', 1),
    ("avnoeuds", "function dzAvCompile(", 1),
    ("avatar", '{id:"avatarlive",', 1),
    ("imagegen", "function DzImgModelSel(", 1),
    ("imagegen", "function dzIsImgNode(", 1),          # t185 : lu par dzFinImg
    ("montage", "function dzEndOK(", 1),               # t185 : lu par E14 (Quick › Composition)
    ("dzglyph", "function __dzGlyphe(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# E6 — l'ancre : la liste écrite en dur dans le bundle (relevée le 11/10 sur 5195eaee)
ENG_AVANT = 'var ENG=[{value:"tripo",label:"Tripo3D v2.5 — game-ready topology, broad export (~$0.30)"},{value:"tripo-h3.1",label:"Tripo H3.1 — face budget + quad topology (~$0.30)"},{value:"hunyuan",label:"Hunyuan3D — cleanest geometry (~$0.16–0.48)"},{value:"trellis",label:"TRELLIS — best textures (~$0.16–0.50)"},{value:"rodin",label:"Hyper3D Rodin — pro realism ($0.40)"},{value:"triposr",label:"TripoSR — fastest/cheapest ($0.07)"},{value:"meshy",label:"Meshy 6 — needs API key (Settings)"}];\r\n'

# E1 — les aides (une ligne, comme le code injecté par imagegen).
# RÈGLES UNIQUES (relecture t183) : `dzPrixUsd` a le CORPS de prixUsd de /shared/dz-modeles-ia.js (la source) et
# `dzVoiesOrdre` son ORDRE ; dz-champ-ia.js porte les mêmes — le banc test_encarts_ia compare les trois et exécute les
# deux chargeurs (bundle, pastille) sur un même jeu. Si la page a chargé DzModelesIA, sa fonction est préférée.
PRIX_CORPS = '{ var v = Number(usd); if (!(v > 0) || !isFinite(v)) return ""; var s = (Math.round(v * 1000) / 1000).toFixed(3); while (/\\.\\d{3,}$/.test(s) && s.charAt(s.length - 1) === "0") s = s.slice(0, -1); return "$" + s + ({ image: "/image", s: "/s", min: "/min", "1k": "/1k" }[unite] || ""); }'
ORDRE_VOIES = '["fal", "openai", "gemini", "elevenlabs", "meshy", "heygen", "local"]'
AIDES = (
    'function dzPrixUsd(usd, unite) ' + PRIX_CORPS
    + 'var dzVoiesOrdre=' + ORDRE_VOIES + ';'
    'function dzPrixImg(m){return((window.DzModelesIA&&window.DzModelesIA.prixUsd)||dzPrixUsd)(m.usd,"image")}'
    'function dzImgLbl(m){return(m.label||m.id)+" · "+(dzPrixImg(m)||dzT("ia.prix.a_mesurer"))'
    '+(m.dispo===false&&m.cle?" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}):"")}'
    'function dzImgOpts(d){var t=(d&&d.tous&&d.tous.length?d.tous:(d&&d.models)||[])'
    '.filter(function(m){return m.sortie!=="svg"});'
    'function rg(m){var k=dzVoiesOrdre.indexOf(m.voie);return k<0?99:k}'
    'return t.map(function(m,i){return[m,i]}).sort(function(a,b){return rg(a[0])-rg(b[0])||a[1]-b[1]})'
    '.map(function(p){return{value:p[0].id,label:dzImgLbl(p[0])}})}'
    # E6-E8 : le registre des moteurs 3D, lu une fois par session (cache de module).
    # REDESSIN (preuve à l'écran du 11/10 : le premier affichage restait sur le libellé de secours jusqu'au clic) :
    # le premier rendu lance la lecture ; une réponse RAPIDE arrive AVANT que l'effet du panneau ait abonné son
    # redessin (effet passif, posé après le dessin) — l'abonnement tardif doit donc redessiner tout de suite si le
    # registre est déjà là, et une réponse (ou un échec) redessine l'abonné. Le redessin passe par le setter d'état
    # EXISTANT du panneau (setPP) : aucun useState ajouté (731).
    # États : EN ATTENTE -> la valeur courante, « chargement… » (jamais « prix à mesurer ») ; ÉCHEC -> la liste de
    # secours (ids, « prix à mesurer »), rien en cache, nouvel essai au rendu suivant (au plus toutes les 4 s).
    'var dzEngCat=null,dzEngEnCours=!1,dzEngEchec=!1,dzEngEssai=0,dzEngFin=null;'
    'var dzEngSecours=["tripo","tripo-h3.1","hunyuan","trellis","rodin","triposr","hunyuan-local"];'
    'function dzEngCharger(fin){if(fin)dzEngFin=fin;if(dzEngCat){fin&&fin();return}if(dzEngEnCours)return;'
    'dzEngEnCours=!0;dzEngEssai=Date.now();'
    'fetch("/api/assets3d/engines").then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json()})'
    '.then(function(d){if(!d||!Array.isArray(d.engines))throw new Error("registre illisible");'
    'dzEngEnCours=!1;dzEngEchec=!1;dzEngCat=d.engines;dzEngFin&&dzEngFin()})'
    '.catch(function(){dzEngEnCours=!1;dzEngEchec=!0;dzEngFin&&dzEngFin()})}'
    'function dzEngTrouve(id){return(dzEngCat||[]).find(function(e){return e.id===id})||null}'
    # un moteur LOCAL est gratuit (« local, gratuit », coût 0) ; un fal dit son coût texturé « ~$ »
    'function dzEngLbl(e){var u=dzPrixUsd(e.usd_texture);'
    'return(e.label||e.id)+" · "+(e.local?dzT("ia.voie.local"):(u?"~"+u:dzT("ia.prix.a_mesurer")))'
    '+(e.available?"":e.local?" · "+dzT("ia.local.a_demarrer"):" · "+dzT("ia.cle.a_ajouter",{cle:"FAL_KEY"}))}'
    'function dzEngOpts(cur){if(!dzEngCat){if(!dzEngEnCours&&(!dzEngEssai||Date.now()-dzEngEssai>4e3))dzEngCharger();'
    'if(!dzEngEchec)return[{value:cur,label:dzT("ia.etat.chargement")}];'
    'var l=dzEngSecours.slice();if(cur&&l.indexOf(cur)<0)l.unshift(cur);'
    'return l.map(function(id){return{value:id,label:id+" · "+dzT("ia.prix.a_mesurer")}})}'
    'return dzEngCat.map(function(e){return{value:e.id,label:dzEngLbl(e)}})}'
)

PAIRES = [
    # E1 + E2 : DzImgModelSel
    ('function DzImgModelSel({value,onChange}){', AIDES + 'function DzImgModelSel({value,onChange}){'),
    ('.concat((mm.models||[]).map(function(m){return{value:m.id,label:m.label}}));'
     'return r.jsx(re,{value:value||"",onChange:onChange,options:opts})}',
     '.concat(dzImgOpts(mm));return r.jsx(re,{value:value||"",onChange:onChange,options:opts})}'),
    # E3 : DzImageModel (le modèle d'image global)
    ('if(d){setModels(d.models||[]);',
     'if(d){setModels(dzImgOpts(d).map(function(o){return{id:o.value,label:o.label}}));'),
    # E4 : DzVideoModelSel — le prix à la règle unique, la mention de clé
    ('var px=v2!=null?" · $"+(Number(v2)>=.1?Number(v2).toFixed(2):Number(v2).toFixed(3))+"/s":"";return m2.label+px+(m2.available?"":dzT("reglages.modeles.cle_manquante"))}',
     'var px=dzPrixUsd(v2,"s")?" · "+dzPrixUsd(v2,"s"):"";return m2.label+px+(m2.available?"":" · "+dzT("ia.cle.a_ajouter",'
     '{cle:m2.provider==="google"?"GEMINI_API_KEY":"FAL_KEY"}))}'),
    # E5 : DzVoModelSel — idem (prix pour mille caractères)
    ('var px=m2.usd_per_char!=null?" · $"+(Number(m2.usd_per_char)*1e3).toFixed(2)+"/1k":"";return m2.label+px+(m2.available?"":dzT("reglages.modeles.cle_manquante"))}',
     'var px=dzPrixUsd(Number(m2.usd_per_char)*1e3,"1k")?" · "+dzPrixUsd(Number(m2.usd_per_char)*1e3,"1k"):"";'
     'return m2.label+px+(m2.available?"":" · "+dzT("ia.cle.a_ajouter",{cle:"ELEVENLABS_API_KEY"}))}'),
    # E6 : Game Assets 3D, la liste des moteurs
    (ENG_AVANT, 'var ENG=dzEngOpts(p.engine);\r\n'),
    # E7 : le coût, lu dans le registre (texturé / brouillon) ; un moteur LOCAL coûte 0, jamais le repli 0,30
    ('var RATES={tripo:p.textures?.3:.2,"tripo-h3.1":p.textures?.3:.2,triposr:.07,hunyuan:p.textures?.48:.16,'
     'trellis:.35,rodin:.4,meshy:.35};\r\nvar cost=(RATES[p.engine]||.3)+(p.multiview?p.views*.03:0);\r\n',
     'var dzE=dzEngTrouve(p.engine);\r\n'
     'var cost=dzE&&dzE.local?0:(dzE&&Number(p.textures?dzE.usd_texture:dzE.usd_brouillon)||.3)+(p.multiview?p.views*.03:0);\r\n'),
    # E8 : le registre chargé au montage du panneau ; le setter EXISTANT redemande un rendu
    ('x.useEffect(function(){refresh();fetch("/api/images")',
     'x.useEffect(function(){refresh();dzEngCharger(function(){setPP(function(o){return Object.assign({},o)})});'
     'fetch("/api/images")'),
]

# t185 (G3) — le port `end` compilé et le sélecteur du nœud Seedance qui le sait (voir l'en-tête)
FIN_IMG = ('function dzFinImg(e,id){var f=Wt(e,id,"end");return f&&dzIsImgNode(f)&&f.props&&f.props.filename||void 0}'
           # `end` branché sur un nœud SANS fichier : refusé (jamais un rendu muet sans image de fin)
           'function dzFinVide(e,id){return!!Wt(e,id,"end")&&!dzFinImg(e,id)}')
FIN_VIDE = 'dzT("studio.compil.fin_vide")'
VEO_FL = "veo-3.1-fast-fal"
SEL_AVANT = ('var opts=[{value:"",label:dzT("reglages.modeles.defaut",{nom:mm.default||"seedance-2.5"})}]'
             '.concat((mm.models||[]).map(function(m2){return{value:m2.id,label:lbl(m2)}}));'
             'return r.jsx("div",{"data-dzvmsel":"1",children:r.jsx(re,{value:value||"",onChange:onChange,options:opts})})}')
SEL_APRES = (
    'var opts=[{value:"",label:dzT("reglages.modeles.defaut",{nom:mm.default||"seedance-2.5"})}]'
    '.concat(dzVmTri(mm.models||[]).map(function(m2){return{value:m2.id,label:lbl(m2)}}));'
    # `fl` (alias de end_image) : le modèle accepte une image de fin ; avec `fin`, ces modèles d'abord
    'function dzVmFl(m2){return!!(m2&&(m2.fl||m2.end_image))}'
    'function dzVmTri(l){return fin||finVide?l.filter(dzVmFl).concat(l.filter(function(m2){return!dzVmFl(m2)})):l}'
    'var sel=r.jsx(re,{value:value||"",onChange:onChange,options:opts});'
    'if(!fin&&!finVide)return r.jsx("div",{"data-dzvmsel":"1",children:sel});'
    # `end` branché sur une image SANS fichier : le panneau le dit avant le lancement (qui serait refusé)
    'if(!fin)return r.jsxs("div",{"data-dzvmsel":"1","data-dzvmfin":"vide",children:[sel,r.jsx("div",{"data-dzvmfinvide":"1",'
    'style:{fontSize:11,marginTop:6,padding:8,background:"var(--amber-soft)",border:"1px solid var(--amber)",'
    'borderRadius:"var(--r-sm)",color:"var(--ink)"},children:dzT("studio.compil.fin_vide")})]});'
    'var cur=value||mm.default||"seedance-2.5",cm=(mm.models||[]).find(function(m2){return m2.id===cur}),'
    'flOk=!cm||dzVmFl(cm),veo=(mm.models||[]).find(function(m2){return m2.id==="' + VEO_FL + '"&&dzVmFl(m2)});'
    'return r.jsxs("div",{"data-dzvmsel":"1","data-dzvmfin":flOk?"oui":"non",children:[sel,'
    'flOk?r.jsx("div",{style:{fontSize:11,marginTop:4,color:"var(--ink-soft)"},children:dzT("studio.compose.fin",{nom:fin})})'
    ':r.jsxs("div",{"data-dzvmflabsent":"1",style:{fontSize:11,marginTop:6,padding:8,background:"var(--amber-soft)",'
    'border:"1px solid var(--amber)",borderRadius:"var(--r-sm)",color:"var(--ink)"},children:['
    'r.jsx("div",{children:dzT("studio.video.fl_absent")}),'
    # le SEUL changement de modèle : au clic, jamais en silence
    'veo?r.jsx("button",{type:"button","data-dzvmfl":"1",style:{marginTop:6,width:"100%",fontSize:12,padding:"5px 10px",'
    'borderRadius:7,cursor:"pointer",background:"var(--bg-panel-2)",border:"1px solid var(--stroke)",color:"var(--ink)"},'
    'onClick:function(){onChange("' + VEO_FL + '")},children:dzT("studio.video.fl")}):null]})]})}'
)
PAIRES += [
    # E9 : l'aide au niveau module, à côté de Wt
    ('function WtAll(e,t,n){', FIN_IMG + 'function WtAll(e,t,n){'),
    # E10 : le tir seul (Mh -> POST /generate)
    ('D.postJson("/generate",{video_model:(h.props&&h.props.model)||void 0,image_filename:b.props.filename,',
     'D.postJson("/generate",{video_model:(h.props&&h.props.model)||void 0,image_filename:b.props.filename,'
     'image_filename_end:dzFinImg(e,h.id),'),
    # E11 : l'Enchaînement (Concatenate), un créneau par Seedance
    ('image_filename:H.props.filename,custom_prompt:(F&&F.props&&F.props.value)||"cinematic motion, deep-sea bioluminescence",duration_s:A,',
     'image_filename:H.props.filename,image_filename_end:dzFinImg(e,j.id),custom_prompt:(F&&F.props&&F.props.value)'
     '||"cinematic motion, deep-sea bioluminescence",duration_s:A,'),
    # E12 : la moitié animation de la composition UGC
    ('N.anim={source_kind:"seedance",seedance:{video_model:(j.props&&j.props.model)||void 0,image_filename:H.props.filename,',
     'N.anim={source_kind:"seedance",seedance:{video_model:(j.props&&j.props.model)||void 0,image_filename:H.props.filename,'
     'image_filename_end:dzFinImg(e,j.id),'),
    # E13 : la Composition spatiale (dzCompose, srcFor)
    ('seedance:{video_model:(g.props&&g.props.model)||void 0,image_filename:img.props.filename,',
     'seedance:{video_model:(g.props&&g.props.model)||void 0,image_filename:img.props.filename,'
     'image_filename_end:dzFinImg(e,g.id),'),
    # E14 : Quick › Composition, l'image de fin du Quick côté Seedance (même règle que l'onglet Seedance)
    ('seedance:{camera_ctrl:dzCam(),video_model:VMQ||void 0,image_filename:w,',
     'seedance:{camera_ctrl:dzCam(),video_model:VMQ||void 0,image_filename:w,image_filename_end:(dzEndOK()?g:"")||void 0,'),
    # E15 : le panneau du nœud Seedance dit au sélecteur l'image de fin branchée
    ('r.jsx(DzVideoModelSel,{value:n.model,onChange:i=>o("model",i)})',
     'r.jsx(DzVideoModelSel,{value:n.model,onChange:i=>o("model",i),fin:g&&g.edges?dzFinImg(g,e.id):void 0,'
     'finVide:g&&g.edges?dzFinVide(g,e.id):!1})'),
    # E18-E21 : `end` branché mais vide -> refus, comme l'image de départ (même mécanisme dans chaque compilateur)
    ('if(!b||!dzIsImgNode(b)||!((c=b.props)!=null&&c.filename))return{ok:!1,error:dzT("studio.compil.image_seedance")};',
     'if(!b||!dzIsImgNode(b)||!((c=b.props)!=null&&c.filename))return{ok:!1,error:dzT("studio.compil.image_seedance")};'
     'if(dzFinVide(e,h.id))return{ok:!1,error:' + FIN_VIDE + '};'),
    ('if(!H||!dzIsImgNode(H)||!(H.props&&H.props.filename))throw new Error(dzT("studio.compil.seedance_image",{n:E+1}));',
     'if(!H||!dzIsImgNode(H)||!(H.props&&H.props.filename))throw new Error(dzT("studio.compil.seedance_image",{n:E+1}));'
     'if(dzFinVide(e,j.id))throw new Error(' + FIN_VIDE + ');'),
    ('if(!H||!dzIsImgNode(H)||!((w=H.props)!=null&&w.filename))return{ok:!1,error:dzT("studio.compil.image_seedance_moitie")};',
     'if(!H||!dzIsImgNode(H)||!((w=H.props)!=null&&w.filename))return{ok:!1,error:dzT("studio.compil.image_seedance_moitie")};'
     'if(dzFinVide(e,j.id))return{ok:!1,error:' + FIN_VIDE + '};'),
    # dzCompose : l'erreur rejoint `errs`, renvoyée avant tout rendu (le créneau reste rempli : pas « connecte une vidéo »)
    ('var pr=Wt(e,g.id,"prompt");', 'var pr=Wt(e,g.id,"prompt");if(dzFinVide(e,g.id))errs.push(' + FIN_VIDE + ');'),
    # E16-E17 : le sélecteur
    ('function DzVideoModelSel({value,onChange}){', 'function DzVideoModelSel({value,onChange,fin,finVide}){'),
    (SEL_AVANT, SEL_APRES),
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


def crlf_homogene(s):
    return s.count("\n") == s.count("\r\n")


def appliquer(s):
    for k, (a, b) in enumerate(PAIRES):
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
    if s2.count(MARKER) != MARKER_ATTENDU:
        raise SystemExit(f"[{TAG}] marqueur x{s2.count(MARKER)} apres application (attendu {MARKER_ATTENDU}).")
    sonder(s2)
    if not crlf_homogene(s2):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes apres application. Aborting.")
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(PAIRES)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
