"""Le canal WhatsApp d'un espace, par Kapso (t310, 27/10/2026) — partie LIAISON.

Spec §6.1 « Liaison d'un numéro dans l'assistant » : un numéro se relie par un LIEN D'INSTALLATION hébergé par Kapso
(connexion Facebook du client, sans compte Kapso à lui), jamais par saisie.
  1. `creer_lien` : consentement daté du client exigé si l'espace est GOUVERNÉ par un client (`espaces.client_responsable` :
     l'espace client lui-même, ou le produit d'un client — §11 bis, un produit suit son client), facturation Meta choisie
     AVANT le lien (`meta_billing_mode` ne se change plus ensuite), customer Kapso créé s'il manque
     (`external_customer_id` = l'espace), puis le lien. Le compte reçoit `KAPSO_CUSTOMER_ID` et `WHATSAPP_FACTURATION_META` ;
     la liaison `{lien_id, cree_le, expire_le, facturation, consentement}` va dans `espaces/<id>/whatsapp.json` (clé
     `liaison`, par compte). Le `token` du lien n'est jamais rendu par `kapso.creer_lien` : il ne peut donc aller nulle part.
  2. `relire_liaison` : SANS webhook (le PC n'a pas d'URL publique), relue à l'ouverture de l'écran et sur « Vérifier »,
     jamais en boucle : au plus un `kapso.liens` et un `kapso.numeros` par appel. Le customer est propre au compte : dès
     qu'UN de ses liens est `completed` (pas forcément le dernier créé), le premier numéro qu'aucun autre compte ne porte
     est rangé (`comptes.poser_publics_serveur`) ; un numéro = un espace. `lien_id` ne sert qu'à dire l'échec ou
     l'expiration du lien suivi. `pending`, `failed`, un lien expiré ou un numéro déjà pris ne rangent rien.
     Choix de Claude : la liaison vaut accord du client sur ce canal. Le consentement `whatsapp:<phone_number_id>` (permis
     `messages`, moyen de la liaison) va sur la fiche du CLIENT RESPONSABLE, AVANT le numéro (convergence : si l'écriture
     échoue, rien n'est rangé et la relecture suivante recommence) ; il est révocable dans la fiche client, et une
     révocation n'est jamais défaite. `fiche_client.ajouter_consentement` le date du jour de la liaison terminée (il ne prend
     pas de date) : la date donnée par l'utilisateur reste dans `whatsapp.json`.
     Une erreur de liaison porte un `code` ∈ `CODES_ERREUR` que l'écran traduit (`erreur` reste le détail brut).
  `ranger=False` : lecture pure (rien n'est écrit, rien n'est ajouté) — c'est ce qu'utilise la vérification.
Les deux gestes d'un même compte sont sérialisés (`_verrou_compte`, un asyncio.Lock par compte et par boucle) : deux
`creer_lien` simultanés ne créent jamais deux customers.

`whatsapp.json` : un seul écrivain atomique (`_modifier`, par `espaces._ecrire_json`) qui garde les autres clés de premier
niveau (`etat` appartient à la tâche 4, par `_poser_cle`). Absent : {}. Illisible (JSON) : mis de côté, jamais écrasé ;
une autre erreur de lecture remonte (on ne réécrit jamais un fichier qu'on n'a pas pu lire). Aucune clé, aucun jeton.
"""
import asyncio
import json
import re
import threading
import weakref
from datetime import date, datetime, timezone

from loguru import logger

from app.services import comptes, espaces as _es, kapso

FACTURATIONS = ("customer_managed", "partner_managed")
CODES_ERREUR = ("numero_deja_relie", "fournisseur", "expire")
FICHIER = "whatsapp.json"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LANGUE = re.compile(r"^[a-z]{2}(?:[-_][A-Za-z]{2})?$")
_verrou = threading.Lock()
_VERROUS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()     # boucle -> {cid: asyncio.Lock}


