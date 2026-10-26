# -*- coding: utf-8 -*-
"""t309 (26/10/2026) — les RÈGLES d'un client (spec boîte à outils §5.5), une seule source de vérité pour les routes du
Planificateur, la boucle (`marketing.tick`), `fire_post` et `sync_lot`.

Le client qui gouverne un post = `espaces.client_responsable(post.espace_id)` : l'espace lui-même s'il est de type client,
sinon le parent client d'un PRODUIT (même archivé). Pas de client -> aucune règle (Deepotus et les marques ne changent pas).
Pour un client :
  - chaque canal visé doit avoir un consentement EN COURS (`revoque_le` None) dans la fiche du client ; le canal d'un compte
    est son `canal_id` (vérification t308, `comptes.canal_id`) : None = jamais couvert ; aucun compte visé = rien de prouvé ;
  - en mode `valide_par_client`, programmer exige la date de validation du client (`valide_client_le`) ;
  - en mode `publie_en_son_nom`, programmer exige la confirmation nominative (`confirme_client == <id du client>`).
Un refus lève `RefusClient` (un PermissionError : les routes en font un 409 structuré ; ses messages passent par L10).

Lecture BRUTE (`brut=True`, la boucle de fond) : espaces.json, client.json et comptes.json sont lus tels quels, sans
`espaces.lire()` ni `fiche_client.lire()` (qui migrent, mettent de côté et écrivent : WinError 32 sous Windows, cf.
`marketing._espaces_archives`) ; aucun fichier ni dossier n'est jamais créé ni touché. Un fichier illisible pour un espace
gouverné rend `illisible: True` : rien n'est prouvé couvert, le post ne part pas (refus par défaut)."""
import json

from loguru import logger

from app.config import DATA_ROOT
from app.services import comptes as _co
from app.services import espaces as _es
from app.services import fiche_client as _fc


class RefusClient(PermissionError):
    """t309 : un post de client qui ne peut pas être programmé ni partir. `code` ∈ {consentement, a_valider, confirmation},
    `client` (id du client responsable), `nom` (société de la fiche, sinon nom de l'espace), `canaux` (libellés ou canal_id)."""

    def __init__(self, message, code, client, nom, canaux):
        super().__init__(message)
        self.message = message
        self.code = code
        self.client = client
        self.nom = nom
        self.canaux = list(canaux)


# ---- lecteurs BRUTS (jamais d'écriture, jamais de mkdir) --------------------------------------------------------------

class _Illisible(Exception):
    """Un fichier lu brut qui n'a pas la forme attendue (interne : jamais rendu à l'écran, donc hors L10)."""


def _brut_json(f):
    """Le document JSON du fichier `f`, None s'il est absent ; ValueError / OSError s'il est illisible."""
    try:
        txt = f.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return json.loads(txt)


def _brut_espaces() -> dict:
    """Les espaces d'espaces.json lu tel quel ({} s'il est absent). _Illisible s'il n'a pas sa forme."""
    doc = _brut_json(DATA_ROOT / "espaces" / "espaces.json")
    if doc is None:
        return {}
    if not isinstance(doc, dict) or not isinstance(doc.get("espaces"), dict):
        raise _Illisible("espaces.json")
    return doc["espaces"]


def _brut_fiche(client: str) -> dict:
    """La fiche du client lue telle quelle puis normalisée par `fiche_client.valider` (pure) ; absente = défauts."""
    if not _es.id_valide(client):
        raise _Illisible("client.json")
    doc = _brut_json(DATA_ROOT / "espaces" / client / "client.json")
    return _fc.valider(doc if doc is not None else {})


def _brut_comptes() -> dict:
    """comptes.json lu tel quel ({"comptes": {}} s'il est absent) ; `verifications` abîmées = aucune (comme `comptes._lire`)."""
    doc = _brut_json(DATA_ROOT / "espaces" / "comptes.json")
    if doc is None:
        return {"comptes": {}, "verifications": {}}
    if not isinstance(doc, dict) or not isinstance(doc.get("comptes"), dict):
        raise _Illisible("comptes.json")
    if not isinstance(doc.get("verifications"), dict):
        doc["verifications"] = {}
    return doc


