"""Le canal WhatsApp d'un espace, par Kapso (t310, 27/10/2026) — partie LIAISON.

Spec §6.1 « Liaison d'un numéro dans l'assistant » : un numéro se relie par un LIEN D'INSTALLATION hébergé par Kapso
(connexion Facebook du client, sans compte Kapso à lui), jamais par saisie.
  1. `creer_lien` : consentement daté du client (espace `type == "client"` seulement), facturation Meta choisie AVANT le lien
     (`meta_billing_mode` ne se change plus ensuite), customer Kapso créé s'il manque (`external_customer_id` = l'espace),
     puis le lien. Le compte reçoit `KAPSO_CUSTOMER_ID` et `WHATSAPP_FACTURATION_META` ; la liaison
     `{lien_id, cree_le, expire_le, facturation, consentement}` va dans `espaces/<id>/whatsapp.json` (clé `liaison`, par
     compte). Le `token` du lien n'est jamais rendu par `kapso.creer_lien` : il ne peut donc aller nulle part.
  2. `relire_liaison` : SANS webhook (le PC n'a pas d'URL publique), relue à l'ouverture de l'écran et sur « Vérifier »,
     jamais en boucle : au plus un `kapso.liens` et un `kapso.numeros` par appel. Sur `completed`, le premier numéro
     qu'aucun autre compte ne porte est rangé (`comptes.poser_publics_serveur`) ; un numéro = un espace. Rien ne se range à
     moitié : `pending`, `failed`, un lien expiré ou un numéro déjà pris ne rangent rien.
     Choix de Claude : la liaison vaut accord du client sur ce canal. Pour un espace client, le consentement
     `whatsapp:<phone_number_id>` (permis `messages`, moyen de la liaison) est ajouté à la fiche une seule fois ; il est
     révocable dans la fiche client. `fiche_client.ajouter_consentement` le date du jour de la liaison terminée (il ne prend
     pas de date) : la date donnée par l'utilisateur reste dans `whatsapp.json`.

`whatsapp.json` : un seul écrivain atomique (`_poser_cle`, par `espaces._ecrire_json`) qui garde les autres clés de premier
niveau (`etat` appartient à la tâche 4). Un fichier illisible est mis de côté, jamais écrasé. Aucune clé, aucun jeton.
"""
import json
import re
import threading
from datetime import date, datetime, timezone

from loguru import logger

from app.services import comptes, espaces as _es, kapso

FACTURATIONS = ("customer_managed", "partner_managed")
FICHIER = "whatsapp.json"
ETATS_LIAISON = ("aucune", "en_cours", "terminee", "echouee", "expiree")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LANGUE = re.compile(r"^[a-z]{2}(?:[-_][A-Za-z]{2})?$")
_verrou = threading.Lock()


# ---- whatsapp.json -------------------------------------------------------------------------------------------------------

def _lire_doc(eid: str) -> dict:
    """Le document `whatsapp.json` de l'espace ({} s'il manque). Illisible : mis de côté (`.illisible-<horodatage>`)."""
    f = _es.chemin(eid, FICHIER)
    if f is None:
        raise KeyError(eid)
    try:
        brut = f.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        doc = json.loads(brut)
        if isinstance(doc, dict):
            return doc
    except ValueError:
        pass
    cote = f.with_name(f"{FICHIER}.illisible-{datetime.now():%Y%m%d-%H%M%S}")
    try:
        f.replace(cote)
        logger.warning(f"{FICHIER} illisible : mis de côté ({cote.name})")
    except OSError as e:
        logger.warning(f"{FICHIER} illisible, mise de côté impossible ({type(e).__name__})")
        raise
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

def _compte(cid: str) -> tuple[dict, dict, dict]:
    """(vue, publics, espace) d'un compte whatsapp. KeyError = compte ou espace inconnu ; ValueError = autre plateforme."""
    vue = comptes.obtenir(cid)
    if vue.get("plateforme") != "whatsapp":
        raise ValueError("ce compte n'est pas un compte WhatsApp")
    esp = _es.lire()["espaces"].get(vue.get("espace_id"))
    if esp is None:
        raise KeyError(vue.get("espace_id"))
    pub = {ch["nom"]: str(ch.get("valeur") or "") for ch in vue.get("champs") or [] if not ch.get("secret")}
    return vue, pub, esp


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