def _verrou_compte(cid: str) -> asyncio.Lock:
    """Le verrou asyncio du compte `cid` dans la boucle courante (un verrou ne sert qu'à la boucle qui l'a créé)."""
    par = _VERROUS.setdefault(asyncio.get_running_loop(), {})
    return par.setdefault(cid, asyncio.Lock())


# ---- whatsapp.json -------------------------------------------------------------------------------------------------------

def _lire_doc(eid: str) -> dict:
    """Le document `whatsapp.json` de l'espace ({} s'il manque). JSON illisible : mis de côté (`.illisible-<horodatage>`).
    Toute autre erreur de lecture (fichier verrouillé…) remonte."""
    f = _es.chemin(eid, FICHIER)
    if f is None:
        raise KeyError(eid)
    try:
        brut = f.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except UnicodeDecodeError:
        brut = None
    if brut is not None:
        try:
            doc = json.loads(brut)
            if isinstance(doc, dict):
                return doc
        except ValueError:
            pass
    cote = f.with_name(f"{FICHIER}.illisible-{datetime.now():%Y%m%d-%H%M%S}")
    f.replace(cote)
    logger.warning(f"{FICHIER} illisible : mis de côté ({cote.name})")
    return {}


def _modifier(eid: str, geste) -> None:
    """Relit, modifie (`geste(doc)`) et réécrit `whatsapp.json` sous verrou, atomiquement (`espaces._ecrire_json`)."""
    with _verrou:
        doc = _lire_doc(eid)
        geste(doc)
        _es._ecrire_json(_es.chemin(eid, FICHIER), doc)


def _poser_cle(eid: str, cle: str, valeur) -> None:
    """Écrit UNE clé de premier niveau de `whatsapp.json`, sans toucher aux autres."""
    _modifier(eid, lambda doc: doc.__setitem__(cle, valeur))


def _liaisons(eid: str) -> dict:
    lia = _lire_doc(eid).get("liaison")
    return lia if isinstance(lia, dict) else {}


def _ranger_liaison(eid: str, cid: str, liaison_: dict) -> None:
    """La liaison du compte `cid` sous la clé `liaison` (par compte : un espace peut porter plusieurs comptes whatsapp)."""
    def geste(doc):
        lia = doc.get("liaison") if isinstance(doc.get("liaison"), dict) else {}
        lia[cid] = liaison_
        doc["liaison"] = lia
    _modifier(eid, geste)


# ---- aides ------------------------------------------------------------------------------------------------------------

def _compte(cid: str) -> tuple[dict, dict]:
    """(vue, publics) d'un compte whatsapp. KeyError = compte ou espace inconnu ; ValueError = autre plateforme."""
    vue = comptes.obtenir(cid)
    if vue.get("plateforme") != "whatsapp":
        raise ValueError("ce compte n'est pas un compte WhatsApp")
    if _es.lire()["espaces"].get(vue.get("espace_id")) is None:
        raise KeyError(vue.get("espace_id"))
    pub = {ch["nom"]: str(ch.get("valeur") or "") for ch in vue.get("champs") or [] if not ch.get("secret")}
    return vue, pub


def _consentement(c) -> dict:
    """Le consentement daté du client à la liaison : {moyen ∈ fiche_client.MOYENS, date AAAA-MM-JJ réelle}. ValueError sinon."""
    from app.services import fiche_client
    ok = isinstance(c, dict) and c.get("moyen") in fiche_client.MOYENS and isinstance(c.get("date"), str) \
        and bool(_DATE.match(c["date"]))
    if ok:
        try:
            date.fromisoformat(c["date"])
        except ValueError:
            ok = False
    if not ok:
        raise ValueError("consentement daté du client exigé avant la liaison")
    return {"moyen": c["moyen"], "date": c["date"]}


def _expire(iso) -> bool:
    """Vrai si la date ISO 8601 est passée (illisible ou absente : faux)."""
    if not isinstance(iso, str) or not iso:
        return False
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return False
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d < datetime.now(timezone.utc)


