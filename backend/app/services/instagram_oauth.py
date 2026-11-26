# -*- coding: utf-8 -*-
"""t493 (lot G3, 26/11/2026) — Instagram : connexion OAuth « Instagram Login » (Business Login for Instagram).

PRÉPARÉ SANS LA DÉCISION D7 (application Meta propre, en mode développement ; revue d'application seulement quand des
clients relieront leur compte) : tout est INERTE tant que l'utilisateur n'a pas saisi IG_APP_ID et IG_APP_SECRET dans
Réglages › Comptes connectés. Le collage manuel (IG_ACCESS_TOKEN + IG_BUSINESS_ID, jeton EAA… de l'application
« Unified login » ou IG…) reste la voie de secours et n'est pas touché : la liaison ÉCRIT ces deux mêmes champs.

Doc Meta relue le 26/11/2026 (WebFetch + WebSearch) :
- developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login
  · autorisation : `https://www.instagram.com/oauth/authorize` ?client_id (ID de l'application INSTAGRAM, pas celui
    de l'application Meta) &redirect_uri &response_type=code &scope (« comma-separated or URL-encoded
    space-separated ») &state (facultatif, « such as for CSRF protection », rendu tel quel) ; enable_fb_login,
    force_reauth facultatifs ;
  · l'adresse de retour doit être EXACTEMENT l'une des « OAuth redirect URIs » déclarées dans App Dashboard › Instagram ›
    API setup with Instagram login › 3. Set up Instagram business login › Business login settings (le tableau de bord
    peut y ajouter une barre oblique finale) ; « #_ » est ajouté à la fin de l'adresse de retour : « strip it out » ;
  · code : « valid for 1 hour and can only be used once » ; échange `POST https://api.instagram.com/oauth/access_token`
    (client_id, client_secret, grant_type=authorization_code, redirect_uri, code) → `data: [{access_token, user_id,
    permissions}]` (jeton COURT, une heure) ;
  · jeton longue durée : `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret&
    access_token` « must be made in server-side code » → {access_token, token_type, expires_in} (5183944 s, ~60 j) ;
  · renouvellement : `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token`,
    jeton d'au moins 24 h, non expiré, `instagram_business_basic` accordé ; 60 jours de plus ; « Tokens that have not
    been refreshed in 60 days will expire and can no longer be refreshed ».
- …/reference/oauth-authorize : refus de l'utilisateur → error=access_denied, error_reason=user_denied ; scope :
  instagram_business_basic requis.
- …/docs/instagram-platform/insights et le billet du 24/03/2025 « User and media insights on Instagram API with
  Instagram Login » : `instagram_business_manage_insights` (absent de la page d'aperçu, présent sur la page Insights).
Ce que la doc NE DIT PAS (et qui contredit la fiche) :
- PKCE : aucune mention (ni code_challenge ni code_verifier) — l'échange exige le client_secret, côté serveur ; on
  n'envoie donc PAS de PKCE (un paramètre inconnu n'apporterait rien et pourrait être refusé). L'anti-rejeu tient au
  `state` aléatoire, à usage unique, borné à ETAT_DUREE_S.
- Boucle locale http : la doc ne dit ni oui ni non ; des retours de développeurs (communauté Meta, Strapi, NextAuth)
  disent que le champ des adresses refuse un http://localhost et n'accepte que https. Alternative la plus simple,
  sans serveur ni tunnel : déclarer chez Meta `https://localhost/` (réglage IG_OAUTH_REDIRECT) ; Instagram y renvoie
  le navigateur, la page ne s'affiche pas mais l'ADRESSE (code + state) est dans la barre : l'utilisateur la colle
  dans « Relier par Instagram » (`POST /api/oauth/instagram/retour`). Si Meta accepte la boucle locale
  (http://127.0.0.1:8765/api/oauth/instagram/callback, défaut) ou sur le VPS (https://<DEEPOTUS_HOSTNAME>/…, t534),
  le rappel direct `GET /api/oauth/instagram/callback` termine seul.

Garde-fous : le jeton longue durée ne va QUE dans le coffre OUVERT (refus 409 avant tout appel sinon : il ne serait
qu'en mémoire ou en clair au .env) ; le fichier d'état `scheduler/instagram_oauth.json` ne porte AUCUN secret (dates,
user_id, @nom, type de compte, dernière erreur nettoyée) ; aucun jeton, code ni secret dans un journal, une réponse ou
une URL rendue au navigateur (l'URL d'autorisation ne porte que l'ID public de l'application). Le renouvellement passe
une fois par jour avec la passe de métriques du Planificateur (`marketing.tick`) : jeton d'au moins 24 h, à moins de
RENOUVELER_AVANT_S de l'échéance.
"""
from __future__ import annotations

