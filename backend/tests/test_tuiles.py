# -*- coding: utf-8 -*-
"""Tuiles — lot 1 (plan 2026-09-03-plan-tuiles, tâche t113 : T1-T2).
T1 : la table du blob (47 / 16), la numérotation horaire depuis le nord (= wangid de Tiled), les masques dessinés
par PIL, et LE raccord des voisines LÉGALES (1156 paires E, 1156 paires S) — exactement 0.
T2 : un jeu depuis deux matières (47 + la VIDE), l'atlas 8 x 6, son dossier (motif PUIS confinement, liste blanche
de fichiers servis), la route /api/tiles qui rend la mesure du raccord du jeu entier, et la provenance : l'atlas
est COPIÉ dans la Bibliothèque (tile_<id>_atlas.png) et indexé source « tuiles » — l'index ne pointe jamais un
fichier absent.
Run: python tests/test_tuiles.py   (depuis backend/)"""
import asyncio
import io
import json
import math
import os
import pathlib
import random
import sys
import tempfile
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="dztuiles_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = ""
os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                # noqa: E402
logger.remove()
from PIL import Image, ImageChops, ImageStat            # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"


def _bruit(s=64, seed=1):
    """Bruit en MIROIR 2x2 : raccord exactement 0, donc tout raccord non nul
    mesuré plus loin vient des masques, jamais de la matière."""
    rng = random.Random(seed)
    h = s // 2
    q = Image.frombytes("RGB", (h, h),
                        bytes(rng.randrange(256) for _ in range(h * h * 3)))
    out = Image.new("RGB", (s, s))
    out.paste(q, (0, 0))
    out.paste(q.transpose(Image.FLIP_LEFT_RIGHT), (h, 0))
    out.paste(q.transpose(Image.FLIP_TOP_BOTTOM), (0, h))
    out.paste(q.transpose(Image.ROTATE_180), (h, h))
    return out


def _rampe(s=64):
    return Image.frombytes(
        "L", (s, 1), bytes(int(255 * x / (s - 1)) for x in range(s))
    ).resize((s, s)).convert("RGB")


def _uni(s=64, rgb=(120, 120, 120)):
    return Image.new("RGB", (s, s), rgb)


from app.services import tile_ops as TO                  # noqa: E402
from app.services import tile_store as TS                # noqa: E402


# ═════════════════════════════════ T1 ═════════════════════════════════
def test_table_du_blob_vaut_47_et_16():
    """47 masques canoniques, 16 en arêtes seules — le dénombrement du plan."""
    assert len(TO.BLOB47) == 47, len(TO.BLOB47)
    assert len(TO.BLOB16) == 16, len(TO.BLOB16)
    assert TO.BLOB47 == sorted(set(TO.BLOB47))
    assert TO.BLOB47[0] == 0 and TO.BLOB47[-1] == 255
    assert TO.BLOB47 == [0, 1, 4, 5, 7, 16, 17, 20, 21, 23, 28, 29, 31, 64, 65, 68, 69, 71, 80, 81,
                         84, 85, 87, 92, 93, 95, 112, 113, 116, 117, 119, 124, 125, 127, 193, 197,
                         199, 209, 213, 215, 221, 223, 241, 245, 247, 253, 255], TO.BLOB47
    assert TO.BLOB16 == [0, 1, 4, 5, 16, 17, 20, 21,
                         64, 65, 68, 69, 80, 81, 84, 85], TO.BLOB16
    # la numérotation FIXÉE : horaire depuis le nord, ordre du wangid Tiled
    assert TO.ORDRE == ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    assert (TO.N, TO.NE, TO.E, TO.SE, TO.S, TO.SW, TO.W, TO.NW) == \
        (1, 2, 4, 8, 16, 32, 64, 128)


