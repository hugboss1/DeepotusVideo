# -*- coding: utf-8 -*-
"""t332 (A2 du lot Scenario, 29/10/2026) — l'ALLER-RETOUR Plateau 3D ↔ Blender, sur le socle t331 (client MCP
services/blender_mcp.py, gabarits services/blender_gabarits.py, routes /api/blender).

  [G] les gabarits : l'élément « maquette » (import du GLB de la scène par un chemin LOCAL du serveur, vérifié : absolu,
      .glb, sans « .. » ni saut de ligne), le gabarit de RETOUR (un seul littéral, même arbre quelle que soit la
      demande, copie .blend par save_as_mainfile(copy=True)), le VRAI validateur du mode sûr de mcp-for-blender accepte
      l'aller avec maquette et le retour (s'il est installé) ; la relecture (`lire_retour`) refuse un JSON abîmé et
      NETTOIE les noms venus du fichier de l'utilisateur ; champ vertical selon l'ajustement du capteur ; repère
      Blender → glTF ; ALLER puis RETOUR = la caméra et les keyframes du Plateau à l'identique ;
  [R] les routes : /aller (caméra, clés si le plan bouge, maquette composée dans outputs/blender/plans/<plan>/,
      faisceaux exclus ; aucun corps) ; /reprendre (copie .blend rangée, vignette en Bibliothèque source « blender »
      avec la provenance et le .blend pour mère, rien écrit au Plateau) ; /retours, /retour/{rid}/blend|vignette ;
      /appliquer sans confirmer = avant/après seulement, avec confirmer = caméra + keyframes au Plateau ; refus : pas de
      copie .blend (502, dossier retiré), Blender fermé (503), caméra inconnue (409), compagnon (403) ;
  [A] l'outil d'agent blender_retour (lecture du disque seulement, boîte « blender ») ;
  [H] FACULTATIF (BLENDER_REEL=1) : aller puis retour dans un vrai Blender HEADLESS (BLENDER_PATH ou Program Files),
      fichier vierge, copie .blend relue.
AUCUN appel réseau, aucune dépense. Run (depuis backend/) : & $PY tests/test_blender_aller_retour.py"""
import ast
import asyncio
import base64
import importlib.util
import io
import json
import math
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzblender332_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[_k] = ""
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
from app.services import scene3d as S  # noqa: E402
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
os.environ["BLENDER_MCP_EXE"] = str(FAUX)


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


def literal_et_arbre(script):
    a = ast.parse(script)
    lit = None
    for n in ast.walk(a):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "P":
            lit = n.value.args[0]
            n.value.args[0] = ast.Constant("X")
    return lit, ast.dump(a)


def refuse(fn, *a, **k):
    try:
        fn(*a, **k)
    except G.GabaritRefuse:
        return True
    return False


