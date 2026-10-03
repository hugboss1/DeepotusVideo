# -*- coding: utf-8 -*-
"""Plan-templates T1 (tache #72 du suivi, 03/10/2026) — PLUSIEURS kits de marque.

Un kit = un nom affiche + les six champs de marque de v1.11 (app_name, app_sub, tagline_1, tagline_2, brand_color,
accent_color) + un logo (`logos/<id>.png`). Decisions de l'utilisateur (03/10) : Reglages -> Branding modifie le kit
ACTIF (les routes /branding deviennent sa vue) ; un rendu FIGE le kit actif a l'envoi ; on ne supprime ni le kit
actif ni le dernier ; un ecran gere les kits (PR B).

Migration : au premier appel, le `branding.json` + `logo.png` d'avant deviennent le kit `deepotus` (le logo est COPIE,
les originaux restent). Un `kits.json` ILLISIBLE n'est jamais ecrase en silence : il est mis de cote
(`kits.json.illisible-<horodatage>`) et dit, puis les kits repartent de la migration.

Les gabarits peuvent porter des jetons `{{brand.accent_color}}` ; `appliquer` les remplace par le kit donne, et un
jeton qui ne correspond a aucun champ est REFUSE en le nommant (le plan le laissait tel quel : ffmpeg plantait dessus).
Stockage : DATA_ROOT/assets/branding/ (kits.json, logos/), sous assets/ donc jamais touche par une mise a jour.
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import DATA_ROOT

DEFAUTS: dict[str, str] = {
    "app_name": "DEEPOTUS",
    "app_sub": "VIDEO",
    "tagline_1": "From the deep,",
    "tagline_2": "for the deep.",
    "brand_color": "#ef4444",
    "accent_color": "#00e5ff",
}
CHAMPS = ("name",) + tuple(DEFAUTS)
MAX = 60                                   # la longueur de v1.11, gardee
MAX_KITS = 50
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_JETON = re.compile(r"\{\{\s*brand\.([A-Za-z0-9_]+)\s*\}\}")   # chiffres compris : tagline_1


def dossier() -> Path:
    p = DATA_ROOT / "assets" / "branding"
    (p / "logos").mkdir(parents=True, exist_ok=True)
    return p


def _fichier() -> Path:
    return dossier() / "kits.json"


def _migrer() -> dict:
    kit = dict(DEFAUTS, name="Deepotus")
    ancien = dossier() / "branding.json"
    if ancien.is_file():
        try:
            u = json.loads(ancien.read_text(encoding="utf-8"))
            for k in DEFAUTS:
                if isinstance(u.get(k), str) and u[k].strip():
                    kit[k] = u[k].strip()[:MAX]
        except (ValueError, OSError) as e:
            logger.warning(f"branding.json illisible, kit par defaut : {e}")
    logo = dossier() / "logo.png"
    if logo.is_file():
        shutil.copyfile(logo, dossier() / "logos" / "deepotus.png")
    return {"actif": "deepotus", "kits": {"deepotus": kit}}


def _ecrire(doc: dict) -> None:
    f = _fichier()
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def _sain(doc) -> bool:
    return (isinstance(doc, dict) and isinstance(doc.get("kits"), dict) and doc["kits"]
            and all(isinstance(k, str) and _ID.match(k) and isinstance(v, dict) for k, v in doc["kits"].items()))


def lire() -> dict:
    """{actif, kits} — cree (migration) au premier appel. Un fichier illisible est MIS DE COTE, jamais ecrase."""
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            doc = None
        if _sain(doc):
            if doc.get("actif") not in doc["kits"]:
                doc["actif"] = sorted(doc["kits"])[0]
            return doc
        cote = f.with_name(f"kits.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"kits.json illisible : mis de cote ({cote.name}), kits repris de la migration")
    doc = _migrer()
    _ecrire(doc)
    return doc


def _vue(kid: str, kit: dict, actif: str) -> dict:
    v = {k: (kit.get(k) if isinstance(kit.get(k), str) and kit.get(k) else DEFAUTS.get(k, kid)) for k in CHAMPS}
    v["id"] = kid
    v["actif"] = kid == actif
    v["logo"] = logo_path(kid) is not None
    return v


def actif() -> dict:
    doc = lire()
    return _vue(doc["actif"], doc["kits"][doc["actif"]], doc["actif"])


def lister() -> list:
    doc = lire()
    return [_vue(k, v, doc["actif"]) for k, v in sorted(doc["kits"].items(), key=lambda kv: (kv[0] != doc["actif"], kv[1].get("name", kv[0]).lower()))]


def _propre(champs: dict, base: dict) -> dict:
    out = dict(base)
    for k in CHAMPS:
        v = champs.get(k)
        if not isinstance(v, str) or not v.strip():
            continue
        v = v.strip()
        if k.endswith("_color") and not _COULEUR.match(v):
            raise ValueError(f"{k} doit être #RRGGBB (reçu : {v})")
        out[k] = v[:MAX]
    return out


def enregistrer(champs: dict) -> str:
    """Cree (sans id, ou id neuf) ou met a jour (id existant). Rend l'id. ValueError = entree fautive, dite."""
    doc = lire()
    kid = str(champs.get("id") or "").strip()
    if kid and not _ID.match(kid):
        raise ValueError(f"identifiant de kit invalide : {kid!r} — lettres, chiffres, tiret et souligné seulement")
    if not kid:
        kid = "kit_" + uuid.uuid4().hex[:8]
    neuf = kid not in doc["kits"]
    if neuf and len(doc["kits"]) >= MAX_KITS:
        raise ValueError(f"{MAX_KITS} kits au plus : supprimez-en un d'abord")
    base = doc["kits"].get(kid) or dict(DEFAUTS, name="Nouveau kit")
    doc["kits"][kid] = _propre(champs, base)
    _ecrire(doc)
    return kid