def test_canon_ote_un_coin_sans_ses_deux_aretes():
    """Règle citée de boristhebrave (relue le 06/10/2026) : un coin ne compte que si les deux arêtes adjacentes
    sont posées."""
    assert TO.canon(TO.NE) == 0                      # NE seul : effacé
    assert TO.canon(TO.N | TO.NE) == TO.N            # une seule arête
    assert TO.canon(TO.N | TO.E | TO.NE) == TO.N | TO.E | TO.NE   # gardé
    assert TO.canon(TO.N | TO.E) == TO.N | TO.E      # sans le coin : inchangé
    assert TO.canon(TO.S | TO.W | TO.SW | TO.NE) == TO.S | TO.W | TO.SW   # chaque coin jugé seul
    assert TO.canon(255) == 255
    assert TO.canon(256 + TO.N) == TO.N              # borné à 8 bits
    for m in range(256):
        assert TO.canon(TO.canon(m)) == TO.canon(m), m
    assert {TO.canon(m) for m in range(256)} == set(TO.BLOB47)


def test_index_de_est_une_bijection_sur_la_table():
    for i, m in enumerate(TO.BLOB47):
        assert TO.index_de(m, "blob47") == i, (i, m)
    for i, m in enumerate(TO.BLOB16):
        assert TO.index_de(m, "blob16") == i, (i, m)
    assert TO.index_de(TO.NE, "blob47") == 0          # canonisé vers 0
    assert TO.index_de(TO.N | TO.E | TO.NE, "blob16") == TO.BLOB16.index(TO.N | TO.E)   # coins ignorés en 16
    try:
        TO.cles("blob99")
    except ValueError as e:
        assert "blob99" in str(e)
    else:
        raise AssertionError("un jeu inconnu doit être refusé")


def test_47_masques_deux_a_deux_distincts():
    """Un masque par entrée de table : si deux se confondent, le jeu ment."""
    vus = {TO.masque_blob(m, 64).tobytes() for m in TO.BLOB47}
    assert len(vus) == 47, len(vus)
    plein = TO.masque_blob(255, 64)
    assert plein.getextrema() == (255, 255)           # tout entouré : plein
    isole = TO.masque_blob(0, 64)
    assert isole.getpixel((0, 0)) == 0                # isolée : anneau ouvert
    assert isole.getpixel((32, 32)) == 255            # noyau toujours plein
    assert isole.mode == "L" and isole.size == (64, 64)


def test_anneau_ne_depend_que_des_aretes():
    """L'anneau (b px) : bandes = bit d'arête, coins = OU des deux arêtes.
    C'est CE choix qui rend le raccord des voisines légales exactement 0."""
    cote, b = 64, 8
    for m in TO.BLOB47:
        px = TO.masque_blob(m, cote).load()
        for bit, xs, ys in ((TO.E, [cote - 1], range(b, cote - b)), (TO.W, [0], range(b, cote - b)),
                            (TO.N, range(b, cote - b), [0]), (TO.S, range(b, cote - b), [cote - 1])):
            attendu = 255 if (m & bit) else 0
            for x in xs:
                for y in ys:
                    assert px[x, y] == attendu, (m, bit, x, y)
        for (x, y), a, c in (((cote - 1, 0), TO.N, TO.E), ((cote - 1, cote - 1), TO.S, TO.E),
                             ((0, cote - 1), TO.S, TO.W), ((0, 0), TO.N, TO.W)):
            assert px[x, y] == (255 if (m & a or m & c) else 0), (m, x, y)


def test_raccord_des_paires_legales_est_nul():
    """LA mesure de P1 : chaque tuile contre ses voisines LÉGALES, pas contre elle-même. 1156 paires E et 1156
    paires S, raccord max 0.00 (mesuré)."""
    A, B = _bruit(64, 1), _bruit(64, 2)
    tuiles = {m: Image.composite(A, B, TO.masque_blob(m, 64)) for m in TO.BLOB47}

    def _seam(a, b, sens):
        w, h = a.size
        if sens == "E":
            x, y = a.crop((w - 1, 0, w, h)), b.crop((0, 0, 1, h))
        else:
            x, y = a.crop((0, h - 1, w, h)), b.crop((0, 0, w, 1))
        d = ImageStat.Stat(ImageChops.difference(x, y)).mean
        return sum(d) / len(d) / 255 * 100

    n_e = n_s = 0
    for ma, ta in tuiles.items():
        for mb, tb in tuiles.items():
            if (ma & TO.E) and (mb & TO.W):
                assert _seam(ta, tb, "E") == 0.0, (ma, mb)
                n_e += 1
            if (ma & TO.S) and (mb & TO.N):
                assert _seam(ta, tb, "S") == 0.0, (ma, mb)
                n_s += 1
    assert n_e == 1156, n_e
    assert n_s == 1156, n_s


