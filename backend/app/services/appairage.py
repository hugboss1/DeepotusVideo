# -*- coding: utf-8 -*-
"""Plan mobile T2 (tâche #56, P1, 01/10/2026) — appairage d'un appareil, jeton révocable, garde de jeton.

Trois faits mesurés qui commandent tout ce fichier :

1. La garde CSRF de `main.py` fait `if origin:` — une application NATIVE n'envoie pas d'en-tête `Origin` et passe donc
   la garde CSRF. Ouvrir `HOST` sur le LAN sans jeton exposerait toute l'API au Wi-Fi. Le jeton est LA garde.
2. `_require_localhost` (routes.py) reste INTACT : le téléphone ne lit jamais les clés par le backend. Elles lui
   viennent de l'archive chiffrée (R11 D1).
3. Le runtime embarqué est stdlib pur + Pillow : `secrets`, `hashlib` et `time` suffisent.

Les secrets d'appairage vivent EN MÉMOIRE (un seul processus uvicorn) : un redémarrage les oublie, ce qui est voulu
(il suffit de réafficher le QR).
"""
import hashlib
import secrets as _secrets
import time
from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from sqlalchemy import select as _select, update as _update

DUREE_SECRET_S = 300          # 5 minutes (R12 réponse 11)
MAX_APPAREILS = 5             # « jusqu'à cinq appareils nommés »
_CACHE_TTL_S = 5.0            # la synchro tire des centaines de vignettes : pas une requête SQL par appel

#: secret à usage unique -> {"cree_a": float, "expire_a": float}
_SECRETS: dict[str, dict] = {}

#: cache des sha256 encore valides + l'instant de son chargement
_ACTIFS: set[str] = set()
_ACTIFS_A: float = 0.0


class SecretRefuse(Exception):
    """Le secret d'appairage est inconnu, expiré, déjà consommé, ou le quota de cinq appareils est atteint. Le message
    DIT lequel."""


@dataclass
class Secret:
    secret: str
    cree_a: float
    expire_a: float


#: R12 réponse 12 — « révocation + rappel de régénérer les clés chez chaque fournisseur (liste avec liens vers chaque
#: console) ». Les noms sont ceux de _ALLOWED_ENV_KEYS (routes.py) ; écart au plan : les comptes de publication du
#: Scheduler (YouTube, Instagram, TikTok), arrivés depuis, y sont aussi.
CONSOLES: list[dict] = [
    {"cle": "FAL_KEY", "nom": "fal.ai", "url": "https://fal.ai/dashboard/keys"},
    {"cle": "HEYGEN_API_KEY", "nom": "HeyGen", "url": "https://app.heygen.com/settings/api"},
    {"cle": "MESHY_API_KEY", "nom": "Meshy", "url": "https://www.meshy.ai/settings/api"},
    {"cle": "ELEVENLABS_API_KEY", "nom": "ElevenLabs", "url": "https://elevenlabs.io/app/settings/api-keys"},
    {"cle": "ANTHROPIC_API_KEY", "nom": "Anthropic", "url": "https://console.anthropic.com/settings/keys"},
    {"cle": "OPENAI_API_KEY", "nom": "OpenAI", "url": "https://platform.openai.com/api-keys"},
    {"cle": "GEMINI_API_KEY", "nom": "Google AI Studio", "url": "https://aistudio.google.com/app/apikey"},
    {"cle": "FIGMA_TOKEN", "nom": "Figma", "url": "https://www.figma.com/settings"},
    {"cle": "X_API_KEY", "nom": "X (developer portal)", "url": "https://developer.x.com/en/portal/dashboard"},
    {"cle": "TELEGRAM_BOT_TOKEN", "nom": "Telegram BotFather", "url": "https://t.me/BotFather"},
    {"cle": "YOUTUBE_CLIENT_SECRET", "nom": "Google Cloud (YouTube)", "url": "https://console.cloud.google.com/apis/credentials"},
    {"cle": "IG_ACCESS_TOKEN", "nom": "Meta for Developers (Instagram)", "url": "https://developers.facebook.com/apps/"},
    {"cle": "TIKTOK_CLIENT_SECRET", "nom": "TikTok for Developers", "url": "https://developers.tiktok.com/apps/"},
]


