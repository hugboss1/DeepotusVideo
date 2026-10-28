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
    r = subprocess.run(args, capture_output=True, timeout=timeout, creationflags=_SANS_FENETRE)
    sortie = (r.stdout or b"").decode("utf-8", "replace").lstrip("\ufeff")
    return r.returncode, sortie, (r.stderr or b"").decode("utf-8", "replace")


_executer = _executer_reel


def disponible() -> dict:
    """{"ok", "langues", "raison"} : les langues installées pour Windows.Media.Ocr (« fr-FR », « en-US »…).
    Calculé une fois par processus (succès comme échec)."""
    global _dispo
    if _dispo is not None:
        return _dispo
    if sys.platform != "win32":
        _dispo = {"ok": False, "langues": [], "raison": "La lecture de texte locale n'existe que sous Windows."}
        return _dispo
    try:
        code, sortie, _err = _executer(_commande("-Langues"), DELAI_LANGUES)
        langues = json.loads(sortie)["langues"] if code == 0 else None
        if langues is not None and (not isinstance(langues, list) or not all(isinstance(x, str) for x in langues)):
            langues = None
    except subprocess.TimeoutExpired:
        langues = None
    except (OSError, ValueError, KeyError, TypeError):
        langues = None
    if langues is None:
        _dispo = {"ok": False, "langues": [],
                  "raison": "La lecture de texte de Windows ne répond pas (PowerShell absent ou bloqué)."}
    elif not langues:
        _dispo = {"ok": False, "langues": [],
                  "raison": "Aucune langue de lecture de texte n'est installée dans Windows."}
    else:
        _dispo = {"ok": True, "langues": langues, "raison": ""}
    return _dispo


def _preparer(octets: bytes) -> tuple[bytes, float, tuple[int, int]]:
    """(PNG préparé, facteur appliqué, (largeur, hauteur) d'origine après rotation EXIF)."""
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
    if f != 1.0:
        im = im.resize((max(1, min(COTE_MAX, int(w * f))), max(1, min(COTE_MAX, int(h * f)))), Image.LANCZOS)
        f = im.size[0] / w
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue(), f, (w, h)


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


def _normaliser(brut, f: float) -> tuple[float, list]:
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
            mots.append({"texte": m["texte"], **{k: _ramener(_nombre(m.get(k)), f) for k in ("x", "y", "l", "h")}})
        texte = li.get("texte")
        lignes.append({"texte": texte if isinstance(texte, str) else " ".join(m["texte"] for m in mots), "mots": mots})
    angle = brut.get("angle")
    angle = 0 if angle is None else _nombre(angle)
    return angle, lignes


def lire_page(octets: bytes, langue: str = "fr") -> dict:
    """Lit une page : {"langue", "angle", "lignes": [{"texte", "mots": [{"texte","x","y","l","h"}]}], "largeur",
    "hauteur"} (repère de l'image d'origine). ValueError (langue ou image), ScanIndisponible, ScanErreur."""
    tag = LANGUES.get(langue) if isinstance(langue, str) else None
    if tag is None:
        raise ValueError("Langue de lecture inconnue : fr ou en.")
    png, f, (w, h) = _preparer(octets)
    if sys.platform != "win32":
        raise ScanIndisponible("La lecture de texte locale n'existe que sous Windows.")
    fd, chemin = tempfile.mkstemp(prefix="dzscan_", suffix=".png")
    t0 = time.perf_counter()
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(png)
        try:
            code, sortie, _err = _executer(_commande("-Image", chemin, "-Langue", tag), DELAI)
        except subprocess.TimeoutExpired:
            raise ScanErreur("La lecture de texte de Windows a dépassé le délai d'une minute.") from None
        except OSError:
            raise ScanIndisponible("La lecture de texte de Windows ne répond pas (PowerShell absent ou bloqué).") from None
    finally:
        try:
            os.unlink(chemin)
        except OSError:
            pass
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
