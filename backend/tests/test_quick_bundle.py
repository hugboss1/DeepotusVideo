# -*- coding: utf-8 -*-
"""Plan Quick T1 (tache #48 du suivi, 01/10/2026) — « Rouvrir dans Quick » dans le BUNDLE ECRIT (groupe P5qr du
maillon montage). Les chaines sont comptees, et le code est EXECUTE sous node : __dzReopenQuick (recette, repli sur
le job, rendu introuvable) avec un faux fetch, et dzQuickApply avec de faux setters — chaque champ de la recette doit
tomber dans le BON etat de l'ecran Quick (les noms minifies sont le risque).
Temoin positif : le bundle de la base (15c4c12) n'a ni __dzReopenQuick ni quick_recipe.
Run (depuis backend/) : & $PY tests/test_quick_bundle.py"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_RACINE = pathlib.Path(__file__).resolve().parents[2]
_BUNDLE = _RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


s = _BUNDLE.read_bytes().decode("utf-8")
r0 = subprocess.run(["git", "show", "15c4c12:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(_RACINE))
s0 = r0.stdout.decode("utf-8") if r0.returncode == 0 else ""
i_um = s.find("function um(")
um = s[i_um:s.find("\nfunction ", i_um + 20) if s.find("\nfunction ", i_um + 20) > 0 else i_um + 200000]

print("\n[T] temoin")
check("T1 la base n'a ni __dzReopenQuick ni quick_recipe", bool(s0) and "__dzReopenQuick" not in s0 and "quick_recipe" not in s0)

print("\n[A] le bundle ecrit")
# __dzSendTo 2 -> 3 (t139, 08/10/2026) : patch_bundle_plenvoi expose le menu aux labs en iframe (window.__dzEnvoyerVers)
check("A1 l'amont est intact (Quick unique, pickers et envois)", s.count("function um(") == 1 and s.count("__dzLibPicker") == 11
      and s.count("__dzSendTo") == 3)
check("A2 __dzQuickStart 3 -> 4 (dzQuickApply pose le global quand les images ne sont pas chargees)", s.count("__dzQuickStart") == 4)
check("A3 __dzReopenQuick : definition + modal + carte de la file", s.count("__dzReopenQuick") == 3 and s.count("function __dzReopenQuick(") == 1
      and s.count("function __dzQuickFromJob(") == 1)
check("A4 les trois payloads portent la recette EN TETE", s.count("quick_recipe:dzQuickRecipe()") == 3
      and "je={quick_recipe:dzQuickRecipe(),camera_ctrl:dzCam(),video_model:VMQ||void 0,image_filename:w," in s
      and 'D.postJson("/generate/heygen",{quick_recipe:dzQuickRecipe(),avatar_id:C,' in s
      and 'D.postJson("/generate/composition",{quick_recipe:dzQuickRecipe(),seedance:{camera_ctrl:dzCam(),video_model:' in s)
check("A5 l'evenement : emis par le helper, ecoute par Quick (et retire au demontage)", s.count('"deepotus:quick-recipe"') == 3
      and 'window.removeEventListener("deepotus:quick-recipe",onR)' in s)
# t141 (08/10) : la traduction L1 passe ces libelles par dzT("cle") ; epingles par leur cle, et chaque cle rend le
# francais d'avant
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402
# t142 (09/10) : la traduction L2 passe les textes de Quick par dzT (globale) ; chaque script node recoit le prelude,
# dans sa propre portee (son `var window` ne masque pas celui des harnais), en francais : les attentes restent vraies
PRELUDE = "(function(){\n" + AIDE.PRELUDE_DZT + "\n})();\n"
check("A6 le bouton de la Bibliotheque (renders seulement) et l'icone de la file, avec un title",
      'm.kind==="render"&&m.jobId&&r.jsx(K,{variant:"ghost",size:"sm",icon:"dz-action-rouvrir-quick",title:dzT("biblio.detail.rouvrir_quick_aide")' in s
      and AIDE.fr("biblio.detail.rouvrir_quick_aide").startswith("Rouvrir ce rendu dans Quick")
      and 'children:dzT("biblio.detail.rouvrir_quick")},"dzquick")' in s
      and AIDE.fr("biblio.detail.rouvrir_quick") == "Rouvrir dans Quick"
      and 'm&&r.jsx(se,{name:"dz-action-rouvrir-quick",title:dzT("coque.file.rouvrir_quick"),onClick:function(){__dzReopenQuick(e.id)}})' in s
      and AIDE.fr("coque.file.rouvrir_quick") == "Rouvrir dans Quick (prérempli)")
fn = s[s.find("function __dzReopenQuick("):s.find("function __dzReopenStudio(")]
check("A7 aucun window.alert ni window.prompt dans le groupe", "window.alert" not in fn and "window.prompt" not in fn and "__dzToast(" in fn)

print("\n[N] execution sous node")
node = shutil.which("node")
check("N0 node est present", bool(node))


def fonc(nom, src=s):
    i = src.find(f"function {nom}(")
    prof, j = 0, src.find("{", i)
    for k in range(j, len(src)):
        prof += {"{": 1, "}": -1}.get(src[k], 0)
        if prof == 0:
            return src[i:k + 1]


if node:
    rec_fn = fonc("dzQuickRecipe")
    app_fn = fonc("dzQuickApply")
    SETTERS = "i v k a V dzSetVMQ b z P F Hsrc Q ne W Eng Mimg Mp Xp De dzSetSubOn dzSetSubSty dzSetSubLang dzSetSubTxt dzSetSubTr dzSetLipOn dzSetLipFile dzSetCamCtl".split()
    js = "\n".join([fonc("__dzQuickFromJob"), fonc("__dzReopenQuick"), r"""
var toasts=[],navs=[],evts=[],appels=[],reponses={};
globalThis.__dzToast=function(m){toasts.push(m)};globalThis.__dzSendNav=function(t){navs.push(t)};
globalThis.window={dispatchEvent:function(e){evts.push(e)}};globalThis.CustomEvent=function(n,o){this.type=n;this.detail=o&&o.detail};
globalThis.localStorage={setItem:function(){}};
function rep(st,j){return Promise.resolve({status:st,ok:st>=200&&st<300,json:function(){return Promise.resolve(j)}})}
globalThis.fetch=function(u){appels.push(u);var f=reponses[u];return f?f():rep(404,{})};
var attendre=function(){return new Promise(function(r){setTimeout(r,120)})};
var appliques={};
function fabrique(etat){var u=etat.u||[];""" + "".join(f"var {n}=function(x){{appliques['{n}']=x}};" for n in SETTERS) + r"""
 var o=etat.o,w=etat.w,g=etat.g,s=etat.s,A=etat.A,VMQ=etat.VMQ,h=etat.h,_=etat._,N=etat.N,H=etat.H,hsrc=etat.hsrc,C=etat.C,ee=etat.ee,R=etat.R,eng=etat.eng,mimg=etat.mimg,mp=etat.mp,xp=etat.xp,We=etat.We,dzSubOn=etat.dzSubOn,dzSubSty=etat.dzSubSty,dzSubLang=etat.dzSubLang,dzSubTxt=etat.dzSubTxt,dzSubTr=etat.dzSubTr,dzLipOn=etat.dzLipOn,dzLipFile=etat.dzLipFile,dzCamCtl=etat.dzCamCtl||{};
 """ + rec_fn + app_fn + r"""
 return {recette:dzQuickRecipe,appliquer:dzQuickApply}}
