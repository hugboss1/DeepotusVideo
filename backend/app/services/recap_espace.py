"""t308 (26/10/2026) : le RÉCAPITULATIF d'un espace : l'état de chaque canal (vérification de t308) et, pour un espace
gouverné par un client, le consentement qui couvre chacun. Lecture seule, aucun secret, aucun appel réseau.

Module à part (et non dans espaces.py) : il croise trois services (espaces, comptes, fiche_client) ; le mettre dans
espaces.py créerait un import circulaire, `fiche_client` important déjà `espaces`.

Règles :
  - `etat` vaut vert / orange / rouge (la dernière vérification du compte) ou « non_verifie » (aucune, ou effacée par une
    réécriture du compte) ;
  - `consentement` : « sans_objet » si aucun client ne gouverne l'espace ; sinon « en_cours » si un consentement court
    pour le `canal_id` du compte, « manquant » dans tous les autres cas, y compris `canal_id` inconnu (canal jamais
    vérifié : on ne le croit jamais couvert) ;
  - un produit suit son client (§11 bis, `espaces.client_responsable`) : mode de publication et consentements sont ceux
    du client ; un produit sous une marque n'a pas de client.
`espaces.lire()` migre et écrit : ce module ne se lance donc que depuis une requête, jamais d'une boucle de fond."""
from app.services import comptes, espaces, fiche_client

ETATS = ("vert", "orange", "rouge")


def recapitulatif(eid: str) -> dict:
    """Le récapitulatif de l'espace `eid`. KeyError si l'espace est inconnu."""
    e = espaces.lire()["espaces"].get(eid) if isinstance(eid, str) else None
    if e is None:
        raise KeyError(eid)
    type_ = e.get("type") if e.get("type") in espaces.TYPES else "marque"
    client = espaces.client_responsable(eid)
    fiche = fiche_client.lire(client) if client else None
    en_cours = {x["canal_id"] for x in fiche["consentements"] if x["revoque_le"] is None} if fiche else set()
    canaux = []
    for v in comptes.lister(eid):
        ver = v.get("verification")
        etat = ver["etat"] if isinstance(ver, dict) and ver.get("etat") in ETATS else "non_verifie"
        cid = v.get("canal_id")
        if client is None:
            cons = "sans_objet"
        else:
            cons = "en_cours" if cid and cid in en_cours else "manquant"
        canaux.append({"compte": v["id"], "plateforme": v["plateforme"], "libelle": v["libelle"], "etat": etat,
                       "verifie_le": ver.get("date") if isinstance(ver, dict) else None, "canal_id": cid,
                       "consentement": cons})
    return {"espace_id": eid, "type": type_, "client_responsable": client,
            "mode_publication": fiche["mode_publication"] if fiche else None, "canaux": canaux,
            "manques": {"non_verifies": sum(1 for c in canaux if c["etat"] == "non_verifie"),
                        "consentements": sum(1 for c in canaux if c["consentement"] == "manquant")}}
