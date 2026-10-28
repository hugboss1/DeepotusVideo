# -*- coding: utf-8 -*-
"""t328 tâche 3 (27/10/2026) — les DIFFUSIONS WhatsApp d'un post du Planificateur (API Broadcasts de Kapso).

Plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md (Décisions 1-7), relevé
docs/superpowers/specs/2026-10-27-kapso-broadcasts-releve.md. S'appuie sur `kapso.py` (seul client réseau), `whatsapp.py`
(audience, plafond de messages, désinscriptions) et `whatsapp_echanges.py` (modèles, paramètres, composants Meta, marché).

Stockage (Décision 5) : `espaces/<eid>/whatsapp_diffusions.json` = {post_id: {compte, modele: {nom, langue, meta_id,
categorie}, parametres, identites|null, broadcast_id, statut, incertain, attente_confirmation, n, lignes: [{id, marche}],
ajout: {ajoutes, doublons, erreurs}, compteurs, ecartes, reel_note, anciennes: [{broadcast_id, lignes}], maj}}. Écrit
atomiquement (`espaces._ecrire_json`). Jamais de numéro au journal, jamais le texte du modèle.
Fichier ILLISIBLE : jamais remis à zéro ni mis de côté (les marqueurs « déjà lancée » / « incertain » y vivent) ;
`configurer`, `lancer` et `relire` refusent (ValueError) tant qu'il n'est pas réparé ; `lire` et `a_relire` le voient vide.

Verrous : celui du POST (`_verrou_post`, un asyncio.Lock par post et par boucle) puis celui du COMPTE
(`whatsapp._verrou_compte`), toujours dans cet ordre, pour `configurer`, `lancer` et `relire` : une configuration (même
par un autre compte de l'espace) n'écrase jamais une diffusion en vol, et deux `lancer` simultanés font un seul send.

Statuts : `configuree` (prête), `preparation` (diffusion créée chez Kapso, destinataires en cours d'ajout ; une panne ou
un 402 à cette étape ramène à `configuree` ; un `preparation` vu sous le verrou du post est le reste d'un arrêt brutal :
rien n'est parti), `envoi` (send en vol ou issue incertaine), puis le statut de Kapso (`sending`, `completed`, `stopped`,
`failed`…), ou `echec` (send refusé 4xx, ou aucun destinataire accepté). Relançables : `configuree`, `preparation`,
`echec`, et `failed` de Kapso quand AUCUN message n'est parti, ce qui se PROUVE à la relecture (compteur `sent` à 0 —
absent, il vaut 0 — ET relecture complète des destinataires sans aucune ligne `sent` : `rien_envoye`) et une fois la
réservation soldée (`reel_note`) ; sinon `failed` reste définitif. Un send 2xx déjà `failed` est relu et soldé aussitôt. Tout autre statut (ou `incertain`) = diffusion LANCÉE : `configurer` et un nouveau
`lancer` sont refusés (`deja_lancee`).

  · `configurer` : modèle APPROUVÉ (nom + langue, avec son id Meta), paramètres vérifiés comme un envoi unitaire
    (`_valider_envoi`, `_verifier_parametres`, `_verifier_composants` : un modèle à en-tête média est refusé en v1),
    audience (`audience_diffusion` ; vide = n 0 avec les écartés comptés, la config est rangée quand même), devis par
    marché (`pricing.estimate`, AUCUNE réservation).
  · `lancer` : config → espace actif → (incertain non confirmé : relecture, puis refus `incertain` si Kapso ne tranche
    pas) → audience → plafond du mois → modèle encore approuvé → devis → `creer_broadcast` → destinataires par 1 000 →
    `plafonds.verifier` (ref = broadcast) → `envoyer_broadcast` (UN essai). L'enregistrement passe à `envoi` +
    `incertain` AVANT le send : un arrêt brutal pendant l'envoi laisse une diffusion à relire, jamais à renvoyer.
    2xx : statut de Kapso, compteur du mois + n. 4xx : réservation à 0, `echec` (429 : rien n'a été traité, retour à
    `configuree`), la KapsoErreur remonte. 5xx / réseau : `incertain`, réservation gardée, rendu sans lever.
    Relance confirmée d'une diffusion incertaine (revue finale I1) : si Kapso disait `draft`, le brouillon est d'abord
    VIDÉ (`kapso.vider_destinataires`) — vidé : rien ne partira, l'ancienne réservation passe à 0 et la relance a lieu ;
    422 (plus un brouillon : Kapso a pris l'envoi) : AUCUNE relance, la diffusion est relue et suivie normalement ;
    panne : refus `incertain`, rien ne change. Re-revue O1 : ce vidage a lieu QUELLE QUE SOIT la relecture (`draft`,
    `scheduled`, statut inconnu, relecture en échec) : jamais de send d'une relance sans preuve que l'ancienne ne peut
    plus partir ; plus rien n'est « parqué » dans `anciennes` (les anciennes héritées restent relues). N1 : un 404 au
    vidage ne vaut « vidé » que si le GET de la diffusion est aussi en 404. N2 : après un 422, `vidage_refuse` — la
    diffusion reste suivie et n'est plus jamais « en attente de confirmation » jusqu'à ce que Kapso tranche.
  · `configurer` d'une diffusion en attente de confirmation (revue finale M3) : même vidage d'abord (vidé : solde à 0,
    retour à `configuree` ; 422 : relue, refus `deja_lancee` ; panne : refus `incertain`). Modèles refusés (M4) :
    catégorie `authentication`, en-tête texte variable (WhatsappRefus « modele »).
  · `relire` : GET du broadcast et de TOUTES les pages de destinataires (et de chaque diffusion de `anciennes`) ;
    `suppressed` et le code Meta 131050 notent la désinscription marketing ; statut terminal : coût réel par marché
    (destinataires `sent` × prix) posé UNE fois ; une ancienne terminée est soldée puis retirée ; une ancienne encore
    `draft` n'est soldée (à 0) et retirée qu'une fois VIDÉE. Incertaine et Kapso dit `draft` : `attente_confirmation`
    (plus de relecture de fond jusqu'à la décision). Revue finale M9 : SEUIL_INTROUVABLE relectures en 404 de suite ->
    `introuvable` (plus suivie, réservation gardée comme estimation, une ligne au journal).
  · `a_relire` : diffusions lancées non terminées (hors attente de confirmation et `introuvable`), ou avec des
    `anciennes`, dont `maj` a plus de 60 s ; les espaces sont lus sur le DISQUE (dossiers), jamais par `espaces.lire()`.

t328 tâche 4 : l'adaptateur `publishers.register("whatsapp", …)` (enregistré à l'import, importé par `marketing` avec
les autres) lance la diffusion du post `meta["post_id"]` sur le compte courant, s'il est celui de la config ;
`reporter_post` reporte une diffusion prise par Kapso sur son post (remote_ids, `posted`) ; `apercu` recalcule audience
et devis sans réseau (GET de la route).
"""
from __future__ import annotations

