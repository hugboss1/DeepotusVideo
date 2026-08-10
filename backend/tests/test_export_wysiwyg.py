# -*- coding: utf-8 -*-
"""« Ce que l'ecran montre est ce que l'archive contient » — ronde 5.

Trois defauts mesures sur l'API qui tournait, verrouilles ici.

1. LE GLB LIVRE N'ETAIT PAS CELUI QU'ON REGARDAIT. `/preview.glb` posait
   l'echelle de matiere du maillage (sphere : UV 0..4 x 0..2, une tuile ~ une
   unite monde) ; `/export?format=glb` sortait les memes textures sur des UV
   0..1 et un maillage fige sur "sphere". Le fichier telecharge montrait donc
   une tuile etiree la ou le lab en montrait huit — et un tore choisi a l'ecran
   partait en sphere, pendant que le bordereau chiffrait « geometrie torus ».
   Verifie : apercu et export sont OCTET POUR OCTET le meme GLB, et le maillage
   demande est celui qui sort.

2. LE BORDEREAU FACTURAIT UNE IMAGE ABSENTE. En GLB/glTF il listait `ao.png`
   alors que gltf_builder lit l'occlusion dans le canal R de l'ORM et n'embarque
   pas d'AO separee : 4,71 Mo annonces pour 4,19 Mo livres.

3. LE POIDS « MESURE » NE L'ETAIT PAS. Les entrees prenaient la taille du PNG
   SUR DISQUE, alors que l'export livre la map APRES `bake_levels` : sur une
   matiere dielectrique, `metallic.png` passe de 319 556 o (le motif derive) a
   1 097 o (un uni), et le bordereau annoncait le premier en se declarant
   « exact ». Verifie : un uni est encode pour de vrai, et rien ne se declare
   exact quand la cuisson reecrit les pixels.

Run : <embedded python> backend/tests/test_export_wysiwyg.py
"""
import asyncio
import io
import json
import os
import pathlib
import struct
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                        # noqa: E402
from httpx import AsyncClient, ASGITransport                 # noqa: E402

from app.main import app                                     # noqa: E402
import app.services.material_store as MS                     # noqa: E402
import app.services.pbr_service as PBR                       # noqa: E402


def _motif(w=512):
    """Une image qui a du grain (sinon toutes les maps sont uniformes et le
    test ne mesure plus rien)."""
    im = Image.new("RGB", (w, w))
    px = im.load()
    for y in range(w):
        for x in range(w):
            v = (x * 7 + y * 13) % 97 + ((x * x + y * y) % 61)
            px[x, y] = (v % 256, (v * 3) % 256, (v * 5) % 256)
    return im


def _glb_json(blob: bytes):
    assert blob[:4] == b"glTF", "pas un GLB"
    ln = struct.unpack("<I", blob[12:16])[0]
    return json.loads(blob[20:20 + ln].decode("utf-8"))


