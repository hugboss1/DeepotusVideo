# -*- coding: utf-8 -*-
"""t312 — la lecture locale d'un scan (OCR Windows + nettoyage), partagée par les routes `/api/scan/*` et l'outil d'agent
`lire_texte_image` (qui ne doit pas importer les routes). Bloquant : à lancer dans un fil. Aucun journal du texte lu."""
from __future__ import annotations

import time

from app.services import scan_ocr as O

DELAI_PAGE = "La lecture de texte de Windows a dépassé le délai d'une minute."


class _Arret(Exception):
    """L'échéance globale de la lecture est atteinte (revue finale t312, m1)."""

# ------------------------------------------------------------------------------------------------- lecture locale
def _indisponible(raison: str):
    """Les raisons de `scan_ocr.disponible()` levées en littéraux (couverts par L10)."""
    if raison == "Aucune langue de lecture de texte n'est installée dans Windows.":
        raise O.ScanIndisponible("Aucune langue de lecture de texte n'est installée dans Windows.")
    if raison == "La lecture de texte locale n'existe que sous Windows.":
        raise O.ScanIndisponible("La lecture de texte locale n'existe que sous Windows.")
    raise O.ScanIndisponible("La lecture de texte de Windows ne répond pas (PowerShell absent ou bloqué).")


def _langues(langue: str) -> list[str]:
    """Les passes à faire : [langue] ou, en auto, celles de fr/en installées dans Windows. ScanIndisponible sinon."""
    d = O.disponible()
    if not d.get("ok"):
        _indisponible(d.get("raison") or "")
    installees = d.get("langues") or []
    voulues = ["fr", "en"] if langue == "auto" else [langue]
    passes = [lg for lg in voulues if O.LANGUES[lg] in installees]
    if not passes:
        raise O.ScanIndisponible("Cette langue de lecture n'est pas installée dans Windows.")
    return passes


def _page_texte(texte: str) -> str:
    return "\n".join(li.rstrip() for li in (texte or "").strip().splitlines())


def _joindre(morceaux: list[tuple[str, list]]) -> tuple[str, list]:
    """[(texte, incertains)] -> (texte joint par une ligne vide, positions décalées). Les morceaux vides sautent."""
    parts, incertains, n = [], [], 0
    for texte, inc in morceaux:
        if not texte:
            continue
        if parts:
            parts.append("\n\n")
            n += 2
        incertains += [{"debut": i["debut"] + n, "fin": i["fin"] + n} for i in inc]
        parts.append(texte)
        n += len(texte)
    return "".join(parts), incertains


def _lire_ocr(plan: list[dict], langue: str, echeance: float | None = None) -> dict:
    """La lecture locale du scan (bloquante : à lancer dans un fil). ScanIndisponible, ScanErreur, ValueError.
    `echeance` (time.monotonic, revue finale t312, m1) : passée, les pages restantes ne sont pas lues ; ce qui a été lu
    est rendu avec `partiel: True` et `pages_lues` (pages du dépôt traitées, dans l'ordre) ; rien de lu -> ScanErreur
    (délai total, 504 sur la route)."""
    from app.services import scan_nettoyage as N
    passes = _langues(langue) if any(p["genre"] == "image" for p in plan) else []
    morceaux, stats, langue_lue, groupe = [], {}, None, []
    arret = False

    def lire_un(octets, lg):
        if echeance is None:
            return O.lire_page(octets, lg)
        reste = echeance - time.monotonic()
        if reste <= 1.0:
            raise _Arret()
        try:
            return O.lire_page(octets, lg, delai=reste)
        except O.ScanErreur as e:
            if str(e) == DELAI_PAGE and time.monotonic() >= echeance - 1.0:
                raise _Arret() from None
            raise

    def vider():
        nonlocal langue_lue, arret
        if not groupe:
            return 0
        lus = {lg: [] for lg in passes}
        faites = 0
        for octets in groupe:
            try:
                une = {lg: lire_un(octets, lg) for lg in passes}
            except _Arret:
                arret = True
                break
            for lg in passes:
                lus[lg].append(une[lg])
            faites += 1
        groupe.clear()
        if not faites:
            return 0
        r = N.nettoyer(lus[passes[0]], langue=passes[0], autre=lus[passes[1]] if len(passes) > 1 else None)
        morceaux.append((r["texte"], r["incertains"]))
        for k, v in (r.get("stats") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                stats[k] = stats.get(k, 0) + v
        langue_lue = langue_lue or r.get("langue")
        return faites

    pages_texte, traitees = 0, 0
    for p in plan:
        if p["genre"] == "image":
            groupe.append(p["octets"])
            continue
        traitees += vider()
        if arret:
            break
        t = _page_texte(p["texte"])
        morceaux.append((t, []))
        pages_texte += 1
        traitees += 1
        stats["mots"] = stats.get("mots", 0) + len(t.split())
    if not arret:
        traitees += vider()
    if arret and not traitees:
        raise O.ScanErreur("La lecture de texte de Windows a dépassé deux minutes : réessaie avec moins de pages.")
    texte, incertains = _joindre(morceaux)
    stats.setdefault("pages", 0)
    stats.setdefault("mots", 0)
    stats["pages_texte"] = pages_texte
    stats["incertains"] = len(incertains)
    r = {"moteur": "windows" if passes else "texte",
         "langue": langue_lue or (langue if langue in ("fr", "en") else "fr"),
         "texte": texte, "incertains": incertains, "stats": stats, "passes": len(passes)}
    if arret:
        r.update(partiel=True, pages_lues=traitees)
    return r
