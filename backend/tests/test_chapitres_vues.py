# -*- coding: utf-8 -*-
"""Plan chapitres T7 (tache #62 du suivi, 02/10/2026) — les VUES de reference d'une entite, pour les generations
multi-references :
  - la recette v3 garde le FICHIER de chaque panneau, les miroirs et la planche (v2 ne gardait que la planche : une
    mosaique 4 colonnes n'est pas quatre references) ; le rejeu accepte v2 ET v3 — aux TROIS gardes, canon compris
    (le plan en oubliait une : le rejeu d'une v3 aurait perdu son canon de proportions) ;
  - DECISION DE L'UTILISATEUR (02/10) : les entites d'avant, qui n'ont que leur planche, ont leurs vues DECOUPEES dans
    la planche (geometrie fixee par le code : bandes de hauteur connue, fond uni) — gratuit, sans regenerer ;
  - GET /bible/entities/{id}/vues dit d'ou viennent les vues : recette | decoupe | planche (geometrie inconnue : la
    planche entiere, en le disant) | aucune.
Aucun appel paye : fal et les telechargements simules, data-dir isole, cles videes (le controle de proportions par
vision n'a donc pas de moteur). Temoin positif : la base (ce7852e3) ecrit une recette v2 et n'a pas la route.
Run (depuis backend/) : & $PY tests/test_chapitres_vues.py"""
import io, json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzvues_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "ce7852e3"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base ecrit une recette v2 et n'a pas la route /vues", r0.returncode == 0 and b'{"v": 2, "kind": e.kind' in r0.stdout
      and b"/vues" not in r0.stdout)

APPELS = []
from PIL import Image                                               # noqa: E402
_buf = io.BytesIO(); Image.new("RGB", (30, 40), (30, 60, 90)).save(_buf, "PNG"); PNG = _buf.getvalue()


async def _fake_subscribe(model, arguments=None, **kw):
    APPELS.append(model)
    return {"images": [{"url": "http://fal.test/img.png"}], "seed": (arguments or {}).get("seed", 424242)}


async def _fake_upload(path):
    return "http://fal.test/up.png"
_stub = types.ModuleType("fal_client"); _stub.subscribe_async = _fake_subscribe; _stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub
import httpx as _httpx                                              # noqa: E402
_orig_get = _httpx.AsyncClient.get


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG, request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)
_httpx.AsyncClient.get = _fake_get

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
from app.services import board_service as BS                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
IMG = _tmp / "images"


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def panneau(nom, couleur, taille):
    Image.new("RGB", taille, couleur).save(IMG / nom)
    return nom


def couleur_moyenne(nom):
    im = Image.open(IMG / nom).convert("RGB").resize((1, 1), Image.BOX)
    return im.getpixel((0, 0))


print("[C] decoupe d'une planche (geometrie du code)")
COUL = {"face_front": (200, 30, 30), "face_left": (30, 200, 30), "face_right": (30, 30, 200),
        "front": (200, 200, 30), "left": (30, 200, 200), "right": (200, 30, 200), "back": (90, 90, 90)}
TAILLES = {"face_front": (300, 400), "face_left": (280, 400), "face_right": (280, 400),
           "front": (300, 700), "left": (260, 700), "right": (260, 700), "back": (320, 700)}
pans = {k: panneau(f"p_{k}.png", COUL[k], TAILLES[k]) for k in COUL}
board = BS.compose_character_board(IMG, pans)
try:
    vues = BS.decouper_planche(IMG, board, "character")
except AttributeError as e:
    vues = None
    print("   ", repr(e))
check("C1 personnage : les SEPT vues retrouvees, par cle", isinstance(vues, dict) and set(vues) == set(COUL), str(vues))
if isinstance(vues, dict) and set(vues) == set(COUL):
    exact = all(max(abs(a - b) for a, b in zip(couleur_moyenne(vues[k]), COUL[k])) <= 2 for k in COUL)
    check("C2 chaque vue est le BON panneau (sa couleur), sans fond de planche autour", exact,
          str({k: couleur_moyenne(v) for k, v in vues.items()}))
    h_face = Image.open(IMG / vues["face_front"]).size[1]; h_corps = Image.open(IMG / vues["front"]).size[1]
    check("C3 tailles : visages 300 px de haut, corps 560 (celles de la planche)", h_face == 300 and h_corps == 560, f"{h_face} {h_corps}")
    deja = sorted(p.name for p in IMG.iterdir())
    vues2 = BS.decouper_planche(IMG, board, "character")
    check("C4 redecouper : les MEMES fichiers (rien de neuf dans la Bibliotheque)", vues2 == vues and sorted(p.name for p in IMG.iterdir()) == deja)
