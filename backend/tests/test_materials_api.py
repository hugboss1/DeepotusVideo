# -*- coding: utf-8 -*-
"""Material Forge — API /api/materials et stockage disque des matières PBR.

Couvre le contrat des sections 1 à 3 du SPEC :
CRUD complet, validation stricte de `mid` (^mat_[0-9a-f]{8}$ — traversée
refusée), fusion PARTIELLE de props/derive (entrée pourrie -> défauts, jamais
de 500), listes blanches (kind de map, mesh, naming, format, bits,
seam_method, environnement), vignette, export ZIP (4 conventions de nommage +
16 bits pour height/normal), GLB/glTF, et le job de génération de bout en bout.

Les modules `pbr_service` et `gltf_builder` sont écrits en parallèle : s'ils
sont absents, un bouchon PIL/stdlib est injecté pour que l'orchestration
testée ici soit tout de même exercée (le test l'annonce dans sa sortie).

Run : <embedded python> backend/tests/test_materials_api.py
"""
import asyncio
import io
import json
import os
import pathlib
import struct
import sys
import tempfile
import types
import zipfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                       # noqa: E402
from httpx import AsyncClient, ASGITransport                # noqa: E402
import httpx as _httpx                                      # noqa: E402

# ── image de référence servie par les faux clients réseau ────────────────────
_buf = io.BytesIO()
_ref = Image.new("RGB", (512, 512))
_px = _ref.load()
for y in range(512):        # rampe NON periodique : gros raccord a corriger
    for x in range(512):
        _px[x, y] = (x * 255 // 511, y * 255 // 511,
                     (x + y) * 255 // 1022)
_ref.save(_buf, "PNG")
_PNG = _buf.getvalue()

FAL_CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    FAL_CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/out.png"}], "seed": 7}

_stub_fal = types.ModuleType("fal_client")
_stub_fal.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub_fal


class _FakeResp:
    status_code = 200
    content = _PNG
    text = ""

    def json(self):
        return {"data": []}

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kw):
        return _FakeResp()

    async def post(self, url, **kw):
        return _FakeResp()

_httpx.AsyncClient = _FakeAsyncClient          # après l'import du vrai client

# ── bouchons pbr_service / gltf_builder si les vrais ne sont pas encore là ───
STUBBED = []

try:
    import app.services.pbr_service                          # noqa: F401
except Exception:
    _pbr = types.ModuleType("app.services.pbr_service")

    def _derive_maps(base, derive, want):
        rgb = base.convert("RGB")
        lum = rgb.convert("L")
        out = {}
        for k in want:
            if k in ("normal", "emissive", "orm"):
                out[k] = Image.merge("RGB", (lum, lum, lum))
            else:
                out[k] = lum.copy()
        return out

    def _resize_maps(maps, res):
        return {k: (v if v.size == (res, res) else v.resize((res, res)))
                for k, v in maps.items()}

    _pbr.derive_maps = _derive_maps
    _pbr.resize_maps = _resize_maps
    sys.modules["app.services.pbr_service"] = _pbr
    STUBBED.append("pbr_service")

try:
    import app.services.gltf_builder                         # noqa: F401
except Exception:
    _gb = types.ModuleType("app.services.gltf_builder")

    def _build_glb(maps, props, mesh):
        bin_ = b"".join(maps.values()) or b"\x00\x00\x00\x00"
        bin_ += b"\x00" * ((4 - len(bin_) % 4) % 4)
        doc = {"asset": {"version": "2.0", "generator": "stub"},
               "scene": 0, "scenes": [{"nodes": []}], "nodes": [],
               "buffers": [{"byteLength": len(bin_)}],
               "extras": {"mesh": mesh, "maps": sorted(maps)}}
        js = json.dumps(doc).encode("utf-8")
        js += b" " * ((4 - len(js) % 4) % 4)
        total = 12 + 8 + len(js) + 8 + len(bin_)
        return (b"glTF" + struct.pack("<II", 2, total)
                + struct.pack("<II", len(js), 0x4E4F534A) + js
                + struct.pack("<II", len(bin_), 0x004E4942) + bin_)

    _gb.build_glb = _build_glb
    sys.modules["app.services.gltf_builder"] = _gb
    STUBBED.append("gltf_builder")

from app.main import app                                     # noqa: E402
from app.config import settings                              # noqa: E402
from app.services import material_store as MS                # noqa: E402

