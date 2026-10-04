# -*- coding: utf-8 -*-
"""Tâche #82 (04/10/2026, plan-library T14) — les COMMENTAIRES d'un asset de la Bibliothèque.

Décision de l'utilisateur (04/10) : des commentaires de revue DATÉS avec un STATUT (à revoir / validé / rejeté), comme le
plan (façon Frame.io), nommés « commentaires » — « note » désigne déjà la note 0..5 (#77) ; pour un son, l'instant visé ;
la recherche (PR C) les lira. Le plan les rangeait dans `library_fiche.sections`, qui n'existe pas : routes à part,
lues par la fiche.
Un commentaire suit son asset : renommé (library_index.renommer), il change de référence ; jeté à la corbeille, il part
dans le journal et revient avec lui (sous le nom rendu).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

STATUTS = ("a_revoir", "valide", "rejete")
TEXTE_MAX = 2000


def _ref(ref: str) -> str:
    r = Path(str(ref or "")).name
    if not r or r in (".", "..") or r != str(ref):
        raise ValueError("Référence invalide")
    return r


def _vue(c) -> dict:
    return {"id": c.id, "ref": c.ref, "texte": c.texte, "statut": c.statut, "t_s": c.t_s,
            "cree_le": c.created_at.replace(tzinfo=timezone.utc).isoformat(timespec="seconds") if c.created_at else None,
            "modifie_le": c.updated_at.replace(tzinfo=timezone.utc).isoformat(timespec="seconds") if c.updated_at else None}


def _valider(texte=None, statut=None, t_s=None, exiger_texte=False) -> dict:
    out = {}
    if texte is not None or exiger_texte:
        if not isinstance(texte, str) or not texte.strip():
            raise ValueError("Le commentaire est vide.")
        if len(texte) > TEXTE_MAX:
            raise ValueError(f"Le commentaire dépasse {TEXTE_MAX} caractères.")
        out["texte"] = texte.strip()
    if statut is not None:
        if statut not in STATUTS:
            raise ValueError(f"statut parmi {', '.join(STATUTS)}")
        out["statut"] = statut
    if t_s is not None:
        if isinstance(t_s, bool) or not isinstance(t_s, (int, float)) or t_s < 0 or t_s > 86400:
            raise ValueError("t_s : un instant en secondes (0 à 86400)")
        out["t_s"] = float(t_s)
    return out


async def lister(ref: str) -> list[dict]:
    from sqlalchemy import select
    from app.services.storage import LibraryComment, async_session_factory
    r = _ref(ref)
    async with async_session_factory() as s:
        res = await s.execute(select(LibraryComment).where(LibraryComment.ref == r)
                              .order_by(LibraryComment.created_at, LibraryComment.id))
        return [_vue(c) for c in res.scalars().all()]


async def ajouter(ref: str, texte, statut=None, t_s=None) -> dict:
    from app.services.storage import LibraryComment, async_session_factory
    r = _ref(ref)
    v = _valider(texte, statut, t_s, exiger_texte=True)
    maintenant = datetime.now(timezone.utc).replace(tzinfo=None)
    c = LibraryComment(id=uuid4().hex, ref=r, texte=v["texte"], statut=v.get("statut", "a_revoir"), t_s=v.get("t_s"),
                       created_at=maintenant, updated_at=maintenant)
    async with async_session_factory() as s:
        s.add(c)
        await s.commit()
        return _vue(c)


async def modifier(cid: str, champs: dict) -> dict | None:
    from app.services.storage import LibraryComment, async_session_factory
    v = _valider(champs.get("texte"), champs.get("statut"), champs.get("t_s"))
    if not v:
        raise ValueError("Rien à modifier (texte, statut ou t_s).")
    async with async_session_factory() as s:
        c = await s.get(LibraryComment, str(cid))
        if c is None:
            return None
        for k, val in v.items():
            setattr(c, k, val)
        c.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await s.commit()
        return _vue(c)


async def supprimer(cid: str) -> bool:
    from app.services.storage import LibraryComment, async_session_factory
    async with async_session_factory() as s:
        c = await s.get(LibraryComment, str(cid))
        if c is None:
            return False
        await s.delete(c)
        await s.commit()
        return True


async def renommer_ref(ancien: str, nouveau: str) -> None:
    from sqlalchemy import update
    from app.services.storage import LibraryComment, async_session_factory
    a, n = Path(str(ancien or "")).name, Path(str(nouveau or "")).name
    if not a or not n or a == n:
        return
    async with async_session_factory() as s:
        await s.execute(update(LibraryComment).where(LibraryComment.ref == a).values(ref=n))
        await s.commit()


async def emporter(ref: str) -> list[dict]:
    """Pour la corbeille : rend les commentaires (lignes complètes) et les RETIRE."""
    from sqlalchemy import delete, select
    from app.services.storage import LibraryComment, async_session_factory
    async with async_session_factory() as s:
        res = await s.execute(select(LibraryComment).where(LibraryComment.ref == ref))
        out = [{"id": c.id, "texte": c.texte, "statut": c.statut, "t_s": c.t_s,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None} for c in res.scalars().all()]
        await s.execute(delete(LibraryComment).where(LibraryComment.ref == ref))
        await s.commit()
    return out


async def rapporter(ref: str, lignes: list[dict]) -> None:
    """Pour la corbeille : remet les commentaires emportés, sous la référence rendue."""
    from app.services.storage import LibraryComment, async_session_factory
    async with async_session_factory() as s:
        for l in lignes or []:
            if await s.get(LibraryComment, l["id"]) is not None:
                continue
            s.add(LibraryComment(id=l["id"], ref=ref, texte=l["texte"], statut=l.get("statut") or "a_revoir", t_s=l.get("t_s"),
                                 created_at=datetime.fromisoformat(l["created_at"]) if l.get("created_at") else None,
                                 updated_at=datetime.fromisoformat(l["updated_at"]) if l.get("updated_at") else None))
        await s.commit()
