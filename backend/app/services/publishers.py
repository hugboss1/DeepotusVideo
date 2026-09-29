"""Registre des adaptateurs de publication (plan scheduler, P1 — tâche #24 du 29/09/2026).

Décision T0, TRANCHÉE PAR L'UTILISATEUR le 29/09/2026 (tâche #23) : adaptateurs DIRECTS plutôt que Postiz en relais.
Mesure du jour : Postiz auto-hébergé demande Postgres + Redis + Temporal, ne dispense pas des apps développeur
Meta / Google / TikTok (« Most platforms need you to register a developer app »), et Postiz Cloud est un tiers payant.
Mêmes apps, mêmes quotas, aucun service permanent à faire tourner (R12 : pas d'hôte, aucun tiers). Postiz reste une
note (R12 E2).

Un adaptateur = (canal, disponible(), publier(caption, video, image, meta)). `disponible()` est relu à CHAQUE appel
(une clé posée à chaud compte tout de suite). `publish` vérifie le quota AVANT l'appel réseau, compte APRÈS un succès,
et ne lève jamais : l'échec est une chaîne qui nomme le canal et la cause."""
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from loguru import logger

from app.services import quota


@dataclass
class PublishResult:
    ok: bool
    detail: str                      # "youtube: short abc" | "youtube init 403: …"
    remote_id: Optional[str] = None


Publisher = Callable[[str, Optional[str], Optional[str], dict], Awaitable[PublishResult]]
_REGISTRY: dict[str, tuple[Callable[[], bool], Publisher]] = {}


def register(channel: str, available: Callable[[], bool], fn: Publisher) -> None:
    _REGISTRY[channel] = (available, fn)


def available_channels() -> set[str]:
    return {ch for ch, (avail, _fn) in _REGISTRY.items() if avail()}


async def publish(channel: str, caption: str, video_path: Optional[str],
                  image_path: Optional[str], meta: dict | None = None) -> PublishResult:
    entry = _REGISTRY.get(channel)
    if not entry or not entry[0]():
        return PublishResult(False, f"{channel}: assisted (no auto adapter)")
    ok, msg = quota.check(channel)
    if not ok:
        return PublishResult(False, msg)
    try:
        res = await entry[1](caption or "", video_path, image_path, meta or {})
    except Exception as e:
        logger.warning(f"publish {channel} raised: {e}")
        return PublishResult(False, f"{channel} error: {e}")
    if res.ok:
        quota.count(channel)
    return res
