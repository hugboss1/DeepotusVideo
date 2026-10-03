# -*- coding: utf-8 -*-
"""Tâche #81 (03/10/2026, plan-library T9) — le NETTOYAGE de la Bibliothèque : le poids par sorte et les DOUBLONS
EXACTS.

Décisions de l'utilisateur (03/10) : doublons EXACTS (même sha256, recalculé quand le fichier change) ; pour chaque
groupe, les fichiers avec leurs USAGES ; l'utilisateur coche ce qui part ; la copie UTILISÉE est PROTÉGÉE (usage connu,
favori ou projet) et un groupe garde toujours au moins une copie — le serveur le refuse s'il le faut, l'écran ne le
propose pas. Ce qui part va à la CORBEILLE (restaurable, PR A). Rien n'est jeté sans l'utilisateur.
Mesuré sur la vraie bibliothèque (03/10, lecture seule) : 1009 images, 1,07 Go, sha256 en 3,1 s ; 5 groupes, 17 copies
en trop. L'empreinte réutilise le cache de sync_lot (chemin + mtime) : un fichier réécrit en place est re-haché.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def _empreintes(fichiers: list[Path]) -> dict[str, tuple[str, int]]:
    """{nom: (sha256, octets)} — synchrone (thread de l'appelant)."""
    from app.services.sync_lot import _sha256
    out = {}
    for p in fichiers:
        try:
            out[p.name] = (_sha256(p), p.stat().st_size)
        except OSError:
            continue
    return out


def _poids(d: Path, motif: str = "*") -> dict:
    n, o = 0, 0
    if d.is_dir():
        for f in d.rglob(motif):
            if f.is_file():
                n += 1
                o += f.stat().st_size
    return {"fichiers": n, "octets": o}


def mesurer() -> dict:
    """La partie DISQUE (thread) : empreintes des images et poids par sorte."""
    from app.services.library_index import _IMAGE_EXTS
    imgs = [p for p in settings.images_path.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_EXTS] \
        if settings.images_path.is_dir() else []
    from app.services.library_corbeille import dossier as _corb
    poids = {"images": {"fichiers": len(imgs), "octets": sum(p.stat().st_size for p in imgs)},
             "sons": _poids(settings.images_path.parent / "audio"),
             "rendus": _poids(settings.outputs_path),
             "corbeille": _poids(_corb())}
    return {"empreintes": _empreintes(imgs), "poids": poids}


async def rapport() -> dict:
    """Poids par sorte + groupes de doublons exacts, chaque fichier avec usages, favori, projets et `protege`."""
    import asyncio
    from sqlalchemy import select
    from app.services import library_fiche as LF
    from app.services.storage import LibraryAsset, async_session_factory
    t0 = datetime.now(timezone.utc)
    m = await asyncio.to_thread(mesurer)
    emp = m["empreintes"]
    # l'empreinte et le poids vont à l'index (colonnes posées par #77, jamais écrites jusqu'ici)
    async with async_session_factory() as s:
        rows = {r.filename: r for r in (await s.execute(select(LibraryAsset).where(LibraryAsset.filename.in_(list(emp))))).scalars()}
        for nom, (h, o) in emp.items():
            r = rows.get(nom)
            if r is not None and (r.sha256 != h or r.taille_o != o):
                r.sha256, r.taille_o = h, o
        await s.commit()
    par_h: dict[str, list[str]] = {}
    for nom, (h, _o) in emp.items():
        if h:
            par_h.setdefault(h, []).append(nom)
    groupes = []
    for h, noms in par_h.items():
        if len(noms) < 2:
            continue
        fichiers = []
        for nom in sorted(noms):
            us = await LF._usages(nom)
            r = rows.get(nom)
            projets = [u for u in us if u["type"] == "projet"]
            p = settings.images_path / nom
            fichiers.append({"filename": nom, "octets": emp[nom][1],
                             "modifie": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                             "usages": [u for u in us if u["type"] != "projet"], "projets": [u["libelle"] for u in projets],
                             "fav": bool(r and r.fav), "source": r.source if r else None})
        for f in fichiers:
            f["protege"] = bool(f["usages"] or f["projets"] or f["fav"])
        if not any(f["protege"] for f in fichiers):
            # personne n'est protégé : on GARDE la plus ancienne (proposée, pas imposée — l'écran la laisse décochée)
            min(fichiers, key=lambda f: (f["modifie"], f["filename"]))["garder"] = True
        groupes.append({"sha256": h, "octets": emp[noms[0]][1], "fichiers": fichiers,
                        "en_trop": len(noms) - 1})
    groupes.sort(key=lambda g: -g["octets"] * g["en_trop"])
    return {"poids": m["poids"], "doublons": groupes,
            "copies_en_trop": sum(g["en_trop"] for g in groupes),
            "octets_recuperables": sum(g["octets"] * g["en_trop"] for g in groupes),
            "duree_s": round((datetime.now(timezone.utc) - t0).total_seconds(), 2)}


async def jeter(noms: list[str]) -> dict:
    """Envoie des copies de doublons à la CORBEILLE, après vérification FRAÎCHE : chaque nom est bien un doublon,
    aucun n'est protégé, aucun groupe ne perd sa dernière copie. Tout ou rien : ValueError nommée sinon."""
    from app.services import library_corbeille as LC
    noms = [Path(str(n)).name for n in (noms or []) if str(n).strip()]
    if not noms:
        raise ValueError("Aucun fichier à jeter.")
    r = await rapport()
    groupe_de, fiche = {}, {}
    for g in r["doublons"]:
        for f in g["fichiers"]:
            groupe_de[f["filename"]] = g
            fiche[f["filename"]] = f
    for n in noms:
        if n not in groupe_de:
            raise ValueError(f"« {n} » n'est pas (ou plus) un doublon.")
        if fiche[n]["protege"]:
            raise ValueError(f"« {n} » est utilisé (usage, favori ou projet) : il est protégé.")
    for g in {id(groupe_de[n]): groupe_de[n] for n in noms}.values():
        restants = [f for f in g["fichiers"] if f["filename"] not in noms]
        if not restants:
            raise ValueError("Un groupe garderait zéro copie : gardez-en au moins une.")
    faits = []
    for n in noms:
        e = await LC.jeter_fichier(n, "image")
        if e:
            faits.append({"filename": n, "corbeille": e["id"]})
    return {"jetes": faits}