(async function(){
 var out={};
 var REC={v:1,tab:"heygen",seedance:{image:"a.png",end:"b.png",prompt:"abysse",vibe:"noir",model:"kling-v3-pro",duration:5,aspect:"1:1",seed:4421,template:"tpl1"},
   heygen:{src:"photo",avatar:"av1",voice:"vx",script:"salut",engine:"iv",image:"m.png",motion:"lent",expr:"haute"},layout:"pip"};
 reponses["/api/jobs/j1/recipe"]=function(){return rep(200,REC)};
 __dzReopenQuick("j1");await attendre();
 out.a={nav:navs.slice(),glob:window.__dzQuickRecipe,evt:evts.length&&evts[0].type,detail:evts.length&&evts[0].detail,toast:toasts.slice(-1)[0]};
 navs=[];evts=[];delete window.__dzQuickRecipe;
 reponses["/api/jobs/j2"]=function(){return rep(200,{provider:"heygen",image_filename:"av9",final_prompt:"le script",aspect_ratio:"16:9",duration_s:8,seed:7})};
 __dzReopenQuick("j2");await attendre();
 out.b={glob:window.__dzQuickRecipe,appels:appels.slice(-2)};
 delete window.__dzQuickRecipe;navs=[];
 __dzReopenQuick("absent");await attendre();
 out.c={nav:navs.slice(),glob:window.__dzQuickRecipe||null,toast:toasts.slice(-1)[0]};
 var ecran=fabrique({o:"seedance",w:"a.png",g:"",s:"abysse",A:"noir",VMQ:"seedance-2",h:10,_:"9:16",N:"42",H:"",hsrc:"avatar",C:"av1",ee:"vx",R:"txt",eng:"",mimg:"",mp:"",xp:"",We:"sequential",u:[1],dzSubOn:true,dzSubSty:"pop",dzSubLang:"en",dzSubTxt:"bonjour",dzSubTr:false,dzLipOn:true,dzLipFile:"voix.mp3",dzCamCtl:{zoom:7,tilt:-4}});
 out.recette=ecran.recette();
 ecran.appliquer(REC);out.appliques=appliques;
 appliques={};var vide=fabrique({u:[]});window.__dzQuickStart=null;vide.appliquer({seedance:{image:"z.png"}});out.global=window.__dzQuickStart;out.app2=appliques;
 appliques={};vide.appliquer({tab:"pirate"});out.pirate=appliques;
 appliques={};vide.appliquer({subs:{on:true,style:"neon",lang:"en",text:"t",tr:true}});out.subs=appliques;
 appliques={};vide.appliquer({lip:{on:true,file:"v.mp3"}});out.lip=appliques;
 appliques={};vide.appliquer({cam:{pan:3}});out.cam=appliques;
 appliques={};vide.appliquer({cam:"pirate"});out.camPirate=appliques;
 console.log(JSON.stringify(out));
})();
"""])
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickb_"), "q.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    a = o.get("a") or {}
    check("N1 recette trouvee : global pose, navigation vers quick, evenement emis avec la recette, toast",
          a.get("nav") == ["quick"] and (a.get("glob") or {}).get("tab") == "heygen" and a.get("evt") == "deepotus:quick-recipe"
          and (a.get("detail") or {}).get("layout") == "pip" and "j1" in str(a.get("toast")), str(a)[:300])
    b = (o.get("b") or {}).get("glob") or {}
    check("N2 sans recette : repli sur les colonnes du job (heygen : avatar, script, format)", b.get("tab") == "heygen"
          and b["heygen"]["avatar"] == "av9" and b["heygen"]["script"] == "le script" and b["seedance"]["aspect"] == "16:9"
          and b["seedance"]["seed"] == "7" and (o.get("b") or {}).get("appels") == ["/api/jobs/j2/recipe", "/api/jobs/j2"], str(o.get("b"))[:300])
    c = o.get("c") or {}
    check("N3 rendu introuvable : ni navigation ni global, un toast le dit", c.get("nav") == [] and c.get("glob") is None
          and "introuvable" in str(c.get("toast")), str(c))
    rc = o.get("recette") or {}
    check("N4 dzQuickRecipe lit le BON etat de Quick", rc.get("tab") == "seedance" and rc.get("seedance", {}).get("model") == "seedance-2"
          and rc["seedance"]["prompt"] == "abysse" and rc["seedance"]["seed"] == "42" and rc["heygen"]["script"] == "txt"
          and rc["heygen"]["avatar"] == "av1" and rc["layout"] == "sequential", str(rc)[:300])
    ap = o.get("appliques") or {}
    attendu = {"i": "heygen", "v": "a.png", "k": "b.png", "a": "abysse", "V": "noir", "dzSetVMQ": "kling-v3-pro", "b": 5, "z": "1:1",
               "P": "4421", "F": "tpl1", "Hsrc": "photo", "Q": "av1", "ne": "vx", "W": "salut", "Eng": "iv", "Mimg": "m.png",
               "Mp": "lent", "Xp": "haute", "De": "pip"}
    check("N5 dzQuickApply pose CHAQUE champ dans le bon setter (19 setters)", ap == attendu,
          str({k: (ap.get(k), v) for k, v in attendu.items() if ap.get(k) != v}))
    check("N6 images pas encore chargees : le global __dzQuickStart est pose (la greffe libsend ne l'ecrasera pas)",
          o.get("global") == "z.png" and (o.get("app2") or {}).get("v") == "z.png")
    check("N7 un onglet inconnu n'est pas applique", "pirate" in o and "i" not in o["pirate"])
    check("N8 (tache #50) la recette porte les sous-titres et leur application les restaure (cinq setters)",
          (o.get("recette") or {}).get("subs") == {"on": True, "style": "pop", "lang": "en", "text": "bonjour", "tr": False}
          and o.get("subs") == {"dzSetSubOn": True, "dzSetSubSty": "neon", "dzSetSubLang": "en", "dzSetSubTxt": "t", "dzSetSubTr": True},
          str(o.get("subs")))
    check("N9 (tache #52) la recette porte le lip-sync et son application le restaure",
          (o.get("recette") or {}).get("lip") == {"on": True, "file": "voix.mp3"}
          and o.get("lip") == {"dzSetLipOn": True, "dzSetLipFile": "v.mp3"}, str(o.get("lip")))
    check("N10 (tache #54) la recette porte les curseurs camera ; l'application COMPLETE les six axes a zero ; un objet seulement",
          (o.get("recette") or {}).get("cam") == {"zoom": 7, "tilt": -4}
          and o.get("cam") == {"dzSetCamCtl": {"zoom": 0, "horizontal": 0, "vertical": 0, "pan": 3, "tilt": 0, "roll": 0}}
          and o.get("camPirate") == {}, str(o.get("cam")) + str(o.get("camPirate")))

print("\n[E] l'image de fin grisee avec la raison (tache #49, plan Quick T3, groupe P5ef)")
check("E0 temoin : la base (15c4c12) n'a ni dzEndOK ni le libelle « indisponible »", "dzEndOK" not in s0 and "Image de fin — indisponible" not in s0)
check("E1 un etat, deux fonctions, la table lue sur /api/video-models (rien en dur)", s.count("dzSetEndCaps") == 2
      and s.count("function dzEndOK(") == 1 and s.count("function dzEndWhy(") == 1 and 'fetch("/api/video-models")' in um
      and "kling-v3-pro" not in fonc("dzEndWhy"))
# t142 (09/10) : libelles et title passes par dzT ; epingles par cle, chaque cle rend le francais d'avant
check("E2 le champ porte la raison a la place du select, avec un title",
      'label:dzEndOK()?dzT("quick.source.image_fin"):dzT("quick.source.image_fin_indispo")' in um
      and AIDE.fr("quick.source.image_fin") == "Image de fin (optionnelle)" and AIDE.fr("quick.source.image_fin_indispo") == "Image de fin — indisponible"
      # tache #54 T9 (01/10) : le select et la vraie DropZone dans un meme bloc « dz-fin »
      and 'children:dzEndOK()?r.jsxs("div",{className:"dz-fin",children:[u.length>0?r.jsx(re,{value:g,' in um
      and 'r.jsx("div",{title:dzT("quick.source.fin_aide")' in um
      and AIDE.fr("quick.source.fin_aide") == "Choisissez un modèle qui accepte une image de fin" and 'children:dzEndWhy()})})' in um)
check("E3 le bouton « Parcourir » de fin n'existe que si c'est accepte", 'dzEndOK()&&r.jsx(O,{label:"",children:r.jsx("button"' in um
      and 'titre:dzT("quick.source.image_fin")},k)' in um)
check("E4 le payload n'envoie jamais une fin refusee", 'image_filename_end:(dzEndOK()?g:"")||null,' in s and "image_filename_end:g||null," not in s)
if node:
    i5 = s.find('onChange:function(v2){dzSetVMQ(v2);')
    change = s[i5 + len("onChange:"):s.find('if(dzEndCaps&&dzEndCaps.map[v2]===!1)k("")}', i5) + len('if(dzEndCaps&&dzEndCaps.map[v2]===!1)k("")}')]
    js = r"""
