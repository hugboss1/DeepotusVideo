# -*- coding: utf-8 -*-
"""Plan mobile T17 (tâche #58, 01-02/10/2026) — les événements du PC que le téléphone change en notifications.

Le PC ne notifie rien : il fournit la matière, et chaque événement porte une CLÉ stable — le téléphone retient les
clés déjà vues, un même événement relu ne sonne pas deux fois. Deux sortes :
  - des FAITS datés (rendu terminé / échoué, post publié), filtrés par `depuis` ;
  - des ÉTATS en cours (un post attend un geste, une publication a échoué, un plafond est approché ou dépassé),
    rendus tant qu'ils durent : `depuis` ne les cache pas, leur clé évite le doublon.

Écarts au plan du 03/09, mesurés dans le code :
  - un rendu fini a le statut « done » (`JobStatus.DONE`), pas « completed » — le plan n'en aurait jamais vu un ;
  - un post n'a pas de statut « failed » : un échec est « ready » AVEC une erreur, « ready » SANS erreur est un post
    assisté qui attend un geste ; un post publié se date par `posted_at`, pas par `run_at` ;
  - délégation D6 : un post confié à un appareil n'est plus l'affaire du PC (le téléphone a son rappel local) ;
  - les plafonds existent (#16) : `plafonds.etat()` et sa liste `alerte` ;
  - « synchronisation terminée / en conflit » sont LOCALES au téléphone (il reçoit les conflits en réponse).
"""
import hashlib
from datetime import datetime

from sqlalchemy import select as _select

from app.services.sync_lot import _iso

FAMILLES = ("rendu_termine", "rendu_echoue", "post_a_publier", "post_publie", "post_echoue",
            "plafond_approche", "plafond_depasse")
LIMITE_MAX = 500


def _seuil(depuis: str | None) -> datetime | None:
    """`depuis` en ISO UTC ; les colonnes sont en UTC naïf. Illisible -> aucun filtre (tout, pas une erreur)."""
    if not depuis:
        return None
    try:
        return datetime.fromisoformat(str(depuis).replace("Z", "")).replace(tzinfo=None)
    except ValueError:
        return None


def _usd(x: float) -> str:
    return f"{x:,.2f} $".replace(",", " ").replace(".", ",")


async def _plafonds() -> list[dict]:
    from app.services import plafonds as _pl
    try:
        e = await _pl.etat()
    except Exception:  # noqa: BLE001 — un compteur illisible ne doit pas priver le téléphone des autres événements
        return []
    out = []
    for qui in e.get("alerte", []):
        v = e["global"] if qui == "global" else (e.get("par_moteur") or {}).get(qui) or {}
        pct, plafond, eff = float(v.get("pct") or 0), float(v.get("plafond_usd") or 0), float(v.get("effectif_usd") or 0)
        famille = "plafond_depasse" if pct >= 100 else "plafond_approche"
        nom = "Plafond mensuel global" if qui == "global" else f"Plafond {qui}"
        out.append({"type": famille, "ref": qui, "titre": nom,
                    "detail": f"{qui} : {pct:.0f} % du plafond ({_usd(eff)} sur {_usd(plafond)}) — {e.get('mois')}",
                    "quand": None, "cle": f"{famille}:{qui}:{e.get('mois')}"})
    return out


async def evenements(depuis: str | None = None, limite: int = 200) -> dict:
    from app.services.storage import JobRecord, ScheduledPost, async_session_factory
    seuil = _seuil(depuis)
    limite = max(1, min(int(limite or 200), LIMITE_MAX))
    out: list[dict] = []
    async with async_session_factory() as session:
        q = _select(JobRecord).where(JobRecord.status.in_(("done", "failed"))).where(JobRecord.completed_at.is_not(None))
        if seuil is not None:
            q = q.where(JobRecord.completed_at > seuil)
        for j in (await session.execute(q.order_by(JobRecord.completed_at.desc()).limit(limite))).scalars().all():
            famille = "rendu_termine" if j.status == "done" else "rendu_echoue"
            out.append({"type": famille, "ref": j.id, "titre": j.title or j.id, "detail": (j.error or "")[:200],
                        "quand": _iso(j.completed_at), "cle": f"{famille}:{j.id}"})

        q = _select(ScheduledPost).where(ScheduledPost.status == "posted").where(ScheduledPost.posted_at.is_not(None))
        if seuil is not None:
            q = q.where(ScheduledPost.posted_at > seuil)
        for p in (await session.execute(q.order_by(ScheduledPost.posted_at.desc()).limit(limite))).scalars().all():
            out.append({"type": "post_publie", "ref": p.id, "titre": p.title or p.id, "detail": "",
                        "quand": _iso(p.posted_at), "cle": f"post_publie:{p.id}:{_iso(p.posted_at)}"})

        # ÉTATS : un post « ready » que le PC garde (D6 : aucun post confié à un appareil)
        q = (_select(ScheduledPost).where(ScheduledPost.status == "ready").where(ScheduledPost.delegue_a.is_(None))
             .order_by(ScheduledPost.run_at.desc()).limit(limite))
        for p in (await session.execute(q)).scalars().all():
            if p.error:
                empreinte = hashlib.sha1(p.error.encode("utf-8")).hexdigest()[:10]
                out.append({"type": "post_echoue", "ref": p.id, "titre": p.title or p.id, "detail": p.error[:200],
                            "quand": _iso(p.run_at), "cle": f"post_echoue:{p.id}:{empreinte}"})
            else:
                out.append({"type": "post_a_publier", "ref": p.id, "titre": p.title or p.id,
                            "detail": "attend un geste sur le PC (mode assisté)",
                            "quand": _iso(p.run_at), "cle": f"post_a_publier:{p.id}:{_iso(p.run_at)}"})
    out.extend(await _plafonds())
    return {"evenements": out, "familles": list(FAMILLES), "genere_a": _iso(datetime.utcnow())}
