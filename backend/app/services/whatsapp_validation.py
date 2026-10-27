# -*- coding: utf-8 -*-
"""t311 tâche 6 (27/10/2026) — la validation d'un post par le CLIENT, par WhatsApp (spec boîte à outils §6.4).

`envoyer_validation(post_id)` (route POST /api/schedule/{id}/validation-whatsapp) : le post doit être `a_valider` ; le
client responsable de son espace (`espaces.client_responsable` : le client, ou le parent client d'un produit) doit avoir
un contact WhatsApp sur sa fiche (`contact.whatsapp`, texte libre normalisé par `whatsapp.numero_normalise` au marché de
l'espace client -> `tel:…`) et un compte whatsapp RELIÉ dans son espace. Les règles t310 s'appliquent avant tout geste
(consentement `whatsapp:<pid>` de la fiche, STOP, ACCORD du contact : sans accord, refus `accord` 409 — l'accord se note
sur la page WhatsApp, jamais ici). Aperçu : la `source_image` du post (bibliothèque) téléversée chez Kapso si JPEG ou PNG
de 5 Mo au plus, sinon texte seul. Fenêtre de 24 h ouverte -> message à boutons (ids `val:<post>:ok` / `val:<post>:corr`,
titres de BOUTONS selon `fiche.langue`) ; fermée -> le modèle `agent.modele_validation` des réglages de l'espace client
(sinon ValueError), en-tête image si le modèle en a un, boutons de réponse rapide 0 et 1 aux mêmes payloads. L'envoi passe
TOUJOURS par `whatsapp_echanges.envoyer` (règles, devis, `plafonds.verifier`). Puis
`validations[post] = {identite, cid, envoye_le, etat: "envoye", id}` dans `whatsapp_brouillons.json` de l'espace client
(sous le verrou de `agent_whatsapp`).

`traiter_reponse(cid, eid, msg_plat)` (appelé par le relevé de fond pour CHAQUE entrant neuf, avant tout le reste) :
  · bouton (`msg_plat["bouton"]`, id ou payload) `val:<post>:ok|corr` : exige une validation `envoye` du même contact
    (identité ou alias) et un post encore `a_valider` ; appelle `valider_post(post, "valide"|"corriger", "whatsapp")`
    (même logique que la route t309 : date, statut, journal de la fiche) ; état `valide` ou `a_corriger`. Sinon (post
    supprimé, déjà décidé, autre contact) : rien ne change, une ligne `validation_ignoree` SANS texte au journal de
    `whatsapp.json`, rend False ;
  · texte d'un contact dont une validation est `a_corriger` depuis moins de 24 h : rangé en `note` (≤ MAX_NOTE), état
    `corrige` ; la note se lit dans la fiche client (GET /api/schedule/{id}/client), elle n'est envoyée à aucun agent.
Rend True quand le message est consommé (le relevé ne le donne alors pas à l'agent). Aucun texte au journal (`logger`).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from loguru import logger

from app.services import agent_whatsapp as AW

MAX_NOTE = 2000
DELAI_NOTE = timedelta(hours=24)        # la note de « Corriger » : le premier texte du contact dans les 24 h
ETATS = ("envoye", "valide", "a_corriger", "corrige", "perimee")
EN_ATTENTE = ("envoye", "a_corriger")   # le relevé lit le compte même si l'agent est inactif
EXTENSIONS_APERCU = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
SIGNATURES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}
_ID = re.compile(r"^val:([A-Za-z0-9-]{1,64}):(ok|corr)$")
# Titres des boutons (≤ 20 caractères, Meta) par langue de la fiche ; corps vide : le texte de repli.
BOUTONS = {"fr": {"ok": "Valider", "corr": "Corriger", "vide": "Publication à valider"},
           "en": {"ok": "Approve", "corr": "Request changes", "vide": "Post to approve"}}


class PostInconnu(KeyError):
    """Le post n'existe pas (404 à la route)."""


def _horloge() -> datetime:
    """HOOK DE BANC : l'heure (UTC)."""
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds")