var etat={VMQ:"",caps:null,g:"b.png",vide:[]};
globalThis.localStorage={setItem:function(){}};
function monter(VMQ,dzEndCaps){var k=function(x){etat.vide.push(x)},dzSetVMQ=function(x){etat.VMQ=x};
 """ + fonc("dzEndOK") + fonc("dzEndWhy") + """
 var change=""" + change + r""";
 return {ok:dzEndOK,why:dzEndWhy,change:change,payload:function(g){return(dzEndOK()?g:"")||null}}}
var CAPS={map:{"kling-v3-pro":true,"seedance-2.5":true,"veo-3.1-fast-fal":false},dflt:"seedance-2.5",oui:["Kling v3 Pro","Seedance 2.5"]};
var out={};
var a=monter("",null);out.sansTable=a.ok();
var b=monter("veo-3.1-fast-fal",CAPS);out.veo={ok:b.ok(),why:b.why(),payload:b.payload("b.png")};
var c=monter("kling-v3-pro",CAPS);out.kling={ok:c.ok(),payload:c.payload("b.png")};
var d=monter("",CAPS);out.defaut=d.ok();
var e=monter("inconnu",CAPS);out.inconnu=e.ok();
var f=monter("",{map:CAPS.map,dflt:"veo-3.1-fast-fal",oui:CAPS.oui});out.defautRefuse=f.ok();
etat.vide=[];c.change("veo-3.1-fast-fal");out.versVeo=etat.vide.slice();etat.vide=[];c.change("seedance-2.5");out.versSeed=etat.vide.slice();
console.log(JSON.stringify(out));
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquicke_"), "e.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("E5 table pas encore chargee : le champ reste offert (pas de faux refus)", o.get("sansTable") is True)
    v = o.get("veo") or {}
    check("E6 Veo : refuse, la raison nomme le modele et ceux qui acceptent, le payload n'envoie rien", v.get("ok") is False
          and "« veo-3.1-fast-fal » n’accepte pas d’image de fin" in v.get("why", "") and "Kling v3 Pro, Seedance 2.5" in v.get("why", "")
          and v.get("payload") is None, str(v))
    check("E7 Kling : accepte, la fin part dans le payload", (o.get("kling") or {}) == {"ok": True, "payload": "b.png"}, str(o.get("kling")))
    check("E8 sans modele choisi : le defaut du serveur decide (accepte ou refuse) ; un modele inconnu n'est pas refuse",
          o.get("defaut") is True and o.get("defautRefuse") is False and o.get("inconnu") is True, str(o.get("defautRefuse")))
    check("E9 passer a un modele qui refuse vide la fin ; a un modele qui accepte, non", o.get("versVeo") == [""] and o.get("versSeed") == [],
          f'{o.get("versVeo")} {o.get("versSeed")}')

print("\n[S] sous-titres graves dans Quick (tache #50, plan Quick T4, groupe P5st)")
check("S0 temoin : la base (15c4c12) n'a ni dzSubs (dzSubsExp du Montage est autre) ni « Sous-titrer le rendu »", "function dzSubs(" not in s0 and "subtitles:dzSubs()" not in s0 and "Sous-titrer le rendu" not in s0)
check("S1 un dzSubs, trois payloads (seedance, heygen, composition)", s.count("function dzSubs(") == 1 and s.count("subtitles:dzSubs()") == 3
      and 'template_id:H||null,subtitles:dzSubs(),lipsync:dzLip()},we=await D.postJson("/generate",je)' in s
      # t142 : le message passe par dzT ; son anglais est l'ancien « HeyGen queued. »
      and 'engine:eng||void 0,subtitles:dzSubs()});at(Z.ok?{msg:dzT("quick.lancer.heygen_file")}' in s
      and AIDE.DICO["quick.lancer.heygen_file"]["en"] == "HeyGen queued."
      and 'transition_duration_s:.5,subtitles:dzSubs()});' in s)
check("S2 les preselections viennent de /api/subtitles/presets", 'fetch("/api/subtitles/presets?ratio=9:16")' in um)
check("S3 le bloc : interrupteur, style, langue, texte, case de transcription PAYANTE (seulement sans texte), aide",
      # t142 : libelles par cle, le francais d'avant verifie
      'r.jsx(Ze,{checked:dzSubOn,label:dzT("quick.soustitres.activer"),onChange:dzSetSubOn})' in um
      and AIDE.fr("quick.soustitres.activer") == "Sous-titrer le rendu"
      and 'dzSubOn&&!dzSubTexte()&&r.jsx(O,{children:r.jsx(Ze,{checked:dzSubTr,label:dzT("quick.soustitres.transcrire")' in um
      and AIDE.fr("quick.soustitres.transcrire") == "Transcrire si aucun texte (payant, sous le plafond de dépense)"
      and 'dzSubTexte()?dzT("quick.soustitres.calage_local")' in um
      and AIDE.fr("quick.soustitres.calage_local").startswith("Calage local du texte connu — 0 $"))
if node:
    js = r"""
function monter(st){var o=st.o,R=st.R,dzSubOn=st.on,dzSubSty="pop",dzSubLang="fr",dzSubTxt=st.txt,dzSubTr=st.tr;
 """ + fonc("dzSubTexte") + fonc("dzSubs") + r"""
 return dzSubs()}
console.log(JSON.stringify({
 off:monter({on:false,o:"heygen",R:"x",txt:"",tr:false})===undefined,
 texte:monter({on:true,o:"seedance",R:"",txt:" Bonjour ",tr:true}),
 avatar:monter({on:true,o:"heygen",R:"Le script lu",txt:"",tr:false}),
 seedSansTexte:monter({on:true,o:"seedance",R:"script avatar",txt:"",tr:false}),
 seedTr:monter({on:true,o:"seedance",R:"",txt:"",tr:true})}));
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquicks_"), "s.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("S4 eteint : rien n'est envoye", o.get("off") is True)
    check("S5 texte saisi : calage GRATUIT meme si la case payante est cochee", (o.get("texte") or {}).get("source") == "align"
          and o["texte"]["text"] == "Bonjour", str(o.get("texte")))
    check("S6 onglet avatar sans texte : le script de l'avatar est cale (gratuit)", (o.get("avatar") or {}).get("source") == "align"
          and o["avatar"]["text"] == "Le script lu", str(o.get("avatar")))
    check("S7 Seedance sans texte ni case : align a vide (le serveur dira « aucun texte »), JAMAIS transcribe",
          (o.get("seedSansTexte") or {}).get("source") == "align" and o["seedSansTexte"]["text"] == "", str(o.get("seedSansTexte")))
    check("S8 temoin : sans texte ET case cochee, transcription demandee", (o.get("seedTr") or {}).get("source") == "transcribe", str(o.get("seedTr")))

print("\n[X] prolonger le clip (tache #51, plan Quick T2, groupe P5ex)")
check("X0 temoin : la base (15c4c12) n'a pas __dzExtendClip", "__dzExtendClip" not in s0)
check("X1 un helper, une entree de menu (branche render), aucun window.prompt/alert",
      s.count("function __dzExtendClip(") == 1 and s.count("__dzExtendClip(") == 2
      # t141 (08/10) : libelle passe par dzT ; la cle rend le francais d'avant
      and 'items.push({ic:"dz-media-generer-video",g:"⚡",lbl:dzT("biblio.envoyer.cible.prolonger"),fn:function(){onClose&&onClose();__dzExtendClip(m.jobId)}});' in s
      and AIDE.fr("biblio.envoyer.cible.prolonger") == "⚡ Prolonger le clip (+7 s, Veo 3.1 Fast, prix montré avant)"
      and "window.prompt" not in fonc("__dzExtendClip") and "window.alert" not in fonc("__dzExtendClip"))
if node:
    js = fonc("__dzExtendClip") + r"""
var toasts=[],infos=[],saisies=[],confirms=[],posts=[],etape={};
globalThis.__dzToast=function(m){toasts.push(m)};
globalThis.window={__dzDialogue:{informer:function(m){infos.push(m);return Promise.resolve()},
  saisir:function(m,o){saisies.push(m);return Promise.resolve(etape.prompt)},
  confirmer:function(m,o){confirms.push([m,o]);return Promise.resolve(etape.son)}}};
