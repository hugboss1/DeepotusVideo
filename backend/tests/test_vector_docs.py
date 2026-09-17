"""Vectorlab — documents vectoriels versionnés (fichiers + index SQLite).

Phase 0 du plan docs/superpowers/plans/2026-08-27-editeur-vectoriel-vitrail.md :
le magasin disque (écriture atomique, historique .v<n>.json ×10), l'index
SQLite VectorDoc, le CRUD /api/vector/docs, et les miroirs de surface
(mount /vectorlab, panneau chapitre de l'Atelier).

Run: pytest tests/test_vector_docs.py -q
"""
import json
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Le pont cartes (27/08) ajoute `deck_id` par _auto_migrate : la migration
# est exercée EN VRAI — la base est pré-créée ici à l'ANCIENNE forme
# (vector_docs sans deck_id, une ligne héritée) AVANT tout import de l'app ;
# le premier init_db() la migre, et TOUT le banc tourne sur la base migrée.
import sqlite3

_con = sqlite3.connect(pathlib.Path(_tmp, "t.db"))
_con.execute("""CREATE TABLE vector_docs (
    id VARCHAR(36) NOT NULL PRIMARY KEY, name VARCHAR(120) NOT NULL,
    chapter_id VARCHAR(36), entity_id VARCHAR(36),
    role VARCHAR(12) NOT NULL, version INTEGER NOT NULL,
    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)""")
_con.execute(
    "INSERT INTO vector_docs VALUES ('vd-legacy', 'Legacy pré-migration', "
    "'ch-legacy', NULL, 'decor', 1, '2026-08-27 00:00:00.000000', "
    "'2026-08-27 00:00:00.000000')")
_con.commit()
_con.close()


def _doc(nom="Baie test"):
    return {"v": 1, "nom": nom, "taille": {"w": 640, "h": 960},
            "calques": [{"id": "c1", "nom": "plombs", "visible": True,
                         "verrou": False, "objets": []}]}


# ── A. le magasin disque : atomique, historisé ───────────────────────────────

def test_le_magasin_ecrit_atomique_et_historise():
    from app.services import vector_store as VS
    doc = _doc()
    did = VS.creer(doc)                    # écrit <did>.json, version 1
    assert VS.lire(did)["nom"] == "Baie test"
    doc["nom"] = "Baie v2"
    v = VS.ecrire(did, doc)                # bump version + garde .v1.json
    assert v == 2 and VS.lire(did)["nom"] == "Baie v2"
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    assert (dossier / f"{did}.v1.json").is_file()
    # l'écriture est atomique : jamais de fichier tronqué visible
    assert json.loads(
        (dossier / f"{did}.json").read_text("utf-8"))["nom"] == "Baie v2"


def test_l_historique_garde_dix_versions_et_la_suppression_archive():
    from app.services import vector_store as VS
    doc = _doc("Rotation")
    did = VS.creer(doc)
    for i in range(12):                    # 12 réécritures → versions 2..13
        doc["nom"] = f"Rotation {i}"
        VS.ecrire(did, doc)
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    hist = sorted(dossier.glob(f"{did}.v*.json"))
    assert len(hist) == 10                 # élagué aux 10 dernières
    # la suppression n'efface pas : le courant part en historique
    v_finale = VS.version(did)
    VS.supprimer(did)
    assert not (dossier / f"{did}.json").is_file()
    assert (dossier / f"{did}.v{v_finale}.json").is_file()


# ── B. l'index SQLite : VectorDoc (catalogue + ancrage chapitre/entité) ──────

def test_l_index_sqlite_porte_le_catalogue_et_l_ancrage():
    import asyncio
    from app.services.storage import (VectorDoc, async_session_factory,
                                      init_db)

    async def scenario():
        await init_db()
        async with async_session_factory() as s:
            s.add(VectorDoc(id="vd1", name="Baie test", chapter_id="ch1",
                            role="decor", version=1))
            await s.commit()
        async with async_session_factory() as s:
            row = await s.get(VectorDoc, "vd1")
            assert row.name == "Baie test" and row.role == "decor"
            assert row.chapter_id == "ch1" and row.entity_id is None
            assert row.version == 1 and row.updated_at is not None

    asyncio.run(scenario())


# ── C. le CRUD /api/vector/docs ──────────────────────────────────────────────

def test_le_crud_vector_docs():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # créer (rôle validé, version 1)
            r = await c.post("/api/vector/docs", json={
                "name": "Baie ogivale", "role": "decor",
                "chapter_id": "ch-42", "doc": _doc("Baie ogivale")})
            assert r.status_code == 200, r.text
            did = r.json()["id"]
            assert r.json()["version"] == 1
            # rôle hors liste → 400, rien d'écrit
            r = await c.post("/api/vector/docs", json={
                "name": "X", "role": "gothico", "doc": _doc()})
            assert r.status_code == 400
            # liste filtrée par chapitre puis par rôle
            await c.post("/api/vector/docs", json={
                "name": "Halo", "role": "lumiere", "doc": _doc("Halo")})
            r = await c.get("/api/vector/docs",
                            params={"chapter_id": "ch-42"})
            assert [d["name"] for d in r.json()["docs"]] == ["Baie ogivale"]
            r = await c.get("/api/vector/docs", params={"role": "lumiere"})
            assert [d["name"] for d in r.json()["docs"]] == ["Halo"]
            # lire : méta + contenu
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.status_code == 200
            assert r.json()["meta"]["role"] == "decor"
            assert r.json()["doc"]["taille"] == {"w": 640, "h": 960}
            # réécrire : version bump, contenu remplacé
            d2 = _doc("Baie ogivale")
            d2["calques"][0]["nom"] = "verre"
            r = await c.put(f"/api/vector/docs/{did}", json={"doc": d2})
            assert r.status_code == 200 and r.json()["version"] == 2
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["doc"]["calques"][0]["nom"] == "verre"
            assert r.json()["meta"]["version"] == 2
            # document invalide → 400
            r = await c.put(f"/api/vector/docs/{did}", json={"doc": {"x": 1}})
            assert r.status_code == 400
            # suppression = archivage : la ligne part, le contenu reste
            r = await c.delete(f"/api/vector/docs/{did}")
            assert r.status_code == 200
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.status_code == 404
        dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
        assert list(dossier.glob("*.v*.json"))   # l'archive est bien là

    asyncio.run(scenario())


# ── E. l'export SVG : le client compile, le serveur stocke et sert ───────────

def test_l_export_svg_stocke_et_sert():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={
                "name": "Export", "role": "decor", "doc": _doc("Export")})
            did = r.json()["id"]
            # avant tout export : 404 parlant
            r = await c.get(f"/api/vector/docs/{did}/export.svg")
            assert r.status_code == 404
            assert "export" in r.json()["detail"].lower()
            # pousser un SVG compilé côté client
            svg1 = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect x="1" y="1" width="6" height="6" fill="#0047AB"/></svg>'
            r = await c.post(f"/api/vector/docs/{did}/export",
                             json={"svg": svg1})
            assert r.status_code == 200, r.text
            assert r.json()["filename"] == f"{did}.svg"
            fichier = pathlib.Path(os.environ["VECTOR_FOLDER"]) / f"{did}.svg"
            assert fichier.is_file()
            # le GET sert le SVG stocké, au bon type
            r = await c.get(f"/api/vector/docs/{did}/export.svg")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("image/svg+xml")
            assert r.text == svg1
            # le ré-export remplace
            svg2 = svg1.replace("#0047AB", "#9B111E")
            await c.post(f"/api/vector/docs/{did}/export", json={"svg": svg2})
            r = await c.get(f"/api/vector/docs/{did}/export.svg")
            assert "#9B111E" in r.text
            # refus nets : pas un svg ; id inconnu
            r = await c.post(f"/api/vector/docs/{did}/export",
                             json={"svg": "PAS DU SVG"})
            assert r.status_code == 400
            r = await c.post("/api/vector/docs/fantome/export",
                             json={"svg": svg1})
            assert r.status_code == 404

    asyncio.run(scenario())


# ── F. le mode vitrail lit la FICHE ÉPINGLÉE — l'unique source ───────────────

