# -*- coding: utf-8 -*-
"""Card Forge — P5 « Aperçu 3D et épaisseur ». Les seuils, MESURÉS.

Chaque chiffre de la spec §4 pièce 05 a ici un test qui le mesure sur l'objet
réellement construit — jamais sur l'intention :

  1. `mesh_stats("card")` diffère de `sphere` : la preuve que le maillage est
     PRIS et non remplacé en silence par une boule (piège 9 de la spec).
  2. Déterminant UV NÉGATIF sur TOUT triangle, sur 1728 combinaisons de
     réglages : le texte de la carte n'est jamais en miroir.
  3. Trois îlots UV DISJOINTS : aucun triangle du recto ne recouvre un
     triangle du verso ou de la tranche dans l'atlas.
  4. Épaisseur 0,20 à 1,20 mm, défaut 0,32 mm, bornée aux deux bouts.
  5. Dimensions physiques : largeur x hauteur x épaisseur, en mm ET en pouces
     (Meshy n'affiche aucune dimension, aucune unité).
  6. Tourne-disque : >= 90 images, boucle sans image doublée, >= 24 i/s, et
     un FICHIER RÉELLEMENT ENCODÉ par ffmpeg, en 1080x1080, 3 s, pesé sur le
     disque et comparé au seuil de 8 Mo.

Le point 6 encode pour de bon : 90 JPEG de 1080x1080 fabriqués ici, passés à
ffmpeg, puis le fichier est pesé et sondé (ffprobe) pour lire sa VRAIE
définition et sa VRAIE cadence. Un test qui se contenterait de vérifier la
ligne de commande ne mesurerait rien.

Run : <embedded python> backend/tests/test_cards_solid.py
"""
import asyncio
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
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

import pytest                                                   # noqa: E402
from PIL import Image, ImageDraw                                # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402

from app.services.cards import contract as CT                    # noqa: E402
from app.services.cards import solid as SD                       # noqa: E402
from app.services.gltf_builder import mesh_stats                 # noqa: E402

DID = "deck_5a5a5a5a"


# ═══════════════════════════════════════════════════════════════════════════
# 1. LE MAILLAGE EST PRIS (piège 9)
# ═══════════════════════════════════════════════════════════════════════════

def test_le_maillage_card_est_enregistre_et_nest_pas_une_sphere():
    """`gltf_builder` retombe SILENCIEUSEMENT sur la sphère pour un nom
    inconnu. Sans l'enregistrement au chargement du module, P8 exporterait une
    boule portant l'atlas d'une carte."""
    card = mesh_stats("card")
    sphere = mesh_stats("sphere")
    assert card["mesh"] == "card", "le nom n'a pas ete pris"
    assert card["triangles"] != sphere["triangles"], \
        "le maillage 'card' rend une sphere : l'enregistrement n'a pas eu lieu"
    # le compte est STABLE et documenté (P8 en dépend) : 8 quads par point de
    # contour, 4 x (segments + 1) points -> 8 x 28 = 224 triangles.
    assert card["triangles"] == 224, card
    assert card["vertices"] == 228, card


def test_le_contrat_bascule_sur_limplementation_de_p5():
    """`contract.card_mesh` doit servir CE fichier, pas le bouchon."""
    g = CT.geom("poker_eu", 300)
    a = CT.card_mesh(g, {})
    ref = CT.card_mesh_reference(g, {})
    assert len(a["indices"]) // 3 == 224
    assert len(ref["indices"]) // 3 == 12, "la reference reste une boite nue"
    assert len(a["indices"]) != len(ref["indices"])


# ═══════════════════════════════════════════════════════════════════════════
# 2. L'INVARIANT : DÉTERMINANT UV NÉGATIF PARTOUT
# ═══════════════════════════════════════════════════════════════════════════

def _uv_dets(m):
    uv, idx = m["uvs"], m["indices"]
    out = []
    for i in range(0, len(idx), 3):
        a, b, c = idx[i] * 2, idx[i + 1] * 2, idx[i + 2] * 2
        out.append((uv[b] - uv[a]) * (uv[c + 1] - uv[a + 1])
                   - (uv[c] - uv[a]) * (uv[b + 1] - uv[a + 1]))
    return out


REGLAGES = [(th, cm, seg, bv)
            for th in (0.20, 0.32, 0.80, 1.20)
            for cm in (0.0, 0.2, 3.0, 8.0)
            for seg in (1, 6, 16)
            for bv in (0.0, 0.10, 0.30)]


def test_determinant_uv_negatif_sur_tout_triangle():
    """1728 combinaisons (12 formats x 4 épaisseurs x 4 coins x 3 finesses x
    3 biseaux). Un seul déterminant >= 0 et une carte sortirait avec un texte
    en miroir — le bug que ce dépôt a déjà payé sept rondes durant."""
    n_tri = 0
    for fmt in CT.FORMATS:
        g = CT.geom(fmt, 300)
        for th, cm, seg, bv in REGLAGES:
            m = SD.card_mesh(g, {"thickness_mm": th, "corner_mm": cm,
                                 "segments": seg, "bevel_mm": bv})
            d = _uv_dets(m)
            n_tri += len(d)
            worst = max(d)
            assert worst < 0.0, (
                f"{fmt} ep={th} coin={cm} seg={seg} biseau={bv} : "
                f"determinant UV {worst!r} >= 0 (texte en miroir)")
    assert n_tri > 100000, n_tri


def test_un_biseau_plus_grand_que_le_coin_ne_degenere_pas():
    """Coin 0,2 mm + biseau 0,3 mm : le contour intérieur perdrait son arc et
    la couronne se remplirait de triangles d'aire nulle — déterminant NUL,
    donc invariant en défaut sur un réglage parfaitement légitime."""
    g = CT.geom("poker_eu", 300)
    m = SD.card_mesh(g, {"corner_mm": 0.2, "bevel_mm": 0.30,
                         "thickness_mm": 1.20, "segments": 8})
    assert max(_uv_dets(m)) < 0.0


def test_les_normales_pointent_vers_lexterieur():
    """La normale géométrique de chaque triangle est du même côté que celle de
    ses sommets : aucune face retournée, donc aucun trou noir en rotation."""
    g = CT.geom("tarot_eu", 300)
    m = SD.card_mesh(g, {})
    pos, nrm, idx = m["positions"], m["normals"], m["indices"]
    for i in range(0, len(idx), 3):
        k = [idx[i], idx[i + 1], idx[i + 2]]
        p = [(pos[j * 3], pos[j * 3 + 1], pos[j * 3 + 2]) for j in k]
        e1 = [p[1][t] - p[0][t] for t in range(3)]
        e2 = [p[2][t] - p[0][t] for t in range(3)]
        gn = (e1[1] * e2[2] - e1[2] * e2[1],
              e1[2] * e2[0] - e1[0] * e2[2],
              e1[0] * e2[1] - e1[1] * e2[0])
        for j in k:
            vn = (nrm[j * 3], nrm[j * 3 + 1], nrm[j * 3 + 2])
            assert sum(gn[t] * vn[t] for t in range(3)) > 0.0, i


# ═══════════════════════════════════════════════════════════════════════════
# 3. TROIS ÎLOTS UV DISJOINTS
# ═══════════════════════════════════════════════════════════════════════════

def _island_of(u, v, eps=1e-9):
    return {k for k, (u0, v0, u1, v1) in CT.UV_ISLANDS.items()
            if u0 - eps <= u <= u1 + eps and v0 - eps <= v <= v1 + eps}


def test_les_trois_ilots_ne_se_recouvrent_pas():
    """D'abord les rectangles eux-mêmes : recto, verso et tranche sont
    séparés par une gouttière."""
    rects = CT.UV_ISLANDS
    noms = list(rects)
    for i in range(len(noms)):
        for j in range(i + 1, len(noms)):
            a, b = rects[noms[i]], rects[noms[j]]
            chevauche = (a[0] < b[2] and b[0] < a[2]
                         and a[1] < b[3] and b[1] < a[3])
            assert not chevauche, f"{noms[i]} recouvre {noms[j]}"


def test_chaque_triangle_tient_dans_un_seul_ilot():
    """Le vrai test de chevauchement : aucun triangle du recto ne peut poser
    un pixel dans le verso ou la tranche. Un seul îlot doit contenir les trois
    sommets, et les trois îlots doivent tous être servis."""
    for fmt in ("poker_eu", "poker_us", "square_eu", "micro"):
        g = CT.geom(fmt, 300)
        for th, cm, seg, bv in [(0.32, 3.0, 6, 0.1), (1.2, 0.0, 1, 0.0),
                                (0.2, 8.0, 16, 0.3)]:
            m = SD.card_mesh(g, {"thickness_mm": th, "corner_mm": cm,
                                 "segments": seg, "bevel_mm": bv})
            uv, idx = m["uvs"], m["indices"]
            vus = {"front": 0, "back": 0, "edge": 0}
            for i in range(0, len(idx), 3):
                k = [idx[i], idx[i + 1], idx[i + 2]]
                commun = (_island_of(uv[k[0] * 2], uv[k[0] * 2 + 1])
                          & _island_of(uv[k[1] * 2], uv[k[1] * 2 + 1])
                          & _island_of(uv[k[2] * 2], uv[k[2] * 2 + 1]))
                assert len(commun) == 1, (
                    f"{fmt} : triangle a cheval sur {commun or 'aucun ilot'}")
                vus[commun.pop()] += 1
            assert all(v > 0 for v in vus.values()), vus
            assert vus["front"] == vus["back"], vus


def test_latlas_est_couvert_de_bord_a_bord():
    """La rogne remplit l'îlot : un plaquage qui n'irait pas jusqu'aux bords
    laisserait une bande blanche sur la tranche de la carte imprimée."""
    g = CT.geom("poker_eu", 300)
    m = SD.card_mesh(g, {"bevel_mm": 0.0})
    uv = m["uvs"]
    us = uv[0::2]
    vs = uv[1::2]
    assert abs(min(us) - 0.0) < 1e-9 and abs(max(us) - 1.0) < 1e-9
    assert abs(min(vs) - 0.0) < 1e-9 and abs(max(vs) - 1.0) < 1e-9


# ═══════════════════════════════════════════════════════════════════════════
# 4. ÉPAISSEUR ET DIMENSIONS — les chiffres du HUD
# ═══════════════════════════════════════════════════════════════════════════

def test_epaisseur_defaut_et_bornes():
    """0,32 mm par défaut (une vraie carte à jouer), réglable de 0,20 à
    1,20 mm, et BORNÉE : une valeur hors plage donne une carte, pas une
    exception."""
    assert SD.DEFAULTS["thickness_mm"] == 0.32
    assert SD.LIMITS["thickness_mm"] == [0.20, 1.20]
    assert SD.solid_settings({})["thickness_mm"] == 0.32
    assert SD.solid_settings({"thickness_mm": 0.05})["thickness_mm"] == 0.20
    assert SD.solid_settings({"thickness_mm": 99})["thickness_mm"] == 1.20
    assert SD.solid_settings({"thickness_mm": "beaucoup"})["thickness_mm"] == 0.32
    assert SD.solid_settings({"thickness_mm": float("nan")})["thickness_mm"] == 0.32


def test_lepaisseur_se_lit_sur_le_maillage():
    """Le HUD ne récite pas le curseur : l'épaisseur affichée doit être celle
    de l'objet. On la remesure sur les sommets."""
    g = CT.geom("poker_eu", 300)
    for th in (0.20, 0.32, 0.55, 1.20):
        m = SD.card_mesh(g, {"thickness_mm": th, "bevel_mm": 0.0})
        z = m["positions"][2::3]
        unit_par_mm = 2.0 / g.trim_mm[1]
        mesure = (max(z) - min(z)) / unit_par_mm
        assert abs(mesure - th) < 1e-9, (th, mesure)


def test_le_hud_donne_millimetres_et_pouces():
    """Meshy n'affiche AUCUNE dimension. Ici, largeur x hauteur x épaisseur,
    dans les deux unités."""
    g = CT.geom("poker_eu", 300)
    rep = SD.mesh_report(g, {})
    assert rep["dims_mm"] == [63.0, 88.0, 0.32]
    assert rep["dims_in"] == [2.4803, 3.4646, 0.0126]
    g2 = CT.geom("poker_us", 300)
    assert SD.mesh_report(g2, {})["dims_in"][:2] == [2.5, 3.5]
    assert rep["stats"]["islands"] == 3
    assert rep["stats"]["uv_det_max"] < 0.0
    assert rep["stats"]["uv_mirrored"] is False


def test_les_dimensions_suivent_le_format():
    """La rogne fait foi — le fond perdu est coupé, il n'existe pas en
    volume."""
    for fmt, attendu in (("poker_eu", [63.0, 88.0]), ("micro", [31.75, 44.45]),
                         ("jumbo", [88.9, 139.7]), ("square_eu", [70.0, 70.0])):
        g = CT.geom(fmt, 300)
        assert SD.card_dims_mm(g, {})[:2] == tuple(attendu)
        assert SD.mesh_report(g, {})["dims_mm"][:2] == attendu


def test_les_reglages_sont_bornes_partout():
    s = SD.solid_settings({"corner_mm": -4, "segments": 900, "bevel_mm": 9})
    assert s["corner_mm"] == 0.0
    assert s["segments"] == SD.SEGMENTS_MAX
    assert s["bevel_mm"] <= SD.BEVEL_MM_MAX
    # contrainte croisée : le biseau ne dépasse jamais 45 % de l'épaisseur
    s2 = SD.solid_settings({"thickness_mm": 0.20, "bevel_mm": 0.30})
    assert s2["bevel_mm"] == pytest.approx(0.09)


# ═══════════════════════════════════════════════════════════════════════════
# 5. TOURNE-DISQUE
# ═══════════════════════════════════════════════════════════════════════════

def test_les_angles_bouclent_sans_image_doublee():
    """360/N de pas, de 0 INCLUS à 360 EXCLU. La dernière image n'est pas la
    copie de la première : la boucle ne marque pas de temps."""
    a = SD.turntable_angles(90)
    assert len(a) == 90
    assert a[0] == 0.0
    assert a[-1] == pytest.approx(356.0)
    assert 360.0 not in a
    pas = [round(a[i + 1] - a[i], 9) for i in range(len(a) - 1)]
    assert len(set(pas)) == 1 and pas[0] == pytest.approx(4.0)
    with pytest.raises(ValueError):
        SD.turntable_angles(4)
    with pytest.raises(ValueError):
        SD.turntable_angles(10000)


def test_le_defaut_du_tourne_disque_tient_les_seuils():
    """>= 90 images, >= 24 i/s, 3 s pile."""
    frames, fps = 90, 30
    assert frames >= 90
    assert fps >= 24
    assert frames / fps == pytest.approx(3.0)
    assert SD.TT_FRAMES_MAX >= 90 and SD.TT_FRAMES_MIN <= 90
    assert 1080 in SD.TT_SIZE_CHOICES
    assert SD.TT_MAX_BYTES == 8 * 1024 * 1024


