# -*- coding: utf-8 -*-
"""t521 lot 2 (14/11/2026) — Réglages › « Moteurs et logiciels 3D » : Unreal Engine, Unity et la carte Blender MCP.
Unreal : exécutable UnrealEditor.exe, version lue dans Engine/Build/Build.version (rien n'est lancé), détection par le
lanceur Epic (LauncherInstalled.dat) puis Program Files ; projet = dossier qui contient un .uproject.
Unity : Unity.exe, version lue dans le dossier de l'éditeur Hub (rien n'est lancé), détection Unity Hub ; projet = dossier
qui contient Assets/ (version de l'éditeur lue dans ProjectSettings/ProjectVersion.txt, glTFast vérifié).
Blender MCP : exécutable mcp-for-blender et port ; « Tester » = la sonde existante (lit, ne modifie rien).
Aucun vrai logiciel : arborescences factices, coutures remplacées.
Run (depuis backend/) : & $PY tests/test_logiciels3d_lot2_t521.py"""
import json, os, pathlib, re, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt521b_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
CLES = ("UNREAL_PATH", "UNREAL_PROJECT_DIR", "UNITY_PATH", "UNITY_PROJECT_DIR", "BLENDER_MCP_EXE", "BLENDER_MCP_PORT")
for k in CLES:
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
from app.services import logiciels_3d as L, blender_mcp as BM        # noqa: E402
from app.i18n import texte as _texte                                  # noqa: E402

print("[1] les réglages")
for k in CLES:
    check(f"1.1 {k} admise, rubrique moteurs", k in _ALLOWED_ENV_KEYS and SR.rubrique_de(k) == "moteurs")
check("1.2 cinq cartes, dans l'ordre", list(L.LOGICIELS) == ["blender", "blender_mcp", "godot", "unreal", "unity"], list(L.LOGICIELS))

print("[2] Unreal")
ue = _tmp / "Epic Games" / "UE_5.4"
exe_ue = ue / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
exe_ue.parent.mkdir(parents=True)
exe_ue.write_bytes(b"MZ")
(ue / "Engine" / "Build").mkdir(parents=True)
(ue / "Engine" / "Build" / "Build.version").write_text(json.dumps({"MajorVersion": 5, "MinorVersion": 4, "PatchVersion": 4}), "utf-8")
lanceur = _tmp / "LauncherInstalled.dat"
lanceur.write_text(json.dumps({"InstallationList": [{"InstallLocation": str(ue), "AppName": "UE_5.4", "AppVersion": "5.4.4"},
                                                    {"InstallLocation": str(_tmp / "Fortnite"), "AppName": "Fortnite"}]}), "utf-8")
L._lanceur_epic = lambda: lanceur
L._racines_unreal = lambda: []
c = L.detecter("unreal")
check("2.1 détecté par le lanceur Epic, version dite", [x["chemin"] for x in c] == [str(exe_ue)] and c[0].get("version") == "5.4.4", c)
r = L.tester("unreal")
check("2.2 sans chemin : ok None, rien lancé", r["ok"] is None and "UNREAL_PATH" in _texte(r["message"], "fr"), r)
os.environ["UNREAL_PATH"] = str(exe_ue)
r = L.tester("unreal")
check("2.3 version lue dans Build.version (5.4.4)", r["ok"] is True and r["version"] == "5.4.4", r)
(ue / "Engine" / "Build" / "Build.version").write_text(json.dumps({"MajorVersion": 4, "MinorVersion": 27, "PatchVersion": 2}), "utf-8")
r = L.tester("unreal")
check("2.4 Unreal 4 : refusé (Unreal Engine 5 requis : import glTF Interchange)", r["ok"] is False and "5" in _texte(r["message"], "fr"), r)
(ue / "Engine" / "Build" / "Build.version").write_text(json.dumps({"MajorVersion": 5, "MinorVersion": 4, "PatchVersion": 4}), "utf-8")
proj = _tmp / "MonJeuUE"
proj.mkdir()
os.environ["UNREAL_PROJECT_DIR"] = str(proj)
r = L.tester("unreal")
check("2.5 dossier sans .uproject : refus clair", r["ok"] is False and ".uproject" in _texte(r["message"], "fr"), r)
(proj / "Poulpe.uproject").write_text(json.dumps({"EngineAssociation": "5.4"}), "utf-8")
r = L.tester("unreal")
check("2.6 projet reconnu (nom du .uproject)", r["ok"] is True and (r.get("details") or {}).get("projet") == "Poulpe", r)
check("2.7 EN traduit", "Unreal" in _texte(r["message"], "en") and _texte(r["message"], "en") != _texte(r["message"], "fr"))