def test_l_endpoint_vitrail_sert_la_fiche_epinglee():
    """`GET /api/vector/vitrail` sert `familles.vitrail` de
    style_vitrail.json (copie épinglée du skill). Le test compare À L'OCTET
    avec le fichier : toute divergence endpoint↔fiche rougit ici — aucune
    constante recopiée nulle part."""
    import asyncio
    from httpx import AsyncClient, ASGITransport

    services = (pathlib.Path(__file__).resolve().parent.parent
                / "app" / "services")
    fiche = json.loads((services / "style_vitrail.json").read_text("utf-8"))

    async def scenario():
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/api/vector/vitrail")
            assert r.status_code == 200, r.text
            corps = r.json()
            assert corps["famille"] == fiche["familles"]["vitrail"]
            assert "épinglée" in corps["source"]
            # les pièces dont le Vectorlab dépend sont bien là
            f = corps["famille"]
            assert len(f["palette"]["ancres"]) == 5
            assert f["palette"]["contour"]["noir_brun"].startswith("#")
            lo, hi = f["bornes"]["part_contours_plomb"]
            assert 0 < lo < hi < 1
            assert f["bornes"]["part_bordure_ornementale"]

    asyncio.run(scenario())


# ── D. les surfaces : mount /vectorlab et panneau chapitre de l'Atelier ──────

def test_le_mount_vectorlab_et_le_panneau_atelier():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/vectorlab/")
            assert r.status_code == 200 and "Vectorlab" in r.text

    asyncio.run(scenario())
    # miroirs atelier : le panneau par chapitre interroge /vector/docs et
    # ouvre l'éditeur — même nature d'assertion que les miroirs de presets.
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    js = (racine / "frontend" / "atelier" / "atelier.js").read_text("utf-8")
    assert "Éléments vectoriels" in (racine / "frontend" / "atelier"
                                     / "index.html").read_text("utf-8")
    assert "/vector/docs?chapter_id=" in js
    assert "/vectorlab/?doc=" in js
    assert "loadVectorDocs" in js


# ── G. les vignettes (phase 6) : mini-PNG au save, à CÔTÉ du JSON ────────────
# Jamais par /images/upload : chaque sauvegarde spammerait la Library réelle.
# Le magasin stocke des octets ; c'est la ROUTE qui vérifie le magic PNG.

_PNG_MIN = b"\x89PNG\r\n\x1a\n" + b"vectorlab-banc-p6"


def test_le_magasin_des_vignettes_ecrit_lit_copie():
    from app.services import vector_store as VS
    did = VS.creer(_doc("Vignette"))
    assert VS.a_vignette(did) is False
    assert VS.lire_vignette(did) is None
    VS.ecrire_vignette(did, _PNG_MIN)
    assert VS.a_vignette(did) is True
    assert VS.lire_vignette(did) == _PNG_MIN
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    assert (dossier / f"{did}.png").is_file()
    # la copie (socle de « dupliquer ») : la cible hérite des mêmes octets
    d2 = VS.creer(_doc("Copie"))
    VS.copier_vignette(did, d2)
    assert VS.lire_vignette(d2) == _PNG_MIN
    # source sans vignette → no-op silencieux, rien de créé
    d3 = VS.creer(_doc("Sans"))
    VS.copier_vignette("fantome", d3)
    assert VS.a_vignette(d3) is False
    # supprimer ARCHIVE le doc mais emporte la vignette : artefact dérivé,
    # elle renaît au premier Sauver — pas d'orpheline sur disque
    VS.supprimer(did)
    assert VS.a_vignette(did) is False
    assert (dossier / f"{did}.v1.json").is_file()   # l'archive, elle, reste


