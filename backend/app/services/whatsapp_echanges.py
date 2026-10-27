"""Le canal WhatsApp d'un espace, par Kapso (t310 tâche 6, 27/10/2026) — partie LECTURE ET ENVOI.

Spec §6.1 (« Coûts Meta », « Identité des contacts ») et §6.3 (règles dures). S'appuie sur `whatsapp.py` (liaison, règles,
état par NUMÉRO et réglages par espace dans `espaces/<id>/whatsapp.json`) et sur `kapso.py` (le seul client réseau). Module à part : `whatsapp.py`
porte déjà la liaison et les règles (décision 13 du contrôleur).
  · `lire` : les messages chez Kapso, à plat ; chaque ENTRANT passe une fois par `whatsapp.noter_entrant` (accord, STOP,
    journal sans texte). Le texte vient de Kapso, à la lecture seulement : il n'est jamais rangé.
  · `conversations` : les conversations (`fields=kapso()` pour `last_inbound_at`), avec la fenêtre de 24 h et le STOP.
  · `modeles` : les modèles APPROUVÉS du compte WhatsApp Business, paramètres lus dans le composant BODY.
  · `envoyer` : validation (400) ; pré-contrôle des règles SANS réseau (consentement, STOP, accord, plafond de messages) ;
    puis, sous le verrou du compte (`whatsapp._verrou_compte`) pour que deux envois simultanés ne passent pas le plafond :
    `controler` complet, préférence marketing de Kapso (avant un modèle MARKETING), devis (`pricing.estimate`, prix
    inconnu = refus `prix`), `plafonds.verifier` (402 inchangé), `kapso.envoyer`, puis journal et compteurs
    (`noter_envoi`) et `plafonds.rattacher` au wamid — seulement si Kapso a accepté le message.
    Un refus 4xx de Kapso après le devis remet la réservation à 0 (`plafonds.noter_reel_lignes(lignes, 0.0)`, précédent
    de l'agent Campagnes : un refus du fournisseur n'est pas facturé) ; un 5xx, une panne réseau ou une réponse illisible
    après un 2xx la laissent (le message a pu partir) et le journal le dit (chemin et type seulement).
    Avant le contrôle complet, les entrants récents chez Kapso passent par `noter_entrant` (`_relire_entrants`, même
    dédoublonnage que `lire`) : un STOP jamais lu dans l'écran bloque quand même l'envoi (fix 1, revue de e0ae86d6).
    `marketing_preference_stopped` et `131050` notent la désinscription (refus `marketing`) ; `131047` est rendu comme
    refus `fenetre`, jamais renvoyé en texte libre. Aucun autre réessai que celui de `kapso` (429).
  · `media` : les octets d'un média reçu et son type : le fichier rangé par `ranger_media` s'il existe, sinon Kapso (rien
    n'est écrit à ce moment-là).
  t311 tâche 2 (27/10/2026) : `lire` RANGE chaque média entrant neuf (`ranger_media`, `espaces/<id>/whatsapp_medias/<numéro>/
    <id>.<ext>`, 16 Mo au plus, 20 par lecture, un échec ne retire rien au message) ; `marquer_lu` (avec « en train d'écrire »),
    `fil` (un humain prend ou rend la conversation), `modeles(tous=)` avec `statut` et `composants` (entête, boutons), envoi
    de modèle avec `entete` et `boutons` (payloads), envoi `image`, envoi `boutons` avec `entete_media_id` et `ids` fournis.
Erreurs : `whatsapp.WhatsappRefus` (règles), ValueError (envoi ou compte invalide, compte non relié), KeyError (compte ou
espace inconnu), `kapso.KapsoErreur` (message déjà nettoyé), HTTPException 402 de `plafonds`. Aucune clé, aucun jeton.
"""
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

from app.services import espaces as _es, kapso, plafonds, pricing
from app.services import whatsapp as WA
from app.services.whatsapp import WhatsappRefus

MAX_TEXTE = 4096                  # texte libre (Meta)
MAX_CORPS_BOUTONS = 1024          # corps d'un message à boutons (relevé Kapso §2)
MAX_BOUTONS = 3
MAX_TITRE = 20
MAX_PARAMETRE = 1024
PAGES_MAX = 5                     # pages lues au plus pour retrouver une conversation ou un dernier entrant
TYPES_MEDIA = ("image", "video", "audio", "document", "sticker")
CODES_DESINSCRIPTION = ("marketing_preference_stopped", "131050")
CODE_FENETRE = "131047"
MAX_LEGENDE = 1024                # légende d'une image (Meta)
MAX_PAYLOAD = 128                 # payload d'un bouton de modèle (Meta)
MAX_BOUTONS_MODELE = 10
MAX_MEDIA_RANGE = 16 * 1024 * 1024
DELAI_REESSAI_MEDIA = timedelta(hours=6)   # un média non rangé (erreur Kapso) n'est redemandé qu'après ce délai
MAX_RANGES_PAR_LECTURE = 20       # médias entrants rangés au plus par appel de `lire`
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
              "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/amr": ".amr", "audio/aac": ".aac",
              "video/mp4": ".mp4", "video/3gpp": ".3gp", "application/pdf": ".pdf", "text/plain": ".txt"}
