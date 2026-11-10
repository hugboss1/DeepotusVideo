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

from app.services import croissance, publishers, quota
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
        # t204 (Espaces de marque E4) : les publications PAR COMPTE (clé « canal:id » de remote_ids) sont lues avec les
        # identifiants de CE compte ; la métrique garde le canal (les analyses agrègent par canal, comme avant).
        from app.services import comptes as _cpt
        par_compte: dict = {}
        for p in posts:
            try:
                rem = json.loads(p.remote_ids) if p.remote_ids else {}
            except (ValueError, TypeError):
                rem = {}
            for k, rid in (rem or {}).items() if isinstance(rem, dict) else ():
                if ":" in k and rid and k.split(":", 1)[0] in FETCHERS:
                    par_compte.setdefault(tuple(k.split(":", 1)), []).append((p, rid))
        for (ch, cid), pairs in par_compte.items():
            try:
                bloc = _cpt.sous_compte(cid)
                bloc.__enter__()
            except KeyError:
                continue                             # compte supprimé depuis : plus d'identifiants pour lire
            try:
                if not _disponible(ch):
                    continue
                borne = max_per_channel
                if ch == "x":
                    borne = min(borne, quota.LIMITS["x_lecture"][1] - quota.used("x_lecture"))
                    if borne <= 0:
                        continue
                pairs = pairs[:borne]
                try:
                    got = await FETCHERS[ch]([rid for _p, rid in pairs])
                except Exception as e:
                    logger.warning(f"metrics {ch}:{cid}: {e}")
                    continue
            finally:
                bloc.__exit__(None, None, None)
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
                n += 1
            counts[f"{ch}:{cid}"] = n
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
                      "espace_id": getattr(p, "espace_id", None),   # t492 : le tableau filtre par espace
                      "posted_at": p.posted_at.isoformat() + "Z", **m, "engagement": e})
    cr = _croissance(*(await _historique()))
    for d in items:
        d["croissance"] = cr.get((d["id"], d["channel"])) or dict(_SANS, raison="sans_releve")
    items.sort(key=lambda d: d["engagement"], reverse=True)
    return {"days": days, "channels": by_ch, "formats": by_fmt,
            "weeks": [{"week": w, **v} for w, v in sorted(by_week.items())],
            "items": items, "top": items[:5], "quotas": quota.summary(), "notes": notes(),
            "seuil_gagnant": croissance.SEUIL_GAGNANT,
            "gagnants": sorted((d for d in items if d["croissance"].get("gagnant")),
                               key=lambda d: d["croissance"]["multiplicateur"], reverse=True)}


# ---- t491 (lot G1, 09/11/2026) : la croissance d'un post contre l'habituel de son compte --------------------------------
_SANS = {"jalons": {f"j{j}": None for j in croissance.JALONS}, "jalon": None, "vues": None, "habituel": None,
         "multiplicateur": None, "gagnant": False, "recul": 0, "visionnage_s": None, "raison": None}
MAX_HISTORIQUE = 2000


async def _historique() -> tuple[list, list]:
    """Les posts publiés (les MAX_HISTORIQUE plus récents) et TOUS leurs instantanés, pour comparer à âge égal."""
    async with async_session_factory() as session:
        posts = list((await session.execute(
            select(ScheduledPost).where(ScheduledPost.status == "posted").where(ScheduledPost.posted_at.isnot(None))
            .order_by(ScheduledPost.posted_at.desc()).limit(MAX_HISTORIQUE))).scalars().all())
        rows = list((await session.execute(
            select(PostMetric).where(PostMetric.post_id.in_([p.id for p in posts] or ["-"]))
            .order_by(PostMetric.fetched_at.asc()))).scalars().all())
    return posts, rows


def _visionnage(raw: str | None):
    try:
        ms_ = (json.loads(raw) or {}).get("avg_watch_ms") if raw else None
    except (ValueError, TypeError, AttributeError):
        return None
    return round(ms_ / 1000.0, 1) if isinstance(ms_, (int, float)) and not isinstance(ms_, bool) and ms_ > 0 else None