def test_une_paire_illegale_se_voit():
    """Témoin positif de la mesure : une tuile SANS l'arête E contre une voisine qui l'attend raccorde MAL —
    sinon le 0.00 ci-dessus ne prouverait rien."""
    A, B = _bruit(64, 1), _bruit(64, 2)
    sans_e = Image.composite(A, B, TO.masque_blob(TO.N | TO.S, 64))
    avec_w = Image.composite(A, B, TO.masque_blob(TO.W, 64))
    w, h = sans_e.size
    d = ImageStat.Stat(ImageChops.difference(sans_e.crop((w - 1, 0, w, h)), avec_w.crop((0, 0, 1, h)))).mean
    assert sum(d) / len(d) > 5, d


# ═════════════════════════════════ T2 ═════════════════════════════════
def test_assembler_jeu_rend_47_tuiles_plus_la_vide():
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, jeu="blob47", cote=64, variantes=1)
    assert jeu["jeu"] == "blob47"
    assert jeu["variantes"] == 1
    assert len(jeu["tuiles"]) == 48, len(jeu["tuiles"])   # 47 + la vide
    assert jeu["vide"] == 47
    assert all(t.size == (64, 64) for t in jeu["tuiles"])
    # la 48e est la matière B nue : c'est la case sans terrain
    assert jeu["tuiles"][47].tobytes() == B.resize((64, 64), Image.LANCZOS).tobytes()
    # et la tuile pleine (255) est la matière A nue
    assert jeu["tuiles"][46].tobytes() == A.resize((64, 64), Image.LANCZOS).tobytes()
    j16 = TO.assembler_jeu(A, B, jeu="blob16", cote=32, variantes=1)
    assert len(j16["tuiles"]) == 17, len(j16["tuiles"])
    assert j16["vide"] == 16 and j16["cote"] == 32


