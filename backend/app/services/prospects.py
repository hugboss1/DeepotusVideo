# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2 : la FICHE PROSPECTS d'un espace (CRM léger), `DATA_ROOT/espaces/<id>/
prospects.json` = {"version": 1, "prospects": [...]}. Spec `2026-10-27-agent-veille-prospection-design.md` §3, §6, §9.2.

RGPD par construction, côté serveur :
  - `source` {type, url, date, detail} et `base_legale` OBLIGATOIRES (refus explicite, jamais une valeur par défaut) ;
  - `interet_legitime_b2b` refusé si un e-mail du prospect est sur une messagerie grand public (`WEBMAILS`) ;
  - registre GLOBAL des oppositions (`oppositions`) : un identifiant opposé ne se crée dans aucun espace ;
  - `purge_le` = dernier contact VENU DU PROSPECT (réponse, inscription, rendez-vous) + 3 ans, sinon collecte + 3 ans
    (règle CNIL : un message que nous envoyons ne prolonge rien) ; `purger` retire les fiches échues (boucle quotidienne) ;
  - opposition = anonymisation immédiate (décision de l'utilisateur, 27/10) : il ne reste que {id, dates, statut, offre,
    type de source, base légale}, les identifiants vont au registre, haché ;
  - export complet (droit d'accès) ; effacement (droit à l'effacement) qui inscrit au registre, sauf saisie erronée.
Aucun envoi, aucune dépense, aucun réseau : le statut `contacte` se pose à la main (l'humain a écrit lui-même).
Les gestes `rdv` / `perdu` / `client` / `oppose` sur l'espace démonstration passent par la couture `_DEMO` (t353 tâche 3).
Un fichier illisible est mis de côté (`prospects.json.illisible-<horodatage>`), jamais écrasé. Écrivain unique sous verrou.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import date, datetime

from loguru import logger

from app.config import DATA_ROOT
from app.services import espaces as _es, oppositions as _op

STATUTS = ("propose", "qualifie", "contacte", "repondu", "rdv", "client", "perdu", "oppose")
TRANSITIONS = {
    "propose": ("qualifie", "perdu", "oppose"),
    "qualifie": ("contacte", "perdu", "oppose"),
    "contacte": ("repondu", "perdu", "oppose"),
    "repondu": ("rdv", "client", "perdu", "oppose"),
    "rdv": ("client", "perdu", "oppose"),
    "perdu": ("qualifie", "oppose"),
    "client": ("oppose",),
    "oppose": (),
}
SOURCES = ("web", "liste_attente", "whatsapp", "telegram", "formulaire", "reponse_post", "recommandation", "salon", "autre")
BASES = ("consentement", "interet_legitime_b2b", "mesures_precontractuelles")
OFFRES = ("licence", "prestation", "a_definir")
CANAUX = ("email", "whatsapp", "telephone", "x", "instagram", "linkedin", "site", "autre")
MOYENS = ("ecrit", "formulaire", "inscription", "whatsapp", "oral")
QUI = ("utilisateur", "agent", "systeme")
CODES = ("source", "base_legale", "email_perso", "opposition", "doublon", "transition", "plafond", "inconnu", "champ",
         "indisponible")
_HTTP = {"source": 422, "base_legale": 422, "champ": 422, "inconnu": 404, "indisponible": 503}
WEBMAILS = re.compile(r"^(gmail\.com|googlemail\.com|hotmail\.[a-z.]+|outlook\.[a-z.]+|live\.[a-z.]+|yahoo\.[a-z.]+|"
                      r"icloud\.com|me\.com|aol\.[a-z.]+|gmx\.[a-z.]+|proton\.me|protonmail\.com|orange\.fr|wanadoo\.fr|"
                      r"free\.fr|sfr\.fr|laposte\.net|bbox\.fr)$")
MAX_PROSPECTS = 2000
MAX_HISTORIQUE = 200
MAX_CANAUX = 10
FICHIER = "prospects.json"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ID = re.compile(r"^pr_[0-9a-f]{8}$")
_verrou = threading.RLock()
_EDITABLES = ("nom", "entreprise", "role", "source", "signal", "offre", "score", "canaux", "base_legale",
              "prochaine_action")


class RefusProspect(Exception):
    """Un geste refusé : `message` (texte de l'utilisateur, traduit par L10), `code` ∈ CODES, `statut` HTTP ; `pid` = la
    fiche existante pour un doublon."""

    def __init__(self, message: str, code: str, pid: str | None = None):
        super().__init__(message)
        self.message, self.code, self.pid = message, code, pid
        self.statut = _HTTP.get(code, 409)


def _aujourdhui() -> date:          # couture de banc
    return date.today()


def _nom_affiche(fiche: dict) -> str:
    return (fiche.get("entreprise") or fiche.get("nom") or fiche["id"])[:50]


def _nom_demo(fiche: dict) -> str:
    """t353 (relecture I1) : « Démo · <entreprise> », sinon « Démo · <id> » : jamais le nom d'une personne."""
    return "Démo · " + ((fiche.get("entreprise") or "")[:50] or fiche["id"])


def neutraliser_demo(fiche: dict) -> None:
    """t353 (relecture I1) : opposition, effacement ou purge : l'espace démonstration de la fiche (s'il l'est encore)
    perd le nom de l'entreprise et s'archive. Un échec est journalisé, jamais remonté (la fiche est déjà traitée)."""
    demo = fiche.get("espace_demo")
    if not demo:
        return
    try:
        _es.neutraliser_demonstration(demo, "Démo · " + fiche["id"])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"prospects : espace démonstration {demo} non neutralisé ({type(e).__name__})")


def _contact(fiche: dict) -> dict:
    email = next((c["valeur"] for c in fiche.get("canaux") or [] if c["type"] == "email"), "")
    wa = next((c["valeur"] for c in fiche.get("canaux") or [] if c["type"] == "whatsapp"), "")
    return {"nom": fiche.get("nom") or "", "email": email, "whatsapp": wa}


def _geste_demo(eid, fiche, statut):
    """t353 tâche 3 (spec §9.2) : l'espace DÉMONSTRATION suit le statut. `rdv` : créé (ou désarchivé s'il existe) ;
    `perdu` / `oppose` : archivé s'il est encore une démonstration (jamais un espace client) — note `demo_active` s'il est
    l'espace actif ; `client` : converti en espace client, ou un espace client neuf (note `demo_absente`). Le plafond
    d'espaces rend la note `plafond_espaces`. Rend la note, ou None. Écrit `fiche["espace_demo"]`."""
    doc = _es.lire()
    demo = fiche.get("espace_demo")
    e = doc["espaces"].get(demo) if demo else None
    if statut == "rdv":
        if isinstance(e, dict) and e.get("type") == "demonstration":
            if e.get("archive"):
                _es.archiver(demo, False)
            return None
        origine = doc["espaces"].get(eid) or {}
        try:
            v = _es.creer_demonstration(_nom_demo(fiche), origine.get("couleur") or "#ef4444",
                                        {"espace": eid, "prospect": fiche["id"]})
        except _es.PlafondEspaces:
            return "plafond_espaces"
        fiche["espace_demo"] = v["id"]
        return None
    if statut == "oppose":
        if isinstance(e, dict) and e.get("type") == "demonstration":
            return "demo_active" if _es.neutraliser_demonstration(demo, "Démo · " + fiche["id"]) == "actif" else None
        return None
    if statut == "perdu":
        if isinstance(e, dict) and e.get("type") == "demonstration" and not e.get("archive"):
            return "demo_active" if _es.archiver(demo, True) == "actif" else None
        return None
    if statut == "client":
        if isinstance(e, dict) and e.get("type") == "demonstration":
            _es.convertir_demonstration(demo, _nom_affiche(fiche), fiche.get("entreprise") or "", _contact(fiche))
            return None
        if isinstance(e, dict) and e.get("type") == "client":
            return None
        try:
            v = _es.creer({"nom": _nom_affiche(fiche), "type": "client",
                           "couleur": (doc["espaces"].get(eid) or {}).get("couleur")})
        except _es.PlafondEspaces:
            return "plafond_espaces"
        from app.services import fiche_client
        fiche_client.ecrire(v["id"], {"societe": fiche.get("entreprise") or "", "contact": _contact(fiche)})
        fiche["espace_demo"] = v["id"]
        return "demo_absente"
    return None


_DEMO = _geste_demo


# ---- normalisation pure ---------------------------------------------------------------------------------------------

def _txt(v, n: int) -> str:
    return v.strip()[:n] if isinstance(v, str) else ""


def _date_ok(v) -> str:
    """La date AAAA-MM-JJ si elle est valide, sinon ''."""
    if not isinstance(v, str) or not _DATE.match(v.strip()):
        return ""
    try:
        return date.fromisoformat(v.strip()).isoformat()
    except ValueError:
        return ""


def purge_le(fiche: dict) -> str:
    """Le jour de purge : (dernier contact venu du prospect, sinon collecte, sinon création) + 3 ans ; 29/02 → 28/02."""
    s = fiche.get("source") if isinstance(fiche.get("source"), dict) else {}
    d = (_date_ok(fiche.get("dernier_contact_entrant")) or _date_ok(s.get("date"))
         or _date_ok(_txt(fiche.get("cree_le"), 10)) or _aujourdhui().isoformat())
    j = date.fromisoformat(d)
    try:
        return j.replace(year=j.year + 3).isoformat()
    except ValueError:
        return j.replace(year=j.year + 3, day=28).isoformat()


def valider(doc) -> dict | None:
    """Une fiche normalisée (pure), ou None si elle n'a pas d'id valide. Les clés inconnues tombent."""
    d = doc if isinstance(doc, dict) else {}
    if not isinstance(d.get("id"), str) or not _ID.match(d["id"]):
        return None
    s = d.get("source") if isinstance(d.get("source"), dict) else {}
    canaux = [{"type": c["type"], "valeur": _txt(c.get("valeur"), 200)}
              for c in (d.get("canaux") if isinstance(d.get("canaux"), list) else [])
              if isinstance(c, dict) and c.get("type") in CANAUX and _txt(c.get("valeur"), 200)][:MAX_CANAUX]
    cons = [{"canal": c["canal"], "base_legale": c.get("base_legale") if c.get("base_legale") in BASES else "consentement",
             "date": _date_ok(c.get("date")), "moyen": c.get("moyen") if c.get("moyen") in MOYENS else "ecrit",
             "revoque_le": _date_ok(c.get("revoque_le")) or None}
            for c in (d.get("consentements") if isinstance(d.get("consentements"), list) else [])
            if isinstance(c, dict) and c.get("canal") in CANAUX and _date_ok(c.get("date"))]
    hist = [{"quand": _txt(h.get("quand"), 40), "quoi": _txt(h.get("quoi"), 40), "detail": _txt(h.get("detail"), 300),
             "qui": h.get("qui") if h.get("qui") in QUI else "utilisateur"}
            for h in (d.get("historique") if isinstance(d.get("historique"), list) else [])
            if isinstance(h, dict) and _txt(h.get("quand"), 40) and _txt(h.get("quoi"), 40)][-MAX_HISTORIQUE:]
    pa = d.get("prochaine_action") if isinstance(d.get("prochaine_action"), dict) else None
    score = d.get("score")
    out = {"id": d["id"], "cree_le": _txt(d.get("cree_le"), 40), "maj_le": _txt(d.get("maj_le"), 40),
           "nom": _txt(d.get("nom"), 200), "entreprise": _txt(d.get("entreprise"), 200), "role": _txt(d.get("role"), 200),
           "source": {"type": s.get("type") if s.get("type") in SOURCES else "autre", "url": _txt(s.get("url"), 500),
                      "date": _date_ok(s.get("date")), "detail": _txt(s.get("detail"), 300)},
           "signal": _txt(d.get("signal"), 1000),
           "offre": d.get("offre") if d.get("offre") in OFFRES else "a_definir",
           "score": score if isinstance(score, int) and not isinstance(score, bool) and 0 <= score <= 100 else None,
           "canaux": canaux,
           "base_legale": d.get("base_legale") if d.get("base_legale") in BASES else "",
           "consentements": cons,
           "statut": d.get("statut") if d.get("statut") in STATUTS else "propose",
           "historique": hist,
           "prochaine_action": ({"texte": _txt(pa.get("texte"), 300), "le": _date_ok(pa.get("le")) or None}
                                if pa and _txt(pa.get("texte"), 300) else None),
           "dernier_contact_entrant": _date_ok(d.get("dernier_contact_entrant")) or None,
           "espace_demo": d.get("espace_demo") if _es.id_valide(d.get("espace_demo")) else None}
    out["purge_le"] = _date_ok(d.get("purge_le")) or purge_le(out)
    return out


# ---- contrôles des champs saisis ------------------------------------------------------------------------------------

def _source(v) -> dict:
    if not isinstance(v, dict):
        raise RefusProspect("source du prospect exigée (type, date, et l'adresse pour une page web)", "source")
    if v.get("type") not in SOURCES:
        raise RefusProspect("type de source inconnu", "source")
    url = _txt(v.get("url"), 500)
    if url and not re.match(r"^https?://\S+$", url, re.I):
        raise RefusProspect("adresse de la source invalide (http ou https)", "source")
    if v["type"] == "web" and not url:
        raise RefusProspect("l'adresse de la page est exigée pour une source web", "source")
    d = _date_ok(v.get("date"))
    if not d:
        raise RefusProspect("date de la source exigée (AAAA-MM-JJ)", "source")
    if d > _aujourdhui().isoformat():
        raise RefusProspect("la date de la source ne peut pas être dans le futur", "source")
    return {"type": v["type"], "url": url, "date": d, "detail": _txt(v.get("detail"), 300)}


def _base(v) -> str:
    if v not in BASES:
        raise RefusProspect("base légale exigée (consentement, intérêt légitime B2B ou mesures précontractuelles)",
                            "base_legale")
    return v


def _canaux(v) -> list:
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > MAX_CANAUX:
        raise RefusProspect("canaux invalides : une liste de 10 canaux au plus est attendue", "champ")
    out = []
    for c in v:
        if not isinstance(c, dict) or c.get("type") not in CANAUX or not _txt(c.get("valeur"), 200):
            raise RefusProspect("canal invalide (type connu et valeur exigés)", "champ")
        out.append({"type": c["type"], "valeur": _txt(c["valeur"], 200)})
    return out


def _score(v):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 100:
        raise RefusProspect("score invalide : un entier de 0 à 100 est attendu", "champ")
    return v


def _webmail(valeur: str) -> bool:
    dom = valeur.strip().lower().rpartition("@")[2]
    return bool(WEBMAILS.match(dom))


def _verifier_b2b(base: str, canaux: list) -> None:
    if base == "interet_legitime_b2b" and any(c["type"] == "email" and _webmail(c["valeur"]) for c in canaux):
        raise RefusProspect("l'intérêt légitime B2B exige une adresse professionnelle : pour une messagerie grand "
                            "public, il faut le consentement du prospect", "email_perso")


def identifiants(fiche: dict) -> list:
    """Les identifiants d'une fiche qui comptent pour le registre et les doublons (formes normalisées)."""
    out = []
    for c in fiche.get("canaux") or []:
        f = _op.normaliser_canal(c.get("type"), c.get("valeur"))      # t353 suite (M7) : un pseudo compte aussi
        if f and f not in out:
            out.append(f)
    return out


# ---- stockage -------------------------------------------------------------------------------------------------------

def _mettre_de_cote(f) -> None:
    base = f"{FICHIER}.illisible-{datetime.now():%Y%m%d-%H%M%S}"
    cote, n = f.with_name(base), 2
    while cote.exists():
        cote, n = f.with_name(f"{base}-{n}"), n + 1
    try:
        f.replace(cote)
        logger.warning(f"prospects.json illisible : mis de côté ({cote.name}), liste reprise vide")
    except OSError as e:
        logger.warning(f"prospects.json illisible et impossible à mettre de côté ({e})")


def _lire_fichier(f, mettre_de_cote: bool = True) -> list | None:
    """Les fiches du fichier ; [] s'il est absent ; None s'il est illisible (mis de côté si demandé)."""
    try:
        brut = f.read_bytes()
    except FileNotFoundError:
        return []
    except OSError:          # t353 (relecture I2) : verrouillé : refus, jamais une liste vide qu'on réécrirait
        raise RefusProspect("fiche Prospects momentanément illisible : réessayez dans un instant", "indisponible") from None
    try:
        doc = json.loads(brut.decode("utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("prospects"), list):
            raise ValueError("forme inattendue")
    except ValueError:
        if mettre_de_cote:
            _mettre_de_cote(f)
        return None
    return [x for x in (valider(p) for p in doc["prospects"]) if x is not None]


def _espace(eid, archive_ok: bool = False) -> None:
    """RefusProspect(inconnu) si l'espace n'existe pas, est archivé ou est un espace démonstration. t353 (relecture M3) :
    `archive_ok` pour les droits RGPD (lire, exporter, s'opposer, effacer) d'une fiche d'un espace archivé."""
    e = _es.lire()["espaces"].get(eid) if _es.id_valide(eid) else None
    if not isinstance(e, dict) or (e.get("archive") and not archive_ok):
        raise RefusProspect("espace inconnu ou archivé", "inconnu")
    if e.get("type") == "demonstration":
        raise RefusProspect("un espace démonstration n'a pas de prospects", "inconnu")


def _reg(fn, *a):
    """Un appel au registre ; t353 (relecture I2) : registre verrouillé = refus 503, jamais « pas opposé »."""
    try:
        return fn(*a)
    except _op.RegistreIndisponible as e:
        raise RefusProspect(str(e), "indisponible") from None


def _charger(eid) -> list:
    """Les fiches de l'espace. t353 (relecture I3) : une fiche dont un identifiant est entré au registre depuis (STOP,
    opposition dans un autre espace, saisie) est anonymisée ICI, à la lecture, et le fichier réécrit."""
    fiches = _lire_fichier(_es.chemin(eid, FICHIER)) or []
    vivantes = [i for i, x in enumerate(fiches) if x["statut"] != "oppose" and identifiants(x)]
    if not vivantes:
        return fiches
    marques = _reg(_op.opposes, [identifiants(fiches[i]) for i in vivantes])
    touchees = [i for i, m in zip(vivantes, marques) if m]
    for i in touchees:
        neutraliser_demo(fiches[i])
        fiches[i] = _anonymiser(fiches[i])
    if touchees:
        _poser(eid, fiches)
    return fiches


def _poser(eid, fiches: list) -> None:
    _es._ecrire_json(_es.chemin(eid, FICHIER), {"version": 1, "prospects": fiches})


def _trouver(fiches: list, pid) -> dict:
    for f in fiches:
        if f["id"] == pid:
            return f
    raise RefusProspect("prospect inconnu", "inconnu")


def _noter(f: dict, quoi: str, detail: str = "", qui: str = "utilisateur") -> None:
    f["historique"].append({"quand": _es._maintenant(), "quoi": quoi, "detail": _txt(detail, 300),
                            "qui": qui if qui in QUI else "utilisateur"})
    del f["historique"][:-MAX_HISTORIQUE]
    f["maj_le"] = _es._maintenant()


def _doublon(fiches: list, fiche: dict, sauf: str | None = None) -> None:
    ids = set(identifiants(fiche))
    for f in fiches:
        if f["id"] != sauf and ids & set(identifiants(f)):
            raise RefusProspect("ce prospect existe déjà dans cet espace", "doublon", pid=f["id"])


# ---- gestes ---------------------------------------------------------------------------------------------------------

def lister(eid, statut=None) -> list:
    _espace(eid)
    with _verrou:
        fiches = _charger(eid)
    return [f for f in fiches if statut in (None, "") or f["statut"] == statut]


def lire(eid, pid) -> dict:
    _espace(eid, archive_ok=True)
    with _verrou:
        return _trouver(_charger(eid), pid)


def creer(eid, champs, qui: str = "utilisateur") -> dict:
    _espace(eid)
    if not isinstance(champs, dict):
        raise RefusProspect("un objet est attendu", "champ")
    source = _source(champs.get("source"))
    base = _base(champs.get("base_legale"))
    nom, entreprise = _txt(champs.get("nom"), 200), _txt(champs.get("entreprise"), 200)
    if not nom and not entreprise:
        raise RefusProspect("un nom ou une entreprise est exigé", "champ")
    if champs.get("offre") not in (None, "", *OFFRES):
        raise RefusProspect("offre inconnue (licence, prestation ou à définir)", "champ")
    canaux = _canaux(champs.get("canaux"))
    _verifier_b2b(base, canaux)
    maintenant = _es._maintenant()
    fiche = valider({"id": "pr_" + uuid.uuid4().hex[:8], "cree_le": maintenant, "maj_le": maintenant, "nom": nom,
                     "entreprise": entreprise, "role": champs.get("role"), "source": source,
                     "signal": champs.get("signal"), "offre": champs.get("offre"), "score": _score(champs.get("score")),
                     "canaux": canaux, "base_legale": base, "statut": "propose",
                     "prochaine_action": champs.get("prochaine_action")})
    fiche["purge_le"] = purge_le(fiche)
    if _reg(_op.oppose, identifiants(fiche)):
        raise RefusProspect("cette personne s'est opposée à la prospection : elle ne peut pas être ajoutée", "opposition")
    with _verrou:
        fiches = _charger(eid)
        if len(fiches) >= MAX_PROSPECTS:
            raise RefusProspect(f"{MAX_PROSPECTS} prospects au plus par espace", "plafond")
        _doublon(fiches, fiche)
        _noter(fiche, "creation", "", qui)
        fiches.append(fiche)
        _poser(eid, fiches)
    return fiche


def _modifiable(f: dict) -> None:
    if f["statut"] == "oppose":
        raise RefusProspect("ce prospect s'est opposé : sa fiche est anonymisée et ne se modifie plus", "transition")


def modifier(eid, pid, champs, qui: str = "utilisateur") -> dict:
    _espace(eid)
    if not isinstance(champs, dict):
        raise RefusProspect("un objet est attendu", "champ")
    if any(k in champs for k in ("statut", "consentements", "historique", "id", "purge_le", "espace_demo")):
        raise RefusProspect("statut, consentements et historique ont leurs propres gestes", "champ")
    with _verrou:
        fiches = _charger(eid)
        f = _trouver(fiches, pid)
        _modifiable(f)
        neuf = dict(f)
        if "source" in champs:
            neuf["source"] = _source(champs["source"])
        if "base_legale" in champs:
            neuf["base_legale"] = _base(champs["base_legale"])
        if "canaux" in champs:
            neuf["canaux"] = _canaux(champs["canaux"])
        if "score" in champs:
            neuf["score"] = _score(champs["score"])
        if "offre" in champs and champs["offre"] not in OFFRES:
            raise RefusProspect("offre inconnue (licence, prestation ou à définir)", "champ")
        for k in ("nom", "entreprise", "role", "signal", "offre", "prochaine_action"):
            if k in champs:
                neuf[k] = champs[k]
        neuf = valider(neuf)
        if not neuf["nom"] and not neuf["entreprise"]:
            raise RefusProspect("un nom ou une entreprise est exigé", "champ")
        _verifier_b2b(neuf["base_legale"], neuf["canaux"])
        if _reg(_op.oppose, identifiants(neuf)):
            raise RefusProspect("cette personne s'est opposée à la prospection : elle ne peut pas être ajoutée",
                                "opposition")
        _doublon(fiches, neuf, sauf=pid)
        neuf["purge_le"] = purge_le(neuf)
        _noter(neuf, "modification", ", ".join(k for k in _EDITABLES if k in champs), qui)
        fiches[fiches.index(f)] = neuf
        _poser(eid, fiches)
    if neuf["espace_demo"] and neuf["entreprise"] != f["entreprise"]:     # t353 suite (M9) : la démo suit l'entreprise
        try:
            _es.renommer_demonstration(neuf["espace_demo"], _nom_demo(neuf))
        except Exception as e:  # noqa: BLE001 — la fiche est enregistrée ; le nom de la démo est un plus
            logger.warning(f"prospects : espace démonstration {neuf['espace_demo']} non renommé ({type(e).__name__})")
    return neuf


def _anonymiser(f: dict) -> dict:
    garde = valider({"id": f["id"], "cree_le": f["cree_le"], "statut": "oppose", "offre": f["offre"],
                     "base_legale": f["base_legale"], "source": {"type": f["source"]["type"], "date": f["source"]["date"]},
                     "dernier_contact_entrant": f["dernier_contact_entrant"], "espace_demo": f["espace_demo"]})
    garde["purge_le"] = f["purge_le"]
    _noter(garde, "opposition")
    return garde


def opposer(eid, pid, qui: str = "utilisateur") -> dict:
    return changer_statut(eid, pid, "oppose", qui=qui)["prospect"]


def _defaire_demo(statut: str, pid: str, avant: str | None, apres: str | None, archive_avant: bool | None) -> None:
    """t353 suite (M4) : la fiche n'a pas pu être écrite après le geste sur l'espace démonstration : on le défait, pour
    qu'un nouvel essai ne crée pas un second espace. `rdv` : la démo NEUVE est neutralisée (renommée, archivée), une démo
    rouverte est refermée ; `perdu` : la démo archivée est rouverte ; `client` : l'espace client NEUF est archivé (une
    démo convertie le reste : le nouvel essai la retrouve). `oppose` : rien (le registre a déjà parlé). Jamais remonté."""
    try:
        if statut == "rdv":
            if apres and apres != avant:
                _es.neutraliser_demonstration(apres, "Démo · " + pid)
            elif avant and archive_avant:
                _es.archiver(avant, True)
        elif statut == "perdu" and avant and archive_avant is False:
            _es.archiver(avant, False)
        elif statut == "client" and apres and apres != avant:
            _es.archiver(apres, True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"prospects : geste sur l'espace démonstration non défait ({type(e).__name__})")


def changer_statut(eid, pid, statut, detail: str = "", qui: str = "utilisateur") -> dict:
    """{prospect, note} ; note ∈ {None, demo_active, plafond_espaces, demo_absente, demo_erreur} (tâche 3)."""
    if statut not in STATUTS:              # t353 suite (M5) : absent ou inconnu = un champ fautif, pas une transition
        raise RefusProspect("statut inconnu", "champ")
    _espace(eid, archive_ok=(statut == "oppose"))
    with _verrou:
        fiches = _charger(eid)
        f = _trouver(fiches, pid)
        if statut not in TRANSITIONS.get(f["statut"], ()):
            raise RefusProspect(f"passage impossible de « {f['statut']} » à « {statut} »", "transition")
        avant = f["statut"]
        demo_avant = f.get("espace_demo")
        e = _es.lire()["espaces"].get(demo_avant) if demo_avant else None
        archive_avant = bool(e.get("archive")) if isinstance(e, dict) else None
        if statut == "oppose":             # t353 suite (M4) : le registre d'abord ; indisponible = rien n'a bougé
            _reg(_op.inscrire, identifiants(f), "prospect")
        try:
            note = _DEMO(eid, f, statut)
        except Exception as e:  # noqa: BLE001 — le statut passe toujours ; l'espace démonstration est un plus
            logger.warning(f"prospects : geste sur l'espace démonstration en échec ({type(e).__name__}: {e})")
            note = "demo_erreur"
        demo_apres = f.get("espace_demo")
        try:
            if statut == "oppose":
                f = _anonymiser(f)
            else:
                f["statut"] = statut
                if statut in ("repondu", "rdv"):
                    f["dernier_contact_entrant"] = _aujourdhui().isoformat()
                    f["purge_le"] = purge_le(f)
                _noter(f, "statut", f"{avant} → {statut}" + (f" · {detail}" if _txt(detail, 200) else ""), qui)
            fiches = [f if x["id"] == pid else x for x in fiches]
            _poser(eid, fiches)
        except Exception:
            _defaire_demo(statut, pid, demo_avant, demo_apres, archive_avant)
            raise
    return {"prospect": f, "note": note}


def noter_contact(eid, pid, sens, detail: str = "", qui: str = "utilisateur") -> dict:
    """Un contact noté à la main. Seul un contact ENTRANT (venu du prospect) repousse la purge."""
    if sens not in ("entrant", "sortant"):
        raise RefusProspect("sens du contact inconnu (entrant ou sortant)", "champ")
    _espace(eid)
    with _verrou:
        fiches = _charger(eid)
        f = _trouver(fiches, pid)
        _modifiable(f)
        if sens == "entrant":
            f["dernier_contact_entrant"] = _aujourdhui().isoformat()
            f["purge_le"] = purge_le(f)
        _noter(f, "contact_" + sens, detail, qui)
        _poser(eid, fiches)
    return f


def ajouter_consentement(eid, pid, canal, base_legale, moyen, date_=None) -> dict:
    if canal not in CANAUX:
        raise RefusProspect("canal inconnu", "champ")
    _base(base_legale)
    if moyen not in MOYENS:
        raise RefusProspect("moyen de consentement inconnu", "champ")
    d = _date_ok(date_) if date_ else _aujourdhui().isoformat()
    if not d or d > _aujourdhui().isoformat():
        raise RefusProspect("date du consentement invalide (AAAA-MM-JJ, pas dans le futur)", "champ")
    _espace(eid)
    with _verrou:
        fiches = _charger(eid)
        f = _trouver(fiches, pid)
        _modifiable(f)
        if canal == "email":
            _verifier_b2b(base_legale, f["canaux"])
        if any(c["canal"] == canal and c["revoque_le"] is None for c in f["consentements"]):
            raise RefusProspect("un consentement court déjà pour ce canal", "champ")
        f["consentements"].append({"canal": canal, "base_legale": base_legale, "date": d, "moyen": moyen,
                                   "revoque_le": None})
        _noter(f, "consentement", canal)
        _poser(eid, fiches)
    return f


def revoquer_consentement(eid, pid, canal) -> dict:
    _espace(eid)
    with _verrou:
        fiches = _charger(eid)
        f = _trouver(fiches, pid)
        en_cours = [c for c in f["consentements"] if c["canal"] == canal and c["revoque_le"] is None]
        if not en_cours:
            raise RefusProspect("aucun consentement en cours pour ce canal", "inconnu")
        for c in en_cours:
            c["revoque_le"] = _aujourdhui().isoformat()
        _noter(f, "revocation", canal)
        _poser(eid, fiches)
    return f


def exporter(eid, pid) -> dict:
    """La fiche entière (droit d'accès), avec la date d'export, l'espace et l'état au registre."""
    f = lire(eid, pid)
    return dict(f, exporte_le=_es._maintenant(), espace=eid, oppose=_reg(_op.oppose, identifiants(f)))


def effacer(eid, pid, inscrire_opposition: bool = True) -> None:
    _espace(eid, archive_ok=True)
    with _verrou:
        fiches = _charger(eid)
        f = _trouver(fiches, pid)
        if inscrire_opposition:
            _reg(_op.inscrire, identifiants(f), "effacement")
        _poser(eid, [x for x in fiches if x["id"] != pid])
    neutraliser_demo(f)


def purger(maintenant: date, demos: list | None = None) -> dict:
    """Retire les fiches dont `purge_le` est atteinte, dans chaque espace. Lecture BRUTE : ni `espaces.lire()` ni mkdir ;
    un fichier illisible est sauté (il sera mis de côté à la prochaine lecture de l'écran). Rend {espace: nombre}."""
    racine = DATA_ROOT / "espaces"
    jour = maintenant.isoformat()
    out = {}
    try:
        dossiers = [d for d in racine.iterdir() if d.is_dir() and _es.id_valide(d.name)]
    except OSError:
        return out
    for d in sorted(dossiers):
        f = d / FICHIER
        if not f.is_file():
            continue
        with _verrou:
            try:
                fiches = _lire_fichier(f, mettre_de_cote=False)
            except RefusProspect:         # verrouillé : la purge de demain le reprendra
                continue
            if fiches is None:
                continue
            gardees = [x for x in fiches if x["purge_le"] > jour]
            if demos is not None:
                demos.extend(x for x in fiches if x["purge_le"] <= jour and x.get("espace_demo"))
            if len(gardees) != len(fiches):
                _es._ecrire_json(f, {"version": 1, "prospects": gardees})
                out[d.name] = len(fiches) - len(gardees)
    if out:
        logger.info(f"prospects : purge à 3 ans, {sum(out.values())} fiche(s) retirée(s)")
    return out


async def purger_tout(maintenant: date) -> dict:
    """La purge, puis la neutralisation des espaces démonstration des fiches purgées (relecture I1). Sur la boucle :
    t353 (relecture I4) : espaces.json n'a qu'un écrivain, la boucle (routes async comprises), jamais un thread."""
    demos: list = []
    out = purger(maintenant, demos)
    for fiche in demos:
        neutraliser_demo(fiche)
    return out


async def purge_loop(premier: float = 120, intervalle: float = 86400) -> None:
    """t353 : la purge à 3 ans, `premier` secondes après le démarrage puis toutes les `intervalle` secondes, SUR la
    boucle (relecture I4 : quelques fichiers JSON, rien de long). Une erreur est journalisée, jamais remontée."""
    import asyncio
    await asyncio.sleep(premier)
    while True:
        try:
            await purger_tout(_aujourdhui())
        except Exception as e:  # noqa: BLE001
            logger.warning(f"prospects : purge en échec ({type(e).__name__}: {e})")
        await asyncio.sleep(intervalle)
