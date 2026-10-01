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
check("A1 l'amont est intact (Quick unique, pickers et envois)", s.count("function um(") == 1 and s.count("__dzLibPicker") == 10
      and s.count("__dzSendTo") == 2)
check("A2 __dzQuickStart 3 -> 4 (dzQuickApply pose le global quand les images ne sont pas chargees)", s.count("__dzQuickStart") == 4)
check("A3 __dzReopenQuick : definition + modal + carte de la file", s.count("__dzReopenQuick") == 3 and s.count("function __dzReopenQuick(") == 1
      and s.count("function __dzQuickFromJob(") == 1)
check("A4 les trois payloads portent la recette EN TETE", s.count("quick_recipe:dzQuickRecipe()") == 3
      and "je={quick_recipe:dzQuickRecipe(),video_model:VMQ||void 0,image_filename:w," in s
      and 'D.postJson("/generate/heygen",{quick_recipe:dzQuickRecipe(),avatar_id:C,' in s
      and 'D.postJson("/generate/composition",{quick_recipe:dzQuickRecipe(),seedance:{video_model:' in s)
check("A5 l'evenement : emis par le helper, ecoute par Quick (et retire au demontage)", s.count('"deepotus:quick-recipe"') == 3
      and 'window.removeEventListener("deepotus:quick-recipe",onR)' in s)
check("A6 le bouton de la Bibliotheque (renders seulement) et l'icone de la file, avec un title",
      'm.kind==="render"&&m.jobId&&r.jsx(K,{variant:"ghost",size:"sm",icon:"bolt",title:"Rouvrir ce rendu dans Quick' in s
      and 'children:"Rouvrir dans Quick"},"dzquick")' in s
      and 'm&&r.jsx(se,{name:"bolt",title:"Rouvrir dans Quick (prérempli)",onClick:function(){__dzReopenQuick(e.id)}})' in s)
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
    SETTERS = "i v k a V dzSetVMQ b z P F Hsrc Q ne W Eng Mimg Mp Xp De".split()
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
 var o=etat.o,w=etat.w,g=etat.g,s=etat.s,A=etat.A,VMQ=etat.VMQ,h=etat.h,_=etat._,N=etat.N,H=etat.H,hsrc=etat.hsrc,C=etat.C,ee=etat.ee,R=etat.R,eng=etat.eng,mimg=etat.mimg,mp=etat.mp,xp=etat.xp,We=etat.We;
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
 var ecran=fabrique({o:"seedance",w:"a.png",g:"",s:"abysse",A:"noir",VMQ:"seedance-2",h:10,_:"9:16",N:"42",H:"",hsrc:"avatar",C:"av1",ee:"vx",R:"txt",eng:"",mimg:"",mp:"",xp:"",We:"sequential",u:[1]});
 out.recette=ecran.recette();
 ecran.appliquer(REC);out.appliques=appliques;
 appliques={};var vide=fabrique({u:[]});window.__dzQuickStart=null;vide.appliquer({seedance:{image:"z.png"}});out.global=window.__dzQuickStart;out.app2=appliques;
 appliques={};vide.appliquer({tab:"pirate"});out.pirate=appliques;
 console.log(JSON.stringify(out));
})();
"""])
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquickb_"), "q.mjs"); f.write_text(js, encoding="utf-8")
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

print("\n[E] l'image de fin grisee avec la raison (tache #49, plan Quick T3, groupe P5ef)")
check("E0 temoin : la base (15c4c12) n'a ni dzEndOK ni le libelle « indisponible »", "dzEndOK" not in s0 and "Image de fin — indisponible" not in s0)
check("E1 un etat, deux fonctions, la table lue sur /api/video-models (rien en dur)", s.count("dzSetEndCaps") == 2
      and s.count("function dzEndOK(") == 1 and s.count("function dzEndWhy(") == 1 and 'fetch("/api/video-models")' in um
      and "kling-v3-pro" not in fonc("dzEndWhy"))
check("E2 le champ porte la raison a la place du select, avec un title", 'label:dzEndOK()?"Image de fin (optionnelle)":"Image de fin — indisponible"' in um
      and 'children:dzEndOK()?(u.length>0?r.jsx(re,{value:g,' in um
      and 'r.jsx("div",{title:"Choisissez un modèle qui accepte une image de fin"' in um and 'children:dzEndWhy()})})' in um)
check("E3 le bouton « Parcourir » de fin n'existe que si c'est accepte", 'dzEndOK()&&r.jsx(O,{label:"",children:r.jsx("button"' in um
      and 'titre:"Image de fin (optionnelle)"},k)' in um)
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
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzquicke_"), "e.mjs"); f.write_text(js, encoding="utf-8")
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

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
