"""T108 (plan-sprites T1, P1) — cellule « native » : la feuille pose les frames à leur taille, sans agrandissement ; les
octets d'une frame sont ceux de la source ; la cellule est la plus grande dimension MESURÉE (recadrage tight compris) ;
une frame trop grande (vidéo brute) est refusée en le disant ; l'écran propose l'option et l'envoie.

Run: python tests/test_sprite_native.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspn_")
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

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent


def _png(nom, taille, couleur, marge=1):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([marge, marge, taille[0] - 1 - marge, taille[1] - 1 - marge], fill=couleur)
    im.save(settings.images_path / nom)
    return nom, im


def _gen(payload, job):
    from app.config import settings
    from app.services import sprite_service as S
    r = asyncio.run(S.generate_sprites(payload, job))
    d = settings.outputs_path / "sprites" / job
    return r, d, json.loads((d / "manifest.json").read_text("utf-8"))


def test_normalize_accepte_native_et_refuse_le_reste():
    from app.services import sprite_service as S
    assert S.normalize_opts({"cell": {"size": "native"}})["cell_size"] == 0
    assert S.normalize_opts({"cell": {"size": "NATIVE"}})["cell_size"] == 0
    assert S.normalize_opts({"cell": {"size": 256}})["cell_size"] == 256
    assert S.normalize_opts({"cell": {"size": "512"}})["cell_size"] == 512
    assert S.normalize_opts({"cell": {}})["cell_size"] == 256
    for bad in ({"cell": {"size": "natif"}}, {"cell": {"size": 0}}, {"cell": {"size": 64}}):
        with pytest.raises(ValueError, match="native"):
            S.normalize_opts(bad)


def test_la_feuille_native_ne_redimensionne_pas():
    noms, ims = zip(*[_png(f"n{i}.png", (24, 16), (10 * i + 20, 200, 30, 255)) for i in range(3)])
    r, d, m = _gen({"source": {"kind": "images", "filenames": list(noms)},
                    "cell": {"size": "native", "align": "feet"}, "columns": 3}, "j-nat")
    assert m["native"] is True and m["grid"] == {"cols": 3, "rows": 1, "cell_w": 24, "cell_h": 24}
    with Image.open(d / "sheet.png") as sh:
        assert sh.size == (72, 24)
        # frame 1 posée « pieds » : ses 16 lignes occupent y = 8..23, octets identiques
        crop = sh.convert("RGBA").crop((24, 8, 48, 24))
    assert crop.tobytes() == ims[1].tobytes()
    assert r["grid"]["cell_w"] == 24
    with Image.open(d / "frames" / "002.png") as f2:
        assert f2.size == (24, 24)
    unity = json.loads((d / "sheet.unity.json").read_text("utf-8"))
    assert unity["pixelsPerUnit"] == 24 and unity["frames"][1]["w"] == 24


def test_native_centre_et_tight_mesure_la_cellule_apres_recadrage():
    noms, ims = zip(*[_png(f"t{i}.png", (40, 40), (200, 10 * i, 10, 255), marge=12) for i in range(2)])
    _, d, m = _gen({"source": {"kind": "images", "filenames": list(noms)},
                    "cell": {"size": "native", "align": "center"}, "trim": "tight"}, "j-tight")
    assert m["grid"]["cell_w"] == 16, m["grid"]                       # 40 px de toile, 16 px de contenu
    with Image.open(d / "sheet.png") as sh:
        assert sh.size == (32, 16)
        assert sh.convert("RGBA").crop((16, 0, 32, 16)).tobytes() == ims[1].crop((12, 12, 28, 28)).tobytes()


def test_native_pose_aussi_des_frames_de_tailles_differentes_sans_les_agrandir():
    a, ia = _png("pa.png", (10, 30), (255, 0, 0, 255), marge=0)
    b, ib = _png("pb.png", (30, 10), (0, 0, 255, 255), marge=0)
    _, d, m = _gen({"source": {"kind": "images", "filenames": [a, b]},
                    "cell": {"size": "native", "align": "center"}, "columns": 2}, "j-mix")
    assert m["grid"]["cell_w"] == 30
    with Image.open(d / "sheet.png") as sh:
        rgba = sh.convert("RGBA")
        assert rgba.crop((10, 0, 20, 30)).tobytes() == ia.tobytes()       # x centré : (30 - 10) // 2 = 10
        assert rgba.crop((30, 10, 60, 20)).tobytes() == ib.tobytes()      # y centré : (30 - 10) // 2 = 10
        assert rgba.getpixel((5, 5))[3] == 0                              # rien d'étiré dans les marges


def test_une_petite_frame_a_cote_d_une_grande_n_est_pas_agrandie():
    petit, ip = _png("sp.png", (8, 8), (0, 255, 0, 255), marge=0)
    grand, _ = _png("sg.png", (24, 24), (0, 0, 255, 255), marge=0)
    _, d, m = _gen({"source": {"kind": "images", "filenames": [petit, grand]},
                    "cell": {"size": "native", "align": "feet"}, "columns": 2}, "j-petit")
    assert m["grid"]["cell_w"] == 24
    with Image.open(d / "sheet.png") as sh:
        rgba = sh.convert("RGBA")
        assert rgba.crop((8, 16, 16, 24)).tobytes() == ip.tobytes()      # 8×8 posé aux pieds, centré en x
        assert rgba.getpixel((2, 2))[3] == 0                              # jamais étiré à 24×24


def test_des_frames_plus_hautes_que_larges_dimensionnent_par_la_hauteur():
    noms, _ = zip(*[_png(f"h{i}.png", (6, 20), (200, 200, 0, 255), marge=0) for i in range(2)])
    _, d, m = _gen({"source": {"kind": "images", "filenames": list(noms)}, "cell": {"size": "native"}}, "j-haut")
    assert m["grid"]["cell_w"] == 20 and m["grid"]["cell_h"] == 20, m["grid"]


def test_une_cellule_classique_agrandit_toujours_temoin():
    noms, _ = zip(*[_png(f"c{i}.png", (24, 16), (50, 50, 50, 255)) for i in range(2)])
    _, d, m = _gen({"source": {"kind": "images", "filenames": list(noms)}, "cell": {"size": 128}}, "j-128")
    assert m["native"] is False and m["grid"]["cell_w"] == 128


def test_native_refuse_une_frame_trop_grande_en_le_disant():
    from app.services import sprite_service as S
    nom, _ = _png("big.png", (1500, 40), (9, 9, 9, 255))
    with pytest.raises(RuntimeError, match="1024"):
        _gen({"source": {"kind": "images", "filenames": [nom]}, "cell": {"size": "native"}}, "j-big")
    assert S.NATIVE_MAX == 1024


def test_l_ecran_propose_native_et_l_envoie():
    html = (RACINE / "frontend" / "spritelab" / "index.html").read_text(encoding="utf-8")
    js = (RACINE / "frontend" / "spritelab" / "spritelab.js").read_text(encoding="utf-8")
    assert '<option value="native">' in html
    assert '$("#cellSize").value === "native" ? "native"' in js


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