# `mid` refusés qui ATTEIGNENT la route (un seul segment d'URL) : hexa
# invalide, longueur, casse, préfixe, extension, traversée sans séparateur.
BAD_MIDS = [
    "mat_ZZZZZZZZ", "mat_1234567", "mat_123456789", "MAT_12345678",
    "mat_1234567g", "matx_12345678", "material", "mat_", "mat_..",
    "mat_ab12cd34.png", "mat_ab12cd34%20", r"C:\Windows\system32",
    "mat_%2e%2e", "..%5c..%5csecret",
]

# Traversées AVEC séparateur : elles ne doivent jamais résoudre une matière
# (elles ne matchent même plus le motif de route — vérifié ci-dessous).
TRAVERSAL_MIDS = [
    "mat_../../secret", "..%2f..%2fsecret", "mat_%2e%2e%2fetc",
    "mat_12345678/../../etc", "/etc/passwd",
]


def _make_material(name="Fer rouillé", res=512, maps=True):
    """Matière complète écrite directement par le store (chemin rapide)."""
    mat = MS.create_material(
        name=name, prompt="rusty iron",
        full_prompt=MS.build_full_prompt("rusty iron"),
        source={"kind": "prompt", "model": "flux", "filename": None},
        res=res, seamless=True, seam={"before": 12.4, "after": 1.1})
    if maps:
        base = Image.new("RGB", (res, res), (120, 70, 40))
        lum = base.convert("L")
        allm = {"basecolor": base, "normal": base.copy(),
                "emissive": base.copy(), "orm": base.copy(),
                "roughness": lum.copy(), "metallic": lum.copy(),
                "ao": lum.copy(), "height": lum.copy()}
        MS.save_maps(mat["id"], allm)
    return MS.read_material(mat["id"])


