"""P2 (plan Quick T2, tâche #51 du suivi, 01/10/2026) — les outils fal qui prennent une VIDÉO en entrée (extension
générative), par opposition à fal_service.py qui part d'une image.

Ici la garde ne porte pas sur ce que l'écran promet mais sur ce que ffprobe MESURE du fichier déjà rendu — durée,
taille, format — et un refus CITE la mesure : « ce clip fait 31,0 s » vaut mieux que « source invalide ».

MESURÉ le 01/10/2026 (OpenAPI publique fal, `endpoint_id=fal-ai/veo3.1/extend-video` et `.../fast/extend-video`) :
champs requis `video_url` et `prompt` (le prompt est OBLIGATOIRE), `generate_audio` (vrai par défaut), `duration` « 7s »,
`aspect_ratio` auto | 16:9 | 9:16, `resolution` 720p par défaut ; la source doit être en 720p ou 1080p, 16:9 ou 9:16.
Prix relevés sur fal.ai le même jour (le plan, « de mémoire », disait 0,10 $/s pour le standard — quatre fois moins) :
Veo 3.1 = 0,20 $/s sans son, 0,40 $/s avec ; Veo 3.1 Fast = 0,10 $/s sans son, 0,15 $/s avec. fal présente l'outil
comme « prolonger des vidéos créées par Veo, jusqu'à 30 s » : la borne de SOURCE n'est pas publiée, on garde
30 − 7 = 23 s ; un clip d'un autre modèle peut être refusé ou mal prolongé (l'écran le dit).
Décision de l'utilisateur (01/10) : Veo 3.1 Fast par défaut, le son au choix, le prix montré avant le tir et chiffré
dans la garde des plafonds. Tout est PUR sauf `probe`, qui lance ffprobe.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_EXTEND = "veo-3.1-fast-extend"
EXTEND_MODELS: dict = {
    "veo-3.1-fast-extend": {
        "label": "Veo 3.1 Fast · extension",
        "endpoint": "fal-ai/veo3.1/fast/extend-video",
        "video_param": "video_url",
        "max_source_s": 23.0,
        "added_s": 7,
        "ratios": ["16:9", "9:16"],
        "hauteurs": [720, 1080],          # le plus petit côté : 720p ou 1080p
        "usd_per_s": {"son": 0.15, "muet": 0.10},
    },
    "veo-3.1-extend": {
        "label": "Veo 3.1 · extension",
        "endpoint": "fal-ai/veo3.1/extend-video",
        "video_param": "video_url",
        "max_source_s": 23.0,
        "added_s": 7,
        "ratios": ["16:9", "9:16"],
        "hauteurs": [720, 1080],
        "usd_per_s": {"son": 0.40, "muet": 0.20},
    },
}


def _bin(name: str) -> str:
    exe = shutil.which(name)
    if exe:
        return exe
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{name}.exe")
    return cand if os.path.isfile(cand) else name


def ratio_of(w: int, h: int) -> str:
    """Le format NOMMÉ le plus proche — l'app n'en connaît que quatre."""
    if not w or not h:
        return "?"
    r = w / float(h)
    connus = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5}
    return min(connus, key=lambda k: abs(connus[k] - r))


def probe(path) -> dict:
    """{duration_s, width, height, ratio} d'un fichier vidéo, par ffprobe."""
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"Clip source introuvable : {p.name}")
    out = subprocess.run([_bin("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-show_entries", "format=duration", "-of", "json", str(p)],
                         capture_output=True, timeout=60)
    try:
        d = json.loads(out.stdout.decode("utf-8", "replace") or "{}")
    except ValueError:
        d = {}
    st = (d.get("streams") or [{}])[0]
    w, h = int(st.get("width") or 0), int(st.get("height") or 0)
    dur = float((d.get("format") or {}).get("duration") or 0)
    return {"duration_s": round(dur, 3), "width": w, "height": h, "ratio": ratio_of(w, h)}


def guard_extend(model_id: str, src: dict) -> None:
    """Lève ValueError AVANT tout appel payant, message citant la mesure."""
    m = EXTEND_MODELS.get(model_id)
    if m is None:
        raise ValueError(f"Modèle d'extension inconnu : {model_id}. Disponibles : " + ", ".join(sorted(EXTEND_MODELS)))
    d = float(src.get("duration_s") or 0)
    if d <= 0:
        raise ValueError("Durée du clip source illisible — ffprobe n'a rien rendu.")
    if d > m["max_source_s"]:
        raise ValueError(f"{m['label']} prolonge jusqu'à 30 s au total ; ce clip fait {d:.1f} s (au plus "
                         f"{m['max_source_s']:.0f} s). Coupez-le au Montage, puis relancez l'extension sur le morceau.")
    w, h = int(src.get("width") or 0), int(src.get("height") or 0)
    if src.get("ratio") not in m["ratios"] or abs((w / h if h else 0) - (16 / 9 if w >= h else 9 / 16)) > 0.02:
        raise ValueError(f"{m['label']} n'accepte que {' et '.join(m['ratios'])} ; ce clip est en "
                         f"{src.get('ratio')} ({w}x{h}).")
    if min(w, h) not in m["hauteurs"]:
        raise ValueError(f"{m['label']} n'accepte que du 720p ou du 1080p ; ce clip fait {w}x{h}.")


def prix(model_id: str, son: bool) -> float:
    m = EXTEND_MODELS[model_id]
    return round(m["added_s"] * m["usd_per_s"]["son" if son else "muet"], 4)


def build_extend_args(model_id: str, *, video_url: str, prompt: str, son: bool = True) -> tuple:
    """(endpoint, arguments). Le prompt est OBLIGATOIRE pour fal : vide, on refuse ici plutôt qu'après l'upload."""
    m = EXTEND_MODELS[model_id]
    if not (prompt or "").strip():
        raise ValueError("Décrivez ce qui se passe dans les secondes ajoutées : fal exige un prompt.")
    return m["endpoint"], {m["video_param"]: video_url, "prompt": prompt.strip(), "generate_audio": bool(son)}
