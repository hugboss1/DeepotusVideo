"""Client REST Kapso pour WhatsApp, SANS webhook ni SDK (t310, 27/10/2026).

Deux familles d'URL, une seule clé de projet (`comptes.cle_kapso()`, lue À CHAQUE requête, en-tête `X-API-Key` seulement) :
  · Platform `https://api.kapso.ai/platform/v1` : customers, liens de liaison, numéros, préférences marketing ;
  · proxy WhatsApp `https://api.kapso.ai/meta/whatsapp/v24.0` : envoi, lecture des messages et conversations, modèles, médias.
Relevé : docs/superpowers/specs/2026-10-27-kapso-releve.md (§0 à §7).

Seule `_requete` touche le réseau (httpx, SSL_VERIFY, pas de redirection) : les bancs la remplacent, ainsi que `_dormir`
(attente du réessai 429). Elle refuse toute URL hors HTTPS `api.kapso.ai` : la clé ne part jamais ailleurs.

Erreurs : toujours `KapsoErreur(statut, code, reessayable, message)`. L'erreur se lit sous les deux formes du relevé
(Platform `{"error": str, "code"?}` ; proxy `{"error": {"message", "type", "code", "error_subcode"}}`). Le message est le texte
du fournisseur NETTOYÉ (clé, `token=…`, `"token": "…"` retirés) et borné à 200 caractères ; il n'est pas traduit (l'écran
traduit `code`). Un corps non JSON n'est jamais recopié. Le journal ne note que méthode, chemin SANS query, statut, code, et
`type(e).__name__` pour une exception réseau : jamais une clé, un jeton de lien ni l'URL d'un média (`?token=`).

Réessai : 429 (attente `Retry-After`, sinon 1, 2, 4, 8 s) et 409 `message_in_flight` (même attente) ; cinq essais au plus,
puis `KapsoErreur(code="429")` (ou `message_in_flight`) réessayable par l'appelant. Aucun autre statut n'est réessayé : 422
`131047`, `marketing_preference_stopped`, 409 `thread_not_owner`, 402, 5xx sont rendus tout de suite.
"""
import asyncio
import re
from urllib.parse import quote, urlparse

import httpx
from loguru import logger

from app.config import SSL_VERIFY
from app.services import comptes
from app.services.diagnostic import _sans

PLATFORM = "https://api.kapso.ai/platform/v1"
PROXY = "https://api.kapso.ai/meta/whatsapp/v24.0"
HOTE = "api.kapso.ai"
MAX_ESSAIS = 5                    # essais au total pour un 429 (relevé §6 : « 5 essais maximum »)
ATTENTE_MAX = 120.0               # un Retry-After démesuré ne bloque pas l'application
_RE_TOKEN_URL = re.compile(r"token=[^&\s]+", re.I)
_RE_TOKEN_JSON = re.compile(r'"token"\s*:\s*"[^"]+"', re.I)


class KapsoErreur(RuntimeError):
    """Refus ou panne de Kapso. `code` : code fournisseur (`131047`, `marketing_preference_stopped`, `thread_not_owner`,
    `insufficient_credits`…), ou `reseau`, `cle_absente`, `hote_refuse`, `media_*`, `reponse_invalide`, sinon le statut HTTP."""

    def __init__(self, message: str = "", *, statut: int = 0, code: str = "", reessayable: bool = False):
        self.message = str(message)[:200]
        super().__init__(self.message)
        self.statut = int(statut)
        self.code = str(code)
        self.reessayable = bool(reessayable)


# ---- le seul accès réseau ---------------------------------------------------------------------------------------------

async def _dormir(secondes: float) -> None:
    """Attente d'un réessai 429 (remplacée au banc)."""
    await asyncio.sleep(secondes)


