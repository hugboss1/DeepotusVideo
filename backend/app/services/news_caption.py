# -*- coding: utf-8 -*-
"""La ligne de sources posee en LEGENDE (plan 2026-09-03 T9, tache #34 du suivi, 30/09/2026).

Reponse 2 de R8 : les sources vont en legende, jamais a l'ecran (bac ecarte E1). La ligne est construite par le
pipeline, pas par le LLM : elle doit etre exacte, et un modele qui « resume » une URL invente un lien.
"""
from datetime import datetime
from urllib.parse import urlparse

MEDIAS_MAX = 4


def _domaine(lien: str) -> str:
    try:
        h = urlparse(str(lien or "")).netloc
    except ValueError:
        return ""
    h = h.rsplit("@", 1)[-1].split(":", 1)[0].lower()
    return h[4:] if h.startswith("www.") else h


def _date(v: str) -> str:
    try:
        return datetime.fromisoformat(str(v or "")).date().isoformat()
    except ValueError:
        return ""


def _entrees(items: list[dict]) -> list[tuple[str, str, str]]:
    """(media, date, domaine) sans doublon de media, dans l'ordre d'arrivee. Les medias FONDUS par le
    dedoublonnage (cle `doublons`) comptent : ils ont couvert le meme sujet, ils meritent la citation."""
    vus: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for it in items:
        candidats = [(it.get("source_name"), it.get("published"), it.get("link"))]
        for d in (it.get("doublons") or []):
            if isinstance(d, dict):
                candidats.append((d.get("source_name"), it.get("published"), d.get("link")))
        for media, quand, lien in candidats:
            nom = " ".join(str(media or "").split())
            if not nom or nom.lower() in vus:
                continue
            vus.add(nom.lower())
            out.append((nom, _date(quand), _domaine(lien)))
    return out


def bloc_sources(items: list[dict], *, langue: str = "EN") -> str:
    """« Sources: CoinDesk, 2026-09-03, coindesk.com | Decrypt, ... +2 ». Chaine vide si aucun media : une
    legende ne porte pas une etiquette « Sources: » suivie de rien."""
    entrees = _entrees(items)
    if not entrees:
        return ""
    tete = "Sources : " if str(langue).upper().startswith("FR") else "Sources: "
    morceaux = [", ".join(x for x in (nom, date, dom) if x) for nom, date, dom in entrees[:MEDIAS_MAX]]
    ligne = tete + " | ".join(morceaux)
    reste = len(entrees) - MEDIAS_MAX
    if reste > 0:
        ligne += f" +{reste}"
    return ligne
