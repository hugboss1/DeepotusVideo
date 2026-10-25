"""Vérification d'un compte de diffusion SANS publier (t308, 26/10/2026).

Un appel en LECTURE SEULE par plateforme, qui rend l'état du compte et l'identité distante :
  · X : `get_me` (tweepy) ; Telegram : `getMe` puis `getChat` (jamais `sendMessage`, contrairement à `_test_channel`) ;
  · YouTube : `channels?mine=true` ; Instagram : `GET /<id>?fields=username` ; TikTok : `/v2/user/info/`.
Ne publie rien, ne dépense rien, n'envoie aucun message. Aucune valeur secrète dans un résultat : les messages passent par
`diagnostic._sans` (jeton Telegram dans l'URL `bot<jeton>`, jeton Instagram dans la query, jetons d'accès OAuth).
À appeler SOUS `comptes.sous_compte(cid)`. Hooks remplaçables au banc : `_get` et `_x_me` (test_verif_canaux).

États : `vert` (le compte répond, identité lue) · `orange` (indéterminé : réseau, 5xx/429, champ manquant, TikTok non
audité) · `rouge` (refusé : 401/403, jeton invalide, chat introuvable).
"""
import asyncio
import re
from urllib.parse import quote, urlencode

from app.services import comptes
from app.services.diagnostic import _get as _http_get, _msg, _res, _sans

_REFUS = re.compile(r"\b(401|403)\b|invalid_grant|invalid_client|unauthori[sz]ed|forbidden", re.I)
_REFUS_X = {"Unauthorized", "Forbidden"}


async def _get(url: str, headers: dict | None = None, params: dict | None = None):
    """(code HTTP, corps) — réemploie l'aide de diagnostic ; les paramètres rejoignent la query."""
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urlencode(params)}"
    return await _http_get(url, headers)


def _x_me() -> tuple:
    """(id, username) du compte X courant — tweepy `get_me`, synchrone (appelé dans un fil)."""
    from app.services import marketing
    me = marketing._x_client().get_me()
    return str(me.data.id), me.data.username


def _secrets(plateforme: str, *extra: str) -> list[str]:
    vals = [str(comptes.cle(c) or "").strip() for c, secret in comptes.PLATEFORMES[plateforme][1] if secret]
    vals += [str(e or "").strip() for e in extra]
    out: list[str] = []
    for v in vals:
        if v:
            out += [v, quote(v, safe=""), quote(v)]
    return sorted(set(out), key=len, reverse=True)


def _propre(texte, secrets_: list[str]) -> str:
    t = str(texte)
    for s in secrets_:
        t = _sans(t, s)
    return t[:200]


def _r(etat: str, raison: str, id_distant=None, nom_distant=None, secrets_: list[str] | None = None) -> dict:
    return {"etat": etat, "raison": _propre(raison, secrets_ or []),
            "id_distant": None if id_distant is None else str(id_distant), "nom_distant": nom_distant}


def _etat_http(code: int) -> str:
    return "rouge" if code in (401, 403) else "orange"


def _etat_exception(e: Exception) -> str:
    """Un refus (401/403, jeton invalide) est rouge ; le réseau, un 5xx ou un 429 restent orange."""
    if type(e).__name__ in _REFUS_X or _REFUS.search(str(e)):
        return "rouge"
    return "orange"


def _manquants(plateforme: str) -> list[str]:
    return [c for c in comptes.PLATEFORMES[plateforme][2] if not str(comptes.cle(c) or "").strip()]


async def _x() -> dict:
    ident, nom = await asyncio.to_thread(_x_me)      # to_thread garde le compte courant (ContextVar)
    return _r("vert", "compte X joint", ident, f"@{nom}")