async def _requete(methode: str, url: str, *, json=None, params=None) -> tuple[int, object, dict]:
    """HOOK DE BANC : (statut, corps, en-têtes). Corps = JSON décodé si le type le dit, sinon octets bruts.
    La clé part en en-tête `X-API-Key` seulement, vers HTTPS `api.kapso.ai` seulement, sans suivre de redirection."""
    u = urlparse(url)
    if u.scheme != "https" or u.hostname != HOTE or u.username or u.password:
        raise KapsoErreur("Adresse Kapso refusée (HTTPS api.kapso.ai seulement)", code="hote_refuse")
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=30, follow_redirects=False) as c:
        r = await c.request(methode, url, json=json, params=params,
                            headers={"X-API-Key": comptes.cle_kapso(), "Accept": "application/json, */*"})
    entetes = dict(r.headers)
    corps: object = r.content
    if "json" in str(entetes.get("content-type", "")).lower():
        try:
            corps = r.json()
        except ValueError:
            corps = r.content
    return r.status_code, corps, entetes


# ---- nettoyage et lecture d'une erreur ---------------------------------------------------------------------------------

def _propre(texte, cle: str = "", max_: int = 200) -> str:
    """Retire clé (brute et encodée), `token=…` et `"token": "…"` ; borne la longueur."""
    t = str(texte)
    for s in {cle, quote(cle, safe=""), quote(cle)} if cle else ():
        t = _sans(t, s)
    t = _RE_TOKEN_URL.sub("token=…", t)
    t = _RE_TOKEN_JSON.sub('"token": "…"', t)
    return t[:max_]


def _lire_erreur(statut: int, corps, cle: str) -> tuple[str, str]:
    """(code, message) nettoyés, depuis les deux formes d'erreur ; un corps non JSON donne un message générique."""
    code = message = ""
    if isinstance(corps, dict):
        err = corps.get("error")
        if isinstance(err, dict):                              # forme proxy (Meta)
            message = err.get("message") or ""
            code = err.get("code") or err.get("error_subcode") or err.get("type") or corps.get("code") or ""
        else:                                                  # forme Platform
            message = err or corps.get("message") or ""
            code = corps.get("code") or ""
    code = _propre(code, cle, 64).strip() or str(statut)
    message = _propre(message, cle).strip() or f"Réponse Kapso inattendue (HTTP {statut})"
    return code, message


def _chemin(url: str) -> str:
    """Le chemin SANS query (la query d'un média porte un jeton) pour le journal."""
    return urlparse(url).path or "/"


def _attente(entetes: dict, essai: int) -> float:
    """`Retry-After` (secondes) s'il est lisible, sinon repli 1, 2, 4, 8 s."""
    for k, v in (entetes or {}).items():
        if str(k).lower() == "retry-after":
            try:
                return max(0.0, min(float(v), ATTENTE_MAX))
            except (TypeError, ValueError):
                break
    return float(2 ** essai)


async def _appel(methode: str, url: str, *, json=None, params=None, reessai_ok: bool = True) -> tuple[int, object, dict]:
    """Un appel avec clé vérifiée, réessai 429/409 `message_in_flight`, erreurs normalisées ; rend (statut, corps, en-têtes) en 2xx.
    `reessai_ok=False` : un seul essai (un 429 reste marqué réessayable : c'est à l'appelant de décider)."""
    cle = comptes.cle_kapso()
    if not cle:
        raise KapsoErreur("Clé Kapso absente", code="cle_absente")
    chemin = _chemin(url)
    for essai in range(MAX_ESSAIS):
        panne = None
        try:
            statut, corps, entetes = await _requete(methode, url, json=json, params=params)
        except KapsoErreur:
            raise
        except Exception as e:  # noqa: BLE001 — le texte d'une exception réseau peut porter une URL : jamais recopié
            panne = type(e).__name__          # on ne garde que le nom : l'exception (et sa requête, avec la clé) est lâchée
        if panne is not None:                 # levée HORS du `except` : `__context__` reste vide
            logger.warning(f"kapso {methode} {chemin} : réseau ({panne})")
            raise KapsoErreur("Kapso injoignable", code="reseau", reessayable=True)
        if 200 <= statut < 300:
            return statut, corps, entetes
        code, message = _lire_erreur(statut, corps, cle)
        reessai = statut == 429 or (statut == 409 and code == "message_in_flight")
        if reessai and reessai_ok and essai < MAX_ESSAIS - 1:
            await _dormir(_attente(entetes, essai))
            continue
        if statut == 429:
            code = "429"
        logger.warning(f"kapso {methode} {chemin} -> {statut} {code}")
        raise KapsoErreur(message, statut=statut, code=code, reessayable=reessai)
    raise KapsoErreur("Kapso : essais épuisés", code="429", reessayable=True)     # inatteignable : la boucle a rendu ou levé


