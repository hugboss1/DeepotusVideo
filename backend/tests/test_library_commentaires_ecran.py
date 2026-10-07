# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR A (plan-library T14, 04/10/2026) — les COMMENTAIRES a l'ecran, dans le bundle LIVRE :
DzCommentaires (et ses aides pures) est extrait et EXECUTE sous node (fetch et dialogue maison simules).
DECISION DE L'UTILISATEUR (04/10) : commentaires dates avec statut (a revoir / valide / rejete), instant pour un son.
Temoin positif : le bundle de la base (329aa702) n'a pas les commentaires.
Run (depuis backend/) : & $PY tests/test_library_commentaires_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzcme_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "329aa702"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la fiche mais pas les commentaires", r0.returncode == 0 and b"DzFiche" in r0.stdout and b"DzCommentaires" not in r0.stdout)
check("T2 les commentaires suivent la fiche", BUN.count('fav:!1}].concat(L)})}}),r.jsx(DzCommentaires,{m:m}),r.jsx(DzSemblables,') == 1)


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


NOMS = ("dzDuree", "dzInstant", "dzInstantTxt", "DzCommentaires")
k = BUN.find("var DZ_CM_STATUTS=")
STAT = BUN[k:BUN.find("];", k) + 2] if k >= 0 else ""
COUCHE = STAT + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a ses fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS) and BUN.count("var DZ_CM_STATUTS=") == 1)

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={},DIAL=[],DREP=true;
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f){EFF.push(f)},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{confirmer:async function(m,o){DIAL.push([m,o]);return DREP}}};
async function fetch(u,o){var m=o&&o.method||"GET";FETCH.push([u,m,o&&o.body?JSON.parse(o.body):null]);var q=REP[m+" "+u];
  await new Promise(function(s){setTimeout(s,3)});if(typeof q==="function")q=q();
  return {ok:!!q&&!q.__ko,status:q&&q.__ko?q.__ko:(q?200:404),json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
async function attendre(){await new Promise(function(s){setTimeout(s,40)})}
function rendu(p){hi=0;EFF=[];return DzCommentaires(p)}
async function monter(p){rendu(p);var e=EFF.slice();e.forEach(function(f){f()});await attendre();return rendu(p)}
var AUJ=new Date().toISOString();
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-600:])
        return None


R = node("""
var U="/api/library/commentaires/a%20b.png";
REP["GET "+U]={commentaires:[{id:"c1",texte:"ciel trop sature",statut:"a_revoir",t_s:null,cree_le:AUJ},{id:"c2",texte:"ok",statut:"valide",t_s:null,cree_le:AUJ}]};
var M={name:"a b.png",kind:"image"};var T=await monter({m:M});R.txt=texte(T);R.fetch=FETCH.slice();
R.instantImg=trouver(T,function(n){return n.t==="input"&&n.p.placeholder==="mm:ss"}).length;
var pills=trouver(T,function(n){return n.t==="button"&&n.p["aria-pressed"]!==undefined});R.pills=pills.map(function(b){return [b.p.children,b.p["aria-pressed"],b.p.title]});
REP["PATCH /api/library/commentaires/c/c1"]={id:"c1",statut:"valide"};FETCH=[];pills[1].p.onClick();await attendre();R.patch=FETCH[0];R.relu=FETCH[1]&&FETCH[1][0];
FETCH=[];pills[0].p.onClick();await attendre();R.memeStatut=FETCH.length;
var bt=trouver(rendu({m:M}),function(n){return n.t==="K"})[0];R.comInactif=bt.p.disabled;R.comTitre=bt.p.title;
trouver(rendu({m:M}),function(n){return n.t==="input"})[0].p.onChange({target:{value:"  nouvelle remarque "}});
REP["POST "+U]={id:"c3"};FETCH=[];var b2=trouver(rendu({m:M}),function(n){return n.t==="K"})[0];var p1=b2.p.onClick(),p2=b2.p.onClick();await p1;await p2;await attendre();
R.post=FETCH.filter(function(f){return f[1]==="POST"});R.vide=trouver(rendu({m:M}),function(n){return n.t==="input"})[0].p.value;
REP["POST "+U]={__ko:400,detail:"Le commentaire est vide."};trouver(rendu({m:M}),function(n){return n.t==="input"})[0].p.onChange({target:{value:"x"}});
await trouver(rendu({m:M}),function(n){return n.t==="K"})[0].p.onClick();R.refus=texte(rendu({m:M}));
var del=trouver(rendu({m:M}),function(n){return n.t==="button"&&n.p.children==="×"})[0];R.delTitre=del.p.title;
DREP=false;DIAL=[];FETCH=[];await del.p.onClick();R.annule=[DIAL.length,FETCH.length];R.dial=DIAL[0];
DREP=true;REP["DELETE /api/library/commentaires/c/c1"]={supprime:"c1"};FETCH=[];await del.p.onClick();await attendre();R.del=FETCH[0];
""")
check("N0 sous node : les commentaires s'executent", R is not None)
if R:
    check("N1 UNE requete au nom encode ; en-tete « Commentaires (2) · 1 a revoir · 1 valide » ; textes et dates ; pas d'instant pour une image",
          R["fetch"] == [["/api/library/commentaires/a%20b.png", "GET", None]] and "Commentaires (2) · 1 à revoir · 1 validé" in R["txt"]
          and "ciel trop sature" in R["txt"] and "aujourd’hui" in R["txt"] and R["instantImg"] == 0, R["txt"])
    check("N2 trois pastilles de statut par commentaire (title) ; la courante est marquee ; un clic CHANGE le statut (PATCH) et relit ; recliquer la courante ne fait rien",
          len(R["pills"]) == 6 and R["pills"][0][:2] == ["à revoir", True] and R["pills"][1][:2] == ["validé", False] and "Passer à « validé »" in R["pills"][1][2]
          and R["patch"] == ["/api/library/commentaires/c/c1", "PATCH", {"statut": "valide"}] and R["relu"] == "/api/library/commentaires/a%20b.png"
          and R["memeStatut"] == 0, str(R["pills"]) + str(R["patch"]))
    check("N3 « Commenter » (title) inactif sans texte ; envoie le texte NETTOYE une seule fois (double clic) et vide le champ ; un refus est dit",
          R["comInactif"] is True and "à revoir" in R["comTitre"] and R["post"] == [["/api/library/commentaires/a%20b.png", "POST", {"texte": "nouvelle remarque"}]]
          and R["vide"] == "" and "Non enregistré : Le commentaire est vide." in R["refus"], str(R["post"]) + R["refus"])
    check("N4 supprimer (title) passe par le dialogue maison qui CITE le commentaire ; annule = rien ; confirme = DELETE",
          R["delTitre"] == "Supprimer ce commentaire" and R["annule"] == [1, 0] and "« ciel trop sature »" in R["dial"][0] and R["dial"][1]["ok"] == "Supprimer"
          and R["del"] == ["/api/library/commentaires/c/c1", "DELETE", None], str(R["del"]))