async def _telegram() -> dict:
    tok = str(comptes.cle("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = str(comptes.cle("TELEGRAM_CHAT_ID") or "").strip()
    base = f"https://api.telegram.org/bot{tok}"
    sec = _secrets("telegram")
    code, corps = await _get(f"{base}/getMe")
    if not (code == 200 and isinstance(corps, dict) and corps.get("ok")):
        etat = "rouge" if code in (401, 403, 404) else "orange"
        return _r(etat, f"jeton {'refusé' if etat == 'rouge' else 'indéterminé'} ({code}) : {_msg(corps)}", secrets_=sec)
    code, corps = await _get(f"{base}/getChat", params={"chat_id": chat})
    if code == 200 and isinstance(corps, dict) and corps.get("ok"):
        c = corps.get("result") or {}
        nom = c.get("title") or (f"@{c['username']}" if c.get("username") else None) or c.get("first_name")
        return _r("vert", "bot et chat joints", c.get("id", chat), nom, sec)
    etat = "rouge" if code in (400, 401, 403, 404) else "orange"
    return _r(etat, f"chat {'introuvable' if etat == 'rouge' else 'indéterminé'} ({code}) : {_msg(corps)}", secrets_=sec)


async def _youtube() -> dict:
    from app.services import youtube_publisher
    tok = await youtube_publisher.access_token()
    sec = _secrets("youtube", tok)
    code, corps = await _get("https://www.googleapis.com/youtube/v3/channels",
                             headers={"Authorization": f"Bearer {tok}"}, params={"part": "snippet", "mine": "true"})
    if code != 200:
        return _r(_etat_http(code), f"youtube {code} : {_msg(corps)}", secrets_=sec)
    items = (corps.get("items") if isinstance(corps, dict) else None) or []
    if not items:
        return _r("orange", "youtube : aucune chaîne sur ce compte", secrets_=sec)
    return _r("vert", "chaîne YouTube jointe", items[0].get("id"), (items[0].get("snippet") or {}).get("title"), sec)


async def _instagram() -> dict:
    from app.services import instagram_publisher
    tok = str(comptes.cle("IG_ACCESS_TOKEN") or "").strip()
    ig = str(comptes.cle("IG_BUSINESS_ID") or "").strip()
    sec = _secrets("instagram")
    code, corps = await _get(f"{instagram_publisher._graph()}/{ig}",
                             params={"fields": "username", "access_token": tok})
    if code != 200 or not isinstance(corps, dict) or not corps.get("username"):
        return _r(_etat_http(code) if code != 200 else "orange",
                  f"instagram {code} : {_msg(corps)}" if code != 200 else "instagram : aucun nom de compte rendu", secrets_=sec)
    return _r("vert", "compte Instagram joint", corps.get("id") or ig, f"@{corps['username']}", sec)


async def _tiktok() -> dict:
    from app.services import tiktok_publisher
    tok = await tiktok_publisher.access_token()
    sec = _secrets("tiktok", tok)
    code, corps = await _get("https://open.tiktokapis.com/v2/user/info/",
                             headers={"Authorization": f"Bearer {tok}"}, params={"fields": "open_id,display_name"})
    user = ((corps.get("data") or {}).get("user") if isinstance(corps, dict) else None) or {}
    if code != 200 or not user.get("open_id"):
        return _r(_etat_http(code) if code != 200 else "orange",
                  f"tiktok {code} : {_msg(corps)}" if code != 200 else "tiktok : aucune identité rendue", secrets_=sec)
    if not comptes.cle("TIKTOK_AUDITED"):
        return _r("orange", "compte non audité : publication privée seulement", user["open_id"], user.get("display_name"), sec)
    return _r("vert", "compte TikTok joint", user["open_id"], user.get("display_name"), sec)


_PAR_PLATEFORME = {"x": _x, "telegram": _telegram, "youtube": _youtube, "instagram": _instagram, "tiktok": _tiktok}


async def verifier_plateforme(plateforme: str) -> dict:
    """État et identité distante du compte COURANT de `plateforme`. Ne lève jamais, ne publie jamais."""
    if plateforme not in _PAR_PLATEFORME:
        return _r("orange", f"plateforme inconnue : {plateforme}"[:80])
    try:
        manque = _manquants(plateforme)
        if manque:
            return _r("orange", "identifiants incomplets : " + ", ".join(manque))
        return await _PAR_PLATEFORME[plateforme]()
    except Exception as e:  # noqa: BLE001 — une vérification ne casse jamais l'écran
        try:
            sec = _secrets(plateforme)
        except Exception:  # noqa: BLE001
            sec = []
        return _r(_etat_exception(e), f"{plateforme} : {type(e).__name__} : {e}", secrets_=sec)