_MIME_DE = {v: k for k, v in EXTENSIONS.items()}
_ENTETES_MEDIA = ("image", "video", "document")
_MEDIA_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_ID_BOUTON = re.compile(r"^[A-Za-z0-9_:.-]{1,256}$")
_NOM_MODELE = re.compile(r"^[A-Za-z0-9_]{1,512}$")
_LANGUE_MODELE = re.compile(r"^[a-z]{2,3}(?:_[A-Za-z]{2,4})?$")
_NOM_PARAMETRE = re.compile(r"^[a-z0-9_]{1,64}$")
_JALON = re.compile(r"\{\{\s*([^{}\s]+)\s*\}\}")


def _horloge() -> datetime:
    """HOOK DE BANC : l'heure (UTC)."""
    return datetime.now(timezone.utc)


# ---- aides -------------------------------------------------------------------------------------------------------------

def _compte_relie(cid: str) -> tuple[dict, dict, str]:
    """(vue, publics, phone_number_id) d'un compte whatsapp RELIÉ. ValueError s'il n'a pas encore de numéro."""
    vue, pub = WA._compte(cid)
    pid = str(pub.get("WHATSAPP_PHONE_ID") or "").strip()
    if not pid:
        raise ValueError("ce compte WhatsApp n'est relié à aucun numéro")
    return vue, pub, pid


def _date_iso(v) -> datetime | None:
    """Une date ISO 8601 (« Z » accepté) en UTC, sinon None."""
    if not isinstance(v, str) or not v:
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return WA._utc(d)


