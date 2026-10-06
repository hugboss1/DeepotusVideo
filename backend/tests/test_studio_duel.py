# -*- coding: utf-8 -*-
"""Plan-studio T11 (tache #71 du suivi, PR B, 03/10/2026) — le DUEL DE MOTEURS sur un noeud Image gen, dans le bundle
LIVRE : le panneau (couche du maillon montage) est extrait et EXECUTE sous node, fetch, dialogue maison et generateur
remplaces par des doublures qui notent tout (aucun appel paye).
DECISIONS DE L'UTILISATEUR (03/10) : Image gen seulement ; cout des DEUX annonce et CONFIRME avant le tir ; la perdante
reste dans la Bibliotheque.
Ce que le plan faisait faux, et que ce banc garde : il chiffrait le champion « flux » quand le noeud n'a pas de modele,
alors que le tir part avec le modele choisi dans l'app ou le defaut du serveur ; il n'annoncait pas le cout avant ; il
ecrivait une epingle et une pile inexistantes pour un noeud Image gen (#67 : Seedance et HeyGen seulement).
Temoin positif : le bundle de la base (e02826cb) n'a pas le duel.
Run (depuis backend/) : & $PY tests/test_studio_duel.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzduel_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "e02826cb"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : le bundle de la base a le panneau Image gen mais pas le duel", r0.returncode == 0
      and b"function DzImageGenPanel(" in r0.stdout and b"DzDuelPanel" not in r0.stdout)
GREFFE = ('(e.type==="Seedance"||e.type==="HeyGenAvatar")&&r.jsx(DzPinPanel,{node:e,graph:t,onUpdate:o}),'
          'e.type==="ImageGen"&&r.jsx(DzDuelPanel,{node:e,graph:t,onUpdate:o}),')
check("T2 le duel est monte dans l'inspecteur d'un noeud Image gen, a cote de l'epingle (jamais dans DzImageGenPanel)",
      BUN.count(GREFFE) == 1 and BUN.count("r.jsx(DzDuelPanel,") == 1 and "DzDuelPanel" not in BUN[BUN.find("function DzImageGenPanel("):BUN.find("function DzImgProcPanel(")])


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


COUCHE = "\n".join(fonction(n) for n in ("dzDuelPrompt", "dzDuelChampion", "dzDuelLabel", "dzDuelUsd", "DzDuelPanel"))
check("T3 la couche livree a le duel (cinq fonctions, une fois chacune)", all(BUN.count("function " + n + "(") == 1
      for n in ("dzDuelPrompt", "dzDuelChampion", "dzDuelLabel", "dzDuelUsd", "DzDuelPanel")) and "function DzDuelPanel(" in COUCHE)

HARNAIS = r"""
var H=[],hi=0,EFF=[],J=[],UPD=[],LS={dz_image_model:""},LSCASSE=false,CONF=true,EST=null,GEN={},PEND=[];
var MM={default:"flux",models:[{id:"flux",label:"FLUX schnell"},{id:"nano-banana",label:"Nano Banana (Gemini)"},{id:"gpt-image-2-fal",label:"GPT Image 2 (via fal)"}]};
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};var K="K";var DzImgModelSel="Sel";
var localStorage={getItem:function(k){if(LSCASSE)throw new Error("stockage interdit");return LS[k]||null}};
var D={imageUrl:function(f){return "/api/images/"+f},
  generateImage:function(p,n,s,m){J.push(["gen",p,n,s,m]);return new Promise(function(res,rej){PEND.push({m:m,res:res,rej:rej})})}};
var window={__dzDialogue:{confirmer:async function(m,o){J.push(["confirmer",m,o&&o.titre,o&&o.ok]);return CONF}}};
globalThis.fetch=async function(u,o){J.push(["fetch",u,o?JSON.parse(o.body):null]);
  if(u==="/api/image-models")return {ok:true,json:async function(){return MM}};
  if(u==="/api/cost/estimate"){if(EST==="ko")return {ok:false,json:async function(){return {}}};return {ok:true,json:async function(){return EST}}}
  return {ok:false}};