def test_atlas_range_les_tuiles_en_colonnes_fixes():
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 64, 1)
    img, colonnes, rangees = TO.atlas(jeu)
    assert colonnes == 8 and rangees == 6                 # 48 = 8 x 6
    assert img.size == (8 * 64, 6 * 64)
    for i in (0, 9, 47):
        x, y = (i % 8) * 64, (i // 8) * 64
        assert img.crop((x, y, x + 64, y + 64)).tobytes() == jeu["tuiles"][i].convert("RGB").tobytes(), i
    j16 = TO.assembler_jeu(A, B, "blob16", 32, 1)
    img16, c16, r16 = TO.atlas(j16)
    assert (c16, r16) == (4, 5) and img16.size == (4 * 32, 5 * 32)   # 17 tuiles : 4 colonnes, 5 rangées


def test_store_refuse_un_tid_hors_motif():
    assert TS.is_valid_tid("tile_0123abcd")
    for mauvais in ("tile_XYZ", "../etc", "tile_0123abc", "", None,
                    "tile_0123abcd/x", "TILE_0123ABCD"):
        assert not TS.is_valid_tid(mauvais), mauvais
    # `tileset_dir` refuse par le MOTIF, pas seulement par le confinement : `tile_XYZ` resterait sous la racine.
    for mauvais in ("../evasion", "tile_XYZ", "tile_0123abc", "TILE_0123ABCD"):
        try:
            TS.tileset_dir(mauvais)
        except ValueError:
            continue
        raise AssertionError(f"tileset_dir a accepte {mauvais!r}")
    for nom in ("../meta.json", "atlas.png/../x", "secret.txt", ""):
        try:
            TS.chemin_fichier("tile_0123abcd", nom)
        except ValueError:
            continue
        raise AssertionError(f"chemin_fichier a accepte {nom!r}")


def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _poser_image(nom, img):
    from app.config import settings
    img.save(settings.images_path / nom, "PNG")
    return nom


def test_route_jeu_ecrit_un_dossier_lisible():
    """Banc-miroir : on relit l'atlas SUR DISQUE avec PIL, pas la réponse."""
    from app.config import settings
    from app.services.storage import init_db, LibraryAsset, async_session_factory
    from sqlalchemy import select

    async def scenario():
        await init_db()
        a = _poser_image("tuile_a.png", _bruit(128, 1))
        b = _poser_image("tuile_b.png", _bruit(128, 2))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": a}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 64, "variantes": 1, "nom": "banc"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert TS.is_valid_tid(d["tid"]), d
            assert d["tuiles"] == 48 and d["colonnes"] == 8 and d["rangees"] == 6
            assert d["raccord"] == 0.0, d["raccord"]
            # le fichier ÉCRIT, relu par PIL
            dossier = TS.tileset_dir(d["tid"])
            with Image.open(dossier / "atlas.png") as im:
                assert im.size == (8 * 64, 6 * 64), im.size
            meta = json.loads((dossier / "meta.json").read_text("utf-8"))
            assert meta["jeu"] == "blob47" and meta["cote"] == 64 and meta["nom"] == "banc"
            assert meta["cles"] == TO.BLOB47 and meta["raccord"] == 0.0
            # la COPIE dans la Bibliothèque existe, est l'atlas, et l'index la range en « tuiles »
            copie = settings.images_path / f"{d['tid']}_atlas.png"
            assert copie.is_file(), copie
            assert copie.read_bytes() == (dossier / "atlas.png").read_bytes()
            async with async_session_factory() as s:
                row = (await s.execute(select(LibraryAsset).where(LibraryAsset.filename == copie.name))).scalar_one_or_none()
            assert row is not None and row.source == "tuiles", (row and row.source)
            # servi par la route de fichier
            r2 = await c.get(f"/api/tiles/{d['tid']}/fichier/atlas.png")
            assert r2.status_code == 200 and r2.content[:8] == b"\x89PNG\r\n\x1a\n"
            r2b = await c.get(f"/api/tiles/{d['tid']}")
            assert r2b.status_code == 200 and r2b.json()["tid"] == d["tid"]
            # et listé
            r3 = await c.get("/api/tiles")
            assert any(x["tid"] == d["tid"] and "atlas.png" in x["fichiers"] for x in r3.json()["tilesets"]), r3.text[:300]
            # blob16 : 17 tuiles, 4 colonnes
            r16 = await c.post("/api/tiles/jeu", json={"matiere_a": {"image": a}, "matiere_b": {"image": b},
                                                       "jeu": "blob16", "cote": 32})
            assert r16.status_code == 200 and r16.json()["tuiles"] == 17 and r16.json()["colonnes"] == 4, r16.text
            # refus nommés
            r4 = await c.post("/api/tiles/jeu", json={"matiere_a": {"image": "absente.png"}, "matiere_b": {"image": b}})
            assert r4.status_code == 400 and "absente.png" in r4.text
            r4b = await c.post("/api/tiles/jeu", json={"matiere_a": {"image": "../t.db"}, "matiere_b": {"image": b}})
            assert r4b.status_code == 400, r4b.text
            for corps, mot in (({"jeu": "blob99"}, "blob99"), ({"cote": 8}, "cote"), ({"variantes": 9}, "variantes"),
                               ({"cote": "x"}, "entiers")):
                rr = await c.post("/api/tiles/jeu", json=dict({"matiere_a": {"image": a}, "matiere_b": {"image": b}}, **corps))
                assert rr.status_code == 400 and mot in rr.text, (corps, rr.status_code, rr.text)
            r5 = await c.get("/api/tiles/tile_zzzzzzzz/fichier/atlas.png")
            assert r5.status_code == 404, r5.text
            r5b = await c.get("/api/tiles/tile_0000beef")
            assert r5b.status_code == 404, r5b.text
            # un nom hors liste blanche est refusé MÊME si le fichier existe
            (dossier / "secret.txt").write_text("x", encoding="utf-8")
            r6 = await c.get(f"/api/tiles/{d['tid']}/fichier/secret.txt")
            assert r6.status_code == 404, r6.text
            assert "inconnu" in r6.text.lower(), r6.text

    asyncio.run(scenario())


def test_raccord_du_jeu_exact_et_rapide():
    """MESURÉ le 06/10/2026 : la boucle naïve (une découpe + une différence par paire légale) prenait 60,2 s pour
    un jeu de 512 px à 5 variantes (236 tuiles, 57 800 paires) — trop pour une route. Les bords d'une tuile ne
    dépendent que de ses arêtes et les variantes ne touchent que le cœur : les bandes de bord se répètent, et
    chaque COUPLE de bandes distinct n'a besoin d'être mesuré qu'une fois. Même chiffre au centième que la boucle
    naïve (vérifié ici sur des matières NON raccordables, où le pire raccord n'est pas nul), sous 5 s à 512 px x5."""
    import time
    from app.services import tile_metrics as TM
    rng = random.Random(7)

    def _brut(s):
        return Image.frombytes("RGB", (s, s), bytes(rng.randrange(256) for _ in range(s * s * 3)))
    for jeu_nom, cote, v in (("blob47", 32, 3), ("blob16", 48, 2)):
        jeu = TO.assembler_jeu(_brut(cote), _brut(cote), jeu_nom, cote, v)
        naif = 0.0
        for sens in ("E", "S"):
            for ia, ib in TM.paires_legales(jeu, sens):
                naif = max(naif, TM.seam_pair(jeu["tuiles"][ia], jeu["tuiles"][ib], sens))
        assert TM.raccord_jeu(jeu) == round(naif, 2) and naif > 5, (jeu_nom, TM.raccord_jeu(jeu), naif)
    gros = TO.assembler_jeu(_brut(512), _brut(512), "blob47", 512, 5)
    t0 = time.perf_counter()
    TM.raccord_jeu(gros)
    dt = time.perf_counter() - t0
    assert dt < 5.0, f"raccord de 236 tuiles de 512 px en {dt:.1f} s (budget 5 s)"


def test_variantes_ne_touchent_que_le_coeur():
    """Les variantes (k > 0) diffèrent de la tuile de base, mais seulement au CŒUR : le raccord des paires légales
    reste exactement 0 sur des matières miroir (sinon une variante casserait le jeu)."""
    from app.services import tile_metrics as TM
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 64, 3, graine=5)
    assert len(jeu["tuiles"]) == 47 * 3 + 1 and jeu["vide"] == 141
    base, var = jeu["tuiles"][0], jeu["tuiles"][1]
    assert base.tobytes() != var.tobytes(), "la variante est identique à la base"
    b = 64 // 8
    for x in range(64):
        for y in (0, b - 1, 63):
            assert base.getpixel((x, y)) == var.getpixel((x, y)), (x, y)
    assert TM.raccord_jeu(jeu) == 0.0


