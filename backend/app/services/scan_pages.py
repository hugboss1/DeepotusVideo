# -*- coding: utf-8 -*-
"""t312 (28/10/2026) (C1 Scan, tâche 4) — les fichiers déposés dans la boîte Scan, et le cache des scans (1 h).

`charger(fichiers)` : [(nom, octets)] -> pages dans l'ordre, chacune {"genre": "image", "octets"} ou
{"genre": "texte", "texte"} (Décision 6 du plan) :
- image PNG / JPEG / WEBP / BMP / TIFF reconnue par Pillow (le nom n'est pas cru) ; autre format -> 415 ;
- PDF : chaque page dont le texte sélectionnable (pypdf) compte ≥ 30 caractères hors blancs est une page TEXTE (aucune
  lecture OCR) ; sinon la plus grande image incorporée de la page est lue ; une page sans l'un ni l'autre est sautée ;
  si rien n'en sort -> 422. Pas de rastériseur PDF dans le runtime : c'est la seule voie pour un PDF scanné.
- 1 à 10 fichiers, ≤ 20 Mo chacun (413), ≤ 10 pages en tout après dépliage des PDF (400) ; un PDF de plus de 200
  pages n'est même pas parcouru (400) ;
- revue t312 : toute image (déposée ou incorporée à un PDF) de plus de 60 mégapixels -> 413, jugée sur sa taille
  DÉCLARÉE avant tout décodage (en-tête Pillow, /Width × /Height de l'XObject PDF) ; une image de page PDF qui pèse
  plus de 20 Mo (telle quelle ou ré-encodée) -> 413.
Refus : `RefusPages(message, statut)` (ValueError ; message littéral couvert par L10, statut HTTP pour la route).

Cache : `ranger(resultat, images) -> scan_id`, `obtenir(scan_id)` -> {"images", "resultat", "cree"} (KeyError si
inconnu ou plus vieux d'une heure). En mémoire, 20 scans au plus (le plus ancien est évincé), purgé à chaque accès.
Budget mémoire (revue t312) : 256 Mo d'octets d'image en tout ; au-delà, les plus anciens sont évincés ; un scan
plus lourd que le budget à lui seul n'est PAS gardé (`ranger` rend None : la route le dit, scan_id null).
`images` = la liste de `charger` (pages image ET texte, dans l'ordre) : le secours Claude relit les images et remet
les pages texte à leur place.
Lecture Claude (revue finale t312, Important 1) : `vision_debut(scan_id)` pose le drapeau « lecture payante en cours »
(VisionEnCours s'il l'était déjà : la route rend 409 sans aucun appel), `vision_fin` le lève ; `garder_vision(scan_id, r)` garde
la transcription PAYÉE à part du résultat local (`vision_gardee` la rend, None sinon) et rajeunit le scan d'une heure.
Un scan dont la lecture payante est en cours n'est ni purgé ni évincé (sa réponse payée doit trouver sa place).
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
MAX_OCTETS_IMAGE = MAX_OCTETS  # une image de page PDF, telle quelle ou ré-encodée en PNG
MAX_PIXELS = 60_000_000        # au-delà, le décodage (préparation OCR, réduction Claude) coûterait des centaines de Mo
MAX_PAGES_PDF = 200            # pages brutes parcourues au plus dans un PDF (pages vides comprises)
BUDGET = 256 * 1024 * 1024     # octets d'image gardés en cache, tous scans confondus
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


def _trop_grande():
    raise RefusPages("Image trop grande : 60 mégapixels au plus par page.", 413)


def _format_image(octets: bytes) -> str | None:
    """Le format Pillow de l'image, ou None si elle est illisible. RefusPages 413 au-delà de MAX_PIXELS (taille lue
    dans l'en-tête, avant tout décodage ; une bombe que Pillow refuse dès l'ouverture est aussi un 413)."""
    try:
        with Image.open(io.BytesIO(octets)) as im:
            if im.size[0] * im.size[1] > MAX_PIXELS:
                _trop_grande()
            fmt = (im.format or "").upper()
            im.verify()
    except RefusPages:
        raise
    except Image.DecompressionBombError:
        _trop_grande()
    except Exception:  # noqa: BLE001 — illisible, tronqué : pas une image acceptée
        return None
    return fmt


def _pixels_declares(page) -> int:
    """Le plus grand /Width × /Height des images XObject de la page (et de ses formulaires), lu SANS décoder."""
    plus, pile, vus = 0, [page.get("/Resources")], set()
    while pile:
        res = pile.pop()
        try:
            res = res.get_object() if res is not None else None
            xobj = res.get("/XObject") if res is not None else None
            xobj = xobj.get_object() if xobj is not None else None
        except Exception:  # noqa: BLE001
            continue
        for nom in list(xobj or {}):
            try:
                o = xobj[nom].get_object()
                if id(o) in vus:
                    continue
                vus.add(id(o))
                if o.get("/Subtype") == "/Image":
                    plus = max(plus, int(o.get("/Width", 0)) * int(o.get("/Height", 0)))
                elif o.get("/Subtype") == "/Form":
                    pile.append(o.get("/Resources"))
            except Exception:  # noqa: BLE001
                continue
    return plus


def _image_de_page(page) -> bytes | None:
    """La plus grande image incorporée de la page PDF, en octets lisibles par Pillow (PNG si son format n'est pas
    accepté tel quel) ; None si la page n'en a pas ou si aucune ne se décode."""
    meilleure, aire = None, -1
    if _pixels_declares(page) > MAX_PIXELS:     # avant `page.images`, qui décode toutes les images de la page
        _trop_grande()
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
        sortie = data
    else:
        try:
            tampon = io.BytesIO()
            (pil if pil.mode in ("RGB", "L", "RGBA") else pil.convert("RGB")).save(tampon, "PNG")
            sortie = tampon.getvalue()
        except Exception:  # noqa: BLE001
            return None
    if len(sortie) > MAX_OCTETS_IMAGE:
        raise RefusPages("Image de page PDF trop lourde : 20 Mo au plus.", 413)
    return sortie