def _png_depth(data: bytes) -> tuple:
    """(profondeur, type couleur) lus dans l'IHDR."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", data[:8]
    return data[24], data[25]


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           follow_redirects=False) as c:

        # ─── 1. défauts du SPEC ─────────────────────────────────────────────
        p, d = MS.default_props(), MS.default_derive()
        assert p["color"] == "#ffffff" and p["roughness"] == 1.0
        assert p["metallic"] == 0.0 and p["ior"] == 1.5 and p["tiling"] == 1.0
        assert d["normal_strength"] == 0.8 and d["ao_radius"] == 4.0
        assert d["metallic_mode"] == "auto" and d["emissive_threshold"] == 0.85
        assert set(MS.MAP_KINDS) == {"basecolor", "normal", "roughness",
                                     "metallic", "ao", "height", "emissive",
                                     "orm"}

        # ─── 2. validation de mid au niveau du store ────────────────────────
        assert MS.is_valid_mid("mat_ab12cd34")
        for bad in ("mat_AB12CD34", "mat_ab12cd3", "mat_ab12cd345",
                    "mat_../../x", "", None, 42, "mat_ab12cd3g"):
            assert not MS.is_valid_mid(bad), bad
            try:
                MS.material_dir(bad)
                raise AssertionError(f"material_dir a accepté {bad!r}")
            except ValueError:
                pass
        for bad in ("source", "meta", "thumb", "basecolor.png", "../basecolor"):
            try:
                MS.map_path("mat_ab12cd34", bad)
                raise AssertionError(f"map_path a accepté {bad!r}")
            except ValueError:
                pass

        # ─── 3. CRUD ────────────────────────────────────────────────────────
        mat = _make_material()
        mid = mat["id"]
        assert MS.MID_RE.match(mid), mid
        assert mat["maps"] == list(MS.MAP_KINDS), mat["maps"]
        # `ratio` / `grade` (le raccord APRES correction) complètent le couple
        # avant/après : ils viennent de la mesure, donc None tant qu'aucune
        # dérivation ne les a écrits.
        assert mat["seam"] == {"before": 12.4, "after": 1.1,
                               "ratio": None, "grade": None}

        r = await c.get("/api/materials")
        assert r.status_code == 200, r.text
        ids = [m["id"] for m in r.json()["materials"]]
        assert mid in ids

        r = await c.get(f"/api/materials/{mid}")
        assert r.status_code == 200 and r.json()["material"]["id"] == mid

        r = await c.get("/api/materials/mat_00000000")
        assert r.status_code == 404, r.text

        # tri : plus récent d'abord
        second = _make_material(name="Pierre")
        r = await c.get("/api/materials")
        got = [m["id"] for m in r.json()["materials"]]
        assert got.index(second["id"]) < got.index(mid), got

        # ─── 4. mid invalide -> 400 partout (jamais de lecture disque) ──────
        for bad in BAD_MIDS:
            for url, meth in ((f"/api/materials/{bad}", "get"),
                              (f"/api/materials/{bad}", "delete"),
                              (f"/api/materials/{bad}/map/basecolor.png", "get"),
                              (f"/api/materials/{bad}/export", "get"),
                              (f"/api/materials/{bad}/preview.glb", "get")):
                r = await getattr(c, meth)(url)
                assert r.status_code in (400, 404), (bad, url, r.status_code)
                assert r.status_code != 500, (bad, url)
            r = await c.patch(f"/api/materials/{bad}", json={"name": "x"})
            assert r.status_code in (400, 404), (bad, r.status_code)
            r = await c.post(f"/api/materials/{bad}/duplicate")
            assert r.status_code in (400, 404), (bad, r.status_code)
        # traversées avec séparateur : jamais une matière en retour
        for bad in TRAVERSAL_MIDS:
            for url in (f"/api/materials/{bad}",
                        f"/api/materials/{bad}/map/basecolor.png",
                        f"/api/materials/{bad}/export"):
                r = await c.get(url)
                assert r.status_code != 500, (bad, url)
                if "application/json" in r.headers.get("content-type", ""):
                    body = r.json()
                    assert not isinstance(body, dict) or "material" not in body, \
                        (bad, url, body)

        # le mid bien formé mais absent ne doit pas être confondu avec invalide
        r = await c.get("/api/materials/mat_deadbeef")
        assert r.status_code == 404

        # ─── 5. fusion PARTIELLE de props / derive ──────────────────────────
        r = await c.patch(f"/api/materials/{mid}",
                          json={"props": {"roughness": 0.2, "metallic": 0.9}})
        assert r.status_code == 200, r.text
        props = r.json()["material"]["props"]
        assert props["roughness"] == 0.2 and props["metallic"] == 0.9
        assert props["color"] == "#ffffff" and props["ior"] == 1.5  # intacts

        r = await c.patch(f"/api/materials/{mid}",
                          json={"props": {"color": "#FF8A1F"}})
        props = r.json()["material"]["props"]
        assert props["color"] == "#ff8a1f"
        assert props["roughness"] == 0.2, props     # la fusion n'écrase pas

        # entrées pourries -> défauts/bornes, jamais 500
        r = await c.patch(f"/api/materials/{mid}", json={"props": {
            "roughness": "oui", "metallic": 99, "opacity": -5,
            "color": "pas une couleur", "ior": None, "inconnu": 1,
            "tiling": [1, 2], "rotation": {"a": 1}}})
        assert r.status_code == 200, r.text
        props = r.json()["material"]["props"]
        assert props["roughness"] == 1.0            # défaut (valeur illisible)
        assert props["metallic"] == 1.0             # borné
        assert props["opacity"] == 0.0              # borné
        assert props["color"] == "#ffffff"          # défaut
        assert props["ior"] == 1.5 and "inconnu" not in props
        assert props["tiling"] == 1.0 and props["rotation"] == 0.0
        # NaN/inf ne passent pas par JSON : vérifiés directement sur le store
        nan = MS.merge_props(None, {"tiling": float("nan"),
                                    "ior": float("inf"),
                                    "metallic": float("-inf")})
        assert nan["tiling"] == 1.0 and nan["ior"] == 1.5
        assert nan["metallic"] == 0.0

        r = await c.patch(f"/api/materials/{mid}", json={"props": "n'importe quoi",
                                                        "derive": 12})
        assert r.status_code == 200, r.text

        r = await c.patch(f"/api/materials/{mid}", json={"derive": {
            "normal_strength": 1.5, "metallic_mode": "magique",
            "roughness_invert": "oui", "ao_radius": 999}})
        assert r.status_code == 200, r.text
        der = r.json()["material"]["derive"]
        assert der["normal_strength"] == 1.5
        assert der["metallic_mode"] == "auto"       # liste blanche
        assert der["roughness_invert"] is True
        assert der["ao_radius"] == 32.0             # borné
        assert der["emissive_threshold"] == 0.85    # intact

        r = await c.patch(f"/api/materials/{mid}",
                          json={"name": "  Fer rouillé v2  "})
        assert r.json()["material"]["name"] == "Fer rouillé v2"
        # la persistance a bien eu lieu
        assert MS.read_material(mid)["derive"]["normal_strength"] == 1.5

        # ─── 6. duplication ─────────────────────────────────────────────────
        r = await c.post(f"/api/materials/{mid}/duplicate")
        assert r.status_code == 200, r.text
        dup = r.json()["material"]
        assert dup["id"] != mid and MS.MID_RE.match(dup["id"])
        assert dup["name"].endswith("(copie)"), dup["name"]
        assert dup["maps"] == list(MS.MAP_KINDS)
        assert dup["props"]["roughness"] == 1.0     # props copiées telles quelles
        assert MS.material_dir(dup["id"]).joinpath("basecolor.png").is_file()

        # ─── 7. vignette ────────────────────────────────────────────────────
        big = io.BytesIO()
        Image.new("RGB", (700, 700), (10, 200, 30)).save(big, "PNG")
        r = await c.put(f"/api/materials/{mid}/thumb", content=big.getvalue(),
                        headers={"Content-Type": "image/png"})
        assert r.status_code == 200 and r.json() == {"ok": True}, r.text
        with Image.open(MS.material_dir(mid) / "thumb.png") as im:
            assert im.size == (512, 512)
        assert MS.read_material(mid)["thumb"] is True
        r = await c.get(f"/api/materials/{mid}/thumb.png")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"

        r = await c.put(f"/api/materials/{mid}/thumb", content=b"pas un png")
        assert r.status_code == 400, r.text
        r = await c.put(f"/api/materials/{mid}/thumb", content=b"")
        assert r.status_code == 400, r.text

        # ─── 8. maps : liste blanche + redimensionnement ────────────────────
        r = await c.get(f"/api/materials/{mid}/map/basecolor.png")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        for bad in ("bogus", "meta", "source", "thumb", "orm2"):
            r = await c.get(f"/api/materials/{mid}/map/{bad}.png")
            assert r.status_code == 400, (bad, r.status_code)
        r = await c.get(f"/api/materials/{mid}/map/orm.png?res=1024")
        assert r.status_code == 200, r.text
        with Image.open(io.BytesIO(r.content)) as im:
            assert im.size == (1024, 1024), im.size

        # ─── 9. export ZIP : conventions de nommage + 16 bits ───────────────
        r = await c.get(f"/api/materials/{mid}/export?format=zip")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            names = set(z.namelist())
            assert "material.json" in names and "LISEZMOI.txt" in names
            assert "thumb.png" in names
            assert "Fer_rouille_v2_basecolor.png" in names, sorted(names)
            assert "Fer_rouille_v2_orm.png" in names
            assert len([n for n in names if n.endswith(".png")
                        and n != "thumb.png"]) == 8
            txt = z.read("LISEZMOI.txt").decode("utf-8")
            assert "12.4" in txt and "1.1" in txt          # scores de raccord
            d8, ct8 = _png_depth(z.read("Fer_rouille_v2_height.png"))
            assert (d8, ct8) == (8, 0), (d8, ct8)

        expected = {
            "unity": ("Fer_rouille_v2_BaseMap.png",
                      "Fer_rouille_v2_MetallicOcclusion.png"),
            "unity_urp": ("Fer_rouille_v2_BaseMap.png",
                          "Fer_rouille_v2_MetallicOcclusion.png"),
            "unity_hdrp": ("Fer_rouille_v2_BaseMap.png",
                           "Fer_rouille_v2_MaskMap.png"),
            "unreal": ("T_Fer_rouille_v2_BC.png", "T_Fer_rouille_v2_ORM.png"),
            "godot": ("Fer_rouille_v2_albedo.png", "Fer_rouille_v2_orm.png"),
        }
        for naming, (a, b) in expected.items():
            r = await c.get(f"/api/materials/{mid}/export?format=zip&naming={naming}")
            assert r.status_code == 200, (naming, r.text)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                names = set(z.namelist())
                assert a in names and b in names, (naming, sorted(names))

        # 16 bits : honoré pour height et normal, ignoré ailleurs
        r = await c.get(f"/api/materials/{mid}/export?format=zip&bits=16")
        assert r.status_code == 200, r.text
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            assert _png_depth(z.read("Fer_rouille_v2_height.png")) == (16, 0)
            assert _png_depth(z.read("Fer_rouille_v2_normal.png")) == (16, 2)
            assert _png_depth(z.read("Fer_rouille_v2_basecolor.png")) == (8, 2)
            # relisible par Pillow (PNG 16 bits valide)
            with Image.open(io.BytesIO(z.read("Fer_rouille_v2_height.png"))) as im:
                assert im.size == (512, 512), im.size

        # sous-ensemble de maps + résolution
        r = await c.get(f"/api/materials/{mid}/export"
                        "?format=zip&maps=basecolor,normal&res=1024")
        assert r.status_code == 200, r.text
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            pngs = [n for n in z.namelist()
                    if n.endswith(".png") and n != "thumb.png"]
            assert len(pngs) == 2, pngs
            with Image.open(io.BytesIO(z.read("Fer_rouille_v2_normal.png"))) as im:
                assert im.size == (1024, 1024), im.size

        # listes blanches de l'export
        for q, why in ((f"format=obj", "format"), ("naming=cryengine", "naming"),
                       ("bits=12", "bits"), ("maps=basecolor,secret", "maps")):
            r = await c.get(f"/api/materials/{mid}/export?{q}")
            assert r.status_code == 400, (why, r.status_code, r.text)

        # ─── 10. GLB / glTF ────────────────────────────────────────────────
        r = await c.get(f"/api/materials/{mid}/preview.glb?mesh=torus&res=512")
        assert r.status_code == 200, r.text
        assert r.content[:4] == b"glTF", r.content[:8]
        assert r.headers["content-type"] == "model/gltf-binary"
        for bad in ("teapot", "sphere2", "../plane"):
            r = await c.get(f"/api/materials/{mid}/preview.glb?mesh={bad}")
            assert r.status_code == 400, (bad, r.status_code)

        r = await c.get(f"/api/materials/{mid}/export?format=glb")
        assert r.status_code == 200 and r.content[:4] == b"glTF"
        assert "attachment" in r.headers.get("content-disposition", "")

        r = await c.get(f"/api/materials/{mid}/export?format=gltf")
        assert r.status_code == 200, r.text
        doc = json.loads(r.content.decode("utf-8"))
        assert doc["asset"]["version"] == "2.0"
        uri = doc["buffers"][0]["uri"]
        assert uri.startswith("data:application/octet-stream;base64,"), uri[:40]
        import base64 as _b64
        raw = _b64.b64decode(uri.split(",", 1)[1])
        assert len(raw) == doc["buffers"][0]["byteLength"], len(raw)

        # ─── 11. environnements et préréglages ─────────────────────────────
        r = await c.get("/api/materials/envs")
        assert r.status_code == 200
        envs = r.json()["envs"]
        assert [e["name"] for e in envs] == ["unlit", "daylight", "studio",
                                             "sunset", "overcast", "night",
                                             "dramatic"]
        r = await c.get("/api/materials/envs/sunset.jpg")
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        with Image.open(io.BytesIO(r.content)) as im:
            assert im.size == (1024, 512), im.size
        r = await c.get("/api/materials/envs/mars.jpg")
        assert r.status_code == 404, r.status_code

        r = await c.get("/api/materials/presets")
        assert r.status_code == 200
        presets = r.json()["presets"]
        assert len(presets) >= 6
        for pr in presets:
            assert {"id", "label", "props"} <= set(pr)
            # les props d'un préréglage passent la validation sans perte
            merged = MS.merge_props(MS.default_props(), pr["props"])
            for k, v in pr["props"].items():
                assert merged[k] == v, (pr["id"], k, merged[k], v)

        # ─── 12. génération : refus immédiats ──────────────────────────────
        r = await c.post("/api/materials/generate", json={})
        assert r.status_code == 400 and "prompt" in r.text, r.text
        r = await c.post("/api/materials/generate",
                         json={"prompt": "x", "seam_method": "kaleido"})
        assert r.status_code == 400, r.text
        for bad in (r"..\..\secret.png", "../../etc/passwd", "sub/dir/a.png",
                    r"C:\Windows\win.ini", "absent.png"):
            r = await c.post("/api/materials/generate", json={"filename": bad})
            assert r.status_code == 400, (bad, r.status_code)
            assert "Librairie" in r.text or "manquant" in r.text, r.text
        r = await c.get("/api/materials/jobs/inconnu")
        assert r.status_code == 404

        # ─── 13. génération de bout en bout (prompt -> FLUX bouchonné) ─────
        r = await c.post("/api/materials/generate",
                         json={"prompt": "rusty iron", "res": 512,
                               "seamless": True, "seam_method": "offset",
                               "enhance": True, "model": "flux"})
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        for _ in range(200):
            r = await c.get(f"/api/materials/jobs/{jid}")
            assert r.status_code == 200, r.text
            st = r.json()
            if st["status"] in ("done", "failed"):
                break
            await asyncio.sleep(0.05)
        assert st["status"] == "done", st
        assert st["pct"] == 100
        gen = st["material"]
        assert gen["maps"] == list(MS.MAP_KINDS), gen["maps"]
        assert gen["res"] == 512 and gen["seamless"] is True
        assert gen["source"]["kind"] == "prompt" and gen["source"]["model"] == "flux"
        assert gen["full_prompt"].startswith("PBR texture, flat surface, "
                                             "rusty iron, top-down view")
        assert "seamless tileable" in gen["full_prompt"]      # enhance
        assert gen["seam"]["before"] is not None and gen["seam"]["after"] is not None
        # le raccord est MESURE, pas promis : il doit vraiment s'ameliorer
        # (methode offset sur une rampe pleine echelle : 50.0 -> ~10)
        assert gen["seam"]["after"] < gen["seam"]["before"] / 2, gen["seam"]
        gdir = MS.material_dir(gen["id"])
        assert (gdir / "source.png").is_file()               # traçabilité
        for kind in MS.MAP_KINDS:
            with Image.open(gdir / f"{kind}.png") as im:
                assert im.size == (512, 512), (kind, im.size)
        assert FAL_CALLS and FAL_CALLS[-1]["model"] == "fal-ai/flux/schnell"

        # ─── 14. génération depuis la Library (fichier pris tel quel) ──────
        lib = "mat_src_test.png"
        (settings.images_path / lib).write_bytes(_PNG)
        r = await c.post("/api/materials/generate",
                         json={"filename": lib, "res": 512, "seamless": True,
                               "seam_method": "mirror",
                               "name": "Depuis la Library"})
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        for _ in range(200):
            st = (await c.get(f"/api/materials/jobs/{jid}")).json()
            if st["status"] in ("done", "failed"):
                break
            await asyncio.sleep(0.05)
        assert st["status"] == "done", st
        libmat = st["material"]
        assert libmat["source"] == {"kind": "library", "model": None,
                                    "filename": lib}, libmat["source"]
        assert libmat["seamless"] is True
        assert libmat["name"] == "Depuis la Library"
        # methode miroir : raccord nul, tres en dessous du seuil de 2.0
        assert libmat["seam"]["after"] <= 2.0, libmat["seam"]

        # ─── 15. re-dérivation locale ──────────────────────────────────────
        r = await c.post(f"/api/materials/{libmat['id']}/derive",
                         json={"derive": {"normal_strength": 2.0,
                                          "roughness_invert": True},
                               "res": 1024})
        assert r.status_code == 200, r.text
        red = r.json()["material"]
        assert red["derive"]["normal_strength"] == 2.0
        assert red["derive"]["roughness_invert"] is True
        assert red["res"] == 1024
        with Image.open(MS.material_dir(red["id"]) / "normal.png") as im:
            assert im.size == (1024, 1024), im.size
        # matière sans basecolor -> 409, pas 500
        empty = MS.create_material(name="Vide", res=512)
        r = await c.post(f"/api/materials/{empty['id']}/derive", json={})
        assert r.status_code == 409, r.status_code

        # ─── 16. suppression ───────────────────────────────────────────────
        r = await c.delete(f"/api/materials/{dup['id']}")
        assert r.status_code == 200 and r.json() == {"ok": True}, r.text
        assert not MS.material_dir(dup["id"]).exists()
        r = await c.get(f"/api/materials/{dup['id']}")
        assert r.status_code == 404
        r = await c.delete(f"/api/materials/{dup['id']}")
        assert r.status_code == 404

        # rien n'a fui hors du dossier materials
        root = MS.materials_root()
        for d in root.iterdir():
            assert d.name.startswith("_") or MS.MID_RE.match(d.name), d.name

    note = f" (bouchons: {', '.join(STUBBED)})" if STUBBED else ""
    print(f"OK — Material Forge: CRUD, mid strict ({len(BAD_MIDS)} refus), "
          f"fusion partielle, listes blanches, export ZIP/GLB/glTF 8+16 bits, "
          f"job de génération prompt + Library{note}")


asyncio.run(main())