def _date_ts(v) -> datetime | None:
    """Un horodatage Kapso (secondes Unix, en chaîne) en UTC, sinon None."""
    try:
        return datetime.fromtimestamp(int(str(v)), timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _entrant(msg: dict) -> bool:
    k = msg.get("kapso")
    return isinstance(k, dict) and k.get("direction") == "inbound"


def _identites_message(msg: dict, entrant: bool) -> list:
    """Les identités du contact d'un message (BSUID d'abord) : l'émetteur d'un entrant, le destinataire d'un sortant."""
    bsuid = str(msg.get("from_user_id" if entrant else "to_user_id") or "").strip()
    chiffres = re.sub(r"\D", "", str(msg.get("from" if entrant else "to") or ""))
    return ([f"bsuid:{bsuid}"] if bsuid else []) + ([f"tel:{chiffres}"] if chiffres else [])


def _identites_conv(cv: dict) -> list:
    bsuid = str(cv.get("business_scoped_user_id") or "").strip()
    chiffres = re.sub(r"\D", "", str(cv.get("phone_number") or ""))
    return ([f"bsuid:{bsuid}"] if bsuid else []) + ([f"tel:{chiffres}"] if chiffres else [])


def _groupe(e: dict, idents: list) -> set:
    """Les identités et leurs alias (même contact vu par BSUID et par numéro)."""
    out = set()
    for i in idents:
        out.update(WA._groupe(e, i))
    return out


def _texte(msg: dict):
    corps = msg.get(msg.get("type") or "text")
    if isinstance(corps, dict) and isinstance(corps.get("body"), str):
        return corps["body"]
    k = msg.get("kapso")
    return k.get("content") if isinstance(k, dict) and isinstance(k.get("content"), str) else None


def _plat(msg: dict) -> dict:
    """Un message Kapso à plat : {id, identite, sens, type, texte, quand, statut, media_id?, bouton?}."""
    entrant = _entrant(msg)
    idents = _identites_message(msg, entrant)
    k = msg.get("kapso") if isinstance(msg.get("kapso"), dict) else {}
    quand = _date_ts(msg.get("timestamp"))
    out = {"id": msg.get("id"), "identite": idents[0] if idents else None, "sens": "entrant" if entrant else "sortant",
           "type": msg.get("type"), "texte": _texte(msg), "quand": quand.isoformat(timespec="seconds") if quand else None,
           "statut": k.get("status")}
    media = msg.get(msg.get("type")) if msg.get("type") in TYPES_MEDIA else None
    if isinstance(media, dict) and media.get("id"):
        out["media_id"] = str(media["id"])
    bouton = _bouton(msg)
    if bouton:
        out["bouton"] = bouton
    return out


def _bouton(msg: dict) -> dict | None:
    """t311 tâche 6 : le bouton touché par le contact. Réponse à un message à boutons (`interactive.button_reply`) ->
    {"id", "titre"} ; bouton de réponse rapide d'un modèle (`button`) -> {"payload", "titre"}. Bornés (256 / 128 / 60)."""
    if msg.get("type") == "interactive":
        it = msg.get("interactive") if isinstance(msg.get("interactive"), dict) else {}
        br = it.get("button_reply") if isinstance(it.get("button_reply"), dict) else {}
        if br.get("id"):
            return {"id": str(br["id"])[:256], "titre": str(br.get("title") or "")[:60]}
    if msg.get("type") == "button":
        bt = msg.get("button") if isinstance(msg.get("button"), dict) else {}
        if bt.get("payload"):
            return {"payload": str(bt["payload"])[:MAX_PAYLOAD], "titre": str(bt.get("text") or "")[:60]}
    return None


def _marche(identite: str, defaut: str) -> str:
    """Le marché de prix d'une identité : l'indicatif le plus long de la grille saisie par lequel commence le numéro,
    sinon le marché par défaut du compte (toujours pour un BSUID seul)."""
    if not identite.startswith("tel:"):
        return defaut
    chiffres = identite[4:]
    grille = pricing.load().get("whatsapp_meta_usd")
    cles = [str(m) for m in (grille if isinstance(grille, dict) else {}) if str(m).isdigit() and chiffres.startswith(str(m))]
    return max(cles, key=len) if cles else defaut


# ---- lecture ---------------------------------------------------------------------------------------------------------

async def lire(cid: str, *, depuis: str | None = None, apres: str | None = None) -> dict:
    """Une page de messages (plus récents d'abord) : {"messages": [...], "suivant": curseur | None}. `depuis` : ISO 8601
    (créés depuis) ; `apres` : le curseur `suivant` d'une page précédente. Chaque entrant pas encore journalisé passe par
    `noter_entrant`, dans l'ordre chronologique, daté de son horodatage."""
    if depuis and _date_iso(depuis) is None:
        raise ValueError("depuis : une date ISO 8601 est attendue")
    vue, _pub, pid = _compte_relie(cid)
    liste, suivant = await kapso.messages(pid, depuis=depuis or None, apres=apres or None)
    liste = [m for m in liste if isinstance(m, dict)]
    _noter_entrants(cid, liste, _deja_journalises(cid))
    await _ranger_entrants(cid, vue["espace_id"], liste)
    return {"messages": [_plat(m) for m in liste], "suivant": suivant}


async def _ranger_entrants(cid: str, eid: str, liste: list) -> None:
    """Range les médias des messages ENTRANTS pas encore rangés (`MAX_RANGES_PAR_LECTURE` au plus par appel). Un échec
    (réseau, Kapso, disque, trop gros) ne retire rien au message : il est journalisé par `type(e).__name__` seulement."""
    n = 0
    for msg in liste:
        if n >= MAX_RANGES_PAR_LECTURE:
            break
        p = _plat(msg)
        mid = p.get("media_id")
        if p["sens"] != "entrant" or not mid or not _MEDIA_ID.match(mid):
            continue
        try:
            if _chemin_range(cid, eid, mid) is not None or not _refus_expire(cid, eid, mid):
                continue
            n += 1
            if await ranger_media(cid, eid, mid) is None:        # trop gros : marqué pour toujours par ranger_media
                continue
        except Exception as e:  # noqa: BLE001 — jamais un texte d'exception (une URL de média y porte un jeton)
            logger.warning(f"whatsapp média entrant non rangé ({type(e).__name__})")
            try:
                _noter_refus(cid, eid, mid, f"erreur:{type(e).__name__}")
            except Exception:  # noqa: BLE001
                pass


def _fichier_refus(cid: str, eid: str, media_id: str) -> Path:
    return _dossier_medias(cid, eid) / f"{_nom_fichier(media_id)}.refus"


def _noter_refus(cid: str, eid: str, media_id: str, raison: str) -> None:
    """Marqueur `<id>.refus` : horodatage ISO puis raison courte (jamais un texte de message ni d'exception)."""
    f = _fichier_refus(cid, eid, media_id)
    if not f.resolve().is_relative_to((_es.dossier() / eid).resolve()):
        raise ValueError("chemin de média refusé")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"{_horloge().isoformat(timespec='seconds')}\n{raison}\n", encoding="utf-8")


def _refus_expire(cid: str, eid: str, media_id: str) -> bool:
    """Vrai si on peut (re)tenter ce média : aucun marqueur, ou marqueur d'erreur vieux de 6 h au moins. `trop_gros` : jamais."""
    f = _fichier_refus(cid, eid, media_id)
    if not f.is_file():
        return True
    try:
        quand, _, raison = f.read_text(encoding="utf-8").partition("\n")
        if raison.strip() == "trop_gros":
            return False
        return _horloge() - _date_iso(quand.strip()) >= DELAI_REESSAI_MEDIA
    except (OSError, TypeError, ValueError):
        return True                                              # marqueur illisible : on retente


def _deja_journalises(cid: str) -> set:
    """Les ids (bornés comme au journal) des entrants déjà journalisés."""
    return {x.get("id") for x in WA.etat(cid)["journal"] if x.get("sens") == "entrant" and x.get("id")}


