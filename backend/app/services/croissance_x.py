# -*- coding: utf-8 -*-
"""t500 (G10, 26/11/2026) — X, la même boucle : mesurer ses posts X, les comparer à l'habituel, les mettre en ligne en
connaissant leur prix. L'API X est PAYANTE À L'USAGE (décision de l'utilisateur du 26/11 : acceptée, avec le coût par
post affiché au devis et un plafond de dépense à part) ; aucune dépense réelle sans son clic.

- TARIFS : `pricing.DEFAULTS["x_api_usd"]` (table datée, relue sur docs.x.com le 26/11/2026, `pricing.X_API_RELU`),
  corrigeable dans pricing.json. Le devis d'une lecture prend le tarif « Posts: Read » (le plus haut).
- PLAFOND X PROPRE : le plafond du moteur « x » de `plafonds.json` (posé ici par `regler_accord` ou dans Réglages) ;
  toute dépense X passe `plafonds.verifier` catégorie « x » AVANT l'appel : relevés et mises en ligne.
- JALONS : un post X se relève quand son jalon courant (J1, J3, J7, J30 de `croissance`) n'a pas encore d'instantané
  et qu'on est encore dans sa fenêtre (`a_relever`) : on ne paie que les lectures qui comptent pour le multiplicateur.
- RELEVÉ À LA DEMANDE : `devis_releve` (gratuit) puis `relever(max_usd)` (PAYANT : l'accord du devis affiché, puis la
  garde, puis le fetcher X de `metrics_service.FETCHERS`).
- JAMAIS AUTOMATIQUE SANS ACCORD : la passe quotidienne de `metrics_service.refresh_all` saute X tant que l'accord
  automatique n'est pas ENREGISTRÉ (`accord.json`, daté) ; l'accord exige un plafond X ; chaque passe passe la garde
  (`garder_auto`), sans confirmation possible : au plafond, elle s'arrête.
- MISE EN LIGNE : `devis_publication` (par message : un post, un post avec lien, plus cher, un média) ;
  `garder_publication` est appelé par le publieur X juste avant `publish_x`.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from uuid import uuid4

from loguru import logger

from app.config import DATA_ROOT
from app.services import croissance, plafonds, pricing

CATEGORIE = "x"
MOTEUR = "x"
MAX_RELEVE = 100                 # ids par appel de l'API X (GET /2/tweets?ids=…)
EPS_USD = 0.0001
RELU = pricing.X_API_RELU
_LIEN = re.compile(r"(?i)\bhttps?://\S+|\bwww\.\S+")


class CoutChange(ValueError):
    def __init__(self, message: str, usd: float):
        super().__init__(message)
        self.usd = usd


class RefusX(ValueError):
    pass


# ---- tarifs et devis --------------------------------------------------------------------------------------------------

def tarifs() -> dict:
    t = pricing.load().get("x_api_usd")
    return dict(t) if isinstance(t, dict) else dict(pricing.DEFAULTS["x_api_usd"])


def op_lectures(n: int) -> dict:
    return {"kind": "x_api", "lectures": int(n)}


def a_lien(texte: str) -> bool:
    return bool(_LIEN.search(str(texte or "")))


def op_publication(messages: list, medias: int = 0) -> dict:
    liens = sum(1 for m in messages if a_lien(m))
    return {"kind": "x_api", "posts": len(messages) - liens, "liens": liens, "medias": int(medias)}


def devis_publication(messages: list, medias: int = 0) -> dict:
    """Le coût de mise en ligne d'un post ou d'un fil, message par message (pur)."""
    t = tarifs()
    msgs = [str(m or "") for m in messages or []]
    lignes = [{"n": i + 1, "caracteres": len(m), "lien": a_lien(m),
               "usd": round(t["post_lien"] if a_lien(m) else t["post"], 4)} for i, m in enumerate(msgs)]
    usd = round(sum(l["usd"] for l in lignes) + max(0, int(medias)) * t["media"], 4)
    return {"messages": lignes, "medias": max(0, int(medias)), "usd": usd, "tarifs": t, "relu": RELU}


async def devis_publication_post(post_id: str) -> dict:
    """Le devis de mise en ligne X d'un post du Planificateur et de la suite de son fil (thread_of)."""
    from sqlalchemy import select
    from app.services.storage import ScheduledPost, async_session_factory
    async with async_session_factory() as s:
        p = await s.get(ScheduledPost, str(post_id)[:36])
        if p is None:
            raise LookupError("Post introuvable.")
        racine = p.thread_of or p.id
        tete = p if p.id == racine else await s.get(ScheduledPost, racine) or p
        suite = list((await s.execute(select(ScheduledPost).where(ScheduledPost.thread_of == racine))).scalars().all())
    fil = [tete] + sorted(suite, key=lambda x: x.thread_index or 0)
    medias = sum(1 for x in fil if x.job_id or x.source_image)
    return {"post_id": tete.id, **devis_publication([x.caption or x.title or "" for x in fil], medias)}


