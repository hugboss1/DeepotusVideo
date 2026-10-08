# -*- coding: utf-8 -*-
"""Plan-studio T12 (tache #71 du suivi, PR C, 03/10/2026) — « Envoyer vers… » de la Bibliotheque : « Studio — nouveau
graphe » depuis un RENDU, « Lancer une recette… » depuis une IMAGE. Les fonctions de la couche (maillon montage) et le
menu __dzSendTo LIVRE sont extraits du bundle et EXECUTES sous node, menu, dialogues et fetch remplaces par des doublures.
DECISIONS DE L'UTILISATEUR (03/10) : trous = images + textes (chaque texte garde ou change) ; DEVIS du serveur montre et
confirme avant le lancement, et seul ce montant part en max_usd ; nom « Recette ».
Ce que le plan faisait faux, et que ce banc garde : son lancement depuis la Bibliotheque tirait SANS devis ni
confirmation ; son ancre ecrivait les accents en echappements (0 dans le bundle) ; son graphe neuf depuis un rendu
prenait la duree du registre (18,4 s) au lieu de celle du rendu.
Temoin positif : le bundle de la base (d29d3ad0) n'a aucune des deux entrees.
Run (depuis backend/) : & $PY tests/test_studio_envoyer.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzenv_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "d29d3ad0"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a « Envoyer vers » mais ni « Lancer une recette » ni « Studio — nouveau graphe »", r0.returncode == 0
      and b"function __dzSendTo(" in r0.stdout and b"dzSendRecette" not in r0.stdout and b"dzSendStudioRendu" not in r0.stdout)


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


NOMS = ("dzSendChoisir", "dzSendStudioRendu", "dzRecLancerAvec", "dzSendRecette", "__dzSendTo")
COUCHE = "\n".join(fonction(n) for n in NOMS)
check("T2 la couche livree a les quatre fonctions, une fois chacune, et le menu les appelle",
      all(BUN.count("function " + n + "(") == 1 for n in NOMS) and "items.push(dzSendRecette(nom,onClose));" in COUCHE
      and "items.push(dzSendStudioRendu(m,nom,onClose));" in COUCHE)

HARNAIS = r"""
var J=[],MENUS=[],CHOIX=[],SAISIES=[],CONF=true,REP={},HOTE=null,NAV=[],TOASTS=[];
var window={__dzDialogue:{informer:async function(m,o){J.push(["informer",m,o&&o.titre])},
  saisir:async function(m,o){J.push(["saisir",m,o.titre,o.valeur,o.ok]);return SAISIES.length?SAISIES.shift():o.valeur},
  confirmer:async function(m,o){J.push(["confirmer",m,o.titre,o.ok]);return CONF}}};
var document={getElementById:function(id){return id==="__dzSendHost"?HOTE:null}};
function __dzSendMenu(items,titre){MENUS.push({titre:titre,lbl:items.map(function(i){return i.lbl})});HOTE={};
  var c=CHOIX.shift();if(c===undefined)return;if(c===null){setTimeout(function(){HOTE=null},10);return}
  setTimeout(function(){HOTE=null;items[c].fn()},5)}
function __dzSendNav(v){NAV.push([v,window.__dzRenderGraph||null])}
function __dzToast(m){TOASTS.push(m)}
function __dzExtendClip(){}function __dzSendBible(){}function __dzToSpriteLab(){}function __dzSendSched(){}function __dzPrint3d(){}
globalThis.fetch=async function(u,o){var m=String(o&&o.method||"GET"),b=o&&o.body?JSON.parse(o.body):null;J.push(["fetch",m,u,b]);
  var r=REP[m+" "+u];if(r==="panne")throw new Error("hors ligne");r=r||{s:404,d:{detail:"inconnu"}};
  return {ok:r.s<300,status:r.s,json:async function(){return r.d}}};
async function attendre(){for(var i=0;i<40;i++)await new Promise(function(r){setTimeout(r,2)})}
function raz(){J=[];MENUS=[];CHOIX=[];SAISIES=[];CONF=true;REP={};HOTE=null;NAV=[];TOASTS=[];window.__dzRenderGraph=null}
var LISTE1={s:200,d:{graphs:[{id:"g1",name:"Matin",recette:2},{id:"g9",name:"Simple",recette:null}]}};
var REC1={s:200,d:{id:"g1",name:"Matin",trous:[{id:"t1",nature:"image",libelle:"Image n1 — image de départ",valeur:"depart.png"},
  {id:"t2",nature:"texte",libelle:"Text n6 — script de l'avatar",valeur:"Bonjour."}]}};
