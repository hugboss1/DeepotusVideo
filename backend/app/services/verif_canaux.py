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
from app.services.diagnostic import _get as _http_get, _msg, _sans

# Refus d'un échange de jeton OAuth : « youtube token 401: … » EN TÊTE du message, ou invalid_grant / invalid_client.
_REFUS = re.compile(r"^(youtube|tiktok) token (400|401|403)\b|invalid_grant|invalid_client", re.I)
_REFUS_X = {"Unauthorized", "Forbidden"}      # tweepy : par TYPE d'exception, jamais par le texte
_QUOTA_YT = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
_GRAPH_REFUS = {190, 102, 10, 200}            # Graph : jeton expiré/invalide, session, permission


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


# t308 (26/10/2026) : le CODE d'un résultat (jeu fermé) : l'écran le traduit (dzT), `raison` reste le détail français brut.
CODES = ("ok", "incomplet", "refuse", "refuse_palier", "quota", "reseau", "indetermine", "non_audite", "chat_introuvable",
         "telephone_verifie", "telephone_jamais", "plateforme_inconnue")


def _code_http(etat: str) -> str:
    return "refuse" if etat == "rouge" else "indetermine"


def _r(etat: str, raison: str, id_distant=None, nom_distant=None, secrets_: list[str] | None = None, *, code: str) -> dict:
    assert code in CODES, code
    return {"etat": etat, "code": code, "raison": _propre(raison, secrets_ or []),
            "id_distant": None if id_distant is None else str(id_distant), "nom_distant": nom_distant}


def _etat_http(code: int) -> str:
    return "rouge" if code in (401, 403) else "orange"


def _etat_exception(e: Exception) -> str:
    """Un refus (401/403, jeton invalide) est rouge ; le réseau, un 5xx ou un 429 restent orange."""
    if type(e).__name__ in _REFUS_X or _REFUS.search(str(e)):
        return "rouge"
    return "orange"


def _raison_yt(corps) -> str:
    """Raison de la première erreur d'un corps d'erreur Google ('' si absente)."""
    try:
        return str(corps["error"]["errors"][0]["reason"])
    except (KeyError, IndexError, TypeError):
        return ""


def _graph_refus(corps) -> bool:
    """Jeton Graph invalide : HTTP 400 + OAuthException (ou code 190/102/10/200), pas un 401."""
    e = corps.get("error") if isinstance(corps, dict) else None
    return isinstance(e, dict) and (e.get("type") == "OAuthException" or e.get("code") in _GRAPH_REFUS)


def _manquants(plateforme: str) -> list[str]:
    return [c for c in comptes.PLATEFORMES[plateforme][2] if not str(comptes.cle(c) or "").strip()]


async def _x() -> dict:
    ident, nom = await asyncio.to_thread(_x_me)      # to_thread garde le compte courant (ContextVar)
    return _r("vert", "compte X joint", ident, f"@{nom}", code="ok")


