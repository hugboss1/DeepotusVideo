# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR D (plan-library T12-T13, 04/10/2026) — CLIP en LOCAL a l'ecran, dans le bundle LIVRE :
DzClipBloc (installer, indexer, suivre), DzSemblables (sous la fiche) et le selecteur de DzRecherche sont extraits et
EXECUTES sous node (fetch et dialogue maison simules : rien n'est telecharge).
DECISIONS DE L'UTILISATEUR (04/10) : version legere ≈ 186 Mo, annoncee AVANT le telechargement par le dialogue maison ;
CLIP comprend l'ANGLAIS : le selecteur le dit.
Temoin positif : le bundle de la base (64f12040) n'a pas CLIP a l'ecran.
Run (depuis backend/) : & $PY tests/test_library_clip_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE  # t141 : dzT (prelude node) et textes francais des cles
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzclipe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "64f12040"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la recherche mais pas CLIP a l'ecran", r0.returncode == 0 and b"function DzRecherche(" in r0.stdout
      and b"DzClipBloc" not in r0.stdout and b"DzSemblables" not in r0.stdout)
check("T2 la fiche porte « ≈ Images semblables » (une fois, avec la liste chargee et l'ouverture) ; la recherche porte le bloc CLIP",
      BUN.count("r.jsx(DzSemblables,{m:m,liste:l,ouvrir:y})") == 1 and BUN.count("r.jsx(DzClipBloc,{et:clip,setEt:setClip})") == 1)


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


NOMS = ("dzUsdLeg", "dzMo", "DzClipBloc", "DzSemblables", "DzRecherche")
k = BUN.find("var DZ_MOTEURS=")
MOT = BUN[k:BUN.find("]];", k) + 3] if k >= 0 else ""
COUCHE = MOT + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a ses fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS) and MOT != "")

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={},DIAL=[],DREP=true,INTER=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f,d){EFF.push(f)},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{confirmer:async function(m,o){DIAL.push([m,o]);return DREP}}};
var setInterval=function(f,ms){INTER.push([f,ms]);return INTER.length},clearInterval=function(){};
async function fetch(u,o){var m=o&&o.method||"GET";FETCH.push([u,m]);var q=REP[m+" "+u];
  await new Promise(function(s){setTimeout(s,3)});if(typeof q==="function")q=q();
  return {ok:!!q&&!q.__ko,status:q&&q.__ko?q.__ko:(q?200:404),json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
function boutons(T,debut){return trouver(T,function(n){return n.t==="K"&&String(n.p.children).indexOf(debut)===0})}
async function attendre(){await new Promise(function(s){setTimeout(s,40)})}
var ET=null;function setEt(e){ET=e}
function bloc(){hi=0;EFF=[];return DzClipBloc({et:ET,setEt:setEt})}
function semb(p){hi=0;EFF=[];return DzSemblables(p)}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    # t141 (08/10) : la couche passe ses textes par dzT -> le prelude AVANT (constantes evaluees au chargement),
    # et de nouveau APRES le harnais, dont le `var window=` remplace l'objet qui portait DZ_I18N.
    f.write_text(AIDE.PRELUDE_DZT + "\n" + COUCHE + "\n" + HARNAIS + "\n" + AIDE.PRELUDE_DZT + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R));process.exit(0)})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-600:])
        return None


