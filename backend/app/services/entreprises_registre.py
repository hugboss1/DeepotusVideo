# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 5a : le REGISTRE DES ENTREPRISES, par l'API Recherche
d'entreprises de l'État (https://recherche-entreprises.api.gouv.fr/search ; gratuite, sans clé, ~7 requêtes/s ; paramètres
relus le 28/10/2026 : activite_principale, departement, code_postal, etat_administratif, q, page, per_page).

Il désigne des CIBLES pour la prestation clé en main (studios, agences, éditeurs de jeux…), jamais des fiches : il ne
donne ni e-mail ni site. Minimisation : sociétés actives seulement ; jamais un entrepreneur individuel (nature juridique
1000 : une personne physique) ni une diffusion partielle ; jamais les dirigeants ni l'adresse complète. 429 → un nouvel
essai après 2 s, puis `RegistreIndisponible`. Cache 24 h sur disque (DATA_ROOT/cache/registre). Aucune dépense.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time

from app.config import DATA_ROOT

URL = "https://recherche-entreprises.api.gouv.fr/search"
DELAI = 10.0
CACHE_S = 24 * 3600
PAR_PAGE = 25
_NAF = re.compile(r"^\d{2}\.\d{2}[A-Z]$")
_CP = re.compile(r"^\d{5}$")
_DEP = re.compile(r"^(\d{2}|2A|2B|97\d)$")


class RegistreIndisponible(RuntimeError):
    """Le registre ne répond pas (trop de requêtes, panne) : réessayer plus tard."""


async def _get(url: str, params: dict) -> tuple[int, dict]:
    import httpx
    async with httpx.AsyncClient(timeout=DELAI) as c:
        r = await c.get(url, params=params, headers={"Accept": "application/json"})
        try:
            corps = r.json()
        except ValueError:
            corps = {}
        return r.status_code, corps if isinstance(corps, dict) else {}


_GET = _get                         # couture du banc
_DORMIR = asyncio.sleep             # couture du banc


def _cache(params: dict):
    cle = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:24]
    return DATA_ROOT / "cache" / "registre" / f"{cle}.json"


def _cible(e: dict) -> dict | None:
    if not isinstance(e, dict) or e.get("etat_administratif") != "A":
        return None
    if str(e.get("nature_juridique") or "") == "1000" or e.get("statut_diffusion") != "O":
        return None
    s = e.get("siege") if isinstance(e.get("siege"), dict) else {}
    return {"siren": str(e.get("siren") or ""), "nom": str(e.get("nom_complet") or "")[:200],
            "naf": str(e.get("activite_principale") or ""), "commune": str(s.get("libelle_commune") or ""),
            "code_postal": str(s.get("code_postal") or ""), "tranche_effectif": e.get("tranche_effectif_salarie"),
            "creee_le": e.get("date_creation")}


async def chercher(naf: str | None = None, code_postal: str | None = None, departement: str | None = None,
                   q: str | None = None, page: int = 1) -> list:
    """Les sociétés actives qui correspondent ; ValueError si un critère est fautif ou si aucun n'est donné."""
    params = {"etat_administratif": "A", "per_page": PAR_PAGE, "page": max(1, min(int(page or 1), 20))}
    if naf:
        if not _NAF.match(str(naf).upper()):
            raise ValueError("code NAF invalide (ex. 59.11A)")
        params["activite_principale"] = str(naf).upper()
    if code_postal:
        if not _CP.match(str(code_postal)):
            raise ValueError("code postal invalide (5 chiffres)")
        params["code_postal"] = str(code_postal)
    if departement:
        if not _DEP.match(str(departement).upper()):
            raise ValueError("département invalide (ex. 69, 2A, 974)")
        params["departement"] = str(departement).upper()
    if q:
        params["q"] = str(q).strip()[:100]
    if not any(k in params for k in ("activite_principale", "code_postal", "departement", "q")):
        raise ValueError("au moins un critère : activité (NAF), code postal, département ou nom")
    f = _cache(params)
    try:
        if time.time() - f.stat().st_mtime < CACHE_S:
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    for essai in range(2):
        try:
            statut, corps = await _GET(URL, params)
        except Exception as e:  # noqa: BLE001 — réseau : dit, jamais une liste vide trompeuse
            raise RegistreIndisponible(f"registre des entreprises injoignable ({type(e).__name__}) : réessayez plus tard") from None
        if statut == 429 and essai == 0:
            await _DORMIR(2)
            continue
        if statut != 200:
            raise RegistreIndisponible("registre des entreprises indisponible : réessayez dans un instant")
        out = [c for c in (_cible(e) for e in corps.get("results") or []) if c]
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        return out
    raise RegistreIndisponible("registre des entreprises indisponible : réessayez dans un instant")