print("[3] Unity")
hub = _tmp / "Unity" / "Hub" / "Editor"
exe_u = hub / "6000.0.32f1" / "Editor" / "Unity.exe"
exe_u.parent.mkdir(parents=True)
exe_u.write_bytes(b"MZ")
L._racines_unity = lambda: [hub]
c = L.detecter("unity")
check("3.1 détecté dans Unity Hub, version du dossier", [x["chemin"] for x in c] == [str(exe_u)] and c[0].get("version") == "6000.0.32f1", c)
os.environ["UNITY_PATH"] = str(exe_u)
r = L.tester("unity")
check("3.2 version lue sans lancer (6000.0.32f1)", r["ok"] is True and r["version"] == "6000.0.32f1", r)
autre = _tmp / "Unity6" / "Editor" / "Unity.exe"
autre.parent.mkdir(parents=True)
autre.write_bytes(b"MZ")
os.environ["UNITY_PATH"] = str(autre)
r = L.tester("unity")
check("3.3 version introuvable dans le chemin : ok None, dit (rien n'est lancé)", r["ok"] is None, r)
os.environ["UNITY_PATH"] = str(exe_u)
pu = _tmp / "MonJeuUnity"
pu.mkdir()
os.environ["UNITY_PROJECT_DIR"] = str(pu)
r = L.tester("unity")
check("3.4 dossier sans Assets/ : refus clair", r["ok"] is False and "Assets" in _texte(r["message"], "fr"), r)
(pu / "Assets").mkdir()
(pu / "ProjectSettings").mkdir()
(pu / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.32f1\n", "utf-8")
r = L.tester("unity")
check("3.5 projet sans glTFast : ok None, le dit (les .glb resteraient inertes)", r["ok"] is None
      and "glTFast" in _texte(r["message"], "fr"), r)
(pu / "Packages").mkdir()
(pu / "Packages" / "manifest.json").write_text('{"dependencies": {"com.unity.cloud.gltfast": "6.8.0"}}', "utf-8")
r = L.tester("unity")
check("3.6 projet avec glTFast : ok True, nom et version de l'éditeur du projet", r["ok"] is True
      and (r.get("details") or {}).get("projet") == "MonJeuUnity" and "6000.0.32f1" in _texte(r["message"], "fr"), r)

print("[4] Blender MCP")
BM.EXE_DEFAUT = _tmp / "absent" / "mcp-for-blender.exe"
r = L.tester("blender_mcp")
check("4.1 exécutable absent : ok None, rien lancé", r["ok"] is None, r)
fe = _tmp / "venv" / "mcp-for-blender.exe"
fe.parent.mkdir()
fe.write_bytes(b"MZ")
BM.EXE_DEFAUT = fe
check("4.2 détecter = l'emplacement d'installation habituel", [x["chemin"] for x in L.detecter("blender_mcp")] == [str(fe)])
BM.sonder = lambda: {"serveur": {"name": "mcp-for-blender", "version": "1.2"}, "outils": ["a", "b", "c"], "connecte": True, "entete": ""}
r = L.tester("blender_mcp")
check("4.3 sonde : serveur, outils, Blender connecté", r["ok"] is True and "3" in _texte(r["message"], "fr"), r)
BM.sonder = lambda: {"serveur": {"name": "mcp-for-blender", "version": "1.2"}, "outils": ["a"], "connecte": False, "entete": ""}
r = L.tester("blender_mcp")
check("4.4 serveur prêt mais Blender fermé : ok None, dit d'ouvrir Blender", r["ok"] is None and "Blender" in _texte(r["message"], "fr"), r)
def _refus():
    raise BM.RefusBlender("blender.lancement", 503, msg="boum")
BM.sonder = _refus
r = L.tester("blender_mcp")
check("4.5 refus du pont : ok False, son message traduit", r["ok"] is False and "boum" in _texte(r["message"], "en")
      and "could not start" in _texte(r["message"], "en"), r)
os.environ["BLENDER_MCP_PORT"] = "70000"
r = L.tester("blender_mcp")
check("4.6 port hors bornes : refus clair", r["ok"] is False and "70000" in _texte(r["message"], "fr"), r)
os.environ["BLENDER_MCP_PORT"] = ""

print("[5] routes et écran")
cl = TestClient(app, client=("127.0.0.1", 50000))
g = cl.get("/api/reglages/logiciels3d").json()
check("5.1 GET : les cinq cartes", [x["id"] for x in g["logiciels"]] == list(L.LOGICIELS), g)
t = cl.post("/api/reglages/logiciels3d/tester", json={"id": "unreal"}, headers={"Accept-Language": "en"})
check("5.2 tester Unreal en anglais", t.status_code == 200 and t.json()["ok"] is True and "Unreal" in t.json()["message"], t.text[:200])
ui = json.loads((RACINE / "frontend" / "shared" / "i18n" / "logiciels3d.json").read_text("utf-8"))
for lid in ("blender_mcp", "unreal", "unity"):
    check(f"5.3 textes de la carte {lid} FR/EN", ui.get(f"logiciels3d.{lid}.titre", {}).get("en")
          and ui.get(f"logiciels3d.{lid}.permet", {}).get("en"))
check("5.4 champ « port » libellé FR/EN", ui.get("logiciels3d.champ.port", {}).get("en"))
src = (RACINE / "frontend" / "shared" / "dz-logiciels3d.js").read_text("utf-8")
check("5.5 le module sait libeller un champ « port » et un projet Unreal/Unity",
      '"port"' in src and "logiciels3d.champ.projet_aide_" in src)
for lid in ("unreal", "unity"):
    check(f"5.6 aide du dossier de projet {lid} FR/EN", ui.get(f"logiciels3d.champ.projet_aide_{lid}", {}).get("en"))
msgs = json.loads((RACINE / "backend" / "app" / "i18n" / "messages.json").read_text("utf-8"))
for k in [k for k in msgs if k.startswith(("logiciels3d.unreal.", "logiciels3d.unity.", "logiciels3d.blender_mcp."))]:
    v = msgs[k]
    check(f"5.7 {k} : mêmes variables FR/EN", sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
