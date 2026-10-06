"""T109 (plan-sprites T3, P3a) — le .tres Godot et l'atlas JSON Hash, LUS sur le disque, plus les routes et l'écran.

Banc-miroir : on ouvre les fichiers écrits, on y cherche les régions, les durées relatives et les noms d'animation —
jamais le code qui prétend les produire. Les tags et les durées par image sont le champ `anim` du manifeste (plan T2,
tâche t110 du suivi) : ici, de bout en bout, la feuille n'en a pas (une animation « default », durée tirée du fps) ;
les tags sont éprouvés sur un manifeste qui les porte, passé aux écrivains.

Run: python tests/test_sprite_exports.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspe_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = ""
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import zipfile  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
TAGS = [{"name": "idle", "from": 0, "to": 1, "direction": "forward", "repeat": 0},
        {"name": "run", "from": 2, "to": 3, "direction": "pingpong", "repeat": 0}]


def _png(nom, couleur, taille=(32, 32)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([3, 3, taille[0] - 4, taille[1] - 4], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"e{i}.png", (40 + 50 * i, 120, 90, 255)) for i in range(4)]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
                                    "columns": 2, "fps_sample": 8}, "j-exp"))
    return settings.outputs_path / "sprites" / "j-exp"


def _avec_tags(dossier):
    m = json.loads((dossier / "manifest.json").read_text("utf-8"))
    m["anim"] = {"tags": TAGS, "durations": [125, 125, 250, 250]}
    for f, d in zip(m["frames"], m["anim"]["durations"]):
        f["duration_ms"] = d
    return m


def test_sans_tag_le_tres_godot_porte_une_animation_default(dossier):
    txt = (dossier / "sheet.tres").read_text("utf-8")
    assert txt.startswith('[gd_resource type="SpriteFrames" ') and "format=3]" in txt
    assert "load_steps=6" in txt                       # 1 ressource + 1 ext + 4 sub
    assert 'path="res://sheet.png"' in txt
    regions = re.findall(r"region = Rect2\(([^)]*)\)", txt)
    assert regions == ["0, 0, 128, 128", "128, 0, 128, 128", "0, 128, 128, 128", "128, 128, 128, 128"]
    assert txt.count('[sub_resource type="AtlasTexture"') == 4
    assert txt.count('"name": &"default"') == 1 and txt.count('"loop": true') == 1
    assert '"speed": 8.0' in txt and txt.count('"duration": 1.0') == 4       # 125 ms à 8 i/s = 1 image


def test_avec_tags_une_animation_par_tag_et_des_durees_relatives(dossier):
    from app.services import sprite_export as SE
    txt = SE.godot_tres(_avec_tags(dossier))
    assert '&"idle"' in txt and '&"run"' in txt and '&"default"' not in txt
    assert txt.count('"duration": 1.0') == 2 and txt.count('"duration": 2.0') == 2     # 125 / 250 ms à 8 i/s
    assert txt.count('"loop": true') == 2
    bloc_run = txt.split('&"run"')[0].split('"frames": [')[-1]
    assert "Frame_002" in bloc_run and "Frame_003" in bloc_run and "Frame_000" not in bloc_run


def test_l_atlas_json_hash_a_les_champs_de_texturepacker(dossier):
    a = json.loads((dossier / "sheet.atlas.json").read_text("utf-8"))
    assert sorted(a["frames"]) == ["frame_000.png", "frame_001.png", "frame_002.png", "frame_003.png"]
    f = a["frames"]["frame_002.png"]
    assert f["frame"] == {"x": 0, "y": 128, "w": 128, "h": 128}
    assert f["rotated"] is False and f["trimmed"] is False
    assert f["spriteSourceSize"] == {"x": 0, "y": 0, "w": 128, "h": 128} and f["sourceSize"] == {"w": 128, "h": 128}
    assert f["pivot"] == {"x": 0.5, "y": 0.5}
    assert a["meta"]["image"] == "sheet.png" and a["meta"]["size"] == {"w": 256, "h": 256}
    assert a["meta"]["scale"] == "1" and a["meta"]["format"] == "RGBA8888"
    assert a["meta"]["frameTags"] == []                # pas de tags : liste vide, jamais « default » inventé
    with Image.open(dossier / "sheet.png") as sh:      # les rectangles collent à la feuille
        for i in range(4):
            r = a["frames"][f"frame_{i:03d}.png"]["frame"]
            case = sh.convert("RGBA").crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
            with Image.open(dossier / "frames" / f"{i:03d}.png") as ref:
                assert case.tobytes() == ref.convert("RGBA").tobytes()


def test_l_atlas_porte_les_tags_quand_le_manifeste_en_a(dossier):
    from app.services import sprite_export as SE
    a = SE.atlas_json_hash(_avec_tags(dossier), 256, 256)
    assert a["meta"]["frameTags"] == [{"name": "idle", "from": 0, "to": 1, "direction": "forward"},
                                      {"name": "run", "from": 2, "to": 3, "direction": "pingpong"}]


def test_l_ancrage_pieds_deplace_le_pivot_de_l_atlas():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"p{i}.png", (200, 60, 40 * i + 40, 255)) for i in range(2)]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms},
                                    "cell": {"size": 128, "align": "feet"}, "columns": 2}, "j-pied"))
    a = json.loads((settings.outputs_path / "sprites" / "j-pied" / "sheet.atlas.json").read_text("utf-8"))
    assert a["frames"]["frame_000.png"]["pivot"] == {"x": 0.5, "y": 0.0}


def test_le_nombre_godot_a_toujours_une_decimale():
    from app.services import sprite_export as SE
    assert SE._num(8) == "8.0" and SE._num(1.25) == "1.25" and SE._num(0.3333333) == "0.3333"


def test_le_zip_emporte_les_quatre_exports(dossier):
    from app.services.sprite_service import build_zip_bytes
    with zipfile.ZipFile(io.BytesIO(build_zip_bytes(dossier))) as z:
        noms = set(z.namelist())
    assert {"sheet.png", "manifest.json", "sheet.unity.json", "SpriteSheetImporter.cs", "sheet.tres",
            "sheet.atlas.json", "sheet.ase", "sheet.paper2dsprites"} <= noms


def test_les_routes_servent_chaque_export_et_le_manifeste_les_annonce(dossier):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            o["files"] = (await c.get("/api/assets/sprite/j-exp/manifest")).json()["files"]
            for nom in ("godot", "atlas", "aseprite", "paper2d"):
                r = await c.get(f"/api/assets/sprite/j-exp/{nom}")
                o[nom] = (r.status_code, r.headers.get("content-type", "").split(";")[0], r.content[:12])
                o[nom + "404"] = (await c.get(f"/api/assets/sprite/absent/{nom}")).status_code
        return o
    o = asyncio.run(main())
    assert all(o["files"][k] for k in ("godot", "atlas", "aseprite", "paper2d")), o["files"]
    assert o["godot"][0] == 200 and o["godot"][2].startswith(b"[gd_resource"), o["godot"]
    assert o["atlas"][:2] == (200, "application/json") and o["paper2d"][:2] == (200, "application/json")
    assert o["aseprite"][0] == 200 and o["aseprite"][2][4:6] == b"\xe0\xa5", o["aseprite"]
    assert all(o[k + "404"] == 404 for k in ("godot", "atlas", "aseprite", "paper2d"))


def test_un_export_telecharge_seul_nomme_la_texture_comme_le_bouton_sheet(dossier):
    """Mesuré sur 8799 : le bouton « Sheet PNG » télécharge sprites_<job>.png ; un .tres qui dirait res://sheet.png
    perdrait sa texture dans Godot. Le fichier du disque (et donc le ZIP) garde sheet.png."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async def main():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            g = (await c.get("/api/assets/sprite/j-exp/godot")).text
            a = (await c.get("/api/assets/sprite/j-exp/atlas")).json()
            p = (await c.get("/api/assets/sprite/j-exp/paper2d")).json()
        return g, a, p
    g, a, p = asyncio.run(main())
    assert 'path="res://sprites_j-exp.png"' in g and "sheet.png" not in g
    assert a["meta"]["image"] == "sprites_j-exp.png" and p["meta"]["image"] == "sprites_j-exp.png"
    assert a["meta"]["size"] == {"w": 256, "h": 256} and len(a["frames"]) == 4
    assert 'path="res://sheet.png"' in (dossier / "sheet.tres").read_text("utf-8")
    js = (RACINE / "frontend" / "spritelab" / "spritelab.js").read_text(encoding="utf-8")
    assert '$("#dlSheet").setAttribute("download", `sprites_${short}.png`);' in js


def test_l_ecran_a_les_quatre_boutons_masques_si_absents():
    html = (RACINE / "frontend" / "spritelab" / "index.html").read_text(encoding="utf-8")
    js = (RACINE / "frontend" / "spritelab" / "spritelab.js").read_text(encoding="utf-8")
    for bid, route, ext in (("dlGodot", "godot", ".tres"), ("dlAtlas", "atlas", ".atlas.json"),
                            ("dlAse", "aseprite", ".ase"), ("dlP2d", "paper2d", ".paper2dsprites")):
        assert f'id="{bid}"' in html, bid
        assert f'$("#{bid}").href = `/api/assets/sprite/${{short}}/{route}`;' in js, bid
        assert f'`sprites_${{short}}{ext}`' in js, bid
    for cle in ("godot", "atlas", "aseprite", "paper2d"):
        assert f"m.files && m.files.{cle}" in js, cle
    assert '$("#" + id).classList.toggle("hidden", !ok);' in js      # masqué quand le manifeste dit « absent »
    for bid in ("dlGodot", "dlAtlas", "dlAse", "dlP2d"):
        assert f'<a id="{bid}" class="btn hidden"' in html, bid           # caché tant qu'aucune feuille n'est montrée


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
