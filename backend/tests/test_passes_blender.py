# -*- coding: utf-8 -*-
"""t334 (A4 du lot Scenario, 29/10/2026) — les PASSES HEADLESS d'un plan par Blender (services/passes_blender.py,
routes /api/passes).

  [V] trouver Blender : BLENDER_PATH puis Program Files (le plus récent) ; trop ancien (< 4.2) et absent dits ;
  [P] PUR : version lue, résolution paire, repère glTF → Blender, états de caméra (image fixe = 1er keyframe ;
      séquence bornée à 12 i/s et 48 images), cadrage, plage de profondeur, couleurs (palette t333 si présente,
      sinon stables par nom ; faisceaux exclus), hex → RVB brut / linéaire, lecture des lignes « DZPASSE » ;
  [G] le SCRIPT : gabarit fixe, un seul littéral (le JSON), même arbre syntaxique quelle que soit la scène (un nom
      d'instance piégé reste une donnée), paramètres re-vérifiés (non fini, chemin relatif, passe inconnue refusés) ;
  [R] les routes avec un FAUX Blender : 404 plan, 409 sans scène, 400 passes inconnues, 503 Blender absent (dit quoi
      installer), 202 → progression → fini, manifeste, fichiers servis (noms validés), Bibliothèque « passe »,
      vignettes du chapitre, 409 une passe déjà en cours, annulation (Blender tué, rien gardé), échec dit ;
  [D] la revue du plan (t337) branchée : contours de la passe de profondeur contre les bords du rendu ;
  [A] l'outil d'agent lire_passes_plan (boîte « chapitres », lecture) ;
  [B] un VRAI rendu Blender court (une image par passe) quand Blender est installé — sinon sauté, et dit.
AUCUN appel réseau. Run (depuis backend/) : & $PY tests/test_passes_blender.py"""
import ast
import asyncio
import io
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

