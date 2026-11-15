# -*- coding: utf-8 -*-
"""SVR (15/11/2026) — les VIDÉOS de la Bibliothèque que la RÉGIE du studio virtuel projette sur l'écran du décor
(conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md, § 11).

Une vidéo n'est PAS recopiée (elle peut peser des centaines de Mo) : le studio garde une FICHE qui la désigne par le
job de la Bibliothèque et par son fichier, rangé sous le dossier des sorties de l'application. La recette d'un décor ne
porte que la référence `vid:<id>` ; si la vidéo quitte la Bibliothèque, l'écran du décor reste noir et la fiche le dit.

- `DATA_ROOT/studiov/videos/<id>/fiche.json` (+ `vignette.jpg`, tirée à 1 s par ffmpeg, à la demande)
Aucun réseau, aucune dépense. Le fichier servi est TOUJOURS revérifié : sous le dossier des sorties, d'une extension
vidéo, présent."""
from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import threading
from pathlib import Path

from app.services import studiov as S

ID_VIDEO = re.compile(r"^[a-f0-9]{16}$")
ID_JOB = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
EXTENSIONS = (".mp4", ".webm", ".mov", ".mkv", ".m4v")
MIMES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}
MAX_VIDEOS = 60
MAX_NOM = 80
_VERROU = threading.RLock()


class RefusVideo(ValueError):
    """Une demande refusée : `statut` = le code HTTP. Message littéral (traduit par L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return S.racine() / "videos"


def _sorties() -> Path:
    from app.config import settings
    return Path(settings.outputs_path).resolve()


def _dossier(vid) -> Path:
    if not isinstance(vid, str) or not ID_VIDEO.match(vid):
        raise RefusVideo("Identifiant de vidéo invalide.", 400)
    return racine() / vid


def _fiche(vid) -> dict:
    dossier = _dossier(vid)
    try:
        d = json.loads((dossier / "fiche.json").read_text("utf-8"))
    except OSError:
        raise RefusVideo("Vidéo introuvable.", 404) from None
    except ValueError:
        raise RefusVideo("Vidéo illisible.", 404) from None
    if not isinstance(d, dict):
        raise RefusVideo("Vidéo illisible.", 404)
    return d


def _fichier(relatif) -> Path | None:
    """Le fichier désigné par une fiche, s'il est TOUJOURS sous le dossier des sorties, vidéo, et présent."""
    if not isinstance(relatif, str) or not relatif:
        return None
    base = _sorties()
    try:
        f = (base / relatif).resolve()
        f.relative_to(base)
    except (OSError, ValueError):
        return None
    return f if f.suffix.lower() in EXTENSIONS and f.is_file() else None


def _vue(vid: str, d: dict) -> dict:
    duree = d.get("duree")
    return {"id": vid, "ref": f"vid:{vid}", "nom": S.K._texte(d.get("nom"), vid, MAX_NOM) or vid, "job": d.get("job") or "",
            "duree": float(duree) if isinstance(duree, (int, float)) and not isinstance(duree, bool) and 0 <= duree < 86400 else 0.0,
            "cree": d.get("cree") or "", "present": _fichier(d.get("fichier")) is not None,
            "url": f"/api/studiov/videos/{vid}/fichier", "vignette": f"/api/studiov/videos/{vid}/vignette.jpg"}


def lire(vid) -> dict:
    return _vue(vid, _fiche(vid))


def lister() -> list:
    out = []
    if racine().is_dir():
        for d in racine().iterdir():
            if d.is_dir() and ID_VIDEO.match(d.name) and (d / "fiche.json").is_file():
                try:
                    out.append(lire(d.name))
                except RefusVideo:
                    continue
    return sorted(out, key=lambda v: v["cree"], reverse=True)


def chemin(vid) -> Path:
    """Le fichier à servir, revérifié à chaque lecture ; 404 s'il a quitté la Bibliothèque."""
    f = _fichier(_fiche(vid).get("fichier"))
    if f is None:
        raise RefusVideo("Cette vidéo n'est plus dans la Bibliothèque.", 404)
    return f


