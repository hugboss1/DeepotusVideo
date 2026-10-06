# -*- coding: utf-8 -*-
"""Lecture d'un .hdr (Radiance RGBE) en stdlib pur — R10c P2, HDRI personnels.

ALLER-RETOUR : le banc ÉCRIT lui-même des .hdr (plat et RLE adaptatif), donc
il prouve le décodeur contre une spécification, pas contre lui-même. Les
octets encodés sont produits ici, à la main, depuis des flottants connus.

Run (depuis backend/) : python tests/test_hdr_reader.py
"""
import math
import os
import pathlib
import struct
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ.setdefault("FAL_KEY", "test-key")
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import hdr_reader as HR                      # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def rgbe(r, g, b):
    """Flottants -> quadruplet RGBE, formule de référence (Real Pixels)."""
    v = max(r, g, b)
    if v < 1e-32:
        return (0, 0, 0, 0)
    m, e = math.frexp(v)               # v = m * 2**e, 0.5 <= m < 1
    k = m * 256.0 / v
    return (int(r * k), int(g * k), int(b * k), int(e + 128))


def scene(w, h):
    """Une scène connue : ciel en dégradé + un soleil 400 fois plus lumineux."""
    px = []
    for y in range(h):
        for x in range(w):
            t = y / max(1, h - 1)
            c = (0.30 + 0.50 * (1 - t), 0.45 + 0.40 * (1 - t), 0.80 - 0.30 * t)
            if abs(x - w * 3 // 4) < max(1, w // 40) and abs(y - h // 4) < max(1, h // 40):
                c = (400.0, 380.0, 340.0)
            px.append(c)
    return px


def ecrire_plat(w, h, px):
    out = bytearray(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\nEXPOSURE=1.0\n\n")
    out += f"-Y {h} +X {w}\n".encode("ascii")
    for c in px:
        out += bytes(rgbe(*c))
    return bytes(out)


def ecrire_rle(w, h, px):
    """RLE adaptatif : chaque scanline commence par 02 02 hi lo, puis quatre
    plans codés. On force les DEUX branches — répétitions et littéraux."""
    out = bytearray(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n")
    out += f"-Y {h} +X {w}\n".encode("ascii")
    for y in range(h):
        quad = [rgbe(*px[y * w + x]) for x in range(w)]
        out += bytes([2, 2, (w >> 8) & 0xFF, w & 0xFF])
        for c in range(4):
            plan = bytes(q[c] for q in quad)
            x = 0
            while x < len(plan):
                n = 1
                while x + n < len(plan) and plan[x + n] == plan[x] and n < 127:
                    n += 1
                if n >= 4:
                    out += bytes([128 + n, plan[x]])
                    x += n
                else:
                    n = 1
                    while (x + n < len(plan) and n < 128
                           and not (x + n + 3 < len(plan)
                                    and plan[x + n] == plan[x + n + 1]
                                    == plan[x + n + 2] == plan[x + n + 3])):
                        n += 1
                    out += bytes([n]) + plan[x:x + n]
                    x += n
    return bytes(out)


W, H = 64, 32
PX = scene(W, H)
PLAT, RLE = ecrire_plat(W, H, PX), ecrire_rle(W, H, PX)

# ══ 1 · en-tête et résolution ══════════════════════════════════════════════
e, off = HR.lire_entete(PLAT)
assert e["width"] == W and e["height"] == H, e
assert e["FORMAT"].lower().endswith("rle_rgbe"), e
assert PLAT[off:off + 4] == bytes(rgbe(*PX[0])), "offset du premier pixel"
ok(f"en-tête : {W}x{H}, FORMAT lu, premier pixel exactement à l'offset rendu")

# ══ 2 · les deux codages donnent les MÊMES octets ══════════════════════════
a = HR.decoder(PLAT)
b = HR.decoder(RLE)
assert a[0] == b[0] == W and a[1] == b[1] == H
assert bytes(a[2]) == bytes(b[2]), "plat et RLE divergent"
assert len(a[2]) == 4 * W * H
# Le littéral MAXIMAL (octet de tête = 128) : sur 64 px de large il n'arrive
# jamais, et confondre « > 128 » et « >= 128 » restait vert (mutant du 06/10).
# Une scanline BRUITÉE de 300 px en produit, et des deux sortes de bloc.
import random                                                  # noqa: E402
_r = random.Random(3)
BRUIT = [(_r.random() + 0.1, _r.random() + 0.1, _r.random() + 0.1) for _ in range(300 * 2)]
assert bytes(HR.decoder(ecrire_plat(300, 2, BRUIT))[2]) == \
    bytes(HR.decoder(ecrire_rle(300, 2, BRUIT))[2]), "littéral de 128 mal lu"
ok("scanline plate et RLE adaptatif décodent aux MÊMES 4·w·h octets "
   "(les deux branches du RLE — répétitions et littéraux, jusqu'au littéral "
   "de 128 sur une scanline bruitée de 300 px — sont exercées)")

# ══ 3 · la valeur reconstruite vaut la valeur écrite ═══════════════════════
plans = a[2]
pires = 0.0
for i in (0, W - 1, W * H // 2, W * H - 1):
    y, x = divmod(i, W)
    base = y * 4 * W
    m = [plans[base + c * W + x] for c in range(3)]
    ex = plans[base + 3 * W + x]
    for c in range(3):
        got = (m[c] + 0.5) / 256.0 * (2.0 ** (ex - 128))
        veut = PX[i][c]
        pires = max(pires, abs(got - veut) / max(1e-6, veut))
assert pires < 0.02, pires
ok(f"reconstruction M·2^(E-128) : écart relatif max {pires * 100:.2f} % "
   f"(quantification 8 bits de la mantisse)")

# ══ 4 · les refus nommés ═══════════════════════════════════════════════════
refus = {}
cas = [
    ("radiance", b"PK\x03\x04pas du tout un hdr"),
    ("xyze", b"#?RADIANCE\nFORMAT=32-bit_rle_xyze\n\n-Y 4 +X 4\n" + b"\0" * 64),
    ("orientation", b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n+Y 4 +X 4\n" + b"\0" * 64),
    ("ancien", b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 2 +X 16\n"
               + bytes([255, 255, 255, 3]) + b"\0" * 200),
    ("mpx", b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 8192 +X 16384\n"),
]
for mot, data in cas:
    try:
        HR.decoder(data)
        raise AssertionError(f"{mot} : aurait dû lever")
    except ValueError as exc:
        assert mot in str(exc).lower(), (mot, str(exc))
        refus[mot] = str(exc)[:46]
ok("refus nommés : " + " | ".join(refus.values()))

# ══ 5 · l'équirectangulaire LDR ════════════════════════════════════════════
img = HR.equirect_ldr(PLAT)
assert img.size == (1024, 512) and img.mode == "RGB", (img.size, img.mode)
petite = img.resize((64, 32), __import__("PIL.Image", fromlist=["Image"]).BOX)
lum = petite.convert("L")
octs = lum.tobytes()          # getdata() est obsolète (Pillow 14), et relu à chaque index
argmax = max(range(64 * 32), key=lambda i: octs[i])
sy, sx = divmod(argmax, 64)
assert abs(sx - 48) <= 3 and abs(sy - 8) <= 3, (sx, sy)
h = lum.histogram()
n = sum(h)
sombres = sum(h[:16]) / n
clairs = sum(h[240:]) / n
assert sombres < 0.25 and clairs < 0.25, (sombres, clairs)
# L'EXPOSITION elle-même : le pixel médian de la scène tombe, par construction,
# entre x = 0,5 et 1 avant Reinhard, soit 155 à 186 après gamma 2,2. Mesuré
# 164 le 06/10. Sans cette borne, décaler l'exposition de 6 crans restait vert
# (Reinhard n'écrête jamais : le test d'écrêtage ne le voit pas).
hl = img.convert("L").histogram()
cumul, mediane = 0, 0
for v, c in enumerate(hl):
    cumul += c
    if cumul >= sum(hl) / 2:
        mediane = v
        break
assert 140 <= mediane <= 200, mediane
ok(f"équirect LDR 1024x512 : le soleil retombe en ({sx}, {sy}) sur 64x32, "
   f"{sombres * 100:.0f} % de pixels noirs et {clairs * 100:.0f} % de blancs "
   f"— l'exposition médiane n'écrase ni le ciel ni le soleil")

# ══ 6 · budget sur un 4k ═══════════════════════════════════════════════════
GW, GH = 4096, 2048
gros = ecrire_plat(GW, GH, scene(GW, GH))
t0 = time.perf_counter()
img4k = HR.equirect_ldr(gros)
dt = time.perf_counter() - t0
assert img4k.size == (1024, 512)
assert dt < 8.0, dt
print(f"\n  .hdr 4096x2048 -> équirect 1024x512 : {dt:.2f} s (budget 8,0 s)")

# ══ 7 · les ROUTES : importer, lister, servir, supprimer (absent du plan) ══
import asyncio                                                 # noqa: E402
import io                                                      # noqa: E402

from httpx import ASGITransport, AsyncClient                   # noqa: E402

from app.main import app                                       # noqa: E402


async def _routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t",
                           timeout=120) as c:
        avant = (await c.get("/api/materials/envs")).json()["envs"]
        assert len(avant) == 7 and not any(e.get("perso") for e in avant), avant
        r = await c.post("/api/materials/envs", files={"file": ("ciel.hdr", PLAT)},
                         data={"label": "Mon ciel"})
        assert r.status_code == 200, r.text
        env = r.json()["env"]
        assert env["name"].startswith("u_") and env["label"] == "Mon ciel" and env["perso"] is True
        liste = (await c.get("/api/materials/envs")).json()["envs"]
        assert len(liste) == 8 and liste[-1]["name"] == env["name"] and liste[-1]["perso"] is True, liste
        j = await c.get(f"/api/materials/envs/{env['name']}.jpg")
        assert j.status_code == 200 and j.content[:3] == b"\xff\xd8\xff"
        from PIL import Image as _I
        with _I.open(io.BytesIO(j.content)) as im:
            assert im.size == (1024, 512), im.size
        refus = []
        for nom, data, mot in (("x.exr", b"v/1\x01", ".exr"), ("x.txt", b"bonjour", "Formats"),
                               ("carre.png", _png_carre(), "deux fois plus")):
            rr = await c.post("/api/materials/envs", files={"file": (nom, data)})
            assert rr.status_code == 400 and mot in rr.json()["detail"], (nom, rr.text)
            refus.append(nom)
        assert (await c.delete("/api/materials/envs/studio")).status_code == 400
        assert (await c.delete(f"/api/materials/envs/{env['name']}")).status_code == 200
        assert (await c.delete(f"/api/materials/envs/{env['name']}")).status_code == 404
        assert (await c.get(f"/api/materials/envs/{env['name']}.jpg")).status_code == 404
        assert len((await c.get("/api/materials/envs")).json()["envs"]) == 7
        assert (await c.get("/api/materials/envs/studio.jpg")).status_code == 200
    return env["name"], refus


def _png_carre():
    from PIL import Image as _I
    b = io.BytesIO()
    _I.new("RGB", (64, 64), (90, 90, 90)).save(b, format="PNG")
    return b.getvalue()


nom_env, refus_r = asyncio.run(_routes())
# LE NOM est la seule garde du chemin (`_cache_dir() / f"{nom}.jpg"`) : un
# « u_ » suivi d'autre chose que de l'alphanumérique ne doit jamais passer.
from app.services import env_service as _ES                    # noqa: E402
for faux in ("u_..\\..\\x", "u_../x", "u_", "u_a b", "studio", "", None):
    assert not _ES.est_perso(faux) and _ES.perso_path(faux) is None, faux
assert _ES.est_perso("u_3eae6ee0a0")
ok(f"routes : .hdr importé ({nom_env}, perso=True, servi en JPEG 1024x512), "
   f"refus {', '.join(refus_r)} ; « studio » ne se supprime pas ; supprimé -> 404 "
   f"et la liste revient à sept")

print(f"\nOK — {PASS} assertions groupées vertes (hdr_reader)")
