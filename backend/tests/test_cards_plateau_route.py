# -*- coding: utf-8 -*-
"""Card Forge — plateau hexagonal, lot 1, tâche 3 : POST /api/cards/decks/plateau.

Une image de la Bibliothèque est découpée en tuiles hexagonales qui deviennent
un jeu « plateau ». L'image source n'est jamais modifiée, un échec à mi-chemin
ne laisse ni tuile ni jeu, un refus ne crée rien. Aucune dépense.

Run : <embedded python> backend/tests/test_cards_plateau_route.py
"""
import asyncio
import hashlib
import os
import pathlib
import re
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
from PIL import Image                                           # noqa: E402

from app.services.cards import core, plateau                    # noqa: E402

IMAGES = pathlib.Path(_tmp, "images")


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


def _tuiles_sur_disque() -> list:
    return sorted(p.name for p in IMAGES.glob("tuile_*"))


def _nb_decks() -> int:
    return len(core.list_deck_summaries())


@pytest.fixture(autouse=True)
def _images():
    Image.effect_mandelbrot((600, 520), (-2, -1.5, 1, 1.5), 40).convert(
        "RGB").save(IMAGES / "fond.png")
    Image.new("RGB", (40, 40), (200, 30, 30)).save(IMAGES / "dos.png")
    yield


def _post(**corps):
    base = {"image": "fond.png", "format": "hex_p90", "colonnes": 6,
            "rangees": 4, "dpi": 72}
    base.update(corps)
    return _api("POST", "/api/cards/decks/plateau", json=base)


def test_cree_un_jeu_plateau_de_24_tuiles():
    r = _post()
    assert r.status_code == 200, r.text
    d = r.json()
    deck = d["deck"]
    assert deck["categorie"] == "plateau" and deck["name"] == "Plateau — fond"
    assert deck["format"]["fmt"] == "hex_p90"
    assert deck["frame"]["family"] == "none"
    assert deck["data"]["columns"] == ["nom", "art", "dos", "rang", "colonne"]
    assert deck["data"]["map"] == {"art": "art", "dos": "back"}
    assert deck["data"]["rows"][0][0] == "plateau-01"
    assert deck["data"]["rows"][23][3:] == ["4", "6"]
    assert [l[1] for l in deck["data"]["rows"]] == d["tuiles"]
    assert len(d["tuiles"]) == 24
    assert all((IMAGES / t).is_file() for t in d["tuiles"])
    assert re.fullmatch(r"tuile_fond_[0-9a-z]{8}_r01c01\.png", d["tuiles"][0])
    assert d["tuiles"][0].split("_")[2] == deck["id"][-8:]
    assert isinstance(d["ppp"], float) and d["ppp"] > 0
    with Image.open(IMAGES / d["tuiles"][0]) as t:
        assert t.mode == "RGBA"


def test_verso_commun_nom_et_prefixe_photolab():
    (IMAGES / "photolab_20261108-101500_carte du roi.png").write_bytes(
        (IMAGES / "fond.png").read_bytes())
    d = _post(image="photolab_20261108-101500_carte du roi.png",
              verso_commun="dos.png", colonnes=2, rangees=2).json()
    assert d["deck"]["name"] == "Plateau — carte du roi"
    assert d["tuiles"][0].startswith("tuile_carte du roi_")
    assert {l[2] for l in d["deck"]["data"]["rows"]} == {"dos.png"}
    assert _post(name="Mon plateau", colonnes=1, rangees=1
                 ).json()["deck"]["name"] == "Mon plateau"


def test_image_source_intacte():
    avant = _empreintes()["fond.png"]
    assert _post().status_code == 200
    assert _empreintes()["fond.png"] == avant


def test_lignee_plateau():
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory, init_db
    asyncio.run(init_db())
    d = _post(colonnes=2, rangees=1).json()

    async def lire():
        async with async_session_factory() as s:
            return (await s.execute(select(LibraryAsset).where(
                LibraryAsset.filename.in_(d["tuiles"])))).scalars().all()
    lignes = asyncio.run(lire())
    assert len(lignes) == 2
    for l in lignes:
        assert l.parent_filename == "fond.png" and l.relation == "plateau"
        assert l.source == "cardforge" and l.deck_id == d["deck"]["id"]


