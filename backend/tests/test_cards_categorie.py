"""Champ `categorie` du jeu (plateau lot 1, tâche 4).

Seul le SERVEUR pose la catégorie (`poser_categorie`) ; le corps d'un
autosave ne le peut pas, et un autosave ne l'efface pas. Le résumé de la
galerie la porte (`""` pour un jeu ordinaire), et un index de listing v1 est
ignoré puis reconstruit en v2 sans perdre de jeu.
"""
import asyncio
import json
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
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402

from app.services.cards import core                             # noqa: E402


def _api(method: str, path: str, **kw):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def test_categorie_gardee_et_filtree():
    assert core.CATEGORIES == ("plateau",)
    assert core.normalize_deck(
        {"id": "deck_abcdef12", "categorie": "plateau"})["categorie"] == "plateau"
    assert "categorie" not in core.normalize_deck(
        {"id": "deck_abcdef12", "categorie": "pirate"})
    assert "categorie" not in core.normalize_deck(
        {"id": "deck_abcdef12", "categorie": ["plateau"]})
    assert "categorie" not in core.default_doc("deck_abcdef12")


def test_poser_categorie():
    did = core.create_deck("p")["id"]
    try:
        doc = core.poser_categorie(did, "plateau")
        assert doc["categorie"] == "plateau"
        assert core.read_deck(did)["categorie"] == "plateau"
        with pytest.raises(ValueError):
            core.poser_categorie(did, "pirate")
        assert core.read_deck(did)["categorie"] == "plateau"
        assert core.poser_categorie("deck_00000000", "plateau") is None
    finally:
        core.delete_deck(did)


def test_categorie_survit_a_l_autosave():
    did = core.create_deck("Plateau")["id"]
    try:
        core.poser_categorie(did, "plateau")
        core.patch_deck(did, {"name": "Mon plateau", "type": {"slots": []}})
        d = core.read_deck(did)
        assert d["categorie"] == "plateau" and d["name"] == "Mon plateau"
    finally:
        core.delete_deck(did)


def test_client_ne_pose_pas_la_categorie():
    did = core.create_deck("x")["id"]
    try:
        core.patch_deck(did, {"categorie": "plateau"})
        assert "categorie" not in core.read_deck(did)
    finally:
        core.delete_deck(did)


def test_resume_et_index():
    simple = core.create_deck("simple")["id"]
    plat = core.create_deck("plat")["id"]
    core.poser_categorie(plat, "plateau")
    try:
        # à froid puis servi depuis l'index : le résumé porte la catégorie
        for _ in range(2):
            r = _api("GET", "/api/cards/decks", params={"limit": 500})
            assert r.status_code == 200, r.text
            par_id = {x["id"]: x for x in r.json()["decks"]}
            assert par_id[plat]["categorie"] == "plateau"
            assert par_id[simple]["categorie"] == ""
        brut = json.loads(
            (core.decks_root() / core.INDEX_NAME).read_text(encoding="utf-8"))
        assert brut["v"] == core.INDEX_VERSION == 2
        assert brut["decks"][plat]["categorie"] == "plateau"
    finally:
        core.delete_deck(simple)
        core.delete_deck(plat)


def test_index_v1_ignore_et_reconstruit():
    plat = core.create_deck("plat")["id"]
    core.poser_categorie(plat, "plateau")
    autre = core.create_deck("autre")["id"]
    try:
        core.list_deck_summaries()
        idx = core.decks_root() / core.INDEX_NAME
        v2 = json.loads(idx.read_text(encoding="utf-8"))
        # un index v1 : mêmes empreintes, mais sans catégorie
        v1 = {"v": 1, "decks": {
            k: {c: e[c] for c in ("name", "created", "updated", "mtime", "size")}
            for k, e in v2["decks"].items()}}
        idx.write_text(json.dumps(v1), encoding="utf-8")
        res = {x["id"]: x for x in core.list_deck_summaries()}
        assert res[plat]["categorie"] == "plateau"   # pas servi depuis le v1
        assert autre in res
        nouveau = json.loads(idx.read_text(encoding="utf-8"))
        assert nouveau["v"] == 2
        assert nouveau["decks"][plat]["categorie"] == "plateau"
    finally:
        core.delete_deck(plat)
        core.delete_deck(autre)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