def _noter_entrants(cid: str, msgs: list, deja: set) -> None:
    """Passe par `noter_entrant`, du plus ancien au plus récent (une date d'accord ne recule jamais), chaque entrant
    pas encore journalisé. Un entrant SANS id est ignoré (il ne pourrait pas être dédoublonné) ; sans identité aussi."""
    for msg in sorted((m for m in msgs if isinstance(m, dict) and _entrant(m) and m.get("id")),
                      key=lambda m: _date_ts(m.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)):
        i = WA._c(msg.get("id"))
        if i in deja:
            continue
        quand = _date_ts(msg.get("timestamp"))
        try:                                             # horodatage illisible : daté de l'horloge, hors fenêtre
            WA.noter_entrant(cid, msg, maintenant=quand, heure_sure=quand is not None)
        except ValueError:
            continue                                     # entrant sans identité de contact : rien à ranger
        deja.add(i)


async def _relire_entrants(cid: str, pid: str) -> None:
    """Range les entrants récents chez Kapso (plus récents d'abord, PAGES_MAX pages au plus) : on s'arrête à la première
    page qui contient un entrant déjà journalisé. Le STOP, l'accord et l'heure du dernier entrant sont alors à jour."""
    deja = _deja_journalises(cid)
    lus, cur = [], None
    for _ in range(PAGES_MAX):
        liste, cur = await kapso.messages(pid, apres=cur)
        page = [m for m in liste if isinstance(m, dict) and _entrant(m) and m.get("id")]
        lus.extend(page)
        if not cur or any(WA._c(m.get("id")) in deja for m in page):
            break
    _noter_entrants(cid, lus, deja)


async def conversations(cid: str) -> list:
    """Les conversations du numéro : {id, identite, nom, dernier_entrant, fenetre_ouverte, stop} (PAGES_MAX pages au plus)."""
    _vue, _pub, pid = _compte_relie(cid)
    e = WA.etat(cid)
    maintenant = datetime.now(timezone.utc)
    out, cur = [], None
    for _ in range(PAGES_MAX):
        liste, cur = await kapso.conversations(pid, apres=cur, champs="kapso()")
        for cv in liste:
            if not isinstance(cv, dict):
                continue
            idents = _identites_conv(cv)
            k = cv.get("kapso") if isinstance(cv.get("kapso"), dict) else {}
            dernier = _date_iso(k.get("last_inbound_at"))
            out.append({"id": cv.get("id"), "identite": idents[0] if idents else None,
                        "nom": k.get("contact_name") or cv.get("username") or None,
                        "dernier_entrant": dernier.isoformat(timespec="seconds") if dernier else None,
                        "fenetre_ouverte": bool(dernier and maintenant - dernier < WA.FENETRE),
                        "stop": any(i in e["stops"] for i in _groupe(e, idents))})
        if not cur:
            break
    return out


async def _dernier_entrant(cid: str, pid: str, identite: str) -> datetime | None:
    """L'heure du dernier message du contact : la plus récente entre `kapso.last_inbound_at` de sa conversation
    (PAGES_MAX pages au plus) et les entrants journalisés (datés de leur horodatage Kapso, à jour après
    `_relire_entrants`), hors entrants à l'horodatage illisible (`heure_sure: False`). None = jamais (fenêtre fermée)."""
    e = WA.etat(cid)
    cible = _groupe(e, [identite])
    dates = [_date_iso(x.get("quand")) for x in e["journal"]       # fail closed : une heure non sûre n'ouvre rien
             if x.get("sens") == "entrant" and x.get("identite") in cible and x.get("heure_sure") is not False]
    cur = None
    for _ in range(PAGES_MAX):
        liste, cur = await kapso.conversations(pid, apres=cur, champs="kapso()")
        cv = next((x for x in liste if isinstance(x, dict) and cible & set(_identites_conv(x))), None)
        if cv is not None:
            k = cv.get("kapso") if isinstance(cv.get("kapso"), dict) else {}
            dates.append(_date_iso(k.get("last_inbound_at")))
            break
        if not cur:
            break
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def _composants(m: dict) -> dict:
    """{"entete": None|text|image|video|document, "boutons": [{"index", "type": quick_reply|url, "parametre": bool}]} :
    l'index est la place du bouton dans le composant BUTTONS (les autres genres de bouton comptent mais ne sont pas rendus)."""
    comps = [c for c in m.get("components") or [] if isinstance(c, dict)]
    ent = next((c for c in comps if str(c.get("type")).upper() == "HEADER"), None)
    fmt = str((ent or {}).get("format") or "").lower()
    boutons = []
    brut = next((c for c in comps if str(c.get("type")).upper() == "BUTTONS"), None)
    for i, b in enumerate((brut or {}).get("buttons") or []):
        if not isinstance(b, dict):
            continue
        genre = str(b.get("type") or "").upper()
        if genre == "QUICK_REPLY":
            boutons.append({"index": i, "type": "quick_reply", "parametre": False})
        elif genre == "URL":
            boutons.append({"index": i, "type": "url", "parametre": "{{" in str(b.get("url") or "")})
    return {"entete": fmt if fmt in ("text",) + _ENTETES_MEDIA else None, "boutons": boutons,
            "entete_variable": fmt == "text" and "{{" in str((ent or {}).get("text") or "")}


