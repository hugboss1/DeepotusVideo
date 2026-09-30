"""Métriques par post et par canal (plan scheduler P2, T7 — tâche #29, 30/09/2026) : instantanés datés dans
post_metrics, rafraîchis une fois par jour par la boucle (marketing.schedule_loop) ou à la demande, agrégés pour le
tableau de bord.

- Un fetcher par canal (`FETCHERS`, déclaré par chaque adaptateur comme son publieur) ; seuls les canaux DISPONIBLES
  (clés posées, `publishers`) sont interrogés : un canal déconnecté ne coûte ni appel ni erreur.
- X : 10 posts par passe ET le budget MENSUEL de lectures du palier gratuit (quota « x_lecture », 100/mois — docs.x.com,
  03/09/2026). Le plan du 03/09 ne rationnait que la passe : 10 par jour = ~300 lectures pour un budget de 100.
- X encore : les posts publiés AVANT le socle (#24) n'ont que `x_post_id` ; ils sont relus. La colonne `metrics` garde
  le format BRUT de X (impression_count, like_count…) que `performance_context` injecte dans le prompt des plans — le
  plan y écrivait la forme normalisée, les plans générés auraient perdu leurs chiffres.
- Telegram : l'API Bot n'expose aucune vue (core.telegram.org/bots/api, relu le 30/09/2026) → aucune métrique, et c'est dit.
- L'engagement est CALCULÉ (likes + 2×commentaires + 3×partages + 2×enregistrements), jamais stocké."""
import json
from datetime import datetime, timedelta
from typing import Awaitable, Callable
from uuid import uuid4

from loguru import logger
from sqlalchemy import or_, select

from app.services import publishers, quota
from app.services.storage import PostMetric, ScheduledPost, async_session_factory

# canal → fetcher(ids distants) → {id: {views, likes, comments, shares, saves[, brut]}}
FETCHERS: dict[str, Callable[[list[str]], Awaitable[dict[str, dict]]]] = {}
_NOTES = {"telegram": "aucune vue exposée par l'API Bot de Telegram — pas de métrique pour ce canal"}


def notes() -> dict:
    lim = quota.LIMITS["x_lecture"]
    n = quota.used("x_lecture")
    x = f"{n}/{lim[1]} lectures ce mois — {lim[2]} ; 10 posts par passe"
    if n >= lim[1]:
        x = "budget de lectures épuisé pour le mois — " + x
    return {**_NOTES, "x": x}


def engagement(m: dict) -> int:
    return (int(m.get("likes", 0)) + 2 * int(m.get("comments", 0))
            + 3 * int(m.get("shares", 0)) + 2 * int(m.get("saves", 0)))


def _remote(p: ScheduledPost, ch: str) -> str | None:
    rid = None
    try:
        rid = (json.loads(p.remote_ids) or {}).get(ch) if p.remote_ids else None
    except (ValueError, TypeError, AttributeError):
        rid = None
    if not rid and ch == "x":
        rid = p.x_post_id                    # publié avant le socle (#24) : x_post_id seul
    return rid or None


def _disponible(ch: str) -> bool:
    entree = publishers._REGISTRY.get(ch)
    return bool(entree and entree[0]())


async def refresh_all(max_per_channel: int = 10) -> dict[str, int]:
    """Une passe : pour chaque canal disponible, les `max_per_channel` derniers posts publiés portant un id distant
    (X : aussi borné par le reste du budget mensuel). Retourne {canal: n mis à jour}."""
    counts: dict[str, int] = {}
    async with async_session_factory() as session:
        res = await session.execute(
            select(ScheduledPost).where(ScheduledPost.status == "posted")
            .where(or_(ScheduledPost.remote_ids.isnot(None), ScheduledPost.x_post_id.isnot(None)))
            .order_by(ScheduledPost.posted_at.desc()).limit(200))
        posts = list(res.scalars().all())
        for ch, fetch in list(FETCHERS.items()):
            if not _disponible(ch):
                continue
            borne = max_per_channel
            if ch == "x":
                borne = min(borne, quota.LIMITS["x_lecture"][1] - quota.used("x_lecture"))
                if borne <= 0:
                    logger.info("metrics x : budget mensuel de lectures épuisé, passe sautée")
                    continue
            pairs = [(p, _remote(p, ch)) for p in posts if _remote(p, ch)][:borne]
            if not pairs:
                continue
            try:
                got = await fetch([rid for _p, rid in pairs])
            except Exception as e:
                logger.warning(f"metrics {ch}: {e}")
                continue
            if ch == "x":
                quota.count("x_lecture", n=len(pairs))
            n = 0
            for p, rid in pairs:
                m = got.get(rid)
                if not m:
                    continue
                session.add(PostMetric(id=str(uuid4()), post_id=p.id, channel=ch, remote_id=rid,
                                       views=int(m.get("views", 0)), likes=int(m.get("likes", 0)),
                                       comments=int(m.get("comments", 0)), shares=int(m.get("shares", 0)),
                                       saves=int(m.get("saves", 0)), raw=json.dumps(m.get("brut", m))))
                if ch == "x":
                    p.metrics = json.dumps(m.get("brut", m))   # performance_context lit le format BRUT de X
                n += 1
            counts[ch] = n
        await session.commit()
    return counts


async def analytics(days: int = 28) -> dict:
    """Dernier instantané par (post, canal) sur `days` jours, agrégé par canal, format et semaine ISO ; `items`
    complet (pour les créneaux, T8) et `top` 5."""
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session_factory() as session:
        posts = {p.id: p for p in (await session.execute(
            select(ScheduledPost).where(ScheduledPost.status == "posted")
            .where(ScheduledPost.posted_at >= since))).scalars().all()}
        rows = (await session.execute(
            select(PostMetric).where(PostMetric.post_id.in_(list(posts) or ["-"]))
            .order_by(PostMetric.fetched_at.asc()))).scalars().all()
    latest: dict[tuple[str, str], PostMetric] = {}
    for r in rows:
        latest[(r.post_id, r.channel)] = r          # ordre ascendant : le dernier gagne
    by_ch: dict = {}
    by_fmt: dict = {}
    by_week: dict = {}
    items = []
    for (pid, ch), r in latest.items():
        p = posts[pid]
        m = {"views": r.views, "likes": r.likes, "comments": r.comments, "shares": r.shares, "saves": r.saves}
        e = engagement(m)
        for bucket, key in ((by_ch, ch), (by_fmt, p.format or "post"), (by_week, p.posted_at.strftime("%G-W%V"))):
            b = bucket.setdefault(key, {"posts": 0, "views": 0, "likes": 0, "comments": 0,
                                        "shares": 0, "saves": 0, "engagement": 0})
            b["posts"] += 1
            b["engagement"] += e
            for k, v in m.items():
                b[k] += v
        items.append({"id": pid, "title": p.title, "channel": ch, "format": p.format,
                      "posted_at": p.posted_at.isoformat() + "Z", **m, "engagement": e})
    items.sort(key=lambda d: d["engagement"], reverse=True)
    return {"days": days, "channels": by_ch, "formats": by_fmt,
            "weeks": [{"week": w, **v} for w, v in sorted(by_week.items())],
            "items": items, "top": items[:5], "quotas": quota.summary(), "notes": notes()}
