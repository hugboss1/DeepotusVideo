# -*- coding: utf-8 -*-
"""Plan-templates T1 (tache #72 du suivi, PR B, 03/10/2026) — les KITS DE MARQUE dans Reglages -> Branding, dans le
bundle LIVRE : le composant (couche du maillon montage) est extrait et EXECUTE sous node, fetch, dialogue maison et
rafraichissement du shell remplaces par des doublures qui notent tout.
DECISIONS DE L'UTILISATEUR (03/10) : les champs de l'ecran modifient le kit ACTIF ; le kit actif et le dernier ne se
suppriment pas (bouton grise, title qui dit pourquoi) ; tout passe par le dialogue maison.
Temoin positif : le bundle de la base (70f4d263) n'a pas l'ecran des kits.
Run (depuis backend/) : & $PY tests/test_brand_kits_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzkite_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "70f4d263"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a l'ecran Branding mais pas les kits", r0.returncode == 0 and b"function Sm(" in r0.stdout and b"DzKits" not in r0.stdout)
APPEL = 'reset any time."]}),r.jsx(DzKits,{onChange:function(){n(null);d(Date.now())}}),r.jsxs(jt,{style:{padding:18},children:['
k = BUN.find("function Sm(")
check("T2 l'ecran des kits est POSE dans Reglages -> Branding, entre l'introduction et les champs ; il remet les champs a zero et rafraichit le logo",
      BUN.count(APPEL) == 1 and 0 <= k < BUN.find(APPEL) < k + 4000 and BUN.count("r.jsx(DzKits,") == 1)


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


COUCHE = fonction("dzKitErr") + "\n" + fonction("DzKits")
check("T3 la couche livree a le composant (une fois)", BUN.count("function DzKits(") == 1 and "function DzKits(" in COUCHE)

HARNAIS = r"""
var H=[],hi=0,EFF=[],J=[],SAISIES=[],CONF=true,REP={},CHG=0;
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};var K="K",jt="Carte";
function Ji(){J.push(["Ji"])}
var ECOUTE={};var window={addEventListener:function(t,f){ECOUTE[t]=f},removeEventListener:function(t,f){if(ECOUTE[t]===f)delete ECOUTE[t]},__dzDialogue:{saisir:async function(m,o){J.push(["saisir",m,o.titre,o.valeur,o.ok]);return SAISIES.length?SAISIES.shift():null},
  confirmer:async function(m,o){J.push(["confirmer",m,o&&o.titre]);return CONF}}};
var LISTE={kits:[{id:"deepotus",name:"Deepotus",app_name:"DEEPOTUS",app_sub:"VIDEO",brand_color:"#ef4444",accent_color:"#00e5ff",actif:true,logo:false},
  {id:"kit_ab12cd34",name:"Client",app_name:"ACME",app_sub:"PROD",brand_color:"#112233",accent_color:"#ff8800",actif:false,logo:true}],actif:"deepotus"};
globalThis.fetch=async function(u,o){var m=String(o&&o.method||"GET"),b=o&&o.body?JSON.parse(o.body):null;J.push(["fetch",m,u,b]);
  var r=REP[m+" "+u]||(m==="GET"&&u==="/api/brand-kits"?{s:200,d:LISTE}:{s:200,d:{}});return {ok:r.s<300,status:r.s,json:async function(){return r.d}}};
var T=null;function rendre(){hi=0;T=DzKits({onChange:function(){CHG++}});EFF.splice(0).forEach(function(f){f()});return T}
async function attendre(){for(var i=0;i<20;i++)await new Promise(function(r){setImmediate(r)})}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(f(n))acc.push(n);var c=n.p&&n.p.children;
  if(Array.isArray(c))c.forEach(function(z){trouver(z,f,acc)});else if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function lignes(){return trouver(T,function(n){return n.p&&n.p.className==="dz-kit"})}