def _pages_pdf(octets: bytes, deja: int) -> list[dict]:
    from pypdf import PdfReader
    try:
        lecteur = PdfReader(io.BytesIO(octets))
        nb = len(lecteur.pages)
    except Exception:  # noqa: BLE001 — PDF cassé ou chiffré
        raise RefusPages("Ce PDF est illisible (abîmé ou protégé par un mot de passe).", 422) from None
    if nb > MAX_PAGES_PDF:
        raise RefusPages("PDF trop long : 200 pages au plus.", 400)
    try:
        pages = list(lecteur.pages)
    except Exception:  # noqa: BLE001
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
    for k in [k for k, v in _CACHE.items() if maintenant - v["cree"] > TTL and not v.get("vision_en_cours")]:
        _CACHE.pop(k, None)


def _poids(images: list[dict]) -> int:
    return sum(len(p.get("octets") or b"") for p in images if isinstance(p, dict))


def ranger(resultat, images: list[dict]) -> str | None:
    """Garde un scan 1 h : ses pages (`charger`) et son résultat (None tant qu'il n'est pas lu). Rend son scan_id,
    ou None si le scan dépasse à lui seul le BUDGET (il n'est pas gardé). Les plus anciens sont évincés au-delà de
    MAX_SCANS scans ou du BUDGET d'octets."""
    images = list(images or [])
    poids = _poids(images)
    with _VERROU:
        maintenant = time.time()
        _purger(maintenant)
        if poids > BUDGET:
            logger.warning(f"scan_pages : scan de {poids} octets plus lourd que le cache ({BUDGET}), non gardé")
            return None
        while _CACHE and (len(_CACHE) >= MAX_SCANS or sum(v["poids"] for v in _CACHE.values()) + poids > BUDGET):
            vieux = next((k for k, v in _CACHE.items() if not v.get("vision_en_cours")), None)
            if vieux is None:
                break                              # tous en lecture payante : on dépasse un instant plutôt que de perdre
            _CACHE.pop(vieux)
        sid = uuid.uuid4().hex
        _CACHE[sid] = {"images": images, "resultat": resultat, "cree": maintenant, "poids": poids}
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


# ------------------------------------------------------------------------------------------------- lecture Claude
class VisionEnCours(RuntimeError):
    """Une lecture payante de ce scan tourne déjà (409 `vision_en_cours` sur la route). Message littéral (L10)."""


def _refus_en_cours():
    raise VisionEnCours("Une lecture par Claude de ce scan est déjà en cours : attends sa réponse.")


def vision_debut(scan_id: str) -> bool:
    """Pose le drapeau « lecture payante en cours » (rend True) ; VisionEnCours s'il était déjà posé. KeyError si le
    scan est inconnu."""
    with _VERROU:
        _purger(time.time())
        e = _CACHE[scan_id]
        if e.get("vision_en_cours"):
            _refus_en_cours()
        e["vision_en_cours"] = True
        return True


def vision_fin(scan_id: str) -> None:
    with _VERROU:
        e = _CACHE.get(scan_id)
        if e is not None:
            e.pop("vision_en_cours", None)


def vision_en_cours(scan_id: str) -> bool:
    with _VERROU:
        return bool((_CACHE.get(scan_id) or {}).get("vision_en_cours"))


def vision_libre(scan_id: str) -> None:
    """VisionEnCours si une lecture payante de ce scan tourne."""
    if vision_en_cours(scan_id):
        _refus_en_cours()


def garder_vision(scan_id: str, resultat: dict) -> None:
    """Garde la transcription payée (et en fait le résultat courant) ; le scan vit une heure de plus."""
    with _VERROU:
        e = _CACHE.get(scan_id)
        if e is None:
            return
        e["vision"] = resultat
        e["resultat"] = resultat
        e["cree"] = time.time()
        _CACHE[scan_id] = _CACHE.pop(scan_id)      # le plus jeune : évincé en dernier


def vision_gardee(scan_id: str) -> dict | None:
    """La transcription payée gardée pour ce scan, ou None. KeyError si le scan est inconnu ou expiré."""
    with _VERROU:
        _purger(time.time())
        return _CACHE[scan_id].get("vision")