function rep(st,j){return Promise.resolve({status:st,ok:st>=200&&st<300,json:function(){return Promise.resolve(j)}})}
globalThis.fetch=function(u,o){if(u.indexOf("/api/generate/extend/check")===0)return rep(200,etape.check);
  posts.push(JSON.parse(o.body));return rep(etape.postStatus||200,{detail:"x"})};
var attendre=function(){return new Promise(function(r){setTimeout(r,60)})};
var OK={ok:true,fal:true,veo_source:true,added_s:7,label:"Veo 3.1 Fast · extension",model:"veo-3.1-fast-extend",
  usd_son:1.05,usd_muet:0.7,source:{duration_s:5,ratio:"9:16"}};
(async function(){var out={};
 etape={check:Object.assign({},OK,{ok:false,reason:"ce clip fait 25.0 s"})};__dzExtendClip("j1");await attendre();
 out.refus={infos:infos.slice(),posts:posts.length,saisies:saisies.length};infos=[];
 etape={check:Object.assign({},OK,{fal:false})};__dzExtendClip("j1");await attendre();out.sansFal={infos:infos.slice(),saisies:saisies.length};infos=[];
 etape={check:OK,prompt:null};__dzExtendClip("j1");await attendre();out.annule={posts:posts.length,confirms:confirms.length};
 saisies=[];etape={check:OK,prompt:"  plus loin ",son:false};__dzExtendClip("j1");await attendre();
 out.muet={post:posts.slice(-1)[0],confirm:confirms.slice(-1)[0],saisie:saisies.slice(-1)[0],toast:toasts.slice(-1)[0]};
 saisies=[];etape={check:Object.assign({},OK,{veo_source:false}),prompt:"x",son:true,postStatus:402};__dzExtendClip("j2");await attendre();
 out.nonVeo={saisie:saisies.slice(-1)[0],post:posts.slice(-1)[0],toast:toasts.slice(-1)[0]};
 console.log(JSON.stringify(out))})();
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickx_"), "x.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    r_ = o.get("refus") or {}
    check("X2 source refusee : la raison est dite (dialogue maison), rien n'est demande ni tire",
          r_.get("posts") == 0 and r_.get("saisies") == 0 and any("25.0 s" in i for i in r_.get("infos", [])), str(r_))
    check("X3 sans cle fal : dit, rien demande", (o.get("sansFal") or {}).get("saisies") == 0 and any("clé fal" in i for i in (o.get("sansFal") or {}).get("infos", [])))
    check("X4 prompt annule : ni question du son ni tir", (o.get("annule") or {}) == {"posts": 0, "confirms": 0}, str(o.get("annule")))
    mu = o.get("muet") or {}
    check("X5 « sans son » : POST avec son:false, prompt nettoye, modele de la mesure ; le toast dit 0.70 $",
          mu.get("post") == {"parent_job_id": "j1", "model": "veo-3.1-fast-extend", "prompt": "plus loin", "son": False}
          and "0.70 $" in str(mu.get("toast")), str(mu.get("post")) + str(mu.get("toast")))
    cf = mu.get("confirm") or ["", {}]
    check("X6 la question du son montre les DEUX prix, sur les boutons aussi", "1.05 $" in cf[0] and "0.70 $" in cf[0]
          and cf[1].get("ok") == "Avec son (1.05 $)" and cf[1].get("annuler") == "Sans son (0.70 $)", str(cf))
    check("X7 la saisie montre la source mesuree ; pas d'avertissement pour une source Veo", "5 s · 9:16" in str(mu.get("saisie"))
          and "Attention" not in str(mu.get("saisie")))
    nv = o.get("nonVeo") or {}
    check("X8 source non-Veo : avertissement ; 402 du plafond : annule proprement", "Attention : fal prolonge surtout" in str(nv.get("saisie"))
          and (nv.get("post") or {}).get("son") is True and "plafond" in str(nv.get("toast")), str(nv)[:300])

print("\n[L] lip-sync Kling dans Quick (tache #52, plan Quick T5)")
check("L0 temoin : la base (15c4c12) n'a pas dzLip", "function dzLip(" not in s0)
check("L1 un dzLip, un seul payload (Seedance), la liste des voix off du dossier audio",
      s.count("function dzLip(") == 1 and s.count("lipsync:dzLip()") == 1 and "D.listAudio().then(function(d2){if(on)" in um
      and "return z.name||z.filename||z" in um)
check("L2 le bloc : onglet Seedance seulement, case qui dit payant, choix de la voix, bornes et prix ecrits",
      # t142 : libelles par cle, le francais d'avant verifie
      'o==="seedance"&&r.jsx(O,{children:r.jsx(Ze,{checked:dzLipOn,label:dzT("quick.lipsync.activer")' in um
      and AIDE.fr("quick.lipsync.activer") == "Lip-sync sur une voix off (Kling, payant)"
      and 'o==="seedance"&&dzLipOn&&r.jsx(O,{label:dzT("quick.lipsync.voix")' in um and AIDE.fr("quick.lipsync.voix") == "Voix off \u00e0 synchroniser"
      and 'o==="seedance"&&dzLipOn&&r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",marginTop:-4},children:dzT("quick.lipsync.note")}' in um
      and "le clip natif doit durer 2 \u00e0 10 s" in AIDE.fr("quick.lipsync.note") and "0,07 $ ou 0,14 $" in AIDE.fr("quick.lipsync.note"))
if node:
    js = r"""
function monter(st){var o=st.o,dzLipOn=st.on,dzLipFile=st.file;
 """ + fonc("dzLip") + r"""
 return dzLip()}
console.log(JSON.stringify({ok:monter({o:"seedance",on:true,file:"v.mp3"}),heygen:monter({o:"heygen",on:true,file:"v.mp3"})===undefined,
 off:monter({o:"seedance",on:false,file:"v.mp3"})===undefined,sansFichier:monter({o:"seedance",on:true,file:""})===undefined}));
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickl_"), "l.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("L3 dzLip : la demande part seulement sur Seedance, case cochee ET voix choisie",
          o.get("ok") == {"on": True, "model": "kling-lipsync", "file": "v.mp3"} and o.get("heygen") is True
          and o.get("off") is True and o.get("sansFichier") is True, str(o))

print("\n[P] presets sur les quatre onglets (tache #53, plan Quick T6, groupe P5pr)")
check("P0 temoin : la base (15c4c12) n'a ni dzQpUI ni __dzQuickVoiceGet", "dzQpUI" not in s0 and "__dzQuickVoiceGet" not in s0)
check("P1 la rangee des presets EN TETE des quatre onglets (voix compris), une fois chacun",
      'children:o==="voice"?[dzQpUI(),r.jsx(DzQuickVoice,{},"dzqv")]:[dzQpUI(),' in um and um.count("dzQpUI()") == 3)
check("P2 les deux boutons ont un title ; aucun window.prompt/confirm/alert dans les gestes",
      # t142 : les title par cle, le francais d'avant verifie
      'title:dzT("quick.preset.enregistrer_aide"),onClick:dzQpSave' in um
      and AIDE.fr("quick.preset.enregistrer_aide") == "Enregistrer l’état complet de l’onglet sous un nom"
      and 'title:dzQsel?dzT("quick.preset.supprimer_aide")' in um
      and AIDE.fr("quick.preset.supprimer_aide") == "Supprimer le preset chargé (confirmation demandée)"
      and all(w not in fonc(f, um) for f in ("dzQpSave", "dzQpDel", "dzQpLoad") for w in ("window.prompt", "window.confirm", "window.alert")))
check("P3 la recette porte la voix (onglet Voix) et son application la rejoue",
      'voice:(o==="voice"&&window.__dzQuickVoiceGet)?window.__dzQuickVoiceGet():void 0' in um
      and 'window.dispatchEvent(new CustomEvent("deepotus:quick-voice",{detail:rc.voice}))' in um)
i_qv = s.find("function DzQuickVoice(")
qv = s[i_qv:i_qv + 20000]
check("P4 DzQuickVoice expose son etat et ecoute l'evenement (retire au demontage)",
      "window.__dzQuickVoiceGet=function(){return{text:txt,lang:lang,voice_id:vid,voice_name:vnm,model:dzM,tune:dzT}};" in qv
      and 'window.removeEventListener("deepotus:quick-voice",onV)' in qv)
if node:
    js = r"""