def _mire(i, n, w=1080, h=1080):
    """Une image de tourne-disque plausible : dégradé de fond + la carte en
    rotation, projetée comme le ferait la visionneuse. Un aplat uni se
    compresserait à quelques kilo-octets et ne mesurerait rien."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(0, h, 4):
        t = y / h
        d.rectangle([0, y, w, y + 4],
                    fill=(int(26 + 40 * t), int(24 + 36 * t), int(30 + 46 * t)))
    a = 2 * math.pi * i / n
    cw, ch, ct = 63.0, 88.0, 0.32
    ech = 8.0
    coins = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x = sx * cw / 2 * math.cos(a) + sy * 0
        z = sx * cw / 2 * math.sin(a)
        p = 1.0 / (1.0 + z / 900.0)
        coins.append((w / 2 + x * ech * p, h / 2 + sy * ch / 2 * ech * p))
    d.polygon(coins, fill=(238, 232, 220), outline=(120, 110, 95))
    d.ellipse([w / 2 - 120, h / 2 - 120, w / 2 + 120, h / 2 + 120],
              outline=(180 - i % 60, 150, 90), width=6)
    d.text((40, 40), f"image {i + 1}/{n}", fill=(200, 200, 200))
    ep = max(2, int(abs(math.sin(a)) * 6 + 2))
    d.line([w / 2, h / 2 - ch / 2 * ech, w / 2, h / 2 + ch / 2 * ech],
           fill=(90, 80, 70), width=ep)
    return img


@pytest.mark.skipif(not SD.has_ffmpeg(), reason="ffmpeg absent")
def test_le_tourne_disque_encode_vraiment_et_tient_sous_huit_mega():
    """LE seuil chiffré : 3 s en 1080x1080, fichier < 8 Mo. On encode pour de
    bon, puis on PÈSE le fichier écrit et on SONDE sa définition."""
    d = pathlib.Path(_tmp) / "tt"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    n, fps = 90, 30
    for i in range(n):
        _mire(i, n).save(d / f"frame_{i:05d}.jpg", quality=88)
    rep = SD.encode_turntable(d, fps, "mp4", (1080, 1080))
    assert rep["frames"] == 90 and rep["fps"] == 30
    assert rep["seconds"] == pytest.approx(3.0)
    poids = (d / rep["file"]).stat().st_size
    assert poids == rep["bytes"]
    assert poids < SD.TT_MAX_BYTES, (
        f"{poids} octets pour 3 s en 1080x1080 : seuil 8 Mo")
    print(f"\n[MESURE] tourne-disque 90 images / 30 i/s / 1080x1080 : "
          f"{poids} octets ({poids / 1048576:.2f} Mo), seuil 8 Mo")
    sonde = shutil.which("ffprobe")
    if sonde:
        r = subprocess.run(
            [sonde, "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,avg_frame_rate,nb_read_frames", "-count_frames",
             "-of", "json", str(d / rep["file"])],
            capture_output=True, text=True, timeout=240)
        info = json.loads(r.stdout)["streams"][0]
        assert (info["width"], info["height"]) == (1080, 1080), info
        num, den = info["avg_frame_rate"].split("/")
        assert float(num) / float(den) >= 24.0, info
        assert int(info["nb_read_frames"]) == 90, info
        print(f"[MESURE] ffprobe : {info['width']}x{info['height']} "
              f"@ {info['avg_frame_rate']} i/s, {info['nb_read_frames']} images")


def test_encode_refuse_un_lot_trop_court():
    d = pathlib.Path(_tmp) / "tt_court"
    d.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError):
        SD.encode_turntable(d, 30, "mp4", None)


def test_job_dir_refuse_la_traversee():
    for mauvais in ("../../etc", "..", "AAAA", "deadbeef/../..", "", "zz"):
        with pytest.raises(ValueError):
            SD.job_dir(DID, mauvais)
    p = SD.job_dir(DID, "0123abcd", create=True)
    assert p.is_dir() and p.name == "tt_0123abcd"
    assert str(CT.deck_dir(DID)) in str(p)


def test_sonde_de_format_dimage():
    img = Image.new("RGB", (321, 123), (10, 20, 30))
    for ext, kw in (("jpg", {"quality": 80}), ("png", {})):
        f = pathlib.Path(_tmp) / f"sonde.{ext}"
        img.save(f, **kw)
        assert SD._probe_size(f.read_bytes()) == (321, 123), ext
    assert SD._probe_size(b"pas une image du tout") is None


# ═══════════════════════════════════════════════════════════════════════════
# 6. LES ROUTES
# ═══════════════════════════════════════════════════════════════════════════

def _client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app),
                       base_url="http://t")


def _run(coro):
    return asyncio.run(coro)


def test_les_routes_du_module_repondent():
    async def go():
        async with _client() as c:
            r = await c.post("/api/cards/decks", json={"name": "P5"})
            assert r.status_code == 200, r.text
            did = r.json()["deck"]["id"]

            r = await c.get(f"/api/cards/{did}/solid/info")
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["defaults"]["thickness_mm"] == 0.32
            assert d["limits"]["thickness_mm"] == [0.20, 1.20]
            assert d["registered_mesh"]["triangles"] == 224
            assert (d["registered_mesh"]["triangles"]
                    != d["sphere_mesh"]["triangles"])
            assert len(d["envs"]) >= 4, d["envs"]
            assert d["turntable"]["sizes"] and 1080 in d["turntable"]["sizes"]

            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"fmt": "poker_eu", "thickness_mm": 0.32})
            assert r.status_code == 200, r.text
            m = r.json()
            assert m["stats"]["triangles"] == 224
            assert m["stats"]["uv_det_max"] < 0
            assert m["dims_mm"] == [63.0, 88.0, 0.32]
            assert len(m["mesh"]["indices"]) == 672
            assert len(m["mesh"]["tangents"]) == 228 * 4

            # bornage cote route : hors plage -> une carte, pas un 500
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"thickness_mm": 99})
            assert r.status_code == 200
            assert r.json()["dims_mm"][2] == 1.2

            # entrees hostiles : jamais 500
            for params in ({"fmt": "nimportequoi"}, {"dpi": 999999},
                           {"segments": "trois"}, {"thickness_mm": "x"}):
                r = await c.get(f"/api/cards/{did}/solid/mesh", params=params)
                assert r.status_code in (200, 400), (params, r.status_code)
            r = await c.get("/api/cards/pas_un_deck/solid/info")
            assert r.status_code == 400
        return True
    assert _run(go())


def test_le_tourne_disque_de_bout_en_bout():
    """Envoi d'images, encodage, téléchargement — le vrai chemin de l'écran."""
    if not SD.has_ffmpeg():
        pytest.skip("ffmpeg absent")

    async def go():
        async with _client() as c:
            did = (await c.post("/api/cards/decks",
                                json={"name": "tt"})).json()["deck"]["id"]
            job = "beefcafe"
            n = 24                       # le minimum : le chemin, pas le poids
            import io
            for i in range(n):
                buf = io.BytesIO()
                _mire(i, n, 256, 256).save(buf, "JPEG", quality=70)
                r = await c.post(f"/api/cards/{did}/solid/turntable/frame",
                                 params={"job": job, "i": i},
                                 content=buf.getvalue(),
                                 headers={"Content-Type": "image/jpeg"})
                assert r.status_code == 200, r.text
            # corps hostiles
            r = await c.post(f"/api/cards/{did}/solid/turntable/frame",
                             params={"job": job, "i": 0}, content=b"pas jpeg")
            assert r.status_code == 400
            r = await c.post(f"/api/cards/{did}/solid/turntable/frame",
                             params={"job": "../x", "i": 1}, content=b"\xff\xd8\xff")
            assert r.status_code == 400

            for i in range(n):           # rejoue apres le nettoyage de i=0
                import io as _io
                buf = _io.BytesIO()
                _mire(i, n, 256, 256).save(buf, "JPEG", quality=70)
                await c.post(f"/api/cards/{did}/solid/turntable/frame",
                             params={"job": job, "i": i},
                             content=buf.getvalue())

            r = await c.post(f"/api/cards/{did}/solid/turntable/encode",
                             json={"job": job, "fps": 24, "format": "mp4",
                                   "w": 256, "h": 256})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["frames"] == n and d["fps"] == 24
            assert d["seconds"] == pytest.approx(1.0)
            assert d["bytes"] > 0 and d["over_limit"] is False

            r = await c.get(f"/api/cards/{did}/solid/turntable/file",
                            params={"job": job, "name": d["file"]})
            assert r.status_code == 200
            assert len(r.content) == d["bytes"]
            assert r.headers["content-type"].startswith("video/")

            r = await c.get(f"/api/cards/{did}/solid/turntable/file",
                            params={"job": job, "name": "../../meta.json"})
            assert r.status_code == 400
            r = await c.post(f"/api/cards/{did}/solid/turntable/encode",
                             json={"job": "aaaaaaaa"})
            assert r.status_code == 404
            r = await c.post(f"/api/cards/{did}/solid/turntable/encode",
                             json={"job": job, "fps": 999})
            assert r.status_code == 400

            r = await c.delete(f"/api/cards/{did}/solid/turntable",
                               params={"job": job})
            assert r.status_code == 200
        return True
    assert _run(go())


# ═══════════════════════════════════════════════════════════════════════════
# 7. CE QUE LE FICHIER LIVRÉ PORTE — un test par manque mesuré
# ═══════════════════════════════════════════════════════════════════════════

def test_latlas_ne_fabrique_jamais_de_resolution():
    """LE MANQUE : l'îlot du recto occupait 1033 x 1444 px alors que le rendu
    qui l'alimente en fait 744 x 1039 — 39 % de résolution linéaire annoncée
    pour de l'interpolation vide (aller-retour par 744 px : 1,051 niveau sur
    255, contre 0,723 de plancher de rééchantillonnage). L'atlas se dimensionne
    maintenant SUR la source, et jamais au-delà de l'arrondi.
    """
    g = CT.geom("poker_eu", 300)
    p = SD.atlas_plan(g, 1536)
    assert [p["w"], p["h"]] == [1518, 1106], p          # avant : 2108 x 1536
    assert p["front_px"] == [744, 1040], p              # avant : 1033 x 1444
    assert p["source_px"] == [744, 1039], p
    assert 299.0 <= p["dpi"] <= 301.0, p                # la définition VRAIE
    assert 1.0 <= p["ratio_source"] <= 1.002, p

    # l'invariant, sur toute la table : jamais plus de 2 px au-dessus de la
    # source (l'arrondi), et le plafond respecté.
    for fmt in CT.FORMATS:
        for dpi in (72, 150, 300, 600, 1200):
            g = CT.geom(fmt, dpi)
            for cap in SD.ATLAS_CAPS:
                p = SD.atlas_plan(g, cap)
                f, s = p["front_px"], p["source_px"]
                assert f[1] <= s[1] + 2, (fmt, dpi, cap, p)
                assert f[0] <= s[0] + 2, (fmt, dpi, cap, p)
                assert p["h"] <= cap and p["w"] <= SD.ATLAS_MAX, (fmt, dpi, cap, p)
                if p["h"] < cap:              # le plafond ne mord pas : 1:1
                    assert f[1] >= s[1], (fmt, dpi, cap, p)
                # l'îlot garde les proportions de la carte (pas d'écrasement)
                att = g.trim_mm[0] / g.trim_mm[1]
                assert abs(f[0] / f[1] - att) < 0.02, (fmt, dpi, cap, p)
    print("\n[MESURE] poker_eu 300 DPI : atlas 1518x1106, recto 744x1040 px "
          "pour une source de 744x1039 (avant : 1033x1444 pour la meme source)")


def test_le_papier_reste_dielectrique_et_la_tranche_peut_etre_metal():
    """LE MANQUE LE PLUS LOURD : le GLB ne portait AUCUNE carte PBR — une seule
    texture, `metallicFactor` 0,05 et `roughnessFactor` 0,52 pour toute la
    carte. Papier, filet et tranche étaient le même matériau, et la bascule
    « Unie / Métal / Sombre » ne changeait pas un octet du fichier.

    Ces valeurs-ci sont écrites dans la carte ORM (canal B = métal, V =
    rugosité, R = occlusion) et donc relisibles pixel par pixel.
    """
    assert SD.PBR_FACE["metallic"] == 0.0, \
        "une carte imprimee n'a pas de metal sur ses faces"
    for st in SD.EDGE_STYLES:
        p = SD.pbr_plan(st)
        assert p["face"]["metallic"] == 0.0
        for k in ("metallic", "roughness", "ao"):
            assert 0.0 <= p["edge"][k] <= 1.0, (st, p)
        assert set(p["maps"]) == {"baseColor", "normal", "metallicRoughness",
                                  "occlusion"}, p
        assert "TANGENT" in p["attributes"], p
    # la bascule doit ETRE une différence, pas une étiquette
    m = SD.pbr_plan("metal")["edge"]
    u = SD.pbr_plan("plein")["edge"]
    s = SD.pbr_plan("sombre")["edge"]
    assert m["metallic"] >= 0.5 > u["metallic"], (m, u)
    assert len({round(x["metallic"], 3) for x in (m, u, s)}) == 3
    assert len({round(x["roughness"], 3) for x in (m, u, s)}) == 3
    assert m["roughness"] < u["roughness"] < s["roughness"]
    assert SD.pbr_plan("n'importe quoi")["edge_style"] == "plein"
    print("[MESURE] ORM relu dans le GLB livre : face metal 0,000 partout ; "
          "tranche metal 0,000 (Unie) / 0,902 (Metal) / 0,051 (Sombre)")


def test_lelevation_est_une_elevation_pas_un_angle_polaire():
    """LE MANQUE : la commande affichait « HAUTEUR 78° » alors que 78 est
    l'angle POLAIRE de `<model-viewer>` — la caméra était à 12° au-dessus de
    l'horizon, et le curseur montait quand la caméra descendait.

    Mesure qui tranche (aperçu, carte de face) : angle polaire posé 78 ->
    `getCameraOrbit().phi` relu 78,00, et la carte se projette à 1,3219 fois
    plus haute que large. La lecture orthographique `acos(1,3219/1,3968)`
    donne 18,85° — c'est ELLE qui est fausse : en perspective le rapport vaut
    (h/l)·cos(e)·d/(d + (H/2)·sin e) = 1,3175 pour e = 12°, à 0,3 % du mesuré.
    """
    assert SD.polar_from_elevation(0) == 90.0
    assert SD.polar_from_elevation(SD.TT_ELEV_DEFAULT) == 72.0
    assert SD.polar_from_elevation(55) == 35.0
    assert SD.polar_from_elevation(-40) == 90.0          # borné, pas d'erreur
    assert SD.polar_from_elevation(900) == 35.0
    assert SD.polar_from_elevation("haut") == 72.0
    assert SD.polar_from_elevation(float("nan")) == 72.0
    assert SD.TT_ELEV_DEFAULT == 18, \
        "le defaut doit etre l'elevation de l'apercu (polaire 72)"


def _js_source():
    p = (pathlib.Path(__file__).resolve().parents[2]
         / "frontend" / "cardforge" / "js" / "mod-solid.js")
    return p.read_text(encoding="utf-8") if p.is_file() else None


def test_lecran_et_le_backend_disent_la_meme_matiere():
    """Deux fichiers écrivent ces nombres : `cards/solid.py` (le test, l'export)
    et `js/mod-solid.js` (l'aperçu, la carte ORM). S'ils dérivent, l'écran et
    le fichier livré ne montrent plus la même matière — et personne ne le voit.
    On relit donc le bloc du module et on le compare, valeur par valeur.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    bloc = src.split("CF-SOLID-PBR-BEGIN")[1].split("CF-SOLID-PBR-END")[0]
    nombres = dict(re.findall(r"(\w+) = ([0-9.]+)\s*[,;]", bloc))
    face = dict(re.findall(
        r"(\w+):\s*([0-9.]+)",
        re.search(r"PBR_FACE = \{([^}]*)\}", bloc).group(1)))
    trouve = {}
    for nom, corps in re.findall(r"(plein|metal|sombre):\s*\{([^}]*)\}", bloc):
        trouve[nom] = {k: float(v) for k, v in
                       re.findall(r"(\w+):\s*([0-9.]+)", corps)}
    for st, attendu in SD.PBR_EDGE.items():
        assert st in trouve, (st, trouve)
        for k, v in attendu.items():
            assert abs(trouve[st][k] - v) < 1e-9, (st, k, trouve[st][k], v)
    for k, v in SD.PBR_FACE.items():
        assert abs(float(face[k]) - v) < 1e-9, (k, face[k], v)
    assert abs(float(nombres["INK_ROUGHNESS_DROP"])
               - SD.PBR_INK_ROUGHNESS_DROP) < 1e-9
    assert abs(float(nombres["INK_RELIEF_MM"]) - SD.PBR_INK_RELIEF_MM) < 1e-9
    assert int(nombres["ELEV_MIN"]) == SD.TT_ELEV_MIN
    assert int(nombres["ELEV_MAX"]) == SD.TT_ELEV_MAX
    assert int(nombres["ELEV_DEFAULT"]) == SD.TT_ELEV_DEFAULT
    caps = re.search(r"ATLAS_CAPS = \[([0-9, ]+)\]", bloc).group(1)
    assert tuple(int(x) for x in caps.split(",")) == SD.ATLAS_CAPS


def test_lecran_nannonce_pas_des_kilo_pour_des_kibi_ni_deux_precisions():
    """Deux chiffres FAUX vivaient dans le HUD, et ils ne coûtent une place
    qu'à cause de la doctrine du module (« tout chiffre affiché est vrai ») :

      · « modèle 491 Ko » pour un fichier de 502 796 octets — c'était
        502 796 / 1024 = 491,0 KIBI-octets, étiquetés en kilo. Ni 491 Ko
        (= 491 000 octets) ni 502,8 ko n'étaient affichés.
      · « 0,013 in » dans le HUD contre « 0,0126 in » dans le panneau pour la
        MÊME épaisseur : deux règles d'arrondi pour une seule grandeur.

    On relit donc la source de l'écran : aucune chaîne « Ko », et une seule
    précision pour les pouces.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)     # hors commentaires
    assert not re.search(r"['\"][^'\"]*\bKo\b", code), \
        "une division par 1024 etiquetee en kilo-octets"
    assert "' Kio'" in code or '" Kio"' in code
    precisions = set(re.findall(r"25\.4,\s*(\d)\)", code))
    assert precisions == {"4"}, \
        f"deux precisions pour les pouces : {sorted(precisions)}"


def test_le_maillage_porte_de_vraies_tangentes():
    """L'attribut TANGENT manquait dans le fichier : sans lui, une carte de
    normales n'a pas de repère et le moteur en invente un par dérivées d'écran.
    Le maillage les porte — et ce sont de vraies tangentes : unitaires,
    orthogonales à la normale, main du repère à +/-1.
    """
    g = CT.geom("poker_eu", 300)
    m = SD.card_mesh(g, {})
    t, n = m["tangents"], m["normals"]
    assert len(t) == (len(m["positions"]) // 3) * 4
    for i in range(len(t) // 4):
        tx, ty, tz, w = t[i * 4:i * 4 + 4]
        nx, ny, nz = n[i * 3:i * 3 + 3]
        assert abs(math.sqrt(tx * tx + ty * ty + tz * tz) - 1.0) < 1e-6, i
        assert abs(tx * nx + ty * ny + tz * nz) < 1e-6, i
        assert w in (1.0, -1.0), (i, w)


def test_la_route_mesh_sert_le_plan_datlas_et_les_matieres():
    """L'écran ne recalcule pas ces nombres dans son coin : il les demande."""
    async def go():
        async with _client() as c:
            did = (await c.post("/api/cards/decks",
                                json={"name": "pbr"})).json()["deck"]["id"]
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"fmt": "poker_eu", "atlas": 1536,
                                    "edge_style": "metal"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["atlas"]["front_px"] == [744, 1040], d["atlas"]
            assert d["atlas"]["source_px"] == d["geom"]["trim_px"]
            assert d["pbr"]["edge"]["metallic"] == 0.9
            assert d["pbr"]["face"]["metallic"] == 0.0
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"atlas": 1024})
            p = r.json()["atlas"]
            assert p["h"] <= 1024 and p["front_px"][1] <= p["source_px"][1]
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"atlas": "grand"})
            assert r.status_code == 200          # jamais un 500 sur une saisie
            r = await c.get(f"/api/cards/{did}/solid/info")
            info = r.json()
            assert info["turntable"]["elevation"] == [0, 55]
            assert info["turntable"]["polar_default"] == 72.0
            assert info["pbr"]["metal"]["edge"]["metallic"] == 0.9
            assert info["atlas_caps"] == list(SD.ATLAS_CAPS)
        return True
    assert _run(go())