def _modele_plat(m: dict) -> dict:
    corps = next((c for c in m.get("components") or [] if isinstance(c, dict) and str(c.get("type")).upper() == "BODY"), {})
    jalons = list(dict.fromkeys(_JALON.findall(str(corps.get("text") or ""))))
    ex = corps.get("example") if isinstance(corps.get("example"), dict) else {}
    nommes = bool(ex.get("body_text_named_params")) or any(not j.isdigit() for j in jalons)
    return {"nom": m.get("name"), "langue": m.get("language"), "categorie": str(m.get("category") or "").lower(),
            "parametres": "nommes" if nommes else "positionnels", "n_parametres": len(jalons),
            "statut": str(m.get("status") or "").lower(), "composants": _composants(m)}


async def _modeles_bruts(pub: dict, tous: bool = False) -> list:
    waba = str(pub.get("WHATSAPP_WABA_ID") or "").strip()
    if not waba:
        raise ValueError("ce compte WhatsApp n'a pas de compte WhatsApp Business relié")
    brut = await kapso.modeles(waba, statut=None if tous else "APPROVED")
    return [m for m in brut if isinstance(m, dict) and m.get("name")
            and (tous or str(m.get("status") or "").upper() == "APPROVED")]


async def modeles(cid: str, *, tous: bool = False) -> list:
    """Les modèles APPROUVÉS (`tous=True` : tous les statuts) : {nom, langue, categorie, parametres: nommes|positionnels,
    n_parametres (composant BODY), statut, composants: {entete, boutons}}."""
    _vue, pub, _pid = _compte_relie(cid)
    return [_modele_plat(m) for m in await _modeles_bruts(pub, tous)]


async def marquer_lu(cid: str, message_id: str, ecrit: bool = False) -> None:
    """Accusé de lecture d'un message reçu ; `ecrit=True` : « en train d'écrire » chez le contact."""
    if not isinstance(message_id, str) or not message_id.strip():
        raise ValueError("identifiant de message invalide")
    _vue, _pub, pid = _compte_relie(cid)
    await kapso.marquer_lu(pid, message_id, ecrit=bool(ecrit))


async def fil(cid: str, identite: str, action: str) -> None:
    """Un humain prend (`prendre`) ou rend (`rendre`) la conversation avec `identite` chez Kapso (thread_control)."""
    dest = WA.destinataire(identite)                     # ValueError : identité invalide
    if action not in ("prendre", "rendre"):
        raise ValueError("action inconnue (prendre ou rendre)")
    _vue, _pub, pid = _compte_relie(cid)
    await (kapso.prendre_fil if action == "prendre" else kapso.rendre_fil)(pid, dest)


def _nom_fichier(media_id: str) -> str:
    """Un nom de fichier sûr : `_MEDIA_ID` vérifié, `:` (flux alternatif sous Windows) remplacé."""
    if not isinstance(media_id, str) or not _MEDIA_ID.match(media_id):
        raise ValueError("identifiant de média invalide")
    return media_id.replace(":", "_")


def _dossier_medias(cid: str, eid: str) -> Path:
    if not _es.id_valide(eid):
        raise ValueError("espace invalide")
    _vue, _pub, pid = _compte_relie(cid)
    if not re.match(r"^[A-Za-z0-9_.-]{1,64}$", pid) or pid in (".", ".."):
        raise ValueError("numéro WhatsApp invalide")
    return _es.dossier() / eid / "whatsapp_medias" / pid


def _chemin_range(cid: str, eid: str, media_id: str) -> Path | None:
    """Le fichier déjà rangé d'un média (n'importe quelle extension connue), sinon None."""
    base, nom = _dossier_medias(cid, eid), _nom_fichier(media_id)
    for ext in (*EXTENSIONS.values(), ".bin"):
        f = base / f"{nom}{ext}"
        if f.is_file():
            return f
    return None