def test_deux_decoupes_n_ecrasent_rien():
    a = _post().json()
    empr = _empreintes()
    n = _nb_decks()
    b = _post().json()
    assert _nb_decks() == n + 1
    assert not set(a["tuiles"]) & set(b["tuiles"])
    apres = _empreintes()
    assert all(apres[t] == empr[t] for t in a["tuiles"])
    assert all(t in apres for t in b["tuiles"])


def test_echec_a_mi_chemin_ne_laisse_rien(monkeypatch):
    avant, n = _tuiles_sur_disque(), _nb_decks()
    vrai, compte = plateau._ecrire_tuile, {"n": 0}

    def casse(tuile, chemin, dpi):
        compte["n"] += 1
        if compte["n"] == 7:
            chemin.write_bytes(b"partiel")        # un fichier à moitié écrit
            raise OSError(28, "No space left on device")
        return vrai(tuile, chemin, dpi)
    monkeypatch.setattr(plateau, "_ecrire_tuile", casse)
    r = _post()
    assert r.status_code == 500
    assert "Création du plateau impossible" in r.json()["detail"]
    assert compte["n"] == 7
    assert _tuiles_sur_disque() == avant and _nb_decks() == n


@pytest.mark.parametrize("corps,code", [
    ({"format": "poker"}, 400), ({"format": "poker_us"}, 400),
    ({"colonnes": 0}, 400), ({"colonnes": 30, "rangees": 17}, 400),
    ({"colonnes": None}, 400), ({"dpi": 10}, 400), ({"dpi": True}, 400),
    ({"image": "absente.png"}, 404), ({"image": "../x.png"}, 400),
    ({"verso_commun": "absent.png"}, 404), ({"cadrage": "x"}, 400),
    ({"cadrage": {"zoom": "gros"}}, 400)])
def test_refus_sans_rien_creer(corps, code):
    avant, n = _tuiles_sur_disque(), _nb_decks()
    r = _post(**corps)
    assert r.status_code == code, r.text
    assert _tuiles_sur_disque() == avant and _nb_decks() == n


def test_image_illisible_ne_cree_rien():
    (IMAGES / "faux.png").write_bytes(b"pas une image")
    avant, n = _tuiles_sur_disque(), _nb_decks()
    r = _post(image="faux.png")
    assert r.status_code == 400
    assert _tuiles_sur_disque() == avant and _nb_decks() == n


def test_messages_refus_traduits():
    """Chaque message neuf de plateau.py a son entrée fr + en au dictionnaire
    (erreurs.json) ; rendus avec Accept-Language: en, les refus sont en anglais."""
    from app.i18n import erreurs as ERR
    sources = {e["fr"] for e in ERR.dico().values() if e["src"] == "fr"}
    for fr in ("Format non hexagonal : {fmt}",
               "colonnes et rangées doivent tenir entre 1 et {COTE_MAX}",
               "{v} tuiles : {TUILES_MAX} au plus",
               "{nom} doit être un entier (reçu {valeur})",
               "{champ} : un nombre attendu",
               "format non hexagonal : {fmt_id}",
               "dpi : un entier attendu",
               "cadrage : un objet {zoom, x, y} attendu",
               "image illisible : {image}",
               "Création du plateau impossible : écriture refusée ({v})"):
        assert fr in sources, fr
    en = {"Accept-Language": "en"}
    r = _api("POST", "/api/cards/decks/plateau", headers=en, json={
        "image": "fond.png", "format": "hex_p90", "colonnes": 0, "rangees": 4})
    assert r.status_code == 400
    assert r.json()["detail"].startswith("columns and rows must be between 1 and")
    r = _api("POST", "/api/cards/decks/plateau", headers=en, json={
        "image": "fond.png", "format": "hex_p90", "colonnes": 2, "rangees": 2,
        "dpi": True})
    assert r.json()["detail"] == "dpi: an integer is expected"


def test_impression_hex_du_jeu_plateau():
    d = _post(colonnes=2, rangees=2).json()
    r = _api("POST", f"/api/cards/{d['deck']['id']}/print/hex/plan", json={})
    assert r.status_code == 200, r.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