def _data(corps, genre: type):
    """Le contenu de `data` s'il a la forme attendue (dict ou list), sinon `reponse_invalide`."""
    d = corps.get("data") if isinstance(corps, dict) else None
    if not isinstance(d, genre):
        raise KapsoErreur("Réponse Kapso invalide", code="reponse_invalide")
    return d


# ---- Platform ---------------------------------------------------------------------------------------------------------

async def creer_customer(nom: str, externe: str) -> dict:
    """POST /customers : le customer Kapso d'un espace (`externe` = identifiant de l'espace)."""
    _s, corps, _e = await _appel("POST", f"{PLATFORM}/customers",
                                 json={"customer": {"name": nom, "external_customer_id": externe}})
    return _data(corps, dict)


async def creer_lien(customer_id: str, facturation: str, langue: str | None = None) -> dict:
    """POST /customers/{id}/setup_links : le lien de liaison hébergé. `facturation` = `customer_managed` | `partner_managed`
    (non modifiable ensuite). Le `token` de la réponse n'est JAMAIS rendu (réservé au SDK navigateur)."""
    lien = {"meta_billing_mode": facturation}
    if langue:
        lien["language"] = langue
    _s, corps, _e = await _appel("POST", f"{PLATFORM}/customers/{quote(str(customer_id), safe='')}/setup_links",
                                 json={"setup_link": lien})
    d = _data(corps, dict)
    return {"id": d.get("id"), "url": d.get("url"), "expire_le": d.get("expires_at"), "statut": d.get("status")}


async def liens(customer_id: str) -> list[dict]:
    """GET /customers/{id}/setup_links (plus récent d'abord) : où en est la liaison. Terminée = `whatsapp_setup_status`
    `completed` ; `whatsapp_setup_error` si `failed`. Première page seulement (20 par défaut)."""
    _s, corps, _e = await _appel("GET", f"{PLATFORM}/customers/{quote(str(customer_id), safe='')}/setup_links")
    return [{"id": x.get("id"), "statut": x.get("status"), "whatsapp_setup_status": x.get("whatsapp_setup_status"),
             "whatsapp_setup_error": x.get("whatsapp_setup_error"), "cree_le": x.get("created_at")}
            for x in _data(corps, list) if isinstance(x, dict)]


async def numeros(customer_id: str) -> list[dict]:
    """GET /whatsapp/phone_numbers?customer_id= : les numéros reliés d'un customer. Première page seulement."""
    _s, corps, _e = await _appel("GET", f"{PLATFORM}/whatsapp/phone_numbers", params={"customer_id": str(customer_id)})
    return [{"phone_number_id": x.get("phone_number_id") or x.get("id"),
             "display_phone_number": x.get("display_phone_number"), "verified_name": x.get("verified_name"),
             "quality_rating": x.get("quality_rating"), "status": x.get("status"),
             "business_account_id": x.get("business_account_id")}
            for x in _data(corps, list) if isinstance(x, dict)]


