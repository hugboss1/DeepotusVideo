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

from app.services import email_canal as _em, prospects as _p

MAX_REPONSES = 5
_GARDES = (
    ("stop", re.compile(r"^\s*(stop|arr[eê]t(e|ez|er)?)\b|d[ée]sinscri|d[ée]sabonn|unsubscrib|ne (plus|pas) (me )?"
                        r"(recevoir|contacter|[ée]crire|solliciter)", re.I | re.M)),
    ("plainte", re.compile(r"\b(plainte|m[ée]content|inadmissible|spam|harc[eè]le\w*|scandal\w*|complain\w*|annoying|"
                           r"abusi[fv]\w*)\b", re.I)),
    ("devis", re.compile(r"\b(devis|quote|quotation|proposition commerciale|cahier des charges)\b", re.I)),
    ("prix", re.compile(r"\b(prix|tarifs?|co[uû]te?s?|combien|budget|facturation|remise|r[ée]duction|price|pricing|cost|"
                        r"how much|discount)\b", re.I)),
)


def garde(texte: str) -> str | None:
    """Le motif qui impose l'humain dans un texte de prospect, ou None."""
    t = str(texte or "")
    for motif, motif_re in _GARDES:
        if motif_re.search(t):
            return motif
    return None


def reponses(eid) -> list:
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
        lignes.sort(key=lambda x: str(x.get("quand") or ""), reverse=True)
        derniere = next((x for x in lignes if x["canal"] == "email"), None)
        out.append({"pid": f["id"], "nom": f["nom"], "entreprise": f["entreprise"], "statut": f["statut"],
                    "offre": f["offre"], "score": f["score"], "prochaine_action": f["prochaine_action"],
                    "a_l_humain": f.get("a_l_humain"), "reponses": lignes[:MAX_REPONSES],
                    "garde": garde((derniere or {}).get("sujet", "") + "\n" + (derniere or {}).get("extrait", "")) if derniere else None})
    out.sort(key=lambda x: str((x["reponses"][0] if x["reponses"] else {}).get("quand") or ""), reverse=True)
    return out
