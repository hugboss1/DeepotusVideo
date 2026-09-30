"""Séries récurrentes (plan scheduler D2, T14 — tâche #32, 30/09/2026) : une série est une règle (jours de semaine, heure
LOCALE, canaux, format, gabarit de légende) qui se MATÉRIALISE en brouillons. Rien ne part tout seul : les brouillons
attendent la validation par lot (P5), comme tout le reste. Rejouer une matérialisation est sans effet — l'unicité est
(series_id, run_at). Une série retirée ne se matérialise plus ; ses brouillons déjà posés restent (du contenu, pas une
dépendance de la règle)."""
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.services.storage import PostSeries, ScheduledPost, async_session_factory

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _weekdays(raw) -> list[int]:
    """« 0,3 » -> [0, 3]. Lève ValueError (qui nomme le champ) sur un jour illisible, hors 0-6, ou une liste vide."""
    out = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError:
            raise ValueError(f"weekdays : « {part} » n'est pas un jour (0=lundi … 6=dimanche)")
        if not 0 <= n <= 6:
            raise ValueError(f"weekdays : jour hors 0-6 : {n}")
        if n not in out:
            out.append(n)
    if not out:
        raise ValueError("weekdays : au moins un jour (0=lundi … 6=dimanche)")
    return sorted(out)


def _hhmm(raw) -> tuple[int, int]:
    hh, _, mm = str(raw or "09:30").partition(":")
    try:
        h, m = int(hh), int(mm or 0)
    except ValueError:
        raise ValueError(f"heure invalide : {raw} (HH:MM attendu)")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"heure invalide : {raw} (HH:MM attendu)")
    return h, m


def to_dict(s: PostSeries) -> dict:
    return {"id": s.id, "name": s.name, "weekdays": s.weekdays, "time": s.time,
            "channels": [c for c in (s.channels or "").split(",") if c],
            "format": s.format, "caption_template": s.caption_template, "active": s.active,
            "created_at": s.created_at.isoformat() + "Z"}


async def list_series() -> list[dict]:
    async with async_session_factory() as session:
        res = await session.execute(
            select(PostSeries).where(PostSeries.active == 1).order_by(PostSeries.created_at.asc()))
        return [to_dict(s) for s in res.scalars().all()]


async def create(body: dict) -> dict:
    """Lève ValueError sur des jours ou une heure invalides — la route la traduit en 400 qui NOMME le champ fautif."""
    days = _weekdays(body.get("weekdays"))
    h, m = _hhmm(body.get("time") or "09:30")
    s = PostSeries(
        id=str(uuid4()), name=str(body.get("name") or "Série")[:120],
        weekdays=",".join(str(d) for d in days), time=f"{h:02d}:{m:02d}",
        channels=",".join(body.get("channels") or ["x"])[:120],
        format=str(body.get("format") or "image")[:20],
        caption_template=str(body.get("caption_template") or "")[:4000],
        active=1, created_at=datetime.utcnow())
    async with async_session_factory() as session:
        session.add(s)
        await session.commit()
    return to_dict(s)


async def delete(series_id: str) -> bool:
    """Retire la série (active = 0). Les brouillons déjà posés RESTENT."""
    async with async_session_factory() as session:
        res = await session.execute(select(PostSeries).where(PostSeries.id == series_id).where(PostSeries.active == 1))
        s = res.scalar_one_or_none()
        if s is None:
            return False
        s.active = 0
        await session.commit()
        return True


async def materialize(series_id: str, *, weeks: int = 1, start_date: str, tz_offset_minutes: int = 0) -> dict:
    """Pose les brouillons de `weeks` semaines à partir de start_date (date LOCALE, YYYY-MM-DD) ; rien avant ce départ.
    utc = local + tz_offset_minutes (JS getTimezoneOffset), comme materialize_plan. Lève ValueError sur une date
    illisible."""
    base = datetime.fromisoformat(str(start_date))
    async with async_session_factory() as session:
        res = await session.execute(select(PostSeries).where(PostSeries.id == series_id).where(PostSeries.active == 1))
        s = res.scalar_one_or_none()
        if s is None:
            return {"created": 0, "skipped": 0, "error": "série inconnue"}
        days = _weekdays(s.weekdays)
        h, m = _hhmm(s.time)
        existants = {p.run_at for p in (await session.execute(
            select(ScheduledPost).where(ScheduledPost.series_id == series_id))).scalars().all()}
        depart = base.replace(hour=h, minute=m, second=0, microsecond=0)
        created = skipped = 0
        for w in range(max(1, min(52, weeks))):
            lundi = base - timedelta(days=base.weekday()) + timedelta(weeks=w)
            for d in days:
                local = (lundi + timedelta(days=d)).replace(hour=h, minute=m, second=0, microsecond=0)
                if local < depart:
                    continue                      # avant le départ demandé
                run_at = local + timedelta(minutes=tz_offset_minutes)
                if run_at in existants:
                    skipped += 1
                    continue
                cap = (s.caption_template or "").replace("{date}", local.strftime("%Y-%m-%d")).replace(
                    "{weekday}", JOURS[local.weekday()]).replace("{week}", local.strftime("%G-W%V"))
                session.add(ScheduledPost(
                    id=str(uuid4()), title=f"{s.name} — {local.strftime('%Y-%m-%d')}"[:200],
                    caption=cap, channels=s.channels, run_at=run_at,
                    status="draft", mode="assisted", format=s.format, series_id=series_id))
                existants.add(run_at)
                created += 1
        await session.commit()
    return {"created": created, "skipped": skipped}
