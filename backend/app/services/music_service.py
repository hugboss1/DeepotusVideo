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
from app.i18n import Message   # t192 : refus et notes traduisibles (texte = le français)

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
        # t187 (12/10/2026) : le catalogue fal liste la forme minuscule (les deux casses répondent) ; schéma relu :
        # `duration` 10-180 (la borne basse était 5 : une demande à 5 s rendait une 422)
        "endpoint": "cassetteai/music-generator",
        "desc": "Le rapide : jusqu'à 3 min en quelques secondes de calcul, "
                "44.1 kHz stéréo. Idéal pour itérer sur une ambiance.",
        "duration": (10, 180), "fixed_duration": None,
        "lyrics": False, "instrumental": False, "seed": False,
        # t187 : tarif relu le 12/10/2026, 0,02 $ par minute de sortie — compté à la minute ENTAMÉE (borne
        # prudente, comme ElevenLabs Music) ; c'était 0,04 $ fixe
        "usd": 0.02, "usd_unit": "min",
    },
    # ── T102 (plan-son-vfx T6, P4) : la chanson chantée ─────────────────────
    # Schémas relus le 06/10/2026 sur l'openapi « queue » de fal :
    # ace-step `duration` 5-240 (défaut 60), `tags` REQUIS, pas de `prompt` ;
    # minimax-music/v2 `prompt` 10-2000 (le plan du 03/09 disait 300) et
    # `lyrics_prompt` 10-3000, TOUS DEUX requis. « MiniMax Music 3 » :
    # minimax-music/v3 rend 404 à l'openapi — il n'entre pas au registre (on
    # n'invente pas un identifiant).
    "ace-step": {
        "label": "ACE-Step (paroles)", "provider": "fal",
        "endpoint": "fal-ai/ace-step",
        "desc": "Le moins cher : chanson complète avec paroles structurées "
                "[verse]/[chorus]/[bridge]. Genres en balises, graine "
                "reproductible.",
        "duration": (5, 240), "fixed_duration": None,
        "lyrics": True, "instrumental": True, "seed": True,
        # « $0.0002 per second of generated audio » (page modèle, 06/10)
        "usd": 0.0002, "usd_unit": "s", "lyrics_style": "ace",
    },
    "minimax-music-20": {
        "label": "MiniMax Music 2.0", "provider": "fal",
        "endpoint": "fal-ai/minimax-music/v2",
        "desc": "Chanson chantée à partir de paroles OBLIGATOIRES "
                "(10 à 3000 caractères) et d'une description.",
        "duration": None, "fixed_duration": None,
        "lyrics": True, "instrumental": False, "seed": False,
        # « $0.03 per generation » (page modèle, 06/10)
        "usd": 0.03, "usd_unit": "gen", "lyrics_style": "minimax",
        "lyrics_required": True, "prompt_max": 2000,
    },
    # ── t187 (G5, plan « Génération IA enrichie ») : musique à jour ─────────
    # Schémas relus le 12/10/2026 sur l'openapi « queue » de fal ; aucun autre
    # nom de paramètre n'est inventé. Ces entrées NOMMENT leurs champs fal
    # (`champs` : prompt, duree [+ duree_ms], paroles, instrumental, seed,
    # negatif) et leurs arguments `fixe` — `_payload_champs` les lit, sans les
    # règles historiques (seconds_total, lyrics_prompt, is_instrumental) des
    # entrées d'avant. Prix : Lyria 3.5, MiniMax Music 3 et Stable Audio 3 « à
    # mesurer » (0 $) ; ElevenLabs Music 0,60 $ par minute de sortie ARRONDIE À
    # LA MINUTE SUPÉRIEURE ; Mureka 9.5 0,225 $ la requête AVEC paroles,
    # 0,75 $ la requête sur description seule.
    "lyria-3.5": {
        "label": "Lyria 3.5 (Google)", "provider": "fal",
        "endpoint": "google/lyria-3.5",
        "desc": "La nouvelle génération Lyria : description et ce qu'il faut "
                "éviter (prompt négatif). Durée choisie par le modèle.",
        "duration": None, "fixed_duration": None,
        "lyrics": False, "instrumental": False, "seed": False,
        "usd": 0.0, "champs": {"prompt": "prompt", "negatif": "negative_prompt"},
    },
    "elevenlabs-music-2.5": {
        "label": "ElevenLabs Music 2.5", "provider": "fal",
        "endpoint": "elevenlabs/music/v2.5",
        "desc": "Piste de 3 s à 10 min, instrumentale ou chantée. Facturée "
                "à la minute entamée.",
        "duration": (3, 600), "fixed_duration": None, "default_s": 60,
        "lyrics": False, "instrumental": True, "seed": True,
        "usd": 0.60, "usd_unit": "min",
        "champs": {"prompt": "prompt", "duree": "music_length_ms", "duree_ms": True,
                   "instrumental": "force_instrumental", "seed": "seed"},
        "fixe": {"output_format": "mp3_44100_128"}, "prompt_max": 4100,
    },
    "minimax-music-3": {
        "label": "MiniMax Music 3", "provider": "fal",
        "endpoint": "minimax/music-3",
        "desc": "Chanson chantée : description ET paroles obligatoires, "
                "jusqu'à 5 min.",
        "duration": (1, 300), "fixed_duration": None, "default_s": 60,
        "lyrics": True, "instrumental": False, "seed": True,
        "usd": 0.0, "lyrics_style": "minimax", "lyrics_required": True,
        "champs": {"prompt": "prompt", "duree": "duration", "paroles": "lyrics", "seed": "seed"},
    },
    "stable-audio-3": {
        "label": "Stable Audio 3", "provider": "fal",
        "endpoint": "fal-ai/stable-audio-3/medium/text-to-audio",
        "desc": "Durée libre jusqu'à 380 s, nappes et ambiances ; prompt "
                "négatif et graine reproductible.",
        "duration": (1, 380), "fixed_duration": None, "default_s": 60,
        "lyrics": False, "instrumental": False, "seed": True,
        "usd": 0.0,
        "champs": {"prompt": "prompt", "duree": "duration", "negatif": "negative_prompt", "seed": "seed"},
    },
    "mureka-9.5": {
        "label": "Mureka 9.5", "provider": "fal",
        "endpoint": "mureka/api/generate/song",
        "desc": "Chanson complète, avec vos paroles (0,225 $) ou sur simple "
                "description (0,75 $).",
        "duration": None, "fixed_duration": None,
        "lyrics": True, "instrumental": False, "seed": False,
        "usd": 0.75, "usd_paroles": 0.225, "lyrics_style": "minimax",
        "champs": {"prompt": "prompt", "paroles": "lyrics"},
        "fixe": {"model": "mureka-9.5"}, "lyrics_max": 5000,
    },
}
# la convention de balises de 2.6 est celle de Music 2.0 ([Verse]/[Chorus])
MUSIC_MODELS["minimax-music-26"]["lyrics_style"] = "minimax"

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