else:
    check("C2 chaque vue est le BON panneau", False); check("C3 tailles", False); check("C4 redecouper", False)
lieu = BS.compose_board(IMG, [[panneau("l1.png", (10, 120, 10), (640, 360)), panneau("l2.png", (120, 10, 10), (640, 360)),
                              panneau("l3.png", (10, 10, 120), (400, 400))]], [400])
vl = BS.decouper_planche(IMG, lieu, "place") if hasattr(BS, "decouper_planche") else None
check("C5 lieu (une rangee de trois) : trois vues, dans l'ordre du plan", isinstance(vl, dict) and list(vl) == ["wide", "angle", "detail"]
      and couleur_moyenne(vl["angle"])[0] > 100, str(vl))
amb = BS.compose_board(IMG, [[panneau("a1.png", (150, 20, 20), (500, 300)), panneau("a2.png", (20, 150, 20), (500, 300)),
                             panneau("a3.png", (20, 20, 150), (500, 300))]], [380], palette_from=["a1.png", "a2.png", "a3.png"])
va = BS.decouper_planche(IMG, amb, "ambiance") if hasattr(BS, "decouper_planche") else None
check("C7 ambiance AVEC sa bande de palette (hauteur comptee) : trois vues", isinstance(va, dict) and list(va) == ["f1", "f2", "f3"]
      and couleur_moyenne(va["f2"])[1] > 100, str(va))
if hasattr(BS, "decouper_planche"):
    faux = Image.new("RGB", Image.open(IMG / board).size, BS._BG)
    faux.paste(Image.new("RGB", (200, 300), (9, 9, 9)), (40, 28)); faux.paste(Image.new("RGB", (200, 300), (9, 9, 9)), (400, 28))
    faux.save(IMG / "board_deux_visages.png")
    check("C8 bonne hauteur mais DEUX visages au lieu de trois : rien n'est decoupe", BS.decouper_planche(IMG, "board_deux_visages.png", "character") is None)
    grand = Image.open(IMG / board).convert("RGB")
    plus = Image.new("RGB", (grand.width, grand.height + 10), BS._BG); plus.paste(grand, (0, 0)); plus.save(IMG / "board_trop_haut.png")
    check("C9 une planche valide rallongee de 10 px (geometrie qui ne colle plus) : rien n'est decoupe",
          BS.decouper_planche(IMG, "board_trop_haut.png", "character") is None)
    tache = Image.open(IMG / board).convert("RGB"); tache.paste(Image.new("RGB", (2, 2), (0, 0, 0)), (10, 100)); tache.save(IMG / "board_tache.png")
    vt = BS.decouper_planche(IMG, "board_tache.png", "character")
    check("C10 une poussiere de 2 px dans une gouttiere est ignoree : sept vues", isinstance(vt, dict) and len(vt) == 7, str(vt))
    if isinstance(vues, dict):
        avant_t = {k: (IMG / f).stat().st_mtime_ns for k, f in vues.items()}
        BS.decouper_planche(IMG, board, "character")
        check("C11 redecouper n'ECRIT rien (les vues deja la sont reutilisees)", {k: (IMG / f).stat().st_mtime_ns for k, f in vues.items()} == avant_t)
Image.new("RGB", (900, 500), (5, 5, 5)).save(IMG / "board_inconnu.png")
check("C6 une planche d'une AUTRE geometrie : rien n'est decoupe (pas de vues fausses)",
      hasattr(BS, "decouper_planche") and BS.decouper_planche(IMG, "board_inconnu.png", "character") is None)

