# -*- coding: utf-8 -*-
"""t328 tâche 3 (27/10/2026) — les DIFFUSIONS WhatsApp d'un post du Planificateur (API Broadcasts de Kapso).

Plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md (Décisions 1-7), relevé
docs/superpowers/specs/2026-10-27-kapso-broadcasts-releve.md. S'appuie sur `kapso.py` (seul client réseau), `whatsapp.py`
(audience, plafond de messages, désinscriptions) et `whatsapp_echanges.py` (modèles, paramètres, composants Meta, marché).

Stockage (Décision 5) : `espaces/<eid>/whatsapp_diffusions.json` = {post_id: {compte, modele: {nom, langue, meta_id,
categorie}, parametres, identites|null, broadcast_id, statut, incertain, n, lignes: [{id, marche}], ajout: {ajoutes,
doublons, erreurs}, compteurs, ecartes, reel_note, maj}}. Écrit atomiquement (`espaces._ecrire_json`) sous le verrou du
compte (`whatsapp._verrou_compte`) ; jamais de numéro au journal, jamais le texte du modèle.

Statuts : `configuree` (prête), `preparation` (diffusion créée chez Kapso, destinataires en cours d'ajout, rien de
réservé), `envoi` (send en vol ou issue incertaine), puis le statut de Kapso (`sending`, `completed`, `stopped`,
`failed`…), ou `echec` (send refusé 4xx). Relançables : `configuree`, `preparation`, `echec`. Tout autre statut (ou
`incertain`) = diffusion LANCÉE : `configurer` et un nouveau `lancer` sont refusés (`deja_lancee`).

  · `configurer` : modèle APPROUVÉ (nom + langue, avec son id Meta), paramètres vérifiés comme un envoi unitaire
    (`_valider_envoi`, `_verifier_parametres`, `_verifier_composants` : un modèle à en-tête média est refusé en v1),
    audience (`audience_diffusion` ; vide = n 0, la config est rangée quand même), devis par marché (`pricing.estimate`,
    AUCUNE réservation).
  · `lancer` : config → espace actif → (incertain non confirmé : relecture, puis refus `incertain` si Kapso ne tranche
    pas) → audience → plafond du mois → modèle encore approuvé → devis → `creer_broadcast` → destinataires par 1 000 →
    `plafonds.verifier` (ref = broadcast) → `envoyer_broadcast` (UN essai). L'enregistrement passe à `envoi` +
    `incertain` AVANT le send : un arrêt brutal pendant l'envoi laisse une diffusion à relire, jamais à renvoyer.
    2xx : statut de Kapso, compteur du mois + n. 4xx : réservation à 0, `echec` (429 : rien n'a été traité, retour à
    `configuree`), la KapsoErreur remonte. 5xx / réseau : `incertain`, réservation gardée, rendu sans lever.
  · `relire` : GET du broadcast et de TOUTES les pages de destinataires ; `suppressed` et le code Meta 131050 notent la
    désinscription marketing ; statut terminal : coût réel par marché (destinataires `sent` × prix) posé UNE fois.
  · `a_relire` : diffusions lancées non terminées dont `maj` a plus de 60 s.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

from loguru import logger

from app.services import espaces as _es, kapso, plafonds, pricing
from app.services import whatsapp as WA
from app.services import whatsapp_echanges as WE
from app.services.whatsapp import WhatsappRefus

FICHIER = "whatsapp_diffusions.json"
RELANCABLES = ("configuree", "preparation", "echec")
TERMINAUX = ("completed", "stopped", "failed")
KAPSO_TRANCHE = ("sending", "completed", "stopped", "failed")    # Kapso a pris le send : l'incertitude est levée
PAR_PAGE = 100
PAGES_MAX = 10_000                                                # 1 000 000 destinataires (PLAFOND_MOIS_MAX)
DELAI_RELECTURE = timedelta(seconds=60)
_verrou = threading.Lock()


class PostInconnu(KeyError):
    """Le post n'existe pas (404 à la route)."""


def _horloge() -> datetime:
    """HOOK DE BANC : l'heure (UTC)."""
    return datetime.now(timezone.utc)


# ---- fichier d'espace ----------------------------------------------------------------------------------------------

def _lire_doc(eid: str) -> dict:
    f = _es.chemin(eid, FICHIER)
    if f is None:
        raise KeyError(eid)
    try:
        brut = f.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
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