def _res(etat: str, erreur=None, numero=None) -> dict:
    return {"etat": etat, "erreur": erreur, "numero": numero}


# ---- la liaison -------------------------------------------------------------------------------------------------------

async def creer_lien(cid: str, facturation: str, consentement: dict | None, langue: str | None) -> dict:
    """Crée le lien d'installation du compte whatsapp `cid` et rend {"url", "expire_le", "facturation"}.
    KeyError = compte ou espace inconnu ; ValueError = refus (plateforme, facturation, consentement, numéro déjà relié) ;
    kapso.KapsoErreur = refus ou panne de Kapso (message déjà nettoyé)."""
    if facturation not in FACTURATIONS:
        raise ValueError("facturation Meta inconnue (customer_managed ou partner_managed)")
    vue, pub, esp = _compte(cid)
    eid = vue["espace_id"]
    if pub.get("WHATSAPP_PHONE_ID"):
        raise ValueError("ce compte WhatsApp est déjà relié à un numéro")
    cons = _consentement(consentement) if esp.get("type") == "client" else None
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


async def relire_liaison(cid: str) -> dict:
    """Où en est la liaison du compte `cid` : {"etat": aucune|en_cours|terminee|echouee|expiree, "erreur", "numero"}.
    Au plus un `kapso.liens` et un `kapso.numeros`. Range le numéro seulement sur `completed`, s'il n'est pas déjà pris."""
    vue, pub, esp = _compte(cid)
    eid = vue["espace_id"]
    if pub.get("WHATSAPP_PHONE_ID"):                     # déjà relié : aucune relecture chez Kapso
        return _res("terminee", numero={"phone_number_id": pub["WHATSAPP_PHONE_ID"],
                                        "display_phone_number": pub.get("WHATSAPP_NUMERO") or None,
                                        "business_account_id": pub.get("WHATSAPP_WABA_ID") or None})
    lia = _liaisons(eid).get(cid)
    customer = pub.get("KAPSO_CUSTOMER_ID")
    if not isinstance(lia, dict) or not customer:
        return _res("aucune")
    cle = comptes.cle_kapso()
    lien = next((x for x in await kapso.liens(customer) if x.get("id") == lia.get("lien_id")), None)
    if lien is None:                                     # absent de la première page : on s'en tient à la date connue
        return _res("expiree" if _expire(lia.get("expire_le")) else "en_cours")
    setup = lien.get("whatsapp_setup_status")
    if setup == "failed":
        err = kapso._propre(lien.get("whatsapp_setup_error") or "", cle).strip()
        return _res("echouee", erreur=err or "liaison échouée chez Kapso")
    if setup != "completed":
        if lien.get("statut") in ("expired", "revoked") or _expire(lia.get("expire_le")):
            return _res("expiree")
        return _res("en_cours")
    nums = [n for n in await kapso.numeros(customer) if str(n.get("phone_number_id") or "").strip()]
    if not nums:
        return _res("en_cours")                          # terminée, mais le numéro n'est pas encore visible
    porteurs = _porteurs(cid)
    libre = next((n for n in nums if str(n["phone_number_id"]).strip() not in porteurs), None)
    if libre is None:
        pris = porteurs[str(nums[0]["phone_number_id"]).strip()]
        return _res("echouee", erreur=f"ce numéro est déjà relié à l'espace {_nom_espace(pris)}"[:200])
    pid = str(libre["phone_number_id"]).strip()
    comptes.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": pid,
                                        "WHATSAPP_NUMERO": libre.get("display_phone_number") or "",
                                        "WHATSAPP_WABA_ID": libre.get("business_account_id") or ""})
    cons = lia.get("consentement")
    if esp.get("type") == "client" and isinstance(cons, dict):
        from app.services import fiche_client
        try:
            fiche_client.ajouter_consentement(eid, f"whatsapp:{pid}", ["messages"], cons.get("moyen"))
        except ValueError as e:                          # un consentement court déjà sur ce canal : la liaison tient
            logger.info(f"whatsapp liaison : consentement non ajouté ({type(e).__name__})")
    _ranger_liaison(eid, cid, {**lia, "termine_le": _es._maintenant(), "phone_number_id": pid})
    return _res("terminee", numero={"phone_number_id": pid, "display_phone_number": libre.get("display_phone_number"),
                                    "verified_name": libre.get("verified_name"),
                                    "business_account_id": libre.get("business_account_id")})
