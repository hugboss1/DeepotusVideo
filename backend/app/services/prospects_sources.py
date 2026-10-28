# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3 : les SOURCES de prospects, en lecteurs purs (spec §4 ; plan t354, tâche 1).

- `whatsapp_entrants(eid)` : les contacts WhatsApp de l'espace qui ont un ACCORD (entrant ou saisi), sans STOP ni
  désinscription marketing (alias compris), absents du registre des oppositions et d'une fiche de l'espace. `whatsapp.json`
  est lu BRUT : jamais réécrit, jamais mis de côté (c'est l'affaire du service WhatsApp).
- `lire_csv(texte, origine)` : l'export d'une liste d'attente ou d'un formulaire déposé dans la conversation de l'agent ;
  une ligne n'est retenue qu'avec un consentement explicite et daté (jamais dans le futur), et au moins un canal.
- `signaux_veille(eid)` : les verbatims de la dernière veille qui disent un BESOIN (thème ou lexique). Jamais une fiche,
  jamais un auteur : la spec §9.4 veut une réponse publique, à la main.
Aucune écriture, aucun réseau, aucune dépense.
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from datetime import date

from app.services import espaces as _es, oppositions as _op

MAX_CSV = 500
MAX_WHATSAPP = 200
ORIGINES_CSV = ("liste_attente", "formulaire")
THEMES_BESOIN = ("prix_credits", "fournisseur_unique", "support_fiabilite", "censure_moderation", "droits_licence")
BESOIN = re.compile(r"alternativ|r[ée]sili|cancel|refund|rembours|switch|quitt|rempla", re.I)
_OUI = ("oui", "1", "true", "vrai", "yes", "x", "o")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_COLONNES = {"email": "email", "e_mail": "email", "mail": "email", "courriel": "email", "nom": "nom", "prenom": "prenom",
             "entreprise": "entreprise", "societe": "entreprise", "role": "role", "fonction": "role",
             "telephone": "telephone", "tel": "telephone", "whatsapp": "whatsapp", "date": "date",
             "date_inscription": "date", "consentement": "consentement", "optin": "consentement", "opt_in": "consentement",
             "url": "url", "site": "url"}


def _aujourdhui() -> date:          # couture de banc
    return date.today()


# ---- WhatsApp entrant ------------------------------------------------------------------------------------------------

def _doc_whatsapp(eid) -> dict:
    f = _es.chemin(eid, "whatsapp.json")
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _masque(ident: str) -> str:
    genre, _, v = ident.partition(":")
    return ("WhatsApp ·· " + v[-4:]) if genre == "tel" else "WhatsApp ·· " + v[-4:]


def _dicts(e: dict, k: str) -> dict:
    return e.get(k) if isinstance(e.get(k), dict) else {}


def whatsapp_entrants(eid) -> list:
    """[{identite, numero_masque, accord: {date, source}, dernier_entrant, compte}], les plus récents d'abord."""
    from app.services import prospects as _p
    etat = _doc_whatsapp(eid).get("etat")
    if not isinstance(etat, dict):
        return []
    connus = set()
    for f in _p._lire_fichier(_es.chemin(eid, _p.FICHIER), mettre_de_cote=False) or []:
        connus.update(_p.identifiants(f))
    cands = []
    for pid, e in etat.items():
        if not isinstance(e, dict):
            continue
        accords, stops, desinscrits, alias = (_dicts(e, k) for k in ("accords", "stops", "desinscrits_marketing", "alias"))
        derniers = {}
        for j in e.get("journal") if isinstance(e.get("journal"), list) else []:
            if isinstance(j, dict) and j.get("sens") == "entrant" and isinstance(j.get("quand"), str):
                derniers[j.get("identite")] = max(derniers.get(j.get("identite"), ""), j["quand"])
        for ident, acc in accords.items():
            if not isinstance(acc, dict) or not isinstance(ident, str):
                continue
            groupe = [ident] + ([alias[ident]] if isinstance(alias.get(ident), str) else [])
            if any(i in stops or i in desinscrits for i in groupe):
                continue
            formes = [f for f in (_op.normaliser(i) for i in groupe) if f]
            if not formes or set(formes) & connus:
                continue
            quand = max([derniers.get(i, "") for i in groupe] + [str(acc.get("date") or "")])
            cands.append({"identite": ident, "numero_masque": _masque(ident), "groupe": groupe, "_quand": quand,
                          "accord": {"date": str(acc.get("date") or "")[:10], "source": str(acc.get("source") or "")[:60]},
                          "dernier_entrant": max(derniers.get(i, "") for i in groupe)[:10] or None, "compte": str(pid)})
    if not cands:
        return []
    marques = _op.opposes([c["groupe"] for c in cands])
    garde = [c for c, m in zip(cands, marques) if not m]
    garde.sort(key=lambda c: c["_quand"], reverse=True)
    for c in garde:
        del c["_quand"], c["groupe"]
    return garde[:MAX_WHATSAPP]