def test_les_routes_vignette():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={
                "name": "Vignette route", "role": "decor", "doc": _doc()})
            did = r.json()["id"]
            # avant la première : 404 parlant, et la méta le dit
            r = await c.get(f"/api/vector/docs/{did}/vignette.png")
            assert r.status_code == 404
            assert "vignette" in r.json()["detail"].lower()
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["meta"]["vignette"] is False
            # refus nets : pas un PNG ; doc inconnu
            r = await c.post(f"/api/vector/docs/{did}/vignette",
                             content=b"PAS UN PNG",
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 400
            r = await c.post("/api/vector/docs/fantome/vignette",
                             content=_PNG_MIN,
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 404
            # la vignette s'écrit puis se sert au bon type, octets exacts
            r = await c.post(f"/api/vector/docs/{did}/vignette",
                             content=_PNG_MIN,
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 200, r.text
            assert r.json()["filename"] == f"{did}.png"
            r = await c.get(f"/api/vector/docs/{did}/vignette.png")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("image/png")
            assert r.content == _PNG_MIN
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["meta"]["vignette"] is True

    asyncio.run(scenario())


# ── H. les liaisons (phase 6) : instancier par RÉFÉRENCE, zéro orpheline ─────
# Un seul document derrière toutes les instances — l'édition se voit partout
# par construction ; retirer la liaison ne touche jamais le doc.

def test_le_crud_des_liaisons():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # un doc de bibliothèque (sans chapitre) et un doc propre à ch-p6a
            r = await c.post("/api/vector/docs", json={
                "name": "Décor partagé p6", "role": "decor", "doc": _doc()})
            biblio = r.json()["id"]
            r = await c.post("/api/vector/docs", json={
                "name": "Propre p6", "role": "decor", "chapter_id": "ch-p6a",
                "doc": _doc()})
            propre = r.json()["id"]
            # instancier le même doc dans DEUX chapitres
            r = await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6a", "doc_id": biblio})
            assert r.status_code == 200, r.text
            r = await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6b", "doc_id": biblio})
            assert r.status_code == 200
            # refus nets : doublon → 409 ; déjà PROPRE au chapitre → 409 ;
            # doc inconnu → 404 ; corps incomplet → 400
            r = await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6a", "doc_id": biblio})
            assert r.status_code == 409
            r = await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6a", "doc_id": propre})
            assert r.status_code == 409
            r = await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6a",
                                   "doc_id": "fantome"})
            assert r.status_code == 404
            r = await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6a"})
            assert r.status_code == 400
            # GET filtré par chapitre puis par doc
            r = await c.get("/api/vector/links",
                            params={"chapter_id": "ch-p6b"})
            assert [l["doc_id"] for l in r.json()["links"]] == [biblio]
            r = await c.get("/api/vector/links", params={"doc_id": biblio})
            assert sorted(l["chapter_id"] for l in r.json()["links"]) == \
                ["ch-p6a", "ch-p6b"]
            # retirer la liaison : elle part, le doc ne bouge pas
            r = await c.delete("/api/vector/links",
                               params={"chapter_id": "ch-p6b",
                                       "doc_id": biblio})
            assert r.status_code == 200
            r = await c.get("/api/vector/links", params={"doc_id": biblio})
            assert [l["chapter_id"] for l in r.json()["links"]] == ["ch-p6a"]
            r = await c.get(f"/api/vector/docs/{biblio}")
            assert r.status_code == 200
            # retirer une liaison absente → 404
            r = await c.delete("/api/vector/links",
                               params={"chapter_id": "ch-p6b",
                                       "doc_id": biblio})
            assert r.status_code == 404

    asyncio.run(scenario())


def test_supprimer_doc_ou_chapitre_emporte_les_liaisons():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # DELETE du doc → ses liaisons partent avec lui
            r = await c.post("/api/vector/docs", json={
                "name": "Éphémère p6", "role": "decor", "doc": _doc()})
            did = r.json()["id"]
            await c.post("/api/vector/links",
                         json={"chapter_id": "ch-p6c", "doc_id": did})
            await c.delete(f"/api/vector/docs/{did}")
            r = await c.get("/api/vector/links", params={"doc_id": did})
            assert r.json()["links"] == []
            # DELETE du chapitre (le vrai, celui de l'Atelier) → pareil
            r = await c.post("/api/chapters", json={"title": "Chapitre banc p6"})
            chid = r.json()["id"]
            r = await c.post("/api/vector/docs", json={
                "name": "Autre p6", "role": "decor", "doc": _doc()})
            d2 = r.json()["id"]
            await c.post("/api/vector/links",
                         json={"chapter_id": chid, "doc_id": d2})
            r = await c.delete(f"/api/chapters/{chid}")
            assert r.status_code == 200
            r = await c.get("/api/vector/links", params={"chapter_id": chid})
            assert r.json()["links"] == []
            await c.delete(f"/api/vector/docs/{d2}")   # banc propre

    asyncio.run(scenario())


# ── I. la liste par chapitre FUSIONNE propres + liés ; recherche `q` ─────────

def test_la_liste_par_chapitre_fusionne_et_la_recherche_filtre():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # un doc PROPRE au chapitre ch-p6f, un doc de bibliothèque LIÉ,
            # un doc d'un AUTRE chapitre LIÉ (D4 : référence inter-chapitres)
            r = await c.post("/api/vector/docs", json={
                "name": "Fresque propre", "role": "decor",
                "chapter_id": "ch-p6f", "doc": _doc()})
            propre = r.json()["id"]
            r = await c.post("/api/vector/docs", json={
                "name": "Fresque biblio", "role": "decor", "doc": _doc()})
            lie1 = r.json()["id"]
            r = await c.post("/api/vector/docs", json={
                "name": "Fresque voisine", "role": "lumiere",
                "chapter_id": "ch-p6g", "doc": _doc()})
            lie2 = r.json()["id"]
            for did in (lie1, lie2):
                await c.post("/api/vector/links",
                             json={"chapter_id": "ch-p6f", "doc_id": did})
            # la liste du chapitre rend les TROIS, les liés marqués
            r = await c.get("/api/vector/docs",
                            params={"chapter_id": "ch-p6f"})
            docs = {d["id"]: d for d in r.json()["docs"]}
            assert set(docs) == {propre, lie1, lie2}
            assert docs[propre]["liaison"] is False
            assert docs[lie1]["liaison"] is True
            assert docs[lie2]["liaison"] is True
            # le filtre rôle s'applique aussi aux liés
            r = await c.get("/api/vector/docs",
                            params={"chapter_id": "ch-p6f",
                                    "role": "lumiere"})
            assert [d["id"] for d in r.json()["docs"]] == [lie2]
            # tri updated_at desc : réécrire le propre le remonte en tête
            await c.put(f"/api/vector/docs/{propre}",
                        json={"doc": _doc("Fresque propre")})
            r = await c.get("/api/vector/docs",
                            params={"chapter_id": "ch-p6f"})
            assert r.json()["docs"][0]["id"] == propre
            # recherche par nom : insensible à la casse, cumulable
            r = await c.get("/api/vector/docs", params={"q": "fresque"})
            assert {d["name"] for d in r.json()["docs"]} == \
                {"Fresque propre", "Fresque biblio", "Fresque voisine"}
            r = await c.get("/api/vector/docs",
                            params={"q": "FRESQUE", "role": "lumiere"})
            assert [d["name"] for d in r.json()["docs"]] == \
                ["Fresque voisine"]
            r = await c.get("/api/vector/docs",
                            params={"chapter_id": "ch-p6f", "q": "voisine"})
            assert [d["id"] for d in r.json()["docs"]] == [lie2]

    asyncio.run(scenario())


# ── J. dupliquer pour diverger : la copie remplace la référence ──────────────

def test_dupliquer_isole():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # source de bibliothèque : v2 sur disque, vignette, lié à ch-p6d
            r = await c.post("/api/vector/docs", json={
                "name": "Source p6", "role": "decor",
                "doc": _doc("Source p6")})
            src = r.json()["id"]
            await c.put(f"/api/vector/docs/{src}",
                        json={"doc": _doc("Source v2")})
            await c.post(f"/api/vector/docs/{src}/vignette",
                         content=_PNG_MIN,
                         headers={"Content-Type": "image/png"})
            await c.post("/api/vector/links",
                         json={"chapter_id": "ch-p6d", "doc_id": src})
            # dupliquer DANS le chapitre : copie indépendante v1, liaison
            # RETIRÉE (la copie remplace la référence)
            r = await c.post(f"/api/vector/docs/{src}/duplicate",
                             json={"chapter_id": "ch-p6d"})
            assert r.status_code == 200, r.text
            cid = r.json()["id"]
            assert cid != src and r.json()["version"] == 1
            r = await c.get(f"/api/vector/docs/{cid}")
            m, d = r.json()["meta"], r.json()["doc"]
            assert m["chapter_id"] == "ch-p6d" and m["role"] == "decor"
            assert m["version"] == 1
            assert m["name"] == "Source p6 (copie)"
            assert d["nom"] == "Source v2"      # le contenu COURANT du disque
            assert m["vignette"] is True        # vignette héritée
            r = await c.get("/api/vector/links", params={"doc_id": src})
            assert r.json()["links"] == []
            # la divergence est réelle : éditer le source laisse la copie
            await c.put(f"/api/vector/docs/{src}",
                        json={"doc": _doc("Source v3")})
            r = await c.get(f"/api/vector/docs/{cid}")
            assert r.json()["doc"]["nom"] == "Source v2"
            # dupliquer SANS chapitre → copie de bibliothèque, nom sur mesure
            r = await c.post(f"/api/vector/docs/{src}/duplicate",
                             json={"name": "Copie libre p6"})
            cid2 = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{cid2}")
            assert r.json()["meta"]["chapter_id"] is None
            assert r.json()["meta"]["name"] == "Copie libre p6"
            # source inconnue → 404
            r = await c.post("/api/vector/docs/fantome/duplicate", json={})
            assert r.status_code == 404
            for i in (cid, cid2):               # banc propre
                await c.delete(f"/api/vector/docs/{i}")

    asyncio.run(scenario())


# ── K. miroirs de l'éditeur (phase 6) : la vignette naît au Sauver ───────────

def test_le_miroir_editeur_vignette_au_save():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vlab = racine / "frontend" / "vectorlab" / "js"
    exp = (vlab / "mod-export.js").read_text("utf-8")
    # le mini-export : rasteriser à 256 px de grand côté, POST binaire vers
    # la route vignette — jamais par /images/upload
    assert "/vignette" in exp
    assert "VL.vignette" in exp
    assert "256" in exp
    core = (vlab / "core.js").read_text("utf-8")
    # accrochée à sauver(), jamais bloquante : l'échec de vignette ne casse
    # pas une sauvegarde
    assert "VL.vignette" in core
    assert core.index("VL.vignette") > core.index("async function sauver")


# ── L. miroirs de l'Atelier (phase 6) : bibliothèque, instancier, diverger ───

def test_le_miroir_atelier_bibliotheque():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    atelier = racine / "frontend" / "atelier"
    html = (atelier / "index.html").read_text("utf-8")
    js = (atelier / "atelier.js").read_text("utf-8")
    # le tiroir Bibliothèque : bouton d'ouverture, recherche, filtre rôle
    assert "vpBiblio" in html and "Bibliothèque" in html
    assert "vbRecherche" in html and "vbRole" in html
    # instancier = POST /vector/links ; retirer = DELETE ; diverger = duplicate
    assert "/vector/links" in js
    assert "/duplicate" in js
    assert "Instancier" in js
    assert "Dupliquer" in js and "Retirer" in js
    # les lignes montrent la vignette servie par la route dédiée et le badge réf
    assert "/vignette.png" in js
    assert "liaison" in js


# ── N. miroirs de la bibliothèque du Vectorlab (accès menu général) ──────────

def test_le_miroir_bibliotheque_vectorlab():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vlab = racine / "frontend" / "vectorlab"
    html = (vlab / "index.html").read_text("utf-8")
    # la section bibliothèque et le retour ⌂ vivent dans la coquille
    assert 'id="biblio"' in html and 'id="btnBiblio"' in html
    assert 'id="bibRecherche"' in html and 'id="bibRole"' in html
    assert 'id="bibCreer"' in html and 'id="bibNouvTaille"' in html
    bib = (vlab / "js" / "mod-biblio.js").read_text("utf-8")
    # la page interroge la liste, ouvre ?doc=, duplique, supprime (archive)
    assert "/vector/docs" in bib and '"?doc="' in bib
    assert "/duplicate" in bib and '"DELETE"' in bib
    assert "vignette.png?v=" in bib
    core = (vlab / "js" / "core.js").read_text("utf-8")
    # sans ?doc, l'éditeur bascule en mode bibliothèque
    assert "ouvrirBiblio" in core
    css = (vlab / "vectorlab.css").read_text("utf-8")
    # la teinte de catégorie et les popups des selects natifs (patron
    # dropdown-theming : le popup suit color-scheme, pas le CSS du bouton)
    assert "--cat-vectoriel" in css and "color-scheme" in css


# ── P. miroirs de l'éditeur complet (27/08) : unités, couleur, classiques ───

def test_le_miroir_editeur_complet():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vlab = racine / "frontend" / "vectorlab"
    js = lambda n: (vlab / "js" / n).read_text("utf-8")  # noqa: E731
    html = (vlab / "index.html").read_text("utf-8")
    # unités : module pur + règles/cotes branchées + bouton cyclique
    unites = js("mod-unites.js")
    assert "libelle_mesure" in unites and "pxParUnite" in unites
    core = js("core.js")
    assert "mod-unites.js" in core and "btnUnite" in core
    assert 'id="btnUnite"' in html
    # couleur : nuancier (RGB/CMJN naïf/hex/palettes) sur les pastilles
    couleur = js("mod-couleur.js")
    assert "rgbVersCmjn" in couleur and "palette_defaut" in couleur
    assert "ouvrirNuancier" in couleur
    assert "ouvrirNuancier" in js("mod-style.js")
    # cotes vives + outils ligne/mesure
    tools = js("mod-tools.js")
    assert "etiquette" in tools and "trace-ligne" in tools
    assert 'data-outil="ligne"' in html and 'data-outil="mesure"' in html
    # formats à la création ; le vitrail est un MODE replié
    assert 'id="bibNouvFormat"' in html
    assert 'id="vitrailDetails"' in html
    # classiques : les ops pures branchées au panneau
    style = js("mod-style.js")
    assert "op_aligner" in style and "op_distribuer" in style
    assert "op_miroir" in style and "op_rect_rayon" in style
    # le pont cartes crée des documents en mm (la carte est physique)
    face = (racine / "frontend" / "cardforge" / "js"
            / "mod-face.js").read_text("utf-8")
    assert '"mm"' in face and "unites" in face


# ── O. miroirs du pont cartes : l'onglet Vectoriel du panneau face ───────────

def test_le_miroir_pont_cartes_mod_face():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    face = (racine / "frontend" / "cardforge" / "js"
            / "mod-face.js").read_text("utf-8")
    core = (racine / "frontend" / "cardforge" / "js"
            / "core.js").read_text("utf-8")
    # le 4e onglet du panneau P1 et son volet
    assert 'data-tab="vec"' in face and "cf-face-pane-vec" in face
    # les docs du JEU : liste filtrée par deck — PAR LE CORE (28/08). Le
    # pont était né (27/08) avec ses fetch nus : exactement le « fetch
    # libre » que makeApi a retiré, et le pin d'architecture cards
    # (test_cards_type, test_P3_…_AUCUN_RESEAU_NU) a rougi comme son pavé
    # l'avait promis. /api/vector vit hors du sous-préfixe de la pièce
    # (règle 8), donc la voie est le patron CF.images : core.js fige la
    # route, le verbe et la validation du deck (URLSearchParams — jamais de
    # concaténation), la pièce consomme.
    assert "CF.vector.docs(" in face and "CF.vector.create(" in face
    assert "CF.vector.del(" in face
    assert '"/vector/docs?" + ps' in core and "deck_id: did" in core
    assert "/vectorlab/?doc=" in face
    # le chemin RETOUR : l'export 2x du magasin posé en illustration img:,
    # présence vérifiée AVANT la pose par la sonde du CORE — un GET dont le
    # content-type est contrôlé, JAMAIS un HEAD : FastAPI ne route pas HEAD,
    # la requête tombait dans le catch-all SPA qui répond 200 HTML (piège
    # n°7 rejoué, attrapé par la preuve réelle du 27/08). La pièce dit le
    # type qu'elle attend ; cache de session purgé pour qu'un ré-export
    # repeigne.
    assert "poserVec" in face and "_2x.png" in face
    assert "CF.images.probe(" in face and '"image/png"' in face
    assert '"HEAD"' not in face and '"HEAD"' not in core
    assert "no-store" in core
    assert "IMGS.delete" in face
    # lot A (D5) : le pont RETOUR — la face rendue par LE moteur (CF.cardBlob)
    # part au magasin d'images du document par le CORE (CF.vector.image), le
    # document se réécrit par le CORE (CF.vector.update) au format physique
    # du jeu (canvas_px, dpi, repères = bleed_off_px / safe_off_px), la face
    # est un calque image VERROUILLÉ, l'éditeur s'ouvre dessus.
    assert 'id="cf-face-vlab-edit"' in face
    assert "CF.vector.image(" in face and "CF.vector.update(" in face
    assert "CF.cardBlob(" in face and "docFaceVec(" in face
    for cle in ("bleed_off_px", "safe_off_px", "canvas_px", '"fondPerdu"', '"zoneSure"',
                'type: "image"', "verrou: true"):
        assert cle in face, cle
    assert '"/images"' in core and 'update: vectorUpdate' in core and 'image: vectorImage' in core
    assert '"image/png"' in core


# ── M. le pont cartes : deck_id (colonne _auto_migrate) + migration réelle ───

def test_le_pont_cartes_deck_id_et_la_migration():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import (VectorDoc, async_session_factory,
                                          init_db)
        await init_db()                  # migre la base pré-créée à froid
        async with async_session_factory() as s:
            legacy = await s.get(VectorDoc, "vd-legacy")
            assert legacy is not None
            assert legacy.name == "Legacy pré-migration"
            assert legacy.deck_id is None    # colonne née, ligne survivante
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={
                "name": "Décor de carte", "role": "libre",
                "deck_id": "deck_test77", "doc": _doc("Décor de carte")})
            assert r.status_code == 200, r.text
            did = r.json()["id"]
            # la méta porte l'ancre
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["meta"]["deck_id"] == "deck_test77"
            # le filtre ?deck_id= ne rend que les docs du jeu
            await c.post("/api/vector/docs", json={
                "name": "Hors deck", "role": "libre", "doc": _doc("Hors deck")})
            r = await c.get("/api/vector/docs",
                            params={"deck_id": "deck_test77"})
            assert [d["name"] for d in r.json()["docs"]] == ["Décor de carte"]
            # dupliquer ancré au jeu : la copie porte l'ancre
            r = await c.post(f"/api/vector/docs/{did}/duplicate",
                             json={"deck_id": "deck_test77",
                                   "name": "Copie deck"})
            assert r.status_code == 200, r.text
            nid = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{nid}")
            assert r.json()["meta"]["deck_id"] == "deck_test77"
            # banc propre (le doc hors deck reste : il est sans ancre)
            r = await c.get("/api/vector/docs",
                            params={"deck_id": "deck_test77"})
            for d in r.json()["docs"]:
                assert (await c.delete(
                    f"/api/vector/docs/{d['id']}")).status_code == 200

    asyncio.run(scenario())