R = node("""
var NI={installe:false,octets:185581726,indexees:0,a_indexer:0,installation:{en_cours:false,fait:0,total:185581726,etape:"",erreur:""},index:{en_cours:false}};
ET=NI;var T=bloc();R.txt=texte(T);var b=boutons(T,"Installer CLIP")[0];R.b=[b.p.children,b.p.title];R.inter0=INTER.length;
DREP=false;FETCH=[];await b.p.onClick();R.annule=[DIAL.length,FETCH.length];R.dial=DIAL[0];
DREP=true;DIAL=[];FETCH=[];REP["POST /api/library/clip/installer"]={lance:true,octets:185581726};
var EN={installe:false,octets:185581726,indexees:0,a_indexer:0,installation:{en_cours:true,fait:52428800,total:185581726,etape:"numpy-2.5.3",erreur:""},index:{en_cours:false}};
REP["GET /api/library/clip/etat"]=EN;var b2=boutons(bloc(),"Installer CLIP")[0];var p1=b2.p.onClick(),p2=b2.p.onClick();await p1;await p2;await attendre();
R.post=FETCH.filter(function(f){return f[1]==="POST"}).length;R.dial2=DIAL.length;var T2=bloc();R.suivi=texte(T2);R.bEnCours=boutons(T2,"Installer").length;
EFF.forEach(function(f){f()});R.inter=INTER.map(function(i){return i[1]});
var FIN={installe:true,octets:185581726,indexees:0,a_indexer:7,installation:{en_cours:false,fait:185581726,total:185581726,etape:"",erreur:""},index:{en_cours:false}};
REP["GET /api/library/clip/etat"]=FIN;FETCH=[];INTER[INTER.length-1][0]();await attendre();R.poll=FETCH.map(function(f){return f[0]});var T3=bloc();R.fin=texte(T3);
var bi=boutons(T3,"Indexer")[0];R.bi=[bi.p.children,bi.p.title];DIAL=[];FETCH=[];REP["POST /api/library/clip/indexer"]={lance:true};
REP["GET /api/library/clip/etat"]={installe:true,octets:1,indexees:2,a_indexer:5,installation:{en_cours:false},index:{en_cours:true,faits:2,total:7}};
await bi.p.onClick();await attendre();R.idx=[DIAL.length,FETCH.filter(function(f){return f[1]==="POST"}).map(function(f){return f[0]})];R.idxTxt=texte(bloc());
ET={installe:true,octets:1,indexees:7,a_indexer:0,installation:{en_cours:false},index:{en_cours:false}};var T4=bloc();R.pret=[texte(T4),boutons(T4,"Indexer").length,boutons(T4,"Installer").length];
ET={installe:false,octets:185581726,installation:{en_cours:false,erreur:"numpy-2.5.3 : empreinte inattendue"},index:{}};R.err=texte(bloc());
H=[];ET=NI;REP["POST /api/library/clip/installer"]={__ko:409,detail:"Une installation de CLIP est déjà en cours."};await boutons(bloc(),"Installer CLIP")[0].p.onClick();await attendre();R.refus=texte(bloc());
ET=null;R.nul=bloc();
""")
check("B0 sous node : le bloc CLIP s'execute", R is not None)
if R:
    check("B1 non installe : la TAILLE est dite (≈ 177 Mo), gratuit, tout reste sur ce PC ; le bouton porte la taille (title : versions figees)",
          "CLIP n’est pas installé — 177 Mo à télécharger" in R["txt"] and "tout reste sur ce PC" in R["txt"]
          and R["b"][0] == "Installer CLIP (177 Mo)" and "empreintes" in R["b"][1] and R["inter0"] == 0, R["txt"] + str(R["b"]))
    check("B2 le dialogue maison ANNONCE la taille et les sources AVANT tout ; annule : RIEN ne part",
          R["annule"] == [1, 0] and "177 Mo" in R["dial"][0] and "PyPI" in R["dial"][0] and "Hugging Face" in R["dial"][0]
          and R["dial"][1]["ok"] == "Installer (177 Mo)", str(R["dial"]))
    check("B3 confirme : UN lancement au double clic ; l'avancement est dit (Mo / Mo, etape), le bouton disparait",
          R["post"] == 1 and R["dial2"] == 1 and "Installation de CLIP : 50 Mo / 177 Mo — numpy-2.5.3" in R["suivi"] and R["bEnCours"] == 0, R["suivi"])
    check("B4 le suivi relit l'etat toutes les 2 s pendant le travail ; installe : « Indexer (7) » (title : sur ce PC, gratuit)",
          R["inter"] == [2000] and R["poll"] == ["/api/library/clip/etat"] and "0 image(s) indexée(s) · 7 à indexer" in R["fin"]
          and R["bi"][0] == "Indexer (7)" and "gratuit" in R["bi"][1], str(R["inter"]) + R["fin"])
    check("B5 indexer : SANS dialogue (gratuit, local), un POST ; l'avancement de l'index est dit",
          R["idx"] == [0, ["/api/library/clip/indexer"]] and "Index CLIP : 2 / 7" in R["idxTxt"], str(R["idx"]) + R["idxTxt"])
    check("B6 pret : le nombre indexe, plus de bouton ; une installation echouee DIT pourquoi ; un refus du serveur est dit ; sans etat : rien",
          "CLIP : 7 image(s) indexée(s)" in R["pret"][0] and R["pret"][1:] == [0, 0] and "Installation échouée : numpy-2.5.3 : empreinte inattendue" in R["err"]
          and "Refusé : Une installation de CLIP est déjà en cours." in R["refus"] and R["nul"] is None, str(R["pret"]) + R["err"] + R["refus"])