import asyncio
import json
import threading
import weakref
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
SEUIL_INTROUVABLE = 3                                             # revue finale M9 : relectures en 404 avant `introuvable`
_verrou = threading.Lock()
_VERROUS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()     # boucle -> {post_id: asyncio.Lock}
_SIGNALES: set = set()            # (espace, mtime) des fichiers illisibles déjà signalés au journal (une fois par version)


class PostInconnu(KeyError):
    """Le post n'existe pas (404 à la route)."""


class FichierIllisible(ValueError):
    """`whatsapp_diffusions.json` illisible : aucun geste d'écriture tant qu'il n'est pas réparé."""


def _horloge() -> datetime:
    """HOOK DE BANC : l'heure (UTC)."""
    return datetime.now(timezone.utc)


def _verrou_post(post_id: str) -> asyncio.Lock:
    par = _VERROUS.setdefault(asyncio.get_running_loop(), {})
    return par.setdefault(str(post_id), asyncio.Lock())


# ---- fichier d'espace ----------------------------------------------------------------------------------------------

def _lire_doc(eid: str, strict: bool = True) -> dict:
    """Le document ({} s'il manque). Illisible : `FichierIllisible` si `strict`, sinon {} (affichage) ; jamais déplacé."""
    f = _es.chemin(eid, FICHIER)
    if f is None:
        raise KeyError(eid)
    try:
        brut = f.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except UnicodeDecodeError:
        brut = None
    try:
        doc = json.loads(brut) if brut is not None else None
    except ValueError:
        doc = None
    if isinstance(doc, dict):
        return doc
    try:
        cle = (eid, f.stat().st_mtime_ns)
    except OSError:
        cle = (eid, None)
    if cle not in _SIGNALES:                     # une fois par version du fichier, pas à chaque tick
        _SIGNALES.add(cle)
        logger.error(f"{FICHIER} illisible dans l'espace {eid} : diffusions bloquées jusqu'à réparation")
    if strict:
        raise FichierIllisible("le fichier des diffusions WhatsApp de cet espace est illisible : réparez-le avant toute "
                               "diffusion")
    return {}


def _rec(post_id: str, eid: str, strict: bool = True) -> dict | None:
    rec = _lire_doc(eid, strict).get(str(post_id))
    return json.loads(json.dumps(rec)) if isinstance(rec, dict) else None


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
    """L'entrée de diffusion du post dans l'espace (copie), ou None (fichier illisible : None, pour l'affichage)."""
    return _rec(str(post_id), espace_id, strict=False)


def _lancee(rec: dict | None) -> bool:
    if not rec:
        return False
    if rec.get("incertain") is True:
        return True
    if rec.get("statut") == "failed" and rec.get("rien_envoye") is True and rec.get("reel_note") is True:
        return False                             # Kapso a échoué sans rien envoyer (PROUVÉ par la relecture), soldée
    return rec.get("statut") not in RELANCABLES


def relancable(rec: dict | None) -> bool:
    """Revue finale M5 : la config du post peut être modifiée et la diffusion (re)lancée — aucune diffusion, ou une
    diffusion non lancée, ou un `failed` de Kapso PROUVÉ sans envoi et soldé. L'écran revient alors à l'édition."""
    return not _lancee(rec)


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
    """L'envoi « modèle » normalisé (ValueError sinon)."""
    return WE._valider_envoi({"type": "modele", "nom": modele.get("nom"), "langue": modele.get("langue"),
                              "parametres": parametres})


def _verifier(e_: dict, plat: dict) -> None:
    WE._verifier_parametres(e_, plat)
    WE._verifier_composants(e_, plat)


def _diffusable(plat: dict) -> None:
    """Revue finale M4 : les modèles qu'une diffusion ne sait pas remplir (un seul jeu de paramètres du CORPS, sans en-tête
    variable ni code) sont refusés AVANT tout appel, comme l'écran les écarte (`utilisable` de dz-diffusion-whatsapp.js) :
    un en-tête texte à variable, et la catégorie `authentication` (bouton de code à usage unique). WhatsappRefus
    « modele »."""
    if str(plat.get("categorie") or "").lower() == "authentication":
        raise WhatsappRefus("un modèle d'authentification (code à usage unique) ne peut pas partir en diffusion", "modele")
    if (plat.get("composants") or {}).get("entete_variable"):
        raise WhatsappRefus("un modèle à en-tête texte variable ne peut pas partir en diffusion (v1 : corps seulement)",
                            "modele")


