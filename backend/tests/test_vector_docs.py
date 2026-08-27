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
