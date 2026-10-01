# -*- coding: utf-8 -*-
"""Plan mobile T18 (tâche #58, 02/10/2026) — les dépenses du téléphone COMPTÉES par le PC.

DÉCISION DE L'UTILISATEUR (01/10) : un tir payant fait depuis le téléphone entre dans la table `Depense` (catégorie
« mobile »), donc dans le plafond mensuel (#16) et le tableau réel/estimé (#21). Le plan du 03/09 le mettait dans un
fichier à part : il y aurait échappé au plafond.

Le téléphone tient son JOURNAL de tirs (plafond journalier local, coût affiché et confirmé AVANT le tir) et l'envoie
au retour sur le Wi-Fi. Chaque tir porte un identifiant du téléphone : la référence `mobile:<appareil>:<tir>` le rend
unique — renvoyé après une coupure, il n'est jamais compté deux fois. Le mois est celui de l'HEURE LOCALE du tir,
comme `plafonds.mois_courant()` ; `quand` est l'instant du tir, pas celui de la synchronisation.
"""
import math
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select as _select

from app.services import plafonds as _pl

MAX_TIRS = 200
MAX_USD = 1000.0          # un tir isolé au-delà est une erreur de saisie, pas une dépense
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_MOTEUR = re.compile(r"^[a-z0-9_.-]{1,24}$")


class TropDeTirs(Exception):
    pass


def _nombre(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = float(v)
    return v if math.isfinite(v) else None


def _valider(t) -> tuple[dict | None, str]:
    """Le tir propre, ou la raison du refus."""
    if not isinstance(t, dict):
        return None, "tir illisible (objet attendu)"
    ident = str(t.get("id") or "")
    if not _ID.match(ident):
        return None, "identifiant de tir invalide"
    moteur = str(t.get("moteur") or "").strip().lower()
    if not _MOTEUR.match(moteur):
        return None, "moteur invalide"
    est = _nombre(t.get("estime_usd"))
    if est is None or est <= 0 or est > MAX_USD:
        return None, "estime_usd doit être un nombre > 0 et raisonnable (un tir gratuit ne se compte pas)"
    reel = t.get("reel_usd")
    if reel is not None:
        reel = _nombre(reel)
        if reel is None or reel < 0 or reel > MAX_USD:
            return None, "reel_usd invalide"
    try:
        quand = datetime.fromisoformat(str(t.get("quand") or "").replace("Z", "")).replace(tzinfo=None)
    except ValueError:
        return None, "quand doit être une date ISO (UTC)"
    if quand > datetime.utcnow() + timedelta(hours=1):
        return None, "tir daté dans le futur"
    return {"id": ident, "moteur": moteur, "op": str(t.get("op") or "")[:32], "estime_usd": round(est, 6),
            "reel_usd": round(reel, 6) if reel is not None else None, "quand": quand}, ""


def _mois_local(quand_utc: datetime) -> str:
    return quand_utc.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m")


async def fondre(appareil: dict, tirs) -> dict:
    """Écrit les tirs valides et NEUFS ; rend {inseres, deja, refuses, plafonds}. Un tir refusé n'écrit rien."""
    from app.services.storage import Depense
    if not isinstance(tirs, list):
        raise ValueError("`tirs` doit être une liste")
    if len(tirs) > MAX_TIRS:
        raise TropDeTirs(f"au plus {MAX_TIRS} tirs par envoi")
    prefixe = f"mobile:{str(appareil['id'])[:8]}:"
    inseres, deja, refuses = [], [], []
    async with _pl._registre() as s:
        for t in tirs:
            propre, raison = _valider(t)
            if propre is None:
                refuses.append({"id": str(t.get("id") or "") if isinstance(t, dict) else "", "raison": raison})
                continue
            ref = prefixe + propre["id"]
            if (await s.execute(_select(Depense.id).where(Depense.ref == ref))).first() is not None:
                deja.append(propre["id"])
                continue
            s.add(Depense(quand=propre["quand"], mois=_mois_local(propre["quand"]), moteur=propre["moteur"],
                          categorie="mobile", op=propre["op"], estime_usd=propre["estime_usd"],
                          reel_usd=propre["reel_usd"], ref=ref))
            inseres.append(propre["id"])
        await s.commit()
    e = await _pl.etat()
    return {"inseres": inseres, "deja": deja, "refuses": refuses,
            "plafonds": {"mois": e["mois"], "global": {k: e["global"].get(k) for k in ("effectif_usd", "plafond_usd", "pct")},
                         "alerte": e["alerte"]}}