def _type(e) -> str:
    t = e.get("type") if isinstance(e, dict) else None
    return t if t in _es.TYPES else "marque"


def _brut_responsable(espaces: dict, eid):
    """La règle de `espaces.client_responsable`, sur un espaces.json lu brut : l'espace s'il est client, sinon le parent
    client d'un PRODUIT (même archivé), sinon None."""
    e = espaces.get(eid) if isinstance(eid, str) else None
    if not isinstance(e, dict):
        return None
    if _type(e) == "client":
        return eid
    parent = e.get("parent") or None
    if _type(e) == "produit" and isinstance(parent, str) and isinstance(espaces.get(parent), dict) \
            and _type(espaces[parent]) == "client":
        return parent
    return None


def _brut_canal(doc: dict, cid: str):
    """(libellé, canal_id) d'un compte d'après comptes.json lu brut ; compte inconnu = (son id, None)."""
    if isinstance(cid, str) and cid.startswith(_co.HISTO):
        p = cid[len(_co.HISTO):]
        if p not in _co.PLATEFORMES:
            return cid, None
        lib = f"{_co.PLATEFORMES[p][0]} (historique)"
    else:
        e = doc["comptes"].get(cid)
        if not isinstance(e, dict) or e.get("plateforme") not in _co.PLATEFORMES:
            return str(cid), None
        p = e["plateforme"]
        lib = e.get("libelle") or _co.PLATEFORMES[p][0]
    verif = doc["verifications"].get(cid)
    return lib, _co.canal_id({"plateforme": p, "verification": verif if isinstance(verif, dict) else None})


def _canal(cid: str):
    """(libellé, canal_id) d'un compte par `comptes.obtenir` (chemin de requête) ; compte inconnu = (son id, None)."""
    try:
        v = _co.obtenir(cid)
    except KeyError:
        return str(cid), None
    return v.get("libelle") or v.get("plateforme") or str(cid), v.get("canal_id")


# ---- les exigences ---------------------------------------------------------------------------------------------------

def _ids(comptes) -> list:
    """Les ids de comptes d'un post : liste, ou texte JSON d'une liste ; tout le reste = aucun."""
    if isinstance(comptes, str):
        try:
            comptes = json.loads(comptes) if comptes.strip() else []
        except ValueError:
            return []
    return [x for x in comptes if isinstance(x, str) and x] if isinstance(comptes, list) else []


def _vue(client, nom, mode, canaux, en_cours, illisible=False) -> dict:
    lignes = [{"compte": cid, "libelle": lib, "canal_id": canal,
               "couvert": (not illisible) and canal is not None and canal in en_cours} for cid, lib, canal in canaux]
    out = {"client": client, "nom": nom, "mode": mode, "canaux": lignes,
           "non_couverts": [x["libelle"] for x in lignes if not x["couvert"]]}
    if illisible:
        out["illisible"] = True
    return out


def _nom(espaces: dict, client: str, fiche: dict) -> str:
    e = espaces.get(client) if isinstance(espaces.get(client), dict) else {}
    return fiche.get("societe") or e.get("nom") or client


def _brut_canaux(ids):
    """[(compte, libellé, canal_id)] d'après comptes.json lu brut, et False s'il est illisible (libellés = ids)."""
    try:
        doc = _brut_comptes()
        return [(cid, *_brut_canal(doc, cid)) for cid in ids], True
    except (OSError, ValueError, _Illisible) as e:
        logger.warning(f"règles client : comptes illisibles ({type(e).__name__})")
        return [(cid, str(cid), None) for cid in ids], False


def _exigences_brutes(espace_id, ids):
    try:
        espaces = _brut_espaces()
    except (OSError, ValueError, _Illisible) as e:
        # on ne sait pas qui gouverne l'espace : rien de prouvé (un post de Deepotus, espace vide, n'arrive pas ici)
        logger.warning(f"règles client : espaces illisibles ({type(e).__name__})")
        return _vue("?", "?", _fc.MODE_DEFAUT, _brut_canaux(ids)[0], set(), illisible=True)
    client = _brut_responsable(espaces, espace_id)
    if client is None:
        return None
    canaux, lisibles = _brut_canaux(ids)
    try:
        fiche = _brut_fiche(client)
    except (OSError, ValueError, _Illisible) as e:
        logger.warning(f"règles client : fiche illisible pour {client} ({type(e).__name__})")
        return _vue(client, _nom(espaces, client, {}), _fc.MODE_DEFAUT, canaux, set(), illisible=True)
    en_cours = {x["canal_id"] for x in fiche["consentements"] if x["revoque_le"] is None}
    return _vue(client, _nom(espaces, client, fiche), fiche["mode_publication"], canaux, en_cours, illisible=not lisibles)