function Wt(g,id,port){var e=(g.edges||[]).find(function(z){return z.to===id&&z.toPort===port});return e?(g.nodes||[]).find(function(n){return n.id===e.from}):null}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(f(n))acc.push(n);var c=n.p&&n.p.children;
  if(Array.isArray(c))c.forEach(function(z){trouver(z,f,acc)});else if(c&&typeof c==="object")trouver(c,f,acc);return acc}
async function attendre(){for(var i=0;i<12;i++)await new Promise(function(r){setImmediate(r)})}
var NOEUD={id:"ig",type:"ImageGen",props:{model:"",size:"square_hd",duelModel:"nano-banana"}};
var GRAPHE={nodes:[{id:"pr",type:"Prompt",props:{value:"  un poulpe sur un trone  "}},NOEUD],edges:[{from:"pr",to:"ig",toPort:"prompt",fromPort:"out"}]};
function rendre(noeud,graphe){hi=0;var T=DzDuelPanel({node:noeud||NOEUD,graph:graphe||GRAPHE,onUpdate:function(pp){UPD.push(pp)}});
  EFF.splice(0).forEach(function(f){f()});return T}
function bouton(T){return trouver(T,function(n){return n.t==="K"&&n.p.children!=="Garder"})[0]}
function texte(T){var d=T.p.children[T.p.children.length-1];return d.p.children}
"""


def node(corps):
    f = _TMP / f"d{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


print("[P] les regles")
R = node("""
R.prompt=[dzDuelPrompt(GRAPHE,{id:"ig",props:{prompt:"ecrit dans le panneau"}}),dzDuelPrompt({nodes:[],edges:[]},{id:"z",props:{prompt:" ecrit "}}),dzDuelPrompt({nodes:[],edges:[]},{id:"z",props:{}})];
R.champ=[dzDuelChampion({model:"gpt-image-2-fal"},MM)];LS.dz_image_model="nano-banana";R.champ.push(dzDuelChampion({model:""},MM));
LS.dz_image_model="";R.champ.push(dzDuelChampion({},{default:"nano-banana-pro"}));R.champ.push(dzDuelChampion({},null));
LSCASSE=true;R.champ.push(dzDuelChampion({},MM));LSCASSE=false;
R.lab=[dzDuelLabel(MM,"nano-banana"),dzDuelLabel(MM,"inconnu"),dzDuelLabel(null,"flux")];
R.usd=[dzDuelUsd({breakdown:[{usd:0.039},{usd:0.003}]},1),dzDuelUsd({breakdown:[{usd:"x"}]},0),dzDuelUsd(null,0),dzDuelUsd({lines:[{usd:1}]},0)];
""")
check("P0 sous node : les regles s'executent", R is not None)
if R:
    check("P1 le prompt : le noeud Prompt/Text BRANCHE l'emporte sur le prompt ecrit (comme « Generer »), nettoye ; sinon celui ecrit",
          R["prompt"] == ["un poulpe sur un trone", "ecrit", ""], str(R["prompt"]))
    check("P2 le champion est le modele EFFECTIF : celui du noeud, sinon celui choisi dans l'app, sinon le defaut du serveur, sinon flux ; "
          "un stockage interdit ne casse rien", R["champ"] == ["gpt-image-2-fal", "nano-banana", "nano-banana-pro", "flux", "flux"], str(R["champ"]))
    check("P3 libelle du catalogue (l'id s'il est inconnu) ; le cout vient du « breakdown » du devis (rien d'autre, rien d'invente)",
          R["lab"] == ["Nano Banana (Gemini)", "inconnu", "flux"] and R["usd"] == [0.003, None, None, None], f"{R['lab']} {R['usd']}")

print("\n[F] le duel")
R = node("""
EST={breakdown:[{usd:0.003},{usd:0.039}],total_usd:0.042};
var T=rendre();await attendre();T=rendre();
R.mount=J.filter(function(z){return z[0]==="fetch"}).map(function(z){return z[1]});
var b=bouton(T);R.btn={title:b.p.title,ch:b.p.children,dis:b.p.disabled};
var sel=trouver(T,function(n){return n.t==="Sel"})[0];sel.p.onChange("gpt-image-2-fal");R.sel=UPD.slice();UPD=[];
J=[];CONF=false;await b.p.onClick();await attendre();R.annule=J.slice();
J=[];CONF=true;var p=b.p.onClick();await attendre();R.avant=J.slice();
var p2=b.p.onClick();await attendre();R.double=J.filter(function(z){return z[0]==="gen"}).length;
PEND[0].res({images:["champ.png"]});PEND[1].res({images:["chall.png"]});await p;await attendre();T=rendre();
var cartes=trouver(T,function(n){return n.p&&n.p.className==="dz-duel-carte"});
R.cartes=cartes.map(function(c){var k=c.p.children;return {img:k[0].p.src,lab:k[1].p.children,cout:k[2].p.children.replace(/[0-9.]+ s$/,"N s"),
  garder:k[3]&&{ch:k[3].p.children,title:k[3].p.title}}});