def _date(v) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def titres(langue: str) -> tuple[str, str]:
    """(« Valider », « Corriger ») dans la langue de la fiche (fr par défaut), 20 caractères au plus."""
    t = BOUTONS.get(langue) or BOUTONS["fr"]
    return t["ok"][:20], t["corr"][:20]


def ids(post_id: str) -> tuple[str, str]:
    return f"val:{post_id}:ok", f"val:{post_id}:corr"


# ---- lectures --------------------------------------------------------------------------------------------------------

async def _post(post_id: str):
    from sqlalchemy import select
    from app.services.storage import ScheduledPost, async_session_factory
    async with async_session_factory() as s:
        return (await s.execute(select(ScheduledPost).where(ScheduledPost.id == str(post_id)))).scalar_one_or_none()


def _compte_relie(eid: str) -> tuple[str, str] | None:
    """(cid, phone_id) du premier compte whatsapp RELIÉ de l'espace (ordre des ids), lu brut dans comptes.json."""
    from app.services import comptes
    for cid, e in sorted((comptes._lire().get("comptes") or {}).items()):
        if isinstance(e, dict) and e.get("plateforme") == "whatsapp" and e.get("espace_id") == eid:
            pid = str((e.get("publics") or {}).get("WHATSAPP_PHONE_ID") or "").strip()
            if pid:
                return cid, pid
    return None


def _apercu(source_image) -> tuple[bytes, str, str] | None:
    """(octets, mime, nom) de l'image du post si c'est un JPEG ou un PNG de la bibliothèque de 5 Mo au plus, sinon None."""
    from pathlib import Path
    from app.config import settings
    from app.services import kapso
    if not source_image:
        return None
    nom = Path(str(source_image)).name
    mime = EXTENSIONS_APERCU.get(Path(nom).suffix.lower())
    f = settings.images_path / nom
    try:
        if mime is None or not f.is_file() or not 0 < f.stat().st_size <= kapso.MAX_TELEVERSE:
            return None
        octets = f.read_bytes()
    except OSError:
        return None
    return (octets, mime, nom) if octets.startswith(SIGNATURES[mime]) else None


def validation_de(eid: str, post_id: str) -> dict | None:
    """La validation WhatsApp du post dans l'espace client (sans l'identité ni le compte), ou None."""
    try:
        v = AW.validations(eid).get(str(post_id))
    except KeyError:
        return None
    if not isinstance(v, dict):
        return None
    return {k: v[k] for k in ("etat", "envoye_le", "decide_le", "note", "note_le") if k in v}


def en_attente(eid: str, maintenant: datetime | None = None) -> bool:
    """L'espace a-t-il une validation qui attend une réponse (`envoye`) ou une note (`a_corriger` de moins de 24 h) ?
    KeyError : espace sans dossier."""
    now = maintenant or _horloge()
    for v in AW.validations(eid).values():
        if not isinstance(v, dict):
            continue
        if v.get("etat") == "envoye":
            return True
        d = _date(v.get("decide_le"))
        if v.get("etat") == "a_corriger" and d is not None and now - d < DELAI_NOTE:
            return True
    return False


# ---- l'envoi ---------------------------------------------------------------------------------------------------------

def _texte(post, langue: str) -> str:
    parts = [str(x).strip() for x in (post.title, post.caption) if isinstance(x, str) and x.strip()]
    t = "\n\n".join(parts) or (BOUTONS.get(langue) or BOUTONS["fr"])["vide"]
    from app.services import whatsapp_echanges as WE
    return t[:WE.MAX_CORPS_BOUTONS]


def _parametre(post, langue: str) -> str:
    """Le paramètre d'un modèle à UNE variable : le titre (repli : la légende, puis le texte de repli), sans retour à la
    ligne ni suite d'espaces (refusés par Meta dans un paramètre), 1024 caractères au plus."""
    for x in (post.title, post.caption):
        if isinstance(x, str) and x.strip():
            return re.sub(r"\s+", " ", x).strip()[:1024]
    return (BOUTONS.get(langue) or BOUTONS["fr"])["vide"]