async def _neutraliser(post_id: str, bid) -> str:
    """Revue finale I1 : rend inerte un brouillon Kapso (diffusion incertaine que Kapso montre encore `draft`) en vidant
    ses destinataires (`DELETE …/recipients`, permis seulement en brouillon). « vide » : plus rien ne pourra partir (un
    404 aussi : la diffusion n'existe plus) ; « partie » : 422, ce n'est plus un brouillon, Kapso a pris l'envoi ;
    « panne » : réseau, 5xx ou autre refus — rien n'est prouvé."""
    if not bid:
        return "vide"
    try:
        await kapso.vider_destinataires(bid)
        return "vide"
    except kapso.KapsoErreur as x:
        if x.statut == 404:
            # re-revue N1 : un 404 au vidage ne vaut « vidé » que si la diffusion elle-même est introuvable (GET 404)
            try:
                await kapso.broadcast(bid)
            except kapso.KapsoErreur as y:
                if y.statut == 404:
                    return "vide"
            logger.warning(f"diffusion post {post_id} broadcast {bid} : vidage en 404 mais diffusion lisible, rien prouvé")
            return "panne"
        if x.statut == 422:
            logger.warning(f"diffusion post {post_id} broadcast {bid} : plus un brouillon au vidage (422), suivie")
            return "partie"
        logger.warning(f"diffusion post {post_id} broadcast {bid} : vidage du brouillon impossible ({x.code})")
        return "panne"


async def _abandonner_attente(post_id: str, eid: str, rec: dict) -> None:
    """Revue finale M3 : une diffusion en ATTENTE DE CONFIRMATION (incertaine, Kapso dit `draft`) que l'utilisateur
    RECONFIGURE au lieu de la confirmer : le brouillon est vidé (rien ne partira), sa réservation soldée à 0, et la
    diffusion redevient `configuree`. 422 (Kapso a pris l'envoi entre-temps) : relue, suivie, refus `deja_lancee` ;
    panne : refus `incertain`, rien ne change. Sous le verrou du post (l'appelant)."""
    cid = rec.get("compte")
    async with WA._verrou_compte(cid):
        rec = _rec(post_id, eid) or rec
        if not (rec.get("incertain") is True and rec.get("attente_confirmation") is True):
            return
        issue = await _neutraliser(post_id, rec.get("broadcast_id"))
        if issue == "panne":
            raise WhatsappRefus("l'ancienne diffusion n'a pas pu être neutralisée chez Kapso (panne) : rien n'est relancé, "
                                "réessayez dans un instant", "incertain")
        if issue == "partie":
            _modifier(eid, post_id, lambda r: {**r, "attente_confirmation": False, "vidage_refuse": True})
            try:
                await _relire_sous_verrou(post_id, eid, cid)
            except kapso.KapsoErreur as x:
                logger.warning(f"diffusion post {post_id} : relecture impossible ({x.code})")
            raise WhatsappRefus("une diffusion de ce post est déjà lancée : elle ne se modifie plus", "deja_lancee")
        await plafonds.noter_reel_lignes([l["id"] for l in rec.get("lignes") or []], 0.0)   # rien n'est parti
        _modifier(eid, post_id, lambda r: {**r, "statut": "configuree", "incertain": False, "attente_confirmation": False,
                                          "reel_note": True})
        logger.info(f"diffusion post {post_id} broadcast {rec.get('broadcast_id')} : brouillon vidé avant reconfiguration, "
                    "réservation soldée à 0")


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
    """Les `n` messages de la diffusion comptent dans le mois (le plafond de l'espace les voit).
    Revue t328 tâche 3 (point 3, accepté) : compté au send accepté ET incertain, jamais décompté : le plafond se trompe
    vers le haut (une relance confirmée après `draft` compte deux fois), jamais vers le bas."""
    mois = WA._mois(maintenant)

    def geste(e):
        m = e["compteur"].setdefault(mois, {})
        m["sortants"] = int(m.get("sortants") or 0) + n
    WA._noter(cid, geste)


# ---- configurer ----------------------------------------------------------------------------------------------------

