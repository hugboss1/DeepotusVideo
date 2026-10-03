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
import json
from pathlib import Path

from loguru import logger

from app.config import settings

# slug stable → libellé UI (servi par GET /api/images ; le front n'invente
# rien). L'ordre est celui des chips.
SOURCES: dict[str, str] = {
    "generation": "Générateur",
    "retouche": "Retouche",
    "matieres": "Matières",
    "atelier": "Atelier",
    "cardforge": "Cardforge",
    "vectorlab": "Vectorlab",
    "figma": "Figma",
    "news": "News",
    "sprites": "Sprite Lab",
    "assets3d": "Game Assets 3D",
    "templates": "Templates",       # plan-templates T5 (tâche #75) : images fixes exportées d'un gabarit
    "import": "Imports",
    "import_url": "Import URL",
    "mobile": "Compagnon mobile",   # plan mobile T12 (tâche #58) : images déposées par le téléphone
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
    ("tpl_still_", "templates"),
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
            # TOUTES les colonnes sauf la clé (03/10/2026) : la liste figée
            # d'avant aurait perdu tags, favori et note au premier renommage,
            # et chaque colonne future avec eux.
            for col in LibraryAsset.__table__.columns.keys():
                if col != "filename":
                    setattr(neuf, col, getattr(row, col))
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


# Bibliothèque #77 (03/10/2026, plan-library T0-T1) — le DAM : tags, favori,
# note 0..5 (deux notions distinctes, décision de l'utilisateur), et les
# colonnes que les tâches suivantes du plan rempliront (lignée, droits,
# empreinte, couleur). `carte()` rend un dict par fichier.
_CHAMPS = ("source", "origin", "kind", "tags", "fav", "note",
           "parent_filename", "relation", "licence", "auteur", "source_url",
           "sha256", "taille_o", "couleur", "teinte",
           "job_id", "deck_id", "doc_id")

_CHAMPS_EDITABLES = ("tags", "fav", "note", "licence", "auteur",
                     "source_url", "parent_filename", "relation")


def tags_lus(brut) -> list[str]:
    """`tags` est du JSON en base. Une valeur abîmée rend [] sans lever :
    l'index est un à-côté, il ne casse jamais la route qui le lit."""
    if not brut:
        return []
    try:
        v = json.loads(brut) if isinstance(brut, str) else brut
    except Exception:  # noqa: BLE001
        return []
    return [str(t) for t in v if str(t).strip()] if isinstance(v, list) else []


def tags_ecrits(tags) -> str:
    """Normalise : minuscules, espaces réduits, dédoublonné, ordre d'arrivée,
    32 caractères par tag, 24 tags. UNE seule plume d'écriture, donc une seule
    forme en base — c'est ce qui rend le filtre exact."""
    vus, out = set(), []
    for t in (tags or []):
        s = " ".join(str(t).split()).strip().lower()[:32]
        if s and s not in vus:
            vus.add(s)
            out.append(s)
    return json.dumps(out[:24], ensure_ascii=False)


def du_magasin(filename: str) -> str | None:
    """Le `kind` du fichier s'il est VRAIMENT dans le magasin (images ou
    audio), sinon None — l'index ne porte pas de ligne pour un fichier
    absent (le plan en créait une : 404 côté route)."""
    nom = Path(str(filename or "")).name
    if not nom or nom in (".", ".."):
        return None
    if (settings.images_path / nom).is_file():
        return "image"
    if (settings.images_path.parent / "audio" / nom).is_file():
        return "audio"
    return None


def _etat(row) -> dict:
    return {"filename": row.filename, "tags": tags_lus(row.tags),
            "fav": bool(row.fav), "note": int(row.note or 0),
            "licence": row.licence, "auteur": row.auteur,
            "source_url": row.source_url,
            "parent_filename": row.parent_filename, "relation": row.relation}


async def editer(filename: str, champs: dict) -> dict:
    """Écrit les champs éditables (déjà validés par la route), en CRÉANT la
    ligne si le fichier est au magasin mais pas encore indexé —
    `reconcilier()` ne tourne qu'au boot, et l'on ne fait pas attendre un
    redémarrage à qui étoile une image. Rend l'état RELU. L'appelant
    vérifie la présence du fichier (`du_magasin`)."""
    from app.services.storage import LibraryAsset, async_session_factory
    nom = Path(str(filename)).name
    async with async_session_factory() as session:
        row = await session.get(LibraryAsset, nom)
        if row is None:
            kind = du_magasin(nom) or "image"
            row = LibraryAsset(filename=nom, kind=kind, origin="heuristique",
                               source=(heuristique(nom) if kind == "image"
                                       else "inconnu"))
            session.add(row)
        if "tags" in champs:
            row.tags = tags_ecrits(champs["tags"])
        if "fav" in champs:
            row.fav = 1 if champs["fav"] else 0
        if "note" in champs:
            row.note = int(champs["note"])
        for c in ("licence", "auteur", "source_url", "parent_filename",
                  "relation"):
            if c in champs:
                v = champs[c]
                setattr(row, c, (str(v)[:255] if v not in (None, "") else None))
        await session.commit()
        await session.refresh(row)
        return _etat(row)


async def facettes() -> dict:
    """Ce qui existe VRAIMENT dans l'index — le front n'invente aucune valeur
    de filtre, et une facette vide n'est pas une rangée de chips."""
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory
    tags: dict[str, int] = {}
    teintes: dict[str, int] = {}
    notes: dict[str, int] = {}
    favoris = 0
    async with async_session_factory() as session:
        res = await session.execute(select(
            LibraryAsset.tags, LibraryAsset.teinte, LibraryAsset.note,
            LibraryAsset.fav))
        for brut, teinte, note, fav in res.fetchall():
            for t in tags_lus(brut):
                tags[t] = tags.get(t, 0) + 1
            if teinte:
                teintes[teinte] = teintes.get(teinte, 0) + 1
            if note:
                notes[str(int(note))] = notes.get(str(int(note)), 0) + 1
            if fav:
                favoris += 1

    def ordonne(d):
        return [{"valeur": k, "n": v} for k, v in
                sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))]

    return {"tags": ordonne(tags), "teintes": ordonne(teintes),
            "notes": notes, "favoris": favoris}


async def carte() -> dict[str, dict]:
    """{filename: {champ: valeur}} en UNE requête — pour list_images. Rendait
    `(source, origin)` jusqu'au 03/10/2026 ; un dict, parce que l'unique
    appelant devrait sinon apprendre une position de tuple de plus à chaque
    colonne neuve."""
    try:
        from sqlalchemy import select
        from app.services.storage import LibraryAsset, async_session_factory
        cols = [getattr(LibraryAsset, c) for c in _CHAMPS]
        async with async_session_factory() as session:
            res = await session.execute(select(LibraryAsset.filename, *cols))
            return {r[0]: dict(zip(_CHAMPS, r[1:])) for r in res.fetchall()}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_index.carte ignorée: {e}")
        return {}
