# -*- coding: utf-8 -*-
"""t312 (28/10/2026) (C1 Scan, tâche 4) — les fichiers déposés dans la boîte Scan, et le cache des scans (1 h).

`charger(fichiers)` : [(nom, octets)] -> pages dans l'ordre, chacune {"genre": "image", "octets"} ou
{"genre": "texte", "texte"} (Décision 6 du plan) :
- image PNG / JPEG / WEBP / BMP / TIFF reconnue par Pillow (le nom n'est pas cru) ; autre format -> 415 ;
- PDF : chaque page dont le texte sélectionnable (pypdf) compte ≥ 30 caractères hors blancs est une page TEXTE (aucune
  lecture OCR) ; sinon la plus grande image incorporée de la page est lue ; une page sans l'un ni l'autre est sautée ;
  si rien n'en sort -> 422. Pas de rastériseur PDF dans le runtime : c'est la seule voie pour un PDF scanné.
- 1 à 10 fichiers, ≤ 20 Mo chacun (413), ≤ 10 pages en tout après dépliage des PDF (400).
Refus : `RefusPages(message, statut)` (ValueError ; message littéral couvert par L10, statut HTTP pour la route).

Cache : `ranger(resultat, images) -> scan_id`, `obtenir(scan_id)` -> {"images", "resultat", "cree"} (KeyError si
inconnu ou plus vieux d'une heure). En mémoire, 20 scans au plus (le plus ancien est évincé), purgé à chaque accès.
`images` = la liste de `charger` (pages image ET texte, dans l'ordre) : le secours Claude relit les images et remet
les pages texte à leur place.
Journaux : nombres de pages et tailles seulement, jamais le texte ni les images.
"""
from __future__ import annotations

import io
import threading
import time
import uuid

from loguru import logger
from PIL import Image

MAX_FICHIERS = 10
MAX_PAGES = 10
MAX_OCTETS = 20 * 1024 * 1024
MIN_TEXTE = 30                 # caractères hors blancs : en dessous, la page PDF est tenue pour scannée
TTL = 3600.0                   # secondes
MAX_SCANS = 20
FORMATS = {"PNG", "JPEG", "MPO", "WEBP", "BMP", "TIFF"}     # MPO = le JPEG des téléphones (Pillow le nomme ainsi)

_CACHE: dict[str, dict] = {}   # ordre d'insertion = ordre d'âge
_VERROU = threading.Lock()


class RefusPages(ValueError):
    """Un dépôt refusé : `statut` = le code HTTP (400, 413, 415, 422). Levée avec un message littéral (L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def _format_image(octets: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(octets)) as im:
            fmt = (im.format or "").upper()
            im.verify()
    except Exception:  # noqa: BLE001 — illisible, tronqué, bombe de décompression : pas une image acceptée
        return None
    return fmt


def _image_de_page(page) -> bytes | None:
    """La plus grande image incorporée de la page PDF, en octets lisibles par Pillow (PNG si son format n'est pas
    accepté tel quel) ; None si la page n'en a pas ou si aucune ne se décode."""
    meilleure, aire = None, -1
    try:
        incorporees = list(page.images)
    except Exception:  # noqa: BLE001 — filtre d'image non pris en charge par pypdf
        return None
    for im in incorporees:
        try:
            pil = im.image
            a = pil.size[0] * pil.size[1]
        except Exception:  # noqa: BLE001
            continue
        if a > aire:
            meilleure, aire = (im, pil), a
    if meilleure is None:
        return None
    im, pil = meilleure
    data = bytes(im.data or b"")
    if data and _format_image(data) in FORMATS:
        return data
    try:
        sortie = io.BytesIO()
        (pil if pil.mode in ("RGB", "L", "RGBA") else pil.convert("RGB")).save(sortie, "PNG")
        return sortie.getvalue()
    except Exception:  # noqa: BLE001
        return None