# ═══════════ POST /api/vector/illustration (handoff Vectorlab Vitrail) ═══
# Le LLM est BOUCHONNÉ par attribut de module (la route lit
# `summarizer._chat_dispatch` au moment de l'appel — aucun réseau, mesuré :
# le bouchon compte ses appels). La réponse du modèle est FILTRÉE serveur :
# seuls des `d` au charset chemin et des fonds #rrggbb passent.


def test_vector_illustration_formes_editables_et_moteur_vise():
    """La route rend des FORMES du vocabulaire du document, et vise le
    moteur ET le modèle demandés (remontées du 07/09/2026)."""
    import asyncio

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.services import vector_illustration as VI

    svg = ('<svg viewBox="0 0 120 100">'
           '<path d="m5 5 h10 v10 z" fill="#1e56c8"/>'
           '<circle cx="50" cy="50" r="20" fill="#c0202f"/>'
           '</svg>')
    vus = []
    v_conf, v_tirer = VI.moteurs_configures, VI.tirer
    VI.moteurs_configures = lambda: ["anthropic", "ollama"]
    VI.tirer = lambda mo, md, p, sy, **k: (vus.append((mo, md)) or svg)
    try:
        async def scenario():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport,
                                   base_url="http://t") as c:
                r = await c.post("/api/vector/illustration",
                                 json={"prompt": "un iris",
                                       "provider": "ollama",
                                       "model": "llama3"})
                assert r.status_code == 200, r.text
                d = r.json()
                # le moteur ET le modèle demandés, sans repli
                assert vus == [("ollama", "llama3")], vus
                assert d["provider"] == "ollama" and d["modele"] == "llama3"
                assert d["viewbox"] == [0.0, 0.0, 120.0, 100.0]
                # des FORMES typées, pas des `paths` bruts : le path relatif
                # est sorti ABSOLU, le cercle est devenu une ellipse
                assert [f["type"] for f in d["formes"]] == ["path", "ellipse"]
                assert d["formes"][0]["d"] == "M 5 5 L 15 5 L 15 15 Z"
                assert d["formes"][1]["rx"] == 20

                # moteur non configuré → 400, AUCUN appel payant
                r = await c.post("/api/vector/illustration",
                                 json={"prompt": "x", "provider": "openai"})
                assert r.status_code == 400 and "openai" in r.json()["detail"]
                assert len(vus) == 1, vus

                # sans prompt → 400 avant tout appel
                r = await c.post("/api/vector/illustration", json={})
                assert r.status_code == 400
                assert len(vus) == 1, vus
        asyncio.run(scenario())
    finally:
        VI.moteurs_configures, VI.tirer = v_conf, v_tirer


