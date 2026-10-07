# -*- coding: utf-8 -*-
"""Tache #79 PR C (plan-etabli T10, 03/10/2026) — les versions de l'Etabli EN ARBRE dans la Bibliotheque, dans le
bundle LIVRE : dzLigneeEtabli est extrait et EXECUTE sous node, sur la liste de tout onglet.
Ce que le plan faisait autrement : un maillon `lignee` en queue de chaine (la pratique est la couche montage) et un
invariant « Etabli x2 » devenu faux ; un replieur qui gardait l'ordre RECU (un tri par nom de l'onglet aurait
melange l'arbre) — ici l'ordre de la lignee est rendu par `rang`.
Temoin positif : le bundle de la base (627df13d) n'a pas le replieur.
Run (depuis backend/) : & $PY tests/test_etabli_lignee_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzetle_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "627df13d"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la liste filtree (Lfs) mais pas le replieur", r0.returncode == 0
      and b"q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]))" in r0.stdout and b"dzLigneeEtabli" not in r0.stdout)
check("T2 la liste de TOUT onglet passe par le replieur, APRES le filtre, une seule fois",
      BUN.count("q=dzLigneeEtabli(Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o])))") == 1 and BUN.count("dzLigneeEtabli(") == 2)

k = BUN.find("function dzLigneeEtabli(L){")
fin = BUN.find("return out}catch(e){return L}}", k)
SRC = BUN[k:fin + len("return out}catch(e){return L}}")] if k >= 0 and fin > 0 else ""
check("T3 la couche livree a dzLigneeEtabli (une fois)", BUN.count("function dzLigneeEtabli(") == 1 and SRC != "")

js = SRC + r"""
var E=[{job:"a",version:3,profondeur:1,rang:3,name:"a v3"},{job:"b",version:1,profondeur:0,rang:0,name:"b v1"},
       {job:"a",version:1,profondeur:0,rang:1,name:"a v1"},{job:"a",version:4,profondeur:2,rang:2,name:"a v4"},
       {job:"c",version:9,profondeur:7,rang:5,name:"c v9"}];
var IM=[{name:"img.png"},{name:"autre.png"}],MIX=[{name:"x",profondeur:1},{name:"y"}];
console.log(JSON.stringify({etabli:dzLigneeEtabli(E).map(function(z){return z.name}),
  meme:dzLigneeEtabli(IM)===IM,mix:dzLigneeEtabli(MIX)===MIX,vide:dzLigneeEtabli([]).length,nul:dzLigneeEtabli(null),
  intact:E[3].name,racine:dzLigneeEtabli([E[2]])[0]===E[2],
  sansrang:dzLigneeEtabli([{job:"z",profondeur:1,name:"p"},{job:"z",profondeur:0,name:"q"}]).map(function(z){return z.name})}));
"""
f = _TMP / "r.js"; f.write_text(js, encoding="utf-8")
p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    R = json.loads(p.stdout.strip().splitlines()[-1])
except Exception:
    R = None; print("   (node)", (p.stderr or p.stdout)[-400:])
check("N0 sous node : le replieur s'execute", R is not None)
if R:
    check("N1 regroupe PAR JOB (dans l'ordre d'arrivee des jobs), remet chaque job dans l'ordre de la LIGNEE (rang), decale d'un ↳ par generation, trois au plus",
          R["etabli"] == ["a v1", "↳ ↳ a v4", "↳ a v3", "b v1", "↳ ↳ ↳ c v9"], str(R["etabli"]))
    check("N2 toute autre liste (images, liste melangee) ressort INCHANGEE — le MEME objet ; vide et nul aussi",
          R["meme"] is True and R["mix"] is True and R["vide"] == 0 and R["nul"] is None)
    check("N3 aucune entree d'origine n'est modifiee (copie) ; une racine est rendue telle quelle", R["intact"] == "a v4" and R["racine"] is True)
    check("N4 sans rang (route d'avant), l'ordre recu est garde dans le job", R["sansrang"] == ["↳ p", "q"], str(R["sansrang"]))
check("T4 la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3, __dzEtabli x2)",
      BUN.count("DzTracks") == 181 and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2
      and BUN.count("dzRunMaxTake()") == 3 and BUN.count("__dzEtabli") == 2)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
