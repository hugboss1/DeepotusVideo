# -*- coding: utf-8 -*-
"""Bibliotheque, tache #80 PR B (plan-library T6-T8, 03/10/2026) — la FICHE complete a l'ecran, dans le bundle LIVRE :
DzFiche (et ses aides pures) est extrait et EXECUTE sous node (fetch et dialogue maison simules : aucun tir).
DECISIONS DE L'UTILISATEUR (03/10) : fiche EXPLICITE et editable (licence avec liste + saisie libre, auteur, lien) ;
alerte ambre si la licence est inconnue ; fichier, recette, usages ; « Rejouer la recette » PAYANT : prix annonce par le
dialogue maison, plafond garde par le serveur ; et la grille qui affichait taille vide et « on disk » partout (l'API
sert size_kb et mtime) est reparee.
Temoin positif : le bundle de la base (0bfc589d) n'a pas la fiche et lit encore S.size / S.modified.
Run (depuis backend/) : & $PY tests/test_library_fiche_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzfie_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "0bfc589d"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
GRILLE_AVANT = 'size:go(S.size),date:mo(S.modified)||"on disk"'
GRILLE = 'size:go(S.size_kb!=null?S.size_kb*1024:S.size),date:mo(S.mtime?S.mtime*1e3:S.modified)||"on disk"'
check("T1 temoin : la base a la lignee mais pas la fiche, et sa grille lit S.size / S.modified",
      r0.returncode == 0 and b"DzLignee" in r0.stdout and b"DzFiche" not in r0.stdout and GRILLE_AVANT.encode() in r0.stdout)
check("T2 la fiche suit la lignee (une image rejouee entre en tete de la liste) ; la grille lit size_kb et mtime",
      BUN.count("r.jsx(DzLignee,{m:m,liste:l,ouvrir:y}),r.jsx(DzFiche,{m:m,lister:function(im){d(function(L){return[{name:im,kind:\"image\"") == 1
      and BUN.count(GRILLE) == 1 and GRILLE_AVANT not in BUN)


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


NOMS = ("dzOctets", "dzFicheLignes", "DzFiche")
COUCHE = "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a les trois fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS))
GOMO = fonction("go") + "\n" + fonction("mo")

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={},DIAL=[],DREP=true,LISTE=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f){EFF.push(f)}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{confirmer:async function(m,o){DIAL.push([m,o]);return DREP}}};
async function fetch(u,o){FETCH.push([u,o&&o.method||"GET",o&&o.body?JSON.parse(o.body):null]);var q=REP[(o&&o.method||"GET")+" "+u];
  await new Promise(function(s){setTimeout(s,3)});if(typeof q==="function")q=q();
  return {ok:!!q&&!q.__ko,status:q&&q.__ko?q.__ko:(q?200:404),json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
function bouton(T,txt){return trouver(T,function(n){return n.t==="K"&&n.p.children===txt})[0]}
function champ(T,ph){return trouver(T,function(n){return n.t==="input"&&n.p.placeholder===ph})[0]}
function rendu(p){hi=0;EFF=[];return DzFiche(p)}
async function monter(p){rendu(p);var e=EFF.slice();e.forEach(function(f){f()});await new Promise(function(s){setTimeout(s,40)});return rendu(p)}
async function attendre(){await new Promise(function(s){setTimeout(s,40)})}
var FICHE={filename:"gen_a b.png",kind:"image",source:"generation",source_libelle:"Générateur",
  droits:{licence:"inconnue",alerte:true,auteur:null,source_url:null,licences:["propriétaire","CC0","inconnue"]},
  fichier:{largeur:720,hauteur:1280,octets:12500,format:"png",modifie:"2026-10-03T10:00:00+00:00"},
  recette:{origine:"generation",prompt:"un phare",model:"flux",style:"vitrail",size:"square_hd",seed:42},
  rejouer:{route:"/api/images/generate",corps:{prompt:"un phare",model:"flux",seed:42,n:1,source:"generation"},usd:0.003},
  usages:[{type:"rendu",id:"j1",libelle:"Rendu A",role:"image de départ"},{type:"projet",id:"p1",libelle:"Campagne",role:"membre"}]};
"""


def node(corps, extra=""):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + extra + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-600:])
        return None