def _modifier(eid: str, post_id: str, geste) -> dict:
    """Relit, modifie l'entrée du post (`geste(rec) -> rec`) et réécrit atomiquement. Rend l'entrée écrite."""
    with _verrou:
        doc = _lire_doc(eid)
        rec = geste(dict(doc.get(post_id) or {}))
        rec["maj"] = _horloge().isoformat()
        doc[post_id] = rec
        _es._ecrire_json(_es.chemin(eid, FICHIER), doc)
        return json.loads(json.dumps(rec))


def lire(post_id, espace_id: str) -> dict | None:
    """L'entrée de diffusion du post dans l'espace (copie), ou None."""
    rec = _lire_doc(espace_id).get(str(post_id))
    return json.loads(json.dumps(rec)) if isinstance(rec, dict) else None


def _lancee(rec: dict | None) -> bool:
    return bool(rec) and (rec.get("incertain") is True or rec.get("statut") not in RELANCABLES)


# ---- aides ---------------------------------------------------------------------------------------------------------

async def _post(post_id: str):
    from sqlalchemy import select
    from app.services.storage import ScheduledPost, async_session_factory
    async with async_session_factory() as s:
        return (await s.execute(select(ScheduledPost).where(ScheduledPost.id == str(post_id)))).scalar_one_or_none()


async def _modele_approuve(cid: str, nom, langue) -> dict:
    """Le modèle APPROUVÉ (plat, avec `meta_id`) de ce nom et de cette langue. ValueError sinon."""
    m = next((m for m in await WE.modeles(cid) if m.get("nom") == nom and m.get("langue") == langue), None)
    if m is None:
        raise ValueError("modèle inconnu ou non approuvé pour cette langue")
    if not m.get("meta_id"):
        raise ValueError("ce modèle n'a pas d'identifiant Meta : il ne peut pas partir en diffusion")
    return m


def _envoi(modele: dict, parametres) -> dict:
    """L'envoi « modèle » normalisé et vérifié contre le modèle (ValueError sinon)."""
    e_ = WE._valider_envoi({"type": "modele", "nom": modele.get("nom"), "langue": modele.get("langue"),
                            "parametres": parametres})
    return e_


def _verifier(e_: dict, plat: dict) -> None:
    WE._verifier_parametres(e_, plat)
    WE._verifier_composants(e_, plat)


def _par_marche(retenus: list, defaut: str) -> dict:
    out: dict = {}
    for i in retenus:
        out.setdefault(WE._marche(i, defaut), []).append(i)
    return dict(sorted(out.items()))


def _op(categorie: str, marches: dict) -> dict:
    return {"kind": "campaign", "ops": [{"kind": "whatsapp", "categorie": categorie, "marche": m, "n": len(ids)}
                                        for m, ids in marches.items()]}


def _devis(op: dict) -> dict:
    try:
        return pricing.estimate(op)
    except ValueError as x:                  # prix inconnu (message de `pricing`, traduit par L10)
        raise WhatsappRefus(str(x), "prix") from None


def _mois_plus(cid: str, n: int, maintenant: datetime) -> None:
    """Les `n` messages de la diffusion comptent dans le mois (le plafond de l'espace les voit)."""
    mois = WA._mois(maintenant)

    def geste(e):
        m = e["compteur"].setdefault(mois, {})
        m["sortants"] = int(m.get("sortants") or 0) + n
    WA._noter(cid, geste)


# ---- configurer ----------------------------------------------------------------------------------------------------

