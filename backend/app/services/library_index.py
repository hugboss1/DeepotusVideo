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
    "tuiles": "Tile Lab",           # t113 (plan-tuiles T2) : les atlas des jeux de tuiles
    "assets3d": "Game Assets 3D",
    "templates": "Templates",       # plan-templates T5 (tâche #75) : images fixes exportées d'un gabarit
    "import": "Imports",
    "import_url": "Import URL",
    "sonvfx": "Son & VFX",                 # T099 : ce que la catégorie Son & VFX écrit (stems, isolations…)
    "mobile": "Compagnon mobile",   # plan mobile T12 (tâche #58) : images déposées par le téléphone
    "plateau": "Plateau 3D",        # t127 (07/10/2026) : les cadres de début et de fin capturés au Plateau
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
    ("tile_", "tuiles"),            # t113 : tile_<id>_atlas.png
    ("plateau_", "plateau"),        # t127 : plateau_<scène>_debut|fin_<n>.png
    ("gen_", "generation"),
]


# Tâche #80 (décision 03/10/2026) : la licence PAR DÉFAUT, par source. Ce que
# l'app PRODUIT est « propriétaire » ; ce qui ENTRE de dehors (imports, URL,
# news, Figma, téléphone, inconnu) est « inconnue » — l'écran l'alerte ; les
# particules du catalogue de démarrage (Kenney) sont CC0. Une licence posée
# n'est JAMAIS écrasée : seules les lignes à NULL reçoivent ce défaut.
SOURCES_PROPRES = {"generation", "retouche", "matieres", "atelier", "cardforge",
                   "vectorlab", "sprites", "assets3d", "templates", "tuiles", "plateau"}
LICENCE_PROPRE, LICENCE_INCONNUE = "propriétaire", "inconnue"


def licence_defaut(filename: str, source: str | None) -> str:
    if Path(str(filename or "")).name.startswith("particule_"):
        return "CC0"
    return LICENCE_PROPRE if source in SOURCES_PROPRES else LICENCE_INCONNUE


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
                doc_id: str | None = None, parent: str | None = None,
                relation: str | None = None, recette: dict | None = None) -> None:
    """Upsert d'index au DÉPÔT (origin=depot). Résilient : une panne
    d'index ne doit jamais faire échouer l'écriture du fichier.
    Tâche #79 (03/10/2026, plan-library T5) : `parent` / `relation` — la
    MÈRE du fichier et ce qui l'en a tiré (crop, upscale, vue_3d, sprite…).
    Nommés : les appelants qui ne les donnent pas ne changent pas."""
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
                if parent is not None:
                    mere = Path(str(parent)).name
                    # Une image ne descend pas d'elle-même : une opération qui
                    # réécrit EN PLACE rendrait le même nom, et la remontée
                    # tournerait en rond dès la première lecture.
                    row.parent_filename = mere[:255] if mere and mere != nom else None
                if relation is not None:
                    row.relation = str(relation)[:24] or None
                if recette is not None:   # tâche #80 : la recette du tir (JSON)
                    row.recette = json.dumps(recette, ensure_ascii=False)
                if row.licence is None:   # tâche #80 : le défaut par source, jamais par-dessus une saisie
                    row.licence = licence_defaut(nom, source)
            await session.commit()
    except Exception as e:  # noqa: BLE001 — l'index est un à-côté
        logger.warning(f"library_index.noter({source}) ignoré: {e}")
    # Bibliothèque #78 (03/10/2026) : ce qui est produit pendant qu'un projet
    # est actif y entre. UN seul site, parce que tous les producteurs de
    # fichiers passent par ici (les jobs : library_projects.installer).
    from app.services import library_projects as _LP
    await _LP.ranger_dans_actif([Path(str(n)).name for n in files if Path(str(n)).name],
                                "audio" if kind == "audio" else "image")
    if kind == "image":   # tâche #81 : la couleur dominante de chaque nouvelle image, en tâche de fond
        from app.services import library_couleur as _LCOL
        _LCOL.en_fond([Path(str(n)).name for n in files if Path(str(n)).name])


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
    from app.services import library_projects as _LP  # #78 : il quitte ses projets
    await _LP.oublier_ref(Path(str(filename)).name)


async def renommer(ancien: str, nouveau: str) -> None:
    """Le rename (file-only) migre la ligne d'index — la provenance suit
    le fichier, le préfixe perdu n'efface plus rien — puis ses projets
    (#78), MÊME sans ligne d'index (un fichier jamais indexé peut être rangé)."""
    await _renommer_index(ancien, nouveau)
    a2, n2 = Path(str(ancien or "")).name, Path(str(nouveau or "")).name
    if a2 and n2 and a2 != n2:
        from app.services import library_projects as _LP
        await _LP.renommer_ref(a2, n2)
        from app.services import library_commentaires as _LCM   # tâche #82 : les commentaires suivent le fichier
        await _LCM.renommer_ref(a2, n2)


