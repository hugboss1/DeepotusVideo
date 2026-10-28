# -*- coding: utf-8 -*-
"""t358 (28/10/2026) — Veille & prospection P7 : le SUIVI des réponses des prospects. Plan
`docs/superpowers/plans/2026-10-28-prospects-p7-t358.md`.

`reponses(eid)` : les fiches qui ont répondu (« A répondu », ou « Contacté » avec un contact entrant noté), avec leurs
dernières réponses : e-mail = objet + extrait gardés par le canal e-mail (t356) ; WhatsApp = la date seulement (le texte
n'est jamais rangé, règle t310). Chaque fiche porte `garde` : le motif qui impose le passage à l'humain (prix, devis,
plainte, stop) lu dans la dernière réponse e-mail, sinon None. L'agent ne prend jamais d'engagement : `garde` non nul =
il ne répond pas, il passe la main (`prospects.passer_a_l_humain`).
Lecture seule, aucun réseau.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.services import email_canal as _em, prospects as _p

MAX_REPONSES = 5
_GARDES = (
    ("stop", re.compile(r"^\s*(stop|arr[eê]t(e|ez|er)?)\b|d[ée]sinscri|d[ée]sabonn|unsubscrib|remove me", re.I | re.M)),
    ("refus", re.compile(r"pas int[ée]ress|non merci|no thanks|not interested|ne (me )?(contactez|[ée]crivez|sollicitez|"
                         r"relancez) plus|ne plus (me )?(recevoir|contacter|[ée]crire|solliciter)|stop (emailing|contacting|"
                         r"messaging|writing)|do not contact|don'?t contact|opt[- ]?out|leave me alone", re.I)),
    ("plainte", re.compile(r"\b(plainte|m[ée]content|inadmissible|spam|harc[eè]le\w*|scandal\w*|complain\w*|annoying|"
                           r"abusi[fv]\w*)\b", re.I)),
    ("devis", re.compile(r"\b(devis|quote|quotation|proposition commerciale|cahier des charges)\b", re.I)),
    ("engagement", re.compile(r"\b(d[ée]lais?|contrat|deadline|garantie|rembourse\w*|engagement|sla)\b", re.I)),
    ("prix", re.compile(r"\b(prix|tarifs?|tarification|co[uû]te?s?|combien|budget|facturation|remise|r[ée]duction|abonnement|"
                        r"price|pricing|cost|how much|discount|rates?|fees?)\b|[€$]", re.I)),
)


def _dt(v) -> datetime | None:
    """Une date ISO en UTC ; sans fuseau = heure locale (l'historique des fiches)."""
    try:
        d = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return (d.astimezone() if d.tzinfo is None else d).astimezone(timezone.utc)


def garde(texte: str) -> str | None:
    """Le motif qui impose l'humain dans un texte de prospect, ou None."""
    t = str(texte or "")
    for motif, motif_re in _GARDES:
        if motif_re.search(t):
            return motif
    return None


def reponses(eid) -> list:
    """Relecture t358 : `garde` lit TOUTES les réponses e-mail reçues depuis le dernier envoi ; si la plus récente est un
    WhatsApp (texte jamais rangé), `garde` = « illisible » ; `canal_reponse` = le canal de la plus récente ;
    `derniere_reponse` = sa date (UTC)."""
    fiches = _p.lister(eid)
    try:
        rep = _em._doc(eid)["reponses"]
    except _em.RefusEmail:
        rep = []
    out = []
    for f in fiches:
        if f["statut"] == "oppose":
            continue
        entrants = [h for h in f["historique"] if h["quoi"] == "contact_entrant"]
        mails = [r for r in rep if r.get("pid") == f["id"] and not r.get("stop")]
        if f["statut"] != "repondu" and not (f["statut"] == "contacte" and entrants):
            continue
        lignes = [{"canal": "email", "quand": r.get("quand"), "sujet": r.get("sujet", ""), "extrait": r.get("extrait", "")}
                  for r in mails]
        lignes += [{"canal": "whatsapp", "quand": h["quand"], "sujet": "", "extrait": ""}
                   for h in entrants if str(h.get("detail") or "").startswith("whatsapp")]
        epoque = datetime(1970, 1, 1, tzinfo=timezone.utc)
        lignes.sort(key=lambda x: _dt(x.get("quand")) or epoque, reverse=True)
        sortants = [_dt(h["quand"]) for h in f["historique"] if h["quoi"] == "contact_sortant"]
        dernier_envoi = max([d for d in sortants if d], default=None)
        recentes = [x for x in lignes if not dernier_envoi or (_dt(x.get("quand")) or epoque) > dernier_envoi] or lignes[:1]
        g = next((m for m in (garde(x.get("sujet", "") + "\n" + x.get("extrait", "")) for x in recentes if x["canal"] == "email") if m), None)
        if g is None and lignes and lignes[0]["canal"] == "whatsapp":
            g = "illisible"
        out.append({"pid": f["id"], "nom": f["nom"], "entreprise": f["entreprise"], "statut": f["statut"],
                    "offre": f["offre"], "score": f["score"], "prochaine_action": f["prochaine_action"],
                    "a_l_humain": f.get("a_l_humain"), "reponses": lignes[:MAX_REPONSES], "garde": g,
                    "canal_reponse": lignes[0]["canal"] if lignes else None,
                    "derniere_reponse": (_dt(lignes[0].get("quand")) or epoque).replace(microsecond=0).isoformat()
                    if lignes else None})
    out.sort(key=lambda x: x["derniere_reponse"] or "", reverse=True)
    return out