async def configurer(post_id, cid: str, *, modele: dict, parametres, identites: list[str] | None) -> dict:
    """Range la configuration de diffusion du post : {config, audience: {n, ecartes}, devis: {usd, lignes}}.
    ValueError : modèle ou paramètres invalides ; WhatsappRefus : `deja_lancee`, `consentement`, `prix`."""
    post_id = str(post_id)
    if not isinstance(modele, dict):
        raise ValueError("modèle : nom et langue exigés")
    if identites is not None and not isinstance(identites, list):
        raise ValueError("identités : une liste est attendue")
    eid, _pid = WA._cle_etat(cid)
    if _lancee(lire(post_id, eid)):              # tôt : aucun appel Kapso pour une diffusion déjà partie (revu sous verrou)
        raise WhatsappRefus("une diffusion de ce post est déjà lancée : elle ne se modifie plus", "deja_lancee")
    e_ = _envoi(modele, parametres)
    plat = await _modele_approuve(cid, e_["nom"], e_["langue"])
    _verifier(e_, plat)
    try:
        aud = WA.audience_diffusion(cid, categorie=plat["categorie"], identites=identites)
    except WhatsappRefus as x:
        if x.code != "accord":
            raise
        aud = {"retenus": [], "ecartes": None}
    marches = _par_marche(aud["retenus"], WA.reglages(eid)["marche_defaut"])
    devis = _devis(_op(plat["categorie"], marches)) if marches else {"total_usd": 0.0, "breakdown": []}
    async with WA._verrou_compte(cid):
        if _lancee(lire(post_id, eid)):
            raise WhatsappRefus("une diffusion de ce post est déjà lancée : elle ne se modifie plus", "deja_lancee")

        def geste(rec):
            return {"compte": cid,
                    "modele": {"nom": plat["nom"], "langue": plat["langue"], "meta_id": plat["meta_id"],
                               "categorie": plat["categorie"]},
                    "parametres": e_["parametres"], "identites": list(identites) if identites is not None else None,
                    "broadcast_id": None, "statut": "configuree", "incertain": False, "n": 0, "lignes": [],
                    "compteurs": {}, "ecartes": aud["ecartes"], "ajout": None, "reel_note": False}
        config = _modifier(eid, post_id, geste)
    return {"config": config, "audience": {"n": len(aud["retenus"]), "ecartes": aud["ecartes"]},
            "devis": {"usd": devis["total_usd"], "lignes": devis["breakdown"]}}


# ---- lancer --------------------------------------------------------------------------------------------------------

def _rendu(rec: dict) -> dict:
    return {"broadcast_id": rec.get("broadcast_id"), "statut": rec.get("statut"), "n": rec.get("n") or 0,
            "incertain": rec.get("incertain") is True}


async def lancer(post_id, *, confirme_incertain: bool = False) -> dict:
    """Lance la diffusion configurée du post : {broadcast_id, statut, n, incertain}. Voir l'en-tête pour l'ordre.
    PostInconnu ; ValueError (config absente, espace archivé, modèle) ; WhatsappRefus (`incertain`, `deja_lancee`,
    `accord`, `consentement`, `plafond`, `prix`) ; KapsoErreur (refus du fournisseur) ; 402 de `plafonds`."""
    post_id = str(post_id)
    post = await _post(post_id)
    if post is None:
        raise PostInconnu(post_id)
    eid = post.espace_id
    rec = lire(post_id, eid) if eid else None
    if not rec or not rec.get("compte"):
        raise ValueError("aucune diffusion WhatsApp n'est configurée pour ce post")
    WA.espace_actif(eid)
    cid = rec["compte"]
    eid_compte, pid = WA._cle_etat(cid)
    if eid_compte != eid:
        raise ValueError("le compte WhatsApp de cette diffusion n'appartient pas à l'espace du post")
    async with WA._verrou_compte(cid):
        return await _lancer_sous_verrou(post_id, eid, cid, pid, rec, confirme_incertain)


