"""T110 (plan-sprites T2, P2) — tags d'animation et durée par image : le manifeste les porte, le GIF d'aperçu porte une
durée PAR IMAGE, les quatre exports de T109 les lisent, et les bornes refusent en le disant — à la route (n inconnu)
puis dans _assemble (n réel, après la sélection du filmstrip).

Run: python tests/test_sprite_anim.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzsan_")
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
import struct  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
TAGS = [{"name": "idle", "from": 0, "to": 2, "direction": "forward"},
        {"name": "run", "from": 3, "to": 5, "direction": "pingpong", "repeat": 3}]
DUREES = [80, 80, 80, 150, 150, 150]


def _png(nom, couleur, taille=(24, 24)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([2, 2, taille[0] - 3, taille[1] - 3], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def test_normalize_anim_borne_tout_ce_qui_entre():
    from app.services import sprite_anim as A
    ok = A.normalize_anim({"tags": TAGS, "durations": DUREES}, 6)
    assert [t["name"] for t in ok["tags"]] == ["idle", "run"]
    assert ok["tags"][1]["direction"] == "pingpong" and ok["tags"][1]["repeat"] == 3
    assert ok["tags"][0]["repeat"] == 0          # défaut : boucle infinie
    assert ok["durations"] == DUREES
    assert A.normalize_anim(None, 6, fps=8)["durations"] == [125] * 6
    assert A.normalize_anim(None, None, fps=8)["durations"] is None       # n inconnu : pas de durées inventées
    assert A.normalize_anim({"durations": DUREES}, None)["durations"] == DUREES
    assert A.spans({"tags": []}, 4) == [("default", 0, 3)]
    assert A.spans(ok, 6) == [("idle", 0, 2), ("run", 3, 5)]
    mauvais = [
        {"tags": [{"name": "idle", "from": 0, "to": 6}]},       # to >= n
        {"tags": [{"name": "idle", "from": 3, "to": 1}]},       # from > to
        {"tags": [{"name": "", "from": 0, "to": 1}]},           # nom vide
        {"tags": [{"name": "a/b", "from": 0, "to": 1}]},        # nom sale
        {"tags": [{"name": "x", "from": 0, "to": 1}, {"name": "x", "from": 2, "to": 3}]},   # doublon
        {"tags": [{"name": "x", "from": 0, "to": 1, "direction": "spin"}]},                # sens inconnu
        {"tags": [{"name": f"t{i}", "from": 0, "to": 1} for i in range(17)]},              # 17 > 16
        {"tags": [{"name": "x", "from": 0, "to": 1, "repeat": 70000}]},                    # repeat > 65535
        {"tags": [{"name": "x", "from": "a", "to": 1}]},                                   # from non entier
        {"durations": [80] * 5},                                # mauvaise longueur
        {"durations": [80] * 5 + [9]},                          # 9 ms < 10
        {"durations": [80] * 5 + [10001]},                      # > 10 000 ms
        {"durations": "80"},                                    # pas une liste
        {"tags": "idle"},                                       # pas une liste
        {"tags": ["idle"]},                                     # pas un objet
        "idle",                                                 # anim pas un objet
    ]
    for m in mauvais:
        with pytest.raises(ValueError):
            A.normalize_anim(m, 6)


def test_le_manifeste_le_gif_et_les_exports_portent_les_tags_et_les_durees():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"a{i}.png", (30 + 40 * i, 90, 200, 255)) for i in range(6)]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
                                    "columns": 3, "fps_sample": 8, "anim": {"tags": TAGS, "durations": DUREES}},
                                   "j-anim"))
    d = settings.outputs_path / "sprites" / "j-anim"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["version"] == 2
    assert [t["name"] for t in m["anim"]["tags"]] == ["idle", "run"] and m["anim"]["durations"] == DUREES
    assert [f["duration_ms"] for f in m["frames"]] == DUREES
    lues = []
    with Image.open(d / "preview.gif") as g:            # le GIF, LU : 80 et 150 sont des multiples de 10
        assert g.n_frames == 6
        for i in range(g.n_frames):
            g.seek(i)
            lues.append(g.info["duration"])
    assert lues == DUREES
    tres = (d / "sheet.tres").read_text("utf-8")        # T109 lit enfin les tags
    assert '&"idle"' in tres and '&"run"' in tres and '&"default"' not in tres
    assert tres.count('"duration": 0.64') == 3 and tres.count('"duration": 1.2') == 3     # 80 / 150 ms à 8 i/s
    atlas = json.loads((d / "sheet.atlas.json").read_text("utf-8"))
    assert [t["name"] for t in atlas["meta"]["frameTags"]] == ["idle", "run"]
    ase = (d / "sheet.ase").read_bytes()
    off, durees = 128, []
    for _ in range(6):
        fb, _mg, _v, dur, _r, _n = struct.unpack("<IHHH2sI", ase[off:off + 16])
        durees.append(dur)
        off += fb
    assert durees == DUREES


def test_sans_anim_la_duree_vient_du_fps_et_le_gif_garde_son_plancher():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"f{i}.png", (200, 20 * i, 40, 255)) for i in range(3)]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
                                    "fps_sample": 24, "anim": {"durations": [10, 10, 10]}}, "j-vite"))
    d = settings.outputs_path / "sprites" / "j-vite"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert [f["duration_ms"] for f in m["frames"]] == [10, 10, 10]      # le manifeste dit la VRAIE durée
    with Image.open(d / "preview.gif") as g:
        assert g.info["duration"] == 20                                  # sous 20 ms, les navigateurs imposent 20


def test_un_tag_qui_deborde_la_selection_du_filmstrip_est_refuse():
    """La route valide AVANT de connaître le nombre d'images (n=None, borne à 64) ; `keep` peut ensuite réduire la
    feuille à 3 images. Sans le second appel dans _assemble, le tag `run` 3-5 passerait et Godot lirait une animation
    vide."""
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"b{i}.png", (200, 40 * i + 30, 60, 255)) for i in range(6)]
    S.normalize_opts({"source": {"kind": "images", "filenames": noms}, "anim": {"tags": TAGS}})   # passe
    with pytest.raises(ValueError) as e:
        asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "keep": [0, 1, 2],
                                        "cell": {"size": 128}, "anim": {"tags": TAGS}}, "j-deborde"))
    assert "run" in str(e.value) and "to < 3" in str(e.value)
    assert not (settings.outputs_path / "sprites" / "j-deborde" / "sheet.png").is_file()


def test_la_route_refuse_une_forme_fausse_en_400():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db
    noms = [_png(f"r{i}.png", (9, 9, 9, 255)) for i in range(2)]

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/api/assets/sprite", json={"source": {"kind": "images", "filenames": noms},
                                                         "anim": {"tags": [{"name": "a/b", "from": 0, "to": 1}]}})
            return r.status_code, r.text
    st, txt = asyncio.run(main())
    assert st == 400 and "a/b" in txt, (st, txt)


def test_l_ecran_porte_le_fieldset_animation_et_l_envoie():
    html = (RACINE / "frontend" / "spritelab" / "index.html").read_text(encoding="utf-8")
    js = (RACINE / "frontend" / "spritelab" / "spritelab.js").read_text(encoding="utf-8")
    assert 'id="animMs"' in html and 'id="tagAdd"' in html and 'id="tagRows"' in html
    assert "body.anim = animOpts(kept.length);" in js
    assert '"animMs"' in js and "p.tagRows = JSON.stringify(tagRows);" in js


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
