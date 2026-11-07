# -*- coding: utf-8 -*-
"""Card Forge — t421 : créer un deck « carte pleine » depuis des images.

`POST /api/cards/decks/depuis-images` fabrique un deck NEUF, sans cadre ni
texte, dont chaque carte est une image de la Bibliothèque. Les images ne sont
JAMAIS touchées (empreintes), rien n'est dépensé, et rien n'est créé si une
seule vérification échoue.

Run : <embedded python> backend/tests/test_cards_depuis_images.py
"""
import asyncio
import hashlib
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["DEEPOTUS_DATA_DIR"] = str(pathlib.Path(_tmp, "data"))
for d in ("images", "outputs", "data"):
    pathlib.Path(_tmp, d).mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402

from app.services.cards import core, hexa                       # noqa: E402
from app.services.cards import contract as CT                   # noqa: E402

IMAGES = pathlib.Path(_tmp, "images")
NOMS = ["le_dragon_rouge.png", "Éléphant_d'été.png".replace("'", ""),
        "troisième carte.jpg"]


def _api(method: str, path: str, **kw):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _empreintes() -> dict:
    return {p.name: hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(IMAGES.iterdir()) if p.is_file()}


@pytest.fixture(autouse=True)
def _images():
    for i, n in enumerate(NOMS):
        (IMAGES / n).write_bytes(b"\x89PNG-banc-%d" % i)
    (IMAGES / "dos_commun.png").write_bytes(b"\x89PNG-dos")
    yield


def _nb_decks() -> int:
    return len(core.list_deck_summaries())


def _post(**corps):
    base = {"name": "Mes images", "format": {"fmt": "poker_us"},
            "images": list(NOMS)}
    base.update(corps)
    return _api("POST", "/api/cards/decks/depuis-images", json=base)


def test_le_deck_est_une_carte_pleine_sans_cadre():
    avant = _empreintes()
    r = _post()
    assert r.status_code == 200, r.text
    d = r.json()["deck"]
    assert d["name"] == "Mes images"
    assert d["frame"]["family"] == "none"
    assert d["frame"]["gem"] is False and d["frame"]["banner"] is False
    assert d["frame"]["corner"] == "none"
    assert d["type"]["slots"] == [] and d["type"]["seeded"] is True
    assert d["face"]["seeded"] is True and d["face"]["fit"] == "cover"
    assert d["data"]["columns"] == ["nom", "art", "dos"]
    assert d["data"]["map"] == {"art": "art", "dos": "back"}
    assert [l[1] for l in d["data"]["rows"]] == NOMS
    assert [l[0] for l in d["data"]["rows"]] == [
        "le dragon rouge", "Éléphant dété", "troisième carte"]
    assert all(l[2] == "" for l in d["data"]["rows"])
    assert _empreintes() == avant


def test_verso_commun_recopie_sur_chaque_ligne():
    d = _post(verso_commun="dos_commun.png").json()["deck"]
    assert [l[2] for l in d["data"]["rows"]] == ["dos_commun.png"] * 3


def test_versos_un_par_image_et_exclusion_avec_verso_commun():
    r = _post(versos=["dos_commun.png", None, ""])
    assert r.status_code == 200, r.text
    assert [l[2] for l in r.json()["deck"]["data"]["rows"]] == \
        ["dos_commun.png", "", ""]
    n = _nb_decks()
    assert _post(versos=["dos_commun.png"]).status_code == 400
    assert _post(versos=[None] * 3,
                 verso_commun="dos_commun.png").status_code == 400
    assert _nb_decks() == n


def test_fond_perdu():
    sans = _post(fond_perdu=False,
                 format={"fmt": "poker_us", "safe_mm": 2.0}).json()["deck"]
    assert sans["format"]["bleed_mm"] == 0 and sans["format"]["safe_mm"] == 2.0
    avec = _post().json()["deck"]
    assert avec["format"]["bleed_mm"] == CT.native_bleed_mm("poker_us")
    assert _post(fond_perdu="non").status_code == 400


def test_rouvert_par_le_build_les_cartes_ont_art_et_dos():
    d = _post(verso_commun="dos_commun.png").json()["deck"]
    r = _api("POST", f"/api/cards/{d['id']}/data/build", json=d["data"])
    assert r.status_code == 200, r.text
    c0 = r.json()["cards"][0]
    assert c0["art"] == NOMS[0] and c0["back"] == "dos_commun.png"


def test_hexagone_sans_fond_perdu_les_six_milieux_sont_couverts():
    d = _post(format={"fmt": "hex_p50"}, fond_perdu=False).json()["deck"]
    f = d["format"]
    assert f["fmt"] == "hex_p50" and f["bleed_mm"] == 0 and f["corner_mm"] == 0
    g = core.geom_of(d)
    k = CT.MM_PER_INCH / g.dpi
    w, h = g.canvas_px[0] * k, g.canvas_px[1] * k
    ms = hexa.milieux_cotes_mm(g)
    assert len(ms) == 6
    tol = k
    for x, y in ms:
        assert -tol <= x <= w + tol and -tol <= y <= h + tol, (x, y, w, h)


def test_refus_ne_creent_aucun_deck():
    n = _nb_decks()
    avant = _empreintes()
    r = _post(images=NOMS + ["fantome.png"])
    assert r.status_code == 404 and "fantome.png" in r.json()["detail"]
    r = _post(verso_commun="absent_dos.png")
    assert r.status_code == 404 and "absent_dos.png" in r.json()["detail"]
    for mauvais in ("../x.png", "a/b.png", "a\b.png", "a\nb.png", "", 3):
        assert _post(images=[NOMS[0], mauvais]).status_code == 400, mauvais
    assert _post(images=[]).status_code == 400
    assert _post(images="x.png").status_code == 400
    assert _post(images=[NOMS[0]] * 501).status_code == 400
    assert _post(format={"fmt": "inconnu"}).status_code == 400
    assert _post(format=None).status_code == 400
    assert _nb_decks() == n
    assert _empreintes() == avant


def test_cinq_cents_images_passent():
    r = _post(images=[NOMS[0]] * 500)
    assert r.status_code == 200 and len(r.json()["deck"]["data"]["rows"]) == 500


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
