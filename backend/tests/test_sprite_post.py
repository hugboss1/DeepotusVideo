"""T110 (plan-sprites T6, P4) — contour, ombre, nettoyage : les PIXELS du résultat, relus en PIL. Le post tourne
APRÈS le pixel-art (1 px natif) et AVANT _assemble (qui mesure la cellule native sur des images déjà agrandies).

Run: python tests/test_sprite_post.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspo_")
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
ROUGE = (220, 40, 40, 255)


def _sujet():
    """20x20 : un carré plein 8x8 en (6,6)-(13,13), un TROU d'un pixel en (10,10), et un pixel ORPHELIN en (18,1)."""
    im = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([6, 6, 13, 13], fill=ROUGE)
    im.putpixel((10, 10), (0, 0, 0, 0))
    im.putpixel((18, 1), ROUGE)
    return im


def test_normalize_post_refuse_ce_qui_sort_des_bornes():
    from app.services import sprite_post as P
    assert P.normalize_post(None) is None
    assert P.normalize_post({}) is None
    assert P.normalize_post({"clean": {"orphans": False, "smooth": False}}) is None    # rien demandé : pas de passe
    o = P.normalize_post({"outline": {"width": 2, "color": "#00ff00"},
                          "shadow": {"dx": -3, "dy": 4, "opacity": 128},
                          "clean": {"orphans": True, "smooth": True}})
    assert o["outline"] == {"width": 2, "color": (0, 255, 0, 255)}
    assert o["shadow"]["dx"] == -3 and o["shadow"]["dy"] == 4 and o["shadow"]["opacity"] == 128
    assert o["shadow"]["color"] == (0, 0, 0, 255) and o["shadow"]["blur"] == 0
    assert o["clean"] == {"orphans": True, "smooth": True}
    assert P.normalize_post({"outline": {"color": "#11223344"}})["outline"] == {"width": 1, "color": (17, 34, 51, 68)}
    for m in ({"outline": {"width": 0}}, {"outline": {"width": 5}},
              {"outline": {"width": 1, "color": "vert"}},
              {"outline": {"width": 1, "color": "#12345"}},
              {"outline": {"width": 1, "color": "#1234567"}},
              {"shadow": {"dx": 33}}, {"shadow": {"dy": -33}},
              {"shadow": {"dx": 1, "blur": 9}},
              {"shadow": {"dx": 1, "opacity": 300}},
              {"shadow": {"dx": "a"}},
              {"outline": "1"}, {"shadow": "1"}, {"clean": "yes"}, "post"):
        with pytest.raises(ValueError):
            P.normalize_post(m)


def test_l_outline_est_un_anneau_d_un_pixel_et_l_orphelin_disparait():
    from app.services import sprite_post as P
    o = P.normalize_post({"outline": {"width": 1, "color": "#00ff00"}, "clean": {"orphans": True}})
    out = P.apply_post(_sujet(), o)
    assert out.size == (22, 22)          # pad = 1 de chaque côté
    px = out.load()
    # le carré s'est décalé de (1,1) : (6,6)-(13,13) -> (7,7)-(14,14)
    assert px[10, 10] == ROUGE                     # intérieur intact
    assert px[6, 8] == (0, 255, 0, 255)            # anneau à gauche
    assert px[15, 8] == (0, 255, 0, 255)           # anneau à droite
    assert px[8, 6] == (0, 255, 0, 255)            # anneau en haut
    assert px[8, 15] == (0, 255, 0, 255)           # anneau en bas
    assert px[5, 8][3] == 0                        # rien à 2 px du bord
    # le TROU a été bouché AVANT l'outline, donc pas d'anneau vert dedans — et il a la couleur de ses voisins
    assert px[11, 11] == ROUGE
    # l'ORPHELIN (18,1) -> (19,2) a disparu, et n'a pas laissé d'anneau
    assert px[19, 2][3] == 0 and px[18, 2][3] == 0 and px[19, 3][3] == 0


def test_un_contour_de_deux_pixels_et_sans_nettoyage_l_orphelin_reste():
    from app.services import sprite_post as P
    out = P.apply_post(_sujet(), P.normalize_post({"outline": {"width": 2, "color": "#0000ff"}}))
    assert out.size == (24, 24)
    px = out.load()
    # carré -> (8,8)-(15,15) ; anneau de 2 : x = 6 et 7 à gauche, 16 et 17 à droite
    assert px[6, 10] == (0, 0, 255, 255) and px[7, 10] == (0, 0, 255, 255)
    assert px[17, 10] == (0, 0, 255, 255) and px[5, 10][3] == 0
    assert px[20, 3] == ROUGE                      # orphelin (18,1) -> (20,3), gardé
    # le trou (10,10) -> (12,12) n'est pas bouché en ROUGE : le contour y entre (anneau intérieur) — c'est pourquoi
    # le nettoyage passe AVANT le contour…
    assert px[12, 12] == (0, 0, 255, 255)
    assert px[21, 3] == (0, 0, 255, 255)           # …et l'orphelin a son anneau


