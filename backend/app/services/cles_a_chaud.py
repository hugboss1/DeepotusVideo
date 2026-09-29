"""Application À CHAUD des clés enregistrées par l'écran Réglages (plan Settings T8 — tâche #17, 29/09/2026).

`restart_required: True` était vrai depuis v1.8 et n'avait jamais été remesuré. MESURE DU 29/09 (balayage AST de
`backend/app` + lecture de `fal_client`) :
  · aucune clé n'est lue à l'import hors `fal_service.py:33-34`, qui recopie FAL_KEY dans `os.environ` ; toutes les
    autres lectures passent par `settings.X` dans un corps de fonction ;
  · MAIS `fal_client` (bibliothèque) garde un client module (`fal_client.async_client`) dont les identifiants sont
    mis en cache au premier appel (`async_cached_property`) : changer `os.environ["FAL_KEY"]` ne suffit pas, l'ancien
    jeton resterait utilisé jusqu'au redémarrage. On RECONSTRUIT donc les deux clients module et on rattache leurs
    alias (`subscribe_async`, `submit_async`, …) — l'appli les appelle toujours par `fal_client.<fonction>` ;
  · `pipeline.heygen` mémorise son `HeyGenClient`, qui fige `api_key` à la construction : on l'oublie ;
  · le seul champ non-texte de `Settings` (ARTICLE_READER_FALLBACK, bool) est validé par pydantic comme au
    démarrage ; une valeur que pydantic refuse est dite « redémarrage » plutôt qu'appliquée de travers.
Les clés hors `Settings` (YouTube, Instagram) sont lues dans `os.environ`, que l'on met à jour aussi.
"""
import os

from loguru import logger


def _renouveler_fal() -> None:
    import fal_client
    vieux_a, vieux_s = fal_client.async_client, fal_client.sync_client
    neuf_a, neuf_s = fal_client.AsyncClient(), fal_client.SyncClient()
    for nom in dir(fal_client):
        obj = getattr(fal_client, nom, None)
        soi = getattr(obj, "__self__", None)
        if soi is vieux_a:
            setattr(fal_client, nom, getattr(neuf_a, obj.__name__))
        elif soi is vieux_s:
            setattr(fal_client, nom, getattr(neuf_s, obj.__name__))
    fal_client.async_client, fal_client.sync_client = neuf_a, neuf_s


def _oublier_heygen() -> None:
    try:
        from app.api.routes import pipeline
        pipeline._heygen = None
    except Exception as e:  # noqa: BLE001 — l'appli sans pipeline (bancs) n'a rien à oublier
        logger.debug(f"cles_a_chaud: pipeline absent ({e})")


def appliquer(changes: dict) -> list:
    """Applique chaque clé à `os.environ` et à `settings`. Rend la liste des clés qui exigent ENCORE un redémarrage."""
    from pydantic import TypeAdapter

    from app.config import settings
    champs = type(settings).model_fields
    a_froid = []
    for k, v in (changes or {}).items():
        v = "" if v is None else str(v)
        if v:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)
        f = champs.get(k)
        if f is None:
            continue
        try:
            val = TypeAdapter(f.annotation).validate_python(v) if v else f.get_default(call_default_factory=True)
            setattr(settings, k, val)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"cles_a_chaud: {k} non appliquée ({type(e).__name__}) — redémarrage nécessaire")
            a_froid.append(k)
    if "FAL_KEY" in (changes or {}):
        _renouveler_fal()
    if "HEYGEN_API_KEY" in (changes or {}):
        _oublier_heygen()
    return a_froid
