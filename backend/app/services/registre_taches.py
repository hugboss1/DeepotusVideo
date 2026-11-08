# -*- coding: utf-8 -*-
"""t434 (lot M1 « Méthodes », 08/11/2026) — B7 : le REGISTRE COÛT/TEMPS des tâches d'agent métier (conception
docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §4).

Chaque étape d'une tâche (`tache` = id de conversation, de méthode lancée…) est OUVERTE avec son devis et les lignes
`Depense` que la garde des plafonds vient d'écrire, puis FERMÉE avec son statut (et le réel quand il est connu) :
sa durée en découle. `lire(tache)` rend les étapes et les totaux (estimé, réel connu, durée). Le réel d'une étape
sans réel posé est lu sur ses lignes `Depense` (`noter_reel*` des fournisseurs). Local et gratuit.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import select

STATUTS = ("en_cours", "fait", "echec", "annule")
MAX_ETAPES = 500


@asynccontextmanager
async def _session():
    """Une session dont la table `etapes_registre` EXISTE (créée à la volée, comme `depenses` dans plafonds)."""
    from app.services.storage import EtapeRegistre, async_session_factory
    async with async_session_factory() as s:
        conn = await s.connection()
        await conn.run_sync(lambda sc: EtapeRegistre.__table__.create(sc, checkfirst=True))
        yield s


def _cle(tache: str) -> str:
    t = " ".join(str(tache or "").split())[:64] if isinstance(tache, str) else ""
    if not t:
        raise ValueError("Identifiant de tâche manquant.")
    return t


async def ouvrir(tache: str, etape: str, estime_usd: float = 0.0, depenses: list[int] | None = None,
                 espace_id: str | None = None) -> int:
    """Ouvre une étape ; rend son id."""
    from app.services.storage import EtapeRegistre
    e = EtapeRegistre(tache=_cle(tache), etape=" ".join(str(etape or "").split())[:80],
                      estime_usd=max(0.0, float(estime_usd or 0.0)),
                      depenses=json.dumps([int(i) for i in depenses or []][:50]),
                      espace_id=(str(espace_id)[:40] if espace_id else None))
    async with _session() as s:
        s.add(e)
        await s.commit()
        return e.id


async def fermer(etape_id: int, statut: str = "fait", reel_usd: float | None = None) -> dict | None:
    """Ferme une étape (statut fait | echec | annule) ; rend {id, duree_s} ou None si elle n'existe pas."""
    from app.services.storage import EtapeRegistre
    if statut not in STATUTS[1:]:
        raise ValueError("Statut d'étape inconnu.")
    async with _session() as s:
        e = await s.get(EtapeRegistre, int(etape_id))
        if e is None:
            return None
        e.fin = datetime.utcnow()
        e.statut = statut
        if reel_usd is not None:
            e.reel_usd = max(0.0, float(reel_usd))
        await s.commit()
        return {"id": e.id, "duree_s": round((e.fin - e.debut).total_seconds(), 3)}


async def lire(tache: str) -> dict:
    """Les étapes de la tâche (les plus anciennes d'abord) et les totaux : estimé, réel connu (posé ou lu sur les
    lignes Depense), durée cumulée des étapes fermées, nombre d'étapes en cours."""
    from app.services.storage import Depense, EtapeRegistre
    t = _cle(tache)
    async with _session() as s:
        etapes = (await s.execute(select(EtapeRegistre).where(EtapeRegistre.tache == t)
                                  .order_by(EtapeRegistre.debut, EtapeRegistre.id).limit(MAX_ETAPES))).scalars().all()
        out = []
        for e in etapes:
            reel = e.reel_usd
            ids = json.loads(e.depenses or "[]")
            if reel is None and ids:
                try:
                    lignes = (await s.execute(select(Depense).where(Depense.id.in_(ids)))).scalars().all()
                except Exception:  # noqa: BLE001 — table des dépenses absente : pas de réel connu
                    lignes = []
                connus = [l.reel_usd for l in lignes if l.reel_usd is not None]
                reel = round(sum(connus), 4) if connus and len(connus) == len(lignes) else None
            out.append({"id": e.id, "etape": e.etape, "statut": e.statut, "debut": e.debut.isoformat(timespec="seconds"),
                        "fin": e.fin.isoformat(timespec="seconds") if e.fin else None,
                        "duree_s": round((e.fin - e.debut).total_seconds(), 3) if e.fin else None,
                        "estime_usd": round(e.estime_usd, 4), "reel_usd": reel, "depenses": ids})
    fermees = [x for x in out if x["duree_s"] is not None]
    return {"tache": t, "etapes": out,
            "totaux": {"estime_usd": round(sum(x["estime_usd"] for x in out), 4),
                       "reel_usd": round(sum(x["reel_usd"] for x in out if x["reel_usd"] is not None), 4),
                       "reel_complet": all(x["reel_usd"] is not None for x in out if x["estime_usd"] > 0),
                       "duree_s": round(sum(x["duree_s"] for x in fermees), 3),
                       "en_cours": sum(1 for x in out if x["statut"] == "en_cours"), "n": len(out)}}
