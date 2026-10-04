# -*- coding: utf-8 -*-
"""Tâche #80 (03/10/2026, plan-library T6-T8) — la FICHE COMPLÈTE d'un asset
de la Bibliothèque, lue d'un coup par l'écran.

Décisions de l'utilisateur (03/10) : une fiche EXPLICITE et éditable (pas le
panneau générique du plan) — droits (licence, auteur, lien source ; alerte si
la licence est inconnue), fichier (dimensions, poids, date), recette, usages ;
la recette d'une image GÉNÉRÉE est enregistrée désormais par /images/generate
(colonne `recette`) et la fiche lit aussi celles qui existaient déjà à côté
des fichiers (images fixes de gabarit, dépôts du téléphone) ; « Rejouer » ne
vaut que pour une recette du générateur (route payante, gardée par le plafond).

Ce que le plan faisait faux : la recette tirée de JobRecord (les images du
générateur n'ont NI job NI prompt stocké) ; « 7 colonnes, 5 tables » (4 tables,
et il manquait shots.image, scenes.vo_audio, les projets) ; rejouer vers
/api/generate (le rendu VIDÉO payant). Lecture seule, aucune dépense.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.services import library_index as LI

#: les licences que l'écran propose (la saisie libre reste possible)
LICENCES = ("propriétaire", "CC0", "CC BY", "CC BY-SA", "CC BY-NC", "domaine public",
            "sous licence (achat)", "inconnue")
#: ce que « Rejouer » renvoie à /images/generate (le reste de la recette est descriptif)
CHAMPS_REJOUER = ("prompt", "style", "model", "size", "seed", "background")


def alerte_licence(licence: str | None) -> bool:
    return not licence or str(licence).strip().lower() == LI.LICENCE_INCONNUE


def _chemin(nom: str, kind: str | None) -> Path | None:
    if kind == "audio":
        p = settings.images_path.parent / "audio" / nom
    else:
        p = settings.images_path / nom
    return p if p.is_file() else None


def _fichier(p: Path | None, kind: str | None) -> dict | None:
    if p is None:
        return None
    st = p.stat()
    out = {"octets": st.st_size,
           "modifie": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
           "largeur": None, "hauteur": None, "format": p.suffix.lower().lstrip(".")}
    if kind != "audio":
        try:
            from PIL import Image
            with Image.open(p) as im:
                out["largeur"], out["hauteur"] = im.size
        except Exception:  # noqa: BLE001 — une image illisible garde poids et date
            pass
    return out


def _json(brut):
    try:
        v = json.loads(brut) if isinstance(brut, str) else brut
    except Exception:  # noqa: BLE001
        return None
    return v if isinstance(v, dict) else None


def _recette(nom: str, brut) -> dict | None:
    """La recette, et D'OÙ elle vient : l'index (générateur), le fichier posé à côté d'une image fixe de gabarit,
    ou la recette d'un dépôt du téléphone. None : inconnue (image antérieure, import…)."""
    r = _json(brut)
    if r:
        return {"origine": "generation", **r}
    side = settings.images_path / f"{nom}.recette.json"
    if side.is_file():
        r = _json(side.read_text(encoding="utf-8", errors="replace"))
        if r:
            return {"origine": "template", **r}
    mob = settings.outputs_path / "_sync" / "recettes" / f"{nom}.json"
    if mob.is_file():
        r = _json(mob.read_text(encoding="utf-8", errors="replace"))
        if r:
            return {"origine": "mobile", **r}
    return None


def rejouer(recette: dict | None) -> dict | None:
    """Le corps à renvoyer à /images/generate — seulement pour une recette du générateur qui a un prompt. Une image
    à la fois ; la graine est gardée (même graine + même modèle = la même image chez FLUX)."""
    if not recette or recette.get("origine") != "generation" or not str(recette.get("prompt") or "").strip():
        return None
    corps = {k: recette[k] for k in CHAMPS_REJOUER if recette.get(k) not in (None, "")}
    corps["n"] = 1
    corps["source"] = "generation"
    # le prix annoncé AVANT le tir (calcul local de la grille, aucun appel) — le plafond reste la garde du serveur
    from app.services import pricing as _P
    try:
        usd = float(_P.estimate({"kind": "image", "n": 1, "model": corps.get("model") or "flux"}).get("total_usd") or 0)
    except Exception:  # noqa: BLE001 — sans grille, le prix est dit inconnu
        usd = None
    return {"route": "/api/images/generate", "corps": corps, "usd": usd}