R = node("""
var LISTE=[{name:"a.png",kind:"image"},{name:"b.png",kind:"image"}],OUV=[];
var P={m:{name:"a.png",kind:"image"},liste:LISTE,ouvrir:function(z){OUV.push(z.name)}};
var T=semb(P);var b=boutons(T,"≈ Images semblables")[0];R.b=[b.p.children,b.p.title];
REP["GET /api/library/semblables/a.png"]={filename:"a.png",semblables:[{filename:"b.png",score:0.91},{filename:"zz.png",score:0.5}]};
FETCH=[];var p1=b.p.onClick(),p2=b.p.onClick();await p1;await p2;R.fetch=FETCH.map(function(f){return f[0]});
var T2=semb(P);var c=trouver(T2,function(n){return n.t==="button"});R.cartes=c.map(function(z){return [!!z.p.disabled,z.p.title]});
c[0].p.onClick();c[1].p.onClick();R.ouv=OUV;R.img=trouver(T2,function(n){return n.t==="img"}).map(function(i){return i.p.src});
REP["GET /api/library/semblables/a.png"]={__ko:503,detail:"CLIP n'est pas installé."};H=[];await boutons(semb(P),"≈ Images")[0].p.onClick();R.m503=texte(semb(P));
REP["GET /api/library/semblables/a.png"]={filename:"a.png",semblables:[]};H=[];await boutons(semb(P),"≈ Images")[0].p.onClick();R.vide=texte(semb(P));
H=[];R.nul=[semb({m:{name:"v.mp4",kind:"video"},liste:[]}),semb({m:{name:"x.png",kind:"image",jobId:"j1"},liste:[]}),semb({m:null,liste:[]})];
H=[];var Pn={m:{name:"un nom#.png",kind:"image"},liste:[]};REP["GET /api/library/semblables/un%20nom%23.png"]={semblables:[]};FETCH=[];
await boutons(semb(Pn),"≈ Images")[0].p.onClick();R.enc=FETCH[0][0];
""")
check("S0 sous node : les semblables s'executent", R is not None)
if R:
    check("S1 « ≈ Images semblables » (title : par CLIP, sur ce PC) ; UN appel au double clic, nom ENCODE",
          R["b"][0] == "≈ Images semblables" and "CLIP" in R["b"][1] and R["fetch"] == ["/api/library/semblables/a.png"]
          and R["enc"] == "/api/library/semblables/un%20nom%23.png", str(R["fetch"]) + R["enc"])
    check("S2 une vignette par voisin (proximite en % dans le title) ; celle de la liste OUVRE sa fiche, l'absente est desactivee",
          R["cartes"] == [[False, "b.png — proximité 91 %"], [True, "zz.png — proximité 50 %"]] and R["ouv"] == ["b.png"]
          and R["img"] == ["/api/images/b.png", "/api/images/zz.png"], str(R["cartes"]))
    check("S3 503 : dit OU installer CLIP ; aucun voisin : dit d'indexer d'abord", "🔎 Recherche → Installer CLIP" in R["m503"]
          and "Aucune image indexée à comparer" in R["vide"], R["m503"] + R["vide"])
    check("S4 pas de bouton pour une video, un rendu, ni sans media", R["nul"] == [None, None, None], str(R["nul"]))

R = node("""
function rech(p){hi=0;EFF=[];return DzRecherche(p)}
async function monter(p,etat){H=[];REP["GET /api/library/clip/etat"]=etat;REP["GET /api/library/legendes/devis"]={n:0,usd:0,modele:"m",cle:true,etat:{en_cours:false}};
  rech(p);var e=EFF.slice();e.forEach(function(f){f()});await attendre();return rech(p)}
function opts(T){return trouver(T,function(n){return n.t==="option"}).map(function(o){return [o.p.value,!!o.p.disabled,o.p.children]})}
var P={liste:[{name:"b.png",kind:"image"}],ouvrir:function(){}};
R.non=opts(await monter(P,{installe:false,octets:185581726,indexees:0,a_indexer:0,installation:{},index:{}}));
R.aidx=opts(await monter(P,{installe:true,octets:1,indexees:0,a_indexer:4,installation:{},index:{}}));
var T=await monter(P,{installe:true,octets:1,indexees:4,a_indexer:0,installation:{},index:{}});R.pret=opts(T);R.bloc=trouver(T,function(n){return n.t===DzClipBloc}).length;
trouver(T,function(n){return n.t==="select"})[0].p.onChange({target:{value:"clip"}});trouver(rech(P),function(n){return n.t==="input"})[0].p.onChange({target:{value:"a red car"}});
REP["GET /api/library/recherche?q=a%20red%20car&moteur=clip"]={n:1,resultats:[{filename:"b.png",score:0.27,champs:["sens"],extrait:""}]};
FETCH=[];boutons(rech(P),"Chercher")[0].p.onClick();await attendre();R.fetch=FETCH.map(function(f){return f[0]});R.txt=texte(rech(P));
""")
check("C0 sous node : le selecteur s'execute", R is not None)
if R:
    check("C1 le selecteur : CLIP grise « a installer », puis « a indexer », puis ACTIF ; il dit « en anglais, sur ce PC »",
          R["non"][1] == ["clip", True, "CLIP — par le sens (en anglais, sur ce PC) — à installer"]
          and R["aidx"][1] == ["clip", True, "CLIP — par le sens (en anglais, sur ce PC) — à indexer"]
          and R["pret"][1] == ["clip", False, "CLIP — par le sens (en anglais, sur ce PC)"] and R["pret"][0][1] is False, str(R["non"]) + str(R["aidx"]) + str(R["pret"]))
    check("C2 la recherche porte le bloc CLIP ; moteur clip : la requete part avec moteur=clip et le resultat s'affiche",
          R["bloc"] == 1 and "/api/library/recherche?q=a%20red%20car&moteur=clip" in R["fetch"] and "1 image(s)" in R["txt"], str(R["fetch"]) + R["txt"])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
