# -*- coding: utf-8 -*-
"""t521 (13/11/2026) — Réglages › « Moteurs et logiciels 3D », lot 1 : Blender et Godot. Chemin de l'exécutable (et
du projet Godot) réglable dans l'interface, détection proposée (jamais enregistrée seule), « Tester » qui lit la
version sans ouvrir de fenêtre, guide FR/EN ; une seule règle pour trouver Blender (l'Établi suit celle des passes).
Aucun vrai Blender ni Godot : exécutables factices et coutures remplacées.
Run (depuis backend/) : & $PY tests/test_logiciels3d_t521.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt521_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("BLENDER_PATH", "GODOT_PATH", "GODOT_PROJECT_DIR"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.api.routes import _ALLOWED_ENV_KEYS                         # noqa: E402
from app.api import settings_routes as SR                            # noqa: E402
from app.services import logiciels_3d as L, passes_blender as PB, mesh_export as ME   # noqa: E402
from app.i18n import texte as _texte                                  # noqa: E402

CLES = ("BLENDER_PATH", "GODOT_PATH", "GODOT_PROJECT_DIR")

print("[1] les réglages")
for k in CLES:
    check(f"1.1 {k} admise par Réglages, rangée dans la rubrique moteurs",
          k in _ALLOWED_ENV_KEYS and SR.rubrique_de(k) == "moteurs")
check("1.2 la rubrique existe pour la recherche des Réglages", "moteurs" in SR._RUBRIQUES
      and any(s == "moteurs" for s, _l, _m in SR._INDEX_FIXE))
check("1.3 deux logiciels dans ce lot, Blender puis Godot", list(L.LOGICIELS) == ["blender", "godot"])
check("1.4 Godot a un exécutable ET un dossier de projet",
      [c["cle"] for c in L.LOGICIELS["godot"]["champs"]] == ["GODOT_PATH", "GODOT_PROJECT_DIR"])

print("[2] Godot : détecter (proposé, jamais enregistré)")
racine_g = _tmp / "pf" / "Godot"
racine_g.mkdir(parents=True)
exe_g = racine_g / "Godot_v4.3-stable_win64.exe"
exe_g.write_bytes(b"MZ")
(racine_g / "Godot_v4.3-stable_win64_console.exe").write_bytes(b"MZ")
(racine_g / "lisez-moi.txt").write_text("x", "utf-8")
L._racines_godot = lambda: [_tmp / "pf"]
L._which = lambda nom: None
cands = L.detecter("godot")
check("2.1 l'exécutable trouvé, la console écartée", [c["chemin"] for c in cands] == [str(exe_g)], cands)
check("2.2 rien n'est enregistré par la détection", os.environ.get("GODOT_PATH", "") == "")
check("2.3 la version se lit dans le nom du fichier", cands and cands[0].get("version") == "4.3", cands)

print("[3] Godot : tester")
APPELS = []


def faux_executer(argv, timeout=20):
    APPELS.append(list(argv))
    return "4.3.stable.official.77dcf97d8\n"


L._executer = faux_executer
r = L.tester("godot")
check("3.1 sans chemin : rien n'est lancé, on dit quoi faire (ok None)", r["ok"] is None and not APPELS
      and "GODOT_PATH" in _texte(r["message"], "fr"), r)
os.environ["GODOT_PATH"] = str(exe_g)
r = L.tester("godot")
check("3.2 version lue (4.3), ok True", r["ok"] is True and r["version"] == "4.3", r)
check("3.3 lancée par la CONSOLE voisine, --headless --version (aucune fenêtre)",
      APPELS and APPELS[-1][0].endswith("_console.exe") and APPELS[-1][1:] == ["--headless", "--version"], APPELS)
L._executer = lambda argv, timeout=20: ""
r = L.tester("godot")
check("3.4 sortie muette : la version du nom de fichier suffit", r["ok"] is True and r["version"] == "4.3", r)
L._executer = lambda argv, timeout=20: "3.5.3.stable.official\n"
r = L.tester("godot")
check("3.5 Godot 3 : refusé en le disant (Godot 4 requis)", r["ok"] is False and "4" in _texte(r["message"], "fr")
      and r["version"] == "3.5.3", r)
os.environ["GODOT_PATH"] = str(racine_g / "absent.exe")
r = L.tester("godot")
check("3.6 chemin vers rien : refus clair", r["ok"] is False and "absent.exe" in _texte(r["message"], "fr"), r)
os.environ["GODOT_PATH"] = str(exe_g)
L._executer = faux_executer
projet = _tmp / "monjeu"
projet.mkdir()
os.environ["GODOT_PROJECT_DIR"] = str(projet)
r = L.tester("godot")
check("3.7 dossier sans project.godot : refus clair", r["ok"] is False and "project.godot" in _texte(r["message"], "fr"), r)
(projet / "project.godot").write_text('[application]\n\nconfig/name="Démo poulpe"\n', "utf-8")
r = L.tester("godot")
check("3.8 projet reconnu, son nom lu", r["ok"] is True and (r.get("details") or {}).get("projet") == "Démo poulpe", r)
check("3.9 EN : message traduit", "Godot" in _texte(r["message"], "en") and _texte(r["message"], "en") != _texte(r["message"], "fr"))

print("[4] Blender : tester et détecter, une seule règle")
fb = _tmp / "Blender 4.5" / "blender.exe"
fb.parent.mkdir(parents=True)
fb.write_bytes(b"MZ")
PB._racines = lambda: [fb]
PB._CACHE.clear()
PB._sortie_version = lambda exe: "Blender 4.5.1 LTS\n"
r = L.tester("blender")
check("4.1 version lue, ok True, exécutable dit", r["ok"] is True and r["version"] == "4.5.1"
      and (r.get("details") or {}).get("exe") == str(fb), r)
PB._CACHE.clear()
PB._sortie_version = lambda exe: "Blender 3.6.2\n"
r = L.tester("blender")
check("4.2 trop ancien : refusé, minimum dit", r["ok"] is False and "4.2" in _texte(r["message"], "fr"), r)
PB._racines = lambda: []
PB._CACHE.clear()
r = L.tester("blender")
check("4.3 introuvable : ok None, renvoi au guide", r["ok"] is None and "Blender" in _texte(r["message"], "fr"), r)
PB.candidats_auto = lambda: [fb]
check("4.4 détecter = les candidats automatiques de passes_blender", [c["chemin"] for c in L.detecter("blender")] == [str(fb)])

LANCES = []
ME._lancer = lambda argv: LANCES.append(argv)
os.environ["BLENDER_PATH"] = ""
PB._racines = lambda: [fb]
PB._CACHE.clear()
PB._sortie_version = lambda exe: "Blender 4.5.1\n"
ME.chemin_export = lambda job, version, cible: fb               # un fichier qui existe suffit ici
try:
    rr = ME.ouvrir("job", 1, "blender")
    check("4.5 l'Établi ouvre Blender trouvé par la règle des passes (BLENDER_PATH vide)",
          LANCES and LANCES[-1][0] == str(fb) and rr["exe"] == str(fb), (LANCES, rr))
except RuntimeError as e:
    check("4.5 l'Établi ouvre Blender trouvé par la règle des passes (BLENDER_PATH vide)", False, e)

print("[5] routes")
c = TestClient(app, client=("127.0.0.1", 50000))
os.environ["GODOT_PATH"] = str(exe_g)
L._executer = faux_executer
g = c.get("/api/reglages/logiciels3d")
j = g.json() if g.status_code == 200 else {}
check("5.1 GET : les deux logiciels, leurs champs et leurs valeurs", g.status_code == 200
      and [x["id"] for x in j.get("logiciels", [])] == ["blender", "godot"]
      and j["logiciels"][1]["champs"][0]["valeur"] == str(exe_g), g.text[:300])
t = c.post("/api/reglages/logiciels3d/tester", json={"id": "godot"}, headers={"Accept-Language": "en"})
check("5.2 POST tester, EN", t.status_code == 200 and t.json()["ok"] is True and "Godot" in t.json()["message"]
      and "projet" not in t.json()["message"], t.text[:300])
d = c.post("/api/reglages/logiciels3d/detecter", json={"id": "godot"})
check("5.3 POST detecter", d.status_code == 200 and d.json()["candidats"][0]["chemin"] == str(exe_g), d.text[:300])
check("5.4 logiciel inconnu : 404", c.post("/api/reglages/logiciels3d/tester", json={"id": "maya"}).status_code == 404)
import _jeton_appareil as _JA                                          # noqa: E402 — le réseau local exige un jeton d'appareil
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    check("5.5 hors boucle locale (appareil appairé) : refusé", c2.get("/api/reglages/logiciels3d").status_code == 403)
w = c.post("/api/settings/keys", json={"name": "GODOT_PROJECT_DIR", "value": str(projet)})
check("5.6 enregistrer un chemin par /api/settings/keys, appliqué à chaud", w.status_code == 200
      and os.environ.get("GODOT_PROJECT_DIR") == str(projet), w.text[:200])

print("[6] traductions et écran")
dico = json.loads((RACINE / "backend" / "app" / "i18n" / "messages.json").read_text("utf-8"))
neufs = {k: v for k, v in dico.items() if k.startswith("logiciels3d.")}
check("6.1 messages logiciels3d.* FR/EN, mêmes variables", len(neufs) >= 8 and all(
    v.get("fr") and v.get("en") and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
    for v in neufs.values()), neufs)
ui = json.loads((RACINE / "frontend" / "shared" / "i18n" / "logiciels3d.json").read_text("utf-8"))
check("6.2 dictionnaire d'écran : clés à trois segments, FR et EN", ui and all(
    re.fullmatch(r"logiciels3d\.[a-z0-9_]+\.[a-z0-9_]+", k) and v.get("fr") and v.get("en") for k, v in ui.items()))
mod = RACINE / "frontend" / "shared" / "dz-logiciels3d.js"
check("6.3 module partagé, copie dist identique", mod.is_file()
      and mod.read_bytes() == (RACINE / "frontend" / "dist" / "shared" / "dz-logiciels3d.js").read_bytes())
check("6.4 chargé par la SPA", '<script src="/shared/dz-logiciels3d.js"></script>'
      in (RACINE / "frontend" / "dist" / "index.html").read_text("utf-8"))
r_ = subprocess.run(["node", "--check", str(mod)], capture_output=True, text=True)
check("6.5 node --check du module", r_.returncode == 0, r_.stderr[-200:])
src = mod.read_text("utf-8")
check("6.6 aucun texte en dur hors dzT : toutes les clés citées existent",
      all(k in ui for k in re.findall(r'T\("(logiciels3d\.[a-z0-9_.]+)"', src)) and 'T("' in src)
B = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text("utf-8")
check("6.7 maillon dzlogiciels3d : onglet, hôte, liste blanche, rubrique",
      '{k:"moteurs",l:dzT("logiciels3d.reglages.onglet")}' in B and "data-dz-logiciels3d-hote" in B
      and '"paths","moteurs","news"' in B and 'moteurs:dzT("logiciels3d.reglages.onglet")' in B)
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                                          # noqa: E402
import patch_bundle_dzlogiciels3d as PM                               # noqa: E402
check("6.8 avant_dzlogiciels3d == defaire, sans marqueur rendu tel quel",
      AIDE.avant_dzlogiciels3d(B) == PM.defaire(B) and AIDE.avant_dzlogiciels3d(PM.defaire(B)) == PM.defaire(B))
aide = (_ICI / "_i18n_l1_aide.py").read_text("utf-8")
i = aide.index("def avant_dzclesguides(")
corps = aide[i:aide.index("\ndef ", i + 10)]
check("6.9 appelé EN TÊTE de avant_dzclesguides", "bundle = avant_dzlogiciels3d(bundle)" in corps
      and corps.index("avant_dzlogiciels3d(") < corps.index("if _m.MARKER not in bundle"))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