def test_vector_illustration_moteurs_liste_les_modeles():
    import asyncio

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.services import vector_illustration as VI

    v_cat = VI.catalogue
    VI.catalogue = lambda **k: [
        {"moteur": "anthropic", "modeles": ["claude-haiku-4-5", "claude-opus-5"],
         "defaut": "claude-haiku-4-5"},
        {"moteur": "ollama", "modeles": ["llama3"], "defaut": "llama3"}]
    try:
        async def scenario():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport,
                                   base_url="http://t") as c:
                r = await c.get("/api/vector/illustration/moteurs")
                assert r.status_code == 200, r.text
                d = r.json()
                assert [m["moteur"] for m in d["moteurs"]] ==                     ["anthropic", "ollama"], d
                # PLUSIEURS modèles par moteur — c'est la remontée
                assert len(d["moteurs"][0]["modeles"]) == 2, d
                assert d["actif"] == "anthropic"
        asyncio.run(scenario())
    finally:
        VI.catalogue = v_cat


def test_vector_illustration_reponse_illisible_et_modele_muet():
    import asyncio

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.services import vector_illustration as VI

    v_conf, v_tirer = VI.moteurs_configures, VI.tirer
    VI.moteurs_configures = lambda: ["anthropic"]
    try:
        async def scenario(attendu, frag):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport,
                                   base_url="http://t") as c:
                r = await c.post("/api/vector/illustration",
                                 json={"prompt": "x"})
                assert r.status_code == attendu, r.text
                assert frag in r.json()["detail"], r.text

        # réponse sans forme exploitable → 400 parlant
        VI.tirer = lambda *a, **k: "voici une explication sans svg"
        asyncio.run(scenario(400, "illisible"))
        # état vide : chaîne vide → même 400, pas de mort
        VI.tirer = lambda *a, **k: ""
        asyncio.run(scenario(400, "illisible"))
        # modèle muet → 502 qui porte la cause
        def _muet(*a, **k):
            raise RuntimeError("Anthropic HTTP 429 — rate limited")
        VI.tirer = _muet
        asyncio.run(scenario(502, "429"))
    finally:
        VI.moteurs_configures, VI.tirer = v_conf, v_tirer


# ── Q. lot A : le magasin d'IMAGES du document (D1 — jamais de base64) ───────

_PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d"
    "4944415478da63f8ffff3f0300050001ff2a5d2b0000000049454e44ae426082")


def test_le_magasin_d_images_du_document():
    import pytest
    from app.services import vector_store as VS
    did = VS.creer(_doc("Avec image"))
    # état vide construit : aucune image, la lecture rend None, la liste []
    assert VS.lister_images(did) == []
    assert VS.lire_image(did, "img1.png") is None
    n1 = VS.ecrire_image(did, _PNG_1PX)
    n2 = VS.ecrire_image(did, _PNG_1PX + b"x")
    assert (n1, n2) == ("img1.png", "img2.png")
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    assert (dossier / f"{did}.img1.png").read_bytes() == _PNG_1PX
    assert VS.lire_image(did, "img2.png") == _PNG_1PX + b"x"
    assert VS.lister_images(did) == ["img1.png", "img2.png"]
    # noms hors patron : refusés sans toucher le disque
    for mauvais in ("../x.png", "img1.jpg", "autre.png", "img.png", ""):
        assert VS.lire_image(did, mauvais) is None
    # la copie (socle de « dupliquer ») emporte les images
    dst = VS.creer(_doc("copie"))
    VS.copier_images(did, dst)
    assert VS.lister_images(dst) == ["img1.png", "img2.png"]
    assert VS.lire_image(dst, "img1.png") == _PNG_1PX
    # un doc sans image : la copie est un no-op silencieux
    vide = VS.creer(_doc("vide"))
    VS.copier_images(vide, dst)
    assert VS.lister_images(dst) == ["img1.png", "img2.png"]
    # document inconnu : refus parlant
    with pytest.raises(FileNotFoundError):
        VS.ecrire_image("inexistant", _PNG_1PX)


