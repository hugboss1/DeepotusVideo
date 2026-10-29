# -*- coding: utf-8 -*-
"""t331 (A1 du lot Scenario, 29/10/2026) — le pont « Scène Blender » : le backend client MCP de mcp-for-blender
(services/blender_mcp.py), ses gabarits (services/blender_gabarits.py) et ses routes /api/blender.

  [M] le protocole avec un FAUX serveur stdio (tests/_faux_mcp_blender.py, un vrai processus) : initialize, liste des
      outils, une requête du serveur refusée (-32601), bavardage et notifications ignorés, environnement MINIMAL (aucune
      clé de l'app ne sort ; DISABLE_TELEMETRY, SAFE_MODE, pas de vérification de mise à jour, hôte local) ;
  [L] la LISTE BLANCHE : execute_blender_code, generate_3d, disable_telemetry… refusés par `appeler` ; `look` sans
      `image` (aucun fichier du disque) ; argument inconnu ou hors bornes refusé ; exe absent 503, Blender fermé 503,
      serveur muet → délai 504 ;
  [G] les GABARITS : un seul littéral (le JSON), même arbre syntaxique quelle que soit la scène (un nom piégé reste une
      donnée nettoyée), focale ↔ champ, repère glTF → Blender, faisceaux exclus, couleurs de la palette t333,
      paramètres re-vérifiés ; le VRAI validateur du mode sûr de mcp-for-blender les accepte quand il est installé ;
  [R] les routes : local seulement (le compagnon appairé ne lit même pas /etat), 409 sans scène au Plateau, envoi des
      éléments → le script du gabarit part (et rien d'autre), regard → PNG rangé et servi, garder → Bibliothèque
      (source « blender », licence des assets importés), recherche → import → provenance (licence, auteur), generate_3d :
      409 sans confirme_cout avec le devis, puis la garde des plafonds (402 sous un plafond dépassé, rien n'est appelé) ;
  [A] les outils d'agent blender_scene / blender_regarder (lecture, boîte « blender », hors téléphone) ;
  [V] FACULTATIF — le vrai pont en LECTURE sur le Blender ouvert (get_scene_info, look) si BLENDER_REEL=1.
AUCUN appel réseau, aucune dépense. Run (depuis backend/) : & $PY tests/test_blender_pont.py"""
import ast
import asyncio
import base64
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzblender331_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY"):
    os.environ[_k] = ""
os.environ["FAL_KEY"] = "cle-secrete-de-banc"            # elle ne doit PAS atteindre le processus du pont
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from loguru import logger  # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import app.main as _MAIN  # noqa: E402
from app.services import blender_mcp as BM, blender_gabarits as G  # noqa: E402
from app.services import agent_outils as ao, agent_boites as B  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

W = pathlib.Path(_tmp)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())

FAUX = _ICI / "_faux_mcp_blender.py"
JOURNAL = W / "journal.jsonl"
_buf = io.BytesIO()
Image.new("RGB", (32, 18), (40, 120, 200)).save(_buf, "PNG")
FAUX_ENV = {"FAUX_JOURNAL": str(JOURNAL), "FAUX_MODE": "ok", "FAUX_PNG_B64": base64.b64encode(_buf.getvalue()).decode()}
_VRAI_POPEN = BM._popen
BM._popen = lambda args, env: _VRAI_POPEN([sys.executable, str(FAUX)], {**env, **FAUX_ENV})
os.environ["BLENDER_MCP_EXE"] = str(FAUX)               # « trouvé » : le faux tient lieu d'exécutable


def journal() -> list:
    if not JOURNAL.is_file():
        return []
    return [json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines() if l.strip()]


def appels(nom=None) -> list:
    return [m["params"] for m in journal() if m.get("method") == "tools/call"
            and (nom is None or m["params"]["name"] == nom)]


def vider():
    if JOURNAL.exists():
        JOURNAL.unlink()


def refus(fn, *a, **k):
    try:
        fn(*a, **k)
    except BM.RefusBlender as e:
        return e
    return None


# ═══════════════════════════════════════ [M] protocole ═══════════════════════════════════════
print("[M] le protocole avec un faux serveur stdio")
vider()
s = BM.sonder()
check("M1 sonder : serveur, neuf outils, Blender connecté, en-tête de scène",
      s["serveur"]["name"] == "MCP for Blender" and len(s["outils"]) == 9 and s["connecte"]
      and s["entete"].startswith("Scene 'Scene'"), s)
