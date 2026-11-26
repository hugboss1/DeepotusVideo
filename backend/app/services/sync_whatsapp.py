# -*- coding: utf-8 -*-
"""t321 (Compagnon M4, 26/11/2026) — WhatsApp vu et nourri par le téléphone.

Spec mère §6.3 et §10 (lecture « état d'un numéro », écriture PC n° 7), spec jumelle §3, D15 :
  · le téléphone envoie lui-même par Kapso, PC éteint, avec la clé plate `KAPSO_API_KEY` venue de l'archive DZKV1 ;
  · il juge ses envois avec LES MÊMES règles que `whatsapp.controler` (portées en TypeScript, figées par une fixture
    produite par ce code-ci) : il lui faut donc, par numéro, les accords, les STOP, les désinscrits marketing, les alias,
    les compteurs du mois, les réglages de l'espace et l'existence du consentement du client responsable ;
  · les accords, les STOP et le journal ont le PC pour SOURCE : le téléphone y dépose ses accords saisis, les STOP qu'il
    a lus chez Kapso ou notés à la main, et ses envois (écriture n° 7).

`lecture()` : aucune écriture, aucun réseau, jamais un secret ni un texte de message (le journal ne part pas).
`deposer(appareil, evenements)` : chaque événement est appliqué UNE fois. Son identifiant (préfixé par l'appareil du
JETON, jamais un champ du corps) est rangé dans `whatsapp.json` (clé `telephone.recus`, avec l'empreinte de l'événement)
DANS LE MÊME `_modifier` que son effet : renvoyé après une coupure, il est « déjà » ; même identifiant et autre contenu,
il est en « conflit » et rien n'est écrasé. Un STOP rejoint ensuite le registre des oppositions comme `noter_stop`.
Le téléphone ne dépose jamais d'ENTRANT : la relève du PC lit Kapso elle-même (sinon les entrants compteraient deux fois).
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from app.services import comptes, espaces as _es, whatsapp as _wa

VERSION = 1
MAX_EVENEMENTS = 200
MAX_RECUS = 5000
GENRES = ("accord", "stop", "envoi")
STATUTS = ("accepted", "sent", "delivered", "read", "failed", "envoye", "echec")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SOURCE = re.compile(r"^[^\x00-\x1f]{1,60}$")


class TropDEvenements(Exception):
    pass


def _numeros() -> list[tuple[str, str, dict]]:
    """(cid, phone_number_id, vue) de chaque compte WhatsApp relié à un numéro."""
    out = []
    for v in comptes.lister():
        if v.get("plateforme") != "whatsapp" or v.get("historique"):
            continue
        pub = {ch["nom"]: str(ch.get("valeur") or "") for ch in v.get("champs") or [] if not ch.get("secret")}
        pid = pub.get("WHATSAPP_PHONE_ID", "").strip()
        if pid:
            out.append((v["id"], pid, {**v, "_publics": pub}))
    return out


def _consentement_client(eid: str, pid: str) -> bool:
    try:
        _wa._exiger_consentement_client(eid, pid)
        return True
    except _wa.WhatsappRefus:
        return False


def lecture(maintenant: datetime | None = None) -> dict:
    """Les espaces qui ont au moins un numéro WhatsApp relié, avec ce qu'il faut au téléphone pour juger un envoi."""
    maintenant = maintenant or datetime.now(timezone.utc)
    vues = _es.lire()["espaces"]
    par_espace: dict = {}
    for cid, pid, v in _numeros():
        eid = v.get("espace_id")
        e = vues.get(eid)
        if e is None:
            continue
        if eid not in par_espace:
            doc = _wa._lire_doc(eid)
            r = _wa._reglages_doc(doc)
            vue = _es._vue(eid, e, "")
            par_espace[eid] = {
                "espace_id": eid, "nom": vue["nom"], "type": vue["type"], "archive": vue["archive"],
                "client_responsable": _es.client_responsable(eid),
                "reglages": {"plafond_mois": r["plafond_mois"], "marche_defaut": r["marche_defaut"],
                             "agent": _wa._agent_complet(r.get("agent"))},
                "mois": _wa._mois(maintenant), "total_mois": _wa._total_mois(doc, _wa._mois(maintenant)),
                "numeros": [], "_doc": doc}
        doc = par_espace[eid]["_doc"]
        etat = json.loads(json.dumps(_wa._etat_doc(doc, pid)))
        etat.pop("journal", None)                                    # jamais le journal (ni aucun texte de message)
        pub = v["_publics"]
        par_espace[eid]["numeros"].append({
            "cid": cid, "phone_number_id": pid, "waba_id": pub.get("WHATSAPP_WABA_ID") or None,
            "numero": pub.get("WHATSAPP_NUMERO") or None, "libelle": v.get("libelle") or "",
            "consentement_client": _consentement_client(eid, pid), "etat": etat})
    espaces = []
    for x in par_espace.values():
        x.pop("_doc", None)
        espaces.append(x)
    espaces.sort(key=lambda x: x["espace_id"])
    return {"version": VERSION, "genere_a": _wa._quand(maintenant), "espaces": espaces}


