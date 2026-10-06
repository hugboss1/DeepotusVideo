# -*- coding: utf-8 -*-
"""Plan-templates T10 / D3 (tache #76 du suivi, PR H, 03/10/2026) — FIGMA et VECTORLAB a l'ecran, dans le bundle
LIVRE : « Importer un cadre Figma… » (galerie), « SVG ↓ » et « Ouvrir dans le Vectorlab » (editeur) sont extraits
et EXECUTES sous node (fetch, dialogue maison et window.open simules : aucun appel Figma).
DECISIONS DE L'UTILISATEUR (03/10) : le cout en appels Figma est ANNONCE avant l'import et rendu apres ; export SVG et
ouverture dans le Vectorlab.
Temoin positif : le bundle de la base (5d8b8ab3) n'a pas l'import Figma a l'ecran.
Run (depuis backend/) : & $PY tests/test_templates_figma_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzfge_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "5d8b8ab3"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a l'export d'image mais pas l'import Figma a l'ecran", r0.returncode == 0 and b"DzExportImage" in r0.stdout and b"DzFigmaImport" not in r0.stdout)
check("T2 l'import suit « Rejouer en » dans l'en-tete de la galerie (meme recharge + selection) ; SVG et Vectorlab suivent « Exporter l'image » dans l'editeur",
      BUN.count('r.jsx(DzFigmaImport,{onSaved:function(id){a(function(w){return w+1});setTimeout(function(){n(id)},200)}})') == 1
      and BUN.count('r.jsx(DzExportImage,{tpl:a,regs:d}),r.jsx(DzExportFigma,{tpl:a,regs:d})') == 1)


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


NOMS = ("dzGabaritCourant", "DzFigmaImport", "DzExportFigma")
COUCHE = "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a les trois fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,FETCH=[],REP=null,SAISI=[],REPONSE=null,OUVERTS=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){p=p||{};return {t:t,p:p,props:p}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var K="K",O="Champ";
var window={__dzDialogue:{saisir:async function(m,o){SAISI.push([m,o]);return REPONSE}},open:function(u,c){OUVERTS.push([u,c])}};
async function fetch(u,o){FETCH.push([u,o&&o.method,o&&o.body&&JSON.parse(o.body)]);var q=REP;await new Promise(function(s){setTimeout(s,5)});
  return {ok:q.ok,status:q.status,json:async function(){return q.json||{}}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function bouton(T,txt){return trouver(T,function(n){return n.t==="K"&&n.p.children===txt})[0]}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
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


print("[F] importer un cadre Figma")
R = node("""
var SAUVE=[];function imp(){hi=0;return DzFigmaImport({onSaved:function(id){SAUVE.push(id)}})}
var T=imp();var b=bouton(T,"Importer un cadre Figma…");R.titre=b.p.title;
REPONSE=null;await b.p.onClick();R.annule=[SAISI.length,FETCH.length,SAUVE.length];R.annonce=SAISI[0][0];R.opts=SAISI[0][1];
REPONSE="  https://www.figma.com/design/K/F?node-id=1-2  ";REP={ok:true,status:200,json:{template_id:"tpl_user_1",name:"Mon reel",appels:2,images:["a.png","b.png"],warnings:["« Logo » sauté.","w2","w3","w4"]}};
var p1=imp().p.children[0].p.onClick(),p2=imp().p.children[0].p.onClick();await p1;await p2;
R.post=FETCH.slice();R.sauve=SAUVE.slice();R.msg=texte(imp());
REP={ok:false,status:503,json:{detail:"FIGMA_TOKEN absent — crée un Personal Access Token Figma"}};FETCH=[];await bouton(imp(),"Importer un cadre Figma…").p.onClick();R.refus=texte(imp());R.sauve2=SAUVE.length;
REP={ok:true,status:200,json:{template_id:"t2",name:"Seul",appels:1,images:[],warnings:[]}};await bouton(imp(),"Importer un cadre Figma…").p.onClick();R.msg2=texte(imp());
""")
check("F0 sous node : l'import s'execute", R is not None)
if R:
    check("F1 le bouton (title qui dit « 1 à 2 appels ») demande le lien par le DIALOGUE MAISON en ANNONCANT le cout (1 appel, 2 avec images, quota Figma) ; annule : rien n'est envoye",
          "1 à 2 appels" in R["titre"] and R["annule"] == [1, 0, 0] and "1 appel à l’API Figma, 2 si le cadre contient des images" in R["annonce"]
          and "quota" in R["annonce"] and R["opts"]["titre"] == "Importer un cadre Figma", R["annonce"])
    check("F2 le lien (nettoye) part UNE fois au double clic ; le gabarit importe est recharge et SELECTIONNE ; le message RENDS les appels faits, les images et les remarques (3 au plus)",
          len(R["post"]) == 1 and R["post"][0] == ["/api/layout-templates/import-figma", "POST", {"url": "https://www.figma.com/design/K/F?node-id=1-2"}]
          and R["sauve"] == ["tpl_user_1"] and "« Mon reel » importé (2 appels Figma, 2 images en Bibliothèque) — 4 remarques : « Logo » sauté. · w2 · w3" in R["msg"], R["msg"])
    check("F3 refus du serveur affiche tel quel (sans jeton : comment l'obtenir), rien de selectionne ; singulier pour UN appel sans image",
          "FIGMA_TOKEN absent" in R["refus"] and R["sauve2"] == 1 and "« Seul » importé (1 appel Figma)" in R["msg2"], R["msg2"])

print("\n[X] SVG et Vectorlab")
R = node("""
var TPL={id:"tpl x",name:"X",regions:[{id:"a",type:"text",x:1,y:2,width:3,height:4}]},REGS=[{id:"a",type:"text",x:10.6,y:20.2,width:30,height:40,_disp:"z",text:"Neuf"}];
function ex(t){hi=0;return DzExportFigma({tpl:t,regs:REGS})}
R.sans=ex(null)===null;var T=ex(TPL);var sv=bouton(T,"SVG ↓"),vl=bouton(T,"Ouvrir dans le Vectorlab");R.titres=[sv.p.title,vl.p.title,sv.p.disabled];
sv.p.onClick();R.svg=OUVERTS.slice();R.svgSansId=bouton(ex({name:"neuf",regions:[]}),"SVG ↓").p.disabled;
REP={ok:true,status:200,json:{id:"abc 1",objets:7,images:2}};OUVERTS=[];var p1=vl.p.onClick(),p2=vl.p.onClick();await p1;await p2;
R.post=FETCH.slice();R.ouv=OUVERTS.slice();R.msg=texte(ex(TPL));
REP={ok:false,status:400,json:{detail:"Jeton de marque inconnu"}};OUVERTS=[];await bouton(ex(TPL),"Ouvrir dans le Vectorlab").p.onClick();R.refus=[texte(ex(TPL)),OUVERTS.length];
""")
check("X0 sous node : les exports s'executent", R is not None)
if R:
    check("X1 « SVG ↓ » telecharge le gabarit ENREGISTRE (id encode) et se DESACTIVE sans id ; titles explicites (Figma, gratuit)",
          R["sans"] and R["svg"] == [["/api/layout-templates/tpl%20x/export.svg", "_blank"]] and R["titres"][2] is False and R["svgSansId"] is True
          and "Figma" in R["titres"][0] and "gratuit" in R["titres"][1], str(R["svg"]))
    check("X2 « Ouvrir dans le Vectorlab » envoie le gabarit TEL QU'A L'ECRAN (une fois au double clic) puis ouvre /vectorlab/?doc=<id> dans un onglet ; le message dit objets et images",
          len(R["post"]) == 1 and R["post"][0][0] == "/api/layout-templates/tpl%20x/vers-vectorlab" and R["post"][0][2]["template"]["regions"][0] == {"id": "a", "type": "text", "x": 11, "y": 20, "width": 30, "height": 40, "text": "Neuf"}
          and R["ouv"] == [["/vectorlab/?doc=abc%201", "_blank"]] and "7 objets, 2 images" in R["msg"], f"{R['post']} {R['ouv']}")
    check("X3 un refus est affiche et RIEN ne s'ouvre", "Jeton de marque inconnu" in R["refus"][0] and R["refus"][1] == 0, str(R["refus"]))

check("T4 aucun prompt/alert/confirm natif (le lien passe par le dialogue maison) ; la chaine tient (DzTracks 180, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 180
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