def test_raccord_jeu_sur_un_jeu_dont_les_bords_different():
    """Les masques du plan rendent tous les bords légaux IDENTIQUES : ils ne peuvent pas éprouver la mesure
    elle-même. Ici, un jeu SYNTHÉTIQUE dont chaque tuile a ses bords à elle — raccordable de gauche à droite (E = 0),
    pas de haut en bas — : la mesure doit voir le sens S, et la mise en cache doit porter sur les OCTETS des bandes,
    pas sur les indices."""
    from app.services import tile_metrics as TM
    rng = random.Random(11)
    tuiles = []
    for _ in range(len(TO.BLOB16)):
        im = Image.frombytes("RGB", (16, 16), bytes(rng.randrange(256) for _ in range(16 * 16 * 3)))
        px = im.load()
        for y in range(16):                       # colonne droite = colonne gauche, et la même pour TOUTES
            px[15, y] = px[0, y] = (y * 9, 40, 200)
        tuiles.append(im)
    jeu = {"jeu": "blob16", "cles": list(TO.BLOB16), "variantes": 1, "cote": 16, "tuiles": tuiles + [tuiles[0]]}
    naif_e = max(TM.seam_pair(tuiles[a], tuiles[b], "E") for a, b in TM.paires_legales(jeu, "E"))
    naif_s = max(TM.seam_pair(tuiles[a], tuiles[b], "S") for a, b in TM.paires_legales(jeu, "S"))
    assert naif_e == 0.0 and naif_s > 10, (naif_e, naif_s)
    assert TM.raccord_jeu(jeu) == naif_s, (TM.raccord_jeu(jeu), naif_s)