def _porteurs(cid: str) -> dict:
    """phone_number_id -> espace_id, pour tous les AUTRES comptes whatsapp (tous espaces)."""
    out = {}
    for v in comptes.lister():
        if v.get("plateforme") != "whatsapp" or v.get("id") == cid:
            continue
        for ch in v.get("champs") or []:
            if ch.get("nom") == "WHATSAPP_PHONE_ID" and str(ch.get("valeur") or "").strip():
                out.setdefault(str(ch["valeur"]).strip(), v.get("espace_id"))
    return out


def _nom_espace(eid) -> str:
    e = _es.lire()["espaces"].get(eid) or {}
    return str(e.get("nom") or eid)


def _res(etat: str, erreur=None, numero=None, code=None, **extra) -> dict:
    return {"etat": etat, "erreur": erreur, "numero": numero, "code": code, **extra}


def _assurer_consentement(client, cons, pid: str, *, revoque_compte: bool) -> None:
    """Le consentement `whatsapp:<pid>` sur la fiche du client responsable, s'il n'en court pas déjà un.
    `revoque_compte=True` (numéro déjà relié) : un consentement révoqué sur ce canal compte aussi — une révocation n'est
    jamais défaite par une relecture. Les autres erreurs de la fiche remontent."""
    if not client or not isinstance(cons, dict):
        return
    from app.services import fiche_client
    canal = f"whatsapp:{pid}"
    if fiche_client.consentement_en_cours(client, canal):
        return
    if revoque_compte and any(x["canal_id"] == canal for x in fiche_client.lire(client)["consentements"]):
        return
    fiche_client.ajouter_consentement(client, canal, ["messages"], cons.get("moyen"))


# ---- la liaison -------------------------------------------------------------------------------------------------------

async def creer_lien(cid: str, facturation: str, consentement: dict | None, langue: str | None) -> dict:
    """Crée le lien d'installation du compte whatsapp `cid` et rend {"url", "expire_le", "facturation"}.
    KeyError = compte ou espace inconnu ; ValueError = refus (plateforme, facturation, consentement, numéro déjà relié) ;
    kapso.KapsoErreur = refus ou panne de Kapso (message déjà nettoyé)."""
    if facturation not in FACTURATIONS:
        raise ValueError("facturation Meta inconnue (customer_managed ou partner_managed)")
    async with _verrou_compte(cid):
        return await _creer_lien(cid, facturation, consentement, langue)


async def _creer_lien(cid: str, facturation: str, consentement, langue) -> dict:
    vue, pub = _compte(cid)
    eid = vue["espace_id"]
    if pub.get("WHATSAPP_PHONE_ID"):
        raise ValueError("ce compte WhatsApp est déjà relié à un numéro")
    cons = _consentement(consentement) if _es.client_responsable(eid) else None
    if pub.get("WHATSAPP_FACTURATION_META") and pub["WHATSAPP_FACTURATION_META"] != facturation:
        raise ValueError("la facturation Meta ne se change plus : créez un nouveau compte WhatsApp")
    langue = langue if isinstance(langue, str) and _LANGUE.match(langue) else None
    customer = pub.get("KAPSO_CUSTOMER_ID")
    if not customer:
        cree = await kapso.creer_customer(_nom_espace(eid)[:80], eid)
        customer = str(cree.get("id") or "")
        if not customer:
            raise kapso.KapsoErreur("Réponse Kapso invalide", code="reponse_invalide")
        # rangé AUSSITÔT : si le lien échoue, le prochain essai réutilise ce customer (jamais deux customers par compte)
        comptes.poser_publics_serveur(cid, {"KAPSO_CUSTOMER_ID": customer})
    lien = await kapso.creer_lien(customer, facturation, langue)
    if not lien.get("url"):
        raise kapso.KapsoErreur("Réponse Kapso invalide", code="reponse_invalide")
    if pub.get("WHATSAPP_FACTURATION_META") != facturation:
        comptes.poser_publics_serveur(cid, {"WHATSAPP_FACTURATION_META": facturation})
    _ranger_liaison(eid, cid, {"lien_id": lien.get("id"), "cree_le": _es._maintenant(), "expire_le": lien.get("expire_le"),
                               "facturation": facturation, "consentement": cons})
    return {"url": lien["url"], "expire_le": lien.get("expire_le"), "facturation": facturation}


