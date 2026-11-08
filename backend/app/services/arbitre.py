# -*- coding: utf-8 -*-
"""t442 (lot M9 « Méthodes », 08/11/2026) — B6 : l'ARBITRE, outil commun des agents métier (conception
docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §4 ; méthodes nine-models-one-brief,
image-to-3d-benchmark : « une consigne vérifiable, la même entrée pour tous, une sortie par modèle aux réglages par
défaut, aucun tri, crédits et temps par job »).

`tableau(sorties, reference)` ne génère rien : il prend les sorties DÉJÀ produites (une par modèle), les mesure toutes
de la même façon (briques.mesurer, contre la même référence quand il y en a une), et rend le tableau COMPLET — rien n'est
écarté, une sortie illisible reste une ligne « illisible ». Le classement suit une note objective (fidélité à la
référence pour une image, dérive pour une vidéo), à égalité le moins cher puis le plus rapide.
"""
from __future__ import annotations

from app.services import briques as BR

MAX_SORTIES = 24


def _nombre(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def note(mesure: dict) -> float | None:
    """PUR — une note 0-100 (plus haut = plus fidèle) tirée des mesures : identité (couleur ΔE et silhouette) contre la
    référence, sinon la corrélation moyenne image par image d'une vidéo ; None sans référence mesurable."""
    ident = mesure.get("identite") or {}
    if "ecart_couleur" in ident and "ecart_silhouette" in ident:
        c = max(0.0, 1 - float(ident["ecart_couleur"]) / 50.0)
        s = max(0.0, 1 - float(ident["ecart_silhouette"]))
        return round(100 * (0.5 * c + 0.5 * s), 1)
    t = mesure.get("temporel") or {}
    if t.get("moyenne") is not None:
        return round(100 * max(0.0, min(1.0, float(t["moyenne"]))), 1)
    return None


def tableau(sorties: list, reference: str = "") -> dict:
    """{reference, lignes: [{rang, modele, chemin, note, usd, secondes, verdict, mesure | erreur}], complet, meilleur}.
    `sorties` = [{modele, chemin, usd?, secondes?}], une par modèle. ValueError : entrée vide, doublon de modèle,
    trop de sorties."""
    if not isinstance(sorties, list) or not sorties:
        raise ValueError("Donne au moins une sortie à arbitrer (modèle et fichier).")
    if len(sorties) > MAX_SORTIES:
        raise ValueError(f"{MAX_SORTIES} sorties au plus.")
    vus, lignes = set(), []
    for s in sorties:
        if not isinstance(s, dict) or not isinstance(s.get("modele"), str) or not s["modele"].strip():
            raise ValueError("Chaque sortie nomme son modèle.")
        m = s["modele"].strip()[:80]
        if m in vus:
            raise ValueError(f"Une seule sortie par modèle (règle d'un comparatif équitable) : {m}")
        vus.add(m)
        ligne = {"modele": m, "chemin": str(s.get("chemin") or ""), "usd": _nombre(s.get("usd")),
                 "secondes": _nombre(s.get("secondes"))}
        try:
            mes = BR.mesurer(ligne["chemin"], reference)
            ligne.update(mesure=mes, note=note(mes), verdict=(mes.get("identite") or {}).get("verdict"))
        except (ValueError, RuntimeError, OSError) as e:
            ligne.update(note=None, verdict="illisible", erreur=str(e)[:200])
        lignes.append(ligne)
    def cle(x):
        return (-(x["note"] if x["note"] is not None else -1), x["usd"] if x["usd"] is not None else 1e9,
                x["secondes"] if x["secondes"] is not None else 1e9)
    lignes.sort(key=cle)
    for i, x in enumerate(lignes, 1):
        x["rang"] = i
    notes = [x for x in lignes if x["note"] is not None]
    return {"reference": reference or None, "lignes": lignes, "complet": True, "n": len(lignes),
            "meilleur": notes[0]["modele"] if notes else None,
            "regle": "même entrée, une sortie par modèle, réglages par défaut, aucune sortie écartée"}