R.msg=texte(T);
cartes[1].p.children[3].p.onClick();T=rendre();R.garde=UPD.slice();R.msg2=texte(T);
""")
check("F0 sous node : le duel s'execute", R is not None)
if R:
    conf = [z for z in R["avant"] if z[0] == "confirmer"]
    est = [z for z in R["avant"] if z[0] == "fetch" and z[1] == "/api/cost/estimate"]
    gen = [z for z in R["avant"] if z[0] == "gen"]
    check("F1 au montage : le catalogue des modeles (rien d'autre) ; « Lancer le duel » AVEC title qui dit que les deux sont payees",
          R["mount"] == ["/api/image-models"] and R["btn"]["ch"] == "Lancer le duel" and R["btn"]["dis"] is False
          and "DEUX images sont payées" in (R["btn"]["title"] or "") and "confirmé avant le tir" in R["btn"]["title"], str(R["btn"]))
    check("F2 le challenger se choisit dans le catalogue et se garde sur le noeud (props.duelModel)", R["sel"] == [{"duelModel": "gpt-image-2-fal"}], str(R["sel"]))
    check("F3 le DEVIS precede tout : les deux modeles EFFECTIFS (flux par defaut serveur, nano-banana), une image chacun",
          len(est) == 1 and est[0][2] == {"kind": "campaign", "ops": [{"kind": "image", "model": "flux", "n": 1}, {"kind": "image", "model": "nano-banana", "n": 1}]}, str(est))
    check("F4 la CONFIRMATION dit les deux noms, les deux couts, le total et que la perdante reste ; bouton « Lancer le duel »",
          len(conf) == 1 and "« FLUX schnell » ≈ $0.003" in conf[0][1] and "« Nano Banana (Gemini) » ≈ $0.039" in conf[0][1]
          and "≈ $0.042 au total" in conf[0][1] and "Bibliothèque" in conf[0][1] and conf[0][2:] == ["Duel de moteurs", "Lancer le duel"], str(conf))
    check("F5 confirmation refusee : RIEN n'est genere", [z[0] for z in R["annule"]] == ["fetch", "confirmer"]
          and not any(z[0] == "gen" for z in R["annule"]), str(R["annule"]))
    check("F6 confirme : les DEUX tirs partent EN PARALLELE (meme prompt, une image, meme cadre), avant qu'aucun ne revienne",
          gen == [["gen", "un poulpe sur un trone", 1, "square_hd", "flux"], ["gen", "un poulpe sur un trone", 1, "square_hd", "nano-banana"]], str(gen))
    check("F7 un second clic pendant le duel (meme avant que l'ecran ne se redessine) ne relance RIEN : deux duels = deux fois paye",
          R["double"] == 2, str(R["double"]))
    check("F8 deux cartes cote a cote : l'image, le modele, le cout estime et la duree mesuree, « Garder » avec title",
          R["cartes"] == [{"img": "/api/images/champ.png", "lab": "FLUX schnell", "cout": "≈ $0.003 · N s",
                           "garder": {"ch": "Garder", "title": "Ce modèle gagne : son image devient celle du nœud ; l’autre reste dans la Bibliothèque"}},
                          {"img": "/api/images/chall.png", "lab": "Nano Banana (Gemini)", "cout": "≈ $0.039 · N s",
                           "garder": {"ch": "Garder", "title": "Ce modèle gagne : son image devient celle du nœud ; l’autre reste dans la Bibliothèque"}}]
          and "Choisis le gagnant" in R["msg"], str(R["cartes"]) + R["msg"])
    check("F9 « Garder » le challenger : son image devient CELLE DU NOEUD (props.filename, rien d'autre) ; l'autre reste en Bibliotheque",
          R["garde"] == [{"filename": "chall.png"}] and "Nano Banana (Gemini) » gagne" in R["msg2"] and "Bibliothèque" in R["msg2"], f"{R['garde']} {R['msg2']}")

R = node("""
EST={breakdown:[{usd:0.003},{usd:0.039}],total_usd:0.042};
var T=rendre();await attendre();T=rendre();J=[];var p=bouton(T).p.onClick();await attendre();
PEND[0].res({images:["a.png"]});PEND[1].res({error:"Nano Banana : quota fal depasse"});await p;await attendre();T=rendre();
var cartes=trouver(T,function(n){return n.p&&n.p.className==="dz-duel-carte"});
R.k=cartes.map(function(c){return c.p.children.map(function(z){return z&&z.p&&typeof z.p.children==="string"?z.p.children:(z&&z.t)})});R.msg=texte(T);
PEND=[];var T2=rendre();J=[];var p2=bouton(T2).p.onClick();await attendre();PEND[0].rej(new Error("reseau coupe"));PEND[1].res({images:["b.png"]});await p2;await attendre();T2=rendre();
R.k2=trouver(T2,function(n){return n.p&&n.p.className==="dz-duel-carte"})[0].p.children[0].p.children;
H=[];EFF=[];EST="ko";T=rendre();await attendre();T=rendre();J=[];await bouton(T).p.onClick();await attendre();T=rendre();R.ko=J.slice();R.kmsg=texte(T);
H=[];EFF=[];EST={breakdown:[{usd:0.003},{usd:0.039}],total_usd:0.042};T=rendre({id:"ig",type:"ImageGen",props:{duelModel:"nano-banana"}},{nodes:[],edges:[]});await attendre();
T=rendre({id:"ig",type:"ImageGen",props:{duelModel:"nano-banana"}},{nodes:[],edges:[]});J=[];await bouton(T).p.onClick();await attendre();
T=rendre({id:"ig",type:"ImageGen",props:{duelModel:"nano-banana"}},{nodes:[],edges:[]});R.sans=J.slice();R.smsg=texte(T);
H=[];EFF=[];var N2={id:"ig",type:"ImageGen",props:{model:"flux",duelModel:"flux",prompt:"x"}};T=rendre(N2,{nodes:[],edges:[]});await attendre();T=rendre(N2,{nodes:[],edges:[]});
R.meme=bouton(T).p.disabled;J=[];await bouton(T).p.onClick();await attendre();R.meme2=J.slice();
H=[];EFF=[];var N3={id:"ig",type:"ImageGen",props:{prompt:"x"}};T=rendre(N3,{nodes:[],edges:[]});await attendre();T=rendre(N3,{nodes:[],edges:[]});R.vide=bouton(T).p.disabled;
""")
check("F10 sous node : les echecs s'executent", R is not None)
if R:
    check("F11 un tir ECHOUE : sa carte dit l'erreur du fournisseur, sans « Garder » ; le message le dit ; l'autre reste gardable",
          R["k"][1][0] == "Échec : Nano Banana : quota fal depasse" and R["k"][1][3] is None and R["k"][0][3] == "Garder"
          and "a échoué" in R["msg"] and R["k2"].startswith("Échec : reseau coupe"), f"{R['k']} {R['msg']} {R['k2']}")
    check("F12 devis impossible : dit, SANS confirmation ni tir", [z[0] for z in R["ko"]] == ["fetch"] and "Devis impossible" in R["kmsg"], f"{R['ko']} {R['kmsg']}")
    check("F13 sans prompt : dit, SANS devis ni tir ; meme modele que le champion ou aucun challenger : bouton grise, rien ne part",
          R["sans"] == [] and "Prompt" in R["smsg"] and R["meme"] is True and R["meme2"] == [] and R["vide"] is True, f"{R['sans']} {R['smsg']} {R['meme']} {R['vide']}")

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 180, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 180
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