import json
import secrets
import time
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

import httpx
from loguru import logger

from app.config import DATA_ROOT, SSL_VERIFY, settings
from app.i18n import Refus

AUTH_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_URL = "https://graph.instagram.com/access_token"
REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
VERSION = "v25.0"                    # celle d'instagram_publisher
ME_URL = f"https://graph.instagram.com/{VERSION}/me"
SCOPES = ("instagram_business_basic", "instagram_business_content_publish", "instagram_business_manage_comments",
          "instagram_business_manage_insights")
CHEMIN_RAPPEL = "/api/oauth/instagram/callback"
ETAT_DUREE_S = 600                   # le code vit une heure ; l'état d'une autorisation lancée ici, dix minutes
ETATS_MAX = 16
AGE_MIN_S = 86400                    # « at least 24 hours old »
RENOUVELER_AVANT_S = 10 * 86400
TYPES_PRO = ("BUSINESS", "MEDIA_CREATOR")
HISTO = "historique-instagram"
_FICHIER = DATA_ROOT / "scheduler" / "instagram_oauth.json"

# state -> {compte, t, redirect} ; consommé une fois, borné
_ETATS: dict[str, dict] = {}


class RefusIG(Refus):
    """Un refus de la liaison, avec son statut HTTP ; texte = le français, traduit par la route."""

    def __init__(self, statut: int, cle: str, /, **vars):
        super().__init__(cle, **vars)
        self.statut = statut


def _client(timeout: float = 30.0) -> httpx.AsyncClient:          # seam des bancs
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def _app_secret() -> str:
    return str(getattr(settings, "IG_APP_SECRET", "") or "").strip()


def _app_id() -> str:
    return str(getattr(settings, "IG_APP_ID", "") or "").strip()


def configure() -> bool:
    """Vrai seulement quand l'ID ET le secret de l'application Instagram sont posés (sinon tout reste inerte)."""
    return bool(_app_id() and _app_secret())


def redirect_uri() -> str:
    """L'adresse de retour : celle réglée (IG_OAUTH_REDIRECT, http(s) seulement), sinon le rappel de ce backend."""
    from app.config import url_rappel
    r = str(getattr(settings, "IG_OAUTH_REDIRECT", "") or "").strip()
    if r and urlsplit(r).scheme in ("http", "https") and urlsplit(r).netloc:
        return r
    return url_rappel(CHEMIN_RAPPEL)


def _nettoyer(texte: str, *extra: str) -> str:
    s = str(texte or "")
    for v in (_app_secret(), *extra):
        if v:
            s = s.replace(v, "…")
    return s[:200]


def _detail_meta(r) -> str:
    """Le message d'erreur d'une réponse Meta (formes `error.message` ou `error_message`), explication connue d'abord."""
    try:
        corps = r.json()
    except Exception:  # noqa: BLE001
        corps = {}
    from app.services import meta_erreurs
    expl = meta_erreurs.expliquer(corps)
    if expl is not None:
        return str(expl)
    e = corps.get("error") if isinstance(corps, dict) else None
    if isinstance(e, dict):
        return str(e.get("message") or e.get("type") or "")
    if isinstance(corps, dict):
        return str(corps.get("error_message") or corps.get("error_type") or e or "")
    return ""


# ---- l'état gardé (aucun secret) --------------------------------------------------------------------------------------