async def _lancer_sous_verrou(post_id, eid, cid, pid, rec, confirme_incertain) -> dict:
    rec = lire(post_id, eid) or rec
    anciennes: list = []
    if rec.get("incertain") is True:
        relu = None
        try:
            relu = await _relire_sous_verrou(post_id, eid, cid)
        except kapso.KapsoErreur as x:
            logger.warning(f"diffusion post {post_id} : relecture impossible ({x.code})")
        rec = lire(post_id, eid) or rec
        if rec.get("incertain") is not True:
            return _rendu(rec)                   # Kapso a pris le send : rien à renvoyer
        if not confirme_incertain:
            raise WhatsappRefus("cette diffusion est peut-être déjà partie (panne de Kapso pendant l'envoi) : vérifiez-la, "
                                "puis confirmez pour la relancer", "incertain")
        if relu is not None and relu.get("statut_kapso") == "draft":
            await plafonds.noter_reel_lignes([l["id"] for l in rec.get("lignes") or []], 0.0)   # rien n'est parti
        else:
            anciennes = [{"broadcast_id": rec.get("broadcast_id"), "lignes": rec.get("lignes") or []}]
    elif _lancee(rec):
        raise WhatsappRefus("une diffusion de ce post est déjà lancée : elle ne se modifie plus", "deja_lancee")

    modele = rec["modele"]
    aud = WA.audience_diffusion(cid, categorie=modele["categorie"], identites=rec.get("identites"))
    retenus = aud["retenus"]
    maintenant = _horloge()
    WA.verifier_plafond_mois(cid, len(retenus), maintenant)
    plat = await _modele_approuve(cid, modele["nom"], modele["langue"])
    e_ = _envoi(modele, rec.get("parametres"))
    _verifier(e_, plat)
    marches = _par_marche(retenus, WA.reglages(eid)["marche_defaut"])
    op = _op(plat["categorie"], marches)
    devis = _devis(op)
    composants = WE._corps(e_)["template"].get("components")

    cree = await kapso.creer_broadcast(f"dz-{post_id}-{maintenant:%Y%m%d%H%M%S}", pid, plat["meta_id"])
    bid = cree["id"]

    def preparer(r):
        r.update(broadcast_id=bid, statut="preparation", incertain=False, n=0, lignes=[], compteurs={},
                 ecartes=aud["ecartes"], ajout=None, reel_note=False,
                 modele={**modele, "meta_id": plat["meta_id"], "categorie": plat["categorie"]})
        if anciennes:
            r["anciennes"] = (r.get("anciennes") or []) + anciennes
        return r
    _modifier(eid, post_id, preparer)
    ajout = {"ajoutes": 0, "doublons": 0, "erreurs": 0}
    for i in range(0, len(retenus), kapso.MAX_DESTINATAIRES):
        lot = [{"phone_number": "+" + ident[4:], **({"components": composants} if composants else {})}
               for ident in retenus[i:i + kapso.MAX_DESTINATAIRES]]
        r = await kapso.ajouter_destinataires(bid, lot)
        ajout["ajoutes"] += r["ajoutes"]
        ajout["doublons"] += r["doublons"]
        ajout["erreurs"] += len(r["erreurs"])
    n = ajout["ajoutes"]
    if n < 1:
        _modifier(eid, post_id, lambda r: {**r, "statut": "echec", "ajout": ajout})
        raise ValueError("Kapso n'a accepté aucun destinataire de cette diffusion")

    garde = await plafonds.verifier(op, "whatsapp", ref=bid, espace_id=eid)     # 402 `dz_plafond` : rien n'est parti
    # `verifier` n'écrit que les lignes payantes, dans l'ordre du devis (une par marché) : on garde le marché de chacune
    marches_payants = [o["marche"] for o, l in zip(op["ops"], devis["breakdown"]) if l["usd"] and l["usd"] > 0]
    lignes = [{"id": i, "marche": m} for i, m in zip(garde["lignes"], marches_payants)]
    _modifier(eid, post_id, lambda r: {**r, "statut": "envoi", "incertain": True, "n": n, "lignes": lignes, "ajout": ajout})
    try:
        res = await kapso.envoyer_broadcast(bid)
    except kapso.KapsoErreur as x:
        if 400 <= x.statut < 500:                # refus du fournisseur (429 compris : un seul essai, rien n'a été traité)
            await plafonds.noter_reel_lignes(garde["lignes"], 0.0)
            statut = "configuree" if x.statut == 429 else "echec"
            _modifier(eid, post_id, lambda r: {**r, "statut": statut, "incertain": False})
            logger.warning(f"diffusion post {post_id} broadcast {bid} : send refusé ({x.statut}), réservation remise à 0")
            raise
        logger.warning(f"diffusion post {post_id} broadcast {bid} : issue incertaine ({x.code}), réservation gardée")
        _mois_plus(cid, n, maintenant)           # a pu partir : compté, le plafond se trompe vers le haut
        return _rendu(lire(post_id, eid))
    statut = res.get("statut") or "sending"
    rec = _modifier(eid, post_id, lambda r: {**r, "statut": statut, "incertain": False})
    _mois_plus(cid, n, maintenant)
    logger.info(f"diffusion post {post_id} broadcast {bid} : {n} destinataires, {ajout['doublons']} doublons, "
                f"{ajout['erreurs']} erreurs, statut {statut}")
    return _rendu(rec)


# ---- relire --------------------------------------------------------------------------------------------------------