def reinitialiser(kid: str) -> None:
    """Les six champs aux defauts deepotus, le logo retire ; le NOM du kit reste."""
    doc = lire()
    if kid not in doc["kits"]:
        raise ValueError(f"kit inconnu : {kid}")
    doc["kits"][kid] = dict(DEFAUTS, name=doc["kits"][kid].get("name") or kid)
    _ecrire(doc)
    (dossier() / "logos" / f"{kid}.png").unlink(missing_ok=True)


def dupliquer(kid: str) -> str:
    doc = lire()
    if kid not in doc["kits"]:
        raise ValueError(f"kit inconnu : {kid}")
    if len(doc["kits"]) >= MAX_KITS:
        raise ValueError(f"{MAX_KITS} kits au plus : supprimez-en un d'abord")
    nid = "kit_" + uuid.uuid4().hex[:8]
    k = dict(doc["kits"][kid])
    k["name"] = (str(k.get("name") or kid) + " (copie)")[:MAX]
    doc["kits"][nid] = k
    _ecrire(doc)
    src = dossier() / "logos" / f"{kid}.png"
    if src.is_file():
        shutil.copyfile(src, dossier() / "logos" / f"{nid}.png")
    return nid


def activer(kid: str) -> str:
    doc = lire()
    if kid not in doc["kits"]:
        raise ValueError(f"kit inconnu : {kid}")
    doc["actif"] = kid
    _ecrire(doc)
    return kid


def supprimer(kid: str) -> str:
    """"supprime" | "absent" | "seul" (le dernier kit) | "actif" (le kit actif : en activer un autre d'abord)."""
    doc = lire()
    if kid not in doc["kits"]:
        return "absent"
    if len(doc["kits"]) == 1:
        return "seul"
    if doc["actif"] == kid:
        return "actif"
    doc["kits"].pop(kid)
    _ecrire(doc)
    (dossier() / "logos" / f"{kid}.png").unlink(missing_ok=True)
    return "supprime"


def logo_path(kid: str) -> Path | None:
    if not isinstance(kid, str) or not _ID.match(kid):
        return None
    p = dossier() / "logos" / f"{kid}.png"
    return p if p.is_file() else None


def jetons(obj) -> set:
    """Les champs que reclament les jetons {{brand.x}} d'une structure JSON."""
    out = set()

    def marche(v):
        if isinstance(v, str):
            out.update(m.group(1) for m in _JETON.finditer(v))
        elif isinstance(v, list):
            for x in v:
                marche(x)
        elif isinstance(v, dict):
            for x in v.values():
                marche(x)
    marche(obj)
    return out


def appliquer(obj, kit: dict | None = None):
    """Remplace `{{brand.champ}}` dans toutes les chaines d'une structure JSON par le kit donne (l'actif sinon). Un
    jeton qui ne correspond a AUCUN champ de kit : ValueError qui le nomme (un rendu ne part pas avec un trou)."""
    inconnus = sorted(jetons(obj) - set(CHAMPS))
    if inconnus:
        raise ValueError("jeton(s) de marque inconnu(s) dans le gabarit : "
                         + ", ".join("{{brand." + j + "}}" for j in inconnus) + f" — connus : {', '.join(CHAMPS)}")
    k = kit or actif()

    def marche(v):
        if isinstance(v, str):
            return _JETON.sub(lambda m: str(k.get(m.group(1), "")), v)
        if isinstance(v, list):
            return [marche(x) for x in v]
        if isinstance(v, dict):
            return {kk: marche(vv) for kk, vv in v.items()}
        return v
    return marche(obj)
