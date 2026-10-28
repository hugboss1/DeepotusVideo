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
    3 essais puis « echec » ;
  - `entrant(eid, identite)` : appelé par `whatsapp.noter_entrant` pour un message reçu (hors STOP, déjà au registre) :
    contact entrant sur la fiche, Contactée → A répondu. Le texte n'est jamais rangé (règle t310).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException
from loguru import logger

from app.services import prospects as _p, prospects_score as _sc, prospects_sequences as _sq

MAX_ESSAIS = 3


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
    for c in fiche.get("canaux") or []:
        if c.get("type") == "whatsapp":
            chiffres = re.sub(r"\D", "", str(c.get("valeur") or ""))
            if chiffres:
                return "tel:" + chiffres
    return None


def compte_pour(eid, identite: str) -> str | None:
    """Le compte de l'espace dont l'état porte un accord de ce contact (alias compris)."""
    from app.services import whatsapp as WA
    doc = WA._lire_doc(eid)
    for cid, phone in _COMPTES(eid):
        e = WA._etat_doc(doc, phone)             # copie de lecture : rien n'est écrit
        if any(i in e["accords"] for i in WA._groupe(e, identite)):
            return cid
    return None


async def envoyer_dues(eid) -> dict:
    from app.services import whatsapp as WA, kapso
    out = {"envoyes": 0, "arretes": 0, "etat": "ok"}
    if not WA.dans_horaires(_sq._agent(eid), _maintenant()):
        out["etat"] = "hors_horaires"
        return out
    for d in _sq.etapes_dues(eid, "whatsapp"):
        try:
            fiche = _p.lire(eid, d["pid"])
        except _p.RefusProspect:
            _sq.arreter(eid, d["sid"], "effacee")
            continue
        ident = identite_de(fiche)
        cid = compte_pour(eid, ident) if ident else None
        if fiche["statut"] not in _sq.STATUTS_FICHE or not cid \
                or "whatsapp" not in [c["canal"] for c in _sc.canaux_possibles(fiche)]:
            _sq.arreter(eid, d["sid"], "canal")
            out["arretes"] += 1
            continue
        m = d.get("modele")
        envoi = {"type": "modele", "nom": m["nom"], "langue": m["langue"], "parametres": m["parametres"]} if m \
            else {"type": "texte", "texte": d["texte"]}
        try:
            r = await _ENVOYER(cid, ident, envoi)
        except WA.WhatsappRefus as e:
            if e.code == "plafond":
                out["etat"] = "plafond"
                break
            _sq.arreter(eid, d["sid"], "fenetre" if e.code == "fenetre" else "canal")
            out["arretes"] += 1
            continue
        except HTTPException as e:                # 402 : plafond de dépense ; l'étape attend
            out["etat"] = "plafond" if e.status_code == 402 else "refus"
            break
        except ValueError:                        # modèle inconnu, non approuvé, paramètres faux
            _sq.arreter(eid, d["sid"], "modele")
            out["arretes"] += 1
            continue
        except (kapso.KapsoErreur, OSError) as e:
            if _sq.noter_essai(eid, d["sid"], d["rang"]) >= MAX_ESSAIS:
                _sq.arreter(eid, d["sid"], "echec")
            logger.warning(f"WhatsApp prospection {eid} : envoi en échec ({type(e).__name__})")
            out["etat"] = "panne"
            break
        _sq.noter_envoi(eid, d["sid"], d["rang"], str((r or {}).get("id") or ""))
        try:
            _p.noter_contact(eid, d["pid"], "sortant", f"whatsapp : message {d['rang'] + 1} envoyé", "systeme")
            if fiche["statut"] == "qualifie":
                _p.changer_statut(eid, d["pid"], "contacte", "1er message WhatsApp envoyé", "systeme")
        except _p.RefusProspect as e:
            logger.warning(f"WhatsApp envoyé mais fiche {d['pid']} non mise à jour : {e.message}")
        out["envoyes"] += 1
    return out


def entrant(eid, identite: str) -> str | None:
    """Un message reçu d'un contact : s'il est le canal WhatsApp d'une fiche de l'espace, contact entrant et Contactée →
    A répondu. Rend l'id de la fiche, ou None."""
    try:
        fiches = _p.lister(eid)
    except _p.RefusProspect:
        return None
    for f in fiches:
        if f["statut"] == "oppose" or identite_de(f) != identite:
            continue
        try:
            _p.noter_contact(eid, f["id"], "entrant", "whatsapp : message reçu", "systeme")
            if f["statut"] == "contacte":
                _p.changer_statut(eid, f["id"], "repondu", "réponse WhatsApp", "systeme")
        except _p.RefusProspect as e:
            logger.warning(f"réponse WhatsApp non rattachée à {f['id']} : {e.message}")
            return None
        return f["id"]
    return None


def crochet_entrant(cid: str, identite: str) -> None:
    """Le crochet de `whatsapp.noter_entrant` : jamais d'exception (la lecture des messages ne doit pas tomber)."""
    try:
        from app.services import whatsapp as WA
        eid, _ = WA._cle_etat(cid)
        entrant(eid, identite)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"réponse WhatsApp non rattachée aux prospects ({type(e).__name__})")
