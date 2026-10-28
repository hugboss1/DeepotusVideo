# -*- coding: utf-8 -*-
"""Format de conversation v1 de l'agent Campagnes (t285a, 23/10/2026).

Défini UNE fois, ici et dans docs/agent/campagnes/format.md + format.schema.json ; le téléphone le reprend.
Un message : {"v": 1, "id", "role", "quand", "origine", "appareil", "blocs", "cout_paye"}.
Aucune dépendance : la validation est faite à la main.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

VERSION = 1
ROLES_MESSAGE = ("utilisateur", "agent", "outil", "fait")
TYPES_BLOC = ("texte", "carte", "resultat_outil", "porte")
GENRES_CARTE = ("porte", "devis", "continuer", "espace", "brouillons", "ouvrir",
                "reponse_whatsapp", "modele_whatsapp", "humain",
                "recherche",                       # t354 : recherche web d'entreprises (devis)
                "sequence",                        # t355 : porte 2 d'une séquence de prospection
                "collecte")                        # t364 : un run Apify de la liste blanche (devis, plafond dur)
ETATS_CARTE = ("proposee", "acceptee", "refusee", "terminee")
ORIGINES = ("pc", "telephone")
ETATS_PORTE = ("proposee", "validee", "refusee")


def nouveau_message(role: str, blocs: list[dict], *, origine: str = "pc", appareil: str | None = None) -> dict:
    """Un message neuf : identifiant UUID créé ici, horodatage UTC, coût payé à zéro."""
    return {
        "v": VERSION,
        "id": str(uuid.uuid4()),
        "role": role,
        "quand": datetime.now(timezone.utc).isoformat(),
        "origine": origine,
        "appareil": appareil,
        "blocs": blocs,
        "cout_paye": 0.0,
    }


def _erreurs_bloc(i: int, b) -> list[str]:
    p = f"blocs[{i}]"
    if not isinstance(b, dict):
        return [f"{p}: objet attendu"]
    t = b.get("type")
    if t not in TYPES_BLOC:
        return [f"{p}: type inconnu {t!r}"]
    err: list[str] = []
    if t == "texte":
        if not isinstance(b.get("texte"), str):
            err.append(f"{p}: texte requis")
    elif t == "carte":
        if b.get("genre") not in GENRES_CARTE:
            err.append(f"{p}: genre requis parmi {', '.join(GENRES_CARTE)}")
        if not isinstance(b.get("libelle"), str):
            err.append(f"{p}: libelle requis")
        if b.get("etat") not in ETATS_CARTE:
            err.append(f"{p}: etat requis parmi {', '.join(ETATS_CARTE)}")
        d = b.get("devis")
        if d is not None and (isinstance(d, bool) or not isinstance(d, (int, float)) or d < 0):
            err.append(f"{p}: devis en dollars, nombre positif")
        if "action" in b and b["action"] is not None and not isinstance(b["action"], str):
            err.append(f"{p}: action en texte")
        if "arguments" in b and b["arguments"] is not None and not isinstance(b["arguments"], dict):
            err.append(f"{p}: arguments en objet")
    elif t == "resultat_outil":
        if not isinstance(b.get("outil"), str):
            err.append(f"{p}: outil requis")
        if not isinstance(b.get("resume"), str):
            err.append(f"{p}: resume requis")
    elif t == "porte":
        if b.get("numero") not in (1, 2) or isinstance(b.get("numero"), bool):
            err.append(f"{p}: numero 1 ou 2")
        if b.get("etat") not in ETATS_PORTE:
            err.append(f"{p}: etat requis parmi {', '.join(ETATS_PORTE)}")
    return err


def valider(message: dict) -> list[str]:
    """Les erreurs du message, liste vide s'il est valide."""
    if not isinstance(message, dict):
        return ["message: objet attendu"]
    err: list[str] = []
    if message.get("v") != VERSION or isinstance(message.get("v"), bool):
        err.append(f"v: {VERSION} attendu")
    if not isinstance(message.get("id"), str) or not message.get("id"):
        err.append("id: texte non vide requis")
    if message.get("role") not in ROLES_MESSAGE:
        err.append(f"role: inconnu {message.get('role')!r}")
    if not isinstance(message.get("quand"), str):
        err.append("quand: date ISO requise")
    if message.get("origine") not in ORIGINES:
        err.append(f"origine: parmi {', '.join(ORIGINES)}")
    if message.get("appareil") is not None and not isinstance(message.get("appareil"), str):
        err.append("appareil: texte ou null")
    c = message.get("cout_paye")
    if isinstance(c, bool) or not isinstance(c, (int, float)) or c < 0:
        err.append("cout_paye: nombre positif requis")
    blocs = message.get("blocs")
    if not isinstance(blocs, list) or not blocs:
        err.append("blocs: liste non vide requise")
    else:
        for i, b in enumerate(blocs):
            err += _erreurs_bloc(i, b)
    return err


def empreinte(message: dict) -> str:
    """sha1 de l'id, du rôle et des blocs en JSON trié : la clé d'idempotence de l'import."""
    corps = {"id": message.get("id"), "role": message.get("role"), "blocs": message.get("blocs")}
    return hashlib.sha1(json.dumps(corps, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":")).encode("utf-8")).hexdigest()
