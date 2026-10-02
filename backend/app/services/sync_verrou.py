# -*- coding: utf-8 -*-
"""Plan mobile T14 + T21 (tâche #59, 02/10/2026) — un chapitre EMPORTÉ par le téléphone, écrit hors ligne, RENDU.

DÉCISIONS DE L'UTILISATEUR (02/10) :
  - PRENDRE et RENDRE sont les deux seules écritures ouvertes au Wi-Fi (`main._ECRITURES_OUVERTES`) ; l'appareil est
    celui du JETON. L'id du chapitre voyage dans le corps : la liste des écritures ouvertes est EXACTE ;
  - un chapitre emporté est protégé PARTOUT sur le PC : modification, suppression et ré-import du manuscrit (`garde`) ;
  - « Reprendre sur le PC » force la libération (boucle locale) ; révoquer l'appareil libère ses chapitres ;
  - un conflit est JOURNALISÉ avec son texte (`SyncConflit`) : rien n'est écrasé en silence, rien n'est perdu.
"""
import hashlib
import json
import os
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete as _delete, select as _select
from sqlalchemy.exc import IntegrityError

from app.config import settings

TEXTE_MAX = 2 * 1024 * 1024
ANNOTATIONS_MAX = 500
ANNOTATION_MAX = 2000


def _iso(d: datetime | None) -> str | None:
    return d.replace(microsecond=0).isoformat() + "Z" if d else None


def empreinte(texte: str | None) -> str:
    return hashlib.sha256((texte or "").encode("utf-8")).hexdigest()


async def _journal(session, chapter_id: str, motif: str, texte: str | None, appareil: dict | None = None) -> None:
    from app.services.storage import SyncConflit
    session.add(SyncConflit(chapter_id=chapter_id, motif=motif, texte=texte,
                            device_id=(appareil or {}).get("id"), device_nom=str((appareil or {}).get("nom") or "")[:60]))


def _refus_verrou(v) -> HTTPException:
    return HTTPException(423, f"Ce chapitre est emporté par le téléphone « {v.device_nom} » depuis le {_iso(v.pris_le)} : "
                              "il l'écrit hors ligne. Reprenez-le d'abord sur le PC (« Reprendre sur le PC ») — "
                              "son retour sera alors gardé au journal, jamais perdu.")


async def garde(chapter_id: str) -> None:
    """À appeler AVANT toute écriture du PC sur un chapitre : 423 s'il est emporté."""
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as s:
        v = await s.get(ChapterLock, chapter_id)
    if v is not None:
        raise _refus_verrou(v)


async def verrouilles() -> set[str]:
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as s:
        return set((await s.execute(_select(ChapterLock.chapter_id))).scalars().all())


async def journaliser_reimport(chapter_id: str, texte: str) -> None:
    """Le ré-import du manuscrit a sauté ce chapitre emporté : son texte va au journal."""
    from app.services.storage import async_session_factory
    async with async_session_factory() as s:
        await _journal(s, chapter_id, "reimport", texte)
        await s.commit()


async def prendre(appareil: dict, chapter_id: str) -> dict:
    from app.services.storage import Chapter, ChapterLock, async_session_factory
    async with async_session_factory() as s:
        ch = await s.get(Chapter, chapter_id)
        if ch is None:
            raise HTTPException(404, "Chapitre introuvable")
        v = await s.get(ChapterLock, chapter_id)
        if v is not None and v.device_id != appareil["id"]:
            raise HTTPException(409, f"Ce chapitre est déjà emporté par « {v.device_nom} »")
        if v is None:
            v = ChapterLock(chapter_id=chapter_id, device_id=appareil["id"], device_nom=str(appareil["nom"])[:60],
                            base_sha256=empreinte(ch.script_text), pris_le=datetime.utcnow())
            s.add(v)
            try:
                await s.commit()
            except IntegrityError:            # deux prises simultanées : la seconde perd, proprement
                raise HTTPException(409, "Ce chapitre vient d'être emporté par un autre appareil") from None
        return {"chapitre": {"id": ch.id, "title": ch.title, "series": ch.series, "script_text": ch.script_text or ""},
                "sha256": v.base_sha256, "pris_le": _iso(v.pris_le)}


def _annotations(brut) -> list[dict]:
    if brut is None:
        return []
    if not isinstance(brut, list) or len(brut) > ANNOTATIONS_MAX:
        raise HTTPException(400, f"annotations : une liste d'au plus {ANNOTATIONS_MAX}")
    out = []
    for a in brut:
        if not isinstance(a, dict) or isinstance(a.get("offset"), bool) or not isinstance(a.get("offset"), int) \
                or a["offset"] < 0 or not isinstance(a.get("texte"), str) or len(a["texte"]) > ANNOTATION_MAX:
            raise HTTPException(400, "annotation illisible : {offset: entier >= 0, texte: chaîne}")
        out.append({"offset": a["offset"], "texte": a["texte"]})
    return out