async def ranger_media(cid: str, eid: str, media_id: str) -> Path | None:
    """Télécharge un média chez Kapso et le range sous `espaces/<eid>/whatsapp_medias/<numéro>/<id>.<ext>` (extension par
    MIME connu, sinon `.bin`). Déjà rangé : rend le fichier sans réseau. Plus de 16 Mo : rien n'est écrit, rend None.
    ValueError (identifiant, espace), `KapsoErreur` ou OSError sont levées à l'appelant."""
    nom = _nom_fichier(media_id)
    deja = _chemin_range(cid, eid, media_id)
    if deja is not None:
        return deja
    _vue, _pub, pid = _compte_relie(cid)
    octets, mime = await kapso.media_et_type(media_id, pid)
    mime = str(mime or "").split(";")[0].strip().lower()
    if len(octets) > MAX_MEDIA_RANGE:
        logger.warning("whatsapp média trop gros : non rangé")
        try:
            _noter_refus(cid, eid, media_id, "trop_gros")
        except OSError:
            pass
        return None
    base = _dossier_medias(cid, eid)
    cible = base / f"{nom}{EXTENSIONS.get(mime or '', '.bin')}"
    if not cible.resolve().is_relative_to((_es.dossier() / eid).resolve()):      # confinement
        raise ValueError("chemin de média refusé")
    base.mkdir(parents=True, exist_ok=True)
    tmp = cible.with_name(cible.name + ".part")
    tmp.write_bytes(octets)
    os.replace(tmp, cible)
    try:
        _fichier_refus(cid, eid, media_id).unlink(missing_ok=True)
    except OSError:
        pass
    return cible


async def media(cid: str, media_id: str) -> tuple[bytes, str | None]:
    """Les octets d'un média et son type MIME (None s'il est inconnu) : le fichier rangé (`ranger_media`) s'il existe,
    sinon Kapso (rien n'est écrit à ce moment-là)."""
    if not isinstance(media_id, str) or not _MEDIA_ID.match(media_id):
        raise ValueError("identifiant de média invalide")
    vue, _pub, pid = _compte_relie(cid)
    local = _chemin_range(cid, vue["espace_id"], media_id)
    if local is not None:
        return local.read_bytes(), _MIME_DE.get(local.suffix)
    return await kapso.media_et_type(media_id, pid)


# ---- envoi ------------------------------------------------------------------------------------------------------------

def _valider_envoi(envoi) -> dict:
    """L'envoi normalisé, ou ValueError (avant tout appel)."""
    if not isinstance(envoi, dict):
        raise ValueError("envoi invalide : un objet {type, …} est attendu")
    t = envoi.get("type")
    if t not in WA.TYPES_ENVOI:
        raise ValueError("type d'envoi inconnu (texte, boutons, modele ou image)")
    if t == "image":
        mid, leg = envoi.get("media_id"), envoi.get("legende")
        if not isinstance(mid, str) or not _MEDIA_ID.match(mid):
            raise ValueError("image : identifiant de média invalide")
        if leg is not None and (not isinstance(leg, str) or len(leg) > MAX_LEGENDE):
            raise ValueError(f"légende trop longue ({MAX_LEGENDE} caractères au plus)")
        return {"type": t, "media_id": mid, **({"legende": leg} if leg else {})}
    if t in ("texte", "boutons"):
        texte = envoi.get("texte")
        if not isinstance(texte, str) or not texte.strip():
            raise ValueError("le texte du message est vide")
        limite = MAX_TEXTE if t == "texte" else MAX_CORPS_BOUTONS
        if len(texte) > limite:
            raise ValueError(f"texte trop long ({limite} caractères au plus)")
        if t == "texte":
            return {"type": t, "texte": texte}
        b = envoi.get("boutons")
        if (not isinstance(b, list) or not 1 <= len(b) <= MAX_BOUTONS
                or not all(isinstance(x, str) and x.strip() and len(x.strip()) <= MAX_TITRE for x in b)):
            raise ValueError("boutons : 1 à 3 titres de 20 caractères au plus")
        titres = [x.strip() for x in b]
        if len(set(titres)) != len(titres):
            raise ValueError("boutons : deux titres identiques")
        out = {"type": t, "texte": texte, "boutons": titres}
        ids = envoi.get("ids")
        if ids is not None:
            if (not isinstance(ids, list) or len(ids) != len(titres) or len(set(map(str, ids))) != len(ids)
                    or not all(isinstance(i, str) and _ID_BOUTON.match(i) for i in ids)):
                raise ValueError("boutons : un identifiant par bouton (lettres, chiffres, _ : . - ; 256 au plus, tous différents)")
            out["ids"] = list(ids)
        em = envoi.get("entete_media_id")
        if em is not None:
            if not isinstance(em, str) or not _MEDIA_ID.match(em):
                raise ValueError("boutons : identifiant de média d'en-tête invalide")
            out["entete_media_id"] = em
        return out
    nom, langue = envoi.get("nom"), envoi.get("langue")
    if not isinstance(nom, str) or not _NOM_MODELE.match(nom) or not isinstance(langue, str) \
            or not _LANGUE_MODELE.match(langue):
        raise ValueError("modèle : nom et langue exigés")
    p = envoi.get("parametres", [])
    p = [] if p is None else p
    valeur = lambda v: (isinstance(v, (str, int, float)) and not isinstance(v, bool)    # noqa: E731
                        and 0 < len(str(v)) <= MAX_PARAMETRE)
    ok = (isinstance(p, list) and all(valeur(v) for v in p)) or (
        isinstance(p, dict) and all(isinstance(k, str) and _NOM_PARAMETRE.match(k) and valeur(v) for k, v in p.items()))
    if not ok:
        raise ValueError("paramètres du modèle : une liste ou un objet de textes")
    out = {"type": t, "nom": nom, "langue": langue, "parametres": p}
    ent = envoi.get("entete")
    if ent is not None:
        out["entete"] = _valider_entete(ent)
    bt = envoi.get("boutons")
    if bt is not None:
        out["boutons"] = _valider_boutons_modele(bt)
    return out


