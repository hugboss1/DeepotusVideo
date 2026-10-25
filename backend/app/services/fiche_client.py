# -*- coding: utf-8 -*-
"""t306 (25/10/2026) — la FICHE d'un client : `DATA_ROOT/espaces/<id>/client.json`, format v1 (repris tel quel par le
compagnon mobile, cf. tests/fixtures_client_v1.json). Contact, mode de publication (`valide_par_client` par défaut :
le plus prudent), consentements DATÉS par identifiant de canal (`plateforme:identifiant`), révocation, et un journal
des gestes (2000 lignes au plus, les plus anciennes sortent).

Règles gardées ici : `valider` est une normalisation PURE (clés inconnues ignorées, absences remplacées par les défauts,
lignes fautives écartées) partagée par `lire` et par l'import ; `ecrire` ignore les clés inconnues mais refuse
`consentements` et `journal` (ils ont leurs propres gestes) ; rien n'est jamais écrit par une lecture.
`lire` appelle `espaces.lire()` qui migre et écrit : ne jamais l'appeler depuis une boucle de fond."""
import json
import re
import threading

from app.services import espaces as _es

CANAL_ID = re.compile(r"^[a-z_]{1,20}:[A-Za-z0-9_.@-]{1,120}$")
MODES = ("valide_par_client", "publie_en_son_nom")
MODE_DEFAUT = "valide_par_client"
MOYENS = ("ecrit", "whatsapp", "doigt")
QUOI = ("mode", "consentement", "revocation", "publication", "validation", "import")
QUI = ("utilisateur", "client", "telephone")
MAX_JOURNAL = 2000
MAX_NOTES = 4000
_PERMIS = re.compile(r"^[a-z_]{2,30}$")
_PAYS = re.compile(r"^[A-Za-z]{2}$")
_verrou = threading.Lock()


def _txt(v, n: int) -> str:
    return v.strip()[:n] if isinstance(v, str) else ""


def valider(doc) -> dict:
    """La fiche normalisée (pure) : toujours un dict complet au format v1, quoi qu'on lui donne."""
    d = doc if isinstance(doc, dict) else {}
    c = d.get("contact") if isinstance(d.get("contact"), dict) else {}
    pays = _txt(d.get("pays"), 2)
    mode = d.get("mode_publication")
    consents = []
    for x in d.get("consentements") if isinstance(d.get("consentements"), list) else []:
        if not isinstance(x, dict) or not isinstance(x.get("canal_id"), str) or not CANAL_ID.match(x["canal_id"]):
            continue
        permis = ([p for p in x["permis"] if isinstance(p, str) and _PERMIS.match(p)][:10]
                  if isinstance(x.get("permis"), list) else [])
        date = _txt(x.get("date"), 40)
        if not permis or not date:
            continue
        consents.append({"canal_id": x["canal_id"], "permis": permis, "date": date,
                         "moyen": x.get("moyen") if x.get("moyen") in MOYENS else "ecrit",
                         "revoque_le": _txt(x.get("revoque_le"), 40) or None})
    journal = []
    for x in d.get("journal") if isinstance(d.get("journal"), list) else []:
        if not isinstance(x, dict) or x.get("quoi") not in QUOI or not _txt(x.get("quand"), 40):
            continue
        cid = x.get("canal_id")
        journal.append({"quand": _txt(x["quand"], 40), "quoi": x["quoi"],
                        "canal_id": cid if isinstance(cid, str) and (cid == "" or CANAL_ID.match(cid)) else "",
                        "qui": x.get("qui") if x.get("qui") in QUI else "utilisateur"})
    return {"version": 1, "societe": _txt(d.get("societe"), 200),
            "contact": {"nom": _txt(c.get("nom"), 200), "email": _txt(c.get("email"), 200),
                        "whatsapp": _txt(c.get("whatsapp"), 40)},
            "pays": pays.upper() if _PAYS.match(pays) else "",
            "langue": d.get("langue") if d.get("langue") in ("fr", "en") else "fr",
            "notes": d["notes"][:MAX_NOTES] if isinstance(d.get("notes"), str) else "",
            "mode_publication": mode if mode in MODES else MODE_DEFAUT,
            "consentements": consents, "journal": journal[-MAX_JOURNAL:]}


def _client(eid) -> None:
    """KeyError si l'espace est inconnu, ValueError s'il n'est pas de type client."""
    e = _es.lire()["espaces"].get(eid) if isinstance(eid, str) else None
    if e is None:
        raise KeyError(eid)
    if e.get("type") != "client":
        raise ValueError("cet espace n'est pas un client")


