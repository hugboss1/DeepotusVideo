"""t312 (28/10/2026) (C1 Scan, tâche 1) — pont vers la lecture de texte de Windows (Windows.Media.Ocr).

Décision 1 du plan : le python embarqué n'a ni winrt ni numpy, la lecture passe par Windows PowerShell 5.1 en
sous-processus SANS fenêtre (`scan_ocr.ps1`, JSON UTF-8 sur stdout). L'image est d'abord préparée par Pillow
(niveaux de gris, autocontraste, ×2 sous 1200 px de large, réduite au-dessus de 10 000 px = MaxImageDimension) et
écrite dans un PNG temporaire supprimé quoi qu'il arrive.

Les boîtes des mots sont rendues dans le repère de l'image D'ORIGINE (le facteur de préparation est retiré), avec
`largeur`/`hauteur` d'origine : le nettoyage (tâche 2) et les calques du Vectorlab (t314) n'ont pas à le connaître.

Aucun message ne contient de chemin ni le texte lu ; les journaux ne portent que tailles, nombres et durées.
Couture des bancs : `_executer` (remplacée), `_dispo` (cache par processus, remis à None par les bancs).
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

from loguru import logger
from PIL import Image, ImageOps

SCRIPT = pathlib.Path(__file__).with_name("scan_ocr.ps1")
LANGUES = {"fr": "fr-FR", "en": "en-US"}
DELAI = 60.0                 # secondes, lecture d'une page
DELAI_LANGUES = 20.0         # secondes, liste des langues
LARGEUR_MIN = 1200           # en dessous : agrandie ×2
COTE_MAX = 10000             # OcrEngine.MaxImageDimension mesuré sur cette machine le 28/10
_SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
_dispo: dict | None = None


class ScanIndisponible(RuntimeError):
    """La lecture locale n'est pas possible ici : pas Windows, langue non installée, PowerShell introuvable/bloqué."""


class ScanErreur(RuntimeError):
    """La lecture a été lancée mais a échoué : délai, code de sortie ≠ 0, réponse illisible."""


def _powershell() -> str:
    """Le Windows PowerShell 5.1 du système (WinRT y est chargeable), sinon celui du PATH."""
    racine = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    p = pathlib.Path(racine) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(p) if p.is_file() else "powershell"


def _commande(*extra: str) -> list[str]:
    return [_powershell(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), *extra]


def _executer_reel(args: list[str], timeout: float) -> tuple[int, str, str]:
    """Lance la commande sans fenêtre ; (code, stdout, stderr) décodés en UTF-8. Délai -> subprocess.TimeoutExpired,
    exécutable absent -> FileNotFoundError (laissés à l'appelant)."""
    r = subprocess.run(args, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL,
                       creationflags=_SANS_FENETRE)
    sortie = (r.stdout or b"").decode("utf-8", "replace").lstrip("\ufeff")
    return r.returncode, sortie, (r.stderr or b"").decode("utf-8", "replace")


_executer = _executer_reel


def disponible() -> dict:
    """{"ok", "langues", "raison"} : les langues installées pour Windows.Media.Ocr (« fr-FR », « en-US »…).
    Calculé une fois par processus, sauf un échec passager (délai, PowerShell non lancé : PC chargé, antivirus au
    démarrage) qui n'est pas retenu, pour que l'appel suivant réessaie."""
    global _dispo
    if _dispo is not None:
        return _dispo
    if sys.platform != "win32":
        _dispo = {"ok": False, "langues": [], "raison": "La lecture de texte locale n'existe que sous Windows."}
        return _dispo
    passager = False
    try:
        code, sortie, _err = _executer(_commande("-Langues"), DELAI_LANGUES)
        langues = json.loads(sortie)["langues"] if code == 0 else None
        if langues is not None and (not isinstance(langues, list) or not all(isinstance(x, str) for x in langues)):
            langues = None
    except (subprocess.TimeoutExpired, OSError):
        langues, passager = None, True
    except (ValueError, KeyError, TypeError):
        langues = None
    if langues is None:
        refus = {"ok": False, "langues": [],
                 "raison": "La lecture de texte de Windows ne répond pas (PowerShell absent ou bloqué)."}
        if passager:
            return refus
        _dispo = refus
    elif not langues:
        _dispo = {"ok": False, "langues": [],
                  "raison": "Aucune langue de lecture de texte n'est installée dans Windows."}
    else:
        _dispo = {"ok": True, "langues": langues, "raison": ""}
    return _dispo


def _preparer(octets: bytes) -> tuple[bytes, tuple[float, float], tuple[int, int]]:
    """(PNG préparé, facteurs (fx, fy) appliqués, (largeur, hauteur) d'origine après rotation EXIF). Deux facteurs :
    l'arrondi entier d'une bande très mince (12 000 × 7 px) fausserait y si l'on prenait celui de x."""
    try:
        im = Image.open(io.BytesIO(octets))
        im.load()
        im = ImageOps.exif_transpose(im)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:
        raise ValueError("Image illisible : formats acceptés PNG, JPEG, WEBP, BMP, TIFF.") from e
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
        fond.alpha_composite(im)
        im = fond
    im = ImageOps.autocontrast(im.convert("L"))
    w, h = im.size
    if w < 1 or h < 1:
        raise ValueError("Image illisible : formats acceptés PNG, JPEG, WEBP, BMP, TIFF.")
    f = 2.0 if w < LARGEUR_MIN else 1.0
    if max(w, h) * f > COTE_MAX:
        f = COTE_MAX / max(w, h)
    fx = fy = f
    if f != 1.0:
        im = im.resize((max(1, min(COTE_MAX, int(w * f))), max(1, min(COTE_MAX, int(h * f)))), Image.LANCZOS)
        fx, fy = im.size[0] / w, im.size[1] / h
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue(), (fx, fy), (w, h)


