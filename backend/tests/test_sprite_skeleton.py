# -*- coding: utf-8 -*-
"""t111 (plan-sprites T12) — le rig Spine, LU sur le disque : skeleton.json et PNG des pièces.

LE BANC NE CROIT PAS LE CODE, IL REFAIT LA CINÉMATIQUE : la doc Spine (relue le 06/10/2026) dit que les x, y, rotation
d'un os sont « relative to the parent » et ceux d'une pièce « relative to the slot's bone ». Le banc relit le JSON,
compose les transformations de la racine à chaque os, puis place le centre de chaque pièce : il doit retomber sur le
centre de la boîte tracée dans la case (y remonte en Spine), pièce droite (rotation monde 0). Le code du plan écrivait
les os en coordonnées ABSOLUES et le décalage des pièces sans la rotation de leur os : la tête d'un « cou » enfant
d'un « torse » décalé sortait ailleurs — ce banc le rougit.

Run: python tests/test_sprite_skeleton.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
TETE = (200, 40, 40, 255)
CORPS = (40, 90, 200, 255)
BRAS = (40, 180, 60, 255)


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _boite(im, couleur):
    """La boîte (x, y, w, h) des pixels d'une couleur — MESURÉE sur la case écrite, pas supposée."""
    xs, ys = [], []
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y] == couleur:
                xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i in range(2):
        n = f"sk{i}.png"
        im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([48, 16, 79, 47], fill=TETE)          # la tête
        d.rectangle([44, 60, 83, 109], fill=CORPS)        # le corps
        d.rectangle([84, 64, 111, 71], fill=BRAS)         # un bras tendu à droite
        im.save(settings.images_path / n)
        noms.append(n)
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms}, "remove_bg": "none",
         "cell": {"size": "native"}, "columns": 2,
         "anim": {"tags": [{"name": "idle", "from": 0, "to": 1}, {"name": "hit", "from": 1, "to": 1}]}}, "j-sk"))
    return settings.outputs_path / "sprites" / "j-sk"


@pytest.fixture(scope="module")
def rig(dossier):
    """Un rig posé COMME LA PAGE LE POSE : positions et angles dans la case (y vers le bas, angle visuel en degrés,
    sens trigonométrique : 90 = vers le haut). Le torse est TOURNÉ (80°) pour que l'enfant ait un repère parent non
    trivial ; le cou a un parent décalé ; le bras pend à 0° d'un torse à 80°."""
    with Image.open(dossier / "frames" / "000.png") as f:
        im = f.convert("RGBA")
    t, c, b = _boite(im, TETE), _boite(im, CORPS), _boite(im, BRAS)
    cx = c[0] + c[2] / 2
    return {
        "frame": 0, "taille": im.size,
        "bones": [{"name": "torse", "x": cx, "y": c[1] + c[3], "length": c[3], "rotation": 80},
                  {"name": "cou", "parent": "torse", "x": cx, "y": c[1], "length": 20, "rotation": 90},
                  {"name": "bras", "parent": "torse", "x": b[0], "y": b[1] + b[3] / 2, "length": b[2], "rotation": 0}],
        "pieces": [{"name": "corps", "bone": "torse", "x": c[0], "y": c[1], "w": c[2], "h": c[3]},
                   {"name": "tete", "bone": "cou", "x": t[0], "y": t[1], "w": t[2], "h": t[3]},
                   {"name": "bras", "bone": "bras", "x": b[0], "y": b[1], "w": b[2], "h": b[3]}],
    }


def _poser(rig):
    return {k: v for k, v in rig.items() if k != "taille"}


def _monde(sk):
    """Cinématique directe, lue dans le JSON : {os: (x, y, rotation monde)}. Échelles à 1 (le rig n'en écrit pas)."""
    out = {}
    for b in sk["bones"]:
        assert b.get("scaleX", 1) == 1 and b.get("scaleY", 1) == 1
        x, y, r = b.get("x", 0), b.get("y", 0), b.get("rotation", 0)
        if "parent" in b:
            px, py, pr = out[b["parent"]]
            a = math.radians(pr)
            x, y, r = px + math.cos(a) * x - math.sin(a) * y, py + math.sin(a) * x + math.cos(a) * y, pr + r
        out[b["name"]] = (x, y, r)
    return out


