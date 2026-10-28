# -*- coding: utf-8 -*-
"""t357 (28/10/2026) — Veille & prospection P6 : WhatsApp pour la prospection. Plan
`docs/superpowers/plans/2026-10-28-prospects-p6-t357.md`.

Aucun chemin d'envoi propre : chaque étape due passe par `whatsapp_echanges.envoyer`, donc par TOUTES ses règles
(consentement d'un espace client, STOP, accord, fenêtre de 24 h, préférence marketing, accord saisi pour un modèle
marketing, plafond du mois, devis et plafond de dépense). Ici seulement :
  - le numéro d'envoi : le compte WhatsApp de l'espace qui porte l'accord du contact (aucun : arrêt « canal ») ;
  - les étapes dues (`prospects_sequences.etapes_dues`), dans les heures calmes, fiche toujours éligible ;
  - refus des règles → séquence arrêtée (« fenetre » pour un texte hors fenêtre, « modele » pour un modèle inconnu,
    « canal » sinon) ; plafond (402 de dépense, plafond du mois) → l'étape attend, la passe s'arrête ; panne de Kapso →
    l'étape attend (jamais arrêtée par une panne) ;
  - `entrant(eid, identite)` : appelé par `whatsapp.noter_entrant` pour un message reçu (hors STOP, déjà au registre) :
    contact entrant sur la fiche, Contactée → A répondu. Le texte n'est jamais rangé (règle t310).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException
from loguru import logger

from app.services import prospects as _p, prospects_score as _sc, prospects_sequences as _sq



def _maintenant() -> datetime:          # couture de banc
    return datetime.now(timezone.utc)


def _comptes(eid) -> list:
    """[(compte_id, phone_id)] des comptes WhatsApp reliés de l'espace."""
    from app.services import whatsapp as WA
    out = []
    for cid in WA._liaisons(eid):
        try:
            out.append((cid, WA._cle_etat(cid)[1]))
        except (KeyError, ValueError):
            continue
    return out


async def _envoyer(cid, identite, envoi):
    from app.services import whatsapp_echanges as WE
    return await WE.envoyer(cid, identite, envoi)


_COMPTES = _comptes                    # coutures de banc
_ENVOYER = _envoyer


def identite_de(fiche: dict) -> str | None:
    """L'identité WhatsApp d'une fiche, normalisée comme le registre (06…, +33 (0)6…, bsuid:… : relecture I3)."""
    from app.services import oppositions as _op
    for c in fiche.get("canaux") or []:
        if c.get("type") == "whatsapp":
            n = _op.normaliser_canal("whatsapp", str(c.get("valeur") or ""))
            if n and (n.startswith("tel:") or n.startswith("bsuid:")):
                return n
    return None


def compte_pour(eid, identite: str) -> str | None:
    """Le compte de l'espace dont l'état porte un accord de ce contact (alias compris) ; AUCUN si un des numéros de
    l'espace a reçu un STOP de ce contact (relecture C1 : le STOP vaut pour tous les numéros)."""
    from app.services import whatsapp as WA
    doc = WA._lire_doc(eid)
    comptes, retenu = _COMPTES(eid), None
    for cid, phone in comptes:
        e = WA._etat_doc(doc, phone)             # copie de lecture : rien n'est écrit
        groupe = WA._groupe(e, identite)
        if any(i in e["stops"] for i in groupe):
            return None
        if retenu is None and any(i in e["accords"] for i in groupe):
            retenu = cid
    return retenu


CODES_MODELE = ("132000", "132001", "132005", "132007", "132012", "132015", "132016")