async def numero(phone_number_id: str) -> dict:
    """GET /whatsapp/phone_numbers/{id} : le détail d'un numéro."""
    _s, corps, _e = await _appel("GET", f"{PLATFORM}/whatsapp/phone_numbers/{quote(str(phone_number_id), safe='')}")
    return _data(corps, dict)


async def preferences_marketing(contact: str, *, phone_number_id: str | None = None) -> bool | None:
    """Le contact accepte-t-il les modèles MARKETING ? Vrai si `marketing_allowed` (ou aucune préférence : tableau vide, ou 404
    « Marketing preference not found » = abonné) ; faux si un arrêt est enregistré (sur ce numéro émetteur si
    `phone_number_id` est donné, sinon sur n'importe lequel) ; None si le contact est inconnu (autre 404). `contact` : numéro
    ou UUID du contact. Les autres erreurs sont levées."""
    try:
        _s, corps, _e = await _appel(
            "GET", f"{PLATFORM}/whatsapp/contacts/{quote(str(contact), safe='')}/marketing_preferences")
    except KapsoErreur as e:
        if e.statut != 404:
            raise
        return True if "preference not found" in e.message.lower() else None
    lignes = [x for x in _data(corps, list) if isinstance(x, dict)]
    if phone_number_id is not None:
        lignes = [x for x in lignes if str(x.get("phone_number_id")) == str(phone_number_id)]
    return all(x.get("marketing_allowed") is not False and x.get("status") != "stopped" for x in lignes)   # fermé


# ---- proxy WhatsApp ---------------------------------------------------------------------------------------------------

async def envoyer(phone_number_id: str, corps: dict) -> dict:
    """POST /{numéro}/messages : `corps` est le message Meta (type, to | recipient, contenu). `messaging_product` est ajouté ;
    un `to` vide est retiré (un BSUID va dans `recipient`, jamais dans `to`). Rend {"id" (wamid), "statut"}."""
    c = dict(corps)
    c.setdefault("messaging_product", "whatsapp")
    if not c.get("to"):
        c.pop("to", None)
    _s, rep, _e = await _appel("POST", f"{PROXY}/{quote(str(phone_number_id), safe='')}/messages", json=c)
    msgs = rep.get("messages") if isinstance(rep, dict) else None
    if not isinstance(msgs, list) or not msgs or not isinstance(msgs[0], dict) or not msgs[0].get("id"):
        raise KapsoErreur("Réponse Kapso invalide", code="reponse_invalide")
    return {"id": msgs[0]["id"], "statut": msgs[0].get("message_status") or "accepted"}


async def marquer_lu(phone_number_id: str, message_id: str) -> None:
    """POST /{numéro}/messages {status: read} : accusé de lecture d'un message reçu."""
    await _appel("POST", f"{PROXY}/{quote(str(phone_number_id), safe='')}/messages",
                 json={"messaging_product": "whatsapp", "status": "read", "message_id": message_id})


def _page(corps, limite: int) -> tuple[list, str | None]:
    liste = _data(corps, list)
    paging = corps.get("paging") if isinstance(corps, dict) else None
    cursors = paging.get("cursors") if isinstance(paging, dict) else None
    apres = cursors.get("after") if isinstance(cursors, dict) else None
    return liste, (str(apres) if apres and liste else None)     # jamais de curseur pour une page vide : `while cur:` s'arrête


async def messages(phone_number_id: str, *, depuis: str | None = None, apres: str | None = None,
                   limite: int = 100) -> tuple[list, str | None]:
    """GET /{numéro}/messages, plus récent d'abord. `depuis` = ISO 8601 (`since`, créés >=) ; `apres` = curseur de la page
    plus ancienne. Rend (messages, curseur `after`) ; le curseur est None pour une page vide (le proxy ne dit pas `next`) :
    une boucle `while cur:` s'arrête toujours."""
    limite = max(1, min(int(limite), 100))
    params: dict = {"limit": limite}
    if depuis:
        params["since"] = depuis
    if apres:
        params["after"] = apres
    _s, corps, _e = await _appel("GET", f"{PROXY}/{quote(str(phone_number_id), safe='')}/messages", params=params)
    return _page(corps, limite)


