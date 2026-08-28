"""Bibliothèque unifiée — import Figma + mtime de la liste + miroirs du
sélecteur (plan 2026-08-28-bibliotheque-unifiee-guide-impression).

Le banc ne SORT jamais : les deux pas réseau de l'import Figma sont des
hooks module monkeypatchés (patron _lancer_startfile de print3d).

Run: pytest tests/test_library_picker.py -q
"""
import json as _json
import os
import pathlib
import sys
import tempfile
import time

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["FIGMA_TOKEN"] = "figd_banc"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_PNG = b"\x89PNG\r\n\x1a\n" + b"figma-banc-payload"


# ── A. la cible Figma : parse PUR, refus parlants ────────────────────────────

def test_figma_cible_parse_les_formes_d_url():
    from app.services.figma_import import figma_cible
    for u in (
        "https://www.figma.com/design/AbC123xyz/Mon-fichier?node-id=12-34&t=q",
        "https://www.figma.com/file/AbC123xyz/Fichier?node-id=12%3A34",
        "https://figma.com/design/AbC123xyz/x?a=1&node-id=12:34",
    ):
        c = figma_cible(u)
        assert c == {"cle": "AbC123xyz", "node": "12:34"}, (u, c)


def test_figma_cible_refuse_parlant():
    from app.services.figma_import import figma_cible
    with pytest.raises(ValueError, match="[Ff]igma"):
        figma_cible("https://exemple.com/design/AbC/x?node-id=1-2")
    # sans node-id : le remède est DIT (copier le lien du calque)
    with pytest.raises(ValueError, match="calque"):
        figma_cible("https://www.figma.com/design/AbC123xyz/Fichier")


# ── B. la route d'import : mockée bout-à-bout, erreurs aux bons codes ────────

def test_la_route_import_figma():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.config import settings
        from app.main import app
        from app.services import figma_import as FI
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)

        appels = {"json": [], "octets": []}

        async def faux_json(url, jeton):
            appels["json"].append((url, jeton))
            return {"images": {"12:34": "https://cdn.figma/rendu.png"}}

        async def faux_octets(url):
            appels["octets"].append(url)
            return _PNG

        vrai_json, vrai_octets = FI._get_json, FI._get_bytes
        FI._get_json, FI._get_bytes = faux_json, faux_octets
        try:
            async with AsyncClient(transport=transport,
                                   base_url="http://t") as c:
                url = ("https://www.figma.com/design/AbC123xyz/Fichier"
                       "?node-id=12-34")
                r = await c.post("/api/images/import-figma",
                                 json={"url": url})
                assert r.status_code == 200, r.text
                nom = r.json()["filename"]
                assert nom == "figma_AbC123xyz_12-34.png"
                ecrit = pathlib.Path(os.environ["IMAGES_FOLDER"]) / nom
                assert ecrit.read_bytes() == _PNG
                # l'API Figma a bien reçu la clé, le node et le jeton
                assert "AbC123xyz" in appels["json"][0][0]
                assert "ids=12:34" in appels["json"][0][0]
                assert appels["json"][0][1] == "figd_banc"
                # ré-importer RÉÉCRIT en place (même nom, pas de doublon)
                r = await c.post("/api/images/import-figma",
                                 json={"url": url})
                assert r.status_code == 200
                assert r.json()["filename"] == nom
                # URL invalide → 400 parlant
                r = await c.post("/api/images/import-figma",
                                 json={"url": "https://figma.com/design/A/x"})
                assert r.status_code == 400
                # Figma en erreur → 502 avec le message TEL QUEL
                async def json_err(url2, jeton2):
                    return {"err": "Figma 403: invalid token"}
                FI._get_json = json_err
                r = await c.post("/api/images/import-figma",
                                 json={"url": url})
                assert r.status_code == 502 and "403" in r.json()["detail"]
                # rendu non-PNG → 502 parlant
                FI._get_json = faux_json

                async def octets_html(url2):
                    return b"<html>pas une image</html>"
                FI._get_bytes = octets_html
                r = await c.post("/api/images/import-figma",
                                 json={"url": url})
                assert r.status_code == 502 and "PNG" in r.json()["detail"]
                # jeton absent → 409 qui NOMME FIGMA_TOKEN et le .env
                ancien = settings.FIGMA_TOKEN
                settings.FIGMA_TOKEN = ""
                try:
                    r = await c.post("/api/images/import-figma",
                                     json={"url": url})
                    assert r.status_code == 409
                    assert "FIGMA_TOKEN" in r.json()["detail"]
                finally:
                    settings.FIGMA_TOKEN = ancien
        finally:
            FI._get_json, FI._get_bytes = vrai_json, vrai_octets

    asyncio.run(scenario())


# ── C. la liste des images porte mtime (le picker trie « récentes ») ────────

def test_la_liste_des_images_porte_mtime():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.main import app
        dossier = pathlib.Path(os.environ["IMAGES_FOLDER"])
        vieux = dossier / "banc_vieux.png"
        neuf = dossier / "banc_neuf.png"
        vieux.write_bytes(_PNG)
        neuf.write_bytes(_PNG)
        os.utime(vieux, (time.time() - 3600, time.time() - 3600))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/api/images")
            par_nom = {i["filename"]: i for i in r.json()["images"]}
            assert isinstance(par_nom["banc_neuf.png"]["mtime"], float)
            assert (par_nom["banc_neuf.png"]["mtime"]
                    > par_nom["banc_vieux.png"]["mtime"])

    asyncio.run(scenario())