INSTANCES = [
    {"id": "sujet", "nom": "Marie", "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4],
     "role": "sujet", "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1}},
    {"id": "arbre", "nom": "cyprès", "source": {"kind": "proxy", "forme": "cylindre"}, "dims": [0.6, 3, 0.6],
     "role": "decor", "transform": {"pos": [1.5, 0, -2], "rot": [0, 90, 0], "scale": 1}},
    {"id": "rayon", "nom": "faisceau du phare", "role": "faisceau", "source": {"kind": "proxy", "forme": "cylindre"},
     "dims": [1, 1, 1], "transform": {"pos": [0, 0, 0]}},
]
KFS = [{"t": 0, "orbit": [20, 80, 6], "target": [0, 1, 0], "fov": 40, "easing": "linear"},
       {"t": 1.5, "orbit": [-10, 85, 4], "target": [0, 1.2, 0], "fov": 30, "easing": "ease-in"}]
SCENE = {"aspect": "16:9", "instances": INSTANCES, "camera": {"orbit": [20, 80, 6], "target": [0, 1, 0], "fov": 40},
         "keyframes": KFS}
GLB = str(W / "outputs" / "scene.glb")

# ═══════════════════════════════════════ [G] gabarits ═══════════════════════════════════════
print("[G] les gabarits de l'aller-retour")
p = G.depuis_scene(SCENE, ["camera", "cles", "maquette"], glb=GLB)
check("G1 maquette : le chemin du GLB entre dans les paramètres, éléments dans l'ordre fermé",
      p["maquette"] == {"glb": GLB} and p["elements"] == ["camera", "cles", "maquette"], p["elements"])
check("G2 maquette sans GLB composé : refus dit", refuse(G.depuis_scene, SCENE, ["maquette"]))
check("G2b les éléments de t331 restent quatre (la boîte « Envoyer vers Blender » n'a pas changé)",
      G.ELEMENTS == ("camera", "eclairage", "blocking", "cles") and G.TOUS[-1] == "maquette")
for etiquette, chemin in (("relatif", "outputs/scene.glb"), ("remontée", "C:/x/../Windows/scene.glb"),
                          ("saut de ligne", "C:/x/a\nimport os.glb"), ("autre suffixe", "C:/x/scene.py"),
                          ("vide", "")):
    check(f"G3 chemin de maquette refusé : {etiquette}",
          refuse(G.generer_script, dict(p, maquette={"glb": chemin})))
check("G3b maquette annoncée sans élément (ou l'inverse) : refus", refuse(G.generer_script, dict(p, maquette=None))
      and refuse(G.generer_script, dict(p, elements=["camera"])))
s_aller = G.generer_script(p)
l1, a1 = literal_et_arbre(s_aller)
l2, a2 = literal_et_arbre(G.generer_script(G.depuis_scene(dict(SCENE, keyframes=[]), ["camera", "maquette"],
                                                           glb="D:/autre/chemin/maquette.glb")))
check("G4 aller : un seul littéral, même arbre quel que soit le chemin ou la scène",
      a1 == a2 and json.loads(l1.value)["maquette"]["glb"] == GLB)
check("G5 aller : l'import passe par import_scene.gltf, les objets importés sont préfixés DZ_Maquette_ et rangés",
      "bpy.ops.import_scene.gltf(filepath=P[\"maquette\"][\"glb\"])" in s_aller
      and '"DZ_Maquette_" + o.name' in s_aller and 'retirer("DZ_Maquette_")' in s_aller)
BLEND = str(W / "outputs" / "copie.blend")
pr = G.retour(BLEND)
s_ret = G.generer_script_retour(pr)
lr1, ar1 = literal_et_arbre(s_ret)
lr2, ar2 = literal_et_arbre(G.generer_script_retour(G.retour(None, "Camera.001")))
check("G6 retour : un seul littéral, même arbre avec ou sans copie, quelle que soit la caméra",
      ar1 == ar2 and json.loads(lr1.value) == json.loads(json.dumps(pr)))
check("G7 retour : copie par save_as_mainfile(copy=True), jamais save_mainfile ni open",
      "save_as_mainfile(filepath=P[\"blend\"], copy=True" in s_ret and "save_mainfile(" not in s_ret.replace(
          "save_as_mainfile(", "") and "open_mainfile" not in s_ret)
for etiquette, mauvais in (("clé en trop", dict(pr, code="import os")), ("copie .py", dict(pr, blend="C:/x/a.py")),
                           ("bornes changées", dict(pr, max_objets=10 ** 6)),
                           ("caméra piégée", dict(pr, camera="x\"); import os #"))):
    check(f"G8 paramètres du retour re-vérifiés : {etiquette} refusé", refuse(G.generer_script_retour, mauvais))
VALIDEUR = pathlib.Path.home() / ".local" / "venvs" / "mcp-for-blender" / "Lib" / "site-packages" / "blender_mcp" / "safe_mode.py"
if VALIDEUR.is_file():
    spec = importlib.util.spec_from_file_location("_safe_mode_mcp", VALIDEUR)
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    res = [sm.is_safe(x) for x in (s_aller, s_ret)]
    check("G9 le VRAI validateur du mode sûr accepte l'aller avec maquette et le retour", all(r[0] for r in res), res)
else:
    print("  SKIP  G9 mcp-for-blender absent : validateur du mode sûr non lu")

check("G10 repère : Blender → glTF est l'inverse de glTF → Blender",
      G.depuis_blender(G.vers_blender([1.0, 2.0, 3.0])) == [1.0, 2.0, 3.0])
check("G11 champ vertical : capteur VERTICAL (24 mm, 32,97 mm → 40°)",
      abs(G.fov_vertical(G.focale_mm(40), 36, 24, "VERTICAL", 1920, 1080) - 40) < 1e-3)
f_h = math.degrees(2 * math.atan(18 / 50))
check("G12 champ vertical : AUTO paysage = largeur du capteur sur la largeur, ramenée à la hauteur",
      abs(G.fov_vertical(50, 36, 24, "AUTO", 1920, 1080)
          - math.degrees(2 * math.atan(math.tan(math.radians(f_h) / 2) * 1080 / 1920))) < 1e-6)
check("G13 champ vertical : AUTO portrait = largeur du capteur sur la HAUTEUR ; HORIZONTAL portrait = sur la largeur",
      abs(G.fov_vertical(50, 36, 24, "AUTO", 1080, 1920) - f_h) < 1e-6
      and G.fov_vertical(50, 36, 24, "HORIZONTAL", 1080, 1920) > f_h)


def blender_depuis_aller(params):
    """Ce que Blender relirait d'une caméra posée par l'aller : position, axe de visée, focale (capteur VERTICAL 24)."""
    def e(c, image=None):
        v = [c["cible"][i] - c["pos"][i] for i in range(3)]
        n = math.sqrt(sum(x * x for x in v))
        out = {"pos": c["pos"], "visee": [x / n for x in v], "lens": c["focale_mm"]}
        if image is not None:
            out["image"] = image
        return out
    cam = params["camera"]
    return {"dz": "retour", "cameras": [dict(e(cam), nom="DZ_Camera", type="PERSP", capteur_l=36.0,
                                             capteur_h=24.0, ajuste="VERTICAL", active=True,
                                             cles=[e(k, k["image"]) for k in params["cles"]])],
            "objets": [], "blend": True, "rendu": {"x": cam["largeur"], "y": cam["hauteur"], "fps": 24.0},
            "version": "5.2.0", "fichier": ""}


lu = G.lire_retour(blender_depuis_aller(p))
prop = G.vers_plateau(lu, SCENE)


def proches(a, b, tol=1e-3):
    return all(abs(x - y) < tol for x, y in zip(a, b))


k_ok = len(prop["keyframes"]) == 2 and all(
    proches(k["orbit"], o["orbit"]) and proches(k["target"], o["target"]) and abs(k["fov"] - o["fov"]) < 1e-3
    and abs(k["t"] - o["t"]) < 1e-9 and k["easing"] == o["easing"] for k, o in zip(prop["keyframes"], KFS))
check("G14 ALLER puis RETOUR : keyframes du Plateau à l'identique (orbite, cible, champ, temps, easing)", k_ok,
      prop["keyframes"])
check("G15 … et la caméra initiale = la première clé, écart nul, focale avant = après",
      proches(prop["camera"]["orbit"], KFS[0]["orbit"]) and prop["ecart_m"] < 1e-3
      and abs(prop["avant"]["focale_mm"] - prop["apres"]["focale_mm"]) < 1e-3, prop)
fixe = G.depuis_scene(dict(SCENE, keyframes=[]), ["camera"])
pf = G.vers_plateau(G.lire_retour(blender_depuis_aller(fixe)), dict(SCENE, keyframes=[]))
check("G16 caméra fixe : aucune keyframe, la caméra du Plateau revient",
      pf["keyframes"] == [] and proches(pf["camera"]["orbit"], SCENE["camera"]["orbit"])
      and proches(pf["camera"]["target"], SCENE["camera"]["target"]), pf)
br = blender_depuis_aller(p)
br["cameras"].append({"nom": "Cam\"; import os #", "type": "ORTHO", "capteur_l": 36, "capteur_h": 24, "ajuste": "AUTO",
                      "pos": [1, 1, 1], "visee": [0, 1, 0], "lens": 50, "cles": []})
br["objets"] = [{"nom": "DZ_Blocking_Marie\n#", "type": "EMPTY", "pos": [0, 0, 1], "rot": [0, 0, 0], "dims": [1, 1, 2],
                 "cle": "sujet"}, {"nom": "Cube", "type": "MESH", "pos": [0, 0, 0], "rot": [0, 0, 0], "dims": [2, 2, 2]}]
lu2 = G.lire_retour(br)
check("G17 relecture : noms NETTOYÉS (ni guillemet ni saut), objets hors DZ_ écartés, ortho repérée",
      lu2["cameras"][1]["nom"] == "Cam import os" and not lu2["cameras"][1]["perspective"]
      and [o["nom"] for o in lu2["objets"]] == ["DZ_Blocking_Marie"], (lu2["cameras"][1], lu2["objets"]))
check("G18 caméra choisie par son nom ; ortho jamais proposée ; inconnue refusée",
      G.vers_plateau(lu2, SCENE)["camera_nom"] == "DZ_Camera"
      and refuse(G.vers_plateau, lu2, SCENE, "Cam import os") and refuse(G.vers_plateau, lu2, SCENE, "Absente"))
for etiquette, mauvais in (("sans marque", {"cameras": []}),
                           ("NaN", dict(br, cameras=[dict(br["cameras"][0], pos=[float("nan"), 0, 0])])),
                           ("focale nulle", dict(br, cameras=[dict(br["cameras"][0], lens=0)])),
                           ("rendu absurde", dict(br, rendu={"x": 0, "y": 1080, "fps": 24})),
                           ("clé sans image", dict(br, cameras=[dict(br["cameras"][0], cles=[{"pos": [0, 0, 0],
                                                    "visee": [0, 1, 0], "lens": 50}])]))):
    check(f"G19 relecture refusée : {etiquette}", refuse(G.lire_retour, mauvais))

# ═══════════════════════════════════════ [R] routes ═══════════════════════════════════════
print("[R] les routes")
c = TestClient(_MAIN.app, client=("127.0.0.1", 50001))
c.__enter__()


def call(m, u, body=None, **kw):
    return c.request(m, "/api" + u, json=body, **kw)


ch = call("POST", "/chapters", {"title": "C", "script_text": "Marie entre.\n\nLa caisse tombe."}).json()
shots = call("POST", f"/chapters/{ch.get('id')}/storyboard/decoupe", {"method": "paragraph"}).json().get("shots", [])
s0 = shots[0]["id"]
r = call("POST", f"/blender/plan/{s0}/aller")
check("R1 aller sans scène au Plateau : 409", r.status_code == 409, r.text[:200])
sc = call("POST", "/scenes3d", {"shot_id": s0, "instances": INSTANCES, "keyframes": KFS}).json()
r = call("POST", f"/blender/plan/{s0}/aller", {"elements": ["eclairage"]})
check("R2 aller : aucun corps permis (400)", r.status_code == 400, r.text[:200])
vider()
r = call("POST", f"/blender/plan/{s0}/aller")
ex = appels("execute_blender_code")
pa = json.loads(literal_et_arbre(ex[0]["arguments"]["code"])[0].value) if ex else {}
maq = W / "outputs" / "blender" / "plans" / s0 / "maquette.glb"
check("R3 aller : caméra, clés et maquette en UN script ; la maquette composée sur disque (GLB)",
      r.status_code == 200 and len(ex) == 1 and pa.get("elements") == ["camera", "cles", "maquette"]
      and maq.is_file() and maq.read_bytes()[:4] == b"glTF" and pathlib.Path(pa["maquette"]["glb"]) == maq.resolve(),
      r.text[:300])
check("R3b la réponse compte les objets de la maquette et les clés", r.json().get("maquette") == 2
      and r.json().get("cles") == 2, r.json())
check("R3c le script est le gabarit (même arbre que G4)", literal_et_arbre(ex[0]["arguments"]["code"])[1] == a1)
from app.services import scene3d_glb as SG  # noqa: E402
noeuds = json.loads(maq.read_bytes()[20:20 + int.from_bytes(maq.read_bytes()[12:16], "little")])["nodes"]
check("R4 maquette : le faisceau n'y entre pas (deux nœuds, Marie et le cyprès)", len(noeuds) == 2, noeuds)
r = call("POST", f"/blender/plan/{s0}/envoyer", {"elements": ["maquette"]})
check("R5 la boîte t331 peut aussi envoyer la maquette seule", r.status_code == 200 and r.json()["maquette"] == 2,
      r.text[:200])

avant_sc = call("GET", f"/scenes3d/{sc['id']}").json()
vider()
r = call("POST", f"/blender/plan/{s0}/reprendre")
rt = r.json()
dos = W / "outputs" / "blender" / "plans" / s0 / rt.get("id", "x")
check("R6 reprendre : 200, copie .blend écrite PAR BLENDER au chemin du serveur, retour.json, vignette",
      r.status_code == 200 and (dos / rt["blend_nom"]).read_bytes()[:7] == b"BLENDER" and (dos / "retour.json").is_file()
      and (dos / "vignette.png").is_file(), r.text[:300])
pret = json.loads(literal_et_arbre(appels("execute_blender_code")[0]["arguments"]["code"])[0].value)
check("R6b le gabarit de retour vise la copie dans outputs/blender/plans/<plan>/<retour>/",
      pathlib.Path(pret["blend"]) == (dos / rt["blend_nom"]).resolve() and pret["elements"] == ["lire"], pret)
check("R6c look (vignette) et get_scene_info (licences) dans la même session, rien d'autre",
      [a["name"] for a in appels()] == ["execute_blender_code", "look", "get_scene_info"], [a["name"] for a in appels()])
prp = rt["proposition"]
check("R7 proposition : DZ_Camera, 2 keyframes (t = 0 et 2 s à 24 i/s), avant/après, rien écrit au Plateau",
      rt["camera_nom"] == "DZ_Camera" and [k["t"] for k in prp["keyframes"]] == [0.0, 2.0]
      and prp["avant"]["keyframes"] == 2 and prp["apres"]["focale_mm"] > 0
      and call("GET", f"/scenes3d/{sc['id']}").json()["camera"] == avant_sc["camera"]
      and call("GET", f"/scenes3d/{sc['id']}").json()["keyframes"] == avant_sc["keyframes"], rt)
check("R7b caméras et objets DZ_ relus, version et fichier de Blender", [x["nom"] for x in rt["cameras"]]
      == ["DZ_Camera", "Camera"] and [o["nom"] for o in rt["objets"]] == ["DZ_Camera", "DZ_Maquette_Marie"]
      and rt["version"] == "5.2.0" and rt["fichier"] == "atelier.blend", rt)
row = sqlite3.connect(str(W / "t.db")).execute(
    "select source, parent_filename, relation, recette from library_assets where filename=?",
    (rt["bibliotheque"] or "",)).fetchone()
rec = json.loads(row[3]) if row else {}
check("R8 Bibliothèque : la vignette (source « blender ») a le .blend pour MÈRE et la provenance en recette",
      row and row[0] == "blender" and row[1] == rt["blend_nom"] and row[2] == "blender"
      and rec.get("plan") == s0 and rec.get("scene") == sc["id"] and rec.get("blend") == rt["blend_nom"]
      and rec.get("blender") == "5.2.0" and rec.get("cameras") == ["DZ_Camera", "Camera"], row)
check("R8b la vignette est au magasin d'images", (W / "images" / rt["bibliotheque"]).is_file())
b = call("GET", rt["blend_url"].replace("/api", "", 1))
check("R9 le .blend est servi (nom du retour)", b.status_code == 200 and b.content[:7] == b"BLENDER"
      and rt["blend_nom"] in b.headers.get("content-disposition", ""), b.status_code)
check("R9b vignette servie ; identifiants piégés : 404", call("GET", rt["vignette_url"].replace("/api", "", 1))
      .status_code == 200 and all(call("GET", f"/blender/retour/{x}/blend").status_code == 404
                                  for x in ("x", "20261029-000000-ab_d", "20261029-000000-abcd")))
ls = call("GET", f"/blender/plan/{s0}/retours").json()["retours"]
check("R10 /retours : le retour sur la fiche du plan, sans la relecture brute", len(ls) == 1 and ls[0]["id"] == rt["id"]
      and "retour" not in ls[0], ls)

r = call("POST", f"/blender/plan/{s0}/retour/{rt['id']}/appliquer", {})
check("R11 appliquer SANS confirmer : avant/après, rien d'écrit", r.status_code == 200 and r.json()["applique"] is False
      and call("GET", f"/scenes3d/{sc['id']}").json()["keyframes"] == avant_sc["keyframes"], r.text[:300])
r = call("POST", f"/blender/plan/{s0}/retour/{rt['id']}/appliquer", {"camera": "Absente", "confirmer": True})
check("R12 caméra inconnue : 409, rien d'écrit", r.status_code == 409
      and call("GET", f"/scenes3d/{sc['id']}").json()["keyframes"] == avant_sc["keyframes"], r.text[:200])
r = call("POST", f"/blender/plan/{s0}/retour/{rt['id']}/appliquer", {"confirmer": True})
apres_sc = call("GET", f"/scenes3d/{sc['id']}").json()
check("R13 appliquer avec confirmer : caméra et keyframes de Blender au Plateau (2 clés, 0 et 2 s)",
      r.status_code == 200 and r.json()["applique"] and [k["t"] for k in apres_sc["keyframes"]] == [0.0, 2.0]
      and apres_sc["camera"] == r.json()["proposition"]["camera"]
      and abs(apres_sc["keyframes"][1]["fov"] - G.fov_vertical(35, 36, 24, "VERTICAL", 1920, 1080)) < 1e-3, apres_sc)
r = call("POST", f"/blender/plan/{s0}/retour/{rt['id']}/appliquer", {"camera": "Camera", "confirmer": True})
check("R14 une autre caméra au choix (fixe) : keyframes vidées, avant/après le disait", r.status_code == 200
      and r.json()["proposition"]["apres"]["keyframes"] == 0
      and call("GET", f"/scenes3d/{sc['id']}").json()["keyframes"] == [], r.text[:300])
r = call("POST", f"/blender/plan/{s0}/retour/{rt['id']}/appliquer", {"code": "x"})
check("R15 appliquer : champ inconnu 400", r.status_code == 400, r.text[:200])

FAUX_ENV["FAUX_SANS_BLEND"] = "1"
n_avant = len(list((W / "outputs" / "blender" / "plans" / s0).iterdir()))
r = call("POST", f"/blender/plan/{s0}/reprendre")
check("R16 Blender n'a pas écrit la copie : 502 dit, dossier du retour retiré",
      r.status_code == 502 and ".blend" in r.text
      and len(list((W / "outputs" / "blender" / "plans" / s0).iterdir())) == n_avant, r.text[:200])
del FAUX_ENV["FAUX_SANS_BLEND"]
FAUX_ENV["FAUX_MODE"] = "ferme"
r = call("POST", f"/blender/plan/{s0}/reprendre")
check("R17 Blender fermé : 503, dossier retiré", r.status_code == 503
      and len(list((W / "outputs" / "blender" / "plans" / s0).iterdir())) == n_avant, r.text[:200])
FAUX_ENV["FAUX_MODE"] = "ok"
FAUX_ENV["FAUX_RETOUR"] = json.dumps({"dz": "retour", "cameras": "pas une liste"})
r = call("POST", f"/blender/plan/{s0}/reprendre")
check("R18 réponse de Blender illisible : 502, dossier retiré", r.status_code == 502
      and len(list((W / "outputs" / "blender" / "plans" / s0).iterdir())) == n_avant, r.text[:200])
del FAUX_ENV["FAUX_RETOUR"]
r = call("POST", f"/blender/plan/{s0}/reprendre", {"code": "import os"})
check("R19 reprendre : seul `camera` est permis (400)", r.status_code == 400, r.text[:200])
import _jeton_appareil as _JA  # noqa: E402
with TestClient(_MAIN.app, client=("192.168.1.20", 50000), headers=_JA.entetes(_MAIN.app)) as lan:
    check("R20 le compagnon appairé : ni aller, ni reprendre, ni retours, ni .blend (403)",
          lan.post(f"/api/blender/plan/{s0}/aller").status_code == 403
          and lan.post(f"/api/blender/plan/{s0}/reprendre").status_code == 403
          and lan.get(f"/api/blender/plan/{s0}/retours").status_code == 403
          and lan.get(f"/api/blender/retour/{rt['id']}/blend").status_code == 403)

# ═══════════════════════════════════════ [A] agent ═══════════════════════════════════════
print("[A] l'outil d'agent")
check("A1 blender_retour : lecture, dans la boîte « blender », registre sain",
      "blender_retour" in B.BOITES["blender"]["outils"] and ao.OUTILS["blender_retour"]["nature"] == "lecture"
      and B.verifier() == [])
vider()
ctx = ao.Ctx(cid="banc", agent="mcp")
r = loop.run_until_complete(ao.blender_retour(ctx, s0))
check("A2 blender_retour : le dernier retour, sans appeler Blender", r["ok"] and r["donnees"]["id"] == rt["id"]
      and r["donnees"]["camera"] == "DZ_Camera" and appels() == [], r)
r = loop.run_until_complete(ao.blender_retour(ctx, shots[1]["id"] if len(shots) > 1 else "autre"))
check("A3 plan sans retour : le dit", r["ok"] and r["donnees"]["retours"] == 0, r)
try:
    loop.run_until_complete(ao.blender_retour(ctx, "../x"))
    check("A4 plan piégé : refus", False)
except Exception as e:  # noqa: BLE001
    check("A4 plan piégé : refus", "plan" in str(e), e)
c.__exit__(None, None, None)

# ═══════════════════════════════════════ [H] vrai Blender headless ═══════════════════════════════════════
if os.environ.get("BLENDER_REEL") == "1":
    print("[H] aller puis retour dans un vrai Blender HEADLESS (fichier vierge)")
    from app.services import passes_blender as PB
    e = PB.etat_blender(True)
    if not e.get("dispo"):
        print("  SKIP  [H] Blender headless introuvable")
    else:
        D = W / "headless"
        D.mkdir()
        glb, _ = SG.composer([i for i in INSTANCES if i["role"] != "faisceau"], lambda i: None)
        (D / "scene.glb").write_bytes(glb)
        (D / "aller.py").write_text(G.generer_script(G.depuis_scene(SCENE, ["camera", "cles", "maquette"],
                                                                     glb=str(D / "scene.glb"))), encoding="utf-8")
        (D / "retour.py").write_text(G.generer_script_retour(G.retour(str(D / "copie.blend"))), encoding="utf-8")
        (D / "pilote.py").write_text(
            "import bpy\nbpy.ops.wm.read_factory_settings(use_empty=True)\n"
            f"exec(open(r'{D / 'aller.py'}', encoding='utf-8').read(), {{'__name__': 'a'}})\n"
            f"exec(open(r'{D / 'retour.py'}', encoding='utf-8').read(), {{'__name__': 'r'}})\n", encoding="utf-8")
        rr = subprocess.run([e["exe"], "-b", "--factory-startup", "--python", str(D / "pilote.py")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        res = [G.lire_resume(l) for l in (rr.stdout or "").splitlines() if "DZBLENDER" in l]
        check("H1 aller : DZ_Camera et la maquette importée (deux objets DZ_Maquette_)", len(res) == 2
              and sum(1 for n in res[0].get("crees", []) if n.startswith("DZ_Maquette_")) == 2, (res, rr.stderr[-600:]))
        luh = G.lire_retour(res[-1]) if len(res) == 2 else None
        check("H2 retour : copie .blend écrite, deux clés lues sur DZ_Camera", luh and luh["blend"]
              and (D / "copie.blend").is_file() and len(luh["cameras"][0]["cles"]) == 2, luh)
        ph = G.vers_plateau(luh, SCENE) if luh else {"keyframes": []}
        check("H3 vrai Blender : ALLER puis RETOUR rend les keyframes du Plateau (au 1/100 près : Blender arrondit à 1e-4)",
              len(ph["keyframes"]) == 2 and all(proches(k["orbit"], o["orbit"], 1e-2)
                                                and proches(k["target"], o["target"], 1e-2) and abs(k["fov"] - o["fov"]) < 1e-2
                                                for k, o in zip(ph["keyframes"], KFS)), ph["keyframes"])
else:
    print("  SKIP  [H] vrai Blender headless (BLENDER_REEL=1 pour le lancer)")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