function bouton(ligne,txt){return trouver(ligne,function(n){return n.t==="K"&&n.p.children===txt})[0]}
function texteMsg(){var c=T.p.children;var m=c[c.length-1];return m?m.p.children:null}
async function demarrer(){H=[];EFF=[];J=[];CHG=0;rendre();await attendre();rendre();J=[]}
"""


def node(corps):
    f = _TMP / f"k{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
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


print("[E] l'ecran")
R = node("""
H=[];EFF=[];J=[];rendre();R.mount=J.slice();await attendre();rendre();
var L=lignes();R.lignes=L.map(function(l){var k=l.p.children;return {img:k[0].p.src,nom:k[1].p.children[0].p.children,
  actif:k[2].t==="span"?k[2].p.children:null,activer:k[2].t==="K"?k[2].p.title:null}});
var s0=bouton(L[0],"Supprimer"),s1=bouton(L[1],"Supprimer");R.supp=[[s0.p.disabled,s0.p.title],[s1.p.disabled,s1.p.title]];
R.titre=T.p.children[0].p.children[0].p.children;var nv=trouver(T,function(n){return n.t==="K"&&n.p.children==="Nouveau kit"})[0];R.nv=nv.p.title;
R.tous=trouver(T,function(n){return n.t==="K"}).every(function(b){return typeof b.p.title==="string"&&b.p.title.length>5});
J=[];ECOUTE["deepotus:brand-refresh"]();await attendre();rendre();R.rf={j:J.filter(function(z){return z[0]==="fetch"}),img:lignes()[0].p.children[0].p.src};
LISTE.kits=[LISTE.kits[0]];await demarrer();var s2=bouton(lignes()[0],"Supprimer");R.seul=[s2.p.disabled,s2.p.title];
""")
check("E0 sous node : l'ecran s'execute", R is not None)
if R:
    check("E1 au montage : la liste des kits (rien d'autre)", R["mount"] == [["fetch", "GET", "/api/brand-kits", None]], str(R["mount"]))
    check("E2 chaque kit : son logo (cache contourne), son nom ; l'actif porte « actif », les autres « Activer » avec un title qui dit la portee",
          R["lignes"][0]["img"] == "/api/brand-kits/deepotus/logo?t=0" and R["lignes"][0]["nom"] == "Deepotus" and R["lignes"][0]["actif"] == "actif"
          and R["lignes"][1]["actif"] is None and "prochains rendus" in (R["lignes"][1]["activer"] or "") and "garde le sien" in R["lignes"][1]["activer"], str(R["lignes"]))
    check("E3 l'en-tete dit QUEL kit les champs modifient ; tous les boutons ont un title",
          R["titre"] == "Kits de marque — les champs ci-dessous modifient « Deepotus »" and R["tous"] is True and "actif que si tu l’actives" in R["nv"], str(R["titre"]))
    check("E4 « Supprimer » GRISE sur le kit actif (title : activer un autre d'abord) ; le DERNIER kit est l'actif, son title le dit aussi",
          R["supp"][0][0] is True and "active d’abord un autre kit" in R["supp"][0][1] and R["supp"][1][0] is False
          and R["seul"][0] is True and "c’est aussi le dernier" in R["seul"][1], f"{R['supp']} {R['seul']}")

if R:
    check("E5 « Save brand »/« Reset »/logo de l'ecran (deepotus:brand-refresh) : la liste se RECHARGE et les logos aussi (sinon le kit actif garde ses anciennes couleurs)",
          R["rf"]["j"] == [["fetch", "GET", "/api/brand-kits", None]] and not R["rf"]["img"].endswith("?t=0"), str(R["rf"]))

print("\n[A] les actions")
R = node("""
await demarrer();var L=lignes();await bouton(L[1],"Activer").p.onClick();await attendre();rendre();
R.act={j:J.slice(),chg:CHG,msg:texteMsg()};
await demarrer();var nv=function(){return trouver(T,function(n){return n.t==="K"&&n.p.children==="Nouveau kit"})[0]};
SAISIES=[null];await nv().p.onClick();await attendre();R.nvAnn=J.slice();
J=[];SAISIES=["  Studio Nord  "];await nv().p.onClick();await attendre();rendre();R.nv={j:J.filter(function(z){return z[0]==="fetch"}),msg:texteMsg()};
await demarrer();SAISIES=["Client"];await bouton(lignes()[1],"Renommer").p.onClick();await attendre();R.renMeme=J.filter(function(z){return z[0]==="fetch"});
J=[];SAISIES=["Client B"];await bouton(lignes()[1],"Renommer").p.onClick();await attendre();R.ren=J.filter(function(z){return z[0]==="fetch"});
await demarrer();await bouton(lignes()[1],"Dupliquer").p.onClick();await attendre();rendre();R.dup={j:J.filter(function(z){return z[0]==="fetch"}),msg:texteMsg()};
await demarrer();CONF=false;await bouton(lignes()[1],"Supprimer").p.onClick();await attendre();R.suppAnn=J.slice();
J=[];CONF=true;await bouton(lignes()[1],"Supprimer").p.onClick();await attendre();rendre();R.supp={j:J,msg:texteMsg()};
await demarrer();REP["DELETE /api/brand-kits/kit_ab12cd34"]={s:400,d:{detail:"Le kit actif ne se supprime pas : activez-en un autre d'abord."}};
await bouton(lignes()[1],"Supprimer").p.onClick();await attendre();rendre();R.refus=texteMsg();REP={};
await demarrer();var p1=bouton(lignes()[1],"Dupliquer").p.onClick();var p2=bouton(lignes()[1],"Dupliquer").p.onClick();await p1;await p2;await attendre();
R.double=J.filter(function(z){return z[0]==="fetch"&&z[1]==="POST"}).length;
""")
check("A0 sous node : les actions s'executent", R is not None)
if R:
    f = [z for z in R["act"]["j"] if z[0] == "fetch"]
    check("A1 « Activer » : POST activate, liste rechargee, SHELL rafraichi (Ji) et champs de l'ecran remis a zero ; message",
          f[:2] == [["fetch", "POST", "/api/brand-kits/kit_ab12cd34/activate", None], ["fetch", "GET", "/api/brand-kits", None]]
          and ["Ji"] in R["act"]["j"] and R["act"]["chg"] == 1 and "« Client » actif" in (R["act"]["msg"] or ""), str(R["act"]))
    check("A2 « Nouveau kit » : nom demande par le dialogue maison ; annule -> rien ; donne -> POST {name} nettoye, liste rechargee, message",
          [z[0] for z in R["nvAnn"]] == ["saisir"] and R["nvAnn"][0][2:] == ["Nouveau kit de marque", "", "Créer"]
          and R["nv"]["j"] == [["fetch", "POST", "/api/brand-kits", {"name": "Studio Nord"}], ["fetch", "GET", "/api/brand-kits", None]]
          and "active-le pour le modifier" in (R["nv"]["msg"] or ""), f"{R['nvAnn']} {R['nv']}")
    check("A3 « Renommer » : meme nom -> rien ; nouveau -> POST {id, name}", R["renMeme"] == []
          and R["ren"][0] == ["fetch", "POST", "/api/brand-kits", {"id": "kit_ab12cd34", "name": "Client B"}], f"{R['renMeme']} {R['ren']}")
    check("A4 « Dupliquer » : POST dupliquer, liste rechargee, message (logo compris)",
          R["dup"]["j"][0] == ["fetch", "POST", "/api/brand-kits/kit_ab12cd34/dupliquer", None] and "logo compris" in (R["dup"]["msg"] or ""), str(R["dup"]))
    conf = [z for z in R["supp"]["j"] if z[0] == "confirmer"]
    check("A5 « Supprimer » : CONFIRME (nom, logo, irreversible) ; refuse -> rien ; accepte -> DELETE, liste rechargee",
          [z[0] for z in R["suppAnn"]] == ["confirmer"] and conf and "« Client » et son logo" in conf[0][1] and "irréversible" in conf[0][1]
          and ["fetch", "DELETE", "/api/brand-kits/kit_ab12cd34", None] in R["supp"]["j"] and "supprimé" in (R["supp"]["msg"] or ""), str(R["supp"]))
    check("A6 refus du serveur : SA phrase s'affiche", R["refus"] == "Le kit actif ne se supprime pas : activez-en un autre d'abord.", str(R["refus"]))
    check("A7 deux clics pendant une action (avant que l'ecran ne se redessine) : une seule part — deux clics = deux copies", R["double"] == 1, str(R["double"]))

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 180, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 180
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