R = node("""
REP["GET /api/library/commentaires/v.mp3"]={commentaires:[{id:"s1",texte:"souffle",statut:"rejete",t_s:83.5,cree_le:AUJ}]};
var M={name:"v.mp3",kind:"audio",audioFile:"v.mp3"};var T=await monter({m:M});R.txt=texte(T);
var ins=trouver(T,function(n){return n.t==="input"&&n.p.placeholder==="mm:ss"})[0];R.insTitre=ins&&ins.p.title;
ins.p.onChange({target:{value:"1:05.5"}});trouver(rendu({m:M}),function(n){return n.t==="input"&&n.p.placeholder==="Ajouter un commentaire…"})[0].p.onChange({target:{value:"clic"}});
REP["POST /api/library/commentaires/v.mp3"]={id:"s2"};FETCH=[];await trouver(rendu({m:M}),function(n){return n.t==="K"})[0].p.onClick();await attendre();R.post=FETCH[0];
trouver(rendu({m:M}),function(n){return n.t==="input"&&n.p.placeholder==="mm:ss"})[0].p.onChange({target:{value:"une minute"}});
trouver(rendu({m:M}),function(n){return n.t==="input"&&n.p.placeholder==="Ajouter un commentaire…"})[0].p.onChange({target:{value:"x"}});
FETCH=[];await trouver(rendu({m:M}),function(n){return n.t==="K"})[0].p.onClick();R.illisible=[FETCH.length,texte(rendu({m:M}))];
FETCH=[];R.job=await monter({m:{name:"r",kind:"render",jobId:"j"}});R.jobFetch=FETCH.length;R.panne=await monter({m:{name:"z.png",kind:"image"}});
R.inst=[dzInstant("1:05"),dzInstant("83.5"),dzInstant("12,5"),dzInstant(""),isNaN(dzInstant("abc")),dzInstantTxt(83.5),dzInstantTxt(5),dzInstantTxt(null)];
""")
check("A0 sous node : un son s'execute", R is not None)
if R:
    check("A1 un SON : l'instant s'affiche (1:23.5) ; un champ mm:ss (title) ; « 1:05.5 » part en secondes (65.5) avec le texte",
          "1:23.5" in R["txt"] and "souffle" in R["txt"] and "rejeté" in R["txt"] and "instant" in (R["insTitre"] or "")
          and R["post"] == ["/api/library/commentaires/v.mp3", "POST", {"texte": "clic", "t_s": 65.5}], str(R["post"]))
    check("A2 un instant illisible est DIT et rien ne part", R["illisible"][0] == 0 and "Instant illisible" in R["illisible"][1], str(R["illisible"]))
    check("A3 un rendu : rien et AUCUNE requete ; une panne (404) : rien", R["job"] is None and R["jobFetch"] == 0 and R["panne"] is None)
    check("A4 dzInstant / dzInstantTxt : mm:ss, secondes, virgule, vide, illisible ; et l'affichage", R["inst"] == [65, 83.5, 12.5, None, True, "1:23.5", "0:05", ""], str(R["inst"]))
check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 181
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