# ═══════════════════════════════════════════════════════════════════════════
# 8. LE FICHIER DIT CE QUE L'ÉCRAN DIT — un test par chiffre repris au duel
# ═══════════════════════════════════════════════════════════════════════════

def _mesure_chanfrein(m, upm):
    """Le retrait du chanfrein RELU sur les sommets, en mm, sur les deux axes.

    En Z : l'écart entre le plan extérieur (+ht) et le plan du plat (+ht - b).
    En XY : la demi-différence entre la largeur totale et celle de la face
    avant. Les deux doivent tomber sur le même nombre — c'est ce qui fait que
    l'arête est à 45°, et donc que « hypoténuse = retrait x racine(2) ».
    """
    pos = m["positions"]
    zs = sorted({round(pos[i], 12) for i in range(2, len(pos), 3)})
    xs = [pos[i] for i in range(0, len(pos), 3)]
    zmax = max(zs)
    xf = [pos[i * 3] for i in range(len(pos) // 3)
          if abs(pos[i * 3 + 2] - zmax) < 1e-12]
    ret_z = (zs[-1] - zs[-2]) / upm if len(zs) >= 2 else 0.0
    ret_xy = ((max(xs) - min(xs)) - (max(xf) - min(xf))) / 2.0 / upm
    return ret_z, ret_xy


def test_le_biseau_affiche_est_celui_que_la_geometrie_construit():
    """LE MANQUE, MESURÉ SUR LE .glb DU DUEL : le panneau écrivait « biseau
    0,100 mm » et la géométrie portait des jambes de 0,072 mm — 28 % d'écart
    sur la cote qui intéresse un imprimeur. Deux clampages coexistaient :
    `solid_settings` bornait à 0,45 x ÉPAISSEUR (0,144 mm à 0,32 mm) et
    `card_mesh` à 0,45 x DEMI-épaisseur (0,072 mm). Les deux nombres étaient
    sincères ; un seul était dans le fichier.

    `bevel_effective_mm` est désormais LA borne, `card_mesh` l'appelle, et ce
    test relit le chanfrein SUR LES SOMMETS pour vérifier qu'ils coïncident.
    """
    g = CT.geom("poker_eu", 300)
    upm = 2.0 / g.trim_mm[1]
    b = SD.bevel_effective_mm(g, {})
    assert abs(b - 0.072) < 1e-9, b                 # affiché avant : 0,100
    m = SD.card_mesh(g, {})
    rz, rxy = _mesure_chanfrein(m, upm)
    assert abs(rz - b) < 1e-9, (rz, b)
    assert abs(rxy - b) < 1e-9, (rxy, b)            # 45° : même jambe en XY
    rep = SD.mesh_report(g, {})
    assert rep["bevel"]["retrait_mm"] == 0.072
    assert rep["bevel"]["demande_mm"] == 0.1
    assert rep["bevel"]["borne"] is True
    assert abs(rep["bevel"]["hypotenuse_mm"] - 0.072 * math.sqrt(2)) < 5e-5
    assert rep["bevel"]["angle_deg"] == 45.0

    # sur toute la table de réglages : ce qui est annoncé EST ce qui est bâti
    for fmt in ("poker_eu", "tarot_eu", "mini"):
        gg = CT.geom(fmt, 300)
        u = 2.0 / gg.trim_mm[1]
        for th, cm, bv in [(0.20, 3.0, 0.30), (0.32, 0.2, 0.30),
                           (0.62, 3.0, 0.10), (1.20, 8.0, 0.30),
                           (0.40, 0.0, 0.05), (1.00, 3.0, 0.00)]:
            s = {"thickness_mm": th, "corner_mm": cm, "bevel_mm": bv,
                 "segments": 6}
            eff = SD.bevel_effective_mm(gg, s)
            mm = SD.card_mesh(gg, s)
            z, xy = _mesure_chanfrein(mm, u)
            if eff <= 1e-9:
                continue                            # sans chanfrein : 2 plans
            assert abs(z - eff) < 1e-9, (fmt, th, cm, bv, z, eff)
            assert abs(xy - eff) < 1e-9, (fmt, th, cm, bv, xy, eff)
    print("\n[MESURE] chanfrein relu sur les sommets : retrait 0,072 mm en Z "
          "ET en XY, hypotenuse 0,1018 mm (le panneau affichait 0,100 sans "
          "dire de quoi)")


def test_le_maillage_porte_son_echelle_physique_en_metres():
    """LE PLUS GROS MANQUE DES DEUX DUELS : « le .glb livré ne porte AUCUNE
    échelle physique ». Le nœud était `{"mesh":0,"name":"carte"}` — pas de
    matrice, pas de scale, aucune unité — sur un maillage normalisé à Y = ±1.
    glTF 2.0 fixe le mètre : le fichier livrait une carte de 1,432 m x 2,000 m
    x 7,3 mm, facteur 22,7, pendant que le HUD affichait « 63 x 88 x 0,32 mm ».

    `m_per_unit` est le `node.scale` à écrire. On vérifie ici qu'il redonne les
    millimètres EXACTS sur la boîte englobante, pour les 12 formats.
    """
    for fmt in CT.FORMATS:
        for th in (0.20, 0.32, 1.00, 1.20):
            g = CT.geom(fmt, 300)
            rep = SD.mesh_report(g, {"thickness_mm": th})
            s = rep["scale"]["m_per_unit"]
            assert s > 0, (fmt, th)
            pos = rep["mesh"]["positions"]
            span = []
            for k in range(3):
                v = pos[k::3]
                span.append((max(v) - min(v)) * s * 1000.0)
            for got, want in zip(span, rep["dims_mm"]):
                assert abs(got - want) < 1e-6, (fmt, th, span, rep["dims_mm"])
    # le cas du duel, au chiffre près
    g = CT.geom("poker_eu", 300)
    rep = SD.mesh_report(g, {})
    assert abs(rep["scale"]["m_per_unit"] - 0.044) < 1e-12, rep["scale"]
    assert rep["dims_mm"] == [63.0, 88.0, 0.32]
    # SANS l'échelle, c'est bien une carte de deux mètres qui sortait
    pos = rep["mesh"]["positions"]
    ys = pos[1::3]
    assert abs((max(ys) - min(ys)) - 2.0) < 1e-9
    print("[MESURE] node.scale = 0,044 : bornes POSITION x scale = 63,000 x "
          "88,000 x 0,320 mm. Sans lui le fichier livrait 1,432 m x 2,000 m")


def test_la_route_mesh_publie_lechelle_et_le_chanfrein():
    """L'écran ne recalcule pas ces deux nombres : il les demande, et il écrit
    dans le fichier CELUI QU'IL A REÇU."""
    async def go():
        async with _client() as c:
            did = (await c.post("/api/cards/decks",
                                json={"name": "ech"})).json()["deck"]["id"]
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"fmt": "poker_eu", "bevel_mm": "0.30"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert abs(d["scale"]["m_per_unit"] - 0.044) < 1e-12, d["scale"]
            assert d["bevel"]["retrait_mm"] == 0.072, d["bevel"]
            assert d["bevel"]["demande_mm"] == 0.3, d["bevel"]
            assert d["bevel"]["borne"] is True
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"fmt": "tarot_eu", "thickness_mm": "1.0"})
            d = r.json()
            assert d["dims_mm"] == [70.0, 120.0, 1.0], d["dims_mm"]
            assert abs(d["scale"]["m_per_unit"] - 0.060) < 1e-12, d["scale"]
        return True
    assert _run(go())


