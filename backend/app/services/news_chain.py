# -*- coding: utf-8 -*-
"""La chaine article -> post (plan 2026-09-03 T12-T13, tache #35 du suivi, 30/09/2026).

Reponse 5 de R8 : choix des articles, script propose, forme, creneau — l'utilisateur ne fait que valider.

Decisions de l'utilisateur (30/09) : (1) `preparer()` est GRATUITE — classement deterministe, voix par les mots du
sujet, script en brouillon SANS polissage LLM (`polir=False`) ; le polissage se demande post par post (`polir()`,
derriere la garde des plafonds de sa route) ; (2) chaque post valide recoit le reel « cartes » rendu localement
(ffmpeg, gratuit) : `valider()` programme le post avec son `job_id`, la route lance le rendu, et la couverture
(`news_memory`) est notee au rendu REUSSI — jamais deux fois, jamais pour un reel qui n'existe pas.
Le creneau propose est le prochain creneau du Scheduler pour le premier canal (`schedule_slots`, heures locales).
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from loguru import logger

ARTICLES_MAX = 8


def _creneau_propose(canal: str = "x", maintenant: datetime | None = None) -> str:
    """Le prochain creneau du canal (heures LOCALES du Scheduler, converties en UTC), demain s'ils sont passes."""
    from app.services import schedule_slots
    ref = maintenant or datetime.now(timezone.utc)
    heures = schedule_slots.load().get(canal) or ["18:00"]
    decalage = timedelta(minutes=schedule_slots.tz_offset())      # UTC - local (getTimezoneOffset)
    local_ref = (ref - decalage).replace(tzinfo=None)
    for jours in (0, 1, 2):
        base = (local_ref + timedelta(days=jours)).replace(hour=0, minute=0, second=0, microsecond=0)
        for hhmm in sorted(heures):
            h, m = (int(x) for x in hhmm.split(":")[:2])
            local = base.replace(hour=h, minute=m)
            if local > local_ref:
                return (local + decalage).replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
    return (ref + timedelta(days=1)).isoformat(timespec="seconds")


async def preparer(engine, *, forme: str, brief: str = "", articles_max: int = 3, language: str = "EN",
                   creneau: str | None = None, voice_mode: str | None = None, canal: str = "x") -> dict:
    """Assemble le lot du jour sans rien ecrire et sans appel payant. Leve ValueError avec un motif lisible."""
    import asyncio

    from app.models.schemas import Language, VoiceMode
    from app.services import news_filter, news_forms, news_memory, news_rank, news_trends
    from app.services.news_caption import bloc_sources
    from app.services.news_service import news_service
    from app.services.news_voice import choisir_mode

    if forme not in news_forms.IDS:
        raise ValueError(f"forme de reel inconnue : {forme!r} — les formes sont " + ", ".join(news_forms.IDS))
    n = max(1, min(ARTICLES_MAX, int(articles_max)))
    bruts = news_service.get_items().get("items") or []
    gardes, _motifs = news_filter.filtrer(bruts, news_filter.lire_reglages())
    if not gardes:
        raise ValueError("aucun article ne passe le filtre : rafraichis les flux ou elargis la fenetre de fraicheur")
    gardes = news_trends.marquer_tendances(news_memory.marquer(gardes))
    classes = await asyncio.to_thread(news_rank.classer, gardes, brief=brief,
                                      penalites=news_memory.penalites_de_source())
    choisis = classes[:n]
    mode, pourquoi = await asyncio.to_thread(choisir_mode, choisis, force=voice_mode)
    langue = Language.FR if str(language).upper().startswith("FR") else Language.EN
    base = await asyncio.to_thread(engine.generate_news_script, choisis, voice_mode=VoiceMode(mode), language=langue,
                                   max_words=90, angle=brief or None, polir=False)
    ligne = bloc_sources(choisis, langue=langue.value)
    caption = (base.suggested_caption or "").rstrip()
    if ligne:
        caption = f"{caption}\n\n{ligne}"
    cout = news_forms.estimer(forme, choisis, {"chars": len(base.script)})
    logger.info(f"news chain: lot de {len(choisis)} articles, forme {forme}, mode {mode}, estime {cout['total_usd']:.4f} $")
    return {"articles": choisis, "script": base.script, "caption": caption, "sources_line": ligne, "forme": forme,
            "cout": cout, "creneau": creneau or _creneau_propose(canal), "voice_mode": mode,
            "voice_mode_reason": pourquoi, "language": langue.value, "poli": False}


