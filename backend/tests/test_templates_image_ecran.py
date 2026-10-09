# -*- coding: utf-8 -*-
"""Plan-templates T5-T6 (tache #75 du suivi, PR B, 03/10/2026) — IMAGE FIXE et VIGNETTES au contenu reel, dans le
bundle LIVRE : la vignette de galerie, l'export d'image et l'echantillon d'apercu sont extraits et EXECUTES sous node.
DECISIONS DE L'UTILISATEUR (03/10) : echantillon choisi par case (dans la Bibliotheque), sinon mire ; instant reglable,
1 s ; PNG, JPEG, WebP ; l'image va dans la Bibliotheque ; vignettes a la demande, le schema reste en attendant.
Temoin positif : le bundle de la base (ff050214) n'a pas l'export d'image.
Run (depuis backend/) : & $PY tests/test_templates_image_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzime_"))
# t142 (09/10) : la traduction L2 fait passer les libelles par dzT (globale) ; le code execute sous node recoit le
# prelude qui la pose en FRANCAIS (les attentes en francais restent vraies).
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                               # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "ff050214"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la galerie et l'editeur mais pas l'export d'image", r0.returncode == 0
      and b"children:r.jsx(gm,{id:f.id,regions:f.regions,canvas:f.canvas})})" in r0.stdout and b"DzExportImage" not in r0.stdout)
k_ech = BUN.find('r.jsx(DzEchantillon,{rg:c,tpl:a,setTpl:l}),r.jsx(DzAnimEditor,')   # #76 PR B : la section Animation suit l'echantillon
check("T2 la carte de galerie enveloppe son schema dans la vignette (l'apercu de reagencement NON) ; l'export suit « Open in Studio » ; l'echantillon precede « Delete region »",
      BUN.count('children:r.jsx(DzTplVignette,{id:f.id,regions:f.regions,canvas:f.canvas,children:r.jsx(gm,{id:f.id,regions:f.regions,canvas:f.canvas})})})') == 1
      and BUN.count("r.jsx(DzTplVignette,") == 1 and BUN.count('r.jsx(gm,{id:tp.id||"apercu"') == 1
      # t142 (09/10) : « Open in Studio » passe par dzT (francais « Ouvrir dans le Studio », anglais d'origine garde)
      and BUN.count('children:dzT("templates.editeur.ouvrir_studio")}),r.jsx(DzExportImage,{tpl:a,regs:d})') == 1
      and AIDE.fr("templates.editeur.ouvrir_studio") == "Ouvrir dans le Studio" and AIDE.DICO["templates.editeur.ouvrir_studio"]["en"] == "Open in Studio"
      and k_ech > 0 and BUN.count("r.jsx(DzEchantillon,") == 1)


def fonction(nom):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = BUN.find("){", k) + 1, 0, None, False
    while i < len(BUN):
        c_ = BUN[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k - 6 if BUN[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


NOMS = ("dzHache", "DzTplVignette", "dzGabaritCourant", "DzExportImage", "DzEchantillon")
COUCHE = "var __dzTplThumbV=0;\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a le compteur et les cinq fonctions (une fois chacune)", BUN.count("var __dzTplThumbV=0;") == 1
      and all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,FETCH=[],REP=null,PICK=[],window={};
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){p=p||{};return {t:t,p:p,props:p}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var K="K",O="Champ",Ze="Case",re="Liste",Oe="Curseur",le="Saisie",gm="Schema";
window.__dzLibPicker=function(o,cb){PICK.push([o,cb])};
async function fetch(u,o){FETCH.push([u,o&&o.method,o&&o.body&&JSON.parse(o.body)]);var q=REP;await new Promise(function(s){setTimeout(s,5)});
  return {ok:q.ok,status:q.status,json:async function(){return q.json||{}}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function par(T,t){return trouver(T,function(n){return n.t===t})}
function bouton(T,txt){return par(T,"K").find(function(b){return b.p.children===txt})}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    # t142 : le prelude APRES le harnais (qui pose son propre `window`), sinon son dictionnaire serait ecrase
    f.write_text(COUCHE + "\n" + HARNAIS + "\n" + AIDE.PRELUDE_DZT + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    try:
        p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except subprocess.TimeoutExpired:
        print("   (node) suspendu plus de 60 s")
        return None
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


print("[V] la vignette de galerie")
R = node("""
var SCH=el("Schema",{});var RG=[{id:"a",x:0}],CV={width:1080,height:1920};
function v(id,rg){hi=0;return DzTplVignette({id:id,regions:rg||RG,canvas:CV,children:SCH})}
R.sansId=v("")===SCH;var T=v("tpl news/1");var im=par(T,"img")[0];R.src=im.p.src;R.op0=im.p.style.opacity;R.titre=im.p.title;R.lazy=im.p.loading;
R.enfant=T.p.children[0]===SCH;R.pos=T.p.style.position;
im.p.onLoad();T=v("tpl news/1");R.op1=par(T,"img")[0].p.style.opacity;
R.autreCases=par(v("tpl news/1",[{id:"a",x:5}]),"img")[0].p.src;
__dzTplThumbV++;R.apresEch=par(v("tpl news/1"),"img")[0].p.src;
T=v("tpl news/1");par(T,"img")[0].p.onLoad();T=v("tpl news/1");R.opAvantErr=par(T,"img")[0].p.style.opacity;
par(T,"img")[0].p.onError();T=v("tpl news/1");R.opErr=par(T,"img")[0].p.style.opacity;
""")
check("V0 sous node : la vignette s'execute", R is not None)
if R:
    check("V1 sans id, le schema seul ; sinon le schema PUIS l'image reelle par-dessus (meme boite, en absolu), chargee a la demande, avec un title ; l'id est encode",
          R["sansId"] and R["enfant"] and R["pos"] == "relative" and R["src"].startswith("/api/layout-templates/tpl%20news%2F1/thumb?v=") and R["lazy"] == "lazy" and R["titre"], R["src"])
    check("V2 invisible tant qu'elle n'est pas chargee (le schema reste), visible une fois chargee, de nouveau cachee si le serveur echoue",
          R["op0"] == 0 and R["op1"] == 1 and R["opAvantErr"] == 1 and R["opErr"] == 0, f"{R['op0']} {R['op1']} {R['opAvantErr']} {R['opErr']}")
    check("V3 l'adresse CHANGE quand les cases changent, et quand un echantillon est choisi (le navigateur redemande la vignette)",
          len({R["src"], R["autreCases"], R["apresEch"]}) == 3, f"{R['src']} {R['autreCases']} {R['apresEch']}")

print("\n[X] exporter l'image")
R = node("""
var TPL={id:"tpl_x",name:"X",canvas:{width:400,height:400},metadata:{samples:{v:"a.png"}},regions:[{id:"v",type:"video_slot",slot_name:"v",x:0,y:0,width:10,height:10,fit:"cover"}]};
var REGS=[{id:"v",type:"video_slot",slot_name:"v",x:10.4,y:20.6,width:100.2,height:50.7,_disp:{z:1}}];
function ex(t,rg){hi=0;return DzExportImage({tpl:t,regs:rg})}
R.sans=ex(null,[])===null;var T=ex(TPL,REGS);R.titre=bouton(T,"Exporter l’image").p.title;R.formats=par(T,"Liste")[0].p.options.map(function(o){return o.value});R.defaut=[H[0],H[1]];
par(T,"Saisie")[0].p.onChange("1,5");par(ex(TPL,REGS),"Liste")[0].p.onChange("webp");
REP={ok:true,status:200,json:{filename:"tpl_still_ab.webp"}};T=ex(TPL,REGS);var b=bouton(T,"Exporter l’image");var p1=b.p.onClick(),p2=b.p.onClick();await p1;await p2;
R.fetch=FETCH.slice();R.msg=texte(ex(TPL,REGS));
FETCH=[];par(ex(TPL,REGS),"Saisie")[0].p.onChange("bientot");await bouton(ex(TPL,REGS),"Exporter l’image").p.onClick();R.illisible=[FETCH.length,texte(ex(TPL,REGS))];
par(ex(TPL,REGS),"Saisie")[0].p.onChange("2");REP={ok:false,status:400,json:{detail:"Format inconnu : gif — png, jpeg ou webp."}};
await bouton(ex(TPL,REGS),"Exporter l’image").p.onClick();R.refus=texte(ex(TPL,REGS));
FETCH=[];REP={ok:true,status:200,json:{filename:"f.png"}};hi=0;H=[];await bouton(ex({name:"neuf",canvas:{},regions:[]},[]),"Exporter l’image").p.onClick();R.sansId=FETCH[0][0];
""")
check("X0 sous node : l'export s'execute", R is not None)
if R:
    f0 = R["fetch"][0] if R["fetch"] else [None, None, {}]
    check("X1 sans gabarit rien ; PNG par defaut a 1 s ; trois formats ; le bouton (avec title « gratuit ») ne part qu'UNE fois au double clic",
          R["sans"] and R["defaut"] == ["1", "png"] and R["formats"] == ["png", "jpeg", "webp"] and "gratuit" in R["titre"] and len(R["fetch"]) == 1, str(R["fetch"]))
    check("X2 il envoie le gabarit TEL QU'A L'ECRAN : cases de travail (sans _disp) fondues sur l'original, geometrie arrondie, metadonnees (echantillons) gardees ; instant « 1,5 » -> 1.5 ; format choisi",
          f0[0] == "/api/layout-templates/tpl_x/render-image" and f0[1] == "POST" and f0[2]["at_s"] == 1.5 and f0[2]["format"] == "webp"
          and f0[2]["template"]["metadata"] == {"samples": {"v": "a.png"}} and f0[2]["template"]["regions"] == [
              {"id": "v", "type": "video_slot", "slot_name": "v", "x": 10, "y": 21, "width": 100, "height": 51, "fit": "cover"}], json.dumps(f0)[:400])
    check("X3 succes : le nom du fichier depose est dit ; instant illisible : refuse SANS appel ; refus du serveur affiche tel quel ; gabarit sans id -> _editeur",
          "Ajoutée à la Bibliothèque : tpl_still_ab.webp" in R["msg"] and R["illisible"][0] == 0 and "Instant illisible" in R["illisible"][1]
          and "Format inconnu : gif" in R["refus"] and R["sansId"] == "/api/layout-templates/_editeur/render-image", f"{R['illisible']} {R['sansId']}")

print("\n[E] l'echantillon d'apercu")
R = node("""
var TPL={id:"t",metadata:{tags:["x"],samples:{autre:"b.png"}},regions:[]};var ETAT=TPL;function setTpl(f){ETAT=f(ETAT)}
function ec(rg,t){return DzEchantillon({rg:rg,tpl:t||ETAT,setTpl:setTpl})}
R.texte=ec({type:"text",slot_name:"t"})===null;R.sansNom=ec({type:"image_slot"})===null;
var RG={type:"video_slot",slot_name:"clip",slot_label:"Le clip"};var T=ec(RG);R.vide=[par(T,"img").length,par(T,"K").map(function(b){return b.p.children}),texte(T).indexOf("jamais au rendu vidéo")>=0];
var v0=__dzTplThumbV;bouton(T,"Choisir…").p.onClick();R.titre=PICK[0][0].titre;PICK[0][1]("photo 1.png");R.choisi=JSON.parse(JSON.stringify(ETAT.metadata));R.bump=__dzTplThumbV>v0;
T=ec(RG);R.plein=[par(T,"img")[0].p.src,par(T,"K").map(function(b){return [b.p.children,!!b.p.title]})];
bouton(T,"Changer…").p.onClick();PICK[1][1]("");R.vide2=ETAT.metadata.samples.clip;
bouton(ec(RG),"Retirer").p.onClick();R.retire=JSON.parse(JSON.stringify(ETAT.metadata));
ETAT={id:"t",metadata:{samples:{clip:"x.png"}},regions:[]};bouton(ec(RG),"Retirer").p.onClick();R.vide3=JSON.parse(JSON.stringify(ETAT.metadata));
ETAT=null;setTpl(function(A){return A});R.nul=ETAT;
""")
check("E0 sous node : l'echantillon s'execute", R is not None)
if R:
    check("E1 rien pour un texte ou une case sans nom ; sans echantillon : « Choisir… » et l'explication (jamais au rendu video)",
          R["texte"] and R["sansNom"] and R["vide"] == [0, ["Choisir…"], True], str(R["vide"]))
    check("E2 « Choisir… » ouvre la Bibliotheque titree au nom de la case ; le fichier choisi entre dans metadata.samples SANS toucher le reste ; la vignette sera redemandee",
          "Le clip" in R["titre"] and R["choisi"] == {"tags": ["x"], "samples": {"autre": "b.png", "clip": "photo 1.png"}} and R["bump"], str(R["choisi"]))
    check("E3 avec echantillon : sa miniature (nom encode), « Changer… » et « Retirer » (avec title) ; un choix vide ne change rien",
          R["plein"][0] == "/api/images/photo%201.png" and R["plein"][1] == [["Changer…", True], ["Retirer", True]] and R["vide2"] == "photo 1.png", str(R["plein"]))
    check("E4 « Retirer » enleve la case ; plus aucun echantillon -> la cle samples disparait",
          R["retire"] == {"tags": ["x"], "samples": {"autre": "b.png"}} and R["vide3"] == {}, f"{R['retire']} {R['vide3']}")

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3, __dzLibPicker x11)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 181
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3 and BUN.count("__dzLibPicker") == 11)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