var DEVIS={s:200,d:{usd:2.838,generations:1,voix:1,reemplois:1}};
function fetchs(){return J.filter(function(z){return z[0]==="fetch"}).map(function(z){return z[1]+" "+z[2]})}
"""


sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE  # noqa: E402
# t141 (08/10) : la traduction L1 passe les libelles du menu par dzT ; le prelude (dictionnaire + dzT en FRANCAIS) est
# pose dans sa propre portee — son `var window` ne doit pas heurter le window du harnais ; dzT est publie sur
# globalThis et garde SON window (le dictionnaire). Les attentes francaises restent inchangees.
PRELUDE = "(function(){\n" + AIDE.PRELUDE_DZT + "\n})();\n"


def node(corps):
    f = _TMP / f"e{abs(hash(corps)) % 10**9}.js"
    f.write_text(PRELUDE + COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    try:
        p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except subprocess.TimeoutExpired:
        print("   (node) suspendu plus de 60 s : une promesse ne s'est jamais resolue")
        return None
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


print("[M] les entrees du menu")
R = node("""
raz();__dzSendTo({kind:"image",name:"autre.png"},function(){});R.img=MENUS[0];
raz();__dzSendTo({kind:"render",jobId:"j1",name:"Rendu du matin"},function(){});R.ren=MENUS[0];
""")
check("M0 sous node : le menu s'execute", R is not None)
if R:
    check("M1 IMAGE : « Lancer une recette… » juste apres « Studio — noeud Image », le devis annonce dans le libelle",
          R["img"]["lbl"][:3] == ["🎬 Studio — nœud Image", "🍳 Lancer une recette… (devis montré avant)", "⚡ Quick — image de départ"], str(R["img"]["lbl"][:4]))
    check("M2 RENDU : « Studio — nouveau graphe » apres « Prolonger », avant « Montage » ; titre du menu inchange",
          R["ren"]["lbl"][:3] == ["⚡ Prolonger le clip (+7 s, Veo 3.1 Fast, prix montré avant)", "🎬 Studio — nouveau graphe (Existing render → Render)",
                                  "🎞 Montage — clip vidéo"] and R["ren"]["titre"] == "Envoyer « Rendu du matin » vers…", str(R["ren"]))

print("\n[S] Studio — nouveau graphe depuis un rendu")
R = node("""
raz();REP["GET /api/jobs/j%201"]={s:200,d:{duration_real_s:7.04,duration_s:10}};var ferme=0;dzSendStudioRendu({jobId:"j 1"},"Rendu",function(){ferme++}).fn();await attendre();R.a={nav:NAV,ferme:ferme,f:fetchs()};
raz();REP["GET /api/jobs/j2"]={s:200,d:{duration_s:10}};dzSendStudioRendu({jobId:"j2"},"",null).fn();await attendre();R.b=NAV;
raz();REP["GET /api/jobs/j3"]="panne";dzSendStudioRendu({jobId:"j3"},"x",null).fn();await attendre();R.c=NAV;
""")
check("S0 sous node : l'entree s'execute", R is not None)
if R:
    g = R["a"]["nav"][0][1] if R["a"]["nav"] else {}
    check("S1 un graphe NEUF Existing render -> Render, a la DUREE REELLE du rendu (7,04 s -> 7 s), puis le Studio ; le menu se ferme",
          R["a"]["nav"][0][0] == "studio" and R["a"]["ferme"] == 1 and R["a"]["f"] == ["GET /api/jobs/j%201"] and g.get("name") == "Rendu.graph"
          and [n["type"] for n in g.get("nodes", [])] == ["ExistingRender", "Render"] and g["nodes"][0]["props"] == {"jobId": "j 1", "durationS": 7}
          and g.get("edges") == [{"id": "e1", "from": "er1", "fromPort": "out", "to": "rn1", "toPort": "in"}], str(R["a"]))
    check("S2 sans duree reelle : la duree du job ; job illisible : le graphe s'ouvre quand meme (sans duree inventee)",
          R["b"][0][1]["nodes"][0]["props"] == {"jobId": "j2", "durationS": 10} and R["b"][0][1]["name"] == "rendu.graph"
          and R["c"][0][1]["nodes"][0]["props"] == {"jobId": "j3"}, f"{R['b']} {R['c']}")

print("\n[L] Lancer une recette depuis une image")
R = node("""
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]=REC1;REP["POST /api/studio-graphs/g1/recette/devis"]=DEVIS;
REP["POST /api/studio-graphs/g1/recette/lancer"]={s:200,d:{job_id:"jx"}};
await dzRecLancerAvec("autre.png");R.ok={j:J,t:TOASTS,menus:MENUS};
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]=REC1;REP["POST /api/studio-graphs/g1/recette/devis"]=DEVIS;
REP["POST /api/studio-graphs/g1/recette/lancer"]={s:200,d:{job_id:"jx"}};SAISIES=["Salut."];await dzRecLancerAvec("autre.png");R.texte=J.filter(function(z){return z[0]==="fetch"&&z[1]==="POST"}).map(function(z){return z[3]});
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]=REC1;SAISIES=[null];await dzRecLancerAvec("autre.png");R.annSaisie=fetchs();
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]=REC1;REP["POST /api/studio-graphs/g1/recette/devis"]=DEVIS;CONF=false;await dzRecLancerAvec("autre.png");R.refus=fetchs();
""")
check("L0 sous node : le lancement s'execute", R is not None)
if R:
    j = R["ok"]["j"]
    sai = [z for z in j if z[0] == "saisir"]
    conf = [z for z in j if z[0] == "confirmer"]
    posts = [z for z in j if z[0] == "fetch" and z[1] == "POST"]
    check("L1 une seule recette : choisie d'office ; une seule image : remplacee d'office (aucun menu)", R["ok"]["menus"] == []
          and [z[2] for z in j if z[0] == "fetch" and z[1] == "GET"] == ["/api/studio-graphs", "/api/studio-graphs/g1/recette"], str(j[:3]))
    check("L2 chaque TEXTE est montre avec sa valeur d'origine, a garder ou changer (dialogue maison, « Suivant »)",
          sai == [["saisir", "Text n6 — script de l'avatar — garde-le ou change-le :", "Recette « Matin » (1/1)", "Bonjour.", "Suivant"]], str(sai))
    check("L3 le DEVIS est demande au serveur avec les valeurs ; un texte garde n'est pas envoye",
          posts[0][2] == "/api/studio-graphs/g1/recette/devis" and posts[0][3] == {"valeurs": {"t1": "autre.png"}}, str(posts[:1]))
    check("L4 la CONFIRMATION dit la recette, l'image, le montant, les generations, la voix, les reemplois gratuits et la regle du plafond",
          len(conf) == 1 and "Lancer « Matin » avec « autre.png » : ≈ $2.84 — 1 génération(s), 1 voix off, 1 nœud(s) réemployé(s) gratuitement" in conf[0][1]
          and "refusé avant toute génération" in conf[0][1] and conf[0][2:] == ["Lancer la recette", "Lancer ($2.84)"], str(conf))
    check("L5 confirme : le lancement part avec les MEMES valeurs et max_usd = le devis EXACT ; un toast le dit",
          posts[1][2] == "/api/studio-graphs/g1/recette/lancer" and posts[1][3] == {"valeurs": {"t1": "autre.png"}, "max_usd": 2.838}
          and len(posts) == 2 and R["ok"]["t"] == ["Recette « Matin » lancée (≈ $2.84) — le rendu est dans la file"], f"{posts} {R['ok']['t']}")
    check("L6 un texte CHANGE part au devis et au lancement", R["texte"][0] == {"valeurs": {"t1": "autre.png", "t2": "Salut."}}
          and R["texte"][1]["valeurs"] == {"t1": "autre.png", "t2": "Salut."}, str(R["texte"]))
    check("L7 annuler un texte : ni devis ni lancement ; refuser la confirmation : pas de lancement",
          R["annSaisie"] == ["GET /api/studio-graphs", "GET /api/studio-graphs/g1/recette"]
          and R["refus"] == ["GET /api/studio-graphs", "GET /api/studio-graphs/g1/recette", "POST /api/studio-graphs/g1/recette/devis"], f"{R['annSaisie']} {R['refus']}")

R = node("""
var DEUX={s:200,d:{graphs:[{id:"g1",name:"Matin",recette:2},{id:"g2",name:"Soir",recette:3}]}};
var REC2={s:200,d:{id:"g2",name:"Soir",trous:[{id:"t1",nature:"image",libelle:"Image a — image de départ",valeur:"a.png"},{id:"t2",nature:"image",libelle:"Image b — image",valeur:"b.png"}]}};
raz();REP["GET /api/studio-graphs"]=DEUX;REP["GET /api/studio-graphs/g2/recette"]=REC2;REP["POST /api/studio-graphs/g2/recette/devis"]=DEVIS;CONF=false;CHOIX=[1,1];
await dzRecLancerAvec("neuve.png");await attendre();R.choix={menus:MENUS,posts:J.filter(function(z){return z[0]==="fetch"&&z[1]==="POST"}).map(function(z){return z[3]})};
raz();REP["GET /api/studio-graphs"]=DEUX;CHOIX=[null];await dzRecLancerAvec("neuve.png");await attendre();R.annMenu=fetchs();
raz();REP["GET /api/studio-graphs"]={s:200,d:{graphs:[{id:"g9",name:"Simple",recette:null}]}};await dzRecLancerAvec("x.png");R.aucune=J.slice();
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]={s:200,d:{name:"Matin",trous:[{id:"t1",nature:"texte",libelle:"x",valeur:"y"}]}};
await dzRecLancerAvec("x.png");R.sansImage=J.filter(function(z){return z[0]==="informer"});
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]=REC1;REP["POST /api/studio-graphs/g1/recette/devis"]={s:400,d:{detail:"Image n1 — image de départ : « x.png » est absente de la Bibliothèque."}};
await dzRecLancerAvec("x.png");R.devisKo=J.filter(function(z){return z[0]!=="fetch"&&z[0]!=="saisir"});
raz();REP["GET /api/studio-graphs"]=LISTE1;REP["GET /api/studio-graphs/g1/recette"]=REC1;REP["POST /api/studio-graphs/g1/recette/devis"]=DEVIS;
REP["POST /api/studio-graphs/g1/recette/lancer"]={s:402,d:{detail:"Estimation 3.10 $ au-dessus du plafond accepté (2.84 $)."}};await dzRecLancerAvec("x.png");
R.lanceKo={inf:J.filter(function(z){return z[0]==="informer"}),t:TOASTS};
raz();REP["GET /api/studio-graphs"]="panne";await dzRecLancerAvec("x.png");R.panne=J.filter(function(z){return z[0]==="informer"});
raz();var f=0;var it=dzSendRecette("y.png",function(){f++});REP["GET /api/studio-graphs"]={s:200,d:{graphs:[]}};it.fn();await attendre();R.item={lbl:it.lbl,ferme:f,inf:J.filter(function(z){return z[0]==="informer"}).length};
""")
check("L8 sous node : les cas limites s'executent", R is not None)
if R:
    check("L9 plusieurs recettes : menu (nom + nombre de sources, sans les graphes simples) ; plusieurs images : menu (libelle + image actuelle) ; le choix part",
          R["choix"]["menus"] == [{"titre": "Lancer quelle recette avec « neuve.png » ?", "lbl": ["🍳 Matin — 2 source(s)", "🍳 Soir — 3 source(s)"]},
                                  {"titre": "« neuve.png » remplace quelle image ?", "lbl": ["Image a — image de départ (aujourd’hui : a.png)", "Image b — image (aujourd’hui : b.png)"]}]
          and R["choix"]["posts"] == [{"valeurs": {"t2": "neuve.png"}}], str(R["choix"]))
    check("L10 menu ANNULE : rien ne part (la promesse se resout, rien ne reste suspendu)", R["annMenu"] == ["GET /api/studio-graphs"], str(R["annMenu"]))
    check("L11 aucune recette : dit (avec le bouton a utiliser) ; une recette sans image : dit", R["aucune"][-1][0] == "informer" and "« Recette »" in R["aucune"][-1][1]
          and len([z for z in R["aucune"] if z[0] == "fetch"]) == 1 and "aucune image" in R["sansImage"][0][1], f"{R['aucune']} {R['sansImage']}")
    check("L12 devis refuse : SA phrase (titre « Devis impossible »), sans confirmation ; lancement refuse (402) : SA phrase, pas de toast",
          R["devisKo"] == [["informer", "Image n1 — image de départ : « x.png » est absente de la Bibliothèque.", "Devis impossible"]]
          and R["lanceKo"]["inf"] == [["informer", "Estimation 3.10 $ au-dessus du plafond accepté (2.84 $).", "Lancement refusé"]] and R["lanceKo"]["t"] == [],
          f"{R['devisKo']} {R['lanceKo']}")
    check("L13 serveur injoignable : dit ; l'entree du menu ferme le menu puis lance le parcours",
          R["panne"] and "hors ligne" in R["panne"][0][1] and R["item"] == {"lbl": "🍳 Lancer une recette… (devis montré avant)", "ferme": 1, "inf": 1}, f"{R['panne']} {R['item']}")

check("T3 aucun prompt/alert/confirm natif dans la couche neuve ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      all(x not in "\n".join(fonction(n) for n in NOMS[:4]) for x in ("window.prompt(", "window.confirm(", "alert(")) and BUN.count("DzTracks") == 181
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