async def relire_liaison(cid: str, ranger: bool = True) -> dict:
    """Où en est la liaison du compte `cid` : {"etat": aucune|en_cours|terminee|echouee|expiree, "erreur", "numero", "code"}
    (+ "espace" pour `numero_deja_relie`). Au plus un `kapso.liens` et un `kapso.numeros`. `ranger=True` : sur un lien
    `completed`, ajoute le consentement du client PUIS range le numéro ; `ranger=False` : lecture pure."""
    async with _verrou_compte(cid):
        return await _relire(cid, ranger)


async def _relire(cid: str, ranger: bool) -> dict:
    vue, pub = _compte(cid)
    eid = vue["espace_id"]
    lia = _liaisons(eid).get(cid)
    lia = lia if isinstance(lia, dict) else None
    client = _es.client_responsable(eid)
    if pub.get("WHATSAPP_PHONE_ID"):                     # déjà relié : aucune relecture chez Kapso
        pid = pub["WHATSAPP_PHONE_ID"]
        if ranger and lia:
            _assurer_consentement(client, lia.get("consentement"), pid, revoque_compte=True)
        return _res("terminee", numero={"phone_number_id": pid,
                                        "display_phone_number": pub.get("WHATSAPP_NUMERO") or None,
                                        "business_account_id": pub.get("WHATSAPP_WABA_ID") or None})
    customer = pub.get("KAPSO_CUSTOMER_ID")
    if not lia or not customer:
        return _res("aucune")
    liste = await kapso.liens(customer)
    if not any(x.get("whatsapp_setup_status") == "completed" for x in liste):
        suivi = next((x for x in liste if x.get("id") == lia.get("lien_id")), None)
        if suivi is not None and suivi.get("whatsapp_setup_status") == "failed":
            err = kapso._propre(suivi.get("whatsapp_setup_error") or "", comptes.cle_kapso()).strip()
            return _res("echouee", erreur=err or "liaison échouée chez Kapso", code="fournisseur")
        if (suivi is not None and suivi.get("statut") in ("expired", "revoked")) or _expire(lia.get("expire_le")):
            return _res("expiree", erreur="lien d'installation expiré", code="expire")
        return _res("en_cours")
    nums = [n for n in await kapso.numeros(customer) if str(n.get("phone_number_id") or "").strip()]
    if not nums:
        return _res("en_cours")                          # terminée, mais le numéro n'est pas encore visible
    porteurs = _porteurs(cid)
    libre = next((n for n in nums if str(n["phone_number_id"]).strip() not in porteurs), None)
    if libre is None:
        nom = _nom_espace(porteurs[str(nums[0]["phone_number_id"]).strip()])
        return _res("echouee", erreur=f"ce numéro est déjà relié à l'espace {nom}"[:200], code="numero_deja_relie",
                    espace=nom)
    pid = str(libre["phone_number_id"]).strip()
    numero = {"phone_number_id": pid, "display_phone_number": libre.get("display_phone_number"),
              "verified_name": libre.get("verified_name"), "business_account_id": libre.get("business_account_id")}
    if not ranger:
        return _res("terminee", numero=numero)
    # convergence : le consentement D'ABORD ; s'il échoue, aucun numéro n'est rangé et la relecture suivante recommence
    _assurer_consentement(client, lia.get("consentement"), pid, revoque_compte=False)
    comptes.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": pid,
                                        "WHATSAPP_NUMERO": libre.get("display_phone_number") or "",
                                        "WHATSAPP_WABA_ID": libre.get("business_account_id") or ""})
    _ranger_liaison(eid, cid, {**lia, "termine_le": _es._maintenant(), "phone_number_id": pid})
    return _res("terminee", numero=numero)