def _fichier_annotations(chapter_id: str):
    return settings.outputs_path / "_sync" / "annotations" / f"{chapter_id}.json"


def lire_annotations(chapter_id: str) -> list[dict]:
    f = _fichier_annotations(chapter_id)
    try:
        v = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else []
        return v if isinstance(v, list) else []
    except (OSError, ValueError):
        return []


async def _spans(session, texte: str) -> str:
    """Le surlignage des entités de la Bible, recalculé sur le texte rendu (sinon il pointerait à côté)."""
    from app.services import manuscript_agent as MA
    from app.services.storage import BibleEntity
    ents = [{"id": e.id, "name": e.name, "aliases": json.loads(e.aliases) if e.aliases else [], "quotes": []}
            for e in (await session.execute(_select(BibleEntity))).scalars().all()]
    try:
        return json.dumps(MA.compute_spans(texte, ents))
    except Exception:  # noqa: BLE001 — un surlignage raté ne doit pas faire perdre le texte
        return "[]"


async def rendre(appareil: dict, corps: dict) -> dict:
    from app.services.storage import Chapter, ChapterLock, async_session_factory
    chapter_id = str(corps.get("chapitre") or "")
    texte = corps.get("texte")
    if not isinstance(texte, str) or len(texte.encode("utf-8")) > TEXTE_MAX:
        raise HTTPException(400, f"texte : une chaîne d'au plus {TEXTE_MAX} octets")
    notes = _annotations(corps.get("annotations"))
    async with async_session_factory() as s:
        ch = await s.get(Chapter, chapter_id)
        if ch is None:
            raise HTTPException(404, "Chapitre introuvable")
        v = await s.get(ChapterLock, chapter_id)
        if v is None or v.device_id != appareil["id"]:
            await _journal(s, chapter_id, "verrou_perdu", texte, appareil)
            await s.commit()
            raise HTTPException(409, "Ce téléphone n'a plus ce chapitre (repris sur le PC, ou emporté ailleurs) : "
                                     "votre texte est gardé au journal des conflits du PC.")
        if str(corps.get("base_sha256") or "") != v.base_sha256:
            await _journal(s, chapter_id, "base_differente", texte, appareil)
            await s.commit()
            raise HTTPException(409, "Ce texte part d'une autre version du chapitre : il est gardé au journal des conflits.")
        ch.script_text = texte
        ch.spans = await _spans(s, texte)
        ch.updated_at = datetime.utcnow()
        sha = empreinte(texte)
        if corps.get("garder") is True:
            v.base_sha256 = sha
        else:
            await s.delete(v)
        await s.commit()
    if notes or corps.get("annotations") is not None:
        f = _fichier_annotations(chapter_id)
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".part")
        tmp.write_text(json.dumps(notes, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, f)
    return {"chapitre": chapter_id, "sha256": sha, "garde": corps.get("garder") is True}


async def reprendre(chapter_id: str) -> bool:
    """« Reprendre sur le PC » : libération forcée, journalisée."""
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as s:
        v = await s.get(ChapterLock, chapter_id)
        if v is None:
            return False
        await _journal(s, chapter_id, "repris_pc", None, {"id": v.device_id, "nom": v.device_nom})
        await s.delete(v)
        await s.commit()
    return True


async def liberer_appareil(device_id: str | None = None) -> int:
    """Révocation : les chapitres de l'appareil (ou de tous, `None`) reviennent au PC, journalisés."""
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as s:
        q = _select(ChapterLock)
        if device_id is not None:
            q = q.where(ChapterLock.device_id == device_id)
        vs = (await s.execute(q)).scalars().all()
        for v in vs:
            await _journal(s, v.chapter_id, "revoque", None, {"id": v.device_id, "nom": v.device_nom})
        if vs:
            await s.execute(_delete(ChapterLock).where(ChapterLock.chapter_id.in_([v.chapter_id for v in vs])))
        await s.commit()
    return len(vs)


async def lister() -> dict:
    from app.services.storage import Chapter, ChapterLock, async_session_factory
    async with async_session_factory() as s:
        out = []
        for v in (await s.execute(_select(ChapterLock).order_by(ChapterLock.pris_le))).scalars().all():
            ch = await s.get(Chapter, v.chapter_id)
            out.append({"chapitre": v.chapter_id, "titre": ch.title if ch else "", "pris_le": _iso(v.pris_le),
                        "appareil": {"id": v.device_id, "nom": v.device_nom}})
    return {"verrous": out}


async def conflits(limite: int = 100) -> dict:
    from app.services.storage import SyncConflit, async_session_factory
    async with async_session_factory() as s:
        rows = (await s.execute(_select(SyncConflit).order_by(SyncConflit.id.desc())
                                .limit(max(1, min(int(limite or 100), 500))))).scalars().all()
    return {"conflits": [{"id": c.id, "quand": _iso(c.quand), "chapitre": c.chapter_id, "motif": c.motif,
                          "appareil": c.device_nom, "texte": c.texte} for c in rows]}
