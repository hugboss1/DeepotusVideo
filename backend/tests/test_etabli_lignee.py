# -*- coding: utf-8 -*-
"""Tache #79 PR C (plan-etabli T10, 03/10/2026) — la LIGNEE des productions de l'Etabli, cote serveur.
DECISION DE L'UTILISATEUR (03/10) : les versions 3D de l'Etabli en arbre (« Etabli T10 »), en section de la couche
montage (pas de nouveau patcher).
Ce que le plan faisait faux, et que ce banc garde : il triait un job par (mere, version) — une petite-fille passait
avant une soeur de sa mere et le decalage ↳ la rangeait sous la mauvaise version ; ici un vrai parcours en profondeur.
Une version tiree du BROUILLON du moteur (non affiche) est une racine de l'affichage ; une boucle de `depuis` (report.json
ouvert aux mains de l'utilisateur) ne fait ni tourner ni disparaitre une version.
Temoin positif : la base (627df13d) ne rend ni profondeur ni mere.
Run (depuis backend/) : & $PY tests/test_etabli_lignee.py"""
import io, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzetlign_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["VECTOR_FOLDER"] = str(_tmp / "vector")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "627df13d"
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base ne rend ni profondeur ni mere dans /etabli/productions", b'"profondeur"' not in r_ro and b"_etabli_productions" in r_ro)

from PIL import Image                                               # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import gltf_builder, mesh_edit, mesh_report      # noqa: E402


def glb():
    t = io.BytesIO(); Image.new("RGBA", (1, 1)).save(t, "PNG")
    return gltf_builder.build_glb({}, None, "cube", "banc", stage_png=t.getvalue())


def job(nom):
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(glb())


def depuis(v):
    return {"depuis": {"version": v, "fichier": "model.glb" if v == 1 else f"model.v{v}.glb"}}


def items():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.get("/api/etabli/productions")
    assert r.status_code == 200, r.text
    return r.json()["items"]


# un arbre : v1 adoptee ; v2 depuis v1 ; v3 depuis v1 ; v4 (extraction) depuis v2
job("j_arbre")
mesh_report.write_report("j_arbre", "model.glb", version=1, extra={"outil": "etabli", "operation": "adoption"})
mesh_edit.ecrire_version("j_arbre", glb(), operation="reparer", detail=depuis(1))
mesh_edit.ecrire_version("j_arbre", glb(), operation="couper", detail=depuis(1))
mesh_edit.ecrire_version("j_arbre", glb(), operation="extraire", detail={**depuis(2), "element": {"noeud": 0, "rang": 0, "sur": 2}})
# tiree du brouillon du moteur (v1 non affichee)
job("j_brouillon")
mesh_edit.ecrire_version("j_brouillon", glb(), operation="reparer", detail=depuis(1))
mesh_edit.ecrire_version("j_brouillon", glb(), operation="couper", detail=depuis(2))
# une boucle : v1 dit venir de v2, v2 de v1
job("j_boucle")
mesh_report.write_report("j_boucle", "model.glb", version=1, extra={"outil": "etabli", "operation": "adoption", **depuis(2)})
mesh_edit.ecrire_version("j_boucle", glb(), operation="reparer", detail=depuis(1))
# une version qui dit venir d'elle-meme, et une `depuis` abimee
job("j_abime")
mesh_edit.ecrire_version("j_abime", glb(), operation="reparer", detail={"depuis": {"version": 2}})
mesh_edit.ecrire_version("j_abime", glb(), operation="couper", detail={"depuis": {"version": "deux"}})

# une version tiree du brouillon (v2) AVANT une racine sans `depuis` (v3) : les racines restent par numero
job("j_melange")
mesh_edit.ecrire_version("j_melange", glb(), operation="reparer", detail=depuis(1))
mesh_edit.ecrire_version("j_melange", glb(), operation="couper", detail={})
# j_arbre devient le job le PLUS RECENT (date reecrite au registre) : il doit sortir en tete
_reg = settings.outputs_path / "assets3d" / "j_arbre" / "report.json"
_r = json.loads(_reg.read_text(encoding="utf-8"))
for _e in _r.get("entries") or []:
    if _e.get("version") == 3:
        _e["created_at"] = "2099-01-01T00:00:00+00:00"
_reg.write_text(json.dumps(_r), encoding="utf-8")

I = items()
def du(j):
    return [z for z in I if z["job"] == j]

A = du("j_arbre")
check("R1 l'ordre est celui de la LIGNEE (parcours en profondeur) : v1, v2, sa fille v4, PUIS la soeur v3 — jamais l'ordre du temps",
      [z["version"] for z in A] == [1, 2, 4, 3], str([z["version"] for z in A]))
check("R2 profondeur, mere (la racine) et depuis_version (telle qu'ecrite) ; l'element extrait remonte",
      [z["profondeur"] for z in A] == [0, 1, 2, 1] and [z["mere"] for z in A] == [1, 1, 1, 1]
      and [z["depuis_version"] for z in A] == [None, 1, 2, 1] and A[2]["element"] == {"noeud": 0, "rang": 0, "sur": 2}
      and A[0]["element"] is None, json.dumps([(z["version"], z["profondeur"], z["depuis_version"]) for z in A]))
Bj = du("j_brouillon")
check("R3 une version tiree du BROUILLON du moteur (non affiche) est une racine de l'affichage ; depuis_version dit encore 1",
      [(z["version"], z["profondeur"], z["mere"], z["depuis_version"]) for z in Bj] == [(2, 0, 2, 1), (3, 1, 2, 2)], str(Bj and [(z["version"], z["profondeur"]) for z in Bj]))
Cj = du("j_boucle")
check("R4 une BOUCLE de `depuis` : chaque version sort UNE fois, avec une profondeur finie (la plus petite reprise en racine)",
      sorted(z["version"] for z in Cj) == [1, 2] and [(z["version"], z["profondeur"]) for z in Cj] == [(1, 0), (2, 1)], str([(z["version"], z["profondeur"]) for z in Cj]))
Dj = du("j_abime")
check("R5 une version qui se designe elle-meme, ou une `depuis` qui n'est pas un numero : racines, sans erreur",
      [(z["version"], z["profondeur"], z["depuis_version"]) for z in Dj] == [(2, 0, None), (3, 0, None)], str([(z["version"], z["profondeur"], z["depuis_version"]) for z in Dj]))
Mj = du("j_melange")
check("R3b une version tiree du brouillon et une racine sans `depuis` sont deux racines, rangees PAR NUMERO",
      [(z["version"], z["profondeur"]) for z in Mj] == [(2, 0), (3, 0)], str([(z["version"], z["profondeur"]) for z in Mj]))
jobs = []
for z in I:
    if not jobs or jobs[-1] != z["job"]:
        jobs.append(z["job"])
dern = {j: max(z["created_at"] or "" for z in du(j)) for j in set(jobs)}
check("R6 les productions d'un job sont CONTIGUES, les jobs classes par leur production la plus recente ; `rang` = la position",
      len(jobs) == len(set(jobs)) and jobs[0] == "j_arbre" and [dern[j] for j in jobs] == sorted((dern[j] for j in jobs), reverse=True)
      and [z["rang"] for z in I] == list(range(len(I))), str(jobs))
check("R7 la carte garde sa forme (nom, url, vignette, provider) — la lignee ne fait qu'ajouter des champs",
      A[1]["name"].endswith("· v2 · reparer") and A[1]["url"] == "/api/assets/3d/j_arbre/version/2" and A[1]["provider"] == "Établi"
      and A[1]["kind"] == "asset3d" and A[1]["short"] == "j_arbre")

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
