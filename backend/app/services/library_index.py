# -*- coding: utf-8 -*-
"""Index de provenance de la Bibliothèque (plan
2026-08-28-bibliotheque-provenance-envoyer-vers, chantier A).

`library_assets` porte, par FICHIER de la Bibliothèque, la FONCTION
productrice (`source`), la façon dont on le sait (`origin` : ``depot`` =
enregistré au moment de l'écriture par le producteur ; ``heuristique`` =
déduit du nom après coup — l'UI le dit tel quel), et les liens utiles
(job/deck/doc). Le filename canonique RESTE l'identifiant de tout le
dépôt (décision D5) : la table ajoute la provenance, elle ne remplace
aucune ancre. Les hooks ne cassent JAMAIS la route qui les appelle.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from app.config import settings

# slug stable → libellé UI (servi par GET /api/images ; le front n'invente
# rien). L'ordre est celui des chips.
SOURCES: dict[str, str] = {
    "generation": "Générateur d'images",
    "retouche": "Retouche",
    "matieres": "Material Forge",
    "atelier": "Atelier",
    "cardforge": "Cardforge",
    "vectorlab": "Vectorlab",
    "figma": "Figma",
    "news": "News",
    "sprites": "Sprite Lab",
    "assets3d": "Game Assets 3D",
    "import": "Import fichier",
    "import_url": "Import URL",
    "inconnu": "Inconnu",
}

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# préfixes mesurés dans le code (plan, inventaire) — gen_sprite_ AVANT gen_
_PREFIXES: list[tuple[str, str]] = [
    ("gen_sprite_", "sprites"),
    ("vector_", "vectorlab"),
    ("figma_", "figma"),
    ("news_", "news"),
    ("board_", "atelier"),
    ("shot_", "assets3d"),
    ("gen_", "generation"),
]


def heuristique(filename: str) -> str:
    """Source déduite du NOM seul — honnête : `gen_` est ambigu entre
    plusieurs fonctions (générateur, retouche, matières, planches,
    cardforge…), on rend la plus probable ; tout le reste est inconnu."""
    nom = str(filename or "")
    for prefixe, source in _PREFIXES:
        if nom.startswith(prefixe):
            return source
    return "inconnu"


async def noter(files, source: str, kind: str = "image",
                job_id: str | None = None, deck_id: str | None = None,
                doc_id: str | None = None) -> None:
    """Upsert d'index au DÉPÔT (origin=depot). Résilient : une panne
    d'index ne doit jamais faire échouer l'écriture du fichier."""
    if not files:
        return
    if source not in SOURCES:
        source = "inconnu"
    try:
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as session:
            for name in files:
                nom = Path(str(name)).name
                if not nom:
                    continue
                row = await session.get(LibraryAsset, nom)
                if row is None:
                    row = LibraryAsset(filename=nom)
                    session.add(row)
                row.source = source
                row.kind = kind
                row.origin = "depot"
                if job_id is not None:
                    row.job_id = job_id
                if deck_id is not None:
                    row.deck_id = deck_id
                if doc_id is not None:
                    row.doc_id = doc_id
            await session.commit()
    except Exception as e:  # noqa: BLE001 — l'index est un à-côté
        logger.warning(f"library_index.noter({source}) ignoré: {e}")


def noter_bg(files, source: str, **kw) -> None:
    """Variante pour les sites synchrones DANS la boucle (helpers appelés
    par une route async). Hors boucle (thread) : no-op silencieux — la
    réconciliation au boot rattrape par préfixe."""
    try:
        asyncio.get_running_loop().create_task(noter(files, source, **kw))
    except RuntimeError:
        pass


async def retirer(filename: str) -> None:
    """Le fichier supprimé quitte l'index."""
    try:
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as session:
            row = await session.get(LibraryAsset, Path(str(filename)).name)
            if row is not None:
                await session.delete(row)
                await session.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_index.retirer ignoré: {e}")


async def renommer(ancien: str, nouveau: str) -> None:
    """Le rename (file-only) migre la ligne d'index — la provenance suit
    le fichier, le préfixe perdu n'efface plus rien."""
    try:
        from app.services.storage import LibraryAsset, async_session_factory
        a, n = Path(str(ancien)).name, Path(str(nouveau)).name
        if not a or not n or a == n:
            return
        async with async_session_factory() as session:
            row = await session.get(LibraryAsset, a)
            if row is None:
                return
            neuf = await session.get(LibraryAsset, n)
            if neuf is None:
                neuf = LibraryAsset(filename=n)
                session.add(neuf)
            neuf.source, neuf.kind = row.source, row.kind
            neuf.origin = row.origin
            neuf.job_id, neuf.deck_id, neuf.doc_id = \
                row.job_id, row.deck_id, row.doc_id
            neuf.created = row.created
            await session.delete(row)
            await session.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_index.renommer ignoré: {e}")


async def reconcilier() -> int:
    """Rétro-remplissage UNE-FOIS des existants + filet permanent (boot) :
    tout fichier du magasin absent de l'index y entre par heuristique de
    nom, en le DISANT (origin=heuristique). Idempotent ; rend le nombre
    de lignes ajoutées. Rattrape aussi les écritures hors boucle (ex.
    vignettes news téléchargées en thread)."""
    try:
        from sqlalchemy import select
        from app.services.storage import LibraryAsset, async_session_factory
        dossiers: list[tuple[Path, str]] = [(settings.images_path, "image")]
        audio = settings.images_path.parent / "audio"
        if audio.is_dir():
            dossiers.append((audio, "audio"))
        ajout = 0
        async with async_session_factory() as session:
            res = await session.execute(select(LibraryAsset.filename))
            connus = {r[0] for r in res.fetchall()}
            for dossier, kind in dossiers:
                if not dossier.is_dir():
                    continue
                for p in sorted(dossier.iterdir()):
                    if not p.is_file() or p.name in connus:
                        continue
                    if kind == "image" and p.suffix.lower() not in _IMAGE_EXTS:
                        continue
                    session.add(LibraryAsset(
                        filename=p.name, kind=kind,
                        source=(heuristique(p.name) if kind == "image"
                                else "inconnu"),
                        origin="heuristique"))
                    connus.add(p.name)
                    ajout += 1
            if ajout:
                await session.commit()
        if ajout:
            logger.info(f"library_index: {ajout} asset(s) rétro-indexés "
                        "(heuristique)")
        return ajout
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_index.reconcilier ignoré: {e}")
        return 0


async def carte() -> dict[str, tuple[str, str]]:
    """{filename: (source, origin)} en UNE requête — pour list_images."""
    try:
        from sqlalchemy import select
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as session:
            res = await session.execute(
                select(LibraryAsset.filename, LibraryAsset.source,
                       LibraryAsset.origin))
            return {r[0]: (r[1], r[2]) for r in res.fetchall()}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_index.carte ignorée: {e}")
        return {}