def test_route_rend_le_raccord_mesure_et_refuse_un_chemin():
    """Sur des matières NON raccordables, la route rend le raccord MESURÉ (non nul, égal à raccord_jeu) ; et une
    image hors de la Bibliothèque, même réelle, est refusée par son chemin."""
    from app.config import settings
    from app.services import tile_metrics as TM
    from app.services.storage import init_db
    rng = random.Random(3)
    brut_a = Image.frombytes("RGB", (64, 64), bytes(rng.randrange(256) for _ in range(64 * 64 * 3)))
    brut_b = Image.frombytes("RGB", (64, 64), bytes(rng.randrange(256) for _ in range(64 * 64 * 3)))
    dehors = settings.images_path.parent / "dehors.png"
    brut_a.save(dehors)

    async def scenario():
        await init_db()
        a = _poser_image("brut_a.png", brut_a)
        b = _poser_image("brut_b.png", brut_b)
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={"matiere_a": {"image": a}, "matiere_b": {"image": b},
                                                     "jeu": "blob16", "cote": 32})
            assert r.status_code == 200, r.text
            attendu = TM.raccord_jeu(TO.assembler_jeu(brut_a, brut_b, "blob16", 32, 1))
            assert r.json()["raccord"] == attendu and attendu > 1, (r.json()["raccord"], attendu)
            for chemin in ("../dehors.png", "..\\dehors.png"):
                rr = await c.post("/api/tiles/jeu", json={"matiere_a": {"image": chemin}, "matiere_b": {"image": b}})
                assert rr.status_code == 400 and "introuvable" in rr.text, (chemin, rr.status_code, rr.text)

    asyncio.run(scenario())


def test_provenance_des_tuiles_est_declaree():
    from app.services import library_index as LI
    assert LI.SOURCES.get("tuiles") == "Tile Lab"
    assert LI.heuristique("tile_0123abcd_atlas.png") == "tuiles"
    assert LI.licence_defaut("tile_0123abcd_atlas.png", "tuiles") == LI.LICENCE_PROPRE


# ═════════════════════════════════ T6 (t115) ═════════════════════════════════
def test_les_variantes_ne_touchent_pas_le_bord():
    """Le masque de cœur est 0 DUR sur l'anneau : la variante ne peut pas déplacer un pixel de bord, donc le
    raccord reste 0.00 (mesuré sur les 10404 paires E légales d'un jeu à 3 variantes)."""
    coeur = TO.masque_coeur(64)
    b = 8
    bords = (coeur.crop((0, 0, 64, b)), coeur.crop((0, 64 - b, 64, 64)),
             coeur.crop((0, 0, b, 64)), coeur.crop((64 - b, 0, 64, 64)))
    assert max(max(im.getextrema()) for im in bords) == 0
    assert coeur.getpixel((32, 32)) == 255

    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 64, variantes=3, graine=5)
    assert len(jeu["tuiles"]) == 47 * 3 + 1
    # les 3 variantes d'une même tuile diffèrent VRAIMENT...
    i = jeu["cles"].index(255) * 3
    assert len({jeu["tuiles"][i + k].tobytes() for k in range(3)}) == 3
    # ... et ont exactement le même bord
    for k in (1, 2):
        assert jeu["tuiles"][i + k].crop((63, 0, 64, 64)).tobytes() == \
            jeu["tuiles"][i].crop((63, 0, 64, 64)).tobytes()