def test_les_routes_images_du_document():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={"name": "Img", "role": "libre",
                                                       "doc": _doc()})
            did = r.json()["id"]
            # pas un PNG → 400 ; doc inconnu → 404
            r = await c.post(f"/api/vector/docs/{did}/images", content=b"GIF89a",
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 400 and "PNG" in r.json()["detail"]
            r = await c.post("/api/vector/docs/nope/images", content=_PNG_1PX,
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 404
            # dépôt → nom stable, servi en image/png
            r = await c.post(f"/api/vector/docs/{did}/images", content=_PNG_1PX,
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 200 and r.json() == {"name": "img1.png"}
            r = await c.get(f"/api/vector/docs/{did}/images/img1.png")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("image/png")
            assert r.content == _PNG_1PX
            # nom hors patron ou absent → 404 (jamais le catch-all SPA en 200)
            for mauvais in ("img9.png", "x.png", "img1.PNG", "img1.png.bak"):
                r = await c.get(f"/api/vector/docs/{did}/images/{mauvais}")
                assert r.status_code == 404, mauvais
            # « .. » : le client normalise le chemin AVANT l'envoi et la requête
            # tombe dans le catch-all SPA (200 HTML — piège n°7) : ce qui compte
            # est qu'AUCUN octet d'image ne sorte par cette porte
            r = await c.get(f"/api/vector/docs/{did}/images/..%2Fimg1.png")
            assert not r.headers.get("content-type", "").startswith("image/")
            # le document qui RÉFÉRENCE l'image se sauve et se relit tel quel
            doc = _doc()
            doc["calques"][0]["objets"].append(
                {"id": "o1", "type": "image", "x": 0, "y": 0, "w": 640, "h": 960,
                 "href": "img1.png", "nat": {"w": 1, "h": 1}, "verrou": True})
            doc["reperes"] = {"fondPerdu": [10, 10], "zoneSure": [30, 30]}
            r = await c.put(f"/api/vector/docs/{did}", json={"doc": doc})
            assert r.status_code == 200 and r.json()["version"] == 2
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["doc"]["calques"][0]["objets"][0]["href"] == "img1.png"
            assert r.json()["doc"]["reperes"]["zoneSure"] == [30, 30]
            # dupliquer emporte les images : la copie sert img1.png
            r = await c.post(f"/api/vector/docs/{did}/duplicate", json={})
            nid = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{nid}/images/img1.png")
            assert r.status_code == 200 and r.content == _PNG_1PX
            # supprimer archive le JSON ; les images restent (dit dans le service)
            r = await c.delete(f"/api/vector/docs/{did}")
            assert r.status_code == 200
            from app.services import vector_store as VS
            assert VS.lire_image(did, "img1.png") == _PNG_1PX

    asyncio.run(scenario())


# ── R. lot A : miroir de la surface du Vectorlab (vendor, modules, menus) ────

def test_le_miroir_lot_a_images_et_cartes():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    html = (vl / "index.html").read_text("utf-8")
    core = (vl / "js" / "core.js").read_text("utf-8")
    # le vendor et sa licence — zéro dépendance payante (D7)
    assert (vl / "vendor" / "imagetracer_v1.2.6.js").is_file()
    lic = (vl / "vendor" / "LICENSE-imagetracerjs.txt").read_text("utf-8")
    assert "public domain" in lic.lower()
    assert 'src="vendor/imagetracer_v1.2.6.js"' in html
    # les trois modules, initialisés par le cœur ; le brouillon AVANT charger()
    for m in ("mod-image.js", "mod-trace.js", "mod-brouillon.js"):
        assert (vl / "js" / m).is_file(), m
        assert m in core, m
    assert core.index("initBrouillon(VL)") < core.index("charger();")
    # le rendu passe le résolveur d'href ; l'overlay trace les repères
    assert "compilerSVG(etat.doc, { image: VL.imageUrl, mesure: VL.mesureTexte })" in core   # lot F : la mesure du texte s ajoute
    assert "reperes_rects" in core and 'data-repere' in core
    # les surfaces : menu Image (4 sources + vectoriser), panneaux, dialogues
    for tok in ("imgBiblio", "imgFichier", "imgColler", "imgGenerer", "imgVectoriser",
                "panneauImage", "panneauReperes", "libDlg", "traceDlg"):
        assert f'id="{tok}"' in html, tok
    # le banc node porte les cinq bancs du lot
    qa = vl / "qa"
    for b in ("image", "image_ui", "reperes", "trace", "brouillon"):
        assert (qa / f"{b}.test.mjs").is_file(), b
    # le JSON d'un document ne porte JAMAIS de base64 (D1) : l'export inline,
    # pas le modèle
    exp = (vl / "js" / "mod-export.js").read_text("utf-8")
    assert "readAsDataURL" in exp and "image_hrefs" in exp
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    assert ";base64," not in doc and "data:image" not in doc   # le JETON, pas le mot


# ── S. lot C : grille, terrains, tuiles, planches — aller-retour et surface ──

def test_les_champs_du_lot_c_font_l_aller_retour():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            doc = _doc("Plateau")
            doc["grille"] = {"type": "hex", "pas": 40, "sous": 1, "orientation": "plat",
                             "origine": [320, 480], "echelle": [1, 1]}
            doc["terrains"] = {"lave": {"nom": "Lave", "couleur": "#D33", "hauteur_mm": 1, "motif": ""}}
            doc["planches"] = [{"id": "p1", "nom": "Plateau", "x": 0, "y": 0, "w": 640, "h": 480}]
            doc["calques"][0]["objets"].append({"id": "t1", "type": "tuile", "q": 0, "r": 0, "terrain": "lave"})
            r = await c.post("/api/vector/docs", json={"name": "Plateau", "role": "libre", "doc": doc})
            did = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{did}")
            d = r.json()["doc"]
            assert d["grille"]["orientation"] == "plat" and d["grille"]["origine"] == [320, 480]
            assert d["terrains"]["lave"]["hauteur_mm"] == 1
            assert d["planches"][0]["w"] == 640
            assert d["calques"][0]["objets"][0]["type"] == "tuile"
            # un document SANS ces champs reste intact (rétro-compatibilité)
            r = await c.post("/api/vector/docs", json={"name": "V1", "role": "libre", "doc": _doc()})
            r = await c.get(f"/api/vector/docs/{r.json()['id']}")
            assert "grille" not in r.json()["doc"] and "planches" not in r.json()["doc"]

    asyncio.run(scenario())


def test_le_miroir_lot_c_grilles_plateau_planches():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    html = (vl / "index.html").read_text("utf-8")
    core = (vl / "js" / "core.js").read_text("utf-8")
    for m in ("mod-grille.js", "mod-aimant.js", "mod-plateau.js", "mod-planches.js"):
        assert (vl / "js" / m).is_file(), m
    # les modules géométriques sont des FEUILLES : aucun import (bancables partout)
    for m in ("mod-grille.js", "mod-aimant.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m
    assert "initPlateau(VL)" in core and "initPlanches(VL)" in core
    assert "grille_d(" in core and "aimant_fusion(" in core and "planches_guides(" in core
    for tok in ("panneauGrille", "panneauTerrains", "panneauPlateau", "panneauPlanches",
                "assetsDetails", "assetsGrille", "btnAimant"):
        assert f'id="{tok}"' in html, tok
    assert 'data-outil="tuiles"' in html
    qa = vl / "qa"
    for b in ("grille", "aimant_objets", "tuiles", "planches", "plateau_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    assert "TERRAINS_DEFAUT" in doc and "op_plateau_generer" in doc and "op_tuiles_peindre" in doc
    assert 'case "tuile"' in doc and "opts.cadre" in doc


# ── T. lot D : impression 3D — modules, vendor, surface ─────────────────────

def test_le_miroir_lot_d_impression_3d():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    core = (vl / "js" / "core.js").read_text("utf-8")
    for m in ("mod-solide.js", "mod-texte3d.js", "mod-impression.js"):
        assert (vl / "js" / m).is_file(), m
    assert "initImpression(VL)" in core
    # opentype.js vendorisé sous MIT (D7) ; les polices sont celles du dist
    assert (vl / "vendor" / "opentype.min.js").is_file()
    assert "MIT" in (vl / "vendor" / "LICENSE-opentype.txt").read_text("utf-8")
    t3 = (vl / "js" / "mod-texte3d.js").read_text("utf-8")
    for police in ("Anton.ttf", "Inter.ttf", "Cinzel.ttf"):
        assert police in t3 and (racine / "frontend" / "dist" / "fonts" / police).is_file(), police
    # le modèle : texte → chemin ; le panneau Apparence porte le bouton
    assert "export function op_texte_vectoriser" in (vl / "js" / "mod-doc.js").read_text("utf-8")
    assert 'id="txContours"' in (vl / "js" / "mod-typo.js").read_text("utf-8")   # Texte & logo : la vectorisation vit dans le panneau Texte
    # le mur minimal est une constante nommée, la garde des 256 reste au backend
    sol = (vl / "js" / "mod-solide.js").read_text("utf-8")
    assert "MUR_MIN_MM = 0.8" in sol and "glb_de_triangles" in sol
    assert "def creer_lot" in (racine / "backend" / "app" / "services" / "print3d.py").read_text("utf-8")
    qa = vl / "qa"
    for b in ("solide", "texte3d", "impression_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b


# ── U. lot B : géométrie et gestes de classe Affinity ────────────────────────

def test_le_miroir_lot_b_geometrie_gestes():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    for m in ("mod-formes.js", "mod-crayon.js", "mod-noeuds.js", "mod-outils2.js"):
        assert (vl / "js" / m).is_file(), m
    for m in ("mod-formes.js", "mod-crayon.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m       # feuilles
    core = (vl / "js" / "core.js").read_text("utf-8")
    assert "initOutils2(VL)" in core and "new Historique()" in core
    html = (vl / "index.html").read_text("utf-8")
    for outil in ("forme", "crayon", "couteau", "gomme", "coin", "constructeur"):
        assert f'data-outil="{outil}"' in html, outil
    for tok in ("panneauForme", "panneauNoeuds", "panneauInstantanes"):
        assert f'id="{tok}"' in html, tok
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    for op in ("op_forme_param", "op_forme_en_chemin", "op_incliner", "op_dupliquer_puissance",
               "selection_par_attribut", "formule"):
        assert f"export function {op}" in doc, op
    assert "constructor(cap = 1000)" in doc and "instantane(nom, doc)" in doc
    boolmod = (vl / "js" / "mod-bool.js").read_text("utf-8")
    for op in ("op_couteau", "op_gomme", "op_contour", "atomes", "op_constructeur"):
        assert f"export function {op}" in boolmod, op
    style = (vl / "js" / "mod-style.js").read_text("utf-8")
    assert "formule(" in style and 'id="apIncliner"' in style and 'id="apPuissance"' in style
    assert 'type="text" id="apX"' in style                              # les formules
    tools = (vl / "js" / "mod-tools.js").read_text("utf-8")
    assert "etat.pivot" in tools
    qa = vl / "qa"
    for b in ("formes", "crayon", "noeuds2", "opsbool2", "gestes"):
        assert (qa / f"{b}.test.mjs").is_file(), b


# ── V. lot E : le journal raster du persona Pixel (D1 : `.pix<n>.png` ×10) ──

def test_le_journal_raster_du_document():
    import pytest
    from app.services import vector_store as VS
    did = VS.creer(_doc("Pixel"))
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    # état vide construit : rien à annuler, rien à remplacer
    assert VS.journal_images(did, "img1.png") == 0
    assert VS.annuler_image(did, "img1.png") is None
    with pytest.raises(FileNotFoundError):
        VS.remplacer_image(did, "img1.png", _PNG_1PX)
    VS.ecrire_image(did, _PNG_1PX)
    # remplacer journalise l'état PRÉCÉDENT ; la révision compte les journaux
    assert VS.remplacer_image(did, "img1.png", _PNG_1PX + b"A") == 1
    assert VS.lire_image(did, "img1.png") == _PNG_1PX + b"A"
    assert (dossier / f"{did}.img1.pix1.png").read_bytes() == _PNG_1PX
    for k in range(2, 14):
        VS.remplacer_image(did, "img1.png", _PNG_1PX + bytes([64 + k]))
    # ×10 : les plus anciens sont tombés, le plus récent est pix10
    assert VS.journal_images(did, "img1.png") == 10
    assert not (dossier / f"{did}.img1.pix11.png").exists()
    assert (dossier / f"{did}.img1.pix10.png").read_bytes() == _PNG_1PX + bytes([64 + 12])
    # annuler rend l'état précédent et dépile
    assert VS.annuler_image(did, "img1.png") == 9
    assert VS.lire_image(did, "img1.png") == _PNG_1PX + bytes([64 + 12])
    for _ in range(9):
        VS.annuler_image(did, "img1.png")
    assert VS.journal_images(did, "img1.png") == 0 and VS.annuler_image(did, "img1.png") is None
    # noms hors patron : refusés
    with pytest.raises(ValueError):
        VS.remplacer_image(did, "../img1.png", _PNG_1PX)
    # le journal ne pollue pas la liste des images ni la copie
    assert VS.lister_images(did) == ["img1.png"]
    dst = VS.creer(_doc("copie"))
    VS.remplacer_image(did, "img1.png", _PNG_1PX + b"Z")
    VS.copier_images(did, dst)
    assert VS.lister_images(dst) == ["img1.png"] and VS.journal_images(dst, "img1.png") == 0


def test_les_routes_du_journal_raster():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={"name": "Pix", "role": "libre", "doc": _doc()})
            did = r.json()["id"]
            r = await c.post(f"/api/vector/docs/{did}/images", content=_PNG_1PX,
                             headers={"Content-Type": "image/png"})
            assert r.json() == {"name": "img1.png"}
            # état vide : rien à annuler → 409 parlant ; image inconnue → 404 ; pas un PNG → 400
            r = await c.post(f"/api/vector/docs/{did}/images/img1.png/annuler")
            assert r.status_code == 409
            r = await c.put(f"/api/vector/docs/{did}/images/img7.png", content=_PNG_1PX,
                            headers={"Content-Type": "image/png"})
            assert r.status_code == 404
            r = await c.put(f"/api/vector/docs/{did}/images/img1.png", content=b"GIF89a",
                            headers={"Content-Type": "image/png"})
            assert r.status_code == 400
            # remplacer → rev 1, l'image servie est la nouvelle
            r = await c.put(f"/api/vector/docs/{did}/images/img1.png", content=_PNG_1PX + b"B",
                            headers={"Content-Type": "image/png"})
            assert r.status_code == 200 and r.json() == {"name": "img1.png", "rev": 1}
            r = await c.get(f"/api/vector/docs/{did}/images/img1.png")
            assert r.content == _PNG_1PX + b"B"
            # annuler → rev 0, l'image d'origine revient
            r = await c.post(f"/api/vector/docs/{did}/images/img1.png/annuler")
            assert r.status_code == 200 and r.json() == {"name": "img1.png", "rev": 0}
            r = await c.get(f"/api/vector/docs/{did}/images/img1.png")
            assert r.content == _PNG_1PX
            # le chemin de journal n'est PAS servi comme image
            r = await c.get(f"/api/vector/docs/{did}/images/img1.pix1.png")
            assert r.status_code == 404

    asyncio.run(scenario())


# ── W. lot E : miroir de la surface — personas, persona Pixel, pixel-art ────

def test_le_miroir_lot_e_persona_pixel():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    for m in ("mod-pixel.js", "mod-pixelart.js", "mod-persona.js", "mod-pixelui.js"):
        assert (vl / "js" / m).is_file(), m
    for m in ("mod-pixel.js", "mod-pixelart.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m       # feuilles
    core = (vl / "js" / "core.js").read_text("utf-8")
    assert "initPersona(VL)" in core and "initPixelUI(VL)" in core
    assert core.index("initOutils(VL)") < core.index("initPersona(VL)") < core.index("initPixelUI(VL)") < core.index("initBrouillon(VL)")
    html = (vl / "index.html").read_text("utf-8")
    for tok in ('id="personas"', 'id="panneauPixel"', 'id="panneauExport"'):
        assert tok in html, tok
    css = (vl / "vectorlab.css").read_text("utf-8")
    for tok in ("persona-pixel", "persona-export", ".outil-pixel", "image-rendering: pixelated"):
        assert tok in css, tok
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    for op in ("op_pixelart", "op_image_rev"):
        assert f"export function {op}" in doc, op
    assert "?v=${rev}" in (vl / "js" / "mod-image.js").read_text("utf-8")
    ui = (vl / "js" / "mod-pixelui.js").read_text("utf-8")
    assert '"/api/images/upload"' in ui and "/tilelab/" not in ui.replace("`/${surface}/`", "")   # la cible est calculée
    assert "px-" in ui and "annuler" in ui
    routes = (racine / "backend" / "app" / "api" / "routes.py").read_text("utf-8")
    assert '@router.put("/vector/docs/{doc_id}/images/{name}")' in routes
    assert '@router.post("/vector/docs/{doc_id}/images/{name}/annuler")' in routes
    qa = vl / "qa"
    for b in ("pixel", "pixelart", "pixel_doc", "pixel_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b


# ── X. lot F : miroir de l'apparence avancée (effets, motifs, symboles, texte +) ──

def test_le_miroir_lot_f_apparence_avancee():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    for m in ("mod-effets.js", "mod-texteplus.js", "mod-pinceauvec.js", "mod-apparence2.js"):
        assert (vl / "js" / m).is_file(), m
    for m in ("mod-effets.js", "mod-texteplus.js", "mod-pinceauvec.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m       # feuilles
    core = (vl / "js" / "core.js").read_text("utf-8")
    assert "initApparence2(VL)" in core and 'j: "pinceauv"' in core and "mesure: VL.mesureTexte" in core
    assert core.index("initOutils(VL)") < core.index("initApparence2(VL)") < core.index("initBrouillon(VL)")
    html = (vl / "index.html").read_text("utf-8")
    assert 'id="panneauApparence2"' in html and 'id="apparence2Details"' in html
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    for op in ("op_motif_creer", "op_degrade_transparence", "op_couleur_globale_definir", "op_couleur_globale_supprimer",
               "op_ecreter", "op_desecreter", "op_style_definir", "op_style_appliquer", "op_symbole_creer",
               "op_instance_poser", "op_symbole_detacher", "op_texte_en_cadre", "op_texte_sur_chemin"):
        assert f"export function {op}" in doc, op
    assert '"conique"' in doc and "mix-blend-mode" in doc and "<clipPath id=" in doc and "<mask id=" in doc and '<use${t}' in doc
    effets = (vl / "js" / "mod-effets.js").read_text("utf-8")
    assert "feSpecularLighting" in effets and "MODES_FUSION" in effets and "<pattern" in effets
    assert "export function palette_harmonique" in (vl / "js" / "mod-couleur.js").read_text("utf-8")
    assert "mesure: VL.mesureTexte" in (vl / "js" / "mod-export.js").read_text("utf-8")
    qa = vl / "qa"
    for b in ("effets", "apparence2", "harmonie", "symboles", "texteplus", "pinceauvec", "apparence2_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b


def test_les_champs_du_lot_f_font_l_aller_retour():
    """Un document avec effets, motif, couleurs globales, styles, symbole +
    instance, cadre et texte sur chemin se sauve et se relit tel quel."""
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            doc = _doc()
            doc["motifs"] = {"m1": {"type": "hachures", "pas": 8, "angle": 45, "epaisseur": 1, "couleur": "#1F1512"}}
            doc["couleursGlobales"] = {"marque": "#12AB34"}
            doc["styles"] = {"cerne": {"fond": "#FF0000", "effets": [{"type": "ombre"}]}}
            doc["symboles"] = {"s1": {"nom": "pion", "bbox": {"x": 0, "y": 0, "w": 10, "h": 10},
                                      "objets": [{"id": "q", "type": "rect", "x": 0, "y": 0, "w": 10, "h": 10, "style": {}}]}}
            doc["calques"][0]["objets"] += [
                {"id": "r1", "type": "rect", "x": 0, "y": 0, "w": 50, "h": 20,
                 "style": {"fond": "motif:m1", "contour": "glob:marque", "epaisseur": 2, "fusion": "multiply",
                           "effets": [{"type": "lueur", "flou": 3}], "contours": [{"couleur": "#0000FF", "epaisseur": 6}]}},
                {"id": "i1", "type": "instance", "symbole": "s1", "x": 20, "y": 20, "sx": 1, "sy": 1, "style": {}},
                {"id": "k1", "type": "cadre", "x": 0, "y": 40, "w": 100, "h": 40, "contenu": "un deux trois", "style": {"corps": 10, "aligner": "justifie"}},
                {"id": "t2", "type": "textechemin", "d": "M 0 0 L 100 0", "contenu": "suivre", "decalage": 25, "style": {}},
            ]
            r = await c.post("/api/vector/docs", json={"name": "F", "role": "libre", "doc": doc})
            assert r.status_code == 200, r.text
            did = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{did}")
            relu = r.json()["doc"]
            assert relu["motifs"]["m1"]["pas"] == 8 and relu["couleursGlobales"]["marque"] == "#12AB34"
            assert relu["styles"]["cerne"]["effets"][0]["type"] == "ombre"
            assert relu["symboles"]["s1"]["objets"][0]["id"] == "q"
            objs = {o["id"]: o for o in relu["calques"][0]["objets"]}
            assert objs["r1"]["style"]["fusion"] == "multiply" and objs["r1"]["style"]["contours"][0]["epaisseur"] == 6
            assert objs["i1"]["symbole"] == "s1" and objs["k1"]["style"]["aligner"] == "justifie" and objs["t2"]["decalage"] == 25

    asyncio.run(scenario())


# ── Y. lot G : le PDF d'impression (stdlib, une image JPEG par page) ───────

# le plus petit JPEG valide : 1×1 gris (SOI … EOI)
_JPEG_1PX = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432"
    "ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9fa"
    "ffda0008010100003f00fbd3ffd9")


def test_le_pdf_d_impression_stdlib():
    import pytest, re
    from app.services import pdf_service as PDF
    pdf = PDF.creer_pdf([{"w_mm": 63.5, "h_mm": 88.9, "jpeg": _JPEG_1PX, "w_px": 1, "h_px": 1},
                         {"w_mm": 210, "h_mm": 297, "jpeg": _JPEG_1PX, "w_px": 1, "h_px": 1}])
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert pdf.count(b"/Type /Page\n") == 2 or pdf.count(b"/Type /Page ") == 2 or len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 2
    # la page en POINTS depuis les mm : 63,5 mm = 180 pt, 88,9 mm = 252 pt ; A4 = 595.28 × 841.89
    assert b"/MediaBox [0 0 180 252]" in pdf and b"/MediaBox [0 0 595.28 841.89]" in pdf
    # l'image : XObject JPEG (DCTDecode) aux dimensions pixel, dessinée pleine page
    assert pdf.count(b"/Filter /DCTDecode") == 2 and b"/Width 1 /Height 1" in pdf
    assert b"180 0 0 252 0 0 cm" in pdf and b"/Im0 Do" in pdf
    # xref : autant d'entrées que d'objets + 1, startxref pointe sur « xref »
    m = re.search(rb"startxref\n(\d+)\n%%EOF", pdf)
    assert m and pdf[int(m.group(1)):].startswith(b"xref")
    n_obj = len(re.findall(rb"\n(\d+) 0 obj", pdf))
    assert re.search(rb"xref\n0 " + str(n_obj + 1).encode() + rb"\n", pdf)
    # états vides : sans page, jpeg qui n'en est pas un, taille nulle
    with pytest.raises(ValueError):
        PDF.creer_pdf([])
    with pytest.raises(ValueError):
        PDF.creer_pdf([{"w_mm": 10, "h_mm": 10, "jpeg": b"PNG", "w_px": 1, "h_px": 1}])
    with pytest.raises(ValueError):
        PDF.creer_pdf([{"w_mm": 0, "h_mm": 10, "jpeg": _JPEG_1PX, "w_px": 1, "h_px": 1}])


def test_la_route_pdf_du_document():
    import asyncio, json
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={"name": "Pdf", "role": "libre", "doc": _doc()})
            did = r.json()["id"]
            pages = [{"w_mm": 63.5, "h_mm": 88.9, "w_px": 1, "h_px": 1}]
            fichiers = [("pages_fichiers", ("page0.jpg", _JPEG_1PX, "image/jpeg"))]
            # doc inconnu → 404 ; sans fichier → 400
            r = await c.post("/api/vector/docs/nope/pdf", data={"pages": json.dumps(pages)}, files=fichiers)
            assert r.status_code == 404
            r = await c.post(f"/api/vector/docs/{did}/pdf", data={"pages": json.dumps(pages)})
            assert r.status_code == 400
            r = await c.post(f"/api/vector/docs/{did}/pdf", data={"pages": json.dumps(pages)}, files=fichiers)
            assert r.status_code == 200, r.text
            assert r.headers["content-type"].startswith("application/pdf")
            assert r.content.startswith(b"%PDF-1.4") and b"/MediaBox [0 0 180 252]" in r.content
            assert "attachment" in r.headers.get("content-disposition", "") and ".pdf" in r.headers.get("content-disposition", "")

    asyncio.run(scenario())


# ── Z. lot G : miroir du persona Export ──────────────────────────────────

def test_le_miroir_lot_g_persona_export():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    for m in ("mod-tranches.js", "mod-dxf.js", "mod-exportplus.js"):
        assert (vl / "js" / m).is_file(), m
    for m in ("mod-tranches.js", "mod-dxf.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m       # feuilles
    core = (vl / "js" / "core.js").read_text("utf-8")
    assert "initExportPlus(VL)" in core
    assert core.index("initPersona(VL)") < core.index("initExportPlus(VL)") < core.index("initBrouillon(VL)")
    assert "VL.svgCourant = svgCourant" in (vl / "js" / "mod-export.js").read_text("utf-8")
    html = (vl / "index.html").read_text("utf-8")
    assert 'id="panneauExportPlus"' in html
    css = (vl / "vectorlab.css").read_text("utf-8")
    assert ".outil-export" in css
    ui = (vl / "js" / "mod-exportplus.js").read_text("utf-8")
    assert '"/api/images/upload"' in ui and "/pdf`" in ui and "aplatir_objet" in ui
    tr = (vl / "js" / "mod-tranches.js").read_text("utf-8")
    assert "@${k}x" in tr and "marques_svg" in tr
    assert (racine / "backend" / "app" / "services" / "pdf_service.py").is_file()
    assert '@router.post("/vector/docs/{doc_id}/pdf")' in (racine / "backend" / "app" / "api" / "routes.py").read_text("utf-8")
    qa = vl / "qa"
    for b in ("tranches", "dxf", "exportplus_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b


# ── AA. Texte & logo : la bibliothèque de polices déposées (DATA_ROOT/fonts) ──

_TTF_MIN = b"\x00\x01\x00\x00" + b"\x00" * 60


def test_le_magasin_des_polices_deposees(tmp_path, monkeypatch):
    import pytest
    from app.services import fonts_service as FS
    monkeypatch.setattr(FS, "DOSSIER", tmp_path / "fonts")
    # état vide : aucune police, la lecture rend None
    assert FS.lister() == []
    assert FS.lire("MaTypo.ttf") is None
    nom = FS.deposer("Ma Typo.ttf", _TTF_MIN)
    assert nom == "Ma-Typo.ttf" and (tmp_path / "fonts" / "Ma-Typo.ttf").read_bytes() == _TTF_MIN
    assert FS.lister() == [{"nom": "Ma-Typo.ttf", "famille": "Ma-Typo"}]
    assert FS.lire("Ma-Typo.ttf") == _TTF_MIN
    # OTF / WOFF / WOFF2 acceptés par leur magic ; PNG, extension inconnue, nom hors patron refusés
    assert FS.deposer("b.otf", b"OTTO" + b"\x00" * 40).endswith(".otf")
    assert FS.deposer("c.woff", b"wOFF" + b"\x00" * 40) == "c.woff"
    assert FS.deposer("d.woff2", b"wOF2" + b"\x00" * 40) == "d.woff2"
    for mauvais, octets in (("e.png", _TTF_MIN), ("f.ttf", b"\x89PNG" + b"\x00" * 40), ("../g.ttf", _TTF_MIN), ("h.ttf", b"")):
        with pytest.raises(ValueError):
            FS.deposer(mauvais, octets)
    assert FS.lire("../Ma-Typo.ttf") is None and FS.lire("zz.ttf") is None


def test_les_routes_des_polices(tmp_path, monkeypatch):
    import asyncio
    from httpx import AsyncClient, ASGITransport
    from app.services import fonts_service as FS
    monkeypatch.setattr(FS, "DOSSIER", tmp_path / "fonts")

    async def scenario():
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/api/fonts")
            assert r.status_code == 200
            d = r.json()
            # la bibliothèque du dist (OFL) est listée avec sa source, les déposées à part
            assert any(p["fichier"] == "Anton.ttf" and p["source"] == "lib" for p in d["lib"])
            assert d["user"] == []
            r = await c.post("/api/fonts/upload", files={"file": ("Ma Typo.ttf", _TTF_MIN, "font/ttf")})
            assert r.status_code == 200 and r.json() == {"nom": "Ma-Typo.ttf", "famille": "Ma-Typo"}
            r = await c.post("/api/fonts/upload", files={"file": ("x.ttf", b"\x89PNG" + b"\x00" * 40, "font/ttf")})
            assert r.status_code == 400
            r = await c.get("/api/fonts/user/Ma-Typo.ttf")
            assert r.status_code == 200 and r.content == _TTF_MIN and r.headers["content-type"].startswith("font/")
            r = await c.get("/api/fonts/user/zz.ttf")
            assert r.status_code == 404
            r = await c.get("/api/fonts")
            assert r.json()["user"] == [{"nom": "Ma-Typo.ttf", "famille": "Ma-Typo"}]

    asyncio.run(scenario())