var toasts=[],fetchs=[],dlg={},applied=[],etat={o:"heygen",qp:[],sel:""};
globalThis.__dzToast=function(m){toasts.push(m)};
globalThis.window={__dzDialogue:{saisir:function(m,o){dlg.saisir=[m,o];return Promise.resolve(dlg.nom)},
  confirmer:function(m,o){dlg.confirmer=[m,o];return Promise.resolve(dlg.oui)}}};
var BASE=[{id:"p1",name:"Abysse",tab:"heygen",recipe:{v:1,tab:"heygen",heygen:{script:"bonjour"}}}];
function rep(st,j){return Promise.resolve({status:st,ok:st>=200&&st<300,json:function(){return Promise.resolve(j)}})}
globalThis.fetch=function(u,o){fetchs.push([u,o&&o.method||"GET",o&&o.body?JSON.parse(o.body):null]);
  if(o&&o.method==="POST")return rep(dlg.postSt||200,dlg.postSt?{detail:"refus"}:{id:"p2",name:JSON.parse(o.body).name});
  if(o&&o.method==="DELETE")return rep(200,{ok:true});return rep(200,{presets:BASE})};
var o="heygen",dzQp=BASE,dzQsel="";
function dzSetQp(v){dzQp=v;etat.qp=v}function dzSetQsel(v){dzQsel=v;etat.sel=v}
function dzQuickApply(rc){applied.push(rc)}function dzQuickRecipe(){return{v:1,tab:o,heygen:{script:"courant"}}}
""" + "\n".join(fonc(f, um) for f in ("dzQpRefresh", "dzQpLoad", "dzQpSave", "dzQpDel", "dzQpTab")) + r"""
var attendre=function(){return new Promise(function(r){setTimeout(r,40)})};
(async function(){var out={};
 dzQpLoad("p1");out.load={applied:applied.slice(),sel:etat.sel,toast:toasts.slice(-1)[0]};
 dzQpLoad("");out.vide={applied:applied.length,sel:etat.sel};
 dlg.nom=null;fetchs=[];dzQpSave();await attendre();out.annule={fetchs:fetchs.length,saisir:dlg.saisir};
 dlg.nom="  Mon preset ";fetchs=[];dzQpSave();await attendre();
 out.save={post:fetchs[0],relit:fetchs[1]&&fetchs[1][0],sel:etat.sel,toast:toasts.slice(-1)[0]};
 dlg.postSt=422;fetchs=[];dzQpSave();await attendre();out.refus={n:fetchs.length,toast:toasts.slice(-1)[0]};dlg.postSt=0;
 dzQsel="";fetchs=[];dlg.confirmer=null;dzQpDel();await attendre();out.delSans={fetchs:fetchs.length,dlg:dlg.confirmer};
 dzQsel="p1";dlg.oui=false;fetchs=[];dzQpDel();await attendre();out.delNon={fetchs:fetchs.length,msg:dlg.confirmer&&dlg.confirmer[0]};
 dzQsel="p1";dlg.oui=true;fetchs=[];dzQpDel();await attendre();out.delOui={req:fetchs[0],sel:etat.sel,toast:toasts.slice(-1)[0]};
 console.log(JSON.stringify(out))})();
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickp_"), "p.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    ld = o.get("load") or {}
    check("P5 charger : la recette du preset part dans dzQuickApply, le choix est retenu, le toast le nomme",
          ld.get("applied") == [BASE_RC := {"v": 1, "tab": "heygen", "heygen": {"script": "bonjour"}}] and ld.get("sel") == "p1"
          and "« Abysse »" in str(ld.get("toast")), str(ld))
    check("P6 la ligne vide ne charge rien", (o.get("vide") or {}) == {"applied": 1, "sel": ""}, str(o.get("vide")))
    an = o.get("annule") or {}
    check("P7 enregistrer annule : aucun appel ; la question nomme l'onglet", an.get("fetchs") == 0
          and "onglet HeyGen" in str((an.get("saisir") or [""])[0]), str(an))
    sv = o.get("save") or {}
    check("P8 enregistrer : POST nom rogne + onglet + recette COURANTE, puis relit l'onglet et selectionne le neuf",
          sv.get("post") == ["/api/quick/presets", "POST", {"name": "Mon preset", "tab": "heygen", "recipe": {"v": 1, "tab": "heygen", "heygen": {"script": "courant"}}}]
          and sv.get("relit") == "/api/quick/presets?tab=heygen" and sv.get("sel") == "p2" and "enregistr" in str(sv.get("toast")), str(sv))
    check("P9 refus serveur : dit, pas de relecture", (o.get("refus") or {}).get("n") == 1 and "refus" in str((o.get("refus") or {}).get("toast")), str(o.get("refus")))
    check("P10 supprimer sans preset charge : ni question ni appel", (o.get("delSans") or {}) == {"fetchs": 0, "dlg": None}, str(o.get("delSans")))
    check("P11 supprimer refuse a la confirmation : aucun appel ; la question nomme le preset",
          (o.get("delNon") or {}).get("fetchs") == 0 and "« Abysse »" in str((o.get("delNon") or {}).get("msg")), str(o.get("delNon")))
    do = o.get("delOui") or {}
    check("P12 supprimer confirme : DELETE du preset charge, choix vide", do.get("req") == ["/api/quick/presets/p1", "DELETE", None]
          and do.get("sel") == "" and "supprim" in str(do.get("toast")), str(do))
    # l'onglet Voix : le code ECRIT dans DzQuickVoice, execute avec de faux etats
    a_qv = qv.find("var dzQvRef=x.useRef(null);")
    b_qv = qv.find("},[]);", qv.find('window.addEventListener("deepotus:quick-voice",onV)')) + len("},[]);")
    js = r"""
var ecouteurs={},effets=[],set={};globalThis.localStorage={setItem:function(k,v){set["ls:"+k]=v}};
globalThis.window={addEventListener:function(n,f){ecouteurs[n]=f},removeEventListener:function(n,f){if(ecouteurs[n]===f)delete ecouteurs[n]},
  __dzQuickVoicePending:{text:"en attente",lang:"en"}};
var x={useRef:function(v){return{current:v}},useEffect:function(f){effets.push(f)}};
var txt="t0",lang="fr",vid="",vnm="App",dzM="m0",dzT={s:1};
function setTxt(v){set.txt=v}function setLang(v){set.lang=v}function setVid(v){set.vid=v}function setVnm(v){set.vnm=v}
function dzSetM(v){set.m=v}function dzSetT(v){set.t=v}
""" + qv[a_qv:b_qv] + r"""
var out={get:window.__dzQuickVoiceGet()};var nettoie=effets[0]();out.pending=JSON.parse(JSON.stringify(set));
out.pendingVide=!("__dzQuickVoicePending" in window);set={};
window.__dzQuickVoicePending={text:"perime"};
ecouteurs["deepotus:quick-voice"]({detail:{text:"T",lang:"en",voice_id:"v9",voice_name:"Nova",model:"eleven_v3",tune:{s:2}}});
out.evt=set;out.evtPurge=!("__dzQuickVoicePending" in window);nettoie();
out.demonte=!ecouteurs["deepotus:quick-voice"]&&!window.__dzQuickVoiceGet;
console.log(JSON.stringify(out));
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickv_"), "v.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("P13 __dzQuickVoiceGet rend l'etat COURANT de la voix",
          o.get("get") == {"text": "t0", "lang": "fr", "voice_id": "", "voice_name": "App", "model": "m0", "tune": {"s": 1}}, str(o.get("get")))
    check("P14 au montage, la voix en attente est rejouee puis effacee", (o.get("pending") or {}) == {"txt": "en attente", "lang": "en"}
          and o.get("pendingVide") is True, str(o.get("pending")))
    check("P15 l'evenement rejoue CHAQUE champ (modele et reglages memorises) et purge l'attente perimee",
          o.get("evt") == {"txt": "T", "lang": "en", "vid": "v9", "vnm": "Nova", "m": "eleven_v3", "ls:dz_voice_model": "eleven_v3",
                           "t": {"s": 2}, "ls:dz_voice_tune": '{"s":2}'} and o.get("evtPurge") is True, str(o.get("evt")))
    check("P16 au demontage : l'ecouteur et le getter sont retires", o.get("demonte") is True, str(o))

print("\n[G] galerie de mouvements (tache #54, plan Quick T7 = D1, groupe P5ga)")
check("G0 temoin : la base (15c4c12) n'a pas __dzQuickGallery", "__dzQuickGallery" not in s0)
check("G1 un helper + un bouton (section Parameters), aucun window.alert/prompt dans le helper",
      s.count("function __dzQuickGallery(") == 1 and s.count("__dzQuickGallery(") == 2
      # t142 : la section et le title par cle ; « Parameters » est l'anglais de la cle, le title garde son francais
      and 'r.jsxs(ie,{label:dzT("quick.parametres.titre"),right:r.jsx(K,{variant:"ghost",size:"sm",icon:"dz-media-mouvements-camera",title:dzT("quick.galerie.bouton_aide")' in um
      and AIDE.DICO["quick.parametres.titre"]["en"] == "Parameters"
      and AIDE.fr("quick.galerie.bouton_aide").startswith("Galerie de mouvements")
      and "window.alert" not in fonc("__dzQuickGallery") and "window.prompt" not in fonc("__dzQuickGallery"))
check("G2 deux routes seulement (manifeste + build) ; les vignettes viennent du manifeste",
      fonc("__dzQuickGallery").count("/api/quick/gallery") == 2)
i_g2 = um.find('right:r.jsx(K,{variant:"ghost",size:"sm",icon:"dz-media-mouvements-camera"')
# t142 : la borne de fin suit la cle du libelle (« Galerie » passe par dzT) ; sans elle, l'extrait courait jusqu'au
# bout du bundle et le morceau execute ne compilait plus
g2 = um[i_g2:um.find('children:dzT("quick.galerie.bouton")})', i_g2)]
check("G2b la borne de l'extrait existe et le libelle rend le francais d'avant",
      um.find('children:dzT("quick.galerie.bouton")})', i_g2) > i_g2 > 0 and AIDE.fr("quick.galerie.bouton") == "Galerie")
check("G3 le clic ne replie pas la section (stopPropagation) ; Vibe changee seulement si elle existe",
      "e2.stopPropagation()" in g2 and "if(I.some(function(z){return z.id===ti.style}))V(ti.style);" in g2)
if node:
    pick = g2[g2.find("function(ti){"):g2.rfind("})}")]
    js = r"""
