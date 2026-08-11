# -*- coding: utf-8 -*-
"""Génération de musique — fal.ai, avec la clé FAL déjà configurée.

L'écran Son & VFX annonçait « la génération de musique n'est pas encore
câblée » et affichait une estimation de $0.14 la piste. Ce module la câble sur
la MÊME clé fal.ai que la vidéo : personne n'a de compte à créer, personne
n'entre une clé de plus.

Registre `MUSIC_MODELS` sur le modèle de fal_service.VIDEO_MODELS — les
identifiants d'endpoint et les capacités ont été relevés sur le catalogue fal
en direct le 11/08/2026 (pages /models/<id>/api). Les capacités décrivent ce
que l'endpoint accepte VRAIMENT :

  duration    None = durée imposée par le modèle (Lyria fait 30 s, point)
  lyrics      l'endpoint accepte des paroles structurées ([Verse], [Chorus]…)
  instrumental l'endpoint a un interrupteur voix/instrumental
  seed        l'endpoint accepte une graine (reproductibilité)

Un modèle qui n'a pas un réglage ne le reçoit pas — on ne bricole pas un
paramètre inventé dans la charge utile, fal renvoie une 422 et l'utilisateur
lit une erreur incompréhensible. Ce qui est ignoré est REMONTÉ dans `notes`
pour que l'UI puisse le dire.

Le fichier produit atterrit dans le dossier audio de la Bibliothèque avec le
sidecar kind « musique » — donc directement disponible dans le tiroir Sons du
Montage et le sélecteur de piste de fond, sans étape d'import.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

DEFAULT_MUSIC_MODEL = "lyria3"

MUSIC_MODELS: dict = {
    "lyria3": {
        "label": "Lyria 3 (Google)", "provider": "fal",
        "endpoint": "fal-ai/lyria3",
        "desc": "Le plus abouti du catalogue. 30 s, 44.1 kHz, gère la voix "
                "chantée et les paroles (fr, en, es, de, ja, ko, pt, hi).",
        "duration": None, "fixed_duration": 30.0,
        "lyrics": False, "instrumental": False, "seed": False,
        "usd": 0.10,
    },
    "stable-audio-25": {
        "label": "Stable Audio 2.5", "provider": "fal",
        "endpoint": "fal-ai/stable-audio-25/text-to-audio",
        "desc": "Durée libre jusqu'à 190 s — le choix quand la piste doit "
                "couvrir toute la vidéo. Fait aussi des nappes et des SFX.",
        "duration": (5, 190), "fixed_duration": None,
        "lyrics": False, "instrumental": False, "seed": True,
        "usd": 0.06,
    },
    "minimax-music-26": {
        "label": "MiniMax Music 2.6", "provider": "fal",
        "endpoint": "fal-ai/minimax-music/v2.6",
        "desc": "Vraie chanson : couplets, refrains, voix chantée — ou "
                "instrumental. Pour un générique ou un hymne de marque.",
        "duration": None, "fixed_duration": None,
        "lyrics": True, "instrumental": True, "seed": False,
        "usd": 0.14,
    },
    "cassetteai": {
        "label": "CassetteAI", "provider": "fal",
        "endpoint": "CassetteAI/music-generator",
        "desc": "Le rapide : jusqu'à 3 min en quelques secondes de calcul, "
                "44.1 kHz stéréo. Idéal pour itérer sur une ambiance.",
        "duration": (5, 180), "fixed_duration": None,
        "lyrics": False, "instrumental": False, "seed": False,
        "usd": 0.04,
    },
}

# Ambiances proposées dans l'UI : un libellé + le fragment de prompt qu'il
# injecte. Elles existent parce qu'un prompt de musique vide donne toujours le
# même résultat tiède — nommer un genre, un tempo et une instrumentation est ce
# qui change tout, et l'utilisateur ne le devine pas.
MOODS = [
    {"id": "cinematic", "name": "Cinématique",
     "prompt": "cinematic orchestral score, wide strings, deep brass swells, "
               "slow build, epic and solemn, 70 BPM"},
    {"id": "abyss", "name": "Abysses",
     "prompt": "dark ambient underwater drone, sub bass pulses, distant sonar "
               "pings, sparse metallic textures, ominous, 60 BPM"},
    {"id": "hype", "name": "Hype / trailer",
     "prompt": "aggressive trailer music, punchy braams, tight percussion "
               "risers, driving momentum, 128 BPM"},
    {"id": "lofi", "name": "Lo-fi",
     "prompt": "lo-fi hip hop beat, warm dusty piano chords, vinyl crackle, "
               "relaxed swung drums, 82 BPM"},
    {"id": "synthwave", "name": "Synthwave",
     "prompt": "retro synthwave, analog arpeggios, gated reverb drums, neon "
               "lead, nostalgic and driving, 110 BPM"},
    {"id": "corporate", "name": "Corporate clair",
     "prompt": "bright uplifting corporate track, plucked guitar, claps, "
               "optimistic piano motif, clean and modern, 118 BPM"},
    {"id": "tension", "name": "Tension",
     "prompt": "suspense underscore, pulsing ostinato strings, ticking "
               "percussion, rising unease, 96 BPM"},
    {"id": "chill", "name": "Ambiance calme",
     "prompt": "soft ambient pad, gentle felt piano, airy textures, no drums, "
               "spacious and warm, 65 BPM"},
]

MOOD_BY_ID = {m["id"]: m for m in MOODS}

_MAX_PROMPT = 2000
_MAX_LYRICS = 3500


class MusicError(Exception):
    """Erreur à traduire en HTTPException(status, message) par la route."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def catalog() -> dict:
    """Ce que l'UI a besoin de savoir pour dessiner le formulaire."""
    return {
        "enabled": bool(settings.FAL_KEY),
        "default": DEFAULT_MUSIC_MODEL,
        "models": [
            {"id": k, "label": v["label"], "desc": v["desc"],
             "duration": list(v["duration"]) if v["duration"] else None,
             "fixed_duration": v["fixed_duration"], "lyrics": v["lyrics"],
             "instrumental": v["instrumental"], "seed": v["seed"],
             "usd": v["usd"]}
            for k, v in MUSIC_MODELS.items()],
        "moods": MOODS,
    }