def mime(f: Path) -> str:
    return MIMES.get(f.suffix.lower(), "video/mp4")


def lier(job, fichier, nom=None, duree=None) -> dict:
    """Garde la fiche d'une vidéo de la Bibliothèque (job `job`, fichier `fichier` : un chemin que l'APPLICATION connaît,
    jamais une saisie). Refus si le fichier n'est pas une vidéo rangée sous le dossier des sorties. Le même job n'est
    lié qu'une fois."""
    if not isinstance(job, str) or not ID_JOB.match(job):
        raise RefusVideo("Vidéo introuvable dans la Bibliothèque.", 404)
    base = _sorties()
    try:
        f = Path(str(fichier)).resolve()
        relatif = f.relative_to(base).as_posix()
    except (OSError, ValueError, TypeError):
        raise RefusVideo("Vidéo introuvable dans la Bibliothèque.", 404) from None
    if _fichier(relatif) is None:
        raise RefusVideo("Vidéo introuvable dans la Bibliothèque.", 404)
    with _VERROU:
        for v in lister():
            fiche = _fiche(v["id"])
            if fiche.get("job") == job and fiche.get("fichier") == relatif:
                return v
        if len(lister()) >= MAX_VIDEOS:
            raise RefusVideo("Trop de vidéos gardées pour la régie : retirez-en une d'abord.", 409)
        vid = secrets.token_hex(8)
        d = _dossier(vid)
        d.mkdir(parents=True, exist_ok=False)
        try:
            S.K._ecrire_json(d / "fiche.json", {"nom": S.K._texte(nom, "", MAX_NOM) or f.stem[:MAX_NOM], "job": job, "fichier": relatif,
                                                "duree": duree if isinstance(duree, (int, float)) and not isinstance(duree, bool) else 0,
                                                "cree": S.K._maintenant()})
        except OSError:
            shutil.rmtree(d, ignore_errors=True)
            raise RefusVideo("La vidéo n'a pas pu être gardée.", 500) from None
    return lire(vid)


def _ffmpeg() -> str:
    from app.services.transcribe_service import _bin
    return _bin("ffmpeg")


def vignette(vid) -> bytes:
    """Une image de la vidéo (à 1 s, 320 px de large), tirée une fois par ffmpeg puis gardée avec la fiche."""
    f = chemin(vid)
    cache = _dossier(vid) / "vignette.jpg"
    try:
        if cache.stat().st_size > 0:
            return cache.read_bytes()
    except OSError:
        pass
    for instant in ("1", "0"):                          # une vidéo de moins d'une seconde : sa première image
        try:
            subprocess.run([_ffmpeg(), "-v", "error", "-y", "-ss", instant, "-i", str(f), "-frames:v", "1", "-vf", "scale=320:-2",
                            "-q:v", "5", str(cache)], capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            break
        try:
            if cache.stat().st_size > 0:
                return cache.read_bytes()
        except OSError:
            continue
    raise RefusVideo("Aperçu de la vidéo indisponible.", 404)


def emplois(decor: dict) -> set:
    """Les références de vidéos que la régie d'un décor emploie."""
    medias = (decor.get("regie") or {}).get("medias") or []
    return {m.get("ref") for m in medias if isinstance(m, dict) and m.get("type") == "video" and isinstance(m.get("ref"), str)}


def decors_qui_emploient(vid: str) -> list:
    ref = f"vid:{vid}"
    return [v["nom"] for v in S._tous() if ref in emplois(v)]


def supprimer(vid) -> None:
    """Oublie la fiche (jamais la vidéo de la Bibliothèque) ; refusé tant qu'une régie l'emploie."""
    with _VERROU:
        d = _dossier(vid)
        if not d.is_dir():
            raise RefusVideo("Vidéo introuvable.", 404)
        emploi = decors_qui_emploient(vid)
        if emploi:
            raise RefusVideo(f"Cette vidéo est dans la régie de {len(emploi)} décor(s) : retirez-la d'abord de « {emploi[0]} ».", 409)
        shutil.rmtree(d, ignore_errors=True)