def _pages_pdf(octets: bytes, deja: int) -> list[dict]:
    from pypdf import PdfReader
    try:
        lecteur = PdfReader(io.BytesIO(octets))
        pages = list(lecteur.pages)
    except Exception:  # noqa: BLE001 — PDF cassé ou chiffré
        raise RefusPages("Ce PDF est illisible (abîmé ou protégé par un mot de passe).", 422) from None
    out = []
    for page in pages:
        try:
            texte = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            texte = ""
        if sum(1 for ch in texte if not ch.isspace()) >= MIN_TEXTE:
            out.append({"genre": "texte", "texte": texte})
        else:
            image = _image_de_page(page)
            if image is None:
                continue
            out.append({"genre": "image", "octets": image})
        if deja + len(out) > MAX_PAGES:
            raise RefusPages("Trop de pages : 10 au plus par lecture (les pages des PDF comptent).", 400)
    return out


def charger(fichiers: list[tuple[str, bytes]]) -> list[dict]:
    """[(nom, octets)] -> [{"genre": "image", "octets"} | {"genre": "texte", "texte"}] dans l'ordre. RefusPages."""
    if not isinstance(fichiers, list) or not 1 <= len(fichiers) <= MAX_FICHIERS:
        raise RefusPages("Il faut de 1 à 10 pages à lire.", 400)
    pages: list[dict] = []
    for _nom, octets in fichiers:
        octets = bytes(octets or b"")
        if len(octets) > MAX_OCTETS:
            raise RefusPages("Fichier trop lourd : 20 Mo au plus par page.", 413)
    for _nom, octets in fichiers:
        octets = bytes(octets or b"")
        if octets[:5] == b"%PDF-":
            pages += _pages_pdf(octets, len(pages))
        elif _format_image(octets) in FORMATS:
            pages.append({"genre": "image", "octets": octets})
        else:
            raise RefusPages("Format non pris en charge : PNG, JPEG, WEBP, BMP, TIFF ou PDF.", 415)
        if len(pages) > MAX_PAGES:
            raise RefusPages("Trop de pages : 10 au plus par lecture (les pages des PDF comptent).", 400)
    if not pages:
        raise RefusPages("Rien à lire : ce PDF n'a ni texte sélectionnable ni image de page.", 422)
    logger.info(f"scan_pages : {len(fichiers)} fichier(s), {sum(len(o or b'') for _, o in fichiers)} octets, "
                f"{sum(p['genre'] == 'image' for p in pages)} page(s) image, "
                f"{sum(p['genre'] == 'texte' for p in pages)} page(s) texte")
    return pages


# ------------------------------------------------------------------------------------------------- cache
def _purger(maintenant: float) -> None:
    for k in [k for k, v in _CACHE.items() if maintenant - v["cree"] > TTL]:
        _CACHE.pop(k, None)


def ranger(resultat, images: list[dict]) -> str:
    """Garde un scan 1 h : ses pages (`charger`) et son résultat (None tant qu'il n'est pas lu). Rend son scan_id."""
    with _VERROU:
        maintenant = time.time()
        _purger(maintenant)
        while len(_CACHE) >= MAX_SCANS:
            _CACHE.pop(next(iter(_CACHE)))
        sid = uuid.uuid4().hex
        _CACHE[sid] = {"images": list(images or []), "resultat": resultat, "cree": maintenant}
        return sid


def obtenir(scan_id: str) -> dict:
    """{"images", "resultat", "cree"} ; KeyError si inconnu ou expiré."""
    with _VERROU:
        _purger(time.time())
        return _CACHE[scan_id]


def remplacer(scan_id: str, resultat) -> None:
    """Le résultat d'une nouvelle lecture (Claude) remplace l'ancien ; KeyError si le scan a expiré entre-temps."""
    with _VERROU:
        _purger(time.time())
        _CACHE[scan_id]["resultat"] = resultat