async def configurer(post_id, cid: str, *, modele: dict, parametres, identites: list[str] | None) -> dict:
    """Range la configuration de diffusion du post : {config, audience: {n, ecartes}, devis: {usd, lignes}}.
    ValueError : modèle ou paramètres invalides, fichier illisible ; WhatsappRefus : `deja_lancee`, `consentement`,
    `prix`."""
    post_id = str(post_id)
    if not isinstance(modele, dict):
        raise ValueError("modèle : nom et langue exigés")
    if identites is not None and not isinstance(identites, list):
        raise ValueError("identités : une liste est attendue")
    eid, _pid = WA._cle_etat(cid)
    async with _verrou_post(post_id):            # aucun `lancer` de ce post en vol, quel que soit son compte
        rec0 = _rec(post_id, eid)
        if _lancee(rec0) and not (rec0.get("incertain") is True and rec0.get("attente_confirmation") is True):
            raise WhatsappRefus("une diffusion de ce post est déjà lancée : elle ne se modifie plus", "deja_lancee")
        e_ = _envoi(modele, parametres)
        plat = await _modele_approuve(cid, e_["nom"], e_["langue"])
        _verifier(e_, plat)
        _diffusable(plat)
        if _lancee(rec0):                        # revue finale M3 : en attente de confirmation -> brouillon vidé d'abord
            await _abandonner_attente(post_id, eid, rec0)
        try:
            aud = WA.audience_diffusion(cid, categorie=plat["categorie"], identites=identites)
        except WhatsappRefus as x:
            if x.code != "accord":
                raise
            aud = {"retenus": [], "ecartes": x.ecartes}
        marches = _par_marche(aud["retenus"], WA.reglages(eid)["marche_defaut"])
        devis = _devis(_op(plat["categorie"], marches)) if marches else {"total_usd": 0.0, "breakdown": []}
        async with WA._verrou_compte(cid):
            if _lancee(_rec(post_id, eid)):
                raise WhatsappRefus("une diffusion de ce post est déjà lancée : elle ne se modifie plus", "deja_lancee")

            def geste(rec):
                return {"compte": cid,
                        "modele": {"nom": plat["nom"], "langue": plat["langue"], "meta_id": plat["meta_id"],
                                   "categorie": plat["categorie"]},
                        "parametres": e_["parametres"], "identites": list(identites) if identites is not None else None,
                        "broadcast_id": rec.get("broadcast_id"), "statut": "configuree", "incertain": False,
                        "attente_confirmation": False, "n": 0, "lignes": [], "compteurs": {}, "ecartes": aud["ecartes"],
                        "ajout": None, "reel_note": False, "anciennes": rec.get("anciennes") or []}
            config = _modifier(eid, post_id, geste)
    return {"config": config, "audience": {"n": len(aud["retenus"]), "ecartes": aud["ecartes"]},
            "devis": {"usd": devis["total_usd"], "lignes": devis["breakdown"]}}


# ---- lancer --------------------------------------------------------------------------------------------------------

def _rendu(rec: dict) -> dict:
    return {"broadcast_id": rec.get("broadcast_id"), "statut": rec.get("statut"), "n": rec.get("n") or 0,
            "incertain": rec.get("incertain") is True}


async def lancer(post_id, *, confirme_incertain: bool = False) -> dict:
    """Lance la diffusion configurée du post : {broadcast_id, statut, n, incertain}. Voir l'en-tête pour l'ordre.
    PostInconnu ; ValueError (config absente, fichier illisible, espace archivé, modèle) ; WhatsappRefus (`incertain`,
    `deja_lancee`, `accord`, `consentement`, `plafond`, `prix`) ; KapsoErreur (refus du fournisseur) ; 402 de `plafonds`."""
    post_id = str(post_id)
    post = await _post(post_id)
    if post is None:
        raise PostInconnu(post_id)
    eid = post.espace_id
    rec = _rec(post_id, eid) if eid else None
    if not rec or not rec.get("compte"):
        raise ValueError("aucune diffusion WhatsApp n'est configurée pour ce post")
    WA.espace_actif(eid)
    async with _verrou_post(post_id):
        rec = _rec(post_id, eid) or rec          # relu sous le verrou du post : un `configurer` a pu changer le compte
        cid = rec["compte"]
        eid_compte, pid = WA._cle_etat(cid)
        if eid_compte != eid:
            raise ValueError("le compte WhatsApp de cette diffusion n'appartient pas à l'espace du post")
        async with WA._verrou_compte(cid):
            return await _lancer_sous_verrou(post_id, eid, cid, pid, confirme_incertain)


