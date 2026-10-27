# -*- coding: utf-8 -*-
"""t309, extrait en t311 tâche 6 (relecture) : la réponse du CLIENT à la validation d'un post (spec boîte à outils §5.5).

`valider_post(post_id, reponse, moyen)` : « valide » date la validation (un post a_valider devient brouillon, à
programmer) ; « corriger » l'efface et le post repasse a_valider. Une ligne `validation` (qui = client) par canal visé au
journal de la fiche du client responsable. Une décision qui ne vient pas de WhatsApp (moyen ≠ whatsapp : saisie au PC)
rend `perimee` la demande de validation WhatsApp en cours de ce post (ses boutons ne valent plus rien). Refus :
`RefusValidation(message, statut)` — la route POST /api/schedule/{id}/validation-client le traduit en HTTP (400 réponse
ou moyen inconnus, 404 post, 409 sans client). Appelée aussi par `whatsapp_validation.traiter_reponse`.
"""
from __future__ import annotations

from datetime import datetime

from loguru import logger

REPONSES = ("valide", "corriger")


class RefusValidation(Exception):
    """Refus de `valider_post` : `message` (texte de l'utilisateur) et `statut` HTTP (400, 404, 409)."""

    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.message, self.statut = message, statut


async def valider_post(post_id: str, reponse, moyen):
    """Voir l'en-tête. Rend le post (ScheduledPost) après écriture."""
    from sqlalchemy import select
    from app.services import fiche_client as _fc, regles_client as _rc
    from app.services.storage import ScheduledPost, async_session_factory
    if reponse not in REPONSES:
        raise RefusValidation("réponse du client inconnue (valide ou corriger)", 400)
    if moyen not in _fc.MOYENS:
        raise RefusValidation("moyen de réponse inconnu (ecrit, whatsapp ou doigt)", 400)
    async with async_session_factory() as session:
        p = (await session.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))).scalar_one_or_none()
        if p is None:
            raise RefusValidation("post inconnu", 404)
        ex = _rc.exigences(p.espace_id, p.comptes)
        if ex is None:
            raise RefusValidation("ce post n'est gouverné par aucun client", 409)
        if reponse == "valide":
            p.valide_client_le = datetime.utcnow()
            if p.status == "a_valider":
                p.status = "draft"
        else:
            p.valide_client_le = None
            if p.status in ("draft", "scheduled", "ready"):
                p.status = "a_valider"
        await session.commit()
        await session.refresh(p)
        # t309 (revue) : le journal APRÈS l'écriture réussie du post (jamais une validation notée qui n'a pas eu lieu)
        canaux = list(dict.fromkeys(x["canal_id"] or "" for x in ex["canaux"])) or [""]
        for canal in canaux:
            _fc.noter(ex["client"], "validation", canal, "client")
    if moyen != "whatsapp":
        try:
            from app.services import whatsapp_validation as _wv
            _wv.perimer(ex["client"], str(post_id))
        except Exception as e:  # noqa: BLE001 — la décision est prise ; la péremption est un plus, jamais un échec
            logger.warning(f"validation client : demande WhatsApp non périmée ({type(e).__name__})")
    return p