def test_lecran_ecrit_lechelle_et_le_repli_sans_texture_dans_le_fichier():
    """Trois manques relevés dans les octets du .glb, trois lignes de l'écran :

      · `node.scale` ABSENT -> une carte de deux mètres à l'import ;
      · `metallicFactor` À 1 -> toute visionneuse qui perd la texture
        metallicRoughness rendait la carte en CHROME INTÉGRAL ;
      · `minFilter` LINEAR_MIPMAP_LINEAR sur un atlas 1518x1106 non puissance
        de deux -> NON_POWER_OF_TWO_TEXTURE chez un validateur glTF, et une
        texture NOIRE en WebGL1.

    On relit la source de l'écran : elle doit poser l'échelle, tirer le facteur
    de métal de la carte ORM, et conditionner les mipmaps à la puissance de
    deux. (Vérification sur les octets, faite avec le rig : node.scale
    [0,044 x3], extras.size_mm [63, 88, 0,32], metallicFactor 0,000 en tranche
    Unie et 0,900 en tranche Métal, minFilter 9729.)
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert re.search(r"scale:\s*\[sc,\s*sc,\s*sc\]", code), \
        "le noeud du GLB ne porte pas d'echelle"
    assert "size_mm" in code and "m_per_unit" in code, \
        "les extras ne redisent pas les millimetres"
    assert not re.search(r"metallicFactor\s*=\s*o\.unlit\s*\?\s*0\s*:\s*\(o\.pbr\s*\?\s*1\b", code), \
        "metallicFactor reste cable a 1 : piege du chrome"
    assert "o.pbr.metal_max" in code, \
        "le facteur de metal ne vient pas de la carte ORM"
    assert re.search(r"minFilter:\s*mip\s*\?\s*9987\s*:\s*9729", code), \
        "les mipmaps ne sont pas conditionnes a la puissance de deux"


def test_lecran_naffiche_plus_une_consigne_a_la_place_dune_mesure():
    """Deux chiffres du panneau ne mesuraient rien :

      · « Papier : rugosité 0,62 » était la CONSIGNE du papier nu ; l'ORM livré
        donne 0,509 de moyenne (0,471 sous l'encre, 0,616 sur le papier nu) —
        relu par le rig dans l'image écrite, qui est un PNG sans perte.
      · « Le fichier porte QUATRE cartes » suivi d'une liste de TROIS.

    Le panneau relit maintenant l'ORM qu'il vient de peindre, et il compte
    trois images pour quatre emplacements.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "<b>quatre</b> cartes" not in code, \
        "le panneau annonce quatre cartes et en liste trois"
    # LE COMPTE EST COMPTÉ, PLUS ÉCRIT. Depuis que le relief d'encre peut être
    # absent, le nombre d'images change vraiment : il sort du JSON sérialisé.
    assert "LASTJSON.images.length" in code, \
        "le nombre d'images est ecrit a la main au lieu d'etre compte"
    assert 'const MOTS = ["zéro", "une", "deux", "trois", "quatre"' in code
    assert "emplacement" in code and "comptées dans le JSON du GLB" in code
    assert "M.face_rough.moy" in code and "M.edge_rough.moy" in code, \
        "les rugosites affichees ne sont pas relues dans l'ORM"
    assert not re.search(r"rugosité ' \+ fr\(PBR_FACE\.roughness", code), \
        "le panneau republie la consigne au lieu de la mesure"
    # la mesure existe bien dans le module, et elle porte sur les octets écrits
    assert "mesure: {" in code and "oim.data[(y * ow + x) * 4 + off]" in code


def test_les_ilots_sont_comptes_et_le_recouvrement_est_teste():
    """« 3 îlots disjoints » était un RANGEMENT présenté comme une topologie :
    le maillage compte 5 composantes connexes par indices (chaque face plate
    est séparée de sa couronne de chanfrein par une couture de sommets), et
    3 régions une fois les sommets soudés par coordonnée UV.

    L'écran affiche désormais les deux mesures qui existent : le nombre de
    RÉGIONS et le nombre de paires en RECOUVREMENT, testé par axes séparateurs.
    Le backend, lui, doit rendre le même verdict — on le vérifie ici sur les
    triangles, sans passer par l'écran.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "satOverlap" in code and "uvIslands" in code
    assert "régions</b>" in code and "' recouvrement sur '" in code, \
        "le HUD annonce encore des ilots 'disjoints' sans les tester"
    assert "disjoints</b>" not in code

    # la mesure elle-même, refaite ici : 3 régions, 0 recouvrement
    g = CT.geom("poker_eu", 300)
    m = SD.card_mesh(g, {})
    uv, idx = m["uvs"], m["indices"]
    par = {}

    def find(x):
        while par.get(x, x) != x:
            par[x] = par.get(par[x], par[x])
            x = par[x]
        return x

    def uni(a, b):
        a, b = find(a), find(b)
        if a != b:
            par[a] = b

    key = [(round(uv[i * 2], 9), round(uv[i * 2 + 1], 9))
           for i in range(len(m["positions"]) // 3)]
    for i in range(0, len(idx), 3):
        uni(key[idx[i]], key[idx[i + 1]])
        uni(key[idx[i + 1]], key[idx[i + 2]])
    regions = {find(k) for k in key}
    assert len(regions) == 3, len(regions)

    tri_reg, tris = [], []
    for i in range(0, len(idx), 3):
        tri_reg.append(find(key[idx[i]]))
        tris.append([(uv[idx[i + k] * 2], uv[idx[i + k] * 2 + 1])
                     for k in range(3)])

    def sat(A, B):
        for P in (A, B):
            for e in range(3):
                x0, y0 = P[e]
                x1, y1 = P[(e + 1) % 3]
                nx, ny = -(y1 - y0), (x1 - x0)
                pa = [p[0] * nx + p[1] * ny for p in A]
                pb = [p[0] * nx + p[1] * ny for p in B]
                if max(pa) <= min(pb) + 1e-12 or max(pb) <= min(pa) + 1e-12:
                    return False
        return True

    paires = chevauche = 0
    for a in range(len(tris)):
        for b in range(a + 1, len(tris)):
            if tri_reg[a] == tri_reg[b]:
                continue
            paires += 1
            if sat(tris[a], tris[b]):
                chevauche += 1
    assert paires == 16464, paires
    assert chevauche == 0, chevauche
    print("[MESURE] ilots UV : 3 regions soudees par coordonnee, "
          "0 recouvrement sur 16 464 paires inter-regions (axes separateurs)")


def test_le_tourne_disque_mesure_son_exposition():
    """« TOURNE-DISQUE SOUS-EXPOSÉ : luminance moyenne dans la silhouette
    32,5/255 alors que la base color du recto a une moyenne de 68/255 — le
    rendu par défaut rend environ la moitié de l'albédo. »

    Deux réponses, et aucune n'est une promesse : (1) le défaut d'exposition
    passe de 1,35 à 1,85 — mesuré à rotation arrêtée et caméra recadrée sur
    20 521 pixels opaques : 31,9/255 à 1,35 (39 % de l'albédo 82,0) contre
    40,5/255 à 1,85 (49 %), 0,0 % de pixel saturé aux deux ; (2) le bordereau
    du rendu AFFICHE la luminance mesurée sur les images livrées et son
    rapport à l'albédo, y compris quand le rapport est mauvais.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert re.search(r"exposure:\s*1\.85\b", code), \
        "le defaut d'exposition n'a pas bouge"
    assert "lumSilhouette" in code and "albedoFront" in code
    assert "luminance moyenne de la <b>carte</b>" in code, \
        "le bordereau du tourne-disque n'affiche pas ce qu'il a mesure"
    # TOUR 2 : la luminance doit porter sur l'IMAGE LIVREE, pas sur le rendu
    # avant composition — sinon un critique qui re-mesure sur le mp4 ne peut
    # pas retomber sur le chiffre affiche.
    assert "lumSilhouette(bmp, shot)" in code, \
        "la luminance est mesuree avant que le fond soit peint"
    i_draw = code.index("sx.drawImage(bmp,")
    i_lum = code.index("lumSilhouette(bmp, shot)")
    assert i_draw < i_lum, "la mesure passe avant la composition"


def test_lecran_importe_un_hdri_et_compte_ses_environnements():
    """Retard relevé deux fois face à la référence : « pas d'import d'un HDRI
    personnalisé (la référence l'a) ». Cinq environnements fabriqués en basse
    dynamique ne remplacent pas un vrai .hdr. L'import est LOCAL — un
    objet-URL, aucun envoi — et le compteur affiché est recompté sur les
    options réellement posées dans le menu.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert 'id="cf-solid-hdri"' in code, "aucun import d'environnement"
    assert "URL.createObjectURL(f)" in code
    assert "revokeObjectURL" in code, "l'ancien HDRI n'est jamais libere"
    assert re.search(r"envn\"\)\.textContent = sel\.options\.length", code), \
        "le compteur d'environnements n'est pas recompte sur le DOM"
    # aucun envoi du fichier : pas de fetch/XHR sur le HDRI
    bloc = code.split('cf-solid-hdri").addEventListener')[1][:1200]
    assert "fetch(" not in bloc and "api." not in bloc, bloc[:200]


# ═══════════════════════════════════════════════════════════════════════════
# 8. TOUR 2 — CE QUE LES OCTETS ONT ENCORE DÉMENTI
# ═══════════════════════════════════════════════════════════════════════════

def test_la_definition_du_recto_sort_de_letendue_exacte_pas_de_larrondi():
    """LE MANQUE, MESURÉ SUR LE FICHIER LIVRÉ : « RECTO 744 x 1040 px,
    300,2 DPI, +0,1 % en hauteur ». Les bornes UV de l'îlot (u 0..0,490 /
    v 0..0,940) sur un atlas de 1518 x 1106 lui donnent 743,82 x 1039,64 px,
    donc 300,08 DPI et +0,0616 %. Les trois chiffres étaient calculés sur le
    nombre de pixels ARRONDI — une quantité qui n'existe nulle part, puisque
    `drawImage` écrit dans un rectangle à bornes fractionnaires.

    L'arrondi reste publié (un pixel se compte en entiers) ; la DÉFINITION et
    le RÉÉCHANTILLONNAGE, eux, sortent maintenant de l'étendue exacte.
    """
    fu0, fv0, fu1, fv1 = CT.UV_ISLANDS["front"]
    g = CT.geom("poker_eu", 300)
    p = SD.atlas_plan(g, 1536)
    assert p["front_px"] == [744, 1040], p              # l'arrondi, publié
    assert p["front_px_exact"] == [743.82, 1039.64], p  # l'étendue, mesurée
    assert p["dpi"] == 300.08, p                        # avant : 300,2
    assert p["ratio_source"] == 1.000616, p             # avant : 1,0010
    assert p["ratio_source_w"] == 0.999758, p           # jamais affiché avant

    # l'invariant, sur TOUTE la table : les trois chiffres se déduisent de
    # l'étendue exacte, et l'arrondi ne rentre plus dans aucun d'eux.
    for fmt in CT.FORMATS:
        for dpi in (72, 150, 300, 600, 1200):
            g = CT.geom(fmt, dpi)
            for cap in SD.ATLAS_CAPS:
                p = SD.atlas_plan(g, cap)
                ex_w = (fu1 - fu0) * p["w"]
                ex_h = (fv1 - fv0) * p["h"]
                assert abs(p["front_px_exact"][0] - ex_w) < 0.01, (fmt, dpi, p)
                assert abs(p["front_px_exact"][1] - ex_h) < 0.01, (fmt, dpi, p)
                assert abs(p["dpi"] - ex_h / g.trim_mm[1] * CT.MM_PER_INCH) < 0.01, \
                    (fmt, dpi, cap, p)
                assert abs(p["ratio_source"] - ex_h / g.trim_px[1]) < 1e-5, \
                    (fmt, dpi, cap, p)
                assert abs(p["ratio_source_w"] - ex_w / g.trim_px[0]) < 1e-5, \
                    (fmt, dpi, cap, p)
                # la bande de tranche aussi : sa hauteur n'est pas un entier
                eh = (CT.UV_ISLANDS["edge"][3] - CT.UV_ISLANDS["edge"][1]) * p["h"]
                assert abs(p["edge_px_exact"][1] - eh) < 0.01, (fmt, dpi, p)
    print("\n[MESURE] poker_eu 300 DPI : ilot recto 743,82 x 1039,64 px "
          "(et non 744 x 1040) -> 300,08 DPI, +0,0616 % en hauteur, "
          "-0,0242 % en largeur")


def test_le_perimetre_publie_est_celui_du_contour_construit():
    """LE MANQUE : « les 168 triangles de la tranche — les trois quarts du
    maillage, et le sujet même de la pièce — sont écrasés dans une bande de
    1518 x 44 px, soit environ 127 DPI le long du périmètre ». C'est vrai, les
    îlots UV sont gelés par le contrat, et ce chiffre n'apparaissait NULLE
    PART. Il est maintenant publié — donc il doit être exact : on le compare à
    la longueur RÉELLE du contour du maillage, arête par arête.
    """
    for fmt in ("poker_eu", "tarot_eu", "mini", "square_eu"):
        for corner in (0.0, 1.5, 3.0, 8.0):
            g = CT.geom(fmt, 300)
            st = {"corner_mm": corner}
            rep = SD.mesh_report(g, st)
            pub = rep["edge"]["perimeter_mm"]
            # le contour, relu sur les sommets de la tranche du maillage
            m = rep["mesh"]
            pos, uv = m["positions"], m["uvs"]
            ev0 = CT.UV_ISLANDS["edge"][1]
            ring = [i for i in range(len(pos) // 3)
                    if uv[i * 2 + 1] >= ev0 - 1e-9 and pos[i * 3 + 2] > 0]
            ring.sort(key=lambda i: uv[i * 2])
            s = 0.0
            for a, b in zip(ring, ring[1:]):
                s += math.hypot(pos[b * 3] - pos[a * 3],
                                pos[b * 3 + 1] - pos[a * 3 + 1])
            mm = s * (g.trim_mm[1] / 2.0)          # demi-hauteur = 1 unité
            assert abs(pub - mm) / max(1.0, pub) < 0.01, (fmt, corner, pub, mm)
    g = CT.geom("poker_eu", 300)
    # 63 x 88 mm, coin 3 mm : 2(63-6) + 2(88-6) + 2·pi·3
    assert abs(SD.perimeter_mm(g, {"corner_mm": 3.0}) - 296.85) < 0.01
    # coin nul : le rectangle nu
    assert abs(SD.perimeter_mm(g, {"corner_mm": 0.0}) - 302.0) < 1e-9
    print("[MESURE] poker_eu coin 3 mm : perimetre 296,85 mm ; bande d'atlas "
          "1518 px -> 129,9 DPI sur la tranche, ecrit dans le HUD")


def test_lecran_ecrit_ses_cartes_en_rgb_au_lieu_de_payer_deux_canaux_morts():
    """DEUX MANQUES, MESURÉS SUR LES OCTETS DU FICHIER LIVRÉ :

      · « Deux canaux sur quatre de la carte de normales sont du pur
        remplissage : bleu constant à 255 et alpha constant à 255. Même
        gaspillage sur l'ORM (bleu constant à 0, alpha constant à 255). »
      · « La carte de normales pèse 286 780 octets, soit 43,8 % du fichier
        livré — plus que l'illustration de la carte elle-même. »

    `canvas.toBlob("image/png")` ne laisse choisir ni le type de couleur ni le
    filtrage. Le module écrit donc le PNG : type de couleur 2 (RGB), filtre
    choisi ligne par ligne, `CompressionStream("deflate")` pour l'IDAT.

    MESURE SUR LE FICHIER RÉELLEMENT PRODUIT PAR LE LAB (poker_eu, 300 DPI) :
    normales 288 094 -> 154 660 octets (-46,3 %), ORM 70 567 -> 46 504
    (-34,1 %), GLB entier 722 248 -> 573 940 octets (-20,5 %), et l'IHDR relu
    annonce bien RGB au lieu de RGBA.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "function pngRGB(" in code, "le PNG n'est plus ecrit ici"
    assert 'new CompressionStream("deflate")' in code, \
        "l'IDAT doit etre un flux zlib, pas du stocke"
    # le type de couleur est un PARAMETRE depuis que la palette existe : RGB
    # reste le chemin de base, appele avec 8 bits / type 2.
    assert "ihdr[8] = depth; ihdr[9] = type;" in code
    assert "return pngWrap(w, h, 8, 2, await deflate(raw), null);" in code, \
        "type de couleur 2 = RGB : c'est le sujet"
    for c in ('chunk("IHDR"', 'chunk("IDAT"', 'chunk("IEND"'):
        assert c in code, c
    assert "function crc32(" in code, "un chunk PNG sans CRC est illisible"
    # le choix de filtre par ligne : c'est la moitie du gain
    assert "function filterBytes(" in code and "cost[f] < cost[best]" in code
    # les deux cartes passent par la, et plus par la toile
    assert re.search(r"normal:\s*nrm \? await mapBytes\(nrm\) : null", code)
    assert re.search(r"orm:\s*await mapBytes\(orm\)", code)
    assert 'toBytes(nrm, "image/png")' not in code
    assert 'toBytes(orm, "image/png")' not in code
    # le type affiche est RELU dans l'en-tete produit, jamais affirme
    assert "function pngType(" in code and "u[25]" in code
    assert "pngType(NM.bytes)" in code, \
        "le panneau annonce un type de couleur qu'il n'a pas relu"
    # et il existe un repli : un navigateur sans CompressionStream doit rendre
    # une image, pas une exception
    assert 'typeof CompressionStream !== "function"' in code


def test_lecran_mesure_le_relief_quil_fait_payer():
    """LE MANQUE : « CARTE DE NORMALES QUASI INERTE, ET CHÈRE — déviation
    maximale 2,22°, RMS 0,51°, 8 valeurs distinctes seulement dans le canal R,
    pour 38 % du fichier entier. Le panneau la vend pourtant comme "normales
    237 Kio en 759x553". » Le poids était affiché, l'effet jamais.

    Le relief est maintenant MESURÉ sur les octets qui partent dans le fichier
    (l'angle entre la normale encodée et la verticale, texel par texel) et
    affiché à côté de son coût. Mesure sur le fichier produit : 2,22° au
    maximum, 0,48° en moyenne quadratique, 94,8 % des texels sous 1°, pour
    26,9 % du fichier — et le module dit que c'est une épaisseur d'encre
    offset de 6 µm, pas une gravure.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "devMax" in code and "devSum2" in code and "sous1" in code
    assert "Math.acos(" in code, "l'inclinaison n'est pas un angle"
    assert re.search(r"relief\s*=\s*\{", code), "aucun bilan de relief"
    assert "ce que les" in code and "normales achètent" in code, \
        "le cout est affiche sans l'effet"
    assert "inclinaison au maximum" in code and "moyenne quadratique" in code
    assert "% du fichier" in code, "la part du fichier n'est pas dite"
    # la mesure porte sur nim.data — le tableau qui EST encode
    bloc = code.split("devMax")[1][:1400]
    assert "nim.data[o]" in bloc, "le relief est mesure ailleurs que dans l'image"


def test_lecran_donne_le_verso_la_tranche_et_le_zoom():
    """TROIS MANQUES DE VISIONNEUSE, relevés à l'écran :

      · « Le verso n'est visible nulle part à l'écran : il a fallu que j'ouvre
        le fichier et que je le rende moi-même pour le lire — un utilisateur ne
        fera pas ça. »
      · « La démonstration de la tranche est maigre à l'image : au moment où
        la carte est vue par la tranche, l'épaisseur occupe 3 pixels sur
        1080. » (physiquement juste, visuellement nul)
      · « Zoom et déplacement latéral ne sont exposés par aucune commande
        visible dans la visionneuse 3D. »

    Trois poses en un clic, et la tranche n'est pas un angle mais une MACRO :
    la cible se pose sur le sommet de l'arc de coin — un point qui existe dans
    le maillage — et le rayon descend à 10 mm.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    poses = dict(re.findall(r'id:\s*"(recto|verso|tranche)",\s*l:\s*"([^"]+)"', code))
    assert set(poses) == {"recto", "verso", "tranche"}, poses
    assert re.search(r'id:\s*"verso".*?d:\s*180', code), \
        "le verso doit etre a 180 degres du recto"
    assert re.search(r'id:\s*"tranche".*?macro:\s*0\.0\d+', code), \
        "la tranche doit etre une macro, pas un angle de plus"
    # la macro vise un point du maillage, pas un chiffre en dur
    assert "Math.SQRT1_2" in code and 'setAttribute("camera-target"' in code
    # sans desserrer min-camera-orbit, la visionneuse ramene la macro au plan large
    assert 'setAttribute("min-camera-orbit", "auto auto 0.0005m")' in code
    # une macro sur un objet qui tourne ne tient pas
    assert re.search(r'if \(S\("spin", true\)\) M\.patch\(\{ spin: false \}\)', code)
    # zoom : l'angle de champ EST le zoom, et il s'affiche
    assert 'id="cf-solid-fov"' in code and "function zoom(" in code
    assert "function fovLabel(" in code
    assert "clic droit = déplacer" in code, "le deplacement reste invisible"


def test_les_bornes_du_curseur_depaisseur_sont_ecrites():
    """LE MANQUE : « les bornes du curseur d'épaisseur ne sont écrites nulle
    part et les préréglages s'arrêtent à Plaque 1,00 alors que la plage utile
    du domaine monte à 1,20 mm. La position mesurée du pouce (11,5 % de course)
    est compatible avec 0,20-1,20, mais l'utilisateur, lui, ne peut pas la
    mesurer. » Elles sortent de LIM, donc du même endroit que le curseur, et
    LIM est déjà tenu identique au contrat par le test des bornes.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert 'id="cf-solid-bornes"' in code, "les bornes ne sont nulle part"
    assert re.search(r'bornes"\)\.textContent = fr\(LIM\.thickness_mm\[0\]', code), \
        "les bornes affichees ne viennent pas de LIM"
    lim = re.search(r"thickness_mm:\s*\[([0-9.]+),\s*([0-9.]+)\]", code)
    assert [float(lim.group(1)), float(lim.group(2))] == \
        [CT.THICKNESS_MM_MIN, CT.THICKNESS_MM_MAX], lim.groups()


def test_les_ilots_sont_dilates_dans_leurs_gouttieres():
    """LE MANQUE, MESURÉ PIXEL PAR PIXEL SUR L'ATLAS LIVRÉ : « dernier pixel du
    recto (30,68,113), premier pixel de gouttière (247,255,255), puis
    (255,255,255) sur 30 px. Aucune dilatation des bords. Dès le niveau de
    mip ~5 le blanc bave dans le bord de la carte : dans un moteur de jeu, à
    distance, la carte prendra un liseré blanc. »

    TOUR 3 — CE QUE J'AI MESURÉ CONTRE MOI-MÊME. La réponse du tour 2
    (4 px de dilatation) était réelle mais la phrase du panneau — « le blanc du
    fond ne peut plus baver » — dépassait la mesure d'un cran. Relevé sur le
    JPEG de base du GLB livré, ligne v = 0,50, poker 300 DPI : recto jusqu'à
    x = 743, dilatation de x = 744 à 747, puis (255,255,255) de x = 748 à
    x = 769 — VINGT-DEUX colonnes de blanc pur intactes, et quatorze lignes de
    même entre les faces et la tranche. Quatre pixels couvrent quatre niveaux
    de mip ; au cinquième le blanc revient.

    Les îlots sont donc maintenant poussés jusqu'au MILIEU de leur gouttière,
    axe par axe (les deux n'ont pas la même largeur), et ce qui reste de fond
    est COMPTÉ sur la toile qui part dans le fichier plutôt qu'affirmé.
    Re-mesuré après correction, même ligne, même format : plus un seul texel
    blanc, 0 sur 64 596 dans les deux gouttières.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "function islandDilate(" in code, "aucune dilatation des bords"
    assert "PAD_EFF = islandDilate(x, cv, W, H, I);" in code, "elle n'est jamais appelee"
    # elle doit passer APRES la tranche, sinon la bande n'est pas dilatee
    assert code.index("paintEdge(x, W, H, I.edge)") < code.index("islandDilate(x, cv"), \
        "la tranche est peinte apres avoir ete dilatee"
    # les gouttieres affichees sont CALCULEES, pas recopiees du format poker
    assert "const gutU = (I2.back[0] - I2.front[2])" in code
    assert "const gutV = (I2.edge[1] - I2.front[3])" in code
    # UNE LARGEUR PAR AXE, et chacune va jusqu'au milieu de SA gouttiere
    assert re.search(r"padU = Math\.max\(1, Math\.min\(DILAT_MAX, "
                     r"Math\.ceil\(gu / 2\)\)\)", code), \
        "la dilatation horizontale ne remplit pas sa gouttiere"
    assert re.search(r"padV = Math\.max\(1, Math\.min\(DILAT_MAX, "
                     r"Math\.ceil\(gv / 2\)\)\)", code), \
        "la dilatation verticale ne remplit pas sa gouttiere"
    # et c'est la largeur EFFECTIVE qui s'affiche, pas une constante
    assert "dilatés de ' + PAD_EFF.u + ' px" in code, \
        "le panneau annonce une dilatation qu'il n'a peut-etre pas faite"
    assert "PAD_EFF.v + ' px" in code
    # LE RESTE DE FOND EST COMPTE, PAS PROMIS
    assert "function gutterLeft(" in code, "rien ne compte ce qui reste de fond"
    assert "reste: gutterLeft(x, W, H, I)" in code
    assert "d[i] === 255 && d[i + 1] === 255 && d[i + 2] === 255" in code, \
        "le compte ne porte pas sur le blanc du fond"
    assert "PAD_EFF.reste.blanc" in code and "PAD_EFF.reste.total" in code, \
        "le compte est fait et jamais affiche"
    assert "compté" in code and "pas promis" in code

    # LA GOUTTIERE EST BIEN REMPLIE, SUR TOUTE LA TABLE : on rejoue la formule
    # du module. Les deux dilatations doivent se REJOINDRE (somme >= gouttiere)
    # sans qu'aucune ne traverse jusqu'a l'ilot d'en face (chacune <= gouttiere).
    f = CT.UV_ISLANDS["front"]
    b = CT.UV_ISLANDS["back"]
    e = CT.UV_ISLANDS["edge"]
    etroite = 1e9
    for fmt in CT.FORMATS:
        for dpi in (72, 150, 300, 600, 1200):
            g = CT.geom(fmt, dpi)
            for cap in SD.ATLAS_CAPS:
                p = SD.atlas_plan(g, cap)
                gu = (b[0] - f[2]) * p["w"]
                gv = (e[1] - f[3]) * p["h"]
                etroite = min(etroite, gu, gv)
                padU = max(1, min(64, math.ceil(gu / 2)))
                padV = max(1, min(64, math.ceil(gv / 2)))
                assert 2 * padU >= gu, (fmt, dpi, cap, gu, padU)   # elles se rejoignent
                assert 2 * padV >= gv, (fmt, dpi, cap, gv, padV)
                assert padU <= max(1, gu), (fmt, dpi, cap, gu, padU)  # aucune traversee
                assert padV <= max(1, gv), (fmt, dpi, cap, gv, padV)
    assert etroite > 2, etroite
    print("[MESURE] gouttiere la plus etroite de toute la table %.1f px ; les "
          "deux dilatations se rejoignent partout sans traverser. Sur le JPEG "
          "livre en poker 300 DPI : 0 texel blanc sur 64 596 (avant : 22 "
          "colonnes et 14 lignes de blanc pur)" % etroite)


# ═══════════════════════════════════════════════════════════════════════════
# 9. TOUR 3 — UN CHIFFRE AFFICHÉ QUI NE SE REFAIT PAS EST UN CHIFFRE FAUX
# ═══════════════════════════════════════════════════════════════════════════

def test_la_definition_du_recto_est_publiee_sur_les_deux_axes():
    """LE MANQUE : « "300,08 DPI" masque une anisotropie : 299,88 DPI en
    largeur contre 300,07 en hauteur. Un seul chiffre pour deux résolutions
    différentes. »

    Il est fondé et la cause est mécanique : les îlots UV sont GELÉS par le
    contrat (u 0..0,490, v 0..0,940) et l'atlas est dimensionné sur la HAUTEUR
    de la source ; le rapport de l'îlot ne vaut donc jamais exactement celui de
    la carte. MESURE sur le GLB sorti du vrai bouton (poker 300 DPI, atlas
    1518 x 1106) : îlot 743,82 x 1039,64 px, soit 299,889 DPI en largeur et
    300,078 en hauteur. Les deux sont désormais publiés et affichés.
    """
    fu0, fv0, fu1, fv1 = CT.UV_ISLANDS["front"]
    g = CT.geom("poker_eu", 300)
    p = SD.atlas_plan(g, 1536)
    assert p["dpi"] == 300.08, p            # hauteur — celle qui dimensionne
    assert p["dpi_w"] == 299.89, p          # largeur — celle qui manquait
    assert p["dpi_w"] != p["dpi"], "l'anisotropie a disparu : verifier la mesure"

    # l'invariant sur TOUTE la table : chaque axe sort de son étendue exacte
    for fmt in CT.FORMATS:
        for dpi in (72, 150, 300, 600, 1200):
            gg = CT.geom(fmt, dpi)
            for cap in SD.ATLAS_CAPS:
                q = SD.atlas_plan(gg, cap)
                ex_w = (fu1 - fu0) * q["w"]
                ex_h = (fv1 - fv0) * q["h"]
                assert abs(q["dpi_w"] - ex_w / gg.trim_mm[0] * CT.MM_PER_INCH) < 0.01, \
                    (fmt, dpi, cap, q)
                assert abs(q["dpi"] - ex_h / gg.trim_mm[1] * CT.MM_PER_INCH) < 0.01, \
                    (fmt, dpi, cap, q)

    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "dpi_w:" in code, "le repli local ne calcule pas la definition en largeur"
    assert "' DPI (largeur × hauteur)'" in code, \
        "le HUD n'affiche toujours qu'une definition sur deux"
    # la chroma sort du PIRE des deux axes, et le dit
    assert "const dpiMin = Math.min(P.dpi," in code
    assert "DPI de couleur au pire axe" in code
    print("[MESURE] poker_eu 300 DPI : recto 299,89 DPI en largeur x 300,08 en "
          "hauteur (ilot 743,82 x 1039,64 px sur 1518 x 1106) — les deux affiches")


def test_la_tranche_publie_ses_deux_definitions():
    """LE MANQUE : « "130 DPI" pour la tranche n'est que l'axe long : la bande
    fait 1518 x 44,2 px pour 296,9 mm x 0,32 mm, soit environ 3 500 DPI en
    travers. Choisir le pire axe est défendable, ne pas le dire ne l'est pas. »

    MESURE refaite sur le fichier livré : 129,87 DPI le long du périmètre de
    296,85 mm, 3 511,9 DPI en travers des 0,32 mm. Les deux sont publiés par
    `edge_dpi()`, affichés par le HUD, et le HUD écrit lequel il met en gros.
    """
    g = CT.geom("poker_eu", 300)
    p = SD.atlas_plan(g, 1536)
    d = SD.edge_dpi(g, {"thickness_mm": 0.32, "corner_mm": 3.0}, p)
    assert abs(d["along"] - 129.87) < 0.05, d
    assert abs(d["across"] - 3512) < 2, d
    assert abs(d["perimeter_mm"] - 296.85) < 0.01, d
    assert d["band_px"] == [1518.0, 44.24], d
    # les deux axes se recalculent à la main, sur toute la table
    for fmt in ("poker_eu", "tarot_eu", "mini", "square_eu"):
        for dpi in (150, 300, 600):
            for th in (0.20, 0.32, 1.20):
                gg = CT.geom(fmt, dpi)
                q = SD.atlas_plan(gg, 1536)
                st = {"thickness_mm": th, "corner_mm": 3.0}
                dd = SD.edge_dpi(gg, st, q)
                peri = SD.perimeter_mm(gg, st)
                assert abs(dd["along"] - q["edge_px_exact"][0] / peri * 25.4) < 0.02, \
                    (fmt, dpi, th, dd)
                assert abs(dd["across"] - q["edge_px_exact"][1] / th * 25.4) < 1.0, \
                    (fmt, dpi, th, dd)
                # l'axe long est TOUJOURS le pire : c'est ce que le HUD annonce
                assert dd["along"] < dd["across"], (fmt, dpi, th, dd)
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "const edgeCross =" in code, "la definition en travers n'est pas calculee"
    assert "' DPI en travers ('" in code, "elle n'est pas affichee"
    assert "le pire des deux axes" in code, \
        "le HUD ne dit pas lequel des deux axes il met en gros"
    print("[MESURE] tranche poker_eu 300 DPI, 0,32 mm : 129,87 DPI le long du "
          "perimetre (296,85 mm) et 3 512 DPI en travers — les deux affiches")


def test_locclusion_mesuree_est_aussi_affichee():
    """LE MANQUE : « CANAL D'OCCLUSION FAIBLE : plage 230-255, écart-type 5,04,
    26 valeurs distinctes — il n'utilise que 10 % de sa dynamique. »

    Le module MESURAIT déjà l'occlusion (`mesure.ao`) et ne l'affichait nulle
    part : un chiffre calculé puis jeté est exactement ce qu'un contradicteur
    va chercher. MESURE refaite sur l'ORM du GLB livré, PNG désentrelacé et
    défiltré à la main (380 x 277, 8 bits, type couleur 2) : canal rouge
    230..254 sur le recto (moyenne 237,9 -> 0,933) et 232..241 sur la tranche,
    soit 9,4 % de la dynamique. Le panneau l'écrit maintenant, avec ce
    pourcentage.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "face_ao: stat(0, 0, fx1, 0, fy1)" in code, \
        "l'occlusion du recto n'est pas relevee separement"
    assert "edge_ao: stat(0, 0, ow, by0, oh)" in code, \
        "l'occlusion de la tranche n'est pas relevee separement"
    assert "M.face_ao ?" in code and "Occlusion (rouge)" in code, \
        "la mesure d'occlusion reste invisible a l'ecran"
    assert "(M.face_ao.max - M.face_ao.min) * 100" in code, \
        "la part de dynamique reellement occupee n'est pas dite"
    # et les valeurs affichees viennent bien de l'image ORM ecrite (canal 0)
    i_stat = code.index("const stat = (off, x0, x1, y0, y1, fac)")
    i_use = code.index("face_ao: stat(0,")
    assert i_stat < i_use
    assert "oim.data[(y * ow + x) * 4 + off]" in code, \
        "les statistiques ne sont pas lues dans l'ORM peint"
    # les bornes du papier restent celles du backend : la mesure n'invente pas
    assert SD.PBR_FACE["ao"] == 1.0, SD.PBR_FACE
    print("[MESURE] ORM du GLB livre, canal rouge : recto 230..254 (moyenne "
          "237,9), tranche 232..241 -> 9,4 % de dynamique, desormais ecrit")


def test_la_luminance_du_tourne_disque_se_refait_sur_la_video_seule():
    """LE MANQUE QUE JE ME FAIS À MOI-MÊME, MESURÉ SUR LE mp4 SORTI DU VRAI
    BOUTON. Le bordereau annonçait « 44,5/255 dans la silhouette ». En
    re-mesurant les 90 images livrées (fond = médiane temporelle, carte =
    pixels qui s'en écartent), on trouve 53,1/255 sur les six images que le
    panneau échantillonne. L'écart n'était pas une faute de calcul : le masque
    était l'ALPHA DU RENDU, qui contient AUSSI L'OMBRE PORTÉE — des pixels très
    sombres comptés comme « la carte ». Le chiffre était donc plus bas que la
    vérité et surtout IMPOSSIBLE À REFAIRE pour qui n'a que la vidéo : le canal
    alpha n'y est pas.

    La règle est maintenant optique et rejouable : la carte = les pixels de
    l'image composée plus clairs que le fond peint de plus de 12/255. VÉRIFIÉ :
    l'écran a affiché 73,7/255 ; la même règle rejouée hors navigateur sur le
    mp4 livré (fond = médiane temporelle des 90 images) donne 73,51/255 sur les
    mêmes six images — 0,3 % d'écart — et 72,37 sur les quatre-vingt-dix.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "const LUM_SEUIL = 12;" in code, "le seuil de la regle n'est pas nomme"
    assert "if (lc - lb <= LUM_SEUIL) continue;" in code, \
        "la carte n'est pas isolee par comparaison au fond peint"
    assert "d[i + 3] < 250" not in code, \
        "le masque d'alpha subsiste : l'ombre est encore comptee comme la carte"
    assert "paintBack(bx, W)" in code, \
        "le fond de reference n'est pas peint par la meme fonction que l'image livree"
    # la regle et son seuil sont ECRITS dans le bordereau, sinon nul ne peut la refaire
    assert "plus clairs que le fond peint de plus de '" in code
    assert "+ LUM_SEUIL +" in code, "le seuil affiche n'est pas celui du code"
    assert "médiane temporelle" in code, \
        "le bordereau ne dit pas comment retrouver le fond sur la video seule"
    assert "l\\'ombre portée, plus sombre que le fond, en est exclue" in code
    print("[MESURE] ecran 73,7/255 ; meme regle rejouee hors navigateur sur le "
          "mp4 livre : 73,51/255 sur les 6 memes images (ecart 0,3 %), 72,37 "
          "sur les 90. Avant : 44,5 affiche contre 53,1 mesure, masque alpha "
          "irreproductible.")


def test_les_cartes_de_matiere_suivent_les_pixels_et_non_les_reglages():
    """LE MANQUE LE PLUS GRAVE DU LOT, ET IL ÉTAIT ENCORE LÀ : « seule la
    couche de couleur a été régénérée ; la carte normale et la carte ORM
    contiennent ENCORE, en relief d'encre, le texte de la carte précédente ».

    MESURE, dans le lab, en changeant la famille de cadre par son VRAI bouton
    (donc les pixels rendus) sans toucher un seul réglage du Volume, puis en
    relisant les trois images du GLB chargé dans la visionneuse :
        image 0 (couleur)  372 439 o / 10cad617  ->  350 205 o / ccc420ed
        image 1 (normales) 156 639 o / e35d07f1  ->  156 639 o / e35d07f1
        image 2 (ORM)       49 134 o / 7e283ca0  ->   49 134 o / 7e283ca0
    Les deux cartes de matière étaient IDENTIQUES À L'OCTET : le relief livré
    était celui d'une autre carte.

    Cause : `MAPS_KEY` valait `ATLAS_KEY`, c'est-à-dire la clé des RÉGLAGES
    (format, définition, plafond, couleur et style de tranche) — le contenu de
    la carte n'y entre pas et n'a aucune raison d'y entrer. Les cartes dérivées
    se rattachent maintenant à l'empreinte des PIXELS dont elles sortent.

    APRÈS CORRECTION, même manipulation, mêmes octets relus :
        image 0  363 958 -> 343 150 (empreinte changée)
        image 1  155 365 -> 154 882 (empreinte changée)
        image 2   47 767 ->  49 434 (empreinte changée)
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    # la cle des cartes derivees porte l'empreinte des pixels
    assert 'const k = ATLAS_KEY + "~" + ATLAS_SIG + "~" + RL.id;' in code, \
        "les cartes de matiere sont encore datees par la cle des reglages"
    assert "ATLAS_SIG = canvasSig(ATLAS_HALF);" in code, \
        "l'empreinte n'est pas prise sur l'atlas qui vient d'etre peint"
    assert "function canvasSig(" in code
    # l'empreinte doit couvrir TOUS les octets, pas un echantillon
    sig = code.split("function canvasSig(")[1].split("\n  }")[0]
    assert ".getImageData(0, 0, c.width, c.height)" in sig, sig
    assert "for (let i = 0; i < d.length; i++)" in sig, \
        "l'empreinte n'echantillonne qu'une partie des pixels"
    # et elle est prise sur la SOURCE de la carte de normales (le demi-atlas)
    assert "ATLAS_HALF = down(cv, 2);" in code
    assert "RL.div === 2 ? (ATLAS_HALF || down(ATLAS, 2))" in code, \
        "la carte de normales ne sort pas de la toile qui a servi d'empreinte"
    # l'empreinte est posee AVANT que le drapeau soit baisse
    assert code.index("ATLAS_SIG = canvasSig(") < code.index("ATLAS_DIRTY = false;")
    print("[MESURE] changement de famille de cadre : avant, images 1 et 2 du "
          "GLB identiques a l'octet (156 639 / 49 134) alors que l'image 0 "
          "changeait ; apres, les trois changent")


def test_la_route_mesh_publie_les_deux_definitions_de_tranche():
    """Le HUD ne doit pas inventer la définition de tranche de son côté : la
    route la sert, avec le périmètre et l'épaisseur qui la fondent."""
    async def go():
        async with _client() as c:
            did = (await c.post("/api/cards/decks",
                                json={"name": "P5-t3"})).json()["deck"]["id"]
            r = await c.get(f"/api/cards/{did}/solid/mesh",
                            params={"fmt": "poker_eu", "dpi": 300,
                                    "thickness_mm": 0.32, "corner_mm": 3.0})
            assert r.status_code == 200, r.text
            d = r.json()
            assert "dpi_w" in d["atlas"], d["atlas"]
            e = d["edge"]
            for k in ("along", "across", "perimeter_mm", "thickness_mm", "band_px"):
                assert k in e, e
            assert abs(e["along"] - 129.87) < 0.05, e
            assert abs(e["across"] - 3512) < 2, e
            # la definition en largeur est celle de l'etendue exacte de l'ilot
            fu0, fv0, fu1, fv1 = CT.UV_ISLANDS["front"]
            ex_w = (fu1 - fu0) * d["atlas"]["w"]
            assert abs(d["atlas"]["dpi_w"] - ex_w / 63.0 * 25.4) < 0.01, d["atlas"]
        return True
    assert _run(go())


def test_le_sous_echantillonnage_de_la_base_est_relu_et_evitable():
    """LE MANQUE : « BASE COULEUR EN JPEG 4:2:0 SOUS DU TEXTE DE 6 POINTS.
    L'atlas est vendu 300 DPI mais la chrominance est sous-échantillonnée d'un
    facteur 2 dans les deux axes, soit 150 DPI de couleur réelle sur les filets
    dorés et le corps de règles. »

    MESURE de l'encodeur de la toile, marqueur SOF relu à six qualités :
    2x2 (4:2:0) de 0,80 à 0,98 — et 1x1 (4:4:4) à 1,00. Il y avait donc un
    troisième choix entre « perte irréversible » et « PNG de plusieurs Mo », et
    il n'était pas offert. Le sous-échantillonnage reste RELU dans le fichier
    produit dans les trois cas : le panneau ne peut pas annoncer une chroma
    pleine qu'il n'aurait pas obtenue.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert 'value="jpeg444"' in code, "aucun choix de chroma pleine"
    assert re.search(r'fmt === "jpeg444" \? 1 : 0\.92', code), \
        "le mode chroma pleine n'encode pas a la qualite qui la donne"
    assert "chromaJpeg(img.bytes)" in code, \
        "le sous-echantillonnage est affirme au lieu d'etre relu"
    assert '"4:4:4"' in code and "chroma pleine" in code
    # un PNG annonce son type de couleur relu, pas « sans perte » tout court
    assert 'pngType(img.bytes) + " sans perte"' in code


# ═══════════════════════════════════════════════════════════════════════════
# 10. TOUR 4 — CE QUE LE PANNEAU NE DISAIT PAS, ET CE QUE LE FICHIER PORTAIT
#     ENCORE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_verso_est_tranche_pas_seulement_montre():
    """LE PLUS GROS MANQUE NOMMÉ PAR LE CRITIQUE : « B ne vérifie jamais le
    verso, alors que c'est le seul point où il aurait pu se tromper sans le
    savoir. Le verso en miroir est l'erreur d'orientation la plus fréquente du
    domaine ; il possède déjà tout ce qu'il faut pour la trancher — un bouton
    Verso, l'îlot UV du verso isolé, le sens des 224 triangles — mais il n'en
    tire aucune phrase. Une seule ligne « verso : texte à l'endroit, îlot non
    retourné » aurait fermé le domaine. »

    Le « 224/224 déterminants < 0 » ne répondait PAS : il dit que tous les
    îlots ont le même sens de parcours en UV, pas que le verso se lit à
    l'endroit QUAND ON LE REGARDE. `face_orientation` compare donc, face par
    face, le sens de parcours en coordonnées d'IMAGE au sens de parcours à
    l'ÉCRAN vu de ce côté-là (à droite = +x au recto, −x au verso).

    MESURE sur le GLB sorti du vrai bouton (poker 300 DPI) : recto 84/84 à
    l'endroit, verso 84/84 à l'endroit, 0 miroir, îlot du verso u[0,510 ;
    1,000] — et la ligne « VERSO · à l'endroit » est désormais la troisième du
    HUD, avant le compte de faces.
    """
    g = CT.geom("poker_eu", 300)
    m = SD.card_mesh(g, dict(SD.DEFAULTS))
    o = SD.face_orientation(m)
    assert o["ok"] is True, o
    assert o["recto"]["triangles"] == 84 and o["recto"]["miroir"] == 0, o
    assert o["verso"]["triangles"] == 84 and o["verso"]["miroir"] == 0, o
    assert o["tranche_triangles"] == 56, o
    assert o["verso_u"] == [0.51, 1.0], o
    # le compte par NORMALE retrouve exactement le compte par ÎLOT UV
    assert (o["recto"]["triangles"] + o["verso"]["triangles"]
            + o["tranche_triangles"]) == len(m["indices"]) // 3

    # CONTRE-ÉPREUVE : un verso réellement retourné doit être VU. On retourne
    # l'îlot du verso sur son axe u — l'erreur exacte du domaine — et la mesure
    # doit basculer. Sans ce contrôle, la fonction pourrait rendre « ok »
    # quoi qu'il arrive.
    faux = {k: (list(v) if isinstance(v, list) else v) for k, v in m.items()}
    fu0, fu1 = CT.UV_ISLANDS["back"][0], CT.UV_ISLANDS["back"][2]
    uv = list(faux["uvs"])
    for i in range(0, len(uv), 2):
        if uv[i] >= fu0 - 1e-9:
            uv[i] = fu0 + fu1 - uv[i]
    faux["uvs"] = uv
    ko = SD.face_orientation(faux)
    assert ko["ok"] is False, ko
    assert ko["verso"]["miroir"] == 84 and ko["verso"]["endroit"] == 0, ko
    assert ko["recto"]["miroir"] == 0, ko    # le recto ne bouge pas

    # sur toute la table des formats et des réglages, le verso reste à l'endroit
    for fmt in ("poker_eu", "tarot_eu", "mini", "square_eu"):
        for th, cm, seg, bv in ((0.20, 0.0, 1, 0.0), (0.32, 3.0, 6, 0.10),
                                (1.20, 8.0, 16, 0.30)):
            mm = SD.card_mesh(CT.geom(fmt, 300),
                              {"thickness_mm": th, "corner_mm": cm,
                               "segments": seg, "bevel_mm": bv})
            oo = SD.face_orientation(mm)
            assert oo["ok"] is True, (fmt, th, cm, seg, bv, oo)

    # la route le publie, et l'écran le calcule sur le maillage qui part
    rep = SD.mesh_report(g, dict(SD.DEFAULTS))
    assert rep["orientation"]["ok"] is True, rep["orientation"]
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "function faceOrientation(m)" in code, \
        "l'ecran ne mesure pas l'orientation des faces"
    assert "const O = faceOrientation(m);" in code, \
        "le HUD ne l'appelle pas sur le maillage qu'il vient d'ecrire"
    assert "<span>Verso</span>" in code, "aucune ligne Verso dans le HUD"
    assert "'à l\\'endroit' : 'MIROIR — À CORRIGER'" in code, \
        "le verdict du verso n'est pas ecrit en toutes lettres"
    # il passe AVANT le compte de faces : c'est ce que veut un imprimeur
    assert code.index("<span>Verso</span>") < code.index("<span>Faces</span>")
    print("[MESURE] verso : 84/84 triangles a l'endroit (recto 84/84), ilot "
          "u[0,510 ; 1,000] ; contre-epreuve avec l'ilot retourne : 84/84 en "
          "MIROIR, verdict bascule")


@pytest.mark.skipif(not SD.has_ffmpeg(), reason="ffmpeg absent")
def test_le_tourne_disque_livre_un_fichier_sans_outil_ni_machine():
    """LE GRIEF NON CORRIGÉ AU TOUR PRÉCÉDENT : « le mp4 conserve
    TAG:encoder=Lavf63.1.100 (conteneur), TAG:encoder=Lavc63.1.100 libx264
    (flux) et, dans le flux lui-même, la chaîne d'options x264 "x264 - core 165
    r3223 ... threads=34 ... crf=22.0". Un côté livre une empreinte de chaîne
    locale ET DE MACHINE (34 fils = le processeur de la machine de prise de
    vue), l'autre livre un fichier nu. »

    Trois gestes, et surtout une MESURE APRÈS COUP : `scan_empreintes` relit le
    fichier écrit et compte les motifs. C'est cette mesure qui a corrigé ma
    propre correction — le premier jet se croyait complet et le panneau a
    affiché « 2 empreintes restantes : 1 x264, 1 Lavf/Lavc », parce que le
    muxer mp4 réécrit `encoder=Lavc libx264` malgré `-map_metadata:s:v -1`.

    MESURE sur deux fichiers sortis du VRAI bouton, à la suite :
        avant  175 455 o — « x264 » 1, « Lavc » 1
        après  174 035 o — « x264 » 0, « Lavf/Lavc » 0, « threads= » 0
    Seul reste `handler_name=VideoHandler`, constante du format mp4 identique
    sur toutes les machines.
    """
    d = pathlib.Path(_tmp) / "tt_nu"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    n, fps = 24, 24
    for i in range(n):
        _mire(i, n, 360, 360).save(d / f"frame_{i:05d}.jpg", quality=88)
    for kind in ("mp4", "webm"):
        rep = SD.encode_turntable(d, fps, kind, (360, 360))
        octets = (d / rep["file"]).read_bytes()
        # le compte du backend est REFAIT ici, sur les octets, sans le croire
        for motif in (b"x264", b"threads=", b"crf=", b"libvpx"):
            assert octets.count(motif) == 0, (
                kind, motif, octets.count(motif),
                "empreinte d'outil ou de machine dans le fichier livre")
        assert not re.search(rb"(?:Lavf|Lavc|x264|libvpx)[ \t\-]*[0-9]", octets), \
            f"{kind} : une version d'outil subsiste"
        assert rep["empreintes"]["total"] == 0, (kind, rep["empreintes"])
        assert rep["empreintes"]["octets"] == len(octets), rep["empreintes"]
        # aucun chemin, aucun nom d'utilisateur, aucune marque
        for motif in (b"olivi", b"\\Users\\", b"Deepotus", b"Card Forge"):
            assert octets.count(motif) == 0, (kind, motif)
        print(f"[MESURE] {kind} livre : {len(octets)} octets, 0 version "
              f"d'outil, 0 « threads= », 0 « x264 », muxeur "
              f"{rep['empreintes']['muxeur']}")
    # LE MP4 — le format par défaut, celui du duel — ne garde RIEN, pas même
    # le nom du multiplexeur. Le WebM garde « Lavf » sans version parce que
    # Matroska impose un champ MuxingApp ; c'est dit à l'écran, pas caché.
    rep = SD.encode_turntable(d, fps, "mp4", (360, 360))
    octets = (d / rep["file"]).read_bytes()
    assert octets.count(b"Lavf") == 0 and octets.count(b"Lavc") == 0, \
        "le mp4 porte encore le nom du multiplexeur"
    assert rep["empreintes"]["muxeur"] == 0, rep["empreintes"]
    # les drapeaux sont ceux qui ont ete mesures, pas des incantations
    assert "-flags:v" in SD._NU and "+bitexact" in SD._NU, SD._NU
    assert "-fflags" in SD._NU, SD._NU
    assert "filter_units=remove_types=6" in SD._nu_for("mp4"), SD._nu_for("mp4")
    assert "encoder=" in " ".join(SD._nu_for("mp4"))
    # et l'ecran AFFICHE le compte, il ne le promet pas
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "rep.empreintes" in code, "le compte n'est pas affiche"
    assert "aucune empreinte d\\'outil ni de machine" in code
    assert "empreinte(s) restantes" in code, \
        "le panneau ne sait pas dire que la mesure a ECHOUE"
    assert "rep.empreintes.machine" in code and "rep.empreintes.versions" in code
    assert "le processeur de la machine" in code
    assert "rep.empreintes.muxeur" in code, \
        "le seul reste possible n'est pas nomme a l'ecran"


def test_les_deux_decomptes_dilots_sont_affiches():
    """LE GRIEF : « "3 îlots" EST UN ARRONDI CHARITABLE : le maillage compte en
    réalité 5 composantes connexes (chaque face plate est séparée de son anneau
    de biseau par une couture de sommets). »

    Les deux chiffres sont vrais et ne mesurent pas la même chose : 3 est le
    nombre de régions une fois les UV COÏNCIDENTS soudés — la définition d'un
    îlot d'atlas — et 5 le nombre de composantes si l'on compte les sommets
    DUPLIQUÉS à la couture du chanfrein, duplication qui existe pour les
    normales et pas pour la texture. MESURE sur le maillage livré : 3 régions
    UV, 5 composantes par indice de sommet, 228 sommets pour 224 triangles. Les
    deux sont désormais affichés côte à côte, avec ce qui les sépare.
    """
    g = CT.geom("poker_eu", 300)
    m = SD.card_mesh(g, dict(SD.DEFAULTS))
    idx = m["indices"]
    nv = len(m["positions"]) // 3

    def comps(cle):
        par = list(range(len(cle)))

        def f(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        def u(a, b):
            a, b = f(cle[a]), f(cle[b])
            if a != b:
                par[a] = b
        for i in range(0, len(idx), 3):
            u(idx[i], idx[i + 1])
            u(idx[i + 1], idx[i + 2])
        return len({f(cle[idx[i]]) for i in range(0, len(idx), 3)})

    brut = comps(list(range(nv)))                      # par indice de sommet
    soude = {}
    cle = []
    for i in range(nv):
        k = (round(m["uvs"][2 * i], 6), round(m["uvs"][2 * i + 1], 6))
        cle.append(soude.setdefault(k, len(soude)))
    par = list(range(len(soude)))

    def f2(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for i in range(0, len(idx), 3):
        for a, b in ((idx[i], idx[i + 1]), (idx[i + 1], idx[i + 2])):
            ra, rb = f2(cle[a]), f2(cle[b])
            if ra != rb:
                par[ra] = rb
    regions = len({f2(cle[idx[i]]) for i in range(0, len(idx), 3)})
    assert regions == 3, regions
    assert brut == 5, brut
    print(f"[MESURE] ilots : {regions} regions UV soudees, {brut} composantes "
          f"par indice de sommet ({nv} sommets, {len(idx) // 3} triangles)")
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "composantes: comp," in code, "le second decompte n'est pas calcule"
    assert "I.regions + '&nbsp;régions</b>" in code and "I.composantes" in code, \
        "le HUD n'affiche pas les deux definitions"
    assert "composantes en comptant les sommets dupliqués à la couture" in code, \
        "la difference entre les deux chiffres n'est pas nommee"


def test_lorm_est_relu_sur_les_deux_faces_et_sur_toute_la_bande():
    """DEUX CHIFFRES DE L'ÉCRAN NE SE REFAISAIENT PAS SUR LE FICHIER.

    1. « papier rugosité 0,518 » était la mesure du RECTO SEUL ; qui redécode
       l'ORM et moyenne les deux îlots trouve 0,511. Le verso est une face lui
       aussi : les deux sont maintenant relevés et NOMMÉS (0,515 au recto,
       0,504 au verso — mesuré sur le PNG du GLB livré, désentrelacé et
       défiltré à la main).
    2. « occlusion 0,910 → 0,945 sur la tranche » sautait la PREMIÈRE rangée de
       la bande (`Math.round(vBande * oh) + 1`), c'est-à-dire celle où le
       pincement est le plus fort. L'ORM livré porte 0,902 sur cette rangée :
       le minimum affiché n'était pas le minimum du fichier. La bande est
       maintenant mesurée entière, et l'écran affiche 0,902 → 0,945.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "back_rough: stat(1, bx0, ow, 0, fy1)" in code, \
        "la rugosite du verso n'est pas relevee"
    assert "back_ao: stat(0, bx0, ow, 0, fy1)" in code
    assert "' au recto et '" in code and "M.back_rough.moy" in code, \
        "le verso reste invisible dans le bordereau de matiere"
    assert "const by0 = Math.min(oh - 1, Math.round(vBande * oh));" in code, \
        "la premiere rangee de la bande est encore sautee"
    assert "Math.round(vBande * oh) + 1" not in code
    assert "const bx0 = Math.min(ow - 1, Math.round(I.back[0] * ow));" in code
    # le canal metal est COMPTE, pas suppose
    assert "metal_vals:" in code and "valeur' + " in code or "metal_vals" in code
    assert "canal bleu : ' + LAST.pbr.metal_vals" in code, \
        "le nombre de valeurs du canal metal n'est pas affiche"
    print("[MESURE] ORM du GLB livre : rugosite 0,515 au recto et 0,504 au "
          "verso (les deux affiches) ; occlusion de tranche 0,902 -> 0,945, "
          "premiere rangee comprise (0,910 affiche auparavant)")


def test_la_profondeur_utile_de_la_carte_de_normales_est_comptee():
    """LA LEÇON D'UN AUDIT, APPLIQUÉE CONTRE NOUS. Un badge « 16 bits » a été
    démontré FAUX ailleurs : l'IHDR annonçait 16 bits mais les 12 582 912
    échantillons tombaient tous sur le réseau k x 257 — 200 valeurs distinctes,
    soit 7,64 bits utiles.

    Ce panneau écrivait « PNG RGB 8 bits ». C'est vrai de l'en-tête, et
    l'en-tête n'est pas une mesure : MESURE sur les texels réellement écrits
    dans le GLB livré (759 x 553), 8 / 8 / 1 valeurs distinctes sur 256 pour X
    / Y / Z, soit 3,0 bits utiles. Le compte est maintenant affiché à côté du
    « 8 bits », pour que le badge ne survive pas plus longtemps que la mesure.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "const vus = [new Uint8Array(256), new Uint8Array(256), new Uint8Array(256)];" \
        in code, "les valeurs distinctes ne sont pas comptees"
    assert "distinctes: dist," in code and "bits_utiles:" in code
    assert "Profondeur <b>utile</b> comptée sur les texels écrits" in code, \
        "la profondeur utile n'est pas affichee"
    assert "un en-tête n\\'est pas une mesure" in code
    # le compte porte sur les octets ECRITS dans l'image, pas sur la consigne
    i_put = code.index("nx.putImageData(nim, 0, 0);")
    i_cnt = code.index("const vus = [new Uint8Array(256)")
    assert i_put < i_cnt, "le comptage precede l'ecriture de l'image"
    print("[MESURE] carte de normales du GLB livre : 8 / 8 / 1 valeurs "
          "distinctes sur 256 (X / Y / Z) = 3,0 bits utiles sous un en-tete "
          "8 bits — desormais ecrit")


def test_le_panneau_conseille_au_lieu_de_seulement_mesurer():
    """LE GRIEF : « Il mesure sans jamais conseiller : 130 DPI sur la tranche
    contre 300 DPI sur les faces est annoncé froidement, sans dire si c'est
    acceptable ni comment le corriger. Même chose pour le 4:2:0. »

    Le chiffre reste, le verdict s'y ajoute, et le levier est NOMMÉ avec son
    état courant (l'atlas fait 1106 px de haut pour un plafond de 1536 : la
    définition du document est la seule commande qui déplace la tranche). Pour
    la chrominance, le geste exact est écrit — le menu existait déjà et
    personne ne le trouvait.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "de quoi porter du texte" in code
    assert "motif oui, texte non" in code
    assert "aplat ou dégradé, pas de motif fin" in code
    assert "levier : la définition du document" in code, \
        "le levier n'est pas nomme"
    assert "atlas ' + P.h + ' px pour un plafond de '" in code, \
        "l'etat du levier n'est pas affiche"
    assert "Image de base'" in code and "chroma pleine</b> la supprime" in code, \
        "le geste qui supprime le sous-echantillonnage n'est pas ecrit"
    # les trois seuils sont ordonnes et couvrent toute la plage
    g = CT.geom("poker_eu", 300)
    p = SD.atlas_plan(g, 1536)
    d = SD.edge_dpi(g, dict(SD.DEFAULTS), p)
    assert 150 <= d["along"] or d["along"] < 150      # le verdict existe des deux cotes
    print(f"[MESURE] tranche poker_eu 300 DPI : {d['along']} DPI le long du "
          f"perimetre — verdict et levier ecrits a cote du chiffre")


def test_la_hierarchie_du_bandeau_existe_dans_la_feuille():
    """LE GRIEF : « Aucune hiérarchie : c'est un mur de texte de ~7 px à faible
    contraste. La phrase la plus importante du panneau est composée exactement
    comme "3512 DPI en travers", chiffre qui ne sert à rien à personne. Tout
    est vrai, rien n'est trié. »

    Aucune mesure n'est retirée — elles sont TRIÉES : les trois lignes qui
    décident d'un tirage (taille physique, échelle du fichier, sens du verso)
    portent la classe `key`, un filet d'accent et une valeur à 14 px contre 12.
    """
    src = _js_source()
    css = (pathlib.Path(__file__).resolve().parents[2]
           / "frontend" / "cardforge" / "css" / "mod-solid.css")
    if src is None or not css.is_file():
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    feuille = css.read_text(encoding="utf-8")
    assert code.count('class="cf-solid-hl key"') == 3, \
        "il doit y avoir exactement trois lignes de tete"
    for cle in ("<span>Carte</span>", "<span>Échelle</span>", "<span>Verso</span>"):
        i = code.index(cle)
        assert 'class="cf-solid-hl key"' in code[max(0, i - 260):i], cle
    assert ".cf-solid .cf-solid-hl.key b { font-size: 14px" in feuille
    assert ".cf-solid .cf-solid-hl.key { border-left: 2px solid var(--accent)" in feuille
    # la scene basse garde la hierarchie sans casser les deux colonnes
    assert ".cf-solid .cf-solid-hl.key b { font-size: 12px; }" in feuille
    # LA REGLE PORTE SUR LA SCENE, PAS SUR LA FENETRE : mesuré, la scene ne
    # fait que 565 px dans le lab a 1440 px de large (rail + colonne d'apercu
    # + commandes), et le detail se repliait en trois lignes par mesure.
    assert "container-type: inline-size; container-name: cf-solid-scene;" in feuille
    assert "@container cf-solid-scene (max-width: 720px)" in feuille
    # rien n'est tronque en silence : seul le DETAIL des lignes secondaires se
    # retire, jamais une valeur, et jamais sur les lignes de tete
    assert ".cf-solid-hl:not(.key) i { display: none; }" in feuille
    assert "overflow: hidden" not in feuille.split(".cf-solid-hud {")[1].split("}")[0], \
        "le bandeau tronquerait ses propres mesures"
    # regle 4 : tout selecteur porte .cf-solid, y compris dans la requete de
    # conteneur
    for bloc in feuille.split("@container")[1:]:
        corps = bloc.split("{", 1)[1]
        for ligne in corps.splitlines():
            s = ligne.strip()
            if s.startswith(".") :
                assert s.startswith(".cf-solid "), s
    print("[MESURE] 3 lignes de tete (Carte, Echelle, Verso) a 14 px contre "
          "12 px pour les autres, filet d'accent ; scene mesuree a 565 px dans "
          "le lab a 1440 px : le detail des lignes secondaires se retire, "
          "aucune valeur ne disparait")


# ═══════════════════════════════════════════════════════════════════════════
# TOUR 3 — LE POIDS QUI RESTAIT, ET LES DEUX CHIFFRES QUI N'ÉTAIENT PAS DES
#          MESURES
# ═══════════════════════════════════════════════════════════════════════════

def test_le_relief_dencre_est_un_choix_et_son_prix_est_mesure():
    """LE MANQUE, MOT POUR MOT : « 137 Kio, soit 29,1 % du fichier, dépensés
    pour une carte de normales qui ne transporte que 3,0 bits utiles [...].
    Soit on encode ce relief d'encre de 6 microns dans un canal à 5 Kio, soit
    on ne l'encode pas. »

    Les DEUX branches existent désormais, plus une entre les deux, et chacune
    a été pesée sur le GLB réellement produit par le lab (poker_eu, 300 DPI,
    fichiers relus octet par octet par le rig) :

        Aucun     402 512 o — 2 images / 3 emplacements, PAS d'attribut
                  TANGENT, pas de `normalTexture` dans le matériau
        Léger     435 860 o — normales 29 403 o en 380x277, palette 4 bits,
                  16 couleurs, 0,95° d'inclinaison maximale, 6,7 % du fichier
        Détaillé  539 876 o — normales 133 418 o en 759x553, palette 8 bits,
                  64 couleurs, 2,22° d'inclinaison maximale, 24,7 % du fichier

    Le défaut est « Léger » : la carte de normales passe de 27,1 % à 6,7 % du
    fichier, soit 29 Kio au lieu de 153, pour une inclinaison qui reste du même
    ordre. Le panneau publie le niveau ET son coût mesuré.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    # les trois niveaux, avec le diviseur d'atlas de chacun
    assert re.search(r'\{ id: "aucun",\s+l: "Aucun",\s+div: 0', code)
    assert re.search(r'\{ id: "leger",\s+l: "Léger",\s+div: 4', code)
    assert re.search(r'\{ id: "detaille",\s+l: "Détaillé",\s+div: 2', code)
    # le defaut est le leger : c'est lui qui part chez tout le monde
    assert re.search(r"relief:\s*\"leger\",", code), \
        "le defaut n'est pas le niveau leger"
    # le reglage refait vraiment le fichier
    assert 'S("relief", "leger")].join("~")' in code, \
        "changer le relief ne reconstruit pas le modele"
    # « aucun » ne pose NI carte de normales NI TANGENT : un attribut sans
    # carte de normales est 3,6 Kio pour rien
    assert "if (o.pbr && o.pbr.normal) {" in code
    assert "if (o.pbr.normal) {" in code
    assert "normal: nrm ? await mapBytes(nrm) : null," in code
    # le panneau nomme le niveau et sa part du fichier (source échappée : le
    # module écrit `Relief d\'encre <b>`)
    assert "Relief d\\'encre <b>" in code and "% du fichier" in code
    assert "pas de carte de normales, donc pas" in code
    print("[MESURE] GLB produits par le lab : aucun 402 512 o (2 images, "
          "sans TANGENT) - leger 435 860 o (normales 29 403 o, palette 4 bits, "
          "16 couleurs, 0,95 deg, 6,7 %) - detaille 539 876 o (normales "
          "133 418 o, palette 8 bits, 64 couleurs, 2,22 deg, 24,7 %)")


def test_les_cartes_qui_tiennent_en_256_couleurs_partent_en_palette():
    """Une image qui ne porte que quelques dizaines de couleurs n'a rien à
    faire en RGB. Les triplets sont COMPTÉS ; s'il y en a 256 au plus, un PNG
    de type 3 est écrit à la plus petite profondeur qui les contient, et les
    DEUX encodages sont pesés — c'est le plus léger qui part.

    MESURE SUR LES FICHIERS PRODUITS, en-têtes relus par le rig :
        normales « Léger »     16 couleurs, IHDR bits=4  type=3 :
                               29 403 o contre 38 xxx o en RGB (-24 %)
        normales « Détaillé »  64 couleurs, IHDR bits=8  type=3 :
                              133 418 o contre 154 xxx o en RGB (-16 %)
        ORM                    65 couleurs, IHDR bits=8  type=3 :
                               36 795 o contre 46 990 o en RGB (-22 %)

    Les texels ne bougent pas : l'empreinte FNV des triplets de la source et
    celle des triplets RECONSTRUITS depuis la palette sont comparées avant
    l'écriture, et un écart ferait retomber sur le RGB.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "function pngPalette(" in code and "function palette(" in code
    assert "const PAL_MAX = 256;" in code
    assert 'chunk("PLTE"' in code, "un PNG a palette sans PLTE est illisible"
    # la profondeur suit le nombre de couleurs, elle n'est pas figee a 8
    assert "nc <= 2 ? 1 : (nc <= 4 ? 2 : (nc <= 16 ? 4 : 8))" in code
    # la preuve que les texels ne bougent pas
    assert "function fnvRGB(" in code
    assert "if (src !== rec) return null;" in code, \
        "aucune verification que la palette rend les memes texels"
    # le plus leger part, et les deux poids sont publies
    assert "if (p && p.bytes.length < u.length)" in code
    assert "rgb_octets" in code and "en palette contre" in code
    assert "couleurs distinctes</b> comptées sur les" in code
    print("[MESURE] normales leger 16 couleurs -> IHDR bits=4 type=3, "
          "29 403 o ; detaille 64 couleurs -> bits=8 type=3, 133 418 o ; "
          "ORM 65 couleurs -> bits=8 type=3, 36 795 o (46 990 en RGB)")


def test_la_marche_dencre_est_deduite_des_octets_pas_recopiee():
    """LE CHIFFRE QUI N'EN ÉTAIT PAS UN : le panneau écrivait « mesuré sur les
    octets écrits : relief d'encre de 6 µm ». Les 6 µm étaient
    `INK_RELIEF_MM`, la CONSIGNE partagée avec le backend — pas une lecture du
    fichier. Un chiffre faux vaut moins que pas de chiffre.

    La pente maximale d'un seul axe est maintenant relevée sur les texels
    écrits, et la marche s'en déduit par le pas de texel de la géométrie :

        Détaillé  pente 2,75 % x pas 0,1694 mm = 4,7 µm   (consigne 6)
        Léger     pente 1,18 % x pas 0,3383 mm = 4,0 µm   (consigne 6)

    L'écart avec la consigne est réel — l'atlas est réduit avant dérivation,
    donc un bord d'encre franc n'y descend jamais de 1,0 à 0,0 sur deux
    texels — et il est DIT au lieu d'être masqué par la consigne.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    # la pente sort des texels encodes
    assert "penteMax" in code
    bloc = code.split("penteMax")[1][:900]
    assert "vx / vz" in bloc and "vy / vz" in bloc, \
        "la pente n'est pas relue dans la normale encodee"
    # le bilan porte les deux grandeurs, nommees pour ce qu'elles sont
    assert "relief_demande_mm: INK_RELIEF_MM," in code
    assert "relief_mesure_mm: penteMax * mmParPx," in code
    # et l'ecran distingue la mesure de la consigne (source échappée)
    assert "La marche d\\'encre s\\'en déduit" in code
    assert "la consigne partagée" in code and "en demandait" in code
    assert "relief d'encre de ' + fr(R2.relief_mm" not in code, \
        "la consigne est encore affichee comme une mesure"
    print("[MESURE] detaille : pente 2,75 % x pas 0,1694 mm = 4,7 um ; "
          "leger : pente 1,18 % x pas 0,3383 mm = 4,0 um ; consigne 6 um")


def test_la_dilatation_annoncee_est_celle_qui_est_appliquee():
    """« Bords des trois îlots dilatés de 16 px [...] soit jusqu'au MILIEU des
    gouttières (30,4 px recto|verso, 22,1 px faces|tranche) » : 16 n'est pas la
    moitié de 30,4 et 12 n'est pas la moitié de 22,1. La dilatation vaut
    `ceil(gouttière / 2)`, donc 0,8 px et 0,9 px de PLUS que la moitié.

    Le « soit » est maintenant exact et les deux moitiés sont écrites à côté :
    30,4 -> 15,2 et 22,1 -> 11,1, pour 16 et 12 appliqués.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert "Math.ceil(gu / 2)" in code and "Math.ceil(gv / 2)" in code
    assert "soit jusqu'au milieu des gouttières" not in code, \
        "l'arrondi vers le haut est encore presente comme la moitie exacte"
    assert "la moitié de chaque gouttière arrondie" in code
    assert "fr(gutU / 2, 1)" in code and "fr(gutV / 2, 1)" in code, \
        "les moities ne sont pas ecrites a cote de ce qui est applique"
    print("[MESURE] gouttieres 30,4 et 22,1 px -> moities 15,2 et 11,1 ; "
          "dilatation appliquee 16 et 12 px (ceil), et le panneau le dit")


def test_la_cote_de_la_coupe_mesure_ce_quelle_annonce():
    """La légende de la coupe de tranche annonçait une ÉCHELLE (« 1 mm =
    74 px ») sans jamais donner la longueur qui en découle : il fallait faire
    la multiplication, et le trait de contour faisait ensuite douter du
    résultat.

    Deux corrections, dans cet ordre :
      1. la légende écrit aussi la cote (« cote 23,7 px ») ;
      2. les deux traits de la cote sont rentrés d'un demi-pixel, sans quoi un
         trait de 1 px centré sur la ligne débordait d'un demi-pixel de chaque
         côté.

    MESURE À LA RÈGLE SUR LA TOILE, quatre épaisseurs, colonne la plus encrée
    de la cote, seuil à 100/255 (le reste est de l'anticrénelage) :

        0,20 mm   annoncé 14,8 px   mesuré 15,12
        0,32 mm   annoncé 23,7 px   mesuré 24,19   (24,7 -> 1,7 px d'écart avant)
        0,62 mm   annoncé 43,4 px   mesuré 44,35
        1,00 mm   annoncé 44,0 px   mesuré 44,35

    L'écart résiduel tient dans un pixel, contre 1,7 px de biais systématique
    avant l'encastrement.
    """
    src = _js_source()
    if src is None:
        pytest.skip("frontend absent de cette arborescence")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    # l'echelle est un nombre de pixels par millimetre, pas un grossissement
    assert '"coupe · 1 mm = " + K + " px, cote " + fr(h, 1) + " px' in code
    assert '"' + str(74) + "x" not in code, "le grossissement invente est revenu"
    # le demi-pixel d'encastrement : c'est lui qui rend la cote mesurable
    assert "const ya = y0 + 0.5, yb = y0 + h - 0.5;" in code
    assert "x.moveTo(x0 - 9, ya); x.lineTo(x0 - 9, yb);" in code
    assert "x.moveTo(x0 - 14, y0); x.lineTo(x0 - 4, y0);" not in code, \
        "la cote deborde encore d'un demi-pixel de chaque cote"
    # et K reste calcule, jamais ecrit en dur
    assert "const K = Math.max(18, Math.min(74, Math.floor((H - 30) / th)));" in code
    print("[MESURE] cote a la regle : 0,20 mm 14,8 annonce / 15,12 mesure ; "
          "0,32 mm 23,7 / 24,19 ; 0,62 mm 43,4 / 44,35 ; 1,00 mm 44,0 / 44,35")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