async def _lancer_sous_verrou(post_id, eid, cid, pid, confirme_incertain) -> dict:
    rec = _rec(post_id, eid)
    anciennes: list = []
    if rec.get("incertain") is True:
        relu = None
        try:
            relu = await _relire_sous_verrou(post_id, eid, cid)
        except kapso.KapsoErreur as x:
            logger.warning(f"diffusion post {post_id} : relecture impossible ({x.code})")
        rec = _rec(post_id, eid)
        if rec.get("incertain") is not True:
            return _rendu(rec)                   # Kapso a pris le send : rien à renvoyer
        if not confirme_incertain:
            raise WhatsappRefus("cette diffusion est peut-être déjà partie (panne de Kapso pendant l'envoi) : vérifiez-la, "
                                "puis confirmez pour la relancer", "incertain")
        # revue finale I1 + re-revue O1 : JAMAIS de send d'une nouvelle diffusion tant que l'ancienne n'est pas PROUVÉE
        # incapable de partir. Quelle que soit la relecture (`draft`, `scheduled`, statut inconnu, ou relecture en
        # échec), l'ancien broadcast est VIDÉ d'abord (`DELETE …/recipients`, permis en brouillon et en planifié) —
        # vidé : rien ne partira, solde à 0, relance ; 422 : ce n'est plus un brouillon, Kapso a pris l'envoi : aucune
        # relance, la diffusion reste suivie (`vidage_refuse` : plus jamais « en attente de confirmation ») ; panne :
        # refus `incertain`, rien ne change. Plus aucune ancienne n'est « parquée » pendant qu'une relance part.
        issue = await _neutraliser(post_id, rec.get("broadcast_id"))
        if issue == "panne":
            raise WhatsappRefus("l'ancienne diffusion n'a pas pu être neutralisée chez Kapso (panne) : rien n'est "
                                "relancé, réessayez dans un instant", "incertain")
        if issue == "partie":
            _modifier(eid, post_id, lambda r: {**r, "attente_confirmation": False, "vidage_refuse": True})
            try:
                await _relire_sous_verrou(post_id, eid, cid)
            except kapso.KapsoErreur as x:
                logger.warning(f"diffusion post {post_id} : relecture impossible ({x.code})")
            return _rendu(_rec(post_id, eid))
        await plafonds.noter_reel_lignes([l["id"] for l in rec.get("lignes") or []], 0.0)   # rien n'est parti
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
    _diffusable(plat)
    marches = _par_marche(retenus, WA.reglages(eid)["marche_defaut"])
    op = _op(plat["categorie"], marches)
    devis = _devis(op)
    composants = WE._corps(e_)["template"].get("components")

    cree = await kapso.creer_broadcast(f"dz-{post_id}-{maintenant:%Y%m%d%H%M%S}", pid, plat["meta_id"])
    bid = cree["id"]

    def preparer(r):
        r.pop("vidage_refuse", None)
        r.update(broadcast_id=bid, statut="preparation", incertain=False, attente_confirmation=False, n=0, lignes=[],
                 compteurs={}, ecartes=aud["ecartes"], ajout=None, reel_note=False,
                 modele={**modele, "meta_id": plat["meta_id"], "categorie": plat["categorie"]})
        r["anciennes"] = (r.get("anciennes") or []) + anciennes
        return r
    _modifier(eid, post_id, preparer)
    ajout = {"ajoutes": 0, "doublons": 0, "erreurs": 0}
    try:
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
        garde = await plafonds.verifier(op, "whatsapp", ref=bid, espace_id=eid)  # 402 `dz_plafond` : rien n'est parti
    except Exception as x:
        # panne d'ajout, 402… : rien n'est parti ni réservé ; le brouillon reste chez Kapso, jamais envoyé
        _modifier(eid, post_id, lambda r: {**r, "statut": "configuree", "ajout": ajout}
                  if r.get("statut") == "preparation" else r)
        logger.warning(f"diffusion post {post_id} broadcast {bid} : préparation interrompue ({type(x).__name__}), "
                       "rien envoyé")
        raise
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
        return _rendu(_rec(post_id, eid))
    statut = res.get("statut") or "sending"
    rec = _modifier(eid, post_id, lambda r: {**r, "statut": statut, "incertain": False})
    _mois_plus(cid, n, maintenant)
    if statut in TERMINAUX:                      # déjà terminée au send (ex. failed) : relue et soldée tout de suite
        try:
            rec = await _relire_sous_verrou(post_id, eid, cid)
        except kapso.KapsoErreur as x:          # restera suivie par `a_relire` (reel_note faux)
            logger.warning(f"diffusion post {post_id} broadcast {bid} : relecture impossible ({x.code})")
    logger.info(f"diffusion post {post_id} broadcast {bid} : {n} destinataires, {ajout['doublons']} doublons, "
                f"{ajout['erreurs']} erreurs, statut {statut}")
    return _rendu(rec)


# ---- relire --------------------------------------------------------------------------------------------------------

async def relire(post_id, espace_id: str, *, complet: bool = False) -> dict:
    """Relit la diffusion chez Kapso (voir l'en-tête) et rend l'entrée à jour (`statut_kapso` en plus). Une diffusion non
    lancée et sans `anciennes` est rendue telle quelle, sans appel. Revue t328 tâche 4 (point 5) : tant que la diffusion
    n'est pas terminée, seul le RÉSUMÉ (GET du broadcast) est lu ; les pages de destinataires (désinscriptions, coût réel,
    livrés/lus) le sont au terme, ou sur demande explicite (`complet`, route `?relire=1`). ValueError : aucune diffusion
    configurée, fichier illisible."""
    post_id = str(post_id)
    rec = _rec(post_id, espace_id)
    if not rec or not rec.get("compte"):
        raise ValueError("aucune diffusion WhatsApp n'est configurée pour ce post")
    async with _verrou_post(post_id):
        cid = (_rec(post_id, espace_id) or rec)["compte"]
        async with WA._verrou_compte(cid):
            return await _relire_sous_verrou(post_id, espace_id, cid, complet=complet)


async def _lire_kapso(bid: str, complet: bool = False) -> tuple[dict, list | None, bool]:
    """(broadcast, lignes de TOUS les destinataires, complet) : `complet` faux si la borne PAGES_MAX a coupé la lecture.
    Les pages ne sont lues qu'au terme (ou `draft` : rien n'est parti, la lecture est courte) ou si `complet` est demandé ;
    sinon lignes = None (le résumé seul)."""
    b = await kapso.broadcast(bid)
    if not complet and b["statut"] not in TERMINAUX and b["statut"] != "draft":
        return b, None, False
    lignes, page, pages = [], 1, 1
    while page <= pages and page <= PAGES_MAX:
        d = await kapso.destinataires_broadcast(bid, page=page, par_page=PAR_PAGE)
        lignes.extend(d["lignes"])
        pages = d["pages"]
        page += 1
    return b, lignes, page > pages


def _desinscrire(cid: str, lignes: list) -> int:
    """`suppressed` (préférence marketing coupée) et 131050 (Meta : marketing coupé) -> désinscription ; rend les neuves."""
    desinscrits = WA.etat(cid)["desinscrits_marketing"]
    neufs = []
    for l in lignes:
        chiffres = l["phone_number"].lstrip("+")
        if chiffres and (l["statut"] == "suppressed" or "131050" in str(l.get("code_erreur") or "")):
            ident = "tel:" + chiffres
            if ident not in desinscrits and ident not in neufs:
                neufs.append(ident)
    for ident in neufs:
        WA.noter_desinscription(cid, ident)
    return len(neufs)