j = journal()
meth = [m.get("method") for m in j if "method" in m]
check("M2 ordre du cycle de vie : initialize, notifications/initialized, tools/list, tools/call",
      meth[:4] == ["initialize", "notifications/initialized", "tools/list", "tools/call"], meth)
init = next(m for m in j if m.get("method") == "initialize")
check("M3 initialize : version de protocole, aucune capacité déclarée, client nommé",
      init["params"]["protocolVersion"] == BM.VERSION_PROTOCOLE and init["params"]["capabilities"] == {}
      and init["params"]["clientInfo"]["name"] == "deepotus-blender", init)
rep = [m for m in j if m.get("id") == "srv-1"]
check("M4 la requête du serveur (élicitation) reçoit -32601 ; le bavardage non JSON est ignoré",
      rep and rep[0].get("error", {}).get("code") == -32601, rep)
env = next(m for m in j if "env" in m)
check("M5 environnement de sûreté : télémétrie coupée, mode sûr, pas de mise à jour, hôte local, port 9876",
      env["env"] == {"DISABLE_TELEMETRY": "true", "BLENDER_MCP_SAFE_MODE": "1", "BLENDERMCP_NO_UPDATE_CHECK": "1",
                     "BLENDER_HOST": "127.0.0.1", "BLENDER_PORT": "9876"}, env)
check("M6 aucune clé ni variable de l'app ne sort vers le processus (FAL_KEY, DEEPOTUS_*)",
      env["cles"] == [], env["cles"])
check("M7 une ligne de scène se lit en noms d'objets",
      BM.objets_listes(BM.scene()["texte"]) == ["Cube", "Camera", "Chaise_Bois"], BM.scene())

# ═══════════════════════════════════════ [L] liste blanche ═══════════════════════════════════════
print("[L] la liste blanche")
vider()
for nom in ("execute_blender_code", "generate_3d", "disable_telemetry", "record_trajectory_feedback",
            "get_addon_status", "inconnu"):
    e = refus(BM.appeler, nom, {"code": "import os"})
    check(f"L1 appeler({nom}) refusé (403) sans rien envoyer", e and e.statut == 403 and e.cle == "blender.outil_refuse", e)
check("L1b aucun tools/call n'est parti", appels() == [], appels())
e = refus(BM.appeler, "look", {"image": "C:/Windows/win.ini"})
check("L2 look : `image` (un fichier du disque) refusé", e and e.statut == 400, e)
e = refus(BM.appeler, "get_scene_info", {"limit": 9999})
check("L3 argument hors bornes refusé", e and e.statut == 400, e)
e = refus(BM.appeler, "search_assets", {"source": "web", "query": "x"})
check("L4 source d'assets inconnue refusée", e and e.statut == 400, e)
e = refus(BM.appeler, "import_asset", {"source": "sketchfab", "id": "../../x"})
check("L5 identifiant d'asset piégé refusé", e and e.statut == 400, e)
FAUX_ENV["FAUX_MODE"] = "ferme"
e = refus(BM.scene)
check("L6 Blender fermé : 503 blender.ferme (le port dit)", e and e.statut == 503 and e.cle == "blender.ferme"
      and e.valeurs.get("port") == 9876, e)
FAUX_ENV["FAUX_MODE"] = "muet"
_d = dict(BM.DELAIS_S)
BM.DELAIS_S["get_scene_info"] = 1.5
e = refus(BM.scene)
BM.DELAIS_S.update(_d)
check("L7 serveur muet : délai 504, le processus est fermé", e and e.statut == 504 and e.cle == "blender.delai", e)
FAUX_ENV["FAUX_MODE"] = "ok"
os.environ["BLENDER_MCP_EXE"] = str(W / "absent" / "mcp-for-blender.exe")
e = refus(BM.scene)
check("L8 exécutable absent : 503 blender.exe_absent avec le chemin", e and e.statut == 503
      and e.cle == "blender.exe_absent" and "absent" in e.valeurs.get("chemin", ""), e)
