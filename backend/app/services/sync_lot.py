# -*- coding: utf-8 -*-
"""Plan mobile T8 (tâche #57, 01/10/2026) — « le Scheduler dans la poche » : le lot part, l'état revient.

DÉCISIONS DE L'UTILISATEUR (01/10) :
  - DÉLÉGATION EXPLICITE : un post emporté par un téléphone lui est CONFIÉ (`ScheduledPost.delegue_a`). Le Scheduler du
    PC ne le publie plus (tick et « publier maintenant ») tant qu'il ne lui revient pas : échec rapporté, rendu par le
    téléphone, reprise à la main sur le PC, ou appareil révoqué. Aucun doublon possible.
  - UNE SEULE écriture ouverte au réseau local en plus de l'appairage : POST /api/sync/lot/etat, qui porte TOUS les
    statuts du téléphone (emporte, posted, failed, rendu). Un appareil n'agit que sur SES posts.

CE QUE LE LOT NE CONTIENT PAS : aucun jeton, aucune clé — le téléphone les a par l'archive chiffrée (tâche 7) ; le
backend ne fait jamais sortir un secret par le réseau (`_require_localhost` en est l'autre moitié).

QUI GAGNE EN CAS DE CONFLIT : le PC. Un post qu'il a déjà publié ne change plus ; le conflit est RENDU, pas avalé.
"""
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger
from sqlalchemy import or_ as _or, select as _select

PROTOCOLE = 1
STATUTS = ("emporte", "posted", "failed", "rendu")
_EMPREINTES: dict[tuple[str, int], str] = {}


def _sha256(chemin: Path) -> str:
    """sha256 avec cache sur (chemin, mtime_ns) — un rendu fini ne change plus, et le téléphone relit le lot souvent."""
    try:
        cle = (str(chemin), chemin.stat().st_mtime_ns)
    except OSError:
        return ""
    if cle not in _EMPREINTES:
        h = hashlib.sha256()
        with open(chemin, "rb") as fh:
            for bloc in iter(lambda: fh.read(1 << 20), b""):
                h.update(bloc)
        if len(_EMPREINTES) > 4096:
            _EMPREINTES.clear()
        _EMPREINTES[cle] = h.hexdigest()
    return _EMPREINTES[cle]


def _iso(d: datetime | None) -> str | None:
    return d.replace(microsecond=0).isoformat() + "Z" if d else None


async def lot(appareil_id: str, jours: int = 7) -> dict:
    """Les posts actionnables des `jours` prochains (et en retard), LIBRES ou déjà confiés à CET appareil."""
    from app.services.storage import JobRecord, ScheduledPost, async_session_factory
    jours = max(1, min(int(jours or 7), 31))
    limite = datetime.utcnow() + timedelta(days=jours)
    posts = []
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost)
            .where(ScheduledPost.status.in_(("scheduled", "ready")))
            .where(ScheduledPost.run_at <= limite)
            .where(_or(ScheduledPost.delegue_a.is_(None), ScheduledPost.delegue_a == appareil_id))
            .order_by(ScheduledPost.run_at.asc()))
        for p in res.scalars().all():
            media = None
            if p.job_id:
                job = await session.get(JobRecord, p.job_id)
                chemin = Path(job.final_video_path) if job and job.final_video_path else None
                if chemin and chemin.is_file():
                    media = {"nom": chemin.name, "taille": chemin.stat().st_size, "sha256": _sha256(chemin),
                             "url": f"/api/sync/media/{p.job_id}"}
            posts.append({"id": p.id, "titre": p.title, "legende": p.caption or "",
                          "canaux": [c for c in (p.channels or "").split(",") if c], "run_at": _iso(p.run_at),
                          "mode": p.mode, "statut": p.status, "confie": p.delegue_a == appareil_id, "media": media})
    return {"protocole": PROTOCOLE, "posts": posts, "genere_a": _iso(datetime.utcnow())}


async def appliquer_etat(appareil: dict, rapports: list) -> dict:
    """Le téléphone dit ce qu'il emporte, publie, rate ou rend. Rend {appliques, conflits} — jamais silencieux."""
    from app.services.storage import ScheduledPost, async_session_factory
    appliques: list[str] = []
    conflits: list[dict] = []
    moi, nom = appareil["id"], (appareil.get("nom") or "téléphone")[:60]
    async with async_session_factory() as session:
        for r in rapports if isinstance(rapports, list) else []:
            r = r if isinstance(r, dict) else {}
            ident, statut = str(r.get("id") or ""), str(r.get("statut") or "")
            if statut not in STATUTS:
                conflits.append({"id": ident, "raison": f"statut inconnu « {statut} »"})
                continue
            p = await session.get(ScheduledPost, ident)
            if p is None:
                conflits.append({"id": ident, "raison": "post inconnu"})
                continue
            if p.status == "posted":
                conflits.append({"id": ident, "raison": "déjà publié par le PC", "rapport_ignore": statut})
                continue
            if p.delegue_a and p.delegue_a != moi:
                conflits.append({"id": ident, "raison": "confié à un autre appareil"})
                continue
            if statut == "emporte":
                if p.status not in ("scheduled", "ready"):
                    conflits.append({"id": ident, "raison": f"pas actionnable (statut {p.status})"})
                    continue
                p.delegue_a, p.delegue_le = moi, datetime.utcnow()
            elif p.delegue_a != moi:
                conflits.append({"id": ident, "raison": "pas confié à cet appareil : emportez-le d'abord"})
                continue
            elif statut == "posted":
                p.status = "posted"
                try:
                    p.posted_at = datetime.fromisoformat(str(r.get("publie_a") or "").replace("Z", ""))
                except ValueError:
                    p.posted_at = datetime.utcnow()
                p.published_by = nom[:40]
                p.error = None
                p.delegue_a, p.delegue_le = None, None
            elif statut == "failed":
                p.status = "ready"
                p.error = f"échec sur {nom} : {str(r.get('detail') or '')[:400]}"[:500]
                p.delegue_a, p.delegue_le = None, None
            else:                                                  # rendu
                p.delegue_a, p.delegue_le = None, None
            appliques.append(ident)
        await session.commit()
    if conflits:
        logger.warning(f"sync_lot: {len(conflits)} conflit(s) au retour de {nom}")
    return {"appliques": appliques, "conflits": conflits}


async def reprendre(post_id: str) -> bool:
    """Le PC reprend un post confié (téléphone éteint, oublié…). Rend False si le post n'était confié à personne."""
    from sqlalchemy import update as _update
    from app.services.storage import ScheduledPost, async_session_factory
    async with async_session_factory() as session:
        r = await session.execute(_update(ScheduledPost).where(ScheduledPost.id == post_id)
                                  .where(ScheduledPost.delegue_a.is_not(None)).values(delegue_a=None, delegue_le=None))
        await session.commit()
    return r.rowcount > 0
