"""T108 (plan-sprites T0) — source `images` du Sprite Lab : des PNG de la Library deviennent les frames, sans ffmpeg ;
garde des noms (un nom avec un chemin est REFUSÉ, jamais nettoyé) ; feuille lue en PIL ; la route accepte la source
et titre le job d'après la première image.

Run: python tests/test_sprite_images_source.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspi_")
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


def _carre(nom: str, couleur, taille=(40, 24)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([4, 4, taille[0] - 5, taille[1] - 5], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def _run(payload, job):
    from app.services import sprite_service as S
    return asyncio.run(S.generate_sprites(payload, job))


def test_resolve_images_refuse_les_noms_qui_sortent_de_la_library():
    from app.config import settings
    from app.services import sprite_service as S
    _carre("ok.png", (200, 30, 30, 255))
    (settings.images_path / "notes.txt").write_text("x", encoding="utf-8")
    assert [p.name for p in S.resolve_images({"filenames": ["ok.png"]})] == ["ok.png"]
    for bad in ({}, {"filenames": []}, {"filenames": "ok.png"}, {"filenames": ["../ok.png"]},
                {"filenames": ["absent.png"]}, {"filenames": ["ok.png"] * 65}, {"filenames": ["notes.txt"]},
                {"filenames": [None]}):
        with pytest.raises(ValueError):
            S.resolve_images(bad)


def test_resolve_source_connait_images_et_le_dit():
    from app.services import sprite_service as S
    _carre("rs.png", (1, 2, 3, 255))
    r = asyncio.run(S.resolve_source({"kind": "images", "filenames": ["rs.png"]}))
    assert isinstance(r, list) and r[0].name == "rs.png"
    with pytest.raises(ValueError, match="images"):
        asyncio.run(S.resolve_source({"kind": "gif"}))


def test_la_feuille_vient_des_images_sans_ffmpeg():
    from app.config import settings
    from app.services import sprite_service as S
    S._extract_frames = None               # ffmpeg INTERDIT : un appel planterait
    S._ffprobe_duration = None
    noms = [_carre(f"f{i}.png", (40 * i + 40, 30, 30, 255)) for i in range(4)]
    r = _run({"source": {"kind": "images", "filenames": noms}, "remove_bg": "none", "cell": {"size": 128}}, "j-img")
    d = settings.outputs_path / "sprites" / "j-img"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["source"]["kind"] == "images" and m["source"]["file"] == "f0.png" and m["source"]["duration_s"] == 0
    assert len(m["frames"]) == 4 and r["frames"] == 4
    with Image.open(d / "sheet.png") as sh:
        assert sh.size == (256, 256)                 # 2×2 cellules de 128
        px = sh.convert("RGBA").getpixel((64, 64))
    assert px[3] == 255 and px[0] == 40               # frame 0 au centre de sa cellule
    assert not (d / "_raw").exists()


def test_l_ordre_des_images_est_celui_demande_et_max_frames_echantillonne():
    from app.config import settings
    noms = [_carre(f"o{i}.png", (10 + i, 0, 0, 255)) for i in range(6)]
    _run({"source": {"kind": "images", "filenames": list(reversed(noms))}, "cell": {"size": 128},
          "max_frames": 4}, "j-ord")
    d = settings.outputs_path / "sprites" / "j-ord"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert len(m["frames"]) == 4 and m["source"]["sampled"] is True and m["source"]["file"] == "o5.png"
    with Image.open(d / "frames" / "000.png") as f0:
        assert f0.convert("RGBA").getpixel((64, 64))[0] == 15         # la PREMIÈRE demandée : o5


def test_la_route_accepte_images_et_titre_le_job():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db
    noms = [_carre(f"r{i}.png", (90, 90, 90, 255)) for i in range(2)]

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            bad = await c.post("/api/assets/sprite", json={"source": {"kind": "images", "filenames": ["../x.png"]}})
            ok = await c.post("/api/assets/sprite", json={"source": {"kind": "images", "filenames": noms},
                                                          "cell": {"size": 128}})
            jid = ok.json().get("job_id")
            j = (await c.get(f"/api/jobs/{jid}")).json()
        return bad.status_code, ok.status_code, j
    bad, ok, j = asyncio.run(main())
    assert bad == 400 and ok == 200, (bad, ok)
    assert j["title"] == "Sprites · r0" and j["status"] == "done", j


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