with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    print("\n[G] generation : recette v3")
    e = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Elias", "description": "homme fatigue, cape bleue"}))
    APPELS.clear()
    r = c.post(f"/api/bible/entities/{e.get('id')}/generate", json={"seed": 777})
    ent = js(r)
    rec = json.loads(sqlite3.connect(str(_DB)).execute("SELECT prompt_recipe FROM bible_entities WHERE id=?", (e.get("id"),)).fetchone()[0] or "{}")
    check("G1 la generation passe (fal simule : 5 panneaux)", r.status_code == 200 and len(APPELS) == 5, f"{r.status_code} {r.text[:200]} {APPELS}")
    check("G2 recette v3 : chaque panneau garde son FICHIER, les miroirs et la planche sont nommes",
          rec.get("v") == 3 and len(rec.get("panels", [])) == 5 and all(str(p.get("file", "")).endswith(".png") for p in rec["panels"])
          and set(rec.get("mirrors", {})) == {"face_right", "right"} and rec.get("board") == ent.get("ref_image"), json.dumps(rec)[:300])
    v = js(c.get(f"/api/bible/entities/{e.get('id')}/vues"))
    check("G3 /vues : source « recette », SEPT vues (5 generees + 2 miroirs), la planche n'en est pas", v.get("source") == "recette"
          and len(v.get("vues", [])) == 7 and ent.get("ref_image") not in v.get("vues", []) and set(v.get("par_cle", {})) == set(COUL), str(v)[:300])

    print("\n[R] rejeu d'une v3 : les trois gardes")
    cx = sqlite3.connect(str(_DB))
    rec["canon"] = "manga_shonen"
    rec["panels"][0]["seed"] = 31337
    cx.execute("UPDATE bible_entities SET prompt_recipe=?, description='' WHERE id=?", (json.dumps(rec), e.get("id"))); cx.commit(); cx.close()
    APPELS.clear()
    r = c.post(f"/api/bible/entities/{e.get('id')}/generate", json={"use_recipe": True})
    rec2 = json.loads(sqlite3.connect(str(_DB)).execute("SELECT prompt_recipe FROM bible_entities WHERE id=?", (e.get("id"),)).fetchone()[0] or "{}")
    check("R1 sans description, une v3 se REJOUE (garde 2)", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    check("R2 ... avec SES graines (garde 1)", r.status_code == 200 and len(APPELS) == 5 and rec2.get("panels", [{}])[0].get("seed") == 31337, str(rec2.get("panels", [{}])[:1]))
    check("R3 ... et SON canon de proportions (garde 3, oubliee par le plan)", r.status_code == 200 and rec2.get("canon") == "manga_shonen", str(rec2.get("canon")))

    print("\n[V] les entites d'avant")
    v2e = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Ancien"}))
    cx = sqlite3.connect(str(_DB))
    cx.execute("UPDATE bible_entities SET ref_image=?, prompt_recipe=? WHERE id=?",
               (board, json.dumps({"v": 2, "kind": "character", "panels": [{"key": "face_front", "seed": 1}]}), v2e.get("id"))); cx.commit()
    v = js(c.get(f"/api/bible/entities/{v2e.get('id')}/vues"))
    check("V1 recette v2 + planche : les vues sont DECOUPEES (source « decoupe »), sept", v.get("source") == "decoupe" and len(v.get("vues", [])) == 7
          and board not in v.get("vues", []), str(v)[:300])
    inconnue = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Mosaique"}))
    cx.execute("UPDATE bible_entities SET ref_image='board_inconnu.png' WHERE id=?", (inconnue.get("id"),)); cx.commit()
    v = js(c.get(f"/api/bible/entities/{inconnue.get('id')}/vues"))
    check("V2 planche d'une autre geometrie : la planche entiere, EN LE DISANT (« planche »)", v.get("source") == "planche"
          and v.get("vues") == ["board_inconnu.png"], str(v))
    nue = js(c.post("/api/bible/entities", json={"kind": "object", "name": "Cle"}))
    check("V3 sans image : « aucune », liste vide", js(c.get(f"/api/bible/entities/{nue.get('id')}/vues")) .get("source") == "aucune")
    check("V4 entite inconnue : 404", c.get("/api/bible/entities/inconnue/vues").status_code == 404)
    cx.execute("UPDATE bible_entities SET prompt_recipe=? WHERE id=?",
               (json.dumps({**rec, "panels": [{**p, "file": "efface.png"} for p in rec["panels"]], "mirrors": {}}), e.get("id"))); cx.commit(); cx.close()
    v = js(c.get(f"/api/bible/entities/{e.get('id')}/vues"))
    check("V5 recette v3 dont les fichiers ont disparu : on retombe sur la decoupe de SA planche", v.get("source") == "decoupe"
          and len(v.get("vues", [])) == 7, str(v)[:300])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
