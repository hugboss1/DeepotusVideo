# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2 : le REGISTRE GLOBAL des oppositions (spec §3 et §6 : un « STOP » vaut pour
tous les espaces de l'utilisateur). `DATA_ROOT/espaces/oppositions.json`, hors de tout espace.

Minimisation : le registre ne garde que des EMPREINTES `sha256(sel + identifiant normalisé)`, jamais une adresse ni un
numéro en clair ; le sel est tiré une fois et rangé dans le fichier (une empreinte n'est pas un hachage universel de
l'adresse). Un identifiant se normalise en `email:<minuscules>`, `tel:<chiffres avec indicatif>` (même règle que
`whatsapp.numero_normalise`), `bsuid:<id>` ou `profil:<url en minuscules sans / final>`.
Un registre illisible est mis de côté (`oppositions.json.illisible-<horodatage>`), jamais écrasé ; un neuf repart.
Écrivain unique sous verrou, écriture atomique par `espaces._ecrire_json`. Aucun réseau, aucune dépense.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from datetime import datetime

from loguru import logger

from app.services import espaces as _es

ORIGINES = ("prospect", "whatsapp", "saisie", "effacement")
FICHIER = "oppositions.json"
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")
_TEL = re.compile(r"^[+\d\s().-]{5,40}$")
_verrou = threading.Lock()


def _fichier():
    return _es.dossier() / FICHIER


def normaliser(identifiant) -> str | None:
    """La forme canonique d'un identifiant, ou None (vide, inconnu)."""
    if not isinstance(identifiant, str):
        return None
    v = identifiant.strip()
    if not v:
        return None
    bas = v.lower()
    if bas.startswith("bsuid:") and len(v) > 6:
        return "bsuid:" + v[6:].strip()
    if bas.startswith("tel:"):
        v = v[4:]
    elif bas.startswith("email:"):
        bas = bas[6:].strip()
    if _EMAIL.match(bas):
        return "email:" + bas
    if bas.startswith(("http://", "https://")):
        return "profil:" + bas.rstrip("/")
    if _TEL.match(v) and len(re.sub(r"\D", "", v)) >= 5:
        from app.services.whatsapp import numero_normalise
        return "tel:" + numero_normalise(v)
    return None


def _mettre_de_cote(f) -> None:
    base = f"{FICHIER}.illisible-{datetime.now():%Y%m%d-%H%M%S}"
    cote, n = f.with_name(base), 2
    while cote.exists():
        cote, n = f.with_name(f"{base}-{n}"), n + 1
    try:
        f.replace(cote)
        logger.warning(f"registre des oppositions illisible : mis de côté ({cote.name}), un registre neuf repart")
    except OSError as e:
        logger.warning(f"registre des oppositions illisible et impossible à mettre de côté ({e})")


class RegistreIndisponible(RuntimeError):
    """t353 (relecture I2) : le registre existe mais ne se lit pas maintenant (verrou d'un antivirus, d'une synchro…).
    Refus par défaut : on ne crée rien, on n'écrase rien, on ne dit jamais « pas opposé » sans l'avoir lu."""


def mis_de_cote() -> int:
    """Le nombre de registres illisibles mis de côté (l'écran le signale : leurs oppositions ne sont plus appliquées)."""
    try:
        return sum(1 for _ in _es.dossier().glob(FICHIER + ".illisible-*"))
    except OSError:
        return 0


def _charger() -> dict:
    f = _fichier()
    try:
        brut = f.read_bytes()
    except FileNotFoundError:
        return {"version": 1, "sel": secrets.token_hex(16), "empreintes": {}}
    except OSError:
        raise RegistreIndisponible("registre des oppositions momentanément illisible : réessayez dans un instant") from None
    try:
        doc = json.loads(brut.decode("utf-8"))
        if (not isinstance(doc, dict) or not isinstance(doc.get("sel"), str) or len(doc["sel"]) < 16
                or not isinstance(doc.get("empreintes"), dict)):
            raise ValueError("forme inattendue")
        return doc
    except ValueError:
        _mettre_de_cote(f)
        return {"version": 1, "sel": secrets.token_hex(16), "empreintes": {}}


def _empreinte(sel: str, forme: str) -> str:
    return hashlib.sha256((sel + forme).encode("utf-8")).hexdigest()


def _formes(identifiants) -> list:
    if isinstance(identifiants, str):
        identifiants = [identifiants]
    out = []
    for x in identifiants or []:
        f = normaliser(x)
        if f and f not in out:
            out.append(f)
    return out


def inscrire(identifiants, origine: str) -> int:
    """Inscrit les identifiants reconnus ; rend le nombre d'empreintes NEUVES. ValueError : origine inconnue."""
    if origine not in ORIGINES:
        raise ValueError("origine d'opposition inconnue")
    formes = _formes(identifiants)
    if not formes:
        return 0
    with _verrou:
        doc = _charger()
        neuves = 0
        for forme in formes:
            h = _empreinte(doc["sel"], forme)
            if h not in doc["empreintes"]:
                doc["empreintes"][h] = {"le": _es._maintenant(), "origine": origine}
                neuves += 1
        if neuves or not _fichier().exists():
            _es._ecrire_json(_fichier(), doc)
        return neuves


def oppose(identifiants) -> bool:
    """Un des identifiants est-il au registre ? Lecture seule (un fichier absent n'est pas créé)."""
    formes = _formes(identifiants)
    if not formes:
        return False
    with _verrou:
        doc = _charger()
    return any(_empreinte(doc["sel"], f) in doc["empreintes"] for f in formes)


def opposes(groupes) -> list:
    """t353 (relecture I3) : pour chaque groupe d'identifiants, est-il au registre ? Une seule lecture du registre."""
    formes = [_formes(g) for g in groupes]
    if not any(formes):
        return [False] * len(formes)
    with _verrou:
        doc = _charger()
    return [any(_empreinte(doc["sel"], f) in doc["empreintes"] for f in fs) for fs in formes]


def compte() -> int:
    with _verrou:
        return len(_charger()["empreintes"])