async def main():
    mat = MS.create_material(name="or martelé", res=512)
    mid = mat["id"]
    MS.save_maps(mid, PBR.derive_maps(_motif(), None, list(MS.MAP_KINDS)))
    mat = MS.read_material(mid)
    mat["props"]["metallic"] = 1.0
    mat["props"]["roughness"] = 0.25
    mat = MS.refresh_report(mat)
    MS.write_material(mat)

    tr = ASGITransport(app=app)
    async with AsyncClient(transport=tr, base_url="http://t") as c:

        # ─── 1. l'apercu et l'export sont LE MEME fichier ──────────────────
        for mesh in ("sphere", "torus", "plane", "tiled"):
            p = await c.get(f"/api/materials/{mid}/preview.glb"
                            f"?mesh={mesh}&res=512&scale=1&stage=0")
            e = await c.get(f"/api/materials/{mid}/export"
                            f"?format=glb&res=512&mesh={mesh}")
            assert p.status_code == 200 and e.status_code == 200
            assert p.content == e.content, (
                f"{mesh} : l'apercu et l'export ne livrent pas le meme GLB "
                f"({len(p.content)} vs {len(e.content)} octets)")
            j = _glb_json(e.content)
            assert j["meshes"][0]["name"] == mesh, j["meshes"][0]["name"]

        # un maillage inconnu est refuse, pas remplace en silence
        r = await c.get(f"/api/materials/{mid}/export?format=glb&mesh=donut")
        assert r.status_code == 400, r.status_code

        # ─── 2. le bordereau GLB ne liste que ce que le GLB embarque ───────
        r = await c.get(f"/api/materials/{mid}/export/manifest"
                        f"?format=glb&res=512&mesh=sphere")
        man = r.json()
        listed = {e["kind"] for e in man["entries"]}
        assert "orm" in listed
        assert "ao" not in listed, "ao.png annoncee alors que l'ORM porte l'occlusion"
        glb = (await c.get(f"/api/materials/{mid}/export"
                           f"?format=glb&res=512&mesh=sphere")).content
        j = _glb_json(glb)
        assert len(j["images"]) == len(listed), (
            f"{len(listed)} images annoncees, {len(j['images'])} embarquees")
        ecart = abs(man["total_bytes"] - len(glb)) / len(glb)
        assert ecart < 0.15, f"bordereau GLB a {ecart:.0%} du fichier reel"

        # ─── 3. plus aucun poids « mesure » quand la cuisson reecrit ───────
        r = await c.get(f"/api/materials/{mid}/export/manifest"
                        f"?format=zip&naming=standard&res=512&bits=8")
        man = r.json()
        assert man["exact"] is False, (
            "le bordereau se declare mesure alors que bake_levels reecrit "
            "metallic / roughness / orm avant de les ecrire dans l'archive")
        by = {e["kind"]: e for e in man["entries"]}
        # la rugosite et l'ORM gardent du motif apres cuisson : leur poids
        # reste une extrapolation, et le bordereau le dit.
        for kind in ("roughness", "orm"):
            assert by[kind]["exact"] is False, kind

        # Une map devenue UNIFORME est encodee pour de vrai : la taille
        # annoncee est celle du PNG uni, a l'octet pres.
        #
        # ELLE RESTE POURTANT MARQUEE « ~ », ET C'EST LA REGLE QUI L'EXIGE.
        # La regle publiee (material_store.WEIGH_RULE) est : mesure = le
        # fichier qui part existe deja, encode, sur le disque. Ici il n'existe
        # pas — il nait de bake_levels a l'export — et « uniforme » veut dire
        # « a FLAT_SPAN niveaux pres », pas « strictement plat ». Se declarer
        # exact serait l'exception qui rendait le marqueur illisible : trois
        # fichiers 8 bits en « ~ » a cote d'un quatrieme, 8 bits lui aussi,
        # donne comme exact, sans rien qui les separe. Le CHIFFRE reste le bon,
        # seule l'etiquette dit la verite sur sa provenance.
        buf = io.BytesIO()
        Image.new("L", (512, 512), 255).save(buf, format="PNG")
        assert MS._flat_png_size(512, "L", 255) == buf.tell()
        assert by["metallic"]["exact"] is False
        assert "cuit" in by["metallic"]["weigh_tag"], by["metallic"]["weigh_tag"]
        assert by["metallic"]["bytes"] == buf.tell(), (
            f"metallic uni annonce {by['metallic']['bytes']} o "
            f"pour {buf.tell()} o reels")
        # ... et surtout : plus du tout la taille du MOTIF sur disque
        disque = (MS.material_dir(mid) / "metallic.png").stat().st_size
        assert by["metallic"]["bytes"] < disque / 4, (
            f"toujours le poids du fichier sur disque ({disque} o)")

    print("OK — apercu == export (4 maillages), bordereau GLB sans image "
          "fantome, aucun poids annonce mesure quand la cuisson reecrit")


asyncio.run(main())
