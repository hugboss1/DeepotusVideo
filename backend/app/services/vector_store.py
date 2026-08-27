"""Vectorlab — magasin disque des documents vectoriels.

Le contenu vit en fichiers JSON (`<did>.json` = courant, `<did>.v<n>.json` =
historique, élagué aux 10 dernières versions) ; l'index et l'ancrage
(chapitre/entité/rôle) vivent dans SQLite (storage.VectorDoc). Écriture
ATOMIQUE (tmp + os.replace) : jamais de document tronqué visible. La
suppression ARCHIVE (le courant devient sa dernière version d'historique),
elle n'efface rien.

Dossier : env `VECTOR_FOLDER` (les bancs), sinon
`<dossier images>/../vector` (DeepotusVideoGenData/assets/vector en prod).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

_GARDE_HISTORIQUE = 10


def _dossier() -> Path:
    env = os.environ.get("VECTOR_FOLDER", "").strip()
    if env:
        d = Path(env)
    else:
        from app.config import settings
        d = settings.images_path.parent / "vector"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _valider(doc: dict) -> dict:
    if not isinstance(doc, dict) or "taille" not in doc or "calques" not in doc:
        raise ValueError("document invalide: taille et calques requis")
    return doc


def _ecrire_atomique(chemin: Path, doc: dict) -> None:
    tmp = chemin.parent / (chemin.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.replace(tmp, chemin)


def _versions_hist(did: str, d: Path) -> list[int]:
    out = []
    for p in d.glob(f"{did}.v*.json"):
        m = re.fullmatch(re.escape(did) + r"\.v([0-9]+)\.json", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def version(did: str) -> int:
    """Version du document COURANT = max de l'historique + 1 (1 sans rien)."""
    d = _dossier()
    if not (d / f"{did}.json").is_file():
        raise FileNotFoundError(did)
    hist = _versions_hist(did, d)
    return (hist[-1] + 1) if hist else 1


def creer(doc: dict) -> str:
    did = uuid.uuid4().hex[:12]
    _ecrire_atomique(_dossier() / f"{did}.json", _valider(doc))
    return did


def lire(did: str) -> dict:
    p = _dossier() / f"{did}.json"
    if not p.is_file():
        raise FileNotFoundError(did)
    return json.loads(p.read_text(encoding="utf-8"))


def ecrire(did: str, doc: dict) -> int:
    """Réécrit le courant ; l'ancien devient `.v<n>` ; rend la version neuve."""
    d = _dossier()
    courant = d / f"{did}.json"
    if not courant.is_file():
        raise FileNotFoundError(did)
    v = version(did)
    os.replace(courant, d / f"{did}.v{v}.json")
    _ecrire_atomique(courant, _valider(doc))
    hist = _versions_hist(did, d)
    for n in hist[:-_GARDE_HISTORIQUE]:
        (d / f"{did}.v{n}.json").unlink(missing_ok=True)
    return v + 1


def supprimer(did: str) -> None:
    """Archive le courant en `.v<version>` — jamais de suppression brute."""
    d = _dossier()
    courant = d / f"{did}.json"
    if not courant.is_file():
        raise FileNotFoundError(did)
    os.replace(courant, d / f"{did}.v{version(did)}.json")