def _croissance(posts: list, rows: list, maintenant: datetime | None = None) -> dict:
    """{(post, canal): croissance}. L'habituel d'un post = ses prédécesseurs du même canal, du même format et du même
    espace (un client ne se compare pas à un autre), lus au MÊME jalon que lui. Pure : aucune lecture."""
    maintenant = maintenant or datetime.utcnow()
    par_post = {p.id: p for p in posts}
    snaps: dict[tuple, list] = {}
    for r in rows:
        if r.post_id in par_post:
            snaps.setdefault((r.post_id, r.channel), []).append(
                {"fetched_at": r.fetched_at, "views": r.views, "raw": r.raw})
    jal = {k: croissance.jalons_mesures(par_post[k[0]].posted_at, v) for k, v in snaps.items()}
    familles: dict[tuple, list] = {}
    for (pid, ch) in snaps:
        p = par_post[pid]
        familles.setdefault((ch, p.format or "post", getattr(p, "espace_id", None)), []).append(pid)
    for ids in familles.values():
        ids.sort(key=lambda i: par_post[i].posted_at)
    out = {}
    for (ch, _fmt, _eid), ids in familles.items():
        for rang, pid in enumerate(ids):
            p, j = par_post[pid], jal[(pid, ch)]
            c = dict(_SANS, jalons={f"j{k}": (v or {}).get("views") for k, v in j.items()})
            c["visionnage_s"] = _visionnage(snaps[(pid, ch)][-1]["raw"])
            cible = croissance.jalon_courant((maintenant - p.posted_at).total_seconds() / 86400.0)
            if cible is None:
                out[(pid, ch)] = dict(c, raison="trop_tot")
                continue
            # le jalon atteint le plus avancé pour lequel CE post a un relevé
            lus = [k for k in croissance.JALONS if k <= cible and j[k] is not None]
            if not lus:
                out[(pid, ch)] = dict(c, raison="sans_releve")
                continue
            k = lus[-1]
            avant = [(jal[(i, ch)][k] or {}).get("views") for i in ids[:rang]]
            recul = sum(1 for v in avant if v is not None)
            h = croissance.habituel(avant)
            m = croissance.multiplicateur_habituel(j[k]["views"], avant)
            out[(pid, ch)] = dict(c, jalon=k, vues=j[k]["views"], habituel=h, multiplicateur=m, recul=recul,
                                  gagnant=croissance.gagnant(m),
                                  raison=None if m is not None else "peu_de_recul")
    return out


async def croissance_posts(post_ids: list[str]) -> dict:
    """{post: {canal: croissance}} pour les posts demandés qui ont au moins un instantané (l'agent, le compagnon)."""
    voulu = set(post_ids or [])
    out: dict = {}
    for (pid, ch), c in _croissance(*(await _historique())).items():
        if pid in voulu:
            out.setdefault(pid, {})[ch] = c
    return out


# ---- t492 (lot G2, 09/11/2026) : le tableau « Croissance » (totaux, meilleurs posts, gagnants, régularité) ----------------
_CLES = ("views", "likes", "comments", "shares", "saves", "engagement")
TOP_TABLEAU = 6


async def tableau(days: int = 30, espace_id: str | None = None, tz_min: int = 0) -> dict:
    """Ce que l'écran Croissance affiche pour `days` jours, tous espaces ou UN espace. Lecture seule, aucun appel."""
    a = await analytics(days)
    items = [d for d in a["items"] if not espace_id or d.get("espace_id") == espace_id]
    totaux = {"posts": len({d["id"] for d in items}), **{k: sum(int(d.get(k) or 0) for d in items) for k in _CLES}}
    canaux: dict = {}
    for d in items:
        c = canaux.setdefault(d["channel"], {"posts": 0, **{k: 0 for k in _CLES}})
        c["posts"] += 1
        for k in _CLES:
            c[k] += int(d.get(k) or 0)
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session_factory() as session:
        q = (select(ScheduledPost.posted_at).where(ScheduledPost.status == "posted")
             .where(ScheduledPost.posted_at >= since))
        if espace_id:
            q = q.where(ScheduledPost.espace_id == espace_id)
        dates = [r[0] for r in (await session.execute(q)).all()]
    return {"days": days, "espace_id": espace_id or None, "totaux": totaux, "canaux": canaux,
            "top": sorted(items, key=lambda d: d["views"], reverse=True)[:TOP_TABLEAU],
            "gagnants": [d for d in a["gagnants"] if not espace_id or d.get("espace_id") == espace_id],
            "seuil_gagnant": a["seuil_gagnant"],
            "regularite": croissance.regularite(dates, datetime.utcnow(), days, tz_min),
            "notes": a["notes"]}