def _quand(v, maintenant: datetime) -> datetime:
    try:
        d = datetime.fromisoformat(str(v or "").replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("quand doit être une date ISO") from None
    d = _wa._utc(d)
    if d > maintenant + timedelta(hours=1):
        raise ValueError("événement daté dans le futur")
    if d < maintenant - timedelta(days=60):
        raise ValueError("événement trop ancien (plus de 60 jours)")
    return d


def _valider(ev, maintenant: datetime) -> dict:
    """L'événement propre (ValueError sinon). Le compte doit être un compte WhatsApp relié à un numéro."""
    if not isinstance(ev, dict):
        raise ValueError("événement illisible (objet attendu)")
    ident = str(ev.get("id") or "")
    if not _ID.match(ident):
        raise ValueError("identifiant d'événement invalide")
    genre = ev.get("genre")
    if genre not in GENRES:
        raise ValueError("genre inconnu (accord, stop ou envoi)")
    cid = str(ev.get("cid") or "")
    try:
        eid, pid = _wa._cle_etat(cid)
    except (KeyError, ValueError):
        raise ValueError("compte WhatsApp inconnu ou relié à aucun numéro") from None
    contact = _wa._identite_valide(ev.get("identite"))
    quand = _quand(ev.get("quand"), maintenant)
    p = {"id": ident, "genre": genre, "cid": cid, "eid": eid, "pid": pid, "identite": contact, "quand": quand}
    if genre == "accord":
        src = ev.get("source")
        if not isinstance(src, str) or not _SOURCE.match(src.strip() or "") or src.strip().lower() == "entrant":
            raise ValueError("source de l'accord exigée (un accord saisi : formulaire, papier, oral…), jamais « entrant »")
        p["source"] = "telephone:" + src.strip()[:48]
    elif genre == "envoi":
        if ev.get("type") not in _wa.TYPES_ENVOI:
            raise ValueError("type d'envoi inconnu (texte, boutons, modele ou image)")
        statut = str(ev.get("statut") or "")
        if statut not in STATUTS:
            raise ValueError("statut d'envoi inconnu")
        cat = ev.get("categorie")
        if cat is not None and (not isinstance(cat, str) or not re.match(r"^[A-Za-z_]{1,24}$", cat)):
            raise ValueError("catégorie invalide")
        wamid = ev.get("wamid")
        if wamid is not None and (not isinstance(wamid, str) or len(wamid) > 200):
            raise ValueError("identifiant de message invalide")
        p.update(type=ev["type"], categorie=cat, statut=statut, wamid=wamid)
    return p


def _empreinte(ev: dict) -> str:
    return hashlib.sha256(json.dumps(ev, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:32]


def _appliquer(doc: dict, p: dict) -> None:
    """L'effet de l'événement sur le document de l'espace — mêmes écritures que noter_accord / noter_stop / noter_envoi."""
    e = _wa._etat_doc(doc, p["pid"])
    q = _wa._quand(p["quand"])
    if p["genre"] == "accord":
        e["accords"][p["identite"]] = {"date": q, "source": p["source"]}
    elif p["genre"] == "stop":
        for i in _wa._groupe(e, p["identite"]):
            e["stops"].setdefault(i, q)
    else:
        m = e["compteur"].setdefault(_wa._mois(p["quand"]), {})
        m["sortants"] = int(m.get("sortants") or 0) + 1
        m["service"] = int(m.get("service") or 0) + (0 if p["type"] == "modele" else 1)
        _wa._journaliser(e, q, "sortant", p["identite"], p["type"], p["categorie"], p["statut"], p["wamid"])
        e["journal"][-1]["origine"] = "telephone"


def deposer(appareil: dict, evenements, maintenant: datetime | None = None) -> dict:
    """Rend {appliques, deja, conflits, refuses:[{id, raison}]}. Un refus n'écrit rien pour cet événement."""
    maintenant = _wa._utc(maintenant or datetime.now(timezone.utc))
    if not isinstance(evenements, list):
        raise ValueError("`evenements` doit être une liste")
    if len(evenements) > MAX_EVENEMENTS:
        raise TropDEvenements(f"au plus {MAX_EVENEMENTS} événements par envoi")
    prefixe = f"{str(appareil['id'])[:8]}:"
    appliques, deja, conflits, refuses, stops = [], [], [], [], []
    for ev in evenements:
        brut_id = str(ev.get("id") or "") if isinstance(ev, dict) else ""
        try:
            p = _valider(ev, maintenant)
            if p["genre"] == "envoi":
                _wa.espace_actif(p["eid"])            # un envoi depuis un espace archivé est refusé (ValueError)
        except ValueError as x:
            refuses.append({"id": brut_id, "raison": str(x)})
            continue
        cle, emp = prefixe + p["id"], _empreinte({k: v for k, v in ev.items() if k != "id"})
        issue = {}

        def geste(doc, p=p, cle=cle, emp=emp, issue=issue):
            tel = doc.get("telephone") if isinstance(doc.get("telephone"), dict) else {}
            recus = tel.get("recus") if isinstance(tel.get("recus"), dict) else {}
            if cle in recus:
                issue["r"] = "deja" if recus[cle] == emp else "conflit"
                return
            _appliquer(doc, p)
            recus[cle] = emp
            for k in list(recus)[:-MAX_RECUS]:
                recus.pop(k, None)
            tel["recus"] = recus
            doc["telephone"] = tel
            issue["r"] = "applique"
        _wa._modifier(p["eid"], geste)
        r = issue.get("r")
        (appliques if r == "applique" else deja if r == "deja" else conflits).append(p["id"])
        if r == "applique" and p["genre"] == "stop":
            stops.append(p)
    for p in stops:
        _wa._stop_au_registre(p["cid"], p["identite"])
    return {"appliques": appliques, "deja": deja, "conflits": conflits, "refuses": refuses}