async def envoyer_validation(post_id: str) -> dict:
    """Envoie au client la demande de validation du post : {"envoi": "boutons"|"modele", "id"}. Voir l'en-tête.
    PostInconnu (404) ; PermissionError (409) : post pas `a_valider` ou sans client ; WhatsappRefus (409) : règles ;
    ValueError (400) : fiche sans contact, aucun compte relié, fenêtre fermée sans modèle, modèle inadapté."""
    from app.services import espaces, fiche_client, kapso, whatsapp as WA, whatsapp_echanges as WE
    post = await _post(post_id)
    if post is None:
        raise PostInconnu(str(post_id))
    if post.status != "a_valider":
        raise PermissionError("ce post n'est pas à valider : rien à envoyer au client")
    client = espaces.client_responsable(post.espace_id) if post.espace_id else None
    if client is None:
        raise PermissionError("ce post n'est gouverné par aucun client")
    fiche = fiche_client.lire(client)
    langue = fiche.get("langue") if fiche.get("langue") in BOUTONS else "fr"
    relie = _compte_relie(client)
    if relie is None:
        raise ValueError("aucun numéro WhatsApp relié pour ce client")
    cid, pid = relie
    chiffres = WA.numero_normalise(fiche["contact"]["whatsapp"], WA.reglages(client)["marche_defaut"])
    if not 5 <= len(chiffres) <= 20:
        raise ValueError("la fiche du client n'a pas de numéro WhatsApp valide")
    identite = "tel:" + chiffres
    now = _horloge()
    WA.espace_actif(client)
    # les règles AVANT tout téléversement (consentement, STOP, accord, plafond) ; la fenêtre se juge à part
    WA.controler(cid, identite, type="boutons", categorie=None, dernier_entrant=now, maintenant=now)
    dernier = await WE._dernier_entrant(cid, pid, identite)
    ouverte = dernier is not None and now - dernier < WA.FENETRE
    modele = None
    if not ouverte:
        choix = WA.reglages(client)["agent"].get("modele_validation")
        if not isinstance(choix, dict) or not choix.get("nom"):
            raise ValueError("fenêtre de 24 h fermée : choisissez un modèle de validation dans les réglages WhatsApp "
                             "de l'espace")
        modele = next((m for m in await WE.modeles(cid)
                       if m.get("nom") == choix.get("nom") and m.get("langue") == choix.get("langue")), None)
        if modele is None:
            raise ValueError("modèle de validation inconnu ou non approuvé pour cette langue")
    apercu = _apercu(post.source_image)
    entete_image = modele is None or (modele.get("composants") or {}).get("entete") == "image"
    if modele is not None and (modele.get("composants") or {}).get("entete") == "image" and apercu is None:
        raise ValueError("le modèle de validation exige une image : ce post n'a pas d'image JPEG ou PNG")
    media_id = None
    if apercu is not None and entete_image:
        media_id = await kapso.televerser_media(pid, *apercu)
    ok, corr = ids(post.id)
    if modele is None:
        envoi = {"type": "boutons", "texte": _texte(post, langue), "boutons": list(titres(langue)), "ids": [ok, corr]}
        if media_id:
            envoi["entete_media_id"] = media_id
    else:
        n = modele.get("n_parametres") or 0
        envoi = {"type": "modele", "nom": modele["nom"], "langue": modele["langue"],
                 "parametres": [_parametre(post, langue)] if n == 1 and modele.get("parametres") != "nommes" else [],
                 "boutons": [{"index": 0, "payload": ok}, {"index": 1, "payload": corr}]}
        if media_id:
            envoi["entete"] = {"type": "image", "media_id": media_id}
    res = await WE.envoyer(cid, identite, envoi)
    neuf = {"identite": identite, "cid": cid, "envoye_le": _iso(_horloge()), "etat": "envoye", "id": str(res["id"])}

    def geste(vals):
        vals[str(post.id)] = neuf
        return vals
    AW.modifier_validations(client, geste)
    return {"envoi": envoi["type"], "id": res["id"]}


# ---- les réponses ----------------------------------------------------------------------------------------------------

