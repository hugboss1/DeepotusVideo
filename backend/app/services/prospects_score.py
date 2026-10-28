# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3 : le BARÈME du score d'un prospect et ses CANAUX POSSIBLES (pur ; plan
t354, tâche 2, décision de l'utilisateur : barème fixe vérifiable + ajustement de l'agent borné à ±20, raison exigée).

Barème (0 à 100) :
  source entrante (whatsapp, liste d'attente, formulaire, telegram, réponse à un post) +40 ; web, recommandation, salon +15 ;
  consentement daté en cours +20 ; au moins un canal possible en envoi après porte +15 ; adresse professionnelle +10 ;
  signal +5 ; dernier contact venu du prospect il y a moins de 30 jours +10.
Canaux possibles (spec §3) : e-mail pro sous intérêt légitime B2B, ou e-mail avec consentement → `auto_apres_porte` ;
WhatsApp avec consentement en cours → `auto_apres_porte` ; X, Instagram, LinkedIn → `manuel` (l'agent rédige, l'humain
envoie) ; un opposé n'a aucun canal.
"""
from __future__ import annotations

from datetime import date

ENTRANTES = ("whatsapp", "liste_attente", "formulaire", "telegram", "reponse_post")
TIEDES = ("web", "recommandation", "salon")
RESEAUX = ("x", "instagram", "linkedin")
AJUSTEMENT_MAX = 20


def _aujourdhui() -> date:          # couture de banc
    return date.today()


def _webmail(valeur: str) -> bool:
    from app.services.prospects import _webmail as w
    return w(valeur)


def _consentis(fiche: dict) -> set:
    return {c.get("canal") for c in fiche.get("consentements") or [] if isinstance(c, dict) and not c.get("revoque_le")}


def canaux_possibles(fiche: dict) -> list:
    """[{canal, mode, raison}] dans l'ordre des canaux de la fiche, un par type."""
    if fiche.get("statut") == "oppose":
        return []
    consentis, out, vus = _consentis(fiche), [], set()
    for c in fiche.get("canaux") or []:
        t, v = c.get("type"), str(c.get("valeur") or "")
        if t in vus:
            continue
        if t == "email":
            if "email" in consentis:
                out.append({"canal": t, "mode": "auto_apres_porte", "raison": "consentement e-mail daté"})
            elif fiche.get("base_legale") == "interet_legitime_b2b" and not _webmail(v):
                out.append({"canal": t, "mode": "auto_apres_porte", "raison": "adresse professionnelle, intérêt légitime B2B"})
            else:
                continue
        elif t == "whatsapp":
            if "whatsapp" not in consentis:
                continue
            out.append({"canal": t, "mode": "auto_apres_porte", "raison": "accord WhatsApp daté"})
        elif t in RESEAUX:
            out.append({"canal": t, "mode": "manuel", "raison": "pas de message automatique : l'agent rédige, vous envoyez"})
        else:
            continue
        vus.add(t)
    return out


def bareme(fiche: dict) -> dict:
    """{"base": 0-100, "details": [{critere, points}]} — seuls les critères acquis figurent."""
    d = []
    st = (fiche.get("source") or {}).get("type")
    if st in ENTRANTES:
        d.append({"critere": "source_entrante", "points": 40})
    elif st in TIEDES:
        d.append({"critere": "source_web", "points": 15})
    if _consentis(fiche):
        d.append({"critere": "consentement", "points": 20})
    if any(c["mode"] == "auto_apres_porte" for c in canaux_possibles(fiche)):
        d.append({"critere": "canal_possible", "points": 15})
    if any(c.get("type") == "email" and c.get("valeur") and not _webmail(str(c["valeur"])) for c in fiche.get("canaux") or []):
        d.append({"critere": "adresse_pro", "points": 10})
    if str(fiche.get("signal") or "").strip():
        d.append({"critere": "signal", "points": 5})
    dce = fiche.get("dernier_contact_entrant")
    try:
        if dce and (_aujourdhui() - date.fromisoformat(str(dce)[:10])).days < 30:
            d.append({"critere": "contact_recent", "points": 10})
    except ValueError:
        pass
    return {"base": min(100, sum(x["points"] for x in d)), "details": d}


def score(base: int, ajustement) -> int:
    """`base` + `ajustement` (entier de -20 à 20, sinon ValueError), borné à 0-100."""
    if isinstance(ajustement, bool) or not isinstance(ajustement, int) or abs(ajustement) > AJUSTEMENT_MAX:
        raise ValueError("ajustement du score invalide : un entier de -20 à 20 est attendu")
    return max(0, min(100, int(base) + ajustement))
