# -*- coding: utf-8 -*-
"""Material Forge P3 — UN BANC PAR CONVENTION, et il lit l'ARCHIVE.

Ce banc ne demande jamais à `material_store` ce qu'il a écrit : il télécharge
le ZIP par la route, l'ouvre, et confronte les noms de fichiers, les canaux de
l'ORM, ceux du MaskMap et le signe Y de la normale à une table LITTÉRALE,
écrite ici. Dériver la table de `_NAMING_PATTERNS` reviendrait à vérifier le
module contre lui-même : un renommage passerait au vert.

Six conventions : standard, blender, unity_urp, unity_hdrp, unreal, godot.

Run (depuis backend/) : python tests/test_material_naming_archive.py
"""
import asyncio
import io
import os
import pathlib
import sys
import tempfile
import types
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402
from httpx import ASGITransport, AsyncClient                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [], "seed": 0}


_stub.subscribe_async = _sub
sys.modules["fal_client"] = _stub

from app.main import app                                       # noqa: E402
from app.services import material_store as MS                  # noqa: E402
from app.services import pbr_service as PBR                    # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


# LA TABLE, ÉCRITE À LA MAIN. C'est le contrat publié : si le module change un
# nom, ce banc doit rougir, pas suivre.
N = "Pierre_bleue"          # la casse du nom est GARDÉE par l export (le plan disait pierre_bleue)
ATTENDU = {
    "standard": {
        "basecolor": f"{N}_basecolor.png", "normal": f"{N}_normal.png",
        "roughness": f"{N}_roughness.png", "metallic": f"{N}_metallic.png",
        "ao": f"{N}_ao.png", "height": f"{N}_height.png",
        "emissive": f"{N}_emissive.png", "orm": f"{N}_orm.png"},
    "blender": {
        "basecolor": f"{N}_base_color.png", "normal": f"{N}_normal_gl.png",
        "roughness": f"{N}_roughness.png", "metallic": f"{N}_metallic.png",
        "ao": f"{N}_ao.png", "height": f"{N}_height.png",
        "emissive": f"{N}_emission.png"},
    "unity_urp": {
        "basecolor": f"{N}_BaseMap.png", "normal": f"{N}_Normal.png",
        "maskmap": f"{N}_MetallicOcclusion.png", "height": f"{N}_Height.png",
        "emissive": f"{N}_Emission.png"},
    "unity_hdrp": {
        "basecolor": f"{N}_BaseMap.png", "normal": f"{N}_Normal.png",
        "maskmap": f"{N}_MaskMap.png", "height": f"{N}_Height.png",
        "emissive": f"{N}_Emissive.png"},
    "unreal": {
        "basecolor": f"T_{N}_BC.png", "normal": f"T_{N}_N.png",
        "orm": f"T_{N}_ORM.png", "height": f"T_{N}_H.png",
        "emissive": f"T_{N}_E.png"},
    "godot": {
        "basecolor": f"{N}_albedo.png", "normal": f"{N}_normal.png",
        "orm": f"{N}_orm.png", "height": f"{N}_height.png",
        "emissive": f"{N}_emission.png"},
}

AO, ROUGH, METAL = 200, 0.70, 0.40      # constantes distinctes : un canal
                                        # interverti se voit immédiatement


def _plate(v, mode="L", taille=64):
    return Image.new(mode, (taille, taille), v)


def _fabriquer():
    """Une matière dont CHAQUE canal porte une constante différente, plus une
    normale VRAIMENT dérivée (pour que le signe Y ait un sens)."""
    mat = MS.create_material(
        name="Pierre bleue", prompt="blue stone",
        full_prompt=MS.build_full_prompt("blue stone"),
        source={"kind": "prompt", "model": "flux", "filename": None},
        res=64, seamless=True, seam={"before": 9.0, "after": 0.0})
    bosse = Image.new("L", (64, 64), 40)
    px = bosse.load()
    for y in range(20, 44):
        for x in range(64):
            px[x, y] = 40 + int(180 * (1.0 - abs(y - 32) / 12.0))
    gl = PBR.derive_maps(bosse.convert("RGB"), {"normal_invert_y": False},
                         ["normal"])["normal"]
    dx = PBR.derive_maps(bosse.convert("RGB"), {"normal_invert_y": True},
                         ["normal"])["normal"]
    maps = {"basecolor": _plate((60, 90, 150), "RGB"), "normal": gl,
            "roughness": _plate(int(ROUGH * 255)),
            "metallic": _plate(int(METAL * 255)), "ao": _plate(AO),
            "height": bosse, "emissive": _plate((0, 0, 0), "RGB"),
            "orm": Image.merge("RGB", (_plate(AO), _plate(int(ROUGH * 255)),
                                       _plate(int(METAL * 255))))}
    MS.save_maps(mat["id"], maps)
    mat = MS.read_material(mat["id"])
    mat["props"] = MS.merge_props(mat["props"], {"roughness": ROUGH,
                                                 "metallic": METAL})
    MS.write_material(mat)
    return MS.read_material(mat["id"]), gl, dx


