# -*- coding: utf-8 -*-
"""t365-t368 (28/10/2026) — ce que devient une collecte Apify acceptée, selon le BUT de sa carte (plan
docs/superpowers/plans/2026-10-28-veille-apify-t365-t369.md, décision 1). Le dépôt JSON brut du socle t364 reste ; ce
module en tire ce que l'agent et les écrans utilisent :
  leads   (t365) : des CIBLES {nom, site, note, categorie, ville} — ni téléphone ni avis — et le site PUBLIC de chaque
                   cible déposé comme URL, lisible ensuite par `prospects_chercher(source="entreprise")` (lecteur t354) ;
Rien ici n'écrit de fiche ni n'envoie quoi que ce soit.
"""
from __future__ import annotations

BUTS = ("leads",)
MAX_CIBLES = 100


def _texte(v, n: int = 200) -> str:
    return str(v or "").strip()[:n] if isinstance(v, (str, int, float)) else ""


async def _site_public(u) -> str:
    """L'URL normalisée si c'est un site public http(s), sinon "" (hôte local, javascript:, illisible)."""
    from app.services import agent_outils as AO
    n = AO._url_normale(str(u or ""))
    if not n:
        return ""
    try:
        AO._url_sure(n)
    except Exception:  # noqa: BLE001 — hôte local ou interdit
        return ""
    return n


async def _leads(cid: str, args: dict, items: list) -> dict:
    from app.services import agent_outils as AO
    ville = _texte((args.get("entree") or {}).get("locationQuery"), 120)
    cibles, deposes = [], set()
    for it in items[:MAX_CIBLES]:
        site = await _site_public(it.get("website"))
        note = it.get("totalScore")
        cibles.append({"nom": _texte(it.get("title")), "site": site,
                       "note": note if isinstance(note, (int, float)) and not isinstance(note, bool) else None,
                       "categorie": _texte(it.get("categoryName"), 120), "ville": _texte(it.get("city"), 120) or ville})
        if site and site not in deposes:
            deposes.add(site)
            await AO.enregistrer_depot(cid, "url", site)
    return {"cibles": cibles}


async def traiter(but, cid: str, args: dict, items: list) -> dict:
    """Ce que le fait « terminee » de la carte porte en plus ; {} pour un but inconnu ou absent."""
    if but == "leads":
        return await _leads(cid, args, items)
    return {}
