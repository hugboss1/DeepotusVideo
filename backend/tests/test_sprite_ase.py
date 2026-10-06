"""T109 (plan-sprites T4, P3b) — le .ase, LU OCTET PAR OCTET.

Banc-miroir binaire : le lecteur ci-dessous ne connaît pas notre écrivain, il suit la spécification (relue le
06/10/2026 : en-tête 128 o, images 16 o, chunks dont la taille COMPREND leur en-tête) et retombe sur ses pieds —
`assert off == len(d)` attrape une taille de chunk fausse, celle qu'un `assert magic == 0xA5E0` laisserait passer.

Run: python tests/test_sprite_ase.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import struct
import sys
import tempfile
import zlib

_tmp = tempfile.mkdtemp(prefix="dzspa_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = ""
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TETE = "<IHHHHHIHIIB3sHBBhhHH84s"
IMG = "<IHHH2sI"
TAGS = [{"name": "idle", "from": 0, "to": 1, "direction": "forward", "repeat": 0},
        {"name": "run", "from": 2, "to": 3, "direction": "pingpong", "repeat": 3}]


def _png(nom, couleur, taille=(20, 20)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([2, 2, taille[0] - 3, taille[1] - 3], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def lire_ase(d: bytes) -> dict:
    assert struct.calcsize(TETE) == 128 and struct.calcsize(IMG) == 16
    (taille, magic, n, w, h, depth, flags, vitesse, z1, z2, transp, _ign,
     ncolors, pw, ph, gx, gy, gw, gh, _fut) = struct.unpack(TETE, d[:128])
    assert taille == len(d), (taille, len(d))
    off, images = 128, []
    for _ in range(n):
        fb, fmagic, vieux, duree, _r, nchunks = struct.unpack(IMG, d[off:off + 16])
        assert fmagic == 0xF1FA and vieux == nchunks
        q, chunks = off + 16, []
        for _ in range(nchunks):
            csize, ctype = struct.unpack("<IH", d[q:q + 6])
            assert csize >= 6
            chunks.append((ctype, d[q + 6:q + csize]))
            q += csize
        assert q == off + fb, (q, off, fb)
        images.append({"duree": duree, "chunks": chunks})
        off += fb
    assert off == len(d), (off, len(d))
    return {"magic": magic, "n": n, "w": w, "h": h, "depth": depth, "flags": flags, "z": (z1, z2),
            "ncolors": ncolors, "px": (pw, ph), "images": images}


def lire_string(b: bytes, off: int):
    (ln,) = struct.unpack("<H", b[off:off + 2])
    return b[off + 2:off + 2 + ln].decode("utf-8"), off + 2 + ln


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"s{i}.png", (60 + 50 * i, 30, 160, 255)) for i in range(4)]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
                                    "columns": 2, "fps_sample": 10}, "j-ase"))
    return settings.outputs_path / "sprites" / "j-ase"


def test_l_en_tete_et_les_durees_tirees_du_fps(dossier):
    a = lire_ase((dossier / "sheet.ase").read_bytes())
    assert a["magic"] == 0xA5E0 and a["n"] == 4 and a["w"] == 128 and a["h"] == 128
    assert a["depth"] == 32 and a["ncolors"] == 0            # 32 bpp : pas de palette
    assert a["z"] == (0, 0) and a["px"] == (1, 1)
    assert [f["duree"] for f in a["images"]] == [100] * 4     # 10 i/s, pas de durée par image
    types = {t for f in a["images"] for t, _ in f["chunks"]}
    assert types & {0x2019, 0x0004, 0x0011} == set()           # aucun chunk de palette


def test_l_image_zero_porte_le_calque_et_le_cel_sans_tags(dossier):
    a = lire_ase((dossier / "sheet.ase").read_bytes())
    assert [t for t, _ in a["images"][0]["chunks"]] == [0x2004, 0x2005]
    assert [t for t, _ in a["images"][1]["chunks"]] == [0x2005]
    calque = dict(a["images"][0]["chunks"])[0x2004]
    dr, typ, niv, _lw, _lh, fusion, opac = struct.unpack("<HHHHHHB", calque[:13])
    assert (dr, typ, niv, fusion, opac) == (3, 0, 0, 0, 255)
    nom, fin = lire_string(calque, 16)
    assert nom == "Layer 1" and fin == len(calque)


def test_le_cel_decompresse_donne_les_pixels_de_la_case(dossier):
    a = lire_ase((dossier / "sheet.ase").read_bytes())
    cel = dict(a["images"][2]["chunks"])[0x2005]
    couche, x, y, opac, ctype, z = struct.unpack("<HhhBHh", cel[:11])
    assert (couche, x, y, opac, ctype, z) == (0, 0, 0, 255, 2, 0)
    w, h = struct.unpack("<HH", cel[16:20])
    assert (w, h) == (128, 128)
    brut = zlib.decompress(cel[20:])
    assert len(brut) == w * h * 4
    with Image.open(dossier / "frames" / "002.png") as case:
        assert brut == case.convert("RGBA").tobytes()


def test_les_tags_et_les_durees_par_image_quand_il_y_en_a():
    from app.services import sprite_export as SE
    cases = [Image.new("RGBA", (8, 8), (i * 40, 0, 0, 255)) for i in range(4)]
    a = lire_ase(SE.aseprite_bytes(cases, [100, 100, 200, 200], TAGS))
    assert [f["duree"] for f in a["images"]] == [100, 100, 200, 200]
    assert [t for t, _ in a["images"][0]["chunks"]] == [0x2004, 0x2005, 0x2018]
    assert all([t for t, _ in f["chunks"]] == [0x2005] for f in a["images"][1:])     # les tags : image 0 SEULEMENT
    tg = dict(a["images"][0]["chunks"])[0x2018]
    (ntags,) = struct.unpack("<H", tg[:2])
    off, lus = 10, []
    for _ in range(ntags):
        de, a_, sens, rep = struct.unpack("<HHBH", tg[off:off + 7])
        nom, off = lire_string(tg, off + 17)
        lus.append((nom, de, a_, sens, rep))
    assert lus == [("idle", 0, 1, 0, 0), ("run", 2, 3, 2, 3)] and off == len(tg)


def test_les_refus_de_l_ecrivain():
    from app.services import sprite_export as SE
    with pytest.raises(ValueError):
        SE.aseprite_bytes([], [])
    with pytest.raises(ValueError):
        SE.aseprite_bytes([Image.new("RGBA", (8, 8))], [100, 100])
    with pytest.raises(ValueError, match="canvas"):
        SE.aseprite_bytes([Image.new("RGBA", (8, 8)), Image.new("RGBA", (9, 8))], [100, 100])


def test_une_chaine_non_ascii_est_comptee_en_octets():
    from app.services import sprite_export as SE
    s = SE._ase_string("héros")
    assert s[:2] == (6).to_bytes(2, "little") and s[2:].decode("utf-8") == "héros"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