def _charger(eid) -> dict:
    try:
        return valider(json.loads(_es.chemin(eid, "client.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return valider({})


def _poser(eid, fiche: dict) -> dict:
    fiche = valider(fiche)
    _es._ecrire_json(_es.chemin(eid, "client.json"), fiche)
    return fiche


def _ligne(fiche: dict, quoi: str, canal_id: str, qui: str) -> None:
    if quoi not in QUOI:
        raise ValueError("événement de journal inconnu")
    if qui not in QUI:
        raise ValueError("auteur de journal inconnu")
    fiche["journal"].append({"quand": _es._maintenant(), "quoi": quoi, "canal_id": canal_id or "", "qui": qui})
    del fiche["journal"][:-MAX_JOURNAL]


def lire(eid) -> dict:
    _client(eid)
    return _charger(eid)


def ecrire(eid, champs) -> dict:
    if not isinstance(champs, dict):
        raise ValueError("un objet est attendu")
    if "consentements" in champs or "journal" in champs:
        raise ValueError("consentements et journal ne se modifient pas ici : ils ont leurs propres gestes")
    _client(eid)
    with _verrou:
        f = _charger(eid)
        for k in ("societe", "pays", "langue", "notes", "mode_publication"):
            if k in champs and not isinstance(champs[k], str):
                raise ValueError("valeur invalide : un texte est attendu")
        if "societe" in champs:
            f["societe"] = champs["societe"]
        if "contact" in champs:
            if not isinstance(champs["contact"], dict):
                raise ValueError("contact : un objet est attendu")
            for k in ("nom", "email", "whatsapp"):
                if k in champs["contact"]:
                    if not isinstance(champs["contact"][k], str):
                        raise ValueError("valeur invalide : un texte est attendu")
                    f["contact"][k] = champs["contact"][k]
        if "pays" in champs:
            p = champs["pays"].strip()
            if p and not _PAYS.match(p):
                raise ValueError("pays invalide : un code à deux lettres (ISO 3166) est attendu")
            f["pays"] = p
        if "langue" in champs:
            if champs["langue"] not in ("fr", "en"):
                raise ValueError("langue inconnue (fr ou en)")
            f["langue"] = champs["langue"]
        if "notes" in champs:
            if len(champs["notes"]) > MAX_NOTES:
                raise ValueError("notes : 4000 caractères au plus")
            f["notes"] = champs["notes"]
        if "mode_publication" in champs:
            if champs["mode_publication"] not in MODES:
                raise ValueError("mode de publication inconnu (valide_par_client ou publie_en_son_nom)")
            if champs["mode_publication"] != f["mode_publication"]:
                _ligne(f, "mode", "", "utilisateur")
            f["mode_publication"] = champs["mode_publication"]
        return _poser(eid, f)


def consentements_en_cours(eid) -> list:
    return [x for x in lire(eid)["consentements"] if x["revoque_le"] is None]


def consentement_en_cours(eid, canal_id) -> bool:
    return any(x["canal_id"] == canal_id for x in consentements_en_cours(eid))


def ajouter_consentement(eid, canal_id, permis, moyen) -> dict:
    if not isinstance(canal_id, str) or not CANAL_ID.match(canal_id):
        raise ValueError("identifiant de canal invalide (forme attendue : plateforme:identifiant)")
    if (not isinstance(permis, list) or not permis or len(permis) > 10
            or not all(isinstance(p, str) and _PERMIS.match(p) for p in permis)):
        raise ValueError("permissions invalides : une liste de mots (publier…) est attendue")
    if moyen not in MOYENS:
        raise ValueError("moyen de consentement inconnu (ecrit, whatsapp ou doigt)")
    _client(eid)
    with _verrou:
        f = _charger(eid)
        if any(x["canal_id"] == canal_id and x["revoque_le"] is None for x in f["consentements"]):
            raise ValueError("un consentement court déjà pour ce canal")
        f["consentements"].append({"canal_id": canal_id, "permis": list(permis), "date": _es._maintenant(),
                                   "moyen": moyen, "revoque_le": None})
        _ligne(f, "consentement", canal_id, "utilisateur")
        return _poser(eid, f)


def revoquer(eid, canal_id) -> dict:
    _client(eid)
    with _verrou:
        f = _charger(eid)
        for x in f["consentements"]:
            if x["canal_id"] == canal_id and x["revoque_le"] is None:
                x["revoque_le"] = _es._maintenant()
                _ligne(f, "revocation", canal_id, "utilisateur")
                return _poser(eid, f)
    raise KeyError(canal_id)


def noter(eid, quoi, canal_id, qui) -> None:
    _client(eid)
    with _verrou:
        f = _charger(eid)
        _ligne(f, quoi, canal_id if isinstance(canal_id, str) else "", qui)
        _poser(eid, f)