_tmp = tempfile.mkdtemp(prefix="dzpasses334_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
for _k in ("FAL_KEY", "ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
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


import httpx  # noqa: E402

RESEAU = {"n": 0}


def _post_interdit(*a, **k):
    RESEAU["n"] += 1
    raise RuntimeError("GARDE RESEAU : httpx.post appelé dans un banc")


httpx.post = _post_interdit

from httpx import AsyncClient, ASGITransport  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.main import app  # noqa: E402
import app.main as _MAIN  # noqa: E402
from app.services import passes_blender as PB, revue_plan as RV, scene3d as S  # noqa: E402
from app.services import agent_outils as ao, agent_boites as B  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

W = pathlib.Path(_tmp)
IMG = W / "images"
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())
VRAIES = {"racines": PB._racines, "version": PB._sortie_version, "popen": PB._popen}

INSTANCES = [
    {"id": "sujet", "nom": "Marie", "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4],
     "role": "sujet", "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1}},
    {"id": "arbre", "nom": "cyprès", "source": {"kind": "proxy", "forme": "cylindre"}, "dims": [0.6, 3, 0.6],
     "role": "decor", "transform": {"pos": [1.5, 0, -2], "rot": [0, 0, 0], "scale": 1}},
    {"id": "caisse", "nom": "caisse", "source": {"kind": "proxy", "forme": "boite"}, "dims": [1, 1, 1],
     "role": "decor", "transform": {"pos": [-1.5, 0, -1], "rot": [0, 30, 0], "scale": 1}},
]
KFS = [{"t": 0, "orbit": [20, 85, 6], "target": [0, 0.9, 0], "fov": 40, "easing": "linear"},
       {"t": 1.5, "orbit": [-10, 80, 4], "target": [0, 0.9, 0], "fov": 40, "easing": "linear"}]
SCENE = {"aspect": "16:9", "instances": INSTANCES, "camera": {"orbit": [20, 85, 6], "target": [0, 0.9, 0], "fov": 40},
         "keyframes": KFS}

# ═══════════════════════════════════════ [V] trouver Blender ═══════════════════════════════════════
print("[V] trouver Blender")
FAUX = W / "faux_blender"
FAUX.mkdir()
EXES = {}
for nom, v in (("b33", "Blender 3.3.21"), ("b50", "Blender 5.0.1"), ("b52", "Blender 5.2.2 LTS (hash d13f)"),
               ("muet", "rien de lisible")):
    p = FAUX / nom / "blender.exe"
    p.parent.mkdir()
    p.write_bytes(b"MZ")
    EXES[str(p)] = v
PB._sortie_version = lambda exe: EXES[str(exe)]


def racines(*noms):
    return lambda: [FAUX / n / "blender.exe" for n in noms]


PB._racines = racines("absent", "b52", "b50")
e = PB.etat_blender(rafraichir=True)
check("V1 le premier candidat qui EXISTE et dit sa version l'emporte (5.2.2)",
      e["dispo"] and e["version"] == "5.2.2" and pathlib.Path(e["exe"]).parent.name == "b52", e)
PB._racines = racines("muet", "b33")
e = PB.etat_blender(rafraichir=True)
check("V2 seul un Blender 3.3 : refusé, « trop_ancien » (4.2 au moins)",
      not e["dispo"] and e["raison"] == "trop_ancien" and e["version"] == "3.3.21", e)
PB._racines = racines("absent")
e = PB.etat_blender(rafraichir=True)
check("V3 rien : « absent »", e == {"dispo": False, "exe": None, "version": None, "raison": "absent"}, e)
os.environ["BLENDER_PATH"] = str(FAUX / "b50" / "blender.exe")
r = VRAIES["racines"]()
check("V4 BLENDER_PATH passe en tête des candidats (avant Program Files et le PATH)",
      r and r[0] == FAUX / "b50" / "blender.exe", r[:2])
del os.environ["BLENDER_PATH"]

# ═══════════════════════════════════════ [P] PUR ═══════════════════════════════════════
print("[P] calculs purs")
check("P1 version lue : « Blender 5.2.2 LTS » → (5, 2, 2) ; « Blender 4.2 » → (4, 2, 0) ; illisible → None",
      PB.lire_version("Blender 5.2.2 LTS\n\tbuild") == (5, 2, 2) and PB.lire_version("Blender 4.2") == (4, 2, 0)
      and PB.lire_version("rien") is None)
check("P2 résolution : 16:9 → 960×540, 9:16 → 540×960, 2.39:1 → 960×402 (pair), format inconnu refusé",
      PB.resolution("16:9", 960) == (960, 540) and PB.resolution("9:16", 960) == (540, 960)
      and PB.resolution("2.39:1", 960) == (960, 402))
try:
    PB.resolution("4:3", 960)
    check("P2b format inconnu refusé", False)
except PB.PasseRefusee:
    check("P2b format inconnu refusé", True)
check("P3 repère : glTF (x, y, z) → Blender (x, −z, y), comme l'importeur", PB.vers_blender([1, 2, 3]) == [1, -3, 2])
et = PB.etats_camera(SCENE, sequence=False)
check("P4 image fixe = le PREMIER keyframe (le début du plan, comme la capture du Plateau)",
      len(et) == 1 and et[0]["t"] == 0 and et[0]["orbit"] == [20, 85, 6], et)
et = PB.etats_camera(SCENE, sequence=True)
check("P5 séquence : 12 i/s du premier au dernier keyframe (1,5 s → 19 images), bornes exactes",
      len(et) == 19 and et[0]["orbit"] == [20, 85, 6] and abs(et[-1]["t"] - 1.5) < 1e-9
      and [round(x, 6) for x in et[-1]["orbit"]] == [-10, 80, 4], (len(et), et[-1]))
longue = dict(SCENE, keyframes=[dict(KFS[0]), dict(KFS[1], t=30)])
check("P6 une caméra de 30 s est BORNÉE à 48 images", len(PB.etats_camera(longue, sequence=True)) == PB.SEQ_MAX_IMAGES)
fixe = dict(SCENE, keyframes=[KFS[0]])
check("P7 un seul keyframe : pas de séquence même demandée ; sans keyframe : la caméra de la scène",
      len(PB.etats_camera(fixe, True)) == 1 and PB.etats_camera(dict(SCENE, keyframes=[]), True)[0]["orbit"] == [20, 85, 6])
c = PB.cadrage_blender({"orbit": [0, 90, 6], "target": [0, 1, 0], "fov": 40})
check("P8 cadrage : orbite [0°, 90°, 6 m] autour de (0, 1, 0) → caméra en Blender (0, −6, 1) visant (0, 0, 1), 40°",
      [round(v, 6) for v in c["pos"]] == [0, -6, 1] and c["cible"] == [0, 0, 1] and c["fov_v"] == 40, c)
proche, loin = PB.plage_profondeur(INSTANCES, PB.etats_camera(SCENE, False), "16:9")
zs = [p[2] for i in INSTANCES for p in S.projeter(S.coins(i), PB.etats_camera(SCENE, False)[0], 16 / 9)]
check("P9 plage de profondeur : [0,9 × plus proche coin, 1,5 × plus lointain]",
      abs(proche - min(zs) * 0.9) < 1e-4 and abs(loin - max(zs) * 1.5) < 1e-4, (proche, loin, min(zs), max(zs)))
cols, origine, exclus = PB.couleurs(INSTANCES + [{"id": "rayon", "nom": "faisceau du phare", "role": "faisceau",
                                                  "source": {"kind": "proxy", "forme": "cylindre"}, "dims": [1, 1, 1]}])
check("P10 couleurs : une par solide, hex valides, le faisceau EXCLU ; origine dite (palette t333 ou stable)",
      set(cols) == {"sujet", "arbre", "caisse"} and "rayon" in exclus and origine in ("palette", "stable")
      and all(PB._HEX.match(v) for v in cols.values()), (cols, origine, exclus))
check("P11 couleurs STABLES par nom (crc32, pas hash() salé) : deux appels, deux processus, la même teinte",
      PB._hex_stable("cyprès") == PB._STABLES[__import__("zlib").crc32("cyprès".encode()) % len(PB._STABLES)]
      and PB._hex_stable("Marie") != PB._hex_stable("cyprès"), PB._hex_stable("cyprès"))
check("P12 hex → RVB BRUT (la valeur du PNG en « Raw ») et → linéaire (base color)",
      PB.hex_rgb("#ff8000") == [1.0, round(128 / 255, 6), 0.0] and PB.lineaire("#ffffff") == [1.0, 1.0, 1.0]
      and abs(PB.lineaire("#808080")[0] - 0.215861) < 1e-5)
L = PB.lire_ligne
check("P13 lignes DZPASSE : image / fin / erreur lues ; bavardage, passe inconnue, nombres faux ignorés",
      L("DZPASSE image 3 10 profondeur 2\r\n") == {"type": "image", "k": 3, "n": 10, "passe": "profondeur", "i": 2}
      and L("DZPASSE fin") == {"type": "fin"} and L("DZPASSE erreur boum: x") == {"type": "erreur", "msg": "boum: x"}
      and L("Fra:1 Mem:12M") is None and L("DZPASSE image 3 10 rayons 2") is None
      and L("DZPASSE image 11 10 clay 0") is None and L("DZPASSE image a b clay 0") is None)

# ═══════════════════════════════════════ [G] le script ═══════════════════════════════════════
print("[G] le script généré")
D = W / "gen"
D.mkdir()
par = PB.parametres(SCENE, glb=str(D / "scene.glb"), sortie=str(D))
script = PB.generer_script(par)
arbre = ast.parse(script)


def appel_params(a):
    """Le littéral passé à json.loads dans `P = json.loads(…)`."""
    for n in ast.walk(a):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "P":
            return n.value.args[0]
    return None


lit = appel_params(arbre)
check("G1 le script se lit (ast) et P = json.loads(<UN littéral>) rend exactement les paramètres",
      isinstance(lit, ast.Constant) and json.loads(lit.value) == json.loads(json.dumps(par)), type(lit))


def squelette(src):
    a = ast.parse(src)
    for n in ast.walk(a):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("{"):
            n.value = "<PARAMS>"
    return ast.dump(a)


PIEGE = 'x"); import os; os.system("calc") #\'\'\'\n__import__("shutil").rmtree("C:/")'
piegee = [dict(INSTANCES[0], id=PIEGE[:40], nom=PIEGE)] + INSTANCES[1:]
s2 = PB.generer_script(PB.parametres(dict(SCENE, instances=piegee), glb=str(D / "scene.glb"), sortie=str(D)))
check("G2 un nom d'instance PIÉGÉ ne change pas l'arbre du script : il reste dans le JSON (une donnée)",
      squelette(s2) == squelette(script) and "os.system" not in s2.replace(repr(json.dumps(
          json.loads(appel_params(ast.parse(s2)).value), ensure_ascii=True, sort_keys=True)), ""), "arbre différent")
check("G3 le gabarit n'a qu'UN trou, rempli une fois ; JSON ASCII (aucun caractère hors ASCII dans le littéral)",
      PB.GABARIT.count("__PARAMS__") == 1 and "__PARAMS__" not in script and lit.value.isascii())
refus = []
for k, v in (("proche", float("inf")), ("glb", "scene.glb"), ("passes", ["clay", "rayons"]), ("largeur", 99999),
             ("largeur", True), ("masques", {"a": ["x", 1, 2]})):
    bad = dict(par, **{k: v})
    try:
        PB.generer_script(bad)
        refus.append((k, "accepté"))
    except PB.PasseRefusee:
        pass
check("G4 paramètres re-vérifiés : infini, chemin relatif, passe inconnue, résolution, booléen, texte → refusés",
      not refus, refus)
try:
    PB.parametres(SCENE, glb=str(D / "s.glb"), sortie=str(D), passes=["clay", "import os"])
    check("G5 une passe hors de la liste fermée est refusée dès parametres", False)
except PB.PasseRefusee:
    check("G5 une passe hors de la liste fermée est refusée dès parametres", True)
p3 = PB.parametres(SCENE, glb=str(D / "s.glb"), sortie=str(D), passes=["masques", "clay"], sequence=True)
check("G6 passes choisies dans l'ORDRE canonique ; séquence 640 px, fps 12 ; masques en RVB brut",
      p3["passes"] == ["clay", "masques"] and p3["largeur"] == 640 and p3["hauteur"] == 360 and p3["fps"] == 12
      and len(p3["cameras"]) == 19 and p3["masques"]["sujet"] == PB.hex_rgb(p3["couleurs"]["sujet"]))
a = PB.argv("C:/B/blender.exe", D / "x.py")
check("G7 la ligne de commande : -b, --factory-startup (aucun add-on de l'utilisateur), code de sortie sur exception",
      a[:4] == ["C:/B/blender.exe", "-b", "--factory-startup", "-noaudio"] and a[a.index("--python-exit-code") + 1] == "3"
      and a[-2:] == ["--python", str(D / "x.py")])

# ═══════════════════════════════════════ [R] les routes (faux Blender) ═══════════════════════════════════════
print("[R] les routes, faux Blender")


def sql(q, *a):
    con = sqlite3.connect(str(W / "t.db"))
    try:
        r = con.execute(q, a)
        con.commit()
        return r.fetchall()
    finally:
        con.close()


async def _req(meth, path, body=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient", timeout=300) as cl:
        if meth == "GET":
            return await cl.get("/api" + path)
        return await cl.post("/api" + path, json=body)


def call(meth, path, body=None):
    return loop.run_until_complete(_req(meth, path, body))


def js(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


class FauxBlender:
    """Lit le script reçu, écrit les PNG attendus et parle comme le vrai (lignes DZPASSE). mode : ok | bloque |
    echec. Le kill() réveille un faux bloqué."""
    mode = "ok"
    lances = []

    def __init__(self, args, cwd):
        FauxBlender.lances.append(args)
        self.returncode = None
        self.tue = threading.Event()
        src = pathlib.Path(args[-1]).read_text("utf-8")
        P = json.loads(appel_params(ast.parse(src)).value)
        lignes = []
        if self.mode == "echec":
            lignes = [b"Error: boum\n", b"DZPASSE erreur boum dans le gabarit\n"]
            self.code = 3
        else:
            n, k = len(P["passes"]) * len(P["cameras"]), 0
            for passe in P["passes"]:
                for i in range(len(P["cameras"])):
                    mode = "I;16" if passe == "profondeur" else "RGB"
                    Image.new(mode, (P["largeur"], P["hauteur"])).save(pathlib.Path(P["sortie"]) / f"{passe}_{i:03d}.png")
                    k += 1
                    lignes.append(f"Fra:1 Mem:1M | Rendu\nDZPASSE image {k} {n} {passe} {i}\n".encode())
            lignes.append(b"DZPASSE fin\n")
            self.code = 0
        self.stdout = self
        self._lignes = b"".join(lignes).splitlines(keepends=True)

    def readline(self):
        if self._lignes:
            return self._lignes.pop(0)
        if self.mode == "bloque":
            self.tue.wait(20)
            self.code = -9
        return b""

    def wait(self, timeout=None):
        self.returncode = self.code
        return self.code

    def kill(self):
        self.tue.set()


PB._popen = lambda args, cwd: FauxBlender(args, cwd)
PB._racines = racines("b52")
PB._CACHE.clear()


def attendre_job(jid, n=400):
    for _ in range(n):
        j = js(call("GET", f"/passes/job/{jid}"))
        if j.get("statut") in ("fini", "erreur", "annule"):
            return j
        loop.run_until_complete(asyncio.sleep(0.02))
    return j


ch = js(call("POST", "/chapters", {"title": "C", "script_text": "Marie entre.\n\nLa caisse tombe."}))
shots = js(call("POST", f"/chapters/{ch.get('id')}/storyboard/decoupe", {"method": "paragraph"})).get("shots", [])
s0, s1 = shots[0]["id"], shots[1]["id"]
r = call("POST", "/passes/plan/inconnu", {})
check("R1 plan inconnu : 404", r.status_code == 404, r.text[:200])
r = call("POST", f"/passes/plan/{s0}", {})
check("R2 plan sans scène au Plateau : 409, dit d'ouvrir le Plateau", r.status_code == 409 and "Plateau" in r.text, r.text[:300])
sc = js(call("POST", "/scenes3d", {"shot_id": s0, "instances": INSTANCES, "keyframes": KFS}))
check("R3 la scène du plan créée au Plateau", sc.get("shot_id") == s0, sc)
r = call("POST", f"/passes/plan/{s0}", {"passes": ["clay", "rayons-x"]})
check("R4 passe inconnue : 400, la liste dite", r.status_code == 400 and "profondeur" in r.text, r.text[:300])
PB._racines = racines("absent")
PB._CACHE.clear()
r = call("POST", f"/passes/plan/{s0}", {})
check("R5 Blender absent : 503 qui dit QUOI installer (4.2, blender.org, BLENDER_PATH), rien lancé",
      r.status_code == 503 and "4.2" in r.text and "blender.org" in r.text and "BLENDER_PATH" in r.text
      and not FauxBlender.lances, r.text[:400])
g = js(call("GET", f"/passes/plan/{s0}"))
check("R6 GET du plan : Blender absent dit (installer), scène animée vue (2 keyframes, 1,5 s), aucun run",
      g["blender"]["dispo"] is False and "blender.org" in g["blender"]["installer"] and g["scene"]["anime"] is True
      and g["scene"]["duree_s"] == 1.5 and g["runs"] == [] and g["job"] is None, g)
PB._racines = racines("b52")
PB._CACHE.clear()
r = call("POST", f"/passes/plan/{s0}", {})
jid = js(r).get("job", {}).get("id")
check("R7 lancement : 202, un job, 5 passes × 1 image (image fixe par défaut), la version de Blender",
      r.status_code == 202 and jid and js(r)["images"] == 1 and js(r)["passes"] == list(PB.PASSES)
      and js(r)["blender"] == "5.2.2", r.text[:300])
j = attendre_job(jid)
check("R8 le job finit « fini » à 100 %, 5 images sur 5", j.get("statut") == "fini" and j.get("progression") == 100
      and j.get("images") == 5 and j.get("total") == 5, j)
g = js(call("GET", f"/passes/plan/{s0}"))
run = (g.get("runs") or [{}])[0]
check("R9 le manifeste : run, scène, 5 passes, profondeur (plage en m, blanc = proche, 16 bits), normales caméra, "
      "couleurs, image fixe 960×540",
      run.get("scene_id") == sc["id"] and sorted(run.get("passes", {})) == sorted(PB.PASSES)
      and run["profondeur"]["convention"] == "blanc_proche" and run["profondeur"]["bits"] == 16
      and run["profondeur"]["proche_m"] < run["profondeur"]["loin_m"] and run["normales"]["espace"] == "camera"
      and set(run["couleurs"]) == {"sujet", "arbre", "caisse"} and run["sequence"] is False
      and (run["largeur"], run["hauteur"]) == (960, 540), run)
lance = FauxBlender.lances[-1]
check("R10 Blender lancé en arrière-plan sur un script du DOSSIER DU RUN, le GLB de la scène composé à côté",
      lance[1] == "-b" and pathlib.Path(lance[-1]).name == "passes_blender.py"
      and (pathlib.Path(lance[-1]).parent / "scene.glb").is_file(), lance)
nom_b = run["passes"]["profondeur"]["bibliotheque"]
lib = sql("SELECT source, relation FROM library_assets WHERE filename=?", nom_b)
check("R11 Bibliothèque : chaque passe rangée (passe_<plan>_<run>_<passe>.png), provenance « passe »",
      (IMG / nom_b).is_file() and lib and lib[0][0] == "passe" and lib[0][1] == "passe"
      and nom_b.startswith("passe_") and nom_b.endswith("_profondeur.png"), (nom_b, lib))
from app.services import library_index as LI  # noqa: E402
check("R12 la source « passe » est connue (libellé, préfixe, licence propre)",
      LI.SOURCES.get("passe") == "Passes Blender" and LI.heuristique("passe_abc_x_clay.png") == "passe"
      and LI.licence_defaut("passe_x.png", "passe") == LI.LICENCE_PROPRE)
f = call("GET", f"/passes/fichier/{s0}/{run['run']}/{run['passes']['clay']['fichiers'][0]}")
check("R13 le fichier d'une passe est servi (PNG)", f.status_code == 200 and f.headers["content-type"] == "image/png"
      and f.content[:4] == b"\x89PNG", f.status_code)
mauvais = [call("GET", f"/passes/fichier/{s0}/{run['run']}/{n}").status_code
           for n in ("passes_blender.py", "scene.glb", "passes.json", "clay_000.png.py", "clay_1.png")]
# une remontée encodée (%2F) ne trouve aucune route /api/passes : la page de la SPA répond, jamais le fichier
rem = [call("GET", u) for u in (f"/passes/fichier/{s0}/{run['run']}/..%2Fpasses.json",
                                f"/passes/fichier/{s0}/..%2F..%2Fx/clay_000.png")]
check("R14 noms validés : script, GLB, manifeste, nom hors gabarit → 404 ; remontées → jamais le fichier",
      all(c == 404 for c in mauvais) and all(x.status_code == 404 or x.headers["content-type"].startswith("text/html")
                                              for x in rem), (mauvais, [x.headers.get("content-type") for x in rem]))
v = js(call("GET", f"/passes/chapitre/{ch['id']}"))
check("R15 vignettes du chapitre : le dernier run du plan 1, rien pour le plan 2",
      (v.get("plans") or {}).get(s0, {}).get("run") == run["run"] and s1 not in v["plans"], v)
# séquence
r = call("POST", f"/passes/plan/{s0}", {"sequence": True, "passes": ["masques", "profondeur"]})
j = attendre_job(js(r)["job"]["id"])
g = js(call("GET", f"/passes/plan/{s0}"))
run2 = g["runs"][0]
check("R16 séquence : 19 images × 2 passes, fps 12, un run de plus (le plus récent d'abord)",
      j.get("statut") == "fini" and j.get("total") == 38 and run2["sequence"] is True and run2["images"] == 19
      and run2["fps"] == 12 and sorted(run2["passes"]) == ["masques", "profondeur"] and len(g["runs"]) == 2
      and len(run2["passes"]["masques"]["fichiers"]) == 19, (j, run2.get("images")))
# déjà en cours / annulation
FauxBlender.mode = "bloque"
r = call("POST", f"/passes/plan/{s0}", {"passes": ["clay"]})
jb = js(r)["job"]["id"]
for _ in range(100):
    if js(call("GET", f"/passes/job/{jb}")).get("statut") == "rendu":
        break
    loop.run_until_complete(asyncio.sleep(0.02))
r2 = call("POST", f"/passes/plan/{s1}", {})
sc1 = js(call("POST", "/scenes3d", {"shot_id": s1, "instances": INSTANCES}))
r2 = call("POST", f"/passes/plan/{s1}", {})
check("R17 une passe tourne déjà : 409 (une seule à la fois sur ce PC)", r2.status_code == 409 and "déjà" in r2.text, r2.text[:200])
a = js(call("POST", f"/passes/job/{jb}/annuler"))
j = attendre_job(jb)
check("R18 annuler : Blender TUÉ, job « annule », le dossier du run retiré (rien de rangé)",
      a.get("annule") is True and j.get("statut") == "annule"
      and not (PB.dossier_plan(W / "outputs", s0) / j["run"]).exists()
      and len(js(call("GET", f"/passes/plan/{s0}"))["runs"]) == 2, (a, j))
FauxBlender.mode = "echec"
r = call("POST", f"/passes/plan/{s1}", {})
j = attendre_job(js(r)["job"]["id"])
check("R19 Blender échoue : job « erreur » avec SA raison (ligne DZPASSE erreur), rien rangé",
      j.get("statut") == "erreur" and "boum dans le gabarit" in (j.get("erreur") or "") and "code 3" in j["erreur"]
      and js(call("GET", f"/passes/plan/{s1}"))["runs"] == [], j)
g = js(call("GET", f"/passes/plan/{s1}"))
check("R20 le GET du plan rend le DERNIER job (son erreur reste lisible après rechargement)",
      (g.get("job") or {}).get("statut") == "erreur", g.get("job"))
check("R21 job inconnu : 404 ; annuler un job fini : rien", call("GET", "/passes/job/pb_x").status_code == 404
      and js(call("POST", f"/passes/job/{jid}/annuler")).get("annule") is False)
FauxBlender.mode = "ok"

# ═══════════════════════════════════════ [D] la revue du plan ═══════════════════════════════════════
print("[D] la revue du plan : profondeur contre rendu")


def silhouette(w, h, boites, fond=0, val=255, mode="L"):
    im = Image.new(mode, (w, h), fond)
    d = ImageDraw.Draw(im)
    for b in boites:
        d.rectangle(b, fill=val)
    return im


prof = silhouette(320, 180, [(40, 40, 120, 170), (200, 20, 240, 170)], val=200)
meme = silhouette(320, 180, [(40, 40, 120, 170), (200, 20, 240, 170)], fond=90, val=30).convert("RGB")
autre = silhouette(320, 180, [(150, 10, 310, 60)], fond=200, val=20).convert("RGB")
m1, m2 = RV.profondeur_contre_rendu(prof, meme), RV.profondeur_contre_rendu(prof, autre)
check("D1 contours de profondeur contre un rendu au MÊME relief (look inversé) : « proche »",
      m1["verdict"] == "proche" and m1["concordance"] > 0.6, m1)
check("D2 contre un autre relief : « ecart », concordance nettement plus basse",
      m2["verdict"] == "ecart" and m2["concordance"] < m1["concordance"] - 0.3, m2)
p16 = Image.new("I;16", (320, 180), 0)
p16.paste(65535, (40, 40, 120, 170))
check("D3 une passe 16 bits se lit (ramenée à 8 bits), une passe vide est « inconnu »",
      RV.profondeur_contre_rendu(p16, meme)["concordance"] is not None
      and RV.profondeur_contre_rendu(Image.new("L", (64, 64)), meme)["verdict"] == "inconnu")
pp = PB.profondeur_du_plan(W / "outputs", s0)
check("D4 profondeur_du_plan : la passe de profondeur la plus récente du plan (run, plage, instant t)",
      pp and pp["run"] == run2["run"] and pathlib.Path(pp["chemin"]).is_file() and pp["t"] == 0
      and pp["proche_m"] == run2["profondeur"]["proche_m"] and PB.profondeur_du_plan(W / "outputs", s1) is None, pp)
if shutil.which("ffmpeg"):
    CL = W / "clips"
    CL.mkdir()
    meme.save(CL / "f.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(CL / "f.png"), "-t", "1", "-r", "12",
                    "-pix_fmt", "yuv420p", str(CL / "rendu.mp4")], check=True)
    prof.save(CL / "profondeur.png")
    m = RV.mesurer(CL / "rendu.mp4", None, profondeur={"chemin": str(CL / "profondeur.png"), "run": "r", "t": 0.0,
                                                        "proche_m": 1, "loin_m": 9})
    check("D5 revue_plan.mesurer branche la passe : profondeur MESURÉE (contours), raison honnête, run et plage gardés",
          m["profondeur"]["mesuree"] is True and m["profondeur"]["methode"] == "contours"
          and m["profondeur"]["verdict"] == "proche" and "pas estimée" in m["profondeur"]["raison"]
          and m["profondeur"]["passe"]["run"] == "r", m["profondeur"])
    m = RV.mesurer(CL / "rendu.mp4", None)
    check("D6 sans passe : profondeur NON mesurée, la raison d'avant", m["profondeur"] == {"mesuree": False,
          "raison": RV.PROFONDEUR_NON}, m["profondeur"])
else:
    print("  SKIP  D5-D6 : ffmpeg introuvable")

# ═══════════════════════════════════════ [A] l'outil d'agent ═══════════════════════════════════════
print("[A] l'outil d'agent")
check("A1 lire_passes_plan : dans la boîte « chapitres », nature lecture, registre sain",
      "lire_passes_plan" in B.BOITES["chapitres"]["outils"] and ao.OUTILS["lire_passes_plan"]["nature"] == "lecture"
      and B.verifier() == [], B.verifier())
ctx = ao.Ctx(cid="c1")
r = loop.run_until_complete(ao.lire_passes_plan(ctx, plan=s0))
d = r.get("donnees") or {}
check("A2 lit les runs rangés (le plus récent d'abord), Blender et la scène ; ne rend rien",
      r["ok"] and len(d["runs"]) == 2 and d["runs"][0]["sequence"] is True and d["blender"]["dispo"] is True
      and d["scene_plateau"] is True and d["runs"][1]["passes"]["clay"]["bibliotheque"].startswith("passe_"), r)
r = loop.run_until_complete(ao.lire_passes_plan(ctx, plan=s1))
check("A3 un plan sans passe : le geste dit (« Passes Blender » sur la carte)", r["ok"] and "Passes Blender" in r["resume"], r)
try:
    loop.run_until_complete(ao.lire_passes_plan(ctx, plan="../etc"))
    check("A4 identifiant invalide refusé", False)
except ao._Refus:
    check("A4 identifiant invalide refusé", True)

# ═══════════════════════════════════════ [B] un vrai Blender ═══════════════════════════════════════
print("[B] un vrai rendu Blender court")
PB._racines, PB._sortie_version, PB._popen = VRAIES["racines"], VRAIES["version"], VRAIES["popen"]
PB._CACHE.clear()
vrai = PB.etat_blender(rafraichir=True)
if not vrai["dispo"]:
    print(f"  SKIP  B1-B3 : Blender introuvable sur ce PC ({vrai['raison']})")
else:
    t0 = time.time()
    r = call("POST", f"/passes/plan/{s1}", {})
    j = attendre_job(js(r).get("job", {}).get("id"), n=20000)
    g = js(call("GET", f"/passes/plan/{s1}"))
    rr = (g.get("runs") or [{}])[0]
    d = PB.dossier_plan(W / "outputs", s1) / rr.get("run", "x")
    check(f"B1 vrai Blender {vrai['version']} : 5 passes rendues ({time.time() - t0:.0f} s)",
          j.get("statut") == "fini" and sorted(rr.get("passes", {})) == sorted(PB.PASSES), j)
    if j.get("statut") == "fini":
        pr = Image.open(d / "profondeur_000.png")
        ma = Image.open(d / "masques_000.png").convert("RGB")
        cols = {tuple(int(rr["couleurs"][k][i:i + 2], 16) for i in (1, 3, 5)) for k in rr["couleurs"]}
        vues = {c for _, c in ma.getcolors(1 << 20)}
        check("B2 profondeur en PNG 16 bits, de la plage entière (blanc proche … noir)",
              pr.mode.startswith("I;16") and pr.getextrema()[1] > 60000 and pr.getextrema()[0] == 0, (pr.mode, pr.getextrema()))
        check("B3 masques : les couleurs EXACTES de la palette, et le noir du fond, rien d'autre",
              vues == cols | {(0, 0, 0)}, (sorted(vues)[:8], cols))
        nm = Image.open(d / "normales_000.png").convert("RGB")
        px = nm.getpixel((nm.width // 2, int(nm.height * 0.55)))
        check("B4 normales en espace caméra : le sujet au centre fait face à la caméra (bleu dominant)", px[2] > 200, px)

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