# ---- accord et plafond X ----------------------------------------------------------------------------------------------

def _fichier_accord():
    return DATA_ROOT / "croissance" / "x_accord.json"


def lire_accord() -> dict:
    try:
        d = json.loads(_fichier_accord().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d = d if isinstance(d, dict) else {}
    return {"auto": d.get("auto") is True, "le": d.get("le"),
            "plafond_usd": float(plafonds.charger()["par_moteur"].get(MOTEUR) or 0.0)}


def regler_accord(auto, plafond_usd) -> dict:
    """Enregistre (daté) l'accord du relevé automatique et pose le plafond X propre (moteur « x » ; 0 = aucun)."""
    if not isinstance(auto, bool):
        raise RefusX("auto : vrai ou faux.")
    if isinstance(plafond_usd, bool) or not isinstance(plafond_usd, (int, float)) or not 0 <= plafond_usd <= 10_000 \
            or plafond_usd != plafond_usd:
        raise RefusX("Plafond X hors bornes : de 0 à 10 000 $.")
    if auto and plafond_usd <= 0:
        raise RefusX("Le relevé automatique de X demande un plafond X du mois (en dollars).")
    pm = dict(plafonds.charger()["par_moteur"])
    if plafond_usd > 0:
        pm[MOTEUR] = float(plafond_usd)
    else:
        pm.pop(MOTEUR, None)
    plafonds.enregistrer({"par_moteur": pm})
    f = _fichier_accord()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps({"auto": auto, "le": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
                   encoding="utf-8")
    os.replace(tmp, f)
    logger.info(f"croissance x : accord du relevé automatique {'donné' if auto else 'retiré'}, plafond X {plafond_usd} $")
    return lire_accord()


def accord_auto() -> bool:
    return lire_accord()["auto"]


async def garder_auto(n: int) -> dict:
    """La garde de la passe quotidienne : l'accord ENREGISTRÉ, puis le plafond (jamais de confirmation)."""
    if not accord_auto():
        raise RefusX("Aucun accord enregistré pour relever X automatiquement.")
    return await plafonds.verifier(op_lectures(n), CATEGORIE, ref="x_releve_auto", confirme=False)


async def garder_publication(messages: list, medias: int = 0, espace_id: str | None = None) -> dict:
    """La garde d'une mise en ligne X (appelée par le publieur juste avant publish_x)."""
    return await plafonds.verifier(op_publication(messages, medias), CATEGORIE, ref="x_publication",
                                   espace_id=espace_id)


# ---- jalons et relevé -------------------------------------------------------------------------------------------------

def _remotes(p) -> list[tuple[str | None, str]]:
    """[(compte, id distant X)] d'un post : la clé « x » (ou x_post_id d'avant le socle) et les clés « x:<compte> »."""
    out = []
    try:
        rem = json.loads(p.remote_ids) if p.remote_ids else {}
    except (ValueError, TypeError):
        rem = {}
    rem = rem if isinstance(rem, dict) else {}
    if rem.get("x"):
        out.append((None, str(rem["x"])))
    elif p.x_post_id:
        out.append((None, str(p.x_post_id)))
    for k, v in rem.items():
        if isinstance(k, str) and k.startswith("x:") and v:
            out.append((k.split(":", 1)[1], str(v)))
    return out


async def a_relever(maintenant: datetime | None = None) -> list[dict]:
    """Les posts X publiés dont le jalon courant n'a pas d'instantané et dont la fenêtre est encore ouverte."""
    from sqlalchemy import or_, select
    from app.services.storage import PostMetric, ScheduledPost, async_session_factory
    maintenant = maintenant or datetime.utcnow()
    async with async_session_factory() as s:
        posts = list((await s.execute(
            select(ScheduledPost).where(ScheduledPost.status == "posted").where(ScheduledPost.posted_at.isnot(None))
            .where(or_(ScheduledPost.remote_ids.isnot(None), ScheduledPost.x_post_id.isnot(None)))
            .order_by(ScheduledPost.posted_at.desc()).limit(2000))).scalars().all())
        ids = [p.id for p in posts]
        snaps: dict = {}
        if ids:
            for r in (await s.execute(select(PostMetric).where(PostMetric.post_id.in_(ids))
                                      .where(PostMetric.channel == "x"))).scalars().all():
                snaps.setdefault(r.post_id, []).append({"fetched_at": r.fetched_at})
    dus = []
    for p in posts:
        rem = _remotes(p)
        if not rem:
            continue
        age = (maintenant - p.posted_at).total_seconds() / 86400.0
        k = croissance.jalon_courant(age)
        if k is None or age > croissance._borne(k):
            continue
        if croissance.jalons_mesures(p.posted_at, snaps.get(p.id, []))[k] is not None:
            continue
        for compte, rid in rem:
            dus.append({"post_id": p.id, "remote_id": rid, "compte": compte, "jalon": k, "titre": (p.title or "")[:120],
                        "espace_id": getattr(p, "espace_id", None)})
    return dus[:MAX_RELEVE]


async def devis_releve() -> dict:
    """Le devis GRATUIT du prochain relevé X (aucun appel)."""
    dus = await a_relever()
    t = tarifs()
    return {"n": len(dus), "usd": round(len(dus) * t["lecture"], 4), "posts": dus, "tarifs": t, "relu": RELU,
            "accord": lire_accord()}


async def _ecrire_mesures(dus: list[dict], got: dict) -> int:
    from app.services.storage import PostMetric, ScheduledPost, async_session_factory
    n = 0
    async with async_session_factory() as s:
        for d in dus:
            m = got.get(d["remote_id"])
            if not m:
                continue
            s.add(PostMetric(id=str(uuid4()), post_id=d["post_id"], channel="x", remote_id=d["remote_id"],
                             views=int(m.get("views", 0)), likes=int(m.get("likes", 0)),
                             comments=int(m.get("comments", 0)), shares=int(m.get("shares", 0)),
                             saves=int(m.get("saves", 0)), raw=json.dumps(m.get("brut", m))))
            if d["compte"] is None:
                p = await s.get(ScheduledPost, d["post_id"])
                if p is not None:
                    p.metrics = json.dumps(m.get("brut", m))      # performance_context lit le format BRUT de X
            n += 1
        await s.commit()
    return n


async def relever(max_usd) -> dict:
    """Le relevé PAYANT des posts X dus : l'accord (`max_usd` = le montant du devis affiché), la garde « x », puis le
    fetcher X, compte par compte. Rend {releves, usd, lus}."""
    from app.services import comptes as _cpt
    from app.services import metrics_service as MS
    from app.services import quota
    if isinstance(max_usd, bool) or not isinstance(max_usd, (int, float)) or max_usd < 0 or max_usd != max_usd:
        raise ValueError("Accord manquant : max_usd (le montant du devis affiché) est requis.")
    dus = await a_relever()
    usd = round(len(dus) * tarifs()["lecture"], 4)
    if not dus:
        return {"releves": 0, "usd": 0.0, "lus": 0}
    if usd > float(max_usd) + EPS_USD:
        raise CoutChange("Le coût a changé : il dépasse le montant accepté.", usd)
    await plafonds.verifier(op_lectures(len(dus)), CATEGORIE, ref="x_releve")
    fetch = MS.FETCHERS.get("x")
    if fetch is None:
        raise RuntimeError("Le relevé X n'est pas disponible (adaptateur absent).")
    par_compte: dict = {}
    for d in dus:
        par_compte.setdefault(d["compte"], []).append(d)
    got: dict = {}
    for compte, liste in par_compte.items():
        ids = [d["remote_id"] for d in liste]
        if compte is None:
            got.update(await fetch(ids) or {})
            continue
        try:
            with _cpt.sous_compte(compte):
                got.update(await fetch(ids) or {})
        except KeyError:
            logger.warning("croissance x : compte X supprimé depuis la publication, posts non relus")
    quota.count("x_lecture", n=len(dus))
    n = await _ecrire_mesures(dus, got)
    logger.info(f"croissance x : {n}/{len(dus)} post(s) X relus, {usd:.4f} $ (devis)")
    return {"releves": n, "usd": usd, "lus": len(dus)}
# ---- fin du relevé ------------------------------------------------------------------------------------------------------