async def _solder(eid: str, lignes_kapso: list, lignes_res: list, categorie) -> float:
    """Coût réel par marché (destinataires `sent` × prix) posé sur chaque ligne de réservation ; rend le total."""
    defaut = WA.reglages(eid)["marche_defaut"]
    envoyes: dict = {}
    for l in lignes_kapso:
        chiffres = l["phone_number"].lstrip("+")
        if l["statut"] == "sent" and chiffres:
            m = WE._marche("tel:" + chiffres, defaut)
            envoyes[m] = envoyes.get(m, 0) + 1
    total = 0.0
    for ligne in lignes_res or []:
        k = envoyes.get(ligne["marche"], 0)
        usd = pricing.estimate({"kind": "whatsapp", "categorie": categorie, "marche": ligne["marche"], "n": k})["total_usd"] \
            if k else 0.0
        await plafonds.noter_reel_lignes([ligne["id"]], usd)
        total += usd
    return total


async def _relire_sous_verrou(post_id: str, eid: str, cid: str, complet: bool = False) -> dict:
    rec = _rec(post_id, eid) or {}
    cat = (rec.get("modele") or {}).get("categorie")
    neufs = 0
    # les anciennes diffusions (relance confirmée sans relecture possible) : relues jusqu'à leur terme, puis soldées
    anciennes = rec.get("anciennes") or []
    restantes = []
    for a in anciennes:
        try:
            ba, la, _c = await _lire_kapso(a["broadcast_id"])
        except kapso.KapsoErreur as x:
            if x.statut == 404:                  # revue finale M9 : disparue chez Kapso -> abandonnée après N relectures
                a = {**a, "echecs_404": int(a.get("echecs_404") or 0) + 1}
                if a["echecs_404"] >= SEUIL_INTROUVABLE:
                    logger.error(f"diffusion post {post_id} ancienne {a['broadcast_id']} : introuvable chez Kapso, plus "
                                 "suivie ; réservation gardée (estimation)")
                    continue
            logger.warning(f"diffusion post {post_id} ancienne {a['broadcast_id']} : relecture impossible ({x.code})")
            restantes.append(a)
            continue
        neufs += _desinscrire(cid, la or [])
        if ba["statut"] == "draft":
            # revue finale I1 : un brouillon n'est soldé qu'une fois VIDÉ (il ne pourra plus partir) ; sinon il reste suivi
            if await _neutraliser(post_id, a["broadcast_id"]) == "vide":
                await _solder(eid, la, a.get("lignes"), cat)
            else:
                restantes.append(a)
        elif ba["statut"] in TERMINAUX:          # terminée : soldée au réel
            await _solder(eid, la, a.get("lignes"), cat)
        else:
            restantes.append(a)
    bid = rec.get("broadcast_id")
    sk, compteurs, reel, rien = None, None, None, False
    if bid and _lancee(rec) and rec.get("statut") != "introuvable":
        try:
            b, lignes, complet = await _lire_kapso(bid, complet)
        except kapso.KapsoErreur as x:
            if x.statut != 404:
                raise
            # revue finale M9 : un 404 PERSISTANT (diffusion supprimée chez Kapso) -> `introuvable` après N relectures :
            # plus suivie, réservation gardée (estimation, à arbitrer), une seule ligne au journal
            n404 = int(rec.get("echecs_404") or 0) + 1
            perdue = n404 >= SEUIL_INTROUVABLE

            def geste404(r):
                if anciennes:
                    r["anciennes"] = restantes
                r["echecs_404"] = n404
                if perdue:
                    r.update(statut="introuvable", incertain=False, attente_confirmation=False)
                return r
            rec = _modifier(eid, post_id, geste404)
            if not perdue:
                raise
            logger.error(f"diffusion post {post_id} broadcast {bid} : introuvable chez Kapso ({n404} relectures en 404), "
                         "plus suivie ; réservation gardée (estimation)")
            return {**rec, "statut_kapso": None}
        sk = b["statut"]
        compteurs = dict(b.get("compteurs") or {})
        if lignes is None:                       # résumé seul : livrés/lus de la dernière lecture complète gardés
            avant = rec.get("compteurs") or {}
            compteurs.update({k: avant[k] for k in ("livres", "lus") if k in avant})
        else:
            neufs += _desinscrire(cid, lignes)
            compteurs["livres"] = sum(1 for l in lignes if l.get("livre"))
            compteurs["lus"] = sum(1 for l in lignes if l.get("lu"))
        # « rien n'est parti » se PROUVE : compteur Kapso à 0 (un compteur absent vaut 0 chez `kapso.broadcast`) ET
        # relecture complète des destinataires sans aucune ligne `sent`
        rien = (sk == "failed" and complet and lignes is not None and int(compteurs.get("sent") or 0) == 0
                and not any(l["statut"] == "sent" for l in lignes))
        if sk in TERMINAUX and not rec.get("reel_note"):
            reel = await _solder(eid, lignes, rec.get("lignes"), cat)
    elif not anciennes:
        return rec

    def geste(r):
        if anciennes:
            r["anciennes"] = restantes
        if sk is not None:
            r["compteurs"] = compteurs
            r["rien_envoye"] = rien
            r["echecs_404"] = 0
            if sk in KAPSO_TRANCHE:
                r["incertain"] = False
                r.pop("vidage_refuse", None)
            # re-revue N2 : après un vidage refusé (422), Kapso a pris l'envoi : jamais « en attente » (rien n'est parti)
            r["attente_confirmation"] = (r.get("incertain") is True and sk == "draft"
                                         and r.get("vidage_refuse") is not True)
            if r.get("incertain") is not True and sk:
                r["statut"] = sk
        if reel is not None:
            r["reel_note"] = True
            r["reel_usd"] = round(reel, 4)
        return r
    rec = _modifier(eid, post_id, geste)
    logger.info(f"diffusion post {post_id} broadcast {bid} relue : statut {sk}, {neufs} désinscriptions, "
                f"{len(restantes)} anciennes en cours")
    return {**rec, "statut_kapso": sk}