def creer_secret() -> Secret:
    """Un secret à usage unique, valable 5 minutes. Le QR le porte."""
    _purger()
    s = _secrets.token_hex(16)          # 32 caractères hexadécimaux, 128 bits
    maintenant = time.time()
    _SECRETS[s] = {"cree_a": maintenant, "expire_a": maintenant + DUREE_SECRET_S}
    return Secret(secret=s, cree_a=maintenant, expire_a=maintenant + DUREE_SECRET_S)


def _purger() -> None:
    mort = [k for k, v in _SECRETS.items() if v["expire_a"] < time.time()]
    for k in mort:
        _SECRETS.pop(k, None)


async def reclamer(secret: str, nom: str) -> tuple[str, dict]:
    """Consomme le secret et rend (jeton en clair, fiche de l'appareil). Le jeton en clair n'est rendu qu'ICI, une
    seule fois."""
    from uuid import uuid4
    from app.services.storage import Device, async_session_factory

    fiche = _SECRETS.get(secret or "")
    if fiche is None:
        raise SecretRefuse("secret inconnu ou deja consomme — reaffichez le QR")
    if fiche["expire_a"] < time.time():
        _SECRETS.pop(secret, None)
        raise SecretRefuse("secret expire (5 minutes) — reaffichez le QR")
    async with async_session_factory() as session:
        res = await session.execute(_select(Device.id).where(Device.revoque.is_(None)))
        if len(res.all()) >= MAX_APPAREILS:
            raise SecretRefuse("cinq appareils sont deja appaires — revoquez-en un")
        jeton = _secrets.token_hex(32)          # 64 caractères, 256 bits
        appareil = Device(id=str(uuid4()), nom=(nom or "appareil").strip()[:60] or "appareil",
                          jeton_sha256=hashlib.sha256(jeton.encode()).hexdigest(), cree=datetime.utcnow())
        session.add(appareil)
        await session.commit()
    _SECRETS.pop(secret, None)                  # USAGE UNIQUE
    invalider_cache()
    logger.info(f"appairage: {appareil.nom} ({appareil.id})")
    return jeton, {"id": appareil.id, "nom": appareil.nom, "cree": appareil.cree.isoformat()}


def invalider_cache() -> None:
    """La révocation doit mordre TOUT DE SUITE, pas au bout du TTL."""
    global _ACTIFS_A
    _ACTIFS_A = 0.0


async def _charger_actifs() -> set[str]:
    global _ACTIFS, _ACTIFS_A
    if time.time() - _ACTIFS_A < _CACHE_TTL_S:
        return _ACTIFS
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        res = await session.execute(_select(Device.jeton_sha256).where(Device.revoque.is_(None)))
        _ACTIFS = {row[0] for row in res.all()}
    _ACTIFS_A = time.time()
    return _ACTIFS


async def jeton_valide(jeton) -> bool:
    if not isinstance(jeton, str) or len(jeton) != 64:
        return False
    empreinte = hashlib.sha256(jeton.encode()).hexdigest()
    return empreinte in await _charger_actifs()


async def lister() -> list[dict]:
    """Les appareils, révoqués compris (avec leur date) — jamais le jeton ni son empreinte."""
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        res = await session.execute(_select(Device).order_by(Device.cree))
        return [{"id": d.id, "nom": d.nom, "cree": d.cree.isoformat(),
                 "revoque": d.revoque.isoformat() if d.revoque else None,
                 "vu_le": d.vu_le.isoformat() if d.vu_le else None}
                for d in res.scalars().all()]


async def revoquer(device_id: str) -> bool:
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        r = await session.execute(_update(Device).where(Device.id == device_id).where(Device.revoque.is_(None))
                                  .values(revoque=datetime.utcnow()))
        await session.commit()
    invalider_cache()
    return r.rowcount > 0


async def revoquer_tout() -> int:
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        r = await session.execute(_update(Device).where(Device.revoque.is_(None)).values(revoque=datetime.utcnow()))
        await session.commit()
    invalider_cache()
    return r.rowcount