def build_prompt(prompt: str, mood: str = "") -> str:
    """Prompt final = ambiance choisie + description libre. L'ambiance passe
    devant : les modèles de musique lisent surtout le début du prompt."""
    bits = []
    m = MOOD_BY_ID.get(str(mood or "").strip())
    if m:
        bits.append(m["prompt"])
    p = str(prompt or "").strip()
    if p:
        bits.append(p)
    out = ", ".join(bits)
    if not out:
        raise MusicError(400, "Décris la musique voulue, ou choisis une "
                              "ambiance.")
    return out[:_MAX_PROMPT]


def _payload(model: dict, prompt: str, body: dict) -> tuple[dict, list[str]]:
    """Charge utile fal + liste des réglages ignorés faute de support."""
    args: dict = {"prompt": prompt}
    notes: list[str] = []

    dur = body.get("duration_s")
    if model["duration"]:
        lo, hi = model["duration"]
        try:
            d = int(round(float(dur))) if dur not in (None, "", 0) else hi // 2
        except (TypeError, ValueError):
            raise MusicError(400, f"duration_s invalide ({lo}-{hi} s).")
        if not lo <= d <= hi:
            raise MusicError(400, f"duration_s doit être entre {lo} et {hi} s "
                                  f"pour {model['label']}.")
        args["seconds_total" if "stable-audio" in model["endpoint"]
             else "duration"] = d
    elif dur not in (None, "", 0):
        fixed = model["fixed_duration"]
        notes.append(
            f"{model['label']} impose sa durée"
            + (f" ({fixed:g} s)" if fixed else "")
            + " — la durée demandée a été ignorée.")

    lyrics = str(body.get("lyrics") or "").strip()
    instrumental = bool(body.get("instrumental", True))
    if model["lyrics"]:
        if lyrics:
            args["lyrics"] = lyrics[:_MAX_LYRICS]
            args["is_instrumental"] = False
        elif instrumental:
            args["is_instrumental"] = True
        else:
            # voix demandée sans paroles fournies : le modèle sait les écrire
            args["is_instrumental"] = False
            args["lyrics_optimizer"] = True
    elif lyrics:
        notes.append(f"{model['label']} ne prend pas de paroles — le texte "
                     f"saisi a été ignoré.")

    seed = body.get("seed")
    if model["seed"] and seed not in (None, ""):
        try:
            args["seed"] = int(seed)
        except (TypeError, ValueError):
            raise MusicError(400, "seed doit être un entier.")
    elif seed not in (None, "") and not model["seed"]:
        notes.append(f"{model['label']} n'accepte pas de graine — le résultat "
                     f"n'est pas reproductible.")
    return args, notes


