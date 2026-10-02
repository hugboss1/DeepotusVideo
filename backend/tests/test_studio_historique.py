# -*- coding: utf-8 -*-
"""Plan-studio T5 (tache #68 du suivi, 02/10/2026) — la PILE des rendus d'un noeud du Studio, et le choix de celui qui
alimente l'aval. Dans la couche du maillon montage (comme les epingles de #67), executee sous node depuis le bundle
LIVRE.
Ce que le plan prevoyait autrement, et pourquoi : un verrou `lock` contre l'ecrasement par la recolte suivante. Inutile
ici : la recolte ne pose une epingle NEUVE que si le noeud a ete regenere ; et un rendu choisi est VERIFIE par le
serveur au prochain run (empreinte de la requete reelle, #67) — fait avec d'autres reglages, il est ecarte et c'est dit.
Temoin positif : le bundle de la base (8653eee3) n'a pas la pile.
Run (depuis backend/) : & $PY tests/test_studio_historique.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzhist_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "8653eee3"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : le bundle de la base a les epingles mais pas la pile", r0.returncode == 0 and b"DzPinPanel" in r0.stdout
      and b"dzPinHistPush" not in r0.stdout and b"DzPinHist" not in r0.stdout)


def entre(debut, fin):
    i = BUN.find(debut)
    j = BUN.find(fin, i + 1)
    return BUN[i:j] if i >= 0 and j > i else ""


def node(js):
    f = _TMP / f"h{abs(hash(js)) % 10**9}.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (r.stderr or r.stdout)[-400:])
        return None


COUCHE = entre("function dzPinRendu(", "function DzPinHist(")
check("T2 la pile est dans la couche livree (une fois), avant la recolte", BUN.count("function dzPinHistPush(") == 1
      and "function dzPinRecolter(" in COUCHE and "function dzPinHistPush(" in COUCHE)

print("[P] la pile")
R = node(COUCHE + """
var h=null,i;for(i=1;i<=10;i++)h=dzPinHistPush(h,{job_id:"j"+i,empreinte:"e"+i,le:"t"+i});
var a=[h.length,h[0].job_id,h[7].job_id];
h=dzPinHistPush(h,{job_id:"j5",empreinte:"e5bis",le:"tx"});
var b=[h.length,h[0].job_id,h[0].empreinte,h.filter(function(x){return x.job_id==="j5"}).length];
var c=[dzPinHistPush(h,null).length,dzPinHistPush([],{empreinte:"e"}).length], d=dzPinHistPush(undefined,{job_id:"z"}).length;
console.log(JSON.stringify({a:a,b:b,c:c,d:d}))""")
check("P1 en TETE, huit au plus (10 rendus -> j10 devant, j3 en dernier)", R is not None and R["a"] == [8, "j10", "j3"], str(R))
check("P2 sans doublon : un rendu deja empile remonte en tete, une seule fois", R is not None and R["b"] == [8, "j5", "e5bis", 1], str(R))
check("P3 une epingle vide ou sans rendu (job_id) n'empile rien ; une pile absente part de zero", R is not None and R["c"] == [8, 0] and R["d"] == 1, str(R))

print("\n[R] la recolte empile")
G = {"name": "G", "nodes": [{"id": "s1", "type": "Seedance", "props": {"hist": [{"job_id": "vieux", "empreinte": "e0", "le": "x"}]}},
                            {"id": "h1", "type": "HeyGenAvatar", "props": {"pin": {"job_id": "jh", "empreinte": "eh"},
                                                                           "hist": [{"job_id": "jh", "empreinte": "eh", "le": "y"}]}}]}
PARTS = {"parts": [{"slot": "a", "node_id": "s1", "kind": "seedance", "job_id": "neuf", "empreinte": "e1", "reemploi": False},
                   {"slot": "b", "node_id": "h1", "kind": "heygen", "job_id": "jh", "empreinte": "eh", "reemploi": True}]}
R = node(COUCHE + "\nvar MAJ={};var window={__dzStudioMaj:function(n,p){MAJ[n]=p},__dzStudioG:" + json.dumps(G) + "};"
         "globalThis.setTimeout=function(f){f()};globalThis.fetch=async function(u){return {ok:true,json:async function(){return /parts$/.test(u)?"
         + json.dumps(PARTS) + ":{status:'done'}}}};dzPinRecolter({job_id:'r1'}," + json.dumps(G) + ");"
         "new Promise(function(r){setImmediate(r)}).then(function(){return new Promise(function(r){setImmediate(r)})}).then(function(){console.log(JSON.stringify(MAJ))})")
check("R1 un rendu NEUF est epingle ET empile en tete (l'ancien reste dessous)",
      R is not None and R["s1"]["pin"]["job_id"] == "neuf" and [x["job_id"] for x in R["s1"]["hist"]] == ["neuf", "vieux"]
      and R["s1"]["hist"][0]["empreinte"] == "e1", str(R)[:300])
check("R2 un REEMPLOI ne rempile pas (pile inchangee, pas de doublon)", R is not None and R["h1"]["hist"] == G["nodes"][1]["props"]["hist"], str(R and R.get("h1")))

print("\n[U] le panneau")
H = entre("function DzPinHist(", "function DzPinPanel(")
check("U1 la pile se montre sous l'etat de l'epingle, epinglee OU NON (apres « Regenerer », on peut revenir a une prise)",
      BUN.count("r.jsx(DzPinHist,{p:p,onUpdate:onUpdate})") == 2 and "Rendus de ce nœud (" in H)
check("U2 chaque prise : sa video (rendu du job), son identifiant, sa date ; « en aval » pour celle qui alimente",
      "D.jobVideoUrl(x.job_id)" in H and '"rendu "+String(x.job_id).slice(0,8)' in H and '"en aval"' in H)
check("U3 « Utiliser » (avec title) en fait l'epingle, avec SON empreinte — verifiee par le serveur au prochain run",
      'title:"Faire alimenter l\'aval par ce rendu (gratuit) — vérifié au prochain run' in H
      and "onUpdate({pin:{job_id:String(x.job_id),empreinte:x.empreinte||\"\",le:x.le||null,choisi:!0},pinPerime:null})" in H)
check("U4 une prise faite avec d'AUTRES reglages que l'epingle active est signalee", '" · autres réglages"' in H
      and "x.empreinte!==pin.empreinte" in H)
check("U5 la chaine tient : sondes aval inchangees (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2)",
      BUN.count("DzTracks") == 178 and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
