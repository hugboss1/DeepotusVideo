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


def ecrire_svg(did: str, svg: str) -> str:
    """Stocke l'export SVG compilé PAR LE CLIENT (compilateur unique,
    verrouillé au snapshot qa) à côté du JSON — écriture atomique."""
    d = _dossier()
    if not (d / f"{did}.json").is_file():
        raise FileNotFoundError(did)
    tmp = d / f"{did}.svg.tmp"
    tmp.write_text(svg, encoding="utf-8")
    os.replace(tmp, d / f"{did}.svg")
    return f"{did}.svg"


def lire_svg(did: str):
    p = _dossier() / f"{did}.svg"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def supprimer(did: str) -> None:
    """Archive le courant en `.v<version>` — jamais de suppression brute.
    La vignette, elle, PART : artefact dérivé qui renaît au premier Sauver,
    pas d'orpheline sur disque."""
    d = _dossier()
    courant = d / f"{did}.json"
    if not courant.is_file():
        raise FileNotFoundError(did)
    os.replace(courant, d / f"{did}.v{version(did)}.json")
    (d / f"{did}.png").unlink(missing_ok=True)


def ecrire_vignette(did: str, octets: bytes) -> str:
    """Vignette PNG (mini-export du client au save) — `<did>.png` à côté du
    JSON, écriture atomique. Le magasin stocke des octets ; le magic PNG se
    vérifie à la ROUTE."""
    d = _dossier()
    if not (d / f"{did}.json").is_file():
        raise FileNotFoundError(did)
    tmp = d / f"{did}.png.tmp"
    tmp.write_bytes(octets)
    os.replace(tmp, d / f"{did}.png")
    return f"{did}.png"


def lire_vignette(did: str):
    p = _dossier() / f"{did}.png"
    return p.read_bytes() if p.is_file() else None


def a_vignette(did: str) -> bool:
    return (_dossier() / f"{did}.png").is_file()


def copier_vignette(src: str, dst: str) -> None:
    """Socle de « dupliquer » : la copie hérite de la vignette du source —
    no-op silencieux si le source n'en a pas."""
    octets = lire_vignette(src)
    if octets is not None:
        ecrire_vignette(dst, octets)


# ── lot A (D1) : les IMAGES du document — `<did>.img<n>.png` à côté du JSON,
# jamais de base64 dans le document. Le nom rendu (`img<n>.png`) est ce que
# l'objet `image` du modèle porte en `href`. Le magasin stocke des octets ;
# le magic PNG se vérifie à la ROUTE. La suppression du document (archive)
# LAISSE les images : l'archive `.v<n>.json` les référence encore.
_NOM_IMAGE = re.compile(r"img([0-9]+)\.png")


def _numeros_images(did: str, d: Path) -> list[int]:
    out = []
    for p in d.glob(f"{did}.img*.png"):
        m = re.fullmatch(re.escape(did) + r"\.img([0-9]+)\.png", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def lister_images(did: str) -> list[str]:
    return [f"img{n}.png" for n in _numeros_images(did, _dossier())]


def ecrire_image(did: str, octets: bytes) -> str:
    d = _dossier()
    if not (d / f"{did}.json").is_file():
        raise FileNotFoundError(did)
    nums = _numeros_images(did, d)
    n = (nums[-1] + 1) if nums else 1
    nom = f"img{n}.png"
    tmp = d / f"{did}.{nom}.tmp"
    tmp.write_bytes(octets)
    os.replace(tmp, d / f"{did}.{nom}")
    return nom


def lire_image(did: str, nom: str):
    if not _NOM_IMAGE.fullmatch(nom or ""):
        return None
    p = _dossier() / f"{did}.{nom}"
    return p.read_bytes() if p.is_file() else None


# ── lot E (D1) : le JOURNAL RASTER du persona Pixel — chaque remplacement
# d'une image journalise l'état précédent sous `<did>.img<n>.pix<k>.png`,
# dix au plus (les plus anciens tombent, comme les `.v<n>.json`) ; « Annuler
# pixels » dépile. Le Ctrl+Z du document ne rend pas les pixels : ce journal
# le fait. `rev` = nombre d'entrées du journal — le client l'ajoute en
# `?v=rev` à l'href pour casser le cache sans toucher au JSON.
JOURNAL_MAX = 10


def _pix_de(did: str, nom: str, d: Path) -> list[int]:
    base = nom[:-4]                                   # img<n>
    out = []
    for p in d.glob(f"{did}.{base}.pix*.png"):
        m = re.fullmatch(re.escape(f"{did}.{base}") + r"\.pix([0-9]+)\.png", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def journal_images(did: str, nom: str) -> int:
    if not _NOM_IMAGE.fullmatch(nom or ""):
        return 0
    return len(_pix_de(did, nom, _dossier()))


def remplacer_image(did: str, nom: str, octets: bytes) -> int:
    """Remplace `nom` par `octets` en journalisant l'état précédent ; rend
    la révision (taille du journal). ValueError hors patron, FileNotFoundError
    si l'image n'existe pas."""
    if not _NOM_IMAGE.fullmatch(nom or ""):
        raise ValueError(nom)
    d = _dossier()
    cible = d / f"{did}.{nom}"
    if not cible.is_file():
        raise FileNotFoundError(nom)
    base = nom[:-4]
    nums = _pix_de(did, nom, d)
    # décaler : pix1 (le plus ancien) tombe quand le journal est plein
    if len(nums) >= JOURNAL_MAX:
        for k in nums[: len(nums) - JOURNAL_MAX + 1]:
            (d / f"{did}.{base}.pix{k}.png").unlink()
        nums = _pix_de(did, nom, d)
        for i, k in enumerate(nums, 1):
            if k != i:
                os.replace(d / f"{did}.{base}.pix{k}.png", d / f"{did}.{base}.pix{i}.png")
        nums = list(range(1, len(nums) + 1))
    k = (nums[-1] + 1) if nums else 1
    os.replace(cible, d / f"{did}.{base}.pix{k}.png")
    tmp = d / f"{did}.{nom}.tmp"
    tmp.write_bytes(octets)
    os.replace(tmp, cible)
    return k


def annuler_image(did: str, nom: str):
    """Dépile la dernière entrée du journal dans `nom` ; rend la révision
    restante, ou None s'il n'y a rien à annuler."""
    if not _NOM_IMAGE.fullmatch(nom or ""):
        return None
    d = _dossier()
    nums = _pix_de(did, nom, d)
    if not nums:
        return None
    k = nums[-1]
    os.replace(d / f"{did}.{nom[:-4]}.pix{k}.png", d / f"{did}.{nom}")
    return len(nums) - 1


def copier_images(src: str, dst: str) -> None:
    """Socle de « dupliquer » : la copie emporte les images sous les MÊMES
    noms (les href du JSON copié restent valides) — no-op sans image."""
    d = _dossier()
    for nom in lister_images(src):
        octets = (d / f"{src}.{nom}").read_bytes()
        tmp = d / f"{dst}.{nom}.tmp"
        tmp.write_bytes(octets)
        os.replace(tmp, d / f"{dst}.{nom}")