async def envoyer_dues(eid) -> dict:
    """Relecture t357 : une étape tentée dont l'issue est incertaine n'est JAMAIS renvoyée (arrêt « incertain ») ; un
    refus 4xx de Meta arrête la séquence et la passe continue ; seule une panne AVANT l'appel laisse l'étape attendre."""
    from app.services import whatsapp as WA, kapso
    out = {"envoyes": 0, "arretes": 0, "etat": "ok"}
    if not WA.dans_horaires(_sq._agent(eid), _maintenant()):
        out["etat"] = "hors_horaires"
        return out
    for d in _sq.etapes_dues(eid, "whatsapp"):
        if d.get("tentative"):                   # une tentative précédente sans issue sûre : jamais un second envoi
            _sq.arreter(eid, d["sid"], "incertain")
            out["arretes"] += 1
            continue
        try:
            fiche = _p.lire(eid, d["pid"])
        except _p.RefusProspect:
            _sq.arreter(eid, d["sid"], "effacee")
            continue
        ident = identite_de(fiche)
        cid = compte_pour(eid, ident) if ident else None
        if fiche["statut"] not in _sq.STATUTS_FICHE or not cid                 or "whatsapp" not in [c["canal"] for c in _sc.canaux_possibles(fiche)]:
            _sq.arreter(eid, d["sid"], "canal")
            out["arretes"] += 1
            continue
        m = d.get("modele")
        envoi = {"type": "modele", "nom": m["nom"], "langue": m["langue"], "parametres": m["parametres"]} if m             else {"type": "texte", "texte": d["texte"]}
        if not _sq.encore_due(eid, d["sid"], d["rang"]):
            continue
        _sq.marquer_tentative(eid, d["sid"], d["rang"])
        try:
            r = await _ENVOYER(cid, ident, envoi)
        except WA.WhatsappRefus as e:
            _sq.lever_tentative(eid, d["sid"], d["rang"])
            if e.code in ("plafond", "prix"):     # réglage ou plafond : l'étape attend
                out["etat"] = e.code
                break
            _sq.arreter(eid, d["sid"], "fenetre" if e.code == "fenetre" else "canal")
            out["arretes"] += 1
            continue
        except HTTPException as e:                # 402 : plafond de dépense ; l'étape attend
            _sq.lever_tentative(eid, d["sid"], d["rang"])
            out["etat"] = "plafond" if e.status_code == 402 else "refus"
            break
        except ValueError as e:                   # avant tout appel : modèle inconnu, paramètres, espace archivé…
            _sq.lever_tentative(eid, d["sid"], d["rang"])
            _sq.arreter(eid, d["sid"], "modele" if "modèle" in str(e) or "paramètre" in str(e) else "canal")
            out["arretes"] += 1
            continue
        except kapso.KapsoErreur as e:
            if 400 <= e.statut < 500 and e.statut != 429:      # refus définitif (relecture I2) : jamais en boucle
                _sq.lever_tentative(eid, d["sid"], d["rang"])
                _sq.arreter(eid, d["sid"], "modele" if e.code in CODES_MODELE else "canal")
                out["arretes"] += 1
                continue
            if e.code in ("reseau", "cle_absente", "hote_refuse") and not e.statut:   # rien n'est parti : l'étape attend
                _sq.lever_tentative(eid, d["sid"], d["rang"])
                out["etat"] = "panne"
                break
            _sq.arreter(eid, d["sid"], "incertain")        # 5xx, réponse illisible : a pu partir (relecture I1)
            out["arretes"] += 1
            continue
        except OSError:                            # écriture locale après l'appel : a pu partir
            _sq.arreter(eid, d["sid"], "incertain")
            out["arretes"] += 1
            continue
        _sq.noter_envoi(eid, d["sid"], d["rang"], str((r or {}).get("id") or ""))
        try:
            _p.noter_contact(eid, d["pid"], "sortant", f"whatsapp : message {d['rang'] + 1} envoyé", "systeme")
            if fiche["statut"] == "qualifie":
                _p.changer_statut(eid, d["pid"], "contacte", "1er message WhatsApp envoyé", "systeme")
        except _p.RefusProspect as e:
            logger.warning(f"WhatsApp envoyé mais fiche {d['pid']} non mise à jour : {e.message}")
        out["envoyes"] += 1
    return out


def entrant(eid, identites) -> str | None:
    """Un message reçu d'un contact (son groupe d'identités : tel et bsuid, relecture I4) : s'il est le canal WhatsApp
    d'une fiche de l'espace, contact entrant et Contactée → A répondu. Rend l'id de la (première) fiche, ou None."""
    groupe = {identites} if isinstance(identites, str) else set(identites or [])
    try:
        fiches = _p.lister(eid)
    except _p.RefusProspect:
        return None
    trouve = None
    for f in fiches:
        if f["statut"] == "oppose" or identite_de(f) not in groupe:
            continue
        try:
            _p.noter_contact(eid, f["id"], "entrant", "whatsapp : message reçu", "systeme")
            if f["statut"] == "contacte":
                _p.changer_statut(eid, f["id"], "repondu", "réponse WhatsApp", "systeme")
        except _p.RefusProspect as e:
            logger.warning(f"réponse WhatsApp non rattachée à {f['id']} : {e.message}")
            continue
        trouve = trouve or f["id"]
    return trouve


def crochet_entrant(cid: str, identites) -> None:
    """Le crochet de `whatsapp.noter_entrant` : jamais d'exception (la lecture des messages ne doit pas tomber)."""
    try:
        from app.services import whatsapp as WA
        eid, _ = WA._cle_etat(cid)
        entrant(eid, identites)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"réponse WhatsApp non rattachée aux prospects ({type(e).__name__})")