del os.environ["BLENDER_MCP_EXE"]
check("L9 sans réglage : le chemin par défaut du venv", BM.exe() == (BM.EXE_DEFAUT, "defaut"))
e = refus(BM.poser_exe, "C:/Windows/notepad.txt")
check("L10 réglage : un .exe qui existe, sinon refus", e and e.cle == "blender.exe_invalide", e)
os.environ["BLENDER_MCP_EXE"] = str(FAUX)

# ═══════════════════════════════════════ [G] gabarits ═══════════════════════════════════════
print("[G] les gabarits")
INSTANCES = [
    {"id": "sujet", "nom": "Marie", "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4],
     "role": "sujet", "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1}},
    {"id": "arbre", "nom": "cyprès", "source": {"kind": "proxy", "forme": "cylindre"}, "dims": [0.6, 3, 0.6],
     "role": "decor", "transform": {"pos": [1.5, 0, -2], "rot": [0, 90, 0], "scale": 2}},
    {"id": "rayon", "nom": "faisceau du phare", "role": "faisceau", "source": {"kind": "proxy", "forme": "cylindre"},
     "dims": [1, 1, 1], "transform": {"pos": [0, 0, 0]}},
]
KFS = [{"t": 0, "orbit": [0, 90, 6], "target": [0, 1, 0], "fov": 40, "easing": "linear"},
       {"t": 1.5, "orbit": [-10, 80, 4], "target": [0, 1, 0], "fov": 30, "easing": "linear"}]
SCENE = {"aspect": "16:9", "instances": INSTANCES, "camera": {"orbit": [0, 90, 6], "target": [0, 1, 0], "fov": 40},
         "keyframes": KFS}
p = G.depuis_scene(SCENE, list(G.ELEMENTS))
check("G1 caméra : position et visée en repère Blender, focale de 40° sur 24 mm",
      p["camera"]["pos"] == [0.0, -6.0, 1.0] and p["camera"]["cible"] == [0.0, 0.0, 1.0]
      and abs(p["camera"]["focale_mm"] - 12 / __import__("math").tan(__import__("math").radians(20))) < 1e-3
      and (p["camera"]["largeur"], p["camera"]["hauteur"]) == (1920, 1080), p["camera"])
noms = [b["nom"] for b in p["blocking"]]
check("G2 blocking : une forme par instance, faisceau exclu, nom préfixé DZ_Blocking_ et sans accent",
      noms == ["DZ_Blocking_Marie", "DZ_Blocking_cypres"], noms)
arbre_b = p["blocking"][1]
check("G3 blocking : matrice monde = rotation × demi-tailles, centre relevé de la moitié de la hauteur (×2)",
      [round(v, 4) for v in (arbre_b["monde"][0][3], arbre_b["monde"][1][3], arbre_b["monde"][2][3])] == [1.5, 2.0, 3.0]
      and round(abs(arbre_b["monde"][2][2]), 4) == 3.0, arbre_b["monde"])
from app.services import previs_palette as PP  # noqa: E402
pal = PP.palette(INSTANCES)
check("G4 couleurs = palette de la previs colorée (t333)",
      p["blocking"][0]["palette"] == pal["couleurs"]["sujet"] and p["blocking"][1]["palette"] == pal["couleurs"]["arbre"])
check("G5 clés : une par keyframe, image = t × 24 + 1, focale de chaque clé",
      [c["image"] for c in p["cles"]] == [1, 37] and p["cles"][1]["focale_mm"] > p["cles"][0]["focale_mm"], p["cles"])
check("G6 trois lampes surfaciques nommées, visée du centre du sujet",
      [l["nom"] for l in p["eclairage"]] == ["DZ_Cle", "DZ_Debouchage", "DZ_Contre"]
      and p["eclairage"][0]["puissance"] > p["eclairage"][1]["puissance"])


def literal_et_arbre(script):
    a = ast.parse(script)
    lit = None
    for n in ast.walk(a):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "P":
            lit = n.value.args[0]
            n.value.args[0] = ast.Constant("X")
    consts = [n for n in ast.walk(a) if isinstance(n, ast.Constant) and isinstance(n.value, str) and "DZ_Blocking_M" in n.value]
    return lit, ast.dump(a), consts


s1 = G.generer_script(p)
PIEGE = [dict(INSTANCES[0], nom="'); import os; os.system('calc') #\"\"\"")]
p2 = G.depuis_scene(dict(SCENE, instances=PIEGE, keyframes=[]), ["camera", "blocking"])
s2 = G.generer_script(p2)
l1, a1, _ = literal_et_arbre(s1)
l2, a2, _ = literal_et_arbre(s2)
check("G7 un seul littéral (le JSON), qui rend exactement les paramètres",
      isinstance(l1, ast.Constant) and json.loads(l1.value) == json.loads(json.dumps(p)))
check("G8 même arbre syntaxique quelle que soit la scène (nom piégé compris)", a1 == a2)
check("G9 le nom piégé est NETTOYÉ dans le JSON (ni point-virgule, ni dièse, ni guillemet, ni barre, ni saut)",
      p2["blocking"][0]["nom"].startswith("DZ_Blocking_")
      and all(ch not in p2["blocking"][0]["nom"] for ch in ";#\"\\\n"), p2["blocking"][0]["nom"])
for etiquette, mauvais in (("élément inconnu", dict(p, elements=["camera", "shell"])),
                           ("nombre non fini", dict(p, centre=[float("nan"), 0, 0])),
                           ("nom sans préfixe DZ_", dict(p, blocking=[dict(p["blocking"][0], nom="Cube")])),
                           ("collection étrangère", dict(p, collection="Collection")),
                           ("caméra renommée", dict(p, camera=dict(p["camera"], nom="Camera")))):
    try:
        G.generer_script(mauvais)
        check(f"G10 paramètres re-vérifiés : {etiquette} refusé", False)
    except G.GabaritRefuse:
        check(f"G10 paramètres re-vérifiés : {etiquette} refusé", True)
try:
    G.depuis_scene(dict(SCENE, keyframes=[KFS[0]]), ["cles"])
    check("G11 clés sans mouvement de caméra : refus dit", False)
except G.GabaritRefuse as e:
    check("G11 clés sans mouvement de caméra : refus dit", "keyframes" in str(e), e)
check("G12 le résumé DZBLENDER se relit", G.lire_resume('Code executed successfully: DZBLENDER {"crees": ["a"]}')
      == {"crees": ["a"]} and G.lire_resume("rien") is None)
VALIDEUR = pathlib.Path.home() / ".local" / "venvs" / "mcp-for-blender" / "Lib" / "site-packages" / "blender_mcp" / "safe_mode.py"
if VALIDEUR.is_file():
    spec = importlib.util.spec_from_file_location("_safe_mode_mcp", VALIDEUR)
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    res = [sm.is_safe(x) for x in (s1, s2, G.generer_script(G.nettoyage()))]
    check("G13 le VRAI validateur du mode sûr de mcp-for-blender accepte les trois scripts", all(r[0] for r in res), res)
    check("G13b … et refuse bien du code libre (témoin)", not sm.is_safe("import os\nos.system('x')")[0])
else:
    print("  SKIP  G13 mcp-for-blender absent : validateur du mode sûr non lu")

# ═══════════════════════════════════════ [R] routes ═══════════════════════════════════════
print("[R] les routes")
c = TestClient(_MAIN.app, client=("127.0.0.1", 50001))
c.__enter__()


def call(m, u, body=None, **kw):
    return c.request(m, "/api" + u, json=body, **kw)


r = call("GET", "/blender/etat")
check("R1 /etat : exe trouvé, rien lancé", r.status_code == 200 and r.json()["exe"]["trouve"], r.text[:300])
import _jeton_appareil as _JA  # noqa: E402
with TestClient(_MAIN.app, client=("192.168.1.20", 50000), headers=_JA.entetes(_MAIN.app)) as lan:
    check("R2 le compagnon appairé ne lit ni /etat, ni /scene, ni /provenance (403)",
          all(lan.get(u).status_code == 403 for u in ("/api/blender/etat", "/api/blender/scene", "/api/blender/provenance")))
    check("R2b ni ne regarde ni n'envoie (403)", lan.post("/api/blender/regarder", json={}).status_code == 403
          and lan.post("/api/blender/plan/x/envoyer", json={}).status_code == 403)
r = call("PUT", "/blender/reglages", {"exe": str(FAUX)})
check("R3 réglage du chemin sans Origin local : 403", r.status_code == 403, r.text[:200])

ch = call("POST", "/chapters", {"title": "C", "script_text": "Marie entre.\n\nLa caisse tombe."}).json()
shots = call("POST", f"/chapters/{ch.get('id')}/storyboard/decoupe", {"method": "paragraph"}).json().get("shots", [])
s0 = shots[0]["id"]
r = call("POST", "/blender/plan/inconnu/envoyer", {})
check("R4 plan inconnu : 404", r.status_code == 404, r.text[:200])
r = call("POST", f"/blender/plan/{s0}/envoyer", {})
check("R5 plan sans scène au Plateau : 409 qui dit d'ouvrir le Plateau", r.status_code == 409 and "Plateau" in r.text, r.text[:300])
sc = call("POST", "/scenes3d", {"shot_id": s0, "instances": INSTANCES, "keyframes": KFS}).json()
r = call("POST", f"/blender/plan/{s0}/envoyer", {"code": "import os"})
check("R6 le corps ne porte que des éléments : `code` refusé (400), rien envoyé", r.status_code == 400
      and appels("execute_blender_code") == [], r.text[:200])
vider()
r = call("POST", f"/blender/plan/{s0}/envoyer", {"elements": ["camera", "blocking", "cles"]})
ex = appels("execute_blender_code")
check("R7 envoi : 200, un seul execute_blender_code, le script EST le gabarit", r.status_code == 200 and len(ex) == 1
      and literal_et_arbre(ex[0]["arguments"]["code"])[1] == a1, r.text[:300])
check("R7b le résumé de Blender revient, les comptes du gabarit aussi",
      r.json()["resume"]["crees"] == ["DZ_Camera"] and r.json()["blocking"] == 2 and r.json()["cles"] == 2, r.json())
r = call("POST", f"/blender/plan/{s0}/envoyer", {"elements": ["fusee"]})
check("R8 élément inconnu : 409 dit", r.status_code == 409, r.text[:200])

vider()
r = call("POST", "/blender/assets/chercher", {"source": "sketchfab", "query": "chair"})
check("R9 recherche : licence et auteur relevés", r.status_code == 200
      and r.json()["resultats"] == [{"id": "abc123", "nom": "Chaise en bois", "auteur": "Ana", "licence": "CC Attribution"}],
      r.text[:300])
r = call("POST", "/blender/assets/importer", {"source": "sketchfab", "id": "abc123", "target_size": 1.0})
pv = r.json().get("provenance") or {}
check("R10 import : provenance notée (licence de la recherche, auteur, objets créés)", r.status_code == 200
      and pv.get("licence") == "CC Attribution" and pv.get("auteur") == "Ana" and pv.get("objets") == ["Chaise_Bois"], r.text[:300])
check("R10b /provenance le rend", call("GET", "/blender/provenance").json()["imports"][0]["id"] == "abc123")

r = call("POST", "/blender/regarder", {"mode": "camera"})
m = r.json()
check("R11 regard : PNG rangé, légende, licences des imports encore dans la scène", r.status_code == 200
      and m["url"].startswith("/api/blender/regard/") and m["licences"] and m["licences"][0]["licence"] == "CC Attribution",
      r.text[:300])
img = call("GET", m["url"].replace("/api", "", 1))
check("R12 l'image est servie (PNG)", img.status_code == 200 and img.content[:4] == b"\x89PNG", img.status_code)
check("R12b un identifiant de regard piégé : 404", all(call("GET", f"/blender/regard/{x}").status_code == 404 for x in ("x", "20261029-000000-zzzz", "20261029-000000-abcd")))
r = call("POST", f"/blender/regard/{m['id']}/garder", {"plan": s0})
check("R13 garder : Bibliothèque, source « blender », licence CC-BY avec l'auteur", r.status_code == 200
      and r.json()["licence"].startswith("CC Attribution") and "Ana" in r.json()["licence"], r.text[:300])
import sqlite3  # noqa: E402
row = sqlite3.connect(str(W / "t.db")).execute(
    "select source, licence, recette from library_assets where filename=?", (r.json()["nom"],)).fetchone()
check("R13b la ligne de la Bibliothèque : source, licence, recette (licences, plan)",
      row and row[0] == "blender" and "Ana" in row[1] and json.loads(row[2])["plan"] == s0, row)

vider()
r = call("POST", "/blender/generer", {"prompt": "coffre en bois", "fournisseur": "tripo"})
check("R14 generate_3d sans confirme_cout : 409 avec le devis, rien appelé", r.status_code == 409
      and r.json()["detail"]["devis"]["total_usd"] == 0.30 and appels("generate_3d") == [], r.text[:300])
r = call("POST", "/blender/generer", {"prompt": "x", "fournisseur": "magie", "confirme_cout": True})
check("R15 fournisseur inconnu : 400", r.status_code == 400, r.text[:200])
from app.services import plafonds as PL  # noqa: E402
_av = PL.charger()
PL.enregistrer({**_av, "global_usd": 0.01})
r = call("POST", "/blender/generer", {"prompt": "coffre en bois", "fournisseur": "tripo", "confirme_cout": True})
check("R16 plafond dépassé : 402 dz_plafond, generate_3d jamais appelé", r.status_code == 402
      and appels("generate_3d") == [], r.text[:300])
PL.enregistrer(_av)
r = call("POST", "/blender/generer", {"prompt": "coffre en bois", "fournisseur": "tripo", "confirme_cout": True})
g = appels("generate_3d")
check("R17 confirmé, sous plafond : generate_3d appelé UNE fois avec le prompt et le fournisseur",
      r.status_code == 200 and len(g) == 1 and g[0]["arguments"]["prompt"] == "coffre en bois"
      and g[0]["arguments"]["provider"] == "tripo", r.text[:300])
r = call("POST", "/blender/nettoyer")
_lit = literal_et_arbre(appels("execute_blender_code")[-1]["arguments"]["code"])[0]
check("R18 nettoyer : le gabarit de retrait part (élément « nettoyer » seul)", r.status_code == 200
      and json.loads(_lit.value)["elements"] == ["nettoyer"], r.text[:200])

# ═══════════════════════════════════════ [A] agent ═══════════════════════════════════════
print("[A] les outils d'agent")
check("A1 boîte « blender » : deux outils en lecture, hors téléphone, registre sain",
      B.BOITES["blender"]["outils"][:2] == ["blender_scene", "blender_regarder"] and not B.BOITES["blender"]["mobile"]
      and all(ao.OUTILS[o]["nature"] == "lecture" for o in B.BOITES["blender"]["outils"]) and B.verifier() == [])
check("A2 Campagnes ne la voit pas (fixture figée)", "blender_scene" not in B.outils_pour("campagnes"))
ctx = ao.Ctx(cid="banc", agent="campagnes")
r = loop.run_until_complete(ao.blender_scene(ctx))
check("A3 blender_scene : objets listés, résumé encadré comme une preuve", r["ok"] and r["donnees"]["objets"][0] == "Cube"
      and "PREUVE" in r["donnees"]["resume"], r)
r = loop.run_until_complete(ao.blender_regarder(ctx, "camera"))
check("A4 blender_regarder : l'adresse de la capture", r["ok"] and r["donnees"]["capture"].startswith("/api/blender/regard/"), r)
FAUX_ENV["FAUX_MODE"] = "ferme"
try:
    loop.run_until_complete(ao.blender_scene(ctx))
    check("A5 Blender fermé : refus dit au modèle", False)
except Exception as e:  # noqa: BLE001
    check("A5 Blender fermé : refus dit au modèle", "Blender" in str(e), e)
FAUX_ENV["FAUX_MODE"] = "ok"
c.__exit__(None, None, None)

# ═══════════════════════════════════════ [V] vrai Blender, lecture ═══════════════════════════════════════
if os.environ.get("BLENDER_REEL") == "1":
    print("[V] le vrai pont, en lecture, sur le Blender ouvert")
    BM._popen = _VRAI_POPEN
    del os.environ["BLENDER_MCP_EXE"]
    s = BM.sonder()
    check("V1 vrai serveur : neuf outils, Blender connecté", len(s["outils"]) == 9 and s["connecte"], s)
    m = BM.regarder("camera")
    check("V2 vraie capture par la caméra", (BM.dossier_regards() / f"{m['id']}.png").stat().st_size > 1000, m)
else:
    print("  SKIP  [V] vrai Blender (BLENDER_REEL=1 pour le lancer, lecture seule)")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