def _valider_entete(ent) -> dict:
    if not isinstance(ent, dict):
        raise ValueError("en-tête du modèle : un objet {type, …} est attendu")
    if ent.get("type") == "text":
        texte = ent.get("texte")
        if not isinstance(texte, str) or not texte.strip() or len(texte) > MAX_PARAMETRE:
            raise ValueError("en-tête du modèle : texte de 1 à 1024 caractères")
        return {"type": "text", "texte": texte}
    mid = ent.get("media_id")
    if ent.get("type") not in _ENTETES_MEDIA or not isinstance(mid, str) or not _MEDIA_ID.match(mid):
        raise ValueError("en-tête du modèle : image, video ou document avec un identifiant de média, ou un texte")
    return {"type": ent["type"], "media_id": mid}


def _valider_boutons_modele(bt) -> list:
    if not isinstance(bt, list) or len(bt) > MAX_BOUTONS_MODELE:
        raise ValueError("boutons du modèle : une liste de {index, payload}")
    out = []
    for b in bt:
        i, pl = (b.get("index"), b.get("payload")) if isinstance(b, dict) else (None, None)
        if (not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < MAX_BOUTONS_MODELE
                or not isinstance(pl, str) or not 1 <= len(pl) <= MAX_PAYLOAD):
            raise ValueError(f"boutons du modèle : index entier et payload de 1 à {MAX_PAYLOAD} caractères")
        out.append({"index": i, "payload": pl})
    if len({b["index"] for b in out}) != len(out):
        raise ValueError("boutons du modèle : deux fois le même index")
    return out


def _verifier_parametres(e_: dict, modele: dict) -> None:
    p = e_["parametres"]
    if p and isinstance(p, dict) != (modele["parametres"] == "nommes"):
        raise ValueError("paramètres du modèle : nommés ou positionnels comme le modèle")
    n = modele["n_parametres"]
    if len(p) != n:
        raise ValueError(f"le modèle attend {n} paramètre(s)")


def _verifier_composants(e_: dict, modele: dict) -> None:
    """L'en-tête et les boutons demandés existent dans le modèle (même genre d'en-tête ; boutons quick_reply)."""
    comp = modele["composants"]
    ent = e_.get("entete")
    if ent is not None and ent["type"] != comp["entete"]:
        raise ValueError("en-tête : le modèle n'a pas d'en-tête de ce genre")
    if ent is not None and ent["type"] == "text" and not comp.get("entete_variable"):
        raise ValueError("en-tête : un en-tête texte sans variable ne reçoit aucun texte")
    if ent is None and comp["entete"] in _ENTETES_MEDIA:
        raise ValueError("en-tête : ce modèle exige un en-tête média")
    permis = {b["index"] for b in comp["boutons"] if b["type"] == "quick_reply"}
    for b in e_.get("boutons") or []:
        if b["index"] not in permis:
            raise ValueError(f"bouton {b['index']} : le modèle n'a pas de bouton de réponse rapide à cette place")


def _corps(e_: dict) -> dict:
    """Le contenu Meta de l'envoi (sans destinataire). Modèle : en-tête, corps, boutons de réponse rapide (payloads)."""
    if e_["type"] == "texte":
        return {"type": "text", "text": {"body": e_["texte"]}}
    if e_["type"] == "image":
        img = {"id": e_["media_id"]}
        if e_.get("legende"):
            img["caption"] = e_["legende"]
        return {"type": "image", "image": img}
    if e_["type"] == "boutons":
        ids = e_.get("ids") or [f"b{i}" for i in range(1, len(e_["boutons"]) + 1)]
        inter = {"type": "button", "body": {"text": e_["texte"]}, "action": {
            "buttons": [{"type": "reply", "reply": {"id": i, "title": t}} for i, t in zip(ids, e_["boutons"])]}}
        if e_.get("entete_media_id"):
            inter = {"type": "button", "header": {"type": "image", "image": {"id": e_["entete_media_id"]}}, **{
                k: v for k, v in inter.items() if k != "type"}}
        return {"type": "interactive", "interactive": inter}
    p = e_["parametres"]
    params = ([{"type": "text", "parameter_name": k, "text": str(v)} for k, v in p.items()] if isinstance(p, dict)
              else [{"type": "text", "text": str(v)} for v in p])
    modele = {"name": e_["nom"], "language": {"code": e_["langue"]}}
    comps = []
    ent = e_.get("entete")
    if ent is not None:
        val = {"type": "text", "text": ent["texte"]} if ent["type"] == "text" else {
            "type": ent["type"], ent["type"]: {"id": ent["media_id"]}}
        comps.append({"type": "header", "parameters": [val]})
    if params:
        comps.append({"type": "body", "parameters": params})
    for b in e_.get("boutons") or []:
        comps.append({"type": "button", "sub_type": "quick_reply", "index": str(b["index"]),
                      "parameters": [{"type": "payload", "payload": b["payload"]}]})
    if comps:
        modele["components"] = comps
    return {"type": "template", "template": modele}