def test_temoin_la_base_n_a_ni_module_ni_route():
    m = subprocess.run(["git", "show", "48ebf72c:backend/app/services/sprite_skeleton.py"], capture_output=True,
                       cwd=str(RACINE))
    r = subprocess.run(["git", "show", "48ebf72c:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
    assert m.returncode != 0 and r.stdout and b"/skeleton" not in r.stdout


def test_le_squelette_a_la_forme_spine_3_8(dossier, rig):
    r = _client().post("/api/assets/sprite/j-sk/skeleton", json=_poser(rig))
    assert r.status_code == 200, r.text
    sk = json.loads((dossier / "spine" / "skeleton.json").read_text("utf-8"))
    w, h = rig["taille"]
    assert sk["skeleton"]["spine"] == "3.8.99"
    assert (sk["skeleton"]["width"], sk["skeleton"]["height"]) == (w, h)
    assert sk["skeleton"]["images"] == "./images/" and len(sk["skeleton"]["hash"]) == 11
    # un os racine est TOUJOURS émis (origine Spine = coin BAS-GAUCHE de la case), les os s'y accrochent
    assert [b["name"] for b in sk["bones"]] == ["root", "torse", "cou", "bras"]
    assert sk["bones"][0] == {"name": "root"}
    assert [b.get("parent") for b in sk["bones"][1:]] == ["root", "torse", "torse"]
    assert [s["name"] for s in sk["slots"]] == ["corps", "tete", "bras"]
    assert [(s["bone"], s["attachment"]) for s in sk["slots"]] == [("torse", "corps"), ("cou", "tete"), ("bras", "bras")]
    # skins est un TABLEAU de {name, attachments} (3.8), pas une carte de cartes (3.7)
    assert isinstance(sk["skins"], list) and sk["skins"][0]["name"] == "default"
    att = sk["skins"][0]["attachments"]["tete"]["tete"]
    assert (att["width"], att["height"]) == (rig["pieces"][1]["w"], rig["pieces"][1]["h"])
    # les tags donnent des animations NOMMÉES et VIDES : un rig, pas de timeline inventée
    assert sk["animations"] == {"idle": {}, "hit": {}}
    # reçu = ce que la route rend
    assert r.json()["bones"] == 4 and r.json()["slots"] == 3 and r.json()["hash"] == sk["skeleton"]["hash"]


def test_la_cinematique_RELUE_replace_chaque_os_et_chaque_piece_ou_la_page_les_a_poses(dossier, rig):
    sk = json.loads((dossier / "spine" / "skeleton.json").read_text("utf-8"))
    h = rig["taille"][1]
    monde = _monde(sk)
    for b in rig["bones"]:                       # chaque os, à sa position et son angle de la case
        x, y, r = monde[b["name"]]
        assert abs(x - b["x"]) < 0.02 and abs(y - (h - b["y"])) < 0.02, (b["name"], x, y)
        assert abs((r - b["rotation"] + 180) % 360 - 180) < 0.02, (b["name"], r)
    atts = sk["skins"][0]["attachments"]
    for p in rig["pieces"]:                      # chaque pièce, centrée sur sa boîte et DROITE
        a = atts[p["name"]][p["name"]]
        bx, by, br = monde[p["bone"]]
        t = math.radians(br)
        wx = bx + math.cos(t) * a["x"] - math.sin(t) * a["y"]
        wy = by + math.sin(t) * a["x"] + math.cos(t) * a["y"]
        assert abs(wx - (p["x"] + p["w"] / 2)) < 0.03 and abs(wy - (h - (p["y"] + p["h"] / 2))) < 0.03, (p["name"], wx, wy)
        assert abs((br + a.get("rotation", 0) + 180) % 360 - 180) < 0.02, (p["name"], br, a.get("rotation"))


def test_les_pieces_sont_des_PNG_rognes_aux_pixels_de_la_case(dossier, rig):
    img = dossier / "spine" / "images"
    for p, coul in zip(rig["pieces"], (CORPS, TETE, BRAS)):
        with Image.open(img / f"{p['name']}.png") as f:
            assert f.size == (p["w"], p["h"]), p["name"]
            assert f.convert("RGBA").getpixel((p["w"] // 2, p["h"] // 2)) == coul, p["name"]


def test_le_manifeste_le_get_et_le_zip_portent_le_rig(dossier):
    import io
    import zipfile
    from app.services.sprite_service import build_zip_bytes
    c = _client()
    assert c.get("/api/assets/sprite/j-sk/manifest").json()["files"]["spine"] is True
    g = c.get("/api/assets/sprite/j-sk/skeleton")
    assert g.status_code == 200 and g.json()["skeleton"]["spine"] == "3.8.99"
    with zipfile.ZipFile(io.BytesIO(build_zip_bytes(dossier))) as z:
        noms = set(z.namelist())
    assert {"spine/skeleton.json", "spine/images/tete.png", "spine/images/corps.png", "spine/images/bras.png"} <= noms


def test_un_nouveau_rig_remplace_l_ancien_sans_pieces_orphelines(dossier, rig):
    seul = _poser(rig)
    seul["pieces"] = [rig["pieces"][0]]
    assert _client().post("/api/assets/sprite/j-sk/skeleton", json=seul).status_code == 200
    assert sorted(p.name for p in (dossier / "spine" / "images").iterdir()) == ["corps.png"]
    assert _client().post("/api/assets/sprite/j-sk/skeleton", json=_poser(rig)).status_code == 200


def test_les_gardes_du_rig(dossier, rig):
    c = _client()

    def mauvais(**over):
        r = _poser(rig)
        r.update(over)
        return c.post("/api/assets/sprite/j-sk/skeleton", json=r).status_code

    p0 = {"name": "x", "bone": "torse", "x": 0, "y": 0, "w": 4, "h": 4}
    assert mauvais(bones=[]) == 400
    assert mauvais(pieces=[]) == 400
    assert mauvais(bones=[{"name": "a", "parent": "zzz", "x": 1, "y": 1}]) == 400          # parent inconnu
    assert mauvais(bones=[{"name": "a", "parent": "b", "x": 1, "y": 1},                     # parent APRÈS l'enfant :
                          {"name": "b", "x": 1, "y": 1}]) == 400                             # c'est ce qui interdit les cycles
    assert mauvais(bones=[{"name": "root", "x": 1, "y": 1}]) == 400                         # « root » est réservé
    assert mauvais(pieces=[p0, dict(p0, x=8)]) == 400                                       # nom en double
    assert mauvais(pieces=[dict(p0, name="../x")]) == 400                                   # il devient un NOM DE FICHIER
    assert mauvais(pieces=[dict(p0, x=rig["taille"][0] - 2, w=40)]) == 400                  # boîte hors de la case
    assert mauvais(pieces=[dict(p0, bone="zzz")]) == 400                                    # os inconnu
    assert mauvais(pieces=[dict(p0, w="large")]) == 400                                     # pas un nombre
    from app.services import sprite_skeleton as SK                                          # NaN / inf : le JSON
    for v in (float("nan"), float("inf"), True):                                            # ne les porte pas, le
        with pytest.raises(ValueError):                                                     # module les refuse
            SK.normaliser({"bones": [dict(rig["bones"][0], rotation=v)], "pieces": [rig["pieces"][0]]}, 128, 128)
    assert mauvais(frame=9) == 400                                                          # pas de case à ce numéro
    assert mauvais(frame="a") == 400
    assert c.post("/api/assets/sprite/j-absent/skeleton", json=_poser(rig)).status_code == 404
    assert c.get("/api/assets/sprite/j-absent/skeleton").status_code == 404


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
