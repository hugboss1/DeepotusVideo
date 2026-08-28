"""Bibliothèque — provenance & classement (plan
2026-08-28-bibliotheque-provenance-envoyer-vers, chantier A).

Table d'index `library_assets` (source par FONCTION productrice),
alimentée au dépôt par les routes, rétro-remplie par heuristique de noms
(origin honnête), exposée par GET /api/images. Le banc ne SORT jamais
(seules les routes locales — upload, process crop, rename, delete — sont
exercées ; aucun tir fal/OpenAI/Figma).

Run: pytest tests/test_library_provenance.py -q
"""
import io
import os
import pathlib
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_PNG = b"\x89PNG\r\n\x1a\n" + b"provenance-banc"


def _vrai_png(w=8, h=8) -> bytes:
    """Un PNG décodable (le crop de /images/process l'ouvre par PIL)."""
    from PIL import Image
    im = Image.new("RGB", (w, h), (10, 200, 30))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# ── A. l'heuristique de noms : pure, honnête sur l'ambigu ────────────────────

def test_heuristique_des_prefixes():
    from app.services.library_index import heuristique
    attendu = {
        "gen_sprite_ab12cd34.png": "sprites",
        "vector_0abc_2x_t.png": "vectorlab",
        "figma_AbC123_12-34.png": "figma",
        "news_deadbeef.png": "news",
        "board_12345678.png": "atelier",
        "shot_ab12cd34_2.png": "assets3d",
        "gen_11223344.png": "generation",
        "logo perso.webp": "inconnu",
    }
    for nom, src in attendu.items():
        assert heuristique(nom) == src, nom


def test_les_sources_ont_un_libelle():
    from app.services.library_index import SOURCES
    for slug in ("generation", "retouche", "matieres", "atelier",
                 "cardforge", "vectorlab", "figma", "news", "sprites",
                 "assets3d", "import", "import_url", "inconnu"):
        assert slug in SOURCES and SOURCES[slug], slug


# ── B. dépôt par les routes locales : la source suit le geste ────────────────

def test_upload_et_process_sont_sources():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # import fichier quelconque → source "import"
            r = await c.post("/api/images/upload",
                             files={"file": ("mon upload.png", _PNG,
                                            "image/png")})
            assert r.status_code == 200, r.text
            # export Vectorlab (même route, préfixe vector_) → "vectorlab"
            r = await c.post("/api/images/upload",
                             files={"file": ("vector_0abc_2x.png", _PNG,
                                            "image/png")})
            assert r.status_code == 200, r.text
            # retouche locale (crop PIL) d'une image posée → "retouche"
            (pathlib.Path(os.environ["IMAGES_FOLDER"])
             / "banc_source.png").write_bytes(_vrai_png(80, 40))
            r = await c.post("/api/images/process",
                             json={"op": "crop", "filename":
                                   "banc_source.png", "ratio": "1:1"})
            assert r.status_code == 200, r.text
            recadre = r.json()["images"][0]

            r = await c.get("/api/images")
            par_nom = {i["filename"]: i for i in r.json()["images"]}
            assert par_nom["mon upload.png"]["source"] == "import"
            assert par_nom["mon upload.png"]["source_origin"] == "depot"
            assert par_nom["vector_0abc_2x.png"]["source"] == "vectorlab"
            assert par_nom[recadre]["source"] == "retouche"
            assert par_nom[recadre]["source_origin"] == "depot"

    asyncio.run(scenario())


def test_rename_migre_et_delete_retire():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from sqlalchemy import select
        from app.main import app
        from app.services.storage import (LibraryAsset,
                                          async_session_factory, init_db)
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/images/upload",
                             files={"file": ("a renommer.png", _PNG,
                                            "image/png")})
            assert r.status_code == 200
            r = await c.post("/api/images/a renommer.png/rename",
                             json={"new_name": "renomme net"})
            assert r.status_code == 200, r.text
            final = r.json()["new"]
            async with async_session_factory() as s:
                rows = (await s.execute(select(LibraryAsset))).scalars().all()
                par_nom = {x.filename: x for x in rows}
            assert "a renommer.png" not in par_nom
            assert par_nom[final].source == "import"
            assert par_nom[final].origin == "depot"

            r = await c.delete(f"/api/images/{final}")
            assert r.status_code == 200
            async with async_session_factory() as s:
                rows = (await s.execute(select(LibraryAsset))).scalars().all()
            assert final not in {x.filename for x in rows}

    asyncio.run(scenario())


# ── C. rétro-remplissage : heuristique DITE, le dépôt exact intouché ─────────

def test_reconcilier_retro_remplit_honnetement():
    import asyncio

    async def scenario():
        from sqlalchemy import select
        from app.services import library_index as LI
        from app.services.storage import (LibraryAsset,
                                          async_session_factory, init_db)
        await init_db()
        dossier = pathlib.Path(os.environ["IMAGES_FOLDER"])
        (dossier / "gen_ffee0011.png").write_bytes(_PNG)
        (dossier / "figma_Xy12_3-4.png").write_bytes(_PNG)
        (dossier / "banc_depot_exact.png").write_bytes(_PNG)
        await LI.noter(["banc_depot_exact.png"], "cardforge",
                       deck_id="deck_banc")
        n = await LI.reconcilier()
        assert n >= 2
        # idempotent : rien de neuf au second passage
        assert await LI.reconcilier() == 0
        async with async_session_factory() as s:
            rows = (await s.execute(select(LibraryAsset))).scalars().all()
            par_nom = {x.filename: x for x in rows}
        assert par_nom["gen_ffee0011.png"].source == "generation"
        assert par_nom["gen_ffee0011.png"].origin == "heuristique"
        assert par_nom["figma_Xy12_3-4.png"].source == "figma"
        # la ligne déposée EXACTE n'est pas écrasée par l'heuristique
        assert par_nom["banc_depot_exact.png"].source == "cardforge"
        assert par_nom["banc_depot_exact.png"].origin == "depot"
        assert par_nom["banc_depot_exact.png"].deck_id == "deck_banc"

    asyncio.run(scenario())


def test_l_api_replie_sur_l_heuristique_a_la_volee():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        # fichier posé À LA MAIN, jamais noté ni réconcilié
        (pathlib.Path(os.environ["IMAGES_FOLDER"])
         / "news_horsindex.png").write_bytes(_PNG)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/api/images")
            par_nom = {i["filename"]: i for i in r.json()["images"]}
        assert par_nom["news_horsindex.png"]["source"] == "news"
        assert par_nom["news_horsindex.png"]["source_origin"] == "heuristique"

    asyncio.run(scenario())


# ── D. miroirs bundle (posés par patch_bundle_libprov, T3) ───────────────────

def test_le_miroir_bundle_chips():
    """Les chips de provenance vivent dans le BUNDLE (patcher libprov,
    maillon APRÈS libpicker) — ces pins attrapent un effacement silencieux
    de la chaîne. Le pin __dzLibPicker×10 du banc picker doit TENIR."""
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    bundle = (racine / "frontend" / "dist" / "assets"
              / "index-BEOJX8L5.js").read_text("utf-8")
    assert bundle.count("__dzLibPicker") == 10   # inchangé par libprov
    assert bundle.count("dzlp-chips") >= 3       # chips du sélecteur
    assert 'source:S.source||"inconnu"' in bundle  # items vm sourcés
    assert bundle.count("__dzSrcChips") == 2     # rangée de chips de vm
    patcher = (racine / "scripts"
               / "patch_bundle_libprov.py").read_text("utf-8")
    assert "guard_downstream" in patcher and "STABLE_PROBES" in patcher
