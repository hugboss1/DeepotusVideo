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
