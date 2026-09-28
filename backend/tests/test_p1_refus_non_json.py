# -*- coding: utf-8 -*-
"""P1 #10 (28/09/2026) — UN REFUS NON-JSON AFFICHE « HTTP <code> » AU LIEU DU TEXTE DU SERVEUR.

Defaut MESURE le 28/09 (bundle de 5a4043e, fonctions de l'api executees sous
node avec un faux fetch) : D.postJson (R7er1), renderLayoutTemplate (R7er2)
et uploadVideo (R7up1) ne lisaient que le `detail` d'un corps JSON ; un corps
en TEXTE (500 « Internal Server Error » d'uvicorn, page HTML d'un proxy, 413
en clair) donnait « HTTP 500 » -- le texte du serveur etait perdu (R7er2
l'affichait avant R7er2 : regression de la cloture T11b).
Decision : detail texte -> le texte ; liste pydantic -> le premier msg ;
corps NON-JSON non vide -> « HTTP <code> : <texte> » (balises retirees,
blancs replies, 160 caracteres au plus) ; corps vide ou JSON sans detail
lisible -> « HTTP <code> » (inchange). UNE regle pour les trois lecteurs.
Temoin : le bundle de BASE (git show). Faute n6 : details par _d().
Run : & $PY tests/test_p1_refus_non_json.py   (depuis backend/)
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
BASE = "5a4043e"
NODE = shutil.which("node")
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
TMP = tempfile.mkdtemp(prefix="dzp1rj_")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:700]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


def _entre(txt, debut, fin):
    i = txt.find(debut)
    j = txt.find(fin, i)
    return txt[i:j] if i >= 0 and j > i else ""


LONG = "x" * 300
HTML = "<!doctype html><html><head><title>502 Bad Gateway</title></head><body><h1>502   Bad\n Gateway</h1></body></html>"
CAS = [
    ("texte", 500, "Internal Server Error"),
    ("html", 502, HTML),
    ("vide", 413, ""),
    ("blancs", 500, "   \n  "),
    ("long", 500, LONG),
    ("detail", 402, {"detail": "Estimation 4,73 $ > plafond 1,00 $ — rien n'a été généré."}),
    ("liste", 422, {"detail": [{"loc": ["body", "x"], "msg": "Input should be a valid integer", "type": "int_parsing"}]}),
    ("objet", 503, {"detail": {"code": 7}}),
    ("json_nu", 500, "123"),
    ("json_null", 500, "null"),
]
ATTENDU = {
    "texte": "HTTP 500 : Internal Server Error",
    "html": "HTTP 502 : 502 Bad Gateway 502 Bad Gateway",
    "vide": "HTTP 413",
    "blancs": "HTTP 500",
    "long": "HTTP 500 : " + "x" * 160,
    "detail": "Estimation 4,73 $ > plafond 1,00 $ — rien n'a été généré.",
    "liste": "Input should be a valid integer",
    "objet": "HTTP 503",
    "json_nu": "HTTP 500",
    "json_null": "HTTP 500",
}


def _sonde(src):
    pj = _entre(src, "postJson:async(e,t)=>{", "};let Io=null")
    lt = _entre(src, "renderLayoutTemplate:async", ",listSeedanceTemplates:")
    up = _entre(src, "uploadVideo:async e=>{", ",getCaptionPack:")
    js = (r"""
const Te="/api"; var window={}; function dzGraphVoiceover(){return null} function dzRunMaxTake(){return void 0}
class FormData{append(){}}
var REP=null;
async function fetch(u,o){ return REP; }
function rep(status, corps){ const b=corps===undefined?"":(typeof corps=="string"?corps:JSON.stringify(corps));
  return {ok: status>=200&&status<300, status, text: async()=>b, json: async()=>JSON.parse(b)}; }
const api={""" + pj + "};const LT={" + lt + "};const UP={" + up + "};" + r""";
const CAS=__CAS__;
(async()=>{const out={};for(const c of CAS){REP=rep(c[1],c[2]);
  out[c[0]]=[await api.postJson("/generate",{}),await LT.renderLayoutTemplate("t1",{}),await UP.uploadVideo({})];}
  process.stdout.write(JSON.stringify(out));})().catch(e=>{process.stdout.write(JSON.stringify({erreur:String(e)}))});
""").replace("__CAS__", json.dumps(CAS))
    p = pathlib.Path(TMP) / ("s%d.js" % abs(hash(js)))
    p.write_text(js, encoding="utf-8")
    r = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return r.returncode, json.loads(r.stdout), r.stderr, (len(pj), len(lt), len(up))
    except Exception:
        return r.returncode, None, (r.stderr or "")[-400:] + (r.stdout or "")[:200], (len(pj), len(lt), len(up))


bun = BUNDLE.read_bytes().decode("utf-8")
old = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], cwd=ROOT,
                     capture_output=True).stdout.decode("utf-8")

print("\n[0] preconditions et temoin (bundle de %s)" % BASE)
rc, N, err, lg = _sonde(bun)
check("0.1 les trois lecteurs extraits du bundle livre et executes", rc == 0 and isinstance(N, dict) and "erreur" not in N and min(lg) > 100, _d(err, lg, N))
rco, O, erro, lgo = _sonde(old)
check("0.2 temoin : les memes lecteurs extraits du bundle de base et executes", rco == 0 and isinstance(O, dict) and "erreur" not in O, _d(erro, lgo))
N = N if isinstance(N, dict) else {}
O = O if isinstance(O, dict) else {}
check("0.3 TEMOIN : a la base, un 500 en texte brut s'affiche « HTTP 500 » dans les trois lecteurs (le texte est perdu)",
      [x.get("error") for x in O.get("texte", [{}] * 3)] == ["HTTP 500"] * 3, _d(O.get("texte")))
check("0.4 TEMOIN : a la base, une page HTML de proxy s'affiche « HTTP 502 »",
      [x.get("error") for x in O.get("html", [{}] * 3)] == ["HTTP 502"] * 3, _d(O.get("html")))

print("\n[1] une regle pour les trois lecteurs (postJson, rendu de layout, upload)")
NOMS = ("postJson", "layout", "upload")
for nom, att in ATTENDU.items():
    got = [x.get("error") for x in N.get(nom, [{}] * 3)]
    check(f"1.{nom} : {att[:60]}", got == [att] * 3, _d(got))
check("1.z postJson rend toujours `status` ; aucun lecteur ne dit ok:true sur un refus",
      all((N.get(k) or [{}])[0].get("status") == c for k, c, _b in CAS)
      and all(x.get("ok") is False for k in ATTENDU for x in N.get(k, [{}])), "")

print("\n[2] le patcher")
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                           # noqa: E402
check("2.1 R7up1, R7er1 et R7er2 partagent LA lecture (_R7_DETAIL, x1 chacun) ; le bundle la porte x3",
      all(r.count(P._R7_DETAIL) == 1 for r in (P.R_R7UP1, P.R_R7ER1, P.R_R7ER2)) and bun.count(P._R7_DETAIL) == 3,
      _d(bun.count(P._R7_DETAIL)))
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("2.2 le bundle ENTIER passe node --check", _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else ""))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