def _nom(model: dict, mid: str | None = None):
    """t192 : le nom d'un modèle dans un message (libellé en français, ia.nom.<id> en anglais). L'id est passé quand
    l'appelant le connaît (pricing) ; sinon retrouvé par le LIBELLÉ (clé stable : unique dans MUSIC_MODELS)."""
    from app.i18n import Nom
    if mid is None:
        mid = next((k for k, v in MUSIC_MODELS.items() if v.get("label") == model.get("label")), "")
    return Nom(mid, model["label"])


class MusicError(Exception):
    """Erreur à traduire en HTTPException(status, message) par la route."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def catalog() -> dict:
    """Ce que l'UI a besoin de savoir pour dessiner le formulaire."""
    dispo = bool(str(settings.FAL_KEY or "").strip())
    return {
        "enabled": dispo,
        "default": DEFAULT_MUSIC_MODEL,
        "models": [
            {"id": k, "label": v["label"], "desc": v["desc"],
             "duration": list(v["duration"]) if v["duration"] else None,
             "fixed_duration": v["fixed_duration"], "lyrics": v["lyrics"],
             "instrumental": v["instrumental"], "seed": v["seed"],
             "usd": v["usd"], "usd_unit": v.get("usd_unit", "gen"),
             "lyrics_style": v.get("lyrics_style"),
             "lyrics_required": bool(v.get("lyrics_required")),
             # t187 : le prix AVEC paroles quand il diffère (Mureka) ; None ailleurs
             "usd_paroles": v.get("usd_paroles"),
             # t187 : « a_mesurer » quand le prix vaut 0 (jamais « gratuit » : l'écran dit « prix à mesurer »)
             "note": "" if v["usd"] else "a_mesurer",
             # t187 : la voie et SA clé — un modèle sans clé reste LISTÉ et choisissable (décision du 11/10/2026),
             # la carte dit « clé FAL_KEY à ajouter dans Réglages », le tir est refusé en 503 avant toute dépense
             "voie": "fal", "cle": "FAL_KEY", "dispo": dispo}
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
        raise MusicError(400, Message("musique.decrire"))
    return out[:_MAX_PROMPT]


# ── paroles structurées (T102) ─────────────────────────────────────────────
# Les deux familles ne lisent pas les mêmes balises : ACE-Step veut des
# minuscules ([verse]/[chorus]/[bridge], « [inst] » = instrumental), MiniMax
# des capitalisées ([Verse]/[Chorus], doc 2.6). L'utilisateur écrit dans la
# langue qu'il veut (couplet/refrain/pont) ; on traduit à l'envoi.
_TAG_MAP = {"verse": "verse", "couplet": "verse", "chorus": "chorus",
            "refrain": "chorus", "bridge": "bridge", "pont": "bridge",
            "intro": "intro", "outro": "outro"}
_TAG_RX = re.compile(r"\[([^\[\]\n]{1,24})\]")


def normalize_lyrics(text: str, style: str | None,
                     instrumental: bool = False) -> str:
    """Paroles balisées -> convention du modèle. Un tag inconnu ([Solo]) est
    laissé tel quel : le modèle le lit ou l'ignore, on ne l'efface pas."""
    if style == "ace" and instrumental:
        return "[inst]"

    def sub(m):
        k = _TAG_MAP.get(m.group(1).strip().lower())
        if not k:
            return m.group(0)
        return f"[{k}]" if style == "ace" else f"[{k.capitalize()}]"
    return _TAG_RX.sub(sub, str(text or "").strip())[:_MAX_LYRICS]


def lyrics_skeleton(persona_id: str | None = None, theme: str = "") -> str:
    """Squelette [Verse]/[Chorus]/[Verse]/[Bridge]/[Chorus] nourri par la
    persona (nom, mots-clés d'univers) — un point de départ, jamais des
    paroles finies. Persona illisible : le squelette sort quand même."""
    from app.services import espaces          # t201 : le persona de l'espace (courant par defaut)
    pid = str(persona_id or "")
    try:
        d = espaces.persona(persona_id)
    except Exception:  # noqa: BLE001
        d = {}
    name = str(d.get("display_name") or pid).split(" — ")[0]
    kws = ", ".join(str(k) for k in (d.get("vibe_keywords") or [])[:4])
    from app.services import textes_espace    # t208 : le thème de repli est celui de l'espace
    try:
        repli = textes_espace.textes(persona_id)["musique_theme"]
    except Exception:  # noqa: BLE001
        repli = "the story so far"
    t = str(theme or "").strip()[:120] or repli
    return (f"[Verse]\n{name} — {t}\n{kws}\n\n[Chorus]\n{name}, {t}\n\n"
            f"[Verse]\n…\n\n[Bridge]\n…\n\n[Chorus]\n{name}, {t}")


def default_seconds(model: dict) -> int | None:
    """La durée envoyée quand l'utilisateur n'en donne pas — UNE fonction,
    lue par `_payload` ET par l'estimation (pricing) : un modèle facturé à la
    seconde doit être chiffré sur la durée qui partira vraiment. t187 : une
    entrée peut nommer son défaut (`default_s`, 60 s pour ElevenLabs Music :
    le milieu de 3-600 s coûterait 3 $ par défaut)."""
    if not model.get("duration"):
        return None
    return int(model.get("default_s") or model["duration"][1] // 2)


def usd_de(model: dict, duration_s=None, paroles: bool = False) -> float:
    """t187 — LE prix d'UNE génération d'un modèle de musique, lu par le devis
    (pricing, kind « music ») ET par la réponse de generate_music : « gen »
    (par génération ; Mureka : `usd_paroles` quand des paroles partent),
    « s » (à la seconde, sur la durée envoyée), « min » (à la minute de sortie
    ARRONDIE À LA MINUTE SUPÉRIEURE, ElevenLabs Music)."""
    import math
    base = float(model.get("usd_paroles") if (paroles and model.get("usd_paroles") is not None)
                 else model.get("usd") or 0.0)
    unit = model.get("usd_unit", "gen")
    if unit in ("s", "min"):
        sec = billed_seconds(model, duration_s) or 0
        return base * (sec if unit == "s" else math.ceil(sec / 60))
    return base


def billed_seconds(model: dict, duration_s=None) -> int | None:
    """Durée facturée d'un modèle à la seconde (bornée à sa plage), sinon None."""
    if not model.get("duration"):
        return None
    lo, hi = model["duration"]
    try:
        d = (int(round(float(duration_s))) if duration_s not in (None, "", 0)
             else default_seconds(model))
    except (TypeError, ValueError):
        d = default_seconds(model)
    return max(lo, min(hi, d))


def _duree(model: dict, dur) -> int:
    """t187 : la durée envoyée par une entrée à `champs`, bornée à la plage du modèle — 400 nommé sinon."""
    lo, hi = model["duration"]
    try:
        d = (int(round(float(dur))) if dur not in (None, "", 0)
             else default_seconds(model))
    except (TypeError, ValueError):
        raise MusicError(400, f"duration_s invalide ({lo}-{hi} s).")
    if not lo <= d <= hi:
        raise MusicError(400, Message("musique.duree_bornes", lo=lo, hi=hi, modele=_nom(model)))
    return d


def _payload_champs(model: dict, prompt: str, body: dict) -> tuple[dict, list[str]]:
    """t187 — la charge utile d'une entrée qui NOMME ses champs fal (`champs`) : rien d'autre ne part."""
    ch = model["champs"]
    args: dict = dict(model.get("fixe") or {})
    notes: list[str] = []
    args[ch["prompt"]] = prompt[:model.get("prompt_max", _MAX_PROMPT)]
    dur = body.get("duration_s")
    if ch.get("duree") and model.get("duration"):
        d = _duree(model, dur)
        args[ch["duree"]] = d * 1000 if ch.get("duree_ms") else d
    elif dur not in (None, "", 0):
        notes.append(Message("musique.note.duree_imposee", modele=_nom(model)))
    lyrics = str(body.get("lyrics") or "").strip()
    chante = len(_TAG_RX.sub("", lyrics).strip())
    if ch.get("paroles"):
        if model.get("lyrics_required") and chante < 10:
            raise MusicError(400, Message("musique.paroles_exigees_10", modele=_nom(model)))
        if chante:
            args[ch["paroles"]] = normalize_lyrics(
                lyrics, model.get("lyrics_style"))[:model.get("lyrics_max", _MAX_LYRICS)]
    elif lyrics:
        notes.append(Message("musique.note.sans_paroles", modele=_nom(model)))
    if ch.get("instrumental") and model.get("instrumental"):
        args[ch["instrumental"]] = bool(body.get("instrumental", True))
    neg = str(body.get("negative_prompt") or "").strip()
    if ch.get("negatif") and neg:
        args[ch["negatif"]] = neg[:_MAX_PROMPT]
    seed = body.get("seed")
    if ch.get("seed") and seed not in (None, ""):
        try:
            args[ch["seed"]] = int(seed)
        except (TypeError, ValueError):
            raise MusicError(400, "seed doit être un entier.")
    elif seed not in (None, "") and not ch.get("seed"):
        notes.append(Message("musique.note.sans_graine", modele=_nom(model)))
    return args, notes


def paroles_envoyees(model: dict, body: dict) -> bool:
    """t187 : des paroles partiront-elles ? (le prix de Mureka en dépend)."""
    if not (model.get("champs") or {}).get("paroles"):
        return False
    return bool(_TAG_RX.sub("", str((body or {}).get("lyrics") or "")).strip())


def _payload(model: dict, prompt: str, body: dict) -> tuple[dict, list[str]]:
    """Charge utile fal + liste des réglages ignorés faute de support."""
    if model.get("champs"):
        return _payload_champs(model, prompt, body)
    args: dict = {"prompt": prompt}
    notes: list[str] = []

    dur = body.get("duration_s")
    if model["duration"]:
        lo, hi = model["duration"]
        try:
            d = (int(round(float(dur))) if dur not in (None, "", 0)
                 else default_seconds(model))
        except (TypeError, ValueError):
            raise MusicError(400, f"duration_s invalide ({lo}-{hi} s).")
        if not lo <= d <= hi:
            raise MusicError(400, Message("musique.duree_bornes", lo=lo, hi=hi, modele=_nom(model)))
        args["seconds_total" if "stable-audio" in model["endpoint"]
             else "duration"] = d
    elif dur not in (None, "", 0):
        fixed = model["fixed_duration"]
        notes.append(Message("musique.note.duree_imposee_s", modele=_nom(model), s=f"{fixed:g}") if fixed
                     else Message("musique.note.duree_imposee", modele=_nom(model)))

    lyrics = str(body.get("lyrics") or "").strip()
    instrumental = bool(body.get("instrumental", True))
    style = model.get("lyrics_style")
    if style == "ace":
        # ACE-Step n'a PAS de `prompt` : la description part en `tags`
        # (genres séparés par des virgules, seul champ requis). Sans paroles,
        # c'est un instrumental — « [inst] », sa convention. La graine est
        # posée plus bas par la branche commune.
        body_args, args = args, {"tags": prompt[:_MAX_PROMPT]}
        if "duration" in body_args:
            args["duration"] = body_args["duration"]
        args["lyrics"] = normalize_lyrics(
            lyrics, "ace", instrumental=instrumental or not lyrics)
    elif model.get("lyrics_required"):
        # Music 2.0 : paroles ET description obligatoires (schéma : 10 car.
        # minimum chacune) — un refus nommé vaut mieux qu'une 422 de fal. Les
        # BALISES ne comptent pas : « [Verse]\n[Chorus]\nla » fait 16
        # caractères pour fal mais ne chante que deux lettres (mesuré au banc
        # d'écran : l'éditeur sérialise ses sections, et une section vide
        # passait la borne de fal à elle seule).
        if len(_TAG_RX.sub("", lyrics).strip()) < 10:
            raise MusicError(400, Message("musique.paroles_exigees_3000", modele=_nom(model)))
        args["prompt"] = prompt[:model.get("prompt_max", _MAX_PROMPT)]
        args["lyrics_prompt"] = normalize_lyrics(lyrics, "minimax")[:3000]
    elif model["lyrics"]:
        if lyrics:
            args["lyrics"] = normalize_lyrics(lyrics, style)
            args["is_instrumental"] = False
        elif instrumental:
            args["is_instrumental"] = True
        else:
            # voix demandée sans paroles fournies : le modèle sait les écrire
            args["is_instrumental"] = False
            args["lyrics_optimizer"] = True
    elif lyrics:
        notes.append(Message("musique.note.sans_paroles", modele=_nom(model)))

    seed = body.get("seed")
    if model["seed"] and seed not in (None, ""):
        try:
            args["seed"] = int(seed)
        except (TypeError, ValueError):
            raise MusicError(400, "seed doit être un entier.")
    elif seed not in (None, "") and not model["seed"]:
        notes.append(Message("musique.note.sans_graine", modele=_nom(model)))
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


def modele_de(body: dict) -> tuple[str, dict]:
    """t187 : (id, entrée) du modèle demandé (défaut : DEFAULT_MUSIC_MODEL) — 400 nommé pour un id inconnu."""
    model_id = str((body or {}).get("model") or DEFAULT_MUSIC_MODEL).strip()
    model = MUSIC_MODELS.get(model_id)
    if model is None:
        raise MusicError(400, f"modèle de musique inconnu : {model_id!r} "
                              f"(voir GET /api/music-models)")
    return model_id, model


def preparer(body: dict) -> dict:
    """t187 — les refus GRATUITS d'une demande (id, description, paroles exigées, durée, graine), AVANT la garde
    des plafonds : la route l'appelle d'abord, puis garde, puis tire avec ce qu'elle rend."""
    body = body or {}
    model_id, model = modele_de(body)
    prompt = build_prompt(body.get("prompt", ""), body.get("mood", ""))
    args, notes = _payload(model, prompt, body)
    return {"model_id": model_id, "model": model, "prompt": prompt, "args": args, "notes": notes,
            "paroles": paroles_envoyees(model, body)}


async def generate_music(body: dict, prep: dict | None = None) -> dict:
    """Génère une piste et la dépose dans la Bibliothèque (sons).

    Retourne {ok, item:{filename,url,name,dur,size_kb}, model, prompt, notes}.
    t187 : `prep` = le résultat de `preparer` (la route l'a déjà calculé avant sa garde).
    """
    import asyncio

    import fal_client

    from app.services import sfx_service

    if not str(settings.FAL_KEY or "").strip():
        # filet : la route /audio/music refuse déjà en 503 (nommant FAL_KEY) AVANT sa garde ; un appelant direct
        # reçoit le même code
        raise MusicError(503, "fal.ai: clé FAL_KEY à ajouter dans Réglages.")

    prep = prep or preparer(body)
    model_id, model, prompt = prep["model_id"], prep["model"], prep["prompt"]
    args, notes = prep["args"], prep["notes"]

    logger.info("music [{}] -> {} · args={}", model_id, model["endpoint"],
                {k: v for k, v in args.items()
                 if k not in ("lyrics", "lyrics_prompt")})
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
        # un modèle à la seconde coûte usd x la durée DEMANDÉE (celle envoyée) ; t187 : la règle unique usd_de
        # (minute entamée d'ElevenLabs Music, prix avec / sans paroles de Mureka)
        "usd": round(usd_de(model, (body or {}).get("duration_s"), prep["paroles"]), 6),
    }