async def _renommer_index(ancien: str, nouveau: str) -> None:
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
                    if kind == "audio" and (p.name.startswith("_") or p.suffix.lower() in (".json", ".part")):
                        continue   # tâche #81 : le sidecar _sfx_meta.json n'est pas un son
                    src = heuristique(p.name) if kind == "image" else "inconnu"
                    session.add(LibraryAsset(
                        filename=p.name, kind=kind, source=src,
                        origin="heuristique"))   # tâche #80 : la licence vient du rétro-remplissage ci-dessous
                    connus.add(p.name)
                    ajout += 1
            # Tâche #81 : le sidecar des sons avait été indexé COMME un son — on l'en retire.
            from sqlalchemy import delete as _del
            r_side = await session.execute(_del(LibraryAsset).where(LibraryAsset.kind == "audio",
                                                                  LibraryAsset.filename.like("\\_%", escape="\\")))
            if r_side.rowcount:
                await session.commit()
            # Tâche #80 (décision 03/10) : RÉTRO-REMPLISSAGE de la licence des lignes existantes — NULL seulement,
            # une licence saisie n'est jamais touchée. Idempotent (à chaque boot, plus rien à faire).
            res = await session.execute(select(LibraryAsset).where(LibraryAsset.licence.is_(None)))
            remplies = 0
            for row in res.scalars().all():
                row.licence = licence_defaut(row.filename, row.source)
                remplies += 1
            if ajout or remplies:
                await session.commit()
            if remplies:
                logger.info(f"library_index: licence par défaut posée sur {remplies} asset(s)")
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
            src = heuristique(nom) if kind == "image" else "inconnu"
            row = LibraryAsset(filename=nom, kind=kind, origin="heuristique",
                               source=src, licence=licence_defaut(nom, src))   # tâche #80
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


LIGNEE_PAS = 32      # remontée : au-delà, une chaîne est une donnée abîmée
LIGNEE_MAX = 500     # descente : un arbre plus grand est rendu TRONQUÉ (et dit)


async def lignee(filename: str) -> dict | None:
    """Tâche #79 (plan-library T5) : l'arbre d'un fichier. On REMONTE jusqu'à
    la racine (bornée, `cycle: true` si l'on retombe sur un nom déjà vu — un
    `parent_filename` en cycle est une donnée possible : deux éditions
    croisées par PATCH), puis on DESCEND (largeur d'abord, bornée).
    `mere` : la ligne de la mère, ou — mère hors de l'index (la vidéo d'un
    rendu, pour un sprite) — {filename, externe: true, job_id} ; `filles` :
    les enfants DIRECTS du fichier. None si le fichier n'est ni au magasin
    ni dans l'index."""
    from sqlalchemy import select, or_
    from app.services.storage import LibraryAsset, JobRecord, async_session_factory
    nom = Path(str(filename or "")).name
    async with async_session_factory() as s:
        res = await s.execute(select(
            LibraryAsset.filename, LibraryAsset.parent_filename,
            LibraryAsset.relation, LibraryAsset.source, LibraryAsset.kind,
            LibraryAsset.job_id))
        lignes = {r[0]: {"filename": r[0], "parent": r[1], "relation": r[2],
                         "source": r[3], "kind": r[4], "job_id": r[5]}
                  for r in res.fetchall()}
        if nom not in lignes and du_magasin(nom) is None:
            return None
        noeud = lignes.get(nom) or {"filename": nom, "parent": None, "relation": None,
                                    "source": None, "kind": du_magasin(nom), "job_id": None}
        racine, vus, cycle = nom, {nom}, False
        for _ in range(LIGNEE_PAS):
            p = (lignes.get(racine) or {}).get("parent")
            if not p or p not in lignes:
                break
            if p in vus:
                cycle = True
                break
            vus.add(p)
            racine = p
        mere = None
        p = noeud.get("parent")
        if p and p in lignes:
            mere = lignes[p]
        elif p:
            mere = {"filename": p, "externe": True, "job_id": None}
            res = await s.execute(select(JobRecord.id, JobRecord.final_video_path, JobRecord.video_path)
                                  .where(or_(JobRecord.final_video_path.like(f"%{p}"),
                                             JobRecord.video_path.like(f"%{p}"))))
            for jid, fv, v in res.fetchall():
                if p in (Path(str(fv or "")).name, Path(str(v or "")).name):
                    mere["job_id"] = jid
                    break
    enfants_de: dict = {}
    for n, l in lignes.items():
        if l["parent"]:
            enfants_de.setdefault(l["parent"], []).append(l)
    enfants, file_, vus2, tronque = [], [racine], {racine}, False
    while file_:
        cour = file_.pop(0)
        for l in sorted(enfants_de.get(cour, []), key=lambda z: z["filename"]):
            if l["filename"] in vus2:
                continue
            if len(enfants) >= LIGNEE_MAX:
                tronque = True
                break
            vus2.add(l["filename"])
            enfants.append(l)
            file_.append(l["filename"])
    filles = sorted((l for l in enfants_de.get(nom, []) if l["filename"] != nom), key=lambda z: z["filename"])
    return {"filename": nom, "racine": racine, "cycle": cycle, "noeud": noeud,
            "mere": mere, "filles": filles, "enfants": enfants, "tronque": tronque}


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