def test_raccord_du_jeu_a_variantes_reste_nul():
    from app.services import tile_metrics as TM
    jeu = TO.assembler_jeu(_bruit(64, 1), _bruit(64, 2), "blob47", 64, 3, 5)
    n = sum(1 for _ in TM.paires_legales(jeu, "E"))
    assert n == 10404, n                     # 1156 voisinages x 3 x 3
    assert TM.raccord_jeu(jeu) == 0.0


def test_masque_voisins_lit_les_huit_directions():
    g = [[0] * 3 for _ in range(3)]
    g[1][1] = 1
    assert TO.masque_voisins(g, 1, 1, boucle=False) == 0
    g[0][1] = 1                              # la case AU-DESSUS
    assert TO.masque_voisins(g, 1, 1, boucle=False) == TO.N
    g[1][2] = 1                              # la case À DROITE
    assert TO.masque_voisins(g, 1, 1, boucle=False) == TO.N | TO.E
    g[0][2] = 1                              # la diagonale NE, désormais légale
    assert TO.masque_voisins(g, 1, 1, boucle=False) == TO.N | TO.E | TO.NE
    # une diagonale SANS ses deux arêtes est effacée : le voisinage rendu est CANONIQUE
    g2 = [[0, 0, 1], [0, 1, 0], [0, 0, 0]]
    assert TO.masque_voisins(g2, 1, 1, boucle=False) == 0
    # hors carte = vide quand boucle=False, et la carte boucle sinon
    plein = [[1] * 3 for _ in range(3)]
    assert TO.masque_voisins(plein, 0, 0, boucle=False) == \
        TO.canon(TO.E | TO.S | TO.SE)
    assert TO.masque_voisins(plein, 0, 0, boucle=True) == 255
    # une carte NON carrée (une rangée qui boucle sur elle-même) : x lit la largeur, y la hauteur — un échange des
    # deux ramènerait E sur la case elle-même et poserait le bit E
    large = [[1, 0, 0, 0, 1]]
    assert TO.masque_voisins(large, 0, 0, boucle=True) == TO.N | TO.S | TO.W | TO.NW | TO.SW


def test_composer_carte_pose_les_bonnes_tuiles():
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 32, variantes=2, graine=3)
    g = TO.carte_aleatoire(8, densite=0.55, graine=1)
    assert len(g) == 8 and all(len(l) == 8 for l in g)
    assert set(v for l in g for v in l) == {0, 1}
    # la même graine rend la même carte : la recette est rejouable ; une autre graine, une autre carte
    assert TO.carte_aleatoire(8, 0.55, 1) == g
    assert TO.carte_aleatoire(8, 0.55, 2) != g
    assert TO.carte_aleatoire(8, 0.0, 1) == [[0] * 8 for _ in range(8)]
    assert TO.carte_aleatoire(8, 1.0, 1) == [[1] * 8 for _ in range(8)]

    img, plan = TO.composer_carte(g, jeu, graine=1, boucle=True)
    assert img.size == (8 * 32, 8 * 32)
    assert len(plan) == 8 and len(plan[0]) == 8
    variantes_vues = set()
    for y in range(8):
        for x in range(8):
            t = plan[y][x]
            if not g[y][x]:
                assert t == jeu["vide"], (x, y)
            else:
                m = TO.masque_voisins(g, x, y, boucle=True)
                base = jeu["cles"].index(m) * jeu["variantes"]
                assert base <= t < base + jeu["variantes"], (x, y, m, t)
                variantes_vues.add(t - base)
            # le pixel posé est bien celui de la tuile du plan
            assert img.crop((x * 32, y * 32, x * 32 + 32, y * 32 + 32)).tobytes() == \
                jeu["tuiles"][t].convert("RGB").tobytes(), (x, y)
    assert variantes_vues == {0, 1}, "les variantes sont tirées, pas seulement la première"