R = node("""
var U="/api/library/fiche/gen_a%20b.png";REP["GET "+U]=FICHE;var M={name:"gen_a b.png",kind:"image"};
var T=await monter({m:M,lister:function(im){LISTE.push(im)}});R.fetch=FETCH.slice();R.txt=texte(T);
R.champs=[champ(T,"propriétaire, CC BY…").p.value,champ(T,"nom ou crédit").p.value,champ(T,"https://…").p.value,champ(T,"propriétaire, CC BY…").p.list];
R.datalist=trouver(T,function(n){return n.t==="option"}).map(function(n){return n.p.value});
R.enrTitre=bouton(T,"Enregistrer").p.title;R.enrAvant=bouton(T,"Enregistrer").p.disabled;
champ(T,"propriétaire, CC BY…").p.onChange({target:{value:"  CC BY "}});var T2=rendu({m:M});R.enrApres=bouton(T2,"Enregistrer").p.disabled;
champ(T2,"nom ou crédit").p.onChange({target:{value:"AFP"}});T2=rendu({m:M});
REP["PATCH /api/library/asset/gen_a%20b.png"]={licence:"CC BY"};FETCH=[];
var F2=JSON.parse(JSON.stringify(FICHE));F2.droits.licence="CC BY";F2.droits.alerte=false;F2.droits.auteur="AFP";REP["GET "+U]=F2;
bouton(T2,"Enregistrer").p.onClick();await attendre();R.patch=FETCH.slice();var T3=rendu({m:M});R.apres=texte(T3);
R.champsApres=[champ(T3,"propriétaire, CC BY…").p.value,champ(T3,"nom ou crédit").p.value];
REP["PATCH /api/library/asset/gen_a%20b.png"]={__ko:400,detail:"note doit être un entier"};champ(T3,"nom ou crédit").p.onChange({target:{value:"X"}});
var T4=rendu({m:M});bouton(T4,"Enregistrer").p.onClick();await attendre();R.refus=texte(rendu({m:M}));
""")
check("N0 sous node : la fiche s'execute", R is not None)
if R:
    check("N1 UNE requete au nom ENCODE ; Droits pre-remplis (licence, auteur, lien) avec la liste des licences en suggestion",
          R["fetch"] == [["/api/library/fiche/gen_a%20b.png", "GET", None]] and R["champs"] == ["inconnue", "", "", "dz-licences"]
          and R["datalist"] == ["propriétaire", "CC0", "inconnue"], str(R["fetch"]) + str(R["champs"]))
    check("N2 l'ALERTE ambre de la licence inconnue ; fichier (720 × 1280 px · 12.2 Ko · PNG), source, recette, prompt, usages",
          "⚠ Licence inconnue — à vérifier avant diffusion" in R["txt"] and "720 × 1280 px · 12.2 Ko · PNG" in R["txt"] and "Générateur" in R["txt"]
          and "Générateur · modèle flux · style vitrail · format square_hd · graine 42" in R["txt"] and "un phare" in R["txt"]
          and "Rendu « Rendu A » (image de départ) · Projet « Campagne » (membre)" in R["txt"], R["txt"])
    check("N3 « Enregistrer » (title) est INACTIF tant que rien ne change ; le PATCH envoie les valeurs NETTOYEES ; la fiche est RELUE ; l'alerte tombe",
          R["enrAvant"] is True and R["enrApres"] is False and "licence" in R["enrTitre"] and R["patch"][0] == ["/api/library/asset/gen_a%20b.png", "PATCH",
          {"licence": "CC BY", "auteur": "AFP", "source_url": ""}] and R["patch"][1][0] == "/api/library/fiche/gen_a%20b.png"
          and "Droits enregistrés." in R["apres"] and "Licence inconnue" not in R["apres"] and R["champsApres"] == ["CC BY", "AFP"], str(R["patch"]) + R["apres"])
    check("N4 un refus du serveur est DIT (le detail)", "Non enregistré : note doit être un entier" in R["refus"], R["refus"])