def _audio_url(result: dict) -> str:
    """L'URL du fichier, quel que soit le nom du champ selon l'endpoint
    (`audio`, `audio_file`, `audio_url`…). Les schémas fal ne sont pas
    homogènes entre familles de modèles, donc on cherche au lieu de supposer."""
    if not isinstance(result, dict):
        raise MusicError(502, "fal.ai: réponse inattendue (pas un objet).")
    for key in ("audio", "audio_file", "audio_url", "output", "file"):
        v = result.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict) and isinstance(v.get("url"), str):
            return v["url"]
        if isinstance(v, list) and v and isinstance(v[0], dict) \
                and isinstance(v[0].get("url"), str):
            return v[0]["url"]
    raise MusicError(502, f"fal.ai: aucune piste dans la réponse "
                          f"(clés: {', '.join(map(str, result))}).")


_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _filename(prompt: str, ext: str) -> str:
    base = unicodedata.normalize("NFKD", prompt[:40]).encode(
        "ascii", "ignore").decode()
    base = _SAFE.sub("_", base).strip("._-") or "musique"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"musique_{base}_{stamp}{ext}"


async def generate_music(body: dict) -> dict:
    """Génère une piste et la dépose dans la Bibliothèque (sons).

    Retourne {ok, item:{filename,url,name,dur,size_kb}, model, prompt, notes}.
    """
    import asyncio

    import fal_client

    from app.services import sfx_service

    if not settings.FAL_KEY:
        raise MusicError(400, "fal.ai: aucune clé configurée "
                              "(Réglages → clés API).")

    model_id = str(body.get("model") or DEFAULT_MUSIC_MODEL).strip()
    model = MUSIC_MODELS.get(model_id)
    if model is None:
        raise MusicError(400, f"modèle de musique inconnu : {model_id!r} "
                              f"(voir GET /api/music-models)")

    prompt = build_prompt(body.get("prompt", ""), body.get("mood", ""))
    args, notes = _payload(model, prompt, body)

    logger.info("music [{}] -> {} · args={}", model_id, model["endpoint"],
                {k: v for k, v in args.items() if k != "lyrics"})
    try:
        result = await fal_client.subscribe_async(
            model["endpoint"], arguments=args, with_logs=False)
    except Exception as e:
        raise MusicError(502, f"fal.ai: {str(e)[:300]}") from e

    url = _audio_url(result)
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in (".mp3", ".wav", ".ogg", ".m4a", ".flac"):
        ext = ".mp3"

    folder = settings.images_path.parent / "audio"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / _filename(prompt, ext)
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=300) as c:
            r = await c.get(url)
            r.raise_for_status()
            dest.write_bytes(r.content)
    except Exception as e:
        raise MusicError(502, f"fal.ai: téléchargement de la piste impossible "
                              f"({str(e)[:200]})") from e

    dur = await asyncio.get_running_loop().run_in_executor(
        None, sfx_service._probe_duration, dest)
    sfx_service.record_meta(dest.name, {
        "kind": "musique", "prompt": prompt, "model": model_id,
        "provider": "fal", "dur": dur,
        "created": datetime.now().isoformat(timespec="seconds")})

    return {
        "ok": True,
        "item": {"filename": dest.name, "url": f"/api/audio/{dest.name}",
                 "name": dest.stem, "dur": dur,
                 "size_kb": dest.stat().st_size // 1024},
        "model": model_id, "model_label": model["label"],
        "prompt": prompt, "notes": notes,
        "usd": model["usd"],
    }