async def envoyer(cid: str, identite: str, envoi: dict) -> dict:
    """Envoie un message au contact `identite` (`tel:…` | `bsuid:…`) : {"id" (wamid), "statut", "devis"}. Voir l'en-tête du
    module pour l'ordre et les refus."""
    dest = WA.destinataire(identite)                     # ValueError : identité invalide
    e_ = _valider_envoi(envoi)
    vue, pub, pid = _compte_relie(cid)
    WA.espace_actif(vue["espace_id"])                   # un espace archivé n'envoie plus (400) ; ses lectures restent
    t0 = datetime.now(timezone.utc)
    # pré-contrôle SANS réseau : consentement, STOP, accord, plafond de messages (la fenêtre et la catégorie viennent après)
    WA.controler(cid, identite, type=e_["type"], categorie=None, dernier_entrant=t0, maintenant=t0)
    await _relire_entrants(cid, pid)                     # un STOP non lu chez Kapso compte aussi
    WA.controler(cid, identite, type=e_["type"], categorie=None, dernier_entrant=t0, maintenant=t0)
    categorie, dernier = None, None
    if e_["type"] == "modele":
        modele = next((_modele_plat(m) for m in await _modeles_bruts(pub)
                       if m.get("name") == e_["nom"] and m.get("language") == e_["langue"]), None)
        if modele is None:
            raise ValueError("modèle inconnu ou non approuvé pour cette langue")
        _verifier_parametres(e_, modele)
        _verifier_composants(e_, modele)
        categorie = modele["categorie"]
    else:
        dernier = await _dernier_entrant(cid, pid, identite)
    async with WA._verrou_compte(cid):
        return await _envoyer_sous_verrou(cid, vue["espace_id"], pid, identite, dest, e_, categorie, dernier)


async def _envoyer_sous_verrou(cid, eid, pid, identite, dest, e_, categorie, dernier) -> dict:
    maintenant = datetime.now(timezone.utc)
    WA.controler(cid, identite, type=e_["type"], categorie=categorie, dernier_entrant=dernier, maintenant=maintenant)
    if categorie == "marketing" and identite.startswith("tel:"):
        if await kapso.preferences_marketing(identite[4:], phone_number_id=pid) is False:
            WA.noter_desinscription(cid, identite)
            raise WhatsappRefus("ce contact est désinscrit des messages marketing", "marketing")
    cat = categorie if e_["type"] == "modele" else "service"
    etat = WA.etat(cid)
    marche = _marche(identite, etat["marche_defaut"])
    deja = int((etat["compteur"].get(WA._mois(maintenant)) or {}).get("service") or 0)
    op = {"kind": "whatsapp", "categorie": cat, "marche": marche, "service_deja_mois": deja}
    try:
        pricing.estimate(op)
    except ValueError:
        raise WhatsappRefus(f"prix WhatsApp inconnu pour {marche} / {cat} : saisissez la grille de Meta", "prix") from None
    garde = await plafonds.verifier(op, "whatsapp", espace_id=eid)       # 402 `dz_plafond` : rien n'est parti
    try:
        res = await kapso.envoyer(pid, {**dest, **_corps(e_)})
    except kapso.KapsoErreur as x:
        if 400 <= x.statut < 500:                        # refus du fournisseur : le message n'est pas parti
            await plafonds.noter_reel_lignes(garde["lignes"], 0.0)
        else:                                            # 5xx, réseau, réponse illisible : il a pu partir sans être compté
            logger.warning(f"whatsapp envoi /{pid}/messages : issue incertaine ({type(x).__name__} {x.code}), "
                           "réservation gardée")
        if x.code in CODES_DESINSCRIPTION:
            WA.noter_desinscription(cid, identite)
            raise WhatsappRefus("ce contact est désinscrit des messages marketing", "marketing") from None
        if x.code == CODE_FENETRE:
            raise WhatsappRefus("hors de la fenêtre de 24 h : seul un modèle peut partir", "fenetre") from None
        raise
    try:
        WA.noter_envoi(cid, identite, type=e_["type"], categorie=cat, statut=res["statut"], id=res["id"],
                       maintenant=maintenant)
    except Exception as x:
        logger.warning(f"whatsapp envoi /{pid}/messages : parti mais non compté ({type(x).__name__})")
        raise
    await plafonds.rattacher(garde["lignes"], str(res["id"]))
    return {"id": res["id"], "statut": res["statut"], "devis": garde["devis"]}