var V_=[],toasts=[],prompt="un trone abyssal";var I=[{id:"cinematic"},{id:"ugc_raw"},{id:"hybrid"}];
function V(x){V_.push(x)}function a(f){prompt=typeof f==="function"?f(prompt):f}globalThis.__dzToast=function(m){toasts.push(m)};
var pick=""" + pick + r"""};
pick({camera:"crane shot descending",style:"ugc_raw"});var p1=prompt;
pick({camera:"static, locked-off",style:"inconnu"});var p2=prompt;
prompt="";pick({camera:"slow push-in",style:"cinematic"});
console.log(JSON.stringify({p1:p1,p2:p2,p3:prompt,V:V_,t:toasts[0]}));
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickg_"), "g.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("G4 choisir : la phrase camera s'ajoute au prompt", o.get("p1") == "un trone abyssal Camera: crane shot descending.", str(o))
    check("G5 rechoisir : la phrase est REMPLACEE (pas empilee), la virgule de « static, locked-off » tient",
          o.get("p2") == "un trone abyssal Camera: static, locked-off.", str(o.get("p2")))
    check("G6 prompt vide : la phrase seule ; Vibe posee pour les styles connus seulement",
          o.get("p3") == "Camera: slow push-in." and o.get("V") == ["ugc_raw", "cinematic"] and "ajout" in str(o.get("t")), str(o))
    # le helper, sous un faux DOM minimal
    js = r"""
var corps=[],ecouteurs={},posts=[],toasts=[],picks=[],etape={};
function el(tag){var e={tag:tag,style:{},children:[],className:"",textContent:"",title:"",appendChild:function(c){c.parent=e;e.children.push(c)},
  setAttribute:function(k,v){e[k]=String(v)},
  remove:function(){var i=corps.indexOf(e);if(i>=0)corps.splice(i,1)}};return e}
globalThis.document={createElement:el,body:{appendChild:function(e){corps.push(e)}},
  getElementById:function(id){return corps.find(function(e){return e.id===id})||null},
  addEventListener:function(n,f){ecouteurs[n]=f},removeEventListener:function(n,f){if(ecouteurs[n]===f)delete ecouteurs[n]}};
globalThis.__dzToast=function(m){toasts.push(m)};
function rep(st,j){return Promise.resolve({status:st,json:function(){return Promise.resolve(j)}})}
var MAN={built:true,source:"a.png",note:"elles montrent le mot, pas le rendu du modèle.",tiles:[{id:"t1",camera:"slow push-in",style:"cinematic",url:"/api/quick/gallery/t1"},{id:"t2",camera:"tracking shot",style:"hybrid",url:"/api/quick/gallery/t2"}]};
globalThis.fetch=function(u,o){if(o&&o.method==="POST"){posts.push([u,JSON.parse(o.body)]);return rep(etape.postSt||200,etape.postSt?{detail:"Image introuvable"}:Object.assign({},MAN,{source:JSON.parse(o.body).image}))}
  return rep(200,etape.man)};
function tout(e,acc){acc=acc||[];acc.push(e);(e.children||[]).forEach(function(c){tout(c,acc)});return acc}
var attendre=function(){return new Promise(function(r){setTimeout(r,30)})};
""" + fonc("__dzQuickGallery") + r"""
(async function(){var out={};
 etape={man:MAN};__dzQuickGallery("a.png",function(t){picks.push(t)});await attendre();
 var h=corps[0],els=h?tout(h):[];var tuiles=els.filter(function(e){return e.className==="dz-gal-tile"});
 out.grille={hote:!!h&&h.id,n:tuiles.length,video:tuiles[0]&&tuiles[0].children[0].src,note:(els.find(function(e){return e.className==="dz-gal-note"})||{}).textContent,
   rerender:els.some(function(e){return e.className==="dz-gal-rerender"}),posts:posts.length,titres:tuiles.every(function(t){return t.title.indexOf("Camera: ")>0})};
 tuiles[1].onclick();out.clic={picks:picks.map(function(p){return p.camera}),ouvert:corps.length,echap:!!ecouteurs.keydown};
 __dzQuickGallery("b.png",function(){});await attendre();
 var els2=tout(corps[0]);out.autre={rerender:els2.some(function(e){return e.className==="dz-gal-rerender"})};
 var stop=0;ecouteurs.keydown({key:"Escape",stopPropagation:function(){stop++}});out.echap={ouvert:corps.length,stop:stop};
 etape={man:{built:false}};__dzQuickGallery("",function(){});await attendre();out.sansImage={posts:posts.length,toast:toasts.slice(-1)[0],ouvert:corps.length};
 __dzQuickGallery("c.png",function(){});await attendre();out.build={post:posts.slice(-1)[0],ouvert:corps.length,n:tout(corps[0]||{children:[]}).filter(function(e){return e.className==="dz-gal-tile"}).length};
 ecouteurs.keydown&&ecouteurs.keydown({key:"Escape",stopPropagation:function(){}});
 etape={man:{built:false},postSt:404};__dzQuickGallery("z.png",function(){});await attendre();out.refus={toast:toasts.slice(-1)[0],ouvert:corps.length};
 console.log(JSON.stringify(out))})();
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickh_"), "h.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    gr = o.get("grille") or {}
    check("G7 galerie deja rendue : grille ouverte sans rien rendre, une tuile par vignette, la phrase honnete visible",
          gr.get("hote") == "__dzGalHost" and gr.get("n") == 2 and gr.get("video") == "/api/quick/gallery/t1" and gr.get("posts") == 0
          and "montrent le mot, pas le rendu du mod" in str(gr.get("note")) and gr.get("titres") is True, str(gr))
    check("G8 meme image : pas de bouton « Rendre sur » ; image differente : il apparait",
          gr.get("rerender") is False and (o.get("autre") or {}).get("rerender") is True, str(o.get("autre")))
    check("G9 cliquer une tuile : onPick recoit la vignette, la grille se ferme et Echap n'est plus ecoute",
          (o.get("clic") or {}) == {"picks": ["tracking shot"], "ouvert": 0, "echap": False}, str(o.get("clic")))
    check("G10 Echap ferme (sans laisser passer la touche)", (o.get("echap") or {}) == {"ouvert": 0, "stop": 1}, str(o.get("echap")))
    check("G11 jamais rendue et pas d'image : le dit, ne rend rien", (o.get("sansImage") or {}).get("posts") == 0
          and "image de d" in str((o.get("sansImage") or {}).get("toast")) and (o.get("sansImage") or {}).get("ouvert") == 0, str(o.get("sansImage")))
    bd = o.get("build") or {}
    check("G12 jamais rendue + image : POST build sur l'image de depart, puis la grille", bd.get("post") == ["/api/quick/gallery/build", {"image": "c.png"}]
          and bd.get("ouvert") == 1 and bd.get("n") == 2, str(bd))
    check("G13 refus du build : le detail est dit, rien ne s'ouvre", "Image introuvable" in str((o.get("refus") or {}).get("toast"))
          and (o.get("refus") or {}).get("ouvert") == 0, str(o.get("refus")))

print("\n[K] curseurs camera traduits en phrase (tache #54, plan Quick T8 = D2)")
check("K0 temoin : la base (15c4c12) n'a ni dzCam ni camera_ctrl", "function dzCam(" not in s0 and "camera_ctrl" not in s0)
check("K1 un etat, deux payloads (solo + slot seedance de comp), l'apercu par la ROUTE (pas de traduction dans le bundle)",
      s.count("function dzCam(") == 1 and s.count("camera_ctrl:dzCam()") == 2 and s.count("/api/quick/camera-phrase") == 1
      and "pushing in" not in s and "zoom in" not in s)
check("K2 la section : repliee, absente sur HeyGen, six curseurs -10..10, la note honnete, « Remettre a zero » avec un title",
      # t142 : libelles par cle, le francais d'avant verifie
      'o!=="heygen"&&r.jsx(ie,{label:dzT("quick.camera.titre"),defaultOpen:!1,' in um and AIDE.fr("quick.camera.titre") == "Caméra (curseurs)"
      and um.count('dzT("quick.camera.zoom")') == 1 and AIDE.fr("quick.camera.zoom") == "Zoom (− arrière / + avant)"
      and "min:-10,max:10,step:1" in um
      and 'children:dzT("quick.camera.note")' in um
      and AIDE.fr("quick.camera.note").startswith("Aucun modèle du registre n’expose de contrôle caméra via fal")
      and 'title:dzT("quick.camera.zero_aide")' in um and AIDE.fr("quick.camera.zero_aide") == "Remettre les six curseurs à zéro")
if node:
    i_e = um.find("x.useEffect(function(){if(!dzCamN())")
    eff = um[i_e:um.find("},[dzCamCtl,VMQ]);", i_e) + len("},[dzCamCtl,VMQ]);")]
    js = r"""