def polir(engine, script: str, *, voice_mode: str | None = None, language: str = "EN", max_words: int = 90) -> tuple:
    """Le polissage LLM d'un script du lot (PAYANT). La route qui l'appelle passe D'ABORD la garde des plafonds.
    Rend (script, fournisseur) ; sans cle ou sur refus du fournisseur, (script inchange, "")."""
    from app.models.schemas import Language, VoiceMode
    if not (script or "").strip():
        raise ValueError("script vide : rien a polir")
    vm = VoiceMode(voice_mode) if voice_mode in {m.value for m in VoiceMode} else None
    langue = Language.FR if str(language).upper().startswith("FR") else Language.EN
    poli, prov = engine.polish_news_script(script, voice_mode=vm, language=langue, max_words=max_words)
    return (poli, prov) if poli else (script, "")


def _quand(brut: str) -> datetime:
    try:
        quand = datetime.fromisoformat(str(brut or "").replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"creneau illisible : {brut!r} — attendu une date ISO 8601")
    return quand if quand.tzinfo else quand.replace(tzinfo=timezone.utc)


async def valider(lot: dict, *, channels: list[str] | None = None, mode: str = "assisted") -> dict:
    """Programme le lot en UN post, avec le `job_id` du reel « cartes » a rendre. Rend {post_id, job_id, articles}.
    Le creneau et les articles sont verifies AVANT toute ecriture. N'ecrit pas la couverture : c'est le rendu reussi
    qui la note (`rendre_et_noter`)."""
    from app.services import marketing
    from app.services.storage import ScheduledPost, async_session_factory

    articles = [a for a in (lot.get("articles") or []) if str(a.get("title") or "").strip()]
    if not articles:
        raise ValueError("le lot ne porte aucun article : rien a programmer")
    quand = _quand(lot.get("creneau")).astimezone(timezone.utc)
    canaux = [c for c in (channels or ["x"]) if str(c).strip()] or ["x"]
    titre = str(articles[0].get("title") or "News deepotus")[:200]
    ids = await marketing.materialize_plan(
        [{"title": titre, "caption": lot.get("caption") or "", "channels": canaux, "day_offset": 0,
          "time": quand.strftime("%H:%M"), "format": "reel", "hook": (lot.get("script") or "")[:200],
          "script_idea": lot.get("script") or ""}],
        start_date=quand.date().isoformat(), tz_offset_minutes=0, mode=mode)
    post_id, job_id = ids[0], str(uuid4())
    async with async_session_factory() as session:
        p = await session.get(ScheduledPost, post_id)
        p.job_id = job_id
        await session.commit()
    logger.info(f"news chain: lot valide -> post {post_id}, reel cartes {job_id}")
    return {"post_id": post_id, "job_id": job_id, "articles": articles}


async def rendre_et_noter(pipeline, articles: list[dict], *, job_id: str, post_id: str) -> bool:
    """Rend le reel « cartes » (ffmpeg local, gratuit) du post, puis note ses sujets en couverture — seulement si le
    rendu a reussi. Ne leve pas : un echec reste lisible dans le job (statut failed)."""
    from app.services import news_memory
    try:
        await pipeline.run_news_illustration(articles, per_card_s=3.5, engine="ffmpeg", job_id=job_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"news chain: reel cartes {job_id} en echec ({e}) - couverture non notee")
        return False
    news_memory.noter_couverture(articles, post_id=post_id)
    return True