def preparer(octets: bytes) -> bytes:
    """PNG en niveaux de gris, autocontrasté, ×2 sous 1200 px de large, au plus 10 000 px de côté. ValueError si
    l'image est illisible."""
    return _preparer(octets)[0]


def _nombre(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError("boîte non numérique")
    return float(v)


def _ramener(v: float, f: float) -> float:
    r = round(v / f, 1)
    return int(r) if r == int(r) else r


def _normaliser(brut, facteurs: tuple[float, float]) -> tuple[float, list]:
    fx, fy = facteurs
    if not isinstance(brut, dict) or not isinstance(brut.get("lignes", []), list):
        raise TypeError("forme inattendue")
    lignes = []
    for li in brut.get("lignes") or []:
        if not isinstance(li, dict) or not isinstance(li.get("mots", []), list):
            raise TypeError("ligne inattendue")
        mots = []
        for m in li.get("mots") or []:
            if not isinstance(m, dict) or not isinstance(m.get("texte"), str):
                raise TypeError("mot inattendu")
            mots.append({"texte": m["texte"], **{k: _ramener(_nombre(m.get(k)), fx if k in "xl" else fy)
                                                 for k in ("x", "y", "l", "h")}})
        texte = li.get("texte")
        lignes.append({"texte": texte if isinstance(texte, str) else " ".join(m["texte"] for m in mots), "mots": mots})
    angle = brut.get("angle")
    angle = 0 if angle is None else _nombre(angle)
    return angle, lignes


def _supprimer(chemin: str) -> None:
    """Retire le PNG temporaire ; un second essai si un antivirus le tient encore. Journal sans le chemin."""
    for essai in (0, 1):
        try:
            os.unlink(chemin)
            return
        except FileNotFoundError:
            return
        except OSError:
            if essai == 0:
                time.sleep(0.2)
    logger.warning("scan_ocr : PNG temporaire dzscan non supprimé (fichier tenu par un autre programme)")


def lire_page(octets: bytes, langue: str = "fr", *, delai: float | None = None) -> dict:
    """Lit une page : {"langue", "angle", "lignes": [{"texte", "mots": [{"texte","x","y","l","h"}]}], "largeur",
    "hauteur"} (repère de l'image d'origine). ValueError (langue ou image), ScanIndisponible, ScanErreur.
    `delai` (revue finale t312, m1) : le temps qui reste à l'échéance globale de la lecture, s'il est plus court que
    DELAI (le dépassement lève la même ScanErreur de délai)."""
    tag = LANGUES.get(langue) if isinstance(langue, str) else None
    if tag is None:
        raise ValueError("Langue de lecture inconnue : fr ou en.")
    png, f, (w, h) = _preparer(octets)
    if sys.platform != "win32":
        raise ScanIndisponible("La lecture de texte locale n'existe que sous Windows.")
    try:
        fd, chemin = tempfile.mkstemp(prefix="dzscan_", suffix=".png")
    except OSError:
        raise ScanErreur("Impossible d'écrire l'image temporaire de la lecture (disque plein ?).") from None
    t0 = time.perf_counter()
    try:
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(png)
        except OSError:
            raise ScanErreur("Impossible d'écrire l'image temporaire de la lecture (disque plein ?).") from None
        try:
            code, sortie, _err = _executer(_commande("-Image", chemin, "-Langue", tag),
                                           DELAI if delai is None else max(1.0, min(DELAI, float(delai))))
        except subprocess.TimeoutExpired:
            raise ScanErreur("La lecture de texte de Windows a dépassé le délai d'une minute.") from None
        except OSError:
            raise ScanIndisponible("La lecture de texte de Windows ne répond pas (PowerShell absent ou bloqué).") from None
    finally:
        _supprimer(chemin)
    if code == 2:
        raise ScanIndisponible("Cette langue de lecture n'est pas installée dans Windows.")
    if code != 0:
        logger.warning(f"scan_ocr : code {code} ({len(_err or '')} car. sur stderr)")
        raise ScanErreur("La lecture de texte de Windows a échoué.")
    try:
        angle, lignes = _normaliser(json.loads(sortie), f)
    except (ValueError, TypeError, KeyError):
        raise ScanErreur("La lecture de texte de Windows a rendu une réponse illisible.") from None
    logger.info(f"scan_ocr : {w}x{h} px, {len(lignes)} lignes, {sum(len(li['mots']) for li in lignes)} mots, "
                f"{time.perf_counter() - t0:.2f} s")
    return {"langue": langue, "angle": angle, "lignes": lignes, "largeur": w, "hauteur": h}