def _lire() -> dict:
    try:
        d = json.loads(_FICHIER.read_text("utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("comptes"), dict) else {"comptes": {}}
    except (OSError, ValueError):
        return {"comptes": {}}


def _ecrire(doc: dict) -> None:
    _FICHIER.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FICHIER.with_name(_FICHIER.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False), "utf-8")
    tmp.replace(_FICHIER)


def _date(ts) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def _choix() -> list:
    """Les comptes Instagram que la liaison peut remplir : le compte des clés plates, puis ceux des espaces."""
    from app.services import comptes
    out = [{"id": HISTO, "libelle": "Instagram (Deepotus)", "espace_id": "deepotus", "historique": True}]
    for v in comptes.lister():
        if v.get("plateforme") == "instagram" and not v.get("historique") and not isinstance(v.get("porte_par"), dict):
            out.append({"id": v["id"], "libelle": v.get("libelle") or "Instagram", "espace_id": v.get("espace_id"),
                        "historique": False})
    return out


def etat(maintenant: float | None = None) -> dict:
    """{configure, redirect_uri, redirect_regle, scopes, coffre_ouvert, choix, comptes{id: dates…}} — jamais un secret."""
    from app.services import coffre
    t = time.time() if maintenant is None else maintenant
    comptes_ = {}
    for cid, e in _lire()["comptes"].items():
        v = {k: e.get(k) for k in ("user_id", "username", "account_type", "obtenu_ts", "expire_ts", "renouvele_ts",
                                   "erreur")}
        v["expire"] = _date(e.get("expire_ts"))
        v["expire_passe"] = bool(e.get("expire_ts")) and float(e["expire_ts"]) <= t
        comptes_[cid] = v
    try:
        choix = _choix()
    except Exception:  # noqa: BLE001 — une liste illisible ne casse pas l'état
        choix = [{"id": HISTO, "libelle": "Instagram (Deepotus)", "espace_id": "deepotus", "historique": True}]
    return {"configure": configure(), "redirect_uri": redirect_uri(),
            "redirect_regle": bool(str(getattr(settings, "IG_OAUTH_REDIRECT", "") or "").strip()),
            "scopes": list(SCOPES), "coffre_ouvert": coffre.ouvert(), "choix": choix, "comptes": comptes_}


# ---- démarrer ---------------------------------------------------------------------------------------------------------

def _verifier_compte(compte) -> str | None:
    """None (clés plates) ou l'id d'un compte Instagram existant. RefusIG 404 / 400 sinon."""
    from app.services import comptes
    if not compte or compte == HISTO:
        return None
    try:
        vue = comptes.obtenir(compte)
    except KeyError:
        raise RefusIG(404, "ig.oauth.compte_inconnu", compte=str(compte)[:40]) from None
    if vue.get("plateforme") != "instagram":
        raise RefusIG(400, "ig.oauth.pas_instagram", compte=str(compte)[:40])
    return compte


def _exiger_pret() -> None:
    from app.services import coffre
    if not configure():
        raise RefusIG(400, "ig.oauth.non_configure")
    if not coffre.ouvert():
        raise RefusIG(409, "ig.oauth.coffre_requis")


def demarrer(compte=None, maintenant: float | None = None) -> str:
    """L'URL d'autorisation Instagram (à ouvrir dans le navigateur). Rien ne part vers Meta ici."""
    _exiger_pret()
    cid = _verifier_compte(compte)
    t = time.time() if maintenant is None else maintenant
    for s in [s for s, e in _ETATS.items() if t - e["t"] > ETAT_DUREE_S]:
        _ETATS.pop(s, None)
    while len(_ETATS) >= ETATS_MAX:
        _ETATS.pop(next(iter(_ETATS)))
    state = secrets.token_hex(16)
    uri = redirect_uri()
    _ETATS[state] = {"compte": cid, "t": t, "redirect": uri}
    return AUTH_URL + "?" + urlencode({"client_id": _app_id(), "redirect_uri": uri, "response_type": "code",
                                       "scope": ",".join(SCOPES), "state": state})


def lire_retour(adresse: str) -> tuple[str, str, str]:
    """(code, state, erreur) de l'adresse où Instagram a renvoyé le navigateur (collée par l'utilisateur)."""
    a = str(adresse or "").strip()
    q = {k: v[0] for k, v in parse_qs(urlsplit(a).query).items() if v}
    code = unquote(q.get("code", "")).strip()
    if code.endswith("#_"):
        code = code[:-2]
    err = q.get("error_reason") or q.get("error") or ""
    return code, q.get("state", "").strip(), err[:60]


# ---- terminer ---------------------------------------------------------------------------------------------------------

def _garder(cid, jeton: str, user_id: str | None) -> None:
    """Le jeton AU COFFRE (ouvert, vérifié avant) et l'id du compte en champ public, pour le compte de la liaison."""
    from app.services import coffre, comptes
    if cid:
        with comptes.sous_compte(cid):
            comptes.garder_secret("IG_ACCESS_TOKEN", jeton)
        if user_id is not None:
            comptes.poser(cid, {"IG_BUSINESS_ID": user_id})
        return
    coffre.ecrire_cle("IG_ACCESS_TOKEN", jeton)
    if "IG_ACCESS_TOKEN" in coffre.lire_env():         # un ancien jeton collé en clair : le coffre le remplace
        coffre._ecrire_env({}, {"IG_ACCESS_TOKEN"})
    if user_id is not None:
        coffre._ecrire_env({"IG_BUSINESS_ID": user_id}, set())
        coffre._appliquer({"IG_BUSINESS_ID": user_id})


async def terminer(code: str, state: str, erreur: str = "", maintenant: float | None = None) -> dict:
    """Échange le code, obtient le jeton longue durée, vérifie le compte, le range au coffre. RefusIG sinon."""
    ent = _ETATS.pop(state, None) if state else None
    t = time.time() if maintenant is None else maintenant
    if not ent or t - ent["t"] > ETAT_DUREE_S:
        raise RefusIG(400, "ig.oauth.etat_refuse")
    if erreur:
        raise RefusIG(400, "ig.oauth.refus_utilisateur", raison=str(erreur)[:60])
    code = str(code or "").strip()
    if code.endswith("#_"):
        code = code[:-2]
    if not code:
        raise RefusIG(400, "ig.oauth.code_absent")
    _exiger_pret()
    cid = ent["compte"]
    court = long_ = ""
    try:
        async with _client() as c:
            r = await c.post(TOKEN_URL, data={"client_id": _app_id(), "client_secret": _app_secret(),
                                              "grant_type": "authorization_code", "redirect_uri": ent["redirect"],
                                              "code": code})
            if r.status_code != 200:
                raise RefusIG(502, "ig.oauth.meta_refuse", etape="code", code=r.status_code,
                              detail=_nettoyer(_detail_meta(r), code))
            j = r.json() if isinstance(r.json(), dict) else {}
            d = (j.get("data") or [j])[0] if isinstance(j.get("data"), list) else j     # forme d'avant : à plat
            court = str((d or {}).get("access_token") or "")
            if not court:
                raise RefusIG(502, "ig.oauth.meta_refuse", etape="code", code=r.status_code, detail="access_token ?")
            r = await c.get(LONG_URL, params={"grant_type": "ig_exchange_token", "client_secret": _app_secret(),
                                              "access_token": court})
            if r.status_code != 200 or not (r.json() or {}).get("access_token"):
                raise RefusIG(502, "ig.oauth.meta_refuse", etape="ig_exchange_token", code=r.status_code,
                              detail=_nettoyer(_detail_meta(r), code, court))
            long_ = str(r.json()["access_token"])
            duree = int(r.json().get("expires_in") or 5184000)
            r = await c.get(ME_URL, params={"fields": "user_id,username,account_type", "access_token": long_})
            if r.status_code != 200:
                raise RefusIG(502, "ig.oauth.meta_refuse", etape="me", code=r.status_code,
                              detail=_nettoyer(_detail_meta(r), code, court, long_))
            me = r.json() or {}
    except RefusIG:
        raise
    except Exception as e:  # noqa: BLE001 — le type seul : un message réseau peut porter une URL et son jeton
        logger.warning(f"t493 liaison Instagram : panne réseau ({type(e).__name__})")
        raise RefusIG(502, "ig.oauth.reseau", type=type(e).__name__) from None
    nom = str(me.get("username") or "")[:60]
    uid = str(me.get("user_id") or me.get("id") or (d or {}).get("user_id") or "")[:40]
    typ = str(me.get("account_type") or "").upper()[:30]
    if typ not in TYPES_PRO:
        raise RefusIG(400, "ig.oauth.compte_personnel", nom=nom or "?", type=typ or "?")
    _garder(cid, long_, uid or None)
    cle = cid or HISTO
    doc = _lire()
    doc["comptes"][cle] = {"user_id": uid, "username": nom, "account_type": typ, "obtenu_ts": t, "expire_ts": t + duree,
                           "renouvele_ts": None, "erreur": None}
    _ecrire(doc)
    logger.info(f"t493 Instagram relié : @{nom} ({typ}), jeton au coffre jusqu'au {_date(t + duree)}")
    verif = None
    try:
        from app.services import comptes, verif_canaux
        comptes.oublier_verification(cle)
        verif = ((await verif_canaux.verifier(cle)).get("verification") or {}).get("etat")
    except Exception as e:  # noqa: BLE001 — le jeton est rangé : une vérification ratée ne défait pas la liaison
        logger.warning(f"t493 vérification après liaison : {type(e).__name__}")
    return {"ok": True, "compte": cle, "username": nom, "user_id": uid, "account_type": typ, "ou": "coffre",
            "expire": _date(t + duree), "expire_ts": t + duree, "verification": verif}


# ---- renouveler -------------------------------------------------------------------------------------------------------

async def renouveler(cle: str, maintenant: float | None = None) -> bool:
    """Renouvelle le jeton du compte `cle` (ig_refresh_token). Vrai si un jeton neuf est au coffre."""
    from app.services import coffre, comptes
    t = time.time() if maintenant is None else maintenant
    cid = None if cle == HISTO else cle
    if not coffre.ouvert():
        return False
    with comptes.sous_compte(cid):
        tok = str(comptes.cred.IG_ACCESS_TOKEN or "").strip()
    if not tok.startswith("IG"):                    # un jeton EAA collé à la main ne se renouvelle pas ici
        return False
    erreur = None
    neuf, duree = "", 0
    try:
        async with _client() as c:
            r = await c.get(REFRESH_URL, params={"grant_type": "ig_refresh_token", "access_token": tok})
        if r.status_code == 200 and (r.json() or {}).get("access_token"):
            neuf, duree = str(r.json()["access_token"]), int(r.json().get("expires_in") or 5184000)
        else:
            erreur = f"{r.status_code} : {_nettoyer(_detail_meta(r), tok)}"
    except Exception as e:  # noqa: BLE001
        erreur = type(e).__name__
    doc = _lire()
    e = doc["comptes"].get(cle)
    if e is None:
        return False
    if neuf:
        _garder(cid, neuf, None)
        e.update({"expire_ts": t + duree, "renouvele_ts": t, "erreur": None})
        logger.info(f"t493 jeton Instagram renouvelé ({cle}) jusqu'au {_date(t + duree)}")
    else:
        e["erreur"] = _nettoyer(erreur or "", tok, neuf)
        logger.warning(f"t493 renouvellement Instagram ({cle}) refusé : {e['erreur']}")
    _ecrire(doc)
    return bool(neuf)


async def renouveler_dus(maintenant: float | None = None) -> list:
    """Les comptes reliés dont le jeton a au moins 24 h et expire dans moins de RENOUVELER_AVANT_S : renouvelés.
    Coffre fermé : rien (aucun appel). Jeton déjà expiré : noté, aucun appel (il faut relier à nouveau)."""
    from app.services import coffre
    t = time.time() if maintenant is None else maintenant
    if not coffre.ouvert():
        return []
    faits = []
    for cle, e in list(_lire()["comptes"].items()):
        try:
            exp = float(e.get("expire_ts") or 0)
            depuis = float(e.get("renouvele_ts") or e.get("obtenu_ts") or 0)
        except (TypeError, ValueError):
            continue
        if exp <= t or t - depuis < AGE_MIN_S or exp - t > RENOUVELER_AVANT_S:
            continue
        try:
            if await renouveler(cle, t):
                faits.append(cle)
        except Exception as ex:  # noqa: BLE001 — un compte en panne n'arrête pas les autres
            logger.warning(f"t493 renouvellement Instagram ({cle}) : {type(ex).__name__}")
    return faits
