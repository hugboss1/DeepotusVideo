# -*- coding: utf-8 -*-
"""t382 (30/10/2026, lot « Réglages : chemins & apparence ») — Réglages › Apparence : la PALETTE gardée par le serveur
(backend/app/services/apparence.py, routes /api/reglages/apparence). Banc SERVEUR ; l'écran a son banc
(test_apparence_ecran.py, qui joue frontend/shared/qa/apparence.test.mjs).

La palette vit dans DATA_ROOT/apparence.json : l'app s'ouvre sur 127.0.0.1 OU sur deepotus.localhost, deux origines
qui n'ont pas le même localStorage ; le serveur est la vérité, le localStorage n'est que le cache du premier rendu.
  [N] normaliser : préréglage connu, « libre » exige les six couleurs #rrggbb (mises en minuscules), « fort » booléen
      gardé seulement pour « libre » ; tout le reste refusé (ValueError) ;
  [F] fichier : absent ou illisible = Deepotus sombre ; écrire puis relire ; rien d'autre que l'état normalisé ;
  [R] routes : GET (état, préréglages, jetons), POST valide / refusé 400 traduit en anglais, refus depuis un autre
      appareil ; les préréglages du serveur sont EXACTEMENT ceux de l'écran (dz-apparence.js) ;
  [E] chaque message d'erreur neuf est traduit (i18n_l10_erreurs.py --check) ; la recherche des Réglages trouve
      « palette », « thème clair », « contraste ».
Run (depuis backend/) : & $PY tests/test_apparence.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzapparence_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp / "donnees")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "donnees" / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "donnees" / "outputs")
(_tmp / "donnees" / "images").mkdir(parents=True)
(_tmp / "donnees" / "outputs").mkdir(parents=True)
(_tmp / "donnees" / ".env").write_text("# banc\n", encoding="utf-8")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import DATA_ROOT                                    # noqa: E402

try:
    from app.services import apparence as A                         # noqa: E402
except Exception as e:                                               # le banc rougit, ne meurt pas
    A = None
    print(f"  (service introuvable : {e!r})")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def refus(f, *a):
    try:
        f(*a)
    except ValueError as e:
        return str(e) or "?"
    except Exception as e:                                           # noqa: BLE001
        return f"AUTRE {e!r}"
    return ""


LIBRE = {"preset": "libre", "couleurs": {"fond": "#101010", "panneau": "#1A1A1A", "texte": "#F0F0F0",
                                         "accent": "#33AAFF", "succes": "#44DD88", "erreur": "#FF6655"}}
FICHIER = DATA_ROOT / "apparence.json"

print("\n[N] normaliser")
check("N0 le service existe", A is not None)
if A is not None:
    check("N1 préréglages et jetons", list(A.PRESETS) == ["sombre", "clair", "contraste", "deeplab"]
          and list(A.JETONS) == ["fond", "panneau", "texte", "accent", "succes", "erreur"], (A.PRESETS, A.JETONS))
    check("N2 un préréglage seul est gardé seul", A.normaliser({"preset": "clair", "couleurs": LIBRE["couleurs"],
                                                                "fort": True}) == {"preset": "clair"})
    n = A.normaliser(LIBRE)
    check("N3 « libre » garde les six couleurs, en minuscules", n == {"preset": "libre", "couleurs": {
        k: v.lower() for k, v in LIBRE["couleurs"].items()}}, n)
    check("N4 « fort » n'est gardé que vrai et pour « libre »",
          A.normaliser(dict(LIBRE, fort=True)).get("fort") is True and "fort" not in A.normaliser(dict(LIBRE, fort=0)))
    check("N5 préréglage inconnu refusé", "inconnu" in refus(A.normaliser, {"preset": "rose"}).lower())
    check("N6 corps qui n'est pas un objet refusé", refus(A.normaliser, ["sombre"]) and refus(A.normaliser, None))
    for j, mauvais in (("fond", None), ("texte", "#fff"), ("accent", "red"), ("erreur", "#12345g"),
                       ("succes", "#1234567"), ("panneau", 123)):
        c = dict(LIBRE["couleurs"])
        if mauvais is None:
            c.pop(j)
        else:
            c[j] = mauvais
        m = refus(A.normaliser, {"preset": "libre", "couleurs": c})
        check(f"N7 « libre » refuse {j}={mauvais!r}", m and j in m, m)
    check("N8 une couleur en trop est refusée (rien d'inconnu dans le fichier)", refus(A.normaliser, {
        "preset": "libre", "couleurs": dict(LIBRE["couleurs"], brand="#ff0000")}))
    check("N9 « fort » non booléen refusé", refus(A.normaliser, dict(LIBRE, fort="oui")))

print("\n[F] fichier")
if A is not None:
    FICHIER.unlink(missing_ok=True)
    check("F1 absent = Deepotus sombre", A.lire() == {"preset": "sombre"})
    FICHIER.write_text("{pas du json", encoding="utf-8")
    check("F2 illisible = Deepotus sombre", A.lire() == {"preset": "sombre"})
    FICHIER.write_text(json.dumps({"preset": "libre", "couleurs": {"fond": "#000"}}), encoding="utf-8")
    check("F3 invalide = Deepotus sombre", A.lire() == {"preset": "sombre"})
    e = A.ecrire(dict(LIBRE, fort=True, autre="x"))
    check("F4 écrire rend l'état normalisé", e.get("preset") == "libre" and "autre" not in e and e.get("fort") is True)
    check("F5 relire le redonne", A.lire() == e and json.loads(FICHIER.read_text(encoding="utf-8")) == e)
    av = FICHIER.read_bytes()
    check("F6 une écriture refusée ne touche pas le fichier", refus(A.ecrire, {"preset": "?"}) and FICHIER.read_bytes() == av)

print("\n[R] routes")
c = TestClient(app)
cd = TestClient(app, client=("192.168.1.50", 5000))
FICHIER.unlink(missing_ok=True)
r = c.get("/api/reglages/apparence")
check("R1 GET : état par défaut, préréglages, jetons", r.status_code == 200 and r.json() == {
    "etat": {"preset": "sombre"}, "presets": ["sombre", "clair", "contraste", "deeplab"],
    "jetons": ["fond", "panneau", "texte", "accent", "succes", "erreur"]}, (r.status_code, r.text[:200]))
r = c.post("/api/reglages/apparence", json={"preset": "clair"})
check("R2 POST préréglage", r.status_code == 200 and r.json() == {"etat": {"preset": "clair"}}
      and c.get("/api/reglages/apparence").json()["etat"] == {"preset": "clair"}, r.text[:200])
r = c.post("/api/reglages/apparence", json=LIBRE)
check("R3 POST libre", r.status_code == 200 and r.json()["etat"]["couleurs"]["texte"] == "#f0f0f0", r.text[:200])
r = c.post("/api/reglages/apparence", json={"preset": "rose"}, headers={"Accept-Language": "en"})
check("R4 POST refusé : 400 traduit en anglais", r.status_code == 400 and "Unknown" in r.json().get("detail", ""),
      (r.status_code, r.text[:200]))
check("R5 un refus ne change pas l'état", c.get("/api/reglages/apparence").json()["etat"]["preset"] == "libre")
r = cd.post("/api/reglages/apparence", json={"preset": "sombre"})
check("R6 un autre appareil ne change pas la palette", r.status_code in (401, 403)
      and c.get("/api/reglages/apparence").json()["etat"]["preset"] == "libre", r.status_code)
_rt = (RACINE / "backend" / "app" / "api" / "settings_routes.py").read_text(encoding="utf-8")
_p = _rt[_rt.find("async def apparence_poser("):]
_p = _p[:_p.find("\n@router")]
check("R6b l'écriture passe par la garde locale des Réglages (_local), avant tout", _p.split("\n")[1].strip()
      == "_local(request)", _p[:160])
JS = (RACINE / "frontend" / "shared" / "dz-apparence.js")
src = JS.read_text(encoding="utf-8") if JS.exists() else ""
m = re.search(r"var ORDRE = \[([^\]]*)\]", src)
ordre = re.findall(r'"([a-z]+)"', m.group(1)) if m else []
check("R7 l'écran propose exactement les préréglages du serveur", A is not None and ordre == list(A.PRESETS), ordre)
mj = re.search(r"var JETONS = \[([^\]]*)\]", src)
check("R8 l'écran édite exactement les jetons du serveur", A is not None and mj
      and re.findall(r'"([a-z]+)"', mj.group(1)) == list(A.JETONS))

print("\n[E] traductions, recherche")
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
check("E1 i18n_l10_erreurs --check", r.returncode == 0, (r.stdout + r.stderr)[-400:])
r = c.get("/api/reglages/index")
ent = r.json().get("entrees", []) if r.status_code == 200 else []
for mot in ("palette", "thème clair", "contraste", "couleurs"):
    check(f"E2 la recherche des Réglages trouve « {mot} » sous Apparence", any(
        e["section"] == "appearance" and mot in (e["libelle"] + " " + e["mots"]).lower() for e in ent))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