def test_l_ombre_est_decalee_derriere_le_sujet():
    from app.services import sprite_post as P
    o = P.normalize_post({"shadow": {"dx": 2, "dy": 3, "color": "#000000", "opacity": 128}})
    out = P.apply_post(_sujet(), o)
    assert out.size == (26, 26)          # pad = max(|2|, |3|) = 3
    px = out.load()
    # carré (6,6)-(13,13) -> (9,9)-(16,16) ; ombre -> (11,12)-(18,19)
    assert px[18, 19] == (0, 0, 0, 128)            # ombre seule
    assert px[11, 12] == ROUGE                     # le sujet passe devant
    assert px[9, 9] == ROUGE
    assert px[8, 8][3] == 0                        # ni sujet ni ombre
    assert px[17, 11][3] == 0                      # au-dessus de l'ombre : rien (dy positif = vers le bas)


def test_une_ombre_negative_part_en_haut_a_gauche():
    from app.services import sprite_post as P
    out = P.apply_post(_sujet(), P.normalize_post({"shadow": {"dx": -2, "dy": -2, "opacity": 200}}))
    assert out.size == (24, 24)
    px = out.load()
    # carré -> (8,8)-(15,15) ; ombre -> (6,6)-(13,13)
    assert px[6, 6] == (0, 0, 0, 200)
    assert px[15, 15] == ROUGE and px[16, 16][3] == 0


def test_l_alpha_des_couleurs_est_tenu():
    """Un contour #00ff0080 a un anneau à 128 ; une ombre #00000080 d'opacité 255 aussi (alpha × opacité)."""
    from app.services import sprite_post as P
    out = P.apply_post(_sujet(), P.normalize_post({"outline": {"width": 1, "color": "#00ff0080"}}))
    assert out.load()[6, 8] == (0, 255, 0, 128)
    out = P.apply_post(_sujet(), P.normalize_post({"shadow": {"dx": 2, "dy": 3, "color": "#00000080",
                                                              "opacity": 255}}))
    assert out.load()[18, 19] == (0, 0, 0, 128)


def test_le_lissage_mange_une_dent_d_un_pixel():
    from app.services import sprite_post as P
    im = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([3, 3, 8, 8], fill=ROUGE)
    im.putpixel((9, 5), ROUGE)                     # dent d'un pixel de large
    out = P.apply_post(im, P.normalize_post({"clean": {"smooth": True}}))
    assert out.size == (12, 12)                    # pas d'outline : pad = 0
    assert out.load()[9, 5][3] == 0
    assert out.load()[6, 6] == ROUGE


def test_le_post_traverse_le_pipeline_et_le_manifeste_le_dit():
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i in range(2):
        n = f"post{i}.png"
        _sujet().save(settings.images_path / n)
        noms.append(n)
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms}, "cell": {"size": "native"}, "columns": 2,
         "post": {"outline": {"width": 1, "color": "#00ff00"}, "clean": {"orphans": True}}}, "j-post"))
    d = settings.outputs_path / "sprites" / "j-post"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["post"]["outline"]["width"] == 1
    assert m["grid"]["cell_w"] == 22            # la toile a grandi de 2 px, et la cellule native l'a MESURÉ
    with Image.open(d / "frames" / "000.png") as c:
        assert c.convert("RGBA").load()[6, 8] == (0, 255, 0, 255)
    with Image.open(d / "sheet.png") as sh:     # la feuille, pas seulement la case : 2e case, anneau gauche
        assert sh.convert("RGBA").getpixel((22 + 6, 8)) == (0, 255, 0, 255)


def test_sans_post_le_manifeste_dit_none_et_rien_ne_grandit():
    from app.config import settings
    from app.services import sprite_service as S
    _sujet().save(settings.images_path / "nopost.png")
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": ["nopost.png"]},
                                    "cell": {"size": "native"}}, "j-nopost"))
    m = json.loads((settings.outputs_path / "sprites" / "j-nopost" / "manifest.json").read_text("utf-8"))
    assert m["post"] is None and m["grid"]["cell_w"] == 20


def test_la_route_refuse_un_post_faux_en_400():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db
    _sujet().save(pathlib.Path(os.environ["IMAGES_FOLDER"]) / "r.png")

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/api/assets/sprite", json={"source": {"kind": "images", "filenames": ["r.png"]},
                                                         "post": {"outline": {"width": 9}}})
            return r.status_code, r.text
    st, txt = asyncio.run(main())
    assert st == 400 and "post.width" in txt, (st, txt)


def test_l_ecran_porte_le_fieldset_post_et_l_envoie():
    html = (RACINE / "frontend" / "spritelab" / "index.html").read_text(encoding="utf-8")
    js = (RACINE / "frontend" / "spritelab" / "spritelab.js").read_text(encoding="utf-8")
    for i in ("postOn", "poWidth", "poColor", "poDx", "poDy", "poOpacity", "poOrphans", "poSmooth"):
        assert f'id="{i}"' in html, i
    assert "const po = postOpts(); if (po) body.post = po;" in js
    assert "postOn: $(\"#postOn\").checked" in js and "syncPostSet();" in js


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
