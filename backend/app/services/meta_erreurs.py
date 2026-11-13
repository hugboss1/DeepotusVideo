# -*- coding: utf-8 -*-
"""t520 (13/11/2026) — les refus de la Graph API de Meta (Instagram) DITS EN CLAIR, en français et en anglais.

Relevé du 13/11/2026 sur developers.facebook.com :
  - « Marketing API error codes » : code 200, sous-code 5258005 = « API access blocked. » (sans autre explication),
    5258004 = « API access deactivated. To reactivate, go to the My Apps page to unarchive it. » (application archivée),
    5258006 = « API access deactivated. » (application supprimée, renvoi à « App States : Removed ») ;
  - « App States » : une application archivée voit tous ses appels échouer ; restreinte, elle se conteste.
  - code 190 : jeton d'accès invalide, expiré ou révoqué (« Graph API error handling »).
La famille 52580xx porte donc sur l'ÉTAT DE L'APPLICATION, pas sur le jeton : c'est une déduction, Meta ne l'écrit pas.
Le pas à pas est au guide, chapitre « Relier un compte Instagram », section Dépannage.

`expliquer(corps)` rend un `app.i18n.Message` (texte = le français) ou None : l'appelant garde alors le détail brut.
"""
from __future__ import annotations

import json

from app.i18n import Message

_SOUS_CODES = {5258005: "meta.erreur.app_bloquee", 5258004: "meta.erreur.app_archivee",
               5258006: "meta.erreur.app_supprimee"}
SOUS_CODES_APP = frozenset(_SOUS_CODES)


def _erreur(corps) -> dict | None:
    if isinstance(corps, (str, bytes)):
        try:
            corps = json.loads(corps)
        except (ValueError, TypeError):
            return None
    e = corps.get("error") if isinstance(corps, dict) else None
    return e if isinstance(e, dict) else None


def sous_code(corps) -> int | None:
    e = _erreur(corps)
    try:
        return int(e.get("error_subcode")) if e and e.get("error_subcode") is not None else None
    except (TypeError, ValueError):
        return None


def expliquer(corps) -> Message | None:
    """L'explication d'un corps d'erreur Graph (dict ou texte JSON), ou None si l'erreur n'est pas une connue."""
    e = _erreur(corps)
    if not e:
        return None
    sc = sous_code(corps)
    if sc in _SOUS_CODES:
        return Message(_SOUS_CODES[sc], sous_code=sc)
    if e.get("code") == 190:
        return Message("meta.erreur.jeton_invalide")
    return None
