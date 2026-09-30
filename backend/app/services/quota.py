"""Compteurs de publication par canal, bornés par les quotas VÉRIFIÉS (plan scheduler, R6, 03/09/2026 — tâche #24 du
29/09/2026). Fichier JSON DATA_ROOT/scheduler/quota.json : {"x": {"2026-09": 12}, "youtube": {"2026-09-03": 2}}.

Instagram compte 100 posts par 24 h GLISSANTES (doc relue le 29/09/2026 ; le plan du 03/09 disait 50). Un seau par
jour UTC ne borne PAS une fenêtre glissante (100 à 23 h 59 puis 100 à 0 h 01) : ce seau n'est qu'un garde-fou local,
le compteur d'Instagram (`content_publishing_limit`) est demandé avant chaque envoi par instagram_publisher et fait foi.
Telegram n'a pas de plafond publié : non compté. Le quota est vérifié AVANT l'appel réseau et compté APRÈS
un succès (publishers.publish) : un échec ne consomme rien."""
import json
from datetime import datetime

from app.config import DATA_ROOT

# canal -> (période, plafond, source datée — reprise telle quelle dans l'erreur)
LIMITS = {
    "x": ("month", 500, "palier gratuit X : 500 posts/mois (docs.x.com, 03/09/2026)"),
    "instagram": ("day", 100, "Instagram : 100 posts API/24 h glissantes, compteur d'Instagram demandé avant chaque "
                              "envoi (developers.facebook.com, relu 29/09/2026)"),
    "youtube": ("day", 100, "YouTube Data API : 100 envois/jour (developers.google.com, 03/09/2026)"),
    "tiktok": ("day", 15, "TikTok Direct Post : ~15 posts/jour par créateur (developers.tiktok.com, 03/09/2026)"),
    # tâche #29 (30/09) : un budget de LECTURES, pas de publications — la passe de métriques (metrics_service) le borne
    "x_lecture": ("month", 100, "palier gratuit X : 100 lectures/mois (docs.x.com, 03/09/2026)"),
}
_FILE = DATA_ROOT / "scheduler" / "quota.json"


def _key(period: str, now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    return now.strftime("%Y-%m") if period == "month" else now.strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        return json.loads(_FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1), "utf-8")
    tmp.replace(_FILE)


def used(channel: str, now: datetime | None = None) -> int:
    lim = LIMITS.get(channel)
    return int(_load().get(channel, {}).get(_key(lim[0], now), 0)) if lim else 0


def check(channel: str, now: datetime | None = None) -> tuple[bool, str]:
    """(True, 'n/plafond') ou (False, message parlant qui nomme la source)."""
    lim = LIMITS.get(channel)
    if not lim:
        return True, ""
    n = used(channel, now)
    if n >= lim[1]:
        return False, f"quota {channel} : {n}/{lim[1]} — {lim[2]}"
    return True, f"{n}/{lim[1]}"


def count(channel: str, now: datetime | None = None, n: int = 1) -> int:
    """+n (1 par défaut) sur la période courante. Synchrone de bout en bout : entre la lecture et l'écriture, la boucle d'événements
    ne rend pas la main — deux publications concurrentes ne peuvent pas perdre un compte."""
    lim = LIMITS.get(channel)
    if not lim:
        return 0
    d = _load()
    k = _key(lim[0], now)
    d.setdefault(channel, {})[k] = int(d.get(channel, {}).get(k, 0)) + int(n)
    _save(d)
    return d[channel][k]


def summary() -> dict:
    return {ch: {"used": used(ch), "limit": lim[1], "period": lim[0], "source": lim[2]}
            for ch, lim in LIMITS.items()}