# ---- relecture de fond -------------------------------------------------------------------------------------------------

def _date(v) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _a_suivre(rec: dict) -> bool:
    if rec.get("anciennes"):
        return True
    if (not rec.get("broadcast_id") or not _lancee(rec) or rec.get("attente_confirmation") is True
            or rec.get("statut") == "introuvable"):
        return False
    if rec.get("statut") in TERMINAUX and rec.get("incertain") is not True:
        return not rec.get("reel_note")          # terminée : suivie seulement tant qu'elle n'est pas soldée
    return True


def _espaces_avec_diffusions() -> list:
    """Revue finale I3 : les espaces qui ont un fichier de diffusions, en LECTURE SEULE du disque (les dossiers de
    `espaces.dossier()`), jamais `espaces.lire()` — elle migre, répare et peut mettre `espaces.json` de côté, ce que la
    boucle de fond ne doit jamais faire (même règle que `marketing._espaces_archives`)."""
    try:
        racine = _es.dossier()
        return sorted(d.name for d in racine.iterdir()
                      if d.is_dir() and _es.id_valide(d.name) and (d / FICHIER).is_file())
    except OSError as x:
        logger.warning(f"diffusions WhatsApp : dossiers des espaces illisibles ({type(x).__name__})")
        return []


def a_relire(maintenant: datetime) -> list:
    """[(post_id, espace_id)] des diffusions à relire en fond (voir l'en-tête) dont `maj` a plus de 60 s."""
    out = []
    if maintenant.tzinfo is None:
        maintenant = maintenant.replace(tzinfo=timezone.utc)
    for eid in _espaces_avec_diffusions():
        try:
            doc = _lire_doc(eid, strict=False)
        except (KeyError, OSError):
            continue
        for post_id, rec in sorted(doc.items()):
            if not isinstance(rec, dict) or not _a_suivre(rec):
                continue
            quand = _date(rec.get("maj"))
            if quand is None or maintenant - quand >= DELAI_RELECTURE:
                out.append((post_id, eid))
    return out


# ---- t328 tâche 4 : le Planificateur (aperçu, report sur le post, adaptateur « whatsapp ») -----------------------------

def apercu(rec: dict | None, espace_id: str) -> dict:
    """{audience: {n, ecartes}, devis: {usd, lignes}} de la config rangée, recalculés SANS réseau ni écriture (l'état des
    accords a pu changer depuis `configurer`). Un refus des règles (consentement, prix…) : {audience: None, devis: None,
    refus: code}."""
    if not rec or not rec.get("compte") or not rec.get("modele"):
        return {"audience": None, "devis": None}
    cat = rec["modele"].get("categorie")
    try:
        try:
            aud = WA.audience_diffusion(rec["compte"], categorie=cat, identites=rec.get("identites"))
        except WhatsappRefus as x:
            if x.code != "accord":
                raise
            aud = {"retenus": [], "ecartes": x.ecartes}
        marches = _par_marche(aud["retenus"], WA.reglages(espace_id)["marche_defaut"])
        devis = _devis(_op(cat, marches)) if marches else {"total_usd": 0.0, "breakdown": []}
    except WhatsappRefus as x:
        return {"audience": None, "devis": None, "refus": x.code}
    return {"audience": {"n": len(aud["retenus"]), "ecartes": aud["ecartes"]},
            "devis": {"usd": devis["total_usd"], "lignes": devis["breakdown"]}}


def _cles_cibles(ids: list) -> list:
    from app.services import comptes as _cpt
    out = []
    for c in ids:
        try:
            out.append(_cpt.cle_distante(_cpt.obtenir(c)))
        except KeyError:
            out.append(None)
    return out


async def reporter_post(post_id, espace_id: str, rec: dict | None) -> bool:
    """Décision 7 : une diffusion que Kapso a PRISE (`deja_prise` : sending/completed/stopped, plus incertaine) est reportée sur son post :
    remote_ids["whatsapp:<compte>"] = broadcast, et le post passe `posted` si toutes ses cibles sont parties. Seulement
    pour un post `ready`/`failed`/`posted` de l'espace qui vise encore ce compte (jamais un post en cours de publication).
    Rend True si le post a changé."""
    if not deja_prise(rec) or not rec.get("compte"):
        return False
    from sqlalchemy import select
    from app.services.storage import ScheduledPost, async_session_factory
    async with async_session_factory() as s:
        p = (await s.execute(select(ScheduledPost).where(ScheduledPost.id == str(post_id)))).scalar_one_or_none()
        if p is None or p.status not in ("ready", "failed", "posted") or (p.espace_id or "deepotus") != espace_id:
            return False
        try:
            ids = json.loads(p.comptes) if p.comptes else []
            remote = json.loads(p.remote_ids) if p.remote_ids else {}
        except (TypeError, ValueError):
            return False
        if not isinstance(ids, list) or rec["compte"] not in ids or not isinstance(remote, dict):
            return False
        cle = f"whatsapp:{rec['compte']}"
        if remote.get(cle) == rec["broadcast_id"]:
            return False
        remote[cle] = rec["broadcast_id"]
        p.remote_ids = json.dumps(remote)
        if p.status != "posted" and all(k is not None and k in remote for k in _cles_cibles(ids)):
            p.status, p.posted_at, p.error = "posted", datetime.utcnow(), None
        try:                                     # revue finale M1 : les règles du client (lecture brute, comme fire_post)
            from app.services import regles_client as _rc
            regles = _rc.exigences(espace_id, p.comptes, brut=True)
        except Exception:  # noqa: BLE001 — sans règles lisibles, pas de ligne de journal (jamais bloquant)
            regles = None
        await s.commit()
    if isinstance(regles, dict) and not regles.get("illisible"):
        # revue finale M1 : la diffusion PUBLIÉE par la relecture de fond (ou ?relire=1) a sa ligne `publication` au
        # journal du client, exactement comme un canal publié par fire_post (même fonction)
        from app.services import marketing as _mk
        _mk._journaliser_publication(regles, rec["compte"])
    logger.info(f"diffusion post {post_id} broadcast {rec['broadcast_id']} : reportée sur le post")
    return True