def _meme_contact(cid: str, a: str, b: str) -> bool:
    from app.services import whatsapp as WA
    if not a or not b:
        return False
    if a == b:
        return True
    e = WA.etat(cid)
    return bool(set(WA._groupe(e, a)) & set(WA._groupe(e, b)))


def _ignorer(cid: str, identite, msg_id, quand) -> None:
    """Une ligne `validation_ignoree` au journal de whatsapp.json (sans texte), datée de l'entrant."""
    from app.services import whatsapp as WA
    try:
        WA._identite_valide(identite)
        q = _date(quand) or _horloge()
        WA._noter(cid, lambda e: WA._journaliser(e, _iso(q.astimezone(timezone.utc)), "entrant", identite, "bouton",
                                                  None, "validation_ignoree", msg_id))
    except Exception as e:  # noqa: BLE001 — la trace est un plus : jamais un échec du relevé pour elle
        logger.warning(f"validation WhatsApp : réponse ignorée non notée ({type(e).__name__})")


async def traiter_reponse(cid: str, eid: str, msg: dict) -> bool:
    """Voir l'en-tête du module. True = message consommé."""
    if not isinstance(msg, dict) or msg.get("sens") != "entrant" or not msg.get("identite"):
        return False
    identite = msg["identite"]
    b = msg.get("bouton") if isinstance(msg.get("bouton"), dict) else None
    m = _ID.match(str((b or {}).get("id") or (b or {}).get("payload") or ""))
    if m:
        return await _bouton(cid, eid, msg, identite, m.group(1), m.group(2))
    texte = msg.get("texte")
    if b is None and msg.get("type") == "text" and isinstance(texte, str) and texte.strip():
        return _note(cid, eid, identite, texte)
    return False


async def _bouton(cid, eid, msg, identite, post_id, choix) -> bool:
    v = AW.validations(eid).get(post_id)
    if not isinstance(v, dict) or v.get("etat") != "envoye" or not _meme_contact(cid, v.get("identite"), identite):
        _ignorer(cid, identite, msg.get("id"), msg.get("quand"))
        return False
    post = await _post(post_id)
    if post is None or post.status != "a_valider":           # supprimé, ou décidé au PC entre-temps
        _ignorer(cid, identite, msg.get("id"), msg.get("quand"))
        _poser(eid, post_id, "envoye", {"etat": "perimee", "decide_le": _iso(_horloge())})
        return False
    from fastapi import HTTPException
    from app.api.routes import valider_post
    try:
        await valider_post(post_id, "valide" if choix == "ok" else "corriger", "whatsapp")
    except HTTPException:                                      # 404 (supprimé à l'instant) ou 409 (plus de client)
        _ignorer(cid, identite, msg.get("id"), msg.get("quand"))
        _poser(eid, post_id, "envoye", {"etat": "perimee", "decide_le": _iso(_horloge())})
        return False
    _poser(eid, post_id, "envoye", {"etat": "valide" if choix == "ok" else "a_corriger", "decide_le": _iso(_horloge())})
    return True


def _poser(eid: str, post_id: str, si_etat: str, champs: dict) -> bool:
    """Met à jour la validation du post si elle est encore à l'état `si_etat` (sous le verrou du fichier)."""
    fait = []

    def geste(vals):
        v = vals.get(post_id)
        if not isinstance(v, dict) or v.get("etat") != si_etat:
            return None
        v.update(champs)
        fait.append(1)
        return vals
    AW.modifier_validations(eid, geste)
    return bool(fait)


def _note(cid: str, eid: str, identite: str, texte: str) -> bool:
    now = _horloge()
    cands = []
    for post_id, v in AW.validations(eid).items():
        d = _date((v or {}).get("decide_le")) if isinstance(v, dict) else None
        if (isinstance(v, dict) and v.get("etat") == "a_corriger" and d is not None and timedelta(0) <= now - d < DELAI_NOTE
                and _meme_contact(cid, v.get("identite"), identite)):
            cands.append((d, post_id))
    if not cands:
        return False
    _d, post_id = max(cands)
    return _poser(eid, post_id, "a_corriger", {"etat": "corrige", "note": texte.strip()[:MAX_NOTE], "note_le": _iso(now)})