def exigences(espace_id, comptes_ids, brut=False):
    """None si l'espace n'est gouverné par aucun client ; sinon {client, nom, mode, canaux:[{compte, libelle, canal_id,
    couvert}], non_couverts:[libellés]} (et `illisible: True` en lecture brute quand un fichier ne se lit pas).
    Un espace vide (post d'avant les espaces) est de Deepotus : aucune règle, rien n'est lu."""
    ids = _ids(comptes_ids)
    if not espace_id:
        return None
    if brut:
        return _exigences_brutes(espace_id, ids)
    client = _es.client_responsable(espace_id)
    if client is None:
        return None
    fiche = _fc.lire(client)
    en_cours = {x["canal_id"] for x in fiche["consentements"] if x["revoque_le"] is None}
    return _vue(client, _nom(_es.lire()["espaces"], client, fiche), fiche["mode_publication"],
                [(cid, *_canal(cid)) for cid in ids], en_cours)


def _champ(post, k):
    return post.get(k) if isinstance(post, dict) else getattr(post, k, None)


def controler(post, confirme=None, brut=False):
    """Les exigences du post si tout va (None sans client) ; sinon RefusClient, dans cet ordre : `consentement` (un canal
    non couvert, ou aucun compte visé), `a_valider` (valide_par_client sans `valide_client_le`), `confirmation`
    (publie_en_son_nom sans confirmation nominative, ni dans `confirme` ni dans `post.confirme_client`)."""
    ex = exigences(_champ(post, "espace_id"), _champ(post, "comptes"), brut=brut)
    if ex is None:
        return None
    client, nom = ex["client"], ex["nom"]
    if ex.get("illisible") or ex["non_couverts"] or not ex["canaux"]:
        liste = ex["non_couverts"]
        canaux = ", ".join(liste) or "—"
        raise RefusClient(f"aucun consentement en cours du client « {nom} » pour : {canaux}",
                          "consentement", client, nom, liste)
    if ex["mode"] == "valide_par_client" and _champ(post, "valide_client_le") is None:
        liste = [x["libelle"] for x in ex["canaux"]]
        raise RefusClient(f"post à valider par le client « {nom} » avant d'être programmé",
                          "a_valider", client, nom, liste)
    if ex["mode"] == "publie_en_son_nom" and (confirme or _champ(post, "confirme_client")) != client:
        liste = [x["canal_id"] or x["libelle"] for x in ex["canaux"]]
        canaux = ", ".join(liste)
        raise RefusClient(f"confirmez la publication au nom du client « {nom} » sur : {canaux}",
                          "confirmation", client, nom, liste)
    return ex


def statut_initial(espace_id, demande) -> str:
    """L'état d'un post créé : `a_valider` au lieu de `draft` pour un client en `valide_par_client`, sinon la demande."""
    if demande != "draft":
        return demande
    ex = exigences(espace_id, [])
    return "a_valider" if ex is not None and ex["mode"] == "valide_par_client" else demande


def en_pause(post) -> bool:
    """La boucle saute ce post : lecture brute, canal non couvert ou post non validé. La confirmation nominative n'est pas
    redemandée à l'heure de partir (elle a été donnée en programmant). Une erreur imprévue = en pause (refus par défaut)."""
    try:
        controler(post, brut=True)
    except RefusClient as e:
        return e.code in ("consentement", "a_valider")
    except Exception as e:  # noqa: BLE001 — jamais une boucle arrêtée pour ça ; rien de prouvé = ne part pas
        logger.warning(f"règles client : contrôle impossible ({type(e).__name__}), post en pause")
        return True
    return False