var appels=[],ph=[],nettoyages=[];var x={useEffect:function(f){var n=f();if(n)nettoyages.push(n)}};
globalThis.fetch=function(u,o){appels.push([u,JSON.parse(o.body)]);return Promise.resolve({ok:true,json:function(){return Promise.resolve({phrase:"Camera: zoom in."})}})};
function monter(ctrl,VMQ){var dzCamCtl=ctrl;function dzSetCamPh(p){ph.push(p)}
""" + fonc("dzCamN", um) + fonc("dzCam", um) + "\n" + eff + r"""
 return {cam:dzCam(),n:dzCamN()}}
var attendre=function(ms){return new Promise(function(r){setTimeout(r,ms)})};
(async function(){var out={};
 out.zero=monter({zoom:0,horizontal:0,vertical:0,pan:0,tilt:0,roll:0},"kling-v3-pro");await attendre(260);
 out.zeroAppels=appels.length;out.zeroPh=ph.slice();
 out.un=monter({zoom:7,horizontal:0,vertical:0,pan:0,tilt:-4,roll:0},"kling-v3-pro");await attendre(60);out.avant=appels.length;
 await attendre(260);out.apres=appels.slice();out.ph=ph.slice(-1)[0];
 monter({zoom:1},"");nettoyages.slice(-1)[0]();await attendre(260);out.annule=appels.length;
 console.log(JSON.stringify(out))})();
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickk_"), "k.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("K3 tout a zero : dzCam() n'envoie rien (undefined), aucun appel d'apercu, phrase videe",
          (o.get("zero") or {}).get("n") == 0 and "cam" not in (o.get("zero") or {}) and o.get("zeroAppels") == 0 and o.get("zeroPh") == [""], str(o)[:300])
    check("K4 deux axes : dzCam() rend une COPIE des six, l'apercu part APRES 200 ms avec le modele, la phrase de la route s'affiche",
          (o.get("un") or {}).get("n") == 2 and (o.get("un") or {}).get("cam", {}).get("tilt") == -4 and o.get("avant") == 0
          and o.get("apres") == [["/api/quick/camera-phrase", {"ctrl": {"zoom": 7, "horizontal": 0, "vertical": 0, "pan": 0, "tilt": -4, "roll": 0},
                                                              "model": "kling-v3-pro"}]]
          and o.get("ph") == "Camera: zoom in.", str(o)[:400])
    check("K5 un curseur bouge encore avant 200 ms : l'appel precedent est annule (nettoyage de l'effet)", o.get("annule") == 1, str(o.get("annule")))

def fonc_d(nom, src=s):
    """Comme fonc, pour un composant a parametres DESTRUCTURES : le corps commence apres « ){ »."""
    i = src.find(f"function {nom}(")
    j = src.find("){", i) + 1
    prof = 0
    for k in range(j, len(src)):
        prof += {"{": 1, "}": -1}.get(src[k], 0)
        if prof == 0:
            return src[i:k + 1]


print("\n[U] les quatre onglets en studio (tache #54, plan Quick T9 = D3, groupe P5su)")
check("U0 temoin : la base (15c4c12) n'a ni DzQuickDrop ni DzQuickStage, et la colonne fait 380 px",
      "DzQuickDrop" not in s0 and "DzQuickStage" not in s0 and 'gridTemplateColumns:"380px 1fr"' in s0)
check("U1 deux composants, la colonne a 360 px (plus de 380), deux DropZones (depart + fin), l'apercu APPELE comme fonction",
      s.count("function DzQuickDrop(") == 1 and s.count("function DzQuickStage(") == 1 and 'gridTemplateColumns:"360px 1fr"' in s
      and 'gridTemplateColumns:"380px 1fr"' not in s and um.count("r.jsx(DzQuickDrop,") == 2
      and um.count("DzQuickStage({tab:o,img:w,layout:We,avatarUrl:") == 1 and "r.jsx(DzQuickStage" not in s)
check("U2 la maquette vd n'est plus dans les champs image de Quick ; le repli « upload an image in Library » reste derriere ||",
      'r.jsx(vd,{label:"upload images in Library"' not in um and 'r.jsx(vd,{label:"drop or pick"' not in um
      and 'avatarUrl:(function(){var _a=U.find(function(z){return z.avatar_id===C});return(_a&&_a.preview_image_url)||""})()})||r.jsxs("div"' in um
      # t142 : le repli passe par dzT("quick.apercu.importer") ; son anglais est l'ancien texte
      and 'children:dzT("quick.apercu.importer")' in um and AIDE.DICO["quick.apercu.importer"]["en"] == "upload an image in Library")
check("U3 le bandeau et l'avertissement suivent l'onglet (Composition nomme les deux fournisseurs)",
      # t142 : « voix off » par cle, son francais verifie ; les fournisseurs restent des litteraux
      'children:[o==="seedance"?A:o==="heygen"?"avatar":o==="comp"?We:dzT("quick.apercu.voix_off")," · ",h,"s"]' in um
      and AIDE.fr("quick.apercu.voix_off") == "voix off"
      and 'children:o==="heygen"?"heygen.com":o==="comp"?"fal.ai + heygen.com":"fal.ai"})' in um)
check("U13 chaque zone alimente SON champ (depart -> v, fin -> k) et ajoute le fichier a la liste des images",
      'onFile:function(nm){f(function(p2){return p2.indexOf(nm)>=0?p2:[nm].concat(p2)});v(nm)}},"dzdropdep")' in um
      and 'onFile:function(nm){f(function(p2){return p2.indexOf(nm)>=0?p2:[nm].concat(p2)});k(nm)}},"dzdropfin")' in um)