# ---- CSV déposé ------------------------------------------------------------------------------------------------------

def _cle(nom: str) -> str:
    s = unicodedata.normalize("NFKD", str(nom or "")).encode("ascii", "ignore").decode().strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _cellule(v) -> str:
    s = str(v or "").strip()
    # formule de tableur : jamais exécutable une fois réexportée (un numéro « +33 6… » reste un numéro)
    while s[:1] in ("=", "@") or (s[:1] in ("+", "-") and not re.match(r"^[+-][\d\s().-]+$", s)):
        s = s[1:].lstrip()
    return s[:200]


def lire_csv(texte: str, origine: str) -> dict:
    """{"lignes": [champs de prospects.creer + consentements], "refus": [{ligne, raison}]} ; `ligne` = rang dans le
    fichier (l'en-tête est la ligne 1). ValueError : origine inconnue."""
    if origine not in ORIGINES_CSV:
        raise ValueError("origine du fichier inconnue (liste_attente ou formulaire)")
    texte = str(texte or "").lstrip("﻿")
    tete = texte.split("\n", 1)[0]
    sep = ";" if tete.count(";") > tete.count(",") else ","
    lecteur = csv.reader(io.StringIO(texte), delimiter=sep)
    try:
        entete = [_COLONNES.get(_cle(c)) for c in next(lecteur)]
    except StopIteration:
        return {"lignes": [], "refus": []}
    lignes, refus = [], []
    moyen = "inscription" if origine == "liste_attente" else "formulaire"
    jour = _aujourdhui().isoformat()
    for n, brut in enumerate(lecteur, start=2):
        if not any(c.strip() for c in brut):
            continue
        if len(lignes) >= MAX_CSV:
            refus.append({"ligne": n, "raison": f"au-delà de {MAX_CSV} lignes : déposez la suite dans un autre fichier"})
            break
        v = {}
        for k, c in zip(entete, brut):
            if k and k not in v:
                v[k] = _cellule(c)
        d = v.get("date", "")[:10]
        if v.get("consentement", "").lower() not in _OUI:
            refus.append({"ligne": n, "raison": "sans consentement explicite"})
            continue
        if not _DATE.match(d):
            refus.append({"ligne": n, "raison": "sans date d'inscription (AAAA-MM-JJ)"})
            continue
        if d > jour:
            refus.append({"ligne": n, "raison": "date d'inscription dans le futur"})
            continue
        canaux = [{"type": t, "valeur": v[t]} for t in ("email", "telephone", "whatsapp") if v.get(t)]
        if not canaux:
            refus.append({"ligne": n, "raison": "aucun canal (e-mail, téléphone ou WhatsApp)"})
            continue
        nom = " ".join(x for x in (v.get("prenom", ""), v.get("nom", "")) if x)
        if not nom and not v.get("entreprise"):
            nom = canaux[0]["valeur"].split("@")[0]
        lignes.append({"nom": nom, "entreprise": v.get("entreprise", ""), "role": v.get("role", ""), "canaux": canaux,
                       "source": {"type": origine, "date": d, "url": v.get("url", "") if re.match(r"^https?://", v.get("url", ""), re.I) else ""},
                       "base_legale": "consentement",
                       "consentements": [{"canal": c["type"], "base_legale": "consentement", "moyen": moyen, "date": d}
                                         for c in canaux[:1]]})
    return {"lignes": lignes, "refus": refus}


# ---- signaux de la veille --------------------------------------------------------------------------------------------

def signaux_veille(eid, limite: int = 30) -> list:
    """[{theme, concurrent, source, date, url, texte}] — jamais d'auteur."""
    from app.services import veille as _v
    try:
        vs = _v.verbatims(eid, limite=200)
    except (ValueError, OSError):
        return []
    out = []
    for x in vs:
        if x.get("polarite") == "force":
            continue
        if x.get("theme") in THEMES_BESOIN or BESOIN.search(str(x.get("texte") or "")):
            out.append({k: x.get(k) for k in ("theme", "concurrent", "source", "date", "url", "texte")})
        if len(out) >= limite:
            break
    return out
