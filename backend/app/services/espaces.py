# -*- coding: utf-8 -*-
"""t200 (Espaces de marque E0, 13/10/2026) — PLUSIEURS espaces de marque sur une instance.

Un espace = une marque ou un projet (Deepotus, Rippled, un client) : un nom, une couleur, un kit de marque par
defaut, et un dossier `DATA_ROOT/espaces/<id>/` qui porte son `persona.json` (persona v2 en t201) et son
`contenus.json` (modeles de prompt Quick, categories, ingredients du generateur, vibes — t207). Les comptes de
diffusion (t203), les posts (t204) et les depenses (t209) s'y rattacheront par l'id.

Un espace ACTIF a la fois, comme le kit actif ; activer un espace active son kit.
Migration : au premier appel, l'existant devient l'espace `deepotus` A L'OCTET (persona livre, liste Quick actuelle
tiree de prompts.jsx par scripts/espaces/extraire_contenus_deepotus.mjs, kit `deepotus`). Un fichier deja present
n'est jamais ecrase. Un `espaces.json` ILLISIBLE est mis de cote (`espaces.json.illisible-<horodatage>`), jamais
ecrase en silence. Stockage hors du dossier d'installation : une mise a jour n'y touche pas.
"""
from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import DATA_ROOT
from app.services import brand_kits

MAX = 60
MAX_ESPACES = 50
FICHIERS = ("persona.json", "contenus.json", "client.json", "whatsapp.json", "whatsapp_brouillons.json")   # t311 : whatsapp_brouillons.json = les brouillons de l'agent WhatsApp ; t306 : client.json = la fiche d'un espace client ; t310 : whatsapp.json = le canal WhatsApp
_ICI = Path(__file__).resolve().parent.parent
PERSONA_LIVRE = _ICI / "personas" / "deepotus.json"
GRAINE_DEEPOTUS = _ICI / "espaces" / "deepotus_contenus.json"
CONTENUS_VIDES = {"version": 1, "prompt_templates": [], "prompt_cats": [], "ingredients": {}, "vibes": []}
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
# t306 (25/10/2026) : le TYPE d'un espace. Absent du JSON = « marque » (jamais réécrit). Un produit peut avoir un parent
# (une marque ou un client) ; `client_responsable` dit quel client gouverne un espace.
TYPES = ("marque", "produit", "client")


class ConflitClient(ValueError):
    """t306 : passer de « client » à un autre type est refusé tant que des consentements courent (la route dit 409)."""


def dossier() -> Path:
    p = DATA_ROOT / "espaces"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fichier() -> Path:
    return dossier() / "espaces.json"


def id_valide(eid) -> bool:
    return isinstance(eid, str) and bool(_ID.match(eid))


def chemin(eid, nom: str) -> Path | None:
    """Le fichier `nom` de l'espace `eid`, ou None si l'id ou le nom sortent de la liste blanche (jamais de ../)."""
    if not id_valide(eid) or nom not in FICHIERS:
        return None
    return dossier() / eid / nom


def _ecrire_json(f: Path, doc) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    for essai in range(6):          # t210 : sous Windows, un lecteur qui tient le fichier refuse le remplacement un instant
        try:
            tmp.replace(f)
            return
        except PermissionError:
            if essai == 5:
                raise
            time.sleep(0.05 * (essai + 1))


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _migrer() -> dict:
    d = dossier() / "deepotus"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "persona.json").exists():
        shutil.copyfile(PERSONA_LIVRE, d / "persona.json")
    if not (d / "contenus.json").exists():
        shutil.copyfile(GRAINE_DEEPOTUS, d / "contenus.json")
    kit = None                       # Deepotus SUIT le kit de Réglages › Branding (décision du 13/10, après t205)
    return {"actif": "deepotus", "kit_app_repare": True, "espaces": {"deepotus": {   # installation neuve : rien à réparer
        "nom": "Deepotus", "couleur": "#ef4444", "kit_id": kit, "archive": False, "created_at": _maintenant()}}}


def _ecrire(doc: dict) -> None:
    _ecrire_json(_fichier(), doc)


def _sain(doc) -> bool:
    return (isinstance(doc, dict) and isinstance(doc.get("espaces"), dict) and doc["espaces"]
            and all(id_valide(k) and isinstance(v, dict) for k, v in doc["espaces"].items()))