R = node("""
var U="/api/library/fiche/g.png";REP["GET "+U]=FICHE;var M={name:"g.png",kind:"image"};
var T=await monter({m:M,lister:function(im){LISTE.push(im)}});var b=bouton(T,"Rejouer la recette");R.titre=b.p.title;
DREP=false;FETCH=[];await b.p.onClick();R.annule=[DIAL.length,FETCH.length,LISTE.length];R.dial=DIAL[0];
DREP=true;REP["POST /api/images/generate"]={images:["gen_neuf.png"]};FETCH=[];
var p1=bouton(rendu({m:M,lister:function(im){LISTE.push(im)}}),"Rejouer la recette").p.onClick(),p2=bouton(rendu({m:M,lister:function(im){LISTE.push(im)}}),"Rejouer la recette").p.onClick();
await p1;await p2;R.post=FETCH.slice();R.liste=LISTE.slice();R.msg=texte(rendu({m:M}));
REP["POST /api/images/generate"]={__ko:402,detail:"Plafond de dépense atteint"};LISTE=[];
await bouton(rendu({m:M,lister:function(im){LISTE.push(im)}}),"Rejouer la recette").p.onClick();R.refus=[texte(rendu({m:M})),LISTE.length];
// sans recette du generateur : pas de bouton ; un rendu (job) : rien, aucune requete ; un son : la fiche
var F3=JSON.parse(JSON.stringify(FICHE));F3.rejouer=null;F3.recette={origine:"template",template_name:"News",at_s:1};F3.droits.alerte=false;
REP["GET /api/library/fiche/t.png"]=F3;var T5=await monter({m:{name:"t.png",kind:"image"}});R.sansBouton=!bouton(T5,"Rejouer la recette");R.tpl=texte(T5);
FETCH=[];R.job=await monter({m:{name:"r",kind:"render",jobId:"j"}});R.jobFetch=FETCH.length;
var F4=JSON.parse(JSON.stringify(FICHE));F4.kind="audio";F4.rejouer=null;F4.recette=null;F4.usages=[];F4.fichier={largeur:null,hauteur:null,octets:900,format:"mp3"};
REP["GET /api/library/fiche/vo.mp3"]=F4;R.son=texte(await monter({m:{name:"vo.mp3",kind:"audio",audioFile:true}}));
R.panne=await monter({m:{name:"absent.png",kind:"image"}});
R.oct=[dzOctets(0),dzOctets(1023),dzOctets(1024),dzOctets(5*1048576)];
""")
check("R0 sous node : Rejouer s'execute", R is not None)
if R:
    check("R1 « Rejouer » dit PAYANT et le prix (title) ; le dialogue maison ANNONCE le prix ; annule : aucune requete",
          "PAYANT" in R["titre"] and "0.003 $" in R["titre"] and R["annule"] == [1, 0, 0] and "≈ 0.003 $" in R["dial"][0] and R["dial"][1]["ok"] == "Rejouer (≈ 0.003 $)", str(R["dial"]))
    check("R2 confirme : UN tir au double clic, vers la route et avec le corps de la fiche ; la nouvelle image entre dans la liste et est NOMMEE",
          R["post"] == [["/api/images/generate", "POST", {"prompt": "un phare", "model": "flux", "seed": 42, "n": 1, "source": "generation"}]]
          and R["liste"] == ["gen_neuf.png"] and "Nouvelle image : gen_neuf.png" in R["msg"], str(R["post"]) + R["msg"])
    check("R3 un refus (plafond, 402) est DIT et rien n'entre dans la liste", "Refusé : Plafond de dépense atteint" in R["refus"][0] and R["refus"][1] == 0, str(R["refus"]))
    check("R4 sans recette du generateur : pas de bouton, la recette de gabarit est dite ; un rendu : rien et AUCUNE requete ; un son : sa fiche ; une panne : rien",
          R["sansBouton"] and "Image fixe de gabarit · gabarit News · à 1 s" in R["tpl"] and R["job"] is None and R["jobFetch"] == 0
          and "900 o · MP3" in R["son"] and "Usages | aucun" in R["son"] and R["panne"] is None, R["tpl"] + " // " + R["son"])
    check("R5 les octets en o / Ko / Mo", R["oct"] == ["0 o", "1023 o", "1.0 Ko", "5.0 Mo"], str(R["oct"]))

G = node("""var S={size_kb:12,mtime:Date.now()/1e3-120,modified:"x"};var o=eval("({"+""" + json.dumps(GRILLE) + """+"})");
var S2={size:2048,modified:null};var S=S2;var o2=eval("({"+""" + json.dumps(GRILLE) + """+"})");R.g=[o.size,o.date,o2.size,o2.date];""", extra=GOMO)
check("G1 la GRILLE : 12 Ko et « 2m ago » depuis size_kb / mtime ; repli sur size / modified (ancienne forme) intact",
      G is not None and G["g"] == ["12.0 KB", "2m ago", "2.0 KB", "on disk"], str(G and G["g"]))
check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 178
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