async def _telegram() -> dict:
    tok = str(comptes.cle("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = str(comptes.cle("TELEGRAM_CHAT_ID") or "").strip()
    base = f"https://api.telegram.org/bot{tok}"
    sec = _secrets("telegram")
    code, corps = await _get(f"{base}/getMe")
    if not (code == 200 and isinstance(corps, dict) and corps.get("ok")):
        etat = "rouge" if code in (401, 403, 404) else "orange"
        return _r(etat, f"jeton {'refusé' if etat == 'rouge' else 'indéterminé'} ({code}) : {_msg(corps)}", secrets_=sec, code=_code_http(etat))
    code, corps = await _get(f"{base}/getChat", params={"chat_id": chat})
    if code == 200 and isinstance(corps, dict) and corps.get("ok"):
        c = corps.get("result") or {}
        nom = c.get("title") or (f"@{c['username']}" if c.get("username") else None) or c.get("first_name")
        return _r("vert", "bot et chat joints", c.get("id", chat), nom, sec, code="ok")
    etat = "rouge" if code in (400, 401, 403, 404) else "orange"
    return _r(etat, f"chat {'introuvable' if etat == 'rouge' else 'indéterminé'} ({code}) : {_msg(corps)}", secrets_=sec,
              code="chat_introuvable" if etat == "rouge" else "indetermine")


async def _youtube() -> dict:
    from app.services import youtube_publisher
    tok = await youtube_publisher.access_token()
    sec = _secrets("youtube", tok)
    code, corps = await _get("https://www.googleapis.com/youtube/v3/channels",
                             headers={"Authorization": f"Bearer {tok}"}, params={"part": "snippet", "mine": "true"})
    if code == 403 and _raison_yt(corps) in _QUOTA_YT:
        return _r("orange", f"quota YouTube épuisé ({_raison_yt(corps)}) : réessayer plus tard", secrets_=sec, code="quota")
    if code != 200:
        return _r(_etat_http(code), f"youtube {code} : {_msg(corps)}", secrets_=sec,
                  code=_code_http(_etat_http(code)))
    items = (corps.get("items") if isinstance(corps, dict) else None) or []
    if not items:
        return _r("orange", "youtube : aucune chaîne sur ce compte", secrets_=sec, code="indetermine")
    return _r("vert", "chaîne YouTube jointe", items[0].get("id"), (items[0].get("snippet") or {}).get("title"), sec,
              code="ok")


async def _instagram() -> dict:
    from app.services import instagram_publisher
    tok = str(comptes.cle("IG_ACCESS_TOKEN") or "").strip()
    ig = str(comptes.cle("IG_BUSINESS_ID") or "").strip()
    sec = _secrets("instagram")
    code, corps = await _get(f"{instagram_publisher._graph()}/{ig}",
                             params={"fields": "username", "access_token": tok})
    if code != 200 or not isinstance(corps, dict) or not corps.get("username"):
        etat = "rouge" if code in (401, 403) or (code == 400 and _graph_refus(corps)) else "orange"
        return _r(etat,
                  f"instagram {code} : {_msg(corps)}" if code != 200 else "instagram : aucun nom de compte rendu", secrets_=sec,
                  code=_code_http(etat))
    return _r("vert", "compte Instagram joint", corps.get("id") or ig, f"@{corps['username']}", sec, code="ok")


async def _tiktok() -> dict:
    from app.services import tiktok_publisher
    tok = await tiktok_publisher.access_token()
    sec = _secrets("tiktok", tok)
    code, corps = await _get("https://open.tiktokapis.com/v2/user/info/",
                             headers={"Authorization": f"Bearer {tok}"}, params={"fields": "open_id,display_name"})
    user = ((corps.get("data") or {}).get("user") if isinstance(corps, dict) else None) or {}
    if code != 200 or not user.get("open_id"):
        return _r(_etat_http(code) if code != 200 else "orange",
                  f"tiktok {code} : {_msg(corps)}" if code != 200 else "tiktok : aucune identité rendue", secrets_=sec,
                  code=_code_http(_etat_http(code)) if code != 200 else "indetermine")
    if not comptes.cle("TIKTOK_AUDITED"):
        return _r("orange", "compte non audité : publication privée seulement", user["open_id"], user.get("display_name"), sec,
                  code="non_audite")
    return _r("vert", "compte TikTok joint", user["open_id"], user.get("display_name"), sec, code="ok")


_PAR_PLATEFORME = {"x": _x, "telegram": _telegram, "youtube": _youtube, "instagram": _instagram, "tiktok": _tiktok}


async def verifier_plateforme(plateforme: str) -> dict:
    """État et identité distante du compte COURANT de `plateforme`. Ne lève jamais, ne publie jamais."""
    if plateforme not in _PAR_PLATEFORME:
        return _r("orange", f"plateforme inconnue : {plateforme}"[:80], code="plateforme_inconnue")
    try:
        manque = _manquants(plateforme)
        if manque:
            return _r("orange", "identifiants incomplets : " + ", ".join(manque), code="incomplet")
        return await _PAR_PLATEFORME[plateforme]()
    except Exception as e:  # noqa: BLE001 — une vérification ne casse jamais l'écran
        try:
            sec = _secrets(plateforme)
        except Exception:  # noqa: BLE001
            sec = []
        raison = f"{plateforme} : {type(e).__name__} : {e}"
        etat = _etat_exception(e)
        code = "refuse" if etat == "rouge" else "reseau"
        if plateforme == "x" and type(e).__name__ == "Forbidden":
            raison = f"x : accès refusé (palier d'API X insuffisant ?) : {e}"
            code = "refuse_palier"
        return _r(etat, raison, secrets_=sec, code=code)


# ---- t308 (26/10/2026) : la vérification ENREGISTRÉE ------------------------------------------------------------------------------

def _portee(pp: dict) -> dict:
    """Le résultat d'un compte PORTÉ PAR LE TÉLÉPHONE : la déclaration de l'appareil, sans réseau ni secret."""
    date = pp.get("verifie_le")
    if not date:
        return _r("orange", "porté par le téléphone, jamais vérifié", pp.get("id_distant"), code="telephone_jamais")
    etat = pp.get("etat") if pp.get("etat") in comptes.ETATS else "orange"
    return _r(etat, f"porté par le téléphone, vérifié le {date}", pp.get("id_distant"), code="telephone_verifie")


async def verifier(cid: str) -> dict:
    """Vérifie le compte `cid` (ou `historique-<p>`), RANGE le résultat daté (`comptes.noter_verification`) et rend la vue
    relue. Un compte porté par le téléphone ne lit aucun secret et n'appelle aucun réseau. KeyError = compte inconnu."""
    vue = comptes.obtenir(cid)
    rev = comptes.revision(cid)          # relevée AVANT le réseau : si le compte change pendant l'appel, rien n'est rangé
    if isinstance(vue.get("porte_par"), dict):
        res = _portee(vue["porte_par"])
    else:
        with comptes.sous_compte(cid):
            res = await verifier_plateforme(vue["plateforme"])
    comptes.noter_verification(cid, res, rev=rev)
    return comptes.obtenir(cid)