async def conversations(phone_number_id: str, *, apres: str | None = None, limite: int = 100,
                        champs: str | None = None) -> tuple[list, str | None]:
    """GET /{numéro}/conversations. `champs` (optionnel) = `fields` du proxy, par ex. `kapso()` pour l'extension
    (`last_inbound_at`, fenêtre 24 h). Rend (conversations, curseur `after`) ; curseur None pour une page vide."""
    limite = max(1, min(int(limite), 100))
    params: dict = {"limit": limite}
    if apres:
        params["after"] = apres
    if champs:
        params["fields"] = champs
    _s, corps, _e = await _appel("GET", f"{PROXY}/{quote(str(phone_number_id), safe='')}/conversations", params=params)
    return _page(corps, limite)


async def modeles(waba_id: str, *, statut: str = "APPROVED") -> list[dict]:
    """GET /{WABA}/message_templates?status= : les modèles (le chemin porte l'ID du compte WhatsApp Business, pas du numéro).
    Première page de 100 (aucun curseur d'entrée documenté)."""
    _s, corps, _e = await _appel("GET", f"{PROXY}/{quote(str(waba_id), safe='')}/message_templates",
                                 params={"status": statut, "limit": 100})
    return _data(corps, list)


def _url_media_sure(url) -> bool:
    """HTTPS, hôte exactement `api.kapso.ai`, port par défaut, sans identifiant dans l'URL."""
    try:
        u = urlparse(str(url))
        return (u.scheme == "https" and u.hostname == HOTE and u.port in (None, 443)
                and not u.username and not u.password)
    except ValueError:
        return False


async def media(media_id: str, phone_number_id: str) -> bytes:
    """Les octets d'un média reçu : GET /{media_id}?phone_number_id= donne `download_url` (valide 4 minutes, jeton intégré),
    téléchargée AUSSITÔT. Refusée AVANT tout appel si elle n'est pas en HTTPS sur `api.kapso.ai` ; aucune redirection suivie."""
    return (await media_et_type(media_id, phone_number_id))[0]


def _type_mime(v) -> str | None:
    """Un type MIME lisible (`image/jpeg`, paramètres ôtés), sinon None."""
    t = str(v or "").split(";", 1)[0].strip().lower()
    return t if re.match(r"^[a-z0-9.+-]+/[a-z0-9.+-]+$", t) else None


async def media_et_type(media_id: str, phone_number_id: str) -> tuple[bytes, str | None]:
    """t310 tâche 6 (27/10/2026) : comme `media`, avec le type MIME du fournisseur (`mime_type` de la fiche du média,
    sinon le `Content-Type` du téléchargement ; None s'il est illisible)."""
    _s, corps, _e = await _appel("GET", f"{PROXY}/{quote(str(media_id), safe='')}",
                                 params={"phone_number_id": str(phone_number_id)})
    url = corps.get("download_url") if isinstance(corps, dict) else None
    if not url:
        raise KapsoErreur("Kapso n'a pas donné d'adresse de téléchargement", code="media_sans_url")
    if not _url_media_sure(url):
        logger.warning("kapso media : adresse de téléchargement refusée (hôte ou schéma)")
        raise KapsoErreur("Adresse de téléchargement refusée", code="media_hote_refuse")
    _s, octets, entetes = await _appel("GET", str(url), reessai_ok=False)    # 4 min de vie : un seul essai, jamais d'attente
    if not isinstance(octets, (bytes, bytearray)):
        raise KapsoErreur("Réponse Kapso invalide", code="reponse_invalide")
    ct = next((v for k, v in (entetes or {}).items() if str(k).lower() == "content-type"), None)
    return bytes(octets), _type_mime(corps.get("mime_type")) or _type_mime(ct)
