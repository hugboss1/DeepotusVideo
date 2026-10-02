# -*- coding: utf-8 -*-
"""Plan-studio T8 (tache #70 du suivi, 02/10/2026) — la CADENCE reelle d'un rendu, lue dans le fichier (ffprobe).

Le defilement image par image du Studio a besoin du nombre d'images par seconde et du nombre d'images. Le plan les
prenait au noeud Render du graphe ouvert : le compilateur l'ignore (30 en dur), un clip Seedance ou HeyGen garde sa
cadence d'origine, et le graphe ouvert n'est pas forcement celui qui a ete rendu. Decision de l'utilisateur (02/10) :
la cadence est LUE dans le fichier ; si elle ne peut pas l'etre, 30 et la raison sont DITS (`source: "defaut"`).

`lire_sonde` est pure (le JSON de ffprobe -> le resultat) ; `cadence` lance ffprobe, avec un cache par (chemin, mtime) :
un rendu fini ne change plus.
"""
import json
import subprocess
from pathlib import Path

DEFAUT_FPS = 30.0
_CACHE: dict = {}
_CACHE_MAX = 256


def _taux(v) -> float:
    """« 30000/1001 » -> 29.97 ; « 25 » -> 25.0 ; illisible ou hors [1, 240] -> 0."""
    try:
        s = str(v or "").strip()
        if "/" in s:
            a, b = s.split("/", 1)
            f = float(a) / float(b) if float(b) else 0.0
        else:
            f = float(s)
    except (TypeError, ValueError):
        return 0.0
    return f if 1.0 <= f <= 240.0 else 0.0


def _nombre(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if f > 0 else 0.0


def defaut(raison: str) -> dict:
    return {"fps": DEFAUT_FPS, "frames": None, "duration_s": None, "source": "defaut", "raison": raison}


def lire_sonde(texte: str) -> dict:
    """Le JSON de `ffprobe -show_entries stream=avg_frame_rate,r_frame_rate,nb_frames,duration:format=duration`."""
    try:
        d = json.loads(texte or "{}")
        s = (d.get("streams") or [{}])[0] or {}
        fmt = d.get("format") or {}
    except (ValueError, TypeError, AttributeError, IndexError):
        return defaut("réponse de ffprobe illisible")
    # avg d'abord : r_frame_rate vaut le pas de base du flux (90000/1 sur certains fichiers a cadence variable)
    fps = _taux(s.get("avg_frame_rate")) or _taux(s.get("r_frame_rate"))
    if not fps:
        return defaut("cadence absente du flux vidéo")
    dur = _nombre(s.get("duration")) or _nombre(fmt.get("duration"))
    n = int(_nombre(s.get("nb_frames")))
    if not n and dur:
        n = int(round(dur * fps))
    return {"fps": round(fps, 3), "frames": n or None, "duration_s": round(dur, 3) if dur else None,
            "source": "fichier", "raison": None}


def cadence(path) -> dict:
    p = Path(path)
    try:
        cle = (str(p.resolve()), p.stat().st_mtime_ns)
    except OSError:
        return defaut("fichier introuvable")
    if cle in _CACHE:
        return dict(_CACHE[cle])
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=avg_frame_rate,r_frame_rate,nb_frames,duration:format=duration",
                            "-of", "json", str(p)], capture_output=True, timeout=15, check=False)
    except FileNotFoundError:
        return defaut("ffprobe introuvable")
    except subprocess.TimeoutExpired:
        return defaut("ffprobe n'a pas répondu en 15 s")
    if r.returncode != 0:
        return defaut("ffprobe a refusé le fichier")
    res = lire_sonde((r.stdout or b"").decode("utf-8", errors="replace"))
    if res["source"] == "fichier":
        while len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)), None)
        _CACHE[cle] = dict(res)
    return res
