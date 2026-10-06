"""T109 (plan-sprites T5, P3c) — la feuille Paper2D, LUE sur le disque.

Ce que le banc peut prouver : notre fichier a la forme JSON Array de TexturePacker, l'ordre des images y est celui de
l'animation, et les rectangles collent à la feuille PNG (relus en PIL). Ce qu'il ne peut PAS prouver : qu'Unreal
l'importe — la documentation a refusé la relecture (03/09 : 403 et 404 ; 06/10 : tutoriel TexturePacker toujours 404).

Run: python tests/test_sprite_paper2d.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspp_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = ""
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def _png(nom, couleur, taille=(16, 16)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([1, 1, taille[0] - 2, taille[1] - 2], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"w{i}.png", (200, 40 * i + 40, 30, 255)) for i in range(3)]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
                                    "columns": 2, "fps_sample": 10}, "j-p2d"))
    return settings.outputs_path / "sprites" / "j-p2d"


def test_les_images_sont_une_LISTE_dans_l_ordre_de_l_animation(dossier):
    d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    assert isinstance(d["frames"], list)            # Array, pas Hash
    assert [f["filename"] for f in d["frames"]] == ["frame_000.png", "frame_001.png", "frame_002.png"]
    f = d["frames"][2]
    assert f["frame"] == {"x": 0, "y": 128, "w": 128, "h": 128}
    assert f["rotated"] is False and f["trimmed"] is False
    assert f["spriteSourceSize"] == {"x": 0, "y": 0, "w": 128, "h": 128} and f["sourceSize"] == {"w": 128, "h": 128}
    assert f["pivot"] == {"x": 0.5, "y": 0.5}


def test_les_rectangles_collent_a_la_feuille_PNG(dossier):
    d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    with Image.open(dossier / "sheet.png") as sh:
        assert (sh.width, sh.height) == (d["meta"]["size"]["w"], d["meta"]["size"]["h"])
        rgba = sh.convert("RGBA")
        for i, f in enumerate(d["frames"]):
            r = f["frame"]
            assert r["x"] + r["w"] <= sh.width and r["y"] + r["h"] <= sh.height
            case = rgba.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
            with Image.open(dossier / "frames" / f"{i:03d}.png") as ref:
                assert case.tobytes() == ref.convert("RGBA").tobytes()


def test_le_meta_nomme_la_texture(dossier):
    d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    assert d["meta"]["image"] == "sheet.png" and d["meta"]["format"] == "RGBA8888" and d["meta"]["scale"] == "1"


def test_les_quatre_exports_partagent_le_nom_des_cases(dossier):
    """frame_000.png est la convention que les moteurs utilisent pour relier une animation à ses cases : UN seul
    endroit la décide (sprite_export.frame_name)."""
    a = json.loads((dossier / "sheet.atlas.json").read_text("utf-8"))
    p = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    assert sorted(a["frames"]) == [f["filename"] for f in p["frames"]]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