check("U4 aucun window.alert dans les deux composants ; la zone a un title", "window.alert" not in fonc_d("DzQuickDrop")
      and "window.alert" not in fonc_d("DzQuickStage") and 'className:"dz-drop",title:dzT("quick.import.depot_aide")' in s
      and AIDE.fr("quick.import.depot_aide").startswith("Glissez une image ici"))   # t142 : title par cle
if node:
    js = r"""
var etats=[],refs=[],toasts=[],posts=[],fichiers=[],reponse={};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};
var x={useState:function(v){var c=[v,function(n){c[0]=n;etats.push(n)}];return c},useRef:function(v){var o={current:v};refs.push(o);return o}};
var D={imageUrl:function(n){return "/api/images/"+n}};globalThis.__dzToast=function(m){toasts.push(m)};
globalThis.fetch=function(u,o){posts.push([u,o.method,o.body instanceof FormData&&o.body.get("file")&&o.body.get("file").name]);
  return Promise.resolve({status:reponse.s,json:function(){return reponse.j===undefined?Promise.reject(new Error("pas de json")):Promise.resolve(reponse.j)}})};
""" + fonc_d("DzQuickStage") + fonc_d("DzQuickDrop") + r"""
function trouve(e,pred,acc){acc=acc||[];if(!e||typeof e!=="object")return acc;if(pred(e))acc.push(e);var c=e.p&&e.p.children;
  (Array.isArray(c)?c:[c]).forEach(function(k){trouve(k,pred,acc)});return acc}
var attendre=function(){return new Promise(function(r2){setTimeout(r2,30)})};
(async function(){var out={};
 out.seedVide=DzQuickStage({tab:"seedance",img:"",layout:"sequential",avatarUrl:""});
 var sd=DzQuickStage({tab:"seedance",img:"a.png"});out.seed=sd&&sd.t+"|"+sd.p.src;
 var hg=DzQuickStage({tab:"heygen",img:"a.png",avatarUrl:"https://x/p.jpg"});out.hg=hg.t+"|"+hg.p.src;
 var hg0=DzQuickStage({tab:"heygen",img:"a.png",avatarUrl:""});out.hg0=hg0.p.children;
 var c1=DzQuickStage({tab:"comp",img:"a.png",layout:"split_vstack",avatarUrl:"https://x/p.jpg"});
 out.comp={rows:c1.p.style.gridTemplateRows,cols:c1.p.style.gridTemplateColumns,n:c1.p.children.filter(Boolean).length,
   img:c1.p.children[0].p.style.backgroundImage,av:c1.p.children[1].p.style.backgroundImage};
 var c2=DzQuickStage({tab:"comp",img:"a.png",layout:"sequential"});out.compSeq=c2.p.children.filter(Boolean).length;
 var c3=DzQuickStage({tab:"comp",img:"a.png",layout:"split_hstack"});out.compH=c3.p.style.gridTemplateColumns;
 out.voix=DzQuickStage({tab:"voice"}).p.children;
 // la DropZone
 var recus=[];var z=DzQuickDrop({label:"glissez",onFile:function(n){recus.push(n)}});
 var inp=trouve(z,function(e){return e.t==="input"})[0];refs[0].current={click:function(){out.clic=(out.clic||0)+1}};
 z.p.onClick();
 var prevenu=0,ev=function(f){return {preventDefault:function(){prevenu++},dataTransfer:{files:f?[f]:[]}}};
 z.p.onDragOver(ev());out.survol=etats.slice(-1)[0];
 reponse={s:200,j:{filename:"dep.png"}};z.p.onDrop(ev(new File(["x"],"dep.png",{type:"image/png"})));await attendre();
 out.drop={post:posts.slice(-1)[0],recus:recus.slice(),toast:toasts.slice(-1)[0],survol:etats.slice(-1)[0],prevenu:prevenu};
 reponse={s:415,j:{detail:"Format non pris en charge (.gif)"}};z.p.onDrop(ev(new File(["x"],"a.gif")));await attendre();
 out.refus={recus:recus.length,toast:toasts.slice(-1)[0]};
 reponse={s:500,j:undefined};z.p.onDrop(ev(new File(["x"],"b.png")));await attendre();out.panne=toasts.slice(-1)[0];
 var n0=posts.length;z.p.onDrop(ev(null));await attendre();out.vide=posts.length-n0;
 // preuve ecran 01/10 : /images/upload acceptait un .txt depose (le accept du selecteur ne vaut pas pour un depot)
 n0=posts.length;var r0=recus.length;z.p.onDrop(ev(new File(["pas une image"],"note.txt",{type:"text/plain"})));await attendre();
 out.texte={posts:posts.length-n0,recus:recus.length-r0,toast:toasts.slice(-1)[0]};
 n0=posts.length;reponse={s:200,j:{filename:"sans-type.JPG"}};z.p.onDrop(ev(new File(["x"],"sans-type.JPG")));await attendre();out.sansType=posts.length-n0;
 reponse={s:200,j:{filename:"via-clic.png"}};var cible={files:[new File(["x"],"via-clic.png")],value:"C:/fakepath/via-clic.png"};
 inp.p.onChange({target:cible});await attendre();out.input={recus:recus.slice(-1)[0],valeur:cible.value,accept:inp.p.accept,cache:inp.p.style.display};
 console.log(JSON.stringify(out))})();
"""
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquicks_"), "s.mjs"); f.write_text(PRELUDE + js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("U5 Seedance : l'image de depart ; SANS image : null (le repli d'origine prend la main)",
          o.get("seedVide") is None and "seedVide" in o and o.get("seed") == "img|/api/images/a.png", str(o)[:200])
    check("U6 HeyGen : le portrait de l'avatar, sinon une phrase qui dit quoi faire",
          o.get("hg") == "img|https://x/p.jpg" and "Choisissez un avatar" in str(o.get("hg0")), str(o.get("hg")) + str(o.get("hg0")))
    cp = o.get("comp") or {}
    check("U7 Composition : deux bandes en split_vstack (image + portrait), une seule en sequentiel, colonnes en split_hstack",
          cp.get("rows") == "1fr 1fr" and cp.get("cols") == "1fr" and cp.get("n") == 2 and cp.get("img") == "url(/api/images/a.png)"
          and cp.get("av") == "url(https://x/p.jpg)" and o.get("compSeq") == 1 and o.get("compH") == "1fr 1fr", str(cp))
    check("U8 Voix off : la phrase qui explique qu'il n'y a pas d'image", "fichier audio" in str(o.get("voix")))
    dr = o.get("drop") or {}
    check("U9 deposer un fichier : POST /api/images/upload avec CE fichier, onFile recoit le nom rendu, toast, survol retombe",
          o.get("survol") is True and dr.get("post") == ["/api/images/upload", "POST", "dep.png"] and dr.get("recus") == ["dep.png"]
          and "dep.png" in str(dr.get("toast")) and dr.get("survol") is False and dr.get("prevenu") == 2, str(dr))
    check("U10 refus (415) : le detail est dit, onFile n'est PAS appele ; reponse illisible : le statut est dit",
          (o.get("refus") or {}).get("recus") == 1 and "Format non pris en charge" in str((o.get("refus") or {}).get("toast"))
          and "500" in str(o.get("panne")), str(o.get("refus")) + str(o.get("panne")))
    check("U11 depot vide : aucun appel", o.get("vide") == 0)
    tx = o.get("texte") or {}
    check("U14 un fichier qui n'est pas une image est refuse AVANT l'envoi, en le nommant ; une image sans type MIME passe par son extension",
          tx.get("posts") == 0 and tx.get("recus") == 0 and "note.txt" in str(tx.get("toast")) and "pas une image" in str(tx.get("toast"))
          and o.get("sansType") == 1, str(tx) + str(o.get("sansType")))
    check("U12 cliquer la zone ouvre le selecteur ; le fichier choisi est importe, le champ remis a vide (meme fichier rechoisissable)",
          o.get("clic") == 1 and (o.get("input") or {}) == {"recus": "via-clic.png", "valeur": "", "accept": "image/*", "cache": "none"},
          str(o.get("input")))

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