async def relire(post_id, espace_id: str) -> dict:
    """Relit la diffusion chez Kapso (voir l'en-tête) et rend l'entrée à jour (`statut_kapso` en plus). Une diffusion non
    lancée est rendue telle quelle, sans appel. ValueError : aucune diffusion configurée."""
    post_id = str(post_id)
    rec = lire(post_id, espace_id)
    if not rec or not rec.get("compte"):
        raise ValueError("aucune diffusion WhatsApp n'est configurée pour ce post")
    async with WA._verrou_compte(rec["compte"]):
        return await _relire_sous_verrou(post_id, espace_id, rec["compte"])


async def _relire_sous_verrou(post_id: str, eid: str, cid: str) -> dict:
    rec = lire(post_id, eid) or {}
    bid = rec.get("broadcast_id")
    if not bid or not _lancee(rec):
        return rec
    b = await kapso.broadcast(bid)
    lignes, page, pages = [], 1, 1
    while page <= pages and page <= PAGES_MAX:
        d = await kapso.destinataires_broadcast(bid, page=page, par_page=PAR_PAGE)
        lignes.extend(d["lignes"])
        pages = d["pages"]
        page += 1
    sk = b["statut"]
    # désinscriptions : `suppressed` (préférence marketing coupée) et 131050 (Meta : l'utilisateur a coupé le marketing)
    desinscrits = WA.etat(cid)["desinscrits_marketing"]
    neufs = []
    for l in lignes:
        chiffres = l["phone_number"].lstrip("+")
        if not chiffres:
            continue
        if l["statut"] == "suppressed" or "131050" in str(l.get("code_erreur") or ""):
            ident = "tel:" + chiffres
            if ident not in desinscrits and ident not in neufs:
                neufs.append(ident)
    for ident in neufs:
        WA.noter_desinscription(cid, ident)
    compteurs = dict(b.get("compteurs") or {})
    compteurs["livres"] = sum(1 for l in lignes if l.get("livre"))
    compteurs["lus"] = sum(1 for l in lignes if l.get("lu"))
    reel = None
    if sk in TERMINAUX and not rec.get("reel_note"):
        defaut = WA.reglages(eid)["marche_defaut"]
        envoyes: dict = {}
        for l in lignes:
            if l["statut"] == "sent" and l["phone_number"].lstrip("+"):
                m = WE._marche("tel:" + l["phone_number"].lstrip("+"), defaut)
                envoyes[m] = envoyes.get(m, 0) + 1
        cat = (rec.get("modele") or {}).get("categorie")
        reel = 0.0
        for ligne in rec.get("lignes") or []:
            k = envoyes.get(ligne["marche"], 0)
            usd = pricing.estimate({"kind": "whatsapp", "categorie": cat, "marche": ligne["marche"], "n": k})["total_usd"] \
                if k else 0.0
            await plafonds.noter_reel_lignes([ligne["id"]], usd)
            reel += usd

    def geste(r):
        r["compteurs"] = compteurs
        if sk in KAPSO_TRANCHE:
            r["incertain"] = False
        if r.get("incertain") is not True and sk:
            r["statut"] = sk
        if reel is not None:
            r["reel_note"] = True
            r["reel_usd"] = round(reel, 4)
        return r
    rec = _modifier(eid, post_id, geste)
    logger.info(f"diffusion post {post_id} broadcast {bid} relue : statut {sk}, {len(lignes)} destinataires, "
                f"{len(neufs)} désinscriptions")
    return {**rec, "statut_kapso": sk}


# ---- relecture de fond -------------------------------------------------------------------------------------------------

def _date(v) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def a_relire(maintenant: datetime) -> list:
    """[(post_id, espace_id)] des diffusions lancées non terminées (ou incertaines) dont `maj` a plus de 60 s."""
    out = []
    if maintenant.tzinfo is None:
        maintenant = maintenant.replace(tzinfo=timezone.utc)
    for eid in sorted(_es.lire()["espaces"]):
        try:
            doc = _lire_doc(eid)
        except (KeyError, OSError):
            continue
        for post_id, rec in sorted(doc.items()):
            if not isinstance(rec, dict) or not rec.get("broadcast_id") or not _lancee(rec):
                continue
            if rec.get("statut") in TERMINAUX and rec.get("incertain") is not True:
                continue
            quand = _date(rec.get("maj"))
            if quand is None or maintenant - quand >= DELAI_RELECTURE:
                out.append((post_id, eid))
    return out