async def main():
    global PASS
    mat, gl, dx = _fabriquer()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           timeout=120) as c:

        # ══ 1 · la liste publiée ═══════════════════════════════════════════
        d = (await c.get("/api/materials/namings")).json()
        ids = [n["id"] for n in d["namings"]]
        assert ids == ["standard", "blender", "unity_urp", "unity_hdrp",
                       "unreal", "godot"], ids
        par_id = {n["id"]: n for n in d["namings"]}
        bl = par_id["blender"]
        assert "Principled BSDF" in bl["label"], bl["label"]
        for mot in ("Non-Color", "OpenGL", "Emission Strength",
                    "Separate Color"):
            assert mot in bl["note"], (mot, bl["note"])
        assert "Blender" not in par_id["standard"]["label"], \
            "« standard » ne doit plus s'annoncer comme la cible Blender"
        ok("GET /materials/namings : six conventions, Blender nommée, sa note "
           "cite Non-Color, OpenGL, Emission Strength et Separate Color")

        # ══ 2 · l'ARCHIVE de chaque convention ═════════════════════════════
        for nom, attendu in ATTENDU.items():
            r = await c.get(f"/api/materials/{mat['id']}/export"
                            f"?format=zip&naming={nom}")
            assert r.status_code == 200, (nom, r.text)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                dedans = set(z.namelist())
                images = {n for n in dedans if n.lower().endswith(".png")
                          and n != "thumb.png"}
                assert images == set(attendu.values()), (nom, sorted(images))
                assert {"material.json", "LISEZMOI.txt"} <= dedans, nom
                lisez = z.read("LISEZMOI.txt").decode("utf-8")
                assert "OpenGL" in lisez, nom
                # « standard » est NEUTRE : aucun moteur, donc aucun emplacement
                # à nommer (le plan exigeait des flèches partout — faux pour lui)
                fleches = [l for l in lisez.splitlines()
                           if " -> " in l and "avant/après" not in l]
                if nom == "standard":
                    assert not fleches and "Où déposer" not in lisez, fleches
                else:
                    assert len(fleches) >= len(images) - 1, (nom, fleches)

                if "orm" in attendu:
                    with Image.open(io.BytesIO(z.read(attendu["orm"]))) as im:
                        r_, g_, b_ = im.convert("RGB").split()
                    assert r_.getpixel((3, 3)) == AO, (nom, "R != AO")
                    assert abs(g_.getpixel((3, 3)) - ROUGH * 255) <= 2, nom
                    assert abs(b_.getpixel((3, 3)) - METAL * 255) <= 2, nom
                if "maskmap" in attendu:
                    with Image.open(io.BytesIO(z.read(attendu["maskmap"]))) as im:
                        assert im.mode == "RGBA", (nom, im.mode)
                        mr, mg, mb, ma = im.split()
                    assert abs(mr.getpixel((3, 3)) - METAL * 255) <= 2, nom
                    assert mg.getpixel((3, 3)) == AO, (nom, "V != occlusion")
                    assert mb.getpixel((3, 3)) == 0, (nom, "B != détail")
                    assert abs(ma.getpixel((3, 3)) - (255 - ROUGH * 255)) <= 2, nom
                # LE SIGNE Y, épinglé par son TÉMOIN : la même normale dérivée
                # en DirectX est le miroir exact autour de 128.
                # L'export REMONTE une matière de 64 px à la résolution minimale
                # (512, mesuré) : le pixel (x, y) de la carte source devient le
                # centre du bloc k x k livré. Le plan comparait aux coordonnées
                # brutes et lisait donc la zone plate (128 partout).
                with Image.open(io.BytesIO(z.read(attendu["normal"]))) as im:
                    livre = im.convert("RGB").split()[1]
                k = livre.size[0] // gl.size[0]
                assert k >= 1 and livre.size[0] == k * gl.size[0], livre.size
                for xy in ((7, 26), (7, 38), (31, 24)):
                    xyl = (xy[0] * k + k // 2, xy[1] * k + k // 2)
                    v, a, b = (livre.getpixel(xyl), gl.split()[1].getpixel(xy),
                               dx.split()[1].getpixel(xy))
                    assert abs(v - a) <= 6, (nom, xy, v, a)
                    assert abs(v - b) > 40, (nom, xy, v, b, "signe Y inversé ?")
                    assert abs((a + b) - 256) <= 2, (nom, xy, a, b)
            ok(f"archive « {nom} » : {len(images)} PNG aux noms exacts, "
               f"canaux et signe Y vérifiés dans les octets livrés")

        # ══ 3 · Blender ne livre PAS d'ORM par défaut, et le dit ═══════════
        r = await c.get(f"/api/materials/{mat['id']}/export/manifest"
                        f"?format=zip&naming=blender")
        m = r.json()
        # le bordereau liste TOUTES les cartes (`entries`), chacune avec son
        # drapeau `selected` — le plan lisait une clé `files` qui n'existe pas
        roles = {e["kind"]: e for e in m["entries"]}
        assert "orm" in roles and not roles["orm"]["selected"], roles["orm"]
        assert "orm" not in m["default_maps"], m["default_maps"]
        assert "Multiply" in roles["ao"]["slot"] or \
               "multiplier" in roles["ao"]["slot"].lower(), roles["ao"]["slot"]
        assert "Non-Color" in roles["roughness"]["slot"], roles["roughness"]
        assert "Emission Strength" in roles["emissive"]["slot"], roles["emissive"]
        ok("bordereau Blender : pas d'ORM par défaut (le Principled BSDF n'a "
           "pas d'entrée pour lui), l'AO se multiplie, les cartes de données "
           "sont en Non-Color")

    print(f"\nOK — {PASS} assertions groupées vertes (conventions d'export, "
          f"lues dans l'archive)")


asyncio.run(main())
