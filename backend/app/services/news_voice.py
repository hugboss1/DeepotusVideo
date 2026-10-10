# -*- coding: utf-8 -*-
"""Le mode de voix choisi selon le sujet (plan 2026-09-03 T10, tache #34 du suivi, 30/09/2026).

Reponse 3 de R8 : UNE persona, plusieurs modes. Un mode explicitement demande gagne toujours ; sinon le choix est
DETERMINISTE, par les mots-cles `sujets` de la persona. Ecart date (30/09, dans la ligne de la decision de
l'utilisateur sur le score News) : le LLM ne choisit que sur demande (`llm=True`), et la route qui le demande le
chiffre dans sa garde des plafonds. Le choix est TOUJOURS rendu avec son motif.
"""
import json

from loguru import logger

from app.services.news_filter import jetons

MODES = ("oracle", "alpha", "zen", "memer")
MODE_DEFAUT = "oracle"

_SYSTEME = (
    "You pick the voice mode for a deep-sea crypto brand's daily news video. "
    "Allowed modes: oracle (solemn, institutional news), alpha (blunt, market "
    "moves), zen (calm, no drama), memer (fast, absurd). Reply with JSON "
    "ONLY: {\"mode\": one of those four, \"pourquoi\": short reason}."
)


def _persona() -> dict:
    from app.services.prompt_engine import PromptEngine
    return PromptEngine("deepotus").persona


def _deterministe(items: list[dict]) -> tuple[str, str]:
    """Le mode dont les mots-cles `sujets` touchent le plus les titres et resumes. Egalite ou zero touche : le
    premier dans l'ordre de MODES, ou MODE_DEFAUT. Le motif nomme les mots qui ont decide."""
    modes = _persona().get("voice_modes") or {}
    mots: set = set()
    for it in items:
        mots.update(jetons(str(it.get("title") or "")))
        mots.update(jetons(str(it.get("summary") or "")))
    meilleur, touches_du_meilleur = MODE_DEFAUT, []
    for nom in MODES:
        bloc = modes.get(nom) or {}
        touches = []
        for s in bloc.get("sujets") or []:
            cle = jetons(str(s))
            if cle and all(c in mots for c in cle):
                touches.append(str(s))
        if len(touches) > len(touches_du_meilleur):
            meilleur, touches_du_meilleur = nom, touches
    if not touches_du_meilleur:
        return MODE_DEFAUT, "aucun mot du sujet ne tranche, mode par défaut"
    return meilleur, "mots du sujet : " + ", ".join(touches_du_meilleur[:3])


def _llm(items: list[dict]) -> tuple[str, str] | None:
    from app.services import summarizer
    titres = "\n".join(f"- {str(it.get('title') or '')[:140]}" for it in items[:8])
    try:
        brut, _prov = summarizer._chat_dispatch(f"Headlines:\n{titres}\n\nPick the voice mode.", _SYSTEME, 200)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"news_voice: dispatch en echec ({e}) - deterministe")
        return None
    if not brut:
        return None
    d0, f0 = brut.find("{"), brut.rfind("}")
    if d0 < 0 or f0 <= d0:
        return None
    try:
        d = json.loads(brut[d0:f0 + 1])
    except json.JSONDecodeError:
        return None
    mode = str(d.get("mode") or "").strip().lower()
    if mode not in MODES:
        logger.warning(f"news_voice: mode inconnu rendu ({mode!r}) - repli")
        return None
    return mode, str(d.get("pourquoi") or "")[:200] or "choisi par le modèle"


def choisir_mode(items: list[dict], *, force: str | None = None, llm: bool = False) -> tuple[str, str]:
    """Rend (mode, pourquoi). Ne leve jamais. `llm=True` seulement quand l'utilisateur l'a demande ET que la garde
    des plafonds est passee."""
    if force and str(force).strip().lower() in MODES:
        return str(force).strip().lower(), "mode force par l'utilisateur"
    if not items:
        return MODE_DEFAUT, "aucun article, mode par defaut"
    if llm:
        par_llm = _llm(items)
        if par_llm:
            return par_llm
    try:
        return _deterministe(items)
    except Exception as e:  # noqa: BLE001 - une persona illisible ne casse pas le script
        logger.warning(f"news_voice: choix deterministe en echec ({e})")
        return MODE_DEFAUT, "persona illisible, mode par defaut"