async def _usages(nom: str) -> list[dict]:
    """Où l'asset sert : rendus (image de départ / de fin), posts programmés, bible, plans, scènes (voix), projets."""
    from sqlalchemy import or_, select
    from app.services.storage import (BibleEntity, JobRecord, LibraryProject, LibraryProjectItem, ScheduledPost,
                                      Scene, Shot, async_session_factory)
    out: list[dict] = []
    async with async_session_factory() as s:
        for j in (await s.execute(select(JobRecord).where(or_(JobRecord.image_filename == nom,
                                                            JobRecord.image_filename_end == nom)))).scalars():
            out.append({"type": "rendu", "id": j.id, "libelle": j.title or j.id[:8],
                        "role": "image de fin" if j.image_filename_end == nom and j.image_filename != nom else "image de départ"})
        for p in (await s.execute(select(ScheduledPost).where(ScheduledPost.source_image == nom))).scalars():
            out.append({"type": "post", "id": p.id, "libelle": p.title or p.id[:8], "role": p.status})
        motif = f'%"{nom}"%'
        for b in (await s.execute(select(BibleEntity).where(or_(BibleEntity.ref_image == nom, BibleEntity.face_image == nom,
                                                              BibleEntity.inspiration_images.like(motif))))).scalars():
            role = "référence" if b.ref_image == nom else "visage" if b.face_image == nom else "inspiration"
            if role == "inspiration":   # le LIKE est large : on relit la liste
                try:
                    if nom not in (json.loads(b.inspiration_images or "[]") or []):
                        continue
                except Exception:  # noqa: BLE001
                    continue
            out.append({"type": "bible", "id": b.id, "libelle": b.name, "role": role})
        for sh in (await s.execute(select(Shot).where(or_(Shot.sketch_image == nom, Shot.image == nom)))).scalars():
            out.append({"type": "plan", "id": sh.id, "libelle": f"plan {sh.idx + 1}", "role": "production" if sh.image == nom else "croquis",
                        "chapitre": sh.chapter_id})
        for sc in (await s.execute(select(Scene).where(Scene.vo_audio == nom))).scalars():
            out.append({"type": "scene", "id": sc.id, "libelle": getattr(sc, "slugline", None) or sc.id[:8], "role": "voix off",
                        "chapitre": sc.chapter_id})
        res = await s.execute(select(LibraryProject.id, LibraryProject.nom)
                              .join(LibraryProjectItem, LibraryProjectItem.project_id == LibraryProject.id)
                              .where(LibraryProjectItem.ref == nom))
        for pid, pnom in res.fetchall():
            out.append({"type": "projet", "id": pid, "libelle": pnom, "role": "membre"})
    return out


async def fiche(filename: str) -> dict | None:
    """La fiche, ou None si le fichier n'est ni au magasin ni dans l'index."""
    from app.services.storage import LibraryAsset, async_session_factory
    nom = Path(str(filename or "")).name
    if not nom or nom in (".", ".."):
        return None
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, nom)
    kind = (row.kind if row else None) or LI.du_magasin(nom)
    p = _chemin(nom, kind)
    if row is None and p is None:
        return None
    source = row.source if row else (LI.heuristique(nom) if kind != "audio" else "inconnu")
    licence = row.licence if row and row.licence else LI.licence_defaut(nom, source)
    rec = _recette(nom, row.recette if row else None)
    return {
        "filename": nom, "kind": kind or "image", "source": source,
        "source_libelle": LI.SOURCES.get(source, source), "origin": row.origin if row else "heuristique",
        "job_id": row.job_id if row else None,
        "droits": {"licence": licence, "alerte": alerte_licence(licence), "auteur": row.auteur if row else None,
                   "source_url": row.source_url if row else None, "licences": list(LICENCES)},
        "fichier": _fichier(p, kind),
        "couleur": {"hex": row.couleur, "teinte": row.teinte} if row and row.couleur else None,   # tâche #81
        "recette": rec,
        "legende": {"texte": row.legende, "modele": row.legende_modele} if row and row.legende else None,   # tâche #82
        "rejouer": rejouer(rec),
        "usages": await _usages(nom),
    }