def test_composer_carte_blob16_lit_les_aretes_seules():
    """Un jeu d'ARÊTES n'a pas de clé pour un voisinage à coins : la carte doit chercher le voisinage réduit aux
    quatre arêtes, sinon le premier coin posé lève une KeyError."""
    jeu = TO.assembler_jeu(_bruit(64, 1), _bruit(64, 2), "blob16", 16, 1, 1)
    plein = [[1] * 4 for _ in range(4)]
    _img, plan = TO.composer_carte(plein, jeu, graine=1, boucle=True)
    assert {t for l in plan for t in l} == {jeu["cles"].index(TO.N | TO.E | TO.S | TO.W)}


def test_route_apercu_ecrit_le_png_et_le_plan():
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("ap_a.png", _bruit(128, 4))
        b = _poser_image("ap_b.png", _bruit(128, 5))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": a}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 32, "variantes": 3, "nom": "ap"})
            tid = r.json()["tid"]
            r = await c.post(f"/api/tiles/{tid}/apercu",
                             json={"cases": 8, "densite": 0.55, "graine": 7})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["cases"] == 8 and d["graine"] == 7
            assert len(d["plan"]) == 8 and len(d["plan"][0]) == 8
            assert d["url"] == f"/api/tiles/{tid}/fichier/apercu.png"
            # le PNG ÉCRIT, relu par PIL, et identique à la composition refaite hors de la route
            with Image.open(TS.tileset_dir(tid) / "apercu.png") as im:
                assert im.size == (256, 256), im.size
                jeu = TO.assembler_jeu(_bruit(128, 4), _bruit(128, 5), "blob47", 32, 3, 1)
                attendu, plan = TO.composer_carte(TO.carte_aleatoire(8, 0.55, 7), jeu, graine=7)
                assert plan == d["plan"] and im.convert("RGB").tobytes() == attendu.tobytes()
            # la même graine redonne le même plan
            r2 = await c.post(f"/api/tiles/{tid}/apercu",
                              json={"cases": 8, "densite": 0.55, "graine": 7})
            assert r2.json()["plan"] == d["plan"]
            # densité 0 est une valeur, pas un oubli : carte toute vide
            r0 = await c.post(f"/api/tiles/{tid}/apercu", json={"cases": 4, "densite": 0})
            assert r0.status_code == 200 and r0.json()["densite"] == 0.0, r0.text
            assert {t for l in r0.json()["plan"] for t in l} == {47 * 3}
            for corps, mot in (({"cases": 999}, "cases"), ({"cases": 3}, "cases"),
                               ({"densite": 1.5}, "densite"), ({"graine": "x"}, "entiers")):
                rr = await c.post(f"/api/tiles/{tid}/apercu", json=corps)
                assert rr.status_code == 400 and mot in rr.text, (corps, rr.status_code, rr.text)
            r4 = await c.post("/api/tiles/tile_00000000/apercu", json={})
            assert r4.status_code == 404, r4.text

    asyncio.run(scenario())


def test_apercu_borne_la_taille_en_pixels():
    """16 cases de 512 px feraient une image de 8192 px de côté (≈ 200 Mo en RGB) : la route borne le côté de
    l'aperçu en PIXELS, pas seulement en cases, et le dit."""
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("big_a.png", _bruit(128, 4))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={"matiere_a": {"image": a}, "matiere_b": {"image": a},
                                                     "jeu": "blob16", "cote": 512})
            assert r.status_code == 200, r.text
            tid = r.json()["tid"]
            rr = await c.post(f"/api/tiles/{tid}/apercu", json={"cases": 16})
            assert rr.status_code == 400 and "4096" in rr.text, rr.text
            ok = await c.post(f"/api/tiles/{tid}/apercu", json={"cases": 8})
            assert ok.status_code == 200, ok.text

    asyncio.run(scenario())


def _main():
    rouges = 0
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", nom)
            except Exception:
                rouges += 1
                print("FAIL", nom)
                traceback.print_exc()
    print(f"{'ROUGE' if rouges else 'OK'} — {rouges} echec(s)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    _main()