def lire() -> dict:
    """{actif, espaces} — cree (migration) au premier appel. Un fichier illisible est MIS DE COTE, jamais ecrase."""
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            doc = None
        if _sain(doc):
            if doc.get("actif") not in doc["espaces"]:
                doc["actif"] = sorted(doc["espaces"])[0]
            if not doc.get("kit_app_repare"):
                _reparer_kit_app(doc)
            return doc
        cote = f.with_name(f"espaces.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"espaces.json illisible : mis de cote ({cote.name}), espaces repris de la migration")
    doc = _migrer()
    _ecrire(doc)
    return doc


def _vue(eid: str, e: dict, actif: str) -> dict:
    return {"id": eid, "nom": e.get("nom") or eid, "couleur": e.get("couleur") or "#ef4444",
            "type": e.get("type") if e.get("type") in TYPES else "marque", "parent": e.get("parent") or None,
            "kit_id": e.get("kit_id"), "archive": bool(e.get("archive")), "created_at": e.get("created_at"),
            "actif": eid == actif, "plafond_usd": plafond_valide(e.get("plafond_usd"))}


def plafond_valide(v) -> float:
    """t209 : le plafond mensuel OPTIONNEL d'un espace, en $ ; illisible, négatif ou non fini = 0 = aucun (comme le
    plafond global : jamais une ouverture, jamais un refus de l'écran)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return 0.0
    v = float(v)
    return round(v, 4) if v > 0 and v == v and v != float("inf") else 0.0


def filtre(colonne, eid):
    """t209 (Espaces de marque E9) : la condition SQL « appartient à l'espace `eid` ». Une ligne d'avant les espaces
    (colonne vide) est de Deepotus. `eid` vide ou « * » : None = aucun filtre (tout, comme avant)."""
    from sqlalchemy import or_
    if not eid or eid == "*":
        return None
    if eid == "deepotus":
        return or_(colonne.is_(None), colonne == "", colonne == "deepotus")
    return colonne == eid


def de_l_espace(valeur, eid) -> bool:
    """Le même jugement que `filtre`, en Python (une ligne d'index, un fichier jamais indexé = None)."""
    if not eid or eid == "*":
        return True
    return (valeur or "deepotus") == eid


def actif() -> dict:
    doc = lire()
    return _vue(doc["actif"], doc["espaces"][doc["actif"]], doc["actif"])


def lister(archives: bool = False) -> list:
    doc = lire()
    vues = [_vue(k, v, doc["actif"]) for k, v in doc["espaces"].items()]
    vues = [v for v in vues if archives or not v["archive"]]
    return sorted(vues, key=lambda v: (not v["actif"], v["archive"], v["nom"].lower()))


def _nom(v) -> str:
    n = v.strip()[:MAX] if isinstance(v, str) else ""
    if not n:
        raise ValueError("un espace a besoin d'un nom")
    return n


def _couleur(v, defaut: str) -> str:
    if v in (None, ""):
        return defaut
    if not isinstance(v, str) or not _COULEUR.match(v.strip()):
        raise ValueError(f"couleur doit être #RRGGBB (reçu : {v})")
    return v.strip()


def _type_valide(v) -> str:
    """t306 : le type demandé, ou ValueError s'il n'est pas dans TYPES."""
    if v not in TYPES:
        raise ValueError(f"type d'espace inconnu : {v} (marque, produit ou client)")
    return v


def _parent_valide(doc: dict, type_: str, parent, eid: str | None = None) -> str | None:
    """t306 : le parent d'un espace de type `type_`. Seul un produit en a un ; il doit exister (archivé ou non) et être
    une marque ou un client. None / vide = pas de parent. ValueError sinon."""
    if parent in (None, ""):
        return None
    if type_ != "produit":
        raise ValueError("seul un produit peut avoir un parent")
    if eid is not None and parent == eid:
        raise ValueError("un espace ne peut pas être son propre parent")
    if not isinstance(parent, str) or parent not in doc["espaces"]:
        raise ValueError(f"parent inconnu : {parent}")
    if _vue(parent, doc["espaces"][parent], doc["actif"])["type"] not in ("marque", "client"):
        raise ValueError("le parent d'un produit est une marque ou un client")
    return parent


def _consentements_en_cours(eid: str) -> list:
    """t306 : les consentements qui courent pour le client `eid` (lus dans sa fiche) ; vide pour un espace qui n'est pas
    un client ou dont la fiche manque."""
    from app.services import fiche_client      # import local : fiche_client importe espaces
    try:
        return fiche_client.consentements_en_cours(eid)
    except (KeyError, ValueError):
        return []


def creer(champs: dict) -> dict:
    """Un espace neuf, NON actif : persona squelette a son nom, contenus vides, et son propre kit (sauf kit_id
    existant donne). ValueError = entree fautive, dite."""
    doc = lire()
    if len(doc["espaces"]) >= MAX_ESPACES:
        raise ValueError(f"{MAX_ESPACES} espaces au plus : archivez-en ou supprimez-en un d'abord")
    nom = _nom(champs.get("nom"))
    couleur = _couleur(champs.get("couleur"), "#ef4444")
    # Décision de l'utilisateur (13/10/2026, après t205) : un espace neuf SUIT le kit défini dans Réglages › Branding
    # (kit_id vide) — aucun kit n'est fabriqué à son nom ; on peut lui en choisir un pour SES contenus (Réglages › Espaces).
    kit = champs.get("kit_id") or None
    if kit is not None and kit not in brand_kits.lire()["kits"]:
        raise ValueError(f"kit inconnu : {kit}")
    type_ = _type_valide(champs["type"]) if champs.get("type") is not None else "marque"      # t306
    parent = _parent_valide(doc, type_, champs.get("parent"))
    eid = "esp_" + uuid.uuid4().hex[:8]
    _ecrire_json(dossier() / eid / "persona.json", {
        "persona_id": eid, "display_name": nom, "version": 2, "vibe_keywords": [], "default_negative_prompt": "",
        "default_hashtags_pool": [], "templates": []})
    _ecrire_json(dossier() / eid / "contenus.json", CONTENUS_VIDES)
    doc["espaces"][eid] = {"nom": nom, "couleur": couleur, "kit_id": kit, "archive": False, "created_at": _maintenant(),
                           "type": type_, "parent": parent}
    _ecrire(doc)
    return _vue(eid, doc["espaces"][eid], doc["actif"])


def modifier(eid: str, champs: dict) -> dict:
    doc = lire()
    if eid not in doc["espaces"]:
        raise KeyError(eid)
    e = doc["espaces"][eid]
    if "nom" in champs:
        e["nom"] = _nom(champs.get("nom"))
    if "couleur" in champs:
        e["couleur"] = _couleur(champs.get("couleur"), e.get("couleur") or "#ef4444")
    if "kit_id" in champs:                     # vide = suivre le kit de Réglages › Branding
        if champs["kit_id"] and champs["kit_id"] not in brand_kits.lire()["kits"]:
            raise ValueError(f"kit inconnu : {champs['kit_id']}")
        e["kit_id"] = champs["kit_id"] or None
    if "plafond_usd" in champs:                # t209 : 0 = aucun plafond propre à l'espace
        e["plafond_usd"] = plafond_valide(champs.get("plafond_usd"))
    if "type" in champs or "parent" in champs:  # t306 (25/10/2026) : type et parent, mêmes règles qu'à la création
        avant = _vue(eid, e, doc["actif"])
        type_ = _type_valide(champs["type"]) if champs.get("type") is not None else avant["type"]
        if type_ != avant["type"]:
            if avant["type"] == "client" and _consentements_en_cours(eid):
                raise ConflitClient("des consentements courent pour ce client : révoquez-les avant de changer son type")
            if type_ == "produit" and any(_vue(k, v, doc["actif"])["parent"] == eid for k, v in doc["espaces"].items()):
                raise ValueError("des produits dépendent de cet espace : il ne peut pas devenir un produit")
        parent = champs["parent"] if "parent" in champs else (avant["parent"] if type_ == "produit" else None)
        e["type"] = type_
        e["parent"] = _parent_valide(doc, type_, parent, eid)
    _ecrire(doc)
    return _vue(eid, e, doc["actif"])


def client_responsable(eid: str | None = None) -> str | None:
    """t306 : le client qui gouverne l'espace `eid` (courant par défaut) : lui-même s'il est de type client, sinon son
    parent s'il est de type client (même archivé), sinon None. Aucune écriture."""
    doc = lire()
    eid = eid if eid is not None else espace_courant()
    e = doc["espaces"].get(eid) if isinstance(eid, str) else None
    if e is None:
        return None
    v = _vue(eid, e, doc["actif"])
    if v["type"] == "client":
        return eid
    # t306 (25/10/2026) : le parent ne compte que pour un PRODUIT (un `parent` posé à la main sur une marque est ignoré).
    p = doc["espaces"].get(v["parent"]) if v["type"] == "produit" and v["parent"] else None
    if p is not None and _vue(v["parent"], p, doc["actif"])["type"] == "client":
        return v["parent"]
    return None


def activer(eid: str) -> dict:
    """Rend l'espace actif. KeyError = inconnu, ValueError = archivé.
    Décision de l'utilisateur (13/10/2026, après t205) : le logo et le nom de l'APPLICATION ne changent JAMAIS avec
    l'espace ou le persona — activer un espace ne touche plus au kit actif (celui de Réglages › Branding, qui habille
    l'interface). Le kit d'un espace ne sert qu'à SES contenus (jetons {{brand.x}} des gabarits : kit_de_l_espace)."""
    doc = lire()
    if eid not in doc["espaces"]:
        raise KeyError(eid)
    if doc["espaces"][eid].get("archive"):
        raise ValueError("cet espace est archivé : désarchivez-le d'abord")
    doc["actif"] = eid
    _ecrire(doc)
    return _vue(eid, doc["espaces"][eid], eid)


def kit_de_l_espace(eid=None) -> dict:
    """Le kit des CONTENUS de l'espace (courant par défaut) : celui qu'il nomme s'il existe encore, sinon (vide ou kit
    supprimé) le kit actif de Réglages › Branding. N'habille jamais l'interface."""
    kid = (lire()["espaces"].get(resoudre(eid)) or {}).get("kit_id")
    for v in brand_kits.lister():
        if v["id"] == kid:
            return v
    return brand_kits.actif()


def _reparer_kit_app(doc: dict) -> None:
    """Une fois : avant le 13/10, activer un espace activait son kit — l'interface a pu rester habillée du kit d'un
    autre espace (« RIPPLED »). Si le kit actif est celui d'un espace autre que Deepotus, on rend à l'interface le kit
    de Deepotus. Marqué fait dans espaces.json : jamais rejoué (un choix fait ensuite dans Branding est respecté)."""
    try:
        kits = brand_kits.lire()
        dz = doc["espaces"].get("deepotus") or {}
        deep = dz.get("kit_id") if dz.get("kit_id") in kits["kits"] else ("deepotus" if "deepotus" in kits["kits"] else None)
        autres = {e.get("kit_id") for k, e in doc["espaces"].items() if k != "deepotus"} - {None}
        if deep and kits["actif"] != deep and kits["actif"] in autres:
            brand_kits.activer(deep)
            logger.info(f"kit de l'interface rendu à Deepotus ({kits['actif']} -> {deep})")
        if dz:
            dz["kit_id"] = None                 # Deepotus suit désormais le kit de Branding
    except Exception as e:  # noqa: BLE001 — jamais une lecture d'espaces perdue pour ça
        logger.warning(f"réparation du kit de l'interface : {e}")
        return
    doc["kit_app_repare"] = True
    _ecrire(doc)


def archiver(eid: str, archive: bool = True) -> str:
    """"ok" | "absent" | "actif" (l'espace actif ne s'archive pas) | "seul" (le dernier non archive)."""
    doc = lire()
    if eid not in doc["espaces"]:
        return "absent"
    if archive:
        if doc["actif"] == eid:
            return "actif"
        if sum(1 for v in doc["espaces"].values() if not v.get("archive")) <= 1:
            return "seul"
    doc["espaces"][eid]["archive"] = bool(archive)
    _ecrire(doc)
    return "ok"


def contenus(eid: str) -> dict:
    """Le contenus.json de l'espace (contenus vides s'il manque ou est illisible). KeyError = espace inconnu."""
    if eid not in lire()["espaces"]:
        raise KeyError(eid)
    f = chemin(eid, "contenus.json")
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else dict(CONTENUS_VIDES)
    except (OSError, ValueError):
        return dict(CONTENUS_VIDES)


# ---- t201 (Espaces de marque E1) : le persona v2 PAR ESPACE ----------------------------------------------------------
# L'espace « courant » d'un traitement = celui fige pour la requete (middleware de main.py) ou pose par sous_espace(),
# sinon l'espace actif. Une tache de fond lancee pendant une requete herite de son contexte : elle garde son espace
# meme si l'utilisateur en active un autre pendant qu'elle tourne.
from contextlib import contextmanager                                   # noqa: E402
from contextvars import ContextVar                                      # noqa: E402

_ESPACE: ContextVar = ContextVar("dz_espace_courant", default=None)
PERSONA_DEFAUTS = {"version": 2, "vibe_keywords": [], "default_negative_prompt": "", "default_hashtags_pool": [],
                   "voice_modes": {}, "voice_ids": {}, "templates": [], "identite": {}, "audience": {}, "ton": {},
                   "visuel": {}}
_LISTES = ("vibe_keywords", "default_hashtags_pool")
_OBJETS = ("voice_modes", "voice_ids", "brand_colors", "identite", "audience", "ton", "visuel")
_TEXTES = ("default_negative_prompt",)
_MAX_PERSONA = 1_000_000
_cache_persona: dict = {}


def espace_courant() -> str:
    doc = lire()
    e = _ESPACE.get()
    return e if e in doc["espaces"] else doc["actif"]


def figer(eid: str | None = None):
    """Fige l'espace du contexte courant (l'actif par defaut). Rend le jeton a passer a liberer()."""
    return _ESPACE.set(eid if eid is not None else lire()["actif"])


def liberer(jeton) -> None:
    _ESPACE.reset(jeton)


@contextmanager
def sous_espace(eid: str):
    j = figer(eid)
    try:
        yield
    finally:
        liberer(j)


def resoudre(eid=None) -> str:
    """L'id d'espace a lire : `eid` s'il est connu, sinon l'espace courant (un id hostile ne touche pas le disque)."""
    return eid if id_valide(eid) and eid in lire()["espaces"] else espace_courant()


def persona(eid=None) -> dict:
    """Le persona v2 de l'espace (courant par defaut), normalise EN MEMOIRE (le fichier n'est pas reecrit). Relu quand
    le fichier change. Illisible : Deepotus retombe sur le persona livre, un autre espace sur un squelette a son nom."""
    eid = resoudre(eid)
    f = chemin(eid, "persona.json")
    try:
        st = f.stat()
        cle = (str(f), st.st_mtime_ns, st.st_size)
        doc = _cache_persona.get(cle)
        if doc is None:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("persona.json n'est pas un objet")
            _cache_persona.clear()
            _cache_persona[cle] = doc
    except (OSError, ValueError) as e:
        logger.warning(f"persona de l'espace {eid} illisible ({e}) : repli")
        doc = (json.loads(PERSONA_LIVRE.read_text(encoding="utf-8")) if eid == "deepotus"
               else {"display_name": lire()["espaces"][eid].get("nom") or eid})
    out = json.loads(json.dumps(doc))
    for k, v in PERSONA_DEFAUTS.items():
        out.setdefault(k, json.loads(json.dumps(v)))
    out.setdefault("persona_id", eid)
    out.setdefault("display_name", lire()["espaces"][eid].get("nom") or eid)
    return out


def _valider_persona(doc) -> dict:
    from app.models.schemas import PromptTemplate
    if not isinstance(doc, dict):
        raise ValueError("le persona doit être un objet JSON")
    if len(json.dumps(doc, ensure_ascii=False)) > _MAX_PERSONA:
        raise ValueError("persona trop gros (1 Mo au plus)")
    nom = doc.get("display_name")
    if not isinstance(nom, str) or not nom.strip():
        raise ValueError("display_name : le persona a besoin d'un nom")
    for k in _LISTES:
        if k in doc and not (isinstance(doc[k], list) and all(isinstance(x, str) for x in doc[k])):
            raise ValueError(f"{k} doit être une liste de textes")
    for k in _OBJETS:
        if k in doc and not isinstance(doc[k], dict):
            raise ValueError(f"{k} doit être un objet")
    for k in _TEXTES:
        if k in doc and not isinstance(doc[k], str):
            raise ValueError(f"{k} doit être un texte")
    tpls = doc.get("templates", [])
    if not isinstance(tpls, list):
        raise ValueError("templates doit être une liste")
    vus = set()
    for i, t in enumerate(tpls):
        if not isinstance(t, dict):
            raise ValueError(f"modèle n°{i + 1} invalide : pas un objet")
        try:
            PromptTemplate(**t)
        except Exception as e:  # noqa: BLE001 — l'erreur pydantic, dite en une ligne
            raise ValueError(f"modèle n°{i + 1} invalide : {e}".splitlines()[0])
        if t["id"] in vus:
            raise ValueError(f"id de modèle en double : {t['id']}")
        vus.add(t["id"])
    out = dict(doc)
    out["display_name"] = nom.strip()[:120]
    out["version"] = 2
    return out


def ecrire_persona(eid: str, doc) -> dict:
    """Remplace le persona de l'espace apres validation (rien n'est ecrit sur un refus). KeyError = espace inconnu."""
    if not id_valide(eid) or eid not in lire()["espaces"]:
        raise KeyError(eid)
    propre = _valider_persona(doc)
    propre["persona_id"] = eid
    _ecrire_json(chemin(eid, "persona.json"), propre)
    return persona(eid)