def deja_prise(rec: dict | None) -> bool:
    """La diffusion est PARTIE et Kapso l'a prise : lancée, plus incertaine, broadcast connu, et pas un `failed` (un
    échec de Kapso n'est pas une publication)."""
    return bool(rec and rec.get("broadcast_id") and _lancee(rec) and rec.get("incertain") is not True
                and rec.get("statut") not in ("failed", "envoi", "introuvable"))


def exiger_incertaine(rec: dict | None) -> None:
    """Revue t328 tâche 4 (point 1a) : une relance CONFIRMÉE ne vaut que pour une diffusion à l'issue incertaine (ou en
    attente de confirmation) ; sinon `WhatsappRefus` « pas_incertaine » (409)."""
    if not rec or not (rec.get("incertain") is True or rec.get("attente_confirmation") is True):
        raise WhatsappRefus("aucune diffusion à l'issue incertaine à confirmer pour ce post : publiez-le normalement",
                            "pas_incertaine")


def vue_config(rec: dict | None) -> dict | None:
    """L'entrée rendue par les routes : les identités explicites COMPTÉES (`n_identites`, None = toute l'audience),
    jamais la liste des numéros."""
    if not rec:
        return rec
    out = {k: v for k, v in rec.items() if k != "identites"}
    ids = rec.get("identites")
    out["n_identites"] = len(ids) if isinstance(ids, list) else None
    return out


def _disponible() -> bool:
    from app.services import comptes as _cpt
    return _cpt.disponible("whatsapp")


async def _publier(caption, video_path, image_path, meta) -> "PublishResult":
    """L'adaptateur du Planificateur (Décision 6) : lance la diffusion configurée du post (`meta["post_id"]`) sur le
    compte COURANT (publishers.publish l'a posé par `comptes.sous_compte`). ok = send accepté (remote_id = broadcast) ;
    sinon un détail NEUTRE : jamais de numéro, de texte de modèle ni de paramètre (refus : son code)."""
    from app.services import comptes as _cpt
    from app.services.publishers import PublishResult
    post_id = str((meta or {}).get("post_id") or "")
    cid = _cpt.courant()
    if not post_id or not cid:
        return PublishResult(False, "whatsapp: diffusion impossible sans post ni compte WhatsApp")
    try:
        eid, _pid = WA._cle_etat(cid)
        rec = lire(post_id, eid)
    except (KeyError, ValueError):
        return PublishResult(False, "whatsapp: compte WhatsApp relié à aucun numéro")
    if not rec or not rec.get("compte"):
        return PublishResult(False, "whatsapp: aucune diffusion configurée pour ce post (modèle et paramètres à choisir)")
    if rec["compte"] != cid:
        return PublishResult(False, "whatsapp: la diffusion de ce post est configurée sur un autre compte WhatsApp")
    if deja_prise(rec):
        # revue t328 tâche 4 (point 1b) : déjà partie (relance confirmée, autre chemin) -> le post la reprend, sans lancer
        return PublishResult(True, f"whatsapp: diffusion {rec['broadcast_id']} déjà lancée ({rec.get('statut')})",
                             rec["broadcast_id"])
    try:
        r = await lancer(post_id)
    except WhatsappRefus as x:
        return PublishResult(False, f"whatsapp: diffusion refusée ({x.code}) : {x.message}")
    except kapso.KapsoErreur as x:
        return PublishResult(False, f"whatsapp: Kapso a refusé la diffusion ({x.statut} {x.code})")
    except PostInconnu:
        return PublishResult(False, "whatsapp: post inconnu")
    except ValueError as x:                      # textes fixes du service (config, espace archivé, modèle…)
        return PublishResult(False, f"whatsapp: {x}")
    except Exception as x:  # noqa: BLE001 — 402 du plafond et le reste : le type seulement, jamais un contenu
        if getattr(x, "status_code", None) == 402:
            return PublishResult(False, "whatsapp: plafond de dépenses atteint, diffusion non lancée")
        logger.warning(f"diffusion post {post_id} : échec ({type(x).__name__})")
        return PublishResult(False, f"whatsapp: diffusion en échec ({type(x).__name__})")
    if r.get("incertain"):
        return PublishResult(False, "whatsapp: issue incertaine (panne de Kapso pendant l'envoi) : relisez la diffusion "
                                    "avant de confirmer une relance")
    return PublishResult(True, f"whatsapp: diffusion {r['broadcast_id']} ({r['n']} destinataires, {r['statut']})",
                         r["broadcast_id"])


def _enregistrer() -> None:
    from app.services import publishers
    publishers.register("whatsapp", _disponible, _publier)


_enregistrer()
